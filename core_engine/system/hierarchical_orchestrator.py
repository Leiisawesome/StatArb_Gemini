"""
Enhanced System Orchestrator - TradeDesk Architecture Compliance
===============================================================

Implements hierarchical control pattern: SystemOrchestrator → RiskManager → Trading Components
Ensures proper governance boundaries and authority limits at each layer.

Architecture Compliance:
- Layer 1: SystemOrchestrator (Operational Control)
- Layer 2: RiskManager (Trading Governance) 
- Layer 3: Trading Components (Operational Execution)
- Clear escalation procedures and accountability framework

Author: StatArb_Gemini Architecture Compliance
Version: 1.0.0 (TradeDesk Architecture)
"""

import asyncio
import logging
import threading
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import json

# Import interfaces to avoid circular imports
from .interfaces import ISystemComponent

logger = logging.getLogger(__name__)


class SystemStatus(Enum):
    """System operational status"""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"
    EMERGENCY = "emergency"
    SHUTDOWN = "shutdown"


class ComponentLayer(Enum):
    """Component layers in hierarchical control"""
    ORCHESTRATION = "orchestration"    # Layer 1: System control
    GOVERNANCE = "governance"          # Layer 2: Risk/Trading governance
    EXECUTION = "execution"            # Layer 3: Trading operations
    SUPPORT = "support"                # Support components


class AuthorityLevel(Enum):
    """Authority levels for different operations"""
    SYSTEM_CONTROL = "system_control"        # SystemOrchestrator only
    GOVERNANCE_CONTROL = "governance_control" # RiskManager authority
    OPERATIONAL = "operational"              # Component operations
    READ_ONLY = "read_only"                 # Monitoring only


@dataclass
class ComponentRegistration:
    """Component registration with hierarchical control info"""
    
    component_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    layer: ComponentLayer = ComponentLayer.SUPPORT
    authority_level: AuthorityLevel = AuthorityLevel.READ_ONLY
    
    # Hierarchical relationships
    reports_to: Optional[str] = None  # Parent component ID
    controls: List[str] = field(default_factory=list)  # Child component IDs
    
    # Component instance and metadata
    component_instance: Optional[Any] = None
    initialization_order: int = 100  # Lower numbers initialize first
    shutdown_order: int = 100       # Lower numbers shutdown last
    
    # Status tracking
    status: str = "unregistered"
    last_heartbeat: Optional[datetime] = None
    error_count: int = 0
    last_error: Optional[str] = None
    
    # Authority and permissions
    allowed_operations: Set[str] = field(default_factory=set)
    required_permissions: Set[str] = field(default_factory=set)
    
    # Health monitoring
    health_check_interval: int = 30  # seconds
    max_error_count: int = 5
    
    def update_status(self, status: str, error: Optional[str] = None):
        """Update component status"""
        self.status = status
        self.last_heartbeat = datetime.now()
        
        if error:
            self.error_count += 1
            self.last_error = error


@dataclass
class SystemOrchestrationConfig:
    """Configuration for system orchestration"""
    
    # Initialization settings
    component_startup_timeout: int = 60  # seconds
    initialization_retry_attempts: int = 3
    graceful_shutdown_timeout: int = 30  # seconds
    
    # Monitoring settings
    health_check_interval: int = 30      # seconds
    performance_monitoring_interval: int = 5  # seconds
    
    # Authority and governance
    enforce_hierarchical_control: bool = True
    require_risk_manager_authorization: bool = True
    emergency_override_enabled: bool = True
    
    # Escalation settings
    max_component_errors: int = 5
    escalation_timeout: int = 300  # 5 minutes
    
    # Resource management
    max_concurrent_operations: int = 100
    resource_allocation_timeout: int = 10  # seconds


