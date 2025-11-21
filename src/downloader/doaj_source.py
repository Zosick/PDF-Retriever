# downloader/doaj_source.py
"""
Defines the source for the Directory of Open Access Journals (DOAJ).
"""
import logging
from typing import Any

import requests

from . import config
from .sources import Source

log = logging.getLogger(__name__)


class DOAJSource(Source):
    """
    A source for finding open access articles from the DOAJ.
    """

    def __init__(self, session: requests.Session):
        super().__init__(session)
        self.api_url = config.DOAJ_API_URL

    def get_metadata(self, doi: str) -> dict[str, Any] | None:
        """
        Gets the metadata for a given DOI from the DOAJ API.
        """
        try:
            search_url = f"{self.api_url}search/articles/doi:{doi}"
            response = self._make_request(search_url)
            if not response:
                return None

            data = response.json()
            if data.get("total", 0) == 0:
                log.debug(f"[{self.name}] No results found for DOI: {doi}")
                return None

            # The first result is the most likely match
            result = data.get("results", [])[0]
            bibjson = result.get("bibjson", {})

            title = bibjson.get("title", "Unknown Title")
            year = bibjson.get("year", "Unknown")

            # Find the full-text URL
            pdf_url = None
            for identifier in bibjson.get("identifier", []):
                if identifier.get("type") == "fulltext":
                    pdf_url = identifier.get("id")
                    break

            authors = [author.get("name") for author in bibjson.get("author", [])]

            return {
                "title": title,
                "year": year,
                "authors": authors,
                "doi": doi,
                "_pdf_url": pdf_url,
            }

        except (requests.RequestException, ValueError) as e:
            log.warning(f"[{self.name}] Metadata request failed for {doi}: {e}")
            return None

    def download(self, doi: str, filepath: str, metadata: dict[str, Any]) -> bool:
        """
        Downloads the PDF for a given DOI from the DOAJ.
        """
        pdf_url = metadata.get("_pdf_url")
        if not pdf_url:
            # If _pdf_url is not in the provided metadata, try to get fresh metadata
            meta = self.get_metadata(doi)
            pdf_url = meta.get("_pdf_url") if meta else None

        if pdf_url:
            return self._fetch_and_save(pdf_url, filepath)
        return False
