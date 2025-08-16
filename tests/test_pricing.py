"""Tests for pricing extraction functionality."""

import pytest

from src.core.types import PriceData


class TestPriceData:
    """Test PriceData dataclass."""

    def test_price_data_default_initialization(self):
        """Test PriceData with required values."""
        price_data = PriceData(
            tcgplayer_market_usd=None,
            cardmarket_trend_eur=None,
            cardmarket_avg30_eur=None,
            pricing_updatedAt_tcgplayer="",
            pricing_updatedAt_cardmarket="",
            price_sources=["pokemontcg.io"]
        )

        assert price_data.tcgplayer_market_usd is None
        assert price_data.cardmarket_trend_eur is None
        assert price_data.cardmarket_avg30_eur is None
        assert price_data.pricing_updatedAt_tcgplayer == ""
        assert price_data.pricing_updatedAt_cardmarket == ""
        assert price_data.price_sources == ["pokemontcg.io"]

    def test_price_data_custom_initialization(self):
        """Test PriceData with custom values."""
        price_data = PriceData(
            tcgplayer_market_usd="125.00",
            cardmarket_trend_eur="120.00",
            cardmarket_avg30_eur="118.75",
            pricing_updatedAt_tcgplayer="2023/12/01",
            pricing_updatedAt_cardmarket="2023/12/01",
            price_sources=["pokemontcg.io", "manual"],
        )

        assert price_data.tcgplayer_market_usd == "125.00"
        assert price_data.cardmarket_trend_eur == "120.00"
        assert price_data.cardmarket_avg30_eur == "118.75"
        assert price_data.pricing_updatedAt_tcgplayer == "2023/12/01"
        assert price_data.pricing_updatedAt_cardmarket == "2023/12/01"
        assert price_data.price_sources == ["pokemontcg.io", "manual"]

    def test_price_data_price_sources_default(self):
        """Test price_sources can be set to pokemontcg.io."""
        price_data = PriceData(
            tcgplayer_market_usd=None,
            cardmarket_trend_eur=None,
            cardmarket_avg30_eur=None,
            pricing_updatedAt_tcgplayer="",
            pricing_updatedAt_cardmarket="",
            price_sources=["pokemontcg.io"]
        )
        assert price_data.price_sources == ["pokemontcg.io"]


class TestMapPriceBlocks:
    """Test the new map_price_blocks function."""

    def test_map_price_blocks_with_tcgplayer_prices(self):
        """Test mapping TCGPlayer prices with fallback order."""
        from src.pricing.poketcg_prices import map_price_blocks
        
        card_json = {
            "tcgplayer": {
                "updatedAt": "2023/12/01",
                "prices": {
                    "normal": {"market": 10.00},
                    "holofoil": {"market": 20.00},
                    "reverseHolofoil": {"market": 15.00}
                }
            },
            "cardmarket": {
                "updatedAt": "2023/12/01",
                "prices": {
                    "trendPrice": 12.50,
                    "avg30": 11.75
                }
            }
        }
        
        price_data = map_price_blocks(card_json)
        
        # Should pick normal first (10.00) over holofoil (20.00) and reverseHolofoil (15.00)
        assert price_data.tcgplayer_market_usd == 10.00
        assert price_data.cardmarket_trend_eur == 12.50
        assert price_data.cardmarket_avg30_eur == 11.75
        assert price_data.pricing_updatedAt_tcgplayer == "2023/12/01"
        assert price_data.pricing_updatedAt_cardmarket == "2023/12/01"
        assert price_data.price_sources == ["pokemontcg.io"]

    def test_map_price_blocks_fallback_to_holofoil(self):
        """Test fallback to holofoil when normal price is missing."""
        from src.pricing.poketcg_prices import map_price_blocks
        
        card_json = {
            "tcgplayer": {
                "updatedAt": "2023/12/01",
                "prices": {
                    "holofoil": {"market": 25.00},
                    "reverseHolofoil": {"market": 18.00}
                }
            },
            "cardmarket": {
                "updatedAt": "2023/12/01",
                "prices": {
                    "trendPrice": 22.50,
                    "avg30": 21.00
                }
            }
        }
        
        price_data = map_price_blocks(card_json)
        
        # Should pick holofoil (25.00) since normal is missing
        assert price_data.tcgplayer_market_usd == 25.00
        assert price_data.cardmarket_trend_eur == 22.50
        assert price_data.cardmarket_avg30_eur == 21.00

    def test_map_price_blocks_no_tcgplayer_prices(self):
        """Test handling when TCGPlayer has no market prices."""
        from src.pricing.poketcg_prices import map_price_blocks
        
        card_json = {
            "tcgplayer": {
                "updatedAt": "2023/12/01",
                "prices": {
                    "normal": {"low": 5.00, "mid": 7.50, "high": 10.00}
                }
            },
            "cardmarket": {
                "updatedAt": "2023/12/01",
                "prices": {
                    "trendPrice": 6.50,
                    "avg30": 6.00
                }
            }
        }
        
        price_data = map_price_blocks(card_json)
        
        # Should be None since no market prices exist
        assert price_data.tcgplayer_market_usd is None
        assert price_data.cardmarket_trend_eur == 6.50
        assert price_data.cardmarket_avg30_eur == 6.00

    def test_map_price_blocks_empty_data(self):
        """Test handling of empty or missing data."""
        from src.pricing.poketcg_prices import map_price_blocks
        
        card_json = {}
        
        price_data = map_price_blocks(card_json)
        
        # All fields should be None or empty
        assert price_data.tcgplayer_market_usd is None
        assert price_data.cardmarket_trend_eur is None
        assert price_data.cardmarket_avg30_eur is None
        assert price_data.pricing_updatedAt_tcgplayer == ""
        assert price_data.pricing_updatedAt_cardmarket == ""
        assert price_data.price_sources == ["pokemontcg.io"]


if __name__ == "__main__":
    pytest.main([__file__])
