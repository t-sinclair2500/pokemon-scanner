"""SQLite cache for cards and scans."""

import sqlite3
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path

from ..utils.log import get_logger
from ..utils.config import settings, ensure_cache_dir
from ..resolve.poketcg import PokemonCard
from ..pricing.poketcg_prices import PriceData


class PokemonCardCache:
    """SQLite cache for Pokemon card data."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        ensure_cache_dir()
        self.db_path = Path(settings.CACHE_DB_PATH)
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database with required tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Cards table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS cards (
                        card_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        set_id TEXT,
                        set_name TEXT,
                        number TEXT,
                        rarity TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Prices table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS prices (
                        card_id TEXT PRIMARY KEY,
                        ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        tcgplayer_market_usd REAL,
                        cardmarket_trend_eur REAL,
                        cardmarket_avg30_eur REAL,
                        pricing_updatedAt_tcgplayer TEXT,
                        pricing_updatedAt_cardmarket TEXT,
                        sources_json TEXT,
                        FOREIGN KEY (card_id) REFERENCES cards (card_id)
                    )
                """)
                
                # Scans table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS scans (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        image_path TEXT,
                        ocr_json TEXT,
                        status TEXT DEFAULT 'NEW'
                    )
                """)
                
                conn.commit()
                
        except Exception as e:
            self.logger.error("Error initializing database", error=str(e))
            raise
    
    def cache_card(self, card: PokemonCard) -> bool:
        """Cache a Pokemon card."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO cards 
                    (card_id, name, set_id, set_name, number, rarity)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (card.id, card.name, card.set_id, card.set_name, card.number, card.rarity))
                conn.commit()
                return True
        except Exception as e:
            self.logger.error("Error caching card", card_id=card.id, error=str(e))
            return False
    
    def get_card(self, card_id: str) -> Optional[PokemonCard]:
        """Get cached card by ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM cards WHERE card_id = ?", (card_id,)
                )
                row = cursor.fetchone()
                
                if row:
                    return PokemonCard(
                        id=row["card_id"],
                        name=row["name"],
                        number=row["number"] or "",
                        set_name=row["set_name"] or "",
                        set_id=row["set_id"] or "",
                        rarity=row["rarity"] or "",
                        images={}
                    )
                return None
        except Exception as e:
            self.logger.error("Error getting card", card_id=card_id, error=str(e))
            return None
    
    def cache_prices(self, price_data: PriceData) -> bool:
        """Cache pricing data."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO prices 
                    (card_id, tcgplayer_market_usd, cardmarket_trend_eur, cardmarket_avg30_eur,
                     pricing_updatedAt_tcgplayer, pricing_updatedAt_cardmarket, sources_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    price_data.card_id,
                    price_data.prices.tcgplayer_market_usd,
                    price_data.prices.cardmarket_trend_eur,
                    price_data.prices.cardmarket_avg30_eur,
                    price_data.prices.pricing_updatedAt_tcgplayer,
                    price_data.prices.pricing_updatedAt_cardmarket,
                    json.dumps(price_data.prices.price_sources)
                ))
                conn.commit()
                return True
        except Exception as e:
            self.logger.error("Error caching prices", card_id=price_data.card_id, error=str(e))
            return False
    
    def get_prices(self, card_id: str) -> Optional[PriceData]:
        """Get cached pricing data if not expired."""
        try:
            cutoff = datetime.now() - timedelta(hours=settings.CACHE_EXPIRE_HOURS)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT p.*, c.name 
                    FROM prices p 
                    JOIN cards c ON p.card_id = c.card_id 
                    WHERE p.card_id = ? AND p.ts > ?
                """, (card_id, cutoff.isoformat()))
                
                row = cursor.fetchone()
                if row:
                    from ..pricing.poketcg_prices import CardPrice
                    
                    sources = json.loads(row["sources_json"]) if row["sources_json"] else ["pokemontcg.io"]
                    
                    prices = CardPrice(
                        tcgplayer_market_usd=row["tcgplayer_market_usd"],
                        cardmarket_trend_eur=row["cardmarket_trend_eur"],
                        cardmarket_avg30_eur=row["cardmarket_avg30_eur"],
                        pricing_updatedAt_tcgplayer=row["pricing_updatedAt_tcgplayer"] or "",
                        pricing_updatedAt_cardmarket=row["pricing_updatedAt_cardmarket"] or "",
                        price_sources=sources
                    )
                    
                    return PriceData(
                        card_id=card_id,
                        card_name=row["name"],
                        prices=prices
                    )
                
                return None
        except Exception as e:
            self.logger.error("Error getting prices", card_id=card_id, error=str(e))
            return None
    
    def add_scan(self, image_path: str, ocr_data: Dict[str, Any]) -> int:
        """Add new scan record."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    INSERT INTO scans (image_path, ocr_json, status)
                    VALUES (?, ?, 'NEW')
                """, (image_path, json.dumps(ocr_data)))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            self.logger.error("Error adding scan", error=str(e))
            return -1
    
    def get_new_scans(self) -> List[Dict[str, Any]]:
        """Get all scans with status NEW."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM scans WHERE status = 'NEW' ORDER BY ts
                """)
                
                scans = []
                for row in cursor.fetchall():
                    scans.append({
                        "id": row["id"],
                        "ts": row["ts"],
                        "image_path": row["image_path"],
                        "ocr_data": json.loads(row["ocr_json"]) if row["ocr_json"] else {},
                        "status": row["status"]
                    })
                return scans
        except Exception as e:
            self.logger.error("Error getting new scans", error=str(e))
            return []
    
    def update_scan_status(self, scan_id: int, status: str) -> bool:
        """Update scan status."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("UPDATE scans SET status = ? WHERE id = ?", (status, scan_id))
                conn.commit()
                return True
        except Exception as e:
            self.logger.error("Error updating scan status", scan_id=scan_id, error=str(e))
            return False


# Global singleton
card_cache = PokemonCardCache()