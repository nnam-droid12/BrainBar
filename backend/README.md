# Backend

FastAPI orchestration layer. Listens for slate/cut/node_down events pushed live from
the Stage Simulator, drives the five-agent crew on every cut, exposes REST reads for
the frontend, and streams every event live over WebSocket.

## Run locally

```bash
cd BrainBar
python -m venv .venv
.venv/Scripts/activate        # .venv/bin/activate on macOS/Linux
pip install -r backend/requirements.txt -r agents/requirements.txt
cp .env.example .env           # fill in GCP + Grafana config
python -m backend.run          # serves on :8080
```

Requires the Stage Simulator running (`simulator/README.md`) with
`BACKEND_WEBHOOK_URL=http://localhost:8080/internal/simulator-events` set, and a
Grafana MCP server reachable at `GRAFANA_MCP_URL` (`scripts/run_grafana_mcp_oss.md`).

## Endpoints

| Endpoint | Purpose |
|---|---|
| `POST /shoot/start {setup_id}` | Proxies to the Simulator to roll a take |
| `POST /shoot/stop` | Cuts the current take early |
| `POST /shoot/wrap` | Compiles dailies (DIT) and the end-of-day report (Supervisor) |
| `GET /shoot/status` | Simulator's current take/fault status |
| `GET /take/{id}/verdict` | A take's verdict + action log |
| `GET /coverage` | Coverage owed per scene |
| `GET /dailies` | The compiled dailies package (after wrap) |
| `GET /state` | Full shoot state (for a fresh page load) |
| `POST /stage/loadshed`, `/stage/node/{id}/drain`, `/stage/affinity` | Mock stage-control plane the First AD calls |
| `POST /faults/next`, `/faults/clear` | Demo control — arm/clear a Simulator fault |
| `POST /internal/simulator-events` | Simulator → backend event webhook (slate/cut/node_down) |
| `POST /internal/grafana-webhook` | Grafana alert-rule notification receiver |
| `WS /stream` | Live event feed: slate, cut, verdict, action_log, stage_action, wrap |

## How a take flows through the system

1. Simulator posts `slate` to `/internal/simulator-events` → backend starts tracking the take, broadcasts `slate`.
2. Simulator posts `cut` → backend broadcasts `cut`, then calls `agents.supervisor.orchestrate.handle_cut`
   (Continuity + Technical Director in parallel, then Supervisor synthesis) and broadcasts `verdict`.
3. Backend calls `agents.first_ad.act.act` with the verdict → broadcasts `action_log`.
4. At wrap, `agents.dit.compile.compile_dailies` and `agents.supervisor.end_of_day.generate_report`
   run, and the backend broadcasts `wrap`.

Every step is a real Gemini/Grafana MCP call — see `agents/README.md`.
