"""Execution-aware simulator with latency and state-alignment checks."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import blake2b
from math import exp, log1p
from uuid import uuid4

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
    client_order_id: str = ""

    def __post_init__(self) -> None:
        if not self.client_order_id:
            object.__setattr__(self, "client_order_id", uuid4().hex)


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
    client_order_id: str | None = None
    external_order_id: str | None = None


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
        queue_survival_probability = self._queue_survival_probability(request, realized_state)
        aggressiveness = self._aggressiveness_scale(request)
        fill_probability = self._fill_probability(alignment_probability, spread_bps, regime, queue_survival_probability)
        fill_probability *= aggressiveness
        slippage_bps = min(
            self.config.max_slippage_bps,
            self._slippage_bps(
                spread_bps,
                request.intent.posterior.mean_bps,
                request.intent.posterior.threshold_bps,
                regime,
            ) * aggressiveness,
        )
        touch = realized_state.book.ask_price if request.action == TradeAction.BUY else realized_state.book.bid_price
        fill_multiplier = 1.0 + slippage_bps / 10_000.0 if request.action == TradeAction.BUY else 1.0 - slippage_bps / 10_000.0
        fill_price = touch * fill_multiplier
        filled = self._did_fill(request, realized_state, fill_probability)

        return ExecutionReport(
            symbol=request.symbol,
            action=request.action,
            status="filled" if filled else "rejected",
            quantity=request.quantity if filled else 0,
            fill_price=float(fill_price) if filled else None,
            alignment_probability=alignment_probability,
            fill_probability=fill_probability,
            slippage_bps=float(slippage_bps),
            reason=self._fill_reason(request) if filled else "fill draw exceeded probability",
            timestamp_ns=realized_state.timestamp_ns,
        )

    @staticmethod
    def state_alignment_probability(expected_state: ObservedState, realized_state: ObservedState) -> float:
        distance = float(
            np.linalg.norm(
                ExecutionSimulator._scaled_state_delta(
                    expected_state.vector,
                    realized_state.vector,
                )
            )
        )
        return float(exp(-0.5 * distance * distance))

    @staticmethod
    def _scaled_state_delta(expected_vector: np.ndarray, realized_vector: np.ndarray) -> np.ndarray:
        scale = np.maximum(np.maximum(np.abs(expected_vector), np.abs(realized_vector)), 1.0)
        return (expected_vector - realized_vector) / scale

    @staticmethod
    def _fill_reason(request: ExecutionRequest) -> str:
        if request.intent.reason.endswith("invalidation"):
            return request.intent.reason
        return "executed at forward shifted state"

    def _fill_probability(
        self,
        alignment_probability: float,
        spread_bps: float,
        regime: str,
        queue_survival_probability: float,
    ) -> float:
        if self.execution_calibration is None:
            fill_probability = self.config.base_fill_probability * alignment_probability * max(0.2, 1.0 - spread_bps / 50.0)
            fill_probability *= queue_survival_probability
            return float(min(max(fill_probability, 0.0), 1.0))

        regime_multiplier = self.execution_calibration.regime_fill_multipliers.get(regime, 1.0)
        queue_survival_probability = min(max(queue_survival_probability, self.config.queue_survival_floor), 1.0)
        queue_log_odds = np.log(queue_survival_probability / max(1.0 - queue_survival_probability, 1e-6))
        score = (
            self.execution_calibration.fill_probability_intercept
            + self.execution_calibration.alignment_weight * alignment_probability
            - self.execution_calibration.spread_penalty * spread_bps
            + queue_log_odds
        )
        fill_probability = regime_multiplier / (1.0 + exp(-score))
        return float(min(max(fill_probability, 0.0), 1.0))

    def _did_fill(self, request: ExecutionRequest, realized_state: ObservedState, fill_probability: float) -> bool:
        if fill_probability <= 0.0:
            return False
        if fill_probability >= 1.0:
            return True
        return self._fill_uniform(request, realized_state) < fill_probability

    @staticmethod
    def _fill_uniform(request: ExecutionRequest, realized_state: ObservedState) -> float:
        payload = "|".join(
            [
                request.symbol,
                request.action.value,
                str(request.quantity),
                str(request.decision_timestamp_ns),
                str(request.executable_timestamp_ns),
                str(realized_state.timestamp_ns),
                f"{realized_state.book.bid_price:.8f}",
                f"{realized_state.book.ask_price:.8f}",
                str(realized_state.book.bid_size),
                str(realized_state.book.ask_size),
                realized_state.label,
                request.intent.reason,
            ]
        )
        digest = blake2b(payload.encode("ascii"), digest_size=8).digest()
        return int.from_bytes(digest, byteorder="big", signed=False) / 2**64

    def _queue_survival_probability(self, request: ExecutionRequest, realized_state: ObservedState) -> float:
        touch_depth = realized_state.book.ask_size if request.action == TradeAction.BUY else realized_state.book.bid_size
        reference_depth = max(float(touch_depth), self.config.queue_reference_size, 1.0)
        queue_load = max(float(request.quantity), 0.0) / reference_depth
        adjusted_load = queue_load ** max(self.config.queue_penalty_exponent, 0.0)
        direction = 1.0 if request.action == TradeAction.BUY else -1.0
        same_side_pressure = max(
            direction * (realized_state.trade_pressure + 0.5 * realized_state.quote_pressure),
            0.0,
        )
        latency_ms = max(
            float(request.executable_timestamp_ns - request.decision_timestamp_ns) / 1_000_000.0,
            0.0,
        )
        reference_latency_ms = max(float(self.config.latency_ms), 1.0)
        hazard = self.config.queue_penalty_weight * log1p(adjusted_load)
        hazard += self.config.queue_pressure_weight * same_side_pressure
        hazard += self.config.queue_latency_weight * (latency_ms / reference_latency_ms)
        if hazard <= 0.0:
            return 1.0
        survival = exp(-hazard)
        return float(min(max(survival, self.config.queue_survival_floor), 1.0))

    def _aggressiveness_scale(self, request: ExecutionRequest) -> float:
        confidence = min(max(request.intent.observation_confidence, 0.0), 1.0)
        floor = min(max(self.config.confidence_aggressiveness_floor, 0.0), 1.0)
        return float(floor + (1.0 - floor) * confidence)

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
