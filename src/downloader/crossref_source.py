# downloader/crossref_source.py
"""
Defines the source for Crossref.
"""
import logging
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import requests

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
        self._metadata_cache: dict[str, dict[str, Any] | None] = {}

    @staticmethod
    def _parse_metadata(message: dict) -> dict[str, Any]:
        """Parse Crossref API response into standard metadata format."""
        title = message.get("title", ["Unknown Title"])[0]
        
        year = None
        if "published-print" in message and "date-parts" in message["published-print"]:
            year = message["published-print"]["date-parts"][0][0]
        elif "published-online" in message and "date-parts" in message["published-online"]:
            year = message["published-online"]["date-parts"][0][0]
        elif "issued" in message and "date-parts" in message["issued"]:
            year = message["issued"]["date-parts"][0][0]

        authors = [f"{author.get('given', '')} {author.get('family', '')}" for author in message.get("author", [])]
        return {
            "title": title,
            "year": str(year) if year else "Unknown",
            "authors": authors,
        }

    def get_metadata(self, doi: str) -> dict[str, Any] | None:
        """
        Gets the metadata for a given DOI from the Crossref API.
        Results are cached in-memory to avoid redundant API calls.
        
        API Compliance: Respects Crossref rate limits (1 req/sec implicit via 2-sec intervals).
        """
        if doi in self._metadata_cache:
            return self._metadata_cache[doi]
        
        try:
            # --- MODIFIED: URL-encode the DOI ---
            search_url = f"{self.api_url}works/{quote_plus(doi)}"
            response = self._make_request(search_url)
            if not response:
                self._metadata_cache[doi] = None
                return None

            data = response.json()
            log.debug(f"[{self.name}] Full response for {doi}: {data}")
            if data.get("status") != "ok":
                log.debug(f"[{self.name}] No results found for DOI: {doi}")
                self._metadata_cache[doi] = None
                return None

            message = data.get("message", {})
            log.debug(f"[{self.name}] Message for {doi}: {message}")

            result = self._parse_metadata(message)
            result["doi"] = doi
            self._metadata_cache[doi] = result
            return result

        except (requests.RequestException, ValueError) as e:
            log.warning(f"[{self.name}] Metadata request failed for {doi}: {e}")
            self._metadata_cache[doi] = None
            return None

    def download(self, doi: str, filepath: Path, metadata: dict[str, Any]) -> bool:
        """
        This source only provides metadata, so it does not download anything.
        """
        return False
