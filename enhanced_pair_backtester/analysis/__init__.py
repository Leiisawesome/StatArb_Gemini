"""
Performance Analysis Module

This module provides comprehensive performance analysis capabilities for pairs trading:
- Return and risk metrics calculation
- Sharpe ratio, Sortino ratio, and other risk-adjusted returns
- Drawdown analysis and recovery metrics
- Trade-level performance analysis
- Benchmark comparison and attribution
- Rolling performance windows
- Statistical significance testing
"""

from .performance_metrics import PerformanceAnalyzer, PerformanceMetrics, ReturnMetrics, RiskMetrics

__all__ = [
    'PerformanceAnalyzer',
    'PerformanceMetrics',
    'ReturnMetrics',
    'RiskMetrics'
] 