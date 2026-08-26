# Demo path: the hosted, OAuth Grafana Cloud MCP server

BrainBar's deployed crew runs against the open-source `grafana/mcp-grafana` server on
Cloud Run with a service-account token (see `scripts/run_grafana_mcp_oss.md`) — IAM-
protected, unattended, no browser required, which is what production needs. That's a
deliberate tradeoff, not the only supported path: `agents/mcp_client.py` also supports
Grafana's hosted `https://mcp.grafana.com/mcp` endpoint, authorized interactively over
OAuth as *your own* Grafana Cloud identity rather than a shared service-account token —
no service account, no static credential, exactly your permissions on the stack, and
the browser consent only has to happen once per session.

This path is local-dev-only (it needs an interactive browser login, so it can't run
unattended on Cloud Run), which is exactly why it's worth running once live during a
demo/judging walkthrough: it's the more legible "authorize as yourself" story, even
though the deployed system runs the IAM path day-to-day.

## Running it

```
GRAFANA_MCP_MODE=hosted
GRAFANA_MCP_URL=https://mcp.grafana.com/mcp
```

Set those two in `.env` (or export them) instead of the OSS `GRAFANA_MCP_URL=http://localhost:8000/mcp`,
then run the same smoke test used to verify the OSS path:

```bash
python -m scripts.list_grafana_mcp_tools
```

The first call opens a browser window for Grafana Cloud login/consent — approve once,
and the session persists for the rest of that run. On success this prints every tool
the hosted MCP server discovers, the same live discovery `agents/mcp_client.py`'s
docstring describes for the OSS path — nothing is hardcoded either way.

## Why this is worth narrating, not just running

- **No service-account token in the picture at all** for this path — the crew is
  authorized as whoever approved the browser consent, scoped to exactly that person's
  Grafana Cloud permissions, not a standing credential that outlives the session.
- **Same crew, same tools, same tool-filter-per-agent code** — switching
  `GRAFANA_MCP_MODE` doesn't touch `agents/technical_director/agent.py`,
  `agents/first_ad/agent.py`, or any other agent; `build_grafana_toolset()` in
  `agents/mcp_client.py` is the only place that knows which mode is active.
- **Why production doesn't use this path**: an interactive browser OAuth flow cannot
  run unattended on Cloud Run — there's no browser to click "Allow" in a deployed
  service, which is why the OSS+IAM path (`agents/mcp_client.py`'s Google-ID-token
  authentication to a private Cloud Run MCP server) is what's actually deployed. Both
  paths exist in the same codebase on purpose: the tradeoff between them is itself part
  of the story worth telling, not something to pick silently.
