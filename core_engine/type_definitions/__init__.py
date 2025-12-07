"""
Core Engine Types - Standalone Trading System Types

Essential types and interfaces for core_engine independence.
Lightweight implementations replacing core_structure dependencies.
"""

from .orders import Order, OrderType, OrderStatus, OrderSide, ExecutionResult
from .portfolio import Portfolio, PortfolioManager, PortfolioSnapshot, PortfolioConfig, Position
from .strategy import (
    BaseStrategy, StrategyInterface, StrategyMetrics, StrategyType,
    StrategyConfig, TradingSignal, StrategyManager,
    SignalType, SignalStrength  # Canonical signal types
)
from .risk import RiskManager, RiskMetrics, RiskConfig, RiskResult, RiskLevel
from .regime import MarketRegime, RegimeType, RegimeState, RegimeConfig, RegimeSignal, RegimeEngine
from .data import DataManager, DataProvider, MarketData, DataConfig
from .analytics import AnalyticsEngine, PerformanceMetrics
from .broker import BrokerInterface, BrokerManager, BrokerConfig, PaperBroker, BrokerType

__all__ = [
    # Orders
    'Order', 'OrderType', 'OrderStatus', 'OrderSide', 'ExecutionResult',

    # Portfolio
    'Portfolio', 'PortfolioManager', 'PortfolioSnapshot', 'PortfolioConfig', 'Position',

    # Strategy
    'BaseStrategy', 'StrategyInterface', 'StrategyMetrics', 'StrategyType',
    'StrategyConfig', 'TradingSignal', 'StrategyManager',
    'SignalType', 'SignalStrength',  # Canonical signal types

    # Risk
    'RiskManager', 'RiskMetrics', 'RiskConfig', 'RiskResult', 'RiskLevel',

    # Regime (Canonical types - Single Source of Truth)
    'MarketRegime', 'RegimeType', 'RegimeState', 'RegimeConfig', 'RegimeSignal', 'RegimeEngine',

    # Data
    'DataManager', 'DataProvider', 'MarketData', 'DataConfig',

    # Analytics
    'AnalyticsEngine', 'PerformanceMetrics',

    # Broker
    'BrokerInterface', 'BrokerManager', 'BrokerConfig', 'PaperBroker', 'BrokerType'
]