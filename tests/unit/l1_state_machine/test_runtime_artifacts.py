from __future__ import annotations

from dataclasses import asdict
import pytest

from l1_microstructure.artifacts import ArtifactBundleLoader, ArtifactMetadata, LocalArtifactStore
from l1_microstructure.calibration import (
    CalibrationDataset,
    EmpiricalExecutionCalibrator,
    EmpiricalRegimeCalibrator,
    ExecutionCalibrationDataset,
    QuantileStateCalibrator,
)
from l1_microstructure.events import QuoteEvent
from l1_microstructure.features import FeatureEngine
from l1_microstructure.live import RunnerConfig, SimulatorPaperTradingRunner
from l1_microstructure.training import EmpiricalTransitionTrainer
import pandas as pd


def test_artifact_bundle_loader_reconstructs_runtime_bundle(tmp_path) -> None:
    store = LocalArtifactStore(tmp_path)
    state_payload = {
        "symbol": "AAPL",
        "spread_quantiles": (50.0, 150.0),
        "volatility_quantiles": (0.0005, 0.0015),
        "flicker_baseline": 7.0,
        "quote_pressure_scale": 0.5,
        "regime_surfaces": {
            "execution_flow": {
                "spread_quantiles": (40.0, 80.0),
                "volatility_quantiles": (0.0004, 0.0010),
                "flicker_baseline": 6.0,
                "quote_pressure_scale": 0.25,
                "sample_count": 8,
            }
        },
        "metadata": {"source": "unit-test"},
    }
    regime_payload = {
        "symbol": "AAPL",
        "regime_priors": {"calm_liquidity": 0.05, "execution_flow": 0.80, "liquidity_shock": 0.05, "competitive_liquidity": 0.10},
        "holding_time_seconds": {"calm_liquidity": 12.0, "execution_flow": 9.0, "liquidity_shock": 2.0, "competitive_liquidity": 4.0},
        "metadata": {"source": "unit-test"},
    }
    transition_payload = {
        "model_id": "transition-1",
        "created_at": "2026-03-09T00:00:00+00:00",
        "edge_count": 1,
        "sample_count": 2,
        "edges": {
            "edge-1": {
                "from_state": "tight|neutral|neutral|stable|quiet",
                "to_state": "wide|buy_heavy|buy_heavy|chaotic|stressed",
                "regime": "execution_flow",
                "count": 2,
                "holding_times_ns": [1_000_000_000, 2_000_000_000],
                "drift_samples_bps": [1.0, 2.0],
            }
        },
    }
    execution_payload = {
        "symbol": "AAPL",
        "fill_probability_intercept": 0.9,
        "alignment_weight": 2.4,
        "spread_penalty": 0.08,
        "slippage_intercept_bps": 0.6,
        "spread_slippage_weight": 0.7,
        "adverse_selection_weight": 0.5,
        "regime_fill_multipliers": {"execution_flow": 1.05, "liquidity_shock": 0.7},
        "regime_slippage_multipliers": {"execution_flow": 1.1, "liquidity_shock": 1.8},
        "metadata": {"source": "unit-test"},
    }
    store.save(ArtifactMetadata("state-1", "state_calibration", "v1", "2026-03-09T00:00:00+00:00"), state_payload)
    store.save(ArtifactMetadata("regime-1", "regime_calibration", "v1", "2026-03-09T00:00:00+00:00"), regime_payload)
    store.save(ArtifactMetadata("execution-1", "execution_calibration", "v1", "2026-03-09T00:00:00+00:00"), execution_payload)
    store.save(ArtifactMetadata("transition-1", "transition_model", "v1", "2026-03-09T00:00:00+00:00"), transition_payload)

    bundle = ArtifactBundleLoader(store).load_runtime_bundle(
        state_calibration_id="state-1",
        regime_calibration_id="regime-1",
        execution_calibration_id="execution-1",
        transition_model_id="transition-1",
    )

    assert bundle.state_calibration is not None
    assert bundle.state_calibration.flicker_baseline == 7.0
    assert bundle.state_calibration.regime_surfaces["execution_flow"].sample_count == 8
    assert bundle.regime_calibration is not None
    assert bundle.regime_calibration.holding_time_seconds["execution_flow"] == 9.0
    assert bundle.execution_calibration is not None
    assert bundle.execution_calibration.regime_slippage_multipliers["liquidity_shock"] == 1.8
    assert bundle.transition_model is not None
    assert bundle.artifact_ids["transition_model"] == "transition-1"


