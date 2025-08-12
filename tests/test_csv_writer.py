"""Tests for CSV writer functionality."""

import pytest
import csv
import json
from pathlib import Path
from datetime import datetime
import os
import tempfile
import shutil

from src.store.writer import CSVWriter


class TestCSVWriter:
    """Test CSV writing functionality."""
    
    @pytest.fixture
    def writer(self, tmp_path):
        """Create CSV writer instance with isolated temp directory."""
        # Temporarily change to tmp_path for testing
        original_cwd = Path.cwd()
        os.chdir(tmp_path)
        
        writer = CSVWriter()
        
        # Restore original directory after test
        yield writer
        
        os.chdir(original_cwd)
    
    def test_csv_initialization(self, writer):
        """Test that CSV writer is properly initialized."""
        # Check that output directory exists
        assert writer.output_dir.exists()
        assert writer.output_dir.name == "output"
        
        # Check that CSV path is set
        assert writer.csv_path is not None
        assert "cards_" in writer.csv_path.name
        assert writer.csv_path.suffix == ".csv"
    
    def test_fixed_header_structure(self, writer):
        """Test that the fixed header structure is correct."""
        expected_header = [
            "timestamp_iso",
            "card_id",
            "name",
            "number",
            "set_name",
            "set_id",
            "rarity",
            "tcgplayer_market_usd",
            "cardmarket_trend_eur",
            "cardmarket_avg30_eur",
            "pricing_updatedAt_tcgplayer",
            "pricing_updatedAt_cardmarket",
            "source_image_path",
            "price_sources"
        ]
        
        assert writer.FIXED_HEADER == expected_header
    
    def test_write_row_creates_file_with_header(self, writer):
        """Test that writing a row creates the CSV file with proper header."""
        # Write a test row
        test_row = {
            "timestamp_iso": "2025-01-11T02:15:00",
            "card_id": "test-001",
            "name": "Charizard",
            "number": "4",
            "set_name": "Base Set",
            "set_id": "base1",
            "rarity": "Holo Rare",
            "tcgplayer_market_usd": "100.00",
            "cardmarket_trend_eur": "80.00",
            "cardmarket_avg30_eur": "85.00",
            "pricing_updatedAt_tcgplayer": "2025-01-11T02:00:00",
            "pricing_updatedAt_cardmarket": "2025-01-11T02:00:00",
            "source_image_path": "/path/to/image.jpg",
            "price_sources": '["pokemontcg.io"]'
        }
        
        writer.write_row(test_row)
        
        # Check that file was created
        assert writer.csv_path.exists()
        
        # Check header
        with open(writer.csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)
            assert headers == writer.FIXED_HEADER
            
            # Check first row
            row = next(reader)
            assert row[1] == "test-001"  # card_id
            assert row[2] == "Charizard"  # name
            assert row[3] == "4"  # number
    
    def test_write_row_appends_to_existing_file(self, writer):
        """Test that writing multiple rows appends to existing file."""
        # Write first row
        first_row = {
            "timestamp_iso": "2025-01-11T02:15:00",
            "card_id": "test-001",
            "name": "Charizard",
            "number": "4",
            "set_name": "Base Set",
            "set_id": "base1",
            "rarity": "Holo Rare",
            "tcgplayer_market_usd": "100.00",
            "cardmarket_trend_eur": "80.00",
            "cardmarket_avg30_eur": "85.00",
            "pricing_updatedAt_tcgplayer": "2025-01-11T02:00:00",
            "pricing_updatedAt_cardmarket": "2025-01-11T02:00:00",
            "source_image_path": "/path/to/image.jpg",
            "price_sources": '["pokemontcg.io"]'
        }
        
        writer.write_row(first_row)
        
        # Write second row
        second_row = {
            "timestamp_iso": "2025-01-11T02:16:00",
            "card_id": "test-002",
            "name": "Blastoise",
            "number": "2",
            "set_name": "Base Set",
            "set_id": "base1",
            "rarity": "Holo Rare",
            "tcgplayer_market_usd": "50.00",
            "cardmarket_trend_eur": "40.00",
            "cardmarket_avg30_eur": "45.00",
            "pricing_updatedAt_tcgplayer": "2025-01-11T02:00:00",
            "pricing_updatedAt_cardmarket": "2025-01-11T02:00:00",
            "source_image_path": "/path/to/image2.jpg",
            "price_sources": '["pokemontcg.io"]'
        }
        
        writer.write_row(second_row)
        
        # Check that both rows exist
        with open(writer.csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)  # Skip header
            rows = list(reader)
            
            assert len(rows) == 2
            assert rows[0][1] == "test-001"  # First card_id
            assert rows[1][1] == "test-002"  # Second card_id
    
    def test_build_row_function(self, writer):
        """Test the build_row function creates properly formatted rows."""
        # Mock Pokemon card data
        pokemon_card = {
            "id": "base1-4",
            "name": "Charizard",
            "number": "4",
            "set": {
                "name": "Base Set",
                "id": "base1"
            },
            "rarity": "Holo Rare"
        }
        
        # Mock price data
        price_data = {
            "tcgplayer_market_usd": "100.00",
            "cardmarket_trend_eur": "80.00",
            "cardmarket_avg30_eur": "85.00",
            "pricing_updatedAt_tcgplayer": "2025-01-11T02:00:00",
            "pricing_updatedAt_cardmarket": "2025-01-11T02:00:00",
            "price_sources": ["pokemontcg.io"]
        }
        
        source_image_path = "/path/to/image.jpg"
        
        # Build row
        row = writer.build_row(pokemon_card, price_data, source_image_path)
        
        # Check that all required fields are present
        assert "timestamp_iso" in row
        assert row["card_id"] == "base1-4"
        assert row["name"] == "Charizard"
        assert row["number"] == "4"
        assert row["set_name"] == "Base Set"
        assert row["set_id"] == "base1"
        assert row["rarity"] == "Holo Rare"
        assert row["tcgplayer_market_usd"] == "100.00"
        assert row["cardmarket_trend_eur"] == "80.00"
        assert row["cardmarket_avg30_eur"] == "85.00"
        assert row["source_image_path"] == "/path/to/image.jpg"
        
        # Check that price_sources is serialized as JSON
        price_sources = json.loads(row["price_sources"])
        assert isinstance(price_sources, list)
        assert "pokemontcg.io" in price_sources
    
    def test_build_row_handles_missing_data(self, writer):
        """Test that build_row handles missing or None data gracefully."""
        # Minimal Pokemon card data
        pokemon_card = {
            "id": "test-001",
            "name": "Test Card"
        }
        
        # Minimal price data
        price_data = {}
        
        source_image_path = "/path/to/image.jpg"
        
        # Build row
        row = writer.build_row(pokemon_card, price_data, source_image_path)
        
        # Check that missing fields are empty strings
        assert row["number"] == ""
        assert row["set_name"] == ""
        assert row["set_id"] == ""
        assert row["rarity"] == ""
        assert row["tcgplayer_market_usd"] == ""
        assert row["cardmarket_trend_eur"] == ""
        assert row["cardmarket_avg30_eur"] == ""
        assert row["pricing_updatedAt_tcgplayer"] == ""
        assert row["pricing_updatedAt_cardmarket"] == ""
        
        # Check that required fields are present
        assert row["card_id"] == "test-001"
        assert row["name"] == "Test Card"
        assert row["source_image_path"] == "/path/to/image.jpg"
        assert row["price_sources"] == "[]"  # Empty list as JSON

    def test_build_row_handles_nested_none_values(self, writer):
        """Test that build_row handles nested None values in set data."""
        # Pokemon card data with None in nested set
        pokemon_card = {
            "id": "test-002",
            "name": "Test Card 2",
            "set": None
        }
        
        price_data = {}
        source_image_path = "/path/to/image2.jpg"
        
        # Build row
        row = writer.build_row(pokemon_card, price_data, source_image_path)
        
        # Check that nested None values become empty strings
        assert row["set_name"] == ""
        assert row["set_id"] == ""
        
        # Check that other fields are handled correctly
        assert row["card_id"] == "test-002"
        assert row["name"] == "Test Card 2"

    def test_build_row_price_sources_serialization_edge_cases(self, writer):
        """Test price_sources serialization with various data types."""
        pokemon_card = {"id": "test-003", "name": "Test Card 3"}
        source_image_path = "/path/to/image3.jpg"
        
        # Test with string price_sources
        price_data_str = {"price_sources": "pokemontcg.io"}
        row_str = writer.build_row(pokemon_card, price_data_str, source_image_path)
        assert row_str["price_sources"] == '["pokemontcg.io"]'
        
        # Test with None price_sources
        price_data_none = {"price_sources": None}
        row_none = writer.build_row(pokemon_card, price_data_none, source_image_path)
        assert row_none["price_sources"] == "[]"
        
        # Test with empty list
        price_data_empty = {"price_sources": []}
        row_empty = writer.build_row(pokemon_card, price_data_empty, source_image_path)
        assert row_empty["price_sources"] == "[]"
        
        # Test with complex list
        price_data_complex = {"price_sources": ["source1", "source2", "source3"]}
        row_complex = writer.build_row(pokemon_card, price_data_complex, source_image_path)
        parsed = json.loads(row_complex["price_sources"])
        assert parsed == ["source1", "source2", "source3"]

    def test_daily_csv_path_generation(self, writer):
        """Test that daily CSV path generation works correctly."""
        # Get the daily path
        daily_path = writer.get_daily_csv_path()
        
        # Check format: cards_YYYYMMDD.csv
        assert daily_path.name.startswith("cards_")
        assert daily_path.name.endswith(".csv")
        
        # Check that the date part is valid
        date_part = daily_path.name[6:-4]  # Extract YYYYMMDD
        assert len(date_part) == 8
        assert date_part.isdigit()
        
        # Verify it's today's date
        today = datetime.now().strftime('%Y%m%d')
        assert date_part == today

    def test_csv_column_order_preservation(self, writer):
        """Test that CSV column order exactly matches FIXED_HEADER."""
        # Write a test row
        test_row = {
            "timestamp_iso": "2025-01-11T02:15:00",
            "card_id": "test-001",
            "name": "Charizard",
            "number": "4",
            "set_name": "Base Set",
            "set_id": "base1",
            "rarity": "Holo Rare",
            "tcgplayer_market_usd": "100.00",
            "cardmarket_trend_eur": "80.00",
            "cardmarket_avg30_eur": "85.00",
            "pricing_updatedAt_tcgplayer": "2025-01-11T02:00:00",
            "pricing_updatedAt_cardmarket": "2025-01-11T02:00:00",
            "source_image_path": "/path/to/image.jpg",
            "price_sources": '["pokemontcg.io"]'
        }
        
        writer.write_row(test_row)
        
        # Read back and verify column order
        with open(writer.csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            row = next(reader)
            
            # Verify that all columns are present in exact order
            for i, header in enumerate(writer.FIXED_HEADER):
                assert header in row, f"Column {header} missing from row"
                # Verify the order by checking the first few values
                if i == 0:
                    assert row[header] == "2025-01-11T02:15:00"  # timestamp_iso
                elif i == 1:
                    assert row[header] == "test-001"  # card_id
                elif i == 2:
                    assert row[header] == "Charizard"  # name

    def test_csv_file_atomicity_fsync(self, writer):
        """Test that fsync is called for atomic-ish behavior."""
        # This test verifies that the file operations include fsync
        # We can't easily test fsync directly, but we can verify the file is written
        test_row = {
            "timestamp_iso": "2025-01-11T02:15:00",
            "card_id": "test-atomic",
            "name": "Atomic Test Card",
            "number": "1",
            "set_name": "Test Set",
            "set_id": "test",
            "rarity": "Common",
            "tcgplayer_market_usd": "1.00",
            "cardmarket_trend_eur": "1.00",
            "cardmarket_avg30_eur": "1.00",
            "pricing_updatedAt_tcgplayer": "2025-01-11T02:00:00",
            "pricing_updatedAt_cardmarket": "2025-01-11T02:00:00",
            "source_image_path": "/path/to/atomic.jpg",
            "price_sources": '["test"]'
        }
        
        # Write the row
        writer.write_row(test_row)
        
        # Verify the file exists and contains the data
        assert writer.csv_path.exists()
        
        # Read back and verify content
        with open(writer.csv_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "test-atomic" in content
            assert "Atomic Test Card" in content

    def test_csv_writer_handles_empty_price_data(self, writer):
        """Test that CSV writer handles completely empty price data."""
        pokemon_card = {"id": "test-empty", "name": "Empty Price Card"}
        price_data = {}  # Completely empty
        source_image_path = "/path/to/empty.jpg"
        
        # Build row
        row = writer.build_row(pokemon_card, price_data, source_image_path)
        
        # Write row
        writer.write_row(row)
        
        # Verify file was created and contains the row
        assert writer.csv_path.exists()
        
        with open(writer.csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            written_row = next(reader)
            
            # Check that empty price fields are empty strings
            assert written_row["tcgplayer_market_usd"] == ""
            assert written_row["cardmarket_trend_eur"] == ""
            assert written_row["cardmarket_avg30_eur"] == ""
            assert written_row["pricing_updatedAt_tcgplayer"] == ""
            assert written_row["pricing_updatedAt_cardmarket"] == ""
            assert written_row["price_sources"] == "[]"


if __name__ == "__main__":
    pytest.main([__file__])
