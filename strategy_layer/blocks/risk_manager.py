"""
Risk Manager Building Block

Risk management building blocks for stop loss, take profit, and risk monitoring.

Author: Pro Quant Desk Trader
"""

import logging
import numpy as np
import pandas as pd
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from strategy_layer.base import StrategyError


@dataclass
class RiskConfig:
    """Configuration for risk management"""
    # Stop loss configuration
    stop_loss_enabled: bool = True
    stop_loss_percentage: float = 0.02
    stop_loss_trailing: bool = False
    stop_loss_atr_multiplier: float = 2.0
    
    # Take profit configuration
    take_profit_enabled: bool = True
    take_profit_percentage: float = 0.04
    take_profit_atr_multiplier: float = 4.0
    
    # Portfolio risk limits
    max_daily_loss: float = 0.05
    max_drawdown: float = 0.15
    max_portfolio_risk: float = 0.10
    
    # Position risk limits
    max_position_risk: float = 0.02
    max_correlation: float = 0.7
    
    # Time-based risk
    max_holding_period: Optional[int] = None  # days
    time_decay_enabled: bool = False
    
    # Volatility-based risk
    volatility_threshold: float = 0.5
    volatility_lookback: int = 20
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'stop_loss_enabled': self.stop_loss_enabled,
            'stop_loss_percentage': self.stop_loss_percentage,
            'stop_loss_trailing': self.stop_loss_trailing,
            'stop_loss_atr_multiplier': self.stop_loss_atr_multiplier,
            'take_profit_enabled': self.take_profit_enabled,
            'take_profit_percentage': self.take_profit_percentage,
            'take_profit_atr_multiplier': self.take_profit_atr_multiplier,
            'max_daily_loss': self.max_daily_loss,
            'max_drawdown': self.max_drawdown,
            'max_portfolio_risk': self.max_portfolio_risk,
            'max_position_risk': self.max_position_risk,
            'max_correlation': self.max_correlation,
            'max_holding_period': self.max_holding_period,
            'time_decay_enabled': self.time_decay_enabled,
            'volatility_threshold': self.volatility_threshold,
            'volatility_lookback': self.volatility_lookback
        }


