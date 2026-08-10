"""Model-tier routing: which sub-agents run on Flash vs Pro for a given take.

This is the pre-observability heuristic (Milestone 8). Milestone 11 replaces
`decide_model_tier` with a version that reads the crew's own AI Observability
metrics (verdict latency, cost) back through the Grafana MCP server before each take
and adjusts routing to stay inside the on-set latency budget — the closed
self-governing loop described in architecture/architecture.md.
"""
from __future__ import annotations

from agents.schemas import ModelTier, RoutingDecision

# Coverage types whose loss is expensive to redo (a missed master eats the whole
# setup's schedule) get the stronger model; routine singles/reverses get Flash.
HERO_COVERAGE_TYPES = {"master"}


def decide_model_tier(
    *, take_id: str, coverage_type: str, fault_active: bool
) -> RoutingDecision:
    if fault_active or coverage_type in HERO_COVERAGE_TYPES:
        tier = ModelTier.PRO
        reason = (
            f"coverage_type={coverage_type} is hero coverage or a fault is active this take — "
            "routing to Pro for the stronger diagnosis."
        )
    else:
        tier = ModelTier.FLASH
        reason = f"routine {coverage_type} take, no active fault — routing to Flash to stay inside budget."

    return RoutingDecision(take_id=take_id, agent="technical_director", tier=tier, reason=reason)
