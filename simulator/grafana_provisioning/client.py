"""Thin client over the Grafana Cloud HTTP API for provisioning-as-code.

Distinct from the Grafana MCP server (agents/mcp_client.py), which the crew calls at
runtime during the demo. This client is the "as code" apply step: it pushes the
dashboard JSON and alert-rule definitions committed in this directory into a live
Grafana Cloud stack, using a service-account token with the Editor role.
"""
from __future__ import annotations

import httpx

from simulator.config import config


class GrafanaProvisioningClient:
    def __init__(self, stack_url: str | None = None, token: str | None = None) -> None:
        self.stack_url = (stack_url or config.grafana_cloud_stack_url).rstrip("/")
        self.token = token or config.grafana_service_account_token
        self._client = httpx.Client(
            base_url=self.stack_url,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    def get_datasource_uids(self) -> dict[str, str]:
        """Returns {'prometheus': uid, 'loki': uid, 'tempo': uid} for the stack's
        built-in Grafana Cloud datasources (there is exactly one of each per stack)."""
        resp = self._client.get("/api/datasources")
        resp.raise_for_status()
        uids: dict[str, str] = {}
        for ds in resp.json():
            ds_type = ds.get("type")
            if ds_type in ("prometheus", "loki", "tempo") and ds_type not in uids:
                uids[ds_type] = ds["uid"]
        return uids

    def ensure_folder(self, title: str, uid: str) -> str:
        resp = self._client.get(f"/api/folders/{uid}")
        if resp.status_code == 200:
            return resp.json()["uid"]
        resp = self._client.post("/api/folders", json={"uid": uid, "title": title})
        resp.raise_for_status()
        return resp.json()["uid"]

    def upsert_dashboard(self, dashboard: dict, folder_uid: str) -> dict:
        payload = {
            "dashboard": dashboard,
            "folderUid": folder_uid,
            "overwrite": True,
            "message": "provisioned by simulator/grafana_provisioning",
        }
        resp = self._client.post("/api/dashboards/db", json=payload)
        resp.raise_for_status()
        return resp.json()

    def ensure_contact_point(self, contact_point: dict) -> None:
        resp = self._client.get("/api/v1/provisioning/contact-points")
        resp.raise_for_status()
        existing = {cp["name"] for cp in resp.json()}
        if contact_point["name"] in existing:
            return
        resp = self._client.post(
            "/api/v1/provisioning/contact-points",
            json=contact_point,
            headers={"X-Disable-Provenance": "true"},
        )
        resp.raise_for_status()

    def upsert_alert_rule(self, rule: dict, folder_uid: str) -> None:
        rule = {**rule, "folderUID": folder_uid}
        resp = self._client.get("/api/v1/provisioning/alert-rules")
        resp.raise_for_status()
        existing = {r["title"]: r["uid"] for r in resp.json() if r.get("folderUID") == folder_uid}
        headers = {"X-Disable-Provenance": "true"}
        if rule["title"] in existing:
            resp = self._client.put(
                f"/api/v1/provisioning/alert-rules/{existing[rule['title']]}",
                json=rule,
                headers=headers,
            )
        else:
            resp = self._client.post(
                "/api/v1/provisioning/alert-rules", json=rule, headers=headers
            )
        resp.raise_for_status()

    def close(self) -> None:
        self._client.close()
