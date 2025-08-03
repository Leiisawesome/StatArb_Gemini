#!/usr/bin/env python3
"""
System Orchestrator Tests
=========================

Comprehensive test suite for the SystemOrchestrator functionality.
Tests cover module registration, messaging, health monitoring, and system coordination.

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
    SystemMessage,
    ModuleInfo
)

class TestSystemOrchestratorInitialization:
    """Test SystemOrchestrator initialization and configuration"""
    
    def test_default_initialization(self):
        """Test orchestrator initialization with default config"""
        orchestrator = SystemOrchestrator()
        
        assert orchestrator.config is not None
        assert orchestrator.config.auto_register_modules is True
        assert orchestrator.config.health_check_interval == 30.0
        assert orchestrator.config.enable_messaging is True
        assert len(orchestrator.modules) == 0
        assert orchestrator._running is False
    
    def test_custom_config_initialization(self):
        """Test orchestrator initialization with custom config"""
        config = OrchestrationConfig(
            auto_register_modules=False,
            health_check_interval=60.0,
            enable_messaging=False,
            max_message_queue_size=500
        )
        
        orchestrator = SystemOrchestrator(config)
        
        assert orchestrator.config.auto_register_modules is False
        assert orchestrator.config.health_check_interval == 60.0
        assert orchestrator.config.enable_messaging is False
        assert orchestrator.config.max_message_queue_size == 500
    
    def test_integration_points_config(self):
        """Test integration points configuration"""
        config = OrchestrationConfig(
            integration_points=["test_point_1", "test_point_2"]
        )
        
        orchestrator = SystemOrchestrator(config)
        
        assert "test_point_1" in orchestrator.config.integration_points
        assert "test_point_2" in orchestrator.config.integration_points

class TestModuleRegistration:
    """Test module registration and unregistration functionality"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create a fresh orchestrator for each test"""
        return SystemOrchestrator()
    
    def test_register_module_success(self, orchestrator):
        """Test successful module registration"""
        result = orchestrator.register_module(
            name="test_module",
            module_type="test_type",
            version="1.0.0",
            capabilities=["cap1", "cap2"],
            integration_points=["point1", "point2"]
        )
        
        assert result is True
        assert "test_module" in orchestrator.modules
        
        module_info = orchestrator.modules["test_module"]
        assert module_info.name == "test_module"
        assert module_info.module_type == "test_type"
        assert module_info.version == "1.0.0"
        assert module_info.status == ModuleStatus.REGISTERED
        assert "cap1" in module_info.capabilities
        assert "point1" in module_info.integration_points
    
    def test_register_duplicate_module(self, orchestrator):
        """Test registering a module that already exists"""
        # Register module first time
        result1 = orchestrator.register_module(
            name="test_module",
            module_type="test_type",
            version="1.0.0"
        )
        assert result1 is True
        
        # Try to register same module again
        result2 = orchestrator.register_module(
            name="test_module",
            module_type="test_type",
            version="2.0.0"
        )
        assert result2 is False
    
    def test_register_module_with_handlers(self, orchestrator):
        """Test module registration with health checker and metrics collector"""
        health_checker = Mock()
        metrics_collector = Mock()
        
        result = orchestrator.register_module(
            name="test_module",
            module_type="test_type",
            version="1.0.0",
            health_checker=health_checker,
            metrics_collector=metrics_collector
        )
        
        assert result is True
        assert "test_module" in orchestrator.health_checkers
        assert "test_module" in orchestrator.metrics_collectors
        assert orchestrator.health_checkers["test_module"] == health_checker
        assert orchestrator.metrics_collectors["test_module"] == metrics_collector
    
    def test_unregister_module_success(self, orchestrator):
        """Test successful module unregistration"""
        # Register module
        orchestrator.register_module(
            name="test_module",
            module_type="test_type",
            version="1.0.0"
        )
        
        # Verify module is registered
        assert "test_module" in orchestrator.modules
        
        # Unregister module
        result = orchestrator.unregister_module("test_module")
        assert result is True
        
        # Verify module is no longer in modules dictionary
        assert "test_module" not in orchestrator.modules
    
    def test_unregister_nonexistent_module(self, orchestrator):
        """Test unregistering a module that doesn't exist"""
        result = orchestrator.unregister_module("nonexistent_module")
        assert result is False

