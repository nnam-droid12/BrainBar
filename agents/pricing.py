"""Gemini token pricing, so the crew's own token usage (agents/observability.py) can be
turned into an estimated dollar cost instead of a raw token count nobody on set can
size up at a glance.

List prices for the Vertex AI "≤200k context" tier as of this writing (per 1M tokens);
BrainBar's per-take prompts are well under that threshold. These are estimates for
on-set cost governance, not a billing-grade reconciliation against the Cloud Billing
API — check current Vertex AI pricing before treating this as exact. Keep this table in
sync with the literal PromQL constants in
simulator/grafana_provisioning/crew_health_dashboard.py, which computes the same
estimate for the Crew Health dashboard directly from Prometheus (no Python in that
path) — both read from agents/config.py's gemini_pro_model/gemini_flash_model so a
model swap only needs a price added here, not a rename in two places.

Dependency-free (no ADK/Grafana/GCP imports), same rule as agents/schemas.py, so the
backend can import this cheaply too.
"""
from __future__ import annotations

from agents.config import config

# USD per 1,000 tokens.
_PRICE_PER_1K_USD: dict[str, dict[str, float]] = {
    config.gemini_pro_model: {"input": 0.00125, "output": 0.010},
    config.gemini_flash_model: {"input": 0.00030, "output": 0.0025},
}


def estimate_cost_usd(model: str, *, input_tokens: float, output_tokens: float) -> float:
    """Returns 0.0 for an unrecognized model rather than raising — a cost estimate is
    advisory, and a model this table hasn't been updated for shouldn't break the page
    that displays it."""
    price = _PRICE_PER_1K_USD.get(model)
    if price is None:
        return 0.0
    return (input_tokens / 1000) * price["input"] + (output_tokens / 1000) * price["output"]
