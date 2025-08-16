"""Tests for resolver backoff functionality."""

import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from src.resolve.poketcg import _fetch_json, get_card, search_by_number_name
from src.core.constants import BACKOFF_S


class TestResolverBackoff:
    """Test resolver backoff and retry functionality."""

    @pytest.mark.asyncio
    async def test_backoff_constants(self):
        """Test that backoff constants are properly defined."""
        assert len(BACKOFF_S) == 3
        assert BACKOFF_S == [0.2, 1.0, 3.0]
        assert all(isinstance(delay, (int, float)) for delay in BACKOFF_S)
        assert all(delay > 0 for delay in BACKOFF_S)

    @pytest.mark.asyncio
    async def test_fetch_json_backoff_sequence_429_to_200(self):
        """Test that _fetch_json properly handles 429 → 200 sequence with backoff."""
        # Create a mock response that simulates the behavior we need
        mock_response_429 = MagicMock()
        mock_response_429.status = 429
        
        mock_response_200 = MagicMock()
        mock_response_200.status = 200
        mock_response_200.raise_for_status.return_value = None
        mock_response_200.json = AsyncMock(return_value={"data": {"test": "success"}})
        
        # Create a mock session that can be used as an async context manager
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        # Mock the get method to return responses that can be used as async context managers
        mock_get_429 = MagicMock()
        mock_get_429.__aenter__ = AsyncMock(return_value=mock_response_429)
        mock_get_429.__aexit__ = AsyncMock(return_value=None)
        
        mock_get_200 = MagicMock()
        mock_get_200.__aenter__ = AsyncMock(return_value=mock_response_200)
        mock_get_200.__aexit__ = AsyncMock(return_value=None)
        
        # Set up the side effect to return 429 first, then 200
        mock_session.get.side_effect = [
            mock_get_429,
            mock_get_200
        ]
        
        # Mock the entire aiohttp.ClientSession class
        with patch('src.resolve.poketcg.aiohttp.ClientSession', return_value=mock_session):
            # Mock asyncio.sleep to avoid actual delays in tests
            with patch('src.resolve.poketcg.asyncio.sleep') as mock_sleep:
                result = await _fetch_json("https://test.com", None, None)
                
                # Should have made 2 requests
                assert mock_session.get.call_count == 2
                
                # Should have slept once with the first backoff delay
                assert mock_sleep.call_count == 1
                mock_sleep.assert_called_with(BACKOFF_S[0])
                
                # Result should be the successful response
                assert result == {"data": {"test": "success"}}

    @pytest.mark.asyncio
    async def test_fetch_json_backoff_sequence_500_to_200(self):
        """Test that _fetch_json properly handles 500 → 200 sequence with backoff."""
        mock_response_500 = MagicMock()
        mock_response_500.status = 500
        
        mock_response_200 = MagicMock()
        mock_response_200.status = 200
        mock_response_200.raise_for_status.return_value = None
        mock_response_200.json = AsyncMock(return_value={"data": {"test": "success"}})
        
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        mock_get_500 = MagicMock()
        mock_get_500.__aenter__ = AsyncMock(return_value=mock_response_500)
        mock_get_500.__aexit__ = AsyncMock(return_value=None)
        
        mock_get_200 = MagicMock()
        mock_get_200.__aenter__ = AsyncMock(return_value=mock_response_200)
        mock_get_200.__aexit__ = AsyncMock(return_value=None)
        
        mock_session.get.side_effect = [
            mock_get_500,
            mock_get_200
        ]
        
        with patch('src.resolve.poketcg.aiohttp.ClientSession', return_value=mock_session):
            with patch('src.resolve.poketcg.asyncio.sleep') as mock_sleep:
                result = await _fetch_json("https://test.com", None, None)
                
                assert mock_session.get.call_count == 2
                assert mock_sleep.call_count == 1
                assert result == {"data": {"test": "success"}}

    @pytest.mark.asyncio
    async def test_fetch_json_max_retries_exceeded(self):
        """Test that _fetch_json gives up after max retries."""
        mock_response_429 = MagicMock()
        mock_response_429.status = 429
        # Need to mock json method as AsyncMock since it's awaited
        mock_response_429.json = AsyncMock(return_value={"data": {"test": "429"}})
        # Mock raise_for_status to raise an exception when called
        mock_response_429.raise_for_status.side_effect = Exception("429 Too Many Requests")
        
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        mock_get_429 = MagicMock()
        mock_get_429.__aenter__ = AsyncMock(return_value=mock_response_429)
        mock_get_429.__aexit__ = AsyncMock(return_value=None)
        
        # Always return 429
        mock_session.get.return_value = mock_get_429
        
        with patch('src.resolve.poketcg.aiohttp.ClientSession', return_value=mock_session):
            with patch('src.resolve.poketcg.asyncio.sleep') as mock_sleep:
                # Should raise an exception after max retries
                with pytest.raises(Exception, match="429 Too Many Requests"):
                    await _fetch_json("https://test.com", None, None)
                
                # Should have made len(BACKOFF_S) + 1 requests (initial + retries)
                expected_calls = len(BACKOFF_S) + 1
                assert mock_session.get.call_count == expected_calls
                
                # Should have slept for each backoff delay
                assert mock_sleep.call_count == len(BACKOFF_S)

    @pytest.mark.asyncio
    async def test_fetch_json_immediate_success(self):
        """Test that _fetch_json succeeds immediately on first try."""
        mock_response_200 = MagicMock()
        mock_response_200.status = 200
        mock_response_200.raise_for_status.return_value = None
        mock_response_200.json = AsyncMock(return_value={"data": {"test": "immediate"}})
        
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        mock_get_200 = MagicMock()
        mock_get_200.__aenter__ = AsyncMock(return_value=mock_response_200)
        mock_get_200.__aexit__ = AsyncMock(return_value=None)
        
        mock_session.get.return_value = mock_get_200
        
        with patch('src.resolve.poketcg.aiohttp.ClientSession', return_value=mock_session):
            with patch('src.resolve.poketcg.asyncio.sleep') as mock_sleep:
                result = await _fetch_json("https://test.com", None, None)
                
                # Should have made only 1 request
                assert mock_session.get.call_count == 1
                
                # Should not have slept
                assert mock_sleep.call_count == 0
                
                # Result should be the successful response
                assert result == {"data": {"test": "immediate"}}

    @pytest.mark.asyncio
    async def test_fetch_json_backoff_delays(self):
        """Test that _fetch_json uses correct backoff delays."""
        mock_response_429 = MagicMock()
        mock_response_429.status = 429
        
        mock_response_200 = MagicMock()
        mock_response_200.status = 200
        mock_response_200.raise_for_status.return_value = None
        mock_response_200.json = AsyncMock(return_value={"data": {"test": "delayed"}})
        
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        mock_get_429 = MagicMock()
        mock_get_429.__aenter__ = AsyncMock(return_value=mock_response_429)
        mock_get_429.__aexit__ = AsyncMock(return_value=None)
        
        mock_get_200 = MagicMock()
        mock_get_200.__aenter__ = AsyncMock(return_value=mock_response_200)
        mock_get_200.__aexit__ = AsyncMock(return_value=None)
        
        # First call returns 429, second call returns 200
        mock_session.get.side_effect = [
            mock_get_429,
            mock_get_200
        ]
        
        # Mock asyncio.sleep to track calls
        with patch('src.resolve.poketcg.aiohttp.ClientSession', return_value=mock_session):
            with patch('src.resolve.poketcg.asyncio.sleep') as mock_sleep:
                result = await _fetch_json("https://test.com", None, None)
                
                # Should have slept once with the first backoff delay
                assert mock_sleep.call_count == 1
                mock_sleep.assert_called_with(BACKOFF_S[0])  # First backoff delay
                
                # Result should be the successful response
                assert result == {"data": {"test": "delayed"}}

    @pytest.mark.asyncio
    async def test_get_card_with_backoff(self):
        """Test that get_card function works with backoff functionality."""
        # Mock the _fetch_json function to simulate backoff
        mock_response = {
            "data": {
                "id": "base1-4",
                "name": "Charizard",
                "number": "4",
                "set": {"name": "Base Set", "id": "base1"},
                "rarity": "Holo Rare",
                "images": {"small": "url1", "large": "url2"},
                "tcgplayer": {"prices": {"normal": {"market": 100.00}}},
                "cardmarket": {"prices": {"trendPrice": 80.00}}
            }
        }
        
        with patch('src.resolve.poketcg._fetch_json', return_value=mock_response):
            result = await get_card("base1-4", "test-api-key")
            
            assert result is not None
            assert result.card_id == "base1-4"
            assert result.name == "Charizard"
            assert result.number == "4"

    @pytest.mark.asyncio
    async def test_search_by_number_name_with_backoff(self):
        """Test that search_by_number_name function works with backoff functionality."""
        # Mock the _fetch_json function to simulate backoff
        mock_response = {
            "data": [
                {
                    "id": "base1-4",
                    "name": "Charizard",
                    "number": "4",
                    "set": {"name": "Base Set", "id": "base1"},
                    "rarity": "Holo Rare",
                    "images": {"small": "url1", "large": "url2"},
                    "tcgplayer": {"prices": {"normal": {"market": 100.00}}},
                }
            ]
        }
        
        with patch('src.resolve.poketcg._fetch_json', return_value=mock_response):
            result = await search_by_number_name("4", "Charizard", "test-api-key")
            
            assert result is not None
            assert result.card_id == "base1-4"
            assert result.name == "Charizard"
            assert result.number == "4"


if __name__ == "__main__":
    pytest.main([__file__])
