import logging
import sys
import os
    
    # Mock dependencies
    with patch("downloader.core.SourceManager") as MockSourceManager:
        
        # Setup mocks
        downloader = Downloader("downloads", "test@example.com", "key")
        
        # Get the mock instance
        mock_sm_instance = downloader.source_manager
        
        # Create mock sources
        mock_crossref = MagicMock()
        mock_crossref.name = "Crossref"
        mock_crossref.get_metadata.return_value = {
            "title": "Test Paper",
            "year": "2023",
            "authors": ["Doe, J."],
            "doi": "10.1234/test",
            "_pdf_url": None
        }

        mock_unpaywall = MagicMock()
        mock_unpaywall.name = "Unpaywall"
        mock_unpaywall.get_metadata.return_value = None
        mock_unpaywall._fetch_and_save.return_value = True # Simulate success here if primary fails, or for pipeline
        mock_unpaywall.download.return_value = True

        # Configure SourceManager mocks
        mock_sm_instance.metadata_sources = [mock_crossref, mock_unpaywall]
        mock_sm_instance.pipeline = [mock_unpaywall]
        mock_sm_instance.unpaywall_source = mock_unpaywall

        # Test download_one
        result = downloader.download_one("10.1234/test")
        
        print(f"Result: {result}")
        
        if result["status"] == "success" and result["source"] == "Unpaywall":
            print("SUCCESS: Download flow verified.")
        else:
            print("FAILURE: Download flow failed.")

if __name__ == "__main__":
    test_download_one_flow()
