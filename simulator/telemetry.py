"""OpenTelemetry wiring that pushes Stage Simulator telemetry to Grafana Cloud.

Metrics land in Mimir, logs in Loki, traces in Tempo — all via Grafana Cloud's OTLP
gateway. Field names here must match architecture/telemetry-schema.md exactly, since
the agent crew's PromQL/LogQL/Tempo queries are written against those names.
"""
from __future__ import annotations

import logging
import time
from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry._logs import SeverityNumber, set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.metrics import set_meter_provider
from opentelemetry.sdk._logs import LoggerProvider, LogRecord
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Status, StatusCode

from simulator.config import config

_log = logging.getLogger(__name__)


class StageTelemetry:
    """One instance per simulator process; owns every OTel provider and instrument."""

    def __init__(self) -> None:
        resource = Resource.create({"service.name": config.service_name})
        headers = config.otlp_headers

        tracer_provider = TracerProvider(resource=resource)
        tracer_provider.add_span_processor(
            BatchSpanProcessor(
                OTLPSpanExporter(endpoint=f"{config.otlp_endpoint}/v1/traces", headers=headers)
            )
        )
        trace.set_tracer_provider(tracer_provider)
        self.tracer = trace.get_tracer("brainbar.simulator")

        meter_provider = MeterProvider(
            resource=resource,
            metric_readers=[
                PeriodicExportingMetricReader(
                    OTLPMetricExporter(
                        endpoint=f"{config.otlp_endpoint}/v1/metrics", headers=headers
                    ),
                    export_interval_millis=2000,
                )
            ],
        )
        set_meter_provider(meter_provider)
        self.meter = meter_provider.get_meter("brainbar.simulator")

        logger_provider = LoggerProvider(resource=resource)
        logger_provider.add_log_record_processor(
            BatchLogRecordProcessor(
                OTLPLogExporter(endpoint=f"{config.otlp_endpoint}/v1/logs", headers=headers)
            )
        )
        set_logger_provider(logger_provider)
        self.logger = logger_provider.get_logger("brainbar.simulator")

        self._frame_time_ms = self.meter.create_gauge(
            "brainbar_render_frame_time_ms", unit="ms"
        )
        self._frame_drops_total = self.meter.create_counter("brainbar_frame_drops_total")
        self._vram_percent = self.meter.create_gauge("brainbar_node_vram_percent", unit="%")
        self._gpu_util_percent = self.meter.create_gauge(
            "brainbar_node_gpu_util_percent", unit="%"
        )
        self._gpu_temp_c = self.meter.create_gauge("brainbar_node_gpu_temp_c", unit="C")
        self._genlock_drift_us = self.meter.create_gauge(
            "brainbar_genlock_drift_us", unit="us"
        )
        self._timecode_drift_frames = self.meter.create_gauge(
            "brainbar_timecode_drift_frames"
        )
        self._wall_refresh_hz = self.meter.create_gauge("brainbar_wall_refresh_hz", unit="Hz")
        self._tracking_jitter_mm = self.meter.create_gauge(
            "brainbar_tracking_jitter_mm", unit="mm"
        )
        self._tracking_latency_ms = self.meter.create_gauge(
            "brainbar_tracking_latency_ms", unit="ms"
        )
        self._take_active = self.meter.create_gauge("brainbar_take_active")

        self.shutdown_hooks = [tracer_provider.shutdown, logger_provider.shutdown]

    # --- metrics -----------------------------------------------------------------

    def record_frame_time(self, node: str, take_id: str, ms: float) -> None:
        self._frame_time_ms.set(ms, {"node": node, "take_id": take_id})

    def record_frame_drop(self, node: str, take_id: str, count: int = 1) -> None:
        self._frame_drops_total.add(count, {"node": node, "take_id": take_id})

    def record_node_health(
        self, node: str, vram_percent: float, gpu_util_percent: float, gpu_temp_c: float
    ) -> None:
        self._vram_percent.set(vram_percent, {"node": node})
        self._gpu_util_percent.set(gpu_util_percent, {"node": node})
        self._gpu_temp_c.set(gpu_temp_c, {"node": node})

    def record_genlock_drift(self, device: str, drift_us: float) -> None:
        self._genlock_drift_us.set(drift_us, {"device": device})

    def record_timecode_drift(self, device: str, drift_frames: float) -> None:
        self._timecode_drift_frames.set(drift_frames, {"device": device})

    def record_wall_refresh(self, wall_region: str, hz: float) -> None:
        self._wall_refresh_hz.set(hz, {"wall_region": wall_region})

    def record_tracking(self, camera: str, jitter_mm: float, latency_ms: float) -> None:
        self._tracking_jitter_mm.set(jitter_mm, {"camera": camera})
        self._tracking_latency_ms.set(latency_ms, {"camera": camera})

    def set_take_active(self, take_id: str, scene: str, setup: str, active: bool) -> None:
        self._take_active.set(
            1 if active else 0, {"take_id": take_id, "scene": scene, "setup": setup}
        )

    # --- logs ----------------------------------------------------------------------

    def log_event(
        self,
        event_type: str,
        message: str,
        *,
        node: str = "",
        take_id: str = "",
        level: str = "info",
        **attrs: str,
    ) -> None:
        severity = SeverityNumber.WARN if level == "warning" else SeverityNumber.INFO
        self.logger.emit(
            LogRecord(
                timestamp=time.time_ns(),
                severity_number=severity,
                severity_text=level.upper(),
                body=message,
                attributes={
                    "service": "stage",
                    "node": node,
                    "take_id": take_id,
                    "level": level,
                    "event_type": event_type,
                    **attrs,
                },
            )
        )

    # --- traces ----------------------------------------------------------------------

    @contextmanager
    def frame_render_trace(self, take_id: str, frame_number: int, node: str):
        with self.tracer.start_as_current_span(
            "frame_render",
            attributes={"take_id": take_id, "frame_number": frame_number, "node": node},
        ) as span:
            yield span

    @contextmanager
    def pipeline_stage(self, name: str):
        with self.tracer.start_as_current_span(name) as span:
            yield span

    def mark_span_dropped(self, span: trace.Span, reason: str) -> None:
        span.set_status(Status(StatusCode.ERROR, reason))
        span.set_attribute("frame.dropped", True)
        span.set_attribute("frame.drop_reason", reason)

    def shutdown(self) -> None:
        for hook in self.shutdown_hooks:
            try:
                hook()
            except Exception:  # pragma: no cover - best-effort flush on exit
                _log.exception("telemetry shutdown hook failed")


telemetry = StageTelemetry()
