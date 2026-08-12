# Architecture

BrainBar is four platform boundaries wired into one closed loop: a simulated LED-volume
stage, Grafana Cloud, Google Cloud (Gemini Enterprise Agent Platform), and a
presentation layer (FastAPI backend + React cockpit).

## 1. Simulated LED-Volume Stage (`simulator/`)

A 6-node nDisplay render cluster (`node-1`…`node-6`), camera tracking, a genlock/
timecode reference, and a fault injector (`simulator/faults.py`) that can inject a VRAM
spike, node death, genlock drift, tracking jitter, or thermal throttle on the next take.
Every frame of every take, the simulator pushes real OTLP telemetry to Grafana Cloud —
this is the only part of the system that's simulated; the data it produces is real. See
[telemetry-schema.md](telemetry-schema.md) for the exact metric/log/span names.

On slate and cut, the simulator also posts directly to the backend's
`/internal/simulator-events` webhook so the crew can react within seconds rather than
polling Grafana for state changes.

## 2. Grafana Cloud

- **Mimir** (metrics), **Loki** (logs), **Tempo** (traces) — ingest the simulator's OTLP
  push, and are queried back by the Technical Director and Continuity.
- **Stage Health** and **Crew Health** dashboards — provisioned as code
  (`simulator/grafana_provisioning/`), showing stage telemetry and the crew's own
  Gemini/MCP call latency and token cost respectively.
- **Alert rules + Incidents (IRM)** — three alert rules (node offline, sustained VRAM,
  genlock drift) provisioned as code; the First AD opens/drives/resolves incidents and
  silences alert storms through MCP when they fire.
- **Grafana MCP server** (`grafana/mcp-grafana`, deployed as its own Cloud Run service,
  IAM-protected) — the single connection point every agent's Grafana tool call goes
  through (`agents/mcp_client.py`). ADK discovers the live tool set from the server at
  runtime; nothing is hardcoded.
- **AI Observability** (`agents/observability.py`) — every Gemini call and MCP tool call
  the crew makes is itself exported as OTLP metrics into the same Grafana Cloud stack.

## 3. Google Cloud / Gemini Enterprise Agent Platform (`agents/`)

Five ADK agents, each a typed contract in `agents/schemas.py` in, structured verdict out:

- **Supervisor** (`agents/supervisor/`) — synthesizes the Technical Director's and
  Continuity's verdicts into the circle-take call (circle / hold / reshoot /
  fixable-in-post), reads Memory Bank for cross-take continuity, and self-governs model
  routing by reading the crew's own recent verdict latency back through the Grafana MCP
  server before each take (`agents/supervisor/latency_check.py` +
  `agents/supervisor/routing.py`) — downgrading Pro→Flash on non-fault takes when
  running behind budget. Deployed to **Agent Engine** as the hosted, independently
  queryable root agent (`deploy/agent-engine/`); the production take pipeline also
  invokes the same agent object directly in-process for on-set latency.
- **Continuity** (`agents/continuity/`) — grounded via **RAG Engine + Vector Search** on
  the script, shot list, storyboards, and call sheet, parsed through **Document AI**
  first (`agents/continuity/documentai_client.py`); reads Loki slate/cut events via MCP
  to align takes to setups.
- **Technical Director** (`agents/technical_director/`) — the heaviest Grafana user:
  Prometheus/Mimir, Loki, and Tempo queries via MCP to diagnose a take's telemetry and
  correlate a metric spike to the trace span and log event that explain it.
- **First AD** (`agents/first_ad/`) — converts verdicts into action: pre-stages the
  corrective take via the mock stage-control API, opens/drives Grafana incidents,
  silences alerts, and annotates the Stage Health dashboard, all via MCP.
- **DIT** (`agents/dit/`) — compiles technical dailies with a Grafana deep-link per
  shot, uploads to **Cloud Storage**, writes a row to **BigQuery**, and produces the
  end-of-day report.

All five agents run on **Gemini Pro** or **Gemini Flash** (`agents/config.py` pins the
exact model IDs in one place), routed per-take by the Supervisor.

## 4. Presentation (`backend/` + `frontend/`)

FastAPI backend (`backend/`) orchestrates the crew on every cut event
(`agents/supervisor/orchestrate.py`), exposes REST reads for page reload, drives the
mock stage-control plane the First AD calls, and streams every event live over
WebSocket (`backend/websocket_manager.py`). The React cockpit (`frontend/`) is a light
marketing landing page routing into a dark control-room dashboard with two live views:
the Production Wall (verdict card, take timeline, coverage map, incident banner, demo
controls, embedded Stage Health panel) and the Crew Wall (verdict latency vs. budget,
model routing per take with the Supervisor's reason, embedded Crew Health panel).

## The closed loop

Two loops run through the same Grafana Cloud stack:

1. **The crew watching the shoot** — Stage → OTLP → Mimir/Loki/Tempo → Grafana MCP →
   Technical Director/Continuity → Supervisor verdict → First AD action → back to the
   stage (pre-staged corrective take) and to Grafana (incident/annotation).
2. **The crew watching itself** — every Gemini/MCP call → AI Observability OTLP → Mimir
   → Grafana MCP → Supervisor's routing self-check → the next take's model tier.

## Deployment topology

All services run on Cloud Run except the Supervisor's Agent Engine deployment:

| Service | Cloud Run | Notes |
|---|---|---|
| `brainbar-simulator` | ✓ | `--no-cpu-throttling` (background take-processing thread needs CPU outside request handling) |
| `brainbar-backend` | ✓ | CORS-enabled for the cross-origin frontend; orchestrates the crew in-process |
| `brainbar-frontend` | ✓ | Static Vite build served by nginx, SPA fallback for client-side routing |
| `brainbar-grafana-mcp` | ✓ | IAM-protected (not public); callers authenticate with a Google ID token |
| Supervisor (Agent Engine) | — | `deploy/agent-engine/deploy.py`; independently queryable hosted deployment of the same root agent |

See [telemetry-schema.md](telemetry-schema.md) for the metric/log/trace field
reference.
