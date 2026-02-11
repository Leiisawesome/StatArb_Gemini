"""
Momentum State Machine: Structural Edge Architecture
===================================================

This module implements the "Brain" of the momentum strategy, responsible for
identifying structural patterns (Breakouts) and managing trade lifecycle 
states based on professional candle-reading principles.

Patterns are identified by the Brain and verified by the core_engine's 
statistical indicators (The Eyes).
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Optional, Any, Tuple
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class SymbolStateName(Enum):
    FLAT = "FLAT"
    SETUP_BREAKOUT = "SETUP_BREAKOUT"
    IN_POSITION = "IN_POSITION"

@dataclass
class SymbolState:
    """Tracks the trade narrative for a specific symbol."""
    symbol: str
    state: SymbolStateName = SymbolStateName.FLAT
    
    # Structural Anchors (The Breakout Base)
    setup_high: Optional[float] = None
    setup_low: Optional[float] = None
    setup_idx: Optional[int] = None
    setup_ts: Optional[datetime] = None
    
    # State Metadata
    pattern_mode: str = "BREAKOUT"
    bars_in_setup: int = 0
    invalidation_reason: Optional[str] = None
    
    # Verification Data
    last_update: datetime = field(default_factory=datetime.now)

class MomentumStateMachine:
    """
    Professional state machine for managing momentum trade lifecycles.
    
    Responsibilities:
    1. Pattern Recognition (Brain)
    2. State Transitions (Logic)
    3. Position Reconciliation (SSOT)
    """
    
    def __init__(self):
        self._states: Dict[str, SymbolState] = {}
        
    def get_state(self, symbol: str) -> SymbolState:
        """Retrieve or initialize state for a symbol."""
        if symbol not in self._states:
            self._states[symbol] = SymbolState(symbol=symbol)
        return self._states[symbol]
    
    def reconcile(self, symbol: str, has_position: bool):
        """
        Sync internal state with PositionBook (SSOT).
        Ensures the machine knows if a trade was filled or closed externally.
        """
        state = self.get_state(symbol)
        
        # 1. External Position Found -> Force IN_POSITION
        if has_position and state.state != SymbolStateName.IN_POSITION:
            logger.info(f"🔄 [{symbol}] Reconciling: Position found, transitioning to IN_POSITION")
            self.transition_to(symbol, SymbolStateName.IN_POSITION)
            
        # 2. No External Position -> Force FLAT if we thought we were in-position
        elif not has_position and state.state == SymbolStateName.IN_POSITION:
            logger.info(f"🔄 [{symbol}] Reconciling: No position found, resetting to FLAT")
            self.transition_to(symbol, SymbolStateName.FLAT)

    def transition_to(self, symbol: str, next_state: SymbolStateName, **metadata):
        """Handle state transitions and cleanup."""
        state = self.get_state(symbol)
        old_state = state.state
        
        if old_state == next_state:
            return state
            
        state.state = next_state
        state.last_update = datetime.now()
        
        # Cleanup / Initialization logic
        if next_state == SymbolStateName.FLAT:
            state.setup_high = None
            state.setup_low = None
            state.setup_idx = None
            state.setup_ts = None
            state.bars_in_setup = 0
            
        elif next_state == SymbolStateName.SETUP_BREAKOUT:
            state.setup_high = metadata.get('setup_high')
            state.setup_low = metadata.get('setup_low')
            state.setup_idx = metadata.get('idx')
            state.setup_ts = metadata.get('ts')
            state.bars_in_setup = 0
            
        logger.info(f"📈 [{symbol}] State Transition: {old_state.value} -> {next_state.value}")
        return state

    def update_setup_age(self, symbol: str):
        """Increment bars spent in the current setup."""
        state = self.get_state(symbol)
        if state.state == SymbolStateName.SETUP_BREAKOUT:
            state.bars_in_setup += 1

    def evaluate(self, 
                 symbol: str, 
                 idx: int, 
                 current_data: pd.Series, 
                 enriched_data: pd.DataFrame,
                 config: Any) -> Tuple[bool, Optional[str]]:
        """
        The main Brain logic for identifying structural trade entries.
        
        Returns:
            (should_trigger_entry, reason)
        """
        state = self.get_state(symbol)
        
        # --- FLAT STATE: SEARCHING FOR PATTERNS ---
        if state.state == SymbolStateName.FLAT:
            # Filter 1: Opening Range Filter (ORB) - Use time if available
            is_orb = False
            bar_ts = current_data.name if isinstance(current_data.name, datetime) else None
            if bar_ts:
                # Check minutes since 9:30 AM EST
                minutes_since_open = (bar_ts.hour * 60 + bar_ts.minute) - (9 * 60 + 30)
                if 0 <= minutes_since_open < getattr(config, 'orb_minutes', 15):
                    is_orb = True
            elif idx < getattr(config, 'orb_minutes', 15):
                is_orb = True
                
            if is_orb:
                return False, None
            
            # Filter 2: Near 20-bar High (Consolidation Location)
            lookback = 20
            if idx < lookback:
                return False, None
            
            recent_high = enriched_data['high'].iloc[idx-lookback:idx].max()
            current_close = current_data['close']
            
            # Brain: "Is it basing near the high?" (Within 2% of high)
            is_near_high = current_close >= (0.98 * recent_high)

            if is_near_high:
                # Filter 3: Tightness (VCP - Contraction Check)
                # We synthesize "Volatility Ratio" from ATR
                atr_col = 'atr' if 'atr' in enriched_data.columns else 'ATR_14'
                atr_series = enriched_data[atr_col] if atr_col in enriched_data.columns else None

                # P2-11 NOTE: Fallback ATR calculation from OHLC is a defensive SSOT violation.
                # The canonical ATR should come from EnhancedTechnicalIndicators ('atr' column).
                # This fallback exists because short data windows can produce NaN from the
                # indicator engine. Once warm-up handling is improved, this can be removed.
                # TODO: Remove fallback once indicator warm-up produces valid ATR for all windows.
                def _fallback_atr() -> Optional[pd.Series]:
                    try:
                        high = enriched_data["high"]
                        low = enriched_data["low"]
                        close = enriched_data["close"]
                        prev_close = close.shift(1)
                        tr = pd.concat(
                            [
                                (high - low).abs(),
                                (high - prev_close).abs(),
                                (low - prev_close).abs(),
                            ],
                            axis=1,
                        ).max(axis=1)
                        return tr.rolling(14, min_periods=14).mean()
                    except Exception:
                        return None

                if atr_series is not None:
                    current_atr = atr_series.iloc[idx]
                    avg_atr = atr_series.iloc[idx-lookback:idx].mean()

                    if pd.isna(current_atr) or pd.isna(avg_atr):
                        atr_series2 = _fallback_atr()
                        if atr_series2 is None:
                            return False, None
                        current_atr = atr_series2.iloc[idx]
                        avg_atr = atr_series2.iloc[idx-lookback:idx].mean()

                    vol_ratio = current_atr / avg_atr if avg_atr > 0 else 1.0
                    if pd.isna(vol_ratio):
                        return False, None

                    if vol_ratio < getattr(config, 'tightness_threshold', 0.75):
                        # SUCCESS: SETUP IDENTIFIED
                        setup_low = enriched_data['low'].iloc[idx-lookback:idx].min()
                        self.transition_to(symbol, SymbolStateName.SETUP_BREAKOUT, 
                                          setup_high=recent_high, 
                                          setup_low=setup_low, 
                                          idx=idx, 
                                          ts=current_data.name if isinstance(current_data.name, datetime) else None)
                        return False, "setup_identified"
            
            return False, None

        # --- SETUP STATE: WAITING FOR TRIGGER ---
        elif state.state == SymbolStateName.SETUP_BREAKOUT:
            self.update_setup_age(symbol)
            
            # Check for Invalidation (Thesis Broken)
            current_close = current_data['close']
            # Professional tweak: avoid resetting the setup on small undercuts.
            # Use an ATR buffer (default 0.25 ATR) so noise doesn't constantly wipe setups.
            try:
                atr_col = 'atr' if 'atr' in enriched_data.columns else 'ATR_14'
                atr = current_data.get(atr_col, None)
                if atr is None or pd.isna(atr):
                    # Fallback ATR(14)
                    high = enriched_data["high"]
                    low = enriched_data["low"]
                    close = enriched_data["close"]
                    prev_close = close.shift(1)
                    tr = pd.concat(
                        [
                            (high - low).abs(),
                            (high - prev_close).abs(),
                            (low - prev_close).abs(),
                        ],
                        axis=1,
                    ).max(axis=1)
                    atr = tr.rolling(14, min_periods=14).mean().iloc[idx]
                atr = float(atr) if atr is not None and not pd.isna(atr) else float(current_close) * 0.01
            except Exception:
                atr = float(current_close) * 0.01

            buf_mult = float(getattr(config, "setup_invalidation_atr", 0.25))
            breach_level = float(state.setup_low) - buf_mult * atr
            if current_close < breach_level:
                self.transition_to(symbol, SymbolStateName.FLAT)
                return False, "invalidation_price_breach"
            
            if state.bars_in_setup > getattr(config, 'setup_expiry_bars', 10):
                self.transition_to(symbol, SymbolStateName.FLAT)
                return False, "setup_expired"
            
            # Check for Trigger (Breakout Expansion)
            if current_close > state.setup_high:
                # Verification Filter: Volume Surge (Effort)
                # NOTE: Different pipelines may define `volume_ratio` differently (or clip it).
                # For the state machine, we want a robust "effort" proxy. We therefore compute a
                # local fallback (volume / rolling mean) and take the max of the two.
                vol_ratio_raw = current_data.get('volume_ratio', None)
                vr_fallback = 1.0
                try:
                    v = enriched_data["volume"]
                    v_ma = v.rolling(20, min_periods=20).mean()
                    if idx < len(v_ma) and v_ma.iloc[idx] and not pd.isna(v_ma.iloc[idx]):
                        vr_fallback = float(v.iloc[idx] / v_ma.iloc[idx])
                except Exception:
                    vr_fallback = 1.0

                if vol_ratio_raw is None or pd.isna(vol_ratio_raw):
                    vol_ratio = vr_fallback
                else:
                    try:
                        vol_ratio = max(float(vol_ratio_raw), float(vr_fallback))
                    except Exception:
                        vol_ratio = vr_fallback

                if vol_ratio > float(getattr(config, "breakout_volume_ratio_threshold", 1.1)):  # Volume confirmation
                    
                    # Verification Filter: Anti-Chase (Extension)
                    ma_col = getattr(config, 'anchor_ma', 'sma_20')
                    # Anchor MA fallback (default sma_20)
                    if ma_col in enriched_data.columns:
                        ma_val = current_data.get(ma_col, None)
                    else:
                        try:
                            ma_val = enriched_data["close"].rolling(20, min_periods=20).mean().iloc[idx]
                        except Exception:
                            ma_val = None

                    if ma_val is not None and not pd.isna(ma_val):
                        atr_col = 'atr' if 'atr' in enriched_data.columns else 'ATR_14'
                        atr = current_data.get(atr_col, None)
                        if atr is None or pd.isna(atr):
                            # Fallback ATR(14) as above
                            try:
                                high = enriched_data["high"]
                                low = enriched_data["low"]
                                close = enriched_data["close"]
                                prev_close = close.shift(1)
                                tr = pd.concat(
                                    [
                                        (high - low).abs(),
                                        (high - prev_close).abs(),
                                        (low - prev_close).abs(),
                                    ],
                                    axis=1,
                                ).max(axis=1)
                                atr = tr.rolling(14, min_periods=14).mean().iloc[idx]
                            except Exception:
                                atr = current_close * 0.01
                        if atr is None or pd.isna(atr) or float(atr) <= 0:
                            atr = current_close * 0.01
                        extension = (current_close - ma_val) / atr if atr > 0 else 0
                        
                        if extension > getattr(config, 'max_extension_atr', 1.5):
                            # Extension trap! Transition back to FLAT (or stay in setup, 
                            # but pros usually wait for a reset)
                            self.transition_to(symbol, SymbolStateName.FLAT)
                            return False, "invalidation_extension_trap"

                    # TRIGGER SUCCESS!
                    # Note: reconciliation will move us to IN_POSITION after fill
                    return True, "breakout_acceleration"

            return False, None

        # --- IN_POSITION STATE: MONITORING RISK ---
        elif state.state == SymbolStateName.IN_POSITION:
            # Structural Stop Check (thesis level)
            if current_data['close'] < state.setup_low:
                # This will be handled in EnhancedMomentumStrategy._check_structural_stop
                return False, "structural_stop_ready"
            
            return False, None
            
        return False, None

