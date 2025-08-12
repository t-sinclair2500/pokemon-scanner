You are my senior Python pair programmer.
Use THINK → PLAN → APPLY → TEST and log to TASKLOG.md.

GOAL
Finalize README and runbook for Phase-1 (visual matching primary, OCR fallback, CSV-only).

THINK
We need crystal-clear steps: install, build index, run, batch mode, CSV schema, troubleshooting.

PLAN
Update README.md with:
- Install (macOS M2): `brew install tesseract`, create venv, `pip install -r requirements.txt`.
- Build the index: `python -m src.reference.build_index` (downloads EN cards, images, embeddings, HNSW).
- Run one-pass: `python -m src.cli run`.
- Batch: `python -m src.cli scan` then `python -m src.cli price`.
- CSV location: `output/cards_YYYY-MM-DD.csv` and exact header order.
- Notes: Tesseract path `/opt/homebrew/bin/tesseract` (auto-detected), confidence thresholds, rate limit (~5 QPS).

APPLY
Update README.md accordingly.

TEST
- Proofread; no broken commands.
