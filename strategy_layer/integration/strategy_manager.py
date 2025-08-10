"""
Strategy Manager

Unified strategy management system integrating all strategy layer components.

Author: Pro Quant Desk Trader
"""

import logging
import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from strategy_layer.base import StrategyConfig, StrategyType, StrategyStatus
from strategy_layer.parsers import StrategyParser, SchemaValidator
from strategy_layer.builders import StrategyBuilder, StrategyFactory
from strategy_layer.strategies import (
    MomentumStrategyDefinition,
    PairTradingStrategyDefinition,
    MeanReversionStrategyDefinition
)
from strategy_layer.optimization import (
    GeneticOptimizer,
    BayesianOptimizer,
    GridSearchOptimizer,
    RandomSearchOptimizer
)
from strategy_layer.validation import (
    BacktestingValidator,
    WalkForwardValidator,
    ParameterValidator
)
from strategy_layer.testing import StrategyTestSuite, RegressionTestSuite
from strategy_layer.deployment import (
    StrategyDeployer,
    DeploymentConfig,
    EnvironmentManager,
    EnvironmentType
)
from strategy_layer.monitoring import (
    StrategyMonitor,
    MonitoringConfig,
    PerformanceAnalytics
)
from strategy_layer.registry import StrategyRegistry


@dataclass
class StrategyManagerConfig:
    """Configuration for the strategy manager"""
    enable_parsing: bool = True
    enable_building: bool = True
    enable_optimization: bool = True
    enable_validation: bool = True
    enable_testing: bool = True
    enable_deployment: bool = True
    enable_monitoring: bool = True
    enable_registry: bool = True
    auto_validate: bool = True
    auto_test: bool = True
    auto_deploy: bool = False
    auto_monitor: bool = True
    default_environment: str = "development"
    monitoring_interval: int = 30
    max_concurrent_strategies: int = 10


