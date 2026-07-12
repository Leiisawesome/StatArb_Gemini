"""Lazy facade for paper, routed, and broker integration components."""

from importlib import import_module
from typing import Any


_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "BrokerOpenOrderRecovery": (".router_adapters", "BrokerOpenOrderRecovery"),
    "BrokerOrder": (".broker_models", "BrokerOrder"),
    "BrokerOrderSide": (".broker_models", "BrokerOrderSide"),
    "BrokerOrderStatus": (".broker_models", "BrokerOrderStatus"),
    "BrokerOrderType": (".broker_models", "BrokerOrderType"),
    "BrokerRouterRecoveryState": (".router_adapters", "BrokerRouterRecoveryState"),
    "ExecutionReportConsumer": (".execution_session", "ExecutionReportConsumer"),
    "IBKRBrokerOrderRouter": (".router_adapters", "IBKRBrokerOrderRouter"),
    "IBKRConnectionConfig": (".broker_models", "IBKRConnectionConfig"),
    "OrderRouter": (".interfaces", "OrderRouter"),
    "PaperTradingRunner": (".interfaces", "PaperTradingRunner"),
    "ProductionOrderRouter": (".interfaces", "ProductionOrderRouter"),
    "RouteAcknowledgement": (".interfaces", "RouteAcknowledgement"),
    "RoutedExecutionService": (".execution_session", "RoutedExecutionService"),
    "RoutedLiveTradingRunner": (".routed", "RoutedLiveTradingRunner"),
    "RunnerConfig": (".interfaces", "RunnerConfig"),
    "SimulatorPaperTradingRunner": (".paper", "SimulatorPaperTradingRunner"),
    "SourceBackedPaperRunner": (".source", "SourceBackedPaperRunner"),
}


def __getattr__(name: str) -> Any:
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute_name = target
    value = getattr(import_module(module_name, __name__), attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))


__all__ = [
    "OrderRouter",
    "PaperTradingRunner",
    "ProductionOrderRouter",
    "RouteAcknowledgement",
    "RunnerConfig",
    "BrokerOrder",
    "BrokerOrderSide",
    "BrokerOrderStatus",
    "BrokerOrderType",
    "IBKRConnectionConfig",
    "ExecutionReportConsumer",
    "BrokerOpenOrderRecovery",
    "BrokerRouterRecoveryState",
    "IBKRBrokerOrderRouter",
    "RoutedLiveTradingRunner",
    "RoutedExecutionService",
    "SimulatorPaperTradingRunner",
    "SourceBackedPaperRunner",
]
