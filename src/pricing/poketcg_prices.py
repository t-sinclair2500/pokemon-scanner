from typing import Optional
from src.core.types import PriceData

def _first_market(tcg: dict|None) -> Optional[float]:
    if not tcg: 
        return None
    prices = tcg.get("prices") or {}
    for key in ("normal", "holofoil", "reverseHolofoil"):
        v = prices.get(key) or {}
        m = v.get("market")
        if m is not None: 
            return float(m)
    return None

def map_price_blocks(card_json: dict) -> PriceData:
    tcg = card_json.get("tcgplayer")
    ckm = card_json.get("cardmarket") or {}
    return PriceData(
        tcgplayer_market_usd=_first_market(tcg),
        cardmarket_trend_eur=(ckm.get("prices") or {}).get("trendPrice"),
        cardmarket_avg30_eur=(ckm.get("prices") or {}).get("avg30"),
        pricing_updatedAt_tcgplayer=(tcg or {}).get("updatedAt", ""),
        pricing_updatedAt_cardmarket=ckm.get("updatedAt", ""),
        price_sources=["pokemontcg.io"],
    )

class PokemonPricer:
    """Pricing extractor for Pokemon cards."""
    
    def extract_prices_from_card(self, card_json: dict) -> PriceData:
        """Extract pricing data from a card JSON object."""
        return map_price_blocks(card_json)

# Global instance
pokemon_pricer = PokemonPricer()
