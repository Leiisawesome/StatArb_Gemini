"""Execution-aware simulator with latency and state-alignment checks."""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, log1p

import numpy as np

from .calibration.interfaces import ExecutionCalibrationArtifact
from .config import ExecutionConfig
from .decision import TradeAction, TradeIntent
from .features import ObservedState


@dataclass(frozen=True, slots=True)
class ExecutionRequest:
    symbol: str
    action: TradeAction
    quantity: int
    decision_timestamp_ns: int
    executable_timestamp_ns: int
    expected_state: ObservedState
    intent: TradeIntent


@dataclass(frozen=True, slots=True)
class ExecutionReport:
    symbol: str
    action: TradeAction
    status: str
    quantity: int
    fill_price: float | None
    alignment_probability: float
    fill_probability: float
    slippage_bps: float
    reason: str
    timestamp_ns: int


class ExecutionSimulator:
    def __init__(
        self,
        config: ExecutionConfig | None = None,
        execution_calibration: ExecutionCalibrationArtifact | None = None,
    ):
        self.config = config or ExecutionConfig()
        self.execution_calibration = execution_calibration

    def build_request(self, intent: TradeIntent, state: ObservedState, quantity: int) -> ExecutionRequest:
        return ExecutionRequest(
            symbol=state.symbol,
            action=intent.action,
            quantity=quantity,
            decision_timestamp_ns=state.timestamp_ns,
            executable_timestamp_ns=state.timestamp_ns + self.config.latency_ns,
            expected_state=state,
            intent=intent,
        )

    def execute(self, request: ExecutionRequest, realized_state: ObservedState) -> ExecutionReport:
        alignment_probability = self.state_alignment_probability(request.expected_state, realized_state)
        if alignment_probability < self.config.alignment_probability_threshold:
            return ExecutionReport(
                symbol=request.symbol,
                action=request.action,
                status="cancelled",
                quantity=0,
                fill_price=None,
                alignment_probability=alignment_probability,
                fill_probability=0.0,
                slippage_bps=0.0,
                reason="state alignment failed",
                timestamp_ns=realized_state.timestamp_ns,
            )

        spread_bps = (realized_state.book.spread / max(realized_state.book.midpoint, 1e-6)) * 10_000.0
        regime = request.intent.edge.regime.value
        queue_penalty = self._queue_penalty(request, realized_state)
        fill_probability = self._fill_probability(alignment_probability, spread_bps, regime, queue_penalty)
        slippage_bps = min(
            self.config.max_slippage_bps,
            self._slippage_bps(spread_bps, request.intent.posterior.mean_bps, request.intent.posterior.threshold_bps, regime),
        )
        touch = realized_state.book.ask_price if request.action is TradeAction.BUY else realized_state.book.bid_price
        fill_multiplier = 1.0 + slippage_bps / 10_000.0 if request.action is TradeAction.BUY else 1.0 - slippage_bps / 10_000.0
        fill_price = touch * fill_multiplier

        return ExecutionReport(
            symbol=request.symbol,
            action=request.action,
            status="filled" if fill_probability > 0.0 else "rejected",
            quantity=request.quantity if fill_probability > 0.0 else 0,
            fill_price=float(fill_price) if fill_probability > 0.0 else None,
            alignment_probability=alignment_probability,
            fill_probability=fill_probability,
            slippage_bps=float(slippage_bps),
            reason="executed at forward shifted state" if fill_probability > 0.0 else "fill probability collapsed",
            timestamp_ns=realized_state.timestamp_ns,
        )

    @staticmethod
    def state_alignment_probability(expected_state: ObservedState, realized_state: ObservedState) -> float:
        distance = float(np.linalg.norm(expected_state.vector - realized_state.vector))
        return float(exp(-0.5 * distance * distance))

    def _fill_probability(self, alignment_probability: float, spread_bps: float, regime: str, queue_penalty: float) -> float:
        if self.execution_calibration is None:
            fill_probability = self.config.base_fill_probability * alignment_probability * max(0.2, 1.0 - spread_bps / 50.0)
            fill_probability *= exp(-queue_penalty)
            return float(min(max(fill_probability, 0.0), 1.0))

        regime_multiplier = self.execution_calibration.regime_fill_multipliers.get(regime, 1.0)
        score = (
            self.execution_calibration.fill_probability_intercept
            + self.execution_calibration.alignment_weight * alignment_probability
            - self.execution_calibration.spread_penalty * spread_bps
            - queue_penalty
        )
        fill_probability = regime_multiplier / (1.0 + exp(-score))
        return float(min(max(fill_probability, 0.0), 1.0))

    def _queue_penalty(self, request: ExecutionRequest, realized_state: ObservedState) -> float:
        if self.config.queue_penalty_weight <= 0.0:
            return 0.0

        touch_depth = realized_state.book.ask_size if request.action is TradeAction.BUY else realized_state.book.bid_size
        reference_depth = max(float(touch_depth), self.config.queue_reference_size, 1.0)
        queue_load = max(float(request.quantity), 0.0) / reference_depth
        adjusted_load = queue_load ** max(self.config.queue_penalty_exponent, 0.0)
        return float(self.config.queue_penalty_weight * log1p(adjusted_load))

    def _slippage_bps(
        self,
        spread_bps: float,
        posterior_mean_bps: float,
        posterior_threshold_bps: float,
        regime: str,
    ) -> float:
        if self.execution_calibration is None:
            return self.config.base_slippage_bps + 0.5 * spread_bps + self.config.adverse_selection_penalty * spread_bps

        regime_multiplier = self.execution_calibration.regime_slippage_multipliers.get(regime, 1.0)
        expected_edge_excess = max(abs(posterior_mean_bps) - posterior_threshold_bps, 0.0)
        slippage_bps = (
            self.execution_calibration.slippage_intercept_bps
            + self.execution_calibration.spread_slippage_weight * spread_bps
            + self.execution_calibration.adverse_selection_weight * expected_edge_excess
        )
        return float(slippage_bps * regime_multiplier)