class HierarchicalSystemOrchestrator(ISystemComponent):
    """
    Enhanced System Orchestrator - TradeDesk Architecture Compliance
    
    Implements institutional hierarchical control pattern:
    Layer 1: SystemOrchestrator (Operational Control)
    Layer 2: RiskManager (Trading Governance) 
    Layer 3: Trading Components (Operational Execution)
    
    Key Features:
    - Clear authority boundaries at each layer
    - Mandatory hierarchical authorization flow
    - Complete system lifecycle management
    - Emergency response coordination
    - Performance monitoring and resource allocation
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize hierarchical system orchestrator"""
        
        self.config = SystemOrchestrationConfig(**(config or {}))
        
        # Core system state
        self.system_status = SystemStatus.UNINITIALIZED
        self.system_id = str(uuid.uuid4())
        self.started_at: Optional[datetime] = None
        
        # Component registry with hierarchical tracking
        self.component_registry: Dict[str, ComponentRegistration] = {}
        self.layer_components: Dict[ComponentLayer, List[str]] = {
            layer: [] for layer in ComponentLayer
        }
        
        # Core governance components
        self.central_risk_manager: Optional[Any] = None
        self.risk_manager_id: Optional[str] = None
        
        # System monitoring
        self.system_metrics = {
            'total_components': 0,
            'operational_components': 0,
            'failed_components': 0,
            'system_uptime': 0.0,
            'total_operations': 0,
            'failed_operations': 0
        }
        
        # Control mechanisms
        self.initialization_lock = threading.Lock()
        self.operation_semaphore = asyncio.Semaphore(self.config.max_concurrent_operations)
        self.monitoring_task: Optional[asyncio.Task] = None
        
        # Emergency state
        self.emergency_mode = False
        self.emergency_initiated_at: Optional[datetime] = None
        
        logger.info("Hierarchical System Orchestrator initialized")
    
    async def initialize_system(self) -> bool:
        """
        Initialize the complete system with hierarchical control
        
        Initialization Order:
        1. Core system infrastructure
        2. Central Risk Manager (Layer 2 Governance)
        3. Trading components under Risk Manager control (Layer 3)
        4. Support components (monitoring, analytics, etc.)
        """
        
        try:
            with self.initialization_lock:
                if self.system_status != SystemStatus.UNINITIALIZED:
                    logger.warning("System already initialized")
                    return True
                
                self.system_status = SystemStatus.INITIALIZING
                logger.info("🚀 Initializing hierarchical system...")
                
                # Initialize Central Risk Manager first (Layer 2 Governance)
                # Note: CentralRiskManager will be imported dynamically to avoid circular imports
                if not await self._initialize_central_risk_manager():
                    logger.error("❌ Failed to initialize Central Risk Manager")
                    self.system_status = SystemStatus.EMERGENCY
                    return False
                
                # Initialize components in hierarchical order
                if not await self._initialize_components_hierarchically():
                    logger.error("❌ Failed to initialize components")
                    self.system_status = SystemStatus.EMERGENCY
                    return False
                
                # Establish hierarchical control relationships
                if not await self._establish_control_relationships():
                    logger.error("❌ Failed to establish control relationships")
                    self.system_status = SystemStatus.EMERGENCY
                    return False
                
                # Start system monitoring
                await self._start_system_monitoring()
                
                self.system_status = SystemStatus.READY
                self.started_at = datetime.now()
                
                logger.info("✅ Hierarchical system initialization completed")
                return True
                
        except Exception as e:
            logger.error(f"❌ System initialization failed: {e}")
            self.system_status = SystemStatus.EMERGENCY
            return False
    
    # ISystemComponent interface implementation
    async def initialize(self) -> bool:
        """Initialize component (ISystemComponent interface)"""
        return await self.initialize_system()
    
    async def start(self) -> bool:
        """Start component operations"""
        if self.system_status != SystemStatus.READY:
            logger.error("Cannot start system - not in ready state")
            return False
        
        try:
            self.system_status = SystemStatus.OPERATIONAL
            logger.info("✅ System started and operational")
            return True
        except Exception as e:
            logger.error(f"❌ System start failed: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop component operations"""
        try:
            await self.shutdown_system()
            return True
        except Exception as e:
            logger.error(f"❌ System stop failed: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        return {
            'healthy': self.system_status == SystemStatus.OPERATIONAL,
            'system_status': self.system_status.value,
            'component_count': len(self.component_registry),
            'operational_components': len([r for r in self.component_registry.values() 
                                         if r.status == 'operational']),
            'uptime_seconds': (datetime.now() - self.started_at).total_seconds() if self.started_at else 0,
            'emergency_mode': self.emergency_mode
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get component status"""
        return {
            'component_type': 'HierarchicalSystemOrchestrator',
            'system_status': self.system_status.value,
            'component_count': len(self.component_registry),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'emergency_mode': self.emergency_mode,
            'central_risk_manager_id': self.central_risk_manager_id
        }
    
    def register_component(self, name: str, component: Any, 
                         layer: ComponentLayer = ComponentLayer.SUPPORT,
                         authority_level: AuthorityLevel = AuthorityLevel.READ_ONLY,
                         initialization_order: int = 100,
                         reports_to: Optional[str] = None) -> str:
        """Register component with hierarchical control"""
        
        try:
            registration = ComponentRegistration(
                name=name,
                layer=layer,
                authority_level=authority_level,
                component_instance=component,
                initialization_order=initialization_order,
                reports_to=reports_to
            )
            
            # Store registration
            self.component_registry[registration.component_id] = registration
            self.layer_components[layer].append(registration.component_id)
            
            # Set allowed operations based on authority level
            registration.allowed_operations = self._get_allowed_operations(authority_level)
            
            logger.info(f"📝 Registered {name} (Layer: {layer.value}, Authority: {authority_level.value})")
            return registration.component_id
            
        except Exception as e:
            logger.error(f"❌ Failed to register component {name}: {e}")
            return ""
    
    def register_central_risk_manager(self, risk_manager: Any) -> str:
        """Register the Central Risk Manager as Layer 2 Governance"""
        
        self.central_risk_manager = risk_manager
        self.risk_manager_id = self.register_component(
            name="CentralRiskManager",
            component=risk_manager,
            layer=ComponentLayer.GOVERNANCE,
            authority_level=AuthorityLevel.GOVERNANCE_CONTROL,
            initialization_order=10  # High priority initialization
        )
        
        logger.info("🛡️ Central Risk Manager registered as governance layer")
        return self.risk_manager_id
    
    async def _initialize_central_risk_manager(self) -> bool:
        """Initialize the Central Risk Manager first"""
        
        try:
            if not self.central_risk_manager:
                logger.error("Central Risk Manager not registered")
                return False
            
            logger.info("🛡️ Initializing Central Risk Manager...")
            
            # Initialize with system-level configuration
            execution_config = {
                'max_market_impact': 0.05,
                'default_time_horizon': 300
            }
            
            success = await self.central_risk_manager.initialize(execution_config)
            
            if success:
                # Update registration status
                if self.risk_manager_id:
                    registration = self.component_registry[self.risk_manager_id]
                    registration.update_status("operational")
                
                logger.info("✅ Central Risk Manager initialized")
            else:
                logger.error("❌ Central Risk Manager initialization failed")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Central Risk Manager initialization error: {e}")
            return False
    
    async def _initialize_components_hierarchically(self) -> bool:
        """Initialize components in hierarchical order"""
        
        try:
            # Get components sorted by initialization order
            components_by_order = sorted(
                self.component_registry.items(),
                key=lambda x: x[1].initialization_order
            )
            
            initialized_count = 0
            
            for component_id, registration in components_by_order:
                # Skip if already initialized (like Central Risk Manager)
                if registration.status == "operational":
                    initialized_count += 1
                    continue
                
                logger.info(f"🔄 Initializing {registration.name}...")
                
                try:
                    registration.update_status("initializing")
                    
                    # Initialize component if it implements ISystemComponent
                    if hasattr(registration.component_instance, 'initialize'):
                        success = await registration.component_instance.initialize()
                        
                        if success:
                            registration.update_status("initialized")
                            initialized_count += 1
                            logger.info(f"✅ {registration.name} initialized")
                        else:
                            registration.update_status("failed", "Initialization failed")
                            logger.error(f"❌ {registration.name} initialization failed")
                    else:
                        # Assume non-interface components are ready
                        registration.update_status("initialized")
                        initialized_count += 1
                        logger.info(f"✅ {registration.name} registered (no initialization required)")
                        
                except Exception as e:
                    registration.update_status("failed", str(e))
                    logger.error(f"❌ {registration.name} initialization error: {e}")
            
            total_components = len(self.component_registry)
            success_rate = initialized_count / total_components if total_components > 0 else 0
            
            logger.info(f"Component initialization: {initialized_count}/{total_components} ({success_rate:.1%})")
            
            # Require at least 80% success rate
            return success_rate >= 0.8
            
        except Exception as e:
            logger.error(f"❌ Hierarchical component initialization failed: {e}")
            return False
    
    async def _establish_control_relationships(self) -> bool:
        """Establish hierarchical control relationships"""
        
        try:
            logger.info("🔗 Establishing hierarchical control relationships...")
            
            # Set up RiskManager control over trading components
            if self.central_risk_manager and self.risk_manager_id:
                trading_components = []
                
                # Find trading components that should report to RiskManager
                for component_id, registration in self.component_registry.items():
                    if (registration.layer == ComponentLayer.EXECUTION and 
                        registration.name != "CentralRiskManager"):
                        
                        # Set RiskManager as parent
                        registration.reports_to = self.risk_manager_id
                        trading_components.append(component_id)
                
                # Update RiskManager's controlled components
                if self.risk_manager_id in self.component_registry:
                    self.component_registry[self.risk_manager_id].controls = trading_components
                
                # Register trading components with RiskManager
                strategy_manager = None
                trading_engine = None
                
                for component_id in trading_components:
                    registration = self.component_registry[component_id]
                    
                    if "Strategy" in registration.name:
                        strategy_manager = registration.component_instance
                    elif "Trading" in registration.name or "Execution" in registration.name:
                        trading_engine = registration.component_instance
                
                # Set controlled components in RiskManager
                self.central_risk_manager.set_controlled_components(
                    strategy_manager=strategy_manager,
                    trading_engine=trading_engine
                )
                
                logger.info(f"✅ RiskManager control established over {len(trading_components)} components")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to establish control relationships: {e}")
            return False
    
    async def _start_system_monitoring(self):
        """Start continuous system monitoring"""
        
        try:
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
            logger.info("📊 System monitoring started")
            
        except Exception as e:
            logger.error(f"❌ Failed to start system monitoring: {e}")
    
    async def _monitoring_loop(self):
        """Continuous system monitoring loop"""
        
        logger.info("📊 System monitoring loop started")
        
        try:
            while self.system_status not in [SystemStatus.SHUTDOWN, SystemStatus.EMERGENCY]:
                # Health check all components
                await self._health_check_components()
                
                # Update system metrics
                self._update_system_metrics()
                
                # Check for emergency conditions
                await self._check_emergency_conditions()
                
                # Sleep until next monitoring cycle
                await asyncio.sleep(self.config.health_check_interval)
                
        except Exception as e:
            logger.error(f"❌ System monitoring error: {e}")
        
        logger.info("📊 System monitoring stopped")
    
    async def _health_check_components(self):
        """Perform health checks on all components"""
        
        try:
            for component_id, registration in self.component_registry.items():
                if hasattr(registration.component_instance, 'health_check'):
                    try:
                        health_status = await registration.component_instance.health_check()
                        
                        if health_status.get('healthy', False):
                            registration.update_status("operational")
                        else:
                            error_msg = health_status.get('error', 'Health check failed')
                            registration.update_status("unhealthy", error_msg)
                            
                    except Exception as e:
                        registration.update_status("unhealthy", str(e))
                else:
                    # Assume components without health checks are healthy if no recent errors
                    if registration.error_count == 0:
                        registration.update_status("operational")
                        
        except Exception as e:
            logger.error(f"❌ Health check error: {e}")
    
    def _update_system_metrics(self):
        """Update system performance metrics"""
        
        try:
            total_components = len(self.component_registry)
            operational_components = sum(
                1 for reg in self.component_registry.values() 
                if reg.status == "operational"
            )
            failed_components = sum(
                1 for reg in self.component_registry.values() 
                if reg.status in ["failed", "unhealthy"]
            )
            
            self.system_metrics.update({
                'total_components': total_components,
                'operational_components': operational_components,
                'failed_components': failed_components,
                'system_uptime': (datetime.now() - self.started_at).total_seconds() if self.started_at else 0
            })
            
        except Exception as e:
            logger.error(f"❌ Metrics update error: {e}")
    
    async def _check_emergency_conditions(self):
        """Check for conditions requiring emergency response"""
        
        try:
            # Check if RiskManager is unhealthy
            if (self.risk_manager_id and 
                self.component_registry[self.risk_manager_id].status != "operational"):
                
                await self._initiate_emergency_response("RiskManager unhealthy")
                return
            
            # Check component failure rate
            total_components = len(self.component_registry)
            failed_components = self.system_metrics['failed_components']
            
            if total_components > 0 and (failed_components / total_components) > 0.5:
                await self._initiate_emergency_response("High component failure rate")
                return
                
        except Exception as e:
            logger.error(f"❌ Emergency condition check error: {e}")
    
    async def _initiate_emergency_response(self, reason: str):
        """Initiate emergency response procedures"""
        
        try:
            if self.emergency_mode:
                return  # Already in emergency mode
            
            logger.critical(f"🚨 EMERGENCY RESPONSE INITIATED: {reason}")
            
            self.emergency_mode = True
            self.emergency_initiated_at = datetime.now()
            self.system_status = SystemStatus.EMERGENCY
            
            # Emergency shutdown of RiskManager
            if self.central_risk_manager:
                self.central_risk_manager.emergency_shutdown()
            
            # Stop all trading operations
            await self._emergency_stop_trading()
            
            logger.critical("🚨 EMERGENCY RESPONSE COMPLETED")
            
        except Exception as e:
            logger.error(f"❌ Emergency response failed: {e}")
    
    async def _emergency_stop_trading(self):
        """Emergency stop of all trading operations"""
        
        try:
            # Stop all execution layer components
            execution_components = self.layer_components[ComponentLayer.EXECUTION]
            
            for component_id in execution_components:
                registration = self.component_registry[component_id]
                
                if hasattr(registration.component_instance, 'emergency_stop'):
                    try:
                        await registration.component_instance.emergency_stop()
                        logger.warning(f"Emergency stopped: {registration.name}")
                    except Exception as e:
                        logger.error(f"Failed to emergency stop {registration.name}: {e}")
                        
        except Exception as e:
            logger.error(f"❌ Emergency stop failed: {e}")
    
    async def request_system_authorization(self, operation: str, component_id: str,
                                         details: Dict[str, Any]) -> bool:
        """Request system-level authorization for operations"""
        
        try:
            # Check if component is registered and authorized
            if component_id not in self.component_registry:
                logger.error(f"Unauthorized component request: {component_id}")
                return False
            
            registration = self.component_registry[component_id]
            
            # Check operation authorization
            if operation not in registration.allowed_operations:
                logger.error(f"Unauthorized operation {operation} for {registration.name}")
                return False
            
            # For trading operations, must go through RiskManager
            if (operation.startswith("trade_") and 
                registration.layer == ComponentLayer.EXECUTION and
                self.config.require_risk_manager_authorization):
                
                return await self._route_to_risk_manager(operation, component_id, details)
            
            # System-level operations require SYSTEM_CONTROL authority
            if (operation.startswith("system_") and 
                registration.authority_level != AuthorityLevel.SYSTEM_CONTROL):
                
                logger.error(f"Insufficient authority for {operation}")
                return False
            
            logger.info(f"✅ Authorized operation {operation} for {registration.name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Authorization request failed: {e}")
            return False
    
    async def _route_to_risk_manager(self, operation: str, component_id: str,
                                   details: Dict[str, Any]) -> bool:
        """Route trading operations to RiskManager for authorization"""
        
        try:
            if not self.central_risk_manager:
                logger.error("No RiskManager available for authorization")
                return False
            
            # Convert to trading decision request
            request = TradingDecisionRequest(
                requesting_component=component_id,
                justification=f"System operation: {operation}",
                **details
            )
            
            # Request authorization from RiskManager
            authorization = await self.central_risk_manager.authorize_trading_decision(request)
            
            # Check if authorized
            authorized = authorization.authorization_level.value != "rejected"
            
            if authorized:
                logger.info(f"✅ RiskManager authorized {operation}")
            else:
                logger.warning(f"❌ RiskManager rejected {operation}: {authorization.rejection_reason}")
            
            return authorized
            
        except Exception as e:
            logger.error(f"❌ RiskManager routing failed: {e}")
            return False
    
    def _get_allowed_operations(self, authority_level: AuthorityLevel) -> Set[str]:
        """Get allowed operations for authority level"""
        
        operations = {"health_check", "status_report", "metrics_report"}
        
        if authority_level == AuthorityLevel.OPERATIONAL:
            operations.update({"data_request", "signal_generation", "analytics_compute"})
        
        if authority_level == AuthorityLevel.GOVERNANCE_CONTROL:
            operations.update({"trade_authorization", "risk_assessment", "position_management"})
        
        if authority_level == AuthorityLevel.SYSTEM_CONTROL:
            operations.update({"system_shutdown", "emergency_stop", "component_restart"})
        
        return operations
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        
        return {
            'system_id': self.system_id,
            'status': self.system_status.value,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'emergency_mode': self.emergency_mode,
            'emergency_initiated_at': self.emergency_initiated_at.isoformat() if self.emergency_initiated_at else None,
            'metrics': self.system_metrics.copy(),
            'component_summary': {
                layer.value: len(components) 
                for layer, components in self.layer_components.items()
            },
            'risk_manager_status': (
                self.component_registry[self.risk_manager_id].status 
                if self.risk_manager_id else "not_registered"
            )
        }
    
    async def shutdown_system(self) -> bool:
        """Shutdown the system (alias for graceful_shutdown)"""
        return await self.graceful_shutdown()
    
    async def graceful_shutdown(self) -> bool:
        """Perform graceful system shutdown"""
        
        try:
            logger.info("🔄 Initiating graceful system shutdown...")
            
            self.system_status = SystemStatus.SHUTDOWN
            
            # Stop monitoring
            if self.monitoring_task:
                self.monitoring_task.cancel()
            
            # Shutdown components in reverse order
            components_by_shutdown_order = sorted(
                self.component_registry.items(),
                key=lambda x: x[1].shutdown_order,
                reverse=True
            )
            
            for component_id, registration in components_by_shutdown_order:
                try:
                    if registration.component_instance is not None:
                        shutdown_method = getattr(registration.component_instance, 'shutdown', None)
                        if shutdown_method is not None and callable(shutdown_method):
                            try:
                                await shutdown_method()
                                logger.info(f"✅ Shutdown: {registration.name}")
                            except Exception as shutdown_error:
                                logger.warning(f"⚠️ Shutdown method failed for {registration.name}: {shutdown_error}")
                        else:
                            logger.debug(f"📝 No shutdown method for {registration.name}")
                    
                    registration.update_status("shutdown")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to shutdown {registration.name}: {e}")
            
            logger.info("✅ Graceful system shutdown completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Graceful shutdown failed: {e}")
            return False


# Example usage
if __name__ == "__main__":
    async def test_hierarchical_orchestrator():
        """Test the hierarchical system orchestrator"""
        
        # Initialize orchestrator
        config = {
            'component_startup_timeout': 30,
            'health_check_interval': 10
        }
        
        orchestrator = HierarchicalSystemOrchestrator(config)
        
        # Create and register Central Risk Manager
        # Import CentralRiskManager dynamically to avoid circular imports
        from .central_risk_manager import CentralRiskManager
        risk_manager = CentralRiskManager()
        orchestrator.register_central_risk_manager(risk_manager)
        
        # Register mock components
        class MockComponent:
            def __init__(self, name):
                self.name = name
            
            async def initialize(self):
                return True
            
            async def health_check(self):
                return {'healthy': True}
        
        # Register components
        strategy_comp = MockComponent("StrategyManager")
        orchestrator.register_component(
            "StrategyManager", strategy_comp,
            ComponentLayer.EXECUTION, AuthorityLevel.OPERATIONAL,
            initialization_order=20
        )
        
        trading_comp = MockComponent("TradingEngine")
        orchestrator.register_component(
            "TradingEngine", trading_comp,
            ComponentLayer.EXECUTION, AuthorityLevel.OPERATIONAL,
            initialization_order=30
        )
        
        # Initialize system
        success = await orchestrator.initialize_system()
        print(f"System initialization: {'Success' if success else 'Failed'}")
        
        # Get system status
        status = orchestrator.get_system_status()
        print(f"System status: {status}")
        
        # Test authorization
        auth_result = await orchestrator.request_system_authorization(
            "health_check", "test_component", {}
        )
        print(f"Authorization test: {auth_result}")
        
        # Shutdown
        await asyncio.sleep(2)  # Let it run briefly
        await orchestrator.graceful_shutdown()
    
    # Run test
    asyncio.run(test_hierarchical_orchestrator())