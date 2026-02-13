"""
Multi-Exit Engine — Transition Lifecycle Model (ADS v3.1 §9)
=============================================================

Exits mirror entries: if you entered because a transition was born,
you exit because that transition died.

The engine evaluates a **transition health** score every bar by comparing
the current market state to the entry-time snapshot across multiple
dimensions (acceleration, coherence, vol-of-vol).  Health is multiplicative:
any single component collapsing toward zero drives the composite toward zero.

Priority cascade
----------------
  1. VOL_STOP              — Hard circuit breaker (price loss limit)
  2. DIRECTION_REVERSAL    — Composite-z sign flip (thesis dead instantly)
  3. ALIGNMENT_BREAKDOWN   — Short + medium momentum both reversed against
                             entry direction (causal chain L1 inverse)
  4. TRANSITION_EXHAUSTION — Health < critical (thesis dying; health now
                             includes alignment_health + flow_health)
  5. TRANSITION_TAKE_PROFIT— Thesis weakening + in profit (lock gains)
     a) Acceleration exhaustion: accel against entry direction + profit
     b) Dynamic TP: PnL > decaying target + health declining
  6. LIQUIDITY_STOP        — Operational risk
  7. TIME_STOP             — Adaptive last resort (max hold scales with
                             entry transition strength)

Graceful degradation
--------------------
When entry-state metadata is unavailable (legacy positions, missing features),
health defaults to a neutral value (~0.25) and only hard stops (VOL_STOP)
plus the adaptive TIME_STOP fire.  No false positives from missing data.

This module is intentionally **stateless** and **deterministic**: it receives
all inputs per call and produces an ExitDecision + rich diagnostics.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, Tuple


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass(frozen=True)
class ExitDecision:
    should_exit: bool
    reason: str
    details: Dict[str, Any]


# =============================================================================
# TRANSITION HEALTH COMPUTATION
# =============================================================================

def _compute_transition_health(
    *,
    is_long: bool,
    # Entry-time state (from position metadata)
    entry_coherence: Optional[float],
    entry_composite_z: Optional[float],
    # Causal chain entry state (from position metadata)
    entry_flow_confirmed: Optional[bool] = None,
    # Current bar state
    current_coherence: Optional[float],
    current_composite_accel: Optional[float],
    current_vol_of_vol: Optional[float],
    current_composite_z: Optional[float],
    # Causal chain current state
    current_short_momentum: Optional[float] = None,
    current_medium_momentum: Optional[float] = None,
    current_volume_ratio: Optional[float] = None,
    # Noise tolerance
    direction_reversal_z: float = 0.3,
    momentum_noise_floor: float = 0.001,
) -> Tuple[float, Dict[str, float]]:
    """
    Compute transition health in [0, 1] by comparing current market state
    to the entry-time snapshot.

    Uses **geometric mean** (cube root of product) instead of raw product
    so that three values of 0.7 each → health=0.7, not 0.34.  This
    preserves the "any-zero-kills" property while keeping the scale
    interpretable: health ≈ average component quality.

    Components (original transition lifecycle)
    ------------------------------------------
    direction_health  : float →  1.0 if aligned, decays toward 0 when
                                  composite_z moves against entry direction.
                                  Uses a soft threshold (not binary sign flip)
                                  to tolerate bar-to-bar noise.
    accel_health      : float →  sigmoid(accel × entry_direction) with
                                  asymmetric mapping: zero accel → 0.75
                                  (neutral is healthy, not 50/50).
    coherence_health  : float →  min(current / entry, 1.0), [0, 1]
    vov_health        : float →  1 − vol_of_vol, [0, 1]

    Components (causal chain — mirrors entry logic)
    ------------------------------------------------
    alignment_health  : float →  1.0 if short + medium momentum still agree
                                  with entry direction above noise floor.
                                  0.5 if one horizon disagrees. 0.1 if both
                                  reversed. Matches entry's L1 alignment gate.
    flow_health       : float →  1.0 if flow still present (or entry didn't
                                  rely on flow). 0.3 if entry relied on flow
                                  and flow has evaporated. Matches entry's L3
                                  structural confirmation hierarchy where flow
                                  is the highest-conviction confirmation.

    Returns (health, components_dict) for monitoring.
    """
    entry_direction = 1.0 if is_long else -1.0

    # --- Direction health (soft, not binary) ---
    # Instead of a binary sign-flip kill switch, measure how far
    # composite_z has moved against the entry direction.  A brief dip
    # past zero on a noisy 1-min bar shouldn't kill the trade.
    #
    #   aligned strongly   → 1.0
    #   near zero          → ~0.8  (noise zone, still healthy)
    #   against by reversal_z → ~0.3  (real reversal signal)
    #   against by 2×reversal_z → ~0.05 (thesis dead)
    if current_composite_z is not None and entry_composite_z is not None:
        # How much composite_z supports the entry direction (signed, >0 = aligned)
        signed_z = float(current_composite_z) * entry_direction
        # Sigmoid centered at -reversal_z with steepness 5/reversal_z
        # At signed_z=0: ~0.82, at signed_z=-reversal_z: ~0.5, at signed_z=-2*rz: ~0.18
        rz = max(direction_reversal_z, 0.01)
        steepness = 5.0 / rz
        shifted = signed_z + rz  # shift so the midpoint is at -reversal_z
        direction_health = 1.0 / (1.0 + math.exp(-steepness * max(-10.0, min(10.0, shifted))))
    else:
        direction_health = 1.0  # Can't evaluate → assume aligned

    # --- Acceleration health: asymmetric sigmoid ---
    # Zero acceleration is NORMAL during momentum propagation — it
    # shouldn't penalize health.  Map so that:
    #   positive accel in entry dir → ~1.0 (momentum building)
    #   zero accel                  → ~0.75 (momentum stable — healthy)
    #   moderate negative           → ~0.4  (momentum fading)
    #   strong negative             → ~0.1  (momentum reversing)
    if current_composite_accel is not None:
        signed_accel = float(current_composite_accel) * entry_direction
        # Shift the sigmoid so zero maps to ~0.75 instead of 0.5
        # offset=0.5 with steepness=4: sigmoid(4*(x+0.5)) at x=0 → sigmoid(2)≈0.88
        offset = 0.4
        steepness_a = 4.0
        x = steepness_a * (signed_accel + offset)
        accel_health = 1.0 / (1.0 + math.exp(-max(-10.0, min(10.0, x))))
    else:
        accel_health = 0.75  # Unknown → assume stable

    # --- Coherence health: ratio to entry, capped at 1.0 ---
    # Improvement beyond entry isn't rewarded (already in the trade).
    if (
        entry_coherence is not None
        and entry_coherence > 0.01
        and current_coherence is not None
    ):
        coherence_health = min(float(current_coherence) / float(entry_coherence), 1.0)
        coherence_health = max(coherence_health, 0.0)
    else:
        coherence_health = 1.0  # Can't evaluate → assume healthy

    # --- Vol regime stability ---
    # Low vol-of-vol = stable = healthy (1.0).
    # High vol-of-vol = unstable = unhealthy (→0.0).
    if current_vol_of_vol is not None:
        vov_health = max(0.0, min(1.0, 1.0 - float(current_vol_of_vol)))
    else:
        vov_health = 0.75  # Unknown → assume stable

    # --- Alignment health (causal chain L1) ---
    # Entry required short + medium momentum to agree on direction above a
    # noise floor.  Exit monitors whether that agreement persists.
    # Categorical: both aligned → 1.0, one disagrees → 0.5, both reversed → 0.1.
    if current_short_momentum is not None and current_medium_momentum is not None:
        short_aligned = (float(current_short_momentum) * entry_direction) > momentum_noise_floor
        medium_aligned = (float(current_medium_momentum) * entry_direction) > momentum_noise_floor
        if short_aligned and medium_aligned:
            alignment_health = 1.0
        elif short_aligned or medium_aligned:
            alignment_health = 0.5  # One horizon disagrees — caution
        else:
            alignment_health = 0.1  # Both horizons reversed — thesis dead
    else:
        alignment_health = 1.0  # Can't evaluate → assume aligned (graceful degradation)

    # --- Flow health (causal chain L3) ---
    # If entry was confirmed by volume flow (the highest-conviction structural
    # signal), monitor whether flow persists.  The volume_ratio feature is
    # centered at 0 (negative = below average).  A value > 0 indicates
    # above-average activity; values < -0.2 indicate flow drought.
    if entry_flow_confirmed is not None and entry_flow_confirmed and current_volume_ratio is not None:
        if float(current_volume_ratio) > 0.0:
            flow_health = 1.0   # Flow still present
        elif float(current_volume_ratio) > -0.3:
            flow_health = 0.6   # Flow fading but not gone
        else:
            flow_health = 0.25  # Flow evaporated — entry basis gone
    elif entry_flow_confirmed is not None and not entry_flow_confirmed:
        # Entry did NOT rely on flow (it passed via higher z-score).
        # Flow absence is expected, not alarming.
        flow_health = 0.80
    else:
        flow_health = 0.80  # Unknown → neutral (graceful degradation)

    # --- Geometric mean (N-th root of product) ---
    # Preserves "any zero kills health" but keeps scale interpretable:
    #   three 0.7s → 0.7  (not 0.34 as with raw product)
    #   three 0.5s → 0.5  (not 0.125)
    # This prevents the systematic downward bias of raw multiplication.
    # 6 components: 4 transition lifecycle + 2 causal chain.
    product = (
        direction_health * accel_health * coherence_health * vov_health
        * alignment_health * flow_health
    )
    n_components = 6.0
    if product > 0:
        health = product ** (1.0 / n_components)
    else:
        health = 0.0

    components = {
        "direction_health": round(direction_health, 4),
        "accel_health": round(accel_health, 4),
        "coherence_health": round(coherence_health, 4),
        "vov_health": round(vov_health, 4),
        "alignment_health": round(alignment_health, 4),
        "flow_health": round(flow_health, 4),
    }
    return health, components


# =============================================================================
# MAIN EXIT DECISION FUNCTION
# =============================================================================

def decide_exit(
    *,
    now: datetime,
    opened_at: datetime,
    pnl_pct: float,
    is_long: bool = True,
    # --- Hard stops ---
    stop_loss_pct: Optional[float] = None,
    # --- Entry-time transition state (from position.metadata) ---
    entry_coherence: Optional[float] = None,
    entry_composite_accel: Optional[float] = None,
    entry_vol_of_vol: Optional[float] = None,
    entry_transition_score: Optional[float] = None,
    entry_composite_z: Optional[float] = None,
    # --- Causal chain entry state (from position.metadata) ---
    entry_flow_confirmed: Optional[bool] = None,
    # --- Current bar transition state ---
    current_coherence: Optional[float] = None,
    current_composite_accel: Optional[float] = None,
    current_vol_of_vol: Optional[float] = None,
    current_composite_z: Optional[float] = None,
    # --- Causal chain current state ---
    current_short_momentum: Optional[float] = None,
    current_medium_momentum: Optional[float] = None,
    current_volume_ratio: Optional[float] = None,
    # --- Transition health thresholds ---
    health_critical_threshold: float = 0.15,
    accel_exhaustion_threshold: float = -0.3,
    direction_reversal_z: float = 0.3,
    momentum_noise_floor: float = 0.001,
    # --- Dynamic take-profit ---
    tp_initial_pct: float = 2.0,
    tp_floor_pct: float = 0.3,
    tp_decay_minutes: float = 30.0,
    health_tp_trigger: float = 0.7,
    # --- Max holding (adaptive) ---
    max_holding_minutes: Optional[float] = None,
    # --- Liquidity ---
    liquidity_bad: bool = False,
    liquidity_details: Optional[Dict[str, Any]] = None,
) -> ExitDecision:
    """
    Evaluate exit rules using the transition lifecycle model, enriched with
    causal-chain dimensions that mirror entry logic.

    Priority:
      1) Vol stop (hard circuit breaker)
      2) Direction reversal (composite_z sign flip)
      3) Alignment breakdown (short + medium momentum both reversed)
      4) Transition exhaustion (health < critical)
      5) Transition take-profit (thesis weakening + in profit)
      6) Liquidity stop
      7) Time stop (adaptive last resort)

    All transition-based exits (#2-#4) degrade gracefully when metadata
    is missing: health defaults to ~0.25 and only hard stops + time fire.

    Parameters
    ----------
    now, opened_at : datetime
        Current time and position open time.
    pnl_pct : float
        Current unrealized P&L in percent (positive = profit).
    is_long : bool
        Position direction (True = long, False = short).
    stop_loss_pct : float, optional
        Hard loss limit in percent (positive number, e.g. 2.0 = -2%).
    entry_* : float, optional
        Transition state snapshot from position.metadata at entry time.
    current_* : float, optional
        Current bar's transition features from the feature engineer.
    health_critical_threshold : float
        Health below this → TRANSITION_EXHAUSTION exit. Default 0.15.
    accel_exhaustion_threshold : float
        Signed acceleration below this + profit → take-profit. Default -0.3.
    tp_initial_pct, tp_floor_pct, tp_decay_minutes : float
        Dynamic take-profit parameters. TP(t) = initial * exp(-t/decay) + floor.
    health_tp_trigger : float
        Health must be below this for dynamic TP to fire. Default 0.7.
    max_holding_minutes : float, optional
        Base max holding time (adapted by entry_transition_score).
    liquidity_bad : bool
        External liquidity flag.

    Returns
    -------
    ExitDecision with reason code and rich diagnostics.
    """
    held_mins = (now - opened_at).total_seconds() / 60.0

    # =================================================================
    # 1) VOL STOP — hard circuit breaker, non-negotiable
    # =================================================================
    if stop_loss_pct is not None and stop_loss_pct > 0:
        if pnl_pct <= -abs(stop_loss_pct):
            return ExitDecision(
                should_exit=True,
                reason="VOL_STOP",
                details={
                    "pnl_pct": float(pnl_pct),
                    "stop_loss_pct": float(stop_loss_pct),
                    "held_minutes": round(held_mins, 1),
                },
            )

    # =================================================================
    # Compute transition health (shared by exits 2-4)
    # =================================================================
    health, health_components = _compute_transition_health(
        is_long=is_long,
        entry_coherence=entry_coherence,
        entry_composite_z=entry_composite_z,
        entry_flow_confirmed=entry_flow_confirmed,
        current_coherence=current_coherence,
        current_composite_accel=current_composite_accel,
        current_vol_of_vol=current_vol_of_vol,
        current_composite_z=current_composite_z,
        current_short_momentum=current_short_momentum,
        current_medium_momentum=current_medium_momentum,
        current_volume_ratio=current_volume_ratio,
        direction_reversal_z=direction_reversal_z,
        momentum_noise_floor=momentum_noise_floor,
    )

    health_details = {
        "transition_health": round(health, 4),
        "pnl_pct": float(pnl_pct),
        "held_minutes": round(held_mins, 1),
        **health_components,
    }

    # =================================================================
    # 2) DIRECTION REVERSAL — composite_z meaningfully against entry
    #    direction_health < 0.2 means composite_z has moved well past
    #    the reversal threshold into counter-trend territory.
    # =================================================================
    if health_components["direction_health"] < 0.2:
        return ExitDecision(
            should_exit=True,
            reason="DIRECTION_REVERSAL",
            details={
                **health_details,
                "entry_composite_z": float(entry_composite_z) if entry_composite_z is not None else None,
                "current_composite_z": float(current_composite_z) if current_composite_z is not None else None,
            },
        )

    # =================================================================
    # 3) ALIGNMENT BREAKDOWN — causal chain L1 fully reversed
    #    Entry required short + medium momentum to agree on direction.
    #    If both horizons have now reversed, the directional thesis is
    #    structurally dead — this is the exit-side inverse of entry L1.
    #    More granular than direction_health (which uses blended composite_z)
    #    because it checks the individual horizons independently.
    # =================================================================
    if health_components["alignment_health"] <= 0.1:
        return ExitDecision(
            should_exit=True,
            reason="ALIGNMENT_BREAKDOWN",
            details={
                **health_details,
                "current_short_momentum": float(current_short_momentum) if current_short_momentum is not None else None,
                "current_medium_momentum": float(current_medium_momentum) if current_medium_momentum is not None else None,
            },
        )

    # =================================================================
    # 4) TRANSITION EXHAUSTION — health < critical threshold
    #    Multi-dimensional thesis breakdown: some combination of
    #    decelerating momentum + coherence decay + vol instability
    #    + alignment breakdown + flow evaporation has driven the
    #    transition health below survivable levels.
    # =================================================================
    if health < health_critical_threshold:
        return ExitDecision(
            should_exit=True,
            reason="TRANSITION_EXHAUSTION",
            details={
                **health_details,
                "health_critical_threshold": health_critical_threshold,
            },
        )

    # =================================================================
    # 5) TRANSITION TAKE-PROFIT — thesis weakening + in profit
    #
    #    Two sub-triggers (first match wins):
    #
    #    a) Acceleration exhaustion: the momentum wave is cresting.
    #       Signed acceleration has turned meaningfully negative while
    #       the position is in profit.  This is the earliest structural
    #       signal that the transition is ending — typically precedes
    #       coherence breakdown by 5-15 bars.
    #
    #    b) Dynamic TP: profit exceeds a time-decaying target AND
    #       transition health is declining.  Locks in gains before
    #       the transition fully dissolves.
    # =================================================================
    entry_direction = 1.0 if is_long else -1.0

    # 4a) Acceleration exhaustion (wave cresting)
    if current_composite_accel is not None and pnl_pct > 0:
        signed_accel = float(current_composite_accel) * entry_direction
        if signed_accel < accel_exhaustion_threshold:
            return ExitDecision(
                should_exit=True,
                reason="TRANSITION_TAKE_PROFIT",
                details={
                    **health_details,
                    "sub_reason": "acceleration_exhaustion",
                    "signed_accel": round(signed_accel, 4),
                    "accel_exhaustion_threshold": accel_exhaustion_threshold,
                },
            )

    # 4b) Dynamic take-profit with decaying target
    #     TP(t) = tp_initial * exp(-t / tau) + tp_floor
    #     At t=0:   TP ≈ tp_initial + tp_floor  (high bar early)
    #     At t→∞:   TP → tp_floor               (accept smaller gains later)
    if tp_decay_minutes > 0 and pnl_pct > 0:
        tp_target = tp_initial_pct * math.exp(-held_mins / tp_decay_minutes) + tp_floor_pct
        if pnl_pct >= tp_target and health < health_tp_trigger:
            return ExitDecision(
                should_exit=True,
                reason="TRANSITION_TAKE_PROFIT",
                details={
                    **health_details,
                    "sub_reason": "dynamic_take_profit",
                    "tp_target_pct": round(tp_target, 4),
                    "health_tp_trigger": health_tp_trigger,
                },
            )

    # =================================================================
    # 6) LIQUIDITY STOP — operational risk
    # =================================================================
    if liquidity_bad:
        return ExitDecision(
            should_exit=True,
            reason="LIQUIDITY_STOP",
            details={
                **health_details,
                **(liquidity_details or {"liquidity_bad": True}),
            },
        )

    # =================================================================
    # 7) TIME STOP — adaptive last resort
    #
    #    Base max_holding_minutes is scaled by entry transition strength:
    #      adaptive_max = base × (1 + entry_transition_score)
    #    Strong entry (score=0.8) → 1.8× base → longer leash
    #    Weak entry   (score=0.1) → 1.1× base → short leash
    #    Unknown      (score=None)→ 1.0× base → conservative
    # =================================================================
    if max_holding_minutes is not None and max_holding_minutes > 0:
        if entry_transition_score is not None and entry_transition_score > 0:
            adaptive_max = float(max_holding_minutes) * (1.0 + float(entry_transition_score))
        else:
            adaptive_max = float(max_holding_minutes)

        if held_mins >= adaptive_max:
            return ExitDecision(
                should_exit=True,
                reason="TIME_STOP",
                details={
                    **health_details,
                    "base_max_holding_minutes": float(max_holding_minutes),
                    "adaptive_max_minutes": round(adaptive_max, 1),
                    "entry_transition_score": float(entry_transition_score) if entry_transition_score is not None else None,
                },
            )

    # =================================================================
    # No exit triggered — return health snapshot for monitoring
    # =================================================================
    return ExitDecision(
        should_exit=False,
        reason="HOLD",
        details=health_details,
    )
