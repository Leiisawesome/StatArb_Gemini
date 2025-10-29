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
    pass


class DataUnavailableError(CoreEngineError):
    """Raised when required data is unavailable"""
    pass


class ClickHouseConnectionError(CoreEngineError):
    """Raised when ClickHouse database connection fails"""
    pass


class BrokerConnectionError(CoreEngineError):
    """Raised when broker connection fails"""
    pass


class ExecutionEngineUnavailableError(CoreEngineError):
    """Raised when execution engine is unavailable"""
    pass


class EnhancedStrategyUnavailableError(CoreEngineError):
    """Raised when enhanced strategies are unavailable"""
    pass


class ConfigurationRequiredError(CoreEngineError):
    """Raised when required configuration is missing"""
    pass


class PerformanceDataUnavailableError(CoreEngineError):
    """Raised when real performance data is unavailable"""
    pass


class BenchmarkDataUnavailableError(CoreEngineError):
    """Raised when real benchmark data is unavailable"""
    pass


class StrategyDataUnavailableError(CoreEngineError):
    """Raised when strategy data is unavailable"""
    pass
