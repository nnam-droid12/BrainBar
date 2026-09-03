"""Shared ADK Runner boilerplate: every agent module runs a single-turn request
through this helper and gets back the structured Pydantic object it declared as its
`output_schema`. Centralized so the Runner/session wiring is written once — including
the Sigil (Agent Observability) generation/tool-call wrapping, so no individual agent
file needs to touch it.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import TypeVar

from google.adk.agents import LlmAgent
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types
from google.genai.errors import ClientError
from pydantic import BaseModel
from tenacity import RetryCallState, retry, retry_if_exception, stop_after_attempt, wait_exponential

from agents.observability import (
    init_observability,
    record_hallucinated_tool_call,
    record_model_call_error,
)
from agents.profiling import init_profiling
from agents.sigil_client import get_sigil_client

init_observability()
# Must run after init_observability(): it attaches a span processor to the global
# TracerProvider that call already installed (see agents/profiling.py's docstring).
init_profiling()

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


def _model_name(agent: LlmAgent) -> str:
    model = getattr(agent, "model", None)
    return model if isinstance(model, str) else "unknown"


class _SigilToolPlugin(BasePlugin):
    """Wraps every tool call this agent makes this turn — Grafana MCP tools and plain
    Python function tools alike — with a Sigil ToolExecutionRecorder, so Grafana Cloud's
    Tools tab shows input/output/duration per call, linked to the same conversation_id
    as the generation that made it (feature: bidirectional tool-call <-> conversation
    drill-down). Built fresh per run_single_turn call, so conversation_id/agent_name are
    just constructor state, not something threaded through every ADK callback signature.
    """

    def __init__(self, *, client, conversation_id: str, agent_name: str, model: str) -> None:
        super().__init__(name="sigil_tool_plugin")
        self._client = client
        self._conversation_id = conversation_id
        self._agent_name = agent_name
        self._model = model
        # Keyed by tool_context identity — ADK passes the same ToolContext object
        # through before/after/error for one tool call, and a fresh one per call, so
        # this is a safe-enough correlation key without threading extra ids around.
        self._active: dict[int, tuple[object, dict]] = {}

    async def before_tool_callback(
        self, *, tool: BaseTool, tool_args: dict, tool_context: ToolContext
    ) -> dict | None:
        from sigil_sdk import ToolExecutionStart

        rec = self._client.start_tool_execution(
            ToolExecutionStart(
                tool_name=tool.name,
                conversation_id=self._conversation_id,
                agent_name=self._agent_name,
                request_model=self._model,
                request_provider="google",
                include_content=True,
            )
        )
        self._active[id(tool_context)] = (rec, tool_args)
        return None

    async def after_tool_callback(
        self, *, tool: BaseTool, tool_args: dict, tool_context: ToolContext, result: dict
    ) -> dict | None:
        from sigil_sdk import ToolExecutionEnd

        entry = self._active.pop(id(tool_context), None)
        if entry is None:
            return None
        rec, args = entry
        rec.set_result(ToolExecutionEnd(arguments=args, result=result))
        return None

    async def on_tool_error_callback(
        self, *, tool: BaseTool, tool_args: dict, tool_context: ToolContext, error: Exception
    ) -> dict | None:
        entry = self._active.pop(id(tool_context), None)
        if entry is not None:
            rec, _args = entry
            rec.set_exec_error(error)
        return None


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
    conversation_id: str | None = None,
    conversation_title: str = "",
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

    `conversation_id` groups this call with every other agent's call for the same take
    in Sigil (Agent Observability) — pass the take_id where one exists. Defaults to
    session_id, which is unique per call and so keeps every call its own conversation
    (correct for callers with no natural take_id, e.g. the end-of-day report).
    """
    session_id = session_id or f"{app_name}-{uuid.uuid4().hex}"
    await _session_service.create_session(app_name=app_name, user_id=user_id, session_id=session_id)

    conv_id = conversation_id or session_id
    model = _model_name(agent)
    sigil_client = get_sigil_client()

    plugins = []
    if sigil_client is not None:
        plugins.append(
            _SigilToolPlugin(client=sigil_client, conversation_id=conv_id, agent_name=agent.name, model=model)
        )

    runner = Runner(app_name=app_name, agent=agent, session_service=_session_service, plugins=plugins)

    sigil_gen = None
    if sigil_client is not None:
        from sigil_sdk import GenerationStart, ModelRef

        sigil_gen = sigil_client.start_streaming_generation(
            GenerationStart(
                conversation_id=conv_id,
                conversation_title=conversation_title,
                user_id=user_id,
                agent_name=agent.name,
                model=ModelRef(provider="google", name=model),
                system_prompt=getattr(agent, "instruction", "") or "",
            )
        )

    final_text = ""
    tool_calls: list[str] = []
    first_token_recorded = False
    try:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=types.UserContent(parts=[types.Part(text=prompt)]),
        ):
            if sigil_gen is not None and not first_token_recorded:
                has_text = bool(
                    event.content and event.content.parts and any(p.text for p in event.content.parts)
                )
                if has_text:
                    sigil_gen.set_first_token_at(datetime.now(timezone.utc))
                    first_token_recorded = True
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
        if sigil_gen is not None:
            sigil_gen.set_call_error(exc)
        raise
    except Exception as exc:
        if sigil_gen is not None:
            sigil_gen.set_call_error(exc)
        raise
    else:
        if sigil_gen is not None:
            sigil_gen.set_result()

    return final_text, tool_calls


def parse_output(schema: type[T], raw_text: str) -> T:
    return schema.model_validate_json(raw_text)
