"""The single connection point to the Grafana Cloud MCP server.

Every Grafana tool call any agent makes — Prometheus/Mimir queries, LogQL, Tempo trace
lookups, dashboard/datasource search, annotations, alerting, and incidents (IRM) — goes
through the `McpToolset` built here. ADK auto-discovers the live tool set from the
server at runtime; nothing here hardcodes a tool list.

Two modes (see agents/config.py):
  * "oss" (default, used in deployment): the open-source `grafana/mcp-grafana` server
    run as its own service (Cloud Run), configured with a Grafana service-account
    token so the deployed crew runs unattended.
  * "hosted": the interactive-OAuth `https://mcp.grafana.com/mcp` endpoint. Local dev
    only — it requires a browser login and cannot run unattended.
"""
from __future__ import annotations

from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset

from agents.config import config


def build_grafana_toolset(tool_filter: list[str] | None = None) -> McpToolset:
    """Builds the McpToolset the crew's agents attach as an ADK tool.

    `tool_filter` narrows the tool set to what a specific agent needs (e.g. the First
    AD only needs incident/alerting/annotation tools) — ADK still discovers the full
    live tool set from the server and filters client-side, so a renamed or newly added
    server-side tool is never silently missed, only tools outside the filter are hidden.
    """
    headers = {}
    if config.grafana_mcp_mode == "oss" and config.grafana_service_account_token:
        # The OSS server can also be configured to require this itself; sending it as
        # a bearer header too lets the same server be shared behind a proxy that
        # expects per-request auth.
        headers["Authorization"] = f"Bearer {config.grafana_service_account_token}"

    return McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=config.grafana_mcp_url,
            headers=headers or None,
            timeout=15.0,
        ),
        tool_filter=tool_filter,
        tool_name_prefix="grafana",
    )
