#!/usr/bin/env python3
"""Test runner for Pokemon Scanner application.

This script provides easy access to run different types of tests:
- Unit tests only
- Integration tests only  
- All tests
- Specific test files
- Performance tests
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}\n")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"\n✅ {description} completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {description} failed with exit code {e.returncode}")
        return False
    except FileNotFoundError:
        print(f"\n❌ Command not found: {cmd[0]}")
        print("Make sure you're in the virtual environment and dependencies are installed.")
        return False


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(
        description="Run Pokemon Scanner tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                    # Run all tests
  python run_tests.py --unit            # Run only unit tests
  python run_tests.py --integration     # Run only integration tests
  python run_tests.py --performance     # Run performance tests
  python run_tests.py --file test_cache.py  # Run specific test file
  python run_tests.py --verbose         # Run with verbose output
  python run_tests.py --coverage        # Run with coverage report
        """
    )
    
    parser.add_argument(
        '--unit', 
        action='store_true',
        help='Run only unit tests'
    )
    
    parser.add_argument(
        '--integration', 
        action='store_true',
        help='Run only integration tests'
    )
    
    parser.add_argument(
        '--performance', 
        action='store_true',
        help='Run performance tests'
    )
    
    parser.add_argument(
        '--file', 
        type=str,
        help='Run tests from specific file'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Run tests with verbose output'
    )
    
    parser.add_argument(
        '--coverage', 
        action='store_true',
        help='Run tests with coverage report'
    )
    
    parser.add_argument(
        '--fast', 
        action='store_true',
        help='Skip slow tests'
    )
    
    parser.add_argument(
        '--fix', 
        action='store_true',
        help='Fix failing tests by updating test data'
    )
    
    args = parser.parse_args()
    
    # Check if we're in the right directory
    if not Path('src').exists() or not Path('tests').exists():
        print("❌ Error: Please run this script from the pokemon-scanner root directory")
        sys.exit(1)
    
    # Check if virtual environment is activated
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  Warning: Virtual environment may not be activated")
        print("   Run: source venv/bin/activate")
    
    # Build pytest command
    cmd = ['python', '-m', 'pytest']
    
    # Add markers based on arguments
    if args.unit:
        cmd.extend(['-m', 'unit'])
    elif args.integration:
        cmd.extend(['-m', 'integration'])
    elif args.performance:
        cmd.extend(['-m', 'slow'])
    
    # Add file filter
    if args.file:
        cmd.append(f'tests/{args.file}')
    else:
        cmd.append('tests/')
    
    # Add options
    if args.verbose:
        cmd.append('-v')
    
    if args.coverage:
        cmd.extend(['--cov=src', '--cov-report=html', '--cov-report=term-missing'])
    
    if args.fast:
        cmd.extend(['-m', 'not slow'])
    
    # Add common options
    cmd.extend([
        '--tb=short',  # Short traceback format
        '--strict-markers',  # Strict marker checking
        '--disable-warnings'  # Disable warnings for cleaner output
    ])
    
    # Run the tests
    success = run_command(cmd, "Pokemon Scanner Tests")
    
    if args.coverage and success:
        print("\n📊 Coverage report generated in htmlcov/ directory")
        print("   Open htmlcov/index.html in your browser to view detailed coverage")
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
