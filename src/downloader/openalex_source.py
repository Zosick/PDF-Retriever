import logging
from typing import Any
from urllib.parse import quote_plus

import requests

from . import config
from .sources import Source

log = logging.getLogger(__name__)

class OpenAlexSource(Source):
    def __init__(self, session: requests.Session):
        super().__init__(session)
        self.api_url = config.OPENALEX_API_URL

    def get_metadata(self, doi: str) -> dict[str, Any] | None:
        try:
            url = config.OPENALEX_API_URL.format(doi=quote_plus(doi))
            resp = self._make_request(url, timeout=10)
            if not resp: return None
            data = resp.json()
            return {
                "year": str(data.get("publication_year", "Unknown")),
                "title": data.get("title", "Unknown Title"),
                "authors": [a.get("au_name") for a in data.get("authorships", [])],
                "doi": doi,
                "_pdf_url": data.get("open_access", {}).get("oa_url")
            }
        except Exception: return None

    def download(self, doi: str, filepath, metadata: dict[str, Any]) -> bool:
        pdf_url = metadata.get("_pdf_url")
        if not pdf_url:
            meta = self.get_metadata(doi)
            pdf_url = meta.get("_pdf_url") if meta else None
        if pdf_url:
            return self._fetch_and_save(pdf_url, filepath)
        return False