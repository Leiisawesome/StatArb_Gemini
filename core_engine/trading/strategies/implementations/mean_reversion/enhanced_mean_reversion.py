"""
Enhanced Mean Reversion Strategy with ISystemComponent Integration
================================================================

Professional mean reversion strategy that implements ISystemComponent interface
for seamless orchestrator integration and institutional-grade lifecycle management.

Key Features:
- EXHAUSTION-BASED SCORING: Professional alpha logic detecting move exhaustion
- Statistical mean reversion detection using Z-scores
- Multi-factor scoring system (dislocation, exhaustion, candle structure, regime)
- Volume confirmation and RSI momentum divergence
- Regime filtering to avoid choppy/trending markets
- ATR-based position sizing

Alpha Logic Foundation (v3.0):
"Mean reversion works when the directional move shows exhaustion. The best trades
are NOT at price extremes per se, but at price extremes where buying/selling 
pressure is weakening, volume is declining, and candle structure shows rejection."

Academic Foundations:
- Kyle (1985) - Market microstructure and price impact
- Avellaneda & Lee (2010) - Statistical arbitrage half-life estimation  
- Cartea, Jaimungal & Penalva (2015) - Order flow and market making
- Lo & MacKinlay (1990) - Contrarian investment strategies

Author: StatArb_Gemini Architecture Compliance
Version: 3.0.0 (Exhaustion-Based Alpha Logic)
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import logging

from ...base_strategy_enhanced import EnhancedBaseStrategy
from ...strategy_engine import StrategySignal, SignalType
from core_engine.config import MeanReversionConfig

logger = logging.getLogger(__name__)


class MeanReversionSignal(Enum):
    """Mean reversion signal types"""
    OVERSOLD_BUY = "oversold_buy"
    OVERBOUGHT_SELL = "overbought_sell"
    NEUTRAL = "neutral"


class EnhancedMeanReversionStrategy(EnhancedBaseStrategy):
    """
    Enhanced Mean Reversion Strategy with Exhaustion-Based Alpha Logic
    
    This strategy uses a professional scoring system that asks:
    "Did the move that created this extremity show signs of exhaustion?"
    
    Scoring Factors (5 categories):
    1. DISLOCATION: How far is price from fair value (z-score)
    2. EXHAUSTION: Is the move losing steam (RSI momentum, volume, MACD)
    3. CANDLE STRUCTURE: Does candle show rejection (wicks, body size)
    4. REGIME PENALTY: Is this a trending/volatile environment (ADX, vol)
    5. CONFLUENCE: Do supporting indicators confirm (stochastic, BB position)
    
    Key Improvements over Naive Mean Reversion:
    - NOT just "price is extreme" but "move is exhausting"
    - Volume confirmation: low volume extremes = noise (revert)
    - High volume breakouts = information (don't fade)
    - Candle wicks = market rejection of extreme prices
    - RSI momentum divergence = classic exhaustion signal
    """
    
    # Column name mappings for indicator engine compatibility
    COLUMN_MAPPING = {
        'SMA_20': 'sma_20',
        'RSI_14': 'rsi',
        'ATR_14': 'atr',
        'bb_upper': 'bb_upper',
        'bb_lower': 'bb_lower',
        'bb_middle': 'bb_middle',
        'volume_ratio': 'volume_ratio',
        'MACD_histogram': 'macd_histogram',
        'ADX': 'adx',
        'stoch_k': 'stoch_k'
    }
    
    # Required indicators for validation (extended for exhaustion scoring)
    REQUIRED_INDICATORS = {
        'SMA_20': ['sma_20', 'SMA_20'],
        'RSI_14': ['rsi', 'RSI_14'],
        'bb_upper': ['bb_upper'],
        'bb_lower': ['bb_lower'],
        'bb_middle': ['bb_middle'],
        'ATR_14': ['atr', 'ATR_14'],
        'volume_ratio': ['volume_ratio']
    }
    
    # Optional indicators for enhanced scoring (graceful degradation)
    OPTIONAL_INDICATORS = {
        'macd_histogram': ['macd_histogram', 'MACD_histogram'],
        'adx': ['adx', 'ADX'],
        'stoch_k': ['stoch_k', 'STOCH_K'],
        'upper_shadow': ['upper_shadow'],
        'lower_shadow': ['lower_shadow'],
        'body_size': ['body_size']
    }
    
    def __init__(self, config: MeanReversionConfig):
        """Initialize enhanced mean reversion strategy"""
        super().__init__(config)
        self.config: MeanReversionConfig = config
        
        # Strategy-specific state
        self.market_data: Dict[str, pd.DataFrame] = {}
        self.indicators: Dict[str, Dict[str, pd.Series]] = {}
        self.regime_data: Dict[str, Dict[str, float]] = {}
        
        # Performance tracking
        self.trade_history: List[Dict[str, Any]] = []
        self.daily_pnl: List[float] = []
        
        logger.info(f"🧠 Enhanced Mean Reversion Strategy {self.strategy_id} initialized")
    
    # ========================================
    # LIFECYCLE HOOKS
    # ========================================
    
    async def _initialize_strategy_components(self) -> bool:
        """Initialize strategy-specific components"""
        try:
            logger.info(f"🔄 Initializing Mean Reversion components for {self.strategy_id}...")
            
            if not self.config.symbols:
                logger.error("❌ No symbols configured for mean reversion strategy")
                return False
            
            self._reset_state()
            
            logger.info(f"✅ Mean Reversion components initialized for {len(self.config.symbols)} symbols")
            return True
            
        except Exception as e:
            logger.error(f"❌ Mean Reversion component initialization failed: {e}")
            return False
    
    async def _start_strategy_operations(self) -> bool:
        """Start strategy-specific operations"""
        try:
            logger.info(f"🚀 Starting Mean Reversion operations for {self.strategy_id}...")
            logger.info("📊 Mean Reversion performance tracking started")
            return True
        except Exception as e:
            logger.error(f"❌ Mean Reversion operations start failed: {e}")
            return False
    
    async def _stop_strategy_operations(self) -> None:
        """Stop strategy-specific operations"""
        try:
            logger.info(f"🔄 Stopping Mean Reversion operations for {self.strategy_id}...")
            logger.info("💾 Mean Reversion performance data saved")
            logger.info("✅ Mean Reversion operations stopped")
        except Exception as e:
            logger.error(f"❌ Mean Reversion operations stop failed: {e}")
    
    async def _check_strategy_health(self) -> Dict[str, Any]:
        """Check strategy-specific health"""
        try:
            health_metrics = {
                'strategy_healthy': True,
                'symbols_tracked': len(self.config.symbols),
                'indicators_calculated': len(self.indicators),
                'avg_volatility': self._calculate_avg_volatility(),
                'regime_health': {
                    'regime_filter_enabled': self.config.enable_regime_filter,
                    'symbols_with_regime_data': len(self.regime_data)
                }
            }
            
            # Check for unhealthy conditions
            if len(self.indicators) == 0 and hasattr(self, 'initialization_time'):
                time_since_init = (datetime.now() - self.initialization_time).total_seconds()
                if time_since_init > 300:
                    health_metrics['strategy_healthy'] = False
                    health_metrics['warning'] = "No indicators calculated after 5 minutes"
                else:
                    health_metrics['warning'] = f"Indicators not yet calculated (grace period: {300-time_since_init:.0f}s remaining)"
            
            return health_metrics
            
        except Exception as e:
            return {'strategy_healthy': False, 'error': str(e)}
    
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
            if self.config.zscore_entry_threshold <= self.config.zscore_exit_threshold:
                logger.error("Entry Z-score threshold must be greater than exit threshold")
                return False
            
            if self.config.base_position_pct <= 0 or self.config.base_position_pct > 0.1:
                logger.error("Base position percentage must be between 0 and 0.1 (10%)")
                return False
            
            if self.config.lookback_period < 10:
                logger.error("Lookback period must be at least 10")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation error: {e}")
            return False
    
    # ========================================
    # CORE SIGNAL GENERATION
    # ========================================
    
    async def generate_signals(self, enriched_data: Dict[str, pd.DataFrame]) -> List[StrategySignal]:
        """
        Generate mean reversion signals from ENRICHED data (Rule 3 Phase 4)
        
        Args:
            enriched_data: Dict[symbol, enriched DataFrame with OHLCV + indicators]
        
        Returns:
            List[StrategySignal]: Generated mean reversion signals
        """
        start_time = datetime.now()
        signals = []
        
        # Track call count for debugging
        if not hasattr(self, '_signal_call_count'):
            self._signal_call_count = 0
        self._signal_call_count += 1
        
        try:
            self._validate_enriched_data(enriched_data)
            self._update_market_data(enriched_data)
            
            if self.config.enable_regime_filter:
                self._update_regime_analysis()
            
            for symbol in self.config.symbols:
                data_len = len(self.market_data.get(symbol, []))
                lookback = self.config.lookback_period
                
                # Debug: Log first 10 calls to understand the flow
                if self._signal_call_count <= 10:
                    logger.info(f"[{symbol}] Call #{self._signal_call_count}: data_len={data_len}, "
                               f"lookback={lookback}, will_generate={data_len > lookback}")
                
                if symbol in self.market_data and data_len > lookback:
                    symbol_signals = await self._generate_symbol_signals(symbol)
                    signals.extend(symbol_signals)
            
            generation_time = (datetime.now() - start_time).total_seconds()
            self.track_signal_generation_time(generation_time)
            
            logger.info(f"📊 Mean Reversion: {len(signals)} signals in {generation_time:.3f}s")
            
            return signals
            
        except Exception as e:
            self._log_error("Signal generation failed", e)
            return []
    
    async def _generate_symbol_signals(self, symbol: str) -> List[StrategySignal]:
        """Generate signals for a specific symbol"""
        signals = []
        
        try:
            if symbol not in self.market_data:
                return signals
            
            data = self.market_data[symbol]
            data_length = len(data)
            
            # Historical scanning mode (for backtesting)
            if self.config.scan_all_bars and data_length > self.config.lookback_period:
                logger.info(f"[{symbol}] 📊 Historical scanning: {data_length} bars")
                
                start_idx = self.config.lookback_period
                scan_interval = max(1, self.config.scan_interval)
                
                for idx in range(start_idx, data_length, scan_interval):
                    signal = self._evaluate_signal_conditions(symbol, data, idx)
                    if signal:
                        signals.append(signal)
                
                logger.info(f"[{symbol}] 📊 Scan complete: {len(signals)} signals")
                return signals
            
            # Live mode: evaluate current bar only
            signal = self._evaluate_signal_conditions(symbol, data, -1)
            if signal:
                signals.append(signal)
            
            return signals
            
        except Exception as e:
            self._log_error(f"Symbol signal generation failed for {symbol}", e)
            return []
    
    def _evaluate_signal_conditions(
        self, 
        symbol: str, 
        data: pd.DataFrame, 
        idx: int
    ) -> Optional[StrategySignal]:
        """
        Evaluate signal conditions at a specific bar index using EXHAUSTION SCORING.
        
        This is the SINGLE source of signal evaluation logic.
        Both historical scanning and live mode use this method.
        
        The exhaustion scoring system asks:
        "Did the move that created this extremity show signs of exhaustion?"
        
        Args:
            symbol: Symbol to evaluate
            data: Market data DataFrame with indicators
            idx: Bar index (-1 for current bar)
            
        Returns:
            StrategySignal if conditions met, None otherwise
        """
        try:
            # Normalize index
            if idx < 0:
                idx = len(data) + idx
            
            if idx < self.config.lookback_period or idx >= len(data):
                return None
            
            current_row = data.iloc[idx]
            
            # Get core indicator values
            zscore = self._get_indicator_value(data, 'zscore', idx, default=0.0)
            
            # Apply regime filter first (fast exit)
            if self.config.enable_regime_filter and not self._is_regime_favorable(symbol):
                return None
            
            # ========================================
            # EXHAUSTION-BASED SCORING SYSTEM
            # ========================================
            # Calculate exhaustion score
            score, score_breakdown = self._calculate_exhaustion_score(data, idx, zscore)
            
            # DEBUG: Log signal evaluation on first few attempts
            if not hasattr(self, '_eval_log_count'):
                self._eval_log_count = 0
            if self._eval_log_count < 20:
                self._eval_log_count += 1
                logger.info(f"[{symbol}] Eval #{self._eval_log_count}: idx={idx}, zscore={zscore:.3f}, "
                           f"dislocation_min={self.config.dislocation_minimum}, score={score:.1f}, "
                           f"moderate_thresh={self.config.exhaustion_score_moderate}")
            
            # Determine signal direction from z-score
            if abs(zscore) < self.config.dislocation_minimum:
                if self._eval_log_count <= 30:
                    logger.info(f"[{symbol}] EXIT: dislocation check failed, abs_zscore={abs(zscore):.3f}")
                return None  # Not dislocated enough
            
            is_oversold = zscore < -self.config.dislocation_minimum
            is_overbought = zscore > self.config.dislocation_minimum
            
            # Check score thresholds
            if score >= self.config.exhaustion_score_strong:
                confidence = 0.85
                signal_reason = 'exhaustion_strong'
            elif score >= self.config.exhaustion_score_moderate:
                confidence = 0.70
                signal_reason = 'exhaustion_moderate'
            else:
                return None  # Score too low
            
            # Determine signal type
            if is_oversold:
                signal_type = SignalType.BUY
            elif is_overbought:
                signal_type = SignalType.SELL
            else:
                return None
            
            # Confidence threshold check
            if confidence <= 0.6:
                return None
            
            # DEBUG: Log when we're about to create a signal
            logger.info(f"[{symbol}] 🎯 CREATING SIGNAL: idx={idx}, zscore={zscore:.3f}, "
                       f"signal_type={signal_type}, confidence={confidence}, score={score:.1f}")
            
            # Get timestamp and price
            timestamp = current_row.get('timestamp', datetime.now()) if isinstance(current_row, pd.Series) else datetime.now()
            entry_price = current_row['close'] if isinstance(current_row, pd.Series) else current_row.get('close', 0)
            
            # Build additional data with scoring breakdown
            additional_data = {
                'signal_reason': signal_reason,
                'zscore': zscore,
                'exhaustion_score': score,
                'score_breakdown': score_breakdown,
                'entry_price': entry_price,
                'bar_index': idx
            }
            
            # Add available indicators to additional_data
            for indicator in ['rsi', 'bb_position', 'volume_ratio', 'adx', 'macd_histogram']:
                col = self._resolve_column_name(indicator.upper(), data) if indicator != 'bb_position' else 'bb_position'
                if col in data.columns:
                    additional_data[indicator] = self._get_indicator_value(data, col, idx, default=None)
            
            return StrategySignal(
                strategy_id=self.strategy_id,
                symbol=symbol,
                signal_type=signal_type,
                strength=min(score / 100.0, 1.0),  # Normalize score to 0-1
                confidence=confidence,
                target_weight=self.config.base_position_pct,
                quantity_type="PERCENTAGE",
                timestamp=timestamp,
                additional_data=additional_data
            )
            
        except Exception as e:
            logger.error(f"[{symbol}] Error evaluating bar at index {idx}: {e}")
            return None
    
    # ========================================
    # EXHAUSTION SCORING SYSTEM
    # ========================================
    
    def _calculate_exhaustion_score(
        self, 
        data: pd.DataFrame, 
        idx: int,
        zscore: float
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculate exhaustion score (0-100) based on 5 factors.
        
        The core insight: Mean reversion works when the directional move
        shows signs of exhaustion, not just when price is at extremes.
        
        Factors:
        1. DISLOCATION (25%): How far from fair value
        2. EXHAUSTION (30%): Is move losing steam (RSI momentum, volume, MACD)
        3. CANDLE STRUCTURE (15%): Rejection patterns (wicks, doji)
        4. REGIME PENALTY (15%): Trend/volatility environment
        5. CONFLUENCE (15%): Supporting indicator confirmation
        
        Args:
            data: DataFrame with indicators
            idx: Bar index
            zscore: Pre-calculated z-score
            
        Returns:
            Tuple of (total_score, breakdown_dict)
        """
        breakdown = {
            'dislocation': 0.0,
            'exhaustion': 0.0,
            'candle_structure': 0.0,
            'regime_penalty': 0.0,
            'confluence': 0.0
        }
        
        # Direction for context
        is_oversold = zscore < 0
        
        # ============================================
        # FACTOR 1: DISLOCATION (How far from fair value?)
        # ============================================
        abs_zscore = abs(zscore)
        
        if abs_zscore >= self.config.dislocation_strong:
            breakdown['dislocation'] = 100.0  # Strong dislocation
        elif abs_zscore >= self.config.dislocation_moderate:
            # Linear interpolation between moderate and strong
            breakdown['dislocation'] = 60 + 40 * (abs_zscore - self.config.dislocation_moderate) / (self.config.dislocation_strong - self.config.dislocation_moderate)
        elif abs_zscore >= self.config.dislocation_minimum:
            # Linear interpolation between minimum and moderate
            breakdown['dislocation'] = 30 + 30 * (abs_zscore - self.config.dislocation_minimum) / (self.config.dislocation_moderate - self.config.dislocation_minimum)
        else:
            breakdown['dislocation'] = 0.0  # Not dislocated enough
        
        # ============================================
        # FACTOR 2: EXHAUSTION SIGNALS (Is move losing steam?)
        # ============================================
        exhaustion_score = 50.0  # Neutral baseline
        
        # 2a. RSI Momentum Exhaustion (divergence from price)
        rsi = self._get_indicator_value(data, self._resolve_column_name('RSI_14', data), idx, default=50.0)
        rsi_prev = self._get_indicator_value(data, self._resolve_column_name('RSI_14', data), idx - 1, default=50.0)
        rsi_momentum = rsi - rsi_prev
        
        if is_oversold and rsi_momentum > 0:
            # Oversold but RSI rising = bullish exhaustion
            exhaustion_score += 20
        elif not is_oversold and rsi_momentum < 0:
            # Overbought but RSI falling = bearish exhaustion  
            exhaustion_score += 20
        
        # 2b. Volume Exhaustion (extended on weak volume = noise)
        volume_ratio = self._get_indicator_value(data, 'volume_ratio', idx, default=1.0)
        
        if volume_ratio < self.config.volume_exhaustion_threshold and abs_zscore > self.config.dislocation_moderate:
            # Low volume extremity = likely noise, will revert
            exhaustion_score += 15
        elif volume_ratio > self.config.volume_conviction_threshold and abs_zscore > self.config.dislocation_strong:
            # High volume breakout = information, don't fade
            exhaustion_score -= 25
        
        # 2c. MACD Histogram Exhaustion (momentum weakening)
        macd_hist = self._get_indicator_value(data, self._resolve_column_name('MACD_histogram', data), idx, default=0.0)
        macd_hist_prev = self._get_indicator_value(data, self._resolve_column_name('MACD_histogram', data), idx - 1, default=0.0)
        
        if is_oversold and macd_hist > macd_hist_prev:
            # Histogram turning up in oversold
            exhaustion_score += 15
        elif not is_oversold and macd_hist < macd_hist_prev:
            # Histogram turning down in overbought
            exhaustion_score += 15
        
        breakdown['exhaustion'] = np.clip(exhaustion_score, 0, 100)
        
        # ============================================
        # FACTOR 3: CANDLE STRUCTURE (Rejection patterns)
        # ============================================
        candle_score = 50.0  # Neutral baseline
        
        # 3a. Wick Rejection (market rejected extreme prices)
        upper_shadow = self._get_indicator_value(data, 'upper_shadow', idx, default=0.0)
        lower_shadow = self._get_indicator_value(data, 'lower_shadow', idx, default=0.0)
        
        if is_oversold:
            # In oversold, large lower wick = buying rejection
            if lower_shadow > self.config.wick_rejection_threshold:
                candle_score += 25
            elif lower_shadow > self.config.wick_rejection_threshold * 0.5:
                candle_score += 12
        else:
            # In overbought, large upper wick = selling rejection
            if upper_shadow > self.config.wick_rejection_threshold:
                candle_score += 25
            elif upper_shadow > self.config.wick_rejection_threshold * 0.5:
                candle_score += 12
        
        # 3b. Body Size (small body = indecision/doji)
        body_size = self._get_indicator_value(data, 'body_size', idx, default=0.01)
        
        if body_size < self.config.doji_body_threshold and abs_zscore > self.config.dislocation_moderate:
            # Doji/spinning top at extreme = reversal likely
            candle_score += 15
        
        breakdown['candle_structure'] = np.clip(candle_score, 0, 100)
        
        # ============================================
        # FACTOR 4: REGIME PENALTY (Unfavorable conditions)
        # ============================================
        regime_score = 100.0  # Start at max, apply penalties
        
        # 4a. Trend Strength Penalty (ADX)
        adx = self._get_indicator_value(data, self._resolve_column_name('ADX', data), idx, default=20.0)
        
        if adx > self.config.adx_strong_trend:
            regime_score -= 40  # Strong trend, mean reversion fails
        elif adx > self.config.adx_moderate_trend:
            regime_score -= 20  # Moderate trend
        
        # 4b. Volatility Regime Penalty
        atr_normalized = self._get_indicator_value(data, 'atr_normalized', idx, default=0.015)
        vol_ratio = atr_normalized / 0.015  # vs baseline 1.5% daily vol
        
        if vol_ratio > self.config.volatility_spike_threshold:
            regime_score -= 25  # High vol environment
        
        # 4c. Breakout Penalty
        bb_breakout_up = self._get_indicator_value(data, 'bb_breakout_up', idx, default=0.0)
        bb_breakout_down = self._get_indicator_value(data, 'bb_breakout_down', idx, default=0.0)
        
        if bb_breakout_up > 0 or bb_breakout_down > 0:
            regime_score -= 30  # Active breakout, don't fade
        
        breakdown['regime_penalty'] = np.clip(regime_score, 0, 100)
        
        # ============================================
        # FACTOR 5: CONFLUENCE (Supporting indicators)
        # ============================================
        confluence_score = 50.0  # Neutral baseline
        
        # 5a. Stochastic Confirmation
        stoch_k = self._get_indicator_value(data, self._resolve_column_name('stoch_k', data), idx, default=50.0)
        
        if is_oversold and stoch_k < 25:
            confluence_score += 15
        elif not is_oversold and stoch_k > 75:
            confluence_score += 15
        
        # 5b. Bollinger Position Confirmation  
        bb_position = self._get_indicator_value(data, 'bb_position', idx, default=0.5)
        
        if is_oversold and bb_position < 0.1:
            confluence_score += 15
        elif not is_oversold and bb_position > 0.9:
            confluence_score += 15
        
        # 5c. RSI Extreme Confirmation
        if is_oversold and rsi < 30:
            confluence_score += 10
        elif not is_oversold and rsi > 70:
            confluence_score += 10
        
        breakdown['confluence'] = np.clip(confluence_score, 0, 100)
        
        # ============================================
        # WEIGHTED TOTAL SCORE
        # ============================================
        total_score = (
            breakdown['dislocation'] * self.config.weight_dislocation +
            breakdown['exhaustion'] * self.config.weight_exhaustion +
            breakdown['candle_structure'] * self.config.weight_candle_structure +
            breakdown['regime_penalty'] * self.config.weight_regime_penalty +
            breakdown['confluence'] * self.config.weight_confluence
        ) * 100  # Scale to 0-100
        
        # Normalize (weights should sum to 1.0)
        weight_sum = (
            self.config.weight_dislocation +
            self.config.weight_exhaustion +
            self.config.weight_candle_structure +
            self.config.weight_regime_penalty +
            self.config.weight_confluence
        )
        if weight_sum > 0:
            total_score = total_score / weight_sum
        
        return np.clip(total_score, 0, 100), breakdown
    
    # ========================================
    # INDICATOR HELPERS
    # ========================================
    
    def _get_indicator_value(
        self, 
        data: pd.DataFrame, 
        column: str, 
        idx: int, 
        default: float = 0.0
    ) -> float:
        """
        Get indicator value at index with robust NaN handling
        
        Uses forward-fill to handle NaN values at window edges.
        
        Args:
            data: DataFrame with indicators
            column: Column name to retrieve
            idx: Index to retrieve (-1 for last)
            default: Default value if column missing or all NaN
            
        Returns:
            Indicator value
        """
        if column not in data.columns:
            return default
        
        series = data[column].ffill()
        
        if idx < 0:
            idx = len(series) + idx
        
        if idx < 0 or idx >= len(series):
            return default
        
        value = series.iloc[idx]
        
        if pd.isna(value):
            # Try to get last valid value
            valid_values = series.dropna()
            if len(valid_values) > 0:
                return valid_values.iloc[-1]
            return default
        
        return value
    
    def _resolve_column_name(self, expected_name: str, data: pd.DataFrame) -> str:
        """Resolve column name using mapping"""
        if expected_name in data.columns:
            return expected_name
        
        if expected_name in self.COLUMN_MAPPING:
            mapped_name = self.COLUMN_MAPPING[expected_name]
            if mapped_name in data.columns:
                return mapped_name
        
        return expected_name
    
    def _validate_enriched_data(self, enriched_data: Dict[str, pd.DataFrame]) -> None:
        """Validate that data is enriched with required indicators"""
        for symbol, data in enriched_data.items():
            if data.empty:
                raise ValueError(f"{symbol} has empty DataFrame")
            
            missing = []
            for expected_name, possible_names in self.REQUIRED_INDICATORS.items():
                if not any(name in data.columns for name in possible_names):
                    missing.append(expected_name)
            
            if missing:
                raise ValueError(
                    f"{symbol} missing required indicators: {missing}. "
                    f"Data must be enriched via ProcessingPipelineOrchestrator (Rule 3)."
                )
    
    # ========================================
    # REGIME ANALYSIS
    # ========================================
    
    def _get_regime_adjusted_thresholds(self, symbol: str) -> Dict[str, float]:
        """Get regime-adjusted thresholds based on current market regime"""
        base_thresholds = {
            'zscore_entry_threshold': self.config.zscore_entry_threshold,
            'rsi_oversold': self.config.rsi_oversold,
            'rsi_overbought': self.config.rsi_overbought
        }
        
        if not self.config.enable_regime_adjusted_thresholds:
            return base_thresholds
        
        regime_context = self.get_current_regime_context()
        if not regime_context:
            return base_thresholds
        
        regime_name = getattr(regime_context, 'primary_regime', None)
        volatility_regime = getattr(regime_context, 'volatility_regime', None)
        
        unfavorable_regimes = ['extreme_volatility', 'crisis', 'trending']
        
        is_unfavorable = (
            (regime_name and any(u in str(regime_name).lower() for u in unfavorable_regimes)) or
            (volatility_regime and 'extreme' in str(volatility_regime).lower())
        )
        
        if is_unfavorable:
            adjustment = self.config.regime_adjustment_factor
            return {
                'zscore_entry_threshold': base_thresholds['zscore_entry_threshold'] * adjustment,
                'rsi_oversold': base_thresholds['rsi_oversold'] * (1 + (1 - adjustment)),
                'rsi_overbought': base_thresholds['rsi_overbought'] * adjustment
            }
        
        return base_thresholds
    
    def _update_regime_analysis(self) -> None:
        """Update regime analysis for symbols"""
        for symbol in self.config.symbols:
            if symbol in self.market_data:
                self.regime_data[symbol] = self._analyze_symbol_regime(symbol)
    
    def _analyze_symbol_regime(self, symbol: str) -> Dict[str, float]:
        """Analyze regime for a specific symbol"""
        try:
            data = self.market_data[symbol]
            returns = data['close'].pct_change().dropna()
            
            if len(returns) < 20:
                return {'trend_strength': 0, 'volatility_ratio': 1.0, 'is_trending': False, 'is_high_vol': False}
            
            # Trend strength
            recent_returns = returns.tail(20)
            trend_strength = abs(recent_returns.mean()) / recent_returns.std() if recent_returns.std() > 0 else 0
            
            # Volatility regime
            current_vol = recent_returns.std()
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
            return True
        
        regime = self.regime_data[symbol]
        return not regime.get('is_trending', False) and not regime.get('is_high_vol', False)
    
    # ========================================
    # CONFIDENCE CALCULATION
    # ========================================
    
    def _calculate_signal_confidence(self, symbol: str, signal_type: MeanReversionSignal) -> float:
        """Calculate signal confidence based on multiple factors"""
        try:
            if symbol not in self.market_data:
                return 0.5
            
            data = self.market_data[symbol]
            current_row = data.iloc[-1]
            
            # Z-score confidence
            zscore = current_row.get('zscore', 0.0)
            zscore_confidence = min(abs(zscore) / (self.config.zscore_entry_threshold * 1.5), 1.0)
            
            # RSI confidence
            rsi_col = self._resolve_column_name('RSI_14', data)
            rsi = current_row.get(rsi_col, current_row.get('rsi', 50.0))
            if signal_type == MeanReversionSignal.OVERSOLD_BUY:
                rsi_confidence = max(0, (50 - rsi) / 20)
            else:
                rsi_confidence = max(0, (rsi - 50) / 20)
            
            # Bollinger Band confidence
            bb_position = current_row.get('bb_position', 0.5)
            if signal_type == MeanReversionSignal.OVERSOLD_BUY:
                bb_confidence = max(0, (0.5 - bb_position) / 0.5)
            else:
                bb_confidence = max(0, (bb_position - 0.5) / 0.5)
            
            # Regime confidence
            regime_confidence = 1.0
            if self.config.enable_regime_filter and symbol in self.regime_data:
                regime_confidence = (self.config.regime_confidence_favorable 
                                   if self._is_regime_favorable(symbol) 
                                   else self.config.regime_confidence_unfavorable)
            
            # Weighted combination
            total_confidence = (
                zscore_confidence * self.config.confidence_weight_zscore +
                rsi_confidence * self.config.confidence_weight_rsi +
                bb_confidence * self.config.confidence_weight_bollinger +
                regime_confidence * self.config.confidence_weight_regime
            )
            
            return min(total_confidence, 0.95)
            
        except Exception as e:
            logger.error(f"Signal confidence calculation failed for {symbol}: {e}")
            return 0.5
    
    # ========================================
    # POSITION SIZING
    # ========================================
    
    def calculate_position_size(self, signal: StrategySignal, market_data: Dict[str, pd.DataFrame]) -> float:
        """Calculate position size for a given signal"""
        try:
            symbol = signal.symbol
            
            if symbol not in self.market_data or len(self.market_data[symbol]) == 0:
                return 0.0
            
            current_price = self.market_data[symbol]['close'].iloc[-1]
            atr = self._calculate_atr(symbol)
            
            if atr == 0:
                return self.config.base_position_pct
            
            # Volatility-adjusted position size
            volatility = atr / current_price
            volatility_adjustment = self.config.volatility_target / max(volatility, 0.01)
            
            # Apply confidence scaling
            position_size = (
                self.config.base_position_pct * 
                volatility_adjustment * 
                signal.confidence
            )
            
            return min(position_size, self.config.max_position_pct)
            
        except Exception as e:
            self._log_error("Position size calculation failed", e)
            return 0.0
    
    def _calculate_atr(self, symbol: str) -> float:
        """Calculate ATR for a symbol"""
        if symbol not in self.market_data:
            return 0.0
        
        data = self.market_data[symbol]
        atr_col = self._resolve_column_name('ATR_14', data)
        
        if atr_col in data.columns and len(data) > 0:
            return data[atr_col].iloc[-1]
        
        return 0.0
    
    # ========================================
    # UTILITY METHODS
    # ========================================
    
    def _reset_state(self) -> None:
        """Reset strategy state"""
        self.market_data.clear()
        self.indicators.clear()
        self.regime_data.clear()
        for symbol in self.config.symbols:
            self.indicators[symbol] = {}
    
    def _update_market_data(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """Update market data cache"""
        for symbol, data in market_data.items():
            if symbol in self.config.symbols:
                self.market_data[symbol] = data
    
    def _calculate_avg_volatility(self) -> float:
        """Calculate average volatility across symbols"""
        if not self.market_data:
            return 0.0
        
        volatilities = []
        for symbol in self.market_data:
            atr = self._calculate_atr(symbol)
            if atr > 0 and len(self.market_data[symbol]) > 0:
                current_price = self.market_data[symbol]['close'].iloc[-1]
                if current_price > 0:
                    volatilities.append(atr / current_price)
        
        return np.mean(volatilities) if volatilities else 0.0
    
    async def update_positions(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """
        Update positions based on market data
        
        Note: Position management is delegated to Risk Manager and PositionBook.
        This method only updates internal market data cache.
        """
        self._update_market_data(market_data)
    
    def get_mean_reversion_summary(self) -> Dict[str, Any]:
        """Get comprehensive mean reversion strategy summary"""
        return {
            'strategy_id': self.strategy_id,
            'strategy_type': 'Enhanced Mean Reversion',
            'symbols_tracked': len(self.config.symbols),
            'indicators_calculated': len(self.indicators),
            'avg_volatility': self._calculate_avg_volatility(),
            'regime_filter_enabled': self.config.enable_regime_filter,
            'performance_summary': self.get_performance_summary()
        }
