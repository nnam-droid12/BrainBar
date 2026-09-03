"""Memory Bank: carries continuity and recurring-technical-problem notes across takes
and shooting days.

Requires a deployed Agent Engine resource (see deploy/agent-engine/, Milestone 14) to
back Vertex AI Memory Bank. Until MEMORY_BANK_AGENT_ENGINE_ID is set, falls back to
ADK's in-memory service so the Supervisor's synthesis logic is fully testable locally
before that deployment exists — the fallback is functionally real (writes/searches
really happen), just not persisted across process restarts.
"""
from __future__ import annotations

import logging
import uuid

from google.adk.events.event import Event
from google.adk.memory import InMemoryMemoryService
from google.adk.memory.base_memory_service import BaseMemoryService
from google.adk.sessions.session import Session
from google.genai import types

from agents.config import config

_log = logging.getLogger(__name__)

APP_NAME = "brainbar-crew"
USER_ID = "brainbar-stage"  # one shared production "user" — memory scopes per show, not per person

_service: BaseMemoryService | None = None


def get_memory_service() -> BaseMemoryService:
    global _service
    if _service is not None:
        return _service

    if config.memory_bank_agent_engine_id:
        from google.adk.memory import VertexAiMemoryBankService

        _service = VertexAiMemoryBankService(
            project=config.google_cloud_project,
            location=config.google_cloud_location,
            agent_engine_id=config.memory_bank_agent_engine_id,
        )
        _log.info("Memory Bank: using Vertex AI Agent Engine %s", config.memory_bank_agent_engine_id)
    else:
        _service = InMemoryMemoryService()
        _log.warning(
            "MEMORY_BANK_AGENT_ENGINE_ID not set — using in-memory fallback "
            "(not persisted across restarts). Deploy Agent Engine to enable real Memory Bank."
        )
    return _service


async def record_note(
    *, scene: str, setup_id: str, take_id: str, note: str, category: str
) -> None:
    """Writes one continuity/technical fact to memory, e.g. "coverage owed" or a
    recurring node problem ("node-6 has spiked VRAM on 2 of the last 3 pyro cues").

    Uses add_session_to_memory with a single synthetic event rather than the
    Memory-Bank-specific add_memory, so the same call works against both the real
    Vertex AI Memory Bank and the local InMemoryMemoryService fallback.
    """
    tagged_note = f"[{scene}/setup{setup_id}/{take_id}/{category}] {note}"
    service = get_memory_service()
    session_id = f"note-{uuid.uuid4().hex}"
    session = Session(
        id=session_id,
        app_name=APP_NAME,
        user_id=USER_ID,
        events=[
            Event(
                invocation_id=session_id,
                author="supervisor",
                content=types.Content(role="model", parts=[types.Part(text=tagged_note)]),
            )
        ],
    )
    await service.add_session_to_memory(session)


async def recall_notes(query: str) -> list[str]:
    """Returns prior notes relevant to `query` (e.g. "node-6 VRAM problems" or "SC03 coverage")."""
    # A blank/whitespace query reaches here when the model calls this tool without a
    # specific angle in mind. Memory Bank's own backend rejects an empty search_query
    # with a raw 400 INVALID_ARGUMENT that nothing upstream catches — confirmed live,
    # this killed the whole take's Supervisor synthesis. Guard it here rather than
    # ever sending Vertex AI a blank query.
    if not query or not query.strip():
        return [
            "recall_notes was called with no query — retry with a specific search "
            "string, e.g. a node id, scene/setup, or the kind of problem you're "
            "checking for."
        ]
    service = get_memory_service()
    response = await service.search_memory(app_name=APP_NAME, user_id=USER_ID, query=query)
    notes: list[str] = []
    for memory in response.memories:
        for part in memory.content.parts or []:
            if part.text:
                notes.append(part.text)
    return notes
