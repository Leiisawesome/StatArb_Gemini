"""
Components Module - Core Trading Components
==========================================

This module contains all core trading components used by the UnifiedTradingEngine.
Organized by functional area for better maintainability.

Components:
- execution/: Order execution and trade management
- market_data/: Market data feeds and management
- portfolio/: Portfolio tracking and management
- risk/: Risk management and controls
- signal_generation/: Trading signal generation
- broker_integration/: Broker connectivity

Author: Professional Trading System Architecture
Version: PRODUCTION (Reorganized)
"""

# Unified Execution Engine
from .execution import (
    UnifiedExecutionEngine,
    ExecutionMode,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus
)

# Market Data
from .market_data import (
    EnhancedDataManager,
    EnhancedClickHouseLoader,
    BacktestingDataProvider,
    DataRequest
)

# Portfolio Management
from .portfolio import (
    PortfolioManager,
    PortfolioMetrics
)

# Risk Management
from .risk import (
    RiskManager,
    RiskLimits
)

# Signal Generation
from .signal_generation import (
    UnifiedSignalEngine,
    SignalConfig,
    TradingSignal,
    SignalType,
    SignalStrength
)

# Broker Integration
from .broker_integration import (
    BaseBroker,
    IBKRClient
)

__all__ = [
    # Unified Execution
    'UnifiedExecutionEngine',
    'ExecutionMode',
    'ExecutionRequest',
    'ExecutionResult',
    'ExecutionStatus',
    
    # Market Data
    'EnhancedDataManager',
    'EnhancedClickHouseLoader',
    'BacktestingDataProvider',
    'DataRequest',
    
    # Portfolio
    'PortfolioManager',
    'PortfolioMetrics',
    
    # Risk
    'RiskManager',
    'RiskLimits',
    
    # Signal Generation
    'UnifiedSignalEngine',
    'SignalConfig',
    'TradingSignal', 
    'SignalType',
    'SignalStrength',
    
    # Broker Integration
    'BaseBroker',
    'IBKRClient'
]
