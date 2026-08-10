"""Mock stage-control plane. The First AD agent (agents/first_ad/stage_control_client.py)
calls these over HTTP to pre-stage a corrective take. Every call defensively clears any
armed/active fault on the Simulator so the next take actually comes back clean —
this is what makes "pre-staging worked" visibly true in the demo rather than a no-op.
"""
from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from backend.config import config
from backend.websocket_manager import manager

router = APIRouter(prefix="/stage", tags=["stage-control"])
_log = logging.getLogger(__name__)


class LoadshedRequest(BaseModel):
    node_id: str
    reason: str = ""


class DrainRequest(BaseModel):
    reason: str = ""


class AffinityRequest(BaseModel):
    node_id: str
    target_nodes: list[str]
    reason: str = ""


async def _clear_simulator_fault() -> dict:
    url = f"{config.simulator_base_url}/control/faults/clear"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as exc:
        return {"status": "error", "detail": f"simulator unreachable at {url}: {exc}"}


@router.post("/loadshed")
async def loadshed(req: LoadshedRequest) -> dict:
    sim_result = await _clear_simulator_fault()
    result = {
        "status": "ok",
        "action": "loadshed",
        "node_id": req.node_id,
        "reason": req.reason,
        "detail": f"Render load shed off {req.node_id}; armed fault cleared for next take.",
        "simulator_response": sim_result,
    }
    await manager.broadcast("stage_action", result)
    return result


@router.post("/node/{node_id}/drain")
async def drain_node(node_id: str, req: DrainRequest) -> dict:
    sim_result = await _clear_simulator_fault()
    result = {
        "status": "ok",
        "action": "drain",
        "node_id": node_id,
        "reason": req.reason,
        "detail": f"{node_id} draining; render affinity steered to healthy nodes.",
        "simulator_response": sim_result,
    }
    await manager.broadcast("stage_action", result)
    return result


@router.post("/affinity")
async def set_affinity(req: AffinityRequest) -> dict:
    sim_result = await _clear_simulator_fault()
    result = {
        "status": "ok",
        "action": "affinity",
        "node_id": req.node_id,
        "target_nodes": req.target_nodes,
        "reason": req.reason,
        "detail": f"Render affinity for {req.node_id} steered to {', '.join(req.target_nodes)}.",
        "simulator_response": sim_result,
    }
    await manager.broadcast("stage_action", result)
    return result
