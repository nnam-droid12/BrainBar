"""Read endpoints backing the frontend's reload-on-refresh state (everything shown
live over the WebSocket is also available here for a fresh page load)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.state import state

router = APIRouter(tags=["takes"])


@router.get("/take/{take_id}/verdict")
async def get_take_verdict(take_id: str) -> dict:
    record = state.takes.get(take_id)
    if record is None:
        raise HTTPException(404, f"unknown take_id {take_id}")
    return {
        "take_id": record.take_id,
        "verdict": record.verdict.model_dump(mode="json") if record.verdict else None,
        "action_log": record.action_log.model_dump(mode="json") if record.action_log else None,
        "rolling": record.rolling,
    }


@router.get("/coverage")
async def get_coverage() -> dict:
    return {"coverage_owed": state.coverage_owed}


@router.get("/dailies")
async def get_dailies() -> dict:
    if state.dailies is None:
        raise HTTPException(404, "dailies not compiled yet — call at wrap")
    return state.dailies.model_dump(mode="json")


@router.get("/state")
async def get_full_state() -> dict:
    return state.to_dict()
