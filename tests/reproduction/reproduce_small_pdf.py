import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from src.downloader.sources import Source


class TestSmallPDF(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.filepath = Path(self.temp_dir.name) / "small.pdf"
        
        # Create a concrete implementation of abstract Source
        class ConcreteSource(Source):
            def download(self, doi, filepath, metadata):
                return False
        
        self.source = ConcreteSource(MagicMock())

    def tearDown(self):
        self.temp_dir.cleanup()

        
    def test_validate_small_pdf_fixed(self):
        # This test expects the fix to be applied
        with self.filepath.open("wb") as f:
            f.write(b"%PDF-1.4\nSmall file content\n%%EOF")
            
        try:
            valid = self.source._validate_pdf_structure(self.filepath)
            # It should be valid because it has header and EOF
            self.assertTrue(valid, "Small PDF with valid structure should be valid")
        except OSError:
            self.fail("Should not raise OSError for small files")

if __name__ == "__main__":
    unittest.main()
