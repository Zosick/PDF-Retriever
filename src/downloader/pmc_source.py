# downloader/pmc_source.py
"""
Defines the source for PubMed Central.
"""
import logging
from pathlib import Path
from typing import Any

import requests

from . import config
from .sources import Source

log = logging.getLogger(__name__)


class PubMedCentralSource(Source):
    """
    A source for downloading PDFs from PubMed Central.
    """

    def __init__(self, session: requests.Session):
        super().__init__(session)
        self.api_url = config.PUBMED_API_URL

    def get_metadata(self, doi: str) -> dict[str, Any] | None:
        """
        Gets the metadata for a given DOI from PubMed Central.
        """
        try:
            # First, use ESearch to find the PMCID for the DOI
            esearch_url = f"{self.api_url}esearch.fcgi"
            params = {
                "db": "pmc",
                "term": f"{doi}[DOI]",
                "retmode": "json",
            }
            response = self._make_request(esearch_url, params=params)
            if not response:
                return None

            data = response.json()
            id_list = data.get("esearchresult", {}).get("idlist", [])
            if not id_list:
                log.debug(f"[{self.name}] No PMCID found for DOI: {doi}")
                return None

            pmcid = id_list[0]

            # Now, use EFetch to get the metadata for the PMCID
            efetch_url = f"{self.api_url}efetch.fcgi"
            params = {
                "db": "pmc",
                "id": pmcid,
                "retmode": "xml",
            }
            response = self._make_request(efetch_url, params=params)
            if not response:
                return None

            # Parse the XML response to get the metadata
            root = ET.fromstring(response.content)

            title = root.findtext(".//article-title") or "Unknown Title"
            year = root.findtext(".//pub-date/year") or "Unknown"
            doi = root.findtext(".//article-id[@pub-id-type='doi']") or doi
            authors = [author.text for author in root.findall(".//contrib[@contrib-type='author']/name/surname")]

            return {
                "title": title,
                "year": year,
                "authors": authors,
                "doi": doi,
                "pmcid": pmcid,
            }

        except (requests.RequestException, ValueError) as e:
            log.warning(f"[{self.name}] Metadata request failed for {doi}: {e}")
            return None

    def download(self, doi: str, filepath: Path, metadata: dict[str, Any]) -> bool:
        """
        Downloads the PDF for a given DOI from PubMed Central.
        """
        pmcid = metadata.get("pmcid")
        if not pmcid:
            log.debug(f"[{self.name}] No PMCID found in metadata for DOI: {doi}")
            return False

        try:
            # Use the PMC OA Web Service API to get the download link
            oa_url = f"{self.api_url}oa.fcgi"
            params = {"id": pmcid}
            response = self._make_request(oa_url, params=params)
            if not response:
                return False

            # Parse the XML response to find the PDF download link
            root = ET.fromstring(response.content)
            pdf_link = root.find(".//link[@format='pdf']")
            if pdf_link is None or not pdf_link.get("href"):
                log.debug(f"[{self.name}] No PDF link found for PMCID: {pmcid}")
                return False

            pdf_url = pdf_link.get("href")
            return self._fetch_and_save(pdf_url, filepath)

        except (requests.RequestException, ET.ParseError) as e:
            log.warning(f"[{self.name}] Download failed for {doi}: {e}")
            return False
