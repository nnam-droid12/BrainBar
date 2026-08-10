"""Parses production-document PDFs with Document AI before they're grounded in RAG
Engine. Real calls against a real Document AI OCR processor — nothing here is a local
PDF-text-extraction shortcut.
"""
from __future__ import annotations

import logging

from google.cloud import documentai

from agents.config import config

_log = logging.getLogger(__name__)


def _client() -> documentai.DocumentProcessorServiceClient:
    return documentai.DocumentProcessorServiceClient(
        client_options={
            "api_endpoint": f"{config.documentai_location}-documentai.googleapis.com"
        }
    )


def ensure_ocr_processor() -> str:
    """Returns the resource name of the brainbar-ocr processor, creating it once if
    it doesn't already exist in this project/location."""
    client = _client()
    parent = client.common_location_path(config.google_cloud_project, config.documentai_location)

    for processor in client.list_processors(parent=parent):
        if (
            processor.type_ == "OCR_PROCESSOR"
            and processor.display_name == config.documentai_ocr_processor_display_name
        ):
            return processor.name

    _log.info("Creating Document AI OCR processor %r", config.documentai_ocr_processor_display_name)
    processor = client.create_processor(
        parent=parent,
        processor=documentai.Processor(
            display_name=config.documentai_ocr_processor_display_name,
            type_="OCR_PROCESSOR",
        ),
    )
    return processor.name


def parse_pdf_text(pdf_path: str) -> str:
    """Sends a local PDF through the Document AI OCR processor and returns its
    extracted plain text."""
    processor_name = ensure_ocr_processor()
    client = _client()

    with open(pdf_path, "rb") as f:
        content = f.read()

    request = documentai.ProcessRequest(
        name=processor_name,
        raw_document=documentai.RawDocument(content=content, mime_type="application/pdf"),
    )
    result = client.process_document(request=request)
    return result.document.text
