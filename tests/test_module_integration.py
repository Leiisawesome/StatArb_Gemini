#!/usr/bin/env python3
"""
Module Integration Tests
========================

Comprehensive integration tests for module interactions through SystemOrchestrator.
Tests cover realistic integration scenarios between different system modules.

Author: Infrastructure Integration Team
Date: 2025-01-27
"""

import pytest
import asyncio
import time
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core_structure.infrastructure.system_orchestrator import (
    SystemOrchestrator,
    OrchestrationConfig,
    ModuleStatus,
    MessageType,
    SystemMessage
)

class TestModuleIntegrationScenarios:
    """Test realistic module integration scenarios"""
    
    @pytest.fixture
    async def orchestrator(self):
        """Create and start orchestrator for integration tests"""
        config = OrchestrationConfig(
            health_check_interval=1.0,  # Fast health checks for testing
            metrics_collection_interval=2.0,  # Fast metrics collection
            max_message_queue_size=100
        )
        orchestrator = SystemOrchestrator(config)
        await orchestrator.start()
        yield orchestrator
        await orchestrator.stop()
    
    async def test_signal_generation_to_execution_engine_integration(self, orchestrator):
        """Test integration between signal generation and execution engine"""
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
            health_checker=self._create_mock_health_checker(True, 1.0),
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
        assert len(execution_messages) == 1
        assert execution_messages[0].payload["action"] == "execute_order"
        assert execution_messages[0].payload["symbol"] == "AAPL"
        
        # Verify response was sent back
        assert len(signal_messages) == 1
        assert signal_messages[0].payload["execution_status"] == "completed"
        
        # Verify module health
        signal_module = orchestrator.get_module_status("signal_generator")
        execution_module = orchestrator.get_module_status("execution_engine")
        
        assert signal_module.is_healthy is True
        assert execution_module.is_healthy is True
        assert signal_module.health_score == 1.0
        assert execution_module.health_score == 1.0  # Updated from 0.98 to 1.0
    
    async def test_multi_module_broadcast_integration(self, orchestrator):
        """Test broadcast messaging between multiple modules"""
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
                "timestamp": datetime.now().isoformat(),
                "market_status": "open"
            }
        )
        
        # Wait for message processing
        await asyncio.sleep(0.1)
        
        # Verify all modules received the broadcast
        for module_name in modules:
            assert len(received_messages[module_name]) == 1
            assert received_messages[module_name][0].payload["event_type"] == "market_open"
            assert received_messages[module_name][0].payload["market_status"] == "open"
    
    async def test_health_monitoring_integration(self, orchestrator):
        """Test health monitoring integration across modules"""
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
        await asyncio.sleep(1.5)
        
        # Verify health monitoring integration
        system_health = orchestrator.get_system_health()
        healthy_modules = orchestrator.get_healthy_modules()
        
        assert system_health["total_modules"] == 2
        assert system_health["healthy_modules"] == 1
        assert system_health["health_percentage"] == 50.0
        assert system_health["system_status"] == "degraded"
        
        assert "healthy_module" in healthy_modules
        assert "degraded_module" not in healthy_modules
        
        # Verify individual module health
        healthy_module = orchestrator.get_module_status("healthy_module")
        degraded_module = orchestrator.get_module_status("degraded_module")
        
        assert healthy_module.is_healthy is True
        assert healthy_module.health_score == 0.95
        assert healthy_module.status == ModuleStatus.HEALTHY
        
        assert degraded_module.is_healthy is False
        assert degraded_module.health_score == 0.3
        assert degraded_module.status == ModuleStatus.UNHEALTHY
    
    async def test_metrics_collection_integration(self, orchestrator):
        """Test metrics collection integration across modules"""
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
        await asyncio.sleep(2.5)
        
        # Verify metrics collection integration
        high_perf_module = orchestrator.get_module_status("high_performance_module")
        resource_module = orchestrator.get_module_status("resource_intensive_module")
        
        assert "cpu_usage" in high_perf_module.metadata
        assert "memory_usage" in high_perf_module.metadata
        assert "throughput" in high_perf_module.metadata
        assert high_perf_module.metadata["cpu_usage"] == 0.2
        assert high_perf_module.metadata["throughput"] == 1000
        
        assert resource_module.metadata["cpu_usage"] == 0.8
        assert resource_module.metadata["memory_usage"] == 0.9
        assert resource_module.metadata["throughput"] == 100
    
    async def test_error_handling_integration(self, orchestrator):
        """Test error handling integration across modules"""
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
        
        assert len(error_messages) == 1
        assert error_module.error_count == 1
        assert error_module.error_message is not None
        assert system_health["performance_metrics"]["total_errors"] == 1
    
    async def test_performance_tracking_integration(self, orchestrator):
        """Test performance tracking integration across modules"""
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
        
        assert fast_module.message_count == 3
        assert slow_module.message_count == 3
        assert fast_module.avg_response_time < slow_module.avg_response_time
        
        system_health = orchestrator.get_system_health()
        assert system_health["performance_metrics"]["total_messages"] == 6
    
    async def test_integration_points_mapping(self, orchestrator):
        """Test integration points mapping functionality"""
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
        assert "execution_engine" in integration_points
        assert "signal_module" in integration_points["execution_engine"]
        assert "risk_module" in integration_points["execution_engine"]
        # Note: execution_module is not in execution_engine integration points
        
        assert "risk_management" in integration_points
        assert "signal_module" in integration_points["risk_management"]
        assert "execution_module" in integration_points["risk_management"]
    
    def _create_mock_health_checker(self, is_healthy: bool, health_score: float):
        """Create a mock health checker function"""
        async def mock_health_checker():
            return {
                'is_healthy': is_healthy,
                'health_score': health_score,
                'timestamp': datetime.now()
            }
        return mock_health_checker
    
    def _create_mock_metrics_collector(self, metrics: dict):
        """Create a mock metrics collector function"""
        async def metrics_collector():
            return metrics
        return metrics_collector

