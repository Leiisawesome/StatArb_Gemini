"""
Trading strategy implementation for statistical arbitrage.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from model.kalman import KalmanFilter
from strategy.stationarity import StationarityTester, is_stationary_robust
from strategy.risk_management import RiskManager
import logging

logger = logging.getLogger(__name__)

class StatisticalArbitrageStrategy:
    """
    Statistical arbitrage strategy using Kalman filter for spread modeling.
    """
    
    def __init__(self, 
                 lookback_window: int = 100,
                 entry_threshold: float = 2.0,
                 exit_threshold: float = 0.5,
                 max_position_size: float = 0.1,
                 transaction_cost: float = 0.001):
        
        self.lookback_window = lookback_window
        self.entry_threshold = entry_threshold
        self.exit_threshold = exit_threshold
        self.max_position_size = max_position_size
        self.transaction_cost = transaction_cost
        
        # Initialize components
        self.kalman_filter = KalmanFilter()
        self.stationarity_tester = StationarityTester(window_size=lookback_window)
        self.risk_manager = RiskManager()
        
        # State tracking
        self.current_positions = {}
        self.trade_history = []
        self.spread_history = []
        
    def compute_spread(self, price_data: pd.DataFrame) -> pd.Series:
        """
        Compute the spread between two assets using linear regression.
        """
        if price_data.shape[1] != 2:
            raise ValueError("Price data must contain exactly 2 assets for pair trading")
        
        asset1, asset2 = price_data.columns[0], price_data.columns[1]
        
        # Use linear regression to find hedge ratio
        X = price_data[asset1].to_numpy().reshape(-1, 1)
        y = price_data[asset2].to_numpy()
        
        # Add constant term
        X = np.column_stack([np.ones(X.shape[0]), X])
        
        # Solve using least squares
        try:
            beta = np.linalg.lstsq(X, y, rcond=None)[0]
            hedge_ratio = float(beta[1])
            intercept = float(beta[0])
            
            # Compute spread
            spread = price_data[asset2] - (hedge_ratio * price_data[asset1] + intercept)
            
            return spread
            
        except np.linalg.LinAlgError:
            logger.warning("Linear regression failed, using simple difference")
            return price_data[asset2] - price_data[asset1]
    
    def is_stationary(self, spread: pd.Series) -> bool:
        """
        Check if the spread is stationary using robust testing.
        """
        return is_stationary_robust(spread, window_size=self.lookback_window)
    
    def generate_signals(self, price_data: pd.DataFrame) -> Dict[str, float]:
        """
        Generate trading signals based on spread analysis.
        """
        if len(price_data) < self.lookback_window:
            return {}
        
        # Compute spread
        spread = self.compute_spread(price_data)
        self.spread_history.append(spread.iloc[-1])
        
        # Check stationarity
        is_stationary = self.is_stationary(spread)
        self.stationarity_tester.update_stationarity_history(spread, is_stationary)
        
        if not is_stationary:
            logger.debug("Spread is not stationary, no signals generated")
            return {}
        
        # Update Kalman filter
        self.kalman_filter.update(spread.iloc[-1])
        
        # Get current state
        current_spread = spread.iloc[-1]
        kalman_mean = self.kalman_filter.get_mean()
        kalman_std = self.kalman_filter.get_std()
        
        if kalman_std == 0:
            return {}
        
        # Compute z-score
        z_score = (current_spread - kalman_mean) / kalman_std
        
        signals = {}
        
        # Entry signals
        if abs(z_score) > self.entry_threshold:
            if z_score > 0:  # Spread is high, short asset2, long asset1
                signals['short'] = min(abs(z_score) / self.entry_threshold, 1.0)
            else:  # Spread is low, long asset2, short asset1
                signals['long'] = min(abs(z_score) / self.entry_threshold, 1.0)
        
        # Exit signals for existing positions
        for position_type in self.current_positions:
            if abs(z_score) < self.exit_threshold:
                signals[f'exit_{position_type}'] = 1.0
        
        return signals
    
    def execute_trades(self, signals: Dict[str, float], 
                      current_prices: pd.Series) -> List[Dict]:
        """
        Execute trades based on signals.
        """
        trades = []
        
        for signal_type, strength in signals.items():
            if signal_type.startswith('exit_'):
                # Exit existing position
                position_type = signal_type[5:]  # Remove 'exit_' prefix
                if position_type in self.current_positions:
                    trades.append({
                        'action': 'exit',
                        'position_type': position_type,
                        'strength': strength,
                        'timestamp': current_prices.name
                    })
                    del self.current_positions[position_type]
            
            elif signal_type in ['long', 'short']:
                # Check risk limits
                if not self.risk_manager.can_take_position(signal_type, strength):
                    logger.warning(f"Risk limit exceeded for {signal_type} signal")
                    continue
                
                # Enter new position
                self.current_positions[signal_type] = {
                    'strength': strength,
                    'entry_price': current_prices.mean(),
                    'timestamp': current_prices.name
                }
                
                trades.append({
                    'action': 'enter',
                    'position_type': signal_type,
                    'strength': strength,
                    'timestamp': current_prices.name
                })
        
        self.trade_history.extend(trades)
        return trades
    
    def calculate_pnl(self, current_prices: pd.Series) -> float:
        """
        Calculate current P&L for open positions.
        """
        if not self.current_positions:
            return 0.0
        
        pnl = 0.0
        current_price = current_prices.mean()
        
        for position_type, position in self.current_positions.items():
            entry_price = position['entry_price']
            strength = position['strength']
            
            if position_type == 'long':
                pnl += strength * (current_price - entry_price) / entry_price
            else:  # short
                pnl += strength * (entry_price - current_price) / entry_price
        
        return pnl
    
    def get_performance_metrics(self) -> Dict[str, float]:
        """
        Calculate performance metrics.
        """
        if not self.trade_history:
            return {}
        
        # Calculate basic metrics
        total_trades = len(self.trade_history)
        winning_trades = sum(1 for trade in self.trade_history if trade.get('pnl', 0) > 0)
        win_rate = float(winning_trades / total_trades if total_trades > 0 else 0)
        
        # Calculate returns
        returns = [trade.get('pnl', 0) for trade in self.trade_history]
        total_return = float(sum(returns))
        avg_return = float(np.mean(returns) if returns else 0)
        return_std = float(np.std(returns) if returns else 0)
        
        # Sharpe ratio (assuming risk-free rate of 0)
        sharpe_ratio = float(avg_return / return_std if return_std > 0 else 0)
        
        return {
            'total_trades': float(total_trades),
            'win_rate': win_rate,
            'total_return': total_return,
            'avg_return': avg_return,
            'return_std': return_std,
            'sharpe_ratio': sharpe_ratio
        }
    
    def reset(self):
        """Reset strategy state."""
        self.kalman_filter = KalmanFilter()
        self.stationarity_tester = StationarityTester(window_size=self.lookback_window)
        self.current_positions = {}
        self.trade_history = []
        self.spread_history = [] 