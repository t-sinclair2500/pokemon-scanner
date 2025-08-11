"""Pokemon Card Scanner - Scan, identify, and price Pokemon cards using computer vision."""

__version__ = "1.0.0"
__author__ = "Pokemon Scanner Team"
__description__ = "A comprehensive tool for scanning Pokemon cards using computer vision, OCR, and API integration"

# Core functionality imports
from .utils.log import configure_logging, get_logger
from .utils.config import settings
from .capture.warp import card_detector, perspective_corrector
from .ocr.extract import ocr_extractor, CardInfo
from .resolve.poketcg import pokemon_resolver, PokemonCard
from .pricing.poketcg_prices import pokemon_pricer, CardPrice, PriceData
from .store.cache import card_cache
from .store.writer import csv_writer
from .store.logger import card_data_logger
from .ui.notifier import notifier

__all__ = [
    # Version info
    "__version__",
    "__author__", 
    "__description__",
    
    # Core components
    "configure_logging",
    "get_logger", 
    "settings",
    "card_detector", 
    "perspective_corrector",
    "ocr_extractor",
    "CardInfo",
    "pokemon_resolver",
    "PokemonCard",
    "pokemon_pricer",
    "CardPrice",
    "PriceData", 
    "card_cache",
    "csv_writer",
    "card_data_logger",
    "notifier"
]
