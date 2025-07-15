"""
Advanced Spread Calculator for StatArb Gemini Trading System
=========================================================

A comprehensive spread calculation module that supports multiple hedge ratio
estimation methods and can work with any trading pair.

Features:
- Multiple hedge ratio estimation methods (OLS, TLS, Kalman, Rolling)
- Dynamic hedge ratio updates
- Spread statistics and z-score calculations
- Cointegration-based hedge ratios
- Robust error handling and validation
- Integration with new structure components

Enhanced for StatArb Gemini system with async support and advanced analytics.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Union
import logging
import asyncio
from scipy import stats
from scipy.optimize import minimize
from sklearn.linear_model import LinearRegression
from sklearn.decomposition import PCA
from dataclasses import dataclass
import warnings

# Import new structure components
from ...infrastructure.config.base_config import BaseConfig

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)

# Optional imports for advanced features
try:
    from statsmodels.tsa.stattools import coint, adfuller
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False
    logger.warning("statsmodels not available - limited statistical tests")

try:
    import numba
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False

@dataclass
class SpreadResult:
    """Container for spread calculation results."""
    spread: pd.Series
    hedge_ratio: Union[float, pd.Series]
    spread_mean: float
    spread_std: float
    z_score: pd.Series
    method: str
    statistics: Dict[str, Any]
    confidence_interval: Optional[Tuple[float, float]] = None
    quality_metrics: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Initialize additional metrics."""
        if self.quality_metrics is None:
            self.quality_metrics = self._calculate_quality_metrics()
    
    def _calculate_quality_metrics(self) -> Dict[str, Any]:
        """Calculate quality metrics for the spread."""
        return {
            'data_points': len(self.spread),
            'spread_volatility': self.spread_std,
            'z_score_range': (self.z_score.min(), self.z_score.max()),
            'mean_reversion_strength': self._calculate_mean_reversion(),
            'outlier_ratio': self._calculate_outlier_ratio()
        }
    
    def _calculate_mean_reversion(self) -> float:
        """Calculate mean reversion strength."""
        if len(self.z_score) < 2:
            return 0.0
        
        # Calculate autocorrelation of z-scores
        z_values = self.z_score.dropna().values
        if len(z_values) < 2:
            return 0.0
        
        autocorr = np.corrcoef(z_values[:-1], z_values[1:])[0, 1]
        return 1 - autocorr if not np.isnan(autocorr) else 0.0
    
    def _calculate_outlier_ratio(self) -> float:
        """Calculate ratio of outlier observations."""
        extreme_threshold = 3.0
        outliers = (self.z_score.abs() > extreme_threshold).sum()
        return outliers / len(self.z_score) if len(self.z_score) > 0 else 0.0

@dataclass
class SpreadConfig(BaseConfig):
    """Configuration for spread calculator."""
    
    # Method selection
    hedge_ratio_method: str = 'ols'  # ols, tls, rolling_ols, exponential, kalman, pca, cointegration
    
    # Window parameters
    lookback_window: int = 60
    rolling_window: int = 252
    min_observations: int = 30
    
    # Statistical parameters
    confidence_level: float = 0.95
    outlier_threshold: float = 3.0
    
    # Dynamic parameters
    half_life: int = 30
    regularization: float = 0.0
    adaptation_speed: float = 0.1
    
    # Quality control
    min_quality_score: float = 50.0
    require_stationarity: bool = True
    max_hedge_ratio_volatility: float = 0.5
    
    # Performance optimization
    use_numba: bool = True
    cache_results: bool = True
    parallel_processing: bool = False

