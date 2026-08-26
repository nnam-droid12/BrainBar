"""Builds the "Stage Health" dashboard JSON — provisioned as code into Grafana Cloud.

Panels cover every metric/log stream in architecture/telemetry-schema.md: frame time
and drops per node, VRAM/GPU health, genlock/timecode drift, tracking jitter, the
active-take marker, and a live log feed of slate/cut/warning/sync_loss/cue/node
events. The First AD annotates this dashboard per take (see agents/first_ad/), and the
DIT deep-links into it per take window (see agents/dit/).
"""
from __future__ import annotations

from simulator.grafana_provisioning.panel_helpers import (
    GridCursor,
    logs_panel,
    stat_panel,
    timeseries_panel,
)

DASHBOARD_UID = "brainbar-stage-health"

# Name of the Grafana ML metric forecast job this dashboard visualizes, if one has been
# created (see README.md's "Predictive VRAM forecasting" setup section — creating the
# job itself is a one-time Grafana Cloud portal action, not something provisioned here).
# agents/first_ad/agent.py queries this same job's output at runtime to act on it.
VRAM_FORECAST_JOB_NAME = "brainbar_vram_forecast"


def build_dashboard(prom_uid: str, loki_uid: str, ml_uid: str | None = None) -> dict:
    grid = GridCursor(row_height=8)
    panels = [
        stat_panel(
            "Active take",
            prom_uid,
            'brainbar_take_active == 1',
            grid.place(6, 4),
        ),
        stat_panel(
            "Frame drops (5m)",
            prom_uid,
            "sum(increase(brainbar_frame_drops_total[5m]))",
            grid.place(6, 4),
            thresholds=[
                {"color": "green", "value": None},
                {"color": "orange", "value": 1},
                {"color": "red", "value": 5},
            ],
        ),
        stat_panel(
            "Peak VRAM % (all nodes)",
            prom_uid,
            "max(brainbar_node_vram_percent)",
            grid.place(6, 4),
            unit="percent",
            thresholds=[
                {"color": "green", "value": None},
                {"color": "orange", "value": 85},
                {"color": "red", "value": 95},
            ],
        ),
        stat_panel(
            "Peak genlock drift (us)",
            prom_uid,
            "max(brainbar_genlock_drift_us)",
            grid.place(6, 4),
            thresholds=[
                {"color": "green", "value": None},
                {"color": "orange", "value": 200},
                {"color": "red", "value": 500},
            ],
        ),
        timeseries_panel(
            "Render frame time by node (ms)",
            prom_uid,
            [("brainbar_render_frame_time_ms", "{{node}}")],
            grid.place(12),
            unit="ms",
            thresholds=[{"color": "green", "value": None}, {"color": "red", "value": 16.6}],
        ),
        timeseries_panel(
            "Frame drops by node (rate)",
            prom_uid,
            [("rate(brainbar_frame_drops_total[1m])", "{{node}}")],
            grid.place(12),
        ),
        timeseries_panel(
            "VRAM % by node",
            prom_uid,
            [("brainbar_node_vram_percent", "{{node}}")],
            grid.place(8),
            unit="percent",
        ),
        timeseries_panel(
            "GPU temp by node (C)",
            prom_uid,
            [("brainbar_node_gpu_temp_c", "{{node}}")],
            grid.place(8),
            unit="celsius",
        ),
        timeseries_panel(
            "GPU util by node",
            prom_uid,
            [("brainbar_node_gpu_util_percent", "{{node}}")],
            grid.place(8),
            unit="percent",
        ),
        timeseries_panel(
            "Genlock drift by device (us)",
            prom_uid,
            [("brainbar_genlock_drift_us", "{{device}}")],
            grid.place(12),
            unit="µs",
        ),
        timeseries_panel(
            "Timecode drift by device (frames)",
            prom_uid,
            [("brainbar_timecode_drift_frames", "{{device}}")],
            grid.place(12),
        ),
        timeseries_panel(
            "Camera tracking jitter (mm)",
            prom_uid,
            [("brainbar_tracking_jitter_mm", "{{camera}}")],
            grid.place(12),
            unit="lengthmm",
        ),
        timeseries_panel(
            "Camera tracking latency (ms)",
            prom_uid,
            [("brainbar_tracking_latency_ms", "{{camera}}")],
            grid.place(12),
            unit="ms",
        ),
        logs_panel(
            "Stage event log — slate / cut / cue / warning / sync_loss / node up-down",
            loki_uid,
            '{service="stage"}',
            grid.place(24, 10),
        ),
    ]

    if ml_uid:
        panels.append(
            timeseries_panel(
                "VRAM % — actual vs. Grafana ML forecast, by node",
                ml_uid,
                [
                    (f"{VRAM_FORECAST_JOB_NAME}:actual", "{{node}} actual"),
                    (f"{VRAM_FORECAST_JOB_NAME}:predicted", "{{node}} forecast"),
                ],
                grid.place(24),
                unit="percent",
                thresholds=[
                    {"color": "green", "value": None},
                    {"color": "red", "value": 90},
                ],
            )
        )

    return {
        "uid": DASHBOARD_UID,
        "title": "BrainBar — Stage Health",
        "tags": ["brainbar", "stage"],
        "timezone": "utc",
        "schemaVersion": 39,
        "version": 1,
        "refresh": "5s",
        "time": {"from": "now-15m", "to": "now"},
        "panels": panels,
        "annotations": {
            "list": [
                {
                    "name": "Take verdicts",
                    "datasource": {"type": "grafana", "uid": "-- Grafana --"},
                    "enable": True,
                    "iconColor": "purple",
                    "type": "tags",
                    "tags": ["brainbar-verdict"],
                }
            ]
        },
    }
