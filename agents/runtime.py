"""Shared ADK Runner boilerplate: every agent module runs a single-turn request
through this helper and gets back the structured Pydantic object it declared as its
`output_schema`. Centralized so the Runner/session wiring is written once.
"""
from __future__ import annotations

import uuid
from typing import TypeVar

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from google.genai.errors import ClientError
from pydantic import BaseModel
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from agents.observability import init_observability

init_observability()

_session_service = InMemorySessionService()

T = TypeVar("T", bound=BaseModel)


def _is_transient(exc: BaseException) -> bool:
    # 429 RESOURCE_EXHAUSTED (quota) and 5xx are worth retrying; 400s are not.
    return isinstance(exc, ClientError) and (
        exc.code == 429 or (exc.code is not None and exc.code >= 500)
    )


@retry(
    retry=retry_if_exception(_is_transient),
    stop=stop_after_attempt(8),
    wait=wait_exponential(multiplier=2, min=2, max=60),
    reraise=True,
)
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

    Each call gets a fresh session by default (a new uuid) — callers doing many
    independent per-take analyses should never share a session_id, or each new take's
    prompt gets appended to the prior take's conversation history instead of starting
    clean. Pass an explicit session_id only when multi-turn continuity is intended.
    """
    session_id = session_id or f"{app_name}-{uuid.uuid4().hex}"
    await _session_service.create_session(app_name=app_name, user_id=user_id, session_id=session_id)

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
