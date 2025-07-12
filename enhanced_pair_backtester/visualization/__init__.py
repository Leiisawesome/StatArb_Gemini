"""
Visualization module for enhanced pair trading system.

This module provides comprehensive visualization capabilities including:
- Performance charts and analytics
- Walk forward analysis plots
- Risk and return analysis
- Signal and position visualization
- Interactive dashboards
"""

from .charts import (
    PerformanceCharts,
    WalkForwardCharts,
    SignalCharts,
    RiskCharts
)
from .dashboard import TradingDashboard
from .utils import ChartConfig, ColorScheme

__all__ = [
    'PerformanceCharts',
    'WalkForwardCharts', 
    'SignalCharts',
    'RiskCharts',
    'TradingDashboard',
    'ChartConfig',
    'ColorScheme'
] 