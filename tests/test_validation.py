"""
Tests for the validation utilities.

This module tests the input validation and sanitization functions to ensure
data integrity and prevent invalid data from causing runtime errors.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, Mock
from src.utils.validation import (
    validate_file_path,
    validate_directory_path,
    validate_url,
    validate_api_key,
    validate_numeric_range,
    validate_string_length,
    validate_enum_value,
    sanitize_filename
)
from src.utils.error_handler import ConfigurationError


class TestValidateFilePath:
    """Test file path validation functionality."""
    
    def test_validate_file_path_valid(self, tmp_path):
        """Test validation of valid file path."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        result = validate_file_path(test_file)
        assert isinstance(result, Path)
        assert result == test_file.resolve()
    
    def test_validate_file_path_string(self, tmp_path):
        """Test validation of file path as string."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        result = validate_file_path(str(test_file))
        assert isinstance(result, Path)
        assert result == test_file.resolve()
    
    def test_validate_file_path_must_exist_true(self, tmp_path):
        """Test validation when file must exist and does exist."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        result = validate_file_path(test_file, must_exist=True)
        assert result == test_file.resolve()
    
    def test_validate_file_path_must_exist_false(self, tmp_path):
        """Test validation when file must exist but doesn't exist."""
        non_existent_file = tmp_path / "nonexistent.txt"
        
        with pytest.raises(ConfigurationError) as exc_info:
            validate_file_path(non_existent_file, must_exist=True)
        
        error = exc_info.value
        assert "File does not exist" in error.message
        assert error.details["file_path"] == str(non_existent_file.resolve())
        assert error.details["must_exist"] is True
    
    def test_validate_file_path_invalid_path(self):
        """Test validation of invalid file path."""
        invalid_path = "/invalid/path/with/invalid/chars/\0"
        
        with pytest.raises(ConfigurationError) as exc_info:
            validate_file_path(invalid_path)
        
        error = exc_info.value
        assert "Invalid file path" in error.message
        assert error.details["file_path"] == invalid_path


