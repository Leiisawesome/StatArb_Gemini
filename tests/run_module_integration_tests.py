#!/usr/bin/env python3
"""
Module Integration Test Runner
==============================

Standalone test runner for module integration tests.
Runs integration tests without requiring pytest-asyncio configuration.

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

from core_structure.infrastructure.system_orchestrator import (
    SystemOrchestrator,
    OrchestrationConfig,
    ModuleStatus,
    MessageType
)

class ModuleIntegrationTestRunner:
    """Standalone test runner for module integration tests"""
    
    def __init__(self):
        self.test_results = []
        self.passed_tests = 0
        self.failed_tests = 0
    
    async def run_all_tests(self):
        """Run all module integration tests"""
        print("🚀 Starting Module Integration Tests...")
        print("=" * 60)
        
        # Test scenarios
        await self._test_signal_generation_to_execution_engine_integration()
        await self._test_multi_module_broadcast_integration()
        await self._test_health_monitoring_integration()
        await self._test_metrics_collection_integration()
        await self._test_error_handling_integration()
        await self._test_performance_tracking_integration()
        await self._test_integration_points_mapping()
        await self._test_high_message_volume_integration()
        await self._test_concurrent_module_registration()
        
        # Print results
        self._print_results()
    
    async def _test_signal_generation_to_execution_engine_integration(self):
        """Test integration between signal generation and execution engine"""
        test_name = "Signal Generation to Execution Engine Integration"
        print(f"Running: {test_name}")
        
        try:
            # Create orchestrator
            config = OrchestrationConfig(
                health_check_interval=1.0,
                metrics_collection_interval=2.0,
                max_message_queue_size=100
            )
            orchestrator = SystemOrchestrator(config)
            await orchestrator.start()
            
            # Register signal generation module
            signal_messages = []
            
            async def signal_message_handler(message):
                signal_messages.append(message)
            
            orchestrator.register_module(
                name="signal_generator",
                module_type="signal_generation",
                version="1.0.0",
                capabilities=["technical_analysis", "pattern_recognition"],
                integration_points=["execution_engine", "risk_management"],
                health_checker=self._create_mock_health_checker(True, 0.95),
                metrics_collector=self._create_mock_metrics_collector({"signals_generated": 10})
            )
            orchestrator.add_message_handler("signal_generator", signal_message_handler)
            
            # Register execution engine module
            execution_messages = []
            
            async def execution_message_handler(message):
                execution_messages.append(message)
                # Simulate execution response
                await orchestrator.send_message(
                    source_module="execution_engine",
                    target_module="signal_generator",
                    message_type=MessageType.RESPONSE,
                    payload={"execution_status": "completed", "order_id": "12345"}
                )
            
            orchestrator.register_module(
                name="execution_engine",
                module_type="execution",
                version="1.0.0",
                capabilities=["order_execution", "market_impact_analysis"],
                integration_points=["signal_generation", "risk_management"],
                health_checker=self._create_mock_health_checker(True, 0.98),
                metrics_collector=self._create_mock_metrics_collector({"orders_executed": 5})
            )
            orchestrator.add_message_handler("execution_engine", execution_message_handler)
            
            # Simulate signal generation sending execution request
            await orchestrator.send_message(
                source_module="signal_generator",
                target_module="execution_engine",
                message_type=MessageType.COMMAND,
                payload={
                    "action": "execute_order",
                    "symbol": "AAPL",
                    "side": "buy",
                    "quantity": 100,
                    "price": 150.0
                }
            )
            
            # Wait for message processing
            await asyncio.sleep(0.1)
            
            # Verify integration
            assert len(execution_messages) == 1, "Execution module should receive message"
            assert execution_messages[0].payload["action"] == "execute_order", "Wrong action"
            assert execution_messages[0].payload["symbol"] == "AAPL", "Wrong symbol"
            
            # Verify response was sent back
            assert len(signal_messages) == 1, "Signal module should receive response"
            assert signal_messages[0].payload["execution_status"] == "completed", "Wrong status"
            
            # Verify module health
            signal_module = orchestrator.get_module_status("signal_generator")
            execution_module = orchestrator.get_module_status("execution_engine")
            
            assert signal_module.is_healthy is True, "Signal module should be healthy"
            assert execution_module.is_healthy is True, "Execution module should be healthy"
            assert signal_module.health_score == 0.95, "Wrong health score"
            assert execution_module.health_score == 0.98, "Wrong health score"
            
            await orchestrator.stop()
            self._record_success(test_name)
            
        except Exception as e:
            await orchestrator.stop()
            self._record_failure(test_name, str(e))
    
    async def _test_multi_module_broadcast_integration(self):
        """Test broadcast messaging between multiple modules"""
        test_name = "Multi-Module Broadcast Integration"
        print(f"Running: {test_name}")
        
        try:
            config = OrchestrationConfig(
                health_check_interval=1.0,
                metrics_collection_interval=2.0,
                max_message_queue_size=100
            )
            orchestrator = SystemOrchestrator(config)
            await orchestrator.start()
            
            # Register multiple modules
            modules = ["risk_manager", "analytics_engine", "portfolio_manager"]
            received_messages = {module: [] for module in modules}
            
            for module_name in modules:
                async def create_handler(module):
                    async def handler(message):
                        received_messages[module].append(message)
                    return handler
                
                orchestrator.register_module(
                    name=module_name,
                    module_type=module_name.split("_")[0],
                    version="1.0.0",
                    capabilities=[f"{module_name}_capability"],
                    integration_points=["signal_generation", "execution_engine"],
                    health_checker=self._create_mock_health_checker(True, 0.9),
                    metrics_collector=self._create_mock_metrics_collector({"processed_events": 1})
                )
                orchestrator.add_message_handler(module_name, await create_handler(module_name))
            
            # Broadcast market event to all modules
            await orchestrator.broadcast_message(
                source_module="market_data_feed",
                message_type=MessageType.EVENT,
                payload={
                    "event_type": "market_open",
                    "timestamp": time.time(),
                    "market_status": "open"
                }
            )
            
            # Wait for message processing
            await asyncio.sleep(0.1)
            
            # Verify all modules received the broadcast
            for module_name in modules:
                assert len(received_messages[module_name]) == 1, f"{module_name} should receive message"
                assert received_messages[module_name][0].payload["event_type"] == "market_open", "Wrong event type"
                assert received_messages[module_name][0].payload["market_status"] == "open", "Wrong market status"
            
            await orchestrator.stop()
            self._record_success(test_name)
            
        except Exception as e:
            await orchestrator.stop()
            self._record_failure(test_name, str(e))
    
    async def _test_health_monitoring_integration(self):
        """Test health monitoring integration across modules"""
        test_name = "Health Monitoring Integration"
        print(f"Running: {test_name}")
        
        try:
            config = OrchestrationConfig(
                health_check_interval=0.5,  # Fast health checks for testing
                metrics_collection_interval=1.0,
                max_message_queue_size=100
            )
            orchestrator = SystemOrchestrator(config)
            await orchestrator.start()
            
            # Register modules with different health states
            orchestrator.register_module(
                name="healthy_module",
                module_type="test",
                version="1.0.0",
                health_checker=self._create_mock_health_checker(True, 0.95),
                metrics_collector=self._create_mock_metrics_collector({"status": "healthy"})
            )
            
            orchestrator.register_module(
                name="degraded_module",
                module_type="test",
                version="1.0.0",
                health_checker=self._create_mock_health_checker(False, 0.3),
                metrics_collector=self._create_mock_metrics_collector({"status": "degraded"})
            )
            
            # Wait for health checks to run
            await asyncio.sleep(1.0)
            
            # Verify health monitoring integration
            system_health = orchestrator.get_system_health()
            healthy_modules = orchestrator.get_healthy_modules()
            
            assert system_health["total_modules"] == 2, "Wrong total modules"
            assert system_health["healthy_modules"] == 1, "Wrong healthy modules count"
            assert system_health["health_percentage"] == 50.0, "Wrong health percentage"
            assert system_health["system_status"] == "degraded", "Wrong system status"
            
            assert "healthy_module" in healthy_modules, "Healthy module should be in healthy list"
            assert "degraded_module" not in healthy_modules, "Degraded module should not be in healthy list"
            
            await orchestrator.stop()
            self._record_success(test_name)
            
        except Exception as e:
            await orchestrator.stop()
            self._record_failure(test_name, str(e))
    
    async def _test_metrics_collection_integration(self):
        """Test metrics collection integration across modules"""
        test_name = "Metrics Collection Integration"
        print(f"Running: {test_name}")
        
        try:
            config = OrchestrationConfig(
                health_check_interval=1.0,
                metrics_collection_interval=1.0,  # Fast metrics collection
                max_message_queue_size=100
            )
            orchestrator = SystemOrchestrator(config)
            await orchestrator.start()
            
            # Register modules with different metrics
            orchestrator.register_module(
                name="high_performance_module",
                module_type="test",
                version="1.0.0",
                health_checker=self._create_mock_health_checker(True, 0.99),
                metrics_collector=self._create_mock_metrics_collector({
                    "cpu_usage": 0.2,
                    "memory_usage": 0.1,
                    "throughput": 1000
                })
            )
            
            orchestrator.register_module(
                name="resource_intensive_module",
                module_type="test",
                version="1.0.0",
                health_checker=self._create_mock_health_checker(True, 0.7),
                metrics_collector=self._create_mock_metrics_collector({
                    "cpu_usage": 0.8,
                    "memory_usage": 0.9,
                    "throughput": 100
                })
            )
            
            # Wait for metrics collection
            await asyncio.sleep(1.5)
            
            # Verify metrics collection integration
            high_perf_module = orchestrator.get_module_status("high_performance_module")
            resource_module = orchestrator.get_module_status("resource_intensive_module")
            
            assert "cpu_usage" in high_perf_module.metadata, "CPU usage should be in metadata"
            assert "memory_usage" in high_perf_module.metadata, "Memory usage should be in metadata"
            assert "throughput" in high_perf_module.metadata, "Throughput should be in metadata"
            assert high_perf_module.metadata["cpu_usage"] == 0.2, "Wrong CPU usage"
            assert high_perf_module.metadata["throughput"] == 1000, "Wrong throughput"
            
            assert resource_module.metadata["cpu_usage"] == 0.8, "Wrong CPU usage"
            assert resource_module.metadata["memory_usage"] == 0.9, "Wrong memory usage"
            assert resource_module.metadata["throughput"] == 100, "Wrong throughput"
            
            await orchestrator.stop()
            self._record_success(test_name)
            
        except Exception as e:
            await orchestrator.stop()
            self._record_failure(test_name, str(e))
    
    async def _test_error_handling_integration(self):
        """Test error handling integration across modules"""
        test_name = "Error Handling Integration"
        print(f"Running: {test_name}")
        
        try:
            config = OrchestrationConfig(
                health_check_interval=1.0,
                metrics_collection_interval=2.0,
                max_message_queue_size=100
            )
            orchestrator = SystemOrchestrator(config)
            await orchestrator.start()
            
            # Register module with error-prone handler
            error_messages = []
            
            async def error_handler(message):
                error_messages.append(message)
                raise Exception("Simulated processing error")
            
            orchestrator.register_module(
                name="error_prone_module",
                module_type="test",
                version="1.0.0",
                health_checker=self._create_mock_health_checker(True, 0.5),
                metrics_collector=self._create_mock_metrics_collector({"errors": 1})
            )
            orchestrator.add_message_handler("error_prone_module", error_handler)
            
            # Send message that will cause error
            await orchestrator.send_message(
                source_module="test_sender",
                target_module="error_prone_module",
                message_type=MessageType.COMMAND,
                payload={"test": "data"}
            )
            
            # Wait for processing
            await asyncio.sleep(0.1)
            
            # Verify error handling integration
            error_module = orchestrator.get_module_status("error_prone_module")
            system_health = orchestrator.get_system_health()
            
            assert len(error_messages) == 1, "Error message should be captured"
            assert error_module.error_count == 1, "Error count should be incremented"
            assert error_module.error_message is not None, "Error message should be set"
            assert system_health["performance_metrics"]["total_errors"] == 1, "System error count should be incremented"
            
            await orchestrator.stop()
            self._record_success(test_name)
            
        except Exception as e:
            await orchestrator.stop()
            self._record_failure(test_name, str(e))
    
    async def _test_performance_tracking_integration(self):
        """Test performance tracking integration across modules"""
        test_name = "Performance Tracking Integration"
        print(f"Running: {test_name}")
        
        try:
            config = OrchestrationConfig(
                health_check_interval=1.0,
                metrics_collection_interval=2.0,
                max_message_queue_size=100
            )
            orchestrator = SystemOrchestrator(config)
            await orchestrator.start()
            
            # Register modules with different performance characteristics
            orchestrator.register_module(
                name="fast_module",
                module_type="test",
                version="1.0.0",
                health_checker=self._create_mock_health_checker(True, 0.95),
                metrics_collector=self._create_mock_metrics_collector({"response_time": 0.01})
            )
            
            orchestrator.register_module(
                name="slow_module",
                module_type="test",
                version="1.0.0",
                health_checker=self._create_mock_health_checker(True, 0.8),
                metrics_collector=self._create_mock_metrics_collector({"response_time": 0.5})
            )
            
            # Add handlers with different response times
            async def fast_handler(message):
                await asyncio.sleep(0.01)  # Fast response
            
            async def slow_handler(message):
                await asyncio.sleep(0.1)  # Slow response
            
            orchestrator.add_message_handler("fast_module", fast_handler)
            orchestrator.add_message_handler("slow_module", slow_handler)
            
            # Send messages to both modules
            for i in range(3):
                await orchestrator.send_message(
                    source_module="test_sender",
                    target_module="fast_module",
                    message_type=MessageType.COMMAND,
                    payload={"index": i}
                )
                
                await orchestrator.send_message(
                    source_module="test_sender",
                    target_module="slow_module",
                    message_type=MessageType.COMMAND,
                    payload={"index": i}
                )
            
            # Wait for processing
            await asyncio.sleep(0.5)
            
            # Verify performance tracking integration
            fast_module = orchestrator.get_module_status("fast_module")
            slow_module = orchestrator.get_module_status("slow_module")
            
            assert fast_module.message_count == 3, "Fast module should process 3 messages"
            assert slow_module.message_count == 3, "Slow module should process 3 messages"
            assert fast_module.avg_response_time < slow_module.avg_response_time, "Fast module should be faster"
            
            system_health = orchestrator.get_system_health()
            assert system_health["performance_metrics"]["total_messages"] == 6, "Total messages should be 6"
            
            await orchestrator.stop()
            self._record_success(test_name)
            
        except Exception as e:
            await orchestrator.stop()
            self._record_failure(test_name, str(e))
    
    async def _test_integration_points_mapping(self):
        """Test integration points mapping functionality"""
        test_name = "Integration Points Mapping"
        print(f"Running: {test_name}")
        
        try:
            config = OrchestrationConfig()
            orchestrator = SystemOrchestrator(config)
            await orchestrator.start()
            
            # Register modules with different integration points
            orchestrator.register_module(
                name="signal_module",
                module_type="signal",
                version="1.0.0",
                integration_points=["execution_engine", "risk_management", "analytics"]
            )
            
            orchestrator.register_module(
                name="execution_module",
                module_type="execution",
                version="1.0.0",
                integration_points=["signal_generation", "risk_management", "portfolio"]
            )
            
            orchestrator.register_module(
                name="risk_module",
                module_type="risk",
                version="1.0.0",
                integration_points=["signal_generation", "execution_engine", "analytics"]
            )
            
            # Get integration points mapping
            integration_points = orchestrator.get_integration_points()
            
            # Verify integration points mapping
            assert "execution_engine" in integration_points, "execution_engine should be in integration points"
            assert "risk_management" in integration_points, "risk_management should be in integration points"
            assert "analytics" in integration_points, "analytics should be in integration points"
            assert "signal_generation" in integration_points, "signal_generation should be in integration points"
            assert "portfolio" in integration_points, "portfolio should be in integration points"
            
            assert "signal_module" in integration_points["execution_engine"], "signal_module should be in execution_engine"
            assert "risk_module" in integration_points["execution_engine"], "risk_module should be in execution_engine"
            assert "execution_module" not in integration_points["execution_engine"], "execution_module should NOT be in execution_engine"
            
            await orchestrator.stop()
            self._record_success(test_name)
            
        except Exception as e:
            await orchestrator.stop()
            self._record_failure(test_name, str(e))
    
    async def _test_high_message_volume_integration(self):
        """Test integration under high message volume"""
        test_name = "High Message Volume Integration"
        print(f"Running: {test_name}")
        
        try:
            config = OrchestrationConfig(
                health_check_interval=1.0,
                metrics_collection_interval=2.0,
                max_message_queue_size=200
            )
            orchestrator = SystemOrchestrator(config)
            await orchestrator.start()
            
            # Register processing module
            processed_messages = []
            
            async def processor_handler(message):
                processed_messages.append(message)
                await asyncio.sleep(0.001)  # Small processing delay
            
            orchestrator.register_module(
                name="message_processor",
                module_type="processor",
                version="1.0.0",
                health_checker=self._create_mock_health_checker(True, 0.9),
                metrics_collector=self._create_mock_metrics_collector({"processed": len(processed_messages)})
            )
            orchestrator.add_message_handler("message_processor", processor_handler)
            
            # Send high volume of messages
            message_count = 50  # Reduced for faster testing
            for i in range(message_count):
                await orchestrator.send_message(
                    source_module="high_volume_sender",
                    target_module="message_processor",
                    message_type=MessageType.COMMAND,
                    payload={"message_id": i, "data": f"data_{i}"}
                )
            
            # Wait for processing
            await asyncio.sleep(1.0)
            
            # Verify high volume integration
            processor_module = orchestrator.get_module_status("message_processor")
            system_health = orchestrator.get_system_health()
            
            assert len(processed_messages) == message_count, f"Should process {message_count} messages"
            assert processor_module.message_count == message_count, "Message count should match"
            assert system_health["performance_metrics"]["total_messages"] == message_count, "System message count should match"
            
            await orchestrator.stop()
            self._record_success(test_name)
            
        except Exception as e:
            await orchestrator.stop()
            self._record_failure(test_name, str(e))
    
    async def _test_concurrent_module_registration(self):
        """Test concurrent module registration"""
        test_name = "Concurrent Module Registration"
        print(f"Running: {test_name}")
        
        try:
            config = OrchestrationConfig()
            orchestrator = SystemOrchestrator(config)
            await orchestrator.start()
            
            # Register multiple modules concurrently
            module_count = 10  # Reduced for faster testing
            registration_tasks = []
            
            for i in range(module_count):
                task = asyncio.create_task(self._register_module_async(
                    orchestrator, f"module_{i}", "test", "1.0.0"
                ))
                registration_tasks.append(task)
            
            # Wait for all registrations
            results = await asyncio.gather(*registration_tasks)
            
            # Verify concurrent registration
            assert all(results), "All registrations should succeed"
            assert len(orchestrator.modules) == module_count, f"Should have {module_count} modules"
            
            # Verify all modules are registered
            for i in range(module_count):
                module_name = f"module_{i}"
                assert module_name in orchestrator.modules, f"Module {module_name} should be registered"
                assert orchestrator.modules[module_name].status == ModuleStatus.REGISTERED, f"Module {module_name} should be registered"
            
            await orchestrator.stop()
            self._record_success(test_name)
            
        except Exception as e:
            await orchestrator.stop()
            self._record_failure(test_name, str(e))
    
    async def _register_module_async(self, orchestrator, name, module_type, version):
        """Helper function to register module asynchronously"""
        return orchestrator.register_module(name, module_type, version)
    
    def _create_mock_health_checker(self, is_healthy: bool, health_score: float):
        """Create a mock health checker function"""
        async def health_checker():
            return {
                "is_healthy": is_healthy,
                "health_score": health_score,
                "error_message": None if is_healthy else "Mock error"
            }
        return health_checker
    
    def _create_mock_metrics_collector(self, metrics: dict):
        """Create a mock metrics collector function"""
        async def metrics_collector():
            return metrics
        return metrics_collector
    
    def _record_success(self, test_name: str):
        """Record a successful test"""
        self.test_results.append({"name": test_name, "status": "PASSED", "error": None})
        self.passed_tests += 1
        print(f"✅ PASSED: {test_name}")
    
    def _record_failure(self, test_name: str, error: str):
        """Record a failed test"""
        self.test_results.append({"name": test_name, "status": "FAILED", "error": error})
        self.failed_tests += 1
        print(f"❌ FAILED: {test_name} - {error}")
    
    def _print_results(self):
        """Print test results summary"""
        print("\n" + "=" * 60)
        print("📊 MODULE INTEGRATION TEST RESULTS")
        print("=" * 60)
        print(f"Total Tests: {len(self.test_results)}")
        print(f"Passed: {self.passed_tests}")
        print(f"Failed: {self.failed_tests}")
        print(f"Success Rate: {(self.passed_tests / len(self.test_results) * 100):.1f}%")
        print()
        
        if self.failed_tests > 0:
            print("❌ FAILED TESTS:")
            for result in self.test_results:
                if result["status"] == "FAILED":
                    print(f"  - {result['name']}: {result['error']}")
            print()
        
        if self.passed_tests == len(self.test_results):
            print("🎉 ALL TESTS PASSED! Module integration is working correctly.")
        else:
            print("⚠️  Some tests failed. Please review the errors above.")
        
        print("=" * 60)

async def main():
    """Main test runner function"""
    runner = ModuleIntegrationTestRunner()
    await runner.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main()) 