def test_simulator_runner_consumes_runtime_artifacts(tmp_path) -> None:
    calibration_frame = pd.DataFrame(
        [
            {
                "symbol": "AAPL",
                "spread_norm": 60.0,
                "realized_volatility": 0.0004,
                "flicker_intensity": 6.5,
                "quote_pressure": 0.2,
                "dominant_regime": "execution_flow",
                "regime_confidence": 0.8,
                "expected_holding_time_ns": 9_000_000_000,
            },
            {
                "symbol": "AAPL",
                "spread_norm": 200.0,
                "realized_volatility": 0.0020,
                "flicker_intensity": 7.5,
                "quote_pressure": 0.5,
                "dominant_regime": "execution_flow",
                "regime_confidence": 0.7,
                "expected_holding_time_ns": 9_000_000_000,
            },
        ]
    )
    state_artifact = QuantileStateCalibrator().fit(CalibrationDataset(symbol="AAPL", features=calibration_frame))
    regime_artifact = EmpiricalRegimeCalibrator().fit(CalibrationDataset(symbol="AAPL", features=calibration_frame))

    transition_panel = pd.DataFrame(
        [
            {
                "symbol": "AAPL",
                "from_state": "tight|neutral|neutral|stable|quiet",
                "to_state": "wide|buy_heavy|buy_heavy|chaotic|stressed",
                "regime": "execution_flow",
                "holding_time_ns": 1_000_000_000,
                "realized_drift_bps": 2.0,
            },
            {
                "symbol": "AAPL",
                "from_state": "tight|neutral|neutral|stable|quiet",
                "to_state": "wide|buy_heavy|buy_heavy|chaotic|stressed",
                "regime": "execution_flow",
                "holding_time_ns": 2_000_000_000,
                "realized_drift_bps": 3.0,
            },
        ]
    )
    trainer = EmpiricalTransitionTrainer()
    transition_model = trainer.last_payload
    if transition_model is None:
        transition_model = trainer._build_payload(trainer.samples_from_frame(transition_panel), model_id="transition-runtime", created_at="2026-03-09T00:00:00+00:00")
    execution_artifact = EmpiricalExecutionCalibrator().fit(
        ExecutionCalibrationDataset(
            symbol="AAPL",
            state_features=calibration_frame,
            transition_features=transition_panel,
        )
    )

    from l1_microstructure.artifacts import RuntimeArtifactBundle

    bundle = RuntimeArtifactBundle(
        state_calibration=state_artifact,
        regime_calibration=regime_artifact,
        execution_calibration=execution_artifact,
        transition_model=transition_model,
    )
    events = [
        type("Quote", (), {})
    ]
    source_events = [
        {"ev": "Q", "sym": "AAPL", "t": 1710163800000000000, "bp": 100.0, "ap": 100.02, "bs": 100, "as": 100},
        {"ev": "Q", "sym": "AAPL", "t": 1710163801000000000, "bp": 100.01, "ap": 100.02, "bs": 400, "as": 50},
        {"ev": "T", "sym": "AAPL", "t": 1710163802000000000, "p": 100.02, "s": 400, "side": "buy"},
        {"ev": "Q", "sym": "AAPL", "t": 1710163804000000000, "bp": 100.04, "ap": 100.08, "bs": 40, "as": 300},
    ]
    from l1_microstructure.ingest import LiveSubscriptionRequest
    from tests.unit.l1_state_machine.support import FixtureMarketDataSource as InMemoryPolygonDataSource
    source = InMemoryPolygonDataSource(source_events)
    normalized_events = list(source.subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))

    runner = SimulatorPaperTradingRunner(events=normalized_events, runtime_artifacts=bundle)
    runner.start(RunnerConfig(symbols=("AAPL",), mode="paper", latency_ms=100))

    assert runner.updates
    assert runner.updates[0].regime.expected_holding_time_ns == 9_000_000_000
    assert runner.updates[0].state.flicker_state.value in {"stable", "competitive", "chaotic"}
    assert runner.monitoring_frame().iloc[0]["dominant_regime"] == "execution_flow"


def test_execution_calibration_artifact_changes_fill_surface() -> None:
    calibration_frame = pd.DataFrame(
        [
            {
                "symbol": "AAPL",
                "spread_norm": 40.0,
                "realized_volatility": 0.0004,
                "flicker_intensity": 5.0,
                "quote_pressure": 0.3,
                "dominant_regime": "execution_flow",
                "regime_confidence": 0.8,
            },
            {
                "symbol": "AAPL",
                "spread_norm": 120.0,
                "realized_volatility": 0.0010,
                "flicker_intensity": 6.0,
                "quote_pressure": 0.2,
                "dominant_regime": "liquidity_shock",
                "regime_confidence": 0.6,
            },
        ]
    )
    transition_panel = pd.DataFrame(
        [
            {"symbol": "AAPL", "regime": "execution_flow", "realized_drift_bps": 1.0},
            {"symbol": "AAPL", "regime": "liquidity_shock", "realized_drift_bps": 4.0},
        ]
    )

    artifact = EmpiricalExecutionCalibrator().fit(
        ExecutionCalibrationDataset(
            symbol="AAPL",
            state_features=calibration_frame,
            transition_features=transition_panel,
        )
    )

    assert artifact.alignment_weight >= 1.0
    assert artifact.regime_fill_multipliers["execution_flow"] > artifact.regime_fill_multipliers["liquidity_shock"]
    assert artifact.regime_slippage_multipliers["liquidity_shock"] >= artifact.regime_slippage_multipliers["execution_flow"]


