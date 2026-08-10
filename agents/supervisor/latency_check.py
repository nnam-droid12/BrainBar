"""The self-governing loop: before routing a take, the Supervisor checks its own
recent verdict latency — read back through the Grafana MCP server from the same
Grafana Cloud stack agents/observability.py exports crew telemetry to — so it can
stay inside the on-set latency budget instead of routing blind.
"""
from __future__ import annotations

from google.adk.agents import LlmAgent
from pydantic import BaseModel

from agents.config import config
from agents.mcp_client import build_grafana_toolset
from agents.runtime import parse_output, run_single_turn

GRAFANA_TOOL_FILTER = ["query_prometheus", "list_prometheus_metric_names"]

INSTRUCTION = f"""\
You check the crew's own recent performance before the next take rolls. Query the
brainbar_crew_verdict_latency_ms metric (a histogram, labeled by take_id/scene/setup_id)
for the last 10 minutes and compute the p95 (or max, if too few samples for a
percentile) verdict latency in milliseconds. If the metric has no data yet (e.g. this
is the first take of the day), report recent_p95_latency_ms as null and
within_budget as true.

The on-set verdict latency budget is {config.verdict_latency_budget_seconds * 1000:.0f}ms.
Set within_budget to true if the recent p95/max is at or under that budget.

Report the required structured LatencyCheck.
"""


class LatencyCheck(BaseModel):
    recent_p95_latency_ms: float | None
    within_budget: bool
    note: str


def build_agent() -> LlmAgent:
    return LlmAgent(
        name="latency_check",
        model=config.gemini_flash_model,
        description="Checks the crew's recent self-observability latency before routing the next take.",
        instruction=INSTRUCTION,
        tools=[build_grafana_toolset(tool_filter=GRAFANA_TOOL_FILTER)],
        output_schema=LatencyCheck,
        output_key="latency_check",
    )


async def check_recent_latency() -> LatencyCheck:
    agent = build_agent()
    raw_text, _tool_calls = await run_single_turn(
        agent, "Check recent verdict latency against budget.", app_name="brainbar-latency-check"
    )
    return parse_output(LatencyCheck, raw_text)
