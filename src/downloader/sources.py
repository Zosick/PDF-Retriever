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

    def _fetch_and_save(self, url: str, filepath: Path, headers: dict[str, str] | None = None, max_retries: int = 3) -> bool:
        for attempt in range(max_retries):
            try:
                self._rate_limit()
                req_headers = self.session.headers.copy()
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
                return False
            except Exception as e:
                if attempt == max_retries - 1: log.warning(f"[{self.name}] Fetch failed: {e}")
                time.sleep((attempt + 1) * 2)
        return False

    def _make_request(self, url: str, method: str = "GET", **kwargs) -> requests.Response | None:
        try:
            self._rate_limit()
            r = self.session.request(method, url, **kwargs)
            r.raise_for_status()
            return r
        except Exception as e:
            log.debug(f"[{self.name}] Request failed: {e}")
            return None