#!/usr/bin/env python3
"""
Performance Analyzer
===================

ML-powered performance analysis system providing:
- Predictive performance modeling
- Pattern recognition and trend analysis
- Performance anomaly detection
- Factor attribution analysis
- Real-time performance insights

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
from sklearn.ensemble import RandomForestRegressor, IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
import joblib

logger = logging.getLogger(__name__)

class PerformancePatternType(Enum):
    """Performance pattern types"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    MEAN_REVERTING = "mean_reverting"
    VOLATILE = "volatile"
    STABLE = "stable"
    BREAKOUT = "breakout"
    BREAKDOWN = "breakdown"

class PerformanceAlert(Enum):
    """Performance alert levels"""
    EXCEPTIONAL = "exceptional"  # Unusually good performance
    NORMAL = "normal"
    WARNING = "warning"  # Performance degradation
    CRITICAL = "critical"  # Severe underperformance

@dataclass
class PerformanceMetrics:
    """Performance metrics data structure"""
    timestamp: datetime
    returns: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    calmar_ratio: float
    sortino_ratio: float
    var_95: float
    cvar_95: float

@dataclass
class PerformanceForecast:
    """Performance forecast data structure"""
    timestamp: datetime
    forecast_horizon: int  # Days
    expected_return: float
    expected_volatility: float
    confidence_interval: Tuple[float, float]
    forecast_confidence: float
    pattern_type: PerformancePatternType

@dataclass
class PerformancePattern:
    """Detected performance pattern"""
    pattern_type: PerformancePatternType
    confidence: float
    start_date: datetime
    duration_days: int
    strength: float  # Pattern strength 0-1
    description: str

@dataclass
class PerformanceAnomaly:
    """Performance anomaly detection result"""
    timestamp: datetime
    anomaly_score: float  # Higher = more anomalous
    anomaly_type: str
    severity: PerformanceAlert
    description: str
    affected_metrics: List[str]

