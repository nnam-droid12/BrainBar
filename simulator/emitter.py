"""Runs one take: paces frames at real camera fps, emitting metrics/logs/traces for
every node each frame, and notifies the backend on slate/cut so it can react live."""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

import httpx

from simulator.config import config
from simulator.faults import FaultInjector
from simulator.models import ShootScript, TakeState
from simulator.telemetry import StageTelemetry
from simulator.timecode import frames_to_timecode

_log = logging.getLogger(__name__)


def _notify_backend(event: str, payload: dict) -> None:
    """Best-effort but retried: a dropped "cut" notification leaves the backend
    thinking the take is still rolling forever (nothing else ever tells it the take
    ended), so a single 2s attempt with no retry was silently losing takes in
    deployment whenever the backend was mid cold-start. Three attempts with a longer
    per-attempt timeout comfortably covers a Cloud Run cold start (~5-10s)."""
    if not config.backend_webhook_url:
        return
    for attempt in range(3):
        try:
            resp = httpx.post(
                config.backend_webhook_url, json={"event": event, **payload}, timeout=15.0
            )
            resp.raise_for_status()
            return
        except httpx.HTTPError:
            if attempt == 2:
                _log.warning(
                    "backend webhook unreachable for event=%s after 3 attempts", event
                )
            else:
                time.sleep(2.0 * (attempt + 1))


class TakeRunner:
    def __init__(self, telemetry: StageTelemetry, faults: FaultInjector, shoot: ShootScript):
        self.telemetry = telemetry
        self.faults = faults
        self.shoot = shoot
        self._take_counters: dict[str, int] = {}
        self.current_take: TakeState | None = None
        self._abort = False

    def abort(self) -> None:
        self._abort = True

    def next_take_number(self, setup_id: str) -> int:
        n = self._take_counters.get(setup_id, 0) + 1
        self._take_counters[setup_id] = n
        return n

    def run_take(self, setup_id: str) -> TakeState:
        self._abort = False
        setup = self.shoot.setup(setup_id)
        take_number = self.next_take_number(setup_id)
        take_id = f"{self.shoot.scene.lower()}-setup{setup_id}-take{take_number}"
        take = TakeState(
            take_id=take_id, scene=self.shoot.scene, setup_id=setup_id, take_number=take_number
        )
        self.current_take = take

        default_node = config.node_ids[take_number % len(config.node_ids)]
        self.faults.activate_for_take(default_node=default_node)

        take.rolling = True
        take.start_timecode = frames_to_timecode(0, config.camera_fps)
        take.start_time_utc = datetime.now(timezone.utc).isoformat()
        self.telemetry.log_event(
            "slate",
            f"SLATE — {self.shoot.scene} setup {setup_id} take {take_number}",
            take_id=take.take_id,
            level="info",
            scene=self.shoot.scene,
            setup=setup_id,
            take=str(take_number),
            timecode=take.start_timecode,
        )
        self.telemetry.set_take_active(take.take_id, self.shoot.scene, setup_id, True)
        _notify_backend(
            "slate",
            {
                "take_id": take.take_id,
                "scene": self.shoot.scene,
                "setup": setup_id,
                "take": take_number,
                "fault_armed": str(self.faults.active_fault) if self.faults.active_fault else None,
                "start_time_utc": take.start_time_utc,
            },
        )

        node_down_logged: set[str] = set()
        frame_interval = (1.0 / config.camera_fps) / max(config.playback_speed, 0.01)

        for frame_number in range(1, config.take_length_frames + 1):
            if self._abort:
                break
            take.frame_number = frame_number
            self._emit_frame(take, setup, frame_number, node_down_logged)
            time.sleep(frame_interval)

        take.rolling = False
        take.end_timecode = frames_to_timecode(take.frame_number, config.camera_fps)
        take.end_time_utc = datetime.now(timezone.utc).isoformat()
        self.telemetry.log_event(
            "cut",
            f"CUT — {self.shoot.scene} setup {setup_id} take {take_number}",
            take_id=take.take_id,
            level="info",
            timecode=take.end_timecode,
        )
        self.telemetry.set_take_active(take.take_id, self.shoot.scene, setup_id, False)
        _notify_backend(
            "cut",
            {
                "take_id": take.take_id,
                "scene": self.shoot.scene,
                "setup": setup_id,
                "take": take_number,
                "start_timecode": take.start_timecode,
                "end_timecode": take.end_timecode,
                "start_time_utc": take.start_time_utc,
                "end_time_utc": take.end_time_utc,
            },
        )
        self.faults.clear()
        return take

    def _emit_frame(self, take: TakeState, setup, frame_number: int, node_down_logged: set[str]) -> None:
        t = self.telemetry
        cue_active = any(
            0 <= frame_number - cue.frame_number <= config.cue_active_window_frames
            for cue in setup.cues
        )
        for cue in setup.cues:
            if cue.frame_number == frame_number:
                t.log_event(
                    "cue",
                    f"CUE — {cue.type} at frame {frame_number}",
                    take_id=take.take_id,
                    level="info",
                    cue_type=cue.type,
                    frame_number=str(frame_number),
                )

        for node in config.node_ids:
            if self.faults.is_node_dead(node, frame_number):
                if node not in node_down_logged:
                    t.log_event(
                        "node_down", f"{node} went offline", node=node,
                        take_id=take.take_id, level="warning",
                    )
                    node_down_logged.add(node)
                    _notify_backend("node_down", {"node": node, "take_id": take.take_id})
                continue

            readout = self.faults.frame_readout(node, frame_number, cue_active, config.frame_budget_ms)
            t.record_frame_time(node, take.take_id, readout.frame_time_ms)
            t.record_node_health(node, readout.vram_percent, readout.gpu_util_percent, readout.gpu_temp_c)
            if readout.dropped:
                t.record_frame_drop(node, take.take_id)
            if self.faults.should_log_thermal_warning(node, readout.gpu_temp_c):
                t.log_event(
                    "warning",
                    f"{node} GPU temp {readout.gpu_temp_c:.1f}C — thermal throttle risk",
                    node=node, take_id=take.take_id, level="warning",
                )

            with t.frame_render_trace(take.take_id, frame_number, node) as root_span:
                with t.pipeline_stage("camera_tracking_ingest"):
                    pass
                with t.pipeline_stage("genlock_sync"):
                    pass
                with t.pipeline_stage("ndisplay_render") as render_span:
                    render_span.set_attribute("render.duration_ms", readout.frame_time_ms)
                    if readout.dropped:
                        t.mark_span_dropped(render_span, readout.drop_reason or "frame_budget_exceeded")
                        t.mark_span_dropped(root_span, readout.drop_reason or "frame_budget_exceeded")
                with t.pipeline_stage("composite"):
                    pass
                with t.pipeline_stage("wall_output"):
                    pass

        for device in config.node_ids:
            drift_us = self.faults.genlock_readout(device, frame_number)
            t.record_genlock_drift(device, drift_us)
            tc_drift = self.faults.timecode_drift_readout(device, frame_number)
            t.record_timecode_drift(device, tc_drift)
            if self.faults.should_log_sync_loss(device, drift_us):
                t.log_event(
                    "sync_loss",
                    f"{device} genlock drift {drift_us:.0f}us exceeds threshold",
                    node=device, take_id=take.take_id, level="warning", drift_us=f"{drift_us:.0f}",
                )

        t.record_wall_refresh("wall-full", config.wall_refresh_hz)
        jitter_mm, latency_ms = self.faults.tracking_readout("cam-A", frame_number, cue_active)
        t.record_tracking("cam-A", jitter_mm, latency_ms)