class TestValidateDirectoryPath:
    """Test directory path validation functionality."""
    
    def test_validate_directory_path_valid(self, tmp_path):
        """Test validation of valid directory path."""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        
        result = validate_directory_path(test_dir)
        assert isinstance(result, Path)
        assert result == test_dir.resolve()
    
    def test_validate_directory_path_string(self, tmp_path):
        """Test validation of directory path as string."""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        
        result = validate_directory_path(str(test_dir))
        assert isinstance(result, Path)
        assert result == test_dir.resolve()
    
    def test_validate_directory_path_create_if_missing(self, tmp_path):
        """Test validation with directory creation."""
        new_dir = tmp_path / "new_dir"
        
        result = validate_directory_path(new_dir, create_if_missing=True)
        assert result == new_dir.resolve()
        assert new_dir.exists()
        assert new_dir.is_dir()
    
    def test_validate_directory_path_not_exists_no_create(self, tmp_path):
        """Test validation when directory doesn't exist and creation not allowed."""
        non_existent_dir = tmp_path / "nonexistent_dir"
        
        with pytest.raises(ConfigurationError) as exc_info:
            validate_directory_path(non_existent_dir, create_if_missing=False)
        
        error = exc_info.value
        assert "Directory does not exist" in error.message
        assert error.details["dir_path"] == str(non_existent_dir.resolve())
        assert error.details["create_if_missing"] is False
    
    def test_validate_directory_path_not_directory(self, tmp_path):
        """Test validation when path exists but is not a directory."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        with pytest.raises(ConfigurationError) as exc_info:
            validate_directory_path(test_file)
        
        error = exc_info.value
        assert "Path is not a directory" in error.message
        assert error.details["dir_path"] == str(test_file.resolve())


class TestValidateURL:
    """Test URL validation functionality."""
    
    def test_validate_url_valid_http(self):
        """Test validation of valid HTTP URL."""
        valid_urls = [
            "http://example.com",
            "http://www.example.com",
            "http://example.com/path",
            "http://example.com:8080/path",
            "http://localhost:3000",
            "http://192.168.1.1:8080"
        ]
        
        for url in valid_urls:
            result = validate_url(url)
            assert result == url
    
    def test_validate_url_valid_https(self):
        """Test validation of valid HTTPS URL."""
        valid_urls = [
            "https://example.com",
            "https://www.example.com",
            "https://example.com/path",
            "https://example.com:8443/path"
        ]
        
        for url in valid_urls:
            result = validate_url(url)
            assert result == url
    
    def test_validate_url_invalid_format(self):
        """Test validation of invalid URL format."""
        invalid_urls = [
            "not_a_url",
            "ftp://example.com",  # Wrong scheme
            "http://",  # Missing host
            "http://example",  # Invalid TLD
            "http://example.com:99999",  # Invalid port
        ]
        
        for url in invalid_urls:
            with pytest.raises(ConfigurationError) as exc_info:
                validate_url(url)
            
            error = exc_info.value
            assert "Invalid URL format" in error.message
            assert error.details["url"] == url
    
    def test_validate_url_custom_schemes(self):
        """Test validation with custom allowed schemes."""
        # Test with only HTTP allowed
        result = validate_url("http://example.com", allowed_schemes=["http"])
        assert result == "http://example.com"
        
        # Test with only HTTPS allowed
        result = validate_url("https://example.com", allowed_schemes=["https"])
        assert result == "https://example.com"
        
        # Test with custom scheme not allowed
        with pytest.raises(ConfigurationError) as exc_info:
            validate_url("https://example.com", allowed_schemes=["http"])
        
        error = exc_info.value
        assert "not allowed" in error.message
        assert error.details["scheme"] == "https"
        assert error.details["allowed_schemes"] == ["http"]


class TestValidateAPIKey:
    """Test API key validation functionality."""
    
    def test_validate_api_key_valid(self):
        """Test validation of valid API keys."""
        valid_keys = [
            "abcdefghijklmnop",  # 16 chars
            "very_long_api_key_with_many_characters_12345",  # 45 chars
            "  api_key_with_spaces  ",  # With spaces
        ]
        
        for key in valid_keys:
            result = validate_api_key(key)
            assert result == key.strip()
    
    def test_validate_api_key_too_short(self):
        """Test validation of API key that's too short."""
        short_key = "short"
        
        with pytest.raises(ConfigurationError) as exc_info:
            validate_api_key(short_key, min_length=10)
        
        error = exc_info.value
        assert "too short" in error.message
        assert error.details["api_key_length"] == 5
        assert error.details["min_length"] == 10
    
    def test_validate_api_key_empty(self):
        """Test validation of empty API key."""
        empty_keys = ["", "   ", None]
        
        for key in empty_keys:
            with pytest.raises(ConfigurationError) as exc_info:
                validate_api_key(key)
            
            error = exc_info.value
            assert "non-empty string" in error.message
    
    def test_validate_api_key_placeholder_values(self):
        """Test validation of placeholder API key values."""
        placeholder_keys = ["none", "null", "undefined", "NONE", "NULL"]
        
        for key in placeholder_keys:
            with pytest.raises(ConfigurationError) as exc_info:
                validate_api_key(key)
            
            error = exc_info.value
            assert "placeholder value" in error.message
    
    def test_validate_api_key_custom_min_length(self):
        """Test validation with custom minimum length."""
        # Test with 5 character minimum
        result = validate_api_key("12345", min_length=5)
        assert result == "12345"
        
        # Test with 5 character minimum but key too short
        with pytest.raises(ConfigurationError) as exc_info:
            validate_api_key("1234", min_length=5)
        
        error = exc_info.value
        assert error.details["min_length"] == 5


