"""Pokemon TCG API integration for card resolution."""

import aiohttp
import asyncio
from rapidfuzz import fuzz
from typing import Optional, List, Dict, Any
from src.utils.config import Settings
from src.core.types import ResolvedCard
from src.core.constants import BACKOFF_S

BASE = "https://api.pokemontcg.io/v2/cards"

async def _fetch_json(url: str, params: dict|None, headers: dict|None) -> dict:
    for i, delay in enumerate([0.0, *BACKOFF_S], start=0):
        if delay: 
            await asyncio.sleep(delay)
        async with aiohttp.ClientSession(headers=headers) as s:
            async with s.get(url, params=params) as r:
                if r.status in (429, 500, 502, 503, 504) and i < len(BACKOFF_S):
                    continue
                r.raise_for_status()
                return await r.json()
    raise RuntimeError("unreachable")

def _to_resolved(card: dict) -> ResolvedCard:
    return ResolvedCard(
        card_id=card["id"], 
        name=card["name"], 
        number=card.get("number", ""),
        set_name=card["set"]["name"], 
        set_id=card["set"]["id"], 
        rarity=card.get("rarity"),
        images=card["images"], 
        raw_tcgplayer=card.get("tcgplayer"), 
        raw_cardmarket=card.get("cardmarket")
    )

async def get_card(card_id: str, api_key: Optional[str]) -> ResolvedCard | None:
    headers = {"X-Api-Key": api_key} if api_key else {}
    j = await _fetch_json(f"{BASE}/{card_id}", None, headers)
    data = j.get("data")
    return _to_resolved(data) if data else None

async def search_by_number_name(number: str|None, name: str|None, api_key: Optional[str]) -> ResolvedCard | None:
    q = []
    if number: 
        q.append(f'number:"{number}"')
    if name: 
        q.append(f'name:"{name}"')
    params = {"q": " ".join(q) if q else None, "pageSize": 50}
    headers = {"X-Api-Key": api_key} if api_key else {}
    j = await _fetch_json(BASE, params, headers)
    candidates = j.get("data", [])
    if not candidates: 
        return None
    pool = [c for c in candidates if not number or str(c.get("number", "")).strip() == str(number).strip()]
    pool = pool or candidates
    if name:
        pool.sort(key=lambda c: fuzz.ratio(name.lower(), c["name"].lower()), reverse=True)
    return _to_resolved(pool[0])

