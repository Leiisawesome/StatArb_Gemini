#!/usr/bin/env python3
"""
StatArb Gemini Test Runner - Root Level Entry Point
==================================================

Simple entry point to run tests from the project root.
Delegates to the comprehensive testing framework.

Usage:
    python run_tests.py [arguments]

Examples:
    # Run all tests
    python run_tests.py
    
    # Run specific test
    python run_tests.py --test=multi_strategy_backtest_real_data
    
    # List available tests
    python run_tests.py --list

Author: Pro Quant Desk Trader
"""

import sys
import subprocess
from pathlib import Path

def main():
    """Delegate to the main test runner in testing_framework/"""
    test_runner_path = Path("testing_framework") / "run_all_tests.py"
    
    if not test_runner_path.exists():
        print("❌ Testing framework not found!")
        print("   Expected: testing_framework/run_all_tests.py")
        sys.exit(1)
    
    # Pass all arguments to the main test runner
    cmd = [sys.executable, str(test_runner_path)] + sys.argv[1:]
    
    try:
        result = subprocess.run(cmd)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\n⏹️  Test execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"💥 Error running tests: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
