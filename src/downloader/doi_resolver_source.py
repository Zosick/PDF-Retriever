import logging
from typing import Dict, Any
from urllib.parse import quote_plus
import requests
from . import config
from .sources import Source

log = logging.getLogger(__name__)

class DoiResolverSource(Source):
    def __init__(self, session: requests.Session):
        super().__init__(session)
        self.api_url = config.DOI_RESOLVER_URL

    def download(self, doi: str, filepath, metadata: Dict[str, Any]) -> bool:
        try:
            url = config.DOI_RESOLVER_URL.format(doi=quote_plus(doi))
            # Try to negotiate for PDF content
            headers = {"Accept": "application/pdf"}
            # We use _make_request to get the response but need stream=True which _make_request doesn't default to
            # So we use _fetch_and_save's logic but targeted
            return self._fetch_and_save(url, filepath, headers=headers)
        except Exception as e:
            log.debug(f"DOI Resolver failed: {e}")
            return False