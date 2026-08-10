"""Provisions the Vertex AI RAG Engine corpus Continuity grounds against, and ingests
the production assets into it: script and call sheet (parsed via Document AI first),
shot list, and storyboard descriptions.

Run once (idempotent — safe to re-run): `python -m agents.continuity.rag_setup`
"""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import vertexai
from vertexai import rag

from agents.config import config
from agents.continuity.documentai_client import parse_pdf_text

vertexai.init(project=config.google_cloud_project, location=config.rag_corpus_location)

_log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent.parent
ASSETS = ROOT / "assets"

PDF_SOURCES = {
    "script": ASSETS / "script" / "scene.pdf",
    "call_sheet": ASSETS / "call-sheet" / "call_sheet.pdf",
}
TEXT_SOURCES = {
    "shot_list": ASSETS / "shot-list" / "shot_list.csv",
    "storyboard": ASSETS / "storyboards" / "storyboard.md",
}


def ensure_corpus() -> str:
    """Returns the RAG corpus resource name, creating it once if it doesn't exist."""
    for corpus in rag.list_corpora():
        if corpus.display_name == config.rag_corpus_display_name:
            return corpus.name

    _log.info("Creating RAG corpus %r", config.rag_corpus_display_name)
    corpus = rag.create_corpus(
        display_name=config.rag_corpus_display_name,
        description="BrainBar production assets: script, shot list, storyboards, call sheet",
    )
    return corpus.name


def _existing_display_names(corpus_name: str) -> set[str]:
    return {f.display_name for f in rag.list_files(corpus_name)}


def ingest_assets(corpus_name: str | None = None) -> list[str]:
    """Uploads every production asset into the corpus. Returns the display names of
    files newly uploaded (already-present files are skipped, so this is safe to
    re-run as assets are edited — delete the file in the corpus first to refresh it)."""
    corpus_name = corpus_name or ensure_corpus()
    already = _existing_display_names(corpus_name)
    uploaded: list[str] = []

    for key, pdf_path in PDF_SOURCES.items():
        display_name = f"{key}.txt"
        if display_name in already:
            continue
        text = parse_pdf_text(str(pdf_path))
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(text)
            tmp_path = tmp.name
        rag.upload_file(
            corpus_name,
            path=tmp_path,
            display_name=display_name,
            description=f"Document AI OCR text extracted from {pdf_path.name}",
        )
        Path(tmp_path).unlink(missing_ok=True)
        uploaded.append(display_name)

    for key, path in TEXT_SOURCES.items():
        # RAG Engine's upload_file only accepts a fixed set of extensions (no .csv) —
        # upload a .txt copy of the content regardless of the source file's own type.
        display_name = f"{path.stem}.txt"
        if display_name in already:
            continue
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(path.read_text(encoding="utf-8"))
            tmp_path = tmp.name
        rag.upload_file(
            corpus_name,
            path=tmp_path,
            display_name=display_name,
            description=f"Source: assets/{path.relative_to(ASSETS).as_posix()}",
        )
        Path(tmp_path).unlink(missing_ok=True)
        uploaded.append(display_name)

    return uploaded


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    name = ensure_corpus()
    print(f"Corpus: {name}")
    new_files = ingest_assets(name)
    print(f"Uploaded {len(new_files)} new file(s): {new_files}")
