#!/usr/bin/env python3
"""
StatArb Gemini Test Runner
=========================

Main test runner for the StatArb Gemini testing framework.
Executes all available test suites and provides comprehensive reporting.

Usage:
    python testing_framework/run_all_tests.py [--test=TEST_NAME] [--category=CATEGORY]

Examples:
    # Run all tests
    python testing_framework/run_all_tests.py
    
    # Run specific test
    python testing_framework/run_all_tests.py --test=multi_strategy_backtest_real_data
    
    # Run tests by category
    python testing_framework/run_all_tests.py --category=multi_strategy

Author: Pro Quant Desk Trader
"""

import asyncio
import argparse
import logging
import sys
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from testing_framework import AVAILABLE_TESTS, TEST_CATEGORIES

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f'testing_framework/test_run_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)

class TestRunner:
    """Main test runner for StatArb Gemini testing framework"""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = None
        self.end_time = None
        
    def run_single_test(self, test_name: str, test_info: Dict) -> bool:
        """Run a single test and return success status"""
        logger.info(f"🚀 Running test: {test_name}")
        logger.info(f"   Description: {test_info['description']}")
        logger.info(f"   Category: {test_info['category']}")
        
        test_file = Path("testing_framework") / test_info['file']
        
        if not test_file.exists():
            logger.error(f"❌ Test file not found: {test_file}")
            return False
        
        try:
            # Run the test
            start_time = datetime.now()
            result = subprocess.run(
                [sys.executable, str(test_file)],
                capture_output=True,
                text=True,
                timeout=1800  # 30 minute timeout
            )
            end_time = datetime.now()
            
            execution_time = (end_time - start_time).total_seconds()
            
            if result.returncode == 0:
                logger.info(f"✅ Test {test_name} PASSED ({execution_time:.1f}s)")
                self.test_results[test_name] = {
                    'status': 'PASSED',
                    'execution_time': execution_time,
                    'output': result.stdout[-1000:] if result.stdout else '',  # Last 1000 chars
                    'error': ''
                }
                return True
            else:
                logger.error(f"❌ Test {test_name} FAILED ({execution_time:.1f}s)")
                logger.error(f"   Error: {result.stderr}")
                self.test_results[test_name] = {
                    'status': 'FAILED',
                    'execution_time': execution_time,
                    'output': result.stdout[-1000:] if result.stdout else '',
                    'error': result.stderr[-1000:] if result.stderr else ''
                }
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"⏰ Test {test_name} TIMEOUT (exceeded 30 minutes)")
            self.test_results[test_name] = {
                'status': 'TIMEOUT',
                'execution_time': 1800,
                'output': '',
                'error': 'Test exceeded 30 minute timeout'
            }
            return False
        except Exception as e:
            logger.error(f"💥 Test {test_name} ERROR: {str(e)}")
            self.test_results[test_name] = {
                'status': 'ERROR',
                'execution_time': 0,
                'output': '',
                'error': str(e)
            }
            return False
    
    def run_tests(self, test_filter: Optional[str] = None, category_filter: Optional[str] = None) -> None:
        """Run tests based on filters"""
        self.start_time = datetime.now()
        
        logger.info("🎯 StatArb Gemini Test Runner Starting...")
        logger.info(f"   Start time: {self.start_time}")
        
        # Filter tests
        tests_to_run = {}
        
        if test_filter:
            if test_filter in AVAILABLE_TESTS:
                tests_to_run[test_filter] = AVAILABLE_TESTS[test_filter]
            else:
                logger.error(f"❌ Test '{test_filter}' not found")
                return
        elif category_filter:
            tests_to_run = {
                name: info for name, info in AVAILABLE_TESTS.items()
                if info['category'] == category_filter
            }
            if not tests_to_run:
                logger.error(f"❌ No tests found for category '{category_filter}'")
                return
        else:
            tests_to_run = AVAILABLE_TESTS
        
        logger.info(f"📋 Running {len(tests_to_run)} test(s):")
        for name, info in tests_to_run.items():
            logger.info(f"   • {name}: {info['description']}")
        
        # Run tests
        passed_tests = 0
        failed_tests = 0
        
        for test_name, test_info in tests_to_run.items():
            if self.run_single_test(test_name, test_info):
                passed_tests += 1
            else:
                failed_tests += 1
        
        self.end_time = datetime.now()
        total_time = (self.end_time - self.start_time).total_seconds()
        
        # Generate report
        self.generate_report(passed_tests, failed_tests, total_time)
    
    def generate_report(self, passed: int, failed: int, total_time: float) -> None:
        """Generate comprehensive test report"""
        logger.info("📊 GENERATING TEST REPORT...")
        
        total_tests = passed + failed
        success_rate = (passed / total_tests * 100) if total_tests > 0 else 0
        
        report = f"""
================================================================================
🎯 STATARB GEMINI TEST EXECUTION REPORT
================================================================================

📅 Execution Details:
   • Start Time: {self.start_time}
   • End Time: {self.end_time}
   • Total Duration: {total_time:.1f} seconds

📊 Test Results Summary:
   • Total Tests: {total_tests}
   • Passed: {passed} ✅
   • Failed: {failed} ❌
   • Success Rate: {success_rate:.1f}%

📋 Individual Test Results:
"""
        
        for test_name, result in self.test_results.items():
            status_icon = "✅" if result['status'] == 'PASSED' else "❌"
            report += f"""
   {status_icon} {test_name}:
      Status: {result['status']}
      Duration: {result['execution_time']:.1f}s
"""
            if result['error']:
                report += f"      Error: {result['error'][:200]}...\n"
        
        report += f"""
================================================================================
🎯 TEST EXECUTION COMPLETED - {'SUCCESS' if failed == 0 else 'ISSUES DETECTED'}
================================================================================
"""
        
        logger.info(report)
        
        # Save report to file
        report_file = f"testing_framework/test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w') as f:
            f.write(report)
        
        logger.info(f"📄 Report saved to: {report_file}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='StatArb Gemini Test Runner')
    parser.add_argument('--test', help='Run specific test by name')
    parser.add_argument('--category', help='Run tests by category')
    parser.add_argument('--list', action='store_true', help='List available tests')
    
    args = parser.parse_args()
    
    if args.list:
        print("📋 Available Tests:")
        for category, description in TEST_CATEGORIES.items():
            print(f"\n🏷️  Category: {category}")
            print(f"   {description}")
            
            category_tests = [name for name, info in AVAILABLE_TESTS.items() if info['category'] == category]
            for test_name in category_tests:
                test_info = AVAILABLE_TESTS[test_name]
                print(f"   • {test_name}: {test_info['description']}")
        return
    
    # Run tests
    runner = TestRunner()
    runner.run_tests(test_filter=args.test, category_filter=args.category)

if __name__ == "__main__":
    main()
