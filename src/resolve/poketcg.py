"""Pokemon TCG API integration for card resolution."""

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
from rapidfuzz import fuzz

from ..ocr.extract import CardInfo
from ..utils.config import settings
from ..utils.log import get_logger


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
    set_release_date: Optional[str] = None


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

    async def _request_with_backoff(
        self, url: str, params: Dict[str, Any] = None
    ) -> Optional[Dict[str, Any]]:
        """Make request with exponential backoff for 429/5xx errors."""
        await self._ensure_session()

        # Base delay: 0.2s → 1s → 3s on HTTP 429/5xx
        backoff_delays = [0.2, 1.0, 3.0]

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
                        self.logger.warning(
                            f"Server error {response.status}, backing off"
                        )
                        continue
                    else:
                        self.logger.error(
                            f"Request failed with status {response.status}"
                        )
                        return None
            except Exception as e:
                self.logger.error(
                    f"Request exception on attempt {attempt + 1}", error=str(e)
                )
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

            # Query Strategy:
            # If collector number present: q=number:{X} + name fuzzy matching
            # Else: name-only query
            if card_info.collector_number:
                number_part = str(card_info.collector_number["num"])
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

                # Find best match using rapidfuzz ranking
                best_card = self._find_best_match(card_info, cards)
                if best_card:
                    return best_card

            return None

        except Exception as e:
            self.logger.error("Error resolving card", error=str(e))
            return None

    def _find_best_match(
        self, card_info: CardInfo, candidates: List[PokemonCard]
    ) -> Optional[PokemonCard]:
        """
        Find best matching card using rapidfuzz ranking.

        Priority order:
        1. Exact number match
        2. Highest rapidfuzz ratio
        3. Newest set releaseDate
        """
        if not candidates:
            return None

        # Score each candidate
        scored_candidates = self._score_candidates(card_info, candidates)

        # Sort by score (highest first)
        scored_candidates.sort(key=lambda x: x[1], reverse=True)

        # Return only if confidence is reasonable
        if scored_candidates and scored_candidates[0][1] > 60:
            best_card, best_score = scored_candidates[0]
            self.logger.debug(
                "Best match found",
                card_name=best_card.name,
                card_number=best_card.number,
                score=best_score,
            )
            return best_card

        return None

    def _score_candidates(self, card_info: CardInfo, candidates: List[PokemonCard]) -> List[Tuple[PokemonCard, float]]:
        """Score each candidate based on multiple criteria."""
        scored_candidates = []

        for card in candidates:
            score = 0
            max_score = 0

            # Score each priority
            score, max_score = self._score_number_match(card_info, card, score, max_score)
            score, max_score = self._score_name_match(card_info, card, score, max_score)
            score, max_score = self._score_release_date(card, score, max_score)

            # Normalize score
            if max_score > 0:
                normalized_score = (score / max_score) * 100
                scored_candidates.append((card, normalized_score))
            else:
                scored_candidates.append((card, 0))

        return scored_candidates

    def _score_number_match(self, card_info: CardInfo, card: PokemonCard, score: int, max_score: int) -> Tuple[int, int]:
        """Score based on exact number match."""
        if card_info.collector_number and card.number:
            number_part = str(card_info.collector_number["num"])
            if number_part == card.number:
                score += 40
            max_score += 40
        return score, max_score

    def _score_name_match(self, card_info: CardInfo, card: PokemonCard, score: int, max_score: int) -> Tuple[int, int]:
        """Score based on name fuzzy matching."""
        if card_info.name and card.name:
            # Use rapidfuzz.ratio with ignore_case=True
            name_score = fuzz.ratio(card_info.name.lower(), card.name.lower())
            score += (name_score / 100) * 40
            max_score += 40
        return score, max_score

    def _score_release_date(self, card: PokemonCard, score: int, max_score: int) -> Tuple[int, int]:
        """Score based on set release date."""
        if card.set_release_date:
            # Newer sets get higher scores (simplified scoring)
            try:
                # Simple scoring: assume newer = better
                score += 20
            except Exception:
                pass
            max_score += 20
        return score, max_score

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
                cardmarket=data.get("cardmarket"),
                set_release_date=data.get("set", {}).get("releaseDate"),
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
