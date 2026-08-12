"""Continuity: knows what each setup was *supposed* to be and tracks what's captured.

Grounded via Vertex AI RAG Engine on the script, shot list, storyboards, and call
sheet (agents/continuity/rag_setup.py ingests them, parsing the PDFs through Document
AI first). Reads Loki slate/cut events through the Grafana MCP server to map take IDs
to shot-list setups by timecode.
"""
from __future__ import annotations

import asyncio

import vertexai
from google.adk.agents import LlmAgent
from vertexai import rag

from agents.config import config
from agents.continuity.rag_setup import ensure_corpus
from agents.mcp_client import build_grafana_toolset
from agents.schemas import CreativeVerdict, ModelTier

# ADK's native VertexAiRagRetrieval tool asks Gemini 2+ models to use RAG as a
# built-in "retrieval" tool alongside our function-declared Grafana MCP tools. That
# mix is flagged by the SDK itself as incompatible with automatic function calling
# and was intermittently rejected outright by the API (400 INVALID_ARGUMENT) when
# both were attached to the same agent. A plain function tool wrapping
# rag.retrieval_query keeps every tool on the same function-calling path — still a
# real RAG Engine call, just not the native-tool shortcut.
def _make_retrieval_tool(corpus_name: str):
    vertexai.init(project=config.google_cloud_project, location=config.rag_corpus_location)

    async def retrieve_production_documents(query: str) -> list[str]:
        """Retrieves relevant passages from the script, shot list, storyboards, and
        call sheet for the given query (e.g. "setup 1 intended framing and lens")."""
        response = await asyncio.to_thread(
            rag.retrieval_query,
            text=query,
            rag_resources=[rag.RagResource(rag_corpus=corpus_name)],
            rag_retrieval_config=rag.RagRetrievalConfig(top_k=5),
        )
        return [context.text for context in response.contexts.contexts]

    return retrieve_production_documents


GRAFANA_TOOL_FILTER = [
    "query_loki_logs",
    "list_loki_label_names",
    "list_loki_label_values",
    "query_loki_patterns",
]

INSTRUCTION = """\
You are Continuity on an LED-volume virtual-production stage. You know what every
setup in today's scene was written and storyboarded to be, and you track what
coverage has actually been captured across takes.

You have a retrieval tool grounded on today's production documents: the script, the
shot list (setup id, intended lens, movement, framing, coverage type), storyboard
frame descriptions, and the call sheet. Always retrieve before answering — do not rely
on memory of a prior turn for setup details.

You will be given a take_id, scene, setup_id, its start/end timecode, and its real
start/end time (RFC3339). If useful, query Loki for the stage event log
(event_type=slate or event_type=cut, labeled by take_id) to confirm the take's actual
timecode window and to see whether a cue (dolly/pyro/lighting) fired as scripted. If
you do query Loki: call list_datasources first and use the loki-type datasource's exact
uid (never rely on default-datasource resolution — it lacks permission and will 403),
and always pass the take's real start/end time as explicit query time bounds.

Workflow:
1. Retrieve the shot-list entry and storyboard description for this setup_id — that is
   the intended framing, lens, movement, and coverage_type.
2. Compare intended vs what you know was captured this take (from the take metadata
   you're given and, if you queried it, the stage event log).
3. Decide `matches_intent`: true only if framing/movement/coverage type are consistent
   with what was scripted for this setup.
4. Track `coverage_owed`: consult the shot list for every setup in this scene and note
   coverage types not yet captured across the takes you know about this session.
5. Flag continuity issues (lens/cadence mismatch with an established master, a cue that
   didn't fire, missing required coverage) with a severity of info, warning, or
   critical.
6. Write a one-paragraph `summary` covering intent match and anything still owed.

Report your findings as the required structured CreativeVerdict.
"""


def build_agent(model_tier: ModelTier, corpus_name: str | None = None) -> LlmAgent:
    model = config.gemini_pro_model if model_tier == ModelTier.PRO else config.gemini_flash_model
    corpus_name = corpus_name or ensure_corpus()
    return LlmAgent(
        name="continuity",
        model=model,
        description="Grounds each take against the script/shot-list/storyboard and tracks coverage.",
        instruction=INSTRUCTION,
        tools=[
            _make_retrieval_tool(corpus_name),
            build_grafana_toolset(tool_filter=GRAFANA_TOOL_FILTER),
        ],
        output_schema=CreativeVerdict,
        output_key="creative_verdict",
    )
