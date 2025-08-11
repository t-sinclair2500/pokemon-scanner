"""Pricing extraction from Pokemon TCG API data."""

from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime

from ..utils.log import get_logger
from ..resolve.poketcg import PokemonCard


@dataclass
class CardPrice:
    """Card pricing information."""
    tcgplayer_market_usd: Optional[float] = None
    cardmarket_trend_eur: Optional[float] = None  
    cardmarket_avg30_eur: Optional[float] = None
    pricing_updatedAt_tcgplayer: str = ""
    pricing_updatedAt_cardmarket: str = ""
    price_sources: List[str] = None
    
    def __post_init__(self):
        if self.price_sources is None:
            self.price_sources = ["pokemontcg.io"]


@dataclass
class PriceData:
    """Complete pricing data for a card."""
    card_id: str
    card_name: str
    prices: CardPrice


class PokemonTCGPricer:
    """Extracts pricing from Pokemon TCG API card data."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def extract_prices(self, card: PokemonCard) -> Optional[PriceData]:
        """Extract pricing data from Pokemon card."""
        try:
            prices = CardPrice()
            
            # Extract TCGPlayer prices
            if card.tcgplayer and "prices" in card.tcgplayer:
                tcg_prices = card.tcgplayer["prices"]
                
                # Try normal -> holofoil -> reverseHolofoil for market price
                for condition in ["normal", "holofoil", "reverseHolofoil"]:
                    if condition in tcg_prices and "market" in tcg_prices[condition]:
                        market_price = tcg_prices[condition]["market"]
                        if market_price is not None:
                            prices.tcgplayer_market_usd = float(market_price)
                            break
                
                # Extract updatedAt for TCGPlayer
                if "updatedAt" in card.tcgplayer:
                    prices.pricing_updatedAt_tcgplayer = card.tcgplayer["updatedAt"]
            
            # Extract CardMarket prices
            if card.cardmarket and "prices" in card.cardmarket:
                cm_prices = card.cardmarket["prices"]
                
                if "trendPrice" in cm_prices and cm_prices["trendPrice"] is not None:
                    prices.cardmarket_trend_eur = float(cm_prices["trendPrice"])
                
                # Try avg30 first, then fallback to averageSellPrice
                if "avg30" in cm_prices and cm_prices["avg30"] is not None:
                    prices.cardmarket_avg30_eur = float(cm_prices["avg30"])
                elif "averageSellPrice" in cm_prices and cm_prices["averageSellPrice"] is not None:
                    prices.cardmarket_avg30_eur = float(cm_prices["averageSellPrice"])
                
                # Extract updatedAt for CardMarket
                if "updatedAt" in card.cardmarket:
                    prices.pricing_updatedAt_cardmarket = card.cardmarket["updatedAt"]
            
            # Only return if we have at least one price
            if (prices.tcgplayer_market_usd is not None or 
                prices.cardmarket_trend_eur is not None or 
                prices.cardmarket_avg30_eur is not None):
                
                return PriceData(
                    card_id=card.id,
                    card_name=card.name,
                    prices=prices
                )
            
            return None
            
        except Exception as e:
            self.logger.error("Error extracting prices", card_id=card.id, error=str(e))
            return None


# Global singleton
pokemon_pricer = PokemonTCGPricer()