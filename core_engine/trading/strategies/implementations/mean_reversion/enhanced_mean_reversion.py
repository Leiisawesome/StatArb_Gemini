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

Alpha Logic Foundation (v4.0):
"Mean reversion works when the directional move shows exhaustion. The best trades
are NOT at price extremes per se, but at price extremes where buying/selling
pressure is weakening, volume is declining, and candle structure shows rejection."

v4.0 Enhancements (Professional Quant Optimizations):
- HALF-LIFE ESTIMATION: Ornstein-Uhlenbeck process for optimal entry timing
- HURST EXPONENT: Statistical validation of mean-reversion regime (H < 0.5)
- EWMA Z-SCORE: Exponentially weighted std for regime-responsive dislocation
- VOLATILITY-ADJUSTED THRESHOLDS: Dynamic scaling based on vol regime
- MULTI-TIMEFRAME CONFIRMATION: Higher TF trend filter

Academic Foundations:
- Kyle (1985) - Market microstructure and price impact
- Avellaneda & Lee (2010) - Statistical arbitrage half-life estimation
- Cartea, Jaimungal & Penalva (2015) - Order flow and market making
- Lo & MacKinlay (1990) - Contrarian investment strategies
- Hurst (1951) - Long-term storage capacity of reservoirs (Hurst exponent)
- Uhlenbeck & Ornstein (1930) - Theory of Brownian motion

Author: StatArb_Gemini Architecture Compliance
Version: 4.0.0 (Professional Quant Alpha Optimizations)
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import logging

from ...base_strategy_enhanced import EnhancedBaseStrategy
from ...strategy_engine import StrategySignal, SignalType
from core_engine.config import MeanReversionConfig

# ADS v3.0 Components - Critical fixes per alpha_design_philosophy.mdc
from core_engine.alpha import (
    SignalMaturityScore,
    ERAR,
    Cooldown,
    PendingSignalQueue,
    compute_exhaustion,
    compute_reversal_probability,
    compute_vol_compression,
    estimate_expected_pnl,
    estimate_cvar_95,
)

