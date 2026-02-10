"""
Phase 0: Statistical Test Battery
===================================

13 tests, ordered. Each returns a dict with at minimum a 'PASS' key (bool).

Design: detect state first, then validate economics. Never reverse this order.
"""

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from scipy.stats import normaltest, pearsonr, spearmanr

from .config import (
    BLOCK_SIZE,
    FORWARD_HORIZONS,
    KILL_MAE_IMPROVEMENT_PCT,
    KILL_MAX_INVERSIONS,
    KILL_MIN_REGIMES_PASS,
    MIN_OBSERVATIONS_PER_CELL,
    N_PERMUTATIONS,
    NORM_WINDOW,
    PRIMARY_HORIZON,
    ROUND_TRIP_COST_BPS,
    SIGNIFICANCE_LEVEL,
)


# ═══════════════════════════════════════════════
# Block Permutation Test (temporal dependence)
# ═══════════════════════════════════════════════


def block_permutation_test(
    quintiles: pd.Series,
    returns: pd.Series,
    n_perms: int = N_PERMUTATIONS,
    block_size: int = BLOCK_SIZE,
) -> float:
    """
    Test Q5 vs Q1 return difference using block permutation.

    Block bootstrap preserves temporal autocorrelation structure.
    Returns: p-value.
    """
    q5 = quintiles == 5
    q1 = quintiles == 1

    q5_returns = returns[q5].dropna()
    q1_returns = returns[q1].dropna()

    if len(q5_returns) < 10 or len(q1_returns) < 10:
        return 1.0  # insufficient data

    observed_diff = q5_returns.mean() - q1_returns.mean()

    # Block permutation
    n = len(quintiles)
    n_blocks = n // block_size

    if n_blocks < 3:
        return 1.0

    null_diffs = []
    rng = np.random.default_rng(42)

    for _ in range(n_perms):
        # Shuffle entire blocks
        perm = rng.permutation(n_blocks)
        idx_perm = np.concatenate(
            [np.arange(b * block_size, (b + 1) * block_size) for b in perm]
        )
        idx_perm = idx_perm[idx_perm < n]

        shuffled_q = quintiles.iloc[idx_perm].values
        shuffled_r = returns.iloc[idx_perm].values

        sq5 = shuffled_q == 5
        sq1 = shuffled_q == 1

        if sq5.sum() > 0 and sq1.sum() > 0:
            null_diffs.append(shuffled_r[sq5].mean() - shuffled_r[sq1].mean())

    if not null_diffs:
        return 1.0

    return float((np.array(null_diffs) >= observed_diff).mean())


# ═══════════════════════════════════════════════
# Helper: Quintile Assignment
# ═══════════════════════════════════════════════


def _assign_quintiles(ps: pd.Series) -> pd.Series:
    """Assign PS quintiles. Handles duplicate boundaries gracefully."""
    try:
        return pd.qcut(ps, 5, labels=[1, 2, 3, 4, 5], duplicates="drop")
    except ValueError:
        # Fallback: use rank-based assignment
        ranks = ps.rank(method="first", pct=True)
        return pd.cut(ranks, bins=5, labels=[1, 2, 3, 4, 5])


def _thin_entries(entries: pd.Series, min_gap: int = 5) -> pd.Series:
    """Ensure minimum gap between entries to avoid autocorrelation clustering."""
    thinned = entries.copy()
    last_idx = -min_gap - 1
    for i in range(len(entries)):
        if entries.iloc[i]:
            if (i - last_idx) >= min_gap:
                last_idx = i
            else:
                thinned.iloc[i] = False
    return thinned


# ═══════════════════════════════════════════════
# Test 1: State Detection — Distribution
# ═══════════════════════════════════════════════


