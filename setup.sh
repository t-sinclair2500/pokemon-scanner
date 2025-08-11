#!/bin/bash

# Pokemon Scanner Setup Script
# This script sets up the development environment for macOS

set -e  # Exit on any error

echo "Setting up Pokemon Scanner development environment..."

# Check if Python 3.11 is available
if ! command -v python3.11 &> /dev/null; then
    echo "Python 3.11 not found. Please install Python 3.11 first."
    echo "You can install it with: brew install python@3.11"
    exit 1
fi

# Check if Tesseract is installed
if ! command -v tesseract &> /dev/null; then
    echo "Tesseract not found. Installing with Homebrew..."
    if ! command -v brew &> /dev/null; then
        echo "Homebrew not found. Please install Homebrew first:"
        echo "/bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        exit 1
    fi
    brew install tesseract
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3.11 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip and install dependencies
echo "Installing dependencies..."
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# Create necessary directories
echo "Creating cache and output directories..."
mkdir -p cache output

# Test the installation
echo "Testing installation..."
python -c "import src; print('✓ All modules imported successfully')"
python -c "from src.utils.config import ensure_tesseract; print(f'✓ Tesseract found at: {ensure_tesseract()}')"

echo ""
echo "Setup complete! To start working:"
echo "1. Activate the virtual environment: source venv/bin/activate"
echo "2. Run the scanner: python -m src.cli run"
echo "3. Or use individual commands: python -m src.cli scan, then python -m src.cli price"
echo ""
echo "For help: python -m src.cli --help"
