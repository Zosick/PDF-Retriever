# src/downloader/sources.py
import logging
import threading
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests

from .utils import find_pdf_link_on_page

log = logging.getLogger(__name__)

class Source(ABC):
    """Abstract base class for a PDF source."""

    def __init__(self, session: requests.Session):
        self.session = session
        self.name = self.__class__.__name__.replace("Source", "")
        self._last_request_time = 0.0
        self._min_request_interval = 2.0
        self._lock = threading.Lock()

    @abstractmethod
    def download(self, doi: str, filepath: Path, metadata: dict[str, Any]) -> bool:
        pass

    def get_metadata(self, doi: str) -> dict[str, Any] | None:
        """
        Retrieves metadata for a DOI. Subclasses can override with caching.
        """
        return None

    def test_connection(self) -> tuple[bool, str]:
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

    def _rate_limit(self) -> None:
        with self._lock:
            elapsed = time.time() - self._last_request_time
            if elapsed < self._min_request_interval:
                time.sleep(self._min_request_interval - elapsed)
            self._last_request_time = time.time()

    def _save_stream(self, resp: requests.Response, filepath: Path) -> bool:
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
                log.warning(f"[{self.name}] File too small ({file_size} bytes).")
                return False
            
            if content_length and abs(file_size - int(content_length)) > 1000:
                log.warning(f"[{self.name}] File size mismatch.")

            with tmp_path.open("rb") as fh:
                header = fh.read(1024)
                if not header.startswith(b"%PDF-"):
                    log.warning(f"[{self.name}] Invalid PDF header.")
                    return False
                fh.seek(-1024, 2)
                if b"%%EOF" not in fh.read(1024):
                    log.warning(f"[{self.name}] Incomplete PDF (missing EOF).")
                    return False

            tmp_path.rename(filepath)
            log.info(f"[{self.name}] Saved PDF: {filepath.name}")
            return True
        except Exception as e:
            log.error(f"[{self.name}] Save error: {e}")
            return False
        finally:
            if tmp_path.exists(): tmp_path.unlink()

<<<<<<< HEAD
    def _fetch_and_save(
        self, url: str, filepath: Path, headers: Optional[Dict[str, str]] = None
    ) -> bool:
        """Convenience method to fetch a URL and save it via the streaming helper."""
        try:
            # Use session's headers as base, then update with any provided headers
            request_headers = self.session.headers.copy()
            request_headers.update(
                {"Accept": "application/pdf,text/html;q=0.9,*/*;q=0.8"}
            )
            if headers:
                request_headers.update(headers)

            self._rate_limit()

            # --- MODIFIED: Removed 'with' statement ---
            r = self.session.get(url, timeout=30, stream=True, headers=request_headers)
            r.raise_for_status()
            content_type = r.headers.get("Content-Type", "").lower()

            if "application/pdf" in content_type:
                return self._save_stream(r, filepath)

            # If not a PDF, assume it's a landing page and try to find a link
            log.debug(
                f"[{self.name}] URL is not a direct PDF link. Trying to find a link on the page."
            )
            pdf_url = find_pdf_link_on_page(url, self.session)
            if pdf_url:
                log.debug(f"[{self.name}] Found direct PDF link: {pdf_url}")

                # --- MODIFIED: Removed 'with' statement ---
                pdf_response = self.session.get(pdf_url, stream=True, timeout=20)
                pdf_response.raise_for_status()
                return self._save_stream(pdf_response, filepath)

            return False
        except requests.RequestException as e:
            log.warning(f"[{self.name}] Fetch failed for {url}: {e}")
            return False

    def _make_request(
        self, url: str, method: str = "GET", **kwargs
    ) -> Optional[requests.Response]:
        """Helper method for making HTTP requests with rate limiting and error handling."""
        log.debug(f"[{self.name}] Making request: {method} {url} {kwargs}")
        try:
            self._rate_limit()

            # --- MODIFIED: Smartly merge headers ---
            if "headers" in kwargs:
                # Merge session headers with provided headers
                merged_headers = self.session.headers.copy()
                merged_headers.update(kwargs["headers"])
                kwargs["headers"] = merged_headers
            # --- END MODIFICATION ---

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
        # --- MODIFIED: Set the correct base URL for the test ---
        self.api_url = "https://api.core.ac.uk/"

    def _get_data(self, doi: str) -> Optional[Dict[str, Any]]:
        if not self.api_key:
            log.debug("CORE API key not provided, skipping.")
            return None

        try:
            # --- MODIFIED: Hardcode the correct v3 API endpoint ---
            # This bypasses the (likely incorrect) config.py URL
            # and fixes the 404 error.
            url = f"https://api.core.ac.uk/v3/works/doi:{quote_plus(doi)}"
            # --- END MODIFICATION ---

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
                pass  # Keep pass to continue trying other sources if this one fails

        if pdf_url:
            return self._fetch_and_save(pdf_url, filepath)
        return False


