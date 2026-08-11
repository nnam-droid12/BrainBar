"""Entrypoint: `python -m simulator.main` serves the Stage Simulator control API."""
from __future__ import annotations

import os

import uvicorn

from simulator.config import config


def main() -> None:
    # Cloud Run injects PORT and requires the container to bind to it; fall back to
    # CONTROL_PORT/9000 for local dev where PORT is typically unset.
    port = int(os.environ.get("PORT", config.control_port))
    uvicorn.run(
        "simulator.control_api:app",
        host=config.control_host,
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    main()
