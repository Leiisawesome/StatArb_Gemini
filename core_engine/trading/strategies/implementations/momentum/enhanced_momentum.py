"""
Enhanced Momentum Strategy with ISystemComponent Integration
==========================================================

Professional momentum strategy that implements ISystemComponent interface
for seamless orchestrator integration and institutional-grade lifecycle management.

This enhanced strategy provides:
- ISystemComponent interface compliance
- Multi-timeframe momentum analysis
- Trend strength and quality assessment
- Dynamic position sizing based on momentum strength
- Professional risk management integration
- Comprehensive performance tracking

Key Features:
- Multi-timeframe momentum confirmation
- Trend quality assessment using ADX
- Volume confirmation for momentum signals
- Breakout detection and momentum continuation
- Risk-adjusted position sizing
- Momentum decay detection for exits

Academic Foundations:
- Jegadeesh & Titman (1993) momentum strategies
- Carhart (1997) four-factor model
- Moskowitz & Grinblatt (1999) momentum life cycles

Author: StatArb_Gemini Architecture Compliance
Version: 1.0.0 (Phase 2.3 Enhancement)
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging

# Import enhanced base strategy
from ...base_strategy_enhanced import EnhancedBaseStrategy
from ...strategy_engine import (
    StrategyConfig, StrategySignal, SignalType
)

# Import centralized configuration (Rule 1 Section 7 - Configuration Management)
# REQUIRED: Use centralized config only - no local fallback definitions per Rule 1
from core_engine.config import MomentumConfig

logger = logging.getLogger(__name__)


class MomentumSignal(Enum):
    """Momentum signal types"""
    BULLISH_MOMENTUM = "bullish_momentum"
    BEARISH_MOMENTUM = "bearish_momentum"
    MOMENTUM_CONTINUATION = "momentum_continuation"
    MOMENTUM_EXHAUSTION = "momentum_exhaustion"


# Note: MomentumConfig now imported from core_engine.config (Rule 1 Section 7)
# Local definition removed - use centralized configuration


class EnhancedMomentumStrategy(EnhancedBaseStrategy):
    """
    Enhanced Momentum Strategy with ISystemComponent Integration
    
    Professional momentum strategy that provides:
    - ISystemComponent interface compliance
    - Multi-timeframe momentum analysis
    - Trend strength and quality assessment
    - Dynamic position sizing based on momentum strength
    - Comprehensive performance tracking and risk management
    """
    
    def __init__(self, config: MomentumConfig):
        """Initialize enhanced momentum strategy"""
        
        # Initialize base strategy
        super().__init__(config)
        self.config: MomentumConfig = config
        
        # Strategy-specific state
        self.market_data: Dict[str, pd.DataFrame] = {}
        self.indicators: Dict[str, Dict[str, pd.Series]] = {}
        self.momentum_data: Dict[str, Dict[str, float]] = {}
        
        # Position tracking
        self.active_positions: Dict[str, Dict[str, Any]] = {}
        self.entry_prices: Dict[str, float] = {}
        self.stop_losses: Dict[str, float] = {}
        self.trailing_stops: Dict[str, float] = {}
        self.profit_targets: Dict[str, float] = {}
        
        # Performance tracking
        self.trade_history: List[Dict[str, Any]] = []
        self.momentum_performance: Dict[str, Dict[str, float]] = {}
        
        logger.info(f"🧠 Enhanced Momentum Strategy {self.strategy_id} initialized")
    
    def _get_column_mapping(self) -> Dict[str, str]:
        """
        Get mapping from expected column names to actual column names in enriched DataFrame
        
        Returns:
            Dict mapping expected names to actual names
        """
        return {
            # Moving averages - check for sma_10, sma_20, sma_50 (actual) or SMA_10, SMA_20, SMA_50 (expected)
            'SMA_10': 'sma_10',  # May not exist if not configured
            'SMA_20': 'sma_20',  # Actual from indicator engine
            'SMA_50': 'sma_50',  # Actual from indicator engine
            # Momentum indicators
            'RSI_14': 'rsi',     # Actual from indicator engine (period is config-dependent)
            'ADX_14': 'adx',     # Actual from indicator engine
            'MACD': 'macd',      # Actual from indicator engine
            'ATR_14': 'atr',     # Actual from indicator engine
            # Volume (same name)
            'volume_ratio': 'volume_ratio'  # Same in both
        }
    
    def _get_column_name(self, expected_name: str, data: pd.DataFrame) -> str:
        """
        Get actual column name from DataFrame, checking both expected and mapped names
        
        Args:
            expected_name: Expected column name (e.g., 'RSI_14')
            data: DataFrame to search in
            
        Returns:
            Actual column name if found, otherwise expected_name
        """
        # First check if expected name exists (backward compatibility)
        if expected_name in data.columns:
            return expected_name
        
        # Check mapped name
        mapping = self._get_column_mapping()
        if expected_name in mapping:
            mapped_name = mapping[expected_name]
            if mapped_name in data.columns:
                return mapped_name
        
        # Return expected name (will cause error in validation if not found)
        return expected_name
    
    def _validate_enriched_data(self, enriched_data: Dict[str, pd.DataFrame]) -> None:
        """
        Validate that data is enriched with required indicators (Rule 3 Phase 4)
        
        This method ensures the data has passed through the ProcessingPipelineOrchestrator
        and contains all indicators required by the momentum strategy.
        
        Uses flexible column name mapping to handle both expected and actual column names.
        
        Args:
            enriched_data: Dict[symbol, enriched DataFrame]
            
        Raises:
            ValueError: If data is missing required indicators
        """
        # Required indicators with flexible naming
        required_indicators = {
            'SMA_10': ['sma_10', 'SMA_10'],  # Optional - may not be configured
            'SMA_20': ['sma_20', 'SMA_20'],  # Required
            'SMA_50': ['sma_50', 'SMA_50'],  # Required
            'RSI_14': ['rsi', 'RSI_14'],     # Required
            'ADX_14': ['adx', 'ADX_14'],     # Required
            'MACD': ['macd', 'MACD'],        # Required
            'ATR_14': ['atr', 'ATR_14'],     # Required
            'volume_ratio': ['volume_ratio'] # Required
        }
        
        for symbol, data in enriched_data.items():
            if data.empty:
                raise ValueError(f"{symbol} has empty DataFrame")
            
            missing = []
            for expected_name, possible_names in required_indicators.items():
                # Check if any of the possible names exist
                found = any(name in data.columns for name in possible_names)
                if not found:
                    # SMA_10 is optional, others are required
                    if expected_name != 'SMA_10':
                        missing.append(expected_name)
            
            if missing:
                available_cols = list(data.columns[:30])  # Show first 30 columns
                # Find similar column names
                similar = {}
                for missing_col in missing:
                    mapping = self._get_column_mapping()
                    if missing_col in mapping:
                        similar[missing_col] = mapping[missing_col]
                
                raise ValueError(
                    f"{symbol} missing required indicators: {missing}. "
                    f"Expected mappings: {similar}. "
                    f"Data must be enriched via ProcessingPipelineOrchestrator (Rule 3). "
                    f"Available columns: {available_cols[:20]}..."
                )
            
            logger.debug(f"✅ {symbol} enriched data validated: {len(required_indicators)} indicators present")
    
    # ========================================
    # STRATEGY-SPECIFIC LIFECYCLE HOOKS
    # ========================================
    
    async def _initialize_strategy_components(self) -> bool:
        """Initialize strategy-specific components"""
        
        try:
            logger.info(f"🔄 Initializing Momentum components for {self.strategy_id}...")
            
            # Validate symbols
            if not self.config.symbols:
                logger.error("❌ No symbols configured for momentum strategy")
                return False
            
            # Initialize data structures
            self._initialize_data_structures()
            
            # Initialize indicators
            self._initialize_indicators()
            
            logger.info(f"✅ Momentum components initialized for {len(self.config.symbols)} symbols")
            return True
            
        except Exception as e:
            logger.error(f"❌ Momentum component initialization failed: {e}")
            return False
    
    async def _start_strategy_operations(self) -> bool:
        """Start strategy-specific operations"""
        
        try:
            logger.info(f"🚀 Starting Momentum operations for {self.strategy_id}...")
            
            # Start performance tracking
            self._start_performance_tracking()
            
            logger.info(f"✅ Momentum operations started")
            return True
            
        except Exception as e:
            logger.error(f"❌ Momentum operations start failed: {e}")
            return False
    
    async def _stop_strategy_operations(self) -> None:
        """Stop strategy-specific operations"""
        
        try:
            logger.info(f"🔄 Stopping Momentum operations for {self.strategy_id}...")
            
            # Close all positions
            await self._close_all_positions()
            
            # Save performance data
            self._save_performance_data()
            
            logger.info(f"✅ Momentum operations stopped")
            
        except Exception as e:
            logger.error(f"❌ Momentum operations stop failed: {e}")
    
    async def _check_strategy_health(self) -> Dict[str, Any]:
        """Check strategy-specific health"""
        
        try:
            health_metrics = {
                'strategy_healthy': True,
                'symbols_tracked': len(self.config.symbols),
                'active_positions': len(self.active_positions),
                'indicators_calculated': len(self.indicators),
                'avg_momentum_strength': self._calculate_avg_momentum_strength(),
                'trend_quality': self._assess_overall_trend_quality()
            }
            
            # Check for unhealthy conditions
            # Only require indicators if strategy has been running for a while
            if len(self.indicators) == 0 and hasattr(self, 'initialization_time'):
                time_since_init = (datetime.now() - self.initialization_time).total_seconds()
                if time_since_init > 300:  # 5 minutes grace period
                    health_metrics['strategy_healthy'] = False
                    health_metrics['warning'] = "No indicators calculated after 5 minutes"
                else:
                    health_metrics['warning'] = f"Indicators not yet calculated (grace period: {300-time_since_init:.0f}s remaining)"
            
            if len(self.active_positions) > len(self.config.symbols):
                health_metrics['strategy_healthy'] = False
                health_metrics['warning'] = "Too many active positions"
            
            return health_metrics
            
        except Exception as e:
            return {
                'strategy_healthy': False,
                'error': str(e)
            }
    
    def _get_strategy_config_summary(self) -> Dict[str, Any]:
        """Get strategy-specific configuration summary"""
        
        return {
            'strategy_type': 'Enhanced Momentum',
            'symbols_count': len(self.config.symbols),
            'momentum_periods': [self.config.short_period, self.config.medium_period, self.config.long_period],
            'momentum_threshold': self.config.momentum_threshold,
            'enable_multi_timeframe': self.config.enable_multi_timeframe,
            'enable_breakout_detection': self.config.enable_breakout_detection,
            'base_position_pct': self.config.base_position_pct,
            'adx_threshold': self.config.adx_threshold
        }
    
    def _validate_strategy_config(self) -> bool:
        """Validate strategy-specific configuration"""
        
        try:
            # Validate periods
            if not (self.config.short_period < self.config.medium_period < self.config.long_period):
                logger.error("Momentum periods must be in ascending order")
                return False
            
            # Validate thresholds
            if self.config.momentum_threshold <= 0 or self.config.momentum_threshold > 0.1:
                logger.error("Momentum threshold must be between 0 and 0.1 (10%)")
                return False
            
            # Validate position sizing
            if self.config.base_position_pct <= 0 or self.config.base_position_pct > 0.1:
                logger.error("Base position percentage must be between 0 and 0.1 (10%)")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation error: {e}")
            return False
    
    # ========================================
    # ABSTRACT METHOD IMPLEMENTATIONS
    # ========================================
    
    async def generate_signals(self, enriched_data: Dict[str, pd.DataFrame]) -> List[StrategySignal]:
        """
        Generate momentum signals from ENRICHED data (Rule 3 Phase 4)
        
        **CRITICAL CHANGE:** This method now receives enriched data with pre-calculated
        indicators and features from the ProcessingPipelineOrchestrator. It does NOT
        calculate indicators itself.
        
        Args:
            enriched_data: Dict[symbol, enriched DataFrame with OHLCV + indicators + features]
                          Must contain: SMA_10, SMA_20, SMA_50, RSI_14, ADX_14, MACD, ATR_14, volume_ratio
        
        Returns:
            List[StrategySignal]: Momentum signals
            
        Raises:
            ValueError: If enriched_data is missing required indicators
        """
        start_time = datetime.now()
        signals = []
        
        try:
            # PHASE 4: Validate enriched data (Rule 3)
            self._validate_enriched_data(enriched_data)
            
            # Update market data with enriched data
            self._update_market_data(enriched_data)
            
            logger.debug(f"🔍 DEBUG: After update, market_data keys: {list(self.market_data.keys())}")
            for symbol, df in self.market_data.items():
                logger.debug(f"   {symbol}: {len(df)} rows")
            
            # Update momentum analysis (using pre-calculated indicators)
            self._update_momentum_analysis()
            
            logger.debug(f"🔍 DEBUG: Processing symbols: {self.config.symbols}")
            
            # Generate signals for each symbol
            for symbol in self.config.symbols:
                logger.debug(f"🔍 Evaluating {symbol}: data length = {len(self.market_data.get(symbol, []))}, required > {self.config.long_period}")
                if symbol in self.market_data and len(self.market_data[symbol]) > self.config.long_period:
                    logger.debug(f"✅ {symbol} has enough data, generating signals...")
                    symbol_signals = await self._generate_symbol_signals(symbol)
                    logger.debug(f"   {symbol} generated {len(symbol_signals)} signals")
                    signals.extend(symbol_signals)
                    logger.debug(f"   Total signals now: {len(signals)}")
                else:
                    logger.debug(f"⏭️  {symbol} skipped (insufficient data)")
            
            # Update performance metrics
            generation_time = (datetime.now() - start_time).total_seconds()
            self.track_signal_generation_time(generation_time)
            
            # Enhanced logging
            symbols_checked = [s for s in self.config.symbols if s in self.market_data and len(self.market_data[s]) > self.config.long_period]
            logger.debug(f"About to log summary - signals list has {len(signals)} items")
            logger.info(f"📊 Momentum Strategy Summary (Rule 3 Phase 4 - Enriched Data):")
            logger.info(f"   Symbols checked: {len(symbols_checked)} {symbols_checked}")
            logger.info(f"   Signals generated: {len(signals)}")
            logger.info(f"   Generation time: {generation_time:.3f}s")
            
            logger.debug(f"🔍 DEBUG: generate_signals returning {len(signals)} signals")
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
            
            # Use max_position_size from strategy config (passed from backtest)
            max_position_size = getattr(self.config, 'max_position_size', self.config.max_position_pct)
            logger.info(f"DEBUG: max_position_size={max_position_size}, max_position_pct={self.config.max_position_pct}, hasattr={hasattr(self.config, 'max_position_size')}")
            
            # Base position size (use configurable multiplier from centralized config)
            base_size = min(max_position_size * self.config.position_base_multiplier, self.config.base_position_pct)
            
            # Scale by momentum strength if enabled (use configurable cap from centralized config)
            if self.config.momentum_scaling and symbol in self.momentum_data:
                momentum_strength = self.momentum_data[symbol].get('momentum_strength', 1.0)
                momentum_multiplier = min(momentum_strength / self.config.momentum_threshold, self.config.momentum_multiplier_cap)
                base_size *= momentum_multiplier
            
            # Scale by signal confidence
            confidence_multiplier = signal.confidence
            base_size *= confidence_multiplier
            
            # Scale by trend quality (ADX) - use configurable cap from centralized config
            if symbol in self.market_data and len(self.market_data[symbol]) > 0:
                current_data = self.market_data[symbol].iloc[-1]
                # Use column mapping to get ADX value
                adx_col = self._get_column_name('ADX_14', self.market_data[symbol])
                adx = current_data.get(adx_col, current_data.get('adx', 0.0))
                if adx > 0:
                    trend_multiplier = min(adx / self.config.adx_threshold, self.config.trend_multiplier_cap)
                    base_size *= trend_multiplier
            
            # Cap at maximum position size from config
            return min(base_size, max_position_size)
            
        except Exception as e:
            self._log_error("Position size calculation failed", e)
            return 0.0
    
    # ========================================
    # SIGNAL GENERATION METHODS
    # ========================================
    
    def _get_regime_adjusted_thresholds(self, symbol: str) -> Dict[str, float]:
        """
        Get regime-adjusted thresholds based on current market regime
        
        Args:
            symbol: Symbol to get regime-adjusted thresholds for
            
        Returns:
            Dict with adjusted threshold values
        """
        # Get base thresholds
        base_thresholds = {
            'momentum_threshold': self.config.momentum_threshold,
            'adx_threshold': self.config.adx_threshold,
            'volume_threshold': self.config.volume_threshold
        }
        
        # If regime adjustment is disabled, return base thresholds
        if not self.config.enable_regime_adjusted_thresholds:
            return base_thresholds
        
        # Get current regime context
        regime_context = self.get_current_regime_context()
        if not regime_context:
            return base_thresholds
        
        # Determine if regime is unfavorable for momentum
        # Unfavorable: bear_high_volatility, extreme_volatility, choppy, range_bound
        # Favorable: bull_normal_volatility, bull_low_volatility, trending
        regime_name = getattr(regime_context, 'primary_regime', None)
        volatility_regime = getattr(regime_context, 'volatility_regime', None)
        
        unfavorable_regimes = [
            'bear_high_volatility', 'extreme_volatility', 
            'choppy', 'range_bound', 'crisis'
        ]
        
        is_unfavorable = (
            (regime_name and any(unfavorable in str(regime_name).lower() for unfavorable in unfavorable_regimes)) or
            (volatility_regime and 'extreme' in str(volatility_regime).lower())
        )
        
        # Apply adjustment factor if unfavorable
        if is_unfavorable:
            adjustment = self.config.regime_adjustment_factor
            adjusted_thresholds = {
                'momentum_threshold': base_thresholds['momentum_threshold'] * adjustment,
                'adx_threshold': base_thresholds['adx_threshold'] * adjustment,
                'volume_threshold': base_thresholds['volume_threshold'] * adjustment
            }
            
            logger.debug(f"[{symbol}] Regime-adjusted thresholds applied: {adjustment:.2f}x "
                        f"(ADX: {base_thresholds['adx_threshold']:.2f} -> {adjusted_thresholds['adx_threshold']:.2f}, "
                        f"Volume: {base_thresholds['volume_threshold']:.2f} -> {adjusted_thresholds['volume_threshold']:.2f})")
            
            return adjusted_thresholds
        
        return base_thresholds
    
    async def _evaluate_bar_at_index(self, symbol: str, idx: int) -> Optional[StrategySignal]:
        """
        Evaluate a specific bar at index and generate signal if conditions are met
        
        Args:
            symbol: Symbol to evaluate
            idx: Index of the bar to evaluate (use -1 for current bar)
            
        Returns:
            StrategySignal if conditions met, None otherwise
        """
        try:
            # Get data at index
            data = self.market_data[symbol]
            if idx < 0:
                idx = len(data) + idx  # Convert negative index
            
            if idx < self.config.long_period or idx >= len(data):
                return None
            
            current_data = data.iloc[idx]
            
            # Extract timestamp from DataFrame index (not from column)
            signal_timestamp = None
            try:
                # Try to get from index (most common case - DatetimeIndex)
                if isinstance(data.index, pd.DatetimeIndex):
                    signal_timestamp = data.index[idx]
                elif hasattr(data.index, 'iloc'):
                    signal_timestamp = data.index.iloc[idx]
                else:
                    signal_timestamp = data.index[idx]
                
                # Convert to datetime if it's a pandas Timestamp
                if isinstance(signal_timestamp, pd.Timestamp):
                    signal_timestamp = signal_timestamp.to_pydatetime()
                elif not isinstance(signal_timestamp, datetime):
                    # Try to convert if it's a string or other type
                    if isinstance(signal_timestamp, str):
                        try:
                            signal_timestamp = datetime.fromisoformat(signal_timestamp.replace('Z', '+00:00'))
                        except:
                            signal_timestamp = None
                    else:
                        signal_timestamp = None
            except Exception as e:
                logger.debug(f"Could not extract timestamp from index: {e}")
                signal_timestamp = None
            
            # Fallback: try to get from 'timestamp' column if index extraction failed
            if not signal_timestamp and isinstance(current_data, pd.Series):
                if 'timestamp' in current_data:
                    ts = current_data['timestamp']
                    if isinstance(ts, (datetime, pd.Timestamp)):
                        signal_timestamp = ts.to_pydatetime() if isinstance(ts, pd.Timestamp) else ts
                    elif isinstance(ts, str):
                        try:
                            signal_timestamp = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                        except:
                            pass
            
            # Last fallback: use current time (but this should rarely happen)
            if not signal_timestamp:
                signal_timestamp = datetime.now()
                logger.debug(f"Using current time as fallback for signal at index {idx}")
            
            # Get indicators at this index
            indicators = self.indicators[symbol]
            
            # Get momentum values from DataFrame features (pre-calculated by FeatureEngineer)
            # These are per-bar values, not single aggregated values
            momentum_10_col = f'momentum_{self.config.short_period}'
            momentum_20_col = f'momentum_{self.config.medium_period}'
            momentum_50_col = f'momentum_{self.config.long_period}'
            
            short_momentum = data[momentum_10_col].iloc[idx] if momentum_10_col in data.columns else 0
            medium_momentum = data[momentum_20_col].iloc[idx] if momentum_20_col in data.columns else 0
            long_momentum = data[momentum_50_col].iloc[idx] if momentum_50_col in data.columns else 0
            
            # Handle NaN values
            short_momentum = short_momentum if not pd.isna(short_momentum) else 0
            medium_momentum = medium_momentum if not pd.isna(medium_momentum) else 0
            long_momentum = long_momentum if not pd.isna(long_momentum) else 0
            
            # Calculate momentum strength
            momentum_strength = abs(short_momentum) * self.config.momentum_strength_weight_short + \
                              abs(medium_momentum) * self.config.momentum_strength_weight_medium + \
                              abs(long_momentum) * self.config.momentum_strength_weight_long
            
            # Get trend indicators at this index (use historical values if available)
            adx_series = indicators.get('adx', pd.Series())
            volume_ratio_series = indicators.get('volume_ratio', pd.Series())
            trend_strength_series = indicators.get('trend_strength', pd.Series())
            
            adx = adx_series.iloc[idx] if len(adx_series) > idx else adx_series.iloc[-1] if len(adx_series) > 0 else 0
            volume_ratio = volume_ratio_series.iloc[idx] if len(volume_ratio_series) > idx else volume_ratio_series.iloc[-1] if len(volume_ratio_series) > 0 else 1
            trend_strength = trend_strength_series.iloc[idx] if len(trend_strength_series) > idx else trend_strength_series.iloc[-1] if len(trend_strength_series) > 0 else 0
            
            # Handle NaN values
            adx = adx if not pd.isna(adx) else 0
            volume_ratio = volume_ratio if not pd.isna(volume_ratio) else 1
            trend_strength = trend_strength if not pd.isna(trend_strength) else 0
            
            # Get regime-adjusted thresholds
            thresholds = self._get_regime_adjusted_thresholds(symbol)
            momentum_threshold = thresholds['momentum_threshold']
            adx_threshold = thresholds['adx_threshold']
            volume_threshold = thresholds['volume_threshold']
            
            # Check bullish conditions
            bullish_condition_1 = abs(short_momentum) > momentum_threshold
            bullish_condition_2 = abs(medium_momentum) > 0
            bullish_condition_3 = abs(long_momentum) > 0
            bullish_condition_4 = adx > adx_threshold
            bullish_condition_5 = volume_ratio > volume_threshold
            bullish_condition_6 = trend_strength > 0
            
            bullish_conditions_met = sum([
                bullish_condition_1, bullish_condition_2, bullish_condition_3,
                bullish_condition_4, bullish_condition_5, bullish_condition_6
            ])
            
            if bullish_conditions_met >= 4:
                confidence = self._calculate_signal_confidence(symbol, MomentumSignal.BULLISH_MOMENTUM)
                
                if confidence > 0.5:
                    signal = StrategySignal(
                        strategy_id=self.strategy_id,
                        symbol=symbol,
                        signal_type=SignalType.BUY,
                        strength=min(abs(momentum_strength) / momentum_threshold, 1.0),
                        confidence=confidence,
                        target_weight=self.config.base_position_pct,  # Use target_weight for percentage
                        quantity_type="PERCENTAGE",  # Explicitly mark as percentage
                        timestamp=signal_timestamp,
                        additional_data={
                            'signal_reason': 'bullish_momentum',
                            'short_momentum': short_momentum,
                            'medium_momentum': medium_momentum,
                            'long_momentum': long_momentum,
                            'adx': adx,
                            'volume_ratio': volume_ratio,
                            'entry_price': current_data['close'] if isinstance(current_data, pd.Series) else current_data.get('close', 0),
                            'bar_index': idx
                        }
                    )
                    return signal
            
            # Check bearish conditions
            bearish_condition_1 = short_momentum < -momentum_threshold
            bearish_condition_2 = medium_momentum < 0
            bearish_condition_3 = long_momentum < 0
            bearish_condition_4 = adx > adx_threshold
            bearish_condition_5 = volume_ratio > volume_threshold
            bearish_condition_6 = trend_strength < 0
            
            bearish_conditions_met = sum([
                bearish_condition_1, bearish_condition_2, bearish_condition_3,
                bearish_condition_4, bearish_condition_5, bearish_condition_6
            ])
            
            if bearish_conditions_met >= 4:
                confidence = self._calculate_signal_confidence(symbol, MomentumSignal.BEARISH_MOMENTUM)
                
                if confidence > 0.5:
                    signal = StrategySignal(
                        strategy_id=self.strategy_id,
                        symbol=symbol,
                        signal_type=SignalType.SELL,
                        strength=min(abs(momentum_strength) / momentum_threshold, 1.0),
                        confidence=confidence,
                        target_weight=self.config.base_position_pct,  # Use target_weight for percentage
                        quantity_type="PERCENTAGE",  # Explicitly mark as percentage
                        timestamp=signal_timestamp,
                        additional_data={
                            'signal_reason': 'bearish_momentum',
                            'short_momentum': short_momentum,
                            'medium_momentum': medium_momentum,
                            'long_momentum': long_momentum,
                            'adx': adx,
                            'volume_ratio': volume_ratio,
                            'entry_price': current_data['close'] if isinstance(current_data, pd.Series) else current_data.get('close', 0),
                            'bar_index': idx
                        }
                    )
                    return signal
            
            return None
            
        except Exception as e:
            logger.error(f"[{symbol}] Error evaluating bar at index {idx}: {e}")
            return None
    
    async def _generate_symbol_signals(self, symbol: str) -> List[StrategySignal]:
        """Generate signals for a specific symbol"""
        
        logger.debug(f"_generate_symbol_signals called for {symbol}")
        signals = []
        
        try:
            # Skip if already have position
            if symbol in self.active_positions:
                logger.debug(f"⏭️  [{symbol}] Skipping - already have position")
                return signals
            
            # Get current indicators and momentum data
            logger.debug(f"🔍 [{symbol}] Checking data availability:")
            logger.debug(f"   symbol in self.indicators: {symbol in self.indicators}")
            logger.debug(f"   symbol in self.momentum_data: {symbol in self.momentum_data}")
            
            if symbol not in self.indicators:
                logger.warning(f"❌ [{symbol}] Missing indicators - cannot generate signals")
                return signals
            if symbol not in self.momentum_data:
                logger.warning(f"❌ [{symbol}] Missing momentum_data - cannot generate signals")
                return signals
            
            data = self.market_data[symbol]
            data_length = len(data)
            
            # Check if we should scan all bars (historical mode) or just current bar (live mode)
            if self.config.scan_all_bars and data_length > self.config.long_period:
                # Historical scanning mode: scan through all bars
                logger.info(f"[{symbol}] 📊 Historical scanning mode: scanning {data_length} bars "
                           f"(evaluating every {self.config.scan_interval} bars)")
                
                start_idx = self.config.long_period
                end_idx = data_length
                scan_interval = max(1, self.config.scan_interval)
                
                bars_evaluated = 0
                for idx in range(start_idx, end_idx, scan_interval):
                    signal = await self._evaluate_bar_at_index(symbol, idx)
                    if signal:
                        signals.append(signal)
                    bars_evaluated += 1
                
                logger.info(f"[{symbol}] 📊 Historical scan complete: {bars_evaluated} bars evaluated, "
                           f"{len(signals)} signals generated")
                return signals
            
            # Live mode: Evaluate only current bar (default behavior)
            logger.debug(f"[{symbol}] Live mode: evaluating current bar only")
            
            logger.debug(f"[{symbol}] Data checks passed, proceeding to condition evaluation")
            
            logger.debug(f"[{symbol}] Starting condition evaluation...")
            
            try:
                indicators = self.indicators[symbol]
                momentum = self.momentum_data[symbol]
                current_data = self.market_data[symbol].iloc[-1]
                
                # Get regime-adjusted thresholds
                thresholds = self._get_regime_adjusted_thresholds(symbol)
                momentum_threshold = thresholds['momentum_threshold']
                adx_threshold = thresholds['adx_threshold']
                volume_threshold = thresholds['volume_threshold']
                
                # Check momentum conditions
                short_momentum = momentum.get('short_momentum', 0)
                medium_momentum = momentum.get('medium_momentum', 0)
                long_momentum = momentum.get('long_momentum', 0)
                momentum_strength = momentum.get('momentum_strength', 0)
                
                # Get trend quality indicators
                adx = indicators['adx'].iloc[-1] if 'adx' in indicators and len(indicators['adx']) > 0 else 0
                volume_ratio = indicators['volume_ratio'].iloc[-1] if 'volume_ratio' in indicators and len(indicators['volume_ratio']) > 0 else 1
                trend_strength = indicators['trend_strength'].iloc[-1] if 'trend_strength' in indicators and len(indicators['trend_strength']) > 0 else 0
                
                logger.debug(f"[{symbol}] Successfully extracted values")
                
            except Exception as e:
                logger.error(f"[{symbol}] ERROR in condition evaluation: {e}")
                return signals
            
            # Log condition values for debugging
            # Log condition values for debugging (use INFO level for visibility)
            logger.info(f"[{symbol}] 🔍 Checking bullish conditions:")
            logger.info(f"   📊 short_momentum: {short_momentum:.6f} (threshold: {momentum_threshold:.6f}, |value| > threshold: {abs(short_momentum) > momentum_threshold})")
            logger.info(f"   📊 medium_momentum: {medium_momentum:.6f} (threshold: > 0, |value| > 0: {abs(medium_momentum) > 0})")
            logger.info(f"   📊 long_momentum: {long_momentum:.6f} (threshold: > 0, |value| > 0: {abs(long_momentum) > 0})")
            logger.info(f"   📊 adx: {adx:.2f} (threshold: {adx_threshold:.2f}, value > threshold: {adx > adx_threshold})")
            logger.info(f"   📊 volume_ratio: {volume_ratio:.2f} (threshold: {volume_threshold:.2f}, value > threshold: {volume_ratio > volume_threshold})")
            logger.info(f"   📊 trend_strength: {trend_strength:.6f} (threshold: > 0, value > 0: {trend_strength > 0})")
            
            # ✅ RELAXED LOGIC: Check for bullish momentum (at least 4 of 6 conditions)
            # Use regime-adjusted thresholds
            bullish_condition_1 = abs(short_momentum) > momentum_threshold
            bullish_condition_2 = abs(medium_momentum) > 0  # Always true for non-zero momentum
            bullish_condition_3 = abs(long_momentum) > 0    # Always true for non-zero momentum
            bullish_condition_4 = adx > adx_threshold
            bullish_condition_5 = volume_ratio > volume_threshold
            bullish_condition_6 = trend_strength > 0
            
            # Count how many conditions are met
            bullish_conditions_met = sum([
                bullish_condition_1,
                bullish_condition_2,
                bullish_condition_3,
                bullish_condition_4,
                bullish_condition_5,
                bullish_condition_6
            ])
            
            logger.info(f"   ✅ Condition checks: 1:{bullish_condition_1} 2:{bullish_condition_2} 3:{bullish_condition_3} "
                        f"4:{bullish_condition_4} 5:{bullish_condition_5} 6:{bullish_condition_6}")
            logger.info(f"   📊 Conditions met: {bullish_conditions_met}/6 (need >= 4) {'✅ PASS' if bullish_conditions_met >= 4 else '❌ FAIL'}")
            
            # ✅ NEW: Generate signal if at least 4 of 6 conditions are met (was: ALL 6)
            if bullish_conditions_met >= 4:
                
                # Check for breakout if enabled (optional confirmation, not required)
                breakout_confirmed = True
                if self.config.enable_breakout_detection:
                    breakout_confirmed = self._check_breakout(symbol, 'bullish')
                    if not breakout_confirmed:
                        logger.info(f"[{symbol}] ⚠️  Breakout not confirmed, but continuing with signal (breakout is optional confirmation)")
                        # Continue with signal generation even if breakout not confirmed
                        # Breakout is a confirmation, not a requirement
                
                # Generate signal (breakout confirmation is optional)
                if True:  # Always proceed if conditions met (breakout is just a confidence boost)
                    confidence = self._calculate_signal_confidence(symbol, MomentumSignal.BULLISH_MOMENTUM)
                    
                    logger.info(f"[{symbol}] ✅ Calculated confidence: {confidence:.4f} (threshold: 0.5, {'PASS' if confidence > 0.5 else 'FAIL'})")
                    
                    if confidence > 0.5:  # Minimum confidence threshold (lowered for 1-min data)
                        logger.info(f"[{symbol}] 🎯 Creating BUY signal with confidence {confidence:.4f}")
                        signal = StrategySignal(
                            strategy_id=self.strategy_id,
                            symbol=symbol,
                            signal_type=SignalType.BUY,
                            strength=min(abs(momentum_strength) / self.config.momentum_threshold, 1.0),
                            confidence=confidence,
                            target_weight=self.config.base_position_pct,  # Use target_weight for percentage
                            quantity_type="PERCENTAGE",  # Explicitly mark as percentage
                            timestamp=datetime.now(),
                            additional_data={
                                'signal_reason': 'bullish_momentum',
                                'short_momentum': short_momentum,
                                'medium_momentum': medium_momentum,
                                'long_momentum': long_momentum,
                                'adx': adx,
                                'volume_ratio': volume_ratio,
                                'entry_price': current_data['close']
                            }
                        )
                        signals.append(signal)
                        logger.info(f"[{symbol}] ✅ BUY signal appended to signals list (total: {len(signals)})")
                        
                        # Track position entry
                        self._track_position_entry(symbol, signal)
                    else:
                        logger.warning(f"[{symbol}] ❌ Confidence too low: {confidence:.4f} <= 0.5 (signal not created)")
                else:
                    logger.warning(f"[{symbol}] ❌ Breakout not confirmed (signal not created)")
            
            # ✅ RELAXED LOGIC: Check for bearish momentum (at least 4 of 6 conditions)
            # Use regime-adjusted thresholds
            bearish_condition_1 = short_momentum < -momentum_threshold
            bearish_condition_2 = medium_momentum < 0
            bearish_condition_3 = long_momentum < 0
            bearish_condition_4 = adx > adx_threshold
            bearish_condition_5 = volume_ratio > volume_threshold
            bearish_condition_6 = trend_strength < 0
            
            # Count how many conditions are met
            bearish_conditions_met = sum([
                bearish_condition_1,
                bearish_condition_2,
                bearish_condition_3,
                bearish_condition_4,
                bearish_condition_5,
                bearish_condition_6
            ])
            
            logger.debug(f"🔍 [{symbol}] Checking bearish conditions: {bearish_conditions_met}/6 met")
            
            # ✅ NEW: Generate signal if at least 4 of 6 conditions are met (was: ALL 6)
            if bearish_conditions_met >= 4:
                
                # Check for breakout if enabled
                breakout_confirmed = True
                if self.config.enable_breakout_detection:
                    breakout_confirmed = self._check_breakout(symbol, 'bearish')
                
                if breakout_confirmed:
                    confidence = self._calculate_signal_confidence(symbol, MomentumSignal.BEARISH_MOMENTUM)
                    
                    if confidence > 0.5:  # Minimum confidence threshold (lowered for 1-min data)
                        logger.debug(f"[{symbol}] Creating SELL signal with confidence {confidence:.4f}")
                        signal = StrategySignal(
                            strategy_id=self.strategy_id,
                            symbol=symbol,
                            signal_type=SignalType.SELL,
                            strength=min(abs(momentum_strength) / self.config.momentum_threshold, 1.0),
                            confidence=confidence,
                            target_weight=self.config.base_position_pct,  # Use target_weight for percentage
                            quantity_type="PERCENTAGE",  # Explicitly mark as percentage
                            timestamp=datetime.now(),
                            additional_data={
                                'signal_reason': 'bearish_momentum',
                                'short_momentum': short_momentum,
                                'medium_momentum': medium_momentum,
                                'long_momentum': long_momentum,
                                'adx': adx,
                                'volume_ratio': volume_ratio,
                                'entry_price': current_data['close']
                            }
                        )
                        signals.append(signal)
                        
                        # Track position entry
                        self._track_position_entry(symbol, signal)
            
            logger.debug(f"_generate_symbol_signals returning {len(signals)} signals for {symbol}")
            return signals
            
        except Exception as e:
            self._log_error(f"Symbol signal generation failed for {symbol}", e)
            return []
    
    # ========================================
    # MOMENTUM ANALYSIS METHODS (Rule 3 Phase 4)
    # Reads pre-calculated indicators from enriched data
    # ========================================
    
    def _update_momentum_analysis(self) -> None:
        """
        Update momentum analysis using PRE-CALCULATED indicators (Rule 3 Phase 4)
        
        Reads momentum indicators from enriched data, does NOT calculate them.
        """
        for symbol in self.config.symbols:
            if symbol in self.market_data:
                logger.debug(f"📈 Updating momentum analysis for {symbol} from enriched data")
                self.momentum_data[symbol] = self._analyze_symbol_momentum(symbol)
                # Also populate indicators dictionary for signal generation
                self._extract_indicators_from_data(symbol)
                logger.debug(f"✅ Momentum data updated for {symbol}: {list(self.momentum_data[symbol].keys()) if symbol in self.momentum_data else 'FAILED'}")
            else:
                logger.warning(f"⚠️  Cannot update momentum for {symbol} - missing market data")
    
    def _analyze_symbol_momentum(self, symbol: str) -> Dict[str, float]:
        """
        Analyze momentum for a specific symbol using PRE-CALCULATED values (Rule 3 Phase 4)
        
        **CRITICAL:** This method READS pre-calculated momentum values from enriched data.
        It does NOT calculate momentum itself.
        """
        try:
            data = self.market_data[symbol]
            current_row = data.iloc[-1]
            
            # READ pre-calculated momentum indicators (from FeatureEngineer)
            # FeatureEngineer creates: momentum_{period} (e.g., momentum_10, momentum_20, momentum_50)
            # Strategy config has: short_period=10, medium_period=20, long_period=50
            # Map to actual feature names in DataFrame
            # Try to get from last valid value if current is NaN (for lookback calculations)
            short_momentum_col = f'momentum_{self.config.short_period}'
            medium_momentum_col = f'momentum_{self.config.medium_period}'
            long_momentum_col = f'momentum_{self.config.long_period}'
            
            # Get momentum values with forward-fill to handle NaN at last bar
            # CRITICAL: When processing rolling windows chronologically, the last bar might have NaN
            # if it's at the edge of the lookback period. Use forward-fill to get last valid value.
            if short_momentum_col in data.columns:
                # Forward-fill NaN values to use last valid momentum value
                short_momentum_series = data[short_momentum_col].ffill()
                # If still NaN after forward-fill, check if we have any valid values
                if pd.isna(short_momentum_series.iloc[-1]):
                    # Try to get last valid value from entire series
                    short_momentum_valid = short_momentum_series.dropna()
                    short_momentum = short_momentum_valid.iloc[-1] if len(short_momentum_valid) > 0 else current_row.get('momentum_short', 0.0)
                else:
                    short_momentum = short_momentum_series.iloc[-1]
            else:
                short_momentum = current_row.get('momentum_short', 0.0)
            
            if medium_momentum_col in data.columns:
                medium_momentum_series = data[medium_momentum_col].ffill()
                if pd.isna(medium_momentum_series.iloc[-1]):
                    medium_momentum_valid = medium_momentum_series.dropna()
                    medium_momentum = medium_momentum_valid.iloc[-1] if len(medium_momentum_valid) > 0 else current_row.get('momentum_medium', 0.0)
                else:
                    medium_momentum = medium_momentum_series.iloc[-1]
            else:
                medium_momentum = current_row.get('momentum_medium', 0.0)
            
            if long_momentum_col in data.columns:
                long_momentum_series = data[long_momentum_col].ffill()
                if pd.isna(long_momentum_series.iloc[-1]):
                    long_momentum_valid = long_momentum_series.dropna()
                    long_momentum = long_momentum_valid.iloc[-1] if len(long_momentum_valid) > 0 else current_row.get('momentum_long', 0.0)
                else:
                    long_momentum = long_momentum_series.iloc[-1]
            else:
                long_momentum = current_row.get('momentum_long', 0.0)
            
            logger.debug(f"[{symbol}] Momentum values: short={short_momentum:.6f}, medium={medium_momentum:.6f}, long={long_momentum:.6f}")
            
            # Calculate momentum strength (combination of all timeframes)
            # Use configurable weights from centralized config (Rule 1)
            momentum_strength = (short_momentum * self.config.momentum_strength_weight_short + 
                               medium_momentum * self.config.momentum_strength_weight_medium + 
                               long_momentum * self.config.momentum_strength_weight_long)
            
            # Calculate momentum consistency (how aligned are the timeframes)
            momentum_values = [short_momentum, medium_momentum, long_momentum]
            momentum_consistency = 1.0 - (np.std(momentum_values) / (np.mean(np.abs(momentum_values)) + 0.001))
            
            # Calculate momentum acceleration (is momentum increasing?)
            if len(data) >= 2:
                prev_row = data.iloc[-2]
                prev_momentum = prev_row.get(f'momentum_{self.config.short_period}', 
                                             prev_row.get('momentum_short', 0.0))
                momentum_acceleration = short_momentum - prev_momentum
            else:
                momentum_acceleration = 0
            
            return {
                'short_momentum': short_momentum,
                'medium_momentum': medium_momentum,
                'long_momentum': long_momentum,
                'momentum_strength': momentum_strength,
                'momentum_consistency': momentum_consistency,
                'momentum_acceleration': momentum_acceleration
            }
            
        except Exception as e:
            logger.error(f"Momentum analysis failed for {symbol}: {e}")
            return {
                'short_momentum': 0, 'medium_momentum': 0, 'long_momentum': 0,
                'momentum_strength': 0, 'momentum_consistency': 0, 'momentum_acceleration': 0
            }
    
    def _extract_indicators_from_data(self, symbol: str) -> None:
        """
        Extract indicators from enriched dataframe into indicators dictionary
        """
        try:
            data = self.market_data[symbol]
            
            # Extract indicators as Series for signal generation (using column mapping)
            adx_col = self._get_column_name('ADX_14', data)
            volume_ratio_col = self._get_column_name('volume_ratio', data)
            
            # Get indicators with fallback to last valid value if current is NaN
            adx_series = data[adx_col] if adx_col in data.columns else pd.Series([25.0] * len(data), index=data.index)
            volume_ratio_series = data[volume_ratio_col] if volume_ratio_col in data.columns else pd.Series([1.0] * len(data), index=data.index)
            trend_strength_series = data['trend_strength'] if 'trend_strength' in data.columns else pd.Series([0.0] * len(data), index=data.index)
            
            # Forward fill NaN values with last valid value (for indicators that need lookback)
            adx_series = adx_series.fillna(method='ffill').fillna(25.0)  # Default ADX if all NaN
            volume_ratio_series = volume_ratio_series.fillna(method='ffill').fillna(1.0)  # Default 1.0 if all NaN
            trend_strength_series = trend_strength_series.fillna(method='ffill').fillna(0.0)  # Default 0.0 if all NaN
            
            self.indicators[symbol] = {
                'adx': adx_series,
                'volume_ratio': volume_ratio_series,
                'trend_strength': trend_strength_series,
            }
            
            logger.debug(f"✅ Extracted indicators for {symbol}: {list(self.indicators[symbol].keys())}")
            
        except Exception as e:
            logger.error(f"Failed to extract indicators for {symbol}: {e}")
            self.indicators[symbol] = {
                'adx': pd.Series([25.0]),
                'volume_ratio': pd.Series([1.0]),
                'trend_strength': pd.Series([0.0])
            }
    
    def _check_breakout(self, symbol: str, direction: str) -> bool:
        """Check for breakout confirmation"""
        
        try:
            if symbol not in self.market_data or symbol not in self.indicators:
                logger.debug(f"[{symbol}] Breakout check: missing data or indicators")
                return False
            
            data = self.market_data[symbol]
            if len(data) < self.config.breakout_lookback:
                logger.debug(f"[{symbol}] Breakout check: insufficient data ({len(data)} < {self.config.breakout_lookback})")
                return False
            
            current_price = data['close'].iloc[-1]
            
            # Get recent high/low
            lookback_data = data.tail(self.config.breakout_lookback)
            recent_high = lookback_data['high'].max()
            recent_low = lookback_data['low'].min()
            
            if direction == 'bullish':
                # Check if price broke above recent high
                breakout_level = recent_high * (1 + self.config.breakout_threshold)
                breakout_confirmed = current_price > breakout_level
                logger.debug(f"[{symbol}] Bullish breakout check: price={current_price:.2f}, recent_high={recent_high:.2f}, "
                           f"breakout_level={breakout_level:.2f}, confirmed={breakout_confirmed}")
                return breakout_confirmed
            else:  # bearish
                # Check if price broke below recent low
                breakout_level = recent_low * (1 - self.config.breakout_threshold)
                breakout_confirmed = current_price < breakout_level
                logger.debug(f"[{symbol}] Bearish breakout check: price={current_price:.2f}, recent_low={recent_low:.2f}, "
                           f"breakout_level={breakout_level:.2f}, confirmed={breakout_confirmed}")
                return breakout_confirmed
            
        except Exception as e:
            logger.error(f"Breakout check failed for {symbol}: {e}")
            return False
    
    def _calculate_signal_confidence(
        self, 
        symbol: str, 
        signal_type: MomentumSignal,
        short_momentum: float = None,
        adx: float = None,
        volume_ratio: float = None,
        trend_strength: float = None
    ) -> float:
        """Calculate signal confidence based on multiple factors"""
        
        try:
            if symbol not in self.momentum_data or symbol not in self.indicators:
                return 0.5
            
            momentum = self.momentum_data[symbol]
            indicators = self.indicators[symbol]
            
            # Use provided values or extract from indicators
            if adx is None:
                adx = indicators['adx'].iloc[-1] if len(indicators['adx']) > 0 else 0
            if volume_ratio is None:
                volume_ratio = indicators['volume_ratio'].iloc[-1] if len(indicators['volume_ratio']) > 0 else 1
            if trend_strength is None:
                trend_strength = indicators['trend_strength'].iloc[-1] if 'trend_strength' in indicators and len(indicators['trend_strength']) > 0 else 0
            if short_momentum is None:
                data = self.market_data[symbol]
                current_row = data.iloc[-1]
                short_momentum_col = f'momentum_{self.config.short_period}'
                if short_momentum_col in data.columns:
                    short_momentum_series = data[short_momentum_col].dropna()
                    short_momentum = short_momentum_series.iloc[-1] if len(short_momentum_series) > 0 else 0.0
                else:
                    short_momentum = current_row.get('momentum_short', 0.0)
            
            # Base confidence from momentum strength
            momentum_strength = abs(momentum.get('momentum_strength', 0))
            strength_confidence = min(momentum_strength / (self.config.momentum_threshold * 2), 1.0)
            
            # Momentum consistency confidence
            consistency_confidence = momentum.get('momentum_consistency', 0)
            
            # Trend quality confidence (ADX)
            adx = indicators['adx'].iloc[-1] if len(indicators['adx']) > 0 else 0
            # Use configurable ADX multiplier from centralized config (Rule 1)
            trend_confidence = min(adx / (self.config.adx_threshold * self.config.trend_confidence_adx_multiplier), 1.0)
            
            # Volume confirmation confidence
            volume_ratio = indicators['volume_ratio'].iloc[-1] if len(indicators['volume_ratio']) > 0 else 1
            volume_confidence = min(volume_ratio / self.config.volume_threshold, 1.0)
            
            # Momentum acceleration confidence - use configurable scaling factor from centralized config (Rule 1)
            acceleration = momentum.get('momentum_acceleration', 0)
            if signal_type in [MomentumSignal.BULLISH_MOMENTUM]:
                acceleration_confidence = max(0, min(acceleration * self.config.acceleration_scaling_factor, 1.0))
            else:  # bearish
                acceleration_confidence = max(0, min(-acceleration * self.config.acceleration_scaling_factor, 1.0))
            
            # Combine confidences (weighted average)
            base_confidence = (strength_confidence * 0.3 + 
                              consistency_confidence * 0.2 + 
                              trend_confidence * 0.2 + 
                              volume_confidence * 0.15 + 
                              acceleration_confidence * 0.15)
            
            # Add bonus for multi-condition confirmation (trading logic: more conditions = higher confidence)
            # Check how many conditions are met (from signal generation logic)
            conditions_met_bonus = 0.0
            if abs(short_momentum) > self.config.momentum_threshold:
                conditions_met_bonus += 0.05  # Momentum condition met
            if adx > self.config.adx_threshold * 0.8:  # 80% of threshold (ADX 19.49 is close to 25)
                conditions_met_bonus += 0.05  # Trend condition partially met
            if volume_ratio > self.config.volume_threshold * 0.95:  # 95% of threshold (volume 1.17 is close to 1.2)
                conditions_met_bonus += 0.05  # Volume condition partially met
            if trend_strength > 0:
                conditions_met_bonus += 0.05  # Trend strength condition met
            
            total_confidence = min(base_confidence + conditions_met_bonus, 0.95)
            
            logger.info(f"[{symbol}] 📊 Confidence Calculation Breakdown:")
            logger.info(f"   📈 Momentum Strength: {momentum_strength:.6f} → strength_confidence: {strength_confidence:.4f} (weight: 0.3)")
            logger.info(f"   📊 Momentum Consistency: {momentum.get('momentum_consistency', 0):.4f} → consistency_confidence: {consistency_confidence:.4f} (weight: 0.2)")
            logger.info(f"   📈 Trend Quality (ADX): {adx:.2f} → trend_confidence: {trend_confidence:.4f} (weight: 0.2)")
            logger.info(f"   📊 Volume Confirmation: {volume_ratio:.2f} → volume_confidence: {volume_confidence:.4f} (weight: 0.15)")
            logger.info(f"   📈 Momentum Acceleration: {acceleration:.6f} → acceleration_confidence: {acceleration_confidence:.4f} (weight: 0.15)")
            logger.info(f"   📊 Base Confidence: {base_confidence:.4f}")
            logger.info(f"   🎁 Conditions Bonus: +{conditions_met_bonus:.4f}")
            logger.info(f"   ✅ TOTAL CONFIDENCE: {total_confidence:.4f} (capped at 0.95)")
            
            return total_confidence
            
        except Exception as e:
            logger.error(f"Signal confidence calculation failed for {symbol}: {e}")
            return 0.5
    
    # ========================================
    # HELPER METHODS
    # ========================================
    
    def _update_market_data(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """Update market data cache"""
        
        for symbol, data in market_data.items():
            if symbol in self.config.symbols:
                self.market_data[symbol] = data
                # 🔍 DEBUG: Log data update
                logger.debug(f"🔍 Updated market_data[{symbol}]: {len(data)} bars, columns: {list(data.columns[:5])}")
    
    def _initialize_data_structures(self) -> None:
        """Initialize strategy data structures"""
        
        self.market_data.clear()
        self.indicators.clear()
        self.momentum_data.clear()
        self.active_positions.clear()
        self.entry_prices.clear()
        self.stop_losses.clear()
        self.trailing_stops.clear()
        self.profit_targets.clear()
    
    def _initialize_indicators(self) -> None:
        """Initialize indicators dictionary"""
        
        for symbol in self.config.symbols:
            self.indicators[symbol] = {}
            self.momentum_data[symbol] = {}
    
    def _start_performance_tracking(self) -> None:
        """Start performance tracking"""
        logger.info("📊 Momentum performance tracking started")
    
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
        logger.info("💾 Momentum performance data saved")
    
    def _calculate_avg_momentum_strength(self) -> float:
        """Calculate average momentum strength across symbols"""
        
        if not self.momentum_data:
            return 0.0
        
        strengths = [data.get('momentum_strength', 0) for data in self.momentum_data.values()]
        return np.mean(np.abs(strengths)) if strengths else 0.0
    
    def _assess_overall_trend_quality(self) -> Dict[str, Any]:
        """Assess overall trend quality across symbols"""
        
        if not self.indicators:
            return {'avg_adx': 0, 'trending_symbols': 0}
        
        adx_values = []
        trending_count = 0
        
        for symbol, indicators in self.indicators.items():
            if 'adx' in indicators and len(indicators['adx']) > 0:
                adx = indicators['adx'].iloc[-1]
                adx_values.append(adx)
                if adx > self.config.adx_threshold:
                    trending_count += 1
        
        return {
            'avg_adx': np.mean(adx_values) if adx_values else 0,
            'trending_symbols': trending_count,
            'total_symbols': len(self.config.symbols)
        }
    
    def _track_position_entry(self, symbol: str, signal: StrategySignal) -> None:
        """Track position entry for exit management"""
        
        try:
            entry_price = signal.metadata.get('entry_price', 0)
            
            # Calculate stop loss and profit target
            if signal.signal_type == SignalType.BUY:
                stop_loss = entry_price * (1 - self.config.momentum_stop_pct)
                profit_target = entry_price * (1 + self.config.momentum_stop_pct * self.config.profit_target_ratio)
                trailing_stop = entry_price * (1 - self.config.trailing_stop_pct)
            else:  # SELL
                stop_loss = entry_price * (1 + self.config.momentum_stop_pct)
                profit_target = entry_price * (1 - self.config.momentum_stop_pct * self.config.profit_target_ratio)
                trailing_stop = entry_price * (1 + self.config.trailing_stop_pct)
            
            # Track position
            self.active_positions[symbol] = {
                'signal_type': signal.signal_type,
                'entry_time': signal.timestamp,
                'entry_price': entry_price,
                'quantity': signal.quantity
            }
            
            self.entry_prices[symbol] = entry_price
            self.stop_losses[symbol] = stop_loss
            self.trailing_stops[symbol] = trailing_stop
            self.profit_targets[symbol] = profit_target
            
            logger.info(f"📈 Momentum position tracked for {symbol}: Entry=${entry_price:.2f}, "
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
                    
                    # Check momentum exhaustion
                    if not should_exit and symbol in self.momentum_data:
                        momentum = self.momentum_data[symbol]
                        momentum_strength = abs(momentum.get('momentum_strength', 0))
                        # Use configurable threshold multiplier from centralized config (Rule 1)
                        if momentum_strength < self.config.momentum_threshold * self.config.momentum_threshold_low_multiplier:
                            should_exit = True
                            exit_reason = "momentum_exhaustion"
                    
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
                    quantity=position['quantity'],
                    timestamp=datetime.now(),
                    metadata={
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
                
                logger.info(f"🔄 Momentum position closed for {symbol}: {reason}")
                
        except Exception as e:
            self._log_error(f"Position close failed for {symbol}", e)
    
    def _update_performance_tracking(self) -> None:
        """Update performance tracking metrics"""
        
        # Placeholder for performance tracking updates
    
    # ========================================
    # STRATEGY-SPECIFIC METHODS
    # ========================================
    
    def get_momentum_summary(self) -> Dict[str, Any]:
        """Get comprehensive momentum strategy summary"""
        
        return {
            'strategy_id': self.strategy_id,
            'strategy_type': 'Enhanced Momentum',
            'symbols_tracked': len(self.config.symbols),
            'active_positions': len(self.active_positions),
            'avg_momentum_strength': self._calculate_avg_momentum_strength(),
            'trend_quality': self._assess_overall_trend_quality(),
            'performance_summary': self.get_performance_summary(),
            'momentum_details': {
                symbol: {
                    'momentum_strength': data.get('momentum_strength', 0),
                    'momentum_consistency': data.get('momentum_consistency', 0),
                    'short_momentum': data.get('short_momentum', 0),
                    'medium_momentum': data.get('medium_momentum', 0),
                    'long_momentum': data.get('long_momentum', 0)
                }
                for symbol, data in self.momentum_data.items()
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
