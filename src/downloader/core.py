# src/downloader/core.py
import logging
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import requests
<<<<<<< HEAD

# Import the impersonation library
from curl_cffi import requests as requests_impersonate

from . import sources, config
from .pmc_source import PubMedCentralSource
from .doaj_source import DOAJSource
from .zenodo_source import ZenodoSource
from .osf_source import OSFSource
from .crossref_source import CrossrefSource
from .utils import safe_filename, format_authors_apa
from concurrent.futures import ThreadPoolExecutor, as_completed
=======
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
>>>>>>> 85cb3d387c185462bcf3032d3f6a75495df95de8

log = logging.getLogger(__name__)

class Downloader:
<<<<<<< HEAD
    """Manages the PDF download pipeline and metadata orchestration."""

    def __init__(
        self,
        output_dir: str,
        email: str,
        core_api_key: str | None,
        verify_ssl: bool = True,
    ):
=======
    def __init__(self, output_dir: str, email: str, core_api_key: str | None, verify_ssl: bool = True):
>>>>>>> 85cb3d387c185462bcf3032d3f6a75495df95de8
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.email = email
        self.verify_ssl = verify_ssl
        self.session = self._create_session()
        self.stats: dict[str, Any] = {"success": 0, "fail": 0, "skipped": 0, "sources": {}}
        self._stats_lock = threading.Lock()

<<<<<<< HEAD
        # Initialize sources
        self.core_source = sources.CoreApiSource(self.session, core_api_key)
        self.unpaywall_source = sources.UnpaywallSource(self.session, self.email)
=======
        # Initialize Sources
        self.core_source = CoreApiSource(self.session, core_api_key)
        self.unpaywall_source = UnpaywallSource(self.session, self.email)
>>>>>>> 85cb3d387c185462bcf3032d3f6a75495df95de8
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

    # -------------------------------------------------------------------------
    # Session and helpers
    # -------------------------------------------------------------------------

    def _create_session(self) -> requests.Session:
<<<<<<< HEAD
        """
        Creates a session that impersonates a real browser to bypass
        client-fingerprinting (e.g., JA3/TLS fingerprinting).
        """

        session = requests_impersonate.Session(impersonate="chrome110")
=======
        session = requests.Session()
        session.headers["User-Agent"] = random.choice(config.USER_AGENTS)
>>>>>>> 85cb3d387c185462bcf3032d3f6a75495df95de8
        session.verify = self.verify_ssl
        if not self.verify_ssl:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
<<<<<<< HEAD
            log.warning("SSL verification disabled.")

        return session

    def _generate_filename(self, metadata: Dict[str, Any]) -> str:
