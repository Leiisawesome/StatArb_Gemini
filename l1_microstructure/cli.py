"""Command-line entrypoints for successor-package research and replay workflows."""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict
from datetime import date
from typing import Any, Sequence

from l1_microstructure.config import FrameworkConfig
from l1_microstructure.decision import PosteriorEstimate, TradeAction, TradeIntent
from l1_microstructure.events import MarketEvent
from l1_microstructure.execution import ExecutionReport, ExecutionRequest, ExecutionSimulator
from l1_microstructure.features import FeatureEngine, ObservedState
from l1_microstructure.ingest import (
    HistoricalBatchRequest,
    LiveSubscriptionRequest,
    MassivePayloadNormalizer,
    MassiveRESTDataSource,
    MassiveWebSocketConfig,
    MassiveWebSocketDataSource,
)
from l1_microstructure.ingest.massive import _resolve_massive_api_key
from l1_microstructure.live import (
    IBKRBrokerOrderRouter,
    RoutedLiveTradingRunner,
    RunnerConfig,
    SourceBackedPaperRunner,
)
from l1_microstructure.regime import MicrostructureRegime
from l1_microstructure.transitions import EdgeKey
from l1_microstructure.workflow import ArtifactDrivenResearchWorkflow
from l1_microstructure.artifacts import ArtifactBundleSelector, LocalArtifactStore, RunQualityGate


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if not hasattr(args, "command") or args.command is None:
        parser.print_help()
        return 1

    if args.command == "workflow":
        return _run_workflow_command(args)
    if args.command == "list-runs":
        return _run_list_runs_command(args)
    if args.command == "paper-historical":
        return _run_historical_command(args)
    if args.command == "paper-live":
        return _run_live_command(args)
    if args.command == "live-routed":
        return _run_routed_live_command(args)
    if args.command == "ibkr-live-smoke":
        return _run_ibkr_live_smoke_command(args)
    if args.command == "ibkr-live-order-smoke":
        return _run_ibkr_live_order_smoke_command(args)
    parser.error(f"unknown command: {args.command}")
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="l1-microstructure")
    subparsers = parser.add_subparsers(dest="command")

    workflow_parser = subparsers.add_parser("workflow")
    workflow_parser.add_argument("--artifact-root", required=True)
    workflow_parser.add_argument("--symbol", required=True)
    workflow_parser.add_argument("--trade-date", required=True)
    workflow_parser.add_argument("--transition-threshold", type=float, default=None)

    list_runs_parser = subparsers.add_parser("list-runs")
    list_runs_parser.add_argument("--artifact-root", required=True)
    list_runs_parser.add_argument("--symbol", required=True)
    list_runs_parser.add_argument("--trade-date", default=None)
    list_runs_parser.add_argument("--passing-only", action="store_true")
    _add_quality_gate_arguments(list_runs_parser)

    historical_parser = subparsers.add_parser("paper-historical")
    historical_parser.add_argument("--artifact-root", required=True)
    historical_parser.add_argument("--symbol", required=True)
    historical_parser.add_argument("--trade-date", required=True)
    historical_parser.add_argument("--run-id", default=None)
    historical_parser.add_argument("--mode", default="paper")
    historical_parser.add_argument("--latency-ms", type=int, default=100)
    historical_parser.add_argument("--transition-threshold", type=float, default=None)
    historical_parser.add_argument("--require-validation-passed", action="store_true")
    _add_quality_gate_arguments(historical_parser)

    live_parser = subparsers.add_parser("paper-live")
    live_parser.add_argument("--artifact-root", required=True)
    live_parser.add_argument("--symbol", required=True)
    live_parser.add_argument("--run-id", default=None)
    live_parser.add_argument("--mode", default="paper")
    live_parser.add_argument("--latency-ms", type=int, default=100)
    live_parser.add_argument("--transition-threshold", type=float, default=None)
    live_parser.add_argument("--require-validation-passed", action="store_true")
    _add_quality_gate_arguments(live_parser)

    routed_live_parser = subparsers.add_parser("live-routed")
    routed_live_parser.add_argument("--artifact-root", required=True)
    routed_live_parser.add_argument("--symbol", required=True)
    routed_live_parser.add_argument("--run-id", default=None)
    routed_live_parser.add_argument("--mode", default="live")
    routed_live_parser.add_argument("--latency-ms", type=int, default=100)
    routed_live_parser.add_argument("--transition-threshold", type=float, default=None)
    routed_live_parser.add_argument("--require-validation-passed", action="store_true")
    routed_live_parser.add_argument("--broker-env-file", default=None)
    routed_live_parser.add_argument("--broker-order-mode", choices=("market", "limit"), default="market")
    routed_live_parser.add_argument("--broker-limit-offset-bps", type=float, default=0.0)
    routed_live_parser.add_argument("--allow-live-broker-routing", action="store_true")
    _add_quality_gate_arguments(routed_live_parser)

    ibkr_smoke_parser = subparsers.add_parser("ibkr-live-smoke")
    ibkr_smoke_parser.add_argument("--broker-env-file", default=None)
    ibkr_smoke_parser.add_argument("--allow-live-broker-routing", action="store_true")

    ibkr_order_smoke_parser = subparsers.add_parser("ibkr-live-order-smoke")
    ibkr_order_smoke_parser.add_argument("--symbol", required=True)
    ibkr_order_smoke_parser.add_argument("--quantity", type=int, default=1)
    ibkr_order_smoke_parser.add_argument("--action", choices=("buy", "sell"), default="buy")
    ibkr_order_smoke_parser.add_argument("--broker-env-file", default=None)
    ibkr_order_smoke_parser.add_argument("--broker-order-mode", choices=("market", "limit"), default="limit")
    ibkr_order_smoke_parser.add_argument("--broker-limit-offset-bps", type=float, default=0.0)
    ibkr_order_smoke_parser.add_argument("--poll-attempts", type=int, default=3)
    ibkr_order_smoke_parser.add_argument("--poll-interval-ms", type=int, default=250)
    ibkr_order_smoke_parser.add_argument("--allow-live-broker-routing", action="store_true")

    return parser


