"""High-level entrypoint: check one take's creative intent and return a CreativeVerdict."""
from __future__ import annotations

from agents.continuity.agent import build_agent
from agents.runtime import parse_output, run_single_turn
from agents.schemas import CreativeVerdict, ModelTier


async def analyze_take(
    *,
    take_id: str,
    scene: str,
    setup_id: str,
    start_timecode: str,
    end_timecode: str,
    start_time_utc: str,
    end_time_utc: str,
    model_tier: ModelTier = ModelTier.FLASH,
) -> CreativeVerdict:
    agent = build_agent(model_tier)
    prompt = (
        f"Take {take_id} just cut. Scene {scene}, setup {setup_id}, "
        f"timecode {start_timecode} to {end_timecode} "
        f"(real time: {start_time_utc} to {end_time_utc} — use these as the actual "
        f"query bounds if you query Loki). "
        "Retrieve this setup's intended framing/lens/movement/coverage from the "
        "production documents and report a CreativeVerdict."
    )
    raw_text, _tool_calls = await run_single_turn(
        agent,
        prompt,
        app_name="brainbar-continuity",
        conversation_id=take_id,
        conversation_title=f"{take_id} — Continuity",
    )
    return parse_output(CreativeVerdict, raw_text)
