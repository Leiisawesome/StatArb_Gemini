"""
Statistical Analysis Engine for Performance Testing
Enhanced statistical analysis with significance validation, confidence intervals,
and comprehensive performance metrics for institutional-grade testing.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
import scipy.stats as stats
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class StatisticalMetrics:
    """Comprehensive statistical metrics for performance analysis"""
    
    # Basic statistics
    sample_count: int
    mean: float
    median: float
    std_dev: float
    variance: float
    
    # Percentiles
    p25: float
    p50: float
    p75: float
    p90: float
    p95: float
    p99: float
    p999: float
    
    # Range statistics
    min_value: float
    max_value: float
    range_value: float
    iqr: float  # Interquartile range
    
    # Distribution characteristics
    skewness: float
    kurtosis: float
    
    # Confidence intervals
    mean_ci_95: Tuple[float, float]
    mean_ci_99: Tuple[float, float]
    std_ci_95: Tuple[float, float]
    
    # Statistical significance
    is_normal_distributed: bool
    shapiro_p_value: float
    anderson_darling_statistic: float
    
    # Outlier detection
    outlier_count: int
    outlier_percentage: float
    
    # Performance characteristics
    coefficient_of_variation: float
    stability_score: float

@dataclass
class ConfidenceInterval:
    """Confidence interval with statistical properties"""
    lower_bound: float
    upper_bound: float
    confidence_level: float
    margin_of_error: float
    sample_size: int
    degrees_of_freedom: int
    critical_value: float

@dataclass
class StatisticalSignificance:
    """Statistical significance analysis"""
    is_significant: bool
    p_value: float
    effect_size: float
    statistical_power: float
    minimum_detectable_effect: float
    required_sample_size: int
    confidence_level: float

class StatisticalAnalysisEngine:
    """Enhanced statistical analysis for testing validation"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.minimum_samples = self.config.get('minimum_samples', 1000)
        self.confidence_level = self.config.get('confidence_level', 0.95)
        self.margin_of_error = self.config.get('margin_of_error', 0.05)
        self.significance_level = self.config.get('significance_level', 0.05)
        
        # Performance standards
        self.performance_standards = {
            'latency_p99_max_ms': 10.0,
            'latency_p95_max_ms': 5.0,
            'latency_p999_max_ms': 20.0,
            'memory_efficiency_min': 85.0,
            'throughput_min_ops_per_sec': 1000.0,
            'stability_min_score': 80.0
        }
    
    def validate_statistical_significance(self, measurements: List[float]) -> Dict[str, Any]:
        """Validate statistical significance of measurements"""
        
        if not measurements:
            return {
                'valid': False,
                'reason': 'No measurements provided',
                'required_samples': self.minimum_samples,
                'actual_samples': 0,
                'recommendation': f'Provide at least {self.minimum_samples} measurements'
            }
        
        # Check sample size
        if len(measurements) < self.minimum_samples:
            return {
                'valid': False,
                'reason': 'Insufficient sample size',
                'required_samples': self.minimum_samples,
                'actual_samples': len(measurements),
                'recommendation': f'Increase sample size to {self.minimum_samples}'
            }
        
        # Calculate comprehensive statistics
        stats_metrics = self._calculate_comprehensive_statistics(measurements)
        
        # Validate confidence interval
        confidence_interval = self._calculate_confidence_interval(measurements)
        
        # Check if meets standards
        meets_standards = self._validate_performance_standards(stats_metrics)
        
        # Calculate statistical power
        statistical_power = self._calculate_statistical_power(measurements)
        
        return {
            'valid': True,
            'statistics': stats_metrics,
            'confidence_interval': confidence_interval,
            'meets_standards': meets_standards,
            'statistical_power': statistical_power,
            'sample_adequacy': self._assess_sample_adequacy(measurements),
            'distribution_analysis': self._analyze_distribution(measurements)
        }
    
    def _calculate_comprehensive_statistics(self, measurements: List[float]) -> StatisticalMetrics:
        """Calculate comprehensive statistical metrics"""
        
        measurements_array = np.array(measurements)
        n = len(measurements)
        
        # Basic statistics
        mean = np.mean(measurements_array)
        median = np.median(measurements_array)
        std_dev = np.std(measurements_array, ddof=1)
        variance = np.var(measurements_array, ddof=1)
        
        # Percentiles
        percentiles = np.percentile(measurements_array, [25, 50, 75, 90, 95, 99, 99.9])
        
        # Range statistics
        min_value = np.min(measurements_array)
        max_value = np.max(measurements_array)
        range_value = max_value - min_value
        iqr = percentiles[2] - percentiles[0]  # Q3 - Q1
        
        # Distribution characteristics
        skewness = stats.skew(measurements_array)
        kurtosis = stats.kurtosis(measurements_array)
        
        # Confidence intervals
        mean_ci_95 = self._calculate_mean_confidence_interval(measurements_array, 0.95)
        mean_ci_99 = self._calculate_mean_confidence_interval(measurements_array, 0.99)
        std_ci_95 = self._calculate_std_confidence_interval(measurements_array, 0.95)
        
        # Statistical tests
        is_normal_distributed, shapiro_p_value = self._test_normality(measurements_array)
        anderson_darling_statistic = self._anderson_darling_test(measurements_array)
        
        # Outlier detection
        outlier_count, outlier_percentage = self._detect_outliers(measurements_array)
        
        # Performance characteristics
        coefficient_of_variation = (std_dev / mean) * 100 if mean != 0 else 0
        stability_score = self._calculate_stability_score(measurements_array)
        
        return StatisticalMetrics(
            sample_count=n,
            mean=mean,
            median=median,
            std_dev=std_dev,
            variance=variance,
            p25=percentiles[0],
            p50=percentiles[1],
            p75=percentiles[2],
            p90=percentiles[3],
            p95=percentiles[4],
            p99=percentiles[5],
            p999=percentiles[6],
            min_value=min_value,
            max_value=max_value,
            range_value=range_value,
            iqr=iqr,
            skewness=skewness,
            kurtosis=kurtosis,
            mean_ci_95=mean_ci_95,
            mean_ci_99=mean_ci_99,
            std_ci_95=std_ci_95,
            is_normal_distributed=is_normal_distributed,
            shapiro_p_value=shapiro_p_value,
            anderson_darling_statistic=anderson_darling_statistic,
            outlier_count=outlier_count,
            outlier_percentage=outlier_percentage,
            coefficient_of_variation=coefficient_of_variation,
            stability_score=stability_score
        )
    
    def _calculate_confidence_interval(self, measurements: List[float]) -> ConfidenceInterval:
        """Calculate confidence interval for measurements"""
        
        measurements_array = np.array(measurements)
        n = len(measurements_array)
        mean = np.mean(measurements_array)
        std_dev = np.std(measurements_array, ddof=1)
        
        # Calculate critical value
        alpha = 1 - self.confidence_level
        degrees_of_freedom = n - 1
        critical_value = stats.t.ppf(1 - alpha/2, degrees_of_freedom)
        
        # Calculate margin of error
        margin_of_error = critical_value * (std_dev / np.sqrt(n))
        
        # Calculate confidence interval
        lower_bound = mean - margin_of_error
        upper_bound = mean + margin_of_error
        
        return ConfidenceInterval(
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            confidence_level=self.confidence_level,
            margin_of_error=margin_of_error,
            sample_size=n,
            degrees_of_freedom=degrees_of_freedom,
            critical_value=critical_value
        )
    
    def _calculate_mean_confidence_interval(self, measurements: np.ndarray, confidence_level: float) -> Tuple[float, float]:
        """Calculate confidence interval for the mean"""
        n = len(measurements)
        mean = np.mean(measurements)
        std_dev = np.std(measurements, ddof=1)
        
        alpha = 1 - confidence_level
        degrees_of_freedom = n - 1
        critical_value = stats.t.ppf(1 - alpha/2, degrees_of_freedom)
        
        margin_of_error = critical_value * (std_dev / np.sqrt(n))
        
        return (mean - margin_of_error, mean + margin_of_error)
    
    def _calculate_std_confidence_interval(self, measurements: np.ndarray, confidence_level: float) -> Tuple[float, float]:
        """Calculate confidence interval for the standard deviation"""
        n = len(measurements)
        std_dev = np.std(measurements, ddof=1)
        
        alpha = 1 - confidence_level
        degrees_of_freedom = n - 1
        
        # Chi-square distribution for standard deviation
        chi2_lower = stats.chi2.ppf(alpha/2, degrees_of_freedom)
        chi2_upper = stats.chi2.ppf(1 - alpha/2, degrees_of_freedom)
        
        lower_bound = std_dev * np.sqrt(degrees_of_freedom / chi2_upper)
        upper_bound = std_dev * np.sqrt(degrees_of_freedom / chi2_lower)
        
        return (lower_bound, upper_bound)
    
    def _test_normality(self, measurements: np.ndarray) -> Tuple[bool, float]:
        """Test if measurements follow normal distribution"""
        if len(measurements) < 3:
            return False, 1.0
        
        # Shapiro-Wilk test for normality
        try:
            statistic, p_value = stats.shapiro(measurements)
            is_normal = p_value > self.significance_level
            return is_normal, p_value
        except Exception:
            return False, 0.0
    
    def _anderson_darling_test(self, measurements: np.ndarray) -> float:
        """Anderson-Darling test for normality"""
        try:
            result = stats.anderson(measurements, dist='norm')
            return result.statistic
        except Exception:
            return float('inf')
    
    def _detect_outliers(self, measurements: np.ndarray) -> Tuple[int, float]:
        """Detect outliers using IQR method"""
        Q1 = np.percentile(measurements, 25)
        Q3 = np.percentile(measurements, 75)
        IQR = Q3 - Q1
        
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        outliers = measurements[(measurements < lower_bound) | (measurements > upper_bound)]
        outlier_count = len(outliers)
        outlier_percentage = (outlier_count / len(measurements)) * 100
        
        return outlier_count, outlier_percentage
    
    def _calculate_stability_score(self, measurements: np.ndarray) -> float:
        """Calculate stability score based on coefficient of variation"""
        mean = np.mean(measurements)
        std_dev = np.std(measurements)
        
        if mean == 0:
            return 0.0
        
        cv = std_dev / mean
        # Convert to stability score (0-100, higher is better)
        stability_score = max(0, 100 - (cv * 100))
        return min(100, stability_score)
    
    def _validate_performance_standards(self, stats: StatisticalMetrics) -> Dict[str, bool]:
        """Validate performance against institutional standards"""
        
        # Convert measurements to appropriate units (assuming microseconds for latency)
        p99_ms = stats.p99 / 1000  # Convert to milliseconds
        p95_ms = stats.p95 / 1000
        p999_ms = stats.p999 / 1000
        
        standards_met = {
            'latency_p99': p99_ms <= self.performance_standards['latency_p99_max_ms'],
            'latency_p95': p95_ms <= self.performance_standards['latency_p95_max_ms'],
            'latency_p999': p999_ms <= self.performance_standards['latency_p999_max_ms'],
            'memory_efficiency': stats.stability_score >= self.performance_standards['memory_efficiency_min'],
            'stability': stats.stability_score >= self.performance_standards['stability_min_score'],
            'outlier_control': stats.outlier_percentage <= 5.0,  # Max 5% outliers
            'distribution_normal': stats.is_normal_distributed
        }
        
        return standards_met
    
    def _calculate_statistical_power(self, measurements: List[float]) -> float:
        """Calculate statistical power of the test with improved edge case handling"""
        n = len(measurements)
        if n < 2:
            return 0.0
        
        measurements_array = np.array(measurements)
        mean = np.mean(measurements_array)
        std_dev = np.std(measurements_array, ddof=1)
        
        # Handle edge cases
        if std_dev == 0:
            # All values are identical - no power to detect differences
            return 0.0
        
        if np.isnan(mean) or np.isnan(std_dev):
            return 0.0
        
        # Effect size (Cohen's d) - assume we're testing against null hypothesis of mean = 0
        effect_size = abs(mean) / std_dev
        
        # Handle very small effect sizes
        if effect_size < 0.01:
            return 0.0
        
        # Calculate power using t-test with improved error handling
        try:
            # Ensure we have valid parameters
            if n < 2 or effect_size <= 0 or self.significance_level <= 0 or self.significance_level >= 1:
                return 0.0
            
            # Use scipy's power calculation with bounds checking
            try:
                from scipy.stats import power
                power_value = power.ttest_power(
                    effect_size=effect_size, 
                    nobs=n, 
                    alpha=self.significance_level,
                    alternative='two-sided'
                )
            except (ImportError, AttributeError):
                # Fallback to manual power calculation
                # Approximate power using t-distribution
                t_critical = stats.t.ppf(1 - self.significance_level/2, n-1)
                t_effect = effect_size * np.sqrt(n)
                power_value = 1 - stats.t.cdf(t_critical - t_effect, n-1) + stats.t.cdf(-t_critical - t_effect, n-1)
            
            # Ensure power is within valid range
            if np.isnan(power_value) or np.isinf(power_value):
                return 0.0
            
            return min(1.0, max(0.0, power_value))
            
        except (ValueError, OverflowError, ZeroDivisionError) as e:
            logger.warning(f"Statistical power calculation failed: {e}")
            return 0.0
        except Exception as e:
            logger.warning(f"Unexpected error in power calculation: {e}")
            return 0.0
    
    def _assess_sample_adequacy(self, measurements: List[float]) -> Dict[str, Any]:
        """Assess if sample size is adequate for reliable results"""
        n = len(measurements)
        
        # Calculate required sample size for desired precision
        measurements_array = np.array(measurements)
        std_dev = np.std(measurements_array, ddof=1)
        mean = np.mean(measurements_array)
        
        # Required sample size for margin of error
        z_score = stats.norm.ppf(1 - (1 - self.confidence_level) / 2)
        required_n = (z_score * std_dev / (mean * self.margin_of_error)) ** 2
        
        return {
            'current_sample_size': n,
            'required_sample_size': int(np.ceil(required_n)),
            'is_adequate': n >= required_n,
            'adequacy_ratio': n / required_n if required_n > 0 else float('inf'),
            'recommendation': 'Increase sample size' if n < required_n else 'Sample size adequate'
        }
    
    def _analyze_distribution(self, measurements: List[float]) -> Dict[str, Any]:
        """Analyze the distribution of measurements"""
        measurements_array = np.array(measurements)
        
        # Distribution characteristics
        skewness = stats.skew(measurements_array)
        kurtosis = stats.kurtosis(measurements_array)
        
        # Distribution type assessment
        if abs(skewness) < 0.5 and abs(kurtosis) < 0.5:
            distribution_type = 'approximately_normal'
        elif skewness > 0.5:
            distribution_type = 'right_skewed'
        elif skewness < -0.5:
            distribution_type = 'left_skewed'
        elif kurtosis > 0.5:
            distribution_type = 'heavy_tailed'
        else:
            distribution_type = 'unknown'
        
        return {
            'distribution_type': distribution_type,
            'skewness': skewness,
            'kurtosis': kurtosis,
            'is_normal': abs(skewness) < 0.5 and abs(kurtosis) < 0.5,
            'tail_behavior': 'heavy' if kurtosis > 0.5 else 'light',
            'symmetry': 'symmetric' if abs(skewness) < 0.5 else 'asymmetric'
        }
    
    def calculate_effect_size(self, group1: List[float], group2: List[float]) -> float:
        """Calculate Cohen's d effect size between two groups"""
        if not group1 or not group2:
            return 0.0
        
        mean1, mean2 = np.mean(group1), np.mean(group2)
        std1, std2 = np.std(group1, ddof=1), np.std(group2, ddof=1)
        
        # Pooled standard deviation
        n1, n2 = len(group1), len(group2)
        pooled_std = np.sqrt(((n1 - 1) * std1**2 + (n2 - 1) * std2**2) / (n1 + n2 - 2))
        
        if pooled_std == 0:
            return 0.0
        
        return abs(mean1 - mean2) / pooled_std
    
    def calculate_statistical_power_for_comparison(self, group1: List[float], group2: List[float]) -> float:
        """Calculate statistical power for comparing two groups with improved edge case handling"""
        if not group1 or not group2:
            return 0.0
        
        n1, n2 = len(group1), len(group2)
        if n1 < 2 or n2 < 2:
            return 0.0
        
        # Calculate effect size with improved error handling
        effect_size = self.calculate_effect_size(group1, group2)
        
        # Handle edge cases
        if effect_size <= 0 or np.isnan(effect_size) or np.isinf(effect_size):
            return 0.0
        
        # Use harmonic mean for more accurate power calculation
        n_harmonic = 2 * n1 * n2 / (n1 + n2) if (n1 + n2) > 0 else 0
        
        if n_harmonic < 2:
            return 0.0
        
        try:
            # Ensure valid parameters
            if (effect_size <= 0 or n_harmonic < 2 or 
                self.significance_level <= 0 or self.significance_level >= 1):
                return 0.0
            
            # Calculate power with bounds checking
            try:
                from scipy.stats import power
                power_value = power.ttest_power(
                    effect_size=effect_size,
                    nobs=n_harmonic,
                    alpha=self.significance_level,
                    alternative='two-sided'
                )
            except (ImportError, AttributeError):
                # Fallback to manual power calculation
                t_critical = stats.t.ppf(1 - self.significance_level/2, n_harmonic-1)
                t_effect = effect_size * np.sqrt(n_harmonic)
                power_value = 1 - stats.t.cdf(t_critical - t_effect, n_harmonic-1) + stats.t.cdf(-t_critical - t_effect, n_harmonic-1)
            
            # Ensure power is within valid range
            if np.isnan(power_value) or np.isinf(power_value):
                return 0.0
            
            return min(1.0, max(0.0, power_value))
            
        except (ValueError, OverflowError, ZeroDivisionError) as e:
            logger.warning(f"Group comparison power calculation failed: {e}")
            return 0.0
        except Exception as e:
            logger.warning(f"Unexpected error in group power calculation: {e}")
            return 0.0
    
    def generate_statistical_report(self, measurements: List[float], test_name: str = "Performance Test") -> Dict[str, Any]:
        """Generate comprehensive statistical report"""
        
        if not measurements:
            return {
                'test_name': test_name,
                'status': 'failed',
                'reason': 'No measurements provided',
                'recommendations': ['Provide measurement data']
            }
        
        # Validate statistical significance
        validation_result = self.validate_statistical_significance(measurements)
        
        if not validation_result['valid']:
            return {
                'test_name': test_name,
                'status': 'failed',
                'reason': validation_result['reason'],
                'recommendations': [validation_result['recommendation']]
            }
        
        # Extract results
        stats = validation_result['statistics']
        standards = validation_result['meets_standards']
        power = validation_result['statistical_power']
        
        # Determine overall status
        all_standards_met = all(standards.values())
        adequate_power = power >= 0.8
        
        status = 'passed' if all_standards_met and adequate_power else 'warning' if all_standards_met else 'failed'
        
        # Generate recommendations
        recommendations = []
        if not standards['latency_p99']:
            recommendations.append(f"Optimize P99 latency (current: {stats.p99/1000:.2f}ms, target: ≤{self.performance_standards['latency_p99_max_ms']}ms)")
        if not standards['latency_p95']:
            recommendations.append(f"Optimize P95 latency (current: {stats.p95/1000:.2f}ms, target: ≤{self.performance_standards['latency_p95_max_ms']}ms)")
        if not standards['stability']:
            recommendations.append(f"Improve stability (current: {stats.stability_score:.1f}%, target: ≥{self.performance_standards['stability_min_score']}%)")
        if not adequate_power:
            recommendations.append(f"Increase sample size for adequate statistical power (current: {power:.2f}, target: ≥0.8)")
        
        return {
            'test_name': test_name,
            'status': status,
            'statistics': {
                'sample_count': stats.sample_count,
                'mean': stats.mean,
                'median': stats.median,
                'std_dev': stats.std_dev,
                'p95': stats.p95,
                'p99': stats.p99,
                'p999': stats.p999,
                'stability_score': stats.stability_score,
                'outlier_percentage': stats.outlier_percentage
            },
            'standards_met': standards,
            'statistical_power': power,
            'confidence_interval': {
                'mean_95': stats.mean_ci_95,
                'mean_99': stats.mean_ci_99
            },
            'distribution_analysis': validation_result['distribution_analysis'],
            'recommendations': recommendations,
            'overall_score': self._calculate_overall_score(stats, standards, power)
        }
    
    def _calculate_overall_score(self, stats: StatisticalMetrics, standards: Dict[str, bool], power: float) -> float:
        """Calculate overall performance score"""
        score = 0.0
        max_score = 100.0
        
        # Standards compliance (60% weight)
        standards_score = sum(standards.values()) / len(standards) * 60
        score += standards_score
        
        # Statistical power (20% weight)
        power_score = power * 20
        score += power_score
        
        # Stability score (20% weight)
        stability_score = (stats.stability_score / 100) * 20
        score += stability_score
        
        return min(max_score, score)