class TestValidateNumericRange:
    """Test numeric range validation functionality."""
    
    def test_validate_numeric_range_no_bounds(self):
        """Test validation with no bounds specified."""
        values = [-100, 0, 100, 3.14, -2.5]
        
        for value in values:
            result = validate_numeric_range(value)
            assert result == value
    
    def test_validate_numeric_range_min_only(self):
        """Test validation with only minimum bound."""
        values = [5, 10, 15, 20]
        
        for value in values:
            result = validate_numeric_range(value, min_value=5)
            assert result == value
        
        # Test value below minimum
        with pytest.raises(ConfigurationError) as exc_info:
            validate_numeric_range(3, min_value=5)
        
        error = exc_info.value
        assert "below minimum 5" in error.message
        assert error.details["value"] == 3
        assert error.details["min_value"] == 5
    
    def test_validate_numeric_range_max_only(self):
        """Test validation with only maximum bound."""
        values = [1, 5, 10, 15]
        
        for value in values:
            result = validate_numeric_range(value, max_value=15)
            assert result == value
        
        # Test value above maximum
        with pytest.raises(ConfigurationError) as exc_info:
            validate_numeric_range(20, max_value=15)
        
        error = exc_info.value
        assert "above maximum 15" in error.message
        assert error.details["value"] == 20
        assert error.details["max_value"] == 15
    
    def test_validate_numeric_range_both_bounds(self):
        """Test validation with both minimum and maximum bounds."""
        values = [5, 10, 15]
        
        for value in values:
            result = validate_numeric_range(value, min_value=5, max_value=15)
            assert result == value
        
        # Test value below minimum
        with pytest.raises(ConfigurationError) as exc_info:
            validate_numeric_range(3, min_value=5, max_value=15)
        
        error = exc_info.value
        assert "below minimum 5" in error.message
        
        # Test value above maximum
        with pytest.raises(ConfigurationError) as exc_info:
            validate_numeric_range(20, min_value=5, max_value=15)
        
        error = exc_info.value
        assert "above maximum 15" in error.message
    
    def test_validate_numeric_range_custom_field_name(self):
        """Test validation with custom field name."""
        with pytest.raises(ConfigurationError) as exc_info:
            validate_numeric_range(3, min_value=5, field_name="age")
        
        error = exc_info.value
        assert "age 3 is below minimum 5" in error.message
        assert error.details["field_name"] == "age"


class TestValidateStringLength:
    """Test string length validation functionality."""
    
    def test_validate_string_length_no_bounds(self):
        """Test validation with no length bounds specified."""
        strings = ["", "a", "hello", "very long string with many characters"]
        
        for string in strings:
            result = validate_string_length(string)
            assert result == string
    
    def test_validate_string_length_min_only(self):
        """Test validation with only minimum length."""
        strings = ["hello", "world", "testing"]
        
        for string in strings:
            result = validate_string_length(string, min_length=3)
            assert result == string
        
        # Test string below minimum length
        with pytest.raises(ConfigurationError) as exc_info:
            validate_string_length("hi", min_length=3)
        
        error = exc_info.value
        assert "below minimum 3" in error.message
        assert error.details["length"] == 2
        assert error.details["min_length"] == 3
    
    def test_validate_string_length_max_only(self):
        """Test validation with only maximum length."""
        strings = ["a", "hi", "hello"]
        
        for string in strings:
            result = validate_string_length(string, max_length=5)
            assert result == string
        
        # Test string above maximum length
        with pytest.raises(ConfigurationError) as exc_info:
            validate_string_length("very long", max_length=5)
        
        error = exc_info.value
        assert "above maximum 5" in error.message
        assert error.details["length"] == 9
        assert error.details["max_length"] == 5
    
    def test_validate_string_length_both_bounds(self):
        """Test validation with both minimum and maximum length bounds."""
        strings = ["hi", "hello", "world"]
        
        for string in strings:
            result = validate_string_length(string, min_length=2, max_length=5)
            assert result == string
        
        # Test string below minimum length
        with pytest.raises(ConfigurationError) as exc_info:
            validate_string_length("a", min_length=2, max_length=5)
        
        error = exc_info.value
        assert "below minimum 2" in error.message
        
        # Test string above maximum length
        with pytest.raises(ConfigurationError) as exc_info:
            validate_string_length("very long string", min_length=2, max_length=5)
        
        error = exc_info.value
        assert "above maximum 5" in error.message
    
    def test_validate_string_length_not_string(self):
        """Test validation with non-string input."""
        non_strings = [123, 3.14, True, None, [1, 2, 3]]
        
        for value in non_strings:
            with pytest.raises(ConfigurationError) as exc_info:
                validate_string_length(value)
            
            error = exc_info.value
            assert "must be a string" in error.message
            assert error.details["value_type"] == type(value).__name__


