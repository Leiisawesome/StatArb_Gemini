"""
Economic viability analysis — Phase 2 economics.

Handles Tier 1 gate: T1.2 (net edge after penalized cost)
Handles Tier 3 gates: T3.1-T3.6

Computes:
- Forward returns per imbalance event
- Penalized cost (tier × elasticity multiplier)
- Net edge distribution (mean, median, CI, hit rate, skew)
- Conditional slippage model
- Cross-event correlation
- Edge distribution shape

Blueprint: v1.6-FINAL Section 2.7
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy import stats as sp_stats

from core_engine.microstructure.constants import (
    DEPTH_COST_MULTIPLIER_TIER_A,
    DEPTH_COST_MULTIPLIER_TIER_B,
    DEPTH_COST_MULTIPLIER_TIER_C,
    ELASTICITY_COST_MULT_HIGH,
    ELASTICITY_COST_MULT_LOW,
    ELASTICITY_COST_MULT_MID,
    ESTIMATION_ERROR_BUFFER_BPS,
    NET_EDGE_CI_LOWER_MIN_BPS,
    NET_EDGE_POINT_MIN_BPS,
)

logger = logging.getLogger(__name__)

TIER_COST_MULT = {"A": DEPTH_COST_MULTIPLIER_TIER_A,
                  "B": DEPTH_COST_MULTIPLIER_TIER_B,
                  "C": DEPTH_COST_MULTIPLIER_TIER_C}

PRIMARY_THRESHOLD = 0.10


@dataclass
class EdgeStats:
    """Distribution statistics for net edge."""
    mean_bps: float = 0.0
    median_bps: float = 0.0
    ci_lower_bps: float = 0.0
    ci_upper_bps: float = 0.0
    p10_bps: float = 0.0
    p25_bps: float = 0.0
    p75_bps: float = 0.0
    p90_bps: float = 0.0
    hit_rate: float = 0.0
    skewness: float = 0.0
    kurtosis: float = 0.0
    n_events: int = 0


@dataclass
class EconomicOutput:
    """Full economic analysis output for one symbol."""
    symbol: str
    tier: str

    gross_edge: EdgeStats = field(default_factory=EdgeStats)
    penalized_cost_mean_bps: float = 0.0
    net_edge: EdgeStats = field(default_factory=EdgeStats)

    # Classification correlation (T1.4)
    classification_corr: float = 0.0

    # Conditional slippage (T3.1)
    high_imb_high_elast_edge_bps: float = 0.0

    # Edge shape (T3.6)
    median_net_edge_positive: bool = False


class EconomicAnalyzer:
    """Computes economic viability diagnostics from volume bucket data."""

    def analyze(
        self,
        symbol: str,
        tier: str,
        flow_imbalance: np.ndarray,
        close_prices: np.ndarray,
        bucket_dates: np.ndarray,
        effective_spread_bps: np.ndarray,
        price_impact_per_volume: np.ndarray,
        same_day_next: np.ndarray,
    ) -> EconomicOutput:
        """Full economic analysis for one symbol."""
        forward_ret = self._forward_returns(close_prices, same_day_next)
        tier_mult = TIER_COST_MULT.get(tier, 1.3)

        event_mask = (
            (np.abs(flow_imbalance) > PRIMARY_THRESHOLD)
            & np.isfinite(forward_ret)
            & same_day_next
        )
        n_events = int(np.sum(event_mask))

        output = EconomicOutput(symbol=symbol, tier=tier)

        if n_events < 50:
            logger.warning("%s: only %d events, insufficient for economics", symbol, n_events)
            return output

        direction = np.sign(flow_imbalance[event_mask])
        gross = direction * forward_ret[event_mask]
        output.gross_edge = self._compute_stats(gross)

        # Penalized cost
        elast_mult = self._elasticity_multipliers(
            price_impact_per_volume[event_mask]
        )
        cost = effective_spread_bps[event_mask] * tier_mult * elast_mult
        output.penalized_cost_mean_bps = float(np.mean(cost))

        net = gross - cost
        output.net_edge = self._compute_stats(net)
        output.median_net_edge_positive = output.net_edge.median_bps > 0

        # Classification correlation (T1.4): flow_imbalance vs forward return
        valid = np.isfinite(flow_imbalance) & np.isfinite(forward_ret) & same_day_next
        if np.sum(valid) > 50:
            corr, _ = sp_stats.pearsonr(flow_imbalance[valid], forward_ret[valid])
            output.classification_corr = float(corr)

        # Conditional slippage: high-imbalance × high-elasticity cell
        output.high_imb_high_elast_edge_bps = self._conditional_slippage(
            flow_imbalance[event_mask], price_impact_per_volume[event_mask],
            gross, cost
        )

        logger.info(
            "%s: gross=%.2f bps, cost=%.2f bps, net=%.2f bps (median=%.2f), "
            "hit=%.1f%%, corr=%.4f, n=%d",
            symbol, output.gross_edge.mean_bps, output.penalized_cost_mean_bps,
            output.net_edge.mean_bps, output.net_edge.median_bps,
            output.net_edge.hit_rate * 100, output.classification_corr, n_events,
        )

        return output

    @staticmethod
    def _forward_returns(close_prices: np.ndarray, same_day_next: np.ndarray) -> np.ndarray:
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

    @staticmethod
    def _elasticity_multipliers(pip_vol: np.ndarray) -> np.ndarray:
        """Compute elasticity-based cost multiplier per event."""
        valid = np.isfinite(pip_vol) & (pip_vol != 0)
        if np.sum(valid) < 10:
            return np.ones(len(pip_vol))

        abs_pip = np.abs(pip_vol)
        try:
            decile_edges = np.percentile(abs_pip[valid], np.arange(10, 100, 10))
            deciles = np.searchsorted(decile_edges, abs_pip) + 1
        except Exception:
            return np.ones(len(pip_vol))

        mult = np.where(
            deciles <= 3, ELASTICITY_COST_MULT_LOW,
            np.where(deciles <= 7, ELASTICITY_COST_MULT_MID, ELASTICITY_COST_MULT_HIGH)
        )
        return mult.astype(np.float64)

    @staticmethod
    def _compute_stats(values: np.ndarray) -> EdgeStats:
        valid = values[np.isfinite(values)]
        if len(valid) < 10:
            return EdgeStats(n_events=len(valid))

        mean_val = float(np.mean(valid))
        se = float(np.std(valid, ddof=1) / np.sqrt(len(valid)))
        return EdgeStats(
            mean_bps=mean_val,
            median_bps=float(np.median(valid)),
            ci_lower_bps=mean_val - 1.96 * se,
            ci_upper_bps=mean_val + 1.96 * se,
            p10_bps=float(np.percentile(valid, 10)),
            p25_bps=float(np.percentile(valid, 25)),
            p75_bps=float(np.percentile(valid, 75)),
            p90_bps=float(np.percentile(valid, 90)),
            hit_rate=float(np.mean(valid > 0)),
            skewness=float(sp_stats.skew(valid)),
            kurtosis=float(sp_stats.kurtosis(valid)),
            n_events=len(valid),
        )

    @staticmethod
    def _conditional_slippage(
        imb: np.ndarray,
        pip_vol: np.ndarray,
        gross: np.ndarray,
        cost: np.ndarray,
    ) -> float:
        """Net edge in the high-imbalance × high-elasticity cell."""
        abs_imb = np.abs(imb)
        abs_pip = np.abs(pip_vol)

        valid = np.isfinite(abs_imb) & np.isfinite(abs_pip)
        if np.sum(valid) < 30:
            return 0.0

        imb_t = np.percentile(abs_imb[valid], 66.7)
        pip_t = np.percentile(abs_pip[valid], 66.7)

        cell = (abs_imb > imb_t) & (abs_pip > pip_t)
        if np.sum(cell) < 5:
            return 0.0

        net = gross[cell] - cost[cell]
        return float(np.mean(net))
