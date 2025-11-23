# downloader/crossref_source.py
"""
Defines the source for Crossref.
"""
import logging
from typing import Dict, Any, Optional
import requests

# --- MODIFIED: Added quote_plus ---
from urllib.parse import quote_plus
from . import config
from .sources import Source

log = logging.getLogger(__name__)


class CrossrefSource(Source):
    """
    A source for finding metadata from Crossref.
    """

    def __init__(self, session: requests.Session):
        super().__init__(session)
        self.api_url = config.CROSSREF_API_URL

    def get_metadata(self, doi: str) -> Optional[Dict[str, Any]]:
        """
        Gets the metadata for a given DOI from the Crossref API.
        """
        try:
            # --- MODIFIED: URL-encode the DOI ---
            search_url = f"{self.api_url}works/{quote_plus(doi)}"
            response = self._make_request(search_url)
            if not response:
                return None

            data = response.json()
            log.debug(f"[{self.name}] Full response for {doi}: {data}")
            if data.get("status") != "ok":
                log.debug(f"[{self.name}] No results found for DOI: {doi}")
                return None

            message = data.get("message", {})
            log.debug(f"[{self.name}] Message for {doi}: {message}")

            title = message.get("title", ["Unknown Title"])[0]

            year = None
            if (
                "published-print" in message
                and "date-parts" in message["published-print"]
            ):
                year = message["published-print"]["date-parts"][0][0]
            elif (
                "published-online" in message
                and "date-parts" in message["published-online"]
            ):
                year = message["published-online"]["date-parts"][0][0]
            elif "issued" in message and "date-parts" in message["issued"]:
                year = message["issued"]["date-parts"][0][0]

            authors = [
                f"{author.get('given', '')} {author.get('family', '')}"
                for author in message.get("author", [])
            ]

            return {
                "title": title,
                "year": str(year) if year else "Unknown",
                "authors": authors,
                "doi": doi,
            }

        except (requests.RequestException, ValueError) as e:
            log.warning(f"[{self.name}] Metadata request failed for {doi}: {e}")
            return None

    def download(self, doi: str, filepath: str, metadata: Dict[str, Any]) -> bool:
        """
        This source only provides metadata, so it does not download anything.
        """
        return False
