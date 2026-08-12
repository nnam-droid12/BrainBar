"""BrainBar backend: orchestrates the crew on every cut event, exposes REST reads for
frontend reload, drives the mock stage-control plane, and streams everything live over
WebSocket.
"""
from __future__ import annotations

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.routes import faults, internal, shoot, stage, takes, telemetry
from backend.websocket_manager import manager

app = FastAPI(title="BrainBar Backend")

# The frontend is deployed on its own Cloud Run origin (a different hostname from the
# backend), so browser fetch() calls to REST routes need explicit CORS — without this
# the WebSocket stream still connects (browsers don't apply CORS to WebSockets), but
# every REST call the cockpit makes (state hydration on load, demo controls) is
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
