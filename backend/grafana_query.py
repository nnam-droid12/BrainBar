"""Direct, server-side Mimir queries for the frontend's native charts.

This is deliberately separate from agents/mcp_client.py: that's the agent crew's tool
path (ADK-discovered, used for reasoning). This is a plain HTTP query used only to feed
chart data to the frontend — the frontend can't call Grafana Cloud itself (the service
account token must never reach the browser), so the backend queries Mimir directly with
the same token already used elsewhere for server-side Grafana access, and returns JSON.

Real Grafana Cloud queries, real data — just not through MCP, since MCP is for agent
tool-calling, not for a REST endpoint's read path.
"""
from __future__ import annotations

import logging

import httpx

from agents.config import config

_log = logging.getLogger(__name__)


async def query_instant(promql: str) -> list[dict]:
    """Runs an instant PromQL query against the stack's default Mimir datasource and
    returns the raw Prometheus API `result` list (empty if Grafana isn't configured or
    the query errors — callers should treat that as "no data yet", not fail the page).
    Logs the real failure reason rather than swallowing it silently, so a
    misconfiguration shows up in Cloud Run logs instead of just looking like "no data"."""
    if not config.grafana_cloud_stack_url or not config.grafana_service_account_token:
        _log.warning("grafana_query: stack URL or service-account token not configured")
        return []

    url = f"{config.grafana_cloud_stack_url}/api/datasources/proxy/uid/grafanacloud-prom/api/v1/query"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(
                url,
                data={"query": promql},
                headers={"Authorization": f"Bearer {config.grafana_service_account_token}"},
            )
            resp.raise_for_status()
            body = resp.json()
    except httpx.HTTPError as exc:
        _log.warning("grafana_query failed for %r: %s", promql, exc)
        return []

    if body.get("status") != "success":
        _log.warning("grafana_query non-success response for %r: %s", promql, body)
        return []
    return body["data"]["result"]
