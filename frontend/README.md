# Frontend — BrainBar dashboard

React + plain JavaScript (Vite), dark control-room UI with two live views over
WebSocket: the **Production Wall** (verdict card, take timeline, coverage map,
incident banner, demo controls, embedded Stage Health panel) and the **Crew Wall**
(verdict latency vs. budget, model routing per take, embedded Crew Health panel).

## Run locally

```bash
cd frontend
npm install
cp .env.example .env   # point at your running backend (see ../backend/README.md)
npm run dev
```

Open the printed local URL. The header's LIVE/DISCONNECTED indicator reflects the
WebSocket connection to the backend's `/stream` endpoint; on load it also hydrates
from `GET /state` so a page refresh doesn't lose the current session.

## Demo mode

The Production Wall's "Demo controls" panel drives the whole reproducible demo
without touching a terminal: pick a setup and roll a take, optionally arm one of the
five stage faults for the next take first, and wrap the shoot to generate dailies
and the end-of-day report.

## Files

- `src/useLiveStream.js` — the WebSocket + REST-hydration hook; owns all live state.
- `src/api.js` — REST calls to the backend.
- `src/walls/` — the two top-level views.
- `src/components/` — verdict card, timeline, coverage map, incident banner, demo
  controls, and the Grafana panel embed helper.
