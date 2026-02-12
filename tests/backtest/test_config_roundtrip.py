"""
Phase 0B: Config Round-Trip Verification Test
==============================================

Verifies that the YAML config loading pipeline preserves all fields:

    smoke_test_mom.yaml (papertest schema)
        -> load_with_includes()
        -> _papertest_to_backtest_config()
        -> flat dict with expected keys/values

This catches silent field-dropping bugs in the schema adapter.

Usage:
    pytest tests/backtest/test_config_roundtrip.py -v
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def loaded_config_mom() -> Dict[str, Any]:
    """Load the MOM smoke test config through the full pipeline."""
    from backtest.utils.config_loader import load_config

    config_path = str(REPO_ROOT / "backtest" / "configs" / "smoke_test_mom.yaml")
    return load_config(config_path)


@pytest.fixture(scope="module")
def raw_yaml_mom() -> Dict[str, Any]:
    """Load the raw canonical YAML for comparison."""
    from core_engine.config.yaml_loader import load_with_includes

    yaml_path = REPO_ROOT / "core_engine" / "config" / "catalog" / "suites" / "smoke_test_mom.yaml"
    return load_with_includes(yaml_path)


# ---------------------------------------------------------------------------
# Tests: Data Section
# ---------------------------------------------------------------------------

class TestDataFieldsPreserved:
    """Verify papertest.data fields map correctly."""

    def test_symbols(self, loaded_config_mom, raw_yaml_mom):
        expected = raw_yaml_mom["papertest"]["data"]["symbols"]
        assert loaded_config_mom["symbols"] == expected

    def test_start_date(self, loaded_config_mom, raw_yaml_mom):
        expected = raw_yaml_mom["papertest"]["data"]["start_date"]
        assert loaded_config_mom["start_date"] == expected

    def test_end_date(self, loaded_config_mom, raw_yaml_mom):
        expected = raw_yaml_mom["papertest"]["data"]["end_date"]
        assert loaded_config_mom["end_date"] == expected

    def test_interval(self, loaded_config_mom, raw_yaml_mom):
        expected = raw_yaml_mom["papertest"]["data"]["interval"]
        assert loaded_config_mom["interval"] == expected


# ---------------------------------------------------------------------------
# Tests: Buffer Section
# ---------------------------------------------------------------------------

class TestBufferFieldsPreserved:
    """Verify papertest.buffers fields map correctly."""

    def test_warmup_bars(self, loaded_config_mom, raw_yaml_mom):
        expected = raw_yaml_mom["papertest"]["buffers"]["warmup_required"]
        assert loaded_config_mom["warmup_bars"] == expected


# ---------------------------------------------------------------------------
# Tests: Execution Section
# ---------------------------------------------------------------------------

class TestExecutionFieldsPreserved:
    """Verify papertest.execution fields map correctly."""

    def test_initial_capital(self, loaded_config_mom, raw_yaml_mom):
        expected = raw_yaml_mom["papertest"]["execution"]["initial_cash"]
        assert loaded_config_mom["initial_capital"] == expected

    def test_execution_seed(self, loaded_config_mom, raw_yaml_mom):
        expected = raw_yaml_mom["papertest"]["execution"]["seed"]
        assert loaded_config_mom["execution_seed"] == expected

    def test_commission_per_trade(self, loaded_config_mom, raw_yaml_mom):
        expected = raw_yaml_mom["papertest"]["execution"]["commission_per_share"]
        assert loaded_config_mom["commission_per_trade"] == expected

    def test_min_commission(self, loaded_config_mom, raw_yaml_mom):
        expected = raw_yaml_mom["papertest"]["execution"]["min_commission"]
        assert loaded_config_mom["min_commission"] == expected

    def test_slippage_bps(self, loaded_config_mom, raw_yaml_mom):
        expected = raw_yaml_mom["papertest"]["execution"]["slippage_bps_max"]
        assert loaded_config_mom["base_slippage_bps"] == expected

    def test_impact_coefficient(self, loaded_config_mom, raw_yaml_mom):
        expected = raw_yaml_mom["papertest"]["execution"]["impact_coefficient"]
        assert loaded_config_mom["linear_coefficient"] == expected


# ---------------------------------------------------------------------------
# Tests: Risk Section
# ---------------------------------------------------------------------------

class TestRiskFieldsPreserved:
    """Verify papertest.risk fields map correctly."""

    def test_allow_shorts(self, loaded_config_mom, raw_yaml_mom):
        expected = raw_yaml_mom["papertest"]["risk"]["allow_shorts"]
        assert loaded_config_mom["allow_shorts"] == expected

    def test_min_signal_confidence(self, loaded_config_mom, raw_yaml_mom):
        expected = raw_yaml_mom["papertest"]["risk"]["min_signal_confidence"]
        assert loaded_config_mom["min_signal_confidence"] == expected

    def test_max_position_size(self, loaded_config_mom, raw_yaml_mom):
        expected = raw_yaml_mom["papertest"]["risk"]["max_position_size"]
        assert loaded_config_mom["max_position_size"] == expected

    def test_max_positions(self, loaded_config_mom, raw_yaml_mom):
        expected = raw_yaml_mom["papertest"]["risk"]["max_positions"]
        assert loaded_config_mom["max_positions"] == expected

    def test_daily_risk_budget(self, loaded_config_mom, raw_yaml_mom):
        expected = raw_yaml_mom["papertest"]["risk"]["daily_risk_budget_pct"]
        assert loaded_config_mom["max_daily_var"] == expected

    def test_per_trade_risk(self, loaded_config_mom, raw_yaml_mom):
        expected = raw_yaml_mom["papertest"]["risk"]["per_trade_risk_pct"]
        assert loaded_config_mom["per_trade_risk_pct"] == expected


# ---------------------------------------------------------------------------
# Tests: Strategy Section
# ---------------------------------------------------------------------------

class TestStrategyFieldsPreserved:
    """Verify papertest.strategies list is passed through."""

    def test_strategies_is_list(self, loaded_config_mom):
        assert isinstance(loaded_config_mom["strategies"], list)

    def test_strategies_not_empty(self, loaded_config_mom):
        assert len(loaded_config_mom["strategies"]) > 0

    def test_first_strategy_type(self, loaded_config_mom, raw_yaml_mom):
        expected_type = raw_yaml_mom["papertest"]["strategies"][0]["type"]
        actual_type = loaded_config_mom["strategies"][0].get("type")
        assert actual_type == expected_type

    def test_first_strategy_name(self, loaded_config_mom, raw_yaml_mom):
        expected_name = raw_yaml_mom["papertest"]["strategies"][0]["name"]
        actual_name = loaded_config_mom["strategies"][0].get("name")
        assert actual_name == expected_name

    def test_strategy_parameters_preserved(self, loaded_config_mom, raw_yaml_mom):
        """Key strategy parameters should be passed through intact."""
        raw_params = raw_yaml_mom["papertest"]["strategies"][0].get("parameters", {})
        loaded_params = loaded_config_mom["strategies"][0].get("parameters", {})

        # Check a representative set of parameters
        for key in ["short_period", "medium_period", "long_period",
                     "enable_ads_gates", "tau_0", "erar_gamma",
                     "enable_eod_liquidation", "eod_close_time"]:
            if key in raw_params:
                assert key in loaded_params, f"Strategy parameter '{key}' was dropped"
                assert loaded_params[key] == raw_params[key], (
                    f"Strategy parameter '{key}': {loaded_params[key]} != {raw_params[key]}"
                )


# ---------------------------------------------------------------------------
# Tests: Pipeline Trace Section
# ---------------------------------------------------------------------------

class TestTraceFieldsPreserved:
    """Verify papertest.trace fields map correctly."""

    def test_enable_pipeline_trace(self, loaded_config_mom, raw_yaml_mom):
        expected = raw_yaml_mom["papertest"]["trace"]["enable_pipeline_trace"]
        assert loaded_config_mom.get("enable_pipeline_trace") == expected


# ---------------------------------------------------------------------------
# Tests: No Silent Field Drops
# ---------------------------------------------------------------------------

class TestNoSilentFieldDrops:
    """Verify that critical fields are not None or missing."""

    @pytest.mark.parametrize("field", [
        "symbols", "start_date", "end_date", "interval",
        "initial_capital", "warmup_bars",
        "allow_shorts", "min_signal_confidence",
        "max_position_size", "strategies",
    ])
    def test_critical_field_not_none(self, loaded_config_mom, field):
        assert field in loaded_config_mom, f"Field '{field}' missing from loaded config"
        assert loaded_config_mom[field] is not None, f"Field '{field}' is None"
