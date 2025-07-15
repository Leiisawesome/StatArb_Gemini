"""
Portfolio Management Module for AI-Ready Statistical Arbitrage System
====================================================================

This module provides advanced portfolio management capabilities with:
- AI-driven portfolio optimization and allocation
- Real-time portfolio monitoring and rebalancing
- Multi-strategy portfolio construction
- Advanced performance attribution and analytics
- Risk-adjusted position sizing and capital allocation

Key Components:
- PortfolioManager: Core portfolio management engine
- AllocationOptimizer: AI-driven allocation optimization
- PerformanceAnalyzer: Comprehensive performance analytics
- RebalancingEngine: Automated rebalancing with smart triggers

Author: Pro Quant Desk Trader
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# Core portfolio management components
try:
    from .portfolio_manager import (
        PortfolioManager,
        PortfolioConfig,
        PortfolioState,
        Position,
        PortfolioMetrics
    )
    
    from .allocation_optimizer import (
        AllocationOptimizer,
        AllocationMethod,
        AllocationConfig,
        AllocationResult,
        OptimizationConstraints
    )
    
    from .performance_analyzer import (
        PerformanceAnalyzer,
        PerformanceMetrics,
        AttributionAnalysis,
        RiskMetrics,
        PerformanceReport
    )
    
    from .rebalancing_engine import (
        RebalancingEngine,
        RebalancingConfig,
        RebalancingTrigger,
        RebalancingResult,
        RebalancingSchedule
    )
    
    PORTFOLIO_MANAGEMENT_AVAILABLE = True
    logger.info("Portfolio management module loaded successfully")
    
except ImportError as e:
    logger.error(f"Failed to import portfolio management components: {e}")
    PORTFOLIO_MANAGEMENT_AVAILABLE = False
    
    # Fallback imports for graceful degradation
    PortfolioManager = None
    AllocationOptimizer = None
    PerformanceAnalyzer = None
    RebalancingEngine = None

# Module configuration
DEFAULT_CONFIG = {
    'max_positions': 50,
    'max_position_weight': 0.15,
    'rebalancing_frequency': 'daily',
    'risk_budget': 0.02,
    'target_volatility': 0.12,
    'correlation_threshold': 0.8,
    'minimum_position_size': 0.01
}

def get_module_health() -> Dict[str, Any]:
    """Get portfolio management module health status"""
    return {
        'module_name': 'portfolio_management',
        'version': '1.0.0',
        'status': 'healthy' if PORTFOLIO_MANAGEMENT_AVAILABLE else 'degraded',
        'components_available': PORTFOLIO_MANAGEMENT_AVAILABLE,
        'last_check': datetime.now().isoformat(),
        'dependencies': ['numpy', 'pandas', 'scipy', 'scikit-learn'],
        'config': DEFAULT_CONFIG
    }

def create_portfolio_manager(config: Optional[Dict[str, Any]] = None) -> Optional['PortfolioManager']:
    """Factory function to create portfolio manager instance"""
    if not PORTFOLIO_MANAGEMENT_AVAILABLE:
        logger.error("Portfolio management components not available")
        return None
    
    try:
        manager_config = {**DEFAULT_CONFIG, **(config or {})}
        return PortfolioManager(manager_config)
    except Exception as e:
        logger.error(f"Failed to create portfolio manager: {e}")
        return None

__all__ = [
    'PortfolioManager',
    'AllocationOptimizer', 
    'PerformanceAnalyzer',
    'RebalancingEngine',
    'PortfolioConfig',
    'PortfolioState',
    'Position',
    'PortfolioMetrics',
    'AllocationMethod',
    'AllocationConfig',
    'AllocationResult',
    'OptimizationConstraints',
    'PerformanceMetrics',
    'AttributionAnalysis',
    'RiskMetrics',
    'PerformanceReport',
    'RebalancingConfig',
    'RebalancingTrigger',
    'RebalancingResult',
    'RebalancingSchedule',
    'get_module_health',
    'create_portfolio_manager',
    'DEFAULT_CONFIG'
]

__version__ = "1.0.0" 