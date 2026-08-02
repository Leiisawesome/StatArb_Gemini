"""HSMM Weibull sojourn times for the main regime filter."""

from __future__ import annotations

from dataclasses import asdict
from math import exp

import pandas as pd

from l1_microstructure.artifacts import ArtifactBundleLoader, ArtifactMetadata, LocalArtifactStore
from l1_microstructure.calibration import CalibrationDataset, EmpiricalRegimeCalibrator
from l1_microstructure.calibration.interfaces import (
    RegimeCalibrationArtifact,
    RegimeDurationModel,
)
from l1_microstructure.config import RegimeConfig
from l1_microstructure.events import QuoteEvent
from l1_microstructure.features import FeatureEngine
from l1_microstructure.regime import (
    MicrostructureRegime,
    RegimeInferencer,
    conditional_weibull_survival,
)


def _panel_with_runs() -> pd.DataFrame:
    """Long calm runs and short shock runs for duration shape contrast."""
    rows: list[dict[str, object]] = []
    ts = 0
    # Several multi-second calm runs
    for run in range(6):
        for step in range(8):
            ts += 1_000_000_000
            rows.append(
                {
                    "symbol": "AAPL",
                    "timestamp_ns": ts,
                    "spread_norm": 0.8,
                    "quote_pressure": 0.0,
                    "trade_pressure": 0.0,
                    "flicker_intensity": 2.5,
                    "realized_volatility": 0.0005,
                    "dominant_regime": "calm_liquidity",
                    "expected_holding_time_ns": 12_000_000_000,
                }
            )
        # brief switch
        ts += 1_000_000_000
        rows.append(
            {
                "symbol": "AAPL",
                "timestamp_ns": ts,
                "spread_norm": 2.8,
                "quote_pressure": 0.1,
                "trade_pressure": 0.1,
                "flicker_intensity": 7.0,
                "realized_volatility": 0.003,
                "dominant_regime": "liquidity_shock",
                "expected_holding_time_ns": 2_000_000_000,
            }
        )
        ts += 1_000_000_000
        rows.append(
            {
                "symbol": "AAPL",
                "timestamp_ns": ts,
                "spread_norm": 2.9,
                "quote_pressure": 0.0,
                "trade_pressure": 0.0,
                "flicker_intensity": 7.2,
                "realized_volatility": 0.0032,
                "dominant_regime": "liquidity_shock",
                "expected_holding_time_ns": 2_000_000_000,
            }
        )
    # Fill remaining regimes lightly so priors exist
    for regime in ("execution_flow", "competitive_liquidity"):
        for _ in range(4):
            ts += 1_000_000_000
            rows.append(
                {
                    "symbol": "AAPL",
                    "timestamp_ns": ts,
                    "spread_norm": 1.0,
                    "quote_pressure": 0.5 if regime == "execution_flow" else 0.0,
                    "trade_pressure": 0.6 if regime == "execution_flow" else 0.0,
                    "flicker_intensity": 4.0 if regime == "execution_flow" else 9.0,
                    "realized_volatility": 0.001,
                    "dominant_regime": regime,
                    "expected_holding_time_ns": 5_000_000_000,
                }
            )
    return pd.DataFrame(rows)


def test_conditional_weibull_shape_one_matches_exponential() -> None:
    mean_ns = 5_000_000_000
    dt_ns = 1_000_000_000
    exponential = exp(-dt_ns / mean_ns)
    weibull = conditional_weibull_survival(0, dt_ns, mean_ns, shape=1.0)
    assert abs(weibull - exponential) < 1e-9


def test_conditional_weibull_shape_above_one_raises_early_exit_survival() -> None:
    mean_ns = 5_000_000_000
    dt_ns = 500_000_000
    # Fresh sojourn (dwell=0): shape>1 has higher early survival than exponential.
    exponential = conditional_weibull_survival(0, dt_ns, mean_ns, shape=1.0)
    persistent = conditional_weibull_survival(0, dt_ns, mean_ns, shape=3.0)
    assert persistent > exponential


def test_empirical_regime_calibrator_fits_duration_shapes() -> None:
    dataset = CalibrationDataset(symbol="AAPL", features=_panel_with_runs())
    artifact = EmpiricalRegimeCalibrator(em_iterations=2, fit_emissions=False).fit(dataset)

    assert artifact.duration_model is not None
    assert artifact.duration_model.family == "weibull"
    assert artifact.duration_model.run_count["calm_liquidity"] >= 1
    assert artifact.duration_model.run_count["liquidity_shock"] >= 1
    # Mean sojourns from runs override defaults for calm (long runs).
    assert artifact.holding_time_seconds["calm_liquidity"] > artifact.holding_time_seconds["liquidity_shock"]
    assert "hsmm" in artifact.metadata["method"]
    for shape in artifact.duration_model.shapes.values():
        assert 0.5 <= shape <= 10.0


