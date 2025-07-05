"""
Robust stationarity testing for quantitative trading.
"""
import pandas as pd
import numpy as np
from statsmodels.tsa.stattools import adfuller
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class StationarityTester:
    """Robust stationarity testing with multiple methods."""
    
    def __init__(self, window_size: int = 100, min_observations: int = 20):
        self.window_size = window_size
        self.min_observations = min_observations
        self.stationarity_history = []
        
    def adf_test(self, series: pd.Series, significance_level: float = 0.05) -> Tuple[bool, float]:
        """
        Augmented Dickey-Fuller test for stationarity.
        """
        if len(series) < self.min_observations:
            return False, 1.0
        
        try:
            # Remove any remaining NaN values
            clean_series = series.dropna()
            if len(clean_series) < self.min_observations:
                return False, 1.0
            
            # Check for constant series
            if clean_series.std() == 0:
                return True, 0.0
            
            # Perform ADF test
            adf_result = adfuller(clean_series, regression='c', autolag='AIC')
            p_value = float(adf_result[1])  # Ensure it's a float
            
            return p_value < significance_level, p_value
            
        except Exception as e:
            logger.warning(f"ADF test failed: {e}")
            return False, 1.0
    
    def rolling_stationarity_test(self, series: pd.Series, 
                                significance_level: float = 0.05) -> bool:
        """
        Rolling window stationarity test for robust assessment.
        """
        if len(series) < self.window_size:
            return True  # Assume stationary if insufficient data
        
        # Use rolling window to test recent stationarity
        recent_series = series.tail(self.window_size)
        
        # Perform multiple tests for robustness
        is_stationary_adf, p_value = self.adf_test(recent_series, significance_level)
        
        # Additional checks for robustness
        is_stationary_variance = self._check_variance_stability(recent_series)
        is_stationary_mean = self._check_mean_stability(recent_series)
        
        # Combined decision
        stationarity_score = sum([is_stationary_adf, is_stationary_variance, is_stationary_mean])
        is_stationary = stationarity_score >= 2  # At least 2 out of 3 tests pass
        
        # Log results
        logger.debug(f"Stationarity test: ADF={is_stationary_adf}(p={p_value:.4f}), "
                    f"Variance={is_stationary_variance}, Mean={is_stationary_mean}")
        
        return is_stationary
    
    def _check_variance_stability(self, series: pd.Series, threshold: float = 0.5) -> bool:
        """
        Check if variance is relatively stable over time.
        """
        if len(series) < 20:
            return True
        
        # Split series into two halves
        mid_point = len(series) // 2
        first_half = series.iloc[:mid_point]
        second_half = series.iloc[mid_point:]
        
        # Compare variances
        var_ratio = second_half.var() / first_half.var()
        if var_ratio == 0:
            return True
        
        # Check if variance ratio is within reasonable bounds
        return 1/threshold <= var_ratio <= threshold
    
    def _check_mean_stability(self, series: pd.Series, threshold: float = 2.0) -> bool:
        """
        Check if mean is relatively stable over time.
        """
        if len(series) < 20:
            return True
        
        # Split series into two halves
        mid_point = len(series) // 2
        first_half = series.iloc[:mid_point]
        second_half = series.iloc[mid_point:]
        
        # Compare means using t-test approach
        mean_diff = abs(second_half.mean() - first_half.mean())
        pooled_std = np.sqrt((first_half.var() + second_half.var()) / 2)
        
        if pooled_std == 0:
            return True
        
        # Normalized mean difference
        normalized_diff = mean_diff / pooled_std
        return normalized_diff <= threshold
    
    def update_stationarity_history(self, series: pd.Series, is_stationary: bool):
        """Update stationarity history for trend analysis."""
        self.stationarity_history.append({
            'timestamp': series.index[-1] if len(series) > 0 else pd.Timestamp.now(),
            'is_stationary': is_stationary,
            'series_length': len(series)
        })
        
        # Keep only recent history
        if len(self.stationarity_history) > 100:
            self.stationarity_history = self.stationarity_history[-50:]
    
    def get_stationarity_trend(self) -> Optional[float]:
        """
        Calculate trend in stationarity over time.
        Returns positive value if becoming more stationary, negative if less.
        """
        if len(self.stationarity_history) < 10:
            return None
        
        # Calculate rolling stationarity rate
        recent_history = self.stationarity_history[-20:]
        stationarity_rate = sum(1 for h in recent_history if h['is_stationary']) / len(recent_history)
        
        return stationarity_rate

def is_stationary_robust(series: pd.Series, window_size: int = 100) -> bool:
    """
    Robust stationarity check using rolling window approach.
    """
    tester = StationarityTester(window_size=window_size)
    return tester.rolling_stationarity_test(series)

def check_stationarity_with_confidence(series: pd.Series, 
                                     confidence_level: float = 0.95) -> Tuple[bool, float]:
    """
    Stationarity check with confidence level.
    """
    tester = StationarityTester()
    is_stationary, p_value = tester.adf_test(series, significance_level=1-confidence_level)
    return is_stationary, p_value 