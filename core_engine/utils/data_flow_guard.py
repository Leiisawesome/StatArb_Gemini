"""
DataFlowGuard — Inline Invariant Assertions for Pipeline Plumbing
=================================================================

Lightweight boolean checks that fire at component boundaries during
execution.  When enabled, violations are logged as warnings (default)
or raised as exceptions (strict mode).  When disabled, every call is
an immediate return — zero overhead.

Design principles:
    - Zero-cost when disabled (guard.enabled checked once per call)
    - Never breaks the pipeline by default (log-only mode)
    - Strict mode available for CI/test environments
    - All violations are counted and retrievable for post-hoc reporting

Usage:
    from core_engine.utils.data_flow_guard import get_guard

    guard = get_guard()
    guard.configure(enabled=True, strict=False)

    # At component boundaries:
    guard.assert_no_lookahead(
        slice_end_ts=features_df.index[-1],
        bar_ts=current_bar_timestamp,
        context="bar_42_TSLA",
    )

    guard.assert_price_coherence(
        decision_price=450.0,
        execution_price=449.5,
        max_drift_pct=5.0,
        context="fill_TSLA_2024-12-18",
    )

Author: StatArb_Gemini Core Engine
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class Violation:
    """A single invariant violation record."""
    check_name: str
    message: str
    context: str = ""
    data: Dict[str, Any] = field(default_factory=dict)


class DataFlowGuard:
    """
    Inline invariant checker for pipeline component boundaries.

    Singleton pattern — one guard per process, configurable at startup.
    """

    _instance: Optional[DataFlowGuard] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._enabled = False
        self._strict = False  # If True, raise on violation instead of logging
        self._violations: List[Violation] = []
        self._stats: Dict[str, int] = {
            "checks_performed": 0,
            "violations_detected": 0,
        }

    @classmethod
    def get_instance(cls) -> DataFlowGuard:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        with cls._lock:
            cls._instance = None

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def violations(self) -> List[Violation]:
        return list(self._violations)

    @property
    def stats(self) -> Dict[str, int]:
        return dict(self._stats)

    @property
    def violation_count(self) -> int:
        return self._stats["violations_detected"]

    def configure(self, enabled: bool = False, strict: bool = False) -> None:
        """Configure the guard.  Call once at startup."""
        self._enabled = enabled
        self._strict = strict
        self._violations.clear()
        self._stats = {"checks_performed": 0, "violations_detected": 0}
        if enabled:
            logger.info(
                f"DataFlowGuard enabled (strict={'ON' if strict else 'OFF'})"
            )

    def _record_violation(self, v: Violation) -> None:
        self._violations.append(v)
        self._stats["violations_detected"] += 1
        msg = f"[GUARD VIOLATION] {v.check_name}: {v.message} ({v.context})"
        if self._strict:
            raise AssertionError(msg)
        else:
            logger.warning(msg)

    # ------------------------------------------------------------------
    # Assertion: No Lookahead
    # ------------------------------------------------------------------

    def assert_no_lookahead(
        self,
        slice_end_ts: Any,
        bar_ts: Any,
        context: str = "",
    ) -> bool:
        """Feature slice must not include current or future bars.

        Args:
            slice_end_ts: Last timestamp in the feature slice.
            bar_ts: Current bar's timestamp.
            context: Human-readable context for violation messages.

        Returns:
            True if safe, False if lookahead detected.
        """
        if not self._enabled:
            return True
        self._stats["checks_performed"] += 1

        try:
            end = pd.Timestamp(slice_end_ts)
            bar = pd.Timestamp(bar_ts)
            if end >= bar:
                self._record_violation(Violation(
                    check_name="no_lookahead",
                    message=f"Feature slice ends at {end} >= bar timestamp {bar}",
                    context=context,
                    data={"slice_end": str(end), "bar_ts": str(bar)},
                ))
                return False
        except Exception as e:
            logger.debug(f"DataFlowGuard.assert_no_lookahead: cannot parse timestamps: {e}")

        return True

    # ------------------------------------------------------------------
    # Assertion: Price Coherence
    # ------------------------------------------------------------------

    def assert_price_coherence(
        self,
        decision_price: float,
        execution_price: float,
        max_drift_pct: float = 5.0,
        context: str = "",
    ) -> bool:
        """Fill price must be within max_drift_pct of decision price.

        Returns:
            True if coherent, False if drift exceeded.
        """
        if not self._enabled:
            return True
        self._stats["checks_performed"] += 1

        if decision_price <= 0:
            return True  # Cannot check without valid decision price

        drift_pct = abs(execution_price - decision_price) / decision_price * 100
        if drift_pct > max_drift_pct:
            self._record_violation(Violation(
                check_name="price_coherence",
                message=(
                    f"Price drift {drift_pct:.2f}% exceeds threshold {max_drift_pct}% "
                    f"(decision={decision_price:.2f}, execution={execution_price:.2f})"
                ),
                context=context,
                data={
                    "decision_price": decision_price,
                    "execution_price": execution_price,
                    "drift_pct": round(drift_pct, 4),
                },
            ))
            return False

        return True

    # ------------------------------------------------------------------
    # Assertion: Quantity Conservation
    # ------------------------------------------------------------------

    def assert_quantity_monotonic(
        self,
        requested: float,
        authorized: float,
        filled: float,
        context: str = "",
    ) -> bool:
        """filled <= authorized <= requested (monotonic reduction).

        Returns:
            True if valid, False if violated.
        """
        if not self._enabled:
            return True
        self._stats["checks_performed"] += 1

        violations = []
        if authorized > requested * 1.01:
            violations.append(f"authorized({authorized:.2f}) > requested({requested:.2f})")
        if filled > authorized * 1.01:
            violations.append(f"filled({filled:.2f}) > authorized({authorized:.2f})")

        if violations:
            self._record_violation(Violation(
                check_name="quantity_monotonic",
                message="; ".join(violations),
                context=context,
                data={"requested": requested, "authorized": authorized, "filled": filled},
            ))
            return False

        return True

    # ------------------------------------------------------------------
    # Assertion: Cash Conservation
    # ------------------------------------------------------------------

    def assert_cash_conservation(
        self,
        prev_cash: float,
        cash_change: float,
        new_cash: float,
        epsilon: float = 0.01,
        context: str = "",
    ) -> bool:
        """prev_cash + cash_change == new_cash (within epsilon).

        Returns:
            True if balanced, False if violated.
        """
        if not self._enabled:
            return True
        self._stats["checks_performed"] += 1

        expected = prev_cash + cash_change
        drift = abs(expected - new_cash)
        if drift > epsilon:
            self._record_violation(Violation(
                check_name="cash_conservation",
                message=(
                    f"{prev_cash:.2f} + {cash_change:.2f} = {expected:.2f} "
                    f"!= {new_cash:.2f} (drift: {drift:.4f})"
                ),
                context=context,
                data={
                    "prev_cash": prev_cash,
                    "cash_change": cash_change,
                    "expected": expected,
                    "new_cash": new_cash,
                    "drift": drift,
                },
            ))
            return False

        return True

    # ------------------------------------------------------------------
    # Assertion: Position Arithmetic
    # ------------------------------------------------------------------

    def assert_position_update(
        self,
        prev_qty: float,
        fill_qty: float,
        fill_side: str,
        new_qty: float,
        epsilon: float = 0.001,
        context: str = "",
    ) -> bool:
        """Position arithmetic is correct given fill side and quantity.

        Returns:
            True if correct, False if violated.
        """
        if not self._enabled:
            return True
        self._stats["checks_performed"] += 1

        if fill_side.lower() in ("buy", "long"):
            expected = prev_qty + fill_qty
        elif fill_side.lower() in ("sell", "short"):
            expected = prev_qty - fill_qty
        else:
            return True  # Unknown side, skip

        drift = abs(expected - new_qty)
        if drift > epsilon:
            self._record_violation(Violation(
                check_name="position_update",
                message=(
                    f"{prev_qty:.4f} {'+' if fill_side.lower() in ('buy', 'long') else '-'} "
                    f"{fill_qty:.4f} = {expected:.4f} != {new_qty:.4f} "
                    f"(drift: {drift:.4f})"
                ),
                context=context,
                data={
                    "prev_qty": prev_qty,
                    "fill_qty": fill_qty,
                    "fill_side": fill_side,
                    "expected": expected,
                    "new_qty": new_qty,
                },
            ))
            return False

        return True

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def print_summary(self) -> str:
        """Print a summary of all guard checks and violations."""
        if not self._enabled:
            return ""

        lines = [
            "",
            "DataFlowGuard Summary",
            "-" * 40,
            f"  Checks performed:    {self._stats['checks_performed']}",
            f"  Violations detected: {self._stats['violations_detected']}",
        ]

        if self._violations:
            lines.append("  Violations:")
            by_check: Dict[str, int] = {}
            for v in self._violations:
                by_check[v.check_name] = by_check.get(v.check_name, 0) + 1
            for name, count in sorted(by_check.items()):
                lines.append(f"    {name}: {count}")

        lines.append("-" * 40)
        output = "\n".join(lines)
        print(output)
        return output


# ---------------------------------------------------------------------------
# Convenience: module-level access
# ---------------------------------------------------------------------------

def get_guard() -> DataFlowGuard:
    """Get the global DataFlowGuard singleton."""
    return DataFlowGuard.get_instance()
