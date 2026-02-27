"""
Phase 0A: Golden-Output Snapshot Regression Test
=================================================

Runs the canonical BT MOM smoke test (smoke_test_mom.yaml) and compares
the result against a deterministic golden baseline.

The backtest is seeded (seed=42) with fill_probability=1.0 and zero latency,
so identical inputs MUST produce identical outputs.  Any deviation in trade
count, trade direction/quantity, or aggregate PnL signals a regression.

Usage:
    # Normal regression check
    pytest tests/backtest/test_regression_golden.py -v

    # Re-capture golden baseline after intentional changes
    pytest tests/backtest/test_regression_golden.py -v --update-golden

Requires: ClickHouse with TSLA 1-min data for 2024-12-18 to 2024-12-20.
"""

from __future__ import annotations

import asyncio
import json
import socket
from pathlib import Path
from typing import Any, Dict, List

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_DIR = REPO_ROOT / "tests" / "backtest" / "golden"
GOLDEN_FILE = GOLDEN_DIR / "smoke_test_mom_golden.json"

# Tolerances for floating-point comparisons
PNL_ABS_TOL = 0.02          # dollars
PRICE_ABS_TOL = 0.01        # dollars
QTY_REL_TOL = 1e-6          # relative
METRIC_ABS_TOL = 0.01       # percent (for return%, drawdown%, win_rate%)
SHARPE_ABS_TOL = 0.05       # Sharpe ratio tolerance


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clickhouse_available(host: str = "localhost", port: int = 8123) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


def _run_smoke_test() -> Dict[str, Any]:
    """Run BT MOM smoke test and return ExperimentResult.to_dict()."""
    from backtest.utils.config_loader import load_config
    from backtest.experiments.smoke_test import SmokeTest

    config_path = str(REPO_ROOT / "backtest" / "configs" / "smoke_test_mom.yaml")
    config = load_config(config_path)

    experiment = SmokeTest(config)
    result = asyncio.run(experiment.run())
    assert result.success, f"Smoke test failed: {result.error_message}"
    return result.to_dict()


