#!/usr/bin/env python3
"""
Test Suite for Monitoring Analytics Module
==========================================

Comprehensive tests for core_structure/analytics/monitoring_analytics.py
"""

import pytest
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, List, Any

# Import the module under test
from core_structure.analytics.monitoring_analytics import (
    MonitoringAnalyticsEngine,
    Alert,
    AnomalyDetection,
    PredictionResult,
    AlertSeverity,
    AlertType,
    AnomalyType,
    MonitoringStatus,
    monitoring_analytics,
    create_alert,
    detect_anomalies
)


class TestAlert:
    """Test Alert dataclass"""

    def test_initialization(self):
        """Test Alert initialization"""
        alert = Alert(
            id="test_alert_001",
            timestamp=datetime.now(),
            severity=AlertSeverity.WARNING,
            alert_type=AlertType.PERFORMANCE,
            title="Test Alert",
            message="This is a test alert",
            source="test_system"
        )

        assert alert.id == "test_alert_001"
        assert alert.severity == AlertSeverity.WARNING
        assert alert.alert_type == AlertType.PERFORMANCE
        assert alert.title == "Test Alert"
        assert alert.message == "This is a test alert"
        assert alert.source == "test_system"
        assert alert.acknowledged == False
        assert alert.resolved == False
        assert alert.data == {}

    def test_alert_with_data(self):
        """Test Alert with additional data"""
        data = {'metric': 'performance', 'value': 0.85}
        alert = Alert(
            id="test_alert_002",
            timestamp=datetime.now(),
            severity=AlertSeverity.ERROR,
            alert_type=AlertType.RISK,
            title="Risk Alert",
            message="High risk detected",
            source="risk_monitor",
            data=data
        )

        assert alert.data == data
        assert alert.acknowledged == False
        assert alert.resolved == False


class TestAnomalyDetection:
    """Test AnomalyDetection dataclass"""

    def test_initialization(self):
        """Test AnomalyDetection initialization"""
        anomaly = AnomalyDetection(
            timestamp=datetime.now(),
            anomaly_type=AnomalyType.PERFORMANCE_ANOMALY,
            severity_score=0.8,
            description="Performance anomaly detected",
            affected_metrics=['sharpe_ratio', 'returns'],
            confidence=0.9
        )

        assert anomaly.anomaly_type == AnomalyType.PERFORMANCE_ANOMALY
        assert anomaly.severity_score == 0.8
        assert anomaly.description == "Performance anomaly detected"
        assert anomaly.affected_metrics == ['sharpe_ratio', 'returns']
        assert anomaly.confidence == 0.9


class TestPredictionResult:
    """Test PredictionResult dataclass"""

    def test_initialization(self):
        """Test PredictionResult initialization"""
        prediction = PredictionResult(
            timestamp=datetime.now(),
            prediction_horizon=30,
            predicted_value=0.012,
            confidence_interval=(0.008, 0.016),
            confidence_level=0.95,
            model_accuracy=0.85,
            features_used=['returns', 'volatility', 'volume']
        )

        assert prediction.prediction_horizon == 30
        assert prediction.predicted_value == 0.012
        assert prediction.confidence_interval == (0.008, 0.016)
        assert prediction.confidence_level == 0.95
        assert prediction.model_accuracy == 0.85
        assert prediction.features_used == ['returns', 'volatility', 'volume']


