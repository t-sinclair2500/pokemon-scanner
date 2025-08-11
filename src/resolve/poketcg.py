"""Pokemon TCG API integration for card resolution."""

import aiohttp
import asyncio
import time
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from rapidfuzz import fuzz

from ..utils.log import get_logger
from ..utils.config import settings
from ..ocr.extract import CardInfo


@dataclass
class PokemonCard:
    """Pokemon card data."""
    id: str
    name: str
    number: str
    set_name: str
    set_id: str
    rarity: str
    images: Dict[str, str]
    tcgplayer: Optional[Dict[str, Any]] = None
    cardmarket: Optional[Dict[str, Any]] = None


class PokemonTCGResolver:
    """Resolves Pokemon cards using pokemontcg.io API."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.base_url = "https://api.pokemontcg.io/v2"
        self.session: Optional[aiohttp.ClientSession] = None
        self.last_request_time = 0
        self.min_request_interval = 0.2  # 5 QPS limit
    
    async def _ensure_session(self):
        """Ensure aiohttp session exists."""
        if self.session is None:
            headers = {"User-Agent": "Pokemon-Scanner/1.0"}
            if settings.POKEMON_TCG_API_KEY:
                headers["X-Api-Key"] = settings.POKEMON_TCG_API_KEY
            
            self.session = aiohttp.ClientSession(headers=headers)
    
    async def _rate_limit(self):
        """Apply rate limiting with 5 QPS."""
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()
    
    async def _request_with_backoff(self, url: str, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Make request with exponential backoff for 429/5xx errors."""
        await self._ensure_session()
        
        backoff_delays = [0.2, 1.0, 3.0]  # 200ms, 1s, 3s
        
        for attempt, delay in enumerate(backoff_delays):
            if attempt > 0:
                self.logger.info(f"Retrying request after {delay}s", attempt=attempt)
                await asyncio.sleep(delay)
            
            await self._rate_limit()
            
            try:
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:
                        self.logger.warning("Rate limited, backing off")
                        continue
                    elif response.status >= 500:
                        self.logger.warning(f"Server error {response.status}, backing off")
                        continue
                    else:
                        self.logger.error(f"Request failed with status {response.status}")
                        return None
            except Exception as e:
                self.logger.error(f"Request exception on attempt {attempt + 1}", error=str(e))
                if attempt == len(backoff_delays) - 1:
                    raise
        
        return None
    
    async def search_cards(self, query: str, limit: int = 20) -> List[PokemonCard]:
        """Search for cards using text query."""
        try:
            url = f"{self.base_url}/cards"
            params = {"q": query, "pageSize": min(limit, 250)}
            
            data = await self._request_with_backoff(url, params)
            if not data or "data" not in data:
                return []
            
            cards = []
            for card_data in data["data"]:
                card = self._parse_card_data(card_data)
                if card:
                    cards.append(card)
            
            return cards
            
        except Exception as e:
            self.logger.error("Error searching cards", query=query, error=str(e))
            return []
    
    async def resolve_card(self, card_info: CardInfo) -> Optional[PokemonCard]:
        """Resolve card from OCR info using pokemontcg.io."""
        try:
            # Build search queries in order of specificity
            queries = []
            
            # If collector number present, search by number first
            if card_info.collector_number:
                number_part = card_info.collector_number.split('/')[0]
                queries.append(f"number:{number_part}")
                
                # Add name if available for better matching
                if card_info.name:
                    queries.append(f"number:{number_part} name:{card_info.name}")
            
            # If name present, search by name
            if card_info.name:
                queries.append(f'name:"{card_info.name}"')
            
            # Try each query
            for query in queries:
                cards = await self.search_cards(query, limit=50)
                if not cards:
                    continue
                
                # Find best match using fuzzy matching
                best_card = self._find_best_match(card_info, cards)
                if best_card:
                    return best_card
            
            return None
            
        except Exception as e:
            self.logger.error("Error resolving card", error=str(e))
            return None
    
    def _find_best_match(self, card_info: CardInfo, candidates: List[PokemonCard]) -> Optional[PokemonCard]:
        """Find best matching card using fuzzy matching."""
        if not candidates:
            return None
        
        best_card = None
        best_score = 0
        
        for card in candidates:
            score = 0
            max_score = 0
            
            # Name matching (most important)
            if card_info.name and card.name:
                name_score = fuzz.ratio(card_info.name.lower(), card.name.lower())
                score += name_score * 0.6
                max_score += 100 * 0.6
            
            # Collector number matching
            if card_info.collector_number and card.number:
                number_part = card_info.collector_number.split('/')[0]
                if number_part == card.number:
                    score += 100 * 0.4
                max_score += 100 * 0.4
            
            # Normalize score
            if max_score > 0:
                normalized_score = (score / max_score) * 100
                if normalized_score > best_score:
                    best_score = normalized_score
                    best_card = card
        
        # Return only if confidence is reasonable
        return best_card if best_score > 60 else None
    
    def _parse_card_data(self, data: Dict[str, Any]) -> Optional[PokemonCard]:
        """Parse API card data into PokemonCard."""
        if not data:
            return None
        
        try:
            # Ensure we have at least ID and name
            if not data.get("id") or not data.get("name"):
                return None
            
            return PokemonCard(
                id=data.get("id", ""),
                name=data.get("name", ""),
                number=data.get("number", ""),
                set_name=data.get("set", {}).get("name", ""),
                set_id=data.get("set", {}).get("id", ""),
                rarity=data.get("rarity", ""),
                images=data.get("images", {}),
                tcgplayer=data.get("tcgplayer"),
                cardmarket=data.get("cardmarket")
            )
        except Exception as e:
            self.logger.error("Error parsing card data", error=str(e))
            return None
    
    # Sync wrappers
    def search_cards_sync(self, query: str, limit: int = 20) -> List[PokemonCard]:
        """Synchronous wrapper for search_cards."""
        return asyncio.run(self.search_cards(query, limit))
    
    def resolve_card_sync(self, card_info: CardInfo) -> Optional[PokemonCard]:
        """Synchronous wrapper for resolve_card.""" 
        return asyncio.run(self.resolve_card(card_info))
    
    async def close(self):
        """Close the session."""
        if self.session:
            await self.session.close()
            self.session = None


# Global singleton
pokemon_resolver = PokemonTCGResolver()