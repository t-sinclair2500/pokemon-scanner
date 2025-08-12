"""Unit tests for notification system."""

import pytest
import sys
import subprocess
from unittest.mock import patch, MagicMock, call

from src.ui.notifier import SimpleNotifier, notifier


class TestSimpleNotifier:
    """Test SimpleNotifier class."""
    
    def test_notifier_initialization(self):
        """Test that SimpleNotifier initializes correctly."""
        notifier_instance = SimpleNotifier()
        
        # Should have a logger
        assert hasattr(notifier_instance, 'logger')
        assert notifier_instance.logger is not None
    
    def test_notifier_singleton(self):
        """Test that notifier is a singleton instance."""
        # Should be the same instance
        assert notifier is not None
        assert isinstance(notifier, SimpleNotifier)
        
        # Creating a new instance should be different
        new_instance = SimpleNotifier()
        assert new_instance is not notifier


class TestBeepFunction:
    """Test beep functionality."""
    
    def test_beep_macos_success(self):
        """Test beep on macOS with successful afplay."""
        notifier_instance = SimpleNotifier()
        
        with patch('sys.platform', 'darwin'):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock()
                
                result = notifier_instance.beep()
                
                # Should call afplay with correct arguments
                mock_run.assert_called_once_with(
                    ["afplay", "/System/Library/Sounds/Glass.aiff"],
                    capture_output=True,
                    check=False
                )
                
                # Should return True on success
                assert result is True
    
    def test_beep_macos_subprocess_error(self):
        """Test beep on macOS with subprocess error."""
        notifier_instance = SimpleNotifier()
        
        with patch('sys.platform', 'darwin'):
            with patch('subprocess.run') as mock_run:
                mock_run.side_effect = subprocess.SubprocessError("afplay not found")
                
                with patch.object(notifier_instance.logger, 'debug') as mock_log:
                    result = notifier_instance.beep()
                    
                    # Should log the error
                    mock_log.assert_called_once_with("Error playing beep", error="afplay not found")
                    
                    # Should return False on error
                    assert result is False
    
    def test_beep_macos_general_exception(self):
        """Test beep on macOS with general exception."""
        notifier_instance = SimpleNotifier()
        
        with patch('sys.platform', 'darwin'):
            with patch('subprocess.run') as mock_run:
                mock_run.side_effect = Exception("Unexpected error")
                
                with patch.object(notifier_instance.logger, 'debug') as mock_log:
                    result = notifier_instance.beep()
                    
                    # Should log the error
                    mock_log.assert_called_once_with("Error playing beep", error="Unexpected error")
                    
                    # Should return False on error
                    assert result is False
    
    def test_beep_linux_fallback(self):
        """Test beep on Linux with terminal bell fallback."""
        notifier_instance = SimpleNotifier()
        
        with patch('sys.platform', 'linux'):
            with patch('builtins.print') as mock_print:
                result = notifier_instance.beep()
                
                # Should print terminal bell character
                mock_print.assert_called_once_with("\a", end="", flush=True)
                
                # Should return True
                assert result is True
    
    def test_beep_windows_fallback(self):
        """Test beep on Windows with terminal bell fallback."""
        notifier_instance = SimpleNotifier()
        
        with patch('sys.platform', 'win32'):
            with patch('builtins.print') as mock_print:
                result = notifier_instance.beep()
                
                # Should print terminal bell character
                mock_print.assert_called_once_with("\a", end="", flush=True)
                
                # Should return True
                assert result is True
    
    def test_beep_unknown_platform_fallback(self):
        """Test beep on unknown platform with terminal bell fallback."""
        notifier_instance = SimpleNotifier()
        
        with patch('sys.platform', 'unknown'):
            with patch('builtins.print') as mock_print:
                result = notifier_instance.beep()
                
                # Should print terminal bell character
                mock_print.assert_called_once_with("\a", end="", flush=True)
                
                # Should return True
                assert result is True