class BaseRiskManager(ABC):
    """Base class for risk management methods"""
    
    def __init__(self, config: RiskConfig):
        self.config = config
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self._validate_config()
    
    @abstractmethod
    def should_exit_position(self, symbol: str, position: float, entry_price: float, 
                           current_price: float, market_data: pd.DataFrame, 
                           portfolio_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Determine if position should be exited"""
        pass
    
    @abstractmethod
    def calculate_stop_loss(self, entry_price: float, position: float, 
                          market_data: pd.DataFrame) -> float:
        """Calculate stop loss price"""
        pass
    
    @abstractmethod
    def calculate_take_profit(self, entry_price: float, position: float, 
                            market_data: pd.DataFrame) -> float:
        """Calculate take profit price"""
        pass
    
    def _validate_config(self):
        """Validate risk management configuration"""
        if self.config.stop_loss_percentage < 0 or self.config.stop_loss_percentage > 1:
            raise StrategyError("Stop loss percentage must be between 0 and 1")
        
        if self.config.take_profit_percentage < 0 or self.config.take_profit_percentage > 1:
            raise StrategyError("Take profit percentage must be between 0 and 1")
        
        if self.config.max_daily_loss < 0 or self.config.max_daily_loss > 1:
            raise StrategyError("Max daily loss must be between 0 and 1")
        
        if self.config.max_drawdown < 0 or self.config.max_drawdown > 1:
            raise StrategyError("Max drawdown must be between 0 and 1")


class PercentageRiskManager(BaseRiskManager):
    """Percentage-based risk management"""
    
    def should_exit_position(self, symbol: str, position: float, entry_price: float, 
                           current_price: float, market_data: pd.DataFrame, 
                           portfolio_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Check if position should be exited based on percentage risk"""
        try:
            if position == 0:
                return False, "No position"
            
            # Calculate current P&L
            if position > 0:  # Long position
                pnl_pct = (current_price - entry_price) / entry_price
            else:  # Short position
                pnl_pct = (entry_price - current_price) / entry_price
            
            # Check stop loss
            if self.config.stop_loss_enabled:
                stop_loss_pct = -self.config.stop_loss_percentage
                if pnl_pct <= stop_loss_pct:
                    return True, f"Stop loss triggered: {pnl_pct:.2%}"
            
            # Check take profit
            if self.config.take_profit_enabled:
                take_profit_pct = self.config.take_profit_percentage
                if pnl_pct >= take_profit_pct:
                    return True, f"Take profit triggered: {pnl_pct:.2%}"
            
            # Check portfolio risk limits
            if self._check_portfolio_risk_limits(portfolio_data):
                return True, "Portfolio risk limit exceeded"
            
            return False, "Position within risk limits"
            
        except Exception as e:
            self.logger.error(f"Error checking position exit: {e}")
            return False, f"Error: {e}"
    
    def calculate_stop_loss(self, entry_price: float, position: float, 
                          market_data: pd.DataFrame) -> float:
        """Calculate percentage-based stop loss"""
        try:
            if not self.config.stop_loss_enabled:
                return 0.0
            
            if position > 0:  # Long position
                stop_loss = entry_price * (1 - self.config.stop_loss_percentage)
            else:  # Short position
                stop_loss = entry_price * (1 + self.config.stop_loss_percentage)
            
            return stop_loss
            
        except Exception as e:
            self.logger.error(f"Error calculating stop loss: {e}")
            return 0.0
    
    def calculate_take_profit(self, entry_price: float, position: float, 
                            market_data: pd.DataFrame) -> float:
        """Calculate percentage-based take profit"""
        try:
            if not self.config.take_profit_enabled:
                return 0.0
            
            if position > 0:  # Long position
                take_profit = entry_price * (1 + self.config.take_profit_percentage)
            else:  # Short position
                take_profit = entry_price * (1 - self.config.take_profit_percentage)
            
            return take_profit
            
        except Exception as e:
            self.logger.error(f"Error calculating take profit: {e}")
            return 0.0
    
    def _check_portfolio_risk_limits(self, portfolio_data: Dict[str, Any]) -> bool:
        """Check portfolio risk limits"""
        try:
            # Check daily loss
            daily_return = portfolio_data.get('daily_return', 0)
            if daily_return < -self.config.max_daily_loss:
                self.logger.warning(f"Daily loss limit exceeded: {daily_return:.2%}")
                return True
            
            # Check drawdown
            current_drawdown = portfolio_data.get('current_drawdown', 0)
            if current_drawdown > self.config.max_drawdown:
                self.logger.warning(f"Drawdown limit exceeded: {current_drawdown:.2%}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking portfolio risk limits: {e}")
            return False


class ATRRiskManager(BaseRiskManager):
    """ATR-based risk management"""
    
    def should_exit_position(self, symbol: str, position: float, entry_price: float, 
                           current_price: float, market_data: pd.DataFrame, 
                           portfolio_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Check if position should be exited based on ATR"""
        try:
            if position == 0:
                return False, "No position"
            
            # Calculate ATR
            atr = self._calculate_atr(market_data)
            if atr <= 0:
                return False, "Invalid ATR"
            
            # Calculate current P&L in ATR units
            if position > 0:  # Long position
                pnl_atr = (current_price - entry_price) / atr
            else:  # Short position
                pnl_atr = (entry_price - current_price) / atr
            
            # Check stop loss
            if self.config.stop_loss_enabled:
                stop_loss_atr = -self.config.stop_loss_atr_multiplier
                if pnl_atr <= stop_loss_atr:
                    return True, f"ATR stop loss triggered: {pnl_atr:.2f} ATR"
            
            # Check take profit
            if self.config.take_profit_enabled:
                take_profit_atr = self.config.take_profit_atr_multiplier
                if pnl_atr >= take_profit_atr:
                    return True, f"ATR take profit triggered: {pnl_atr:.2f} ATR"
            
            # Check portfolio risk limits
            if self._check_portfolio_risk_limits(portfolio_data):
                return True, "Portfolio risk limit exceeded"
            
            return False, "Position within risk limits"
            
        except Exception as e:
            self.logger.error(f"Error checking position exit: {e}")
            return False, f"Error: {e}"
    
    def calculate_stop_loss(self, entry_price: float, position: float, 
                          market_data: pd.DataFrame) -> float:
        """Calculate ATR-based stop loss"""
        try:
            if not self.config.stop_loss_enabled:
                return 0.0
            
            atr = self._calculate_atr(market_data)
            if atr <= 0:
                return 0.0
            
            if position > 0:  # Long position
                stop_loss = entry_price - (atr * self.config.stop_loss_atr_multiplier)
            else:  # Short position
                stop_loss = entry_price + (atr * self.config.stop_loss_atr_multiplier)
            
            return stop_loss
            
        except Exception as e:
            self.logger.error(f"Error calculating ATR stop loss: {e}")
            return 0.0
    
    def calculate_take_profit(self, entry_price: float, position: float, 
                            market_data: pd.DataFrame) -> float:
        """Calculate ATR-based take profit"""
        try:
            if not self.config.take_profit_enabled:
                return 0.0
            
            atr = self._calculate_atr(market_data)
            if atr <= 0:
                return 0.0
            
            if position > 0:  # Long position
                take_profit = entry_price + (atr * self.config.take_profit_atr_multiplier)
            else:  # Short position
                take_profit = entry_price - (atr * self.config.take_profit_atr_multiplier)
            
            return take_profit
            
        except Exception as e:
            self.logger.error(f"Error calculating ATR take profit: {e}")
            return 0.0
    
    def _calculate_atr(self, market_data: pd.DataFrame) -> float:
        """Calculate Average True Range"""
        try:
            if len(market_data) < 14:
                return 0.0
            
            high = market_data['high']
            low = market_data['low']
            close = market_data['close']
            
            # True Range calculation
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = true_range.rolling(window=14).mean().iloc[-1]
            
            return atr
            
        except Exception as e:
            self.logger.error(f"Error calculating ATR: {e}")
            return 0.0
    
    def _check_portfolio_risk_limits(self, portfolio_data: Dict[str, Any]) -> bool:
        """Check portfolio risk limits"""
        try:
            # Check daily loss
            daily_return = portfolio_data.get('daily_return', 0)
            if daily_return < -self.config.max_daily_loss:
                self.logger.warning(f"Daily loss limit exceeded: {daily_return:.2%}")
                return True
            
            # Check drawdown
            current_drawdown = portfolio_data.get('current_drawdown', 0)
            if current_drawdown > self.config.max_drawdown:
                self.logger.warning(f"Drawdown limit exceeded: {current_drawdown:.2%}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking portfolio risk limits: {e}")
            return False


class TimeBasedRiskManager(BaseRiskManager):
    """Time-based risk management"""
    
    def should_exit_position(self, symbol: str, position: float, entry_price: float, 
                           current_price: float, market_data: pd.DataFrame, 
                           portfolio_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Check if position should be exited based on time"""
        try:
            if position == 0:
                return False, "No position"
            
            # Check holding period
            if self.config.max_holding_period:
                entry_date = portfolio_data.get('entry_date', datetime.now())
                current_date = datetime.now()
                holding_days = (current_date - entry_date).days
                
                if holding_days >= self.config.max_holding_period:
                    return True, f"Maximum holding period reached: {holding_days} days"
            
            # Check time decay
            if self.config.time_decay_enabled:
                if self._should_time_decay_exit(portfolio_data):
                    return True, "Time decay exit triggered"
            
            # Check other risk limits
            if self._check_portfolio_risk_limits(portfolio_data):
                return True, "Portfolio risk limit exceeded"
            
            return False, "Position within time limits"
            
        except Exception as e:
            self.logger.error(f"Error checking time-based exit: {e}")
            return False, f"Error: {e}"
    
    def calculate_stop_loss(self, entry_price: float, position: float, 
                          market_data: pd.DataFrame) -> float:
        """Calculate time-based stop loss (not applicable)"""
        return 0.0
    
    def calculate_take_profit(self, entry_price: float, position: float, 
                            market_data: pd.DataFrame) -> float:
        """Calculate time-based take profit (not applicable)"""
        return 0.0
    
    def _should_time_decay_exit(self, portfolio_data: Dict[str, Any]) -> bool:
        """Check if time decay exit should be triggered"""
        try:
            # Simple time decay: exit if position has been held too long
            # This could be enhanced with more sophisticated time decay models
            entry_date = portfolio_data.get('entry_date', datetime.now())
            current_date = datetime.now()
            holding_days = (current_date - entry_date).days
            
            # Exit if held for more than 30 days (example)
            return holding_days > 30
            
        except Exception as e:
            self.logger.error(f"Error checking time decay: {e}")
            return False
    
    def _check_portfolio_risk_limits(self, portfolio_data: Dict[str, Any]) -> bool:
        """Check portfolio risk limits"""
        try:
            # Check daily loss
            daily_return = portfolio_data.get('daily_return', 0)
            if daily_return < -self.config.max_daily_loss:
                self.logger.warning(f"Daily loss limit exceeded: {daily_return:.2%}")
                return True
            
            # Check drawdown
            current_drawdown = portfolio_data.get('current_drawdown', 0)
            if current_drawdown > self.config.max_drawdown:
                self.logger.warning(f"Drawdown limit exceeded: {current_drawdown:.2%}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking portfolio risk limits: {e}")
            return False


class RiskManager:
    """Main risk manager that combines different risk management methods"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.risk_managers = self._create_risk_managers()
    
    def _create_risk_managers(self) -> List[BaseRiskManager]:
        """Create risk managers based on configuration"""
        try:
            risk_managers = []
            
            # Create risk config
            risk_config = RiskConfig(
                stop_loss_enabled=self.config.get('stop_loss', {}).get('enabled', True),
                stop_loss_percentage=self.config.get('stop_loss', {}).get('percentage', 0.02),
                stop_loss_trailing=self.config.get('stop_loss', {}).get('trailing', False),
                stop_loss_atr_multiplier=self.config.get('stop_loss', {}).get('atr_multiplier', 2.0),
                take_profit_enabled=self.config.get('take_profit', {}).get('enabled', True),
                take_profit_percentage=self.config.get('take_profit', {}).get('percentage', 0.04),
                take_profit_atr_multiplier=self.config.get('take_profit', {}).get('atr_multiplier', 4.0),
                max_daily_loss=self.config.get('max_daily_loss', 0.05),
                max_drawdown=self.config.get('max_drawdown', 0.15),
                max_portfolio_risk=self.config.get('max_portfolio_risk', 0.10),
                max_position_risk=self.config.get('max_position_risk', 0.02),
                max_correlation=self.config.get('max_correlation', 0.7),
                max_holding_period=self.config.get('max_holding_period'),
                time_decay_enabled=self.config.get('time_decay_enabled', False),
                volatility_threshold=self.config.get('volatility_threshold', 0.5),
                volatility_lookback=self.config.get('volatility_lookback', 20)
            )
            
            # Add percentage-based risk manager
            risk_managers.append(PercentageRiskManager(risk_config))
            
            # Add ATR-based risk manager if ATR is configured
            if self.config.get('use_atr', False):
                risk_managers.append(ATRRiskManager(risk_config))
            
            # Add time-based risk manager if time limits are configured
            if risk_config.max_holding_period or risk_config.time_decay_enabled:
                risk_managers.append(TimeBasedRiskManager(risk_config))
            
            self.logger.info(f"Created {len(risk_managers)} risk managers")
            return risk_managers
            
        except Exception as e:
            self.logger.error(f"Error creating risk managers: {e}")
            return []
    
    def should_exit_position(self, symbol: str, position: float, entry_price: float, 
                           current_price: float, market_data: pd.DataFrame, 
                           portfolio_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Check if position should be exited using all risk managers"""
        try:
            for risk_manager in self.risk_managers:
                should_exit, reason = risk_manager.should_exit_position(
                    symbol, position, entry_price, current_price, market_data, portfolio_data
                )
                
                if should_exit:
                    return True, reason
            
            return False, "Position within all risk limits"
            
        except Exception as e:
            self.logger.error(f"Error checking position exit: {e}")
            return False, f"Error: {e}"
    
    def calculate_stop_loss(self, entry_price: float, position: float, 
                          market_data: pd.DataFrame) -> float:
        """Calculate stop loss using the first applicable risk manager"""
        try:
            for risk_manager in self.risk_managers:
                stop_loss = risk_manager.calculate_stop_loss(entry_price, position, market_data)
                if stop_loss > 0:
                    return stop_loss
            
            return 0.0
            
        except Exception as e:
            self.logger.error(f"Error calculating stop loss: {e}")
            return 0.0
    
    def calculate_take_profit(self, entry_price: float, position: float, 
                            market_data: pd.DataFrame) -> float:
        """Calculate take profit using the first applicable risk manager"""
        try:
            for risk_manager in self.risk_managers:
                take_profit = risk_manager.calculate_take_profit(entry_price, position, market_data)
                if take_profit > 0:
                    return take_profit
            
            return 0.0
            
        except Exception as e:
            self.logger.error(f"Error calculating take profit: {e}")
            return 0.0
    
    def validate_risk_limits(self, portfolio_data: Dict[str, Any]) -> bool:
        """Validate portfolio risk limits"""
        try:
            # Check daily loss
            daily_return = portfolio_data.get('daily_return', 0)
            max_daily_loss = self.config.get('max_daily_loss', 0.05)
            if daily_return < -max_daily_loss:
                self.logger.warning(f"Daily loss limit exceeded: {daily_return:.2%}")
                return False
            
            # Check drawdown
            current_drawdown = portfolio_data.get('current_drawdown', 0)
            max_drawdown = self.config.get('max_drawdown', 0.15)
            if current_drawdown > max_drawdown:
                self.logger.warning(f"Drawdown limit exceeded: {current_drawdown:.2%}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating risk limits: {e}")
            return False
    
    def get_risk_metrics(self, portfolio_data: Dict[str, Any]) -> Dict[str, float]:
        """Get current risk metrics"""
        try:
            return {
                'daily_return': portfolio_data.get('daily_return', 0),
                'current_drawdown': portfolio_data.get('current_drawdown', 0),
                'portfolio_volatility': portfolio_data.get('portfolio_volatility', 0),
                'var_95': portfolio_data.get('var_95', 0),
                'max_position_size': portfolio_data.get('max_position_size', 0)
            }
        except Exception as e:
            self.logger.error(f"Error getting risk metrics: {e}")
            return {}
