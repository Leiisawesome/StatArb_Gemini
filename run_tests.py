#!/usr/bin/env python3
"""
StatArb Gemini Test Runner
=========================

Comprehensive test runner for the StatArb Gemini trading system.
Provides different test execution modes and reporting options.
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path
from datetime import datetime


def run_command(cmd, description=""):
    """Run a command and handle output"""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"\n✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {description} failed with exit code {e.returncode}")
        return False
    except FileNotFoundError:
        print(f"\n❌ Command not found: {cmd[0]}")
        print("Make sure pytest is installed: pip install pytest")
        return False


def main():
    parser = argparse.ArgumentParser(description="StatArb Gemini Test Runner")
    
    # Test selection arguments
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--performance", action="store_true", help="Run performance tests only")
    parser.add_argument("--all", action="store_true", help="Run all tests (default)")
    parser.add_argument("--fast", action="store_true", help="Skip slow tests")
    
    # Output options
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--quiet", "-q", action="store_true", help="Quiet output")
    parser.add_argument("--no-cov", action="store_true", help="Skip coverage reporting")
    parser.add_argument("--html-report", action="store_true", help="Generate HTML coverage report")
    
    # Test filtering
    parser.add_argument("--pattern", "-k", help="Run tests matching pattern")
    parser.add_argument("--file", help="Run specific test file")
    
    # Environment options
    parser.add_argument("--env", default="test", help="Test environment (default: test)")
    parser.add_argument("--parallel", "-n", type=int, help="Run tests in parallel (requires pytest-xdist)")
    
    args = parser.parse_args()
    
    # Set up environment
    os.environ["TRADING_ENV"] = args.env
    os.environ["PYTHONPATH"] = str(Path.cwd())
    
    # Build pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Test selection
    if args.unit:
        cmd.extend(["tests/unit/"])
        test_type = "Unit Tests"
    elif args.integration:
        cmd.extend(["tests/integration/"])
        test_type = "Integration Tests"
    elif args.performance:
        cmd.extend(["tests/performance/"])
        test_type = "Performance Tests"
    elif args.file:
        cmd.extend([args.file])
        test_type = f"Tests in {args.file}"
    else:
        cmd.extend(["tests/"])
        test_type = "All Tests"
    
    # Output options
    if args.verbose:
        cmd.extend(["-v", "-s"])
    elif args.quiet:
        cmd.extend(["-q"])
    
    # Coverage options
    if not args.no_cov and not args.performance:
        cmd.extend([
            "--cov=core_structure",
            "--cov-report=term-missing"
        ])
        
        if args.html_report:
            cmd.extend(["--cov-report=html:htmlcov"])
    
    # Test filtering
    if args.pattern:
        cmd.extend(["-k", args.pattern])
    
    if args.fast:
        cmd.extend(["-m", "not slow"])
    
    # Parallel execution
    if args.parallel:
        cmd.extend(["-n", str(args.parallel)])
    
    # Additional pytest options
    cmd.extend([
        "--tb=short",
        "--durations=10",
        "--color=yes"
    ])
    
    # Run tests
    print(f"🧪 StatArb Gemini Test Suite")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Running: {test_type}")
    print(f"🌍 Environment: {args.env}")
    
    success = run_command(cmd, f"Running {test_type}")
    
    if success:
        print(f"\n🎉 All tests passed!")
        
        if args.html_report and not args.no_cov:
            print(f"📊 Coverage report available at: htmlcov/index.html")
    else:
        print(f"\n💥 Some tests failed!")
        sys.exit(1)


def run_quick_tests():
    """Run a quick subset of tests for development"""
    cmd = [
        "python", "-m", "pytest",
        "tests/unit/test_config.py",
        "tests/unit/test_engines.py::TestTradingEngine::test_engine_initialization",
        "tests/integration/test_system_workflows.py::TestSystemLifecycle::test_system_creation_and_startup",
        "-v", "--tb=short"
    ]
    
    return run_command(cmd, "Running Quick Development Tests")


def run_ci_tests():
    """Run tests suitable for CI/CD pipeline"""
    cmd = [
        "python", "-m", "pytest",
        "tests/",
        "-m", "not slow and not performance",
        "--cov=core_structure",
        "--cov-report=xml",
        "--cov-report=term",
        "--cov-fail-under=70",
        "--tb=short",
        "--durations=10"
    ]
    
    return run_command(cmd, "Running CI/CD Tests")


def run_performance_suite():
    """Run comprehensive performance test suite"""
    cmd = [
        "python", "-m", "pytest",
        "tests/performance/",
        "-v",
        "--tb=short",
        "--durations=0"
    ]
    
    return run_command(cmd, "Running Performance Test Suite")


if __name__ == "__main__":
    # Check if specific test mode requested via script name or arguments
    script_name = Path(sys.argv[0]).stem
    
    if len(sys.argv) == 1:
        # No arguments, show help
        main()
    elif "quick" in script_name or (len(sys.argv) == 2 and sys.argv[1] == "quick"):
        success = run_quick_tests()
        sys.exit(0 if success else 1)
    elif "ci" in script_name or (len(sys.argv) == 2 and sys.argv[1] == "ci"):
        success = run_ci_tests()
        sys.exit(0 if success else 1)
    elif "perf" in script_name or (len(sys.argv) == 2 and sys.argv[1] == "perf"):
        success = run_performance_suite()
        sys.exit(0 if success else 1)
    else:
        main()
