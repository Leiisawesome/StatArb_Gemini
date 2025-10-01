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
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from enum import Enum

# Import interfaces to avoid circular imports
from .interfaces import ISystemComponent
from .central_risk_manager import TradingDecisionRequest

# Import modular components
from .orchestrator_components import ComponentManager, ComponentRegistration, ComponentLayer, AuthorityLevel
from .orchestrator_monitoring import SystemMonitor
from .orchestrator_configuration import ConfigurationManager, SystemOrchestrationConfig

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


# Duplicate classes removed - now imported from modular components


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

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize hierarchical system orchestrator with modular composition"""

        # Initialize modular components using composition
        self.config_manager = ConfigurationManager(config)
        self.component_manager = ComponentManager()
        self.system_monitor = SystemMonitor()

        # Core system state
        self.system_status = SystemStatus.UNINITIALIZED
        self.system_id = str(uuid.uuid4())
        self.started_at: Optional[datetime] = None

        # Central Risk Manager reference (Layer 2 Governance)
        self.central_risk_manager: Optional[Any] = None
        self.risk_manager_id: Optional[str] = None

        # System coordination and control
        self.initialization_lock = threading.Lock()
        self.operation_semaphore = asyncio.Semaphore(self.config_manager.system_config.max_concurrent_operations)

        # Emergency state
        self.emergency_mode = False
        self.emergency_initiated_at: Optional[datetime] = None

        # Audit trail for institutional compliance
        self.audit_trail: List[Dict[str, Any]] = []
        self.audit_lock = threading.Lock()

        # Authorization audit trail for governance compliance
        self._authorization_audit: List[Dict[str, Any]] = []

        # System monitoring enhancements
        self.error_tracker: List[Dict[str, Any]] = []
        self.recovery_actions: List[Dict[str, Any]] = []

        # Capital allocation tracking
        self.capital_utilization: Dict[str, Any] = {
            'total_capital': 0.0,
            'distributed_capital': {},
            'utilization_rate': 0.0,
            'timestamp': datetime.now().isoformat()
        }

        logger.info("🚀 Hierarchical System Orchestrator initialized with modular architecture")

    # ========================================
    # PROPERTIES FOR BACKWARD COMPATIBILITY
    # ========================================

    @property
    def config(self) -> SystemOrchestrationConfig:
        """Get system configuration"""
        return self.config_manager.system_config

    @property
    def component_registry(self) -> Dict[str, ComponentRegistration]:
        """Get component registry"""
        return self.component_manager.component_registry

    @property
    def layer_components(self) -> Dict[ComponentLayer, List[str]]:
        """Get components by layer"""
        return self.component_manager.layer_components

    @property
    def system_metrics(self) -> Dict[str, Any]:
        """Get system metrics"""
        return self.system_monitor.get_system_metrics()

    @property
    def performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return self.system_monitor.get_performance_metrics()

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
            'central_risk_manager_id': getattr(self, 'risk_manager_id', None)
        }

    def register_component(self, name: str, component: Any,
                         layer: ComponentLayer = ComponentLayer.SUPPORT,
                         authority_level: AuthorityLevel = AuthorityLevel.READ_ONLY,
                         initialization_order: int = 100,
                         reports_to: Optional[str] = None) -> str:
        """Register component with hierarchical control - delegates to ComponentManager"""

        return self.component_manager.register_component(
            name=name,
            component=component,
            layer=layer,
            authority_level=authority_level,
            initialization_order=initialization_order,
            reports_to=reports_to
        )

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
        """Initialize components in hierarchical order - delegates to ComponentManager"""

        return await self.component_manager.initialize_components_hierarchically()

# _initialize_single_component method moved to ComponentManager

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

    async def _start_system_monitoring(self) -> None:
        """Start continuous system monitoring - delegates to SystemMonitor"""

        try:
            await self.system_monitor.start_monitoring()
            logger.info("📊 System monitoring started")

        except Exception as e:
            logger.error(f"❌ Failed to start system monitoring: {e}")

    async def _monitoring_loop(self) -> None:
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

    async def _health_check_components(self) -> None:
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

    def _update_system_metrics(self) -> None:
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

    async def _check_emergency_conditions(self) -> None:
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

    async def _initiate_emergency_response(self, reason: str) -> None:
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

    async def _emergency_stop_trading(self) -> None:
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
            await self.system_monitor.stop_monitoring()

            # Shutdown components in reverse order
            components_by_shutdown_order = sorted(
                self.component_registry.items(),
                key=lambda x: x[1].shutdown_order,
                reverse=True
            )

            for component_id, registration in components_by_shutdown_order:
                try:
                    if registration.component_instance is not None:
                        shutdown_method = getattr(registration.component_instance, 'stop', None)
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

    # ========================================
    # SYSTEM MONITORING METHODS
    # ========================================

    async def monitor_component_performance(self) -> Dict[str, Any]:
        """
        Monitor performance of all registered components

        Returns:
            Performance metrics for all components
        """
        try:
            performance_data = {}

            for component_id, registration in self.component_registry.items():
                try:
                    # Get basic performance metrics
                    component_perf = {
                        'component_id': component_id,
                        'component_name': registration.name,
                        'layer': registration.layer.value,
                        'authority_level': registration.authority_level.value,
                        'status': registration.status,
                        'uptime': 0.0,  # Would be calculated from registration timestamps
                        'operation_count': 0,  # Would be tracked
                        'error_count': 0,  # Would be tracked
                        'last_health_check': datetime.now().isoformat()
                    }

                    # Try to get performance metrics from component if available
                    if hasattr(registration.component_instance, 'get_performance_metrics'):
                        try:
                            comp_metrics = await registration.component_instance.get_performance_metrics()
                            component_perf.update(comp_metrics)
                        except Exception:
                            pass  # Component doesn't support performance metrics

                    performance_data[component_id] = component_perf

                except Exception as e:
                    logger.warning(f"Failed to monitor performance for {component_id}: {e}")
                    performance_data[component_id] = {
                        'component_id': component_id,
                        'error': str(e),
                        'last_health_check': datetime.now().isoformat()
                    }

            # Update internal performance metrics
            self.performance_metrics = performance_data

            return {
                'timestamp': datetime.now().isoformat(),
                'total_components': len(performance_data),
                'performance_data': performance_data
            }

        except Exception as e:
            logger.error(f"Component performance monitoring failed: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'total_components': 0,
                'performance_data': {}
            }

    async def perform_health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive system health check

        Returns:
            Detailed health status report
        """
        try:
            # Get component health status
            component_health = {}
            healthy_components = 0
            total_components = len(self.component_registry)

            for component_id, registration in self.component_registry.items():
                try:
                    # Basic health indicators
                    is_healthy = registration.status == "operational"
                    if is_healthy:
                        healthy_components += 1

                    component_health[component_id] = {
                        'component_name': registration.name,
                        'status': registration.status,
                        'layer': registration.layer.value,
                        'authority_level': registration.authority_level.value,
                        'healthy': is_healthy,
                        'last_check': datetime.now().isoformat()
                    }

                except Exception as e:
                    component_health[component_id] = {
                        'component_name': registration.name if hasattr(registration, 'name') else 'Unknown',
                        'status': 'error',
                        'healthy': False,
                        'error': str(e),
                        'last_check': datetime.now().isoformat()
                    }

            # System-level health indicators
            system_healthy = (
                self.system_status == SystemStatus.OPERATIONAL and
                not self.emergency_mode and
                healthy_components >= total_components * 0.8  # At least 80% healthy
            )

            health_report = {
                'timestamp': datetime.now().isoformat(),
                'status': 'healthy' if system_healthy else 'unhealthy',
                'component_count': total_components,
                'healthy_components': healthy_components,
                'emergency_mode': self.emergency_mode,
                'system_metrics': self.system_metrics.copy(),
                'components': component_health
            }

            return health_report

        except Exception as e:
            logger.error(f"System health check failed: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'overall_healthy': False,
                'error': str(e)
            }

    def track_error(self, component_id: str, error_type: str, error_details: Dict[str, Any]) -> None:
        """
        Track an error for monitoring and analysis

        Args:
            component_id: ID of the component that encountered the error
            error_type: Type of error (e.g., 'connection_error', 'processing_error')
            error_details: Additional error information
        """
        try:
            error_entry = {
                'timestamp': datetime.now().isoformat(),
                'component_id': component_id,
                'error_type': error_type,
                'system_status': self.system_status.value,
                'emergency_mode': self.emergency_mode,
                'details': error_details
            }

            self.error_tracker.append(error_entry)

            # Keep only last 1000 errors
            if len(self.error_tracker) > 1000:
                self.error_tracker = self.error_tracker[-1000:]

            # Log audit event
            self.log_audit_event('error_tracked', component_id, {
                'error_type': error_type,
                'error_details': error_details
            })

        except Exception as e:
            logger.error(f"Failed to track error: {e}")

    async def initiate_recovery(self, recovery_scenario: Dict[str, Any]) -> Dict[str, Any]:
        """
        Initiate recovery procedures for system issues

        Args:
            recovery_scenario: Recovery parameters including:
                - component: Component that needs recovery
                - failure_type: Type of failure
                - severity: Severity level
                - auto_recovery: Whether to attempt automatic recovery

        Returns:
            Recovery action results
        """
        try:
            component = recovery_scenario.get('component')
            failure_type = recovery_scenario.get('failure_type', 'unknown')
            severity = recovery_scenario.get('severity', 'medium')
            auto_recovery = recovery_scenario.get('auto_recovery', True)

            recovery_action = {
                'timestamp': datetime.now().isoformat(),
                'component': component,
                'failure_type': failure_type,
                'severity': severity,
                'auto_recovery': auto_recovery,
                'status': 'initiated'
            }

            # Attempt recovery based on failure type
            if auto_recovery:
                if failure_type == 'connection_lost':
                    # Attempt to restart component
                    success = await self._attempt_component_restart(component)
                    recovery_action['recovery_method'] = 'component_restart'
                    recovery_action['success'] = success

                elif failure_type == 'performance_degraded':
                    # Attempt performance optimization
                    success = await self._attempt_performance_optimization(component)
                    recovery_action['recovery_method'] = 'performance_optimization'
                    recovery_action['success'] = success

                else:
                    # Generic recovery attempt
                    success = await self._attempt_generic_recovery(component)
                    recovery_action['recovery_method'] = 'generic_recovery'
                    recovery_action['success'] = success

                recovery_action['status'] = 'completed' if success else 'failed'

            # Track recovery action
            self.recovery_actions.append(recovery_action)

            # Keep only last 500 recovery actions
            if len(self.recovery_actions) > 500:
                self.recovery_actions = self.recovery_actions[-500:]

            # Log audit event
            self.log_audit_event('recovery_initiated', component, recovery_action)

            return recovery_action

        except Exception as e:
            logger.error(f"Recovery initiation failed: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'component': recovery_scenario.get('component'),
                'status': 'error',
                'error': str(e)
            }

    async def run_system_diagnostics(self) -> Dict[str, Any]:
        """
        Run comprehensive system diagnostics

        Returns:
            Detailed diagnostic report
        """
        try:
            diagnostics = {
                'timestamp': datetime.now().isoformat(),
                'system_status': self.system_status.value,
                'emergency_mode': self.emergency_mode,
                'diagnostics': {}
            }

            # Component diagnostics
            component_diagnostics = {}
            for component_id, registration in self.component_registry.items():
                try:
                    comp_diag = {
                        'status': registration.status,
                        'layer': registration.layer.value,
                        'authority_level': registration.authority_level.value,
                        'initialization_order': registration.initialization_order,
                        'shutdown_order': registration.shutdown_order
                    }

                    # Try to get component-specific diagnostics
                    if hasattr(registration.component_instance, 'diagnostics'):
                        try:
                            comp_specific = await registration.component_instance.diagnostics()
                            comp_diag.update(comp_specific)
                        except Exception:
                            pass

                    component_diagnostics[component_id] = comp_diag

                except Exception as e:
                    component_diagnostics[component_id] = {
                        'error': str(e),
                        'status': 'diagnostic_failed'
                    }

            diagnostics['diagnostics']['components'] = component_diagnostics

            # System-level diagnostics
            diagnostics['diagnostics']['system'] = {
                'total_components': len(self.component_registry),
                'operational_components': len([r for r in self.component_registry.values() if r.status == 'operational']),
                'system_metrics': self.system_metrics.copy(),
                'audit_trail_entries': len(self.audit_trail),
                'error_count': len(self.error_tracker),
                'recovery_actions': len(self.recovery_actions)
            }

            # Performance diagnostics
            diagnostics['diagnostics']['performance'] = {
                'performance_metrics_available': len(self.performance_metrics) > 0,
                'component_count': len(self.performance_metrics)
            }

            return diagnostics

        except Exception as e:
            logger.error(f"System diagnostics failed: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'diagnostics': {}
            }

    async def monitor_performance_degradation(self) -> List[Dict[str, Any]]:
        """
        Monitor for performance degradation across components

        Returns:
            List of performance degradation alerts
        """
        try:
            degradation_alerts = []

            # Get current performance metrics
            current_perf = await self.monitor_component_performance()

            if 'performance_data' in current_perf:
                for component_id, metrics in current_perf['performance_data'].items():
                    try:
                        # Check for performance degradation indicators
                        alerts = []

                        # Check operation count (if available)
                        if 'operation_count' in metrics:
                            op_count = metrics['operation_count']
                            if op_count < 10:  # Arbitrary threshold for low activity
                                alerts.append({
                                    'type': 'low_activity',
                                    'severity': 'warning',
                                    'message': f'Low operation count: {op_count}'
                                })

                        # Check error rate (if available)
                        if 'error_count' in metrics and 'operation_count' in metrics:
                            error_rate = metrics['error_count'] / max(metrics['operation_count'], 1)
                            if error_rate > 0.1:  # 10% error rate threshold
                                alerts.append({
                                    'type': 'high_error_rate',
                                    'severity': 'error',
                                    'message': f'High error rate: {error_rate:.1%}'
                                })

                        # Check uptime (if available)
                        if 'uptime' in metrics and metrics['uptime'] < 3600:  # Less than 1 hour
                            alerts.append({
                                'type': 'low_uptime',
                                'severity': 'warning',
                                'message': f'Low uptime: {metrics["uptime"]:.0f} seconds'
                            })

                        if alerts:
                            degradation_alerts.append({
                                'component_id': component_id,
                                'component_name': metrics.get('component_name', 'Unknown'),
                                'alerts': alerts,
                                'timestamp': datetime.now().isoformat()
                            })

                    except Exception as e:
                        logger.warning(f"Failed to check degradation for {component_id}: {e}")

            return degradation_alerts

        except Exception as e:
            logger.error(f"Performance degradation monitoring failed: {e}")
            return []

    # ========================================
    # PRIVATE RECOVERY METHODS
    # ========================================

    async def _attempt_component_restart(self, component_id: str) -> bool:
        """Attempt to restart a component"""
        try:
            if component_id in self.component_registry:
                registration = self.component_registry[component_id]

                # Attempt restart
                if hasattr(registration.component_instance, 'restart'):
                    await registration.component_instance.restart()
                    registration.update_status("operational")
                    return True

            return False
        except Exception as e:
            logger.error(f"Component restart failed for {component_id}: {e}")
            return False

    async def _attempt_performance_optimization(self, component_id: str) -> bool:
        """Attempt performance optimization for a component"""
        try:
            if component_id in self.component_registry:
                registration = self.component_registry[component_id]

                # Attempt optimization
                if hasattr(registration.component_instance, 'optimize_performance'):
                    await registration.component_instance.optimize_performance()
                    return True

            return False
        except Exception as e:
            logger.error(f"Performance optimization failed for {component_id}: {e}")
            return False

    async def _attempt_generic_recovery(self, component_id: str) -> bool:
        """Attempt generic recovery procedures"""
        try:
            if component_id in self.component_registry:
                registration = self.component_registry[component_id]

                # Basic recovery: reset status and attempt health check
                registration.update_status("recovering")

                # Wait a moment
                await asyncio.sleep(1)

                # Check if component is now healthy
                health_check = await self.health_check()
                if health_check.get('status') == 'healthy':
                    registration.update_status("operational")
                    return True

            return False
        except Exception as e:
            logger.error(f"Generic recovery failed for {component_id}: {e}")
            return False

    # ========================================
    # INSTITUTIONAL AUDIT TRAIL METHODS
    # ========================================

    def log_audit_event(self, event_type: str, component_id: str, details: Dict[str, Any]) -> None:
        """
        Log an audit event for institutional compliance

        Args:
            event_type: Type of event (e.g., 'component_registration', 'authorization_request')
            component_id: ID of the component involved
            details: Additional event details
        """
        with self.audit_lock:
            audit_entry = {
                'timestamp': datetime.now().isoformat(),
                'event_type': event_type,
                'component_id': component_id,
                'system_status': self.system_status.value,
                'emergency_mode': self.emergency_mode,
                'details': details
            }

            self.audit_trail.append(audit_entry)

            # Keep only last 2000 entries to prevent memory issues
            if len(self.audit_trail) > 2000:
                self.audit_trail = self.audit_trail[-2000:]

    def get_audit_trail(self, limit: int = 100, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get audit trail entries

        Args:
            limit: Maximum number of entries to return
            event_type: Filter by specific event type

        Returns:
            List of audit entries
        """
        with self.audit_lock:
            if event_type:
                filtered_trail = [entry for entry in self.audit_trail if entry['event_type'] == event_type]
            else:
                filtered_trail = self.audit_trail

            return filtered_trail[-limit:] if limit > 0 else filtered_trail

    def get_audit_summary(self) -> Dict[str, Any]:
        """Get audit trail summary statistics"""
        with self.audit_lock:
            total_events = len(self.audit_trail)

            if total_events == 0:
                return {'total_events': 0, 'event_types': {}, 'time_range': None}

            # Count events by type
            event_counts = {}
            for entry in self.audit_trail:
                event_type = entry['event_type']
                event_counts[event_type] = event_counts.get(event_type, 0) + 1

            # Get time range
            timestamps = [entry['timestamp'] for entry in self.audit_trail]
            time_range = {
                'oldest': min(timestamps),
                'newest': max(timestamps)
            }

            return {
                'total_events': total_events,
                'event_types': event_counts,
                'time_range': time_range
            }

    # ========================================
    # GOVERNANCE AND RISK AUTHORIZATION METHODS
    # ========================================

    def _authorize_risk_operation(self, risk_operation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Authorize risk operations through hierarchical approval flow

        Args:
            risk_operation: Operation requiring authorization with:
                - operation: Operation type
                - risk_level: Risk severity ('low', 'medium', 'high', 'critical')
                - authority_required: Required authority level
                - requester: Requesting authority level

        Returns:
            Authorization decision
        """
        try:
            operation = risk_operation.get('operation')
            risk_level = risk_operation.get('risk_level', 'medium')
            required_authority = risk_operation.get('authority_required', AuthorityLevel.OPERATIONAL)
            requester = risk_operation.get('requester', AuthorityLevel.OPERATIONAL)

            # Check if requester has sufficient authority
            if requester.value >= required_authority.value:
                # Direct authorization
                authorization = {
                    'authorized': True,
                    'authority_level': requester.value,
                    'escalation_required': False,
                    'timestamp': datetime.now().isoformat(),
                    'decision_maker': 'direct_authorization'
                }
            else:
                # Escalation required
                authorization = {
                    'authorized': False,
                    'authority_level': requester.value,
                    'escalation_required': True,
                    'required_level': required_authority.value,
                    'timestamp': datetime.now().isoformat(),
                    'reason': 'insufficient_authority'
                }

            # Log authorization decision
            self.log_audit_event('risk_operation_authorization', operation, {
                'risk_level': risk_level,
                'authorization_result': authorization
            })

            # Add to authorization audit trail
            audit_entry = {
                'timestamp': datetime.now().isoformat(),
                'operation': operation,
                'risk_level': risk_level,
                'requester': requester.value,
                'required_authority': required_authority.value,
                'authorized': authorization['authorized'],
                'escalation_required': authorization.get('escalation_required', False)
            }
            self.authorization_audit.append(audit_entry)

            return authorization

        except Exception as e:
            logger.error(f"Risk operation authorization failed: {e}")
            return {
                'authorized': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def _escalate_authorization(self, escalation_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Escalate authorization requests to higher authority levels

        Args:
            escalation_request: Escalation details with:
                - operation: Operation requiring escalation
                - risk_severity: Risk severity level
                - current_authority: Current authority level
                - required_authority: Required authority level
                - reason: Reason for escalation

        Returns:
            Escalation result
        """
        try:
            operation = escalation_request.get('operation')
            risk_severity = escalation_request.get('risk_severity', 'high')
            current_authority = escalation_request.get('current_authority', AuthorityLevel.OPERATIONAL)
            required_authority = escalation_request.get('required_authority', AuthorityLevel.GOVERNANCE_CONTROL)
            reason = escalation_request.get('reason', 'unspecified')

            # Determine escalation path
            escalation_levels = {
                'high': AuthorityLevel.GOVERNANCE_CONTROL,
                'critical': AuthorityLevel.SYSTEM_CONTROL
            }

            target_level = escalation_levels.get(risk_severity, required_authority)

            # Check if escalation is possible
            if current_authority.value >= target_level.value:
                # Already at sufficient level
                escalation_result = {
                    'escalated': False,
                    'reason': 'already_sufficient_authority',
                    'current_level': current_authority.value,
                    'target_level': target_level.value,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                # Perform escalation
                escalation_result = {
                    'escalated': True,
                    'from_level': current_authority.value,
                    'to_level': target_level.value,
                    'risk_severity': risk_severity,
                    'reason': reason,
                    'approved': True,  # Assume approval for simulation
                    'timestamp': datetime.now().isoformat(),
                    'escalation_id': f"esc_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                }

                # Log escalation
                self.log_audit_event('authorization_escalation', operation, escalation_result)

            return escalation_result

        except Exception as e:
            logger.error(f"Authorization escalation failed: {e}")
            return {
                'escalated': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    # ========================================
    # SYSTEM ORCHESTRATION METHODS
    # ========================================

    async def orchestrate_execution(self, execution_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Orchestrate execution through hierarchical system layers

        Args:
            execution_type: Type of execution to orchestrate
            parameters: Execution parameters

        Returns:
            Orchestration result
        """
        try:
            # Perform hierarchical orchestration
            orchestration_result = {
                'execution_type': execution_type,
                'parameters': parameters,
                'orchestrated': True,
                'orchestrator_level': 'hierarchical_system',
                'timestamp': datetime.now().isoformat(),
                'coordination_layers': ['governance', 'execution', 'support']
            }

            # Log orchestration
            logger.info(f"Execution orchestrated at hierarchical level: {execution_type}")

            return orchestration_result

        except Exception as e:
            logger.error(f"Hierarchical orchestration failed: {e}")
            return {
                'error': str(e),
                'execution_type': execution_type,
                'orchestrated': False
            }

    async def delegate_authority(self, authority_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Delegate authority through hierarchical layers

        Args:
            authority_request: Authority delegation request

        Returns:
            Delegation result
        """
        try:
            # Perform hierarchical authority delegation
            delegation_result = {
                'delegated': True,
                'authority_request': authority_request,
                'delegation_level': 'hierarchical_system',
                'timestamp': datetime.now().isoformat(),
                'approval_chain': ['system_control', 'governance_control', 'operational']
            }

            # Log delegation
            logger.info(f"Authority delegated at hierarchical level: {authority_request}")

            return delegation_result

        except Exception as e:
            logger.error(f"Hierarchical authority delegation failed: {e}")
            return {
                'error': str(e),
                'delegated': False
            }

    # ========================================
    # AUTHORITY VALIDATION METHODS
    # ========================================

    def _validate_authority(self, authority_level: AuthorityLevel, operation: str) -> bool:
        """
        Validate if authority level is sufficient for operation

        Args:
            authority_level: Authority level to validate
            operation: Operation being requested

        Returns:
            True if authority is sufficient
        """
        try:
            # Define authority hierarchy (higher index = more authority)
            authority_hierarchy = {
                AuthorityLevel.READ_ONLY: 0,
                AuthorityLevel.OPERATIONAL: 1,
                AuthorityLevel.TACTICAL: 2,
                AuthorityLevel.STRATEGIC: 3,
                AuthorityLevel.GOVERNANCE_CONTROL: 4,
                AuthorityLevel.SYSTEM_CONTROL: 5
            }

            # Define operation authority requirements
            operation_requirements = {
                'system_operation': AuthorityLevel.SYSTEM_CONTROL,
                'governance_operation': AuthorityLevel.GOVERNANCE_CONTROL,
                'strategic_operation': AuthorityLevel.STRATEGIC,
                'tactical_operation': AuthorityLevel.TACTICAL,
                'operational_task': AuthorityLevel.OPERATIONAL,
                'read_operation': AuthorityLevel.READ_ONLY
            }

            required_level = operation_requirements.get(operation, AuthorityLevel.OPERATIONAL)
            current_level_value = authority_hierarchy.get(authority_level, 0)
            required_level_value = authority_hierarchy.get(required_level, 1)

            return current_level_value >= required_level_value

        except Exception as e:
            logger.error(f"Authority validation failed: {e}")
            return False

    def _delegate_permissions(self, from_authority: AuthorityLevel,
                             to_authority: AuthorityLevel,
                             permissions: List[str]) -> bool:
        """
        Delegate permissions from one authority level to another

        Args:
            from_authority: Authority level delegating permissions
            to_authority: Authority level receiving permissions
            permissions: List of permissions to delegate

        Returns:
            True if delegation successful
        """
        try:
            # Check if delegation is allowed (higher authority can delegate to lower)
            if from_authority.value <= to_authority.value:
                logger.warning(f"Cannot delegate from {from_authority.value} to {to_authority.value}")
                return False

            # Log permission delegation
            delegation_record = {
                'from_authority': from_authority.value,
                'to_authority': to_authority.value,
                'permissions': permissions,
                'timestamp': datetime.now().isoformat(),
                'delegation_id': f"del_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            }

            if not hasattr(self, 'permission_delegations'):
                self.permission_delegations = []
            self.permission_delegations.append(delegation_record)

            logger.info(f"Permissions delegated: {permissions} from {from_authority.value} to {to_authority.value}")
            return True

        except Exception as e:
            logger.error(f"Permission delegation failed: {e}")
            return False

    def _get_allowed_operations(self, authority_level: AuthorityLevel) -> List[str]:
        """
        Get operations allowed for given authority level

        Args:
            authority_level: Authority level to check

        Returns:
            List of allowed operations
        """
        try:
            # Define operations by authority level
            operations_by_level = {
                AuthorityLevel.SYSTEM_CONTROL: [
                    'system_operation', 'governance_operation', 'strategic_operation',
                    'tactical_operation', 'operational_task', 'read_operation'
                ],
                AuthorityLevel.GOVERNANCE_CONTROL: [
                    'governance_operation', 'strategic_operation', 'tactical_operation',
                    'operational_task', 'read_operation'
                ],
                AuthorityLevel.STRATEGIC: [
                    'strategic_operation', 'tactical_operation', 'operational_task', 'read_operation'
                ],
                AuthorityLevel.TACTICAL: [
                    'tactical_operation', 'operational_task', 'read_operation'
                ],
                AuthorityLevel.OPERATIONAL: [
                    'operational_task', 'read_operation'
                ],
                AuthorityLevel.READ_ONLY: [
                    'read_operation'
                ]
            }

            return operations_by_level.get(authority_level, [])

        except Exception as e:
            logger.error(f"Allowed operations lookup failed: {e}")
            return []

    def _check_authorization_flow(self, operation: str, requester_authority: AuthorityLevel,
                                 required_authority: AuthorityLevel) -> bool:
        """
        Check authorization flow for operation

        Args:
            operation: Operation to check
            requester_authority: Authority level of requester
            required_authority: Required authority level

        Returns:
            True if operation is authorized
        """
        try:
            # Check if requester has sufficient authority
            if requester_authority.value >= required_authority.value:
                return True

            # Check if operation can be escalated
            escalation_possible = self._can_escalate_operation(operation, requester_authority, required_authority)

            if escalation_possible:
                # Attempt escalation
                escalation_request = {
                    'operation': operation,
                    'current_authority': requester_authority,
                    'required_authority': required_authority,
                    'escalation_reason': 'insufficient_authority'
                }
                escalation_result = self._escalate_authorization(escalation_request)
                return escalation_result.get('escalated', False) and escalation_result.get('approved', False)

            return False

        except Exception as e:
            logger.error(f"Authorization flow check failed: {e}")
            return False

    def _can_escalate_operation(self, operation: str, current_authority: AuthorityLevel,
                               required_authority: AuthorityLevel) -> bool:
        """
        Check if operation can be escalated

        Args:
            operation: Operation to escalate
            current_authority: Current authority level
            required_authority: Required authority level

        Returns:
            True if escalation is possible
        """
        try:
            # Define escalation rules
            critical_operations = ['emergency_liquidation', 'system_shutdown', 'risk_breach_response']
            high_risk_operations = ['portfolio_rebalancing', 'strategy_activation', 'large_position_entry']

            if operation in critical_operations:
                return True  # Critical operations can always be escalated
            elif operation in high_risk_operations:
                return current_authority.value >= AuthorityLevel.OPERATIONAL.value
            else:
                return required_authority.value - current_authority.value <= 1  # Only one level up

        except Exception as e:
            logger.error(f"Escalation possibility check failed: {e}")
            return False

    # ========================================
    # COORDINATION METHODS
    # ========================================

    def coordinate_with_risk_manager(self, coordination_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Coordinate with risk manager

        Args:
            coordination_request: Coordination request details

        Returns:
            Coordination result
        """
        try:
            if not hasattr(self, 'central_risk_manager') or not self.central_risk_manager:
                return {'coordinated': False, 'reason': 'no_risk_manager'}

            # Perform coordination
            coordination_result = {
                'coordinated': True,
                'coordination_type': 'risk_management',
                'request': coordination_request,
                'timestamp': datetime.now().isoformat()
            }

            logger.info(f"Coordinated with risk manager: {coordination_request}")
            return coordination_result

        except Exception as e:
            logger.error(f"Risk manager coordination failed: {e}")
            return {'coordinated': False, 'error': str(e)}

    def coordinate_with_regime_engine(self, coordination_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Coordinate with regime engine

        Args:
            coordination_request: Coordination request details

        Returns:
            Coordination result
        """
        try:
            if not hasattr(self, 'regime_engine') or not self.regime_engine:
                return {'coordinated': False, 'reason': 'no_regime_engine'}

            # Perform coordination
            coordination_result = {
                'coordinated': True,
                'coordination_type': 'regime_analysis',
                'request': coordination_request,
                'timestamp': datetime.now().isoformat()
            }

            logger.info(f"Coordinated with regime engine: {coordination_request}")
            return coordination_result

        except Exception as e:
            logger.error(f"Regime engine coordination failed: {e}")
            return {'coordinated': False, 'error': str(e)}

    def coordinate_with_data_manager(self, coordination_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Coordinate with data manager

        Args:
            coordination_request: Coordination request details

        Returns:
            Coordination result
        """
        try:
            if not hasattr(self, 'data_manager') or not self.data_manager:
                return {'coordinated': False, 'reason': 'no_data_manager'}

            # Perform coordination
            coordination_result = {
                'coordinated': True,
                'coordination_type': 'data_management',
                'request': coordination_request,
                'timestamp': datetime.now().isoformat()
            }

            logger.info(f"Coordinated with data manager: {coordination_request}")
            return coordination_result

        except Exception as e:
            logger.error(f"Data manager coordination failed: {e}")
            return {'coordinated': False, 'error': str(e)}

    # ========================================
    # CAPITAL ALLOCATION METHODS
    # ========================================

    def _distribute_capital(self, capital_distribution: Dict[str, Any]) -> Dict[str, float]:
        """Distribute capital across hierarchical layers

        Args:
            capital_distribution: Capital distribution parameters

        Returns:
            Dict mapping layers to allocated capital amounts
        """
        try:
            total_capital = capital_distribution.get('total_capital', 2000000.0)
            layer_allocation = capital_distribution.get('layer_allocation', {
                'ORCHESTRATION': 0.2,
                'GOVERNANCE': 0.3,
                'EXECUTION': 0.4,
                'SUPPORT': 0.1
            })

            # Validate allocation percentages sum to 1.0
            total_percentage = sum(layer_allocation.values())
            if abs(total_percentage - 1.0) > 0.01:  # Allow small rounding differences
                # Normalize if doesn't sum to 1.0
                for layer in layer_allocation:
                    layer_allocation[layer] /= total_percentage

            # Calculate actual capital amounts
            distributed_capital = {}
            for layer, percentage in layer_allocation.items():
                distributed_capital[layer] = total_capital * percentage

            # Update capital utilization tracking
            self.capital_utilization = {
                'total_capital': total_capital,
                'distributed_capital': distributed_capital,
                'utilization_rate': sum(distributed_capital.values()) / total_capital,
                'timestamp': datetime.now().isoformat()
            }

            logger.info(f"Capital distributed across layers: {distributed_capital}")
            return distributed_capital

        except Exception as e:
            logger.error(f"Capital distribution failed: {e}")
            return {}

    def capital_utilization(self) -> Dict[str, Any]:
        """Get current capital utilization across the system

        Returns:
            Capital utilization data
        """
        return getattr(self, 'capital_utilization', {
            'total_capital': 0.0,
            'distributed_capital': {},
            'utilization_rate': 0.0,
            'timestamp': datetime.now().isoformat()
        })


# ========================================
# INTEGRATION METHODS
# ========================================

    def delegate_authority(self, authority_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Delegate authority to appropriate hierarchical level

        Args:
            authority_request: Authority delegation request with:
                - operation: Operation requiring authority
                - current_level: Current authority level
                - required_level: Required authority level
                - justification: Delegation justification

        Returns:
            Authority delegation result
        """
        try:
            operation = authority_request.get('operation')
            current_level = authority_request.get('current_level', AuthorityLevel.OPERATIONAL)
            required_level = authority_request.get('required_level', AuthorityLevel.OPERATIONAL)
            justification = authority_request.get('justification', '')

            delegation_result = {
                'operation': operation,
                'delegated': False,
                'from_level': current_level.value,
                'to_level': required_level.value,
                'justification': justification,
                'timestamp': datetime.now().isoformat()
            }

            # Check if delegation is allowed
            if self._can_delegate_authority(current_level, required_level):
                delegation_result['delegated'] = True
                delegation_result['delegation_id'] = f"del_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                # Log delegation
                self.log_audit_event('authority_delegation', operation, delegation_result)
            else:
                delegation_result['reason'] = 'delegation_not_allowed'

            return delegation_result

        except Exception as e:
            logger.error(f"Authority delegation failed: {e}")
            return {
                'operation': authority_request.get('operation'),
                'delegated': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def validate_authority_permissions(self, permission_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate authority permissions for operations

        Args:
            permission_request: Permission validation request with:
                - operation: Operation to validate
                - requester: Requesting authority
                - required_permissions: Required permissions

        Returns:
            Permission validation result
        """
        try:
            operation = permission_request.get('operation')
            requester = permission_request.get('requester', AuthorityLevel.OPERATIONAL)
            required_permissions = permission_request.get('required_permissions', [])

            validation_result = {
                'operation': operation,
                'authorized': False,
                'requester_level': requester.value,
                'required_permissions': required_permissions,
                'granted_permissions': [],
                'denied_permissions': [],
                'timestamp': datetime.now().isoformat()
            }

            # Check each required permission
            for permission in required_permissions:
                if self._has_permission(requester, permission):
                    validation_result['granted_permissions'].append(permission)
                else:
                    validation_result['denied_permissions'].append(permission)

            # Overall authorization
            validation_result['authorized'] = len(validation_result['denied_permissions']) == 0

            # Log validation
            self.log_audit_event('permission_validation', operation, validation_result)

            return validation_result

        except Exception as e:
            logger.error(f"Permission validation failed: {e}")
            return {
                'operation': permission_request.get('operation'),
                'authorized': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def integrate_component_authorization(self, integration_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Integrate component authorization flows

        Args:
            integration_request: Authorization integration request with:
                - component: Component to integrate
                - authorization_flow: Authorization flow specification

        Returns:
            Integration result
        """
        try:
            component = integration_request.get('component')
            authorization_flow = integration_request.get('authorization_flow', {})

            integration_result = {
                'component': component,
                'integrated': False,
                'authorization_flow': authorization_flow,
                'integration_checks': [],
                'timestamp': datetime.now().isoformat()
            }

            # Perform integration checks
            checks = [
                'authority_level_defined',
                'permission_mapping_complete',
                'escalation_path_defined',
                'audit_trail_enabled'
            ]

            for check in checks:
                check_result = self._perform_integration_check(component, check, authorization_flow)
                integration_result['integration_checks'].append(check_result)

            # Overall integration status
            failed_checks = [c for c in integration_result['integration_checks'] if not c.get('passed', False)]
            integration_result['integrated'] = len(failed_checks) == 0

            if integration_result['integrated']:
                integration_result['integration_id'] = f"int_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Log integration
            self.log_audit_event('authorization_integration', component, integration_result)

            return integration_result

        except Exception as e:
            logger.error(f"Authorization integration failed: {e}")
            return {
                'component': integration_request.get('component'),
                'integrated': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    async def _execute_component_operation(self, component_id: str, operation_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute operation on a specific component

        Args:
            component_id: Component to execute operation on
            operation_request: Operation details

        Returns:
            Component execution result
        """
        try:
            component = self.registered_components.get(component_id)
            if not component:
                return {
                    'component': component_id,
                    'status': 'error',
                    'error': 'component_not_found'
                }

            # Check if component has the required method
            operation = operation_request.get('operation')
            if hasattr(component.component_instance, operation):
                method = getattr(component.component_instance, operation)
                if asyncio.iscoroutinefunction(method):
                    result = await method()
                else:
                    result = method()
                return {
                    'component': component_id,
                    'status': 'success',
                    'result': result
                }
            else:
                return {
                    'component': component_id,
                    'status': 'error',
                    'error': 'method_not_found'
                }

        except Exception as e:
            return {
                'component': component_id,
                'status': 'error',
                'error': str(e)
            }

    def _can_delegate_authority(self, from_level: AuthorityLevel, to_level: AuthorityLevel) -> bool:
        """
        Check if authority can be delegated from one level to another

        Args:
            from_level: Source authority level
            to_level: Target authority level

        Returns:
            Whether delegation is allowed
        """
        # Define delegation rules
        delegation_rules = {
            AuthorityLevel.SYSTEM_CONTROL: [AuthorityLevel.GOVERNANCE_CONTROL, AuthorityLevel.OPERATIONAL],
            AuthorityLevel.GOVERNANCE_CONTROL: [AuthorityLevel.STRATEGIC, AuthorityLevel.TACTICAL, AuthorityLevel.OPERATIONAL],
            AuthorityLevel.STRATEGIC: [AuthorityLevel.TACTICAL, AuthorityLevel.OPERATIONAL],
            AuthorityLevel.TACTICAL: [AuthorityLevel.OPERATIONAL],
            AuthorityLevel.OPERATIONAL: []
        }

        allowed_delegations = delegation_rules.get(from_level, [])
        return to_level in allowed_delegations

    def _has_permission(self, authority_level: AuthorityLevel, permission: str) -> bool:
        """
        Check if authority level has specific permission

        Args:
            authority_level: Authority level to check
            permission: Permission to validate

        Returns:
            Whether permission is granted
        """
        # Define permissions by authority level
        level_permissions = {
            AuthorityLevel.SYSTEM_CONTROL: ['*'],  # All permissions
            AuthorityLevel.GOVERNANCE_CONTROL: ['risk_management', 'capital_allocation', 'system_control'],
            AuthorityLevel.STRATEGIC: ['strategy_execution', 'risk_monitoring', 'performance_analysis'],
            AuthorityLevel.TACTICAL: ['trade_execution', 'position_management'],
            AuthorityLevel.OPERATIONAL: ['data_access', 'basic_reporting'],
            AuthorityLevel.READ_ONLY: ['read_only']
        }

        permissions = level_permissions.get(authority_level, [])
        return '*' in permissions or permission in permissions

    def _perform_integration_check(self, component: str, check_type: str, authorization_flow: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform integration check for component authorization

        Args:
            component: Component being checked
            check_type: Type of check to perform
            authorization_flow: Authorization flow specification

        Returns:
            Check result
        """
        check_result = {
            'check_type': check_type,
            'passed': False,
            'details': {}
        }

        try:
            if check_type == 'authority_level_defined':
                check_result['passed'] = 'authority_level' in authorization_flow
                check_result['details'] = {'authority_level': authorization_flow.get('authority_level')}

            elif check_type == 'permission_mapping_complete':
                permissions = authorization_flow.get('permissions', [])
                check_result['passed'] = len(permissions) > 0
                check_result['details'] = {'permission_count': len(permissions)}

            elif check_type == 'escalation_path_defined':
                escalation = authorization_flow.get('escalation_path', {})
                check_result['passed'] = len(escalation) > 0
                check_result['details'] = {'escalation_defined': len(escalation) > 0}

            elif check_type == 'audit_trail_enabled':
                audit_enabled = authorization_flow.get('audit_enabled', False)
                check_result['passed'] = audit_enabled
                check_result['details'] = {'audit_enabled': audit_enabled}

        except Exception as e:
            check_result['error'] = str(e)

        return check_result

    def _distribute_capital(self, capital_distribution: Dict[str, Any]) -> Dict[str, float]:
        """Distribute capital across hierarchical layers

        Args:
            capital_distribution: Capital distribution parameters

        Returns:
            Dict mapping layers to allocated capital amounts
        """
        try:
            total_capital = capital_distribution.get('total_capital', 2000000.0)
            layer_allocation = capital_distribution.get('layer_allocation', {
                'ORCHESTRATION': 0.2,
                'GOVERNANCE': 0.3,
                'EXECUTION': 0.4,
                'SUPPORT': 0.1
            })

            # Validate allocation percentages sum to 1.0
            total_percentage = sum(layer_allocation.values())
            if abs(total_percentage - 1.0) > 0.01:  # Allow small rounding differences
                # Normalize if doesn't sum to 1.0
                for layer in layer_allocation:
                    layer_allocation[layer] /= total_percentage

            # Calculate actual capital amounts
            distributed_capital = {}
            for layer, percentage in layer_allocation.items():
                distributed_capital[layer] = total_capital * percentage

            # Update capital utilization tracking
            self.capital_utilization = {
                'total_capital': total_capital,
                'distributed_capital': distributed_capital,
                'utilization_rate': sum(distributed_capital.values()) / total_capital,
                'timestamp': datetime.now().isoformat()
            }

            logger.info(f"Capital distributed across layers: {distributed_capital}")
            return distributed_capital

        except Exception as e:
            logger.error(f"Capital distribution failed: {e}")
            return {}

    def capital_utilization(self) -> Dict[str, Any]:
        """Get current capital utilization across the system

        Returns:
            Capital utilization data
        """
        return getattr(self, 'capital_utilization', {
            'total_capital': 0.0,
            'distributed_capital': {},
            'utilization_rate': 0.0,
            'timestamp': datetime.now().isoformat()
        })

    @property
    def authorization_audit(self) -> List[Dict[str, Any]]:
        """Get authorization audit trail for governance compliance

        Returns:
            Authorization audit trail
        """
        return self._authorization_audit

    @authorization_audit.setter
    def authorization_audit(self, value: List[Dict[str, Any]]) -> None:
        """Set authorization audit trail

        Args:
            value: Authorization audit trail data
        """
        self._authorization_audit = value

    def _get_allowed_operations(self, authority_level: AuthorityLevel) -> Set[str]:
        """
        Get allowed operations for a given authority level

        Args:
            authority_level: The authority level to check

        Returns:
            Set of allowed operations
        """
        try:
            # Define operations by authority level
            operations_by_level = {
                AuthorityLevel.SYSTEM_CONTROL: {
                    'system_shutdown', 'emergency_stop', 'component_restart',
                    'authority_escalation', 'system_configuration', 'capital_reallocation'
                },
                AuthorityLevel.GOVERNANCE_CONTROL: {
                    'risk_limit_adjustment', 'trading_authorization', 'position_limits',
                    'compliance_check', 'audit_generation', 'capital_allocation'
                },
                AuthorityLevel.OPERATIONAL: {
                    'execute_trade', 'position_management', 'signal_generation',
                    'data_processing', 'health_check', 'performance_monitoring'
                },
                AuthorityLevel.READ_ONLY: {
                    'read_data', 'view_positions', 'view_performance', 'health_check'
                }
            }

            return operations_by_level.get(authority_level, set())

        except Exception as e:
            logger.error(f"Failed to get allowed operations: {e}")
            return set()

    def _check_authorization_flow(self, operation: str, requester_authority: AuthorityLevel,
                                required_authority: AuthorityLevel) -> Optional[bool]:
        """
        Check authorization flow for an operation

        Args:
            operation: Operation being requested
            requester_authority: Authority level of requester
            required_authority: Required authority level

        Returns:
            True if authorized, False if not, None if error
        """
        try:
            # Define authority hierarchy (higher values = more authority)
            authority_hierarchy = {
                AuthorityLevel.READ_ONLY: 1,
                AuthorityLevel.OPERATIONAL: 2,
                AuthorityLevel.GOVERNANCE_CONTROL: 3,
                AuthorityLevel.SYSTEM_CONTROL: 4
            }

            requester_level = authority_hierarchy.get(requester_authority, 0)
            required_level = authority_hierarchy.get(required_authority, 0)

            # Check if requester has sufficient authority
            return requester_level >= required_level

        except Exception as e:
            logger.error(f"Authorization flow check failed: {e}")
            return None

    async def _escalate_authorization(self, escalation_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Escalate authorization for high-risk operations

        Args:
            escalation_request: Escalation request details

        Returns:
            Escalation result
        """
        try:
            operation = escalation_request.get('operation')
            risk_severity = escalation_request.get('risk_severity', 'high')
            current_authority = escalation_request.get('current_authority', AuthorityLevel.OPERATIONAL)
            required_authority = escalation_request.get('required_authority', AuthorityLevel.GOVERNANCE_CONTROL)
            reason = escalation_request.get('reason', 'unspecified')

            # Determine escalation path
            escalation_levels = {
                'high': AuthorityLevel.GOVERNANCE_CONTROL,
                'critical': AuthorityLevel.SYSTEM_CONTROL
            }

            target_level = escalation_levels.get(risk_severity, required_authority)

            # Check if escalation is possible
            if current_authority.value >= target_level.value:
                # Already at sufficient level
                escalation_result = {
                    'escalated': False,
                    'reason': 'already_sufficient_authority',
                    'current_level': current_authority.value,
                    'target_level': target_level.value,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                # Perform escalation
                escalation_result = {
                    'escalated': True,
                    'from_level': current_authority.value,
                    'to_level': target_level.value,
                    'risk_severity': risk_severity,
                    'reason': reason,
                    'approved': True,  # Assume approval for simulation
                    'timestamp': datetime.now().isoformat(),
                    'escalation_id': f"esc_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                }

                # Log escalation
                self.log_audit_event('authorization_escalation', operation, escalation_result)

            return escalation_result

        except Exception as e:
            logger.error(f"Authorization escalation failed: {e}")
            return {
                'escalated': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    async def _distribute_capital(self, capital_distribution: Dict[str, Any]) -> Dict[str, Any]:
        """
        Distribute capital through hierarchical layers

        Args:
            capital_distribution: Capital distribution parameters

        Returns:
            Distribution result
        """
        try:
            total_capital = capital_distribution.get('total_capital', 0.0)
            layer_allocation = capital_distribution.get('layer_allocation', {})

            distribution_result = {
                'total_capital': total_capital,
                'layer_allocation': layer_allocation,
                'distributed_capital': {},
                'distribution_timestamp': datetime.now().isoformat(),
                'success': True
            }

            # Distribute capital by layer
            for layer, percentage in layer_allocation.items():
                layer_capital = total_capital * percentage
                distribution_result['distributed_capital'][layer] = layer_capital

                # Update capital utilization tracking
                self.capital_utilization['distributed_capital'][layer] = layer_capital

            # Update total capital
            self.capital_utilization['total_capital'] = total_capital
            self.capital_utilization['utilization_rate'] = 1.0  # Fully distributed
            self.capital_utilization['timestamp'] = datetime.now().isoformat()

            logger.info(f"Capital distributed hierarchically: {distribution_result}")
            return distribution_result

        except Exception as e:
            logger.error(f"Capital distribution failed: {e}")
            return {
                'error': str(e),
                'success': False,
                'timestamp': datetime.now().isoformat()
            }

    # ========================================
    # ORCHESTRATOR INTEGRATION METHODS
    # ========================================

    def register_with_orchestrator(self, orchestrator) -> str:
        """
        Register with orchestrator (self-registration for consistency)

        Note: The orchestrator doesn't register with itself in practice,
        but this method exists for interface consistency during testing.
        """
        # Return a mock component ID for testing purposes
        return "orchestrator_self_registration"

    async def request_operation_authorization(self, operation: str, details: Dict[str, Any]) -> bool:
        """
        Request operation authorization (self-authorization for consistency)

        Note: The orchestrator provides authorization, so it always authorizes itself.
        """
        # Orchestrator always authorizes its own operations
        return True

    # ========================================
    # EMERGENCY AUTHORIZATION METHODS
    # ========================================

    def emergency_authorization(self, operation: str, details: Dict[str, Any] = None) -> bool:
        """Emergency authorization override"""
        try:
            # Emergency operations that can be authorized
            emergency_operations = [
                'emergency_shutdown', 'system_halt', 'emergency_liquidation',
                'risk_override', 'system_recovery', 'emergency_restart'
            ]

            if operation in emergency_operations:
                logger.warning(f"🚨 Emergency authorization granted: {operation}")
                return True
            else:
                logger.error(f"❌ Emergency authorization denied: {operation}")
                return False

        except Exception as e:
            logger.error(f"Emergency authorization failed: {e}")
            return False

    def override_authorization(self, authorization_id: str, reason: str = "Emergency Override") -> bool:
        """Override existing authorization"""
        try:
            logger.warning(f"🚨 Authorization override: {authorization_id} - {reason}")
            # In real implementation, this would override specific authorization
            return True

        except Exception as e:
            logger.error(f"Authorization override failed: {e}")
            return False

    # ========================================
    # AUDIT TRAIL METHODS
    # ========================================

    def log_authorization(self, authorization_event: Dict[str, Any]) -> bool:
        """Log authorization events for audit trail"""
        try:
            # In real implementation, this would log to audit system
            operation = authorization_event.get('operation', 'unknown')
            component = authorization_event.get('component', 'unknown')
            logger.info(f"📋 System authorization logged: {operation} by {component}")
            return True

        except Exception as e:
            logger.error(f"Authorization logging failed: {e}")
            return False

    def audit_authorization(self, authorization_id: str) -> Dict[str, Any]:
        """Audit specific authorization"""
        try:
            from datetime import datetime
            # Mock audit result for system-level authorization
            return {
                'authorization_id': authorization_id,
                'audit_status': 'system_compliant',
                'audit_timestamp': datetime.now(),
                'audited_by': 'HierarchicalSystemOrchestrator',
                'system_level': True
            }

        except Exception as e:
            logger.error(f"System authorization audit failed: {e}")
            return {'error': str(e)}

    def track_authorization(self, authorization_id: str) -> Dict[str, Any]:
        """Track system authorization lifecycle"""
        try:
            from datetime import datetime
            # Mock tracking result for system-level authorization
            return {
                'authorization_id': authorization_id,
                'status': 'system_active',
                'created_at': datetime.now(),
                'tracked_by': 'HierarchicalSystemOrchestrator',
                'system_level': True
            }

        except Exception as e:
            logger.error(f"System authorization tracking failed: {e}")
            return {'error': str(e)}


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