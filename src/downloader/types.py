# src/downloader/types.py
"""Type definitions for the PDF downloader."""

from typing import TypedDict


class Metadata(TypedDict, total=False):
    """Structured metadata for a PDF."""
    doi: str
    title: str
    year: str
    authors: list[str]
    _pdf_url: str | None
    source: str | None


class DownloadResult(TypedDict):
    """Result of a download operation."""
    doi: str
    status: str
    source: str | None
    filename: str | None
