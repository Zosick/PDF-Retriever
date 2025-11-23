import textwrap

import pytest

from src.downloader.parsers import extract_dois_from_file


def test_extract_bibtex(tmp_path):
    """Test extracting DOIs from a BibTeX file."""
    content = textwrap.dedent("""
    @article{example2023,
        title={Sample Article},
        author={Doe, John},
        doi={10.1038/nature12373},
        year={2023}
    }
    @book{book2022,
        doi={10.1126/science.123456}
    }
    """)
    p = tmp_path / "test.bib"
    p.write_text(content, encoding="utf-8")
    
    dois = extract_dois_from_file(str(p))
    assert "10.1038/nature12373" in dois
    assert "10.1126/science.123456" in dois
    assert len(dois) == 2


def test_extract_ris(tmp_path):
    """Test extracting DOIs from a RIS file."""
    # RIS format is sensitive to whitespace at the start of the line
    content = textwrap.dedent("""
    TY  - JOUR
    TI  - RIS Example
    DO  - 10.1002/andp.19053221004
    ER  -
    """).strip()
    
    p = tmp_path / "test.ris"
    p.write_text(content, encoding="utf-8")
    
    dois = extract_dois_from_file(str(p))
    assert "10.1002/andp.19053221004" in dois


def test_extract_plaintext_and_csv(tmp_path):
    """Test extracting DOIs from plain text and CSV files using regex."""
    
    # Plain text
    content_txt = "Check out this paper 10.1234/test-doi and 10.5678/another-one"
    p_txt = tmp_path / "list.txt"
    p_txt.write_text(content_txt, encoding="utf-8")
    
    dois_txt = extract_dois_from_file(str(p_txt))
    assert "10.1234/test-doi" in dois_txt
    assert "10.5678/another-one" in dois_txt

    # CSV
    content_csv = "ID,DOI,Title\n1,10.9999/csv-doi,Test Title"
    p_csv = tmp_path / "data.csv"
    p_csv.write_text(content_csv, encoding="utf-8")
    
    dois_csv = extract_dois_from_file(str(p_csv))
    assert "10.9999/csv-doi" in dois_csv


def test_extract_json(tmp_path):
    """Test extracting DOIs from CSL/Zotero JSON."""
    content = textwrap.dedent("""
    [
        {
            "id": "item1",
            "DOI": "10.5555/json-doi"
        }
    ]
    """)
    p = tmp_path / "export.json"
    p.write_text(content, encoding="utf-8")
    
    dois = extract_dois_from_file(str(p))
    assert "10.5555/json-doi" in dois


def test_file_not_found():
    """Test that a non-existent file raises the correct error."""
    with pytest.raises(FileNotFoundError):
        extract_dois_from_file("non_existent_file.bib")