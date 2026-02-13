"""
Intraday Session Isolation Regression Test
============================================

Validates the fundamental intraday additivity invariant:

    Multi-day PnL == Sum of individual per-day PnLs

When ``intraday_session_isolation`` is enabled, the backtest engine resets
all runtime state (price history, regime EWMA, pending signals) at each
trading-day boundary and replays prior-day bars for warmup.  This ensures
each day is independent — trades on Day N are identical regardless of
whether the backtest started on Day 1 or Day N.

Test Strategy:
    1. Run multi-day backtest (Dec 18–20) with session isolation ON
    2. Run each day individually (Dec 18, Dec 19, Dec 20) with same config
    3. Assert per-day trade lists match between multi-day and individual runs
    4. Assert total PnL of individual runs sums to multi-day PnL

Requires: ClickHouse with TSLA 1-min data for 2024-12-16 to 2024-12-20.

Usage:
    pytest tests/backtest/test_intraday_session_isolation.py -v -s
"""

from __future__ import annotations

import asyncio
import copy
import socket
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]

# Tolerances
PNL_ABS_TOL = 0.10         # dollars — allows for tiny float rounding
TRADE_COUNT_TOL = 0         # must match exactly
PRICE_ABS_TOL = 0.02        # dollars


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clickhouse_available(host: str = "localhost", port: int = 8123) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


def _load_base_config() -> Dict[str, Any]:
    """Load the canonical MOM smoke test config with session isolation ON."""
    from backtest.utils.config_loader import load_config

    config_path = str(REPO_ROOT / "backtest" / "configs" / "smoke_test_mom.yaml")
    config = load_config(config_path)

    # Force session isolation ON (it should already be in the YAML,
    # but be explicit for the test)
    config["intraday_session_isolation"] = True
    return config


def _run_backtest(config: Dict[str, Any]) -> Dict[str, Any]:
    """Run a single backtest and return (result_dict, experiment_result)."""
    from backtest.experiments.smoke_test import SmokeTest

    experiment = SmokeTest(config)
    result = asyncio.run(experiment.run())
    assert result.success, f"Backtest failed: {result.error_message}"
    return {
        "total_return_pct": result.total_return_pct,
        "total_trades": result.total_trades,
        "engine_results": result.engine_results,
    }


