"""Simulator-only paper runner for the successor package."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

import pandas as pd

from l1_microstructure.artifacts import RuntimeArtifactBundle
from l1_microstructure.config import FrameworkConfig
from l1_microstructure.events import MarketEvent
from l1_microstructure.monitoring import InMemoryMonitoringSink, RuntimeMonitor
from l1_microstructure.pipeline import FrameworkUpdate, L1MicrostructureStateMachine
from l1_microstructure.replay import DeterministicReplayEngine

from .interfaces import RunnerConfig


@dataclass(slots=True)
class SimulatorPaperTradingRunner:
    events: Iterable[MarketEvent]
    framework_config: FrameworkConfig | None = None
    runtime_artifacts: RuntimeArtifactBundle | None = None
    monitoring_sink: InMemoryMonitoringSink | None = None
    replay_engine: DeterministicReplayEngine | None = None
    is_running: bool = False
    updates: list[FrameworkUpdate] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.framework_config = self.framework_config or FrameworkConfig()
        self.runtime_artifacts = self.runtime_artifacts or RuntimeArtifactBundle()
        self.monitoring_sink = self.monitoring_sink or InMemoryMonitoringSink()
        self.replay_engine = self.replay_engine or DeterministicReplayEngine()

    def start(self, config: RunnerConfig) -> None:
        self.is_running = True
        self.updates = []
        machine = L1MicrostructureStateMachine(self.framework_config, runtime_artifacts=self.runtime_artifacts)
        monitor = RuntimeMonitor(self.monitoring_sink)
        selected_symbols = set(config.symbols)

        for event in self.replay_engine.replay(self.events):
            if not self.is_running:
                break
            if event.symbol not in selected_symbols:
                continue
            update = machine.on_event(event)
            if update is None:
                continue
            self.updates.append(update)
            monitor.publish_update(update, machine)

        self.is_running = False

    def stop(self) -> None:
        self.is_running = False

    def monitoring_frame(self) -> pd.DataFrame:
        return self.monitoring_sink.to_frame()

    def execution_summary(self) -> dict[str, float]:
        if not self.updates:
            return {"update_count": 0.0, "fill_count": 0.0, "cancel_count": 0.0}
        reports = [report for update in self.updates for report in update.execution_reports]
        fill_count = sum(1 for report in reports if report.status == "filled")
        cancel_count = sum(1 for report in reports if report.status == "cancelled")
        return {
            "update_count": float(len(self.updates)),
            "fill_count": float(fill_count),
            "cancel_count": float(cancel_count),
        }