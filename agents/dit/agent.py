"""The DIT: assembles technical dailies — one deep-linked, evidenced entry per shot,
handed to editorial/VFX/color at wrap.
"""
from __future__ import annotations

from google.adk.agents import LlmAgent

from agents.config import config
from agents.mcp_client import build_grafana_toolset
from agents.schemas import DailiesPackage, ModelTier

GRAFANA_TOOL_FILTER = [
    "generate_deeplink",
    "search_dashboards",
    "get_dashboard_summary",
]

INSTRUCTION = """\
You are the DIT (data-wrangler / post-liaison) on an LED-volume virtual-production
stage. At wrap, you assemble the technical dailies package editorial, VFX, and color
will use to decide what needs attention before the shoot leaves the stage.

You will be given a list of this scene's take verdicts (take_id, scene, setup_id,
verdict, headline, start/end timecode). For each take:
1. Find the Stage Health dashboard (search_dashboards if you don't already know its
   UID) and generate a deep-link (generate_deeplink) scoped to that take's timecode
   window, so a click lands exactly on the relevant telemetry.
2. Write a one-sentence evidence_summary citing the concrete technical/creative
   reason for the verdict (reuse the headline you were given — don't invent new
   claims).

Report the required structured DailiesPackage: one DailyShot per take. Leave
`generated_at` as an empty string and `gcs_uri` null — the caller fills both in
after you respond (you have no reliable access to the actual wall-clock time).
"""


def build_agent(model_tier: ModelTier = ModelTier.FLASH) -> LlmAgent:
    model = config.gemini_pro_model if model_tier == ModelTier.PRO else config.gemini_flash_model
    return LlmAgent(
        name="dit",
        model=model,
        description="Assembles technical dailies with per-shot Grafana deep-links.",
        instruction=INSTRUCTION,
        tools=[build_grafana_toolset(tool_filter=GRAFANA_TOOL_FILTER)],
        output_schema=DailiesPackage,
        output_key="dailies_package",
    )
