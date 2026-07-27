"""Typed, versioned recovery snapshots for the state-machine facade."""

from __future__ import annotations

from collections import deque
from copy import deepcopy
from dataclasses import dataclass
from math import isfinite
from typing import Deque, Protocol

import numpy as np

from .config import FrameworkConfig
from .events import BookSnapshot, QuoteEvent
from .execution import ExecutionReport, ExecutionRequest
from .features import FeatureEngine, ObservedState
from .regime import MicrostructureRegime, RegimeInferencer
from .risk import OpenPosition, RiskEngine
from .transitions import EdgeKey, EdgeStatistics, TransitionKernel


RECOVERY_SNAPSHOT_VERSION = 1


@dataclass(slots=True)
class PendingOutcome:
    edge: EdgeKey
    reference_price: float
    resolve_timestamp_ns: int


@dataclass(frozen=True, slots=True)
class RiskRecoveryState:
    starting_equity: float
    peak_equity: float
    realized_pnl: float
    trade_count: int
    halted: bool


@dataclass(frozen=True, slots=True)
class FeatureRecoveryState:
    current_book: BookSnapshot | None
    quote_history: list[QuoteEvent]
    microprice_history: list[tuple[int, float]]
    trade_pressure_window: list[tuple[int, float]]
    spread_norm_history: list[float]
    volatility_history: list[float]
    flicker_baseline: float
    flicker_intensity: float
    last_quote_ts: int | None
    active_regime_hint: str | None


@dataclass(frozen=True, slots=True)
class RegimeRecoveryState:
    state_window: list[ObservedState]
    previous_probabilities: dict[MicrostructureRegime, float] | None
    previous_timestamp_ns: int | None


@dataclass(frozen=True, slots=True)
class TransitionRecoveryState:
    edge_stats: dict[EdgeKey, EdgeStatistics]
    outgoing_counts: dict[tuple[str, MicrostructureRegime], dict[str, int]]
    increment_history: list[np.ndarray]
    observation_index: int


@dataclass(frozen=True, slots=True)
class StateMachineRecoverySnapshot:
    previous_state: ObservedState | None
    pending_outcomes: list[PendingOutcome]
    pending_orders: list[ExecutionRequest]
    open_positions: dict[str, OpenPosition]
    execution_history: list[ExecutionReport]
    signal_expectations: dict[str, float]
    last_midpoints: dict[str, float]
    return_history: dict[str, list[float]]
    realized_volatility_by_symbol: dict[str, float]
    risk_state: RiskRecoveryState
    feature_state: FeatureRecoveryState
    regime_state: RegimeRecoveryState
    transition_state: TransitionRecoveryState
    symbol: str | None = None
    version: int = RECOVERY_SNAPSHOT_VERSION


class RecoveryTarget(Protocol):
    config: FrameworkConfig
    symbol: str | None
    previous_state: ObservedState | None
    pending_outcomes: Deque[PendingOutcome]
    pending_orders: Deque[ExecutionRequest]
    open_positions: dict[str, OpenPosition]
    execution_history: list[ExecutionReport]
    fill_count: int
    cancel_count: int
    signal_expectations: dict[str, float]
    last_midpoints: dict[str, float]
    return_history: dict[str, Deque[float]]
    realized_volatility_by_symbol: dict[str, float]
    risk_engine: RiskEngine
    feature_engine: FeatureEngine
    regime_inferencer: RegimeInferencer
    transition_kernel: TransitionKernel


