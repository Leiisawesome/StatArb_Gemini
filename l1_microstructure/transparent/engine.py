"""Integrated version-two transparent statistical state engine."""

from __future__ import annotations

from dataclasses import dataclass, field

from l1_microstructure.calibration.interfaces import ExecutionCalibrationArtifact, StateCalibrationArtifact
from l1_microstructure.config import FrameworkConfig
from l1_microstructure.decision import TradeAction
from l1_microstructure.events import MarketEvent
from l1_microstructure.features import FeatureEngine, ObservedState

from .contracts import TRANSPARENT_ENGINE_VERSION
from .edges import (
    HierarchicalDriftPosterior,
    HierarchicalTransitionModel,
    HierarchicalTransitionRuntime,
)
from .outcomes import MultiHorizonOutcomeTracker, ResolvedHorizonOutcome
from .regime import SemiMarkovRegimeModel, SemiMarkovRegimePosterior, SemiMarkovRegimeRuntime
from .utility import ExpectedUtilityDecisionEngine, UtilityDecision, UtilityModel
from .vector import RobustStateVectorRuntime, StateVectorModel, TransitionEvidence


@dataclass(frozen=True, slots=True)
class TransparentEngineArtifacts:
    state_vector_model: StateVectorModel
    semi_markov_regime_model: SemiMarkovRegimeModel
    hierarchical_transition_model: HierarchicalTransitionModel
    utility_model: UtilityModel
    state_calibration: StateCalibrationArtifact | None = None
    execution_calibration: ExecutionCalibrationArtifact | None = None
    artifact_ids: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)
    engine_version: str = TRANSPARENT_ENGINE_VERSION

    def __post_init__(self) -> None:
        if self.engine_version != TRANSPARENT_ENGINE_VERSION:
            raise ValueError("transparent engine artifacts require engine version v2")
        symbols = {
            self.state_vector_model.symbol,
            self.semi_markov_regime_model.symbol,
            self.hierarchical_transition_model.symbol,
            self.utility_model.symbol,
        }
        if self.state_calibration is not None:
            symbols.add(self.state_calibration.symbol)
        if self.execution_calibration is not None:
            symbols.add(self.execution_calibration.symbol)
        if self.state_calibration is not None and self.state_calibration.regime_surfaces:
            raise ValueError(
                "transparent v2 requires global state calibration; regime surfaces create cyclic features"
            )
        if len(symbols) != 1:
            raise ValueError(f"transparent artifacts contain multiple symbols: {sorted(symbols)}")
        if self.state_vector_model.feature_names != self.semi_markov_regime_model.feature_names:
            raise ValueError("transparent vector and regime feature contracts differ")
        if set(self.hierarchical_transition_model.horizons_ns) != {
            int(key) for key in self.utility_model.slippage_bps_by_horizon
        }:
            raise ValueError("transparent transition and utility horizons differ")

    @property
    def symbol(self) -> str:
        return self.state_vector_model.symbol


@dataclass(frozen=True, slots=True)
class TransparentFrameworkUpdate:
    state: ObservedState
    regime: SemiMarkovRegimePosterior
    transition: TransitionEvidence
    posteriors: tuple[HierarchicalDriftPosterior, ...]
    decision: UtilityDecision | None
    resolved_outcomes: tuple[ResolvedHorizonOutcome, ...]
    shadow_only: bool = True

    @property
    def action(self) -> TradeAction:
        return TradeAction.HOLD if self.decision is None else self.decision.action


class TransparentStatisticalEngine:
    """V2 inference engine. It intentionally owns no order-routing capability."""

    def __init__(
        self,
        artifacts: TransparentEngineArtifacts,
        config: FrameworkConfig | None = None,
    ) -> None:
        self.artifacts = artifacts
        self.config = config or FrameworkConfig()
        self.feature_engine = FeatureEngine(self.config.feature, artifacts.state_calibration)
        self.vector_runtime = RobustStateVectorRuntime(artifacts.state_vector_model)
        self.regime_runtime = SemiMarkovRegimeRuntime(
            artifacts.semi_markov_regime_model,
            artifacts.state_vector_model,
        )
        self.transition_runtime = HierarchicalTransitionRuntime(
            HierarchicalTransitionModel.from_dict(artifacts.hierarchical_transition_model.to_dict())
        )
        self.outcomes = MultiHorizonOutcomeTracker(artifacts.hierarchical_transition_model.horizons_ns)
        self.utility_engine = ExpectedUtilityDecisionEngine(artifacts.utility_model)
        self.previous_state: ObservedState | None = None

    def on_event(self, event: MarketEvent) -> TransparentFrameworkUpdate | None:
        state = self.feature_engine.update(event)
        return None if state is None else self.on_state(state)

    def on_state(
        self,
        state: ObservedState,
        *,
        alignment_probability: float = 1.0,
        current_risk_fraction: float = 0.0,
    ) -> TransparentFrameworkUpdate:
        if state.symbol != self.artifacts.symbol:
            raise ValueError(f"transparent engine for {self.artifacts.symbol} cannot process {state.symbol}")
        resolved = self.outcomes.resolve(state)
        for outcome in resolved:
            self.transition_runtime.observe(
                from_state=outcome.from_state,
                to_state=outcome.to_state,
                regime=outcome.regime,
                horizon_ns=outcome.horizon_ns,
                drift_bps=outcome.realized_drift_bps,
                holding_time_ns=outcome.holding_time_ns,
            )
        regime = self.regime_runtime.update(state)
        self.feature_engine.set_regime_hint(regime.dominant_regime)
        transition = self.vector_runtime.update(state)
        posteriors: tuple[HierarchicalDriftPosterior, ...] = ()
        decision: UtilityDecision | None = None
        if self.previous_state is not None and transition.is_transition:
            threshold_bps = self.config.decision.transaction_cost_bps + self.config.decision.risk_premium_bps * max(
                state.realized_volatility * 10_000.0,
                0.1,
            )
            posteriors = tuple(
                self.transition_runtime.posterior(
                    from_state=self.previous_state.label,
                    to_state=state.label,
                    regime=regime.dominant_regime,
                    horizon_ns=horizon_ns,
                    threshold_bps=threshold_bps,
                )
                for horizon_ns in self.artifacts.hierarchical_transition_model.horizons_ns
            )
            decision = self.utility_engine.decide(
                posteriors,
                state,
                alignment_probability=alignment_probability,
                transition_probability=transition.probability,
                current_risk_fraction=current_risk_fraction,
                regime=regime.dominant_regime,
            )
            self.outcomes.schedule(
                state=state,
                from_state=self.previous_state.label,
                to_state=state.label,
                regime=regime.dominant_regime,
                holding_time_ns=state.timestamp_ns - self.previous_state.timestamp_ns,
            )
        self.previous_state = state
        return TransparentFrameworkUpdate(
            state=state,
            regime=regime,
            transition=transition,
            posteriors=posteriors,
            decision=decision,
            resolved_outcomes=resolved,
        )

    def snapshot_outcomes(self) -> dict[str, object]:
        return self.outcomes.snapshot()

    def restore_outcomes(self, payload: dict[str, object]) -> None:
        restored = MultiHorizonOutcomeTracker.restore(payload)
        if restored.horizons_ns != self.outcomes.horizons_ns:
            raise ValueError("transparent recovery horizons do not match loaded artifacts")
        if restored.max_pending_outcomes != self.outcomes.max_pending_outcomes:
            raise ValueError("transparent recovery pending-outcome bound does not match runtime")
        self.outcomes = restored
