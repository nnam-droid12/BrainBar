"""Starts/stops the shoot by driving the Simulator. Take lifecycle itself (slate/cut)
is event-driven — see backend/routes/internal.py, which the Simulator posts to.
"""
from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.config import config as agents_config
from agents.dit.compile import compile_dailies
from agents.schemas import ModelTier
from agents.supervisor.end_of_day import generate_report
from backend.config import config
from backend.state import state
from backend.websocket_manager import manager

router = APIRouter(prefix="/shoot", tags=["shoot"])


class StartShootRequest(BaseModel):
    setup_id: str


@router.post("/start")
async def start_shoot(req: StartShootRequest) -> dict:
    url = f"{config.simulator_base_url}/control/take/start"
    try:
        # Generous timeout: the simulator's Cloud Run instance may need a cold start
        # (min-instances=0 by default) before it can accept the request.
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, json={"setup_id": req.setup_id})
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"simulator unreachable: {exc}")


@router.post("/stop")
async def stop_shoot() -> dict:
    url = f"{config.simulator_base_url}/control/take/stop"
    try:
        # Generous timeout: the simulator's Cloud Run instance may need a cold start
        # (min-instances=0 by default) before it can accept the request.
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"simulator unreachable: {exc}")


@router.post("/wrap")
async def wrap_shoot() -> dict:
    """At wrap: compile technical dailies and write the plain-English end-of-day
    report. Requires at least one take with a synthesized verdict."""
    records = [r for r in state.takes.values() if r.verdict is not None]
    if not records:
        raise HTTPException(400, "no completed takes to wrap")

    verdicts = [r.verdict for r in records]
    takes = [
        {
            "take_id": r.take_id,
            "start_timecode": r.start_timecode,
            "end_timecode": r.end_timecode,
            "start_time_utc": r.start_time_utc,
            "end_time_utc": r.end_time_utc,
        }
        for r in records
    ]
    dailies = await compile_dailies(
        scene=state.scene, verdicts=verdicts, takes=takes, model_tier=ModelTier.FLASH
    )
    state.set_dailies(dailies)

    report_tier = ModelTier.FLASH if agents_config.force_flash_only else ModelTier.PRO
    report = await generate_report(verdicts, dailies, model_tier=report_tier)

    payload = {"dailies": dailies.model_dump(mode="json"), "report": report}
    await manager.broadcast("wrap", payload)
    return payload


@router.get("/status")
async def shoot_status() -> dict:
    url = f"{config.simulator_base_url}/control/status"
    try:
        # Generous timeout: the simulator's Cloud Run instance may need a cold start
        # (min-instances=0 by default) before it can accept the request.
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"simulator unreachable: {exc}")
