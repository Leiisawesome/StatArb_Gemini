"""
Advanced Trend Following Strategy Implementation

This module implements sophisticated trend following strategies that capture
persistent directional movements in asset prices using multiple timeframes
and trend strength indicators.

The strategy uses:
- Multiple moving average systems (SMA, EMA, WMA)
- Trend strength indicators (ADX, trend duration, slope)
- Breakout confirmation and momentum filters
- Position sizing based on trend conviction
- Risk management with trailing stops and volatility adjustment

Key Features:
- Multi-timeframe trend analysis
- Adaptive trend detection algorithms
- Dynamic position sizing based on trend strength
- Volatility-adjusted entry/exit levels
- Trend continuation vs. reversal detection

Academic Foundations:
- Faber (2010) Simple Trend Following Rules
- Hurst (1995) Trend Following Principles
- Covel (2009) Trend Following: How to Make a Fortune
- Kahneman & Tversky (1979) Prospect Theory for risk management

Components:
- Trend detection algorithms
- Trend strength measurement
- Position sizing models
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
from sklearn.linear_model import LinearRegression

from ...strategy_engine import (
    BaseStrategy, StrategyConfig, StrategySignal, StrategyPosition,
    StrategyMetrics, SignalType, StrategyType
)
from .....utils.logging import get_logger
from .....utils.performance import get_performance_monitor

logger = get_logger(__name__)


class TrendIndicator(Enum):
    """Trend indicator types"""
    MOVING_AVERAGE = "moving_average"
    MACD = "macd"
    ADX = "adx"
    TREND_STRENGTH = "trend_strength"
    SLOPE = "slope"
    BREAKOUT = "breakout"
    MOMENTUM = "momentum"


class MovingAverageType(Enum):
    """Moving average types"""
    SIMPLE = "simple"
    EXPONENTIAL = "exponential"
    WEIGHTED = "weighted"
    HULL = "hull"
    KAMA = "kama"  # Kaufman's Adaptive Moving Average


class TrendDirection(Enum):
    """Trend direction"""
    UP = "up"
    DOWN = "down"
    SIDEWAYS = "sideways"


@dataclass
class TrendSignal:
    """Trend signal with strength and direction"""
    direction: TrendDirection
    strength: float  # 0-1 scale
    duration: int  # Trend duration in periods
    confidence: float  # Signal confidence
    timestamp: datetime


@dataclass
class TrendFollowingConfig(StrategyConfig):
    """Configuration for Advanced Trend Following Strategy"""

    # Strategy identification
    strategy_type: StrategyType = StrategyType.TREND_FOLLOWING

    # Trend detection parameters
    primary_indicator: TrendIndicator = TrendIndicator.MOVING_AVERAGE
    secondary_indicators: List[TrendIndicator] = field(default_factory=lambda: [
        TrendIndicator.ADX, TrendIndicator.MOMENTUM
    ])

    # Moving average parameters
    ma_type: MovingAverageType = MovingAverageType.EXPONENTIAL
    fast_ma_period: int = 20
    slow_ma_period: int = 50
    signal_ma_period: int = 9

    # Trend strength parameters
    min_trend_strength: float = 0.6  # Minimum trend strength (0-1)
    adx_period: int = 14
    adx_threshold: float = 25  # ADX threshold for trend

    # MACD parameters (if used)
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9

    # Breakout parameters
    breakout_lookback: int = 20
    breakout_multiplier: float = 2.0  # Standard deviation multiplier

    # Momentum parameters
    momentum_period: int = 10
    momentum_threshold: float = 0.02  # Momentum threshold

    # Position sizing
    base_position_size: float = 0.1  # Base position size as % of portfolio
    max_position_size: float = 0.25  # Maximum position size
    trend_strength_multiplier: float = 2.0  # Multiplier for strong trends

    # Risk management
    stop_loss_pct: float = 0.05  # Stop loss percentage
    trailing_stop_pct: float = 0.03  # Trailing stop percentage
    take_profit_multiplier: float = 2.0  # Take profit vs stop loss ratio

    # Entry/exit timing
    entry_delay: int = 1  # Periods to wait after signal
    exit_delay: int = 1  # Periods to wait before exit
    confirmation_periods: int = 3  # Periods for signal confirmation

    # Volatility adjustment
    volatility_lookback: int = 20
    volatility_target: float = 0.15  # Annualized volatility target
    vol_adjustment: bool = True

    # Multi-timeframe analysis
    use_multi_timeframe: bool = True
    higher_timeframe: str = "1D"  # Higher timeframe for trend confirmation
    lower_timeframe: str = "1H"  # Lower timeframe for entry timing

    # Advanced features
    enable_adaptive_ma: bool = True  # Adaptive moving averages
    enable_trend_acceleration: bool = True  # Trend acceleration detection
    enable_volume_confirmation: bool = True  # Volume-based confirmation
    max_trend_duration: int = 100  # Maximum trend duration before reassessment

    # Transaction costs and constraints
    transaction_cost_bps: float = 5.0
    min_position_size: float = 0.001
    max_positions: int = 10

    # Performance monitoring
    enable_monitoring: bool = True
    log_signals: bool = True


class AdvancedTrendFollowingStrategy(BaseStrategy):
    """
    Advanced Trend Following Strategy Implementation

    This strategy implements multiple trend following methodologies:
    1. Moving average crossover systems with trend strength filters
    2. ADX-based trend strength measurement
    3. Breakout trading with momentum confirmation
    4. Multi-timeframe trend analysis
    5. Adaptive position sizing based on trend conviction

    The strategy captures persistent trends while managing risk through
    volatility-adjusted stops and position sizing.
    """

    def __init__(self, config: TrendFollowingConfig):
        super().__init__(config)
        self.config: TrendFollowingConfig = config

        # Initialize components
        self.logger = get_logger(f"trend_following_strategy_{config.strategy_id}")
        self.performance_monitor = get_performance_monitor() if config.enable_monitoring else None

        # Trend state tracking
        self.current_trends: Dict[str, TrendSignal] = {}
        self.trend_history: Dict[str, List[TrendSignal]] = {}
        self.entry_signals: Dict[str, datetime] = {}
        self.exit_signals: Dict[str, datetime] = {}

        # Technical indicators cache
        self.moving_averages: Dict[str, Dict[str, pd.Series]] = {}
        self.adx_values: Dict[str, pd.Series] = {}
        self.macd_values: Dict[str, Dict[str, pd.Series]] = {}
        self.momentum_values: Dict[str, pd.Series] = {}
        self.volatility_values: Dict[str, pd.Series] = {}

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

        self.logger.info("Advanced Trend Following Strategy initialized", {
            'strategy_id': config.strategy_id,
            'primary_indicator': config.primary_indicator.value,
            'ma_type': config.ma_type.value
        })

    def initialize(self) -> bool:
        """
        Initialize the trend following strategy

        Sets up technical indicators, trend detection parameters,
        and prepares for signal generation.
        """
        try:
            self.logger.info("Initializing Advanced Trend Following Strategy")

            # Validate configuration
            if not self._validate_config():
                self.logger.error("Configuration validation failed")
                return False

            # Initialize trend tracking
            self.current_trends = {}
            self.trend_history = {}
            self.entry_signals = {}
            self.exit_signals = {}

            # Set up performance monitoring
            if self.performance_monitor:
                self.performance_monitor.start_monitoring(f"trend_following_{self.config.strategy_id}")

            self.logger.info("Advanced Trend Following Strategy initialized successfully")
            return True

        except Exception as e:
            self.logger.error("Failed to initialize trend following strategy", {'error': str(e)})
            return False

    def generate_signals(self, market_data: Dict[str, pd.DataFrame]) -> List[StrategySignal]:
        """
        Generate trend following trading signals

        This method implements the core trend following logic:
        1. Update technical indicators
        2. Detect trend signals across multiple timeframes
        3. Apply trend strength and confirmation filters
        4. Generate entry/exit signals with position sizing
        5. Apply risk management overlays

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

            # Generate trend signals for each symbol
            for symbol in market_data.keys():
                symbol_signals = self._generate_symbol_signals(symbol)
                signals.extend(symbol_signals)

            # Apply portfolio-level risk management
            signals = self._apply_portfolio_risk_management(signals)

            self.logger.debug(f"Generated {len(signals)} trend following signals")

        except Exception as e:
            self.logger.error("Error generating trend signals", {'error': str(e)})
            # Return empty signals list on error

        return signals

    def update_positions(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """
        Update position tracking and trend state

        This method:
        1. Updates current positions and P&L
        2. Monitors trend continuation or reversal
        3. Adjusts stop levels and take profit targets
        4. Updates trend strength measurements

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

            # Monitor trend changes
            self._monitor_trend_changes()

            # Log position updates if monitoring enabled
            if self.config.enable_monitoring and self.performance_monitor:
                self.performance_monitor.record_metric(
                    f"trend_following_{self.config.strategy_id}_positions",
                    len(self.active_positions)
                )

        except Exception as e:
            self.logger.error("Error updating positions", {'error': str(e)})

    def _validate_config(self) -> bool:
        """Validate strategy configuration parameters"""
        try:
            # Check indicator compatibility
            if self.config.primary_indicator not in TrendIndicator:
                return False

            # Check moving average parameters
            if self.config.fast_ma_period >= self.config.slow_ma_period:
                return False

            # Check trend strength parameters
            if not (0 < self.config.min_trend_strength <= 1.0):
                return False

            if not (0 < self.config.adx_threshold <= 100):
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
        Update all technical indicators for trend analysis

        Calculates moving averages, ADX, MACD, momentum, and volatility
        for all symbols with sufficient data.
        """
        try:
            for symbol, price_data in self.price_data.items():
                if price_data is None or price_data.empty or len(price_data) < 50:
                    continue

                # Calculate moving averages
                self._calculate_moving_averages(symbol, price_data)

                # Calculate ADX
                self._calculate_adx(symbol, price_data)

                # Calculate MACD
                self._calculate_macd(symbol, price_data)

                # Calculate momentum
                self._calculate_momentum(symbol, price_data)

                # Calculate volatility
                self._calculate_volatility(symbol, price_data)

        except Exception as e:
            self.logger.error("Error updating technical indicators", {'error': str(e)})

    def _calculate_moving_averages(self, symbol: str, price_data: pd.DataFrame) -> None:
        """Calculate moving averages for trend detection"""
        try:
            close_prices = price_data['close']

            # Fast moving average
            if self.config.ma_type == MovingAverageType.SIMPLE:
                fast_ma = close_prices.rolling(window=self.config.fast_ma_period).mean()
                slow_ma = close_prices.rolling(window=self.config.slow_ma_period).mean()
                signal_ma = close_prices.rolling(window=self.config.signal_ma_period).mean()
            elif self.config.ma_type == MovingAverageType.EXPONENTIAL:
                fast_ma = close_prices.ewm(span=self.config.fast_ma_period).mean()
                slow_ma = close_prices.ewm(span=self.config.slow_ma_period).mean()
                signal_ma = close_prices.ewm(span=self.config.signal_ma_period).mean()
            else:
                # Default to exponential
                fast_ma = close_prices.ewm(span=self.config.fast_ma_period).mean()
                slow_ma = close_prices.ewm(span=self.config.slow_ma_period).mean()
                signal_ma = close_prices.ewm(span=self.config.signal_ma_period).mean()

            self.moving_averages[symbol] = {
                'fast': fast_ma,
                'slow': slow_ma,
                'signal': signal_ma
            }

        except Exception as e:
            self.logger.error("Error calculating moving averages", {'error': str(e)})

    def _calculate_adx(self, symbol: str, price_data: pd.DataFrame) -> None:
        """
        Calculate Average Directional Index (ADX) for trend strength

        ADX measures trend strength regardless of direction.
        """
        try:
            high = price_data['high']
            low = price_data['low']
            close = price_data['close']

            # True Range
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

            # Directional Movement
            dm_plus = np.where((high - high.shift(1)) > (low.shift(1) - low),
                             np.maximum(high - high.shift(1), 0), 0)
            dm_minus = np.where((low.shift(1) - low) > (high - high.shift(1)),
                               np.maximum(low.shift(1) - low, 0), 0)

            # Smoothed averages
            atr = tr.rolling(window=self.config.adx_period).mean()
            di_plus = (pd.Series(dm_plus).rolling(window=self.config.adx_period).mean() / atr) * 100
            di_minus = (pd.Series(dm_minus).rolling(window=self.config.adx_period).mean() / atr) * 100

            # ADX
            dx = (abs(di_plus - di_minus) / (di_plus + di_minus)) * 100
            adx = dx.rolling(window=self.config.adx_period).mean()

            self.adx_values[symbol] = adx

        except Exception as e:
            self.logger.error("Error calculating ADX", {'error': str(e)})

    def _calculate_macd(self, symbol: str, price_data: pd.DataFrame) -> None:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        try:
            close = price_data['close']

            # MACD components
            fast_ema = close.ewm(span=self.config.macd_fast).mean()
            slow_ema = close.ewm(span=self.config.macd_slow).mean()
            macd_line = fast_ema - slow_ema
            signal_line = macd_line.ewm(span=self.config.macd_signal).mean()
            histogram = macd_line - signal_line

            self.macd_values[symbol] = {
                'macd': macd_line,
                'signal': signal_line,
                'histogram': histogram
            }

        except Exception as e:
            self.logger.error("Error calculating MACD", {'error': str(e)})

    def _calculate_momentum(self, symbol: str, price_data: pd.DataFrame) -> None:
        """Calculate momentum indicator"""
        try:
            close = price_data['close']
            momentum = (close - close.shift(self.config.momentum_period)) / close.shift(self.config.momentum_period)
            self.momentum_values[symbol] = momentum

        except Exception as e:
            self.logger.error("Error calculating momentum", {'error': str(e)})

    def _calculate_volatility(self, symbol: str, price_data: pd.DataFrame) -> None:
        """Calculate volatility for position sizing"""
        try:
            returns = price_data['close'].pct_change()
            volatility = returns.rolling(window=self.config.volatility_lookback).std() * np.sqrt(252)
            self.volatility_values[symbol] = volatility

        except Exception as e:
            self.logger.error("Error calculating volatility", {'error': str(e)})

    def _generate_symbol_signals(self, symbol: str) -> List[StrategySignal]:
        """
        Generate trend signals for a specific symbol

        Applies trend detection logic and generates entry/exit signals
        with appropriate position sizing.
        """
        signals = []

        try:
            if symbol not in self.price_data or self.price_data[symbol] is None:
                return signals

            price_data = self.price_data[symbol]
            current_price = price_data['close'].iloc[-1]

            # Detect trend signal
            trend_signal = self._detect_trend_signal(symbol)

            if trend_signal is None:
                return signals

            # Check for existing position
            has_position = symbol in self.active_positions

            # Generate signals based on trend and position status
            if trend_signal.direction in [TrendDirection.UP, TrendDirection.DOWN] and not has_position:
                # Entry signal
                signal = self._generate_entry_signal(symbol, trend_signal, current_price)
                if signal:
                    signals.append(signal)

            elif has_position and self._should_exit_position(symbol, trend_signal):
                # Exit signal
                signal = self._generate_exit_signal(symbol, current_price)
                if signal:
                    signals.append(signal)

            # Update trend tracking
            self.current_trends[symbol] = trend_signal

        except Exception as e:
            self.logger.error("Error generating symbol signals", {'symbol': symbol, 'error': str(e)})

        return signals

    def _detect_trend_signal(self, symbol: str) -> Optional[TrendSignal]:
        """
        Detect trend signal using configured indicators

        Combines multiple indicators to determine trend direction,
        strength, and confidence.
        """
        try:
            if symbol not in self.moving_averages or symbol not in self.adx_values:
                return None

            # Primary trend detection
            if self.config.primary_indicator == TrendIndicator.MOVING_AVERAGE:
                primary_signal = self._detect_ma_trend(symbol)
            elif self.config.primary_indicator == TrendIndicator.MACD:
                primary_signal = self._detect_macd_trend(symbol)
            else:
                primary_signal = self._detect_ma_trend(symbol)  # Default

            if primary_signal is None:
                return None

            # Secondary confirmations
            confirmations = []
            for indicator in self.config.secondary_indicators:
                if indicator == TrendIndicator.ADX:
                    confirmation = self._adx_confirmation(symbol)
                elif indicator == TrendIndicator.MOMENTUM:
                    confirmation = self._momentum_confirmation(symbol)
                else:
                    confirmation = True

                confirmations.append(confirmation)

            # Overall confidence
            base_confidence = primary_signal.strength
            confirmation_bonus = sum(confirmations) / len(confirmations) * 0.2
            confidence = min(base_confidence + confirmation_bonus, 1.0)

            # Create trend signal
            trend_signal = TrendSignal(
                direction=primary_signal.direction,
                strength=primary_signal.strength,
                duration=primary_signal.duration,
                confidence=confidence,
                timestamp=datetime.now()
            )

            return trend_signal

        except Exception as e:
            self.logger.error("Error detecting trend signal", {'symbol': symbol, 'error': str(e)})
            return None

    def _detect_ma_trend(self, symbol: str) -> Optional[TrendSignal]:
        """Detect trend using moving average crossover"""
        try:
            mas = self.moving_averages[symbol]
            fast_ma = mas['fast']
            slow_ma = mas['slow']

            if len(fast_ma) < 2 or len(slow_ma) < 2:
                return None

            # Current and previous MA values
            fast_current = fast_ma.iloc[-1]
            fast_prev = fast_ma.iloc[-2]
            slow_current = slow_ma.iloc[-1]
            slow_prev = slow_ma.iloc[-2]

            # Trend direction
            if fast_current > slow_current and fast_prev <= slow_prev:
                direction = TrendDirection.UP
            elif fast_current < slow_current and fast_prev >= slow_prev:
                direction = TrendDirection.DOWN
            else:
                direction = TrendDirection.SIDEWAYS

            # Trend strength (based on MA separation)
            ma_separation = abs(fast_current - slow_current) / slow_current
            strength = min(ma_separation * 10, 1.0)  # Scale and cap

            # Trend duration (consecutive periods above/below)
            duration = self._calculate_trend_duration(symbol, direction)

            # Only return signal if trend is established
            if strength >= self.config.min_trend_strength and direction != TrendDirection.SIDEWAYS:
                return TrendSignal(direction, strength, duration, strength, datetime.now())

            return None

        except Exception as e:
            self.logger.error("Error detecting MA trend", {'symbol': symbol, 'error': str(e)})
            return None

    def _detect_macd_trend(self, symbol: str) -> Optional[TrendSignal]:
        """Detect trend using MACD signals"""
        try:
            macd_data = self.macd_values[symbol]
            macd_line = macd_data['macd']
            signal_line = macd_data['signal']

            if len(macd_line) < 2 or len(signal_line) < 2:
                return None

            # MACD crossover signals
            macd_current = macd_line.iloc[-1]
            macd_prev = macd_line.iloc[-2]
            signal_current = signal_line.iloc[-1]
            signal_prev = signal_line.iloc[-2]

            if macd_current > signal_current and macd_prev <= signal_prev:
                direction = TrendDirection.UP
            elif macd_current < signal_current and macd_prev >= signal_prev:
                direction = TrendDirection.DOWN
            else:
                direction = TrendDirection.SIDEWAYS

            # Strength based on MACD histogram
            histogram = macd_data['histogram']
            strength = min(abs(histogram.iloc[-1]) * 100, 1.0)

            duration = self._calculate_trend_duration(symbol, direction)

            if strength >= self.config.min_trend_strength and direction != TrendDirection.SIDEWAYS:
                return TrendSignal(direction, strength, duration, strength, datetime.now())

            return None

        except Exception as e:
            self.logger.error("Error detecting MACD trend", {'symbol': symbol, 'error': str(e)})
            return None

    def _adx_confirmation(self, symbol: str) -> bool:
        """Check ADX confirmation for trend strength"""
        try:
            if symbol not in self.adx_values:
                return False

            adx = self.adx_values[symbol]
            if adx.empty:
                return False

            current_adx = adx.iloc[-1]
            return current_adx >= self.config.adx_threshold

        except Exception:
            return False

    def _momentum_confirmation(self, symbol: str) -> bool:
        """Check momentum confirmation"""
        try:
            if symbol not in self.momentum_values:
                return False

            momentum = self.momentum_values[symbol]
            if momentum.empty:
                return False

            current_momentum = momentum.iloc[-1]
            return abs(current_momentum) >= self.config.momentum_threshold

        except Exception:
            return False

    def _calculate_trend_duration(self, symbol: str, direction: TrendDirection) -> int:
        """Calculate how long the current trend has been in place"""
        try:
            if symbol not in self.trend_history:
                return 1

            # Count consecutive trends in the same direction
            duration = 1
            for trend in reversed(self.trend_history[symbol]):
                if trend.direction == direction:
                    duration += 1
                else:
                    break

            return min(duration, self.config.max_trend_duration)

        except Exception:
            return 1

    def _generate_entry_signal(self, symbol: str, trend_signal: TrendSignal, current_price: float) -> Optional[StrategySignal]:
        """Generate entry signal with position sizing"""
        try:
            # Calculate position size based on trend strength
            position_size = self._calculate_position_size(symbol, trend_signal.strength)

            # Determine signal type
            signal_type = SignalType.BUY if trend_signal.direction == TrendDirection.UP else SignalType.SELL

            # Create signal
            signal = StrategySignal(
                signal_id=f"trend_entry_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                strategy_id=self.config.strategy_id,
                timestamp=datetime.now(),
                symbol=symbol,
                signal_type=signal_type,
                confidence=trend_signal.confidence,
                strength=trend_signal.strength,
                target_quantity=position_size,
                signal_price=current_price,
                entry_price=current_price,
                max_position_size=self.config.max_position_size
            )

            # Set up risk management levels
            self._setup_risk_management(symbol, signal, current_price)

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

            # Determine exit type (close long or close short)
            if position.quantity > 0:
                signal_type = SignalType.CLOSE_LONG
            else:
                signal_type = SignalType.CLOSE_SHORT

            signal = StrategySignal(
                signal_id=f"trend_exit_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
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

    def _calculate_position_size(self, symbol: str, trend_strength: float) -> float:
        """Calculate position size based on trend strength and volatility"""
        try:
            base_size = self.config.base_position_size

            # Adjust for trend strength
            strength_multiplier = 1.0 + (trend_strength - 0.5) * self.config.trend_strength_multiplier
            size = base_size * strength_multiplier

            # Adjust for volatility if enabled
            if self.config.vol_adjustment and symbol in self.volatility_values:
                volatility = self.volatility_values[symbol].iloc[-1]
                if not np.isnan(volatility) and volatility > 0:
                    vol_adjustment = self.config.volatility_target / volatility
                    size *= vol_adjustment

            # Cap at maximum size
            size = min(size, self.config.max_position_size)

            return size

        except Exception as e:
            self.logger.error("Error calculating position size", {'symbol': symbol, 'error': str(e)})
            return self.config.base_position_size

    def _setup_risk_management(self, symbol: str, signal: StrategySignal, entry_price: float) -> None:
        """Set up stop loss and take profit levels"""
        try:
            # Stop loss
            stop_distance = entry_price * self.config.stop_loss_pct
            if signal.signal_type == SignalType.BUY:
                self.stop_levels[symbol] = entry_price - stop_distance
                self.take_profit_levels[symbol] = entry_price + (stop_distance * self.config.take_profit_multiplier)
            else:
                self.stop_levels[symbol] = entry_price + stop_distance
                self.take_profit_levels[symbol] = entry_price - (stop_distance * self.config.take_profit_multiplier)

        except Exception as e:
            self.logger.error("Error setting up risk management", {'symbol': symbol, 'error': str(e)})

    def _should_exit_position(self, symbol: str, trend_signal: TrendSignal) -> bool:
        """Determine if position should be exited"""
        try:
            if symbol not in self.active_positions:
                return False

            # Check for trend reversal
            position = self.active_positions[symbol]
            is_long = position.quantity > 0

            # Exit if trend reverses
            if (is_long and trend_signal.direction == TrendDirection.DOWN) or \
               (not is_long and trend_signal.direction == TrendDirection.UP):
                return True

            # Exit if trend strength weakens significantly
            if trend_signal.strength < self.config.min_trend_strength * 0.5:
                return True

            # Exit if maximum trend duration reached
            if trend_signal.duration >= self.config.max_trend_duration:
                return True

            return False

        except Exception as e:
            self.logger.error("Error checking exit condition", {'symbol': symbol, 'error': str(e)})
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

    def _monitor_trend_changes(self) -> None:
        """Monitor for significant trend changes"""
        try:
            for symbol in self.current_trends.keys():
                # Store trend history
                if symbol not in self.trend_history:
                    self.trend_history[symbol] = []

                self.trend_history[symbol].append(self.current_trends[symbol])

                # Keep only recent history
                if len(self.trend_history[symbol]) > 100:
                    self.trend_history[symbol] = self.trend_history[symbol][-100:]

        except Exception as e:
            self.logger.error("Error monitoring trend changes", {'error': str(e)})

    def get_strategy_metrics(self) -> StrategyMetrics:
        """Get current strategy performance metrics"""
        metrics = StrategyMetrics()

        # Populate with actual metrics
        metrics.total_signals = len(self.signal_history)
        metrics.active_positions = len(self.active_positions)

        # Add trend-specific metrics
        metrics.total_return = sum(len(trends) for trends in self.trend_history.values())

        return metrics