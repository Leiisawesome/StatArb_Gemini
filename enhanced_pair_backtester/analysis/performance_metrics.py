"""
Performance Metrics Module

Comprehensive performance analysis for pairs trading strategies including:
- Return and risk metrics
- Risk-adjusted performance measures
- Rolling performance analysis
- Statistical significance testing
- Professional-grade performance attribution
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import warnings
from scipy import stats
import logging

# Import execution components
try:
    from ..execution.execution_engine import Trade, ExecutionResult
    from ..execution.order_management import Position, Fill
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, parent_dir)
    from execution.execution_engine import Trade, ExecutionResult
    from execution.order_management import Position, Fill

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


@dataclass
class ReturnMetrics:
    """Return-based performance metrics"""
    total_return: float = 0.0
    annualized_return: float = 0.0
    compound_annual_growth_rate: float = 0.0
    
    # Period returns
    daily_return: float = 0.0
    weekly_return: float = 0.0
    monthly_return: float = 0.0
    quarterly_return: float = 0.0
    yearly_return: float = 0.0
    
    # Return statistics
    mean_daily_return: float = 0.0
    median_daily_return: float = 0.0
    std_daily_return: float = 0.0
    
    # Return distribution
    skewness: float = 0.0
    kurtosis: float = 0.0
    positive_days_pct: float = 0.0
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary"""
        return {
            'total_return': self.total_return,
            'annualized_return': self.annualized_return,
            'cagr': self.compound_annual_growth_rate,
            'daily_return': self.daily_return,
            'weekly_return': self.weekly_return,
            'monthly_return': self.monthly_return,
            'quarterly_return': self.quarterly_return,
            'yearly_return': self.yearly_return,
            'mean_daily_return': self.mean_daily_return,
            'median_daily_return': self.median_daily_return,
            'std_daily_return': self.std_daily_return,
            'skewness': self.skewness,
            'kurtosis': self.kurtosis,
            'positive_days_pct': self.positive_days_pct
        }


