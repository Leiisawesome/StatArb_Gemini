"""
Position Sizer Building Block

Position sizing building blocks for calculating optimal position sizes
based on various methods and risk parameters.

Author: Pro Quant Desk Trader
"""

import logging
import numpy as np
import pandas as pd
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field

from strategy_layer.base import StrategyError


@dataclass
class PositionSizingConfig:
    """Configuration for position sizing"""
    method: str
    max_position_size: float = 0.1
    max_portfolio_allocation: float = 0.2
    risk_per_trade: float = 0.02
    volatility_lookback: int = 20
    kelly_fraction: float = 0.25
    fixed_size: float = 0.05
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'method': self.method,
            'max_position_size': self.max_position_size,
            'max_portfolio_allocation': self.max_portfolio_allocation,
            'risk_per_trade': self.risk_per_trade,
            'volatility_lookback': self.volatility_lookback,
            'kelly_fraction': self.kelly_fraction,
            'fixed_size': self.fixed_size,
            'parameters': self.parameters
        }


class BasePositionSizer(ABC):
    """Base class for position sizing methods"""
    
    def __init__(self, config: PositionSizingConfig):
        self.config = config
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self._validate_config()
    
    @abstractmethod
    def calculate_position_size(self, signal: float, market_data: pd.DataFrame, 
                              portfolio_value: float, current_positions: Dict[str, float]) -> float:
        """Calculate position size based on signal and market data"""
        pass
    
    def _validate_config(self):
        """Validate position sizing configuration"""
        if not self.config.method:
            raise StrategyError("Position sizing method is required")
        
        if self.config.max_position_size <= 0 or self.config.max_position_size > 1:
            raise StrategyError("Max position size must be between 0 and 1")
        
        if self.config.max_portfolio_allocation <= 0 or self.config.max_portfolio_allocation > 1:
            raise StrategyError("Max portfolio allocation must be between 0 and 1")
    
    def _apply_limits(self, position_size: float, portfolio_value: float, 
                     current_positions: Dict[str, float]) -> float:
        """Apply position size limits"""
        try:
            # Apply max position size limit
            max_size = self.config.max_position_size
            position_size = min(position_size, max_size)
            
            # Apply max portfolio allocation limit
            total_allocation = sum(abs(pos) for pos in current_positions.values())
            remaining_allocation = self.config.max_portfolio_allocation - total_allocation
            
            if remaining_allocation <= 0:
                self.logger.warning("Portfolio allocation limit reached")
                return 0.0
            
            position_size = min(position_size, remaining_allocation)
            
            # Ensure non-negative
            position_size = max(0.0, position_size)
            
            return position_size
            
        except Exception as e:
            self.logger.error(f"Error applying position limits: {e}")
            return 0.0


class FixedPositionSizer(BasePositionSizer):
    """Fixed position sizing method"""
    
    def calculate_position_size(self, signal: float, market_data: pd.DataFrame, 
                              portfolio_value: float, current_positions: Dict[str, float]) -> float:
        """Calculate fixed position size"""
        try:
            if abs(signal) < 0.1:  # Minimum signal threshold
                return 0.0
            
            # Use fixed size from config
            position_size = self.config.fixed_size
            
            # Apply signal direction
            if signal < 0:
                position_size = -position_size
            
            # Apply limits
            position_size = self._apply_limits(abs(position_size), portfolio_value, current_positions)
            
            # Restore sign
            if signal < 0:
                position_size = -position_size
            
            return position_size
            
        except Exception as e:
            self.logger.error(f"Error calculating fixed position size: {e}")
            return 0.0