=======
        retries = Retry(total=5, backoff_factor=1, status_forcelist=[408, 429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def _generate_filename(self, metadata: dict[str, Any]) -> str:
>>>>>>> 85cb3d387c185462bcf3032d3f6a75495df95de8
        title = (metadata.get("title") or "Unknown Title").strip()
        year = (metadata.get("year") or "Unknown").strip()
        authors = metadata.get("authors", [])
        doi_part = metadata.get("doi", "unknown").replace("/", "_")
        author_str = format_authors_apa(authors)
        parts = []
<<<<<<< HEAD
        if author_str != "Unknown Author" and year != "Unknown":
            parts.append(f"{author_str}, {year}")
        elif author_str != "Unknown Author":
            parts.append(author_str)
        elif year != "Unknown":
            parts.append(year)
        if title != "Unknown Title":
            parts.append(title)
        parts.append(doi_part)

=======
        if author_str != "Unknown Author" and year != "Unknown": parts.append(f"{author_str}, {year}")
        elif author_str != "Unknown Author": parts.append(author_str)
        elif year != "Unknown": parts.append(year)
        if title != "Unknown Title": parts.append(title)
        parts.append(doi_part)
>>>>>>> 85cb3d387c185462bcf3032d3f6a75495df95de8
        name = " - ".join(parts)
        return safe_filename(name) + ".pdf"

    def _record_outcome(self, doi: str, source_name: str, filename: str):
<<<<<<< HEAD
        with self._stats_lock:
            self.stats["success"] += 1
            self.stats["sources"][source_name] = (
                self.stats["sources"].get(source_name, 0) + 1
            )
        log.info(f"Success ({source_name}): {doi} -> {filename}")

    # -------------------------------------------------------------------------
    # Download logic (with cancel support + APA citation)
    # -------------------------------------------------------------------------
    def download_one(self, doi: str, cancel_event: threading.Event) -> Dict[str, Any]:
        """Runs full download pipeline for one DOI with cancel support."""
        if cancel_event.is_set():
            return {"doi": doi, "status": "error", "message": "Cancelled before start"}

        metadata = None
        primary_pdf_url = None

        for meta_source in self.metadata_sources:
            if cancel_event.is_set():
                return {
                    "doi": doi,
                    "status": "error",
                    "message": "Cancelled during metadata fetch",
                }
            try:
                temp_meta = meta_source.get_metadata(doi)
                if temp_meta:
                    metadata = temp_meta
                    primary_pdf_url = temp_meta.get("_pdf_url")
            except Exception as e:
                log.warning(f"{meta_source.name} metadata failed: {e}")
            if metadata:
                break

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

        if primary_pdf_url and not cancel_event.is_set():
            if self.unpaywall_source._fetch_and_save(primary_pdf_url, filepath):
                self._record_outcome(doi, "Unpaywall", filename)
                return {
                    "doi": doi,
                    "status": "success",
                    "source": "Unpaywall",
                    "filename": str(filepath),
                    "citation": citation,
                }

        for source in self.pipeline:
            if cancel_event.is_set():
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

        if cancel_event.is_set():
            return {"doi": doi, "status": "error", "message": "Cancelled before finish"}

        with self._stats_lock:
            self.stats["fail"] += 1
        return {"doi": doi, "status": "failed", "message": "No valid source found"}

    # -------------------------------------------------------------------------
    def test_connections(self):
        results = []

        # --- MODIFIED: This dictionary comprehension now correctly ---
        # --- de-duplicates all sources from both lists. ---
        all_sources_dict = {s.name: s for s in self.metadata_sources + self.pipeline}
        all_sources = list(all_sources_dict.values())

        # --- REMOVED THE BUGGY LINE ---
        # all_sources.append(self.unpaywall_source) # <-- This was the BUG

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
=======
        log.info(f"Success ({source_name}): {doi} -> {filename}")
        with self._stats_lock:
            self.stats["success"] += 1
            self.stats["sources"][source_name] = self.stats["sources"].get(source_name, 0) + 1

    def _fetch_metadata_parallel(self, doi: str) -> tuple[dict[str, Any] | None, str | None]:
        """
        Fetches metadata from multiple sources in parallel and returns the best result.
        Stops early if a high-confidence source (Crossref, Unpaywall) succeeds.
        
        API Compliance: All sources respect rate limiting (2-second intervals).
        Returns only the first successful metadata, avoiding redundant calls.
        """
        metadata = None
        primary_pdf_url = None
        high_confidence_sources = {"Crossref", "Unpaywall"}
        
        def fetch_from_source(source: Any) -> tuple[dict[str, Any] | None, str | None, str]:
            """Fetch metadata from a single source. Returns (metadata, pdf_url, source_name)."""
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

    def download_one(self, doi: str) -> dict[str, Any]:
        """
        Downloads a PDF for a given DOI using parallel metadata retrieval and intelligent
        source prioritization. Respects all API rate limits and Terms of Service.
        """
        # Fetch metadata in parallel from multiple sources
        metadata, primary_pdf_url = self._fetch_metadata_parallel(doi)

        # Fallback: ensure we have at least basic metadata
        if metadata is None:
            metadata = {"doi": doi}
        
        filename = self._generate_filename(metadata)
        filepath = self.output_dir / filename

        # Skip if file already exists and is valid
        if filepath.exists() and filepath.stat().st_size > 5000:
            self._record_outcome(doi, "Skipped", filename)
            with self._stats_lock:
                self.stats["skipped"] += 1
            return {"doi": doi, "status": "skipped", "filename": str(filepath)}

        # Try primary PDF URL from high-confidence source (usually Unpaywall)
        if primary_pdf_url and self.unpaywall_source._fetch_and_save(primary_pdf_url, filepath):
            self._record_outcome(doi, "Unpaywall", filename)
            return {"doi": doi, "status": "success", "source": "Unpaywall", "filename": str(filepath)}

        # Try remaining pipeline sources with short-circuiting
        for source in self.pipeline:
            if source.download(doi, filepath, metadata):
                self._record_outcome(doi, source.name, filename)
                return {"doi": doi, "status": "success", "source": source.name, "filename": str(filepath)}

        # Record failure
        with self._stats_lock:
            self.stats["fail"] += 1
        return {"doi": doi, "status": "failed"}
>>>>>>> 85cb3d387c185462bcf3032d3f6a75495df95de8
