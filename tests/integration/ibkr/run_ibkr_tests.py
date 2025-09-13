#!/usr/bin/env python3
"""
IBKR Test Runner
===============

Comprehensive test runner for IBKR broker integration testing.
Provides multiple test options and comprehensive reporting.

Author: Professional Trading System Architecture
Version: 1.0.0 (IBKR Test Runner)
"""

import asyncio
import logging
import sys
import os
import argparse
from datetime import datetime

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from tests.integration.ibkr.ibkr_connection_diagnostics import run_diagnostics
from tests.integration.ibkr.ibkr_simple_test import run_simple_test
from tests.integration.ibkr.ibkr_real_test import run_ibkr_real_test

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IBKRTestRunner:
    """IBKR test runner with multiple test options"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.IBKRTestRunner")
        self.test_results = {}
    
    async def run_diagnostics(self):
        """Run connection diagnostics"""
        
        self.logger.info("🔍 Running IBKR Connection Diagnostics")
        self.logger.info("=" * 50)
        
        try:
            await run_diagnostics()
            self.test_results["diagnostics"] = "PASSED"
            self.logger.info("✅ Diagnostics completed successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Diagnostics failed: {e}")
            self.test_results["diagnostics"] = f"FAILED: {e}"
    
    async def run_simple_test(self):
        """Run simple connection test"""
        
        self.logger.info("🚀 Running IBKR Simple Connection Test")
        self.logger.info("=" * 50)
        
        try:
            await run_simple_test()
            self.test_results["simple_test"] = "PASSED"
            self.logger.info("✅ Simple test completed successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Simple test failed: {e}")
            self.test_results["simple_test"] = f"FAILED: {e}"
    
    async def run_comprehensive_test(self):
        """Run comprehensive test suite"""
        
        self.logger.info("🎯 Running IBKR Comprehensive Test Suite")
        self.logger.info("=" * 50)
        
        try:
            await run_ibkr_real_test()
            self.test_results["comprehensive_test"] = "PASSED"
            self.logger.info("✅ Comprehensive test completed successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Comprehensive test failed: {e}")
            self.test_results["comprehensive_test"] = f"FAILED: {e}"
    
    async def run_all_tests(self):
        """Run all available tests"""
        
        self.logger.info("🏆 Running All IBKR Tests")
        self.logger.info("=" * 50)
        
        # Run diagnostics first
        await self.run_diagnostics()
        
        # Run simple test
        await self.run_simple_test()
        
        # Run comprehensive test
        await self.run_comprehensive_test()
        
        # Generate summary
        self._generate_summary()
    
    def _generate_summary(self):
        """Generate test summary"""
        
        self.logger.info("\n📊 Test Summary")
        self.logger.info("=" * 50)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results.values() if r == "PASSED"])
        failed_tests = total_tests - passed_tests
        
        self.logger.info(f"Total Tests: {total_tests}")
        self.logger.info(f"Passed: {passed_tests}")
        self.logger.info(f"Failed: {failed_tests}")
        self.logger.info(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        self.logger.info("\nDetailed Results:")
        for test_name, result in self.test_results.items():
            status = "✅" if result == "PASSED" else "❌"
            self.logger.info(f"  {status} {test_name}: {result}")
        
        if failed_tests == 0:
            self.logger.info("\n🎉 All tests passed! IBKR integration is working correctly.")
        else:
            self.logger.info(f"\n⚠️ {failed_tests} test(s) failed. Please check the logs for details.")


async def main():
    """Main function with argument parsing"""
    
    parser = argparse.ArgumentParser(description="IBKR Test Runner")
    parser.add_argument(
        "--test",
        choices=["diagnostics", "simple", "comprehensive", "all"],
        default="all",
        help="Type of test to run (default: all)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    runner = IBKRTestRunner()
    
    print("🚀 IBKR Test Runner")
    print("=" * 50)
    print(f"Running test: {args.test}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 50)
    
    try:
        if args.test == "diagnostics":
            await runner.run_diagnostics()
        elif args.test == "simple":
            await runner.run_simple_test()
        elif args.test == "comprehensive":
            await runner.run_comprehensive_test()
        elif args.test == "all":
            await runner.run_all_tests()
        
        print("\n✅ Test execution completed")
        
    except KeyboardInterrupt:
        print("\n🛑 Test execution interrupted by user")
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