class KellyPositionSizer(BasePositionSizer):
    """Kelly Criterion position sizing method"""
    
    def calculate_position_size(self, signal: float, market_data: pd.DataFrame, 
                              portfolio_value: float, current_positions: Dict[str, float]) -> float:
        """Calculate Kelly Criterion position size"""
        try:
            if abs(signal) < 0.1:  # Minimum signal threshold
                return 0.0
            
            # Calculate win rate and average win/loss from historical data
            win_rate, avg_win, avg_loss = self._calculate_kelly_parameters(market_data)
            
            if win_rate <= 0 or avg_win <= 0 or avg_loss <= 0:
                self.logger.warning("Insufficient data for Kelly calculation, using fixed size")
                return self._fallback_position_size(signal, portfolio_value, current_positions)
            
            # Calculate Kelly fraction
            kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
            
            # Apply Kelly fraction limit
            kelly_fraction = min(kelly_fraction, self.config.kelly_fraction)
            kelly_fraction = max(kelly_fraction, 0.0)
            
            # Calculate position size
            position_size = kelly_fraction * abs(signal)
            
            # Apply signal direction
            if signal < 0:
                position_size = -position_size
            
            # Apply limits
            position_size = self._apply_limits(abs(position_size), portfolio_value, current_positions)
            
            # Restore sign
            if signal < 0:
                position_size = -position_size
            
            return position_size
            
        except Exception as e:
            self.logger.error(f"Error calculating Kelly position size: {e}")
            return 0.0
    
    def _calculate_kelly_parameters(self, market_data: pd.DataFrame) -> tuple:
        """Calculate Kelly Criterion parameters from historical data"""
        try:
            if len(market_data) < 50:
                return 0.5, 0.02, 0.01  # Default values
            
            # Calculate returns
            returns = market_data['close'].pct_change().dropna()
            
            # Calculate win rate
            wins = (returns > 0).sum()
            total_trades = len(returns)
            win_rate = wins / total_trades if total_trades > 0 else 0.5
            
            # Calculate average win and loss
            winning_returns = returns[returns > 0]
            losing_returns = returns[returns < 0]
            
            avg_win = winning_returns.mean() if len(winning_returns) > 0 else 0.02
            avg_loss = abs(losing_returns.mean()) if len(losing_returns) > 0 else 0.01
            
            return win_rate, avg_win, avg_loss
            
        except Exception as e:
            self.logger.error(f"Error calculating Kelly parameters: {e}")
            return 0.5, 0.02, 0.01
    
    def _fallback_position_size(self, signal: float, portfolio_value: float, 
                               current_positions: Dict[str, float]) -> float:
        """Fallback to fixed position sizing"""
        try:
            position_size = self.config.fixed_size * abs(signal)
            
            if signal < 0:
                position_size = -position_size
            
            position_size = self._apply_limits(abs(position_size), portfolio_value, current_positions)
            
            if signal < 0:
                position_size = -position_size
            
            return position_size
            
        except Exception as e:
            self.logger.error(f"Error in fallback position sizing: {e}")
            return 0.0


class VolatilityAdjustedPositionSizer(BasePositionSizer):
    """Volatility-adjusted position sizing method"""
    
    def calculate_position_size(self, signal: float, market_data: pd.DataFrame, 
                              portfolio_value: float, current_positions: Dict[str, float]) -> float:
        """Calculate volatility-adjusted position size"""
        try:
            if abs(signal) < 0.1:  # Minimum signal threshold
                return 0.0
            
            # Calculate volatility
            volatility = self._calculate_volatility(market_data)
            
            if volatility <= 0:
                self.logger.warning("Invalid volatility, using fixed size")
                return self._fallback_position_size(signal, portfolio_value, current_positions)
            
            # Calculate volatility-adjusted position size
            # Higher volatility = smaller position size
            volatility_factor = 1.0 / (1.0 + volatility)
            base_size = self.config.fixed_size
            
            position_size = base_size * volatility_factor * abs(signal)
            
            # Apply signal direction
            if signal < 0:
                position_size = -position_size
            
            # Apply limits
            position_size = self._apply_limits(abs(position_size), portfolio_value, current_positions)
            
            # Restore sign
            if signal < 0:
                position_size = -position_size
            
            return position_size
            
        except Exception as e:
            self.logger.error(f"Error calculating volatility-adjusted position size: {e}")
            return 0.0
    
    def _calculate_volatility(self, market_data: pd.DataFrame) -> float:
        """Calculate historical volatility"""
        try:
            if len(market_data) < self.config.volatility_lookback:
                return 0.02  # Default volatility
            
            # Calculate returns
            returns = market_data['close'].pct_change().dropna()
            
            # Calculate rolling volatility
            volatility = returns.rolling(window=self.config.volatility_lookback).std().iloc[-1]
            
            # Annualize volatility (assuming daily data)
            annualized_volatility = volatility * np.sqrt(252)
            
            return annualized_volatility
            
        except Exception as e:
            self.logger.error(f"Error calculating volatility: {e}")
            return 0.02
    
    def _fallback_position_size(self, signal: float, portfolio_value: float, 
                               current_positions: Dict[str, float]) -> float:
        """Fallback to fixed position sizing"""
        try:
            position_size = self.config.fixed_size * abs(signal)
            
            if signal < 0:
                position_size = -position_size
            
            position_size = self._apply_limits(abs(position_size), portfolio_value, current_positions)
            
            if signal < 0:
                position_size = -position_size
            
            return position_size
            
        except Exception as e:
            self.logger.error(f"Error in fallback position sizing: {e}")
            return 0.0


