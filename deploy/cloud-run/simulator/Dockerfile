# Build from the repo root: docker build -f deploy/cloud-run/simulator/Dockerfile .
FROM python:3.11-slim

WORKDIR /app

COPY simulator/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY simulator/ simulator/

ENV PYTHONUNBUFFERED=1
EXPOSE 9000

CMD ["python", "-m", "simulator.main"]
