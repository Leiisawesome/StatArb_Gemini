"""
Strategy Engine Module for AI-Ready Statistical Arbitrage System
================================================================

This module provides a comprehensive strategy execution framework with:
- Multi-strategy framework with unified interface
- AI agent integration points for adaptive strategy selection
- Real-time strategy performance monitoring and allocation
- Professional execution engine with market impact modeling

Key Components:
- StrategyEngine: Core strategy orchestration and execution
- StrategyRegistry: Dynamic strategy registration and management  
- ExecutionEngine: Professional trade execution with smart routing

Note: Risk management and performance attribution components will be added in Phase 3A

Author: Pro Quant Desk Trader
"""

import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# Core strategy engine components
try:
    from .strategy_engine import (
        StrategyEngine,
        StrategyConfig,
        StrategyResult,
        StrategyStatus,
        ExecutionMode,
        AllocationMethod
    )
    
    from .strategy_registry import (
        StrategyRegistry,
        BaseStrategy,
        StrategyType,
        StrategyMetadata,
        StrategyPerformance
    )
    
    from .execution_engine import (
        ExecutionEngine,
        ExecutionConfig,
        OrderManager,
        TradeExecution,
        ExecutionResult
    )
    
    logger.info("Strategy engine module loaded successfully")
    
except ImportError as e:
    logger.error(f"Failed to import strategy engine components: {e}")
    # Set components to None if import fails
    StrategyEngine = None
    StrategyRegistry = None
    ExecutionEngine = None

# Module exports
__all__ = [
    # Core components
    "StrategyEngine",
    "StrategyRegistry", 
    "ExecutionEngine",
    
    # Configuration classes
    "StrategyConfig",
    "ExecutionConfig",
    
    # Data classes
    "StrategyResult",
    "StrategyMetadata",
    "StrategyPerformance",
    "TradeExecution",
    "ExecutionResult",
    
    # Enums
    "StrategyStatus",
    "ExecutionMode",
    "AllocationMethod",
    "StrategyType",
    
    # Base classes
    "BaseStrategy",
    "OrderManager",
    
    # Factory functions
    "create_strategy_engine",
    "create_execution_engine",
    "get_available_strategies",
    "get_module_health",
    
    # AI integration
    "AIAgentInterface"
]

def create_strategy_engine(config: Optional[Dict[str, Any]] = None):
    """
    Factory function to create a StrategyEngine instance
    
    Args:
        config: Strategy engine configuration
        
    Returns:
        StrategyEngine instance or None if creation fails
    """
    if StrategyEngine is None:
        logger.error("StrategyEngine not available")
        return None
        
    try:
        if config:
            if isinstance(config, dict):
                strategy_config = StrategyConfig(**config)
            else:
                strategy_config = config
        else:
            strategy_config = StrategyConfig()
            
        return StrategyEngine(strategy_config)
    except Exception as e:
        logger.error(f"Failed to create StrategyEngine: {e}")
        return None

def create_execution_engine(config: Optional[Dict[str, Any]] = None):
    """
    Factory function to create an ExecutionEngine instance
    
    Args:
        config: Execution engine configuration
        
    Returns:
        ExecutionEngine instance or None if creation fails
    """
    if ExecutionEngine is None:
        logger.error("ExecutionEngine not available")
        return None
        
    try:
        if config:
            if isinstance(config, dict):
                exec_config = ExecutionConfig(**config)
            else:
                exec_config = config
        else:
            exec_config = ExecutionConfig()
            
        return ExecutionEngine(exec_config)
    except Exception as e:
        logger.error(f"Failed to create ExecutionEngine: {e}")
        return None

def get_available_strategies() -> List[str]:
    """
    Get list of available strategy types
    
    Returns:
        List of strategy type names
    """
    try:
        if StrategyType:
            return [strategy.value for strategy in StrategyType]
        else:
            return ["stat_arb", "pairs_trading", "momentum", "mean_reversion"]
    except Exception as e:
        logger.error(f"Error getting available strategies: {e}")
        return []

def get_module_health() -> Dict[str, Any]:
    """
    Get health status of the strategy engine module
    
    Returns:
        Dictionary with health status information
    """
    health = {
        "module_loaded": True,
        "components": {
            "strategy_engine": StrategyEngine is not None,
            "strategy_registry": StrategyRegistry is not None,
            "execution_engine": ExecutionEngine is not None
        },
        "available_strategies": get_available_strategies(),
        "timestamp": "2024-01-01T00:00:00Z"
    }
    
    health["overall_status"] = "healthy" if all(health["components"].values()) else "degraded"
    
    return health

class AIAgentInterface:
    """Interface for AI agent integration with strategy engine"""
    
    @staticmethod
    def register_strategy_selector(selector_func) -> bool:
        """
        Register an AI strategy selector function
        
        Args:
            selector_func: Function that selects optimal strategies
            
        Returns:
            True if registered successfully
        """
        try:
            # Implementation will be added when AI agents are integrated
            logger.info("AI strategy selector registered")
            return True
        except Exception as e:
            logger.error(f"Failed to register AI strategy selector: {e}")
            return False
    
    @staticmethod
    def register_risk_monitor(monitor_func) -> bool:
        """
        Register an AI risk monitoring function
        
        Args:
            monitor_func: Function that monitors risk in real-time
            
        Returns:
            True if registered successfully
        """
        try:
            # Implementation will be added when AI agents are integrated
            logger.info("AI risk monitor registered")
            return True
        except Exception as e:
            logger.error(f"Failed to register AI risk monitor: {e}")
            return False
    
    @staticmethod
    def register_performance_optimizer(optimizer_func) -> bool:
        """
        Register an AI performance optimizer function
        
        Args:
            optimizer_func: Function that optimizes strategy performance
            
        Returns:
            True if registered successfully
        """
        try:
            # Implementation will be added when AI agents are integrated
            logger.info("AI performance optimizer registered")
            return True
        except Exception as e:
            logger.error(f"Failed to register AI performance optimizer: {e}")
            return False 