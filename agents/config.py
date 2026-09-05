"""Central configuration for the agent crew, read from environment.

Every Gemini model ID and every Grafana/GCP endpoint the crew touches is pinned here
once, so swapping a model tier or a datasource is a one-line change.
"""
from __future__ import annotations

import os

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

    # GA on Vertex AI in us-central1 as of this writing — used only for spoken verdict
    # narration (text in, audio out; see agents/narration.py), never for analysis itself.
    gemini_live_model: str = "gemini-live-2.5-flash-native-audio"
    narrator_voice: str = "Charon"

    rag_corpus_display_name: str = "brainbar-production-assets"
    # RAG Engine's Spanner-backed mode is allowlist-only in us-central1/us-east1/us-east4
    # for new projects; europe-west4 runs the default (Basic/serverless) tier without
    # that restriction. The corpus resource name is fully-qualified, so Gemini calls
    # in google_cloud_location can reference a corpus that lives in a different region.
    rag_corpus_location: str = "europe-west4"
    vector_search_index_endpoint: str = ""

    documentai_location: str = "us"
    documentai_ocr_processor_display_name: str = "brainbar-ocr"

    agent_engine_resource_name: str = ""
    memory_bank_agent_engine_id: str = ""

    # Bucket names are globally unique across all of GCS — prefixed with the project
    # id to avoid collisions with other projects' "brainbar-*" buckets.
    gcs_assets_bucket: str = "nixora-project-brainbar-assets"
    gcs_dailies_bucket: str = "nixora-project-brainbar-dailies"

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

    # --- Model Armor (agents/model_armor_client.py) ---
    # Guards agents/mcp_server.py's public tool surface: caller-supplied strings
    # (take_id, scene, setup_id) get interpolated into an LLM prompt downstream, and
    # this server is reachable by callers BrainBar doesn't control. Template is a
    # one-time gcloud/Console resource, not something this code creates — see the
    # README's Model Armor section.
    model_armor_template: str = ""
    model_armor_location: str = ""

    # --- Agent Observability (Sigil) ---
    # A distinct product surface from the OTLP_* fields above: conversations, per-tool
    # traces, and evaluations in Grafana Cloud's native AI Observability app, rather
    # than raw OTel GenAI metrics on a hand-built dashboard. Needs its own Grafana
    # Cloud Access Policy Token (scope sigil:write) and endpoint from the stack's
    # Configuration page — see README's "Agent Observability (Sigil)" section.
    sigil_endpoint: str = ""
    sigil_instance_id: str = ""
    sigil_api_key: str = ""
    # Reported as OTel resource attributes (see agents/observability.py) so Grafana
    # Cloud's AI Observability app can group/filter crew telemetry by version and
    # environment instead of lumping every deploy into one unlabeled series.
    brainbar_version: str = "dev"
    deployment_environment: str = "production"

    # --- Grafana Pyroscope (continuous profiling — see agents/profiling.py) ---
    pyroscope_enabled: bool = True
    # Find these under your Grafana Cloud stack's "Connections -> Add new connection ->
    # Pyroscope" page (the same place OTLP's instance id/API key live for that stack's
    # OTLP endpoint) — a Pyroscope stack has its own separate instance id/push URL from
    # the Mimir/Loki/Tempo one above, and its own scoped API key (profiles:write).
    pyroscope_server_address: str = ""
    pyroscope_instance_id: str = ""
    pyroscope_api_key: str = ""

    # --- Grafana Cloud IRM on-call paging (see agents/first_ad/oncall_client.py) ---
    # The inbound webhook URL for a Grafana Cloud IRM integration wired to a real
    # escalation chain/on-call schedule — created once in the portal (Alerting & IRM ->
    # Integrations -> New integration -> Webhook), not provisionable from this repo
    # since the URL embeds a per-integration secret token.
    grafana_oncall_webhook_url: str = ""

    # TEMPORARY: this project's Pro-tier Dynamic Shared Quota is currently exhausted
    # and not eligible for a self-service increase (confirmed in Cloud Console), so
    # every hero-coverage/fault-active take that routes to Pro fails outright rather
    # than just running slower. Force Flash everywhere until Pro quota is usable
    # again — see agents/supervisor/routing.py's decide_model_tier. Flip back to
    # False once Pro calls succeed reliably again.
    force_flash_only: bool = True

    # --- Backend ---
    backend_host: str = "0.0.0.0"
    backend_port: int = 8080
    backend_base_url: str = "http://localhost:8080"

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

# Every LlmAgent below is built with a bare model-id string (e.g. "gemini-2.5-flash"),
# so ADK constructs its own default google-genai Client for it — and that Client reads
# GOOGLE_GENAI_USE_VERTEXAI/GOOGLE_CLOUD_PROJECT/GOOGLE_CLOUD_LOCATION directly from
# os.environ, never from this AgentsConfig object. On Cloud Run that's harmless (the
# deploy config sets these as real container env vars), but pydantic-settings' env_file
# loading above only populates *this object's* attributes — it does not export them to
# os.environ for other libraries to see. Without this, a bare `python -m backend.run`
# reading only .env silently falls back to the free Gemini Developer API (5 req/min)
# instead of Vertex AI, and every take fails with an empty response once that quota is
# hit — confirmed by an actual local run, not a hypothetical. setdefault() so a real
# pre-set env var (Cloud Run, a shell export) always wins over the .env-derived value.
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", str(config.google_genai_use_vertexai).lower())
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", config.google_cloud_project)
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", config.google_cloud_location)
