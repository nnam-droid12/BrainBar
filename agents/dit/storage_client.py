"""Cloud Storage sink for technical dailies packages."""
from __future__ import annotations

import json

from google.cloud import storage

from agents.config import config

_client: storage.Client | None = None


def _get_client() -> storage.Client:
    global _client
    if _client is None:
        _client = storage.Client(project=config.google_cloud_project)
    return _client


def ensure_bucket() -> storage.Bucket:
    client = _get_client()
    bucket = client.bucket(config.gcs_dailies_bucket)
    if not bucket.exists():
        bucket = client.create_bucket(config.gcs_dailies_bucket, location=config.google_cloud_location)
    return bucket


def upload_dailies_json(scene: str, generated_at: str, payload: dict) -> str:
    """Uploads the dailies package JSON and returns its gs:// URI."""
    bucket = ensure_bucket()
    blob_name = f"dailies/{scene}/{generated_at.replace(':', '-')}.json"
    blob = bucket.blob(blob_name)
    blob.upload_from_string(json.dumps(payload, indent=2), content_type="application/json")
    return f"gs://{config.gcs_dailies_bucket}/{blob_name}"
