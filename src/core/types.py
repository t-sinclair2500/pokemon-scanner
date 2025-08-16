from dataclasses import dataclass
from typing import Optional, List, Dict, Any

@dataclass
class MatchResult:
    card_id: str
    distance: float
    inliers: int
    confidence: float

@dataclass
class ResolvedCard:
    card_id: str
    name: str
    number: str
    set_name: str
    set_id: str
    rarity: Optional[str]
    images: Dict[str, str]  # small/large
    raw_tcgplayer: Optional[Dict[str, Any]]
    raw_cardmarket: Optional[Dict[str, Any]]
    set_release_date: Optional[str] = None
    
    @property
    def id(self) -> str:
        """Backward compatibility property for card_id."""
        return self.card_id
    
    @property
    def tcgplayer(self) -> Optional[Dict[str, Any]]:
        """Backward compatibility property for raw_tcgplayer."""
        return self.raw_tcgplayer
    
    @property
    def cardmarket(self) -> Optional[Dict[str, Any]]:
        """Backward compatibility property for raw_cardmarket."""
        return self.raw_cardmarket

@dataclass
class PriceData:
    tcgplayer_market_usd: Optional[float]
    cardmarket_trend_eur: Optional[float]
    cardmarket_avg30_eur: Optional[float]
    pricing_updatedAt_tcgplayer: str
    pricing_updatedAt_cardmarket: str
    price_sources: List[str]

@dataclass
class CardRow:
    timestamp_iso: str
    card: ResolvedCard
    price: PriceData
    source_image_path: str
