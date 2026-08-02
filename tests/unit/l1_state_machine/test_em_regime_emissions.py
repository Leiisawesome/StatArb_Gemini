"""EM-fitted regime emissions for the HMM-style regime filter."""

from __future__ import annotations

from dataclasses import asdict, replace

import pandas as pd

from l1_microstructure.artifacts import ArtifactBundleLoader, ArtifactMetadata, LocalArtifactStore
from l1_microstructure.calibration import CalibrationDataset, EmpiricalRegimeCalibrator
from l1_microstructure.calibration.interfaces import RegimeCalibrationArtifact, RegimeEmissionModel
from l1_microstructure.config import FrameworkConfig, RegimeConfig
from l1_microstructure.events import QuoteEvent, TradeEvent, TradeSide
from l1_microstructure.features import FeatureEngine
from l1_microstructure.regime import MicrostructureRegime, RegimeInferencer


def _state_panel_frame() -> pd.DataFrame:
    """Synthetic panel with separable regimes for emission EM."""
    rows: list[dict[str, object]] = []
    # Calm: tight spread, low vol, low flicker, weak pressure
    for index in range(20):
        rows.append(
            {
                "symbol": "AAPL",
                "timestamp_ns": index * 1_000_000_000,
                "spread_norm": 0.7 + 0.02 * (index % 3),
                "quote_pressure": 0.05 * ((index % 2) - 0.5),
                "trade_pressure": 0.05 * ((index % 3) - 1),
                "flicker_intensity": 2.0 + 0.1 * (index % 2),
                "realized_volatility": 0.0004 + 0.00002 * (index % 2),
                "dominant_regime": "calm_liquidity",
                "expected_holding_time_ns": 12_000_000_000,
            }
        )
    # Execution flow: elevated trade/quote pressure
    for index in range(20):
        rows.append(
            {
                "symbol": "AAPL",
                "timestamp_ns": (20 + index) * 1_000_000_000,
                "spread_norm": 1.0 + 0.03 * (index % 3),
                "quote_pressure": 0.55 + 0.05 * (index % 2),
                "trade_pressure": 0.65 + 0.05 * (index % 3),
                "flicker_intensity": 4.0 + 0.1 * (index % 2),
                "realized_volatility": 0.0010 + 0.00003 * (index % 2),
                "dominant_regime": "execution_flow",
                "expected_holding_time_ns": 6_000_000_000,
            }
        )
    # Liquidity shock: wide spread, high vol
    for index in range(20):
        rows.append(
            {
                "symbol": "AAPL",
                "timestamp_ns": (40 + index) * 1_000_000_000,
                "spread_norm": 2.5 + 0.05 * (index % 3),
                "quote_pressure": 0.2 * ((index % 2) - 0.5),
                "trade_pressure": 0.15 * ((index % 3) - 1),
                "flicker_intensity": 7.0 + 0.2 * (index % 2),
                "realized_volatility": 0.0035 + 0.0001 * (index % 2),
                "dominant_regime": "liquidity_shock",
                "expected_holding_time_ns": 2_000_000_000,
            }
        )
    # Competitive: tight + high flicker
    for index in range(20):
        rows.append(
            {
                "symbol": "AAPL",
                "timestamp_ns": (60 + index) * 1_000_000_000,
                "spread_norm": 0.5 + 0.02 * (index % 3),
                "quote_pressure": 0.1 * ((index % 2) - 0.5),
                "trade_pressure": 0.1 * ((index % 3) - 1),
                "flicker_intensity": 9.0 + 0.2 * (index % 2),
                "realized_volatility": 0.0007 + 0.00002 * (index % 2),
                "dominant_regime": "competitive_liquidity",
                "expected_holding_time_ns": 4_000_000_000,
            }
        )
    return pd.DataFrame(rows)


def test_empirical_regime_calibrator_fits_emission_model() -> None:
    dataset = CalibrationDataset(symbol="AAPL", features=_state_panel_frame(), metadata={"source": "unit"})
    artifact = EmpiricalRegimeCalibrator(em_iterations=4).fit(dataset)

    assert artifact.emission_model is not None
    model = artifact.emission_model
    assert model.feature_names == (
        "spread_norm",
        "quote_pressure",
        "trade_pressure",
        "flicker_intensity",
        "realized_volatility",
    )
    assert set(model.means) == {regime.value for regime in MicrostructureRegime}
    # Separable clusters: calm spread mean < shock spread mean
    calm_mean = model.means["calm_liquidity"]
    shock_mean = model.means["liquidity_shock"]
    assert calm_mean[0] < shock_mean[0]
    # Execution flow should have higher |trade pressure| mean than calm
    assert abs(model.means["execution_flow"][2]) > abs(calm_mean[2])
    assert "em_emissions" in artifact.metadata["method"]
    assert artifact.metadata["emission_uses_timestamps"] is True
    assert artifact.duration_model is not None


