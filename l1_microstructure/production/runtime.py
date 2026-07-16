"""Supervised multi-symbol production runtime."""

from __future__ import annotations

from collections import deque
from dataclasses import asdict
from datetime import datetime, time, timedelta, timezone
from hashlib import sha256
import json
from random import random
from threading import RLock
from time import perf_counter_ns, sleep, time_ns
from typing import Any, Callable
from zoneinfo import ZoneInfo

from l1_microstructure.artifacts import ArtifactBundleSelector, LocalArtifactStore, RunQualityGate
from l1_microstructure.config import FrameworkConfig
from l1_microstructure.decision import TradeAction, TradeIntent
from l1_microstructure.events import MarketEvent
from l1_microstructure.execution import ExecutionReport, ExecutionRequest
from l1_microstructure.ingest.interfaces import LiveSubscriptionRequest, MarketDataSource
from l1_microstructure.live.execution_session import RoutedExecutionService
from l1_microstructure.live.interfaces import ProductionOrderRouter, RouteAcknowledgement
from l1_microstructure.live.recovery import (
    BrokerOpenOrderRecovery,
    BrokerRecoveryCodec,
    BrokerRouterRecoveryState,
)
from l1_microstructure.monitoring import AlertCategory, AlertSeverity, OperationalAlertManager
from l1_microstructure.pipeline import L1MicrostructureStateMachine
from l1_microstructure.risk import OpenPosition
from l1_microstructure.retry import RetryExecutor, RetryResult
from l1_microstructure.transitions import EdgeKey
from l1_microstructure.transparent.artifacts import TransparentArtifactSelector
from l1_microstructure.transparent.engine import TransparentStatisticalEngine

from .config import OperatingMode, ProductionConfig
from .alerts import LedgerAlertStore, LocalAlertSink
from .ledger import OperationalLedger
from .lifecycle import LifecycleState, RuntimeLifecycle
from .readiness import OperationalCheck, RuntimeHealthReport, RuntimeReadinessReport


