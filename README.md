# BrainBar

**An autonomous multi-agent crew that answers, per take, on an LED-volume stage: did we actually get it — technically and creatively — or do we go again?**

Built for the Grafana track of Agentic Cinema: The Blockbuster Hackathon.

**Live:** [brainbar-frontend-854441956422.us-central1.run.app](https://brainbar-frontend-854441956422.us-central1.run.app)

## The problem

Modern tent-pole films are shot on LED volumes: a curved wall of LED panels driven by a real-time render cluster, synchronized to the camera via tracking, genlock, and timecode. A render node can drop frames on a hard camera move, genlock can drift, tracking can jitter, or VRAM can spike during an effects cue — and the take looks perfect in the viewfinder while quietly being broken. The damage is discovered weeks later in the 4K deliverable, when reshoots cost six figures. A volume stage costs $200,000–$500,000 per day.

## What BrainBar does

BrainBar is a five-agent crew that fuses a shot's **creative intent** (script, shot list, storyboard, call sheet) with the take's **live technical telemetry** (frame times, sync drift, tracking jitter, GPU/VRAM) flowing into Grafana Cloud during that exact take window, and takes real action: it issues a per-take verdict (circle / hold / reshoot / fixable-in-post), pre-stages the corrective take, opens and drives Grafana incidents when stage hardware fails, silences alert storms, annotates dashboards, and hands editorial a technical-dailies package with a Grafana deep-link for every shot.

BrainBar also watches itself: the crew's own Gemini call latency, token cost, and MCP tool activity flow into the same Grafana Cloud stack it queries, and the Supervisor reads that data back through the Grafana MCP server to stay inside an on-set latency budget and route routine takes to a fast model and hero shots to a stronger one.

## Architecture

[architecture/architecture.md](architecture/architecture.md) — the four platform boundaries and the closed loop.
[architecture/telemetry-schema.md](architecture/telemetry-schema.md) — every metric/log/trace field the simulator emits and the crew queries.

## Google Cloud — used where

Every row below is a real, runtime call — not a name-drop. File paths point at the exact import/call site.

| Service | Where it's called |
|---|---|
| Gemini Enterprise Agent Platform (ADK) | Every agent module builds a `google.adk.agents.LlmAgent`, e.g. [`agents/supervisor/agent.py`](agents/supervisor/agent.py), [`agents/technical_director/agent.py`](agents/technical_director/agent.py) |
| Gemini Pro / Flash | [`agents/config.py`](agents/config.py) pins the model IDs once (verified GA via direct API calls — see [`scripts/list_vertex_models.md`](scripts/list_vertex_models.md)); every agent's `build_agent()` reads them |
| RAG Engine + Vector Search | [`agents/continuity/rag_setup.py`](agents/continuity/rag_setup.py) (corpus + ingestion), [`agents/continuity/agent.py`](agents/continuity/agent.py) (`rag.retrieval_query` as a tool) |
| Document AI | [`agents/continuity/documentai_client.py`](agents/continuity/documentai_client.py) — parses the script/call-sheet PDFs before RAG ingestion |
| Memory Bank | [`agents/supervisor/memory.py`](agents/supervisor/memory.py) — `VertexAiMemoryBankService` backed by the Agent Engine deployment below |
| Agent Engine | [`deploy/agent-engine/deploy.py`](deploy/agent-engine/deploy.py) — the Supervisor deployed as an independently queryable hosted agent (`reasoningEngines/940312789434499072`) |
| Cloud Run | [`deploy/cloud-run/`](deploy/cloud-run/) — simulator, backend, frontend, and the Grafana MCP service all run here |
| Cloud Storage | [`agents/dit/storage_client.py`](agents/dit/storage_client.py) — dailies JSON uploads |
| BigQuery | [`agents/dit/bigquery_sink.py`](agents/dit/bigquery_sink.py) — one row per take |
| Secret Manager | Cloud Run `--set-secrets` for the Grafana token and OTLP API key (see deploy commands below) |

## Grafana — used where

| Surface | Where it's called |
|---|---|
| Metrics (Mimir/PromQL) | [`agents/technical_director/agent.py`](agents/technical_director/agent.py) — frame-time, VRAM, drift, jitter queries via MCP |
| Logs (Loki/LogQL) | [`agents/technical_director/agent.py`](agents/technical_director/agent.py), [`agents/continuity/agent.py`](agents/continuity/agent.py) — slate/cut/warning events via MCP |
| Traces (Tempo) | [`agents/technical_director/agent.py`](agents/technical_director/agent.py) — `find_slow_requests` / TraceQL via MCP |
| Dashboards + deep-links | [`agents/dit/agent.py`](agents/dit/agent.py) — `generate_deeplink` per shot via MCP |
| Alerting + Incidents (IRM) | [`agents/first_ad/agent.py`](agents/first_ad/agent.py) — incident open/annotate/resolve, alert silencing via MCP |
| Annotations | [`agents/first_ad/agent.py`](agents/first_ad/agent.py) — per-take verdict annotations via MCP |
| AI Observability | [`agents/observability.py`](agents/observability.py) — the crew's own Gemini/MCP call telemetry, exported as OTLP |
| Grafana MCP server | [`agents/mcp_client.py`](agents/mcp_client.py) — the single connection point every call above goes through; ADK discovers the live tool set at runtime, nothing is hardcoded |
| Dashboards/alerts as code | [`simulator/grafana_provisioning/`](simulator/grafana_provisioning/) — Stage Health + Crew Health dashboards and 3 alert rules, provisioned via the Grafana HTTP API |
| Annotation history as playbook | [`agents/technical_director/agent.py`](agents/technical_director/agent.py) — `get_annotations` search over past `brainbar-verdict` annotations before diagnosing a new fault, via MCP |
| Token cost governance | [`agents/pricing.py`](agents/pricing.py) — estimated $ per agent per take, on the Crew Health dashboard and in the frontend |
| Hosted OAuth MCP (demo) | [`scripts/demo_hosted_oauth_mcp.md`](scripts/demo_hosted_oauth_mcp.md) — the interactive "authorize as yourself" Cloud MCP path, alongside the unattended OSS+IAM path used in deployment |
| Predictive VRAM forecasting (Grafana ML) | [`agents/first_ad/agent.py`](agents/first_ad/agent.py) — pre-emptive load-shed when Grafana ML forecasts a node's VRAM will breach threshold, via MCP |
| Continuous profiling (Pyroscope) | [`agents/profiling.py`](agents/profiling.py) — the crew's own process, trace-linked, pushed via OTLP |
| Sift second opinion | [`agents/technical_director/agent.py`](agents/technical_director/agent.py) — reconciles with any existing Sift investigation for the take window, via MCP |
| On-call paging (IRM) | [`agents/first_ad/oncall_client.py`](agents/first_ad/oncall_client.py) — real escalation-chain page on a hardware failure, not just an incident |

### Predictive VRAM forecasting with Grafana ML

`brainbar_node_vram_percent` is already alerted on reactively (`simulator/grafana_provisioning/alert_rules.py`, threshold 90%) — this adds a forecast so First AD can act *before* that threshold is crossed, not after. GPU VRAM exhaustion is the single most common cause of render-farm job failure industry-wide, which is what makes forecasting it specifically (rather than, say, frame time) worth the setup:

1. In the Grafana Cloud stack: **Administration → AI & Machine Learning → Metric Forecasts → New Forecast**.
2. Name it exactly `brainbar_vram_forecast` (this literal name is hardcoded in `agents/first_ad/agent.py`'s instruction and in `simulator/grafana_provisioning/stage_health_dashboard.py`'s `VRAM_FORECAST_JOB_NAME` — keep both in sync if you rename it).
3. Query: `max by (node) (brainbar_node_vram_percent)`. Forecast horizon: 10–15 minutes is enough to act on before the next take rolls.
4. Once it's producing predictions, re-run `python -m simulator.grafana_provisioning.provision` — it looks up the resulting `grafanacloud-ml-metrics` datasource automatically and adds the actual-vs-forecast panel to the Stage Health dashboard. Without step 1–3 done first, provisioning still succeeds; it just skips that one panel and says why.

First AD checks this every take (see its instruction) via `list_datasources` + `query_prometheus` against the forecast job's `:predicted` series — no new MCP tool needed, forecasts are just another Prometheus metric once the job exists.

### Continuous profiling with Pyroscope

Metrics/logs/traces establish *that* something was slow; profiling establishes *why*, at the function level. `agents/profiling.py` pushes the crew's own process to Grafana Cloud Pyroscope and links it to the same OTel traces `agents/observability.py` already exports, so a slow span in Tempo opens straight into a flamegraph.

1. In the Grafana Cloud stack: **Connections → Add new connection → Pyroscope**, or reuse an existing one — note its push URL, instance ID, and a scoped API key (`profiles:write`).
2. Set `PYROSCOPE_SERVER_ADDRESS`, `PYROSCOPE_INSTANCE_ID`, `PYROSCOPE_API_KEY` in `.env` (separate credentials from the OTLP ones above — Pyroscope is a distinct product/endpoint on the same stack).
3. `pip install -r agents/requirements.txt` pulls in `pyroscope-io` + `pyroscope-otel`. **Windows note**: `pyroscope-io` is a Rust extension with prebuilt wheels for Linux/macOS only as of this writing — a Windows dev machine needs a Rust toolchain on `PATH` to build it from source, or run the crew under WSL/Docker instead. This does not affect the deployed Cloud Run image, which builds on Linux and installs the prebuilt wheel normally. If the package isn't importable, `agents/profiling.py` logs a warning and disables profiling rather than crashing the crew.
4. In Grafana Explore, open a slow trace span from the `brainbar-crew` service and use **Trace to profiles** to jump straight to its flamegraph.

### Sift as a second opinion

Grafana Sift is Grafana Cloud's own ML-powered diagnostic assistant (error-log spikes, overloaded nodes, related config changes). The Grafana MCP server exposes tools to *read* Sift investigations (`list_sift_investigations`, `get_sift_investigation`, `get_sift_analysis`) but none to *start* one — so Technical Director checks for and reconciles with whatever investigation already exists for the take window, rather than fabricating a "run investigation" tool call that doesn't exist. To have one exist during a demo, start it manually from Grafana Explore (**+ Add → Run investigation**) or the ML app around the fault window before rolling that take. Grafana's own auto-trigger-on-incident-creation only fires for Kubernetes-backed data (this stage isn't Kubernetes), so it isn't relied on here.

