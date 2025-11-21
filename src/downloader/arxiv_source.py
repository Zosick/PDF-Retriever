import logging
import re
import xml.etree.ElementTree as ET
from typing import Any

import requests

from . import config
from .sources import Source

log = logging.getLogger(__name__)

class ArxivSource(Source):
    ARXIV_DOI_REGEX = r"10\.48550/arXiv\.(\d+\.\d+v?\d*)"
    ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}

    def __init__(self, session: requests.Session):
        super().__init__(session)
        self.api_url = config.ARXIV_API_URL

    def _get_arxiv_id(self, doi: str) -> str | None:
        if m := re.search(self.ARXIV_DOI_REGEX, doi, flags=re.IGNORECASE):
            return m.group(1)
        return None

    def get_metadata(self, doi: str) -> dict[str, Any] | None:
        arxiv_id = self._get_arxiv_id(doi)
        if not arxiv_id: return None
        try:
            url = f"{config.ARXIV_API_URL}?id_list={arxiv_id}"
            resp = self._make_request(url, timeout=10)
            if not resp: return None
            
            root = ET.fromstring(resp.text)
            entry = root.find("atom:entry", self.ATOM_NS)
            if entry is None: return None
            
            return {
                "year": entry.find("atom:published", self.ATOM_NS).text.split("-")[0],
                "title": entry.find("atom:title", self.ATOM_NS).text.strip().replace("\n", " "),
                "authors": [a.find('atom:name', self.ATOM_NS).text for a in entry.findall('atom:author', self.ATOM_NS)],
                "doi": doi
            }
        except Exception: return None

    def download(self, doi: str, filepath, metadata: dict[str, Any]) -> bool:
        arxiv_id = self._get_arxiv_id(doi)
        if arxiv_id:
            return self._fetch_and_save(config.ARXIV_PDF_URL.format(arxiv_id=arxiv_id), filepath)
        return False