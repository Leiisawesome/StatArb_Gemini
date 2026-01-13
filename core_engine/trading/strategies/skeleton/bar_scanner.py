"""
Skeleton bar-scanning utilities (Rule 7).

This module centralizes strategy-agnostic orchestration patterns (e.g., scanning
historical bars at an interval). Strategy implementations should provide the
core-alpha evaluation callback(s), while this module handles iteration semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, List, Optional


@dataclass(frozen=True)
class BarScanResult:
    signals: List[Any]
    bars_evaluated: int


async def scan_bars_at_interval(
    *,
    start_idx: int,
    end_idx: int,
    scan_interval: int,
    emit_pending_at_index: Optional[Callable[[int], Optional[Any]]] = None,
    evaluate_at_index: Callable[[int], Awaitable[Optional[Any]]],
) -> BarScanResult:
    """
    Scan indices [start_idx, end_idx) stepping by scan_interval, producing signals.

    - `emit_pending_at_index`: optional sync callback to emit a matured pending signal
    - `evaluate_at_index`: required async callback that returns a signal (or None)
    """
    if scan_interval <= 0:
        raise ValueError(f"scan_interval must be > 0, got {scan_interval}")
    if end_idx < start_idx:
        return BarScanResult(signals=[], bars_evaluated=0)

    signals: List[Any] = []
    bars_evaluated = 0

    for idx in range(start_idx, end_idx, scan_interval):
        if emit_pending_at_index is not None:
            matured = emit_pending_at_index(idx)
            if matured is not None:
                signals.append(matured)

        signal = await evaluate_at_index(idx)
        if signal is not None:
            signals.append(signal)
        bars_evaluated += 1

    return BarScanResult(signals=signals, bars_evaluated=bars_evaluated)

