"""
Performance Dashboard
====================

Real-time performance dashboard for monitoring and visualizing
system performance metrics and optimization status.

Author: Pro Quant Desk Trader
"""

import asyncio
import logging
import time
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

class DashboardMode(Enum):
    """Dashboard display modes"""
    OVERVIEW = "overview"
    DETAILED = "detailed"
    OPTIMIZATION = "optimization"
    ALERTS = "alerts"

@dataclass
class DashboardConfig:
    """Configuration for performance dashboard"""
    # Display settings
    refresh_interval_seconds: int = 5
    history_duration_minutes: int = 60
    max_alerts_displayed: int = 20
    
    # Visualization settings
    enable_real_time_charts: bool = True
    enable_performance_trends: bool = True
    enable_optimization_tracking: bool = True
    
    # Export settings
    enable_data_export: bool = True
    export_format: str = "json"  # json, csv, html

@dataclass
class DashboardMetric:
    """Dashboard metric representation"""
    name: str
    current_value: float
    target_value: Optional[float]
    trend: str  # "improving", "degrading", "stable"
    status: str  # "healthy", "warning", "critical"
    history: List[float] = field(default_factory=list)

class MetricFormatter:
    """Formats metrics for dashboard display"""
    
    @staticmethod
    def format_latency(value_ms: float) -> str:
        """Format latency for display"""
        if value_ms < 1:
            return f"{value_ms:.3f}ms"
        elif value_ms < 1000:
            return f"{value_ms:.1f}ms"
        else:
            return f"{value_ms/1000:.2f}s"
    
    @staticmethod
    def format_throughput(value: float) -> str:
        """Format throughput for display"""
        if value < 1000:
            return f"{value:.0f}/sec"
        elif value < 1000000:
            return f"{value/1000:.1f}k/sec"
        else:
            return f"{value/1000000:.1f}M/sec"
    
    @staticmethod
    def format_percentage(value: float) -> str:
        """Format percentage for display"""
        return f"{value*100:.1f}%" if value < 1 else f"{value:.1f}%"
    
    @staticmethod
    def format_memory(value_mb: float) -> str:
        """Format memory usage for display"""
        if value_mb < 1024:
            return f"{value_mb:.0f}MB"
        else:
            return f"{value_mb/1024:.1f}GB"