# Convenience functions
def analyze_performance_measurements(measurements: List[float], test_name: str = "Performance Test") -> Dict[str, Any]:
    """Convenience function to analyze performance measurements"""
    engine = StatisticalAnalysisEngine()
    return engine.generate_statistical_report(measurements, test_name)

def validate_statistical_significance(measurements: List[float]) -> Dict[str, Any]:
    """Convenience function to validate statistical significance"""
    engine = StatisticalAnalysisEngine()
    return engine.validate_statistical_significance(measurements)

if __name__ == "__main__":
    # Test the statistical analysis engine
    import random
    
    # Generate sample data
    sample_data = [random.gauss(1000, 100) for _ in range(1000)]
    
    # Analyze the data
    engine = StatisticalAnalysisEngine()
    report = engine.generate_statistical_report(sample_data, "Sample Performance Test")
    
    print("📊 Statistical Analysis Report")
    print("=" * 50)
    print(f"Test Name: {report['test_name']}")
    print(f"Status: {report['status']}")
    print(f"Overall Score: {report['overall_score']:.1f}/100")
    print(f"Sample Count: {report['statistics']['sample_count']}")
    print(f"Mean: {report['statistics']['mean']:.2f}")
    print(f"P95: {report['statistics']['p95']:.2f}")
    print(f"P99: {report['statistics']['p99']:.2f}")
    print(f"Stability Score: {report['statistics']['stability_score']:.1f}%")
    print(f"Statistical Power: {report['statistical_power']:.2f}")
    
    if report['recommendations']:
        print("\n🔧 Recommendations:")
        for rec in report['recommendations']:
            print(f"  • {rec}")
