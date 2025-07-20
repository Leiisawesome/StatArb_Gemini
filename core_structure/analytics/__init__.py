"""
Analytics Platform Module

Professional-grade analytics platform providing:
- Advanced performance analytics and attribution
- Research and backtesting platform
- Real-time monitoring and alerting
- AI-powered insights and recommendations
- Interactive data visualization
- Comprehensive reporting engine

This module transforms raw trading data into actionable insights
with institutional-grade analytics capabilities.
"""

from .performance_analytics import (
    PerformanceAnalyzer, AttributionAnalyzer, RiskAnalyzer,
    PerformanceMetrics, AttributionReport
)
from .research_platform import (
    ResearchEngine, BacktestEngine, StrategyDeveloper,
    BacktestResult, StrategyPerformance
)
from .monitoring_system import (
    MonitoringEngine, AlertManager, RealTimeMonitor,
    AlertRule, MonitoringDashboard
)
from .reporting_engine import (
    ReportGenerator, DashboardManager, ReportScheduler,
    Report, Dashboard, ReportTemplate
)
from .data_visualization import (
    ChartGenerator, InteractiveCharts, VisualizationEngine,
    Chart, PlotConfig, ChartTheme
)
from .ai_insights import (
    InsightsEngine, RecommendationEngine, PatternDetector,
    Insight, Recommendation, Pattern
)

__all__ = [
    # Performance analytics
    'PerformanceAnalyzer',
    'AttributionAnalyzer',
    'RiskAnalyzer',
    'PerformanceMetrics',
    'AttributionReport',
    
    # Research platform
    'ResearchEngine',
    'BacktestEngine',
    'StrategyDeveloper',
    'BacktestResult',
    'StrategyPerformance',
    
    # Monitoring system
    'MonitoringEngine',
    'AlertManager',
    'RealTimeMonitor',
    'AlertRule',
    'MonitoringDashboard',
    
    # Reporting engine
    'ReportGenerator',
    'DashboardManager',
    'ReportScheduler',
    'Report',
    'Dashboard',
    'ReportTemplate',
    
    # Data visualization
    'ChartGenerator',
    'InteractiveCharts',
    'VisualizationEngine',
    'Chart',
    'PlotConfig',
    'ChartTheme',
    
    # AI insights
    'InsightsEngine',
    'RecommendationEngine',
    'PatternDetector',
    'Insight',
    'Recommendation',
    'Pattern'
]

__version__ = "1.0.0" 