"""Model-tier routing: which sub-agents run on Flash vs Pro for a given take.

`decide_model_tier` is the base heuristic, plus the manual force_flash_only kill-switch
in agents/config.py for a known, ongoing Pro-quota outage. `decide_model_tier_observed`
wraps it with the self-governing loop: it reads the crew's own recent verdict latency
(agents/supervisor/latency_check.py) and recent Pro-tier 429s
(agents/supervisor/quota_check.py) back through the Grafana MCP server — both querying
metrics agents/observability.py exports — and downgrades a Pro routing decision to Flash
when the crew is already running behind budget, or when Pro has been erroring, favoring
finishing the take over a call that's likely to fail or blow the latency budget. The
quota check means that once the manual override in agents/config.py is flipped back off,
the crew still notices live if Pro is still actually broken, instead of trusting it
blind. This is the closed loop described in architecture/architecture.md: the crew
watching the shoot, and watching itself.
"""
from __future__ import annotations

import logging

from agents.config import config
from agents.observability import record_routing_decision
from agents.schemas import ModelTier, RoutingDecision
from agents.supervisor.latency_check import check_recent_latency
from agents.supervisor.quota_check import check_recent_pro_quota

_log = logging.getLogger(__name__)

# Coverage types whose loss is expensive to redo (a missed master eats the whole
# setup's schedule) get the stronger model; routine singles/reverses get Flash.
HERO_COVERAGE_TYPES = {"master"}


def decide_model_tier(
    *, take_id: str, coverage_type: str, fault_active: bool
) -> RoutingDecision:
    if config.force_flash_only:
        return RoutingDecision(
            take_id=take_id,
            agent="technical_director",
            tier=ModelTier.FLASH,
            reason="force_flash_only is set (Pro-tier quota currently exhausted) — routing to Flash.",
        )

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

    # Quota health matters even on a fault-active hero take: a Pro call that's going to
    # 429 anyway is strictly worse than a Flash diagnosis, so this check isn't gated on
    # `not fault_active` the way the latency check below is.
    if decision.tier == ModelTier.PRO:
        try:
            quota = await check_recent_pro_quota()
        except Exception:
            _log.exception("quota self-check failed (non-fatal) — using base heuristic routing")
            quota = None

        if quota and not quota.quota_healthy:
            decision = RoutingDecision(
                take_id=take_id,
                agent="technical_director",
                tier=ModelTier.FLASH,
                reason=(
                    f"recent Pro-tier quota errors detected ({quota.recent_429_count} in the "
                    "last 10 minutes) — downgrading to Flash to avoid a call likely to fail."
                ),
            )

    if decision.tier == ModelTier.PRO and not fault_active:
        try:
            check = await check_recent_latency()
        except Exception:
            _log.exception("latency self-check failed (non-fatal) — using base heuristic routing")
            check = None

        if check and not check.within_budget:
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
