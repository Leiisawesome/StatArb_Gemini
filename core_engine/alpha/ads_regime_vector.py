"""
ADS v3.1 Regime Vector Adapter
=============================

ADS v3.1 requires strategies/risk to consume a *continuous* regime vector R, while
allowing discrete labels only as deterministic functions of that vector.

This module provides a minimal, engineering-complete adapter from the existing
system-wide `RegimeContext` into an ADS-friendly numeric vector.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


try:
    # Canonical system regime context
    from core_engine.system.interfaces import RegimeContext
except Exception:  # pragma: no cover - unit tests may import without full system wiring
    RegimeContext = Any  # type: ignore


@dataclass(frozen=True)
class ADSRegimeVector:
    """
    Minimal ADS numeric regime vector.

    R_vol         in [0, 1]
    R_trend       in [-1, 1]
    R_liq         in [0, 1]
    R_micro       in [0, 1]
    d_*           in R  (smoothed first differences; optional / best-effort)
    confidence    in [0, 1]
    """

    volatility: float
    trend: float
    liquidity: float
    microstructure: float
    d_volatility: float = 0.0
    d_trend: float = 0.0
    d_liquidity: float = 0.0
    d_microstructure: float = 0.0
    confidence: float = 0.5

    @staticmethod
    def _clip(x: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, float(x)))

    @classmethod
    def from_regime_context(
        cls,
        regime_context: Optional[RegimeContext],
        *,
        liquidity: Optional[float] = None,
        microstructure: Optional[float] = None,
        prev: Optional["ADSRegimeVector"] = None,
        ewma_alpha: float = 0.3,
    ) -> Tuple["ADSRegimeVector", Dict[str, Any]]:
        """
        Build an ADSRegimeVector from a RegimeContext.

        Returns (vector, diagnostics) where diagnostics includes which fallbacks were used.
        """

        fallbacks: Dict[str, Any] = {"used": []}

        if regime_context is None:
            # Conservative but permissive defaults (explicitly flagged)
            fallbacks["used"].append("regime_context_missing")
            base = cls(
                volatility=0.5,
                trend=0.0,
                liquidity=cls._clip(liquidity if liquidity is not None else 0.6, 0.0, 1.0),
                microstructure=cls._clip(microstructure if microstructure is not None else 0.6, 0.0, 1.0),
                confidence=0.5,
            )
            return cls._with_velocities(base, prev=prev, ewma_alpha=ewma_alpha), fallbacks

        # Confidence
        conf = getattr(regime_context, "regime_confidence", 0.5)
        if conf is None:
            fallbacks["used"].append("regime_confidence_missing")
            conf = 0.5
        conf = cls._clip(conf, 0.0, 1.0)

        # Volatility regime mapping to [0, 1]
        vol_reg = str(getattr(regime_context, "volatility_regime", "normal_volatility") or "normal_volatility").lower()
        if "extreme" in vol_reg or "crisis" in vol_reg:
            r_vol = 1.0
        elif "high" in vol_reg:
            r_vol = 0.8
        elif "low" in vol_reg:
            r_vol = 0.2
        else:
            r_vol = 0.5

        # Trend regime mapping to [-1, 1]
        tr_reg = str(getattr(regime_context, "trend_regime", "sideways") or "sideways").lower()
        if "strong_up" in tr_reg:
            r_trend = 1.0
        elif "weak_up" in tr_reg:
            r_trend = 0.5
        elif "strong_down" in tr_reg:
            r_trend = -1.0
        elif "weak_down" in tr_reg:
            r_trend = -0.5
        else:
            r_trend = 0.0

        # Liquidity and microstructure are optional numeric inputs; if not supplied, fall back
        if liquidity is None:
            fallbacks["used"].append("liquidity_missing_defaulted")
            liquidity = 0.6
        if microstructure is None:
            fallbacks["used"].append("microstructure_missing_defaulted")
            microstructure = 0.6

        base = cls(
            volatility=cls._clip(r_vol, 0.0, 1.0),
            trend=cls._clip(r_trend, -1.0, 1.0),
            liquidity=cls._clip(liquidity, 0.0, 1.0),
            microstructure=cls._clip(microstructure, 0.0, 1.0),
            confidence=conf,
        )

        return cls._with_velocities(base, prev=prev, ewma_alpha=ewma_alpha), fallbacks

    @classmethod
    def _with_velocities(
        cls,
        curr: "ADSRegimeVector",
        *,
        prev: Optional["ADSRegimeVector"],
        ewma_alpha: float,
    ) -> "ADSRegimeVector":
        if prev is None:
            return curr

        α = cls._clip(ewma_alpha, 0.0, 1.0)

        # EWMA-smoothed deltas to avoid noise-triggering
        d_vol = α * (curr.volatility - prev.volatility) + (1 - α) * prev.d_volatility
        d_trend = α * (curr.trend - prev.trend) + (1 - α) * prev.d_trend
        d_liq = α * (curr.liquidity - prev.liquidity) + (1 - α) * prev.d_liquidity
        d_micro = α * (curr.microstructure - prev.microstructure) + (1 - α) * prev.d_microstructure

        return cls(
            volatility=curr.volatility,
            trend=curr.trend,
            liquidity=curr.liquidity,
            microstructure=curr.microstructure,
            d_volatility=d_vol,
            d_trend=d_trend,
            d_liquidity=d_liq,
            d_microstructure=d_micro,
            confidence=curr.confidence,
        )


def compute_sms_tau(
    r: ADSRegimeVector,
    *,
    tau_0: float = 0.50,
    ofi_proxy_used: bool = False,
    bb_missing: bool = False,
) -> float:
    """
    ADS v3.1 Appendix A.1 recommended SMS threshold:

        tau = clip(tau0 + 0.15*R_vol + 0.10*(1-R_liq) + 0.10*(1-Conf), 0.35, 0.80)

    Then apply small conservative increments when fallbacks are used.
    """

    base = (
        float(tau_0)
        + 0.15 * r.volatility
        + 0.10 * (1.0 - r.liquidity)
        + 0.10 * (1.0 - r.confidence)
    )

    if ofi_proxy_used:
        base += 0.05
    if bb_missing:
        base += 0.05

    return max(0.35, min(0.80, base))


