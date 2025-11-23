import unittest
from unittest.mock import patch, MagicMock
import tkinter

# Mock customtkinter before importing the GUI
import sys

# Mock the customtkinter library
sys.modules['customtkinter'] = MagicMock()

from src.downloader import gui

@unittest.skip("GUI tests require a display")
class TestGUI(unittest.TestCase):

    @patch('src.downloader.gui.settings_manager')
    def test_load_settings(self, mock_settings_manager):
        mock_settings_manager.read_config_raw.return_value = {
            "output_dir": "/test/dir",
            "email": "test@example.com",
            "core_api_key": "test_key",
            "verify_ssl": False
        }

        app = gui.App()

        app.output_dir_entry.insert.assert_called_with(0, "/test/dir")
        app.email_entry.insert.assert_called_with(0, "test@example.com")
        app.core_api_key_entry.insert.assert_called_with(0, "test_key")
        app.ssl_checkbox.select.assert_called_once()

    @patch('src.downloader.gui.settings_manager')
    def test_save_settings(self, mock_settings_manager):
        app = gui.App()
        app.output_dir_entry.get.return_value = "/test/dir"
        app.email_entry.get.return_value = "test@example.com"
        app.core_api_key_entry.get.return_value = "test_key"
        app.ssl_checkbox.get.return_value = 1 # Corresponds to True (checked)

        app.save_settings()

        expected_settings = {
            "output_dir": "/test/dir",
            "email": "test@example.com",
            "core_api_key": "test_key",
            "verify_ssl": False, # Not of the checkbox value
        }
        mock_settings_manager.write_config_raw.assert_called_with(expected_settings)

    def test_get_dois_from_textbox(self):
        app = gui.App()
        app.doi_textbox.get.return_value = "10.1000/123, 10.1000/456\n10.1000/789"

        dois = app.get_dois_from_textbox()

        self.assertEqual(dois, ["10.1000/123", "10.1000/456", "10.1000/789"])

    @patch('src.downloader.gui.Downloader')
    @patch('src.downloader.gui.threading.Thread')
    def test_start_download(self, mock_thread, mock_downloader):
        app = gui.App()
        app.start_download()
        mock_thread.assert_called_with(target=app.start_download_thread)
        mock_thread.return_value.start.assert_called_once()

if __name__ == '__main__':
    unittest.main()