# Build from the repo root: docker build -f deploy/cloud-run/backend/Dockerfile .
# The backend imports the agents/ package directly (agents.supervisor.orchestrate,
# agents.first_ad.act, agents.dit.compile), so both packages must ship in this image.
FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt backend-requirements.txt
COPY agents/requirements.txt agents-requirements.txt
RUN pip install --no-cache-dir -r backend-requirements.txt -r agents-requirements.txt

COPY backend/ backend/
COPY agents/ agents/
COPY assets/ assets/

ENV PYTHONUNBUFFERED=1
EXPOSE 8080

CMD ["python", "-m", "backend.run"]
