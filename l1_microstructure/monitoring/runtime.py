"""Runtime monitoring helpers for successor-package replay and paper workflows."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from l1_microstructure.pipeline import FrameworkUpdate, L1MicrostructureStateMachine

from .alerts import OperationalAlertManager
from .interfaces import AlertCategory, AlertSeverity, OperationalAlert, RuntimeSnapshot


class InMemoryMonitoringSink:
    def __init__(self, *, max_snapshots: int | None = None):
        if max_snapshots is not None and max_snapshots < 1:
            raise ValueError("max_snapshots must be positive")
        self.max_snapshots = max_snapshots
        self.snapshots: list[RuntimeSnapshot] = []
        self.alerts: list[OperationalAlert] = []
        self.published_snapshot_count = 0
        self.sampling_stride = 1

    def publish(self, snapshot: RuntimeSnapshot) -> None:
        self.published_snapshot_count += 1
        if self.max_snapshots is not None:
            if self.published_snapshot_count % self.sampling_stride:
                return
            if len(self.snapshots) >= self.max_snapshots:
                # Keep observations aligned to the doubled stride. With
                # one-based publication indexes these are the second, fourth,
                # and subsequent even slots in the current sample.
                self.snapshots = self.snapshots[1::2]
                self.sampling_stride *= 2
                if self.published_snapshot_count % self.sampling_stride:
                    return
        self.snapshots.append(snapshot)

    def publish_alert(self, alert: OperationalAlert) -> None:
        self.alerts.append(alert)

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "timestamp_ns": snapshot.timestamp_ns,
                    "state_label": snapshot.state_label,
                    "dominant_regime": snapshot.dominant_regime,
                    "entropy": snapshot.entropy,
                    "alpha_score": snapshot.alpha_score,
                    **snapshot.metadata,
                }
                for snapshot in self.snapshots
            ]
        )

    def alerts_frame(self) -> pd.DataFrame:
        return pd.DataFrame([alert.to_dict() for alert in self.alerts])


class JsonlMonitoringSink:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Keep the handle open and use line-buffering so each "\n"-terminated
        # write is flushed to the OS immediately without explicit flush() calls.
        self._handle = self.path.open("a", encoding="utf-8", buffering=1)

    def publish(self, snapshot: RuntimeSnapshot) -> None:
        record = {"record_type": "snapshot", **asdict(snapshot)}
        self._handle.write(json.dumps(record, sort_keys=True) + "\n")

    def publish_alert(self, alert: OperationalAlert) -> None:
        record = {"record_type": "alert", **alert.to_dict()}
        self._handle.write(json.dumps(record, sort_keys=True) + "\n")

    def close(self) -> None:
        self._handle.close()

    def __del__(self) -> None:
        try:
            self._handle.close()
        except Exception:
            pass


class RuntimeMonitor:
    def __init__(self, sink: InMemoryMonitoringSink | JsonlMonitoringSink):
        self.sink = sink
        self.alerts = OperationalAlertManager(sink)

    def publish_alert(
        self,
        severity: AlertSeverity,
        category: AlertCategory,
        code: str,
        message: str,
        *,
        symbol: str | None = None,
        metadata: dict | None = None,
        timestamp_ns: int | None = None,
    ) -> OperationalAlert | None:
        return self.alerts.emit(
            severity,
            category,
            code,
            message,
            symbol=symbol,
            metadata=metadata,
            timestamp_ns=timestamp_ns,
        )

    def publish_update(self, update: FrameworkUpdate, machine: L1MicrostructureStateMachine) -> RuntimeSnapshot:
        total_reports = max(len(machine.execution_history), 1)
        resolved_realized_drift = None
        if update.resolved_outcomes:
            resolved_realized_drift = float(
                sum(drift for _, drift in update.resolved_outcomes) / len(update.resolved_outcomes)
            )

        edge_count = 0
        if update.transition_edge is not None:
            edge_count = machine.transition_kernel.get_edge(update.transition_edge).count

        expected_drift_bps = update.intent.posterior.mean_bps if update.intent is not None else None
        snapshot = RuntimeSnapshot(
            timestamp_ns=update.state.timestamp_ns,
            state_label=update.state.label,
            dominant_regime=update.regime.dominant_regime.value,
            entropy=update.diagnostic.entropy if update.diagnostic is not None else 0.0,
            alpha_score=update.diagnostic.alpha_score if update.diagnostic is not None else 0.0,
            metadata={
                "symbol": update.state.symbol,
                "edge_activation_count": edge_count,
                "fill_rate": machine.fill_count / total_reports,
                "cancel_rate": machine.cancel_count / total_reports,
                "expected_drift_bps": expected_drift_bps,
                "realized_drift_bps": resolved_realized_drift,
                "kill_switch_active": machine.risk_engine.halted,
                "trade_count": machine.risk_engine.trade_count,
            },
        )
        self.sink.publish(snapshot)
        return snapshot
