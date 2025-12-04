import os
import sys
from unittest.mock import MagicMock
from pathlib import Path

# Mock bibtexparser and rispy
sys.modules["bibtexparser"] = MagicMock()
sys.modules["rispy"] = MagicMock()

# Setup mock return values
def mock_bibtex_loads(text):
    mock_db = MagicMock()
    if "doi={10.1000/1}" in text:
        mock_db.entries = [{"doi": "10.1000/1"}]
    elif "doi={10.1000/6}" in text:
        mock_db.entries = [{"doi": "10.1000/6"}]
    else:
        mock_db.entries = []
    return mock_db

sys.modules["bibtexparser"].loads.side_effect = mock_bibtex_loads

def mock_rispy_loads(text):
    if "DO  - 10.1000/2" in text:
        return [{"doi": "10.1000/2"}]
    elif "DO  - 10.1000/5" in text:
        return [{"doi": "10.1000/5"}]
    return []

sys.modules["rispy"].loads.side_effect = mock_rispy_loads

from src.downloader.parsers import extract_dois_from_file

def test_extract_dois():
    # Create dummy files
    files = {
        "test.bib": "@article{key, doi={10.1000/1}, author={A}}",
        "test.ris": "TY  - JOUR\nDO  - 10.1000/2\nER  -",
        "test.json": '[{"DOI": "10.1000/3"}]',
        "test.txt": "Some text with doi: 10.1000/4",
        "test_ris.txt": "TY  - JOUR\nDO  - 10.1000/5\nER  -",
        "test_bib.txt": "@article{key, doi={10.1000/6}}"
    }

    for filename, content in files.items():
        Path(filename).write_text(content, encoding="utf-8")

    try:
        assert extract_dois_from_file("test.bib") == ["10.1000/1"]
        assert extract_dois_from_file("test.ris") == ["10.1000/2"]
        assert extract_dois_from_file("test.json") == ["10.1000/3"]
        assert extract_dois_from_file("test.txt") == ["10.1000/4"]
        assert extract_dois_from_file("test_ris.txt") == ["10.1000/5"]
        assert extract_dois_from_file("test_bib.txt") == ["10.1000/6"]
        print("SUCCESS: All parser tests passed.")
    except AssertionError as e:
        print(f"FAILURE: Assertion failed: {e}")
    except Exception as e:
        print(f"FAILURE: Exception: {e}")
    finally:
        # Cleanup
        for filename in files:
            try:
                os.remove(filename)
            except:
                pass

if __name__ == "__main__":
    test_extract_dois()
