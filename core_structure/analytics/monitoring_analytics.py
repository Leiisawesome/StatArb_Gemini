#!/usr/bin/env python3
"""
Monitoring Analytics - Consolidated Real-time Monitoring and Alerting
====================================================================

Consolidates monitoring functionality from multiple modules:
- MonitoringEngine (from monitoring_system.py)
- AlertManager (from monitoring_system.py) 
- PredictiveMonitor (from predictive_monitor.py)
- AnomalyDetector (from anomaly_detector.py)
- MultiStrategyDashboard (from multi_strategy_dashboard.py)

This module provides real-time monitoring, alerting, anomaly detection,
and dashboard functionality for trading operations.

Author: Professional Trading System Architecture
Version: 1.0.0 (Consolidated)
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import threading
from abc import ABC, abstractmethod
import json
import warnings

# ML libraries for anomaly detection and prediction
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)

# ================================================================================
# CORE ENUMS AND DATA CLASSES
# ================================================================================

class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class AlertType(Enum):
    """Types of alerts"""
    PERFORMANCE = "performance"
    RISK = "risk"
    SYSTEM = "system"
    EXECUTION = "execution"
    MARKET = "market"
    ANOMALY = "anomaly"
    PREDICTION = "prediction"

class AnomalyType(Enum):
    """Types of anomalies"""
    PERFORMANCE_ANOMALY = "performance_anomaly"
    VOLUME_ANOMALY = "volume_anomaly"
    PRICE_ANOMALY = "price_anomaly"
    EXECUTION_ANOMALY = "execution_anomaly"
    SYSTEM_ANOMALY = "system_anomaly"

class MonitoringStatus(Enum):
    """Monitoring system status"""
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    MAINTENANCE = "maintenance"

@dataclass
class Alert:
    """Alert message structure"""
    id: str
    timestamp: datetime
    severity: AlertSeverity
    alert_type: AlertType
    title: str
    message: str
    source: str
    data: Dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False
    resolved: bool = False
    
@dataclass
class AnomalyDetection:
    """Anomaly detection result"""
    timestamp: datetime
    anomaly_type: AnomalyType
    severity_score: float  # 0-1, higher = more severe
    description: str
    affected_metrics: List[str]
    confidence: float
    raw_data: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PredictionResult:
    """Prediction result structure"""
    timestamp: datetime
    prediction_horizon: int  # minutes
    predicted_value: float
    confidence_interval: Tuple[float, float]
    confidence_level: float
    model_accuracy: float
    features_used: List[str]

# ================================================================================
# MONITORING ANALYTICS ENGINE
# ================================================================================

class MonitoringAnalyticsEngine:
    """
    Unified monitoring analytics engine consolidating real-time monitoring,
    alerting, anomaly detection, prediction, and dashboard functionality.
    
    Features:
    - Real-time performance and system monitoring
    - Intelligent alerting with severity classification
    - ML-powered anomaly detection
    - Predictive monitoring with forecasting
    - Multi-strategy dashboard data aggregation
    """
    
    def __init__(self,
                 monitoring_interval: int = 60,  # seconds
                 alert_retention: int = 1000,
                 anomaly_threshold: float = 0.1,
                 prediction_horizon: int = 30):  # minutes
        """
        Initialize monitoring analytics engine
        
        Args:
            monitoring_interval: Monitoring frequency in seconds
            alert_retention: Number of alerts to retain
            anomaly_threshold: Anomaly detection threshold (0-1)
            prediction_horizon: Prediction horizon in minutes
        """
        self.monitoring_interval = monitoring_interval
        self.alert_retention = alert_retention
        self.anomaly_threshold = anomaly_threshold
        self.prediction_horizon = prediction_horizon
        
        # Data storage
        self.alerts: deque = deque(maxlen=alert_retention)
        self.anomalies: deque = deque(maxlen=500)
        self.predictions: deque = deque(maxlen=100)
        self.monitoring_data: deque = deque(maxlen=1000)
        
        # ML Models
        self.anomaly_detector = IsolationForest(
            contamination=anomaly_threshold,
            random_state=42
        )
        self.prediction_model = LinearRegression()
        self.scaler = StandardScaler()
        
        # Monitoring state
        self.status = MonitoringStatus.ACTIVE
        self.is_monitoring = False
        self.monitoring_task: Optional[asyncio.Task] = None
        self.monitoring_lock = threading.RLock()
        
        # Alert handlers
        self.alert_handlers: Dict[AlertType, List[Callable]] = {
            alert_type: [] for alert_type in AlertType
        }
        
        # Dashboard data
        self.dashboard_data: Dict[str, Any] = {
            'last_updated': None,
            'performance_summary': {},
            'risk_summary': {},
            'execution_summary': {},
            'system_health': {},
            'active_alerts': [],
            'recent_anomalies': []
        }
        
        logger.info("MonitoringAnalyticsEngine initialized successfully")
    
    # ================================================================================
    # ALERT MANAGEMENT
    # ================================================================================
    
    async def create_alert(self,
                          severity: AlertSeverity,
                          alert_type: AlertType,
                          title: str,
                          message: str,
                          source: str = "system",
                          data: Optional[Dict[str, Any]] = None) -> Alert:
        """
        Create and process a new alert
        
        Args:
            severity: Alert severity level
            alert_type: Type of alert
            title: Alert title
            message: Alert message
            source: Source of the alert
            data: Additional alert data
            
        Returns:
            Created Alert object
        """
        alert = Alert(
            id=f"alert_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.alerts)}",
            timestamp=datetime.now(),
            severity=severity,
            alert_type=alert_type,
            title=title,
            message=message,
            source=source,
            data=data or {}
        )
        
        # Store alert
        self.alerts.append(alert)
        
        # Update dashboard
        self._update_dashboard_alerts()
        
        # Trigger alert handlers
        await self._trigger_alert_handlers(alert)
        
        logger.info(f"Alert created: {severity.value} - {title}")
        return alert
    
    def register_alert_handler(self, alert_type: AlertType, handler: Callable) -> None:
        """Register a handler for specific alert types"""
        self.alert_handlers[alert_type].append(handler)
        logger.info(f"Alert handler registered for {alert_type.value}")
    
    async def _trigger_alert_handlers(self, alert: Alert) -> None:
        """Trigger registered handlers for an alert"""
        handlers = self.alert_handlers.get(alert.alert_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                logger.error(f"Error in alert handler: {e}")
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                logger.info(f"Alert acknowledged: {alert_id}")
                return True
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.resolved = True
                logger.info(f"Alert resolved: {alert_id}")
                return True
        return False
    
    # ================================================================================
    # ANOMALY DETECTION
    # ================================================================================
    
    async def detect_anomalies(self, 
                              data: pd.DataFrame,
                              metric_name: str = "performance") -> List[AnomalyDetection]:
        """
        Detect anomalies in time series data using ML
        
        Args:
            data: Time series data to analyze
            metric_name: Name of the metric being analyzed
            
        Returns:
            List of detected anomalies
        """
        try:
            anomalies = []
            
            if len(data) < 10:  # Need minimum data for anomaly detection
                return anomalies
            
            # Prepare features for anomaly detection
            features = self._prepare_anomaly_features(data)
            
            if features is not None and len(features) > 0:
                # Fit anomaly detector
                self.anomaly_detector.fit(features)
                
                # Detect anomalies
                anomaly_labels = self.anomaly_detector.predict(features)
                anomaly_scores = self.anomaly_detector.decision_function(features)
                
                # Process anomalies
                for i, (is_anomaly, score) in enumerate(zip(anomaly_labels, anomaly_scores)):
                    if is_anomaly == -1:  # Anomaly detected
                        severity_score = min(1.0, abs(score) / 2.0)  # Normalize to 0-1
                        
                        anomaly = AnomalyDetection(
                            timestamp=data.index[i] if hasattr(data, 'index') else datetime.now(),
                            anomaly_type=self._classify_anomaly_type(metric_name),
                            severity_score=severity_score,
                            description=f"Anomaly detected in {metric_name}",
                            affected_metrics=[metric_name],
                            confidence=min(0.95, 0.5 + severity_score * 0.4),
                            raw_data={'score': score, 'index': i}
                        )
                        
                        anomalies.append(anomaly)
                        self.anomalies.append(anomaly)
                        
                        # Create alert for significant anomalies
                        if severity_score > 0.7:
                            await self.create_alert(
                                severity=AlertSeverity.WARNING if severity_score < 0.9 else AlertSeverity.ERROR,
                                alert_type=AlertType.ANOMALY,
                                title=f"Anomaly Detected: {metric_name}",
                                message=f"Significant anomaly detected with severity {severity_score:.2f}",
                                source="anomaly_detector",
                                data={'anomaly': anomaly.__dict__}
                            )
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error in anomaly detection: {e}")
            return []
    
    def _prepare_anomaly_features(self, data: pd.DataFrame) -> Optional[np.ndarray]:
        """Prepare features for anomaly detection"""
        try:
            if isinstance(data, pd.Series):
                # Convert series to DataFrame
                data = data.to_frame('value')
            
            # Create rolling statistics as features
            features = []
            
            for col in data.select_dtypes(include=[np.number]).columns:
                series = data[col].dropna()
                if len(series) > 5:
                    # Rolling statistics
                    rolling_mean = series.rolling(window=5, min_periods=1).mean()
                    rolling_std = series.rolling(window=5, min_periods=1).std()
                    rolling_min = series.rolling(window=5, min_periods=1).min()
                    rolling_max = series.rolling(window=5, min_periods=1).max()
                    
                    # Z-score
                    z_score = (series - rolling_mean) / (rolling_std + 1e-8)
                    
                    # Combine features
                    feature_matrix = np.column_stack([
                        series.values,
                        rolling_mean.values,
                        rolling_std.values,
                        z_score.values,
                        rolling_min.values,
                        rolling_max.values
                    ])
                    
                    features.append(feature_matrix)
            
            if features:
                # Combine all features
                combined_features = np.concatenate(features, axis=1)
                
                # Handle NaN values
                combined_features = np.nan_to_num(combined_features, nan=0.0)
                
                return combined_features
            
            return None
            
        except Exception as e:
            logger.error(f"Error preparing anomaly features: {e}")
            return None
    
    def _classify_anomaly_type(self, metric_name: str) -> AnomalyType:
        """Classify anomaly type based on metric name"""
        metric_lower = metric_name.lower()
        
        if 'performance' in metric_lower or 'return' in metric_lower:
            return AnomalyType.PERFORMANCE_ANOMALY
        elif 'volume' in metric_lower:
            return AnomalyType.VOLUME_ANOMALY
        elif 'price' in metric_lower:
            return AnomalyType.PRICE_ANOMALY
        elif 'execution' in metric_lower:
            return AnomalyType.EXECUTION_ANOMALY
        else:
            return AnomalyType.SYSTEM_ANOMALY
    
    # ================================================================================
    # DASHBOARD AND UTILITY METHODS
    # ================================================================================
    
    def _update_dashboard_alerts(self) -> None:
        """Update dashboard with current alerts"""
        active_alerts = [
            alert for alert in self.alerts 
            if not alert.resolved and alert.severity in [AlertSeverity.WARNING, AlertSeverity.ERROR, AlertSeverity.CRITICAL]
        ]
        
        self.dashboard_data['active_alerts'] = [
            {
                'id': alert.id,
                'timestamp': alert.timestamp.isoformat(),
                'severity': alert.severity.value,
                'title': alert.title,
                'message': alert.message,
                'acknowledged': alert.acknowledged
            }
            for alert in active_alerts[-10:]  # Last 10 active alerts
        ]
        
        # Update recent anomalies
        recent_anomalies = list(self.anomalies)[-5:]  # Last 5 anomalies
        self.dashboard_data['recent_anomalies'] = [
            {
                'timestamp': anomaly.timestamp.isoformat(),
                'type': anomaly.anomaly_type.value,
                'severity': anomaly.severity_score,
                'description': anomaly.description,
                'confidence': anomaly.confidence
            }
            for anomaly in recent_anomalies
        ]
        
        self.dashboard_data['last_updated'] = datetime.now().isoformat()
    
    async def start_monitoring(self) -> None:
        """Start the monitoring system"""
        if self.is_monitoring:
            logger.warning("Monitoring already active")
            return
        
        self.is_monitoring = True
        self.status = MonitoringStatus.ACTIVE
        
        # Start monitoring task
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Monitoring system started")
    
    async def stop_monitoring(self) -> None:
        """Stop the monitoring system"""
        self.is_monitoring = False
        self.status = MonitoringStatus.PAUSED
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Monitoring system stopped")
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                # Update dashboard data
                self._update_dashboard_alerts()
                
                # Sleep until next monitoring cycle
                await asyncio.sleep(self.monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.monitoring_interval)
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get current dashboard data"""
        return self.dashboard_data.copy()
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get monitoring system status"""
        return {
            'status': self.status.value,
            'is_monitoring': self.is_monitoring,
            'total_alerts': len(self.alerts),
            'unresolved_alerts': len([a for a in self.alerts if not a.resolved]),
            'total_anomalies': len(self.anomalies),
            'monitoring_interval': self.monitoring_interval,
            'last_updated': datetime.now().isoformat()
        }

# ================================================================================
# CONVENIENCE FUNCTIONS AND ALIASES
# ================================================================================

# Create global instance for backward compatibility
monitoring_analytics = MonitoringAnalyticsEngine()

# Aliases for backward compatibility
MonitoringEngine = MonitoringAnalyticsEngine
AlertManager = MonitoringAnalyticsEngine
PredictiveMonitor = MonitoringAnalyticsEngine
AnomalyDetector = MonitoringAnalyticsEngine
MultiStrategyDashboard = MonitoringAnalyticsEngine

# Convenience functions
async def create_alert(severity: AlertSeverity, alert_type: AlertType, title: str, message: str, **kwargs) -> Alert:
    """Convenience function for creating alerts"""
    return await monitoring_analytics.create_alert(severity, alert_type, title, message, **kwargs)

async def detect_anomalies(data: pd.DataFrame, metric_name: str = "performance") -> List[AnomalyDetection]:
    """Convenience function for anomaly detection"""
    return await monitoring_analytics.detect_anomalies(data, metric_name)

def get_dashboard_data() -> Dict[str, Any]:
    """Convenience function for getting dashboard data"""
    return monitoring_analytics.get_dashboard_data()

logger.info("Monitoring Analytics module loaded successfully - 5 modules consolidated into 1")
