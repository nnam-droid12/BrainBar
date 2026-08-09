"""Demo control plane for the Stage Simulator.

Lets the backend (or a human on a laptop just off stage) drive the shoot and arm faults
on cue, so the 3-minute demo is reproducible: trigger fault X, then roll the next take.
"""
from __future__ import annotations

import threading

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from simulator.config import config
from simulator.faults import FaultInjector, FaultType
from simulator.models import load_shoot_script
from simulator.emitter import TakeRunner
from simulator.telemetry import telemetry

app = FastAPI(title="BrainBar Stage Simulator Control API")

shoot = load_shoot_script(config.shoot_script_path)
faults = FaultInjector()
runner = TakeRunner(telemetry, faults, shoot)


class StartTakeRequest(BaseModel):
    setup_id: str


class ArmFaultRequest(BaseModel):
    fault_type: FaultType
    node: str | None = None


@app.get("/control/shoot")
def get_shoot() -> dict:
    return {
        "scene": shoot.scene,
        "scene_title": shoot.scene_title,
        "setups": [s.id for s in shoot.setups],
    }


@app.get("/control/status")
def get_status() -> dict:
    take = runner.current_take
    return {
        "take": None
        if take is None
        else {
            "take_id": take.take_id,
            "scene": take.scene,
            "setup_id": take.setup_id,
            "take_number": take.take_number,
            "frame_number": take.frame_number,
            "rolling": take.rolling,
        },
        "armed_fault": faults.armed_fault,
        "active_fault": faults.active_fault,
        "active_fault_node": faults.active_node,
    }


@app.post("/control/take/start")
def start_take(req: StartTakeRequest) -> dict:
    if runner.current_take is not None and runner.current_take.rolling:
        raise HTTPException(409, "a take is already rolling")
    try:
        shoot.setup(req.setup_id)
    except KeyError:
        raise HTTPException(404, f"unknown setup_id {req.setup_id}")
    thread = threading.Thread(target=runner.run_take, args=(req.setup_id,), daemon=True)
    thread.start()
    return {"status": "rolling", "setup_id": req.setup_id}


@app.post("/control/take/stop")
def stop_take() -> dict:
    runner.abort()
    return {"status": "cut"}


@app.post("/control/faults/next")
def arm_fault(req: ArmFaultRequest) -> dict:
    faults.arm(req.fault_type, req.node)
    return {"status": "armed", "fault_type": req.fault_type, "node": req.node}


@app.post("/control/faults/clear")
def clear_fault() -> dict:
    faults.arm(None)
    return {"status": "cleared"}
