"""
Entry/Exit Logic Building Block

Entry and exit logic building blocks for determining when to enter and exit positions
based on various conditions and market signals.

Author: Pro Quant Desk Trader
"""

import logging
import numpy as np
import pandas as pd
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime, time

from strategy_layer.base import StrategyError


@dataclass
class EntryExitConfig:
    """Configuration for entry/exit logic"""
    # Entry conditions
    min_signal_strength: float = 0.3
    confirmation_period: int = 1
    volume_confirmation: bool = False
    volume_threshold: float = 1.5
    
    # Exit conditions
    signal_reversal_threshold: float = 0.2
    max_holding_period: int = 30  # days
    profit_target: float = 0.05
    
    # Time-based rules
    trading_hours_start: Optional[str] = None  # "09:30"
    trading_hours_end: Optional[str] = None    # "16:00"
    avoid_weekends: bool = True
    avoid_holidays: bool = True
    
    # Market condition filters
    volatility_filter: bool = False
    volatility_threshold: float = 0.5
    trend_filter: bool = False
    trend_period: int = 20
    
    # Risk filters
    max_correlation: float = 0.7
    max_sector_exposure: float = 0.3
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'min_signal_strength': self.min_signal_strength,
            'confirmation_period': self.confirmation_period,
            'volume_confirmation': self.volume_confirmation,
            'volume_threshold': self.volume_threshold,
            'signal_reversal_threshold': self.signal_reversal_threshold,
            'max_holding_period': self.max_holding_period,
            'profit_target': self.profit_target,
            'trading_hours_start': self.trading_hours_start,
            'trading_hours_end': self.trading_hours_end,
            'avoid_weekends': self.avoid_weekends,
            'avoid_holidays': self.avoid_holidays,
            'volatility_filter': self.volatility_filter,
            'volatility_threshold': self.volatility_threshold,
            'trend_filter': self.trend_filter,
            'trend_period': self.trend_period,
            'max_correlation': self.max_correlation,
            'max_sector_exposure': self.max_sector_exposure
        }


