# src/downloader/core.py
import logging
import random
import threading
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from . import config
from .arxiv_source import ArxivSource
from .core_api_source import CoreApiSource
from .crossref_source import CrossrefSource
from .doaj_source import DOAJSource
from .doi_resolver_source import DoiResolverSource
from .openalex_source import OpenAlexSource
from .osf_source import OSFSource
from .pmc_source import PubMedCentralSource
from .semantic_scholar_source import SemanticScholarSource

# Modular Imports
from .sources import Source
from .unpaywall_source import UnpaywallSource
from .utils import format_authors_apa, safe_filename
from .zenodo_source import ZenodoSource

log = logging.getLogger(__name__)

class Downloader:
    def __init__(self, output_dir: str, email: str, core_api_key: str | None, verify_ssl: bool = True):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.email = email
        self.verify_ssl = verify_ssl
        self.session = self._create_session()
        self.stats = {"success": 0, "fail": 0, "skipped": 0, "sources": {}}
        self._stats_lock = threading.Lock()

        # Initialize Sources
        self.core_source = CoreApiSource(self.session, core_api_key)
        self.unpaywall_source = UnpaywallSource(self.session, self.email)
        self.pubmed_central_source = PubMedCentralSource(self.session)
        self.doaj_source = DOAJSource(self.session)
        self.zenodo_source = ZenodoSource(self.session)
        self.osf_source = OSFSource(self.session)
        self.openalex_source = OpenAlexSource(self.session)
        self.semantic_scholar_source = SemanticScholarSource(self.session)
        self.arxiv_source = ArxivSource(self.session)
        self.crossref_source = CrossrefSource(self.session)
        self.doi_resolver_source = DoiResolverSource(self.session)

        # Define Pipelines
        self.metadata_sources: list[Source] = [
            self.crossref_source,
            self.unpaywall_source,
            self.core_source,
            self.pubmed_central_source,
            self.doaj_source,
            self.zenodo_source,
            self.osf_source,
            self.arxiv_source,
            self.openalex_source,
            self.semantic_scholar_source,
        ]

        self.pipeline: list[Source] = [
            self.core_source,
            self.unpaywall_source,
            self.pubmed_central_source,
            self.doaj_source,
            self.zenodo_source,
            self.osf_source,
            self.openalex_source,
            self.semantic_scholar_source,
            self.arxiv_source,
            self.doi_resolver_source,
        ]

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        session.headers["User-Agent"] = random.choice(config.USER_AGENTS)
        session.verify = self.verify_ssl
        if not self.verify_ssl:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        retries = Retry(total=5, backoff_factor=1, status_forcelist=[408, 429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def _generate_filename(self, metadata: dict[str, Any]) -> str:
        title = (metadata.get("title") or "Unknown Title").strip()
        year = (metadata.get("year") or "Unknown").strip()
        authors = metadata.get("authors", [])
        doi_part = metadata.get("doi", "unknown").replace("/", "_")
        author_str = format_authors_apa(authors)
        parts = []
        if author_str != "Unknown Author" and year != "Unknown": parts.append(f"{author_str}, {year}")
        elif author_str != "Unknown Author": parts.append(author_str)
        elif year != "Unknown": parts.append(year)
        if title != "Unknown Title": parts.append(title)
        parts.append(doi_part)
        name = " - ".join(parts)
        return safe_filename(name) + ".pdf"

    def _record_outcome(self, doi: str, source_name: str, filename: str):
        log.info(f"Success ({source_name}): {doi} -> {filename}")
        with self._stats_lock:
            self.stats["success"] += 1
            self.stats["sources"][source_name] = self.stats["sources"].get(source_name, 0) + 1

    def download_one(self, doi: str) -> dict[str, Any]:
        metadata = None
        primary_pdf_url = None

        for meta_source in self.metadata_sources:
            try:
                temp_meta = meta_source.get_metadata(doi)
                if temp_meta:
                    metadata = temp_meta
                    if temp_meta.get("_pdf_url"):
                        primary_pdf_url = temp_meta.get("_pdf_url")
            except Exception: pass
            if metadata: break

        if metadata is None or not metadata.get("title") or metadata.get("title") == "Unknown Title":
            crossref_meta = self.crossref_source.get_metadata(doi)
            if crossref_meta:
                if metadata:
                    existing = metadata.copy()
                    crossref_meta.update(existing)
                    metadata = crossref_meta
                else:
                    metadata = crossref_meta

        if metadata is None: metadata = {"doi": doi}
        filename = self._generate_filename(metadata)
        filepath = self.output_dir / filename

        if filepath.exists() and filepath.stat().st_size > 5000:
            self._record_outcome(doi, "Skipped", filename)
            with self._stats_lock: self.stats["skipped"] += 1
            return {"doi": doi, "status": "skipped", "filename": str(filepath)}

        if primary_pdf_url and self.unpaywall_source._fetch_and_save(primary_pdf_url, filepath):
            self._record_outcome(doi, "Unpaywall", filename)
            return {"doi": doi, "status": "success", "source": "Unpaywall", "filename": str(filepath)}

        for source in self.pipeline:
            if source.download(doi, filepath, metadata):
                self._record_outcome(doi, source.name, filename)
                return {"doi": doi, "status": "success", "source": source.name, "filename": str(filepath)}

        with self._stats_lock: self.stats["fail"] += 1
        return {"doi": doi, "status": "failed"}