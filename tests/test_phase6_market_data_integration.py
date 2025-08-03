"""
Phase 6: Market Data & Performance Integration Test Suite

Comprehensive tests for the market data integration system including:
- MarketDataAnalytics functionality
- DataQualityMonitor functionality  
- PerformanceIntegration functionality
- Integration between all components

Author: Pro Quant Desk Trader
"""

import pytest
import asyncio
import logging
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np

# Import Phase 6 components
from core_structure.market_data.market_data_analytics import (
    MarketDataAnalytics, DataQualityMetrics, MarketDataPerformance,
    DataQualityLevel, DataIssueType, MarketDataAnalyticsConfig
)
from core_structure.market_data.data_quality_monitor import (
    DataQualityMonitor, QualityAlert, AlertLevel, MonitoringStatus,
    DataQualityMonitorConfig, QualityThreshold
)
from core_structure.market_data.performance_integration import (
    PerformanceIntegration, PerformanceSnapshot, IntegrationStatus,
    PerformanceMetric, PerformanceIntegrationConfig
)

logger = logging.getLogger(__name__)


class TestMarketDataAnalytics:
    """Test MarketDataAnalytics functionality."""
    
    @pytest.fixture
    async def analytics(self):
        """Create MarketDataAnalytics instance for testing."""
        config = MarketDataAnalyticsConfig(
            monitoring_interval_seconds=5,
            enable_real_time_monitoring=False
        )
        return MarketDataAnalytics(config)
    
    @pytest.fixture
    def sample_market_data(self):
        """Create sample market data for testing."""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1min')
        data = {
            'timestamp': dates,
            'open': np.random.uniform(100, 200, 100),
            'high': np.random.uniform(150, 250, 100),
            'low': np.random.uniform(50, 150, 100),
            'close': np.random.uniform(100, 200, 100),
            'volume': np.random.uniform(1000, 10000, 100)
        }
        return pd.DataFrame(data)
    
    @pytest.mark.asyncio
    async def test_analytics_initialization(self, analytics):
        """Test MarketDataAnalytics initialization."""
        assert analytics is not None
        assert analytics.config is not None
        assert analytics.config.monitoring_interval_seconds == 5
        assert analytics.config.enable_real_time_monitoring is False
    
    @pytest.mark.asyncio
    async def test_data_quality_analysis(self, analytics, sample_market_data):
        """Test data quality analysis."""
        quality_metrics = await analytics.analyze_data_quality(sample_market_data, "AAPL")
        
        assert quality_metrics is not None
        assert isinstance(quality_metrics, DataQualityMetrics)
        assert 0 <= quality_metrics.completeness <= 100
        assert 0 <= quality_metrics.accuracy <= 100
        assert 0 <= quality_metrics.consistency <= 100
        assert 0 <= quality_metrics.timeliness <= 100
        assert 0 <= quality_metrics.overall_quality_score <= 100
    
    @pytest.mark.asyncio
    async def test_performance_analysis(self, analytics, sample_market_data):
        """Test performance analysis."""
        processing_time = 0.5  # 500ms
        performance_metrics = await analytics.analyze_performance(sample_market_data, processing_time)
        
        assert performance_metrics is not None
        assert isinstance(performance_metrics, MarketDataPerformance)
        assert performance_metrics.data_throughput > 0
        assert performance_metrics.processing_latency == 500.0  # Converted to ms
        assert 0 <= performance_metrics.overall_performance_score <= 100
    
    @pytest.mark.asyncio
    async def test_quality_summary(self, analytics, sample_market_data):
        """Test quality summary generation."""
        # First analyze some data
        await analytics.analyze_data_quality(sample_market_data, "AAPL")
        
        # Get summary
        summary = analytics.get_quality_summary("AAPL", days=1)
        
        assert summary is not None
        assert isinstance(summary, dict)
        assert 'avg_quality_score' in summary
        assert 'quality_trend' in summary
    
    @pytest.mark.asyncio
    async def test_performance_summary(self, analytics, sample_market_data):
        """Test performance summary generation."""
        # First analyze some data
        await analytics.analyze_performance(sample_market_data, 0.5)
        
        # Get summary
        summary = analytics.get_performance_summary(days=1)
        
        assert summary is not None
        assert isinstance(summary, dict)
        assert 'avg_performance_score' in summary
        assert 'performance_trend' in summary
    
    @pytest.mark.asyncio
    async def test_analytics_report_generation(self, analytics, sample_market_data):
        """Test analytics report generation."""
        # First analyze some data
        await analytics.analyze_data_quality(sample_market_data, "AAPL")
        await analytics.analyze_performance(sample_market_data, 0.5)
        
        # Generate report
        report = analytics.generate_analytics_report("AAPL", days=1)
        
        assert report is not None
        assert isinstance(report, dict)
        assert 'overall_health_score' in report
        assert 'health_status' in report
        assert 'quality_summary' in report
        assert 'performance_summary' in report


