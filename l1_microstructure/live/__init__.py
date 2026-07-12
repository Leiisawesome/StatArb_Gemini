"""Paper and live runner contracts and implementations for the successor package."""

from .interfaces import OrderRouter, PaperTradingRunner, ProductionOrderRouter, RouteAcknowledgement, RunnerConfig
from .execution_session import ExecutionReportConsumer, RoutedExecutionService
from .broker_models import BrokerOrder, BrokerOrderSide, BrokerOrderStatus, BrokerOrderType, IBKRConnectionConfig
from .paper import SimulatorPaperTradingRunner
from .router_adapters import (
    BrokerOpenOrderRecovery,
    BrokerRouterRecoveryState,
    IBKRBrokerOrderRouter,
)
from .routed import RoutedLiveTradingRunner
from .source import SourceBackedPaperRunner

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
