"""Deploys the Supervisor — the crew's root ADK agent — to Vertex AI Agent Engine, the
hosted, unattended agent runtime.

The production take pipeline (backend/routes/internal.py) orchestrates the five agents
directly in Python for low-latency on-set control (agents.supervisor.orchestrate).
This deployment is the separate, spec-required Agent Engine hosting of the root agent
itself: a real, independently queryable, unattended-capable deployment of the same
Supervisor object used in that pipeline, satisfying "deploy the ADK crew as the hosted
agent runtime" as a genuine artifact rather than only inline invocation.

Run from the repo root: python deploy/agent-engine/deploy.py
(the directory is hyphenated to match the spec's layout, so it can't be run as a
`-m` module — this script adds the repo root to sys.path itself instead).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import vertexai
from vertexai import agent_engines

from agents.config import config
from agents.schemas import ModelTier
from agents.supervisor.agent import build_agent
REQUIREMENTS = [
    line.strip()
    for line in (ROOT / "agents" / "requirements.txt").read_text().splitlines()
    if line.strip() and not line.startswith("#")
]

STAGING_BUCKET = f"gs://{config.gcs_assets_bucket}"


def main() -> None:
    vertexai.init(
        project=config.google_cloud_project,
        location=config.google_cloud_location,
        staging_bucket=STAGING_BUCKET,
    )

    supervisor = build_agent(ModelTier.PRO)

    remote_agent = agent_engines.create(
        agent_engine=supervisor,
        requirements=REQUIREMENTS,
        extra_packages=[str(ROOT / "agents")],
        display_name="brainbar-supervisor",
        description=(
            "BrainBar Supervisor — synthesizes the circle-take call from the "
            "Technical Director's and Continuity's verdicts."
        ),
        env_vars={
            "GOOGLE_CLOUD_PROJECT": config.google_cloud_project,
            "GOOGLE_CLOUD_LOCATION": config.google_cloud_location,
            "GOOGLE_GENAI_USE_VERTEXAI": "true",
            "GEMINI_PRO_MODEL": config.gemini_pro_model,
            "GEMINI_FLASH_MODEL": config.gemini_flash_model,
        },
        service_account=f"brainbar-runtime@{config.google_cloud_project}.iam.gserviceaccount.com",
        min_instances=0,
        max_instances=2,
    )

    print(f"Deployed: {remote_agent.resource_name}")
    print(
        "Set AGENT_ENGINE_RESOURCE_NAME to this value in .env / Cloud Run env vars "
        "to reference this deployment."
    )


if __name__ == "__main__":
    main()
