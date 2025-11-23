# downloader/core.py
"""Core Downloader class that orchestrates the PDF fetching process."""

import logging
import random
import threading
from pathlib import Path
from typing import Dict, List, Any
import requests

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
        self.stats = {"success": 0, "fail": 0, "skipped": 0, "sources": {}}
        self._stats_lock = threading.Lock()

        # Initialize sources
        self.core_source = sources.CoreApiSource(self.session, core_api_key)
        self.unpaywall_source = sources.UnpaywallSource(self.session, self.email)
        self.pubmed_central_source = PubMedCentralSource(self.session)
        self.doaj_source = DOAJSource(self.session)
        self.zenodo_source = ZenodoSource(self.session)
        self.osf_source = OSFSource(self.session)
        self.openalex_source = sources.OpenAlexSource(self.session)
        self.semantic_scholar_source = sources.SemanticScholarSource(self.session)
        self.arxiv_source = sources.ArxivSource(self.session)
        self.crossref_source = CrossrefSource(self.session)

        self.metadata_sources: List[sources.Source] = [
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

        self.pipeline: List[sources.Source] = [
            self.core_source,
            self.unpaywall_source,
            self.pubmed_central_source,
            self.doaj_source,
            self.zenodo_source,
            self.osf_source,
            self.openalex_source,
            self.semantic_scholar_source,
            self.arxiv_source,
            sources.DoiResolverSource(self.session),
        ]

    # -------------------------------------------------------------------------
    # Session and helpers
    # -------------------------------------------------------------------------

    def _create_session(self) -> requests.Session:
        """
        Creates a session that impersonates a real browser to bypass
        client-fingerprinting (e.g., JA3/TLS fingerprinting).
        """

        session = requests_impersonate.Session(impersonate="chrome110")
        session.verify = self.verify_ssl

        if not self.verify_ssl:
            import urllib3

            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            log.warning("SSL verification disabled.")

        return session

    def _generate_filename(self, metadata: Dict[str, Any]) -> str:
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
