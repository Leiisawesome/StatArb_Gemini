"""
Skeleton helpers for ADS/SMS glue code (Rule 7).

These functions are strategy-agnostic and support multiple strategies that consume
ADS continuous regime vectors and SMS gating.
"""

from __future__ import annotations

from core_engine.alpha.ads_regime_vector import ADSRegimeVector


def sms_regime_label_from_ads_vector(r: ADSRegimeVector) -> str:
    """
    Map ADS regime vector to the SMS exponent label used by SignalMaturityScore.
    """
    v = float(r.volatility)
    if v <= 0.30:
        return "low_vol"
    if v <= 0.70:
        return "normal"
    if v <= 0.90:
        return "high_vol"
    return "crisis"

