# downloader/core.py
"""Core Downloader class that orchestrates the PDF fetching process."""

import logging
import random
import threading
from pathlib import Path
from typing import Dict, List, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from . import sources, config
from .pmc_source import PubMedCentralSource
from .doaj_source import DOAJSource
from .zenodo_source import ZenodoSource
from .osf_source import OSFSource
from .crossref_source import CrossrefSource
from .utils import safe_filename, format_authors_apa

log = logging.getLogger(__name__)


class Downloader:
    """
    Manages the PDF download pipeline by orchestrating different sources.
    It handles session creation, filename generation, and download statistics.
    """

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

    def _create_session(self) -> requests.Session:
        """Creates a requests.Session with a user-agent and robust retry logic."""
        session = requests.Session()
        session.headers["User-Agent"] = random.choice(config.USER_AGENTS)
        session.verify = self.verify_ssl

        if not self.verify_ssl:
            import urllib3

            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            log.warning("SSL certificate verification is disabled.")

        retries = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[408, 429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def _generate_filename(self, metadata: Dict[str, Any]) -> str:
        """Generates a unique, safe filename from article metadata."""

        log.debug(f"Generating filename with metadata: {metadata}")
        title = (metadata.get("title") or "Unknown Title").strip()
        log.debug(f"Title from metadata: '{title}'")
        year = (metadata.get("year") or "Unknown").strip()
        authors = metadata.get("authors", [])
        # Format DOI, replacing / with _
        doi_part = metadata.get("doi", "unknown").replace("/", "_")

        log.debug(f"Metadata fields: {list(metadata.keys())}")
        log.debug(f"Using Year: '{year}', Title: '{title}', Authors: {authors}")

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

        # Always append DOI for uniqueness, even if title/author unknown
        parts.append(doi_part)

        # --- FIX: Define 'name' and add .pdf extension ---
        name = " - ".join(parts)
        final_name = safe_filename(name) + ".pdf"
        # --- END FIX ---

        log.debug(f"Final filename: '{final_name}'")
        return final_name

    def _record_outcome(self, doi: str, source_name: str, filename: str):
        """Thread-safe method to record a successful download."""
        log.info(f"Success ({source_name}): {doi} -> {filename}")
        with self._stats_lock:
            self.stats["success"] += 1
            self.stats["sources"][source_name] = (
                self.stats["sources"].get(source_name, 0) + 1
            )

    def download_one(self, doi: str) -> Dict[str, Any]:
        """
        Runs the complete download pipeline for a single DOI.
        """
        log.debug(f"Processing DOI: {doi}")

        metadata = None
        primary_pdf_url = None

        for meta_source in self.metadata_sources:
            log.debug(f"Trying metadata source: {meta_source.name}")
            try:
                temp_meta = meta_source.get_metadata(doi)
                if temp_meta:
                    metadata = temp_meta
                    if temp_meta.get("_pdf_url"):
                        primary_pdf_url = temp_meta.get("_pdf_url")
            except Exception as e:
                log.warning(f"Metadata source {meta_source.name} failed: {e}")

            if metadata:
                log.debug(f"Got metadata from {meta_source.name}")
                if "citation" in metadata:
                    log.debug(f"Citation field: '{metadata['citation']}'")
                else:
                    log.debug("No citation field in metadata")
                break

        if metadata is None or not metadata.get("title") or metadata.get("title") == "Unknown Title":
            log.debug("Metadata is incomplete, trying Crossref as fallback.")
            crossref_meta = self.crossref_source.get_metadata(doi)
            if crossref_meta:
                if metadata:
                    # Update existing metadata but don't overwrite good values
                    existing_meta = metadata.copy()
                    crossref_meta.update(existing_meta)
                    metadata = crossref_meta
                else:
                    metadata = crossref_meta

        if metadata is None:
            log.warning(f"Could not find metadata for {doi}. Using DOI as fallback.")
            metadata = {"doi": doi}
        elif not metadata.get("title") or metadata.get("title") == "Unknown Title":
            log.warning(f"Could not find title for {doi}. Filename will be based on DOI.")

        filename = self._generate_filename(metadata)
        filepath = self.output_dir / filename

        if filepath.exists() and filepath.stat().st_size > 5000:
            log.info(f"Skipping (exists): {filename}")
            with self._stats_lock:
                self.stats["skipped"] += 1
            return {"doi": doi, "status": "skipped", "filename": str(filepath)}

        if primary_pdf_url and self.unpaywall_source._fetch_and_save(
            primary_pdf_url, filepath
        ):
            self._record_outcome(doi, "Unpaywall", filename)
            return {
                "doi": doi,
                "status": "success",
                "source": "Unpaywall",
                "filename": str(filepath),
            }

        for source in self.pipeline:
            if source.download(doi, filepath, metadata):
                self._record_outcome(doi, source.name, filename)
                return {
                    "doi": doi,
                    "status": "success",
                    "source": source.name,
                    "filename": str(filepath),
                }

        # Best effort: try the DOI resolver as a last resort
        if sources.DoiResolverSource(self.session).download(doi, filepath, metadata):
            self._record_outcome(doi, "DoiResolver", filename)
            return {
                "doi": doi,
                "status": "success",
                "source": "DoiResolver",
                "filename": str(filepath),
            }

        log.error(f"Failed to find PDF for: {doi}")
        with self._stats_lock:
            self.stats["fail"] += 1
        return {"doi": doi, "status": "failed"}

