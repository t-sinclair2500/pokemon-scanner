"""Tests for pricing extraction functionality."""

import pytest

from src.pricing.poketcg_prices import PokemonTCGPricer, CardPrice, PriceData
from src.resolve.poketcg import PokemonCard


class TestCardPrice:
    """Test CardPrice dataclass."""
    
    def test_card_price_creation(self):
        """Test creating CardPrice instance."""
        price = CardPrice(
            tcgplayer_market_usd=125.00,
            cardmarket_trend_eur=120.00,
            cardmarket_avg30_eur=118.75,
            pricing_updatedAt_tcgplayer="2023/12/01",
            pricing_updatedAt_cardmarket="2023/12/01",
            price_sources=["pokemontcg.io"]
        )
        
        assert price.tcgplayer_market_usd == 125.00
        assert price.cardmarket_trend_eur == 120.00
        assert price.cardmarket_avg30_eur == 118.75
        assert price.pricing_updatedAt_tcgplayer == "2023/12/01"
        assert price.pricing_updatedAt_cardmarket == "2023/12/01"
        assert price.price_sources == ["pokemontcg.io"]
    
    def test_card_price_defaults(self):
        """Test CardPrice with default values."""
        price = CardPrice()
        
        assert price.tcgplayer_market_usd is None
        assert price.cardmarket_trend_eur is None
        assert price.cardmarket_avg30_eur is None
        assert price.pricing_updatedAt_tcgplayer == ""
        assert price.pricing_updatedAt_cardmarket == ""
        assert price.price_sources == ["pokemontcg.io"]


class TestPokemonTCGPricer:
    """Test Pokemon TCG pricing extraction."""
    
    @pytest.fixture
    def pricer(self):
        """Create pricer instance."""
        return PokemonTCGPricer()
    
    def test_extract_prices_holofoil_priority(self, pricer):
        """Test extracting holofoil market price."""
        card = PokemonCard(
            id="base1-4", name="Charizard", number="4", set_name="Base", 
            set_id="base1", rarity="Rare Holo", images={},
            tcgplayer={
                "updatedAt": "2023/12/01",
                "prices": {
                    "holofoil": {"market": 125.00}
                }
            },
            cardmarket={
                "updatedAt": "2023/12/01", 
                "prices": {
                    "trendPrice": 120.00,
                    "averageSellPrice": 118.75
                }
            }
        )
        
        price_data = pricer.extract_prices(card)
        
        assert price_data is not None
        assert price_data.card_id == "base1-4"
        assert price_data.card_name == "Charizard"
        assert price_data.prices.tcgplayer_market_usd == 125.00
        assert price_data.prices.cardmarket_trend_eur == 120.00
        assert price_data.prices.cardmarket_avg30_eur == 118.75
    
    def test_extract_prices_normal_priority(self, pricer):
        """Test normal market price takes priority."""
        card = PokemonCard(
            id="test-1", name="Test", number="1", set_name="Test",
            set_id="test", rarity="Common", images={},
            tcgplayer={
                "prices": {
                    "normal": {"market": 10.00},
                    "holofoil": {"market": 20.00}
                }
            }
        )
        
        price_data = pricer.extract_prices(card)
        assert price_data.prices.tcgplayer_market_usd == 10.00
    
    def test_extract_prices_no_pricing(self, pricer):
        """Test card with no valid pricing."""
        card = PokemonCard(
            id="test-2", name="Test", number="2", set_name="Test",
            set_id="test", rarity="Common", images={}
        )
        
        price_data = pricer.extract_prices(card)
        assert price_data is None


if __name__ == "__main__":
    pytest.main([__file__])