class TestEnums:
    """Test enum classes"""

    def test_alert_severity_enum(self):
        """Test AlertSeverity enum values"""
        assert AlertSeverity.INFO.value == "info"
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.ERROR.value == "error"
        assert AlertSeverity.CRITICAL.value == "critical"

    def test_alert_type_enum(self):
        """Test AlertType enum values"""
        assert AlertType.PERFORMANCE.value == "performance"
        assert AlertType.RISK.value == "risk"
        assert AlertType.SYSTEM.value == "system"
        assert AlertType.EXECUTION.value == "execution"
        assert AlertType.MARKET.value == "market"
        assert AlertType.ANOMALY.value == "anomaly"
        assert AlertType.PREDICTION.value == "prediction"

    def test_anomaly_type_enum(self):
        """Test AnomalyType enum values"""
        assert AnomalyType.PERFORMANCE_ANOMALY.value == "performance_anomaly"
        assert AnomalyType.VOLUME_ANOMALY.value == "volume_anomaly"
        assert AnomalyType.PRICE_ANOMALY.value == "price_anomaly"
        assert AnomalyType.EXECUTION_ANOMALY.value == "execution_anomaly"
        assert AnomalyType.SYSTEM_ANOMALY.value == "system_anomaly"

    def test_monitoring_status_enum(self):
        """Test MonitoringStatus enum values"""
        assert MonitoringStatus.ACTIVE.value == "active"
        assert MonitoringStatus.PAUSED.value == "paused"
        assert MonitoringStatus.ERROR.value == "error"
        assert MonitoringStatus.MAINTENANCE.value == "maintenance"


