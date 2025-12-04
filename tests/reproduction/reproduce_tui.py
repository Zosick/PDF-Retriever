import sys
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

# Mock dependencies
sys.modules["msvcrt"] = MagicMock()
sys.modules["termios"] = MagicMock()
sys.modules["tty"] = MagicMock()
sys.modules["rich"] = MagicMock()
sys.modules["rich.console"] = MagicMock()
sys.modules["rich.progress"] = MagicMock()
sys.modules["rich.prompt"] = MagicMock()
sys.modules["rich.live"] = MagicMock()
sys.modules["rich.panel"] = MagicMock()
sys.modules["rich.align"] = MagicMock()
sys.modules["rich.text"] = MagicMock()
sys.modules["rich.table"] = MagicMock()
sys.modules["rich.rule"] = MagicMock()

# Mock internal modules
sys.modules["src.downloader.settings_manager"] = MagicMock()
sys.modules["src.downloader.core"] = MagicMock()
sys.modules["src.downloader.parsers"] = MagicMock()
sys.modules["src.downloader.utils"] = MagicMock()

from src.downloader.tui import get_single_key, get_settings, get_dois, run_download

class TestTUI(unittest.TestCase):
    def test_get_single_key_windows(self):
        # Mock msvcrt.getch
        sys.modules["msvcrt"].getch.side_effect = [b"a"]
        key = get_single_key()
        self.assertEqual(key, "a")

    @patch("src.downloader.tui.Prompt.ask")
    def test_get_settings(self, mock_ask):
        mock_ask.side_effect = [
            "downloads", # output_dir
            "email@example.com", # email
            "", # core_api_key
            "5", # max_workers
            "research", # ui_mode
            "n" # ssl
        ]
        cfg = {}
        settings = get_settings(cfg)
        self.assertEqual(settings["output_dir"], "downloads")
        self.assertEqual(settings["email"], "email@example.com")

    @patch("src.downloader.tui.Prompt.ask")
    @patch("src.downloader.tui.extract_dois_from_file")
    def test_get_dois_manual(self, mock_extract, mock_ask):
        mock_ask.side_effect = [
            "", # file input (empty for manual)
            "10.1000/1, 10.1000/2" # manual input
        ]
        # Mock clean_doi to return the input if it looks like a DOI
        with patch("src.downloader.tui.clean_doi", side_effect=lambda x: x):
            dois = get_dois({})
            self.assertEqual(dois, ["10.1000/1", "10.1000/2"])

    @patch("src.downloader.tui.Downloader")
    @patch("src.downloader.tui.Progress")
    @patch("src.downloader.tui.Live")
    @patch("src.downloader.tui.ThreadPoolExecutor")
    def test_run_download(self, mock_executor, mock_live, mock_progress, mock_downloader):
        # Setup mocks
        mock_dl_instance = mock_downloader.return_value
        mock_dl_instance.stats = {"success": 1, "skipped": 0, "fail": 0}
        
        mock_future = MagicMock()
        mock_future.result.return_value = {"doi": "10.1000/1", "status": "success", "source": "Test"}
        
        mock_executor_instance = mock_executor.return_value
        mock_executor_instance.__enter__.return_value = mock_executor_instance
        mock_executor_instance.submit.return_value = mock_future
        
        # Mock as_completed to yield the future
        # Mock as_completed to yield the future
        with patch("src.downloader.tui.as_completed", return_value=[mock_future]):
            run_download({"output_dir": "out", "email": "e", "verify_ssl": True, "max_workers": 1}, ["10.1000/1"])

        # Assertions
        mock_downloader.assert_called_once()
        _, kwargs = mock_downloader.call_args
        self.assertEqual(kwargs["output_dir"], "out")
        self.assertEqual(kwargs["email"], "e")
        self.assertEqual(kwargs["verify_ssl"], True)

        mock_executor.assert_called_once_with(max_workers=1)
        mock_executor_instance.submit.assert_called_once()
        
        # Verify submit was called with the download task and correct arguments
        # Note: submit(task, doi)
        args, _ = mock_executor_instance.submit.call_args
        self.assertEqual(args[1], "10.1000/1")

        mock_future.result.assert_called_once()
        mock_live.return_value.__enter__.assert_called_once()

if __name__ == "__main__":
    unittest.main()
