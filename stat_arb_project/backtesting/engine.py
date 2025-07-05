"""
Production-ready backtesting engine for statistical arbitrage strategies.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
from ..data.data_loader import load_intraday_data
from ..strategy.trading import StatisticalArbitrageStrategy
from ..evaluation.metrics import calculate_sharpe_ratio, calculate_max_drawdown
from ..evaluation.robustness import RobustnessTester

logger = logging.getLogger(__name__)

@dataclass
class BacktestConfig:
    """Configuration for backtesting."""
    start_date: str
    end_date: str
    initial_capital: float = 100000.0
    transaction_cost: float = 0.001
    slippage: float = 0.0005
    max_position_size: float = 0.1
    entry_threshold: float = 2.0
    exit_threshold: float = 0.5
    lookback_window: int = 100
    rebalance_frequency: str = '1D'
    risk_free_rate: float = 0.02

@dataclass
class BacktestResult:
    """Results from backtesting."""
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    profit_factor: float
    calmar_ratio: float
    equity_curve: pd.Series
    trade_history: List[Dict]
    performance_metrics: Dict[str, float]

class BacktestingEngine:
    """
    Production-ready backtesting engine with comprehensive risk management.
    """
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.strategy = StatisticalArbitrageStrategy(
            lookback_window=config.lookback_window,
            entry_threshold=config.entry_threshold,
            exit_threshold=config.exit_threshold,
            max_position_size=config.max_position_size,
            transaction_cost=config.transaction_cost
        )
        self.robustness_tester = RobustnessTester()
        
        # Performance tracking
        self.equity_curve = []
        self.trade_history = []
        self.daily_returns = []
        self.current_capital = config.initial_capital
        self.peak_capital = config.initial_capital
        
    def run_backtest(self, tickers: List[str], interval: str = '1h') -> BacktestResult:
        """
        Run comprehensive backtest with error handling and validation.
        """
        logger.info(f"Starting backtest for {tickers} from {self.config.start_date} to {self.config.end_date}")
        
        try:
            # Load data with retry logic
            data = self._load_data_with_validation(tickers, interval)
            if data.empty:
                raise ValueError("No valid data loaded for backtesting")
            
            # Run the backtest
            self._execute_backtest(data)
            
            # Calculate results
            result = self._calculate_results()
            
            # Run robustness tests
            robustness_metrics = self.robustness_tester.test_strategy_robustness(
                self.equity_curve, self.trade_history
            )
            result.performance_metrics.update(robustness_metrics)
            
            logger.info(f"Backtest completed successfully. Total return: {result.total_return:.2%}")
            return result
            
        except Exception as e:
            logger.error(f"Backtest failed: {e}")
            raise
    
    def _load_data_with_validation(self, tickers: List[str], interval: str) -> pd.DataFrame:
        """Load and validate data with comprehensive checks."""
        # Calculate duration based on config dates
        start_dt = pd.to_datetime(self.config.start_date)
        end_dt = pd.to_datetime(self.config.end_date)
        duration_days = (end_dt - start_dt).days
        
        # Add buffer for lookback window
        buffer_days = max(duration_days + 30, 60)  # At least 60 days
        
        data = load_intraday_data(tickers, buffer_days, interval)
        
        if data.empty:
            raise ValueError("Failed to load data from data source")
        
        # Filter to exact date range
        data = data[(data.index >= start_dt) & (data.index <= end_dt)]
        
        if len(data) < self.config.lookback_window * 2:
            raise ValueError(f"Insufficient data: {len(data)} points, need at least {self.config.lookback_window * 2}")
        
        logger.info(f"Loaded {len(data)} data points for backtesting")
        return data
    
    def _execute_backtest(self, data: pd.DataFrame):
        """Execute the backtest with proper position tracking."""
        self.strategy.reset()
        
        for i in range(self.config.lookback_window, len(data)):
            current_data = data.iloc[:i+1]
            current_prices = data.iloc[i]
            
            # Generate signals
            signals = self.strategy.generate_signals(current_data)
            
            # Execute trades
            trades = self.strategy.execute_trades(signals, current_prices)
            
            # Update portfolio
            self._update_portfolio(trades, current_prices, i)
            
            # Record daily performance
            if i % 24 == 0:  # Daily recording for intraday data
                self._record_daily_performance(current_prices, i)
    
    def _update_portfolio(self, trades: List[Dict], current_prices: pd.Series, timestamp_idx: int):
        """Update portfolio based on executed trades."""
        for trade in trades:
            # Apply transaction costs and slippage
            cost = self.config.transaction_cost + self.config.slippage
            
            if trade['action'] == 'enter':
                # Calculate position value
                position_value = trade['strength'] * self.current_capital
                transaction_cost = position_value * cost
                
                # Update capital
                self.current_capital -= transaction_cost
                
                # Record trade
                trade_record = {
                    'timestamp': current_prices.name,
                    'action': trade['action'],
                    'position_type': trade['position_type'],
                    'strength': trade['strength'],
                    'price': current_prices.mean(),
                    'cost': transaction_cost,
                    'capital': self.current_capital
                }
                self.trade_history.append(trade_record)
                
            elif trade['action'] == 'exit':
                # Calculate P&L
                entry_trade = next((t for t in self.trade_history 
                                  if t['action'] == 'enter' and t['position_type'] == trade['position_type']), None)
                
                if entry_trade:
                    entry_price = entry_trade['price']
                    current_price = current_prices.mean()
                    
                    if trade['position_type'] == 'long':
                        pnl = (current_price - entry_price) / entry_price
                    else:  # short
                        pnl = (entry_price - current_price) / entry_price
                    
                    # Apply transaction costs
                    position_value = entry_trade['strength'] * self.current_capital
                    transaction_cost = position_value * cost
                    net_pnl = position_value * pnl - transaction_cost
                    
                    # Update capital
                    self.current_capital += net_pnl
                    
                    # Record exit trade
                    trade_record = {
                        'timestamp': current_prices.name,
                        'action': trade['action'],
                        'position_type': trade['position_type'],
                        'pnl': net_pnl,
                        'capital': self.current_capital
                    }
                    self.trade_history.append(trade_record)
        
        # Update peak capital
        self.peak_capital = max(self.peak_capital, self.current_capital)
    
    def _record_daily_performance(self, current_prices: pd.Series, timestamp_idx: int):
        """Record daily performance metrics."""
        self.equity_curve.append(self.current_capital)
        
        if len(self.equity_curve) > 1:
            daily_return = (self.current_capital - self.equity_curve[-2]) / self.equity_curve[-2]
            self.daily_returns.append(daily_return)
    
    def _calculate_results(self) -> BacktestResult:
        """Calculate comprehensive backtest results."""
        if not self.equity_curve:
            raise ValueError("No equity curve data available")
        
        equity_series = pd.Series(self.equity_curve)
        returns_series = pd.Series(self.daily_returns)
        
        # Basic metrics
        total_return = (self.current_capital - self.config.initial_capital) / self.config.initial_capital
        annualized_return = self._calculate_annualized_return(total_return)
        volatility = returns_series.std() * np.sqrt(252) if len(returns_series) > 0 else 0
        
        # Risk-adjusted metrics
        sharpe_ratio = calculate_sharpe_ratio(returns_series, self.config.risk_free_rate)
        max_drawdown = calculate_max_drawdown(equity_series)
        
        # Trade metrics
        total_trades = len([t for t in self.trade_history if t['action'] == 'exit'])
        winning_trades = len([t for t in self.trade_history if t['action'] == 'exit' and t.get('pnl', 0) > 0])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # Profit factor
        gross_profit = sum(t.get('pnl', 0) for t in self.trade_history if t.get('pnl', 0) > 0)
        gross_loss = abs(sum(t.get('pnl', 0) for t in self.trade_history if t.get('pnl', 0) < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Calmar ratio
        calmar_ratio = annualized_return / max_drawdown if max_drawdown > 0 else 0
        
        # Performance metrics dictionary
        performance_metrics = {
            'sortino_ratio': self._calculate_sortino_ratio(returns_series),
            'var_95': self._calculate_var(returns_series, 0.95),
            'cvar_95': self._calculate_cvar(returns_series, 0.95),
            'avg_trade_duration': self._calculate_avg_trade_duration(),
            'max_consecutive_losses': self._calculate_max_consecutive_losses(),
            'recovery_factor': total_return / max_drawdown if max_drawdown > 0 else 0
        }
        
        return BacktestResult(
            total_return=total_return,
            annualized_return=annualized_return,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            total_trades=total_trades,
            profit_factor=profit_factor,
            calmar_ratio=calmar_ratio,
            equity_curve=equity_series,
            trade_history=self.trade_history,
            performance_metrics=performance_metrics
        )
    
    def _calculate_annualized_return(self, total_return: float) -> float:
        """Calculate annualized return."""
        start_dt = pd.to_datetime(self.config.start_date)
        end_dt = pd.to_datetime(self.config.end_date)
        years = (end_dt - start_dt).days / 365.25
        return (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
    
    def _calculate_sortino_ratio(self, returns: pd.Series) -> float:
        """Calculate Sortino ratio."""
        if len(returns) == 0:
            return 0.0
        
        negative_returns = returns[returns < 0]
        downside_deviation = negative_returns.std() * np.sqrt(252) if len(negative_returns) > 0 else 0
        
        avg_return = returns.mean() * 252
        return (avg_return - self.config.risk_free_rate) / downside_deviation if downside_deviation > 0 else 0
    
    def _calculate_var(self, returns: pd.Series, confidence_level: float) -> float:
        """Calculate Value at Risk."""
        if len(returns) == 0:
            return 0.0
        return float(np.percentile(returns, (1 - confidence_level) * 100))
    
    def _calculate_cvar(self, returns: pd.Series, confidence_level: float) -> float:
        """Calculate Conditional Value at Risk."""
        if len(returns) == 0:
            return 0.0
        var = self._calculate_var(returns, confidence_level)
        tail_returns = returns[returns <= var]
        return float(tail_returns.mean()) if len(tail_returns) > 0 else 0
    
    def _calculate_avg_trade_duration(self) -> float:
        """Calculate average trade duration."""
        exit_trades = [t for t in self.trade_history if t['action'] == 'exit']
        if not exit_trades:
            return 0.0
        
        durations = []
        for exit_trade in exit_trades:
            entry_trade = next((t for t in self.trade_history 
                              if t['action'] == 'enter' and t['position_type'] == exit_trade['position_type']), None)
            if entry_trade:
                duration = (pd.to_datetime(exit_trade['timestamp']) - 
                           pd.to_datetime(entry_trade['timestamp'])).total_seconds() / 3600  # hours
                durations.append(duration)
        
        return float(np.mean(durations)) if durations else 0.0
    
    def _calculate_max_consecutive_losses(self) -> int:
        """Calculate maximum consecutive losses."""
        exit_trades = [t for t in self.trade_history if t['action'] == 'exit']
        if not exit_trades:
            return 0
        
        max_consecutive = 0
        current_consecutive = 0
        
        for trade in exit_trades:
            if trade.get('pnl', 0) < 0:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
        
        return max_consecutive 