"""
Volatility Forecasting Utilities (ADS v3.1)
===========================================

Implements a lightweight forward-looking volatility proxy using EWMA.
This is used to build σ_eff = max(σ_realized, σ_forecast) as required by ADS §5 / Appendix A.5.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence, Tuple

import numpy as np

from core_engine.utils.jit_utils import jit_ewma_volatility, jit_correlation


def _to_np(x: Iterable[float]) -> np.ndarray:
    arr = np.asarray(list(x), dtype=float)
    return arr[np.isfinite(arr)]


def realized_volatility(returns: Sequence[float], window: int = 20) -> float:
    """Rolling realized volatility (stdev of returns) over last `window` points."""
    r = _to_np(returns)
    if r.size < max(2, window):
        return float(np.std(r)) if r.size >= 2 else 0.0
    return float(np.std(r[-window:]))


def ewma_volatility(returns: Sequence[float], lambda_: float = 0.94) -> float:
    """
    EWMA volatility forecast for next period.

    λ close to 1.0 gives longer memory. Standard RiskMetrics uses 0.94 (daily).
    """
    r = _to_np(returns)
    if r.size < 2:
        return 0.0

    if jit_ewma_volatility:
        return float(jit_ewma_volatility(r, float(lambda_)))

    lam = float(lambda_)
    lam = max(0.0, min(0.9999, lam))

    # EWMA variance recursion
    var = float(np.var(r[-min(20, r.size):]))  # seed with recent variance
    for x in r:
        var = lam * var + (1.0 - lam) * float(x) ** 2
    return float(np.sqrt(max(var, 0.0)))


def sigma_eff(
    returns: Sequence[float],
    *,
    realized_window: int = 20,
    lambda_: float = 0.94,
) -> Tuple[float, float, float]:
    """
    Compute σ_eff and its components.
    Returns (sigma_eff, sigma_realized, sigma_forecast).
    """
    s_real = realized_volatility(returns, window=realized_window)
    s_fcst = ewma_volatility(returns, lambda_=lambda_)
    return max(s_real, s_fcst), s_real, s_fcst


def correlation_change(
    returns: Sequence[float],
    benchmark_returns: Sequence[float],
    *,
    short_window: int = 20,
    long_window: int = 60,
) -> float:
    """
    Δρ = ρ_short - ρ_long

    Returns 0.0 if insufficient data.
    """
    r = _to_np(returns)
    b = _to_np(benchmark_returns)
    n = min(r.size, b.size)
    if n < max(5, long_window):
        return 0.0

    r = r[-n:]
    b = b[-n:]

    def corr(x: np.ndarray, y: np.ndarray) -> float:
        if x.size < 5:
            return 0.0
        if jit_correlation:
            return float(jit_correlation(x, y))
        if np.std(x) == 0 or np.std(y) == 0:
            return 0.0
        return float(np.corrcoef(x, y)[0, 1])

    ρ_short = corr(r[-short_window:], b[-short_window:])
    ρ_long = corr(r[-long_window:], b[-long_window:])
    return ρ_short - ρ_long


@dataclass(frozen=True)
class VolStopParams:
    k: float = 2.0
    kappa: float = 0.5
    overnight_mult: float = 1.5


def stop_distance_pct(
    sigma_eff_value: float,
    *,
    delta_rho: float = 0.0,
    params: Optional[VolStopParams] = None,
    overnight: bool = False,
) -> float:
    """
    Stop distance as a fraction of entry price (e.g., 0.03 => 3%).

        SL = k * σ_eff * sqrt(1 + κ * max(0, Δρ))
    """
    p = params or VolStopParams()
    dr = max(0.0, float(delta_rho))
    base = float(p.k) * float(sigma_eff_value) * float(np.sqrt(1.0 + float(p.kappa) * dr))
    if overnight:
        base *= float(p.overnight_mult)
    return max(0.0, base)


