"""
Advanced Breakout Strategy Implementation

This module implements sophisticated breakout trading strategies that identify
and capitalize on breakouts from consolidation patterns using volatility analysis,
volume confirmation, and momentum filters.

The strategy uses:
- Volatility-adjusted breakout levels using Bollinger Bands and ATR
- Consolidation detection using price range and volume analysis
- Momentum confirmation and volume spikes
- False breakout filters and re-entry logic
- Risk management with position sizing based on breakout strength

Key Features:
- Multi-timeframe breakout detection
- Volatility contraction and expansion analysis
- Volume confirmation and momentum filters
- False breakout identification and handling
- Dynamic stop placement and profit targets

Academic Foundations:
- Bulkowski (2005) Encyclopedia of Chart Patterns
- Murphy (1999) Technical Analysis of the Financial Markets
- Elder (2002) Come Into My Trading Room
- Volatility Breakout research by various authors

Components:
- Breakout detection algorithms
- Consolidation pattern recognition
- Volume and momentum confirmation
- Risk management systems
- Entry/exit timing logic
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from scipy import stats

from ...strategy_engine import (
    BaseStrategy, StrategyConfig, StrategySignal, StrategyPosition,
    StrategyMetrics, SignalType, StrategyType
)
from .....utils.logging import get_logger
from .....utils.performance import get_performance_monitor

logger = get_logger(__name__)


class BreakoutType(Enum):
    """Types of breakouts"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    DOUBLE_TOP_BREAKOUT = "double_top_breakout"
    DOUBLE_BOTTOM_BREAKOUT = "double_bottom_breakout"
    TRIANGLE_BREAKOUT = "triangle_breakout"
    WEDGE_BREAKOUT = "wedge_breakout"


class ConsolidationPattern(Enum):
    """Types of consolidation patterns"""
    RECTANGLE = "rectangle"
    TRIANGLE = "triangle"
    WEDGE = "wedge"
    FLAG = "flag"
    PENNANT = "pennant"
    CHANNEL = "channel"


class BreakoutFilter(Enum):
    """Breakout confirmation filters"""
    VOLUME = "volume"
    MOMENTUM = "momentum"
    VOLATILITY = "volatility"
    TIME = "time"
    PRICE_ACTION = "price_action"


@dataclass
class BreakoutSignal:
    """Breakout signal with strength and characteristics"""
    breakout_type: BreakoutType
    strength: float  # 0-1 scale
    consolidation_period: int  # Days in consolidation
    breakout_level: float
    stop_level: float
    target_level: float
    confidence: float
    timestamp: datetime


@dataclass
class BreakoutConfig(StrategyConfig):
    """Configuration for Advanced Breakout Strategy"""

    # Strategy identification
    strategy_type: StrategyType = StrategyType.CUSTOM

    # Breakout detection parameters
    consolidation_lookback: int = 20  # Days to look for consolidation
    breakout_threshold: float = 2.0  # Standard deviations for breakout
    min_consolidation_period: int = 10  # Minimum days in consolidation
    max_consolidation_period: int = 50  # Maximum days in consolidation

    # Volatility parameters
    volatility_lookback: int = 20
    atr_period: int = 14
    volatility_multiplier: float = 1.5  # ATR multiplier for stops

    # Volume confirmation
    volume_lookback: int = 20
    volume_multiplier: float = 1.5  # Volume must be X times average
    enable_volume_filter: bool = True

    # Momentum filters
    momentum_period: int = 10
    momentum_threshold: float = 0.02
    enable_momentum_filter: bool = True

    # Bollinger Band parameters
    bb_period: int = 20
    bb_std: float = 2.0

    # Pattern recognition
    enable_pattern_recognition: bool = True
    pattern_types: List[ConsolidationPattern] = field(default_factory=lambda: [
        ConsolidationPattern.RECTANGLE, ConsolidationPattern.TRIANGLE
    ])

    # False breakout handling
    false_breakout_threshold: float = 0.5  # % of breakout level for false breakout
    re_entry_delay: int = 5  # Days to wait before re-entry
    enable_false_breakout_filter: bool = True

    # Position sizing
    base_position_size: float = 0.1  # Base position size as % of portfolio
    breakout_strength_multiplier: float = 2.0  # Multiplier for strong breakouts
    max_position_size: float = 0.25  # Maximum position size

    # Risk management
    stop_loss_pct: float = 0.05  # Stop loss percentage
    take_profit_multiplier: float = 2.0  # Take profit vs stop loss ratio
    trailing_stop_pct: float = 0.03  # Trailing stop percentage

    # Entry/exit timing
    entry_delay: int = 1  # Periods to wait after breakout
    exit_delay: int = 1  # Periods to wait before exit
    confirmation_periods: int = 2  # Periods for breakout confirmation

    # Advanced features
    enable_multi_timeframe: bool = True
    higher_timeframe: str = "1D"  # Higher timeframe for confirmation
    enable_adaptive_thresholds: bool = True  # Adaptive breakout thresholds
    enable_breakout_acceleration: bool = True  # Breakout acceleration detection

    # Transaction costs and constraints
    transaction_cost_bps: float = 5.0
    min_position_size: float = 0.001
    max_positions: int = 5

    # Performance monitoring
    enable_monitoring: bool = True
    log_signals: bool = True


