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
from enum import Enum
import logging
import asyncio  # FIXED: LOW #13 - Add asyncio for Lock

# Professional re-architecture imports
from .momentum_state_machine import MomentumStateMachine, SymbolStateName

# Import enhanced base strategy
from ...base_strategy_enhanced import EnhancedBaseStrategy
from ...strategy_engine import (
    StrategySignal, SignalType
)

# ADS v3.1: continuous regime vector + tau(R)
from core_engine.alpha.ads_regime_vector import ADSRegimeVector, compute_sms_tau
from core_engine.alpha.ads_components import PendingSignalQueue, PendingSignalContext, SignalMaturityScore, ERAR, estimate_cvar_95

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

        # State Machine (Professional re-architecture)
        self.state_machine = MomentumStateMachine()

        # Performance tracking
        self.trade_history: List[Dict[str, Any]] = []
        self.momentum_performance: Dict[str, Dict[str, float]] = {}

        # ADS v3.1: pending signal queue (SMS maturation) + per-symbol regime vector memory
        self.pending_signals = PendingSignalQueue(
            max_pending=getattr(config, "sms_max_pending", 50)
        )
        self._ads_regime_prev: Dict[str, ADSRegimeVector] = {}

        # FIXED: MED #8 - Cache column mapping for performance
        self._column_mapping_cache = self._get_column_mapping()

        logger.info(f"  Enhanced Momentum Strategy {self.strategy_id} initialized")

        # Performance/log-noise: avoid per-bar INFO logs in generate_signals().
        self._bar_log_counter: int = 0

        # Diagnostics: summarize why the state machine didn't trigger entries (no per-bar spam).
        self._sm_entry_reasons: Dict[str, int] = {}
        self._sm_entries_triggered: int = 0

    # ========================================
    # ADS v3.1: REGIME VECTOR ADAPTER
    # ========================================

    def _get_ads_regime_vector(self, symbol: str) -> Tuple[ADSRegimeVector, Dict[str, Any]]:
        """
        Best-effort adapter to ADS continuous regime vector.
        Uses system RegimeContext if available; otherwise falls back to conservative defaults.
        """
        regime_context = None
        try:
            regime_context = self.get_current_regime_context()
        except Exception:
            regime_context = None

        prev = self._ads_regime_prev.get(symbol)
        r, diag = ADSRegimeVector.from_regime_context(regime_context, prev=prev)
        self._ads_regime_prev[symbol] = r
        return r, diag

    @staticmethod
    def _normalize_composite_pct(x: float) -> float:
        """
        Normalize composite_pct into [0, 100].

        Runtime evidence shows some pipelines emit composite_pct in [-1, 1] (signed scale),
        while others may emit [0, 1] or [0, 100]. We normalize conservatively:
          - If -1 <= x <= 1: treat as signed scale and map to [0,100] via (x+1)/2*100.
          - Else: assume already in percent space (best-effort) and clip.
        """
        try:
            v = float(x)
        except Exception:
            return 0.0
        if -1.0 <= v <= 1.0:
            v = (v + 1.0) * 50.0
        return float(np.clip(v, 0.0, 100.0))

    def _fallback_compute_composite_signals(
        self,
        data: pd.DataFrame,
        idx: int,
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Compute (composite_z, composite_pct) from price history when the enrichment pipeline
        does not provide them (or provides NaNs).

        This is intentionally lightweight and deterministic (smoke-test focused).
        """
        try:
            if "close" not in data.columns:
                return None, None

            n = len(data)
            if idx < 0:
                idx = n + idx
            if idx <= 0 or idx >= n:
                return None, None

            sp = int(getattr(self.config, "short_period", 10))
            mp = int(getattr(self.config, "medium_period", 20))
            lp = int(getattr(self.config, "long_period", 50))
            lookback = int(getattr(self.config, "lookback_period", 60))

            # Need enough history for long_period and rolling window.
            if idx < max(lp, lookback):
                return None, None

            close = data["close"].to_numpy(copy=False)

            def m_at(j: int) -> float:
                # Multi-horizon return blend (weights tuned for stability)
                r_s = (close[j] / close[j - sp] - 1.0) if j - sp >= 0 else 0.0
                r_m = (close[j] / close[j - mp] - 1.0) if j - mp >= 0 else 0.0
                r_l = (close[j] / close[j - lp] - 1.0) if j - lp >= 0 else 0.0
                return float(0.5 * r_s + 0.3 * r_m + 0.2 * r_l)

            start = max(lp, idx - lookback + 1)
            window = [m_at(j) for j in range(start, idx + 1)]
            if len(window) < 10:
                return None, None

            mu = float(np.mean(window))
            sd = float(np.std(window))
            if sd <= 1e-12:
                return None, None

            m_last = float(window[-1])
            composite_z = (m_last - mu) / sd

            # Percentile rank within the window (0..100), ties -> upper rank.
            sorted_w = sorted(window)
            rank = 0
            for v in sorted_w:
                if v <= m_last:
                    rank += 1
                else:
                    break
            composite_pct = 100.0 * rank / float(len(sorted_w))

            return float(composite_z), float(composite_pct)
        except Exception:
            return None, None

    @staticmethod
    def _sms_regime_label(r: ADSRegimeVector) -> str:
        """Map ADS regime vector to SMS exponent label."""
        v = float(r.volatility)
        if v <= 0.30:
            return "low_vol"
        if v <= 0.70:
            return "normal"
        if v <= 0.90:
            return "high_vol"
        return "crisis"

    def _try_emit_matured_pending(self, symbol: str, data: pd.DataFrame, idx: int) -> Optional[StrategySignal]:
        """
        Attempt to mature and emit a pending momentum signal for this symbol.
        Returns a StrategySignal if matured, else None.
        """
        # Prefer BUY pending first, then SELL
        for side in ("BUY", "SELL"):
            ctx = self.pending_signals.get(symbol, side)
            if ctx is None:
                continue

            # Normalize index
            if idx < 0:
                idx = len(data) + idx
            if idx < 0 or idx >= len(data):
                return None

            row = data.iloc[idx]

            # Thesis validation: require composite signals still present
            composite_z = float(row.get("composite_z", 0.0)) if hasattr(row, "get") else 0.0
            composite_pct_raw = float(row.get("composite_pct", 0.0)) if hasattr(row, "get") else 0.0
            composite_pct = self._normalize_composite_pct(composite_pct_raw)

            if side == "BUY" and composite_z <= 0:
                self.pending_signals.remove(symbol, side)
                continue
            if side == "SELL" and composite_z >= 0:
                self.pending_signals.remove(symbol, side)
                continue

            # Consolidated ADS Context Calculation
            ads_ctx = self._calculate_ads_context(
                symbol, data, idx, side, 
                raw_strength=float(ctx.raw_signal_strength)
            )
            
            ctx.sms.exhaustion = ads_ctx["exhaustion"]
            ctx.sms.reversal_prob = ads_ctx["reversal_prob"]
            ctx.sms.ofi_shift = ads_ctx["ofi_shift"]
            ctx.sms.vol_compression = ads_ctx["vol_compression"]

            # Tick pending bars + stale kill
            ctx.increment_pending()
            if ctx.sms.is_stale():
                self.pending_signals.remove(symbol, side)
                continue

            # Compute tau(R) from consolidated context
            tau = ads_ctx["tau"]
            regime_label = ads_ctx["regime_label"]
            sms_score = float(ctx.sms.compute(regime_label))
            
            if sms_score < tau:
                continue

            # ADS v3.1 3: ERAR gate (strategy-side) at maturity time
            erar = ads_ctx["erar"]
            gamma = float(getattr(self.config, "erar_gamma", 0.5))
            if bool(getattr(self.config, "enable_ads_gates", True)):
                if not erar.should_trade(gamma=gamma):
                    # Keep pending, do not emit this bar
                    ctx.erar = erar
                    ctx.metadata["ads_erar"] = ads_ctx["erar_val"]
                    ctx.metadata["ads_erar_diag"] = erar.get_diagnostics()
                    continue

            # Get timestamp for signal
            try:
                ts = row.get("timestamp", None)
                if ts is None and isinstance(data.index, pd.DatetimeIndex):
                    ts = data.index[idx].to_pydatetime()
                elif isinstance(ts, pd.Timestamp):
                    ts = ts.to_pydatetime()
                if not isinstance(ts, datetime):
                    ts = None
            except Exception:
                ts = None
            if ts is None:
                return None

            additional_data = {
                "signal_reason": "ads_sms_matured_pending",
                "pending_bars": ctx.sms.pending_bars,
                "composite_z": ads_ctx["composite_z"],
                "composite_pct": ads_ctx["composite_pct"],
                "ads_tau": tau,
                "ads_sms": sms_score,
                "ads_erar": ads_ctx["erar_val"],
                "ads_erar_diag": erar.get_diagnostics(),
                "ads_regime_vector": ads_ctx["ads_regime_vector"],
                "ads_fallbacks_used": ads_ctx["ads_fallbacks_used"],
                "ads_diag": ads_ctx["ads_diag"],
                "ads_fallbacks": {"ofi_source": "proxy_volume_ratio", "bb_missing": True},
            }

            signal_type = SignalType.BUY if side == "BUY" else SignalType.SELL
            # Strategy expresses allocation intent as a static target weight hint.
            # RiskManager remains the final authority for sizing.
            base_tw = float(getattr(self.config, "base_position_pct", 0.0) or 0.0)
            max_tw = float(getattr(self.config, "max_position_pct", base_tw) or base_tw)
            target_weight_hint = float(np.clip(base_tw, 0.0, max_tw))
            return StrategySignal(
                strategy_id=self.strategy_id,
                symbol=symbol,
                signal_type=signal_type,
                strength=min(max(float(ctx.raw_signal_strength), 0.0), 1.0),
                confidence=min(0.95, max(0.55, 0.50 + sms_score * 0.45)),
                target_weight=target_weight_hint,
                quantity_type="PERCENTAGE",
                timestamp=ts,
                additional_data=additional_data
            )

        return None

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
            logger.warning(f"    Index {idx} out of bounds for DataFrame with {len(df)} rows")
            return None

        return df.iloc[idx]

    def _is_long_signal(self, signal_type: SignalType) -> bool:
        """Check if signal is a long entry/buy"""
        return signal_type in [SignalType.BUY, SignalType.LONG_ENTRY]

    def _is_short_signal(self, signal_type: SignalType) -> bool:
        """Check if signal is a short entry/sell"""
        return signal_type in [SignalType.SELL, SignalType.SHORT_ENTRY]

    def _get_side_from_signal(self, signal_type: SignalType) -> str:
        """Normalize signal type to BUY/SELL string for pending queue"""
        if self._is_long_signal(signal_type):
            return "BUY"
        if self._is_short_signal(signal_type):
            return "SELL"
        return "UNKNOWN"

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

            logger.debug(f"  {symbol} enriched data validated: {len(required_indicators)} indicators present")

    # ========================================
    # STRATEGY-SPECIFIC LIFECYCLE HOOKS
    # ========================================

    async def _initialize_strategy_components(self) -> bool:
        """Initialize strategy-specific components"""

        try:
            logger.info(f"  Initializing Momentum components for {self.strategy_id}...")

            # Validate symbols
            if not self.config.symbols:
                logger.error("  No symbols configured for momentum strategy")
                return False

            # Initialize data structures
            self._initialize_data_structures()

            # Initialize indicators
            self._initialize_indicators()

            logger.info(f"  Momentum components initialized for {len(self.config.symbols)} symbols")
            return True

        except Exception as e:
            logger.error(f"  Momentum component initialization failed: {e}")
            return False

    async def _start_strategy_operations(self) -> bool:
        """Start strategy-specific operations"""

        try:
            logger.info(f"  Starting Momentum operations for {self.strategy_id}...")

            # Start performance tracking
            self._start_performance_tracking()

            logger.info(f"  Momentum operations started")
            return True

        except Exception as e:
            logger.error(f"  Momentum operations start failed: {e}")
            return False

    async def _stop_strategy_operations(self) -> None:
        """Stop strategy-specific operations"""

        try:
            logger.info(f"  Stopping Momentum operations for {self.strategy_id}...")

            # One-line diagnostic summary for smoke-test debugging (no per-bar spam).
            # Only emit when state machine is enabled and it never triggered an entry.
            if bool(getattr(self.config, "enable_state_machine", False)) and int(getattr(self, "_sm_entries_triggered", 0)) == 0:
                reasons = getattr(self, "_sm_entry_reasons", None) or {}
                if reasons:
                    top = sorted(reasons.items(), key=lambda kv: kv[1], reverse=True)[:5]
                    top_str = ", ".join([f"{k}={v}" for k, v in top])
                    logger.info(f"  StateMachine entry triggers: 0 (top reasons: {top_str})")
                else:
                    logger.info("  StateMachine entry triggers: 0 (no reasons recorded)")

            # Close all positions
            await self._close_all_positions()

            # Save performance data
            self._save_performance_data()

            logger.info(f"  Momentum operations stopped")

        except Exception as e:
            logger.error(f"  Momentum operations stop failed: {e}")

    async def _check_strategy_health(self) -> Dict[str, Any]:
        """Check strategy-specific health"""

        try:
            # ADS v3.1: Use PositionBook SSOT for accurate health metrics
            active_pos_count = 0
            if hasattr(self, '_position_book'):
                active_pos_count = len(self._position_book.get_all_positions())

            health_metrics = {
                'strategy_healthy': True,
                'symbols_tracked': len(self.config.symbols),
                'active_positions': active_pos_count,
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
        """
        start_time = datetime.now()
        signals = []

        # FIXED: EXTRA - Comprehensive input validation at strategy boundary
        if not isinstance(enriched_data, dict):
            raise TypeError(f"enriched_data must be a dictionary, got {type(enriched_data)}")

        if not enriched_data:
            logger.warning("    generate_signals() called with empty enriched_data")
            return []

        # Validate all values are DataFrames with numeric dtypes
        for symbol, data in enriched_data.items():
            if not isinstance(data, pd.DataFrame):
                raise TypeError(f"{symbol} data must be a DataFrame, got {type(data)}")

            if data.empty:
                logger.warning(f"    {symbol} has empty DataFrame, skipping")
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

        try:
            # PHASE 4: Validate enriched data (Rule 3)
            self._validate_enriched_data(enriched_data)

            # Update market data with enriched data
            self._update_market_data(enriched_data)

            # Update momentum analysis (using pre-calculated indicators)
            self._update_momentum_analysis()

            # Generate signals for each symbol
            for symbol in self.config.symbols:
                if symbol in self.market_data and len(self.market_data[symbol]) > self.config.long_period:
                    symbol_signals = await self._generate_symbol_signals(symbol)
                    signals.extend(symbol_signals)

            # Update performance metrics
            generation_time = (datetime.now() - start_time).total_seconds()
            self.track_signal_generation_time(generation_time)

            # Summary logging
            symbols_checked = [s for s in self.config.symbols if s in self.market_data and len(self.market_data[s]) > self.config.long_period]
            
            if len(signals) > 0:
                logger.info(f"  Momentum Strategy: {len(symbols_checked)} symbols, {len(signals)} signals in {generation_time:.3f}s")
            # Heartbeat removed to reduce log noise during long backtests (ADS v3.1 compliance)

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

        # ADS v3.1 compliance (single-authority exits):
        # Exit logic and position SSOT live in CentralRiskManager + PositionBook.
        # Momentum strategy only emits entry intent; it does not generate exits or track positions locally.
        try:
            self._update_market_data(market_data)
            self._update_performance_tracking()
        except Exception as e:
            self._log_error("Position update failed", e)

    async def _check_exits_for_all_positions(self, enriched_data_dict: Dict[str, pd.DataFrame]) -> None:
        """
        ADS v3.1: Legacy exit path is disabled. 
        Exits are managed by Risk Manager + PositionBook authority.
        """
        return

    # ========================================
    # SIGNAL GENERATION METHODS
    # ========================================

    # REMOVED: _get_regime_adjusted_thresholds_old (FIXED: LOW #11 - dead code removed)
    # Use _get_regime_adjusted_thresholds (Phase 4B) instead

    async def _evaluate_bar_at_index(self, symbol: str, idx: int) -> Optional[StrategySignal]:
        """
        Evaluate a specific bar at index and generate signal if conditions are met
        """
        try:
            # Get data at index (FIXED: HIGH #2 - use safe_iloc)
            data = self.market_data[symbol]

            # Use safe_iloc for bounds checking
            current_data = self._safe_iloc(data, idx)
            if current_data is None:
                logger.warning(f"    [{symbol}] Cannot evaluate bar at index {idx} - out of bounds")
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

            # Fallback: try to get from timestamp-like columns if index extraction failed
            if not signal_timestamp:
                try:
                    # Prefer DataFrame columns (works even when index is RangeIndex)
                    for col in ("timestamp", "Timestamp", "datetime", "date", "time"):
                        if col in data.columns:
                            ts = data[col].iloc[actual_idx]
                            if isinstance(ts, pd.Timestamp):
                                signal_timestamp = ts.to_pydatetime()
                            elif isinstance(ts, datetime):
                                signal_timestamp = ts
                            elif isinstance(ts, str):
                                try:
                                    signal_timestamp = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                                except Exception:
                                    signal_timestamp = None
                            else:
                                # Best-effort coercion (e.g., numpy datetime64)
                                try:
                                    ts2 = pd.Timestamp(ts)
                                    signal_timestamp = ts2.to_pydatetime()
                                except Exception:
                                    signal_timestamp = None
                            if signal_timestamp:
                                break
                except Exception:
                    signal_timestamp = None

            # Last resort: attempt to coerce the index value at actual_idx into a timestamp
            if not signal_timestamp:
                try:
                    ts2 = pd.Timestamp(data.index[actual_idx])
                    if not pd.isna(ts2):
                        signal_timestamp = ts2.to_pydatetime()
                except Exception:
                    signal_timestamp = None

            # FIXED: HIGH #4 - Do NOT use datetime.now() fallback for bar timestamps
            if not signal_timestamp:
                logger.error(f"  [{symbol}] Missing bar timestamp at index {idx} - skipping bar (do not use datetime.now())")
                return None

            # ========================================
            # PROFESSIONAL RE-ARCHITECTURE: State Machine (V1)
            # ========================================
            has_pos = self._has_position(symbol)

            # A. EXIT EVALUATION (If in position)
            if has_pos:
                # 1. State Machine: Structural Stop (Thesis Level)
                if getattr(self.config, 'enable_state_machine', False):
                    self.state_machine.reconcile(symbol, True)
                    state = self.state_machine.get_state(symbol)
                    if state.setup_low and current_data['close'] < state.setup_low:
                        logger.warning(f"🛑 [{symbol}] STRUCTURAL STOP HIT: {current_data['close']:.2f} < {state.setup_low:.2f}")
                        pos_info = self._get_position_info(symbol)
                        return await self._generate_exit_signal(
                            symbol, pos_info, current_data['close'], "structural_stop", signal_timestamp
                        )
                
                # 2. Hybrid Exit Logic: ADS v3.1 + Standard Stops
                should_exit, exit_reason = await self._check_exit_conditions_hybrid(
                    symbol, data, signal_timestamp
                )
                if should_exit:
                    pos_info = self._get_position_info(symbol)
                    exit_sig = await self._generate_exit_signal(
                        symbol, pos_info, current_data['close'], exit_reason, signal_timestamp
                    )
                    return exit_sig
                
                # Already in position and no exit triggered -> done for this bar
                return None

            # B. ENTRY EVALUATION (If flat)
            if getattr(self.config, 'enable_state_machine', False):
                # 1. State Machine: Brain Evaluation
                self.state_machine.reconcile(symbol, False)
                should_entry, reason = self.state_machine.evaluate(
                    symbol, actual_idx, current_data, data, self.config
                )
                if reason:
                    self._sm_entry_reasons[reason] = int(self._sm_entry_reasons.get(reason, 0)) + 1
                
                if should_entry:
                    self._sm_entries_triggered += 1
                    confidence = self._calculate_signal_confidence(symbol, MomentumSignal.BULLISH_MOMENTUM)
                    state = self.state_machine.get_state(symbol)
                    signal = StrategySignal(
                        strategy_id=self.strategy_id,
                        symbol=symbol,
                        signal_type=SignalType.LONG_ENTRY,
                        strength=1.0,
                        confidence=confidence,
                        timestamp=signal_timestamp,
                        additional_data={
                            'signal_reason': reason,
                            'setup_high': state.setup_high,
                            'setup_low': state.setup_low,
                            'structural_stop': state.setup_low,
                            'pattern_mode': 'BREAKOUT_ACCELERATION'
                        }
                    )
                    base_tw = float(getattr(self.config, "base_position_pct", 0.0) or 0.0)
                    max_tw = float(getattr(self.config, "max_position_pct", base_tw) or base_tw)
                    signal.target_weight = float(np.clip(base_tw, 0.0, max_tw))
                    signal.quantity_type = "PERCENTAGE"
                    return signal
                
                # If state machine is enabled, it handles its own entry/exit checks.
                return None

            # --- ADS v3.1: ENHANCED COMPOSITE ENTRY LOGIC ---
            # Use multi-horizon momentum and composite indicators for high-probability setups.
            
            # Get indicators for the current bar
            indicators = self.indicators[symbol]

            # Extract momentum horizons (short, medium, long)
            momentum_10_col = f'momentum_{self.config.short_period}'
            momentum_20_col = f'momentum_{self.config.medium_period}'
            momentum_50_col = f'momentum_{self.config.long_period}'

            short_m = data[momentum_10_col].iloc[actual_idx] if momentum_10_col in data.columns else 0
            medium_m = data[momentum_20_col].iloc[actual_idx] if momentum_20_col in data.columns else 0
            long_m = data[momentum_50_col].iloc[actual_idx] if momentum_50_col in data.columns else 0

            # Handle NaN values gracefully
            short_momentum = short_m if not pd.isna(short_m) else 0
            medium_momentum = medium_m if not pd.isna(medium_m) else 0
            long_momentum = long_m if not pd.isna(long_m) else 0

            # Calculate weighted momentum strength
            momentum_strength = abs(short_momentum) * self.config.momentum_strength_weight_short + \
                              abs(medium_momentum) * self.config.momentum_strength_weight_medium + \
                              abs(long_momentum) * self.config.momentum_strength_weight_long

            # Retrieve trend and volume confirmation indicators
            adx_series = indicators.get('adx', pd.Series())
            volume_ratio_series = indicators.get('volume_ratio', pd.Series())
            trend_strength_series = indicators.get('trend_strength', pd.Series())

            adx = adx_series.iloc[actual_idx] if len(adx_series) > actual_idx else adx_series.iloc[-1] if len(adx_series) > 0 else 0
            vol_ratio = volume_ratio_series.iloc[actual_idx] if len(volume_ratio_series) > actual_idx else volume_ratio_series.iloc[-1] if len(volume_ratio_series) > 0 else 1
            trend_str = trend_strength_series.iloc[actual_idx] if len(trend_strength_series) > actual_idx else trend_strength_series.iloc[-1] if len(trend_strength_series) > 0 else 0

            # Clean and normalize indicators
            adx = adx if not pd.isna(adx) else 0
            volume_ratio = vol_ratio if not pd.isna(vol_ratio) else 1
            trend_strength = trend_str if not pd.isna(trend_str) else 0

            # ========================================
            # PHASE 4A: COMPOSITE SIGNAL EVALUATION
            # ========================================

            # Check composite entry conditions (normalized thresholds)
            should_enter, signal_type = self._check_composite_entry(
                symbol, current_data,
                enriched_data=data,
                current_idx=actual_idx
            )

            if should_enter and signal_type:
                # ADS v3.1  1: SMS gate with pending/stale maturation
                side = self._get_side_from_signal(signal_type)
                
                # Check if already pending for this symbol/side to avoid logic flooding
                if self.pending_signals.get(symbol, side):
                    logger.debug(f"  [{symbol}] {side} signal already pending, skipping redundant enqueue")
                    return None

                # ADS v3.1: Consolidate ADS context (SMS values + ERAR object)
                raw_strength = float(min(abs(momentum_strength) / self.config.momentum_threshold, 1.0))
                ads_ctx = self._calculate_ads_context(symbol, data, actual_idx, side, raw_strength=raw_strength)
                
                tau = ads_ctx["tau"]
                regime_label = ads_ctx["regime_label"]
                ads_diag = ads_ctx["ads_diag"]

                sms = SignalMaturityScore(
                    exhaustion=ads_ctx["exhaustion"],
                    reversal_prob=ads_ctx["reversal_prob"],
                    ofi_shift=ads_ctx["ofi_shift"],
                    vol_compression=ads_ctx["vol_compression"],
                    pending_bars=0,
                    decay_rate=0.05,
                    max_pending=int(getattr(self.config, "sms_max_pending", 50)),
                )

                sms_score = float(sms.compute(regime_label))
                if sms_score < tau:
                    # Enqueue pending instead of emitting
                    try:
                        price = float(current_data.get("close", 0.0))
                    except Exception:
                        price = 0.0
                    
                    ctx = PendingSignalContext(
                        symbol=symbol,
                        side=side,
                        sms=sms,
                        erar=ads_ctx["erar"],
                        raw_signal_strength=raw_strength,
                        timestamp=signal_timestamp,
                        entry_price=price if price > 0 else 0.0,
                        metadata={
                            "ads_tau": tau,
                            "ads_sms": sms_score,
                            "ads_regime_vector": ads_ctx["ads_regime_vector"],
                            "ads_fallbacks_used": ads_ctx["ads_fallbacks_used"],
                            "ads_diag": ads_diag,
                            "ofi_source": "proxy_volume_ratio",
                            "bb_missing": True,
                            "composite_z": ads_ctx["composite_z"],
                            "composite_pct": ads_ctx["composite_pct"],
                        },
                    )
                    self.pending_signals.add(ctx)
                    return None

                # ADS v3.1  3: ERAR gate (strategy-side)
                erar = ads_ctx["erar"]
                gamma = float(getattr(self.config, "erar_gamma", 0.5))
                if bool(getattr(self.config, "enable_ads_gates", True)):
                    if not erar.should_trade(gamma=gamma):
                        return None

                # Generate signal based on composite entry
                mom_signal = MomentumSignal.BULLISH_MOMENTUM if side == "BUY" else MomentumSignal.BEARISH_MOMENTUM
                confidence = self._calculate_signal_confidence(symbol, mom_signal)

                if confidence > 0.4:  # Minimum confidence threshold (lowered for composite signals)
                    base_tw = float(getattr(self.config, "base_position_pct", 0.0) or 0.0)
                    max_tw = float(getattr(self.config, "max_position_pct", base_tw) or base_tw)
                    target_weight = float(np.clip(base_tw, 0.0, max_tw))

                    signal = StrategySignal(
                        strategy_id=self.strategy_id,
                        symbol=symbol,
                        signal_type=signal_type,
                        strength=min(abs(momentum_strength) / self.config.momentum_threshold, 1.0),
                        confidence=confidence,
                        target_weight=float(target_weight),
                        quantity_type="PERCENTAGE",  # Explicitly mark as percentage
                        timestamp=signal_timestamp,
                        additional_data={
                            'signal_reason': 'composite_entry',
                            'entry_method': 'composite_z_pct',
                            'composite_z': float(ads_ctx['composite_z']),
                            'composite_pct': float(ads_ctx['composite_pct']),
                            'ads_tau': float(tau),
                            'ads_sms': float(sms_score),
                            'ads_erar': float(ads_ctx['erar_val']),
                            'ads_erar_diag': erar.get_diagnostics(),
                            'ads_regime_vector': ads_ctx['ads_regime_vector'],
                            'ads_fallbacks_used': ads_ctx['ads_fallbacks_used'],
                            'ads_diag': ads_diag,
                            'ads_fallbacks': {'ofi_source': 'proxy_volume_ratio', 'bb_missing': True},
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
            # ADS v3.1: strategies should not maintain local position state.
            # Use PositionBook SSOT (via EnhancedBaseStrategy._has_position()).
            

            # Get current indicators and momentum data
            logger.debug(f"  [{symbol}] Checking data availability:")
            logger.debug(f"   symbol in self.indicators: {symbol in self.indicators}")
            logger.debug(f"   symbol in self.momentum_data: {symbol in self.momentum_data}")

            if symbol not in self.indicators:
                logger.warning(f"  [{symbol}] Missing indicators - cannot generate signals")
                return signals
            if symbol not in self.momentum_data:
                logger.warning(f"  [{symbol}] Missing momentum_data - cannot generate signals")
                return signals

            data = self.market_data[symbol]
            data_length = len(data)

            # Check if we should scan all bars (historical mode) or just current bar (live mode)
            if self.config.scan_all_bars and data_length > self.config.long_period:
                # Historical scanning mode: scan through all bars
                logger.info(f"[{symbol}]   Historical scanning mode: scanning {data_length} bars "
                           f"(evaluating every {self.config.scan_interval} bars)")

                start_idx = self.config.long_period
                end_idx = data_length
                scan_interval = max(1, self.config.scan_interval)

                bars_evaluated = 0
                for idx in range(start_idx, end_idx, scan_interval):
                    # ADS v3.1: emit any matured pending signals first
                    matured = self._try_emit_matured_pending(symbol, data, idx)
                    if matured is not None:
                        signals.append(matured)

                    signal = await self._evaluate_bar_at_index(symbol, idx)
                    if signal:
                        signals.append(signal)
                    bars_evaluated += 1

                logger.info(f"[{symbol}]   Historical scan complete: {bars_evaluated} bars evaluated, "
                           f"{len(signals)} signals generated")
                return signals

            # Live mode: Evaluate only current bar (default behavior)
            logger.debug(f"[{symbol}] Live mode: evaluating current bar only")

            matured = self._try_emit_matured_pending(symbol, self.market_data[symbol], -1)
            if matured is not None:
                signals.append(matured)

            # Reuse the same evaluation path as historical scanning to avoid logic drift
            signal = await self._evaluate_bar_at_index(symbol, -1)
            if signal is not None:
                signals.append(signal)
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
                logger.debug(f"  Updating momentum analysis for {symbol} from enriched data")
                self.momentum_data[symbol] = self._analyze_symbol_momentum(symbol)
                # Also populate indicators dictionary for signal generation
                self._extract_indicators_from_data(symbol)
                logger.debug(f"  Momentum data updated for {symbol}: {list(self.momentum_data[symbol].keys()) if symbol in self.momentum_data else 'FAILED'}")
            else:
                logger.warning(f"    Cannot update momentum for {symbol} - missing market data")

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
            adx_series = adx_series.ffill().fillna(25.0)  # Default ADX if all NaN
            volume_ratio_series = volume_ratio_series.ffill().fillna(1.0)  # Default 1.0 if all NaN
            trend_strength_series = trend_strength_series.ffill().fillna(0.0)  # Default 0.0 if all NaN

            self.indicators[symbol] = {
                'adx': adx_series,
                'volume_ratio': volume_ratio_series,
                'trend_strength': trend_strength_series,
            }

            logger.debug(f"  Extracted indicators for {symbol}: {list(self.indicators[symbol].keys())}")

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
                # Create defensive copy to prevent mutations
                self.market_data[symbol] = data.copy()

    def _initialize_data_structures(self) -> None:
        """Initialize strategy data structures"""

        self.market_data.clear()
        self.indicators.clear()
        self.momentum_data.clear()

    def _initialize_indicators(self) -> None:
        """Initialize indicators dictionary"""

        for symbol in self.config.symbols:
            self.indicators[symbol] = {}
            self.momentum_data[symbol] = {}

    def _start_performance_tracking(self) -> None:
        """Start performance tracking"""
        logger.info("  Momentum performance tracking started")

    async def _close_all_positions(self) -> None:
        """Best-effort close request (authority lives in Risk Manager + PositionBook)."""
        logger.info("  Momentum Strategy requesting close-all via Risk Manager (best-effort)")
        await super()._close_all_positions()

    def _save_performance_data(self) -> None:
        """Save performance data"""
        logger.info("  Momentum performance data saved")

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

    def _get_position_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get enhanced position information (Phase 2)
        SSOT Compliant: Use PositionBook as authority.
        """
        if self._position_book:
            pos = self._position_book.get_position(symbol)
            if pos:
                return {
                    'symbol': symbol,
                    'direction': 1 if pos.is_long else -1 if pos.is_short else 0,
                    'avg_entry_price': float(pos.avg_entry_price),
                    'total_quantity': float(pos.quantity),
                    'high_water_mark': float(pos.current_price), # Initial HWM
                    'entry_time': pos.opened_at,
                    'trailing_stop_activated': False # Will be updated by stop logic
                }
        return None

    # ========================================
    # NEW: REGIME-AWARE ENTRY LOGIC (Phase 4B)
    # ========================================

    def _get_regime_adjusted_thresholds(
        self,
        symbol: str,
        current_bar: pd.Series
    ) -> Dict[str, float]:
        """
        ADS v3.1: return fully adjusted entry thresholds derived from continuous regime vector R.

        Discrete labels may exist in bar data, but they are not the sole regime representation.

        Returns:
            Dict with:
              - long_threshold (abs composite_z threshold)
              - short_threshold (abs composite_z threshold)
              - pct_threshold (0-100)
              - adjustment_reason
              - ads_regime_vector (snapshot)
              - ads_fallbacks_used
        """
        # Base thresholds (strategy-defined)
        base_long = float(getattr(self.config, "composite_z_entry", 0.5))
        base_short = float(getattr(self.config, "composite_z_entry", 0.5))
        base_pct = float(getattr(self.config, "composite_pct_entry", 70.0))

        ads_r, diag = self._get_ads_regime_vector(symbol=symbol)

        reason_parts: List[str] = []

        # Trend alignment: make it easier to trade with the prevailing trend, harder against it
        long_mult = 1.0
        short_mult = 1.0
        if ads_r.trend >= 0.3:
            long_mult *= 0.9
            short_mult *= 1.2
            reason_parts.append("trend_bull")
        elif ads_r.trend <= -0.3:
            long_mult *= 1.2
            short_mult *= 0.9
            reason_parts.append("trend_bear")
        else:
            long_mult *= 1.1
            short_mult *= 1.1
            reason_parts.append("trend_choppy")

        # Volatility: high vol -> stricter (avoid noisy breakouts), low vol -> slightly lenient
        vol_mult = 1.0
        if ads_r.volatility >= 0.75:
            vol_mult *= 1.1
            reason_parts.append("vol_high")
        elif ads_r.volatility <= 0.25:
            vol_mult *= 0.95
            reason_parts.append("vol_low")

        # Liquidity: low liquidity -> stricter thresholds
        liq_mult = 1.0
        pct_bump = 0.0
        if ads_r.liquidity <= 0.4:
            liq_mult *= 1.1
            pct_bump += 5.0
            reason_parts.append("liq_low")

        # Confidence: low confidence -> stricter
        conf_mult = 1.0
        if ads_r.confidence <= 0.5:
            conf_mult *= 1.05
            reason_parts.append("conf_low")

        long_threshold = base_long * long_mult * vol_mult * liq_mult * conf_mult
        short_threshold = base_short * short_mult * vol_mult * liq_mult * conf_mult
        pct_threshold = min(95.0, max(50.0, base_pct + pct_bump))

        return {
            "long_threshold": float(long_threshold),
            "short_threshold": float(short_threshold),
            "pct_threshold": float(pct_threshold),
            "adjustment_reason": "+".join(reason_parts) if reason_parts else "none",
            "ads_regime_vector": {
                "volatility": ads_r.volatility,
                "trend": ads_r.trend,
                "liquidity": ads_r.liquidity,
                "microstructure": ads_r.microstructure,
                "confidence": ads_r.confidence,
            },
            "ads_regime_vector_obj": ads_r,
            "ads_fallbacks_used": diag.get("used", []),
            "ads_diag": diag
        }

    def _calculate_ads_context(
        self,
        symbol: str,
        data: pd.DataFrame,
        idx: int,
        side: str,
        raw_strength: float = 1.0
    ) -> Dict[str, Any]:
        """
        Consolidate logic for ADS v3.1 gates (SMS/ERAR) to resolve logic overlays.
        """
        row = data.iloc[idx]
        actual_idx = idx if idx >= 0 else len(data) + idx

        # 1. SMS Components
        composite_z = float(row.get("composite_z", 0.0))
        composite_pct_raw = float(row.get("composite_pct", 0.0))
        composite_pct = self._normalize_composite_pct(composite_pct_raw)

        thresholds = self._get_regime_adjusted_thresholds(symbol, row if isinstance(row, pd.Series) else pd.Series())
        z_thresh = float(thresholds.get("long_threshold", getattr(self.config, "composite_z_entry", 1.0)))
        pct_thresh = float(thresholds.get("pct_threshold", getattr(self.config, "composite_pct_entry", 70.0)))

        z_margin = max(0.0, (abs(composite_z) - z_thresh) / max(z_thresh, 1e-6))
        z_maturity = 1.0 - float(np.exp(-2.0 * z_margin))
        pct_margin = max(0.0, (composite_pct - pct_thresh) / max(100.0 - pct_thresh, 1.0))
        pct_maturity = 1.0 - float(np.exp(-2.0 * pct_margin))

        structure_q = 0.5
        try:
            if actual_idx >= 5:
                sd = self._detect_price_structure(symbol, data, actual_idx, lookback=5)
                structure_q = float(sd.get("structure_quality", 0.5))
        except Exception:
            structure_q = 0.5

        exhaustion = float(np.clip((max(z_maturity, 1e-3) * max(pct_maturity, 1e-3) * (0.5 + 0.5 * structure_q)) ** (1 / 3), 0.0, 1.0))

        # Reversal Prob
        rsi_col = self._get_column_name("RSI_14", data)
        rsi = float(row.get(rsi_col, row.get("rsi", 50.0)))
        if side == "BUY":
            p_rev_rsi = 1.0 / (1.0 + float(np.exp(-(rsi - float(getattr(self.config, "rsi_overbought", 70.0))) / 5.0)))
        else:
            p_rev_rsi = 1.0 / (1.0 + float(np.exp(-(float(getattr(self.config, "rsi_oversold", 30.0)) - rsi) / 5.0)))
        reversal_prob = float(np.clip(1.0 - p_rev_rsi, 0.001, 1.0))

        # OFI Proxy
        vol_ratio = float(row.get("volume_ratio", 1.0))
        sign = 1.0 if side == "BUY" else -1.0
        ofi_shift = float(np.clip((vol_ratio - 1.0) * sign, -1.0, 1.0))

        # Vol Compression
        vol_comp = 1.0
        try:
            if "close" in data.columns and actual_idx >= 20:
                prices = data["close"].iloc[max(0, actual_idx - 20) : actual_idx + 1]
                rets = prices.pct_change()
                short_vol = float(rets.tail(5).std()) if len(rets) >= 5 else 0.02
                long_vol = float(rets.std()) if len(rets) >= 10 else 0.02
                if short_vol > 0:
                    vol_comp = float(np.clip(long_vol / short_vol, 0.5, 2.0))
        except Exception:
            vol_comp = 1.0

        # SMS Score logic (consolidated)
        tau_0 = float(getattr(self.config, "tau_0", 0.50))
        tau = float(np.clip(
            0.4 * (1.0 - exhaustion) + 
            0.3 * (1.0 - reversal_prob) + 
            0.2 * ofi_shift + 
            0.1 * vol_comp, 
            0.0, 1.0))
        
        # Adjust tau based on tau_0 baseline
        tau = min(0.9, max(0.1, tau * (tau_0 / 0.5)))
        
        # Get regime label for stateful SMS if needed, but for context we compute a snapshot score
        ads_r = thresholds.get("ads_regime_vector_obj")
        regime_label = self._sms_regime_label(ads_r)
        
        sms_score = float(np.clip(0.5 * tau + 0.5 * raw_strength, 0.0, 1.0))

        # 2. ERAR Components
        price = float(row.get("close", 0.0))
        atr_col = self._get_column_name("ATR_14", data)
        atr = float(row.get(atr_col, row.get("atr", 0.0)))
        volatility = (atr / price) if (price > 0 and atr > 0) else 0.02
        holding_minutes = float(getattr(self.config, "time_stop_minutes", 90))
        holding_days = max(0.05, min(1.0, holding_minutes / 390.0))

        edge_strength = float(np.clip(0.6 * raw_strength + 0.4 * max(z_maturity, pct_maturity), 0.0, 1.0))
        expected_move = atr * (0.35 + 0.95 * edge_strength)
        expected_pnl_bps = (expected_move / price) * 10000 if price > 0 else 0.0

        cvar_95_bps = estimate_cvar_95(volatility=volatility, holding_days=holding_days)
        erar = ERAR(
            expected_pnl=float(expected_pnl_bps),
            cvar_95=float(cvar_95_bps),
            skewness=0.0,
            spread_bps=float(getattr(self.config, "spread_bps", 2.0)),
            participation=0.01,
            volatility=float(volatility),
            adverse_prob=0.1,
            kyle_lambda=0.0001,
            holding_days=float(holding_days),
            alt_return_bps=float(getattr(self.config, "alt_return_bps", 0.5)),
            tail_lambda=float(getattr(self.config, "erar_tail_lambda", 1.0)),
        )

        return {
            "composite_z": composite_z,
            "composite_pct": composite_pct,
            "exhaustion": exhaustion,
            "reversal_prob": reversal_prob,
            "ofi_shift": ofi_shift,
            "vol_compression": vol_comp,
            "tau": tau,
            "sms": sms_score,
            "regime_label": regime_label,
            "erar": erar,
            "erar_val": float(erar.compute()),
            "z_maturity": z_maturity,
            "pct_maturity": pct_maturity,
            "ads_regime_vector": thresholds.get("ads_regime_vector", {}),
            "ads_regime_vector_obj": ads_r,
            "ads_fallbacks_used": thresholds.get("ads_fallbacks_used", []),
            "ads_diag": thresholds.get("ads_diag", {}),
            "thresholds": thresholds
        }

    # ========================================
    # NEW: COMPOSITE SIGNAL ENTRY LOGIC (Phase 4A)
    # ========================================

    def _check_composite_entry(
        self,
        symbol: str,
        current_bar: pd.Series,
        enriched_data: pd.DataFrame = None,
        current_idx: int = None
    ) -> Tuple[bool, Optional[SignalType]]:
        """
        Check composite signal entry conditions with CRITICAL FIXES applied
        """

        # FIXED: HIGH #3 - Narrow exception handling for specific errors
        try:
            # Get composite signals
            composite_z = current_bar.get('composite_z', None)
            composite_pct = current_bar.get('composite_pct', None)
        except (KeyError, AttributeError) as e:
            logger.error(f"  [{symbol}] Missing required columns in current_bar: {e}")
            raise  # Re-raise to surface data pipeline issues
        except Exception:
            logger.exception(f"  [{symbol}] Unexpected error getting composite signals")
            raise  # Don't mask unexpected errors

        # Check 1: Is composite_z valid?
        if composite_z is None or pd.isna(composite_z) or composite_pct is None or pd.isna(composite_pct):
            # Fallback: some enrichment pipelines may not emit composite_z/composite_pct.
            # For smoke tests, compute a minimal composite signal from price history so the
            # state machine can be exercised deterministically.
            if enriched_data is not None and current_idx is not None:
                cz, cp = self._fallback_compute_composite_signals(enriched_data, current_idx)
                if cz is not None and cp is not None:
                    composite_z = cz
                    composite_pct = cp
                else:
                    return False, None
            else:
                return False, None

        # Normalize composite_pct to [0, 100] (handles signed [-1,1] pipelines too)
        composite_pct = self._normalize_composite_pct(composite_pct)

        # Base thresholds come from centralized config (do not hardcode)
        BASE_LONG_THRESHOLD = float(getattr(self.config, "composite_z_entry", 1.0))
        BASE_SHORT_THRESHOLD = float(getattr(self.config, "composite_z_entry", 1.0))
        BASE_PCT_THRESHOLD = float(getattr(self.config, "composite_pct_entry", 70.0))

        # ADS v3.1: Get regime-adjusted thresholds from continuous regime vector R
        thresholds = self._get_regime_adjusted_thresholds(symbol, current_bar)

        # Fully adjusted thresholds (no regime_multiplier indirection)
        long_threshold = float(thresholds.get("long_threshold", BASE_LONG_THRESHOLD))
        short_threshold = float(thresholds.get("short_threshold", BASE_SHORT_THRESHOLD))
        pct_threshold = float(thresholds.get("pct_threshold", BASE_PCT_THRESHOLD))
        adjustment_reason = thresholds.get("adjustment_reason", "none")

        # CRITICAL FIX #2: Pre-Inflection Detection
        inflection_data = None
        if enriched_data is not None and current_idx is not None:
            inflection_data = self._detect_momentum_inflection(
                symbol, enriched_data, current_idx, lookback=5
            )
            logger.debug(f"  [{symbol}] Inflection: detected={inflection_data.get('inflection_detected')}, "
                        f"type={inflection_data.get('inflection_type')}, "
                        f"slope={inflection_data.get('momentum_slope'):.4f}, "
                        f"accel={inflection_data.get('momentum_accel'):.4f}")

        # CRITICAL FIX #4: Price Structure Detection
        structure_data = None
        if enriched_data is not None and current_idx is not None:
            structure_data = self._detect_price_structure(
                symbol, enriched_data, current_idx, lookback=5
            )
            logger.debug(f"  [{symbol}] Structure: type={structure_data.get('structure_type')}, "
                        f"quality={structure_data.get('structure_quality'):.2f}, "
                        f"pivot={structure_data.get('pivot_confirmed')}, "
                        f"basing={structure_data.get('basing_detected')}")

        # CRITICAL FIX #5: Fast Momentum Slope (replaces slow ADX)
        momentum_slope = 0.0
        if enriched_data is not None and current_idx is not None:
            momentum_slope = self._calculate_momentum_slope(
                symbol, enriched_data, current_idx, lookback=3
            )
            logger.debug(f"  [{symbol}] Momentum slope: {momentum_slope:.4f}")

        # LONG entry: Composite threshold + structure + momentum
        long_condition_met = (
            composite_z > long_threshold and
            composite_pct > pct_threshold and
            momentum_slope > 0  # NEW: Momentum must be trending up
        )

        # Add inflection boost (allows earlier entry if inflection detected)
        if inflection_data and inflection_data.get('inflection_detected') and inflection_data.get('inflection_type') == 'bullish':
            logger.info(f"  [{symbol}] BULLISH INFLECTION DETECTED - boosting entry confidence")
            long_condition_met = (
                composite_z > long_threshold * 0.8 and  # 20% lower threshold if inflection
                composite_pct > pct_threshold * 0.9 and  # 10% lower percentile
                inflection_data.get('momentum_accel', 0) > 0
            )

        # Add structure validation (prefer higher lows or pivot confirmation)
        if structure_data:
            structure_confirms_long = (
                structure_data.get('structure_type') == 'higher_lows' or
                structure_data.get('pivot_confirmed') or
                structure_data.get('basing_detected')
            )
            if not structure_confirms_long:
                logger.debug(f"    [{symbol}] LONG: Weak price structure, reducing confidence")
                long_condition_met = long_condition_met and composite_z > long_threshold * 1.2  # Require stronger signal

        # SHORT entry: Composite threshold + structure + momentum
        short_condition_met = (
            composite_z < -short_threshold and
            composite_pct < (100 - pct_threshold) and
            momentum_slope < 0  # NEW: Momentum must be trending down
        )

        # Add inflection boost for shorts
        if inflection_data and inflection_data.get('inflection_detected') and inflection_data.get('inflection_type') == 'bearish':
            logger.info(f"  [{symbol}] BEARISH INFLECTION DETECTED - boosting entry confidence")
            short_condition_met = (
                composite_z < -short_threshold * 0.8 and
                composite_pct < (100 - pct_threshold * 0.9) and
                inflection_data.get('momentum_accel', 0) < 0
            )

        # Add structure validation for shorts
        if structure_data:
            structure_confirms_short = (
                structure_data.get('structure_type') == 'lower_highs' or
                structure_data.get('pivot_confirmed')
            )
            if not structure_confirms_short:
                logger.debug(f"    [{symbol}] SHORT: Weak price structure, reducing confidence")
                short_condition_met = short_condition_met and composite_z < -short_threshold * 1.2

        if long_condition_met:
            return True, SignalType.LONG_ENTRY
        if short_condition_met:
            return True, SignalType.SHORT_ENTRY

        return False, None

    # ========================================
    # POSITION TRACKING & EXIT LOGIC
    # ========================================

    async def _check_exit_conditions_hybrid(
        self,
        symbol: str,
        enriched_data: pd.DataFrame,
        bar_timestamp: datetime
    ) -> Tuple[bool, Optional[str]]:
        """
        Check hybrid exit conditions for active position (Phase 3)
        """

        # Check if we have a position
        pos_info = self._get_position_info(symbol)
        if not pos_info:
            return False, None

        # Get current bar data
        if bar_timestamp not in enriched_data.index:
            logger.warning(f"    {symbol} bar timestamp {bar_timestamp} not in enriched_data")
            return False, None

        current_bar = enriched_data.loc[bar_timestamp]
        current_price = current_bar['close']

        # Priority 1: ATR-based stops (hard stops)
        should_exit, exit_reason = self._check_atr_stops(
            symbol, pos_info, current_price, current_bar
        )
        if should_exit:
            return True, exit_reason

        # Priority 2: Composite signal exits (momentum deterioration - CRITICAL FIXES applied)
        should_exit, exit_reason = self._check_composite_exits(
            symbol, pos_info, current_bar,
            enriched_data=enriched_data,
            current_idx=enriched_data.index.get_loc(bar_timestamp) if bar_timestamp in enriched_data.index else None
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
        1. Initial stop: entry_price +/- (atr_initial_stop_multiple * ATR)
        2. Trailing stop: activated after profit > atr_trailing_activation * ATR

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
        pos_info['trailing_stop_activated']

        # Get ATR
        atr = current_bar.get('ATR_14', current_bar.get('atr', None))
        if atr is None or pd.isna(atr):
            logger.warning(f"    {symbol} ATR not available for stop calculation")
            return False, None

        # LONG position exits
        if direction == 1:
            # Initial stop (hard stop)
            initial_stop = entry_price - (self.config.atr_initial_stop_multiple * atr)
            if current_price <= initial_stop:
                logger.info(f"  {symbol} LONG hit initial stop: ${current_price:.2f} <= ${initial_stop:.2f}")
                return True, "atr_initial_stop"

            # Trailing stop (profit protection)
            profit_atr = (high_water_mark - entry_price) / atr
            if profit_atr >= self.config.atr_trailing_activation:
                trailing_stop = high_water_mark - (self.config.atr_trailing_distance * atr)
                if current_price <= trailing_stop:
                    logger.info(f"  {symbol} LONG hit trailing stop: ${current_price:.2f} <= ${trailing_stop:.2f}")
                    return True, "atr_trailing_stop"

        # SHORT position exits
        elif direction == -1:
            # Initial stop (hard stop)
            initial_stop = entry_price + (self.config.atr_initial_stop_multiple * atr)
            if current_price >= initial_stop:
                logger.info(f"  {symbol} SHORT hit initial stop: ${current_price:.2f} >= ${initial_stop:.2f}")
                return True, "atr_initial_stop"

            # Trailing stop (profit protection)
            profit_atr = (entry_price - high_water_mark) / atr
            if profit_atr >= self.config.atr_trailing_activation:
                trailing_stop = high_water_mark + (self.config.atr_trailing_distance * atr)
                if current_price >= trailing_stop:
                    logger.info(f"  {symbol} SHORT hit trailing stop: ${current_price:.2f} >= ${trailing_stop:.2f}")
                    return True, "atr_trailing_stop"

        return False, None

    def _check_composite_exits(
        self,
        symbol: str,
        pos_info: Dict[str, Any],
        current_bar: pd.Series,
        enriched_data: pd.DataFrame = None,
        current_idx: int = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Check composite signal exit conditions with CRITICAL FIX #1 applied

        CRITICAL FIX #1: Entry/Exit Symmetry
        - Exit threshold NOW SYMMETRIC with entry threshold
        - Entry at Z=1.0, Exit at Z=0.6 (0.6 times entry, was 0.3 times before)
        - Added momentum acceleration check (must be negative to exit)

        Exit triggers (SYMMETRIC with entry):
        1. Composite Z-score falls below 0.6 (60% of entry threshold 1.0)
        2. Composite percentile falls below 40% (was 30%, now higher)
        3. Momentum acceleration < 0 (NEW: momentum must be decelerating)
        4. Momentum slope < 0 (NEW: momentum must be trending down)

        Args:
            symbol: Trading symbol
            pos_info: Position information
            current_bar: Current bar data
            enriched_data: Full enriched DataFrame (for momentum acceleration)
            current_idx: Current bar index (for momentum acceleration)

        Returns:
            Tuple[should_exit, exit_reason]
        """

        # Get composite signals
        composite_z = current_bar.get('composite_z', None)
        composite_pct = current_bar.get('composite_pct', None)

        if composite_z is None or pd.isna(composite_z):
            logger.debug(f"    {symbol} composite_z not available for exit check")
            return False, None

        if composite_pct is None or pd.isna(composite_pct):
            logger.debug(f"    {symbol} composite_pct not available for exit check")
            return False, None

        # Normalize composite_pct to [0, 100] (Rule 3)
        composite_pct = self._normalize_composite_pct(composite_pct)

        direction = pos_info['direction']

        # CRITICAL FIX #1: Symmetric exit thresholds
        # Entry is at Z=1.0, Exit at Z=0.6 (maintains 40% buffer zone)
        EXIT_Z_THRESHOLD = 0.6  # Was 0.5, now 0.6 (60% of entry threshold 1.0)
        EXIT_PCT_THRESHOLD = 40.0  # Was 30%, now 40% (more conservative)

        # CRITICAL FIX #2: Get momentum acceleration for exit validation
        momentum_accel = 0.0
        momentum_slope = 0.0
        if enriched_data is not None and current_idx is not None:
            inflection_data = self._detect_momentum_inflection(
                symbol, enriched_data, current_idx, lookback=5
            )
            momentum_accel = inflection_data.get('momentum_accel', 0.0)
            momentum_slope = inflection_data.get('momentum_slope', 0.0)

        logger.debug(f"  [{symbol}] Exit check: Z={composite_z:.4f}, "
                    f"pct={composite_pct:.1f}%, accel={momentum_accel:.4f}, "
                    f"slope={momentum_slope:.4f}")

        # LONG position: exit if momentum deteriorates
        if direction == 1:
            # Primary exit: Z-score decay + momentum deceleration
            if composite_z < EXIT_Z_THRESHOLD and momentum_accel < 0:
                logger.info(f"  {symbol} LONG composite_z exit: {composite_z:.2f} < {EXIT_Z_THRESHOLD:.2f} "
                           f"AND momentum_accel < 0 ({momentum_accel:.4f})")
                return True, "composite_z_momentum_decay"

            # Secondary exit: Percentile decay + momentum turning down
            if composite_pct < EXIT_PCT_THRESHOLD and momentum_slope < 0:
                logger.info(f"  {symbol} LONG composite_pct exit: {composite_pct:.1f} < {EXIT_PCT_THRESHOLD:.1f} "
                           f"AND momentum_slope < 0 ({momentum_slope:.4f})")
                return True, "composite_pct_momentum_decay"

            # Aggressive exit: Both Z and percentile weak + strong deceleration
            if composite_z < EXIT_Z_THRESHOLD * 1.2 and composite_pct < EXIT_PCT_THRESHOLD * 1.2 and momentum_accel < -0.002:
                logger.info(f"  {symbol} LONG aggressive exit: weak signals + strong deceleration")
                return True, "composite_aggressive_decay"

        # SHORT position: exit if momentum strengthens (opposite)
        elif direction == -1:
            # Primary exit: Z-score rises + momentum accelerates upward
            if composite_z > -EXIT_Z_THRESHOLD and momentum_accel > 0:
                logger.info(f"  {symbol} SHORT composite_z exit: {composite_z:.2f} > {-EXIT_Z_THRESHOLD:.2f} "
                           f"AND momentum_accel > 0 ({momentum_accel:.4f})")
                return True, "composite_z_momentum_reversal"

            # Secondary exit: Percentile rises + momentum turning up
            if composite_pct > (100 - EXIT_PCT_THRESHOLD) and momentum_slope > 0:
                logger.info(f"  {symbol} SHORT composite_pct exit: {composite_pct:.1f} > {100 - EXIT_PCT_THRESHOLD:.1f} "
                           f"AND momentum_slope > 0 ({momentum_slope:.4f})")
                return True, "composite_pct_momentum_reversal"

            # Aggressive exit: Both weak + strong upward acceleration
            if composite_z > -EXIT_Z_THRESHOLD * 1.2 and composite_pct > (100 - EXIT_PCT_THRESHOLD * 1.2) and momentum_accel > 0.002:
                logger.info(f"  {symbol} SHORT aggressive exit: weak signals + strong upward acceleration")
                return True, "composite_aggressive_reversal"

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
            logger.info(f"  {symbol} max holding period: {holding_minutes:.1f}min >= {self.config.time_stop_minutes}min")
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
            logger.debug(f"    {symbol} volume_ratio not available for exit check")
            return False, None

        # Check if volume is too low
        if volume_ratio < self.config.volume_failure_multiplier:
            logger.info(f"  {symbol} volume failure: {volume_ratio:.2f} < {self.config.volume_failure_multiplier:.2f}")
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
        if direction == 1:  # LONG position   SELL signal
            signal_type = SignalType.LONG_EXIT
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
        else:  # SHORT position   BUY signal (cover)
            signal_type = SignalType.SHORT_EXIT
            pnl_pct = ((entry_price - current_price) / entry_price) * 100

        # Create exit signal
        exit_signal = StrategySignal(
            strategy_id=self.strategy_id,
            symbol=symbol,
            signal_type=signal_type,
            strength=1.0,  # Exits are strong signals (max strength)
            confidence=0.9,  # High confidence for exits
            target_quantity=float(quantity),
            quantity_type="ABSOLUTE",
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

        logger.info(f"  Exit signal generated: {symbol} {signal_type.value} {quantity:.2f} @ ${current_price:.2f} | "
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

        # ADS v3.1: Retrieve active positions from PositionBook SSOT
        active_positions = {}
        if hasattr(self, '_position_book') and self._position_book:
            for symbol, pos in self._position_book.get_all_positions().items():
                active_positions[symbol] = {
                    'direction': 1 if pos.is_long else -1 if pos.is_short else 0,
                    'avg_entry_price': float(pos.avg_entry_price),
                    'total_quantity': float(pos.quantity),
                    'entry_time': pos.opened_at.isoformat() if hasattr(pos, 'opened_at') and pos.opened_at else datetime.now().isoformat(),
                    'current_price': float(pos.current_price)
                }

        summary = {
            'strategy_id': self.strategy_id,
            'strategy_type': 'Enhanced Momentum',
            'symbols_tracked': len(self.config.symbols),
            'active_positions': len(active_positions),
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
            'position_details': active_positions
        }
        return summary

    # ========================================
    # CRITICAL FIX #1-3: MICRO-STRUCTURE & PRE-INFLECTION DETECTION
    # ========================================

    def _detect_momentum_inflection(
        self,
        symbol: str,
        enriched_data: pd.DataFrame,
        current_idx: int,
        lookback: int = 5
    ) -> Dict[str, Any]:
        """
        Detect momentum inflection points (pre-acceleration triggers)

        CRITICAL FIX #2: Pre-Inflection Entry Triggers

        Detects:
        1. Momentum slope changes (derivative sign flip)
        2. Momentum acceleration (2nd derivative positive)
        3. Volatility compression   expansion transitions

        Returns:
            Dict with:
            - inflection_detected: bool
            - inflection_type: 'bullish' or 'bearish'
            - momentum_slope: float (1st derivative)
            - momentum_accel: float (2nd derivative)
            - vol_expansion: bool
        """

        try:
            if current_idx < lookback + 2:
                return {
                    'inflection_detected': False,
                    'inflection_type': None,
                    'momentum_slope': 0.0,
                    'momentum_accel': 0.0,
                    'vol_expansion': False
                }

            # Get momentum series (use short-term momentum for faster response)
            momentum_col = f'momentum_{self.config.short_period}'
            if momentum_col not in enriched_data.columns:
                # Fallback to composite_z
                momentum_series = enriched_data['composite_z'].iloc[current_idx - lookback:current_idx + 1]
            else:
                momentum_series = enriched_data[momentum_col].iloc[current_idx - lookback:current_idx + 1]

            if len(momentum_series) < 3:
                return {
                    'inflection_detected': False,
                    'inflection_type': None,
                    'momentum_slope': 0.0,
                    'momentum_accel': 0.0,
                    'vol_expansion': False
                }

            # Calculate 1st derivative (momentum slope)
            momentum_slope = momentum_series.diff().iloc[-1]

            # Calculate 2nd derivative (momentum acceleration)
            momentum_accel = momentum_series.diff().diff().iloc[-1]

            # Detect volatility compression   expansion
            vol_col = 'volatility_10' if 'volatility_10' in enriched_data.columns else 'ATR_14'
            if vol_col in enriched_data.columns:
                vol_series = enriched_data[vol_col].iloc[current_idx - lookback:current_idx + 1]
                vol_current = vol_series.iloc[-1]
                vol_avg = vol_series.iloc[:-1].mean()
                vol_expansion = vol_current > vol_avg * 1.15  # 15% expansion threshold
            else:
                vol_expansion = False

            # Inflection detection logic
            inflection_detected = False
            inflection_type = None

            # BULLISH INFLECTION: Momentum was negative/flat, now accelerating upward
            if momentum_accel > 0.001 and momentum_slope > 0:
                prev_momentum = momentum_series.iloc[-3:-1].mean()
                current_momentum = momentum_series.iloc[-1]

                # Check if momentum flipped from negative to positive (true inflection)
                if prev_momentum <= 0 and current_momentum > 0:
                    inflection_detected = True
                    inflection_type = 'bullish'
                # Or if momentum was weak and now strengthening rapidly
                elif abs(prev_momentum) < 0.5 and current_momentum > prev_momentum * 1.5:
                    inflection_detected = True
                    inflection_type = 'bullish'

            # BEARISH INFLECTION: Momentum was positive/flat, now decelerating downward
            elif momentum_accel < -0.001 and momentum_slope < 0:
                prev_momentum = momentum_series.iloc[-3:-1].mean()
                current_momentum = momentum_series.iloc[-1]

                # Check if momentum flipped from positive to negative
                if prev_momentum >= 0 and current_momentum < 0:
                    inflection_detected = True
                    inflection_type = 'bearish'
                # Or if momentum was strong and now weakening rapidly
                elif abs(prev_momentum) > 0.5 and current_momentum < prev_momentum * 0.5:
                    inflection_detected = True
                    inflection_type = 'bearish'

            logger.debug(f"[{symbol}] Inflection check: slope={momentum_slope:.4f}, "
                        f"accel={momentum_accel:.4f}, detected={inflection_detected}, "
                        f"type={inflection_type}")

            return {
                'inflection_detected': inflection_detected,
                'inflection_type': inflection_type,
                'momentum_slope': float(momentum_slope),
                'momentum_accel': float(momentum_accel),
                'vol_expansion': vol_expansion
            }

        except Exception as e:
            logger.error(f"[{symbol}] Inflection detection failed: {e}")
            return {
                'inflection_detected': False,
                'inflection_type': None,
                'momentum_slope': 0.0,
                'momentum_accel': 0.0,
                'vol_expansion': False
            }

    def _detect_price_structure(
        self,
        symbol: str,
        enriched_data: pd.DataFrame,
        current_idx: int,
        lookback: int = 5
    ) -> Dict[str, Any]:
        """
        Detect price micro-structure patterns (higher lows, lower highs, pivots)

        CRITICAL FIX #4: Price-Path Awareness

        Detects:
        1. Higher lows sequence (bullish structure)
        2. Lower highs sequence (bearish structure)
        3. Pivot lows/highs validation
        4. Micro-pullback detection

        Returns:
            Dict with:
            - structure_type: 'higher_lows', 'lower_highs', 'ranging', 'choppy'
            - structure_quality: float (0-1, higher = cleaner structure)
            - pivot_confirmed: bool
            - last_pivot_distance: float (ATR units from current price)
        """

        try:
            if current_idx < lookback + 2:
                return {
                    'structure_type': 'unknown',
                    'structure_quality': 0.0,
                    'pivot_confirmed': False,
                    'last_pivot_distance': 0.0,
                    'basing_detected': False
                }

            # Get price data
            price_data = enriched_data.iloc[current_idx - lookback:current_idx + 1]
            lows = price_data['low'].values
            highs = price_data['high'].values
            closes = price_data['close'].values

            # Detect higher lows (bullish structure)
            higher_lows_count = 0
            for i in range(1, len(lows)):
                if lows[i] > lows[i-1]:
                    higher_lows_count += 1

            # Detect lower highs (bearish structure)
            lower_highs_count = 0
            for i in range(1, len(highs)):
                if highs[i] < highs[i-1]:
                    lower_highs_count += 1

            # Determine structure type
            structure_quality = 0.0
            if higher_lows_count >= lookback * 0.6:  # 60% higher lows
                structure_type = 'higher_lows'
                structure_quality = higher_lows_count / (lookback - 1)
            elif lower_highs_count >= lookback * 0.6:  # 60% lower highs
                structure_type = 'lower_highs'
                structure_quality = lower_highs_count / (lookback - 1)
            elif higher_lows_count == lower_highs_count:
                structure_type = 'ranging'
                structure_quality = 0.5
            else:
                structure_type = 'choppy'
                structure_quality = 0.3

            # Detect pivot validation (local extrema)
            current_price = closes[-1]
            recent_low = lows.min()
            recent_high = highs.max()

            # Pivot confirmed if current price is near recent high (for longs)
            # or near recent low (for shorts)
            pivot_confirmed = False
            if structure_type == 'higher_lows' and current_price > recent_high * 0.98:
                pivot_confirmed = True
            elif structure_type == 'lower_highs' and current_price < recent_low * 1.02:
                pivot_confirmed = True

            # Calculate distance from last pivot in ATR units
            atr = price_data['ATR_14'].iloc[-1] if 'ATR_14' in price_data.columns else (recent_high - recent_low)
            if structure_type == 'higher_lows':
                last_pivot_distance = (current_price - recent_low) / atr if atr > 0 else 0
            else:
                last_pivot_distance = (recent_high - current_price) / atr if atr > 0 else 0

            # Detect basing (consolidation before breakout)
            price_range = (highs.max() - lows.min()) / closes.mean()
            basing_detected = price_range < 0.02  # Less than 2% range = basing

            logger.debug(f"[{symbol}] Structure: type={structure_type}, quality={structure_quality:.2f}, "
                        f"pivot={pivot_confirmed}, basing={basing_detected}")

            return {
                'structure_type': structure_type,
                'structure_quality': float(structure_quality),
                'pivot_confirmed': pivot_confirmed,
                'last_pivot_distance': float(last_pivot_distance),
                'basing_detected': basing_detected
            }

        except Exception as e:
            logger.error(f"[{symbol}] Price structure detection failed: {e}")
            return {
                'structure_type': 'unknown',
                'structure_quality': 0.0,
                'pivot_confirmed': False,
                'last_pivot_distance': 0.0,
                'basing_detected': False
            }

    def _calculate_momentum_slope(
        self,
        symbol: str,
        enriched_data: pd.DataFrame,
        current_idx: int,
        lookback: int = 3
    ) -> float:
        """
        Calculate fast momentum slope (replaces slow ADX)

        CRITICAL FIX #5: Faster Trend Indicator

        Uses simple linear regression of momentum over lookback period
        Returns slope coefficient (positive = upward momentum, negative = downward)
        """

        try:
            if current_idx < lookback:
                return 0.0

            # Get momentum series
            momentum_col = f'momentum_{self.config.short_period}'
            if momentum_col not in enriched_data.columns:
                # Fallback to composite_z
                if 'composite_z' in enriched_data.columns:
                    momentum_series = enriched_data['composite_z'].iloc[current_idx - lookback + 1:current_idx + 1]
                else:
                    return 0.0
            else:
                momentum_series = enriched_data[momentum_col].iloc[current_idx - lookback + 1:current_idx + 1]

            if len(momentum_series) < 2:
                return 0.0

            # Simple linear regression: y = mx + b (we only need slope m)
            x = np.arange(len(momentum_series))
            y = momentum_series.values

            # Calculate slope using least squares
            x_mean = x.mean()
            y_mean = y.mean()

            numerator = ((x - x_mean) * (y - y_mean)).sum()
            denominator = ((x - x_mean) ** 2).sum()

            slope = numerator / denominator if denominator != 0 else 0.0

            return float(slope)

        except Exception as e:
            logger.error(f"[{symbol}] Momentum slope calculation failed: {e}")
            return 0.0