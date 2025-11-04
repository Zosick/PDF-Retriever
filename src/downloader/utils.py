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

from urllib.parse import urljoin
from bs4 import BeautifulSoup

def find_pdf_link_on_page(url: str, session: requests.Session) -> str | None:
    """
    Tries to find a direct PDF link on a landing page using BeautifulSoup.
    """
    try:
        response = session.get(url, timeout=20)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Look for links that end in .pdf
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if href.lower().endswith(".pdf"):
                if not href.startswith("http"):
                    href = urljoin(url, href)
                return href

        # Look for links that contain "download pdf"
        for link in soup.find_all("a", string=re.compile(r"download pdf", re.IGNORECASE)):
            href = link.get("href")
            if href:
                if not href.startswith("http"):
                    href = urljoin(url, href)
                return href

        return None

    except (requests.RequestException, AttributeError):
        return None

def format_authors_apa(authors: list[str] | None) -> str:
    """
    Formats a list of authors according to the 7th APA style, using only surnames.
    """
    if not authors:
        return "Unknown Author"

    surnames = []
    for author in authors:
        if author:
            parts = author.strip().split(' ')
            if parts:
                surnames.append(parts[-1])

    if not surnames:
        return "Unknown Author"

    if len(surnames) == 1:
        return surnames[0]
    elif len(surnames) == 2:
        return f"{surnames[0]} & {surnames[1]}"
    else:
        return f"{surnames[0]} et al."
