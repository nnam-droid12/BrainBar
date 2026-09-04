"""BrainBar backend: orchestrates the crew on every cut event, exposes REST reads for
frontend reload, drives the mock stage-control plane, and streams everything live over
WebSocket.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.routes import faults, internal, shoot, stage, takes, telemetry
from backend.websocket_manager import manager

# Nothing in this codebase ever called logging.basicConfig — every _log.info/.debug
# call across backend/ and agents/ (Sigil's own included) was silently dropped by
# Python's default root-logger level (WARNING), only .exception/.error ever surfaced.
# Confirmed live: a full take produced zero "Sigil:" log lines, success or failure,
# because none of them could print, not because nothing happened.
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
# DEBUG specifically for the modules whose debug-level detail is actually worth
# reading (Sigil's per-call tool/generation tracing) — global DEBUG would drown that
# signal in every dependency's own verbose logging (httpx, grpc, urllib3, ...).
logging.getLogger("agents.runtime").setLevel(logging.DEBUG)
logging.getLogger("agents.sigil_client").setLevel(logging.DEBUG)

app = FastAPI(title="BrainBar Backend")

# The frontend is deployed on its own Cloud Run origin (a different hostname from the
# backend), so browser fetch() calls to REST routes need explicit CORS — without this
# the WebSocket stream still connects (browsers don't apply CORS to WebSockets), but
# every REST call the frontend makes (state hydration on load, demo controls) is
# silently blocked by the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(shoot.router)
app.include_router(takes.router)
app.include_router(stage.router)
app.include_router(faults.router)
app.include_router(internal.router)
app.include_router(telemetry.router)


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}


@app.websocket("/stream")
async def stream(ws: WebSocket) -> None:
    await manager.connect(ws)
    try:
        while True:
            # The frontend is a read-only listener; we just need the recv loop to
            # detect disconnects (ping frames etc. are handled by the websockets library).
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)
