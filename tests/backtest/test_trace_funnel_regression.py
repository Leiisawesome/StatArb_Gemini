"""
Phase 0C: Pipeline Trace Funnel Regression Test
================================================

Verifies that the pipeline trace funnel checkpoint counts match expected
values for each canonical smoke test suite.

This is a lightweight structural integrity check: if a code change alters
which signals get generated, authorized, or filled, the funnel shape changes
and this test catches it.

Unlike the full golden regression test (Phase 0A), this test only compares
funnel counts — it runs faster and provides a quick "did the pipeline break?"
signal.

Usage:
    pytest tests/backtest/test_trace_funnel_regression.py -v

    # Re-capture baselines
    pytest tests/backtest/test_trace_funnel_regression.py -v --update-golden

Requires: ClickHouse with TSLA 1-min data for 2024-12-18 to 2024-12-20.
"""

from __future__ import annotations

import asyncio
import json
import socket
from pathlib import Path
from typing import Any, Dict

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_DIR = REPO_ROOT / "tests" / "backtest" / "golden"
FUNNEL_GOLDEN_FILE = GOLDEN_DIR / "smoke_test_mom_funnel.json"


def _clickhouse_available(host: str = "localhost", port: int = 8123) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def funnel_result() -> Dict[str, Any]:
    """Run smoke test and extract funnel + summary metrics."""
    if not _clickhouse_available():
        pytest.skip("ClickHouse not reachable on localhost:8123")

    from core_engine.utils.pipeline_trace import PipelineTracer
    PipelineTracer.reset_instance()

    from backtest.utils.config_loader import load_config
    from backtest.experiments.smoke_test import SmokeTest

    config_path = str(REPO_ROOT / "backtest" / "configs" / "smoke_test_mom.yaml")
    config = load_config(config_path)
    config["enable_pipeline_trace"] = True

    experiment = SmokeTest(config)
    result = asyncio.run(experiment.run())
    assert result.success, f"Smoke test failed: {result.error_message}"

    # Collect funnel from tracer
    tracer = PipelineTracer.get_instance()
    from collections import Counter
    funnel = dict(Counter(r.checkpoint for r in tracer.records))

    # Collect authorized vs rejected at CP3
    cp3_records = [r for r in tracer.records if r.checkpoint == "CP3"]
    authorized = sum(1 for r in cp3_records if r.metadata.get("authorized", False))
    rejected = sum(1 for r in cp3_records if not r.metadata.get("authorized", True))

    return {
        "funnel": funnel,
        "authorized": authorized,
        "rejected": rejected,
        "total_trades": result.total_trades,
        "bars_processed": result.custom_metrics.get("bars_processed", 0),
    }


@pytest.fixture(scope="module")
def funnel_golden(funnel_result, request) -> Dict[str, Any]:
    """Load or regenerate the funnel golden baseline."""
    if request.config.getoption("--update-golden"):
        GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
        FUNNEL_GOLDEN_FILE.write_text(json.dumps(funnel_result, indent=2))
        print(f"\n[GOLDEN] Funnel baseline updated: {FUNNEL_GOLDEN_FILE}")
        return funnel_result

    if not FUNNEL_GOLDEN_FILE.exists():
        pytest.fail(
            f"Funnel golden baseline not found: {FUNNEL_GOLDEN_FILE}\n"
            "Run with --update-golden to create it."
        )

    return json.loads(FUNNEL_GOLDEN_FILE.read_text())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestFunnelRegression:
    """Pipeline funnel shape must match golden baseline."""

    def test_checkpoint_counts_match(self, funnel_result, funnel_golden):
        """Every checkpoint count must match exactly."""
        live = funnel_result["funnel"]
        gold = funnel_golden["funnel"]

        all_cps = sorted(set(list(live.keys()) + list(gold.keys())))
        mismatches = []
        for cp in all_cps:
            lv = live.get(cp, 0)
            gv = gold.get(cp, 0)
            if lv != gv:
                mismatches.append(f"  {cp}: {lv} (live) != {gv} (golden)")

        assert not mismatches, (
            "Funnel checkpoint count regression:\n" + "\n".join(mismatches)
        )

    def test_authorized_count_matches(self, funnel_result, funnel_golden):
        """Number of authorized trades at CP3 must match."""
        assert funnel_result["authorized"] == funnel_golden["authorized"], (
            f"Authorized count: {funnel_result['authorized']} != {funnel_golden['authorized']}"
        )

    def test_rejected_count_matches(self, funnel_result, funnel_golden):
        """Number of rejected trades at CP3 must match."""
        assert funnel_result["rejected"] == funnel_golden["rejected"], (
            f"Rejected count: {funnel_result['rejected']} != {funnel_golden['rejected']}"
        )

    def test_trade_count_matches(self, funnel_result, funnel_golden):
        """Total round-trip trade count must match."""
        assert funnel_result["total_trades"] == funnel_golden["total_trades"], (
            f"Trade count: {funnel_result['total_trades']} != {funnel_golden['total_trades']}"
        )

    def test_bars_processed_matches(self, funnel_result, funnel_golden):
        """Bars processed count must match (data pipeline integrity)."""
        assert funnel_result["bars_processed"] == funnel_golden["bars_processed"], (
            f"Bars processed: {funnel_result['bars_processed']} != {funnel_golden['bars_processed']}"
        )


@pytest.mark.integration
class TestFunnelInvariants:
    """Structural invariants that must always hold, regardless of golden baseline."""

    def test_monotonic_funnel(self, funnel_result):
        """CP4 <= CP3_authorized (can't execute more than authorized)."""
        funnel = funnel_result["funnel"]
        cp3_auth = funnel_result["authorized"]
        cp4 = funnel.get("CP4", 0)
        assert cp4 <= cp3_auth or cp3_auth == 0, (
            f"CP4 ({cp4}) > authorized CP3 ({cp3_auth}) — more executions than authorizations"
        )

    def test_cp5_equals_cp4(self, funnel_result):
        """In deterministic mode (fill_probability=1.0), CP5 == CP4."""
        funnel = funnel_result["funnel"]
        cp4 = funnel.get("CP4", 0)
        cp5 = funnel.get("CP5", 0)
        assert cp5 == cp4, (
            f"CP5 ({cp5}) != CP4 ({cp4}) — fill gap in deterministic mode"
        )

    def test_cp6_ge_cp5(self, funnel_result):
        """Every fill (CP5) should produce a position update (CP6)."""
        funnel = funnel_result["funnel"]
        cp5 = funnel.get("CP5", 0)
        cp6 = funnel.get("CP6", 0)
        assert cp6 >= cp5, (
            f"CP6 ({cp6}) < CP5 ({cp5}) — missing position updates"
        )

    def test_cp7_ge_cp5(self, funnel_result):
        """Every fill should produce a PnL record."""
        funnel = funnel_result["funnel"]
        cp5 = funnel.get("CP5", 0)
        cp7 = funnel.get("CP7", 0)
        assert cp7 >= cp5, (
            f"CP7 ({cp7}) < CP5 ({cp5}) — missing PnL records"
        )

    def test_nonzero_signals(self, funnel_result):
        """At least some signals must be generated."""
        cp2 = funnel_result["funnel"].get("CP2", 0)
        assert cp2 > 0, "Zero signals generated — pipeline is dead"
