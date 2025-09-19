#!/usr/bin/env python3
"""
Core Structure - Simplified Trading System Architecture
=====================================================

This module exports the complete SystemOrchestrator architecture with
all essential flow components integrated and ready for use.

Essential Flow:
Market Data -> UnifiedDataManager -> UnifiedRegimeEngine -> RiskManager -> 
StrategyManager -> UnifiedExecutionEngine -> PortfolioManager

Author: Professional Trading System Architecture
Version: 1.0.0 (Complete Integration)
"""

import logging

# Main exports
from .infrastructure.system_orchestrator import (
    SystemOrchestrator, 
    OrchestrationConfig as SystemConfig, 
    ModuleStatus as SystemState,
    create_system_orchestrator
)

from .regime_engine import (
    UnifiedRegimeEngine,
    RegimeConfig,
    RegimeState
)

# Component exports
from .data_manager import (
    UnifiedDataManager,
    DataConfig,
    MarketData
)

from .advanced_risk_management import (
    AdvancedRiskManager as UnifiedRiskManager,
    RiskConfiguration as RiskConfig,
    RiskMetrics,
    RiskLevel
)

from .strategies import (
    StrategyManager,
    StrategyConfig,
    TradingSignal,
    SignalType,
    BaseStrategy
)

from .execution_engine import (
    UnifiedExecutionEngine,
    ExecutionConfig,
    Order,
    Position,
    OrderType,
    OrderStatus,
    OrderSide
)

from .portfolio_manager import (
    PortfolioManager,
    PortfolioConfig,
    PerformanceMetrics,
    PortfolioSnapshot
)

logger = logging.getLogger(__name__)

def get_system_info():
    """Get information about the trading system"""
    return {
        "name": "SystemOrchestrator Trading System",
        "version": "1.0.0",
        "architecture": "Complete Integration",
        "essential_flow": [
            "Market Data",
            "UnifiedDataManager", 
            "UnifiedRegimeEngine",
            "UnifiedRiskManager",
            "StrategyManager",
            "UnifiedExecutionEngine",
            "PortfolioManager"
        ],
        "components": {
            "SystemOrchestrator": "Main coordination class",
            "UnifiedDataManager": "Market data ingestion and processing",
            "UnifiedRegimeEngine": "Market condition assessment", 
            "UnifiedRiskManager": "Risk assessment and control",
            "StrategyManager": "Strategy execution and signal generation",
            "UnifiedExecutionEngine": "Trade execution and order management",
            "PortfolioManager": "Portfolio tracking and performance"
        }
    }

def check_dependencies():
    """Check system dependencies"""
    dependencies = {}
    
    try:
        import pandas as pd
        dependencies["pandas"] = pd.__version__
    except ImportError:
        dependencies["pandas"] = "missing"
    
    try:
        import numpy as np
        dependencies["numpy"] = np.__version__
    except ImportError:
        dependencies["numpy"] = "missing"
    
    try:
        import asyncio
        dependencies["asyncio"] = "available"
    except ImportError:
        dependencies["asyncio"] = "missing"
    
    return dependencies

# Initialize logging
logger.info("Core Structure initialized - SystemOrchestrator Architecture Ready")

# Export all components
__all__ = [
    'SystemOrchestrator',
    'SystemConfig', 
    'SystemState',
    'create_system_orchestrator',
    'UnifiedRegimeEngine',
    'RegimeConfig',
    'RegimeState',
    'UnifiedDataManager',
    'DataConfig',
    'MarketData',
    'UnifiedRiskManager',
    'RiskConfig',
    'RiskMetrics',
    'RiskLevel',
    'StrategyManager',
    'StrategyConfig',
    'TradingSignal',
    'SignalType',
    'BaseStrategy',
    'UnifiedExecutionEngine',
    'ExecutionConfig',
    'Order',
    'Position',
    'OrderType',
    'OrderStatus',
    'OrderSide',
    'PortfolioManager',
    'PortfolioConfig',
    'PerformanceMetrics',
    'PortfolioSnapshot',
    'get_system_info',
    'check_dependencies'
]
