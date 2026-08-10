# BrainBar

**An autonomous multi-agent crew that answers, per take, on an LED-volume stage: did we actually get it — technically and creatively — or do we go again?**

> Status: under active development for the Grafana track of Agentic Cinema: The Blockbuster Hackathon. This README is updated as each milestone lands; see the build-order checklist below for current progress.

## The problem

Modern tent-pole films are shot on LED volumes: a curved wall of LED panels driven by a real-time render cluster, synchronized to the camera via tracking, genlock, and timecode. A render node can drop frames on a hard camera move, genlock can drift, tracking can jitter, or VRAM can spike during an effects cue — and the take looks perfect in the viewfinder while quietly being broken. The damage is discovered weeks later in the 4K deliverable, when reshoots cost six figures. A volume stage costs $200,000–$500,000 per day.

## What BrainBar does

BrainBar is a five-agent crew that fuses a shot's **creative intent** (script, shot list, storyboard, call sheet) with the take's **live technical telemetry** (frame times, sync drift, tracking jitter, GPU/VRAM) flowing into Grafana Cloud during that exact take window, and takes real action: it issues a per-take verdict (circle / hold / reshoot / fixable-in-post), pre-stages the corrective take, opens and drives Grafana incidents when stage hardware fails, silences alert storms, annotates dashboards, and hands editorial a technical-dailies package with a Grafana deep-link for every shot.

BrainBar also watches itself: the crew's own Gemini call latency, token cost, and MCP tool activity flow into the same Grafana Cloud stack it queries, and the Supervisor reads that data back through the Grafana MCP server to stay inside an on-set latency budget and route routine takes to a fast model and hero shots to a stronger one.

## Architecture

See [architecture/architecture.md](architecture/architecture.md) for the full breakdown and [architecture/telemetry-schema.md](architecture/telemetry-schema.md) for every metric/log/trace field.

A generated architecture diagram will be linked here once produced (see `diagram-prompt.md`, generated as the final build step and kept out of the repo).

## Google Cloud — used where

| Service | Where it's called |
|---|---|
| Gemini Enterprise Agent Platform (ADK) | `agents/` — root Supervisor + 4 sub-agents |
| Gemini Pro / Flash | `agents/config.py` model routing; used across all five agents |
| Multimodal vision | `agents/continuity/` (storyboard + proxy-frame reads) |
| RAG Engine / Vector Search | `agents/continuity/grounding.py` |
| Document AI | `agents/continuity/ingest.py` (script/call-sheet parsing) |
| Memory Bank | `agents/supervisor/memory.py` |
| Agent Engine | `deploy/agent-engine/` (hosted crew runtime) |
| Cloud Run | `deploy/cloud-run/` (simulator, backend, frontend, MCP service) |
| Cloud Storage | `agents/dit/` (assets + dailies) |
| BigQuery | `agents/dit/bigquery_sink.py` (per-take dailies rows) |
| Secret Manager | `deploy/` (Grafana token, deployment secrets) |

## Grafana — used where

| Surface | Where it's called |
|---|---|
| Metrics (Mimir/PromQL) | `agents/technical_director/` — frame-time, VRAM, drift, jitter queries via MCP |
| Logs (Loki/LogQL) | `agents/technical_director/`, `agents/continuity/` — slate/cut/warning events via MCP |
| Traces (Tempo) | `agents/technical_director/` — per-frame render pipeline trace lookup via MCP |
| Dashboards | `agents/dit/` — deep-links and panel metadata via MCP |
| Alerting + Incidents (IRM) | `agents/first_ad/` — incident open/annotate/resolve, alert silencing via MCP |
| Annotations | `agents/first_ad/` — per-take verdict annotations via MCP |
| AI Observability | `agents/observability.py` — crew's own Gemini/MCP call telemetry |
| Grafana MCP server | `agents/mcp_client.py` — the single connection point every agent tool call above goes through |

## Repository layout

```
simulator/    Stage Simulator — emits real telemetry to Grafana Cloud (Section 7 of the spec)
agents/       The five-agent ADK crew
backend/      FastAPI orchestration + mock stage-control API
frontend/     React control-room UI (Production Wall + Crew Wall)
assets/       Synthetic script, shot list, storyboards, call sheet
deploy/       Cloud Run + Agent Engine deployment configs
architecture/ Architecture + telemetry schema docs
```

## Local setup

_Filled in as each service lands — see `simulator/README.md`, `agents/README.md`, `backend/README.md`, `frontend/README.md` for per-service instructions once available._

1. Copy `.env.example` to `.env` and fill in your GCP project, Grafana Cloud stack URL, and Grafana service-account token.
2. `gcloud auth application-default login` and `gcloud config set project <your-project>`.
3. See per-service READMEs for install/run commands.

## Hosted deployment

_Hosted Cloud Run + Agent Engine URLs added once Milestone 14 lands._

## Running the demo

_Reproducible demo script added once Milestone 15 lands (see Section 15 of the build spec)._

## License

Apache-2.0, see [LICENSE](LICENSE).
