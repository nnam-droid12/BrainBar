"""Shared ADK Runner boilerplate: every agent module runs a single-turn request
through this helper and gets back the structured Pydantic object it declared as its
`output_schema`. Centralized so the Runner/session wiring is written once.
"""
from __future__ import annotations

from typing import TypeVar

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import BaseModel

_session_service = InMemorySessionService()

T = TypeVar("T", bound=BaseModel)


async def run_single_turn(
    agent: LlmAgent,
    prompt: str,
    *,
    app_name: str,
    user_id: str = "brainbar-crew",
    session_id: str | None = None,
) -> tuple[str, object]:
    """Runs one user turn against `agent` and returns (raw_text, event_stream_summary).

    Every BrainBar agent sets `output_schema`, so ADK enforces structure on the final
    model turn while still letting the agent call Grafana MCP tools freely along the
    way (see llm_agent.py: "output_schema and tools together ... enforcing structure
    only on the final output"). The caller parses `raw_text` with the same Pydantic
    model it passed as `output_schema`.
    """
    session_id = session_id or f"{app_name}-session"
    session = await _session_service.get_session(
        app_name=app_name, user_id=user_id, session_id=session_id
    )
    if session is None:
        await _session_service.create_session(
            app_name=app_name, user_id=user_id, session_id=session_id
        )

    runner = Runner(app_name=app_name, agent=agent, session_service=_session_service)

    final_text = ""
    tool_calls: list[str] = []
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=types.UserContent(parts=[types.Part(text=prompt)]),
    ):
        if event.get_function_calls():
            tool_calls.extend(call.name for call in event.get_function_calls())
        if event.is_final_response() and event.content and event.content.parts:
            text = "".join(p.text for p in event.content.parts if p.text and not p.thought)
            if text.strip():
                final_text = text

    return final_text, tool_calls


def parse_output(schema: type[T], raw_text: str) -> T:
    return schema.model_validate_json(raw_text)