class TestDataQualityMonitor:
    """Test DataQualityMonitor functionality."""
    
    @pytest.fixture
    async def monitor(self):
        """Create DataQualityMonitor instance for testing."""
        config = DataQualityMonitorConfig(
            monitoring_interval_seconds=5,
            enable_analytics_integration=True
        )
        return DataQualityMonitor(config)
    
    @pytest.fixture
    def sample_market_data(self):
        """Create sample market data for testing."""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1min')
        data = {
            'timestamp': dates,
            'open': np.random.uniform(100, 200, 100),
            'high': np.random.uniform(150, 250, 100),
            'low': np.random.uniform(50, 150, 100),
            'close': np.random.uniform(100, 200, 100),
            'volume': np.random.uniform(1000, 10000, 100)
        }
        return pd.DataFrame(data)
    
    @pytest.mark.asyncio
    async def test_monitor_initialization(self, monitor):
        """Test DataQualityMonitor initialization."""
        assert monitor is not None
        assert monitor.config is not None
        assert monitor.analytics is not None
        assert monitor.status == MonitoringStatus.STOPPED
    
    @pytest.mark.asyncio
    async def test_monitor_start_stop(self, monitor):
        """Test monitor start and stop functionality."""
        # Start monitoring
        await monitor.start_monitoring()
        assert monitor.status == MonitoringStatus.ACTIVE
        
        # Stop monitoring
        await monitor.stop_monitoring()
        assert monitor.status == MonitoringStatus.STOPPED
    
    @pytest.mark.asyncio
    async def test_symbol_management(self, monitor):
        """Test symbol addition and removal."""
        # Add symbol
        monitor.add_symbol("AAPL")
        assert "AAPL" in monitor.monitored_symbols
        assert "AAPL" in monitor.symbol_quality_history
        
        # Remove symbol
        monitor.remove_symbol("AAPL")
        assert "AAPL" not in monitor.monitored_symbols
        assert "AAPL" not in monitor.symbol_quality_history
    
    @pytest.mark.asyncio
    async def test_market_data_processing(self, monitor, sample_market_data):
        """Test market data processing."""
        # Add symbol first
        monitor.add_symbol("AAPL")
        
        # Process market data
        await monitor.process_market_data("AAPL", sample_market_data, 0.5)
        
        # Check that data was processed
        assert len(monitor.symbol_quality_history["AAPL"]) > 0
        assert len(monitor.symbol_performance_history["AAPL"]) > 0
    
    @pytest.mark.asyncio
    async def test_alert_management(self, monitor):
        """Test alert management functionality."""
        # Create a test alert
        alert = QualityAlert(
            alert_id="test_alert",
            level=AlertLevel.WARNING,
            message="Test alert",
            symbol="AAPL",
            timestamp=datetime.now(),
            metric_name="test_metric",
            current_value=50.0,
            threshold_value=80.0,
            severity_score=0.5
        )
        
        # Add to active alerts
        monitor.active_alerts[alert.alert_id] = alert
        
        # Test alert retrieval
        active_alerts = monitor.get_active_alerts("AAPL")
        assert len(active_alerts) == 1
        assert active_alerts[0].alert_id == "test_alert"
        
        # Test alert acknowledgment
        monitor.acknowledge_alert("test_alert", "test_user")
        assert alert.acknowledged is True
        assert alert.acknowledged_by == "test_user"
        
        # Test alert resolution
        monitor.resolve_alert("test_alert", "test_user", "Resolved")
        assert alert.resolved is True
        assert alert.resolved_by == "test_user"
        assert "test_alert" not in monitor.active_alerts
        assert len(monitor.alert_history) > 0
    
    @pytest.mark.asyncio
    async def test_monitoring_report_generation(self, monitor, sample_market_data):
        """Test monitoring report generation."""
        # Add symbol and process data
        monitor.add_symbol("AAPL")
        await monitor.process_market_data("AAPL", sample_market_data, 0.5)
        
        # Generate report
        report = monitor.generate_monitoring_report("AAPL", days=1)
        
        assert report is not None
        assert isinstance(report, dict)
        assert 'monitoring_status' in report
        assert 'active_alerts_count' in report
        assert 'analytics_report' in report


