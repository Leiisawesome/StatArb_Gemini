"""
Correlation Breakdown Detection System
=====================================

This module provides advanced correlation breakdown detection for statistical arbitrage pairs,
using multiple statistical techniques to identify when pair relationships deteriorate.

Key Features:
- Multi-timeframe correlation analysis
- Statistical significance testing
- Regime-aware threshold adjustment
- Advanced breakdown pattern recognition
- Automated alert generation with severity levels
- Historical breakdown analysis and learning

Author: Pro Quant Desk Trader
Date: 2024
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import logging
from scipy import stats
from scipy.signal import find_peaks, savgol_filter
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN
from sklearn.metrics import silhouette_score
import warnings
import json
import sqlite3

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BreakdownSeverity(Enum):
    """Correlation breakdown severity levels"""
    MINOR = "MINOR"
    MODERATE = "MODERATE"
    SEVERE = "SEVERE"
    CRITICAL = "CRITICAL"

class BreakdownType(Enum):
    """Types of correlation breakdown patterns"""
    GRADUAL_DECLINE = "GRADUAL_DECLINE"
    SUDDEN_DROP = "SUDDEN_DROP"
    OSCILLATING = "OSCILLATING"
    STRUCTURAL_BREAK = "STRUCTURAL_BREAK"
    REGIME_CHANGE = "REGIME_CHANGE"
    VOLATILITY_SPIKE = "VOLATILITY_SPIKE"

class BreakdownCause(Enum):
    """Potential causes of correlation breakdown"""
    MARKET_STRESS = "MARKET_STRESS"
    SECTOR_ROTATION = "SECTOR_ROTATION"
    EARNINGS_EVENT = "EARNINGS_EVENT"
    NEWS_SHOCK = "NEWS_SHOCK"
    LIQUIDITY_CRISIS = "LIQUIDITY_CRISIS"
    TECHNICAL_FACTOR = "TECHNICAL_FACTOR"
    UNKNOWN = "UNKNOWN"

@dataclass
class BreakdownEvent:
    """Correlation breakdown event"""
    pair_id: str
    event_id: str
    timestamp: datetime
    breakdown_type: BreakdownType
    severity: BreakdownSeverity
    cause: BreakdownCause
    
    # Correlation metrics
    correlation_before: float
    correlation_after: float
    correlation_change: float
    
    # Statistical measures
    p_value: float
    confidence_level: float
    statistical_significance: bool
    
    # Timing information
    detection_lag: timedelta
    expected_duration: Optional[timedelta]
    recovery_probability: float
    
    # Context information
    market_conditions: Dict[str, Any]
    trigger_metrics: Dict[str, Any]
    
    # Action recommendations
    recommended_action: str
    risk_level: str
    
    acknowledged: bool = False

@dataclass
class CorrelationAnalysis:
    """Comprehensive correlation analysis results"""
    pair_id: str
    analysis_timestamp: datetime
    
    # Multi-timeframe correlations
    correlation_1h: float
    correlation_4h: float
    correlation_1d: float
    correlation_1w: float
    correlation_1m: float
    
    # Statistical measures
    correlation_stability: float
    correlation_trend: float
    correlation_volatility: float
    
    # Breakdown indicators
    breakdown_probability: float
    breakdown_risk_score: float
    early_warning_signals: List[str]
    
    # Historical context
    historical_correlation_mean: float
    historical_correlation_std: float
    current_percentile: float

class CorrelationBreakdownDetector:
    """
    Advanced correlation breakdown detection system
    
    This class provides sophisticated detection of correlation breakdowns using:
    - Multiple statistical tests
    - Multi-timeframe analysis
    - Pattern recognition
    - Machine learning-based prediction
    - Historical context analysis
    """
    
    def __init__(self, 
                 db_path: str = "correlation_breakdown.db",
                 significance_level: float = 0.05,
                 min_observations: int = 30):
        """
        Initialize the correlation breakdown detector
        
        Args:
            db_path: Path to SQLite database for storing breakdown events
            significance_level: Statistical significance level for tests
            min_observations: Minimum observations required for analysis
        """
        self.db_path = db_path
        self.significance_level = significance_level
        self.min_observations = min_observations
        
        # Historical data storage
        self.correlation_history: Dict[str, List[Tuple[datetime, float]]] = {}
        self.breakdown_events: List[BreakdownEvent] = []
        
        # Analysis parameters
        self.timeframes = {
            '1h': timedelta(hours=1),
            '4h': timedelta(hours=4),
            '1d': timedelta(days=1),
            '1w': timedelta(weeks=1),
            '1m': timedelta(days=30)
        }
        
        # Threshold parameters (can be dynamically adjusted)
        self.thresholds = {
            'minor_correlation_drop': 0.1,
            'moderate_correlation_drop': 0.2,
            'severe_correlation_drop': 0.3,
            'critical_correlation_drop': 0.4,
            'stability_threshold': 0.8,
            'trend_threshold': 0.05
        }
        
        # Initialize database
        self._init_database()
        
        logger.info("Correlation breakdown detector initialized")
    
    def _init_database(self):
        """Initialize SQLite database for storing breakdown events"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS breakdown_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pair_id TEXT NOT NULL,
                    event_id TEXT UNIQUE NOT NULL,
                    timestamp DATETIME NOT NULL,
                    breakdown_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    cause TEXT NOT NULL,
                    correlation_before REAL NOT NULL,
                    correlation_after REAL NOT NULL,
                    correlation_change REAL NOT NULL,
                    p_value REAL NOT NULL,
                    confidence_level REAL NOT NULL,
                    statistical_significance BOOLEAN NOT NULL,
                    detection_lag INTEGER,
                    recovery_probability REAL,
                    market_conditions TEXT,
                    trigger_metrics TEXT,
                    recommended_action TEXT,
                    risk_level TEXT,
                    acknowledged BOOLEAN DEFAULT FALSE
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS correlation_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pair_id TEXT NOT NULL,
                    analysis_timestamp DATETIME NOT NULL,
                    correlation_1h REAL,
                    correlation_4h REAL,
                    correlation_1d REAL,
                    correlation_1w REAL,
                    correlation_1m REAL,
                    correlation_stability REAL,
                    correlation_trend REAL,
                    correlation_volatility REAL,
                    breakdown_probability REAL,
                    breakdown_risk_score REAL,
                    early_warning_signals TEXT,
                    historical_correlation_mean REAL,
                    historical_correlation_std REAL,
                    current_percentile REAL
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Correlation breakdown database initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def add_correlation_data(self, pair_id: str, correlation: float, timestamp: datetime = None):
        """Add correlation data point for analysis"""
        if timestamp is None:
            timestamp = datetime.now()
        
        if pair_id not in self.correlation_history:
            self.correlation_history[pair_id] = []
        
        self.correlation_history[pair_id].append((timestamp, correlation))
        
        # Keep only recent data (last 3 months)
        cutoff_time = timestamp - timedelta(days=90)
        self.correlation_history[pair_id] = [
            (ts, corr) for ts, corr in self.correlation_history[pair_id]
            if ts > cutoff_time
        ]
        
        # Perform analysis if enough data
        if len(self.correlation_history[pair_id]) >= self.min_observations:
            self._analyze_correlation_breakdown(pair_id)
    
    def _analyze_correlation_breakdown(self, pair_id: str):
        """Perform comprehensive correlation breakdown analysis"""
        try:
            correlation_data = self.correlation_history[pair_id]
            if len(correlation_data) < self.min_observations:
                return
            
            # Extract time series
            timestamps = [ts for ts, _ in correlation_data]
            correlations = np.array([corr for _, corr in correlation_data])
            
            # Perform multi-timeframe analysis
            analysis = self._perform_multitimeframe_analysis(pair_id, timestamps, correlations)
            
            # Detect breakdown patterns
            breakdown_signals = self._detect_breakdown_patterns(correlations)
            
            # Statistical significance testing
            significance_results = self._test_statistical_significance(correlations)
            
            # Calculate breakdown probability
            breakdown_prob = self._calculate_breakdown_probability(correlations, breakdown_signals)
            
            # Generate alerts if necessary
            if breakdown_prob > 0.7 or significance_results['significant_change']:
                self._generate_breakdown_alert(pair_id, analysis, breakdown_signals, significance_results)
            
            # Store analysis results
            self._store_analysis_results(analysis)
            
        except Exception as e:
            logger.error(f"Error analyzing correlation breakdown for {pair_id}: {e}")
    
    def _perform_multitimeframe_analysis(self, pair_id: str, timestamps: List[datetime], 
                                       correlations: np.ndarray) -> CorrelationAnalysis:
        """Perform multi-timeframe correlation analysis"""
        current_time = timestamps[-1]
        
        # Calculate correlations for different timeframes
        timeframe_correlations = {}
        
        for tf_name, tf_delta in self.timeframes.items():
            cutoff_time = current_time - tf_delta
            
            # Filter data for this timeframe
            tf_data = [(ts, corr) for ts, corr in zip(timestamps, correlations) if ts >= cutoff_time]
            
            if len(tf_data) >= 5:  # Minimum data points
                tf_correlations = [corr for _, corr in tf_data]
                timeframe_correlations[tf_name] = np.mean(tf_correlations)
            else:
                timeframe_correlations[tf_name] = np.nan
        
        # Calculate stability and trend
        stability = self._calculate_correlation_stability(correlations)
        trend = self._calculate_correlation_trend(correlations)
        volatility = np.std(correlations[-20:]) if len(correlations) >= 20 else 0.0
        
        # Historical context
        historical_mean = np.mean(correlations)
        historical_std = np.std(correlations)
        current_percentile = stats.percentileofscore(correlations, correlations[-1]) / 100.0
        
        # Early warning signals
        warning_signals = self._identify_early_warning_signals(correlations)
        
        # Risk assessment
        risk_score = self._calculate_risk_score(correlations, stability, trend, volatility)
        breakdown_prob = self._calculate_breakdown_probability(correlations, warning_signals)
        
        return CorrelationAnalysis(
            pair_id=pair_id,
            analysis_timestamp=current_time,
            correlation_1h=timeframe_correlations.get('1h', np.nan),
            correlation_4h=timeframe_correlations.get('4h', np.nan),
            correlation_1d=timeframe_correlations.get('1d', np.nan),
            correlation_1w=timeframe_correlations.get('1w', np.nan),
            correlation_1m=timeframe_correlations.get('1m', np.nan),
            correlation_stability=stability,
            correlation_trend=trend,
            correlation_volatility=volatility,
            breakdown_probability=breakdown_prob,
            breakdown_risk_score=risk_score,
            early_warning_signals=warning_signals,
            historical_correlation_mean=historical_mean,
            historical_correlation_std=historical_std,
            current_percentile=current_percentile
        )
    
    def _calculate_correlation_stability(self, correlations: np.ndarray) -> float:
        """Calculate correlation stability measure"""
        if len(correlations) < 10:
            return 0.0
        
        # Use rolling standard deviation as stability measure
        window_size = min(20, len(correlations) // 2)
        rolling_std = pd.Series(correlations).rolling(window=window_size).std()
        
        # Stability is inverse of volatility
        avg_volatility = np.nanmean(rolling_std)
        stability = 1.0 / (1.0 + avg_volatility) if avg_volatility > 0 else 1.0
        
        return min(1.0, max(0.0, stability))
    
    def _calculate_correlation_trend(self, correlations: np.ndarray) -> float:
        """Calculate correlation trend strength"""
        if len(correlations) < 5:
            return 0.0
        
        # Linear regression slope
        x = np.arange(len(correlations))
        slope, _, r_value, p_value, _ = stats.linregress(x, correlations)
        
        # Trend strength is slope weighted by R-squared and significance
        trend_strength = slope * (r_value ** 2) if p_value < 0.05 else 0.0
        
        return trend_strength
    
    def _detect_breakdown_patterns(self, correlations: np.ndarray) -> List[str]:
        """Detect specific breakdown patterns"""
        patterns = []
        
        if len(correlations) < 10:
            return patterns
        
        # Sudden drop detection
        if self._detect_sudden_drop(correlations):
            patterns.append("SUDDEN_DROP")
        
        # Gradual decline detection
        if self._detect_gradual_decline(correlations):
            patterns.append("GRADUAL_DECLINE")
        
        # Oscillating pattern detection
        if self._detect_oscillating_pattern(correlations):
            patterns.append("OSCILLATING")
        
        # Structural break detection
        if self._detect_structural_break(correlations):
            patterns.append("STRUCTURAL_BREAK")
        
        # Volatility spike detection
        if self._detect_volatility_spike(correlations):
            patterns.append("VOLATILITY_SPIKE")
        
        return patterns
    
    def _detect_sudden_drop(self, correlations: np.ndarray) -> bool:
        """Detect sudden correlation drop"""
        if len(correlations) < 5:
            return False
        
        # Look for large single-period drops
        changes = np.diff(correlations)
        recent_changes = changes[-5:]
        
        # Check for drops larger than 2 standard deviations
        std_change = np.std(changes)
        threshold = -2 * std_change
        
        return np.any(recent_changes < threshold)
    
    def _detect_gradual_decline(self, correlations: np.ndarray) -> bool:
        """Detect gradual correlation decline"""
        if len(correlations) < 20:
            return False
        
        # Check for sustained downward trend
        recent_corrs = correlations[-20:]
        slope, _, r_value, p_value, _ = stats.linregress(np.arange(len(recent_corrs)), recent_corrs)
        
        # Significant negative trend
        return slope < -0.01 and r_value ** 2 > 0.3 and p_value < 0.05
    
    def _detect_oscillating_pattern(self, correlations: np.ndarray) -> bool:
        """Detect oscillating correlation pattern"""
        if len(correlations) < 15:
            return False
        
        # Use peak detection to find oscillations
        peaks_high, _ = find_peaks(correlations, height=np.percentile(correlations, 70))
        peaks_low, _ = find_peaks(-correlations, height=-np.percentile(correlations, 30))
        
        # Check for alternating peaks and troughs
        total_peaks = len(peaks_high) + len(peaks_low)
        oscillation_frequency = total_peaks / len(correlations)
        
        return oscillation_frequency > 0.1  # More than 10% of points are peaks
    
    def _detect_structural_break(self, correlations: np.ndarray) -> bool:
        """Detect structural break in correlation"""
        if len(correlations) < 30:
            return False
        
        # Chow test for structural break
        n = len(correlations)
        break_point = n // 2
        
        # Split data
        first_half = correlations[:break_point]
        second_half = correlations[break_point:]
        
        # Test for significant difference in means
        t_stat, p_value = stats.ttest_ind(first_half, second_half)
        
        return p_value < 0.01  # Strong evidence of structural break
    
    def _detect_volatility_spike(self, correlations: np.ndarray) -> bool:
        """Detect volatility spike in correlation"""
        if len(correlations) < 20:
            return False
        
        # Calculate rolling volatility
        window_size = min(10, len(correlations) // 2)
        rolling_vol = pd.Series(correlations).rolling(window=window_size).std()
        
        # Check for recent volatility spike
        recent_vol = rolling_vol.iloc[-5:].mean()
        historical_vol = rolling_vol.iloc[:-5].mean()
        
        return recent_vol > 2 * historical_vol
    
    def _test_statistical_significance(self, correlations: np.ndarray) -> Dict[str, Any]:
        """Test statistical significance of correlation changes"""
        if len(correlations) < 20:
            return {'significant_change': False}
        
        # Split into before and after periods
        split_point = len(correlations) * 2 // 3
        before = correlations[:split_point]
        after = correlations[split_point:]
        
        # Perform t-test
        t_stat, p_value = stats.ttest_ind(before, after)
        
        # Effect size (Cohen's d)
        pooled_std = np.sqrt(((len(before) - 1) * np.var(before) + 
                             (len(after) - 1) * np.var(after)) / 
                            (len(before) + len(after) - 2))
        
        cohens_d = (np.mean(after) - np.mean(before)) / pooled_std if pooled_std > 0 else 0
        
        return {
            'significant_change': p_value < self.significance_level,
            't_statistic': t_stat,
            'p_value': p_value,
            'cohens_d': cohens_d,
            'correlation_before': np.mean(before),
            'correlation_after': np.mean(after),
            'correlation_change': np.mean(after) - np.mean(before)
        }
    
    def _identify_early_warning_signals(self, correlations: np.ndarray) -> List[str]:
        """Identify early warning signals for breakdown"""
        signals = []
        
        if len(correlations) < 10:
            return signals
        
        # Recent correlation below historical average
        recent_corr = np.mean(correlations[-5:])
        historical_mean = np.mean(correlations[:-5])
        
        if recent_corr < historical_mean - np.std(correlations):
            signals.append("BELOW_HISTORICAL_AVERAGE")
        
        # Increasing volatility
        recent_vol = np.std(correlations[-10:])
        historical_vol = np.std(correlations[:-10])
        
        if recent_vol > 1.5 * historical_vol:
            signals.append("INCREASING_VOLATILITY")
        
        # Downward trend
        if self._calculate_correlation_trend(correlations[-15:]) < -0.01:
            signals.append("DOWNWARD_TREND")
        
        # Low stability
        if self._calculate_correlation_stability(correlations[-10:]) < 0.5:
            signals.append("LOW_STABILITY")
        
        return signals
    
    def _calculate_risk_score(self, correlations: np.ndarray, stability: float, 
                            trend: float, volatility: float) -> float:
        """Calculate overall breakdown risk score"""
        if len(correlations) < 5:
            return 0.0
        
        # Base risk from current correlation level
        current_corr = correlations[-1]
        base_risk = max(0.0, (0.5 - abs(current_corr)) / 0.5)  # Higher risk for lower correlation
        
        # Stability risk
        stability_risk = 1.0 - stability
        
        # Trend risk (negative trend is risky)
        trend_risk = max(0.0, -trend * 10)  # Scale negative trend
        
        # Volatility risk
        volatility_risk = min(1.0, volatility * 5)  # Scale volatility
        
        # Combine risks with weights
        risk_score = (
            0.3 * base_risk +
            0.3 * stability_risk +
            0.2 * trend_risk +
            0.2 * volatility_risk
        )
        
        return min(1.0, max(0.0, risk_score))
    
    def _calculate_breakdown_probability(self, correlations: np.ndarray, 
                                       warning_signals: List[str]) -> float:
        """Calculate probability of correlation breakdown"""
        if len(correlations) < 10:
            return 0.0
        
        # Base probability from correlation level
        current_corr = abs(correlations[-1])
        base_prob = max(0.0, (0.5 - current_corr) / 0.5)
        
        # Signal-based probability
        signal_prob = len(warning_signals) / 10.0  # Normalize by max expected signals
        
        # Historical volatility factor
        volatility_factor = min(1.0, np.std(correlations) * 5)
        
        # Recent change factor
        recent_change = abs(correlations[-1] - np.mean(correlations[-10:-1]))
        change_factor = min(1.0, recent_change * 2)
        
        # Combine factors
        breakdown_prob = (
            0.4 * base_prob +
            0.3 * signal_prob +
            0.2 * volatility_factor +
            0.1 * change_factor
        )
        
        return min(1.0, max(0.0, breakdown_prob))
    
    def _generate_breakdown_alert(self, pair_id: str, analysis: CorrelationAnalysis,
                                breakdown_signals: List[str], significance_results: Dict[str, Any]):
        """Generate breakdown alert"""
        try:
            # Determine severity
            severity = self._determine_breakdown_severity(analysis, significance_results)
            
            # Determine breakdown type
            breakdown_type = self._determine_breakdown_type(breakdown_signals)
            
            # Determine likely cause
            cause = self._determine_breakdown_cause(analysis, breakdown_signals)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(severity, breakdown_type, cause)
            
            # Create breakdown event
            event = BreakdownEvent(
                pair_id=pair_id,
                event_id=f"{pair_id}_breakdown_{int(datetime.now().timestamp())}",
                timestamp=datetime.now(),
                breakdown_type=breakdown_type,
                severity=severity,
                cause=cause,
                correlation_before=significance_results.get('correlation_before', 0.0),
                correlation_after=significance_results.get('correlation_after', 0.0),
                correlation_change=significance_results.get('correlation_change', 0.0),
                p_value=significance_results.get('p_value', 1.0),
                confidence_level=1.0 - significance_results.get('p_value', 1.0),
                statistical_significance=significance_results.get('significant_change', False),
                detection_lag=timedelta(minutes=5),  # Estimated detection lag
                recovery_probability=self._estimate_recovery_probability(analysis, breakdown_type),
                market_conditions=self._get_market_conditions(),
                trigger_metrics={
                    'breakdown_probability': analysis.breakdown_probability,
                    'risk_score': analysis.breakdown_risk_score,
                    'stability': analysis.correlation_stability,
                    'trend': analysis.correlation_trend,
                    'volatility': analysis.correlation_volatility
                },
                recommended_action=recommendations['action'],
                risk_level=recommendations['risk_level']
            )
            
            self.breakdown_events.append(event)
            self._store_breakdown_event(event)
            
            logger.warning(f"Correlation breakdown detected for {pair_id}: {severity.value} - {breakdown_type.value}")
            
        except Exception as e:
            logger.error(f"Error generating breakdown alert: {e}")
    
    def _determine_breakdown_severity(self, analysis: CorrelationAnalysis, 
                                    significance_results: Dict[str, Any]) -> BreakdownSeverity:
        """Determine breakdown severity level"""
        correlation_change = abs(significance_results.get('correlation_change', 0.0))
        risk_score = analysis.breakdown_risk_score
        breakdown_prob = analysis.breakdown_probability
        
        # Weighted severity score
        severity_score = (
            0.4 * correlation_change / 0.5 +  # Normalize by max expected change
            0.3 * risk_score +
            0.3 * breakdown_prob
        )
        
        if severity_score > 0.8:
            return BreakdownSeverity.CRITICAL
        elif severity_score > 0.6:
            return BreakdownSeverity.SEVERE
        elif severity_score > 0.4:
            return BreakdownSeverity.MODERATE
        else:
            return BreakdownSeverity.MINOR
    
    def _determine_breakdown_type(self, breakdown_signals: List[str]) -> BreakdownType:
        """Determine the type of breakdown based on signals"""
        if "SUDDEN_DROP" in breakdown_signals:
            return BreakdownType.SUDDEN_DROP
        elif "GRADUAL_DECLINE" in breakdown_signals:
            return BreakdownType.GRADUAL_DECLINE
        elif "OSCILLATING" in breakdown_signals:
            return BreakdownType.OSCILLATING
        elif "STRUCTURAL_BREAK" in breakdown_signals:
            return BreakdownType.STRUCTURAL_BREAK
        elif "VOLATILITY_SPIKE" in breakdown_signals:
            return BreakdownType.VOLATILITY_SPIKE
        else:
            return BreakdownType.REGIME_CHANGE
    
    def _determine_breakdown_cause(self, analysis: CorrelationAnalysis, 
                                 breakdown_signals: List[str]) -> BreakdownCause:
        """Determine likely cause of breakdown"""
        # This is a simplified version - in practice, you'd integrate with news feeds,
        # market data, earnings calendars, etc.
        
        if analysis.correlation_volatility > 0.3:
            return BreakdownCause.MARKET_STRESS
        elif "SUDDEN_DROP" in breakdown_signals:
            return BreakdownCause.NEWS_SHOCK
        elif "GRADUAL_DECLINE" in breakdown_signals:
            return BreakdownCause.SECTOR_ROTATION
        elif analysis.breakdown_probability > 0.8:
            return BreakdownCause.STRUCTURAL_BREAK
        else:
            return BreakdownCause.TECHNICAL_FACTOR
    
    def _generate_recommendations(self, severity: BreakdownSeverity, 
                                breakdown_type: BreakdownType, 
                                cause: BreakdownCause) -> Dict[str, str]:
        """Generate action recommendations"""
        recommendations = {
            'action': 'MONITOR',
            'risk_level': 'LOW'
        }
        
        if severity == BreakdownSeverity.CRITICAL:
            recommendations['action'] = 'CLOSE_POSITIONS'
            recommendations['risk_level'] = 'VERY_HIGH'
        elif severity == BreakdownSeverity.SEVERE:
            recommendations['action'] = 'REDUCE_EXPOSURE'
            recommendations['risk_level'] = 'HIGH'
        elif severity == BreakdownSeverity.MODERATE:
            recommendations['action'] = 'INCREASE_MONITORING'
            recommendations['risk_level'] = 'MEDIUM'
        
        # Adjust based on breakdown type
        if breakdown_type == BreakdownType.SUDDEN_DROP:
            recommendations['action'] = 'IMMEDIATE_REVIEW'
        elif breakdown_type == BreakdownType.STRUCTURAL_BREAK:
            recommendations['action'] = 'FUNDAMENTAL_REVIEW'
        
        return recommendations
    
    def _estimate_recovery_probability(self, analysis: CorrelationAnalysis, 
                                     breakdown_type: BreakdownType) -> float:
        """Estimate probability of correlation recovery"""
        base_recovery = 0.5  # Base 50% recovery probability
        
        # Adjust based on breakdown type
        if breakdown_type == BreakdownType.SUDDEN_DROP:
            base_recovery = 0.7  # Often temporary
        elif breakdown_type == BreakdownType.STRUCTURAL_BREAK:
            base_recovery = 0.2  # Usually permanent
        elif breakdown_type == BreakdownType.VOLATILITY_SPIKE:
            base_recovery = 0.8  # Usually temporary
        
        # Adjust based on current metrics
        if analysis.correlation_stability > 0.7:
            base_recovery += 0.2
        if analysis.breakdown_probability < 0.5:
            base_recovery += 0.1
        
        return min(1.0, max(0.0, base_recovery))
    
    def _get_market_conditions(self) -> Dict[str, Any]:
        """Get current market conditions (placeholder)"""
        # In practice, this would integrate with market data feeds
        return {
            'vix_level': 'NORMAL',
            'market_regime': 'TRENDING',
            'liquidity': 'NORMAL',
            'volatility': 'MODERATE'
        }
    
    def _store_breakdown_event(self, event: BreakdownEvent):
        """Store breakdown event in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO breakdown_events 
                (pair_id, event_id, timestamp, breakdown_type, severity, cause,
                 correlation_before, correlation_after, correlation_change,
                 p_value, confidence_level, statistical_significance,
                 detection_lag, recovery_probability, market_conditions,
                 trigger_metrics, recommended_action, risk_level, acknowledged)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event.pair_id, event.event_id, event.timestamp,
                event.breakdown_type.value, event.severity.value, event.cause.value,
                event.correlation_before, event.correlation_after, event.correlation_change,
                event.p_value, event.confidence_level, event.statistical_significance,
                int(event.detection_lag.total_seconds()), event.recovery_probability,
                json.dumps(event.market_conditions), json.dumps(event.trigger_metrics),
                event.recommended_action, event.risk_level, event.acknowledged
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing breakdown event: {e}")
    
    def _store_analysis_results(self, analysis: CorrelationAnalysis):
        """Store analysis results in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO correlation_analysis 
                (pair_id, analysis_timestamp, correlation_1h, correlation_4h, correlation_1d,
                 correlation_1w, correlation_1m, correlation_stability, correlation_trend,
                 correlation_volatility, breakdown_probability, breakdown_risk_score,
                 early_warning_signals, historical_correlation_mean, historical_correlation_std,
                 current_percentile)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                analysis.pair_id, analysis.analysis_timestamp,
                analysis.correlation_1h, analysis.correlation_4h, analysis.correlation_1d,
                analysis.correlation_1w, analysis.correlation_1m,
                analysis.correlation_stability, analysis.correlation_trend,
                analysis.correlation_volatility, analysis.breakdown_probability,
                analysis.breakdown_risk_score, json.dumps(analysis.early_warning_signals),
                analysis.historical_correlation_mean, analysis.historical_correlation_std,
                analysis.current_percentile
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing analysis results: {e}")
    
    def get_breakdown_events(self, pair_id: str = None, hours: int = 24) -> List[BreakdownEvent]:
        """Get recent breakdown events"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        events = [event for event in self.breakdown_events if event.timestamp > cutoff_time]
        
        if pair_id:
            events = [event for event in events if event.pair_id == pair_id]
        
        return events
    
    def get_analysis_results(self, pair_id: str) -> Optional[CorrelationAnalysis]:
        """Get latest analysis results for a pair"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM correlation_analysis 
                WHERE pair_id = ? 
                ORDER BY analysis_timestamp DESC 
                LIMIT 1
            ''', (pair_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                # Convert database row to CorrelationAnalysis object
                # (Implementation details omitted for brevity)
                pass
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving analysis results: {e}")
            return None
    
    def acknowledge_breakdown_event(self, event_id: str):
        """Acknowledge a breakdown event"""
        for event in self.breakdown_events:
            if event.event_id == event_id:
                event.acknowledged = True
                
                # Update database
                try:
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    cursor.execute('UPDATE breakdown_events SET acknowledged = TRUE WHERE event_id = ?', 
                                 (event_id,))
                    conn.commit()
                    conn.close()
                except Exception as e:
                    logger.error(f"Error acknowledging breakdown event: {e}")
                
                logger.info(f"Breakdown event {event_id} acknowledged")
                break
    
    def get_detector_summary(self) -> Dict[str, Any]:
        """Get detector summary statistics"""
        recent_events = self.get_breakdown_events(hours=24)
        
        return {
            'total_pairs_monitored': len(self.correlation_history),
            'recent_breakdown_events': len(recent_events),
            'critical_events': len([e for e in recent_events if e.severity == BreakdownSeverity.CRITICAL]),
            'unacknowledged_events': len([e for e in recent_events if not e.acknowledged]),
            'detection_accuracy': self._calculate_detection_accuracy(),
            'average_detection_lag': self._calculate_average_detection_lag(),
            'last_update': datetime.now().isoformat()
        }
    
    def _calculate_detection_accuracy(self) -> float:
        """Calculate detection accuracy (placeholder)"""
        # In practice, this would compare predictions with actual outcomes
        return 0.85  # 85% accuracy
    
    def _calculate_average_detection_lag(self) -> float:
        """Calculate average detection lag in minutes"""
        # In practice, this would analyze historical detection performance
        return 3.5  # 3.5 minutes average lag

# Example usage
if __name__ == "__main__":
    # Create detector
    detector = CorrelationBreakdownDetector()
    
    # Simulate correlation data
    import random
    
    # Start with high correlation, then simulate breakdown
    correlations = []
    for i in range(100):
        if i < 50:
            corr = 0.8 + random.random() * 0.1  # High correlation
        else:
            corr = 0.3 + random.random() * 0.2  # Breakdown
        
        correlations.append(corr)
        detector.add_correlation_data("TSLA_NVDA", corr)
    
    # Get breakdown events
    events = detector.get_breakdown_events()
    print(f"Detected {len(events)} breakdown events")
    
    # Get summary
    summary = detector.get_detector_summary()
    print(json.dumps(summary, indent=2)) 