def _add_quality_gate_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--min-fill-rate", type=float, default=None)
    parser.add_argument("--max-cancel-rate", type=float, default=None)
    parser.add_argument("--max-drift-tracking-error-bps", type=float, default=None)
    parser.add_argument("--max-unseen-edge-rate", type=float, default=None)


def _framework_config(transition_threshold: float | None) -> FrameworkConfig:
    config = FrameworkConfig()
    if transition_threshold is not None:
        config.transition.mahalanobis_threshold = transition_threshold
    return config


def _historical_source() -> MassiveRESTDataSource:
    return MassiveRESTDataSource()


def _live_source() -> MassiveWebSocketDataSource:
    return MassiveWebSocketDataSource(MassiveWebSocketConfig())


def _run_workflow_command(args: argparse.Namespace) -> int:
    source = _historical_source()
    events = list(
        source.load_historical(
            HistoricalBatchRequest(symbols=(args.symbol,), trade_date=date.fromisoformat(args.trade_date))
        )
    )
    workflow = ArtifactDrivenResearchWorkflow(
        args.artifact_root,
        framework_config=_framework_config(args.transition_threshold),
    )
    result = workflow.run(symbol=args.symbol, events=events)
    print(json.dumps(_workflow_result_to_json(result), sort_keys=True))
    return 0


def _run_list_runs_command(args: argparse.Namespace) -> int:
    selector = ArtifactBundleSelector(LocalArtifactStore(args.artifact_root))
    quality_gate = _quality_gate_from_args(args)
    manifests = selector.list_run_manifests(args.symbol, passing_only=args.passing_only, quality_gate=quality_gate)
    if args.trade_date is not None:
        manifests = [manifest for manifest in manifests if manifest.trade_date == args.trade_date]
    manifests.sort(key=lambda manifest: (manifest.created_at, manifest.run_id), reverse=True)
    print(
        json.dumps(
            {
                "symbol": args.symbol,
                "trade_date": args.trade_date,
                "passing_only": args.passing_only,
                "quality_gate": _quality_gate_to_json(quality_gate),
                "run_count": len(manifests),
                "runs": [
                    {
                        "run_id": manifest.run_id,
                        "trade_date": manifest.trade_date,
                        "created_at": manifest.created_at,
                        "artifact_ids": manifest.artifact_ids,
                        "quality_metrics": _quality_metrics_from_metadata(manifest.metadata),
                        "metadata": manifest.metadata,
                    }
                    for manifest in manifests
                ],
            },
            sort_keys=True,
        )
    )
    return 0


