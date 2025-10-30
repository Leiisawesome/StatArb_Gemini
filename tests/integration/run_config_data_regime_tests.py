#!/usr/bin/env python3
"""
Config + Data + Regime Integration Test Runner
==============================================

Comprehensive test runner for config + data + regime integration testing.
Executes the complete test suite with detailed reporting and validation.

Features:
- Test execution with detailed logging
- Performance benchmarking
- Test data generation
- Results validation and reporting
- Error analysis and debugging

Author: StatArb_Gemini Integration Testing
Phase: Integration Testing - Test Execution
"""

import asyncio
import logging
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

# Add core_engine to path
current_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(current_dir))

# Import test modules
from test_config_data_regime_final import FinalIntegrationTest
from test_data_generators import get_standard_test_data, get_known_regime_test_data

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('integration_test_results.log')
    ]
)

logger = logging.getLogger(__name__)

class IntegrationTestRunner:
    """
    Comprehensive integration test runner
    
    Executes config + data + regime integration tests with:
    - Detailed test execution
    - Performance monitoring
    - Error analysis
    - Results reporting
    """
    
    def __init__(self):
        self.test_results = {}
        self.performance_metrics = {}
        self.start_time = None
        self.end_time = None
        
    async def run_all_tests(self) -> Dict[str, Any]:
        """
        Run all integration tests
        
        Returns:
            Dict with test results and metrics
        """
        logger.info("🚀 Starting Config + Data + Regime Integration Tests")
        self.start_time = time.time()
        
        # Initialize test class
        test_instance = FinalIntegrationTest()
        
        # Test execution order (dependencies matter)
        test_methods = [
            ('config_loading', 'test_config_loading'),
            ('data_manager_init', 'test_data_manager_initialization'),
            ('regime_engine_init', 'test_regime_engine_initialization'),
            ('data_pipeline', 'test_data_processing_pipeline'),
            ('regime_detection', 'test_regime_detection'),
            ('indicators_regime', 'test_indicators_with_regime_awareness'),
            ('end_to_end', 'test_end_to_end_integration')
        ]
        
        # Execute tests
        for test_name, method_name in test_methods:
            await self._run_single_test(test_instance, test_name, method_name)
        
        self.end_time = time.time()
        
        # Generate final report
        report = self._generate_final_report()
        
        logger.info("✅ All integration tests completed")
        return report
    
    async def _run_single_test(
        self, 
        test_instance: FinalIntegrationTest,
        test_name: str,
        method_name: str
    ) -> None:
        """
        Run a single test method
        
        Args:
            test_instance: Test class instance
            test_name: Human-readable test name
            method_name: Method name to execute
        """
        logger.info(f"🧪 Running test: {test_name}")
        
        test_start_time = time.time()
        test_result = {
            'name': test_name,
            'method': method_name,
            'status': 'unknown',
            'error': None,
            'duration': 0.0,
            'details': {}
        }
        
        try:
            # Get test method
            test_method = getattr(test_instance, method_name)
            
            # Run test with timeout
            await asyncio.wait_for(test_method(), timeout=60.0)
            
            test_result['status'] = 'passed'
            logger.info(f"✅ {test_name} passed")
            
        except asyncio.TimeoutError:
            test_result['status'] = 'timeout'
            test_result['error'] = f"Test timed out after 60 seconds"
            logger.error(f"⏰ {test_name} timed out")
            
        except Exception as e:
            test_result['status'] = 'failed'
            test_result['error'] = str(e)
            logger.error(f"❌ {test_name} failed: {e}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
        
        finally:
            test_end_time = time.time()
            test_result['duration'] = test_end_time - test_start_time
            self.test_results[test_name] = test_result
    
    def _generate_final_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive test report
        
        Returns:
            Dict with complete test results
        """
        total_duration = self.end_time - self.start_time if self.end_time and self.start_time else 0
        
        # Calculate summary statistics
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results.values() if r['status'] == 'passed'])
        failed_tests = len([r for r in self.test_results.values() if r['status'] == 'failed'])
        timeout_tests = len([r for r in self.test_results.values() if r['status'] == 'timeout'])
        
        # Calculate performance metrics
        avg_test_duration = np.mean([r['duration'] for r in self.test_results.values()])
        total_test_duration = sum([r['duration'] for r in self.test_results.values()])
        
        report = {
            'summary': {
                'total_tests': total_tests,
                'passed': passed_tests,
                'failed': failed_tests,
                'timeout': timeout_tests,
                'success_rate': passed_tests / total_tests if total_tests > 0 else 0,
                'total_duration': total_duration,
                'avg_test_duration': avg_test_duration
            },
            'test_results': self.test_results,
            'performance_metrics': self.performance_metrics,
            'timestamp': datetime.now().isoformat(),
            'recommendations': self._generate_recommendations()
        }
        
        # Log summary
        logger.info("📊 Test Summary:")
        logger.info(f"   Total Tests: {total_tests}")
        logger.info(f"   Passed: {passed_tests}")
        logger.info(f"   Failed: {failed_tests}")
        logger.info(f"   Timeout: {timeout_tests}")
        logger.info(f"   Success Rate: {report['summary']['success_rate']:.1%}")
        logger.info(f"   Total Duration: {total_duration:.2f}s")
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """
        Generate recommendations based on test results
        
        Returns:
            List of recommendations
        """
        recommendations = []
        
        # Check for failed tests
        failed_tests = [name for name, result in self.test_results.items() 
                       if result['status'] == 'failed']
        
        if failed_tests:
            recommendations.append(f"Investigate failed tests: {', '.join(failed_tests)}")
        
        # Check for timeout tests
        timeout_tests = [name for name, result in self.test_results.items() 
                        if result['status'] == 'timeout']
        
        if timeout_tests:
            recommendations.append(f"Optimize slow tests: {', '.join(timeout_tests)}")
        
        # Check performance
        slow_tests = [name for name, result in self.test_results.items() 
                     if result['duration'] > 10.0]
        
        if slow_tests:
            recommendations.append(f"Consider performance optimization for: {', '.join(slow_tests)}")
        
        # Check success rate
        success_rate = len([r for r in self.test_results.values() if r['status'] == 'passed']) / len(self.test_results)
        if success_rate < 0.8:
            recommendations.append("Overall success rate is low - review test environment and dependencies")
        
        if not recommendations:
            recommendations.append("All tests passed successfully - system is ready for production")
        
        return recommendations
    
    def save_report(self, report: Dict[str, Any], filename: str = None) -> str:
        """
        Save test report to file
        
        Args:
            report: Test report dictionary
            filename: Output filename (optional)
            
        Returns:
            Path to saved report file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"integration_test_report_{timestamp}.json"
        
        import json
        report_path = Path(filename)
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"📄 Test report saved to: {report_path}")
        return str(report_path)


