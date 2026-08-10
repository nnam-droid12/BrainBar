"""Entrypoint: `python -m backend.run` serves the FastAPI backend."""
from __future__ import annotations

import uvicorn

from backend.config import config


def main() -> None:
    uvicorn.run("backend.main:app", host=config.backend_host, port=config.backend_port, reload=False)


if __name__ == "__main__":
    main()
