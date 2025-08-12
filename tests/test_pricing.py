"""Tests for pricing extraction functionality."""

import pytest

from src.pricing.poketcg_prices import PokemonTCGPricer, PriceData
from src.resolve.poketcg import PokemonCard


class TestPriceData:
    """Test PriceData dataclass."""

    def test_price_data_default_initialization(self):
        """Test PriceData with default values."""
        price_data = PriceData()

        assert price_data.tcgplayer_market_usd == ""
        assert price_data.cardmarket_trend_eur == ""
        assert price_data.cardmarket_avg30_eur == ""
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
        """Test price_sources defaults to pokemontcg.io when None."""
        price_data = PriceData(price_sources=None)
        assert price_data.price_sources == ["pokemontcg.io"]


class TestPokemonTCGPricer:
    """Test Pokemon TCG pricing extraction."""

    @pytest.fixture
    def pricer(self):
        """Create pricer instance."""
        return PokemonTCGPricer()

    def test_extract_prices_holofoil_priority(self, pricer):
        """Test extracting holofoil market price with fallback order."""
        card = PokemonCard(
            id="base1-4",
            name="Charizard",
            number="4",
            set_name="Base",
            set_id="base1",
            rarity="Rare Holo",
            images={},
            tcgplayer={
                "updatedAt": "2023/12/01",
                "prices": {"holofoil": {"market": 125.00}},
            },
            cardmarket={
                "updatedAt": "2023/12/01",
                "prices": {"trendPrice": 120.00, "avg30": 118.75},
            },
        )

        price_data = pricer.extract_prices_from_card(card)

        assert price_data.tcgplayer_market_usd == "125.00"
        assert price_data.cardmarket_trend_eur == "120.00"
        assert price_data.cardmarket_avg30_eur == "118.75"
        assert price_data.pricing_updatedAt_tcgplayer == "2023/12/01"
        assert price_data.pricing_updatedAt_cardmarket == "2023/12/01"
        assert price_data.price_sources == ["pokemontcg.io"]

    def test_extract_prices_normal_priority(self, pricer):
        """Test normal market price takes priority over holofoil."""
        card = PokemonCard(
            id="test-1",
            name="Test",
            number="1",
            set_name="Test",
            set_id="test",
            rarity="Common",
            images={},
            tcgplayer={
                "prices": {"normal": {"market": 10.00}, "holofoil": {"market": 20.00}}
            },
        )

        price_data = pricer.extract_prices_from_card(card)
        assert price_data.tcgplayer_market_usd == "10.00"
        assert price_data.cardmarket_trend_eur == ""
        assert price_data.cardmarket_avg30_eur == ""

    def test_extract_prices_reverse_holofoil_fallback(self, pricer):
        """Test reverse holofoil fallback when normal and holofoil missing."""
        card = PokemonCard(
            id="test-2",
            name="Test",
            number="2",
            set_name="Test",
            set_id="test",
            rarity="Common",
            images={},
            tcgplayer={"prices": {"reverseHolofoil": {"market": 15.00}}},
        )

        price_data = pricer.extract_prices_from_card(card)
        assert price_data.tcgplayer_market_usd == "15.00"

    def test_extract_prices_no_pricing(self, pricer):
        """Test card with no valid pricing returns empty PriceData."""
        card = PokemonCard(
            id="test-3",
            name="Test",
            number="3",
            set_name="Test",
            set_id="test",
            rarity="Common",
            images={},
        )

        price_data = pricer.extract_prices_from_card(card)
        assert isinstance(price_data, PriceData)
        assert price_data.tcgplayer_market_usd == ""
        assert price_data.cardmarket_trend_eur == ""
        assert price_data.cardmarket_avg30_eur == ""
        assert price_data.pricing_updatedAt_tcgplayer == ""
        assert price_data.pricing_updatedAt_cardmarket == ""

    def test_extract_prices_partial_tcgplayer(self, pricer):
        """Test partial TCGPlayer data extraction."""
        card = PokemonCard(
            id="test-4",
            name="Test",
            number="4",
            set_name="Test",
            set_id="test",
            rarity="Common",
            images={},
            tcgplayer={"prices": {"normal": {"market": 25.00}}},
        )

        price_data = pricer.extract_prices_from_card(card)
        assert price_data.tcgplayer_market_usd == "25.00"
        assert price_data.cardmarket_trend_eur == ""
        assert price_data.cardmarket_avg30_eur == ""

    def test_extract_prices_partial_cardmarket(self, pricer):
        """Test partial CardMarket data extraction."""
        card = PokemonCard(
            id="test-5",
            name="Test",
            number="5",
            set_name="Test",
            set_id="test",
            rarity="Common",
            images={},
            cardmarket={"prices": {"trendPrice": 30.00}},
        )

        price_data = pricer.extract_prices_from_card(card)
        assert price_data.tcgplayer_market_usd == ""
        assert price_data.cardmarket_trend_eur == "30.00"
        assert price_data.cardmarket_avg30_eur == ""

    def test_extract_prices_malformed_data(self, pricer):
        """Test handling of malformed pricing data."""
        card = PokemonCard(
            id="test-6",
            name="Test",
            number="6",
            set_name="Test",
            set_id="test",
            rarity="Common",
            images={},
            tcgplayer={
                "prices": {
                    "normal": {"market": None},
                    "holofoil": {"market": "invalid_price"},
                }
            },
            cardmarket={"prices": {"trendPrice": None, "avg30": "not_a_number"}},
        )

        price_data = pricer.extract_prices_from_card(card)
        assert isinstance(price_data, PriceData)
        # Should handle None values gracefully
        assert price_data.tcgplayer_market_usd == ""
        assert price_data.cardmarket_trend_eur == ""
        assert price_data.cardmarket_avg30_eur == ""

    def test_extract_prices_empty_prices_dict(self, pricer):
        """Test handling of empty prices dictionary."""
        card = PokemonCard(
            id="test-7",
            name="Test",
            number="7",
            set_name="Test",
            set_id="test",
            rarity="Common",
            images={},
            tcgplayer={"prices": {}},
            cardmarket={"prices": {}},
        )

        price_data = pricer.extract_prices_from_card(card)
        assert isinstance(price_data, PriceData)
        assert price_data.tcgplayer_market_usd == ""
        assert price_data.cardmarket_trend_eur == ""
        assert price_data.cardmarket_avg30_eur == ""

    def test_extract_prices_missing_prices_key(self, pricer):
        """Test handling of missing 'prices' key."""
        card = PokemonCard(
            id="test-8",
            name="Test",
            number="8",
            set_name="Test",
            set_id="test",
            rarity="Common",
            images={},
            tcgplayer={"updatedAt": "2023/12/01"},
            cardmarket={"updatedAt": "2023/12/01"},
        )

        price_data = pricer.extract_prices_from_card(card)
        assert isinstance(price_data, PriceData)
        assert price_data.tcgplayer_market_usd == ""
        assert price_data.cardmarket_trend_eur == ""
        assert price_data.cardmarket_avg30_eur == ""
        assert price_data.pricing_updatedAt_tcgplayer == "2023/12/01"
        assert price_data.pricing_updatedAt_cardmarket == "2023/12/01"

    def test_extract_prices_numeric_strings(self, pricer):
        """Test that numeric values are converted to strings."""
        card = PokemonCard(
            id="test-9",
            name="Test",
            number="9",
            set_name="Test",
            set_id="test",
            rarity="Common",
            images={},
            tcgplayer={"prices": {"normal": {"market": 42.50}}},
            cardmarket={"prices": {"trendPrice": 40.00, "avg30": 38.75}},
        )

        price_data = pricer.extract_prices_from_card(card)
        assert price_data.tcgplayer_market_usd == "42.50"
        assert price_data.cardmarket_trend_eur == "40.00"
        assert price_data.cardmarket_avg30_eur == "38.75"
        # Verify they are strings, not numbers
        assert isinstance(price_data.tcgplayer_market_usd, str)
        assert isinstance(price_data.cardmarket_trend_eur, str)
        assert isinstance(price_data.cardmarket_avg30_eur, str)


if __name__ == "__main__":
    pytest.main([__file__])