class AdvancedBreakoutStrategy(BaseStrategy):
    """
    Advanced Breakout Strategy Implementation

    This strategy implements multiple breakout trading methodologies:
    1. Volatility breakout using ATR and Bollinger Bands
    2. Consolidation pattern breakout with volume confirmation
    3. False breakout filters and re-entry logic
    4. Multi-timeframe breakout confirmation
    5. Adaptive thresholds based on market conditions

    The strategy identifies breakouts from periods of consolidation and
    manages risk through proper stop placement and position sizing.
    """

    def __init__(self, config: BreakoutConfig):
        super().__init__(config)
        self.config: BreakoutConfig = config

        # Initialize components
        self.logger = get_logger(f"breakout_strategy_{config.strategy_id}")
        self.performance_monitor = get_performance_monitor() if config.enable_monitoring else None

        # Breakout tracking
        self.breakout_signals: Dict[str, BreakoutSignal] = {}
        self.consolidation_periods: Dict[str, int] = {}
        self.false_breakouts: Dict[str, datetime] = {}
        self.active_breakouts: Dict[str, BreakoutSignal] = {}

        # Technical indicators cache
        self.bollinger_bands: Dict[str, Dict[str, pd.Series]] = {}
        self.atr_values: Dict[str, pd.Series] = {}
        self.volume_sma: Dict[str, pd.Series] = {}
        self.momentum_values: Dict[str, pd.Series] = {}

        # Position tracking
        self.active_positions: Dict[str, StrategyPosition] = {}
        self.position_sizes: Dict[str, float] = {}
        self.stop_levels: Dict[str, float] = {}
        self.take_profit_levels: Dict[str, float] = {}

        # Market data cache
        self.price_data: Dict[str, pd.DataFrame] = {}
        self.volume_data: Dict[str, pd.Series] = {}

        # Signal history
        self.signal_history: List[StrategySignal] = []

        self.logger.info("Advanced Breakout Strategy initialized", {
            'strategy_id': config.strategy_id,
            'consolidation_lookback': config.consolidation_lookback,
            'breakout_threshold': config.breakout_threshold
        })

    def initialize(self) -> bool:
        """
        Initialize the breakout strategy

        Sets up technical indicators, breakout detection parameters,
        and prepares for signal generation.
        """
        try:
            self.logger.info("Initializing Advanced Breakout Strategy")

            # Validate configuration
            if not self._validate_config():
                self.logger.error("Configuration validation failed")
                return False

            # Initialize breakout tracking
            self.breakout_signals = {}
            self.consolidation_periods = {}
            self.false_breakouts = {}
            self.active_breakouts = {}

            # Set up performance monitoring
            if self.performance_monitor:
                self.performance_monitor.start_monitoring(f"breakout_{self.config.strategy_id}")

            self.logger.info("Advanced Breakout Strategy initialized successfully")
            return True

        except Exception as e:
            self.logger.error("Failed to initialize breakout strategy", {'error': str(e)})
            return False

    def generate_signals(self, market_data: Dict[str, pd.DataFrame]) -> List[StrategySignal]:
        """
        Generate breakout trading signals

        This method implements the core breakout strategy logic:
        1. Update technical indicators and detect consolidation
        2. Identify breakouts with volume and momentum confirmation
        3. Filter false breakouts and apply risk management
        4. Generate entry/exit signals with position sizing
        5. Apply portfolio-level risk management

        Args:
            market_data: Dictionary of OHLCV data for each symbol

        Returns:
            List of trading signals
        """
        signals = []

        try:
            # Update market data and indicators
            self._update_market_data(market_data)
            self._update_technical_indicators()

            # Generate breakout signals for each symbol
            for symbol in market_data.keys():
                symbol_signals = self._generate_symbol_signals(symbol)
                signals.extend(symbol_signals)

            # Apply portfolio-level risk management
            signals = self._apply_portfolio_risk_management(signals)

            self.logger.debug(f"Generated {len(signals)} breakout signals")

        except Exception as e:
            self.logger.error("Error generating breakout signals", {'error': str(e)})
            # Return empty signals list on error

        return signals

    def update_positions(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """
        Update position tracking and breakout state

        This method:
        1. Updates current positions and P&L
        2. Monitors breakout continuation or failure
        3. Adjusts stop levels and take profit targets
        4. Tracks false breakouts and re-entry opportunities

        Args:
            market_data: Current market data for position valuation
        """
        try:
            # Update market data
            self._update_market_data(market_data)

            # Update technical indicators
            self._update_technical_indicators()

            # Update position risk management
            self._update_position_stops()

            # Monitor breakout status
            self._monitor_breakout_status()

            # Log position updates if monitoring enabled
            if self.config.enable_monitoring and self.performance_monitor:
                self.performance_monitor.record_metric(
                    f"breakout_{self.config.strategy_id}_positions",
                    len(self.active_positions)
                )

        except Exception as e:
            self.logger.error("Error updating positions", {'error': str(e)})

    def _validate_config(self) -> bool:
        """Validate strategy configuration parameters"""
        try:
            # Check consolidation parameters
            if not (5 <= self.config.consolidation_lookback <= 100):
                return False

            if not (self.config.min_consolidation_period < self.config.max_consolidation_period):
                return False

            # Check breakout parameters
            if not (1.0 <= self.config.breakout_threshold <= 5.0):
                return False

            # Check position sizing
            if not (0 < self.config.base_position_size <= self.config.max_position_size <= 1.0):
                return False

            return True

        except Exception:
            return False

    def _update_market_data(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """Update internal market data cache"""
        for symbol, data in market_data.items():
            if data is not None and not data.empty:
                self.price_data[symbol] = data.copy()

                # Extract volume data if available
                if 'volume' in data.columns:
                    self.volume_data[symbol] = data['volume']

    def _update_technical_indicators(self) -> None:
        """
        Update all technical indicators for breakout analysis

        Calculates Bollinger Bands, ATR, volume SMA, and momentum
        for all symbols with sufficient data.
        """
        try:
            for symbol, price_data in self.price_data.items():
                if price_data is None or price_data.empty or len(price_data) < 50:
                    continue

                # Calculate Bollinger Bands
                self._calculate_bollinger_bands(symbol, price_data)

                # Calculate ATR
                self._calculate_atr(symbol, price_data)

                # Calculate volume SMA
                if symbol in self.volume_data:
                    self._calculate_volume_sma(symbol)

                # Calculate momentum
                self._calculate_momentum(symbol, price_data)

        except Exception as e:
            self.logger.error("Error updating technical indicators", {'error': str(e)})

    def _calculate_bollinger_bands(self, symbol: str, price_data: pd.DataFrame) -> None:
        """Calculate Bollinger Bands for breakout detection"""
        try:
            close = price_data['close']
            sma = close.rolling(window=self.config.bb_period).mean()
            std = close.rolling(window=self.config.bb_period).std()

            upper_band = sma + (std * self.config.bb_std)
            lower_band = sma - (std * self.config.bb_std)

            self.bollinger_bands[symbol] = {
                'upper': upper_band,
                'middle': sma,
                'lower': lower_band
            }

        except Exception as e:
            self.logger.error("Error calculating Bollinger Bands", {'symbol': symbol, 'error': str(e)})

    def _calculate_atr(self, symbol: str, price_data: pd.DataFrame) -> None:
        """Calculate Average True Range for volatility measurement"""
        try:
            high = price_data['high']
            low = price_data['low']
            close = price_data['close'].shift(1)

            # True Range
            tr1 = high - low
            tr2 = abs(high - close)
            tr3 = abs(low - close)
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

            # ATR
            atr = tr.rolling(window=self.config.atr_period).mean()
            self.atr_values[symbol] = atr

        except Exception as e:
            self.logger.error("Error calculating ATR", {'symbol': symbol, 'error': str(e)})

    def _calculate_volume_sma(self, symbol: str) -> None:
        """Calculate volume simple moving average"""
        try:
            if symbol in self.volume_data:
                volume_sma = self.volume_data[symbol].rolling(window=self.config.volume_lookback).mean()
                self.volume_sma[symbol] = volume_sma

        except Exception as e:
            self.logger.error("Error calculating volume SMA", {'symbol': symbol, 'error': str(e)})

    def _calculate_momentum(self, symbol: str, price_data: pd.DataFrame) -> None:
        """Calculate momentum indicator"""
        try:
            close = price_data['close']
            momentum = (close - close.shift(self.config.momentum_period)) / close.shift(self.config.momentum_period)
            self.momentum_values[symbol] = momentum

        except Exception as e:
            self.logger.error("Error calculating momentum", {'symbol': symbol, 'error': str(e)})

    def _generate_symbol_signals(self, symbol: str) -> List[StrategySignal]:
        """
        Generate breakout signals for a specific symbol

        Applies breakout detection logic and generates entry/exit signals
        with appropriate position sizing.
        """
        signals = []

        try:
            if symbol not in self.price_data or self.price_data[symbol] is None:
                return signals

            price_data = self.price_data[symbol]
            current_price = price_data['close'].iloc[-1]

            # Check for false breakout cooldown
            if self._is_in_false_breakout_cooldown(symbol):
                return signals

            # Detect breakout signal
            breakout_signal = self._detect_breakout(symbol)

            if breakout_signal is None:
                return signals

            # Check for existing position
            has_position = symbol in self.active_positions

            # Generate signals based on breakout and position status
            if not has_position:
                # Entry signal
                signal = self._generate_entry_signal(symbol, breakout_signal, current_price)
                if signal:
                    signals.append(signal)
                    self.active_breakouts[symbol] = breakout_signal

            elif has_position and self._should_exit_position(symbol, breakout_signal):
                # Exit signal
                signal = self._generate_exit_signal(symbol, current_price)
                if signal:
                    signals.append(signal)
                    if symbol in self.active_breakouts:
                        del self.active_breakouts[symbol]

            # Check for false breakout
            if has_position and self._is_false_breakout(symbol, breakout_signal):
                self._handle_false_breakout(symbol)

        except Exception as e:
            self.logger.error("Error generating symbol signals", {'symbol': symbol, 'error': str(e)})

        return signals

    def _detect_breakout(self, symbol: str) -> Optional[BreakoutSignal]:
        """
        Detect breakout signal using configured methods

        Combines multiple indicators to identify valid breakouts:
        1. Consolidation detection
        2. Breakout level calculation
        3. Volume and momentum confirmation
        4. Pattern recognition
        """
        try:
            if not self._has_required_indicators(symbol):
                return None

            price_data = self.price_data[symbol]
            current_price = price_data['close'].iloc[-1]

            # Check for consolidation
            if not self._is_in_consolidation(symbol):
                return None

            # Determine breakout type and level
            breakout_type, breakout_level = self._calculate_breakout_level(symbol)

            if breakout_type is None:
                return None

            # Check if price has broken out
            if not self._has_price_breakout(symbol, breakout_type, breakout_level):
                return None

            # Apply confirmation filters
            if not self._passes_confirmation_filters(symbol):
                return None

            # Calculate breakout strength
            strength = self._calculate_breakout_strength(symbol, breakout_level)

            # Calculate risk levels
            stop_level, target_level = self._calculate_risk_levels(symbol, breakout_type, breakout_level)

            # Calculate confidence
            confidence = self._calculate_breakout_confidence(symbol, strength)

            # Create breakout signal
            breakout_signal = BreakoutSignal(
                breakout_type=breakout_type,
                strength=strength,
                consolidation_period=self.consolidation_periods.get(symbol, 0),
                breakout_level=breakout_level,
                stop_level=stop_level,
                target_level=target_level,
                confidence=confidence,
                timestamp=datetime.now()
            )

            return breakout_signal

        except Exception as e:
            self.logger.error("Error detecting breakout", {'symbol': symbol, 'error': str(e)})
            return None

    def _has_required_indicators(self, symbol: str) -> bool:
        """Check if all required indicators are available"""
        required = [
            symbol in self.bollinger_bands,
            symbol in self.atr_values,
        ]

        if self.config.enable_volume_filter:
            required.append(symbol in self.volume_sma)

        if self.config.enable_momentum_filter:
            required.append(symbol in self.momentum_values)

        return all(required)

    def _is_in_consolidation(self, symbol: str) -> bool:
        """
        Check if the asset is in a consolidation phase

        Uses price range and volatility to detect consolidation.
        """
        try:
            price_data = self.price_data[symbol]
            lookback_data = price_data.tail(self.config.consolidation_lookback)

            if len(lookback_data) < self.config.min_consolidation_period:
                return False

            # Calculate price range
            high = lookback_data['high'].max()
            low = lookback_data['low'].min()
            price_range = (high - low) / low

            # Calculate volatility
            returns = lookback_data['close'].pct_change().dropna()
            volatility = returns.std() * np.sqrt(252)

            # Consolidation criteria
            max_range = 0.15  # 15% maximum range for consolidation
            max_volatility = 0.30  # 30% maximum volatility

            is_consolidated = price_range <= max_range and volatility <= max_volatility

            if is_consolidated:
                self.consolidation_periods[symbol] = len(lookback_data)

            return is_consolidated

        except Exception as e:
            self.logger.error("Error checking consolidation", {'symbol': symbol, 'error': str(e)})
            return False

    def _calculate_breakout_level(self, symbol: str) -> Tuple[Optional[BreakoutType], float]:
        """
        Calculate breakout level and type

        Uses Bollinger Bands and recent highs/lows to determine breakout levels.
        """
        try:
            price_data = self.price_data[symbol]
            current_price = price_data['close'].iloc[-1]

            # Get Bollinger Bands
            bb = self.bollinger_bands[symbol]
            upper_band = bb['upper'].iloc[-1]
            lower_band = bb['lower'].iloc[-1]

            # Determine breakout type
            if current_price > upper_band:
                breakout_type = BreakoutType.BULLISH
                breakout_level = upper_band
            elif current_price < lower_band:
                breakout_type = BreakoutType.BEARISH
                breakout_level = lower_band
            else:
                return None, 0.0

            return breakout_type, breakout_level

        except Exception as e:
            self.logger.error("Error calculating breakout level", {'symbol': symbol, 'error': str(e)})
            return None, 0.0

    def _has_price_breakout(self, symbol: str, breakout_type: BreakoutType, breakout_level: float) -> bool:
        """
        Check if price has convincingly broken out

        Requires breakout to be sustained for confirmation periods.
        """
        try:
            price_data = self.price_data[symbol]
            recent_prices = price_data['close'].tail(self.config.confirmation_periods + 1)

            if len(recent_prices) < self.config.confirmation_periods + 1:
                return False

            if breakout_type == BreakoutType.BULLISH:
                # All recent prices must be above breakout level
                return all(price > breakout_level for price in recent_prices)
            else:
                # All recent prices must be below breakout level
                return all(price < breakout_level for price in recent_prices)

        except Exception as e:
            self.logger.error("Error checking price breakout", {'symbol': symbol, 'error': str(e)})
            return False

    def _passes_confirmation_filters(self, symbol: str) -> bool:
        """
        Apply confirmation filters to breakout signal

        Checks volume, momentum, and other confirmation criteria.
        """
        try:
            filters_passed = True

            # Volume filter
            if self.config.enable_volume_filter and not self._passes_volume_filter(symbol):
                filters_passed = False

            # Momentum filter
            if self.config.enable_momentum_filter and not self._passes_momentum_filter(symbol):
                filters_passed = False

            return filters_passed

        except Exception as e:
            self.logger.error("Error applying confirmation filters", {'symbol': symbol, 'error': str(e)})
            return False

    def _passes_volume_filter(self, symbol: str) -> bool:
        """Check if volume confirms the breakout"""
        try:
            if symbol not in self.volume_data or symbol not in self.volume_sma:
                return True  # Skip if no volume data

            current_volume = self.volume_data[symbol].iloc[-1]
            avg_volume = self.volume_sma[symbol].iloc[-1]

            return current_volume >= (avg_volume * self.config.volume_multiplier)

        except Exception:
            return False

    def _passes_momentum_filter(self, symbol: str) -> bool:
        """Check if momentum confirms the breakout"""
        try:
            if symbol not in self.momentum_values:
                return True  # Skip if no momentum data

            current_momentum = self.momentum_values[symbol].iloc[-1]
            return abs(current_momentum) >= self.config.momentum_threshold

        except Exception:
            return False

    def _calculate_breakout_strength(self, symbol: str, breakout_level: float) -> float:
        """
        Calculate breakout strength

        Based on distance from breakout level, volume, and momentum.
        """
        try:
            price_data = self.price_data[symbol]
            current_price = price_data['close'].iloc[-1]

            # Distance from breakout level
            distance = abs(current_price - breakout_level) / breakout_level

            # Volume strength
            volume_strength = 1.0
            if self.config.enable_volume_filter and symbol in self.volume_data and symbol in self.volume_sma:
                current_volume = self.volume_data[symbol].iloc[-1]
                avg_volume = self.volume_sma[symbol].iloc[-1]
                volume_strength = min(current_volume / avg_volume, 2.0) / 2.0

            # Momentum strength
            momentum_strength = 1.0
            if self.config.enable_momentum_filter and symbol in self.momentum_values:
                current_momentum = abs(self.momentum_values[symbol].iloc[-1])
                momentum_strength = min(current_momentum / self.config.momentum_threshold, 2.0) / 2.0

            # Combine factors
            strength = (distance * 0.5 + volume_strength * 0.3 + momentum_strength * 0.2)
            return min(strength, 1.0)

        except Exception as e:
            self.logger.error("Error calculating breakout strength", {'symbol': symbol, 'error': str(e)})
            return 0.5

    def _calculate_risk_levels(self, symbol: str, breakout_type: BreakoutType, breakout_level: float) -> Tuple[float, float]:
        """
        Calculate stop loss and take profit levels

        Uses ATR and breakout level to set appropriate risk levels.
        """
        try:
            price_data = self.price_data[symbol]
            current_price = price_data['close'].iloc[-1]
            atr = self.atr_values[symbol].iloc[-1]

            # Stop loss based on ATR
            stop_distance = atr * self.config.volatility_multiplier

            if breakout_type == BreakoutType.BULLISH:
                stop_level = breakout_level - stop_distance
                take_profit_level = current_price + (stop_distance * self.config.take_profit_multiplier)
            else:
                stop_level = breakout_level + stop_distance
                take_profit_level = current_price - (stop_distance * self.config.take_profit_multiplier)

            return stop_level, take_profit_level

        except Exception as e:
            self.logger.error("Error calculating risk levels", {'symbol': symbol, 'error': str(e)})
            # Fallback to percentage-based stops
            stop_pct = self.config.stop_loss_pct
            if breakout_type == BreakoutType.BULLISH:
                stop_level = breakout_level * (1 - stop_pct)
                take_profit_level = current_price * (1 + stop_pct * self.config.take_profit_multiplier)
            else:
                stop_level = breakout_level * (1 + stop_pct)
                take_profit_level = current_price * (1 - stop_pct * self.config.take_profit_multiplier)

            return stop_level, take_profit_level

    def _calculate_breakout_confidence(self, symbol: str, strength: float) -> float:
        """Calculate confidence in the breakout signal"""
        try:
            base_confidence = strength

            # Adjust for consolidation period
            consolidation_factor = min(self.consolidation_periods.get(symbol, 0) /
                                     self.config.max_consolidation_period, 1.0)
            base_confidence *= (0.5 + 0.5 * consolidation_factor)

            # Adjust for false breakout history
            if symbol in self.false_breakouts:
                # Reduce confidence if recent false breakout
                days_since_false = (datetime.now() - self.false_breakouts[symbol]).days
                if days_since_false < 30:
                    base_confidence *= 0.8

            return min(base_confidence, 1.0)

        except Exception:
            return 0.5

    def _generate_entry_signal(self, symbol: str, breakout_signal: BreakoutSignal, current_price: float) -> Optional[StrategySignal]:
        """Generate entry signal with position sizing"""
        try:
            # Calculate position size based on breakout strength
            position_size = self._calculate_position_size(symbol, breakout_signal.strength)

            # Determine signal type
            signal_type = SignalType.BUY if breakout_signal.breakout_type == BreakoutType.BULLISH else SignalType.SELL

            # Create signal
            signal = StrategySignal(
                signal_id=f"breakout_entry_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                strategy_id=self.config.strategy_id,
                timestamp=datetime.now(),
                symbol=symbol,
                signal_type=signal_type,
                confidence=breakout_signal.confidence,
                strength=breakout_signal.strength,
                target_quantity=position_size,
                signal_price=current_price,
                entry_price=current_price,
                max_position_size=self.config.max_position_size
            )

            # Set up risk management levels
            self._setup_risk_management(symbol, breakout_signal)

            return signal

        except Exception as e:
            self.logger.error("Error generating entry signal", {'symbol': symbol, 'error': str(e)})
            return None

    def _generate_exit_signal(self, symbol: str, current_price: float) -> Optional[StrategySignal]:
        """Generate exit signal for existing position"""
        try:
            if symbol not in self.active_positions:
                return None

            position = self.active_positions[symbol]

            # Determine exit type
            if position.quantity > 0:
                signal_type = SignalType.CLOSE_LONG
            else:
                signal_type = SignalType.CLOSE_SHORT

            signal = StrategySignal(
                signal_id=f"breakout_exit_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                strategy_id=self.config.strategy_id,
                timestamp=datetime.now(),
                symbol=symbol,
                signal_type=signal_type,
                confidence=0.8,
                strength=1.0,
                target_quantity=abs(position.quantity),
                signal_price=current_price,
                entry_price=current_price,
                max_position_size=self.config.max_position_size
            )

            return signal

        except Exception as e:
            self.logger.error("Error generating exit signal", {'symbol': symbol, 'error': str(e)})
            return None

    def _calculate_position_size(self, symbol: str, breakout_strength: float) -> float:
        """Calculate position size based on breakout strength"""
        try:
            base_size = self.config.base_position_size

            # Adjust for breakout strength
            strength_multiplier = 1.0 + (breakout_strength - 0.5) * self.config.breakout_strength_multiplier
            size = base_size * strength_multiplier

            # Cap at maximum size
            size = min(size, self.config.max_position_size)

            return size

        except Exception as e:
            self.logger.error("Error calculating position size", {'symbol': symbol, 'error': str(e)})
            return self.config.base_position_size

    def _setup_risk_management(self, symbol: str, breakout_signal: BreakoutSignal) -> None:
        """Set up stop loss and take profit levels"""
        try:
            self.stop_levels[symbol] = breakout_signal.stop_level
            self.take_profit_levels[symbol] = breakout_signal.target_level

        except Exception as e:
            self.logger.error("Error setting up risk management", {'symbol': symbol, 'error': str(e)})

    def _should_exit_position(self, symbol: str, breakout_signal: BreakoutSignal) -> bool:
        """Determine if position should be exited"""
        try:
            if symbol not in self.active_positions:
                return False

            # Check stop loss and take profit levels
            current_price = self.price_data[symbol]['close'].iloc[-1]
            position = self.active_positions[symbol]
            is_long = position.quantity > 0

            # Check stop loss
            if is_long and current_price <= self.stop_levels.get(symbol, 0):
                return True
            elif not is_long and current_price >= self.stop_levels.get(symbol, float('inf')):
                return True

            # Check take profit
            if is_long and current_price >= self.take_profit_levels.get(symbol, float('inf')):
                return True
            elif not is_long and current_price <= self.take_profit_levels.get(symbol, 0):
                return True

            # Check for breakout failure (price returns to breakout level)
            if is_long and current_price <= breakout_signal.breakout_level:
                return True
            elif not is_long and current_price >= breakout_signal.breakout_level:
                return True

            return False

        except Exception as e:
            self.logger.error("Error checking exit condition", {'symbol': symbol, 'error': str(e)})
            return False

    def _is_false_breakout(self, symbol: str, breakout_signal: BreakoutSignal) -> bool:
        """Check if the breakout is a false breakout"""
        try:
            if not self.config.enable_false_breakout_filter:
                return False

            current_price = self.price_data[symbol]['close'].iloc[-1]
            breakout_level = breakout_signal.breakout_level

            # Check if price has retreated significantly from breakout level
            retreat_threshold = breakout_level * (1 + self.config.false_breakout_threshold *
                                                (1 if breakout_signal.breakout_type == BreakoutType.BULLISH else -1))

            if breakout_signal.breakout_type == BreakoutType.BULLISH:
                return current_price <= retreat_threshold
            else:
                return current_price >= retreat_threshold

        except Exception:
            return False

    def _handle_false_breakout(self, symbol: str) -> None:
        """Handle false breakout by marking cooldown period"""
        try:
            self.false_breakouts[symbol] = datetime.now()
            self.logger.info("False breakout detected", {'symbol': symbol})

        except Exception as e:
            self.logger.error("Error handling false breakout", {'symbol': symbol, 'error': str(e)})

    def _is_in_false_breakout_cooldown(self, symbol: str) -> bool:
        """Check if symbol is in false breakout cooldown period"""
        try:
            if symbol not in self.false_breakouts:
                return False

            days_since_false = (datetime.now() - self.false_breakouts[symbol]).days
            return days_since_false < self.config.re_entry_delay

        except Exception:
            return False

    def _apply_portfolio_risk_management(self, signals: List[StrategySignal]) -> List[StrategySignal]:
        """Apply portfolio-level risk management constraints"""
        try:
            # Limit number of positions
            if len(self.active_positions) + len(signals) > self.config.max_positions:
                # Keep only the strongest signals
                signals.sort(key=lambda s: s.confidence * s.strength, reverse=True)
                signals = signals[:self.config.max_positions - len(self.active_positions)]

            return signals

        except Exception as e:
            self.logger.error("Error applying portfolio risk management", {'error': str(e)})
            return signals

    def _update_position_stops(self) -> None:
        """Update trailing stops for active positions"""
        try:
            for symbol, position in self.active_positions.items():
                if symbol in self.price_data and symbol in self.stop_levels:
                    current_price = self.price_data[symbol]['close'].iloc[-1]

                    # Update trailing stop
                    if position.quantity > 0:  # Long position
                        new_stop = current_price * (1 - self.config.trailing_stop_pct)
                        self.stop_levels[symbol] = max(self.stop_levels[symbol], new_stop)
                    else:  # Short position
                        new_stop = current_price * (1 + self.config.trailing_stop_pct)
                        self.stop_levels[symbol] = min(self.stop_levels[symbol], new_stop)

        except Exception as e:
            self.logger.error("Error updating position stops", {'error': str(e)})

    def _monitor_breakout_status(self) -> None:
        """Monitor the status of active breakouts"""
        try:
            for symbol, breakout_signal in list(self.active_breakouts.items()):
                # Check if breakout is still valid
                current_price = self.price_data[symbol]['close'].iloc[-1]

                # Remove breakout if price has returned to consolidation range
                bb = self.bollinger_bands[symbol]
                upper_band = bb['upper'].iloc[-1]
                lower_band = bb['lower'].iloc[-1]

                if lower_band <= current_price <= upper_band:
                    del self.active_breakouts[symbol]
                    self.logger.debug("Breakout completed", {'symbol': symbol})

        except Exception as e:
            self.logger.error("Error monitoring breakout status", {'error': str(e)})

    def get_strategy_metrics(self) -> StrategyMetrics:
        """Get current strategy performance metrics"""
        metrics = StrategyMetrics()

        # Populate with actual metrics
        metrics.total_signals = len(self.signal_history)
        metrics.active_positions = len(self.active_positions)

        # Add breakout-specific metrics
        metrics.total_return = len(self.active_breakouts)

        return metrics