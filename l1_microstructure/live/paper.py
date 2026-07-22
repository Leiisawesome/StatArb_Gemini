"""Simulator-only paper runner for the successor package."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Iterable

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
    retain_updates: bool = True
    is_running: bool = False
    updates: list[FrameworkUpdate] = field(default_factory=list)
    _update_count: int = field(default=0, init=False)
    _fill_count: int = field(default=0, init=False)
    _cancel_count: int = field(default=0, init=False)
    _transition_count: int = field(default=0, init=False)
    _actionable_intent_count: int = field(default=0, init=False)
    _risk_approved_count: int = field(default=0, init=False)
    _intent_action_counts: Counter[str] = field(default_factory=Counter, init=False)
    _intent_reason_counts: Counter[str] = field(default_factory=Counter, init=False)
    _risk_reason_counts: Counter[str] = field(default_factory=Counter, init=False)

    def __post_init__(self) -> None:
        self.framework_config = self.framework_config or FrameworkConfig()
        self.runtime_artifacts = self.runtime_artifacts or RuntimeArtifactBundle()
        self.monitoring_sink = self.monitoring_sink or InMemoryMonitoringSink()
        self.replay_engine = self.replay_engine or DeterministicReplayEngine()

    def start(self, config: RunnerConfig) -> None:
        self.is_running = True
        self.updates = []
        self._update_count = 0
        self._fill_count = 0
        self._cancel_count = 0
        self._transition_count = 0
        self._actionable_intent_count = 0
        self._risk_approved_count = 0
        self._intent_action_counts.clear()
        self._intent_reason_counts.clear()
        self._risk_reason_counts.clear()
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
            self._update_count += 1
            if update.transition_edge is not None:
                self._transition_count += 1
            if update.intent is not None:
                action = update.intent.action.value
                self._intent_action_counts[action] += 1
                self._intent_reason_counts[update.intent.reason] += 1
                if action in {"buy", "sell"}:
                    self._actionable_intent_count += 1
            if update.risk_decision is not None:
                self._risk_reason_counts[update.risk_decision.reason] += 1
                self._risk_approved_count += int(update.risk_decision.approved)
            for report in update.execution_reports:
                self._fill_count += int(report.status == "filled")
                self._cancel_count += int(report.status == "cancelled")
            if self.retain_updates:
                self.updates.append(update)
            monitor.publish_update(update, machine)

        self.is_running = False

    def stop(self) -> None:
        self.is_running = False

    def monitoring_frame(self) -> pd.DataFrame:
        return self.monitoring_sink.to_frame()

    def execution_summary(self) -> dict[str, float]:
        if self.retain_updates:
            reports = (report for update in self.updates for report in update.execution_reports)
            fill_count = 0
            cancel_count = 0
            for report in reports:
                fill_count += int(report.status == "filled")
                cancel_count += int(report.status == "cancelled")
            return {
                "update_count": float(len(self.updates)),
                "fill_count": float(fill_count),
                "cancel_count": float(cancel_count),
            }
        return {
            "update_count": float(self._update_count),
            "fill_count": float(self._fill_count),
            "cancel_count": float(self._cancel_count),
        }

    def activation_summary(self) -> dict[str, Any]:
        """Return decision-funnel evidence without retaining every framework update."""
        return {
            "transition_count": self._transition_count,
            "actionable_intent_count": self._actionable_intent_count,
            "risk_approved_count": self._risk_approved_count,
            "intent_action_counts": dict(sorted(self._intent_action_counts.items())),
            "intent_reason_counts": dict(sorted(self._intent_reason_counts.items())),
            "risk_reason_counts": dict(sorted(self._risk_reason_counts.items())),
        }