logger = logging.getLogger(__name__)

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

        # ============================================
        # ADS v3.0 COMPONENTS (Critical Compliance)
        # ============================================
        # §1: Pending signal queue with SMS maturation
        self.pending_signals = PendingSignalQueue(
            max_pending=getattr(config, 'sms_max_pending', 50)
        )

        # §8: Cooldown (PVSI) tracker
        self.cooldown = Cooldown(
            threshold=getattr(config, 'pvsi_threshold', 2.0),
            baseline_window=100,
            recent_window=20
        )

        # ADS configuration
        self.ads_config = {
            'sms_threshold': getattr(config, 'sms_threshold', 0.5),
            'erar_gamma': getattr(config, 'erar_gamma', 0.5),
            'enable_ads_gates': getattr(config, 'enable_ads_gates', True),
        }

        logger.info(f"🧠 Enhanced Mean Reversion Strategy {self.strategy_id} initialized")
        logger.info(f"   ADS v3.0: SMS threshold={self.ads_config['sms_threshold']}, "
                   f"ERAR gamma={self.ads_config['erar_gamma']}")

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

    async def generate_signals(self, enriched_data: Dict[str, pd.DataFrame],
                               position_details: Optional[Dict[str, Dict[str, Any]]] = None) -> List[StrategySignal]:
        """
        Generate mean reversion signals from ENRICHED data (Rule 3 Phase 4)

        Args:
            enriched_data: Dict[symbol, enriched DataFrame with OHLCV + indicators]
            position_details: Dict mapping symbol to rich position info:
                {
                    'quantity': float,        # Current position size
                    'entry_price': float,     # Average entry price
                    'current_price': float,   # Current market price
                    'unrealized_pnl': float,  # Unrealized P&L in dollars
                    'pnl_pct': float,         # Unrealized P&L as percentage
                    'is_profitable': bool     # True if position is profitable
                }

        Returns:
            List[StrategySignal]: Generated mean reversion signals
        """
        start_time = datetime.now()
        signals = []

        # Store position details for price-aware decisions
        self._position_details = position_details or {}

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
            current_ts = None
            try:
                current_ts = current_row.get("timestamp", None) if hasattr(current_row, "get") else None
            except Exception:
                current_ts = None

            # Trace only a tight window to keep log volume low (debug mode)
            trace = False

            # Get core indicator values
            # Calculate zscore using strategy's lookback_period (more accurate than pre-calculated)
            zscore = self._calculate_strategy_zscore(data, idx)

            # Apply regime filter first (fast exit)
            if self.config.enable_regime_filter and not self._is_regime_favorable(symbol):
                return None

            # ========================================
            # PROACTIVE STOP-LOSS CHECK (CRITICAL)
            # ========================================
            # Check EVERY bar if we have a position that needs stop-loss exit.
            # This runs BEFORE z-score signal logic to ensure stop-loss fires
            # even when z-score would generate a BUY (averaging down) signal.
            stop_loss_signal = self._check_proactive_stop_loss(symbol, data, idx)
            if stop_loss_signal is not None:
                return stop_loss_signal

            # ========================================
            # ADS v3.0 §1: SIGNAL MATURITY SCORE (SMS)
            # ========================================
            # Multiplicative formula per alpha_design_philosophy.mdc

            # Determine signal direction from z-score first
            if abs(zscore) < self.config.dislocation_minimum:
                return None  # Not dislocated enough

            is_oversold = zscore < -self.config.dislocation_minimum
            is_overbought = zscore > self.config.dislocation_minimum

            # Get indicators for SMS calculation (using DRY helpers)
            rsi = self._get_rsi(data, idx)
            rsi_prev = self._get_rsi(data, idx - 1, default=rsi)
            volume_ratio = self._get_volume_ratio(data, idx)
            macd_hist = self._get_macd_histogram(data, idx)
            macd_hist_prev = self._get_macd_histogram(data, idx - 1)
            bb_position = self._get_indicator_value(data, 'bb_position', idx, default=0.5)

            # Calculate volatility compression
            if 'close' in data.columns and idx >= 20:
                prices = data['close'].iloc[max(0, idx-20):idx+1]
                short_vol = prices.tail(5).pct_change().std() if len(prices) >= 5 else 0.02
                long_vol = prices.pct_change().std() if len(prices) >= 10 else 0.02
                vol_compression = compute_vol_compression(short_vol, long_vol)
            else:
                vol_compression = 1.0

            # Compute SMS components
            exhaustion = compute_exhaustion(
                zscore=zscore,
                rsi=rsi,
                volume_ratio=volume_ratio,
                macd_histogram=macd_hist,
                macd_histogram_prev=macd_hist_prev,
                is_oversold=is_oversold
            )

            reversal_prob = compute_reversal_probability(
                zscore=zscore,
                rsi=rsi,
                bb_position=bb_position,
                is_oversold=is_oversold
            )

            # Order flow imbalance shift (use volume ratio as proxy)
            ofi_shift = (volume_ratio - 1.0) * -0.5 if is_oversold else (volume_ratio - 1.0) * 0.5
            ofi_shift = np.clip(ofi_shift, -1.0, 1.0)

            # Get current regime
            regime_label = self._get_regime_label(symbol)

            # Create multiplicative SMS
            sms = SignalMaturityScore(
                exhaustion=exhaustion,
                reversal_prob=reversal_prob,
                ofi_shift=ofi_shift,
                vol_compression=vol_compression,
                pending_bars=0,  # Fresh signal
                decay_rate=0.05,
                max_pending=getattr(self.config, 'sms_max_pending', 50)
            )

            # Compute SMS score
            sms_score = sms.compute(regime_label)
            sms_threshold = self.ads_config.get('sms_threshold', 0.5)

            # DEBUG: Log SMS evaluation
            if not hasattr(self, '_eval_log_count'):
                self._eval_log_count = 0
            if self._eval_log_count < 20:
                self._eval_log_count += 1
                logger.info(f"[{symbol}] ADS SMS #{self._eval_log_count}: zscore={zscore:.3f}, "
                           f"SMS={sms_score:.3f} (E={exhaustion:.3f}, P_rev={reversal_prob:.3f}, "
                           f"VC={vol_compression:.3f}), threshold={sms_threshold}")

            # Check SMS threshold
            if sms_score < sms_threshold:
                return None  # Signal not mature enough

            # ========================================
            # ADS v3.0 §3: ERAR GATE (Risk-Adjusted Return)
            # ========================================
            if self.ads_config.get('enable_ads_gates', True):
                # Estimate expected PnL (using DRY helpers)
                atr = self._get_atr(data, idx)
                price = data['close'].iloc[idx] if 'close' in data.columns else 100.0
                half_life = self._calculate_half_life(data['close'].iloc[max(0, idx-50):idx+1]) if 'close' in data.columns else 10.0

                expected_pnl = estimate_expected_pnl(
                    zscore=zscore,
                    atr=atr,
                    price=price,
                    half_life=half_life if half_life != float('inf') else 20.0,
                    holding_bars=10
                )

                # Estimate CVaR95
                volatility = atr / price if price > 0 else 0.02
                cvar_95 = estimate_cvar_95(volatility=volatility, holding_days=0.5)

                # Create ERAR
                erar = ERAR(
                    expected_pnl=expected_pnl,
                    cvar_95=cvar_95,
                    skewness=0.0,  # Conservative assumption
                    spread_bps=getattr(self.config, 'spread_bps', 2.0),
                    participation=0.01,
                    volatility=volatility,
                    adverse_prob=0.1,
                    kyle_lambda=0.0001,
                    holding_days=0.5,
                    alt_return_bps=0.5,
                    tail_lambda=self.ads_config.get('erar_gamma', 0.5)
                )

                erar_score = erar.compute()
                erar_gamma = self.ads_config.get('erar_gamma', 0.5)

                if not erar.should_trade(gamma=erar_gamma):
                    if self._eval_log_count <= 30:
                        logger.debug(f"[{symbol}] ERAR gate blocked: ERAR={erar_score:.3f} < gamma={erar_gamma}")
                    return None  # Doesn't meet risk-adjusted return threshold

                if self._eval_log_count <= 20:
                    logger.info(f"[{symbol}] ERAR passed: {erar_score:.3f} >= {erar_gamma}")

            # ========================================
            # LEGACY: Calculate exhaustion score for confidence
            # ========================================
            score, score_breakdown = self._calculate_exhaustion_score(data, idx, zscore)

            # Set confidence based on SMS score (continuous mapping)
            # Map SMS (0.0-1.0) to confidence (0.50-0.95) with floor at min threshold
            self.ads_config.get('sms_threshold', 0.5)
            confidence = max(0.50, min(0.95, 0.50 + sms_score * 0.45))

            # Determine signal reason for logging
            if sms_score >= 0.7:
                signal_reason = 'ads_sms_strong'
            elif sms_score >= 0.5:
                signal_reason = 'ads_sms_moderate'
            else:
                signal_reason = 'ads_sms_marginal'

            # Determine signal type (using explicit semantics per Rule 2)
            if is_oversold:
                signal_type = SignalType.LONG_ENTRY  # Price low → go long
            elif is_overbought:
                signal_type = SignalType.SHORT_ENTRY  # Price high → go short (or close long)
            else:
                return None

            # ========================================
            # MOMENTUM-AWARE EXIT LOGIC (NEW)
            # ========================================
            # For EXIT signals, check if momentum is exhausted before allowing exit
            # This prevents exiting too early in strong trends
            # SHORT_ENTRY with long position → close long (handled by backtest engine)
            # LONG_ENTRY with short position → close short (handled by backtest engine)
            is_exit_signal = (
                (signal_type == SignalType.SHORT_ENTRY) or  # Will close long if has one
                (signal_type == SignalType.LONG_ENTRY and hasattr(self, '_position_details') and
                 self._position_details.get(symbol, {}).get('quantity', 0) < 0)  # Will close short
            )

            if is_exit_signal and getattr(self.config, 'enable_momentum_exit', True):
                # Get momentum indicators (using DRY helpers)
                exit_rsi = self._get_rsi(data, idx)
                exit_adx = self._get_adx(data, idx)
                exit_volume_ratio = self._get_volume_ratio(data, idx)

                # Get thresholds from config
                adx_threshold = getattr(self.config, 'momentum_adx_threshold', 20.0)
                rsi_overbought = getattr(self.config, 'momentum_rsi_overbought', 70.0)
                vol_ratio_threshold = getattr(self.config, 'momentum_volume_ratio', 0.7)
                extended_zscore = getattr(self.config, 'momentum_extended_zscore', 3.0)

                # Check if we should allow exit (only handling long exits - strategy doesn't short)
                momentum_exhausted = False
                hold_reason = None
                exit_reason = None

                # Get previous RSI to check if momentum is reversing
                exit_rsi_prev = self._get_rsi(data, idx - 1, default=exit_rsi) if idx > 0 else exit_rsi
                rsi_declining = exit_rsi < exit_rsi_prev - 1.0

                # Always exit if z-score is extremely extended
                if abs(zscore) >= extended_zscore:
                    momentum_exhausted = True
                    exit_reason = f"extended_zscore ({zscore:.2f} >= {extended_zscore})"

                # Exit if RSI shows exhaustion AND is declining
                elif exit_rsi >= rsi_overbought and rsi_declining:
                    momentum_exhausted = True
                    exit_reason = f"rsi_overbought_declining ({exit_rsi:.1f} >= {rsi_overbought}, prev={exit_rsi_prev:.1f})"
                elif exit_rsi >= rsi_overbought:
                    # RSI overbought but still rising - HOLD
                    hold_reason = f"rsi_overbought_but_rising ({exit_rsi:.1f}, prev={exit_rsi_prev:.1f}) - wait for reversal"

                # Exit if trend is weak (ADX low)
                elif exit_adx < adx_threshold:
                    momentum_exhausted = True
                    exit_reason = f"weak_trend (ADX {exit_adx:.1f} < {adx_threshold})"

                # Exit if volume is fading
                elif exit_volume_ratio < vol_ratio_threshold:
                    momentum_exhausted = True
                    exit_reason = f"volume_fading (ratio {exit_volume_ratio:.2f} < {vol_ratio_threshold})"

                # Momentum still strong - HOLD for extended move
                else:
                    hold_reason = f"momentum_strong (ADX={exit_adx:.1f}, RSI={exit_rsi:.1f}, vol_ratio={exit_volume_ratio:.2f})"

                # Log the decision
                if momentum_exhausted:
                    logger.debug(f"[{symbol}] MOMENTUM EXIT ALLOWED: {exit_reason}")
                else:
                    logger.debug(f"[{symbol}] MOMENTUM HOLD: {hold_reason}")
                    return None  # Don't exit yet, momentum still strong

            # ========================================
            # MOMENTUM-AWARE ENTRY LOGIC (LONG_ENTRY FILTER)
            # ========================================
            # For LONG_ENTRY (new long positions), check if downward momentum is exhausted
            # This prevents buying into "falling knife" scenarios
            is_entry_signal = (
                signal_type == SignalType.LONG_ENTRY and
                (not hasattr(self, '_position_details') or
                 self._position_details.get(symbol, {}).get('quantity', 0) <= 0)
            )

            if is_entry_signal and getattr(self.config, 'enable_momentum_entry', True):
                # Get momentum indicators (using DRY helpers)
                entry_rsi = self._get_rsi(data, idx)
                entry_adx = self._get_adx(data, idx)
                entry_volume_ratio = self._get_volume_ratio(data, idx)

                # Get previous RSI to check if momentum is reversing
                entry_rsi_prev = self._get_rsi(data, idx - 1, default=entry_rsi) if idx > 0 else entry_rsi
                rsi_rising = entry_rsi > entry_rsi_prev + 1.0
                rsi_still_falling = entry_rsi < entry_rsi_prev - 1.0

                # Thresholds
                rsi_oversold = getattr(self.config, 'rsi_oversold', 30.0)
                adx_threshold = getattr(self.config, 'momentum_adx_threshold', 25.0)
                extended_zscore_entry = getattr(self.config, 'extended_zscore_entry_threshold', -3.0)

                momentum_reversing = False
                entry_reason = None
                hold_entry_reason = None

                # Always enter if z-score is extremely extended (very oversold)
                if zscore <= extended_zscore_entry:
                    momentum_reversing = True
                    entry_reason = f"extended_zscore ({zscore:.2f} <= {extended_zscore_entry})"

                # Enter if RSI shows exhaustion AND is rising (momentum reversing)
                elif entry_rsi <= rsi_oversold and rsi_rising:
                    momentum_reversing = True
                    entry_reason = f"rsi_oversold_rising ({entry_rsi:.1f} <= {rsi_oversold}, prev={entry_rsi_prev:.1f})"
                elif entry_rsi <= rsi_oversold and rsi_still_falling:
                    # RSI oversold but still falling - WAIT for bounce
                    hold_entry_reason = f"rsi_oversold_but_falling ({entry_rsi:.1f}, prev={entry_rsi_prev:.1f}) - wait for reversal"

                # Enter if trend is weak (low ADX = mean reversion more likely)
                elif entry_adx < adx_threshold:
                    momentum_reversing = True
                    entry_reason = f"weak_trend (ADX {entry_adx:.1f} < {adx_threshold})"

                # For BUY entries: High volume = selling climax (capitulation), OK to enter
                elif entry_volume_ratio > 1.5:  # Volume spike = potential capitulation/reversal
                    momentum_reversing = True
                    entry_reason = f"volume_spike (ratio {entry_volume_ratio:.2f} > 1.5) - potential capitulation"

                # Strong downward momentum - WAIT for exhaustion
                else:
                    hold_entry_reason = f"momentum_strong (ADX={entry_adx:.1f}, RSI={entry_rsi:.1f}, vol_ratio={entry_volume_ratio:.2f})"

                # Log the decision
                if momentum_reversing:
                    logger.debug(f"[{symbol}] MOMENTUM ENTRY ALLOWED: {entry_reason}")
                else:
                    logger.debug(f"[{symbol}] MOMENTUM ENTRY WAIT: {hold_entry_reason}")
                    return None  # Don't enter yet, downward momentum still strong

            # ========================================
            # PRICE-AWARE EXIT LOGIC
            # ========================================
            # For SHORT_ENTRY signals (overbought), check position context
            # SHORT_ENTRY with existing long → closes long (via backtest engine)
            has_details = hasattr(self, '_position_details')
            details_content = self._position_details if has_details else {}

            if signal_type == SignalType.SHORT_ENTRY and has_details and details_content:
                pos_info = details_content.get(symbol)

                if pos_info and pos_info.get('quantity', 0) > 0:
                    entry_price_pos = pos_info.get('entry_price', 0)
                    current_price = pos_info.get('current_price', 0)
                    pos_info.get('unrealized_pnl', 0)
                    pnl_pct = pos_info.get('pnl_pct', 0)

                    # Get price-aware thresholds from config (with defaults)
                    stop_loss_pct = getattr(self.config, 'stop_loss_pct', -5.0)  # -5% default
                    take_profit_pct = getattr(self.config, 'take_profit_pct', 10.0)  # +10% default
                    min_profit_to_exit = getattr(self.config, 'min_profit_to_exit', -2.0)  # Allow -2% loss max

                    # Log position context
                    logger.debug(f"[{symbol}] Price-aware: entry=${entry_price_pos:.2f}, current=${current_price:.2f}, "
                                f"pnl={pnl_pct:+.2f}%, stop={stop_loss_pct}%")

                    # RULE 1: Take profit if exceeds threshold (always exit)
                    if pnl_pct >= take_profit_pct:
                        logger.info(f"[{symbol}] ✅ TAKE PROFIT: pnl={pnl_pct:+.2f}% >= {take_profit_pct}%")
                        # Boost confidence for profitable exits
                        confidence = min(confidence * 1.2, 1.0)

                    # RULE 2: Stop loss if exceeds threshold (always exit)
                    elif pnl_pct <= stop_loss_pct:
                        logger.info(f"[{symbol}] ⚠️ STOP LOSS: pnl={pnl_pct:+.2f}% <= {stop_loss_pct}%")
                        # Still exit but log it

                    # RULE 3: Don't sell at significant loss just because z-score says overbought
                    elif pnl_pct < min_profit_to_exit:
                        logger.info(f"[{symbol}] ❌ SKIPPING SELL: pnl={pnl_pct:+.2f}% < {min_profit_to_exit}%, "
                                   f"waiting for better price (entry=${entry_price_pos:.2f})")
                        return None  # Skip this sell signal

                    # RULE 4: Small loss or breakeven - allow exit if z-score strong enough
                    else:
                        # Allow exit if z-score is very strong (>2.5) even at small loss
                        if zscore > self.config.dislocation_strong:
                            logger.info(f"[{symbol}] ✅ STRONG Z-SCORE EXIT: z={zscore:.2f} > {self.config.dislocation_strong}")
                        else:
                            logger.info(f"[{symbol}] ⚠️ MARGINAL EXIT: pnl={pnl_pct:+.2f}%, z={zscore:.2f}")

            # Confidence threshold check
            if confidence <= 0.6:
                return None

            # Calculate composite signal strength (0-1 scale)
            # Combines multiple quality factors for more granular strength
            exhaustion_component = min(score / 100.0, 1.0) * 0.40  # 40% weight
            sms_component = sms_score * 0.35  # 35% weight - signal maturity
            zscore_component = min(abs(zscore) / 3.0, 1.0) * 0.25  # 25% weight - z-score magnitude (cap at 3)

            strength = min(exhaustion_component + sms_component + zscore_component, 1.0)

            # Log signal creation details
            logger.debug(f"[{symbol}] Signal: {signal_type.value.upper()} zscore={zscore:.3f}, score={score:.1f}, "
                        f"strength={strength:.2f} (exh={exhaustion_component:.2f}+sms={sms_component:.2f}+z={zscore_component:.2f}), confidence={confidence:.2f}")

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
                strength=strength,  # Composite strength from exhaustion + SMS + z-score
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

        # 2a. RSI Momentum Exhaustion (using DRY helpers)
        exh_rsi = self._get_rsi(data, idx)
        exh_rsi_prev = self._get_rsi(data, idx - 1, default=50.0)
        rsi_momentum = exh_rsi - exh_rsi_prev

        if is_oversold and rsi_momentum > 0:
            # Oversold but RSI rising = bullish exhaustion
            exhaustion_score += 20
        elif not is_oversold and rsi_momentum < 0:
            # Overbought but RSI falling = bearish exhaustion
            exhaustion_score += 20

        # 2b. Volume Exhaustion (using DRY helpers)
        exh_volume_ratio = self._get_volume_ratio(data, idx)

        if exh_volume_ratio < self.config.volume_exhaustion_threshold and abs_zscore > self.config.dislocation_moderate:
            # Low volume extremity = likely noise, will revert
            exhaustion_score += 15
        elif exh_volume_ratio > self.config.volume_conviction_threshold and abs_zscore > self.config.dislocation_strong:
            # High volume breakout = information, don't fade
            exhaustion_score -= 25

        # 2c. MACD Histogram Exhaustion (using DRY helpers)
        exh_macd = self._get_macd_histogram(data, idx)
        exh_macd_prev = self._get_macd_histogram(data, idx - 1)

        if is_oversold and exh_macd > exh_macd_prev:
            # Histogram turning up in oversold
            exhaustion_score += 15
        elif not is_oversold and exh_macd < exh_macd_prev:
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

        # 4a. Trend Strength Penalty (using DRY helpers)
        exh_adx = self._get_adx(data, idx, default=20.0)

        if exh_adx > self.config.adx_strong_trend:
            regime_score -= 40  # Strong trend, mean reversion fails
        elif exh_adx > self.config.adx_moderate_trend:
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

        # 5c. RSI Extreme Confirmation (using already-fetched value)
        if is_oversold and exh_rsi < 30:
            confluence_score += 10
        elif not is_oversold and exh_rsi > 70:
            confluence_score += 10

        breakdown['confluence'] = np.clip(confluence_score, 0, 100)

        # ============================================
        # FACTOR 6: ALPHA QUALITY (v4.0 Quant Methods)
        # ============================================
        # Only calculate if enabled (adds ~1ms per evaluation)
        alpha_quality_score = 50.0  # Neutral default
        if getattr(self.config, 'enable_alpha_quality_scoring', True):
            alpha_quality_score, alpha_diagnostics = self._calculate_alpha_quality_score(
                data, idx, zscore
            )
            breakdown['alpha_quality'] = alpha_quality_score
            breakdown['alpha_diagnostics'] = alpha_diagnostics
        else:
            breakdown['alpha_quality'] = 50.0
            breakdown['alpha_diagnostics'] = {}

        # ============================================
        # WEIGHTED TOTAL SCORE (v4.0 with Alpha Quality)
        # ============================================
        # Get alpha quality weight (default 0.10 = 10%)
        weight_alpha = getattr(self.config, 'weight_alpha_quality', 0.10)

        # Scale down other weights proportionally if alpha quality is enabled
        scale_factor = 1.0 - weight_alpha if weight_alpha > 0 else 1.0

        total_score = (
            breakdown['dislocation'] * self.config.weight_dislocation * scale_factor +
            breakdown['exhaustion'] * self.config.weight_exhaustion * scale_factor +
            breakdown['candle_structure'] * self.config.weight_candle_structure * scale_factor +
            breakdown['regime_penalty'] * self.config.weight_regime_penalty * scale_factor +
            breakdown['confluence'] * self.config.weight_confluence * scale_factor +
            breakdown['alpha_quality'] * weight_alpha
        )  # Factors are already 0-100, weights sum to ~1.0, so result is 0-100

        # Normalize (weights should sum to 1.0)
        weight_sum = (
            self.config.weight_dislocation * scale_factor +
            self.config.weight_exhaustion * scale_factor +
            self.config.weight_candle_structure * scale_factor +
            self.config.weight_regime_penalty * scale_factor +
            self.config.weight_confluence * scale_factor +
            weight_alpha
        )
        if weight_sum > 0:
            total_score = total_score / weight_sum

        return np.clip(total_score, 0, 100), breakdown

    # ========================================
    # INDICATOR HELPERS
    # ========================================

    def _calculate_strategy_zscore(self, data: pd.DataFrame, idx: int) -> float:
        """
        Calculate z-score using strategy's configured lookback_period

        This ensures zscore is calculated with the SAME lookback the strategy
        uses for its trading decisions, rather than relying on pre-calculated
        features which may use a different lookback.

        Args:
            data: DataFrame with at least 'close' column
            idx: Index to calculate zscore at

        Returns:
            Z-score value (standard deviations from mean)
        """
        lookback = self.config.lookback_period

        # Need sufficient history
        if idx < lookback:
            return 0.0

        if 'close' not in data.columns:
            return self._get_indicator_value(data, 'zscore', idx, default=0.0)

        # Get lookback window of prices
        prices = data['close'].iloc[max(0, idx - lookback + 1):idx + 1].values

        if len(prices) < lookback // 2:  # Need at least half the lookback
            return 0.0

        mean_price = float(np.mean(prices))
        std_price = float(np.std(prices))

        if std_price < 0.001:  # Avoid division by zero
            return 0.0

        current_price = float(data['close'].iloc[idx])
        zscore = (current_price - mean_price) / std_price

        return zscore

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

    # ========================================
    # INDICATOR HELPERS (DRY - Single Source)
    # ========================================

    def _get_rsi(self, data: pd.DataFrame, idx: int, default: float = 50.0) -> float:
        """
        Get RSI value at index with column name resolution.

        Handles both 'RSI_14' and 'rsi' column naming conventions.
        """
        rsi_col = self._resolve_column_name('RSI_14', data)
        return self._get_indicator_value(data, rsi_col, idx, default=default)

    def _get_volume_ratio(self, data: pd.DataFrame, idx: int, default: float = 1.0) -> float:
        """
        Get volume ratio at index with fallback calculation.

        Tries 'volume_ratio' column first, then calculates from volume/volume_sma.
        """
        # Try pre-calculated column first
        if 'volume_ratio' in data.columns:
            value = self._get_indicator_value(data, 'volume_ratio', idx, default=None)
            if value is not None and not pd.isna(value):
                return value

        # Fallback: calculate from volume columns
        volume = self._get_indicator_value(data, 'volume', idx, default=0)
        volume_ma = self._get_indicator_value(data, 'volume_sma', idx, default=volume)

        if volume_ma > 0:
            return volume / volume_ma
        return default

    def _get_macd_histogram(self, data: pd.DataFrame, idx: int, default: float = 0.0) -> float:
        """
        Get MACD histogram value at index with column name resolution.

        Handles both 'MACD_histogram' and 'macd_histogram' conventions.
        """
        macd_col = self._resolve_column_name('MACD_histogram', data)
        return self._get_indicator_value(data, macd_col, idx, default=default)

    def _get_adx(self, data: pd.DataFrame, idx: int, default: float = 25.0) -> float:
        """
        Get ADX value at index with column name resolution.

        Handles both 'ADX' and 'adx' column naming conventions.
        """
        adx_col = self._resolve_column_name('ADX', data)
        return self._get_indicator_value(data, adx_col, idx, default=default)

    def _get_atr(self, data: pd.DataFrame, idx: int, default: float = 1.0) -> float:
        """
        Get ATR value at index with column name resolution.

        Handles both 'ATR_14' and 'atr' column naming conventions.
        """
        atr_col = self._resolve_column_name('ATR_14', data)
        return self._get_indicator_value(data, atr_col, idx, default=default)

    # ========================================
    # v4.0 PROFESSIONAL QUANT ALPHA ENHANCEMENTS
    # ========================================

    def _calculate_half_life(self, prices: pd.Series, max_lag: int = 1) -> float:
        """
        Calculate mean-reversion half-life using Ornstein-Uhlenbeck process.

        The half-life tells us how long (in bars) it takes for price to revert
        halfway back to its mean. Shorter half-life = faster mean reversion.

        Based on: Avellaneda & Lee (2010) "Statistical Arbitrage in the US Equities Market"

        Method:
        1. Compute log prices
        2. Run AR(1) regression: Δy_t = α + β*y_{t-1} + ε_t
        3. Half-life = -ln(2) / ln(1 + β) ≈ -ln(2) / β for small β

        Args:
            prices: Price series
            max_lag: Maximum lag for AR regression (default 1)

        Returns:
            Half-life in bars (inf if not mean-reverting)
        """
        try:
            if len(prices) < 30:
                return float('inf')

            # Use log prices for stationarity
            log_prices = np.log(prices.dropna())

            if len(log_prices) < 30:
                return float('inf')

            # Compute lagged series
            y = log_prices.values
            y_lag = np.roll(y, 1)[1:]
            y_diff = np.diff(y)

            # Ensure same length
            y_lag = y_lag[:len(y_diff)]

            # AR(1) regression: Δy = α + β*y_{t-1}
            # Using numpy for speed
            X = np.column_stack([np.ones(len(y_lag)), y_lag])
            try:
                beta = np.linalg.lstsq(X, y_diff, rcond=None)[0]
                slope = beta[1]  # The mean-reversion speed
            except np.linalg.LinAlgError:
                return float('inf')

            # Half-life calculation
            if slope >= 0:
                # Not mean-reverting (random walk or trending)
                return float('inf')

            half_life = -np.log(2) / slope

            # Sanity check: half-life should be positive and reasonable
            if half_life <= 0 or half_life > len(prices):
                return float('inf')

            return half_life

        except Exception as e:
            logger.debug(f"Half-life calculation failed: {e}")
            return float('inf')

    def _calculate_hurst_exponent(self, prices: pd.Series, max_lag: int = 20) -> float:
        """
        Calculate Hurst exponent to validate mean-reversion regime.

        Hurst Exponent Interpretation:
        - H < 0.5: Mean-reverting (anti-persistent)
        - H = 0.5: Random walk (no memory)
        - H > 0.5: Trending (persistent)

        Based on: Hurst (1951) "Long-term storage capacity of reservoirs"
        Method: Rescaled Range (R/S) analysis

        Args:
            prices: Price series
            max_lag: Maximum lag for R/S calculation

        Returns:
            Hurst exponent (0 to 1)
        """
        try:
            if len(prices) < 50:
                return 0.5  # Default to random walk

            returns = prices.pct_change().dropna().values

            if len(returns) < 50:
                return 0.5

            # R/S analysis at different scales
            lags = range(10, min(max_lag + 1, len(returns) // 4))
            rs_values = []

            for lag in lags:
                # Split into non-overlapping windows
                n_windows = len(returns) // lag
                if n_windows < 2:
                    continue

                rs_for_lag = []
                for i in range(n_windows):
                    window = returns[i * lag:(i + 1) * lag]

                    # Calculate mean-adjusted cumulative sum
                    mean_adj = window - np.mean(window)
                    cumsum = np.cumsum(mean_adj)

                    # Range
                    R = np.max(cumsum) - np.min(cumsum)

                    # Standard deviation
                    S = np.std(window, ddof=1)

                    if S > 0:
                        rs_for_lag.append(R / S)

                if rs_for_lag:
                    rs_values.append((np.log(lag), np.log(np.mean(rs_for_lag))))

            if len(rs_values) < 3:
                return 0.5

            # Linear regression on log-log plot
            x = np.array([v[0] for v in rs_values])
            y = np.array([v[1] for v in rs_values])

            # H = slope of log(R/S) vs log(n)
            slope, _ = np.polyfit(x, y, 1)

            # Clip to valid range
            return np.clip(slope, 0.0, 1.0)

        except Exception as e:
            logger.debug(f"Hurst exponent calculation failed: {e}")
            return 0.5

    def _calculate_ewma_zscore(
        self,
        prices: pd.Series,
        span: int = 20,
        min_periods: int = 10
    ) -> float:
        """
        Calculate z-score using exponentially weighted mean and std.

        EWMA z-score is more responsive to regime changes than rolling z-score
        because it gives more weight to recent observations.

        Args:
            prices: Price series
            span: EWMA span (half-life in bars)
            min_periods: Minimum periods for valid calculation

        Returns:
            EWMA z-score
        """
        try:
            if len(prices) < min_periods:
                return 0.0

            # EWMA mean
            ewma_mean = prices.ewm(span=span, min_periods=min_periods).mean()

            # EWMA standard deviation
            ewma_std = prices.ewm(span=span, min_periods=min_periods).std()

            # Current values
            current_price = prices.iloc[-1]
            current_mean = ewma_mean.iloc[-1]
            current_std = ewma_std.iloc[-1]

            if pd.isna(current_std) or current_std <= 0:
                return 0.0

            zscore = (current_price - current_mean) / current_std

            return zscore

        except Exception as e:
            logger.debug(f"EWMA z-score calculation failed: {e}")
            return 0.0

    def _get_volatility_adjusted_threshold(
        self,
        data: pd.DataFrame,
        base_threshold: float,
        lookback: int = 60
    ) -> float:
        """
        Dynamically adjust dislocation threshold based on volatility regime.

        In high-vol environments, a z-score of 2.0 is less extreme than in low-vol.
        We scale the threshold to maintain consistent statistical significance.

        Args:
            data: DataFrame with price data
            base_threshold: Base z-score threshold
            lookback: Lookback for historical volatility

        Returns:
            Volatility-adjusted threshold
        """
        try:
            if 'close' not in data.columns or len(data) < lookback:
                return base_threshold

            returns = data['close'].pct_change().dropna()

            if len(returns) < lookback:
                return base_threshold

            # Current volatility (recent 10 bars)
            current_vol = returns.tail(10).std()

            # Historical volatility
            hist_vol = returns.tail(lookback).std()

            if hist_vol <= 0 or pd.isna(hist_vol):
                return base_threshold

            # Volatility ratio
            vol_ratio = current_vol / hist_vol

            # Adjust threshold: higher vol = higher threshold needed
            # Clamp adjustment between 0.7x and 1.5x
            adjustment = np.clip(vol_ratio, 0.7, 1.5)

            return base_threshold * adjustment

        except Exception as e:
            logger.debug(f"Volatility-adjusted threshold failed: {e}")
            return base_threshold

    def _calculate_alpha_quality_score(
        self,
        data: pd.DataFrame,
        idx: int,
        zscore: float
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate comprehensive alpha quality score using v4.0 quant methods.

        This aggregates:
        1. Half-life quality (shorter = better)
        2. Hurst exponent validity (H < 0.5 = good)
        3. EWMA z-score confirmation
        4. Volatility regime appropriateness

        Args:
            data: DataFrame with OHLCV data
            idx: Current bar index
            zscore: Current z-score value

        Returns:
            Tuple of (quality_score 0-100, diagnostic dict)
        """
        diagnostics = {
            'half_life': None,
            'hurst_exponent': None,
            'ewma_zscore': None,
            'vol_adjusted_threshold': None,
            'alpha_valid': False
        }

        try:
            if 'close' not in data.columns:
                return 50.0, diagnostics

            # Get lookback window
            lookback = min(idx, getattr(self.config, 'lookback_period', 20))
            if lookback < 20:
                return 50.0, diagnostics

            prices = data['close'].iloc[max(0, idx - lookback):idx + 1]

            if len(prices) < 20:
                return 50.0, diagnostics

            quality_score = 50.0  # Neutral baseline

            # 1. Half-Life Quality (20% weight)
            half_life = self._calculate_half_life(prices)
            diagnostics['half_life'] = half_life

            if half_life != float('inf'):
                # Ideal half-life: 5-20 bars (fast enough to profit, slow enough to trade)
                if 5 <= half_life <= 20:
                    quality_score += 20  # Excellent half-life
                elif 3 <= half_life < 5 or 20 < half_life <= 40:
                    quality_score += 10  # Good half-life
                elif half_life > 40:
                    quality_score -= 10  # Too slow to revert
            else:
                quality_score -= 15  # Not mean-reverting

            # 2. Hurst Exponent Validation (25% weight)
            hurst = self._calculate_hurst_exponent(prices)
            diagnostics['hurst_exponent'] = hurst

            if hurst < 0.4:
                quality_score += 25  # Strongly mean-reverting
                diagnostics['alpha_valid'] = True
            elif hurst < 0.5:
                quality_score += 15  # Moderately mean-reverting
                diagnostics['alpha_valid'] = True
            elif hurst < 0.55:
                quality_score += 0   # Near random walk
            else:
                quality_score -= 20  # Trending - don't mean-revert!

            # 3. EWMA Z-Score Confirmation (15% weight)
            ewma_zscore = self._calculate_ewma_zscore(prices)
            diagnostics['ewma_zscore'] = ewma_zscore

            # EWMA and rolling z-score should agree in direction
            if np.sign(ewma_zscore) == np.sign(zscore):
                if abs(ewma_zscore) >= abs(zscore) * 0.8:
                    quality_score += 15  # Strong confirmation
                else:
                    quality_score += 7   # Partial confirmation
            else:
                quality_score -= 10  # Divergence - be cautious

            # 4. Volatility Regime (10% weight)
            vol_adj_thresh = self._get_volatility_adjusted_threshold(
                data.iloc[:idx + 1],
                self.config.dislocation_minimum
            )
            diagnostics['vol_adjusted_threshold'] = vol_adj_thresh

            # If current z-score exceeds vol-adjusted threshold, it's significant
            if abs(zscore) >= vol_adj_thresh:
                quality_score += 10

            return np.clip(quality_score, 0, 100), diagnostics

        except Exception as e:
            logger.debug(f"Alpha quality score failed: {e}")
            return 50.0, diagnostics

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

    def _check_proactive_stop_loss(
        self,
        symbol: str,
        data: pd.DataFrame,
        idx: int
    ) -> Optional[StrategySignal]:
        """
        Proactive stop-loss check - runs EVERY bar regardless of z-score.

        This is CRITICAL for mean reversion: when a trade goes against us,
        z-score becomes MORE extreme (e.g., more oversold after buying oversold),
        so the normal signal logic would generate another BUY instead of a SELL.

        This method checks if we have an open position that exceeds stop-loss
        and generates a FORCED SELL signal, bypassing z-score logic entirely.

        Args:
            symbol: Symbol to check
            data: Market data with OHLCV
            idx: Current bar index

        Returns:
            StrategySignal if stop-loss triggered, None otherwise
        """
        # Check if we have position tracking
        if not hasattr(self, '_position_details') or not self._position_details:
            return None

        pos_info = self._position_details.get(symbol)
        if not pos_info or pos_info.get('quantity', 0) == 0:
            return None

        # Get position details
        entry_price = pos_info.get('entry_price', 0)
        quantity = pos_info.get('quantity', 0)

        if entry_price <= 0:
            return None

        # Get current price
        current_row = data.iloc[idx]
        current_price = current_row.get('close', current_row.get('Close', 0))

        if current_price <= 0:
            return None

        # Calculate P&L
        if quantity > 0:  # Long position
            pnl_pct = (current_price - entry_price) / entry_price * 100
        else:  # Short position
            pnl_pct = (entry_price - current_price) / entry_price * 100

        # Get stop-loss threshold from config
        stop_loss_pct = getattr(self.config, 'stop_loss_pct', -2.0)

        # Check if stop-loss triggered
        if pnl_pct <= stop_loss_pct:
            # Generate FORCED exit signal (explicit exit types per Rule 2)
            signal_type = SignalType.LONG_EXIT if quantity > 0 else SignalType.SHORT_EXIT

            # Get timestamp
            timestamp = current_row.get('timestamp', data.index[idx] if hasattr(data, 'index') else datetime.now())

            logger.warning(
                f"⛔ [{symbol}] PROACTIVE STOP-LOSS TRIGGERED @ bar {idx}: "
                f"P&L={pnl_pct:+.2f}% <= {stop_loss_pct}%, "
                f"Entry=${entry_price:.2f}, Current=${current_price:.2f}"
            )

            try:
                return StrategySignal(
                    symbol=symbol,
                    signal_type=signal_type,
                    confidence=1.0,  # High confidence - stop-loss is mandatory
                    strength=0.0,    # Forced exit, not quality-based
                    timestamp=timestamp,
                    signal_price=current_price,
                    entry_price=entry_price,
                    target_quantity=abs(quantity),  # Exit full position
                    quantity_type="ABSOLUTE",
                    strategy_id=getattr(self, 'strategy_id', 'mean_reversion'),
                    signal_source='PROACTIVE_STOP_LOSS',
                    signal_reason=f"Stop-loss triggered: {pnl_pct:+.2f}% <= {stop_loss_pct}%",
                    additional_data={
                        'current_price': current_price,
                        'pnl_pct': pnl_pct,
                        'stop_loss_threshold': stop_loss_pct
                    }
                )
            except Exception as e:
                return None

        return None

    def _is_regime_favorable(self, symbol: str) -> bool:
        """Check if current regime is favorable for mean reversion"""
        if symbol not in self.regime_data:
            return True

        regime = self.regime_data[symbol]
        return not regime.get('is_trending', False) and not regime.get('is_high_vol', False)

    def _get_regime_label(self, symbol: str) -> str:
        """
        Get regime label for ADS SMS exponent selection.

        Maps internal regime data to ADS regime categories:
        - 'low_vol': Low volatility environment
        - 'normal': Normal conditions
        - 'high_vol': High volatility
        - 'crisis': Extreme volatility/trending

        Returns:
            Regime label string for SMS exponent selection
        """
        if symbol not in self.regime_data:
            return 'normal'

        regime = self.regime_data[symbol]
        vol_ratio = regime.get('volatility_ratio', 1.0)
        is_trending = regime.get('is_trending', False)
        is_high_vol = regime.get('is_high_vol', False)

        # Map to ADS regime categories
        if is_trending and is_high_vol:
            return 'crisis'
        elif is_high_vol or vol_ratio > 1.5:
            return 'high_vol'
        elif vol_ratio < 0.7:
            return 'low_vol'
        else:
            return 'normal'

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
