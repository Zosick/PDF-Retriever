# downloader/sources.py
"""
Defines the abstract base class for a PDF source and its implementations.
Each source is responsible for finding and downloading a PDF for a given DOI.
"""
import logging
import re
import time
import json
import threading  # <--- ADDED THIS
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Tuple, List, Optional
from urllib.parse import quote_plus, urljoin
import requests
from . import config
from .exceptions import UnrecoverableError
from .utils import find_pdf_link_on_page

log = logging.getLogger(__name__)


class Source(ABC):
    """Abstract base class for a PDF source."""

    def __init__(self, session: requests.Session):
        self.session = session
        self.name = self.__class__.__name__.replace("Source", "")
        self._last_request_time = 0
        self._min_request_interval = 2.0
        self._lock = threading.Lock()     # <--- ADDED THREAD LOCK

    @abstractmethod
    def download(self, doi: str, filepath: Path, metadata: Dict[str, Any]) -> bool:
        """Attempt to download a PDF for the given DOI. Returns True on success."""
        pass

    def get_metadata(self, doi: str) -> Optional[Dict[str, Any]]:
        """(Optional) Fetches metadata for a DOI. Not all sources implement this."""
        return None

    def test_connection(self) -> Tuple[bool, str]:
        """Runs a simple test to check if the source is configured and reachable."""
        base_url = getattr(self, "api_url", None)
        if base_url:
            try:
                domain = urljoin(base_url, "/")
                r = self.session.get(domain, timeout=5)
                r.raise_for_status()
                return (True, "API is reachable")
            except Exception as e:
                log.debug(f"[{self.name}] Test ping failed: {e}")
                return (False, "API may be unreachable")
        return (True, "No test implemented")

    def _rate_limit(self):
        """Basic rate limiting to be respectful to APIs"""
        # <--- CRITICAL FIX: THREAD SAFETY --->
        with self._lock:
            elapsed = time.time() - self._last_request_time
            if elapsed < self._min_request_interval:
                time.sleep(self._min_request_interval - elapsed)
            self._last_request_time = time.time()

    def _save_stream(self, resp: requests.Response, filepath: Path) -> bool:
        """
        Saves a response stream to a file with size and content validation.
        Writes to a temporary '.part' file first to prevent corruption.
        """
        tmp_path = filepath.with_suffix(".part")
        content_length = resp.headers.get("Content-Length")
        content_type = resp.headers.get("Content-Type", "").lower()

        if "application/pdf" not in content_type:
            log.warning(f"[{self.name}] Content-Type is not PDF ({content_type})")
            return False

        try:
            with tmp_path.open("wb") as fh:
                for chunk in resp.iter_content(chunk_size=8192):
                    fh.write(chunk)

            file_size = tmp_path.stat().st_size

            if file_size < 5000:
                log.warning(
                    f"[{self.name}] File too small ({file_size} bytes), likely an error page."
                )
                return False

            if content_length and abs(file_size - int(content_length)) > 1000:
                log.warning(
                    f"[{self.name}] File size mismatch: expected {content_length}, got {file_size}"
                )

            with tmp_path.open("rb") as fh:
                header = fh.read(1024)
                if not header.startswith(b"%PDF-"):
                    header_lower = header.lower()
                    if (
                        b"html" in header_lower
                        or b"error" in header_lower
                        or b"not found" in header_lower
                        or b"<!doctype" in header_lower
                        or b"access denied" in header_lower
                        or b"forbidden" in header_lower
                    ):
                        log.warning(
                            f"[{self.name}] File appears to be an error page, not a PDF"
                        )
                        return False
                    log.warning(f"[{self.name}] File does not have PDF signature")
                    return False
                
                # Check for PDF EOF marker to ensure file is complete
                fh.seek(-1024, 2)
                footer = fh.read(1024)
                if b"%%EOF" not in footer:
                    log.warning(f"[{self.name}] PDF file appears incomplete (missing EOF marker)")
                    return False

            tmp_path.rename(filepath)
            log.info(f"[{self.name}] Successfully saved PDF ({file_size} bytes)")
            return True

        except Exception as exc:
            log.error(
                f"[{self.name}] Save failed for {filepath.name}: {exc}", exc_info=True
            )
            return False
        finally:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)

    def _fetch_and_save(
        self, url: str, filepath: Path, headers: Optional[Dict[str, str]] = None, max_retries: int = 3
    ) -> bool:
        """Convenience method to fetch a URL and save it via the streaming helper with retry logic."""
        for attempt in range(max_retries):
            try:
                request_headers = self.session.headers.copy()
                request_headers.update({"Accept": "application/pdf,text/html;q=0.9,*/*;q=0.8"})
                if headers:
                    request_headers.update(headers)

                self._rate_limit()
                timeout = 90
                
                with self.session.get(
                    url, timeout=timeout, stream=True, headers=request_headers
                ) as r:
                    r.raise_for_status()
                    content_type = r.headers.get("Content-Type", "").lower()

                    if "application/pdf" in content_type:
                        return self._save_stream(r, filepath)

                    log.debug(f"[{self.name}] URL is not a direct PDF link. Trying to find a link on the page.")
                    pdf_url = find_pdf_link_on_page(url, self.session)
                    if pdf_url:
                        log.debug(f"[{self.name}] Found direct PDF link: {pdf_url}")
                        with self.session.get(
                            pdf_url, stream=True, timeout=timeout
                        ) as pdf_response:
                            pdf_response.raise_for_status()
                            return self._save_stream(pdf_response, filepath)

                return False
            except (requests.Timeout, requests.ConnectionError) as e:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    log.debug(f"[{self.name}] Retry {attempt + 1}/{max_retries} after {wait_time}s: {e}")
                    time.sleep(wait_time)
                    continue
                log.warning(f"[{self.name}] Fetch failed after {max_retries} attempts for {url}: {e}")
                return False
            except requests.RequestException as e:
                log.warning(f"[{self.name}] Fetch failed for {url}: {e}")
                return False
        return False

    def _make_request(
        self, url: str, method: str = "GET", **kwargs
    ) -> Optional[requests.Response]:
        """Helper method for making HTTP requests with rate limiting and error handling."""
        log.debug(f"[{self.name}] Making request: {method} {url} {kwargs}")
        try:
            self._rate_limit()
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            log.debug(f"[{self.name}] Request failed for {url}: {e}")
            return None

