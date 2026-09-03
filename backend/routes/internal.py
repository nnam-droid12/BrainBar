"""Receives slate/cut/node_down events pushed live from the Stage Simulator
(simulator/emitter.py's `_notify_backend`, configured via BACKEND_WEBHOOK_URL) and
drives the agent crew: on `cut`, run the full per-take pipeline and broadcast the
result to every connected frontend.
"""
from __future__ import annotations

import asyncio
import base64
import csv
import logging
from pathlib import Path

from fastapi import APIRouter

from agents.first_ad.act import act
from agents.narration import synthesize_verdict_audio
from agents.sigil_client import rate_take_conversation
from agents.supervisor.orchestrate import handle_cut
from backend.state import state
from backend.websocket_manager import manager

router = APIRouter(prefix="/internal", tags=["internal"])
_log = logging.getLogger(__name__)

NODE_IDS = [f"node-{i}" for i in range(1, 7)]

_SHOT_LIST_PATH = Path(__file__).resolve().parent.parent.parent / "assets" / "shot-list" / "shot_list.csv"


def _load_coverage_types() -> dict[str, str]:
    with open(_SHOT_LIST_PATH, newline="", encoding="utf-8") as f:
        return {row["setup_id"]: row["coverage_type"] for row in csv.DictReader(f)}


_COVERAGE_TYPES = _load_coverage_types()

# Tracks per-take runtime facts the webhook events reveal incrementally.
_fault_armed_by_take: dict[str, str | None] = {}
_node_down_by_take: dict[str, str | None] = {}

# Keeps strong references to in-flight background pipeline tasks so they aren't
# garbage-collected mid-run (see asyncio docs on create_task); pruned on completion.
_background_tasks: set[asyncio.Task] = set()


@router.post("/grafana-webhook")
async def grafana_webhook(payload: dict) -> dict:
    """Receives Grafana alert-rule webhook notifications (see
    simulator/grafana_provisioning/alert_rules.py's CONTACT_POINT). Broadcast as-is;
    the First AD agent is the one that actually acts on alerts via the MCP server."""
    await manager.broadcast("grafana_alert", {"payload": payload})
    return {"status": "received"}


@router.post("/simulator-events")
async def simulator_event(payload: dict) -> dict:
    event = payload.get("event")
    if event == "slate":
        await _on_slate(payload)
    elif event == "cut":
        # Fire-and-forget: _on_cut runs the full multi-agent pipeline (multiple
        # Gemini calls, can take well over a minute). Awaiting it here would block
        # this HTTP response until the pipeline finished, which the Simulator's
        # webhook caller has no reason to wait on and no timeout budget for — it
        # only needs an ack that the event was received. Task runs on the same
        # event loop, so in-memory state and WebSocket broadcasts stay consistent.
        task = asyncio.create_task(_run_cut_pipeline(payload))
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
    elif event == "node_down":
        await _on_node_down(payload)
    else:
        _log.warning("unknown simulator event: %s", event)
    return {"status": "ok"}


async def _run_cut_pipeline(payload: dict) -> None:
    take_id = payload.get("take_id", "")
    try:
        await _on_cut(payload)
    except Exception as exc:
        _log.exception("cut pipeline failed for take_id=%s", take_id)
        # Without this the take sits at rolling=false/verdict=None forever — the
        # frontend has no way to tell "still analyzing" from "will never finish"
        # (this happens for real: sustained Vertex AI 429s can exhaust every retry).
        message = f"{type(exc).__name__}: {exc}"[:300]
        state.set_error(take_id, message)
        await manager.broadcast("verdict_error", {"take_id": take_id, "error": message})
        rate_take_conversation(take_id=take_id, success=False, comment=message)


async def _on_slate(payload: dict) -> None:
    take_id = payload["take_id"]
    state.start_take(take_id, payload["scene"], payload["setup"], payload["take"])
    _fault_armed_by_take[take_id] = payload.get("fault_armed")
    _node_down_by_take[take_id] = None
    await manager.broadcast("slate", payload)


async def _on_node_down(payload: dict) -> None:
    take_id = payload["take_id"]
    _node_down_by_take[take_id] = payload["node"]
    state.active_incident = {"node": payload["node"], "take_id": take_id, "status": "detected"}
    await manager.broadcast("node_down", payload)


async def _on_cut(payload: dict) -> None:
    take_id = payload["take_id"]
    scene = payload["scene"]
    setup_id = payload["setup"]
    take_number = payload["take"]
    start_timecode = payload["start_timecode"]
    end_timecode = payload["end_timecode"]
    start_time_utc = payload["start_time_utc"]
    end_time_utc = payload["end_time_utc"]

    fault_active = bool(_fault_armed_by_take.get(take_id))
    node_down = _node_down_by_take.get(take_id)
    coverage_type = _COVERAGE_TYPES.get(str(setup_id), "single")

    await manager.broadcast("cut", payload)

    verdict, routing = await handle_cut(
        take_id=take_id,
        scene=scene,
        setup_id=str(setup_id),
        take_number=take_number,
        start_timecode=start_timecode,
        end_timecode=end_timecode,
        start_time_utc=start_time_utc,
        end_time_utc=end_time_utc,
        node_ids=NODE_IDS,
        coverage_type=coverage_type,
        fault_active=fault_active,
    )
    state.set_verdict(
        take_id,
        verdict,
        start_timecode=start_timecode,
        end_timecode=end_timecode,
        start_time_utc=start_time_utc,
        end_time_utc=end_time_utc,
    )
    state.set_routing(take_id, routing)
    await manager.broadcast("verdict", {"take_id": take_id, "verdict": verdict.model_dump(mode="json")})
    await manager.broadcast(
        "routing_decision", {"take_id": take_id, "routing": routing.model_dump(mode="json")}
    )

    # Fire-and-forget: spoken narration is a demo enhancement layered on top of a
    # verdict that has already landed, not something the pipeline should ever wait on
    # or fail over. Runs concurrently with the First AD's action-taking below.
    narration_task = asyncio.create_task(_narrate_verdict(take_id, verdict.headline))
    _background_tasks.add(narration_task)
    narration_task.add_done_callback(_background_tasks.discard)

    action_log = await act(
        verdict=verdict,
        start_timecode=start_timecode,
        end_timecode=end_timecode,
        start_time_utc=start_time_utc,
        end_time_utc=end_time_utc,
        node_ids=NODE_IDS,
        node_down=node_down,
    )
    state.set_action_log(take_id, action_log)
    if node_down:
        state.active_incident = {
            "node": node_down,
            "take_id": take_id,
            "status": "handled",
            "actions": [a.model_dump(mode="json") for a in action_log.actions],
        }
    await manager.broadcast(
        "action_log", {"take_id": take_id, "action_log": action_log.model_dump(mode="json")}
    )
    rate_take_conversation(
        take_id=take_id, success=True, comment="Pipeline completed: verdict synthesized, actions taken."
    )


async def _narrate_verdict(take_id: str, headline: str) -> None:
    audio = await synthesize_verdict_audio(headline)
    if audio is None:
        return
    await manager.broadcast(
        "verdict_audio",
        {
            "take_id": take_id,
            "audio_base64": base64.b64encode(audio).decode("ascii"),
            "mime_type": "audio/wav",
        },
    )
