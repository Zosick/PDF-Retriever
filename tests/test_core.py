import pytest
import responses
import re
from src.downloader.core import Downloader

@pytest.fixture
def mock_output_dir(tmp_path):
    return tmp_path / "downloads"

@pytest.fixture
def downloader(mock_output_dir):
    return Downloader(
        output_dir=str(mock_output_dir),
        email="test@example.com",
        core_api_key=None,
        verify_ssl=True
    )

@responses.activate
def test_download_one_success_unpaywall(downloader, mock_output_dir):
    """Test that a valid DOI with an Unpaywall result downloads correctly."""
    doi = "10.1234/example"

    responses.add(
        responses.GET,
        re.compile(r"https://api\.unpaywall\.org/v2/.*"),
        json={
            "best_oa_location": {"url_for_pdf": "http://example.com/paper.pdf"},
            "title": "Test Paper",
            "year": "2023",
            "z_authors": [{"family": "Smith"}]
        },
        status=200
    )

    # -------- FIX: large enough fake PDF --------
    pdf_body = b"%PDF-1.4\n" + b"0" * 5000 + b"\n%%EOF"
    # -------------------------------------------

    responses.add(
        responses.GET,
        "http://example.com/paper.pdf",
        body=pdf_body,
        headers={
            "Content-Type": "application/pdf",
            "Content-Length": str(len(pdf_body))
        },
        status=200
    )

    result = downloader.download_one(doi)

    assert result["status"] == "success"
    assert result["source"] == "Unpaywall"

    files = list(mock_output_dir.glob("*.pdf"))
    assert len(files) == 1
    assert "Smith" in files[0].name
    assert "Test" in files[0].name


@responses.activate
def test_download_one_failed(downloader):
    """Test that the downloader handles a DOI with no results gracefully."""
    doi = "10.0000/nonexistent"

    responses.add(responses.GET, re.compile(".*"), status=404)

    result = downloader.download_one(doi)
    assert result["status"] == "failed"
    assert result["doi"] == doi