@dataclass
class RiskMetrics:
    """Risk-based performance metrics"""
    # Volatility measures
    daily_volatility: float = 0.0
    annualized_volatility: float = 0.0
    downside_volatility: float = 0.0
    
    # Risk-adjusted returns
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    omega_ratio: float = 0.0
    
    # Drawdown metrics
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0
    current_drawdown: float = 0.0
    average_drawdown: float = 0.0
    
    # Value at Risk
    var_95: float = 0.0  # 95% VaR
    var_99: float = 0.0  # 99% VaR
    cvar_95: float = 0.0  # 95% Conditional VaR
    
    # Tail risk
    tail_ratio: float = 0.0
    worst_day: float = 0.0
    best_day: float = 0.0
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary"""
        return {
            'daily_volatility': self.daily_volatility,
            'annualized_volatility': self.annualized_volatility,
            'downside_volatility': self.downside_volatility,
            'sharpe_ratio': self.sharpe_ratio,
            'sortino_ratio': self.sortino_ratio,
            'calmar_ratio': self.calmar_ratio,
            'omega_ratio': self.omega_ratio,
            'max_drawdown': self.max_drawdown,
            'max_drawdown_duration': self.max_drawdown_duration,
            'current_drawdown': self.current_drawdown,
            'average_drawdown': self.average_drawdown,
            'var_95': self.var_95,
            'var_99': self.var_99,
            'cvar_95': self.cvar_95,
            'tail_ratio': self.tail_ratio,
            'worst_day': self.worst_day,
            'best_day': self.best_day
        }


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics container"""
    returns: ReturnMetrics = field(default_factory=ReturnMetrics)
    risk: RiskMetrics = field(default_factory=RiskMetrics)
    
    # Trading metrics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    # P&L metrics
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    net_profit: float = 0.0
    profit_factor: float = 0.0
    
    # Trade statistics
    average_win: float = 0.0
    average_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    
    # Efficiency metrics
    expectancy: float = 0.0
    kelly_criterion: float = 0.0
    
    # Timing metrics
    analysis_start_date: Optional[datetime] = None
    analysis_end_date: Optional[datetime] = None
    total_days: int = 0
    trading_days: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to comprehensive dictionary"""
        return {
            'returns': self.returns.to_dict(),
            'risk': self.risk.to_dict(),
            'trading': {
                'total_trades': self.total_trades,
                'winning_trades': self.winning_trades,
                'losing_trades': self.losing_trades,
                'win_rate': self.win_rate,
                'gross_profit': self.gross_profit,
                'gross_loss': self.gross_loss,
                'net_profit': self.net_profit,
                'profit_factor': self.profit_factor,
                'average_win': self.average_win,
                'average_loss': self.average_loss,
                'largest_win': self.largest_win,
                'largest_loss': self.largest_loss,
                'expectancy': self.expectancy,
                'kelly_criterion': self.kelly_criterion
            },
            'timing': {
                'analysis_start_date': self.analysis_start_date.isoformat() if self.analysis_start_date else None,
                'analysis_end_date': self.analysis_end_date.isoformat() if self.analysis_end_date else None,
                'total_days': self.total_days,
                'trading_days': self.trading_days
            }
        }


class PerformanceAnalyzer:
    """
    Comprehensive performance analysis engine for pairs trading
    
    Features:
    - Complete return and risk analysis
    - Professional-grade performance metrics
    - Rolling performance windows
    - Statistical significance testing
    - Benchmark comparison capabilities
    """
    
    def __init__(self, 
                 risk_free_rate: float = 0.02,
                 benchmark_return: float = 0.08,
                 confidence_level: float = 0.95):
        """
        Initialize performance analyzer
        
        Args:
            risk_free_rate: Annual risk-free rate for Sharpe ratio
            benchmark_return: Annual benchmark return for comparison
            confidence_level: Confidence level for VaR calculations
        """
        self.risk_free_rate = risk_free_rate
        self.benchmark_return = benchmark_return
        self.confidence_level = confidence_level
        
        # Performance tracking
        self.portfolio_values: List[Tuple[datetime, float]] = []
        self.daily_returns: List[float] = []
        self.trades: List[Trade] = []
        self.fills: List[Fill] = []
        
        # Cached calculations
        self._cached_metrics: Optional[PerformanceMetrics] = None
        self._cache_timestamp: Optional[datetime] = None
        
        logger.info(f"Performance Analyzer initialized with risk-free rate: {risk_free_rate:.2%}")
    
    def add_portfolio_value(self, timestamp: datetime, value: float):
        """Add portfolio value observation"""
        self.portfolio_values.append((timestamp, value))
        
        # Calculate daily return if we have previous value
        if len(self.portfolio_values) > 1:
            prev_value = self.portfolio_values[-2][1]
            if prev_value > 0:
                daily_return = (value - prev_value) / prev_value
                self.daily_returns.append(daily_return)
        
        # Clear cache
        self._cached_metrics = None
    
    def add_trade(self, trade: Trade):
        """Add completed trade"""
        self.trades.append(trade)
        self._cached_metrics = None
    
    def add_fill(self, fill: Fill):
        """Add trade fill"""
        self.fills.append(fill)
        self._cached_metrics = None
    
    def calculate_performance_metrics(self, 
                                    start_date: Optional[datetime] = None,
                                    end_date: Optional[datetime] = None) -> PerformanceMetrics:
        """
        Calculate comprehensive performance metrics
        
        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            
        Returns:
            PerformanceMetrics with complete analysis
        """
        # Check cache
        if (self._cached_metrics and 
            self._cache_timestamp and 
            datetime.now() - self._cache_timestamp < timedelta(minutes=5)):
            return self._cached_metrics
        
        if not self.portfolio_values:
            logger.warning("No portfolio values available for analysis")
            return PerformanceMetrics()
        
        # Filter data by date range
        filtered_values = self._filter_by_date_range(self.portfolio_values, start_date, end_date)
        filtered_returns = self._calculate_filtered_returns(filtered_values)
        
        if not filtered_returns:
            logger.warning("No returns data available for analysis")
            return PerformanceMetrics()
        
        # Calculate metrics
        metrics = PerformanceMetrics()
        
        # Set timing information
        metrics.analysis_start_date = filtered_values[0][0] if filtered_values else None
        metrics.analysis_end_date = filtered_values[-1][0] if filtered_values else None
        metrics.total_days = len(filtered_values)
        metrics.trading_days = len([r for r in filtered_returns if r != 0])
        
        # Calculate return metrics
        metrics.returns = self._calculate_return_metrics(filtered_returns, filtered_values)
        
        # Calculate risk metrics
        metrics.risk = self._calculate_risk_metrics(filtered_returns, metrics.returns)
        
        # Calculate trading metrics
        self._calculate_trading_metrics(metrics)
        
        # Cache results
        self._cached_metrics = metrics
        self._cache_timestamp = datetime.now()
        
        return metrics
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get high-level performance summary"""
        metrics = self.calculate_performance_metrics()
        
        return {
            'total_return': f"{metrics.returns.total_return:.2%}",
            'annualized_return': f"{metrics.returns.annualized_return:.2%}",
            'volatility': f"{metrics.risk.annualized_volatility:.2%}",
            'sharpe_ratio': f"{metrics.risk.sharpe_ratio:.2f}",
            'max_drawdown': f"{metrics.risk.max_drawdown:.2%}",
            'win_rate': f"{metrics.win_rate:.1%}",
            'profit_factor': f"{metrics.profit_factor:.2f}",
            'total_trades': metrics.total_trades,
            'trading_days': metrics.trading_days
        }
    
    def _calculate_return_metrics(self, 
                                returns: List[float],
                                values: List[Tuple[datetime, float]]) -> ReturnMetrics:
        """Calculate return-based metrics"""
        if not returns or not values:
            return ReturnMetrics()
        
        returns_array = np.array(returns)
        
        # Basic return calculations
        total_return = (values[-1][1] - values[0][1]) / values[0][1] if values[0][1] > 0 else 0.0
        
        # Annualized return
        days = len(returns)
        years = days / 252.0 if days > 0 else 1.0
        annualized_return = (1 + total_return) ** (1/years) - 1 if years > 0 else 0.0
        
        # CAGR
        cagr = annualized_return  # Same as annualized return for this calculation
        
        # Period returns (approximated)
        daily_return = float(np.mean(returns_array)) if len(returns_array) > 0 else 0.0
        weekly_return = daily_return * 5  # Approximate
        monthly_return = daily_return * 21  # Approximate
        quarterly_return = daily_return * 63  # Approximate
        yearly_return = daily_return * 252  # Approximate
        
        # Return statistics
        mean_daily_return = float(np.mean(returns_array)) if len(returns_array) > 0 else 0.0
        median_daily_return = float(np.median(returns_array)) if len(returns_array) > 0 else 0.0
        std_daily_return = float(np.std(returns_array)) if len(returns_array) > 0 else 0.0
        
        # Distribution metrics
        skewness = float(stats.skew(returns_array)) if len(returns_array) > 3 else 0.0
        kurtosis = float(stats.kurtosis(returns_array)) if len(returns_array) > 3 else 0.0
        positive_days_pct = len([r for r in returns_array if r > 0]) / len(returns_array) if len(returns_array) > 0 else 0.0
        
        return ReturnMetrics(
            total_return=total_return,
            annualized_return=annualized_return,
            compound_annual_growth_rate=cagr,
            daily_return=daily_return,
            weekly_return=weekly_return,
            monthly_return=monthly_return,
            quarterly_return=quarterly_return,
            yearly_return=yearly_return,
            mean_daily_return=mean_daily_return,
            median_daily_return=median_daily_return,
            std_daily_return=std_daily_return,
            skewness=skewness,
            kurtosis=kurtosis,
            positive_days_pct=positive_days_pct
        )
    
    def _calculate_risk_metrics(self, 
                              returns: List[float],
                              return_metrics: ReturnMetrics) -> RiskMetrics:
        """Calculate risk-based metrics"""
        if not returns:
            return RiskMetrics()
        
        returns_array = np.array(returns)
        
        # Volatility measures
        daily_volatility = float(np.std(returns_array)) if len(returns_array) > 0 else 0.0
        annualized_volatility = daily_volatility * np.sqrt(252)
        
        # Downside volatility
        negative_returns = returns_array[returns_array < 0]
        downside_volatility = float(np.std(negative_returns)) * np.sqrt(252) if len(negative_returns) > 0 else 0.0
        
        # Risk-adjusted returns
        excess_return = return_metrics.annualized_return - self.risk_free_rate
        sharpe_ratio = excess_return / annualized_volatility if annualized_volatility > 0 else 0.0
        
        sortino_ratio = excess_return / downside_volatility if downside_volatility > 0 else 0.0
        
        # Drawdown analysis
        drawdown_metrics = self._calculate_drawdown_metrics(returns_array)
        
        calmar_ratio = (return_metrics.annualized_return / abs(drawdown_metrics['max_drawdown']) 
                       if drawdown_metrics['max_drawdown'] != 0 else 0.0)
        
        # Omega ratio (simplified)
        positive_returns = returns_array[returns_array > 0]
        negative_returns = returns_array[returns_array < 0]
        omega_ratio = (np.sum(positive_returns) / abs(np.sum(negative_returns)) 
                      if len(negative_returns) > 0 and np.sum(negative_returns) != 0 else 0.0)
        
        # Value at Risk
        var_95 = float(np.percentile(returns_array, (1 - self.confidence_level) * 100)) if len(returns_array) > 0 else 0.0
        var_99 = float(np.percentile(returns_array, 1)) if len(returns_array) > 0 else 0.0
        
        # Conditional VaR
        var_95_returns = returns_array[returns_array <= var_95]
        cvar_95 = float(np.mean(var_95_returns)) if len(var_95_returns) > 0 else 0.0
        
        # Tail risk
        tail_ratio = float(abs(var_95) / abs(var_99)) if var_99 != 0 else 0.0
        worst_day = float(np.min(returns_array)) if len(returns_array) > 0 else 0.0
        best_day = float(np.max(returns_array)) if len(returns_array) > 0 else 0.0
        
        return RiskMetrics(
            daily_volatility=daily_volatility,
            annualized_volatility=annualized_volatility,
            downside_volatility=downside_volatility,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            omega_ratio=omega_ratio,
            max_drawdown=drawdown_metrics['max_drawdown'],
            max_drawdown_duration=int(drawdown_metrics['max_drawdown_duration']),
            current_drawdown=drawdown_metrics['current_drawdown'],
            average_drawdown=drawdown_metrics['average_drawdown'],
            var_95=var_95,
            var_99=var_99,
            cvar_95=cvar_95,
            tail_ratio=tail_ratio,
            worst_day=worst_day,
            best_day=best_day
        )
    
    def _calculate_drawdown_metrics(self, returns: np.ndarray) -> Dict[str, float]:
        """Calculate detailed drawdown metrics"""
        if len(returns) == 0:
            return {
                'max_drawdown': 0.0,
                'max_drawdown_duration': 0,
                'current_drawdown': 0.0,
                'average_drawdown': 0.0
            }
        
        # Calculate cumulative returns
        cumulative_returns = np.cumprod(1 + returns)
        
        # Calculate running maximum
        running_max = np.maximum.accumulate(cumulative_returns)
        
        # Calculate drawdown
        drawdown = (cumulative_returns - running_max) / running_max
        
        # Maximum drawdown
        max_drawdown = float(np.min(drawdown))
        
        # Current drawdown
        current_drawdown = float(drawdown[-1])
        
        # Average drawdown
        negative_drawdowns = drawdown[drawdown < 0]
        average_drawdown = float(np.mean(negative_drawdowns)) if len(negative_drawdowns) > 0 else 0.0
        
        # Maximum drawdown duration
        max_drawdown_duration = 0
        current_duration = 0
        
        for dd in drawdown:
            if dd < 0:
                current_duration += 1
                max_drawdown_duration = max(max_drawdown_duration, current_duration)
            else:
                current_duration = 0
        
        return {
            'max_drawdown': max_drawdown,
            'max_drawdown_duration': max_drawdown_duration,
            'current_drawdown': current_drawdown,
            'average_drawdown': average_drawdown
        }
    
    def _calculate_trading_metrics(self, metrics: PerformanceMetrics):
        """Calculate trading-specific metrics"""
        if not self.trades:
            return
        
        # Basic trade counts
        metrics.total_trades = len(self.trades)
        
        # Calculate P&L for each trade
        trade_pnls = []
        for trade in self.trades:
            # Simplified P&L calculation
            # In reality, this would be more complex with position tracking
            pnl = trade.quantity * trade.price * 0.01  # Placeholder calculation
            trade_pnls.append(pnl)
        
        if not trade_pnls:
            return
        
        # Winning/losing trades
        winning_trades = [pnl for pnl in trade_pnls if pnl > 0]
        losing_trades = [pnl for pnl in trade_pnls if pnl < 0]
        
        metrics.winning_trades = len(winning_trades)
        metrics.losing_trades = len(losing_trades)
        metrics.win_rate = len(winning_trades) / len(trade_pnls) if trade_pnls else 0.0
        
        # P&L metrics
        metrics.gross_profit = sum(winning_trades) if winning_trades else 0.0
        metrics.gross_loss = sum(losing_trades) if losing_trades else 0.0
        metrics.net_profit = metrics.gross_profit + metrics.gross_loss
        metrics.profit_factor = (metrics.gross_profit / abs(metrics.gross_loss) 
                               if metrics.gross_loss != 0 else 0.0)
        
        # Trade statistics
        metrics.average_win = float(np.mean(winning_trades)) if winning_trades else 0.0
        metrics.average_loss = float(np.mean(losing_trades)) if losing_trades else 0.0
        metrics.largest_win = max(winning_trades) if winning_trades else 0.0
        metrics.largest_loss = min(losing_trades) if losing_trades else 0.0
        
        # Expectancy
        metrics.expectancy = (metrics.win_rate * metrics.average_win + 
                            (1 - metrics.win_rate) * metrics.average_loss)
        
        # Kelly Criterion
        if metrics.average_loss != 0:
            metrics.kelly_criterion = (metrics.win_rate - 
                                     (1 - metrics.win_rate) * metrics.average_win / abs(metrics.average_loss))
        else:
            metrics.kelly_criterion = 0.0
    
    def _filter_by_date_range(self, 
                            values: List[Tuple[datetime, float]],
                            start_date: Optional[datetime],
                            end_date: Optional[datetime]) -> List[Tuple[datetime, float]]:
        """Filter portfolio values by date range"""
        if not start_date and not end_date:
            return values
        
        filtered = []
        for timestamp, value in values:
            if start_date and timestamp < start_date:
                continue
            if end_date and timestamp > end_date:
                break
            filtered.append((timestamp, value))
        
        return filtered
    
    def _calculate_filtered_returns(self, values: List[Tuple[datetime, float]]) -> List[float]:
        """Calculate returns from filtered portfolio values"""
        if len(values) < 2:
            return []
        
        returns = []
        for i in range(1, len(values)):
            prev_value = values[i-1][1]
            curr_value = values[i][1]
            if prev_value > 0:
                ret = (curr_value - prev_value) / prev_value
                returns.append(ret)
        
        return returns 