def _extract_trade_fingerprints(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract a deterministic trade fingerprint list from engine results."""
    engine = result.get("engine_results") or {}
    summary = engine.get("summary") or {}
    history = engine.get("execution_history") or summary.get("execution_history") or []
    if not history:
        return []

    fingerprints = []
    for t in history:
        fingerprints.append({
            "timestamp": str(t.get("timestamp", ""))[:19],
            "symbol": t.get("symbol"),
            "side": t.get("side", t.get("action")),
            "quantity": round(t.get("quantity", t.get("qty", 0)), 6),
            "fill_price": round(t.get("fill_price", t.get("price", 0)), 4),
        })

    # Sort by timestamp then side for deterministic ordering
    fingerprints.sort(key=lambda x: (x["timestamp"], x["side"]))
    return fingerprints


def _extract_metrics_fingerprint(result: Dict[str, Any]) -> Dict[str, Any]:
    """Extract key performance metrics for comparison."""
    perf = result.get("performance") or {}
    return {
        "total_return_pct": perf.get("total_return_pct", 0.0),
        "sharpe_ratio": perf.get("sharpe_ratio", 0.0),
        "max_drawdown_pct": perf.get("max_drawdown_pct", 0.0),
        "total_trades": perf.get("total_trades", 0),
        "win_rate": perf.get("win_rate", 0.0),
    }


def _extract_funnel_fingerprint(result: Dict[str, Any]) -> Dict[str, int]:
    """Extract pipeline trace funnel counts."""
    return (result.get("custom_metrics") or {}).get("trace_funnel") or {}


def _build_golden(result: Dict[str, Any]) -> Dict[str, Any]:
    """Build the golden snapshot from a result dict."""
    return {
        "_comment": "AUTO-GENERATED golden baseline. Regenerate with: pytest tests/backtest/test_regression_golden.py --update-golden",
        "trades": _extract_trade_fingerprints(result),
        "metrics": _extract_metrics_fingerprint(result),
        "funnel": _extract_funnel_fingerprint(result),
        "trade_count": len(_extract_trade_fingerprints(result)),
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def smoke_result() -> Dict[str, Any]:
    """Run the smoke test once per module and cache the result."""
    if not _clickhouse_available():
        pytest.skip("ClickHouse not reachable on localhost:8123")
    return _run_smoke_test()


@pytest.fixture(scope="module")
def golden_baseline(smoke_result, request) -> Dict[str, Any]:
    """Load or regenerate the golden baseline."""
    if request.config.getoption("--update-golden"):
        golden = _build_golden(smoke_result)
        GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
        GOLDEN_FILE.write_text(json.dumps(golden, indent=2, default=str))
        print(f"\n[GOLDEN] Baseline updated: {GOLDEN_FILE}")
        return golden

    if not GOLDEN_FILE.exists():
        pytest.fail(
            f"Golden baseline not found: {GOLDEN_FILE}\n"
            "Run with --update-golden to create it:\n"
            "  pytest tests/backtest/test_regression_golden.py --update-golden"
        )

    return json.loads(GOLDEN_FILE.read_text())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestGoldenRegression:
    """Compare live smoke test output against golden baseline."""

    def test_trade_count_matches(self, smoke_result, golden_baseline):
        """Total fill count must be identical."""
        live_trades = _extract_trade_fingerprints(smoke_result)
        golden_count = golden_baseline["trade_count"]
        assert len(live_trades) == golden_count, (
            f"Trade count changed: expected {golden_count}, got {len(live_trades)}"
        )

    def test_trade_directions_match(self, smoke_result, golden_baseline):
        """Every trade must have same timestamp + side + symbol."""
        live_trades = _extract_trade_fingerprints(smoke_result)
        golden_trades = golden_baseline["trades"]

        assert len(live_trades) == len(golden_trades), "Trade count mismatch (pre-check)"

        for i, (live, gold) in enumerate(zip(live_trades, golden_trades)):
            assert live["timestamp"] == gold["timestamp"], (
                f"Trade {i}: timestamp {live['timestamp']} != {gold['timestamp']}"
            )
            assert live["side"] == gold["side"], (
                f"Trade {i} @ {live['timestamp']}: side {live['side']} != {gold['side']}"
            )
            assert live["symbol"] == gold["symbol"], (
                f"Trade {i} @ {live['timestamp']}: symbol {live['symbol']} != {gold['symbol']}"
            )

    def test_trade_quantities_match(self, smoke_result, golden_baseline):
        """Quantities must match within relative tolerance."""
        live_trades = _extract_trade_fingerprints(smoke_result)
        golden_trades = golden_baseline["trades"]

        for i, (live, gold) in enumerate(zip(live_trades, golden_trades)):
            if gold["quantity"] == 0:
                assert live["quantity"] == 0, f"Trade {i}: qty diverged from zero"
                continue
            rel_err = abs(live["quantity"] - gold["quantity"]) / abs(gold["quantity"])
            assert rel_err < QTY_REL_TOL, (
                f"Trade {i} @ {live['timestamp']}: qty {live['quantity']} vs "
                f"{gold['quantity']} (rel_err={rel_err:.2e})"
            )

    def test_fill_prices_match(self, smoke_result, golden_baseline):
        """Fill prices must match within absolute tolerance."""
        live_trades = _extract_trade_fingerprints(smoke_result)
        golden_trades = golden_baseline["trades"]

        for i, (live, gold) in enumerate(zip(live_trades, golden_trades)):
            diff = abs(live["fill_price"] - gold["fill_price"])
            assert diff < PRICE_ABS_TOL, (
                f"Trade {i} @ {live['timestamp']}: fill_price {live['fill_price']} vs "
                f"{gold['fill_price']} (diff=${diff:.4f})"
            )

    def test_total_return_matches(self, smoke_result, golden_baseline):
        """Total return % must match within tolerance."""
        live = _extract_metrics_fingerprint(smoke_result)
        gold = golden_baseline["metrics"]
        diff = abs(live["total_return_pct"] - gold["total_return_pct"])
        assert diff < METRIC_ABS_TOL, (
            f"Total return diverged: {live['total_return_pct']:.4f}% vs "
            f"{gold['total_return_pct']:.4f}% (diff={diff:.4f}%)"
        )

    def test_sharpe_ratio_matches(self, smoke_result, golden_baseline):
        """Sharpe ratio must match within tolerance."""
        live = _extract_metrics_fingerprint(smoke_result)
        gold = golden_baseline["metrics"]
        diff = abs(live["sharpe_ratio"] - gold["sharpe_ratio"])
        assert diff < SHARPE_ABS_TOL, (
            f"Sharpe diverged: {live['sharpe_ratio']:.4f} vs "
            f"{gold['sharpe_ratio']:.4f} (diff={diff:.4f})"
        )

    def test_max_drawdown_matches(self, smoke_result, golden_baseline):
        """Max drawdown % must match within tolerance."""
        live = _extract_metrics_fingerprint(smoke_result)
        gold = golden_baseline["metrics"]
        diff = abs(live["max_drawdown_pct"] - gold["max_drawdown_pct"])
        assert diff < METRIC_ABS_TOL, (
            f"Max drawdown diverged: {live['max_drawdown_pct']:.4f}% vs "
            f"{gold['max_drawdown_pct']:.4f}% (diff={diff:.4f}%)"
        )

    def test_win_rate_matches(self, smoke_result, golden_baseline):
        """Win rate must match within tolerance."""
        live = _extract_metrics_fingerprint(smoke_result)
        gold = golden_baseline["metrics"]
        diff = abs(live["win_rate"] - gold["win_rate"])
        assert diff < METRIC_ABS_TOL, (
            f"Win rate diverged: {live['win_rate']:.2f}% vs "
            f"{gold['win_rate']:.2f}% (diff={diff:.2f}%)"
        )

    def test_pipeline_funnel_matches(self, smoke_result, golden_baseline):
        """Pipeline trace funnel checkpoint counts must match exactly."""
        live_funnel = _extract_funnel_fingerprint(smoke_result)
        gold_funnel = golden_baseline.get("funnel", {})

        if not gold_funnel:
            pytest.skip("Golden baseline has no funnel data")

        for cp in sorted(set(list(live_funnel.keys()) + list(gold_funnel.keys()))):
            live_count = live_funnel.get(cp, 0)
            gold_count = gold_funnel.get(cp, 0)
            assert live_count == gold_count, (
                f"Funnel {cp}: count {live_count} != golden {gold_count}"
            )