class SpreadCalculator:
    """
    Advanced spread calculator supporting multiple hedge ratio estimation methods.
    Designed for the StatArb Gemini system with async support and performance optimization.
    """
    
    def __init__(self, config: Optional[SpreadConfig] = None):
        """
        Initialize the spread calculator.
        
        Args:
            config: Configuration object for the calculator
        """
        self.config = config or SpreadConfig()
        self.method = self.config.hedge_ratio_method
        
        # Cache for performance
        self._cache = {} if self.config.cache_results else None
        
        # Compilation cache for numba functions
        self._compiled_functions = {}
        
        logger.info(f"Initialized SpreadCalculator with method: {self.method}")
        logger.info(f"Configuration: {self.config.dict()}")
    
    async def calculate_spread(self, 
                              price1: pd.Series, 
                              price2: pd.Series, 
                              symbol1: str = "S1", 
                              symbol2: str = "S2") -> SpreadResult:
        """
        Calculate spread using the configured method.
        
        Args:
            price1: First asset price series
            price2: Second asset price series
            symbol1: First asset symbol
            symbol2: Second asset symbol
            
        Returns:
            SpreadResult containing spread and related statistics
        """
        # Check cache first
        cache_key = f"{symbol1}_{symbol2}_{self.method}_{hash(tuple(price1.values))}_{hash(tuple(price2.values))}"
        if self._cache and cache_key in self._cache:
            logger.debug(f"Using cached result for {symbol1}/{symbol2}")
            return self._cache[cache_key]
        
        # Validate inputs
        self._validate_inputs(price1, price2)
        
        # Align data
        aligned_data = self._align_data(price1, price2)
        price1_aligned = aligned_data['price1']
        price2_aligned = aligned_data['price2']
        
        # Calculate hedge ratio using specified method
        if self.method == 'ols':
            result = await self._calculate_ols_spread(price1_aligned, price2_aligned)
        elif self.method == 'tls':
            result = await self._calculate_tls_spread(price1_aligned, price2_aligned)
        elif self.method == 'rolling_ols':
            result = await self._calculate_rolling_ols_spread(price1_aligned, price2_aligned)
        elif self.method == 'exponential':
            result = await self._calculate_exponential_spread(price1_aligned, price2_aligned)
        elif self.method == 'cointegration':
            result = await self._calculate_cointegration_spread(price1_aligned, price2_aligned)
        elif self.method == 'pca':
            result = await self._calculate_pca_spread(price1_aligned, price2_aligned)
        elif self.method == 'kalman':
            result = await self._calculate_kalman_spread(price1_aligned, price2_aligned)
        else:
            raise ValueError(f"Unknown hedge ratio method: {self.method}")
        
        # Add metadata
        result.method = self.method
        result.statistics['symbol1'] = symbol1
        result.statistics['symbol2'] = symbol2
        result.statistics['observations'] = len(price1_aligned)
        
        # Validate quality
        quality_validation = self.validate_spread_quality(result)
        result.quality_metrics.update(quality_validation)
        
        # Cache result
        if self._cache:
            self._cache[cache_key] = result
        
        logger.info(f"Calculated spread for {symbol1}/{symbol2} using {self.method}")
        logger.info(f"Quality score: {quality_validation.get('quality_score', 0):.1f}")
        
        return result
    
    def _validate_inputs(self, price1: pd.Series, price2: pd.Series):
        """Validate input data."""
        if len(price1) < self.config.min_observations or len(price2) < self.config.min_observations:
            raise ValueError(f"Insufficient data: need at least {self.config.min_observations} observations")
        
        if (price1 <= 0).any() or (price2 <= 0).any():
            raise ValueError("Prices must be positive")
        
        if price1.isnull().any() or price2.isnull().any():
            logger.warning("NaN values detected, will be handled in alignment")
    
    def _align_data(self, price1: pd.Series, price2: pd.Series) -> Dict[str, pd.Series]:
        """Align price series by index and handle missing data."""
        # Find common index
        common_index = price1.index.intersection(price2.index)
        
        if len(common_index) < self.config.min_observations:
            raise ValueError(f"Insufficient overlapping data: {len(common_index)} observations")
        
        # Align and clean data
        aligned_price1 = price1.loc[common_index].fillna(method='ffill').fillna(method='bfill')
        aligned_price2 = price2.loc[common_index].fillna(method='ffill').fillna(method='bfill')
        
        # Remove any remaining NaN values
        valid_mask = ~(aligned_price1.isna() | aligned_price2.isna())
        aligned_price1 = aligned_price1[valid_mask]
        aligned_price2 = aligned_price2[valid_mask]
        
        return {
            'price1': aligned_price1,
            'price2': aligned_price2
        }
    
    async def _calculate_ols_spread(self, price1: pd.Series, price2: pd.Series) -> SpreadResult:
        """Calculate spread using Ordinary Least Squares hedge ratio."""
        if self.config.use_numba and NUMBA_AVAILABLE:
            return await self._calculate_ols_spread_numba(price1, price2)
        
        # Prepare data for regression
        X = price2.values.reshape(-1, 1)
        y = price1.values
        
        # Fit OLS regression: price1 = alpha + beta * price2
        model = LinearRegression(fit_intercept=True)
        model.fit(X, y)
        
        hedge_ratio = model.coef_[0]
        intercept = model.intercept_
        
        # Calculate spread
        spread = price1 - hedge_ratio * price2
        
        # Calculate statistics
        spread_mean = spread.mean()
        spread_std = spread.std()
        z_score = (spread - spread_mean) / spread_std
        
        # Calculate additional statistics
        y_pred = model.predict(X)
        r_squared = model.score(X, y)
        residuals = y - y_pred
        
        # Calculate confidence interval for hedge ratio
        n = len(price1)
        mse = np.mean(residuals**2)
        var_beta = mse / np.sum((price2 - price2.mean())**2)
        se_beta = np.sqrt(var_beta)
        
        t_critical = stats.t.ppf((1 + self.config.confidence_level) / 2, n - 2)
        ci_lower = hedge_ratio - t_critical * se_beta
        ci_upper = hedge_ratio + t_critical * se_beta
        
        statistics = {
            'hedge_ratio': hedge_ratio,
            'intercept': intercept,
            'r_squared': r_squared,
            'std_error': se_beta,
            'residual_std': np.std(residuals),
            'durbin_watson': self._calculate_durbin_watson(residuals),
            'adf_pvalue': self._calculate_adf_test(spread) if STATSMODELS_AVAILABLE else np.nan,
            'jarque_bera': self._calculate_jarque_bera_test(residuals)
        }
        
        return SpreadResult(
            spread=spread,
            hedge_ratio=hedge_ratio,
            spread_mean=spread_mean,
            spread_std=spread_std,
            z_score=z_score,
            method='ols',
            statistics=statistics,
            confidence_interval=(ci_lower, ci_upper)
        )
    
    async def _calculate_ols_spread_numba(self, price1: pd.Series, price2: pd.Series) -> SpreadResult:
        """Numba-optimized OLS calculation."""
        if 'ols_numba' not in self._compiled_functions:
            self._compiled_functions['ols_numba'] = self._compile_ols_function()
        
        ols_func = self._compiled_functions['ols_numba']
        hedge_ratio, intercept, r_squared = ols_func(price1.values, price2.values)
        
        # Calculate spread
        spread = price1 - hedge_ratio * price2
        spread_mean = spread.mean()
        spread_std = spread.std()
        z_score = (spread - spread_mean) / spread_std
        
        statistics = {
            'hedge_ratio': hedge_ratio,
            'intercept': intercept,
            'r_squared': r_squared,
            'adf_pvalue': self._calculate_adf_test(spread) if STATSMODELS_AVAILABLE else np.nan
        }
        
        return SpreadResult(
            spread=spread,
            hedge_ratio=hedge_ratio,
            spread_mean=spread_mean,
            spread_std=spread_std,
            z_score=z_score,
            method='ols_numba',
            statistics=statistics
        )
    
    def _compile_ols_function(self):
        """Compile numba function for OLS calculation."""
        if not NUMBA_AVAILABLE:
            raise ImportError("numba not available")
        
        @numba.jit(nopython=True)
        def ols_calculation(y, x):
            n = len(x)
            x_mean = np.mean(x)
            y_mean = np.mean(y)
            
            numerator = np.sum((x - x_mean) * (y - y_mean))
            denominator = np.sum((x - x_mean) ** 2)
            
            hedge_ratio = numerator / denominator
            intercept = y_mean - hedge_ratio * x_mean
            
            # Calculate R-squared
            y_pred = intercept + hedge_ratio * x
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - y_mean) ** 2)
            r_squared = 1 - (ss_res / ss_tot)
            
            return hedge_ratio, intercept, r_squared
        
        return ols_calculation
    
    async def _calculate_rolling_ols_spread(self, price1: pd.Series, price2: pd.Series) -> SpreadResult:
        """Calculate spread using rolling OLS hedge ratio."""
        if self.config.parallel_processing:
            return await self._calculate_rolling_ols_parallel(price1, price2)
        
        hedge_ratios = []
        spreads = []
        
        for i in range(self.config.rolling_window, len(price1)):
            # Get rolling window data
            p1_window = price1.iloc[i-self.config.rolling_window:i]
            p2_window = price2.iloc[i-self.config.rolling_window:i]
            
            # Calculate OLS hedge ratio for this window
            X = p2_window.values.reshape(-1, 1)
            y = p1_window.values
            
            model = LinearRegression(fit_intercept=True)
            model.fit(X, y)
            
            hedge_ratio = model.coef_[0]
            hedge_ratios.append(hedge_ratio)
            
            # Calculate spread for current observation
            current_spread = price1.iloc[i] - hedge_ratio * price2.iloc[i]
            spreads.append(current_spread)
        
        # Create series with proper index
        spread_index = price1.index[self.config.rolling_window:]
        spread = pd.Series(spreads, index=spread_index)
        hedge_ratio_series = pd.Series(hedge_ratios, index=spread_index)
        
        # Calculate statistics
        spread_mean = spread.mean()
        spread_std = spread.std()
        z_score = (spread - spread_mean) / spread_std
        
        statistics = {
            'hedge_ratio_mean': hedge_ratio_series.mean(),
            'hedge_ratio_std': hedge_ratio_series.std(),
            'hedge_ratio_min': hedge_ratio_series.min(),
            'hedge_ratio_max': hedge_ratio_series.max(),
            'rolling_window': self.config.rolling_window,
            'adf_pvalue': self._calculate_adf_test(spread) if STATSMODELS_AVAILABLE else np.nan
        }
        
        return SpreadResult(
            spread=spread,
            hedge_ratio=hedge_ratio_series,
            spread_mean=spread_mean,
            spread_std=spread_std,
            z_score=z_score,
            method='rolling_ols',
            statistics=statistics
        )
    
    async def _calculate_kalman_spread(self, price1: pd.Series, price2: pd.Series) -> SpreadResult:
        """Calculate spread using Kalman filter for dynamic hedge ratio."""
        try:
            # Simple Kalman filter implementation
            hedge_ratios = []
            spreads = []
            
            # Initialize state
            hedge_ratio = 1.0  # Initial guess
            P = 1.0  # Initial uncertainty
            Q = 0.01  # Process noise
            R = 0.1   # Measurement noise
            
            for i in range(len(price1)):
                # Prediction step
                # hedge_ratio = hedge_ratio (no change in prediction)
                P = P + Q
                
                # Update step
                if price2.iloc[i] != 0:
                    innovation = price1.iloc[i] - hedge_ratio * price2.iloc[i]
                    S = P * price2.iloc[i]**2 + R  # Innovation covariance
                    K = P * price2.iloc[i] / S     # Kalman gain
                    
                    hedge_ratio = hedge_ratio + K * innovation / price2.iloc[i]
                    P = (1 - K * price2.iloc[i]) * P
                
                hedge_ratios.append(hedge_ratio)
                spreads.append(price1.iloc[i] - hedge_ratio * price2.iloc[i])
            
            # Create series
            spread = pd.Series(spreads, index=price1.index)
            hedge_ratio_series = pd.Series(hedge_ratios, index=price1.index)
            
            # Calculate statistics
            spread_mean = spread.mean()
            spread_std = spread.std()
            z_score = (spread - spread_mean) / spread_std
            
            statistics = {
                'mean_hedge_ratio': hedge_ratio_series.mean(),
                'current_hedge_ratio': hedge_ratio,
                'hedge_ratio_std': hedge_ratio_series.std(),
                'process_noise': Q,
                'measurement_noise': R,
                'adf_pvalue': self._calculate_adf_test(spread) if STATSMODELS_AVAILABLE else np.nan
            }
            
            return SpreadResult(
                spread=spread,
                hedge_ratio=hedge_ratio_series,
                spread_mean=spread_mean,
                spread_std=spread_std,
                z_score=z_score,
                method='kalman',
                statistics=statistics
            )
            
        except Exception as e:
            logger.error(f"Kalman filter failed: {e}, falling back to OLS")
            return await self._calculate_ols_spread(price1, price2)
    
    async def _calculate_cointegration_spread(self, price1: pd.Series, price2: pd.Series) -> SpreadResult:
        """Calculate spread using cointegration-based hedge ratio."""
        if not STATSMODELS_AVAILABLE:
            logger.warning("statsmodels not available, falling back to OLS")
            return await self._calculate_ols_spread(price1, price2)
        
        try:
            # Test for cointegration
            score, pvalue, crit_values = coint(price1, price2)
            
            # Use OLS for hedge ratio but validate with cointegration
            result = await self._calculate_ols_spread(price1, price2)
            
            # Update statistics with cointegration info
            result.statistics.update({
                'cointegration_score': score,
                'cointegration_pvalue': pvalue,
                'critical_values': crit_values.tolist(),
                'is_cointegrated': pvalue < 0.05,
                'cointegration_strength': max(0, 1 - pvalue)  # Strength measure
            })
            
            result.method = 'cointegration'
            
            return result
            
        except Exception as e:
            logger.error(f"Cointegration analysis failed: {e}, falling back to OLS")
            return await self._calculate_ols_spread(price1, price2)
    
    # Additional methods would be implemented similarly...
    async def _calculate_tls_spread(self, price1: pd.Series, price2: pd.Series) -> SpreadResult:
        """Total Least Squares implementation."""
        # Implementation similar to legacy but with async support
        pass
    
    async def _calculate_exponential_spread(self, price1: pd.Series, price2: pd.Series) -> SpreadResult:
        """Exponentially weighted moving average implementation."""
        # Implementation similar to legacy but with async support
        pass
    
    async def _calculate_pca_spread(self, price1: pd.Series, price2: pd.Series) -> SpreadResult:
        """PCA-based hedge ratio implementation."""
        # Implementation similar to legacy but with async support
        pass
    
    def _calculate_durbin_watson(self, residuals: np.ndarray) -> float:
        """Calculate Durbin-Watson statistic for autocorrelation."""
        if len(residuals) < 2:
            return np.nan
        diff = np.diff(residuals)
        return np.sum(diff**2) / np.sum(residuals**2)
    
    def _calculate_adf_test(self, series: pd.Series) -> float:
        """Calculate Augmented Dickey-Fuller test p-value."""
        if not STATSMODELS_AVAILABLE:
            return np.nan
        
        try:
            result = adfuller(series.dropna())
            return result[1]  # p-value
        except Exception as e:
            logger.warning(f"ADF test failed: {e}")
            return np.nan
    
    def _calculate_jarque_bera_test(self, residuals: np.ndarray) -> Dict[str, float]:
        """Calculate Jarque-Bera test for normality."""
        try:
            from scipy.stats import jarque_bera
            statistic, pvalue = jarque_bera(residuals)
            return {'jb_statistic': statistic, 'jb_pvalue': pvalue}
        except Exception:
            return {'jb_statistic': np.nan, 'jb_pvalue': np.nan}
    
    def validate_spread_quality(self, result: SpreadResult) -> Dict[str, Any]:
        """
        Validate the quality of the spread calculation.
        
        Args:
            result: SpreadResult to validate
            
        Returns:
            Dictionary with validation results
        """
        validation = {
            'valid': True,
            'issues': [],
            'warnings': [],
            'quality_score': 0.0
        }
        
        spread = result.spread
        
        # Check for sufficient data
        if len(spread) < self.config.min_observations:
            validation['valid'] = False
            validation['issues'].append(f"Insufficient data: {len(spread)} observations")
            return validation
        
        # Check for stationarity (ADF test)
        adf_pvalue = result.statistics.get('adf_pvalue', np.nan)
        if not np.isnan(adf_pvalue):
            if adf_pvalue > 0.05:
                if self.config.require_stationarity:
                    validation['issues'].append(f"Spread not stationary (ADF p-value: {adf_pvalue:.4f})")
                else:
                    validation['warnings'].append(f"Spread may not be stationary (ADF p-value: {adf_pvalue:.4f})")
            else:
                validation['quality_score'] += 25  # Stationary spread is good
        
        # Check hedge ratio stability (for dynamic ratios)
        if isinstance(result.hedge_ratio, pd.Series):
            hr_std = result.hedge_ratio.std()
            hr_mean = result.hedge_ratio.mean()
            if hr_mean != 0 and hr_std / abs(hr_mean) > self.config.max_hedge_ratio_volatility:
                validation['warnings'].append("Hedge ratio is highly variable")
            else:
                validation['quality_score'] += 25  # Stable hedge ratio is good
        
        # Check spread distribution
        if abs(spread.skew()) > 2:
            validation['warnings'].append(f"Spread is highly skewed ({spread.skew():.2f})")
        else:
            validation['quality_score'] += 25  # Normal distribution is good
        
        # Check for outliers
        z_scores = result.z_score
        extreme_count = (z_scores.abs() > self.config.outlier_threshold).sum()
        if extreme_count > len(z_scores) * 0.01:  # More than 1% extreme values
            validation['warnings'].append(f"High number of extreme values: {extreme_count}")
        else:
            validation['quality_score'] += 25  # Few outliers is good
        
        # Overall quality assessment
        if validation['quality_score'] < self.config.min_quality_score:
            validation['warnings'].append(f"Low quality score: {validation['quality_score']:.1f}")
        
        return validation
    
    async def update_spread_realtime(self, 
                                   result: SpreadResult, 
                                   new_price1: float, 
                                   new_price2: float,
                                   timestamp: Optional[pd.Timestamp] = None) -> SpreadResult:
        """
        Update spread calculation with new price data in real-time.
        
        Args:
            result: Previous spread result
            new_price1: New price for first asset
            new_price2: New price for second asset
            timestamp: Timestamp for new data point
            
        Returns:
            Updated SpreadResult
        """
        if timestamp is None:
            timestamp = pd.Timestamp.now()
        
        # Handle dynamic vs static hedge ratios
        if isinstance(result.hedge_ratio, pd.Series):
            # For dynamic hedge ratios, update using the method
            if result.method == 'kalman':
                current_hedge_ratio = await self._update_kalman_hedge_ratio(
                    result, new_price1, new_price2
                )
            else:
                # Use the last value for other dynamic methods
                current_hedge_ratio = result.hedge_ratio.iloc[-1]
        else:
            current_hedge_ratio = result.hedge_ratio
        
        # Calculate new spread value
        new_spread = new_price1 - current_hedge_ratio * new_price2
        
        # Update spread series (keep only recent data for efficiency)
        max_history = self.config.lookback_window * 2
        updated_spread = pd.concat([
            result.spread.tail(max_history - 1), 
            pd.Series([new_spread], index=[timestamp])
        ])
        
        # Recalculate statistics using exponential weighting for efficiency
        alpha = self.config.adaptation_speed
        new_mean = alpha * new_spread + (1 - alpha) * result.spread_mean
        new_std = np.sqrt(alpha * (new_spread - new_mean)**2 + (1 - alpha) * result.spread_std**2)
        
        # Calculate z-score
        z_score = (updated_spread - new_mean) / new_std if new_std > 0 else pd.Series([0], index=[timestamp])
        
        # Create updated result
        updated_result = SpreadResult(
            spread=updated_spread,
            hedge_ratio=result.hedge_ratio,
            spread_mean=new_mean,
            spread_std=new_std,
            z_score=z_score,
            method=result.method,
            statistics=result.statistics.copy(),
            confidence_interval=result.confidence_interval
        )
        
        return updated_result
    
    async def _update_kalman_hedge_ratio(self, result: SpreadResult, 
                                       new_price1: float, new_price2: float) -> float:
        """Update Kalman filter hedge ratio with new data."""
        # Get current state from statistics
        current_hr = result.statistics.get('current_hedge_ratio', 1.0)
        current_P = result.statistics.get('current_uncertainty', 1.0)
        Q = result.statistics.get('process_noise', 0.01)
        R = result.statistics.get('measurement_noise', 0.1)
        
        # Prediction step
        P_pred = current_P + Q
        
        # Update step
        if new_price2 != 0:
            innovation = new_price1 - current_hr * new_price2
            S = P_pred * new_price2**2 + R
            K = P_pred * new_price2 / S
            
            updated_hr = current_hr + K * innovation / new_price2
            updated_P = (1 - K * new_price2) * P_pred
            
            # Update statistics for future use
            result.statistics['current_hedge_ratio'] = updated_hr
            result.statistics['current_uncertainty'] = updated_P
            
            return updated_hr
        
        return current_hr