def test_state_detection(df: pd.DataFrame) -> Dict[str, Any]:
    """Does PS identify a distinct market condition?"""
    ps = df["ps"].dropna()

    if len(ps) < 100:
        return {"PASS": False, "reason": "insufficient data"}

    results: Dict[str, Any] = {
        "n_observations": len(ps),
        "mean": float(ps.mean()),
        "std": float(ps.std()),
        "skewness": float(ps.skew()),
        "kurtosis": float(ps.kurtosis()),
        "is_right_skewed": float(ps.skew()) > 0.3,
    }

    # Normality test (we WANT rejection — markets hide regimes in non-normal distributions)
    stat, pval = normaltest(ps.values)
    results["normality_pvalue"] = float(pval)
    results["is_non_gaussian"] = pval < 0.05

    # Hartigan's dip test (optional)
    try:
        from diptest import diptest

        dip_stat, dip_pval = diptest(ps.values)
        results["dip_statistic"] = float(dip_stat)
        results["dip_pvalue"] = float(dip_pval)
        results["is_multimodal"] = dip_pval < 0.05
    except ImportError:
        results["dip_test"] = "SKIPPED (diptest not installed)"
        results["is_multimodal"] = None

    # PASS: non-Gaussian AND (right-skewed or multimodal)
    results["PASS"] = results["is_non_gaussian"] and (
        results["is_right_skewed"]
        or results.get("is_multimodal", False)
    )

    return results


# ═══════════════════════════════════════════════
# Test 2: Temporal Clustering
# ═══════════════════════════════════════════════


def test_temporal_clustering(
    df: pd.DataFrame, threshold_pctile: float = 0.80
) -> Dict[str, Any]:
    """Does high PS persist? Or is it random jitter?"""
    ps = df["ps"].dropna()

    if len(ps) < 100:
        return {"PASS": False, "reason": "insufficient data"}

    threshold = ps.quantile(threshold_pctile)
    is_high = ps > threshold

    # Episode durations
    episodes = (is_high != is_high.shift(1)).cumsum()
    episode_durations = is_high.groupby(episodes).sum()
    episode_durations = episode_durations[episode_durations > 0]

    if len(episode_durations) == 0:
        return {"PASS": False, "reason": "no high-PS episodes"}

    results = {
        "n_episodes": len(episode_durations),
        "median_duration_bars": float(episode_durations.median()),
        "mean_duration_bars": float(episode_durations.mean()),
        "max_duration_bars": float(episode_durations.max()),
        "p90_duration_bars": float(episode_durations.quantile(0.9)),
    }

    # PASS: median ≥5 bars (propagation should persist ≥5 minutes at 1-min)
    results["PASS"] = results["median_duration_bars"] >= 5

    return results


# ═══════════════════════════════════════════════
# Test 3: Conditional Returns (Quintile)
# ═══════════════════════════════════════════════


def test_conditional_returns(
    df: pd.DataFrame, horizon: int = PRIMARY_HORIZON
) -> Dict[str, Any]:
    """When PS is high, are returns different?"""
    col = f"fwd_return_{horizon}bar_net_bps"
    ps = df["ps"].dropna()
    fwd = df[col].dropna() if col in df.columns else pd.Series(dtype=float)

    common = ps.index.intersection(fwd.index)
    if len(common) < MIN_OBSERVATIONS_PER_CELL * 5:
        return {"PASS": False, "reason": "insufficient data", "table": {}}

    ps = ps.loc[common]
    fwd = fwd.loc[common]

    quintiles = _assign_quintiles(ps)

    table: Dict[str, Dict[str, float]] = {}
    for q in range(1, 6):
        mask = quintiles == q
        qr = fwd[mask]
        table[f"Q{q}"] = {
            "n_obs": int(mask.sum()),
            "mean_bps": float(qr.mean()) if len(qr) > 0 else np.nan,
            "median_bps": float(qr.median()) if len(qr) > 0 else np.nan,
            "std_bps": float(qr.std()) if len(qr) > 0 else np.nan,
            "skew": float(qr.skew()) if len(qr) > 2 else np.nan,
            "hit_rate": float((qr > 0).mean()) if len(qr) > 0 else np.nan,
            "p95_loss_bps": float(qr.quantile(0.05)) if len(qr) > 0 else np.nan,
        }

    results = {
        "table": table,
        "q5_minus_q1_mean": table["Q5"]["mean_bps"] - table["Q1"]["mean_bps"],
        "q5_minus_q1_hitrate": table["Q5"]["hit_rate"] - table["Q1"]["hit_rate"],
        "q5_skew_improvement": table["Q5"]["skew"] - table["Q1"]["skew"],
        "horizon": horizon,
    }

    return results