def _run_historical_command(args: argparse.Namespace) -> int:
    source = _historical_source()
    selector = ArtifactBundleSelector(LocalArtifactStore(args.artifact_root))
    runner = SourceBackedPaperRunner(
        source=source,
        framework_config=_framework_config(args.transition_threshold),
        bundle_selector=selector,
        require_validation_passed=args.require_validation_passed,
        quality_gate=_quality_gate_from_args(args),
    )
    historical_runner = runner.run_historical(
        HistoricalBatchRequest(symbols=(args.symbol,), trade_date=date.fromisoformat(args.trade_date)),
        RunnerConfig(symbols=(args.symbol,), mode=args.mode, latency_ms=args.latency_ms),
        run_id=args.run_id,
    )
    print(json.dumps(_runner_result_to_json(historical_runner), sort_keys=True))
    return 0


def _run_live_command(args: argparse.Namespace) -> int:
    source = _live_source()
    selector = ArtifactBundleSelector(LocalArtifactStore(args.artifact_root))
    runner = SourceBackedPaperRunner(
        source=source,
        framework_config=_framework_config(args.transition_threshold),
        bundle_selector=selector,
        require_validation_passed=args.require_validation_passed,
        quality_gate=_quality_gate_from_args(args),
    )
    live_runner = runner.run_live(
        LiveSubscriptionRequest(symbols=(args.symbol,)),
        RunnerConfig(symbols=(args.symbol,), mode=args.mode, latency_ms=args.latency_ms),
        run_id=args.run_id,
    )
    print(json.dumps(_runner_result_to_json(live_runner), sort_keys=True))
    return 0


def _run_routed_live_command(args: argparse.Namespace) -> int:
    if bool(getattr(args, "allow_live_broker_routing", False)):
        raise ValueError("live capital routing requires the supervised trading-daemon runtime")
    source = _live_source()
    selector = ArtifactBundleSelector(LocalArtifactStore(args.artifact_root))
    router = _router_from_args(args)
    runner = RoutedLiveTradingRunner(
        source=source,
        router=router,
        framework_config=_framework_config(args.transition_threshold),
        bundle_selector=selector,
        require_validation_passed=args.require_validation_passed,
        quality_gate=_quality_gate_from_args(args),
    )
    try:
        live_runner = runner.run_live(
            LiveSubscriptionRequest(symbols=(args.symbol,)),
            RunnerConfig(symbols=(args.symbol,), mode=args.mode, latency_ms=args.latency_ms),
            run_id=args.run_id,
        )
        print(json.dumps(_runner_result_to_json(live_runner), sort_keys=True))
    finally:
        runner.stop()
    return 0


def _run_ibkr_live_smoke_command(args: argparse.Namespace) -> int:
    router = IBKRBrokerOrderRouter.from_env(
        getattr(args, "broker_env_file", None),
        require_paper=not bool(getattr(args, "allow_live_broker_routing", False)),
    )
    try:
        health = router.health_check()
        payload = {
            "router_type": "ibkr-live",
            "health": health,
            "open_order_ids": router.open_order_ids(),
            "diagnostics": _ibkr_diagnostics(health),
        }
        print(json.dumps(payload, sort_keys=True, default=str))
    finally:
        router.stop()
    return 0