class SemanticScholarSource(Source):
    """Finds a PDF link via the Semantic Scholar API."""

    def __init__(self, session: requests.Session):
        super().__init__(session)
        # --- MODIFIED: Set the correct base URL for the test ---
        self.api_url = "https://api.semanticscholar.org/"

    def get_metadata(self, doi: str) -> Optional[Dict[str, Any]]:
        """Fetches metadata from Semantic Scholar."""
        try:
            # --- MODIFIED: Hardcode the correct v1 API endpoint ---
            # This fixes the 404 error
            url = (
                f"https://api.semanticscholar.org/graph/v1/paper/DOI:{quote_plus(doi)}"
            )
            # --- END MODIFICATION ---

            response = self._make_request(
                url, timeout=10, params={"fields": "year,title,authors,pdfUrl"}
            )

            if not response or response.status_code != 200:
                return None

            data = response.json()

            year = str(data.get("year", "Unknown"))
            title = data.get("title", "Unknown Title")

            # --- MODIFIED: Check for 'openAccessPdf' first ---
            pdf_url = (data.get("openAccessPdf") or {}).get("url")
            if not pdf_url:
                pdf_url = data.get("pdfUrl")  # Fallback to any pdfUrl
            # --- END MODIFICATION ---

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
                # --- MODIFIED: Hardcode the correct v1 API endpoint ---
                url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{quote_plus(doi)}"
                # --- END MODIFICATION ---

                response = self._make_request(
                    url, timeout=10, params={"fields": "pdfUrl,openAccessPdf"}
                )
                if response and response.status_code == 200:
                    data = response.json()
                    # --- MODIFIED: Check for 'openAccessPdf' first ---
                    pdf_url = (data.get("openAccessPdf") or {}).get("url")
                    if not pdf_url:
                        pdf_url = data.get("pdfUrl")
                    # --- END MODIFICATION ---
            except (requests.RequestException, json.JSONDecodeError) as e:
                log.warning(f"[{self.name}] Failed to re-fetch metadata for {doi}: {e}")
                pass  # Keep pass to continue trying other sources if this one fails

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

            authors = [
                author.find("atom:name", self.ATOM_NS).text
                for author in entry.findall("atom:author", self.ATOM_NS)
            ]

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

            # --- MODIFIED: Create headers to be *merged* ---
            # This fixes the 403 error by not overwriting
            # the browser-impersonation headers.
            headers = {"Accept": "application/pdf"}
            # --- END MODIFICATION ---

            response = self._make_request(url, headers=headers, timeout=20, stream=True)

            if not response:
=======
    def _fetch_and_save(self, url: str, filepath: Path, headers: dict[str, str] | None = None, max_retries: int = 3) -> bool:
        for attempt in range(max_retries):
            try:
                self._rate_limit()
                req_headers = dict(self.session.headers)
                req_headers.update({"Accept": "application/pdf,text/html;q=0.9,*/*;q=0.8"})
                if headers: req_headers.update(headers)
                
                with self.session.get(url, timeout=90, stream=True, headers=req_headers) as r:
                    r.raise_for_status()
                    if "application/pdf" in r.headers.get("Content-Type", "").lower():
                        return self._save_stream(r, filepath)
                    
                    log.debug(f"[{self.name}] scraping fallback for {url}")
                    pdf_url = find_pdf_link_on_page(url, self.session)
                    if pdf_url:
                        with self.session.get(pdf_url, stream=True, timeout=90) as r2:
                            r2.raise_for_status()
                            return self._save_stream(r2, filepath)
>>>>>>> 85cb3d387c185462bcf3032d3f6a75495df95de8
                return False
            except Exception as e:
                if attempt == max_retries - 1: log.warning(f"[{self.name}] Fetch failed: {e}")
                time.sleep((attempt + 1) * 2)
        return False
<<<<<<< HEAD
=======

    def _make_request(self, url: str, method: str = "GET", **kwargs) -> requests.Response | None:
        try:
            self._rate_limit()
            r = self.session.request(method, url, **kwargs)
            r.raise_for_status()
            return r
        except Exception as e:
            log.debug(f"[{self.name}] Request failed: {e}")
            return None
>>>>>>> 85cb3d387c185462bcf3032d3f6a75495df95de8