class BaseEntryExitLogic(ABC):
    """Base class for entry/exit logic"""
    
    def __init__(self, config: EntryExitConfig):
        self.config = config
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self._validate_config()
    
    @abstractmethod
    def should_enter_position(self, symbol: str, signal: float, market_data: pd.DataFrame, 
                            portfolio_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Determine if should enter a position"""
        pass
    
    @abstractmethod
    def should_exit_position(self, symbol: str, position: float, signal: float, 
                           market_data: pd.DataFrame, portfolio_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Determine if should exit a position"""
        pass
    
    def _validate_config(self):
        """Validate entry/exit configuration"""
        if self.config.min_signal_strength < 0 or self.config.min_signal_strength > 1:
            raise StrategyError("Min signal strength must be between 0 and 1")
        
        if self.config.confirmation_period < 0:
            raise StrategyError("Confirmation period must be non-negative")
        
        if self.config.max_holding_period < 1:
            raise StrategyError("Max holding period must be at least 1 day")


class SignalThresholdLogic(BaseEntryExitLogic):
    """Signal threshold-based entry/exit logic"""
    
    def should_enter_position(self, symbol: str, signal: float, market_data: pd.DataFrame, 
                            portfolio_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Check if should enter position based on signal threshold"""
        try:
            # Check signal strength
            if abs(signal) < self.config.min_signal_strength:
                return False, f"Signal too weak: {signal:.3f}"
            
            # Check confirmation period
            if self.config.confirmation_period > 0:
                if not self._check_signal_confirmation(signal, market_data):
                    return False, "Signal confirmation failed"
            
            # Check volume confirmation
            if self.config.volume_confirmation:
                if not self._check_volume_confirmation(market_data):
                    return False, "Volume confirmation failed"
            
            # Check time-based rules
            if not self._check_trading_hours():
                return False, "Outside trading hours"
            
            # Check market condition filters
            if not self._check_market_conditions(market_data):
                return False, "Market conditions unfavorable"
            
            # Check risk filters
            if not self._check_risk_filters(symbol, portfolio_data):
                return False, "Risk filters not met"
            
            return True, f"Entry signal confirmed: {signal:.3f}"
            
        except Exception as e:
            self.logger.error(f"Error checking entry conditions: {e}")
            return False, f"Error: {e}"
    
    def should_exit_position(self, symbol: str, position: float, signal: float, 
                           market_data: pd.DataFrame, portfolio_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Check if should exit position based on signal threshold"""
        try:
            if position == 0:
                return False, "No position to exit"
            
            # Check signal reversal
            if abs(signal) < self.config.signal_reversal_threshold:
                return True, f"Signal reversal: {signal:.3f}"
            
            # Check holding period
            if self._check_holding_period_exceeded(portfolio_data):
                return True, "Maximum holding period exceeded"
            
            # Check profit target
            if self._check_profit_target_reached(position, portfolio_data):
                return True, "Profit target reached"
            
            # Check time-based rules
            if not self._check_trading_hours():
                return True, "Outside trading hours"
            
            return False, "Position should be maintained"
            
        except Exception as e:
            self.logger.error(f"Error checking exit conditions: {e}")
            return False, f"Error: {e}"
    
    def _check_signal_confirmation(self, current_signal: float, market_data: pd.DataFrame) -> bool:
        """Check if signal is confirmed over the confirmation period"""
        try:
            if len(market_data) < self.config.confirmation_period:
                return False
            
            # Check if signal has been consistent over the confirmation period
            # This is a simplified implementation - could be enhanced with more sophisticated logic
            return abs(current_signal) >= self.config.min_signal_strength
            
        except Exception as e:
            self.logger.error(f"Error checking signal confirmation: {e}")
            return False
    
    def _check_volume_confirmation(self, market_data: pd.DataFrame) -> bool:
        """Check if volume confirms the signal"""
        try:
            if 'volume' not in market_data.columns:
                return True  # No volume data available
            
            if len(market_data) < 20:
                return True  # Insufficient data
            
            current_volume = market_data['volume'].iloc[-1]
            avg_volume = market_data['volume'].rolling(window=20).mean().iloc[-1]
            
            if avg_volume <= 0:
                return True  # Invalid average volume
            
            volume_ratio = current_volume / avg_volume
            return volume_ratio >= self.config.volume_threshold
            
        except Exception as e:
            self.logger.error(f"Error checking volume confirmation: {e}")
            return True  # Default to allowing entry
    
    def _check_trading_hours(self) -> bool:
        """Check if current time is within trading hours"""
        try:
            if not self.config.trading_hours_start or not self.config.trading_hours_end:
                return True  # No trading hours specified
            
            current_time = datetime.now().time()
            start_time = time.fromisoformat(self.config.trading_hours_start)
            end_time = time.fromisoformat(self.config.trading_hours_end)
            
            return start_time <= current_time <= end_time
            
        except Exception as e:
            self.logger.error(f"Error checking trading hours: {e}")
            return True  # Default to allowing trading
    
    def _check_market_conditions(self, market_data: pd.DataFrame) -> bool:
        """Check if market conditions are favorable"""
        try:
            # Check volatility filter
            if self.config.volatility_filter:
                if not self._check_volatility_condition(market_data):
                    return False
            
            # Check trend filter
            if self.config.trend_filter:
                if not self._check_trend_condition(market_data):
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking market conditions: {e}")
            return True  # Default to allowing trading
    
    def _check_volatility_condition(self, market_data: pd.DataFrame) -> bool:
        """Check if volatility is within acceptable range"""
        try:
            if len(market_data) < 20:
                return True
            
            # Calculate rolling volatility
            returns = market_data['close'].pct_change().dropna()
            volatility = returns.rolling(window=20).std().iloc[-1]
            
            # Annualize volatility
            annualized_volatility = volatility * np.sqrt(252)
            
            return annualized_volatility <= self.config.volatility_threshold
            
        except Exception as e:
            self.logger.error(f"Error checking volatility condition: {e}")
            return True
    
    def _check_trend_condition(self, market_data: pd.DataFrame) -> bool:
        """Check if trend is favorable"""
        try:
            if len(market_data) < self.config.trend_period:
                return True
            
            # Calculate trend using simple moving average
            sma = market_data['close'].rolling(window=self.config.trend_period).mean()
            current_price = market_data['close'].iloc[-1]
            current_sma = sma.iloc[-1]
            
            # Trend is favorable if price is above SMA (for long positions)
            return current_price > current_sma
            
        except Exception as e:
            self.logger.error(f"Error checking trend condition: {e}")
            return True
    
    def _check_risk_filters(self, symbol: str, portfolio_data: Dict[str, Any]) -> bool:
        """Check risk filters"""
        try:
            # Check correlation limit
            if not self._check_correlation_limit(symbol, portfolio_data):
                return False
            
            # Check sector exposure limit
            if not self._check_sector_exposure_limit(symbol, portfolio_data):
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking risk filters: {e}")
            return True  # Default to allowing trading
    
    def _check_correlation_limit(self, symbol: str, portfolio_data: Dict[str, Any]) -> bool:
        """Check if adding this symbol would exceed correlation limit"""
        try:
            # This is a simplified implementation
            # In practice, you would calculate correlation with existing positions
            current_positions = portfolio_data.get('positions', {})
            
            if len(current_positions) == 0:
                return True  # No existing positions
            
            # For now, assume correlation is acceptable
            # This could be enhanced with actual correlation calculation
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking correlation limit: {e}")
            return True
    
    def _check_sector_exposure_limit(self, symbol: str, portfolio_data: Dict[str, Any]) -> bool:
        """Check if adding this symbol would exceed sector exposure limit"""
        try:
            # This is a simplified implementation
            # In practice, you would check sector classification
            current_positions = portfolio_data.get('positions', {})
            
            if len(current_positions) == 0:
                return True  # No existing positions
            
            # For now, assume sector exposure is acceptable
            # This could be enhanced with actual sector analysis
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking sector exposure limit: {e}")
            return True
    
    def _check_holding_period_exceeded(self, portfolio_data: Dict[str, Any]) -> bool:
        """Check if maximum holding period has been exceeded"""
        try:
            entry_date = portfolio_data.get('entry_date', datetime.now())
            current_date = datetime.now()
            holding_days = (current_date - entry_date).days
            
            return holding_days >= self.config.max_holding_period
            
        except Exception as e:
            self.logger.error(f"Error checking holding period: {e}")
            return False
    
    def _check_profit_target_reached(self, position: float, portfolio_data: Dict[str, Any]) -> bool:
        """Check if profit target has been reached"""
        try:
            if position == 0:
                return False
            
            entry_price = portfolio_data.get('entry_price', 0)
            current_price = portfolio_data.get('current_price', 0)
            
            if entry_price <= 0 or current_price <= 0:
                return False
            
            if position > 0:  # Long position
                profit_pct = (current_price - entry_price) / entry_price
            else:  # Short position
                profit_pct = (entry_price - current_price) / entry_price
            
            return profit_pct >= self.config.profit_target
            
        except Exception as e:
            self.logger.error(f"Error checking profit target: {e}")
            return False


class TimeBasedLogic(BaseEntryExitLogic):
    """Time-based entry/exit logic"""
    
    def should_enter_position(self, symbol: str, signal: float, market_data: pd.DataFrame, 
                            portfolio_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Check if should enter position based on time rules"""
        try:
            # Check if it's a good time to enter
            if not self._is_good_entry_time():
                return False, "Not a good time to enter"
            
            # Check signal strength
            if abs(signal) < self.config.min_signal_strength:
                return False, f"Signal too weak: {signal:.3f}"
            
            return True, f"Time-based entry signal: {signal:.3f}"
            
        except Exception as e:
            self.logger.error(f"Error checking time-based entry: {e}")
            return False, f"Error: {e}"
    
    def should_exit_position(self, symbol: str, position: float, signal: float, 
                           market_data: pd.DataFrame, portfolio_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Check if should exit position based on time rules"""
        try:
            if position == 0:
                return False, "No position to exit"
            
            # Check if it's time to exit
            if self._is_time_to_exit():
                return True, "Time-based exit"
            
            # Check holding period
            if self._check_holding_period_exceeded(portfolio_data):
                return True, "Maximum holding period exceeded"
            
            return False, "Position should be maintained"
            
        except Exception as e:
            self.logger.error(f"Error checking time-based exit: {e}")
            return False, f"Error: {e}"
    
    def _is_good_entry_time(self) -> bool:
        """Check if it's a good time to enter positions"""
        try:
            current_time = datetime.now()
            
            # Avoid weekends
            if self.config.avoid_weekends and current_time.weekday() >= 5:
                return False
            
            # Check trading hours
            if not self._check_trading_hours():
                return False
            
            # Avoid market open/close (first/last 30 minutes)
            current_time_str = current_time.strftime("%H:%M")
            if current_time_str < "10:00" or current_time_str > "15:30":
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking entry time: {e}")
            return True
    
    def _is_time_to_exit(self) -> bool:
        """Check if it's time to exit positions"""
        try:
            current_time = datetime.now()
            
            # Exit before market close
            current_time_str = current_time.strftime("%H:%M")
            if current_time_str >= "15:45":
                return True
            
            # Exit on Fridays before weekend
            if self.config.avoid_weekends and current_time.weekday() == 4 and current_time_str >= "15:00":
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking exit time: {e}")
            return False
    
    def _check_trading_hours(self) -> bool:
        """Check if current time is within trading hours"""
        try:
            if not self.config.trading_hours_start or not self.config.trading_hours_end:
                return True
            
            current_time = datetime.now().time()
            start_time = time.fromisoformat(self.config.trading_hours_start)
            end_time = time.fromisoformat(self.config.trading_hours_end)
            
            return start_time <= current_time <= end_time
            
        except Exception as e:
            self.logger.error(f"Error checking trading hours: {e}")
            return True
    
    def _check_holding_period_exceeded(self, portfolio_data: Dict[str, Any]) -> bool:
        """Check if maximum holding period has been exceeded"""
        try:
            entry_date = portfolio_data.get('entry_date', datetime.now())
            current_date = datetime.now()
            holding_days = (current_date - entry_date).days
            
            return holding_days >= self.config.max_holding_period
            
        except Exception as e:
            self.logger.error(f"Error checking holding period: {e}")
            return False


class EntryExitLogic:
    """Main entry/exit logic that combines different logic methods"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logic_components = self._create_logic_components()
    
    def _create_logic_components(self) -> List[BaseEntryExitLogic]:
        """Create entry/exit logic components"""
        try:
            logic_components = []
            
            # Create config
            logic_config = EntryExitConfig(
                min_signal_strength=self.config.get('min_signal_strength', 0.3),
                confirmation_period=self.config.get('confirmation_period', 1),
                volume_confirmation=self.config.get('volume_confirmation', False),
                volume_threshold=self.config.get('volume_threshold', 1.5),
                signal_reversal_threshold=self.config.get('signal_reversal_threshold', 0.2),
                max_holding_period=self.config.get('max_holding_period', 30),
                profit_target=self.config.get('profit_target', 0.05),
                trading_hours_start=self.config.get('trading_hours_start'),
                trading_hours_end=self.config.get('trading_hours_end'),
                avoid_weekends=self.config.get('avoid_weekends', True),
                avoid_holidays=self.config.get('avoid_holidays', True),
                volatility_filter=self.config.get('volatility_filter', False),
                volatility_threshold=self.config.get('volatility_threshold', 0.5),
                trend_filter=self.config.get('trend_filter', False),
                trend_period=self.config.get('trend_period', 20),
                max_correlation=self.config.get('max_correlation', 0.7),
                max_sector_exposure=self.config.get('max_sector_exposure', 0.3)
            )
            
            # Add signal threshold logic
            logic_components.append(SignalThresholdLogic(logic_config))
            
            # Add time-based logic if time rules are configured
            if (logic_config.trading_hours_start or logic_config.trading_hours_end or 
                logic_config.avoid_weekends or logic_config.avoid_holidays):
                logic_components.append(TimeBasedLogic(logic_config))
            
            self.logger.info(f"Created {len(logic_components)} entry/exit logic components")
            return logic_components
            
        except Exception as e:
            self.logger.error(f"Error creating logic components: {e}")
            return []
    
    def should_enter_position(self, symbol: str, signal: float, market_data: pd.DataFrame, 
                            portfolio_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Check if should enter position using all logic components"""
        try:
            for logic in self.logic_components:
                should_enter, reason = logic.should_enter_position(
                    symbol, signal, market_data, portfolio_data
                )
                
                if not should_enter:
                    return False, reason
            
            return True, "All entry conditions met"
            
        except Exception as e:
            self.logger.error(f"Error checking entry conditions: {e}")
            return False, f"Error: {e}"
    
    def should_exit_position(self, symbol: str, position: float, signal: float, 
                           market_data: pd.DataFrame, portfolio_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Check if should exit position using all logic components"""
        try:
            for logic in self.logic_components:
                should_exit, reason = logic.should_exit_position(
                    symbol, position, signal, market_data, portfolio_data
                )
                
                if should_exit:
                    return True, reason
            
            return False, "All exit conditions met"
            
        except Exception as e:
            self.logger.error(f"Error checking exit conditions: {e}")
            return False, f"Error: {e}"
    
    def get_entry_conditions(self) -> Dict[str, Any]:
        """Get current entry conditions configuration"""
        try:
            return {
                'min_signal_strength': self.config.get('min_signal_strength', 0.3),
                'confirmation_period': self.config.get('confirmation_period', 1),
                'volume_confirmation': self.config.get('volume_confirmation', False),
                'trading_hours': {
                    'start': self.config.get('trading_hours_start'),
                    'end': self.config.get('trading_hours_end')
                }
            }
        except Exception as e:
            self.logger.error(f"Error getting entry conditions: {e}")
            return {}
    
    def get_exit_conditions(self) -> Dict[str, Any]:
        """Get current exit conditions configuration"""
        try:
            return {
                'signal_reversal_threshold': self.config.get('signal_reversal_threshold', 0.2),
                'max_holding_period': self.config.get('max_holding_period', 30),
                'profit_target': self.config.get('profit_target', 0.05)
            }
        except Exception as e:
            self.logger.error(f"Error getting exit conditions: {e}")
            return {}
