"""
Core Engine - Standalone Trading System

A complete institutional-grade trading engine with no external dependencies.
Features comprehensive portfolio management, strategy execution, risk controls,
and performance analytics.

Key Components:
1. CoreEngine - Main trading engine
2. Portfolio Management - Position tracking and risk controls
3. Strategy System - Signal generation and execution
4. Risk Management - Trade authorization and limits
5. Data Management - Market data handling
6. Broker Integration - Order execution (paper and live)
7. Analytics - Performance measurement and reporting
8. Regime Detection - Market condition assessment

Usage:
    from core_engine import CoreEngine
    
    engine = CoreEngine({
        'initial_cash': 100000,
        'commission_rate': 0.001
    })
    
    engine.initialize()
    # Add strategies and run backtests
"""

# Import main engine
from .engine import CoreEngine

# Import key types for strategy development
from .types import (
    BaseStrategy, StrategyConfig, StrategyType, TradingSignal,
    PortfolioConfig, RiskConfig, DataConfig,
    Order, OrderType, OrderSide
)

__version__ = "1.0.0"
__all__ = [
    'CoreEngine',
    'BaseStrategy', 
    'StrategyConfig', 
    'StrategyType', 
    'TradingSignal',
    'PortfolioConfig',
    'RiskConfig', 
    'DataConfig',
    'Order',
    'OrderType', 
    'OrderSide'
]