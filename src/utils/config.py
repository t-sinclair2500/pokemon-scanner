"""Configuration and settings management."""

from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path
import os

class Settings(BaseSettings):
    # Pokemon TCG API
    POKEMON_TCG_API_KEY: Optional[str] = Field(None, env="POKEMON_TCG_API_KEY")
    
    # Logging
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")
    
    # Cache and storage
    CACHE_DB_PATH: str = Field("cache/cards.db", env="CACHE_DB_PATH")
    CACHE_EXPIRE_HOURS: int = Field(24, env="CACHE_EXPIRE_HOURS")
    
    # Camera settings
    CAMERA_INDEX: int = Field(0, env="CAMERA_INDEX")
    
    # OCR settings
    TESSERACT_PATH: Optional[str] = Field(None, env="TESSERACT_PATH")
    OCR_CONFIDENCE_THRESHOLD: int = Field(60, env="OCR_CONFIDENCE_THRESHOLD")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

settings = Settings()

def ensure_cache_and_output_dirs():
    """Ensure cache and output directories exist."""
    cache_dir = Path(settings.CACHE_DB_PATH).parent
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

def resolve_tesseract_path() -> str:
    """Get Tesseract path, with fallback to common locations."""
    if settings.TESSERACT_PATH and Path(settings.TESSERACT_PATH).exists():
        return settings.TESSERACT_PATH
    
    # Try to find tesseract in PATH
    import shutil
    tesseract_path = shutil.which("tesseract")
    if tesseract_path:
        return tesseract_path
    
    # Common macOS Homebrew paths
    common_paths = [
        "/opt/homebrew/bin/tesseract",  # Apple Silicon Homebrew
        "/usr/local/bin/tesseract",     # Intel Homebrew
        "/usr/bin/tesseract",           # System package
    ]
    
    for path in common_paths:
        if Path(path).exists():
            return path
    
    raise FileNotFoundError(
        "Tesseract not found. Please install with: brew install tesseract"
    )

# Legacy function names for backward compatibility
def ensure_cache_dir():
    """Ensure cache and output directories exist."""
    ensure_cache_and_output_dirs()

def ensure_tesseract():
    """Get Tesseract path, with fallback to common locations."""
    return resolve_tesseract_path()
