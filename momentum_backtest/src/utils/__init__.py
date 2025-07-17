"""
Performance analysis utilities
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class PerformanceAnalyzer:
    """
    Comprehensive performance analysis for trading strategies
    """
    
    def __init__(self, risk_free_rate: float = 0.02):
        """
        Initialize performance analyzer
        
        Args:
            risk_free_rate: Annual risk-free rate for Sharpe calculation
        """
        self.risk_free_rate = risk_free_rate
    
    def calculate_metrics(self, 
                         portfolio_values: pd.Series,
                         trade_history: pd.DataFrame = None,
                         benchmark: pd.Series = None) -> Dict[str, Any]:
        """
        Calculate comprehensive performance metrics
        
        Args:
            portfolio_values: Time series of portfolio values
            trade_history: DataFrame of trade records
            benchmark: Benchmark time series for comparison
        
        Returns:
            Dictionary of performance metrics
        """
        if len(portfolio_values) < 2:
            return self._empty_metrics()
        
        # Basic return metrics
        total_return = (portfolio_values.iloc[-1] / portfolio_values.iloc[0]) - 1
        daily_returns = portfolio_values.pct_change().dropna()
        
        # Risk metrics
        metrics = {
            'total_return': total_return,
            'annualized_return': self._annualized_return(daily_returns),
            'volatility': daily_returns.std() * np.sqrt(252),
            'sharpe_ratio': self._sharpe_ratio(daily_returns),
            'max_drawdown': self._max_drawdown(portfolio_values),
            'calmar_ratio': self._calmar_ratio(daily_returns, portfolio_values),
            'sortino_ratio': self._sortino_ratio(daily_returns),
            'skewness': daily_returns.skew(),
            'kurtosis': daily_returns.kurtosis(),
            'var_95': daily_returns.quantile(0.05),
            'cvar_95': daily_returns[daily_returns <= daily_returns.quantile(0.05)].mean()
        }
        
        # Trade analysis if available
        if trade_history is not None and not trade_history.empty:
            metrics.update(self._trade_analysis(trade_history))
        
        # Benchmark comparison if available
        if benchmark is not None:
            metrics.update(self._benchmark_analysis(daily_returns, benchmark))
        
        return metrics
    
    def _annualized_return(self, daily_returns: pd.Series) -> float:
        """Calculate annualized return"""
        if len(daily_returns) == 0:
            return 0.0
        return (1 + daily_returns.mean()) ** 252 - 1
    
    def _sharpe_ratio(self, daily_returns: pd.Series) -> float:
        """Calculate Sharpe ratio"""
        if len(daily_returns) == 0 or daily_returns.std() == 0:
            return 0.0
        excess_return = daily_returns.mean() - (self.risk_free_rate / 252)
        return excess_return / daily_returns.std() * np.sqrt(252)
    
    def _max_drawdown(self, portfolio_values: pd.Series) -> float:
        """Calculate maximum drawdown"""
        running_max = portfolio_values.cummax()
        drawdown = (portfolio_values / running_max) - 1
        return drawdown.min()
    
    def _calmar_ratio(self, daily_returns: pd.Series, portfolio_values: pd.Series) -> float:
        """Calculate Calmar ratio (annualized return / max drawdown)"""
        annual_return = self._annualized_return(daily_returns)
        max_dd = abs(self._max_drawdown(portfolio_values))
        return annual_return / max_dd if max_dd > 0 else 0.0
    
    def _sortino_ratio(self, daily_returns: pd.Series) -> float:
        """Calculate Sortino ratio (downside deviation)"""
        if len(daily_returns) == 0:
            return 0.0
        downside_returns = daily_returns[daily_returns < 0]
        if len(downside_returns) == 0:
            return float('inf')
        downside_std = downside_returns.std()
        if downside_std == 0:
            return 0.0
        excess_return = daily_returns.mean() - (self.risk_free_rate / 252)
        return excess_return / downside_std * np.sqrt(252)
    
    def _trade_analysis(self, trade_history: pd.DataFrame) -> Dict[str, Any]:
        """Analyze individual trades"""
        if 'pnl' not in trade_history.columns:
            return {}
        
        closed_trades = trade_history[trade_history['action'] == 'CLOSE']
        if closed_trades.empty:
            return {}
        
        pnl_series = closed_trades['pnl']
        winning_trades = pnl_series[pnl_series > 0]
        losing_trades = pnl_series[pnl_series < 0]
        
        return {
            'total_trades': len(closed_trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': len(winning_trades) / len(closed_trades) if len(closed_trades) > 0 else 0,
            'avg_win': winning_trades.mean() if len(winning_trades) > 0 else 0,
            'avg_loss': losing_trades.mean() if len(losing_trades) > 0 else 0,
            'largest_win': winning_trades.max() if len(winning_trades) > 0 else 0,
            'largest_loss': losing_trades.min() if len(losing_trades) > 0 else 0,
            'profit_factor': abs(winning_trades.sum() / losing_trades.sum()) if len(losing_trades) > 0 and losing_trades.sum() != 0 else float('inf')
        }
    
    def _benchmark_analysis(self, strategy_returns: pd.Series, benchmark: pd.Series) -> Dict[str, Any]:
        """Compare strategy to benchmark"""
        # Align dates
        aligned_data = pd.concat([strategy_returns, benchmark], axis=1, join='inner')
        aligned_data.columns = ['strategy', 'benchmark']
        
        if len(aligned_data) < 2:
            return {}
        
        # Calculate metrics
        excess_returns = aligned_data['strategy'] - aligned_data['benchmark']
        
        return {
            'beta': self._calculate_beta(aligned_data['strategy'], aligned_data['benchmark']),
            'alpha': excess_returns.mean() * 252,
            'correlation': aligned_data['strategy'].corr(aligned_data['benchmark']),
            'tracking_error': excess_returns.std() * np.sqrt(252),
            'information_ratio': excess_returns.mean() / excess_returns.std() * np.sqrt(252) if excess_returns.std() > 0 else 0
        }
    
    def _calculate_beta(self, strategy_returns: pd.Series, benchmark_returns: pd.Series) -> float:
        """Calculate beta relative to benchmark"""
        covariance = np.cov(strategy_returns, benchmark_returns)[0][1]
        variance = np.var(benchmark_returns)
        return covariance / variance if variance > 0 else 0.0
    
    def _empty_metrics(self) -> Dict[str, Any]:
        """Return empty metrics dict for edge cases"""
        return {
            'total_return': 0.0,
            'annualized_return': 0.0,
            'volatility': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'calmar_ratio': 0.0,
            'sortino_ratio': 0.0,
            'skewness': 0.0,
            'kurtosis': 0.0
        }
