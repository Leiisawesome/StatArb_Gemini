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
Version: 1.0.0 (Consolidated) - Phase 2: Enhanced Error Handling
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

# Enhanced error handling
from .error_handling import (
    error_handling_manager, 
    CircuitBreakerError, 
    MaxRetriesExceededError,
    circuit_breaker,
    retry_on_failure
)

# Performance optimizations
from .performance_optimization import (
    VectorizedCalculations,
    ParallelProcessor,
    performance_optimized,
    vectorized_calc,
    parallel_processor,
    intelligent_cache,
    performance_profiler
)

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
    
    def __init__(self):
        """Initialize monitoring analytics with error handling"""
        self.alerts: List[Alert] = []
        self.anomaly_history: List[AnomalyDetection] = []
        self.dashboard_data: Dict[str, Any] = {}
        self.monitoring_status = MonitoringStatus.MAINTENANCE
        self.last_update = datetime.now()
        
        # Initialize error handling and performance optimization components
        self.error_handling_manager = error_handling_manager
        self.vectorized_calc = vectorized_calc
        self.intelligent_cache = intelligent_cache
        
        # ML models for anomaly detection
        self.isolation_forest = None
        self.model_last_trained = None
        
        self.monitoring_status = MonitoringStatus.ACTIVE
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
        Create and process a new alert with enhanced error handling
        
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
        async with error_handling_manager.protected_operation(
            "alert_creation",
            "database",
            "database",
            retryable_exceptions=(ValueError, RuntimeError),
            non_retryable_exceptions=(TypeError, MemoryError)
        ) as protected_op:
            
            async def _create_alert():
                try:
                    # Input validation
                    if not title or not isinstance(title, str):
                        title_safe = "Untitled Alert"
                        logger.warning(f"Invalid alert title provided, using default: {title_safe}")
                    else:
                        title_safe = title[:200]  # Limit title length
                    
                    if not message or not isinstance(message, str):
                        message_safe = "No message provided"
                        logger.warning(f"Invalid alert message provided, using default: {message_safe}")
                    else:
                        message_safe = message[:1000]  # Limit message length
                    
                    if not isinstance(source, str):
                        source_safe = "unknown"
                        logger.warning(f"Invalid alert source provided, using default: {source_safe}")
                    else:
                        source_safe = source[:50]  # Limit source length
                    
                    # Sanitize data payload
                    data_safe = {}
                    if data:
                        try:
                            # Ensure data is serializable and bounded
                            import json
                            data_str = json.dumps(data)
                            if len(data_str) > 10000:  # Limit data size
                                data_safe = {"warning": "Data payload too large, truncated"}
                                logger.warning("Alert data payload truncated due to size")
                            else:
                                data_safe = data
                        except (TypeError, ValueError) as e:
                            logger.warning(f"Alert data not serializable: {e}")
                            data_safe = {"error": "Data not serializable"}
                    
                    # Create alert with safe timestamp
                    try:
                        timestamp = datetime.now()
                        alert_id = f"alert_{timestamp.strftime('%Y%m%d_%H%M%S')}_{len(self.alerts)}"
                    except Exception as e:
                        logger.warning(f"Error generating alert ID: {e}")
                        timestamp = datetime.now()
                        alert_id = f"alert_{int(timestamp.timestamp())}_{len(self.alerts)}"
                    
                    alert = Alert(
                        id=alert_id,
                        timestamp=timestamp,
                        severity=severity,
                        alert_type=alert_type,
                        title=title_safe,
                        message=message_safe,
                        source=source_safe,
                        data=data_safe
                    )
                    
                    # Store alert with bounds checking
                    try:
                        if len(self.alerts) >= 5000:  # Prevent unbounded growth
                            # Remove oldest alerts, keep last 4000
                            old_count = len(self.alerts)
                            self.alerts = self.alerts[-4000:]
                            logger.info(f"Alert history trimmed from {old_count} to {len(self.alerts)} entries")
                        
                        self.alerts.append(alert)
                        
                    except Exception as e:
                        logger.error(f"Error storing alert: {e}")
                        # Continue processing even if storage fails
                    
                    # Update dashboard with error handling
                    try:
                        self._update_dashboard_alerts()
                    except Exception as e:
                        logger.warning(f"Error updating dashboard for alert: {e}")
                    
                    # Trigger alert handlers with error handling
                    try:
                        await self._trigger_alert_handlers(alert)
                    except Exception as e:
                        logger.warning(f"Error triggering alert handlers: {e}")
                    
                    logger.info(f"Alert created successfully: {severity.value} - {title_safe[:50]}")
                    return alert
                    
                except Exception as e:
                    logger.error(f"Critical error creating alert: {e}")
                    # Return a minimal alert to prevent complete failure
                    return Alert(
                        id=f"error_alert_{int(datetime.now().timestamp())}",
                        timestamp=datetime.now(),
                        severity=AlertSeverity.ERROR,
                        alert_type=AlertType.SYSTEM,
                        title="Alert Creation Error",
                        message=f"Failed to create alert: {e}",
                        source="error_handler",
                        data={}
                    )
            
            return await protected_op.execute(_create_alert)
    
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
    
    @performance_optimized(
        cache_key_func=lambda self, data, metric_name="performance": 
            f"anomaly_detection_{metric_name}_{hash(str(data.index))}_{len(data)}",
        vectorization_ratio=0.90,
        enable_parallel=False
    )
    async def detect_anomalies(self, 
                              data: pd.DataFrame,
                              metric_name: str = "performance") -> List[AnomalyDetection]:
        """
        Detect anomalies in time series data using ML with enhanced error handling
        
        Args:
            data: Time series data to analyze
            metric_name: Name of the metric being analyzed
            
        Returns:
            List of detected anomalies
        """
        async with error_handling_manager.protected_operation(
            "anomaly_detection",
            "external_data",
            "external_data",
            retryable_exceptions=(ValueError, RuntimeError, pd.errors.DataError),
            non_retryable_exceptions=(KeyError, TypeError, MemoryError)
        ) as protected_op:
            
            async def _perform_anomaly_detection():
                try:
                    anomalies = []
                    
                    # Input validation
                    if data is None:
                        logger.warning("No data provided for anomaly detection")
                        return anomalies
                    
                    if len(data) < 10:  # Need minimum data for anomaly detection
                        logger.debug(f"Insufficient data for anomaly detection: {len(data)} rows (minimum 10 required)")
                        return anomalies
                    
                    # Validate data quality
                    if isinstance(data, pd.DataFrame):
                        numeric_cols = data.select_dtypes(include=[np.number]).columns
                        if len(numeric_cols) == 0:
                            logger.warning("No numeric columns found for anomaly detection")
                            return anomalies
                        
                        # Check for excessive NaN values
                        nan_ratio = data[numeric_cols].isnull().sum().sum() / (len(data) * len(numeric_cols))
                        if nan_ratio > 0.5:
                            logger.warning(f"High NaN ratio ({nan_ratio:.2f}) in data for anomaly detection")
                    
                    # Prepare features for anomaly detection with error handling
                    try:
                        features = self._prepare_anomaly_features(data)
                        
                        if features is None:
                            logger.warning("Failed to prepare features for anomaly detection")
                            return anomalies
                        
                        if len(features) == 0:
                            logger.warning("Empty features array for anomaly detection")
                            return anomalies
                        
                        # Check for invalid values in features
                        if np.any(np.isnan(features)) or np.any(np.isinf(features)):
                            logger.warning("Invalid values (NaN/Inf) found in features, cleaning...")
                            features = np.nan_to_num(features, nan=0.0, posinf=1e6, neginf=-1e6)
                        
                    except Exception as e:
                        logger.error(f"Error preparing anomaly detection features: {e}")
                        return anomalies
                    
                    # Fit anomaly detector with error handling
                    try:
                        if self.anomaly_detector is None:
                            logger.warning("Anomaly detector not initialized, creating new instance")
                            self.anomaly_detector = IsolationForest(
                                contamination=0.1, 
                                random_state=42,
                                n_estimators=50  # Reduced for better performance
                            )
                        
                        # Fit detector with timeout protection
                        self.anomaly_detector.fit(features)
                        
                    except (ValueError, MemoryError) as e:
                        logger.error(f"Error fitting anomaly detector: {e}")
                        return anomalies
                    
                    # Detect anomalies with error handling
                    try:
                        anomaly_labels = self.anomaly_detector.predict(features)
                        anomaly_scores = self.anomaly_detector.decision_function(features)
                        
                        # Validate prediction results
                        if len(anomaly_labels) != len(features) or len(anomaly_scores) != len(features):
                            logger.error("Mismatch in anomaly detection results length")
                            return anomalies
                        
                    except Exception as e:
                        logger.error(f"Error in anomaly prediction: {e}")
                        return anomalies
                    
                    # Process anomalies with validation
                    try:
                        for i, (is_anomaly, score) in enumerate(zip(anomaly_labels, anomaly_scores)):
                            if is_anomaly == -1:  # Anomaly detected
                                try:
                                    # Bound severity score
                                    severity_score = min(1.0, max(0.0, abs(score) / 2.0))  # Normalize to 0-1
                                    
                                    # Get timestamp safely
                                    if hasattr(data, 'index') and i < len(data.index):
                                        timestamp = data.index[i]
                                    else:
                                        timestamp = datetime.now()
                                    
                                    anomaly = AnomalyDetection(
                                        timestamp=timestamp,
                                        anomaly_type=self._classify_anomaly_type(metric_name),
                                        severity_score=severity_score,
                                        description=f"Anomaly detected in {metric_name} (score: {score:.3f})",
                                        affected_metrics=[metric_name],
                                        confidence=min(0.95, max(0.1, 0.5 + severity_score * 0.4)),
                                        raw_data={'score': float(score), 'index': i, 'feature_vector': features[i].tolist() if i < len(features) else []}
                                    )
                                    
                                    anomalies.append(anomaly)
                                    
                                    # Add to history with bounds checking
                                    if len(self.anomalies) >= 1000:  # Prevent unbounded growth
                                        self.anomalies.popleft()  # Remove oldest
                                    self.anomalies.append(anomaly)
                                    
                                    # Create alert for significant anomalies with error handling
                                    if severity_score > 0.7:
                                        try:
                                            alert_severity = AlertSeverity.WARNING if severity_score < 0.9 else AlertSeverity.ERROR
                                            await self.create_alert(
                                                severity=alert_severity,
                                                alert_type=AlertType.ANOMALY,
                                                title=f"Anomaly Detected: {metric_name}",
                                                message=f"Significant anomaly detected with severity {severity_score:.2f} at index {i}",
                                                source="anomaly_detector",
                                                data={'anomaly': anomaly.__dict__}
                                            )
                                        except Exception as alert_error:
                                            logger.warning(f"Failed to create alert for anomaly: {alert_error}")
                                
                                except Exception as anomaly_error:
                                    logger.warning(f"Error processing anomaly at index {i}: {anomaly_error}")
                                    continue
                    
                    except Exception as e:
                        logger.error(f"Error processing anomaly results: {e}")
                    
                    logger.debug(f"Anomaly detection completed: {len(anomalies)} anomalies found in {metric_name}")
                    return anomalies
                    
                except Exception as e:
                    logger.error(f"Critical error in anomaly detection: {e}")
                    return []
            
            return await protected_op.execute(_perform_anomaly_detection)
    
    def _prepare_anomaly_features(self, data: pd.DataFrame) -> Optional[np.ndarray]:
        """Prepare features for anomaly detection using vectorized operations"""
        try:
            if isinstance(data, pd.Series):
                # Convert series to DataFrame
                data = data.to_frame('value')
            
            # Get numeric columns and convert to numpy array for vectorized operations
            numeric_cols = data.select_dtypes(include=[np.number])
            if numeric_cols.empty:
                return None
            
            # Use vectorized calculations for performance optimization
            data_array = numeric_cols.values
            if data_array.shape[0] < 5:
                return None
            
            # Vectorized rolling statistics computation
            rolling_features = self.vectorized_calc.calculate_rolling_features(
                data_array, window=5
            )
            
            # Compute additional statistical features vectorized
            z_scores = self.vectorized_calc.calculate_rolling_z_scores(
                data_array, window=5
            )
            
            # Combine all features using vectorized operations
            feature_matrices = []
            for i in range(data_array.shape[1]):
                col_data = data_array[:, i:i+1]  # Keep 2D shape
                col_rolling = rolling_features[i]  # Shape: (n_samples, 4) for mean,std,min,max
                col_z_scores = z_scores[:, i:i+1]  # Keep 2D shape
                
                # Stack all features for this column
                col_features = np.hstack([
                    col_data,           # Original values
                    col_rolling,        # Rolling statistics
                    col_z_scores        # Z-scores
                ])
                feature_matrices.append(col_features)
            
            if feature_matrices:
                # Vectorized concatenation
                combined_features = np.hstack(feature_matrices)
                
                # Efficient NaN handling
                combined_features = np.nan_to_num(combined_features, nan=0.0, 
                                                posinf=0.0, neginf=0.0)
                
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

# Create alias for backward compatibility  
MonitoringAnalytics = MonitoringAnalyticsEngine

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
