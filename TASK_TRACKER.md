# Pokemon Scanner Task Tracker

## Global Constraints
- **Phase-1 scope ONLY**: accurate recognition + flat CSV storage. No paid APIs, no Google Sheets.
- **Pricing source**: pokemontcg.io v2 card objects (embedded TCGplayer/Cardmarket fields).
- **Platform**: macOS (M2), Python 3.11.
- **HTTP handling**: Implement exponential backoff on HTTP 429/5xx (0.2s → 1s → 3s), light batch rate limit (~5 QPS).
- **CSV format**: Fixed CSV header and column order (see below). One row per card.
- **Code quality**: Small functions, type hints, structured JSON logs (structlog).
- **Testing**: STOP on any test failure; print traceback and diffs; do not proceed.

## Fixed CSV Header (exact order)
```
timestamp_iso,
card_id,
name,
number,
set_name,
set_id,
rarity,
tcgplayer_market_usd,
cardmarket_trend_eur,
cardmarket_avg30_eur,
pricing_updatedAt_tcgplayer,
pricing_updatedAt_cardmarket,
source_image_path,
price_sources
```

## Task Execution Progress

### TASK 0 — De-Google & dependencies
- [x] **0.1 THINK/PLAN**: Identify all Google Sheets code, env, and docs; confirm deps for OCR/resolve/pricing.
- [x] **0.2 APPLY**: Edit requirements.txt — REMOVE: asyncio, gspread, oauth2client, fuzzywuzzy, python-Levenshtein. ADD/ENSURE: rapidfuzz>=3, aiohttp, opencv-python, pytesseract, pillow, numpy, requests, pydantic, pydantic-settings, typer, rich, structlog, python-dotenv, pandas.
- [x] **0.3 APPLY**: Remove Sheets code/exports from src/store/writer.py and src/store/__init__.py; delete any separate Sheets writer if present.
- [x] **0.4 APPLY**: Remove Sheets envs from src/utils/config.py and .env.example.
- [x] **0.5 APPLY**: Update README.md to CSV-only (Phase-1 scope), remove Sheets mentions.
- [x] **0.6 TEST**: pip install -r requirements.txt; python -c "import src; print('imports-ok')"; ripgrep repository for 'gspread|oauth2client|SHEET_ID|Sheets' → expect no matches.

### TASK 1 — Config & logging foundation
- [x] **1.1 APPLY** (src/utils/config.py): Keep fields: POKEMON_TCG_API_KEY (optional), LOG_LEVEL=INFO, CACHE_DB_PATH=cache/cards.db, CACHE_EXPIRE_HOURS=24, CAMERA_INDEX=0, TESSERACT_PATH (optional), OCR_CONFIDENCE_THRESHOLD=60. Add ensure_cache_and_output_dirs() and resolve_tesseract_path() defaulting to /opt/homebrew/bin/tesseract if present.
- [x] **1.2 APPLY** (src/utils/log.py): Finish structlog JSON config; implement get_logger(name) + LoggerMixin with log_start/log_success/log_error wrappers.
- [x] **1.3 TEST**: python -c "from src.utils.config import Settings; from src.utils.log import get_logger; print('ok')"

### TASK 2 — Warp & overlay (operator framing)
- [x] **2.1 APPLY** (src/capture/warp.py): Implement largest quadrilateral detection, approxPolyDP to 4 points, order points, warp to 900x1260. Return np.ndarray.
- [x] **2.2 APPLY** (src/capture/overlay.py): Draw two translucent ROI rectangles: TOP name band (y 5–14% height, x 8–92%), BOTTOM collector band (y 88–98% height, x 5–95%); color by status.
- [x] **2.3 APPLY** (src/capture/camera.py): SPACE captures stabilized frame; ESC exits; read CAMERA_INDEX from settings.
- [x] **2.4 TEST**: tests/test_warp.py — synthetic quad image → warp returns 900x1260; overlay renders without exceptions (headless check ok).

### TASK 3 — OCR ROIs & parsing
- [x] **3.1 APPLY** (src/ocr/extract.py): 
      - get_name(warped): crop TOP ROI; light denoise; Tesseract '--psm 7'; strip artifacts; return text + heuristic confidence (ratio of A-Z/a-z chars).
      - get_collector_number(warped): crop BOTTOM ROI; grayscale→adaptive threshold; Tesseract '--psm 7' with whitelist '0123456789/'; regex r'\b\d{1,3}\s*/\s*\d{1,3}\b' → dict {'num':int,'den':int}.
      - extract_card_info(): returns CardInfo(name?, collector_number?, confidences).
- [x] **3.2 TEST**: tests/test_ocr_regex.py — strings '12 / 159', '123/123', noise; assert parsed ints; ensure failure on invalid.

### TASK 4 — Resolver (pokemontcg.io v2) with backoff & rapidfuzz
- [x] **4.1 APPLY** (src/resolve/poketcg.py): Replace fuzzywuzzy with rapidfuzz. Implement aiohttp GET with exponential backoff on 429/5xx; include X-Api-Key header if provided. Query:
      - If collector number present → q=number:{X}; if name present, AND name fuzzy.
      - Else name-only query.
      Rank candidates by: exact number match → highest rapidfuzz.ratio(name, candidate_name, ignore_case) → newest set releaseDate.
      Return PokemonCard including id, name, number, set_name, set_id, rarity, images, and raw tcgplayer/cardmarket blobs.
