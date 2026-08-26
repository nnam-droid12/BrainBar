"""Grafana alert rule definitions — provisioned as code via the alerting provisioning API.

These are the danger conditions the First AD agent (agents/first_ad/) reacts to: when
one fires, it opens/updates a Grafana incident, silences downstream alert noise, and
annotates the Stage Health dashboard.
"""
from __future__ import annotations

RULE_GROUP = "brainbar-stage-alerts"


def _threshold_rule(
    title: str, prom_uid: str, expr: str, gt: float, for_: str, summary: str, severity: str
) -> dict:
    return {
        "title": title,
        "ruleGroup": RULE_GROUP,
        "condition": "C",
        "data": [
            {
                "refId": "A",
                "queryType": "",
                "relativeTimeRange": {"from": 120, "to": 0},
                "datasourceUid": prom_uid,
                "model": {"expr": expr, "refId": "A", "instant": True},
            },
            {
                "refId": "C",
                "queryType": "",
                "relativeTimeRange": {"from": 0, "to": 0},
                "datasourceUid": "__expr__",
                "model": {
                    "type": "threshold",
                    "expression": "A",
                    "refId": "C",
                    "conditions": [
                        {
                            "evaluator": {"type": "gt", "params": [gt]},
                            "operator": {"type": "and"},
                            "query": {"params": ["A"]},
                            "reducer": {"type": "last", "params": []},
                        }
                    ],
                },
            },
        ],
        "noDataState": "OK",
        "execErrState": "Error",
        "for": for_,
        "annotations": {"summary": summary},
        "labels": {"severity": severity, "app": "brainbar"},
    }


def build_alert_rules(prom_uid: str) -> list[dict]:
    return [
        _threshold_rule(
            title="BrainBar: render node offline",
            prom_uid=prom_uid,
            expr='max by (node) (time() - timestamp(brainbar_node_gpu_util_percent))',
            gt=20,
            for_="10s",
            summary="A render node has stopped reporting telemetry for over 20s — likely offline mid-take.",
            severity="critical",
        ),
        _threshold_rule(
            title="BrainBar: node VRAM sustained high",
            prom_uid=prom_uid,
            expr="max by (node) (brainbar_node_vram_percent)",
            gt=90,
            for_="15s",
            summary="A render node's VRAM has been above 90% for a sustained period — dropped-frame risk on the next hard cue.",
            severity="warning",
        ),
        _threshold_rule(
            title="BrainBar: genlock drift over threshold",
            prom_uid=prom_uid,
            expr="max by (device) (brainbar_genlock_drift_us)",
            gt=500,
            for_="10s",
            summary="Genlock drift has exceeded 500us — wall sync is degrading and takes may show tearing.",
            severity="critical",
        ),
        _threshold_rule(
            title="BrainBar: Pro-tier quota errors",
            prom_uid=prom_uid,
            expr='sum(increase(brainbar_crew_model_call_errors_total{code="429"}[10m]))',
            gt=0,
            for_="10s",
            summary=(
                "The crew hit a 429 on a Gemini Pro call in the last 10 minutes — the "
                "self-governing routing loop (agents/supervisor/quota_check.py) should "
                "already be downgrading new takes to Flash, but quota may need attention."
            ),
            severity="warning",
        ),
        _threshold_rule(
            title="BrainBar: agent hallucinated a tool call",
            prom_uid=prom_uid,
            expr="sum(increase(brainbar_crew_hallucinated_tool_calls_total[10m]))",
            gt=0,
            for_="10s",
            summary=(
                "An agent called a tool name outside its declared tool list in the last "
                "10 minutes — check the Hallucinated tool calls panel on Crew Health for "
                "which agent and tool, and tighten that agent's instruction."
            ),
            severity="warning",
        ),
    ]


# Shape required by POST /api/v1/provisioning/contact-points: a single embedded
# contact point, not the nested {"receivers": [...]} shape used by the legacy
# Alertmanager config API.
CONTACT_POINT = {
    "uid": "brainbar-first-ad-webhook",
    "name": "brainbar-first-ad",
    "type": "webhook",
    "settings": {
        "url": "http://backend:8080/internal/grafana-webhook",
        "httpMethod": "POST",
    },
    "disableResolveMessage": False,
}
