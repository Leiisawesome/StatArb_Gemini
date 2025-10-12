"""
Strategy Engine - Strategy Manager
Advanced strategy lifecycle management and orchestration system
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Type
from dataclasses import dataclass, field
from enum import Enum
import threading
import warnings
import time
from collections import defaultdict

# Import strategy components
from .strategy_engine import (
    BaseStrategy, StrategyExecutionEngine, StrategyConfig, StrategySignal,
    StrategyPosition, StrategyMetrics, StrategyState, StrategyType
)

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class StrategyStatus(Enum):
    """Extended strategy status"""
    CREATED = "created"
    CONFIGURED = "configured"
    VALIDATED = "validated"
    DEPLOYED = "deployed"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"
    RETIRED = "retired"


class DeploymentMode(Enum):
    """Strategy deployment modes"""
    PAPER_TRADING = "paper_trading"
    LIVE_TRADING = "live_trading"
    SIMULATION = "simulation"
    BACKTESTING = "backtesting"
    RESEARCH = "research"


class ResourceType(Enum):
    """Strategy resource types"""
    CPU = "cpu"
    MEMORY = "memory"
    NETWORK = "network"
    STORAGE = "storage"
    DATA_FEEDS = "data_feeds"
    COMPUTE = "compute"


@dataclass
class StrategyDependency:
    """Strategy dependency specification"""
    
    dependency_id: str = ""
    dependency_type: str = ""  # service, data, strategy, etc.
    required: bool = True
    version: Optional[str] = None
    configuration: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategyResource:
    """Strategy resource requirements"""
    
    resource_type: ResourceType = ResourceType.CPU
    amount: float = 0.0
    unit: str = ""
    priority: int = 1  # 1=low, 5=high
    shared: bool = True


@dataclass
class StrategyDeployment:
    """Strategy deployment configuration"""
    
    deployment_id: str = ""
    strategy_id: str = ""
    deployment_mode: DeploymentMode = DeploymentMode.PAPER_TRADING
    
    # Environment settings
    environment: str = "development"  # development, staging, production
    instance_count: int = 1
    auto_scale: bool = False
    
    # Resource allocation
    resources: List[StrategyResource] = field(default_factory=list)
    max_cpu_usage: float = 50.0  # Percentage
    max_memory_usage: float = 512.0  # MB
    
    # Network settings
    network_access: bool = True
    api_endpoints: List[str] = field(default_factory=list)
    
    # Data access
    data_sources: List[str] = field(default_factory=list)
    data_permissions: Dict[str, str] = field(default_factory=dict)
    
    # Monitoring
    enable_monitoring: bool = True
    monitoring_interval: int = 60  # seconds
    alert_thresholds: Dict[str, float] = field(default_factory=dict)
    
    # Deployment metadata
    deployed_at: Optional[datetime] = None
    deployed_by: str = ""
    deployment_version: str = "1.0.0"


@dataclass
class StrategyHealthCheck:
    """Strategy health check configuration"""
    
    # Health check settings
    enable_health_checks: bool = True
    check_interval: int = 30  # seconds
    timeout: float = 10.0  # seconds
    
    # Health check types
    check_connectivity: bool = True
    check_data_feeds: bool = True
    check_performance: bool = True
    check_positions: bool = True
    check_risk_limits: bool = True
    
    # Thresholds
    max_response_time: float = 5.0  # seconds
    min_signal_rate: float = 0.1   # signals per minute
    max_error_rate: float = 0.05   # 5% error rate
    max_drawdown_threshold: float = 0.1  # 10%
    
    # Actions
    auto_restart_on_failure: bool = False
    escalate_critical_issues: bool = True
    notify_on_issues: bool = True


@dataclass
class StrategyTemplate:
    """Strategy template for easy strategy creation"""
    
    template_id: str = ""
    template_name: str = ""
    template_type: StrategyType = StrategyType.CUSTOM
    description: str = ""
    
    # Template configuration
    default_config: StrategyConfig = field(default_factory=StrategyConfig)
    parameter_schema: Dict[str, Any] = field(default_factory=dict)
    required_parameters: List[str] = field(default_factory=list)
    
    # Code template
    strategy_class: Optional[Type[BaseStrategy]] = None
    code_template: str = ""
    
    # Dependencies and resources
    dependencies: List[StrategyDependency] = field(default_factory=list)
    resources: List[StrategyResource] = field(default_factory=list)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""
    version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)


class StrategyRegistry:
    """Registry for strategy templates and instances"""
    
    def __init__(self):
        self._templates: Dict[str, StrategyTemplate] = {}
        self._strategies: Dict[str, BaseStrategy] = {}
        self._deployments: Dict[str, StrategyDeployment] = {}
        
        # Strategy metadata
        self._strategy_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Thread safety
        self._lock = threading.RLock()
        
        logger.info("Strategy registry initialized")
    
    def register_template(self, template: StrategyTemplate) -> bool:
        """Register a strategy template"""
        
        try:
            with self._lock:
                if template.template_id in self._templates:
                    logger.warning(f"Template {template.template_id} already exists")
                    return False
                
                self._templates[template.template_id] = template
                
                logger.info(f"Strategy template registered: {template.template_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error registering template: {e}")
            return False
    
    def get_template(self, template_id: str) -> Optional[StrategyTemplate]:
        """Get strategy template"""
        
        with self._lock:
            return self._templates.get(template_id)
    
    def list_templates(self) -> List[StrategyTemplate]:
        """List all strategy templates"""
        
        with self._lock:
            return list(self._templates.values())
    
    def register_strategy(self, strategy: BaseStrategy, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Register a strategy instance"""
        
        try:
            with self._lock:
                if strategy.strategy_id in self._strategies:
                    logger.warning(f"Strategy {strategy.strategy_id} already exists")
                    return False
                
                self._strategies[strategy.strategy_id] = strategy
                
                if metadata:
                    self._strategy_metadata[strategy.strategy_id] = metadata
                
                logger.info(f"Strategy registered: {strategy.strategy_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error registering strategy: {e}")
            return False
    
    def get_strategy(self, strategy_id: str) -> Optional[BaseStrategy]:
        """Get strategy instance"""
        
        with self._lock:
            return self._strategies.get(strategy_id)
    
    def list_strategies(self) -> List[BaseStrategy]:
        """List all strategy instances"""
        
        with self._lock:
            return list(self._strategies.values())
    
    def register_deployment(self, deployment: StrategyDeployment) -> bool:
        """Register strategy deployment"""
        
        try:
            with self._lock:
                self._deployments[deployment.deployment_id] = deployment
                
                logger.info(f"Deployment registered: {deployment.deployment_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error registering deployment: {e}")
            return False


