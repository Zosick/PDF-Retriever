import json
from unittest.mock import patch
from src.downloader import cli

def test_should_show_debug():
    """Test the debug flag logic."""
    assert cli.should_show_debug({"ui_mode": "debug"}) is True
    assert cli.should_show_debug({"ui_mode": "research"}) is False
    assert cli.should_show_debug({}) is False

@patch("src.downloader.cli.CONFIG_FILE")
@patch("src.downloader.cli.FERNET")
def test_load_config_success(mock_fernet, mock_config_file):
    """Test loading and decrypting a valid configuration file."""
    # Setup mock file existance
    mock_config_file.exists.return_value = True
    mock_config_file.read_bytes.return_value = b"encrypted_data"
    
    # Setup mock decryption
    expected_config = {"email": "test@example.com", "ui_mode": "research"}
    mock_fernet.decrypt.return_value = json.dumps(expected_config).encode()
    
    config = cli.load_config()
    
    assert config == expected_config
    mock_fernet.decrypt.assert_called_once_with(b"encrypted_data")

@patch("src.downloader.cli.CONFIG_FILE")
def test_load_config_missing(mock_config_file):
    """Test that load_config returns None if file doesn't exist."""
    mock_config_file.exists.return_value = False
    assert cli.load_config() is None

@patch("src.downloader.cli.CONFIG_FILE")
@patch("src.downloader.cli.FERNET")
def test_load_config_corrupted(mock_fernet, mock_config_file):
    """Test that load_config handles corrupted data gracefully."""
    mock_config_file.exists.return_value = True
    mock_config_file.read_bytes.return_value = b"bad_data"
    
    # Simulate decryption failure
    mock_fernet.decrypt.side_effect = Exception("Decryption failed")
    
    # Should return None and print a warning (printing not captured here)
    config = cli.load_config()
    assert config is None