def test_emission_model_skipped_without_feature_columns() -> None:
    frame = pd.DataFrame(
        [
            {
                "dominant_regime": "calm_liquidity",
                "expected_holding_time_ns": 12_000_000_000,
            },
            {
                "dominant_regime": "execution_flow",
                "expected_holding_time_ns": 6_000_000_000,
            },
        ]
    )
    artifact = EmpiricalRegimeCalibrator().fit(CalibrationDataset("AAPL", frame))
    assert artifact.emission_model is None
    assert artifact.metadata["method"] == "empirical_regime_priors"


def test_fitted_emissions_prefer_matching_regime_on_clear_observation() -> None:
    dataset = CalibrationDataset(symbol="AAPL", features=_state_panel_frame())
    artifact = EmpiricalRegimeCalibrator(em_iterations=5).fit(dataset)
    assert artifact.emission_model is not None

    # Build a state that looks like liquidity shock using the feature engine path,
    # then force emission vector by constructing inferencer with the artifact.
    config = RegimeConfig(use_fitted_emissions=True, emission_heuristic_blend=0.0)
    inferencer = RegimeInferencer(regime_config=config, regime_calibration=artifact)

    # Drive feature engine with a wide, stressed book; may not map perfectly but
    # we can also call emission path indirectly via update after warm-up.
    engine = FeatureEngine()
    # Quiet calm-like prints first
    for index in range(5):
        ts = (index + 1) * 1_000_000_000
        state = engine.update(
            QuoteEvent(
                symbol="AAPL",
                timestamp_ns=ts,
                bid_price=100.0,
                ask_price=100.01,
                bid_size=200,
                ask_size=200,
            )
        )
        assert state is not None
        inferencer.update(state)

    # Stress: jump mid hard and trade aggressively while widening
    shock_state = engine.update(
        QuoteEvent(
            symbol="AAPL",
            timestamp_ns=10_000_000_000,
            bid_price=99.0,
            ask_price=100.5,
            bid_size=20,
            ask_size=20,
        )
    )
    assert shock_state is not None
    # Directly verify fitted emission puts mass on the closest cluster for a
    # synthetic shock-like feature vector through the private emission API.
    shock_like = replace(
        shock_state,
        spread_norm=2.6,
        quote_pressure=0.0,
        trade_pressure=0.0,
        flicker_intensity=7.2,
        realized_volatility=0.0036,
    )
    emission = inferencer._fitted_emission_probabilities(shock_like)
    assert max(emission, key=emission.get) is MicrostructureRegime.LIQUIDITY_SHOCK


def test_heuristic_blend_moves_emissions_toward_scores() -> None:
    means = {
        regime.value: (1.0, 0.0, 0.0, 4.0, 0.001)
        for regime in MicrostructureRegime
    }
    stds = {
        regime.value: (0.5, 0.5, 0.5, 1.0, 0.001)
        for regime in MicrostructureRegime
    }
    # Make calm distinctly low-vol / low-spread in the model.
    means["calm_liquidity"] = (0.5, 0.0, 0.0, 2.0, 0.0003)
    means["liquidity_shock"] = (3.0, 0.0, 0.0, 8.0, 0.004)
    model = RegimeEmissionModel(
        feature_names=(
            "spread_norm",
            "quote_pressure",
            "trade_pressure",
            "flicker_intensity",
            "realized_volatility",
        ),
        means=means,
        stds=stds,
        effective_weight={regime.value: 10.0 for regime in MicrostructureRegime},
    )
    artifact = RegimeCalibrationArtifact(
        symbol="AAPL",
        regime_priors={regime.value: 0.25 for regime in MicrostructureRegime},
        holding_time_seconds={
            "calm_liquidity": 12.0,
            "execution_flow": 6.0,
            "liquidity_shock": 2.0,
            "competitive_liquidity": 4.0,
        },
        emission_model=model,
    )
    state = FeatureEngine().update(
        QuoteEvent(symbol="AAPL", timestamp_ns=1_000_000_000, bid_price=100.0, ask_price=100.02, bid_size=100, ask_size=100)
    )
    assert state is not None

    pure = RegimeInferencer(
        regime_config=RegimeConfig(use_fitted_emissions=True, emission_heuristic_blend=0.0),
        regime_calibration=artifact,
    )
    blended = RegimeInferencer(
        regime_config=RegimeConfig(use_fitted_emissions=True, emission_heuristic_blend=1.0),
        regime_calibration=artifact,
    )
    pure_emission = pure._resolve_emission_probabilities(
        state,
        {
            MicrostructureRegime.CALM_LIQUIDITY: 2.0,
            MicrostructureRegime.EXECUTION_FLOW: 0.5,
            MicrostructureRegime.LIQUIDITY_SHOCK: -0.5,
            MicrostructureRegime.COMPETITIVE_LIQUIDITY: 0.0,
        },
    )
    heuristic_emission = blended._resolve_emission_probabilities(
        state,
        {
            MicrostructureRegime.CALM_LIQUIDITY: 2.0,
            MicrostructureRegime.EXECUTION_FLOW: 0.5,
            MicrostructureRegime.LIQUIDITY_SHOCK: -0.5,
            MicrostructureRegime.COMPETITIVE_LIQUIDITY: 0.0,
        },
    )
    # blend=1.0 must equal pure heuristic path
    only_heuristic = RegimeInferencer(regime_config=RegimeConfig(use_fitted_emissions=False))
    scores = {
        MicrostructureRegime.CALM_LIQUIDITY: 2.0,
        MicrostructureRegime.EXECUTION_FLOW: 0.5,
        MicrostructureRegime.LIQUIDITY_SHOCK: -0.5,
        MicrostructureRegime.COMPETITIVE_LIQUIDITY: 0.0,
    }
    expected_heuristic = only_heuristic._emission_probabilities(scores)
    for regime in MicrostructureRegime:
        assert abs(heuristic_emission[regime] - expected_heuristic[regime]) < 1e-12
    # Fitted path is defined and differs from pure heuristic in general
    assert pure_emission[MicrostructureRegime.CALM_LIQUIDITY] > 0.0


