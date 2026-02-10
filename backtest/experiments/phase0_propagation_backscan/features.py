"""
Phase 0: Propagation Feature Computation
==========================================

Core PS components + diagnostics.

Design principles:
1. Compute, do not tune. Use config defaults. Move on.
2. Session-safe. No feature spans overnight gaps.
3. Point-in-time. Normalization uses ONLY past data.
4. Coarse-correct. Surgical parameters = noise, not signal.
"""

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from .config import (
    COUNTERFAIL_LOOKBACKS,
    COUNTERFAIL_TREND_WINDOW,
    DIRECTION_SMOOTH_SPAN,
    DIRECTION_WINDOW,
    FORWARD_HORIZONS,
    NORM_WINDOW,
    PATHEFF_WINDOWS,
    PROPACCEL_BASE_K,
    PROPACCEL_VOL_REF_WINDOW,
    ROUND_TRIP_COST_BPS,
    RPS_BETA_WINDOW,
    SIGMOID_SCALE,
    VOLSTORE_COMPRESSION_THRESHOLD,
    VOLSTORE_FLOOR,
    VOLSTORE_LONG_SPAN,
    VOLSTORE_MIN_COMPRESSION_BARS,
    VOLSTORE_RELEASE_RATIO,
    VOLSTORE_RELEASE_WINDOW,
    VOLSTORE_SHORT_SPAN,
)


# ═══════════════════════════════════════════════════════════
# Utilities
# ═══════════════════════════════════════════════════════════


def percentile_normalize(
    series: pd.Series, window: int, min_pct: float = 0.5
) -> pd.Series:
    """
    Point-in-time percentile rank within trailing window.

    Output: [0, 1]. Uses ONLY past data (no lookahead).
    Requires at least min_pct * window data points.
    """
    min_periods = max(int(window * min_pct), 10)

    def _pctile(x: np.ndarray) -> float:
        if len(x) < min_periods:
            return np.nan
        # Fraction of past values less than current value
        return float((x[:-1] < x[-1]).mean())

    return series.rolling(window, min_periods=min_periods).apply(
        _pctile, raw=True
    )


def session_safe_rolling_std(
    series: pd.Series, window: int, session_id: pd.Series
) -> pd.Series:
    """Rolling std that resets at session boundaries. NaN when window spans sessions."""
    result = pd.Series(np.nan, index=series.index)
    for sid, group in series.groupby(session_id):
        if len(group) >= window:
            result.loc[group.index] = group.rolling(window).std().values
    return result


# ═══════════════════════════════════════════════════════════
# Component 1: PathEff — Directional Transmission Efficiency
# ═══════════════════════════════════════════════════════════


def compute_path_efficiency(df: pd.DataFrame, window: int) -> pd.Series:
    """
    PathEff = |displacement| / (realized_vol * sqrt(window) + epsilon)

    Under random walk: E[PathEff] ~ 1.0
    PathEff >> 1: structured directional flow (straighter than noise)
    PathEff << 1: mean-reverting or choppy
    """
    close = df["close"]
    returns = close.pct_change()
    session_id = df["session_id"]

    displacement = (close - close.shift(window)).abs()

    # Session-safe realized vol
    realized_vol = session_safe_rolling_std(returns, window, session_id) * np.sqrt(
        window
    )

    epsilon = 1e-8
    path_eff = displacement / (realized_vol + epsilon)

    # NaN if window spans session boundary
    session_changed = session_id != session_id.shift(window)
    path_eff[session_changed] = np.nan

    return path_eff


def compute_multiscale_patheff(
    df: pd.DataFrame, windows: Optional[List[int]] = None
) -> pd.DataFrame:
    """Compute PathEff at multiple scales and aggregate via geometric mean."""
    windows = windows or PATHEFF_WINDOWS

    for w in windows:
        df[f"patheff_{w}"] = compute_path_efficiency(df, w)

    # Geometric mean across scales (coherence = no dispersion)
    cols = [f"patheff_{w}" for w in windows]
    log_patheff = np.log(df[cols].clip(lower=1e-8))
    df["patheff_multiscale"] = np.exp(log_patheff.mean(axis=1))

    # Percentile normalization (point-in-time)
    df["patheff_norm"] = percentile_normalize(df["patheff_multiscale"], NORM_WINDOW)

    return df


# ═══════════════════════════════════════════════════════════
# Component 2: CounterFail — Opposition Failure + Recovery
# ═══════════════════════════════════════════════════════════


