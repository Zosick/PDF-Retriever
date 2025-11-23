import sys
import os

# Add the project root to sys.path
sys.path.insert(0, os.getcwd())

try:
    from src.downloader.core import Downloader
    print("Successfully imported Downloader")
except Exception as e:
    print(f"Failed to import Downloader: {e}")
    import traceback
    traceback.print_exc()
