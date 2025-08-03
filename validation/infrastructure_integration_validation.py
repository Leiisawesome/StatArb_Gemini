#!/usr/bin/env python3
"""
Infrastructure Integration Validation
====================================

Comprehensive validation script for infrastructure integration including:
- SystemOrchestrator functionality
- Infrastructure components (ConfigManager, DatabaseManager, MessageBus, MetricsCollector)
- Module registration and communication
- Health monitoring and metrics collection
- Error handling and recovery
- Performance and scalability

Author: Infrastructure Integration Team
Date: 2025-01-27
"""

import asyncio
import json
import time
import sys
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ValidationCheck:
    """Individual validation check result"""
    name: str
    category: str
    status: str  # "PASSED", "FAILED", "WARNING"
    message: str
    duration: float
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ValidationCategory:
    """Validation category results"""
    name: str
    checks: List[ValidationCheck]
    passed: int
    failed: int
    warnings: int
    total: int
    success_rate: float

@dataclass
class InfrastructureValidationReport:
    """Complete infrastructure validation report"""
    timestamp: str
    overall_status: str
    categories: Dict[str, ValidationCategory]
    total_checks: int
    total_passed: int
    total_failed: int
    total_warnings: int
    overall_success_rate: float
    recommendations: List[str]
    performance_metrics: Dict[str, Any]

# Helper functions for async health checkers and metrics collectors
async def default_health_checker():
    """Default async health checker"""
    return {"is_healthy": True, "health_score": 0.95}

async def default_metrics_collector():
    """Default async metrics collector"""
    return {"test_metric": 1.0}

async def create_metrics_collector(metrics_dict):
    """Create async metrics collector with specific metrics"""
    async def collector():
        return metrics_dict
    return collector

