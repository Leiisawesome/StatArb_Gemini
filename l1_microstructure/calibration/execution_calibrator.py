"""Execution fill/slippage surface calibration."""

from __future__ import annotations

import pandas as pd

from l1_microstructure.regime import MicrostructureRegime

from .interfaces import ExecutionCalibrationArtifact, ExecutionCalibrationDataset


class EmpiricalExecutionCalibrator:
    _MAXIMUM_ROUND_TRIP_ADVERSE_SELECTION_FRACTION = 0.50

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
        raw_adverse_selection_weight = max(drift_upper, drift_median) / max(drift_median + 0.50, 0.50)

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

        maximum_regime_slippage_multiplier = max(regime_slippage_multipliers.values(), default=1.0)
        adverse_selection_weight_cap = self._MAXIMUM_ROUND_TRIP_ADVERSE_SELECTION_FRACTION / max(
            2.0 * maximum_regime_slippage_multiplier,
            1.0,
        )
        adverse_selection_weight = self._clip(
            raw_adverse_selection_weight,
            0.0,
            adverse_selection_weight_cap,
        )
        metadata = {
            "row_count": int(len(state_frame)),
            "transition_row_count": int(len(transition_frame)),
            "method": "empirical_execution_surface_v1",
            "raw_adverse_selection_weight": float(raw_adverse_selection_weight),
            "adverse_selection_weight_cap": float(adverse_selection_weight_cap),
            "maximum_round_trip_adverse_selection_fraction": (
                self._MAXIMUM_ROUND_TRIP_ADVERSE_SELECTION_FRACTION
            ),
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