class StateMachineRecoveryCodec:
    """Capture and restore state without exposing subordinate engine internals."""

    @staticmethod
    def snapshot(machine: RecoveryTarget) -> StateMachineRecoverySnapshot:
        return StateMachineRecoverySnapshot(
            previous_state=deepcopy(machine.previous_state),
            pending_outcomes=deepcopy(list(machine.pending_outcomes)),
            pending_orders=deepcopy(list(machine.pending_orders)),
            open_positions=deepcopy(machine.open_positions),
            execution_history=deepcopy(machine.execution_history),
            signal_expectations=deepcopy(machine.signal_expectations),
            last_midpoints=deepcopy(machine.last_midpoints),
            return_history={symbol: list(history) for symbol, history in machine.return_history.items()},
            realized_volatility_by_symbol=deepcopy(machine.realized_volatility_by_symbol),
            risk_state=RiskRecoveryState(
                starting_equity=float(machine.risk_engine.starting_equity),
                peak_equity=float(machine.risk_engine.peak_equity),
                realized_pnl=float(machine.risk_engine.realized_pnl),
                trade_count=int(machine.risk_engine.trade_count),
                halted=bool(machine.risk_engine.halted),
            ),
            feature_state=FeatureRecoveryState(
                current_book=deepcopy(machine.feature_engine.current_book),
                quote_history=deepcopy(list(machine.feature_engine.quote_history)),
                microprice_history=deepcopy(list(machine.feature_engine.microprice_history)),
                trade_pressure_window=deepcopy(list(machine.feature_engine.trade_pressure_window)),
                spread_norm_history=deepcopy(list(machine.feature_engine.spread_norm_history)),
                volatility_history=deepcopy(list(machine.feature_engine.volatility_history)),
                flicker_baseline=float(machine.feature_engine.flicker_baseline),
                flicker_intensity=float(machine.feature_engine.flicker_intensity),
                last_quote_ts=machine.feature_engine.last_quote_ts,
                active_regime_hint=machine.feature_engine.active_regime_hint,
            ),
            regime_state=RegimeRecoveryState(
                state_window=deepcopy(list(machine.regime_inferencer.state_window)),
                previous_probabilities=deepcopy(machine.regime_inferencer.previous_probabilities),
                previous_timestamp_ns=machine.regime_inferencer.previous_timestamp_ns,
            ),
            transition_state=TransitionRecoveryState(
                edge_stats=deepcopy(machine.transition_kernel.edge_stats),
                outgoing_counts=deepcopy(dict(machine.transition_kernel.outgoing_counts)),
                increment_history=deepcopy(list(machine.transition_kernel.increment_history)),
                observation_index=int(machine.transition_kernel.observation_index),
            ),
            symbol=machine.symbol,
        )

    @classmethod
    def restore(cls, machine: RecoveryTarget, snapshot: StateMachineRecoverySnapshot) -> None:
        cls.validate(machine, snapshot)

        machine.symbol = snapshot.symbol or machine.symbol
        machine.previous_state = deepcopy(snapshot.previous_state)
        if machine.symbol is None and machine.previous_state is not None:
            machine.symbol = machine.previous_state.symbol
        machine.pending_outcomes = deque(deepcopy(snapshot.pending_outcomes))
        machine.pending_orders = deque(deepcopy(snapshot.pending_orders))
        machine.open_positions = deepcopy(snapshot.open_positions)
        machine.execution_history = deepcopy(snapshot.execution_history)
        machine.signal_expectations = deepcopy(snapshot.signal_expectations)
        machine.last_midpoints = deepcopy(snapshot.last_midpoints)
        machine.return_history = {
            symbol: deque(history, maxlen=machine.config.transition.covariance_history)
            for symbol, history in deepcopy(snapshot.return_history).items()
        }
        machine.realized_volatility_by_symbol = deepcopy(snapshot.realized_volatility_by_symbol)

        risk = snapshot.risk_state
        machine.risk_engine.starting_equity = risk.starting_equity
        machine.risk_engine.peak_equity = risk.peak_equity
        machine.risk_engine.realized_pnl = risk.realized_pnl
        machine.risk_engine.trade_count = risk.trade_count
        machine.risk_engine.halted = risk.halted

        feature = snapshot.feature_state
        machine.feature_engine.current_book = deepcopy(feature.current_book)
        machine.feature_engine.quote_history = deque(
            deepcopy(feature.quote_history),
            maxlen=machine.feature_engine.quote_history.maxlen,
        )
        machine.feature_engine.microprice_history = deque(deepcopy(feature.microprice_history))
        machine.feature_engine.trade_pressure_window = deque(deepcopy(feature.trade_pressure_window))
        machine.feature_engine.spread_norm_history = deque(
            deepcopy(feature.spread_norm_history),
            maxlen=machine.feature_engine.spread_norm_history.maxlen,
        )
        machine.feature_engine.volatility_history = deque(
            deepcopy(feature.volatility_history),
            maxlen=machine.feature_engine.volatility_history.maxlen,
        )
        machine.feature_engine.rebuild_rolling_caches()
        machine.feature_engine.flicker_baseline = feature.flicker_baseline
        machine.feature_engine.flicker_intensity = feature.flicker_intensity
        machine.feature_engine.last_quote_ts = feature.last_quote_ts
        machine.feature_engine.active_regime_hint = feature.active_regime_hint

        regime = snapshot.regime_state
        machine.regime_inferencer.state_window = deque(deepcopy(regime.state_window))
        machine.regime_inferencer.rebuild_context_sums()
        machine.regime_inferencer.previous_probabilities = deepcopy(regime.previous_probabilities)
        machine.regime_inferencer.previous_timestamp_ns = regime.previous_timestamp_ns

        transition = snapshot.transition_state
        machine.transition_kernel.edge_stats = deepcopy(transition.edge_stats)
        machine.transition_kernel.outgoing_counts.clear()
        for key, value in deepcopy(transition.outgoing_counts).items():
            machine.transition_kernel.outgoing_counts[key].update(value)
        machine.transition_kernel.increment_history = deque(
            deepcopy(transition.increment_history),
            maxlen=machine.transition_kernel.increment_history.maxlen,
        )
        machine.transition_kernel.observation_index = transition.observation_index
        machine.transition_kernel._precision_matrix = None
        machine.transition_kernel._precision_stale_count = 0

        machine.fill_count = sum(1 for report in machine.execution_history if report.status == "filled")
        machine.cancel_count = sum(1 for report in machine.execution_history if report.status == "cancelled")

    @staticmethod
    def validate(machine: RecoveryTarget, snapshot: StateMachineRecoverySnapshot) -> None:
        if not isinstance(snapshot, StateMachineRecoverySnapshot):
            raise TypeError("state machine recovery requires a StateMachineRecoverySnapshot")
        if snapshot.version != RECOVERY_SNAPSHOT_VERSION:
            raise ValueError(
                f"unsupported recovery snapshot version {snapshot.version}; expected {RECOVERY_SNAPSHOT_VERSION}"
            )
        if not isinstance(snapshot.risk_state, RiskRecoveryState):
            raise TypeError("recovery snapshot risk state has an invalid type")
        if not isinstance(snapshot.feature_state, FeatureRecoveryState):
            raise TypeError("recovery snapshot feature state has an invalid type")
        if not isinstance(snapshot.regime_state, RegimeRecoveryState):
            raise TypeError("recovery snapshot regime state has an invalid type")
        if not isinstance(snapshot.transition_state, TransitionRecoveryState):
            raise TypeError("recovery snapshot transition state has an invalid type")

        state_symbol = snapshot.previous_state.symbol if snapshot.previous_state is not None else None
        snapshot_symbol = snapshot.symbol or state_symbol
        if snapshot.symbol is not None and state_symbol is not None and snapshot.symbol != state_symbol:
            raise ValueError("recovery snapshot symbol does not match its previous state")
        if machine.symbol is not None and snapshot_symbol is not None and machine.symbol != snapshot_symbol:
            raise ValueError(f"snapshot symbol {snapshot_symbol} does not match state machine symbol {machine.symbol}")

        owned_symbols = set(snapshot.open_positions) | set(snapshot.return_history)
        owned_symbols.update(request.symbol for request in snapshot.pending_orders)
        owned_symbols.update(report.symbol for report in snapshot.execution_history)
        if snapshot_symbol is not None and any(symbol != snapshot_symbol for symbol in owned_symbols):
            raise ValueError("recovery snapshot contains state for multiple symbols")
        if any(key != position.symbol for key, position in snapshot.open_positions.items()):
            raise ValueError("recovery snapshot position keys do not match position symbols")
        if any(request.expected_state.symbol != request.symbol for request in snapshot.pending_orders):
            raise ValueError("recovery snapshot order symbols do not match expected states")

        risk = snapshot.risk_state
        if risk.starting_equity <= 0 or risk.peak_equity <= 0 or risk.trade_count < 0:
            raise ValueError("recovery snapshot contains invalid risk state")
        if not all(isfinite(value) for value in (risk.starting_equity, risk.peak_equity, risk.realized_pnl)):
            raise ValueError("recovery snapshot contains non-finite risk values")

        feature = snapshot.feature_state
        if (
            feature.current_book is not None
            and snapshot_symbol is not None
            and feature.current_book.symbol != snapshot_symbol
        ):
            raise ValueError("recovery snapshot book symbol does not match snapshot symbol")
        numeric_feature_values = [
            feature.flicker_baseline,
            feature.flicker_intensity,
            *feature.spread_norm_history,
            *feature.volatility_history,
        ]
        if not all(isfinite(float(value)) for value in numeric_feature_values):
            raise ValueError("recovery snapshot contains non-finite feature values")

        probabilities = snapshot.regime_state.previous_probabilities
        if probabilities is not None:
            if not probabilities or any(
                not isinstance(regime, MicrostructureRegime)
                or not isfinite(float(probability))
                or float(probability) < 0.0
                for regime, probability in probabilities.items()
            ):
                raise ValueError("recovery snapshot contains invalid regime probabilities")
        numeric_history_values = [
            *snapshot.signal_expectations.values(),
            *snapshot.last_midpoints.values(),
            *snapshot.realized_volatility_by_symbol.values(),
            *(value for history in snapshot.return_history.values() for value in history),
        ]
        if not all(isfinite(float(value)) for value in numeric_history_values):
            raise ValueError("recovery snapshot contains non-finite history values")

        transition = snapshot.transition_state
        if transition.observation_index < 0:
            raise ValueError("recovery snapshot contains an invalid transition observation index")
        for increment in transition.increment_history:
            values = np.asarray(increment, dtype=float)
            if values.shape != (5,) or not np.all(np.isfinite(values)):
                raise ValueError("recovery snapshot contains an invalid transition increment")
