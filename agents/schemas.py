"""Shared Pydantic contracts passed between the five agents.

Every agent returns one of these instead of free-text, so the Supervisor can
synthesize a verdict programmatically and the backend/frontend can render it without
re-parsing prose. Keep this module dependency-free (no ADK/Grafana/GCP imports) so any
agent or the backend can import it cheaply.
"""
from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class Verdict(StrEnum):
    CIRCLE = "circle"
    HOLD = "hold"
    RESHOOT = "reshoot"
    FIXABLE_IN_POST = "fixable_in_post"


class ModelTier(StrEnum):
    FLASH = "flash"
    PRO = "pro"


# --- Technical Director -----------------------------------------------------------


class TechnicalIssue(BaseModel):
    node: str
    timecode: str
    metric: str
    value: float
    threshold: float
    trace_id: str | None = None
    root_cause: str
    description: str


class TechnicalVerdict(BaseModel):
    take_id: str
    clean: bool
    issues: list[TechnicalIssue] = Field(default_factory=list)
    frame_drop_count: int = 0
    peak_vram_percent: float | None = None
    peak_genlock_drift_us: float | None = None
    summary: str
    model_tier_used: ModelTier
    # Grafana Sift second opinion (see agents/technical_director/agent.py) — structured
    # so the frontend can show it as its own element instead of hoping it's mentioned
    # in `summary`'s free text.
    sift_checked: bool = False
    sift_investigation_found: bool = False
    sift_note: str = ""
    # Structural evidence-grounding gate (see analyze.py's _validate_evidence_grounding)
    # — a code-level check every model tier is forced through, distinct from the async
    # Grafana Agent Observability LLM-judge that grades the same thing.
    evidence_validated: bool = True
    evidence_validation_note: str = ""


# --- Continuity ---------------------------------------------------------------------


class CoverageItem(BaseModel):
    setup_id: str
    coverage_type: str  # master | single | reverse | insert | clean_plate
    captured: bool
    take_ids: list[str] = Field(default_factory=list)


class ContinuityFlag(BaseModel):
    take_id: str
    issue: str
    severity: str  # info | warning | critical


class CreativeVerdict(BaseModel):
    take_id: str
    setup_id: str
    intended_framing: str
    intended_movement: str
    matches_intent: bool
    coverage_owed: list[str] = Field(default_factory=list)
    flags: list[ContinuityFlag] = Field(default_factory=list)
    summary: str


# --- Supervisor -----------------------------------------------------------------------


class TakeVerdict(BaseModel):
    take_id: str
    scene: str
    setup_id: str
    take_number: int
    verdict: Verdict
    headline: str
    reasoning: str
    technical: TechnicalVerdict
    creative: CreativeVerdict
    recommend_reshoot: bool
    latency_ms: float
    grafana_deeplink: str | None = None


# --- First AD -----------------------------------------------------------------------


class ActionType(StrEnum):
    PRE_STAGE_RESHOOT = "pre_stage_reshoot"
    OPEN_INCIDENT = "open_incident"
    SILENCE_ALERT = "silence_alert"
    RESOLVE_INCIDENT = "resolve_incident"
    ANNOTATE_DASHBOARD = "annotate_dashboard"
    PREVENTIVE_LOAD_SHED = "preventive_load_shed"
    PAGE_ONCALL = "page_oncall"


class Action(BaseModel):
    type: ActionType
    rationale: str
    target: str
    grafana_ref: str | None = None
    result: str


class ActionLog(BaseModel):
    take_id: str
    actions: list[Action] = Field(default_factory=list)


# --- DIT -----------------------------------------------------------------------------


class DailyShot(BaseModel):
    take_id: str
    scene: str
    setup_id: str
    verdict: Verdict
    evidence_summary: str
    grafana_deeplink: str


class DailiesPackage(BaseModel):
    scene: str
    shots: list[DailyShot] = Field(default_factory=list)
    generated_at: str
    gcs_uri: str | None = None


# --- Crew self-observability (Section 9) -------------------------------------------


class RoutingDecision(BaseModel):
    take_id: str
    agent: str
    tier: ModelTier
    reason: str
