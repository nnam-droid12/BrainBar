"""Model Armor: screens caller-supplied text before it reaches a Gemini prompt.

Every other agents/ module trusts its own inputs — BrainBar's own backend constructs
the take metadata that gets interpolated into Technical Director's and Continuity's
prompts. agents/mcp_server.py breaks that assumption: it's a public MCP tool surface,
and take_id/scene/setup_id there come directly from whatever external caller invokes
it, not from BrainBar's own pipeline. Those strings get interpolated into an LLM
prompt the same way internal ones do, so a caller BrainBar doesn't control has a real
prompt-injection surface to try.

This module is that check, run once per external tool call before the take metadata
ever reaches analyze_take_technical/analyze_take_creative. It is deliberately narrow:
it only screens the free-text fields a caller controls, not Grafana's own telemetry
(that's already bounded by analyze_take's own structured output, per
agents/mcp_server.py's docstring).

Requires a Model Armor template already created in the Cloud project (a one-time
gcloud/Console action, not something this module can do — see the README's Model
Armor section) and MODEL_ARMOR_TEMPLATE/MODEL_ARMOR_LOCATION set. Without those, this
degrades to a no-op — logged once, never a hard failure for local dev without the
template configured — but note that's a real tradeoff, not just a convenience: unlike
this crew's telemetry integrations, this one is a security control, so leaving it
unconfigured in a real deployment means the public MCP surface runs unguarded, not
degraded-but-safe.
"""
from __future__ import annotations

import logging

from agents.config import config

_log = logging.getLogger(__name__)

_client = None
_client_built = False


class PromptRejected(Exception):
    """Raised when Model Armor finds a match (prompt injection, jailbreak, etc.) in
    caller-supplied text. agents/mcp_server.py lets this propagate as a tool error —
    the caller gets told their input was rejected, not a fabricated verdict."""


def _get_client():
    global _client, _client_built
    if _client_built:
        return _client
    _client_built = True

    if not (config.model_armor_template and config.model_armor_location):
        _log.warning(
            "Model Armor disabled — MODEL_ARMOR_TEMPLATE/MODEL_ARMOR_LOCATION not "
            "set. agents/mcp_server.py's public tool surface is running without a "
            "prompt-injection screen. See README's Model Armor section."
        )
        return None

    from google.api_core.client_options import ClientOptions
    from google.cloud import modelarmor_v1

    _client = modelarmor_v1.ModelArmorAsyncClient(
        client_options=ClientOptions(
            api_endpoint=f"modelarmor.{config.model_armor_location}.rep.googleapis.com"
        )
    )
    _log.info("Model Armor client initialized — location=%s", config.model_armor_location)
    return _client


async def check_caller_text(text: str, *, context: str) -> None:
    """Screens caller-supplied text before it reaches an LLM prompt. Raises
    PromptRejected if Model Armor finds a match; returns silently if clean, not
    configured, or the call itself fails (logged, not blocking — an availability
    problem in the guard itself shouldn't take down the tool it's guarding, but is
    always logged loudly enough to notice, unlike this crew's telemetry integrations).

    `context` is just for the log line / rejection message (e.g. "diagnose_take_technical
    take_id/scene/setup_id") — which tool call this was, not sanitized itself.
    """
    client = _get_client()
    if client is None:
        return

    from google.cloud import modelarmor_v1

    try:
        response = await client.sanitize_user_prompt(
            request=modelarmor_v1.SanitizeUserPromptRequest(
                name=config.model_armor_template,
                user_prompt_data=modelarmor_v1.DataItem(text=text),
            )
        )
    except Exception:
        _log.exception("Model Armor call failed for %s (fail-closed: rejecting)", context)
        raise PromptRejected(
            f"{context}: could not verify input safety (Model Armor call failed) — "
            "rejecting rather than passing unverified input to the model."
        ) from None

    result = response.sanitization_result
    if result.invocation_result != modelarmor_v1.InvocationResult.SUCCESS:
        _log.warning("Model Armor invocation_result=%s for %s (fail-closed: rejecting)", result.invocation_result, context)
        raise PromptRejected(
            f"{context}: Model Armor could not complete the safety check — "
            "rejecting rather than passing unverified input to the model."
        )

    if result.filter_match_state == modelarmor_v1.FilterMatchState.MATCH_FOUND:
        # Each nested *FilterResult (pi_and_jailbreak, sdp, malicious_uri, ...) has its
        # own shape — pi_and_jailbreak_filter_result.match_state is the one that
        # matters here, since that's the only filter the README's template setup
        # enables. Reported generically rather than assuming every filter type is
        # populated, since a template with other filters enabled would leave this
        # blank while still tripping the top-level match above.
        reasons = [
            name
            for name, fr in result.filter_results.items()
            if fr.pi_and_jailbreak_filter_result.match_state
            == modelarmor_v1.FilterMatchState.MATCH_FOUND
        ] or ["unspecified filter"]
        _log.warning("Model Armor rejected input for %s — matched: %s", context, reasons)
        raise PromptRejected(
            f"{context}: input rejected by Model Armor (matched: {', '.join(reasons)})."
        )
