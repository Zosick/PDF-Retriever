import logging
from typing import Dict, Any, Optional
from urllib.parse import quote_plus
import requests
from . import config
from .sources import Source

log = logging.getLogger(__name__)

class CoreApiSource(Source):
    def __init__(self, session: requests.Session, api_key: Optional[str]):
        super().__init__(session)
        self.api_key = api_key
        self.api_url = config.CORE_API_URL

    def _get_data(self, doi: str):
        if not self.api_key: return None
        try:
            url = config.CORE_API_URL.format(doi=quote_plus(doi))
            headers = {"Authorization": f"Bearer {self.api_key}"}
            resp = self._make_request(url, headers=headers, timeout=10)
            if resp and resp.status_code == 200: return resp.json()
        except Exception: pass
        return None

    def get_metadata(self, doi: str) -> Optional[Dict[str, Any]]:
        data = self._get_data(doi)
        if not data: return None
        return {
            "year": str(data.get("year", "Unknown")),
            "title": data.get("title", "Unknown Title"),
            "authors": [a.get("name") for a in data.get("authors", [])],
            "doi": data.get("doi", doi),
            "_pdf_url": data.get("fullTextLink")
        }

    def download(self, doi: str, filepath, metadata: Dict[str, Any]) -> bool:
        pdf_url = metadata.get("_pdf_url")
        if not pdf_url:
            data = self._get_data(doi)
            pdf_url = data.get("fullTextLink") if data else None
        if pdf_url and ("pdf" in pdf_url.lower()):
            return self._fetch_and_save(pdf_url, filepath)
        return False