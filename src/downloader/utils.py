# downloader/utils.py
"""Utility functions for the downloader."""

import re
from .config import MAX_FILENAME_LEN


def safe_filename(text: str) -> str:
    """
    Creates a cross-platform safe filename from a string.
    Removes illegal characters and truncates to a safe length.
    """
    text = re.sub(r'[<>:"/\\|?*\n\r\t]+', "_", text)
    text = re.sub(r"[^A-Za-z0-9 _\-\.\(\)\[\],&]+", "", text)
    return text.strip()[:MAX_FILENAME_LEN]


def clean_doi(doi: str) -> str | None:
    """
    Cleans a string to extract a valid DOI.
    Removes URL prefixes and trailing punctuation.
    """
    if not doi or not isinstance(doi, str):
        return None

    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi.strip(), flags=re.IGNORECASE)
    doi = doi.rstrip(".,;})] ")

    if re.match(r"^10\.\d{4,9}/.+$", doi):
        return doi
    return None
