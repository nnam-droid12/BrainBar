"""The single connection point to the Grafana Cloud MCP server.

Every Grafana tool call any agent makes — Prometheus/Mimir queries, LogQL, Tempo trace
lookups, dashboard/datasource search, annotations, alerting, and incidents (IRM) — goes
through the `McpToolset` built here. ADK auto-discovers the live tool set from the
server at runtime; nothing here hardcodes a tool list.

Two modes (see agents/config.py):
  * "oss" (default, used in deployment): the open-source `grafana/mcp-grafana` server
    run as its own service (Cloud Run), configured with a Grafana service-account
    token so the deployed crew runs unattended. The Cloud Run service itself is
    IAM-protected (not public) since it proxies real Grafana access — when the
    configured URL isn't localhost, this module authenticates to it with a Google
    ID token for the service's own audience, minted from the caller's ambient
    credentials (the Cloud Run/Agent Engine runtime service account when deployed;
    local `gcloud auth application-default login` credentials otherwise).
  * "hosted": the interactive-OAuth `https://mcp.grafana.com/mcp` endpoint. Local dev
    only — it requires a browser login and cannot run unattended.
"""
from __future__ import annotations

import time

import google.auth.transport.requests
import google.oauth2.id_token
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset

from agents.config import config

_id_token_cache: dict[str, tuple[str, float]] = {}
_ID_TOKEN_TTL_SECONDS = 45 * 60  # Google-minted ID tokens are valid ~1h; refresh early.


def _is_local(url: str) -> bool:
    return "localhost" in url or "127.0.0.1" in url


def _cloud_run_id_token(audience: str) -> str:
    cached = _id_token_cache.get(audience)
    if cached and cached[1] > time.time():
        return cached[0]
    token = google.oauth2.id_token.fetch_id_token(
        google.auth.transport.requests.Request(), audience
    )
    _id_token_cache[audience] = (token, time.time() + _ID_TOKEN_TTL_SECONDS)
    return token


def build_grafana_toolset(tool_filter: list[str] | None = None) -> McpToolset:
    """Builds the McpToolset the crew's agents attach as an ADK tool.

    `tool_filter` narrows the tool set to what a specific agent needs (e.g. the First
    AD only needs incident/alerting/annotation tools) — ADK still discovers the full
    live tool set from the server and filters client-side, so a renamed or newly added
    server-side tool is never silently missed, only tools outside the filter are hidden.
    """
    headers: dict[str, str] = {}
    if config.grafana_mcp_mode == "oss" and not _is_local(config.grafana_mcp_url):
        # Audience for a Cloud Run ID token is the service's own base URL, i.e. the
        # MCP URL with the /mcp path stripped.
        audience = config.grafana_mcp_url.rsplit("/mcp", 1)[0]
        headers["Authorization"] = f"Bearer {_cloud_run_id_token(audience)}"

    return McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=config.grafana_mcp_url,
            headers=headers or None,
            timeout=15.0,
        ),
        tool_filter=tool_filter,
        tool_name_prefix="grafana",
    )