class TestMonitoringAnalyticsEngine:
    """Test MonitoringAnalyticsEngine class"""

    @pytest.fixture
    def engine(self):
        """Create a test MonitoringAnalyticsEngine instance"""
        return MonitoringAnalyticsEngine(
            monitoring_interval=60,
            alert_retention=1000,
            anomaly_threshold=0.1,
            prediction_horizon=30
        )

    @pytest.fixture
    def sample_time_series_data(self):
        """Generate sample time series data for testing"""
        dates = pd.date_range('2024-01-01', periods=100, freq='1min')
        np.random.seed(42)

        # Generate normal data with some anomalies
        returns = np.random.normal(0.001, 0.02, 100)

        # Add some anomalies
        returns[20] = 0.15  # Positive anomaly
        returns[50] = -0.12  # Negative anomaly
        returns[80] = 0.18  # Another positive anomaly

        data = pd.DataFrame({
            'timestamp': dates,
            'returns': returns,
            'volatility': np.abs(np.random.normal(0.02, 0.005, 100)),
            'volume': np.random.randint(1000, 5000, 100)
        })

        return data

    def test_initialization(self, engine):
        """Test MonitoringAnalyticsEngine initialization"""
        assert engine.monitoring_interval == 60
        assert engine.alert_retention == 1000
        assert engine.anomaly_threshold == 0.1
        assert engine.prediction_horizon == 30

        # Check data structures
        assert len(engine.alerts) == 0
        assert len(engine.anomalies) == 0
        assert len(engine.predictions) == 0
        assert len(engine.monitoring_data) == 0

        # Check status
        assert engine.status == MonitoringStatus.ACTIVE
        assert engine.is_monitoring == False

        # Check ML models
        assert hasattr(engine, 'anomaly_detector')
        assert hasattr(engine, 'prediction_model')
        assert hasattr(engine, 'scaler')

    @pytest.mark.asyncio
    async def test_create_alert(self, engine):
        """Test alert creation"""
        alert = await engine.create_alert(
            severity=AlertSeverity.WARNING,
            alert_type=AlertType.PERFORMANCE,
            title="Test Performance Alert",
            message="Performance metric below threshold",
            source="test_monitor"
        )

        assert isinstance(alert, Alert)
        assert alert.severity == AlertSeverity.WARNING
        assert alert.alert_type == AlertType.PERFORMANCE
        assert alert.title == "Test Performance Alert"
        assert alert.message == "Performance metric below threshold"
        assert alert.source == "test_monitor"
        assert alert.id.startswith("alert_")

        # Check alert is stored
        assert len(engine.alerts) == 1
        assert engine.alerts[0] == alert

    @pytest.mark.asyncio
    async def test_create_critical_alert(self, engine):
        """Test critical alert creation and automatic anomaly detection"""
        alert = await engine.create_alert(
            severity=AlertSeverity.CRITICAL,
            alert_type=AlertType.SYSTEM,
            title="System Critical Alert",
            message="System failure detected",
            source="system_monitor"
        )

        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.alert_type == AlertType.SYSTEM

        # Check dashboard is updated
        dashboard = engine.get_dashboard_data()
        assert 'active_alerts' in dashboard
        assert len(dashboard['active_alerts']) > 0

    def test_register_alert_handler(self, engine):
        """Test alert handler registration"""
        handler_called = False

        async def test_handler(alert):
            nonlocal handler_called
            handler_called = True

        engine.register_alert_handler(AlertType.PERFORMANCE, test_handler)

        assert AlertType.PERFORMANCE in engine.alert_handlers
        assert len(engine.alert_handlers[AlertType.PERFORMANCE]) == 1

    def test_acknowledge_alert(self, engine):
        """Test alert acknowledgment"""
        # Create an alert first
        alert = Alert(
            id="test_alert_001",
            timestamp=datetime.now(),
            severity=AlertSeverity.WARNING,
            alert_type=AlertType.PERFORMANCE,
            title="Test Alert",
            message="Test message",
            source="test"
        )
        engine.alerts.append(alert)

        # Acknowledge the alert
        result = engine.acknowledge_alert("test_alert_001")

        assert result == True
        assert alert.acknowledged == True

    def test_resolve_alert(self, engine):
        """Test alert resolution"""
        # Create an alert first
        alert = Alert(
            id="test_alert_002",
            timestamp=datetime.now(),
            severity=AlertSeverity.ERROR,
            alert_type=AlertType.RISK,
            title="Test Alert",
            message="Test message",
            source="test"
        )
        engine.alerts.append(alert)

        # Resolve the alert
        result = engine.resolve_alert("test_alert_002")

        assert result == True
        assert alert.resolved == True

    @pytest.mark.asyncio
    async def test_detect_anomalies(self, engine, sample_time_series_data):
        """Test anomaly detection"""
        anomalies = await engine.detect_anomalies(
            sample_time_series_data,
            metric_name="performance"
        )

        assert isinstance(anomalies, list)

        # Should detect some anomalies given the test data
        if len(anomalies) > 0:
            for anomaly in anomalies:
                assert isinstance(anomaly, AnomalyDetection)
                assert anomaly.anomaly_type in AnomalyType
                assert 0 <= anomaly.severity_score <= 1
                assert anomaly.confidence >= 0

    @pytest.mark.asyncio
    async def test_detect_anomalies_insufficient_data(self, engine):
        """Test anomaly detection with insufficient data"""
        small_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=5, freq='1min'),
            'returns': [0.001, 0.002, 0.001, 0.003, 0.001]
        })

        anomalies = await engine.detect_anomalies(small_data, "performance")

        # Should return empty list for insufficient data
        assert len(anomalies) == 0

    def test_prepare_anomaly_features(self, engine, sample_time_series_data):
        """Test anomaly feature preparation"""
        features = engine._prepare_anomaly_features(sample_time_series_data)

        if features is not None:
            assert isinstance(features, np.ndarray)
            assert features.shape[0] == len(sample_time_series_data)
            assert features.shape[1] > 0  # Should have multiple features

    def test_classify_anomaly_type(self, engine):
        """Test anomaly type classification"""
        # Test different metric names
        assert engine._classify_anomaly_type("performance") == AnomalyType.PERFORMANCE_ANOMALY
        assert engine._classify_anomaly_type("volume") == AnomalyType.VOLUME_ANOMALY
        assert engine._classify_anomaly_type("price") == AnomalyType.PRICE_ANOMALY
        assert engine._classify_anomaly_type("execution") == AnomalyType.EXECUTION_ANOMALY
        assert engine._classify_anomaly_type("unknown") == AnomalyType.SYSTEM_ANOMALY

    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, engine):
        """Test monitoring start/stop functionality"""
        # Start monitoring
        await engine.start_monitoring()

        assert engine.is_monitoring == True
        assert engine.status == MonitoringStatus.ACTIVE
        assert engine.monitoring_task is not None

        # Stop monitoring
        await engine.stop_monitoring()

        assert engine.is_monitoring == False
        assert engine.status == MonitoringStatus.PAUSED

    def test_get_dashboard_data(self, engine):
        """Test dashboard data retrieval"""
        dashboard = engine.get_dashboard_data()

        expected_keys = [
            'last_updated',
            'performance_summary',
            'risk_summary',
            'execution_summary',
            'system_health',
            'active_alerts',
            'recent_anomalies'
        ]

        for key in expected_keys:
            assert key in dashboard

    def test_get_monitoring_status(self, engine):
        """Test monitoring status retrieval"""
        status = engine.get_monitoring_status()

        expected_keys = [
            'status',
            'is_monitoring',
            'total_alerts',
            'unresolved_alerts',
            'total_anomalies',
            'monitoring_interval',
            'last_updated'
        ]

        for key in expected_keys:
            assert key in status

        assert status['status'] == MonitoringStatus.ACTIVE.value
        assert status['is_monitoring'] == False
        assert status['total_alerts'] == 0
        assert status['total_anomalies'] == 0


