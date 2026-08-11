"""High-level entrypoint: compile a scene's technical dailies and persist them."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from agents.dit.agent import build_agent
from agents.dit.bigquery_sink import insert_take_row
from agents.dit.storage_client import upload_dailies_json
from agents.runtime import parse_output, run_single_turn
from agents.schemas import DailiesPackage, ModelTier, TakeVerdict

_log = logging.getLogger(__name__)


async def compile_dailies(
    *,
    scene: str,
    verdicts: list[TakeVerdict],
    takes: list[dict],  # [{take_id, start_timecode, end_timecode}, ...] aligned to verdicts
    model_tier: ModelTier = ModelTier.FLASH,
) -> DailiesPackage:
    agent = build_agent(model_tier)
    verdict_lines = "\n".join(
        f"- {v.take_id}: verdict={v.verdict.value}, setup={v.setup_id}, "
        f"headline={v.headline!r}, timecode={t['start_timecode']}-{t['end_timecode']}, "
        f"real_time={t['start_time_utc']} to {t['end_time_utc']} (use this as the "
        "deep-link's actual time range)"
        for v, t in zip(verdicts, takes)
    )
    prompt = f"Scene {scene} wrapped. Takes this scene:\n{verdict_lines}\n\nCompile the DailiesPackage."
    raw_text, _tool_calls = await run_single_turn(agent, prompt, app_name="brainbar-dit")
    package = parse_output(DailiesPackage, raw_text)

    # The model has no reliable access to wall-clock time — set it here, not in the prompt.
    generated_at = datetime.now(timezone.utc).isoformat()
    package = package.model_copy(update={"generated_at": generated_at})

    gcs_uri = upload_dailies_json(scene, package.generated_at, package.model_dump(mode="json"))
    package = package.model_copy(update={"gcs_uri": gcs_uri})

    shots_by_take = {shot.take_id: shot for shot in package.shots}
    for verdict in verdicts:
        shot = shots_by_take.get(verdict.take_id)
        try:
            insert_take_row(
                verdict, package.generated_at, shot.grafana_deeplink if shot else None
            )
        except Exception:
            _log.exception("BigQuery insert failed for %s (non-fatal)", verdict.take_id)

    return package
