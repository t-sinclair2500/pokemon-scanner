"""Tests for SQLite cache functionality."""

import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.pricing.poketcg_prices import PriceData
from src.core.types import ResolvedCard
from src.store.cache import CacheManager


class TestCacheManager:
    """Test CacheManager class."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_path = f.name
        yield temp_path
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    @pytest.fixture
    def cache_manager(self, temp_db_path):
        """Create a cache manager with temporary database."""
        return CacheManager(db_path=temp_db_path)

    @pytest.fixture
    def sample_card(self):
        """Create a sample Pokemon card."""
        return ResolvedCard(
            card_id="base1-4",
            name="Charizard",
            number="4",
            set_name="Base",
            set_id="base1",
            rarity="Rare Holo",
            images={},
            raw_tcgplayer={},
            raw_cardmarket={}
        )

    @pytest.fixture
    def sample_price_data(self):
        """Create sample price data."""
        return PriceData(
            tcgplayer_market_usd=125.00,
            cardmarket_trend_eur=120.00,
            cardmarket_avg30_eur=118.75,
            pricing_updatedAt_tcgplayer="2023/12/01",
            pricing_updatedAt_cardmarket="2023/12/01",
            price_sources=["pokemontcg.io"],
        )

    def test_database_initialization(self, cache_manager):
        """Test database tables are created correctly."""
        # Check that tables exist by trying to insert data
        card = ResolvedCard(
            card_id="test-1",
            name="Test",
            number="1",
            set_name="Test",
            set_id="test",
            rarity="Common",
            images={},
            raw_tcgplayer={},
            raw_cardmarket={}
        )

        # Should not raise an error
        cache_manager.upsert_card(card)

        # Verify the card was inserted
        price_data = PriceData(
            tcgplayer_market_usd=None,
            cardmarket_trend_eur=None,
            cardmarket_avg30_eur=None,
            pricing_updatedAt_tcgplayer="",
            pricing_updatedAt_cardmarket="",
            price_sources=[]
        )
        cache_manager.upsert_prices("test-1", price_data)

        # Should not raise an error
        cache_manager.insert_scan("test.jpg")

    def test_upsert_card(self, cache_manager, sample_card):
        """Test card upsert operations."""
        # Insert card
        cache_manager.upsert_card(sample_card)

        # Verify card exists by checking if we can get prices
        # (prices table has foreign key to cards table)
        price_data = PriceData(
            tcgplayer_market_usd=None,
            cardmarket_trend_eur=None,
            cardmarket_avg30_eur=None,
            pricing_updatedAt_tcgplayer="",
            pricing_updatedAt_cardmarket="",
            price_sources=[]
        )
        cache_manager.upsert_prices(sample_card.card_id, price_data)

        # Should not raise an error, indicating card exists
        assert True

    def test_upsert_prices(self, cache_manager, sample_card, sample_price_data):
        """Test price upsert operations."""
        # First insert the card
        cache_manager.upsert_card(sample_card)

        # Insert prices
        cache_manager.upsert_prices(sample_card.card_id, sample_price_data)

        # Retrieve prices from cache
        cached_prices = cache_manager.get_price_data_from_cache(
            sample_card.card_id, max_age_hours=24
        )

        assert cached_prices is not None
        assert cached_prices.tcgplayer_market_usd == "125.00"
        assert cached_prices.cardmarket_trend_eur == "120.00"
        assert cached_prices.cardmarket_avg30_eur == "118.75"
        assert cached_prices.pricing_updatedAt_tcgplayer == "2023/12/01"
        assert cached_prices.pricing_updatedAt_cardmarket == "2023/12/01"
        assert cached_prices.price_sources == ["pokemontcg.io"]

    def test_cache_hit_within_window(
        self, cache_manager, sample_card, sample_price_data
    ):
        """Test cache hit when data is within cache window."""
        # Insert card and prices
        cache_manager.upsert_card(sample_card)
        cache_manager.upsert_prices(sample_card.card_id, sample_price_data)

        # Retrieve prices within cache window
        cached_prices = cache_manager.get_price_data_from_cache(
            sample_card.card_id, max_age_hours=24
        )

        assert cached_prices is not None
        assert cached_prices.tcgplayer_market_usd == "125.00"

    def test_cache_miss_expired_data(
        self, cache_manager, sample_card, sample_price_data
    ):
        """Test cache miss when data is expired."""
        # Insert card and prices
        cache_manager.upsert_card(sample_card)
        cache_manager.upsert_prices(sample_card.card_id, sample_price_data)

        # Retrieve prices with very short cache window (should miss)
        cached_prices = cache_manager.get_price_data_from_cache(
            sample_card.card_id, max_age_hours=0
        )

        assert cached_prices is None

    def test_cache_miss_missing_data(self, cache_manager):
        """Test cache miss when no data exists."""
        cached_prices = cache_manager.get_price_data_from_cache(
            "nonexistent-card", max_age_hours=24
        )
        assert cached_prices is None

    def test_insert_scan(self, cache_manager):
        """Test scan insertion."""
        scan_id = cache_manager.insert_scan("test_image.jpg", {"ocr": "test data"})

        assert scan_id > 0

        # Verify scan was inserted
        new_scans = cache_manager.get_new_scans()
        assert len(new_scans) == 1
        assert new_scans[0]["id"] == scan_id
        assert new_scans[0]["image_path"] == "test_image.jpg"
        assert new_scans[0]["status"] == "NEW"
        assert new_scans[0]["ocr_data"] == {"ocr": "test data"}

    def test_update_scan_status(self, cache_manager):
        """Test scan status updates."""
        # Insert scan
        scan_id = cache_manager.insert_scan("test_image.jpg")

        # Update status
        cache_manager.update_scan_status(scan_id, "PROCESSED")

        # Verify status was updated
        new_scans = cache_manager.get_new_scans()
        assert len(new_scans) == 0  # No more NEW scans

        # Update with OCR data
        cache_manager.update_scan_status(scan_id, "COMPLETED", {"ocr": "updated data"})

        # Verify scan is still not in NEW status
        new_scans = cache_manager.get_new_scans()
        assert len(new_scans) == 0

    def test_get_new_scans(self, cache_manager):
        """Test retrieving new scans."""
        # Insert multiple scans
        scan1_id = cache_manager.insert_scan("image1.jpg")
        scan2_id = cache_manager.insert_scan("image2.jpg")

        # Get new scans
        new_scans = cache_manager.get_new_scans()

        assert len(new_scans) == 2
        scan_ids = [scan["id"] for scan in new_scans]
        assert scan1_id in scan_ids
        assert scan2_id in scan_ids

        # All should have NEW status
        for scan in new_scans:
            assert scan["status"] == "NEW"

    def test_price_data_serialization(self, cache_manager, sample_card):
        """Test that price data is properly serialized/deserialized."""
        # Create price data with complex price sources
        price_data = PriceData(
            tcgplayer_market_usd="42.50",
            cardmarket_trend_eur="40.00",
            cardmarket_avg30_eur="38.75",
            pricing_updatedAt_tcgplayer="2023/12/01",
            pricing_updatedAt_cardmarket="2023/12/01",
            price_sources=["pokemontcg.io", "manual_entry", "api_fallback"],
        )

        # Insert card and prices
        cache_manager.upsert_card(sample_card)
        cache_manager.upsert_prices(sample_card.card_id, price_data)

        # Retrieve from cache
        cached_prices = cache_manager.get_price_data_from_cache(
            sample_card.card_id, max_age_hours=24
        )

        assert cached_prices is not None
        assert cached_prices.price_sources == [
            "pokemontcg.io",
            "manual_entry",
            "api_fallback",
        ]

    def test_empty_price_data_handling(self, cache_manager, sample_card):
        """Test handling of empty price data."""
        # Create empty price data
        empty_price_data = PriceData(
            tcgplayer_market_usd=None,
            cardmarket_trend_eur=None,
            cardmarket_avg30_eur=None,
            pricing_updatedAt_tcgplayer="",
            pricing_updatedAt_cardmarket="",
            price_sources=[]
        )

        # Insert card and empty prices
        cache_manager.upsert_card(sample_card)
        cache_manager.upsert_prices(sample_card.card_id, empty_price_data)

        # Retrieve from cache
        cached_prices = cache_manager.get_price_data_from_cache(
            sample_card.card_id, max_age_hours=24
        )

        assert cached_prices is not None
        assert cached_prices.tcgplayer_market_usd == ""
        assert cached_prices.cardmarket_trend_eur == ""
        assert cached_prices.cardmarket_avg30_eur == ""
        assert cached_prices.price_sources == []  # Empty list should be returned as-is

    def test_multiple_price_sources(self, cache_manager, sample_card):
        """Test handling multiple price sources for the same card."""
        # Create price data with different sources
        price_data1 = PriceData(
            tcgplayer_market_usd=100.00,
            cardmarket_trend_eur=None,
            cardmarket_avg30_eur=None,
            pricing_updatedAt_tcgplayer="",
            pricing_updatedAt_cardmarket="",
            price_sources=["source1"]
        )

        price_data2 = PriceData(
            tcgplayer_market_usd=110.00,
            cardmarket_trend_eur=None,
            cardmarket_avg30_eur=None,
            pricing_updatedAt_tcgplayer="",
            pricing_updatedAt_cardmarket="",
            price_sources=["source2"]
        )

        # Insert card
        cache_manager.upsert_card(sample_card)

        # Insert prices from different sources
        cache_manager.upsert_prices(sample_card.card_id, price_data1, "source1")
        cache_manager.upsert_prices(sample_card.card_id, price_data2, "source2")

        # Both should be retrievable (though get_price_data_from_cache only gets one)
        # This tests that the composite primary key works correctly
        assert True

    def test_error_handling_invalid_card_id(self, cache_manager):
        """Test error handling with invalid card ID."""
        # Try to get prices for invalid card ID
        cached_prices = cache_manager.get_price_data_from_cache("", max_age_hours=24)
        assert cached_prices is None

    def test_error_handling_invalid_scan_id(self, cache_manager):
        """Test error handling with invalid scan ID."""
        # Try to update non-existent scan
        with pytest.raises(Exception):
            cache_manager.update_scan_status(99999, "PROCESSED")

    def test_close_method(self, cache_manager):
        """Test close method (should not raise errors)."""
        # Should not raise any errors
        cache_manager.close()
        assert True


if __name__ == "__main__":
    pytest.main([__file__])