@dataclass
class StrategyLifecycle:
    """Strategy lifecycle information"""
    strategy_id: str
    status: str
    created_at: datetime
    last_updated: datetime
    current_phase: str
    phases_completed: List[str] = field(default_factory=list)
    phases_pending: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class StrategyManager:
    """Unified strategy management system"""
    
    def __init__(self, config: StrategyManagerConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize components
        self._initialize_components()
        
        # Strategy lifecycle tracking
        self.strategy_lifecycles: Dict[str, StrategyLifecycle] = {}
        
        self.logger.info("Strategy Manager initialized successfully")
    
    def _initialize_components(self):
        """Initialize all strategy layer components"""
        try:
            # Initialize parsers
            if self.config.enable_parsing:
                self.parser = StrategyParser()
                self.schema_validator = SchemaValidator()
                self.logger.info("Parsers initialized")
            
            # Initialize builders
            if self.config.enable_building:
                self.strategy_builder = StrategyBuilder()
                self.strategy_factory = StrategyFactory()
                self.logger.info("Builders initialized")
            
            # Initialize optimizers
            if self.config.enable_optimization:
                from strategy_layer.optimization import OptimizationConfig
                
                # Create default optimization configs with sample parameter bounds
                default_bounds = {
                    'rsi_period': (10, 30),
                    'macd_fast': (8, 16),
                    'macd_slow': (20, 40),
                    'signal_strength': (0.1, 0.9),
                    'position_size': (0.01, 0.2)
                }
                
                genetic_config = OptimizationConfig(
                    max_iterations=100,
                    population_size=50,
                    mutation_rate=0.1,
                    crossover_rate=0.8,
                    elite_size=5,
                    parameter_bounds=default_bounds
                )
                
                bayesian_config = OptimizationConfig(
                    max_iterations=50,
                    parameter_bounds=default_bounds
                )
                
                grid_config = OptimizationConfig(
                    max_iterations=100,
                    parameter_bounds=default_bounds
                )
                
                random_config = OptimizationConfig(
                    max_iterations=100,
                    parameter_bounds=default_bounds
                )
                
                self.genetic_optimizer = GeneticOptimizer(genetic_config)
                self.bayesian_optimizer = BayesianOptimizer(bayesian_config)
                self.grid_search_optimizer = GridSearchOptimizer(grid_config)
                self.random_search_optimizer = RandomSearchOptimizer(random_config)
                self.logger.info("Optimizers initialized")
            
            # Initialize validators
            if self.config.enable_validation:
                from strategy_layer.validation import ValidationConfig
                
                # Create default validation config
                validation_config = ValidationConfig(
                    start_date=datetime.now() - timedelta(days=365),
                    end_date=datetime.now(),
                    symbols=["AAPL", "GOOGL", "MSFT"],
                    initial_capital=100000.0,
                    commission_rate=0.001,
                    slippage_rate=0.0005
                )
                
                self.backtesting_validator = BacktestingValidator(validation_config)
                self.walk_forward_validator = WalkForwardValidator(validation_config)
                self.parameter_validator = ParameterValidator(validation_config)
                self.logger.info("Validators initialized")
            
            # Initialize testing (simplified for now)
            if self.config.enable_testing:
                # Create simple test config
                test_config = {
                    'performance_thresholds': {
                        'max_execution_time': 0.1,
                        'max_memory_increase': 50
                    }
                }
                self.test_suite = StrategyTestSuite(test_config)
                self.regression_suite = RegressionTestSuite()
                self.logger.info("Testing initialized")
            
            # Initialize deployment
            if self.config.enable_deployment:
                deployment_config = DeploymentConfig(
                    environment=EnvironmentType.DEVELOPMENT,
                    max_concurrent_strategies=self.config.max_concurrent_strategies,
                    monitoring_enabled=False
                )
                self.deployer = StrategyDeployer(deployment_config)
                self.env_manager = EnvironmentManager()
                self.logger.info("Deployment initialized")
            
            # Initialize monitoring
            if self.config.enable_monitoring:
                monitoring_config = MonitoringConfig(
                    monitoring_interval=self.config.monitoring_interval,
                    enable_alerting=True
                )
                self.monitor = StrategyMonitor(monitoring_config)
                self.analytics = PerformanceAnalytics()
                self.logger.info("Monitoring initialized")
            
            # Initialize registry
            if self.config.enable_registry:
                self.registry = StrategyRegistry()
                self.logger.info("Registry initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize components: {e}")
            raise
    
    async def start(self):
        """Start the strategy manager"""
        self.logger.info("Starting Strategy Manager")
        
        try:
            # Start deployment system
            if self.config.enable_deployment:
                await self.deployer.start()
            
            # Start monitoring system
            if self.config.enable_monitoring:
                await self.monitor.start()
            
            self.logger.info("Strategy Manager started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start Strategy Manager: {e}")
            raise
    
    async def stop(self):
        """Stop the strategy manager"""
        self.logger.info("Stopping Strategy Manager")
        
        try:
            # Stop deployment system
            if self.config.enable_deployment:
                await self.deployer.stop()
            
            # Stop monitoring system
            if self.config.enable_monitoring:
                await self.monitor.stop()
            
            self.logger.info("Strategy Manager stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to stop Strategy Manager: {e}")
            raise
    
    async def create_strategy_from_json(self, json_config: str) -> Dict[str, Any]:
        """Create a strategy from JSON configuration"""
        strategy_id = f"strategy_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Initialize lifecycle
        lifecycle = StrategyLifecycle(
            strategy_id=strategy_id,
            status="creating",
            created_at=datetime.now(),
            last_updated=datetime.now(),
            current_phase="parsing",
            phases_pending=["parsing", "building", "validation", "testing", "deployment", "monitoring"]
        )
        self.strategy_lifecycles[strategy_id] = lifecycle
        
        try:
            # Phase 1: Parsing
            if self.config.enable_parsing:
                self.logger.info(f"Parsing strategy {strategy_id}")
                lifecycle.current_phase = "parsing"
                
                # Validate schema
                validation_result = self.schema_validator.validate(json_config)
                if not validation_result.is_valid:
                    raise ValueError(f"Schema validation failed: {validation_result.errors}")
                
                # Parse strategy
                strategy_config = self.parser.parse_strategy(json_config)
                lifecycle.phases_completed.append("parsing")
                lifecycle.current_phase = "building"
                self.logger.info(f"Strategy {strategy_id} parsed successfully")
            
            # Phase 2: Building
            if self.config.enable_building:
                self.logger.info(f"Building strategy {strategy_id}")
                lifecycle.current_phase = "building"
                
                # Build strategy
                strategy = self.strategy_builder.build_strategy(strategy_config)
                lifecycle.phases_completed.append("building")
                lifecycle.current_phase = "validation"
                self.logger.info(f"Strategy {strategy_id} built successfully")
            
            # Phase 3: Validation
            if self.config.enable_validation and self.config.auto_validate:
                self.logger.info(f"Validating strategy {strategy_id}")
                lifecycle.current_phase = "validation"
                
                # Run validation
                validation_result = await self.backtesting_validator.validate_strategy(strategy)
                if not validation_result.success:
                    lifecycle.errors.append(f"Validation failed: {validation_result.message}")
                    lifecycle.status = "validation_failed"
                    return self._create_response(strategy_id, False, "Validation failed", lifecycle)
                
                lifecycle.phases_completed.append("validation")
                lifecycle.current_phase = "testing"
                self.logger.info(f"Strategy {strategy_id} validated successfully")
            
            # Phase 4: Testing
            if self.config.enable_testing and self.config.auto_test:
                self.logger.info(f"Testing strategy {strategy_id}")
                lifecycle.current_phase = "testing"
                
                # Run tests
                test_results = self.test_suite.run_all_tests([strategy])
                passed_tests = len([r for r in test_results if r.status == "PASS"])
                total_tests = len(test_results)
                
                if total_tests > 0 and passed_tests / total_tests < 0.8:  # 80% pass rate
                    lifecycle.errors.append(f"Testing failed: {passed_tests}/{total_tests} tests passed")
                    lifecycle.status = "testing_failed"
                    return self._create_response(strategy_id, False, "Testing failed", lifecycle)
                
                lifecycle.phases_completed.append("testing")
                lifecycle.current_phase = "deployment"
                self.logger.info(f"Strategy {strategy_id} tested successfully")
            
            # Phase 5: Deployment
            if self.config.enable_deployment and self.config.auto_deploy:
                self.logger.info(f"Deploying strategy {strategy_id}")
                lifecycle.current_phase = "deployment"
                
                # Deploy strategy
                deployment_result = await self.deployer.deploy_strategy(strategy_config)
                if not deployment_result.success:
                    lifecycle.errors.append(f"Deployment failed: {deployment_result.message}")
                    lifecycle.status = "deployment_failed"
                    return self._create_response(strategy_id, False, "Deployment failed", lifecycle)
                
                lifecycle.phases_completed.append("deployment")
                lifecycle.current_phase = "monitoring"
                self.logger.info(f"Strategy {strategy_id} deployed successfully")
            
            # Phase 6: Monitoring
            if self.config.enable_monitoring and self.config.auto_monitor:
                self.logger.info(f"Adding strategy {strategy_id} to monitoring")
                lifecycle.current_phase = "monitoring"
                
                # Add to monitoring
                if hasattr(self, 'deployer'):
                    deployment_info = self.deployer.get_deployment_status(deployment_result.deployment_id)
                    if deployment_info:
                        self.monitor.add_strategy(deployment_info)
                
                lifecycle.phases_completed.append("monitoring")
                self.logger.info(f"Strategy {strategy_id} added to monitoring")
            
            # Register strategy
            if self.config.enable_registry:
                # Registry is a placeholder for now
                pass
            
            # Update lifecycle
            lifecycle.status = "active"
            lifecycle.current_phase = "completed"
            lifecycle.last_updated = datetime.now()
            
            self.logger.info(f"Strategy {strategy_id} created successfully")
            return self._create_response(strategy_id, True, "Strategy created successfully", lifecycle)
            
        except Exception as e:
            self.logger.error(f"Failed to create strategy {strategy_id}: {e}")
            lifecycle.errors.append(str(e))
            lifecycle.status = "failed"
            lifecycle.last_updated = datetime.now()
            return self._create_response(strategy_id, False, f"Strategy creation failed: {e}", lifecycle)
    
    def get_strategy_status(self, strategy_id: str) -> Dict[str, Any]:
        """Get comprehensive status of a strategy"""
        try:
            status = {
                "strategy_id": strategy_id,
                "lifecycle": None,
                "deployment": None,
                "monitoring": None,
                "registry": None
            }
            
            # Get lifecycle
            if strategy_id in self.strategy_lifecycles:
                lifecycle = self.strategy_lifecycles[strategy_id]
                status["lifecycle"] = {
                    "status": lifecycle.status,
                    "current_phase": lifecycle.current_phase,
                    "phases_completed": lifecycle.phases_completed,
                    "phases_pending": lifecycle.phases_pending,
                    "errors": lifecycle.errors,
                    "warnings": lifecycle.warnings,
                    "created_at": lifecycle.created_at.isoformat(),
                    "last_updated": lifecycle.last_updated.isoformat()
                }
            
            # Get deployment status
            if self.config.enable_deployment:
                deployments = self.deployer.get_all_deployments()
                for deployment in deployments:
                    if deployment.strategy_id == strategy_id:
                        status["deployment"] = {
                            "deployment_id": deployment.deployment_id,
                            "status": deployment.status.value,
                            "deployment_time": deployment.deployment_time.isoformat(),
                            "total_executions": deployment.total_executions,
                            "success_count": deployment.success_count,
                            "error_count": deployment.error_count,
                            "restart_count": deployment.restart_count
                        }
                        break
            
            # Get monitoring status
            if self.config.enable_monitoring:
                # Get performance metrics
                metrics = self.monitor.get_performance_metrics(strategy_id, hours=24)
                if metrics:
                    latest_metrics = metrics[-1]
                    status["monitoring"] = {
                        "success_rate": latest_metrics.success_rate,
                        "error_rate": latest_metrics.error_rate,
                        "avg_execution_time": latest_metrics.execution_time,
                        "memory_usage": latest_metrics.memory_usage,
                        "cpu_usage": latest_metrics.cpu_usage
                    }
                
                # Get health status
                health_statuses = self.monitor.get_health_status(strategy_id, hours=24)
                if health_statuses:
                    latest_health = health_statuses[-1]
                    status["monitoring"]["health"] = {
                        "is_healthy": latest_health.is_healthy,
                        "health_score": latest_health.health_score,
                        "uptime": latest_health.uptime,
                        "restart_count": latest_health.restart_count
                    }
            
            # Get registry status
            if self.config.enable_registry:
                # Registry is a placeholder for now
                status["registry"] = {
                    "strategy_type": "unknown",
                    "name": "unknown",
                    "version": "unknown",
                    "status": "unknown"
                }
            
            return status
            
        except Exception as e:
            self.logger.error(f"Failed to get strategy status {strategy_id}: {e}")
            return {"error": str(e)}
    
    def get_system_summary(self) -> Dict[str, Any]:
        """Get comprehensive system summary"""
        try:
            summary = {
                "system_status": "active",
                "components": {},
                "statistics": {}
            }
            
            # Component status
            summary["components"] = {
                "parsing": self.config.enable_parsing,
                "building": self.config.enable_building,
                "optimization": self.config.enable_optimization,
                "validation": self.config.enable_validation,
                "testing": self.config.enable_testing,
                "deployment": self.config.enable_deployment,
                "monitoring": self.config.enable_monitoring,
                "registry": self.config.enable_registry
            }
            
            # Statistics
            if self.config.enable_registry:
                # Registry is a placeholder for now
                summary["statistics"]["total_strategies"] = 0
            
            if self.config.enable_deployment:
                deployments = self.deployer.get_all_deployments()
                summary["statistics"]["deployed_strategies"] = len(deployments)
                summary["statistics"]["active_deployments"] = len([
                    d for d in deployments if d.status.value == "active"
                ])
            
            if self.config.enable_monitoring:
                monitoring_summary = self.monitor.get_monitoring_summary()
                summary["statistics"]["monitoring"] = monitoring_summary
            
            # Lifecycle statistics
            total_lifecycles = len(self.strategy_lifecycles)
            active_lifecycles = len([
                l for l in self.strategy_lifecycles.values() if l.status == "active"
            ])
            failed_lifecycles = len([
                l for l in self.strategy_lifecycles.values() if l.status == "failed"
            ])
            
            summary["statistics"]["lifecycles"] = {
                "total": total_lifecycles,
                "active": active_lifecycles,
                "failed": failed_lifecycles
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to get system summary: {e}")
            return {"error": str(e)}
    
    def _create_response(self, strategy_id: str, success: bool, message: str, lifecycle: StrategyLifecycle) -> Dict[str, Any]:
        """Create a standardized response"""
        return {
            "strategy_id": strategy_id,
            "success": success,
            "message": message,
            "lifecycle": {
                "status": lifecycle.status,
                "current_phase": lifecycle.current_phase,
                "phases_completed": lifecycle.phases_completed,
                "phases_pending": lifecycle.phases_pending,
                "errors": lifecycle.errors,
                "warnings": lifecycle.warnings
            }
        }
