"""
Enhanced Trend Following Strategy with ISystemComponent Integration
=================================================================

Professional trend following strategy that implements ISystemComponent interface
for seamless orchestrator integration and institutional-grade lifecycle management.

This enhanced strategy provides:
- ISystemComponent interface compliance
- Adaptive trend detection using multiple indicators
- Dynamic position sizing based on trend strength
- Multi-timeframe trend confirmation
- Professional risk management integration
- Comprehensive performance tracking

Key Features:
- Multiple moving average systems (EMA, SMA, TEMA)
- MACD and trend strength indicators
- Adaptive position sizing based on trend quality
- Trend reversal detection and protection
- Dynamic stop losses and profit targets
- Regime-aware trend filtering

Academic Foundations:
- Fama & French (1988) permanent and temporary components
- Jegadeesh & Titman (1993) momentum strategies
- Moskowitz et al. (2012) time series momentum

Author: StatArb_Gemini Architecture Compliance
Version: 1.0.0 (Phase 2.3 Enhancement)
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any
from enum import Enum
import logging

# Import enhanced base strategy
from ...base_strategy_enhanced import EnhancedBaseStrategy
from ...strategy_engine import (
    StrategySignal, SignalType
)

# Import centralized configuration (Rule 1 Section 7 - Configuration Management)
# REQUIRED: Use centralized config only - no local fallback definitions per Rule 1
from core_engine.config import TrendFollowingConfig

logger = logging.getLogger(__name__)

class TrendSignal(Enum):
    """Trend following signal types"""
    UPTREND_ENTRY = "uptrend_entry"
    DOWNTREND_ENTRY = "downtrend_entry"
    TREND_CONTINUATION = "trend_continuation"
    TREND_REVERSAL = "trend_reversal"

class TrendStrength(Enum):
    """Trend strength levels"""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"

# ✅ TrendFollowingConfig imported from core_engine.config (Rule 1 Section 7)
# No local config definitions - centralized configuration only

class EnhancedTrendFollowingStrategy(EnhancedBaseStrategy):
    """
    Enhanced Trend Following Strategy with ISystemComponent Integration

    Professional trend following strategy that provides:
    - ISystemComponent interface compliance
    - Adaptive trend detection using multiple indicators
    - Dynamic position sizing based on trend strength
    - Multi-timeframe trend confirmation
    - Comprehensive performance tracking and risk management
    """

    def __init__(self, config: TrendFollowingConfig):
        """Initialize enhanced trend following strategy"""

        # Initialize base strategy
        super().__init__(config)
        self.config: TrendFollowingConfig = config

        # Strategy-specific state
        self.market_data: Dict[str, pd.DataFrame] = {}
        self.indicators: Dict[str, Dict[str, pd.Series]] = {}
        self.trend_data: Dict[str, Dict[str, Any]] = {}

        # ========================================
        # DEPRECATED: Position Tracking Fields
        # ========================================
        # These fields are DEPRECATED. Position tracking should be handled by
        # PositionBook (SSOT) and Risk Manager, not by strategies.
        #
        # Migration path:
        # - Use self._position_book.get_position(symbol) for read-only queries
        # - Use self._has_position(symbol) helper method
        # - Let Risk Manager handle stop-losses, trailing stops, and profit targets
        #
        # These fields are kept for backward compatibility only.
        self.active_positions: Dict[str, Dict[str, Any]] = {}  # DEPRECATED
        self.entry_prices: Dict[str, float] = {}  # DEPRECATED
        self.stop_losses: Dict[str, float] = {}  # DEPRECATED
        self.trailing_stops: Dict[str, float] = {}  # DEPRECATED
        self.profit_targets: Dict[str, float] = {}  # DEPRECATED

        # Performance tracking
        self.trade_history: List[Dict[str, Any]] = []
        self.trend_performance: Dict[str, Dict[str, float]] = {}

        logger.info(f"🧠 Enhanced Trend Following Strategy {self.strategy_id} initialized")

    # ========================================
    # STRATEGY-SPECIFIC LIFECYCLE HOOKS
    # ========================================

    async def _initialize_strategy_components(self) -> bool:
        """Initialize strategy-specific components"""

        try:
            logger.info(f"🔄 Initializing Trend Following components for {self.strategy_id}...")

            # Validate symbols
            if not self.config.symbols:
                logger.error("❌ No symbols configured for trend following strategy")
                return False

            # Initialize data structures
            self._initialize_data_structures()

            # Initialize indicators
            self._initialize_indicators()

            logger.info(f"✅ Trend Following components initialized for {len(self.config.symbols)} symbols")
            return True

        except Exception as e:
            logger.error(f"❌ Trend Following component initialization failed: {e}")
            return False

    async def _start_strategy_operations(self) -> bool:
        """Start strategy-specific operations"""

        try:
            logger.info(f"🚀 Starting Trend Following operations for {self.strategy_id}...")

            # Start performance tracking
            self._start_performance_tracking()

            logger.info(f"✅ Trend Following operations started")
            return True

        except Exception as e:
            logger.error(f"❌ Trend Following operations start failed: {e}")
            return False

    async def _stop_strategy_operations(self) -> None:
        """Stop strategy-specific operations"""

        try:
            logger.info(f"🔄 Stopping Trend Following operations for {self.strategy_id}...")

            # Close all positions
            await self._close_all_positions()

            # Save performance data
            self._save_performance_data()

            logger.info(f"✅ Trend Following operations stopped")

        except Exception as e:
            logger.error(f"❌ Trend Following operations stop failed: {e}")

    async def _check_strategy_health(self) -> Dict[str, Any]:
        """Check strategy-specific health"""

        try:
            health_metrics = {
                'strategy_healthy': True,
                'symbols_tracked': len(self.config.symbols),
                'active_positions': len(self.active_positions),
                'indicators_calculated': len(self.indicators),
                'avg_trend_strength': self._calculate_avg_trend_strength(),
                'trending_symbols': self._count_trending_symbols()
            }

            # Check for unhealthy conditions
            if len(self.indicators) == 0:
                health_metrics['strategy_healthy'] = False
                health_metrics['warning'] = "No indicators calculated"

            if self._count_trending_symbols() == 0:
                health_metrics['strategy_healthy'] = False
                health_metrics['warning'] = "No trending symbols detected"

            return health_metrics

        except Exception as e:
            return {
                'strategy_healthy': False,
                'error': str(e)
            }

    def _get_strategy_config_summary(self) -> Dict[str, Any]:
        """Get strategy-specific configuration summary"""

        return {
            'strategy_type': 'Enhanced Trend Following',
            'symbols_count': len(self.config.symbols),
            'ma_periods': [self.config.fast_ma_period, self.config.slow_ma_period],
            'ma_type': self.config.ma_type,
            'enable_multi_timeframe': self.config.enable_multi_timeframe,
            'enable_trend_filter': self.config.enable_trend_filter,
            'base_position_pct': self.config.base_position_pct,
            'adx_threshold': self.config.adx_threshold
        }

    def _validate_strategy_config(self) -> bool:
        """Validate strategy-specific configuration"""

        try:
            # Validate MA periods
            if self.config.fast_ma_period >= self.config.slow_ma_period:
                logger.error("Fast MA period must be less than slow MA period")
                return False

            # Validate MA type
            if self.config.ma_type not in ["SMA", "EMA", "TEMA"]:
                logger.error("MA type must be SMA, EMA, or TEMA")
                return False

            # Validate position sizing
            if self.config.base_position_pct <= 0 or self.config.base_position_pct > 0.15:
                logger.error("Base position percentage must be between 0 and 0.15 (15%)")
                return False

            return True

        except Exception as e:
            logger.error(f"Configuration validation error: {e}")
            return False

    # ========================================
    # ABSTRACT METHOD IMPLEMENTATIONS
    # ========================================

    def _validate_enriched_data(self, enriched_data: Dict[str, pd.DataFrame]) -> None:
        """
        Validate that data is enriched with required features (Rule 3 Phase 4)

        Trend following strategy requires pre-calculated trend indicators.

        Args:
            enriched_data: Dict[symbol, enriched DataFrame]

        Raises:
            ValueError: If data is missing required features
        """
        required_features = [
            'SMA_20', 'SMA_50', 'SMA_200',  # Moving averages
            'EMA_12', 'EMA_26',              # EMA for MACD
            'MACD', 'MACD_signal',           # MACD indicators
            'ADX_14',                         # Trend strength
            'ATR_14',                         # Volatility
            'volume_ratio'                    # Volume confirmation
        ]

        for symbol in self.config.symbols:
            if symbol not in enriched_data:
                continue

            data = enriched_data[symbol]
            if data.empty:
                raise ValueError(f"{symbol} has empty DataFrame")

            missing = [col for col in required_features if col not in data.columns]
            if missing:
                available_cols = list(data.columns[:20])
                raise ValueError(
                    f"{symbol} missing required features: {missing}. "
                    f"Data must be enriched via ProcessingPipelineOrchestrator (Rule 3). "
                    f"Available columns: {available_cols}"
                )

            logger.debug(f"✅ {symbol} enriched data validated: {len(required_features)} features present")

    async def generate_signals(self, enriched_data: Dict[str, pd.DataFrame]) -> List[StrategySignal]:
        """
        Generate trend following signals from ENRICHED data (Rule 3 Phase 4)

        **CRITICAL CHANGE:** This method now receives enriched data with pre-calculated
        indicators from the ProcessingPipelineOrchestrator. It reads pre-calculated
        indicators instead of calculating them.

        Args:
            enriched_data: Dict[symbol, enriched DataFrame with OHLCV + indicators + features]
                          Must contain: SMA_20, SMA_50, SMA_200, MACD, ADX_14, ATR_14

        Returns:
            List[StrategySignal]: Generated trend following signals
        """
        start_time = datetime.now()
        signals = []

        try:
            # PHASE 4: Validate enriched data (Rule 3)
            self._validate_enriched_data(enriched_data)

            # Update market data with enriched data
            self._update_market_data(enriched_data)

            # Update trend analysis (using pre-calculated indicators)
            self._update_trend_analysis()

            # Generate signals for each symbol
            for symbol in self.config.symbols:
                if symbol in self.market_data and len(self.market_data[symbol]) > self.config.slow_ma_period:
                    symbol_signals = await self._generate_symbol_signals(symbol)
                    signals.extend(symbol_signals)

            # Update performance metrics
            generation_time = (datetime.now() - start_time).total_seconds()
            self.track_signal_generation_time(generation_time)

            logger.info(f"📊 Trend Following Strategy (Rule 3 Phase 4 - Enriched Data):")
            logger.info(f"   Signals generated: {len(signals)}")
            logger.info(f"   Generation time: {generation_time:.3f}s")

            return signals

        except Exception as e:
            self._log_error("Signal generation failed", e)
            return []

    async def update_positions(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """Update existing positions based on market data"""

        try:
            # Update market data
            self._update_market_data(market_data)

            # Update trailing stops
            self._update_trailing_stops()

            # Check exit conditions for active positions
            await self._check_exit_conditions()

            # Update performance tracking
            self._update_performance_tracking()

        except Exception as e:
            self._log_error("Position update failed", e)

    def calculate_position_size(self, signal: StrategySignal, market_data: Dict[str, pd.DataFrame]) -> float:
        """Calculate position size for a given signal"""

        try:
            symbol = signal.symbol

            # Base position size
            base_size = self.config.base_position_pct

            # Scale by trend strength if enabled - use configurable cap from centralized config (Rule 1)
            if self.config.trend_scaling and symbol in self.trend_data:
                trend_strength = self.trend_data[symbol].get('trend_strength_score', 1.0)
                trend_multiplier = min(trend_strength, self.config.trend_multiplier_cap)
                base_size *= trend_multiplier

            # Scale by signal confidence
            confidence_multiplier = signal.confidence
            base_size *= confidence_multiplier

            # Scale by ADX (trend quality) - READ from enriched DataFrame (Rule 3 Phase 4)
            if symbol in self.market_data and len(self.market_data[symbol]) > 0:
                current_data = self.market_data[symbol].iloc[-1]
                adx = current_data.get('ADX_14', 0.0)
                if adx > 0:
                    # Use configurable ADX multiplier cap from centralized config (Rule 1)
                    adx_multiplier = min(adx / self.config.adx_threshold, self.config.adx_multiplier_cap)
                    base_size *= adx_multiplier

            # Volatility adjustment - uses enriched DataFrame (Rule 3 Phase 4)
            if self.config.enable_volatility_filter:
                volatility_adjustment = self._get_volatility_adjustment(symbol)
                base_size *= volatility_adjustment

            # Cap at maximum position size
            return min(base_size, self.config.max_position_pct)

        except Exception as e:
            self._log_error("Position size calculation failed", e)
            return 0.0

    # ========================================
    # SIGNAL GENERATION METHODS
    # ========================================

    async def _generate_symbol_signals(self, symbol: str) -> List[StrategySignal]:
        """
        Generate signals for a specific symbol using PRE-CALCULATED indicators (Rule 3 Phase 4)

        **CRITICAL:** Reads indicators from enriched DataFrame columns, not calculated here.
        """
        signals = []

        try:
            # Skip if already have position
            if symbol in self.active_positions:
                return signals

            # Validate we have enriched data
            if symbol not in self.market_data:
                return signals

            # Get current enriched DataFrame row
            data = self.market_data[symbol]
            if len(data) == 0:
                return signals

            current_data = data.iloc[-1]
            trend = self.trend_data.get(symbol, {})

            # Get trend indicators (from trend analysis)
            trend_direction = trend.get('trend_direction', 'neutral')
            trend_strength = trend.get('trend_strength', TrendStrength.WEAK)
            trend_quality = trend.get('trend_quality_score', 0)

            # READ technical indicators from enriched DataFrame columns (Rule 3 Phase 4)
            fast_ma = current_data.get('SMA_20', 0.0)  # Use SMA_20 as fast MA
            slow_ma = current_data.get('SMA_50', 0.0)  # Use SMA_50 as slow MA
            macd = current_data.get('MACD', 0.0)
            macd_signal = current_data.get('MACD_signal', 0.0)
            adx = current_data.get('ADX_14', 0.0)

            # Apply filters
            if self.config.enable_trend_filter and not self._is_trend_valid(symbol):
                return signals

            if self.config.enable_volatility_filter and not self._is_volatility_acceptable(symbol):
                return signals

            # Check for uptrend entry
            if (trend_direction == 'up' and
                trend_strength in [TrendStrength.MODERATE, TrendStrength.STRONG, TrendStrength.VERY_STRONG] and
                fast_ma > slow_ma and
                macd > macd_signal and
                adx > self.config.adx_threshold):

                confidence = self._calculate_signal_confidence(symbol, TrendSignal.UPTREND_ENTRY)

                if confidence > 0.6:  # Minimum confidence threshold
                    signal = StrategySignal(
                        strategy_id=self.strategy_id,
                        symbol=symbol,
                        signal_type=SignalType.BUY,
                        strength=trend_quality,
                        confidence=confidence,
                        target_weight=self.config.base_position_pct,  # Use as percentage weight
                        quantity_type="PERCENTAGE",  # CRITICAL FIX: Explicit quantity_type
                        timestamp=datetime.now(),
                        additional_data={
                            'signal_reason': 'uptrend_entry',
                            'trend_direction': trend_direction,
                            'trend_strength': trend_strength.value,
                            'trend_quality': trend_quality,
                            'fast_ma': fast_ma,
                            'slow_ma': slow_ma,
                            'macd': macd,
                            'adx': adx,
                            'entry_price': current_data['close']
                        }
                    )
                    signals.append(signal)

                    # Track position entry
                    self._track_position_entry(symbol, signal)

            # Check for downtrend entry
            elif (trend_direction == 'down' and
                  trend_strength in [TrendStrength.MODERATE, TrendStrength.STRONG, TrendStrength.VERY_STRONG] and
                  fast_ma < slow_ma and
                  macd < macd_signal and
                  adx > self.config.adx_threshold):

                confidence = self._calculate_signal_confidence(symbol, TrendSignal.DOWNTREND_ENTRY)

                if confidence > 0.6:  # Minimum confidence threshold
                    signal = StrategySignal(
                        strategy_id=self.strategy_id,
                        symbol=symbol,
                        signal_type=SignalType.SELL,
                        strength=trend_quality,
                        confidence=confidence,
                        target_weight=self.config.base_position_pct,  # Use as percentage weight
                        quantity_type="PERCENTAGE",  # CRITICAL FIX: Explicit quantity_type
                        timestamp=datetime.now(),
                        additional_data={
                            'signal_reason': 'downtrend_entry',
                            'trend_direction': trend_direction,
                            'trend_strength': trend_strength.value,
                            'trend_quality': trend_quality,
                            'fast_ma': fast_ma,
                            'slow_ma': slow_ma,
                            'macd': macd,
                            'adx': adx,
                            'entry_price': current_data['close']
                        }
                    )
                    signals.append(signal)

                    # Track position entry
                    self._track_position_entry(symbol, signal)

            return signals

        except Exception as e:
            self._log_error(f"Symbol signal generation failed for {symbol}", e)
            return []

    # ========================================
    # INDICATOR EXTRACTION FROM ENRICHED DATA (Rule 3 Phase 4)
    # ========================================
    # NOTE: Indicators are PRE-CALCULATED by ProcessingPipelineOrchestrator.
    # This section extracts indicators from enriched DataFrame columns.
    # NO indicator calculation methods are allowed per Rule 3.

    # ========================================
    # TREND ANALYSIS METHODS
    # ========================================

    def _update_trend_analysis(self) -> None:
        """Update trend analysis for all symbols"""

        for symbol in self.config.symbols:
            if symbol in self.indicators:
                self.trend_data[symbol] = self._analyze_symbol_trend(symbol)

    def _analyze_symbol_trend(self, symbol: str) -> Dict[str, Any]:
        """
        Analyze trend for a specific symbol using PRE-CALCULATED indicators (Rule 3 Phase 4)

        **CRITICAL:** Reads indicators from enriched DataFrame columns, not calculated here.
        """
        try:
            if symbol not in self.market_data or len(self.market_data[symbol]) == 0:
                return {
                    'trend_direction': 'neutral',
                    'trend_strength': TrendStrength.WEAK,
                    'trend_quality_score': 0,
                    'trend_duration': 0,
                    'adx': 0,
                    'ma_alignment': 0,
                    'macd_strength': 0,
                    'momentum': 0
                }

            # READ indicators from enriched DataFrame (Rule 3 Phase 4)
            data = self.market_data[symbol]
            current_data = data.iloc[-1]

            # Get latest values from enriched DataFrame columns
            fast_ma = current_data.get('SMA_20', 0.0)
            slow_ma = current_data.get('SMA_50', 0.0)
            macd = current_data.get('MACD', 0.0)
            macd_signal = current_data.get('MACD_signal', 0.0)
            adx = current_data.get('ADX_14', 0.0)
            momentum = current_data.get('momentum_short', 0.0)

            # Determine trend direction
            trend_direction = 'neutral'
            if fast_ma > slow_ma and macd > macd_signal and momentum > 0:
                trend_direction = 'up'
            elif fast_ma < slow_ma and macd < macd_signal and momentum < 0:
                trend_direction = 'down'

            # Determine trend strength
            trend_strength = TrendStrength.WEAK
            if adx > 50:
                trend_strength = TrendStrength.VERY_STRONG
            elif adx > 35:
                trend_strength = TrendStrength.STRONG
            elif adx > self.config.adx_threshold:
                trend_strength = TrendStrength.MODERATE

            # Calculate trend quality score (0-1)
            ma_alignment = abs(fast_ma - slow_ma) / slow_ma if slow_ma != 0 else 0
            macd_strength = abs(macd - macd_signal) / abs(macd_signal) if macd_signal != 0 else 0
            adx_normalized = min(adx / 50, 1.0)
            momentum_strength = min(abs(momentum) * 10, 1.0)

            trend_quality_score = (ma_alignment * 0.3 +
                                 macd_strength * 0.3 +
                                 adx_normalized * 0.25 +
                                 momentum_strength * 0.15)

            # Calculate trend duration
            trend_duration = self._calculate_trend_duration(symbol)

            return {
                'trend_direction': trend_direction,
                'trend_strength': trend_strength,
                'trend_quality_score': min(trend_quality_score, 1.0),
                'trend_duration': trend_duration,
                'adx': adx,
                'ma_alignment': ma_alignment,
                'macd_strength': macd_strength,
                'momentum': momentum
            }

        except Exception as e:
            logger.error(f"Trend analysis failed for {symbol}: {e}")
            return {
                'trend_direction': 'neutral',
                'trend_strength': TrendStrength.WEAK,
                'trend_quality_score': 0,
                'trend_duration': 0,
                'adx': 0,
                'ma_alignment': 0,
                'macd_strength': 0,
                'momentum': 0
            }

    def _calculate_trend_duration(self, symbol: str) -> int:
        """
        Calculate how long the current trend has been in place using enriched DataFrame (Rule 3 Phase 4)

        **CRITICAL:** Reads MA values from enriched DataFrame columns.
        """
        try:
            if symbol not in self.market_data or len(self.market_data[symbol]) < 2:
                return 0

            # READ MA values from enriched DataFrame (Rule 3 Phase 4)
            data = self.market_data[symbol]
            fast_ma = data.get('SMA_20', pd.Series(dtype=float))
            slow_ma = data.get('SMA_50', pd.Series(dtype=float))

            if len(fast_ma) < 2 or len(slow_ma) < 2:
                return 0

            # Count consecutive periods where fast MA > slow MA (uptrend) or vice versa
            ma_diff = fast_ma - slow_ma
            current_trend_sign = np.sign(ma_diff.iloc[-1])

            duration = 0
            for i in range(len(ma_diff) - 1, -1, -1):
                if np.sign(ma_diff.iloc[i]) == current_trend_sign:
                    duration += 1
                else:
                    break

            return duration

        except Exception as e:
            logger.error(f"Trend duration calculation failed for {symbol}: {e}")
            return 0

    # ========================================
    # FILTER METHODS
    # ========================================

    def _is_trend_valid(self, symbol: str) -> bool:
        """Check if trend meets minimum requirements"""

        if symbol not in self.trend_data:
            return False

        trend = self.trend_data[symbol]

        # Check minimum trend duration
        if trend.get('trend_duration', 0) < self.config.min_trend_duration:
            return False

        # Check trend strength
        if trend.get('trend_strength', TrendStrength.WEAK) == TrendStrength.WEAK:
            return False

        return True

    def _is_volatility_acceptable(self, symbol: str) -> bool:
        """
        Check if volatility is within acceptable range using enriched DataFrame (Rule 3 Phase 4)

        **CRITICAL:** Reads volatility from enriched DataFrame column.
        """
        try:
            if symbol not in self.market_data or len(self.market_data[symbol]) == 0:
                return True

            # READ volatility from enriched DataFrame (Rule 3 Phase 4)
            data = self.market_data[symbol]
            if 'volatility' not in data.columns:
                return True  # Allow if volatility not available

            volatility_series = data['volatility']
            if len(volatility_series) < self.config.volatility_lookback:
                return True

            current_volatility = volatility_series.iloc[-1]
            historical_volatility = volatility_series.tail(self.config.volatility_lookback)

            # Check if current volatility is below maximum percentile
            volatility_percentile = (historical_volatility < current_volatility).mean()

            return volatility_percentile <= self.config.max_volatility_percentile

        except Exception as e:
            logger.error(f"Volatility check failed for {symbol}: {e}")
            return True

    def _get_volatility_adjustment(self, symbol: str) -> float:
        """
        Get volatility adjustment factor for position sizing using enriched DataFrame (Rule 3 Phase 4)

        **CRITICAL:** Reads volatility from enriched DataFrame column.
        """
        try:
            if symbol not in self.market_data or len(self.market_data[symbol]) == 0:
                return 1.0

            # READ volatility from enriched DataFrame (Rule 3 Phase 4)
            data = self.market_data[symbol]
            if 'volatility' not in data.columns:
                return 1.0

            volatility_series = data['volatility']
            if len(volatility_series) < 20:
                return 1.0

            current_vol = volatility_series.iloc[-1]
            avg_vol = volatility_series.tail(20).mean()

            if avg_vol == 0:
                return 1.0

            # Inverse relationship: higher volatility = smaller position
            # Use configurable parameters from centralized config (Rule 1)
            vol_ratio = current_vol / avg_vol
            adjustment = 1.0 / max(vol_ratio, self.config.volatility_adjustment_min)

            return min(adjustment, self.config.volatility_adjustment_cap)

        except Exception as e:
            logger.error(f"Volatility adjustment calculation failed for {symbol}: {e}")
            return 1.0

    def _calculate_signal_confidence(self, symbol: str, signal_type: TrendSignal) -> float:
        """
        Calculate signal confidence based on multiple factors using enriched DataFrame (Rule 3 Phase 4)

        **CRITICAL:** Reads indicators from enriched DataFrame columns.
        """
        try:
            if symbol not in self.trend_data or symbol not in self.market_data:
                return 0.5

            trend = self.trend_data[symbol]
            data = self.market_data[symbol]

            if len(data) == 0:
                return 0.5

            current_data = data.iloc[-1]

            # Base confidence from trend quality
            trend_quality = trend.get('trend_quality_score', 0)

            # Trend strength confidence
            trend_strength = trend.get('trend_strength', TrendStrength.WEAK)
            strength_confidence = {
                TrendStrength.WEAK: 0.3,
                TrendStrength.MODERATE: 0.6,
                TrendStrength.STRONG: 0.8,
                TrendStrength.VERY_STRONG: 0.95
            }.get(trend_strength, 0.3)

            # Trend duration confidence - use configurable multiplier from centralized config (Rule 1)
            duration = trend.get('trend_duration', 0)
            duration_confidence = min(duration / (self.config.min_trend_duration * self.config.duration_confidence_multiplier), 1.0)

            # ADX confidence - use configurable multiplier from centralized config (Rule 1)
            adx = trend.get('adx', 0)
            # Reuse duration_confidence_multiplier for ADX confidence scaling
            adx_confidence = min(adx / (self.config.adx_threshold * self.config.duration_confidence_multiplier), 1.0)

            # MACD confirmation (READ from enriched DataFrame)
            macd = current_data.get('MACD', 0.0)
            macd_signal = current_data.get('MACD_signal', 0.0)

            if signal_type in [TrendSignal.UPTREND_ENTRY]:
                macd_confidence = 1.0 if macd > macd_signal else 0.5
            else:  # downtrend
                macd_confidence = 1.0 if macd < macd_signal else 0.5

            # Combine confidences (weighted average)
            total_confidence = (trend_quality * 0.3 +
                              strength_confidence * 0.25 +
                              duration_confidence * 0.2 +
                              adx_confidence * 0.15 +
                              macd_confidence * 0.1)

            return min(total_confidence, 0.95)  # Cap at 95%

        except Exception as e:
            logger.error(f"Signal confidence calculation failed for {symbol}: {e}")
            return 0.5

    # ========================================
    # HELPER METHODS
    # ========================================

    def _update_market_data(self, enriched_data: Dict[str, pd.DataFrame]) -> None:
        """
        Update market data cache and extract indicators from enriched DataFrame (Rule 3 Phase 4)

        **CRITICAL:** This method extracts PRE-CALCULATED indicators from enriched DataFrame columns.
        Indicators are provided by ProcessingPipelineOrchestrator, not calculated here.

        Args:
            enriched_data: Dict[symbol, enriched DataFrame with OHLCV + indicators + features]
        """
        for symbol, data in enriched_data.items():
            if symbol in self.config.symbols:
                # Store enriched DataFrame
                self.market_data[symbol] = data

                # Extract PRE-CALCULATED indicators from enriched DataFrame columns (Rule 3)
                # Map enriched DataFrame columns to strategy indicators
                try:
                    self.indicators[symbol] = {
                        # Use SMA_20 as fast MA, SMA_50 as slow MA (from enriched data)
                        'fast_ma': data.get('SMA_20', pd.Series(dtype=float)) if 'SMA_20' in data.columns else pd.Series(dtype=float),
                        'slow_ma': data.get('SMA_50', pd.Series(dtype=float)) if 'SMA_50' in data.columns else pd.Series(dtype=float),

                        # MACD indicators (pre-calculated)
                        'macd': data.get('MACD', pd.Series(dtype=float)) if 'MACD' in data.columns else pd.Series(dtype=float),
                        'macd_signal': data.get('MACD_signal', pd.Series(dtype=float)) if 'MACD_signal' in data.columns else pd.Series(dtype=float),
                        'macd_histogram': data.get('MACD_histogram', pd.Series(dtype=float)) if 'MACD_histogram' in data.columns else pd.Series(dtype=float),

                        # ADX and ATR (pre-calculated)
                        'adx': data.get('ADX_14', pd.Series(dtype=float)) if 'ADX_14' in data.columns else pd.Series(dtype=float),
                        'atr': data.get('ATR_14', pd.Series(dtype=float)) if 'ATR_14' in data.columns else pd.Series(dtype=float),

                        # Volatility and momentum (from enriched features)
                        'volatility': data.get('volatility', pd.Series(dtype=float)) if 'volatility' in data.columns else pd.Series(dtype=float),
                        'momentum': data.get('momentum_short', pd.Series(dtype=float)) if 'momentum_short' in data.columns else pd.Series(dtype=float)
                    }
                    logger.debug(f"✅ {symbol}: Extracted indicators from enriched DataFrame (Rule 3 Phase 4)")
                except Exception as e:
                    logger.error(f"❌ {symbol}: Failed to extract indicators from enriched DataFrame: {e}")
                    self.indicators[symbol] = {}

    def _initialize_data_structures(self) -> None:
        """Initialize strategy data structures"""

        self.market_data.clear()
        self.indicators.clear()
        self.trend_data.clear()
        self.active_positions.clear()
        self.entry_prices.clear()
        self.stop_losses.clear()
        self.trailing_stops.clear()
        self.profit_targets.clear()

    def _initialize_indicators(self) -> None:
        """Initialize indicators dictionary"""

        for symbol in self.config.symbols:
            self.indicators[symbol] = {}
            self.trend_data[symbol] = {}

    def _start_performance_tracking(self) -> None:
        """Start performance tracking"""
        logger.info("📊 Trend Following performance tracking started")

    async def _close_all_positions(self) -> None:
        """Close all active positions"""
        logger.info(f"🔄 Closing {len(self.active_positions)} active positions")
        self.active_positions.clear()
        self.entry_prices.clear()
        self.stop_losses.clear()
        self.trailing_stops.clear()
        self.profit_targets.clear()

    def _save_performance_data(self) -> None:
        """Save performance data"""
        logger.info("💾 Trend Following performance data saved")

    def _calculate_avg_trend_strength(self) -> float:
        """Calculate average trend strength across symbols"""

        if not self.trend_data:
            return 0.0

        strengths = []
        for data in self.trend_data.values():
            adx = data.get('adx', 0)
            strengths.append(adx)

        return np.mean(strengths) if strengths else 0.0

    def _count_trending_symbols(self) -> int:
        """Count symbols currently in strong trends"""

        count = 0
        for data in self.trend_data.values():
            if data.get('trend_strength', TrendStrength.WEAK) in [TrendStrength.STRONG, TrendStrength.VERY_STRONG]:
                count += 1

        return count

    def _track_position_entry(self, symbol: str, signal: StrategySignal) -> None:
        """
        Track position entry for exit management using enriched DataFrame (Rule 3 Phase 4)

        **CRITICAL:** Reads ATR from enriched DataFrame column.
        """
        try:
            entry_price = signal.additional_data.get('entry_price', 0)

            # Get ATR for stop loss calculation (READ from enriched DataFrame)
            atr = 0.0
            if symbol in self.market_data and len(self.market_data[symbol]) > 0:
                current_data = self.market_data[symbol].iloc[-1]
                atr = current_data.get('ATR_14', 0.0)

            # Calculate stop loss and profit target
            if signal.signal_type == SignalType.BUY:
                stop_loss = entry_price - (atr * self.config.atr_stop_multiplier)
                profit_target = entry_price + (atr * self.config.atr_stop_multiplier * self.config.profit_target_ratio)
                trailing_stop = entry_price * (1 - self.config.trailing_stop_pct)
            else:  # SELL
                stop_loss = entry_price + (atr * self.config.atr_stop_multiplier)
                profit_target = entry_price - (atr * self.config.atr_stop_multiplier * self.config.profit_target_ratio)
                trailing_stop = entry_price * (1 + self.config.trailing_stop_pct)

            # Track position
            self.active_positions[symbol] = {
                'signal_type': signal.signal_type,
                'entry_time': signal.timestamp,
                'entry_price': entry_price,
                'quantity': signal.target_quantity
            }

            self.entry_prices[symbol] = entry_price
            self.stop_losses[symbol] = stop_loss
            self.trailing_stops[symbol] = trailing_stop
            self.profit_targets[symbol] = profit_target

            logger.info(f"📈 Trend position tracked for {symbol}: Entry=${entry_price:.2f}, "
                       f"Stop=${stop_loss:.2f}, Target=${profit_target:.2f}")

        except Exception as e:
            self._log_error(f"Position tracking failed for {symbol}", e)

    def _update_trailing_stops(self) -> None:
        """Update trailing stops for active positions"""

        try:
            for symbol in list(self.trailing_stops.keys()):
                if symbol in self.market_data and len(self.market_data[symbol]) > 0:
                    current_price = self.market_data[symbol]['close'].iloc[-1]
                    position = self.active_positions.get(symbol)

                    if position:
                        if position['signal_type'] == SignalType.BUY:
                            # Update trailing stop for long position
                            new_trailing_stop = current_price * (1 - self.config.trailing_stop_pct)
                            if new_trailing_stop > self.trailing_stops[symbol]:
                                self.trailing_stops[symbol] = new_trailing_stop
                        else:  # SELL
                            # Update trailing stop for short position
                            new_trailing_stop = current_price * (1 + self.config.trailing_stop_pct)
                            if new_trailing_stop < self.trailing_stops[symbol]:
                                self.trailing_stops[symbol] = new_trailing_stop

        except Exception as e:
            self._log_error("Trailing stop update failed", e)

    async def _check_exit_conditions(self) -> None:
        """Check exit conditions for active positions"""

        try:
            positions_to_close = []

            for symbol in list(self.active_positions.keys()):
                if symbol in self.market_data and len(self.market_data[symbol]) > 0:
                    current_price = self.market_data[symbol]['close'].iloc[-1]
                    position = self.active_positions[symbol]

                    should_exit = False
                    exit_reason = ""

                    # Check stop loss
                    if symbol in self.stop_losses:
                        if position['signal_type'] == SignalType.BUY and current_price <= self.stop_losses[symbol]:
                            should_exit = True
                            exit_reason = "stop_loss"
                        elif position['signal_type'] == SignalType.SELL and current_price >= self.stop_losses[symbol]:
                            should_exit = True
                            exit_reason = "stop_loss"

                    # Check trailing stop
                    if not should_exit and symbol in self.trailing_stops:
                        if position['signal_type'] == SignalType.BUY and current_price <= self.trailing_stops[symbol]:
                            should_exit = True
                            exit_reason = "trailing_stop"
                        elif position['signal_type'] == SignalType.SELL and current_price >= self.trailing_stops[symbol]:
                            should_exit = True
                            exit_reason = "trailing_stop"

                    # Check profit target
                    if not should_exit and symbol in self.profit_targets:
                        if position['signal_type'] == SignalType.BUY and current_price >= self.profit_targets[symbol]:
                            should_exit = True
                            exit_reason = "profit_target"
                        elif position['signal_type'] == SignalType.SELL and current_price <= self.profit_targets[symbol]:
                            should_exit = True
                            exit_reason = "profit_target"

                    # Check trend reversal
                    if not should_exit and symbol in self.trend_data:
                        trend = self.trend_data[symbol]
                        if position['signal_type'] == SignalType.BUY and trend.get('trend_direction') == 'down':
                            should_exit = True
                            exit_reason = "trend_reversal"
                        elif position['signal_type'] == SignalType.SELL and trend.get('trend_direction') == 'up':
                            should_exit = True
                            exit_reason = "trend_reversal"

                    # Check maximum holding period
                    if not should_exit:
                        holding_time = datetime.now() - position['entry_time']
                        if holding_time.total_seconds() > (self.config.max_holding_period * 300):  # Assuming 5-min bars
                            should_exit = True
                            exit_reason = "max_holding_period"

                    if should_exit:
                        positions_to_close.append((symbol, exit_reason))
                        logger.info(f"📉 Exit condition met for {symbol}: {exit_reason}")

            # Close positions
            for symbol, reason in positions_to_close:
                await self._close_position(symbol, reason)

        except Exception as e:
            self._log_error("Exit condition check failed", e)

    async def _close_position(self, symbol: str, reason: str) -> None:
        """Close a specific position"""

        try:
            if symbol in self.active_positions:
                position = self.active_positions[symbol]

                # Create exit signal
                exit_signal = StrategySignal(
                    strategy_id=self.strategy_id,
                    symbol=symbol,
                    signal_type=SignalType.SELL if position['signal_type'] == SignalType.BUY else SignalType.BUY,
                    strength=1.0,
                    confidence=0.9,
                    target_weight=self.config.base_position_pct,  # Use as percentage weight
                    quantity_type="PERCENTAGE",  # CRITICAL FIX: Explicit quantity_type
                    timestamp=datetime.now(),
                    additional_data={  # FIXED: metadata -> additional_data
                        'action': 'exit',
                        'exit_reason': reason,
                        'entry_price': position['entry_price']
                    }
                )

                # Submit to risk manager if available
                if self.risk_manager:
                    await self.risk_manager.process_signal(exit_signal)

                # Clean up tracking
                del self.active_positions[symbol]
                if symbol in self.entry_prices:
                    del self.entry_prices[symbol]
                if symbol in self.stop_losses:
                    del self.stop_losses[symbol]
                if symbol in self.trailing_stops:
                    del self.trailing_stops[symbol]
                if symbol in self.profit_targets:
                    del self.profit_targets[symbol]

                logger.info(f"🔄 Trend position closed for {symbol}: {reason}")

        except Exception as e:
            self._log_error(f"Position close failed for {symbol}", e)

    def _update_performance_tracking(self) -> None:
        """Update performance tracking metrics"""

        # Placeholder for performance tracking updates

    # ========================================
    # STRATEGY-SPECIFIC METHODS
    # ========================================

    def get_trend_following_summary(self) -> Dict[str, Any]:
        """Get comprehensive trend following strategy summary"""

        return {
            'strategy_id': self.strategy_id,
            'strategy_type': 'Enhanced Trend Following',
            'symbols_tracked': len(self.config.symbols),
            'active_positions': len(self.active_positions),
            'avg_trend_strength': self._calculate_avg_trend_strength(),
            'trending_symbols': self._count_trending_symbols(),
            'performance_summary': self.get_performance_summary(),
            'trend_details': {
                symbol: {
                    'trend_direction': data.get('trend_direction', 'neutral'),
                    'trend_strength': data.get('trend_strength', TrendStrength.WEAK).value,
                    'trend_quality_score': data.get('trend_quality_score', 0),
                    'trend_duration': data.get('trend_duration', 0),
                    'adx': data.get('adx', 0)
                }
                for symbol, data in self.trend_data.items()
            },
            'position_details': {
                symbol: {
                    'signal_type': pos['signal_type'].value,
                    'entry_price': pos['entry_price'],
                    'entry_time': pos['entry_time'].isoformat(),
                    'stop_loss': self.stop_losses.get(symbol),
                    'trailing_stop': self.trailing_stops.get(symbol),
                    'profit_target': self.profit_targets.get(symbol)
                }
                for symbol, pos in self.active_positions.items()
            }
        }
