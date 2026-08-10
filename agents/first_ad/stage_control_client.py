"""Thin client for the backend's mock stage-control plane (backend/routes/stage.py,
Milestone 12). Real HTTP calls — they simply have nothing to talk to until the
backend is running, at which point pre-staging visibly closes the loop: a load-shed
or affinity change here changes what the Simulator does on the next take.
"""
from __future__ import annotations

import httpx

from agents.config import config


async def loadshed(node_id: str, reason: str) -> dict:
    return await _post("/stage/loadshed", {"node_id": node_id, "reason": reason})


async def drain_node(node_id: str, reason: str) -> dict:
    return await _post(f"/stage/node/{node_id}/drain", {"reason": reason})


async def set_affinity(node_id: str, target_nodes: list[str], reason: str) -> dict:
    return await _post(
        "/stage/affinity",
        {"node_id": node_id, "target_nodes": target_nodes, "reason": reason},
    )


async def _post(path: str, payload: dict) -> dict:
    url = f"{config.backend_base_url}{path}"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as exc:
        return {"status": "error", "detail": f"backend unreachable at {url}: {exc}"}
