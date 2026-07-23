"""Leakage-bounded orchestration for fitting a complete v2 engine bundle."""

from __future__ import annotations

from bisect import bisect_left
from typing import Iterable, Iterator

from l1_microstructure.calibration.interfaces import ExecutionCalibrationArtifact, StateCalibrationArtifact
from l1_microstructure.config import FrameworkConfig
from l1_microstructure.features import ObservedState
from l1_microstructure.training.interfaces import TransitionTrainingSample

from .edges import HierarchicalTransitionTrainer
from .engine import TransparentEngineArtifacts
from .regime import SemiMarkovRegimeRuntime, SemiMarkovRegimeTrainer
from .utility import UtilityCalibrationSample, UtilityModel, UtilityModelTrainer
from .vector import RobustStateVectorRuntime, RobustStateVectorTrainer


class TransparentModelTrainer:
    def __init__(
        self,
        *,
        vector_trainer: RobustStateVectorTrainer | None = None,
        regime_trainer: SemiMarkovRegimeTrainer | None = None,
        transition_trainer: HierarchicalTransitionTrainer | None = None,
        utility_trainer: UtilityModelTrainer | None = None,
    ) -> None:
        self.vector_trainer = vector_trainer or RobustStateVectorTrainer()
        self.regime_trainer = regime_trainer or SemiMarkovRegimeTrainer()
        self.transition_trainer = transition_trainer or HierarchicalTransitionTrainer()
        self.utility_trainer = utility_trainer

    def fit(
        self,
        states: Iterable[ObservedState],
        *,
        state_calibration: StateCalibrationArtifact,
        execution_calibration: ExecutionCalibrationArtifact,
        train_start_ns: int,
        train_end_ns: int,
        config: FrameworkConfig | None = None,
        utility_samples: Iterable[UtilityCalibrationSample] | None = None,
    ) -> TransparentEngineArtifacts:
        observations = tuple(states)
        if not observations:
            raise ValueError("transparent model training requires observed states")
        framework_config = config or FrameworkConfig()
        if any(not train_start_ns <= state.timestamp_ns <= train_end_ns for state in observations):
            raise ValueError("transparent model state crosses the declared training boundary")
        if {state.symbol for state in observations} != {state_calibration.symbol, execution_calibration.symbol}:
            raise ValueError("transparent training artifacts and states must share one symbol")
        targets = _persistence_targets(
            observations,
            framework_config.transition.drift_horizon_ns,
            framework_config.decision.transaction_cost_bps,
        )
        vector_model = self.vector_trainer.fit(
            observations,
            targets,
            train_start_ns=train_start_ns,
            train_end_ns=train_end_ns,
        )
        regime_model = self.regime_trainer.fit(
            observations,
            vector_model,
            train_start_ns=train_start_ns,
            train_end_ns=train_end_ns,
        )
        transition_samples = candidate_transition_samples(
            observations,
            vector_model,
            regime_model,
            framework_config,
        )
        transition_model = self.transition_trainer.fit(
            transition_samples,
            train_start_ns=train_start_ns,
            train_end_ns=train_end_ns,
        )
        provided_utility_samples = tuple(utility_samples or ())
        if provided_utility_samples:
            trainer = self.utility_trainer or UtilityModelTrainer(
                fixed_cost_bps=framework_config.decision.transaction_cost_bps
            )
            utility_model = trainer.fit(
                provided_utility_samples,
                symbol=state_calibration.symbol,
                train_start_ns=train_start_ns,
                train_end_ns=train_end_ns,
            )
        else:
            utility_model = UtilityModel.from_execution_calibration(
                execution_calibration,
                transition_model.horizons_ns,
                train_start_ns=train_start_ns,
                train_end_ns=train_end_ns,
                fixed_cost_bps=framework_config.decision.transaction_cost_bps,
            )
        return TransparentEngineArtifacts(
            state_vector_model=vector_model,
            semi_markov_regime_model=regime_model,
            hierarchical_transition_model=transition_model,
            utility_model=utility_model,
            state_calibration=state_calibration,
            execution_calibration=execution_calibration,
            metadata={
                "trainer": "transparent_model_trainer",
                "train_start_ns": int(train_start_ns),
                "train_end_ns": int(train_end_ns),
                "candidate_transition_sample_count": transition_model.sample_count,
            },
        )


def _persistence_targets(
    states: tuple[ObservedState, ...],
    horizon_ns: int,
    cost_threshold_bps: float,
) -> tuple[bool | None, ...]:
    timestamps = tuple(state.timestamp_ns for state in states)
    targets: list[bool | None] = []
    for index in range(1, len(states)):
        current = states[index]
        future_index = bisect_left(timestamps, current.timestamp_ns + horizon_ns, lo=index + 1)
        if future_index >= len(states):
            targets.append(None)
            continue
        future = states[future_index]
        drift = abs((future.book.microprice - current.book.microprice) / current.book.microprice * 10_000.0)
        state_changed = current.label != states[index - 1].label
        state_persisted = future.label == current.label
        targets.append(bool(state_changed and state_persisted and drift > cost_threshold_bps))
    return tuple(targets)


def candidate_transition_samples(
    states: tuple[ObservedState, ...],
    vector_model,
    regime_model,
    config: FrameworkConfig,
) -> Iterator[TransitionTrainingSample]:
    timestamps = tuple(state.timestamp_ns for state in states)
    vector_runtime = RobustStateVectorRuntime(vector_model)
    regime_runtime = SemiMarkovRegimeRuntime(regime_model, vector_model)
    for index, state in enumerate(states):
        regime = regime_runtime.update(state)
        transition = vector_runtime.update(state)
        if index == 0:
            continue
        previous = states[index - 1]
        for horizon_ns in config.transition.drift_horizon_ns_values:
            end_index = bisect_left(timestamps, state.timestamp_ns + horizon_ns, lo=index + 1)
            if end_index >= len(states):
                continue
            end_state = states[end_index]
            drift_bps = (end_state.book.microprice - state.book.microprice) / state.book.microprice * 10_000.0
            yield TransitionTrainingSample(
                symbol=state.symbol,
                from_state=previous.label,
                to_state=state.label,
                regime=regime.dominant_regime,
                horizon_ns=horizon_ns,
                holding_time_ns=state.timestamp_ns - previous.timestamp_ns,
                realized_drift_bps=float(drift_bps),
                metadata={
                    "timestamp_ns": state.timestamp_ns,
                    "end_timestamp_ns": end_state.timestamp_ns,
                    "threshold_bps": config.decision.transaction_cost_bps
                    + config.decision.risk_premium_bps
                    * max(state.realized_volatility * 10_000.0, 0.1),
                    "vector_transition_detected": transition.is_transition,
                    "transition_probability": transition.probability,
                    "transition_score": transition.score,
                },
            )
