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

# USD per token, list price for the Vertex AI <=200k-context tier as of this writing.
# Mirrors agents/pricing.py's table (divided by 1000) — kept as a literal here rather
# than imported so this dashboard-as-code module doesn't cross the simulator/agents
# package boundary (see simulator/config.py's own mirroring of other agents/config.py
# settings). Update both places together if pricing changes.
_PRICE_PER_TOKEN_USD = {
    "pro": {"input": 1.25e-6, "output": 10e-6},
    "flash": {"input": 0.30e-6, "output": 2.5e-6},
}


def _cost_expr(pro_model: str, flash_model: str, rate_fn: str) -> str:
    """rate_fn: a PromQL range-vector function call with the range baked in, e.g.
    'rate(...[5m])' for a $/sec rate or 'increase(...[1h])' for a $ total over 1h."""
    terms = []
    for tier, model in (("pro", pro_model), ("flash", flash_model)):
        price = _PRICE_PER_TOKEN_USD[tier]
        for token_type in ("input", "output"):
            metric = (
                f'gen_ai_client_token_usage_sum{{gen_ai_request_model="{model}", '
                f'gen_ai_token_type="{token_type}"}}'
            )
            expr = rate_fn.replace("...", metric)
            terms.append(f"(sum({expr}) * {price[token_type]})")
    return " + ".join(terms)


def build_dashboard(
    prom_uid: str,
    verdict_latency_budget_ms: float = 15000.0,
    gemini_pro_model: str = "gemini-2.5-pro",
    gemini_flash_model: str = "gemini-2.5-flash",
) -> dict:
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
        stat_panel(
            "Pro-tier quota errors (10m)",
            prom_uid,
            'sum(increase(brainbar_crew_model_call_errors_total{code="429"}[10m]))',
            grid.place(6, 4),
            thresholds=[
                {"color": "green", "value": None},
                {"color": "red", "value": 1},
            ],
        ),
        stat_panel(
            "Hallucinated tool calls (1h)",
            prom_uid,
            "sum(increase(brainbar_crew_hallucinated_tool_calls_total[1h]))",
            grid.place(6, 4),
            thresholds=[
                {"color": "green", "value": None},
                {"color": "red", "value": 1},
            ],
        ),
        timeseries_panel(
            "Model call errors by model and code",
            prom_uid,
            [
                (
                    "sum by (model, code) (rate(brainbar_crew_model_call_errors_total[5m]))",
                    "{{model}} / {{code}}",
                )
            ],
            grid.place(12),
        ),
        timeseries_panel(
            "Hallucinated tool calls by agent",
            prom_uid,
            [
                (
                    "sum by (agent, attempted_tool) (rate(brainbar_crew_hallucinated_tool_calls_total[5m]))",
                    "{{agent}} → {{attempted_tool}}",
                )
            ],
            grid.place(12),
        ),
        stat_panel(
            "Estimated cost, last 1h ($)",
            prom_uid,
            _cost_expr(gemini_pro_model, gemini_flash_model, "increase(...[1h])"),
            grid.place(6, 4),
            unit="currencyUSD",
        ),
        timeseries_panel(
            "Estimated cost rate ($/hour)",
            prom_uid,
            [(f"({_cost_expr(gemini_pro_model, gemini_flash_model, 'rate(...[5m])')}) * 3600", "cost/hr")],
            grid.place(18),
            unit="currencyUSD",
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
