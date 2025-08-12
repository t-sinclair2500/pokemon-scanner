"""Tests for Pokemon TCG resolver functionality."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from aiohttp import ClientResponseError

from src.resolve.poketcg import PokemonTCGResolver, PokemonCard
from src.ocr.extract import CardInfo


class TestPokemonTCGResolver:
    """Test Pokemon TCG resolver functionality."""
    
    @pytest.fixture
    def resolver(self):
        """Create a resolver instance for testing."""
        return PokemonTCGResolver()
    
    @pytest.fixture
    def sample_card_info(self):
        """Create sample card info for testing."""
        return CardInfo(
            name="Charizard",
            collector_number={'num': 4, 'den': 102},
            confidence=85.0
        )
    
    @pytest.fixture
    def sample_cards(self):
        """Create sample Pokemon cards for testing."""
        return [
            PokemonCard(
                id="base1-4",
                name="Charizard",
                number="4",
                set_name="Base Set",
                set_id="base1",
                rarity="Holo Rare",
                images={"small": "url1", "large": "url2"},
                set_release_date="1999-01-09"
            ),
            PokemonCard(
                id="base1-4-alt",
                name="Charizard",
                number="4",
                set_name="Base Set 2",
                set_id="base2",
                rarity="Holo Rare",
                images={"small": "url3", "large": "url4"},
                set_release_date="2000-02-21"
            ),
            PokemonCard(
                id="base1-5",
                name="Charizard",
                number="5",
                set_name="Base Set",
                set_id="base1",
                rarity="Holo Rare",
                images={"small": "url5", "large": "url6"},
                set_release_date="1999-01-09"
            ),
            PokemonCard(
                id="base1-6",
                name="Blastoise",
                number="6",
                set_name="Base Set",
                set_id="base1",
                rarity="Holo Rare",
                images={"small": "url7", "large": "url8"},
                set_release_date="1999-01-09"
            )
        ]
    
    def test_resolver_initialization(self, resolver):
        """Test resolver initialization."""
        assert resolver.base_url == "https://api.pokemontcg.io/v2"
        assert resolver.min_request_interval == 0.2
        assert resolver.session is None
    
    @pytest.mark.asyncio
    async def test_ensure_session(self, resolver):
        """Test session creation."""
        # Mock aiohttp.ClientSession
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = Mock()
            mock_session.close = AsyncMock()  # Make close method async
            mock_session_class.return_value = mock_session
            
            await resolver._ensure_session()
            
            assert resolver.session is not None
            mock_session_class.assert_called_once()
            
            # Clean up
            await resolver.close()
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, resolver):
        """Test rate limiting functionality."""
        start_time = asyncio.get_event_loop().time()
        
        # First call should not delay
        await resolver._rate_limit()
        first_call_time = asyncio.get_event_loop().time()
        
        # Second call should delay
        await resolver._rate_limit()
        second_call_time = asyncio.get_event_loop().time()
        
        # Should have at least 0.2s delay
        delay = second_call_time - first_call_time
        assert delay >= 0.1  # Allow some tolerance for test environment
    
    @pytest.mark.asyncio
    async def test_request_with_backoff_success(self, resolver):
        """Test successful request without backoff."""
        with patch.object(resolver, '_ensure_session'), \
             patch.object(resolver, '_rate_limit'):
            
            # Mock successful response
            mock_response = Mock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"data": []})
            
            # Mock async context manager
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_response
            
            mock_session = Mock()
            mock_session.get.return_value = mock_context
            resolver.session = mock_session
            
            result = await resolver._request_with_backoff("http://test.com")
            
            assert result == {"data": []}
            mock_session.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_request_with_backoff_429_then_success(self, resolver):
        """Test 429 response then successful response with backoff."""
        with patch.object(resolver, '_ensure_session'), \
             patch.object(resolver, '_rate_limit'), \
             patch('asyncio.sleep') as mock_sleep:
            
            # Mock responses: first 429, then 200
            mock_response_429 = Mock()
            mock_response_429.status = 429
            
            mock_response_200 = Mock()
            mock_response_200.status = 200
            mock_response_200.json = AsyncMock(return_value={"data": []})
            
            # Mock async context managers
            mock_context_429 = AsyncMock()
            mock_context_429.__aenter__.return_value = mock_response_429
            
            mock_context_200 = AsyncMock()
            mock_context_200.__aenter__.return_value = mock_response_200
            
            mock_session = Mock()
            mock_session.get.side_effect = [mock_context_429, mock_context_200]
            resolver.session = mock_session
            
            result = await resolver._request_with_backoff("http://test.com")
            
            assert result == {"data": []}
            assert mock_sleep.called
            assert mock_session.get.call_count == 2
    
    @pytest.mark.asyncio
    async def test_request_with_backoff_500_then_success(self, resolver):
        """Test 500 response then successful response with backoff."""
        with patch.object(resolver, '_ensure_session'), \
             patch.object(resolver, '_rate_limit'), \
             patch('asyncio.sleep') as mock_sleep:
            
            # Mock responses: first 500, then 200
            mock_response_500 = Mock()
            mock_response_500.status = 500
            
            mock_response_200 = Mock()
            mock_response_200.status = 200
            mock_response_200.json = AsyncMock(return_value={"data": []})
            
            # Mock async context managers
            mock_context_500 = AsyncMock()
            mock_context_500.__aenter__.return_value = mock_response_500
            
            mock_context_200 = AsyncMock()
            mock_context_200.__aenter__.return_value = mock_response_200
            
            mock_session = Mock()
            mock_session.get.side_effect = [mock_context_500, mock_context_200]
            resolver.session = mock_session
            
            result = await resolver._request_with_backoff("http://test.com")
            
            assert result == {"data": []}
            assert mock_sleep.called
            assert mock_session.get.call_count == 2
    
    def test_find_best_match_priority_ranking(self, resolver, sample_card_info, sample_cards):
        """Test candidate ranking: number → name → date."""
        # Test that exact number match gets highest priority
        best_card = resolver._find_best_match(sample_card_info, sample_cards)
        
        assert best_card is not None
        # Should prioritize exact number match (4/102)
        assert best_card.number == "4"
        assert best_card.name == "Charizard"
    
    def test_find_best_match_rapidfuzz_accuracy(self, resolver):
        """Test rapidfuzz ranking accuracy."""
        card_info = CardInfo(name="Charizard", collector_number={'num': 4, 'den': 102})
        
        # Cards with different name similarities
        cards = [
            PokemonCard(
                id="1", name="Charizard", number="4", set_name="Set1", set_id="1", 
                rarity="Rare", images={}, set_release_date="1999-01-09"
            ),
            PokemonCard(
                id="2", name="Charizard EX", number="5", set_name="Set2", set_id="2", 
                rarity="Rare", images={}, set_release_date="2000-01-09"
            ),
            PokemonCard(
                id="3", name="Blastoise", number="6", set_name="Set3", set_id="3", 
                rarity="Rare", images={}, set_release_date="2001-01-09"
            )
        ]
        
        best_card = resolver._find_best_match(card_info, cards)
        
        # Should return the exact name match (Charizard)
        assert best_card.name == "Charizard"
        assert best_card.number == "4"
    
    def test_find_best_match_no_collector_number(self, resolver):
        """Test matching when no collector number is available."""
        card_info = CardInfo(name="Charizard", collector_number=None)
        
        cards = [
            PokemonCard(
                id="1", name="Charizard", number="4", set_name="Set1", set_id="1", 
                rarity="Rare", images={}, set_release_date="1999-01-09"
            ),
            PokemonCard(
                id="2", name="Charizard EX", number="5", set_name="Set2", set_id="2", 
                rarity="Rare", images={}, set_release_date="2000-01-09"
            )
        ]
        
        best_card = resolver._find_best_match(card_info, cards)
        
        # Should return based on name similarity only
        assert best_card.name == "Charizard"
    
    def test_find_best_match_low_confidence(self, resolver):
        """Test that low confidence matches are rejected."""
        card_info = CardInfo(name="CompletelyDifferent", collector_number={'num': 999, 'den': 999})
        
        cards = [
            PokemonCard(
                id="1", name="Charizard", number="4", set_name="Set1", set_id="1", 
                rarity="Rare", images={}, set_release_date="1999-01-09"
            )
        ]
        
        best_card = resolver._find_best_match(card_info, cards)
        
        # Should return None due to low confidence
        assert best_card is None
    
    def test_parse_card_data_valid(self, resolver):
        """Test parsing valid card data."""
        card_data = {
            "id": "base1-4",
            "name": "Charizard",
            "number": "4",
            "set": {
                "name": "Base Set",
                "id": "base1",
                "releaseDate": "1999-01-09"
            },
            "rarity": "Holo Rare",
            "images": {"small": "url1", "large": "url2"},
            "tcgplayer": {"prices": {"normal": {"market": 100.0}}},
            "cardmarket": {"prices": {"averageSellPrice": 50.0}}
        }
        
        card = resolver._parse_card_data(card_data)
        
        assert card is not None
        assert card.id == "base1-4"
        assert card.name == "Charizard"
        assert card.number == "4"
        assert card.set_name == "Base Set"
        assert card.set_id == "base1"
        assert card.rarity == "Holo Rare"
        assert card.set_release_date == "1999-01-09"
        assert card.tcgplayer is not None
        assert card.cardmarket is not None
    
    def test_parse_card_data_invalid(self, resolver):
        """Test parsing invalid card data."""
        # Missing required fields
        invalid_data = {"name": "Charizard"}  # Missing id
        
        card = resolver._parse_card_data(invalid_data)
        assert card is None
        
        # Empty data
        card = resolver._parse_card_data({})
        assert card is None
        
        # None data
        card = resolver._parse_card_data(None)
        assert card is None
    
    @pytest.mark.asyncio
    async def test_search_cards_success(self, resolver):
        """Test successful card search."""
        with patch.object(resolver, '_request_with_backoff') as mock_request:
            mock_request.return_value = {
                "data": [
                    {"id": "1", "name": "Charizard", "number": "4", "set": {"name": "Set1", "id": "1"}, "rarity": "Rare", "images": {}}
                ]
            }
            
            cards = await resolver.search_cards("Charizard")
            
            assert len(cards) == 1
            assert cards[0].name == "Charizard"
            assert cards[0].number == "4"
    
    @pytest.mark.asyncio
    async def test_search_cards_no_results(self, resolver):
        """Test card search with no results."""
        with patch.object(resolver, '_request_with_backoff') as mock_request:
            mock_request.return_value = {"data": []}
            
            cards = await resolver.search_cards("NonexistentCard")
            
            assert len(cards) == 0
    
    @pytest.mark.asyncio
    async def test_search_cards_api_error(self, resolver):
        """Test card search with API error."""
        with patch.object(resolver, '_request_with_backoff') as mock_request:
            mock_request.return_value = None  # API error
            
            cards = await resolver.search_cards("Charizard")
            
            assert len(cards) == 0
    
    @pytest.mark.asyncio
    async def test_resolve_card_with_collector_number(self, resolver):
        """Test card resolution with collector number."""
        card_info = CardInfo(name="Charizard", collector_number={'num': 4, 'den': 102})
        
        with patch.object(resolver, 'search_cards') as mock_search:
            mock_search.return_value = [
                PokemonCard(
                    id="1", name="Charizard", number="4", set_name="Set1", set_id="1", 
                    rarity="Rare", images={}, set_release_date="1999-01-09"
                )
            ]
            
            result = await resolver.resolve_card(card_info)
            
            assert result is not None
            assert result.name == "Charizard"
            assert result.number == "4"
    
    @pytest.mark.asyncio
    async def test_resolve_card_name_only(self, resolver):
        """Test card resolution with name only."""
        card_info = CardInfo(name="Charizard", collector_number=None)
        
        with patch.object(resolver, 'search_cards') as mock_search:
            mock_search.return_value = [
                PokemonCard(
                    id="1", name="Charizard", number="4", set_name="Set1", set_id="1", 
                    rarity="Rare", images={}, set_release_date="1999-01-09"
                )
            ]
            
            result = await resolver.resolve_card(card_info)
            
            assert result is not None
            assert result.name == "Charizard"
    
    @pytest.mark.asyncio
    async def test_resolve_card_no_match(self, resolver):
        """Test card resolution with no match."""
        card_info = CardInfo(name="NonexistentCard", collector_number={'num': 999, 'den': 999})
        
        with patch.object(resolver, 'search_cards') as mock_search:
            mock_search.return_value = []
            
            result = await resolver.resolve_card(card_info)
            
            assert result is None


if __name__ == "__main__":
    pytest.main([__file__])