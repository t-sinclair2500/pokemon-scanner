"""Tests for Pokemon card resolution functionality."""

import pytest
import json
from unittest.mock import patch
from pathlib import Path

from src.resolve.poketcg import PokemonTCGResolver, PokemonCard
from src.ocr.extract import CardInfo


class TestPokemonCard:
    """Test PokemonCard dataclass."""
    
    def test_pokemon_card_creation(self):
        """Test creating PokemonCard instance."""
        card = PokemonCard(
            id="base1-4",
            name="Charizard",
            number="4",
            set_name="Base",
            set_id="base1",
            rarity="Rare Holo",
            images={"large": "test.png"}
        )
        
        assert card.id == "base1-4"
        assert card.name == "Charizard"
        assert card.number == "4"
        assert card.set_name == "Base"
        assert card.set_id == "base1"
        assert card.rarity == "Rare Holo"
        assert card.images["large"] == "test.png"


class TestPokemonTCGResolver:
    """Test Pokemon TCG API resolver."""
    
    @pytest.fixture
    def resolver(self):
        """Create resolver instance."""
        return PokemonTCGResolver()
    
    @pytest.fixture
    def charizard_data(self):
        """Load Charizard test data."""
        fixture_path = Path(__file__).parent / "fixtures" / "charizard_sample.json"
        with open(fixture_path) as f:
            return json.load(f)
    
    @pytest.fixture
    def pikachu_data(self):
        """Load Pikachu test data.""" 
        fixture_path = Path(__file__).parent / "fixtures" / "pikachu_sample.json"
        with open(fixture_path) as f:
            return json.load(f)
    
    def test_parse_card_data(self, resolver, charizard_data):
        """Test parsing API card data."""
        card_data = charizard_data["data"][0]
        card = resolver._parse_card_data(card_data)
        
        assert card is not None
        assert card.id == "base1-4"
        assert card.name == "Charizard"
        assert card.number == "4"
        assert card.set_name == "Base"
        assert card.set_id == "base1"
        assert card.rarity == "Rare Holo"
        assert card.tcgplayer is not None
        assert card.cardmarket is not None
    
    def test_parse_card_data_invalid(self, resolver):
        """Test parsing invalid data."""
        assert resolver._parse_card_data(None) is None
        assert resolver._parse_card_data({}) is None
        assert resolver._parse_card_data({"id": "", "name": ""}) is None  # Empty required fields
    
    def test_find_best_match_exact(self, resolver, charizard_data):
        """Test finding exact match."""
        card_info = CardInfo(
            name="Charizard",
            collector_number="4/102",
            confidence=85.0
        )
        
        card_data = charizard_data["data"][0]
        card = resolver._parse_card_data(card_data)
        candidates = [card]
        
        best_match = resolver._find_best_match(card_info, candidates)
        
        assert best_match is not None
        assert best_match.name == "Charizard"
        assert best_match.number == "4"
    
    def test_find_best_match_no_candidates(self, resolver):
        """Test with no candidates."""
        card_info = CardInfo(name="Charizard", collector_number="4/102")
        
        best_match = resolver._find_best_match(card_info, [])
        assert best_match is None
    
    def test_find_best_match_poor_score(self, resolver, pikachu_data):
        """Test when match score is too low."""
        card_info = CardInfo(
            name="Charizard",  # Looking for Charizard
            collector_number="4/102",
            confidence=85.0
        )
        
        # But only have Pikachu data
        card_data = pikachu_data["data"][0]
        card = resolver._parse_card_data(card_data)
        candidates = [card]
        
        best_match = resolver._find_best_match(card_info, candidates)
        
        # Should return None due to poor match (name mismatch)
        assert best_match is None
    
    def test_sync_wrappers(self, resolver):
        """Test synchronous wrapper methods."""
        # Test that sync wrappers exist and can be called
        assert hasattr(resolver, 'search_cards_sync')
        assert hasattr(resolver, 'resolve_card_sync')
        
        # Test with mock to avoid actual async calls
        with patch('asyncio.run') as mock_run:
            mock_run.return_value = []
            
            result = resolver.search_cards_sync("test")
            assert result == []
            mock_run.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])