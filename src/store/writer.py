"""CSV writer for Pokemon card data with fixed header structure."""

import csv
import json
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import os

from ..utils.log import get_logger
from ..utils.config import settings


class CSVWriter:
    """CSV writer with fixed header structure for Phase-1 scope."""
    
    # Fixed CSV header as specified in requirements
    FIXED_HEADER = [
        "timestamp_iso",
        "card_id",
        "name",
        "number",
        "set_name",
        "set_id",
        "rarity",
        "tcgplayer_market_usd",
        "cardmarket_trend_eur",
        "cardmarket_avg30_eur",
        "pricing_updatedAt_tcgplayer",
        "pricing_updatedAt_cardmarket",
        "source_image_path",
        "price_sources"
    ]
    
    def __init__(self):
        self.logger = get_logger(__name__)
        # Resolve output directory relative to project root
        project_root = Path(__file__).parent.parent.parent
        self.output_dir = project_root / "output"
        self.output_dir.mkdir(exist_ok=True)
        
        # Main CSV file for card data
        self.csv_path = self.get_daily_csv_path()
        
        self.logger.info("CSV writer initialized", 
                        output_dir=str(self.output_dir),
                        csv_path=str(self.csv_path))
    
    def get_daily_csv_path(self) -> Path:
        """Get the daily CSV file path, creating directories if needed."""
        # Ensure output directory exists
        self.output_dir.mkdir(exist_ok=True)
        
        # Generate filename: cards_YYYYMMDD.csv
        filename = f"cards_{datetime.now().strftime('%Y%m%d')}.csv"
        return self.output_dir / filename
    
    def write_row(self, row_dict: Dict[str, Any]) -> None:
        """Write a row to the CSV file, creating with header if missing."""
        # Ensure the CSV file exists with proper header
        file_exists = self.csv_path.exists()
        
        # Open file in append mode
        with open(self.csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.FIXED_HEADER)
            
            # Write header if file is new
            if not file_exists:
                writer.writeheader()
                self.logger.info("Created new CSV file with header", file=str(self.csv_path))
            
            # Write the row
            writer.writerow(row_dict)
            
            # Force flush to disk for atomic-ish behavior
            f.flush()
            os.fsync(f.fileno())
        
        self.logger.debug("Row written to CSV", row_dict=row_dict)
    
    def build_row(self, pokemon_card: Dict[str, Any], price_data: Dict[str, Any], 
                  source_image_path: str) -> Dict[str, Any]:
        """Build a row dictionary with columns in EXACT header order."""
        # Ensure price_sources is serialized as JSON string
        price_sources = price_data.get('price_sources', [])
        if isinstance(price_sources, list):
            price_sources_json = json.dumps(price_sources)
        else:
            price_sources_json = json.dumps([price_sources]) if price_sources else '[]'
        
        # Build row in exact header order
        # Handle nested set data safely
        set_data = pokemon_card.get('set')
        if set_data is None:
            set_name = ''
            set_id = ''
        else:
            set_name = set_data.get('name', '')
            set_id = set_data.get('id', '')
        
        row = {
            "timestamp_iso": datetime.now().isoformat(),
            "card_id": pokemon_card.get('id', ''),
            "name": pokemon_card.get('name', ''),
            "number": pokemon_card.get('number', ''),
            "set_name": set_name,
            "set_id": set_id,
            "rarity": pokemon_card.get('rarity', ''),
            "tcgplayer_market_usd": price_data.get('tcgplayer_market_usd', ''),
            "cardmarket_trend_eur": price_data.get('cardmarket_trend_eur', ''),
            "cardmarket_avg30_eur": price_data.get('cardmarket_avg30_eur', ''),
            "pricing_updatedAt_tcgplayer": price_data.get('pricing_updatedAt_tcgplayer', ''),
            "pricing_updatedAt_cardmarket": price_data.get('pricing_updatedAt_cardmarket', ''),
            "source_image_path": source_image_path,
            "price_sources": price_sources_json
        }
        
        return row


# Global singleton
csv_writer = CSVWriter()