def _run_ibkr_live_order_smoke_command(args: argparse.Namespace) -> int:
    request = _build_ibkr_order_smoke_request(
        latest_state=_latest_observed_state_from_rest(args.symbol),
        symbol=args.symbol,
        quantity=max(int(args.quantity), 1),
        action_name=args.action,
    )
    router = IBKRBrokerOrderRouter.from_env(
        getattr(args, "broker_env_file", None),
        prefer_limit_orders=getattr(args, "broker_order_mode", "limit") == "limit",
        limit_price_offset_bps=float(getattr(args, "broker_limit_offset_bps", 0.0)),
        require_paper=not bool(getattr(args, "allow_live_broker_routing", False)),
    )
    poll_attempts = max(int(getattr(args, "poll_attempts", 3)), 0)
    poll_interval_seconds = max(int(getattr(args, "poll_interval_ms", 250)), 0) / 1000.0
    execution_reports: list[ExecutionReport] = []
    acknowledgement = None
    cancel_attempted = False
    cancel_succeeded = False
    open_order_ids_before_cancel: list[str] = []

    try:
        acknowledgement = router.submit(request)
        for attempt in range(poll_attempts):
            execution_reports.extend(router.poll((args.symbol,)))
            if acknowledgement.external_order_id not in router.open_order_ids():
                break
            if attempt + 1 < poll_attempts and poll_interval_seconds > 0.0:
                time.sleep(poll_interval_seconds)

        open_order_ids_before_cancel = router.open_order_ids()
        if acknowledgement.external_order_id in open_order_ids_before_cancel:
            cancel_attempted = True
            cancel_succeeded = bool(router.cancel(acknowledgement.external_order_id))
            if poll_interval_seconds > 0.0:
                time.sleep(poll_interval_seconds)
            execution_reports.extend(router.poll((args.symbol,)))

        health = router.health_check()
        payload = {
            "router_type": "ibkr-live",
            "request": _execution_request_to_json(request),
            "acknowledgement": _route_acknowledgement_to_json(acknowledgement),
            "health": health,
            "execution_reports": [_execution_report_to_json(report) for report in execution_reports],
            "open_order_ids_before_cancel": open_order_ids_before_cancel,
            "final_open_order_ids": router.open_order_ids(),
            "cancel_attempted": cancel_attempted,
            "cancel_succeeded": cancel_succeeded,
            "diagnostics": _ibkr_diagnostics(health, execution_reports),
        }
        print(json.dumps(payload, sort_keys=True, default=str))
    finally:
        router.stop()
    return 0


def _ibkr_diagnostics(
    health: dict[str, Any], execution_reports: Sequence[ExecutionReport] = ()
) -> dict[str, str] | None:
    messages: list[str] = []
    for key in ("last_error", "error"):
        value = health.get(key)
        if isinstance(value, str) and value.strip():
            messages.append(value.strip())
    messages.extend(str(report.reason).strip() for report in execution_reports if getattr(report, "reason", None))

    for message in messages:
        normalized = message.lower()
        if "read-only mode" in normalized or "read-only api" in normalized:
            return {
                "issue": "read_only_api_mode",
                "message": message,
                "recommended_action": "Disable 'Read-Only API' in IBKR Gateway or TWS API settings, then rerun ibkr-live-order-smoke.",
            }
        if "couldn't connect to tws" in normalized or "failed to connect to ibkr gateway" in normalized:
            return {
                "issue": "broker_socket_unreachable",
                "message": message,
                "recommended_action": "Start IBKR Gateway or TWS, verify API socket access is enabled, confirm the host and port in broker.env, then rerun ibkr-live-smoke.",
            }

    return None


def _workflow_result_to_json(result: Any) -> dict[str, Any]:
    return {
        "symbol": result.symbol,
        "run_id": result.run_id,
        "state_panel_rows": result.state_panel_rows,
        "transition_panel_rows": result.transition_panel_rows,
        "artifact_ids": asdict(result.artifact_ids),
        "run_manifest_id": result.artifact_ids.run_manifest_id,
        "validation_passed": result.validation_report.passed,
        "validation_failures": list(result.validation_report.failures),
        "validation_summary": result.validation_report.summary,
        "replay_summary": result.replay_summary,
    }


def _runner_result_to_json(runner: Any) -> dict[str, Any]:
    return {
        "update_count": len(runner.updates),
        "execution_summary": runner.execution_summary(),
        "monitoring_rows": int(runner.monitoring_frame().shape[0]),
        "artifact_bundle": dict(runner.runtime_artifacts.artifact_ids),
        "runtime_metadata": dict(runner.runtime_artifacts.metadata),
        "quality_metrics": _quality_metrics_from_metadata(runner.runtime_artifacts.metadata),
        "route_acknowledgement_count": len(getattr(runner, "route_acknowledgements", [])),
    }


def _router_from_args(args: argparse.Namespace) -> Any:
    return IBKRBrokerOrderRouter.from_env(
        getattr(args, "broker_env_file", None),
        prefer_limit_orders=getattr(args, "broker_order_mode", "market") == "limit",
        limit_price_offset_bps=float(getattr(args, "broker_limit_offset_bps", 0.0)),
        require_paper=not bool(getattr(args, "allow_live_broker_routing", False)),
    )


def _quality_gate_from_args(args: argparse.Namespace) -> RunQualityGate | None:
    quality_gate = RunQualityGate(
        minimum_fill_rate=getattr(args, "min_fill_rate", None),
        maximum_cancel_rate=getattr(args, "max_cancel_rate", None),
        maximum_drift_tracking_error_bps=getattr(args, "max_drift_tracking_error_bps", None),
        maximum_unseen_edge_rate=getattr(args, "max_unseen_edge_rate", None),
    )
    if all(value is None for value in asdict(quality_gate).values()):
        return None
    return quality_gate


