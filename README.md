# Pokemon Card Scanner

A comprehensive tool for scanning, identifying, and pricing Pokemon cards using computer vision and OCR.

## Phase-1 Scope

**Current Version**: CSV-only local storage with accurate recognition and flat CSV storage.
- No paid APIs or Google Sheets integration
- Pricing from pokemontcg.io v2 card objects (embedded TCGplayer/Cardmarket fields)
- Fixed CSV schema with exact column order
- Local SQLite caching for performance

## Features

- **Real-time scanning** - Live camera feed with card detection
- **OCR processing** - Text extraction from card images with ROI optimization
- **Card identification** - Match cards against Pokemon TCG database
- **Price lookup** - Get current market prices from TCGplayer and Cardmarket
- **CSV storage** - Fixed schema output with atomic append operations
- **Local storage** - All data stored locally in organized files
- **Comprehensive logging** - Structured JSON logs with structlog

## Requirements

- Python 3.11+
- Webcam or camera
- Tesseract OCR
- macOS (Apple Silicon) - tested on Apple Silicon Macs

## Installation

### Quick Setup (Recommended)

1. Clone the repository:
```bash
git clone https://github.com/your-username/pokemon-scanner.git
cd pokemon-scanner
```

2. Run the automated setup script:
```bash
./setup.sh
```

This script will:
- Check for Python 3.11 and Tesseract
- Install Tesseract via Homebrew if needed
- Create a virtual environment
- Install all dependencies
- Create necessary directories
- Verify the installation

### Manual Setup

If you prefer manual setup:

1. Clone the repository:
```bash
git clone https://github.com/your-username/pokemon-scanner.git
cd pokemon-scanner
```

2. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install Tesseract OCR on macOS:
```bash
brew install tesseract
```

5. Configure environment variables (create `.env` file):
```bash
# Pokemon TCG API (optional, for enhanced card data)
POKEMON_TCG_API_KEY=your_api_key_here

# Logging level
LOG_LEVEL=INFO

# Cache settings
CACHE_DB_PATH=cache/cards.db
CACHE_EXPIRE_HOURS=24

# Camera settings
CAMERA_INDEX=0

# OCR settings
TESSERACT_PATH=/opt/homebrew/bin/tesseract
OCR_CONFIDENCE_THRESHOLD=60
```

## Usage

### One-Pass Scanning (Recommended)

Scan and process cards in real-time:
```bash
python -m src.cli run
```

- **SPACE**: Capture and process current frame
- **ESC**: Exit scanner
- Automatically processes: capture → warp → OCR → resolve → price → CSV append

### Batch Processing

1. Scan cards (capture and OCR only):
   ```bash
   python -m src.cli scan
   ```

2. Process scanned cards (resolve and price):
   ```bash
   python -m src.cli price
   ```

## CSV Output Schema

The scanner outputs data to `./output/cards_YYYYMMDD.csv` with the following fixed header:

```csv
timestamp_iso,card_id,name,number,set_name,set_id,rarity,tcgplayer_market_usd,cardmarket_trend_eur,cardmarket_avg30_eur,pricing_updatedAt_tcgplayer,pricing_updatedAt_cardmarket,source_image_path,price_sources
```

**Column Details**:
- `timestamp_iso`: ISO format timestamp when card was processed
- `card_id`: Unique identifier from pokemontcg.io
- `name`: Card name (e.g., "Charizard")
- `number`: Collector number (e.g., "4/102")
- `set_name`: Set name (e.g., "Base Set")
- `set_id`: Set identifier
- `rarity`: Card rarity
- `tcgplayer_market_usd`: Current market price in USD
- `cardmarket_trend_eur`: Trend price in EUR
- `cardmarket_avg30_eur`: 30-day average price in EUR
- `pricing_updatedAt_tcgplayer`: Last TCGplayer price update
- `pricing_updatedAt_cardmarket`: Last Cardmarket price update
- `source_image_path`: Path to scanned image
- `price_sources`: JSON array of price sources (e.g., `["pokemontcg.io"]`)

## Data Storage

The scanner automatically stores all data locally in organized files:

- **CSV files**: Daily card data with fixed schema (`cards_YYYYMMDD.csv`)
- **Image storage**: All scanned card images in `output/images/`
- **Detailed logs**: JSON logs with processing details in `output/logs/`
- **Cache database**: SQLite database for card information in `cache/cards.db`

### File Structure

```
output/
├── cards_YYYYMMDD.csv           # Main card data (fixed schema)
├── images/                      # Scanned card images
│   └── scan_YYYYMMDD_HHMMSS_*.jpg
├── logs/                        # Detailed processing logs
│   └── scan_YYYYMMDD_HHMMSS_*.json
└── backups/                     # Automated data backups
```

## Configuration Options

All settings can be configured via environment variables:

- `POKEMON_TCG_API_KEY`: Optional API key for higher rate limits
- `TESSERACT_PATH`: Custom Tesseract binary path (auto-detected on macOS)
- `CAMERA_INDEX`: Camera device index (default 0)
- `OCR_CONFIDENCE_THRESHOLD`: Minimum OCR confidence (default 60)
- `CACHE_EXPIRE_HOURS`: Cache expiration time (default 24)

## Local Storage Benefits

- **Privacy**: All data stays on your local machine
- **Speed**: No network delays for data access
- **Reliability**: Works offline, no external dependencies
- **Control**: Full control over your data and backups

## Development

### Running Tests

```bash
pytest -q
```

### Development Mode

```bash
./dev.sh
```

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- Pokemon TCG API (https://pokemontcg.io/) for card data and pricing
- Tesseract OCR for text recognition
- OpenCV for computer vision capabilities