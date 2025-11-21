import pytest
import responses
import requests
import re
from pathlib import Path
from src.downloader.core import Downloader
from src.downloader.sources import Source

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
    
    # Mock Unpaywall API response
    # We use regex (re.compile) to match the URL because the actual code 
    # appends '?email=...' and encodes the DOI slash as '%2F'
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

    # Mock PDF download
    responses.add(
        responses.GET,
        "http://example.com/paper.pdf",
        body=b"%PDF-1.4 content %%EOF",
        headers={"Content-Type": "application/pdf", "Content-Length": "20"},
        status=200
    )

    result = downloader.download_one(doi)

    # Debug print if it fails again
    if result["status"] != "success":
        print(f"Failed result: {result}")

    assert result["status"] == "success"
    assert result["source"] == "Unpaywall"
    
    # Check file existence
    files = list(mock_output_dir.glob("*.pdf"))
    assert len(files) == 1
    # Filename generation might vary, but keywords should be present
    assert "Smith" in files[0].name
    assert "Test" in files[0].name

@responses.activate
def test_download_one_failed(downloader):
    """Test that the downloader handles a DOI with no results gracefully."""
    doi = "10.0000/nonexistent"
    
    # Mock failures for all metadata sources
    responses.add(responses.GET, re.compile(".*"), status=404)

    result = downloader.download_one(doi)
    assert result["status"] == "failed"
    assert result["doi"] == doi