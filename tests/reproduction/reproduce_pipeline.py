import logging
import threading
from pathlib import Path
from unittest.mock import MagicMock

from src.downloader.download_pipeline import DownloadPipeline

# Setup logging
logging.basicConfig(level=logging.INFO)

def test_pipeline_flow():
    print("Testing DownloadPipeline flow...")
    
    # Mock dependencies
    mock_source_manager = MagicMock()
    mock_source_manager.metadata_sources = []
    mock_source_manager.pipeline = []
    
    # Mock Unpaywall source specifically
    mock_unpaywall = MagicMock()
    mock_unpaywall.name = "Unpaywall"
    mock_unpaywall.get_metadata.return_value = None
    mock_unpaywall._fetch_and_save.return_value = False
    mock_source_manager.unpaywall_source = mock_unpaywall
    
    # Create pipeline
    stats = {"success": 0, "fail": 0, "skipped": 0, "sources": {}}
    stats_lock = threading.Lock()
    pipeline = DownloadPipeline(mock_source_manager, Path("downloads"), stats, stats_lock)
    
    # Mock metadata_fetcher.fetch_metadata to control flow
    pipeline.metadata_fetcher.fetch_metadata = MagicMock(return_value=(
        {"title": "Test", "year": "2023", "authors": ["Me"], "doi": "10.1234/test"},
        None
    ))
    
    # Mock download_executor methods
    pipeline.download_executor.check_if_skipped = MagicMock(return_value=None)
    pipeline.download_executor.try_primary_pdf = MagicMock(return_value=None)
    pipeline.download_executor.try_pipeline_sources = MagicMock(return_value={
        "doi": "10.1234/test",
        "status": "success",
        "source": "MockSource",
        "filename": "test.pdf",
        "citation": "Me, 2023"
    })
    
    # Test download_one
    result = pipeline.download_one("10.1234/test")
    
    print(f"Result: {result}")
    
    if result["status"] == "success":
        print("SUCCESS: Pipeline flow verified.")
    else:
        print("FAILURE: Pipeline flow failed.")

if __name__ == "__main__":
    test_pipeline_flow()