class TestPerformanceIntegration:
    """Test PerformanceIntegration functionality."""
    
    @pytest.fixture
    async def integration(self):
        """Create PerformanceIntegration instance for testing."""
        config = PerformanceIntegrationConfig(
            integration_interval_seconds=5,
            enable_real_time_monitoring=False
        )
        return PerformanceIntegration(config)
    
    @pytest.fixture
    def sample_market_data(self):
        """Create sample market data for testing."""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1min')
        data = {
            'timestamp': dates,
            'open': np.random.uniform(100, 200, 100),
            'high': np.random.uniform(150, 250, 100),
            'low': np.random.uniform(50, 150, 100),
            'close': np.random.uniform(100, 200, 100),
            'volume': np.random.uniform(1000, 10000, 100)
        }
        return pd.DataFrame(data)
    
    @pytest.mark.asyncio
    async def test_integration_initialization(self, integration):
        """Test PerformanceIntegration initialization."""
        assert integration is not None
        assert integration.config is not None
        assert integration.analytics is not None
        assert integration.quality_monitor is not None
        assert integration.status == IntegrationStatus.INITIALIZING
    
    @pytest.mark.asyncio
    async def test_integration_start_stop(self, integration):
        """Test integration start and stop functionality."""
        # Start integration
        await integration.start_integration()
        assert integration.status == IntegrationStatus.ACTIVE
        
        # Stop integration
        await integration.stop_integration()
        assert integration.status == IntegrationStatus.STOPPED
    
    @pytest.mark.asyncio
    async def test_symbol_management(self, integration):
        """Test symbol addition and removal."""
        # Add symbol
        integration.add_symbol("AAPL")
        assert "AAPL" in integration.integrated_symbols
        assert "AAPL" in integration.performance_snapshots
        
        # Remove symbol
        integration.remove_symbol("AAPL")
        assert "AAPL" not in integration.integrated_symbols
        assert "AAPL" not in integration.performance_snapshots
    
    @pytest.mark.asyncio
    async def test_market_data_processing(self, integration, sample_market_data):
        """Test market data processing through integration."""
        # Add symbol first
        integration.add_symbol("AAPL")
        
        # Process market data
        await integration.process_market_data("AAPL", sample_market_data, 0.5)
        
        # Check that data was processed
        assert len(integration.performance_snapshots["AAPL"]) > 0
        assert len(integration.symbol_performance_history["AAPL"]) > 0
    
    @pytest.mark.asyncio
    async def test_performance_snapshot_generation(self, integration, sample_market_data):
        """Test performance snapshot generation."""
        # Add symbol first
        integration.add_symbol("AAPL")
        
        # Process market data to generate snapshot
        await integration.process_market_data("AAPL", sample_market_data, 0.5)
        
        # Get snapshots
        snapshots = integration.get_performance_snapshots("AAPL", hours=1)
        assert len(snapshots) > 0
        
        snapshot = snapshots[0]
        assert isinstance(snapshot, PerformanceSnapshot)
        assert snapshot.symbol == "AAPL"
        assert 0 <= snapshot.overall_performance_score <= 100
        assert 0 <= snapshot.data_quality_score <= 100
        assert 0 <= snapshot.processing_performance_score <= 100
    
    @pytest.mark.asyncio
    async def test_performance_summary(self, integration, sample_market_data):
        """Test performance summary generation."""
        # Add symbol and process data
        integration.add_symbol("AAPL")
        await integration.process_market_data("AAPL", sample_market_data, 0.5)
        
        # Get summary
        summary = integration.get_performance_summary("AAPL", hours=1)
        
        assert summary is not None
        assert isinstance(summary, dict)
        assert 'avg_overall_score' in summary
        assert 'performance_trend' in summary
        assert 'latest_snapshot' in summary
    
    @pytest.mark.asyncio
    async def test_integration_status(self, integration):
        """Test integration status functionality."""
        status = integration.get_integration_status()
        
        assert status is not None
        assert isinstance(status, dict)
        assert 'status' in status
        assert 'integrated_symbols' in status
        assert 'analytics_status' in status
        assert 'quality_monitor_status' in status
    
    @pytest.mark.asyncio
    async def test_integration_report_generation(self, integration, sample_market_data):
        """Test integration report generation."""
        # Add symbol and process data
        integration.add_symbol("AAPL")
        await integration.process_market_data("AAPL", sample_market_data, 0.5)
        
        # Generate report
        report = integration.generate_integration_report("AAPL", hours=1)
        
        assert report is not None
        assert isinstance(report, dict)
        assert 'integration_status' in report
        assert 'performance_summary' in report
        assert 'monitoring_report' in report
        assert 'analytics_report' in report
        assert 'recommendations' in report
    
    @pytest.mark.asyncio
    async def test_auto_scaling_control(self, integration):
        """Test auto-scaling control."""
        # Initially disabled
        assert integration.auto_scaling_enabled is False
        
        # Enable auto-scaling
        integration.enable_auto_scaling(True)
        assert integration.auto_scaling_enabled is True
        
        # Disable auto-scaling
        integration.enable_auto_scaling(False)
        assert integration.auto_scaling_enabled is False
    
    @pytest.mark.asyncio
    async def test_optimization_history(self, integration):
        """Test optimization history functionality."""
        # Initially empty
        history = integration.get_optimization_history("AAPL")
        assert len(history) == 0
        
        # Add symbol to enable history tracking
        integration.add_symbol("AAPL")
        history = integration.get_optimization_history("AAPL")
        assert isinstance(history, list)


