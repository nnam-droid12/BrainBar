"""Central configuration for the FastAPI backend, read from environment."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class BackendConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    backend_host: str = "0.0.0.0"
    backend_port: int = 8080

    simulator_base_url: str = "http://localhost:9000"

    verdict_latency_budget_seconds: float = 15.0


config = BackendConfig()
