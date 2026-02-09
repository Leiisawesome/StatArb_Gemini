"""
Transition Supervisor Metrics (Phase 1)
=======================================

Computes operational diagnostics for the Transition Supervisor gating layer.
Designed to be called from any analytics pipeline (backtest, live, or manual)
by passing a list of trade records whose ``additional_data`` includes the
transition supervisor fields emitted by ``EnhancedMomentumStrategy``.

Tracked metrics (per the reconciled architecture spec):
  - average_time_in_trade           : mean holding duration (minutes)
  - time_in_trade_by_transition_q   : holding time segmented by transition_score quartile
  - transition_capture_ratio        : fraction of the move captured relative to full range
  - premature_transition_rate       : fraction of trades stopped out in first 25% of expected hold
  - coherence_at_entry_dist         : distribution stats of entry coherence
  - coherence_at_exit_dist          : distribution stats of exit-time coherence
  - coherence_decay_rate            : mean / median / p75 of coherence change during trade
  - vov_block_rate                  : fraction of bars blocked by vol-of-vol filter
  - transition_score_histogram      : quartile distribution of transition_score at entry
  - exit_reason_distribution        : counts by exit reason (VOL_STOP, DIRECTION_REVERSAL, TRANSITION_EXHAUSTION, TRANSITION_TAKE_PROFIT, TIME_STOP, …)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np


@dataclass
class TransitionMetricsReport:
    """Container for transition supervisor diagnostics."""

    total_trades: int = 0

    # Time-in-trade
    avg_time_in_trade_minutes: float = 0.0
    median_time_in_trade_minutes: float = 0.0
    time_in_trade_by_transition_quartile: Dict[str, float] = field(default_factory=dict)

    # Transition capture
    avg_transition_capture_ratio: float = 0.0
    median_transition_capture_ratio: float = 0.0

    # Premature transition (stopped out in first quartile of expected holding)
    premature_transition_rate: float = 0.0
    premature_transition_count: int = 0

    # Coherence distributions
    coherence_at_entry: Dict[str, float] = field(default_factory=dict)  # mean, median, std, p25, p75
    coherence_at_exit: Dict[str, float] = field(default_factory=dict)
    coherence_decay: Dict[str, float] = field(default_factory=dict)

    # Vol-of-vol
    avg_entry_vov: float = 0.0

    # Transition score at entry
    transition_score_quartiles: Dict[str, float] = field(default_factory=dict)

    # Exit reason breakdown
    exit_reason_distribution: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to flat dictionary for logging / JSON export."""
        return {
            "total_trades": self.total_trades,
            "avg_time_in_trade_minutes": round(self.avg_time_in_trade_minutes, 2),
            "median_time_in_trade_minutes": round(self.median_time_in_trade_minutes, 2),
            "time_in_trade_by_transition_quartile": self.time_in_trade_by_transition_quartile,
            "avg_transition_capture_ratio": round(self.avg_transition_capture_ratio, 4),
            "median_transition_capture_ratio": round(self.median_transition_capture_ratio, 4),
            "premature_transition_rate": round(self.premature_transition_rate, 4),
            "premature_transition_count": self.premature_transition_count,
            "coherence_at_entry": self.coherence_at_entry,
            "coherence_at_exit": self.coherence_at_exit,
            "coherence_decay": self.coherence_decay,
            "avg_entry_vov": round(self.avg_entry_vov, 4),
            "transition_score_quartiles": self.transition_score_quartiles,
            "exit_reason_distribution": self.exit_reason_distribution,
        }