class PerformanceAnalyzer:
    """
    Advanced ML-powered performance analysis system.
    
    Features:
    - Predictive performance modeling using Random Forest
    - Real-time pattern recognition
    - Anomaly detection using Isolation Forest
    - Performance forecasting with confidence intervals
    - Factor attribution analysis
    - Adaptive model retraining
    """
    
    def __init__(
        self,
        history_window: int = 252,  # 1 year of daily data
        forecast_horizon: int = 5,  # 5-day forecasts
        retrain_frequency: int = 30,  # Retrain every 30 days
        anomaly_threshold: float = 0.1  # Top 10% as anomalies
    ):
        self.history_window = history_window
        self.forecast_horizon = forecast_horizon
        self.retrain_frequency = retrain_frequency
        self.anomaly_threshold = anomaly_threshold
        
        # Data storage
        self.performance_history: deque = deque(maxlen=history_window * 2)  # Extra buffer
        self.forecasts_history: deque = deque(maxlen=100)
        self.patterns_history: deque = deque(maxlen=50)
        self.anomalies_history: deque = deque(maxlen=100)
        
        # ML Models
        self.performance_model: Optional[RandomForestRegressor] = None
        self.anomaly_model: Optional[IsolationForest] = None
        self.scaler = StandardScaler()
        
        # Model state
        self.model_last_trained: Optional[datetime] = None
        self.is_analyzing = False
        self.analysis_lock = threading.RLock()
        
        # Analysis parameters
        self.feature_names = [
            'returns_1d', 'returns_5d', 'returns_20d',
            'volatility_5d', 'volatility_20d',
            'rsi_14', 'momentum_10', 'momentum_20',
            'max_drawdown_20d', 'win_rate_20d',
            'sharpe_5d', 'sharpe_20d'
        ]
        
        logger.info("PerformanceAnalyzer initialized")
    
    async def start_analysis(self):
        """Start performance analysis"""
        if self.is_analyzing:
            logger.warning("Performance analysis already active")
            return
        
        self.is_analyzing = True
        
        # Initialize models if we have enough data
        await self._initialize_models()
        
        logger.info("Performance analysis started")
    
    async def stop_analysis(self):
        """Stop performance analysis"""
        self.is_analyzing = False
        logger.info("Performance analysis stopped")
    
    def add_performance_data(self, metrics: PerformanceMetrics):
        """Add new performance data point"""
        with self.analysis_lock:
            self.performance_history.append(metrics)
            
            # Trigger retraining if needed
            if self._should_retrain():
                asyncio.create_task(self._retrain_models())
    
    async def analyze_current_performance(self) -> Dict[str, Any]:
        """Analyze current performance state"""
        if len(self.performance_history) < 20:
            return {"status": "insufficient_data", "message": "Need at least 20 data points"}
        
        with self.analysis_lock:
            # Get recent data
            recent_data = list(self.performance_history)[-50:]  # Last 50 periods
            
            # Detect patterns
            current_pattern = await self._detect_performance_pattern(recent_data)
            
            # Generate forecast
            forecast = await self._generate_performance_forecast()
            
            # Detect anomalies
            anomalies = await self._detect_performance_anomalies(recent_data[-5:])
            
            # Calculate performance indicators
            indicators = self._calculate_performance_indicators(recent_data)
            
            return {
                "timestamp": datetime.now(),
                "current_pattern": current_pattern,
                "forecast": forecast,
                "anomalies": anomalies,
                "indicators": indicators,
                "data_points": len(self.performance_history),
                "model_last_trained": self.model_last_trained
            }
    
    async def _detect_performance_pattern(self, data: List[PerformanceMetrics]) -> PerformancePattern:
        """Detect current performance pattern"""
        if len(data) < 10:
            return PerformancePattern(
                pattern_type=PerformancePatternType.STABLE,
                confidence=0.0,
                start_date=datetime.now(),
                duration_days=0,
                strength=0.0,
                description="Insufficient data for pattern detection"
            )
        
        # Extract returns series
        returns = np.array([d.returns for d in data])
        volatility = np.array([d.volatility for d in data])
        
        # Pattern detection logic
        pattern_type = PerformancePatternType.STABLE
        confidence = 0.5
        strength = 0.0
        
        # Trend analysis
        trend_slope = np.polyfit(range(len(returns)), returns, 1)[0]
        trend_r2 = np.corrcoef(range(len(returns)), returns)[0, 1] ** 2
        
        # Volatility analysis
        vol_mean = np.mean(volatility)
        vol_std = np.std(volatility)
        
        # Pattern classification
        if trend_r2 > 0.3:  # Strong trend
            if trend_slope > 0.001:  # 0.1% daily
                pattern_type = PerformancePatternType.TRENDING_UP
                strength = min(trend_slope * 100, 1.0)
            elif trend_slope < -0.001:
                pattern_type = PerformancePatternType.TRENDING_DOWN
                strength = min(abs(trend_slope) * 100, 1.0)
            confidence = trend_r2
            
        elif vol_mean > 0.02:  # High volatility (2% daily)
            pattern_type = PerformancePatternType.VOLATILE
            strength = min(vol_mean * 10, 1.0)
            confidence = 0.7
            
        elif np.std(returns) < 0.005:  # Very low volatility
            pattern_type = PerformancePatternType.STABLE
            strength = 1.0 - min(np.std(returns) * 100, 1.0)
            confidence = 0.8
            
        # Mean reversion detection
        else:
            autocorr = np.corrcoef(returns[:-1], returns[1:])[0, 1]
            if autocorr < -0.2:  # Negative autocorrelation
                pattern_type = PerformancePatternType.MEAN_REVERTING
                strength = abs(autocorr)
                confidence = 0.6
        
        # Breakout detection (simplified)
        recent_returns = returns[-5:]
        if len(recent_returns) == 5:
            if np.all(recent_returns > 0) and np.mean(recent_returns) > 0.01:
                pattern_type = PerformancePatternType.BREAKOUT
                strength = min(np.mean(recent_returns) * 50, 1.0)
                confidence = 0.8
            elif np.all(recent_returns < 0) and np.mean(recent_returns) < -0.01:
                pattern_type = PerformancePatternType.BREAKDOWN
                strength = min(abs(np.mean(recent_returns)) * 50, 1.0)
                confidence = 0.8
        
        return PerformancePattern(
            pattern_type=pattern_type,
            confidence=confidence,
            start_date=data[-len(data)//2].timestamp,  # Approximate start
            duration_days=len(data),
            strength=strength,
            description=f"{pattern_type.value} pattern detected with {confidence:.1%} confidence"
        )
    
    async def _generate_performance_forecast(self) -> Optional[PerformanceForecast]:
        """Generate performance forecast using ML model"""
        if self.performance_model is None or len(self.performance_history) < 50:
            return None
        
        try:
            # Prepare features
            features = self._extract_features(list(self.performance_history)[-50:])
            if features is None:
                return None
            
            # Scale features
            features_scaled = self.scaler.transform([features])
            
            # Generate prediction
            prediction = self.performance_model.predict(features_scaled)[0]
            
            # Calculate confidence (simplified - based on recent model performance)
            confidence = min(0.95, max(0.3, 0.8 - abs(prediction) * 10))
            
            # Generate confidence interval (simplified)
            std_error = 0.01  # 1% standard error assumption
            ci_lower = prediction - 1.96 * std_error
            ci_upper = prediction + 1.96 * std_error
            
            # Estimate volatility
            recent_vol = np.mean([d.volatility for d in list(self.performance_history)[-20:]])
            
            # Determine pattern type based on prediction
            if prediction > 0.005:
                pattern_type = PerformancePatternType.TRENDING_UP
            elif prediction < -0.005:
                pattern_type = PerformancePatternType.TRENDING_DOWN
            else:
                pattern_type = PerformancePatternType.STABLE
            
            return PerformanceForecast(
                timestamp=datetime.now(),
                forecast_horizon=self.forecast_horizon,
                expected_return=prediction,
                expected_volatility=recent_vol,
                confidence_interval=(ci_lower, ci_upper),
                forecast_confidence=confidence,
                pattern_type=pattern_type
            )
            
        except Exception as e:
            logger.error(f"Error generating forecast: {e}")
            return None
    
    async def _detect_performance_anomalies(self, recent_data: List[PerformanceMetrics]) -> List[PerformanceAnomaly]:
        """Detect performance anomalies"""
        anomalies = []
        
        if len(recent_data) < 3:
            return anomalies
        
        try:
            # Simple anomaly detection based on statistical thresholds
            current = recent_data[-1]
            historical = list(self.performance_history)
            
            if len(historical) < 30:
                return anomalies
            
            # Calculate historical statistics
            hist_returns = [d.returns for d in historical[-30:]]
            hist_vol = [d.volatility for d in historical[-30:]]
            hist_sharpe = [d.sharpe_ratio for d in historical[-30:] if d.sharpe_ratio is not None]
            
            mean_return = np.mean(hist_returns)
            std_return = np.std(hist_returns)
            mean_vol = np.mean(hist_vol)
            std_vol = np.std(hist_vol)
            
            # Return anomaly detection
            if abs(current.returns - mean_return) > 3 * std_return:
                severity = PerformanceAlert.CRITICAL if abs(current.returns - mean_return) > 4 * std_return else PerformanceAlert.WARNING
                anomalies.append(PerformanceAnomaly(
                    timestamp=current.timestamp,
                    anomaly_score=abs(current.returns - mean_return) / std_return,
                    anomaly_type="return_anomaly",
                    severity=severity,
                    description=f"Unusual return: {current.returns:.2%} vs expected {mean_return:.2%}",
                    affected_metrics=["returns"]
                ))
            
            # Volatility anomaly detection
            if abs(current.volatility - mean_vol) > 2 * std_vol:
                severity = PerformanceAlert.WARNING if current.volatility > mean_vol else PerformanceAlert.NORMAL
                anomalies.append(PerformanceAnomaly(
                    timestamp=current.timestamp,
                    anomaly_score=abs(current.volatility - mean_vol) / std_vol,
                    anomaly_type="volatility_anomaly",
                    severity=severity,
                    description=f"Unusual volatility: {current.volatility:.2%} vs expected {mean_vol:.2%}",
                    affected_metrics=["volatility"]
                ))
            
            # Exceptional performance detection
            if len(hist_sharpe) > 10 and current.sharpe_ratio is not None:
                mean_sharpe = np.mean(hist_sharpe)
                if current.sharpe_ratio > mean_sharpe + 1.0:
                    anomalies.append(PerformanceAnomaly(
                        timestamp=current.timestamp,
                        anomaly_score=current.sharpe_ratio - mean_sharpe,
                        anomaly_type="exceptional_performance",
                        severity=PerformanceAlert.EXCEPTIONAL,
                        description=f"Exceptional Sharpe ratio: {current.sharpe_ratio:.2f}",
                        affected_metrics=["sharpe_ratio"]
                    ))
            
        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
        
        return anomalies
    
    def _calculate_performance_indicators(self, data: List[PerformanceMetrics]) -> Dict[str, Any]:
        """Calculate various performance indicators"""
        if len(data) < 5:
            return {}
        
        returns = np.array([d.returns for d in data])
        volatility = np.array([d.volatility for d in data])
        
        return {
            "current_momentum": np.mean(returns[-5:]) if len(returns) >= 5 else 0.0,
            "momentum_20d": np.mean(returns[-20:]) if len(returns) >= 20 else 0.0,
            "volatility_trend": (volatility[-1] - np.mean(volatility[:-1])) if len(volatility) > 1 else 0.0,
            "consistency_score": 1.0 - (np.std(returns) / (abs(np.mean(returns)) + 1e-6)),
            "recent_win_rate": np.mean(returns[-10:] > 0) if len(returns) >= 10 else 0.5,
            "trend_strength": abs(np.corrcoef(range(len(returns)), returns)[0, 1]) if len(returns) > 2 else 0.0,
            "max_consecutive_wins": self._max_consecutive(returns > 0),
            "max_consecutive_losses": self._max_consecutive(returns < 0)
        }
    
    def _max_consecutive(self, boolean_array: np.ndarray) -> int:
        """Calculate maximum consecutive True values"""
        if len(boolean_array) == 0:
            return 0
        
        max_count = current_count = 0
        for value in boolean_array:
            if value:
                current_count += 1
                max_count = max(max_count, current_count)
            else:
                current_count = 0
        
        return max_count
    
    def _extract_features(self, data: List[PerformanceMetrics]) -> Optional[List[float]]:
        """Extract ML features from performance data"""
        if len(data) < 20:
            return None
        
        try:
            returns = np.array([d.returns for d in data])
            volatility = np.array([d.volatility for d in data])
            
            features = []
            
            # Return features
            features.append(returns[-1])  # 1d return
            features.append(np.mean(returns[-5:]))  # 5d average return
            features.append(np.mean(returns[-20:]))  # 20d average return
            
            # Volatility features
            features.append(np.mean(volatility[-5:]))  # 5d volatility
            features.append(np.mean(volatility[-20:]))  # 20d volatility
            
            # Technical indicators
            features.append(self._calculate_rsi(returns, 14))  # RSI
            features.append(np.mean(returns[-10:]))  # 10d momentum
            features.append(np.mean(returns[-20:]))  # 20d momentum
            
            # Risk metrics
            drawdowns = np.array([d.max_drawdown for d in data[-20:]])
            features.append(np.mean(drawdowns))  # 20d average max drawdown
            
            win_rates = np.array([d.win_rate for d in data[-20:]])
            features.append(np.mean(win_rates))  # 20d average win rate
            
            # Sharpe ratios
            sharpe_5d = np.mean([d.sharpe_ratio for d in data[-5:] if d.sharpe_ratio is not None])
            sharpe_20d = np.mean([d.sharpe_ratio for d in data[-20:] if d.sharpe_ratio is not None])
            features.append(sharpe_5d if not np.isnan(sharpe_5d) else 0.0)
            features.append(sharpe_20d if not np.isnan(sharpe_20d) else 0.0)
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting features: {e}")
            return None
    
    def _calculate_rsi(self, returns: np.ndarray, period: int = 14) -> float:
        """Calculate RSI (Relative Strength Index)"""
        if len(returns) < period + 1:
            return 50.0  # Neutral RSI
        
        try:
            gains = np.where(returns > 0, returns, 0)
            losses = np.where(returns < 0, -returns, 0)
            
            avg_gain = np.mean(gains[-period:])
            avg_loss = np.mean(losses[-period:])
            
            if avg_loss == 0:
                return 100.0
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
            
        except Exception:
            return 50.0
    
    async def _initialize_models(self):
        """Initialize ML models"""
        if len(self.performance_history) < 50:
            logger.info("Insufficient data for model initialization")
            return
        
        await self._train_performance_model()
        await self._train_anomaly_model()
        
        self.model_last_trained = datetime.now()
        logger.info("ML models initialized")
    
    async def _train_performance_model(self):
        """Train performance prediction model"""
        try:
            data = list(self.performance_history)
            if len(data) < 50:
                return
            
            # Prepare training data
            features_list = []
            targets = []
            
            for i in range(20, len(data) - self.forecast_horizon):
                features = self._extract_features(data[i-20:i])
                if features is not None:
                    target = np.mean([d.returns for d in data[i:i+self.forecast_horizon]])
                    features_list.append(features)
                    targets.append(target)
            
            if len(features_list) < 20:
                logger.warning("Insufficient training samples")
                return
            
            X = np.array(features_list)
            y = np.array(targets)
            
            # Scale features
            X_scaled = self.scaler.fit_transform(X)
            
            # Train model
            self.performance_model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
            
            self.performance_model.fit(X_scaled, y)
            
            logger.info(f"Performance model trained on {len(X)} samples")
            
        except Exception as e:
            logger.error(f"Error training performance model: {e}")
    
    async def _train_anomaly_model(self):
        """Train anomaly detection model"""
        try:
            data = list(self.performance_history)
            if len(data) < 30:
                return
            
            # Prepare features for anomaly detection
            features_list = []
            
            for i in range(20, len(data)):
                features = self._extract_features(data[i-20:i])
                if features is not None:
                    features_list.append(features)
            
            if len(features_list) < 20:
                return
            
            X = np.array(features_list)
            X_scaled = self.scaler.fit_transform(X)
            
            # Train anomaly detection model
            self.anomaly_model = IsolationForest(
                contamination=self.anomaly_threshold,
                random_state=42
            )
            
            self.anomaly_model.fit(X_scaled)
            
            logger.info(f"Anomaly model trained on {len(X)} samples")
            
        except Exception as e:
            logger.error(f"Error training anomaly model: {e}")
    
    def _should_retrain(self) -> bool:
        """Check if models should be retrained"""
        if self.model_last_trained is None:
            return True
        
        days_since_training = (datetime.now() - self.model_last_trained).days
        return days_since_training >= self.retrain_frequency
    
    async def _retrain_models(self):
        """Retrain ML models"""
        logger.info("Starting model retraining")
        
        try:
            await self._train_performance_model()
            await self._train_anomaly_model()
            self.model_last_trained = datetime.now()
            
            logger.info("Model retraining completed")
            
        except Exception as e:
            logger.error(f"Error during model retraining: {e}")
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get analysis system summary"""
        return {
            "is_analyzing": self.is_analyzing,
            "data_points": len(self.performance_history),
            "model_trained": self.performance_model is not None,
            "last_training": self.model_last_trained.isoformat() if self.model_last_trained else None,
            "forecast_horizon": self.forecast_horizon,
            "patterns_detected": len(self.patterns_history),
            "anomalies_detected": len(self.anomalies_history),
            "forecasts_generated": len(self.forecasts_history)
        }

# Global performance analyzer instance
performance_analyzer = PerformanceAnalyzer()

async def start_performance_analysis():
    """Start global performance analysis"""
    await performance_analyzer.start_analysis()

async def stop_performance_analysis():
    """Stop global performance analysis"""
    await performance_analyzer.stop_analysis()