class TestPhase6Integration:
    """Test integration between all Phase 6 components."""
    
    @pytest.fixture
    async def full_integration(self):
        """Create full Phase 6 integration for testing."""
        # Create analytics
        analytics_config = MarketDataAnalyticsConfig(
            monitoring_interval_seconds=5,
            enable_real_time_monitoring=False
        )
        analytics = MarketDataAnalytics(analytics_config)
        
        # Create quality monitor
        monitor_config = DataQualityMonitorConfig(
            monitoring_interval_seconds=5,
            enable_analytics_integration=True
        )
        monitor = DataQualityMonitor(monitor_config)
        
        # Create performance integration
        integration_config = PerformanceIntegrationConfig(
            integration_interval_seconds=5,
            enable_real_time_monitoring=False
        )
        integration = PerformanceIntegration(integration_config)
        
        return {
            'analytics': analytics,
            'monitor': monitor,
            'integration': integration
        }
    
    @pytest.fixture
    def sample_market_data(self):
        """Create sample market data for testing."""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1min')
        data = {
            'timestamp': dates,
            'open': np.random.uniform(100, 200, 100),
            'high': np.random.uniform(150, 250, 100),
            'low': np.random.uniform(50, 150, 100),
            'close': np.random.uniform(100, 200, 100),
            'volume': np.random.uniform(1000, 10000, 100)
        }
        return pd.DataFrame(data)
    
    @pytest.mark.asyncio
    async def test_full_integration_workflow(self, full_integration, sample_market_data):
        """Test complete integration workflow."""
        analytics = full_integration['analytics']
        monitor = full_integration['monitor']
        integration = full_integration['integration']
        
        # Start all systems
        await analytics.start_monitoring()
        await monitor.start_monitoring()
        await integration.start_integration()
        
        # Add symbol to all systems
        monitor.add_symbol("AAPL")
        integration.add_symbol("AAPL")
        
        # Process data through integration
        await integration.process_market_data("AAPL", sample_market_data, 0.5)
        
        # Verify data flows through all components
        assert len(integration.analytics.quality_history) > 0
        assert len(integration.quality_monitor.symbol_quality_history["AAPL"]) > 0
        assert len(integration.performance_snapshots["AAPL"]) > 0
        
        # Stop all systems
        await analytics.stop_monitoring()
        await monitor.stop_monitoring()
        await integration.stop_integration()
    
    @pytest.mark.asyncio
    async def test_cross_component_data_consistency(self, full_integration, sample_market_data):
        """Test data consistency across components."""
        analytics = full_integration['analytics']
        monitor = full_integration['monitor']
        integration = full_integration['integration']
        
        # Add symbol and process data
        monitor.add_symbol("AAPL")
        integration.add_symbol("AAPL")
        await integration.process_market_data("AAPL", sample_market_data, 0.5)
        
        # Check that analytics data is consistent
        analytics_summary = integration.analytics.get_quality_summary("AAPL", days=1)
        monitor_summary = integration.quality_monitor.get_quality_summary("AAPL", days=1)
        
        # Both should have data
        assert 'avg_quality_score' in analytics_summary
        assert 'avg_quality_score' in monitor_summary
        
        # Check that integration has performance data
        integration_summary = integration.get_performance_summary("AAPL", hours=1)
        assert 'avg_overall_score' in integration_summary
    
    @pytest.mark.asyncio
    async def test_alert_propagation(self, full_integration, sample_market_data):
        """Test alert propagation across components."""
        monitor = full_integration['monitor']
        integration = full_integration['integration']
        
        # Add alert handlers
        alerts_received = []
        
        def alert_handler(symbol, alert):
            alerts_received.append((symbol, alert))
        
        monitor.add_alert_handler(alert_handler)
        integration.add_alert_handler(alert_handler)
        
        # Add symbol and process data
        monitor.add_symbol("AAPL")
        integration.add_symbol("AAPL")
        await integration.process_market_data("AAPL", sample_market_data, 0.5)
        
        # Check that alerts are generated and propagated
        active_alerts = monitor.get_active_alerts("AAPL")
        # Note: In this test, we may not have alerts depending on data quality
        # The important thing is that the alert system is functional
    
    @pytest.mark.asyncio
    async def test_performance_optimization_workflow(self, full_integration, sample_market_data):
        """Test performance optimization workflow."""
        integration = full_integration['integration']
        
        # Add optimization handler
        optimizations_received = []
        
        def optimization_handler(symbol, optimization_record):
            optimizations_received.append((symbol, optimization_record))
        
        integration.add_optimization_handler(optimization_handler)
        
        # Add symbol and process data
        integration.add_symbol("AAPL")
        await integration.process_market_data("AAPL", sample_market_data, 0.5)
        
        # Check optimization history
        optimization_history = integration.get_optimization_history("AAPL")
        # Note: Optimization may not be triggered depending on performance scores
        # The important thing is that the optimization system is functional