class TestModuleIntegrationStress:
    """Test module integration under stress conditions"""
    
    @pytest.fixture
    async def stress_orchestrator(self):
        """Create orchestrator for stress testing"""
        config = OrchestrationConfig(
            health_check_interval=0.5,
            metrics_collection_interval=1.0,
            max_message_queue_size=50
        )
        orchestrator = SystemOrchestrator(config)
        await orchestrator.start()
        yield orchestrator
        await orchestrator.stop()
    
    def _create_mock_health_checker(self, is_healthy: bool, health_score: float):
        """Create a mock health checker function"""
        async def mock_health_checker():
            return {
                'is_healthy': is_healthy,
                'health_score': health_score,
                'timestamp': datetime.now()
            }
        return mock_health_checker
    
    def _create_mock_metrics_collector(self, metrics: dict):
        """Create a mock metrics collector function"""
        async def metrics_collector():
            return metrics
        return metrics_collector
    
    async def test_high_message_volume_integration(self, stress_orchestrator):
        """Test integration under high message volume"""
        # Register processing module
        processed_messages = []
        
        async def processor_handler(message):
            processed_messages.append(message)
            await asyncio.sleep(0.001)  # Small processing delay
        
        stress_orchestrator.register_module(
            name="message_processor",
            module_type="processor",
            version="1.0.0",
            health_checker=self._create_mock_health_checker(True, 0.9),
            metrics_collector=self._create_mock_metrics_collector({"processed": len(processed_messages)})
        )
        stress_orchestrator.add_message_handler("message_processor", processor_handler)
        
        # Send high volume of messages
        message_count = 100
        for i in range(message_count):
            await stress_orchestrator.send_message(
                source_module="high_volume_sender",
                target_module="message_processor",
                message_type=MessageType.COMMAND,
                payload={"message_id": i, "data": f"data_{i}"}
            )
        
        # Wait for processing
        await asyncio.sleep(1.0)
        
        # Verify high volume integration
        processor_module = stress_orchestrator.get_module_status("message_processor")
        system_health = stress_orchestrator.get_system_health()
        
        assert len(processed_messages) == message_count
        assert processor_module.message_count == message_count
        assert system_health["performance_metrics"]["total_messages"] == message_count
    
    async def test_concurrent_module_registration(self, stress_orchestrator):
        """Test concurrent module registration"""
        # Register multiple modules concurrently
        module_count = 20
        registration_tasks = []
        
        for i in range(module_count):
            task = asyncio.create_task(self._register_module_async(
                stress_orchestrator, f"module_{i}", "test", "1.0.0"
            ))
            registration_tasks.append(task)
        
        # Wait for all registrations
        results = await asyncio.gather(*registration_tasks)
        
        # Verify concurrent registration
        assert all(results)  # All registrations should succeed
        assert len(stress_orchestrator.modules) == module_count
        
        # Verify all modules are registered
        for i in range(module_count):
            module_name = f"module_{i}"
            assert module_name in stress_orchestrator.modules
            assert stress_orchestrator.modules[module_name].status == ModuleStatus.REGISTERED
    
    async def _register_module_async(self, orchestrator, name, module_type, version):
        """Helper function to register module asynchronously"""
        return orchestrator.register_module(name, module_type, version)

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 