"""
Persistence analysis — Phase 2b.

Handles Tier 1 gates: T1.1 (continuation), T1.3 (temporal stability)
Handles Tier 2 gates: T2.1 (monotonicity), T2.2 (regime conditioning), T2.3 (threshold sweep)

Computes:
- Continuation probabilities P(run ≥ k+1 | run ≥ k) with Wilson CI
- Dual half-life (bucket-clock + wall-clock)
- Event categorization (micro-burst / intermediate / mandate)
- Magnitude monotonicity (decile-based)
- Regime-conditioned persistence (vol tertiles)
- Temporal block stability
- Threshold sensitivity sweep

Blueprint: v1.6-FINAL Section 2.3
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy import stats as sp_stats

from core_engine.microstructure.constants import (
    CONSTANTS_VERSION,
    CONTINUATION_K3_CI_LOWER_MIN,
    CONTINUATION_K3_CI_WIDTH_MAX,
    CONTINUATION_K3_POINT_MIN,
    IMBALANCE_THRESHOLDS,
    MAGNITUDE_ADJACENT_MONOTONIC_MIN,
    MAGNITUDE_D10_D1_MIN_SPREAD_PP,
    MAGNITUDE_D10_D1_SCALE,
    MAGNITUDE_MONOTONICITY_MIN_RHO,
    MICRO_BURST_MAX_FRACTION,
    TEMPORAL_BLOCKS,
    TEMPORAL_STABILITY_MIN_POSITIVE,
    THRESHOLD_STABILITY_MIN_PASSING,
    VOL_REGIME_TERTILES,
)

logger = logging.getLogger(__name__)

KS = [1, 2, 3, 5, 10]
PRIMARY_THRESHOLD = 0.10
Z_95 = 1.96


@dataclass
class ContinuationResult:
    """Continuation probability at a specific k."""
    k: int
    point: float
    ci_lower: float
    ci_upper: float
    n_runs_at_k: int
    n_continued: int


@dataclass
class PersistenceOutput:
    """Full persistence analysis output for one symbol."""
    symbol: str
    tier: str

    # Continuation
    continuation: Dict[int, ContinuationResult]
    continuation_k3_point: float
    continuation_k3_ci_lower: float
    continuation_k3_ci_upper: float

    # Half-life
    half_life_buckets: float
    half_life_minutes: float

    # Event categories
    total_runs: int
    micro_burst_pct: float
    intermediate_pct: float
    mandate_pct: float

    # Magnitude monotonicity
    magnitude_rho: float
    magnitude_d10_d1_pp: float
    magnitude_adjacent_monotonic: int

    # Regime conditioning
    regime_edges: Dict[str, float]  # {low/mid/high: mean_forward_return}
    regime_positive_count: int

    # Temporal blocks
    block_edges: List[float]
    temporal_positive_count: int

    # Threshold sweep
    threshold_results: Dict[float, float]  # {threshold: continuation_k3}
    threshold_passing_count: int


class PersistenceAnalyzer:
    """Computes flow persistence diagnostics from volume bucket data."""

    def analyze(
        self,
        symbol: str,
        tier: str,
        flow_imbalance: np.ndarray,
        close_prices: np.ndarray,
        bucket_dates: np.ndarray,
        effective_spread_bps: np.ndarray,
        price_impact_per_volume: np.ndarray,
        fill_duration_ms: np.ndarray,
        classification_confidence: np.ndarray,
    ) -> PersistenceOutput:
        """Full persistence analysis for one symbol."""
        n = len(flow_imbalance)
        same_day_next = np.zeros(n, dtype=bool)
        if n > 1:
            same_day_next[:-1] = bucket_dates[:-1] == bucket_dates[1:]

        forward_ret = self._forward_returns(close_prices, same_day_next)

        # Continuation at primary threshold
        continuation = self._continuation_all_k(
            flow_imbalance, same_day_next, PRIMARY_THRESHOLD, KS
        )
        k3 = continuation.get(3)
        k3_point = k3.point if k3 else 0.0
        k3_ci_lower = k3.ci_lower if k3 else 0.0
        k3_ci_upper = k3.ci_upper if k3 else 0.0

        # Run lengths for event categorization
        runs = self._compute_runs(flow_imbalance, same_day_next, PRIMARY_THRESHOLD)
        micro, inter, mandate = self._event_categories(runs)

        # Half-life
        hl_buckets = self._half_life_acf(flow_imbalance, same_day_next)
        median_fill_ms = float(np.median(fill_duration_ms[fill_duration_ms > 0])) if np.any(fill_duration_ms > 0) else 60000.0
        hl_minutes = hl_buckets * median_fill_ms / 60000.0

        # Magnitude monotonicity
        rho, d10d1, adj_mono = self._magnitude_monotonicity(
            flow_imbalance, forward_ret, same_day_next, PRIMARY_THRESHOLD
        )

        # Regime conditioning (use fill_duration_ms std as vol proxy)
        regime_edges, regime_pos = self._regime_conditioning(
            flow_imbalance, forward_ret, same_day_next,
            effective_spread_bps, bucket_dates, PRIMARY_THRESHOLD
        )

        # Temporal blocks
        block_edges, temporal_pos = self._temporal_blocks(
            flow_imbalance, forward_ret, same_day_next,
            effective_spread_bps, bucket_dates, PRIMARY_THRESHOLD
        )

        # Threshold sweep
        threshold_results = {}
        passing = 0
        for tau in IMBALANCE_THRESHOLDS:
            cont = self._continuation_all_k(flow_imbalance, same_day_next, tau, [3])
            p = cont[3].point if 3 in cont else 0.0
            threshold_results[tau] = p
            if p >= CONTINUATION_K3_POINT_MIN:
                passing += 1

        logger.info(
            "%s: k3=%.3f [%.3f,%.3f], hl=%.1f buckets, "
            "micro=%.1f%%, rho=%.3f, temporal=%d/%d, sweep=%d/%d",
            symbol, k3_point, k3_ci_lower, k3_ci_upper,
            hl_buckets, micro * 100, rho,
            temporal_pos, TEMPORAL_BLOCKS, passing, len(IMBALANCE_THRESHOLDS),
        )

        return PersistenceOutput(
            symbol=symbol, tier=tier,
            continuation=continuation,
            continuation_k3_point=k3_point,
            continuation_k3_ci_lower=k3_ci_lower,
            continuation_k3_ci_upper=k3_ci_upper,
            half_life_buckets=hl_buckets, half_life_minutes=hl_minutes,
            total_runs=len(runs),
            micro_burst_pct=micro, intermediate_pct=inter, mandate_pct=mandate,
            magnitude_rho=rho, magnitude_d10_d1_pp=d10d1,
            magnitude_adjacent_monotonic=adj_mono,
            regime_edges=regime_edges, regime_positive_count=regime_pos,
            block_edges=block_edges, temporal_positive_count=temporal_pos,
            threshold_results=threshold_results,
            threshold_passing_count=passing,
        )

    # ── Continuation ──────────────────────────────────────────────────

    def _continuation_all_k(
        self,
        flow_imb: np.ndarray,
        same_day_next: np.ndarray,
        threshold: float,
        ks: List[int],
    ) -> Dict[int, ContinuationResult]:
        runs = self._compute_runs(flow_imb, same_day_next, threshold)
        if not runs:
            return {k: ContinuationResult(k, 0, 0, 0, 0, 0) for k in ks}

        run_arr = np.array(runs)
        result = {}
        for k in ks:
            n_k = int(np.sum(run_arr >= k))
            n_k1 = int(np.sum(run_arr >= k + 1))
            if n_k == 0:
                result[k] = ContinuationResult(k, 0, 0, 0, 0, 0)
            else:
                point = n_k1 / n_k
                ci_lo, ci_hi = self._wilson_ci(n_k1, n_k)
                result[k] = ContinuationResult(k, point, ci_lo, ci_hi, n_k, n_k1)
        return result

    @staticmethod
    def _compute_runs(
        flow_imb: np.ndarray, same_day_next: np.ndarray, threshold: float
    ) -> List[int]:
        """Compute lengths of consecutive same-sign imbalance runs within days."""
        n = len(flow_imb)
        if n == 0:
            return []

        signs = np.zeros(n, dtype=np.int8)
        signs[flow_imb > threshold] = 1
        signs[flow_imb < -threshold] = -1

        runs = []
        current_sign = np.int8(0)
        current_len = 0

        for i in range(n):
            if signs[i] != 0 and signs[i] == current_sign:
                current_len += 1
            else:
                if current_len > 0:
                    runs.append(current_len)
                if signs[i] != 0:
                    current_sign = signs[i]
                    current_len = 1
                else:
                    current_sign = np.int8(0)
                    current_len = 0

            if i < n - 1 and not same_day_next[i]:
                if current_len > 0:
                    runs.append(current_len)
                current_sign = np.int8(0)
                current_len = 0

        if current_len > 0:
            runs.append(current_len)

        return runs

    @staticmethod
    def _wilson_ci(successes: int, trials: int, z: float = Z_95) -> Tuple[float, float]:
        if trials == 0:
            return (0.0, 0.0)
        p_hat = successes / trials
        denom = 1 + z * z / trials
        center = (p_hat + z * z / (2 * trials)) / denom
        half_width = z / denom * math.sqrt(p_hat * (1 - p_hat) / trials + z * z / (4 * trials * trials))
        return (max(0.0, center - half_width), min(1.0, center + half_width))

    # ── Forward returns ───────────────────────────────────────────────

    @staticmethod
    def _forward_returns(close_prices: np.ndarray, same_day_next: np.ndarray) -> np.ndarray:
        """Compute per-bucket forward return in bps (next bucket close - this close)."""
        n = len(close_prices)
        fwd = np.full(n, np.nan)
        if n < 2:
            return fwd
        valid = same_day_next[:-1] & (close_prices[:-1] > 0)
        fwd[:-1] = np.where(
            valid,
            (close_prices[1:] - close_prices[:-1]) / close_prices[:-1] * 10000,
            np.nan,
        )
        return fwd

    # ── Half-life ─────────────────────────────────────────────────────

    @staticmethod
    def _half_life_acf(flow_imb: np.ndarray, same_day_next: np.ndarray, max_lag: int = 50) -> float:
        """Estimate half-life via autocorrelation function exponential fit."""
        valid = np.isfinite(flow_imb) & (flow_imb != 0)
        x = flow_imb[valid]
        if len(x) < 100:
            return 0.0

        x_centered = x - np.mean(x)
        var = np.var(x_centered)
        if var < 1e-12:
            return 0.0

        acf_vals = []
        for lag in range(1, min(max_lag + 1, len(x))):
            c = np.mean(x_centered[:-lag] * x_centered[lag:]) / var
            acf_vals.append(c)

        acf_arr = np.array(acf_vals)
        positive = acf_arr > 0
        if not np.any(positive):
            return 0.0

        # Find first zero-crossing
        first_neg = np.argmax(~positive)
        if first_neg == 0 and positive[0]:
            first_neg = len(acf_arr)
        usable = min(first_neg, 20)
        if usable < 2:
            return 1.0

        lags = np.arange(1, usable + 1, dtype=np.float64)
        log_acf = np.log(np.clip(acf_arr[:usable], 1e-10, None))

        try:
            slope, _, _, _, _ = sp_stats.linregress(lags, log_acf)
            if slope >= 0:
                return float(usable)
            return float(-np.log(2) / slope)
        except Exception:
            return float(usable)

    # ── Event categories ──────────────────────────────────────────────

    @staticmethod
    def _event_categories(runs: List[int]) -> Tuple[float, float, float]:
        if not runs:
            return (0.0, 0.0, 0.0)
        arr = np.array(runs)
        total = len(arr)
        micro = float(np.sum(arr < 3)) / total
        inter = float(np.sum((arr >= 3) & (arr <= 10))) / total
        mandate = float(np.sum(arr > 10)) / total
        return (micro, inter, mandate)

    # ── Magnitude monotonicity ────────────────────────────────────────

    def _magnitude_monotonicity(
        self,
        flow_imb: np.ndarray,
        forward_ret: np.ndarray,
        same_day_next: np.ndarray,
        threshold: float,
    ) -> Tuple[float, float, int]:
        """
        P(continuation | |flow_imbalance| decile).

        Returns (spearman_rho, d10_d1_spread_pp, adjacent_monotonic_count).
        """
        event_mask = (np.abs(flow_imb) > threshold) & np.isfinite(forward_ret) & same_day_next
        if np.sum(event_mask) < 100:
            return (0.0, 0.0, 0)

        abs_imb = np.abs(flow_imb[event_mask])
        fwd = forward_ret[event_mask]
        direction = np.sign(flow_imb[event_mask])
        directional_ret = direction * fwd

        # Compute deciles of |flow_imbalance|
        try:
            decile_edges = np.percentile(abs_imb, np.arange(10, 100, 10))
            deciles = np.searchsorted(decile_edges, abs_imb) + 1
        except Exception:
            return (0.0, 0.0, 0)

        # P(positive directional return) per decile
        continuation_by_decile = []
        for d in range(1, 11):
            mask = deciles == d
            if np.sum(mask) < 10:
                continuation_by_decile.append(np.nan)
                continue
            pos_frac = float(np.mean(directional_ret[mask] > 0))
            continuation_by_decile.append(pos_frac)

        cont_arr = np.array(continuation_by_decile)
        valid_mask = np.isfinite(cont_arr)
        if np.sum(valid_mask) < 5:
            return (0.0, 0.0, 0)

        valid_vals = cont_arr[valid_mask]
        valid_ranks = np.arange(1, 11)[valid_mask]

        rho, _ = sp_stats.spearmanr(valid_ranks, valid_vals)

        # D10 - D1 spread
        d1 = cont_arr[0] if np.isfinite(cont_arr[0]) else 0.5
        d10 = cont_arr[9] if np.isfinite(cont_arr[9]) else 0.5
        d10_d1_pp = (d10 - d1) * 100

        # Adjacent monotonic pairs
        adj_mono = 0
        valid_indices = np.where(valid_mask)[0]
        for i in range(len(valid_indices) - 1):
            if cont_arr[valid_indices[i + 1]] > cont_arr[valid_indices[i]]:
                adj_mono += 1

        return (float(rho), float(d10_d1_pp), adj_mono)

    # ── Regime conditioning ───────────────────────────────────────────

    def _regime_conditioning(
        self,
        flow_imb: np.ndarray,
        forward_ret: np.ndarray,
        same_day_next: np.ndarray,
        effective_spread: np.ndarray,
        bucket_dates: np.ndarray,
        threshold: float,
    ) -> Tuple[Dict[str, float], int]:
        """Split by volatility regime (realized spread volatility), compute edge per regime."""
        event_mask = (np.abs(flow_imb) > threshold) & np.isfinite(forward_ret) & same_day_next

        spread_vol = self._rolling_spread_vol(effective_spread, bucket_dates, window=20)

        valid = event_mask & np.isfinite(spread_vol) & (spread_vol > 0)
        if np.sum(valid) < 50:
            return ({"low": 0.0, "mid": 0.0, "high": 0.0}, 0)

        vol_vals = spread_vol[valid]
        direction = np.sign(flow_imb[valid])
        fwd = forward_ret[valid] * direction

        t1, t2 = np.percentile(vol_vals, [33.3, 66.7])

        regime_labels = ["low", "mid", "high"]
        regime_masks = [vol_vals <= t1, (vol_vals > t1) & (vol_vals <= t2), vol_vals > t2]

        edges = {}
        pos_count = 0
        for label, mask in zip(regime_labels, regime_masks):
            if np.sum(mask) > 10:
                mean_edge = float(np.mean(fwd[mask]))
                edges[label] = mean_edge
                if mean_edge > 0:
                    pos_count += 1
            else:
                edges[label] = 0.0

        return (edges, pos_count)

    @staticmethod
    def _rolling_spread_vol(spread: np.ndarray, dates: np.ndarray, window: int = 20) -> np.ndarray:
        """Rolling standard deviation of effective spread as vol proxy."""
        n = len(spread)
        result = np.full(n, np.nan)
        for i in range(window, n):
            chunk = spread[i - window : i]
            valid = chunk[np.isfinite(chunk)]
            if len(valid) > 5:
                result[i] = float(np.std(valid))
        return result

    # ── Temporal blocks ───────────────────────────────────────────────

    def _temporal_blocks(
        self,
        flow_imb: np.ndarray,
        forward_ret: np.ndarray,
        same_day_next: np.ndarray,
        effective_spread: np.ndarray,
        bucket_dates: np.ndarray,
        threshold: float,
        n_blocks: int = TEMPORAL_BLOCKS,
    ) -> Tuple[List[float], int]:
        """Split data into temporal blocks, compute net edge per block."""
        unique_dates = np.unique(bucket_dates)
        n_dates = len(unique_dates)
        if n_dates < n_blocks:
            return ([0.0] * n_blocks, 0)

        block_size = n_dates // n_blocks
        block_edges = []
        pos_count = 0

        for b in range(n_blocks):
            start_idx = b * block_size
            end_idx = (b + 1) * block_size if b < n_blocks - 1 else n_dates
            block_dates = set(unique_dates[start_idx:end_idx].tolist())

            mask = np.array([d in block_dates for d in bucket_dates])
            block_mask = mask & (np.abs(flow_imb) > threshold) & np.isfinite(forward_ret) & same_day_next

            if np.sum(block_mask) < 20:
                block_edges.append(0.0)
                continue

            direction = np.sign(flow_imb[block_mask])
            fwd = forward_ret[block_mask] * direction
            cost = effective_spread[block_mask]
            net = fwd - cost
            mean_net = float(np.mean(net))
            block_edges.append(mean_net)
            if mean_net > 0:
                pos_count += 1

        return (block_edges, pos_count)
