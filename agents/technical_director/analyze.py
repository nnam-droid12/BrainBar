"""High-level entrypoint: analyze one take's telemetry and return a TechnicalVerdict."""
from __future__ import annotations

from agents.runtime import parse_output, run_single_turn
from agents.schemas import ModelTier, TechnicalVerdict
from agents.technical_director.agent import build_agent


async def analyze_take(
    *,
    take_id: str,
    scene: str,
    setup_id: str,
    start_timecode: str,
    end_timecode: str,
    start_time_utc: str,
    end_time_utc: str,
    node_ids: list[str],
    model_tier: ModelTier = ModelTier.FLASH,
) -> TechnicalVerdict:
    agent = build_agent(model_tier)
    prompt = (
        f"Analyze take {take_id} (scene {scene}, setup {setup_id}). "
        f"Take window: timecode {start_timecode} to {end_timecode} "
        f"(real time: {start_time_utc} to {end_time_utc} — use these as the actual "
        f"start/end bounds for every Grafana time-range query; the timecodes are only "
        f"for correlating with slate/cut/cue log lines). "
        f"Active render nodes: {', '.join(node_ids)}. "
        "Query Grafana for this take's telemetry and report a TechnicalVerdict."
    )
    raw_text, _tool_calls = await run_single_turn(
        agent,
        prompt,
        app_name="brainbar-technical-director",
        conversation_id=take_id,
        conversation_title=f"{take_id} — Technical Director",
    )
    verdict = parse_output(TechnicalVerdict, raw_text)
    return verdict.model_copy(update={"model_tier_used": model_tier})
