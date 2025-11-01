#!/usr/bin/env python3
"""
Core Engine Fail-Fast Exception Hierarchy
========================================

Defines exceptions for fail-fast strategy implementation.
All fallback mechanisms are replaced with explicit exceptions.

Author: StatArb_Gemini Core Engine Team
Version: 1.0.0
"""


class CoreEngineError(Exception):
    """Base exception for core engine failures"""


class DataUnavailableError(CoreEngineError):
    """Raised when required data is unavailable"""


class ClickHouseConnectionError(CoreEngineError):
    """Raised when ClickHouse database connection fails"""


class BrokerConnectionError(CoreEngineError):
    """Raised when broker connection fails"""


class ExecutionEngineUnavailableError(CoreEngineError):
    """Raised when execution engine is unavailable"""


class EnhancedStrategyUnavailableError(CoreEngineError):
    """Raised when enhanced strategies are unavailable"""


class ConfigurationRequiredError(CoreEngineError):
    """Raised when required configuration is missing"""


class PerformanceDataUnavailableError(CoreEngineError):
    """Raised when real performance data is unavailable"""


class BenchmarkDataUnavailableError(CoreEngineError):
    """Raised when real benchmark data is unavailable"""


class StrategyDataUnavailableError(CoreEngineError):
    """Raised when strategy data is unavailable"""
