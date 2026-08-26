"""Thin client for a Grafana Cloud IRM (OnCall) inbound webhook integration.

Distinct from stage_control_client.py's target (this repo's own mock stage-control
plane) — this POSTs to a Grafana-Cloud-hosted integration URL that runs the payload
through a real escalation chain/on-call schedule, configured once in the Grafana Cloud
portal (see README.md's "Paging on-call" setup section: Alerting & IRM -> Integrations
-> New integration -> Webhook, then attach an escalation chain). The payload shape
below is IRM's documented inbound-webhook format — alert_uid groups repeated pages for
the same node into one alert group instead of paging on every single occurrence.
"""
from __future__ import annotations

import httpx

from agents.config import config


async def page_oncall(*, alert_uid: str, title: str, message: str, state: str = "alerting") -> dict:
    """state is "alerting" to open/re-fire a page or "ok" to resolve one — matching
    IRM's inbound webhook contract, not an arbitrary string."""
    if not config.grafana_oncall_webhook_url:
        return {
            "status": "error",
            "detail": "GRAFANA_ONCALL_WEBHOOK_URL not configured — no on-call integration to page.",
        }
    payload = {"alert_uid": alert_uid, "title": title, "message": message, "state": state}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(config.grafana_oncall_webhook_url, json=payload)
            resp.raise_for_status()
            return {"status": "ok", "payload": payload}
    except httpx.HTTPError as exc:
        return {"status": "error", "detail": f"on-call webhook unreachable: {exc}"}
