# downloader/osf_source.py
"""
Defines the source for the Open Science Framework (OSF).
"""
import logging
from typing import Dict, Any, Optional
import requests

# --- MODIFIED: Added quote_plus ---
from urllib.parse import quote_plus
from . import config
from .sources import Source

log = logging.getLogger(__name__)


class OSFSource(Source):
    """
    A source for finding open access articles from the OSF.
    """

    def __init__(self, session: requests.Session):
        super().__init__(session)
        self.api_url = config.OSF_API_URL

    def get_metadata(self, doi: str) -> Optional[Dict[str, Any]]:
        """
        Gets the metadata for a given DOI from the OSF API.
        """
        try:
            # --- MODIFIED: URL-encode the DOI in the query ---
            search_url = f"{self.api_url}search/?q={quote_plus(doi)}"
            response = self._make_request(search_url)
            if not response:
                return None

            data = response.json()
            if data.get("meta", {}).get("total", 0) == 0:
                log.debug(f"[{self.name}] No results found for DOI: {doi}")
                return None

            # The first result is the most likely match
            result = data.get("data", [])[0]
            attributes = result.get("attributes", {})

            title = attributes.get("title", "Unknown Title")
            year = attributes.get("date_published", "Unknown").split("-")[0]

            # Find the PDF URL
            pdf_url = None
            links = result.get("links", {})
            if "download" in links:
                pdf_url = links.get("download")

            authors = attributes.get("creators", [])

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

    def download(self, doi: str, filepath: str, metadata: Dict[str, Any]) -> bool:
        """
        Downloads the PDF for a given DOI from the OSF.
        """
        pdf_url = metadata.get("_pdf_url")
        if not pdf_url:
            # If _pdf_url is not in the provided metadata, try to get fresh metadata
            meta = self.get_metadata(doi)
            pdf_url = meta.get("_pdf_url") if meta else None

        if pdf_url:
            return self._fetch_and_save(pdf_url, filepath)
        return False
