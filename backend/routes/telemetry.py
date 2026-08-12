"""Native chart data for the cockpit — real Mimir queries, no iframe.

Grafana Cloud blocks iframe embedding of authenticated dashboards by design (no
allow_embedding on Cloud stacks), so the cockpit renders its own charts from the same
underlying data instead of embedding Grafana's UI.
"""
from __future__ import annotations

from fastapi import APIRouter

from backend.grafana_query import query_instant

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.get("/stage")
async def stage_telemetry() -> dict:
    frame_time = await query_instant("brainbar_render_frame_time_ms")
    vram = await query_instant("brainbar_node_vram_percent")
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
        "sum by (gen_ai_agent_name, gen_ai_token_type) (gen_ai_client_token_usage_sum)"
    )
    tool_calls = await query_instant(
        'topk(8, sum by (gen_ai_tool_name) '
        '(gen_ai_execute_tool_duration_seconds_count{gen_ai_tool_type="MCPTool"}))'
    )

    by_agent: dict[str, dict[str, float]] = {}
    for r in tokens:
        agent = r["metric"].get("gen_ai_agent_name", "?")
        token_type = r["metric"].get("gen_ai_token_type", "?")
        by_agent.setdefault(agent, {"input": 0.0, "output": 0.0})[token_type] = float(r["value"][1])

    return {
        "tokens_by_agent": [
            {"agent": agent, "input": v.get("input", 0.0), "output": v.get("output", 0.0)}
            for agent, v in by_agent.items()
        ],
        "mcp_tool_calls": sorted(
            (
                {"tool": r["metric"].get("gen_ai_tool_name", "?"), "count": float(r["value"][1])}
                for r in tool_calls
            ),
            key=lambda x: -x["count"],
        ),
    }
