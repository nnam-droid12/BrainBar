"""Entrypoint: `python -m backend.run` serves the FastAPI backend."""
from __future__ import annotations

import os

import uvicorn

from backend.config import config


def main() -> None:
    # Cloud Run injects PORT and requires the container to bind to it; fall back to
    # BACKEND_PORT/8080 for local dev where PORT is typically unset.
    port = int(os.environ.get("PORT", config.backend_port))
    uvicorn.run("backend.main:app", host=config.backend_host, port=port, reload=False)


if __name__ == "__main__":
    main()
