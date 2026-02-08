"""
Fractional Kelly Position Sizer (ADS v3.1 §7)
=============================================

CentralRiskManager uses this module to compute a *risk-aware* sizing suggestion
from realized trade outcomes, liquidity, drawdown state, and regime scaling.

This is designed to be robust under small sample sizes via Bayesian shrinkage
and conservative caps.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np


def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(x)))


@dataclass(frozen=True)
class KellyParams:
    # Fractional Kelly multiplier
    kelly_frac: float = 0.33
    # Raw Kelly bounds (ADS rule: no full Kelly)
    kelly_min: float = 0.02
    kelly_max: float = 0.20

    # Bayesian prior for win probability (Beta(a,b))
    prior_a: float = 5.0
    prior_b: float = 5.0

    # Minimum trades before trusting estimates
    min_trades: int = 30

    # Uncertainty penalty floor
    uncertainty_floor: float = 0.3

    # Drawdown gamma
    dd_gamma: float = 2.0

    # Conservatism penalty when below min_trades
    pre_min_trades_penalty: float = 0.5


def estimate_win_prob(pnls: Sequence[float], *, prior_a: float, prior_b: float) -> Tuple[float, float]:
    """
    Estimate win probability and an uncertainty proxy.

    Returns (p_hat, p_std_proxy) where p_std_proxy is conservative.
    """
    pnls = [float(x) for x in pnls if np.isfinite(x)]
    n = len(pnls)
    wins = sum(1 for x in pnls if x > 0)
    a = float(prior_a) + wins
    b = float(prior_b) + (n - wins)
    p = a / (a + b) if (a + b) > 0 else 0.5
    # Beta variance: ab/((a+b)^2*(a+b+1))
    var = (a * b) / (((a + b) ** 2) * (a + b + 1.0)) if (a + b) > 0 else 0.25
    return _clip(p, 0.01, 0.99), float(np.sqrt(max(var, 0.0)))


def estimate_win_loss_ratio(pnls: Sequence[float]) -> Tuple[float, float]:
    """
    Estimate win/loss ratio b and a rough uncertainty proxy.

    b = mean(win) / abs(mean(loss))
    """
    pnls = np.asarray([float(x) for x in pnls if np.isfinite(x)], dtype=float)
    wins = pnls[pnls > 0]
    losses = pnls[pnls < 0]
    if wins.size < 3 or losses.size < 3:
        return 1.0, 1.0

    mean_win = float(np.mean(wins))
    mean_loss = float(abs(np.mean(losses)))
    b = mean_win / mean_loss if mean_loss > 1e-12 else 1.0

    # Uncertainty proxy: coefficient of variation of wins/losses combined
    win_cv = float(np.std(wins) / max(abs(mean_win), 1e-12))
    loss_cv = float(np.std(losses) / max(mean_loss, 1e-12))
    return _clip(b, 0.5, 5.0), _clip((win_cv + loss_cv) / 2.0, 0.1, 2.0)


def raw_kelly(p: float, b: float, *, kelly_min: float, kelly_max: float) -> float:
    """Kelly fraction: clip((p(1+b)-1)/b, kelly_min, kelly_max)."""
    p = _clip(p, 0.01, 0.99)
    b = max(1e-6, float(b))
    k = (p * (1.0 + b) - 1.0) / b
    return _clip(k, kelly_min, kelly_max)


def uncertainty_adjustment(
    *,
    p: float,
    p_std: float,
    b: float,
    b_std_proxy: float,
    floor: float,
) -> float:
    """
    ADS-style uncertainty penalty.

    Conservative heuristic: penalize when uncertainty is large relative to edge.
    """
    edge = p * b
    edge_std = float(np.sqrt((p_std * b) ** 2 + (p * b_std_proxy) ** 2))
    if edge <= 1e-6:
        return 0.0
    adj = 1.0 - (edge_std / max(edge, 1e-6))
    return _clip(adj, float(floor), 1.0)


def drawdown_factor(current_dd: float, max_dd: float, *, gamma: float) -> float:
    """DF = exp(-gamma * DD / DD_max)."""
    dd = max(0.0, float(current_dd))
    m = max(1e-6, float(max_dd))
    return float(np.exp(-float(gamma) * dd / m))


@dataclass(frozen=True)
class KellySizingResult:
    target_fraction_of_capital: float
    diagnostics: Dict[str, float]


def compute_fractional_kelly_fraction_of_capital(
    *,
    signal_strength: float,
    pnls: Sequence[float],
    liquidity_factor: float,
    current_dd: float,
    max_dd: float,
    regime_factor: float,
    params: KellyParams = KellyParams(),
) -> KellySizingResult:
    """
    Compute fraction of capital to allocate (0..1).

    This returns a *fraction of capital*, not shares.
    """
    s = _clip(signal_strength, 0.0, 1.0)
    lf = _clip(liquidity_factor, 0.0, 1.0)
    rf = _clip(regime_factor, 0.0, 2.0)

    n = len([x for x in pnls if np.isfinite(x)])
    if n < params.min_trades:
        # Not enough data: be conservative
        p_hat, p_std = estimate_win_prob(pnls, prior_a=params.prior_a, prior_b=params.prior_b)
        b_hat, b_std = estimate_win_loss_ratio(pnls)
        k = raw_kelly(p_hat, b_hat, kelly_min=params.kelly_min, kelly_max=params.kelly_max)
        u = uncertainty_adjustment(p=p_hat, p_std=p_std, b=b_hat, b_std_proxy=b_std, floor=params.uncertainty_floor)
        dd_f = drawdown_factor(current_dd, max_dd, gamma=params.dd_gamma)
        frac = s * params.kelly_frac * k * u * lf * dd_f * rf * params.pre_min_trades_penalty  # extra conservatism pre-min_trades
        return KellySizingResult(
            target_fraction_of_capital=_clip(frac, 0.0, 1.0),
            diagnostics={
                "n_trades": float(n),
                "p_hat": float(p_hat),
                "b_hat": float(b_hat),
                "raw_kelly": float(k),
                "uncertainty_adj": float(u),
                "liquidity_factor": float(lf),
                "drawdown_factor": float(dd_f),
                "regime_factor": float(rf),
                "signal_strength": float(s),
                "conservative_penalty": float(params.pre_min_trades_penalty),
            },
        )

    p_hat, p_std = estimate_win_prob(pnls, prior_a=params.prior_a, prior_b=params.prior_b)
    b_hat, b_std = estimate_win_loss_ratio(pnls)
    k = raw_kelly(p_hat, b_hat, kelly_min=params.kelly_min, kelly_max=params.kelly_max)
    u = uncertainty_adjustment(p=p_hat, p_std=p_std, b=b_hat, b_std_proxy=b_std, floor=params.uncertainty_floor)
    dd_f = drawdown_factor(current_dd, max_dd, gamma=params.dd_gamma)

    frac = s * params.kelly_frac * k * u * lf * dd_f * rf

    return KellySizingResult(
        target_fraction_of_capital=_clip(frac, 0.0, 1.0),
        diagnostics={
            "n_trades": float(n),
            "p_hat": float(p_hat),
            "b_hat": float(b_hat),
            "raw_kelly": float(k),
            "uncertainty_adj": float(u),
            "liquidity_factor": float(lf),
            "drawdown_factor": float(dd_f),
            "regime_factor": float(rf),
            "signal_strength": float(s),
            "conservative_penalty": 1.0,
        },
    )


