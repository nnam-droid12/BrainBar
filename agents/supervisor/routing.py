"""Model-tier routing: which sub-agents run on Flash vs Pro for a given take.

`decide_model_tier` is the base heuristic. `decide_model_tier_observed` wraps it with
the self-governing loop: it reads the crew's own recent verdict latency back through
the Grafana MCP server (agents/supervisor/latency_check.py, querying the metric
agents/observability.py exports) and downgrades hero-coverage routing to Flash when
the crew is already running behind budget — favoring finishing the take over the
stronger model. This is the closed loop described in architecture/architecture.md:
the crew watching the shoot, and watching itself.
"""
from __future__ import annotations

import logging

from agents.observability import record_routing_decision
from agents.schemas import ModelTier, RoutingDecision
from agents.supervisor.latency_check import check_recent_latency

_log = logging.getLogger(__name__)

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


async def decide_model_tier_observed(
    *, take_id: str, coverage_type: str, fault_active: bool
) -> RoutingDecision:
    decision = decide_model_tier(
        take_id=take_id, coverage_type=coverage_type, fault_active=fault_active
    )

    try:
        check = await check_recent_latency()
    except Exception:
        _log.exception("latency self-check failed (non-fatal) — using base heuristic routing")
        check = None

    if check and not check.within_budget and decision.tier == ModelTier.PRO and not fault_active:
        decision = RoutingDecision(
            take_id=take_id,
            agent="technical_director",
            tier=ModelTier.FLASH,
            reason=(
                f"recent p95 verdict latency ({check.recent_p95_latency_ms}ms) is over budget — "
                "downgrading to Flash on this non-fault hero take to recover headroom."
            ),
        )

    record_routing_decision(agent=decision.agent, tier=decision.tier.value, take_id=take_id)
    return decision
