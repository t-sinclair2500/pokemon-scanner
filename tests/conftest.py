"""Pytest configuration and shared fixtures for Pokemon Scanner tests."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch


@pytest.fixture(scope="session")
def test_environment():
    """Set up test environment for the entire test session."""
    # Configure test environment variables
    with patch.dict('os.environ', {
        'POKEMON_SCANNER_ENV': 'test',
        'POKEMON_SCANNER_LOG_LEVEL': 'DEBUG',
        'POKEMON_SCANNER_CACHE_DIR': '/tmp/test_cache',
        'POKEMON_SCANNER_OUTPUT_DIR': '/tmp/test_output'
    }):
        yield


@pytest.fixture(scope="function")
def temp_dirs():
    """Create temporary directories for each test function."""
    temp_dir = Path(tempfile.mkdtemp())
    output_dir = temp_dir / "output"
    cache_dir = temp_dir / "cache"
    output_dir.mkdir()
    cache_dir.mkdir()
    
    yield {
        'temp_dir': temp_dir,
        'output_dir': output_dir,
        'cache_dir': cache_dir
    }
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture(scope="function")
def mock_settings(temp_dirs):
    """Mock application settings to use test directories."""
    with patch('src.utils.config.settings') as mock_settings:
        mock_settings.OUTPUT_DIR = str(temp_dirs['output_dir'])
        mock_settings.CACHE_DIR = str(temp_dirs['cache_dir'])
        mock_settings.CACHE_EXPIRE_HOURS = 24
        mock_settings.LOG_LEVEL = 'DEBUG'
        mock_settings.ENVIRONMENT = 'test'
        yield mock_settings


@pytest.fixture(scope="function")
def mock_camera():
    """Mock camera functionality for tests."""
    with patch('src.capture.camera.camera_capture.initialize', return_value=True), \
         patch('src.capture.camera.camera_capture.get_preview_frame') as mock_preview, \
         patch('src.capture.camera.camera_capture.capture_stable_frame') as mock_capture, \
         patch('src.capture.camera.camera_capture.detect_card_region') as mock_detect, \
         patch('src.capture.camera.camera_capture.release') as mock_release:
        
        # Create mock frames
        import numpy as np
        mock_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_card = np.zeros((400, 300, 3), dtype=np.uint8)
        
        mock_preview.return_value = mock_frame
        mock_capture.return_value = mock_frame
        mock_detect.return_value = mock_card
        
        yield {
            'preview': mock_preview,
            'capture': mock_capture,
            'detect': mock_detect,
            'release': mock_release,
            'frame': mock_frame,
            'card': mock_card
        }


@pytest.fixture(scope="function")
def mock_ocr():
    """Mock OCR functionality for tests."""
    from src.ocr.extract import CardInfo
    
    with patch('src.ocr.extract.ocr_extractor.extract_card_info') as mock_extract:
        mock_extract.return_value = CardInfo(
            name="Charizard",
            collector_number="4",
            confidence=85.0
        )
        yield mock_extract


@pytest.fixture(scope="function")
def mock_resolver():
    """Mock Pokemon TCG resolver for tests."""
    with patch('src.resolve.poketcg.PokemonTCGResolver.search_cards') as mock_search, \
         patch('src.resolve.poketcg.PokemonTCGResolver.find_best_match') as mock_match:
        
        # Mock successful card search
        mock_card = {
            'id': 'charizard-base-4',
            'name': 'Charizard',
            'number': '4',
            'set': {'name': 'Base Set', 'id': 'base1'},
            'rarity': 'Holo Rare',
            'tcgplayer': {
                'prices': {
                    'holofoil': {'market': 100.0, 'low': 80.0, 'high': 120.0}
                }
            },
            'cardmarket': {
                'prices': {
                    'averageSellPrice': 85.0,
                    'lowPrice': 70.0,
                    'highPrice': 100.0
                }
            }
        }
        
        mock_search.return_value = [mock_card]
        mock_match.return_value = mock_card
        
        yield {
            'search': mock_search,
            'match': mock_match,
            'card': mock_card
        }


@pytest.fixture(scope="function")
def mock_pricer():
    """Mock pricing functionality for tests."""
    with patch('src.pricing.poketcg_prices.pokemon_pricer.extract_prices_from_card') as mock_extract:
        mock_extract.return_value = {
            'tcgplayer_market_usd': 100.0,
            'tcgplayer_low_usd': 80.0,
            'tcgplayer_high_usd': 120.0,
            'cardmarket_trend_eur': 85.0,
            'cardmarket_avg30_eur': 82.0,
            'cardmarket_low_eur': 70.0,
            'cardmarket_high_eur': 100.0
        }
        yield mock_extract


@pytest.fixture(scope="function")
def mock_cv2():
    """Mock OpenCV functionality for tests."""
    with patch('cv2.imshow') as mock_imshow, \
         patch('cv2.waitKey') as mock_waitkey, \
         patch('cv2.destroyAllWindows') as mock_destroy, \
         patch('cv2.imwrite') as mock_imwrite, \
         patch('cv2.putText') as mock_puttext, \
         patch('cv2.rectangle') as mock_rectangle:
        
        # Mock key presses (ESC to exit immediately)
        mock_waitkey.return_value = 27  # ESC key
        
        yield {
            'imshow': mock_imshow,
            'waitKey': mock_waitkey,
            'destroyAllWindows': mock_destroy,
            'imwrite': mock_imwrite,
            'putText': mock_puttext,
            'rectangle': mock_rectangle
        }


@pytest.fixture(scope="function")
def sample_card_data():
    """Sample card data for testing."""
    return {
        'id': 'charizard-base-4',
        'name': 'Charizard',
        'number': '4',
        'set': {'name': 'Base Set', 'id': 'base1'},
        'rarity': 'Holo Rare',
        'tcgplayer': {
            'prices': {
                'holofoil': {'market': 100.0, 'low': 80.0, 'high': 120.0}
            }
        },
        'cardmarket': {
            'prices': {
                'averageSellPrice': 85.0,
                'lowPrice': 70.0,
                'highPrice': 100.0
            }
        }
    }


@pytest.fixture(scope="function")
def sample_price_data():
    """Sample price data for testing."""
    return {
        'tcgplayer_market_usd': 100.0,
        'tcgplayer_low_usd': 80.0,
        'tcgplayer_high_usd': 120.0,
        'cardmarket_trend_eur': 85.0,
        'cardmarket_avg30_eur': 82.0,
        'cardmarket_low_eur': 70.0,
        'cardmarket_high_eur': 100.0
    }


@pytest.fixture(scope="function")
def sample_ocr_data():
    """Sample OCR data for testing."""
    return {
        'name': 'Charizard',
        'collector_number': '4',
        'confidence': 85.0
    }


@pytest.fixture(scope="function")
def mock_file_system(temp_dirs):
    """Mock file system operations for tests."""
    with patch('pathlib.Path.exists', return_value=True), \
         patch('pathlib.Path.mkdir'), \
         patch('pathlib.Path.parent', return_value=temp_dirs['output_dir']):
        yield


# Configure pytest options
def pytest_configure(config):
    """Configure pytest with custom options."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Mark integration tests
        if "integration" in item.name.lower() or "TestFullAppIntegration" in str(item.cls):
            item.add_marker(pytest.mark.integration)
        
        # Mark slow tests
        if any(slow_indicator in item.name.lower() for slow_indicator in ['performance', 'bulk', 'cache']):
            item.add_marker(pytest.mark.slow)
        
        # Mark unit tests (default)
        if not item.get_closest_marker('integration') and not item.get_closest_marker('slow'):
            item.add_marker(pytest.mark.unit)