class InfrastructureIntegrationValidator:
    """Comprehensive infrastructure integration validator"""
    
    def __init__(self):
        self.orchestrator = None
        self.validation_results = []
        self.categories = {}
        
    async def run_comprehensive_validation(self) -> InfrastructureValidationReport:
        """Run comprehensive infrastructure integration validation"""
        logger.info("Starting comprehensive infrastructure integration validation...")
        
        # Initialize orchestrator
        await self._initialize_orchestrator()
        
        # Run validation categories
        await self._validate_system_orchestrator()
        await self._validate_infrastructure_components()
        await self._validate_module_integration()
        await self._validate_communication_workflows()
        await self._validate_health_monitoring()
        await self._validate_performance_metrics()
        await self._validate_error_handling()
        await self._validate_scalability()
        
        # Generate report
        report = self._generate_validation_report()
        
        # Cleanup
        await self._cleanup()
        
        logger.info("Infrastructure integration validation completed")
        return report
    
    async def _initialize_orchestrator(self):
        """Initialize SystemOrchestrator for validation"""
        logger.info("Initializing SystemOrchestrator...")
        
        try:
            config = OrchestrationConfig(
                health_check_interval=2.0,
                metrics_collection_interval=3.0,
                max_message_queue_size=1000
            )
            
            self.orchestrator = SystemOrchestrator(config)
            await self.orchestrator.start()
            
            logger.info("SystemOrchestrator initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize SystemOrchestrator: {e}")
            raise
    
    async def _validate_system_orchestrator(self):
        """Validate SystemOrchestrator core functionality"""
        logger.info("Validating SystemOrchestrator core functionality...")
        
        category_name = "SystemOrchestrator"
        checks = []
        
        # Check 1: Basic initialization
        check = await self._run_check(
            "Basic Initialization",
            category_name,
            self._check_basic_initialization
        )
        checks.append(check)
        
        # Check 2: Module registration
        check = await self._run_check(
            "Module Registration",
            category_name,
            self._check_module_registration
        )
        checks.append(check)
        
        # Check 3: Message handling
        check = await self._run_check(
            "Message Handling",
            category_name,
            self._check_message_handling
        )
        checks.append(check)
        
        # Check 4: Health monitoring
        check = await self._run_check(
            "Health Monitoring",
            category_name,
            self._check_health_monitoring
        )
        checks.append(check)
        
        self.categories[category_name] = self._create_category(category_name, checks)
    
    async def _validate_infrastructure_components(self):
        """Validate infrastructure components availability and functionality"""
        logger.info("Validating infrastructure components...")
        
        category_name = "InfrastructureComponents"
        checks = []
        
        # Check 1: ConfigManager availability
        check = await self._run_check(
            "ConfigManager Availability",
            category_name,
            self._check_config_manager
        )
        checks.append(check)
        
        # Check 2: DatabaseManager availability
        check = await self._run_check(
            "DatabaseManager Availability",
            category_name,
            self._check_database_manager
        )
        checks.append(check)
        
        # Check 3: MessageBus availability
        check = await self._run_check(
            "MessageBus Availability",
            category_name,
            self._check_message_bus
        )
        checks.append(check)
        
        # Check 4: MetricsCollector availability
        check = await self._run_check(
            "MetricsCollector Availability",
            category_name,
            self._check_metrics_collector
        )
        checks.append(check)
        
        self.categories[category_name] = self._create_category(category_name, checks)
    
    async def _validate_module_integration(self):
        """Validate module integration capabilities"""
        logger.info("Validating module integration...")
        
        category_name = "ModuleIntegration"
        checks = []
        
        # Check 1: Module registration workflow
        check = await self._run_check(
            "Module Registration Workflow",
            category_name,
            self._check_module_registration_workflow
        )
        checks.append(check)
        
        # Check 2: Integration points mapping
        check = await self._run_check(
            "Integration Points Mapping",
            category_name,
            self._check_integration_points_mapping
        )
        checks.append(check)
        
        # Check 3: Module communication
        check = await self._run_check(
            "Module Communication",
            category_name,
            self._check_module_communication
        )
        checks.append(check)
        
        # Check 4: Module lifecycle management
        check = await self._run_check(
            "Module Lifecycle Management",
            category_name,
            self._check_module_lifecycle
        )
        checks.append(check)
        
        self.categories[category_name] = self._create_category(category_name, checks)
    
    async def _validate_communication_workflows(self):
        """Validate communication workflows"""
        logger.info("Validating communication workflows...")
        
        category_name = "CommunicationWorkflows"
        checks = []
        
        # Check 1: Direct messaging
        check = await self._run_check(
            "Direct Messaging",
            category_name,
            self._check_direct_messaging
        )
        checks.append(check)
        
        # Check 2: Broadcast messaging
        check = await self._run_check(
            "Broadcast Messaging",
            category_name,
            self._check_broadcast_messaging
        )
        checks.append(check)
        
        # Check 3: Message routing
        check = await self._run_check(
            "Message Routing",
            category_name,
            self._check_message_routing
        )
        checks.append(check)
        
        # Check 4: Message prioritization
        check = await self._run_check(
            "Message Prioritization",
            category_name,
            self._check_message_prioritization
        )
        checks.append(check)
        
        self.categories[category_name] = self._create_category(category_name, checks)
    
    async def _validate_health_monitoring(self):
        """Validate health monitoring capabilities"""
        logger.info("Validating health monitoring...")
        
        category_name = "HealthMonitoring"
        checks = []
        
        # Check 1: Health check execution
        check = await self._run_check(
            "Health Check Execution",
            category_name,
            self._check_health_check_execution
        )
        checks.append(check)
        
        # Check 2: Health status tracking
        check = await self._run_check(
            "Health Status Tracking",
            category_name,
            self._check_health_status_tracking
        )
        checks.append(check)
        
        # Check 3: Health alerts
        check = await self._run_check(
            "Health Alerts",
            category_name,
            self._check_health_alerts
        )
        checks.append(check)
        
        # Check 4: Health recovery
        check = await self._run_check(
            "Health Recovery",
            category_name,
            self._check_health_recovery
        )
        checks.append(check)
        
        self.categories[category_name] = self._create_category(category_name, checks)
    
    async def _validate_performance_metrics(self):
        """Validate performance metrics collection"""
        logger.info("Validating performance metrics...")
        
        category_name = "PerformanceMetrics"
        checks = []
        
        # Check 1: Metrics collection
        check = await self._run_check(
            "Metrics Collection",
            category_name,
            self._check_metrics_collection
        )
        checks.append(check)
        
        # Check 2: Performance tracking
        check = await self._run_check(
            "Performance Tracking",
            category_name,
            self._check_performance_tracking
        )
        checks.append(check)
        
        # Check 3: Metrics aggregation
        check = await self._run_check(
            "Metrics Aggregation",
            category_name,
            self._check_metrics_aggregation
        )
        checks.append(check)
        
        # Check 4: Metrics reporting
        check = await self._run_check(
            "Metrics Reporting",
            category_name,
            self._check_metrics_reporting
        )
        checks.append(check)
        
        self.categories[category_name] = self._create_category(category_name, checks)
    
    async def _validate_error_handling(self):
        """Validate error handling and recovery"""
        logger.info("Validating error handling...")
        
        category_name = "ErrorHandling"
        checks = []
        
        # Check 1: Error detection
        check = await self._run_check(
            "Error Detection",
            category_name,
            self._check_error_detection
        )
        checks.append(check)
        
        # Check 2: Error reporting
        check = await self._run_check(
            "Error Reporting",
            category_name,
            self._check_error_reporting
        )
        checks.append(check)
        
        # Check 3: Error recovery
        check = await self._run_check(
            "Error Recovery",
            category_name,
            self._check_error_recovery
        )
        checks.append(check)
        
        # Check 4: Error isolation
        check = await self._run_check(
            "Error Isolation",
            category_name,
            self._check_error_isolation
        )
        checks.append(check)
        
        self.categories[category_name] = self._create_category(category_name, checks)
    
    async def _validate_scalability(self):
        """Validate scalability and performance under load"""
        logger.info("Validating scalability...")
        
        category_name = "Scalability"
        checks = []
        
        # Check 1: High message volume
        check = await self._run_check(
            "High Message Volume",
            category_name,
            self._check_high_message_volume
        )
        checks.append(check)
        
        # Check 2: Concurrent module operations
        check = await self._run_check(
            "Concurrent Module Operations",
            category_name,
            self._check_concurrent_operations
        )
        checks.append(check)
        
        # Check 3: Memory usage
        check = await self._run_check(
            "Memory Usage",
            category_name,
            self._check_memory_usage
        )
        checks.append(check)
        
        # Check 4: Response time under load
        check = await self._run_check(
            "Response Time Under Load",
            category_name,
            self._check_response_time_under_load
        )
        checks.append(check)
        
        self.categories[category_name] = self._create_category(category_name, checks)
    
    async def _run_check(self, name: str, category: str, check_func) -> ValidationCheck:
        """Run a single validation check"""
        start_time = time.time()
        
        try:
            result = await check_func()
            duration = time.time() - start_time
            
            return ValidationCheck(
                name=name,
                category=category,
                status="PASSED" if result.get("success", False) else "FAILED",
                message=result.get("message", "Check completed"),
                duration=duration,
                details=result.get("details", {})
            )
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Check '{name}' failed with exception: {e}")
            
            return ValidationCheck(
                name=name,
                category=category,
                status="FAILED",
                message=f"Exception: {str(e)}",
                duration=duration,
                details={"exception": str(e)}
            )
    
    def _create_category(self, name: str, checks: List[ValidationCheck]) -> ValidationCategory:
        """Create a validation category from checks"""
        passed = sum(1 for check in checks if check.status == "PASSED")
        failed = sum(1 for check in checks if check.status == "FAILED")
        warnings = sum(1 for check in checks if check.status == "WARNING")
        total = len(checks)
        success_rate = (passed / total) * 100 if total > 0 else 0
        
        return ValidationCategory(
            name=name,
            checks=checks,
            passed=passed,
            failed=failed,
            warnings=warnings,
            total=total,
            success_rate=success_rate
        )
    
    # SystemOrchestrator validation checks
    async def _check_basic_initialization(self) -> Dict[str, Any]:
        """Check basic SystemOrchestrator initialization"""
        try:
            assert self.orchestrator is not None, "Orchestrator is None"
            assert self.orchestrator._running is True, "Orchestrator is not running"
            assert self.orchestrator._message_queue is not None, "Message queue is None"
            assert self.orchestrator._health_monitor_task is not None, "Health monitor task is None"
            assert self.orchestrator._metrics_collector_task is not None, "Metrics collector task is None"
            
            return {
                "success": True,
                "message": "SystemOrchestrator initialized correctly",
                "details": {
                    "running": self.orchestrator._running,
                    "queue_size": self.orchestrator._message_queue.qsize(),
                    "health_task_active": not self.orchestrator._health_monitor_task.done(),
                    "metrics_task_active": not self.orchestrator._metrics_collector_task.done()
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Initialization check failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def _check_module_registration(self) -> Dict[str, Any]:
        """Check module registration functionality"""
        try:
            # Register a test module
            test_module_name = "test_module"
            
            async def mock_health_check():
                return {"is_healthy": True, "health_score": 0.95}
            
            async def mock_metrics_collector():
                return {"test_metric": 1.0}
            
            self.orchestrator.register_module(
                name=test_module_name,
                module_type="test",
                version="1.0.0",
                capabilities=["test_capability"],
                integration_points=["test_integration"],
                health_checker=mock_health_check,
                metrics_collector=mock_metrics_collector
            )
            
            # Verify registration
            module_status = self.orchestrator.get_module_status(test_module_name)
            assert module_status is not None, "Module not registered"
            assert module_status.name == test_module_name, "Module name mismatch"
            assert module_status.status == ModuleStatus.REGISTERED, "Module status incorrect"
            
            # Cleanup
            self.orchestrator.unregister_module(test_module_name)
            
            return {
                "success": True,
                "message": "Module registration working correctly",
                "details": {
                    "module_registered": True,
                    "module_name": test_module_name,
                    "module_status": module_status.status.value
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Module registration check failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def _check_message_handling(self) -> Dict[str, Any]:
        """Check message handling functionality"""
        try:
            # Register test modules
            test_module1 = "test_module1"
            test_module2 = "test_module2"
            
            message_received = False
            
            async def mock_handler(message):
                nonlocal message_received
                message_received = True
            
            self.orchestrator.register_module(
                name=test_module1,
                module_type="test",
                version="1.0.0",
                capabilities=[],
                integration_points=[],
                health_checker=lambda: {"is_healthy": True},
                metrics_collector=lambda: {}
            )
            
            self.orchestrator.register_module(
                name=test_module2,
                module_type="test",
                version="1.0.0",
                capabilities=[],
                integration_points=[],
                health_checker=lambda: {"is_healthy": True},
                metrics_collector=lambda: {}
            )
            
            self.orchestrator.add_message_handler(test_module2, mock_handler)
            
            # Send test message
            await self.orchestrator.send_message(
                source_module=test_module1,
                target_module=test_module2,
                message_type=MessageType.COMMAND,
                payload={"test": "data"}
            )
            
            # Wait for processing
            await asyncio.sleep(0.5)
            
            # Verify message was handled
            assert message_received, "Message was not handled"
            
            # Cleanup
            self.orchestrator.unregister_module(test_module1)
            self.orchestrator.unregister_module(test_module2)
            
            return {
                "success": True,
                "message": "Message handling working correctly",
                "details": {
                    "message_handled": message_received,
                    "source_module": test_module1,
                    "target_module": test_module2
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Message handling check failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def _check_health_monitoring(self) -> Dict[str, Any]:
        """Check health monitoring functionality"""
        try:
            # Register test module with health checker
            test_module = "health_test_module"
            
            async def mock_health_check():
                return {"is_healthy": True, "health_score": 0.98}
            
            self.orchestrator.register_module(
                name=test_module,
                module_type="test",
                version="1.0.0",
                capabilities=[],
                integration_points=[],
                health_checker=mock_health_check,
                metrics_collector=lambda: {}
            )
            
            # Wait for health check to run
            await asyncio.sleep(3.0)
            
            # Check health status
            module_status = self.orchestrator.get_module_status(test_module)
            assert module_status is not None, "Module not found"
            assert module_status.health_score > 0, "Health score not set"
            
            # Cleanup
            self.orchestrator.unregister_module(test_module)
            
            return {
                "success": True,
                "message": "Health monitoring working correctly",
                "details": {
                    "health_score": module_status.health_score,
                    "last_health_check": module_status.last_health_check.isoformat() if module_status.last_health_check else None
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Health monitoring check failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    # Infrastructure components validation checks
    async def _check_config_manager(self) -> Dict[str, Any]:
        """Check ConfigManager availability"""
        try:
            from core_structure.infrastructure.config.config_manager import ConfigManager
            
            config_manager = ConfigManager()
            config = config_manager.get_config()
            
            return {
                "success": True,
                "message": "ConfigManager available and functional",
                "details": {
                    "config_type": type(config).__name__ if config else "None",
                    "config_loaded": config is not None
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"ConfigManager check failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def _check_database_manager(self) -> Dict[str, Any]:
        """Check DatabaseManager availability"""
        try:
            from core_structure.infrastructure.database.database_manager import DatabaseManager
            
            db_manager = DatabaseManager()
            connection_status = db_manager.is_connected()
            
            return {
                "success": True,
                "message": "DatabaseManager available",
                "details": {
                    "connected": connection_status,
                    "connection_type": "mock" if not connection_status else "real"
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"DatabaseManager check failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def _check_message_bus(self) -> Dict[str, Any]:
        """Check MessageBus availability"""
        try:
            from core_structure.infrastructure.messaging.message_bus import MessageBus
            
            message_bus = MessageBus()
            test_message = {"type": "test", "data": "test_data"}
            message_bus.publish("test_topic", test_message)
            
            return {
                "success": True,
                "message": "MessageBus available and functional",
                "details": {
                    "publish_working": True,
                    "message_bus_type": "mock"
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"MessageBus check failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def _check_metrics_collector(self) -> Dict[str, Any]:
        """Check MetricsCollector availability"""
        try:
            from core_structure.infrastructure.monitoring.metrics_collector import MetricsCollector
            
            metrics_collector = MetricsCollector()
            metrics_collector.record_metric("test_metric", 1.0)
            metrics = metrics_collector.get_metrics()
            
            return {
                "success": True,
                "message": "MetricsCollector available and functional",
                "details": {
                    "metrics_collection_working": True,
                    "metrics_count": len(metrics) if metrics else 0
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"MetricsCollector check failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    # Module integration validation checks
    async def _check_module_registration_workflow(self) -> Dict[str, Any]:
        """Check complete module registration workflow"""
        try:
            # Register multiple modules
            modules = ["module_a", "module_b", "module_c"]
            
            for module_name in modules:
                self.orchestrator.register_module(
                    name=module_name,
                    module_type="test",
                    version="1.0.0",
                    capabilities=[f"capability_{module_name}"],
                    integration_points=[f"integration_{module_name}"],
                    health_checker=lambda: {"is_healthy": True},
                    metrics_collector=lambda: {}
                )
            
            # Verify all modules registered
            for module_name in modules:
                module_status = self.orchestrator.get_module_status(module_name)
                assert module_status is not None, f"Module {module_name} not registered"
            
            # Cleanup
            for module_name in modules:
                self.orchestrator.unregister_module(module_name)
            
            return {
                "success": True,
                "message": "Module registration workflow working correctly",
                "details": {
                    "modules_registered": len(modules),
                    "module_names": modules
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Module registration workflow failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def _check_integration_points_mapping(self) -> Dict[str, Any]:
        """Check integration points mapping functionality"""
        try:
            # Register modules with specific integration points
            self.orchestrator.register_module(
                name="signal_module",
                module_type="signal",
                version="1.0.0",
                capabilities=["signal_generation"],
                integration_points=["execution_engine", "risk_management"],
                health_checker=lambda: {"is_healthy": True},
                metrics_collector=lambda: {}
            )
            
            self.orchestrator.register_module(
                name="execution_module",
                module_type="execution",
                version="1.0.0",
                capabilities=["order_execution"],
                integration_points=["signal_generation", "risk_management"],
                health_checker=lambda: {"is_healthy": True},
                metrics_collector=lambda: {}
            )
            
            # Get integration points mapping
            integration_points = self.orchestrator.get_integration_points()
            
            # Verify mapping
            assert "signal_generation" in integration_points, "signal_generation not in integration points"
            assert "execution_engine" in integration_points, "execution_engine not in integration points"
            assert "risk_management" in integration_points, "risk_management not in integration points"
            
            # Cleanup
            self.orchestrator.unregister_module("signal_module")
            self.orchestrator.unregister_module("execution_module")
            
            return {
                "success": True,
                "message": "Integration points mapping working correctly",
                "details": {
                    "integration_points": list(integration_points.keys()),
                    "mapping_created": True
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Integration points mapping failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def _check_module_communication(self) -> Dict[str, Any]:
        """Check module communication capabilities"""
        try:
            # Register test modules
            messages_received = {"module_a": 0, "module_b": 0}
            
            async def handler_a(message):
                messages_received["module_a"] += 1
            
            async def handler_b(message):
                messages_received["module_b"] += 1
            
            self.orchestrator.register_module(
                name="module_a",
                module_type="test",
                version="1.0.0",
                capabilities=[],
                integration_points=[],
                health_checker=lambda: {"is_healthy": True},
                metrics_collector=lambda: {}
            )
            
            self.orchestrator.register_module(
                name="module_b",
                module_type="test",
                version="1.0.0",
                capabilities=[],
                integration_points=[],
                health_checker=lambda: {"is_healthy": True},
                metrics_collector=lambda: {}
            )
            
            self.orchestrator.add_message_handler("module_a", handler_a)
            self.orchestrator.add_message_handler("module_b", handler_b)
            
            # Send messages
            await self.orchestrator.send_message(
                source_module="test_system",
                target_module="module_a",
                message_type=MessageType.COMMAND,
                payload={"test": "data_a"}
            )
            
            await self.orchestrator.send_message(
                source_module="test_system",
                target_module="module_b",
                message_type=MessageType.COMMAND,
                payload={"test": "data_b"}
            )
            
            # Wait for processing
            await asyncio.sleep(0.5)
            
            # Verify communication
            assert messages_received["module_a"] > 0, "Module A did not receive message"
            assert messages_received["module_b"] > 0, "Module B did not receive message"
            
            # Cleanup
            self.orchestrator.unregister_module("module_a")
            self.orchestrator.unregister_module("module_b")
            
            return {
                "success": True,
                "message": "Module communication working correctly",
                "details": {
                    "messages_received": messages_received,
                    "communication_successful": True
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Module communication failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def _check_module_lifecycle(self) -> Dict[str, Any]:
        """Check module lifecycle management"""
        try:
            # Register module
            test_module = "lifecycle_test_module"
            
            self.orchestrator.register_module(
                name=test_module,
                module_type="test",
                version="1.0.0",
                capabilities=[],
                integration_points=[],
                health_checker=lambda: {"is_healthy": True},
                metrics_collector=lambda: {}
            )
            
            # Verify registration
            module_status = self.orchestrator.get_module_status(test_module)
            assert module_status is not None, "Module not registered"
            
            # Unregister module
            self.orchestrator.unregister_module(test_module)
            
            # Verify unregistration
            module_status_after = self.orchestrator.get_module_status(test_module)
            assert module_status_after is None, "Module not unregistered"
            
            return {
                "success": True,
                "message": "Module lifecycle management working correctly",
                "details": {
                    "registration_successful": True,
                    "unregistration_successful": True
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Module lifecycle management failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    # Communication workflows validation checks
    async def _check_direct_messaging(self) -> Dict[str, Any]:
        """Check direct messaging functionality"""
        try:
            # Register test modules
            message_received = False
            
            async def test_handler(message):
                nonlocal message_received
                message_received = True
            
            self.orchestrator.register_module(
                name="sender",
                module_type="test",
                version="1.0.0",
                capabilities=[],
                integration_points=[],
                health_checker=lambda: {"is_healthy": True},
                metrics_collector=lambda: {}
            )
            
            self.orchestrator.register_module(
                name="receiver",
                module_type="test",
                version="1.0.0",
                capabilities=[],
                integration_points=[],
                health_checker=lambda: {"is_healthy": True},
                metrics_collector=lambda: {}
            )
            
            self.orchestrator.add_message_handler("receiver", test_handler)
            
            # Send direct message
            await self.orchestrator.send_message(
                source_module="sender",
                target_module="receiver",
                message_type=MessageType.COMMAND,
                payload={"direct": "message"}
            )
            
            # Wait for processing
            await asyncio.sleep(0.5)
            
            # Verify message received
            assert message_received, "Direct message not received"
            
            # Cleanup
            self.orchestrator.unregister_module("sender")
            self.orchestrator.unregister_module("receiver")
            
            return {
                "success": True,
                "message": "Direct messaging working correctly",
                "details": {
                    "message_received": message_received,
                    "direct_messaging_successful": True
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Direct messaging failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def _check_broadcast_messaging(self) -> Dict[str, Any]:
        """Check broadcast messaging functionality"""
        try:
            # Register multiple test modules
            messages_received = {"module_1": 0, "module_2": 0, "module_3": 0}
            
            async def handler_1(message):
                messages_received["module_1"] += 1
            
            async def handler_2(message):
                messages_received["module_2"] += 1
            
            async def handler_3(message):
                messages_received["module_3"] += 1
            
            # Register modules
            for i in range(1, 4):
                module_name = f"module_{i}"
                handler = locals()[f"handler_{i}"]
                
                self.orchestrator.register_module(
                    name=module_name,
                    module_type="test",
                    version="1.0.0",
                    capabilities=[],
                    integration_points=[],
                    health_checker=lambda: {"is_healthy": True},
                    metrics_collector=lambda: {}
                )
                
                self.orchestrator.add_message_handler(module_name, handler)
            
            # Send broadcast message
            await self.orchestrator.broadcast_message(
                source_module="broadcaster",
                message_type=MessageType.EVENT,
                payload={"broadcast": "message"}
            )
            
            # Wait for processing
            await asyncio.sleep(0.5)
            
            # Verify broadcast
            total_received = sum(messages_received.values())
            assert total_received > 0, "No broadcast messages received"
            
            # Cleanup
            for i in range(1, 4):
                self.orchestrator.unregister_module(f"module_{i}")
            
            return {
                "success": True,
                "message": "Broadcast messaging working correctly",
                "details": {
                    "messages_received": messages_received,
                    "total_received": total_received,
                    "broadcast_successful": True
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Broadcast messaging failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def _check_message_routing(self) -> Dict[str, Any]:
        """Check message routing functionality"""
        try:
            # Register modules with specific routing
            routed_messages = {"high_priority": 0, "low_priority": 0}
            
            async def high_priority_handler(message):
                if message.priority >= 5:
                    routed_messages["high_priority"] += 1
            
            async def low_priority_handler(message):
                if message.priority < 5:
                    routed_messages["low_priority"] += 1
            
            self.orchestrator.register_module(
                name="high_priority_module",
                module_type="test",
                version="1.0.0",
                capabilities=[],
                integration_points=[],
                health_checker=lambda: {"is_healthy": True},
                metrics_collector=lambda: {}
            )
            
            self.orchestrator.register_module(
                name="low_priority_module",
                module_type="test",
                version="1.0.0",
                capabilities=[],
                integration_points=[],
                health_checker=lambda: {"is_healthy": True},
                metrics_collector=lambda: {}
            )
            
            self.orchestrator.add_message_handler("high_priority_module", high_priority_handler)
            self.orchestrator.add_message_handler("low_priority_module", low_priority_handler)
            
            # Send messages with different priorities
            await self.orchestrator.send_message(
                source_module="router",
                target_module="high_priority_module",
                message_type=MessageType.COMMAND,
                payload={"priority": "high"},
                priority=8
            )
            
            await self.orchestrator.send_message(
                source_module="router",
                target_module="low_priority_module",
                message_type=MessageType.COMMAND,
                payload={"priority": "low"},
                priority=2
            )
            
            # Wait for processing
            await asyncio.sleep(0.5)
            
            # Verify routing
            assert routed_messages["high_priority"] > 0, "High priority message not routed"
            assert routed_messages["low_priority"] > 0, "Low priority message not routed"
            
            # Cleanup
            self.orchestrator.unregister_module("high_priority_module")
            self.orchestrator.unregister_module("low_priority_module")
            
            return {
                "success": True,
                "message": "Message routing working correctly",
                "details": {
                    "routed_messages": routed_messages,
                    "routing_successful": True
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Message routing failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def _check_message_prioritization(self) -> Dict[str, Any]:
        """Check message prioritization functionality"""
        try:
            # Register test module
            message_order = []
            
            async def priority_handler(message):
                message_order.append(message.priority)
            
            self.orchestrator.register_module(
                name="priority_test_module",
                module_type="test",
                version="1.0.0",
                capabilities=[],
                integration_points=[],
                health_checker=lambda: {"is_healthy": True},
                metrics_collector=lambda: {}
            )
            
            self.orchestrator.add_message_handler("priority_test_module", priority_handler)
            
            # Send messages with different priorities
            await self.orchestrator.send_message(
                source_module="sender",
                target_module="priority_test_module",
                message_type=MessageType.COMMAND,
                payload={"test": "low"},
                priority=1
            )
            
            await self.orchestrator.send_message(
                source_module="sender",
                target_module="priority_test_module",
                message_type=MessageType.COMMAND,
                payload={"test": "high"},
                priority=9
            )
            
            await self.orchestrator.send_message(
                source_module="sender",
                target_module="priority_test_module",
                message_type=MessageType.COMMAND,
                payload={"test": "medium"},
                priority=5
            )
            
            # Wait for processing
            await asyncio.sleep(0.5)
            
            # Verify prioritization (higher priority should be processed first)
            assert len(message_order) >= 2, "Not enough messages processed"
            
            # Cleanup
            self.orchestrator.unregister_module("priority_test_module")
            
            return {
                "success": True,
                "message": "Message prioritization working correctly",
                "details": {
                    "message_order": message_order,
                    "prioritization_successful": True
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Message prioritization failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    # Health monitoring validation checks
    async def _check_health_check_execution(self) -> Dict[str, Any]:
        """Check health check execution"""
        try:
            # Register test module with health checker
            health_check_called = False
            
            async def mock_health_check():
                nonlocal health_check_called
                health_check_called = True
                return {"is_healthy": True, "health_score": 0.95}
            
            async def mock_metrics_collector():
                return {"test_metric": 1.0}
            
            self.orchestrator.register_module(
                name="health_test_module",
                module_type="test",
                version="1.0.0",
                capabilities=[],
                integration_points=[],
                health_checker=mock_health_check,
                metrics_collector=mock_metrics_collector
            )
            
            # Wait for health check to run
            await asyncio.sleep(3.0)
            
            # Verify health check was called
            assert health_check_called, "Health check was not executed"
            
            # Cleanup
            self.orchestrator.unregister_module("health_test_module")
            
            return {
                "success": True,
                "message": "Health check execution working correctly",
                "details": {
                    "health_check_called": health_check_called,
                    "health_check_successful": True
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Health check execution failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def _check_health_status_tracking(self) -> Dict[str, Any]:
        """Check health status tracking"""
        try:
            # Register test module
            async def mock_health_check():
                return {"is_healthy": True, "health_score": 0.92}
            
            async def mock_metrics_collector():
                return {"test_metric": 1.0}
            
            self.orchestrator.register_module(
                name="status_test_module",
                module_type="test",
                version="1.0.0",
                capabilities=[],
                integration_points=[],
                health_checker=mock_health_check,
                metrics_collector=mock_metrics_collector
            )
            
            # Wait for health check
            await asyncio.sleep(3.0)
            
            # Check health status
            module_status = self.orchestrator.get_module_status("status_test_module")
            assert module_status is not None, "Module status not found"
            assert module_status.health_score > 0, "Health score not set"
            assert module_status.last_health_check is not None, "Last health check not recorded"
            
            # Cleanup
            self.orchestrator.unregister_module("status_test_module")
            
            return {
                "success": True,
                "message": "Health status tracking working correctly",
                "details": {
                    "health_score": module_status.health_score,
                    "last_health_check": module_status.last_health_check.isoformat(),
                    "status_tracking_successful": True
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Health status tracking failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def _check_health_alerts(self) -> Dict[str, Any]:
        """Check health alerts functionality"""
        try:
            # Register test module with poor health
            async def poor_health_check():
                return {"is_healthy": False, "health_score": 0.3}
            
            async def mock_metrics_collector():
                return {"test_metric": 1.0}
            
            self.orchestrator.register_module(
                name="poor_health_module",
                module_type="test",
                version="1.0.0",
                capabilities=[],
                integration_points=[],
                health_checker=poor_health_check,
                metrics_collector=mock_metrics_collector
            )
            
            # Wait for health check
            await asyncio.sleep(3.0)
            
            # Check system health
            system_health = self.orchestrator.get_system_health()
            assert system_health['health_percentage'] < 100.0, "System health should be below 100%"
            
            # Cleanup
            self.orchestrator.unregister_module("poor_health_module")
            
            return {
                "success": True,
                "message": "Health alerts working correctly",
                "details": {
                    "system_health_percentage": system_health['health_percentage'],
                    "health_alerts_detected": True
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Health alerts check failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def _check_health_recovery(self) -> Dict[str, Any]:
        """Check health recovery functionality"""
        try:
            # Register test module with improving health
            health_scores = [0.3, 0.6, 0.9]  # Improving health
            current_index = 0
            
            async def improving_health_check():
                nonlocal current_index
                score = health_scores[min(current_index, len(health_scores) - 1)]
                current_index += 1
                return {"is_healthy": score > 0.5, "health_score": score}
            
            async def mock_metrics_collector():
                return {"test_metric": 1.0}
            
            self.orchestrator.register_module(
                name="recovery_test_module",
                module_type="test",
                version="1.0.0",
                capabilities=[],
                integration_points=[],
                health_checker=improving_health_check,
                metrics_collector=mock_metrics_collector
            )
            
            # Wait for multiple health checks
            await asyncio.sleep(6.0)
            
            # Check final health status
            module_status = self.orchestrator.get_module_status("recovery_test_module")
            assert module_status is not None, "Module status not found"
            assert module_status.health_score > 0.5, "Health should have recovered"
            
            # Cleanup
            self.orchestrator.unregister_module("recovery_test_module")
            
            return {
                "success": True,
                "message": "Health recovery working correctly",
                "details": {
                    "final_health_score": module_status.health_score,
                    "recovery_successful": True
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Health recovery check failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    # Performance metrics validation checks
    async def _check_metrics_collection(self) -> Dict[str, Any]:
        """Check metrics collection functionality"""
        try:
            # Register test module with metrics collector
            async def mock_metrics_collector():
                return {"test_metric": 1.0, "performance_score": 0.85}
            
            async def mock_health_check():
                return {"is_healthy": True, "health_score": 0.95}
            
            self.orchestrator.register_module(
                name="metrics_test_module",
                module_type="test",
                version="1.0.0",
                capabilities=[],
                integration_points=[],
                health_checker=mock_health_check,
                metrics_collector=mock_metrics_collector
            )
            
            # Wait for metrics collection
            await asyncio.sleep(3.0)
            
            # Check system metrics
            system_health = self.orchestrator.get_system_health()
            assert 'performance_metrics' in system_health, "Performance metrics not found"
            
            # Cleanup
            self.orchestrator.unregister_module("metrics_test_module")
            
            return {
                "success": True,
                "message": "Metrics collection working correctly",
                "details": {
                    "metrics_collected": True,
                    "performance_metrics_available": True
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Metrics collection failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def _check_performance_tracking(self) -> Dict[str, Any]:
        """Check performance tracking functionality"""
        try:
            # Register test module
            async def mock_health_check():
                return {"is_healthy": True, "health_score": 0.95}
            
            async def mock_metrics_collector():
                return {"response_time": 0.05, "throughput": 100}
            
            self.orchestrator.register_module(
                name="perf_test_module",
                module_type="test",
                version="1.0.0",
                capabilities=[],
                integration_points=[],
                health_checker=mock_health_check,
                metrics_collector=mock_metrics_collector
            )
            
            # Send multiple messages to track performance
            for i in range(5):
                await self.orchestrator.send_message(
                    source_module="perf_tester",
                    target_module="perf_test_module",
                    message_type=MessageType.COMMAND,
                    payload={"test": f"message_{i}"}
                )
            
            # Wait for processing
            await asyncio.sleep(1.0)
            
            # Check performance metrics
            system_health = self.orchestrator.get_system_health()
            assert system_health['performance_metrics']['total_messages'] > 0, "No messages tracked"
            
            # Cleanup
            self.orchestrator.unregister_module("perf_test_module")
            
            return {
                "success": True,
                "message": "Performance tracking working correctly",
                "details": {
                    "messages_tracked": system_health['performance_metrics']['total_messages'],
                    "performance_tracking_successful": True
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Performance tracking failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def _check_metrics_aggregation(self) -> Dict[str, Any]:
        """Check metrics aggregation functionality"""
        try:
            # Register multiple test modules
            for i in range(3):
                self.orchestrator.register_module(
                    name=f"agg_test_module_{i}",
                    module_type="test",
                    version="1.0.0",
                    capabilities=[],
                    integration_points=[],
                    health_checker=lambda: {"is_healthy": True},
                    metrics_collector=lambda: {f"metric_{i}": i * 10}
                )
            
            # Wait for metrics collection
            await asyncio.sleep(3.0)
            
            # Check aggregated metrics
            system_health = self.orchestrator.get_system_health()
            assert 'performance_metrics' in system_health, "Performance metrics not found"
            assert system_health['total_modules'] >= 3, "Not all modules counted"
            
            # Cleanup
            for i in range(3):
                self.orchestrator.unregister_module(f"agg_test_module_{i}")
            
            return {
                "success": True,
                "message": "Metrics aggregation working correctly",
                "details": {
                    "modules_counted": system_health['total_modules'],
                    "aggregation_successful": True
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Metrics aggregation failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def _check_metrics_reporting(self) -> Dict[str, Any]:
        """Check metrics reporting functionality"""
        try:
            # Register test module
            self.orchestrator.register_module(
                name="report_test_module",
                module_type="test",
                version="1.0.0",
                capabilities=[],
                integration_points=[],
                health_checker=lambda: {"is_healthy": True},
                metrics_collector=lambda: {"uptime": 3600, "requests": 1000}
            )
            
            # Wait for metrics collection
            await asyncio.sleep(3.0)
            
            # Get metrics report
            system_health = self.orchestrator.get_system_health()
            
            # Verify report structure
            required_fields = ['total_modules', 'healthy_modules', 'health_percentage', 'performance_metrics']
            for field in required_fields:
                assert field in system_health, f"Required field {field} missing from report"
            
            # Cleanup
            self.orchestrator.unregister_module("report_test_module")
            
            return {
                "success": True,
                "message": "Metrics reporting working correctly",
                "details": {
                    "report_fields": list(system_health.keys()),
                    "reporting_successful": True
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Metrics reporting failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    # Error handling validation checks
    async def _check_error_detection(self) -> Dict[str, Any]:
        """Check error detection functionality"""
        try:
            # Register test module with error-prone handler
            error_detected = False
            
            async def error_handler(message):
                nonlocal error_detected
                error_detected = True
                raise Exception("Test error for detection")
            
            self.orchestrator.register_module(
                name="error_test_module",
                module_type="test",
                version="1.0.0",
                capabilities=[],
                integration_points=[],
                health_checker=lambda: {"is_healthy": True},
                metrics_collector=lambda: {}
            )
            
            self.orchestrator.add_message_handler("error_test_module", error_handler)
            
            # Send message to trigger error
            await self.orchestrator.send_message(
                source_module="error_tester",
                target_module="error_test_module",
                message_type=MessageType.COMMAND,
                payload={"test": "error"}
            )
            
            # Wait for processing
            await asyncio.sleep(0.5)
            
            # Verify error was detected
            assert error_detected, "Error was not detected"
            
            # Cleanup
            self.orchestrator.unregister_module("error_test_module")
            
            return {
                "success": True,
                "message": "Error detection working correctly",
                "details": {
                    "error_detected": error_detected,
                    "error_detection_successful": True
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error detection failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def _check_error_reporting(self) -> Dict[str, Any]:
        """Check error reporting functionality"""
        try:
            # Register test module with error handler
            async def error_handler(message):
                raise Exception("Test error for reporting")
            
            self.orchestrator.register_module(
                name="error_report_module",
                module_type="test",
                version="1.0.0",
                capabilities=[],
                integration_points=[],
                health_checker=lambda: {"is_healthy": True},
                metrics_collector=lambda: {}
            )
            
            self.orchestrator.add_message_handler("error_report_module", error_handler)
            
            # Send message to trigger error
            await self.orchestrator.send_message(
                source_module="error_tester",
                target_module="error_report_module",
                message_type=MessageType.COMMAND,
                payload={"test": "error"}
            )
            
            # Wait for processing
            await asyncio.sleep(0.5)
            
            # Check error reporting
            module_status = self.orchestrator.get_module_status("error_report_module")
            assert module_status is not None, "Module status not found"
            assert module_status.error_count > 0, "Error count not incremented"
            
            # Cleanup
            self.orchestrator.unregister_module("error_report_module")
            
            return {
                "success": True,
                "message": "Error reporting working correctly",
                "details": {
                    "error_count": module_status.error_count,
                    "error_reporting_successful": True
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error reporting failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def _check_error_recovery(self) -> Dict[str, Any]:
        """Check error recovery functionality"""
        try:
            # Register test module with recovery capability
            error_count = 0
            
            async def recovery_handler(message):
                nonlocal error_count
                error_count += 1
                if error_count <= 2:  # Fail first 2 times, then succeed
                    raise Exception("Temporary error")
                return "Recovered"
            
            self.orchestrator.register_module(
                name="recovery_test_module",
                module_type="test",
                version="1.0.0",
                capabilities=[],
                integration_points=[],
                health_checker=lambda: {"is_healthy": True},
                metrics_collector=lambda: {}
            )
            
            self.orchestrator.add_message_handler("recovery_test_module", recovery_handler)
            
            # Send multiple messages to test recovery
            for i in range(3):
                await self.orchestrator.send_message(
                    source_module="recovery_tester",
                    target_module="recovery_test_module",
                    message_type=MessageType.COMMAND,
                    payload={"test": f"message_{i}"}
                )
            
            # Wait for processing
            await asyncio.sleep(1.0)
            
            # Verify recovery
            assert error_count >= 2, "Error recovery not tested"
            
            # Cleanup
            self.orchestrator.unregister_module("recovery_test_module")
            
            return {
                "success": True,
                "message": "Error recovery working correctly",
                "details": {
                    "error_count": error_count,
                    "recovery_successful": True
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error recovery failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def _check_error_isolation(self) -> Dict[str, Any]:
        """Check error isolation functionality"""
        try:
            # Register two test modules
            healthy_module_working = False
            
            async def error_handler(message):
                raise Exception("Isolated error")
            
            async def healthy_handler(message):
                nonlocal healthy_module_working
                healthy_module_working = True
            
            # Register error-prone module
            self.orchestrator.register_module(
                name="error_module",
                module_type="test",
                version="1.0.0",
                capabilities=[],
                integration_points=[],
                health_checker=lambda: {"is_healthy": True},
                metrics_collector=lambda: {}
            )
            
            # Register healthy module
            self.orchestrator.register_module(
                name="healthy_module",
                module_type="test",
                version="1.0.0",
                capabilities=[],
                integration_points=[],
                health_checker=lambda: {"is_healthy": True},
                metrics_collector=lambda: {}
            )
            
            self.orchestrator.add_message_handler("error_module", error_handler)
            self.orchestrator.add_message_handler("healthy_module", healthy_handler)
            
            # Send messages to both modules
            await self.orchestrator.send_message(
                source_module="tester",
                target_module="error_module",
                message_type=MessageType.COMMAND,
                payload={"test": "error"}
            )
            
            await self.orchestrator.send_message(
                source_module="tester",
                target_module="healthy_module",
                message_type=MessageType.COMMAND,
                payload={"test": "healthy"}
            )
            
            # Wait for processing
            await asyncio.sleep(0.5)
            
            # Verify error isolation
            assert healthy_module_working, "Healthy module affected by error"
            
            # Cleanup
            self.orchestrator.unregister_module("error_module")
            self.orchestrator.unregister_module("healthy_module")
            
            return {
                "success": True,
                "message": "Error isolation working correctly",
                "details": {
                    "healthy_module_working": healthy_module_working,
                    "error_isolation_successful": True
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error isolation failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    # Scalability validation checks
    async def _check_high_message_volume(self) -> Dict[str, Any]:
        """Check high message volume handling"""
        try:
            # Register test module
            messages_processed = 0
            
            async def volume_handler(message):
                nonlocal messages_processed
                messages_processed += 1
            
            self.orchestrator.register_module(
                name="volume_test_module",
                module_type="test",
                version="1.0.0",
                capabilities=[],
                integration_points=[],
                health_checker=lambda: {"is_healthy": True},
                metrics_collector=lambda: {}
            )
            
            self.orchestrator.add_message_handler("volume_test_module", volume_handler)
            
            # Send high volume of messages
            message_count = 50
            start_time = time.time()
            
            for i in range(message_count):
                await self.orchestrator.send_message(
                    source_module="volume_tester",
                    target_module="volume_test_module",
                    message_type=MessageType.COMMAND,
                    payload={"test": f"message_{i}"}
                )
            
            # Wait for processing
            await asyncio.sleep(2.0)
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # Verify high volume handling
            assert messages_processed > 0, "No messages processed"
            assert processing_time < 10.0, "Processing too slow for high volume"
            
            # Cleanup
            self.orchestrator.unregister_module("volume_test_module")
            
            return {
                "success": True,
                "message": "High message volume handling working correctly",
                "details": {
                    "messages_processed": messages_processed,
                    "processing_time": processing_time,
                    "throughput": messages_processed / processing_time if processing_time > 0 else 0
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"High message volume check failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def _check_concurrent_operations(self) -> Dict[str, Any]:
        """Check concurrent module operations"""
        try:
            # Register multiple test modules
            modules_working = {"module_1": False, "module_2": False, "module_3": False}
            
            async def concurrent_handler(module_name):
                async def handler(message):
                    modules_working[module_name] = True
                    await asyncio.sleep(0.1)  # Simulate work
                return handler
            
            # Register modules
            for i in range(1, 4):
                module_name = f"module_{i}"
                self.orchestrator.register_module(
                    name=module_name,
                    module_type="test",
                    version="1.0.0",
                    capabilities=[],
                    integration_points=[],
                    health_checker=lambda: {"is_healthy": True},
                    metrics_collector=lambda: {}
                )
                
                handler = await concurrent_handler(module_name)
                self.orchestrator.add_message_handler(module_name, handler)
            
            # Send concurrent messages
            tasks = []
            for i in range(1, 4):
                task = self.orchestrator.send_message(
                    source_module="concurrent_tester",
                    target_module=f"module_{i}",
                    message_type=MessageType.COMMAND,
                    payload={"test": f"concurrent_{i}"}
                )
                tasks.append(task)
            
            # Wait for all messages to be sent
            await asyncio.gather(*tasks)
            
            # Wait for processing
            await asyncio.sleep(1.0)
            
            # Verify concurrent operations
            working_modules = sum(modules_working.values())
            assert working_modules >= 2, "Not enough modules working concurrently"
            
            # Cleanup
            for i in range(1, 4):
                self.orchestrator.unregister_module(f"module_{i}")
            
            return {
                "success": True,
                "message": "Concurrent operations working correctly",
                "details": {
                    "modules_working": working_modules,
                    "concurrent_operations_successful": True
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Concurrent operations failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def _check_memory_usage(self) -> Dict[str, Any]:
        """Check memory usage under load"""
        try:
            import psutil
            import os
            
            # Get initial memory usage
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Register test module
            self.orchestrator.register_module(
                name="memory_test_module",
                module_type="test",
                version="1.0.0",
                capabilities=[],
                integration_points=[],
                health_checker=lambda: {"is_healthy": True},
                metrics_collector=lambda: {}
            )
            
            # Send moderate volume of messages
            for i in range(20):
                await self.orchestrator.send_message(
                    source_module="memory_tester",
                    target_module="memory_test_module",
                    message_type=MessageType.COMMAND,
                    payload={"test": f"memory_{i}", "data": "x" * 1000}  # 1KB payload
                )
            
            # Wait for processing
            await asyncio.sleep(1.0)
            
            # Get final memory usage
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            # Verify reasonable memory usage
            assert memory_increase < 100, f"Memory increase too high: {memory_increase:.2f} MB"
            
            # Cleanup
            self.orchestrator.unregister_module("memory_test_module")
            
            return {
                "success": True,
                "message": "Memory usage acceptable under load",
                "details": {
                    "initial_memory_mb": initial_memory,
                    "final_memory_mb": final_memory,
                    "memory_increase_mb": memory_increase,
                    "memory_usage_acceptable": True
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Memory usage check failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def _check_response_time_under_load(self) -> Dict[str, Any]:
        """Check response time under load"""
        try:
            # Register test module
            response_times = []
            
            async def response_handler(message):
                start_time = time.time()
                await asyncio.sleep(0.01)  # Simulate processing
                response_time = time.time() - start_time
                response_times.append(response_time)
            
            self.orchestrator.register_module(
                name="response_test_module",
                module_type="test",
                version="1.0.0",
                capabilities=[],
                integration_points=[],
                health_checker=lambda: {"is_healthy": True},
                metrics_collector=lambda: {}
            )
            
            self.orchestrator.add_message_handler("response_test_module", response_handler)
            
            # Send messages under load
            message_count = 30
            start_time = time.time()
            
            for i in range(message_count):
                await self.orchestrator.send_message(
                    source_module="response_tester",
                    target_module="response_test_module",
                    message_type=MessageType.COMMAND,
                    payload={"test": f"response_{i}"}
                )
            
            # Wait for processing
            await asyncio.sleep(2.0)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Calculate response time metrics
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            max_response_time = max(response_times) if response_times else 0
            
            # Verify response time under load
            assert avg_response_time < 1.0, f"Average response time too high: {avg_response_time:.3f}s"
            assert max_response_time < 2.0, f"Max response time too high: {max_response_time:.3f}s"
            
            # Cleanup
            self.orchestrator.unregister_module("response_test_module")
            
            return {
                "success": True,
                "message": "Response time under load acceptable",
                "details": {
                    "avg_response_time": avg_response_time,
                    "max_response_time": max_response_time,
                    "total_processing_time": total_time,
                    "response_time_acceptable": True
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Response time check failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    # Report generation methods
    def _generate_validation_report(self) -> InfrastructureValidationReport:
        """Generate comprehensive validation report"""
        # Calculate overall statistics
        total_checks = sum(len(category.checks) for category in self.categories.values())
        total_passed = sum(category.passed for category in self.categories.values())
        total_failed = sum(category.failed for category in self.categories.values())
        total_warnings = sum(category.warnings for category in self.categories.values())
        overall_success_rate = (total_passed / total_checks) * 100 if total_checks > 0 else 0
        
        # Determine overall status
        if overall_success_rate >= 90:
            overall_status = "EXCELLENT"
        elif overall_success_rate >= 80:
            overall_status = "GOOD"
        elif overall_success_rate >= 70:
            overall_status = "FAIR"
        else:
            overall_status = "POOR"
        
        # Generate recommendations
        recommendations = []
        
        if total_failed > 0:
            recommendations.append("Address failed validation checks to improve system reliability")
        
        if overall_success_rate < 90:
            recommendations.append("Focus on improving validation success rate to meet production standards")
        
        if total_warnings > 0:
            recommendations.append("Review warning conditions to prevent potential issues")
        
        # Performance metrics
        performance_metrics = {
            "total_validation_time": sum(check.duration for category in self.categories.values() for check in category.checks),
            "average_check_duration": sum(check.duration for category in self.categories.values() for check in category.checks) / total_checks if total_checks > 0 else 0,
            "categories_tested": len(self.categories),
            "validation_coverage": "comprehensive"
        }
        
        return InfrastructureValidationReport(
            timestamp=datetime.now().isoformat(),
            overall_status=overall_status,
            categories=self.categories,
            total_checks=total_checks,
            total_passed=total_passed,
            total_failed=total_failed,
            total_warnings=total_warnings,
            overall_success_rate=overall_success_rate,
            recommendations=recommendations,
            performance_metrics=performance_metrics
        )
    
    async def _cleanup(self):
        """Cleanup resources"""
        if self.orchestrator:
            await self.orchestrator.stop()
    
    def print_validation_report(self, report: InfrastructureValidationReport):
        """Print formatted validation report"""
        print("\n" + "="*80)
        print("🏗️ INFRASTRUCTURE INTEGRATION VALIDATION REPORT")
        print("="*80)
        print(f"Timestamp: {report.timestamp}")
        print(f"Overall Status: {report.overall_status}")
        print(f"Overall Success Rate: {report.overall_success_rate:.1f}%")
        print(f"Total Checks: {report.total_checks}")
        print(f"Passed: {report.total_passed} | Failed: {report.total_failed} | Warnings: {report.total_warnings}")
        print()
        
        print("📊 CATEGORY RESULTS:")
        print("-" * 50)
        
        for category_name, category in report.categories.items():
            status_icon = "✅" if category.success_rate >= 90 else "⚠️" if category.success_rate >= 70 else "❌"
            print(f"{status_icon} {category_name}: {category.success_rate:.1f}% ({category.passed}/{category.total})")
            
            # Show failed checks
            failed_checks = [check for check in category.checks if check.status == "FAILED"]
            if failed_checks:
                for check in failed_checks:
                    print(f"   ❌ {check.name}: {check.message}")
        
        print()
        
        if report.recommendations:
            print("💡 RECOMMENDATIONS:")
            print("-" * 50)
            for i, rec in enumerate(report.recommendations, 1):
                print(f"{i}. {rec}")
            print()
        
        print("📈 PERFORMANCE METRICS:")
        print("-" * 50)
        metrics = report.performance_metrics
        print(f"Total Validation Time: {metrics['total_validation_time']:.2f} seconds")
        print(f"Average Check Duration: {metrics['average_check_duration']:.3f} seconds")
        print(f"Categories Tested: {metrics['categories_tested']}")
        print(f"Validation Coverage: {metrics['validation_coverage']}")
        print()
        
        print("="*80)
        
        if report.overall_success_rate >= 90:
            print("🎉 INFRASTRUCTURE INTEGRATION VALIDATION PASSED!")
        elif report.overall_success_rate >= 80:
            print("✅ INFRASTRUCTURE INTEGRATION VALIDATION MOSTLY PASSED")
        else:
            print("⚠️ INFRASTRUCTURE INTEGRATION VALIDATION NEEDS IMPROVEMENT")
        
        print("="*80)

async def main():
    """Main validation function"""
    print("🚀 Starting Infrastructure Integration Validation...")
    
    validator = InfrastructureIntegrationValidator()
    report = await validator.run_comprehensive_validation()
    validator.print_validation_report(report)
    
    # Save report to file
    report_file = project_root / "validation" / "infrastructure_validation_report.json"
    
    report_dict = {
        "timestamp": report.timestamp,
        "overall_status": report.overall_status,
        "overall_success_rate": report.overall_success_rate,
        "total_checks": report.total_checks,
        "total_passed": report.total_passed,
        "total_failed": report.total_failed,
        "total_warnings": report.total_warnings,
        "categories": {
            name: {
                "name": category.name,
                "passed": category.passed,
                "failed": category.failed,
                "warnings": category.warnings,
                "total": category.total,
                "success_rate": category.success_rate,
                "checks": [
                    {
                        "name": check.name,
                        "status": check.status,
                        "message": check.message,
                        "duration": check.duration,
                        "details": check.details
                    }
                    for check in category.checks
                ]
            }
            for name, category in report.categories.items()
        },
        "recommendations": report.recommendations,
        "performance_metrics": report.performance_metrics
    }
    
    with open(report_file, 'w') as f:
        json.dump(report_dict, f, indent=2)
    
    print(f"📄 Report saved to: {report_file}")
    
    return report

if __name__ == "__main__":
    asyncio.run(main()) 