class TestMessaging:
    """Test inter-module messaging functionality"""
    
    @pytest.fixture
    async def running_orchestrator(self):
        """Create and start an orchestrator for messaging tests"""
        orchestrator = SystemOrchestrator()
        await orchestrator.start()
        yield orchestrator
        await orchestrator.stop()
    
    async def test_send_message_success(self, running_orchestrator):
        """Test successful message sending"""
        # Register target module
        running_orchestrator.register_module(
            name="target_module",
            module_type="test_type",
            version="1.0.0"
        )
        
        # Send message
        message = await running_orchestrator.send_message(
            source_module="source_module",
            target_module="target_module",
            message_type=MessageType.COMMAND,
            payload={"command": "test"}
        )
        
        assert message is not None
        assert message.source_module == "source_module"
        assert message.target_module == "target_module"
        assert message.message_type == MessageType.COMMAND
        assert message.payload["command"] == "test"
    
    async def test_send_message_to_nonexistent_module(self, running_orchestrator):
        """Test sending message to non-existent module"""
        message = await running_orchestrator.send_message(
            source_module="source_module",
            target_module="nonexistent_module",
            message_type=MessageType.COMMAND,
            payload={"command": "test"}
        )
        
        assert message is None
    
    async def test_broadcast_message(self, running_orchestrator):
        """Test broadcast messaging"""
        # Register multiple modules
        running_orchestrator.register_module("module1", "test_type", "1.0.0")
        running_orchestrator.register_module("module2", "test_type", "1.0.0")
        running_orchestrator.register_module("module3", "test_type", "1.0.0")
        
        # Set modules to running status
        running_orchestrator.modules["module1"].status = ModuleStatus.RUNNING
        running_orchestrator.modules["module2"].status = ModuleStatus.RUNNING
        running_orchestrator.modules["module3"].status = ModuleStatus.RUNNING
        
        # Broadcast message
        messages = await running_orchestrator.broadcast_message(
            source_module="broadcaster",
            message_type=MessageType.EVENT,
            payload={"event": "test_event"}
        )
        
        assert len(messages) == 3
        for message in messages:
            assert message.source_module == "broadcaster"
            assert message.message_type == MessageType.EVENT
            assert message.payload["event"] == "test_event"
    
    async def test_message_handler_registration(self, running_orchestrator):
        """Test message handler registration and execution"""
        # Register module
        running_orchestrator.register_module("test_module", "test_type", "1.0.0")
        
        # Create mock handler
        handler_called = False
        received_message = None
        
        async def mock_handler(message):
            nonlocal handler_called, received_message
            handler_called = True
            received_message = message
        
        # Register handler
        running_orchestrator.add_message_handler("test_module", mock_handler)
        
        # Send message
        await running_orchestrator.send_message(
            source_module="source",
            target_module="test_module",
            message_type=MessageType.COMMAND,
            payload={"test": "data"}
        )
        
        # Wait for message processing
        await asyncio.sleep(0.1)
        
        assert handler_called is True
        assert received_message is not None
        assert received_message.payload["test"] == "data"

class TestHealthMonitoring:
    """Test health monitoring functionality"""
    
    @pytest.fixture
    async def orchestrator_with_health_checker(self):
        """Create orchestrator with health checker"""
        orchestrator = SystemOrchestrator()
        
        # Create mock health checker
        async def mock_health_checker():
            return {
                "is_healthy": True,
                "health_score": 0.95,
                "error_message": None
            }
        
        # Register module with health checker
        orchestrator.register_module(
            name="test_module",
            module_type="test_type",
            version="1.0.0",
            health_checker=mock_health_checker
        )
        
        await orchestrator.start()
        yield orchestrator
        await orchestrator.stop()
    
    async def test_health_check_execution(self, orchestrator_with_health_checker):
        """Test health check execution"""
        orchestrator = orchestrator_with_health_checker
        
        # Wait for health check to run
        await asyncio.sleep(0.1)
        
        # Check module health
        module_info = orchestrator.modules["test_module"]
        assert module_info.is_healthy is True
        assert module_info.health_score == 0.95
        assert module_info.last_health_check is not None
    
    async def test_health_check_failure(self):
        """Test health check failure handling"""
        orchestrator = SystemOrchestrator()
        
        # Create failing health checker
        async def failing_health_checker():
            raise Exception("Health check failed")
        
        # Register module with failing health checker
        orchestrator.register_module(
            name="test_module",
            module_type="test_type",
            version="1.0.0",
            health_checker=failing_health_checker
        )
        
        await orchestrator.start()
        
        # Wait for health check to run
        await asyncio.sleep(0.1)
        
        # Check module health
        module_info = orchestrator.modules["test_module"]
        assert module_info.is_healthy is False
        assert module_info.health_score == 0.0
        assert module_info.status == ModuleStatus.ERROR
        assert module_info.error_message is not None
        
        await orchestrator.stop()

class TestMetricsCollection:
    """Test metrics collection functionality"""
    
    @pytest.fixture
    async def orchestrator_with_metrics_collector(self):
        """Create orchestrator with metrics collector"""
        orchestrator = SystemOrchestrator()
        
        # Create mock metrics collector
        async def mock_metrics_collector():
            return {
                "cpu_usage": 0.5,
                "memory_usage": 0.3,
                "active_connections": 10
            }
        
        # Register module with metrics collector
        orchestrator.register_module(
            name="test_module",
            module_type="test_type",
            version="1.0.0",
            metrics_collector=mock_metrics_collector
        )
        
        await orchestrator.start()
        yield orchestrator
        await orchestrator.stop()
    
    async def test_metrics_collection(self, orchestrator_with_metrics_collector):
        """Test metrics collection execution"""
        orchestrator = orchestrator_with_metrics_collector
        
        # Wait for metrics collection to run
        await asyncio.sleep(0.1)
        
        # Check module metrics
        module_info = orchestrator.modules["test_module"]
        assert "cpu_usage" in module_info.metadata
        assert "memory_usage" in module_info.metadata
        assert "active_connections" in module_info.metadata
        assert module_info.metadata["cpu_usage"] == 0.5

