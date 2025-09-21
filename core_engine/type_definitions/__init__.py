"""
Core Engine Types - Standalone Trading System Types

Essential types and interfaces for core_engine independence.
Lightweight implementations replacing core_structure dependencies.
"""

from .orders import Order, OrderType, OrderStatus, OrderSide, ExecutionResult
from .portfolio import Portfolio, PortfolioManager, PortfolioSnapshot, PortfolioConfig
from .strategy import (
    BaseStrategy, StrategyInterface, StrategyMetrics, StrategyType, 
    StrategyConfig, TradingSignal, StrategyManager
)
from .risk import RiskManager, RiskMetrics, RiskConfig, RiskResult, RiskLevel
from .regime import RegimeState, RegimeConfig, RegimeEngine
from .data import DataManager, DataProvider, MarketData, DataConfig
from .analytics import AnalyticsEngine, PerformanceMetrics
from .broker import BrokerInterface, BrokerManager, BrokerConfig, PaperBroker, BrokerType

__all__ = [
    # Orders
    'Order', 'OrderType', 'OrderStatus', 'OrderSide', 'ExecutionResult',
    
    # Portfolio
    'Portfolio', 'PortfolioManager', 'PortfolioSnapshot', 'PortfolioConfig',
    
    # Strategy
    'BaseStrategy', 'StrategyInterface', 'StrategyMetrics', 'StrategyType',
    'StrategyConfig', 'TradingSignal', 'StrategyManager',
    
    # Risk
    'RiskManager', 'RiskMetrics', 'RiskConfig', 'RiskResult', 'RiskLevel',
    
    # Regime
    'RegimeState', 'RegimeConfig', 'RegimeEngine',
    
    # Data
    'DataManager', 'DataProvider', 'MarketData', 'DataConfig',
    
    # Analytics
    'AnalyticsEngine', 'PerformanceMetrics',
    
    # Broker
    'BrokerInterface', 'BrokerManager', 'BrokerConfig', 'PaperBroker', 'BrokerType'
]