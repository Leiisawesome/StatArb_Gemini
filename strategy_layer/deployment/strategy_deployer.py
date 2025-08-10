"""
Strategy Deployer

Live strategy deployment and execution management.

Author: Pro Quant Desk Trader
"""

import logging
import asyncio
import json
import os
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

from strategy_layer.base import StrategyConfig, StrategyType, StrategyStatus
from ..strategies import (
    MomentumStrategyDefinition,
    PairTradingStrategyDefinition,
    MeanReversionStrategyDefinition
)
from ..testing import StrategyTestSuite, TestResult


class DeploymentStatus(Enum):
    """Deployment status enumeration"""
    PENDING = "pending"
    DEPLOYING = "deploying"
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"
    ROLLING_BACK = "rolling_back"


class EnvironmentType(Enum):
    """Environment type enumeration"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    PAPER_TRADING = "paper_trading"


@dataclass
class DeploymentConfig:
    """Configuration for strategy deployment"""
    environment: EnvironmentType
    max_concurrent_strategies: int = 10
    health_check_interval: int = 30  # seconds
    max_memory_usage: float = 0.8  # 80% of available memory
    max_cpu_usage: float = 0.9  # 90% of available CPU
    auto_restart_on_failure: bool = True
    max_restart_attempts: int = 3
    rollback_on_failure: bool = True
    monitoring_enabled: bool = True
    logging_level: str = "INFO"
    backup_enabled: bool = True
    backup_interval: int = 3600  # 1 hour


@dataclass
class DeploymentResult:
    """Result of a strategy deployment"""
    strategy_id: str
    deployment_id: str
    status: DeploymentStatus
    deployment_time: datetime
    environment: EnvironmentType
    success: bool
    message: str
    error_details: Optional[str] = None
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    resource_usage: Dict[str, float] = field(default_factory=dict)


@dataclass
class DeploymentInfo:
    """Information about a deployed strategy"""
    strategy_id: str
    deployment_id: str
    config: StrategyConfig
    status: DeploymentStatus
    deployment_time: datetime
    last_health_check: datetime
    restart_count: int = 0
    total_executions: int = 0
    success_count: int = 0
    error_count: int = 0
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    resource_usage: Dict[str, float] = field(default_factory=dict)


class StrategyDeployer:
    """Main strategy deployment and execution manager"""
    
    def __init__(self, config: DeploymentConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.deployed_strategies: Dict[str, DeploymentInfo] = {}
        self.deployment_history: List[DeploymentResult] = []
        self.is_running = False
    
    async def start(self):
        """Start the deployment manager"""
        self.logger.info("Starting Strategy Deployer")
        self.is_running = True
        self.logger.info("Strategy Deployer started successfully")
    
    async def stop(self):
        """Stop the deployment manager"""
        self.logger.info("Stopping Strategy Deployer")
        self.is_running = False
        await self.stop_all_strategies()
        self.logger.info("Strategy Deployer stopped")
    
    async def deploy_strategy(self, strategy_config: StrategyConfig) -> DeploymentResult:
        """Deploy a strategy to the specified environment"""
        deployment_id = f"{strategy_config.strategy_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.logger.info(f"Deploying strategy {strategy_config.strategy_id}")
        
        try:
            # Check deployment limits
            if len(self.deployed_strategies) >= self.config.max_concurrent_strategies:
                return DeploymentResult(
                    strategy_id=strategy_config.strategy_id,
                    deployment_id=deployment_id,
                    status=DeploymentStatus.ERROR,
                    deployment_time=datetime.now(),
                    environment=self.config.environment,
                    success=False,
                    message="Maximum concurrent strategies limit reached"
                )
            
            # Create strategy instance
            strategy = await self._create_strategy_instance(strategy_config)
            
            # Initialize deployment info
            deployment_info = DeploymentInfo(
                strategy_id=strategy_config.strategy_id,
                deployment_id=deployment_id,
                config=strategy_config,
                status=DeploymentStatus.ACTIVE,
                deployment_time=datetime.now(),
                last_health_check=datetime.now()
            )
            
            # Add to deployed strategies
            self.deployed_strategies[deployment_id] = deployment_info
            
            # Create deployment result
            result = DeploymentResult(
                strategy_id=strategy_config.strategy_id,
                deployment_id=deployment_id,
                status=DeploymentStatus.ACTIVE,
                deployment_time=datetime.now(),
                environment=self.config.environment,
                success=True,
                message="Strategy deployed successfully"
            )
            
            self.deployment_history.append(result)
            self.logger.info(f"Strategy {strategy_config.strategy_id} deployed successfully")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to deploy strategy {strategy_config.strategy_id}: {e}")
            
            result = DeploymentResult(
                strategy_id=strategy_config.strategy_id,
                deployment_id=deployment_id,
                status=DeploymentStatus.ERROR,
                deployment_time=datetime.now(),
                environment=self.config.environment,
                success=False,
                message=f"Deployment failed: {str(e)}",
                error_details=str(e)
            )
            
            self.deployment_history.append(result)
            return result
    
    async def stop_strategy(self, deployment_id: str) -> bool:
        """Stop a deployed strategy"""
        if deployment_id not in self.deployed_strategies:
            return False
        
        deployment_info = self.deployed_strategies[deployment_id]
        self.logger.info(f"Stopping strategy {deployment_info.strategy_id}")
        
        try:
            deployment_info.status = DeploymentStatus.STOPPED
            del self.deployed_strategies[deployment_id]
            return True
        except Exception as e:
            self.logger.error(f"Failed to stop strategy {deployment_info.strategy_id}: {e}")
            return False
    
    async def stop_all_strategies(self):
        """Stop all deployed strategies"""
        self.logger.info("Stopping all deployed strategies")
        deployment_ids = list(self.deployed_strategies.keys())
        for deployment_id in deployment_ids:
            await self.stop_strategy(deployment_id)
    
    def get_deployment_status(self, deployment_id: str) -> Optional[DeploymentInfo]:
        """Get status of a deployed strategy"""
        return self.deployed_strategies.get(deployment_id)
    
    def get_all_deployments(self) -> List[DeploymentInfo]:
        """Get all deployed strategies"""
        return list(self.deployed_strategies.values())
    
    def get_deployment_history(self) -> List[DeploymentResult]:
        """Get deployment history"""
        return self.deployment_history.copy()
    
    async def _create_strategy_instance(self, strategy_config: StrategyConfig):
        """Create strategy instance based on configuration"""
        strategy_type = strategy_config.strategy_type
        
        if strategy_type == StrategyType.MOMENTUM:
            return MomentumStrategyDefinition(strategy_config)
        elif strategy_type == StrategyType.PAIR_TRADING:
            return PairTradingStrategyDefinition(strategy_config)
        elif strategy_type == StrategyType.MEAN_REVERSION:
            return MeanReversionStrategyDefinition(strategy_config)
        else:
            raise ValueError(f"Unsupported strategy type: {strategy_type}")
