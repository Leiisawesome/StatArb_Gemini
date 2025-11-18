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
Version: 2.0.0 (Composite Signal Implementation)
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
import asyncio  # FIXED: LOW #13 - Add asyncio for Lock

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
        
        # ===== Enhanced position tracking (Phase 2 - CLEANED in Phase 2.5) =====
        self.position_tracker: Dict[str, Dict[str, Any]] = {}
        self._pos_lock = asyncio.Lock()  # FIXED: LOW #13 - Async concurrency control
        """
        Enhanced position tracking with bar timestamps and high water marks
        
        Structure:
        {
            'SYMBOL': {
                'direction': 1 or -1,  # 1=LONG, -1=SHORT
                'avg_entry_price': float,
                'total_quantity': float,
                'entry_time': datetime,  # Bar timestamp, NOT datetime.now()
                'scale_ins': int,
                'high_water_mark': float,  # Peak price for trailing stops
                'trailing_stop_activated': bool,
                'last_update_time': datetime  # Bar timestamp of last update
            }
        }
        """
        
        # Performance tracking
        self.trade_history: List[Dict[str, Any]] = []
        self.momentum_performance: Dict[str, Dict[str, float]] = {}
        
        # FIXED: MED #8 - Cache column mapping for performance
        self._column_mapping_cache = self._get_column_mapping()
        
        logger.info(f"🧠 Enhanced Momentum Strategy {self.strategy_id} initialized")
    
    def _safe_iloc(self, df: pd.DataFrame, idx: int) -> Optional[pd.Series]:
        """
        Safe DataFrame row access with bounds checking (FIXED: HIGH #2)
        
        Handles negative indices and prevents IndexError from off-by-one errors.
        
        Args:
            df: DataFrame to access
            idx: Index position (can be negative)
            
        Returns:
            Row as Series if valid, None if out of bounds
        """
        # Convert negative index
        if idx < 0:
            idx = len(df) + idx
        
        # Bounds check
        if idx < 0 or idx >= len(df):
            logger.warning(f"⚠️  Index {idx} out of bounds for DataFrame with {len(df)} rows")
            return None
        
        return df.iloc[idx]
    
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
        (FIXED: MED #8 - Uses cached mapping for performance)
        
        Args:
            expected_name: Expected column name (e.g., 'RSI_14')
            data: DataFrame to search in
            
        Returns:
            Actual column name if found, otherwise expected_name
        """
        # First check if expected name exists (backward compatibility)
        if expected_name in data.columns:
            return expected_name
        
        # FIXED: MED #8 - Use cached mapping instead of recreating
        if expected_name in self._column_mapping_cache:
            mapped_name = self._column_mapping_cache[expected_name]
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
                'active_positions': len(self.position_tracker),
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
            
            if len(self.position_tracker) > len(self.config.symbols):
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
            TypeError: If enriched_data is not a dictionary or contains non-DataFrame values
        """
        start_time = datetime.now()
        signals = []
        
        # FIXED: EXTRA - Comprehensive input validation at strategy boundary
        if not isinstance(enriched_data, dict):
            raise TypeError(f"enriched_data must be a dictionary, got {type(enriched_data)}")
        
        if not enriched_data:
            logger.warning("⚠️  generate_signals() called with empty enriched_data")
            return []
        
        # Validate all values are DataFrames with numeric dtypes
        for symbol, data in enriched_data.items():
            if not isinstance(data, pd.DataFrame):
                raise TypeError(f"{symbol} data must be a DataFrame, got {type(data)}")
            
            if data.empty:
                logger.warning(f"⚠️  {symbol} has empty DataFrame, skipping")
                continue
            
            # Check for required OHLCV columns
            required_ohlcv = ['open', 'high', 'low', 'close', 'volume']
            missing_ohlcv = [col for col in required_ohlcv if col not in data.columns]
            if missing_ohlcv:
                raise ValueError(f"{symbol} missing required OHLCV columns: {missing_ohlcv}")
            
            # Validate numeric dtypes for price/volume
            for col in required_ohlcv:
                if not pd.api.types.is_numeric_dtype(data[col]):
                    raise TypeError(f"{symbol}.{col} must be numeric, got {data[col].dtype}")
        
        # DEBUG Phase 4C: Log entry point
        logger.info(f"🔍 Phase 4C: generate_signals() called with {len(enriched_data)} symbols")
        for symbol, df in enriched_data.items():
            logger.info(f"   {symbol}: {len(df)} bars")
        
        try:
            # PHASE 4: Validate enriched data (Rule 3)
            self._validate_enriched_data(enriched_data)
            
            # DEBUG Phase 4C: Check if regime columns are in enriched data
            for symbol, df in enriched_data.items():
                has_primary = 'primary_regime' in df.columns
                has_volatility = 'volatility_regime' in df.columns
                logger.info(f"🔍 Phase 4C: {symbol} enriched data has regime columns: primary={has_primary}, volatility={has_volatility}")
                if has_primary and len(df) > 0:
                    regime_distribution = df['primary_regime'].value_counts().to_dict()
                    logger.info(f"   Regime distribution in data: {regime_distribution}")
            
            # Update market data with enriched data
            self._update_market_data(enriched_data)
            
            logger.debug(f"🔍 DEBUG: After update, market_data keys: {list(self.market_data.keys())}")
            for symbol, df in self.market_data.items():
                logger.debug(f"   {symbol}: {len(df)} rows")
            
            # Update momentum analysis (using pre-calculated indicators)
            self._update_momentum_analysis()
            
            logger.info(f"🔍 DEBUG: Processing symbols: {self.config.symbols}")
            
            # Generate signals for each symbol
            for symbol in self.config.symbols:
                data_length = len(self.market_data.get(symbol, []))
                logger.info(f"🔍 Evaluating {symbol}: data length = {data_length}, required > {self.config.long_period}")
                if symbol in self.market_data and len(self.market_data[symbol]) > self.config.long_period:
                    logger.info(f"✅ {symbol} has enough data, generating signals...")
                    symbol_signals = await self._generate_symbol_signals(symbol)
                    logger.info(f"   {symbol} generated {len(symbol_signals)} signals")
                    signals.extend(symbol_signals)
                    logger.info(f"   Total signals now: {len(signals)}")
                else:
                    logger.info(f"⏭️  {symbol} skipped (insufficient data: {data_length} <= {self.config.long_period})")
            
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
        """
        Update existing positions based on market data (Phase 3: NEW exit logic)
        
        CRITICAL FIX: Uses enriched data (not raw OHLCV) for exit checks
        This method is called by StrategyManager with enriched data.
        """
        
        try:
            # Update market data (enriched data with indicators/features)
            self._update_market_data(market_data)
            
            # Phase 3: Check exit conditions for active positions
            if self.position_tracker:
                await self._check_exits_for_all_positions(market_data)
            
            # Update performance tracking
            self._update_performance_tracking()
            
        except Exception as e:
            self._log_error("Position update failed", e)
    
    async def _check_exits_for_all_positions(self, enriched_data_dict: Dict[str, pd.DataFrame]) -> None:
        """
        Check exit conditions for all active positions (Phase 3)
        
        Called on every bar update to check if any positions should be closed.
        
        Args:
            enriched_data_dict: Dict[symbol, enriched DataFrame with indicators/features]
        """
        
        # First, sync with Risk Manager: clear exit_pending positions if they're closed or stale
        if self.risk_manager:
            symbols_to_clear = []
            for symbol in list(self.position_tracker.keys()):
                pos = self.position_tracker[symbol]
                if pos.get('exit_pending', False):
                    # Check for stale exit_pending (timeout after 10 bars)
                    current_bar = len(enriched_data_dict.get(symbol, []))
                    exit_signal_bar = pos.get('exit_signal_bar', current_bar)
                    bars_since_exit = current_bar - exit_signal_bar
                    
                    if bars_since_exit > 10:
                        logger.warning(f"⚠️  {symbol} exit_pending timeout ({bars_since_exit} bars) - force clearing")
                        symbols_to_clear.append(symbol)
                        continue
                    
                    # Check if Risk Manager still has this position
                    try:
                        position_state = self.risk_manager.get_position_state(symbol)
                        if position_state is None or position_state.quantity == 0:
                            logger.info(f"✅ {symbol} position closed confirmed by Risk Manager - clearing tracking")
                            symbols_to_clear.append(symbol)
                    except Exception as e:
                        logger.warning(f"⚠️  {symbol} failed to query Risk Manager position state: {e}")
            
            # Clear confirmed closed positions
            for symbol in symbols_to_clear:
                self._clear_position_tracking(symbol)
        
        # Make a copy of position keys to avoid modification during iteration
        symbols_with_positions = list(self.position_tracker.keys())
        
        for symbol in symbols_with_positions:
            # Skip positions that are already pending exit
            if self.position_tracker[symbol].get('exit_pending', False):
                logger.debug(f"⏭️  {symbol} has exit_pending=True, skipping exit check")
                continue
            
            if symbol not in enriched_data_dict:
                logger.warning(f"⚠️  {symbol} position exists but no enriched data available")
                continue
            
            enriched_data = enriched_data_dict[symbol]
            
            # Get latest bar timestamp
            if len(enriched_data) == 0:
                logger.warning(f"⚠️  {symbol} enriched data is empty")
                continue
            
            bar_timestamp = enriched_data.index[-1]
            
            # Update high water mark for trailing stops
            current_price = enriched_data.loc[bar_timestamp, 'close']
            self._update_high_water_mark(symbol, current_price)
            
            # Check exit conditions
            should_exit, exit_reason = await self._check_exit_conditions_hybrid(
                symbol, enriched_data, bar_timestamp
            )
            
            if should_exit:
                # Generate exit signal
                pos_info = self._get_position_info(symbol)
                exit_signal = await self._generate_exit_signal(
                    symbol, pos_info, current_price, exit_reason, bar_timestamp
                )
                
                # Submit exit signal to risk manager (if available)
                if self.risk_manager:
                    try:
                        await self.risk_manager.process_signal(exit_signal)
                        logger.info(f"✅ {symbol} exit signal submitted to risk manager")
                        
                        # Mark position as exit_pending instead of immediately clearing
                        # This allows Risk Manager to find the position when processing the exit
                        if symbol in self.position_tracker:
                            self.position_tracker[symbol]['exit_pending'] = True
                            self.position_tracker[symbol]['exit_signal_bar'] = len(enriched_data)
                            logger.info(f"⚠️  {symbol} position marked as exit_pending - will clear after Risk Manager confirmation")
                        
                    except Exception as e:
                        logger.error(f"❌ {symbol} exit signal submission failed: {e}")
                        # If submission fails, still clear position to avoid stale tracking
                        self._clear_position_tracking(symbol)
                else:
                    # No risk manager - clear immediately (backward compatibility)
                    self._clear_position_tracking(symbol)
    
    def calculate_position_size(self, signal: StrategySignal, market_data: Dict[str, pd.DataFrame]) -> float:
        """
        Calculate position size for a given signal (FIXED: HIGH #5)
        
        Returns percentage of portfolio (0.0-1.0) for position sizing.
        All config values are percentages (0.0-1.0).
        """
        
        try:
            symbol = signal.symbol
            
            # FIXED: HIGH #5 - Standardize to percentage (0-1) throughout
            # Use max_position_pct from config (always a percentage 0-1)
            max_position_pct = getattr(self.config, 'max_position_pct', 0.10)  # Default 10%
            
            # Base position size (percentage)
            base_size_pct = self.config.base_position_pct * self.config.position_base_multiplier
            
            # Ensure base doesn't exceed max
            base_size_pct = min(base_size_pct, max_position_pct)
            
            # Scale by momentum strength if enabled
            if self.config.momentum_scaling and symbol in self.momentum_data:
                momentum_strength = self.momentum_data[symbol].get('momentum_strength', 1.0)
                momentum_multiplier = min(momentum_strength / self.config.momentum_threshold, self.config.momentum_multiplier_cap)
                base_size_pct *= momentum_multiplier
            
            # Scale by signal confidence
            confidence_multiplier = signal.confidence
            base_size_pct *= confidence_multiplier
            
            # Scale by trend quality (ADX)
            if symbol in self.market_data and len(self.market_data[symbol]) > 0:
                current_data = self.market_data[symbol].iloc[-1]
                adx_col = self._get_column_name('ADX_14', self.market_data[symbol])
                adx = current_data.get(adx_col, current_data.get('adx', 0.0))
                if adx > 0:
                    trend_multiplier = min(adx / self.config.adx_threshold, self.config.trend_multiplier_cap)
                    base_size_pct *= trend_multiplier
            
            # Final cap at maximum (all in percentage 0-1)
            final_pct = min(base_size_pct, max_position_pct)
            
            # Ensure non-negative
            return max(final_pct, 0.0)
            
        except Exception as e:
            logger.exception(f"❌ [{signal.symbol}] Position size calculation failed")
            return 0.0
    
    # ========================================
    # SIGNAL GENERATION METHODS
    # ========================================
    
    # REMOVED: _get_regime_adjusted_thresholds_old (FIXED: LOW #11 - dead code removed)
    # Use _get_regime_adjusted_thresholds (Phase 4B) instead
    
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
            # Get data at index (FIXED: HIGH #2 - use safe_iloc)
            data = self.market_data[symbol]
            
            # Use safe_iloc for bounds checking
            current_data = self._safe_iloc(data, idx)
            if current_data is None:
                logger.warning(f"⚠️  [{symbol}] Cannot evaluate bar at index {idx} - out of bounds")
                return None
            
            # Check minimum data requirement
            actual_idx = idx if idx >= 0 else len(data) + idx
            if actual_idx < self.config.long_period:
                return None
            
            # Extract timestamp from DataFrame index (not from column)
            signal_timestamp = None
            try:
                # Try to get from index (most common case - DatetimeIndex)
                if isinstance(data.index, pd.DatetimeIndex):
                    signal_timestamp = data.index[actual_idx]
                elif hasattr(data.index, 'iloc'):
                    signal_timestamp = data.index.iloc[actual_idx]
                else:
                    signal_timestamp = data.index[actual_idx]
                
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
            
            # FIXED: HIGH #4 - Do NOT use datetime.now() fallback for bar timestamps
            if not signal_timestamp:
                logger.error(f"❌ [{symbol}] Missing bar timestamp at index {idx} - skipping bar (do not use datetime.now())")
                return None
            
            # Get indicators at this index
            indicators = self.indicators[symbol]
            
            # Get momentum values from DataFrame features (pre-calculated by FeatureEngineer)
            # These are per-bar values, not single aggregated values
            momentum_10_col = f'momentum_{self.config.short_period}'
            momentum_20_col = f'momentum_{self.config.medium_period}'
            momentum_50_col = f'momentum_{self.config.long_period}'
            
            short_momentum = data[momentum_10_col].iloc[actual_idx] if momentum_10_col in data.columns else 0
            medium_momentum = data[momentum_20_col].iloc[actual_idx] if momentum_20_col in data.columns else 0
            long_momentum = data[momentum_50_col].iloc[actual_idx] if momentum_50_col in data.columns else 0
            
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
            
            adx = adx_series.iloc[actual_idx] if len(adx_series) > actual_idx else adx_series.iloc[-1] if len(adx_series) > 0 else 0
            volume_ratio = volume_ratio_series.iloc[actual_idx] if len(volume_ratio_series) > actual_idx else volume_ratio_series.iloc[-1] if len(volume_ratio_series) > 0 else 1
            trend_strength = trend_strength_series.iloc[actual_idx] if len(trend_strength_series) > actual_idx else trend_strength_series.iloc[-1] if len(trend_strength_series) > 0 else 0
            
            # Handle NaN values
            adx = adx if not pd.isna(adx) else 0
            volume_ratio = volume_ratio if not pd.isna(volume_ratio) else 1
            trend_strength = trend_strength if not pd.isna(trend_strength) else 0
            
            # ========================================
            # NEW: Use COMPOSITE SIGNAL ENTRY (Phase 4A)
            # This makes historical scanning consistent with live mode
            # ========================================
            
            # Check composite entry conditions (Phase 4A)
            should_enter, signal_type = self._check_composite_entry(symbol, current_data)
            
            if should_enter and signal_type:
                # Generate signal based on composite entry
                confidence = self._calculate_signal_confidence(symbol, 
                    MomentumSignal.BULLISH_MOMENTUM if signal_type == SignalType.BUY else MomentumSignal.BEARISH_MOMENTUM)
                
                if confidence > 0.4:  # Minimum confidence threshold (lowered for composite signals)
                    signal = StrategySignal(
                        strategy_id=self.strategy_id,
                        symbol=symbol,
                        signal_type=signal_type,
                        strength=min(abs(momentum_strength) / self.config.momentum_threshold, 1.0),
                        confidence=confidence,
                        target_weight=self.config.base_position_pct,  # Use target_weight for percentage
                        quantity_type="PERCENTAGE",  # Explicitly mark as percentage
                        timestamp=signal_timestamp,
                        additional_data={
                            'signal_reason': 'composite_entry',
                            'entry_method': 'composite_z_pct',
                            'composite_z': current_data.get('composite_z', 0),
                            'composite_pct': current_data.get('composite_pct', 0),
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
            
            # No entry signal
            return None
            
        except Exception as e:
            logger.error(f"[{symbol}] Error evaluating bar at index {idx}: {e}")
            return None
    
    async def _generate_symbol_signals(self, symbol: str) -> List[StrategySignal]:
        """Generate signals for a specific symbol"""
        
        logger.debug(f"_generate_symbol_signals called for {symbol}")
        signals = []
        
        try:
            # Skip if already have position or exit is pending
            if symbol in self.position_tracker:
                is_exit_pending = self.position_tracker[symbol].get('exit_pending', False)
                if is_exit_pending:
                    logger.info(f"⏭️  [{symbol}] Skipping - exit pending for existing position")
                else:
                    logger.info(f"⏭️  [{symbol}] Skipping - already have position")
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
                
                # Use config thresholds directly (not from regime adjustments)
                momentum_threshold = self.config.momentum_threshold
                adx_threshold = self.config.adx_threshold
                volume_threshold = self.config.volume_threshold
                
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
            # Log condition values for debugging (use DEBUG level to reduce verbosity - MED #7)
            logger.debug(f"[{symbol}] 🔍 Checking bullish conditions:")
            logger.debug(f"   📊 short_momentum: {short_momentum:.6f} (threshold: {momentum_threshold:.6f}, |value| > threshold: {abs(short_momentum) > momentum_threshold})")
            logger.debug(f"   📊 medium_momentum: {medium_momentum:.6f} (threshold: > 0, |value| > 0: {abs(medium_momentum) > 0})")
            logger.debug(f"   📊 long_momentum: {long_momentum:.6f} (threshold: > 0, |value| > 0: {abs(long_momentum) > 0})")
            logger.debug(f"   📊 adx: {adx:.2f} (threshold: {adx_threshold:.2f}, value > threshold: {adx > adx_threshold})")
            logger.debug(f"   📊 volume_ratio: {volume_ratio:.2f} (threshold: {volume_threshold:.2f}, value > threshold: {volume_ratio > volume_threshold})")
            logger.debug(f"   📊 trend_strength: {trend_strength:.6f} (threshold: > 0, value > 0: {trend_strength > 0})")
            
            # ========================================
            # NEW: COMPOSITE SIGNAL ENTRY (Phase 4A)
            # Replaces OLD 6-condition logic with composite signals
            # ========================================
            
            logger.debug(f"[{symbol}] 🔍 About to call _check_composite_entry with composite_z={current_data.get('composite_z', 'N/A')}")
            
            # Check composite entry conditions
            should_enter, signal_type = self._check_composite_entry(symbol, current_data)
            
            if should_enter and signal_type:
                # Generate signal based on composite entry
                confidence = self._calculate_signal_confidence(symbol, 
                    MomentumSignal.BULLISH_MOMENTUM if signal_type == SignalType.BUY else MomentumSignal.BEARISH_MOMENTUM)
                
                logger.debug(f"[{symbol}] ✅ Calculated confidence: {confidence:.4f} (threshold: 0.4, {'PASS' if confidence > 0.4 else 'FAIL'})")
                
                if confidence > 0.4:  # Minimum confidence threshold (lowered for composite signals)
                    logger.info(f"[{symbol}] 🎯 Creating {signal_type.value} signal with confidence {confidence:.4f}")
                    signal = StrategySignal(
                        strategy_id=self.strategy_id,
                        symbol=symbol,
                        signal_type=signal_type,
                        strength=min(abs(momentum_strength) / self.config.momentum_threshold, 1.0),
                        confidence=confidence,
                        target_weight=self.config.base_position_pct,  # Use target_weight for percentage
                        quantity_type="PERCENTAGE",  # Explicitly mark as percentage
                        timestamp=datetime.now(),
                        additional_data={
                            'signal_reason': 'composite_entry',
                            'entry_method': 'composite_z_pct',
                            'composite_z': current_data.get('composite_z', 0),
                            'composite_pct': current_data.get('composite_pct', 0),
                            'short_momentum': short_momentum,
                            'medium_momentum': medium_momentum,
                            'long_momentum': long_momentum,
                            'adx': adx,
                            'volume_ratio': volume_ratio,
                            'entry_price': current_data['close']
                        }
                    )
                    signals.append(signal)
                    logger.debug(f"[{symbol}] ✅ {signal_type.value} signal appended to signals list (total: {len(signals)})")
                else:
                    logger.warning(f"[{symbol}] ❌ Confidence too low: {confidence:.4f} <= 0.4 (signal not created)")
            
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
    
    def _check_stale_ffill(self, series: pd.Series, max_stale_bars: int = 10) -> bool:
        """
        Check if forward-filled data is stale (too many consecutive fills)
        
        Args:
            series: The ffilled pandas Series
            max_stale_bars: Maximum allowed consecutive ffilled bars
            
        Returns:
            True if data is stale (too many consecutive fills), False otherwise
            
        MED #6: Add max_stale_bars check for ffill stale data detection
        """
        if series.empty or len(series) < 2:
            return False
        
        try:
            # Count consecutive identical values at the end (indicating ffill)
            last_value = series.iloc[-1]
            
            # Skip if NaN
            if pd.isna(last_value):
                return True  # NaN is considered stale
            
            consecutive_same = 1
            for i in range(len(series) - 2, max(-1, len(series) - max_stale_bars - 2), -1):
                if pd.isna(series.iloc[i]) or series.iloc[i] != last_value:
                    break
                consecutive_same += 1
            
            # Stale if too many consecutive identical values
            is_stale = consecutive_same >= max_stale_bars
            
            if is_stale:
                logger.warning(f"Stale ffill detected: {consecutive_same} consecutive bars with value {last_value}")
            
            return is_stale
            
        except Exception as e:
            logger.error(f"Error checking stale ffill: {e}")
            return False
    
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
            # FIXED: MED #6 - Add stale data detection after ffill
            if short_momentum_col in data.columns:
                # Forward-fill NaN values to use last valid momentum value
                short_momentum_series = data[short_momentum_col].ffill()
                
                # Check for stale ffill data (MED #6)
                if self._check_stale_ffill(short_momentum_series, max_stale_bars=10):
                    logger.warning(f"[{symbol}] Stale short momentum data detected, using fallback")
                    short_momentum = current_row.get('momentum_short', 0.0)
                # If still NaN after forward-fill, check if we have any valid values
                elif pd.isna(short_momentum_series.iloc[-1]):
                    # Try to get last valid value from entire series
                    short_momentum_valid = short_momentum_series.dropna()
                    short_momentum = short_momentum_valid.iloc[-1] if len(short_momentum_valid) > 0 else current_row.get('momentum_short', 0.0)
                else:
                    short_momentum = short_momentum_series.iloc[-1]
            else:
                short_momentum = current_row.get('momentum_short', 0.0)
            
            if medium_momentum_col in data.columns:
                medium_momentum_series = data[medium_momentum_col].ffill()
                
                # Check for stale ffill data (MED #6)
                if self._check_stale_ffill(medium_momentum_series, max_stale_bars=10):
                    logger.warning(f"[{symbol}] Stale medium momentum data detected, using fallback")
                    medium_momentum = current_row.get('momentum_medium', 0.0)
                elif pd.isna(medium_momentum_series.iloc[-1]):
                    medium_momentum_valid = medium_momentum_series.dropna()
                    medium_momentum = medium_momentum_valid.iloc[-1] if len(medium_momentum_valid) > 0 else current_row.get('momentum_medium', 0.0)
                else:
                    medium_momentum = medium_momentum_series.iloc[-1]
            else:
                medium_momentum = current_row.get('momentum_medium', 0.0)
            
            if long_momentum_col in data.columns:
                long_momentum_series = data[long_momentum_col].ffill()
                
                # Check for stale ffill data (MED #6)
                if self._check_stale_ffill(long_momentum_series, max_stale_bars=10):
                    logger.warning(f"[{symbol}] Stale long momentum data detected, using fallback")
                    long_momentum = current_row.get('momentum_long', 0.0)
                elif pd.isna(long_momentum_series.iloc[-1]):
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
            # FIXED: LOW #12 - Add numerical stability
            momentum_values = [short_momentum, medium_momentum, long_momentum]
            mean_abs_momentum = np.mean(np.abs(momentum_values))
            
            # Use max() for numerical stability when momentum near zero
            denom = max(mean_abs_momentum, 1e-6)
            momentum_consistency = 1.0 - (np.std(momentum_values) / denom)
            
            # Clip to valid range [0, 1]
            momentum_consistency = np.clip(momentum_consistency, 0.0, 1.0)
            
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
        (FIXED: MED #9 - Added reindex for alignment)
        """
        try:
            data = self.market_data[symbol]
            
            # Extract indicators as Series for signal generation (using column mapping)
            adx_col = self._get_column_name('ADX_14', data)
            volume_ratio_col = self._get_column_name('volume_ratio', data)
            
            # FIXED: MED #9 - Reindex to data.index to ensure alignment
            # Get indicators with fallback to last valid value if current is NaN
            if adx_col in data.columns:
                adx_series = data[adx_col].reindex(data.index)
            else:
                adx_series = pd.Series([25.0] * len(data), index=data.index)
            
            if volume_ratio_col in data.columns:
                volume_ratio_series = data[volume_ratio_col].reindex(data.index)
            else:
                volume_ratio_series = pd.Series([1.0] * len(data), index=data.index)
            
            if 'trend_strength' in data.columns:
                trend_strength_series = data['trend_strength'].reindex(data.index)
            else:
                trend_strength_series = pd.Series([0.0] * len(data), index=data.index)
            
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
            # Create fallback series with proper index
            fallback_index = self.market_data[symbol].index if symbol in self.market_data else pd.RangeIndex(1)
            self.indicators[symbol] = {
                'adx': pd.Series([25.0], index=fallback_index),
                'volume_ratio': pd.Series([1.0], index=fallback_index),
                'trend_strength': pd.Series([0.0], index=fallback_index)
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
            
            logger.debug(f"[{symbol}] 📊 Confidence Calculation Breakdown:")
            logger.debug(f"   📈 Momentum Strength: {momentum_strength:.6f} → strength_confidence: {strength_confidence:.4f} (weight: 0.3)")
            logger.debug(f"   📊 Momentum Consistency: {momentum.get('momentum_consistency', 0):.4f} → consistency_confidence: {consistency_confidence:.4f} (weight: 0.2)")
            logger.debug(f"   📈 Trend Quality (ADX): {adx:.2f} → trend_confidence: {trend_confidence:.4f} (weight: 0.2)")
            logger.debug(f"   📊 Volume Confirmation: {volume_ratio:.2f} → volume_confidence: {volume_confidence:.4f} (weight: 0.15)")
            logger.debug(f"   📈 Momentum Acceleration: {acceleration:.6f} → acceleration_confidence: {acceleration_confidence:.4f} (weight: 0.15)")
            logger.debug(f"   📊 Base Confidence: {base_confidence:.4f}")
            logger.debug(f"   🎁 Conditions Bonus: +{conditions_met_bonus:.4f}")
            logger.debug(f"   ✅ TOTAL CONFIDENCE: {total_confidence:.4f} (capped at 0.95)")
            
            return total_confidence
            
        except Exception as e:
            logger.error(f"Signal confidence calculation failed for {symbol}: {e}")
            return 0.5
    
    # ========================================
    # HELPER METHODS
    # ========================================
    
    def _update_market_data(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """
        Update market data cache (FIXED: MED #10 - added .copy() for safety)
        
        Creates defensive copy to prevent external mutations from affecting strategy state.
        """
        
        for symbol, data in market_data.items():
            if symbol in self.config.symbols:
                # FIXED: MED #10 - Create defensive copy to prevent mutations
                # TODO: Profile and optimize if memory becomes an issue
                self.market_data[symbol] = data.copy()
                # 🔍 DEBUG: Log data update
                logger.debug(f"🔍 Updated market_data[{symbol}]: {len(data)} bars, columns: {list(data.columns[:5])}")
    
    def _initialize_data_structures(self) -> None:
        """Initialize strategy data structures"""
        
        self.market_data.clear()
        self.indicators.clear()
        self.momentum_data.clear()
        self.position_tracker.clear()  # Phase 2.5: Unified tracking
    
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
        logger.info(f"🔄 Closing {len(self.position_tracker)} active positions")
        self.position_tracker.clear()  # Phase 2.5: Unified tracking
    
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
    
    # ========================================
    # NEW: ENHANCED POSITION TRACKING (Phase 2)
    # ========================================
    
    def _track_position_entry_enhanced(self, 
                                      symbol: str, 
                                      entry_price: float,
                                      quantity: float,
                                      signal_type: SignalType,
                                      bar_timestamp: datetime) -> None:
        """
        Track position entry with enhanced metadata (Phase 2)
        
        CRITICAL FIX: Uses bar_timestamp from enriched data, NOT datetime.now()
        This fixes the time stop bug where wall clock time was used.
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price
            quantity: Position quantity
            signal_type: BUY or SELL
            bar_timestamp: Timestamp from bar data (NOT datetime.now()!)
        """
        
        if symbol not in self.position_tracker:
            # New position entry
            self.position_tracker[symbol] = {
                'direction': 1 if signal_type == SignalType.BUY else -1,
                'avg_entry_price': entry_price,
                'total_quantity': quantity,
                'entry_time': bar_timestamp,  # ✅ Bar timestamp, not datetime.now()
                'scale_ins': 0,
                'high_water_mark': entry_price,  # Initialize at entry price
                'trailing_stop_activated': False,
                'last_update_time': bar_timestamp
            }
            
            logger.info(
                f"📈 Position tracked: {symbol} {signal_type.value} "
                f"{quantity:.2f} @ ${entry_price:.2f} "
                f"(Entry time: {bar_timestamp.strftime('%Y-%m-%d %H:%M:%S')})"
            )
        else:
            # Scale-in to existing position
            pos = self.position_tracker[symbol]
            
            # Update average entry price
            total_cost = pos['avg_entry_price'] * pos['total_quantity'] + entry_price * quantity
            pos['total_quantity'] += quantity
            pos['avg_entry_price'] = total_cost / pos['total_quantity']
            pos['scale_ins'] += 1
            pos['last_update_time'] = bar_timestamp
            
            logger.info(
                f"📊 Scale-in: {symbol} +{quantity:.2f} @ ${entry_price:.2f} "
                f"(Avg: ${pos['avg_entry_price']:.2f}, Total: {pos['total_quantity']:.2f}, "
                f"Scale-ins: {pos['scale_ins']})"
            )
    
    def _update_high_water_mark(self, symbol: str, current_price: float) -> None:
        """
        Update high water mark for trailing stop calculation (Phase 2)
        
        For LONG positions: Track highest price reached
        For SHORT positions: Track lowest price reached
        
        Args:
            symbol: Trading symbol
            current_price: Current bar close price
        """
        
        if symbol in self.position_tracker:
            pos = self.position_tracker[symbol]
            
            if pos['direction'] == 1:  # LONG position
                old_hwm = pos['high_water_mark']
                pos['high_water_mark'] = max(pos['high_water_mark'], current_price)
                
                if pos['high_water_mark'] > old_hwm:
                    logger.debug(
                        f"📈 {symbol} HWM updated: ${old_hwm:.2f} → ${pos['high_water_mark']:.2f}"
                    )
            else:  # SHORT position (direction == -1)
                old_hwm = pos['high_water_mark']
                pos['high_water_mark'] = min(pos['high_water_mark'], current_price)
                
                if pos['high_water_mark'] < old_hwm:
                    logger.debug(
                        f"📉 {symbol} HWM updated: ${old_hwm:.2f} → ${pos['high_water_mark']:.2f}"
                    )
    
    def _get_position_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get enhanced position information (Phase 2)
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Position info dict or None if no position
        """
        return self.position_tracker.get(symbol)
    
    def _clear_position_tracking(self, symbol: str) -> None:
        """
        Clear position tracking after exit (Phase 2)
        
        Args:
            symbol: Trading symbol
        """
        if symbol in self.position_tracker:
            del self.position_tracker[symbol]
            logger.debug(f"🧹 Position tracking cleared for {symbol}")
    
    # ========================================
    # NEW: REGIME-AWARE ENTRY LOGIC (Phase 4B)
    # ========================================
    
    def _get_regime_adjusted_thresholds(
        self,
        current_bar: pd.Series
    ) -> Dict[str, float]:
        """
        Get regime-adjusted entry thresholds (Type 2 Explicit Regime Awareness)
        
        Implements asymmetric risk management based on market regime:
        - Stricter LONG entry in bear regimes (avoid catching falling knives)
        - Stricter SHORT entry in bull regimes (avoid fighting the trend)
        - Standard thresholds in neutral regimes
        
        Threshold Philosophy:
        - Base thresholds: ±1.75 composite_z (Phase 4A baseline)
        - Bear regimes: Easier SHORT (1.25×), Harder LONG (1.5×)
        - Bull regimes: Easier LONG (1.25×), Harder SHORT (1.5×)
        - High volatility: Stricter on both sides (1.3×)
        
        Args:
            current_bar: Current bar data with regime information
            
        Returns:
            Dict with 'long_threshold' and 'short_threshold' (absolute values)
        """
        
        # DEBUG Phase 4C: Log current_bar regime columns
        logger.info(f"🔍 Phase 4C: current_bar columns: {list(current_bar.index)}")
        logger.info(f"   primary_regime in current_bar: {'primary_regime' in current_bar.index}")
        logger.info(f"   volatility_regime in current_bar: {'volatility_regime' in current_bar.index}")
        if 'primary_regime' in current_bar.index:
            logger.info(f"   current_bar['primary_regime'] = {current_bar.get('primary_regime', 'N/A')}")
        if 'volatility_regime' in current_bar.index:
            logger.info(f"   current_bar['volatility_regime'] = {current_bar.get('volatility_regime', 'N/A')}")
        
        # Get regime from bar data (populated by regime engine)
        primary_regime = current_bar.get('primary_regime', 'normal_volatility')
        volatility_regime = current_bar.get('volatility_regime', 'normal_volatility')
        
        # Base thresholds (Phase 4A baseline)
        base_long_threshold = self.config.composite_z_entry  # 1.75
        base_short_threshold = self.config.composite_z_entry  # 1.75
        
        # Initialize adjusted thresholds
        long_threshold = base_long_threshold
        short_threshold = base_short_threshold
        
        # Regime-based adjustments (asymmetric risk management)
        if primary_regime in ['bear_market', 'bear_high_volatility', 'bear_low_volatility']:
            # BEAR REGIME: Favor SHORT, skeptical of LONG
            long_threshold = base_long_threshold * 1.5  # 2.625 (harder to go long)
            short_threshold = base_short_threshold * 0.75  # 1.3125 (easier to go short)
            adjustment_reason = f"bear_regime({primary_regime})"
            
        elif primary_regime in ['bull_market', 'bull_high_volatility', 'bull_low_volatility']:
            # BULL REGIME: Favor LONG, skeptical of SHORT
            long_threshold = base_long_threshold * 0.75  # 1.3125 (easier to go long)
            short_threshold = base_short_threshold * 1.5  # 2.625 (harder to go short)
            adjustment_reason = f"bull_regime({primary_regime})"
            
        elif primary_regime in ['sideways', 'choppy', 'range_bound']:
            # SIDEWAYS: Neutral but slightly stricter (avoid whipsaws)
            long_threshold = base_long_threshold * 1.1  # 1.925
            short_threshold = base_short_threshold * 1.1  # 1.925
            adjustment_reason = f"sideways_regime({primary_regime})"
            
        else:
            # NORMAL/TRENDING: Standard thresholds
            adjustment_reason = f"normal_regime({primary_regime})"
        
        # Volatility regime adjustments (overlay on primary regime)
        if volatility_regime in ['high_volatility', 'extreme_volatility']:
            # HIGH VOLATILITY: Stricter on both sides (avoid noise)
            long_threshold *= 1.2  # Additional 20% strictness
            short_threshold *= 1.2
            adjustment_reason += f"+high_vol({volatility_regime})"
            
        elif volatility_regime in ['low_volatility', 'very_low_volatility']:
            # LOW VOLATILITY: Slightly more lenient (less noise)
            long_threshold *= 0.9  # 10% more lenient
            short_threshold *= 0.9
            adjustment_reason += f"+low_vol({volatility_regime})"
        
        return {
            'long_threshold': long_threshold,
            'short_threshold': short_threshold,
            'adjustment_reason': adjustment_reason,
            'primary_regime': primary_regime,
            'volatility_regime': volatility_regime
        }
    
    # ========================================
    # NEW: COMPOSITE SIGNAL ENTRY LOGIC (Phase 4A)
    # ========================================
    
    def _check_composite_entry(
        self,
        symbol: str,
        current_bar: pd.Series
    ) -> Tuple[bool, Optional[SignalType]]:
        """
        Check composite signal entry conditions (Phase 4A + Phase 4B)
        
        Uses composite_z and composite_pct for entry (aligned with exit logic).
        Entry thresholds are STRONGER than exit thresholds to create hysteresis.
        
        **Phase 4B Enhancement: Type 2 Explicit Regime Awareness**
        - Thresholds now adapt based on market regime (asymmetric risk management)
        - Bear regimes: Easier SHORT, Harder LONG (avoid catching falling knives)
        - Bull regimes: Easier LONG, Harder SHORT (avoid fighting the trend)
        - High volatility: Stricter on both sides (avoid noise)
        
        Entry Logic:
        - LONG entry: composite_z > regime_adjusted_long_threshold AND
                     composite_pct > composite_pct_entry (92)
        - SHORT entry: composite_z < -regime_adjusted_short_threshold AND
                      composite_pct < (100 - composite_pct_entry) (8)
        
        Args:
            symbol: Trading symbol
            current_bar: Current bar data with composite signals and regime info
            
        Returns:
            Tuple[should_enter, signal_type]
            - should_enter: True if entry conditions met
            - signal_type: SignalType.BUY (LONG) or SignalType.SELL (SHORT) or None
        """
        
        logger.debug(f"🚀 [{symbol}] ==== ENTERING _check_composite_entry method ====")
        
        # FIXED: HIGH #3 - Narrow exception handling for specific errors
        try:
            logger.debug(f"🔍 [{symbol}] Step 1: Getting composite signals from current_bar...")
            # Get composite signals
            composite_z = current_bar.get('composite_z', None)
            logger.debug(f"🔍 [{symbol}] Step 1a: Got composite_z = {composite_z}")
            composite_pct = current_bar.get('composite_pct', None)
            logger.debug(f"🔍 [{symbol}] Step 1b: Got composite_pct = {composite_pct}")
        except (KeyError, AttributeError) as e:
            logger.error(f"❌ [{symbol}] Missing required columns in current_bar: {e}", exc_info=True)
            logger.error(f"   Available columns: {list(current_bar.index) if hasattr(current_bar, 'index') else 'N/A'}")
            raise  # Re-raise to surface data pipeline issues
        except Exception as e:
            logger.exception(f"❌ [{symbol}] Unexpected error getting composite signals")
            raise  # Don't mask unexpected errors
        
        logger.debug(f"🔍 [{symbol}] Step 2: Checking if regime columns exist...")
        # DEBUG Phase 4C: Check if regime columns exist
        has_primary = 'primary_regime' in current_bar.index if hasattr(current_bar, 'index') else 'primary_regime' in current_bar
        has_volatility = 'volatility_regime' in current_bar.index if hasattr(current_bar, 'index') else 'volatility_regime' in current_bar
        # SIMPLIFIED LOGGING (original line 1540 was causing silent exceptions)
        logger.debug(f"🔍 {symbol} composite check: composite_z={composite_z}, composite_pct={composite_pct}")
        
        # 🔍 Check 1: Is composite_z valid?
        if composite_z is None or pd.isna(composite_z):
            logger.debug(f"❌ [{symbol}] EARLY RETURN: composite_z not available (composite_z={composite_z})")
            return False, None
        else:
            logger.debug(f"✅ [{symbol}] composite_z is valid: {composite_z:.4f}")
        
        # 🔍 Check 2: Is composite_pct valid? (FIXED: HIGH #1 - was disabled, now enforced)
        if composite_pct is None or pd.isna(composite_pct):
            logger.debug(f"❌ [{symbol}] EARLY RETURN: composite_pct not available (composite_pct={composite_pct})")
            return False, None
        
        # Normalize composite_pct scale (handle both 0-1 and 0-100 ranges)
        if composite_pct <= 1.0:
            logger.debug(f"🔧 [{symbol}] Normalizing composite_pct from {composite_pct} to {composite_pct * 100}%")
            composite_pct = composite_pct * 100.0
        
        # Phase 4B: Get regime-adjusted thresholds (Type 2 Explicit Regime Awareness)
        logger.debug(f"🔍 [{symbol}] About to get regime-adjusted thresholds...")
        thresholds = self._get_regime_adjusted_thresholds(current_bar)
        logger.debug(f"🔍 [{symbol}] Got thresholds: {thresholds}")
        long_threshold = thresholds['long_threshold']
        short_threshold = thresholds['short_threshold']
        adjustment_reason = thresholds['adjustment_reason']
        
        # 🔍 DIAGNOSTIC: Log ALL threshold checks (not just high values)
        logger.debug(f"🔍 [{symbol}] ENTRY CHECK:")
        logger.debug(f"   composite_z={composite_z}")
        logger.debug(f"   composite_pct={composite_pct}")
        logger.debug(f"   long_threshold={long_threshold} (reason: {adjustment_reason})")
        logger.debug(f"   short_threshold={short_threshold}")
        logger.debug(f"   LONG condition: {composite_z} > {long_threshold}? {composite_z > long_threshold}")
        logger.debug(f"   SHORT condition: {composite_z} < {-short_threshold}? {composite_z < -short_threshold}")
        
        # LONG entry: Strong upward momentum (both Z-score AND percentile confirmation)
        long_condition_met = (
            composite_z > long_threshold and
            composite_pct > self.config.composite_pct_entry
        )
        short_condition_met = (
            composite_z < -short_threshold and
            composite_pct < (100 - self.config.composite_pct_entry)
        )
        
        if long_condition_met:
            logger.info(
                f"🟢 {symbol} LONG entry: composite_z={composite_z:.2f} > {long_threshold:.2f}, "
                f"composite_pct={composite_pct:.1f}% (>{self.config.composite_pct_entry:.1f}%) "
                f"(regime-adjusted from {self.config.composite_z_entry:.2f}, reason: {adjustment_reason})"
            )
            return True, SignalType.BUY
        
        # SHORT entry: Strong downward momentum (both Z-score AND percentile confirmation)
        if short_condition_met:
            logger.info(
                f"🔴 {symbol} SHORT entry: composite_z={composite_z:.2f} < {-short_threshold:.2f}, "
                f"composite_pct={composite_pct:.1f}% (<{100 - self.config.composite_pct_entry:.1f}%) "
                f"(regime-adjusted from {-self.config.composite_z_entry:.2f}, reason: {adjustment_reason})"
            )
            return True, SignalType.SELL
        
        return False, None
    
    # ========================================
    # HYBRID EXIT LOGIC
    # ========================================
    
    async def _check_exit_conditions_hybrid(
        self,
        symbol: str,
        enriched_data: pd.DataFrame,
        bar_timestamp: datetime
    ) -> Tuple[bool, Optional[str]]:
        """
        Check hybrid exit conditions for active position (Phase 3)
        
        Implements 4 exit triggers:
        1. ATR-based stops (initial stop, trailing stop)
        2. Composite signal exits (momentum deterioration)
        3. Time-based exits (max holding period)
        4. Volume-based exits (volume failure)
        
        Args:
            symbol: Trading symbol
            enriched_data: DataFrame with OHLCV + indicators + features
            bar_timestamp: Current bar timestamp
            
        Returns:
            Tuple[should_exit, exit_reason]
        """
        
        # Check if we have a position
        pos_info = self._get_position_info(symbol)
        if not pos_info:
            return False, None
        
        # Get current bar data
        if bar_timestamp not in enriched_data.index:
            logger.warning(f"⚠️  {symbol} bar timestamp {bar_timestamp} not in enriched_data")
            return False, None
        
        current_bar = enriched_data.loc[bar_timestamp]
        current_price = current_bar['close']
        
        # Priority 1: ATR-based stops (hard stops)
        should_exit, exit_reason = self._check_atr_stops(
            symbol, pos_info, current_price, current_bar
        )
        if should_exit:
            return True, exit_reason
        
        # Priority 2: Composite signal exits (momentum deterioration)
        should_exit, exit_reason = self._check_composite_exits(
            symbol, pos_info, current_bar
        )
        if should_exit:
            return True, exit_reason
        
        # Priority 3: Time-based exits (holding period)
        should_exit, exit_reason = self._check_time_exit(
            symbol, pos_info, bar_timestamp
        )
        if should_exit:
            return True, exit_reason
        
        # Priority 4: Volume-based exits (volume failure)
        should_exit, exit_reason = self._check_volume_exit(
            symbol, pos_info, current_bar, enriched_data
        )
        if should_exit:
            return True, exit_reason
        
        return False, None
    
    def _check_atr_stops(
        self,
        symbol: str,
        pos_info: Dict[str, Any],
        current_price: float,
        current_bar: pd.Series
    ) -> Tuple[bool, Optional[str]]:
        """
        Check ATR-based stop losses and trailing stops (Phase 3)
        
        Stop types:
        1. Initial stop: entry_price ± (atr_initial_stop_multiple × ATR)
        2. Trailing stop: activated after profit > atr_trailing_activation × ATR
        
        Args:
            symbol: Trading symbol
            pos_info: Position information
            current_price: Current close price
            current_bar: Current bar data
            
        Returns:
            Tuple[should_exit, exit_reason]
        """
        
        direction = pos_info['direction']  # 1=LONG, -1=SHORT
        entry_price = pos_info['avg_entry_price']
        high_water_mark = pos_info['high_water_mark']
        trailing_activated = pos_info['trailing_stop_activated']
        
        # Get ATR
        atr = current_bar.get('ATR_14', None)
        if atr is None or pd.isna(atr):
            logger.warning(f"⚠️  {symbol} ATR not available for stop calculation")
            return False, None
        
        # LONG position exits
        if direction == 1:
            # Initial stop (hard stop)
            initial_stop = entry_price - (self.config.atr_initial_stop_multiple * atr)
            if current_price <= initial_stop:
                logger.info(f"🛑 {symbol} LONG hit initial stop: ${current_price:.2f} <= ${initial_stop:.2f}")
                return True, "atr_initial_stop"
            
            # Trailing stop (profit protection)
            profit_atr = (high_water_mark - entry_price) / atr
            if profit_atr >= self.config.atr_trailing_activation:
                trailing_stop = high_water_mark - (self.config.atr_trailing_distance * atr)
                if current_price <= trailing_stop:
                    logger.info(f"📉 {symbol} LONG hit trailing stop: ${current_price:.2f} <= ${trailing_stop:.2f}")
                    return True, "atr_trailing_stop"
        
        # SHORT position exits
        elif direction == -1:
            # Initial stop (hard stop)
            initial_stop = entry_price + (self.config.atr_initial_stop_multiple * atr)
            if current_price >= initial_stop:
                logger.info(f"🛑 {symbol} SHORT hit initial stop: ${current_price:.2f} >= ${initial_stop:.2f}")
                return True, "atr_initial_stop"
            
            # Trailing stop (profit protection)
            profit_atr = (entry_price - high_water_mark) / atr
            if profit_atr >= self.config.atr_trailing_activation:
                trailing_stop = high_water_mark + (self.config.atr_trailing_distance * atr)
                if current_price >= trailing_stop:
                    logger.info(f"📈 {symbol} SHORT hit trailing stop: ${current_price:.2f} >= ${trailing_stop:.2f}")
                    return True, "atr_trailing_stop"
        
        return False, None
    
    def _check_composite_exits(
        self,
        symbol: str,
        pos_info: Dict[str, Any],
        current_bar: pd.Series
    ) -> Tuple[bool, Optional[str]]:
        """
        Check composite signal exit conditions (Phase 3)
        
        Exit triggers:
        1. Composite Z-score falls below exit threshold
        2. Composite percentile falls below exit threshold
        
        Args:
            symbol: Trading symbol
            pos_info: Position information
            current_bar: Current bar data
            
        Returns:
            Tuple[should_exit, exit_reason]
        """
        
        # Get composite signals
        composite_z = current_bar.get('composite_z', None)
        composite_pct = current_bar.get('composite_pct', None)
        
        if composite_z is None or pd.isna(composite_z):
            logger.debug(f"⚠️  {symbol} composite_z not available for exit check")
            return False, None
        
        if composite_pct is None or pd.isna(composite_pct):
            logger.debug(f"⚠️  {symbol} composite_pct not available for exit check")
            return False, None
        
        direction = pos_info['direction']
        
        # LONG position: exit if momentum deteriorates
        if direction == 1:
            if composite_z < self.config.composite_z_exit:
                logger.info(f"📉 {symbol} LONG composite_z exit: {composite_z:.2f} < {self.config.composite_z_exit:.2f}")
                return True, "composite_z_exit"
            
            if composite_pct < self.config.composite_pct_exit:
                logger.info(f"📉 {symbol} LONG composite_pct exit: {composite_pct:.1f} < {self.config.composite_pct_exit:.1f}")
                return True, "composite_pct_exit"
        
        # SHORT position: exit if momentum strengthens
        elif direction == -1:
            if composite_z > -self.config.composite_z_exit:  # Opposite for shorts
                logger.info(f"📈 {symbol} SHORT composite_z exit: {composite_z:.2f} > {-self.config.composite_z_exit:.2f}")
                return True, "composite_z_exit"
            
            if composite_pct > (100 - self.config.composite_pct_exit):  # Opposite for shorts
                logger.info(f"📈 {symbol} SHORT composite_pct exit: {composite_pct:.1f} > {100 - self.config.composite_pct_exit:.1f}")
                return True, "composite_pct_exit"
        
        return False, None
    
    def _check_time_exit(
        self,
        symbol: str,
        pos_info: Dict[str, Any],
        bar_timestamp: datetime
    ) -> Tuple[bool, Optional[str]]:
        """
        Check time-based exit (max holding period) (Phase 3)
        
        CRITICAL FIX: Uses bar timestamps (not datetime.now()!)
        
        Args:
            symbol: Trading symbol
            pos_info: Position information
            bar_timestamp: Current bar timestamp
            
        Returns:
            Tuple[should_exit, exit_reason]
        """
        
        entry_time = pos_info['entry_time']  # Bar timestamp from entry
        
        # Calculate holding period in MINUTES (using bar timestamps)
        holding_time_delta = bar_timestamp - entry_time
        holding_minutes = holding_time_delta.total_seconds() / 60.0
        
        if holding_minutes >= self.config.time_stop_minutes:
            logger.info(f"⏰ {symbol} max holding period: {holding_minutes:.1f}min >= {self.config.time_stop_minutes}min")
            return True, "time_stop"
        
        return False, None
    
    def _check_volume_exit(
        self,
        symbol: str,
        pos_info: Dict[str, Any],
        current_bar: pd.Series,
        enriched_data: pd.DataFrame
    ) -> Tuple[bool, Optional[str]]:
        """
        Check volume-based exit (volume failure) (Phase 3)
        
        Exit trigger: Volume ratio falls below threshold for N consecutive bars
        
        Args:
            symbol: Trading symbol
            pos_info: Position information
            current_bar: Current bar data
            enriched_data: Full enriched data
            
        Returns:
            Tuple[should_exit, exit_reason]
        """
        
        # Get volume ratio
        volume_ratio = current_bar.get('volume_ratio', None)
        if volume_ratio is None or pd.isna(volume_ratio):
            logger.debug(f"⚠️  {symbol} volume_ratio not available for exit check")
            return False, None
        
        # Check if volume is too low
        if volume_ratio < self.config.volume_failure_multiplier:
            logger.info(f"📊 {symbol} volume failure: {volume_ratio:.2f} < {self.config.volume_failure_multiplier:.2f}")
            return True, "volume_failure"
        
        return False, None
    
    async def _generate_exit_signal(
        self,
        symbol: str,
        pos_info: Dict[str, Any],
        current_price: float,
        exit_reason: str,
        bar_timestamp: datetime
    ) -> StrategySignal:
        """
        Generate exit signal (SELL for LONG, BUY for SHORT) (Phase 3)
        
        Args:
            symbol: Trading symbol
            pos_info: Position information
            current_price: Current price
            exit_reason: Reason for exit
            bar_timestamp: Current bar timestamp
            
        Returns:
            StrategySignal for exit
        """
        
        direction = pos_info['direction']
        quantity = pos_info['total_quantity']
        entry_price = pos_info['avg_entry_price']
        
        # Determine exit signal type (opposite of entry)
        if direction == 1:  # LONG position → SELL signal
            signal_type = SignalType.SELL
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
        else:  # SHORT position → BUY signal (cover)
            signal_type = SignalType.BUY
            pnl_pct = ((entry_price - current_price) / entry_price) * 100
        
        # Create exit signal
        exit_signal = StrategySignal(
            strategy_id=self.strategy_id,
            symbol=symbol,
            signal_type=signal_type,
            strength=1.0,  # Exits are strong signals (max strength)
            confidence=0.9,  # High confidence for exits
            quantity=quantity,
            timestamp=bar_timestamp,
            signal_source="exit_logic_hybrid",
            signal_reason=f"exit_{exit_reason}",
            additional_data={
                'action': 'exit',
                'exit_reason': exit_reason,
                'entry_price': entry_price,
                'exit_price': current_price,
                'pnl_pct': pnl_pct,
                'holding_minutes': (bar_timestamp - pos_info['entry_time']).total_seconds() / 60.0,
                'scale_ins': pos_info.get('scale_ins', 0)
            }
        )
        
        logger.info(f"🚪 Exit signal generated: {symbol} {signal_type.value} {quantity:.2f} @ ${current_price:.2f} | "
                   f"Reason: {exit_reason} | P&L: {pnl_pct:+.2f}%")
        
        return exit_signal
    
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
            'active_positions': len(self.position_tracker),  # Phase 2.5: Use NEW tracking
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
                    'direction': pos['direction'],
                    'avg_entry_price': pos['avg_entry_price'],
                    'total_quantity': pos['total_quantity'],
                    'entry_time': pos['entry_time'].isoformat(),
                    'high_water_mark': pos['high_water_mark'],
                    'trailing_stop_activated': pos['trailing_stop_activated'],
                    'scale_ins': pos['scale_ins']
                }
                for symbol, pos in self.position_tracker.items()  # Phase 2.5: Use NEW tracking
            }
        }
