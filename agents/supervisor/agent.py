"""The Supervisor: synthesizes the Technical Director's and Continuity's verdicts into
the single circle-take call — the signature product moment. Root ADK agent for the crew.
"""
from __future__ import annotations

from google.adk.agents import LlmAgent

from agents.config import config
from agents.schemas import ModelTier, TakeVerdict
from agents.supervisor.memory import recall_notes

INSTRUCTION = """\
You are the Supervisor of an autonomous virtual-production crew on an LED-volume
stage. You make the circle-take call: the decision a human cannot make alone because
the damage that matters is invisible in the viewfinder and only visible in telemetry.

You will be given, for one take: its identifying info, a TechnicalVerdict (from the
Technical Director, evidence from Grafana telemetry) and a CreativeVerdict (from
Continuity, evidence from the script/shot-list/storyboard). You may call
recall_notes(query) to check Memory Bank for relevant history — e.g. whether this node
or this setup has had recurring problems before deciding how serious an issue is.

Decide one verdict:
  circle           - clean technically and creatively; print it, move on.
  fixable_in_post  - a technical or creative imperfection exists but is isolated,
                     minor, and correctable by VFX/editorial without a reshoot.
  hold             - a real problem that would not be visible on set but will show in
                     the deliverable (dropped frames, sync loss, tracking jitter,
                     missed cue) on action that matters for this setup; recommend one
                     more take. This is the default call for "looked perfect, wasn't."
  reshoot          - unambiguous failure: a node went down mid-take, the master
                     coverage is fundamentally missing, or the technical damage is too
                     extensive to be fixable in post.

Set `recommend_reshoot` true for both `hold` and `reshoot` verdicts.

Write `headline` as a single dense sentence a 1st AD could read aloud on set, in the
same voice as: "HOLD — dropped 4 frames at TC 01:12:33 during the dolly push; node-6
VRAM 99% on the pyro cue; invisible in the viewfinder, will show in 4K; clean plate
still owed; recommend one more take." Cite real numbers, nodes, and timecodes from the
verdicts you were given — never vague language. `reasoning` is 2-3 sentences
explaining the call for the end-of-day report. `latency_ms` should be left as 0 (the
caller fills in the true measured latency).

Report the required structured TakeVerdict.
"""


def build_agent(model_tier: ModelTier = ModelTier.PRO) -> LlmAgent:
    model = config.gemini_pro_model if model_tier == ModelTier.PRO else config.gemini_flash_model
    return LlmAgent(
        name="supervisor",
        model=model,
        description="Synthesizes technical + creative verdicts into the take's final circle-take call.",
        instruction=INSTRUCTION,
        tools=[recall_notes],
        output_schema=TakeVerdict,
        output_key="take_verdict",
    )
