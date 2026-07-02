import logging
from unittest.mock import patch, mock_open
import pytest
import shlex
from termstory.formatter import get_operator_handle, get_github_avatar_ascii

def test_logging_on_exception():
    with patch('termstory.formatter.logger') as mock_logger:
        with patch('subprocess.run', side_effect=Exception("subprocess failed")):
            try:
                get_operator_handle()
            except Exception:
                pass
        # Ensure at least one log method was called (error, exception, warning, debug, etc.)
        assert mock_logger.method_calls, "No log calls were made when an exception occurred"

def test_oserror_handling():
    with patch('termstory.formatter.logger') as mock_logger:
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open()) as mock_file:
                mock_file.side_effect = OSError("Disk full")
                try:
                    get_github_avatar_ascii("testuser")
                except OSError:
                    pass
        mock_logger.warning.assert_called_once()
        # The actual message logged is "Failed to read avatar from disk cache"
        assert "Failed to read avatar from disk cache" in mock_logger.warning.call_args[0][0]

def test_valueerror_fallback():
    def split_command(cmd):
        try:
            return shlex.split(cmd)
        except ValueError:
            return cmd.split()
    malformed = "echo 'unclosed quote"
    result = split_command(malformed)
    assert result == malformed.split()

def test_debug_logs_config_unavailable():
    with patch('termstory.formatter.logger') as mock_logger:
        with patch('configparser.ConfigParser.read', return_value=[]):
            with patch('subprocess.run', side_effect=Exception("git not found")):
                get_operator_handle()
        # Ensure debug logging was called at least once
        debug_calls = [call for call in mock_logger.method_calls if call[0] == 'debug']
        assert debug_calls, "No debug log emitted when config/git was unavailable"
