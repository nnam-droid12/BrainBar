"""Grafana Pyroscope: continuous profiling for the crew's own process, linked to its
OTel traces so a slow span (e.g. a slow gen_ai.invoke_agent call, or a slow Grafana MCP
tool call) can be opened straight into a flamegraph of exactly what the Python process
was doing — not just "this span took 4 seconds", but which function.

This goes one level past agents/observability.py's metrics/traces/logs: those establish
*that* something was slow and roughly where; this establishes *why*, at the code level.
Call `init_profiling()` once at process start, right after init_observability() (so the
global OTel TracerProvider it sets up already exists for PyroscopeSpanProcessor to
attach to).

Requires `pyroscope-io` and `pyroscope-otel` (see agents/requirements.txt). Both ship
prebuilt wheels for Linux/macOS (pyroscope-io is a Rust extension); on Windows there is
no prebuilt wheel as of this writing, so a Windows dev machine needs either a Rust
toolchain on PATH to build from source, or to run the crew inside Docker/WSL instead —
this does not affect the deployed Cloud Run image, which builds on Linux.
"""
from __future__ import annotations

import logging

from agents.config import config

_log = logging.getLogger(__name__)
_initialized = False


def init_profiling() -> None:
    global _initialized
    if _initialized or not config.pyroscope_enabled:
        return
    if not config.pyroscope_server_address or not config.pyroscope_instance_id or not config.pyroscope_api_key:
        _log.warning(
            "PYROSCOPE_SERVER_ADDRESS/PYROSCOPE_INSTANCE_ID/PYROSCOPE_API_KEY not set — "
            "crew continuous profiling disabled until Grafana Cloud Pyroscope credentials "
            "are configured."
        )
        return

    try:
        import pyroscope
        from pyroscope.otel import PyroscopeSpanProcessor
        from opentelemetry import trace
    except ImportError:
        _log.warning(
            "pyroscope-io/pyroscope-otel not importable (see this module's docstring — "
            "likely a Windows dev machine without a Rust toolchain) — profiling disabled."
        )
        return

    pyroscope.configure(
        application_name="brainbar-crew",
        server_address=config.pyroscope_server_address,
        basic_auth_username=config.pyroscope_instance_id,
        basic_auth_password=config.pyroscope_api_key,
        tags={"environment": config.deployment_environment, "version": config.brainbar_version},
    )

    # Attaches to whatever TracerProvider init_observability() already installed
    # globally — this module doesn't create its own, so call order matters (see
    # docstring above).
    trace.get_tracer_provider().add_span_processor(PyroscopeSpanProcessor())

    _initialized = True
    _log.info("Continuous profiling: pushing crew profiles to %s", config.pyroscope_server_address)
