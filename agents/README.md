# Agents

The five-agent ADK crew: one root Supervisor and four sub-agents, each an
`google.adk.agents.LlmAgent` with a Pydantic `output_schema` (`agents/schemas.py`) so
every result is structured, not free-text.

| Agent | Model | Role |
|---|---|---|
| `supervisor/` | Gemini Pro | Synthesizes Continuity + Technical Director into the circle-take call; owns Memory Bank, routing, and the end-of-day report |
| `continuity/` | Gemini Flash | Grounds each take against the script/shot-list/storyboard (RAG Engine, Document AI) and tracks coverage |
| `technical_director/` | Flash (Pro for hero/fault takes) | Diagnoses take telemetry via Grafana MCP (Mimir/Loki/Tempo) |
| `first_ad/` | Flash | Converts verdicts into action: pre-stage a retake, open/resolve Grafana incidents, silence alerts, annotate dashboards |
| `dit/` | Flash | Compiles technical dailies with Grafana deep-links, writes to Cloud Storage + BigQuery |

## Shared infrastructure

- `config.py` — every Gemini model ID, GCP resource, and Grafana endpoint, read once from environment.
- `schemas.py` — the Pydantic contracts every agent returns (`TechnicalVerdict`, `CreativeVerdict`, `TakeVerdict`, `ActionLog`, `DailiesPackage`).
- `mcp_client.py` — the one place the Grafana MCP `McpToolset` connection is built; every agent's Grafana tool access goes through this.
- `runtime.py` — shared ADK `Runner`/session boilerplate (`run_single_turn`), with retry-with-backoff for transient 429/5xx errors.
- `observability.py` — Grafana AI Observability instrumentation (OpenTelemetry) for the crew's own Gemini/MCP call latency, cost, and tool activity.

## Run locally

```bash
cd BrainBar
python -m venv .venv
.venv/Scripts/activate
pip install -r agents/requirements.txt
cp .env.example .env
gcloud auth application-default login
gcloud config set project <your-project>
```

A Grafana MCP server must be reachable at `GRAFANA_MCP_URL` — see
`scripts/run_grafana_mcp_oss.md`. Each agent has an `analyze.py` (or `act.py`/
`compile.py`) entrypoint that can be called directly for testing, e.g.:

```python
from agents.technical_director.analyze import analyze_take
from agents.schemas import ModelTier

verdict = await analyze_take(
    take_id="sc03-setup1-take1", scene="SC03", setup_id="1",
    start_timecode="00:00:00:00", end_timecode="00:00:12:12",
    node_ids=["node-1", "node-2", "node-3", "node-4", "node-5", "node-6"],
    model_tier=ModelTier.FLASH,
)
```

The full per-take pipeline (what the backend calls on every cut event) is
`agents.supervisor.orchestrate.handle_cut`.

## One-time setup

- `python -m agents.continuity.rag_setup` — provisions the RAG Engine corpus and
  ingests the production assets (parsing PDFs through Document AI first).
- Deploy Agent Engine (`deploy/agent-engine/`) and set `MEMORY_BANK_AGENT_ENGINE_ID`
  to enable persistent Memory Bank — until then, `agents/supervisor/memory.py` falls
  back to an in-memory service so everything else still works locally.

## Notes from live verification

- Gemini model IDs are pinned in `config.py` after live-verifying availability
  against this project (`scripts/list_vertex_models.md`) — don't trust a model ID
  from documentation alone, Vertex AI's allowlist varies per project/region.
- RAG Engine's default (Spanner-backed) mode is allowlist-only in `us-central1` for
  new projects; the corpus lives in `europe-west4` instead (`agents/config.py`'s
  `rag_corpus_location`) while Gemini calls stay in `google_cloud_location`.
- Don't mix ADK's native `VertexAiRagRetrieval` tool with function-declared MCP tools
  on the same agent — the SDK flags it as AFC-incompatible and it was intermittently
  rejected outright by the API. `continuity/agent.py` uses a plain function-tool
  wrapper around `rag.retrieval_query` instead.
- `runtime.run_single_turn` gives every call a fresh session by default — never pass
  a shared `session_id` across independent per-take analyses, or each new prompt gets
  appended to the previous take's conversation history.
