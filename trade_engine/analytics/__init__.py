#!/usr/bin/env python3
"""
Analytics Package Initialization
================================

Unified analytics and intelligence system for the trading engine.
Comprehensive analytics platform providing:
- ML-powered performance analysis and attribution
- Advanced risk assessment and modeling
- Research and backtesting platform
- Real-time monitoring and alerting
- AI-powered insights and recommendations
- Interactive data visualization
- Comprehensive reporting engine
- Execution analytics and optimization

Author: StatArb_Gemini Team
"""

# Core ML-powered analytics
from .performance_analyzer import PerformanceAnalyzer, performance_analyzer
from .predictive_monitor import PredictiveMonitor, predictive_monitor
from .anomaly_detector import AnomalyDetector, anomaly_detector
from .risk_analyzer import RiskAnalyzer
from .attribution_analyzer import AttributionAnalyzer
from .optimization_engine import OptimizationEngine
from .regime_detector import RegimeDetector

# Execution and research analytics
from .execution_analytics import ExecutionAnalytics, ExecutionQualityMetrics
from .research_platform import ResearchEngine, BacktestEngine, StrategyDeveloper

# Monitoring and visualization
from .monitoring_system import MonitoringEngine, AlertManager, RealTimeMonitor
from .multi_strategy_dashboard import MultiStrategyDashboard
from .data_visualization import ChartGenerator, InteractiveCharts, VisualizationEngine
from .reporting_engine import ReportGenerator, DashboardManager, ReportScheduler
from .ai_insights import InsightsEngine, RecommendationEngine, PatternDetector

# Legacy compatibility
from .legacy_performance_analytics import PerformanceAnalyzer as LegacyPerformanceAnalyzer

__all__ = [
    # Core ML analytics
    'PerformanceAnalyzer',
    'performance_analyzer',
    'PredictiveMonitor', 
    'predictive_monitor',
    'AnomalyDetector',
    'anomaly_detector',
    'RiskAnalyzer',
    'AttributionAnalyzer',
    'OptimizationEngine',
    'RegimeDetector',
    
    # Execution and research
    'ExecutionAnalytics',
    'ExecutionQualityMetrics',
    'ResearchEngine',
    'BacktestEngine',
    'StrategyDeveloper',
    
    # Monitoring and visualization
    'MonitoringEngine',
    'AlertManager',
    'RealTimeMonitor',
    'MultiStrategyDashboard',
    'ChartGenerator',
    'InteractiveCharts',
    'VisualizationEngine',
    'ReportGenerator',
    'DashboardManager',
    'ReportScheduler',
    'InsightsEngine',
    'RecommendationEngine',
    'PatternDetector',
    
    # Legacy compatibility
    'LegacyPerformanceAnalyzer'
]
