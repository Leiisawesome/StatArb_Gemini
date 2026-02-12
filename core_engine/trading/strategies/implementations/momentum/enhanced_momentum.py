"""
Enhanced Momentum Strategy with ISystemComponent Integration
==========================================================

Professional momentum strategy that implements ISystemComponent interface
for seamless orchestrator integration and institutional-grade lifecycle management.

This enhanced strategy provides:
- ISystemComponent interface compliance
- Multi-timeframe momentum analysis
- Trend strength and quality assessment
- Strategy emits trade intent only (Rule 7); sizing/authorization/exits are handled by CentralRiskManager
- Comprehensive performance tracking

Key Features:
- Multi-timeframe momentum confirmation
- Trend quality assessment using ADX
- Volume confirmation for momentum signals
- Breakout detection and momentum continuation
- Entry-intent signal construction with diagnostics for monitoring

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
import math
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import logging

# Professional re-architecture imports
from .momentum_state_machine import MomentumStateMachine

# Import enhanced base strategy
from ...base_strategy_enhanced import EnhancedBaseStrategy
from ...contracts import StrategySignal
from core_engine.type_definitions.strategy import SignalType

# ADS v3.1: continuous regime vector + tau(R)
from core_engine.alpha.ads_regime_vector import ADSRegimeVector, compute_sms_tau
from core_engine.alpha.ads_components import (
    ADSSMSGateInputs,
    PendingSignalQueue,
    PendingSignalContext,
    SignalMaturityScore,
    SequentialLogOddsSMS,
    ERAR,
    estimate_cvar_95,
    compute_vol_compression,
)

# Import centralized configuration (Rule 1 Section 7 - Configuration Management)
# REQUIRED: Use centralized config only - no local fallback definitions per Rule 1
from core_engine.config import MomentumConfig

# Skeleton utilities (Rule 7): schema compatibility glue lives outside core alpha.
from core_engine.trading.strategies.skeleton.enriched_data_utils import (
    extract_momentum_indicator_series,
    momentum_default_column_mapping,
    resolve_expected_or_mapped_column,
    validate_required_indicator_columns,
)
from core_engine.trading.strategies.skeleton.bar_scanner import scan_bars_at_interval
from core_engine.trading.strategies.skeleton.composite_feature_utils import (
    CompositeFallbackParams,
    fallback_compute_composite_signals,
    normalize_composite_pct,
)
from core_engine.trading.strategies.skeleton.ads_sms_utils import (
    sms_regime_label_from_ads_vector,
    compute_sms_info_increment,
)
from core_engine.trading.strategies.skeleton.ads_regime_adapter import ADSRegimeVectorCache
from core_engine.trading.strategies.skeleton.data_quality_utils import is_ffill_stale
from core_engine.trading.strategies.skeleton.dataframe_utils import extract_bar_timestamp, safe_iloc
from core_engine.trading.strategies.skeleton.signal_type_utils import side_from_signal

logger = logging.getLogger(__name__)

class MomentumSignal(Enum):
    """Momentum signal types"""
    BULLISH_MOMENTUM = "bullish_momentum"
    BEARISH_MOMENTUM = "bearish_momentum"

# Note: MomentumConfig now imported from core_engine.config (Rule 1 Section 7)
# Local definition removed - use centralized configuration

class EnhancedMomentumStrategy(EnhancedBaseStrategy):
    """
    Enhanced Momentum Strategy with ISystemComponent Integration

    Professional momentum strategy that provides:
    - ISystemComponent interface compliance
    - Multi-timeframe momentum analysis
    - Trend strength and quality assessment
    - Trade intent generation only (Rule 7); sizing/authorization/exits are handled by CentralRiskManager
    - Comprehensive performance tracking (skeleton) + diagnostics in intent additional_data (alpha)
    """

    def __init__(self, config: MomentumConfig):
        """Initialize enhanced momentum strategy"""
        # Initialize base strategy
        super().__init__(config)
        self.config: MomentumConfig = config

        # Strategy-specific state
        self.indicators: Dict[str, Dict[str, pd.Series]] = {}
        self.momentum_data: Dict[str, Dict[str, float]] = {}

        # State Machine (Professional re-architecture)
        self.state_machine = MomentumStateMachine()

        # ADS v3.1: pending signal queue (SMS maturation) + per-symbol regime vector memory
        self.pending_signals = PendingSignalQueue(
            max_pending=getattr(config, "sms_max_pending", 50)
        )
        self._ads_regime_cache = ADSRegimeVectorCache()

        # FIXED: MED #8 - Cache column mapping for performance
        self._column_mapping_cache = momentum_default_column_mapping()

        # Avoid noisy init logs from inside alpha implementations; skeleton/orchestrator can own lifecycle logging.

        # Diagnostics: summarize why the state machine didn't trigger entries (no per-bar spam).
        self._sm_entry_reasons: Dict[str, int] = {}
        self._sm_entries_triggered: int = 0

        # MQS v3.3: per-bar microstructure quality state (reset each evaluation)
        self._current_mqs: float = 1.0
        self._current_mqs_penalty: float = 1.0

    @staticmethod
    def _normalize_composite_pct(x: float) -> float:
        """
        Normalize composite_pct into [0, 100].

        Runtime evidence shows some pipelines emit composite_pct in [-1, 1] (signed scale),
        while others may emit [0, 1] or [0, 100]. We normalize conservatively:
          - If -1 <= x <= 1: treat as signed scale and map to [0,100] via (x+1)/2*100.
          - Else: assume already in percent space (best-effort) and clip.
        """
        return normalize_composite_pct(x)

    def _passes_trend_persistence_filter(
        self,
        data: pd.DataFrame,
        idx: int,
        side: str,
    ) -> bool:
        """
        Core-alpha filter: require recent return signs to persist in the intended direction.
        """
        if not bool(getattr(self.config, "enable_trend_persistence_filter", False)):
            return True

        lookback = int(getattr(self.config, "trend_persistence_lookback", 10))
        min_ratio = float(getattr(self.config, "trend_persistence_min_ratio", 0.6))
        if lookback <= 1:
            return True

        # Normalize index
        if idx < 0:
            idx = len(data) + idx
        if idx <= 0 or idx >= len(data):
            return True

        try:
            closes = data["close"].iloc[max(0, idx - lookback): idx + 1]
        except Exception:
            return True
        if closes is None or len(closes) < 3:
            return True

        rets = closes.diff().dropna()
        if len(rets) == 0:
            return True

        if side == "BUY":
            favorable = float((rets > 0).sum())
        else:
            favorable = float((rets < 0).sum())

        ratio = favorable / float(len(rets))
        return ratio >= min_ratio

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
        params = CompositeFallbackParams(
            short_period=int(getattr(self.config, "short_period", 10)),
            medium_period=int(getattr(self.config, "medium_period", 20)),
            long_period=int(getattr(self.config, "long_period", 50)),
            lookback_period=int(getattr(self.config, "lookback_period", 60)),
        )
        return fallback_compute_composite_signals(data=data, idx=idx, params=params)

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
            
            # Refresh SMS evidence inputs for the pending signal (strategy-independent contract)
            ctx.sms.inputs = ADSSMSGateInputs(
                setup_maturity=float(ads_ctx["setup_maturity"]),
                setup_validity_prob=float(ads_ctx["setup_validity_prob"]),
                signed_flow_support=float(ads_ctx["signed_flow_support"]),
                vol_compression=float(ads_ctx["vol_compression"]),
                flow_source=str(ads_ctx.get("flow_source", "unknown")),
                diagnostics=dict(ads_ctx.get("sms_diag", {})),
            )
            # Keep legacy aliases in sync for older diagnostics/readers.
            ctx.sms.exhaustion = float(ads_ctx["setup_maturity"])
            ctx.sms.reversal_prob = float(ads_ctx["setup_validity_prob"])
            ctx.sms.ofi_shift = float(ads_ctx["signed_flow_support"])
            ctx.sms.vol_compression = float(ads_ctx["vol_compression"])

            # Tick pending bars + stale kill
            ctx.increment_pending()
            if ctx.sms.is_stale():
                self.pending_signals.remove(symbol, side)
                continue

            # Compute tau(R) from consolidated context
            tau = ads_ctx["tau"]
            regime_label = ads_ctx["regime_label"]
            if ctx.bayes_sms is not None:
                try:
                    prev_row = data.iloc[idx - 1] if idx > 0 else None
                except Exception:
                    prev_row = None

                info_inc = float(
                    compute_sms_info_increment(
                        row=row,
                        prev_row=prev_row,
                        w_volume=float(getattr(self.config, "sms_info_w_volume", 0.55)),
                        w_volatility=float(getattr(self.config, "sms_info_w_volatility", 0.45)),
                        cap=float(getattr(self.config, "sms_info_cap", 3.0)),
                    )
                )
                p_est = float(ctx.bayes_sms.update(ctx.sms.inputs, info_increment=info_inc))

                if ctx.bayes_sms.is_stale():
                    self.pending_signals.remove(symbol, side)
                    continue

                sms_score = p_est
                if not ctx.bayes_sms.is_mature(threshold=float(tau)):
                    ctx.metadata["ads_sms_prob"] = float(p_est)
                    ctx.metadata["ads_sms_log_odds"] = float(ctx.bayes_sms.log_odds)
                    ctx.metadata["ads_sms_info_clock"] = float(ctx.bayes_sms.info_clock)
                    ctx.metadata["ads_sms_info_inc"] = float(info_inc)
                    continue
            else:
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
                "ads_fallbacks": {"ofi_source": ads_ctx.get("txn_flow_source", "proxy_volume_ratio"), "bb_missing": True},
                "txn_ratio": ads_ctx.get("txn_ratio"),
                "txn_ratio_cs_rank": ads_ctx.get("txn_ratio_cs_rank"),
                "avg_trade_size_ratio": ads_ctx.get("avg_trade_size_ratio"),
                "txn_volume_divergence": ads_ctx.get("txn_volume_divergence"),
                "txn_flow_source": ads_ctx.get("txn_flow_source"),
            }
            additional_data.update(
                self._build_hybrid_metadata(
                    signal_source="momentum",
                    strength=float(ctx.raw_signal_strength),
                    side=side,
                    data_row=row,
                    ads_r=ads_ctx.get("ads_regime_vector_obj"),
                )
            )
            if ctx.bayes_sms is not None:
                additional_data.update(
                    {
                        "sms_mode": "bayes_log_odds",
                        "ads_sms_prob": float(ctx.bayes_sms.prob()),
                        "ads_sms_log_odds": float(ctx.bayes_sms.log_odds),
                        "ads_sms_info_clock": float(ctx.bayes_sms.info_clock),
                        "ads_sms_can_mature": bool(ctx.bayes_sms.can_mature()),
                    }
                )
            else:
                additional_data["sms_mode"] = "multiplicative"

            signal_type = SignalType.BUY if side == "BUY" else SignalType.SELL
            # Strategy expresses allocation intent as a hint.
            # RiskManager remains the final authority for sizing.
            base_tw = float(getattr(self.config, "base_position_pct", 0.0) or 0.0)
            target_weight_hint = self._calculate_regime_adaptive_weight(
                symbol=symbol,
                base_weight=base_tw,
                side=side,
                ads_r=ads_ctx.get("ads_regime_vector_obj")
            )
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

    def _calculate_regime_adaptive_weight(
        self,
        symbol: str,
        base_weight: float,
        side: str,
        ads_r: Optional[ADSRegimeVector] = None
    ) -> float:
        """
        Calculate regime-adaptive position size based on ADS continuous regime vector R.

        Sizing logic:
        1. Base: Strategy-defined base_position_pct
        2. Confidence scaling: size * (0.5 + 0.5 * Confidence)
        3. Volatility scaling: size * (1.25 - Volatility)
        4. Liquidity scaling: size * (0.5 + 0.5 * Liquidity)
        5. Trend alignment:
           - confirmed: +25% size boost
           - headwind: -25% size penalty
        """
        if not bool(getattr(self.config, "enable_regime_adaptive_sizing", False)):
            return base_weight

        if ads_r is None:
            ads_r, _ = self._ads_regime_cache.get_vector(
                symbol=symbol,
                get_regime_context=self.get_current_regime_context,
            )

        weight = float(base_weight)

        # 1. Confidence scaling (0.7 to 1.3)
        weight *= (0.7 + 0.6 * float(ads_r.confidence))

        # 2. Volatility scaling (0.5 to 1.5)
        # High vol (1.0) -> 0.5x size; Low vol (0.0) -> 1.5x size
        vol_penalty = float(ads_r.volatility)
        
        # 3. Liquidity scaling (0.7 to 1.1)
        weight *= (0.7 + 0.4 * float(ads_r.liquidity))

        # 4. Trend alignment boost/penalty
        is_bullish_signal = (side in ("BUY", "LONG_ENTRY", "bullish_momentum"))

        if is_bullish_signal:
            if ads_r.trend >= 0.2:  # Bullish regime confirms long signal
                weight *= 1.5
                vol_penalty *= 0.5 # Half the vol penalty if trending in our direction
            elif ads_r.trend <= -0.2:  # Bearish regime headwind for long signal
                weight *= 0.5
        else:  # Bearish/Short signal
            if ads_r.trend <= -0.2:  # Bearish regime confirms short signal
                weight *= 1.5
                vol_penalty *= 0.5
            elif ads_r.trend >= 0.2:  # Bullish regime headwind for short signal
                weight *= 0.5

        # Apply volatility scaling after adjustment
        weight *= (1.5 - vol_penalty)

        # Final clip to strategy max
        max_tw = float(getattr(self.config, "max_position_pct", base_weight * 1.5) or base_weight * 1.5)
        return float(np.clip(weight, 0.0, max_tw))

    def _build_hybrid_metadata(
        self,
        *,
        signal_source: str,
        strength: float,
        side: Optional[str] = None,
        data_row: Optional[pd.Series] = None,
        ads_r: Optional[ADSRegimeVector] = None
    ) -> Dict[str, Any]:
        """
        Build standardized metadata for MOM/MR recombination.
        """
        expected_holding = int(getattr(self.config, "expected_holding_period_bars", 5) or 5)

        volatility_norm = float(strength)
        if data_row is not None:
            atr_pct = data_row.get("atr_percentile", None)
            if atr_pct is not None and not pd.isna(atr_pct):
                pct = max(0.0, min(1.0, float(atr_pct)))
                volatility_norm = float(strength) * (1.0 - pct)

        regime_alignment = None
        if ads_r is not None:
            trend = float(getattr(ads_r, "trend", 0.0))
            if side in ("BUY", "LONG_ENTRY", "LONG", "bullish_momentum"):
                regime_alignment = max(0.0, trend)
            elif side in ("SELL", "SHORT", "SHORT_ENTRY", "bearish_momentum"):
                regime_alignment = max(0.0, -trend)
            else:
                regime_alignment = abs(trend)

        return {
            "signal_source": signal_source,
            "expected_holding_period": expected_holding,
            "volatility_normalized_strength": volatility_norm,
            "regime_alignment_score": regime_alignment,
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
        # Rule 7: schema compatibility glue belongs in skeleton utilities.
        # Preserve historical behavior: return expected_name if nothing matches.
        return resolve_expected_or_mapped_column(
            data=data,
            expected_name=expected_name,
            mapping=self._column_mapping_cache,
        )

    def _validate_enriched_data(self, enriched_data: Dict[str, pd.DataFrame]) -> None:
        """
        Core-alpha declaration: required indicators for momentum signal generation.

        The mechanics of validation live in skeleton utilities (Rule 7).
        """
        required_indicators = {
            "SMA_10": ["sma_10", "SMA_10"],  # Optional - may not be configured
            "SMA_20": ["sma_20", "SMA_20"],
            "SMA_50": ["sma_50", "SMA_50"],
            "RSI_14": ["rsi", "RSI_14"],
            "ADX_14": ["adx", "ADX_14"],
            "MACD": ["macd", "MACD"],
            "ATR_14": ["atr", "ATR_14"],
            "volume_ratio": ["volume_ratio"],
        }

        validate_required_indicator_columns(
            enriched_data,
            required_indicators=required_indicators,
            optional_expected={"SMA_10"},
            mapping_suggestions=self._column_mapping_cache,
            cols_preview=20,
            logger=logger,
        )

    # NOTE (Rule 7): lifecycle, health, summary, and config validation are provided by
    # `EnhancedBaseStrategy`. This implementation is intentionally core-alpha only.

    # ========================================
    # ABSTRACT METHOD IMPLEMENTATIONS
    # ========================================

    async def generate_signals(self, enriched_data: Dict[str, pd.DataFrame]) -> List[StrategySignal]:
        """
        Generate momentum signals from ENRICHED data (Rule 3 Phase 4)
        """
        start_time = datetime.now()
        signals = []

        if not enriched_data:
            logger.warning("generate_signals() called with empty enriched_data")
            return []

        # Rule 7: generic boundary validation belongs in skeleton (EnhancedBaseStrategy).
        # Keep momentum-specific indicator validation below.
        self._validate_enriched_data_basic(
            enriched_data,
            required_ohlcv=["open", "high", "low", "close", "volume"],
            skip_empty_frames=True,
        )

        try:
            # PHASE 4: Validate enriched data (Rule 3)
            self._validate_enriched_data(enriched_data)

            # Update market data with enriched data
            self._update_market_data_cache(enriched_data)

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
            
            # One bounded summary line (acceptable ops visibility, not per-bar spam).
            if len(signals) > 0:
                logger.info(
                    f"Momentum: {len(symbols_checked)} symbols, {len(signals)} signals in {generation_time:.3f}s"
                )
            # Heartbeat removed to reduce log noise during long backtests (ADS v3.1 compliance)

            return signals

        except Exception as e:
            self._log_error("Signal generation failed", e)
            return []

    # ========================================
    # SIGNAL GENERATION METHODS
    # ========================================

    async def _evaluate_bar_at_index(self, symbol: str, idx: int) -> Optional[StrategySignal]:
        """
        Evaluate a specific bar at index and generate signal if conditions are met
        """
        try:
            # Get data at index (FIXED: HIGH #2 - use safe_iloc)
            data = self.market_data[symbol]

            # Use safe_iloc for bounds checking
            current_data = safe_iloc(data, idx, logger=logger)
            if current_data is None:
                # Defensive guard; avoid log spam in historical scan mode.
                return None

            # Check minimum data requirement
            actual_idx = idx if idx >= 0 else len(data) + idx
            if actual_idx < self.config.long_period:
                return None

            # Extract timestamp (skeleton utility)
            signal_timestamp = extract_bar_timestamp(data, actual_idx, logger=logger)

            # FIXED: HIGH #4 - Do NOT use datetime.now() fallback for bar timestamps
            if not signal_timestamp:
                logger.error(f"  [{symbol}] Missing bar timestamp at index {idx} - skipping bar (do not use datetime.now())")
                return None

            # ========================================
            # PROFESSIONAL RE-ARCHITECTURE: State Machine (V1)
            # ========================================
            has_pos = self._has_position(symbol)

            # Rule 7: exit authority lives in CentralRiskManager. Momentum alpha is entry-intent only.
            if has_pos:
                return None

            # ENTRY EVALUATION (If flat)
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
                    signal.additional_data.update(
                        self._build_hybrid_metadata(
                            signal_source="momentum",
                            strength=1.0,
                            side="LONG_ENTRY",
                            data_row=current_data if isinstance(current_data, pd.Series) else None,
                            ads_r=None,
                        )
                    )
                    base_tw = float(getattr(self.config, "base_position_pct", 0.0) or 0.0)
                    signal.target_weight = self._calculate_regime_adaptive_weight(
                        symbol=symbol,
                        base_weight=base_tw,
                        side="LONG_ENTRY"
                    )
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

            # Fallback: if enrichment didn't provide momentum_* columns, compute simple returns from close.
            def _ret_at(period: int) -> float:
                try:
                    if "close" not in data.columns:
                        return 0.0
                    j = int(actual_idx)
                    p = int(period)
                    if j - p < 0:
                        return 0.0
                    c0 = float(data["close"].iloc[j - p])
                    c1 = float(data["close"].iloc[j])
                    if c0 <= 0:
                        return 0.0
                    return (c1 / c0) - 1.0
                except Exception:
                    return 0.0

            short_m = data[momentum_10_col].iloc[actual_idx] if momentum_10_col in data.columns else _ret_at(self.config.short_period)
            medium_m = data[momentum_20_col].iloc[actual_idx] if momentum_20_col in data.columns else _ret_at(self.config.medium_period)
            long_m = data[momentum_50_col].iloc[actual_idx] if momentum_50_col in data.columns else _ret_at(self.config.long_period)

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
                side = side_from_signal(signal_type)

                # ========================================================
                # TRANSITION SUPERVISOR GATE (Phase 1)
                # Detects participant synchronisation phase changes.
                # Blocks entry when market is NOT structurally ready for
                # momentum (low coherence, no acceleration, vol mirage).
                # Runs BEFORE SMS/ERAR to avoid wasted ADS computation.
                # ========================================================
                if bool(getattr(self.config, "enable_transition_supervisor", True)):
                    transition_score = float(current_data.get("transition_score", 1.0))
                    vov = float(current_data.get("vol_of_vol", 0.5))
                    coherence = float(current_data.get("directional_coherence", 0.5))

                    # Hard block: vol-of-vol mirage (pre-news, macro uncertainty)
                    vov_block = float(getattr(self.config, "vov_block_threshold", 0.85))
                    if vov > vov_block:
                        return None

                    # Hard block: VPIN toxicity (informed/adverse flow regime)
                    # When VPIN percentile exceeds threshold, the probability of
                    # informed trading is elevated — entries face systematic
                    # adverse selection. Block until toxicity subsides.
                    if bool(getattr(self.config, "enable_vpin_gate", True)):
                        vpin_pct = float(current_data.get("vpin_percentile", 0.5))
                        vpin_block = float(getattr(self.config, "vpin_block_threshold", 0.85))
                        if vpin_pct > vpin_block:
                            return None

                    # ========================================================
                    # MICROSTRUCTURE QUALITY SCORE (MQS) — v3.3
                    #
                    # Addresses three universal momentum failure modes via a
                    # single multiplicative quality score rather than independent
                    # hard blocks (which over-kill due to feature overlap
                    # between winners and losers at 1-min resolution).
                    #
                    # MQS = coherence_f × flow_alignment_f × liquidity_f
                    #
                    # Each factor ∈ [0, 1]; any single factor at zero kills
                    # the score (ADS-compliant multiplicative design).
                    #
                    # The MQS is applied as a confidence penalty: it scales
                    # down signal confidence proportionally. Entries with
                    # multiple adverse microstructure conditions see their
                    # confidence collapse below the minimum threshold.
                    #
                    # Additionally, extreme BVC contra-flow (buy_vol_pct < 0.15
                    # on BUY) is a hard block — this is the Kyle (1985)
                    # adverse selection check for egregious cases only.
                    # ========================================================
                    if bool(getattr(self.config, "enable_microstructure_quality", True)):
                        _buy_vol_pct = float(current_data.get("buy_volume_pct", 0.5))
                        # volume_ratio in the features DataFrame is normalized/centered
                        # (0 = average, negative = below average).
                        _vol_ratio = float(current_data.get("volume_ratio", 0.0))

                        # Hard block: extreme BVC contra-flow only
                        # (catching only egregious cases like Trade #2: BVC=0.057)
                        bvc_hard_block = float(getattr(self.config, "bvc_hard_block", 0.15))
                        if side == "BUY" and _buy_vol_pct < bvc_hard_block:
                            return None
                        elif side == "SELL" and (1.0 - _buy_vol_pct) < bvc_hard_block:
                            return None

                        # Compute MQS components (each [0, 1])
                        coh_ref = float(getattr(self.config, "mqs_coherence_ref", 0.30))
                        bvc_ref = float(getattr(self.config, "mqs_bvc_ref", 0.45))
                        # volume_ratio is centered at 0 (negative = below avg)
                        vol_floor = float(getattr(self.config, "mqs_vol_floor", -0.50))
                        vol_range = float(getattr(self.config, "mqs_vol_range", 0.50))

                        coherence_f = min(1.0, max(0.0, coherence / max(coh_ref, 1e-6)))

                        aligned_bvc = _buy_vol_pct if side == "BUY" else (1.0 - _buy_vol_pct)
                        flow_alignment_f = min(1.0, max(0.0, aligned_bvc / max(bvc_ref, 1e-6)))

                        liquidity_f = min(1.0, max(0.0, (_vol_ratio - vol_floor) / max(vol_range, 1e-6)))

                        mqs = coherence_f * flow_alignment_f * liquidity_f

                        # Apply MQS as confidence penalty via a stored attribute
                        # that will be read when _calculate_signal_confidence runs.
                        # Lower bound: MQS can reduce confidence by up to mqs_max_penalty.
                        mqs_penalty_weight = float(getattr(self.config, "mqs_penalty_weight", 0.40))
                        self._current_mqs = float(mqs)
                        self._current_mqs_penalty = 1.0 - mqs_penalty_weight * (1.0 - mqs)



                    # Regime-adaptive threshold: stricter in adverse conditions
                    base_tau = float(getattr(self.config, "transition_threshold", 0.15))
                    strict_tau = float(getattr(self.config, "transition_threshold_strict", 0.30))

                    # Use strict threshold if regime indicates high vol or low liquidity
                    use_strict = False
                    try:
                        regime_ctx = self.get_current_regime_context()
                        if regime_ctx is not None:
                            r_vol = getattr(regime_ctx, 'volatility', None) or getattr(regime_ctx, 'r_vol', 0.5)
                            r_liq = getattr(regime_ctx, 'liquidity', None) or getattr(regime_ctx, 'r_liq', 0.5)
                            if float(r_vol) > 0.7 or float(r_liq) < 0.3:
                                use_strict = True
                    except Exception:
                        pass  # Degrade safely: use base threshold

                    tau = strict_tau if use_strict else base_tau

                    if transition_score < tau:
                        return None

                # ADS v3.1 §1: SMS gate with pending/stale maturation
                
                # Trend persistence filter (core alpha)
                if not self._passes_trend_persistence_filter(data=data, idx=actual_idx, side=side):
                    return None

                # Check if already pending for this symbol/side to avoid logic flooding
                if self.pending_signals.get(symbol, side):
                    # Avoid noisy per-bar diagnostics here; pending queue already prevents flooding.
                    return None

                # ADS v3.1: Consolidate ADS context (SMS values + ERAR object)
                raw_strength = float(min(abs(momentum_strength) / self.config.momentum_threshold, 1.0))
                ads_ctx = self._calculate_ads_context(symbol, data, actual_idx, side, raw_strength=raw_strength)
                
                tau = ads_ctx["tau"]
                regime_label = ads_ctx["regime_label"]
                ads_diag = ads_ctx["ads_diag"]

                sms = SignalMaturityScore(
                    # Legacy fields kept for safety, but the SSOT contract drives computation.
                    pending_bars=0,
                    decay_rate=float(getattr(self.config, "sms_decay_rate", 0.05)),
                    max_pending=int(getattr(self.config, "sms_max_pending", 50)),
                    inputs=ADSSMSGateInputs(
                        setup_maturity=float(ads_ctx["setup_maturity"]),
                        setup_validity_prob=float(ads_ctx["setup_validity_prob"]),
                        signed_flow_support=float(ads_ctx["signed_flow_support"]),
                        vol_compression=float(ads_ctx["vol_compression"]),
                        flow_source=str(ads_ctx.get("flow_source", "unknown")),
                        diagnostics=dict(ads_ctx.get("sms_diag", {})),
                    ),
                )

                sms_mode = str(getattr(self.config, "sms_mode", "multiplicative") or "multiplicative").lower()
                if sms_mode in ("bayes", "bayes_log_odds", "log_odds", "sequential_log_odds"):
                    # "Bayesian-lite" SMS: sequential log-odds with event-time maturation clock
                    try:
                        row = data.iloc[actual_idx]
                        prev_row = data.iloc[actual_idx - 1] if actual_idx > 0 else None
                    except Exception:
                        row = None
                        prev_row = None

                    p0 = float(getattr(self.config, "sms_prior_p0", 0.55))
                    coef = float(getattr(self.config, "sms_prior_strength_coef", 0.10))
                    prior = float(np.clip(p0 + coef * (raw_strength - 0.5), 0.05, 0.95))

                    bayes_sms = SequentialLogOddsSMS(
                        log_odds=float(math.log(prior / (1.0 - prior))),
                        pending_bars=0,
                        info_clock=0.0,
                        min_info_to_mature=float(getattr(self.config, "sms_min_info_to_mature", 0.5)),
                        max_info=float(getattr(self.config, "sms_max_info", 12.0)),
                        max_pending=int(getattr(self.config, "sms_max_pending", 50)),
                        w_setup_maturity=float(getattr(self.config, "sms_w_setup_maturity", 1.10)),
                        w_setup_validity=float(getattr(self.config, "sms_w_setup_validity", 1.25)),
                        w_flow_support=float(getattr(self.config, "sms_w_flow_support", 0.80)),
                        w_vol_compression=float(getattr(self.config, "sms_w_vol_compression", 0.60)),
                        delay_penalty_per_bar=float(getattr(self.config, "sms_delay_penalty_per_bar", 0.02)),
                    )

                    info_inc = 0.0
                    if row is not None:
                        info_inc = float(
                            compute_sms_info_increment(
                                row=row,
                                prev_row=prev_row,
                                w_volume=float(getattr(self.config, "sms_info_w_volume", 0.55)),
                                w_volatility=float(getattr(self.config, "sms_info_w_volatility", 0.45)),
                                cap=float(getattr(self.config, "sms_info_cap", 3.0)),
                            )
                        )
                    p_est = float(bayes_sms.update(sms.inputs, info_increment=info_inc))

                    if (not bayes_sms.can_mature()) or (p_est < float(tau)):
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
                                "sms_mode": "bayes_log_odds",
                                "ads_tau": tau,
                                "ads_sms_prob": p_est,
                                "ads_sms_log_odds": float(bayes_sms.log_odds),
                                "ads_sms_info_clock": float(bayes_sms.info_clock),
                                "ads_sms_info_inc": float(info_inc),
                                "ads_regime_vector": ads_ctx["ads_regime_vector"],
                                "ads_fallbacks_used": ads_ctx["ads_fallbacks_used"],
                                "ads_diag": ads_diag,
                                "ofi_source": ads_ctx.get("txn_flow_source", "proxy_volume_ratio"),
                                "bb_missing": True,
                                "composite_z": ads_ctx["composite_z"],
                                "composite_pct": ads_ctx["composite_pct"],
                                "txn_ratio": ads_ctx.get("txn_ratio"),
                                "txn_ratio_cs_rank": ads_ctx.get("txn_ratio_cs_rank"),
                                "avg_trade_size_ratio": ads_ctx.get("avg_trade_size_ratio"),
                                "txn_volume_divergence": ads_ctx.get("txn_volume_divergence"),
                                "sms_inputs": {
                                    "setup_maturity": float(ads_ctx["setup_maturity"]),
                                    "setup_validity_prob": float(ads_ctx["setup_validity_prob"]),
                                    "signed_flow_support": float(ads_ctx["signed_flow_support"]),
                                    "vol_compression": float(ads_ctx["vol_compression"]),
                                    "flow_source": str(ads_ctx.get("flow_source", "unknown")),
                                },
                            },
                            bayes_sms=bayes_sms,
                        )
                        self.pending_signals.add(ctx)
                        return None

                    sms_score = p_est
                else:
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
                                "sms_mode": "multiplicative",
                                "ads_tau": tau,
                                "ads_sms": sms_score,
                                "ads_regime_vector": ads_ctx["ads_regime_vector"],
                                "ads_fallbacks_used": ads_ctx["ads_fallbacks_used"],
                                "ads_diag": ads_diag,
                                "ofi_source": ads_ctx.get("txn_flow_source", "proxy_volume_ratio"),
                                "bb_missing": True,
                                "composite_z": ads_ctx["composite_z"],
                                "composite_pct": ads_ctx["composite_pct"],
                                "txn_ratio": ads_ctx.get("txn_ratio"),
                                "txn_ratio_cs_rank": ads_ctx.get("txn_ratio_cs_rank"),
                                "avg_trade_size_ratio": ads_ctx.get("avg_trade_size_ratio"),
                                "txn_volume_divergence": ads_ctx.get("txn_volume_divergence"),
                                "sms_inputs": {
                                    "setup_maturity": float(ads_ctx["setup_maturity"]),
                                    "setup_validity_prob": float(ads_ctx["setup_validity_prob"]),
                                    "signed_flow_support": float(ads_ctx["signed_flow_support"]),
                                    "vol_compression": float(ads_ctx["vol_compression"]),
                                    "flow_source": str(ads_ctx.get("flow_source", "unknown")),
                                },
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

                # Apply MQS confidence penalty (v3.3)
                # Trades with poor microstructure quality see confidence reduced,
                # potentially below the minimum threshold → auto-killed.
                mqs_penalty = getattr(self, '_current_mqs_penalty', 1.0)
                confidence = confidence * mqs_penalty

                if confidence > 0.4:  # Minimum confidence threshold (lowered for composite signals)
                    base_tw = float(getattr(self.config, "base_position_pct", 0.0) or 0.0)
                    target_weight = self._calculate_regime_adaptive_weight(
                        symbol=symbol,
                        base_weight=base_tw,
                        side=side,
                        ads_r=ads_ctx.get("ads_regime_vector_obj")
                    )

                    # Capture transition supervisor state at entry for
                    # downstream exit monitoring (coherence decay detection)
                    _entry_transition_score = float(current_data.get("transition_score", 0.0))
                    _entry_coherence = float(current_data.get("directional_coherence", 0.5))
                    _entry_vov = float(current_data.get("vol_of_vol", 0.5))
                    _entry_accel = float(current_data.get("composite_accel_norm", 0.0))
                    _entry_vol_expansion = float(current_data.get("vol_expansion", 0.0))
                    _entry_vpin = float(current_data.get("vpin", 0.5))
                    _entry_vpin_pct = float(current_data.get("vpin_percentile", 0.5))

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
                            'ads_fallbacks': {'ofi_source': ads_ctx.get("txn_flow_source", "proxy_volume_ratio"), 'bb_missing': True},
                            'short_momentum': short_momentum,
                            'medium_momentum': medium_momentum,
                            'long_momentum': long_momentum,
                            'adx': adx,
                            'volume_ratio': volume_ratio,
                            'txn_ratio': ads_ctx.get("txn_ratio"),
                            'txn_ratio_cs_rank': ads_ctx.get("txn_ratio_cs_rank"),
                            'avg_trade_size_ratio': ads_ctx.get("avg_trade_size_ratio"),
                            'txn_volume_divergence': ads_ctx.get("txn_volume_divergence"),
                            'txn_flow_source': ads_ctx.get("txn_flow_source"),
                            'entry_price': current_data['close'] if isinstance(current_data, pd.Series) else current_data.get('close', 0),
                            'bar_index': idx,
                            # Transition Supervisor diagnostics (Phase 1)
                            'transition_score': _entry_transition_score,
                            'entry_coherence': _entry_coherence,
                            'entry_vol_of_vol': _entry_vov,
                            'entry_composite_accel': _entry_accel,
                            'entry_vol_expansion': _entry_vol_expansion,
                            # VPIN / Flow Toxicity diagnostics (v3.2)
                            'entry_vpin': _entry_vpin,
                            'entry_vpin_percentile': _entry_vpin_pct,
                            # Microstructure Quality Score (v3.3)
                            'entry_mqs': getattr(self, '_current_mqs', 1.0),
                            'entry_mqs_penalty': getattr(self, '_current_mqs_penalty', 1.0),
                        }
                    )
                    signal.additional_data.update(
                        self._build_hybrid_metadata(
                            signal_source="momentum",
                            strength=signal.strength,
                            side=side,
                            data_row=current_data if isinstance(current_data, pd.Series) else None,
                            ads_r=ads_ctx.get("ads_regime_vector_obj"),
                        )
                    )
                    return signal

            # No entry signal
            return None

        except Exception as e:
            logger.error(f"[{symbol}] Error evaluating bar at index {idx}: {e}")
            return None

    async def _generate_symbol_signals(self, symbol: str) -> List[StrategySignal]:
        """Generate signals for a specific symbol"""

        signals = []

        try:
            # ADS v3.1: strategies should not maintain local position state.
            # Use PositionBook SSOT (via EnhancedBaseStrategy._has_position()).
            

            # Get current indicators and momentum data
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
                # (No per-symbol scan mode logging; backtest harness can report progress)

                start_idx = self.config.long_period
                end_idx = data_length
                scan_interval = max(1, self.config.scan_interval)

                # Rule 7: bar-iteration orchestration is skeleton; alpha supplies evaluation callbacks.
                res = await scan_bars_at_interval(
                    start_idx=int(start_idx),
                    end_idx=int(end_idx),
                    scan_interval=int(scan_interval),
                    emit_pending_at_index=lambda i: self._try_emit_matured_pending(symbol, data, i),
                    evaluate_at_index=lambda i: self._evaluate_bar_at_index(symbol, i),
                )

                return res.signals

            # Live mode: Evaluate only current bar (default behavior)

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
                self.momentum_data[symbol] = self._analyze_symbol_momentum(symbol)
                # Also populate indicators dictionary for signal generation
                self._extract_indicators_from_data(symbol)
            else:
                logger.warning(f"    Cannot update momentum for {symbol} - missing market data")

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
                if is_ffill_stale(short_momentum_series, max_stale_bars=10, logger=logger):
                    # Data-quality guard; keep as warning because it indicates pipeline/data issues.
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
                if is_ffill_stale(medium_momentum_series, max_stale_bars=10, logger=logger):
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
                if is_ffill_stale(long_momentum_series, max_stale_bars=10, logger=logger):
                    logger.warning(f"[{symbol}] Stale long momentum data detected, using fallback")
                    long_momentum = current_row.get('momentum_long', 0.0)
                elif pd.isna(long_momentum_series.iloc[-1]):
                    long_momentum_valid = long_momentum_series.dropna()
                    long_momentum = long_momentum_valid.iloc[-1] if len(long_momentum_valid) > 0 else current_row.get('momentum_long', 0.0)
                else:
                    long_momentum = long_momentum_series.iloc[-1]
            else:
                long_momentum = current_row.get('momentum_long', 0.0)

            # Avoid per-bar debug logging inside alpha.

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

            # Rule 7: schema-compatibility glue lives in skeleton utilities.
            bundle = extract_momentum_indicator_series(
                data=data,
                adx_candidates=[self._get_column_name("ADX_14", data), "ADX_14", "adx"],
                volume_ratio_candidates=[self._get_column_name("volume_ratio", data), "volume_ratio"],
                trend_strength_candidates=["trend_strength"],
                default_adx=25.0,
                default_volume_ratio=1.0,
                default_trend_strength=0.0,
            )

            self.indicators[symbol] = {
                'adx': bundle.adx,
                'volume_ratio': bundle.volume_ratio,
                'trend_strength': bundle.trend_strength,
            }

            # Avoid per-symbol debug logging inside alpha.

        except Exception as e:
            logger.error(f"Failed to extract indicators for {symbol}: {e}")
            # Create fallback series with proper index
            fallback_index = self.market_data[symbol].index if symbol in self.market_data else pd.RangeIndex(1)
            self.indicators[symbol] = {
                'adx': pd.Series([25.0], index=fallback_index),
                'volume_ratio': pd.Series([1.0], index=fallback_index),
                'trend_strength': pd.Series([0.0], index=fallback_index)
            }

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

            txn_bonus = 0.0
            if bool(getattr(self.config, "enable_transactions_confirm", False)) and symbol in self.market_data:
                try:
                    latest_row = self.market_data[symbol].iloc[-1]
                    txn_ratio = float(latest_row.get("txn_ratio", 1.0))
                    avg_size_ratio = float(latest_row.get("avg_trade_size_ratio", 1.0))
                    if txn_ratio > 1.3 and avg_size_ratio < 1.0:
                        txn_bonus = 0.05
                except Exception:
                    txn_bonus = 0.0

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

            total_confidence = min(base_confidence + conditions_met_bonus + txn_bonus, 0.95)

            return total_confidence

        except Exception as e:
            logger.error(f"Signal confidence calculation failed for {symbol}: {e}")
            return 0.5

    # ========================================
    # HELPER METHODS
    # ========================================

    # ========================================
    # REGIME-AWARE ENTRY LOGIC (Phase 4B)
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

        ads_r, diag = self._ads_regime_cache.get_vector(
            symbol=symbol,
            get_regime_context=self.get_current_regime_context,
        )

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

        # 1. SMS Components (strategy-independent contract inputs)
        #
        # If enrichment does not provide composite_z/composite_pct, use the deterministic fallback
        # (smoke-test focused). This keeps ADS/SMS gating testable even with minimal pipelines.
        composite_z = float(row.get("composite_z", 0.0))
        composite_pct_raw = float(row.get("composite_pct", 0.0))
        if ("composite_z" not in data.columns) or ("composite_pct" not in data.columns):
            cz, cp = self._fallback_compute_composite_signals(data, actual_idx)
            if cz is not None and cp is not None:
                composite_z = float(cz)
                composite_pct_raw = float(cp)
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

        setup_maturity = float(
            np.clip(
                (max(z_maturity, 1e-3) * max(pct_maturity, 1e-3) * (0.5 + 0.5 * structure_q)) ** (1 / 3),
                0.0,
                1.0,
            )
        )

        # Setup validity probability (strategy-independent semantic).
        #
        # For momentum, we treat "not over-extended against the intended direction" as validity.
        rsi_col = self._get_column_name("RSI_14", data)
        rsi = float(row.get(rsi_col, row.get("rsi", 50.0)))
        if side == "BUY":
            p_rev_rsi = 1.0 / (1.0 + float(np.exp(-(rsi - float(getattr(self.config, "rsi_overbought", 70.0))) / 5.0)))
        else:
            p_rev_rsi = 1.0 / (1.0 + float(np.exp(-(float(getattr(self.config, "rsi_oversold", 30.0)) - rsi) / 5.0)))
        setup_validity_prob = float(np.clip(1.0 - p_rev_rsi, 0.001, 1.0))

        # Flow support proxy (signed by intended direction)
        vol_ratio = float(row.get("volume_ratio", 1.0))
        sign = 1.0 if side == "BUY" else -1.0
        flow_source = "proxy_volume_ratio"
        signed_flow_support = float(np.clip((vol_ratio - 1.0) * sign, -1.0, 1.0))

        if bool(getattr(self.config, "enable_txn_sms_flow_blend", False)):
            txn_ratio = float(row.get("txn_ratio", 1.0))
            w = float(getattr(self.config, "txn_sms_flow_weight", 0.3))
            blended_ratio = (1.0 - w) * vol_ratio + w * txn_ratio
            signed_flow_support = float(np.clip((blended_ratio - 1.0) * sign, -1.0, 1.0))
            flow_source = "blended_vol_txn"

        # Volatility compression (SSOT): VC = σ_short / σ_long
        vol_comp = 1.0
        try:
            if "close" in data.columns and actual_idx >= 20:
                prices = data["close"].iloc[max(0, actual_idx - 20) : actual_idx + 1]
                rets = prices.pct_change()
                short_vol = float(rets.tail(5).std()) if len(rets) >= 5 else 0.02
                long_vol = float(rets.std()) if len(rets) >= 10 else 0.02
                vol_comp = float(compute_vol_compression(short_vol=short_vol, long_vol=long_vol))
        except Exception:
            vol_comp = 1.0

        # SMS threshold policy: tau(R) should be derived from regime/liquidity/confidence,
        # not from the same evidence inputs used by the SMS score (avoid circular gating).
        tau_0 = float(getattr(self.config, "tau_0", 0.50))
        ads_r = thresholds.get("ads_regime_vector_obj")
        bb_missing = ("bb_position" not in data.columns) and ("bb_upper" not in data.columns)

        # VPIN-conditioned tau hardening: pass current VPIN percentile to tau(R)
        # so that signal maturity threshold increases during toxic flow regimes.
        vpin_pct_for_tau = 0.5  # neutral default
        if bool(getattr(self.config, "enable_vpin_gate", True)):
            vpin_pct_for_tau = float(row.get("vpin_percentile", 0.5))

        tau = float(
            compute_sms_tau(
                ads_r,
                tau_0=tau_0,
                ofi_proxy_used=True,
                bb_missing=bb_missing,
                direction="long" if side == "BUY" else "short",
                vpin_percentile=vpin_pct_for_tau,
                vpin_tau_sensitivity=float(getattr(self.config, "vpin_tau_sensitivity", 0.15)),
            )
        )
        
        # Get regime label for regime-adaptive exponents (stateful SMS compute)
        regime_label = sms_regime_label_from_ads_vector(ads_r)
        sms_diag = {
            "tau_0": tau_0,
            "ofi_proxy_used": True,
            "bb_missing": bb_missing,
        }

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

        # VPIN-adjusted adverse selection probability:
        # Base P_adv = 0.10 (uninformed baseline). When VPIN percentile is elevated,
        # scale P_adv up to capture the higher probability of trading against
        # informed counterparties.
        #   P_adv = base + vpin_sensitivity × max(0, vpin_pct - vpin_neutral)
        # where vpin_neutral = 0.50 (median = uninformed).
        base_adverse_prob = float(getattr(self.config, "erar_base_adverse_prob", 0.10))
        if bool(getattr(self.config, "enable_vpin_gate", True)):
            vpin_pct = float(row.get("vpin_percentile", 0.5))
            vpin_sensitivity = float(getattr(self.config, "vpin_adverse_sensitivity", 0.40))
            vpin_neutral = 0.50
            adverse_prob = float(np.clip(
                base_adverse_prob + vpin_sensitivity * max(0.0, vpin_pct - vpin_neutral),
                0.01, 0.50
            ))
        else:
            adverse_prob = base_adverse_prob

        erar = ERAR(
            expected_pnl=float(expected_pnl_bps),
            cvar_95=float(cvar_95_bps),
            skewness=0.0,
            spread_bps=float(getattr(self.config, "spread_bps", 2.0)),
            participation=0.01,
            volatility=float(volatility),
            adverse_prob=adverse_prob,
            kyle_lambda=0.0001,
            holding_days=float(holding_days),
            alt_return_bps=float(getattr(self.config, "alt_return_bps", 0.5)),
            tail_lambda=float(getattr(self.config, "erar_tail_lambda", 1.0)),
        )

        return {
            "composite_z": composite_z,
            "composite_pct": composite_pct,
            # SSOT SMS contract fields
            "setup_maturity": setup_maturity,
            "setup_validity_prob": setup_validity_prob,
            "signed_flow_support": signed_flow_support,
            "vol_compression": vol_comp,
            "flow_source": flow_source,
            "sms_diag": sms_diag,
            "tau": tau,
            "regime_label": regime_label,
            "erar": erar,
            "erar_val": float(erar.compute()),
            "z_maturity": z_maturity,
            "pct_maturity": pct_maturity,
            "ads_regime_vector": thresholds.get("ads_regime_vector", {}),
            "ads_regime_vector_obj": ads_r,
            "ads_fallbacks_used": thresholds.get("ads_fallbacks_used", []),
            "ads_diag": thresholds.get("ads_diag", {}),
            "thresholds": thresholds,
            "txn_ratio": float(row.get("txn_ratio", 1.0)),
            "txn_ratio_cs_rank": float(row.get("txn_ratio_cs_rank", 0.5)),
            "avg_trade_size_ratio": float(row.get("avg_trade_size_ratio", 1.0)),
            "txn_volume_divergence": float(row.get("txn_volume_divergence", 0.0)),
            "txn_flow_source": flow_source,
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
            # Avoid per-bar debug logging inside alpha.

        # CRITICAL FIX #4: Price Structure Detection
        structure_data = None
        if enriched_data is not None and current_idx is not None:
            structure_data = self._detect_price_structure(
                symbol, enriched_data, current_idx, lookback=5
            )
            # Avoid per-bar debug logging inside alpha.

        # CRITICAL FIX #5: Fast Momentum Slope (replaces slow ADX)
        momentum_slope = 0.0
        if enriched_data is not None and current_idx is not None:
            momentum_slope = self._calculate_momentum_slope(
                symbol, enriched_data, current_idx, lookback=3
            )
            # Avoid per-bar debug logging inside alpha.

        # LONG entry: Composite threshold + structure + momentum
        long_condition_met = (
            composite_z > long_threshold and
            composite_pct > pct_threshold and
            momentum_slope > 0  # NEW: Momentum must be trending up
        )

        # Add inflection boost (allows earlier entry if inflection detected)
        if inflection_data and inflection_data.get('inflection_detected') and inflection_data.get('inflection_type') == 'bullish':
            # Avoid per-bar INFO spam; diagnostic lives in signal additional_data if emitted.
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
                # Avoid per-bar debug logging inside alpha.
                long_condition_met = long_condition_met and composite_z > long_threshold * 1.2  # Require stronger signal

        # SHORT entry: Composite threshold + structure + momentum
        short_condition_met = (
            composite_z < -short_threshold and
            composite_pct < (100 - pct_threshold) and
            momentum_slope < 0  # NEW: Momentum must be trending down
        )

        # Add inflection boost for shorts
        if inflection_data and inflection_data.get('inflection_detected') and inflection_data.get('inflection_type') == 'bearish':
            # Avoid per-bar INFO spam; diagnostic lives in signal additional_data if emitted.
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
                # Avoid per-bar debug logging inside alpha.
                short_condition_met = short_condition_met and composite_z < -short_threshold * 1.2

        # Transaction-based confirmation (optional)
        if bool(getattr(self.config, "enable_transactions_confirm", False)):
            txn_ratio = float(current_bar.get("txn_ratio", 1.0))
            txn_rank = float(current_bar.get("txn_ratio_cs_rank", 0.5))
            avg_size_ratio = float(current_bar.get("avg_trade_size_ratio", 1.0))
            txn_ratio_min = float(getattr(self.config, "txn_ratio_min", 1.1))
            txn_rank_min = float(getattr(self.config, "txn_rank_min", 0.7))
            avg_size_ratio_max = float(getattr(self.config, "avg_trade_size_ratio_max", 2.0))

            if txn_ratio < txn_ratio_min:
                long_condition_met = False
                short_condition_met = False

            if txn_rank < txn_rank_min:
                long_condition_met = long_condition_met and composite_z > long_threshold * 1.1
                short_condition_met = short_condition_met and composite_z < -short_threshold * 1.1

            if avg_size_ratio > avg_size_ratio_max:
                long_condition_met = long_condition_met and composite_z > long_threshold * 1.2
                short_condition_met = short_condition_met and composite_z < -short_threshold * 1.2

        if long_condition_met:
            return True, SignalType.LONG_ENTRY
        if short_condition_met:
            return True, SignalType.SHORT_ENTRY

        return False, None

    # NOTE (Rule 7): Exit authority lives in CentralRiskManager (+ exit policy). Momentum alpha is entry-only.

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
                # Fallback to composite_z (if present). If not present, skip inflection detection quietly.
                if 'composite_z' not in enriched_data.columns:
                    return {
                        'inflection_detected': False,
                        'inflection_type': None,
                        'momentum_slope': 0.0,
                        'momentum_accel': 0.0,
                        'vol_expansion': False
                    }
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

            # Avoid per-bar debug logging inside alpha.

            return {
                'inflection_detected': inflection_detected,
                'inflection_type': inflection_type,
                'momentum_slope': float(momentum_slope),
                'momentum_accel': float(momentum_accel),
                'vol_expansion': vol_expansion
            }

        except Exception as e:
            # Non-blocking diagnostic; avoid per-bar error spam in smoke tests.
            logger.debug(f"[{symbol}] Inflection detection skipped: {e}")
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

            # Avoid per-bar debug logging inside alpha.

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
                    # Final fallback (smoke-test / pipeline robustness):
                    # derive a short-horizon slope from close prices so ADS-gating branch can run even
                    # when enrichment does not provide momentum_* or composite_z columns.
                    if 'close' not in enriched_data.columns:
                        return 0.0
                    closes = enriched_data['close'].iloc[current_idx - lookback + 1:current_idx + 1]
                    if len(closes) < 2:
                        return 0.0
                    # Use simple returns; slope>0 implies upward drift over the window.
                    momentum_series = closes.pct_change().fillna(0.0)
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