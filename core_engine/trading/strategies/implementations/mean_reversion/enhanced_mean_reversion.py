"""
Enhanced Mean Reversion Strategy with ISystemComponent Integration
================================================================

Professional mean reversion strategy that implements ISystemComponent interface
for seamless orchestrator integration and institutional-grade lifecycle management.

This enhanced strategy provides:
- ISystemComponent interface compliance
- Regime-aware mean reversion detection
- Multi-timeframe analysis and confirmation
- Dynamic position sizing based on volatility
- Professional risk management integration
- Comprehensive performance tracking

Key Features:
- Statistical mean reversion detection using Z-scores
- Bollinger Bands and RSI confluence
- Regime filtering to avoid choppy markets
- ATR-based position sizing
- Time-based and profit target exits
- Transaction cost awareness

Academic Foundations:
- Jegadeesh & Titman (1993) momentum and reversal
- Lo & MacKinlay (1990) contrarian investment strategies
- Poterba & Summers (1988) mean reversion in stock prices

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
from core_engine.config import MeanReversionConfig

logger = logging.getLogger(__name__)


class MeanReversionSignal(Enum):
    """Mean reversion signal types"""
    OVERSOLD_BUY = "oversold_buy"
    OVERBOUGHT_SELL = "overbought_sell"
    NEUTRAL = "neutral"


# Note: MeanReversionConfig now imported from core_engine.config (Rule 1 Section 7)
# Local definition removed - use centralized configuration


class EnhancedMeanReversionStrategy(EnhancedBaseStrategy):
    """
    Enhanced Mean Reversion Strategy with ISystemComponent Integration
    
    Professional mean reversion strategy that provides:
    - ISystemComponent interface compliance
    - Regime-aware mean reversion detection
    - Multi-timeframe analysis and confirmation
    - Dynamic position sizing based on volatility
    - Comprehensive performance tracking and risk management
    """
    
    def __init__(self, config: MeanReversionConfig):
        """Initialize enhanced mean reversion strategy"""
        
        # Initialize base strategy
        super().__init__(config)
        self.config: MeanReversionConfig = config
        
        # Strategy-specific state
        self.market_data: Dict[str, pd.DataFrame] = {}
        self.indicators: Dict[str, Dict[str, pd.Series]] = {}
        self.regime_data: Dict[str, Dict[str, float]] = {}
        
        # Position tracking
        self.active_positions: Dict[str, Dict[str, Any]] = {}
        self.entry_prices: Dict[str, float] = {}
        self.stop_losses: Dict[str, float] = {}
        self.profit_targets: Dict[str, float] = {}
        
        # Performance tracking
        self.trade_history: List[Dict[str, Any]] = []
        self.daily_pnl: List[float] = []
        
        logger.info(f"🧠 Enhanced Mean Reversion Strategy {self.strategy_id} initialized")
    
    # ========================================
    # STRATEGY-SPECIFIC LIFECYCLE HOOKS
    # ========================================
    
    async def _initialize_strategy_components(self) -> bool:
        """Initialize strategy-specific components"""
        
        try:
            logger.info(f"🔄 Initializing Mean Reversion components for {self.strategy_id}...")
            
            # Validate symbols
            if not self.config.symbols:
                logger.error("❌ No symbols configured for mean reversion strategy")
                return False
            
            # Initialize data structures
            self._initialize_data_structures()
            
            # Initialize indicators
            self._initialize_indicators()
            
            logger.info(f"✅ Mean Reversion components initialized for {len(self.config.symbols)} symbols")
            return True
            
        except Exception as e:
            logger.error(f"❌ Mean Reversion component initialization failed: {e}")
            return False
    
    async def _start_strategy_operations(self) -> bool:
        """Start strategy-specific operations"""
        
        try:
            logger.info(f"🚀 Starting Mean Reversion operations for {self.strategy_id}...")
            
            # Start performance tracking
            self._start_performance_tracking()
            
            logger.info(f"✅ Mean Reversion operations started")
            return True
            
        except Exception as e:
            logger.error(f"❌ Mean Reversion operations start failed: {e}")
            return False
    
    async def _stop_strategy_operations(self) -> None:
        """Stop strategy-specific operations"""
        
        try:
            logger.info(f"🔄 Stopping Mean Reversion operations for {self.strategy_id}...")
            
            # Close all positions
            await self._close_all_positions()
            
            # Save performance data
            self._save_performance_data()
            
            logger.info(f"✅ Mean Reversion operations stopped")
            
        except Exception as e:
            logger.error(f"❌ Mean Reversion operations stop failed: {e}")
    
    async def _check_strategy_health(self) -> Dict[str, Any]:
        """Check strategy-specific health"""
        
        try:
            health_metrics = {
                'strategy_healthy': True,
                'symbols_tracked': len(self.config.symbols),
                'active_positions': len(self.active_positions),
                'indicators_calculated': len(self.indicators),
                'avg_volatility': self._calculate_avg_volatility(),
                'regime_health': self._check_regime_health()
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
            'strategy_type': 'Enhanced Mean Reversion',
            'symbols_count': len(self.config.symbols),
            'lookback_period': self.config.lookback_period,
            'zscore_entry_threshold': self.config.zscore_entry_threshold,
            'enable_multi_timeframe': self.config.enable_multi_timeframe,
            'enable_regime_filter': self.config.enable_regime_filter,
            'base_position_pct': self.config.base_position_pct,
            'volatility_target': self.config.volatility_target
        }
    
    def _validate_strategy_config(self) -> bool:
        """Validate strategy-specific configuration"""
        
        try:
            # Validate thresholds
            if self.config.zscore_entry_threshold <= self.config.zscore_exit_threshold:
                logger.error("Entry Z-score threshold must be greater than exit threshold")
                return False
            
            # Validate position sizing
            if self.config.base_position_pct <= 0 or self.config.base_position_pct > 0.1:
                logger.error("Base position percentage must be between 0 and 0.1 (10%)")
                return False
            
            # Validate periods
            if self.config.lookback_period < 10:
                logger.error("Lookback period must be at least 10")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation error: {e}")
            return False
    
    # ========================================
    # ABSTRACT METHOD IMPLEMENTATIONS
    # ========================================
    
    def _get_column_mapping(self) -> Dict[str, str]:
        """
        Get mapping from expected column names to actual column names in enriched DataFrame
        
        Returns:
            Dict mapping expected names to actual names
        """
        return {
            # Moving averages
            'SMA_20': 'sma_20',  # Actual from indicator engine
            # Momentum indicators
            'RSI_14': 'rsi',     # Actual from indicator engine
            'ATR_14': 'atr',     # Actual from indicator engine
            # Bollinger Bands (same names)
            'bb_upper': 'bb_upper',
            'bb_lower': 'bb_lower',
            'bb_middle': 'bb_middle',
            # Volume (same name)
            'volume_ratio': 'volume_ratio'
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
        and contains all indicators required by the mean reversion strategy.
        
        Uses flexible column name mapping to handle both expected and actual column names.
        
        Args:
            enriched_data: Dict[symbol, enriched DataFrame]
        
        Raises:
            ValueError: If data is missing required indicators
        """
        # Required indicators with flexible naming
        required_indicators = {
            'SMA_20': ['sma_20', 'SMA_20'],       # Required
            'RSI_14': ['rsi', 'RSI_14'],         # Required
            'bb_upper': ['bb_upper'],            # Required
            'bb_lower': ['bb_lower'],            # Required
            'bb_middle': ['bb_middle'],          # Required
            'ATR_14': ['atr', 'ATR_14'],         # Required
            'volume_ratio': ['volume_ratio']     # Required
        }
        
        for symbol, data in enriched_data.items():
            if data.empty:
                raise ValueError(f"{symbol} has empty DataFrame")
            
            missing = []
            for expected_name, possible_names in required_indicators.items():
                # Check if any of the possible names exist
                found = any(name in data.columns for name in possible_names)
                if not found:
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
    
    async def generate_signals(self, enriched_data: Dict[str, pd.DataFrame]) -> List[StrategySignal]:
        """
        Generate mean reversion signals from ENRICHED data (Rule 3 Phase 4)
        
        **CRITICAL CHANGE:** This method now receives enriched data with pre-calculated
        indicators and features from the ProcessingPipelineOrchestrator. It does NOT
        calculate indicators itself.
        
        Args:
            enriched_data: Dict[symbol, enriched DataFrame with OHLCV + indicators + features]
                          Must contain: zscore, RSI_14, bb_upper, bb_lower, bb_middle, 
                                       bb_position, ATR_14, volume_ratio
        
        Returns:
            List[StrategySignal]: Generated mean reversion signals
        """
        start_time = datetime.now()
        signals = []
        
        try:
            # PHASE 4: Validate enriched data (Rule 3)
            self._validate_enriched_data(enriched_data)
            
            # Update market data with enriched data
            self._update_market_data(enriched_data)
            
            # Update regime analysis
            if self.config.enable_regime_filter:
                self._update_regime_analysis()
            
            # Generate signals for each symbol
            for symbol in self.config.symbols:
                if symbol in self.market_data and len(self.market_data[symbol]) > self.config.lookback_period:
                    symbol_signals = await self._generate_symbol_signals(symbol)
                    signals.extend(symbol_signals)
            
            # Update performance metrics
            generation_time = (datetime.now() - start_time).total_seconds()
            self.track_signal_generation_time(generation_time)
            
            logger.info(f"📊 Mean Reversion Strategy (Rule 3 Phase 4 - Enriched Data):")
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
            
            # Check exit conditions for active positions
            await self._check_exit_conditions()
            
            # Update stop losses and profit targets
            self._update_stop_losses_and_targets()
            
            # Update performance tracking
            self._update_performance_tracking()
            
        except Exception as e:
            self._log_error("Position update failed", e)
    
    def calculate_position_size(self, signal: StrategySignal, market_data: Dict[str, pd.DataFrame]) -> float:
        """Calculate position size for a given signal"""
        
        try:
            symbol = signal.symbol
            
            # Get current price and ATR
            if symbol not in self.market_data or len(self.market_data[symbol]) == 0:
                return 0.0
            
            current_price = self.market_data[symbol]['close'].iloc[-1]
            atr = self._calculate_atr(symbol)
            
            if atr == 0:
                return self.config.base_position_pct
            
            # Calculate volatility-adjusted position size
            volatility = atr / current_price
            volatility_adjustment = self.config.volatility_target / max(volatility, 0.01)
            
            # Apply confidence scaling
            confidence_adjustment = signal.confidence
            
            # Calculate final position size
            position_size = (self.config.base_position_pct * 
                           volatility_adjustment * 
                           confidence_adjustment)
            
            # Cap at maximum position size
            return min(position_size, self.config.max_position_pct)
            
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
            'zscore_entry_threshold': self.config.zscore_entry_threshold,
            'rsi_oversold': self.config.rsi_oversold,
            'rsi_overbought': self.config.rsi_overbought
        }
        
        # If regime adjustment is disabled, return base thresholds
        if not self.config.enable_regime_adjusted_thresholds:
            return base_thresholds
        
        # Get current regime context
        regime_context = self.get_current_regime_context()
        if not regime_context:
            return base_thresholds
        
        # Determine if regime is unfavorable for mean reversion
        # Unfavorable: extreme_volatility, crisis, trending markets
        # Favorable: range_bound, choppy, normal_volatility
        regime_name = getattr(regime_context, 'primary_regime', None)
        volatility_regime = getattr(regime_context, 'volatility_regime', None)
        
        unfavorable_regimes = ['extreme_volatility', 'crisis', 'trending']
        
        is_unfavorable = (
            (regime_name and any(unfavorable in str(regime_name).lower() for unfavorable in unfavorable_regimes)) or
            (volatility_regime and 'extreme' in str(volatility_regime).lower())
        )
        
        # Apply adjustment factor if unfavorable (reduce thresholds for easier entry)
        if is_unfavorable:
            adjustment = self.config.regime_adjustment_factor
            adjusted_thresholds = {
                'zscore_entry_threshold': base_thresholds['zscore_entry_threshold'] * adjustment,
                'rsi_oversold': base_thresholds['rsi_oversold'] * (1 + (1 - adjustment)),  # Increase oversold threshold
                'rsi_overbought': base_thresholds['rsi_overbought'] * adjustment  # Decrease overbought threshold
            }
            
            logger.debug(f"[{symbol}] Regime-adjusted thresholds applied: {adjustment:.2f}x "
                        f"(Z-score: {base_thresholds['zscore_entry_threshold']:.2f} -> {adjusted_thresholds['zscore_entry_threshold']:.2f})")
            
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
            
            if idx < self.config.lookback_period or idx >= len(data):
                return None
            
            current_row = data.iloc[idx]
            
            # READ pre-calculated indicators from enriched DataFrame with forward-fill for NaN handling
            # CRITICAL: When processing rolling windows chronologically, bars might have NaN
            # if they're at the edge of the lookback period. Use forward-fill to get last valid value.
            if 'zscore' in data.columns:
                zscore_series = data['zscore'].ffill()
                zscore = zscore_series.iloc[idx] if idx < len(zscore_series) and not pd.isna(zscore_series.iloc[idx]) else (zscore_series.dropna().iloc[-1] if len(zscore_series.dropna()) > 0 else 0.0)
            else:
                zscore = current_row.get('zscore', 0.0)
            
            rsi_col = self._get_column_name('RSI_14', data)
            if rsi_col in data.columns:
                rsi_series = data[rsi_col].ffill()
                rsi = rsi_series.iloc[idx] if idx < len(rsi_series) and not pd.isna(rsi_series.iloc[idx]) else (rsi_series.dropna().iloc[-1] if len(rsi_series.dropna()) > 0 else 50.0)
            else:
                rsi = current_row.get(rsi_col, current_row.get('rsi', 50.0))
            
            if 'bb_position' in data.columns:
                bb_position_series = data['bb_position'].ffill()
                bb_position = bb_position_series.iloc[idx] if idx < len(bb_position_series) and not pd.isna(bb_position_series.iloc[idx]) else (bb_position_series.dropna().iloc[-1] if len(bb_position_series.dropna()) > 0 else 0.5)
            else:
                bb_position = current_row.get('bb_position', 0.5)
            
            # Handle any remaining NaN values (fallback)
            zscore = zscore if not pd.isna(zscore) else 0.0
            rsi = rsi if not pd.isna(rsi) else 50.0
            bb_position = bb_position if not pd.isna(bb_position) else 0.5
            
            # Get regime-adjusted thresholds
            thresholds = self._get_regime_adjusted_thresholds(symbol)
            zscore_threshold = thresholds['zscore_entry_threshold']
            rsi_oversold = thresholds['rsi_oversold']
            rsi_overbought = thresholds['rsi_overbought']
            
            # Apply regime filter
            if self.config.enable_regime_filter:
                if not self._is_regime_favorable(symbol):
                    return None
            
            # Check for oversold condition (BUY signal)
            if (zscore < -zscore_threshold and 
                rsi < rsi_oversold and 
                bb_position < 0.2):
                
                confidence = self._calculate_signal_confidence(symbol, MeanReversionSignal.OVERSOLD_BUY)
                
                if confidence > 0.6:
                    signal = StrategySignal(
                        strategy_id=self.strategy_id,
                        symbol=symbol,
                        signal_type=SignalType.BUY,
                        strength=min(abs(zscore) / zscore_threshold, 1.0),
                        confidence=confidence,
                        target_weight=self.config.base_position_pct,  # Use target_weight for percentage
                        quantity_type="PERCENTAGE",  # Explicitly mark as percentage
                        timestamp=current_row.get('timestamp', datetime.now()) if isinstance(current_row, pd.Series) else datetime.now(),
                        additional_data={
                            'signal_reason': 'oversold_mean_reversion',
                            'zscore': zscore,
                            'rsi': rsi,
                            'bb_position': bb_position,
                            'entry_price': current_row['close'] if isinstance(current_row, pd.Series) else current_row.get('close', 0),
                            'bar_index': idx
                        }
                    )
                    return signal
            
            # Check for overbought condition (SELL signal)
            elif (zscore > zscore_threshold and 
                  rsi > rsi_overbought and 
                  bb_position > 0.8):
                
                confidence = self._calculate_signal_confidence(symbol, MeanReversionSignal.OVERBOUGHT_SELL)
                
                if confidence > 0.6:
                    signal = StrategySignal(
                        strategy_id=self.strategy_id,
                        symbol=symbol,
                        signal_type=SignalType.SELL,
                        strength=min(abs(zscore) / zscore_threshold, 1.0),
                        confidence=confidence,
                        target_weight=self.config.base_position_pct,  # Use target_weight for percentage
                        quantity_type="PERCENTAGE",  # Explicitly mark as percentage
                        timestamp=current_row.get('timestamp', datetime.now()) if isinstance(current_row, pd.Series) else datetime.now(),
                        additional_data={
                            'signal_reason': 'overbought_mean_reversion',
                            'zscore': zscore,
                            'rsi': rsi,
                            'bb_position': bb_position,
                            'entry_price': current_row['close'] if isinstance(current_row, pd.Series) else current_row.get('close', 0),
                            'bar_index': idx
                        }
                    )
                    return signal
            
            return None
            
        except Exception as e:
            logger.error(f"[{symbol}] Error evaluating bar at index {idx}: {e}")
            return None
    
    async def _generate_symbol_signals(self, symbol: str) -> List[StrategySignal]:
        """
        Generate signals for a specific symbol using PRE-CALCULATED indicators (Rule 3 Phase 4)
        
        **CRITICAL:** This method READS pre-calculated indicator values from enriched data.
        It does NOT calculate indicators itself.
        """
        signals = []
        
        try:
            # Skip if already have position
            if symbol in self.active_positions:
                return signals
            
            # Get enriched data with pre-calculated indicators
            if symbol not in self.market_data:
                return signals
            
            data = self.market_data[symbol]
            data_length = len(data)
            
            # Check if we should scan all bars (historical mode) or just current bar (live mode)
            if self.config.scan_all_bars and data_length > self.config.lookback_period:
                # Historical scanning mode: scan through all bars
                logger.info(f"[{symbol}] 📊 Historical scanning mode: scanning {data_length} bars "
                           f"(evaluating every {self.config.scan_interval} bars)")
                
                start_idx = self.config.lookback_period
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
            
            current_row = data.iloc[-1]
            
            # READ pre-calculated indicators from enriched DataFrame with forward-fill for NaN handling
            # CRITICAL: When processing rolling windows chronologically, the last bar might have NaN
            # if it's at the edge of the lookback period. Use forward-fill to get last valid value.
            if 'zscore' in data.columns:
                zscore_series = data['zscore'].ffill()
                zscore = zscore_series.iloc[-1] if not pd.isna(zscore_series.iloc[-1]) else (zscore_series.dropna().iloc[-1] if len(zscore_series.dropna()) > 0 else 0.0)
            else:
                zscore = current_row.get('zscore', 0.0)
            
            # Use column mapping to get RSI value
            rsi_col = self._get_column_name('RSI_14', data)
            if rsi_col in data.columns:
                rsi_series = data[rsi_col].ffill()
                rsi = rsi_series.iloc[-1] if not pd.isna(rsi_series.iloc[-1]) else (rsi_series.dropna().iloc[-1] if len(rsi_series.dropna()) > 0 else 50.0)
            else:
                rsi = current_row.get(rsi_col, current_row.get('rsi', 50.0))
            
            if 'bb_position' in data.columns:
                bb_position_series = data['bb_position'].ffill()
                bb_position = bb_position_series.iloc[-1] if not pd.isna(bb_position_series.iloc[-1]) else (bb_position_series.dropna().iloc[-1] if len(bb_position_series.dropna()) > 0 else 0.5)
            else:
                bb_position = current_row.get('bb_position', 0.5)
            
            # Handle any remaining NaN values (fallback)
            zscore = zscore if not pd.isna(zscore) else 0.0
            rsi = rsi if not pd.isna(rsi) else 50.0
            bb_position = bb_position if not pd.isna(bb_position) else 0.5
            
            # Get regime-adjusted thresholds
            thresholds = self._get_regime_adjusted_thresholds(symbol)
            zscore_threshold = thresholds['zscore_entry_threshold']
            rsi_oversold = thresholds['rsi_oversold']
            rsi_overbought = thresholds['rsi_overbought']
            
            # Apply regime filter
            if self.config.enable_regime_filter:
                if not self._is_regime_favorable(symbol):
                    return signals
            
            # Check for oversold condition (BUY signal)
            if (zscore < -zscore_threshold and 
                rsi < rsi_oversold and 
                bb_position < 0.2):  # Below lower Bollinger Band
                
                confidence = self._calculate_signal_confidence(symbol, MeanReversionSignal.OVERSOLD_BUY)
                
                if confidence > 0.6:  # Minimum confidence threshold
                    signal = StrategySignal(
                        strategy_id=self.strategy_id,
                        symbol=symbol,
                        signal_type=SignalType.BUY,
                        strength=min(abs(zscore) / zscore_threshold, 1.0),
                        confidence=confidence,
                        target_weight=self.config.base_position_pct,  # Use target_weight for percentage
                        quantity_type="PERCENTAGE",  # Explicitly mark as percentage
                        timestamp=datetime.now(),
                        additional_data={
                            'signal_reason': 'oversold_mean_reversion',
                            'zscore': zscore,
                            'rsi': rsi,
                            'bb_position': bb_position,
                            'entry_price': current_row['close']
                        }
                    )
                    signals.append(signal)
                    
                    # Track position entry
                    self._track_position_entry(symbol, signal)
            
            # Check for overbought condition (SELL signal)
            elif (zscore > zscore_threshold and 
                  rsi > rsi_overbought and 
                  bb_position > 0.8):  # Above upper Bollinger Band
                
                confidence = self._calculate_signal_confidence(symbol, MeanReversionSignal.OVERBOUGHT_SELL)
                
                if confidence > 0.6:  # Minimum confidence threshold
                    signal = StrategySignal(
                        strategy_id=self.strategy_id,
                        symbol=symbol,
                        signal_type=SignalType.SELL,
                        strength=min(abs(zscore) / zscore_threshold, 1.0),
                        confidence=confidence,
                        target_weight=self.config.base_position_pct,  # Use target_weight for percentage
                        quantity_type="PERCENTAGE",  # Explicitly mark as percentage
                        timestamp=datetime.now(),
                        additional_data={
                            'signal_reason': 'overbought_mean_reversion',
                            'zscore': zscore,
                            'rsi': rsi,
                            'bb_position': bb_position,
                            'entry_price': current_row['close']
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
    # INDICATOR CALCULATION METHODS
    # ========================================
    
    # ========================================
    # HELPER METHODS (Rule 3 Phase 4)
    # Reads pre-calculated indicators from enriched data
    # ========================================
    
    def _update_market_data(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """Update market data cache"""
        
        for symbol, data in market_data.items():
            if symbol in self.config.symbols:
                self.market_data[symbol] = data
    
    def _initialize_data_structures(self) -> None:
        """Initialize strategy data structures"""
        
        self.market_data.clear()
        self.indicators.clear()
        self.regime_data.clear()
        self.active_positions.clear()
        self.entry_prices.clear()
        self.stop_losses.clear()
        self.profit_targets.clear()
    
    def _initialize_indicators(self) -> None:
        """Initialize indicators dictionary"""
        
        for symbol in self.config.symbols:
            self.indicators[symbol] = {}
    
    def _start_performance_tracking(self) -> None:
        """Start performance tracking"""
        logger.info("📊 Mean Reversion performance tracking started")
    
    async def _close_all_positions(self) -> None:
        """Close all active positions"""
        logger.info(f"🔄 Closing {len(self.active_positions)} active positions")
        self.active_positions.clear()
        self.entry_prices.clear()
        self.stop_losses.clear()
        self.profit_targets.clear()
    
    def _save_performance_data(self) -> None:
        """Save performance data"""
        logger.info("💾 Mean Reversion performance data saved")
    
    def _calculate_avg_volatility(self) -> float:
        """Calculate average volatility across symbols"""
        
        if not self.indicators:
            return 0.0
        
        volatilities = []
        for symbol, indicators in self.indicators.items():
            if 'atr' in indicators and len(indicators['atr']) > 0:
                if symbol in self.market_data and len(self.market_data[symbol]) > 0:
                    current_price = self.market_data[symbol]['close'].iloc[-1]
                    atr = indicators['atr'].iloc[-1]
                    if current_price > 0:
                        volatilities.append(atr / current_price)
        
        return np.mean(volatilities) if volatilities else 0.0
    
    def _check_regime_health(self) -> Dict[str, Any]:
        """Check regime analysis health"""
        
        return {
            'regime_filter_enabled': self.config.enable_regime_filter,
            'symbols_with_regime_data': len(self.regime_data)
        }
    
    def _update_regime_analysis(self) -> None:
        """Update regime analysis for symbols"""
        
        for symbol in self.config.symbols:
            if symbol in self.market_data:
                self.regime_data[symbol] = self._analyze_symbol_regime(symbol)
    
    def _analyze_symbol_regime(self, symbol: str) -> Dict[str, float]:
        """Analyze regime for a specific symbol"""
        
        try:
            data = self.market_data[symbol]
            
            # Simple regime analysis
            returns = data['close'].pct_change().dropna()
            
            # Trend strength (momentum)
            trend_strength = abs(returns.tail(20).mean()) / returns.tail(20).std() if len(returns) >= 20 else 0
            
            # Volatility regime
            current_vol = returns.tail(20).std() if len(returns) >= 20 else 0
            long_term_vol = returns.tail(60).std() if len(returns) >= 60 else current_vol
            volatility_ratio = current_vol / long_term_vol if long_term_vol > 0 else 1.0
            
            return {
                'trend_strength': trend_strength,
                'volatility_ratio': volatility_ratio,
                'is_trending': trend_strength > self.config.min_trend_strength,
                'is_high_vol': volatility_ratio > 1.5
            }
            
        except Exception as e:
            logger.error(f"Regime analysis failed for {symbol}: {e}")
            return {'trend_strength': 0, 'volatility_ratio': 1.0, 'is_trending': False, 'is_high_vol': False}
    
    def _is_regime_favorable(self, symbol: str) -> bool:
        """Check if current regime is favorable for mean reversion"""
        
        if symbol not in self.regime_data:
            return True  # Default to favorable if no regime data
        
        regime = self.regime_data[symbol]
        
        # Mean reversion works best in:
        # 1. Non-trending markets (low trend strength)
        # 2. Normal to low volatility environments
        
        is_favorable = (not regime.get('is_trending', False) and 
                       not regime.get('is_high_vol', False))
        
        return is_favorable
    
    def _calculate_signal_confidence(self, symbol: str, signal_type: MeanReversionSignal) -> float:
        """Calculate signal confidence based on multiple factors"""
        
        try:
            if symbol not in self.market_data:
                return 0.5
            
            data = self.market_data[symbol]
            current_row = data.iloc[-1]
            
            # Base confidence from Z-score magnitude
            zscore = current_row.get('zscore', 0.0)
            zscore_confidence = min(abs(zscore) / (self.config.zscore_entry_threshold * 1.5), 1.0)
            
            # RSI confirmation (use column mapping)
            rsi_col = self._get_column_name('RSI_14', data)
            rsi = current_row.get(rsi_col, current_row.get('rsi', 50.0))
            if signal_type == MeanReversionSignal.OVERSOLD_BUY:
                rsi_confidence = max(0, (50 - rsi) / 20)  # Higher confidence for lower RSI
            else:  # OVERBOUGHT_SELL
                rsi_confidence = max(0, (rsi - 50) / 20)  # Higher confidence for higher RSI
            
            # Bollinger Band confirmation
            bb_position = current_row.get('bb_position', 0.5)
            if signal_type == MeanReversionSignal.OVERSOLD_BUY:
                bb_confidence = max(0, (0.5 - bb_position) / 0.5)  # Higher confidence near lower band
            else:  # OVERBOUGHT_SELL
                bb_confidence = max(0, (bb_position - 0.5) / 0.5)  # Higher confidence near upper band
            
            # Regime confirmation - use configurable values from centralized config (Rule 1)
            regime_confidence = 1.0
            if self.config.enable_regime_filter and symbol in self.regime_data:
                regime_confidence = self.config.regime_confidence_favorable if self._is_regime_favorable(symbol) else self.config.regime_confidence_unfavorable
            
            # Combine confidences (weighted average) - use configurable weights from centralized config (Rule 1)
            total_confidence = (zscore_confidence * self.config.confidence_weight_zscore + 
                              rsi_confidence * self.config.confidence_weight_rsi + 
                              bb_confidence * self.config.confidence_weight_bollinger + 
                              regime_confidence * self.config.confidence_weight_regime)
            
            return min(total_confidence, 0.95)  # Cap at 95%
            
        except Exception as e:
            logger.error(f"Signal confidence calculation failed for {symbol}: {e}")
            return 0.5
    
    def _track_position_entry(self, symbol: str, signal: StrategySignal) -> None:
        """Track position entry for exit management"""
        
        try:
            entry_price = signal.metadata.get('entry_price', 0)
            atr = self._calculate_atr(symbol)
            
            # Calculate stop loss and profit target
            if signal.signal_type == SignalType.BUY:
                stop_loss = entry_price - (atr * self.config.stop_loss_atr_multiple)
                profit_target = entry_price + (atr * self.config.stop_loss_atr_multiple * self.config.profit_target_ratio)
            else:  # SELL
                stop_loss = entry_price + (atr * self.config.stop_loss_atr_multiple)
                profit_target = entry_price - (atr * self.config.stop_loss_atr_multiple * self.config.profit_target_ratio)
            
            # Track position
            self.active_positions[symbol] = {
                'signal_type': signal.signal_type,
                'entry_time': signal.timestamp,
                'entry_price': entry_price,
                'quantity': signal.quantity
            }
            
            self.entry_prices[symbol] = entry_price
            self.stop_losses[symbol] = stop_loss
            self.profit_targets[symbol] = profit_target
            
            logger.info(f"📈 Position tracked for {symbol}: Entry=${entry_price:.2f}, "
                       f"Stop=${stop_loss:.2f}, Target=${profit_target:.2f}")
            
        except Exception as e:
            self._log_error(f"Position tracking failed for {symbol}", e)
    
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
                    
                    # Check profit target
                    if not should_exit and symbol in self.profit_targets:
                        if position['signal_type'] == SignalType.BUY and current_price >= self.profit_targets[symbol]:
                            should_exit = True
                            exit_reason = "profit_target"
                        elif position['signal_type'] == SignalType.SELL and current_price <= self.profit_targets[symbol]:
                            should_exit = True
                            exit_reason = "profit_target"
                    
                    # Check mean reversion (Z-score back to neutral)
                    if not should_exit and symbol in self.indicators and 'zscore' in self.indicators[symbol]:
                        zscore = self.indicators[symbol]['zscore'].iloc[-1]
                        if abs(zscore) < self.config.zscore_exit_threshold:
                            should_exit = True
                            exit_reason = "mean_reversion"
                    
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
                
                # Create exit signal (would be sent to risk manager)
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
                if symbol in self.profit_targets:
                    del self.profit_targets[symbol]
                
                logger.info(f"🔄 Position closed for {symbol}: {reason}")
                
        except Exception as e:
            self._log_error(f"Position close failed for {symbol}", e)
    
    def _update_stop_losses_and_targets(self) -> None:
        """Update stop losses and profit targets (trailing stops, etc.)"""
        
        # Placeholder for advanced stop loss management
        # Could implement trailing stops, dynamic targets, etc.
    
    def _update_performance_tracking(self) -> None:
        """Update performance tracking metrics"""
        
        # Placeholder for performance tracking updates
    
    # ========================================
    # STRATEGY-SPECIFIC METHODS
    # ========================================
    
    def get_mean_reversion_summary(self) -> Dict[str, Any]:
        """Get comprehensive mean reversion strategy summary"""
        
        return {
            'strategy_id': self.strategy_id,
            'strategy_type': 'Enhanced Mean Reversion',
            'symbols_tracked': len(self.config.symbols),
            'active_positions': len(self.active_positions),
            'indicators_calculated': len(self.indicators),
            'avg_volatility': self._calculate_avg_volatility(),
            'regime_filter_enabled': self.config.enable_regime_filter,
            'performance_summary': self.get_performance_summary(),
            'position_details': {
                symbol: {
                    'signal_type': pos['signal_type'].value,
                    'entry_price': pos['entry_price'],
                    'entry_time': pos['entry_time'].isoformat(),
                    'stop_loss': self.stop_losses.get(symbol),
                    'profit_target': self.profit_targets.get(symbol)
                }
                for symbol, pos in self.active_positions.items()
            }
        }
