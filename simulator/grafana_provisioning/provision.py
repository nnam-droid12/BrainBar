"""Apply the dashboards and alert rules in this package to a live Grafana Cloud stack.

Run once GRAFANA_CLOUD_STACK_URL and GRAFANA_SERVICE_ACCOUNT_TOKEN are set (in .env or
the environment): `python -m simulator.grafana_provisioning.provision`
"""
from __future__ import annotations

import sys

from simulator.config import config
from simulator.grafana_provisioning.alert_rules import CONTACT_POINT, build_alert_rules
from simulator.grafana_provisioning.client import GrafanaProvisioningClient
from simulator.grafana_provisioning.stage_health_dashboard import build_dashboard

FOLDER_UID = "brainbar"
FOLDER_TITLE = "BrainBar"


def main() -> None:
    if not config.grafana_cloud_stack_url or not config.grafana_service_account_token:
        print(
            "GRAFANA_CLOUD_STACK_URL and GRAFANA_SERVICE_ACCOUNT_TOKEN must be set "
            "(see .env.example). Nothing to provision.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    client = GrafanaProvisioningClient()
    try:
        print(f"Provisioning against {client.stack_url} ...")
        client.ensure_folder(FOLDER_TITLE, FOLDER_UID)
        uids = client.get_datasource_uids()
        for required in ("prometheus", "loki"):
            if required not in uids:
                raise SystemExit(
                    f"Grafana Cloud stack has no built-in '{required}' datasource — "
                    "check the stack was created with the default Cloud stack bundle."
                )

        dashboard = build_dashboard(uids["prometheus"], uids["loki"])
        result = client.upsert_dashboard(dashboard, FOLDER_UID)
        print(f"Stage Health dashboard: {client.stack_url}{result['url']}")

        client.ensure_contact_point(CONTACT_POINT)
        for rule in build_alert_rules(uids["prometheus"]):
            client.upsert_alert_rule(rule, FOLDER_UID)
            print(f"Alert rule provisioned: {rule['title']}")

        print("Done.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
