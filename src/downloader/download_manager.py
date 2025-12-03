"""
DownloadManager (Controller/Model)

Handles concurrent downloads, queue updates, and safe cancellation.
Decoupled from the GUI layer.
"""

import queue
import threading
from concurrent.futures import (
    CancelledError,
    Future,
    ThreadPoolExecutor,
    TimeoutError,
    as_completed,
)
from typing import Any
from pathlib import Path  # <-- Make sure Path is imported

from .core import Downloader


# --- MODIFIED: Inherit from threading.Thread ---
class DownloadManager(threading.Thread):
    """Manages the concurrent download process."""

    # --- MODIFIED: Accept 'dois' and 'failed_dois_path' ---
    def __init__(
        self,
        settings: dict,
        progress_queue: queue.Queue,
        dois: list[str],
        failed_dois_path: Path,
    ):
        # --- MODIFIED: Call super().__init__ ---
        super().__init__(daemon=True)

        self.settings = settings
        self.progress_queue = progress_queue
        self.dois = dois

        # --- NEW: Store path and create a lock for fail file ---
        self.failed_dois_path = failed_dois_path
        self.fail_lock = threading.Lock()
        # --- END NEW ---

        self.downloader = Downloader(
            output_dir=settings["output_dir"],
            email=settings["email"],
            core_api_key=settings.get("core_api_key"),
            verify_ssl=settings["verify_ssl"],
        )
        self.executor = None
        self.future_map: dict[Future[Any], str] = {}
        self._cancel_event = threading.Event()

    # --- NEW: Helper to safely write to the fail log ---
    def _log_failure(self, doi: str):
        """Thread-safely appends a failed DOI to the designated file."""
        try:
            with self.fail_lock:
                with open(self.failed_dois_path, "a", encoding="utf-8") as f:
                    f.write(f"{doi}\n")
        except Exception as e:
            # Log to console if writing to file fails
            print(f"CRITICAL: Failed to write to fail_log: {e}")

    # --- MODIFIED: Renamed 'start_download' to 'run' ---
    def run(self):
        """Runs the entire download process in this worker thread."""
        self._cancel_event.clear()
        success, skipped, failed = 0, 0, 0

        try:
            self.progress_queue.put(
                {"status": "start", "message": "--- Starting Download ---"}
            )
            self.executor = ThreadPoolExecutor(max_workers=self.settings["max_workers"])

            self.future_map = {
                self.executor.submit(
                    self.downloader.download_one, doi, self._cancel_event
                ): doi
                for doi in self.dois
            }
            pending_futures = set(self.future_map.keys())

            while pending_futures:
                if self._cancel_event.is_set():
                    break

                try:
                    for future in as_completed(pending_futures, timeout=0.5):
                        pending_futures.remove(future)
                        doi = self.future_map.get(
                            future, "Unknown DOI"
                        )  # Get DOI early
                        try:
                            result = future.result()
                            status = result.get("status", "failed")

                            if status == "success":
                                success += 1
                            elif status == "skipped":
                                skipped += 1
                            else:
                                failed += 1
                                # --- NEW: Log failure ---
                                self._log_failure(result.get("doi", doi))

                            self.progress_queue.put(result)

                        except CancelledError:
                            failed += 1
                            # --- NEW: Log failure ---
                            self._log_failure(doi)
                            self.progress_queue.put(
                                {
                                    "status": "error",
                                    "doi": doi,
                                    "message": "Task was cancelled",
                                }
                            )
                        except Exception as e:
                            failed += 1
                            # --- NEW: Log failure ---
                            self._log_failure(doi)
                            self.progress_queue.put(
                                {
                                    "status": "error",
                                    "doi": doi,
                                    "message": f"Error: {e}",
                                }
                            )

                        if self._cancel_event.is_set():
                            break

                except TimeoutError:
                    pass

            summary_msg = f"Success: {success}\nSkipped: {skipped}\nFailed: {failed}"

            if self._cancel_event.is_set():
                failed += len(pending_futures)
                # --- NEW: Log all remaining futures as failed ---
                for remaining_future in pending_futures:
                    self._log_failure(
                        self.future_map.get(remaining_future, "Unknown DOI")
                    )

                summary_msg = (
                    f"Success: {success}\nSkipped: {skipped}\nFailed: {failed}"
                )
                self.progress_queue.put({"status": "cancelled", "message": summary_msg})
            else:
                self.progress_queue.put({"status": "complete", "message": summary_msg})

        except Exception as e:
            # --- NEW: Log all DOIs as failed on critical error ---
            for doi in self.dois:
                self._log_failure(doi)
            self.progress_queue.put(
                {"status": "critical_error", "message": f"Manager error: {e}"}
            )

        finally:
            if self.executor:
                # --- MODIFIED: Wait for all threads to shut down ---
                self.executor.shutdown(wait=True, cancel_futures=True)
            self.executor = None
            self.future_map = {}
            self.progress_queue.put({"status": "finished"})

    def cancel_download(self):
        """Signals the download process to stop."""
        self._cancel_event.set()
        if self.future_map:
            for future in self.future_map.keys():
                future.cancel()
