"""Empirical transition-kernel trainer for successor-package research loops."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha1
from math import isnan
from statistics import stdev
from typing import Iterable

import pandas as pd

from l1_microstructure.artifacts import ArtifactMetadata, LocalArtifactStore
from l1_microstructure.session_evidence import leave_one_session_out_hit_evidence

from .interfaces import TransitionModelArtifact, TransitionTrainingSample


class EmpiricalTransitionTrainer:
    def __init__(self, artifact_store: LocalArtifactStore | None = None, version: str = "v1"):
        self.artifact_store = artifact_store
        self.version = version
        self.last_payload: dict[str, object] | None = None

    def fit(
        self,
        samples: Iterable[TransitionTrainingSample],
        runtime_horizon_ns: int | None = None,
    ) -> TransitionModelArtifact:
        sample_list = list(samples)
        if not sample_list:
            raise ValueError("transition training requires at least one sample")

        created_at = datetime.now(timezone.utc).isoformat()
        model_id = self._model_id(sample_list)
        payload = self._build_payload(
            sample_list,
            model_id=model_id,
            created_at=created_at,
            runtime_horizon_ns=runtime_horizon_ns,
        )
        self.last_payload = payload

        artifact = TransitionModelArtifact(
            model_id=model_id,
            created_at=created_at,
            edge_count=len(payload["edges"]),
            metadata={
                "sample_count": len(sample_list),
                "trainer": "empirical_transition_trainer",
                "version": self.version,
            },
        )
        if self.artifact_store is not None:
            self.artifact_store.save(
                ArtifactMetadata(
                    artifact_id=model_id,
                    artifact_type="transition_model",
                    version=self.version,
                    created_at=created_at,
                    tags=("l1_microstructure", "transition_training"),
                    metadata=artifact.metadata,
                ),
                payload,
            )
        return artifact

    def fit_frame(
        self,
        frame: pd.DataFrame,
        runtime_horizon_ns: int | None = None,
    ) -> TransitionModelArtifact:
        """Fit directly from a transition frame without per-row Python objects."""

        self._require_frame_columns(frame)
        if frame.empty:
            raise ValueError("transition training requires at least one sample")

        created_at = datetime.now(timezone.utc).isoformat()
        model_id = self._frame_model_id(frame, runtime_horizon_ns)
        payload = self._build_payload_from_frame(
            frame,
            model_id=model_id,
            created_at=created_at,
            runtime_horizon_ns=runtime_horizon_ns,
        )
        self.last_payload = payload

        artifact = TransitionModelArtifact(
            model_id=model_id,
            created_at=created_at,
            edge_count=len(payload["edges"]),
            metadata={
                "sample_count": len(frame),
                "trainer": "empirical_transition_trainer",
                "version": self.version,
                "storage": "summary_only",
            },
        )
        if self.artifact_store is not None:
            self.artifact_store.save(
                ArtifactMetadata(
                    artifact_id=model_id,
                    artifact_type="transition_model",
                    version=self.version,
                    created_at=created_at,
                    tags=("l1_microstructure", "transition_training"),
                    metadata=artifact.metadata,
                ),
                payload,
            )
        return artifact

    def samples_from_frame(self, frame: pd.DataFrame) -> list[TransitionTrainingSample]:
        self._require_frame_columns(frame)

        required = ("symbol", "from_state", "to_state", "regime", "holding_time_ns", "realized_drift_bps")

        columns = tuple(frame.columns)
        column_indexes = {column: index for index, column in enumerate(columns)}
        metadata_columns = tuple(column for column in columns if column not in required)
        samples: list[TransitionTrainingSample] = []
        for values in frame.itertuples(index=False, name=None):
            metadata = {column: values[column_indexes[column]] for column in metadata_columns}
            samples.append(
                TransitionTrainingSample(
                    symbol=str(values[column_indexes["symbol"]]),
                    from_state=str(values[column_indexes["from_state"]]),
                    to_state=str(values[column_indexes["to_state"]]),
                    regime=str(values[column_indexes["regime"]]),
                    horizon_ns=int(values[column_indexes["horizon_ns"]]) if "horizon_ns" in column_indexes else 0,
                    holding_time_ns=int(values[column_indexes["holding_time_ns"]]),
                    realized_drift_bps=float(values[column_indexes["realized_drift_bps"]]),
                    metadata=metadata,
                )
            )
        return samples

    @staticmethod
    def _require_frame_columns(frame: pd.DataFrame) -> None:
        required = ("symbol", "from_state", "to_state", "regime", "holding_time_ns", "realized_drift_bps")
        missing = [column for column in required if column not in frame.columns]
        if missing:
            raise ValueError(f"transition panel is missing required columns: {missing}")

    def _build_payload(
        self,
        samples: list[TransitionTrainingSample],
        model_id: str,
        created_at: str,
        runtime_horizon_ns: int | None = None,
    ) -> dict[str, object]:
        horizon_buckets: dict[int, list[TransitionTrainingSample]] = defaultdict(list)
        for sample in samples:
            horizon_buckets[int(sample.horizon_ns)].append(sample)

        resolved_runtime_horizon_ns = runtime_horizon_ns
        if resolved_runtime_horizon_ns is None:
            resolved_runtime_horizon_ns = sorted(horizon_buckets)[0]

        horizon_models: dict[str, dict[str, object]] = {}
        for horizon_ns, horizon_samples in sorted(horizon_buckets.items()):
            horizon_models[str(horizon_ns)] = self._build_horizon_payload(horizon_samples)

        runtime_key = str(int(resolved_runtime_horizon_ns))
        runtime_payload = horizon_models.get(runtime_key)
        if runtime_payload is None:
            raise ValueError(f"runtime horizon {resolved_runtime_horizon_ns} is not present in the training samples")

        available_horizons_ns = [int(value) for value in sorted(horizon_buckets)]
        return {
            "model_id": model_id,
            "created_at": created_at,
            "edge_count": int(runtime_payload["edge_count"]),
            "sample_count": len(samples),
            "runtime_horizon_ns": int(resolved_runtime_horizon_ns),
            "available_horizons_ns": available_horizons_ns,
            "horizon_models": horizon_models,
            "edges": runtime_payload["edges"],
        }

    def _build_payload_from_frame(
        self,
        frame: pd.DataFrame,
        model_id: str,
        created_at: str,
        runtime_horizon_ns: int | None = None,
    ) -> dict[str, object]:
        if "horizon_ns" in frame.columns:
            horizon_values = pd.to_numeric(frame["horizon_ns"], errors="raise").astype("int64")
        else:
            horizon_values = pd.Series(0, index=frame.index, dtype="int64")
        available_horizons_ns = sorted(int(value) for value in horizon_values.unique())
        resolved_runtime_horizon_ns = (
            available_horizons_ns[0] if runtime_horizon_ns is None else int(runtime_horizon_ns)
        )
        if resolved_runtime_horizon_ns not in available_horizons_ns:
            raise ValueError(
                f"runtime horizon {resolved_runtime_horizon_ns} is not present in the training samples"
            )

        horizon_models: dict[str, dict[str, object]] = {}
        for horizon_ns in available_horizons_ns:
            horizon_frame = frame.loc[horizon_values == horizon_ns]
            horizon_models[str(horizon_ns)] = self._build_horizon_frame_payload(horizon_frame)

        runtime_payload = horizon_models[str(resolved_runtime_horizon_ns)]
        return {
            "model_id": model_id,
            "created_at": created_at,
            "edge_count": int(runtime_payload["edge_count"]),
            "sample_count": len(frame),
            "runtime_horizon_ns": resolved_runtime_horizon_ns,
            "available_horizons_ns": available_horizons_ns,
            "horizon_models": horizon_models,
            "edges": runtime_payload["edges"],
        }

    def _build_horizon_frame_payload(self, frame: pd.DataFrame) -> dict[str, object]:
        edge_columns = ["from_state", "to_state", "regime"]
        working_columns = [*edge_columns, "holding_time_ns", "realized_drift_bps"]
        session_column = "session_date" if "session_date" in frame.columns else None
        if session_column is None and "trade_date" in frame.columns:
            session_column = "trade_date"
        if session_column is not None:
            working_columns.append(session_column)

        working = frame[working_columns].copy()
        working["training_session_id"] = (
            working[session_column].astype(str) if session_column is not None else "unknown-session"
        )
        working["_positive"] = (working["realized_drift_bps"] > 0.0).astype("int8")
        working["_negative"] = (working["realized_drift_bps"] < 0.0).astype("int8")

        edge_summary = working.groupby(edge_columns, dropna=False, observed=True).agg(
            count=("realized_drift_bps", "size"),
            mean_holding_time_ns=("holding_time_ns", "mean"),
            drift_mean_bps=("realized_drift_bps", "mean"),
            drift_std_bps=("realized_drift_bps", "std"),
        )
        outgoing_counts = working.groupby(
            ["from_state", "regime"], dropna=False, observed=True
        ).size().to_dict()
        session_summary = working.groupby(
            [*edge_columns, "training_session_id"], dropna=False, observed=True
        ).agg(
            session_mean=("realized_drift_bps", "mean"),
            sample_count=("realized_drift_bps", "size"),
            positive_count=("_positive", "sum"),
            negative_count=("_negative", "sum"),
        ).reset_index()

        sessions_by_edge: dict[tuple[str, str, str], list[tuple[str, float, int, int, int]]] = defaultdict(list)
        for row in session_summary.itertuples(index=False):
            edge_key = (str(row.from_state), str(row.to_state), str(row.regime))
            sessions_by_edge[edge_key].append(
                (
                    str(row.training_session_id),
                    float(row.session_mean),
                    int(row.sample_count),
                    int(row.positive_count),
                    int(row.negative_count),
                )
            )

        edges: dict[str, dict[str, object]] = {}
        for index_values, summary in edge_summary.iterrows():
            from_state, to_state, regime = (str(value) for value in index_values)
            edge_tuple = (from_state, to_state, regime)
            session_records = sorted(sessions_by_edge[edge_tuple], key=lambda record: record[0])
            training_session_ids = [record[0] for record in session_records]
            session_drift_means = [record[1] for record in session_records]
            cross_session_evidence = leave_one_session_out_hit_evidence(
                session_drift_means,
                [record[3] for record in session_records],
                [record[4] for record in session_records],
                [record[2] for record in session_records],
            )
            session_balanced_mean = float(sum(session_drift_means) / len(session_drift_means))
            if session_balanced_mean > 0.0:
                aligned_session_count = sum(value > 0.0 for value in session_drift_means)
            elif session_balanced_mean < 0.0:
                aligned_session_count = sum(value < 0.0 for value in session_drift_means)
            else:
                aligned_session_count = 0
            count = int(summary["count"])
            drift_std_bps = float(summary["drift_std_bps"])
            if isnan(drift_std_bps):
                drift_std_bps = 0.0
            payload_key = f"{from_state}::{to_state}::{regime}"
            edges[payload_key] = {
                "from_state": from_state,
                "to_state": to_state,
                "regime": regime,
                "count": count,
                "transition_probability": count / max(int(outgoing_counts[(index_values[0], index_values[2])]), 1),
                "mean_holding_time_ns": float(summary["mean_holding_time_ns"]),
                "drift_mean_bps": float(summary["drift_mean_bps"]),
                "drift_std_bps": drift_std_bps,
                "training_session_count": len(session_drift_means),
                "training_session_ids": training_session_ids,
                "session_drift_means_bps": session_drift_means,
                "session_balanced_drift_mean_bps": session_balanced_mean,
                "directional_consensus": aligned_session_count / len(session_drift_means),
                "cross_session_hit_rates": list(cross_session_evidence.session_hit_rates),
                "cross_session_hit_rate": cross_session_evidence.mean_hit_rate,
                "cross_session_hit_consensus": cross_session_evidence.consensus,
            }

        return {
            "edge_count": len(edges),
            "sample_count": len(frame),
            "edges": edges,
        }

    def _build_horizon_payload(self, samples: list[TransitionTrainingSample]) -> dict[str, object]:
        grouped: dict[tuple[str, str, str], list[TransitionTrainingSample]] = defaultdict(list)
        outgoing: dict[tuple[str, str], int] = defaultdict(int)
        for sample in samples:
            grouped[(sample.from_state, sample.to_state, sample.regime)].append(sample)
            outgoing[(sample.from_state, sample.regime)] += 1

        edges: dict[str, dict[str, object]] = {}
        for (from_state, to_state, regime), edge_samples in sorted(grouped.items()):
            holding_times = [sample.holding_time_ns for sample in edge_samples]
            drifts = [sample.realized_drift_bps for sample in edge_samples]
            session_drifts: dict[str, list[float]] = defaultdict(list)
            for sample in edge_samples:
                session_id = str(
                    sample.metadata.get("session_date")
                    or sample.metadata.get("trade_date")
                    or "unknown-session"
                )
                session_drifts[session_id].append(sample.realized_drift_bps)
            ordered_session_drifts = sorted(session_drifts.items())
            training_session_ids = [session_id for session_id, _ in ordered_session_drifts]
            session_drift_means = [float(sum(values) / len(values)) for _, values in ordered_session_drifts]
            cross_session_evidence = leave_one_session_out_hit_evidence(
                session_drift_means,
                [sum(value > 0.0 for value in values) for _, values in ordered_session_drifts],
                [sum(value < 0.0 for value in values) for _, values in ordered_session_drifts],
                [len(values) for _, values in ordered_session_drifts],
            )
            session_balanced_mean = float(sum(session_drift_means) / len(session_drift_means))
            if session_balanced_mean > 0.0:
                aligned_session_count = sum(value > 0.0 for value in session_drift_means)
            elif session_balanced_mean < 0.0:
                aligned_session_count = sum(value < 0.0 for value in session_drift_means)
            else:
                aligned_session_count = 0
            directional_consensus = aligned_session_count / len(session_drift_means)
            total_outgoing = outgoing[(from_state, regime)]
            edge_key = f"{from_state}::{to_state}::{regime}"
            edges[edge_key] = {
                "from_state": from_state,
                "to_state": to_state,
                "regime": regime,
                "count": len(edge_samples),
                "transition_probability": len(edge_samples) / max(total_outgoing, 1),
                "mean_holding_time_ns": float(sum(holding_times) / max(len(holding_times), 1)),
                "drift_mean_bps": float(sum(drifts) / max(len(drifts), 1)),
                "drift_std_bps": float(stdev(drifts)) if len(drifts) > 1 else 0.0,
                "training_session_count": len(session_drift_means),
                "training_session_ids": training_session_ids,
                "session_drift_means_bps": session_drift_means,
                "session_balanced_drift_mean_bps": session_balanced_mean,
                "directional_consensus": directional_consensus,
                "cross_session_hit_rates": list(cross_session_evidence.session_hit_rates),
                "cross_session_hit_rate": cross_session_evidence.mean_hit_rate,
                "cross_session_hit_consensus": cross_session_evidence.consensus,
                "holding_times_ns": [int(value) for value in holding_times],
                "drift_samples_bps": [float(value) for value in drifts],
            }

        return {
            "edge_count": len(edges),
            "sample_count": len(samples),
            "edges": edges,
        }

    @staticmethod
    def _model_id(samples: list[TransitionTrainingSample]) -> str:
        digest = sha1()
        for sample in sorted(
            samples,
            key=lambda current: (
                current.symbol,
                current.from_state,
                current.to_state,
                current.regime,
                current.holding_time_ns,
                current.realized_drift_bps,
            ),
        ):
            digest.update(repr(asdict(sample)).encode("utf-8"))
        return digest.hexdigest()

    @staticmethod
    def _frame_model_id(frame: pd.DataFrame, runtime_horizon_ns: int | None) -> str:
        digest = sha1()
        digest.update(str(runtime_horizon_ns).encode("utf-8"))
        digest.update(pd.util.hash_pandas_object(frame, index=False).to_numpy().tobytes())
        return digest.hexdigest()
