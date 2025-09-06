"""
Advanced Trading Dashboard Suite
===============================

Professional trading dashboard with comprehensive features:
- Real-time monitoring and analytics
- Interactive charts with technical indicators
- Advanced alert system with multiple notification channels
- Automated reporting and export capabilities

Author: Pro Quant Desk Trader
"""

__version__ = "2.0.0"
__author__ = "Pro Quant Desk Trader"

# Core dashboard components
from .dashboard_server import TradingDashboardServer
from .analytics_engine import RealTimeAnalytics
from .data_collector import TradingDataCollector

# Priority 3 components
from .charting_engine import ChartingEngine, TechnicalAnalysis
from .alert_system import AlertSystem, AlertRule, NotificationConfig, AlertSeverity, AlertType, NotificationChannel
from .reporting_engine import ReportingEngine, ReportConfig, ReportType, ReportFormat

__all__ = [
    # Core components
    'TradingDashboardServer',
    'RealTimeAnalytics', 
    'TradingDataCollector',
    
    # Charting
    'ChartingEngine',
    'TechnicalAnalysis',
    
    # Alerts
    'AlertSystem',
    'AlertRule',
    'NotificationConfig',
    'AlertSeverity',
    'AlertType',
    'NotificationChannel',
    
    # Reporting
    'ReportingEngine',
    'ReportConfig',
    'ReportType',
    'ReportFormat'
]
