"""
Performance metrics and analysis for parameter adaptation.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Tuple
import logging


@dataclass
class PerformanceSnapshot:
    """Snapshot of performance metrics at a point in time."""
    
    timestamp: datetime
    strategy_id: str
    total_trades: int
    
    # Return metrics
    total_return: float
    daily_returns: List[float]
    sharpe_ratio: float
    calmar_ratio: float
    
    # Risk metrics  
    max_drawdown: float
    volatility: float
    var_95: float  # Value at Risk 95%
    
    # Trade metrics
    win_rate: float
    profit_factor: float
    average_win: float
    average_loss: float
    largest_win: float
    largest_loss: float
    
    # Market condition metrics
    market_correlation: float
    beta: float
    
    def __str__(self) -> str:
        return (f"PerformanceSnapshot(strategy={self.strategy_id}, "
                f"sharpe={self.sharpe_ratio:.2f}, win_rate={self.win_rate:.2f}, "
                f"max_dd={self.max_drawdown:.2f})")


class AdaptationMetrics:
    """Tracks and analyzes performance metrics for parameter adaptation decisions."""
    
    def __init__(self, strategy_id: str):
        self.strategy_id = strategy_id
        self.logger = logging.getLogger(__name__)
        
        # Performance tracking
        self.performance_history: List[PerformanceSnapshot] = []
        self.trade_history: List[Dict[str, Any]] = []
        self.daily_returns: List[float] = []
        
        # Market data tracking
        self.market_returns: List[float] = []
        self.volatility_history: List[float] = []
        
        # Adaptation tracking
        self.adaptation_events: List[Dict[str, Any]] = []
        
    def add_trade(self, trade_data: Dict[str, Any]) -> None:
        """Add trade data for performance tracking."""
        net_pnl = trade_data.get('pnl', 0) - trade_data.get('commission', 0)
        
        self.trade_history.append({
            'timestamp': trade_data.get('timestamp', datetime.now()),
            'symbol': trade_data.get('symbol'),
            'side': trade_data.get('side'),  # 'buy' or 'sell'
            'quantity': trade_data.get('quantity', 0),
            'price': trade_data.get('price', 0),
            'pnl': trade_data.get('pnl', 0),
            'commission': trade_data.get('commission', 0),
            'net_pnl': net_pnl
        })
        
        # Update daily returns if this completes a position
        if trade_data.get('position_closed', False):
            daily_return = net_pnl / trade_data.get('position_value', 1)
            self.daily_returns.append(daily_return)
    
    def add_market_data(self, market_return: float, volatility: float) -> None:
        """Add market data for benchmark comparison."""
        self.market_returns.append(market_return)
        self.volatility_history.append(volatility)
    
    def calculate_performance_snapshot(self) -> PerformanceSnapshot:
        """Calculate current performance metrics snapshot."""
        if not self.trade_history:
            return self._empty_snapshot()
        
        # Calculate return metrics
        total_return = sum(trade['net_pnl'] for trade in self.trade_history)
        returns_array = np.array(self.daily_returns) if self.daily_returns else np.array([0])
        
        sharpe_ratio = self._calculate_sharpe_ratio(returns_array)
        max_drawdown = self._calculate_max_drawdown(returns_array)
        calmar_ratio = self._calculate_calmar_ratio(returns_array, max_drawdown)
        
        # Calculate trade metrics
        win_rate = self._calculate_win_rate()
        profit_factor = self._calculate_profit_factor()
        avg_win, avg_loss = self._calculate_average_win_loss()
        largest_win, largest_loss = self._calculate_largest_win_loss()
        
        # Calculate risk metrics
        volatility = np.std(returns_array) * np.sqrt(252) if len(returns_array) > 1 else 0
        var_95 = np.percentile(returns_array, 5) if len(returns_array) > 0 else 0
        
        # Calculate market metrics
        market_correlation = self._calculate_market_correlation()
        beta = self._calculate_beta()
        
        return PerformanceSnapshot(
            timestamp=datetime.now(),
            strategy_id=self.strategy_id,
            total_trades=len(self.trade_history),
            total_return=total_return,
            daily_returns=self.daily_returns.copy(),
            sharpe_ratio=sharpe_ratio,
            calmar_ratio=calmar_ratio,
            max_drawdown=max_drawdown,
            volatility=volatility,
            var_95=var_95,
            win_rate=win_rate,
            profit_factor=profit_factor,
            average_win=avg_win,
            average_loss=avg_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            market_correlation=market_correlation,
            beta=beta
        )
    
    def compare_performance(self, before: PerformanceSnapshot, after: PerformanceSnapshot) -> Dict[str, float]:
        """Compare two performance snapshots."""
        return {
            'sharpe_change': after.sharpe_ratio - before.sharpe_ratio,
            'return_change': after.total_return - before.total_return,
            'drawdown_change': after.max_drawdown - before.max_drawdown,
            'win_rate_change': after.win_rate - before.win_rate,
            'volatility_change': after.volatility - before.volatility,
            'profit_factor_change': after.profit_factor - before.profit_factor
        }
    
    def detect_performance_degradation(self, 
                                     current: PerformanceSnapshot,
                                     baseline: PerformanceSnapshot,
                                     threshold: float = -0.20) -> bool:
        """Detect if performance has degraded significantly."""
        comparison = self.compare_performance(baseline, current)
        
        # Check multiple metrics for degradation
        degradation_indicators = [
            comparison['sharpe_change'] < threshold,
            comparison['win_rate_change'] < -0.10,  # 10% win rate drop
            comparison['drawdown_change'] > 0.05,   # 5% additional drawdown
            comparison['profit_factor_change'] < -0.30  # 30% profit factor drop
        ]
        
        # Trigger if multiple indicators show degradation
        return sum(degradation_indicators) >= 2
    
    def get_adaptation_signal_strength(self) -> float:
        """Calculate signal strength for parameter adaptation (0-1)."""
        if len(self.performance_history) < 2:
            return 0.0
        
        current = self.performance_history[-1]
        baseline = self.performance_history[-2] if len(self.performance_history) >= 2 else current
        
        # Calculate weighted signal strength based on multiple factors
        factors = {
            'sharpe_degradation': max(0, baseline.sharpe_ratio - current.sharpe_ratio) / 2.0,
            'drawdown_increase': max(0, current.max_drawdown - baseline.max_drawdown) * 2.0,
            'win_rate_decline': max(0, baseline.win_rate - current.win_rate) * 2.0,
            'volatility_increase': max(0, current.volatility - baseline.volatility) / baseline.volatility if baseline.volatility > 0 else 0
        }
        
        # Weighted average of factors
        weights = {'sharpe_degradation': 0.3, 'drawdown_increase': 0.3, 'win_rate_decline': 0.25, 'volatility_increase': 0.15}
        signal_strength = sum(factors[key] * weights[key] for key in factors)
        
        return min(1.0, signal_strength)  # Cap at 1.0
    
    def _empty_snapshot(self) -> PerformanceSnapshot:
        """Return empty performance snapshot."""
        return PerformanceSnapshot(
            timestamp=datetime.now(),
            strategy_id=self.strategy_id,
            total_trades=0,
            total_return=0.0,
            daily_returns=[],
            sharpe_ratio=0.0,
            calmar_ratio=0.0,
            max_drawdown=0.0,
            volatility=0.0,
            var_95=0.0,
            win_rate=0.0,
            profit_factor=0.0,
            average_win=0.0,
            average_loss=0.0,
            largest_win=0.0,
            largest_loss=0.0,
            market_correlation=0.0,
            beta=0.0
        )
    
    def _calculate_sharpe_ratio(self, returns: np.ndarray) -> float:
        """Calculate annualized Sharpe ratio."""
        if len(returns) < 2 or np.std(returns) == 0:
            return 0.0
        return (np.mean(returns) / np.std(returns)) * np.sqrt(252)
    
    def _calculate_max_drawdown(self, returns: np.ndarray) -> float:
        """Calculate maximum drawdown."""
        if len(returns) == 0:
            return 0.0
        
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = (cumulative - running_max) / running_max
        return abs(np.min(drawdowns))
    
    def _calculate_calmar_ratio(self, returns: np.ndarray, max_drawdown: float) -> float:
        """Calculate Calmar ratio (annual return / max drawdown)."""
        if max_drawdown == 0 or len(returns) == 0:
            return 0.0
        annual_return = np.mean(returns) * 252
        return annual_return / max_drawdown
    
    def _calculate_win_rate(self) -> float:
        """Calculate win rate from trade history."""
        if not self.trade_history:
            return 0.0
        
        winning_trades = sum(1 for trade in self.trade_history if trade['net_pnl'] > 0)
        return winning_trades / len(self.trade_history)
    
    def _calculate_profit_factor(self) -> float:
        """Calculate profit factor (gross profit / gross loss)."""
        if not self.trade_history:
            return 0.0
        
        gross_profit = sum(trade['net_pnl'] for trade in self.trade_history if trade['net_pnl'] > 0)
        gross_loss = abs(sum(trade['net_pnl'] for trade in self.trade_history if trade['net_pnl'] < 0))
        
        return gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    def _calculate_average_win_loss(self) -> Tuple[float, float]:
        """Calculate average win and loss amounts."""
        if not self.trade_history:
            return 0.0, 0.0
        
        wins = [trade['net_pnl'] for trade in self.trade_history if trade['net_pnl'] > 0]
        losses = [trade['net_pnl'] for trade in self.trade_history if trade['net_pnl'] < 0]
        
        avg_win = np.mean(wins) if wins else 0.0
        avg_loss = np.mean(losses) if losses else 0.0
        
        return avg_win, avg_loss
    
    def _calculate_largest_win_loss(self) -> Tuple[float, float]:
        """Calculate largest win and loss amounts."""
        if not self.trade_history:
            return 0.0, 0.0
        
        pnls = [trade['net_pnl'] for trade in self.trade_history]
        largest_win = max(pnls) if pnls else 0.0
        largest_loss = min(pnls) if pnls else 0.0
        
        return largest_win, largest_loss
    
    def _calculate_market_correlation(self) -> float:
        """Calculate correlation with market returns."""
        if len(self.daily_returns) < 2 or len(self.market_returns) < 2:
            return 0.0
        
        min_length = min(len(self.daily_returns), len(self.market_returns))
        strategy_returns = np.array(self.daily_returns[-min_length:])
        market_returns = np.array(self.market_returns[-min_length:])
        
        if np.std(strategy_returns) == 0 or np.std(market_returns) == 0:
            return 0.0
        
        correlation_matrix = np.corrcoef(strategy_returns, market_returns)
        return correlation_matrix[0, 1]
    
    def _calculate_beta(self) -> float:
        """Calculate beta relative to market."""
        if len(self.daily_returns) < 2 or len(self.market_returns) < 2:
            return 0.0
        
        min_length = min(len(self.daily_returns), len(self.market_returns))
        strategy_returns = np.array(self.daily_returns[-min_length:])
        market_returns = np.array(self.market_returns[-min_length:])
        
        if np.var(market_returns) == 0:
            return 0.0
        
        covariance = np.cov(strategy_returns, market_returns)[0, 1]
        market_variance = np.var(market_returns)
        
        return covariance / market_variance
