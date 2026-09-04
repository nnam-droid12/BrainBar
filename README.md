# BrainBar

**The AI crew that catches a broken take before it becomes a six-figure reshoot.**

> Five Gemini-powered agents fuse a shot's creative intent with live Grafana telemetry
> to issue a per-take verdict, act on it in real time, forecast the next failure before
> it happens, and page a human when a machine cannot fix it, all inside the same
> Grafana Cloud stack they query.

**Built for:** Agentic Cinema: The Blockbuster Hackathon, Grafana track

**Category:** Live agents, Grafana Cloud integration, autonomous multi-agent orchestration

**Built with:** Google Agent Development Kit (ADK), Gemini 2.5 Pro/Flash, Gemini Live API, Grafana Cloud (Mimir, Loki, Tempo, MCP server, Machine Learning, Sift, Pyroscope, Incident Response and Management), Vertex AI RAG Engine, Document AI, Agent Engine, Cloud Run, BigQuery, Cloud Storage

**Live:** [brainbar-frontend-854441956422.us-central1.run.app](https://brainbar-frontend-854441956422.us-central1.run.app)

---

## Table of Contents

- [The Problem](#the-problem)
- [The Solution](#the-solution)
- [A Take, End to End](#a-take-end-to-end)
- [What Makes BrainBar Unique](#what-makes-brainbar-unique)
- [Architecture](#architecture)
- [BrainBar as an MCP Server](#brainbar-as-an-mcp-server)
- [The Take Pipeline](#the-take-pipeline)
- [Agent and Tool Registry](#agent-and-tool-registry)
- [Grafana Cloud Integration](#grafana-cloud-integration)
- [Gemini and ADK Features Used](#gemini-and-adk-features-used)
- [Tech Stack](#tech-stack)
- [Local Setup](#local-setup)
- [Cloud Deployment](#cloud-deployment)
- [Project Structure](#project-structure)
- [Running the Judge Demo](#running-the-judge-demo)
- [License](#license)

---

## The Problem

Modern tent-pole films are shot on LED volumes: a curved wall of LED panels driven by a
real-time render cluster, synchronized to the camera through tracking, genlock, and
timecode. A volume stage costs $200,000 to $500,000 per day. The failure mode that
makes this expensive is not the failure everyone watches for.

| # | Failure Pattern | Why It Is Expensive |
|---|---|---|
| 1 | **Invisible technical damage.** A render node drops frames on a hard camera move, genlock drifts, tracking jitters, or VRAM spikes during an effects cue, and the take looks perfect in the viewfinder while quietly being broken. | The damage surfaces weeks later in the 4K deliverable, when a reshoot means rebooking the volume, the cast, and the crew. |
| 2 | **GPU VRAM exhaustion.** Industry-wide, VRAM ceilings are the single most common cause of render-farm job failure, more than compute or network. | BrainBar's own stage telemetry tracks `brainbar_node_vram_percent` per node for exactly this reason. |
| 3 | **Data and coordination sprawl.** A single day on an LED volume generates terabytes of plate media, tracking data, and renders, moved across disconnected asset, review, and security systems. | Nobody on set has one place to ask "what actually happened on this take, technically and creatively, right now." |
| 4 | **Institutional amnesia.** The same node fails the same way on a later shoot day because nobody wrote down the pattern, or wrote it somewhere nobody checks before rolling the next take. | A postmortem that lives in a doc nobody reopens is not a playbook, it is an archive. |
| 5 | **Monitoring without action.** A dashboard can show a spike. It cannot pre-stage a corrective take, open an incident, silence an alert storm, or page the person who needs to know right now. | Watching is not the same as responding, and on a $500,000 day, the gap between the two is expensive. |

## The Solution

BrainBar is a five-agent crew that fuses a shot's **creative intent** (script, shot
list, storyboard, call sheet) with the take's **live technical telemetry** (frame
times, sync drift, tracking jitter, GPU and VRAM) flowing into Grafana Cloud during
that exact take window, and takes real action on what it finds.

| Capability | Details |
|---|---|
| **Per-take verdict** | Circle, hold, reshoot, or fixable-in-post, synthesized from independent technical and creative analysis, with cited evidence, never a vague "something looked off." |
| **Real action, not a report** | Pre-stages the corrective take, opens and drives Grafana incidents on hardware failure, silences alert storms, annotates dashboards, and pages a real human on-call. |
| **Predictive failure prevention** | Reads a Grafana Machine Learning VRAM forecast and pre-emptively load-sheds a node before it actually exhausts, not after. |
| **A live, self-written playbook** | Searches its own crew's past verdict annotations in Grafana before diagnosing a new fault. Institutional memory that lives in the same stack it queries, not a document nobody reopens. |
| **A second opinion from Grafana's own AI** | Checks for and reconciles with any Grafana Sift investigation overlapping the take window, agreeing or disagreeing explicitly rather than restating it. |
| **Code-level self-diagnosis** | The crew's own process is continuously profiled with Grafana Cloud Pyroscope and linked to its own OpenTelemetry traces, so a slow step opens straight into a flamegraph. |
| **Cost governance on set** | Every agent's real token cost is estimated in dollars and shown live, not buried as a raw token count nobody on set can size up at a glance. |
| **Technical dailies** | A per-shot package with a Grafana deep-link for every take, delivered to editorial at wrap. |
| **The crew watches itself** | Its own Gemini call latency, token cost, and MCP tool activity flow into the same Grafana Cloud stack it queries, and the Supervisor reads that data back before every take to stay inside an on-set latency budget and to detect its own recent quota errors before routing to a model tier likely to fail. |

## A Take, End to End

This is a real sequence of events, captured from an actual run against a live Grafana
Cloud stack and Vertex AI project, generalized slightly for readability.

```
CUT.  Take sc03-setup4-take3 rolls on node-6.

T+0s   Continuity and Technical Director start in parallel.
T+4s   Technical Director pulls Mimir frame-time and VRAM series for the take
       window, checks Loki for warning and sync_loss events, searches its own
       annotation history for prior node-6 incidents, and checks for an
       overlapping Grafana Sift investigation. None found on either count.
T+9s   node-6 stops reporting telemetry. Grafana's alert rule fires within
       seconds of the missing series.
T+11s  Supervisor synthesizes both verdicts into a single call.
T+18s  First AD receives the verdict plus node_down=node-6, and acts:
         - annotates the Stage Health dashboard with the verdict and headline
         - opens a Grafana incident for the hardware failure
         - drains node-6, steering render load to the healthy nodes
         - pages the on-call escalation chain, grouped by node so a repeat
           failure re-fires one alert instead of paging on every occurrence
         - attempts to silence the downstream alert storm for that node, and
           reports honestly when the alerting tool cannot do it without a
           specific rule ID rather than pretending it succeeded
T+22s  Verdict lands: CIRCLE. Technically clean before the node failure,
       intent matched. Coverage still owed for the scene is tracked forward.
```

Every one of those actions is a real MCP call against a live Grafana Cloud stack.
Nothing here is templated copy standing in for a demo.

## What Makes BrainBar Unique

Most take-review tooling stops at a dashboard. BrainBar's five agents act on what the
dashboard shows, and several of the ways they do it are not the obvious use of Grafana
Cloud.

| Feature | What It Does | Why It Is Not The Obvious Choice |
|---|---|---|
| **Predictive VRAM forecasting** | First AD reads a Grafana Machine Learning forecast on `brainbar_node_vram_percent` every take, and pre-emptively load-sheds a node forecast to cross the critical threshold soon, before the next take rolls. | Reactive alerting on VRAM is the obvious move. Forecasting the specific metric that causes the most real-world render-farm failures, and acting on the forecast rather than the breach, is not. |
| **Sift as a second, independent opinion** | Technical Director checks for an existing Grafana Sift investigation overlapping the take window and explicitly reconciles with it, agreeing or disagreeing in its own summary. | The Grafana MCP server exposes tools to read a Sift investigation but none to start one. Most integrations would either ignore Sift entirely or fabricate a tool call that does not exist. BrainBar consults Grafana's own AI as a second opinion instead of pretending it can trigger one on demand. |
| **Continuous profiling with Pyroscope** | The crew's own process is profiled and linked to its own OpenTelemetry traces, so a slow step in Grafana Explore opens straight into a flamegraph. | Metrics, logs, and traces establish that something was slow. Profiling establishes why, at the function level, which almost no hackathon-scale agent project reaches for. |
| **Annotation history as a live playbook** | Technical Director searches its own crew's past verdict annotations before diagnosing a new fault, and cites precedent explicitly when it finds a match. | A static runbook file goes stale. Every past take's annotation already lives in the same Grafana Cloud stack being queried, so the playbook writes and updates itself. |
| **Real on-call paging, not just an incident** | On a hardware failure, First AD pages a real escalation chain through Grafana Cloud Incident Response and Management, grouped by node so repeats do not re-page on every occurrence. | Opening an incident is the obvious action. Paging the person who actually needs to act on it, with the discipline to group repeats instead of flooding them, is the harder and more useful one. |
| **Hallucination and quota self-governance** | The crew's own tool-call errors and 429 quota errors are exported as Grafana metrics, and the Supervisor reads them back before routing a take to a stronger model, downgrading automatically if recent errors suggest it will fail anyway. | Most agent demos treat reliability as someone else's problem. BrainBar's own past incident, an agent hallucinating a tool name that did not exist, is the reason this exists: it is a fix earned from a real failure, exported as a real Grafana signal, not a hypothetical safeguard. |
| **Bidirectional MCP: BrainBar is also a server** | Every agent above is an MCP *client* of Grafana. `agents/mcp_server.py` is the other direction: BrainBar's own diagnosis exposed as MCP tools any external caller can invoke directly, deployed as its own IAM-protected Cloud Run service. | Almost every MCP integration only calls out. Once an agent's reasoning already sits behind a bounded, structured interface, exposing that same interface to the outside world is a few dozen lines, not a second product, and it is what turns a chat feature into infrastructure other agents can build on. |
| **Hardware failures get reacted to in parallel, not in a queue** | When a render node dies mid-take, First AD's incident/drain/page response fires the instant the event arrives, running concurrently with the slower creative and technical analysis of the same take rather than waiting behind it. | The obvious architecture is one pipeline: analyze, then act. A dead node does not care what the creative verdict says, and waiting on a verdict that can take over a minute under load before draining a node that is actively failing is a real, measured latency bug, not a hypothetical one. |
| **One evidence bar, no matter which model answers** | A single function checks that a not-clean verdict's cited issues are real (a real node, a real metric, a substantive root cause), applied identically whether Technical Director ran on Flash or Pro. | The easy version of a model fallback quietly ships whatever the cheaper model produces. Routing this through one shared check, called from one place, makes it structurally impossible for a quota-driven downgrade to lower the bar without anyone noticing. |

## Architecture

BrainBar is four platform boundaries wired into one closed loop: a simulated
LED-volume stage, Grafana Cloud, Google Cloud, and a presentation layer.

```
Simulated LED-Volume Stage (simulator/)
  6-node nDisplay render cluster, camera tracking, genlock/timecode reference,
  a fault injector (VRAM spike, node death, genlock drift, tracking jitter,
  thermal throttle). Every frame of every take, real OTLP telemetry is pushed
  to Grafana Cloud. This is the only simulated part of the system; the data
  it produces is real.
       |
       |  OTLP metrics/logs/traces, every frame
       v
Grafana Cloud
  Mimir (metrics) / Loki (logs) / Tempo (traces)
  Stage Health + Crew Health dashboards, provisioned as code
  3 alert rules + Incidents (IRM) + Annotations
  Grafana MCP server: the single connection point every agent's Grafana
    tool call goes through; tools are discovered live, nothing hardcoded
  AI Observability: the crew's own Gemini/MCP call telemetry, exported back
    into this same stack
  Machine Learning forecasts, Sift investigations, Pyroscope profiles,
    on-call escalation chains
       ^                                    |
       |  query via MCP (BrainBar as        |  query via MCP
       |  a client of Grafana)              v
Google Cloud / Gemini Enterprise Agent Platform (agents/)
  Supervisor (Gemini Pro) - synthesizes the circle-take call, self-governs
    routing, owns Memory Bank, deployed to Agent Engine as an independently
    queryable hosted agent
  Continuity (Flash) - grounded on RAG Engine + Vector Search over the
    script/shot-list/storyboard, parsed through Document AI
  Technical Director (Flash, Pro for hero/fault takes) - heaviest Grafana
    user, diagnoses telemetry via Mimir/Loki/Tempo; every not-clean verdict
    passes the same evidence-grounding gate regardless of which tier ran
  First AD (Flash) - converts a verdict into consequences; a hardware
    failure gets its own immediate reaction, concurrently with the
    creative/technical analysis above, not queued behind it
  DIT (Flash) - compiles technical dailies, writes to Cloud Storage + BigQuery
       |                                    ^
       |                                    |  MCP tool calls, straight into
       v                                    |  analyze_take (bypasses backend/
Presentation (backend/ + frontend/)         |  entirely): agents/mcp_server.py,
  FastAPI backend orchestrates the crew     |  its own IAM-protected Cloud Run
    on every cut event, streams every       |  service — BrainBar as a server
    event live over WebSocket, exposes      |
    REST reads for page reload              |
  React frontend: a light landing page      |  Any external MCP-speaking caller
    routing into a dark control-room        |  (Grafana's own Assistant, a
    dashboard, Production Wall + Crew Wall  |  coding agent, another tool)
```

**Two loops run through the same Grafana Cloud stack:**

1. **The crew watching the shoot.** Stage to OTLP to Mimir/Loki/Tempo to Grafana MCP
   to Technical Director and Continuity to Supervisor verdict to First AD action, back
   to the stage as a pre-staged corrective take and back to Grafana as an incident or
   annotation.
2. **The crew watching itself.** Every Gemini and MCP call to AI Observability OTLP to
   Mimir to Grafana MCP to the Supervisor's own routing self-check, deciding the next
   take's model tier and whether Pro is even safe to try right now.

Full detail: [architecture/architecture.md](architecture/architecture.md) and
[architecture/telemetry-schema.md](architecture/telemetry-schema.md) (every metric,
log, and span name the simulator emits and the crew queries).

## BrainBar as an MCP Server

Every integration described so far is BrainBar calling out to Grafana's MCP server.
[`agents/mcp_server.py`](agents/mcp_server.py) is the other direction: the same
diagnostic reasoning the cut pipeline runs internally, exposed as MCP tools any
external caller can invoke directly.

This works because Technical Director and Continuity already never return raw
telemetry. `analyze_take` in both
[`agents/technical_director/analyze.py`](agents/technical_director/analyze.py) and
[`agents/continuity/analyze.py`](agents/continuity/analyze.py) queries Grafana itself
and hands back one bounded, structured verdict, never a table dump. That is what makes
handing the same function to an untrusted external caller safe to do at all — a caller
gets a purpose-built answer, never a raw connection to Mimir or Loki.

| Tool | What It Does |
|---|---|
| `diagnose_take_technical` | Runs Technical Director against one take's real Grafana telemetry (Mimir frame times/VRAM/drift, Loki stage events, Tempo dropped-frame traces) and returns a structured `TechnicalVerdict` — clean or not, cited issues with exact numbers, a summary. Always Flash tier: an on-demand diagnostic call, not a routed production take. |
| `diagnose_take_creative` | Runs Continuity against one take: grounds it on the real script/shot-list/storyboard/call-sheet via RAG, cross-checks Loki for whether scripted cues fired, and returns whether it matches creative intent plus coverage still owed. |

A coding agent, Grafana's own Assistant, or any other MCP-speaking tool can ask "is
take X clean?" directly, no chat UI, no cut webhook, no dashboard required.

**Access control.** This server is deliberately not mounted on the existing backend:
that service is `--allow-unauthenticated` on purpose, since the frontend calls it
directly from the browser. A tool surface the outside world can call needs real access
control, so `agents/mcp_server.py` runs as its own Cloud Run service
(`deploy/cloud-run/mcp-server/`), IAM-protected rather than public, the same pattern
already used for the Grafana MCP proxy this crew itself authenticates to with a Google
ID token (see [`agents/mcp_client.py`](agents/mcp_client.py)).

Run it locally with `python -m agents.mcp_server` (streamable-HTTP transport on
`:8000`, same transport the Grafana MCP server itself uses).

## The Take Pipeline

Every take runs the same sequence, driven by the backend's response to the simulator's
slate and cut events.

| Step | Actor | What Happens |
|---|---|---|
| 1 | Simulator | Posts `slate` on take start, `cut` on take end, directly to the backend webhook so the crew reacts within seconds, not on a polling delay. |
| — | First AD (concurrent, on `node_down`) | Fires the instant a render node fails — independent of, and running in parallel with, the numbered sequence below, not queued behind it. Opens a Grafana incident, silences the alert storm, drains the node, and pages the real on-call escalation chain before a verdict exists, not after one. A zero-token check runs first: if the same node already triggered a reaction in the last 5 minutes, this is skipped entirely, so a flapping node cannot trigger a second full model call or re-page on-call for nothing new. |
| 2 | Supervisor | Decides the model tier for this take (Flash for routine coverage, Pro for hero or fault-active takes) by reading its own recent verdict latency and quota-error telemetry back from Grafana first. |
| 3 | Continuity + Technical Director | Run in parallel. Continuity grounds the take against the script, shot list, and storyboard, and checks Loki for whether scripted cues actually fired. Technical Director diagnoses the take's Mimir/Loki/Tempo telemetry, checks its own annotation history, and checks for a Sift second opinion. Every not-clean verdict passes the same evidence-grounding check before it is returned — the same function regardless of whether Flash or Pro ran, so a quota-driven fallback cannot quietly ship a less-scrutinized verdict. |
| 4 | Supervisor | Synthesizes both verdicts into one circle-take call, with reasoning and cited evidence, and writes anything worth remembering to Memory Bank. |
| 5 | First AD | Converts the verdict into action: annotate the dashboard, pre-stage a corrective take if warranted, and check the VRAM forecast for every active node. Told exactly what the concurrent reaction above already did, so a hardware failure never gets a second, redundant incident/alert/page/drain, or a redundant load-shed on the same node. |
| 6 | DIT (at wrap) | Compiles the technical dailies package with a Grafana deep-link per shot, writes to Cloud Storage and BigQuery, and the Supervisor generates the end-of-day report. |

## Agent and Tool Registry

Five ADK agents, each an `LlmAgent` with a Pydantic `output_schema`
(`agents/schemas.py`), so every result is structured, never free text.

| Agent | Model | Role |
|---|---|---|
| `supervisor/` | Gemini Pro | Synthesizes Continuity and Technical Director into the circle-take call; owns Memory Bank, model routing, and the end-of-day report |
| `continuity/` | Gemini Flash | Grounds each take against the script, shot list, and storyboard (RAG Engine, Document AI) and tracks coverage owed |
| `technical_director/` | Flash, Pro for hero/fault takes | Diagnoses take telemetry via Grafana MCP, checks annotation history and Sift |
| `first_ad/` | Flash | Converts verdicts into action: pre-stage a retake, open/resolve incidents, page on-call, silence alerts, annotate dashboards, act on VRAM forecasts |
| `dit/` | Flash | Compiles technical dailies with Grafana deep-links, writes to Cloud Storage and BigQuery |

### Grafana MCP tools by agent

The Grafana MCP server exposes its full tool set at runtime; each agent's tool filter
only narrows which of those it is allowed to call.

| Category | Tools |
|---|---|
| **Technical Director** | `query_prometheus`, `query_prometheus_histogram`, `list_prometheus_metric_names`, `list_prometheus_label_names`, `list_prometheus_label_values`, `query_loki_logs`, `query_loki_stats`, `query_loki_patterns`, `list_loki_label_names`, `list_loki_label_values`, `find_slow_requests`, `find_error_pattern_logs`, `list_datasources`, `search_dashboards`, `get_dashboard_summary`, `list_sift_investigations`, `get_sift_investigation`, `get_sift_analysis`, `get_annotations`, `grafana_api_request` |
| **Continuity** | `query_loki_logs`, `list_loki_label_names`, `list_loki_label_values`, `query_loki_patterns` |
| **First AD** | `create_incident`, `get_incident`, `list_incidents`, `add_activity_to_incident`, `alerting_manage_rules`, `alerting_manage_routing`, `create_annotation`, `update_annotation`, `query_prometheus`, `list_datasources` |
| **Supervisor (self-check)** | `query_prometheus`, `list_prometheus_metric_names` |
| **DIT** | dashboard/deep-link generation tools |
| **First AD (custom, non-MCP)** | `loadshed`, `drain_node`, `set_affinity` (mock stage-control API), `page_oncall` (Grafana Cloud IRM webhook) |

## Grafana Cloud Integration

Every row below is a real, runtime call, not a name-drop. File paths point at the
exact import or call site.

| Surface | Where It Is Called |
|---|---|
| Metrics (Mimir/PromQL) | [`agents/technical_director/agent.py`](agents/technical_director/agent.py), frame-time, VRAM, drift, and jitter queries via MCP |
| Logs (Loki/LogQL) | [`agents/technical_director/agent.py`](agents/technical_director/agent.py), [`agents/continuity/agent.py`](agents/continuity/agent.py), slate/cut/warning events via MCP |
| Traces (Tempo) | [`agents/technical_director/agent.py`](agents/technical_director/agent.py), `find_slow_requests` and TraceQL via MCP |
| Dashboards and deep-links | [`agents/dit/agent.py`](agents/dit/agent.py), a per-shot deep-link via MCP |
| Alerting and Incidents (IRM) | [`agents/first_ad/agent.py`](agents/first_ad/agent.py), incident open/annotate/resolve, alert silencing via MCP |
| Annotations | [`agents/first_ad/agent.py`](agents/first_ad/agent.py), a per-take verdict annotation via MCP |
| AI Observability | [`agents/observability.py`](agents/observability.py), the crew's own Gemini/MCP call telemetry, exported as OTLP |
| Grafana MCP server | [`agents/mcp_client.py`](agents/mcp_client.py), the single connection point every call above goes through; ADK discovers the live tool set at runtime |
| Dashboards and alerts as code | [`simulator/grafana_provisioning/`](simulator/grafana_provisioning/), Stage Health + Crew Health dashboards and 3 alert rules, provisioned via the Grafana HTTP API |
| Annotation history as playbook | [`agents/technical_director/agent.py`](agents/technical_director/agent.py), a `get_annotations` search over past `brainbar-verdict` annotations before diagnosing a new fault |
| Token cost governance | [`agents/pricing.py`](agents/pricing.py), estimated dollar cost per agent per take, on the Crew Health dashboard and in the frontend |
| Hosted OAuth MCP (demo) | [`scripts/demo_hosted_oauth_mcp.md`](scripts/demo_hosted_oauth_mcp.md), the interactive "authorize as yourself" Cloud MCP path, alongside the unattended OSS and IAM path used in deployment |
| Predictive VRAM forecasting (Grafana ML) | [`agents/first_ad/agent.py`](agents/first_ad/agent.py), pre-emptive load-shed when a Grafana ML forecast predicts a node's VRAM will breach threshold |
| Continuous profiling (Pyroscope) | [`agents/profiling.py`](agents/profiling.py), the crew's own process, trace-linked, pushed via OTLP |
| Sift second opinion | [`agents/technical_director/agent.py`](agents/technical_director/agent.py), reconciles with any existing Sift investigation for the take window |
| On-call paging (IRM) | [`agents/first_ad/oncall_client.py`](agents/first_ad/oncall_client.py), a real escalation-chain page on a hardware failure |
| Agent Observability (Sigil) | [`agents/sigil_client.py`](agents/sigil_client.py), [`agents/runtime.py`](agents/runtime.py), every agent call and every tool call wrapped as a conversation/generation/tool-execution, grouped by take_id, with time-to-first-token and a GOOD/BAD pipeline-health rating per take |
| Grafana Assistant self-diagnosis | [`agents/supervisor/self_diagnosis.py`](agents/supervisor/self_diagnosis.py), `ask_assistant` via MCP at wrap, the same natural-language investigation a human triggers from Slack, called programmatically and woven into the end-of-day report |
| BrainBar as an MCP server | [`agents/mcp_server.py`](agents/mcp_server.py), the crew's own diagnosis exposed the other direction: any MCP-speaking caller can ask `diagnose_take_technical`/`diagnose_take_creative` directly, bypassing the cut webhook and dashboard entirely. Deployed as its own IAM-protected Cloud Run service, same access-control pattern as the Grafana MCP proxy this crew already authenticates to |

### Predictive VRAM forecasting with Grafana ML

`brainbar_node_vram_percent` is already alerted on reactively at a 90 percent
threshold (`simulator/grafana_provisioning/alert_rules.py`). This adds a forecast so
First AD can act before that threshold is crossed, not after.

1. In the Grafana Cloud stack: Administration, AI and Machine Learning, Metric
   Forecasts, New Forecast.
2. Name it exactly `brainbar_vram_forecast` (hardcoded in `agents/first_ad/agent.py`'s
   instruction and in `simulator/grafana_provisioning/stage_health_dashboard.py`'s
   `VRAM_FORECAST_JOB_NAME`, keep both in sync if renamed).
3. Query: `max by (node) (brainbar_node_vram_percent)`. Forecast horizon of 10 to 15
   minutes is enough to act on before the next take rolls.
4. Once it is producing predictions, re-run
   `python -m simulator.grafana_provisioning.provision`. It looks up the resulting
   `grafanacloud-ml-metrics` datasource automatically and adds the actual-versus-forecast
   panel to the Stage Health dashboard. Without steps 1 through 3, provisioning still
   succeeds, it just skips that panel and says why.

First AD checks this every take via `list_datasources` plus `query_prometheus` against
the forecast job's `:predicted` series. No new MCP tool is needed; a forecast is just
another Prometheus metric once the job exists.

### Continuous profiling with Pyroscope

Metrics, logs, and traces establish that something was slow. Profiling establishes
why, at the function level. `agents/profiling.py` pushes the crew's own process to
Grafana Cloud Pyroscope and links it to the same OTel traces `agents/observability.py`
already exports, so a slow span in Tempo opens straight into a flamegraph.

1. In the Grafana Cloud stack: Connections, Add new connection, Pyroscope (or reuse an
   existing one). Note its push URL, instance ID, and a scoped API key
   (`profiles:write`).
2. Set `PYROSCOPE_SERVER_ADDRESS`, `PYROSCOPE_INSTANCE_ID`, `PYROSCOPE_API_KEY` in
   `.env`, separate credentials from the OTLP ones above since Pyroscope is a distinct
   product and endpoint on the same stack.
3. `pip install -r agents/requirements.txt` pulls in `pyroscope-io` and
   `pyroscope-otel`. On Windows, `pyroscope-io` is a Rust extension with prebuilt
   wheels for Linux and macOS only as of this writing; a Windows dev machine needs a
   Rust toolchain on PATH to build it from source, or run the crew under WSL or Docker
   instead. This does not affect the deployed Cloud Run image, which builds on Linux
   and installs the prebuilt wheel normally. If the package is not importable,
   `agents/profiling.py` logs a warning and disables profiling rather than crashing
   the crew.
4. In Grafana Explore, open a slow trace span from the `brainbar-crew` service and use
   Trace to profiles to jump straight to its flamegraph.

### Sift as a second opinion

Grafana Sift is Grafana Cloud's own ML-powered diagnostic assistant: error-log spikes,
overloaded nodes, related config changes. The Grafana MCP server exposes tools to read
Sift investigations (`list_sift_investigations`, `get_sift_investigation`,
`get_sift_analysis`) but none to start one, so Technical Director checks for and
reconciles with whatever investigation already exists for the take window, rather than
fabricating a tool call that does not exist. To have one exist during a demo, start it
manually from Grafana Explore (Add, Run investigation) or the ML app around the fault
window before rolling that take. Grafana's own auto-trigger-on-incident-creation only
fires for Kubernetes-backed data, and this stage is not Kubernetes, so it is not relied
on here.

### Paging on-call through Grafana Cloud IRM

A hardware failure gets a Grafana incident and an annotation by default, both things
you have to already be looking at Grafana to see. This adds a real page.

1. In the Grafana Cloud stack: Alerting and IRM, Integrations, New integration,
   Webhook. Attach it to an escalation chain and on-call schedule (or a simple
   one-person schedule for demo purposes).
2. Copy the integration's inbound webhook URL into `GRAFANA_ONCALL_WEBHOOK_URL` in
   `.env`.
3. On `node_down`, First AD calls `page_oncall`
   (`agents/first_ad/oncall_client.py`) in addition to opening the incident: a real
   page through the escalation chain, grouped by node (`alert_uid`) so repeated
   failures on the same node re-fire one alert instead of paging on every occurrence.

Without steps 1 and 2, `page_oncall` fails gracefully, logged in the ActionLog as a
failed action with the reason, never silently dropped, rather than blocking the rest
of First AD's actions.

### Agent Observability with Sigil

`agents/observability.py` exports raw OpenTelemetry GenAI-semantic-convention
telemetry (token usage, per-agent invocation duration, per-tool-call duration) to the
same Grafana Cloud OTLP endpoint the Stage Simulator uses — that keeps working
regardless of anything below, and backs the Crew Health dashboard this repo provisions
itself as code (`simulator/grafana_provisioning/crew_health_dashboard.py`).

`agents/sigil_client.py` and `agents/runtime.py` add a second, richer layer on top,
using Grafana's purpose-built `sigil-sdk` (the package backing the "AI Observability"
app's Overview/Performance/Errors/Usage/Tools/Evaluation tabs) rather than only raw
metrics:

- Every agent call for a take is wrapped as a **generation** and grouped under one
  **conversation** keyed by `take_id` — Continuity, Technical Director, Supervisor, and
  First AD's calls for the same take all show up as one conversation, not four
  unrelated log lines.
- Every tool call any agent makes — Grafana MCP tools and plain Python function tools
  alike — is wrapped as a **tool execution** by a Runner-level ADK plugin
  (`_SigilToolPlugin` in `agents/runtime.py`, using `before_tool_callback` /
  `after_tool_callback` / `on_tool_error_callback`), captured with its actual
  input/output/duration and linked to the same conversation — click a tool call in the
  Tools tab, see every take that used it, or the reverse.
- **Time-to-first-token** is captured per generation (`set_first_token_at` on the first
  event carrying real content), a second latency signal alongside the crew's own
  verdict-latency budget metric.
- At the end of every take's pipeline, `agents/sigil_client.py`'s
  `rate_take_conversation` submits a GOOD/BAD rating for that take's conversation —
  GOOD if the whole cut-to-verdict-to-actions pipeline completed, BAD if it hit an
  unhandled error (an exhausted-retry 429, a malformed tool call). This is a simple
  operational-health signal, not a reasoning-quality grade — Grafana Cloud's own
  AI-judge evaluations (configured in the portal below) are better positioned to grade
  whether a verdict was actually well-reasoned than a heuristic here could be.

Setup (distinct credentials from OTLP above — different product surface, different
access scope):

1. In the Grafana Cloud stack: **Observability → AI Observability → Configuration**.
   Copy the Agent Observability API endpoint into `SIGIL_ENDPOINT`.
2. **Administration → Access Policies → Create access policy**, scope `sigil:write`.
   Create a token under it. That token goes in `SIGIL_API_KEY`; the stack's instance ID
   goes in `SIGIL_INSTANCE_ID`.
3. To turn on AI-judge evaluations (the red/green pass/fail grading in the Evaluation
   tab and conversation view): in the same AI Observability app, define an evaluator
   against the `brainbar-crew` service — this is a Grafana Cloud portal action grading
   captured conversation content, not something this repo's code can enable from the
   outside, the same category of one-time setup as the AI Observability app enablement
   below.

Without `SIGIL_ENDPOINT`/`SIGIL_INSTANCE_ID`/`SIGIL_API_KEY` set, every call site above
degrades to a no-op — logged once, never a hard failure — so the crew runs identically
with or without this configured.

### Enabling Grafana Cloud's AI Observability app

Installing the AI Observability app itself on a stack (the container the Sigil data
above and the raw OTel GenAI telemetry both feed) is also a portal action:

1. In the Grafana Cloud stack used by `GRAFANA_CLOUD_STACK_URL`: Administration, Apps,
   AI Observability (search "AI" if it is not pinned), Enable.
2. Give it a few minutes after the next take cuts. It backfills from the data already
   arriving, no re-instrumentation needed.
3. Cross-check against the Crew Health dashboard: if a panel there shows data but the
   AI Observability app does not, the app is either not yet enabled or is reading a
   different stack than `GRAFANA_CLOUD_STACK_URL`.

The Crew Health dashboard stays in the repo regardless, dashboards-as-code, reviewable,
versioned, provisioned by `provision.py`, so the demo does not depend on a portal
toggle having been clicked correctly beforehand.

### Closing the loop: the crew asking Grafana's own AI Assistant

Grafana Cloud's AI Assistant is the same natural-language investigator a human triggers
by tagging `@Grafana` in Slack and asking it to investigate an agent's recent
performance. `agents/supervisor/self_diagnosis.py` calls the same capability
programmatically at wrap, through the `ask_assistant` MCP tool, and its findings are
woven into the Supervisor's end-of-day report (`agents/supervisor/end_of_day.py`) —
observe (Sigil and OTel telemetry) into analyze (the Assistant's own investigation)
into a surfaced recommendation for the humans running the stage, not an auto-applied
change the crew makes to its own prompts mid-demo. If the tool call fails or has
nothing substantive to report, the report simply omits that line rather than
fabricating a plausible-sounding finding.

## Gemini and ADK Features Used

### Google Agent Development Kit

- **`LlmAgent`** with a typed Pydantic `output_schema` per agent, so every result is
  structured, never free text that has to be re-parsed downstream.
- **`Runner` and session boilerplate** (`agents/runtime.py`), a fresh session per
  independent per-take analysis, and retry-with-backoff for transient 429 and 5xx
  errors, instrumented to export a metric on every transient error encountered.
- **`McpToolset`** (`agents/mcp_client.py`), the single connection point for every
  agent's Grafana tool access, tool sets filtered per agent and discovered live from
  the server at runtime, nothing hardcoded.
- **Parallel agent execution**: Continuity and Technical Director run concurrently on
  every cut via `asyncio.gather`, not sequentially.
- **OpenTelemetry GenAI semantic conventions**, emitted by ADK itself and exported to
  Grafana Cloud, the backbone of the crew's own self-observability loop.

### Gemini 2.5 Pro and Flash on Vertex AI

- **Model tiering**: routine coverage routes to Flash, hero and fault-active takes
  route to Pro, decided by the Supervisor after checking its own recent latency and
  quota-error telemetry back through Grafana first.
- **Structured JSON output** enforced via `output_schema`, even while the agent is
  still free to call tools mid-turn.
- **Gemini Live API**, used for spoken verdict narration (text in, audio out), never
  for analysis itself.
- **Live-verified model availability**: model IDs are pinned in `agents/config.py`
  after confirming GA availability against this specific project and region
  (`scripts/list_vertex_models.md`), since a model ID from documentation alone is not
  reliable across every Vertex AI project's allowlist.

### GitLab-equivalent integration depth, applied to Grafana

Where a code-review agent would integrate deeply with a Git host, BrainBar integrates
deeply with Grafana Cloud instead: querying Mimir, Loki, and Tempo, writing incidents,
annotations, and alert-silencing changes back, reading Grafana's own AI (Sift) and
Grafana's own forecasting (Machine Learning) as inputs to its own decisions, and paging
a human through Grafana's own on-call product when a machine cannot fix what it found.

## Tech Stack

| Layer | Technology |
|---|---|
| AI Model | Gemini 2.5 Pro and Flash (Vertex AI), Gemini Live API |
| Agent Framework | Google Agent Development Kit (ADK) |
| Grafana Integration | Grafana MCP server, Mimir, Loki, Tempo, Machine Learning, Sift, Pyroscope, Incident Response and Management, Annotations, AI Observability |
| Backend | FastAPI + Uvicorn (Python) |
| Transport | WebSocket (live event stream) + REST |
| Frontend | React + Vite, plain JavaScript |
| Grounding | Vertex AI RAG Engine + Vector Search, Document AI |
| Memory | Vertex AI Memory Bank (Agent Engine) |
| Telemetry Emission | OpenTelemetry (metrics, logs, traces, GenAI semantic conventions) |
| Storage and Analytics | Cloud Storage, BigQuery |
| Secrets | Secret Manager |
| Deployment | Cloud Run (4 services), Agent Engine (Supervisor), Cloud Build |

## Local Setup

### Prerequisites

- Python 3.11+
- Node.js and npm
- `gcloud` CLI authenticated: `gcloud auth application-default login`
- A Google Cloud project with Vertex AI enabled
- Docker (to run the Grafana MCP server locally)
- A Grafana Cloud stack

### 1. Clone and configure

```bash
git clone https://github.com/nnam-droid12/BrainBar.git && cd BrainBar
cp .env.example .env
```

Fill in `.env` with your GCP project, Grafana Cloud stack URL, and service-account
token.

```bash
gcloud auth application-default login
gcloud config set project <your-project>
```

### 2. Grafana MCP server (OSS)

```bash
docker run --rm -p 8000:8000 -e GRAFANA_URL="$GRAFANA_CLOUD_STACK_URL" \
  -e GRAFANA_SERVICE_ACCOUNT_TOKEN="$GRAFANA_SERVICE_ACCOUNT_TOKEN" \
  mcp/grafana -t streamable-http --address :8000 --allowed-hosts "*" --allowed-origins "*"
```

Full detail: [`scripts/run_grafana_mcp_oss.md`](scripts/run_grafana_mcp_oss.md).

### 3. Stage Simulator

```bash
python -m venv .venv-sim && .venv-sim/Scripts/activate
pip install -r simulator/requirements.txt
python -m simulator.main
```

Serves the control API on port 9000.

### 4. Backend and agent crew

```bash
python -m venv .venv-agents && .venv-agents/Scripts/activate
pip install -r agents/requirements.txt -r backend/requirements.txt
python -m backend.run
```

Serves on port 8080. Requires `BACKEND_WEBHOOK_URL` set so the simulator notifies the
backend of slate and cut events; without it, takes roll but the crew never fires.

### 5. Frontend

```bash
cd frontend && npm install
cp .env.example .env
npm run dev
```

### 6. One-time setup

```bash
python -m agents.continuity.rag_setup
```

Provisions the RAG Engine corpus and ingests the production assets, parsing PDFs
through Document AI first.

Per-service detail: [`simulator/README.md`](simulator/README.md),
[`agents/README.md`](agents/README.md), [`backend/README.md`](backend/README.md),
[`frontend/README.md`](frontend/README.md).

## Cloud Deployment

| Service | URL |
|---|---|
| Frontend (landing and dashboard) | https://brainbar-frontend-854441956422.us-central1.run.app |
| Backend API | https://brainbar-backend-854441956422.us-central1.run.app |
| Stage Simulator | https://brainbar-simulator-854441956422.us-central1.run.app |
| Grafana MCP service | Cloud Run, IAM-protected, not public; agents authenticate with a Google ID token (`agents/mcp_client.py`) |
| Supervisor (Agent Engine) | `projects/854441956422/locations/us-central1/reasoningEngines/940312789434499072` |

Redeploy any Cloud Run service with its `deploy/cloud-run/*/cloudbuild.yaml` and
`gcloud run deploy`. Redeploy the Supervisor with `python deploy/agent-engine/deploy.py`.
Every push to `main` also triggers each service's own Cloud Build pipeline
automatically.

## Project Structure

```
BrainBar/
├── simulator/                     Stage Simulator, emits real telemetry to Grafana Cloud
│   ├── shoot_script.yaml            Declarative scene/setups/cues
│   ├── models.py                    Shoot-script and take-state data model
│   ├── faults.py                    The fault injector
│   ├── telemetry.py                 OpenTelemetry wiring to Grafana Cloud
│   ├── emitter.py                   The take runner, real 24fps pacing
│   ├── control_api.py / main.py     FastAPI demo control plane
│   └── grafana_provisioning/        Dashboards + alert rules, provisioned as code
├── agents/                        The five-agent ADK crew
│   ├── config.py                    Every Gemini model ID, GCP resource, Grafana endpoint
│   ├── schemas.py                   Pydantic contracts every agent returns
│   ├── mcp_client.py                Single Grafana MCP connection point (BrainBar as a client)
│   ├── mcp_server.py                BrainBar's own diagnosis exposed as MCP tools (BrainBar as a server)
│   ├── sigil_client.py              Grafana Agent Observability (Sigil) wiring
│   ├── runtime.py                   Shared ADK Runner/session boilerplate, Sigil tool-call plugin
│   ├── observability.py             Grafana AI Observability instrumentation
│   ├── profiling.py                 Grafana Cloud Pyroscope instrumentation
│   ├── pricing.py                   Gemini token cost estimation
│   ├── supervisor/                  Synthesis, routing, Memory Bank, end-of-day report
│   ├── continuity/                  RAG-grounded creative verdict
│   ├── technical_director/          Telemetry diagnosis, annotation history, Sift
│   ├── first_ad/                    Actions: incidents, paging, alerting, stage control
│   └── dit/                         Technical dailies, Cloud Storage, BigQuery
├── backend/                        FastAPI orchestration + mock stage-control API
├── frontend/                       React dashboard: Production Wall + Crew Wall
├── assets/                         Synthetic script, shot list, storyboards, call sheet
├── deploy/                         Cloud Run + Agent Engine deployment configs
├── architecture/                   Architecture + telemetry schema docs
└── scripts/                        Setup, verification, and demo helper scripts
```

## Running the Judge Demo

The Production Wall's **Run demo scenario** button
(`frontend/src/components/DemoControls.jsx`) drives a scripted, escalating three-take
run, one click instead of several manual arm/roll/cut cycles under demo pressure,
narrated live in its own log as each step lands.

1. **Clean plate, no fault** (setup 4): baseline, all five agents confirm a clean take
   fast.
2. **VRAM spike on node-3** (setup 2): Technical Director's annotation-history
   playbook and Sift second-opinion check both run here; First AD's VRAM-forecast
   check runs on every take regardless, but this is the one most likely to trip it.
3. **Node death on node-6** (setup 3): the full incident path, a Grafana incident
   opened, on-call paged, alert storm silenced, node drained. Watch the incident
   banner flip from red to handled.

It finishes by wrapping the shoot: dailies plus the end-of-day report. Each step waits
for that take's action log to land (up to 90 seconds) before advancing, so it paces
itself to real Gemini and Grafana latency rather than a fixed timer. If a step times
out or errors, it says so in the log and still moves on, rather than leaving the demo
stuck.

**Before judges arrive**, three things the scenario itself cannot do for you:

- Predictive VRAM forecasting only shows a real prediction if the Grafana ML forecast
  job has actual climbing-VRAM history to learn from; run the simulator, or the
  scenario's step 2, a few times beforehand so it has something to train on.
- A Sift second opinion only exists if one was started from Grafana Explore before
  that take cuts (see the Sift section above); otherwise Technical Director correctly
  reports none found, which is honest but less impressive on camera.
- On-call paging needs the IRM webhook integration configured (see above), or
  `page_oncall` will report a failed action with the reason rather than silently doing
  nothing.

Continuous profiling and the Grafana capabilities legend on the Crew Wall need no
pre-demo step; they are either always running or always visible from page load.

### Manual walkthrough

From the Production Wall's Demo controls panel:

1. Pick a setup and Roll take. A clean take circles once the crew analyzes it.
2. Pick a fault (for example VRAM spike), Arm for next take, then roll again. The
   Supervisor issues a hold or reshoot with timecoded evidence, and First AD pre-stages
   the correction and annotates the Stage Health dashboard.
3. Arm Node death and roll. An alert fires, First AD opens a real Grafana incident,
   pages on-call, and drives it to resolution.
4. Switch to the Crew Wall to see verdict latency against budget, model routing per
   take with the Supervisor's own reasoning, and real per-agent token cost.
5. Wrap shoot. The DIT compiles technical dailies with a Grafana deep-link per shot,
   and the Supervisor writes the end-of-day report.

## License

Apache-2.0, see [LICENSE](LICENSE).
