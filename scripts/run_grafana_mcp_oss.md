# Running the OSS Grafana MCP server locally

BrainBar defaults to the open-source [`grafana/mcp-grafana`](https://github.com/grafana/mcp-grafana)
server so the deployed crew can run unattended with a service-account token, instead of
the hosted `https://mcp.grafana.com/mcp` endpoint (which requires an interactive browser
OAuth login and is local-dev-only).

## 1. Create a Grafana Cloud service account token

In your Grafana Cloud stack: **Administration → Service accounts → Add service account**,
role **Editor**, then **Add service account token**. Put the stack URL and token in `.env`:

```
GRAFANA_CLOUD_STACK_URL=https://your-stack.grafana.net
GRAFANA_SERVICE_ACCOUNT_TOKEN=glsa_...
GRAFANA_MCP_MODE=oss
GRAFANA_MCP_URL=http://localhost:8000/mcp
```

## 2. Run the server (Docker)

```bash
docker run --rm -p 8000:8000 \
  -e GRAFANA_URL="$GRAFANA_CLOUD_STACK_URL" \
  -e GRAFANA_SERVICE_ACCOUNT_TOKEN="$GRAFANA_SERVICE_ACCOUNT_TOKEN" \
  mcp/grafana -t streamable-http --address :8000 --allowed-hosts "*" --allowed-origins "*"
```

`--allowed-hosts`/`--allowed-origins` default to loopback variants of `--address`, which
only matches if you connect on the exact same host:port the container thinks it's bound
to. If you publish the container on a different host port (e.g. `-p 8123:8000`) or run
it behind Cloud Run, the default allowlist rejects every request with a bare `403
Forbidden` and no server-side log line — pass `"*"` for local/dev, and something more
specific (your actual public hostname) once deployed. This is the same image
`deploy/cloud-run/grafana-mcp/` deploys to Cloud Run for the hosted build — locally it
just runs on your machine.

## 3. Verify the crew can see it

```bash
python -m scripts.list_grafana_mcp_tools
```

This connects via ADK's `McpToolset` (see `agents/mcp_client.py`) and prints every tool
the live server exposes — Prometheus/Mimir query tools, LogQL tools, Tempo trace tools,
dashboard/datasource search, annotations, alerting, and incident (IRM) tools. The agent
crew never hardcodes this list; it's discovered fresh from the server every time.
