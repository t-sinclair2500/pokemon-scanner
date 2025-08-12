"""Unit tests for configuration management."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import os

from src.utils.config import (
    Settings, 
    ensure_cache_and_output_dirs, 
    resolve_tesseract_path,
    ensure_cache_dir,
    ensure_tesseract
)


class TestSettings:
    """Test Settings class configuration."""
    
    def test_settings_default_values(self):
        """Test that Settings has correct default values."""
        settings = Settings()
        
        assert settings.LOG_LEVEL == "INFO"
        assert settings.CACHE_DB_PATH == "cache/cards.db"
        assert settings.CACHE_EXPIRE_HOURS == 24
        assert settings.CAMERA_INDEX == 0
        assert settings.OCR_CONFIDENCE_THRESHOLD == 60
        assert settings.POKEMON_TCG_API_KEY is None
        assert settings.TESSERACT_PATH is None
    
    def test_settings_from_environment(self):
        """Test that Settings can be configured from environment variables."""
        with patch.dict(os.environ, {
            "LOG_LEVEL": "DEBUG",
            "CACHE_DB_PATH": "custom/cache.db",
            "CACHE_EXPIRE_HOURS": "48",
            "CAMERA_INDEX": "1",
            "OCR_CONFIDENCE_THRESHOLD": "80",
            "POKEMON_TCG_API_KEY": "test_key_123"
        }):
            settings = Settings()
            
            assert settings.LOG_LEVEL == "DEBUG"
            assert settings.CACHE_DB_PATH == "custom/cache.db"
            assert settings.CACHE_EXPIRE_HOURS == 48
            assert settings.CAMERA_INDEX == 1
            assert settings.OCR_CONFIDENCE_THRESHOLD == 80
            assert settings.POKEMON_TCG_API_KEY == "test_key_123"
    
    def test_settings_case_insensitive(self):
        """Test that Settings is case insensitive."""
        with patch.dict(os.environ, {
            "log_level": "WARNING",
            "cache_db_path": "test/path.db"
        }):
            settings = Settings()
            
            assert settings.LOG_LEVEL == "WARNING"
            assert settings.CACHE_DB_PATH == "test/path.db"
    
    def test_settings_validation(self):
        """Test that Settings validates input types."""
        with patch.dict(os.environ, {
            "CACHE_EXPIRE_HOURS": "invalid",
            "CAMERA_INDEX": "not_a_number"
        }):
            with pytest.raises(ValueError):
                Settings()


class TestDirectoryFunctions:
    """Test directory creation functions."""
    
    def test_ensure_cache_and_output_dirs_creates_directories(self, tmp_path):
        """Test that directories are created when they don't exist."""
        with patch('src.utils.config.settings') as mock_settings:
            mock_settings.CACHE_DB_PATH = str(tmp_path / "cache" / "cards.db")
            
            ensure_cache_and_output_dirs()
            
            # Check cache directory was created
            cache_dir = tmp_path / "cache"
            assert cache_dir.exists()
            assert cache_dir.is_dir()
            
            # Check output directory was created
            output_dir = Path("output")
            assert output_dir.exists()
            assert output_dir.is_dir()
    
    def test_ensure_cache_and_output_dirs_existing_directories(self, tmp_path):
        """Test that function works when directories already exist."""
        # Create directories first
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir(parents=True)
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        with patch('src.utils.config.settings') as mock_settings:
            mock_settings.CACHE_DB_PATH = str(cache_dir / "cards.db")
            
            # Should not raise any errors
            ensure_cache_and_output_dirs()
            
            assert cache_dir.exists()
            assert output_dir.exists()
    
    def test_ensure_cache_dir_backward_compatibility(self, tmp_path):
        """Test that ensure_cache_dir is backward compatible."""
        with patch('src.utils.config.settings') as mock_settings:
            mock_settings.CACHE_DB_PATH = str(tmp_path / "cache" / "cards.db")
            
            ensure_cache_dir()
            
            cache_dir = tmp_path / "cache"
            assert cache_dir.exists()
            assert cache_dir.is_dir()