def compute_counter_fail(df: pd.DataFrame) -> pd.Series:
    """
    Two-stage institutional footprint detector:
    Stage A: Did the counter-move fail? (shallow + brief)
    Stage B: Did direction reassert quickly? (recovery quality)

    Output: [0, 1] where 1 = perfect opposition failure with quick recovery.
    """
    close = df["close"]
    returns = close.pct_change()
    session_id = df["session_id"]

    # ATR for normalization (use existing if available, else compute)
    if "atr" in df.columns:
        atr = df["atr"].clip(lower=1e-8)
    else:
        tr = pd.concat(
            [
                (df["high"] - df["low"]).abs(),
                (df["high"] - close.shift(1)).abs(),
                (df["low"] - close.shift(1)).abs(),
            ],
            axis=1,
        ).max(axis=1)
        atr = tr.rolling(14).mean().clip(lower=1e-8)

    # Dominant direction over trend window
    direction = np.sign(close - close.shift(COUNTERFAIL_TREND_WINDOW))

    # Identify counter-move bars (return opposes dominant direction)
    bar_return_sign = np.sign(returns)
    is_counter = (bar_return_sign != direction) & (direction != 0)

    # Counter-move depth: adverse excursion in ATR units
    adverse_move = returns.abs() * is_counter.astype(float)
    depth_in_atr = adverse_move / atr

    # Counter-move streaks (duration)
    counter_groups = (~is_counter).cumsum()
    counter_streaks = is_counter.groupby(counter_groups).cumsum()

    scores = pd.Series(np.nan, index=df.index)

    for lookback in COUNTERFAIL_LOOKBACKS:
        # Average depth of counter-moves in window
        avg_depth = depth_in_atr.rolling(lookback, min_periods=lookback // 2).mean()

        # Average duration of counter-move episodes
        avg_duration = counter_streaks.rolling(
            lookback, min_periods=lookback // 2
        ).mean()

        # Recovery quality: after counter-move ends, how quickly does direction resume?
        # Measure: fraction of next 5 bars aligned with dominant direction
        post_counter = is_counter.shift(1).fillna(False) & ~is_counter
        forward_alignment = pd.Series(0.0, index=df.index)
        for offset in range(1, 6):
            shifted_sign = bar_return_sign.shift(-offset)
            forward_alignment += (shifted_sign == direction).astype(float)
        recovery = forward_alignment / 5.0
        # Only measure at post-counter points, then fill forward for rolling
        recovery_at_events = recovery.where(post_counter)
        avg_recovery = (
            recovery_at_events.rolling(lookback, min_periods=1)
            .mean()
            .ffill()
            .clip(0, 1)
        )

        # Two-stage score
        fail_score = (1 / (1 + avg_depth)) * (1 / (1 + avg_duration))
        episode_score = fail_score * avg_recovery.fillna(0.5)

        # NaN at session boundaries
        session_changed = session_id != session_id.shift(lookback)
        episode_score[session_changed] = np.nan

        scores = scores.combine_first(episode_score)

    return scores.clip(0, 1)


# ═══════════════════════════════════════════════════════════
# Component 3: VolStore — Stored Energy + Release
# ═══════════════════════════════════════════════════════════


def compute_vol_store(df: pd.DataFrame) -> pd.Series:
    """
    VolStore captures the compression -> release transition.

    Compression alone is meaningless. Release alone is noise.
    The informational object is: compression -> release transition.
    """
    returns = df["close"].pct_change()

    vol_short = returns.ewm(span=VOLSTORE_SHORT_SPAN).std()
    vol_long = returns.ewm(span=VOLSTORE_LONG_SPAN).std()

    compression_ratio = vol_short / vol_long.clip(lower=1e-8)

    # Compression detection
    is_compressed = compression_ratio < VOLSTORE_COMPRESSION_THRESHOLD

    # Compression duration (consecutive bars)
    comp_groups = (~is_compressed).cumsum()
    compression_streak = is_compressed.groupby(comp_groups).cumsum()

    # Release detection: vol_short expanding rapidly after sufficient compression
    vol_short_change = vol_short / vol_short.shift(3).clip(lower=1e-8)
    is_releasing = (vol_short_change > VOLSTORE_RELEASE_RATIO) & (
        compression_streak.shift(1) >= VOLSTORE_MIN_COMPRESSION_BARS
    )

    # Energy score: depth * log(1 + duration)
    compression_depth = (1 - compression_ratio).clip(lower=0)
    raw_store = compression_depth * np.log1p(compression_streak)

    # Only produce score when actively releasing (within release window)
    release_window = is_releasing.rolling(VOLSTORE_RELEASE_WINDOW).sum() > 0

    vol_store = pd.Series(0.0, index=df.index)
    vol_store[release_window] = raw_store[release_window]

    # Normalize (point-in-time)
    max_store = raw_store.rolling(NORM_WINDOW, min_periods=NORM_WINDOW // 2).quantile(
        0.99
    )
    vol_store_norm = (vol_store / max_store.clip(lower=1e-8)).clip(0, 1)

    return vol_store_norm


# ═══════════════════════════════════════════════════════════
# Component 4: PropAccel — Formation Velocity of Structure
# ═══════════════════════════════════════════════════════════


def compute_prop_accel(df: pd.DataFrame) -> pd.Series:
    """
    PropAccel = d(PathEff) / dt with regime-adaptive lookback.

    High vol -> longer lookback (more bars to confirm).
    Low vol -> shorter lookback (signal arrives faster).
    """
    patheff = df["patheff_multiscale"]
    returns = df["close"].pct_change()

    vol_current = returns.ewm(span=20).std()
    vol_ref = (
        returns.rolling(PROPACCEL_VOL_REF_WINDOW)
        .std()
        .rolling(PROPACCEL_VOL_REF_WINDOW)
        .mean()
    )

    # Adaptive lookback: scale base_k by vol ratio, bounded [3, 15]
    vol_ratio = (vol_current / vol_ref.clip(lower=1e-8)).clip(0.5, 3.0)
    adaptive_k = (PROPACCEL_BASE_K * vol_ratio).round().clip(3, 15)

    # Use median adaptive_k for vectorized computation
    median_k = int(adaptive_k.median()) if not adaptive_k.isna().all() else PROPACCEL_BASE_K
    prop_accel = (patheff - patheff.shift(median_k)) / median_k

    return prop_accel


def normalize_prop_accel(raw_accel: pd.Series) -> pd.Series:
    """Normalize PropAccel to roughly [-1, 1] via trailing percentile."""
    abs_ref = (
        raw_accel.abs()
        .rolling(NORM_WINDOW, min_periods=NORM_WINDOW // 2)
        .quantile(0.95)
    )
    return (raw_accel / abs_ref.clip(lower=1e-8)).clip(-1, 1)


# ═══════════════════════════════════════════════════════════
# Propagation Direction
# ═══════════════════════════════════════════════════════════


def compute_propagation_direction(df: pd.DataFrame) -> pd.Series:
    """
    Signed direction of propagation. +1 = up, -1 = down.

    Based on displacement sign over dominant PathEff window, smoothed.
    """
    displacement = df["close"] - df["close"].shift(DIRECTION_WINDOW)
    smooth = displacement.ewm(span=DIRECTION_SMOOTH_SPAN).mean()
    return np.sign(smooth)


# ═══════════════════════════════════════════════════════════
# Propagation Score Aggregation
# ═══════════════════════════════════════════════════════════


def compute_propagation_score(df: pd.DataFrame) -> pd.Series:
    """
    PS = (PathEff * CounterFail * max(VolStore, floor) * sigmoid(PropAccel))^(1/4)

    Geometric mean: weak components veto the score.
    VolStore floor: allows continuation trades without prior compression.
    Sigmoid on PropAccel: maps acceleration to (0, 1) smoothly.
    """
    patheff = df["patheff_norm"].clip(lower=1e-8)
    counterfail = df["counterfail_norm"].clip(lower=1e-8)
    volstore = df["volstore_norm"].clip(lower=VOLSTORE_FLOOR)

    # Sigmoid maps PropAccel_norm from [-1,1] to (0,1)
    prop_accel_sigmoid = 1 / (1 + np.exp(-SIGMOID_SCALE * df["prop_accel_norm"]))
    prop_accel_sigmoid = prop_accel_sigmoid.clip(lower=1e-8)

    ps = (patheff * counterfail * volstore * prop_accel_sigmoid) ** 0.25

    return ps


# ═══════════════════════════════════════════════════════════
# Diagnostics (Feature Layer — consumed by strategy + risk)
# ═══════════════════════════════════════════════════════════


def compute_diagnostics(df: pd.DataFrame) -> pd.DataFrame:
    """Compute PS diagnostic metadata."""
    # PS velocity: rate of change (campaign vs spike classifier)
    df["ps_velocity"] = df["ps"].diff(3) / 3

    # Component divergence: std across normalized components
    components = df[["patheff_norm", "counterfail_norm", "volstore_norm"]].copy()
    components["propaccel_sig"] = 1 / (
        1 + np.exp(-SIGMOID_SCALE * df["prop_accel_norm"])
    )
    df["ps_component_divergence"] = components.std(axis=1)

    return df


# ═══════════════════════════════════════════════════════════
# Relative Propagation Strength (Cross-Sectional)
# ═══════════════════════════════════════════════════════════


def compute_rps(
    all_data: Dict[str, pd.DataFrame],
    market_proxy: str = "SPY",
) -> Dict[str, pd.DataFrame]:
    """
    RPS = Symbol_PS - beta_PS * Market_PS

    Decomposes propagation into systematic (beta) and idiosyncratic components.
    Beta-adjusted: numerically stable, regime-invariant.
    """
    if market_proxy not in all_data:
        # If market proxy unavailable, skip RPS
        for symbol in all_data:
            all_data[symbol]["rps"] = 0.0
        return all_data

    market_ps = all_data[market_proxy]["ps"]

    for symbol, df in all_data.items():
        if symbol == market_proxy:
            df["rps"] = 0.0
            continue

        symbol_ps = df["ps"]

        # Rolling OLS beta: cov(symbol, market) / var(market)
        rolling_cov = symbol_ps.rolling(RPS_BETA_WINDOW, min_periods=RPS_BETA_WINDOW // 2).cov(
            market_ps
        )
        rolling_var = market_ps.rolling(RPS_BETA_WINDOW, min_periods=RPS_BETA_WINDOW // 2).var()
        beta_ps = (rolling_cov / rolling_var.clip(lower=1e-8)).clip(-3, 3)

        df["rps"] = symbol_ps - beta_ps * market_ps

    return all_data


# ═══════════════════════════════════════════════════════════
# Forward Returns
# ═══════════════════════════════════════════════════════════


def compute_forward_returns(
    df: pd.DataFrame, horizons: Optional[List[int]] = None
) -> pd.DataFrame:
    """
    Compute direction-adjusted forward returns.

    CRITICAL SPECIFICATIONS:
    - Entry: at CLOSE of signal bar
    - Exit: at CLOSE of bar t+horizon
    - Direction: signed by propagation direction at entry
    - Cost: round-trip deducted
    - Session spanning: flagged (not excluded)
    """
    horizons = horizons or FORWARD_HORIZONS
    direction = df["prop_direction"]

    for h in horizons:
        # Raw forward return (bps)
        raw_fwd = (df["close"].shift(-h) / df["close"] - 1) * 10000

        # Direction-adjusted: positive = correct direction trade
        df[f"fwd_return_{h}bar_bps"] = raw_fwd * direction

        # Net of costs
        df[f"fwd_return_{h}bar_net_bps"] = (
            df[f"fwd_return_{h}bar_bps"] - ROUND_TRIP_COST_BPS
        )

        # Flag returns that span overnight
        if "is_session_start" in df.columns:
            session_starts_ahead = (
                df["is_session_start"].shift(-1).rolling(h).sum()
            )
            df[f"fwd_spans_overnight_{h}bar"] = session_starts_ahead > 0
        else:
            df[f"fwd_spans_overnight_{h}bar"] = False

    return df


# ═══════════════════════════════════════════════════════════
# Master Feature Pipeline
# ═══════════════════════════════════════════════════════════


def compute_all_features(
    df: pd.DataFrame,
    patheff_windows: Optional[List[int]] = None,
) -> pd.DataFrame:
    """
    Compute all propagation features for a single symbol.

    Call this once per symbol. Features are session-safe and point-in-time.
    """
    # PathEff (multi-scale + normalized)
    df = compute_multiscale_patheff(df, windows=patheff_windows)

    # CounterFail (with recovery quality)
    df["counterfail_raw"] = compute_counter_fail(df)
    df["counterfail_norm"] = percentile_normalize(df["counterfail_raw"], NORM_WINDOW)

    # VolStore (compression -> release)
    df["volstore_norm"] = compute_vol_store(df)

    # PropAccel (adaptive lookback)
    df["prop_accel_raw"] = compute_prop_accel(df)
    df["prop_accel_norm"] = normalize_prop_accel(df["prop_accel_raw"])

    # Propagation direction
    df["prop_direction"] = compute_propagation_direction(df)

    # Propagation Score
    df["ps"] = compute_propagation_score(df)

    # Diagnostics
    df = compute_diagnostics(df)

    return df
