"""Rolling OOS validation harness for successor-package transition datasets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .interfaces import RegimeSplitSpec, ValidationReport


@dataclass(slots=True)
class RollingValidationHarness:
    minimum_test_rows: int = 1
    minimum_regime_coverage: float = 0.5
    minimum_hit_rate: float = 0.5
    minimum_decay_ratio: float = 0.25
    minimum_fill_rate: float = 0.0
    maximum_cancel_rate: float = 1.0
    maximum_drift_tracking_error_bps: float = float("inf")
    bootstrap_sample_count: int = 0
    bootstrap_confidence_level: float = 0.90
    minimum_bootstrap_hit_rate_lower_bound: float = 0.0
    minimum_bootstrap_decay_ratio_lower_bound: float = 0.0
    bootstrap_random_seed: int = 7
    timestamp_column: str = "timestamp"
    regime_column: str = "regime"
    drift_column: str = "realized_drift_bps"
    edge_from_column: str = "from_state"
    edge_to_column: str = "to_state"
    execution_timestamp_column: str = "timestamp"
    execution_fill_rate_column: str = "fill_rate"
    execution_cancel_rate_column: str = "cancel_rate"
    execution_expected_drift_column: str = "expected_drift_bps"
    execution_realized_drift_column: str = "realized_drift_bps"
    execution_kill_switch_column: str = "kill_switch_active"

    def run(
        self,
        dataset: pd.DataFrame,
        splits: list[RegimeSplitSpec],
        execution_frame: pd.DataFrame | None = None,
    ) -> ValidationReport:
        self._require_columns(dataset)
        if not splits:
            raise ValueError("validation requires at least one split")

        frame = dataset.copy()
        frame[self.timestamp_column] = pd.to_datetime(frame[self.timestamp_column], utc=True)
        execution = self._prepare_execution_frame(execution_frame)

        failures: list[str] = []
        split_summaries: list[dict[str, float]] = []

        for split in splits:
            train_frame = self._window(frame, split.train_start, split.train_end)
            test_frame = self._window(frame, split.test_start, split.test_end)
            execution_test_frame = self._execution_window(execution, split.test_start, split.test_end)
            split_summary = self._evaluate_split(split.label, train_frame, test_frame, execution_test_frame)
            split_summaries.append(split_summary)
            failures.extend(self._failures_for_split(split.label, split_summary))

        summary = self._aggregate_summary(split_summaries)
        metadata = {
            "split_count": len(splits),
            "per_split": split_summaries,
        }
        return ValidationReport(passed=not failures, summary=summary, failures=tuple(failures), metadata=metadata)

    def _window(self, frame: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
        start_ts = pd.Timestamp(start, tz="UTC")
        end_ts = pd.Timestamp(end, tz="UTC")
        return frame[(frame[self.timestamp_column] >= start_ts) & (frame[self.timestamp_column] <= end_ts)].copy()

    def _evaluate_split(
        self,
        label: str,
        train_frame: pd.DataFrame,
        test_frame: pd.DataFrame,
        execution_test_frame: pd.DataFrame,
    ) -> dict[str, float]:
        train_abs_mean = float(train_frame[self.drift_column].abs().mean()) if not train_frame.empty else 0.0
        test_abs_mean = float(test_frame[self.drift_column].abs().mean()) if not test_frame.empty else 0.0
        decay_ratio = test_abs_mean / max(train_abs_mean, 1e-9)

        train_regimes = set(train_frame[self.regime_column].dropna().astype(str))
        test_regimes = set(test_frame[self.regime_column].dropna().astype(str))
        regime_coverage = len(train_regimes & test_regimes) / max(len(test_regimes), 1)

        test_rows = int(len(test_frame))
        hit_rate = float((test_frame[self.drift_column] > 0.0).mean()) if test_rows else 0.0
        unseen_edge_rate = self._unseen_edge_rate(train_frame, test_frame)
        fill_rate = self._execution_mean(execution_test_frame, self.execution_fill_rate_column)
        cancel_rate = self._execution_mean(execution_test_frame, self.execution_cancel_rate_column)
        drift_tracking_error = self._drift_tracking_error(execution_test_frame)
        kill_switch_rate = self._kill_switch_rate(execution_test_frame)
        bootstrap_metrics = self._bootstrap_metrics(train_frame, test_frame)

        return {
            "train_rows": float(len(train_frame)),
            "test_rows": float(test_rows),
            "train_abs_mean_drift_bps": train_abs_mean,
            "test_abs_mean_drift_bps": test_abs_mean,
            "test_hit_rate": hit_rate,
            "regime_coverage": float(regime_coverage),
            "drift_decay_ratio": float(decay_ratio),
            "unseen_edge_rate": float(unseen_edge_rate),
            "test_fill_rate": float(fill_rate),
            "test_cancel_rate": float(cancel_rate),
            "execution_drift_tracking_error_bps": float(drift_tracking_error),
            "kill_switch_rate": float(kill_switch_rate),
            **bootstrap_metrics,
        }

    def _unseen_edge_rate(self, train_frame: pd.DataFrame, test_frame: pd.DataFrame) -> float:
        if test_frame.empty:
            return 1.0
        train_edges = {
            (str(record[self.edge_from_column]), str(record[self.edge_to_column]), str(record[self.regime_column]))
            for record in train_frame[[self.edge_from_column, self.edge_to_column, self.regime_column]].to_dict(orient="records")
        }
        test_edges = [
            (str(record[self.edge_from_column]), str(record[self.edge_to_column]), str(record[self.regime_column]))
            for record in test_frame[[self.edge_from_column, self.edge_to_column, self.regime_column]].to_dict(orient="records")
        ]
        unseen = sum(1 for edge in test_edges if edge not in train_edges)
        return unseen / max(len(test_edges), 1)

    def _failures_for_split(self, label: str, split_summary: dict[str, float]) -> list[str]:
        failures: list[str] = []
        if split_summary["test_rows"] < self.minimum_test_rows:
            failures.append(f"{label}: insufficient test rows")
        if split_summary["regime_coverage"] < self.minimum_regime_coverage:
            failures.append(f"{label}: insufficient regime coverage")
        if split_summary["test_hit_rate"] < self.minimum_hit_rate:
            failures.append(f"{label}: hit rate below threshold")
        if split_summary["drift_decay_ratio"] < self.minimum_decay_ratio:
            failures.append(f"{label}: excessive drift decay")
        if split_summary["unseen_edge_rate"] >= 1.0:
            failures.append(f"{label}: no trained-edge overlap in test window")
        if split_summary["test_fill_rate"] < self.minimum_fill_rate:
            failures.append(f"{label}: fill rate below threshold")
        if split_summary["test_cancel_rate"] > self.maximum_cancel_rate:
            failures.append(f"{label}: cancel rate above threshold")
        if split_summary["execution_drift_tracking_error_bps"] > self.maximum_drift_tracking_error_bps:
            failures.append(f"{label}: execution drift tracking error above threshold")
        if split_summary["kill_switch_rate"] > 0.0:
            failures.append(f"{label}: kill switch activated during test window")
        if split_summary["bootstrap_hit_rate_lower_bound"] < self.minimum_bootstrap_hit_rate_lower_bound:
            failures.append(f"{label}: bootstrap hit-rate lower bound below threshold")
        if split_summary["bootstrap_decay_ratio_lower_bound"] < self.minimum_bootstrap_decay_ratio_lower_bound:
            failures.append(f"{label}: bootstrap decay-ratio lower bound below threshold")
        return failures

    def _aggregate_summary(self, split_summaries: list[dict[str, float]]) -> dict[str, float]:
        keys = (
            "train_rows",
            "test_rows",
            "train_abs_mean_drift_bps",
            "test_abs_mean_drift_bps",
            "test_hit_rate",
            "regime_coverage",
            "drift_decay_ratio",
            "unseen_edge_rate",
            "test_fill_rate",
            "test_cancel_rate",
            "execution_drift_tracking_error_bps",
            "kill_switch_rate",
            "bootstrap_hit_rate_mean",
            "bootstrap_hit_rate_lower_bound",
            "bootstrap_hit_rate_upper_bound",
            "bootstrap_decay_ratio_mean",
            "bootstrap_decay_ratio_lower_bound",
            "bootstrap_decay_ratio_upper_bound",
        )
        return {
            f"mean_{key}": float(sum(summary[key] for summary in split_summaries) / max(len(split_summaries), 1))
            for key in keys
        }

    def _bootstrap_metrics(self, train_frame: pd.DataFrame, test_frame: pd.DataFrame) -> dict[str, float]:
        empty = {
            "bootstrap_hit_rate_mean": 0.0,
            "bootstrap_hit_rate_lower_bound": 0.0,
            "bootstrap_hit_rate_upper_bound": 0.0,
            "bootstrap_decay_ratio_mean": 0.0,
            "bootstrap_decay_ratio_lower_bound": 0.0,
            "bootstrap_decay_ratio_upper_bound": 0.0,
        }
        if self.bootstrap_sample_count <= 0 or test_frame.empty:
            return empty

        train_abs_mean = float(train_frame[self.drift_column].abs().mean()) if not train_frame.empty else 0.0
        rng = np.random.default_rng(self.bootstrap_random_seed)
        hit_rates: list[float] = []
        decay_ratios: list[float] = []
        test_drifts = test_frame[self.drift_column].to_numpy(dtype=float)
        for _ in range(self.bootstrap_sample_count):
            sample = rng.choice(test_drifts, size=len(test_drifts), replace=True)
            hit_rates.append(float(np.mean(sample > 0.0)))
            sample_abs_mean = float(np.mean(np.abs(sample))) if sample.size else 0.0
            decay_ratios.append(sample_abs_mean / max(train_abs_mean, 1e-9))

        lower_q = max((1.0 - self.bootstrap_confidence_level) / 2.0, 0.0)
        upper_q = min(1.0 - lower_q, 1.0)
        return {
            "bootstrap_hit_rate_mean": float(np.mean(hit_rates)),
            "bootstrap_hit_rate_lower_bound": float(np.quantile(hit_rates, lower_q)),
            "bootstrap_hit_rate_upper_bound": float(np.quantile(hit_rates, upper_q)),
            "bootstrap_decay_ratio_mean": float(np.mean(decay_ratios)),
            "bootstrap_decay_ratio_lower_bound": float(np.quantile(decay_ratios, lower_q)),
            "bootstrap_decay_ratio_upper_bound": float(np.quantile(decay_ratios, upper_q)),
        }

    def _prepare_execution_frame(self, frame: pd.DataFrame | None) -> pd.DataFrame:
        if frame is None or frame.empty:
            return pd.DataFrame(columns=[self.execution_timestamp_column])
        execution = frame.copy()
        if self.execution_timestamp_column not in execution.columns and "timestamp_ns" in execution.columns:
            execution[self.execution_timestamp_column] = pd.to_datetime(execution["timestamp_ns"], unit="ns", utc=True)
        elif self.execution_timestamp_column in execution.columns:
            execution[self.execution_timestamp_column] = pd.to_datetime(execution[self.execution_timestamp_column], utc=True)
        else:
            raise ValueError("execution validation frame is missing a timestamp column")
        return execution

    def _execution_window(self, frame: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
        if frame.empty:
            return frame.copy()
        start_ts = pd.Timestamp(start, tz="UTC")
        end_ts = pd.Timestamp(end, tz="UTC")
        return frame[(frame[self.execution_timestamp_column] >= start_ts) & (frame[self.execution_timestamp_column] <= end_ts)].copy()

    def _execution_mean(self, frame: pd.DataFrame, column: str) -> float:
        if frame.empty or column not in frame.columns:
            return 0.0
        values = pd.to_numeric(frame[column], errors="coerce").dropna()
        return float(values.mean()) if not values.empty else 0.0

    def _drift_tracking_error(self, frame: pd.DataFrame) -> float:
        if frame.empty:
            return 0.0
        required = {self.execution_expected_drift_column, self.execution_realized_drift_column}
        if not required.issubset(frame.columns):
            return 0.0
        paired = frame[[self.execution_expected_drift_column, self.execution_realized_drift_column]].apply(
            pd.to_numeric,
            errors="coerce",
        ).dropna()
        if paired.empty:
            return 0.0
        errors = (paired[self.execution_expected_drift_column] - paired[self.execution_realized_drift_column]).abs()
        return float(errors.mean())

    def _kill_switch_rate(self, frame: pd.DataFrame) -> float:
        if frame.empty or self.execution_kill_switch_column not in frame.columns:
            return 0.0
        values = frame[self.execution_kill_switch_column].astype(bool)
        return float(values.mean()) if not values.empty else 0.0

    def _require_columns(self, frame: pd.DataFrame) -> None:
        required = (
            self.timestamp_column,
            self.regime_column,
            self.drift_column,
            self.edge_from_column,
            self.edge_to_column,
        )
        missing = [column for column in required if column not in frame.columns]
        if missing:
            raise ValueError(f"validation dataset is missing required columns: {missing}")