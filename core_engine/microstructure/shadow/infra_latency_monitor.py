"""
Infrastructure latency monitor for shadow trading system.

Tracks three distinct latency paths (ingest, order RTT, cancel ack)
with p50/p95/p99 statistics. Enforces both relative drift (2x rolling
10-day baseline) and absolute caps (250/400/500ms).

Spec: v1.7-SHADOW
Build Plan: v4-FINAL, Pre-Requisite
"""

from __future__ import annotations

import logging
import statistics
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, List, Optional

from core_engine.microstructure.shadow.constants import (
    CANCEL_ACK_MEDIAN_CAP_MS,
    INGEST_P95_CAP_MS,
    LATENCY_BASELINE_WINDOW_DAYS,
    LATENCY_RELATIVE_DRIFT_MULT,
    NTP_MAX_OFFSET_MS,
    ORDER_RTT_P95_CAP_MS,
)
from core_engine.microstructure.shadow.types import LatencyPath, LatencySnapshot

logger = logging.getLogger(__name__)


_ABSOLUTE_CAPS: Dict[LatencyPath, int] = {
    LatencyPath.INGEST: INGEST_P95_CAP_MS,
    LatencyPath.ORDER_RTT: ORDER_RTT_P95_CAP_MS,
    LatencyPath.CANCEL_ACK: CANCEL_ACK_MEDIAN_CAP_MS,
}


class InfrastructureLatencyMonitor:
    """Monitors clock sync and three-path latency variance.

    Latency paths:
    - INGEST: Polygon exchange_ts -> system receive time
    - ORDER_RTT: system order submit -> IBKR acknowledgment
    - CANCEL_ACK: system cancel request -> IBKR confirmation

    Triggers:
    - Relative: p95 > 2x rolling 10-day baseline
    - Absolute: p95 exceeds hard caps (250/400/500ms)
    """

    def __init__(self) -> None:
        # Per-path latency samples (rolling window)
        self._samples: Dict[LatencyPath, Deque[float]] = {
            path: deque(maxlen=10_000) for path in LatencyPath
        }

        # Historical baselines (loaded from Step 7 backtest)
        self._baselines: Dict[LatencyPath, Optional[float]] = {
            path: None for path in LatencyPath
        }

        # Rolling 10-day p95 for relative drift
        self._daily_p95s: Dict[LatencyPath, Deque[float]] = {
            path: deque(maxlen=LATENCY_BASELINE_WINDOW_DAYS) for path in LatencyPath
        }

        # Clock sync tracking
        self._clock_offsets: Deque[float] = deque(maxlen=5000)
        self._paused: bool = False

    def set_baseline(self, path: LatencyPath, baseline_p95_ms: float) -> None:
        """Set historical baseline for a path (from Step 7)."""
        self._baselines[path] = baseline_p95_ms

    def record_latency(self, path: LatencyPath, latency_ms: float) -> None:
        """Record a single latency observation."""
        self._samples[path].append(latency_ms)

    def record_clock_offset(self, offset_ms: float) -> None:
        """Record exchange_ts - system_receive_ts offset."""
        self._clock_offsets.append(offset_ms)

    def record_daily_p95(self, path: LatencyPath, p95_ms: float) -> None:
        """Record end-of-day p95 for rolling baseline computation."""
        self._daily_p95s[path].append(p95_ms)

    def get_snapshot(self, path: LatencyPath) -> LatencySnapshot:
        """Get current statistics for a latency path."""
        samples = list(self._samples[path])
        if not samples:
            return LatencySnapshot(
                path=path, p50_ms=0, p95_ms=0, p99_ms=0, sample_count=0,
                baseline_p95_ms=self._baselines[path],
                absolute_cap_ms=_ABSOLUTE_CAPS.get(path),
            )

        sorted_s = sorted(samples)
        n = len(sorted_s)
        p50 = sorted_s[int(n * 0.50)]
        p95 = sorted_s[min(int(n * 0.95), n - 1)]
        p99 = sorted_s[min(int(n * 0.99), n - 1)]

        # Compute rolling baseline from daily p95s
        daily = list(self._daily_p95s[path])
        baseline = (
            statistics.mean(daily) if daily
            else self._baselines[path]
        )

        return LatencySnapshot(
            path=path,
            p50_ms=p50,
            p95_ms=p95,
            p99_ms=p99,
            sample_count=n,
            baseline_p95_ms=baseline,
            absolute_cap_ms=_ABSOLUTE_CAPS.get(path),
        )

    def check_health(self) -> tuple[bool, List[str]]:
        """Check all paths for breaches.

        Returns (healthy, list_of_issues).
        """
        issues: List[str] = []

        # Clock sync check
        if self._clock_offsets:
            median_offset = statistics.median(self._clock_offsets)
            if abs(median_offset) > NTP_MAX_OFFSET_MS:
                issues.append(
                    f"Clock drift: median offset {median_offset:.1f}ms > ±{NTP_MAX_OFFSET_MS}ms"
                )

        # Per-path checks
        for path in LatencyPath:
            snap = self.get_snapshot(path)
            if snap.sample_count == 0:
                continue

            if snap.absolute_breach:
                issues.append(
                    f"{path.value}: p95={snap.p95_ms:.0f}ms > absolute cap {snap.absolute_cap_ms}ms"
                )

            if snap.relative_breach:
                issues.append(
                    f"{path.value}: p95={snap.p95_ms:.0f}ms > 2x baseline {snap.baseline_p95_ms:.0f}ms"
                )

        return len(issues) == 0, issues

    def should_pause(self) -> bool:
        """Returns True if any absolute cap is breached."""
        for path in LatencyPath:
            snap = self.get_snapshot(path)
            if snap.absolute_breach:
                return True

        if self._clock_offsets:
            median_offset = statistics.median(self._clock_offsets)
            if abs(median_offset) > NTP_MAX_OFFSET_MS:
                return True

        return False

    def reset_samples(self) -> None:
        """Clear intraday samples (call at start of day)."""
        for path in LatencyPath:
            self._samples[path].clear()
        self._clock_offsets.clear()