# ═══════════════════════════════════════════════
# Test 4: Monotonicity
# ═══════════════════════════════════════════════


def test_monotonicity(quintile_table: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
    """Clean Q1 < Q2 < Q3 < Q4 < Q5 gradient in forward returns."""
    if not quintile_table:
        return {"PASS": False, "reason": "no quintile data"}

    means = [
        quintile_table.get(f"Q{q}", {}).get("mean_bps", np.nan)
        for q in range(1, 6)
    ]

    if any(np.isnan(m) for m in means):
        return {"PASS": False, "reason": "NaN in quintile means"}

    inversions = sum(1 for i in range(4) if means[i + 1] < means[i])

    corr, pval = spearmanr(list(range(1, 6)), means)

    results = {
        "quintile_means": means,
        "inversions": inversions,
        "spearman_corr": float(corr),
        "spearman_pval": float(pval),
        "PASS": inversions <= KILL_MAX_INVERSIONS and corr > 0.8,
    }

    return results


# ═══════════════════════════════════════════════
# Test 5: Left Tail / MAE
# ═══════════════════════════════════════════════


def test_left_tail(df: pd.DataFrame, horizon: int = 30) -> Dict[str, Any]:
    """Does high PS reduce maximum adverse excursion?"""
    ps = df["ps"].dropna()
    direction = df["prop_direction"]
    close = df["close"]

    common = ps.dropna().index
    if len(common) < MIN_OBSERVATIONS_PER_CELL * 5:
        return {"PASS": False, "reason": "insufficient data", "mae_by_quintile": {}}

    # Compute MAE vectorized (approximate: worst 1-bar adverse within window)
    mae = pd.Series(np.nan, index=df.index)
    for i in range(len(df) - horizon):
        entry_price = close.iloc[i]
        if entry_price == 0 or np.isnan(entry_price):
            continue
        future_prices = close.iloc[i + 1 : i + horizon + 1]
        d = direction.iloc[i]
        if d == 1:
            worst = (future_prices.min() - entry_price) / entry_price * 10000
        elif d == -1:
            worst = (entry_price - future_prices.max()) / entry_price * 10000
        else:
            continue
        mae.iloc[i] = worst

    df_local = pd.DataFrame({"ps": ps, "mae": mae}).dropna()
    if len(df_local) < MIN_OBSERVATIONS_PER_CELL * 5:
        return {"PASS": False, "reason": "insufficient MAE data", "mae_by_quintile": {}}

    quintiles = _assign_quintiles(df_local["ps"])

    mae_by_q: Dict[str, Dict[str, float]] = {}
    for q in range(1, 6):
        mask = quintiles == q
        qm = df_local["mae"][mask]
        mae_by_q[f"Q{q}"] = {
            "mean_mae_bps": float(qm.mean()),
            "median_mae_bps": float(qm.median()),
            "p95_mae_bps": float(qm.quantile(0.05)),  # 5th pctile = deepest
        }

    q5_p95 = mae_by_q["Q5"]["p95_mae_bps"]
    q1_p95 = mae_by_q["Q1"]["p95_mae_bps"]

    # Both negative; improvement means Q5 less negative (closer to 0)
    improvement_pct = (
        (1 - q5_p95 / q1_p95) * 100 if q1_p95 != 0 and q1_p95 < 0 else 0
    )

    results = {
        "mae_by_quintile": mae_by_q,
        "tail_improvement_pct": float(improvement_pct),
        "PASS": improvement_pct >= KILL_MAE_IMPROVEMENT_PCT,
    }

    return results


# ═══════════════════════════════════════════════
# Test 6: Statistical Significance
# ═══════════════════════════════════════════════


def test_significance(
    df: pd.DataFrame, horizon: int = PRIMARY_HORIZON
) -> Dict[str, Any]:
    """Block-bootstrap permutation test for Q5 vs Q1."""
    col = f"fwd_return_{horizon}bar_net_bps"
    ps = df["ps"].dropna()
    fwd = df[col].dropna() if col in df.columns else pd.Series(dtype=float)

    common = ps.index.intersection(fwd.index)
    ps = ps.loc[common]
    fwd = fwd.loc[common]

    quintiles = _assign_quintiles(ps)

    p_value = block_permutation_test(quintiles, fwd)

    return {
        "p_value": float(p_value),
        "block_size": BLOCK_SIZE,
        "n_permutations": N_PERMUTATIONS,
        "PASS": p_value < SIGNIFICANCE_LEVEL,
    }


# ═══════════════════════════════════════════════
# Test 7: Regime Invariance
# ═══════════════════════════════════════════════


def test_regime_invariance(
    df: pd.DataFrame, horizon: int = PRIMARY_HORIZON
) -> Dict[str, Any]:
    """Does PS work across volatility regimes?"""
    returns = df["close"].pct_change()
    col = f"fwd_return_{horizon}bar_net_bps"

    # 20-day realized vol (rolling, in bars)
    vol_window = 20 * 390  # 20 trading days
    vol_20d = returns.rolling(min(vol_window, len(returns) // 3)).std()

    try:
        vol_terciles = pd.qcut(vol_20d, 3, labels=["low_vol", "mid_vol", "high_vol"])
    except ValueError:
        vol_terciles = pd.cut(
            vol_20d.rank(pct=True), bins=3, labels=["low_vol", "mid_vol", "high_vol"]
        )

    results_by_regime: Dict[str, Any] = {}
    regime_passes = 0

    for regime in ["low_vol", "mid_vol", "high_vol"]:
        mask = vol_terciles == regime
        regime_df = df[mask]

        ps = regime_df["ps"].dropna()
        fwd = regime_df[col].dropna() if col in regime_df.columns else pd.Series(dtype=float)

        common = ps.index.intersection(fwd.index)
        if len(common) < MIN_OBSERVATIONS_PER_CELL * 5:
            results_by_regime[regime] = {"SKIP": "insufficient data"}
            continue

        quintiles = _assign_quintiles(ps.loc[common])
        means = []
        for q in range(1, 6):
            qr = fwd.loc[common][quintiles == q]
            means.append(float(qr.mean()) if len(qr) > 0 else np.nan)

        inversions = sum(
            1 for i in range(4) if not np.isnan(means[i + 1]) and not np.isnan(means[i]) and means[i + 1] < means[i]
        )

        q5_q1 = means[4] - means[0] if not (np.isnan(means[4]) or np.isnan(means[0])) else 0
        regime_pass = q5_q1 > 0 and inversions <= 2

        if regime_pass:
            regime_passes += 1

        results_by_regime[regime] = {
            "q5_minus_q1": float(q5_q1),
            "quintile_means": means,
            "inversions": inversions,
            "n_observations": len(common),
            "PASS": regime_pass,
        }

    return {
        "by_regime": results_by_regime,
        "regimes_passed": regime_passes,
        "PASS": regime_passes >= KILL_MIN_REGIMES_PASS,
    }


# ═══════════════════════════════════════════════
# Test 8: Parameter Perturbation
# ═══════════════════════════════════════════════


def test_parameter_robustness(
    df_raw: pd.DataFrame,
    perturbation_sets: Optional[List[List[int]]] = None,
) -> Dict[str, Any]:
    """Does performance degrade gracefully across parameter choices?"""
    from .config import PERTURBATION_WINDOW_SETS
    from .features import compute_all_features, compute_forward_returns

    sets = perturbation_sets or PERTURBATION_WINDOW_SETS
    col = f"fwd_return_{PRIMARY_HORIZON}bar_net_bps"

    results: Dict[str, Any] = {}
    q5_q1_diffs: List[float] = []

    for i, windows in enumerate(sets):
        test_df = compute_all_features(df_raw.copy(), patheff_windows=windows)
        test_df = compute_forward_returns(test_df, [PRIMARY_HORIZON])

        ps = test_df["ps"].dropna()
        fwd = test_df[col].dropna() if col in test_df.columns else pd.Series(dtype=float)
        common = ps.index.intersection(fwd.index)

        if len(common) < MIN_OBSERVATIONS_PER_CELL * 5:
            results[f"window_set_{i}"] = {"windows": windows, "SKIP": "insufficient"}
            continue

        quintiles = _assign_quintiles(ps.loc[common])
        q5 = fwd.loc[common][quintiles == 5].mean()
        q1 = fwd.loc[common][quintiles == 1].mean()
        diff = q5 - q1

        results[f"window_set_{i}"] = {"windows": windows, "q5_minus_q1": float(diff)}
        q5_q1_diffs.append(diff)

    if not q5_q1_diffs:
        return {"PASS": False, "reason": "no valid window sets"}

    arr = np.array(q5_q1_diffs)
    positive = arr[arr > 0]

    if len(positive) >= 3:
        ratio = positive.max() / max(positive.min(), 1e-8)
        graceful = ratio < 5.0
    else:
        graceful = False

    results["all_positive"] = int((arr > 0).sum())
    results["total_sets"] = len(sets)
    results["PASS"] = graceful and results["all_positive"] >= len(sets) - 1

    return results


# ═══════════════════════════════════════════════
# Test 9: RPS Validation
# ═══════════════════════════════════════════════


def test_rps_validation(
    all_data: Dict[str, pd.DataFrame], horizon: int = PRIMARY_HORIZON
) -> Dict[str, Any]:
    """Does idiosyncratic propagation outperform beta-driven?"""
    col = f"fwd_return_{horizon}bar_net_bps"

    high_ps_high_rps: List[float] = []
    high_ps_low_rps: List[float] = []

    for symbol, df in all_data.items():
        if symbol in ["SPY", "QQQ"]:
            continue

        ps = df["ps"]
        rps = df.get("rps", pd.Series(dtype=float))
        fwd = df[col] if col in df.columns else pd.Series(dtype=float)

        if ps.isna().all() or rps.isna().all():
            continue

        high_ps = ps > ps.quantile(0.8)
        high_rps = rps > rps.quantile(0.6)
        low_rps = rps < rps.quantile(0.4)

        mask_idio = high_ps & high_rps
        mask_beta = high_ps & low_rps

        high_ps_high_rps.extend(fwd[mask_idio].dropna().tolist())
        high_ps_low_rps.extend(fwd[mask_beta].dropna().tolist())

    idio = np.array(high_ps_high_rps) if high_ps_high_rps else np.array([])
    beta = np.array(high_ps_low_rps) if high_ps_low_rps else np.array([])

    results = {
        "idio_mean_bps": float(idio.mean()) if len(idio) > 0 else np.nan,
        "beta_mean_bps": float(beta.mean()) if len(beta) > 0 else np.nan,
        "idio_mae_p95": float(np.percentile(idio, 5)) if len(idio) > 30 else np.nan,
        "beta_mae_p95": float(np.percentile(beta, 5)) if len(beta) > 30 else np.nan,
        "idio_n": len(idio),
        "beta_n": len(beta),
    }

    results["idio_outperforms"] = (
        not np.isnan(results["idio_mean_bps"])
        and not np.isnan(results["beta_mean_bps"])
        and results["idio_mean_bps"] > results["beta_mean_bps"]
    )
    # Informational, not a kill criterion
    results["PASS"] = results["idio_outperforms"]

    return results


# ═══════════════════════════════════════════════
# Test 10: Trade Geometry
# ═══════════════════════════════════════════════


def test_trade_geometry(
    df: pd.DataFrame,
    entry_threshold_pctile: float = 0.80,
    horizon: int = 30,
) -> Dict[str, Any]:
    """Simulate naive entries at high PS. Measure trade behavior, not just returns."""
    ps = df["ps"]
    direction = df["prop_direction"]
    close = df["close"]

    threshold = ps.quantile(entry_threshold_pctile)
    entries = ps > threshold
    entries = _thin_entries(entries, min_gap=5)

    trades: List[Dict[str, float]] = []

    for idx in df.index[entries]:
        pos = df.index.get_loc(idx)
        if pos + horizon >= len(df):
            continue

        entry_price = close.iloc[pos]
        if entry_price == 0 or np.isnan(entry_price):
            continue

        trade_dir = direction.iloc[pos]
        if trade_dir == 0 or np.isnan(trade_dir):
            continue

        future_prices = close.iloc[pos + 1 : pos + horizon + 1]

        # Direction-adjusted path (bps)
        if trade_dir == 1:
            adj_path = (future_prices.values - entry_price) / entry_price * 10000
        else:
            adj_path = (entry_price - future_prices.values) / entry_price * 10000

        if len(adj_path) == 0:
            continue

        max_heat = float(adj_path.min())
        ttp_arr = np.where(adj_path > 0)[0]
        time_to_profit = int(ttp_arr[0]) if len(ttp_arr) > 0 else horizon
        final_pnl = float(adj_path[-1] - ROUND_TRIP_COST_BPS)
        max_favorable = float(adj_path.max())
        excursion_ratio = max_favorable / max(abs(max_heat), 1e-8)

        # Path smoothness
        if len(adj_path) > 2:
            ideal = np.linspace(0, adj_path[-1], len(adj_path))
            try:
                smoothness, _ = pearsonr(adj_path, ideal)
                smoothness = float(smoothness)
            except Exception:
                smoothness = np.nan
        else:
            smoothness = np.nan

        trades.append(
            {
                "max_heat_bps": max_heat,
                "time_to_profit_bars": time_to_profit,
                "final_pnl_bps": final_pnl,
                "excursion_ratio": excursion_ratio,
                "path_smoothness": smoothness,
            }
        )

    if not trades:
        return {"PASS": False, "reason": "no trades generated", "n_trades": 0}

    tdf = pd.DataFrame(trades)

    results = {
        "n_trades": len(tdf),
        "mean_heat_bps": float(tdf["max_heat_bps"].mean()),
        "mean_time_to_profit": float(tdf["time_to_profit_bars"].mean()),
        "mean_excursion_ratio": float(tdf["excursion_ratio"].mean()),
        "mean_path_smoothness": float(tdf["path_smoothness"].mean()),
        "mean_pnl_bps": float(tdf["final_pnl_bps"].mean()),
        "hit_rate": float((tdf["final_pnl_bps"] > 0).mean()),
    }

    results["PASS"] = (
        results["mean_excursion_ratio"] > 1.5
        and results["mean_time_to_profit"] < horizon * 0.5
    )

    return results


# ═══════════════════════════════════════════════
# Test 11: Shock Regime Inspection
# ═══════════════════════════════════════════════


def test_shock_behavior(
    df: pd.DataFrame, shock_dates: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Does PS spike before violent reversals? Maps the failure surface."""
    if "timestamp" not in df.columns:
        return {"PASS": True, "reason": "no timestamp for shock detection"}

    # Auto-detect shock days: >3x normal daily range
    daily_range = df.groupby(df["timestamp"].dt.date).apply(
        lambda x: (x["high"].max() - x["low"].min()) / x["close"].iloc[0]
        if len(x) > 0 and x["close"].iloc[0] > 0
        else 0
    )
    normal_range = daily_range.median()

    if shock_dates:
        shock_days = [pd.Timestamp(d).date() for d in shock_dates]
    else:
        shock_days = daily_range[daily_range > 3 * normal_range].index.tolist()

    false_signals = 0
    total_checks = 0

    for day in shock_days:
        day_data = df[df["timestamp"].dt.date == day]
        if len(day_data) < 30:
            continue

        returns = day_data["close"].pct_change()
        if returns.abs().max() == 0:
            continue

        worst_bar = returns.abs().idxmax()
        worst_pos = day_data.index.get_loc(worst_bar)

        if worst_pos < 10:
            continue

        pre_ps = day_data["ps"].iloc[max(0, worst_pos - 10) : worst_pos]
        overall_p70 = df["ps"].quantile(0.7)

        if pre_ps.mean() > overall_p70:
            false_signals += 1
        total_checks += 1

    return {
        "n_shock_days": len(shock_days),
        "shock_days_sample": [str(d) for d in shock_days[:10]],
        "false_signal_rate": float(false_signals / max(total_checks, 1)),
        "total_checks": total_checks,
        "INFO": "High false_signal_rate = PS unreliable during shocks (expected). Use for risk intelligence.",
        "PASS": True,  # informational only
    }


# ═══════════════════════════════════════════════
# Test 12: Cross-Sectional Correlation
# ═══════════════════════════════════════════════


def test_cross_sectional_correlation(
    all_data: Dict[str, pd.DataFrame],
) -> Dict[str, Any]:
    """When many symbols propagate simultaneously, portfolio risk spikes."""
    symbols = [s for s in all_data if s not in ["SPY", "QQQ"]]

    if len(symbols) < 3:
        return {"PASS": True, "reason": "too few symbols for cross-sectional test"}

    # Build PS matrix (aligned by position, not timestamp, for simplicity)
    min_len = min(len(all_data[s]) for s in symbols)
    ps_matrix = pd.DataFrame(
        {s: all_data[s]["ps"].iloc[:min_len].values for s in symbols}
    )

    # Rolling mean pairwise correlation
    window = 60  # 1-hour window
    corr_series = []

    for start in range(0, len(ps_matrix) - window, window // 2):
        chunk = ps_matrix.iloc[start : start + window].dropna(axis=1, how="all")
        if chunk.shape[1] < 3:
            continue
        corr_mat = chunk.corr()
        mask = np.triu(np.ones(corr_mat.shape, dtype=bool), k=1)
        avg_corr = corr_mat.values[mask].mean()
        corr_series.append(avg_corr)

    if not corr_series:
        return {"PASS": True, "reason": "insufficient data for correlation"}

    avg_corr_arr = np.array(corr_series)

    return {
        "mean_ps_correlation": float(avg_corr_arr.mean()),
        "p90_ps_correlation": float(np.percentile(avg_corr_arr, 90)),
        "pct_time_high_corr": float((avg_corr_arr > 0.5).mean()),
        "INFO": "High correlation = PS-driven trades will cluster. Risk engine must cap.",
        "PASS": True,  # informational, not kill criterion
    }


# ═══════════════════════════════════════════════
# Test 13: Temporal Stability
# ═══════════════════════════════════════════════


def test_temporal_stability(
    df: pd.DataFrame, horizon: int = PRIMARY_HORIZON
) -> Dict[str, Any]:
    """Does the signal hold in both halves of the sample?"""
    col = f"fwd_return_{horizon}bar_net_bps"
    midpoint = len(df) // 2

    results: Dict[str, Any] = {}

    for label, half in [("first_half", df.iloc[:midpoint]), ("second_half", df.iloc[midpoint:])]:
        ps = half["ps"].dropna()
        fwd = half[col].dropna() if col in half.columns else pd.Series(dtype=float)
        common = ps.index.intersection(fwd.index)

        if len(common) < MIN_OBSERVATIONS_PER_CELL * 5:
            results[label] = {"SKIP": "insufficient data", "PASS": False}
            continue

        quintiles = _assign_quintiles(ps.loc[common])
        means = []
        for q in range(1, 6):
            qr = fwd.loc[common][quintiles == q]
            means.append(float(qr.mean()) if len(qr) > 0 else np.nan)

        inversions = sum(
            1
            for i in range(4)
            if not np.isnan(means[i + 1])
            and not np.isnan(means[i])
            and means[i + 1] < means[i]
        )

        q5_q1 = means[4] - means[0] if not (np.isnan(means[4]) or np.isnan(means[0])) else 0

        results[label] = {
            "quintile_means": means,
            "inversions": inversions,
            "q5_minus_q1": float(q5_q1),
            "is_monotonic": inversions <= 2,
        }

    # Both halves must show Q5 > Q1 and ≤2 inversions
    fh = results.get("first_half", {})
    sh = results.get("second_half", {})

    results["PASS"] = (
        fh.get("q5_minus_q1", 0) > 0
        and sh.get("q5_minus_q1", 0) > 0
        and fh.get("inversions", 99) <= 2
        and sh.get("inversions", 99) <= 2
    )

    return results
