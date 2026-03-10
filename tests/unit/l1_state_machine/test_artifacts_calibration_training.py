from __future__ import annotations

import pandas as pd

from l1_microstructure.artifacts import ArtifactMetadata, LocalArtifactStore
from l1_microstructure.calibration import CalibrationDataset, EmpiricalRegimeCalibrator, QuantileStateCalibrator
from l1_microstructure.training import EmpiricalTransitionTrainer


def test_local_artifact_store_round_trips_payload_and_metadata(tmp_path) -> None:
    store = LocalArtifactStore(tmp_path)
    metadata = ArtifactMetadata(
        artifact_id="artifact-1",
        artifact_type="state_calibration",
        version="v1",
        created_at="2026-03-09T00:00:00+00:00",
        tags=("unit-test",),
        metadata={"symbol": "AAPL"},
    )
    payload = {"spread_quantiles": [1.0, 2.0], "flicker_baseline": 4.0}

    store.save(metadata, payload)

    loaded_payload = store.load("artifact-1")
    loaded_metadata = store.load_metadata("artifact-1")

    assert loaded_payload == payload
    assert loaded_metadata.artifact_id == metadata.artifact_id
    assert loaded_metadata.metadata["symbol"] == "AAPL"


def test_calibrators_fit_symbol_specific_state_and_regime_artifacts() -> None:
    frame = pd.DataFrame(
        [
            {
                "symbol": "AAPL",
                "spread_norm": 0.8,
                "realized_volatility": 0.0008,
                "flicker_intensity": 3.5,
                "quote_pressure": -0.2,
                "dominant_regime": "calm_liquidity",
                "expected_holding_time_ns": 12_000_000_000,
            },
            {
                "symbol": "AAPL",
                "spread_norm": 0.9,
                "realized_volatility": 0.0009,
                "flicker_intensity": 3.6,
                "quote_pressure": -0.1,
                "dominant_regime": "calm_liquidity",
                "expected_holding_time_ns": 11_000_000_000,
            },
            {
                "symbol": "AAPL",
                "spread_norm": 1.0,
                "realized_volatility": 0.0010,
                "flicker_intensity": 3.7,
                "quote_pressure": 0.0,
                "dominant_regime": "calm_liquidity",
                "expected_holding_time_ns": 10_000_000_000,
            },
            {
                "symbol": "AAPL",
                "spread_norm": 1.1,
                "realized_volatility": 0.0011,
                "flicker_intensity": 4.0,
                "quote_pressure": 0.1,
                "dominant_regime": "calm_liquidity",
                "expected_holding_time_ns": 9_000_000_000,
            },
            {
                "symbol": "AAPL",
                "spread_norm": 1.1,
                "realized_volatility": 0.0011,
                "flicker_intensity": 4.0,
                "quote_pressure": 0.1,
                "dominant_regime": "execution_flow",
                "expected_holding_time_ns": 6_000_000_000,
            },
            {
                "symbol": "AAPL",
                "spread_norm": 1.3,
                "realized_volatility": 0.0014,
                "flicker_intensity": 4.2,
                "quote_pressure": 0.2,
                "dominant_regime": "execution_flow",
                "expected_holding_time_ns": 6_000_000_000,
            },
            {
                "symbol": "AAPL",
                "spread_norm": 1.5,
                "realized_volatility": 0.0016,
                "flicker_intensity": 4.4,
                "quote_pressure": 0.3,
                "dominant_regime": "execution_flow",
                "expected_holding_time_ns": 5_000_000_000,
            },
            {
                "symbol": "AAPL",
                "spread_norm": 1.7,
                "realized_volatility": 0.0018,
                "flicker_intensity": 4.8,
                "quote_pressure": 0.35,
                "dominant_regime": "execution_flow",
                "expected_holding_time_ns": 5_000_000_000,
            },
            {
                "symbol": "AAPL",
                "spread_norm": 1.9,
                "realized_volatility": 0.0022,
                "flicker_intensity": 5.2,
                "quote_pressure": 0.4,
                "dominant_regime": "competitive_liquidity",
                "expected_holding_time_ns": 4_000_000_000,
            },
        ]
    )
    dataset = CalibrationDataset(symbol="AAPL", features=frame, metadata={"source": "unit-test"})

    state_artifact = QuantileStateCalibrator(minimum_regime_surface_rows=4).fit(dataset)
    regime_artifact = EmpiricalRegimeCalibrator().fit(dataset)

    assert state_artifact.symbol == "AAPL"
    assert state_artifact.spread_quantiles[0] < state_artifact.spread_quantiles[1]
    assert state_artifact.quote_pressure_scale > 0.0
    assert state_artifact.regime_surfaces["calm_liquidity"].sample_count == 4
    assert state_artifact.regime_surfaces["execution_flow"].sample_count == 4
    assert "competitive_liquidity" not in state_artifact.regime_surfaces
    assert state_artifact.metadata["regime_surface_count"] == 2
    assert state_artifact.metadata["minimum_regime_surface_rows"] == 4
    assert abs(sum(regime_artifact.regime_priors.values()) - 1.0) < 1e-9
    assert regime_artifact.holding_time_seconds["execution_flow"] == 5.5


def test_empirical_transition_trainer_builds_and_persists_artifact(tmp_path) -> None:
    transition_panel = pd.DataFrame(
        [
            {
                "symbol": "AAPL",
                "from_state": "tight|neutral|neutral|competitive|quiet",
                "to_state": "normal|buy_heavy|buy_heavy|competitive|normal",
                "regime": "execution_flow",
                "horizon_ns": 3_000_000_000,
                "holding_time_ns": 1_000_000_000,
                "realized_drift_bps": 1.5,
                "censored": False,
            },
            {
                "symbol": "AAPL",
                "from_state": "tight|neutral|neutral|competitive|quiet",
                "to_state": "normal|buy_heavy|buy_heavy|competitive|normal",
                "regime": "execution_flow",
                "horizon_ns": 15_000_000_000,
                "holding_time_ns": 2_000_000_000,
                "realized_drift_bps": 2.5,
                "censored": False,
            },
        ]
    )
    store = LocalArtifactStore(tmp_path)
    trainer = EmpiricalTransitionTrainer(artifact_store=store)

    samples = trainer.samples_from_frame(transition_panel)
    artifact = trainer.fit(samples, runtime_horizon_ns=3_000_000_000)
    payload = store.load(artifact.model_id)

    assert artifact.edge_count == 1
    assert payload["sample_count"] == 2
    assert payload["runtime_horizon_ns"] == 3_000_000_000
    assert payload["available_horizons_ns"] == [3_000_000_000, 15_000_000_000]
    edge_payload = next(iter(payload["edges"].values()))
    assert edge_payload["transition_probability"] == 1.0
    assert edge_payload["drift_mean_bps"] == 1.5
    assert payload["horizon_models"]["15000000000"]["sample_count"] == 1