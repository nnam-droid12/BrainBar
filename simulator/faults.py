"""Fault injector: the only "scripted" part of a take's telemetry.

Faults are armed for the *next* take via `arm()` (called from the control API/CLI so
the demo is reproducible on cue), then activated when that take starts rolling. Each
fault perturbs the otherwise-clean per-frame telemetry a node/device/camera would
produce, matching the signatures documented in architecture/telemetry-schema.md.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from enum import StrEnum


class FaultType(StrEnum):
    VRAM_SPIKE = "vram_spike"
    NODE_DEATH = "node_death"
    GENLOCK_DRIFT = "genlock_drift"
    TRACKING_JITTER = "tracking_jitter"
    THERMAL_THROTTLE = "thermal_throttle"


@dataclass
class FrameReadout:
    frame_time_ms: float
    vram_percent: float
    gpu_util_percent: float
    gpu_temp_c: float
    dropped: bool
    drop_reason: str = ""


NODE_DEATH_TRIGGER_FRAME = 60
GENLOCK_DRIFT_THRESHOLD_US = 500.0
THERMAL_WARN_TEMP_C = 88.0


class FaultInjector:
    def __init__(self) -> None:
        self._armed: FaultType | None = None
        self._armed_node: str | None = None
        self.active_fault: FaultType | None = None
        self.active_node: str | None = None
        self._sync_loss_logged = False
        self._thermal_warned = False

    def arm(self, fault_type: FaultType | None, node: str | None = None) -> None:
        self._armed = fault_type
        self._armed_node = node

    @property
    def armed_fault(self) -> FaultType | None:
        return self._armed

    def activate_for_take(self, default_node: str) -> None:
        self.active_fault = self._armed
        self.active_node = self._armed_node or default_node
        self._armed = None
        self._armed_node = None
        self._sync_loss_logged = False
        self._thermal_warned = False

    def clear(self) -> None:
        self.active_fault = None
        self.active_node = None

    def is_node_dead(self, node: str, frame_number: int) -> bool:
        return (
            self.active_fault == FaultType.NODE_DEATH
            and node == self.active_node
            and frame_number >= NODE_DEATH_TRIGGER_FRAME
        )

    def frame_readout(
        self,
        node: str,
        frame_number: int,
        cue_active: bool,
        frame_budget_ms: float,
    ) -> FrameReadout:
        base_frame_time = random.uniform(9.5, 13.5)
        base_vram = random.uniform(45.0, 60.0)
        base_gpu_util = random.uniform(40.0, 65.0)
        base_gpu_temp = random.uniform(58.0, 68.0)

        if self.active_fault == FaultType.VRAM_SPIKE and node == self.active_node and cue_active:
            vram = random.uniform(95.0, 99.5)
            gpu_util = random.uniform(97.0, 100.0)
            frame_time = random.uniform(38.0, 62.0)
            dropped = frame_time > frame_budget_ms
            return FrameReadout(
                frame_time, vram, gpu_util, base_gpu_temp, dropped,
                "vram_saturation" if dropped else "",
            )

        if self.active_fault == FaultType.THERMAL_THROTTLE and node == self.active_node:
            progress = min(frame_number / 300.0, 1.0)
            temp = 60.0 + progress * 35.0
            frame_time = base_frame_time + progress * 18.0
            dropped = frame_time > frame_budget_ms
            return FrameReadout(
                frame_time, base_vram, base_gpu_util, temp, dropped,
                "thermal_throttle" if dropped else "",
            )

        dropped = base_frame_time > frame_budget_ms
        return FrameReadout(base_frame_time, base_vram, base_gpu_util, base_gpu_temp, dropped)

    def genlock_readout(self, device: str, frame_number: int) -> float:
        if self.active_fault == FaultType.GENLOCK_DRIFT and device == self.active_node:
            return min(frame_number * 2.2, 900.0)
        return random.uniform(0.0, 15.0)

    def timecode_drift_readout(self, device: str, frame_number: int) -> float:
        if self.active_fault == FaultType.GENLOCK_DRIFT and device == self.active_node:
            return min(frame_number / 45.0, 6.0)
        return 0.0

    def tracking_readout(self, camera: str, frame_number: int, cue_active: bool) -> tuple[float, float]:
        if self.active_fault == FaultType.TRACKING_JITTER and camera == self.active_node:
            jitter = random.uniform(4.5, 9.0) if cue_active else random.uniform(2.0, 4.5)
            latency = random.uniform(35.0, 70.0)
            return jitter, latency
        return random.uniform(0.1, 0.8), random.uniform(4.0, 9.0)

    def should_log_sync_loss(self, device: str, drift_us: float) -> bool:
        if (
            self.active_fault == FaultType.GENLOCK_DRIFT
            and device == self.active_node
            and drift_us >= GENLOCK_DRIFT_THRESHOLD_US
            and not self._sync_loss_logged
        ):
            self._sync_loss_logged = True
            return True
        return False

    def should_log_thermal_warning(self, node: str, temp_c: float) -> bool:
        if (
            self.active_fault == FaultType.THERMAL_THROTTLE
            and node == self.active_node
            and temp_c >= THERMAL_WARN_TEMP_C
            and not self._thermal_warned
        ):
            self._thermal_warned = True
            return True
        return False
