"""Unit tests for store logging functionality."""

import pytest
import csv
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime
import numpy as np
import cv2

from src.store.logger import CardDataLogger, card_data_logger
from src.ocr.extract import CardInfo, OCRResult


class TestCardDataLogger:
    """Test CardDataLogger class."""
    
    def test_logger_initialization(self, tmp_path):
        """Test that CardDataLogger initializes correctly."""
        with patch('src.store.logger.Path') as mock_path:
            mock_path.return_value = tmp_path
            
            logger = CardDataLogger()
            
            # Should have required attributes
            assert hasattr(logger, 'output_dir')
            assert hasattr(logger, 'images_dir')
            assert hasattr(logger, 'logs_dir')
            assert hasattr(logger, 'csv_file')
            assert hasattr(logger, 'csv_columns')
            
            # Should have logger from LoggerMixin
            assert hasattr(logger, 'logger')
    
    def test_logger_creates_directories(self, tmp_path):
        """Test that CardDataLogger creates necessary directories."""
        # Mock the Path to return our tmp_path for the output directory
        with patch('src.store.logger.Path') as mock_path:
            # Mock Path("output") to return tmp_path
            def mock_path_side_effect(path_str):
                if path_str == "output":
                    return tmp_path
                return Path(path_str)
            
            mock_path.side_effect = mock_path_side_effect
            
            logger = CardDataLogger()
            
            # Should create output directory
            assert (tmp_path).exists()
            assert (tmp_path / "images").exists()
            assert (tmp_path / "logs").exists()
    
    def test_logger_csv_columns(self):
        """Test that CSV columns are correctly defined."""
        logger = CardDataLogger()
        
        expected_columns = [
            "timestamp_iso",
            "scan_id",
            "image_filename",
            "card_name",
            "collector_number", 
            "ocr_confidence",
            "processing_time_ms",
            "status",
            "notes"
        ]
        
        assert logger.csv_columns == expected_columns
    
    def test_logger_csv_file_naming(self):
        """Test that CSV file is named with current date."""
        logger = CardDataLogger()
        
        expected_filename = f"card_scans_{datetime.now().strftime('%Y%m%d')}.csv"
        assert logger.csv_file.name == expected_filename


class TestCSVInitialization:
    """Test CSV file initialization."""
    
    def test_init_csv_creates_file_if_not_exists(self, tmp_path):
        """Test that _init_csv creates CSV file with headers if it doesn't exist."""
        with patch('src.store.logger.Path') as mock_path:
            mock_path.return_value = tmp_path
            
            logger = CardDataLogger()
            
            # Mock the CSV file path
            csv_file = tmp_path / "test.csv"
            logger.csv_file = csv_file
            
            # Call _init_csv
            logger._init_csv()
            
            # Should create the file
            assert csv_file.exists()
            
            # Should contain headers
            with open(csv_file, 'r', encoding='utf-8') as f:
                content = f.read()
                assert "timestamp_iso" in content
                assert "scan_id" in content
                assert "card_name" in content
    
    def test_init_csv_doesnt_overwrite_existing(self, tmp_path):
        """Test that _init_csv doesn't overwrite existing CSV file."""
        with patch('src.store.logger.Path') as mock_path:
            mock_path.return_value = tmp_path
            
            logger = CardDataLogger()
            
            # Create a CSV file with custom content
            csv_file = tmp_path / "test.csv"
            logger.csv_file = csv_file
            
            custom_content = "custom,content,here\n"
            with open(csv_file, 'w', encoding='utf-8') as f:
                f.write(custom_content)
            
            # Call _init_csv
            logger._init_csv()
            
            # Should not overwrite existing content
            with open(csv_file, 'r', encoding='utf-8') as f:
                content = f.read()
                assert content == custom_content


