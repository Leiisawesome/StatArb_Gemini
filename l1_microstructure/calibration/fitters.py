"""Empirical calibration utilities for symbol-specific successor-package research."""

from __future__ import annotations

import pandas as pd

from l1_microstructure.config import RegimeConfig
from l1_microstructure.regime import MicrostructureRegime

from .interfaces import (
    CalibrationDataset,
    ExecutionCalibrationArtifact,
    ExecutionCalibrationDataset,
    RegimeCalibrationArtifact,
    StateCalibrationArtifact,
    StateRegimeSurface,
)


class QuantileStateCalibrator:
    def __init__(self, minimum_regime_surface_rows: int = 5):
        self.minimum_regime_surface_rows = minimum_regime_surface_rows

    def fit(self, dataset: CalibrationDataset) -> StateCalibrationArtifact:
        frame = dataset.features
        self._require_columns(frame, ("spread_norm", "realized_volatility", "flicker_intensity", "quote_pressure"))

        spread_quantiles = self._tertiles(frame["spread_norm"])
        volatility_quantiles = self._tertiles(frame["realized_volatility"])
        flicker_baseline = float(frame["flicker_intensity"].median())
        quote_pressure_scale = max(float(frame["quote_pressure"].abs().quantile(0.75)), 1e-6)
        regime_surfaces: dict[str, StateRegimeSurface] = {}
        regime_surface_rows: dict[str, int] = {}
        if "dominant_regime" in frame.columns:
            for regime_value, regime_frame in frame.groupby("dominant_regime"):
                regime_sample_count = int(len(regime_frame))
                regime_surface_rows[str(regime_value)] = regime_sample_count
                if regime_sample_count < self.minimum_regime_surface_rows:
                    continue
                regime_surfaces[str(regime_value)] = StateRegimeSurface(
                    spread_quantiles=self._tertiles(regime_frame["spread_norm"]),
                    volatility_quantiles=self._tertiles(regime_frame["realized_volatility"]),
                    flicker_baseline=float(regime_frame["flicker_intensity"].median()),
                    quote_pressure_scale=max(float(regime_frame["quote_pressure"].abs().quantile(0.75)), 1e-6),
                    sample_count=regime_sample_count,
                )

        metadata = {
            "row_count": int(len(frame)),
            "columns": tuple(frame.columns),
            "method": "empirical_tertiles",
            "minimum_regime_surface_rows": self.minimum_regime_surface_rows,
            "regime_surface_row_counts": regime_surface_rows,
            "regime_surface_count": len(regime_surfaces),
            **dataset.metadata,
        }
        return StateCalibrationArtifact(
            symbol=dataset.symbol,
            spread_quantiles=spread_quantiles,
            volatility_quantiles=volatility_quantiles,
            flicker_baseline=flicker_baseline,
            quote_pressure_scale=quote_pressure_scale,
            regime_surfaces=regime_surfaces,
            metadata=metadata,
        )

    @staticmethod
    def _tertiles(series: pd.Series) -> tuple[float, float]:
        return float(series.quantile(1.0 / 3.0)), float(series.quantile(2.0 / 3.0))

    @staticmethod
    def _require_columns(frame: pd.DataFrame, columns: tuple[str, ...]) -> None:
        missing = [column for column in columns if column not in frame.columns]
        if missing:
            raise ValueError(f"calibration dataset is missing required columns: {missing}")


class EmpiricalRegimeCalibrator:
    def __init__(self, regime_config: RegimeConfig | None = None):
        self.regime_config = regime_config or RegimeConfig()

    def fit(self, dataset: CalibrationDataset) -> RegimeCalibrationArtifact:
        frame = dataset.features
        self._require_columns(frame, ("dominant_regime",))

        defaults = self._default_holding_times()
        counts = frame["dominant_regime"].value_counts(normalize=True)
        priors = {regime.value: float(counts.get(regime.value, self.regime_config.posterior_floor)) for regime in MicrostructureRegime}
        normalizer = sum(priors.values())
        priors = {regime: probability / normalizer for regime, probability in priors.items()}

        holding_time_seconds = defaults.copy()
        if "expected_holding_time_ns" in frame.columns:
            grouped = frame.groupby("dominant_regime")["expected_holding_time_ns"].median()
            for regime in MicrostructureRegime:
                if regime.value in grouped.index:
                    holding_time_seconds[regime.value] = float(grouped.loc[regime.value] / 1_000_000_000.0)

        metadata = {
            "row_count": int(len(frame)),
            "method": "empirical_regime_priors",
            **dataset.metadata,
        }
        return RegimeCalibrationArtifact(
            symbol=dataset.symbol,
            regime_priors=priors,
            holding_time_seconds=holding_time_seconds,
            metadata=metadata,
        )

    def _default_holding_times(self) -> dict[str, float]:
        return {
            MicrostructureRegime.CALM_LIQUIDITY.value: self.regime_config.calm_holding_time_seconds,
            MicrostructureRegime.EXECUTION_FLOW.value: self.regime_config.execution_flow_holding_time_seconds,
            MicrostructureRegime.LIQUIDITY_SHOCK.value: self.regime_config.liquidity_shock_holding_time_seconds,
            MicrostructureRegime.COMPETITIVE_LIQUIDITY.value: self.regime_config.competitive_liquidity_holding_time_seconds,
        }

    @staticmethod
    def _require_columns(frame: pd.DataFrame, columns: tuple[str, ...]) -> None:
        missing = [column for column in columns if column not in frame.columns]
        if missing:
            raise ValueError(f"calibration dataset is missing required columns: {missing}")


