"""
Backtest Types and Configuration
===============================

Common types and configuration classes for backtesting engines.

This module contains shared types that can be imported by both
trading engines and validation components without creating circular imports.

Author: StatArb_Gemini Backtest Types
Version: 1.0.0
"""

from datetime import datetime
from typing import Dict, List, Optional, Union, Any, Tuple, Set, Callable
from dataclasses import dataclass, field
from enum import Enum


class BacktestMode(Enum):
    """Backtest execution modes"""
    HISTORICAL = "historical"
    WALK_FORWARD = "walk_forward"
    MONTE_CARLO = "monte_carlo"
    STRESS_TEST = "stress_test"
    PAPER_TRADING = "paper_trading"


class ExecutionModel(Enum):
    """Trade execution models"""
    IMMEDIATE = "immediate"           # Execute at signal price
    NEXT_BAR = "next_bar"            # Execute at next bar open
    REALISTIC = "realistic"           # Include slippage and delays
    MARKET_IMPACT = "market_impact"   # Model market impact
    LIMIT_ORDERS = "limit_orders"     # Use limit orders


class SlippageModel(Enum):
    """Slippage models"""
    FIXED_PERCENTAGE = "fixed_percentage"
    FIXED_AMOUNT = "fixed_amount"
    VOLUME_BASED = "volume_based"
    SPREAD_BASED = "spread_based"
    MARKET_IMPACT = "market_impact"


class CommissionModel(Enum):
    """Commission models"""
    FIXED_PER_TRADE = "fixed_per_trade"
    PERCENTAGE = "percentage"
    PER_SHARE = "per_share"
    TIERED = "tiered"


@dataclass
class BacktestConfig:
    """Configuration for backtesting"""

    # Basic settings
    start_date: datetime = field(default_factory=lambda: datetime.now().replace(hour=0, minute=0, second=0, microsecond=0))
    end_date: datetime = field(default_factory=lambda: datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999))
    initial_capital: float = 100000.0
    benchmark_symbol: str = "SPY"

    # Execution settings
    execution_model: ExecutionModel = ExecutionModel.NEXT_BAR
    allow_short_selling: bool = True
    margin_requirement: float = 0.5  # 50% margin

    # Transaction costs
    commission_model: CommissionModel = CommissionModel.PERCENTAGE
    commission_rate: float = 0.001   # 0.1% commission
    fixed_commission: float = 5.0    # $5 per trade

    # Slippage settings
    slippage_model: SlippageModel = SlippageModel.FIXED_PERCENTAGE
    slippage_rate: float = 0.0005    # 0.05% slippage
    fixed_slippage: float = 0.01     # $0.01 fixed slippage

    # Risk management
    margin_call_threshold: float = 0.25  # 25% margin call
    stop_loss_on_margin_call: bool = True
    max_leverage: float = 2.0

    # Data settings
    data_frequency: str = "1D"  # Daily data
    adjust_for_splits: bool = True
    adjust_for_dividends: bool = True

    # Strategy settings
    rebalance_frequency: str = "daily"
    max_position_size: float = 0.1  # 10% of portfolio
    min_position_size: float = 0.001  # 0.1% of portfolio

    # Validation settings
    min_trades_required: int = 30
    confidence_level: float = 0.95

    # Walk-forward settings
    walk_forward_window: int = 252  # 1 year
    walk_forward_step: int = 21     # 1 month

    # Monte Carlo settings
    monte_carlo_simulations: int = 1000
    monte_carlo_time_horizon: int = 252


@dataclass
class BacktestResult:
    """Comprehensive backtest results"""

    # Basic information
    strategy_id: str = ""
    backtest_config: Optional[Any] = None  # Avoid circular import

    # Performance metrics
    performance_metrics: Optional[Any] = None  # PerformanceMetrics
    final_portfolio_value: float = 0.0
    total_return: float = 0.0
    annualized_return: float = 0.0
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0

    # Trading statistics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0

    # Time series data
    portfolio_history: List[Any] = field(default_factory=list)  # List[Portfolio]
    returns_series: Optional[Any] = None  # pd.Series
    positions_history: Optional[Any] = None  # pd.DataFrame

    # Trade log
    trade_log: List[Any] = field(default_factory=list)  # List[Trade]

    # Benchmark comparison
    benchmark_returns: Optional[Any] = None  # pd.Series
    alpha: float = 0.0
    beta: float = 0.0
    information_ratio: float = 0.0

    # Risk analysis
    var_95: float = 0.0
    cvar_95: float = 0.0
    calmar_ratio: float = 0.0

    # Validation results
    walk_forward_results: Optional[Any] = None
    monte_carlo_results: Optional[Any] = None

    # Metadata
    execution_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    success: bool = True
    error_message: str = ""