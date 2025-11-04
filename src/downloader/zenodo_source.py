# downloader/zenodo_source.py
"""
Defines the source for Zenodo.
"""
import logging
from typing import Dict, Any, Optional
import requests
from . import config
from .sources import Source

log = logging.getLogger(__name__)


class ZenodoSource(Source):
    """
    A source for finding open access articles from Zenodo.
    """

    def __init__(self, session: requests.Session):
        super().__init__(session)
        self.api_url = config.ZENODO_API_URL

    def get_metadata(self, doi: str) -> Optional[Dict[str, Any]]:
        """
        Gets the metadata for a given DOI from the Zenodo API.
        """
        try:
            search_url = f"{self.api_url}records?q=doi:\"{doi}\""
            response = self._make_request(search_url)
            if not response:
                return None

            data = response.json()
            if data.get("hits", {}).get("total", 0) == 0:
                log.debug(f"[{self.name}] No results found for DOI: {doi}")
                return None

            # The first result is the most likely match
            result = data.get("hits", {}).get("hits", [])[0]
            metadata = result.get("metadata", {})

            title = metadata.get("title", "Unknown Title")
            year = metadata.get("publication_date", "Unknown").split("-")[0]

            # Find the PDF URL
            pdf_url = None
            for f in result.get("files", []):
                if f.get("type") == "pdf":
                    pdf_url = f.get("links", {}).get("self")
                    break

            authors = [creator.get("name") for creator in metadata.get("creators", [])]

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
        Downloads the PDF for a given DOI from Zenodo.
        """
        pdf_url = metadata.get("_pdf_url")
        if not pdf_url:
            # If _pdf_url is not in the provided metadata, try to get fresh metadata
            meta = self.get_metadata(doi)
            pdf_url = meta.get("_pdf_url") if meta else None

        if pdf_url:
            return self._fetch_and_save(pdf_url, filepath)
        return False
