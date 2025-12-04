import sys
import unittest
from unittest.mock import MagicMock, patch

# Mock modules not available on Windows or missing
sys.modules["termios"] = MagicMock()
sys.modules["tty"] = MagicMock()
sys.modules["select"] = MagicMock()
sys.modules["bibtexparser"] = MagicMock()
sys.modules["rispy"] = MagicMock()

from src.downloader.tui import _prompt_for_workers


class TestWorkerInput(unittest.TestCase):
    @patch("src.downloader.tui.Prompt.ask")
    def test_prompt_for_workers_invalid_input(self, mock_ask):
        # Simulate invalid input "abc" then valid "5"
        mock_ask.side_effect = ["abc", "5"]
        
        # This should NOT raise ValueError anymore
        workers = _prompt_for_workers({})
        self.assertEqual(workers, 5)

    @patch("src.downloader.tui.Prompt.ask")
    def test_prompt_for_workers_valid_input(self, mock_ask):
        mock_ask.return_value = "5"
        workers = _prompt_for_workers({})
        self.assertEqual(workers, 5)

if __name__ == "__main__":
    unittest.main()
