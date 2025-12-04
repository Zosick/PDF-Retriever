import sys
from unittest.mock import MagicMock
import xml.etree.ElementTree as ET

# Mock requests
sys.modules["requests"] = MagicMock()

from src.downloader.sources import PubMedCentralSource

def test_get_metadata():
    mock_session = MagicMock()
    source = PubMedCentralSource(mock_session)

    # Mock ESearch response
    mock_esearch_response = MagicMock()
    mock_esearch_response.json.return_value = {
        "esearchresult": {"idlist": ["12345"]}
    }
    
    # Mock EFetch response
    mock_efetch_response = MagicMock()
    mock_efetch_response.content = b"""
        <pmc-articleset>
            <article>
                <front>
                    <article-meta>
                        <article-id pub-id-type="doi">10.1000/1</article-id>
                        <title-group>
                            <article-title>Test Title</article-title>
                        </title-group>
                        <contrib-group>
                            <contrib contrib-type="author">
                                <name><surname>Author</surname></name>
                            </contrib>
                        </contrib-group>
                        <pub-date>
                            <year>2023</year>
                        </pub-date>
                    </article-meta>
                </front>
            </article>
        </pmc-articleset>
    """

    # Configure mock session to return different responses based on URL
    def side_effect(url, params=None, **kwargs):
        if "esearch.fcgi" in url:
            return mock_esearch_response
        elif "efetch.fcgi" in url:
            return mock_efetch_response
        return None

    source._make_request = MagicMock(side_effect=side_effect)

    metadata = source.get_metadata("10.1000/1")
    
    try:
        assert metadata is not None
        assert metadata["title"] == "Test Title"
        assert metadata["year"] == "2023"
        assert metadata["authors"] == ["Author"]
        assert metadata["pmcid"] == "12345"
        print("SUCCESS: PMC metadata extraction passed.")
    except AssertionError as e:
        print(f"FAILURE: Assertion failed: {e}")
    except Exception as e:
        print(f"FAILURE: Exception: {e}")

if __name__ == "__main__":
    test_get_metadata()
