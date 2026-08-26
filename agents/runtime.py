"""Shared ADK Runner boilerplate: every agent module runs a single-turn request
through this helper and gets back the structured Pydantic object it declared as its
`output_schema`. Centralized so the Runner/session wiring is written once.
"""
from __future__ import annotations

import uuid
from typing import TypeVar

import re

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from google.genai.errors import ClientError
from pydantic import BaseModel
from tenacity import RetryCallState, retry, retry_if_exception, stop_after_attempt, wait_exponential

from agents.observability import (
    init_observability,
    record_hallucinated_tool_call,
    record_model_call_error,
)

init_observability()

_session_service = InMemorySessionService()

T = TypeVar("T", bound=BaseModel)


def _is_transient(exc: BaseException) -> bool:
    # 429 RESOURCE_EXHAUSTED (quota) and 5xx are worth retrying; 400s are not.
    return isinstance(exc, ClientError) and (
        exc.code == 429 or (exc.code is not None and exc.code >= 500)
    )


def _record_transient_error(retry_state: RetryCallState) -> None:
    """tenacity before_sleep hook: fires once per retried (transient) attempt, so this
    is the live signal agents/supervisor/quota_check.py reads back through Grafana MCP
    to detect Pro-tier quota exhaustion before routing another take to Pro — instead of
    only finding out from the manual force_flash_only override in agents/config.py.
    """
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    if exc is None:
        return
    agent = retry_state.args[0] if retry_state.args else None
    model = agent.model if isinstance(getattr(agent, "model", None), str) else "unknown"
    code = getattr(exc, "code", None)
    record_model_call_error(model=model, code=code)


# ADK's own error text (google/adk/flows/llm_flows/functions.py:_get_tool) when the model
# calls a tool name outside its declared tool list — literally includes "hallucinated" in
# the message. Matching on this exact, ADK-internal string (not a guess) is what lets
# run_single_turn tell a real hallucinated tool call apart from any other ValueError an
# agent or tool might raise.
_HALLUCINATED_TOOL_RE = re.compile(r"Tool '([^']+)' not found\.\nAvailable tools:")


@retry(
    retry=retry_if_exception(_is_transient),
    stop=stop_after_attempt(8),
    wait=wait_exponential(multiplier=2, min=2, max=60),
    before_sleep=_record_transient_error,
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
    try:
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
    except ValueError as exc:
        match = _HALLUCINATED_TOOL_RE.search(str(exc))
        if match:
            record_hallucinated_tool_call(agent=agent.name, attempted_tool=match.group(1))
        raise

    return final_text, tool_calls


def parse_output(schema: type[T], raw_text: str) -> T:
    return schema.model_validate_json(raw_text)
