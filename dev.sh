#!/bin/bash

# Pokemon Scanner Development Helper Script
# Common development tasks and quality checks

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Please run ./setup.sh first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Function to show usage
show_usage() {
    echo "Pokemon Scanner - Development Helper"
    echo ""
    echo "Usage: ./dev.sh [command]"
    echo ""
    echo "Commands:"
    echo "  test        - Run all tests"
    echo "  smoke       - Run end-to-end smoke tests"
    echo "  test-verbose - Run tests with verbose output"
    echo "  test-coverage - Run tests with coverage report"
    echo "  lint        - Run code linting (requires flake8)"
    echo "  format      - Format code (requires black)"
    echo "  check       - Run format and lint checks"
    echo "  clean       - Clean up cache and temporary files"
    echo "  install-dev - Install development dependencies"
    echo "  help        - Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./dev.sh test          # Run all tests"
    echo "  ./dev.sh test-coverage # Run tests with coverage"
    echo "  ./dev.sh check         # Format and lint code"
}

# Parse command line arguments
case "${1:-help}" in
    "test")
        echo "Running tests..."
        python -m pytest -q
        ;;
    "smoke")
        echo "Running smoke tests..."
        python -c "
import asyncio
from src.resolve.poketcg import PokemonCard
from src.pricing.poketcg_prices import pokemon_pricer
from src.store.cache import card_cache
from src.store.writer import csv_writer
from datetime import datetime

def test_pricing_extraction():
    mock_card = PokemonCard(
        id='test-123', name='Pikachu', number='1/150', set_name='Base Set',
        set_id='base1', rarity='Common', images={'small': 'test.jpg'},
        tcgplayer={'prices': {'normal': {'market': 1.50}, 'updatedAt': '2024-01-01T00:00:00Z'}},
        cardmarket={'prices': {'trendPrice': 1.25, 'avg30': 1.30, 'updatedAt': '2024-01-01T00:00:00Z'}}
    )
    price_data = pokemon_pricer.extract_prices(mock_card)
    if price_data:
        print('✓ Pricing extraction works')
        return price_data
    else:
        print('✗ Pricing extraction failed')
        return None

def test_cache_system():
    mock_card = PokemonCard(
        id='test-456', name='Charizard', number='4/102', set_name='Base Set',
        set_id='base1', rarity='Holo Rare', images={'small': 'test2.jpg'},
        tcgplayer=None, cardmarket=None
    )
    if card_cache.cache_card(mock_card):
        cached_card = card_cache.get_card('test-456')
        if cached_card:
            print('✓ Cache system works')
            return True
    return False

def test_csv_writer(price_data):
    if not price_data:
        return False
    csv_data = [{
        'timestamp_iso': datetime.now().isoformat(),
        'card_id': price_data.card_id, 'name': price_data.card_name,
        'number': '1/150', 'set_name': 'Base Set', 'set_id': 'base1', 'rarity': 'Common',
        'tcgplayer_market_usd': price_data.prices.tcgplayer_market_usd,
        'cardmarket_trend_eur': price_data.prices.cardmarket_trend_eur,
        'cardmarket_avg30_eur': price_data.prices.cardmarket_avg30_eur,
        'pricing_updatedAt_tcgplayer': price_data.prices.pricing_updatedAt_tcgplayer,
        'pricing_updatedAt_cardmarket': price_data.prices.pricing_updatedAt_cardmarket,
        'source_image_path': 'test_smoke.jpg',
        'price_sources': ','.join(price_data.prices.price_sources)
    }]
    try:
        filename = csv_writer.write_cards(csv_data, 'smoke_test.csv')
        print('✓ CSV writer works')
        return True
    except Exception as e:
        print(f'✗ CSV write failed: {e}')
        return False

async def test_api_connection():
    try:
        from src.resolve.poketcg import pokemon_resolver
        cards = await pokemon_resolver.search_cards('pikachu', limit=1)
        if cards:
            print('✓ API connection works')
            return True
        else:
            print('⚠ API connection works but no cards returned')
            return False
    except Exception as e:
        print(f'✗ API connection failed: {e}')
        return False

# Run tests
print('🚀 Pokemon Scanner Smoke Tests')
print('=' * 40)
price_data = test_pricing_extraction()
cache_ok = test_cache_system()
csv_ok = test_csv_writer(price_data)
try:
    api_ok = asyncio.run(test_api_connection())
except Exception as e:
    api_ok = False

print('\\n' + '=' * 40)
print('📊 Smoke Test Results:')
print(f'  Pricing Extraction: {\"✓ PASS\" if price_data else \"✗ FAIL\"}')
print(f'  Cache System: {\"✓ PASS\" if cache_ok else \"✗ FAIL\"}')
print(f'  CSV Writer: {\"✓ PASS\" if csv_ok else \"✗ FAIL\"}')
print(f'  API Connection: {\"✓ PASS\" if api_ok else \"⚠ PARTIAL\"}')

if price_data and cache_ok and csv_ok:
    print('\\n🎉 Core functionality tests PASSED!')
    print('   The scanner should work for local operations.')
    if not api_ok:
        print('   Note: API connection failed - check network/API key for online features.')
else:
    print('\\n❌ Some core functionality tests FAILED!')
"
        ;;
    "test-verbose")
        echo "Running tests with verbose output..."
        python -m pytest -v
        ;;
    "test-coverage")
        echo "Running tests with coverage report..."
        if ! pip show pytest-cov &> /dev/null; then
            echo "Installing pytest-cov..."
            pip install pytest-cov
        fi
        python -m pytest --cov=src --cov-report=term-missing --cov-report=html
        echo "Coverage report generated in htmlcov/"
        ;;
    "lint")
        echo "Running code linting..."
        if ! command -v flake8 &> /dev/null; then
            if ! pip show flake8 &> /dev/null; then
                echo "Installing flake8..."
                pip install flake8
            fi
        fi
        python -m flake8 src/ tests/ --max-line-length=100 --ignore=E203,W503
        ;;
    "format")
        echo "Formatting code..."
        if ! command -v black &> /dev/null; then
            if ! pip show black &> /dev/null; then
                echo "Installing black..."
                pip install black
            fi
        fi
        python -m black src/ tests/ --line-length=100
        ;;
    "check")
        echo "Running format and lint checks..."
        ./dev.sh format
        ./dev.sh lint
        echo "All checks completed!"
        ;;
    "clean")
        echo "Cleaning up cache and temporary files..."
        rm -rf cache/*
        rm -rf output/*
        rm -rf __pycache__
        rm -rf src/__pycache__
        rm -rf src/*/__pycache__
        rm -rf tests/__pycache__
        find . -name "*.pyc" -delete
        find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
        echo "Cleanup complete!"
        ;;
    "install-dev")
        echo "Installing development dependencies..."
        pip install pytest-cov flake8 black
        echo "Development dependencies installed!"
        ;;
    "help"|*)
        show_usage
        ;;
esac