def _quality_gate_to_json(quality_gate: RunQualityGate | None) -> dict[str, float] | None:
    if quality_gate is None:
        return None
    return {key: value for key, value in asdict(quality_gate).items() if value is not None}


def _quality_metrics_from_metadata(metadata: dict[str, Any]) -> dict[str, float]:
    keys = (
        "mean_test_fill_rate",
        "mean_test_cancel_rate",
        "mean_execution_drift_tracking_error_bps",
        "mean_unseen_edge_rate",
        "mean_test_hit_rate",
    )
    return {key: float(metadata[key]) for key in keys if key in metadata}


def _build_ibkr_order_smoke_request(
    latest_state: ObservedState,
    *,
    symbol: str,
    quantity: int,
    action_name: str,
) -> ExecutionRequest:
    action = TradeAction.BUY if action_name == "buy" else TradeAction.SELL
    posterior = PosteriorEstimate(
        mean_bps=1.0 if action == TradeAction.BUY else -1.0,
        std_bps=1.0,
        probability_up=0.75 if action == TradeAction.BUY else 0.25,
        probability_down=0.25 if action == TradeAction.BUY else 0.75,
        threshold_bps=0.0,
        sample_count=1,
    )
    intent = TradeIntent(
        action=action,
        edge=EdgeKey(latest_state.label, latest_state.label, MicrostructureRegime.EXECUTION_FLOW),
        posterior=posterior,
        expected_holding_time_ns=1_000_000_000,
        reason="ibkr routed order smoke",
    )
    return ExecutionSimulator().build_request(intent, latest_state, quantity)


def _latest_observed_state_from_rest(symbol: str) -> ObservedState:
    try:
        from massive import RESTClient
    except ImportError as exc:
        raise RuntimeError("massive client is required for IBKR smoke request construction") from exc

    api_key = _resolve_massive_api_key(None)
    if api_key is None:
        raise RuntimeError("MASSIVE_API_KEY is required for IBKR smoke request construction")

    quote = RESTClient(api_key=api_key, pagination=False).get_last_quote(symbol)
    payload = {
        "ev": "Q",
        "sym": symbol,
        "t": getattr(quote, "sip_timestamp", None) or getattr(quote, "participant_timestamp", None),
        "bp": getattr(quote, "bid_price", None),
        "ap": getattr(quote, "ask_price", None),
        "bs": getattr(quote, "bid_size", None),
        "as": getattr(quote, "ask_size", None),
        "q": getattr(quote, "sequence_number", None),
    }
    event = MassivePayloadNormalizer().normalize(payload)
    if not isinstance(event, MarketEvent):
        raise ValueError(f"could not normalize last quote for symbol {symbol}")
    observed_state = FeatureEngine().update(event)
    if observed_state is None:
        raise ValueError(f"last quote did not produce any observable state for symbol {symbol}")
    return observed_state


def _execution_request_to_json(request: ExecutionRequest) -> dict[str, Any]:
    return {
        "symbol": request.symbol,
        "action": request.action.value,
        "quantity": request.quantity,
        "decision_timestamp_ns": request.decision_timestamp_ns,
        "executable_timestamp_ns": request.executable_timestamp_ns,
        "reason": request.intent.reason,
        "expected_touch": {
            "bid_price": request.expected_state.book.bid_price,
            "ask_price": request.expected_state.book.ask_price,
        },
    }


def _execution_report_to_json(report: ExecutionReport) -> dict[str, Any]:
    return {
        "symbol": report.symbol,
        "action": report.action.value,
        "status": report.status,
        "quantity": report.quantity,
        "fill_price": report.fill_price,
        "alignment_probability": report.alignment_probability,
        "fill_probability": report.fill_probability,
        "slippage_bps": report.slippage_bps,
        "reason": report.reason,
        "timestamp_ns": report.timestamp_ns,
    }


def _route_acknowledgement_to_json(acknowledgement: Any) -> dict[str, Any]:
    return {
        "external_order_id": acknowledgement.external_order_id,
        "status": acknowledgement.status,
        "reason": acknowledgement.reason,
        "metadata": dict(acknowledgement.metadata),
    }


from l1_microstructure.artifacts import LocalArtifactStore  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