class UnpaywallSource(Source):
    """Gets metadata and the primary Open Access PDF link from Unpaywall."""

    def __init__(self, session: requests.Session, email: str):
        super().__init__(session)
        self.email = email
        self.api_url = config.UNPAYWALL_API_URL

    def get_metadata(self, doi: str) -> Optional[Dict[str, Any]]:
        """Fetches metadata and the best OA link for a DOI."""
        if not self.email:
            log.warning("Unpaywall email not provided, cannot fetch metadata.")
            return None

        try:
            url = config.UNPAYWALL_API_URL.format(doi=quote_plus(doi))
            response = self._make_request(url, params={"email": self.email}, timeout=10)
            if not response:
                return None

            data = response.json()

            year = str(data.get("year", "Unknown"))
            title = data.get("title", "Unknown Title")
            pdf_url = (data.get("best_oa_location") or {}).get("url_for_pdf")

            # Get authors
            authors = [author.get("family") for author in data.get("z_authors", [])]

            meta = {
                "year": year,
                "title": title,
                "authors": authors,
                "doi": doi,
                "_pdf_url": pdf_url,
            }
            return meta
        except (requests.RequestException, json.JSONDecodeError, KeyError) as e:
            log.warning(f"Unpaywall metadata request failed for {doi}: {e}")
            return None

    def download(self, doi: str, filepath: Path, metadata: Dict[str, Any]) -> bool:
        pdf_url = metadata.get("_pdf_url")
        if not pdf_url:
            # If _pdf_url is not in the provided metadata, try to get fresh metadata
            meta = self.get_metadata(doi)
            pdf_url = meta.get("_pdf_url") if meta else None

        if pdf_url:
            return self._fetch_and_save(pdf_url, filepath)
        return False

    def test_connection(self) -> Tuple[bool, str]:
        if not self.email:
            return (False, "Email not configured")
        try:
            test_doi = "10.1038/nature12373"
            url = config.UNPAYWALL_API_URL.format(doi=quote_plus(test_doi))
            response = self._make_request(url, params={"email": self.email}, timeout=5)

            if not response:
                return (False, "API unreachable")
            if response.status_code == 403:
                return (False, "Email may be invalid or blocked")

            return (True, "Email and API are valid")
        except Exception as e:
            log.debug(f"[{self.name}] Test failed: {e}")
            return (False, "API unreachable")


