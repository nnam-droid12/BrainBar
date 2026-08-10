"""Receives slate/cut/node_down events pushed live from the Stage Simulator
(simulator/emitter.py's `_notify_backend`, configured via BACKEND_WEBHOOK_URL) and
drives the agent crew: on `cut`, run the full per-take pipeline and broadcast the
result to every connected frontend.
"""
from __future__ import annotations

import csv
import logging
from pathlib import Path

from fastapi import APIRouter

from agents.first_ad.act import act
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
        await _on_cut(payload)
    elif event == "node_down":
        await _on_node_down(payload)
    else:
        _log.warning("unknown simulator event: %s", event)
    return {"status": "ok"}


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
        node_ids=NODE_IDS,
        coverage_type=coverage_type,
        fault_active=fault_active,
    )
    state.set_verdict(take_id, verdict, start_timecode=start_timecode, end_timecode=end_timecode)
    state.set_routing(take_id, routing)
    await manager.broadcast("verdict", {"take_id": take_id, "verdict": verdict.model_dump(mode="json")})
    await manager.broadcast(
        "routing_decision", {"take_id": take_id, "routing": routing.model_dump(mode="json")}
    )

    action_log = await act(
        verdict=verdict,
        start_timecode=start_timecode,
        end_timecode=end_timecode,
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