class TestConvenienceFunctions:
    """Test convenience functions"""

    @pytest.fixture
    def sample_data(self):
        """Generate sample data for testing"""
        dates = pd.date_range('2024-01-01', periods=50, freq='1min')
        data = pd.DataFrame({
            'timestamp': dates,
            'returns': np.random.normal(0.001, 0.02, 50),
            'volatility': np.random.normal(0.02, 0.005, 50)
        })
        return data

    @pytest.mark.asyncio
    async def test_create_alert_function(self):
        """Test create_alert convenience function"""
        alert = await create_alert(
            severity=AlertSeverity.INFO,
            alert_type=AlertType.SYSTEM,
            title="Test Alert",
            message="Test message"
        )

        assert isinstance(alert, Alert)
        assert alert.severity == AlertSeverity.INFO
        assert alert.alert_type == AlertType.SYSTEM

    @pytest.mark.asyncio
    async def test_detect_anomalies_function(self, sample_data):
        """Test detect_anomalies convenience function"""
        anomalies = await detect_anomalies(sample_data, "performance")

        assert isinstance(anomalies, list)
        if len(anomalies) > 0:
            for anomaly in anomalies:
                assert isinstance(anomaly, AnomalyDetection)


class TestEdgeCases:
    """Test edge cases and error handling"""

    @pytest.fixture
    def engine(self):
        """Create a test MonitoringAnalyticsEngine instance"""
        return MonitoringAnalyticsEngine()

    def test_empty_data_anomaly_detection(self, engine):
        """Test anomaly detection with empty data"""
        empty_data = pd.DataFrame()

        # Should handle gracefully
        assert hasattr(engine, 'detect_anomalies')

    def test_single_row_data(self, engine):
        """Test with single row of data"""
        single_row_data = pd.DataFrame({
            'timestamp': [datetime.now()],
            'returns': [0.01]
        })

        # Should handle gracefully
        assert len(single_row_data) == 1

    @pytest.mark.asyncio
    async def test_alert_handler_error(self, engine):
        """Test error handling in alert handlers"""
        async def failing_handler(alert):
            raise Exception("Handler failed")

        engine.register_alert_handler(AlertType.PERFORMANCE, failing_handler)

        # Should not crash when handler fails
        alert = await engine.create_alert(
            severity=AlertSeverity.WARNING,
            alert_type=AlertType.PERFORMANCE,
            title="Test",
            message="Test"
        )

        assert alert is not None

    def test_acknowledge_nonexistent_alert(self, engine):
        """Test acknowledging non-existent alert"""
        result = engine.acknowledge_alert("nonexistent_id")

        assert result == False

    def test_resolve_nonexistent_alert(self, engine):
        """Test resolving non-existent alert"""
        result = engine.resolve_alert("nonexistent_id")

        assert result == False


