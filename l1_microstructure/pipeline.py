"""Orchestration layer for the L1 microstructure state machine."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Iterable

import numpy as np
import pandas as pd

from .artifacts.runtime import RuntimeArtifactBundle
from .config import FrameworkConfig
from .decision import DecisionEngine, TradeAction, TradeIntent
from .events import MarketEvent
from .execution import ExecutionReport, ExecutionRequest, ExecutionSimulator
from .features import FeatureEngine, ObservedState
from .portfolio import PortfolioAllocator
from .recovery import PendingOutcome, StateMachineRecoveryCodec, StateMachineRecoverySnapshot
from .regime import MicrostructureRegime, RegimeInferencer, RegimePosterior
from .risk import OpenPosition, RiskDecision, RiskEngine
from .transitions import EdgeKey, TransitionDiagnostic, TransitionKernel


@dataclass(slots=True)
class FrameworkUpdate:
    state: ObservedState
    regime: RegimePosterior
    transition_edge: EdgeKey | None = None
    diagnostic: TransitionDiagnostic | None = None
    intent: TradeIntent | None = None
    risk_decision: RiskDecision | None = None
    submitted_requests: list[ExecutionRequest] = field(default_factory=list)
    execution_reports: list[ExecutionReport] = field(default_factory=list)
    resolved_outcomes: list[tuple[EdgeKey, float]] = field(default_factory=list)


class L1MicrostructureStateMachine:
    def __init__(
        self,
        config: FrameworkConfig | None = None,
        runtime_artifacts: RuntimeArtifactBundle | None = None,
        route_orders_externally: bool = False,
    ):
        self.config = config or FrameworkConfig()
        self.runtime_artifacts = runtime_artifacts or RuntimeArtifactBundle()
        self.route_orders_externally = route_orders_externally
        artifact_symbols = {
            artifact.symbol
            for artifact in (
                self.runtime_artifacts.state_calibration,
                self.runtime_artifacts.regime_calibration,
                self.runtime_artifacts.execution_calibration,
            )
            if artifact is not None
        }
        if len(artifact_symbols) > 1:
            raise ValueError(f"runtime artifacts contain multiple symbols: {sorted(artifact_symbols)}")
        self.symbol: str | None = next(iter(artifact_symbols), None)
        self.feature_engine = FeatureEngine(self.config.feature, self.runtime_artifacts.state_calibration)
        self.regime_inferencer = RegimeInferencer(
            self.config.regime,
            self.config.feature,
            self.runtime_artifacts.regime_calibration,
        )
        self.transition_kernel = TransitionKernel(self.config.transition)
        if self.runtime_artifacts.transition_model is not None:
            self.transition_kernel.load_trained_payload(self.runtime_artifacts.transition_model)
        self.decision_engine = DecisionEngine(self.config.decision, self.config.transition)
        self.execution_simulator = ExecutionSimulator(
            self.config.execution,
            self.runtime_artifacts.execution_calibration,
        )
        self.risk_engine = RiskEngine(self.config.risk)
        self.portfolio_allocator = PortfolioAllocator(self.config.portfolio)

        self.previous_state: ObservedState | None = None
        self.pending_outcomes: Deque[PendingOutcome] = deque()
        self.pending_orders: Deque[ExecutionRequest] = deque()
        self.open_positions: dict[str, OpenPosition] = {}
        self.execution_history: list[ExecutionReport] = []
        self.fill_count: int = 0
        self.cancel_count: int = 0
        self.signal_expectations: dict[str, float] = {}
        self.last_midpoints: dict[str, float] = {}
        self.return_history: dict[str, Deque[float]] = {}
        self.realized_volatility_by_symbol: dict[str, float] = {}
        self.late_event_count: int = 0

    def snapshot_state(self) -> StateMachineRecoverySnapshot:
        return StateMachineRecoveryCodec.snapshot(self)

    def restore_state(self, snapshot: StateMachineRecoverySnapshot) -> None:
        StateMachineRecoveryCodec.restore(self, snapshot)

    def on_event(self, event: MarketEvent) -> FrameworkUpdate | None:
        if self.symbol is None:
            self.symbol = event.symbol
        elif event.symbol != self.symbol:
            raise ValueError(f"state machine for {self.symbol} cannot process event for {event.symbol}")
        if self.previous_state is not None and event.timestamp_ns < self.previous_state.timestamp_ns:
            self.late_event_count += 1
            return None
        state = self.feature_engine.update(event)
        if state is None:
            return None

        self._record_symbol_return(state)
        regime = self.regime_inferencer.update(state)
        self.feature_engine.set_regime_hint(regime.dominant_regime.value)
        resolved_outcomes = self._resolve_pending_outcomes(state)
        execution_reports = self._process_pending_orders(state)
        if self.route_orders_externally:
            submitted_requests = self._manage_open_position_requests(state, regime)
        else:
            submitted_requests = []
            execution_reports.extend(self._manage_open_positions(state, regime))

        transition_edge = None
        diagnostic = None
        intent = None
        risk_decision = None

        if self.previous_state is not None and self.transition_kernel.is_transition(
            self.previous_state.vector, state.vector
        ):
            transition_edge = EdgeKey(self.previous_state.label, state.label, regime.dominant_regime)
            edge_stats = self.transition_kernel.observe_transition(
                transition_edge,
                holding_time_ns=state.timestamp_ns - self.previous_state.timestamp_ns,
            )
            diagnostic = self.transition_kernel.diagnostic(transition_edge)
            self.pending_outcomes.append(
                PendingOutcome(
                    edge=transition_edge,
                    reference_price=state.book.microprice,
                    resolve_timestamp_ns=state.timestamp_ns + self.config.transition.drift_horizon_ns,
                )
            )
            intent = self.decision_engine.decide(transition_edge, edge_stats, diagnostic, regime, state)
            risk_decision = self._authorize_intent(intent, state)
            if risk_decision.approved:
                request = self.execution_simulator.build_request(intent, state, risk_decision.quantity)
                if self.route_orders_externally:
                    submitted_requests.append(request)
                else:
                    self.pending_orders.append(request)

        self.previous_state = state
        return FrameworkUpdate(
            state=state,
            regime=regime,
            transition_edge=transition_edge,
            diagnostic=diagnostic,
            intent=intent,
            risk_decision=risk_decision,
            submitted_requests=submitted_requests,
            execution_reports=execution_reports,
            resolved_outcomes=resolved_outcomes,
        )

    def ingest_execution_report(self, report: ExecutionReport) -> None:
        self.execution_history.append(report)
        self.risk_engine.process_fill(report)
        if report.status == "filled":
            self.fill_count += 1
            if report.fill_price is not None:
                self._update_position_from_fill(report)
        elif report.status == "cancelled":
            self.cancel_count += 1

    def run_replay(self, events: Iterable[MarketEvent]) -> list[FrameworkUpdate]:
        updates: list[FrameworkUpdate] = []
        for event in sorted(events, key=lambda current: current.timestamp_ns):
            update = self.on_event(event)
            if update is not None:
                updates.append(update)
        return updates

    def summarize_transition_edges(self) -> pd.DataFrame:
        rows = []
        for edge, stats in self.transition_kernel.edge_stats.items():
            diagnostic = self.transition_kernel.diagnostic(edge)
            rows.append(
                {
                    "from_state": edge.from_state,
                    "to_state": edge.to_state,
                    "regime": edge.regime.value,
                    "count": stats.count,
                    "mean_holding_time_ns": stats.mean_holding_time_ns,
                    "drift_mean_bps": stats.drift_mean_bps,
                    "drift_std_bps": stats.drift_std_bps,
                    "transition_probability": diagnostic.transition_probability,
                    "entropy": diagnostic.entropy,
                    "alpha_score": diagnostic.alpha_score,
                    "shrunk_drift_bps": diagnostic.shrunk_drift_bps,
                }
            )
        return pd.DataFrame(rows)

    def _authorize_intent(self, intent: TradeIntent, state: ObservedState) -> RiskDecision:
        if intent.action not in {TradeAction.BUY, TradeAction.SELL}:
            self.signal_expectations.pop(state.symbol, None)
            return self.risk_engine.authorize(intent, state)

        self.signal_expectations[state.symbol] = self._signal_strength(intent)
        target_fraction = self._portfolio_target_fraction(state.symbol)

        # Single pass over open_positions: compute gross/net/symbol/beta exposures together.
        # Also compute the trading symbol's beta once and reuse it for all three callers.
        equity = max(self.risk_engine.equity, 1e-6)
        sym_beta = self._estimate_symbol_beta(state.symbol)
        gross_notional = net_notional = beta_notional = 0.0
        symbol_signed_notional = 0.0
        for pos_symbol, position in self.open_positions.items():
            price = self._mark_price(pos_symbol, state.book.midpoint)
            direction = 1.0 if position.side == TradeAction.BUY else -1.0
            signed_notional = direction * position.quantity * price
            gross_notional += position.quantity * price
            net_notional += signed_notional
            pos_beta = sym_beta if pos_symbol == state.symbol else self._estimate_symbol_beta(pos_symbol)
            beta_notional += signed_notional * pos_beta
            if pos_symbol == state.symbol:
                symbol_signed_notional = signed_notional

        return self.risk_engine.authorize(
            intent,
            state,
            target_fraction=target_fraction,
            current_position=self.open_positions.get(state.symbol),
            current_gross_exposure=gross_notional / equity,
            current_net_exposure=net_notional / equity,
            current_symbol_exposure=symbol_signed_notional / equity,
            current_beta_exposure=beta_notional / equity,
            current_symbol_beta_exposure=symbol_signed_notional * sym_beta / equity,
            proposed_symbol_beta=sym_beta,
        )

    def _portfolio_target_fraction(self, symbol: str) -> float | None:
        if not self.signal_expectations:
            return None
        symbols = list(self.signal_expectations)
        covariance = self._estimate_signal_covariance(symbols)
        weights = self.portfolio_allocator.allocate(
            self.signal_expectations,
            covariance,
            sector_map=self._sector_map_for_symbols(symbols),
        )
        return abs(float(weights.get(symbol, 0.0)))

    def _estimate_signal_covariance(self, symbols: list[str]) -> pd.DataFrame:
        aligned_returns: dict[str, pd.Series[float]] = {}
        for symbol in symbols:
            history = list(self.return_history.get(symbol, ()))
            if not history:
                continue
            tail = history[-self.config.transition.covariance_history :]
            aligned_returns[symbol] = pd.Series(tail, index=range(-len(tail), 0), dtype=float)

        if len(aligned_returns) >= 2:
            covariance = pd.DataFrame(aligned_returns).cov(min_periods=2)
        elif len(aligned_returns) == 1:
            only_symbol = next(iter(aligned_returns))
            variance = (
                float(aligned_returns[only_symbol].var(ddof=1)) if len(aligned_returns[only_symbol]) >= 2 else 0.0
            )
            covariance = pd.DataFrame([[variance]], index=[only_symbol], columns=[only_symbol])
        else:
            covariance = pd.DataFrame(dtype=float)

        covariance = covariance.reindex(index=symbols, columns=symbols, fill_value=0.0).astype(float)
        for current_symbol in symbols:
            fallback_variance = self._fallback_variance(current_symbol)
            current_variance = (
                float(covariance.at[current_symbol, current_symbol]) if current_symbol in covariance.index else 0.0
            )
            covariance.at[current_symbol, current_symbol] = max(current_variance, fallback_variance)
        return covariance

    def _fallback_variance(self, symbol: str) -> float:
        realized_volatility = max(
            float(self.realized_volatility_by_symbol.get(symbol, self.config.feature.minimum_sigma)),
            self.config.feature.minimum_sigma,
        )
        return float(realized_volatility**2)

    def _gross_exposure_fraction(self, state: ObservedState) -> float:
        equity = max(self.risk_engine.equity, 1e-6)
        total_notional = 0.0
        for position in self.open_positions.values():
            total_notional += abs(position.quantity * self._mark_price(position.symbol, state.book.midpoint))
        return total_notional / equity

    def _net_exposure_fraction(self, state: ObservedState) -> float:
        equity = max(self.risk_engine.equity, 1e-6)
        total_signed_notional = 0.0
        for position in self.open_positions.values():
            direction = 1.0 if position.side == TradeAction.BUY else -1.0
            total_signed_notional += (
                direction * position.quantity * self._mark_price(position.symbol, state.book.midpoint)
            )
        return total_signed_notional / equity

    def _symbol_exposure_fraction(self, symbol: str, fallback_midpoint: float) -> float:
        position = self.open_positions.get(symbol)
        if position is None:
            return 0.0
        equity = max(self.risk_engine.equity, 1e-6)
        direction = 1.0 if position.side == TradeAction.BUY else -1.0
        return direction * position.quantity * self._mark_price(symbol, fallback_midpoint) / equity

    def _mark_price(self, symbol: str, fallback_midpoint: float) -> float:
        return max(float(self.last_midpoints.get(symbol, fallback_midpoint)), self.config.feature.minimum_sigma)

    def _sector_map_for_symbols(self, symbols: list[str]) -> dict[str, str]:
        raw_sector_map = self.runtime_artifacts.metadata.get("sector_map", {})
        if not isinstance(raw_sector_map, dict):
            return {}
        return {
            symbol: str(raw_sector_map[symbol])
            for symbol in symbols
            if symbol in raw_sector_map and raw_sector_map[symbol] is not None
        }

    def _beta_exposure_fraction(self, state: ObservedState) -> float:
        equity = max(self.risk_engine.equity, 1e-6)
        total_beta_notional = 0.0
        for symbol, position in self.open_positions.items():
            direction = 1.0 if position.side == TradeAction.BUY else -1.0
            price = self._mark_price(symbol, state.book.midpoint)
            total_beta_notional += direction * position.quantity * price * self._estimate_symbol_beta(symbol)
        return total_beta_notional / equity

    def _symbol_beta_exposure_fraction(self, symbol: str, fallback_midpoint: float) -> float:
        position = self.open_positions.get(symbol)
        if position is None:
            return 0.0
        equity = max(self.risk_engine.equity, 1e-6)
        direction = 1.0 if position.side == TradeAction.BUY else -1.0
        return (
            direction
            * position.quantity
            * self._mark_price(symbol, fallback_midpoint)
            * self._estimate_symbol_beta(symbol)
            / equity
        )

    def _estimate_symbol_beta(self, symbol: str) -> float:
        raw_beta_map = self.runtime_artifacts.metadata.get("symbol_betas", {})
        if isinstance(raw_beta_map, dict) and symbol in raw_beta_map:
            return float(raw_beta_map[symbol])

        aligned_returns: dict[str, pd.Series[float]] = {}
        for current_symbol, history in self.return_history.items():
            if not history:
                continue
            aligned_returns[current_symbol] = pd.Series(list(history), index=range(-len(history), 0), dtype=float)
        if symbol not in aligned_returns:
            return 1.0

        aligned_frame = pd.DataFrame(aligned_returns).dropna(how="any")
        if aligned_frame.empty:
            aligned_frame = pd.DataFrame({symbol: aligned_returns[symbol]}).dropna(how="any")
        market_proxy = aligned_frame.mean(axis=1)
        market_variance = float(market_proxy.var(ddof=1)) if len(market_proxy) >= 2 else 0.0
        if market_variance <= 0.0:
            return 1.0
        beta = float(aligned_frame[symbol].cov(market_proxy) / market_variance)
        return float(np.clip(beta, -3.0, 3.0))

    @staticmethod
    def _signal_strength(intent: TradeIntent) -> float:
        edge_excess = max(abs(intent.posterior.mean_bps) - intent.posterior.threshold_bps, 0.0)
        signal = max(edge_excess, 1e-6) * max(
            intent.posterior.probability_up,
            intent.posterior.probability_down,
            0.5,
        )
        return signal if intent.action == TradeAction.BUY else -signal

    def _record_symbol_return(self, state: ObservedState) -> None:
        midpoint = max(state.book.midpoint, self.config.feature.minimum_sigma)
        previous_midpoint = self.last_midpoints.get(state.symbol)
        self.last_midpoints[state.symbol] = midpoint
        self.realized_volatility_by_symbol[state.symbol] = float(
            max(state.realized_volatility, self.config.feature.minimum_sigma)
        )
        if previous_midpoint is None or previous_midpoint <= 0:
            return

        history = self.return_history.setdefault(
            state.symbol,
            deque(maxlen=self.config.transition.covariance_history),
        )
        history.append(float(np.log(midpoint / previous_midpoint)))

    def _resolve_pending_outcomes(self, state: ObservedState) -> list[tuple[EdgeKey, float]]:
        resolved: list[tuple[EdgeKey, float]] = []
        while self.pending_outcomes and self.pending_outcomes[0].resolve_timestamp_ns <= state.timestamp_ns:
            pending = self.pending_outcomes.popleft()
            if pending.reference_price <= 0:
                continue
            drift_bps = ((state.book.microprice - pending.reference_price) / pending.reference_price) * 10_000.0
            self.transition_kernel.attach_drift(pending.edge, drift_bps)
            resolved.append((pending.edge, float(drift_bps)))
        return resolved

    def _process_pending_orders(self, state: ObservedState) -> list[ExecutionReport]:
        reports: list[ExecutionReport] = []
        remaining: Deque[ExecutionRequest] = deque()
        while self.pending_orders:
            request = self.pending_orders.popleft()
            if request.symbol != state.symbol or request.executable_timestamp_ns > state.timestamp_ns:
                remaining.append(request)
                continue
            report = self.execution_simulator.execute(request, state)
            reports.append(report)
            self.ingest_execution_report(report)
        self.pending_orders = remaining
        return reports

    def _manage_open_positions(self, state: ObservedState, regime: RegimePosterior) -> list[ExecutionReport]:
        request = self._exit_request(state, regime)
        if request is None:
            return []
        report = self.execution_simulator.execute(request, state)
        self.ingest_execution_report(report)
        return [report]

    def _manage_open_position_requests(self, state: ObservedState, regime: RegimePosterior) -> list[ExecutionRequest]:
        request = self._exit_request(state, regime)
        return [request] if request is not None else []

    def _exit_request(self, state: ObservedState, regime: RegimePosterior) -> ExecutionRequest | None:
        position = self.open_positions.get(state.symbol)
        if position is None:
            return None

        hazard = self.decision_engine.exit_hazard_diagnostics(position.side, state, regime)
        if hazard.total_hazard < self.config.decision.exit_hazard_threshold:
            return None

        action = TradeAction.SELL if position.side == TradeAction.BUY else TradeAction.BUY
        exit_intent = TradeIntent(
            action=action,
            edge=EdgeKey(state.label, state.label, regime.dominant_regime),
            posterior=self.decision_engine.estimate_posterior([], 0.0),
            expected_holding_time_ns=0,
            reason=hazard.reason,
        )
        request = self.execution_simulator.build_request(exit_intent, state, position.quantity)
        request = ExecutionRequest(
            symbol=request.symbol,
            action=request.action,
            quantity=request.quantity,
            decision_timestamp_ns=request.decision_timestamp_ns,
            executable_timestamp_ns=state.timestamp_ns,
            expected_state=request.expected_state,
            intent=request.intent,
            client_order_id=request.client_order_id,
        )
        return request

    def _update_position_from_fill(self, report: ExecutionReport) -> None:
        existing = self.open_positions.get(report.symbol)
        if existing is None:
            self.open_positions[report.symbol] = OpenPosition(
                symbol=report.symbol,
                side=report.action,
                quantity=report.quantity,
                entry_price=float(report.fill_price),
                entry_timestamp_ns=report.timestamp_ns,
            )
            return

        if existing.side == report.action:
            total_quantity = existing.quantity + report.quantity
            weighted_entry = (
                existing.entry_price * existing.quantity + float(report.fill_price) * report.quantity
            ) / max(total_quantity, 1)
            self.open_positions[report.symbol] = OpenPosition(
                symbol=existing.symbol,
                side=existing.side,
                quantity=total_quantity,
                entry_price=weighted_entry,
                entry_timestamp_ns=existing.entry_timestamp_ns,
            )
            return

        closing_quantity = min(existing.quantity, report.quantity)
        direction = 1.0 if existing.side == TradeAction.BUY else -1.0
        pnl = direction * (float(report.fill_price) - existing.entry_price) * closing_quantity
        self.risk_engine.register_realized_pnl(pnl)

        remaining = existing.quantity - closing_quantity
        if remaining > 0:
            self.open_positions[report.symbol] = OpenPosition(
                symbol=existing.symbol,
                side=existing.side,
                quantity=remaining,
                entry_price=existing.entry_price,
                entry_timestamp_ns=existing.entry_timestamp_ns,
            )
            return

        residual = report.quantity - closing_quantity
        if residual > 0:
            self.open_positions[report.symbol] = OpenPosition(
                symbol=report.symbol,
                side=report.action,
                quantity=residual,
                entry_price=float(report.fill_price),
                entry_timestamp_ns=report.timestamp_ns,
            )
        else:
            self.open_positions.pop(report.symbol, None)
            self.signal_expectations.pop(report.symbol, None)
