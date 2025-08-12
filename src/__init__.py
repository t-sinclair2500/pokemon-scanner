"""Pokemon Card Scanner - Scan, identify, and price Pokemon cards using computer vision."""

__version__ = "1.0.0"
__author__ = "Pokemon Scanner Team"
__description__ = "A comprehensive tool for scanning Pokemon cards using computer vision, OCR, and API integration"

from .capture.warp import card_detector, perspective_corrector
from .ocr.extract import CardInfo, ocr_extractor
from .pricing.poketcg_prices import PriceData, pokemon_pricer
from .resolve.poketcg import PokemonCard, pokemon_resolver
from .store.cache import card_cache
from .store.logger import card_data_logger
from .store.writer import csv_writer
from .ui.notifier import notifier
from .utils.config import settings

# Core functionality imports
from .utils.log import configure_logging, get_logger

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
    "PriceData",
    "card_cache",
    "csv_writer",
    "card_data_logger",
    "notifier",
]