class TestCardScanLogging:
    """Test card scan logging functionality."""
    
    def test_log_card_scan_success(self, tmp_path):
        """Test successful card scan logging."""
        with patch('src.store.logger.Path') as mock_path:
            mock_path.return_value = tmp_path
            
            logger = CardDataLogger()
            
            # Create mock card image (numpy array)
            card_image = np.zeros((100, 100, 3), dtype=np.uint8)
            
            # Create mock card info
            card_info = CardInfo(
                name="Charizard",
                collector_number="4/102",
                confidence=85.5
            )
            
            # Mock cv2.imwrite
            with patch('cv2.imwrite') as mock_imwrite:
                mock_imwrite.return_value = True
                
                # Mock file operations
                with patch('builtins.open', mock_open()) as mock_file:
                    result = logger.log_card_scan(
                        card_image=card_image,
                        card_info=card_info,
                        processing_time_ms=150
                    )
                    
                    # Should return success
                    assert result["status"] == "success"
                    assert "scan_id" in result
                    assert "image_filename" in result
                    assert "csv_row" in result
    
    def test_log_card_scan_generates_scan_id(self, tmp_path):
        """Test that scan ID is generated if not provided."""
        with patch('src.store.logger.Path') as mock_path:
            mock_path.return_value = tmp_path
            
            logger = CardDataLogger()
            
            # Create mock data
            card_image = np.zeros((100, 100, 3), dtype=np.uint8)
            card_info = CardInfo(name="Pikachu", confidence=90.0)
            
            with patch('cv2.imwrite') as mock_imwrite:
                mock_imwrite.return_value = True
                
                with patch('builtins.open', mock_open()):
                    result = logger.log_card_scan(
                        card_image=card_image,
                        card_info=card_info,
                        processing_time_ms=100
                    )
                    
                    # Should have generated scan ID
                    assert result["status"] == "success"
                    assert result["scan_id"].startswith("scan_")
    
    def test_log_card_scan_uses_provided_scan_id(self, tmp_path):
        """Test that provided scan ID is used."""
        with patch('src.store.logger.Path') as mock_path:
            mock_path.return_value = tmp_path
            
            logger = CardDataLogger()
            
            # Create mock data
            card_image = np.zeros((100, 100, 3), dtype=np.uint8)
            card_info = CardInfo(name="Blastoise", confidence=88.0)
            
            custom_scan_id = "custom_scan_123"
            
            with patch('cv2.imwrite') as mock_imwrite:
                mock_imwrite.return_value = True
                
                with patch('builtins.open', mock_open()):
                    result = logger.log_card_scan(
                        card_image=card_image,
                        card_info=card_info,
                        processing_time_ms=120,
                        scan_id=custom_scan_id
                    )
                    
                    # Should use provided scan ID
                    assert result["scan_id"] == custom_scan_id
    
    def test_log_card_scan_handles_invalid_image(self, tmp_path):
        """Test that invalid image format is handled gracefully."""
        with patch('src.store.logger.Path') as mock_path:
            mock_path.return_value = tmp_path
            
            logger = CardDataLogger()
            
            # Create invalid image (not numpy array)
            invalid_image = "not_an_image"
            
            # Create mock card info
            card_info = CardInfo(name="Venusaur", confidence=75.0)
            
            with patch('builtins.open', mock_open()):
                with patch.object(logger.logger, 'warning') as mock_warning:
                    result = logger.log_card_scan(
                        card_image=invalid_image,
                        card_info=card_info,
                        processing_time_ms=200
                    )
                    
                    # Should log warning about invalid image
                    mock_warning.assert_called_once_with("Invalid image format, skipping image save")
                    
                    # Should still succeed
                    assert result["status"] == "success"
                    assert result["image_filename"] == "no_image"
    
    def test_log_card_scan_handles_exception(self, tmp_path):
        """Test that exceptions during logging are handled gracefully."""
        with patch('src.store.logger.Path') as mock_path:
            mock_path.return_value = tmp_path
            
            logger = CardDataLogger()
            
            # Create mock data
            card_image = np.zeros((100, 100, 3), dtype=np.uint8)
            card_info = CardInfo(name="Raichu", confidence=82.0)
            
            # Mock cv2.imwrite to raise exception
            with patch('cv2.imwrite') as mock_imwrite:
                mock_imwrite.side_effect = Exception("Image save failed")
                
                with patch.object(logger.logger, 'error') as mock_error:
                    result = logger.log_card_scan(
                        card_image=card_image,
                        card_info=card_info,
                        processing_time_ms=180
                    )
                    
                    # Should log error
                    mock_error.assert_called_once_with("Failed to log card scan", error="Image save failed")
                    
                    # Should return error status
                    assert result["status"] == "error"
                    assert "error" in result