def _extract_trades(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract trade list from engine results."""
    engine = result.get("engine_results") or {}
    history = engine.get("execution_history") or []
    if not history:
        summary = engine.get("summary") or {}
        history = summary.get("execution_history") or []
    return history or []


def _compute_total_pnl(trades: List[Dict[str, Any]]) -> float:
    """Sum realized PnL from trade list."""
    total = 0.0
    for t in trades:
        pnl = t.get("realized_pnl") or t.get("pnl") or 0.0
        total += float(pnl)
    return total


def _partition_trades_by_date(trades: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group trades by calendar date string (YYYY-MM-DD)."""
    import pandas as pd
    by_date: Dict[str, List[Dict[str, Any]]] = {}
    for t in trades:
        ts = t.get("timestamp") or t.get("fill_timestamp") or t.get("signal_timestamp")
        if ts is None:
            continue
        try:
            d = pd.Timestamp(ts).strftime("%Y-%m-%d")
        except Exception:
            continue
        by_date.setdefault(d, []).append(t)
    return by_date


def _get_trading_dates(start: str, end: str) -> List[str]:
    """Return trading dates between start and end (inclusive)."""
    import pandas as pd
    dates = pd.bdate_range(start, end)
    return [d.strftime("%Y-%m-%d") for d in dates]


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not _clickhouse_available(),
    reason="ClickHouse not available",
)
class TestIntradaySessionIsolation:
    """Validate intraday additivity: multi-day == sum of per-day."""

    def test_pnl_additivity(self):
        """
        Core invariant: running Dec 18–20 as one backtest produces the same
        per-day trades as running each day individually.
        """
        base_config = _load_base_config()

        # --- Run multi-day backtest (Dec 18–20) ---
        multi_config = copy.deepcopy(base_config)
        multi_config["start_date"] = "2024-12-18"
        multi_config["end_date"] = "2024-12-20"
        multi_config["experiment_name"] = "ISO_MultiDay"

        print("\n=== Running multi-day backtest (Dec 18-20) ===")
        multi_result = _run_backtest(multi_config)
        multi_trades = _extract_trades(multi_result)
        multi_by_date = _partition_trades_by_date(multi_trades)
        multi_pnl = _compute_total_pnl(multi_trades)

        print(f"   Multi-day: {len(multi_trades)} trades, PnL={multi_pnl:.2f}")
        for d, trades in sorted(multi_by_date.items()):
            day_pnl = _compute_total_pnl(trades)
            print(f"     {d}: {len(trades)} trades, PnL={day_pnl:.2f}")

        # --- Run each day individually ---
        trading_dates = _get_trading_dates("2024-12-18", "2024-12-20")
        individual_total_pnl = 0.0
        individual_total_trades = 0
        individual_by_date: Dict[str, List[Dict[str, Any]]] = {}

        for day_str in trading_dates:
            day_config = copy.deepcopy(base_config)
            day_config["start_date"] = day_str
            day_config["end_date"] = day_str
            day_config["experiment_name"] = f"ISO_Day_{day_str}"

            print(f"\n=== Running individual day: {day_str} ===")
            day_result = _run_backtest(day_config)
            day_trades = _extract_trades(day_result)
            day_pnl = _compute_total_pnl(day_trades)

            individual_by_date[day_str] = day_trades
            individual_total_pnl += day_pnl
            individual_total_trades += len(day_trades)

            print(f"   {day_str}: {len(day_trades)} trades, PnL={day_pnl:.2f}")

        # --- Assert PnL additivity ---
        print(f"\n=== Additivity Check ===")
        print(f"   Multi-day total PnL:     {multi_pnl:+.2f}")
        print(f"   Sum of individual PnLs:  {individual_total_pnl:+.2f}")
        print(f"   Difference:              {abs(multi_pnl - individual_total_pnl):.4f}")

        assert abs(multi_pnl - individual_total_pnl) < PNL_ABS_TOL, (
            f"PnL additivity violated: multi-day={multi_pnl:.4f}, "
            f"sum-of-days={individual_total_pnl:.4f}, "
            f"diff={abs(multi_pnl - individual_total_pnl):.4f}"
        )

        # --- Assert per-day trade counts match ---
        for day_str in trading_dates:
            multi_day_trades = multi_by_date.get(day_str, [])
            indiv_day_trades = individual_by_date.get(day_str, [])

            # Trade count match
            assert len(multi_day_trades) == len(indiv_day_trades), (
                f"Trade count mismatch on {day_str}: "
                f"multi-day={len(multi_day_trades)}, "
                f"individual={len(indiv_day_trades)}"
            )

            # Per-day PnL match
            multi_day_pnl = _compute_total_pnl(multi_day_trades)
            indiv_day_pnl = _compute_total_pnl(indiv_day_trades)
            assert abs(multi_day_pnl - indiv_day_pnl) < PNL_ABS_TOL, (
                f"Per-day PnL mismatch on {day_str}: "
                f"multi-day={multi_day_pnl:.4f}, "
                f"individual={indiv_day_pnl:.4f}"
            )

        print("\n✅ Intraday additivity invariant PASSED")

    def test_session_isolation_determinism(self):
        """
        Running the same multi-day backtest twice with session isolation
        produces identical results (deterministic seed=42).
        """
        base_config = _load_base_config()
        base_config["start_date"] = "2024-12-18"
        base_config["end_date"] = "2024-12-20"
        base_config["experiment_name"] = "ISO_Determinism"

        print("\n=== Run 1 ===")
        result_1 = _run_backtest(copy.deepcopy(base_config))
        trades_1 = _extract_trades(result_1)
        pnl_1 = _compute_total_pnl(trades_1)

        print(f"\n=== Run 2 ===")
        result_2 = _run_backtest(copy.deepcopy(base_config))
        trades_2 = _extract_trades(result_2)
        pnl_2 = _compute_total_pnl(trades_2)

        assert len(trades_1) == len(trades_2), (
            f"Trade count not deterministic: run1={len(trades_1)}, run2={len(trades_2)}"
        )
        assert abs(pnl_1 - pnl_2) < PNL_ABS_TOL, (
            f"PnL not deterministic: run1={pnl_1:.4f}, run2={pnl_2:.4f}"
        )

        print(f"\n✅ Determinism check PASSED (PnL={pnl_1:.2f} on both runs)")