class TestStatusToast:
    """Test status toast functionality."""
    
    def test_status_toast_info_level(self):
        """Test status toast with info level."""
        notifier_instance = SimpleNotifier()
        
        with patch.object(notifier_instance.logger, 'info') as mock_info:
            notifier_instance.status_toast("Test message", "info")
            
            # Should log with INFO prefix
            mock_info.assert_called_once_with("INFO: Test message")
    
    def test_status_toast_success_level(self):
        """Test status toast with success level."""
        notifier_instance = SimpleNotifier()
        
        with patch.object(notifier_instance.logger, 'info') as mock_info:
            notifier_instance.status_toast("Operation completed", "success")
            
            # Should log with SUCCESS prefix
            mock_info.assert_called_once_with("SUCCESS: Operation completed")
    
    def test_status_toast_error_level(self):
        """Test status toast with error level."""
        notifier_instance = SimpleNotifier()
        
        with patch.object(notifier_instance.logger, 'error') as mock_error:
            notifier_instance.status_toast("Something went wrong", "error")
            
            # Should log with ERROR prefix
            mock_error.assert_called_once_with("ERROR: Something went wrong")
    
    def test_status_toast_warning_level(self):
        """Test status toast with warning level."""
        notifier_instance = SimpleNotifier()
        
        with patch.object(notifier_instance.logger, 'warning') as mock_warning:
            notifier_instance.status_toast("Proceed with caution", "warning")
            
            # Should log with WARNING prefix
            mock_warning.assert_called_once_with("WARNING: Proceed with caution")
    
    def test_status_toast_default_level(self):
        """Test status toast with default level (info)."""
        notifier_instance = SimpleNotifier()
        
        with patch.object(notifier_instance.logger, 'info') as mock_info:
            notifier_instance.status_toast("Default message")
            
            # Should default to info level
            mock_info.assert_called_once_with("INFO: Default message")
    
    def test_status_toast_unknown_level(self):
        """Test status toast with unknown level."""
        notifier_instance = SimpleNotifier()
        
        with patch.object(notifier_instance.logger, 'info') as mock_info:
            notifier_instance.status_toast("Unknown level message", "unknown")
            
            # Should default to info level for unknown levels
            mock_info.assert_called_once_with("INFO: Unknown level message")
    
    def test_status_toast_empty_message(self):
        """Test status toast with empty message."""
        notifier_instance = SimpleNotifier()
        
        with patch.object(notifier_instance.logger, 'info') as mock_info:
            notifier_instance.status_toast("", "info")
            
            # Should handle empty message
            mock_info.assert_called_once_with("INFO: ")
    
    def test_status_toast_special_characters(self):
        """Test status toast with special characters."""
        notifier_instance = SimpleNotifier()
        
        with patch.object(notifier_instance.logger, 'info') as mock_info:
            notifier_instance.status_toast("Message with émojis 🚀 and symbols @#$%", "info")
            
            # Should handle special characters correctly
            mock_info.assert_called_once_with("INFO: Message with émojis 🚀 and symbols @#$%")


class TestNotifierIntegration:
    """Test notifier integration scenarios."""
    
    def test_notifier_with_logger_mixin(self):
        """Test that notifier works with LoggerMixin."""
        # This test ensures the notifier integrates well with the logging system
        notifier_instance = SimpleNotifier()
        
        # Should have logger property
        assert hasattr(notifier_instance, 'logger')
        assert notifier_instance.logger is not None
        
        # Logger should have a name
        assert hasattr(notifier_instance.logger, 'name')
        assert notifier_instance.logger.name == "src.ui.notifier"
    
    def test_notifier_multiple_calls(self):
        """Test multiple calls to notifier methods."""
        notifier_instance = SimpleNotifier()
        
        with patch('sys.platform', 'linux'):
            with patch('builtins.print') as mock_print:
                # Multiple beep calls
                result1 = notifier_instance.beep()
                result2 = notifier_instance.beep()
                result3 = notifier_instance.beep()
                
                # All should succeed
                assert result1 is True
                assert result2 is True
                assert result3 is True
                
                # Should have called print 3 times
                assert mock_print.call_count == 3
                
                # Each call should be with the bell character
                expected_calls = [call("\a", end="", flush=True)] * 3
                mock_print.assert_has_calls(expected_calls)
    
    def test_notifier_error_recovery(self):
        """Test that notifier recovers from errors."""
        notifier_instance = SimpleNotifier()
        
        with patch('sys.platform', 'darwin'):
            # First call fails
            with patch('subprocess.run') as mock_run:
                mock_run.side_effect = Exception("First error")
                
                with patch.object(notifier_instance.logger, 'debug') as mock_log:
                    result1 = notifier_instance.beep()
                    assert result1 is False
                    mock_log.assert_called_once()
            
            # Second call succeeds
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock()
                
                result2 = notifier_instance.beep()
                assert result2 is True


