#!/usr/bin/env python3
"""
Predictive Monitor
==================

AI-powered predictive monitoring system providing:
- Predictive health monitoring with early warning
- Performance trend prediction
- Risk escalation forecasting
- Proactive alert generation
- System behavior prediction

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
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class PredictionType(Enum):
    """Types of predictions"""
    PERFORMANCE_TREND = "performance_trend"
    HEALTH_STATUS = "health_status"
    RISK_ESCALATION = "risk_escalation"
    SYSTEM_FAILURE = "system_failure"
    ALERT_PROBABILITY = "alert_probability"

class PredictionConfidence(Enum):
    """Prediction confidence levels"""
    HIGH = "high"       # > 80%
    MEDIUM = "medium"   # 60-80%
    LOW = "low"         # < 60%

class AlertProbability(Enum):
    """Alert probability levels"""
    VERY_HIGH = "very_high"  # > 90%
    HIGH = "high"            # 70-90%
    MEDIUM = "medium"        # 40-70%
    LOW = "low"              # < 40%

@dataclass
class PredictiveAlert:
    """Predictive alert data structure"""
    timestamp: datetime
    prediction_type: PredictionType
    predicted_value: float
    confidence: PredictionConfidence
    alert_probability: AlertProbability
    time_horizon: int  # Hours until predicted event
    description: str
    recommended_actions: List[str]
    risk_factors: List[str]

@dataclass
class SystemPrediction:
    """System behavior prediction"""
    timestamp: datetime
    prediction_horizon: int  # Hours
    predicted_metrics: Dict[str, float]
    confidence_scores: Dict[str, float]
    trend_direction: str  # 'improving', 'stable', 'degrading'
    risk_score: float  # 0-1
    early_warnings: List[str]

@dataclass
class TrendPrediction:
    """Performance trend prediction"""
    metric_name: str
    current_value: float
    predicted_values: List[float]  # Next N periods
    confidence_intervals: List[Tuple[float, float]]
    trend_strength: float  # 0-1
    trend_direction: str
    reversal_probability: float

class PredictiveMonitor:
    """
    AI-powered predictive monitoring system.
    
    Features:
    - Performance trend prediction using Gradient Boosting
    - Health status forecasting
    - Risk escalation early warning
    - Proactive alert generation
    - System behavior prediction
    - Adaptive threshold adjustment
    """
    
    def __init__(
        self,
        prediction_horizons: List[int] = [1, 6, 24, 72],  # Hours
        history_window: int = 500,
        retrain_frequency: int = 48,  # Hours
        confidence_threshold: float = 0.6
    ):
        self.prediction_horizons = prediction_horizons
        self.history_window = history_window
        self.retrain_frequency = retrain_frequency
        self.confidence_threshold = confidence_threshold
        
        # Data storage
        self.metrics_history: deque = deque(maxlen=history_window)
        self.predictions_history: deque = deque(maxlen=200)
        self.alerts_history: deque = deque(maxlen=100)
        
        # ML Models for different prediction types
        self.trend_models: Dict[str, GradientBoostingRegressor] = {}
        self.classification_models: Dict[str, GradientBoostingClassifier] = {}
        self.scalers: Dict[str, StandardScaler] = {}
        
        # Monitoring state
        self.is_monitoring = False
        self.monitoring_task: Optional[asyncio.Task] = None
        self.prediction_lock = threading.RLock()
        
        # Model training state
        self.models_last_trained: Optional[datetime] = None
        
        # Adaptive thresholds
        self.adaptive_thresholds: Dict[str, float] = {
            'performance_degradation': 0.7,
            'health_risk': 0.6,
            'system_failure': 0.8,
            'alert_escalation': 0.75
        }
        
        logger.info("PredictiveMonitor initialized")
    
    async def start_monitoring(self):
        """Start predictive monitoring"""
        if self.is_monitoring:
            logger.warning("Predictive monitoring already active")
            return
        
        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        # Initialize models if we have enough data
        if len(self.metrics_history) > 50:
            await self._initialize_models()
        
        logger.info("Predictive monitoring started")
    
    async def stop_monitoring(self):
        """Stop predictive monitoring"""
        self.is_monitoring = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Predictive monitoring stopped")
    
    def add_metrics_data(self, timestamp: datetime, metrics: Dict[str, float]):
        """Add new metrics data for prediction"""
        with self.prediction_lock:
            data_point = {
                'timestamp': timestamp,
                'metrics': metrics.copy()
            }
            self.metrics_history.append(data_point)
            
            # Check if we should retrain models
            if self._should_retrain():
                asyncio.create_task(self._retrain_models())
    
    async def generate_predictions(self) -> Dict[str, Any]:
        """Generate comprehensive predictions"""
        if len(self.metrics_history) < 30:
            return {"status": "insufficient_data", "predictions": []}
        
        with self.prediction_lock:
            predictions = {}
            
            # Generate trend predictions
            trend_predictions = await self._predict_performance_trends()
            predictions['trend_predictions'] = trend_predictions
            
            # Generate system behavior predictions
            system_predictions = await self._predict_system_behavior()
            predictions['system_predictions'] = system_predictions
            
            # Generate risk predictions
            risk_predictions = await self._predict_risk_escalation()
            predictions['risk_predictions'] = risk_predictions
            
            # Generate proactive alerts
            proactive_alerts = await self._generate_proactive_alerts()
            predictions['proactive_alerts'] = proactive_alerts
            
            predictions['timestamp'] = datetime.now()
            predictions['status'] = "success"
            
            return predictions
    
    async def _predict_performance_trends(self) -> List[TrendPrediction]:
        """Predict performance trends for key metrics"""
        trend_predictions = []
        
        try:
            recent_data = list(self.metrics_history)[-50:]  # Last 50 data points
            
            if len(recent_data) < 20:
                return trend_predictions
            
            # Key metrics to predict
            key_metrics = ['cpu_usage', 'memory_usage', 'latency', 'throughput', 'error_rate']
            
            for metric in key_metrics:
                # Extract metric values
                values = []
                for data_point in recent_data:
                    if metric in data_point['metrics']:
                        values.append(data_point['metrics'][metric])
                
                if len(values) < 10:
                    continue
                
                # Simple trend prediction using linear regression
                x = np.arange(len(values))
                y = np.array(values)
                
                # Fit trend
                trend_coef = np.polyfit(x, y, 1)[0]
                
                # Predict next 5 periods
                predicted_values = []
                confidence_intervals = []
                
                for i in range(1, 6):
                    pred_value = y[-1] + trend_coef * i
                    
                    # Simple confidence interval (±2 standard deviations)
                    std_error = np.std(y) * np.sqrt(1 + 1/len(y))
                    ci_lower = pred_value - 2 * std_error
                    ci_upper = pred_value + 2 * std_error
                    
                    predicted_values.append(pred_value)
                    confidence_intervals.append((ci_lower, ci_upper))
                
                # Determine trend characteristics
                trend_strength = min(abs(trend_coef) * 100, 1.0)
                trend_direction = "increasing" if trend_coef > 0 else "decreasing"
                
                # Calculate reversal probability (simplified)
                recent_volatility = np.std(y[-10:])
                reversal_prob = min(recent_volatility * 5, 0.9)
                
                trend_prediction = TrendPrediction(
                    metric_name=metric,
                    current_value=float(y[-1]),
                    predicted_values=predicted_values,
                    confidence_intervals=confidence_intervals,
                    trend_strength=trend_strength,
                    trend_direction=trend_direction,
                    reversal_probability=reversal_prob
                )
                
                trend_predictions.append(trend_prediction)
                
        except Exception as e:
            logger.error(f"Error predicting trends: {e}")
        
        return trend_predictions
    
    async def _predict_system_behavior(self) -> List[SystemPrediction]:
        """Predict overall system behavior"""
        system_predictions = []
        
        try:
            recent_data = list(self.metrics_history)[-24:]  # Last 24 hours
            
            if len(recent_data) < 10:
                return system_predictions
            
            for horizon in self.prediction_horizons:
                # Aggregate current metrics
                current_metrics = {}
                for metric_name in ['cpu_usage', 'memory_usage', 'latency', 'error_rate']:
                    values = []
                    for data_point in recent_data[-5:]:  # Last 5 points
                        if metric_name in data_point['metrics']:
                            values.append(data_point['metrics'][metric_name])
                    
                    if values:
                        current_metrics[metric_name] = np.mean(values)
                
                # Simple prediction based on trends
                predicted_metrics = {}
                confidence_scores = {}
                
                for metric_name, current_value in current_metrics.items():
                    # Extract historical values
                    hist_values = []
                    for data_point in recent_data:
                        if metric_name in data_point['metrics']:
                            hist_values.append(data_point['metrics'][metric_name])
                    
                    if len(hist_values) >= 5:
                        # Simple trend-based prediction
                        trend = np.polyfit(range(len(hist_values)), hist_values, 1)[0]
                        predicted_value = current_value + trend * horizon
                        
                        # Confidence based on trend consistency
                        r_squared = np.corrcoef(range(len(hist_values)), hist_values)[0, 1] ** 2
                        confidence = min(max(r_squared, 0.3), 0.95)
                        
                        predicted_metrics[metric_name] = predicted_value
                        confidence_scores[metric_name] = confidence
                
                # Determine overall trend direction
                avg_trend = np.mean([
                    (predicted_metrics.get(m, current_metrics.get(m, 0)) - current_metrics.get(m, 0))
                    for m in current_metrics.keys()
                ])
                
                if avg_trend > 0.05:
                    trend_direction = "degrading"
                elif avg_trend < -0.05:
                    trend_direction = "improving"
                else:
                    trend_direction = "stable"
                
                # Calculate risk score
                risk_factors = []
                if predicted_metrics.get('cpu_usage', 0) > 80:
                    risk_factors.append("High CPU usage predicted")
                if predicted_metrics.get('memory_usage', 0) > 85:
                    risk_factors.append("High memory usage predicted")
                if predicted_metrics.get('error_rate', 0) > 0.05:
                    risk_factors.append("Elevated error rate predicted")
                
                risk_score = min(len(risk_factors) * 0.3, 1.0)
                
                system_prediction = SystemPrediction(
                    timestamp=datetime.now(),
                    prediction_horizon=horizon,
                    predicted_metrics=predicted_metrics,
                    confidence_scores=confidence_scores,
                    trend_direction=trend_direction,
                    risk_score=risk_score,
                    early_warnings=risk_factors
                )
                
                system_predictions.append(system_prediction)
                
        except Exception as e:
            logger.error(f"Error predicting system behavior: {e}")
        
        return system_predictions
    
    async def _predict_risk_escalation(self) -> Dict[str, float]:
        """Predict risk escalation probabilities"""
        risk_predictions = {
            'performance_degradation': 0.0,
            'system_overload': 0.0,
            'failure_probability': 0.0,
            'alert_storm': 0.0
        }
        
        try:
            recent_data = list(self.metrics_history)[-20:]
            
            if len(recent_data) < 10:
                return risk_predictions
            
            # Extract key metrics
            cpu_values = []
            memory_values = []
            latency_values = []
            error_values = []
            
            for data_point in recent_data:
                metrics = data_point['metrics']
                if 'cpu_usage' in metrics:
                    cpu_values.append(metrics['cpu_usage'])
                if 'memory_usage' in metrics:
                    memory_values.append(metrics['memory_usage'])
                if 'latency' in metrics:
                    latency_values.append(metrics['latency'])
                if 'error_rate' in metrics:
                    error_values.append(metrics['error_rate'])
            
            # Performance degradation risk
            if cpu_values and memory_values:
                cpu_trend = np.polyfit(range(len(cpu_values)), cpu_values, 1)[0]
                memory_trend = np.polyfit(range(len(memory_values)), memory_values, 1)[0]
                
                # Risk increases with upward trends in resource usage
                perf_risk = 0.0
                if cpu_trend > 1.0:  # CPU increasing by 1% per period
                    perf_risk += 0.3
                if memory_trend > 1.0:  # Memory increasing by 1% per period
                    perf_risk += 0.3
                if cpu_values[-1] > 70:  # Current CPU > 70%
                    perf_risk += 0.2
                if memory_values[-1] > 80:  # Current memory > 80%
                    perf_risk += 0.2
                
                risk_predictions['performance_degradation'] = min(perf_risk, 1.0)
            
            # System overload risk
            overload_risk = 0.0
            if cpu_values and memory_values:
                recent_cpu = np.mean(cpu_values[-5:])
                recent_memory = np.mean(memory_values[-5:])
                
                if recent_cpu > 85:
                    overload_risk += 0.4
                if recent_memory > 90:
                    overload_risk += 0.4
                if recent_cpu > 95 or recent_memory > 95:
                    overload_risk += 0.3
                
                risk_predictions['system_overload'] = min(overload_risk, 1.0)
            
            # Failure probability
            failure_risk = 0.0
            if error_values:
                recent_errors = np.mean(error_values[-5:])
                error_trend = np.polyfit(range(len(error_values)), error_values, 1)[0]
                
                if recent_errors > 0.1:  # > 10% error rate
                    failure_risk += 0.5
                if error_trend > 0.01:  # Increasing error trend
                    failure_risk += 0.3
                
                risk_predictions['failure_probability'] = min(failure_risk, 1.0)
            
            # Alert storm risk (simplified)
            if len(recent_data) >= 10:
                # Check for rapid metric changes
                volatility_score = 0.0
                for metric_name in ['cpu_usage', 'memory_usage', 'latency']:
                    values = [d['metrics'].get(metric_name, 0) for d in recent_data[-10:]]
                    if len(values) > 5:
                        volatility = np.std(values) / (np.mean(values) + 1e-6)
                        volatility_score += min(volatility * 10, 0.3)
                
                risk_predictions['alert_storm'] = min(volatility_score, 1.0)
                
        except Exception as e:
            logger.error(f"Error predicting risk escalation: {e}")
        
        return risk_predictions
    
    async def _generate_proactive_alerts(self) -> List[PredictiveAlert]:
        """Generate proactive alerts based on predictions"""
        proactive_alerts = []
        
        try:
            # Get risk predictions
            risk_predictions = await self._predict_risk_escalation()
            
            # Generate alerts for high-risk scenarios
            for risk_type, risk_score in risk_predictions.items():
                if risk_score > self.adaptive_thresholds.get(risk_type, 0.7):
                    
                    # Determine confidence level
                    if risk_score > 0.8:
                        confidence = PredictionConfidence.HIGH
                        alert_prob = AlertProbability.VERY_HIGH
                    elif risk_score > 0.6:
                        confidence = PredictionConfidence.MEDIUM
                        alert_prob = AlertProbability.HIGH
                    else:
                        confidence = PredictionConfidence.LOW
                        alert_prob = AlertProbability.MEDIUM
                    
                    # Estimate time horizon (simplified)
                    time_horizon = max(1, int((1.0 - risk_score) * 24))  # Hours
                    
                    # Generate recommendations
                    recommendations = self._get_risk_recommendations(risk_type, risk_score)
                    
                    # Identify risk factors
                    risk_factors = self._identify_risk_factors(risk_type)
                    
                    alert = PredictiveAlert(
                        timestamp=datetime.now(),
                        prediction_type=PredictionType.RISK_ESCALATION,
                        predicted_value=risk_score,
                        confidence=confidence,
                        alert_probability=alert_prob,
                        time_horizon=time_horizon,
                        description=f"Predicted {risk_type.replace('_', ' ')} risk: {risk_score:.1%}",
                        recommended_actions=recommendations,
                        risk_factors=risk_factors
                    )
                    
                    proactive_alerts.append(alert)
            
            # Store alerts in history
            with self.prediction_lock:
                self.alerts_history.extend(proactive_alerts)
                
        except Exception as e:
            logger.error(f"Error generating proactive alerts: {e}")
        
        return proactive_alerts
    
    def _get_risk_recommendations(self, risk_type: str, risk_score: float) -> List[str]:
        """Get recommended actions for risk type"""
        recommendations = []
        
        if risk_type == "performance_degradation":
            recommendations.extend([
                "Monitor CPU and memory usage closely",
                "Consider scaling up resources",
                "Review recent configuration changes",
                "Check for resource-intensive processes"
            ])
        
        elif risk_type == "system_overload":
            recommendations.extend([
                "Prepare for load balancing",
                "Review system capacity limits",
                "Consider emergency scaling procedures",
                "Monitor system stability metrics"
            ])
        
        elif risk_type == "failure_probability":
            recommendations.extend([
                "Increase monitoring frequency",
                "Prepare backup systems",
                "Review error logs for patterns",
                "Consider preventive maintenance"
            ])
        
        elif risk_type == "alert_storm":
            recommendations.extend([
                "Review alert thresholds",
                "Prepare alert aggregation",
                "Check system stability",
                "Consider temporary alert suppression"
            ])
        
        return recommendations
    
    def _identify_risk_factors(self, risk_type: str) -> List[str]:
        """Identify contributing risk factors"""
        risk_factors = []
        
        if len(self.metrics_history) < 5:
            return risk_factors
        
        recent_data = list(self.metrics_history)[-5:]
        
        # Analyze recent metrics for risk factors
        for data_point in recent_data:
            metrics = data_point['metrics']
            
            if metrics.get('cpu_usage', 0) > 80:
                risk_factors.append("High CPU usage detected")
            if metrics.get('memory_usage', 0) > 85:
                risk_factors.append("High memory usage detected")
            if metrics.get('error_rate', 0) > 0.05:
                risk_factors.append("Elevated error rate")
            if metrics.get('latency', 0) > 1000:  # > 1 second
                risk_factors.append("High latency detected")
        
        return list(set(risk_factors))  # Remove duplicates
    
    async def _monitoring_loop(self):
        """Main predictive monitoring loop"""
        while self.is_monitoring:
            try:
                # Generate predictions periodically
                if len(self.metrics_history) > 10:
                    predictions = await self.generate_predictions()
                    
                    # Log summary
                    if predictions.get('status') == 'success':
                        alerts_count = len(predictions.get('proactive_alerts', []))
                        if alerts_count > 0:
                            logger.info(f"Generated {alerts_count} proactive alerts")
                
                # Check for model retraining
                if self._should_retrain():
                    await self._retrain_models()
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in predictive monitoring loop: {e}")
                await asyncio.sleep(300)
    
    async def _initialize_models(self):
        """Initialize ML models"""
        logger.info("Initializing predictive models")
        # Placeholder for model initialization
        self.models_last_trained = datetime.now()
    
    async def _retrain_models(self):
        """Retrain predictive models"""
        logger.info("Retraining predictive models")
        # Placeholder for model retraining
        self.models_last_trained = datetime.now()
    
    def _should_retrain(self) -> bool:
        """Check if models should be retrained"""
        if self.models_last_trained is None:
            return True
        
        hours_since_training = (datetime.now() - self.models_last_trained).total_seconds() / 3600
        return hours_since_training >= self.retrain_frequency
    
    def get_monitoring_summary(self) -> Dict[str, Any]:
        """Get predictive monitoring summary"""
        return {
            "is_monitoring": self.is_monitoring,
            "data_points": len(self.metrics_history),
            "predictions_generated": len(self.predictions_history),
            "proactive_alerts": len(self.alerts_history),
            "models_last_trained": self.models_last_trained.isoformat() if self.models_last_trained else None,
            "adaptive_thresholds": self.adaptive_thresholds,
            "prediction_horizons": self.prediction_horizons
        }

# Global predictive monitor instance
predictive_monitor = PredictiveMonitor()

async def start_predictive_monitoring():
    """Start global predictive monitoring"""
    await predictive_monitor.start_monitoring()

async def stop_predictive_monitoring():
    """Stop global predictive monitoring"""
    await predictive_monitor.stop_monitoring()