class TestTesseractPathResolution:
    """Test Tesseract path resolution functions."""
    
    def test_resolve_tesseract_path_custom_path_exists(self, tmp_path):
        """Test that custom Tesseract path is used when it exists."""
        # Create a mock tesseract binary
        tesseract_path = tmp_path / "custom_tesseract"
        tesseract_path.touch()
        
        with patch('src.utils.config.settings') as mock_settings:
            mock_settings.TESSERACT_PATH = str(tesseract_path)
            
            result = resolve_tesseract_path()
            assert result == str(tesseract_path)
    
    def test_resolve_tesseract_path_custom_path_not_exists(self, tmp_path):
        """Test fallback when custom Tesseract path doesn't exist."""
        with patch('src.utils.config.settings') as mock_settings:
            mock_settings.TESSERACT_PATH = str(tmp_path / "nonexistent_tesseract")
            
            # Mock shutil.which to return a valid path
            with patch('shutil.which') as mock_which:
                mock_which.return_value = "/usr/bin/tesseract"
                
                result = resolve_tesseract_path()
                assert result == "/usr/bin/tesseract"
    
    def test_resolve_tesseract_path_found_in_path(self):
        """Test that Tesseract is found in system PATH."""
        with patch('src.utils.config.settings') as mock_settings:
            mock_settings.TESSERACT_PATH = None
            
            with patch('shutil.which') as mock_which:
                mock_which.return_value = "/usr/local/bin/tesseract"
                
                result = resolve_tesseract_path()
                assert result == "/usr/local/bin/tesseract"
    
    def test_resolve_tesseract_path_common_paths_fallback(self):
        """Test fallback to common Tesseract installation paths."""
        with patch('src.utils.config.settings') as mock_settings:
            mock_settings.TESSERACT_PATH = None
            
            with patch('shutil.which') as mock_which:
                mock_which.return_value = None
                
                # Mock Path.exists for common paths
                with patch('pathlib.Path.exists') as mock_exists:
                    # First two paths don't exist, third one does
                    mock_exists.side_effect = [False, False, True]
                    
                    result = resolve_tesseract_path()
                    assert result == "/usr/bin/tesseract"
    
    def test_resolve_tesseract_path_not_found(self):
        """Test that FileNotFoundError is raised when Tesseract is not found."""
        with patch('src.utils.config.settings') as mock_settings:
            mock_settings.TESSERACT_PATH = None
            
            with patch('shutil.which') as mock_which:
                mock_which.return_value = None
                
                with patch('pathlib.Path.exists') as mock_exists:
                    mock_exists.return_value = False
                    
                    with pytest.raises(FileNotFoundError) as exc_info:
                        resolve_tesseract_path()
                    
                    assert "Tesseract not found" in str(exc_info.value)
                    assert "brew install tesseract" in str(exc_info.value)
    
    def test_ensure_tesseract_backward_compatibility(self):
        """Test that ensure_tesseract is backward compatible."""
        with patch('src.utils.config.resolve_tesseract_path') as mock_resolve:
            mock_resolve.return_value = "/test/path/tesseract"
            
            result = ensure_tesseract()
            assert result == "/test/path/tesseract"
            mock_resolve.assert_called_once()


