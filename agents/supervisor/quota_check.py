"""The self-governing loop, extended to quota: before routing a take to Pro, the
Supervisor checks whether Pro has been throwing 429s recently — read back through the
Grafana MCP server from the brainbar_crew_model_call_errors_total counter
agents/runtime.py records on every transient Gemini call error. This is what lets the
crew notice Pro-tier quota exhaustion (and recovery) live, instead of only through the
manual force_flash_only override in agents/config.py (see agents/supervisor/routing.py).
"""
from __future__ import annotations

from google.adk.agents import LlmAgent
from pydantic import BaseModel

from agents.config import config
from agents.mcp_client import build_grafana_toolset
from agents.runtime import parse_output, run_single_turn

GRAFANA_TOOL_FILTER = ["query_prometheus", "list_prometheus_metric_names"]

INSTRUCTION = f"""\
You check whether the crew has hit Gemini Pro quota errors recently, before routing
another take to Pro. Query the brainbar_crew_model_call_errors_total metric (a counter,
labeled by model and code) for the last 10 minutes, summed where model="{config.gemini_pro_model}"
and code="429". If the metric has no data yet (e.g. no Pro call has ever errored), report
recent_429_count as 0 and quota_healthy as true.

Set quota_healthy to false if recent_429_count is 1 or more — on this project's Dynamic
Shared Quota, a single 429 means the quota is currently exhausted and the next Pro call
is very likely to fail the same way, not a fluke worth risking on set.

Report the required structured QuotaCheck.
"""


class QuotaCheck(BaseModel):
    recent_429_count: int
    quota_healthy: bool
    note: str


def build_agent() -> LlmAgent:
    return LlmAgent(
        name="quota_check",
        model=config.gemini_flash_model,
        description="Checks the crew's recent Pro-tier quota-error telemetry before routing to Pro.",
        instruction=INSTRUCTION,
        tools=[build_grafana_toolset(tool_filter=GRAFANA_TOOL_FILTER)],
        output_schema=QuotaCheck,
        output_key="quota_check",
    )


async def check_recent_pro_quota() -> QuotaCheck:
    agent = build_agent()
    raw_text, _tool_calls = await run_single_turn(
        agent, "Check recent Pro-tier quota errors before routing.", app_name="brainbar-quota-check"
    )
    return parse_output(QuotaCheck, raw_text)
