#!/bin/bash

# Pokemon Scanner Start Script
# Quick start for common operations

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Please run ./setup.sh first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Function to show usage
show_usage() {
    echo "Pokemon Scanner - Quick Start"
    echo ""
    echo "Usage: ./start.sh [command]"
    echo ""
    echo "Commands:"
echo "  scan     - Scan cards and log results with high accuracy"
echo "  summary  - Show summary of all scanned cards"
echo "  export   - Export scan data to CSV"
echo "  test     - Run all tests"
echo "  help     - Show this help message"
    echo ""
    echo "Examples:"
echo "  ./start.sh scan     # Scan cards and log results"
echo "  ./start.sh summary  # View scan summary"
echo "  ./start.sh export   # Export data to CSV"
    echo ""
    echo "Or use directly: python -m src.cli [command]"
}

# Parse command line arguments
case "${1:-help}" in
    "run")
        echo "Starting full Pokemon scanner workflow..."
        python -m src.cli run
        ;;
    "scan")
        echo "Starting scan mode..."
        python -m src.cli scan
        ;;
    "summary")
        echo "Showing scan summary..."
        python -m src.cli summary
        ;;
    "export")
        echo "Exporting scan data..."
        python -m src.cli export
        ;;
    "test")
        echo "Running tests..."
        python -m pytest -q
        ;;
    "help"|*)
        show_usage
        ;;
esac
