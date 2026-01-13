"""
Skeleton SignalType utilities (Rule 7).

Provides strategy-agnostic helpers for interpreting SignalType enums.
"""

from __future__ import annotations

from core_engine.type_definitions.strategy import SignalType


def is_long_signal(signal_type: SignalType) -> bool:
    return signal_type in (SignalType.BUY, SignalType.LONG_ENTRY)


def is_short_signal(signal_type: SignalType) -> bool:
    return signal_type in (SignalType.SELL, SignalType.SHORT_ENTRY)


def side_from_signal(signal_type: SignalType) -> str:
    """
    Normalize signal type to BUY/SELL string (used by pending queue).
    """
    if is_long_signal(signal_type):
        return "BUY"
    if is_short_signal(signal_type):
        return "SELL"
    return "UNKNOWN"

