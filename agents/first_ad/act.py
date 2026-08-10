"""High-level entrypoint: turn a TakeVerdict into real actions and return the ActionLog."""
from __future__ import annotations

from agents.first_ad.agent import build_agent
from agents.runtime import parse_output, run_single_turn
from agents.schemas import ActionLog, ModelTier, TakeVerdict


async def act(
    *,
    verdict: TakeVerdict,
    start_timecode: str,
    end_timecode: str,
    node_down: str | None = None,
    model_tier: ModelTier = ModelTier.FLASH,
) -> ActionLog:
    agent = build_agent(model_tier)
    prompt = (
        f"Take {verdict.take_id} (scene {verdict.scene}, setup {verdict.setup_id}, "
        f"take {verdict.take_number}), timecode {start_timecode} to {end_timecode}.\n\n"
        f"Verdict: {verdict.verdict.value}\n"
        f"Headline: {verdict.headline}\n"
        f"Reasoning: {verdict.reasoning}\n"
        f"recommend_reshoot: {verdict.recommend_reshoot}\n"
        f"node_down: {node_down or 'none'}\n\n"
        "Take the appropriate actions and report the ActionLog."
    )
    raw_text, _tool_calls = await run_single_turn(agent, prompt, app_name="brainbar-first-ad")
    action_log = parse_output(ActionLog, raw_text)
    return action_log.model_copy(update={"take_id": verdict.take_id})
