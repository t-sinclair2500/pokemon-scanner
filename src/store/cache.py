"""SQLite cache for cards and scans."""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..pricing.poketcg_prices import PriceData
from ..resolve.poketcg import PokemonCard
from ..utils.config import ensure_cache_dir, settings
from ..utils.log import get_logger


class CacheManager:
    """SQLite cache manager for Pokemon card data and scans."""

    def __init__(self, db_path: str = "cache/cards.db"):
        self.logger = get_logger(__name__)
        # Resolve path relative to project root
        project_root = Path(__file__).parent.parent.parent
        self.db_path = project_root / db_path
        ensure_cache_dir()
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database with required tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Cards table
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS cards (
                        card_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        set_id TEXT NOT NULL,
                        set_name TEXT NOT NULL,
                        number TEXT NOT NULL,
                        rarity TEXT,
                        created_at TEXT NOT NULL
                    )
                """
                )

                # Prices table
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS prices (
                        card_id TEXT NOT NULL,
                        source TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        tcgplayer_market_usd REAL,
                        cardmarket_trend_eur REAL,
                        cardmarket_avg30_eur REAL,
                        pricing_updatedAt_tcgplayer TEXT,
                        pricing_updatedAt_cardmarket TEXT,
                        sources_json TEXT,
                        PRIMARY KEY(card_id, source)
                    )
                """
                )

                # Scans table
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS scans (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ts TEXT NOT NULL,
                        image_path TEXT NOT NULL,
                        ocr_json TEXT,
                        status TEXT NOT NULL DEFAULT 'NEW'
                    )
                """
                )

                conn.commit()
                self.logger.info(
                    "Database initialized successfully", db_path=str(self.db_path)
                )

        except Exception as e:
            self.logger.error("Error initializing database", error=str(e))
            raise

    def _float_to_string(self, value) -> str:
        """Convert float value to string with proper decimal formatting."""
        if value is None:
            return ""
        try:
            # Format with 2 decimal places to preserve precision
            return f"{float(value):.2f}"
        except (ValueError, TypeError):
            return ""

    def get_price_data_from_cache(
        self, card_id: str, max_age_hours: int = 24
    ) -> Optional[PriceData]:
        """Query prices table for card_id and check if data is within max_age_hours."""
        try:
            cutoff = datetime.now() - timedelta(hours=max_age_hours)

            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT p.*, c.name 
                    FROM prices p 
                    JOIN cards c ON p.card_id = c.card_id 
                    WHERE p.card_id = ? AND p.updated_at > ?
                    ORDER BY p.updated_at DESC
                    LIMIT 1
                """,
                    (card_id, cutoff.isoformat()),
                )

                row = cursor.fetchone()
                if row:
                    # Parse price sources from JSON
                    sources = (
                        json.loads(row["sources_json"])
                        if row["sources_json"]
                        else ["pokemontcg.io"]
                    )

                    # Create PriceData object with proper string formatting
                    price_data = PriceData(
                        tcgplayer_market_usd=self._float_to_string(
                            row["tcgplayer_market_usd"]
                        ),
                        cardmarket_trend_eur=self._float_to_string(
                            row["cardmarket_trend_eur"]
                        ),
                        cardmarket_avg30_eur=self._float_to_string(
                            row["cardmarket_avg30_eur"]
                        ),
                        pricing_updatedAt_tcgplayer=row["pricing_updatedAt_tcgplayer"]
                        or "",
                        pricing_updatedAt_cardmarket=row["pricing_updatedAt_cardmarket"]
                        or "",
                        price_sources=sources,
                    )

                    self.logger.debug(
                        "Cache hit for card", card_id=card_id, age_hours=max_age_hours
                    )
                    return price_data

                self.logger.debug(
                    "Cache miss for card", card_id=card_id, age_hours=max_age_hours
                )
                return None

        except Exception as e:
            self.logger.error(
                "Error getting prices from cache", card_id=card_id, error=str(e)
            )
            return None

    def upsert_card(self, card: PokemonCard) -> None:
        """Insert or update cards table."""
        try:
            now = datetime.now().isoformat()

            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO cards 
                    (card_id, name, set_id, set_name, number, rarity, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        card.id,
                        card.name,
                        card.set_id,
                        card.set_name,
                        card.number,
                        card.rarity,
                        now,
                    ),
                )
                conn.commit()

                self.logger.debug("Card upserted", card_id=card.id, name=card.name)

        except Exception as e:
            self.logger.error("Error upserting card", card_id=card.id, error=str(e))
            raise

    def upsert_prices(
        self, card_id: str, price_data: PriceData, source: str = "pokemontcg.io"
    ) -> None:
        """Insert or update prices table."""
        try:
            now = datetime.now().isoformat()

            # Convert string prices back to float for storage
            tcgplayer_market = (
                float(price_data.tcgplayer_market_usd)
                if price_data.tcgplayer_market_usd
                else None
            )
            cardmarket_trend = (
                float(price_data.cardmarket_trend_eur)
                if price_data.cardmarket_trend_eur
                else None
            )
            cardmarket_avg30 = (
                float(price_data.cardmarket_avg30_eur)
                if price_data.cardmarket_avg30_eur
                else None
            )

            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO prices 
                    (card_id, source, updated_at, tcgplayer_market_usd, cardmarket_trend_eur, 
                     cardmarket_avg30_eur, pricing_updatedAt_tcgplayer, pricing_updatedAt_cardmarket, sources_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        card_id,
                        source,
                        now,
                        tcgplayer_market,
                        cardmarket_trend,
                        cardmarket_avg30,
                        price_data.pricing_updatedAt_tcgplayer,
                        price_data.pricing_updatedAt_cardmarket,
                        json.dumps(price_data.price_sources),
                    ),
                )
                conn.commit()

                self.logger.debug("Prices upserted", card_id=card_id, source=source)

        except Exception as e:
            self.logger.error(
                "Error upserting prices", card_id=card_id, source=source, error=str(e)
            )
            raise

    def insert_scan(self, image_path: str, ocr_data: Dict = None) -> int:
        """Insert new scan record."""
        try:
            now = datetime.now().isoformat()

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO scans (ts, image_path, ocr_json, status)
                    VALUES (?, ?, ?, 'NEW')
                """,
                    (now, image_path, json.dumps(ocr_data) if ocr_data else None),
                )
                conn.commit()

                scan_id = cursor.lastrowid
                self.logger.debug(
                    "Scan inserted", scan_id=scan_id, image_path=image_path
                )
                return scan_id

        except Exception as e:
            self.logger.error(
                "Error inserting scan", image_path=image_path, error=str(e)
            )
            raise

    def update_scan_status(
        self, scan_id: int, status: str, ocr_data: Dict = None
    ) -> None:
        """Update scan status and OCR data."""
        try:
            now = datetime.now().isoformat()

            with sqlite3.connect(self.db_path) as conn:
                if ocr_data is not None:
                    result = conn.execute(
                        """
                        UPDATE scans 
                        SET status = ?, ocr_json = ?, ts = ?
                        WHERE id = ?
                    """,
                        (status, json.dumps(ocr_data), now, scan_id),
                    )
                else:
                    result = conn.execute(
                        """
                        UPDATE scans 
                        SET status = ?, ts = ?
                        WHERE id = ?
                    """,
                        (status, now, scan_id),
                    )

                # Check if any rows were affected
                if result.rowcount == 0:
                    raise ValueError(f"No scan found with ID {scan_id}")

                conn.commit()
                self.logger.debug("Scan status updated", scan_id=scan_id, status=status)

        except Exception as e:
            self.logger.error(
                "Error updating scan status",
                scan_id=scan_id,
                status=status,
                error=str(e),
            )
            raise

    def get_new_scans(self) -> List[Dict]:
        """Get all scans with status 'NEW'."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT * FROM scans 
                    WHERE status = 'NEW' 
                    ORDER BY ts
                """
                )

                scans = []
                for row in cursor.fetchall():
                    scans.append(
                        {
                            "id": row["id"],
                            "ts": row["ts"],
                            "image_path": row["image_path"],
                            "ocr_data": (
                                json.loads(row["ocr_json"]) if row["ocr_json"] else {}
                            ),
                            "status": row["status"],
                        }
                    )

                self.logger.debug("Retrieved new scans", count=len(scans))
                return scans

        except Exception as e:
            self.logger.error("Error getting new scans", error=str(e))
            return []

    def close(self) -> None:
        """Close database connection."""
        # SQLite connections are automatically closed when using context managers
        # This method is provided for compatibility
        self.logger.debug("Cache manager closing")


# Global singleton
card_cache = CacheManager()