class TestNotesGeneration:
    """Test notes generation functionality."""
    
    def test_generate_notes_no_name_no_number(self):
        """Test notes generation when name and collector number are missing."""
        logger = CardDataLogger()
        
        card_info = CardInfo(name=None, collector_number=None, confidence=45.0)
        
        notes = logger._generate_notes(card_info)
        
        # Should include notes about missing data
        assert "No name extracted" in notes
        assert "No collector number found" in notes
        assert "Low confidence scan" in notes
    
    def test_generate_notes_high_confidence(self):
        """Test notes generation for high confidence scan."""
        logger = CardDataLogger()
        
        card_info = CardInfo(name="Mewtwo", collector_number="150/150", confidence=95.0)
        
        notes = logger._generate_notes(card_info)
        
        # Should indicate high confidence
        assert "High confidence scan" in notes
        assert "No name extracted" not in notes
        assert "No collector number found" not in notes
    
    def test_generate_notes_medium_confidence(self):
        """Test notes generation for medium confidence scan."""
        logger = CardDataLogger()
        
        card_info = CardInfo(name="Gyarados", collector_number="130/150", confidence=65.0)
        
        notes = logger._generate_notes(card_info)
        
        # Should indicate medium confidence
        assert "Medium confidence scan" in notes
    
    def test_generate_notes_with_ocr_result(self):
        """Test notes generation with OCR result data."""
        logger = CardDataLogger()
        
        # Create mock OCR result
        ocr_result = OCRResult(
            raw_text="Test text",
            preprocessing_steps={
                "name": {"method": "denoise"},
                "number": {"method": "threshold"}
            }
        )
        
        card_info = CardInfo(
            name="Dragonite",
            collector_number="149/150",
            confidence=78.0,
            ocr_result=ocr_result
        )
        
        notes = logger._generate_notes(card_info)
        
        # Should include preprocessing method notes
        assert "name: denoise" in notes
        assert "number: threshold" in notes
        assert "Medium confidence scan" in notes
    
    def test_generate_notes_normal_scan(self):
        """Test notes generation for normal scan."""
        logger = CardDataLogger()
        
        card_info = CardInfo(name="Snorlax", collector_number="143/150", confidence=88.0)
        
        notes = logger._generate_notes(card_info)
        
        # Should indicate high confidence scan (88.0 >= 80)
        assert notes == "High confidence scan"


class TestDetailedLogSaving:
    """Test detailed log saving functionality."""
    
    def test_save_detailed_log_success(self, tmp_path):
        """Test successful detailed log saving."""
        with patch('src.store.logger.Path') as mock_path:
            mock_path.return_value = tmp_path
            
            logger = CardDataLogger()
            
            # Create mock data
            scan_id = "test_scan_123"
            card_info = CardInfo(
                name="Arcanine",
                collector_number="59/150",
                confidence=92.0
            )
            csv_row = {
                "timestamp_iso": "2023-01-01T12:00:00",
                "scan_id": scan_id,
                "image_filename": "test.jpg"
            }
            
            # Mock file operations
            with patch('builtins.open', mock_open()) as mock_file:
                logger._save_detailed_log(scan_id, card_info, csv_row)
                
                # Should attempt to write log file
                mock_file.assert_called()
    
    def test_save_detailed_log_with_ocr_result(self, tmp_path):
        """Test detailed log saving with OCR result."""
        with patch('src.store.logger.Path') as mock_path:
            mock_path.return_value = tmp_path
            
            logger = CardDataLogger()
            
            # Create mock OCR result
            ocr_result = OCRResult(
                raw_text="Arcanine 59/150",
                preprocessing_steps={
                    "name": {"method": "denoise", "params": {"strength": 0.5}}
                }
            )
            
            card_info = CardInfo(
                name="Arcanine",
                collector_number="59/150",
                confidence=92.0,
                ocr_result=ocr_result
            )
            
            csv_row = {
                "timestamp_iso": "2023-01-01T12:00:00",
                "scan_id": "test_scan_123",
                "image_filename": "test.jpg"
            }
            
            with patch('builtins.open', mock_open()) as mock_file:
                logger._save_detailed_log("test_scan_123", card_info, csv_row)
                
                # Should attempt to write log file
                mock_file.assert_called()
    
    def test_save_detailed_log_handles_exception(self, tmp_path):
        """Test that exceptions during detailed log saving are handled."""
        with patch('src.store.logger.Path') as mock_path:
            mock_path.return_value = tmp_path
            
            logger = CardDataLogger()
            
            # Create mock data
            card_info = CardInfo(name="Ninetales", confidence=85.0)
            csv_row = {"timestamp_iso": "2023-01-01T12:00:00"}
            
            # Mock file operations to raise exception
            with patch('builtins.open') as mock_file:
                mock_file.side_effect = Exception("File write failed")
                
                with patch.object(logger.logger, 'error') as mock_error:
                    logger._save_detailed_log("test_scan_123", card_info, csv_row)
                    
                    # Should log error
                    mock_error.assert_called_once_with(
                        "Failed to save detailed log",
                        scan_id="test_scan_123",
                        error="File write failed"
                    )


