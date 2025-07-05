"""
Professional Cointegration Testing for Statistical Arbitrage
Implements Johansen test, structural break detection, and robust validation.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.vector_ar.vecm import coint_johansen
from statsmodels.tsa.stattools import coint
import logging

logger = logging.getLogger(__name__)

class CointegrationTester:
    """
    Professional cointegration testing for pair trading.
    Implements multiple tests for robust validation.
    """
    
    def __init__(self, 
                 significance_level: float = 0.05,
                 min_observations: int = 50,
                 max_lags: int = 10):
        """
        Initialize cointegration tester.
        
        Args:
            significance_level: Significance level for tests
            min_observations: Minimum observations required
            max_lags: Maximum lags for Johansen test
        """
        self.significance_level = significance_level
        self.min_observations = min_observations
        self.max_lags = max_lags
        
    def test_cointegration(self, 
                          series1: pd.Series, 
                          series2: pd.Series,
                          test_type: str = 'comprehensive') -> Dict[str, Any]:
        """
        Comprehensive cointegration testing.
        
        Args:
            series1: First time series
            series2: Second time series
            test_type: 'johansen', 'engle_granger', or 'comprehensive'
            
        Returns:
            Dictionary with test results
        """
        if len(series1) != len(series2):
            raise ValueError("Series must have same length")
        
        if len(series1) < self.min_observations:
            return {
                'is_cointegrated': False,
                'reason': f'Insufficient data: {len(series1)} < {self.min_observations}',
                'confidence': 0.0
            }
        
        # Clean data
        series1_clean = series1.dropna()
        series2_clean = series2.dropna()
        
        if len(series1_clean) < self.min_observations:
            return {
                'is_cointegrated': False,
                'reason': f'Insufficient clean data: {len(series1_clean)} < {self.min_observations}',
                'confidence': 0.0
            }
        
        results = {}
        
        if test_type in ['johansen', 'comprehensive']:
            results['johansen'] = self._johansen_test(series1_clean, series2_clean)
        
        if test_type in ['engle_granger', 'comprehensive']:
            results['engle_granger'] = self._engle_granger_test(series1_clean, series2_clean)
        
        if test_type == 'comprehensive':
            results['structural_breaks'] = self._detect_structural_breaks(series1_clean, series2_clean)
            results['stability'] = self._test_parameter_stability(series1_clean, series2_clean)
        
        # Aggregate results
        return self._aggregate_results(results, test_type)
    
    def _johansen_test(self, series1: pd.Series, series2: pd.Series) -> Dict[str, Any]:
        """
        Johansen cointegration test (most robust for pair trading).
        
        Args:
            series1: First time series
            series2: Second time series
            
        Returns:
            Johansen test results
        """
        try:
            # Prepare data for Johansen test
            data = pd.DataFrame({'series1': series1, 'series2': series2})
            
            # Determine optimal lag length using AIC
            optimal_lags = self._select_optimal_lags(data)
            
            # Run Johansen test
            johansen_result = coint_johansen(data, det_order=0, k_ar_diff=optimal_lags)
            
            # Extract test statistics
            trace_stat = johansen_result.lr1[0]  # Trace statistic
            max_eigen_stat = johansen_result.lr2[0]  # Max eigenvalue statistic
            
            # Critical values (95% confidence)
            trace_cv_95 = johansen_result.cvt[0, 1]  # Trace critical value
            max_eigen_cv_95 = johansen_result.cvm[0, 1]  # Max eigenvalue critical value
            
            # Test for cointegration (H0: no cointegration)
            trace_reject = trace_stat > trace_cv_95
            max_eigen_reject = max_eigen_stat > max_eigen_cv_95
            
            # Cointegration rank: number of statistics above critical value
            coint_rank = int((trace_stat > trace_cv_95) + (max_eigen_stat > max_eigen_cv_95))
            
            # Cointegrating vector (normalized)
            coint_vector = johansen_result.evec[:, 0] if coint_rank > 0 else None
            
            return {
                'is_cointegrated': trace_reject and max_eigen_reject,
                'trace_statistic': float(trace_stat),
                'trace_critical_value': float(trace_cv_95),
                'max_eigen_statistic': float(max_eigen_stat),
                'max_eigen_critical_value': float(max_eigen_cv_95),
                'cointegration_rank': coint_rank,
                'cointegrating_vector': coint_vector.tolist() if coint_vector is not None else None,
                'optimal_lags': optimal_lags,
                'confidence': 0.95 if trace_reject and max_eigen_reject else 0.0
            }
            
        except Exception as e:
            logger.warning(f"Johansen test failed: {e}")
            return {
                'is_cointegrated': False,
                'error': str(e),
                'confidence': 0.0
            }
    
    def _engle_granger_test(self, series1: pd.Series, series2: pd.Series) -> Dict[str, Any]:
        """
        Engle-Granger cointegration test.
        
        Args:
            series1: First time series
            series2: Second time series
            
        Returns:
            Engle-Granger test results
        """
        try:
            # Test both directions
            test_1_2 = coint(series1, series2, autolag='AIC')
            test_2_1 = coint(series2, series1, autolag='AIC')
            
            # Use the better result (lower p-value)
            if test_1_2[1] <= test_2_1[1]:
                t_stat, p_value, critical_values = test_1_2
                direction = 'series1 ~ series2'
            else:
                t_stat, p_value, critical_values = test_2_1
                direction = 'series2 ~ series1'
            
            is_cointegrated = p_value < self.significance_level
            # Convert critical_values array to dict
            crit_dict = {'1%': float(critical_values[0]), '5%': float(critical_values[1]), '10%': float(critical_values[2])}
            
            return {
                'is_cointegrated': is_cointegrated,
                't_statistic': float(t_stat),
                'p_value': float(p_value),
                'critical_values': crit_dict,
                'direction': direction,
                'confidence': 1.0 - p_value if is_cointegrated else 0.0
            }
            
        except Exception as e:
            logger.warning(f"Engle-Granger test failed: {e}")
            return {
                'is_cointegrated': False,
                'error': str(e),
                'confidence': 0.0
            }
    
    def _detect_structural_breaks(self, series1: pd.Series, series2: pd.Series) -> Dict[str, Any]:
        """
        Detect structural breaks in the cointegrating relationship.
        
        Args:
            series1: First time series
            series2: Second time series
            
        Returns:
            Structural break analysis results
        """
        try:
            # Calculate spread
            spread = series2 - series1
            
            # Chow test for structural breaks (simplified)
            n = len(spread)
            mid_point = n // 2
            
            # Split data
            spread_1 = spread.iloc[:mid_point]
            spread_2 = spread.iloc[mid_point:]
            
            # Calculate variances
            var_1 = spread_1.var()
            var_2 = spread_2.var()
            
            # F-test for structural break
            if var_1 > 0 and var_2 > 0:
                f_stat = max(var_1, var_2) / min(var_1, var_2)
                p_value = 1.0 / f_stat  # Simplified p-value
                
                has_break = p_value < self.significance_level
            else:
                f_stat = 0.0
                p_value = 1.0
                has_break = False
            
            return {
                'has_structural_break': has_break,
                'f_statistic': float(f_stat),
                'p_value': float(p_value),
                'break_point': mid_point if has_break else None,
                'variance_ratio': float(var_2 / var_1) if var_1 > 0 else 1.0
            }
            
        except Exception as e:
            logger.warning(f"Structural break detection failed: {e}")
            return {
                'has_structural_break': False,
                'error': str(e)
            }
    
    def _test_parameter_stability(self, series1: pd.Series, series2: pd.Series) -> Dict[str, Any]:
        """
        Test parameter stability over time.
        
        Args:
            series1: First time series
            series2: Second time series
            
        Returns:
            Parameter stability test results
        """
        try:
            n = len(series1)
            window_size = min(50, n // 4)
            
            # Rolling correlation
            rolling_corr = series1.rolling(window=window_size).corr(series2)
            
            # Calculate stability metrics
            corr_mean = rolling_corr.mean()
            corr_std = rolling_corr.std()
            corr_stability = 1.0 / (1.0 + corr_std) if corr_std > 0 else 1.0
            
            # Check for significant changes
            corr_changes = rolling_corr.diff().abs()
            max_change = corr_changes.max()
            avg_change = corr_changes.mean()
            
            is_stable = corr_stability > 0.7 and max_change < 0.3
            
            return {
                'is_stable': is_stable,
                'correlation_mean': float(corr_mean),
                'correlation_std': float(corr_std),
                'stability_score': float(corr_stability),
                'max_correlation_change': float(max_change),
                'avg_correlation_change': float(avg_change)
            }
            
        except Exception as e:
            logger.warning(f"Parameter stability test failed: {e}")
            return {
                'is_stable': False,
                'error': str(e)
            }
    
    def _select_optimal_lags(self, data: pd.DataFrame) -> int:
        """
        Select optimal lag length. JohansenTestResult does not provide AIC, so use a simple rule.
        
        Args:
            data: Time series data
            
        Returns:
            Optimal number of lags
        """
        # Use a simple rule: 1 lag if enough data, else min(self.max_lags, len(data)//10)
        if len(data) > 50:
            return min(self.max_lags, 2)
        else:
            return 1
    
    def _aggregate_results(self, results: Dict[str, Any], test_type: str) -> Dict[str, Any]:
        """
        Aggregate test results into final decision.
        
        Args:
            results: Individual test results
            test_type: Type of testing performed
            
        Returns:
            Aggregated results
        """
        if test_type == 'johansen':
            johansen_result = results.get('johansen', {})
            return {
                'is_cointegrated': johansen_result.get('is_cointegrated', False),
                'confidence': johansen_result.get('confidence', 0.0),
                'test_type': 'johansen',
                'details': johansen_result
            }
        
        elif test_type == 'engle_granger':
            eg_result = results.get('engle_granger', {})
            return {
                'is_cointegrated': eg_result.get('is_cointegrated', False),
                'confidence': eg_result.get('confidence', 0.0),
                'test_type': 'engle_granger',
                'details': eg_result
            }
        
        else:  # comprehensive
            # Weighted decision based on multiple tests
            johansen_result = results.get('johansen', {})
            eg_result = results.get('engle_granger', {})
            structural_result = results.get('structural_breaks', {})
            stability_result = results.get('stability', {})
            
            # Johansen test gets highest weight (most robust)
            johansen_weight = 0.5
            eg_weight = 0.3
            structural_weight = 0.1
            stability_weight = 0.1
            
            # Calculate weighted confidence
            confidence = 0.0
            if johansen_result.get('is_cointegrated', False):
                confidence += johansen_weight * johansen_result.get('confidence', 0.0)
            
            if eg_result.get('is_cointegrated', False):
                confidence += eg_weight * eg_result.get('confidence', 0.0)
            
            # Penalize for structural breaks
            if not structural_result.get('has_structural_break', False):
                confidence += structural_weight
            
            # Penalize for instability
            if stability_result.get('is_stable', False):
                confidence += stability_weight
            
            # Final decision
            is_cointegrated = confidence > 0.6
            
            return {
                'is_cointegrated': is_cointegrated,
                'confidence': confidence,
                'test_type': 'comprehensive',
                'details': {
                    'johansen': johansen_result,
                    'engle_granger': eg_result,
                    'structural_breaks': structural_result,
                    'stability': stability_result
                }
            }

def test_cointegration_robust(series1: pd.Series, 
                             series2: pd.Series, 
                             significance_level: float = 0.05) -> Dict[str, Any]:
    """
    Robust cointegration testing with multiple methods.
    
    Args:
        series1: First time series
        series2: Second time series
        significance_level: Significance level for tests
        
    Returns:
        Comprehensive cointegration test results
    """
    tester = CointegrationTester(significance_level=significance_level)
    return tester.test_cointegration(series1, series2, test_type='comprehensive') 