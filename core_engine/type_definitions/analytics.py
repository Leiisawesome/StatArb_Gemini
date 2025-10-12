"""
Core Engine Analytics Types

Lightweight analytics for standalone core_engine.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd
import numpy as np


@dataclass
class PerformanceMetrics:
    """Performance analytics metrics"""
    # Returns
    total_return: float = 0.0
    annualized_return: float = 0.0
    excess_return: float = 0.0  # vs benchmark
    
    # Risk metrics
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    var_95: float = 0.0  # 95% Value at Risk
    
    # Trade metrics
    total_trades: int = 0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    
    # Time-based
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    period_days: int = 0
    
    # Additional metrics
    calmar_ratio: float = 0.0  # Return / Max Drawdown
    recovery_factor: float = 0.0
    
    def calculate_from_returns(self, returns: pd.Series, benchmark_returns: Optional[pd.Series] = None):
        """Calculate metrics from return series"""
        if len(returns) == 0:
            return
        
        # Basic returns
        self.total_return = (1 + returns).prod() - 1
        self.period_days = len(returns)
        
        if self.period_days > 0:
            self.annualized_return = (1 + self.total_return) ** (252 / self.period_days) - 1
        
        # Risk metrics
        self.volatility = returns.std() * np.sqrt(252)
        
        if self.volatility > 0:
            self.sharpe_ratio = (self.annualized_return) / self.volatility
        
        # Sortino ratio (downside deviation)
        downside_returns = returns[returns < 0]
        if len(downside_returns) > 0:
            downside_std = downside_returns.std() * np.sqrt(252)
            if downside_std > 0:
                self.sortino_ratio = self.annualized_return / downside_std
        
        # Drawdown analysis
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        self.max_drawdown = drawdown.min()
        
        # VaR
        self.var_95 = returns.quantile(0.05)
        
        # Calmar ratio
        if self.max_drawdown < 0:
            self.calmar_ratio = self.annualized_return / abs(self.max_drawdown)
        
        # Excess return vs benchmark
        if benchmark_returns is not None and len(benchmark_returns) == len(returns):
            benchmark_total = (1 + benchmark_returns).prod() - 1
            self.excess_return = self.total_return - benchmark_total
        
        # Set dates
        if hasattr(returns.index, 'min') and hasattr(returns.index, 'max'):
            self.start_date = pd.to_datetime(returns.index.min())
            self.end_date = pd.to_datetime(returns.index.max())


class AnalyticsEngine:
    """Core analytics and performance measurement"""
    
    def __init__(self):
        self.portfolio_history: List[Dict[str, Any]] = []
        self.trade_history: List[Dict[str, Any]] = []
        self.benchmark_data: Optional[pd.Series] = None
    
    def add_portfolio_snapshot(self, timestamp: datetime, portfolio_value: float, 
                             positions: Dict[str, float], cash: float):
        """Add portfolio snapshot for tracking"""
        snapshot = {
            'timestamp': timestamp,
            'portfolio_value': portfolio_value,
            'positions': positions.copy(),
            'cash': cash,
            'total_positions': len(positions)
        }
        self.portfolio_history.append(snapshot)
    
    def add_trade(self, timestamp: datetime, symbol: str, side: str, 
                 quantity: float, price: float, commission: float):
        """Add trade record"""
        trade = {
            'timestamp': timestamp,
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'price': price,
            'commission': commission,
            'value': quantity * price
        }
        self.trade_history.append(trade)
    
    def calculate_performance(self, start_date: Optional[datetime] = None,
                            end_date: Optional[datetime] = None) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics"""
        metrics = PerformanceMetrics()
        
        if len(self.portfolio_history) < 2:
            return metrics
        
        # Filter data by date range
        history = self._filter_history_by_date(self.portfolio_history, start_date, end_date)
        
        if len(history) < 2:
            return metrics
        
        # Calculate returns
        values = [h['portfolio_value'] for h in history]
        timestamps = [h['timestamp'] for h in history]
        
        returns_series = pd.Series(values, index=timestamps).pct_change().dropna()
        
        # Calculate metrics
        metrics.calculate_from_returns(returns_series, self.benchmark_data)
        
        # Trade-specific metrics
        trades = self._filter_trades_by_date(self.trade_history, start_date, end_date)
        self._calculate_trade_metrics(metrics, trades)
        
        return metrics
    
    def get_portfolio_returns(self) -> pd.Series:
        """Get portfolio returns series"""
        if len(self.portfolio_history) < 2:
            return pd.Series()
        
        values = [h['portfolio_value'] for h in self.portfolio_history]
        timestamps = [h['timestamp'] for h in self.portfolio_history]
        
        return pd.Series(values, index=timestamps).pct_change().dropna()
    
    def get_position_analytics(self, symbol: str) -> Dict[str, Any]:
        """Get analytics for specific position"""
        position_trades = [t for t in self.trade_history if t['symbol'] == symbol]
        
        if not position_trades:
            return {}
        
        # Calculate position metrics
        total_volume = sum(abs(t['quantity']) for t in position_trades)
        total_commission = sum(t['commission'] for t in position_trades)
        
        buy_trades = [t for t in position_trades if t['side'].upper() == 'BUY']
        sell_trades = [t for t in position_trades if t['side'].upper() == 'SELL']
        
        return {
            'symbol': symbol,
            'total_trades': len(position_trades),
            'total_volume': total_volume,
            'total_commission': total_commission,
            'buy_trades': len(buy_trades),
            'sell_trades': len(sell_trades),
            'first_trade': min(t['timestamp'] for t in position_trades),
            'last_trade': max(t['timestamp'] for t in position_trades)
        }
    
    def set_benchmark(self, benchmark_returns: pd.Series):
        """Set benchmark for comparison"""
        self.benchmark_data = benchmark_returns
    
    def get_drawdown_analysis(self) -> Dict[str, Any]:
        """Get detailed drawdown analysis"""
        if len(self.portfolio_history) < 2:
            return {}
        
        values = [h['portfolio_value'] for h in self.portfolio_history]
        timestamps = [h['timestamp'] for h in self.portfolio_history]
        
        portfolio_series = pd.Series(values, index=timestamps)
        running_max = portfolio_series.expanding().max()
        drawdown = (portfolio_series - running_max) / running_max
        
        # Find drawdown periods
        drawdown_periods = []
        in_drawdown = False
        start_idx = None
        
        for i, dd in enumerate(drawdown):
            if dd < 0 and not in_drawdown:
                in_drawdown = True
                start_idx = i
            elif dd >= 0 and in_drawdown:
                in_drawdown = False
                if start_idx is not None:
                    drawdown_periods.append({
                        'start': timestamps[start_idx],
                        'end': timestamps[i-1] if i > 0 else timestamps[start_idx],
                        'depth': drawdown[start_idx:i].min(),
                        'duration_days': (timestamps[i-1] - timestamps[start_idx]).days if i > start_idx else 0
                    })
        
        return {
            'max_drawdown': drawdown.min(),
            'current_drawdown': drawdown.iloc[-1],
            'drawdown_periods': drawdown_periods,
            'avg_drawdown_duration': np.mean([p['duration_days'] for p in drawdown_periods]) if drawdown_periods else 0
        }
    
    def _filter_history_by_date(self, history: List[Dict], start_date: Optional[datetime], 
                               end_date: Optional[datetime]) -> List[Dict]:
        """Filter history by date range"""
        filtered = history
        
        if start_date:
            filtered = [h for h in filtered if h['timestamp'] >= start_date]
        
        if end_date:
            filtered = [h for h in filtered if h['timestamp'] <= end_date]
        
        return filtered
    
    def _filter_trades_by_date(self, trades: List[Dict], start_date: Optional[datetime],
                              end_date: Optional[datetime]) -> List[Dict]:
        """Filter trades by date range"""
        filtered = trades
        
        if start_date:
            filtered = [t for t in filtered if t['timestamp'] >= start_date]
        
        if end_date:
            filtered = [t for t in filtered if t['timestamp'] <= end_date]
        
        return filtered
    
    def _calculate_trade_metrics(self, metrics: PerformanceMetrics, trades: List[Dict]):
        """Calculate trade-specific metrics"""
        if not trades:
            return
        
        metrics.total_trades = len(trades)
        
        # Group trades into round trips (simplified)
        # For now, just calculate basic trade stats
        [t['value'] for t in trades]
        buy_trades = [t for t in trades if t['side'].upper() == 'BUY']
        sell_trades = [t for t in trades if t['side'].upper() == 'SELL']
        
        if buy_trades and sell_trades:
            avg_buy_price = np.mean([t['price'] for t in buy_trades])
            avg_sell_price = np.mean([t['price'] for t in sell_trades])
            
            # Simplified profit calculation
            if avg_sell_price > avg_buy_price:
                metrics.win_rate = 1.0
                metrics.avg_win = avg_sell_price - avg_buy_price
            else:
                metrics.win_rate = 0.0
                metrics.avg_loss = avg_buy_price - avg_sell_price