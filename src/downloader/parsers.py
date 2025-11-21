# downloader/parsers.py
"""Functions to extract DOIs from various academic citation file formats."""

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import bibtexparser
import rispy

from .utils import clean_doi

DOI_REGEX = r"\b(10[.]\d{4,9}/[-._;()/:A-Z0-9]+)\b"


def _parse_bibtex(text: str) -> list[str]:
    """Extracts DOIs from a BibTeX string."""
    dois = set()
    try:
        db = bibtexparser.loads(text)
        for entry in db.entries:
            if "doi" in entry and (cleaned := clean_doi(entry["doi"])):
                dois.add(cleaned)
    except Exception:
        pass
    return list(dois)


def _parse_ris(text: str) -> list[str]:
    """Extracts DOIs from an RIS string using the rispy library."""
    dois = set()
    try:
        for entry in rispy.loads(text):
            if "doi" in entry and (cleaned := clean_doi(entry["doi"])):
                dois.add(cleaned)
    except Exception:
        pass
    return list(dois)


def _parse_endnote_xml(text: str) -> list[str]:
    """Extracts DOIs from an EndNote XML string."""
    dois = set()
    try:
        root = ET.fromstring(text)
        for doi_node in root.findall(".//electronic-resource-num"):
            if doi_node.text and (cleaned := clean_doi(doi_node.text)):
                dois.add(cleaned)
    except Exception:
        pass
    return list(dois)


def _parse_json(text: str) -> list[str]:
    """Extracts DOIs from a Zotero-style JSON export."""
    dois = set()
    try:
        for item in json.loads(text):
            if item.get("DOI") and (cleaned := clean_doi(item["DOI"])):
                dois.add(cleaned)
    except Exception:
        pass
    return list(dois)


def _parse_plain_text(text: str) -> list[str]:
    """Finds all DOIs in a plain text or CSV string using regex."""
    dois = set()
    for match in re.findall(DOI_REGEX, text, re.IGNORECASE):
        if cleaned := clean_doi(match):
            dois.add(cleaned)
    return list(dois)


def extract_dois_from_file(filepath: str) -> list[str]:
    """
    Reads a file and extracts DOIs based on its content and extension.
    Supports .bib, .ris, .xml, .enw, .txt, .csv, and .json.
    """
    p = Path(filepath)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    text = p.read_text(encoding="utf-8", errors="ignore")
    ext = p.suffix.lower()

    if ext == ".bib":
        dois = _parse_bibtex(text)
    elif ext == ".ris":
        dois = _parse_ris(text)
    elif ext in [".xml", ".enw"]:
        dois = _parse_endnote_xml(text)
    elif ext == ".json":
        dois = _parse_json(text)
    elif ext in [".txt", ".csv"]:
        if "TY  -" in text and "ER  -" in text:
            dois = _parse_ris(text)
        elif "@article" in text.lower() or "@book" in text.lower():
            dois = _parse_bibtex(text)
        else:
            dois = _parse_plain_text(text)
    else:
        dois = _parse_plain_text(text)

    return sorted(list(set(dois)))