def test_regime_calibration_round_trips_emission_model(tmp_path) -> None:
    dataset = CalibrationDataset(symbol="AAPL", features=_state_panel_frame())
    artifact = EmpiricalRegimeCalibrator(em_iterations=2).fit(dataset)
    assert artifact.emission_model is not None

    store = LocalArtifactStore(tmp_path)
    store.save(
        ArtifactMetadata("regime-em-1", "regime_calibration", "v1", "2026-03-09T00:00:00+00:00"),
        asdict(artifact),
    )
    bundle = ArtifactBundleLoader(store).load_runtime_bundle(regime_calibration_id="regime-em-1")
    loaded = bundle.regime_calibration
    assert loaded is not None
    assert loaded.emission_model is not None
    assert loaded.emission_model.feature_names == artifact.emission_model.feature_names
    assert loaded.emission_model.means["execution_flow"] == artifact.emission_model.means["execution_flow"]


def test_legacy_regime_payload_without_emissions_still_loads(tmp_path) -> None:
    store = LocalArtifactStore(tmp_path)
    store.save(
        ArtifactMetadata("regime-legacy", "regime_calibration", "v1", "2026-03-09T00:00:00+00:00"),
        {
            "symbol": "AAPL",
            "regime_priors": {
                "calm_liquidity": 0.25,
                "execution_flow": 0.25,
                "liquidity_shock": 0.25,
                "competitive_liquidity": 0.25,
            },
            "holding_time_seconds": {
                "calm_liquidity": 12.0,
                "execution_flow": 6.0,
                "liquidity_shock": 2.0,
                "competitive_liquidity": 4.0,
            },
            "metadata": {},
        },
    )
    bundle = ArtifactBundleLoader(store).load_runtime_bundle(regime_calibration_id="regime-legacy")
    assert bundle.regime_calibration is not None
    assert bundle.regime_calibration.emission_model is None


def test_pipeline_with_fitted_emissions_runs() -> None:
    dataset = CalibrationDataset(symbol="AAPL", features=_state_panel_frame())
    artifact = EmpiricalRegimeCalibrator(em_iterations=2).fit(dataset)
    from l1_microstructure.artifacts.runtime import RuntimeArtifactBundle
    from l1_microstructure.pipeline import L1MicrostructureStateMachine

    machine = L1MicrostructureStateMachine(
        FrameworkConfig(),
        runtime_artifacts=RuntimeArtifactBundle(regime_calibration=artifact),
    )
    updates = []
    for index in range(8):
        update = machine.on_event(
            QuoteEvent(
                symbol="AAPL",
                timestamp_ns=(index + 1) * 1_000_000_000,
                bid_price=100.0 + 0.01 * index,
                ask_price=100.02 + 0.01 * index,
                bid_size=150,
                ask_size=100,
            )
        )
        if update is not None:
            updates.append(update)
        machine.on_event(
            TradeEvent(
                symbol="AAPL",
                timestamp_ns=(index + 1) * 1_000_000_000 + 100,
                price=100.01 + 0.01 * index,
                size=50,
                side=TradeSide.BUY,
            )
        )
    assert updates
    assert machine.regime_inferencer._emission_model is not None