class TestConfigurationIntegration:
    """Test configuration integration scenarios."""
    
    def test_configuration_with_env_file(self, tmp_path):
        """Test configuration loading from .env file."""
        # Create a .env file in the current working directory for this test
        env_file = Path(".env")
        original_content = env_file.read_text() if env_file.exists() else None
        
        try:
            env_file.write_text("""
LOG_LEVEL=DEBUG
CACHE_DB_PATH=custom/cache.db
CACHE_EXPIRE_HOURS=72
CAMERA_INDEX=2
OCR_CONFIDENCE_THRESHOLD=90
POKEMON_TCG_API_KEY=env_file_key
TESSERACT_PATH=/custom/tesseract
            """.strip())
            
            # Import and reload the config module to pick up the new .env file
            import importlib
            import src.utils.config
            importlib.reload(src.utils.config)
            
            # Get the updated settings
            from src.utils.config import settings
            
            assert settings.LOG_LEVEL == "DEBUG"
            assert settings.CACHE_DB_PATH == "custom/cache.db"
            assert settings.CACHE_EXPIRE_HOURS == 72
            assert settings.CAMERA_INDEX == 2
            assert settings.OCR_CONFIDENCE_THRESHOLD == 90
            assert settings.POKEMON_TCG_API_KEY == "env_file_key"
            assert settings.TESSERACT_PATH == "/custom/tesseract"
            
        finally:
            # Restore original .env file or remove test file
            if original_content is not None:
                env_file.write_text(original_content)
            elif env_file.exists():
                env_file.unlink()
            
            # Reload the config module to restore original settings
            import importlib
            import src.utils.config
            importlib.reload(src.utils.config)
    
    def test_configuration_priority_order(self):
        """Test that environment variables take priority over .env file."""
        with patch.dict(os.environ, {
            "LOG_LEVEL": "ERROR",
            "CACHE_DB_PATH": "env_priority.db"
        }):
            settings = Settings()
            
            # Environment variables should override .env file values
            assert settings.LOG_LEVEL == "ERROR"
            assert settings.CACHE_DB_PATH == "env_priority.db"
    
    def test_configuration_validation_errors(self):
        """Test configuration validation error handling."""
        with patch.dict(os.environ, {
            "CACHE_EXPIRE_HOURS": "-1",  # Invalid negative value
            "CAMERA_INDEX": "abc",        # Invalid non-numeric value
            "OCR_CONFIDENCE_THRESHOLD": "101"  # Invalid out-of-range value
        }):
            with pytest.raises(ValueError):
                Settings()


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_environment_variables(self):
        """Test handling of empty environment variables."""
        with patch.dict(os.environ, {
            "LOG_LEVEL": "",
            "CACHE_DB_PATH": "",
            "POKEMON_TCG_API_KEY": ""
        }):
            settings = Settings()
            
            # Empty strings should be treated as None for optional fields
            assert settings.POKEMON_TCG_API_KEY is None
            # Required fields should use defaults
            assert settings.LOG_LEVEL == "INFO"
            assert settings.CACHE_DB_PATH == "cache/cards.db"
    
    def test_whitespace_environment_variables(self):
        """Test handling of whitespace-only environment variables."""
        with patch.dict(os.environ, {
            "LOG_LEVEL": "   ",
            "CACHE_DB_PATH": "  \t  ",
            "POKEMON_TCG_API_KEY": "  "
        }):
            settings = Settings()
            
            # Whitespace-only strings should be treated as None for optional fields
            assert settings.POKEMON_TCG_API_KEY is None
            # Required fields should use defaults
            assert settings.LOG_LEVEL == "INFO"
            assert settings.CACHE_DB_PATH == "cache/cards.db"
    
    def test_directory_creation_permissions(self, tmp_path):
        """Test directory creation with permission issues."""
        # Create a read-only directory
        read_only_dir = tmp_path / "readonly"
        read_only_dir.mkdir()
        read_only_dir.chmod(0o444)  # Read-only
        
        with patch('src.utils.config.settings') as mock_settings:
            mock_settings.CACHE_DB_PATH = str(read_only_dir / "cache" / "cards.db")
            
            # Should handle permission errors gracefully
            with pytest.raises(PermissionError):
                ensure_cache_and_output_dirs()
    
    def test_tesseract_path_with_symlinks(self, tmp_path):
        """Test Tesseract path resolution with symbolic links."""
        # Create a mock tesseract binary
        real_tesseract = tmp_path / "real_tesseract"
        real_tesseract.touch()
        
        # Create a symlink to it
        symlink_tesseract = tmp_path / "symlink_tesseract"
        symlink_tesseract.symlink_to(real_tesseract)
        
        with patch('src.utils.config.settings') as mock_settings:
            mock_settings.TESSERACT_PATH = str(symlink_tesseract)
            
            result = resolve_tesseract_path()
            assert result == str(symlink_tesseract)