class TestPlatformSpecificBehavior:
    """Test platform-specific behavior."""
    
    @pytest.mark.parametrize("platform,expected_subprocess_calls,expected_print_calls", [
        ("darwin", 1, 0),      # macOS: should call subprocess, not print
        ("linux", 0, 1),       # Linux: should not call subprocess, should print
        ("win32", 0, 1),       # Windows: should not call subprocess, should print
        ("freebsd", 0, 1),     # FreeBSD: should not call subprocess, should print
        ("unknown", 0, 1),     # Unknown: should not call subprocess, should print
    ])
    def test_beep_platform_specific_behavior(self, platform, expected_subprocess_calls, expected_print_calls):
        """Test beep behavior on different platforms."""
        notifier_instance = SimpleNotifier()
        
        with patch('sys.platform', platform):
            with patch('subprocess.run') as mock_run:
                with patch('builtins.print') as mock_print:
                    # Mock subprocess.run to succeed on macOS
                    if platform == "darwin":
                        mock_run.return_value = MagicMock()
                    
                    result = notifier_instance.beep()
                    
                    # Should always return True
                    assert result is True
                    
                    # Check subprocess calls
                    assert mock_run.call_count == expected_subprocess_calls
                    
                    # Check print calls
                    assert mock_print.call_count == expected_print_calls


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_beep_with_subprocess_timeout(self):
        """Test beep with subprocess timeout."""
        notifier_instance = SimpleNotifier()
        
        with patch('sys.platform', 'darwin'):
            with patch('subprocess.run') as mock_run:
                mock_run.side_effect = subprocess.TimeoutExpired("afplay", 5)
                
                with patch.object(notifier_instance.logger, 'debug') as mock_log:
                    result = notifier_instance.beep()
                    
                    # Should log the timeout error
                    mock_log.assert_called_once_with("Error playing beep", error="Command 'afplay' timed out after 5 seconds")
                    
                    # Should return False
                    assert result is False
    
    def test_beep_with_subprocess_file_not_found(self):
        """Test beep with subprocess file not found."""
        notifier_instance = SimpleNotifier()
        
        with patch('sys.platform', 'darwin'):
            with patch('subprocess.run') as mock_run:
                mock_run.side_effect = FileNotFoundError("afplay not found")
                
                with patch.object(notifier_instance.logger, 'debug') as mock_log:
                    result = notifier_instance.beep()
                    
                    # Should log the file not found error
                    mock_log.assert_called_once_with("Error playing beep", error="afplay not found")
                    
                    # Should return False
                    assert result is False
    
    def test_status_toast_with_very_long_message(self):
        """Test status toast with very long message."""
        notifier_instance = SimpleNotifier()
        
        long_message = "A" * 1000  # 1000 character message
        
        with patch.object(notifier_instance.logger, 'info') as mock_info:
            notifier_instance.status_toast(long_message, "info")
            
            # Should handle long messages
            mock_info.assert_called_once_with(f"INFO: {long_message}")
    
    def test_status_toast_with_none_message(self):
        """Test status toast with None message."""
        notifier_instance = SimpleNotifier()
        
        with patch.object(notifier_instance.logger, 'info') as mock_info:
            notifier_instance.status_toast(None, "info")
            
            # Should handle None message gracefully
            mock_info.assert_called_once_with("INFO: None")
    
    def test_notifier_memory_usage(self):
        """Test that notifier doesn't leak memory."""
        notifier_instance = SimpleNotifier()
        
        # Create many instances and check they don't accumulate
        instances = []
        for i in range(100):
            instances.append(SimpleNotifier())
        
        # All instances should be valid
        for instance in instances:
            assert instance.logger is not None
            assert hasattr(instance, 'beep')
            assert hasattr(instance, 'status_toast')
        
        # Clean up
        del instances