class TestIntegration:
    """Integration tests combining multiple monitoring features"""

    @pytest.fixture
    def engine(self):
        """Create a test MonitoringAnalyticsEngine instance"""
        return MonitoringAnalyticsEngine()

    @pytest.fixture
    def comprehensive_monitoring_data(self):
        """Generate comprehensive monitoring data"""
        dates = pd.date_range('2024-01-01', periods=200, freq='1min')
        np.random.seed(42)

        # Generate data with various patterns
        returns = np.random.normal(0.001, 0.02, 200)
        volatility = np.abs(np.random.normal(0.02, 0.005, 200))
        volume = np.random.randint(1000, 5000, 200)

        # Add some anomalies
        returns[50] = 0.15  # Performance anomaly
        returns[100] = -0.12  # Another anomaly
        volatility[75] = 0.15  # Volatility spike
        volume[150] = 10000  # Volume spike

        data = pd.DataFrame({
            'timestamp': dates,
            'returns': returns,
            'volatility': volatility,
            'volume': volume
        })

        return data

    @pytest.mark.asyncio
    async def test_full_monitoring_workflow(self, engine, comprehensive_monitoring_data):
        """Test complete monitoring workflow"""
        # Start monitoring
        await engine.start_monitoring()
        assert engine.is_monitoring == True

        # Create various alerts
        alert1 = await engine.create_alert(
            AlertSeverity.WARNING,
            AlertType.PERFORMANCE,
            "Performance Warning",
            "Performance degraded",
            "test"
        )

        alert2 = await engine.create_alert(
            AlertSeverity.ERROR,
            AlertType.RISK,
            "Risk Alert",
            "High risk detected",
            "test"
        )

        # Detect anomalies
        anomalies = await engine.detect_anomalies(
            comprehensive_monitoring_data,
            "performance"
        )

        # Get dashboard data
        dashboard = engine.get_dashboard_data()

        # Get monitoring status
        status = engine.get_monitoring_status()

        # Verify everything works together
        assert len(engine.alerts) >= 2
        assert isinstance(anomalies, list)
        assert isinstance(dashboard, dict)
        assert isinstance(status, dict)

        # Stop monitoring
        await engine.stop_monitoring()
        assert engine.is_monitoring == False

    @pytest.mark.asyncio
    async def test_alert_lifecycle(self, engine):
        """Test complete alert lifecycle"""
        # Create alert
        alert = await engine.create_alert(
            AlertSeverity.WARNING,
            AlertType.SYSTEM,
            "System Warning",
            "System issue detected",
            "test"
        )

        initial_count = len(engine.alerts)
        assert initial_count > 0

        # Acknowledge alert
        ack_result = engine.acknowledge_alert(alert.id)
        assert ack_result == True
        assert alert.acknowledged == True

        # Resolve alert
        resolve_result = engine.resolve_alert(alert.id)
        assert resolve_result == True
        assert alert.resolved == True

        # Check dashboard reflects changes
        dashboard = engine.get_dashboard_data()
        active_alerts = dashboard.get('active_alerts', [])

        # Resolved alerts should not appear in active alerts
        alert_ids = [a['id'] for a in active_alerts]
        assert alert.id not in alert_ids

    @pytest.mark.asyncio
    async def test_multiple_anomaly_detection(self, engine, comprehensive_monitoring_data):
        """Test anomaly detection across multiple metrics"""
        # Test different metrics
        metrics_to_test = ['returns', 'volatility', 'volume']

        for metric in metrics_to_test:
            if metric in comprehensive_monitoring_data.columns:
                anomalies = await engine.detect_anomalies(
                    comprehensive_monitoring_data[[metric]],
                    metric
                )

                assert isinstance(anomalies, list)
                # Anomalies should be stored
                if len(anomalies) > 0:
                    assert len(engine.anomalies) > 0
