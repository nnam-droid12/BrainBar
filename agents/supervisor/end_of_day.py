"""At wrap: a plain-English end-of-day report — the Supervisor's closing summary,
including the six-figure reshoot that never happened.
"""
from __future__ import annotations

from google.adk.agents import LlmAgent

from agents.config import config
from agents.runtime import run_single_turn
from agents.schemas import DailiesPackage, ModelTier, TakeVerdict

INSTRUCTION = """\
You are the Supervisor of an autonomous virtual-production crew, writing the
end-of-day report for the humans running the stage. You will be given every take
verdict from today and the compiled dailies package.

Write a short, plain-English report (5-8 sentences, no headers, no bullet points) a
producer could read in thirty seconds: how many takes were circled clean, how many
were held or reshot and why (cite the real technical/creative reasons), what coverage
is still owed, and — if any take was headed for a problem that would only have been
caught in the 4K deliverable weeks later — say plainly what that would have cost in
reshoot time and stage-day rate, and that it didn't happen because of what the crew
caught tonight. Be concrete, not generic; use the real verdict headlines you were
given, not placeholder language.
"""


def build_agent(model_tier: ModelTier = ModelTier.PRO) -> LlmAgent:
    model = config.gemini_pro_model if model_tier == ModelTier.PRO else config.gemini_flash_model
    return LlmAgent(
        name="end_of_day_report",
        model=model,
        description="Writes the Supervisor's plain-English end-of-day report.",
        instruction=INSTRUCTION,
    )


async def generate_report(
    verdicts: list[TakeVerdict], dailies: DailiesPackage | None, model_tier: ModelTier = ModelTier.PRO
) -> str:
    agent = build_agent(model_tier)
    verdict_lines = "\n".join(
        f"- {v.take_id}: {v.verdict.value} — {v.headline}" for v in verdicts
    )
    coverage_owed = verdicts[-1].creative.coverage_owed if verdicts else []
    coverage_line = (
        f"Coverage still owed at wrap: {', '.join(coverage_owed)}"
        if coverage_owed
        else "All required coverage was captured."
    )
    dailies_line = (
        f"Dailies package: {len(dailies.shots)} shots, {dailies.gcs_uri}"
        if dailies
        else "Dailies not yet compiled."
    )
    prompt = (
        f"Today's takes:\n{verdict_lines}\n\n{coverage_line}\n{dailies_line}\n\n"
        "Write the end-of-day report."
    )
    raw_text, _tool_calls = await run_single_turn(agent, prompt, app_name="brainbar-end-of-day")
    return raw_text
