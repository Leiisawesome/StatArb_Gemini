#!/usr/bin/env python3
"""
Anomaly Detector
================

Advanced anomaly detection system providing:
- Multi-dimensional anomaly detection
- Real-time anomaly scoring
- Context-aware anomaly classification
- Adaptive threshold management
- Anomaly correlation analysis

Author: StatArb_Gemini Team
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import deque
import threading
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.cluster import DBSCAN
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class AnomalyType(Enum):
    """Types of anomalies"""
    POINT_ANOMALY = "point_anomaly"      # Single data point anomaly
    CONTEXTUAL_ANOMALY = "contextual_anomaly"  # Anomaly in specific context
    COLLECTIVE_ANOMALY = "collective_anomaly"  # Pattern-based anomaly
    TREND_ANOMALY = "trend_anomaly"      # Trend deviation
    SEASONAL_ANOMALY = "seasonal_anomaly"  # Seasonal pattern deviation

class AnomalySeverity(Enum):
    """Anomaly severity levels"""
    LOW = "low"           # Minor deviation
    MEDIUM = "medium"     # Moderate deviation  
    HIGH = "high"         # Significant deviation
    CRITICAL = "critical" # Severe deviation

class AnomalyStatus(Enum):
    """Anomaly investigation status"""
    DETECTED = "detected"
    INVESTIGATING = "investigating"
    CONFIRMED = "confirmed"
    FALSE_POSITIVE = "false_positive"
    RESOLVED = "resolved"

@dataclass
class Anomaly:
    """Anomaly detection result"""
    id: str
    timestamp: datetime
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    anomaly_score: float  # 0-1, higher = more anomalous
    affected_metrics: List[str]
    metric_values: Dict[str, float]
    expected_values: Dict[str, float]
    deviation_percentage: Dict[str, float]
    
    # Fields with defaults must come after fields without defaults
    status: AnomalyStatus = AnomalyStatus.DETECTED
    context: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    confidence: float = 0.0
    
    # Investigation details
    investigated_by: Optional[str] = None
    investigation_notes: List[str] = field(default_factory=list)
    resolution_time: Optional[datetime] = None

@dataclass
class AnomalyPattern:
    """Detected anomaly pattern"""
    pattern_id: str
    pattern_type: str
    first_detected: datetime
    last_detected: datetime
    occurrences: int
    affected_metrics: List[str]
    pattern_strength: float
    description: str

class AnomalyDetector:
    """
    Advanced multi-dimensional anomaly detection system.
    
    Features:
    - Multiple detection algorithms (Isolation Forest, Statistical, Clustering)
    - Real-time anomaly scoring and classification
    - Adaptive threshold management
    - Context-aware anomaly detection
    - Pattern recognition and correlation analysis
    - False positive reduction
    """
    
    def __init__(
        self,
        contamination_rate: float = 0.1,  # Expected anomaly rate
        history_window: int = 1000,
        sensitivity: float = 0.8,  # 0-1, higher = more sensitive
        min_pattern_occurrences: int = 3
    ):
        self.contamination_rate = contamination_rate
        self.history_window = history_window
        self.sensitivity = sensitivity
        self.min_pattern_occurrences = min_pattern_occurrences
        
        # Data storage
        self.metrics_history: deque = deque(maxlen=history_window)
        self.anomalies_history: deque = deque(maxlen=500)
        self.patterns_history: deque = deque(maxlen=100)
        
        # Detection models
        self.isolation_forest: Optional[IsolationForest] = None
        self.scaler = RobustScaler()  # More robust to outliers
        self.dbscan: Optional[DBSCAN] = None
        
        # Detection state
        self.is_detecting = False
        self.detection_lock = threading.RLock()
        
        # Adaptive thresholds
        self.adaptive_thresholds: Dict[str, Dict[str, float]] = {}
        self.threshold_update_frequency = 50  # Update every 50 data points
        
        # Statistical baselines
        self.statistical_baselines: Dict[str, Dict[str, float]] = {}
        
        # Pattern detection
        self.anomaly_patterns: Dict[str, AnomalyPattern] = {}
        
        logger.info("AnomalyDetector initialized")
    
    async def start_detection(self):
        """Start anomaly detection"""
        if self.is_detecting:
            logger.warning("Anomaly detection already active")
            return
        
        self.is_detecting = True
        
        # Initialize models if we have enough data
        if len(self.metrics_history) > 50:
            await self._initialize_models()
        
        logger.info("Anomaly detection started")
    
    async def stop_detection(self):
        """Stop anomaly detection"""
        self.is_detecting = False
        logger.info("Anomaly detection stopped")
    
    def add_metrics_data(self, timestamp: datetime, metrics: Dict[str, float]):
        """Add new metrics data for anomaly detection"""
        with self.detection_lock:
            data_point = {
                'timestamp': timestamp,
                'metrics': metrics.copy()
            }
            self.metrics_history.append(data_point)
            
            # Update statistical baselines
            self._update_statistical_baselines(metrics)
            
            # Update adaptive thresholds periodically
            if len(self.metrics_history) % self.threshold_update_frequency == 0:
                self._update_adaptive_thresholds()
    
    async def detect_anomalies(self, current_metrics: Dict[str, float]) -> List[Anomaly]:
        """Detect anomalies in current metrics"""
        if not self.is_detecting or len(self.metrics_history) < 30:
            return []
        
        anomalies = []
        timestamp = datetime.now()
        
        try:
            with self.detection_lock:
                # 1. Statistical anomaly detection
                statistical_anomalies = await self._detect_statistical_anomalies(
                    timestamp, current_metrics
                )
                anomalies.extend(statistical_anomalies)
                
                # 2. Machine learning anomaly detection
                if self.isolation_forest is not None:
                    ml_anomalies = await self._detect_ml_anomalies(
                        timestamp, current_metrics
                    )
                    anomalies.extend(ml_anomalies)
                
                # 3. Contextual anomaly detection
                contextual_anomalies = await self._detect_contextual_anomalies(
                    timestamp, current_metrics
                )
                anomalies.extend(contextual_anomalies)
                
                # 4. Trend anomaly detection
                trend_anomalies = await self._detect_trend_anomalies(
                    timestamp, current_metrics
                )
                anomalies.extend(trend_anomalies)
                
                # 5. Pattern-based anomaly detection
                pattern_anomalies = await self._detect_pattern_anomalies(
                    timestamp, current_metrics
                )
                anomalies.extend(pattern_anomalies)
                
                # Filter and deduplicate anomalies
                anomalies = self._filter_anomalies(anomalies)
                
                # Store detected anomalies
                self.anomalies_history.extend(anomalies)
                
                # Update anomaly patterns
                self._update_anomaly_patterns(anomalies)
                
        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
        
        return anomalies
    
    async def _detect_statistical_anomalies(
        self, 
        timestamp: datetime, 
        current_metrics: Dict[str, float]
    ) -> List[Anomaly]:
        """Detect anomalies using statistical methods"""
        anomalies = []
        
        try:
            for metric_name, current_value in current_metrics.items():
                if metric_name not in self.statistical_baselines:
                    continue
                
                baseline = self.statistical_baselines[metric_name]
                mean = baseline.get('mean', 0)
                std = baseline.get('std', 1)
                
                # Z-score based detection
                z_score = abs((current_value - mean) / (std + 1e-6))
                
                # Adaptive threshold based on sensitivity
                threshold = 2.0 + (1.0 - self.sensitivity) * 2.0  # 2-4 standard deviations
                
                if z_score > threshold:
                    # Determine severity
                    if z_score > 4.0:
                        severity = AnomalySeverity.CRITICAL
                    elif z_score > 3.5:
                        severity = AnomalySeverity.HIGH
                    elif z_score > 3.0:
                        severity = AnomalySeverity.MEDIUM
                    else:
                        severity = AnomalySeverity.LOW
                    
                    # Calculate deviation percentage
                    deviation_pct = ((current_value - mean) / (mean + 1e-6)) * 100
                    
                    anomaly = Anomaly(
                        id=f"stat_{metric_name}_{int(timestamp.timestamp())}",
                        timestamp=timestamp,
                        anomaly_type=AnomalyType.POINT_ANOMALY,
                        severity=severity,
                        anomaly_score=min(z_score / 6.0, 1.0),  # Normalize to 0-1
                        affected_metrics=[metric_name],
                        metric_values={metric_name: current_value},
                        expected_values={metric_name: mean},
                        deviation_percentage={metric_name: deviation_pct},
                        confidence=min(z_score / 4.0, 1.0),
                        description=f"Statistical anomaly in {metric_name}: {current_value:.3f} "
                                  f"(expected: {mean:.3f}, z-score: {z_score:.2f})"
                    )
                    
                    anomalies.append(anomaly)
                    
        except Exception as e:
            logger.error(f"Error in statistical anomaly detection: {e}")
        
        return anomalies
    
    async def _detect_ml_anomalies(
        self, 
        timestamp: datetime, 
        current_metrics: Dict[str, float]
    ) -> List[Anomaly]:
        """Detect anomalies using machine learning models"""
        anomalies = []
        
        try:
            if self.isolation_forest is None:
                return anomalies
            
            # Prepare feature vector
            recent_data = list(self.metrics_history)[-20:]  # Last 20 points
            if len(recent_data) < 10:
                return anomalies
            
            # Extract features for all metrics
            all_metrics = set()
            for data_point in recent_data:
                all_metrics.update(data_point['metrics'].keys())
            
            # Create feature vector
            features = []
            for metric_name in sorted(all_metrics):
                if metric_name in current_metrics:
                    features.append(current_metrics[metric_name])
                else:
                    features.append(0.0)  # Missing value
            
            if len(features) == 0:
                return anomalies
            
            # Scale features
            features_array = np.array(features).reshape(1, -1)
            features_scaled = self.scaler.transform(features_array)
            
            # Predict anomaly
            anomaly_prediction = self.isolation_forest.predict(features_scaled)[0]
            anomaly_score = self.isolation_forest.decision_function(features_scaled)[0]
            
            # Convert score to 0-1 range (more negative = more anomalous)
            normalized_score = max(0, min(1, (0.5 - anomaly_score) * 2))
            
            if anomaly_prediction == -1:  # Anomaly detected
                # Determine which metrics contributed most to the anomaly
                affected_metrics = []
                metric_contributions = {}
                
                for i, metric_name in enumerate(sorted(all_metrics)):
                    if metric_name in current_metrics:
                        # Simple contribution calculation
                        baseline_val = self.statistical_baselines.get(metric_name, {}).get('mean', 0)
                        contribution = abs(current_metrics[metric_name] - baseline_val)
                        metric_contributions[metric_name] = contribution
                        
                        if contribution > 0.1:  # Threshold for contribution
                            affected_metrics.append(metric_name)
                
                if affected_metrics:
                    # Determine severity based on anomaly score
                    if normalized_score > 0.8:
                        severity = AnomalySeverity.CRITICAL
                    elif normalized_score > 0.6:
                        severity = AnomalySeverity.HIGH
                    elif normalized_score > 0.4:
                        severity = AnomalySeverity.MEDIUM
                    else:
                        severity = AnomalySeverity.LOW
                    
                    anomaly = Anomaly(
                        id=f"ml_{int(timestamp.timestamp())}",
                        timestamp=timestamp,
                        anomaly_type=AnomalyType.POINT_ANOMALY,
                        severity=severity,
                        anomaly_score=normalized_score,
                        affected_metrics=affected_metrics,
                        metric_values=current_metrics,
                        expected_values={},  # ML models don't provide explicit expectations
                        deviation_percentage={},
                        confidence=normalized_score,
                        description=f"ML-detected anomaly affecting {len(affected_metrics)} metrics "
                                  f"(score: {normalized_score:.3f})"
                    )
                    
                    anomalies.append(anomaly)
                    
        except Exception as e:
            logger.error(f"Error in ML anomaly detection: {e}")
        
        return anomalies
    
    async def _detect_contextual_anomalies(
        self, 
        timestamp: datetime, 
        current_metrics: Dict[str, float]
    ) -> List[Anomaly]:
        """Detect contextual anomalies (time-based, correlation-based)"""
        anomalies = []
        
        try:
            # Time-based contextual detection
            hour = timestamp.hour
            weekday = timestamp.weekday()
            
            # Simple contextual rules (can be enhanced with more sophisticated models)
            context_rules = {
                'night_high_activity': {
                    'condition': hour >= 23 or hour <= 5,
                    'metrics': ['cpu_usage', 'memory_usage', 'network_io'],
                    'threshold': 0.7  # 70% usage during night hours
                },
                'weekend_high_activity': {
                    'condition': weekday >= 5,  # Saturday or Sunday
                    'metrics': ['cpu_usage', 'memory_usage'],
                    'threshold': 0.8
                },
                'business_hours_low_activity': {
                    'condition': 9 <= hour <= 17 and weekday < 5,
                    'metrics': ['cpu_usage', 'throughput'],
                    'threshold': 0.1  # Very low activity during business hours
                }
            }
            
            for rule_name, rule in context_rules.items():
                if rule['condition']:
                    for metric_name in rule['metrics']:
                        if metric_name in current_metrics:
                            metric_value = current_metrics[metric_name]
                            
                            # Check if value violates contextual expectation
                            is_anomaly = False
                            if 'high_activity' in rule_name:
                                is_anomaly = metric_value > rule['threshold']
                            elif 'low_activity' in rule_name:
                                is_anomaly = metric_value < rule['threshold']
                            
                            if is_anomaly:
                                anomaly = Anomaly(
                                    id=f"ctx_{rule_name}_{metric_name}_{int(timestamp.timestamp())}",
                                    timestamp=timestamp,
                                    anomaly_type=AnomalyType.CONTEXTUAL_ANOMALY,
                                    severity=AnomalySeverity.MEDIUM,
                                    anomaly_score=0.6,
                                    affected_metrics=[metric_name],
                                    metric_values={metric_name: metric_value},
                                    expected_values={metric_name: rule['threshold']},
                                    deviation_percentage={
                                        metric_name: ((metric_value - rule['threshold']) / rule['threshold']) * 100
                                    },
                                    context={
                                        'rule': rule_name,
                                        'hour': hour,
                                        'weekday': weekday
                                    },
                                    confidence=0.7,
                                    description=f"Contextual anomaly: {metric_name} = {metric_value:.3f} "
                                              f"violates {rule_name} expectation"
                                )
                                
                                anomalies.append(anomaly)
                                
        except Exception as e:
            logger.error(f"Error in contextual anomaly detection: {e}")
        
        return anomalies
    
    async def _detect_trend_anomalies(
        self, 
        timestamp: datetime, 
        current_metrics: Dict[str, float]
    ) -> List[Anomaly]:
        """Detect trend-based anomalies"""
        anomalies = []
        
        try:
            if len(self.metrics_history) < 20:
                return anomalies
            
            recent_data = list(self.metrics_history)[-20:]
            
            for metric_name in current_metrics.keys():
                # Extract metric values over time
                values = []
                for data_point in recent_data:
                    if metric_name in data_point['metrics']:
                        values.append(data_point['metrics'][metric_name])
                
                if len(values) < 10:
                    continue
                
                # Calculate trend
                x = np.arange(len(values))
                trend_slope, _ = np.polyfit(x, values, 1)
                
                # Current rate of change
                current_value = current_metrics[metric_name]
                previous_value = values[-1]
                rate_of_change = current_value - previous_value
                
                # Detect sudden trend reversals or accelerations
                expected_change = trend_slope
                change_deviation = abs(rate_of_change - expected_change)
                
                # Adaptive threshold based on recent volatility
                recent_volatility = np.std(np.diff(values[-10:]))
                threshold = 3 * recent_volatility
                
                if change_deviation > threshold:
                    severity = AnomalySeverity.HIGH if change_deviation > 5 * threshold else AnomalySeverity.MEDIUM
                    
                    anomaly = Anomaly(
                        id=f"trend_{metric_name}_{int(timestamp.timestamp())}",
                        timestamp=timestamp,
                        anomaly_type=AnomalyType.TREND_ANOMALY,
                        severity=severity,
                        anomaly_score=min(change_deviation / (5 * threshold), 1.0),
                        affected_metrics=[metric_name],
                        metric_values={metric_name: current_value},
                        expected_values={metric_name: previous_value + expected_change},
                        deviation_percentage={
                            metric_name: (change_deviation / (abs(previous_value) + 1e-6)) * 100
                        },
                        context={
                            'trend_slope': trend_slope,
                            'expected_change': expected_change,
                            'actual_change': rate_of_change
                        },
                        confidence=0.8,
                        description=f"Trend anomaly in {metric_name}: unexpected change rate "
                                  f"{rate_of_change:.3f} vs expected {expected_change:.3f}"
                    )
                    
                    anomalies.append(anomaly)
                    
        except Exception as e:
            logger.error(f"Error in trend anomaly detection: {e}")
        
        return anomalies
    
    async def _detect_pattern_anomalies(
        self, 
        timestamp: datetime, 
        current_metrics: Dict[str, float]
    ) -> List[Anomaly]:
        """Detect pattern-based anomalies"""
        anomalies = []
        
        try:
            # Simple pattern detection - can be enhanced with more sophisticated methods
            if len(self.metrics_history) < 50:
                return anomalies
            
            # Look for unusual patterns in metric combinations
            recent_data = list(self.metrics_history)[-30:]
            
            # Check for correlation anomalies
            metric_names = list(current_metrics.keys())
            if len(metric_names) >= 2:
                for i, metric1 in enumerate(metric_names):
                    for metric2 in metric_names[i+1:]:
                        # Extract historical correlation
                        values1 = []
                        values2 = []
                        
                        for data_point in recent_data:
                            if metric1 in data_point['metrics'] and metric2 in data_point['metrics']:
                                values1.append(data_point['metrics'][metric1])
                                values2.append(data_point['metrics'][metric2])
                        
                        if len(values1) >= 10:
                            # Calculate historical correlation
                            try:
                                historical_corr = np.corrcoef(values1, values2)[0, 1]
                                
                                # Check if current values violate expected correlation
                                if not np.isnan(historical_corr) and abs(historical_corr) > 0.5:
                                    val1 = current_metrics[metric1]
                                    val2 = current_metrics[metric2]
                                    
                                    # Simple correlation violation check
                                    mean1, mean2 = np.mean(values1), np.mean(values2)
                                    std1, std2 = np.std(values1), np.std(values2)
                                    
                                    normalized_val1 = (val1 - mean1) / (std1 + 1e-6)
                                    normalized_val2 = (val2 - mean2) / (std2 + 1e-6)
                                    
                                    expected_correlation_sign = np.sign(historical_corr)
                                    actual_correlation_sign = np.sign(normalized_val1 * normalized_val2)
                                    
                                    if expected_correlation_sign != actual_correlation_sign and abs(normalized_val1) > 2 and abs(normalized_val2) > 2:
                                        anomaly = Anomaly(
                                            id=f"pattern_corr_{metric1}_{metric2}_{int(timestamp.timestamp())}",
                                            timestamp=timestamp,
                                            anomaly_type=AnomalyType.COLLECTIVE_ANOMALY,
                                            severity=AnomalySeverity.MEDIUM,
                                            anomaly_score=0.7,
                                            affected_metrics=[metric1, metric2],
                                            metric_values={metric1: val1, metric2: val2},
                                            expected_values={metric1: mean1, metric2: mean2},
                                            deviation_percentage={},
                                            context={
                                                'historical_correlation': historical_corr,
                                                'expected_sign': expected_correlation_sign,
                                                'actual_sign': actual_correlation_sign
                                            },
                                            confidence=0.6,
                                            description=f"Correlation anomaly between {metric1} and {metric2}: "
                                                      f"violated expected correlation pattern"
                                        )
                                        
                                        anomalies.append(anomaly)
                                        
                            except Exception:
                                continue  # Skip if correlation calculation fails
                                
        except Exception as e:
            logger.error(f"Error in pattern anomaly detection: {e}")
        
        return anomalies
    
    def _filter_anomalies(self, anomalies: List[Anomaly]) -> List[Anomaly]:
        """Filter and deduplicate anomalies"""
        if not anomalies:
            return anomalies
        
        # Remove duplicates based on affected metrics and timestamp proximity
        filtered_anomalies = []
        
        for anomaly in anomalies:
            is_duplicate = False
            
            for existing in filtered_anomalies:
                # Check if same metrics are affected within 1 minute
                time_diff = abs((anomaly.timestamp - existing.timestamp).total_seconds())
                metric_overlap = set(anomaly.affected_metrics) & set(existing.affected_metrics)
                
                if time_diff < 60 and len(metric_overlap) > 0:
                    # Keep the one with higher anomaly score
                    if anomaly.anomaly_score > existing.anomaly_score:
                        filtered_anomalies.remove(existing)
                        filtered_anomalies.append(anomaly)
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                filtered_anomalies.append(anomaly)
        
        return filtered_anomalies
    
    def _update_statistical_baselines(self, current_metrics: Dict[str, float]):
        """Update statistical baselines for each metric"""
        if len(self.metrics_history) < 10:
            return
        
        # Calculate rolling statistics for each metric
        for metric_name in current_metrics.keys():
            values = []
            for data_point in list(self.metrics_history)[-50:]:  # Last 50 points
                if metric_name in data_point['metrics']:
                    values.append(data_point['metrics'][metric_name])
            
            if len(values) >= 10:
                self.statistical_baselines[metric_name] = {
                    'mean': np.mean(values),
                    'std': np.std(values),
                    'median': np.median(values),
                    'q25': np.percentile(values, 25),
                    'q75': np.percentile(values, 75),
                    'min': np.min(values),
                    'max': np.max(values)
                }
    
    def _update_adaptive_thresholds(self):
        """Update adaptive thresholds based on recent anomaly patterns"""
        # Simple adaptive threshold logic - can be enhanced
        recent_anomalies = [a for a in self.anomalies_history if 
                          (datetime.now() - a.timestamp).total_seconds() < 3600]  # Last hour
        
        if len(recent_anomalies) > 10:  # Too many anomalies - reduce sensitivity
            self.sensitivity = max(0.3, self.sensitivity - 0.1)
            logger.info(f"Reducing anomaly sensitivity to {self.sensitivity:.2f}")
        elif len(recent_anomalies) == 0 and len(self.metrics_history) > 100:  # No anomalies - increase sensitivity
            self.sensitivity = min(1.0, self.sensitivity + 0.05)
            logger.info(f"Increasing anomaly sensitivity to {self.sensitivity:.2f}")
    
    def _update_anomaly_patterns(self, new_anomalies: List[Anomaly]):
        """Update anomaly patterns based on new detections"""
        for anomaly in new_anomalies:
            # Simple pattern matching - look for similar anomalies
            pattern_key = f"{anomaly.anomaly_type.value}_{sorted(anomaly.affected_metrics)}"
            
            if pattern_key in self.anomaly_patterns:
                pattern = self.anomaly_patterns[pattern_key]
                pattern.last_detected = anomaly.timestamp
                pattern.occurrences += 1
            else:
                self.anomaly_patterns[pattern_key] = AnomalyPattern(
                    pattern_id=pattern_key,
                    pattern_type=anomaly.anomaly_type.value,
                    first_detected=anomaly.timestamp,
                    last_detected=anomaly.timestamp,
                    occurrences=1,
                    affected_metrics=anomaly.affected_metrics.copy(),
                    pattern_strength=anomaly.anomaly_score,
                    description=f"Pattern: {anomaly.anomaly_type.value} affecting {anomaly.affected_metrics}"
                )
    
    async def _initialize_models(self):
        """Initialize ML models for anomaly detection"""
        try:
            if len(self.metrics_history) < 50:
                return
            
            # Prepare training data
            training_data = []
            for data_point in list(self.metrics_history):
                metrics = data_point['metrics']
                
                # Create feature vector
                feature_vector = []
                for metric_name in sorted(metrics.keys()):
                    feature_vector.append(metrics[metric_name])
                
                if feature_vector:
                    training_data.append(feature_vector)
            
            if len(training_data) < 30:
                return
            
            X = np.array(training_data)
            
            # Fit scaler
            self.scaler.fit(X)
            X_scaled = self.scaler.transform(X)
            
            # Train Isolation Forest
            self.isolation_forest = IsolationForest(
                contamination=self.contamination_rate,
                random_state=42,
                n_estimators=100
            )
            self.isolation_forest.fit(X_scaled)
            
            logger.info(f"Anomaly detection models initialized with {len(X)} samples")
            
        except Exception as e:
            logger.error(f"Error initializing anomaly detection models: {e}")
    
    def get_anomaly_summary(self) -> Dict[str, Any]:
        """Get anomaly detection summary"""
        recent_anomalies = [a for a in self.anomalies_history if 
                          (datetime.now() - a.timestamp).total_seconds() < 3600]
        
        severity_counts = {}
        for severity in AnomalySeverity:
            severity_counts[severity.value] = len([a for a in recent_anomalies if a.severity == severity])
        
        return {
            "is_detecting": self.is_detecting,
            "total_anomalies_detected": len(self.anomalies_history),
            "recent_anomalies_1h": len(recent_anomalies),
            "severity_distribution": severity_counts,
            "anomaly_patterns": len(self.anomaly_patterns),
            "data_points": len(self.metrics_history),
            "current_sensitivity": self.sensitivity,
            "models_initialized": self.isolation_forest is not None
        }

# Global anomaly detector instance
anomaly_detector = AnomalyDetector()

async def start_anomaly_detection():
    """Start global anomaly detection"""
    await anomaly_detector.start_detection()

async def stop_anomaly_detection():
    """Stop global anomaly detection"""
    await anomaly_detector.stop_detection()