class PokemonTCGResolver:
    """Resolver for Pokemon TCG cards."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.base_url = "https://api.pokemontcg.io/v2"
        self.min_request_interval = 0.2
        self.session: Optional[aiohttp.ClientSession] = None
        self.last_request_time = 0.0
    
    async def _ensure_session(self) -> None:
        """Ensure aiohttp session exists."""
        if self.session is None or self.session.closed:
            headers = {"X-Api-Key": self.api_key} if self.api_key else {}
            self.session = aiohttp.ClientSession(headers=headers)
    
    async def _rate_limit(self) -> None:
        """Apply rate limiting between requests."""
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - time_since_last)
        
        self.last_request_time = asyncio.get_event_loop().time()
    
    async def _request_with_backoff(self, url: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request with exponential backoff for retryable errors."""
        await self._ensure_session()
        await self._rate_limit()
        
        for attempt, delay in enumerate([0.0, *BACKOFF_S]):
            if delay > 0:
                await asyncio.sleep(delay)
            
            try:
                async with self.session.get(url, params=params) as response:
                    if response.status in (429, 500, 502, 503, 504) and attempt < len(BACKOFF_S):
                        continue
                    response.raise_for_status()
                    return await response.json()
            except aiohttp.ClientResponseError as e:
                if e.status in (429, 500, 502, 503, 504) and attempt < len(BACKOFF_S):
                    continue
                raise
        
        raise RuntimeError("All retry attempts failed")
    
    def find_best_match(self, cards: List, card_info: Any) -> Optional[Any]:
        """Find the best matching card from a list of candidates."""
        if not cards:
            return None
        
        # Convert CardInfo to dict format if needed
        if hasattr(card_info, 'name') or hasattr(card_info, 'collector_number'):
            # It's a CardInfo object, convert to dict
            card_dict = {
                'name': getattr(card_info, 'name', None),
                'collector_number': getattr(card_info, 'collector_number', None)
            }
        else:
            card_dict = card_info
        
        # Priority 1: Exact number match
        if card_dict.get("collector_number"):
            number_str = f"{card_dict['collector_number']['num']}/{card_dict['collector_number']['den']}"
            # Handle both dict and ResolvedCard objects
            exact_matches = []
            for c in cards:
                if hasattr(c, 'number'):
                    # ResolvedCard object
                    if c.number == number_str:
                        exact_matches.append(c)
                elif isinstance(c, dict) and c.get("number") == number_str:
                    # Dict object
                    exact_matches.append(c)
            
            if exact_matches:
                # Among exact matches, prefer by name similarity
                if card_dict.get("name"):
                    exact_matches.sort(
                        key=lambda c: fuzz.ratio(card_dict["name"].lower(), 
                                               c.name if hasattr(c, 'name') else c.get("name", "").lower()),
                        reverse=True
                    )
                return exact_matches[0]
        
        # Priority 2: Name similarity ranking
        if card_dict.get("name"):
            # Sort by name similarity, handling both types
            def get_name(card):
                if hasattr(card, 'name'):
                    return card.name
                elif isinstance(card, dict):
                    return card.get("name", "")
                return ""
            
            cards.sort(
                key=lambda c: fuzz.ratio(card_dict["name"].lower(), get_name(c).lower()),
                reverse=True
            )
            return cards[0]
        
        # Priority 3: Return first card if no other criteria
        return cards[0] if cards else None
    
    def _find_best_match(self, card_info: Any, cards: List[ResolvedCard]) -> Optional[ResolvedCard]:
        """Find the best matching card using priority ranking."""
        if not cards:
            return None
        
        # Convert CardInfo to dict format if needed
        if hasattr(card_info, 'name') or hasattr(card_info, 'collector_number'):
            # It's a CardInfo object, convert to dict
            card_dict = {
                'name': getattr(card_info, 'name', None),
                'collector_number': getattr(card_info, 'collector_number', None)
            }
        else:
            card_dict = card_info
        
        # Priority 1: Exact number match
        if card_dict.get("collector_number"):
            number_str = f"{card_dict['collector_number']['num']}/{card_dict['collector_number']['den']}"
            exact_matches = [c for c in cards if c.number == number_str]
            if exact_matches:
                # Among exact matches, prefer by name similarity
                if card_dict.get("name"):
                    exact_matches.sort(
                        key=lambda c: fuzz.ratio(card_dict["name"].lower(), c.name.lower()),
                        reverse=True
                    )
                return exact_matches[0]
        
        # Priority 2: Name similarity ranking
        if card_dict.get("name"):
            cards.sort(
                key=lambda c: fuzz.ratio(card_dict["name"].lower(), c.name.lower()),
                reverse=True
            )
            return cards[0]
        
        # Priority 3: Return first card if no other criteria
        return cards[0] if cards else None
    
    def _parse_card_data(self, card_data: Dict[str, Any]) -> Optional[ResolvedCard]:
        """Parse raw card data into ResolvedCard."""
        try:
            # Validate required fields
            required_fields = ["id", "name", "set"]
            missing_fields = [field for field in required_fields if field not in card_data]
            if missing_fields:
                return None
            
            return ResolvedCard(
                card_id=card_data["id"],
                name=card_data["name"],
                number=card_data.get("number", ""),
                set_name=card_data["set"]["name"],
                set_id=card_data["set"]["id"],
                rarity=card_data.get("rarity"),
                images=card_data.get("images", {}),
                raw_tcgplayer=card_data.get("tcgplayer"),
                raw_cardmarket=card_data.get("cardmarket"),
                set_release_date=card_data["set"].get("releaseDate")
            )
        except (KeyError, TypeError, ValueError):
            return None
    
    async def search_cards(self, query: str, limit: int = 10) -> List[ResolvedCard]:
        """Search for cards using a query string."""
        try:
            url = f"{self.base_url}/cards"
            params = {"q": query, "pageSize": limit}
            
            response_data = await self._request_with_backoff(url, params)
            cards_data = response_data.get("data", [])
            
            # Convert to ResolvedCard objects
            cards = []
            for card_data in cards_data[:limit]:
                card = self._parse_card_data(card_data)
                if card:
                    cards.append(card)
            
            return cards
        except Exception as e:
            # Log error and return empty list
            return []
    
    async def resolve_card(self, card_info: Any) -> Optional[ResolvedCard]:
        """Resolve card information to a ResolvedCard."""
        try:
            # Convert CardInfo to dict format if needed
            if hasattr(card_info, 'name') or hasattr(card_info, 'collector_number'):
                # It's a CardInfo object, convert to dict
                card_dict = {
                    'name': getattr(card_info, 'name', None),
                    'collector_number': getattr(card_info, 'collector_number', None)
                }
            else:
                card_dict = card_info
            
            # Build search query
            query_parts = []
            if card_dict.get("collector_number"):
                number_str = f"{card_dict['collector_number']['num']}/{card_dict['collector_number']['den']}"
                query_parts.append(f'number:"{number_str}"')
            if card_dict.get("name"):
                query_parts.append(f'name:"{card_dict["name"]}"')
            
            if not query_parts:
                return None
            
            query = " ".join(query_parts)
            cards = await self.search_cards(query, limit=10)
            
            if not cards:
                return None
            
            # Find best match
            best_match = self._find_best_match(card_dict, cards)
            if not best_match:
                return None
            
            # Return the best match (already a ResolvedCard)
            return best_match
            
        except Exception as e:
            # Log error and return None
            return None
    
    async def close(self) -> None:
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
    
    def __del__(self):
        """Cleanup on deletion."""
        if self.session and not self.session.closed:
            # Note: This is not ideal but necessary for cleanup
            # In production, always call close() explicitly
            pass