class EmpiricalExecutionCalibrator:
    def fit(self, dataset: ExecutionCalibrationDataset) -> ExecutionCalibrationArtifact:
        state_frame = dataset.state_features.copy()
        transition_frame = dataset.transition_features.copy()
        self._require_columns(state_frame, ("spread_norm", "realized_volatility", "dominant_regime", "regime_confidence"))
        self._require_columns(transition_frame, ("regime", "realized_drift_bps"))

        spread_high = float(state_frame["spread_norm"].quantile(2.0 / 3.0))
        volatility_high = float(state_frame["realized_volatility"].quantile(2.0 / 3.0))
        wide_share = float((state_frame["spread_norm"] >= spread_high).mean()) if len(state_frame) else 0.0
        stressed_share = float((state_frame["realized_volatility"] >= volatility_high).mean()) if len(state_frame) else 0.0
        median_confidence = float(state_frame["regime_confidence"].median()) if len(state_frame) else 0.5

        realized_drift = transition_frame["realized_drift_bps"].abs()
        drift_median = float(realized_drift.median()) if len(realized_drift) else 0.0
        drift_upper = float(realized_drift.quantile(0.75)) if len(realized_drift) else 0.0

        fill_probability_intercept = self._clip(1.2 - 1.1 * wide_share - 0.8 * stressed_share, -1.5, 2.5)
        alignment_weight = self._clip(1.5 + 2.0 * median_confidence, 1.0, 4.0)
        spread_penalty = self._clip(0.035 + 0.085 * wide_share + 0.050 * stressed_share, 0.01, 0.20)
        slippage_intercept_bps = self._clip(max(0.25, drift_median * 0.20), 0.25, 4.0)
        spread_slippage_weight = self._clip(0.35 + 0.80 * wide_share + 0.40 * stressed_share, 0.15, 2.5)
        adverse_selection_weight = self._clip(max(drift_upper, drift_median) / max(drift_median + 0.50, 0.50), 0.20, 3.0)

        regime_drift = transition_frame.groupby("regime")["realized_drift_bps"].apply(lambda series: float(series.abs().median()))
        regime_fill_multipliers: dict[str, float] = {}
        regime_slippage_multipliers: dict[str, float] = {}
        for regime in MicrostructureRegime:
            regime_value = regime.value
            regime_state = state_frame[state_frame["dominant_regime"] == regime_value]
            regime_wide_share = float((regime_state["spread_norm"] >= spread_high).mean()) if not regime_state.empty else wide_share
            regime_confidence = float(regime_state["regime_confidence"].median()) if not regime_state.empty else median_confidence
            drift_scale = float(regime_drift.get(regime_value, drift_median))
            regime_fill_multipliers[regime_value] = self._clip(
                1.05 - 0.45 * regime_wide_share + 0.25 * (regime_confidence - 0.5),
                0.35,
                1.25,
            )
            regime_slippage_multipliers[regime_value] = self._clip(
                0.85 + 0.90 * regime_wide_share + 0.20 * (drift_scale / max(drift_median + 0.25, 0.25)),
                0.75,
                2.50,
            )

        metadata = {
            "row_count": int(len(state_frame)),
            "transition_row_count": int(len(transition_frame)),
            "method": "empirical_execution_surface_v1",
            **dataset.metadata,
        }
        return ExecutionCalibrationArtifact(
            symbol=dataset.symbol,
            fill_probability_intercept=fill_probability_intercept,
            alignment_weight=alignment_weight,
            spread_penalty=spread_penalty,
            slippage_intercept_bps=slippage_intercept_bps,
            spread_slippage_weight=spread_slippage_weight,
            adverse_selection_weight=adverse_selection_weight,
            regime_fill_multipliers=regime_fill_multipliers,
            regime_slippage_multipliers=regime_slippage_multipliers,
            metadata=metadata,
        )

    @staticmethod
    def _require_columns(frame: pd.DataFrame, columns: tuple[str, ...]) -> None:
        missing = [column for column in columns if column not in frame.columns]
        if missing:
            raise ValueError(f"execution calibration dataset is missing required columns: {missing}")

    @staticmethod
    def _clip(value: float, lower: float, upper: float) -> float:
        return float(min(max(value, lower), upper))