"""Tests for CSV writer functionality."""

import pytest
import csv
from pathlib import Path
from datetime import datetime

from src.store.writer import EnhancedCSVWriter


class TestEnhancedCSVWriter:
    """Test Enhanced CSV writing functionality."""
    
    @pytest.fixture
    def writer(self, tmp_path):
        """Create Enhanced CSV writer instance with isolated temp directory."""
        writer = EnhancedCSVWriter()
        writer.set_output_dir(tmp_path)
        return writer
    
    def test_csv_initialization(self, writer, tmp_path):
        """Test that CSV files are properly initialized."""
        # Check that both CSV files exist
        assert writer.scans_csv.exists()
        assert writer.details_csv.exists()
        
        # Check scans CSV headers
        with open(writer.scans_csv, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)
            expected_scans_columns = [
                "timestamp_iso", "scan_id", "image_filename", "card_name",
                "collector_number", "ocr_confidence", "processing_time_ms",
                "status", "notes"
            ]
            assert headers == expected_scans_columns
        
        # Check details CSV headers
        with open(writer.details_csv, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)
            expected_details_columns = [
                "timestamp_iso", "scan_id", "image_filename", "card_name",
                "collector_number", "ocr_confidence", "processing_time_ms",
                "status", "notes", "raw_text_name", "raw_text_number",
                "preprocessing_method_name", "preprocessing_method_number",
                "roi_name", "roi_number", "tesseract_config_name",
                "tesseract_config_number"
            ]
            assert headers == expected_details_columns
    
    def test_write_scan_data(self, writer):
        """Test that scan data is written to both CSV files."""
        # Sample scan data
        scan_data = {
            "scan_id": "test_scan_001",
            "image_filename": "test_card.jpg",
            "card_name": "Charizard",
            "collector_number": "4",
            "ocr_confidence": 0.95,
            "processing_time_ms": 150,
            "status": "success",
            "notes": "Test scan"
        }
        
        # Write scan data
        filepath = writer.write_scan_data(scan_data)
        
        # Verify data was written to scans CSV
        with open(writer.scans_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            assert rows[0]["scan_id"] == "test_scan_001"
            assert rows[0]["card_name"] == "Charizard"
        
        # Verify data was written to details CSV
        with open(writer.details_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            assert rows[0]["scan_id"] == "test_scan_001"
            assert rows[0]["card_name"] == "Charizard"
    
    def test_csv_append_mode(self, writer):
        """Test that CSV writer appends to existing files."""
        # First scan
        first_scan = {
            "scan_id": "scan_001",
            "image_filename": "charizard.jpg",
            "card_name": "Charizard",
            "collector_number": "4",
            "ocr_confidence": 0.95,
            "processing_time_ms": 150,
            "status": "success",
            "notes": ""
        }
        
        writer.write_scan_data(first_scan)
        
        # Second scan (should append)
        second_scan = {
            "scan_id": "scan_002",
            "image_filename": "pikachu.jpg",
            "card_name": "Pikachu",
            "collector_number": "25",
            "ocr_confidence": 0.92,
            "processing_time_ms": 120,
            "status": "success",
            "notes": ""
        }
        
        writer.write_scan_data(second_scan)
        
        # Verify both rows exist in scans CSV
        with open(writer.scans_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 2
            assert rows[0]["card_name"] == "Charizard"
            assert rows[1]["card_name"] == "Pikachu"
        
        # Verify both rows exist in details CSV
        with open(writer.details_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 2
            assert rows[0]["card_name"] == "Charizard"
            assert rows[1]["card_name"] == "Pikachu"
    
    def test_csv_missing_columns(self, writer):
        """Test CSV with missing columns gets empty strings."""
        # Data with only some columns
        scan_data = {
            "scan_id": "test_scan",
            "card_name": "Charizard"
            # Missing other required columns
        }
        
        writer.write_scan_data(scan_data)
        
        # Verify all columns exist with empty strings for missing
        with open(writer.scans_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            row = next(reader)
            
            assert row["scan_id"] == "test_scan"
            assert row["card_name"] == "Charizard"
            assert row["image_filename"] == ""  # Should be empty string
            assert row["collector_number"] == ""  # Should be empty string
            assert row["ocr_confidence"] == ""  # Should be empty string


if __name__ == "__main__":
    pytest.main([__file__])
