# Build from the repo root: docker build -f deploy/cloud-run/mcp-server/Dockerfile .
# BrainBar as an MCP server (agents/mcp_server.py) — the crew's own diagnostic reasoning,
# exposed to any MCP-speaking caller, not just BrainBar's own cut-webhook pipeline.
FROM python:3.11-slim

WORKDIR /app

COPY agents/requirements.txt agents-requirements.txt
RUN pip install --no-cache-dir -r agents-requirements.txt

COPY agents/ agents/
COPY assets/ assets/

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["python", "-m", "agents.mcp_server"]
