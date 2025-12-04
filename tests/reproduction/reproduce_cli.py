import sys
import unittest
from unittest.mock import MagicMock, patch

# Mock dependencies
sys.modules["src.downloader.settings_manager"] = MagicMock()
sys.modules["src.downloader.tui"] = MagicMock()
sys.modules["rich.logging"] = MagicMock()

from src.downloader.cli import main


class TestCLI(unittest.TestCase):
    @patch("src.downloader.cli.show_main_panel")
    @patch("src.downloader.cli.load_config")
    @patch("src.downloader.cli.should_show_debug")
    @patch("src.downloader.cli.logging")
    def test_main_loop_exit(self, mock_logging, mock_should_show_debug, mock_load_config, mock_show_main_panel):
        # Setup mocks
        mock_load_config.return_value = {}
        mock_should_show_debug.return_value = False
        mock_show_main_panel.side_effect = ["8"] # Simulate user choosing "Quit"

        # Run main
        try:
            main()
        except SystemExit:
            pass

        # Verify interactions
        mock_load_config.assert_called()
        mock_show_main_panel.assert_called()

    @patch("src.downloader.cli.show_main_panel")
    @patch("src.downloader.cli.get_settings")
    @patch("src.downloader.cli.save_config")
    @patch("src.downloader.cli.load_config")
    def test_main_configure_settings(self, mock_load_config, mock_save_config, mock_get_settings, mock_show_main_panel):
        # Setup mocks
        mock_load_config.return_value = {}
        mock_show_main_panel.side_effect = ["1", "8"] # Configure, then Quit
        mock_get_settings.return_value = {"new": "settings"}
        
        # Run main
        try:
            main()
        except SystemExit:
            pass
        
        # Verify interactions
        mock_get_settings.assert_called()
        mock_save_config.assert_called()

if __name__ == "__main__":
    unittest.main()
