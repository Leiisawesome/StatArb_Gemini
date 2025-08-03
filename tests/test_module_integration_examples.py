#!/usr/bin/env python3
"""
Test Module Integration Examples
================================

Test script to validate the module integration examples
and ensure they meet all success criteria.

Author: Infrastructure Integration Team
Date: 2025-01-27
"""

import asyncio
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from examples.module_integration_examples import ModuleIntegrationExamples
from core_structure.infrastructure.system_orchestrator import MessageType

class TestModuleIntegrationExamples:
    """Test class for module integration examples"""
    
    def __init__(self):
        self.examples = None
        self.test_results = []
    
    async def run_all_tests(self):
        """Run all validation tests for module integration examples"""
        print("🧪 Testing Module Integration Examples...")
        print("=" * 60)
        
        # Test 1: Verify examples can be imported
        await self._test_examples_import()
        
        # Test 2: Verify orchestrator setup
        await self._test_orchestrator_setup()
        
        # Test 3: Verify module registration
        await self._test_module_registration()
        
        # Test 4: Verify message handling
        await self._test_message_handling()
        
        # Test 5: Verify system health (with delay for health checks)
        await asyncio.sleep(2.0)  # Wait for health checks to run
        await self._test_system_health()
        
        # Test 6: Verify integration points
        await self._test_integration_points()
        
        # Test 7: Verify performance metrics
        await self._test_performance_metrics()
        
        # Print results
        self._print_test_results()
    
    async def _test_examples_import(self):
        """Test that examples can be imported successfully"""
        test_name = "Examples Import Test"
        print(f"Running: {test_name}")
        
        try:
            # This test verifies the import worked (already done above)
            assert ModuleIntegrationExamples is not None
            self._record_success(test_name, "Examples module imported successfully")
        except Exception as e:
            self._record_failure(test_name, f"Import failed: {str(e)}")
    
    async def _test_orchestrator_setup(self):
        """Test that orchestrator can be set up successfully"""
        test_name = "Orchestrator Setup Test"
        print(f"Running: {test_name}")
        
        try:
            self.examples = ModuleIntegrationExamples()
            await self.examples.setup_orchestrator()
            
            assert self.examples.orchestrator is not None
            assert self.examples.orchestrator._running is True
            assert len(self.examples.orchestrator.modules) == 4
            
            self._record_success(test_name, "Orchestrator setup completed successfully")
        except Exception as e:
            self._record_failure(test_name, f"Setup failed: {str(e)}")
    
    async def _test_module_registration(self):
        """Test that all modules are registered correctly"""
        test_name = "Module Registration Test"
        print(f"Running: {test_name}")
        
        try:
            expected_modules = ["signal_generator", "execution_engine", "analytics_engine", "risk_manager"]
            
            for module_name in expected_modules:
                module_status = self.examples.orchestrator.get_module_status(module_name)
                assert module_status is not None, f"Module {module_name} not found"
                assert module_status.status.value in ["registered", "healthy"], f"Module {module_name} not properly registered"
            
            self._record_success(test_name, f"All {len(expected_modules)} modules registered successfully")
        except Exception as e:
            self._record_failure(test_name, f"Registration test failed: {str(e)}")
    
    async def _test_message_handling(self):
        """Test that message handling works correctly"""
        test_name = "Message Handling Test"
        print(f"Running: {test_name}")
        
        try:
            # Send a test message
            await self.examples.orchestrator.send_message(
                source_module="test_system",
                target_module="signal_generator",
                message_type=MessageType.COMMAND,
                payload={
                    'action': 'generate_signal',
                    'market_data': {'symbol': 'TEST', 'price': 100.0, 'volume': 1000000},
                    'portfolio_state': {'total_exposure': 50000, 'max_exposure': 100000, 'cash_available': 75000}
                }
            )
            
            # Wait for processing
            await asyncio.sleep(1.0)
            
            # Verify message was processed
            assert len(self.examples.signal_messages) > 0, "No signal messages received"
            
            self._record_success(test_name, "Message handling working correctly")
        except Exception as e:
            self._record_failure(test_name, f"Message handling failed: {str(e)}")
    
    async def _test_system_health(self):
        """Test that system health monitoring works"""
        test_name = "System Health Test"
        print(f"Running: {test_name}")
        
        try:
            system_health = self.examples.orchestrator.get_system_health()
            
            assert system_health['total_modules'] == 4, "Wrong number of modules"
            assert system_health['healthy_modules'] == 4, "Not all modules are healthy"
            assert system_health['health_percentage'] == 100.0, "System health not 100%"
            assert system_health['system_status'] == "healthy", "System status not healthy"
            
            self._record_success(test_name, f"System health: {system_health['health_percentage']:.1f}%")
        except Exception as e:
            self._record_failure(test_name, f"Health test failed: {str(e)}")
    
    async def _test_integration_points(self):
        """Test that integration points are correctly mapped"""
        test_name = "Integration Points Test"
        print(f"Running: {test_name}")
        
        try:
            integration_points = self.examples.orchestrator.get_integration_points()
            
            expected_points = ["execution_engine", "risk_management", "analytics", "signal_generation"]
            
            for point in expected_points:
                assert point in integration_points, f"Integration point {point} not found"
                assert len(integration_points[point]) > 0, f"No modules connected to {point}"
            
            self._record_success(test_name, f"All {len(expected_points)} integration points mapped correctly")
        except Exception as e:
            self._record_failure(test_name, f"Integration points test failed: {str(e)}")
    
    async def _test_performance_metrics(self):
        """Test that performance metrics are being collected"""
        test_name = "Performance Metrics Test"
        print(f"Running: {test_name}")
        
        try:
            # Send multiple messages to test performance
            start_time = time.time()
            
            for i in range(10):
                await self.examples.orchestrator.send_message(
                    source_module=f"perf_test_{i}",
                    target_module="signal_generator",
                    message_type=MessageType.COMMAND,
                    payload={
                        'action': 'generate_signal',
                        'market_data': {'symbol': 'PERF', 'price': 100.0 + i, 'volume': 1000000},
                        'portfolio_state': {'total_exposure': 50000, 'max_exposure': 100000, 'cash_available': 75000}
                    }
                )
            
            # Wait for processing
            await asyncio.sleep(1.0)
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # Verify performance metrics
            system_health = self.examples.orchestrator.get_system_health()
            
            assert system_health['performance_metrics']['total_messages'] > 0, "No messages processed"
            assert processing_time < 5.0, f"Processing too slow: {processing_time:.2f}s"
            
            throughput = system_health['performance_metrics']['total_messages'] / system_health['uptime']
            assert throughput > 1.0, f"Throughput too low: {throughput:.1f} msg/s"
            
            self._record_success(test_name, f"Performance: {throughput:.1f} msg/s, {processing_time:.2f}s processing time")
        except Exception as e:
            self._record_failure(test_name, f"Performance test failed: {str(e)}")
    
    def _record_success(self, test_name: str, message: str):
        """Record a successful test"""
        self.test_results.append({
            "name": test_name,
            "status": "PASSED",
            "message": message
        })
        print(f"✅ PASSED: {test_name}")
    
    def _record_failure(self, test_name: str, message: str):
        """Record a failed test"""
        self.test_results.append({
            "name": test_name,
            "status": "FAILED",
            "message": message
        })
        print(f"❌ FAILED: {test_name}")
    
    def _print_test_results(self):
        """Print test results summary"""
        print("\n" + "=" * 60)
        print("📊 MODULE INTEGRATION EXAMPLES TEST RESULTS")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["status"] == "PASSED")
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests / total_tests * 100):.1f}%")
        print()
        
        if failed_tests > 0:
            print("❌ FAILED TESTS:")
            for result in self.test_results:
                if result["status"] == "FAILED":
                    print(f"  - {result['name']}: {result['message']}")
            print()
        
        if passed_tests == total_tests:
            print("🎉 ALL TESTS PASSED! Module integration examples are working correctly.")
        else:
            print("⚠️  Some tests failed. Please review the errors above.")
        
        print("=" * 60)
        
        # Cleanup
        if self.examples and self.examples.orchestrator:
            asyncio.create_task(self.examples.orchestrator.stop())

async def main():
    """Main test function"""
    tester = TestModuleIntegrationExamples()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main()) 