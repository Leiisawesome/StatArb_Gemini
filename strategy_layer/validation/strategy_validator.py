"""
Strategy Validator Base Class

Base class for strategy validation and backtesting.

Author: Pro Quant Desk Trader
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple, Callable
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import warnings

from strategy_layer.base import StrategyError, StrategyDefinition, StrategyConfig
from strategy_layer.strategies import (
    MomentumStrategyDefinition,
    PairTradingStrategyDefinition,
    MeanReversionStrategyDefinition
)


@dataclass
class ValidationConfig:
    """Configuration for strategy validation"""
    # Data configuration
    start_date: datetime
    end_date: datetime
    symbols: List[str] = field(default_factory=list)
    
    # Validation parameters
    initial_capital: float = 100000.0
    commission_rate: float = 0.001  # 0.1%
    slippage_rate: float = 0.0005   # 0.05%
    
    # Risk parameters
    max_position_size: float = 0.2  # 20% of portfolio
    max_drawdown: float = 0.25      # 25% max drawdown
    stop_loss: float = 0.02         # 2% stop loss
    take_profit: float = 0.04       # 4% take profit
    
    # Performance metrics
    benchmark_symbol: str = "SPY"
    risk_free_rate: float = 0.02    # 2% annual risk-free rate
    
    # Validation settings
    validation_split: float = 0.2   # 20% for validation
    walk_forward_windows: int = 5   # Number of walk-forward windows
    min_trades: int = 10            # Minimum trades for validation
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'symbols': self.symbols,
            'initial_capital': self.initial_capital,
            'commission_rate': self.commission_rate,
            'slippage_rate': self.slippage_rate,
            'max_position_size': self.max_position_size,
            'max_drawdown': self.max_drawdown,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'benchmark_symbol': self.benchmark_symbol,
            'risk_free_rate': self.risk_free_rate,
            'validation_split': self.validation_split,
            'walk_forward_windows': self.walk_forward_windows,
            'min_trades': self.min_trades
        }


@dataclass
class Trade:
    """Individual trade record"""
    symbol: str
    entry_date: datetime
    exit_date: Optional[datetime] = None
    entry_price: float = 0.0
    exit_price: float = 0.0
    position_size: float = 0.0
    side: str = "LONG"  # LONG or SHORT
    pnl: float = 0.0
    pnl_pct: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    exit_reason: str = "OPEN"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'symbol': self.symbol,
            'entry_date': self.entry_date.isoformat(),
            'exit_date': self.exit_date.isoformat() if self.exit_date else None,
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'position_size': self.position_size,
            'side': self.side,
            'pnl': self.pnl,
            'pnl_pct': self.pnl_pct,
            'commission': self.commission,
            'slippage': self.slippage,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'exit_reason': self.exit_reason
        }


@dataclass
class PortfolioState:
    """Portfolio state at a given point in time"""
    date: datetime
    total_value: float
    cash: float
    positions: Dict[str, float] = field(default_factory=dict)
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    total_commission: float = 0.0
    total_slippage: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'date': self.date.isoformat(),
            'total_value': self.total_value,
            'cash': self.cash,
            'positions': self.positions,
            'unrealized_pnl': self.unrealized_pnl,
            'realized_pnl': self.realized_pnl,
            'total_commission': self.total_commission,
            'total_slippage': self.total_slippage
        }


@dataclass
class ValidationResult:
    """Result of strategy validation"""
    # Strategy information
    strategy_id: str
    strategy_name: str
    validation_period: Tuple[datetime, datetime]
    
    # Performance metrics
    total_return: float
    annualized_return: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    calmar_ratio: float
    
    # Risk metrics
    volatility: float
    var_95: float  # Value at Risk 95%
    cvar_95: float  # Conditional Value at Risk 95%
    beta: float
    alpha: float
    
    # Trading metrics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    
    # Portfolio metrics
    final_value: float
    peak_value: float
    final_positions: Dict[str, float]
    
    # Detailed data
    trades: List[Trade] = field(default_factory=list)
    portfolio_history: List[PortfolioState] = field(default_factory=list)
    benchmark_returns: List[float] = field(default_factory=list)
    
    # Validation metadata
    validation_date: datetime = field(default_factory=datetime.now)
    config: ValidationConfig = field(default_factory=ValidationConfig)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'strategy_id': self.strategy_id,
            'strategy_name': self.strategy_name,
            'validation_period': [self.validation_period[0].isoformat(), self.validation_period[1].isoformat()],
            'total_return': self.total_return,
            'annualized_return': self.annualized_return,
            'sharpe_ratio': self.sharpe_ratio,
            'sortino_ratio': self.sortino_ratio,
            'max_drawdown': self.max_drawdown,
            'calmar_ratio': self.calmar_ratio,
            'volatility': self.volatility,
            'var_95': self.var_95,
            'cvar_95': self.cvar_95,
            'beta': self.beta,
            'alpha': self.alpha,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.win_rate,
            'avg_win': self.avg_win,
            'avg_loss': self.avg_loss,
            'profit_factor': self.profit_factor,
            'final_value': self.final_value,
            'peak_value': self.peak_value,
            'final_positions': self.final_positions,
            'validation_date': self.validation_date.isoformat(),
            'config': self.config.to_dict()
        }


class StrategyValidator(ABC):
    """Base class for strategy validation"""
    
    def __init__(self, config: ValidationConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self._validate_config()
    
    @abstractmethod
    def validate_strategy(self, strategy: StrategyDefinition, market_data: Dict[str, pd.DataFrame]) -> ValidationResult:
        """Validate a trading strategy"""
        pass
    
    def _validate_config(self):
        """Validate validation configuration"""
        if self.config.start_date >= self.config.end_date:
            raise StrategyError("Start date must be before end date")
        
        if self.config.initial_capital <= 0:
            raise StrategyError("Initial capital must be positive")
        
        if not (0 <= self.config.commission_rate <= 1):
            raise StrategyError("Commission rate must be between 0 and 1")
        
        if not (0 <= self.config.slippage_rate <= 1):
            raise StrategyError("Slippage rate must be between 0 and 1")
        
        if not (0 <= self.config.max_position_size <= 1):
            raise StrategyError("Max position size must be between 0 and 1")
        
        if not (0 <= self.config.max_drawdown <= 1):
            raise StrategyError("Max drawdown must be between 0 and 1")
    
    def _calculate_returns(self, prices: pd.Series) -> pd.Series:
        """Calculate returns from price series"""
        return prices.pct_change().dropna()
    
    def _calculate_sharpe_ratio(self, returns: pd.Series, risk_free_rate: float = None) -> float:
        """Calculate Sharpe ratio"""
        if risk_free_rate is None:
            risk_free_rate = self.config.risk_free_rate
        
        if len(returns) == 0:
            return 0.0
        
        excess_returns = returns - risk_free_rate / 252  # Daily risk-free rate
        if excess_returns.std() == 0:
            return 0.0
        
        return excess_returns.mean() / excess_returns.std() * np.sqrt(252)
    
    def _calculate_sortino_ratio(self, returns: pd.Series, risk_free_rate: float = None) -> float:
        """Calculate Sortino ratio"""
        if risk_free_rate is None:
            risk_free_rate = self.config.risk_free_rate
        
        if len(returns) == 0:
            return 0.0
        
        excess_returns = returns - risk_free_rate / 252
        downside_returns = excess_returns[excess_returns < 0]
        
        if len(downside_returns) == 0 or downside_returns.std() == 0:
            return 0.0
        
        return excess_returns.mean() / downside_returns.std() * np.sqrt(252)
    
    def _calculate_max_drawdown(self, portfolio_values: pd.Series) -> float:
        """Calculate maximum drawdown"""
        if len(portfolio_values) == 0:
            return 0.0
        
        peak = portfolio_values.expanding().max()
        drawdown = (portfolio_values - peak) / peak
        return abs(drawdown.min())
    
    def _calculate_var_cvar(self, returns: pd.Series, confidence_level: float = 0.95) -> Tuple[float, float]:
        """Calculate Value at Risk and Conditional Value at Risk"""
        if len(returns) == 0:
            return 0.0, 0.0
        
        var = np.percentile(returns, (1 - confidence_level) * 100)
        cvar = returns[returns <= var].mean()
        
        return var, cvar
    
    def _calculate_beta_alpha(self, strategy_returns: pd.Series, benchmark_returns: pd.Series) -> Tuple[float, float]:
        """Calculate beta and alpha"""
        if len(strategy_returns) == 0 or len(benchmark_returns) == 0:
            return 0.0, 0.0
        
        # Align returns
        aligned_returns = pd.concat([strategy_returns, benchmark_returns], axis=1).dropna()
        if len(aligned_returns) == 0:
            return 0.0, 0.0
        
        strategy_ret = aligned_returns.iloc[:, 0]
        benchmark_ret = aligned_returns.iloc[:, 1]
        
        # Calculate beta
        covariance = np.cov(strategy_ret, benchmark_ret)[0, 1]
        benchmark_variance = np.var(benchmark_ret)
        
        if benchmark_variance == 0:
            beta = 0.0
        else:
            beta = covariance / benchmark_variance
        
        # Calculate alpha
        alpha = strategy_ret.mean() - beta * benchmark_ret.mean()
        
        return beta, alpha
    
    def _calculate_trade_metrics(self, trades: List[Trade]) -> Dict[str, float]:
        """Calculate trading metrics from trades"""
        if not trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'profit_factor': 0.0
            }
        
        total_trades = len(trades)
        winning_trades = len([t for t in trades if t.pnl > 0])
        losing_trades = len([t for t in trades if t.pnl < 0])
        
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        
        winning_pnls = [t.pnl for t in trades if t.pnl > 0]
        losing_pnls = [t.pnl for t in trades if t.pnl < 0]
        
        avg_win = np.mean(winning_pnls) if winning_pnls else 0.0
        avg_loss = abs(np.mean(losing_pnls)) if losing_pnls else 0.0
        
        total_wins = sum(winning_pnls)
        total_losses = abs(sum(losing_pnls))
        
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor
        }
    
    def get_validation_summary(self, result: ValidationResult) -> Dict[str, Any]:
        """Get summary of validation results"""
        return {
            'strategy_id': result.strategy_id,
            'strategy_name': result.strategy_name,
            'validation_period': result.validation_period,
            'total_return': result.total_return,
            'annualized_return': result.annualized_return,
            'sharpe_ratio': result.sharpe_ratio,
            'max_drawdown': result.max_drawdown,
            'total_trades': result.total_trades,
            'win_rate': result.win_rate,
            'profit_factor': result.profit_factor,
            'final_value': result.final_value
        }