class TestScanSummary:
    """Test scan summary functionality."""
    
    def test_get_scan_summary_no_file(self, tmp_path):
        """Test scan summary when CSV file doesn't exist."""
        with patch('src.store.logger.Path') as mock_path:
            mock_path.return_value = tmp_path
            
            logger = CardDataLogger()
            
            # Mock CSV file to not exist
            logger.csv_file = tmp_path / "nonexistent.csv"
            
            summary = logger.get_scan_summary()
            
            # Should return empty summary
            assert summary["total_scans"] == 0
            assert summary["scans"] == []
    
    def test_get_scan_summary_with_data(self, tmp_path):
        """Test scan summary with existing scan data."""
        with patch('src.store.logger.Path') as mock_path:
            mock_path.return_value = tmp_path
            
            logger = CardDataLogger()
            
            # Create mock CSV file with data
            csv_file = tmp_path / "test_scans.csv"
            logger.csv_file = csv_file
            
            # Write test data
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=logger.csv_columns)
                writer.writeheader()
                writer.writerow({
                    "timestamp_iso": "2023-01-01T12:00:00",
                    "scan_id": "scan_1",
                    "image_filename": "scan_1.jpg",
                    "card_name": "Charizard",
                    "collector_number": "4/102",
                    "ocr_confidence": "85.5",
                    "processing_time_ms": "150",
                    "status": "completed",
                    "notes": "High confidence scan"
                })
                writer.writerow({
                    "timestamp_iso": "2023-01-01T12:01:00",
                    "scan_id": "scan_2",
                    "image_filename": "scan_2.jpg",
                    "card_name": "Pikachu",
                    "collector_number": "58/102",
                    "ocr_confidence": "45.0",
                    "processing_time_ms": "200",
                    "status": "failed",
                    "notes": "Low confidence scan"
                })
            
            summary = logger.get_scan_summary()
            
            # Should have correct counts
            assert summary["total_scans"] == 2
            assert summary["successful_scans"] == 1
            assert summary["failed_scans"] == 1
            
            # Should have correct average confidence
            assert summary["average_confidence"] == 65.25
            
            # Should have scans data
            assert len(summary["scans"]) == 2
    
    def test_get_scan_summary_handles_exception(self, tmp_path):
        """Test that exceptions during summary generation are handled."""
        with patch('src.store.logger.Path') as mock_path:
            mock_path.return_value = tmp_path
            
            logger = CardDataLogger()
            
            # Mock file operations to raise exception
            with patch('builtins.open') as mock_file:
                mock_file.side_effect = Exception("File read failed")
                
                with patch.object(logger.logger, 'error') as mock_error:
                    summary = logger.get_scan_summary()
                    
                    # Should log error
                    mock_error.assert_called_once_with("Failed to get scan summary", error="File read failed")
                    
                    # Should return error
                    assert "error" in summary


