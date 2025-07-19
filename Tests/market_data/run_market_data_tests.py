#!/usr/bin/env python3
"""
Market Data Module Test Runner
=============================

Comprehensive test runner for the market data module with:
- Selective test execution
- Performance benchmarking
- Coverage reporting
- Test result analysis
- CI/CD integration support

Usage:
    python run_market_data_tests.py                    # Run all tests
    python run_market_data_tests.py --unit            # Run only unit tests
    python run_market_data_tests.py --integration     # Run integration tests
    python run_market_data_tests.py --performance     # Run performance tests
    python run_market_data_tests.py --coverage        # Run with coverage
    python run_market_data_tests.py --verbose         # Verbose output
    python run_market_data_tests.py --fast            # Skip slow tests
"""

import argparse
import sys
import os
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Test configuration
from test_config import (
    TEST_ENVIRONMENT,
    PERFORMANCE_THRESHOLDS,
    INTEGRATION_TEST_CONFIG
)


class MarketDataTestRunner:
    """Test runner for market data module"""
    
    def __init__(self):
        self.test_dir = Path(__file__).parent
        self.project_root = self.test_dir.parent.parent
        self.results = {}
        self._check_dependencies()
        
    def run_tests(self, 
                  test_type: str = "all",
                  coverage: bool = False,
                  verbose: bool = False,
                  fast: bool = False) -> Dict:
        """
        Run tests based on specified parameters
        
        Args:
            test_type: Type of tests to run (all, unit, integration, performance)
            coverage: Whether to run with coverage reporting
            verbose: Verbose output
            fast: Skip slow tests
            
        Returns:
            Dictionary with test results
        """
        print(f"🚀 Running Market Data Module Tests")
        print(f"Test Type: {test_type}")
        print(f"Coverage: {coverage}")
        print(f"Verbose: {verbose}")
        print(f"Fast Mode: {fast}")
        print("=" * 60)
        
        start_time = time.time()
        
        try:
            if test_type == "all":
                self._run_all_tests(coverage, verbose, fast)
            elif test_type == "unit":
                self._run_unit_tests(coverage, verbose)
            elif test_type == "integration":
                self._run_integration_tests(coverage, verbose)
            elif test_type == "performance":
                self._run_performance_tests(verbose)
            else:
                raise ValueError(f"Unknown test type: {test_type}")
                
        except Exception as e:
            print(f"❌ Test execution failed: {e}")
            self.results['error'] = str(e)
            return self.results
        
        end_time = time.time()
        self.results['total_time'] = end_time - start_time
        
        self._print_summary()
        return self.results
    
    def _run_all_tests(self, coverage: bool, verbose: bool, fast: bool):
        """Run all test suites"""
        print("📊 Running All Tests")
        
        # Unit tests
        print("\n1️⃣ Unit Tests")
        unit_result = self._run_unit_tests(coverage, verbose)
        
        # Integration tests (if enabled)
        if INTEGRATION_TEST_CONFIG['database_tests']['enabled']:
            print("\n2️⃣ Integration Tests")
            integration_result = self._run_integration_tests(coverage, verbose)
        else:
            print("\n⏭️ Integration tests disabled")
            integration_result = {'skipped': True}
        
        # Performance tests (if not in fast mode)
        if not fast and INTEGRATION_TEST_CONFIG['performance_tests']['enabled']:
            print("\n3️⃣ Performance Tests")
            performance_result = self._run_performance_tests(verbose)
        else:
            print("\n⏭️ Performance tests skipped")
            performance_result = {'skipped': True}
        
        self.results.update({
            'unit': unit_result,
            'integration': integration_result,
            'performance': performance_result
        })
    
    def _run_unit_tests(self, coverage: bool, verbose: bool) -> Dict:
        """Run unit tests"""
        test_files = [
            "test_market_data_comprehensive.py",
            "test_data_manager.py",
            "test_feeds.py"
        ]
        
        cmd = self._build_pytest_command(test_files, coverage, verbose)
        cmd.extend(["-m", "not integration and not performance"])
        
        result = self._execute_pytest(cmd, "Unit Tests")
        return result
    
    def _run_integration_tests(self, coverage: bool, verbose: bool) -> Dict:
        """Run integration tests"""
        # Check if ClickHouse is available
        if not self._check_clickhouse_availability():
            print("⚠️ ClickHouse not available, skipping integration tests")
            return {'skipped': True, 'reason': 'ClickHouse not available'}
        
        test_files = [
            "test_market_data_comprehensive.py",
            "test_data_manager.py"
        ]
        
        cmd = self._build_pytest_command(test_files, coverage, verbose)
        cmd.extend(["-m", "integration"])
        
        result = self._execute_pytest(cmd, "Integration Tests")
        return result
    
    def _run_performance_tests(self, verbose: bool) -> Dict:
        """Run performance tests"""
        print("⚡ Running Performance Tests")
        
        test_files = [
            "test_data_manager.py",
            "test_feeds.py"
        ]
        
        cmd = self._build_pytest_command(test_files, False, verbose)
        cmd.extend(["-m", "performance"])
        
        result = self._execute_pytest(cmd, "Performance Tests")
        
        # Check performance thresholds
        self._check_performance_thresholds(result)
        
        return result
    
    def _build_pytest_command(self, test_files: List[str], coverage: bool, verbose: bool) -> List[str]:
        """Build pytest command"""
        cmd = [str(self.project_root / "venv/bin/python"), "-m", "pytest"]

        # Add test files
        for test_file in test_files:
            file_path = self.test_dir / test_file
            if file_path.exists():
                cmd.append(str(file_path))

        # Add options
        if verbose:
            cmd.append("-v")

        if coverage:
            cmd.extend([
                "--cov=core_structure.market_data",
                "--cov-report=html",
                "--cov-report=term-missing"
            ])

        # Add output formatting
        cmd.extend([
            "--tb=short",
            "--show-capture=no"
        ])

        return cmd
    
    def _execute_pytest(self, cmd: List[str], test_name: str) -> Dict:
        """Execute pytest command and capture results"""
        print(f"Running: {' '.join(cmd)}")
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            end_time = time.time()
            
            test_result = {
                'name': test_name,
                'duration': end_time - start_time,
                'return_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'success': result.returncode == 0
            }
            
            # Parse pytest output for test counts
            test_result.update(self._parse_pytest_output(result.stdout))
            
            if test_result['success']:
                print(f"✅ {test_name} completed successfully")
            else:
                print(f"❌ {test_name} failed")
                if result.stderr:
                    print(f"Error: {result.stderr[:500]}...")
            
            return test_result
            
        except subprocess.TimeoutExpired:
            print(f"⏰ {test_name} timed out")
            return {
                'name': test_name,
                'success': False,
                'error': 'timeout',
                'duration': 300
            }
        except Exception as e:
            print(f"❌ Error running {test_name}: {e}")
            return {
                'name': test_name,
                'success': False,
                'error': str(e),
                'duration': 0
            }
    
    def _parse_pytest_output(self, output: str) -> Dict:
        """Parse pytest output to extract test statistics"""
        stats = {
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'errors': 0,
            'warnings': 0
        }
        
        # Look for test result summary
        lines = output.split('\n')
        for line in lines:
            if ('passed' in line or 'failed' in line or 'skipped' in line) and '=' in line:
                # Parse line like "5 passed, 2 failed, 1 skipped in 2.34s"
                # Skip lines that are just formatting (with many = characters)
                if line.count('=') > 10:
                    continue
                    
                parts = line.split(',')
                for part in parts:
                    part = part.strip()
                    if 'passed' in part and part.split()[0].isdigit():
                        stats['passed'] = int(part.split()[0])
                    elif 'failed' in part and part.split()[0].isdigit():
                        stats['failed'] = int(part.split()[0])
                    elif 'skipped' in part and part.split()[0].isdigit():
                        stats['skipped'] = int(part.split()[0])
                    elif 'error' in part and part.split()[0].isdigit():
                        stats['errors'] = int(part.split()[0])
                break
        
        return stats
    
    def _check_clickhouse_availability(self) -> bool:
        """Check if ClickHouse is available for testing"""
        try:
            # Try to import and connect
            sys.path.append(str(self.project_root))
            from Tests.ClickHouse_Manager.clickhouse_manager import ClickHouseManager
            
            config_file = self.project_root / "Tests" / "ClickHouse_Manager" / "configs" / "clickhouse_config.json"
            if config_file.exists():
                manager = ClickHouseManager(str(config_file))
                return True
            else:
                return False
                
        except Exception as e:
            print(f"ClickHouse check failed: {e}")
            return False
    
    def _check_performance_thresholds(self, result: Dict):
        """Check if performance tests meet thresholds"""
        print("📈 Checking Performance Thresholds")
        
        duration = result.get('duration', 0)
        if duration > PERFORMANCE_THRESHOLDS['max_query_time_seconds']:
            print(f"⚠️ Performance test duration ({duration:.2f}s) exceeds threshold ({PERFORMANCE_THRESHOLDS['max_query_time_seconds']}s)")
        else:
            print(f"✅ Performance test duration ({duration:.2f}s) within threshold")
    
    def _print_summary(self):
        """Print test execution summary"""
        print("\n" + "=" * 60)
        print("📋 TEST EXECUTION SUMMARY")
        print("=" * 60)
        
        total_time = self.results.get('total_time', 0)
        print(f"Total Execution Time: {total_time:.2f} seconds")
        
        # Summary by test type
        for test_type, result in self.results.items():
            if test_type == 'total_time':
                continue
                
            if isinstance(result, dict):
                if result.get('skipped'):
                    print(f"{test_type.title()}: ⏭️ SKIPPED")
                elif result.get('success', False):
                    passed = result.get('passed', 0)
                    failed = result.get('failed', 0)
                    skipped = result.get('skipped', 0)
                    duration = result.get('duration', 0)
                    print(f"{test_type.title()}: ✅ PASSED ({passed} passed, {failed} failed, {skipped} skipped) in {duration:.2f}s")
                else:
                    print(f"{test_type.title()}: ❌ FAILED")
        
        # Overall status
        all_success = all(
            result.get('success', True) or result.get('skipped', False)
            for result in self.results.values()
            if isinstance(result, dict)
        )
        
        if all_success:
            print("\n🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
        else:
            print("\n💥 SOME TESTS FAILED!")
        
        print("=" * 60)
    
    def save_results(self, output_file: Optional[str] = None):
        """Save test results to file"""
        if output_file is None:
            output_file = self.test_dir / f"test_results_{int(time.time())}.json"
        
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"📄 Results saved to: {output_file}")
    
    def _check_dependencies(self):
        """Check and report on dependencies"""
        print("🔍 Checking Market Data Dependencies...")
        
        # Core dependencies (required)
        core_deps = ['pandas', 'numpy', 'requests']
        missing_core = []
        
        for dep in core_deps:
            try:
                __import__(dep)
                print(f"✅ {dep} available")
            except ImportError:
                missing_core.append(dep)
                print(f"❌ {dep} missing (REQUIRED)")
        
        # Optional dependencies for DataProcessor
        optional_deps = ['ta', 'sklearn', 'scipy']
        missing_optional = []
        
        for dep in optional_deps:
            try:
                __import__(dep)
                print(f"✅ {dep} available")
            except ImportError:
                missing_optional.append(dep)
                print(f"⚠️  {dep} missing (optional - for DataProcessor)")
        
        # Check market_data module availability
        try:
            sys.path.append(str(self.project_root))
            from core_structure.market_data import DATA_PROCESSOR_AVAILABLE
            print(f"📊 DATA_PROCESSOR_AVAILABLE: {DATA_PROCESSOR_AVAILABLE}")
        except ImportError as e:
            print(f"❌ Cannot import market_data module: {e}")
        
        if missing_core:
            print(f"\n💥 CRITICAL: Missing required dependencies: {missing_core}")
            print("Install with: pip install " + " ".join(missing_core))
        
        if missing_optional:
            print(f"\n⚠️  Optional dependencies missing: {missing_optional}")
            print("DataProcessor features will be limited. Install with:")
            print("pip install " + " ".join(missing_optional))
        
        print()
    
    def install_dependencies(self, include_optional: bool = False):
        """Install missing dependencies"""
        print("📦 Installing Dependencies...")
        
        # Core dependencies
        core_packages = ['pandas', 'numpy', 'requests', 'pytest']
        
        # Optional dependencies for DataProcessor
        optional_packages = ['ta', 'scikit-learn', 'scipy']
        
        packages_to_install = core_packages.copy()
        if include_optional:
            packages_to_install.extend(optional_packages)
        
        for package in packages_to_install:
            try:
                print(f"Installing {package}...")
                result = subprocess.run(
                    [sys.executable, '-m', 'pip', 'install', package],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                if result.returncode == 0:
                    print(f"✅ {package} installed successfully")
                else:
                    print(f"❌ Failed to install {package}: {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                print(f"⏰ Timeout installing {package}")
            except Exception as e:
                print(f"❌ Error installing {package}: {e}")
        
        print("📦 Dependency installation completed\n")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Market Data Module Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Run all tests
  %(prog)s --unit            # Run only unit tests
  %(prog)s --integration     # Run integration tests
  %(prog)s --performance     # Run performance tests
  %(prog)s --coverage        # Run with coverage
  %(prog)s --verbose         # Verbose output
  %(prog)s --fast            # Skip slow tests
        """
    )
    
    parser.add_argument('--unit', action='store_true', help='Run unit tests only')
    parser.add_argument('--integration', action='store_true', help='Run integration tests only')
    parser.add_argument('--performance', action='store_true', help='Run performance tests only')
    parser.add_argument('--coverage', action='store_true', help='Run with coverage reporting')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--fast', action='store_true', help='Skip slow tests')
    parser.add_argument('--save-results', help='Save results to specified file')
    parser.add_argument('--install-deps', action='store_true', help='Install missing dependencies')
    parser.add_argument('--install-optional', action='store_true', help='Install optional dependencies (ta, sklearn, etc.)')
    parser.add_argument('--check-deps', action='store_true', help='Only check dependencies, do not run tests')
    
    args = parser.parse_args()
    
    # Initialize runner (this will check dependencies)
    runner = MarketDataTestRunner()
    
    # Handle dependency management commands
    if args.check_deps:
        print("🎯 Dependency check completed.")
        sys.exit(0)
    
    if args.install_deps or args.install_optional:
        runner.install_dependencies(include_optional=args.install_optional)
        if not (args.unit or args.integration or args.performance):
            print("📦 Dependencies installed. Add test flags to run tests.")
            sys.exit(0)
    
    # Determine test type
    if args.unit:
        test_type = "unit"
    elif args.integration:
        test_type = "integration"
    elif args.performance:
        test_type = "performance"
    else:
        test_type = "all"
    
    # Run tests
    runner = MarketDataTestRunner()
    runner = MarketDataTestRunner()
    results = runner.run_tests(
        test_type=test_type,
        coverage=args.coverage,
        verbose=args.verbose,
        fast=args.fast
    )
    
    # Save results if requested
    if args.save_results:
        runner.save_results(args.save_results)
    
    # Exit with appropriate code
    all_success = all(
        result.get('success', True) or result.get('skipped', False)
        for result in results.values()
        if isinstance(result, dict)
    )
    
    sys.exit(0 if all_success else 1)


if __name__ == "__main__":
    main()