class CoreApiSource(Source):
    """Fetches metadata and OA links from the CORE API (v3)."""

    def __init__(self, session: requests.Session, api_key: Optional[str]):
        super().__init__(session)
        self.api_key = api_key
        self.api_url = config.CORE_API_URL

    def _get_data(self, doi: str) -> Optional[Dict[str, Any]]:
        if not self.api_key:
            log.debug("CORE API key not provided, skipping.")
            return None

        try:
            url = config.CORE_API_URL.format(doi=quote_plus(doi))
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json",
            }
            response = self._make_request(url, headers=headers, timeout=10)

            if not response:
                return None

            if response.status_code == 404:
                log.debug(f"[{self.name}] DOI not found in CORE: {doi}")
                return None
            if response.status_code == 401:
                log.error(f"[{self.name}] Unauthorized — invalid CORE API key")
                return None
            if response.status_code == 429:
                log.warning(f"[{self.name}] Rate limited by CORE API")
                return None

            return response.json()

        except (requests.RequestException, json.JSONDecodeError) as e:
            log.warning(f"[{self.name}] CORE request failed for {doi}: {e}")
            return None

    def get_metadata(self, doi: str) -> Optional[Dict[str, Any]]:
        data = self._get_data(doi)
        if not data:
            return None

        try:
            year = str(data.get("year", "Unknown"))
            title = data.get("title", "Unknown Title")
            pdf_url = data.get("fullTextLink")
            authors = [author.get("name") for author in data.get("authors", [])]

            return {
                "year": year,
                "title": title,
                "authors": authors,
                "doi": data.get("doi", doi),
                "_pdf_url": pdf_url,
            }
        except (KeyError, IndexError, AttributeError) as e:
            log.warning(f"[{self.name}] Metadata parsing failed for {doi}: {e}")
            return None

    def download(self, doi: str, filepath: Path, metadata: Dict[str, Any]) -> bool:
        pdf_url = metadata.get("_pdf_url")
        if not pdf_url:
            data = self._get_data(doi)
            pdf_url = data.get("fullTextLink") if data else None

        if not pdf_url:
            log.debug(f"[{self.name}] No PDF link found for {doi}")
            return False

        if pdf_url.endswith(".pdf") or "pdf" in pdf_url.lower():
            return self._fetch_and_save(pdf_url, filepath)

        log.debug(f"[{self.name}] Not a direct PDF link: {pdf_url}")
        return False

    def test_connection(self) -> Tuple[bool, str]:
        if not self.api_key:
            return (False, "API Key not configured")
        try:
            url = "https://api.core.ac.uk/v3/search/works"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json",
            }
            payload = {"q": "science", "limit": 1}

            response = self._make_request(
                url, method="POST", headers=headers, json=payload, timeout=5
            )

            if not response:
                return (False, "API unreachable")
            if response.status_code == 401:
                return (False, "401 Unauthorized (Invalid API Key)")
            if response.status_code == 429:
                return (False, "429 Rate Limited")

            return (True, "CORE API reachable (Key accepted)")

        except Exception as e:
            log.debug(f"[{self.name}] CORE connection test failed: {e}")
            return (False, "API unreachable")


class OpenAlexSource(Source):
    """Finds a PDF link via the OpenAlex API."""

    def __init__(self, session: requests.Session):
        super().__init__(session)
        self.api_url = config.OPENALEX_API_URL

    def get_metadata(self, doi: str) -> Optional[Dict[str, Any]]:
        """Fetches metadata from OpenAlex."""
        try:
            url = config.OPENALEX_API_URL.format(doi=quote_plus(doi))
            response = self._make_request(url, timeout=10)

            if not response or response.status_code != 200:
                return None

            data = response.json()

            year = str(data.get("publication_year", "Unknown"))
            title = data.get("title", "Unknown Title")
            pdf_url = data.get("open_access", {}).get("oa_url")
            authors = [author.get("au_name") for author in data.get("authorships", [])]

            return {
                "year": year,
                "title": title,
                "authors": authors,
                "doi": doi,
                "_pdf_url": pdf_url,
            }
        except (requests.RequestException, json.JSONDecodeError, KeyError) as e:
            log.debug(f"[{self.name}] Metadata lookup failed for {doi}: {e}")
            return None

    def download(self, doi: str, filepath: Path, metadata: Dict[str, Any]) -> bool:
        pdf_url = metadata.get("_pdf_url")
        if not pdf_url:
            try:
                url = config.OPENALEX_API_URL.format(doi=quote_plus(doi))
                response = self._make_request(url, timeout=10)
                if response and response.status_code == 200:
                    data = response.json()
                    pdf_url = data.get("open_access", {}).get("oa_url")
            except (requests.RequestException, json.JSONDecodeError) as e:
                log.warning(f"[{self.name}] Failed to re-fetch metadata for {doi}: {e}")
                pass # Keep pass to continue trying other sources if this one fails

        if pdf_url:
            return self._fetch_and_save(pdf_url, filepath)
        return False