class TestSummaryExport:
    """Test summary export functionality."""
    
    def test_export_summary_csv_success(self, tmp_path):
        """Test successful summary CSV export."""
        with patch('src.store.logger.Path') as mock_path:
            mock_path.return_value = tmp_path
            
            logger = CardDataLogger()
            
            # Mock get_scan_summary to return data
            mock_summary = {
                "scans": [
                    {
                        "timestamp_iso": "2023-01-01T12:00:00",
                        "scan_id": "scan_1",
                        "card_name": "Charizard"
                    }
                ]
            }
            
            with patch.object(logger, 'get_scan_summary', return_value=mock_summary):
                with patch('builtins.open', mock_open()):
                    export_path = logger.export_summary_csv("test_export.csv")
                    
                    # Should return export path
                    assert "test_export.csv" in export_path
    
    def test_export_summary_csv_generates_filename(self, tmp_path):
        """Test that filename is generated if not provided."""
        with patch('src.store.logger.Path') as mock_path:
            # Mock Path("output") to return tmp_path
            def mock_path_side_effect(path_str):
                if path_str == "output":
                    return tmp_path
                return Path(path_str)
            
            mock_path.side_effect = mock_path_side_effect
            
            logger = CardDataLogger()
            
            # Mock get_scan_summary to return data
            mock_summary = {"scans": []}
            
            with patch.object(logger, 'get_scan_summary', return_value=mock_summary):
                with patch('builtins.open', mock_open()):
                    export_path = logger.export_summary_csv()
                    
                    # Should generate filename with timestamp
                    assert "scan_summary_" in export_path
                    assert export_path.endswith(".csv")
    
    def test_export_summary_csv_handles_error(self, tmp_path):
        """Test that errors during export are handled."""
        with patch('src.store.logger.Path') as mock_path:
            mock_path.return_value = tmp_path
            
            logger = CardDataLogger()
            
            # Mock get_scan_summary to return error
            mock_summary = {"error": "Failed to get summary"}
            
            with patch.object(logger, 'get_scan_summary', return_value=mock_summary):
                with patch.object(logger.logger, 'error') as mock_error:
                    with pytest.raises(Exception) as exc_info:
                        logger.export_summary_csv("test.csv")
                    
                    # Should raise exception with error message
                    assert "Failed to get summary" in str(exc_info.value)
                    
                    # Should log error
                    mock_error.assert_called_once_with("Failed to export summary CSV", error="Failed to get summary")


class TestIntegration:
    """Test integration scenarios."""
    
    def test_logger_singleton(self):
        """Test that card_data_logger is a singleton."""
        # Should be the same instance
        assert card_data_logger is not None
        assert isinstance(card_data_logger, CardDataLogger)
        
        # Creating a new instance should be different
        new_logger = CardDataLogger()
        assert new_logger is not card_data_logger
    
    def test_logger_with_logger_mixin(self):
        """Test that logger works with LoggerMixin."""
        logger = CardDataLogger()
        
        # Should have logger property from LoggerMixin
        assert hasattr(logger, 'logger')
        assert logger.logger is not None
        
        # Should have log methods
        assert hasattr(logger, 'log_start')
        assert hasattr(logger, 'log_success')
        assert hasattr(logger, 'log_error')
    
    def test_logger_file_operations(self, tmp_path):
        """Test that logger performs file operations correctly."""
        # Mock the Path to return our tmp_path for the output directory
        with patch('src.store.logger.Path') as mock_path:
            # Mock Path("output") to return tmp_path
            def mock_path_side_effect(path_str):
                if path_str == "output":
                    return tmp_path
                return Path(path_str)
            
            mock_path.side_effect = mock_path_side_effect
            
            logger = CardDataLogger()
            
            # Should create necessary directories
            assert (tmp_path).exists()
            assert (tmp_path / "images").exists()
            assert (tmp_path / "logs").exists()
            
            # Should create CSV file
            assert logger.csv_file.exists()
            
            # CSV file should contain headers
            with open(logger.csv_file, 'r', encoding='utf-8') as f:
                content = f.read()
                for column in logger.csv_columns:
                    assert column in content
