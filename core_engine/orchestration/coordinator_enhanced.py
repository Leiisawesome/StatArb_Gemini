"""
Enhanced Core Engine Orchestration Coordinator
Manages component lifecycle, workflow orchestration, scheduling, and system coordination
"""
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
import asyncio
import logging
import threading
from enum import Enum

from .workflow_manager import WorkflowManager, WorkflowStep, TaskPriority
from .scheduler import TaskScheduler, ScheduledTask, ScheduleType
from .state_manager import StateManager, SystemState, ComponentState
from .event_dispatcher import EventDispatcher, EventType, EventPriority
from ..types.strategy import StrategyInterface

class SystemMode(Enum):
    """System operation modes"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    PAPER_TRADING = "paper_trading"
    LIVE_TRADING = "live_trading"

@dataclass
class ComponentInfo:
    """Information about a system component"""
    name: str
    component_type: str
    instance: Any
    dependencies: List[str]
    health_check: Optional[callable] = None
    startup_order: int = 100
    critical: bool = False

class EnhancedOrchestrationCoordinator:
    """
    Enhanced orchestration coordinator with workflow management, scheduling, 
    state management, and event-driven communication
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # Core subsystems
        self.workflow_manager = WorkflowManager(max_workers=config.get('workflow_workers', 4))
        self.scheduler = TaskScheduler(max_workers=config.get('scheduler_workers', 8))
        self.state_manager = StateManager(config.get('state_persistence_path', './state_data'))
        self.event_dispatcher = EventDispatcher(max_workers=config.get('event_workers', 4))
        
        # Component management
        self.components: Dict[str, Any] = {}
        self.component_info: Dict[str, ComponentInfo] = {}
        self.system_mode = SystemMode(config.get('system_mode', 'paper_trading'))
        
        # Orchestration state
        self.is_initialized = False
        self.is_running = False
        self.startup_lock = threading.Lock()
        
        # Register state change callbacks
        self.state_manager.register_state_change_callback(
            'system', self._on_system_state_change
        )
        self.state_manager.register_state_change_callback(
            'component', self._on_component_state_change
        )
        
        # Setup core workflows
        self._setup_core_workflows()
        
        # Setup scheduled tasks
        self._setup_scheduled_tasks()
        
        self.logger.info(f"Orchestration coordinator initialized in {self.system_mode.value} mode")
    
    async def initialize(self) -> bool:
        """Initialize the orchestration system"""
        if self.is_initialized:
            return True
        
        with self.startup_lock:
            try:
                self.logger.info("Initializing orchestration coordinator...")
                
                # Set system state
                self.state_manager.set_system_state(SystemState.INITIALIZING, "coordinator_init")
                
                # Start scheduler
                if not self.scheduler.start_scheduler():
                    raise Exception("Failed to start task scheduler")
                
                # Initialize components in dependency order
                await self._initialize_components()
                
                # Set system ready
                self.state_manager.set_system_state(SystemState.READY, "initialization_complete")
                
                self.is_initialized = True
                self.logger.info("Orchestration coordinator initialized successfully")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to initialize coordinator: {e}")
                self.state_manager.set_system_state(SystemState.ERROR, f"init_error: {e}")
                return False
    
    def register_components(self, components: Dict[str, ComponentInfo]):
        """Register system components"""
        for name, info in components.items():
            self.component_info[name] = info
            
            # Register with state manager
            self.state_manager.register_component(name, ComponentState.OFFLINE)
            
            self.logger.info(f"Registered component {name} (type: {info.component_type})")
    
    async def start_trading_session(self) -> bool:
        """Start a trading session"""
        if not self.is_initialized:
            self.logger.error("System not initialized")
            return False
        
        if self.is_running:
            self.logger.warning("Trading session already running")
            return True
        
        try:
            self.logger.info("Starting trading session...")
            
            # Set system state
            self.state_manager.set_system_state(SystemState.RUNNING, "trading_session_start")
            
            # Start components
            await self._start_components()
            
            # Execute session startup workflow
            await self.workflow_manager.execute_workflow('session_startup')
            
            # Publish session start event
            self.event_dispatcher.publish(
                EventType.SYSTEM_STATE_CHANGE,
                'coordinator',
                {'action': 'session_start', 'mode': self.system_mode.value},
                EventPriority.HIGH
            )
            
            self.is_running = True
            self.logger.info("Trading session started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start trading session: {e}")
            self.state_manager.set_system_state(SystemState.ERROR, f"session_start_error: {e}")
            await self.emergency_shutdown()
            return False
    
    async def stop_trading_session(self) -> bool:
        """Stop the trading session gracefully"""
        if not self.is_running:
            return True
        
        try:
            self.logger.info("Stopping trading session...")
            
            # Set system state
            self.state_manager.set_system_state(SystemState.STOPPING, "trading_session_stop")
            
            # Execute session shutdown workflow
            await self.workflow_manager.execute_workflow('session_shutdown')
            
            # Stop components
            await self._stop_components()
            
            # Publish session stop event
            self.event_dispatcher.publish(
                EventType.SYSTEM_STATE_CHANGE,
                'coordinator',
                {'action': 'session_stop'},
                EventPriority.HIGH
            )
            
            # Set system state
            self.state_manager.set_system_state(SystemState.STOPPED, "session_stopped")
            
            self.is_running = False
            self.logger.info("Trading session stopped successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping trading session: {e}")
            await self.emergency_shutdown()
            return False
    
    async def emergency_shutdown(self):
        """Emergency system shutdown"""
        self.logger.warning("Initiating emergency shutdown...")
        
        try:
            # Set error state
            self.state_manager.set_system_state(SystemState.ERROR, "emergency_shutdown")
            
            # Emergency stop all components
            await self._emergency_stop_components()
            
            # Publish emergency event
            self.event_dispatcher.publish(
                EventType.ERROR_EVENT,
                'coordinator',
                {'action': 'emergency_shutdown', 'timestamp': datetime.now().isoformat()},
                EventPriority.CRITICAL
            )
            
            self.is_running = False
            self.logger.warning("Emergency shutdown completed")
            
        except Exception as e:
            self.logger.critical(f"Error during emergency shutdown: {e}")
    
    async def _initialize_components(self):
        """Initialize components in dependency order"""
        # Sort components by startup order
        sorted_components = sorted(
            self.component_info.items(),
            key=lambda x: x[1].startup_order
        )
        
        for name, info in sorted_components:
            try:
                self.logger.info(f"Initializing component {name}")
                self.state_manager.set_component_state(name, ComponentState.INITIALIZING)
                
                # Initialize component
                if hasattr(info.instance, 'initialize'):
                    await info.instance.initialize()
                
                # Store component reference
                self.components[name] = info.instance
                
                # Set online state
                self.state_manager.set_component_state(name, ComponentState.ONLINE)
                
                self.logger.info(f"Component {name} initialized successfully")
                
            except Exception as e:
                self.logger.error(f"Failed to initialize component {name}: {e}")
                self.state_manager.set_component_state(name, ComponentState.FAILED)
                
                if info.critical:
                    raise Exception(f"Critical component {name} failed to initialize: {e}")
    
    async def _start_components(self):
        """Start all components"""
        for name, component in self.components.items():
            try:
                if hasattr(component, 'start'):
                    await component.start()
                    self.logger.debug(f"Started component {name}")
            except Exception as e:
                self.logger.error(f"Failed to start component {name}: {e}")
                self.state_manager.set_component_state(name, ComponentState.FAILED)
    
    async def _stop_components(self):
        """Stop all components gracefully"""
        # Stop in reverse order
        for name in reversed(list(self.components.keys())):
            try:
                component = self.components[name]
                if hasattr(component, 'stop'):
                    await component.stop()
                    self.logger.debug(f"Stopped component {name}")
                self.state_manager.set_component_state(name, ComponentState.OFFLINE)
            except Exception as e:
                self.logger.error(f"Error stopping component {name}: {e}")
    
    async def _emergency_stop_components(self):
        """Emergency stop all components"""
        for name, component in self.components.items():
            try:
                if hasattr(component, 'emergency_stop'):
                    await component.emergency_stop()
                elif hasattr(component, 'stop'):
                    await component.stop()
                self.state_manager.set_component_state(name, ComponentState.OFFLINE)
            except Exception as e:
                self.logger.error(f"Error during emergency stop of {name}: {e}")
    
    def _setup_core_workflows(self):
        """Setup core system workflows"""
        try:
            # Session startup workflow
            startup_steps = [
                WorkflowStep(
                    name="validate_market_data",
                    function=self._validate_market_data,
                    priority=TaskPriority.CRITICAL
                ),
                WorkflowStep(
                    name="initialize_risk_limits",
                    function=self._initialize_risk_limits,
                    dependencies=["validate_market_data"],
                    priority=TaskPriority.HIGH
                ),
                WorkflowStep(
                    name="start_strategy_engines",
                    function=self._start_strategy_engines,
                    dependencies=["initialize_risk_limits"],
                    priority=TaskPriority.HIGH
                ),
                WorkflowStep(
                    name="enable_order_routing",
                    function=self._enable_order_routing,
                    dependencies=["start_strategy_engines"],
                    priority=TaskPriority.NORMAL
                )
            ]
            
            self.workflow_manager.register_workflow('session_startup', startup_steps)
            
            # Session shutdown workflow
            shutdown_steps = [
                WorkflowStep(
                    name="cancel_open_orders",
                    function=self._cancel_open_orders,
                    priority=TaskPriority.CRITICAL
                ),
                WorkflowStep(
                    name="close_positions",
                    function=self._close_positions,
                    dependencies=["cancel_open_orders"],
                    priority=TaskPriority.HIGH
                ),
                WorkflowStep(
                    name="generate_reports",
                    function=self._generate_reports,
                    dependencies=["close_positions"],
                    priority=TaskPriority.NORMAL
                ),
                WorkflowStep(
                    name="cleanup_resources",
                    function=self._cleanup_resources,
                    dependencies=["generate_reports"],
                    priority=TaskPriority.LOW
                )
            ]
            
            self.workflow_manager.register_workflow('session_shutdown', shutdown_steps)
            
        except Exception as e:
            self.logger.error(f"Error setting up workflows: {e}")
    
    def _setup_scheduled_tasks(self):
        """Setup scheduled system tasks"""
        try:
            # System health check task
            health_check_task = ScheduledTask(
                id="system_health_check",
                name="System Health Check",
                function=self._system_health_check,
                schedule_type=ScheduleType.INTERVAL,
                next_run=datetime.now(),
                schedule_config={'interval': {'seconds': 30}},
                priority=2
            )
            
            # Performance monitoring task
            perf_monitor_task = ScheduledTask(
                id="performance_monitoring",
                name="Performance Monitoring",
                function=self._performance_monitoring,
                schedule_type=ScheduleType.INTERVAL,
                next_run=datetime.now(),
                schedule_config={'interval': {'minutes': 5}},
                priority=3
            )
            
            # Risk monitoring task
            risk_monitor_task = ScheduledTask(
                id="risk_monitoring",
                name="Risk Monitoring",
                function=self._risk_monitoring,
                schedule_type=ScheduleType.INTERVAL,
                next_run=datetime.now(),
                schedule_config={'interval': {'seconds': 10}},
                priority=1
            )
            
            # State snapshot task
            snapshot_task = ScheduledTask(
                id="state_snapshot",
                name="State Snapshot",
                function=self._create_state_snapshot,
                schedule_type=ScheduleType.INTERVAL,
                next_run=datetime.now(),
                schedule_config={'interval': {'minutes': 1}},
                priority=4
            )
            
            # Schedule all tasks
            for task in [health_check_task, perf_monitor_task, risk_monitor_task, snapshot_task]:
                self.scheduler.schedule_task(task)
                
        except Exception as e:
            self.logger.error(f"Error setting up scheduled tasks: {e}")
    
    def _on_system_state_change(self, old_state: SystemState, new_state: SystemState):
        """Handle system state changes"""
        self.logger.info(f"System state changed: {old_state.value} -> {new_state.value}")
        
        # Publish state change event
        self.event_dispatcher.publish(
            EventType.SYSTEM_STATE_CHANGE,
            'state_manager',
            {
                'old_state': old_state.value,
                'new_state': new_state.value,
                'timestamp': datetime.now().isoformat()
            },
            EventPriority.HIGH
        )
    
    def _on_component_state_change(self, component: str, old_state: ComponentState, new_state: ComponentState):
        """Handle component state changes"""
        self.logger.info(f"Component {component} state changed: {old_state.value} -> {new_state.value}")
        
        # Publish state change event
        self.event_dispatcher.publish(
            EventType.COMPONENT_STATE_CHANGE,
            'state_manager',
            {
                'component': component,
                'old_state': old_state.value,
                'new_state': new_state.value,
                'timestamp': datetime.now().isoformat()
            },
            EventPriority.NORMAL
        )
    
    # Workflow step functions
    async def _validate_market_data(self, context: Dict[str, Any]) -> bool:
        """Validate market data connectivity"""
        self.logger.info("Validating market data...")
        # Implementation would check data feeds
        return True
    
    async def _initialize_risk_limits(self, context: Dict[str, Any]) -> bool:
        """Initialize risk limits"""
        self.logger.info("Initializing risk limits...")
        # Implementation would set up risk parameters
        return True
    
    async def _start_strategy_engines(self, context: Dict[str, Any]) -> bool:
        """Start strategy engines"""
        self.logger.info("Starting strategy engines...")
        # Implementation would start trading strategies
        return True
    
    async def _enable_order_routing(self, context: Dict[str, Any]) -> bool:
        """Enable order routing"""
        self.logger.info("Enabling order routing...")
        # Implementation would enable order submission
        return True
    
    async def _cancel_open_orders(self, context: Dict[str, Any]) -> bool:
        """Cancel open orders"""
        self.logger.info("Cancelling open orders...")
        # Implementation would cancel all open orders
        return True
    
    async def _close_positions(self, context: Dict[str, Any]) -> bool:
        """Close open positions"""
        self.logger.info("Closing positions...")
        # Implementation would close positions if required
        return True
    
    async def _generate_reports(self, context: Dict[str, Any]) -> bool:
        """Generate session reports"""
        self.logger.info("Generating reports...")
        # Implementation would generate end-of-session reports
        return True
    
    async def _cleanup_resources(self, context: Dict[str, Any]) -> bool:
        """Cleanup system resources"""
        self.logger.info("Cleaning up resources...")
        # Implementation would cleanup temporary resources
        return True
    
    # Scheduled task functions
    def _system_health_check(self) -> Dict[str, Any]:
        """Perform system health check"""
        try:
            health_status = {
                'timestamp': datetime.now().isoformat(),
                'system_healthy': True,
                'component_health': {}
            }
            
            # Check each component
            for name, info in self.component_info.items():
                if info.health_check:
                    try:
                        is_healthy = info.health_check()
                        health_status['component_health'][name] = is_healthy
                        if not is_healthy and info.critical:
                            health_status['system_healthy'] = False
                    except Exception as e:
                        self.logger.error(f"Health check failed for {name}: {e}")
                        health_status['component_health'][name] = False
                        if info.critical:
                            health_status['system_healthy'] = False
            
            # Update system metrics
            self.state_manager.update_system_metrics({
                'last_health_check': datetime.now(),
                'system_healthy': health_status['system_healthy']
            })
            
            return health_status
            
        except Exception as e:
            self.logger.error(f"Error in system health check: {e}")
            return {'error': str(e)}
    
    def _performance_monitoring(self) -> Dict[str, Any]:
        """Monitor system performance"""
        try:
            metrics = {
                'timestamp': datetime.now().isoformat(),
                'workflow_metrics': self.workflow_manager.execution_metrics,
                'scheduler_metrics': self.scheduler.get_scheduler_metrics(),
                'event_metrics': self.event_dispatcher.get_status()['metrics']
            }
            
            # Update system metrics
            self.state_manager.update_system_metrics({
                'last_performance_check': datetime.now(),
                'performance_metrics': metrics
            })
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error in performance monitoring: {e}")
            return {'error': str(e)}
    
    def _risk_monitoring(self) -> Dict[str, Any]:
        """Monitor system risk"""
        try:
            # Implementation would check risk limits, exposures, etc.
            risk_status = {
                'timestamp': datetime.now().isoformat(),
                'risk_within_limits': True,
                'alerts': []
            }
            
            return risk_status
            
        except Exception as e:
            self.logger.error(f"Error in risk monitoring: {e}")
            return {'error': str(e)}
    
    def _create_state_snapshot(self) -> Dict[str, Any]:
        """Create system state snapshot"""
        try:
            snapshot = self.state_manager.create_snapshot()
            return {'snapshot_id': snapshot.snapshot_id, 'timestamp': snapshot.timestamp}
        except Exception as e:
            self.logger.error(f"Error creating state snapshot: {e}")
            return {'error': str(e)}
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            'system_mode': self.system_mode.value,
            'is_initialized': self.is_initialized,
            'is_running': self.is_running,
            'system_state': self.state_manager.get_current_state(),
            'workflow_status': {
                name: self.workflow_manager.get_workflow_status(name)
                for name in ['session_startup', 'session_shutdown']
            },
            'scheduler_status': self.scheduler.get_scheduler_metrics(),
            'event_dispatcher_status': self.event_dispatcher.get_status(),
            'component_count': len(self.components),
            'timestamp': datetime.now().isoformat()
        }
    
    def is_system_healthy(self) -> bool:
        """Check if system is healthy"""
        try:
            current_state = self.state_manager.get_current_state()
            return (
                self.is_initialized and
                current_state['system_state'] in ['ready', 'running'] and
                current_state.get('system_metrics', {}).get('system_healthy', False)
            )
        except:
            return False
    
    def cleanup(self):
        """Cleanup coordinator resources"""
        try:
            self.workflow_manager.cleanup()
            self.scheduler.cleanup()
            self.state_manager.cleanup()
            self.event_dispatcher.cleanup()
            self.logger.info("Orchestration coordinator cleaned up")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")