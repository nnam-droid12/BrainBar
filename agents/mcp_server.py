"""BrainBar as an MCP server, not just an MCP client.

Every other agents/ module is a client of Grafana's MCP server — this module is the
other direction. Technical Director's diagnosis already sits behind a clean, bounded
interface (agents/technical_director/analyze.py's analyze_take): it never dumps raw
telemetry into a caller's context, it queries Grafana itself and returns one structured
TechnicalVerdict. That's what makes exposing it externally safe to do at all — a caller
gets a bounded, purpose-built answer, never a raw connection to Mimir/Loki.

Once that's true, standing up a server is just wrapping the same function ADK's own
Runner already calls. Any MCP-speaking caller — Grafana's own Assistant, a coding agent,
a future tool — can ask "is take X clean?" directly over MCP, with no chat UI, no cut
webhook, and no dashboard required.

Deployed as its own Cloud Run service (deploy/cloud-run/mcp-server/), IAM-protected like
the Grafana MCP proxy this same crew calls into (see agents/mcp_client.py) — a tool
surface the outside world can call needs real access control; a raw SQL connection or an
unauthenticated endpoint would not be safe to hand to a caller you don't control, and
neither is this. Run locally with `python -m agents.mcp_server`.
"""
from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from agents.config import config
from agents.continuity.analyze import analyze_take as analyze_take_creative
from agents.model_armor_client import check_caller_text
from agents.schemas import ModelTier
from agents.technical_director.analyze import analyze_take as analyze_take_technical

_log = logging.getLogger(__name__)

mcp = FastMCP(
    name="brainbar",
    instructions=(
        "BrainBar's own crew reasoning, exposed as tools. diagnose_take_technical and "
        "diagnose_take_creative run the same Technical Director / Continuity analysis "
        "the crew runs on every cut, against live Grafana Cloud telemetry — call them to "
        "ask about a specific take directly, without going through BrainBar's own "
        "cut-webhook pipeline or dashboard."
    ),
)


@mcp.tool()
async def diagnose_take_technical(
    take_id: str,
    scene: str,
    setup_id: str,
    start_timecode: str,
    end_timecode: str,
    start_time_utc: str,
    end_time_utc: str,
    node_ids: list[str],
) -> dict:
    """Runs BrainBar's Technical Director against one take's real Grafana telemetry
    (Mimir frame times/VRAM/drift, Loki stage events, Tempo dropped-frame traces) and
    returns a structured verdict: whether the take is technically clean, cited issues
    with exact numbers, and a one-paragraph summary. Always routes to the fast model
    tier (this is an on-demand diagnostic call, not a routed production take).

    Args:
        take_id: Take identifier, e.g. "sc03-setup1-take1".
        scene: Scene id, e.g. "SC03".
        setup_id: Setup id within the scene, e.g. "1".
        start_timecode: SMPTE start timecode, e.g. "00:00:00:00".
        end_timecode: SMPTE end timecode, e.g. "00:00:12:12".
        start_time_utc: Real RFC3339 start time — used as the actual Grafana query bound.
        end_time_utc: Real RFC3339 end time — used as the actual Grafana query bound.
        node_ids: Render node ids active during the take, e.g. ["node-1", "node-2"].
    """
    await check_caller_text(
        f"take_id={take_id} scene={scene} setup_id={setup_id} node_ids={node_ids}",
        context="diagnose_take_technical",
    )
    verdict = await analyze_take_technical(
        take_id=take_id,
        scene=scene,
        setup_id=setup_id,
        start_timecode=start_timecode,
        end_timecode=end_timecode,
        start_time_utc=start_time_utc,
        end_time_utc=end_time_utc,
        node_ids=node_ids,
        model_tier=ModelTier.FLASH,
    )
    return verdict.model_dump(mode="json")


@mcp.tool()
async def diagnose_take_creative(
    take_id: str,
    scene: str,
    setup_id: str,
    start_timecode: str,
    end_timecode: str,
    start_time_utc: str,
    end_time_utc: str,
) -> dict:
    """Runs BrainBar's Continuity agent against one take: grounds it on the real
    script/shot-list/storyboard/call-sheet via RAG, cross-checks Loki for whether
    scripted cues actually fired, and returns whether the take matches creative intent
    plus what coverage is still owed for the scene.

    Args:
        take_id: Take identifier, e.g. "sc03-setup1-take1".
        scene: Scene id, e.g. "SC03".
        setup_id: Setup id within the scene, e.g. "1".
        start_timecode: SMPTE start timecode, e.g. "00:00:00:00".
        end_timecode: SMPTE end timecode, e.g. "00:00:12:12".
        start_time_utc: Real RFC3339 start time — used as the actual Grafana query bound.
        end_time_utc: Real RFC3339 end time — used as the actual Grafana query bound.
    """
    await check_caller_text(
        f"take_id={take_id} scene={scene} setup_id={setup_id}",
        context="diagnose_take_creative",
    )
    verdict = await analyze_take_creative(
        take_id=take_id,
        scene=scene,
        setup_id=setup_id,
        start_timecode=start_timecode,
        end_timecode=end_timecode,
        start_time_utc=start_time_utc,
        end_time_utc=end_time_utc,
        model_tier=ModelTier.FLASH,
    )
    return verdict.model_dump(mode="json")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    port = int(__import__("os").environ.get("PORT", 8000))
    mcp.settings.host = "0.0.0.0"
    mcp.settings.port = port
    _log.info("BrainBar MCP server starting on :%d (Cloud Run project=%s)", port, config.google_cloud_project)
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
