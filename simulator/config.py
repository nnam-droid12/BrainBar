"""Central configuration for the Stage Simulator, read from environment."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class SimulatorConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    otlp_endpoint: str = "https://otlp-gateway-prod-us-central-0.grafana.net/otlp"
    otlp_instance_id: str = ""
    otlp_api_key: str = ""

    service_name: str = "brainbar-stage-simulator"

    node_count: int = 6
    camera_fps: int = 24
    wall_refresh_hz: int = 60
    frame_budget_ms: float = 1000.0 / 60.0

    control_host: str = "0.0.0.0"
    control_port: int = 9000

    shoot_script_path: str = "simulator/shoot_script.yaml"

    @property
    def otlp_headers(self) -> dict[str, str]:
        if not self.otlp_instance_id or not self.otlp_api_key:
            return {}
        import base64

        token = base64.b64encode(
            f"{self.otlp_instance_id}:{self.otlp_api_key}".encode()
        ).decode()
        return {"Authorization": f"Basic {token}"}

    @property
    def node_ids(self) -> list[str]:
        return [f"node-{i + 1}" for i in range(self.node_count)]


config = SimulatorConfig()