def test_feature_engine_uses_regime_conditioned_state_surface_when_hint_is_available() -> None:
    calibration_frame = pd.DataFrame(
        [
            {
                "symbol": "AAPL",
                "spread_norm": 0.80,
                "realized_volatility": 0.0008,
                "flicker_intensity": 4.0,
                "quote_pressure": 0.10,
                "dominant_regime": "calm_liquidity",
            },
            {
                "symbol": "AAPL",
                "spread_norm": 0.85,
                "realized_volatility": 0.0009,
                "flicker_intensity": 4.1,
                "quote_pressure": 0.12,
                "dominant_regime": "calm_liquidity",
            },
            {
                "symbol": "AAPL",
                "spread_norm": 0.90,
                "realized_volatility": 0.0010,
                "flicker_intensity": 4.2,
                "quote_pressure": 0.14,
                "dominant_regime": "calm_liquidity",
            },
            {
                "symbol": "AAPL",
                "spread_norm": 0.95,
                "realized_volatility": 0.0011,
                "flicker_intensity": 4.3,
                "quote_pressure": 0.16,
                "dominant_regime": "calm_liquidity",
            },
            {
                "symbol": "AAPL",
                "spread_norm": 1.00,
                "realized_volatility": 0.0012,
                "flicker_intensity": 4.4,
                "quote_pressure": 0.18,
                "dominant_regime": "calm_liquidity",
            },
            {
                "symbol": "AAPL",
                "spread_norm": 2.00,
                "realized_volatility": 0.0020,
                "flicker_intensity": 6.0,
                "quote_pressure": 0.30,
                "dominant_regime": "liquidity_shock",
            },
            {
                "symbol": "AAPL",
                "spread_norm": 2.20,
                "realized_volatility": 0.0022,
                "flicker_intensity": 6.2,
                "quote_pressure": 0.32,
                "dominant_regime": "liquidity_shock",
            },
            {
                "symbol": "AAPL",
                "spread_norm": 2.40,
                "realized_volatility": 0.0024,
                "flicker_intensity": 6.4,
                "quote_pressure": 0.34,
                "dominant_regime": "liquidity_shock",
            },
            {
                "symbol": "AAPL",
                "spread_norm": 2.60,
                "realized_volatility": 0.0026,
                "flicker_intensity": 6.6,
                "quote_pressure": 0.36,
                "dominant_regime": "liquidity_shock",
            },
            {
                "symbol": "AAPL",
                "spread_norm": 2.80,
                "realized_volatility": 0.0028,
                "flicker_intensity": 6.8,
                "quote_pressure": 0.38,
                "dominant_regime": "liquidity_shock",
            },
        ]
    )
    artifact = QuantileStateCalibrator().fit(CalibrationDataset(symbol="AAPL", features=calibration_frame))
    baseline_engine = FeatureEngine(state_calibration=artifact)
    hinted_engine = FeatureEngine(state_calibration=artifact)
    hinted_engine.set_regime_hint("liquidity_shock")

    quote_1 = QuoteEvent(symbol="AAPL", timestamp_ns=1, bid_price=100.0, ask_price=100.02, bid_size=100, ask_size=100)
    quote_2 = QuoteEvent(symbol="AAPL", timestamp_ns=2, bid_price=100.01, ask_price=100.02, bid_size=300, ask_size=50)

    baseline_engine.update(quote_1)
    hinted_engine.update(quote_1)
    update_without_hint = baseline_engine.update(quote_2)
    update_with_hint = hinted_engine.update(quote_2)

    assert update_without_hint is not None
    assert update_with_hint is not None
    assert update_with_hint.quote_pressure <= update_without_hint.quote_pressure


def test_artifact_bundle_loader_rejects_version_mismatch(tmp_path) -> None:
    store = LocalArtifactStore(tmp_path)
    store.save(
        ArtifactMetadata("state-legacy", "state_calibration", "v0", "2026-03-09T00:00:00+00:00"),
        {
            "symbol": "AAPL",
            "spread_quantiles": (1.0, 2.0),
            "volatility_quantiles": (0.1, 0.2),
            "flicker_baseline": 4.0,
            "quote_pressure_scale": 0.5,
        },
    )

    with pytest.raises(ValueError, match="expected v1"):
        ArtifactBundleLoader(store)._load_state_calibration("state-legacy")


def test_local_artifact_store_detects_payload_corruption(tmp_path) -> None:
    store = LocalArtifactStore(tmp_path)
    store.save(
        ArtifactMetadata("state-1", "state_calibration", "v1", "2026-03-09T00:00:00+00:00"),
        {
            "symbol": "AAPL",
            "spread_quantiles": (1.0, 2.0),
            "volatility_quantiles": (0.1, 0.2),
            "flicker_baseline": 4.0,
            "quote_pressure_scale": 0.5,
        },
    )
    (tmp_path / "state-1" / "payload.pkl").write_bytes(b"corrupted")

    with pytest.raises(ValueError, match="hash mismatch"):
        store.load("state-1")