def compute_transition_metrics(
    trades: List[Dict[str, Any]],
    expected_hold_minutes: float = 90.0,
) -> TransitionMetricsReport:
    """
    Compute transition supervisor diagnostics from a list of trade records.

    Each trade dict is expected to contain (all optional — degrades gracefully):
      - additional_data.transition_score       (float, 0-1)
      - additional_data.entry_coherence        (float, 0-1)
      - additional_data.entry_vol_of_vol       (float, 0-1)
      - additional_data.entry_composite_accel  (float)
      - additional_data.entry_vol_expansion    (float)
      - held_minutes or holding_duration       (float)
      - pnl_pct                                (float)
      - exit_reason or ads_exit                (str)
      - high_pct / low_pct (for capture ratio) (float)
      - exit_coherence                         (float, if available)

    Parameters
    ----------
    trades : list of dicts
        Trade records from backtest or live system.
    expected_hold_minutes : float
        Expected holding period for premature exit detection.

    Returns
    -------
    TransitionMetricsReport
    """
    report = TransitionMetricsReport()

    if not trades:
        return report

    report.total_trades = len(trades)

    # Extract arrays from trade records (tolerant of missing keys)
    def _get(trade: Dict, *keys, default=None):
        """Drill into trade dict, trying additional_data sub-dict as fallback."""
        for k in keys:
            v = trade.get(k)
            if v is not None:
                return v
            ad = trade.get("additional_data") or {}
            v = ad.get(k)
            if v is not None:
                return v
        return default

    # --- Holding time ---
    hold_times = []
    for t in trades:
        ht = _get(t, "held_minutes", "holding_duration", "holding_minutes")
        if ht is not None:
            hold_times.append(float(ht))

    if hold_times:
        report.avg_time_in_trade_minutes = float(np.mean(hold_times))
        report.median_time_in_trade_minutes = float(np.median(hold_times))

    # --- Transition score at entry ---
    t_scores = []
    for t in trades:
        ts = _get(t, "transition_score")
        if ts is not None:
            t_scores.append(float(ts))

    if t_scores:
        arr = np.array(t_scores)
        report.transition_score_quartiles = {
            "mean": round(float(np.mean(arr)), 4),
            "p25": round(float(np.percentile(arr, 25)), 4),
            "median": round(float(np.median(arr)), 4),
            "p75": round(float(np.percentile(arr, 75)), 4),
        }

    # --- Time in trade by transition score quartile ---
    if t_scores and hold_times and len(t_scores) == len(hold_times):
        ts_arr = np.array(t_scores)
        ht_arr = np.array(hold_times)
        for label, lo, hi in [("Q1", 0, 25), ("Q2", 25, 50), ("Q3", 50, 75), ("Q4", 75, 100)]:
            p_lo = np.percentile(ts_arr, lo) if lo > 0 else -np.inf
            p_hi = np.percentile(ts_arr, hi) if hi < 100 else np.inf
            mask = (ts_arr > p_lo) & (ts_arr <= p_hi)
            if mask.any():
                report.time_in_trade_by_transition_quartile[label] = round(float(np.mean(ht_arr[mask])), 2)

    # --- Entry coherence distribution ---
    entry_coh = []
    for t in trades:
        c = _get(t, "entry_coherence")
        if c is not None:
            entry_coh.append(float(c))

    if entry_coh:
        arr = np.array(entry_coh)
        report.coherence_at_entry = {
            "mean": round(float(np.mean(arr)), 4),
            "median": round(float(np.median(arr)), 4),
            "std": round(float(np.std(arr)), 4),
            "p25": round(float(np.percentile(arr, 25)), 4),
            "p75": round(float(np.percentile(arr, 75)), 4),
        }

    # --- Exit coherence distribution ---
    exit_coh = []
    for t in trades:
        c = _get(t, "exit_coherence", "current_coherence")
        if c is not None:
            exit_coh.append(float(c))

    if exit_coh:
        arr = np.array(exit_coh)
        report.coherence_at_exit = {
            "mean": round(float(np.mean(arr)), 4),
            "median": round(float(np.median(arr)), 4),
            "std": round(float(np.std(arr)), 4),
            "p25": round(float(np.percentile(arr, 25)), 4),
            "p75": round(float(np.percentile(arr, 75)), 4),
        }

    # --- Coherence decay ---
    if entry_coh and exit_coh and len(entry_coh) == len(exit_coh):
        decay = np.array(entry_coh) - np.array(exit_coh)
        report.coherence_decay = {
            "mean": round(float(np.mean(decay)), 4),
            "median": round(float(np.median(decay)), 4),
            "p75": round(float(np.percentile(decay, 75)), 4),
        }

    # --- Vol-of-vol at entry ---
    vov_entries = []
    for t in trades:
        v = _get(t, "entry_vol_of_vol")
        if v is not None:
            vov_entries.append(float(v))

    if vov_entries:
        report.avg_entry_vov = float(np.mean(vov_entries))

    # --- Transition capture ratio ---
    # Measures what fraction of the available move was captured.
    # Requires high/low extremes during the trade to compute full range.
    captures = []
    for t in trades:
        pnl = _get(t, "pnl_pct")
        high_pct = _get(t, "high_pct", "max_favorable_excursion")
        low_pct = _get(t, "low_pct", "max_adverse_excursion")
        if pnl is not None and high_pct is not None and low_pct is not None:
            full_range = float(high_pct) - float(low_pct)
            if full_range > 0.01:  # avoid div-by-zero on flat trades
                captures.append(float(pnl) / full_range)

    if captures:
        arr = np.array(captures)
        report.avg_transition_capture_ratio = float(np.mean(arr))
        report.median_transition_capture_ratio = float(np.median(arr))

    # --- Premature transition rate ---
    # A trade is "premature" if it exits in the first 25% of expected hold time.
    premature_threshold = expected_hold_minutes * 0.25
    premature_count = 0
    if hold_times:
        for ht in hold_times:
            if ht < premature_threshold:
                premature_count += 1
        report.premature_transition_count = premature_count
        report.premature_transition_rate = premature_count / len(hold_times)

    # --- Exit reason distribution ---
    reason_counts: Dict[str, int] = {}
    for t in trades:
        reason = _get(t, "exit_reason", "ads_exit", default="UNKNOWN")
        reason = str(reason)
        reason_counts[reason] = reason_counts.get(reason, 0) + 1
    report.exit_reason_distribution = reason_counts

    return report