def test_hsmm_predict_uses_dwell_for_dominant_regime() -> None:
    duration = RegimeDurationModel(
        family="weibull",
        shapes={
            "calm_liquidity": 4.0,
            "execution_flow": 2.0,
            "liquidity_shock": 1.5,
            "competitive_liquidity": 2.0,
        },
        run_count={regime.value: 5 for regime in MicrostructureRegime},
    )
    artifact = RegimeCalibrationArtifact(
        symbol="AAPL",
        regime_priors={regime.value: 0.25 for regime in MicrostructureRegime},
        holding_time_seconds={
            "calm_liquidity": 10.0,
            "execution_flow": 6.0,
            "liquidity_shock": 2.0,
            "competitive_liquidity": 4.0,
        },
        duration_model=duration,
    )
    config = RegimeConfig(use_hsmm_durations=True)
    inferencer = RegimeInferencer(regime_config=config, regime_calibration=artifact)
    engine = FeatureEngine()

    # Establish calm dominance with quiet book.
    for index in range(5):
        state = engine.update(
            QuoteEvent(
                symbol="AAPL",
                timestamp_ns=(index + 1) * 1_000_000_000,
                bid_price=100.0,
                ask_price=100.01,
                bid_size=200,
                ask_size=200,
            )
        )
        assert state is not None
        posterior = inferencer.update(state)

    assert inferencer.dominant_regime is not None
    assert inferencer.regime_started_at_ns is not None
    started = inferencer.regime_started_at_ns
    # Advance without changing dominance much
    state = engine.update(
        QuoteEvent(
            symbol="AAPL",
            timestamp_ns=20_000_000_000,
            bid_price=100.0,
            ask_price=100.01,
            bid_size=200,
            ask_size=200,
        )
    )
    assert state is not None
    later = inferencer.update(state)
    assert abs(sum(later.probabilities.values()) - 1.0) < 1e-9
    # Dwell clock continues while MAP regime is stable.
    if later.dominant_regime == posterior.dominant_regime:
        assert inferencer.regime_started_at_ns == started


def test_hsmm_disabled_falls_back_to_exponential() -> None:
    duration = RegimeDurationModel(
        shapes={regime.value: 5.0 for regime in MicrostructureRegime},
    )
    artifact = RegimeCalibrationArtifact(
        symbol="AAPL",
        regime_priors={regime.value: 0.25 for regime in MicrostructureRegime},
        holding_time_seconds={regime.value: 5.0 for regime in MicrostructureRegime},
        duration_model=duration,
    )
    hsmm_off = RegimeInferencer(
        regime_config=RegimeConfig(use_hsmm_durations=False),
        regime_calibration=artifact,
    )
    assert hsmm_off._use_hsmm is False

    no_duration = RegimeInferencer(
        regime_config=RegimeConfig(use_hsmm_durations=True),
        regime_calibration=RegimeCalibrationArtifact(
            symbol="AAPL",
            regime_priors={regime.value: 0.25 for regime in MicrostructureRegime},
            holding_time_seconds={regime.value: 5.0 for regime in MicrostructureRegime},
        ),
    )
    assert no_duration._use_hsmm is False


def test_duration_model_round_trips_through_artifact_store(tmp_path) -> None:
    dataset = CalibrationDataset(symbol="AAPL", features=_panel_with_runs())
    artifact = EmpiricalRegimeCalibrator(em_iterations=1, fit_emissions=False).fit(dataset)
    assert artifact.duration_model is not None

    store = LocalArtifactStore(tmp_path)
    store.save(
        ArtifactMetadata("regime-hsmm-1", "regime_calibration", "v1", "2026-03-09T00:00:00+00:00"),
        asdict(artifact),
    )
    loaded = ArtifactBundleLoader(store).load_runtime_bundle(regime_calibration_id="regime-hsmm-1")
    assert loaded.regime_calibration is not None
    assert loaded.regime_calibration.duration_model is not None
    assert (
        loaded.regime_calibration.duration_model.shapes["calm_liquidity"]
        == artifact.duration_model.shapes["calm_liquidity"]
    )


def test_recovery_preserves_hsmm_dwell_state() -> None:
    from l1_microstructure.pipeline import L1MicrostructureStateMachine
    from l1_microstructure.artifacts.runtime import RuntimeArtifactBundle
    from l1_microstructure.config import FrameworkConfig

    dataset = CalibrationDataset(symbol="AAPL", features=_panel_with_runs())
    artifact = EmpiricalRegimeCalibrator(em_iterations=1, fit_emissions=False).fit(dataset)
    machine = L1MicrostructureStateMachine(
        FrameworkConfig(),
        runtime_artifacts=RuntimeArtifactBundle(regime_calibration=artifact),
    )
    for index in range(6):
        machine.on_event(
            QuoteEvent(
                symbol="AAPL",
                timestamp_ns=(index + 1) * 1_000_000_000,
                bid_price=100.0,
                ask_price=100.02,
                bid_size=100,
                ask_size=100,
            )
        )
    started = machine.regime_inferencer.regime_started_at_ns
    dominant = machine.regime_inferencer.dominant_regime
    snapshot = machine.snapshot_state()

    restored = L1MicrostructureStateMachine(
        FrameworkConfig(),
        runtime_artifacts=RuntimeArtifactBundle(regime_calibration=artifact),
    )
    restored.restore_state(snapshot)
    assert restored.regime_inferencer.regime_started_at_ns == started
    assert restored.regime_inferencer.dominant_regime == dominant
