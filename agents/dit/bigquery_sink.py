"""Optional enhancement: one row per take in BigQuery, so dailies are queryable
(and the hackathon's own RAG-with-BigQuery pattern is available if extended later).
"""
from __future__ import annotations

from google.cloud import bigquery

from agents.config import config
from agents.schemas import TakeVerdict

SCHEMA = [
    bigquery.SchemaField("take_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("scene", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("setup_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("take_number", "INTEGER", mode="REQUIRED"),
    bigquery.SchemaField("verdict", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("evidence_summary", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("grafana_deeplink", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED"),
]

_client: bigquery.Client | None = None


def _get_client() -> bigquery.Client:
    global _client
    if _client is None:
        _client = bigquery.Client(project=config.google_cloud_project)
    return _client


def ensure_table() -> bigquery.Table:
    client = _get_client()
    dataset_ref = bigquery.DatasetReference(config.google_cloud_project, config.bigquery_dataset)
    try:
        client.get_dataset(dataset_ref)
    except Exception:
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = config.google_cloud_location
        client.create_dataset(dataset)

    table_ref = dataset_ref.table(config.bigquery_table)
    try:
        return client.get_table(table_ref)
    except Exception:
        table = bigquery.Table(table_ref, schema=SCHEMA)
        return client.create_table(table)


def insert_take_row(verdict: TakeVerdict, generated_at: str, grafana_deeplink: str | None) -> None:
    table = ensure_table()
    client = _get_client()
    row = {
        "take_id": verdict.take_id,
        "scene": verdict.scene,
        "setup_id": verdict.setup_id,
        "take_number": verdict.take_number,
        "verdict": verdict.verdict.value,
        "evidence_summary": verdict.headline,
        "grafana_deeplink": grafana_deeplink,
        "timestamp": generated_at,
    }
    errors = client.insert_rows_json(table, [row])
    if errors:
        raise RuntimeError(f"BigQuery insert failed: {errors}")
