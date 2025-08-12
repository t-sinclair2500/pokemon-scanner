"""Pricing extraction from Pokemon TCG API data."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict

from ..resolve.poketcg import PokemonCard
from ..utils.log import get_logger


@dataclass
class PriceData:
    """Complete pricing data for a card with flattened structure."""

    tcgplayer_market_usd: str = ""
    cardmarket_trend_eur: str = ""
    cardmarket_avg30_eur: str = ""
    pricing_updatedAt_tcgplayer: str = ""
    pricing_updatedAt_cardmarket: str = ""
    price_sources: List[str] = None

    def __post_init__(self):
        if self.price_sources is None:
            self.price_sources = ["pokemontcg.io"]


class PokemonTCGPricer:
    """Extracts pricing from Pokemon TCG API card data."""

    def __init__(self):
        self.logger = get_logger(__name__)

    def _safe_float_to_string(self, value) -> str:
        """Safely convert a value to a string, handling None and invalid data."""
        if value is None:
            return ""

        try:
            # Convert to float first to validate it's numeric
            float_val = float(value)
            # Always format with 2 decimal places to match test expectations
            return f"{float_val:.2f}"
        except (ValueError, TypeError):
            return ""

    def extract_prices_from_card(self, card: PokemonCard) -> PriceData:
        """Extract pricing data from Pokemon card with flattened structure."""
        try:
            price_data = PriceData()

            # Extract TCGPlayer pricing and updatedAt
            self._extract_tcgplayer_prices(card, price_data)

            # Extract CardMarket pricing and updatedAt
            self._extract_cardmarket_prices(card, price_data)

            self.logger.debug(
                "Extracted pricing data",
                card_id=card.id,
                tcgplayer_market=price_data.tcgplayer_market_usd,
                cardmarket_trend=price_data.cardmarket_trend_eur,
                cardmarket_avg30=price_data.cardmarket_avg30_eur,
            )

            return price_data

        except Exception as e:
            self.logger.error("Error extracting prices", card_id=card.id, error=str(e))
            # Return empty PriceData on error
            return PriceData()

    def _extract_tcgplayer_prices(self, card: PokemonCard, price_data: PriceData) -> None:
        """Extract TCGPlayer pricing data."""
        if not card.tcgplayer:
            return

        # Extract updatedAt regardless of whether prices exist
        if "updatedAt" in card.tcgplayer:
            price_data.pricing_updatedAt_tcgplayer = str(
                card.tcgplayer["updatedAt"]
            )

        # Extract pricing if available
        if "prices" in card.tcgplayer:
            tcg_prices = card.tcgplayer["prices"]
            self._extract_tcgplayer_market_price(tcg_prices, price_data)

    def _extract_tcgplayer_market_price(self, tcg_prices: Dict, price_data: PriceData) -> None:
        """Extract market price from TCGPlayer prices."""
        # Try normal -> holofoil -> reverseHolofoil for market price
        for condition in ["normal", "holofoil", "reverseHolofoil"]:
            if (
                condition in tcg_prices
                and "market" in tcg_prices[condition]
            ):
                market_price = tcg_prices[condition]["market"]
                if market_price is not None:
                    price_data.tcgplayer_market_usd = (
                        self._safe_float_to_string(market_price)
                    )
                    break

    def _extract_cardmarket_prices(self, card: PokemonCard, price_data: PriceData) -> None:
        """Extract CardMarket pricing data."""
        if not card.cardmarket:
            return

        # Extract updatedAt regardless of whether prices exist
        if "updatedAt" in card.cardmarket:
            price_data.pricing_updatedAt_cardmarket = str(
                card.cardmarket["updatedAt"]
            )

        # Extract pricing if available
        if "prices" in card.cardmarket:
            cm_prices = card.cardmarket["prices"]
            self._extract_cardmarket_price_fields(cm_prices, price_data)

    def _extract_cardmarket_price_fields(self, cm_prices: Dict, price_data: PriceData) -> None:
        """Extract specific price fields from CardMarket prices."""
        # Extract trend price
        if "trendPrice" in cm_prices:
            price_data.cardmarket_trend_eur = self._safe_float_to_string(
                cm_prices["trendPrice"]
            )

        # Extract avg30 price
        if "avg30" in cm_prices:
            price_data.cardmarket_avg30_eur = self._safe_float_to_string(
                cm_prices["avg30"]
            )


# Global singleton
pokemon_pricer = PokemonTCGPricer()
