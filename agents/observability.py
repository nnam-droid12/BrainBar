"""Grafana AI Observability: the crew watching itself.

ADK already emits OpenTelemetry GenAI-semantic-convention spans and metrics for every
agent invocation, model inference call, and tool call — token usage
(gen_ai.client.token.usage), inference/tool call counts and durations
(gen_ai.invoke_agent.*, gen_ai.execute_tool.duration), all tagged by agent/model. This
module just points those at Grafana Cloud's OTLP endpoint (the same stack the Stage
Simulator pushes stage telemetry to) and adds the few BrainBar-specific metrics ADK
has no concept of: which model tier the Supervisor routed to and why, and total
per-take verdict latency (spans three separate agent invocations, so it isn't any
single ADK span).

Call `init_observability()` once at process start, before running any agent.
"""
from __future__ import annotations

import logging

from google.adk.telemetry.setup import OTelHooks, maybe_set_otel_providers
from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from agents.config import config

_log = logging.getLogger(__name__)
_initialized = False


def init_observability() -> None:
    global _initialized
    if _initialized or not config.ai_observability_enabled:
        return
    if not config.otlp_instance_id or not config.otlp_api_key:
        _log.warning(
            "OTLP_INSTANCE_ID/OTLP_API_KEY not set — crew self-observability disabled "
            "until Grafana Cloud credentials are configured."
        )
        return

    headers = config.otlp_headers
    resource = Resource.create({"service.name": "brainbar-crew"})

    maybe_set_otel_providers(
        otel_hooks_to_setup=[
            OTelHooks(
                span_processors=[
                    BatchSpanProcessor(
                        OTLPSpanExporter(endpoint=f"{config.otlp_endpoint}/v1/traces", headers=headers)
                    )
                ],
                metric_readers=[
                    PeriodicExportingMetricReader(
                        OTLPMetricExporter(
                            endpoint=f"{config.otlp_endpoint}/v1/metrics", headers=headers
                        ),
                        export_interval_millis=5000,
                    )
                ],
                log_record_processors=[
                    BatchLogRecordProcessor(
                        OTLPLogExporter(endpoint=f"{config.otlp_endpoint}/v1/logs", headers=headers)
                    )
                ],
            )
        ],
        otel_resource=resource,
    )
    _initialized = True
    _log.info("AI Observability: exporting crew telemetry to %s", config.otlp_endpoint)


_meter = metrics.get_meter("brainbar.crew")

routing_decisions_total = _meter.create_counter(
    "brainbar_crew_routing_decisions_total",
    description="Model-tier routing decisions made by the Supervisor, by agent and tier.",
)

verdict_latency_ms = _meter.create_histogram(
    # Deliberately no unit= — see simulator/telemetry.py for why: Grafana Cloud's
    # OTLP-to-Prometheus translation appends a unit suffix to the metric name when one
    # is set, which would silently break every PromQL query written against this name.
    "brainbar_crew_verdict_latency_ms",
    description="Total wall-clock time from cut to synthesized TakeVerdict.",
)


def record_routing_decision(*, agent: str, tier: str, take_id: str) -> None:
    routing_decisions_total.add(1, {"agent": agent, "tier": tier, "take_id": take_id})


def record_verdict_latency(*, take_id: str, scene: str, setup_id: str, latency_ms: float) -> None:
    verdict_latency_ms.record(latency_ms, {"take_id": take_id, "scene": scene, "setup_id": setup_id})
