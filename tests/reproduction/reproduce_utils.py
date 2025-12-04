import sys
import unittest
from unittest.mock import MagicMock, patch
import requests

# Mock internal modules
sys.modules["src.downloader.config"] = MagicMock()
sys.modules["src.downloader.config"].MAX_FILENAME_LEN = 255

from src.downloader.utils import find_pdf_link_on_page, format_authors_apa

class TestUtils(unittest.TestCase):
    def test_format_authors_apa(self):
        self.assertEqual(format_authors_apa(None), "Unknown Author")
        self.assertEqual(format_authors_apa([]), "Unknown Author")
        self.assertEqual(format_authors_apa(["Smith"]), "Smith")
        self.assertEqual(format_authors_apa(["John Smith"]), "Smith")
        self.assertEqual(format_authors_apa(["Smith", "Doe"]), "Smith & Doe")
        self.assertEqual(format_authors_apa(["Smith", "Doe", "Johnson"]), "Smith et al.")

    @patch("src.downloader.utils.BeautifulSoup")
    def test_find_pdf_link_on_page(self, mock_bs):
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "<html></html>"
        mock_session.get.return_value = mock_response

        # Test finding .pdf link
        mock_soup = MagicMock()
        mock_link = MagicMock()
        mock_link.__getitem__.return_value = "http://example.com/file.pdf"
        mock_soup.find_all.return_value = [mock_link]
        mock_bs.return_value = mock_soup

        link = find_pdf_link_on_page("http://example.com", mock_session)
        self.assertEqual(link, "http://example.com/file.pdf")

if __name__ == "__main__":
    unittest.main()
