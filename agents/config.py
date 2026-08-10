"""Central configuration for the agent crew, read from environment.

Every Gemini model ID and every Grafana/GCP endpoint the crew touches is pinned here
once, so swapping a model tier or a datasource is a one-line change.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentsConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Google Cloud ---
    google_cloud_project: str = "nixora-project"
    google_cloud_location: str = "us-central1"
    google_genai_use_vertexai: bool = True

    # Verified live against this project's Vertex AI Model Garden (see
    # scripts/list_vertex_models.md): gemini-2.5-pro / gemini-2.5-flash are GA on the
    # us-central1 regional endpoint. gemini-3.1-pro-preview / gemini-3-flash-preview
    # also resolve, but only via the "global" location and only as preview models —
    # swap to those here (and set google_cloud_location=global) once they're GA.
    gemini_pro_model: str = "gemini-2.5-pro"
    gemini_flash_model: str = "gemini-2.5-flash"

    rag_corpus_display_name: str = "brainbar-production-assets"
    vector_search_index_endpoint: str = ""

    documentai_location: str = "us"
    documentai_ocr_processor_display_name: str = "brainbar-ocr"

    agent_engine_resource_name: str = ""
    memory_bank_agent_engine_id: str = ""

    gcs_assets_bucket: str = "brainbar-assets"
    gcs_dailies_bucket: str = "brainbar-dailies"

    bigquery_dataset: str = "brainbar_dailies"
    bigquery_table: str = "takes"

    # --- Grafana Cloud ---
    grafana_cloud_stack_url: str = ""
    grafana_cloud_stack_id: str = ""
    grafana_service_account_token: str = ""

    grafana_mcp_mode: str = "oss"  # "oss" | "hosted"
    grafana_mcp_url: str = "http://localhost:8000/mcp"

    otlp_endpoint: str = "https://otlp-gateway-prod-us-central-0.grafana.net/otlp"
    otlp_instance_id: str = ""
    otlp_api_key: str = ""

    ai_observability_enabled: bool = True

    # --- Backend ---
    backend_host: str = "0.0.0.0"
    backend_port: int = 8080

    verdict_latency_budget_seconds: float = 15.0

    @property
    def otlp_headers(self) -> dict[str, str]:
        if not self.otlp_instance_id or not self.otlp_api_key:
            return {}
        import base64

        token = base64.b64encode(
            f"{self.otlp_instance_id}:{self.otlp_api_key}".encode()
        ).decode()
        return {"Authorization": f"Basic {token}"}


config = AgentsConfig()