- [x] **4.2 TEST** (tests/test_resolve.py): mock HTTP:
      - Multiple candidates → correct ranking by number then name.
      - 429 then 200 path triggers backoff and succeeds.

### TASK 5 — Pricing flattening (single row fields)
- [x] **5.1 APPLY** (src/pricing/poketcg_prices.py): Implement mapper returning PriceData:
      - tcgplayer_market_usd = first non-null among prices.normal.market → prices.holofoil.market → prices.reverseHolofoil.market.
      - cardmarket_trend_eur = cardmarket.prices.trendPrice or ''.
      - cardmarket_avg30_eur = cardmarket.prices.avg30 or ''.
      - pricing_updatedAt_tcgplayer and pricing_updatedAt_cardmarket if present; else ''.
      - price_sources = ["pokemontcg.io"].
      Add backoff to any network calls (if you fetch per-card again; prefer using data from resolver).
- [x] **5.2 TEST** (tests/test_pricing.py): fixtures cover fallback order and missing fields.

### TASK 6 — Cache semantics (SQLite)
- [x] **6.1 APPLY** (src/store/cache.py): Schema:
      - cards(card_id PRIMARY KEY, name, set_id, set_name, number, rarity)
      - prices(card_id TEXT, source TEXT, updated_at TEXT, tcgplayer_market_usd REAL, cardmarket_trend_eur REAL, cardmarket_avg30_eur REAL, pricing_updatedAt_tcgplayer TEXT, pricing_updatedAt_cardmarket TEXT, sources_json TEXT, PRIMARY KEY(card_id, source))
      - scans(id INTEGER PRIMARY KEY, ts TEXT, image_path TEXT, ocr_json TEXT, status TEXT)
      Implement get_price_data_from_cache(card_id, max_age_hours) before any network call; upsert prices idempotently.
- [x] **6.2 TEST**: tests/test_cache.py — two pricing calls within cache window → second call uses cache (mock network to confirm no call).

### TASK 7 — CSV writer (fixed header; atomic-ish append)
- [x] **7.1 APPLY** (src/store/writer.py): Remove Sheets code. Centralize the fixed header. Implement:
      - get_daily_csv_path() → ./output/cards_YYYYMMDD.csv (ensure dirs).
      - write_row(row_dict): create file with header if missing; append **ordered** row; fsync after write.
      - build_row(PokemonCard, PriceData, source_image_path) → dict with columns in EXACT header order and price_sources serialized as JSON string.
- [x] **7.2 TEST** (tests/test_csv_writer.py): write 2 rows; reopen CSV and assert header equality, column order, and serialized price_sources.

### TASK 8 — CLI flows & rate limiting
- [x] **8.1 APPLY** (src/cli.py): 
      - `run`: one-pass loop: capture → warp → OCR → resolve → price → build_row → append → beep; loop until ESC.
      - `scan`: capture/warp/OCR only; insert into scans with status NEW (and save image path).
      - `price`: iterate NEW scans → resolve+price → write CSV → mark DONE; sleep ~150–250ms between cards to rate limit.
      Ensure both paths use cache lookups before resolver/pricer network calls.
- [x] **8.2 APPLY** (src/cli.py): 
      - Cache integration: check cache before resolver network calls, store resolved cards and pricing data, use cache expiration (24 hours default).
      - Rate limiting: ~5 QPS limit (150-250ms between requests), exponential backoff on HTTP 429/5xx errors, respect pokemontcg.io API limits.
      - Error handling: graceful handling of OCR failures, network error recovery with backoff, log all operations with structlog.

### TASK 9 — README & .env.example (CSV-only)
- [x] **9.1 APPLY**: Update README.md with Phase-1 scope, Homebrew Tesseract path (/opt/homebrew/bin/tesseract), venv setup, run commands:
       - One-pass: `python -m src.cli run`
       - Batch: `python -m src.cli scan` then `python -m src.cli price`
       Note the exact CSV schema and output path.
- [x] **9.2 APPLY**: Environment variable configuration documented in README.md with all required settings:
       POKEMON_TCG_API_KEY=
       LOG_LEVEL=INFO
       CACHE_DB_PATH=cache/cards.db
       CACHE_EXPIRE_HOURS=24
       CAMERA_INDEX=0
       TESSERACT_PATH=/opt/homebrew/bin/tesseract
- [x] **9.3 TEST**: n/a.

## FINAL — TEST & SUMMARY
- [x] **Run**: `pytest -q`
- [x] **Manual**: `python -m src.cli --help`; CLI commands working correctly with run, scan, and price commands.
- [x] **Summary**: Append to TASKLOG.md a short summary of changed files and "how to run".

## Progress Summary
- **Completed**: 32/32 micro-tasks (100.0%)
- **Current Focus**: COMPLETE
- **Next**: All tasks completed successfully

## Task Execution Rules
1. **Tracker Update Required**: After each micro-task completion, immediately update this TASK_TRACKER.md with completion status [x]
2. **TASKLOG.md Update**: Also append completion line to TASKLOG.md with timestamp and one-sentence outcome
3. **Test-First Approach**: Run tests after each APPLY task before proceeding to next
4. **Stop on Failure**: If any test fails, print traceback/diffs and do not proceed until fixed
5. **Incremental Progress**: Complete one micro-task at a time, ensuring each is fully functional
