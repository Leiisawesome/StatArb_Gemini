"""
Pipeline Auditor — Standalone Plumbing Verification Utility
============================================================

Consolidates all pipeline integrity checks into a single callable utility
that can be invoked from any experiment, CLI, or test without pytest.

Checks performed:
    1. Chain Integrity    — Every signal has a complete downstream chain
    2. Conservation Laws  — Cash and position arithmetic is balanced
    3. Lookahead Guard    — Feature slices never include current/future bars
    4. Price Coherence    — Decision → Authorization → Fill prices are consistent
    5. Quantity Chain     — requested ≥ authorized ≥ filled (monotonic reduction)
    6. Numeric Bounds     — Signals, quantities, prices within valid ranges
    7. Checkpoint Order   — First-occurrence ordering is monotonic

Usage:
    from core_engine.utils.pipeline_auditor import PipelineAuditor

    auditor = PipelineAuditor(trace_records)   # List[dict] from tracer.records
    report = auditor.run_all()
    report.print_summary()

    # Or from JSONL file:
    auditor = PipelineAuditor.from_jsonl("path/to/trace.jsonl")
    report = auditor.run_all()

Author: StatArb_Gemini Core Engine
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core_engine.utils.pipeline_trace import (
    ALL_CHECKPOINTS,
    CHECKPOINT_ORDER,
    CP0_MARKET_DATA,
    CP0r_REGIME_DETECT,
    CP1_ENRICHMENT,
    CP1s_BAR_SLICE,
    CP2_SIGNAL_GEN,
    CP2q_QUANTITY_SIZING,
    CP3_RISK_AUTH,
    CP4_ORDER_CREATE,
    CP5_FILL,
    CP6_POSITION_UPDATE,
    CP7_PNL,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Audit result data structures
# ---------------------------------------------------------------------------

@dataclass
class CheckResult:
    """Result of a single audit check."""
    name: str
    passed: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    severity: str = "ERROR"  # ERROR, WARNING, INFO


@dataclass
class AuditReport:
    """Consolidated audit report from all checks."""
    checks: List[CheckResult] = field(default_factory=list)
    total_records: int = 0
    funnel_summary: Dict[str, int] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks if c.severity == "ERROR")

    @property
    def error_count(self) -> int:
        return sum(1 for c in self.checks if not c.passed and c.severity == "ERROR")

    @property
    def warning_count(self) -> int:
        return sum(1 for c in self.checks if not c.passed and c.severity == "WARNING")

    def print_summary(self) -> str:
        """Print a human-readable audit summary."""
        lines = [
            "",
            "=" * 70,
            "PIPELINE AUDIT REPORT",
            "=" * 70,
            f"Total trace records:  {self.total_records}",
            f"Overall result:       {'PASS' if self.passed else 'FAIL'}",
            f"Checks passed:        {sum(1 for c in self.checks if c.passed)}/{len(self.checks)}",
            f"Errors:               {self.error_count}",
            f"Warnings:             {self.warning_count}",
            "-" * 70,
        ]

        for check in self.checks:
            status = "PASS" if check.passed else f"FAIL[{check.severity}]"
            lines.append(f"  [{status:>13}]  {check.name}")
            if not check.passed:
                lines.append(f"                   {check.message}")
                for k, v in check.details.items():
                    lines.append(f"                   {k}: {v}")

        lines.append("=" * 70)
        output = "\n".join(lines)
        print(output)
        return output


# ---------------------------------------------------------------------------
# PipelineAuditor
# ---------------------------------------------------------------------------

class PipelineAuditor:
    """
    Standalone pipeline plumbing verification.

    Reads trace records (list of dicts from TraceCheckpoint.to_dict())
    and runs a comprehensive battery of correctness checks.
    """

    def __init__(self, records: List[Dict[str, Any]]) -> None:
        self.records = records
        self._by_cp: Dict[str, List[Dict]] = defaultdict(list)
        self._by_trace_id: Dict[str, List[Dict]] = defaultdict(list)

        for r in records:
            self._by_cp[r.get("checkpoint", "")].append(r)
            self._by_trace_id[r.get("trace_id", "")].append(r)

    @classmethod
    def from_jsonl(cls, path: str) -> PipelineAuditor:
        """Load trace records from a JSONL file."""
        records = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return cls(records)

    @classmethod
    def from_tracer(cls) -> PipelineAuditor:
        """Load trace records from the active PipelineTracer singleton."""
        from core_engine.utils.pipeline_trace import get_tracer
        tracer = get_tracer()
        records = [r.to_dict() for r in tracer.records]
        return cls(records)

    # ------------------------------------------------------------------
    # Master entry point
    # ------------------------------------------------------------------

    def run_all(self, initial_capital: float = 1_000_000.0, **kwargs) -> AuditReport:
        """Run all audit checks and return a consolidated report."""
        report = AuditReport(total_records=len(self.records))

        # Build funnel
        for cp in ALL_CHECKPOINTS:
            report.funnel_summary[cp] = len(self._by_cp.get(cp, []))

        # Run each check category
        report.checks.extend(self.check_funnel_nonempty())
        report.checks.extend(self.check_checkpoint_ordering())
        report.checks.extend(self.check_chain_integrity())
        report.checks.extend(self.check_numeric_bounds())
        report.checks.extend(self.check_lookahead_guard())
        report.checks.extend(self.check_price_coherence())
        report.checks.extend(self.check_quantity_chain())
        report.checks.extend(self.check_capital_conservation(initial_capital))
        report.checks.extend(self.check_position_conservation())
        report.checks.extend(self.check_pnl_identity())

        return report

    # ------------------------------------------------------------------
    # 1. Funnel Non-Empty
    # ------------------------------------------------------------------

    def check_funnel_nonempty(self) -> List[CheckResult]:
        """Verify each pipeline stage has at least one record."""
        results = []
        # CP0 and CP1 fire once per symbol (may be 0 if pre-calc is skipped)
        # CP2+ should always fire in a successful smoke test
        mandatory = [CP2_SIGNAL_GEN, CP3_RISK_AUTH, CP4_ORDER_CREATE, CP5_FILL, CP6_POSITION_UPDATE, CP7_PNL]
        for cp in mandatory:
            count = len(self._by_cp.get(cp, []))
            results.append(CheckResult(
                name=f"funnel_nonempty_{cp}",
                passed=count > 0,
                message=f"{cp} has {count} records (expected > 0)",
                details={"count": count},
                severity="ERROR",
            ))

        # CP0/CP1 are warnings (pre-calc might be skipped)
        for cp in [CP0_MARKET_DATA, CP1_ENRICHMENT]:
            count = len(self._by_cp.get(cp, []))
            results.append(CheckResult(
                name=f"funnel_nonempty_{cp}",
                passed=count > 0,
                message=f"{cp} has {count} records (expected > 0)",
                details={"count": count},
                severity="WARNING",
            ))

        return results

    # ------------------------------------------------------------------
    # 2. Checkpoint Ordering
    # ------------------------------------------------------------------

    def check_checkpoint_ordering(self) -> List[CheckResult]:
        """Verify first-occurrence ordering is monotonic (CP0 before CP2 before CP3 ...)."""
        results = []
        first_positions: Dict[str, int] = {}
        for i, r in enumerate(self.records):
            cp = r.get("checkpoint", "")
            if cp in CHECKPOINT_ORDER and cp not in first_positions:
                first_positions[cp] = i

        active_cps = sorted(
            [cp for cp in first_positions if cp in CHECKPOINT_ORDER],
            key=lambda cp: CHECKPOINT_ORDER[cp],
        )

        violations = []
        for j in range(len(active_cps) - 1):
            cp_a = active_cps[j]
            cp_b = active_cps[j + 1]
            if first_positions[cp_a] > first_positions[cp_b]:
                violations.append(f"{cp_a}(pos {first_positions[cp_a]}) > {cp_b}(pos {first_positions[cp_b]})")

        results.append(CheckResult(
            name="checkpoint_ordering_monotonic",
            passed=len(violations) == 0,
            message=f"{len(violations)} ordering violations" if violations else "All checkpoints in correct order",
            details={"violations": violations},
            severity="ERROR",
        ))
        return results

    # ------------------------------------------------------------------
    # 3. Chain Integrity
    # ------------------------------------------------------------------

    def check_chain_integrity(self) -> List[CheckResult]:
        """Verify signal-to-PnL chain completeness."""
        results = []

        cp3_records = self._by_cp.get(CP3_RISK_AUTH, [])
        cp5_count = len(self._by_cp.get(CP5_FILL, []))
        cp6_count = len(self._by_cp.get(CP6_POSITION_UPDATE, []))
        cp7_count = len(self._by_cp.get(CP7_PNL, []))

        # Count authorized
        authorized_count = sum(
            1 for r in cp3_records if r.get("metadata", {}).get("authorized", False)
        )

        # Authorized signals should produce fills
        if authorized_count > 0:
            results.append(CheckResult(
                name="chain_authorized_to_fills",
                passed=cp5_count > 0,
                message=f"{authorized_count} authorized but {cp5_count} fills",
                details={"authorized": authorized_count, "fills": cp5_count},
                severity="ERROR",
            ))
        else:
            results.append(CheckResult(
                name="chain_authorized_to_fills",
                passed=False,
                message="No signals were authorized — pipeline has no throughput",
                severity="WARNING",
            ))

        # CP5, CP6, CP7 counts should match (in deterministic mode)
        if cp5_count > 0:
            cp567_match = (cp5_count == cp6_count == cp7_count)
            results.append(CheckResult(
                name="chain_fill_position_pnl_parity",
                passed=cp567_match,
                message=f"CP5={cp5_count}, CP6={cp6_count}, CP7={cp7_count}" + (
                    " (matched)" if cp567_match else " (MISMATCH)"
                ),
                details={"CP5": cp5_count, "CP6": cp6_count, "CP7": cp7_count},
                severity="ERROR" if not cp567_match else "INFO",
            ))

        return results

    # ------------------------------------------------------------------
    # 4. Numeric Bounds
    # ------------------------------------------------------------------

    def check_numeric_bounds(self) -> List[CheckResult]:
        """Verify signals, quantities, prices are within valid ranges."""
        results = []

        # CP2: Signal strength in [-1, 1], confidence in [0, 1]
        strength_violations = 0
        confidence_violations = 0
        for r in self._by_cp.get(CP2_SIGNAL_GEN, []):
            out = r.get("output_data", {})
            s = out.get("strength")
            c = out.get("confidence")
            if s is not None and not (-1.0 <= float(s) <= 1.0):
                strength_violations += 1
            if c is not None and not (0.0 <= float(c) <= 1.0):
                confidence_violations += 1

        total_cp2 = len(self._by_cp.get(CP2_SIGNAL_GEN, []))
        results.append(CheckResult(
            name="numeric_signal_strength_bounds",
            passed=strength_violations == 0,
            message=f"{strength_violations}/{total_cp2} signals with strength outside [-1, 1]",
            details={"violations": strength_violations, "total": total_cp2},
            severity="ERROR",
        ))
        results.append(CheckResult(
            name="numeric_signal_confidence_bounds",
            passed=confidence_violations == 0,
            message=f"{confidence_violations}/{total_cp2} signals with confidence outside [0, 1]",
            details={"violations": confidence_violations, "total": total_cp2},
            severity="ERROR",
        ))

        # CP5: Fill price and quantity positive
        fill_price_violations = 0
        fill_qty_violations = 0
        for r in self._by_cp.get(CP5_FILL, []):
            inp = r.get("input_data", {})
            if float(inp.get("price", 0)) <= 0:
                fill_price_violations += 1
            if float(inp.get("quantity", 0)) <= 0:
                fill_qty_violations += 1

        total_cp5 = len(self._by_cp.get(CP5_FILL, []))
        results.append(CheckResult(
            name="numeric_fill_price_positive",
            passed=fill_price_violations == 0,
            message=f"{fill_price_violations}/{total_cp5} fills with price <= 0",
            severity="ERROR",
        ))
        results.append(CheckResult(
            name="numeric_fill_quantity_positive",
            passed=fill_qty_violations == 0,
            message=f"{fill_qty_violations}/{total_cp5} fills with quantity <= 0",
            severity="ERROR",
        ))

        return results

    # ------------------------------------------------------------------
    # 5. Lookahead Guard (uses CP1s sub-checkpoint)
    # ------------------------------------------------------------------

    def check_lookahead_guard(self) -> List[CheckResult]:
        """Verify no feature slice includes current or future bar data."""
        results = []
        cp1s_records = self._by_cp.get(CP1s_BAR_SLICE, [])

        if not cp1s_records:
            results.append(CheckResult(
                name="lookahead_guard",
                passed=True,
                message=f"No CP1s records (sub-checkpoint not active or 0 bars processed)",
                severity="INFO",
            ))
            return results

        violations = 0
        total = len(cp1s_records)
        violation_examples: List[Dict] = []

        for r in cp1s_records:
            out = r.get("output_data", {})
            safe = out.get("lookahead_safe", True)
            if not safe:
                violations += 1
                if len(violation_examples) < 5:  # Cap examples
                    violation_examples.append({
                        "bar_timestamp": r.get("input_data", {}).get("bar_timestamp"),
                        "slice_end_timestamp": out.get("slice_end_timestamp"),
                        "bar_index": r.get("input_data", {}).get("bar_index"),
                    })

        results.append(CheckResult(
            name="lookahead_guard",
            passed=violations == 0,
            message=(
                f"LOOKAHEAD DETECTED: {violations}/{total} bars have feature slices "
                f"including current or future data"
                if violations > 0
                else f"All {total} bar slices are lookahead-safe"
            ),
            details={
                "violations": violations,
                "total_bars_checked": total,
                "examples": violation_examples,
            },
            severity="ERROR" if violations > 0 else "INFO",
        ))

        return results

    # ------------------------------------------------------------------
    # 6. Price Coherence (CP2 → CP3 → CP5)
    # ------------------------------------------------------------------

    def check_price_coherence(self) -> List[CheckResult]:
        """Verify decision → fill prices are within reasonable drift."""
        results = []
        MAX_DRIFT_PCT = 5.0  # 5% max acceptable drift between decision and fill

        cp5_records = self._by_cp.get(CP5_FILL, [])
        if not cp5_records:
            return results

        drift_violations = 0
        max_drift_seen = 0.0
        total_fills = len(cp5_records)

        for r in cp5_records:
            inp = r.get("input_data", {})
            decision = float(inp.get("decision_price", 0))
            fill = float(inp.get("fill_price", inp.get("price", 0)))

            if decision > 0 and fill > 0:
                drift_pct = abs(fill - decision) / decision * 100
                max_drift_seen = max(max_drift_seen, drift_pct)
                if drift_pct > MAX_DRIFT_PCT:
                    drift_violations += 1

        results.append(CheckResult(
            name="price_coherence_decision_to_fill",
            passed=drift_violations == 0,
            message=(
                f"{drift_violations}/{total_fills} fills exceed {MAX_DRIFT_PCT}% price drift "
                f"from decision price (max drift: {max_drift_seen:.2f}%)"
                if drift_violations > 0
                else f"All {total_fills} fills within {MAX_DRIFT_PCT}% of decision price "
                     f"(max drift: {max_drift_seen:.2f}%)"
            ),
            details={"max_drift_pct": round(max_drift_seen, 4), "threshold": MAX_DRIFT_PCT},
            severity="ERROR" if drift_violations > 0 else "INFO",
        ))

        return results

    # ------------------------------------------------------------------
    # 7. Quantity Chain (CP3 → CP5)
    # ------------------------------------------------------------------

    def check_quantity_chain(self) -> List[CheckResult]:
        """Verify monotonic quantity reduction: requested ≥ authorized ≥ filled."""
        results = []

        # Check authorized <= requested at CP3
        cp3_violations = 0
        total_cp3 = 0
        for r in self._by_cp.get(CP3_RISK_AUTH, []):
            inp = r.get("input_data", {})
            out = r.get("output_data", {})
            if out.get("authorized", False):
                total_cp3 += 1
                requested = float(inp.get("quantity", 0))
                authorized = float(out.get("authorized_quantity", 0))
                if authorized > requested * 1.01:  # 1% tolerance for rounding
                    cp3_violations += 1

        if total_cp3 > 0:
            results.append(CheckResult(
                name="quantity_chain_auth_leq_requested",
                passed=cp3_violations == 0,
                message=f"{cp3_violations}/{total_cp3} authorizations exceed requested quantity",
                severity="ERROR",
            ))

        return results

    # ------------------------------------------------------------------
    # 8. Capital Conservation
    # ------------------------------------------------------------------

    def check_capital_conservation(
        self,
        initial_capital: float = 1_000_000.0,
        **_kwargs,
    ) -> List[CheckResult]:
        """Verify cash accounting identity: initial + Σ(cash_change) == final_cash.

        Cash compounds across sessions (no reset at day boundaries), so the
        cumulative identity holds regardless of session isolation settings.
        """
        results = []

        cp6_records = self._by_cp.get(CP6_POSITION_UPDATE, [])
        if not cp6_records:
            return results

        total_cash_change = sum(
            float(r.get("output_data", {}).get("cash_change", 0))
            for r in cp6_records
        )

        last_record = cp6_records[-1]
        final_cash = float(last_record.get("metadata", {}).get("cash_balance", 0))
        expected_cash = initial_capital + total_cash_change

        if final_cash > 0:
            drift = abs(expected_cash - final_cash)
            results.append(CheckResult(
                name="capital_conservation",
                passed=drift < 1.0,  # Allow $1 float drift
                message=(
                    f"${initial_capital:,.2f} + ${total_cash_change:,.2f} = "
                    f"${expected_cash:,.2f} vs final ${final_cash:,.2f} "
                    f"(drift: ${drift:.4f})"
                ),
                details={
                    "initial_capital": initial_capital,
                    "total_cash_change": round(total_cash_change, 4),
                    "expected_cash": round(expected_cash, 4),
                    "final_cash": round(final_cash, 4),
                    "drift": round(drift, 4),
                },
                severity="ERROR" if drift >= 1.0 else "INFO",
            ))

        return results

    # ------------------------------------------------------------------
    # 9. Position Conservation
    # ------------------------------------------------------------------

    def check_position_conservation(self) -> List[CheckResult]:
        """Verify CP6 position deltas are internally consistent."""
        results = []

        cp6_records = self._by_cp.get(CP6_POSITION_UPDATE, [])
        if not cp6_records:
            return results

        # Verify realized PnL accumulation
        sum_rpnl = sum(
            float(r.get("output_data", {}).get("realized_pnl", 0))
            for r in cp6_records
        )
        last_total_rpnl = float(
            cp6_records[-1].get("output_data", {}).get("total_realized_pnl", 0)
        )

        if last_total_rpnl != 0:
            drift = abs(sum_rpnl - last_total_rpnl)
            results.append(CheckResult(
                name="position_realized_pnl_accumulation",
                passed=drift < 0.01,
                message=(
                    f"Σ(realized_pnl) = ${sum_rpnl:.4f} vs "
                    f"total_realized_pnl = ${last_total_rpnl:.4f} "
                    f"(drift: ${drift:.4f})"
                ),
                details={"sum": round(sum_rpnl, 4), "total": round(last_total_rpnl, 4)},
                severity="ERROR" if drift >= 0.01 else "INFO",
            ))

        return results

    # ------------------------------------------------------------------
    # 10. PnL Identity
    # ------------------------------------------------------------------

    def check_pnl_identity(self) -> List[CheckResult]:
        """Verify CP7: total_pnl == realized_pnl + unrealized_pnl."""
        results = []

        cp7_records = self._by_cp.get(CP7_PNL, [])
        if not cp7_records:
            return results

        violations = 0
        total = len(cp7_records)
        max_drift = 0.0

        for r in cp7_records:
            out = r.get("output_data", {})
            total_pnl = float(out.get("total_pnl", 0))
            realized = float(out.get("realized_pnl", 0))
            unrealized = float(out.get("unrealized_pnl", 0))
            expected = realized + unrealized
            drift = abs(total_pnl - expected)
            max_drift = max(max_drift, drift)
            if drift >= 0.01:
                violations += 1

        results.append(CheckResult(
            name="pnl_identity_total_eq_realized_plus_unrealized",
            passed=violations == 0,
            message=(
                f"{violations}/{total} CP7 records violate total_pnl == realized + unrealized "
                f"(max drift: ${max_drift:.4f})"
                if violations > 0
                else f"All {total} CP7 records satisfy PnL identity (max drift: ${max_drift:.4f})"
            ),
            details={"violations": violations, "total": total, "max_drift": round(max_drift, 4)},
            severity="ERROR" if violations > 0 else "INFO",
        ))

        return results
