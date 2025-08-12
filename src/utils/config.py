"""Configuration and settings management."""

from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator
from pathlib import Path
import os

class Settings(BaseSettings):
    # Pokemon TCG API
    POKEMON_TCG_API_KEY: Optional[str] = None
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # Cache and storage
    CACHE_DB_PATH: str = "cache/cards.db"
    CACHE_EXPIRE_HOURS: int = 24
    
    # Camera settings
    CAMERA_INDEX: int = 0
    
    # OCR settings
    TESSERACT_PATH: Optional[str] = None
    OCR_CONFIDENCE_THRESHOLD: int = 60

    @field_validator('POKEMON_TCG_API_KEY', mode='before')
    @classmethod
    def validate_api_key(cls, v):
        """Convert empty/whitespace strings to None."""
        if isinstance(v, str) and not v.strip():
            return None
        return v
    
    @field_validator('LOG_LEVEL', mode='before')
    @classmethod
    def validate_log_level(cls, v):
        """Convert empty/whitespace strings to default."""
        if isinstance(v, str) and not v.strip():
            return "INFO"
        return v
    
    @field_validator('CACHE_DB_PATH', mode='before')
    @classmethod
    def validate_cache_path(cls, v):
        """Convert empty/whitespace strings to default."""
        if isinstance(v, str) and not v.strip():
            return "cache/cards.db"
        return v

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore"
    }

# Global settings instance
settings = Settings()

def ensure_cache_and_output_dirs():
    """Ensure cache and output directories exist."""
    # Get the project root directory (where this file is located)
    project_root = Path(__file__).parent.parent.parent
    
    # Resolve cache directory relative to project root
    cache_dir = project_root / Path(settings.CACHE_DB_PATH).parent
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Resolve output directory relative to project root
    output_dir = project_root / "output"
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
