"""
Simplified Mean Reversion Strategy v5.0
=======================================

Expert-reviewed simplification of the mean reversion strategy.

Key Changes from v4.0:
1. SINGLE UNIFIED SCORE: Replaces SMS + 5-factor exhaustion + ERAR
   with additive model using 4 orthogonal features
2. REGIME-CONDITIONED Z-SCORE: Median/MAD with volatility floor
3. THESIS-INVALIDATION EXITS: Time/trend/regime instead of PnL-based
4. STRUCTURE CONFIRMATION: Higher low / lower high before entry

Removed (per expert review):
- Multiplicative SMS (fragile, one weak factor zeros everything)
- ERAR (false precision with garbage short-horizon data)
- RSI, MACD histogram, stochastic, Bollinger %B as separate factors
  (all ~80% correlated, triple-counting same effect)
- PnL-based stop-loss (fights the alpha)

Design Philosophy:
- "If it can't make money without stacked filters, there is no real edge."
- "Mean reversion succeeds because it's simple, fast, and brutally disciplined."

Author: StatArb_Gemini Architecture Compliance
Version: 5.0.0 (Expert Review Simplification)
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import logging

from ...base_strategy_enhanced import EnhancedBaseStrategy
from ...contracts import StrategySignal
from core_engine.type_definitions.strategy import SignalType
from core_engine.config import MeanReversionConfig

# v5.0 Simplified Components
from core_engine.alpha import (
    UnifiedReversalScore,
    RegimeAdjustedZScore,
    SimpleEdgeRatio,
    ThesisInvalidation,
    compute_momentum_exhaustion,
    compute_flow_signal,
    compute_volatility_signal,
    check_structure_confirmation,
    # Legacy (still needed for pending signals)
    Cooldown,
)

logger = logging.getLogger(__name__)


class SimplifiedMeanReversionStrategy(EnhancedBaseStrategy):
    """
    Simplified Mean Reversion Strategy v5.0
    
    Uses 4 orthogonal features instead of 10+ correlated indicators:
    1. STRETCH: Regime-adjusted z-score (distance from fair value)
    2. EXHAUSTION: RSI momentum decay only (not RSI + MACD + Stoch)
    3. FLOW: Volume-based order flow signal
    4. VOLATILITY: ATR compression ratio
    
    Entry: Unified reversal score > threshold + structure confirmation
    Exit: Thesis invalidation (time/trend/regime) NOT PnL-based stops
    """

    # Required indicators (simplified set)
    REQUIRED_INDICATORS = {
        'close': ['close', 'Close'],
        'volume': ['volume', 'Volume'],
        'RSI_14': ['rsi', 'RSI_14'],
        'ATR_14': ['atr', 'ATR_14'],
    }

    # Optional indicators (used if available)
    OPTIONAL_INDICATORS = {
        'adx': ['adx', 'ADX'],
        'high': ['high', 'High'],
        'low': ['low', 'Low'],
    }

    def __init__(self, config: MeanReversionConfig):
        """Initialize simplified mean reversion strategy."""
        super().__init__(config)
        self.config: MeanReversionConfig = config

        # Strategy-specific state
        self.market_data: Dict[str, pd.DataFrame] = {}
        self.regime_data: Dict[str, Dict[str, float]] = {}

        # v5.0 Components
        self.reversal_scorer = UnifiedReversalScore()
        self.zscore_calculator = RegimeAdjustedZScore()
        self.edge_tracker = SimpleEdgeRatio()
        self.thesis_checker = ThesisInvalidation(
            max_hold_bars=getattr(config, 'max_hold_bars', 20),
            trend_acceleration_threshold=getattr(config, 'trend_acceleration_threshold', 1.5),
            regime_shift_threshold=getattr(config, 'regime_shift_threshold', 2.0)
        )

        # Cooldown (still useful for PVSI tracking)
        self.cooldown = Cooldown(
            threshold=getattr(config, 'pvsi_threshold', 2.0),
            baseline_window=100,
            recent_window=20
        )

        # Position tracking for thesis invalidation
        self._position_entry_state: Dict[str, Dict[str, Any]] = {}

        # Configuration (simplified)
        self.unified_threshold = getattr(config, 'unified_threshold', 0.5)
        self.enable_structure_confirmation = getattr(config, 'enable_structure_confirmation', True)
        self.enable_edge_ratio_check = getattr(config, 'enable_edge_ratio_check', False)
        self.min_edge_ratio = getattr(config, 'min_edge_ratio', 1.2)

        logger.info(f"🧠 Simplified Mean Reversion Strategy v5.0 {self.strategy_id} initialized")
        logger.info(f"   Unified threshold={self.unified_threshold}, "
                   f"Structure confirmation={'ON' if self.enable_structure_confirmation else 'OFF'}")

    # ========================================
    # LIFECYCLE HOOKS
    # ========================================

    async def _initialize_strategy_components(self) -> bool:
        """Initialize strategy-specific components."""
        try:
            logger.info(f"🔄 Initializing Simplified MR v5.0 for {self.strategy_id}...")

            if not self.config.symbols:
                logger.error("❌ No symbols configured")
                return False

            self._reset_state()

            logger.info(f"✅ Simplified MR v5.0 initialized for {len(self.config.symbols)} symbols")
            return True

        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}")
            return False

    async def _start_strategy_operations(self) -> bool:
        """Start strategy-specific operations."""
        logger.info(f"🚀 Starting Simplified MR v5.0 operations...")
        return True

    async def _stop_strategy_operations(self) -> None:
        """Stop strategy-specific operations."""
        logger.info(f"🔄 Stopping Simplified MR v5.0 operations...")

    async def _check_strategy_health(self) -> Dict[str, Any]:
        """Check strategy-specific health."""
        return {
            'strategy_healthy': True,
            'version': '5.0.0',
            'symbols_tracked': len(self.config.symbols),
            'edge_ratio': self.edge_tracker.compute()[0] if len(self.edge_tracker.trade_pnls) >= 10 else 'insufficient_data'
        }

    def _get_strategy_config_summary(self) -> Dict[str, Any]:
        """Get strategy-specific configuration summary."""
        return {
            'strategy_type': 'Simplified Mean Reversion v5.0',
            'symbols_count': len(self.config.symbols),
            'unified_threshold': self.unified_threshold,
            'structure_confirmation': self.enable_structure_confirmation,
            'max_hold_bars': self.thesis_checker.max_hold_bars
        }

    def _validate_strategy_config(self) -> bool:
        """Validate strategy-specific configuration."""
        return True

    # ========================================
    # CORE SIGNAL GENERATION
    # ========================================

    async def generate_signals(
        self,
        enriched_data: Dict[str, pd.DataFrame],
        position_details: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> List[StrategySignal]:
        """
        Generate mean reversion signals using simplified v5.0 logic.
        
        Signal flow:
        1. Regime filter (fast rejection)
        2. Compute regime-adjusted z-score
        3. Check thesis invalidation for existing positions
        4. Compute 4 orthogonal features
        5. Compute unified reversal score
        6. Structure confirmation (optional but recommended)
        """
        start_time = datetime.now()
        signals = []

        self._position_details = position_details or {}

        try:
            self._validate_enriched_data(enriched_data)
            self._update_market_data(enriched_data)

            if self.config.enable_regime_filter:
                self._update_regime_analysis()

            for symbol in self.config.symbols:
                data_len = len(self.market_data.get(symbol, []))
                lookback = self.config.lookback_period

                if symbol in self.market_data and data_len > lookback:
                    symbol_signals = await self._generate_symbol_signals(symbol)
                    signals.extend(symbol_signals)

            generation_time = (datetime.now() - start_time).total_seconds()
            self.track_signal_generation_time(generation_time)

            logger.info(f"📊 Simplified MR v5.0: {len(signals)} signals in {generation_time:.3f}s")

            return signals

        except Exception as e:
            self._log_error("Signal generation failed", e)
            return []

    async def _generate_symbol_signals(self, symbol: str) -> List[StrategySignal]:
        """Generate signals for a specific symbol."""
        signals = []

        try:
            if symbol not in self.market_data:
                return signals

            data = self.market_data[symbol]
            data_length = len(data)

            # Historical scanning mode (for backtesting)
            if self.config.scan_all_bars and data_length > self.config.lookback_period:
                start_idx = self.config.lookback_period
                scan_interval = max(1, self.config.scan_interval)

                for idx in range(start_idx, data_length, scan_interval):
                    signal = self._evaluate_signal_conditions(symbol, data, idx)
                    if signal:
                        signals.append(signal)

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
        Evaluate signal conditions using simplified v5.0 logic.
        
        Signal evaluation flow:
        1. Regime filter
        2. Thesis invalidation check (for existing positions)
        3. Regime-adjusted z-score calculation
        4. 4-feature computation (stretch, exhaustion, flow, vol)
        5. Unified reversal score
        6. Structure confirmation
        """
        try:
            # Normalize index
            if idx < 0:
                idx = len(data) + idx

            if idx < self.config.lookback_period or idx >= len(data):
                return None

            current_row = data.iloc[idx]

            # ========================================
            # STEP 1: REGIME FILTER (fast rejection)
            # ========================================
            if self.config.enable_regime_filter and not self._is_regime_favorable(symbol):
                return None

            # ========================================
            # STEP 2: THESIS INVALIDATION (exit check)
            # ========================================
            exit_signal = self._check_thesis_invalidation(symbol, data, idx)
            if exit_signal is not None:
                return exit_signal

            # ========================================
            # STEP 3: REGIME-ADJUSTED Z-SCORE
            # ========================================
            prices = data['close'].iloc[max(0, idx - self.config.lookback_period):idx + 1].values
            
            # Get ATR for regime conditioning
            current_atr = self._get_atr(data, idx)
            baseline_atr = self._get_baseline_atr(data, idx)
            
            zscore, zscore_diag = self.zscore_calculator.compute(
                prices=prices,
                lookback=self.config.lookback_period,
                current_atr=current_atr,
                baseline_atr=baseline_atr
            )

            # Minimum dislocation check
            if abs(zscore) < self.config.dislocation_minimum:
                return None

            is_oversold = zscore < 0
            is_overbought = zscore > 0

            # ========================================
            # STEP 4: COMPUTE 4 ORTHOGONAL FEATURES
            # ========================================
            
            # 4a. STRETCH: Already have regime-adjusted z-score
            stretch = abs(zscore)
            
            # 4b. EXHAUSTION: RSI momentum only
            rsi = self._get_rsi(data, idx)
            rsi_prev = self._get_rsi(data, idx - 1, default=rsi) if idx > 0 else rsi
            exhaustion = compute_momentum_exhaustion(rsi, rsi_prev, is_oversold)
            
            # 4c. FLOW: Volume-based signal
            volume_ratio = self._get_volume_ratio(data, idx)
            price_change_pct = 0.0
            if idx > 0 and 'close' in data.columns:
                prev_close = data['close'].iloc[idx - 1]
                curr_close = data['close'].iloc[idx]
                price_change_pct = (curr_close - prev_close) / prev_close * 100 if prev_close > 0 else 0.0
            flow = compute_flow_signal(volume_ratio, price_change_pct, is_oversold)
            
            # 4d. VOLATILITY: ATR compression ratio
            volatility = compute_volatility_signal(current_atr, baseline_atr)

            # ========================================
            # STEP 5: UNIFIED REVERSAL SCORE
            # ========================================
            regime_label = self._get_regime_label(symbol)
            score, breakdown = self.reversal_scorer.compute(
                stretch=stretch,
                exhaustion=exhaustion,
                flow=flow,
                volatility=volatility,
                regime=regime_label
            )

            if not self.reversal_scorer.should_trade(score, self.unified_threshold):
                return None

            # ========================================
            # STEP 6: STRUCTURE CONFIRMATION (optional)
            # ========================================
            if self.enable_structure_confirmation:
                direction = 'long' if is_oversold else 'short'
                
                if idx >= 6 and 'high' in data.columns and 'low' in data.columns:
                    highs = data['high'].iloc[max(0, idx - 6):idx + 1].values
                    lows = data['low'].iloc[max(0, idx - 6):idx + 1].values
                    closes = data['close'].iloc[max(0, idx - 6):idx + 1].values
                    confirmed, confirm_reason = check_structure_confirmation(
                        highs, lows, closes, direction
                    )
                    
                    if not confirmed:
                        # Structure not confirmed - skip signal
                        return None

            # ========================================
            # STEP 7: EDGE RATIO CHECK (optional)
            # ========================================
            if self.enable_edge_ratio_check:
                if not self.edge_tracker.should_trade(self.min_edge_ratio):
                    return None

            # ========================================
            # BUILD SIGNAL
            # ========================================
            if is_oversold:
                signal_type = SignalType.LONG_ENTRY
            elif is_overbought:
                signal_type = SignalType.SHORT_ENTRY
            else:
                return None

            # Confidence = unified score (directly interpretable)
            confidence = score
            
            # Strength = stretch component (how far from mean)
            strength = breakdown['stretch_contrib'] / 0.35  # Normalize by weight

            timestamp = current_row.get('timestamp', datetime.now()) if isinstance(current_row, pd.Series) else datetime.now()
            entry_price = current_row['close'] if isinstance(current_row, pd.Series) else current_row.get('close', 0)

            # Store entry state for thesis invalidation tracking
            self._position_entry_state[symbol] = {
                'entry_bar': idx,
                'entry_adx': self._get_adx(data, idx),
                'entry_vol_ratio': volatility,
                'direction': 1 if is_oversold else -1
            }

            additional_data = {
                'signal_reason': 'unified_reversal_v5',
                'zscore': zscore,
                'zscore_type': 'regime_adjusted_median_mad',
                'unified_score': score,
                'score_breakdown': breakdown,
                'features': {
                    'stretch': stretch,
                    'exhaustion': exhaustion,
                    'flow': flow,
                    'volatility': volatility
                },
                'entry_price': entry_price,
                'bar_index': idx
            }

            logger.debug(
                f"[{symbol}] Signal: {signal_type.value.upper()} "
                f"zscore={zscore:.3f}, score={score:.3f}, "
                f"features=[S={stretch:.2f}, E={exhaustion:.2f}, F={flow:.2f}, V={volatility:.2f}]"
            )

            return StrategySignal(
                strategy_id=self.strategy_id,
                symbol=symbol,
                signal_type=signal_type,
                strength=strength,
                confidence=confidence,
                target_weight=self.config.base_position_pct,
                quantity_type="PERCENTAGE",
                timestamp=timestamp,
                additional_data=additional_data
            )

        except Exception as e:
            logger.error(f"[{symbol}] Error evaluating bar at index {idx}: {e}")
            return None

    def _check_thesis_invalidation(
        self,
        symbol: str,
        data: pd.DataFrame,
        idx: int
    ) -> Optional[StrategySignal]:
        """
        Check if thesis is invalidated for existing position.
        
        Exit conditions (NOT PnL-based):
        1. TIME: Position held too long
        2. TREND: Trend accelerated instead of reverting
        3. REGIME: Volatility regime shifted
        """
        if not hasattr(self, '_position_details') or not self._position_details:
            return None

        pos_info = self._position_details.get(symbol)
        if not pos_info or pos_info.get('quantity', 0) == 0:
            return None

        # Get entry state
        entry_state = self._position_entry_state.get(symbol)
        if not entry_state:
            return None

        # Calculate bars held
        entry_bar = entry_state.get('entry_bar', idx)
        bars_held = idx - entry_bar

        # Get current vs entry state
        entry_adx = entry_state.get('entry_adx', 25.0)
        current_adx = self._get_adx(data, idx)
        entry_vol_ratio = entry_state.get('entry_vol_ratio', 1.0)
        
        current_atr = self._get_atr(data, idx)
        baseline_atr = self._get_baseline_atr(data, idx)
        current_vol_ratio = current_atr / baseline_atr if baseline_atr > 0 else 1.0

        direction = entry_state.get('direction', 1)

        # Check thesis invalidation
        is_invalidated, reason = self.thesis_checker.is_invalidated(
            bars_held=bars_held,
            entry_adx=entry_adx,
            current_adx=current_adx,
            entry_vol_ratio=entry_vol_ratio,
            current_vol_ratio=current_vol_ratio,
            position_direction=direction
        )

        if is_invalidated:
            quantity = pos_info.get('quantity', 0)
            signal_type = SignalType.LONG_EXIT if quantity > 0 else SignalType.SHORT_EXIT

            current_row = data.iloc[idx]
            timestamp = current_row.get('timestamp', datetime.now())
            current_price = current_row.get('close', 0)

            logger.warning(
                f"⛔ [{symbol}] THESIS INVALIDATED @ bar {idx}: {reason}"
            )

            # Clear entry state
            if symbol in self._position_entry_state:
                del self._position_entry_state[symbol]

            return StrategySignal(
                symbol=symbol,
                signal_type=signal_type,
                confidence=1.0,
                strength=0.0,
                timestamp=timestamp,
                signal_price=current_price,
                target_quantity=abs(quantity),
                quantity_type="ABSOLUTE",
                strategy_id=getattr(self, 'strategy_id', 'simplified_mr_v5'),
                signal_source='THESIS_INVALIDATION',
                signal_reason=reason,
                additional_data={
                    'exit_type': 'thesis_invalidation',
                    'reason': reason,
                    'bars_held': bars_held
                }
            )

        return None

    # ========================================
    # INDICATOR HELPERS
    # ========================================

    def _get_rsi(self, data: pd.DataFrame, idx: int, default: float = 50.0) -> float:
        """Get RSI value at index."""
        for col in ['rsi', 'RSI_14', 'RSI']:
            if col in data.columns:
                return self._get_indicator_value(data, col, idx, default=default)
        return default

    def _get_atr(self, data: pd.DataFrame, idx: int, default: float = 1.0) -> float:
        """Get ATR value at index."""
        for col in ['atr', 'ATR_14', 'ATR']:
            if col in data.columns:
                return self._get_indicator_value(data, col, idx, default=default)
        return default

    def _get_baseline_atr(self, data: pd.DataFrame, idx: int) -> float:
        """Get baseline ATR (20-bar average of ATR)."""
        if idx < 20:
            return self._get_atr(data, idx)
        
        for col in ['atr', 'ATR_14', 'ATR']:
            if col in data.columns:
                atr_window = data[col].iloc[max(0, idx - 20):idx + 1]
                return atr_window.mean() if len(atr_window) > 0 else 1.0
        return 1.0

    def _get_adx(self, data: pd.DataFrame, idx: int, default: float = 25.0) -> float:
        """Get ADX value at index."""
        for col in ['adx', 'ADX']:
            if col in data.columns:
                return self._get_indicator_value(data, col, idx, default=default)
        return default

    def _get_volume_ratio(self, data: pd.DataFrame, idx: int, default: float = 1.0) -> float:
        """Get volume ratio at index."""
        if 'volume_ratio' in data.columns:
            return self._get_indicator_value(data, 'volume_ratio', idx, default=default)
        
        # Calculate from volume
        if 'volume' in data.columns and idx >= 20:
            vol = data['volume'].iloc[idx]
            vol_ma = data['volume'].iloc[max(0, idx - 20):idx].mean()
            return vol / vol_ma if vol_ma > 0 else default
        
        return default

    def _get_indicator_value(
        self,
        data: pd.DataFrame,
        column: str,
        idx: int,
        default: float = 0.0
    ) -> float:
        """Get indicator value at index with robust NaN handling."""
        if column not in data.columns:
            return default

        series = data[column].ffill()

        if idx < 0:
            idx = len(series) + idx

        if idx < 0 or idx >= len(series):
            return default

        value = series.iloc[idx]

        if pd.isna(value):
            valid_values = series.dropna()
            if len(valid_values) > 0:
                return valid_values.iloc[-1]
            return default

        return value

    # ========================================
    # REGIME ANALYSIS (simplified)
    # ========================================

    def _update_regime_analysis(self) -> None:
        """Update regime analysis for symbols."""
        for symbol in self.config.symbols:
            if symbol in self.market_data:
                self.regime_data[symbol] = self._analyze_symbol_regime(symbol)

    def _analyze_symbol_regime(self, symbol: str) -> Dict[str, float]:
        """Analyze regime for a specific symbol."""
        try:
            data = self.market_data[symbol]
            returns = data['close'].pct_change().dropna()

            if len(returns) < 20:
                return {'trend_strength': 0, 'volatility_ratio': 1.0, 'is_trending': False, 'is_high_vol': False}

            recent_returns = returns.tail(20)
            trend_strength = abs(recent_returns.mean()) / recent_returns.std() if recent_returns.std() > 0 else 0

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
        """Check if current regime is favorable for mean reversion."""
        if symbol not in self.regime_data:
            return True

        regime = self.regime_data[symbol]
        return not regime.get('is_trending', False) and not regime.get('is_high_vol', False)

    def _get_regime_label(self, symbol: str) -> str:
        """Get regime label for scoring."""
        if symbol not in self.regime_data:
            return 'normal'

        regime = self.regime_data[symbol]
        vol_ratio = regime.get('volatility_ratio', 1.0)
        is_trending = regime.get('is_trending', False)
        is_high_vol = regime.get('is_high_vol', False)

        if is_trending and is_high_vol:
            return 'crisis'
        elif is_high_vol or vol_ratio > 1.5:
            return 'high_vol'
        elif vol_ratio < 0.7:
            return 'low_vol'
        else:
            return 'normal'

    # ========================================
    # UTILITY METHODS
    # ========================================

    def _validate_enriched_data(self, enriched_data: Dict[str, pd.DataFrame]) -> None:
        """Validate that data has minimum required columns."""
        for symbol, data in enriched_data.items():
            if data.empty:
                raise ValueError(f"{symbol} has empty DataFrame")

            # Minimum: need close and volume
            if 'close' not in data.columns and 'Close' not in data.columns:
                raise ValueError(f"{symbol} missing 'close' column")

    def _reset_state(self) -> None:
        """Reset strategy state."""
        self.market_data.clear()
        self.regime_data.clear()
        self._position_entry_state.clear()

    def _update_market_data(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """Update market data cache."""
        for symbol, data in market_data.items():
            if symbol in self.config.symbols:
                self.market_data[symbol] = data

    async def update_positions(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """Update positions based on market data."""
        self._update_market_data(market_data)

    def update_edge_tracker(self, pnl: float):
        """Update edge tracker with trade result."""
        self.edge_tracker.update(pnl)

    def get_strategy_summary(self) -> Dict[str, Any]:
        """Get strategy summary."""
        edge_ratio, edge_diag = self.edge_tracker.compute()
        return {
            'strategy_id': self.strategy_id,
            'strategy_type': 'Simplified Mean Reversion v5.0',
            'version': '5.0.0',
            'symbols_tracked': len(self.config.symbols),
            'unified_threshold': self.unified_threshold,
            'structure_confirmation': self.enable_structure_confirmation,
            'edge_ratio': edge_ratio,
            'edge_diagnostics': edge_diag,
            'performance_summary': self.get_performance_summary()
        }
