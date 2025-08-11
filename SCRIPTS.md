# Pokemon Scanner Scripts Reference

This document provides a comprehensive reference for all the scripts and automation tools included in the Pokemon Scanner project.

## Quick Reference

| Script | Purpose | Key Commands |
|--------|---------|--------------|
| `./setup.sh` | Initial setup | Run once after cloning |
| `./start.sh` | Daily usage | `run`, `scan`, `price`, `config`, `test` |
| `./dev.sh` | Development | `test`, `format`, `lint`, `check`, `clean` |
| `make` | Unix/Mac | `setup`, `run`, `scan`, `price`, `test`, `clean` |

## Setup Script (`./setup.sh`)

**Purpose**: One-time setup of the development environment

**What it does**:
- Checks for Python 3.11
- Installs Tesseract via Homebrew if needed
- Creates virtual environment (`venv/`)
- Installs all dependencies from `requirements.txt`
- Creates `cache/` and `output/` directories
- Verifies the installation

**Usage**:
```bash
./setup.sh
```

**When to use**: Run once after cloning the repository

## Start Script (`./start.sh`)

**Purpose**: Quick access to common operations

**Commands**:
- `./start.sh run` - Full scan→resolve→price→append→beep workflow
- `./start.sh scan` - Scan cards and queue them for pricing
- `./start.sh price` - Process queued scans and get prices
- `./start.sh config` - Show current configuration
- `./start.sh test` - Run all tests
- `./start.sh help` - Show help message

**Usage**:
```bash
# Full workflow
./start.sh run

# Just scan some cards
./start.sh scan

# Process scanned cards later
./start.sh price
```

**When to use**: Daily operations and testing

## Development Script (`./dev.sh`)

**Purpose**: Code quality and development tasks

**Commands**:
- `./dev.sh test` - Run all tests
- `./dev.sh test-verbose` - Run tests with verbose output
- `./dev.sh test-coverage` - Run tests with coverage report
- `./dev.sh lint` - Run code linting (requires flake8)
- `./dev.sh format` - Format code (requires black)
- `./dev.sh check` - Run format and lint checks
- `./dev.sh clean` - Clean up cache and temporary files
- `./dev.sh install-dev` - Install development dependencies
- `./dev.sh help` - Show help message

**Usage**:
```bash
# Run tests
./dev.sh test

# Check code quality
./dev.sh check

# Clean up
./dev.sh clean
```

**When to use**: Development, testing, and code maintenance

## Makefile

**Purpose**: Traditional Unix/Mac command interface

**Targets**:
- `make setup` - Initial setup
- `make install` - Install/update dependencies
- `make test` - Run all tests
- `make test-verbose` - Run tests with verbose output
- `make run` - Full workflow
- `make scan` - Scan mode
- `make price` - Pricing mode
- `make config` - Show configuration
- `make clean` - Remove virtual environment and cache
- `make format` - Format code (requires black)
- `make lint` - Lint code (requires flake8)
- `make check` - Run format and lint checks
- `make help` - Show all available commands

**Usage**:
```bash
# Setup
make setup

# Run workflow
make run

# Clean everything
make clean
```

**When to use**: If you prefer traditional Make commands or are on Unix-like systems

## Script Comparison

### Setup
- **`./setup.sh`**: Interactive, comprehensive setup with verification
- **`make setup`**: Calls `./setup.sh` with Make interface

### Daily Operations
- **`./start.sh`**: Simple, focused on common tasks
- **`make`**: More comprehensive, includes development tasks

### Development
- **`./dev.sh`**: Specialized for development tasks
- **`make`**: Includes some development tasks

## Best Practices

### For New Users
1. Run `./setup.sh` once after cloning
2. Use `./start.sh` for daily operations
3. Use `./start.sh help` to see available commands

### For Developers
1. Use `./dev.sh` for development tasks
2. Use `make` for comprehensive operations
3. Run `./dev.sh check` before committing code

### For CI/CD
1. Use `make test` for testing
2. Use `make clean` for cleanup
3. Use `make install` for dependency updates

## Script Dependencies

### Required
- Python 3.11+
- Virtual environment (`venv/`)
- All packages in `requirements.txt`

### Optional (installed as needed)
- `black` - Code formatting
- `flake8` - Code linting
- `pytest-cov` - Test coverage

## Troubleshooting

### Script Permission Denied
```bash
chmod +x setup.sh start.sh dev.sh
```

### Virtual Environment Not Found
```bash
./setup.sh
```

### Dependencies Missing
```bash
./dev.sh install-dev
```

### Tests Failing
```bash
./dev.sh test-verbose
```

## Examples

### Complete Workflow
```bash
# Setup (once)
./setup.sh

# Daily usage
./start.sh run
```

### Development Workflow
```bash
# Setup
./setup.sh

# Development cycle
./dev.sh test          # Run tests
./dev.sh format        # Format code
./dev.sh lint          # Lint code
./dev.sh check         # Both format and lint
```

### Using Make
```bash
# Setup
make setup

# Development
make test
make check
make clean
```

All scripts provide help via `--help` or `help` command, and the Makefile shows all targets with `make help`.
