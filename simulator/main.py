"""Entrypoint: `python -m simulator.main` serves the Stage Simulator control API."""
from __future__ import annotations

import uvicorn

from simulator.config import config


def main() -> None:
    uvicorn.run(
        "simulator.control_api:app",
        host=config.control_host,
        port=config.control_port,
        reload=False,
    )


if __name__ == "__main__":
    main()
