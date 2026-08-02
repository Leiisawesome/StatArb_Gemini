"""Regime priors, HSMM sojourns, and EM emission calibration."""

from __future__ import annotations

from math import exp, log, sqrt

import pandas as pd

from l1_microstructure.config import RegimeConfig
from l1_microstructure.regime import MicrostructureRegime
from l1_microstructure.regime_transition import leave_weight_rows, predict_regime_probabilities
from l1_microstructure.stats.distributions import diagonal_gaussian_log_likelihood

from .interfaces import (
    CalibrationDataset,
    RegimeCalibrationArtifact,
    RegimeDurationModel,
    RegimeEmissionModel,
)

# Continuous features used for P(x | R). Must be present on the state panel and
# reconstructible from ObservedState at runtime (see RegimeInferencer).
REGIME_EMISSION_FEATURES: tuple[str, ...] = (
    "spread_norm",
    "quote_pressure",
    "trade_pressure",
    "flicker_intensity",
    "realized_volatility",
)


class EmpiricalRegimeCalibrator:
    """
    Fit regime priors, HSMM sojourns, and optional EM emission densities.

    Emissions are diagonal Gaussians over continuous L1 features. EM uses the
    continuous-time predict step for sequential responsibilities when
    ``timestamp_ns`` is available. Duration shapes are Weibull moment fits on
    MAP regime runs (shape=1 recovers the memoryless exponential case).
    """

    def __init__(
        self,
        regime_config: RegimeConfig | None = None,
        *,
        fit_emissions: bool = True,
        fit_durations: bool = True,
        em_iterations: int = 5,
        min_emission_std: float = 1e-4,
        min_regime_weight: float = 1.0,
        emission_features: tuple[str, ...] = REGIME_EMISSION_FEATURES,
        min_duration_shape: float = 0.5,
        max_duration_shape: float = 10.0,
        session_gap_seconds: float = 4 * 60 * 60,
    ):
        self.regime_config = regime_config or RegimeConfig()
        self.fit_emissions = fit_emissions
        self.fit_durations = fit_durations
        self.em_iterations = max(int(em_iterations), 1)
        self.min_emission_std = max(float(min_emission_std), 1e-12)
        self.min_regime_weight = max(float(min_regime_weight), 1e-9)
        self.emission_features = tuple(emission_features)
        self.min_duration_shape = max(float(min_duration_shape), 1e-3)
        self.max_duration_shape = max(float(max_duration_shape), self.min_duration_shape)
        self.session_gap_ns = max(int(session_gap_seconds * 1_000_000_000), 1)

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

        duration_model = None
        duration_meta: dict[str, object] = {}
        if self.fit_durations and "timestamp_ns" in frame.columns:
            duration_model, fitted_means, duration_meta = self._fit_duration_model(frame)
            for regime_value, mean_seconds in fitted_means.items():
                if mean_seconds > 0.0:
                    holding_time_seconds[regime_value] = float(mean_seconds)

        emission_model = None
        emission_meta: dict[str, object] = {}
        if self.fit_emissions and self._has_emission_features(frame):
            emission_model, emission_meta = self._fit_emission_model(
                frame,
                priors=priors,
                holding_time_seconds=holding_time_seconds,
                duration_shapes=(
                    duration_model.shapes if duration_model is not None else None
                ),
            )

        method = "empirical_regime_priors"
        if emission_model is not None and duration_model is not None:
            method = "empirical_regime_priors_em_emissions_hsmm"
        elif emission_model is not None:
            method = "empirical_regime_priors_em_emissions"
        elif duration_model is not None:
            method = "empirical_regime_priors_hsmm"

        metadata = {
            "row_count": int(len(frame)),
            "method": method,
            **duration_meta,
            **emission_meta,
            **dataset.metadata,
        }
        return RegimeCalibrationArtifact(
            symbol=dataset.symbol,
            regime_priors=priors,
            holding_time_seconds=holding_time_seconds,
            emission_model=emission_model,
            duration_model=duration_model,
            metadata=metadata,
        )

    def _fit_duration_model(
        self,
        frame: pd.DataFrame,
    ) -> tuple[RegimeDurationModel, dict[str, float], dict[str, object]]:
        """Fit Weibull mean/shape from consecutive MAP regime runs."""
        sorted_frame = frame.sort_values("timestamp_ns")
        labels = [str(value) for value in sorted_frame["dominant_regime"].tolist()]
        timestamps = [int(value) for value in sorted_frame["timestamp_ns"].tolist()]
        session_ids = (
            [str(value) for value in sorted_frame["session_id"].tolist()]
            if "session_id" in sorted_frame.columns
            else None
        )

        deltas = [
            max(timestamps[index] - timestamps[index - 1], 1)
            for index in range(1, len(timestamps))
            if self._same_session(session_ids, index - 1, index)
            and (timestamps[index] - timestamps[index - 1]) < self.session_gap_ns
        ]
        default_delta = int(sorted(deltas)[len(deltas) // 2]) if deltas else 1_000_000_000

        runs: dict[str, list[int]] = {regime.value: [] for regime in MicrostructureRegime}
        if labels:
            run_start = 0
            for index in range(1, len(labels) + 1):
                continues = (
                    index < len(labels)
                    and labels[index] == labels[run_start]
                    and self._same_session(session_ids, run_start, index)
                    and (timestamps[index] - timestamps[index - 1]) < self.session_gap_ns
                )
                if continues:
                    continue
                duration_ns = max(timestamps[index - 1] - timestamps[run_start] + default_delta, 1)
                if labels[run_start] in runs:
                    runs[labels[run_start]].append(duration_ns)
                run_start = index

        default_shape = float(self.regime_config.default_duration_shape)
        shapes: dict[str, float] = {}
        means_seconds: dict[str, float] = {}
        run_count: dict[str, int] = {}
        for regime in MicrostructureRegime:
            values = runs[regime.value]
            run_count[regime.value] = len(values)
            if not values:
                shapes[regime.value] = default_shape
                means_seconds[regime.value] = 0.0
                continue
            mean_ns = sum(values) / len(values)
            means_seconds[regime.value] = float(mean_ns / 1_000_000_000.0)
            if len(values) < 2 or mean_ns <= 0.0:
                shapes[regime.value] = default_shape
                continue
            variance = sum((value - mean_ns) ** 2 for value in values) / (len(values) - 1)
            std = sqrt(max(variance, 0.0))
            coefficient_of_variation = std / mean_ns if mean_ns > 0.0 else 0.0
            if coefficient_of_variation <= 1e-6:
                fitted_shape = self.max_duration_shape
            else:
                # Same Weibull moment approximation as transparent SemiMarkovRegimeTrainer.
                fitted_shape = coefficient_of_variation ** -1.086
            shapes[regime.value] = float(
                min(max(fitted_shape, self.min_duration_shape), self.max_duration_shape)
            )

        model = RegimeDurationModel(family="weibull", shapes=shapes, run_count=run_count)
        meta = {
            "duration_family": "weibull",
            "duration_run_count": dict(run_count),
            "duration_shapes": dict(shapes),
            "duration_default_delta_ns": default_delta,
        }
        return model, means_seconds, meta

    @staticmethod
    def _same_session(session_ids: list[str] | None, left: int, right: int) -> bool:
        if session_ids is None:
            return True
        return session_ids[left] == session_ids[right]

    def _has_emission_features(self, frame: pd.DataFrame) -> bool:
        return all(column in frame.columns for column in self.emission_features)

    def _fit_emission_model(
        self,
        frame: pd.DataFrame,
        *,
        priors: dict[str, float],
        holding_time_seconds: dict[str, float],
        duration_shapes: dict[str, float] | None = None,
    ) -> tuple[RegimeEmissionModel, dict[str, object]]:
        regime_order = tuple(regime.value for regime in MicrostructureRegime)
        feature_names = self.emission_features
        observations = [
            tuple(float(row[name]) for name in feature_names)
            for row in frame.to_dict(orient="records")
        ]
        labels = [str(value) for value in frame["dominant_regime"].tolist()]
        timestamps = (
            [int(value) for value in frame["timestamp_ns"].tolist()]
            if "timestamp_ns" in frame.columns
            else None
        )

        # Hard init from pseudo-labels (heuristic MAP regimes on the panel).
        responsibilities = self._hard_responsibilities(labels, regime_order)
        means: dict[str, tuple[float, ...]] = {}
        stds: dict[str, tuple[float, ...]] = {}
        weights: dict[str, float] = {}
        log_likelihood = float("-inf")
        shapes = duration_shapes or {
            regime: float(self.regime_config.default_duration_shape) for regime in regime_order
        }

        for _ in range(self.em_iterations):
            means, stds, weights = self._m_step(observations, responsibilities, regime_order, feature_names)
            responsibilities, log_likelihood = self._e_step(
                observations,
                means=means,
                stds=stds,
                priors=priors,
                holding_time_seconds=holding_time_seconds,
                duration_shapes=shapes,
                regime_order=regime_order,
                timestamps=timestamps,
            )

        model = RegimeEmissionModel(
            feature_names=feature_names,
            means=means,
            stds=stds,
            effective_weight=weights,
        )
        meta = {
            "emission_em_iterations": self.em_iterations,
            "emission_feature_names": feature_names,
            "emission_log_likelihood": float(log_likelihood),
            "emission_effective_weight": dict(weights),
            "emission_uses_timestamps": timestamps is not None,
        }
        return model, meta

    def _hard_responsibilities(
        self,
        labels: list[str],
        regime_order: tuple[str, ...],
    ) -> list[dict[str, float]]:
        floor = self.regime_config.posterior_floor
        responsibilities: list[dict[str, float]] = []
        for label in labels:
            row = {regime: floor for regime in regime_order}
            if label in row:
                row[label] = 1.0
            else:
                # Unknown label → uniform
                uniform = 1.0 / len(regime_order)
                row = {regime: uniform for regime in regime_order}
            total = sum(row.values())
            responsibilities.append({regime: value / total for regime, value in row.items()})
        return responsibilities

    def _m_step(
        self,
        observations: list[tuple[float, ...]],
        responsibilities: list[dict[str, float]],
        regime_order: tuple[str, ...],
        feature_names: tuple[str, ...],
    ) -> tuple[dict[str, tuple[float, ...]], dict[str, tuple[float, ...]], dict[str, float]]:
        dimension = len(feature_names)
        means: dict[str, tuple[float, ...]] = {}
        stds: dict[str, tuple[float, ...]] = {}
        weights: dict[str, float] = {}
        global_mean = [0.0] * dimension
        if observations:
            for observation in observations:
                for index, value in enumerate(observation):
                    global_mean[index] += value
            global_mean = [value / len(observations) for value in global_mean]
        else:
            global_mean = [0.0] * dimension

        for regime in regime_order:
            weight = sum(row[regime] for row in responsibilities)
            weights[regime] = float(weight)
            if weight < self.min_regime_weight:
                means[regime] = tuple(global_mean)
                stds[regime] = tuple(1.0 for _ in range(dimension))
                continue

            mean_vector = [0.0] * dimension
            for observation, row in zip(observations, responsibilities):
                responsibility = row[regime]
                for index, value in enumerate(observation):
                    mean_vector[index] += responsibility * value
            mean_vector = [value / weight for value in mean_vector]
            means[regime] = tuple(mean_vector)

            second_moment = [0.0] * dimension
            for observation, row in zip(observations, responsibilities):
                responsibility = row[regime]
                for index, value in enumerate(observation):
                    delta = value - mean_vector[index]
                    second_moment[index] += responsibility * delta * delta
            std_vector = [
                max(sqrt(second_moment[index] / weight), self.min_emission_std)
                for index in range(dimension)
            ]
            stds[regime] = tuple(std_vector)

        return means, stds, weights

    def _e_step(
        self,
        observations: list[tuple[float, ...]],
        *,
        means: dict[str, tuple[float, ...]],
        stds: dict[str, tuple[float, ...]],
        priors: dict[str, float],
        holding_time_seconds: dict[str, float],
        duration_shapes: dict[str, float],
        regime_order: tuple[str, ...],
        timestamps: list[int] | None,
    ) -> tuple[list[dict[str, float]], float]:
        floor = self.regime_config.posterior_floor
        responsibilities: list[dict[str, float]] = []
        previous: dict[str, float] | None = None
        previous_timestamp: int | None = None
        dominant_regime: str | None = None
        regime_started_at_ns: int | None = None
        total_log_likelihood = 0.0
        leave_weights = leave_weight_rows(priors, regime_order, floor=floor)
        holding_times_ns = {
            regime: max(int(float(holding_time_seconds.get(regime, 1.0)) * 1_000_000_000), 1)
            for regime in regime_order
        }
        use_hsmm = any(float(duration_shapes.get(regime, 1.0)) != 1.0 for regime in regime_order)

        for index, observation in enumerate(observations):
            log_likelihoods = {
                regime: diagonal_gaussian_log_likelihood(
                    observation,
                    means[regime],
                    stds[regime],
                )
                for regime in regime_order
            }
            if previous is None or timestamps is None:
                predicted = {
                    regime: max(float(priors.get(regime, floor)), floor)
                    for regime in regime_order
                }
            else:
                dt_ns = max(int(timestamps[index] - (previous_timestamp or timestamps[index])), 0)
                dwell_ns = 0
                if (
                    dominant_regime is not None
                    and regime_started_at_ns is not None
                    and previous_timestamp is not None
                ):
                    dwell_ns = max(int(previous_timestamp - regime_started_at_ns), 0)
                predicted = predict_regime_probabilities(
                    previous,
                    regime_order=regime_order,
                    dt_ns=dt_ns,
                    holding_times_ns=holding_times_ns,
                    duration_shapes=duration_shapes,
                    leave_weights=leave_weights,
                    dominant_regime=dominant_regime,
                    dwell_ns=dwell_ns,
                    use_hsmm=use_hsmm,
                    floor=floor,
                )

            # Bayes update: predicted prior × emission likelihood (in log space).
            log_unnormalized = {
                regime: log(max(predicted[regime], floor)) + log_likelihoods[regime]
                for regime in regime_order
            }
            max_log = max(log_unnormalized.values())
            unnormalized = {
                regime: exp(value - max_log)
                for regime, value in log_unnormalized.items()
            }
            total = sum(unnormalized.values())
            if total <= 0.0:
                filtered = {regime: 1.0 / len(regime_order) for regime in regime_order}
                row_ll = max_log
            else:
                filtered = {
                    regime: max(value / total, floor)
                    for regime, value in unnormalized.items()
                }
                renorm = sum(filtered.values())
                filtered = {regime: value / renorm for regime, value in filtered.items()}
                row_ll = max_log + log(total)

            responsibilities.append(filtered)
            total_log_likelihood += float(row_ll)
            new_dominant = max(filtered, key=filtered.get)
            timestamp = timestamps[index] if timestamps is not None else 0
            if dominant_regime != new_dominant:
                dominant_regime = new_dominant
                regime_started_at_ns = timestamp
            previous = filtered
            if timestamps is not None:
                previous_timestamp = timestamps[index]

        return responsibilities, total_log_likelihood

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


