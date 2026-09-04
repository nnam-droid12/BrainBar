"""High-level entrypoints: turn a hardware failure or a TakeVerdict into real actions.

Two entrypoints, matching the two modes agents/first_ad/agent.py's INSTRUCTION
describes. react_to_hardware_failure fires the instant a node goes down — concurrently
with the crew's slower creative/technical analysis of the take, not sequenced behind
it, so a dead render node gets drained and paged before a verdict exists, not after.
act() still runs at verdict time for everything else, and is told (via
already_handled_node) what react_to_hardware_failure already did, so it never repeats
an incident/alert/page/drain for the same node in the same take.
"""
from __future__ import annotations

from agents.first_ad.agent import build_agent
from agents.runtime import parse_output, run_single_turn
from agents.schemas import ActionLog, ModelTier, TakeVerdict


async def react_to_hardware_failure(
    *,
    take_id: str,
    scene: str,
    setup_id: str,
    node: str,
    node_ids: list[str],
    model_tier: ModelTier = ModelTier.FLASH,
) -> ActionLog:
    agent = build_agent(model_tier)
    prompt = (
        f"MODE A — immediate hardware reaction, no verdict yet. Take {take_id} "
        f"(scene {scene}, setup {setup_id}) is still rolling; node {node} just went "
        f"offline mid-take. Active render nodes: {', '.join(node_ids)}.\n\n"
        "React now — do not wait for a verdict. Take the appropriate actions and "
        "report the ActionLog."
    )
    raw_text, _tool_calls = await run_single_turn(
        agent,
        prompt,
        app_name="brainbar-first-ad-hardware",
        conversation_id=take_id,
        conversation_title=f"{take_id} — First AD (hardware reaction)",
    )
    action_log = parse_output(ActionLog, raw_text)
    return action_log.model_copy(update={"take_id": take_id})


async def act(
    *,
    verdict: TakeVerdict,
    start_timecode: str,
    end_timecode: str,
    start_time_utc: str,
    end_time_utc: str,
    node_ids: list[str],
    node_down: str | None = None,
    already_handled_node: str | None = None,
    model_tier: ModelTier = ModelTier.FLASH,
) -> ActionLog:
    agent = build_agent(model_tier)
    prompt = (
        f"MODE B — verdict-time. Take {verdict.take_id} (scene {verdict.scene}, "
        f"setup {verdict.setup_id}, take {verdict.take_number}), timecode "
        f"{start_timecode} to {end_timecode} (real time: {start_time_utc} to "
        f"{end_time_utc} — use these as the actual time range for any dashboard "
        f"annotation or deep-link you create).\n\n"
        f"Verdict: {verdict.verdict.value}\n"
        f"Headline: {verdict.headline}\n"
        f"Reasoning: {verdict.reasoning}\n"
        f"recommend_reshoot: {verdict.recommend_reshoot}\n"
        f"node_down: {node_down or 'none'}\n"
        f"already_handled_node: {already_handled_node or 'none'}\n"
        f"Active render nodes this take: {', '.join(node_ids)}\n\n"
        "Take the appropriate actions and report the ActionLog."
    )
    raw_text, _tool_calls = await run_single_turn(
        agent,
        prompt,
        app_name="brainbar-first-ad",
        conversation_id=verdict.take_id,
        conversation_title=f"{verdict.take_id} — First AD",
    )
    action_log = parse_output(ActionLog, raw_text)
    return action_log.model_copy(update={"take_id": verdict.take_id})