class StrategyLifecycleManager:
    """Manages strategy lifecycle from creation to retirement"""
    
    def __init__(self, registry: StrategyRegistry):
        self.registry = registry
        
        # Lifecycle tracking
        self._strategy_lifecycle: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        # Health monitoring
        self._health_checks: Dict[str, StrategyHealthCheck] = {}
        self._health_status: Dict[str, Dict[str, Any]] = {}
        
        # Performance tracking
        self._performance_history: Dict[str, List[StrategyMetrics]] = defaultdict(list)
        
        # Thread safety
        self._lock = threading.RLock()
        
        logger.info("Strategy lifecycle manager initialized")
    
    def create_strategy_from_template(self, template_id: str, strategy_id: str,
                                    parameters: Dict[str, Any]) -> Optional[BaseStrategy]:
        """Create strategy instance from template"""
        
        try:
            template = self.registry.get_template(template_id)
            if not template:
                logger.error(f"Template {template_id} not found")
                return None
            
            # Validate parameters
            if not self._validate_parameters(template, parameters):
                logger.error(f"Invalid parameters for template {template_id}")
                return None
            
            # Create strategy configuration
            config = self._create_strategy_config(template, strategy_id, parameters)
            
            # Instantiate strategy
            if template.strategy_class:
                strategy = template.strategy_class(config)
            else:
                logger.error(f"No strategy class defined for template {template_id}")
                return None
            
            # Register strategy
            metadata = {
                'template_id': template_id,
                'created_at': datetime.now(),
                'parameters': parameters,
                'status': StrategyStatus.CREATED.value
            }
            
            if self.registry.register_strategy(strategy, metadata):
                self._log_lifecycle_event(strategy_id, StrategyStatus.CREATED, "Strategy created from template")
                return strategy
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating strategy from template: {e}")
            return None
    
    def configure_strategy(self, strategy_id: str, config_updates: Dict[str, Any]) -> bool:
        """Configure strategy parameters"""
        
        try:
            strategy = self.registry.get_strategy(strategy_id)
            if not strategy:
                logger.error(f"Strategy {strategy_id} not found")
                return False
            
            # Update configuration
            for key, value in config_updates.items():
                if hasattr(strategy.config, key):
                    setattr(strategy.config, key, value)
                else:
                    logger.warning(f"Unknown configuration parameter: {key}")
            
            self._log_lifecycle_event(strategy_id, StrategyStatus.CONFIGURED, "Strategy configuration updated")
            return True
            
        except Exception as e:
            logger.error(f"Error configuring strategy {strategy_id}: {e}")
            return False
    
    def validate_strategy(self, strategy_id: str) -> bool:
        """Validate strategy before deployment"""
        
        try:
            strategy = self.registry.get_strategy(strategy_id)
            if not strategy:
                logger.error(f"Strategy {strategy_id} not found")
                return False
            
            validation_results = {
                'configuration_valid': self._validate_configuration(strategy),
                'dependencies_available': self._check_dependencies(strategy),
                'resources_available': self._check_resources(strategy),
                'code_valid': self._validate_code(strategy)
            }
            
            all_valid = all(validation_results.values())
            
            if all_valid:
                self._log_lifecycle_event(strategy_id, StrategyStatus.VALIDATED, "Strategy validation passed")
            else:
                failed_checks = [k for k, v in validation_results.items() if not v]
                self._log_lifecycle_event(
                    strategy_id, StrategyStatus.ERROR, 
                    f"Strategy validation failed: {', '.join(failed_checks)}"
                )
            
            return all_valid
            
        except Exception as e:
            logger.error(f"Error validating strategy {strategy_id}: {e}")
            return False
    
    def deploy_strategy(self, strategy_id: str, deployment_config: StrategyDeployment) -> bool:
        """Deploy strategy to execution environment"""
        
        try:
            strategy = self.registry.get_strategy(strategy_id)
            if not strategy:
                logger.error(f"Strategy {strategy_id} not found")
                return False
            
            # Validate strategy before deployment
            if not self.validate_strategy(strategy_id):
                logger.error(f"Strategy {strategy_id} failed validation")
                return False
            
            # Register deployment
            deployment_config.strategy_id = strategy_id
            deployment_config.deployed_at = datetime.now()
            
            if not self.registry.register_deployment(deployment_config):
                logger.error(f"Failed to register deployment for {strategy_id}")
                return False
            
            # Setup health monitoring
            health_check = StrategyHealthCheck()
            self._health_checks[strategy_id] = health_check
            
            self._log_lifecycle_event(strategy_id, StrategyStatus.DEPLOYED, "Strategy deployed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error deploying strategy {strategy_id}: {e}")
            return False
    
    def start_strategy(self, strategy_id: str) -> bool:
        """Start strategy execution"""
        
        try:
            strategy = self.registry.get_strategy(strategy_id)
            if not strategy:
                logger.error(f"Strategy {strategy_id} not found")
                return False
            
            if strategy.start():
                self._log_lifecycle_event(strategy_id, StrategyStatus.RUNNING, "Strategy started")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error starting strategy {strategy_id}: {e}")
            return False
    
    def stop_strategy(self, strategy_id: str) -> bool:
        """Stop strategy execution"""
        
        try:
            strategy = self.registry.get_strategy(strategy_id)
            if not strategy:
                logger.error(f"Strategy {strategy_id} not found")
                return False
            
            if strategy.stop():
                self._log_lifecycle_event(strategy_id, StrategyStatus.STOPPED, "Strategy stopped")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error stopping strategy {strategy_id}: {e}")
            return False
    
    def pause_strategy(self, strategy_id: str) -> bool:
        """Pause strategy execution"""
        
        try:
            strategy = self.registry.get_strategy(strategy_id)
            if not strategy:
                logger.error(f"Strategy {strategy_id} not found")
                return False
            
            if strategy.pause():
                self._log_lifecycle_event(strategy_id, StrategyStatus.PAUSED, "Strategy paused")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error pausing strategy {strategy_id}: {e}")
            return False
    
    def resume_strategy(self, strategy_id: str) -> bool:
        """Resume strategy execution"""
        
        try:
            strategy = self.registry.get_strategy(strategy_id)
            if not strategy:
                logger.error(f"Strategy {strategy_id} not found")
                return False
            
            if strategy.resume():
                self._log_lifecycle_event(strategy_id, StrategyStatus.RUNNING, "Strategy resumed")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error resuming strategy {strategy_id}: {e}")
            return False
    
    def retire_strategy(self, strategy_id: str, reason: str = "") -> bool:
        """Retire strategy and clean up resources"""
        
        try:
            strategy = self.registry.get_strategy(strategy_id)
            if not strategy:
                logger.error(f"Strategy {strategy_id} not found")
                return False
            
            # Stop strategy if running
            if strategy.get_state() in [StrategyState.ACTIVE, StrategyState.PAUSED]:
                self.stop_strategy(strategy_id)
            
            # Clean up resources
            self._cleanup_strategy_resources(strategy_id)
            
            self._log_lifecycle_event(strategy_id, StrategyStatus.RETIRED, f"Strategy retired: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Error retiring strategy {strategy_id}: {e}")
            return False
    
    def perform_health_check(self, strategy_id: str) -> Dict[str, Any]:
        """Perform health check on strategy"""
        
        try:
            strategy = self.registry.get_strategy(strategy_id)
            if not strategy:
                return {'status': 'error', 'message': 'Strategy not found'}
            
            health_config = self._health_checks.get(strategy_id, StrategyHealthCheck())
            
            health_results = {
                'strategy_id': strategy_id,
                'timestamp': datetime.now(),
                'overall_status': 'healthy',
                'checks': {}
            }
            
            # Check strategy state
            strategy_state = strategy.get_state()
            health_results['checks']['state'] = {
                'status': 'healthy' if strategy_state == StrategyState.ACTIVE else 'warning',
                'value': strategy_state.value
            }
            
            # Check performance metrics
            metrics = strategy.get_metrics()
            health_results['checks']['performance'] = self._check_performance_health(metrics, health_config)
            
            # Check positions
            positions = strategy.get_positions()
            health_results['checks']['positions'] = self._check_positions_health(positions, health_config)
            
            # Check signals
            recent_signals = strategy.get_signals(limit=100)
            health_results['checks']['signals'] = self._check_signals_health(recent_signals, health_config)
            
            # Determine overall status
            check_statuses = [check['status'] for check in health_results['checks'].values()]
            if 'critical' in check_statuses:
                health_results['overall_status'] = 'critical'
            elif 'error' in check_statuses:
                health_results['overall_status'] = 'error'
            elif 'warning' in check_statuses:
                health_results['overall_status'] = 'warning'
            
            # Store health status
            self._health_status[strategy_id] = health_results
            
            return health_results
            
        except Exception as e:
            logger.error(f"Error performing health check for {strategy_id}: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def get_strategy_lifecycle(self, strategy_id: str) -> List[Dict[str, Any]]:
        """Get strategy lifecycle history"""
        
        with self._lock:
            return self._strategy_lifecycle.get(strategy_id, []).copy()
    
    def get_strategy_health(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Get latest health check results"""
        
        with self._lock:
            return self._health_status.get(strategy_id)
    
    def get_performance_history(self, strategy_id: str) -> List[StrategyMetrics]:
        """Get strategy performance history"""
        
        with self._lock:
            return self._performance_history.get(strategy_id, []).copy()
    
    def _validate_parameters(self, template: StrategyTemplate, parameters: Dict[str, Any]) -> bool:
        """Validate strategy parameters against template"""
        
        try:
            # Check required parameters
            for required_param in template.required_parameters:
                if required_param not in parameters:
                    logger.error(f"Required parameter missing: {required_param}")
                    return False
            
            # Validate against schema if available
            if template.parameter_schema:
                # Simple validation - can be extended with jsonschema
                for param, value in parameters.items():
                    if param in template.parameter_schema:
                        expected_type = template.parameter_schema[param].get('type')
                        if expected_type and not isinstance(value, expected_type):
                            logger.error(f"Parameter {param} has wrong type")
                            return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating parameters: {e}")
            return False
    
    def _create_strategy_config(self, template: StrategyTemplate, 
                              strategy_id: str, parameters: Dict[str, Any]) -> StrategyConfig:
        """Create strategy configuration from template and parameters"""
        
        # Start with template default config
        config = template.default_config
        
        # Update with strategy-specific settings
        config.strategy_id = strategy_id
        config.strategy_name = f"{template.template_name}_{strategy_id}"
        config.strategy_type = template.template_type
        
        # Apply parameters
        for param, value in parameters.items():
            if hasattr(config, param):
                setattr(config, param, value)
            else:
                # Add to strategy_parameters
                config.strategy_parameters[param] = value
        
        return config
    
    def _validate_configuration(self, strategy: BaseStrategy) -> bool:
        """Validate strategy configuration"""
        
        try:
            config = strategy.config
            
            # Basic validation
            if not config.strategy_id:
                return False
            
            if config.max_positions <= 0:
                return False
            
            if config.max_position_size <= 0 or config.max_position_size > 1:
                return False
            
            if config.risk_per_trade <= 0 or config.risk_per_trade > 1:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating configuration: {e}")
            return False
    
    def _check_dependencies(self, strategy: BaseStrategy) -> bool:
        """Check if strategy dependencies are available"""
        
        try:
            # Check data feeds
            for symbol in strategy.config.required_symbols:
                # Validate symbol format, availability, etc.
                if not symbol or len(symbol) < 1:
                    return False
            
            # Check data feeds
            for feed in strategy.config.required_data_feeds:
                # Validate data feed availability
                if not feed:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking dependencies: {e}")
            return False
    
    def _check_resources(self, strategy: BaseStrategy) -> bool:
        """Check if required resources are available"""
        
        try:
            # Basic resource checks
            # In a real implementation, this would check actual system resources
            return True
            
        except Exception as e:
            logger.error(f"Error checking resources: {e}")
            return False
    
    def _validate_code(self, strategy: BaseStrategy) -> bool:
        """Validate strategy code"""
        
        try:
            # Check if strategy implements required methods
            required_methods = ['initialize', 'generate_signals', 'update_positions']
            
            for method in required_methods:
                if not hasattr(strategy, method):
                    logger.error(f"Strategy missing required method: {method}")
                    return False
                
                if not callable(getattr(strategy, method)):
                    logger.error(f"Strategy method not callable: {method}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating code: {e}")
            return False
    
    def _check_performance_health(self, metrics: StrategyMetrics, 
                                health_config: StrategyHealthCheck) -> Dict[str, Any]:
        """Check performance health"""
        
        try:
            status = 'healthy'
            issues = []
            
            # Check error rate
            if metrics.total_signals > 0:
                error_rate = metrics.error_count / metrics.total_signals
                if error_rate > health_config.max_error_rate:
                    status = 'error'
                    issues.append(f"High error rate: {error_rate:.2%}")
            
            # Check drawdown
            if abs(metrics.max_drawdown) > health_config.max_drawdown_threshold:
                status = 'warning'
                issues.append(f"High drawdown: {metrics.max_drawdown:.2%}")
            
            return {
                'status': status,
                'issues': issues,
                'metrics': {
                    'total_return': metrics.total_return,
                    'max_drawdown': metrics.max_drawdown,
                    'sharpe_ratio': metrics.sharpe_ratio,
                    'error_count': metrics.error_count
                }
            }
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def _check_positions_health(self, positions: Dict[str, StrategyPosition],
                              health_config: StrategyHealthCheck) -> Dict[str, Any]:
        """Check positions health"""
        
        try:
            status = 'healthy'
            issues = []
            
            # Check for stale positions
            current_time = datetime.now()
            for position in positions.values():
                time_since_update = (current_time - position.last_update).total_seconds()
                if time_since_update > 3600:  # 1 hour
                    status = 'warning'
                    issues.append(f"Stale position: {position.symbol}")
            
            return {
                'status': status,
                'issues': issues,
                'metrics': {
                    'total_positions': len(positions),
                    'total_pnl': sum(pos.total_pnl for pos in positions.values()),
                    'unrealized_pnl': sum(pos.unrealized_pnl for pos in positions.values())
                }
            }
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def _check_signals_health(self, signals: List[StrategySignal],
                            health_config: StrategyHealthCheck) -> Dict[str, Any]:
        """Check signals health"""
        
        try:
            status = 'healthy'
            issues = []
            
            if not signals:
                status = 'warning'
                issues.append("No recent signals")
                return {'status': status, 'issues': issues}
            
            # Check signal rate
            recent_signals = [s for s in signals if (datetime.now() - s.timestamp).total_seconds() < 3600]
            signal_rate = len(recent_signals) / 60  # per minute
            
            if signal_rate < health_config.min_signal_rate:
                status = 'warning'
                issues.append(f"Low signal rate: {signal_rate:.2f}/min")
            
            return {
                'status': status,
                'issues': issues,
                'metrics': {
                    'total_signals': len(signals),
                    'recent_signals': len(recent_signals),
                    'signal_rate': signal_rate
                }
            }
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def _cleanup_strategy_resources(self, strategy_id: str) -> None:
        """Clean up strategy resources"""
        
        try:
            # Remove from health monitoring
            self._health_checks.pop(strategy_id, None)
            self._health_status.pop(strategy_id, None)
            
            # Archive performance history
            # Keep history but mark as retired
            
            logger.info(f"Cleaned up resources for strategy {strategy_id}")
            
        except Exception as e:
            logger.error(f"Error cleaning up resources for {strategy_id}: {e}")
    
    def _log_lifecycle_event(self, strategy_id: str, status: StrategyStatus, message: str) -> None:
        """Log strategy lifecycle event"""
        
        try:
            with self._lock:
                event = {
                    'timestamp': datetime.now(),
                    'status': status.value,
                    'message': message
                }
                
                self._strategy_lifecycle[strategy_id].append(event)
                
                logger.info(f"Strategy {strategy_id} lifecycle event: {status.value} - {message}")
                
        except Exception as e:
            logger.error(f"Error logging lifecycle event: {e}")


class StrategyManager:
    """
    Comprehensive Strategy Management System
    
    Orchestrates strategy lifecycle, deployment, monitoring, and management
    across the entire trading system.
    """
    
    def __init__(self, execution_engine: Optional[StrategyExecutionEngine] = None):
        """Initialize strategy manager"""
        
        # Core components
        self.execution_engine = execution_engine or StrategyExecutionEngine()
        self.registry = StrategyRegistry()
        self.lifecycle_manager = StrategyLifecycleManager(self.registry)
        
        # Manager state
        self._active_deployments: Dict[str, StrategyDeployment] = {}
        self._monitoring_active = False
        self._monitoring_thread: Optional[threading.Thread] = None
        
        # Performance tracking
        self._manager_metrics = {
            'strategies_created': 0,
            'strategies_deployed': 0,
            'strategies_retired': 0,
            'total_signals_processed': 0,
            'health_checks_performed': 0,
            'average_health_score': 0.0
        }
        
        # Thread safety
        self._lock = threading.RLock()
        
        logger.info("Strategy manager initialized")
    
    def create_strategy_template(self, template: StrategyTemplate) -> bool:
        """Create and register strategy template"""
        
        try:
            result = self.registry.register_template(template)
            
            if result:
                logger.info(f"Strategy template created: {template.template_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error creating strategy template: {e}")
            return False
    
    def create_strategy(self, template_id: str, strategy_id: str,
                       parameters: Dict[str, Any]) -> Optional[BaseStrategy]:
        """Create strategy from template"""
        
        try:
            strategy = self.lifecycle_manager.create_strategy_from_template(
                template_id, strategy_id, parameters
            )
            
            if strategy:
                self._manager_metrics['strategies_created'] += 1
                logger.info(f"Strategy created: {strategy_id}")
            
            return strategy
            
        except Exception as e:
            logger.error(f"Error creating strategy: {e}")
            return None
    
    def deploy_strategy(self, strategy_id: str, deployment_config: StrategyDeployment) -> bool:
        """Deploy strategy to execution environment"""
        
        try:
            # Deploy through lifecycle manager
            result = self.lifecycle_manager.deploy_strategy(strategy_id, deployment_config)
            
            if result:
                # Register with execution engine
                strategy = self.registry.get_strategy(strategy_id)
                if strategy:
                    self.execution_engine.register_strategy(strategy)
                    self._active_deployments[strategy_id] = deployment_config
                    self._manager_metrics['strategies_deployed'] += 1
                    
                    logger.info(f"Strategy deployed: {strategy_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error deploying strategy {strategy_id}: {e}")
            return False
    
    def start_strategy(self, strategy_id: str) -> bool:
        """Start strategy execution"""
        
        try:
            # Start through lifecycle manager
            result = self.lifecycle_manager.start_strategy(strategy_id)
            
            if result:
                # Start in execution engine
                self.execution_engine.start_strategy(strategy_id)
                logger.info(f"Strategy started: {strategy_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error starting strategy {strategy_id}: {e}")
            return False
    
    def stop_strategy(self, strategy_id: str) -> bool:
        """Stop strategy execution"""
        
        try:
            # Stop in execution engine
            self.execution_engine.stop_strategy(strategy_id)
            
            # Stop through lifecycle manager
            result = self.lifecycle_manager.stop_strategy(strategy_id)
            
            if result:
                logger.info(f"Strategy stopped: {strategy_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error stopping strategy {strategy_id}: {e}")
            return False
    
    def start_monitoring(self) -> bool:
        """Start strategy monitoring"""
        
        try:
            if self._monitoring_active:
                logger.warning("Strategy monitoring already active")
                return False
            
            self._monitoring_active = True
            
            # Start monitoring thread
            self._monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True
            )
            self._monitoring_thread.start()
            
            logger.info("Strategy monitoring started")
            return True
            
        except Exception as e:
            logger.error(f"Error starting monitoring: {e}")
            return False
    
    def stop_monitoring(self) -> bool:
        """Stop strategy monitoring"""
        
        try:
            self._monitoring_active = False
            
            if self._monitoring_thread and self._monitoring_thread.is_alive():
                self._monitoring_thread.join(timeout=5.0)
            
            logger.info("Strategy monitoring stopped")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping monitoring: {e}")
            return False
    
    def _monitoring_loop(self) -> None:
        """Strategy monitoring loop"""
        
        logger.info("Strategy monitoring loop started")
        
        while self._monitoring_active:
            try:
                # Perform health checks on all deployed strategies
                for strategy_id in self._active_deployments.keys():
                    health_result = self.lifecycle_manager.perform_health_check(strategy_id)
                    self._manager_metrics['health_checks_performed'] += 1
                    
                    # Handle critical issues
                    if health_result.get('overall_status') == 'critical':
                        logger.error(f"Critical health issue for strategy {strategy_id}")
                        # Could trigger automatic actions here
                
                # Update manager metrics
                self._update_manager_metrics()
                
                # Sleep between monitoring cycles
                time.sleep(60)  # 1 minute monitoring cycle
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)
        
        logger.info("Strategy monitoring loop stopped")
    
    def _update_manager_metrics(self) -> None:
        """Update manager performance metrics"""
        
        try:
            # Calculate average health score
            health_scores = []
            for strategy_id in self._active_deployments.keys():
                health = self.lifecycle_manager.get_strategy_health(strategy_id)
                if health:
                    status = health.get('overall_status', 'unknown')
                    score = {'healthy': 100, 'warning': 70, 'error': 30, 'critical': 0}.get(status, 50)
                    health_scores.append(score)
            
            if health_scores:
                self._manager_metrics['average_health_score'] = sum(health_scores) / len(health_scores)
            
        except Exception as e:
            logger.error(f"Error updating manager metrics: {e}")
    
    def get_manager_status(self) -> Dict[str, Any]:
        """Get comprehensive manager status"""
        
        with self._lock:
            return {
                'strategies_registered': len(self.registry.list_strategies()),
                'strategies_deployed': len(self._active_deployments),
                'monitoring_active': self._monitoring_active,
                'execution_engine_active': self.execution_engine._execution_active,
                'templates_available': len(self.registry.list_templates()),
                'metrics': self._manager_metrics.copy()
            }
    
    def get_strategy_summary(self, strategy_id: str) -> Dict[str, Any]:
        """Get comprehensive strategy summary"""
        
        try:
            strategy = self.registry.get_strategy(strategy_id)
            if not strategy:
                return {'error': 'Strategy not found'}
            
            summary = {
                'strategy_id': strategy_id,
                'state': strategy.get_state().value,
                'config': {
                    'strategy_type': strategy.config.strategy_type.value,
                    'max_positions': strategy.config.max_positions,
                    'risk_per_trade': strategy.config.risk_per_trade
                },
                'metrics': strategy.get_metrics(),
                'lifecycle': self.lifecycle_manager.get_strategy_lifecycle(strategy_id),
                'health': self.lifecycle_manager.get_strategy_health(strategy_id),
                'deployment': self._active_deployments.get(strategy_id)
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting strategy summary: {e}")
            return {'error': str(e)}