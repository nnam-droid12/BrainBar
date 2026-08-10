"""Connects to the live Grafana MCP server via ADK and lists every discovered tool.

This is the milestone-5 smoke test: proof the crew's MCP connection is real, not
stubbed. Run it once a Grafana MCP server is reachable at GRAFANA_MCP_URL —
either the OSS `grafana/mcp-grafana` server (see scripts/run_grafana_mcp_oss.md)
or, for local dev, the hosted `https://mcp.grafana.com/mcp` endpoint after an
interactive OAuth login.

    python -m scripts.list_grafana_mcp_tools
"""
from __future__ import annotations

import asyncio

from agents.mcp_client import build_grafana_toolset


async def main() -> None:
    toolset = build_grafana_toolset()
    try:
        tools = await toolset.get_tools()
        print(f"Connected to Grafana MCP server — {len(tools)} tools discovered:\n")
        for tool in tools:
            description = (tool.description or "").strip().splitlines()[0] if tool.description else ""
            print(f"  {tool.name:40s} {description}")
    finally:
        await toolset.close()


if __name__ == "__main__":
    asyncio.run(main())
