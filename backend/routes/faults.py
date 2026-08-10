"""Demo control: arm a specific stage fault on the next take, proxied to the Simulator."""
from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.config import config

router = APIRouter(prefix="/faults", tags=["faults"])


class ArmFaultRequest(BaseModel):
    fault_type: str  # vram_spike | node_death | genlock_drift | tracking_jitter | thermal_throttle
    node: str | None = None


@router.post("/next")
async def arm_next_fault(req: ArmFaultRequest) -> dict:
    url = f"{config.simulator_base_url}/control/faults/next"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, json=req.model_dump())
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"simulator unreachable: {exc}")


@router.post("/clear")
async def clear_fault() -> dict:
    url = f"{config.simulator_base_url}/control/faults/clear"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"simulator unreachable: {exc}")
