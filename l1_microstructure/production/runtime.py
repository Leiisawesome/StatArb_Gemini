"""Supervised multi-symbol production runtime."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, time, timedelta, timezone
from threading import RLock
from time import sleep
from typing import Any
from zoneinfo import ZoneInfo

from l1_microstructure.artifacts import ArtifactBundleSelector, LocalArtifactStore, RunQualityGate
from l1_microstructure.config import FrameworkConfig
from l1_microstructure.decision import TradeAction, TradeIntent
from l1_microstructure.events import MarketEvent
from l1_microstructure.execution import ExecutionReport, ExecutionRequest
from l1_microstructure.ingest.interfaces import LiveSubscriptionRequest, MarketDataSource
from l1_microstructure.live.execution_session import RoutedExecutionService
from l1_microstructure.live.interfaces import ProductionOrderRouter, RouteAcknowledgement
from l1_microstructure.pipeline import L1MicrostructureStateMachine
from l1_microstructure.risk import OpenPosition
from l1_microstructure.transitions import EdgeKey

from .config import OperatingMode, ProductionConfig
from .alerts import LocalAlertSink
from .ledger import OperationalLedger
from .lifecycle import LifecycleState, RuntimeLifecycle


class ProductionRuntime:
    """Owns live engines and keeps broker-facing operation fail closed."""

    def __init__(
        self,
        config: ProductionConfig,
        *,
        source: MarketDataSource,
        router: ProductionOrderRouter,
        framework_config: FrameworkConfig | None = None,
        ledger: OperationalLedger | None = None,
        alert_sink: LocalAlertSink | None = None,
    ):
        self.config = config
        self.source = source
        self._validate_router_capabilities(router)
        self.router = router
        self.execution_service = RoutedExecutionService(router)
        self.framework_config = framework_config or FrameworkConfig()
        self.ledger = ledger or OperationalLedger(config.database_path)
        self.alert_sink = alert_sink or LocalAlertSink()
        persisted_state = self.ledger.get_state("lifecycle_state", LifecycleState.STOPPED.value)
        initial = LifecycleState.HALTED if persisted_state == LifecycleState.HALTED.value else LifecycleState.STOPPED
        self.lifecycle = RuntimeLifecycle(initial)
        persisted_models = self.ledger.get_state("promoted_models", {})
        self.promoted_run_ids = {
            symbol: str(persisted_models.get(symbol, config.promoted_run_ids[symbol])) for symbol in config.symbols
        }
        self.machines: dict[str, L1MicrostructureStateMachine] = {}
        self.last_event_timestamp_ns: dict[str, int] = {}
        self.first_event_timestamp_ns: dict[str, int] = {}
        self._lock = RLock()
        self._running = False
        self._shutdown = False
        self._flatten_started_at_ns: int | None = None
        self._flatten_submitted_symbols: set[str] = set()

    def start(self) -> None:
        with self._lock:
            if self.lifecycle.state is LifecycleState.HALTED:
                self._transition(LifecycleState.RECONCILING, "operator requested reconciliation")
            else:
                self._transition(LifecycleState.STARTING, "runtime startup")
                self._transition(LifecycleState.WARMING, "loading promoted artifacts")
                self._load_machines()
                self._transition(LifecycleState.RECONCILING, "reconciling broker and ledger")
            failure, snapshot = self._reconciliation_failure()
            if failure is not None:
                self._halt(failure)
                return
            if not self.machines:
                self._load_machines()
            self._rehydrate_positions(snapshot)
            if self.config.warmup_seconds > 0:
                self._transition(LifecycleState.WARMING, "reconciliation passed; rebuilding market context")
            else:
                self._transition(LifecycleState.READY, "reconciliation passed")
                self._transition(LifecycleState.RUNNING, "runtime enabled")
            self._running = True

    def run(self) -> None:
        self._shutdown = False
        request = LiveSubscriptionRequest(symbols=self.config.symbols)
        while not self._shutdown:
            if self.lifecycle.state in {LifecycleState.STOPPED, LifecycleState.HALTED, LifecycleState.ERROR}:
                if self.ledger.get_state("kill_switch", False):
                    sleep(self.config.reconnect_backoff_seconds)
                    continue
                if not self._wall_clock_start_allowed():
                    sleep(self.config.reconnect_backoff_seconds)
                    continue
                try:
                    self.start()
                except BaseException as exc:
                    self._halt(f"runtime startup failed: {exc}")
            if self.lifecycle.state not in {LifecycleState.WARMING, LifecycleState.RUNNING, LifecycleState.FLATTENING}:
                sleep(self.config.reconnect_backoff_seconds)
                continue
            try:
                for event in self.source.subscribe_live(request):
                    if self._shutdown or not self._running:
                        break
                    self.process_event(event)
            except BaseException as exc:
                self._halt(f"market-data loop failed: {exc}")
            finally:
                self._poll_reports()
            if not self._shutdown:
                sleep(self.config.reconnect_backoff_seconds)

    def process_event(self, event: MarketEvent) -> None:
        if event.symbol not in self.machines:
            return
        if self._event_is_stale(event):
            self._halt(f"stale market data for {event.symbol}")
            return
        if self.lifecycle.state is LifecycleState.FLATTENING:
            machine = self.machines[event.symbol]
            if event.symbol in machine.open_positions and event.symbol not in self._flatten_submitted_symbols:
                machine.on_event(event)
                self._route_flatten_symbol(event.symbol, machine)
            self._poll_reports()
            if not any(machine.open_positions for machine in self.machines.values()) and not self.ledger.open_orders():
                self._transition(LifecycleState.STOPPED, "flatten complete")
                self._running = False
            elif self._flatten_timed_out(event.timestamp_ns):
                self._halt("flatten timed out with unresolved positions or orders")
            return
        session_phase = self._session_phase(event.timestamp_ns)
        self.last_event_timestamp_ns[event.symbol] = event.timestamp_ns
        self.first_event_timestamp_ns.setdefault(event.symbol, event.timestamp_ns)
        self._poll_reports()
        daily_loss_reason = self._daily_loss_breach()
        if daily_loss_reason is not None:
            self._halt(daily_loss_reason)
            return
        update = self.machines[event.symbol].on_event(event)
        self._complete_warmup_if_ready()
        if session_phase == "flatten" and self.lifecycle.state in {
            LifecycleState.WARMING,
            LifecycleState.RUNNING,
            LifecycleState.PAUSED,
        }:
            self.flatten()
            return
        if session_phase == "closed" and any(machine.open_positions for machine in self.machines.values()):
            self._halt("market closed with unresolved strategy positions")
            return
        if update is None:
            return
        self.ledger.append_event(
            "market",
            "framework_update",
            {
                "symbol": event.symbol,
                "timestamp_ns": event.timestamp_ns,
                "state": update.state.label,
                "regime": update.regime.dominant_regime.value,
                "intent": update.intent.action.value if update.intent is not None else None,
            },
        )
        for request in update.submitted_requests:
            if self._may_route(request):
                self._route(request)

    def pause(self, reason: str = "operator pause") -> None:
        self._transition(LifecycleState.PAUSED, reason)

    def resume(self) -> None:
        failure, _ = self._reconciliation_failure()
        if failure is not None:
            raise ValueError("cannot resume before reconciliation passes")
        self._transition(LifecycleState.RUNNING, "operator resume")

    def halt(self, reason: str = "operator kill switch") -> None:
        self.ledger.set_state("kill_switch", True)
        self._halt(reason)

    def clear_kill_switch(self) -> None:
        if self.lifecycle.state is not LifecycleState.HALTED:
            raise ValueError("kill switch can only be cleared while halted")
        self.ledger.set_state("kill_switch", False)
        self.ledger.append_event("operator", "kill_switch_cleared", {})

    def promote_model(self, symbol: str, run_id: str) -> None:
        symbol = symbol.upper()
        if self.lifecycle.state not in {LifecycleState.STOPPED, LifecycleState.HALTED}:
            raise ValueError("models can only be promoted while stopped or halted")
        if symbol not in self.config.symbols:
            raise ValueError(f"symbol is not in the configured universe: {symbol}")
        selector = ArtifactBundleSelector(LocalArtifactStore(self.config.artifact_root))
        selector.resolve_passing_by_run_id(
            symbol=symbol,
            run_id=run_id,
            quality_gate=self._model_quality_gate(),
        )
        self.promoted_run_ids[symbol] = run_id
        self.ledger.set_state("promoted_models", self.promoted_run_ids)
        self.ledger.append_event("model", "promoted", {"symbol": symbol, "run_id": run_id})
        self.machines = {}

    def flatten(self) -> None:
        if self.lifecycle.state not in {LifecycleState.WARMING, LifecycleState.RUNNING, LifecycleState.PAUSED}:
            raise ValueError("flatten requires a warming, running, or paused runtime")
        self._transition(LifecycleState.FLATTENING, "flatten requested")
        self._flatten_started_at_ns = int(datetime.now(timezone.utc).timestamp() * 1_000_000_000)
        self._flatten_submitted_symbols = set()
        for order_id in self._router_open_order_ids():
            self.execution_service.cancel(order_id)
        for symbol, machine in self.machines.items():
            self._route_flatten_symbol(symbol, machine)
        self._poll_reports()
        if any(machine.open_positions for machine in self.machines.values()):
            self.ledger.append_event("lifecycle", "flatten_pending", {})
        else:
            self._transition(LifecycleState.STOPPED, "flatten complete")
            self._running = False

    def _route_flatten_symbol(self, symbol: str, machine: L1MicrostructureStateMachine) -> None:
        position = machine.open_positions.get(symbol)
        state = machine.previous_state
        if position is None or state is None or symbol in self._flatten_submitted_symbols:
            return
        action = TradeAction.SELL if position.side is TradeAction.BUY else TradeAction.BUY
        intent = TradeIntent(
            action=action,
            edge=EdgeKey(state.label, state.label, machine.regime_inferencer.update(state).dominant_regime),
            posterior=machine.decision_engine.estimate_posterior([], 0.0),
            expected_holding_time_ns=0,
            reason="production flatten",
        )
        request = machine.execution_simulator.build_request(intent, state, position.quantity)
        self._route(request)
        self._flatten_submitted_symbols.add(symbol)

    def stop(self) -> None:
        self._shutdown = True
        self._running = False
        if self.lifecycle.state is LifecycleState.RUNNING:
            self.pause("runtime stopping")
        self.execution_service.stop()
        if self.lifecycle.state in {
            LifecycleState.STARTING,
            LifecycleState.WARMING,
            LifecycleState.RECONCILING,
            LifecycleState.READY,
            LifecycleState.PAUSED,
            LifecycleState.FLATTENING,
            LifecycleState.HALTED,
            LifecycleState.ERROR,
        }:
            self._transition(LifecycleState.STOPPED, "runtime stopped")

    def status(self) -> dict[str, Any]:
        return {
            "lifecycle": self.lifecycle.state.value,
            "mode": self.config.mode.value,
            "symbols": list(self.config.symbols),
            "promoted_run_ids": dict(self.promoted_run_ids),
            "last_event_timestamp_ns": dict(self.last_event_timestamp_ns),
            "kill_switch": bool(self.ledger.get_state("kill_switch", False)),
            "open_orders": self.ledger.open_orders(),
            "positions": {
                symbol: asdict(machine.open_positions[symbol])
                for symbol, machine in self.machines.items()
                if symbol in machine.open_positions
            },
            "broker": self._router_health(),
        }

    def _load_machines(self) -> None:
        selector = ArtifactBundleSelector(LocalArtifactStore(self.config.artifact_root))
        self.machines = {
            symbol: L1MicrostructureStateMachine(
                self.framework_config,
                runtime_artifacts=selector.resolve_passing_by_run_id(
                    symbol=symbol,
                    run_id=self.promoted_run_ids[symbol],
                    quality_gate=self._model_quality_gate(),
                ),
                route_orders_externally=True,
            )
            for symbol in self.config.symbols
        }

    def _reconciliation_failure(self) -> tuple[str | None, dict[str, Any]]:
        if self.ledger.get_state("kill_switch", False):
            return "persistent kill switch is active", {}
        health = self._reconciliation_snapshot()
        if not health.get("connected"):
            return f"broker is not connected: {health.get('error') or health.get('status')}", health
        ledger_external_ids = {
            str(order["external_order_id"]) for order in self.ledger.open_orders() if order.get("external_order_id")
        }
        router_ids = set(self._router_open_order_ids())
        snapshot_ids = {str(value) for value in health.get("open_order_ids", router_ids)}
        if snapshot_ids != router_ids:
            return (
                f"router reconciliation mismatch snapshot={sorted(snapshot_ids)} tracked={sorted(router_ids)}",
                health,
            )
        if ledger_external_ids != router_ids:
            return (
                f"open-order reconciliation mismatch ledger={sorted(ledger_external_ids)} broker={sorted(router_ids)}",
                health,
            )
        expected_positions = self.ledger.get_state("strategy_positions", {})
        broker_positions = health.get("positions", {})
        for symbol in self.config.symbols:
            expected_quantity = float(expected_positions.get(symbol, 0.0))
            broker_quantity = float(dict(broker_positions.get(symbol, {})).get("quantity", 0.0))
            if expected_quantity != broker_quantity:
                return (
                    f"position reconciliation mismatch for {symbol}: ledger={expected_quantity} broker={broker_quantity}",
                    health,
                )
        if self.config.mode is OperatingMode.LIVE and health.get("net_liquidation") is None:
            return "live reconciliation requires broker net liquidation value", health
        if health.get("net_liquidation") is not None and self.ledger.get_state("session_start_net_liquidation") is None:
            self.ledger.set_state("session_start_net_liquidation", float(health["net_liquidation"]))
        return None, health

    def _rehydrate_positions(self, snapshot: dict[str, Any]) -> None:
        timestamp_ns = int(datetime.now(timezone.utc).timestamp() * 1_000_000_000)
        for symbol, payload in dict(snapshot.get("positions", {})).items():
            if symbol not in self.machines:
                continue
            quantity = float(dict(payload).get("quantity", 0.0))
            if quantity == 0.0:
                continue
            self.machines[symbol].open_positions[symbol] = OpenPosition(
                symbol=symbol,
                side=TradeAction.BUY if quantity > 0 else TradeAction.SELL,
                quantity=int(abs(quantity)),
                entry_price=float(dict(payload).get("average_cost", 0.0)),
                entry_timestamp_ns=timestamp_ns,
            )

    def _complete_warmup_if_ready(self) -> None:
        if self.lifecycle.state is not LifecycleState.WARMING:
            return
        required_ns = int(self.config.warmup_seconds * 1_000_000_000)
        if any(symbol not in self.first_event_timestamp_ns for symbol in self.config.symbols):
            return
        if any(
            self.last_event_timestamp_ns[symbol] - self.first_event_timestamp_ns[symbol] < required_ns
            for symbol in self.config.symbols
        ):
            return
        self._transition(LifecycleState.READY, "market context warmup complete")
        self._transition(LifecycleState.RUNNING, "runtime enabled")

    def _reconciliation_snapshot(self) -> dict[str, Any]:
        snapshot = self.execution_service.reconciliation_snapshot()
        return snapshot or {"connected": False, "status": "invalid reconciliation snapshot"}

    def _may_route(self, request: ExecutionRequest) -> bool:
        machine = self.machines[request.symbol]
        position = machine.open_positions.get(request.symbol)
        is_exit = position is not None and position.side is not request.action
        if not is_exit and not self.lifecycle.permits_entries:
            return False
        session_phase = self._session_phase(request.decision_timestamp_ns)
        if not is_exit and session_phase != "entries":
            self.ledger.append_event("risk", "order_blocked", {"reason": session_phase, "symbol": request.symbol})
            return False
        if not is_exit and self._would_breach_exposure(request):
            self.ledger.append_event(
                "risk", "order_blocked", {"reason": "production exposure limit", "symbol": request.symbol}
            )
            return False
        if not is_exit and request.action is TradeAction.SELL and not self.config.risk.allow_shorting:
            self.ledger.append_event("risk", "order_blocked", {"reason": "shorting disabled", "symbol": request.symbol})
            return False
        return True

    def _route(self, request: ExecutionRequest) -> None:
        payload = {
            "symbol": request.symbol,
            "action": request.action.value,
            "quantity": request.quantity,
            "decision_timestamp_ns": request.decision_timestamp_ns,
        }

        def record_intent(current: ExecutionRequest) -> None:
            self.ledger.record_order_intent(payload, current.client_order_id)

        def record_acknowledgement(current: ExecutionRequest, acknowledgement: RouteAcknowledgement) -> None:
            self.ledger.update_order(
                current.client_order_id,
                acknowledgement.status,
                external_order_id=acknowledgement.external_order_id,
                payload={**payload, "reason": acknowledgement.reason},
            )
            self.ledger.append_event("order", "route_acknowledgement", {**payload, **asdict(acknowledgement)})
            if acknowledgement.status != "accepted":
                self._halt(f"broker rejected order for {current.symbol}: {acknowledgement.reason}")

        self.execution_service.submit(
            request,
            before_submit=record_intent,
            after_submit=record_acknowledgement,
        )

    def _poll_reports(self) -> None:
        self.execution_service.poll(
            self.config.symbols,
            consumer_for_symbol=self.machines.get,
            after_report=self._record_execution_report,
        )
        self._persist_positions()

    def _record_execution_report(self, report: ExecutionReport) -> None:
        if report.client_order_id:
            ledger_status = "partial_filled" if report.reason == "broker reported partial fill" else report.status
            self.ledger.update_order(
                report.client_order_id,
                ledger_status,
                external_order_id=report.external_order_id,
                payload=asdict(report),
            )
        self.ledger.append_event("order", "execution_report", asdict(report))

    def _persist_positions(self) -> None:
        positions: dict[str, float] = {}
        for symbol, machine in self.machines.items():
            position = machine.open_positions.get(symbol)
            if position is None:
                continue
            direction = 1.0 if position.side is TradeAction.BUY else -1.0
            positions[symbol] = direction * float(position.quantity)
        self.ledger.set_state("strategy_positions", positions)

    def _daily_loss_breach(self) -> str | None:
        health = self._router_health()
        current = health.get("net_liquidation")
        starting = self.ledger.get_state("session_start_net_liquidation")
        if current is None or starting is None or float(starting) <= 0:
            return None
        loss_fraction = (float(starting) - float(current)) / float(starting)
        if loss_fraction >= self.config.risk.daily_loss_fraction:
            return f"daily loss limit breached: {loss_fraction:.4%}"
        return None

    def _would_breach_exposure(self, request: ExecutionRequest) -> bool:
        health = self._router_health()
        net_liquidation = float(health.get("net_liquidation") or self.framework_config.risk.starting_equity)
        proposed_notional = request.quantity * request.expected_state.book.midpoint
        symbol_notional = proposed_notional
        gross_notional = proposed_notional
        for symbol, machine in self.machines.items():
            position = machine.open_positions.get(symbol)
            if position is None:
                continue
            state = machine.previous_state
            mark = state.book.midpoint if state is not None else position.entry_price
            notional = position.quantity * mark
            gross_notional += notional
            if symbol == request.symbol:
                symbol_notional += notional
        return (
            gross_notional / max(net_liquidation, 1.0) > self.config.risk.max_gross_exposure
            or symbol_notional / max(net_liquidation, 1.0) > self.config.risk.max_symbol_exposure
        )

    def _session_phase(self, timestamp_ns: int) -> str:
        local = datetime.fromtimestamp(timestamp_ns / 1_000_000_000, tz=timezone.utc).astimezone(
            ZoneInfo(self.config.session.timezone)
        )
        current = local.time().replace(tzinfo=None)
        market_open = time.fromisoformat(self.config.session.market_open)
        stop_entries = time.fromisoformat(self.config.session.stop_entries)
        flatten_at = time.fromisoformat(self.config.session.flatten_at)
        market_close = time.fromisoformat(self.config.session.market_close)
        if local.weekday() >= 5 or current < market_open or current >= market_close:
            return "closed"
        if current >= flatten_at:
            return "flatten"
        if current >= stop_entries:
            return "exits_only"
        return "entries"

    def _flatten_timed_out(self, event_timestamp_ns: int) -> bool:
        if self._flatten_started_at_ns is None:
            return False
        elapsed_ns = (
            max(
                event_timestamp_ns,
                int(datetime.now(timezone.utc).timestamp() * 1_000_000_000),
            )
            - self._flatten_started_at_ns
        )
        return elapsed_ns >= int(self.config.flatten_timeout_seconds * 1_000_000_000)

    def _event_is_stale(self, event: MarketEvent) -> bool:
        now_ns = int(datetime.now(timezone.utc).timestamp() * 1_000_000_000)
        lag_seconds = (now_ns - event.timestamp_ns) / 1_000_000_000
        return lag_seconds > self.config.event_stale_after_seconds

    def _wall_clock_start_allowed(self) -> bool:
        local = datetime.now(timezone.utc).astimezone(ZoneInfo(self.config.session.timezone))
        if local.weekday() >= 5:
            return False
        market_open = datetime.combine(local.date(), time.fromisoformat(self.config.session.market_open), local.tzinfo)
        warmup_start = market_open - timedelta(seconds=self.config.warmup_seconds)
        stop_entries = datetime.combine(
            local.date(), time.fromisoformat(self.config.session.stop_entries), local.tzinfo
        )
        return warmup_start <= local < stop_entries

    def _router_health(self) -> dict[str, Any]:
        return self.execution_service.health() or {"connected": False, "status": "invalid health response"}

    def _router_open_order_ids(self) -> list[str]:
        return self.execution_service.open_order_ids()

    def _model_quality_gate(self) -> RunQualityGate:
        policy = self.config.model_quality
        return RunQualityGate(
            minimum_fill_rate=policy.minimum_fill_rate,
            maximum_cancel_rate=policy.maximum_cancel_rate,
            maximum_drift_tracking_error_bps=policy.maximum_drift_tracking_error_bps,
            maximum_unseen_edge_rate=policy.maximum_unseen_edge_rate,
        )

    @staticmethod
    def _validate_router_capabilities(router: ProductionOrderRouter) -> None:
        required = ("submit", "poll", "stop", "cancel", "open_order_ids", "health_check", "reconciliation_snapshot")
        missing = [name for name in required if not callable(getattr(router, name, None))]
        if missing:
            raise TypeError(f"production router is missing required capabilities: {missing}")

    def _halt(self, reason: str) -> None:
        if self.lifecycle.state is not LifecycleState.HALTED:
            self._transition(LifecycleState.HALTED, reason)
        self._running = False
        self.ledger.append_event("incident", "runtime_halted", {"reason": reason})
        self.alert_sink.critical("Trading runtime halted", reason)

    def _transition(self, target: LifecycleState, reason: str) -> None:
        transition = self.lifecycle.transition(target, reason)
        self.ledger.set_state("lifecycle_state", target.value)
        self.ledger.append_event("lifecycle", "transition", asdict(transition))
