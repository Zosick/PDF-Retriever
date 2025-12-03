"""
Unit tests for the DownloadManager.
Run this file using 'python -m pytest' in your terminal.
"""

import queue
import threading
import time
from concurrent.futures import CancelledError
from pathlib import Path
from unittest.mock import call

import pytest

# This import will work thanks to pytest.ini
from downloader.download_manager import DownloadManager


@pytest.fixture
def mock_downloader_class(mocker):
    """Mocks the Downloader class at the class level."""
    # This is the correct path to patch, where Downloader is *used*
    mock = mocker.patch("downloader.download_manager.Downloader", autospec=True)
    return mock


@pytest.fixture
def mock_downloader_instance(mock_downloader_class):
    """Provides a mock instance of the Downloader."""

    def download_side_effect(doi, cancel_event):
        """Simulate a successful download."""
        return {
            "status": "success",
            "doi": doi,
            "source": "Mock",
            "citation": f"Mock, {doi}",
        }

    # mock_downloader_class.return_value is the *instance* that will be created
    mock_downloader_class.return_value.download_one.side_effect = download_side_effect
    return mock_downloader_class.return_value


@pytest.fixture
def test_manager_components(mock_downloader_instance):
    """
    Provides the components needed to create a DownloadManager instance.
    This fixture ensures the Downloader is already mocked.
    """
    settings = {
        "output_dir": "/fake/dir",
        "email": "test@example.com",
        "core_api_key": "fake_key",
        "verify_ssl": True,
        "max_workers": 2,
    }
    return {
        "settings": settings,
        "progress_queue": queue.Queue(),
        "dois": ["doi_1", "doi_2"],
        "failed_dois_path": Path("/fake/failed_dois.txt"),
    }


def test_download_success_happy_path(test_manager_components, mock_downloader_instance):
    """
    Tests a full, successful download process.
    """
    manager = DownloadManager(**test_manager_components)
    progress_queue = test_manager_components["progress_queue"]

    # Act
    manager.run()  # Run the thread's main logic directly in this thread

    # Assert
    # 1. Check that the downloader was called correctly
    expected_calls = [
        call("doi_1", manager._cancel_event),
        call("doi_2", manager._cancel_event),
    ]
    mock_downloader_instance.download_one.assert_has_calls(
        expected_calls, any_order=True
    )

    # 2. Check the messages put into the queue
    results = get_all_from_queue(progress_queue)
    statuses = [msg.get("status") for msg in results]

    assert "start" in statuses
    assert "success" in statuses
    assert "complete" in statuses
    assert "finished" in statuses

    summary_msg = next(msg for msg in results if msg["status"] == "complete")
    assert "Success: 2" in summary_msg["message"]
    assert "Failed: 0" in summary_msg["message"]


# --- MODIFIED: This test is now self-contained and correct ---
def test_download_cancellation(mocker):
    """
    Tests that the download process stops cleanly when 'cancel()' is called.
    This test is self-contained and does not use the fixtures above.
    """
    # 1. Patch the Downloader class *before* it's instantiated
    mock_downloader_class = mocker.patch(
        "downloader.download_manager.Downloader", autospec=True
    )

    # This Event lets our test control the "long-running" task
    long_task_event = threading.Event()

    def long_download_side_effect(doi, cancel_event):
        """Simulate a long-running task that waits for an event."""
        # Wait for the test to unblock us, or timeout
        long_task_event.wait(timeout=5)
        # Check if we were cancelled *while* waiting
        if cancel_event.is_set():
            raise CancelledError()
        return {
            "status": "success",
            "doi": doi,
            "source": "Mock",
            "citation": f"Mock, {doi}",
        }

    # Configure the mock *instance* that will be created
    mock_downloader_instance = mock_downloader_class.return_value
    mock_downloader_instance.download_one.side_effect = long_download_side_effect

    # 2. Set up components manually
    settings = {
        "output_dir": "/fake/dir",
        "email": "test@example.com",
        "core_api_key": "fake_key",
        "verify_ssl": True,
        "max_workers": 2,  # Use 2 workers
    }
    progress_queue = queue.Queue()
    dois = ["doi_1", "doi_2", "doi_3", "doi_4"]  # 4 tasks
    failed_dois_path = Path("/fake/failed_dois.txt")

    # 3. Instantiate the DownloadManager (it will get the mock)
    manager = DownloadManager(settings, progress_queue, dois, failed_dois_path)

    # 4. Act
    manager.start()  # Start in a real thread

    # Give it a moment to start up and get tasks in the pool
    time.sleep(0.1)

    # Request cancellation
    manager.cancel_download()

    # Unblock the "hanging" task (if any started)
    long_task_event.set()

    # Wait for the thread to shut down (up to 2s)
    manager.join(timeout=2)

    # 5. Assert
    assert not manager.is_alive()  # Thread must be shut down

    results = get_all_from_queue(progress_queue)
    statuses = [msg.get("status") for msg in results]

    assert "cancelled" in statuses
    assert "complete" not in statuses  # Should not have completed normally
    assert "finished" in statuses


# --- MODIFIED: More robust helper function ---
def get_all_from_queue(q: queue.Queue):
    """Drains a queue and returns a list of items."""
    items = []
    while True:
        try:
            # Wait a reasonable time for messages
            items.append(q.get(timeout=0.1))
        except queue.Empty:
            # When the queue is empty, we're done
            break
    return items
