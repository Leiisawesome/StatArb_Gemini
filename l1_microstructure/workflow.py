"""Artifact-producing research workflow for the successor package."""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo

import pandas as pd

from .artifacts import ArtifactBundleLoader, ArtifactMetadata, LocalArtifactStore, RuntimeArtifactBundle
from .config import FrameworkConfig
from .datasets import DatasetSlice, PipelineTransitionDatasetBuilder
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
    activation_summary: dict[str, object]


class ArtifactDrivenResearchWorkflow:
    def __init__(
        self,
        artifact_root: str | Path,
        framework_config: FrameworkConfig | None = None,
        validation_harness: RollingValidationHarness | None = None,
        version: str = "v1",
    ):
        self.framework_config = framework_config or FrameworkConfig()
        self.validation_harness = validation_harness or RollingValidationHarness(
            minimum_edge_training_sessions=self.framework_config.transition.min_edge_training_sessions,
            minimum_directional_consensus=self.framework_config.transition.min_directional_consensus,
            minimum_cross_session_hit_rate=self.framework_config.transition.min_cross_session_hit_rate,
            minimum_cross_session_hit_consensus=(
                self.framework_config.transition.min_cross_session_hit_consensus
            ),
        )
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
        normalized_events = sorted(
            (event for event in events if event.symbol == symbol),
            key=lambda event: event.timestamp_ns,
        )
        if not normalized_events:
            raise ValueError(f"no events supplied for symbol {symbol}")
        event_timestamps = tuple(event.timestamp_ns for event in normalized_events)

        run_id = self._run_id(symbol)
        session_dates = self._session_dates(normalized_events)
        trade_date = session_dates[-1]
        full_state_panel, full_transition_panel = self._build_panels(symbol=symbol, events=normalized_events)

        # Ensure horizon_ns is properly typed before filtering
        transition_frame = self._normalize_transition_frame(full_transition_panel.frame)
        target_horizon = int(self.framework_config.transition.drift_horizon_ns)

        runtime_transition_frame = transition_frame[transition_frame["horizon_ns"] == target_horizon].copy()
        if runtime_transition_frame.empty:
            raise ValueError(
                f"no transition rows found for runtime horizon {self.framework_config.transition.drift_horizon_ns}"
            )
        runtime_transition_frame["timestamp"] = pd.to_datetime(
            runtime_transition_frame["timestamp_ns"], unit="ns", utc=True
        )
        effective_splits = splits or self._default_splits(runtime_transition_frame, normalized_events)

        validation_runner_config = runner_config or RunnerConfig(
            symbols=(symbol,),
            mode="paper",
            latency_ms=self.framework_config.execution.latency_ms,
        )
        validation_report, validation_monitoring_frame = self._run_oos_validation(
            symbol=symbol,
            events=normalized_events,
            event_timestamps=event_timestamps,
            validation_frame=runtime_transition_frame,
            full_state_panel=full_state_panel,
            full_transition_panel=full_transition_panel,
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
        ) = self._fit_runtime_artifacts_from_panels(
            symbol=symbol,
            state_panel=full_state_panel,
            transition_panel=full_transition_panel,
        )

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

        runtime_training_transition_frame = transition_panel.frame[
            transition_panel.frame["horizon_ns"] == target_horizon
        ]
        transition_model_id = self._save_artifact(
            artifact_id=f"{run_id}-{symbol}-transition-model",
            artifact_type="transition_model",
            payload=transition_payload,
            metadata={
                "symbol": symbol,
                "run_id": run_id,
                "trainer_model_id": str(transition_payload["model_id"]),
                "runtime_horizon_ns": self.framework_config.transition.drift_horizon_ns,
                "minimum_training_sessions": self.framework_config.transition.min_edge_training_sessions,
                "minimum_directional_consensus": self.framework_config.transition.min_directional_consensus,
                "minimum_cross_session_hit_rate": self.framework_config.transition.min_cross_session_hit_rate,
                "minimum_cross_session_hit_consensus": (
                    self.framework_config.transition.min_cross_session_hit_consensus
                ),
            },
        )

        bundle = ArtifactBundleLoader(self.store).load_runtime_bundle(
            state_calibration_id=state_calibration_id,
            regime_calibration_id=regime_calibration_id,
            execution_calibration_id=execution_calibration_id,
            transition_model_id=transition_model_id,
        )
        # A full liquid-symbol replay can produce millions of updates. Retain
        # deterministic, evenly spaced evidence while preserving the exact
        # publication count and aggregate execution summary.
        monitoring_sink = InMemoryMonitoringSink(max_snapshots=10_000)
        replay_summary, activation_summary, _ = self._run_session_replays(
            events=normalized_events,
            runner_config=validation_runner_config,
            runtime_artifacts=bundle,
            monitoring_sink=monitoring_sink,
        )
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
                "activation_summary": activation_summary,
                "snapshot_count": monitoring_sink.published_snapshot_count,
                "sampled_snapshot_count": len(monitoring_sink.snapshots),
                "sampling_stride": monitoring_sink.sampling_stride,
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
                "training_session_dates": list(session_dates),
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
                    "available_horizons_ns": sorted(
                        {int(value) for value in full_transition_panel.frame["horizon_ns"].unique()}
                    ),
                    "validation_mode": "rolling-oos-retrain",
                    "validation_split_count": int(len(effective_splits)),
                    "validation_execution_snapshot_count": int(len(validation_monitoring_frame)),
                    "validation_passed": validation_report.passed,
                    "training_session_count": len(session_dates),
                    "training_session_dates": list(session_dates),
                    "minimum_edge_training_sessions": self.framework_config.transition.min_edge_training_sessions,
                    "minimum_directional_consensus": self.framework_config.transition.min_directional_consensus,
                    "minimum_cross_session_hit_rate": self.framework_config.transition.min_cross_session_hit_rate,
                    "minimum_cross_session_hit_consensus": (
                        self.framework_config.transition.min_cross_session_hit_consensus
                    ),
                    "replay_transition_count": int(activation_summary["transition_count"]),
                    "replay_actionable_intent_count": int(activation_summary["actionable_intent_count"]),
                    "replay_risk_approved_count": int(activation_summary["risk_approved_count"]),
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
            activation_summary=activation_summary,
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

    def _default_splits(
        self,
        frame: pd.DataFrame,
        events: list[MarketEvent] | None = None,
    ) -> list[RegimeSplitSpec]:
        ordered = frame.sort_values("timestamp").reset_index(drop=True)
        session_dates = tuple(str(value) for value in ordered.get("session_date", pd.Series(dtype=str)).unique())
        if len(session_dates) >= 2 and events:
            event_sessions = self._events_by_session(events)
            splits: list[RegimeSplitSpec] = []
            available_dates = [session_date for session_date in session_dates if session_date in event_sessions]
            minimum_training_sessions = max(self.framework_config.transition.min_edge_training_sessions, 1)
            if len(available_dates) <= minimum_training_sessions:
                raise ValueError(
                    "session-consensus validation requires at least "
                    f"{minimum_training_sessions + 1} completed trade dates"
                )
            for test_index in range(minimum_training_sessions, len(available_dates)):
                train_dates = available_dates[:test_index]
                test_date = available_dates[test_index]
                train_events = [event for session_date in train_dates for event in event_sessions[session_date]]
                test_events = event_sessions[test_date]
                splits.append(
                    RegimeSplitSpec(
                        train_start=self._iso_timestamp(train_events[0].timestamp_ns),
                        train_end=self._iso_timestamp(train_events[-1].timestamp_ns),
                        test_start=self._iso_timestamp(test_events[0].timestamp_ns),
                        test_end=self._iso_timestamp(test_events[-1].timestamp_ns),
                        label=f"walk-forward-{test_date}",
                    )
                )
            if splits:
                return splits

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
    def _session_date(timestamp_ns: int) -> str:
        timestamp = datetime.fromtimestamp(timestamp_ns / 1_000_000_000.0, tz=timezone.utc)
        return timestamp.astimezone(ZoneInfo("America/New_York")).date().isoformat()

    @classmethod
    def _session_dates(cls, events: list[MarketEvent]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(cls._session_date(event.timestamp_ns) for event in events))

    @classmethod
    def _events_by_session(cls, events: list[MarketEvent]) -> dict[str, list[MarketEvent]]:
        sessions: dict[str, list[MarketEvent]] = {}
        for event in events:
            sessions.setdefault(cls._session_date(event.timestamp_ns), []).append(event)
        return sessions

    @staticmethod
    def _iso_timestamp(timestamp_ns: int) -> str:
        return pd.Timestamp(timestamp_ns, unit="ns", tz="UTC").isoformat()

    @staticmethod
    def _timestamp_ns(value: str) -> int:
        timestamp = pd.Timestamp(value)
        if timestamp.tzinfo is None:
            timestamp = timestamp.tz_localize("UTC")
        else:
            timestamp = timestamp.tz_convert("UTC")
        return int(timestamp.value)

    @classmethod
    def _events_for_window(
        cls,
        events: list[MarketEvent],
        timestamps: tuple[int, ...],
        *,
        start: str,
        end: str,
    ) -> list[MarketEvent]:
        start_index = bisect_left(timestamps, cls._timestamp_ns(start))
        end_index = bisect_right(timestamps, cls._timestamp_ns(end))
        return events[start_index:end_index]

    @staticmethod
    def _normalize_transition_frame(frame: pd.DataFrame) -> pd.DataFrame:
        if not pd.api.types.is_integer_dtype(frame["horizon_ns"]):
            frame["horizon_ns"] = pd.to_numeric(frame["horizon_ns"], errors="coerce").fillna(0).astype(int)
        return frame

    def _build_panels(self, *, symbol: str, events: list[MarketEvent]):
        state_frames: list[pd.DataFrame] = []
        transition_frames: list[pd.DataFrame] = []
        session_dates: list[str] = []
        transition_metadata: dict[str, object] = {}

        # Each regular session is an independent state-machine history. This
        # prevents overnight gaps and prior-session rolling state from becoming
        # synthetic features or transitions in multi-session research.
        for session_date, session_events in self._events_by_session(events).items():
            dataset_builder = PipelineTransitionDatasetBuilder(session_events, config=self.framework_config)
            state_panel, transition_panel = dataset_builder.build_panels_single_pass(symbol)
            if not state_panel.frame.empty:
                state_frame = state_panel.frame.copy()
                state_frame["session_date"] = session_date
                state_frames.append(state_frame)
            if not transition_panel.frame.empty:
                transition_frame = transition_panel.frame.copy()
                transition_frame["session_date"] = session_date
                transition_frames.append(transition_frame)
                transition_metadata = dict(transition_panel.metadata)
            if not state_panel.frame.empty or not transition_panel.frame.empty:
                session_dates.append(session_date)

        if not state_frames:
            raise ValueError(f"state panel is empty for symbol {symbol}")
        if not transition_frames:
            raise ValueError(f"transition panel is empty for symbol {symbol}")
        state_frame = pd.concat(state_frames, ignore_index=True)
        transition_frame = pd.concat(transition_frames, ignore_index=True)
        return (
            DatasetSlice(
                name=f"{symbol}_state_panel",
                frame=state_frame,
                metadata={
                    "row_count": len(state_frame),
                    "session_count": len(session_dates),
                    "session_dates": tuple(session_dates),
                },
            ),
            DatasetSlice(
                name=f"{symbol}_transition_panel",
                frame=transition_frame,
                metadata={
                    **transition_metadata,
                    "row_count": len(transition_frame),
                    "session_count": len(session_dates),
                    "session_dates": tuple(session_dates),
                },
            ),
        )

    def _training_panels_for_window(
        self,
        *,
        symbol: str,
        all_events: list[MarketEvent],
        train_events: list[MarketEvent],
        full_state_panel: DatasetSlice,
        full_transition_panel: DatasetSlice,
    ) -> tuple[DatasetSlice, DatasetSlice]:
        all_sessions = self._events_by_session(all_events)
        first_session = self._session_date(train_events[0].timestamp_ns)
        last_session = self._session_date(train_events[-1].timestamp_ns)
        starts_at_session_boundary = train_events[0].timestamp_ns == all_sessions[first_session][0].timestamp_ns
        ends_at_session_boundary = train_events[-1].timestamp_ns == all_sessions[last_session][-1].timestamp_ns
        if not starts_at_session_boundary or not ends_at_session_boundary:
            return self._build_panels(symbol=symbol, events=train_events)

        start_ns = train_events[0].timestamp_ns
        end_ns = train_events[-1].timestamp_ns
        state_frame = full_state_panel.frame[
            (full_state_panel.frame["timestamp_ns"] >= start_ns)
            & (full_state_panel.frame["timestamp_ns"] <= end_ns)
        ].copy()
        transition_frame = full_transition_panel.frame[
            (full_transition_panel.frame["timestamp_ns"] >= start_ns)
            & (full_transition_panel.frame["timestamp_ns"] <= end_ns)
            & full_transition_panel.frame["end_timestamp_ns"].notna()
            & (full_transition_panel.frame["end_timestamp_ns"] <= end_ns)
        ].copy()
        if state_frame.empty or transition_frame.empty:
            return self._build_panels(symbol=symbol, events=train_events)
        session_dates = self._session_dates(train_events)
        return (
            DatasetSlice(
                name=f"{symbol}_state_panel",
                frame=state_frame,
                metadata={
                    "row_count": len(state_frame),
                    "session_count": len(session_dates),
                    "session_dates": session_dates,
                    "source": "complete-session-cache",
                },
            ),
            DatasetSlice(
                name=f"{symbol}_transition_panel",
                frame=transition_frame,
                metadata={
                    **full_transition_panel.metadata,
                    "row_count": len(transition_frame),
                    "session_count": len(session_dates),
                    "session_dates": session_dates,
                    "source": "complete-session-cache",
                },
            ),
        )

    def _run_session_replays(
        self,
        *,
        events: list[MarketEvent],
        runner_config: RunnerConfig,
        runtime_artifacts: RuntimeArtifactBundle,
        monitoring_sink: InMemoryMonitoringSink | None = None,
    ) -> tuple[dict[str, float], dict[str, object], pd.DataFrame]:
        aggregate_execution = {"update_count": 0.0, "fill_count": 0.0, "cancel_count": 0.0}
        aggregate_activation: dict[str, object] = {
            "transition_count": 0,
            "actionable_intent_count": 0,
            "risk_approved_count": 0,
            "intent_action_counts": {},
            "intent_reason_counts": {},
            "risk_reason_counts": {},
        }
        frames: list[pd.DataFrame] = []
        sink = monitoring_sink or InMemoryMonitoringSink()

        for session_events in self._events_by_session(events).values():
            before_count = sink.published_snapshot_count
            runner = SimulatorPaperTradingRunner(
                events=session_events,
                framework_config=self.framework_config,
                runtime_artifacts=runtime_artifacts,
                monitoring_sink=sink,
                retain_updates=False,
            )
            runner.start(runner_config)
            for key, value in runner.execution_summary().items():
                aggregate_execution[key] += float(value)
            self._merge_activation_summary(aggregate_activation, runner.activation_summary())
            session_frame = runner.monitoring_frame()
            if monitoring_sink is None and not session_frame.empty:
                frames.append(session_frame.iloc[before_count:].copy())

        if monitoring_sink is not None:
            monitoring_frame = monitoring_sink.to_frame()
        else:
            monitoring_frame = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        return aggregate_execution, aggregate_activation, monitoring_frame

    @staticmethod
    def _merge_activation_summary(target: dict[str, object], source: dict[str, object]) -> None:
        for key in ("transition_count", "actionable_intent_count", "risk_approved_count"):
            target[key] = int(target[key]) + int(source[key])
        for key in ("intent_action_counts", "intent_reason_counts", "risk_reason_counts"):
            target_counts = target[key]
            source_counts = source[key]
            if not isinstance(target_counts, dict) or not isinstance(source_counts, dict):
                raise TypeError(f"activation summary field {key} must be a mapping")
            for reason, count in source_counts.items():
                target_counts[str(reason)] = int(target_counts.get(str(reason), 0)) + int(count)

    def _fit_runtime_artifacts_from_panels(
        self,
        *,
        symbol: str,
        state_panel: DatasetSlice,
        transition_panel: DatasetSlice,
    ):
        if state_panel.frame.empty:
            raise ValueError(f"state panel is empty for symbol {symbol}")
        if transition_panel.frame.empty:
            raise ValueError(f"transition panel is empty for symbol {symbol}")
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
        event_timestamps: tuple[int, ...],
        validation_frame: pd.DataFrame,
        full_state_panel: DatasetSlice,
        full_transition_panel: DatasetSlice,
        splits: list[RegimeSplitSpec],
        runner_config: RunnerConfig,
    ) -> tuple[ValidationReport, pd.DataFrame]:
        monitoring_frames: list[pd.DataFrame] = []
        training_failures: list[str] = []
        activation_diagnostics: dict[str, dict[str, object]] = {}

        for split in splits:
            train_events = self._events_for_window(
                events,
                event_timestamps,
                start=split.train_start,
                end=split.train_end,
            )
            test_events = self._events_for_window(
                events,
                event_timestamps,
                start=split.test_start,
                end=split.test_end,
            )
            if not train_events:
                training_failures.append(f"{split.label}: training window does not contain any events")
                continue
            if not test_events:
                training_failures.append(f"{split.label}: test window does not contain any events")
                continue
            try:
                training_state_panel, training_transition_panel = self._training_panels_for_window(
                    symbol=symbol,
                    all_events=events,
                    train_events=train_events,
                    full_state_panel=full_state_panel,
                    full_transition_panel=full_transition_panel,
                )
                _, _, state_artifact, regime_artifact, execution_artifact, transition_payload = (
                    self._fit_runtime_artifacts_from_panels(
                        symbol=symbol,
                        state_panel=training_state_panel,
                        transition_panel=training_transition_panel,
                    )
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
            _, split_activation, split_frame = self._run_session_replays(
                events=test_events,
                runner_config=runner_config,
                runtime_artifacts=bundle,
            )
            activation_diagnostics[split.label] = split_activation
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
        enriched_report = ValidationReport(
            passed=validation_report.passed and not training_failures,
            summary=validation_report.summary,
            failures=validation_report.failures + tuple(training_failures),
            metadata={
                **validation_report.metadata,
                "activation_diagnostics": activation_diagnostics,
                **({"training_failures": training_failures} if training_failures else {}),
            },
        )
        return enriched_report, execution_frame
