"""Lazy facade for ingestion contracts and Massive implementations."""

from importlib import import_module
from typing import Any


_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "EventNormalizer": (".interfaces", "EventNormalizer"),
    "ExclusionWindow": ("._massive_support", "ExclusionWindow"),
    "ExtendedHoursSessionFilter": ("._massive_support", "ExtendedHoursSessionFilter"),
    "HistoricalBatchRequest": (".interfaces", "HistoricalBatchRequest"),
    "LiveSubscriptionRequest": (".interfaces", "LiveSubscriptionRequest"),
    "MarketDataSource": (".interfaces", "MarketDataSource"),
    "MassiveFilterConfig": ("._massive_support", "MassiveFilterConfig"),
    "MassivePayloadNormalizer": ("._massive_support", "MassivePayloadNormalizer"),
    "MassiveRESTConfig": (".massive", "MassiveRESTConfig"),
    "MassiveRESTDataSource": (".massive", "MassiveRESTDataSource"),
    "MassiveWebSocketConfig": (".massive", "MassiveWebSocketConfig"),
    "MassiveWebSocketDataSource": (".massive", "MassiveWebSocketDataSource"),
    "RTHSessionFilter": ("._massive_support", "RTHSessionFilter"),
    "SessionFilter": (".interfaces", "SessionFilter"),
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
    "EventNormalizer",
    "ExtendedHoursSessionFilter",
    "ExclusionWindow",
    "HistoricalBatchRequest",
    "LiveSubscriptionRequest",
    "MarketDataSource",
    "MassiveFilterConfig",
    "MassivePayloadNormalizer",
    "MassiveRESTConfig",
    "MassiveRESTDataSource",
    "MassiveWebSocketConfig",
    "MassiveWebSocketDataSource",
    "RTHSessionFilter",
    "SessionFilter",
]
