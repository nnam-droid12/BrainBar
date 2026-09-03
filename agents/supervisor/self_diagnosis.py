"""Closes the crew's self-observability loop one step further: instead of only reading
its own metrics back through Grafana MCP (see latency_check.py, quota_check.py), the
crew asks Grafana Cloud's own AI Assistant to investigate its recent performance and
suggest improvements — the same `ask_assistant` capability a human would use by tagging
@Grafana in Slack, called programmatically at wrap instead of by a person clicking
around a dashboard.

Deliberately observe-and-surface, not observe-and-auto-fix: the Assistant's suggestion
is woven into the end-of-day report (agents/supervisor/end_of_day.py) as a
recommendation for the humans running the stage to act on, not something the crew
silently rewrites its own prompts or config from mid-demo.
"""
from __future__ import annotations

from google.adk.agents import LlmAgent
from pydantic import BaseModel

from agents.config import config
from agents.mcp_client import build_grafana_toolset
from agents.runtime import parse_output, run_single_turn

GRAFANA_TOOL_FILTER = ["ask_assistant"]

INSTRUCTION = """\
Ask Grafana Cloud's own AI Assistant (via the ask_assistant tool) to investigate the
crew's recent performance and suggest concrete improvements. Frame your prompt to it
roughly as: "Investigate the brainbar-crew service's recent Gemini call latency, token
cost, error rate, and tool-call activity in this Grafana Cloud stack, and suggest
specific improvements." Pass its response through in your own summary — don't
editorialize or invent detail beyond what it actually returned.

If the ask_assistant tool call fails, errors, or returns nothing substantive (e.g. no
data yet this early in a session), report investigated as false and leave suggestion
empty — never fabricate a plausible-sounding suggestion when the tool didn't actually
return one.

Report the required structured SelfDiagnosis.
"""


class SelfDiagnosis(BaseModel):
    investigated: bool
    suggestion: str


def build_agent() -> LlmAgent:
    return LlmAgent(
        name="self_diagnosis",
        model=config.gemini_flash_model,
        description="Asks Grafana Cloud's own AI Assistant to investigate the crew's recent performance.",
        instruction=INSTRUCTION,
        tools=[build_grafana_toolset(tool_filter=GRAFANA_TOOL_FILTER)],
        output_schema=SelfDiagnosis,
        output_key="self_diagnosis",
    )


async def investigate() -> SelfDiagnosis:
    agent = build_agent()
    raw_text, _tool_calls = await run_single_turn(
        agent,
        "Investigate the crew's recent performance via Grafana's AI Assistant and report findings.",
        app_name="brainbar-self-diagnosis",
        conversation_id="end-of-day",
        conversation_title="End of day — Grafana Assistant self-diagnosis",
    )
    return parse_output(SelfDiagnosis, raw_text)
