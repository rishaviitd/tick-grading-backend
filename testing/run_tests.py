#!/usr/bin/env python3
"""
Test runner script for TickAI Cloudinary integration tests

This script provides easy ways to run different types of tests:
- Unit tests only
- Integration tests only  
- All tests
- With coverage reporting
"""

import sys
import subprocess
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_tests(test_type="all", coverage=False, verbose=False):
    """Run tests based on type and options"""
    
    # Base pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Add test type filters
    if test_type == "unit":
        cmd.extend(["-m", "unit"])
    elif test_type == "integration":
        cmd.extend(["-m", "integration"])
    elif test_type == "cloudinary":
        cmd.extend(["test_cloudinary_integration.py"])
    elif test_type == "database":
        cmd.extend(["test_cloudinary_save.py"])
    
    # Add coverage if requested
    if coverage:
        cmd.extend([
            "--cov=app.question_parsing",
            "--cov=database",
            "--cov-report=html:htmlcov",
            "--cov-report=term-missing"
        ])
    
    # Add verbose output
    if verbose:
        cmd.append("-v")
    
    # Add test directory
    cmd.append("testing/")
    
    print(f"Running tests: {' '.join(cmd)}")
    print("=" * 60)
    
    try:
        result = subprocess.run(cmd, check=True)
        print("=" * 60)
        print("✅ All tests passed!")
        return True
    except subprocess.CalledProcessError as e:
        print("=" * 60)
        print(f"❌ Tests failed with exit code: {e.returncode}")
        return False


def main():
    """Main function to parse arguments and run tests"""
    parser = argparse.ArgumentParser(description="Run TickAI Cloudinary integration tests")
    
    parser.add_argument(
        "--type", 
        choices=["all", "unit", "integration", "cloudinary", "database"],
        default="all",
        help="Type of tests to run"
    )
    
    parser.add_argument(
        "--coverage", 
        action="store_true",
        help="Generate coverage report"
    )
    
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "--install-deps", 
        action="store_true",
        help="Install test dependencies"
    )
    
    args = parser.parse_args()
    
    # Install dependencies if requested
    if args.install_deps:
        print("📦 Installing test dependencies...")
        subprocess.run([
            "pip", "install", "-r", "testing/requirements-test.txt"
        ], check=True)
        print("✅ Dependencies installed!")
    
    # Run tests
    success = run_tests(args.type, args.coverage, args.verbose)
    
    if success:
        print("🎉 Test execution completed successfully!")
        sys.exit(0)
    else:
        print("💥 Test execution failed!")
        sys.exit(1)


if __name__ == "__main__":
    main() 