# src/downloader/core.py
import logging
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
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
from .sources import Source
from .unpaywall_source import UnpaywallSource
from .utils import format_authors_apa, safe_filename
from .zenodo_source import ZenodoSource

log = logging.getLogger(__name__)

class Downloader:
    """Manages the PDF download pipeline and metadata orchestration."""

    def __init__(
        self,
        output_dir: str,
        email: str,
        core_api_key: str | None,
        verify_ssl: bool = True,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.email = email
        self.verify_ssl = verify_ssl
        self.session = self._create_session()
        self.stats: dict[str, Any] = {"success": 0, "fail": 0, "skipped": 0, "sources": {}}
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
            log.warning("SSL verification disabled.")

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
        
        if author_str != "Unknown Author" and year != "Unknown":
            parts.append(f"{author_str}, {year}")
        elif author_str != "Unknown Author":
            parts.append(author_str)
        elif year != "Unknown":
            parts.append(year)
        if title != "Unknown Title":
            parts.append(title)
        parts.append(doi_part)
        
        name = " - ".join(parts)
        return safe_filename(name) + ".pdf"

    def _record_outcome(self, doi: str, source_name: str, filename: str):
        with self._stats_lock:
            self.stats["success"] += 1
            self.stats["sources"][source_name] = (
                self.stats["sources"].get(source_name, 0) + 1
            )
        log.info(f"Success ({source_name}): {doi} -> {filename}")

    def _fetch_metadata_parallel(self, doi: str) -> tuple[dict[str, Any] | None, str | None]:
        """
        Fetches metadata from multiple sources in parallel and returns the best result.
        Stops early if a high-confidence source (Crossref, Unpaywall) succeeds.
        """
        metadata = None
        primary_pdf_url = None
        high_confidence_sources = {"Crossref", "Unpaywall"}
        
        def fetch_from_source(source: Any) -> tuple[dict[str, Any] | None, str | None, str]:
            try:
                temp_meta = source.get_metadata(doi)
                pdf_url = temp_meta.get("_pdf_url") if temp_meta else None
                return temp_meta, pdf_url, source.name
            except Exception:
                return None, None, source.name
        
        # Parallel fetch with max 4 workers to respect API rate limits
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(fetch_from_source, s): s for s in self.metadata_sources}
            
            for future in as_completed(futures):
                try:
                    temp_meta, pdf_url, source_name = future.result()
                    if temp_meta and not metadata:
                        metadata = temp_meta
                        if pdf_url:
                            primary_pdf_url = pdf_url
                        # Short-circuit: stop if we got high-confidence source
                        if source_name in high_confidence_sources and metadata.get("title"):
                            break
                except Exception:
                    pass
        
        return metadata, primary_pdf_url

    def download_one(self, doi: str, cancel_event: threading.Event | None = None) -> dict[str, Any]:
        """Runs full download pipeline for one DOI with cancel support."""
        if cancel_event and cancel_event.is_set():
            return {"doi": doi, "status": "error", "message": "Cancelled before start"}

        # Fetch metadata in parallel
        metadata, primary_pdf_url = self._fetch_metadata_parallel(doi)

        if cancel_event and cancel_event.is_set():
             return {"doi": doi, "status": "error", "message": "Cancelled during metadata fetch"}

        if metadata is None:
            metadata = {"doi": doi}

        filename = self._generate_filename(metadata)
        filepath = self.output_dir / filename

        authors = metadata.get("authors", [])
        year = metadata.get("year", "n.d.")
        author_str = format_authors_apa(authors)
        citation = f"{author_str}, {year}" if author_str else year

        if filepath.exists() and filepath.stat().st_size > 5000:
            with self._stats_lock:
                self.stats["skipped"] += 1
            return {
                "doi": doi,
                "status": "skipped",
                "filename": str(filepath),
                "citation": citation,
            }

        # Try primary PDF URL from high-confidence source (usually Unpaywall)
        if primary_pdf_url and (not cancel_event or not cancel_event.is_set()):
            if self.unpaywall_source._fetch_and_save(primary_pdf_url, filepath):
                self._record_outcome(doi, "Unpaywall", filename)
                return {
                    "doi": doi,
                    "status": "success",
                    "source": "Unpaywall",
                    "filename": str(filepath),
                    "citation": citation,
                }

        # Try remaining pipeline sources
        for source in self.pipeline:
            if cancel_event and cancel_event.is_set():
                return {
                    "doi": doi,
                    "status": "error",
                    "message": "Cancelled mid-pipeline",
                }
            try:
                if source.download(doi, filepath, metadata):
                    self._record_outcome(doi, source.name, filename)
                    return {
                        "doi": doi,
                        "status": "success",
                        "source": source.name,
                        "filename": str(filepath),
                        "citation": citation,
                    }
            except Exception as e:
                log.warning(f"{source.name} failed: {e}")

        if cancel_event and cancel_event.is_set():
            return {"doi": doi, "status": "error", "message": "Cancelled before finish"}

        with self._stats_lock:
            self.stats["fail"] += 1
        return {"doi": doi, "status": "failed", "message": "No valid source found"}

    def test_connections(self):
        results = []
        all_sources_dict = {s.name: s for s in self.metadata_sources + self.pipeline}
        all_sources = list(all_sources_dict.values())

        with ThreadPoolExecutor(max_workers=len(all_sources)) as executor:
            future_map = {executor.submit(s.test_connection): s for s in all_sources}
            for future in as_completed(future_map):
                src = future_map[future]
                try:
                    status, msg = future.result()
                    results.append({"name": src.name, "status": status, "message": msg})
                except Exception as e:
                    results.append(
                        {"name": src.name, "status": False, "message": str(e)}
                    )
        return results