class TestSystemHealth:
    """Test system health monitoring"""
    
    @pytest.fixture
    async def orchestrator_with_modules(self):
        """Create orchestrator with multiple modules"""
        orchestrator = SystemOrchestrator()
        
        # Register multiple modules
        orchestrator.register_module("module1", "test_type", "1.0.0")
        orchestrator.register_module("module2", "test_type", "1.0.0")
        orchestrator.register_module("module3", "test_type", "1.0.0")
        
        # Set module statuses
        orchestrator.modules["module1"].status = ModuleStatus.HEALTHY
        orchestrator.modules["module1"].is_healthy = True
        orchestrator.modules["module2"].status = ModuleStatus.HEALTHY
        orchestrator.modules["module2"].is_healthy = True
        orchestrator.modules["module3"].status = ModuleStatus.ERROR
        orchestrator.modules["module3"].is_healthy = False
        
        await orchestrator.start()
        yield orchestrator
        await orchestrator.stop()
    
    def test_get_system_health(self, orchestrator_with_modules):
        """Test system health calculation"""
        orchestrator = orchestrator_with_modules
        
        health = orchestrator.get_system_health()
        
        assert health["total_modules"] == 3
        assert health["healthy_modules"] == 2
        assert health["health_percentage"] == pytest.approx(66.67, rel=0.01)
        assert health["system_status"] == "degraded"
        assert "performance_metrics" in health
        assert "uptime" in health
    
    def test_get_healthy_modules(self, orchestrator_with_modules):
        """Test getting list of healthy modules"""
        orchestrator = orchestrator_with_modules
        
        healthy_modules = orchestrator.get_healthy_modules()
        
        assert len(healthy_modules) == 2
        assert "module1" in healthy_modules
        assert "module2" in healthy_modules
        assert "module3" not in healthy_modules
    
    def test_get_integration_points(self, orchestrator_with_modules):
        """Test getting integration points mapping"""
        orchestrator = orchestrator_with_modules
        
        # Add integration points to modules
        orchestrator.modules["module1"].integration_points = ["point1", "point2"]
        orchestrator.modules["module2"].integration_points = ["point2", "point3"]
        orchestrator.modules["module3"].integration_points = ["point1"]
        
        integration_points = orchestrator.get_integration_points()
        
        assert "point1" in integration_points
        assert "point2" in integration_points
        assert "point3" in integration_points
        assert "module1" in integration_points["point1"]
        assert "module3" in integration_points["point1"]
        assert "module1" in integration_points["point2"]
        assert "module2" in integration_points["point2"]

class TestPerformanceTracking:
    """Test performance tracking functionality"""
    
    @pytest.fixture
    async def orchestrator_with_performance(self):
        """Create orchestrator for performance testing"""
        orchestrator = SystemOrchestrator()
        await orchestrator.start()
        yield orchestrator
        await orchestrator.stop()
    
    async def test_message_performance_tracking(self, orchestrator_with_performance):
        """Test message performance tracking"""
        orchestrator = orchestrator_with_performance
        
        # Register module with handler
        orchestrator.register_module("test_module", "test_type", "1.0.0")
        
        async def slow_handler(message):
            await asyncio.sleep(0.01)  # Simulate processing time
        
        orchestrator.add_message_handler("test_module", slow_handler)
        
        # Send multiple messages
        for i in range(5):
            await orchestrator.send_message(
                source_module="source",
                target_module="test_module",
                message_type=MessageType.COMMAND,
                payload={"index": i}
            )
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        # Check performance metrics
        module_info = orchestrator.modules["test_module"]
        assert module_info.message_count == 5
        assert module_info.avg_response_time > 0
        
        system_health = orchestrator.get_system_health()
        assert system_health["performance_metrics"]["total_messages"] == 5

class TestErrorHandling:
    """Test error handling functionality"""
    
    @pytest.fixture
    async def orchestrator_with_error_handler(self):
        """Create orchestrator for error handling tests"""
        orchestrator = SystemOrchestrator()
        await orchestrator.start()
        yield orchestrator
        await orchestrator.stop()
    
    async def test_message_handler_error(self, orchestrator_with_error_handler):
        """Test error handling in message handlers"""
        orchestrator = orchestrator_with_error_handler
        
        # Register module with error-prone handler
        orchestrator.register_module("test_module", "test_type", "1.0.0")
        
        async def error_handler(message):
            raise Exception("Handler error")
        
        orchestrator.add_message_handler("test_module", error_handler)
        
        # Send message
        await orchestrator.send_message(
            source_module="source",
            target_module="test_module",
            message_type=MessageType.COMMAND,
            payload={"test": "data"}
        )
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        # Check error tracking
        module_info = orchestrator.modules["test_module"]
        assert module_info.error_count == 1
        assert module_info.error_message is not None
        
        system_health = orchestrator.get_system_health()
        assert system_health["performance_metrics"]["total_errors"] == 1

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 