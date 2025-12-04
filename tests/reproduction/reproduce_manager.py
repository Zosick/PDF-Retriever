import logging
import queue
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.downloader.download_manager import DownloadManager

# Setup logging
logging.basicConfig(level=logging.INFO)

def test_download_manager_run():
    print("Testing DownloadManager.run flow...")
    
    # Mock settings
    settings = {
        "output_dir": "downloads",
        "email": "test@example.com",
        "core_api_key": "key",
        "verify_ssl": True,
        "max_workers": 2
    }
    
    # Mock queue and path
    progress_queue = queue.Queue()
    failed_dois_path = Path("failed_dois.txt")
    if failed_dois_path.exists():
        failed_dois_path.unlink()
        
    dois = ["10.1234/test1", "10.1234/test2", "10.1234/test3"]
    
    # Mock Downloader
    with patch("src.downloader.download_manager.Downloader") as MockDownloader:
        mock_downloader_instance = MockDownloader.return_value
        
        # Define side effects for download_one
        def download_side_effect(doi, cancel_event):
            if cancel_event.is_set():
                return {"doi": doi, "status": "error", "message": "Cancelled"}
            
            if doi == "10.1234/test1":
                return {"doi": doi, "status": "success", "filename": "test1.pdf"}
            elif doi == "10.1234/test2":
                return {"doi": doi, "status": "skipped", "filename": "test2.pdf"}
            else:
                raise Exception("Download failed")
                
        mock_downloader_instance.download_one.side_effect = download_side_effect
        
        # Initialize Manager
        manager = DownloadManager(settings, progress_queue, dois, failed_dois_path)
        
        # Run manager (not as a thread for easier testing, or join if thread)
        manager.start()
        manager.join()
        
        # Check results
        results = []
        while not progress_queue.empty():
            results.append(progress_queue.get())
            
        print(f"Queue results: {len(results)}")
        
        success_count = 0
        skipped_count = 0
        error_count = 0
        
        for res in results:
            if res.get("status") == "success":
                success_count += 1
            elif res.get("status") == "skipped":
                skipped_count += 1
            elif res.get("status") == "error":
                error_count += 1
                
        print(f"Success: {success_count}, Skipped: {skipped_count}, Error: {error_count}")
        
        if success_count == 1 and skipped_count == 1 and error_count == 1:
            print("SUCCESS: Manager flow verified.")
        else:
            print("FAILURE: Manager flow mismatch.")
            
        # Check fail log
        if failed_dois_path.exists():
            with open(failed_dois_path, "r") as f:
                content = f.read()
                print(f"Fail log content: {content.strip()}")
                if "10.1234/test3" in content:
                     print("SUCCESS: Fail log verified.")
                else:
                     print("FAILURE: Fail log missing failed DOI.")
        else:
            print("FAILURE: Fail log not created.")

        # Clean up
        if failed_dois_path.exists():
            failed_dois_path.unlink()

if __name__ == "__main__":
    test_download_manager_run()
