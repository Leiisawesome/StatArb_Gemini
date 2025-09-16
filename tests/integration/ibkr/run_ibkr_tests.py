#!/usr/bin/env python3
"""
IBKR Test Runner
===============

Streamlined test runner for essential IBKR broker integration testing.
Provides clean, focused test options:

- verification: Quick connection verification utility
- simple: Basic IBKRClient connection and functionality test
- validation: Comprehensive IBKRClient validation with real account data
- all: Run all essential tests

Author: Professional Trading System Architecture
Version: 2.0.0 (Streamlined Test Runner)
"""

import asyncio
import logging
import sys
import os
import argparse
from datetime import datetime

# Add the project root to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.insert(0, project_root)

from tests.integration.ibkr.ibkr_simple_test import run_simple_test
from tests.integration.ibkr.ibkr_client_validation_test import run_validation_test
from tests.integration.ibkr.ibkr_connection_verification import verify_ibkr_connection

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
    
    async def run_verification(self):
        """Run connection verification utility"""
        
        self.logger.info("🔍 Running IBKR Connection Verification")
        self.logger.info("=" * 50)
        
        try:
            await verify_ibkr_connection()
            self.test_results["verification"] = "PASSED"
            self.logger.info("✅ Connection verification completed successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Connection verification failed: {e}")
            self.test_results["verification"] = f"FAILED: {e}"
    
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
    
    async def run_validation_test(self):
        """Run IBKRClient validation test"""
        
        self.logger.info("🔍 Running IBKRClient Validation Test")
        self.logger.info("=" * 50)
        
        try:
            result = await run_validation_test()
            if result == 0:
                self.test_results["validation_test"] = "PASSED"
                self.logger.info("✅ Validation test completed successfully")
            else:
                self.test_results["validation_test"] = "FAILED: Non-zero exit code"
                self.logger.error("❌ Validation test failed")
            
        except Exception as e:
            self.logger.error(f"❌ Validation test failed: {e}")
            self.test_results["validation_test"] = f"FAILED: {e}"
    
    async def run_all_tests(self):
        """Run all available tests"""
        
        self.logger.info("🏆 Running All IBKR Tests")
        self.logger.info("=" * 50)
        
        # Run verification first
        await self.run_verification()
        
        # Run simple test
        await self.run_simple_test()
        
        # Run validation test
        await self.run_validation_test()
        await self.run_validation_test()
        
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
        choices=["verification", "simple", "validation", "all"],
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
        if args.test == "verification":
            await runner.run_verification()
        elif args.test == "simple":
            await runner.run_simple_test()
        elif args.test == "validation":
            await runner.run_validation_test()
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
