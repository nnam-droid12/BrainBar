"""Direct, server-side Mimir queries for the cockpit's native charts.

This is deliberately separate from agents/mcp_client.py: that's the agent crew's tool
path (ADK-discovered, used for reasoning). This is a plain HTTP query used only to feed
chart data to the frontend — the cockpit can't call Grafana Cloud itself (the service
account token must never reach the browser), so the backend queries Mimir directly with
the same token already used elsewhere for server-side Grafana access, and returns JSON.

Real Grafana Cloud queries, real data — just not through MCP, since MCP is for agent
tool-calling, not for a REST endpoint's read path.
"""
from __future__ import annotations

import httpx

from agents.config import config


async def query_instant(promql: str) -> list[dict]:
    """Runs an instant PromQL query against the stack's default Mimir datasource and
    returns the raw Prometheus API `result` list (empty if Grafana isn't configured or
    the query errors — callers should treat that as "no data yet", not fail the page)."""
    if not config.grafana_cloud_stack_url or not config.grafana_service_account_token:
        return []

    url = f"{config.grafana_cloud_stack_url}/api/datasources/proxy/uid/grafanacloud-prom/api/v1/query"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                url,
                params={"query": promql},
                headers={"Authorization": f"Bearer {config.grafana_service_account_token}"},
            )
            resp.raise_for_status()
            body = resp.json()
    except httpx.HTTPError:
        return []

    if body.get("status") != "success":
        return []
    return body["data"]["result"]
