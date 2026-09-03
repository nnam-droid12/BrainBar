"""Agent Observability (Sigil): richer, purpose-built telemetry than the raw OTel
GenAI metrics agents/observability.py already exports — every agent call is grouped
into a conversation (one per take), every tool call is captured with its own
input/output/duration, and both land in Grafana Cloud's native AI Observability app
(Overview/Performance/Errors/Usage/Tools/Evaluation tabs) instead of only custom PromQL
dashboards.

This is additive, not a replacement: agents/observability.py's raw OTel export keeps
working regardless of whether this is configured, and every call site here degrades to
a no-op (returns None) rather than failing the crew if it isn't set up.

Requires a Grafana Cloud Access Policy Token scoped `sigil:write` and the Agent
Observability API endpoint from the stack's Configuration page — both distinct from the
OTLP_* credentials agents/observability.py uses (different product surface, different
scope). See README's "Agent Observability (Sigil)" section for the one-time Grafana
Cloud portal setup this can't do on its own.
"""
from __future__ import annotations

import logging

from agents.config import config

_log = logging.getLogger(__name__)

_client = None
_client_built = False


def get_sigil_client():
    """Returns the singleton Sigil `Client`, or None if not configured.

    Every call site treats None as "skip this telemetry" — never as an error. Built
    lazily and cached: constructing a Client spins up a background export queue, so it
    must happen at most once per process, not per agent call.
    """
    global _client, _client_built
    if _client_built:
        return _client
    _client_built = True

    if not (config.sigil_endpoint and config.sigil_instance_id and config.sigil_api_key):
        _log.warning(
            "Sigil client disabled — SIGIL_ENDPOINT/SIGIL_INSTANCE_ID/SIGIL_API_KEY not "
            "all set. Agent Observability (conversations, per-tool traces, evaluations) "
            "won't appear in Grafana Cloud until these are configured — see README."
        )
        return None

    from sigil_sdk import ApiConfig, AuthConfig, Client, ClientConfig, ContentCaptureMode, GenerationExportConfig

    _client = Client(
        ClientConfig(
            generation_export=GenerationExportConfig(
                protocol="http",
                endpoint=config.sigil_endpoint,
                auth=AuthConfig(
                    mode="basic",
                    tenant_id=config.sigil_instance_id,
                    basic_password=config.sigil_api_key,
                ),
            ),
            # ClientConfig.api is a *separate* endpoint from generation_export above —
            # it's what submit_conversation_rating/get_conversation/the experiments API
            # actually read (self._config.api.endpoint, not generation_export.endpoint).
            # Its default is ApiConfig(endpoint="http://localhost:8080") — which happens
            # to be BrainBar's own backend port — so leaving it unset doesn't fail loudly,
            # it silently points every rating/experiments call at the wrong service.
            # Confirmed live: this was the actual cause of every "connection refused" /
            # timeout on rate_take_conversation, not a real Grafana Cloud issue.
            api=ApiConfig(endpoint=config.sigil_endpoint),
            content_capture=ContentCaptureMode.FULL,
        )
    )
    _log.info("Sigil client initialized — endpoint=%s", config.sigil_endpoint)
    return _client


def rate_take_conversation(*, take_id: str, success: bool, comment: str) -> None:
    """Submits BrainBar's own GOOD/BAD signal for a take's conversation: did the whole
    cut-to-verdict-to-actions pipeline complete without an unhandled error, or not.

    This is deliberately a simple operational-health signal, not a reasoning-quality
    grade — Grafana Cloud's own AI-judge evaluations (configured in the portal, see
    README) are better positioned to grade whether a verdict was well-reasoned than a
    heuristic here could be. This just makes sure a real pipeline failure (a 429 that
    exhausted every retry, a malformed tool call) shows up as a rated bad conversation
    in the Evaluation tab, not just a log line.
    """
    client = get_sigil_client()
    if client is None:
        return

    import uuid

    from sigil_sdk import ConversationRatingInput, ConversationRatingValue

    try:
        client.submit_conversation_rating(
            conversation_id=take_id,
            rating=ConversationRatingInput(
                rating_id=uuid.uuid4().hex,
                rating=ConversationRatingValue.GOOD if success else ConversationRatingValue.BAD,
                comment=comment,
                rater_id="brainbar-pipeline",
                source="automated",
            ),
        )
    except Exception:
        _log.exception("Sigil conversation rating submission failed for take_id=%s (non-fatal)", take_id)
