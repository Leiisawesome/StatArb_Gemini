"""
Skeleton helpers for ADS/SMS glue code (Rule 7).

These functions are strategy-agnostic and support multiple strategies that consume
ADS continuous regime vectors and SMS gating.
"""

from __future__ import annotations

import math
from typing import Any, Optional

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


def compute_sms_info_increment(
    *,
    row: Any,
    prev_row: Optional[Any] = None,
    volume_ratio_fallback: float = 1.0,
    w_volume: float = 0.55,
    w_volatility: float = 0.45,
    cap: float = 3.0,
) -> float:
    """
    Compute a lightweight "information-time" increment for SMS maturation.
    """

    def _get(obj: Any, key: str, default: float) -> float:
        try:
            if hasattr(obj, "get"):
                v = obj.get(key, default)
            else:
                v = getattr(obj, key, default)
            if v is None:
                return float(default)
            return float(v)
        except Exception:
            return float(default)

    # Volume event: log-compressed so open/close spikes don't dominate
    vol_ratio = _get(row, "volume_ratio", float(volume_ratio_fallback))
    vol_ratio = max(0.0, vol_ratio)
    volume_event = math.log1p(vol_ratio)

    # Volatility event: normalize by ATR/price if available; else raw abs return
    close = _get(row, "close", 0.0)
    prev_close = _get(prev_row, "close", close) if prev_row is not None else close
    if close <= 0.0 or prev_close <= 0.0:
        abs_ret = 0.0
    else:
        abs_ret = abs(close / prev_close - 1.0)

    atr = _get(row, "atr", 0.0)
    if atr > 0.0 and close > 0.0:
        typical = max(1e-9, abs(float(atr)) / float(close))
        volatility_event = abs_ret / typical
    else:
        volatility_event = abs_ret

    info = float(w_volume) * float(volume_event) + float(w_volatility) * float(volatility_event)
    return float(min(max(info, 0.0), float(cap)))