### Paging on-call through Grafana Cloud IRM

Today, a hardware failure gets a Grafana incident and an annotation — both things you have to be looking at Grafana to see. This adds a real page:

1. In the Grafana Cloud stack: **Alerting & IRM → Integrations → New integration → Webhook**. Attach it to an escalation chain and on-call schedule (or create a simple one-person schedule for demo purposes).
2. Copy the integration's inbound webhook URL into `GRAFANA_ONCALL_WEBHOOK_URL` in `.env`.
3. On `node_down`, First AD now calls `page_oncall` (`agents/first_ad/oncall_client.py`) in addition to opening the incident — a real page through the escalation chain, grouped by node (`alert_uid`) so repeated failures on the same node re-fire one alert instead of paging on every occurrence.

Without step 1–2, `page_oncall` fails gracefully (logged in the ActionLog as a failed action with the reason, per First AD's rule 6 — never silently dropped) rather than blocking the rest of First AD's actions.

### Enabling Grafana Cloud's AI Observability app

`agents/observability.py` already exports everything the crew does as OpenTelemetry
GenAI-semantic-convention telemetry (token usage, per-agent invocation duration,
per-tool-call duration, tagged with `service.name`/`service.version`/
`deployment.environment`) to the same Grafana Cloud OTLP endpoint the Stage Simulator
uses. That's the exact signal Grafana Cloud's built-in **AI Observability** app (per-
agent reports, AI-generated analysis, token cost per step) is built to read — but
installing that app on a stack is a Grafana Cloud portal action, not something this
repo's service-account token is scoped to do via API:

1. In the Grafana Cloud stack used by `GRAFANA_CLOUD_STACK_URL`: **Administration →
   Apps → AI Observability** (search "AI" if it's not pinned) → **Enable**.
2. Give it a few minutes after the next take cuts — it backfills from the OTLP data
   already arriving, no re-instrumentation needed.
3. Cross-check against `simulator/grafana_provisioning/crew_health_dashboard.py` (the
   "Crew Health" dashboard this repo provisions itself): if a panel there shows data but
   the AI Observability app doesn't, the app is either not yet enabled or is reading a
   different stack than `GRAFANA_CLOUD_STACK_URL`.

The Crew Health dashboard stays in the repo regardless — it's dashboards-as-code
(reviewable, versioned, provisioned by `provision.py`) covering the same signal, so the
demo doesn't depend on a portal toggle having been clicked correctly beforehand.

## Running the judge demo

The Production Wall's **🎬 Run demo scenario** button (`frontend/src/components/DemoControls.jsx`)
drives a scripted, escalating 3-take run — one click instead of several manual arm/roll/cut
cycles under demo pressure — narrated live in its own log as each step lands:

1. **Clean plate, no fault** (setup 4) — baseline: all five agents confirm a clean take fast.
2. **VRAM spike on node-3** (setup 2) — Technical Director's annotation-history playbook and
   Sift second-opinion check both run here; First AD's VRAM-forecast check runs on every
   take regardless, but this is the one likely to actually trip it.
3. **Node death on node-6** (setup 3) — the full incident path: Grafana incident opened,
   on-call paged, alert storm silenced, node drained. Watch the incident banner flip from
   red to handled.

It finishes by wrapping the shoot (dailies + report). Each step waits for that take's
`action_log` to land (up to 90s) before advancing, so it paces itself to real Gemini/Grafana
latency rather than a fixed timer — if a step times out or errors it says so in the log and
still moves on, rather than leaving the demo stuck.

**Before judges arrive**, three of the four setup steps above are things the scenario itself
can't do for you:
- Predictive VRAM forecasting only shows a real prediction if the Grafana ML forecast job
  has actual climbing-VRAM history to learn from — run the simulator (or the scenario's
  step 2) a few times beforehand so it has something to train on.
- A Sift second opinion only exists if you started one from Grafana Explore before that take
  cuts (see the Sift section above) — otherwise Technical Director correctly reports none
  found, which is honest but less impressive on camera.
- On-call paging needs the IRM webhook integration configured (see above) or `page_oncall`
  will report a failed action with the reason, rather than silently doing nothing.

Continuous profiling and the Grafana capabilities legend on the Crew Wall need no pre-demo
step — they're either always running or always visible from page load.

## Repository layout

```
simulator/    Stage Simulator — emits real telemetry to Grafana Cloud
agents/       The five-agent ADK crew
backend/      FastAPI orchestration + mock stage-control API
frontend/     React frontend — light landing page + dashboard (Production Wall + Crew Wall)
assets/       Synthetic script, shot list, storyboards, call sheet
deploy/       Cloud Run + Agent Engine deployment configs
architecture/ Architecture + telemetry schema docs
```

Per-service setup: [`simulator/README.md`](simulator/README.md), [`agents/README.md`](agents/README.md), [`backend/README.md`](backend/README.md), [`frontend/README.md`](frontend/README.md).

## Local setup

```bash
git clone https://github.com/nnam-droid12/BrainBar.git && cd BrainBar
cp .env.example .env   # fill in your GCP project, Grafana Cloud stack URL, and service-account token
gcloud auth application-default login
gcloud config set project <your-project>
```

Then, in separate terminals:

```bash
# Grafana MCP server (OSS) — see scripts/run_grafana_mcp_oss.md
docker run --rm -p 8000:8000 -e GRAFANA_URL="$GRAFANA_CLOUD_STACK_URL" \
  -e GRAFANA_SERVICE_ACCOUNT_TOKEN="$GRAFANA_SERVICE_ACCOUNT_TOKEN" \
  mcp/grafana -t streamable-http --address :8000 --allowed-hosts "*" --allowed-origins "*"

# Simulator
python -m venv .venv-sim && .venv-sim/Scripts/activate
pip install -r simulator/requirements.txt
python -m simulator.main

# Backend + agent crew
python -m venv .venv-agents && .venv-agents/Scripts/activate
pip install -r agents/requirements.txt -r backend/requirements.txt
python -m backend.run

# Frontend
cd frontend && npm install
cp .env.example .env   # point at the backend above
npm run dev
```

## Hosted deployment

| Service | URL |
|---|---|
| Frontend (landing + dashboard) | https://brainbar-frontend-854441956422.us-central1.run.app |
| Backend API | https://brainbar-backend-854441956422.us-central1.run.app |
| Stage Simulator | https://brainbar-simulator-854441956422.us-central1.run.app |
| Grafana MCP service | Cloud Run, IAM-protected (not public — agents authenticate with a Google ID token, see `agents/mcp_client.py`) |
| Supervisor (Agent Engine) | `projects/854441956422/locations/us-central1/reasoningEngines/940312789434499072` |

Redeploy any service with its `deploy/cloud-run/*/cloudbuild.yaml` + `gcloud run deploy`; redeploy the Supervisor with `python deploy/agent-engine/deploy.py`.

## Running the demo

From the frontend's Production Wall, **Demo controls** panel:

1. Pick a setup and **Roll take** — a clean take circles once the crew analyzes it.
2. Pick a fault (e.g. VRAM spike), **Arm for next take**, then roll again — the Supervisor issues a HOLD or RESHOOT with timecoded evidence, and the First AD pre-stages the correction and annotates the Stage Health dashboard.
3. Arm **Node death** and roll — an alert fires, the First AD opens a real Grafana incident and drives it to resolution.
4. Switch to the **Crew Wall** to see verdict latency vs. budget and Flash/Pro routing decisions with the Supervisor's own reasoning.
5. **Wrap shoot** — the DIT compiles technical dailies with a Grafana deep-link per shot, and the Supervisor writes the end-of-day report.

## License

Apache-2.0, see [LICENSE](LICENSE).

