"""Tests for CLI fallback logic when visual confidence is low."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np

from src.cli import _try_resolver_fallback
from src.resolve.poketcg import PokemonTCGResolver
from src.core.types import ResolvedCard


@pytest.fixture
def mock_resolver():
    """Mock resolver for testing."""
    resolver = MagicMock(spec=PokemonTCGResolver)
    resolver.api_key = "test-api-key"
    return resolver


@pytest.fixture
def sample_collector_number():
    """Sample collector number dict."""
    return {"num": 4, "den": 102}


@pytest.fixture
def sample_name():
    """Sample card name."""
    return "Charizard"


@pytest.fixture
def sample_resolved_card():
    """Sample resolved card for testing."""
    return ResolvedCard(
        card_id="base1-4",
        name="Charizard",
        number="4/102",
        set_name="Base Set",
        set_id="base1",
        rarity="Holo Rare",
        images={"small": "test.jpg"},
        raw_tcgplayer={"prices": {"normal": {"market": 100.0}}},
        raw_cardmarket={"prices": {"priceGuide": {"LOW": 90.0}}}
    )


class TestCLIFallback:
    """Test CLI fallback logic."""

    @pytest.mark.asyncio
    async def test_resolver_fallback_success(self, mock_resolver, sample_collector_number, sample_name, sample_resolved_card):
        """Test successful resolver fallback."""
        with patch("src.resolve.poketcg.search_by_number_name", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = sample_resolved_card
            
            result = await _try_resolver_fallback(
                sample_collector_number, 
                sample_name, 
                mock_resolver
            )
            
            # Verify search was called with correct parameters
            mock_search.assert_called_once_with(
                number="4/102",
                name="Charizard",
                api_key="test-api-key"
            )
            
            # Verify result is converted to dict format
            assert result is not None
            assert result["id"] == "base1-4"
            assert result["name"] == "Charizard"
            assert result["number"] == "4/102"
            assert result["set"]["name"] == "Base Set"
            assert result["set"]["id"] == "base1"
            assert result["rarity"] == "Holo Rare"
            assert result["images"] == {"small": "test.jpg"}
            assert result["tcgplayer"] == {"prices": {"normal": {"market": 100.0}}}
            assert result["cardmarket"] == {"prices": {"priceGuide": {"LOW": 90.0}}}

    @pytest.mark.asyncio
    async def test_resolver_fallback_no_result(self, mock_resolver, sample_collector_number, sample_name):
        """Test resolver fallback when no card is found."""
        with patch("src.resolve.poketcg.search_by_number_name", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = None
            
            result = await _try_resolver_fallback(
                sample_collector_number, 
                sample_name, 
                mock_resolver
            )
            
            assert result is None

    @pytest.mark.asyncio
    async def test_resolver_fallback_exception(self, mock_resolver, sample_collector_number, sample_name):
        """Test resolver fallback handles exceptions gracefully."""
        with patch("src.resolve.poketcg.search_by_number_name", new_callable=AsyncMock) as mock_search:
            mock_search.side_effect = Exception("API error")
            
            result = await _try_resolver_fallback(
                sample_collector_number, 
                sample_name, 
                mock_resolver
            )
            
            assert result is None

    def test_collector_number_formatting(self, sample_collector_number):
        """Test collector number is formatted correctly."""
        number_str = f"{sample_collector_number['num']}/{sample_collector_number['den']}"
        assert number_str == "4/102"
