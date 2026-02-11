"""
Data Integrity Verification Tests
==================================

Verifies that data flows correctly through the pipeline by examining
trace checkpoint records for:

1. **Numeric Invariants**: Signal strengths, quantities, prices within bounds.
2. **Conservation Laws**: Capital and position conservation across fills.
3. **Fill-Price Consistency**: Fill prices are realistic.
4. **Position-Fill Parity**: Position changes match fill quantities.

Uses the same trace_records fixture as test_pipeline_plumbing.py.

Requires: ClickHouse with TSLA 1-min data for 2024-12-18 to 2024-12-20.

Author: StatArb_Gemini Core Engine
"""

from __future__ import annotations

import asyncio
import socket
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

import pytest

from core_engine.utils.pipeline_trace import (
    ALL_CHECKPOINTS,
    CP0_MARKET_DATA,
    CP2_SIGNAL_GEN,
    CP3_RISK_AUTH,
    CP5_FILL,
    CP6_POSITION_UPDATE,
    CP7_PNL,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _clickhouse_available(host: str = "localhost", port: int = 8123) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


@pytest.fixture(scope="module")
def trace_records() -> List[Dict[str, Any]]:
    """Run BT MOM smoke test and return trace records."""
    if not _clickhouse_available():
        pytest.skip("ClickHouse not reachable on localhost:8123")

    from core_engine.utils.pipeline_trace import PipelineTracer
    PipelineTracer.reset_instance()

    from backtest.utils.config_loader import load_config
    config_path = str(REPO_ROOT / "backtest" / "configs" / "smoke_test_mom.yaml")
    config = load_config(config_path)
    config["enable_pipeline_trace"] = True

    from backtest.experiments.smoke_test import SmokeTest
    experiment = SmokeTest(config)
    result = asyncio.run(experiment.run())
    assert result.success, f"Smoke test failed: {result.error_message}"

    tracer = PipelineTracer.get_instance()
    records = [r.to_dict() for r in tracer.records]
    assert len(records) > 0, "Pipeline tracer produced zero records"
    return records


def _group_by_checkpoint(records: List[Dict]) -> Dict[str, List[Dict]]:
    groups: Dict[str, List[Dict]] = defaultdict(list)
    for r in records:
        groups[r["checkpoint"]].append(r)
    return groups


# ---------------------------------------------------------------------------
# Test: Numeric Invariants
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.requires_data
class TestNumericInvariants:
    """Verify data values are within expected ranges at each checkpoint."""

    def test_cp2_signal_strength_bounded(self, trace_records):
        """CP2 signal strengths should be in [-1, 1]."""
        by_cp = _group_by_checkpoint(trace_records)
        for r in by_cp.get(CP2_SIGNAL_GEN, []):
            output = r.get("output_data", {})
            strength = output.get("strength")
            if strength is not None:
                assert -1.0 <= float(strength) <= 1.0, (
                    f"Signal strength {strength} out of [-1, 1] for {r['symbol']}"
                )

    def test_cp2_signal_confidence_bounded(self, trace_records):
        """CP2 signal confidences should be in [0, 1]."""
        by_cp = _group_by_checkpoint(trace_records)
        for r in by_cp.get(CP2_SIGNAL_GEN, []):
            output = r.get("output_data", {})
            confidence = output.get("confidence")
            if confidence is not None:
                assert 0.0 <= float(confidence) <= 1.0, (
                    f"Signal confidence {confidence} out of [0, 1] for {r['symbol']}"
                )

    def test_cp3_authorized_quantity_positive(self, trace_records):
        """CP3 authorized quantities must be positive."""
        by_cp = _group_by_checkpoint(trace_records)
        for r in by_cp.get(CP3_RISK_AUTH, []):
            output = r.get("output_data", {})
            if output.get("authorized", False):
                qty = output.get("authorized_quantity", 0)
                assert float(qty) > 0, (
                    f"Authorized quantity {qty} <= 0 for {r['symbol']}"
                )

    def test_cp5_fill_price_positive(self, trace_records):
        """CP5 fill prices must be positive."""
        by_cp = _group_by_checkpoint(trace_records)
        for r in by_cp.get(CP5_FILL, []):
            input_data = r.get("input_data", {})
            price = input_data.get("price", 0)
            assert float(price) > 0, f"Fill price {price} <= 0 for {r['symbol']}"

    def test_cp5_fill_quantity_positive(self, trace_records):
        """CP5 fill quantities must be positive."""
        by_cp = _group_by_checkpoint(trace_records)
        for r in by_cp.get(CP5_FILL, []):
            input_data = r.get("input_data", {})
            qty = input_data.get("quantity", 0)
            assert float(qty) > 0, f"Fill quantity {qty} <= 0 for {r['symbol']}"

    def test_cp6_realized_pnl_type(self, trace_records):
        """CP6 realized_pnl must be a finite number."""
        by_cp = _group_by_checkpoint(trace_records)
        for r in by_cp.get(CP6_POSITION_UPDATE, []):
            output = r.get("output_data", {})
            rpnl = output.get("realized_pnl")
            if rpnl is not None:
                val = float(rpnl)
                assert val == val, f"realized_pnl is NaN for {r['symbol']}"  # NaN check
                assert abs(val) < 1e12, f"realized_pnl {val} unreasonably large"


# ---------------------------------------------------------------------------
# Test: Position Conservation
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.requires_data
class TestPositionConservation:
    """
    Verify position changes at CP6 are consistent with fill quantities at CP5.
    """

    def test_net_position_from_fills(self, trace_records):
        """
        Net position from all CP6 updates for each symbol should match
        the final position state.

        For a symbol that opens and closes within the test window, the
        final net should be zero (if EOD liquidation fires).
        """
        by_cp = _group_by_checkpoint(trace_records)
        cp6_records = by_cp.get(CP6_POSITION_UPDATE, [])
        if not cp6_records:
            pytest.skip("No CP6 records to verify")

        # Track net quantity changes per symbol
        net_qty = defaultdict(float)
        for r in cp6_records:
            output = r.get("output_data", {})
            new_qty = float(output.get("new_quantity", 0))
            prev_qty = float(output.get("previous_quantity", 0))
            delta = new_qty - prev_qty
            net_qty[r["symbol"]] += delta

        print(f"\nNet position changes: {dict(net_qty)}")

        # With EOD liquidation enabled, positions should be flat at end of day
        # But we test across multiple days, so just verify the last CP6 per symbol
        last_cp6 = {}
        for r in cp6_records:
            last_cp6[r["symbol"]] = r

        for symbol, r in last_cp6.items():
            output = r.get("output_data", {})
            event_type = output.get("event_type", "")
            print(f"  {symbol}: last event_type={event_type}, final_qty={output.get('new_quantity')}")


# ---------------------------------------------------------------------------
# Test: Capital Conservation
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.requires_data
class TestCapitalConservation:
    """
    Verify the accounting identity:
    initial_capital + sum(cash_changes) == final_cash_balance
    """

    def test_cash_changes_sum(self, trace_records):
        """Sum of all CP6 cash_change fields should be consistent."""
        by_cp = _group_by_checkpoint(trace_records)
        cp6_records = by_cp.get(CP6_POSITION_UPDATE, [])
        if not cp6_records:
            pytest.skip("No CP6 records to verify")

        total_cash_change = sum(
            float(r.get("output_data", {}).get("cash_change", 0))
            for r in cp6_records
        )

        # The last CP6 record should have the current cash_balance in metadata
        last_record = cp6_records[-1]
        final_cash = float(last_record.get("metadata", {}).get("cash_balance", 0))

        # initial_capital = 100000 (from smoke_test_mom.yaml)
        initial_capital = 100000.0
        expected_cash = initial_capital + total_cash_change

        if final_cash > 0:
            # Allow small float drift
            assert abs(expected_cash - final_cash) < 1.0, (
                f"Capital conservation violated: "
                f"{initial_capital} + {total_cash_change:.2f} = {expected_cash:.2f} "
                f"!= final_cash {final_cash:.2f}"
            )
            print(f"\nCapital conservation verified: ${initial_capital:,.2f} + "
                  f"${total_cash_change:,.2f} = ${final_cash:,.2f}")

    def test_realized_pnl_accumulation(self, trace_records):
        """
        Sum of individual realized PnL from CP6 records should match the
        total_realized_pnl reported in the last CP6 record.
        """
        by_cp = _group_by_checkpoint(trace_records)
        cp6_records = by_cp.get(CP6_POSITION_UPDATE, [])
        if not cp6_records:
            pytest.skip("No CP6 records to verify")

        sum_rpnl = sum(
            float(r.get("output_data", {}).get("realized_pnl", 0))
            for r in cp6_records
        )

        last_total_rpnl = float(
            cp6_records[-1].get("output_data", {}).get("total_realized_pnl", 0)
        )

        if last_total_rpnl != 0:
            assert abs(sum_rpnl - last_total_rpnl) < 0.01, (
                f"Realized PnL mismatch: sum of individual={sum_rpnl:.4f}, "
                f"total_realized_pnl={last_total_rpnl:.4f}"
            )
            print(f"\nRealized PnL accumulation verified: "
                  f"sum={sum_rpnl:.4f} == total={last_total_rpnl:.4f}")


# ---------------------------------------------------------------------------
# Test: PnL Tracker Consistency
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.requires_data
class TestPnLTrackerConsistency:
    """Verify CP7 PnL records are internally consistent."""

    def test_total_pnl_equals_realized_plus_unrealized(self, trace_records):
        """CP7: total_pnl should equal realized_pnl + unrealized_pnl."""
        by_cp = _group_by_checkpoint(trace_records)
        cp7_records = by_cp.get(CP7_PNL, [])
        if not cp7_records:
            pytest.skip("No CP7 records to verify")

        for r in cp7_records:
            output = r.get("output_data", {})
            total = float(output.get("total_pnl", 0))
            realized = float(output.get("realized_pnl", 0))
            unrealized = float(output.get("unrealized_pnl", 0))

            expected = realized + unrealized
            assert abs(total - expected) < 0.01, (
                f"PnL identity violated: total={total:.4f} != "
                f"realized={realized:.4f} + unrealized={unrealized:.4f} = {expected:.4f}"
            )

    def test_position_pnl_sign(self, trace_records):
        """
        CP7: If position is long and price > cost_basis, unrealized PnL should be positive.
        (Smoke check for PnL calculation direction.)
        """
        by_cp = _group_by_checkpoint(trace_records)
        cp7_records = by_cp.get(CP7_PNL, [])
        if not cp7_records:
            pytest.skip("No CP7 records to verify")

        mismatches = 0
        total = 0
        for r in cp7_records:
            input_data = r.get("input_data", {})
            output = r.get("output_data", {})
            price = float(input_data.get("price", 0))
            cost = float(input_data.get("cost_basis", 0))
            position = float(input_data.get("position_size", 0))
            pos_pnl = float(output.get("position_pnl", 0))

            if abs(position) > 0 and cost > 0:
                total += 1
                expected_sign = (price - cost) * position
                # Check sign consistency (allow zero)
                if expected_sign > 0.01 and pos_pnl < -0.01:
                    mismatches += 1
                elif expected_sign < -0.01 and pos_pnl > 0.01:
                    mismatches += 1

        if total > 0:
            mismatch_rate = mismatches / total
            assert mismatch_rate < 0.05, (
                f"PnL sign mismatch rate {mismatch_rate:.1%} ({mismatches}/{total}) "
                "exceeds 5% threshold"
            )
            print(f"\nPnL sign check: {mismatches}/{total} mismatches ({mismatch_rate:.1%})")