class ProductionRuntime:
    """Owns live engines and keeps broker-facing operation fail closed."""

    BROKER_RECOVERY_STATE_KEY = "broker_router_recovery_state"

    def __init__(
        self,
        config: ProductionConfig,
        *,
        source: MarketDataSource,
        router: ProductionOrderRouter,
        framework_config: FrameworkConfig | None = None,
        ledger: OperationalLedger | None = None,
        alert_sink: LocalAlertSink | None = None,
        wait: Callable[[float], None] = sleep,
        retry_clock: Callable[[], int] = time_ns,
        retry_random_source: Callable[[], float] = random,
    ):
        self.config = config
        self.source = source
        self._validate_router_capabilities(router)
        self.router = router
        self.execution_service = RoutedExecutionService(router)
        self.framework_config = framework_config or FrameworkConfig()
        self.ledger = ledger or OperationalLedger(config.database_path)
        self.alert_sink = alert_sink or LocalAlertSink()
        self.alerts = OperationalAlertManager(self.alert_sink, store=LedgerAlertStore(self.ledger))
        self._wait = wait
        self._retry_clock = retry_clock
        self._retry_random_source = retry_random_source
        persisted_state = self.ledger.get_state("lifecycle_state", LifecycleState.STOPPED.value)
        initial = LifecycleState.HALTED if persisted_state == LifecycleState.HALTED.value else LifecycleState.STOPPED
        self.lifecycle = RuntimeLifecycle(initial)
        persisted_models = self.ledger.get_state("promoted_models", {})
        self.promoted_run_ids = {
            symbol: str(persisted_models.get(symbol, config.promoted_run_ids[symbol])) for symbol in config.symbols
        }
        self.machines: dict[str, L1MicrostructureStateMachine] = {}
        self.transparent_shadow_engines: dict[str, TransparentStatisticalEngine] = {}
        self._shadow_baseline_latencies: deque[int] = deque(maxlen=4096)
        self._shadow_candidate_latencies: deque[int] = deque(maxlen=4096)
        self._shadow_candidate_updates = 0
        self._shadow_resolved_outcomes = 0
        self._shadow_candidate_errors = 0
        self._shadow_action_disagreements = 0
        self._shadow_comparisons = 0
        self._campaign_fingerprint: str | None = None
        self.last_event_timestamp_ns: dict[str, int] = {}
        self.first_event_timestamp_ns: dict[str, int] = {}
        self._lock = RLock()
        self._running = False
        self._shutdown = False
        self._flatten_started_at_ns: int | None = None
        self._flatten_submitted_symbols: set[str] = set()
        self._recorded_retry_outcomes: set[tuple[str, int, int, bool]] = set()

    def start(self) -> None:
        with self._lock:
            if self.lifecycle.state is LifecycleState.HALTED:
                self._transition(LifecycleState.RECONCILING, "operator requested reconciliation")
            else:
                self._transition(LifecycleState.STARTING, "runtime startup")
                self._transition(LifecycleState.WARMING, "loading promoted artifacts")
                self._load_machines()
                self._transition(LifecycleState.RECONCILING, "reconciling broker and ledger")
            if not self.machines:
                self._load_machines()
            self._record_session_start()
            try:
                self._restore_router_recovery_state()
            except Exception as exc:
                self._halt(
                    f"broker recovery failed: {exc}",
                    category=AlertCategory.RECONCILIATION,
                    code="reconciliation_failed",
                )
                return
            failure, snapshot = self._reconciliation_failure()
            if failure is not None:
                broker_disconnected = failure.startswith("broker is not connected")
                retry_exhausted = self._retry_exhausted(snapshot)
                self._halt(
                    failure,
                    category=(
                        AlertCategory.BROKER_CONNECTIVITY if broker_disconnected else AlertCategory.RECONCILIATION
                    ),
                    code=(
                        "broker_retry_exhausted"
                        if retry_exhausted
                        else "broker_disconnected"
                        if broker_disconnected
                        else "reconciliation_failed"
                    ),
                    metadata={"retry": snapshot.get("retry", {})},
                )
                return
            self._rehydrate_positions(snapshot)
            self._persist_positions()
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
                    self._wait(self.config.reconnect_backoff_seconds)
                    continue
                if not self._wall_clock_start_allowed():
                    self._wait(self.config.reconnect_backoff_seconds)
                    continue
                try:
                    self.start()
                except BaseException as exc:
                    self._halt(f"runtime startup failed: {exc}", code="runtime_startup_failed")
            if self.lifecycle.state not in {LifecycleState.WARMING, LifecycleState.RUNNING, LifecycleState.FLATTENING}:
                self._wait(self.config.reconnect_backoff_seconds)
                continue
            self._run_market_data_cycle(request)
            if not self._shutdown:
                self._wait(self.config.reconnect_backoff_seconds)

    def _run_market_data_cycle(self, request: LiveSubscriptionRequest) -> RetryResult[None]:
        result = RetryExecutor(
            self.config.retry.market_data,
            wait=self._wait,
            classifier=self._market_data_retryable,
            clock=self._retry_clock,
            random_source=self._retry_random_source,
        ).execute(lambda: self._consume_market_data(request))
        self.ledger.append_event("retry", "market_data_subscription", result.to_dict())
        if result.failures and result.succeeded and self._running:
            self.alerts.emit(
                AlertSeverity.WARNING,
                AlertCategory.MARKET_DATA,
                "market_data_retry_recovered",
                f"market-data subscription recovered after {result.attempts} attempts",
                metadata=result.to_dict(),
            )
        elif not result.succeeded:
            failure = result.final_failure
            detail = "unknown failure" if failure is None else f"{failure.error_type}: {failure.error}"
            self._halt(
                f"market-data retry exhausted after {result.attempts} attempts: {detail}",
                category=AlertCategory.MARKET_DATA,
                code="market_data_retry_exhausted",
                metadata=result.to_dict(),
            )
        return result

    def _consume_market_data(self, request: LiveSubscriptionRequest) -> None:
        try:
            for event in self.source.subscribe_live(request):
                if self._shutdown or not self._running:
                    return
                self.process_event(event)
        finally:
            self._poll_reports()
        if not self._shutdown and self._running:
            raise ConnectionError("market-data subscription ended unexpectedly")

    @staticmethod
    def _market_data_retryable(error: Exception) -> bool:
        if isinstance(error, PermissionError):
            return False
        return isinstance(error, (TimeoutError, ConnectionError, OSError))

    def process_event(self, event: MarketEvent) -> None:
        if event.symbol not in self.machines:
            return
        if self._event_is_stale(event):
            self._halt(
                f"stale market data for {event.symbol}",
                category=AlertCategory.MARKET_DATA,
                code="stale_market_data",
                symbol=event.symbol,
            )
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
                self._record_session_close(event.timestamp_ns)
            elif self._flatten_timed_out(event.timestamp_ns):
                self._halt("flatten timed out with unresolved positions or orders", code="flatten_timeout")
            return
        session_phase = self._session_phase(event.timestamp_ns)
        self.last_event_timestamp_ns[event.symbol] = event.timestamp_ns
        self.first_event_timestamp_ns.setdefault(event.symbol, event.timestamp_ns)
        self._poll_reports()
        daily_loss_reason = self._daily_loss_breach()
        if daily_loss_reason is not None:
            self._halt(daily_loss_reason, category=AlertCategory.RISK, code="daily_loss_limit_breached")
            return
        if event.symbol in self.transparent_shadow_engines:
            baseline_started = perf_counter_ns()
            update = self.machines[event.symbol].on_event(event)
            self._shadow_baseline_latencies.append(max(perf_counter_ns() - baseline_started, 0))
            self._process_transparent_shadow(event, update)
        else:
            update = self.machines[event.symbol].on_event(event)
        risk_engine = getattr(self.machines[event.symbol], "risk_engine", None)
        if bool(getattr(risk_engine, "halted", False)):
            self._halt(
                f"strategy risk engine halted for {event.symbol}",
                category=AlertCategory.RISK,
                code="strategy_risk_halt",
                symbol=event.symbol,
            )
            return
        self._complete_warmup_if_ready()
        if session_phase == "flatten" and self.lifecycle.state in {
            LifecycleState.WARMING,
            LifecycleState.RUNNING,
            LifecycleState.PAUSED,
        }:
            self.flatten(timestamp_ns=event.timestamp_ns)
            return
        if session_phase == "closed" and any(machine.open_positions for machine in self.machines.values()):
            self._halt(
                "market closed with unresolved strategy positions",
                category=AlertCategory.RISK,
                code="positions_open_after_close",
            )
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
                "submitted_client_order_ids": [request.client_order_id for request in update.submitted_requests],
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
        self._halt(reason, category=AlertCategory.RISK, code="operator_kill_switch")

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

    def flatten(self, *, timestamp_ns: int | None = None) -> None:
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
            self._record_session_close(timestamp_ns)

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
            "alerts": self.recent_alerts(20),
            "alert_delivery": self.alerts.delivery_diagnostics(20),
            "alert_persistence": self.alerts.persistence_diagnostics(20),
        }

    def health_report(self, *, timestamp_ns: int | None = None) -> RuntimeHealthReport:
        observed_at_ns = time_ns() if timestamp_ns is None else int(timestamp_ns)
        try:
            self.ledger.get_state("lifecycle_state")
        except Exception as exc:
            ledger_check = OperationalCheck(
                "ledger.readable",
                False,
                "operational ledger is unavailable",
                details={"error_type": type(exc).__name__},
            )
        else:
            ledger_check = OperationalCheck("ledger.readable", True, "operational ledger is readable")
        persistence = self.alerts.persistence_diagnostics(20)
        delivery = self.alerts.delivery_diagnostics(20)
        checks = (
            OperationalCheck("daemon.responding", True, "daemon control process is responding"),
            ledger_check,
            self._alert_diagnostic_check("alerts.persistence", persistence),
            self._alert_diagnostic_check("alerts.delivery", delivery),
        )
        return RuntimeHealthReport.from_checks(observed_at_ns, checks)

    def readiness_report(self, *, timestamp_ns: int | None = None) -> RuntimeReadinessReport:
        observed_at_ns = time_ns() if timestamp_ns is None else int(timestamp_ns)
        lifecycle = self.lifecycle.state
        checks: list[OperationalCheck] = [
            OperationalCheck(
                "runtime.lifecycle_running",
                lifecycle is LifecycleState.RUNNING,
                "runtime permits new entries"
                if lifecycle is LifecycleState.RUNNING
                else "runtime does not permit new entries",
                details={"lifecycle": lifecycle.value},
            )
        ]
        try:
            kill_switch = bool(self.ledger.get_state("kill_switch", False))
        except Exception as exc:
            checks.append(
                OperationalCheck(
                    "safety.kill_switch_clear",
                    False,
                    "kill-switch state is unavailable",
                    details={"error_type": type(exc).__name__},
                )
            )
        else:
            checks.append(
                OperationalCheck(
                    "safety.kill_switch_clear",
                    not kill_switch,
                    "persistent kill switch is clear" if not kill_switch else "persistent kill switch is active",
                )
            )
        loaded_symbols = sorted(set(self.machines).intersection(self.config.symbols))
        models_loaded = set(loaded_symbols) == set(self.config.symbols)
        checks.append(
            OperationalCheck(
                "models.loaded",
                models_loaded,
                "promoted models are loaded" if models_loaded else "one or more promoted models are not loaded",
                details={"loaded_symbols": loaded_symbols, "required_symbols": list(self.config.symbols)},
            )
        )
        checks.extend(self._market_context_checks(observed_at_ns))
        snapshot = self._reconciliation_snapshot()
        broker_connected = bool(snapshot.get("connected"))
        checks.append(
            OperationalCheck(
                "broker.connected",
                broker_connected,
                "broker is connected" if broker_connected else "broker is not connected",
                details={"status": snapshot.get("status", "unknown")},
            )
        )
        reconciliation_failure = self._readiness_reconciliation_failure(snapshot)
        checks.append(
            OperationalCheck(
                "broker.reconciled",
                reconciliation_failure is None,
                "broker and ledger state reconcile" if reconciliation_failure is None else reconciliation_failure,
            )
        )
        checks.extend(
            (
                self._alert_diagnostic_check(
                    "alerts.persistence", self.alerts.persistence_diagnostics(20), required=False
                ),
                self._alert_diagnostic_check("alerts.delivery", self.alerts.delivery_diagnostics(20), required=False),
            )
        )
        return RuntimeReadinessReport.from_checks(observed_at_ns, lifecycle.value, tuple(checks))

    def recent_alerts(self, limit: int = 100) -> list[dict[str, Any]]:
        return self.alerts.recent_dicts(limit)

    def _market_context_checks(self, observed_at_ns: int) -> tuple[OperationalCheck, OperationalCheck]:
        missing_symbols = [symbol for symbol in self.config.symbols if symbol not in self.last_event_timestamp_ns]
        stale_symbols = [
            symbol
            for symbol in self.config.symbols
            if symbol in self.last_event_timestamp_ns
            and (observed_at_ns - self.last_event_timestamp_ns[symbol]) / 1_000_000_000
            > self.config.event_stale_after_seconds
        ]
        market_data_fresh = not missing_symbols and not stale_symbols
        required_ns = int(self.config.warmup_seconds * 1_000_000_000)
        incomplete_warmup = [
            symbol
            for symbol in self.config.symbols
            if symbol not in self.first_event_timestamp_ns
            or symbol not in self.last_event_timestamp_ns
            or self.last_event_timestamp_ns[symbol] - self.first_event_timestamp_ns[symbol] < required_ns
        ]
        return (
            OperationalCheck(
                "market_data.fresh",
                market_data_fresh,
                "market data is fresh for every symbol" if market_data_fresh else "market data is missing or stale",
                details={"missing_symbols": missing_symbols, "stale_symbols": stale_symbols},
            ),
            OperationalCheck(
                "market_data.warmup_complete",
                not incomplete_warmup,
                "market context warmup is complete" if not incomplete_warmup else "market context warmup is incomplete",
                details={"incomplete_symbols": incomplete_warmup},
            ),
        )

    def _readiness_reconciliation_failure(self, snapshot: dict[str, Any]) -> str | None:
        if not snapshot.get("connected"):
            return "broker state is unavailable for reconciliation"
        try:
            ledger_external_ids = {
                str(order["external_order_id"]) for order in self.ledger.open_orders() if order.get("external_order_id")
            }
            broker_order_ids = {str(value) for value in snapshot.get("open_order_ids", [])}
            if ledger_external_ids != broker_order_ids:
                return "open orders do not reconcile"
            expected_positions = self.ledger.get_state("strategy_positions", {})
            broker_positions = snapshot.get("positions", {})
            for symbol in self.config.symbols:
                expected_quantity = float(expected_positions.get(symbol, 0.0))
                broker_quantity = float(dict(broker_positions.get(symbol, {})).get("quantity", 0.0))
                if expected_quantity != broker_quantity:
                    return f"position does not reconcile for {symbol}"
        except Exception as exc:
            return f"reconciliation state is unavailable ({type(exc).__name__})"
        if self.config.mode is OperatingMode.LIVE and snapshot.get("net_liquidation") is None:
            return "live broker net liquidation is unavailable"
        return None

    @staticmethod
    def _alert_diagnostic_check(
        code: str,
        diagnostics: dict[str, Any],
        *,
        required: bool = True,
    ) -> OperationalCheck:
        failure_count = int(diagnostics.get("failure_count", 0))
        return OperationalCheck(
            code,
            failure_count == 0,
            "no failures recorded" if failure_count == 0 else f"{failure_count} failure(s) recorded",
            required=required,
            details={"failure_count": failure_count},
        )

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
        self.transparent_shadow_engines = {}
        artifact_hashes: dict[str, dict[str, str]] = {}
        store = LocalArtifactStore(self.config.artifact_root)
        baseline_artifact_hashes = {
            symbol: {
                kind: str(store.load_metadata(artifact_id).payload_hash)
                for kind, artifact_id in machine.runtime_artifacts.artifact_ids.items()
            }
            for symbol, machine in self.machines.items()
        }
        if self.config.transparent_shadow_run_ids:
            transparent_selector = TransparentArtifactSelector(store)
            for symbol, run_id in self.config.transparent_shadow_run_ids.items():
                artifacts = transparent_selector.resolve(symbol=symbol, run_id=run_id, passing_only=True)
                self.transparent_shadow_engines[symbol] = TransparentStatisticalEngine(
                    artifacts,
                    self.framework_config,
                )
                artifact_hashes[symbol] = {
                    kind: str(store.load_metadata(artifact_id).payload_hash)
                    for kind, artifact_id in artifacts.artifact_ids.items()
                }
        fingerprint_payload = {
            "engine_version": "v2",
            "routing_engine_version": "v1",
            "transparent_shadow_run_ids": self.config.transparent_shadow_run_ids,
            "artifact_hashes": artifact_hashes,
            "baseline_artifact_hashes": baseline_artifact_hashes,
            "framework_config": asdict(self.framework_config),
            "production_config": self.config.public_dict(),
        }
        self._campaign_fingerprint = (
            sha256(json.dumps(fingerprint_payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            if self.transparent_shadow_engines
            else None
        )

    def _process_transparent_shadow(self, event: MarketEvent, baseline_update) -> None:
        engine = self.transparent_shadow_engines.get(event.symbol)
        if engine is None:
            return
        started = perf_counter_ns()
        try:
            candidate_update = engine.on_event(event)
        except Exception:
            self._shadow_candidate_errors += 1
            candidate_update = None
        self._shadow_candidate_latencies.append(max(perf_counter_ns() - started, 0))
        if candidate_update is not None:
            self._shadow_candidate_updates += 1
            self._shadow_resolved_outcomes += len(getattr(candidate_update, "resolved_outcomes", ()))
        if baseline_update is None and candidate_update is None:
            return
        baseline_action = (
            TradeAction.HOLD
            if baseline_update is None or baseline_update.intent is None
            else baseline_update.intent.action
        )
        candidate_action = TradeAction.HOLD if candidate_update is None else candidate_update.action
        self._shadow_comparisons += 1
        self._shadow_action_disagreements += int(baseline_action is not candidate_action)

    @staticmethod
    def _p95(values: deque[int]) -> float:
        if not values:
            return 0.0
        ordered = sorted(values)
        return float(ordered[min(int(0.95 * (len(ordered) - 1)), len(ordered) - 1)])

    def _record_transparent_shadow_summary(self, *, timestamp) -> None:
        if not self.transparent_shadow_engines:
            return
        self.ledger.append_event(
            "model",
            "transparent_shadow_summary",
            {
                "engine_version": "v2",
                "routing_engine_version": "v1",
                "validation_passed": True,
                "campaign_fingerprint": self._campaign_fingerprint,
                "promoted_run_ids": dict(self.config.transparent_shadow_run_ids),
                "candidate_update_count": self._shadow_candidate_updates,
                "resolved_outcome_count": self._shadow_resolved_outcomes,
                "pending_outcome_count": sum(
                    int(getattr(getattr(engine, "outcomes", None), "pending_count", 0))
                    for engine in self.transparent_shadow_engines.values()
                ),
                "candidate_error_count": self._shadow_candidate_errors,
                "comparison_count": self._shadow_comparisons,
                "action_disagreement_rate": self._shadow_action_disagreements / max(self._shadow_comparisons, 1),
                "baseline_p95_latency_ns": self._p95(self._shadow_baseline_latencies),
                "candidate_p95_latency_ns": self._p95(self._shadow_candidate_latencies),
            },
            timestamp=timestamp,
        )

    def _reconciliation_failure(self) -> tuple[str | None, dict[str, Any]]:
        if self.ledger.get_state("kill_switch", False):
            return "persistent kill switch is active", {}
        health = self._reconciliation_snapshot()
        self._record_router_retry_outcomes(health)
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
        try:
            snapshot = self.execution_service.reconciliation_snapshot()
        except Exception as exc:
            return {
                "connected": False,
                "status": "reconciliation_query_failed",
                "error": str(exc),
                "retry": self._router_retry_diagnostics(),
            }
        return snapshot or {"connected": False, "status": "invalid reconciliation snapshot"}

    def _may_route(self, request: ExecutionRequest) -> bool:
        machine = self.machines[request.symbol]
        position = machine.open_positions.get(request.symbol)
        is_exit = position is not None and position.side is not request.action
        if not is_exit and not self.lifecycle.permits_entries:
            self.ledger.append_event(
                "risk",
                "order_blocked",
                {
                    "reason": f"lifecycle_{self.lifecycle.state.value}",
                    "symbol": request.symbol,
                    "client_order_id": request.client_order_id,
                },
            )
            return False
        session_phase = self._session_phase(request.decision_timestamp_ns)
        if not is_exit and session_phase != "entries":
            self.ledger.append_event(
                "risk",
                "order_blocked",
                {"reason": session_phase, "symbol": request.symbol, "client_order_id": request.client_order_id},
            )
            return False
        if not is_exit and self._would_breach_exposure(request):
            self.ledger.append_event(
                "risk",
                "order_blocked",
                {
                    "reason": "production exposure limit",
                    "symbol": request.symbol,
                    "client_order_id": request.client_order_id,
                },
            )
            return False
        if not is_exit and request.action is TradeAction.SELL and not self.config.risk.allow_shorting:
            self.ledger.append_event(
                "risk",
                "order_blocked",
                {"reason": "shorting disabled", "symbol": request.symbol, "client_order_id": request.client_order_id},
            )
            return False
        return True

    def _route(self, request: ExecutionRequest) -> None:
        recovery_request = BrokerRecoveryCodec.request_to_dict(request)
        payload = {
            "client_order_id": request.client_order_id,
            "symbol": request.symbol,
            "action": request.action.value,
            "quantity": request.quantity,
            "decision_timestamp_ns": request.decision_timestamp_ns,
            "recovery_request": recovery_request,
            "recovered_filled_quantity": 0.0,
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
                self._halt(
                    f"broker rejected order for {current.symbol}: {acknowledgement.reason}",
                    category=AlertCategory.ORDER_ROUTING,
                    code="order_rejected",
                    symbol=current.symbol,
                )

        self.execution_service.submit(
            request,
            before_submit=record_intent,
            after_submit=record_acknowledgement,
        )
        self._persist_router_recovery_state()

    def _poll_reports(self) -> None:
        if self._shutdown or self.lifecycle.state is LifecycleState.STOPPED:
            return
        health = self._router_health()
        self._record_router_retry_outcomes(health)
        if not health.get("connected"):
            retry_exhausted = self._retry_exhausted(health)
            self._halt(
                f"broker disconnected: {health.get('error') or health.get('status')}",
                category=AlertCategory.BROKER_CONNECTIVITY,
                code="broker_retry_exhausted" if retry_exhausted else "broker_disconnected",
                metadata={"retry": health.get("retry", {})},
            )
            return
        self.execution_service.poll(
            self.config.symbols,
            consumer_for_symbol=self.machines.get,
            after_report=self._record_execution_report,
        )
        self._persist_positions()
        self._persist_router_recovery_state()

    def _persist_router_recovery_state(self) -> None:
        state = self.execution_service.snapshot_recovery_state()
        if state is None:
            self.ledger.set_state(self.BROKER_RECOVERY_STATE_KEY, None)
            return
        if not isinstance(state, BrokerRouterRecoveryState):
            raise TypeError("production router returned an unsupported recovery state")
        self.ledger.set_state(self.BROKER_RECOVERY_STATE_KEY, BrokerRecoveryCodec.to_dict(state))

    def _restore_router_recovery_state(self) -> None:
        payload = self.ledger.get_state(self.BROKER_RECOVERY_STATE_KEY)
        ledger_orders = self.ledger.open_orders()
        if any(not order.get("external_order_id") for order in ledger_orders):
            raise RuntimeError("ledger contains an open order without a broker acknowledgement")
        ledger_external_ids = {
            str(order["external_order_id"]) for order in ledger_orders if order.get("external_order_id")
        }
        if payload is None and not ledger_orders:
            return
        state = None if payload is None else BrokerRecoveryCodec.from_dict(payload)
        state_external_ids = set() if state is None else {order.external_order_id for order in state.open_orders}
        if state_external_ids != ledger_external_ids:
            state = self._recovery_state_from_ledger(ledger_orders)
        self.execution_service.validate_recovery_state(state, self.config.symbols)
        restored_position_details = self._restore_position_details_from_ledger()
        self.execution_service.restore_recovery_state(state)
        reports = self.execution_service.poll(
            self.config.symbols,
            consumer_for_symbol=self.machines.get,
            after_report=self._record_execution_report,
        )
        if reports:
            expected_positions = self.ledger.get_state("strategy_positions", {})
            if any(float(quantity) != 0.0 for quantity in expected_positions.values()) and not restored_position_details:
                raise RuntimeError("recovered fills require durable strategy position details")
            self._persist_positions()
        self._persist_router_recovery_state()
        reconciliations = self.execution_service.recovery_reconciliations()
        self.ledger.append_event(
            "reconciliation",
            "broker_recovery_restored",
            {
                "open_order_count": len(self._router_open_order_ids()),
                "recovered_report_count": len(reports),
                "orders": [asdict(item) for item in reconciliations],
            },
        )

    @staticmethod
    def _recovery_state_from_ledger(ledger_orders: list[dict[str, Any]]) -> BrokerRouterRecoveryState:
        recovered_orders = []
        for order in ledger_orders:
            external_order_id = order.get("external_order_id")
            payload = dict(order.get("payload", {}))
            request_payload = payload.get("recovery_request")
            if not external_order_id or not isinstance(request_payload, dict):
                raise RuntimeError("ledger open order is missing durable broker recovery data")
            recovered_orders.append(
                BrokerOpenOrderRecovery(
                    external_order_id=str(external_order_id),
                    request=BrokerRecoveryCodec.request_from_dict(request_payload),
                    filled_quantity=float(payload.get("recovered_filled_quantity", 0.0)),
                )
            )
        state = BrokerRouterRecoveryState(open_orders=recovered_orders)
        BrokerRecoveryCodec.validate(state)
        return state

    def _restore_position_details_from_ledger(self) -> bool:
        details = self.ledger.get_state("strategy_position_details", {})
        if not details:
            return False
        expected_positions = {
            str(symbol): float(quantity)
            for symbol, quantity in dict(self.ledger.get_state("strategy_positions", {})).items()
            if float(quantity) != 0.0
        }
        detailed_positions = {
            str(symbol): (1.0 if TradeAction(str(payload["side"])) is TradeAction.BUY else -1.0)
            * float(payload["quantity"])
            for symbol, payload in dict(details).items()
        }
        if detailed_positions != expected_positions:
            raise RuntimeError("durable strategy position details do not match ledger quantities")
        for symbol, payload in dict(details).items():
            if symbol not in self.machines:
                continue
            current = dict(payload)
            self.machines[symbol].open_positions[symbol] = OpenPosition(
                symbol=symbol,
                side=TradeAction(str(current["side"])),
                quantity=int(current["quantity"]),
                entry_price=float(current["entry_price"]),
                entry_timestamp_ns=int(current["entry_timestamp_ns"]),
            )
        return True

    def _record_execution_report(self, report: ExecutionReport) -> None:
        if report.client_order_id:
            ledger_status = "partial_filled" if report.reason == "broker reported partial fill" else report.status
            current_order = next(
                (
                    order
                    for order in self.ledger.open_orders()
                    if order["client_order_id"] == report.client_order_id
                ),
                None,
            )
            payload = dict((current_order or {}).get("payload", {}))
            recovered_filled_quantity = float(payload.get("recovered_filled_quantity", 0.0))
            if report.status == "filled":
                recovered_filled_quantity += float(report.quantity)
            payload.update(
                {
                    "latest_report": asdict(report),
                    "recovered_filled_quantity": recovered_filled_quantity,
                }
            )
            self.ledger.update_order(
                report.client_order_id,
                ledger_status,
                external_order_id=report.external_order_id,
                payload=payload,
            )
        self.ledger.append_event("order", "execution_report", asdict(report))
        if report.status == "rejected":
            self._halt(
                f"broker rejected order for {report.symbol}: {report.reason}",
                category=AlertCategory.ORDER_ROUTING,
                code="order_rejected",
                symbol=report.symbol,
            )

    def _persist_positions(self) -> None:
        positions: dict[str, float] = {}
        details: dict[str, dict[str, Any]] = {}
        for symbol, machine in self.machines.items():
            position = machine.open_positions.get(symbol)
            if position is None:
                continue
            direction = 1.0 if position.side is TradeAction.BUY else -1.0
            positions[symbol] = direction * float(position.quantity)
            details[symbol] = {
                "symbol": position.symbol,
                "side": position.side.value,
                "quantity": position.quantity,
                "entry_price": position.entry_price,
                "entry_timestamp_ns": position.entry_timestamp_ns,
            }
        self.ledger.set_state("strategy_positions", positions)
        self.ledger.set_state("strategy_position_details", details)

    def _record_session_close(self, timestamp_ns: int | None = None) -> None:
        observed_at_ns = (
            int(datetime.now(timezone.utc).timestamp() * 1_000_000_000) if timestamp_ns is None else int(timestamp_ns)
        )
        session_phase = self._session_phase(observed_at_ns)
        if session_phase not in {"flatten", "closed"}:
            return
        local = datetime.fromtimestamp(observed_at_ns / 1_000_000_000, timezone.utc).astimezone(
            ZoneInfo(self.config.session.timezone)
        )
        session_date = local.date().isoformat()
        if self.ledger.get_state("last_closed_session_date") == session_date:
            return
        positions = {
            symbol: (1.0 if position.side is TradeAction.BUY else -1.0) * float(position.quantity)
            for symbol, machine in self.machines.items()
            if (position := machine.open_positions.get(symbol)) is not None
        }
        event_timestamp = local.astimezone(timezone.utc).isoformat()
        self._record_transparent_shadow_summary(timestamp=event_timestamp)
        self.ledger.append_event(
            "session",
            "closed",
            {
                "session_date": session_date,
                "timestamp_ns": observed_at_ns,
                "session_phase": session_phase,
                "mode": self.config.mode.value,
                **self._campaign_session_metadata(),
                "symbols": list(self.config.symbols),
                "positions": positions,
                "open_orders": self.ledger.open_orders(),
            },
            timestamp=event_timestamp,
        )
        self.ledger.set_state("last_closed_session_date", session_date)

    def _record_session_start(self, timestamp_ns: int | None = None) -> None:
        observed_at_ns = (
            int(datetime.now(timezone.utc).timestamp() * 1_000_000_000) if timestamp_ns is None else int(timestamp_ns)
        )
        local = datetime.fromtimestamp(observed_at_ns / 1_000_000_000, timezone.utc).astimezone(
            ZoneInfo(self.config.session.timezone)
        )
        market_open = datetime.combine(local.date(), time.fromisoformat(self.config.session.market_open), local.tzinfo)
        warmup_start = market_open - timedelta(seconds=self.config.warmup_seconds)
        market_close = datetime.combine(
            local.date(), time.fromisoformat(self.config.session.market_close), local.tzinfo
        )
        if local.weekday() >= 5 or not warmup_start <= local < market_close:
            return
        session_date = local.date().isoformat()
        if self.ledger.get_state("last_started_session_date") == session_date:
            if self.transparent_shadow_engines:
                self.ledger.append_event(
                    "model",
                    "transparent_shadow_restart",
                    {
                        "session_date": session_date,
                        "campaign_fingerprint": self._campaign_fingerprint,
                    },
                    timestamp=local.astimezone(timezone.utc).isoformat(),
                )
            return
        self._shadow_baseline_latencies.clear()
        self._shadow_candidate_latencies.clear()
        self._shadow_candidate_updates = 0
        self._shadow_resolved_outcomes = 0
        self._shadow_candidate_errors = 0
        self._shadow_action_disagreements = 0
        self._shadow_comparisons = 0
        self.ledger.append_event(
            "session",
            "started",
            {
                "session_date": session_date,
                "timestamp_ns": observed_at_ns,
                "mode": self.config.mode.value,
                **self._campaign_session_metadata(),
                "symbols": list(self.config.symbols),
            },
            timestamp=local.astimezone(timezone.utc).isoformat(),
        )
        self.ledger.set_state("last_started_session_date", session_date)

    def _campaign_session_metadata(self) -> dict[str, object]:
        if not self.transparent_shadow_engines:
            return {}
        return {
            "engine_version": "v2",
            "routing_engine_version": "v1",
            "campaign_fingerprint": self._campaign_fingerprint,
            "promoted_run_ids": dict(self.config.transparent_shadow_run_ids),
        }

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
        try:
            return self.execution_service.health() or {"connected": False, "status": "invalid health response"}
        except Exception as exc:
            return {
                "connected": False,
                "status": "health_query_failed",
                "error": str(exc),
                "retry": self._router_retry_diagnostics(),
            }

    def _router_retry_diagnostics(self) -> dict[str, Any]:
        diagnostics = getattr(self.router, "retry_diagnostics", None)
        return dict(diagnostics()) if callable(diagnostics) else {}

    def _record_router_retry_outcomes(self, payload: dict[str, Any]) -> None:
        for operation, raw_outcome in dict(payload.get("retry", {})).items():
            outcome = dict(raw_outcome)
            failures = list(outcome.get("failures", []))
            if not failures:
                continue
            final_timestamp_ns = int(dict(failures[-1]).get("timestamp_ns", 0))
            signature = (
                str(operation),
                final_timestamp_ns,
                int(outcome.get("attempts", 0)),
                bool(outcome.get("succeeded", False)),
            )
            if signature in self._recorded_retry_outcomes:
                continue
            self._recorded_retry_outcomes.add(signature)
            self.ledger.append_event("retry", f"broker_{operation}", outcome)
            if outcome.get("succeeded"):
                self.alerts.emit(
                    AlertSeverity.WARNING,
                    AlertCategory.BROKER_CONNECTIVITY,
                    f"broker_{operation}_retry_recovered",
                    f"broker {operation} recovered after {outcome.get('attempts')} attempts",
                    metadata={"operation": operation, **outcome},
                )

    @staticmethod
    def _retry_exhausted(payload: dict[str, Any]) -> bool:
        retry = payload.get("retry", {})
        return any(not bool(result.get("succeeded", False)) for result in dict(retry).values())

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
        required = (
            "submit",
            "poll",
            "stop",
            "cancel",
            "open_order_ids",
            "health_check",
            "reconciliation_snapshot",
            "snapshot_recovery_state",
            "validate_recovery_state",
            "restore_recovery_state",
            "recovery_reconciliations",
        )
        missing = [name for name in required if not callable(getattr(router, name, None))]
        if missing:
            raise TypeError(f"production router is missing required capabilities: {missing}")

    def _halt(
        self,
        reason: str,
        *,
        category: AlertCategory = AlertCategory.RUNTIME,
        code: str = "runtime_halted",
        symbol: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if self.lifecycle.state is not LifecycleState.HALTED:
            self._transition(LifecycleState.HALTED, reason)
        self._running = False
        alert = self.alerts.emit(
            AlertSeverity.CRITICAL,
            category,
            code,
            reason,
            symbol=symbol,
            metadata={"lifecycle": self.lifecycle.state.value, **dict(metadata or {})},
        )
        self.ledger.append_event(
            "incident",
            "runtime_halted",
            {"reason": reason, "alert": alert.to_dict() if alert is not None else None},
        )

    def _transition(self, target: LifecycleState, reason: str) -> None:
        transition = self.lifecycle.transition(target, reason)
        self.ledger.set_state("lifecycle_state", target.value)
        self.ledger.append_event("lifecycle", "transition", asdict(transition))