class SemanticScholarSource(Source):
    """Finds a PDF link via the Semantic Scholar API."""

    def __init__(self, session: requests.Session):
        super().__init__(session)
        self.api_url = config.SEMANTIC_SCHOLAR_API_URL

    def get_metadata(self, doi: str) -> Optional[Dict[str, Any]]:
        """Fetches metadata from Semantic Scholar."""
        try:
            url = config.SEMANTIC_SCHOLAR_API_URL.format(doi=quote_plus(doi))
            response = self._make_request(url, timeout=10)

            if not response or response.status_code != 200:
                return None

            data = response.json()

            year = str(data.get("year", "Unknown"))
            title = data.get("title", "Unknown Title")
            pdf_url = data.get("pdfUrl")
            authors = [author.get("name") for author in data.get("authors", [])]

            return {
                "year": year,
                "title": title,
                "authors": authors,
                "doi": doi,
                "_pdf_url": pdf_url,
            }
        except (requests.RequestException, json.JSONDecodeError, KeyError) as e:
            log.debug(f"[{self.name}] Metadata lookup failed for {doi}: {e}")
            return None

    def download(self, doi: str, filepath: Path, metadata: Dict[str, Any]) -> bool:
        pdf_url = metadata.get("_pdf_url")
        if not pdf_url:
            try:
                url = config.SEMANTIC_SCHOLAR_API_URL.format(doi=quote_plus(doi))
                response = self._make_request(url, timeout=10)
                if response and response.status_code == 200:
                    pdf_url = response.json().get("pdfUrl")
            except (requests.RequestException, json.JSONDecodeError) as e:
                log.warning(f"[{self.name}] Failed to re-fetch metadata for {doi}: {e}")
                pass # Keep pass to continue trying other sources if this one fails

        if pdf_url:
            return self._fetch_and_save(pdf_url, filepath)
        return False


class ArxivSource(Source):
    """Fetches metadata and PDF link from arXiv."""

    ARXIV_DOI_REGEX = r"10\.48550/arXiv\.(\d+\.\d+v?\d*)"
    ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}

    def __init__(self, session: requests.Session):
        super().__init__(session)
        self.api_url = config.ARXIV_API_URL

    def _get_arxiv_id(self, doi: str) -> Optional[str]:
        """Extracts the arXiv ID (e.g., '1234.5678') from a DOI."""
        if m := re.search(self.ARXIV_DOI_REGEX, doi, flags=re.IGNORECASE):
            return m.group(1)
        return None

    def get_metadata(self, doi: str) -> Optional[Dict[str, Any]]:
        """Fetches metadata from the arXiv API."""
        arxiv_id = self._get_arxiv_id(doi)
        if not arxiv_id:
            return None

        try:
            url = f"{config.ARXIV_API_URL}?id_list={arxiv_id}"
            response = self._make_request(url, timeout=10)

            if not response:
                return None

            root = ET.fromstring(response.text)
            entry = root.find("atom:entry", self.ATOM_NS)
            if entry is None:
                log.debug(f"[{self.name}] No <entry> tag found in arXiv response.")
                return None

            title_elem = entry.find("atom:title", self.ATOM_NS)
            title = (title_elem.text or "Unknown Title").strip().replace("\n", " ")

            published_elem = entry.find("atom:published", self.ATOM_NS)
            year = (published_elem.text or "Unknown").split("-")[0]

            authors = [author.find('atom:name', self.ATOM_NS).text for author in entry.findall('atom:author', self.ATOM_NS)]

            return {
                "year": year,
                "title": title,
                "authors": authors,
                "doi": doi,
            }
        except (requests.RequestException, ET.ParseError, AttributeError) as e:
            log.warning(f"[{self.name}] Metadata request failed for {doi}: {e}")
            return None

    def download(self, doi: str, filepath: Path, metadata: Dict[str, Any]) -> bool:
        """Constructs a direct PDF link for an arXiv DOI."""
        arxiv_id = self._get_arxiv_id(doi)
        if arxiv_id:
            pdf_url = config.ARXIV_PDF_URL.format(arxiv_id=arxiv_id)
            return self._fetch_and_save(pdf_url, filepath)
        return False


class DoiResolverSource(Source):
    """Attempts to download a PDF directly from the DOI resolver."""

    def __init__(self, session: requests.Session):
        super().__init__(session)
        self.api_url = config.DOI_RESOLVER_URL

    def download(self, doi: str, filepath: Path, metadata: Dict[str, Any]) -> bool:
        try:
            url = config.DOI_RESOLVER_URL.format(doi=quote_plus(doi))
            headers = {"Accept": "application/pdf"}
            response = self._make_request(url, headers=headers, timeout=20, stream=True)

            if not response:
                return False

            return self._save_stream(response, filepath)

        except requests.RequestException:
            pass
        return False



