"""
Skeleton utilities for composite feature consumption (Rule 7).

These helpers centralize:
- normalization of pipeline-provided composite percentiles
- deterministic fallback computation of (composite_z, composite_pct) from close history

Note: This is "pipeline compensation" glue and is intentionally strategy-agnostic.
Strategies may call this to implement explicit degrade behavior when enrichment is missing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
import pandas as pd


def normalize_composite_pct(x: float) -> float:
    """
    Normalize composite_pct into [0, 100].

    Some pipelines emit composite_pct in [-1, 1] (signed scale), while others may emit
    [0, 1] or [0, 100]. We normalize conservatively:
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


@dataclass(frozen=True)
class CompositeFallbackParams:
    short_period: int
    medium_period: int
    long_period: int
    lookback_period: int


def fallback_compute_composite_signals(
    *,
    data: pd.DataFrame,
    idx: int,
    params: CompositeFallbackParams,
) -> Tuple[Optional[float], Optional[float]]:
    """
    Compute (composite_z, composite_pct) from price history when enrichment is missing.

    Deterministic, lightweight implementation (smoke-test focused).
    """
    try:
        if "close" not in data.columns:
            return None, None

        n = len(data)
        if idx < 0:
            idx = n + idx
        if idx <= 0 or idx >= n:
            return None, None

        sp = int(params.short_period)
        mp = int(params.medium_period)
        lp = int(params.long_period)
        lookback = int(params.lookback_period)

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

