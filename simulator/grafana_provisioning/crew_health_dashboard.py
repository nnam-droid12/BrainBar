"""Builds the "Crew Health" dashboard JSON — the crew watching itself.

Panels read the AI Observability telemetry agents/observability.py exports: ADK's
built-in GenAI-semconv metrics (token usage, inference/tool-call counts, per-agent
invocation duration) plus BrainBar's own routing-decision and verdict-latency
metrics. Same Grafana Cloud stack and provisioning path as the Stage Health
dashboard (stage_health_dashboard.py) — provisioned by provision.py.
"""
from __future__ import annotations

from simulator.grafana_provisioning.panel_helpers import GridCursor, stat_panel, timeseries_panel

DASHBOARD_UID = "brainbar-crew-health"


def build_dashboard(prom_uid: str, verdict_latency_budget_ms: float = 15000.0) -> dict:
    grid = GridCursor(row_height=8)
    panels = [
        stat_panel(
            "Verdict latency p95 (5m)",
            prom_uid,
            "histogram_quantile(0.95, sum(rate(brainbar_crew_verdict_latency_ms_bucket[5m])) by (le))",
            grid.place(6, 4),
            unit="ms",
            thresholds=[
                {"color": "green", "value": None},
                {"color": "orange", "value": verdict_latency_budget_ms * 0.8},
                {"color": "red", "value": verdict_latency_budget_ms},
            ],
        ),
        stat_panel(
            "Takes routed to Pro (1h)",
            prom_uid,
            'sum(increase(brainbar_crew_routing_decisions_total{tier="pro"}[1h]))',
            grid.place(6, 4),
        ),
        stat_panel(
            "Takes routed to Flash (1h)",
            prom_uid,
            'sum(increase(brainbar_crew_routing_decisions_total{tier="flash"}[1h]))',
            grid.place(6, 4),
        ),
        stat_panel(
            "Tool calls (1h)",
            prom_uid,
            "sum(increase(gen_ai_invoke_agent_tool_calls_count[1h]))",
            grid.place(6, 4),
        ),
        timeseries_panel(
            "Verdict latency per take (ms) vs budget",
            prom_uid,
            [
                (
                    "histogram_quantile(0.95, sum(rate(brainbar_crew_verdict_latency_ms_bucket[5m])) by (le, take_id))",
                    "{{take_id}}",
                ),
                (f"{verdict_latency_budget_ms}", "budget"),
            ],
            grid.place(12),
            unit="ms",
        ),
        timeseries_panel(
            "Model routing decisions by tier",
            prom_uid,
            [("sum by (tier) (rate(brainbar_crew_routing_decisions_total[5m]))", "{{tier}}")],
            grid.place(12),
        ),
        timeseries_panel(
            "GenAI token usage by model (input+output)",
            prom_uid,
            [
                (
                    "sum by (gen_ai_request_model, gen_ai_token_type) (rate(gen_ai_client_token_usage_sum[5m]))",
                    "{{gen_ai_request_model}} / {{gen_ai_token_type}}",
                )
            ],
            grid.place(12),
        ),
        timeseries_panel(
            "Agent invocation duration (p95, by agent)",
            prom_uid,
            [
                (
                    "histogram_quantile(0.95, sum(rate(gen_ai_invoke_agent_duration_bucket[5m])) by (le, gen_ai_agent_name))",
                    "{{gen_ai_agent_name}}",
                )
            ],
            grid.place(12),
            unit="s",
        ),
        timeseries_panel(
            "Tool execution duration (p95, by tool)",
            prom_uid,
            [
                (
                    "histogram_quantile(0.95, sum(rate(gen_ai_execute_tool_duration_bucket[5m])) by (le, gen_ai_tool_name))",
                    "{{gen_ai_tool_name}}",
                )
            ],
            grid.place(12),
            unit="s",
        ),
    ]

    return {
        "uid": DASHBOARD_UID,
        "title": "BrainBar — Crew Health",
        "tags": ["brainbar", "crew", "ai-observability"],
        "timezone": "utc",
        "schemaVersion": 39,
        "version": 1,
        "refresh": "10s",
        "time": {"from": "now-1h", "to": "now"},
        "panels": panels,
    }
