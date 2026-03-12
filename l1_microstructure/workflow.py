"""Artifact-producing research workflow for the successor package."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo

import pandas as pd

from .artifacts import ArtifactBundleLoader, ArtifactMetadata, LocalArtifactStore, RuntimeArtifactBundle
from .config import FrameworkConfig
from .datasets import PipelineTransitionDatasetBuilder
from .events import MarketEvent
from .live import RunnerConfig, SimulatorPaperTradingRunner
from .monitoring import InMemoryMonitoringSink
from .validation import RegimeSplitSpec, RollingValidationHarness, ValidationReport
from .calibration import (
    CalibrationDataset,
    EmpiricalExecutionCalibrator,
    EmpiricalRegimeCalibrator,
    ExecutionCalibrationDataset,
    QuantileStateCalibrator,
)
from .training import EmpiricalTransitionTrainer


@dataclass(frozen=True, slots=True)
class WorkflowArtifactIds:
    state_calibration_id: str
    regime_calibration_id: str
    execution_calibration_id: str
    transition_model_id: str
    validation_report_id: str
    monitored_replay_id: str
    run_manifest_id: str


@dataclass(frozen=True, slots=True)
class WorkflowRunResult:
    symbol: str
    run_id: str
    state_panel_rows: int
    transition_panel_rows: int
    artifact_ids: WorkflowArtifactIds
    validation_report: ValidationReport
    replay_summary: dict[str, float]


class ArtifactDrivenResearchWorkflow:
    def __init__(
        self,
        artifact_root: str | Path,
        framework_config: FrameworkConfig | None = None,
        validation_harness: RollingValidationHarness | None = None,
        version: str = "v1",
    ):
        self.framework_config = framework_config or FrameworkConfig()
        self.validation_harness = validation_harness or RollingValidationHarness()
        self.version = version
        self.store = LocalArtifactStore(artifact_root)

    def run(
        self,
        *,
        symbol: str,
        events: Iterable[MarketEvent],
        splits: list[RegimeSplitSpec] | None = None,
        runner_config: RunnerConfig | None = None,
    ) -> WorkflowRunResult:
        normalized_events = [event for event in events if event.symbol == symbol]
        if not normalized_events:
            raise ValueError(f"no events supplied for symbol {symbol}")

        run_id = self._run_id(symbol)
        trade_date = self._trade_date(normalized_events)
        full_state_panel, full_transition_panel = self._build_panels(symbol=symbol, events=normalized_events)

        # Ensure horizon_ns is properly typed before filtering
        transition_frame = full_transition_panel.frame.copy()
        transition_frame["horizon_ns"] = pd.to_numeric(transition_frame["horizon_ns"], errors="coerce").fillna(0).astype(int)
        target_horizon = int(self.framework_config.transition.drift_horizon_ns)

        runtime_transition_frame = transition_frame[
            transition_frame["horizon_ns"] == target_horizon
        ].copy()
        if runtime_transition_frame.empty:
            raise ValueError(f"no transition rows found for runtime horizon {self.framework_config.transition.drift_horizon_ns}")
        runtime_transition_frame["timestamp"] = pd.to_datetime(runtime_transition_frame["timestamp_ns"], unit="ns", utc=True)
        effective_splits = splits or self._default_splits(runtime_transition_frame)

        validation_runner_config = runner_config or RunnerConfig(
            symbols=(symbol,),
            mode="paper",
            latency_ms=self.framework_config.execution.latency_ms,
        )
        validation_report, validation_monitoring_frame = self._run_oos_validation(
            symbol=symbol,
            events=normalized_events,
            validation_frame=runtime_transition_frame,
            splits=effective_splits,
            runner_config=validation_runner_config,
        )

        (
            state_panel,
            transition_panel,
            state_artifact,
            regime_artifact,
            execution_artifact,
            transition_payload,
        ) = self._fit_runtime_artifacts(symbol=symbol, events=normalized_events)

        state_calibration_id = self._save_artifact(
            artifact_id=f"{run_id}-{symbol}-state-calibration",
            artifact_type="state_calibration",
            payload=asdict(state_artifact),
            metadata={"symbol": symbol, "run_id": run_id},
        )
        regime_calibration_id = self._save_artifact(
            artifact_id=f"{run_id}-{symbol}-regime-calibration",
            artifact_type="regime_calibration",
            payload=asdict(regime_artifact),
            metadata={"symbol": symbol, "run_id": run_id},
        )
        execution_calibration_id = self._save_artifact(
            artifact_id=f"{run_id}-{symbol}-execution-calibration",
            artifact_type="execution_calibration",
            payload=asdict(execution_artifact),
            metadata={"symbol": symbol, "run_id": run_id},
        )

        # Ensure horizon_ns is properly typed before filtering
        training_transition_frame = transition_panel.frame.copy()
        training_transition_frame["horizon_ns"] = pd.to_numeric(training_transition_frame["horizon_ns"], errors="coerce").fillna(0).astype(int)
        target_horizon = int(self.framework_config.transition.drift_horizon_ns)

        runtime_training_transition_frame = training_transition_frame[
            training_transition_frame["horizon_ns"] == target_horizon
        ].copy()
        transition_model_id = self._save_artifact(
            artifact_id=f"{run_id}-{symbol}-transition-model",
            artifact_type="transition_model",
            payload=transition_payload,
            metadata={
                "symbol": symbol,
                "run_id": run_id,
                "trainer_model_id": str(transition_payload["model_id"]),
                "runtime_horizon_ns": self.framework_config.transition.drift_horizon_ns,
            },
        )

        bundle = ArtifactBundleLoader(self.store).load_runtime_bundle(
            state_calibration_id=state_calibration_id,
            regime_calibration_id=regime_calibration_id,
            execution_calibration_id=execution_calibration_id,
            transition_model_id=transition_model_id,
        )
        monitoring_sink = InMemoryMonitoringSink()
        runner = SimulatorPaperTradingRunner(
            events=normalized_events,
            framework_config=self.framework_config,
            runtime_artifacts=bundle,
            monitoring_sink=monitoring_sink,
        )
        runner.start(validation_runner_config)
        replay_summary = runner.execution_summary()
        validation_report_id = self._save_artifact(
            artifact_id=f"{run_id}-{symbol}-validation-report",
            artifact_type="validation_report",
            payload={
                "passed": validation_report.passed,
                "summary": validation_report.summary,
                "failures": validation_report.failures,
                "metadata": validation_report.metadata,
            },
            metadata={"symbol": symbol, "run_id": run_id},
        )
        monitored_replay_id = self._save_artifact(
            artifact_id=f"{run_id}-{symbol}-monitored-replay",
            artifact_type="monitored_replay",
            payload={
                "summary": replay_summary,
                "snapshot_count": len(monitoring_sink.snapshots),
                "snapshots": [asdict(snapshot) for snapshot in monitoring_sink.snapshots],
            },
            metadata={"symbol": symbol, "run_id": run_id},
        )
        run_manifest_id = self._save_artifact(
            artifact_id=f"{run_id}-{symbol}-run-manifest",
            artifact_type="run_manifest",
            payload={
                "run_id": run_id,
                "symbol": symbol,
                "trade_date": trade_date,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "artifact_ids": {
                    "state_calibration": state_calibration_id,
                    "regime_calibration": regime_calibration_id,
                    "execution_calibration": execution_calibration_id,
                    "transition_model": transition_model_id,
                    "validation_report": validation_report_id,
                    "monitored_replay": monitored_replay_id,
                },
                "metadata": {
                    "state_panel_rows": int(len(state_panel.frame)),
                    "transition_panel_rows": int(len(transition_panel.frame)),
                    "full_state_panel_rows": int(len(full_state_panel.frame)),
                    "full_transition_panel_rows": int(len(full_transition_panel.frame)),
                    "runtime_transition_rows": int(len(runtime_transition_frame)),
                    "runtime_training_transition_rows": int(len(runtime_training_transition_frame)),
                    "available_horizons_ns": sorted({int(value) for value in full_transition_panel.frame["horizon_ns"].unique()}),
                    "validation_mode": "rolling-oos-retrain",
                    "validation_split_count": int(len(effective_splits)),
                    "validation_execution_snapshot_count": int(len(validation_monitoring_frame)),
                    "validation_passed": validation_report.passed,
                    **validation_report.summary,
                },
            },
            metadata={"symbol": symbol, "run_id": run_id, "trade_date": trade_date},
        )

        return WorkflowRunResult(
            symbol=symbol,
            run_id=run_id,
            state_panel_rows=int(len(full_state_panel.frame)),
            transition_panel_rows=int(len(full_transition_panel.frame)),
            artifact_ids=WorkflowArtifactIds(
                state_calibration_id=state_calibration_id,
                regime_calibration_id=regime_calibration_id,
                execution_calibration_id=execution_calibration_id,
                transition_model_id=transition_model_id,
                validation_report_id=validation_report_id,
                monitored_replay_id=monitored_replay_id,
                run_manifest_id=run_manifest_id,
            ),
            validation_report=validation_report,
            replay_summary=replay_summary,
        )

    def _save_artifact(
        self,
        *,
        artifact_id: str,
        artifact_type: str,
        payload: dict[str, object],
        metadata: dict[str, object],
    ) -> str:
        created_at = datetime.now(timezone.utc).isoformat()
        self.store.save(
            ArtifactMetadata(
                artifact_id=artifact_id,
                artifact_type=artifact_type,
                version=self.version,
                created_at=created_at,
                tags=("l1_microstructure", "workflow"),
                metadata=dict(metadata),
            ),
            payload,
        )
        return artifact_id

    def _default_splits(self, frame: pd.DataFrame) -> list[RegimeSplitSpec]:
        ordered = frame.sort_values("timestamp").reset_index(drop=True)
        if len(ordered) < 2:
            start = ordered.iloc[0]["timestamp"]
            end = ordered.iloc[-1]["timestamp"]
            return [
                RegimeSplitSpec(
                    train_start=start.isoformat(),
                    train_end=end.isoformat(),
                    test_start=start.isoformat(),
                    test_end=end.isoformat(),
                    label="degenerate-split",
                )
            ]

        split_index = max(1, len(ordered) // 2)
        train = ordered.iloc[:split_index]
        test = ordered.iloc[split_index:]
        if test.empty:
            test = ordered.iloc[-1:]
        return [
            RegimeSplitSpec(
                train_start=train.iloc[0]["timestamp"].isoformat(),
                train_end=train.iloc[-1]["timestamp"].isoformat(),
                test_start=test.iloc[0]["timestamp"].isoformat(),
                test_end=test.iloc[-1]["timestamp"].isoformat(),
                label="default-split",
            )
        ]

    @staticmethod
    def _run_id(symbol: str) -> str:
        return f"{symbol.lower()}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}"

    @staticmethod
    def _trade_date(events: list[MarketEvent]) -> str:
        earliest_timestamp_ns = min(event.timestamp_ns for event in events)
        timestamp = datetime.fromtimestamp(earliest_timestamp_ns / 1_000_000_000.0, tz=timezone.utc)
        return timestamp.astimezone(ZoneInfo("America/New_York")).date().isoformat()

    @staticmethod
    def _events_for_window(events: list[MarketEvent], *, start: str, end: str) -> list[MarketEvent]:
        start_ns = int(pd.Timestamp(start, tz="UTC").value)
        end_ns = int(pd.Timestamp(end, tz="UTC").value)
        return [event for event in events if start_ns <= event.timestamp_ns <= end_ns]

    def _build_panels(self, *, symbol: str, events: list[MarketEvent]):
        dataset_builder = PipelineTransitionDatasetBuilder(events, config=self.framework_config)
        state_panel = dataset_builder.build_state_panel(symbol)
        transition_panel = dataset_builder.build_transition_panel(symbol)
        if state_panel.frame.empty:
            raise ValueError(f"state panel is empty for symbol {symbol}")
        if transition_panel.frame.empty:
            raise ValueError(f"transition panel is empty for symbol {symbol}")
        return state_panel, transition_panel

    def _fit_runtime_artifacts(self, *, symbol: str, events: list[MarketEvent]):
        state_panel, transition_panel = self._build_panels(symbol=symbol, events=events)
        state_artifact = QuantileStateCalibrator().fit(
            CalibrationDataset(symbol=symbol, features=state_panel.frame, metadata=state_panel.metadata)
        )
        regime_artifact = EmpiricalRegimeCalibrator().fit(
            CalibrationDataset(symbol=symbol, features=state_panel.frame, metadata=state_panel.metadata)
        )
        execution_artifact = EmpiricalExecutionCalibrator().fit(
            ExecutionCalibrationDataset(
                symbol=symbol,
                state_features=state_panel.frame,
                transition_features=transition_panel.frame,
                metadata={
                    "state_panel_rows": int(len(state_panel.frame)),
                    "transition_panel_rows": int(len(transition_panel.frame)),
                },
            )
        )
        trainer = EmpiricalTransitionTrainer(version=self.version)
        transition_samples = trainer.samples_from_frame(transition_panel.frame)
        trainer.fit(transition_samples, runtime_horizon_ns=self.framework_config.transition.drift_horizon_ns)
        if trainer.last_payload is None:
            raise ValueError("transition trainer did not retain a payload")
        return state_panel, transition_panel, state_artifact, regime_artifact, execution_artifact, trainer.last_payload

    def _run_oos_validation(
        self,
        *,
        symbol: str,
        events: list[MarketEvent],
        validation_frame: pd.DataFrame,
        splits: list[RegimeSplitSpec],
        runner_config: RunnerConfig,
    ) -> tuple[ValidationReport, pd.DataFrame]:
        monitoring_frames: list[pd.DataFrame] = []
        training_failures: list[str] = []

        for split in splits:
            train_events = self._events_for_window(events, start=split.train_start, end=split.train_end)
            test_events = self._events_for_window(events, start=split.test_start, end=split.test_end)
            if not train_events:
                training_failures.append(f"{split.label}: training window does not contain any events")
                continue
            if not test_events:
                training_failures.append(f"{split.label}: test window does not contain any events")
                continue
            try:
                _, _, state_artifact, regime_artifact, execution_artifact, transition_payload = self._fit_runtime_artifacts(
                    symbol=symbol,
                    events=train_events,
                )
            except ValueError as exc:
                training_failures.append(f"{split.label}: {exc}")
                continue

            bundle = RuntimeArtifactBundle(
                state_calibration=state_artifact,
                regime_calibration=regime_artifact,
                execution_calibration=execution_artifact,
                transition_model=transition_payload,
                metadata={
                    "validation_split": split.label,
                    "train_start": split.train_start,
                    "train_end": split.train_end,
                    "test_start": split.test_start,
                    "test_end": split.test_end,
                },
            )
            split_sink = InMemoryMonitoringSink()
            runner = SimulatorPaperTradingRunner(
                events=test_events,
                framework_config=self.framework_config,
                runtime_artifacts=bundle,
                monitoring_sink=split_sink,
            )
            runner.start(runner_config)
            split_frame = runner.monitoring_frame()
            if not split_frame.empty:
                split_frame["validation_split_label"] = split.label
                monitoring_frames.append(split_frame)

        normalized_frames = [frame.dropna(axis="columns", how="all") for frame in monitoring_frames]
        execution_frame = pd.concat(normalized_frames, ignore_index=True) if normalized_frames else pd.DataFrame()
        validation_report = self.validation_harness.run(
            validation_frame,
            splits,
            execution_frame=execution_frame,
        )
        if not training_failures:
            return validation_report, execution_frame

        return (
            ValidationReport(
                passed=False,
                summary=validation_report.summary,
                failures=validation_report.failures + tuple(training_failures),
                metadata={
                    **validation_report.metadata,
                    "training_failures": training_failures,
                },
            ),
            execution_frame,
        )