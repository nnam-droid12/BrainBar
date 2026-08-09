# Telemetry schema

This is the single source of truth for every metric, log line, and trace span the Stage
Simulator emits to Grafana Cloud, and that the agent crew queries back through the Grafana
MCP server. The Simulator's emitter code and the Technical Director's PromQL/LogQL/Tempo
queries are both written against these exact names — if a name changes, it changes here first.

## Modeled stage

- 6 nDisplay render nodes: `node-1` … `node-6`.
- Camera at 24 fps; LED wall genlocked at 60 Hz to a shared reference. Per-refresh render
  budget is ~16.6 ms; a frame whose render exceeds budget is dropped/late.
- One camera tracking stream (position + jitter) per active take.
- A shared timecode + genlock reference; individual devices can drift from it.

## Metrics (Mimir, OTLP push, queried via PromQL)

| Metric | Type | Labels | Meaning |
|---|---|---|---|
| `brainbar_render_frame_time_ms` | gauge | `node`, `take_id` | Render time for the most recent frame on this node |
| `brainbar_frame_drops_total` | counter | `node`, `take_id` | Cumulative dropped/late frames |
| `brainbar_node_vram_percent` | gauge | `node` | VRAM utilization |
| `brainbar_node_gpu_util_percent` | gauge | `node` | GPU utilization |
| `brainbar_node_gpu_temp_c` | gauge | `node` | GPU die temperature |
| `brainbar_genlock_drift_us` | gauge | `device` | Genlock drift from reference, microseconds |
| `brainbar_timecode_drift_frames` | gauge | `device` | Timecode drift from reference, frames |
| `brainbar_wall_refresh_hz` | gauge | `wall_region` | Measured wall refresh rate |
| `brainbar_tracking_jitter_mm` | gauge | `camera` | Camera tracking positional jitter |
| `brainbar_tracking_latency_ms` | gauge | `camera` | Camera tracking pipeline latency |
| `brainbar_take_active` | gauge (0/1) | `take_id`, `scene`, `setup` | 1 while a take is rolling |

## Logs (Loki, OTLP push, queried via LogQL)

Stream labels: `{service="stage", node, take_id, level, event_type}`.

| `event_type` | Fields | Meaning |
|---|---|---|
| `slate` | `scene`, `setup`, `take`, `timecode` | Take start |
| `cut` | `timecode` | Take end |
| `warning` | `message`, `metric_ref` | Non-fatal condition, e.g. VRAM high on a node |
| `sync_loss` | `device`, `drift_us` | Genlock/timecode sync loss |
| `cue` | `cue_type` (`dolly`\|`pyro`\|`lighting`), `frame_number` | Scripted effects/camera cue fired |
| `node_down` / `node_up` | `node` | Render node failure / recovery |

## Traces (Tempo, OTLP push)

Root span `frame_render` (attributes: `take_id`, `frame_number`, `node`), with child spans in
pipeline order:

1. `camera_tracking_ingest`
2. `genlock_sync`
3. `ndisplay_render`
4. `composite`
5. `wall_output`

A dropped frame is represented as the `ndisplay_render` span exceeding the 16.6 ms budget, or
an error status on the root `frame_render` span. The Technical Director correlates a metric
spike (e.g. a `brainbar_frame_drops_total` increment) to the trace ID of the frame that caused
it and to the `cue` log line active at that timecode.

## Fault → telemetry signature

| Fault | Primary metric signature | Secondary signal |
|---|---|---|
| VRAM spike on cue | `brainbar_node_vram_percent` > 90% on the affected node during the cue window | `ndisplay_render` span over budget; `brainbar_frame_drops_total` increments; `warning` log |
| Node death | `brainbar_node_*` series stop updating for the node | `node_down` log; Grafana alert fires |
| Genlock/timecode drift | `brainbar_genlock_drift_us` / `brainbar_timecode_drift_frames` climb steadily | `sync_loss` log once past threshold |
| Tracking jitter | `brainbar_tracking_jitter_mm` spikes | `camera_tracking_ingest` span attributes flag out-of-tolerance |
| Thermal throttle | `brainbar_node_gpu_temp_c` climbs; `brainbar_render_frame_time_ms` climbs in step | `warning` log once temp crosses threshold |

## Identifiers shared across signals

- `take_id`: stable ID for one take, e.g. `sc03-setup2-take5`. Present on the relevant metric
  series, the `slate`/`cut` log pair, and every `frame_render` trace for that take's duration —
  this is the join key the Technical Director uses to scope a take window across Mimir, Loki,
  and Tempo.
- `timecode`: SMPTE `HH:MM:SS:FF` at 24 fps, present on slate/cut/cue/sync_loss logs and used to
  align telemetry with the shot-list setup (Continuity) and with dashboard annotations (First AD).