async def run_integration_tests() -> Dict[str, Any]:
    """
    Main function to run integration tests
    
    Returns:
        Test results dictionary
    """
    runner = IntegrationTestRunner()
    
    try:
        # Run all tests
        report = await runner.run_all_tests()
        
        # Save report
        report_path = runner.save_report(report)
        
        # Print final status
        success_rate = report['summary']['success_rate']
        if success_rate >= 0.9:
            logger.info("🎉 Integration tests PASSED with excellent results!")
        elif success_rate >= 0.7:
            logger.info("✅ Integration tests PASSED with good results")
        else:
            logger.warning("⚠️  Integration tests had issues - review results")
        
        return report
        
    except Exception as e:
        logger.error(f"💥 Test runner failed: {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        raise


def generate_test_data() -> None:
    """
    Generate test data for integration testing
    """
    logger.info("📊 Generating test data...")
    
    try:
        # Generate standard test data
        standard_data = get_standard_test_data()
        
        # Save to files
        test_data_dir = Path("tests/integration/test_data")
        test_data_dir.mkdir(exist_ok=True)
        
        for name, data in standard_data.items():
            if isinstance(data, dict):
                # Handle multi-symbol data (dict of DataFrames)
                for symbol, symbol_data in data.items():
                    filepath = test_data_dir / f"{name}_{symbol}.csv"
                    symbol_data.to_csv(filepath, index=False)
                    logger.info(f"   Generated {name}_{symbol}: {len(symbol_data)} rows")
            else:
                # Handle single DataFrame
                filepath = test_data_dir / f"{name}.csv"
                data.to_csv(filepath, index=False)
                logger.info(f"   Generated {name}: {len(data)} rows")
        
        # Generate known regime test data
        known_regime_data = get_known_regime_test_data()
        filepath = test_data_dir / "known_regime_validation.csv"
        known_regime_data.to_csv(filepath, index=False)
        logger.info(f"   Generated known regime data: {len(known_regime_data)} rows")
        
        logger.info("✅ Test data generation completed")
        
    except Exception as e:
        logger.error(f"❌ Test data generation failed: {e}")
        raise


def main():
    """
    Main entry point for test runner
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Config + Data + Regime Integration Test Runner")
    parser.add_argument("--generate-data", action="store_true", help="Generate test data only")
    parser.add_argument("--run-tests", action="store_true", help="Run integration tests")
    parser.add_argument("--all", action="store_true", help="Generate data and run tests")
    
    args = parser.parse_args()
    
    if args.generate_data or args.all:
        generate_test_data()
    
    if args.run_tests or args.all:
        # Run integration tests
        report = asyncio.run(run_integration_tests())
        
        # Exit with appropriate code
        success_rate = report['summary']['success_rate']
        if success_rate >= 0.8:
            sys.exit(0)  # Success
        else:
            sys.exit(1)  # Failure
    
    if not any([args.generate_data, args.run_tests, args.all]):
        # Default: run everything
        generate_test_data()
        report = asyncio.run(run_integration_tests())
        
        success_rate = report['summary']['success_rate']
        sys.exit(0 if success_rate >= 0.8 else 1)


if __name__ == "__main__":
    main()
