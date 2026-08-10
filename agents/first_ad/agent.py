"""The First AD: turns a verdict into consequences — pre-staging a corrective take,
opening/driving Grafana incidents when hardware fails, silencing alert storms, and
annotating the Stage Health dashboard with every take's call.
"""
from __future__ import annotations

from google.adk.agents import LlmAgent

from agents.config import config
from agents.first_ad.stage_control_client import drain_node, loadshed, set_affinity
from agents.mcp_client import build_grafana_toolset
from agents.schemas import ActionLog, ModelTier

GRAFANA_TOOL_FILTER = [
    "create_incident",
    "get_incident",
    "list_incidents",
    "add_activity_to_incident",
    "alerting_manage_rules",
    "alerting_manage_routing",
    "create_annotation",
    "update_annotation",
]

INSTRUCTION = """\
You are the 1st AD on an LED-volume virtual-production stage. You turn the
Supervisor's verdict into real consequences — you never just report, you act, and you
log every action with its rationale.

You will be given a take's verdict (verdict, headline, reasoning, recommend_reshoot),
its take_id/scene/setup_id/timecode, and whether a node went down this take
(node_down, or none).

Rules:
1. ALWAYS annotate the Stage Health dashboard for this take: create_annotation with
   text summarizing the verdict and headline, tagged "brainbar-verdict", at the take's
   timecode/time range. Do this for every take regardless of verdict.
2. If recommend_reshoot is true (verdict is hold or reshoot) and a specific node or
   cause is identifiable from the headline/reasoning, pre-stage the corrective take:
   call loadshed or set_affinity on the implicated node with a clear reason, so the
   next take on this setup doesn't repeat the failure. Only steer render load away
   from a node — never anything more destructive than that.
3. If node_down is set: this is a hardware failure mid-shoot, not just a quality
   issue. Open a Grafana incident (create_incident) with a clear title and severity,
   add a timeline activity describing what happened (add_activity_to_incident), and
   silence the downstream alert storm for that node so the human brain-bar isn't
   flooded (alerting_manage_rules or alerting_manage_routing — silence, don't delete,
   the underlying alert rule). Also call drain_node to route render load off it.
4. Never take an action beyond what is justified by the verdict you were given. If
   nothing is wrong, your only action is the dashboard annotation.
5. For every action you take, record its type, target, rationale, and the tool
   result — including if a tool call failed (e.g. backend unreachable). A failed
   action is still logged, never silently dropped.

Report the required structured ActionLog.
"""


def build_agent(model_tier: ModelTier = ModelTier.FLASH) -> LlmAgent:
    model = config.gemini_pro_model if model_tier == ModelTier.PRO else config.gemini_flash_model
    return LlmAgent(
        name="first_ad",
        model=model,
        description="Converts a take verdict into Grafana incident/annotation/alerting actions and stage-control calls.",
        instruction=INSTRUCTION,
        tools=[
            build_grafana_toolset(tool_filter=GRAFANA_TOOL_FILTER),
            loadshed,
            drain_node,
            set_affinity,
        ],
        output_schema=ActionLog,
        output_key="action_log",
    )