class TestValidateEnumValue:
    """Test enum value validation functionality."""
    
    def test_validate_enum_value_valid(self):
        """Test validation of valid enum values."""
        allowed_values = ["red", "green", "blue"]
        
        for value in allowed_values:
            result = validate_enum_value(value, allowed_values)
            assert result == value
    
    def test_validate_enum_value_invalid(self):
        """Test validation of invalid enum values."""
        allowed_values = ["red", "green", "blue"]
        invalid_value = "yellow"
        
        with pytest.raises(ConfigurationError) as exc_info:
            validate_enum_value(invalid_value, allowed_values)
        
        error = exc_info.value
        assert f"'{invalid_value}' is not allowed" in error.message
        assert error.details["value"] == invalid_value
        assert error.details["allowed_values"] == allowed_values
    
    def test_validate_enum_value_custom_field_name(self):
        """Test validation with custom field name."""
        allowed_values = ["small", "medium", "large"]
        invalid_value = "extra_large"
        
        with pytest.raises(ConfigurationError) as exc_info:
            validate_enum_value(invalid_value, allowed_values, field_name="size")
        
        error = exc_info.value
        assert "size 'extra_large' is not allowed" in error.message
        assert error.details["field_name"] == "size"


class TestSanitizeFilename:
    """Test filename sanitization functionality."""
    
    def test_sanitize_filename_valid(self):
        """Test sanitization of already valid filenames."""
        valid_names = [
            "normal_file.txt",
            "file_with_underscores.txt",
            "FileWithCaps.txt",
            "123_numbers.txt"
        ]
        
        for name in valid_names:
            result = sanitize_filename(name)
            assert result == name
    
    def test_sanitize_filename_invalid_chars(self):
        """Test sanitization of filenames with invalid characters."""
        test_cases = [
            ("file<name>.txt", "filename.txt"),
            ("file:name.txt", "filename.txt"),
            ("file/name.txt", "filename.txt"),
            ("file\\name.txt", "filename.txt"),
            ("file|name.txt", "filename.txt"),
            ("file?name.txt", "filename.txt"),
            ("file*name.txt", "filename.txt"),
            ("file\"name.txt", "filename.txt")
        ]
        
        for input_name, expected in test_cases:
            result = sanitize_filename(input_name)
            assert result == expected
    
    def test_sanitize_filename_multiple_spaces_underscores(self):
        """Test sanitization of multiple spaces and underscores."""
        test_cases = [
            ("file   name.txt", "file_name.txt"),
            ("file___name.txt", "file_name.txt"),
            ("file _ name.txt", "file_name.txt"),
            ("  file  name  .txt  ", "file_name.txt")
        ]
        
        for input_name, expected in test_cases:
            result = sanitize_filename(input_name)
            assert result == expected
    
    def test_sanitize_filename_leading_trailing_dots(self):
        """Test sanitization of leading and trailing dots."""
        test_cases = [
            (".hidden_file.txt", "hidden_file.txt"),
            ("file.txt.", "file.txt"),
            ("..file..txt..", "file.txt"),
            ("...", "unnamed_file")
        ]
        
        for input_name, expected in test_cases:
            result = sanitize_filename(input_name)
            assert result == expected
    
    def test_sanitize_filename_length_limit(self):
        """Test sanitization with length limits."""
        # Test with default max length (255)
        long_name = "a" * 300
        result = sanitize_filename(long_name)
        assert len(result) <= 255
        
        # Test with custom max length
        result = sanitize_filename("very_long_filename.txt", max_length=20)
        assert len(result) <= 20
        
        # Test with extension
        long_name_with_ext = "a" * 300 + ".txt"
        result = sanitize_filename(long_name_with_ext, max_length=20)
        assert len(result) <= 20
        assert result.endswith(".txt")
    
    def test_sanitize_filename_empty_result(self):
        """Test sanitization that results in empty filename."""
        empty_results = [
            "",
            "   ",
            "...",
            "///",
            "|||"
        ]
        
        for input_name in empty_results:
            result = sanitize_filename(input_name)
            assert result == "unnamed_file"
