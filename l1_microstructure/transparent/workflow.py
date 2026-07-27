"""Leakage-bounded rolling research workflow for the v2 engine."""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd

from l1_microstructure.artifacts import LocalArtifactStore, RuntimeArtifactBundle
from l1_microstructure.calibration import (
    CalibrationDataset,
    EmpiricalExecutionCalibrator,
    EmpiricalRegimeCalibrator,
    ExecutionCalibrationDataset,
    QuantileStateCalibrator,
    StateCalibrationArtifact,
)
from l1_microstructure.config import FrameworkConfig
from l1_microstructure.datasets import PipelineTransitionDatasetBuilder
from l1_microstructure.events import MarketEvent, event_sort_key
from l1_microstructure.features import FeatureEngine, ObservedState
from l1_microstructure.training import EmpiricalTransitionTrainer
from l1_microstructure.validation import RegimeSplitSpec

from .artifacts import TransparentArtifactPublisher, TransparentRunManifest
from .contracts import PromotionThresholds
from .engine import TransparentEngineArtifacts
from .shadow import ComparativeShadowRunner, ShadowReport
from .training import TransparentModelTrainer
from .validation import (
    TransparentOOSValidationReport,
    TransparentOOSValidator,
    ValidationSplitEvidence,
    build_common_opportunity_samples,
)


@dataclass(frozen=True, slots=True)
class TransparentWorkflowResult:
    symbol: str
    run_id: str
    artifacts: TransparentEngineArtifacts
    validation_report: TransparentOOSValidationReport
    manifest: TransparentRunManifest
    split_count: int


@dataclass(frozen=True, slots=True)
class _FittedWindow:
    candidate: TransparentEngineArtifacts
    baseline: RuntimeArtifactBundle
    baseline_transition_payload: dict[str, object]
    states: tuple[ObservedState, ...]


