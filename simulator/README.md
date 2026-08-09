# Stage Simulator

Plays the role of a real LED-volume stage: a 6-node nDisplay render cluster, camera
tracking, genlock/timecode reference, and a fault injector. This is the only simulated
part of BrainBar — the telemetry it emits is real data, pushed via OTLP to a real
Grafana Cloud stack (Mimir metrics, Loki logs, Tempo traces).

## Run locally

```bash
cd BrainBar
python -m venv .venv
.venv/Scripts/activate        # .venv/bin/activate on macOS/Linux
pip install -r simulator/requirements.txt
cp .env.example .env           # fill in OTLP_ENDPOINT / OTLP_INSTANCE_ID / OTLP_API_KEY
python -m simulator.main       # serves the control API on :9000
```

## Control API

| Endpoint | Purpose |
|---|---|
| `GET /control/shoot` | List the scene/setups loaded from `shoot_script.yaml` |
| `GET /control/status` | Current take, frame number, armed/active fault |
| `POST /control/take/start {setup_id}` | Roll a take for the given setup |
| `POST /control/take/stop` | Cut the current take early |
| `POST /control/faults/next {fault_type, node?}` | Arm a fault for the next take rolled |
| `POST /control/faults/clear` | Disarm any pending fault |

Fault types: `vram_spike`, `node_death`, `genlock_drift`, `tracking_jitter`, `thermal_throttle`.

Example — arm the hero-moment VRAM spike on node-6, then roll:

```bash
curl -X POST localhost:9000/control/faults/next -H 'content-type: application/json' \
  -d '{"fault_type": "vram_spike", "node": "node-6"}'
curl -X POST localhost:9000/control/take/start -H 'content-type: application/json' \
  -d '{"setup_id": "1"}'
```

## Files

- `shoot_script.yaml` — declarative scene/setups/cues (must stay aligned with `assets/`).
- `models.py` — shoot-script and take-state data model.
- `faults.py` — the fault injector.
- `telemetry.py` — OpenTelemetry wiring to Grafana Cloud (see `../architecture/telemetry-schema.md`).
- `emitter.py` — the take runner: paces frames at real 24fps and emits telemetry each frame.
- `control_api.py` / `main.py` — FastAPI demo control plane.
