import sys
import unittest
from unittest.mock import MagicMock, patch

# Mock modules not available on Windows or missing
sys.modules["termios"] = MagicMock()
sys.modules["tty"] = MagicMock()
sys.modules["select"] = MagicMock()
sys.modules["bibtexparser"] = MagicMock()
sys.modules["rispy"] = MagicMock()

from src.downloader.tui import _get_key_unix

class TestUnixKey(unittest.TestCase):
    @patch("src.downloader.tui.sys.stdin")
    def test_escape_sequence(self, mock_stdin):
        # Simulate Escape followed by [A (Up Arrow)
        # read(1) -> \x1b
        # read(2) -> [A
        mock_stdin.read.side_effect = ["\x1b", "[A"]
        mock_stdin.fileno.return_value = 0
        
        # Mock select to return ready
        sys.modules["select"].select.return_value = ([mock_stdin], [], [])

        key = _get_key_unix()
        self.assertEqual(key, "UP")

    @patch("src.downloader.tui.sys.stdin")
    def test_standalone_escape(self, mock_stdin):
        # Simulate Escape followed by nothing
        # read(1) -> \x1b
        # Should NOT call read(2) if select times out
        mock_stdin.read.side_effect = ["\x1b"]
        mock_stdin.fileno.return_value = 0
        
        # Mock select to return empty (timeout)
        sys.modules["select"].select.return_value = ([], [], [])

        key = _get_key_unix()
        # If fixed, it should return "\x1b" or "ESC"
        self.assertIn(key, ["\x1b", "ESC"])

if __name__ == "__main__":
    unittest.main()
