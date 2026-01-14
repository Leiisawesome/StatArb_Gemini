"""
ADS v3.0 Alpha Design Philosophy Components
===========================================

Core components implementing the ADS v3.0 Alpha Design Philosophy rules.
These are shared building blocks for all ADS-compliant alpha strategies.

Components:
- §1: SignalMaturityScore (SMS) - Multiplicative signal maturation
- §3: ERAR - Expected Risk-Adjusted Return gate
- §8: Cooldown (PVSI) - PnL volatility-based cooldown

Author: StatArb_Gemini ADS Compliance
Version: 3.0.0
Date: December 3, 2025
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, ClassVar
from datetime import datetime
import logging

# JIT Optimization (Rule: Performance First)
try:
    from core_engine.utils.jit_utils import njit_conditional
except ImportError:
    def njit_conditional(func=None, **kwargs):
        if func is None: return lambda f: f
        return func

logger = logging.getLogger(__name__)

# =============================================================================
# §1. SIGNAL MATURITY SCORE (SMS) - Multiplicative Formula
# =============================================================================

@dataclass
class ADSSMSGateInputs:
    """
    Strategy-independent inputs to ADS §1 Signal Maturity Score (SMS).

    Semantics (SSOT):
    - setup_maturity: [0, 1]  (how developed/baked the setup is)
    - setup_validity_prob: [0, 1]  (probability the setup is valid for the intended direction)
    - signed_flow_support: [-1, 1] (positive supports the intended direction)
    - vol_compression: [0.5, 2.0] where VC = σ_short / σ_long
    """

    setup_maturity: float = 0.5
    setup_validity_prob: float = 0.5
    signed_flow_support: float = 0.0
    vol_compression: float = 1.0
    flow_source: str = "unknown"
    diagnostics: Dict[str, Any] = field(default_factory=dict)


@njit_conditional
def _compute_sms_core(
    exhaustion: Any,
    setup_validity_prob: Any,
    signed_flow_support: Any,
    vol_compression: Any,
    pending_bars: Any,
    decay_rate: Any,
    α: float,
    β: float,
    γ: float,
    δ: float
) -> Any:
    """Core SMS calculation logic (JIT optimized)"""
    # Clamp inputs to valid ranges
    # Using np.minimum/maximum instead of np.clip to handle scalars in Numba
    E = np.minimum(np.maximum(exhaustion, 0.001), 1.0)
    P_valid = np.minimum(np.maximum(setup_validity_prob, 0.001), 1.0)
    flow = np.minimum(np.maximum(signed_flow_support, -1.0), 1.0)
    VC = np.minimum(np.maximum(vol_compression, 0.5), 2.0)
    t = np.maximum(0, pending_bars)
    λ = np.maximum(0.0, decay_rate)

    # Multiplicative SMS formula
    #
    # High-vol hardening:
    # - Penalize adverse flow symmetrically (not just reward favorable flow).
    #   Prior logic used max(0, ofi) which ignored negative flow (dangerous in selloffs).
    # - Use an exponential flow factor for smooth, symmetric scaling:
    #       flow_factor = exp(γ * ofi)  where ofi in [-1, 1]
    sms = (
        (E ** α) *
        (P_valid ** β) *
        (np.exp(γ * flow)) *
        ((1 / VC) ** δ) *
        np.exp(-λ * t)
    )

    return np.minimum(np.maximum(sms, 0.0), 1.0)

@dataclass
class SignalMaturityScore:
    """
    ADS §1: Signal Maturity Score with Multiplicative Formula

    Formula:
        SMS = M^α × P_valid^β × exp(γ × Flow) × VC^(-δ) × e^(-λt)

    Where:
        M = Setup maturity [0, 1]
        P_valid = Setup validity probability for intended direction [0, 1]
        Flow = Signed flow support [-1, 1] (positive supports intended direction)
        VC = Volatility compression (σ_short/σ_long) [0.5, 2.0]
        t = Bars pending (≥ 0)
        λ = Decay rate (configurable via decay_rate)

    Regime-Adaptive Exponents:
        | Regime   | α    | β    | γ    | δ    |
        |----------|------|------|------|------|
        | Low Vol  | 0.30 | 0.40 | 0.20 | 0.10 |
        | Normal   | 0.35 | 0.35 | 0.20 | 0.10 |
        | High Vol | 0.40 | 0.25 | 0.25 | 0.10 |
        | Crisis   | 0.50 | 0.20 | 0.20 | 0.10 |
    """

    # Core SMS components
    exhaustion: float = 0.5          # E: Exhaustion score [0, 1]
    reversal_prob: float = 0.5       # P_rev: Reversal probability [0, 1]
    ofi_shift: float = 0.0           # ΔOFI: Order flow imbalance shift [-1, 1]
    vol_compression: float = 1.0     # VC: Volatility compression [0.5, 2.0]
    pending_bars: int = 0            # t: Bars signal has been pending

    # Configuration
    decay_rate: float = 0.05         # λ: Time decay rate
    max_pending: int = 50            # Maximum bars before signal is stale
    # Preferred strategy-independent contract (strategies should pass this and keep naming consistent).
    inputs: Optional[ADSSMSGateInputs] = None

    # Regime-adaptive exponents
    EXPONENTS: ClassVar[Dict[str, Tuple[float, float, float, float]]] = {
        'low_vol': (0.30, 0.40, 0.20, 0.10),
        'normal': (0.35, 0.35, 0.20, 0.10),
        'high_vol': (0.40, 0.25, 0.25, 0.10),
        'crisis': (0.50, 0.20, 0.20, 0.10)
    }

    def compute(self, regime: str = 'normal') -> float:
        """
        Compute multiplicative SMS score.

        Args:
            regime: Market regime ('low_vol', 'normal', 'high_vol', 'crisis')

        Returns:
            SMS score [0, 1]
        """
        # Backwards compatibility: if a strategy still passes legacy fields, translate them into
        # SSOT contract semantics.
        inputs = self.inputs or ADSSMSGateInputs(
            setup_maturity=float(self.exhaustion),
            setup_validity_prob=float(self.reversal_prob),
            signed_flow_support=float(self.ofi_shift),
            vol_compression=float(self.vol_compression),
        )

        return self.compute_vectorized(
            inputs.setup_maturity,
            inputs.setup_validity_prob,
            inputs.signed_flow_support,
            inputs.vol_compression,
            self.pending_bars,
            self.decay_rate,
            regime,
        )

    @classmethod
    def from_inputs(
        cls,
        inputs: ADSSMSGateInputs,
        *,
        pending_bars: int = 0,
        decay_rate: float = 0.05,
        max_pending: int = 50,
    ) -> "SignalMaturityScore":
        """
        Preferred constructor: strategy supplies strategy-independent inputs, SMS owns only age/decay.
        """
        return cls(
            exhaustion=float(inputs.setup_maturity),
            reversal_prob=float(inputs.setup_validity_prob),
            ofi_shift=float(inputs.signed_flow_support),
            vol_compression=float(inputs.vol_compression),
            pending_bars=int(pending_bars),
            decay_rate=float(decay_rate),
            max_pending=int(max_pending),
            inputs=inputs,
        )

    @classmethod
    def compute_vectorized(
        cls,
        exhaustion: Any,
        setup_validity_prob: Any,
        signed_flow_support: Any,
        vol_compression: Any,
        pending_bars: Any,
        decay_rate: Any,
        regime: str = 'normal'
    ) -> Any:
        """
        Vectorized computation of SMS score.
        Supports both scalar and NumPy array inputs.
        """
        # Get regime-specific exponents
        α, β, γ, δ = cls.EXPONENTS.get(regime, cls.EXPONENTS['normal'])

        return _compute_sms_core(
            exhaustion,
            setup_validity_prob,
            signed_flow_support,
            vol_compression,
            pending_bars,
            decay_rate,
            α, β, γ, δ
        )

    def is_mature(self, threshold: float, regime: str = 'normal') -> bool:
        """
        Check if signal has matured above threshold.

        Args:
            threshold: Minimum SMS score to be considered mature
            regime: Market regime for exponent selection

        Returns:
            True if signal is mature and not stale
        """
        if self.pending_bars > self.max_pending:
            return False  # Stale signal
        return self.compute(regime) >= threshold

    def is_stale(self) -> bool:
        """Check if signal has exceeded maximum pending time."""
        return self.pending_bars > self.max_pending

    def increment_pending(self):
        """Increment pending bar count."""
        self.pending_bars += 1

    def __repr__(self) -> str:
        return (f"SMS(maturity={self.exhaustion:.3f}, validity={self.reversal_prob:.3f}, "
                f"flow={self.ofi_shift:.3f}, VC={self.vol_compression:.3f}, "
                f"bars={self.pending_bars})")

# =============================================================================
# §3. EXPECTED RISK-ADJUSTED RETURN (ERAR)
# =============================================================================

@njit_conditional
def _compute_erar_cost_core(
    spread_bps: Any,
    participation: Any,
    volatility: Any,
    adverse_prob: Any,
    kyle_lambda: Any,
    holding_days: Any,
    alt_return_bps: Any
) -> Any:
    """Core ERAR cost calculation logic (JIT optimized)"""
    c_spread = spread_bps
    c_slip = volatility * np.sqrt(np.maximum(participation, 0.001)) * 10000
    c_adverse = adverse_prob * kyle_lambda * 10000
    c_opp = alt_return_bps * holding_days

    total = (
        c_spread +
        c_slip * (np.maximum(participation, 0.0) ** 0.6) +
        c_adverse +
        c_opp
    )
    return np.maximum(total, 0.1)

@njit_conditional
def _compute_erar_core(
    expected_pnl: Any,
    cvar_95: Any,
    skewness: Any,
    cost: Any,
    tail_lambda: float = 1.0
) -> Any:
    """Core ERAR calculation logic (JIT optimized)"""
    # Using np.minimum/maximum instead of np.clip to handle scalars in Numba
    omega_adj = np.minimum(np.maximum(1 + 0.1 * skewness, 0.5), 1.5)
    risk_adj_return = expected_pnl - tail_lambda * np.abs(cvar_95)
    
    # Handle zero cost case safely in JIT
    # We use a small epsilon to avoid division by zero if cost is 0
    safe_cost = np.maximum(cost, 0.0001)
    erar = (risk_adj_return / safe_cost) * omega_adj
    
    # If cost was actually <= 0, return 0
    # Using np.where to handle both scalars and arrays in JIT
    return np.where(cost <= 0, 0.0, erar)

@dataclass
class ERAR:
    """
    ADS §3: Expected Risk-Adjusted Return Gate

    Formula:
        ERAR = (E[PnL] - λ × CVaR95) / Cost × Ω_adj

    Cost Model:
        Cost = C_spread + C_slip × φ^0.6 + P_adv × λ_K + C_opp

    Where:
        C_spread = Half spread in bps
        C_slip = Slippage = σ × √(Q/ADV)
        P_adv = Adverse selection probability
        λ_K = Kyle's lambda (price impact)
        C_opp = Opportunity cost = E[R_alt] × t_hold
        Ω_adj = clip(1 + 0.1 × skew, 0.5, 1.5)

    Trade Condition: ERAR ≥ γ (default γ = 0.5)
    """

    # Expected return components
    expected_pnl: float = 0.0        # E[PnL] in bps
    cvar_95: float = 0.0             # CVaR95 (expected shortfall) in bps
    skewness: float = 0.0            # Return distribution skewness

    # Cost model inputs
    spread_bps: float = 2.0          # Half spread in basis points
    participation: float = 0.01      # Q/ADV (participation rate)
    volatility: float = 0.02         # Daily volatility (for slippage)
    adverse_prob: float = 0.1        # Adverse selection probability
    kyle_lambda: float = 0.0001      # Kyle's lambda (price impact per unit)
    holding_days: float = 1.0        # Expected holding period in days
    alt_return_bps: float = 0.5      # Alternative investment return (daily)

    # Risk aversion
    tail_lambda: float = 1.0         # Risk aversion for CVaR penalty

    def cost(self) -> float:
        """
        Calculate total transaction cost in basis points.

        Returns:
            Total cost in bps
        """
        return self.cost_vectorized(
            self.spread_bps,
            self.participation,
            self.volatility,
            self.adverse_prob,
            self.kyle_lambda,
            self.holding_days,
            self.alt_return_bps
        )

    @classmethod
    def cost_vectorized(
        cls,
        spread_bps: Any,
        participation: Any,
        volatility: Any,
        adverse_prob: Any,
        kyle_lambda: Any,
        holding_days: Any,
        alt_return_bps: Any
    ) -> Any:
        """Vectorized cost calculation"""
        return _compute_erar_cost_core(
            spread_bps, participation, volatility, adverse_prob,
            kyle_lambda, holding_days, alt_return_bps
        )

    def omega_adj(self) -> float:
        """
        Calculate omega adjustment based on skewness.

        Positive skew = favorable, increases score
        Negative skew = unfavorable, decreases score

        Returns:
            Adjustment factor [0.5, 1.5]
        """
        return self.omega_adj_vectorized(self.skewness)

    @staticmethod
    def omega_adj_vectorized(skewness: Any) -> Any:
        """Vectorized omega adjustment"""
        return np.clip(1 + 0.1 * skewness, 0.5, 1.5)

    def compute(self) -> float:
        """
        Compute ERAR score.

        Returns:
            ERAR value (higher = better risk-adjusted opportunity)
        """
        return self.compute_vectorized(
            self.expected_pnl,
            self.cvar_95,
            self.skewness,
            self.spread_bps,
            self.participation,
            self.volatility,
            self.adverse_prob,
            self.kyle_lambda,
            self.holding_days,
            self.alt_return_bps,
            self.tail_lambda
        )

    @classmethod
    def compute_vectorized(
        cls,
        expected_pnl: Any,
        cvar_95: Any,
        skewness: Any,
        spread_bps: Any,
        participation: Any,
        volatility: Any,
        adverse_prob: Any,
        kyle_lambda: Any,
        holding_days: Any,
        alt_return_bps: Any,
        tail_lambda: float = 1.0
    ) -> Any:
        """Vectorized ERAR computation"""
        cost = cls.cost_vectorized(
            spread_bps, participation, volatility, adverse_prob,
            kyle_lambda, holding_days, alt_return_bps
        )
        
        return _compute_erar_core(
            expected_pnl, cvar_95, skewness, cost, tail_lambda
        )

    def should_trade(self, gamma: float = 0.5) -> bool:
        """
        Check if trade meets minimum ERAR threshold.

        Args:
            gamma: Minimum ERAR threshold (default 0.5)

        Returns:
            True if ERAR >= gamma
        """
        return self.compute() >= gamma

    def get_diagnostics(self) -> Dict[str, float]:
        """Get detailed ERAR breakdown."""
        return {
            'expected_pnl_bps': self.expected_pnl,
            'cvar_95_bps': self.cvar_95,
            'total_cost_bps': self.cost(),
            'omega_adj': self.omega_adj(),
            'erar': self.compute(),
            'spread_cost': self.spread_bps,
            'slippage_cost': self.volatility * np.sqrt(max(self.participation, 0.001)) * 10000 * (self.participation ** 0.6),
            'opportunity_cost': self.alt_return_bps * self.holding_days
        }

    def __repr__(self) -> str:
        return f"ERAR({self.compute():.3f}, cost={self.cost():.2f}bps)"

# =============================================================================
# §8. COOLDOWN (PVSI) - PnL Volatility Spike Index
# =============================================================================

@dataclass
class Cooldown:
    """
    ADS §8: PnL Volatility Spike Index (PVSI) Cooldown

    Formula:
        PVSI = (σ_recent / σ_baseline) × (1 + λc × L_excess) × (1 + λm × M)

    Where:
        σ_recent = Std of recent PnL (20 trades)
        σ_baseline = Std of baseline PnL (100 trades)
        L_excess = max(0, consecutive_losses - 3)
        M = Regime mismatch rate
        λc = 0.5 (loss cluster penalty)
        λm = 0.3 (regime mismatch penalty)

    Trigger: PVSI ≥ 2.0
    """

    pnl_history: List[float] = field(default_factory=list)
    regime_history: List[str] = field(default_factory=list)
    consecutive_losses: int = 0

    # Configuration
    baseline_window: int = 100
    recent_window: int = 20
    threshold: float = 2.0
    loss_penalty_lambda: float = 0.5
    mismatch_penalty_lambda: float = 0.3
    cooldown_bars: int = 0  # Current cooldown countdown
    cooldown_duration: int = 50  # Bars to wait when triggered

    def base_pvsi(self) -> float:
        """Calculate base PVSI (volatility ratio)."""
        if len(self.pnl_history) < self.baseline_window:
            return 1.0

        baseline_pnl = self.pnl_history[-self.baseline_window:-self.recent_window]
        recent_pnl = self.pnl_history[-self.recent_window:]

        if len(baseline_pnl) < 10 or len(recent_pnl) < 5:
            return 1.0

        baseline_std = np.std(baseline_pnl)
        recent_std = np.std(recent_pnl)

        if baseline_std <= 0:
            return 1.0

        return recent_std / baseline_std

    def cluster_penalty(self) -> float:
        """Calculate loss cluster penalty."""
        L_excess = max(0, self.consecutive_losses - 3)
        return 1 + self.loss_penalty_lambda * L_excess

    def mismatch_penalty(self) -> float:
        """Calculate regime mismatch penalty."""
        if len(self.regime_history) < self.baseline_window:
            return 1.0

        recent = self.regime_history[-5:]
        baseline = self.regime_history[-self.baseline_window:-self.recent_window]

        if not baseline or not recent:
            return 1.0

        # Find mode of baseline
        mode = max(set(baseline), key=baseline.count)

        # Calculate mismatch rate in recent
        mismatch_rate = sum(1 for r in recent if r != mode) / len(recent)

        return 1 + self.mismatch_penalty_lambda * mismatch_rate

    def compute(self) -> float:
        """Compute full PVSI score."""
        return self.base_pvsi() * self.cluster_penalty() * self.mismatch_penalty()

    def needs_cooldown(self) -> bool:
        """Check if strategy should enter cooldown."""
        return self.compute() >= self.threshold or self.cooldown_bars > 0

    def update(self, pnl: float, regime: str):
        """
        Update cooldown state with new trade result.

        Args:
            pnl: Trade PnL (positive or negative)
            regime: Current regime label
        """
        self.pnl_history.append(pnl)
        self.regime_history.append(regime)

        # Update consecutive losses
        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

        # Check for cooldown trigger
        if self.compute() >= self.threshold:
            self.cooldown_bars = self.cooldown_duration
            logger.warning(f"⚠️ PVSI cooldown triggered: PVSI={self.compute():.2f} >= {self.threshold}")

    def tick(self):
        """Decrement cooldown counter (call each bar)."""
        if self.cooldown_bars > 0:
            self.cooldown_bars -= 1

    def get_diagnostics(self) -> Dict[str, Any]:
        """Get detailed cooldown diagnostics."""
        return {
            'pvsi': self.compute(),
            'base_pvsi': self.base_pvsi(),
            'cluster_penalty': self.cluster_penalty(),
            'mismatch_penalty': self.mismatch_penalty(),
            'consecutive_losses': self.consecutive_losses,
            'cooldown_bars_remaining': self.cooldown_bars,
            'in_cooldown': self.needs_cooldown(),
            'trade_count': len(self.pnl_history)
        }

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def compute_exhaustion(
    zscore: float,
    rsi: float,
    volume_ratio: float,
    macd_histogram: float,
    macd_histogram_prev: float,
    is_oversold: bool
) -> float:
    """
    Compute exhaustion score from multiple indicators.

    Combines Z-score magnitude with momentum exhaustion signals.

    Args:
        zscore: Current z-score
        rsi: RSI value (0-100)
        volume_ratio: Current volume / average volume
        macd_histogram: Current MACD histogram
        macd_histogram_prev: Previous MACD histogram
        is_oversold: True if looking for oversold exhaustion

    Returns:
        Exhaustion score [0, 1]
    """
    score = 0.5  # Neutral baseline

    # Z-score contribution (dislocation magnitude)
    zscore_factor = min(abs(zscore) / 3.0, 1.0)  # Cap at z=3
    score += 0.2 * zscore_factor

    # RSI momentum exhaustion
    if is_oversold:
        if rsi < 30:
            score += 0.15  # Deep oversold
        if rsi < 20:
            score += 0.10  # Extreme oversold
    else:
        if rsi > 70:
            score += 0.15  # Deep overbought
        if rsi > 80:
            score += 0.10  # Extreme overbought

    # Volume exhaustion / conviction (high-vol hardening)
    #
    # Prior logic used hard thresholds (e.g., volume_ratio > 2.0) which creates
    # brittle boundary failures (e.g., 1.97 treated as "not conviction").
    # Replace with smooth penalties/bonuses.
    def _sigmoid(x: float) -> float:
        return 1.0 / (1.0 + np.exp(-x))

    abs_z = abs(zscore)

    # Low volume at extremes = likely noise (favorable for mean reversion)
    low_vol_gate = _sigmoid((0.90 - volume_ratio) / 0.10)     # ~1 when vol_ratio << 0.9
    disloc_gate1 = _sigmoid((abs_z - 1.5) / 0.3)              # ~1 when abs_z >> 1.5
    score += 0.10 * low_vol_gate * disloc_gate1

    # High volume continuation risk = conviction (unfavorable for mean reversion)
    high_vol_gate = _sigmoid((volume_ratio - 1.50) / 0.20)    # ramps around ~1.5x
    disloc_gate2 = _sigmoid((abs_z - 2.0) / 0.25)             # ramps around abs_z≈2
    score -= 0.25 * high_vol_gate * disloc_gate2

    # MACD histogram turning (momentum shift)
    if is_oversold and macd_histogram > macd_histogram_prev:
        score += 0.10  # Histogram turning up from oversold
    elif not is_oversold and macd_histogram < macd_histogram_prev:
        score += 0.10  # Histogram turning down from overbought

    return np.clip(score, 0.0, 1.0)

def compute_reversal_probability(
    zscore: float,
    rsi: float,
    bb_position: float,
    is_oversold: bool
) -> float:
    """
    Compute reversal probability using logistic-style combining.

    Args:
        zscore: Current z-score
        rsi: RSI value (0-100)
        bb_position: Bollinger band position [0, 1]
        is_oversold: True if looking for bullish reversal

    Returns:
        Reversal probability [0, 1]
    """
    signals = []

    # Z-score signal
    if is_oversold:
        z_signal = 1 / (1 + np.exp(zscore + 1.5))  # Higher prob when z < -1.5
    else:
        z_signal = 1 / (1 + np.exp(-(zscore - 1.5)))  # Higher prob when z > 1.5
    signals.append(z_signal)

    # RSI signal
    if is_oversold:
        rsi_signal = 1 / (1 + np.exp((rsi - 30) / 10))  # Higher prob when RSI < 30
    else:
        rsi_signal = 1 / (1 + np.exp(-(rsi - 70) / 10))  # Higher prob when RSI > 70
    signals.append(rsi_signal)

    # Bollinger position signal
    if is_oversold:
        bb_signal = 1 - bb_position  # Lower BB = higher prob
    else:
        bb_signal = bb_position  # Upper BB = higher prob
    signals.append(bb_signal)

    # Geometric mean (multiplicative combining)
    prob = np.power(np.prod(signals), 1/len(signals))

    return np.clip(prob, 0.0, 1.0)

def compute_vol_compression(
    short_vol: float,
    long_vol: float
) -> float:
    """
    Compute volatility compression ratio.

    Lower values = compression = favorable for mean reversion

    Args:
        short_vol: Short-term volatility (e.g., 5-bar)
        long_vol: Long-term volatility (e.g., 20-bar)

    Returns:
        Volatility compression ratio [0.5, 2.0]
    """
    if long_vol <= 0:
        return 1.0

    ratio = short_vol / long_vol
    return np.clip(ratio, 0.5, 2.0)

def estimate_expected_pnl(
    zscore: float,
    atr: float,
    price: float,
    half_life: float,
    holding_bars: int = 10
) -> float:
    """
    Estimate expected PnL in basis points.

    Uses mean reversion assumption: price reverts to mean.

    Args:
        zscore: Current z-score (distance from mean)
        atr: Average True Range
        price: Current price
        half_life: Estimated half-life in bars
        holding_bars: Expected holding period

    Returns:
        Expected PnL in basis points
    """
    if half_life <= 0 or price <= 0:
        return 0.0

    # Expected reversion based on z-score and half-life
    # After 'holding_bars', expect z-score to decay
    decay_factor = 1 - np.exp(-0.693 * holding_bars / half_life)

    # Expected price move (in terms of standard deviations)
    expected_z_change = abs(zscore) * decay_factor

    # Convert to price (1 std ≈ ATR for daily)
    std_estimate = atr * 0.5  # Rough approximation
    expected_price_change = expected_z_change * std_estimate

    # Convert to basis points
    expected_pnl_bps = (expected_price_change / price) * 10000

    return expected_pnl_bps

def estimate_cvar_95(
    volatility: float,
    holding_days: float = 1.0
) -> float:
    """
    Estimate CVaR95 (expected shortfall) in basis points.

    Uses normal distribution approximation.
    CVaR95 ≈ σ × 2.06 for normal distribution

    Args:
        volatility: Daily volatility (decimal, e.g., 0.02 for 2%)
        holding_days: Holding period in days

    Returns:
        CVaR95 in basis points
    """
    # Scale volatility for holding period
    period_vol = volatility * np.sqrt(holding_days)

    # CVaR95 for normal: E[X | X < VaR95] ≈ -σ × 2.06
    cvar_95 = period_vol * 2.06 * 10000  # Convert to bps

    return cvar_95

# =============================================================================
# PENDING SIGNAL QUEUE
# =============================================================================

@dataclass
class PendingSignalContext:
    """Context for a pending signal awaiting maturation."""
    symbol: str
    side: str  # 'BUY' or 'SELL'
    sms: SignalMaturityScore
    erar: ERAR
    raw_signal_strength: float
    timestamp: datetime
    entry_price: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def increment_pending(self):
        """Increment pending bar count."""
        self.sms.increment_pending()

class PendingSignalQueue:
    """
    Queue for managing pending signals awaiting SMS maturation.

    Signals are added when initial conditions are met but SMS < threshold.
    Each bar, SMS is updated. When SMS >= threshold, signal is emitted.
    Stale signals (>50 bars) are automatically removed.
    """

    def __init__(self, max_pending: int = 50):
        self.pending: Dict[str, PendingSignalContext] = {}
        self.max_pending = max_pending

    def add(self, ctx: PendingSignalContext):
        """Add or update pending signal."""
        key = f"{ctx.symbol}_{ctx.side}"
        self.pending[key] = ctx

    def remove(self, symbol: str, side: str):
        """Remove pending signal."""
        key = f"{symbol}_{side}"
        if key in self.pending:
            del self.pending[key]

    def get(self, symbol: str, side: str) -> Optional[PendingSignalContext]:
        """Get pending signal if exists."""
        key = f"{symbol}_{side}"
        return self.pending.get(key)

    def has_pending(self, symbol: str) -> bool:
        """Check if symbol has any pending signals."""
        return any(k.startswith(symbol) for k in self.pending)

    def tick_all(self) -> List[str]:
        """
        Increment all pending signals and remove stale ones.

        Returns:
            List of removed signal keys
        """
        removed = []
        for key, ctx in list(self.pending.items()):
            ctx.increment_pending()
            if ctx.sms.is_stale():
                removed.append(key)
                del self.pending[key]
        return removed

    def get_mature_signals(self, threshold: float, regime: str) -> List[PendingSignalContext]:
        """
        Get all signals that have matured.

        Args:
            threshold: SMS threshold for maturity
            regime: Current market regime

        Returns:
            List of mature signal contexts
        """
        mature = []
        for key, ctx in list(self.pending.items()):
            if ctx.sms.is_mature(threshold, regime):
                mature.append(ctx)
                del self.pending[key]
        return mature

    def __len__(self):
        return len(self.pending)

    def __repr__(self):
        return f"PendingSignalQueue({len(self)} pending)"