class TransparentArtifactDrivenWorkflow:
    """Fit every rolling split from scratch, compare, then publish immutably."""

    def __init__(
        self,
        artifact_root: str | Path,
        *,
        framework_config: FrameworkConfig | None = None,
        model_trainer: TransparentModelTrainer | None = None,
        promotion_thresholds: PromotionThresholds | None = None,
        minimum_split_count: int = 2,
    ) -> None:
        self.config = framework_config or FrameworkConfig()
        self.model_trainer = model_trainer or TransparentModelTrainer()
        self.validator = TransparentOOSValidator(
            promotion_thresholds,
            minimum_split_count=minimum_split_count,
        )
        self.store = LocalArtifactStore(artifact_root)

    def run(
        self,
        *,
        symbol: str,
        events: Iterable[MarketEvent],
        splits: list[RegimeSplitSpec] | None = None,
        run_id: str | None = None,
    ) -> TransparentWorkflowResult:
        normalized = sorted(
            (event for event in events if event.symbol == symbol),
            key=event_sort_key,
        )
        if not normalized:
            raise ValueError(f"no events supplied for symbol {symbol}")
        timestamps = tuple(event.timestamp_ns for event in normalized)
        effective_splits = splits or self._default_splits(timestamps)
        evidence: list[ValidationSplitEvidence] = []
        split_models: dict[str, tuple[dict[str, object], object, object]] = {}
        shadow_reports: list[ShadowReport] = []
        seen_labels: set[str] = set()
        for split in effective_splits:
            if split.label in seen_labels:
                raise ValueError(f"duplicate transparent validation split label: {split.label}")
            seen_labels.add(split.label)
            train_start_ns = self._timestamp_ns(split.train_start)
            train_end_ns = self._timestamp_ns(split.train_end)
            test_start_ns = self._timestamp_ns(split.test_start)
            test_end_ns = self._timestamp_ns(split.test_end)
            if train_end_ns >= test_start_ns:
                raise ValueError(f"transparent validation split {split.label} overlaps train and test")
            train_events = self._events_for_window(
                normalized, timestamps, train_start_ns, train_end_ns
            )
            test_events = self._events_for_window(
                normalized, timestamps, test_start_ns, test_end_ns
            )
            fitted = self._fit_window(
                symbol=symbol,
                events=train_events,
                train_start_ns=train_start_ns,
                train_end_ns=train_end_ns,
            )
            # This is a new feature engine, vector runtime, and HSMM for every
            # held-out window. No rolling state can cross train/test boundaries.
            test_states = self._states(test_events, fitted.candidate.state_calibration)
            samples = build_common_opportunity_samples(
                test_states,
                candidate_vector_model=fitted.candidate.state_vector_model,
                candidate_regime_model=fitted.candidate.semi_markov_regime_model,
                baseline_regime_calibration=fitted.baseline.regime_calibration,
                baseline_transition_payload=fitted.baseline_transition_payload,
                config=self.config,
            )
            evidence.append(
                ValidationSplitEvidence(
                    label=split.label,
                    test_start_ns=test_start_ns,
                    test_end_ns=test_end_ns,
                    samples=samples,
                )
            )
            split_models[split.label] = (
                fitted.baseline_transition_payload,
                fitted.candidate.hierarchical_transition_model,
                fitted.candidate.utility_model,
            )
            shadow_reports.append(
                ComparativeShadowRunner(
                    baseline_artifacts=fitted.baseline,
                    candidate_artifacts=fitted.candidate,
                    config=self.config,
                ).run(test_events)
            )

        report = self.validator.evaluate(
            models_by_split=split_models,
            splits=evidence,
            config=self.config,
            shadow_reports=shadow_reports,
        )
        final_artifacts = self._fit_window(
            symbol=symbol,
            events=normalized,
            train_start_ns=timestamps[0],
            train_end_ns=timestamps[-1],
        ).candidate
        resolved_run_id = run_id or self._run_id(symbol)
        manifest = TransparentArtifactPublisher(self.store).publish(
            run_id=resolved_run_id,
            trade_date=datetime.fromtimestamp(
                timestamps[0] / 1_000_000_000.0, tz=timezone.utc
            ).date().isoformat(),
            artifacts=final_artifacts,
            validation_report=report.to_dict(),
        )
        return TransparentWorkflowResult(
            symbol=symbol,
            run_id=resolved_run_id,
            artifacts=final_artifacts,
            validation_report=report,
            manifest=manifest,
            split_count=len(effective_splits),
        )

    def _fit_window(
        self,
        *,
        symbol: str,
        events: list[MarketEvent],
        train_start_ns: int,
        train_end_ns: int,
    ) -> _FittedWindow:
        if not events:
            raise ValueError("transparent training window contains no events")
        state_panel, transition_panel = PipelineTransitionDatasetBuilder(
            events, config=self.config
        ).build_panels_single_pass(symbol)
        if state_panel.frame.empty or transition_panel.frame.empty:
            raise ValueError("transparent training window produced an empty panel")
        transition_frame = self._resolved_training_rows(
            transition_panel.frame,
            train_start_ns=train_start_ns,
            train_end_ns=train_end_ns,
        )
        fitted_state_calibration = QuantileStateCalibrator().fit(
            CalibrationDataset(symbol, state_panel.frame, state_panel.metadata)
        )
        # V2 keeps state quantization global. Feeding an inferred regime back
        # into feature scaling creates a cyclic train/runtime dependency and
        # makes identical market observations model-state dependent.
        state_calibration = StateCalibrationArtifact(
            symbol=fitted_state_calibration.symbol,
            spread_quantiles=fitted_state_calibration.spread_quantiles,
            volatility_quantiles=fitted_state_calibration.volatility_quantiles,
            flicker_baseline=fitted_state_calibration.flicker_baseline,
            quote_pressure_scale=fitted_state_calibration.quote_pressure_scale,
            regime_surfaces={},
            metadata={
                **fitted_state_calibration.metadata,
                "transparent_global_quantization": True,
            },
        )
        regime_calibration = EmpiricalRegimeCalibrator().fit(
            CalibrationDataset(symbol, state_panel.frame, state_panel.metadata)
        )
        execution_calibration = EmpiricalExecutionCalibrator().fit(
            ExecutionCalibrationDataset(
                symbol,
                state_panel.frame,
                transition_frame,
                {
                    "state_panel_rows": len(state_panel.frame),
                    "transition_panel_rows": len(transition_frame),
                    "train_start_ns": train_start_ns,
                    "train_end_ns": train_end_ns,
                },
            )
        )
        baseline_trainer = EmpiricalTransitionTrainer(version="v1")
        baseline_trainer.fit(
            baseline_trainer.samples_from_frame(transition_frame),
            runtime_horizon_ns=self.config.transition.drift_horizon_ns,
        )
        if baseline_trainer.last_payload is None:
            raise ValueError("baseline transition training produced no payload")
        states = self._states(events, state_calibration)
        candidate = self.model_trainer.fit(
            states,
            state_calibration=state_calibration,
            execution_calibration=execution_calibration,
            train_start_ns=train_start_ns,
            train_end_ns=train_end_ns,
            config=self.config,
        )
        baseline = RuntimeArtifactBundle(
            state_calibration=fitted_state_calibration,
            regime_calibration=regime_calibration,
            execution_calibration=execution_calibration,
            transition_model=baseline_trainer.last_payload,
            metadata={
                "engine_version": "v1",
                "train_start_ns": train_start_ns,
                "train_end_ns": train_end_ns,
            },
        )
        return _FittedWindow(candidate, baseline, baseline_trainer.last_payload, states)

    def _states(
        self,
        events: Iterable[MarketEvent],
        state_calibration,
    ) -> tuple[ObservedState, ...]:
        engine = FeatureEngine(self.config.feature, state_calibration)
        states = [state for event in events if (state := engine.update(event)) is not None]
        if not states:
            raise ValueError("transparent feature fitting produced no states")
        return tuple(states)

    @staticmethod
    def _resolved_training_rows(
        frame: pd.DataFrame,
        *,
        train_start_ns: int,
        train_end_ns: int,
    ) -> pd.DataFrame:
        required = {"timestamp_ns", "end_timestamp_ns", "censored", "realized_drift_bps"}
        missing = sorted(required.difference(frame.columns))
        if missing:
            raise ValueError(f"transition panel is missing resolution fields: {missing}")
        resolved = frame[
            (~frame["censored"].astype(bool))
            & frame["realized_drift_bps"].notna()
            & frame["end_timestamp_ns"].notna()
            & (frame["timestamp_ns"] >= train_start_ns)
            & (frame["end_timestamp_ns"] <= train_end_ns)
        ].copy()
        if resolved.empty:
            raise ValueError("training window has no labels resolved before its boundary")
        return resolved

    @staticmethod
    def _timestamp_ns(value: str) -> int:
        timestamp = pd.Timestamp(value)
        timestamp = timestamp.tz_localize("UTC") if timestamp.tzinfo is None else timestamp.tz_convert("UTC")
        return int(timestamp.value)

    @staticmethod
    def _events_for_window(
        events: list[MarketEvent],
        timestamps: tuple[int, ...],
        start_ns: int,
        end_ns: int,
    ) -> list[MarketEvent]:
        return events[bisect_left(timestamps, start_ns) : bisect_right(timestamps, end_ns)]

    @staticmethod
    def _default_splits(timestamps: tuple[int, ...]) -> list[RegimeSplitSpec]:
        if len(timestamps) < 10:
            raise ValueError("default transparent validation requires at least ten events")
        fractions = ((0.4, 0.6), (0.6, 0.8), (0.8, 1.0))
        splits: list[RegimeSplitSpec] = []
        for index, (train_fraction, test_fraction) in enumerate(fractions, start=1):
            train_end_index = min(max(int(len(timestamps) * train_fraction) - 1, 0), len(timestamps) - 2)
            test_end_index = min(max(int(len(timestamps) * test_fraction) - 1, train_end_index + 1), len(timestamps) - 1)
            splits.append(
                RegimeSplitSpec(
                    train_start=pd.Timestamp(timestamps[0], unit="ns", tz="UTC").isoformat(),
                    train_end=pd.Timestamp(timestamps[train_end_index], unit="ns", tz="UTC").isoformat(),
                    test_start=pd.Timestamp(timestamps[train_end_index + 1], unit="ns", tz="UTC").isoformat(),
                    test_end=pd.Timestamp(timestamps[test_end_index], unit="ns", tz="UTC").isoformat(),
                    label=f"rolling-{index}",
                )
            )
        return splits

    @staticmethod
    def _run_id(symbol: str) -> str:
        return f"{symbol.lower()}-v2-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}"
