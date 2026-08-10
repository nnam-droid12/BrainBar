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
    node_ids: list[str],
    model_tier: ModelTier = ModelTier.FLASH,
) -> TechnicalVerdict:
    agent = build_agent(model_tier)
    prompt = (
        f"Analyze take {take_id} (scene {scene}, setup {setup_id}). "
        f"Take window: timecode {start_timecode} to {end_timecode}. "
        f"Active render nodes: {', '.join(node_ids)}. "
        "Query Grafana for this take's telemetry and report a TechnicalVerdict."
    )
    raw_text, _tool_calls = await run_single_turn(
        agent, prompt, app_name="brainbar-technical-director"
    )
    verdict = parse_output(TechnicalVerdict, raw_text)
    return verdict.model_copy(update={"model_tier_used": model_tier})