class PerformanceDashboard:
    """
    Real-time performance dashboard for monitoring system performance,
    optimization status, and providing actionable insights.
    """
    
    def __init__(self, config: Optional[DashboardConfig] = None):
        self.config = config or DashboardConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Dashboard state
        self.is_active = False
        self.last_update = datetime.now()
        self.dashboard_metrics: Dict[str, DashboardMetric] = {}
        
        # Data sources
        self.monitor = None
        self.optimizer = None
        self.auto_tuner = None
        
        # Performance tracking
        self.update_count = 0
        self.export_count = 0
        
        self.logger.info("Performance Dashboard initialized")
    
    def connect_data_sources(self, monitor=None, optimizer=None, auto_tuner=None):
        """Connect dashboard to data sources"""
        self.monitor = monitor
        self.optimizer = optimizer
        self.auto_tuner = auto_tuner
        
        connected_sources = []
        if monitor:
            connected_sources.append("monitor")
        if optimizer:
            connected_sources.append("optimizer")
        if auto_tuner:
            connected_sources.append("auto_tuner")
        
        self.logger.info(f"Connected to data sources: {', '.join(connected_sources)}")
    
    def start_dashboard(self):
        """Start the performance dashboard"""
        self.is_active = True
        self.logger.info("Performance dashboard started")
    
    def stop_dashboard(self):
        """Stop the performance dashboard"""
        self.is_active = False
        self.logger.info("Performance dashboard stopped")
    
    def update_dashboard(self) -> Dict[str, Any]:
        """Update dashboard with latest data"""
        if not self.is_active:
            return {}
        
        dashboard_data = {
            'timestamp': datetime.now().isoformat(),
            'update_count': self.update_count,
            'system_overview': self._generate_system_overview(),
            'component_metrics': self._generate_component_metrics(),
            'optimization_status': self._generate_optimization_status(),
            'alerts_summary': self._generate_alerts_summary(),
            'performance_trends': self._generate_performance_trends()
        }
        
        self.update_count += 1
        self.last_update = datetime.now()
        
        return dashboard_data
    
    def _generate_system_overview(self) -> Dict[str, Any]:
        """Generate system overview metrics"""
        overview = {
            'overall_health': 'unknown',
            'total_components': 0,
            'active_alerts': 0,
            'optimization_active': False,
            'auto_tuning_active': False
        }
        
        try:
            # Get monitor status
            if self.monitor:
                monitor_status = self.monitor.get_overall_status()
                overview['total_components'] = len(monitor_status.get('monitored_components', []))
                overview['active_alerts'] = len(monitor_status.get('recent_alerts', []))
                
                # Determine overall health
                if overview['active_alerts'] == 0:
                    overview['overall_health'] = 'healthy'
                elif overview['active_alerts'] < 5:
                    overview['overall_health'] = 'warning'
                else:
                    overview['overall_health'] = 'critical'
            
            # Get optimization status
            if self.optimizer:
                optimizer_status = self.optimizer.get_optimization_status()
                overview['optimization_active'] = optimizer_status.get('optimization_active', False)
            
            # Get auto-tuner status
            if self.auto_tuner:
                tuner_status = self.auto_tuner.get_tuning_status()
                overview['auto_tuning_active'] = tuner_status.get('auto_tuning_active', False)
        
        except Exception as e:
            self.logger.error(f"Error generating system overview: {e}")
        
        return overview
    
    def _generate_component_metrics(self) -> Dict[str, Any]:
        """Generate component-specific metrics"""
        component_metrics = {}
        
        try:
            if self.monitor:
                monitor_status = self.monitor.get_overall_status()
                monitored_components = monitor_status.get('monitored_components', [])
                
                for component_name in monitored_components:
                    component_status = self.monitor.get_component_status(component_name)
                    
                    if component_status.get('metrics'):
                        formatted_metrics = {}
                        
                        for metric_type, stats in component_status['metrics'].items():
                            if isinstance(stats, dict) and 'mean' in stats:
                                # Format metric based on type
                                value = stats['mean']
                                
                                if 'latency' in metric_type or 'time' in metric_type:
                                    formatted_value = MetricFormatter.format_latency(value)
                                    target = 5.0  # 5ms target
                                    status = 'healthy' if value < target else 'warning' if value < target*2 else 'critical'
                                elif 'throughput' in metric_type or 'per_second' in metric_type:
                                    formatted_value = MetricFormatter.format_throughput(value)
                                    target = 1000.0  # 1k/sec target
                                    status = 'healthy' if value > target else 'warning' if value > target*0.5 else 'critical'
                                elif 'error' in metric_type:
                                    formatted_value = MetricFormatter.format_percentage(value)
                                    target = 0.01  # 1% target
                                    status = 'healthy' if value < target else 'warning' if value < target*2 else 'critical'
                                elif 'memory' in metric_type:
                                    formatted_value = MetricFormatter.format_memory(value)
                                    target = 1024.0  # 1GB target
                                    status = 'healthy' if value < target else 'warning' if value < target*1.5 else 'critical'
                                else:
                                    formatted_value = f"{value:.2f}"
                                    status = 'healthy'
                                
                                # Determine trend
                                trend = 'stable'
                                if 'std_dev' in stats and stats['std_dev'] > value * 0.1:  # High variance
                                    trend = 'volatile'
                                
                                formatted_metrics[metric_type] = {
                                    'value': formatted_value,
                                    'raw_value': value,
                                    'status': status,
                                    'trend': trend,
                                    'statistics': stats
                                }
                        
                        component_metrics[component_name] = formatted_metrics
        
        except Exception as e:
            self.logger.error(f"Error generating component metrics: {e}")
        
        return component_metrics
    
    def _generate_optimization_status(self) -> Dict[str, Any]:
        """Generate optimization status information"""
        optimization_status = {
            'optimizer_active': False,
            'total_optimizations': 0,
            'success_rate': 0.0,
            'recent_optimizations': [],
            'auto_tuner_status': {}
        }
        
        try:
            # Get optimizer status
            if self.optimizer:
                optimizer_data = self.optimizer.get_optimization_status()
                optimization_status.update({
                    'optimizer_active': optimizer_data.get('optimization_active', False),
                    'total_optimizations': optimizer_data.get('total_optimizations', 0),
                    'success_rate': optimizer_data.get('success_rate', 0.0),
                    'recent_optimizations': optimizer_data.get('recent_optimizations', [])
                })
            
            # Get auto-tuner status
            if self.auto_tuner:
                tuner_data = self.auto_tuner.get_tuning_status()
                optimization_status['auto_tuner_status'] = {
                    'active': tuner_data.get('auto_tuning_active', False),
                    'mode': tuner_data.get('tuning_mode', 'unknown'),
                    'phase': tuner_data.get('current_phase', 'unknown'),
                    'total_sessions': tuner_data.get('total_sessions', 0),
                    'success_rate': tuner_data.get('session_success_rate', 0.0)
                }
        
        except Exception as e:
            self.logger.error(f"Error generating optimization status: {e}")
        
        return optimization_status
    
    def _generate_alerts_summary(self) -> Dict[str, Any]:
        """Generate alerts summary"""
        alerts_summary = {
            'total_alerts': 0,
            'critical_alerts': 0,
            'warning_alerts': 0,
            'recent_alerts': [],
            'alert_trends': {}
        }
        
        try:
            if self.monitor:
                monitor_status = self.monitor.get_overall_status()
                recent_alerts = monitor_status.get('recent_alerts', [])
                
                alerts_summary['total_alerts'] = len(recent_alerts)
                
                # Count by severity
                for alert in recent_alerts:
                    if hasattr(alert, 'level'):
                        if alert.level.value == 'critical':
                            alerts_summary['critical_alerts'] += 1
                        elif alert.level.value == 'warning':
                            alerts_summary['warning_alerts'] += 1
                
                # Get recent alerts for display
                alerts_summary['recent_alerts'] = [
                    {
                        'timestamp': alert.timestamp.isoformat() if hasattr(alert, 'timestamp') else 'unknown',
                        'level': alert.level.value if hasattr(alert, 'level') else 'unknown',
                        'component': alert.component if hasattr(alert, 'component') else 'unknown',
                        'message': alert.message if hasattr(alert, 'message') else 'unknown'
                    }
                    for alert in recent_alerts[-self.config.max_alerts_displayed:]
                ]
        
        except Exception as e:
            self.logger.error(f"Error generating alerts summary: {e}")
        
        return alerts_summary
    
    def _generate_performance_trends(self) -> Dict[str, Any]:
        """Generate performance trends analysis"""
        trends = {
            'latency_trend': 'stable',
            'throughput_trend': 'stable',
            'error_rate_trend': 'stable',
            'optimization_effectiveness': 'unknown'
        }
        
        try:
            if self.monitor:
                # This would analyze historical data to determine trends
                # For now, provide basic trend analysis
                monitor_status = self.monitor.get_overall_status()
                
                if monitor_status.get('total_metrics_collected', 0) > 100:
                    trends['optimization_effectiveness'] = 'improving'
                
                # Could add more sophisticated trend analysis here
                # using historical performance data
        
        except Exception as e:
            self.logger.error(f"Error generating performance trends: {e}")
        
        return trends
    
    def export_dashboard_data(self, format_type: Optional[str] = None) -> str:
        """Export dashboard data in specified format"""
        format_type = format_type or self.config.export_format
        
        try:
            dashboard_data = self.update_dashboard()
            
            if format_type.lower() == 'json':
                export_data = json.dumps(dashboard_data, indent=2, default=str)
            elif format_type.lower() == 'csv':
                # Convert to CSV format (simplified)
                csv_lines = ['timestamp,component,metric,value,status']
                
                for component, metrics in dashboard_data.get('component_metrics', {}).items():
                    for metric_name, metric_data in metrics.items():
                        csv_lines.append(f"{dashboard_data['timestamp']},{component},{metric_name},"
                                       f"{metric_data.get('raw_value', 0)},{metric_data.get('status', 'unknown')}")
                
                export_data = '\n'.join(csv_lines)
            elif format_type.lower() == 'html':
                # Generate simple HTML report
                export_data = self._generate_html_report(dashboard_data)
            else:
                export_data = str(dashboard_data)
            
            self.export_count += 1
            return export_data
            
        except Exception as e:
            self.logger.error(f"Error exporting dashboard data: {e}")
            return ""
    
    def _generate_html_report(self, dashboard_data: Dict[str, Any]) -> str:
        """Generate HTML report from dashboard data"""
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Performance Dashboard Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { background-color: #f0f0f0; padding: 10px; border-radius: 5px; }
                .section { margin: 20px 0; }
                .metric { display: inline-block; margin: 10px; padding: 10px; border: 1px solid #ccc; border-radius: 5px; }
                .healthy { border-color: green; }
                .warning { border-color: orange; }
                .critical { border-color: red; }
                .alert { padding: 5px; margin: 5px 0; border-radius: 3px; }
                .alert-warning { background-color: #fff3cd; }
                .alert-critical { background-color: #f8d7da; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Performance Dashboard Report</h1>
                <p>Generated: {timestamp}</p>
            </div>
            
            <div class="section">
                <h2>System Overview</h2>
                <p>Overall Health: <strong>{overall_health}</strong></p>
                <p>Total Components: {total_components}</p>
                <p>Active Alerts: {active_alerts}</p>
            </div>
            
            <div class="section">
                <h2>Component Metrics</h2>
                {component_metrics_html}
            </div>
            
            <div class="section">
                <h2>Recent Alerts</h2>
                {alerts_html}
            </div>
        </body>
        </html>
        """
        
        # Generate component metrics HTML
        component_metrics_html = ""
        for component, metrics in dashboard_data.get('component_metrics', {}).items():
            component_metrics_html += f"<h3>{component}</h3>"
            for metric_name, metric_data in metrics.items():
                status_class = metric_data.get('status', 'healthy')
                component_metrics_html += f'<div class="metric {status_class}">'
                component_metrics_html += f"<strong>{metric_name}:</strong> {metric_data.get('value', 'N/A')}"
                component_metrics_html += f"</div>"
        
        # Generate alerts HTML
        alerts_html = ""
        for alert in dashboard_data.get('alerts_summary', {}).get('recent_alerts', []):
            alert_class = f"alert-{alert.get('level', 'info')}"
            alerts_html += f'<div class="alert {alert_class}">'
            alerts_html += f"<strong>{alert.get('component', 'Unknown')}:</strong> {alert.get('message', 'No message')}"
            alerts_html += f" <em>({alert.get('timestamp', 'Unknown time')})</em>"
            alerts_html += f"</div>"
        
        # Fill in the template
        system_overview = dashboard_data.get('system_overview', {})
        
        return html_template.format(
            timestamp=dashboard_data.get('timestamp', 'Unknown'),
            overall_health=system_overview.get('overall_health', 'Unknown'),
            total_components=system_overview.get('total_components', 0),
            active_alerts=system_overview.get('active_alerts', 0),
            component_metrics_html=component_metrics_html,
            alerts_html=alerts_html
        )
    
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get dashboard summary statistics"""
        return {
            'dashboard_active': self.is_active,
            'last_update': self.last_update.isoformat(),
            'update_count': self.update_count,
            'export_count': self.export_count,
            'connected_sources': {
                'monitor': self.monitor is not None,
                'optimizer': self.optimizer is not None,
                'auto_tuner': self.auto_tuner is not None
            },
            'configuration': {
                'refresh_interval': self.config.refresh_interval_seconds,
                'history_duration': self.config.history_duration_minutes,
                'export_format': self.config.export_format
            }
        }
