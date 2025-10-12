"""
Trend Analysis Engine for Performance Testing
Advanced trend analysis and regression detection for performance monitoring
and anomaly identification in institutional-grade testing.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from scipy import stats
from scipy.signal import find_peaks
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

@dataclass
class TrendLine:
    """Trend line analysis results"""
    slope: float
    intercept: float
    r_squared: float
    p_value: float
    confidence_interval: Tuple[float, float]
    trend_direction: str  # 'increasing', 'decreasing', 'stable'
    trend_strength: str   # 'weak', 'moderate', 'strong'
    significance_level: float

@dataclass
class RegressionPoint:
    """Performance regression detection point"""
    timestamp: datetime
    value: float
    severity: str  # 'minor', 'moderate', 'severe', 'critical'
    change_percentage: float
    confidence: float
    context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AnomalyPoint:
    """Anomaly detection point"""
    timestamp: datetime
    value: float
    anomaly_score: float
    anomaly_type: str  # 'outlier', 'spike', 'drop', 'pattern_break'
    severity: str
    context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TrendAnalysis:
    """Comprehensive trend analysis results"""
    trend_line: TrendLine
    regressions: List[RegressionPoint]
    anomalies: List[AnomalyPoint]
    change_points: List[datetime]
    seasonality_detected: bool
    periodicity: Optional[float]
    overall_trend_health: str  # 'healthy', 'concerning', 'critical'
    recommendations: List[str]

class TrendAnalysisEngine:
    """Trend analysis and regression detection for performance testing"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.regression_threshold = self.config.get('regression_threshold', 0.1)  # 10% change
        self.anomaly_threshold = self.config.get('anomaly_threshold', 3.0)  # 3 standard deviations
        self.min_samples_for_trend = self.config.get('min_samples_for_trend', 10)
        self.significance_level = self.config.get('significance_level', 0.05)
        
        # Performance thresholds
        self.performance_thresholds = {
            'latency_regression_pct': 20.0,  # 20% increase in latency
            'throughput_regression_pct': 15.0,  # 15% decrease in throughput
            'memory_regression_pct': 25.0,  # 25% increase in memory usage
            'stability_regression_pct': 10.0  # 10% decrease in stability
        }
    
    def analyze_performance_trends(self, historical_data: List[Dict[str, Any]]) -> TrendAnalysis:
        """Analyze performance trends over time"""
        
        if not historical_data:
            return self._create_empty_analysis()
        
        # Extract time series data
        timestamps = [data['timestamp'] for data in historical_data]
        values = [data['value'] for data in historical_data]
        
        # Convert to numpy arrays for analysis
        timestamps_array = np.array([ts.timestamp() if hasattr(ts, 'timestamp') else ts for ts in timestamps])
        values_array = np.array(values)
        
        # Calculate trend line
        trend_line = self._calculate_trend_line(timestamps_array, values_array)
        
        # Detect regressions
        regressions = self._detect_performance_regressions(timestamps, values_array, trend_line)
        
        # Detect anomalies
        anomalies = self._detect_anomalies(timestamps, values_array)
        
        # Detect change points
        change_points = self._detect_change_points(timestamps, values_array)
        
        # Analyze seasonality
        seasonality_detected, periodicity = self._analyze_seasonality(values_array)
        
        # Determine overall trend health
        trend_health = self._assess_trend_health(trend_line, regressions, anomalies)
        
        # Generate recommendations
        recommendations = self._generate_trend_recommendations(trend_line, regressions, anomalies)
        
        return TrendAnalysis(
            trend_line=trend_line,
            regressions=regressions,
            anomalies=anomalies,
            change_points=change_points,
            seasonality_detected=seasonality_detected,
            periodicity=periodicity,
            overall_trend_health=trend_health,
            recommendations=recommendations
        )
    
    def _calculate_trend_line(self, timestamps: np.ndarray, values: np.ndarray) -> TrendLine:
        """Calculate trend line using linear regression"""
        
        if len(timestamps) < self.min_samples_for_trend:
            return TrendLine(
                slope=0.0, intercept=0.0, r_squared=0.0, p_value=1.0,
                confidence_interval=(0.0, 0.0), trend_direction='stable',
                trend_strength='weak', significance_level=1.0
            )
        
        # Normalize timestamps to start from 0
        timestamps_normalized = timestamps - timestamps[0]
        
        # Perform linear regression
        slope, intercept, r_value, p_value, std_err = stats.linregress(timestamps_normalized, values)
        r_squared = r_value ** 2
        
        # Calculate confidence interval for slope
        n = len(timestamps)
        t_critical = stats.t.ppf(1 - self.significance_level/2, n - 2)
        slope_ci = (slope - t_critical * std_err, slope + t_critical * std_err)
        
        # Determine trend direction and strength
        trend_direction = self._classify_trend_direction(slope, p_value)
        trend_strength = self._classify_trend_strength(r_squared)
        
        return TrendLine(
            slope=slope,
            intercept=intercept,
            r_squared=r_squared,
            p_value=p_value,
            confidence_interval=slope_ci,
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            significance_level=self.significance_level
        )
    
    def _classify_trend_direction(self, slope: float, p_value: float) -> str:
        """Classify trend direction based on slope and significance"""
        if p_value > self.significance_level:
            return 'stable'
        elif slope > 0:
            return 'increasing'
        else:
            return 'decreasing'
    
    def _classify_trend_strength(self, r_squared: float) -> str:
        """Classify trend strength based on R-squared"""
        if r_squared < 0.3:
            return 'weak'
        elif r_squared < 0.7:
            return 'moderate'
        else:
            return 'strong'
    
    def _detect_performance_regressions(self, timestamps: List[datetime], values: np.ndarray, trend_line: TrendLine) -> List[RegressionPoint]:
        """Detect performance regressions in the data"""
        
        regressions = []
        
        if len(values) < 2:
            return regressions
        
        # Calculate expected values based on trend line
        timestamps_normalized = np.array([ts.timestamp() if hasattr(ts, 'timestamp') else ts for ts in timestamps])
        timestamps_normalized = timestamps_normalized - timestamps_normalized[0]
        expected_values = trend_line.slope * timestamps_normalized + trend_line.intercept
        
        # Calculate residuals (actual - expected)
        residuals = values - expected_values
        
        # Detect significant deviations
        residual_std = np.std(residuals)
        threshold = self.regression_threshold * np.mean(values)
        
        for i, (timestamp, actual, expected, residual) in enumerate(zip(timestamps, values, expected_values, residuals)):
            if abs(residual) > threshold:
                change_percentage = (actual - expected) / expected * 100 if expected != 0 else 0
                
                # Determine severity
                severity = self._classify_regression_severity(abs(change_percentage))
                
                # Calculate confidence based on how far from trend
                confidence = min(1.0, abs(residual) / (3 * residual_std))
                
                regressions.append(RegressionPoint(
                    timestamp=timestamp,
                    value=actual,
                    severity=severity,
                    change_percentage=change_percentage,
                    confidence=confidence,
                    context={
                        'expected_value': expected,
                        'residual': residual,
                        'residual_std': residual_std
                    }
                ))
        
        return regressions
    
    def _classify_regression_severity(self, change_percentage: float) -> str:
        """Classify regression severity based on change percentage"""
        abs_change = abs(change_percentage)
        
        if abs_change < 5:
            return 'minor'
        elif abs_change < 15:
            return 'moderate'
        elif abs_change < 30:
            return 'severe'
        else:
            return 'critical'
    
    def _detect_anomalies(self, timestamps: List[datetime], values: np.ndarray) -> List[AnomalyPoint]:
        """Detect anomalies in the performance data"""
        
        anomalies = []
        
        if len(values) < 3:
            return anomalies
        
        # Calculate rolling statistics
        window_size = min(10, len(values) // 3)
        rolling_mean = pd.Series(values).rolling(window=window_size, center=True).mean()
        rolling_std = pd.Series(values).rolling(window=window_size, center=True).std()
        
        # Detect outliers using Z-score
        z_scores = np.abs((values - rolling_mean) / rolling_std)
        outlier_indices = np.where(z_scores > self.anomaly_threshold)[0]
        
        for idx in outlier_indices:
            if not np.isnan(rolling_mean.iloc[idx]) and not np.isnan(rolling_std.iloc[idx]):
                anomaly_score = z_scores[idx]
                anomaly_type = self._classify_anomaly_type(values, idx)
                severity = self._classify_anomaly_severity(anomaly_score)
                
                anomalies.append(AnomalyPoint(
                    timestamp=timestamps[idx],
                    value=values[idx],
                    anomaly_score=anomaly_score,
                    anomaly_type=anomaly_type,
                    severity=severity,
                    context={
                        'rolling_mean': rolling_mean.iloc[idx],
                        'rolling_std': rolling_std.iloc[idx],
                        'z_score': z_scores[idx]
                    }
                ))
        
        return anomalies
    
    def _classify_anomaly_type(self, values: np.ndarray, index: int) -> str:
        """Classify the type of anomaly"""
        if index == 0 or index == len(values) - 1:
            return 'edge_case'
        
        current = values[index]
        prev = values[index - 1]
        next_val = values[index + 1]
        
        if current > max(prev, next_val):
            return 'spike'
        elif current < min(prev, next_val):
            return 'drop'
        else:
            return 'outlier'
    
    def _classify_anomaly_severity(self, anomaly_score: float) -> str:
        """Classify anomaly severity based on score"""
        if anomaly_score < 3:
            return 'minor'
        elif anomaly_score < 5:
            return 'moderate'
        elif anomaly_score < 7:
            return 'severe'
        else:
            return 'critical'
    
    def _detect_change_points(self, timestamps: List[datetime], values: np.ndarray) -> List[datetime]:
        """Detect change points in the time series"""
        
        change_points = []
        
        if len(values) < 10:
            return change_points
        
        # Use rolling window to detect changes
        window_size = min(5, len(values) // 4)
        
        for i in range(window_size, len(values) - window_size):
            before_window = values[i-window_size:i]
            after_window = values[i:i+window_size]
            
            # Perform t-test to detect significant change
            try:
                t_stat, p_value = stats.ttest_ind(before_window, after_window)
                
                if p_value < self.significance_level and abs(t_stat) > 2:
                    change_points.append(timestamps[i])
            except Exception:
                continue
        
        return change_points
    
    def _analyze_seasonality(self, values: np.ndarray) -> Tuple[bool, Optional[float]]:
        """Analyze seasonality in the data"""
        
        if len(values) < 20:
            return False, None
        
        # Use autocorrelation to detect periodicity
        autocorr = np.correlate(values, values, mode='full')
        autocorr = autocorr[autocorr.size // 2:]
        
        # Normalize autocorrelation
        autocorr = autocorr / autocorr[0]
        
        # Find peaks in autocorrelation (excluding lag 0)
        peaks, _ = find_peaks(autocorr[1:], height=0.3)
        peaks = peaks + 1  # Adjust for excluding lag 0
        
        if len(peaks) > 0:
            # Find the most significant period
            significant_peaks = peaks[autocorr[peaks] > 0.5]
            if len(significant_peaks) > 0:
                period = significant_peaks[0]
                return True, float(period)
        
        return False, None
    
    def _assess_trend_health(self, trend_line: TrendLine, regressions: List[RegressionPoint], anomalies: List[AnomalyPoint]) -> str:
        """Assess overall trend health"""
        
        # Count severe issues
        severe_regressions = sum(1 for r in regressions if r.severity in ['severe', 'critical'])
        severe_anomalies = sum(1 for a in anomalies if a.severity in ['severe', 'critical'])
        
        # Assess trend direction for performance metrics
        if trend_line.trend_direction == 'increasing' and trend_line.p_value < self.significance_level:
            # For latency, increasing trend is bad
            if severe_regressions > 2 or severe_anomalies > 3:
                return 'critical'
            elif severe_regressions > 0 or severe_anomalies > 1:
                return 'concerning'
        
        if severe_regressions > 1 or severe_anomalies > 2:
            return 'concerning'
        elif severe_regressions > 0 or severe_anomalies > 0:
            return 'healthy'
        else:
            return 'healthy'
    
    def _generate_trend_recommendations(self, trend_line: TrendLine, regressions: List[RegressionPoint], anomalies: List[AnomalyPoint]) -> List[str]:
        """Generate recommendations based on trend analysis"""
        
        recommendations = []
        
        # Trend-based recommendations
        if trend_line.trend_direction == 'increasing' and trend_line.p_value < self.significance_level:
            recommendations.append("Performance is degrading over time - investigate root causes")
        elif trend_line.trend_direction == 'decreasing' and trend_line.p_value < self.significance_level:
            recommendations.append("Performance is improving - monitor for sustainability")
        
        # Regression-based recommendations
        if regressions:
            severe_count = sum(1 for r in regressions if r.severity in ['severe', 'critical'])
            if severe_count > 0:
                recommendations.append(f"Address {severe_count} severe performance regressions")
        
        # Anomaly-based recommendations
        if anomalies:
            critical_anomalies = sum(1 for a in anomalies if a.severity == 'critical')
            if critical_anomalies > 0:
                recommendations.append(f"Investigate {critical_anomalies} critical anomalies")
        
        # Stability recommendations
        if trend_line.r_squared < 0.3:
            recommendations.append("High performance variability - improve system stability")
        
        return recommendations
    
    def _create_empty_analysis(self) -> TrendAnalysis:
        """Create empty analysis for insufficient data"""
        return TrendAnalysis(
            trend_line=TrendLine(
                slope=0.0, intercept=0.0, r_squared=0.0, p_value=1.0,
                confidence_interval=(0.0, 0.0), trend_direction='stable',
                trend_strength='weak', significance_level=1.0
            ),
            regressions=[],
            anomalies=[],
            change_points=[],
            seasonality_detected=False,
            periodicity=None,
            overall_trend_health='healthy',
            recommendations=['Insufficient data for trend analysis']
        )
    
    def compare_performance_trends(self, baseline_data: List[Dict[str, Any]], current_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compare performance trends between baseline and current data"""
        
        baseline_analysis = self.analyze_performance_trends(baseline_data)
        current_analysis = self.analyze_performance_trends(current_data)
        
        # Calculate trend differences
        slope_difference = current_analysis.trend_line.slope - baseline_analysis.trend_line.slope
        r_squared_difference = current_analysis.trend_line.r_squared - baseline_analysis.trend_line.r_squared
        
        # Count regression differences
        baseline_regressions = len(baseline_analysis.regressions)
        current_regressions = len(current_analysis.regressions)
        regression_change = current_regressions - baseline_regressions
        
        # Count anomaly differences
        baseline_anomalies = len(baseline_analysis.anomalies)
        current_anomalies = len(current_analysis.anomalies)
        anomaly_change = current_anomalies - baseline_anomalies
        
        # Determine overall comparison result
        if regression_change > 0 or anomaly_change > 0 or slope_difference > 0:
            comparison_result = 'degraded'
        elif regression_change < 0 or anomaly_change < 0 or slope_difference < 0:
            comparison_result = 'improved'
        else:
            comparison_result = 'stable'
        
        return {
            'comparison_result': comparison_result,
            'slope_difference': slope_difference,
            'r_squared_difference': r_squared_difference,
            'regression_change': regression_change,
            'anomaly_change': anomaly_change,
            'baseline_analysis': baseline_analysis,
            'current_analysis': current_analysis,
            'recommendations': self._generate_comparison_recommendations(
                comparison_result, slope_difference, regression_change, anomaly_change
            )
        }
    
    def _generate_comparison_recommendations(self, result: str, slope_diff: float, regression_change: int, anomaly_change: int) -> List[str]:
        """Generate recommendations based on trend comparison"""
        
        recommendations = []
        
        if result == 'degraded':
            recommendations.append("Performance has degraded - investigate recent changes")
            if regression_change > 0:
                recommendations.append(f"Address {regression_change} new performance regressions")
            if anomaly_change > 0:
                recommendations.append(f"Investigate {anomaly_change} new anomalies")
        elif result == 'improved':
            recommendations.append("Performance has improved - document successful optimizations")
        else:
            recommendations.append("Performance is stable - continue monitoring")
        
        if slope_diff > 0:
            recommendations.append("Performance trend is worsening - take corrective action")
        elif slope_diff < 0:
            recommendations.append("Performance trend is improving - maintain current approach")
        
        return recommendations

# Convenience functions
def analyze_trends(historical_data: List[Dict[str, Any]]) -> TrendAnalysis:
    """Convenience function to analyze performance trends"""
    engine = TrendAnalysisEngine()
    return engine.analyze_performance_trends(historical_data)

def compare_trends(baseline_data: List[Dict[str, Any]], current_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Convenience function to compare performance trends"""
    engine = TrendAnalysisEngine()
    return engine.compare_performance_trends(baseline_data, current_data)

if __name__ == "__main__":
    # Test the trend analysis engine
    import random
    from datetime import datetime, timedelta
    
    # Generate sample historical data
    base_time = datetime.now() - timedelta(days=30)
    historical_data = []
    
    for i in range(30):
        # Simulate performance degradation over time
        base_value = 1000
        trend = i * 10  # Increasing trend
        noise = random.gauss(0, 50)
        value = base_value + trend + noise
        
        historical_data.append({
            'timestamp': base_time + timedelta(days=i),
            'value': value
        })
    
    # Analyze trends
    engine = TrendAnalysisEngine()
    analysis = engine.analyze_performance_trends(historical_data)
    
    print("📈 Trend Analysis Report")
    print("=" * 50)
    print(f"Trend Direction: {analysis.trend_line.trend_direction}")
    print(f"Trend Strength: {analysis.trend_line.trend_strength}")
    print(f"R-squared: {analysis.trend_line.r_squared:.3f}")
    print(f"P-value: {analysis.trend_line.p_value:.3f}")
    print(f"Regressions Detected: {len(analysis.regressions)}")
    print(f"Anomalies Detected: {len(analysis.anomalies)}")
    print(f"Overall Health: {analysis.overall_trend_health}")
    
    if analysis.recommendations:
        print("\n🔧 Recommendations:")
        for rec in analysis.recommendations:
            print(f"  • {rec}")
