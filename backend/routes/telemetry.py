"""Native chart data for the frontend — real Mimir queries, no iframe.

Grafana Cloud blocks iframe embedding of authenticated dashboards by design (no
allow_embedding on Cloud stacks), so the frontend renders its own charts from the same
underlying data instead of embedding Grafana's UI.
"""
from __future__ import annotations

from fastapi import APIRouter

from agents.pricing import estimate_cost_usd
from backend.grafana_query import query_instant

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


def _scalar(result: list[dict], default: float = 0.0) -> float:
    """A `sum(...)` instant query returns at most one series with no labels — pull its
    value out, or `default` if the underlying metric has no samples yet."""
    if not result:
        return default
    return float(result[0]["value"][1])


@router.get("/stage")
async def stage_telemetry() -> dict:
    # max by (node) — not the bare metric name: brainbar_render_frame_time_ms and
    # brainbar_node_vram_percent both also carry a take_id label, so an unaggregated
    # instant query returns one series per (node, take_id) combination. Once more than
    # one take has recent samples (any session with more than a single take rolled),
    # that's multiple rows sharing the same node — which the frontend keys by node,
    # producing React's "two children with the same key" warning and, worse, silently
    # picking whichever duplicate happens to sort first rather than each node's actual
    # latest value. Confirmed live: this fired on every take past the first one in an
    # actual session. drift below already got this right; frame_time/vram didn't.
    frame_time = await query_instant("max by (node) (brainbar_render_frame_time_ms)")
    vram = await query_instant("max by (node) (brainbar_node_vram_percent)")
    drift = await query_instant("max by (device) (brainbar_genlock_drift_us)")

    return {
        "frame_time_by_node": [
            {"node": r["metric"].get("node", "?"), "ms": float(r["value"][1])} for r in frame_time
        ],
        "vram_by_node": [
            {"node": r["metric"].get("node", "?"), "percent": float(r["value"][1])} for r in vram
        ],
        "genlock_drift_by_device": [
            {"device": r["metric"].get("device", "?"), "us": float(r["value"][1])} for r in drift
        ],
    }


@router.get("/crew")
async def crew_telemetry() -> dict:
    tokens = await query_instant(
        "sum by (gen_ai_agent_name, gen_ai_request_model, gen_ai_token_type) "
        "(gen_ai_client_token_usage_sum)"
    )
    tool_calls = await query_instant(
        'topk(8, sum by (gen_ai_tool_name) '
        '(gen_ai_execute_tool_duration_seconds_count{gen_ai_tool_type="MCPTool"}))'
    )
    hallucinated = await query_instant(
        "sum(increase(brainbar_crew_hallucinated_tool_calls_total[1h]))"
    )
    quota_errors = await query_instant(
        'sum(increase(brainbar_crew_model_call_errors_total{code="429"}[10m]))'
    )

    by_agent: dict[str, dict[str, float]] = {}
    by_agent_model: dict[str, dict[str, dict[str, float]]] = {}
    for r in tokens:
        agent = r["metric"].get("gen_ai_agent_name", "?")
        model = r["metric"].get("gen_ai_request_model", "?")
        token_type = r["metric"].get("gen_ai_token_type", "?")
        value = float(r["value"][1])
        by_agent.setdefault(agent, {"input": 0.0, "output": 0.0})[token_type] = (
            by_agent[agent].get(token_type, 0.0) + value
        )
        by_agent_model.setdefault(agent, {}).setdefault(model, {"input": 0.0, "output": 0.0})[
            token_type
        ] = value

    cost_by_agent = {
        agent: sum(
            estimate_cost_usd(model, input_tokens=v.get("input", 0.0), output_tokens=v.get("output", 0.0))
            for model, v in models.items()
        )
        for agent, models in by_agent_model.items()
    }

    return {
        "tokens_by_agent": [
            {"agent": agent, "input": v.get("input", 0.0), "output": v.get("output", 0.0)}
            for agent, v in by_agent.items()
        ],
        "cost_usd_by_agent": [
            {"agent": agent, "cost_usd": cost} for agent, cost in cost_by_agent.items()
        ],
        "cost_usd_total": sum(cost_by_agent.values()),
        "mcp_tool_calls": sorted(
            (
                {"tool": r["metric"].get("gen_ai_tool_name", "?"), "count": float(r["value"][1])}
                for r in tool_calls
            ),
            key=lambda x: -x["count"],
        ),
        "hallucinated_tool_calls_1h": int(_scalar(hallucinated)),
        "pro_quota_errors_10m": int(_scalar(quota_errors)),
    }