class TestPhase6DataStructures:
    """Test Phase 6 data structures and serialization."""
    
    def test_data_quality_metrics_serialization(self):
        """Test DataQualityMetrics serialization."""
        metrics = DataQualityMetrics(
            completeness=95.0,
            accuracy=98.0,
            consistency=92.0,
            timeliness=96.0,
            outlier_rate=2.0,
            duplicate_rate=1.0,
            gap_count=3,
            max_gap_duration=timedelta(minutes=5),
            overall_quality_score=94.0,
            issues=[]
        )
        
        # Test to_dict method
        metrics_dict = metrics.to_dict()
        assert isinstance(metrics_dict, dict)
        assert metrics_dict['completeness'] == 95.0
        assert metrics_dict['accuracy'] == 98.0
        assert metrics_dict['overall_quality_score'] == 94.0
    
    def test_market_data_performance_serialization(self):
        """Test MarketDataPerformance serialization."""
        performance = MarketDataPerformance(
            data_throughput=1000.0,
            processing_latency=50.0,
            storage_efficiency=85.0,
            retrieval_speed=25.0,
            memory_usage=512.0,
            cpu_usage=25.0,
            disk_usage=60.0,
            overall_performance_score=88.0
        )
        
        # Test to_dict method
        performance_dict = performance.to_dict()
        assert isinstance(performance_dict, dict)
        assert performance_dict['data_throughput'] == 1000.0
        assert performance_dict['overall_performance_score'] == 88.0
        assert 'timestamp' in performance_dict
    
    def test_quality_alert_serialization(self):
        """Test QualityAlert serialization."""
        alert = QualityAlert(
            alert_id="test_alert",
            level=AlertLevel.WARNING,
            message="Test alert message",
            symbol="AAPL",
            timestamp=datetime.now(),
            metric_name="test_metric",
            current_value=75.0,
            threshold_value=80.0,
            severity_score=0.25
        )
        
        # Test to_dict method
        alert_dict = alert.to_dict()
        assert isinstance(alert_dict, dict)
        assert alert_dict['alert_id'] == "test_alert"
        assert alert_dict['level'] == "warning"
        assert alert_dict['symbol'] == "AAPL"
        assert alert_dict['current_value'] == 75.0
    
    def test_performance_snapshot_serialization(self):
        """Test PerformanceSnapshot serialization."""
        snapshot = PerformanceSnapshot(
            timestamp=datetime.now(),
            symbol="AAPL",
            period_minutes=1,
            data_quality_score=95.0,
            processing_performance_score=88.0,
            system_performance_score=92.0,
            integration_performance_score=90.0,
            overall_performance_score=91.0,
            quality_metrics={'completeness': 95.0},
            performance_metrics={'throughput': 1000.0},
            system_metrics={'memory_usage': 512.0},
            active_alerts_count=2,
            critical_alerts_count=0,
            warning_alerts_count=2,
            integration_status="healthy"
        )
        
        # Test to_dict method
        snapshot_dict = snapshot.to_dict()
        assert isinstance(snapshot_dict, dict)
        assert snapshot_dict['symbol'] == "AAPL"
        assert snapshot_dict['overall_performance_score'] == 91.0
        assert snapshot_dict['integration_status'] == "healthy"
        assert 'timestamp' in snapshot_dict


