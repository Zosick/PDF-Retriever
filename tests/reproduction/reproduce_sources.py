import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.downloader.sources import Source


class TestSource(Source):
    def download(self, doi, filepath, metadata):
        return False

class TestSources(unittest.TestCase):
    def setUp(self):
        self.mock_session = MagicMock()
        self.source = TestSource(self.mock_session)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.filepath = Path(self.temp_dir.name) / "test.pdf"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_save_stream_success(self):
        mock_response = MagicMock()
        mock_response.headers = {"Content-Length": "10000", "Content-Type": "application/pdf"}
        mock_response.iter_content.return_value = [b"%PDF-1.4", b" " * 8000, b"%%EOF"]
        
        # Mock file operations to avoid actual disk I/O issues during test if needed, 
        # but using tempfile is better for integration-like testing of _save_stream logic.
        # However, _save_stream writes to a .part file then renames.
        
        result = self.source._save_stream(mock_response, self.filepath)
        self.assertTrue(result)
        self.assertTrue(self.filepath.exists())

    def test_save_stream_invalid_content_type(self):
        mock_response = MagicMock()
        mock_response.headers = {"Content-Type": "text/html"}
        result = self.source._save_stream(mock_response, self.filepath)
        self.assertFalse(result)

    @patch("src.downloader.sources.find_pdf_link_on_page")
    def test_fetch_and_save_direct_pdf(self, mock_find_pdf):
        # Setup mock response for direct PDF
        mock_response = MagicMock()
        mock_response.headers = {"Content-Type": "application/pdf"}
        mock_response.iter_content.return_value = [b"%PDF-1.4", b" " * 8000, b"%%EOF"]
        mock_response.__enter__.return_value = mock_response
        
        self.mock_session.get.return_value = mock_response
        
        result = self.source._fetch_and_save("http://example.com/pdf", self.filepath)
        self.assertTrue(result)

    @patch("src.downloader.sources.find_pdf_link_on_page")
    def test_fetch_and_save_fallback(self, mock_find_pdf):
        # Setup first response as HTML
        mock_response_html = MagicMock()
        mock_response_html.headers = {"Content-Type": "text/html"}
        mock_response_html.__enter__.return_value = mock_response_html
        
        # Setup second response as PDF (fallback)
        mock_response_pdf = MagicMock()
        mock_response_pdf.headers = {"Content-Type": "application/pdf"}
        mock_response_pdf.iter_content.return_value = [b"%PDF-1.4", b" " * 8000, b"%%EOF"]
        mock_response_pdf.__enter__.return_value = mock_response_pdf
        
        self.mock_session.get.side_effect = [mock_response_html, mock_response_pdf]
        mock_find_pdf.return_value = "http://example.com/fallback.pdf"
        
        result = self.source._fetch_and_save("http://example.com/page", self.filepath)
        self.assertTrue(result)

if __name__ == "__main__":
    unittest.main()
