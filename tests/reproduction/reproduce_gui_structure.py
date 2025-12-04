import sys
from unittest.mock import MagicMock

# Mock customtkinter and tkinter
sys.modules["customtkinter"] = MagicMock()
sys.modules["tkinter"] = MagicMock()
sys.modules["tkinter.filedialog"] = MagicMock()
sys.modules["tkinter.messagebox"] = MagicMock()

# Mock other dependencies that might cause issues
sys.modules["src.downloader.core"] = MagicMock()
sys.modules["src.downloader.download_manager"] = MagicMock()
sys.modules["src.downloader.protocol"] = MagicMock()
sys.modules["src.downloader.utils"] = MagicMock()
sys.modules["src.downloader.parsers"] = MagicMock()
sys.modules["src.downloader.settings_manager"] = MagicMock()

try:
    from src.downloader.gui.app import App
    from src.downloader.gui.settings_frame import SettingsFrame
    from src.downloader.gui.doi_frame import DoiFrame
    from src.downloader.gui.right_frame import RightFrame
    
    print("SUCCESS: Imports successful.")
    
    # Try to instantiate App (with mocks)
    # We need to mock the superclass __init__ if it does anything complex, 
    # but MagicMock should handle it.
    
    print("Attempting to instantiate App...")
    app = App()
    print("SUCCESS: App instantiated.")
    
except ImportError as e:
    print(f"FAILURE: ImportError: {e}")
except Exception as e:
    print(f"FAILURE: Exception: {e}")