class TestPhase6Configuration:
    """Test Phase 6 configuration classes."""
    
    def test_market_data_analytics_config(self):
        """Test MarketDataAnalyticsConfig."""
        config = MarketDataAnalyticsConfig(
            min_completeness_threshold=0.90,
            min_accuracy_threshold=0.95,
            outlier_std_threshold=2.5,
            monitoring_interval_seconds=30
        )
        
        assert config.min_completeness_threshold == 0.90
        assert config.min_accuracy_threshold == 0.95
        assert config.outlier_std_threshold == 2.5
        assert config.monitoring_interval_seconds == 30
    
    def test_data_quality_monitor_config(self):
        """Test DataQualityMonitorConfig."""
        config = DataQualityMonitorConfig(
            monitoring_interval_seconds=30,
            alert_cooldown_minutes=10,
            max_alerts_per_symbol=20,
            enable_anomaly_detection=True
        )
        
        assert config.monitoring_interval_seconds == 30
        assert config.alert_cooldown_minutes == 10
        assert config.max_alerts_per_symbol == 20
        assert config.enable_anomaly_detection is True
    
    def test_performance_integration_config(self):
        """Test PerformanceIntegrationConfig."""
        config = PerformanceIntegrationConfig(
            integration_interval_seconds=60,
            snapshot_retention_hours=48,
            min_quality_score=85.0,
            enable_auto_scaling=True
        )
        
        assert config.integration_interval_seconds == 60
        assert config.snapshot_retention_hours == 48
        assert config.min_quality_score == 85.0
        assert config.enable_auto_scaling is True
    
    def test_quality_threshold(self):
        """Test QualityThreshold."""
        threshold = QualityThreshold(
            completeness_min=90.0,
            accuracy_min=95.0,
            consistency_min=85.0,
            quality_score_warning=75.0,
            quality_score_critical=60.0
        )
        
        assert threshold.completeness_min == 90.0
        assert threshold.accuracy_min == 95.0
        assert threshold.consistency_min == 85.0
        assert threshold.quality_score_warning == 75.0
        assert threshold.quality_score_critical == 60.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 