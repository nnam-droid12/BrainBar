"""The per-take pipeline: on `cut`, run Continuity and the Technical Director in
parallel, synthesize the Supervisor's circle-take call, and record anything worth
remembering to Memory Bank. This is what the backend calls on every cut event.
"""
from __future__ import annotations

import asyncio
import time

from agents.continuity.analyze import analyze_take as analyze_creative
from agents.observability import record_verdict_latency
from agents.runtime import parse_output, run_single_turn
from agents.schemas import ModelTier, RoutingDecision, TakeVerdict
from agents.supervisor.agent import build_agent as build_supervisor_agent
from agents.supervisor.memory import record_note
from agents.supervisor.routing import decide_model_tier_observed
from agents.technical_director.analyze import analyze_take as analyze_technical


async def handle_cut(
    *,
    take_id: str,
    scene: str,
    setup_id: str,
    take_number: int,
    start_timecode: str,
    end_timecode: str,
    start_time_utc: str,
    end_time_utc: str,
    node_ids: list[str],
    coverage_type: str,
    fault_active: bool = False,
) -> tuple[TakeVerdict, RoutingDecision]:
    t0 = time.monotonic()

    routing = await decide_model_tier_observed(
        take_id=take_id, coverage_type=coverage_type, fault_active=fault_active
    )

    technical, creative = await asyncio.gather(
        analyze_technical(
            take_id=take_id,
            scene=scene,
            setup_id=setup_id,
            start_timecode=start_timecode,
            end_timecode=end_timecode,
            start_time_utc=start_time_utc,
            end_time_utc=end_time_utc,
            node_ids=node_ids,
            model_tier=routing.tier,
        ),
        analyze_creative(
            take_id=take_id,
            scene=scene,
            setup_id=setup_id,
            start_timecode=start_timecode,
            end_timecode=end_timecode,
            start_time_utc=start_time_utc,
            end_time_utc=end_time_utc,
            model_tier=ModelTier.FLASH,
        ),
    )

    # Mirror the same tier decide_model_tier_observed already made for this take
    # (see agents/supervisor/routing.py) instead of always paying for Pro here — a
    # take that was routed to Flash for its technical diagnosis shouldn't then force
    # a second, separate Pro call just to synthesize the call from already-structured
    # verdicts, which was needlessly doubling this take's Pro-tier load on exactly
    # the hero-coverage/fault takes most likely to already be tight on Pro quota.
    supervisor = build_supervisor_agent(routing.tier)
    prompt = (
        f"Take {take_id} (scene {scene}, setup {setup_id}, take {take_number}) just cut.\n\n"
        f"TechnicalVerdict:\n{technical.model_dump_json(indent=2)}\n\n"
        f"CreativeVerdict:\n{creative.model_dump_json(indent=2)}\n\n"
        "Synthesize the circle-take call."
    )
    raw_text, _tool_calls = await run_single_turn(
        supervisor,
        prompt,
        app_name="brainbar-supervisor",
        conversation_id=take_id,
        conversation_title=f"{take_id} — Supervisor synthesis",
    )
    verdict = parse_output(TakeVerdict, raw_text)

    latency_ms = (time.monotonic() - t0) * 1000
    verdict = verdict.model_copy(
        update={
            "take_id": take_id,
            "scene": scene,
            "setup_id": setup_id,
            "take_number": take_number,
            "technical": technical,
            "creative": creative,
            "latency_ms": latency_ms,
        }
    )

    record_verdict_latency(
        take_id=take_id, scene=scene, setup_id=setup_id, latency_ms=latency_ms
    )
    await _record_memory(verdict)
    return verdict, routing


async def _record_memory(verdict: TakeVerdict) -> None:
    notes: list[tuple[str, str]] = []
    if not verdict.technical.clean:
        notes.append((verdict.headline, "technical"))
    if verdict.creative.coverage_owed:
        notes.append(
            (f"Coverage still owed: {', '.join(verdict.creative.coverage_owed)}", "coverage")
        )
    for note, category in notes:
        await record_note(
            scene=verdict.scene,
            setup_id=verdict.setup_id,
            take_id=verdict.take_id,
            note=note,
            category=category,
        )
