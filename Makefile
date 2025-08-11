# Pokemon Scanner Makefile
# Common development tasks

.PHONY: help setup install test clean run scan price config

# Default target
help:
	@echo "Pokemon Scanner - Available Commands"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  setup     - Initial setup (creates venv, installs deps)"
	@echo "  install   - Install/update dependencies"
	@echo "  clean     - Remove virtual environment and cache"
	@echo ""
	@echo "Testing:"
	@echo "  test      - Run all tests"
	@echo "  test-verbose - Run tests with verbose output"
	@echo ""
	@echo "Running:"
	@echo "  scan      - Scan cards and log results with high accuracy"
	@echo "  summary   - Show summary of all scanned cards"
	@echo "  export    - Export scan data to CSV"
	@echo ""
	@echo "Development:"
	@echo "  format    - Format code with black (if installed)"
	@echo "  lint      - Lint code with flake8 (if installed)"
	@echo "  check     - Run format and lint checks"

# Setup virtual environment and install dependencies
setup:
	@echo "Setting up Pokemon Scanner development environment..."
	@chmod +x setup.sh
	@./setup.sh

# Install/update dependencies
install:
	@echo "Installing dependencies..."
	@source venv/bin/activate && pip install -r requirements.txt

# Clean up
clean:
	@echo "Cleaning up..."
	@rm -rf venv
	@rm -rf cache
	@rm -rf output
	@rm -rf __pycache__
	@rm -rf src/__pycache__
	@rm -rf src/*/__pycache__
	@rm -rf tests/__pycache__
	@find . -name "*.pyc" -delete
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Run tests
test:
	@echo "Running tests..."
	@source venv/bin/activate && python -m pytest -q

# Run tests with verbose output
test-verbose:
	@echo "Running tests with verbose output..."
	@source venv/bin/activate && python -m pytest -v

# Scan cards and log results
scan:
	@echo "Starting card scanning mode..."
	@source venv/bin/activate && python -m src.cli scan

# Show scan summary
summary:
	@echo "Showing scan summary..."
	@source venv/bin/activate && python -m src.cli summary

# Export scan data
export:
	@echo "Exporting scan data..."
	@source venv/bin/activate && python -m src.cli export

# Format code (optional - requires black)
format:
	@echo "Formatting code..."
	@source venv/bin/activate && black src/ tests/

# Lint code (optional - requires flake8)
lint:
	@echo "Linting code..."
	@source venv/bin/activate && flake8 src/ tests/

# Run format and lint checks
check: format lint
	@echo "All checks completed!"
