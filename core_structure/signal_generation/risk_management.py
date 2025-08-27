"""
Dynamic Risk Management Module - Phase 2 Enhancement
Implements ATR-based dynamic stops, regime-aware risk levels, and position exit logic
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

@dataclass
class SignalRiskConfig:
    """Configuration for signal-level dynamic risk management
    
    Note: For portfolio-level risk config, see infrastructure/config/unified_config_manager.py
    For enterprise risk config, see infrastructure/config/risk_config.py
    """
    # ATR settings
    atr_period: int = 14
    atr_multiplier_base: float = 2.0
    
    # Stop loss settings
    max_stop_loss_pct: float = 0.15  # 15% maximum stop loss
    min_stop_loss_pct: float = 0.02  # 2% minimum stop loss
    trailing_stop_enabled: bool = True
    trailing_stop_distance: float = 0.05  # 5% trailing stop
    
    # Take profit settings
    max_take_profit_pct: float = 0.30  # 30% maximum take profit
    min_take_profit_pct: float = 0.05  # 5% minimum take profit
    trailing_take_profit_enabled: bool = True
    
    # Regime-specific multipliers
    regime_multipliers: Dict[str, Dict[str, float]] = None
    
    # Position exit settings
    max_hold_time_hours: int = 48  # Maximum position hold time
    volatility_exit_threshold: float = 0.08  # Exit if volatility > 8%
    profit_taking_threshold: float = 0.10  # Take profit at 10% move
    
    def __post_init__(self):
        if self.regime_multipliers is None:
            self.regime_multipliers = {
                'trending': {'stop': 2.5, 'target': 4.0},
                'mean_reverting': {'stop': 1.8, 'target': 3.0},
                'volatile': {'stop': 3.0, 'target': 3.0},
                'stable': {'stop': 1.5, 'target': 3.5},
                'unknown': {'stop': 2.0, 'target': 3.0}
            }

class DynamicRiskManager:
    """Dynamic risk management with ATR-based stops and regime awareness"""
    
    def __init__(self, config: Optional[SignalRiskConfig] = None):
        self.config = config or SignalRiskConfig()
        self.position_history = []
        self.risk_metrics = {
            'total_stops_hit': 0,
            'total_targets_hit': 0,
            'avg_stop_distance': 0.0,
            'avg_target_distance': 0.0,
            'risk_reward_ratio': 0.0
        }
    
    def calculate_dynamic_stops(
        self,
        current_price: float,
        market_data: pd.DataFrame,
        signal_type: str,
        confidence: float,
        regime: str,
        position_size: float
    ) -> Tuple[float, float]:
        """
        Calculate dynamic stop-loss and take-profit levels
        
        Args:
            current_price: Current market price
            market_data: Historical market data
            signal_type: 'LONG' or 'SHORT'
            confidence: Signal confidence (0.0 to 1.0)
            regime: Market regime
            position_size: Position size as fraction of portfolio
        
        Returns:
            Tuple of (stop_loss, take_profit) prices
        """
        try:
            # Calculate ATR
            atr = self._calculate_atr(market_data)
            
            # Get regime-specific multipliers
            multipliers = self.config.regime_multipliers.get(regime.lower(), 
                                                           {'stop': 2.0, 'target': 3.0})
            
            # Adjust multipliers based on confidence
            confidence_adj = 1.2 - (confidence * 0.4)  # 0.8x to 1.2x adjustment
            
            # Calculate base distances
            stop_distance = atr * multipliers['stop'] * confidence_adj
            target_distance = atr * multipliers['target']
            
            # Adjust for position size (larger positions = tighter stops)
            size_adjustment = 1.0 - (position_size * 0.3)  # 0.7x to 1.0x for large positions
            stop_distance *= size_adjustment
            
            # Apply percentage bounds
            stop_distance_pct = stop_distance / current_price
            target_distance_pct = target_distance / current_price
            
            # Ensure within bounds
            stop_distance_pct = max(self.config.min_stop_loss_pct, 
                                  min(self.config.max_stop_loss_pct, stop_distance_pct))
            target_distance_pct = max(self.config.min_take_profit_pct, 
                                    min(self.config.max_take_profit_pct, target_distance_pct))
            
            # Calculate final prices
            if signal_type == 'LONG':
                stop_loss = current_price * (1 - stop_distance_pct)
                take_profit = current_price * (1 + target_distance_pct)
            else:  # SHORT
                stop_loss = current_price * (1 + stop_distance_pct)
                take_profit = current_price * (1 - target_distance_pct)
            
            logger.debug(f"Dynamic stops: price=${current_price:.2f}, "
                        f"ATR=${atr:.2f}, regime={regime}, confidence={confidence:.2f}, "
                        f"stop=${stop_loss:.2f}, target=${take_profit:.2f}")
            
            return stop_loss, take_profit
            
        except Exception as e:
            logger.error(f"Dynamic stop calculation failed: {e}")
            # Fallback to simple percentage-based stops
            if signal_type == 'LONG':
                return current_price * 0.95, current_price * 1.10
            else:
                return current_price * 1.05, current_price * 0.90
    
    def should_exit_position(
        self,
        entry_price: float,
        current_price: float,
        entry_time: datetime,
        current_volatility: float,
        market_data: pd.DataFrame,
        position_type: str,
        stop_loss: float,
        take_profit: float
    ) -> Tuple[bool, str, float]:
        """
        Determine if position should be exited based on multiple criteria
        
        Args:
            entry_price: Position entry price
            current_price: Current market price
            entry_time: Position entry time
            current_volatility: Current market volatility
            market_data: Historical market data
            position_type: 'LONG' or 'SHORT'
            stop_loss: Stop loss price
            take_profit: Take profit price
        
        Returns:
            Tuple of (should_exit, reason, exit_price)
        """
        try:
            # Check stop loss
            if position_type == 'LONG' and current_price <= stop_loss:
                return True, 'stop_loss', stop_loss
            elif position_type == 'SHORT' and current_price >= stop_loss:
                return True, 'stop_loss', stop_loss
            
            # Check take profit
            if position_type == 'LONG' and current_price >= take_profit:
                return True, 'take_profit', take_profit
            elif position_type == 'SHORT' and current_price <= take_profit:
                return True, 'take_profit', take_profit
            
            # Check time-based exit
            if datetime.now() - entry_time > timedelta(hours=self.config.max_hold_time_hours):
                return True, 'time_exit', current_price
            
            # Check volatility-based exit
            if current_volatility > self.config.volatility_exit_threshold:
                return True, 'volatility_exit', current_price
            
            # Check profit-taking on large moves
            price_change = abs(current_price - entry_price) / entry_price
            if price_change > self.config.profit_taking_threshold:
                return True, 'profit_taking', current_price
            
            # Check trailing stop (if enabled)
            if self.config.trailing_stop_enabled:
                trailing_stop = self._calculate_trailing_stop(
                    entry_price, current_price, position_type, market_data
                )
                if position_type == 'LONG' and current_price <= trailing_stop:
                    return True, 'trailing_stop', trailing_stop
                elif position_type == 'SHORT' and current_price >= trailing_stop:
                    return True, 'trailing_stop', trailing_stop
            
            return False, '', 0.0
            
        except Exception as e:
            logger.error(f"Position exit check failed: {e}")
            return False, '', 0.0
    
    def _calculate_atr(self, market_data: pd.DataFrame) -> float:
        """Calculate Average True Range"""
        try:
            if len(market_data) < self.config.atr_period:
                return market_data['close'].std() if len(market_data) > 1 else 1.0
            
            # Calculate True Range
            high = market_data['high'].values
            low = market_data['low'].values
            close = market_data['close'].values
            
            tr1 = high - low
            tr2 = np.abs(high - np.roll(close, 1))
            tr3 = np.abs(low - np.roll(close, 1))
            
            true_range = np.maximum(tr1, np.maximum(tr2, tr3))
            
            # Calculate ATR using simple moving average
            atr = np.mean(true_range[-self.config.atr_period:])
            
            return atr if atr > 0 else 1.0
            
        except Exception as e:
            logger.error(f"ATR calculation failed: {e}")
            return 1.0
    
    def _calculate_trailing_stop(
        self,
        entry_price: float,
        current_price: float,
        position_type: str,
        market_data: pd.DataFrame
    ) -> float:
        """Calculate trailing stop level"""
        try:
            # Calculate trailing distance based on ATR
            atr = self._calculate_atr(market_data)
            trailing_distance = atr * self.config.atr_multiplier_base
            
            if position_type == 'LONG':
                # For long positions, trailing stop moves up with price
                trailing_stop = current_price - trailing_distance
                # Don't let trailing stop go below entry price initially
                if current_price < entry_price * 1.02:  # 2% profit threshold
                    trailing_stop = max(trailing_stop, entry_price * 0.98)
            else:  # SHORT
                # For short positions, trailing stop moves down with price
                trailing_stop = current_price + trailing_distance
                # Don't let trailing stop go above entry price initially
                if current_price > entry_price * 0.98:  # 2% profit threshold
                    trailing_stop = min(trailing_stop, entry_price * 1.02)
            
            return trailing_stop
            
        except Exception as e:
            logger.error(f"Trailing stop calculation failed: {e}")
            # Fallback to simple percentage-based trailing stop
            if position_type == 'LONG':
                return current_price * (1 - self.config.trailing_stop_distance)
            else:
                return current_price * (1 + self.config.trailing_stop_distance)
    
    def update_risk_metrics(self, exit_result: Dict[str, Any]) -> None:
        """Update risk metrics based on position exit"""
        try:
            exit_reason = exit_result.get('reason', '')
            stop_distance = exit_result.get('stop_distance', 0.0)
            target_distance = exit_result.get('target_distance', 0.0)
            
            # Update counters
            if 'stop' in exit_reason.lower():
                self.risk_metrics['total_stops_hit'] += 1
            elif 'target' in exit_reason.lower() or 'profit' in exit_reason.lower():
                self.risk_metrics['total_targets_hit'] += 1
            
            # Update averages
            if stop_distance > 0:
                current_avg = self.risk_metrics['avg_stop_distance']
                total_stops = self.risk_metrics['total_stops_hit']
                self.risk_metrics['avg_stop_distance'] = (
                    (current_avg * (total_stops - 1) + stop_distance) / total_stops
                )
            
            if target_distance > 0:
                current_avg = self.risk_metrics['avg_target_distance']
                total_targets = self.risk_metrics['total_targets_hit']
                self.risk_metrics['avg_target_distance'] = (
                    (current_avg * (total_targets - 1) + target_distance) / total_targets
                )
            
            # Update risk-reward ratio
            if self.risk_metrics['avg_stop_distance'] > 0:
                self.risk_metrics['risk_reward_ratio'] = (
                    self.risk_metrics['avg_target_distance'] / self.risk_metrics['avg_stop_distance']
                )
            
            logger.debug(f"Updated risk metrics: stops={self.risk_metrics['total_stops_hit']}, "
                        f"targets={self.risk_metrics['total_targets_hit']}, "
                        f"risk_reward={self.risk_metrics['risk_reward_ratio']:.2f}")
            
        except Exception as e:
            logger.error(f"Failed to update risk metrics: {e}")
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """Get current risk metrics summary"""
        return {
            'total_stops_hit': self.risk_metrics['total_stops_hit'],
            'total_targets_hit': self.risk_metrics['total_targets_hit'],
            'avg_stop_distance': self.risk_metrics['avg_stop_distance'],
            'avg_target_distance': self.risk_metrics['avg_target_distance'],
            'risk_reward_ratio': self.risk_metrics['risk_reward_ratio'],
            'stop_hit_rate': (
                self.risk_metrics['total_stops_hit'] / 
                (self.risk_metrics['total_stops_hit'] + self.risk_metrics['total_targets_hit'])
                if (self.risk_metrics['total_stops_hit'] + self.risk_metrics['total_targets_hit']) > 0 
                else 0.0
            )
        }
