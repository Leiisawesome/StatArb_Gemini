"""
Professional Pair Trading Strategy Implementation
Uses advanced Kalman filter and robust cointegration testing.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import logging

from ..model.kalman import AdvancedKalmanFilter
from ..strategy.cointegration import CointegrationTester
from stat_arb_project.strategy.risk_management import RiskManager, RiskLimits

logger = logging.getLogger(__name__)

def validate_price_data(data, assets):
    # Simple validation: check columns exist and no NaNs in last row
    if not all(asset in data.columns for asset in assets):
        return False
    if data.iloc[-1][assets].isnull().any():
        return False
    return True

class ProfessionalPairTradingStrategy:
    """
    Professional pair trading strategy with advanced features:
    - Advanced Kalman filter for hedge ratio estimation
    - Robust cointegration testing
    - Dynamic position sizing
    - Risk management integration
    - Performance monitoring
    """
    
    def __init__(self,
                 asset1: str,
                 asset2: str,
                 kalman_params: Optional[Dict[str, float]] = None,
                 cointegration_params: Optional[Dict[str, Any]] = None,
                 risk_params: Optional[Dict[str, float]] = None,
                 signal_params: Optional[Dict[str, float]] = None):
        """
        Initialize professional pair trading strategy.
        
        Args:
            asset1: First asset symbol
            asset2: Second asset symbol
            kalman_params: Kalman filter parameters
            cointegration_params: Cointegration testing parameters
            risk_params: Risk management parameters
            signal_params: Signal generation parameters
        """
        self.asset1 = asset1
        self.asset2 = asset2
        
        # Initialize components
        self.kalman_filter = AdvancedKalmanFilter(**(kalman_params or {}))
        self.cointegration_tester = CointegrationTester(**(cointegration_params or {}))
        # Ensure risk_params is a dict for RiskLimits
        risk_limits = RiskLimits(**(risk_params or {}))
        self.risk_manager = RiskManager(risk_limits)
        
        # Signal parameters
        self.signal_params = signal_params or {
            'entry_threshold': 2.0,      # Z-score for entry
            'exit_threshold': 0.5,       # Z-score for exit
            'stop_loss': 3.0,           # Stop loss Z-score
            'take_profit': 4.0,         # Take profit Z-score
            'min_holding_period': 5,     # Minimum holding period
            'max_holding_period': 50     # Maximum holding period
        }
        
        # State tracking
        self.current_position = 0  # -1: short spread, 0: flat, 1: long spread
        self.position_entry_time = None
        self.position_entry_price = None
        self.position_entry_zscore = None
        
        # Performance tracking
        self.trade_history = []
        self.daily_pnl = []
        self.performance_metrics = {}
        
        # Cointegration status
        self.is_cointegrated = False
        self.cointegration_confidence = 0.0
        self.last_cointegration_test = None
        
        # Kalman filter status
        self.kalman_initialized = False
        self.min_observations = 50
        
        logger.info(f"Initialized pair trading strategy for {asset1}/{asset2}")
    
    def update(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Update strategy with new data.
        
        Args:
            data: Price data with columns for both assets
            
        Returns:
            Strategy update results
        """
        try:
            # Validate data
            if not validate_price_data(data, [self.asset1, self.asset2]):
                return {'error': 'Invalid price data'}
            
            # Extract current prices
            current_prices = data.iloc[-1]
            price1 = current_prices[self.asset1]
            price2 = current_prices[self.asset2]
            
            # Update Kalman filter
            kalman_result = self.kalman_filter.update(price2, price1)
            
            # Check if Kalman filter is ready
            if not self.kalman_initialized and self.kalman_filter.observation_count >= self.min_observations:
                self.kalman_initialized = True
                logger.info("Kalman filter initialized")
            
            # Test cointegration periodically
            self._update_cointegration_status(data)
            
            # Generate signals
            signals = self._generate_signals(data)
            
            # Execute trades
            trades = self._execute_trades(signals, current_prices)
            
            # Update performance
            self._update_performance(current_prices)
            
            # Risk management
            risk_actions = self.risk_manager.check_risk_limits(self.current_position, self.daily_pnl)
            
            return {
                'kalman_state': kalman_result,
                'cointegration_status': {
                    'is_cointegrated': self.is_cointegrated,
                    'confidence': self.cointegration_confidence
                },
                'signals': signals,
                'trades': trades,
                'risk_actions': risk_actions,
                'position': self.current_position,
                'performance': self.performance_metrics
            }
            
        except Exception as e:
            logger.error(f"Strategy update failed: {e}")
            return {'error': str(e)}
    
    def _update_cointegration_status(self, data: pd.DataFrame):
        """Update cointegration status periodically."""
        # Test cointegration every 20 observations
        if len(data) % 20 == 0 and len(data) >= 100:
            try:
                series1 = pd.Series(data[self.asset1].values, index=data.index)
                series2 = pd.Series(data[self.asset2].values, index=data.index)
                
                coint_result = self.cointegration_tester.test_cointegration(
                    series1, series2, test_type='comprehensive'
                )
                
                self.is_cointegrated = coint_result.get('is_cointegrated', False)
                self.cointegration_confidence = coint_result.get('confidence', 0.0)
                self.last_cointegration_test = len(data)
                
                logger.info(f"Cointegration test: {self.is_cointegrated} "
                           f"(confidence: {self.cointegration_confidence:.3f})")
                
            except Exception as e:
                logger.warning(f"Cointegration test failed: {e}")
    
    def _generate_signals(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate trading signals based on current state.
        
        Args:
            data: Price data
            
        Returns:
            Signal dictionary
        """
        if not self.kalman_initialized:
            return {'signal': 'hold', 'reason': 'Kalman filter not initialized'}
        
        if not self.is_cointegrated:
            return {'signal': 'hold', 'reason': 'Assets not cointegrated'}
        
        # Get current prices
        current_prices = data.iloc[-1]
        price1 = current_prices[self.asset1]
        price2 = current_prices[self.asset2]
        
        # Calculate z-score
        z_score = self.kalman_filter.get_z_score(price2, price1)
        
        # Get confidence intervals
        lower_bound, upper_bound = self.kalman_filter.get_confidence_intervals(price1)
        
        # Signal generation logic
        signal = 'hold'
        reason = ''
        
        if self.current_position == 0:  # No position
            if z_score > self.signal_params['entry_threshold']:
                signal = 'short_spread'  # Short asset2, long asset1
                reason = f'Z-score ({z_score:.2f}) above entry threshold'
            elif z_score < -self.signal_params['entry_threshold']:
                signal = 'long_spread'   # Long asset2, short asset1
                reason = f'Z-score ({z_score:.2f}) below entry threshold'
        
        elif self.current_position == 1:  # Long spread position
            if (z_score < -self.signal_params['exit_threshold'] or 
                z_score > self.signal_params['stop_loss']):
                signal = 'exit_long'
                reason = f'Exit long position: Z-score = {z_score:.2f}'
        
        elif self.current_position == -1:  # Short spread position
            if (z_score > self.signal_params['exit_threshold'] or 
                z_score < -self.signal_params['stop_loss']):
                signal = 'exit_short'
                reason = f'Exit short position: Z-score = {z_score:.2f}'
        
        # Check holding period limits
        if self.position_entry_time is not None:
            holding_period = len(data) - self.position_entry_time
            if holding_period > self.signal_params['max_holding_period']:
                signal = 'exit_force'
                reason = f'Maximum holding period exceeded ({holding_period} periods)'
        
        return {
            'signal': signal,
            'reason': reason,
            'z_score': z_score,
            'confidence_intervals': (lower_bound, upper_bound),
            'kalman_metrics': self.kalman_filter.get_performance_metrics()
        }
    
    def _execute_trades(self, signals: Dict[str, Any], current_prices: pd.Series) -> List[Dict[str, Any]]:
        """
        Execute trades based on signals.
        
        Args:
            signals: Signal dictionary
            current_prices: Current asset prices
            
        Returns:
            List of executed trades
        """
        trades = []
        signal = signals.get('signal', 'hold')
        
        if signal == 'hold':
            return trades
        
        # Calculate position sizes
        price1 = float(current_prices[self.asset1])
        price2 = float(current_prices[self.asset2])
        position_size = self.risk_manager.calculate_position_size(
            price1,
            price2,
            self.kalman_filter.get_hedge_ratio()
        )
        
        if signal == 'long_spread':
            # Long asset2, short asset1
            trade = {
                'timestamp': datetime.now(),
                'signal': signal,
                'asset1_action': 'sell',
                'asset2_action': 'buy',
                'asset1_size': position_size,
                'asset2_size': position_size * self.kalman_filter.get_hedge_ratio(),
                'entry_price1': current_prices[self.asset1],
                'entry_price2': current_prices[self.asset2],
                'z_score': signals.get('z_score', 0)
            }
            
            self.current_position = 1
            self.position_entry_time = len(self.daily_pnl)
            self.position_entry_price = (current_prices[self.asset1], current_prices[self.asset2])
            self.position_entry_zscore = signals.get('z_score', 0)
            
            trades.append(trade)
            
        elif signal == 'short_spread':
            # Short asset2, long asset1
            trade = {
                'timestamp': datetime.now(),
                'signal': signal,
                'asset1_action': 'buy',
                'asset2_action': 'sell',
                'asset1_size': position_size,
                'asset2_size': position_size * self.kalman_filter.get_hedge_ratio(),
                'entry_price1': current_prices[self.asset1],
                'entry_price2': current_prices[self.asset2],
                'z_score': signals.get('z_score', 0)
            }
            
            self.current_position = -1
            self.position_entry_time = len(self.daily_pnl)
            self.position_entry_price = (current_prices[self.asset1], current_prices[self.asset2])
            self.position_entry_zscore = signals.get('z_score', 0)
            
            trades.append(trade)
            
        elif signal in ['exit_long', 'exit_short', 'exit_force']:
            # Close position
            if self.current_position != 0:
                trade = {
                    'timestamp': datetime.now(),
                    'signal': signal,
                    'asset1_action': 'buy' if self.current_position == 1 else 'sell',
                    'asset2_action': 'sell' if self.current_position == 1 else 'buy',
                    'asset1_size': abs(self.current_position),
                    'asset2_size': abs(self.current_position) * self.kalman_filter.get_hedge_ratio(),
                    'exit_price1': current_prices[self.asset1],
                    'exit_price2': current_prices[self.asset2],
                    'z_score': signals.get('z_score', 0),
                    'holding_period': len(self.daily_pnl) - self.position_entry_time if self.position_entry_time else 0
                }
                
                # Calculate P&L
                if self.position_entry_price:
                    entry_price1, entry_price2 = self.position_entry_price
                    pnl = self._calculate_pnl(
                        float(entry_price1), float(entry_price2),
                        float(current_prices[self.asset1]), float(current_prices[self.asset2]),
                        self.current_position
                    )
                    trade['pnl'] = pnl
                
                trades.append(trade)
                self.trade_history.append(trade)
                
                # Reset position
                self.current_position = 0
                self.position_entry_time = None
                self.position_entry_price = None
                self.position_entry_zscore = None
        
        return trades
    
    def _calculate_pnl(self, entry_price1: float, entry_price2: float,
                      exit_price1: float, exit_price2: float, position: int) -> float:
        """
        Calculate P&L for a closed position.
        
        Args:
            entry_price1: Entry price for asset1
            entry_price2: Entry price for asset2
            exit_price1: Exit price for asset1
            exit_price2: Exit price for asset2
            position: Position direction (1: long spread, -1: short spread)
            
        Returns:
            P&L
        """
        if position == 1:  # Long spread: long asset2, short asset1
            pnl = (float(exit_price2) - float(entry_price2)) - (float(exit_price1) - float(entry_price1))
        elif position == -1:  # Short spread: short asset2, long asset1
            pnl = (float(entry_price2) - float(exit_price2)) - (float(entry_price1) - float(exit_price1))
        else:
            pnl = 0.0
        
        return pnl
    
    def _update_performance(self, current_prices: pd.Series):
        """Update performance metrics."""
        # Calculate current P&L if in position
        if self.current_position != 0 and self.position_entry_price:
            entry_price1, entry_price2 = self.position_entry_price
            current_pnl = self._calculate_pnl(
                float(entry_price1), float(entry_price2),
                float(current_prices[self.asset1]), float(current_prices[self.asset2]),
                self.current_position
            )
        else:
            current_pnl = 0.0
        
        self.daily_pnl.append(current_pnl)
        
        # Update performance metrics
        if len(self.daily_pnl) > 1:
            returns = pd.Series(self.daily_pnl).pct_change().dropna()
            
            self.performance_metrics = {
                'total_pnl': sum(self.daily_pnl),
                'sharpe_ratio': returns.mean() / returns.std() if returns.std() > 0 else 0,
                'max_drawdown': self._calculate_max_drawdown(),
                'win_rate': self._calculate_win_rate(),
                'total_trades': len(self.trade_history)
            }
    
    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown."""
        if not self.daily_pnl:
            return 0.0
        
        cumulative = pd.Series(self.daily_pnl).cumsum()
        peak = cumulative.expanding().max()
        drawdown = (cumulative - peak) / peak.abs()
        
        return float(drawdown.min())
    
    def _calculate_win_rate(self) -> float:
        """Calculate win rate from trade history."""
        if not self.trade_history:
            return 0.0
        
        winning_trades = [t for t in self.trade_history if t.get('pnl', 0) > 0]
        return len(winning_trades) / len(self.trade_history)
    
    def get_strategy_summary(self) -> Dict[str, Any]:
        """Get comprehensive strategy summary."""
        return {
            'assets': (self.asset1, self.asset2),
            'kalman_state': {
                'initialized': self.kalman_initialized,
                'observations': self.kalman_filter.observation_count,
                'hedge_ratio': self.kalman_filter.get_hedge_ratio(),
                'volatility': self.kalman_filter.get_volatility(),
                'performance': self.kalman_filter.get_performance_metrics()
            },
            'cointegration': {
                'is_cointegrated': self.is_cointegrated,
                'confidence': self.cointegration_confidence,
                'last_test': self.last_cointegration_test
            },
            'position': {
                'current': self.current_position,
                'entry_time': self.position_entry_time,
                'entry_prices': self.position_entry_price,
                'entry_zscore': self.position_entry_zscore
            },
            'performance': self.performance_metrics,
            'risk_metrics': self.risk_manager.get_risk_metrics()
        }
    
    def reset(self):
        """Reset strategy state."""
        self.kalman_filter.reset()
        self.current_position = 0
        self.position_entry_time = None
        self.position_entry_price = None
        self.position_entry_zscore = None
        self.trade_history = []
        self.daily_pnl = []
        self.performance_metrics = {}
        self.is_cointegrated = False
        self.cointegration_confidence = 0.0
        self.last_cointegration_test = None
        self.kalman_initialized = False
        
        logger.info("Strategy reset completed") 