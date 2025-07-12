"""
Spread Calculator for Enhanced Pair Backtesting System
=====================================================

A comprehensive spread calculation module that supports multiple hedge ratio
estimation methods and can work with any trading pair.

Features:
- Multiple hedge ratio estimation methods (OLS, TLS, Kalman, Rolling)
- Dynamic hedge ratio updates
- Spread statistics and z-score calculations
- Cointegration-based hedge ratios
- Robust error handling and validation

Author: Pro Quant Desk Trader
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Union
import logging
from scipy import stats
from scipy.optimize import minimize
from sklearn.linear_model import LinearRegression
from sklearn.decomposition import PCA
from dataclasses import dataclass
import warnings

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)

try:
    from ..models.kalman_filter import create_kalman_filter
    KALMAN_AVAILABLE = True
except ImportError:
    try:
        from models.kalman_filter import create_kalman_filter
        KALMAN_AVAILABLE = True
    except ImportError:
        try:
            # Try absolute import with sys.path manipulation
            import sys
            import os
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(current_dir)
            sys.path.insert(0, parent_dir)
            from models.kalman_filter import create_kalman_filter
            KALMAN_AVAILABLE = True
        except ImportError:
            KALMAN_AVAILABLE = False
            logger.warning("Kalman filter not available - install scipy for full functionality")

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

class SpreadCalculator:
    """
    Generic spread calculator supporting multiple hedge ratio estimation methods.
    Designed to work with any trading pair.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the spread calculator.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.method = config.get('hedge_ratio_method', 'ols')
        self.lookback_window = config.get('lookback_window', 60)
        self.min_observations = config.get('min_observations', 30)
        self.confidence_level = config.get('confidence_level', 0.95)
        
        # Method-specific parameters
        self.rolling_window = config.get('rolling_window', 252)
        self.half_life = config.get('half_life', 30)
        self.regularization = config.get('regularization', 0.0)
        
        # Cache for performance
        self._cache = {}
        
        logger.info(f"Initialized SpreadCalculator with method: {self.method}")
    
    def calculate_spread(self, 
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
        # Validate inputs
        self._validate_inputs(price1, price2)
        
        # Align data
        aligned_data = self._align_data(price1, price2)
        price1_aligned = aligned_data['price1']
        price2_aligned = aligned_data['price2']
        
        # Calculate hedge ratio using specified method
        if self.method == 'ols':
            result = self._calculate_ols_spread(price1_aligned, price2_aligned)
        elif self.method == 'tls':
            result = self._calculate_tls_spread(price1_aligned, price2_aligned)
        elif self.method == 'rolling_ols':
            result = self._calculate_rolling_ols_spread(price1_aligned, price2_aligned)
        elif self.method == 'exponential':
            result = self._calculate_exponential_spread(price1_aligned, price2_aligned)
        elif self.method == 'cointegration':
            result = self._calculate_cointegration_spread(price1_aligned, price2_aligned)
        elif self.method == 'pca':
            result = self._calculate_pca_spread(price1_aligned, price2_aligned)
        elif self.method == 'kalman':
            result = self._calculate_kalman_spread(price1_aligned, price2_aligned)
        else:
            raise ValueError(f"Unknown hedge ratio method: {self.method}")
        
        # Add metadata
        result.method = self.method
        result.statistics['symbol1'] = symbol1
        result.statistics['symbol2'] = symbol2
        result.statistics['observations'] = len(price1_aligned)
        
        logger.info(f"Calculated spread for {symbol1}/{symbol2} using {self.method} method")
        logger.info(f"Hedge ratio: {result.hedge_ratio if isinstance(result.hedge_ratio, float) else 'Dynamic'}")
        logger.info(f"Spread statistics: mean={result.spread_mean:.4f}, std={result.spread_std:.4f}")
        
        return result
    
    def _validate_inputs(self, price1: pd.Series, price2: pd.Series):
        """Validate input data."""
        if len(price1) < self.min_observations or len(price2) < self.min_observations:
            raise ValueError(f"Insufficient data: need at least {self.min_observations} observations")
        
        if (price1 <= 0).any() or (price2 <= 0).any():
            raise ValueError("Prices must be positive")
        
        if price1.isnull().any() or price2.isnull().any():
            raise ValueError("Price series cannot contain NaN values")
    
    def _align_data(self, price1: pd.Series, price2: pd.Series) -> Dict[str, pd.Series]:
        """Align price series by index."""
        common_index = price1.index.intersection(price2.index)
        
        if len(common_index) < self.min_observations:
            raise ValueError(f"Insufficient overlapping data: {len(common_index)} observations")
        
        return {
            'price1': price1.loc[common_index],
            'price2': price2.loc[common_index]
        }
    
    def _calculate_ols_spread(self, price1: pd.Series, price2: pd.Series) -> SpreadResult:
        """Calculate spread using Ordinary Least Squares hedge ratio."""
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
        
        # Calculate R-squared and other statistics
        y_pred = model.predict(X)
        r_squared = model.score(X, y)
        residuals = y - y_pred
        
        # Calculate confidence interval for hedge ratio
        n = len(price1)
        mse = np.mean(residuals**2)
        var_beta = mse / np.sum((price2 - price2.mean())**2)
        se_beta = np.sqrt(var_beta)
        
        t_critical = stats.t.ppf((1 + self.confidence_level) / 2, n - 2)
        ci_lower = hedge_ratio - t_critical * se_beta
        ci_upper = hedge_ratio + t_critical * se_beta
        
        statistics = {
            'hedge_ratio': hedge_ratio,
            'intercept': intercept,
            'r_squared': r_squared,
            'std_error': se_beta,
            'residual_std': np.std(residuals),
            'durbin_watson': self._calculate_durbin_watson(residuals),
            'adf_pvalue': self._calculate_adf_test(spread)
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
    
    def _calculate_tls_spread(self, price1: pd.Series, price2: pd.Series) -> SpreadResult:
        """Calculate spread using Total Least Squares hedge ratio."""
        # Prepare data
        data = np.column_stack([price1.values, price2.values])
        
        # Center the data
        data_centered = data - np.mean(data, axis=0)
        
        # Perform PCA to find the line of best fit
        pca = PCA(n_components=2)
        pca.fit(data_centered)
        
        # The hedge ratio is the slope of the first principal component
        pc1 = pca.components_[0]
        hedge_ratio = -pc1[0] / pc1[1]  # Negative because we want price1 - beta * price2
        
        # Calculate intercept
        intercept = price1.mean() - hedge_ratio * price2.mean()
        
        # Calculate spread
        spread = price1 - hedge_ratio * price2
        
        # Calculate statistics
        spread_mean = spread.mean()
        spread_std = spread.std()
        z_score = (spread - spread_mean) / spread_std
        
        # Calculate explained variance
        explained_variance_ratio = pca.explained_variance_ratio_[0]
        
        statistics = {
            'hedge_ratio': hedge_ratio,
            'intercept': intercept,
            'explained_variance_ratio': explained_variance_ratio,
            'eigenvalues': pca.explained_variance_.tolist(),
            'adf_pvalue': self._calculate_adf_test(spread)
        }
        
        return SpreadResult(
            spread=spread,
            hedge_ratio=hedge_ratio,
            spread_mean=spread_mean,
            spread_std=spread_std,
            z_score=z_score,
            method='tls',
            statistics=statistics
        )
    
    def _calculate_rolling_ols_spread(self, price1: pd.Series, price2: pd.Series) -> SpreadResult:
        """Calculate spread using rolling OLS hedge ratio."""
        hedge_ratios = []
        spreads = []
        
        for i in range(self.rolling_window, len(price1)):
            # Get rolling window data
            p1_window = price1.iloc[i-self.rolling_window:i]
            p2_window = price2.iloc[i-self.rolling_window:i]
            
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
        spread_index = price1.index[self.rolling_window:]
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
            'rolling_window': self.rolling_window,
            'adf_pvalue': self._calculate_adf_test(spread)
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
    
    def _calculate_exponential_spread(self, price1: pd.Series, price2: pd.Series) -> SpreadResult:
        """Calculate spread using exponentially weighted hedge ratio."""
        # Calculate exponentially weighted moving averages
        alpha = 2.0 / (self.half_life + 1.0)
        
        # Initialize arrays
        hedge_ratios = []
        spreads = []
        
        # Calculate initial hedge ratio using first window
        initial_window = min(self.rolling_window, len(price1) // 2)
        X_init = price2.iloc[:initial_window].values.reshape(-1, 1)
        y_init = price1.iloc[:initial_window].values
        
        model = LinearRegression(fit_intercept=True)
        model.fit(X_init, y_init)
        hedge_ratio = model.coef_[0]
        
        # Calculate exponentially weighted hedge ratios
        for i in range(len(price1)):
            if i > 0:
                # Update hedge ratio using exponential weighting
                error = price1.iloc[i] - hedge_ratio * price2.iloc[i]
                hedge_ratio += alpha * error / price2.iloc[i] if price2.iloc[i] != 0 else 0
            
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
            'hedge_ratio_final': hedge_ratio,
            'hedge_ratio_mean': hedge_ratio_series.mean(),
            'hedge_ratio_std': hedge_ratio_series.std(),
            'half_life': self.half_life,
            'alpha': alpha,
            'adf_pvalue': self._calculate_adf_test(spread)
        }
        
        return SpreadResult(
            spread=spread,
            hedge_ratio=hedge_ratio_series,
            spread_mean=spread_mean,
            spread_std=spread_std,
            z_score=z_score,
            method='exponential',
            statistics=statistics
        )
    
    def _calculate_cointegration_spread(self, price1: pd.Series, price2: pd.Series) -> SpreadResult:
        """Calculate spread using cointegration-based hedge ratio."""
        try:
            from statsmodels.tsa.stattools import coint
            
            # Test for cointegration
            score, pvalue, crit_values = coint(price1, price2)
            
            # Use OLS for hedge ratio but validate with cointegration
            result = self._calculate_ols_spread(price1, price2)
            
            # Update statistics with cointegration info
            result.statistics.update({
                'cointegration_score': score,
                'cointegration_pvalue': pvalue,
                'critical_values': crit_values.tolist(),
                'is_cointegrated': pvalue < 0.05
            })
            
            result.method = 'cointegration'
            
            return result
            
        except ImportError:
            logger.warning("statsmodels not available, falling back to OLS")
            return self._calculate_ols_spread(price1, price2)
    
    def _calculate_pca_spread(self, price1: pd.Series, price2: pd.Series) -> SpreadResult:
        """Calculate spread using PCA-based hedge ratio."""
        # Prepare data matrix
        returns1 = price1.pct_change().dropna()
        returns2 = price2.pct_change().dropna()
        
        # Align returns
        common_index = returns1.index.intersection(returns2.index)
        returns_matrix = np.column_stack([
            returns1.loc[common_index].values,
            returns2.loc[common_index].values
        ])
        
        # Perform PCA
        pca = PCA(n_components=2)
        pca.fit(returns_matrix)
        
        # Use the first principal component to determine hedge ratio
        pc1 = pca.components_[0]
        hedge_ratio = pc1[0] / pc1[1]
        
        # Align original prices and calculate spread
        price1_aligned = price1.loc[common_index]
        price2_aligned = price2.loc[common_index]
        spread = price1_aligned - hedge_ratio * price2_aligned
        
        # Calculate statistics
        spread_mean = spread.mean()
        spread_std = spread.std()
        z_score = (spread - spread_mean) / spread_std
        
        statistics = {
            'hedge_ratio': hedge_ratio,
            'explained_variance_ratio': pca.explained_variance_ratio_[0],
            'total_variance_explained': pca.explained_variance_ratio_.sum(),
            'principal_components': pca.components_.tolist(),
            'adf_pvalue': self._calculate_adf_test(spread)
        }
        
        return SpreadResult(
            spread=spread,
            hedge_ratio=hedge_ratio,
            spread_mean=spread_mean,
            spread_std=spread_std,
            z_score=z_score,
            method='pca',
            statistics=statistics
        )
    
    def _calculate_kalman_spread(self, price1: pd.Series, price2: pd.Series) -> SpreadResult:
        """Calculate spread using Kalman filter for dynamic hedge ratio."""
        if not KALMAN_AVAILABLE:
            logger.warning("Kalman filter not available, falling back to OLS")
            return self._calculate_ols_spread(price1, price2)
        
        try:
            # Use Kalman filter to estimate dynamic hedge ratio
            kalman_result = create_kalman_filter(
                x=price2.values,
                y=price1.values,
                auto_tune=True
            )
            
            # Create hedge ratio series aligned with prices
            hedge_ratio_series = pd.Series(
                kalman_result.hedge_ratios,
                index=price1.index
            )
            
            # Calculate spread using dynamic hedge ratios
            spread = price1 - hedge_ratio_series * price2
            
            # Calculate statistics
            spread_mean = spread.mean()
            spread_std = spread.std()
            z_score = (spread - spread_mean) / spread_std
            
            statistics = {
                'mean_hedge_ratio': kalman_result.mean_hedge_ratio,
                'current_hedge_ratio': kalman_result.current_hedge_ratio,
                'current_uncertainty': kalman_result.current_uncertainty,
                'log_likelihood': kalman_result.log_likelihood,
                'state_variance': kalman_result.state_variance,
                'innovation_variance': kalman_result.innovation_variance,
                'hedge_ratio_std': np.std(kalman_result.hedge_ratios),
                'adf_pvalue': self._calculate_adf_test(spread)
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
            logger.error(f"Kalman filter failed: {e}")
            logger.info("Falling back to OLS method")
            return self._calculate_ols_spread(price1, price2)
    
    def _calculate_durbin_watson(self, residuals: np.ndarray) -> float:
        """Calculate Durbin-Watson statistic for autocorrelation."""
        diff = np.diff(residuals)
        return np.sum(diff**2) / np.sum(residuals**2)
    
    def _calculate_adf_test(self, series: pd.Series) -> float:
        """Calculate Augmented Dickey-Fuller test p-value."""
        try:
            from statsmodels.tsa.stattools import adfuller
            result = adfuller(series.dropna())
            return result[1]  # p-value
        except ImportError:
            logger.warning("statsmodels not available for ADF test")
            return np.nan
    
    def update_spread(self, 
                     result: SpreadResult, 
                     new_price1: float, 
                     new_price2: float) -> SpreadResult:
        """
        Update spread calculation with new price data.
        
        Args:
            result: Previous spread result
            new_price1: New price for first asset
            new_price2: New price for second asset
            
        Returns:
            Updated SpreadResult
        """
        if isinstance(result.hedge_ratio, pd.Series):
            # For dynamic hedge ratios, use the last value
            current_hedge_ratio = result.hedge_ratio.iloc[-1]
        else:
            current_hedge_ratio = result.hedge_ratio
        
        # Calculate new spread value
        new_spread = new_price1 - current_hedge_ratio * new_price2
        
        # Update spread series
        new_timestamp = pd.Timestamp.now()
        updated_spread = pd.concat([result.spread, pd.Series([new_spread], index=[new_timestamp])])
        
        # Recalculate statistics
        spread_mean = updated_spread.mean()
        spread_std = updated_spread.std()
        z_score = (updated_spread - spread_mean) / spread_std
        
        # Create updated result
        return SpreadResult(
            spread=updated_spread,
            hedge_ratio=result.hedge_ratio,
            spread_mean=spread_mean,
            spread_std=spread_std,
            z_score=z_score,
            method=result.method,
            statistics=result.statistics.copy(),
            confidence_interval=result.confidence_interval
        )
    
    def get_current_z_score(self, result: SpreadResult) -> float:
        """Get the current z-score from spread result."""
        if len(result.z_score) == 0:
            return 0.0
        return result.z_score.iloc[-1]
    
    def get_spread_statistics(self, result: SpreadResult) -> Dict[str, Any]:
        """Get comprehensive spread statistics."""
        spread = result.spread
        
        stats_dict = {
            'count': len(spread),
            'mean': spread.mean(),
            'std': spread.std(),
            'min': spread.min(),
            'max': spread.max(),
            'skewness': spread.skew(),
            'kurtosis': spread.kurtosis(),
            'current_value': spread.iloc[-1] if len(spread) > 0 else np.nan,
            'current_z_score': self.get_current_z_score(result),
            'method': result.method,
            'hedge_ratio_type': 'dynamic' if isinstance(result.hedge_ratio, pd.Series) else 'static'
        }
        
        # Add percentiles
        percentiles = [1, 5, 10, 25, 50, 75, 90, 95, 99]
        for p in percentiles:
            stats_dict[f'percentile_{p}'] = spread.quantile(p / 100)
        
        # Add method-specific statistics
        stats_dict.update(result.statistics)
        
        return stats_dict
    
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
        if len(spread) < self.min_observations:
            validation['valid'] = False
            validation['issues'].append(f"Insufficient data: {len(spread)} observations")
        
        # Check for stationarity (ADF test)
        adf_pvalue = result.statistics.get('adf_pvalue', np.nan)
        if not np.isnan(adf_pvalue):
            if adf_pvalue > 0.05:
                validation['warnings'].append(f"Spread may not be stationary (ADF p-value: {adf_pvalue:.4f})")
            else:
                validation['quality_score'] += 25  # Stationary spread is good
        
        # Check hedge ratio stability (for dynamic ratios)
        if isinstance(result.hedge_ratio, pd.Series):
            hr_std = result.hedge_ratio.std()
            hr_mean = result.hedge_ratio.mean()
            if hr_mean != 0 and hr_std / abs(hr_mean) > 0.5:
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
        extreme_count = (z_scores.abs() > 4).sum()
        if extreme_count > len(z_scores) * 0.01:  # More than 1% extreme values
            validation['warnings'].append(f"High number of extreme values: {extreme_count}")
        else:
            validation['quality_score'] += 25  # Few outliers is good
        
        return validation 