class RiskBasedPositionSizer(BasePositionSizer):
    """Risk-based position sizing method"""
    
    def calculate_position_size(self, signal: float, market_data: pd.DataFrame, 
                              portfolio_value: float, current_positions: Dict[str, float]) -> float:
        """Calculate risk-based position size"""
        try:
            if abs(signal) < 0.1:  # Minimum signal threshold
                return 0.0
            
            # Calculate position size based on risk per trade
            risk_amount = portfolio_value * self.config.risk_per_trade
            
            # Calculate stop loss distance (simplified)
            stop_loss_distance = self._calculate_stop_loss_distance(market_data, signal)
            
            if stop_loss_distance <= 0:
                self.logger.warning("Invalid stop loss distance, using fixed size")
                return self._fallback_position_size(signal, portfolio_value, current_positions)
            
            # Calculate position size based on risk
            position_size = risk_amount / stop_loss_distance
            
            # Convert to percentage of portfolio
            position_size = position_size / portfolio_value
            
            # Apply signal direction
            if signal < 0:
                position_size = -position_size
            
            # Apply limits
            position_size = self._apply_limits(abs(position_size), portfolio_value, current_positions)
            
            # Restore sign
            if signal < 0:
                position_size = -position_size
            
            return position_size
            
        except Exception as e:
            self.logger.error(f"Error calculating risk-based position size: {e}")
            return 0.0
    
    def _calculate_stop_loss_distance(self, market_data: pd.DataFrame, signal: float) -> float:
        """Calculate stop loss distance"""
        try:
            if len(market_data) < 20:
                return 0.02  # Default 2% stop loss
            
            # Calculate ATR (Average True Range) for stop loss
            high = market_data['high']
            low = market_data['low']
            close = market_data['close']
            
            # True Range calculation
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = true_range.rolling(window=14).mean().iloc[-1]
            
            # Use ATR as stop loss distance
            stop_loss_distance = atr / close.iloc[-1]
            
            # Ensure reasonable bounds
            stop_loss_distance = max(stop_loss_distance, 0.01)  # Minimum 1%
            stop_loss_distance = min(stop_loss_distance, 0.10)  # Maximum 10%
            
            return stop_loss_distance
            
        except Exception as e:
            self.logger.error(f"Error calculating stop loss distance: {e}")
            return 0.02
    
    def _fallback_position_size(self, signal: float, portfolio_value: float, 
                               current_positions: Dict[str, float]) -> float:
        """Fallback to fixed position sizing"""
        try:
            position_size = self.config.fixed_size * abs(signal)
            
            if signal < 0:
                position_size = -position_size
            
            position_size = self._apply_limits(abs(position_size), portfolio_value, current_positions)
            
            if signal < 0:
                position_size = -position_size
            
            return position_size
            
        except Exception as e:
            self.logger.error(f"Error in fallback position sizing: {e}")
            return 0.0


class PositionSizer:
    """Main position sizer that uses different sizing methods"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.sizer = self._create_position_sizer()
    
    def _create_position_sizer(self) -> BasePositionSizer:
        """Create position sizer based on configuration"""
        try:
            method = self.config.get('method', 'fixed')
            
            sizing_config = PositionSizingConfig(
                method=method,
                max_position_size=self.config.get('max_position_size', 0.1),
                max_portfolio_allocation=self.config.get('max_portfolio_allocation', 0.2),
                risk_per_trade=self.config.get('risk_per_trade', 0.02),
                volatility_lookback=self.config.get('volatility_lookback', 20),
                kelly_fraction=self.config.get('kelly_fraction', 0.25),
                fixed_size=self.config.get('fixed_size', 0.05),
                parameters=self.config.get('parameters', {})
            )
            
            if method == 'fixed':
                return FixedPositionSizer(sizing_config)
            elif method == 'kelly':
                return KellyPositionSizer(sizing_config)
            elif method == 'volatility_adjusted':
                return VolatilityAdjustedPositionSizer(sizing_config)
            elif method == 'risk_based':
                return RiskBasedPositionSizer(sizing_config)
            else:
                self.logger.warning(f"Unknown position sizing method: {method}, using fixed")
                return FixedPositionSizer(sizing_config)
                
        except Exception as e:
            self.logger.error(f"Error creating position sizer: {e}")
            # Fallback to fixed sizing
            sizing_config = PositionSizingConfig(method='fixed', fixed_size=0.05)
            return FixedPositionSizer(sizing_config)
    
    def calculate_position_size(self, signal: float, market_data: pd.DataFrame, 
                              portfolio_value: float, current_positions: Dict[str, float]) -> float:
        """Calculate position size using the configured method"""
        try:
            return self.sizer.calculate_position_size(signal, market_data, portfolio_value, current_positions)
        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return 0.0
    
    def get_method(self) -> str:
        """Get the current position sizing method"""
        return self.sizer.config.method
    
    def update_config(self, config: Dict[str, Any]):
        """Update position sizing configuration"""
        try:
            self.config.update(config)
            self.sizer = self._create_position_sizer()
            self.logger.info(f"Updated position sizing configuration: {config}")
        except Exception as e:
            self.logger.error(f"Error updating position sizing configuration: {e}")
