"""High-level entrypoint: analyze one take's telemetry and return a TechnicalVerdict."""
from __future__ import annotations

from agents.runtime import parse_output, run_single_turn
from agents.schemas import ModelTier, TechnicalVerdict
from agents.technical_director.agent import build_agent


def _validate_evidence_grounding(verdict: TechnicalVerdict) -> TechnicalVerdict:
    """Cheap, deterministic gate every model tier is forced through after parsing —
    the code-level counterpart to the Grafana Agent Observability LLM-judge rubric
    (brainbar.td_evidence_grounding), but with no extra model call, so a Flash
    fallback under Pro quota pressure can't quietly ship a less-scrutinized verdict
    than Pro would have. Same function, same bar, regardless of which tier ran —
    called unconditionally here rather than duplicated per call site, so there's no
    second copy of the check to forget to update.

    Checks the *structured* TechnicalIssue fields the schema already requires are
    real values, not just present-but-empty: a verdict that says clean=false but
    reports an issue with a blank node/metric or a one-word root_cause is exactly the
    "conclusion not backed by data" failure mode the online evaluator grades for —
    caught here for free, before the take ever reaches a human or a dashboard.
    """
    if verdict.clean:
        return verdict.model_copy(update={"evidence_validated": True})

    if not verdict.issues:
        return verdict.model_copy(
            update={
                "evidence_validated": False,
                "evidence_validation_note": (
                    "clean=false but no issues were reported — a not-clean verdict "
                    "needs at least one cited issue."
                ),
            }
        )

    hollow = [
        issue
        for issue in verdict.issues
        if not issue.node.strip()
        or not issue.metric.strip()
        or len(issue.root_cause.strip()) < 10
        or len(issue.description.strip()) < 10
    ]
    if hollow:
        return verdict.model_copy(
            update={
                "evidence_validated": False,
                "evidence_validation_note": (
                    f"{len(hollow)} of {len(verdict.issues)} issue(s) are missing a "
                    "real node/metric or a substantive root_cause/description — "
                    "evidence isn't fully grounded."
                ),
            }
        )

    return verdict.model_copy(update={"evidence_validated": True})


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
    verdict = verdict.model_copy(update={"model_tier_used": model_tier})
    return _validate_evidence_grounding(verdict)
