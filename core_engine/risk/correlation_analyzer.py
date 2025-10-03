"""
Risk Management - Correlation Analyzer
Advanced correlation analysis with dynamic correlation estimation, regime detection, and tail dependence
"""

import logging
import threading
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import time
from collections import deque
from scipy import stats
from scipy.optimize import minimize
from scipy.stats import kendalltau, spearmanr

logger = logging.getLogger(__name__)


class CorrelationMethod(Enum):
    """Correlation calculation methods"""
    PEARSON = "pearson"
    SPEARMAN = "spearman"
    KENDALL = "kendall"
    EWMA = "ewma"  # Exponentially weighted moving average
    DCC = "dcc"   # Dynamic conditional correlation
    SHRINKAGE = "shrinkage"  # Ledoit-Wolf shrinkage


class CorrelationRegime(Enum):
    """Correlation regime types"""
    LOW = "low"
    NORMAL = "normal" 
    HIGH = "high"
    CRISIS = "crisis"


@dataclass
class CorrelationResult:
    """Correlation calculation result"""
    asset1: str
    asset2: str
    correlation: float
    method: CorrelationMethod
    confidence_interval: Tuple[float, float]
    p_value: float
    sample_size: int
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CorrelationMatrix:
    """Correlation matrix with metadata"""
    matrix: pd.DataFrame
    method: CorrelationMethod
    calculation_time: datetime
    eigenvalues: List[float]
    condition_number: float
    assets: List[str]
    sample_period: Tuple[datetime, datetime]
    is_positive_definite: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RegimeDetectionResult:
    """Correlation regime detection result"""
    current_regime: CorrelationRegime
    regime_probability: float
    regime_duration: timedelta
    last_regime_change: datetime
    regime_history: List[Tuple[datetime, CorrelationRegime]]
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TailDependenceResult:
    """Tail dependence analysis result"""
    asset1: str
    asset2: str
    upper_tail_dependence: float
    lower_tail_dependence: float
    tail_correlation: float
    extreme_percentile: float = 0.05
    timestamp: datetime = field(default_factory=datetime.now)


class CorrelationAnalyzer:
    """
    Advanced correlation analyzer for portfolio risk management
    
    Provides comprehensive correlation analysis including dynamic correlations,
    regime detection, tail dependence, and stress testing scenarios.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize correlation analyzer"""
        self.config = config or {}
        self._lock = threading.Lock()
        self._correlation_cache = {}
        self._regime_history = deque(maxlen=1000)
        self._calculation_history = deque(maxlen=1000)
        
        # Configuration parameters
        self.ewma_lambda = self.config.get('ewma_lambda', 0.94)
        self.min_observations = self.config.get('min_observations', 50)
        self.regime_detection_window = self.config.get('regime_detection_window', 60)
        self.tail_threshold = self.config.get('tail_threshold', 0.05)
        self.cache_ttl_seconds = self.config.get('cache_ttl_seconds', 300)
        
        # Regime detection parameters
        self.regime_thresholds = self.config.get('regime_thresholds', {
            'low': 0.3,
            'normal': 0.6,
            'high': 0.8,
            'crisis': 0.9
        })
        
        # Current regime state
        self._current_regime = CorrelationRegime.NORMAL
        self._regime_start_time = datetime.now()
        
        logger.info("CorrelationAnalyzer initialized")
    
    async def calculate_correlation_matrix(
        self,
        returns: pd.DataFrame,
        method: CorrelationMethod = CorrelationMethod.PEARSON,
        min_periods: Optional[int] = None
    ) -> CorrelationMatrix:
        """
        Calculate correlation matrix using specified method
        
        Args:
            returns: DataFrame of asset returns
            method: Correlation calculation method
            min_periods: Minimum number of observations required
            
        Returns:
            Correlation matrix with metadata
        """
        start_time = time.time()
        
        try:
            if min_periods is None:
                min_periods = self.min_observations
            
            # Validate input data
            if len(returns) < min_periods:
                raise ValueError(f"Insufficient data: {len(returns)} < {min_periods}")
            
            # Remove any non-numeric columns
            numeric_returns = returns.select_dtypes(include=[np.number])
            
            # Calculate correlation matrix based on method
            if method == CorrelationMethod.PEARSON:
                corr_matrix = numeric_returns.corr(method='pearson', min_periods=min_periods)
            elif method == CorrelationMethod.SPEARMAN:
                corr_matrix = numeric_returns.corr(method='spearman', min_periods=min_periods)
            elif method == CorrelationMethod.KENDALL:
                corr_matrix = numeric_returns.corr(method='kendall', min_periods=min_periods)
            elif method == CorrelationMethod.EWMA:
                corr_matrix = await self._calculate_ewma_correlation(numeric_returns)
            elif method == CorrelationMethod.SHRINKAGE:
                corr_matrix = await self._calculate_shrinkage_correlation(numeric_returns)
            else:
                raise ValueError(f"Unsupported correlation method: {method}")
            
            # Calculate eigenvalues and condition number
            eigenvalues = np.linalg.eigvals(corr_matrix.values)
            eigenvalues = sorted(eigenvalues, reverse=True)
            condition_number = max(eigenvalues) / min(eigenvalues) if min(eigenvalues) > 1e-12 else np.inf
            
            # Check if matrix is positive definite
            is_positive_definite = all(e > 1e-12 for e in eigenvalues)
            
            # Create result
            correlation_result = CorrelationMatrix(
                matrix=corr_matrix,
                method=method,
                calculation_time=datetime.now(),
                eigenvalues=eigenvalues,
                condition_number=condition_number,
                assets=list(corr_matrix.columns),
                sample_period=(returns.index[0], returns.index[-1]),
                is_positive_definite=is_positive_definite,
                metadata={
                    'calculation_time_seconds': time.time() - start_time,
                    'sample_size': len(returns),
                    'min_periods': min_periods
                }
            )
            
            # Store in calculation history
            calculation_record = {
                'timestamp': datetime.now(),
                'method': method.value,
                'assets': len(corr_matrix.columns),
                'sample_size': len(returns),
                'calculation_time': time.time() - start_time,
                'condition_number': condition_number
            }
            self._calculation_history.append(calculation_record)
            
            logger.info(f"Calculated {len(corr_matrix)}x{len(corr_matrix)} correlation matrix using {method.value} in {time.time() - start_time:.3f}s")
            
            return correlation_result
            
        except Exception as e:
            logger.error(f"Error calculating correlation matrix: {e}")
            raise
    
    async def _calculate_ewma_correlation(self, returns: pd.DataFrame) -> pd.DataFrame:
        """Calculate exponentially weighted moving average correlation"""
        
        # Calculate EWMA covariance matrix
        ewma_cov = returns.ewm(alpha=1-self.ewma_lambda, min_periods=self.min_observations).cov()
        
        # Get the most recent covariance matrix
        latest_cov = ewma_cov.iloc[-len(returns.columns):, :]
        
        # Convert covariance to correlation
        std_matrix = np.sqrt(np.diag(latest_cov))
        corr_matrix = latest_cov / np.outer(std_matrix, std_matrix)
        
        return pd.DataFrame(corr_matrix, index=returns.columns, columns=returns.columns)
    
    async def _calculate_shrinkage_correlation(self, returns: pd.DataFrame) -> pd.DataFrame:
        """Calculate shrinkage estimator correlation (Ledoit-Wolf)"""
        
        # Calculate sample correlation
        sample_corr = returns.corr()
        
        # Target matrix (identity matrix)
        n_assets = len(returns.columns)
        target = np.eye(n_assets)
        
        # Simple shrinkage estimator (constant shrinkage intensity)
        shrinkage_intensity = 0.2  # Could be optimized using Ledoit-Wolf formula
        
        shrunk_corr = (1 - shrinkage_intensity) * sample_corr.values + shrinkage_intensity * target
        
        return pd.DataFrame(shrunk_corr, index=returns.columns, columns=returns.columns)
    
    async def calculate_pairwise_correlation(
        self,
        asset1_returns: pd.Series,
        asset2_returns: pd.Series,
        method: CorrelationMethod = CorrelationMethod.PEARSON,
        confidence_level: float = 0.95
    ) -> CorrelationResult:
        """Calculate pairwise correlation with confidence interval"""
        
        try:
            # Align series
            aligned_data = pd.DataFrame({
                'asset1': asset1_returns,
                'asset2': asset2_returns
            }).dropna()
            
            if len(aligned_data) < self.min_observations:
                raise ValueError(f"Insufficient aligned data: {len(aligned_data)} < {self.min_observations}")
            
            # Calculate correlation based on method
            if method == CorrelationMethod.PEARSON:
                correlation, p_value = stats.pearsonr(aligned_data['asset1'], aligned_data['asset2'])
            elif method == CorrelationMethod.SPEARMAN:
                correlation, p_value = spearmanr(aligned_data['asset1'], aligned_data['asset2'])
            elif method == CorrelationMethod.KENDALL:
                correlation, p_value = kendalltau(aligned_data['asset1'], aligned_data['asset2'])
            else:
                # Default to Pearson for other methods
                correlation, p_value = stats.pearsonr(aligned_data['asset1'], aligned_data['asset2'])
            
            # Calculate confidence interval using Fisher transformation
            n = len(aligned_data)
            z_score = stats.norm.ppf((1 + confidence_level) / 2)
            
            fisher_z = 0.5 * np.log((1 + correlation) / (1 - correlation))
            se_fisher = 1 / np.sqrt(n - 3)
            
            ci_lower_z = fisher_z - z_score * se_fisher
            ci_upper_z = fisher_z + z_score * se_fisher
            
            ci_lower = (np.exp(2 * ci_lower_z) - 1) / (np.exp(2 * ci_lower_z) + 1)
            ci_upper = (np.exp(2 * ci_upper_z) - 1) / (np.exp(2 * ci_upper_z) + 1)
            
            result = CorrelationResult(
                asset1=asset1_returns.name or 'asset1',
                asset2=asset2_returns.name or 'asset2',
                correlation=correlation,
                method=method,
                confidence_interval=(ci_lower, ci_upper),
                p_value=p_value,
                sample_size=n,
                metadata={
                    'confidence_level': confidence_level,
                    'fisher_z': fisher_z
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating pairwise correlation: {e}")
            raise
    
    async def detect_correlation_regime(
        self,
        correlation_matrix: pd.DataFrame,
        returns: pd.DataFrame
    ) -> RegimeDetectionResult:
        """Detect current correlation regime"""
        
        try:
            # Calculate average pairwise correlation (excluding diagonal)
            corr_values = correlation_matrix.values
            n_assets = len(corr_values)
            
            # Get upper triangle excluding diagonal
            upper_triangle = np.triu(corr_values, k=1)
            non_zero_mask = upper_triangle != 0
            avg_correlation = np.mean(upper_triangle[non_zero_mask]) if np.any(non_zero_mask) else 0
            
            # Detect regime based on average correlation
            if avg_correlation < self.regime_thresholds['low']:
                current_regime = CorrelationRegime.LOW
            elif avg_correlation < self.regime_thresholds['normal']:
                current_regime = CorrelationRegime.NORMAL
            elif avg_correlation < self.regime_thresholds['high']:
                current_regime = CorrelationRegime.HIGH
            else:
                current_regime = CorrelationRegime.CRISIS
            
            # Check for regime change
            regime_changed = current_regime != self._current_regime
            
            if regime_changed:
                # Store regime change in history
                self._regime_history.append((datetime.now(), self._current_regime))
                self._regime_start_time = datetime.now()
                self._current_regime = current_regime
            
            # Calculate regime duration
            regime_duration = datetime.now() - self._regime_start_time
            
            # Calculate regime probability (simplified - could use more sophisticated methods)
            regime_probability = self._calculate_regime_probability(avg_correlation, current_regime)
            
            # Get recent regime history
            recent_history = list(self._regime_history)[-10:]  # Last 10 regime changes
            
            # Calculate confidence based on stability
            confidence = self._calculate_regime_confidence(regime_duration, avg_correlation)
            
            result = RegimeDetectionResult(
                current_regime=current_regime,
                regime_probability=regime_probability,
                regime_duration=regime_duration,
                last_regime_change=self._regime_start_time,
                regime_history=recent_history,
                confidence=confidence,
                metadata={
                    'avg_correlation': avg_correlation,
                    'regime_thresholds': self.regime_thresholds,
                    'regime_changed': regime_changed
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error detecting correlation regime: {e}")
            raise
    
    def _calculate_regime_probability(self, avg_correlation: float, regime: CorrelationRegime) -> float:
        """Calculate probability of being in specified regime"""
        
        thresholds = self.regime_thresholds
        
        if regime == CorrelationRegime.LOW:
            if avg_correlation < thresholds['low']:
                return 1.0 - (avg_correlation / thresholds['low'])
            else:
                return max(0.0, 1.0 - (avg_correlation - thresholds['low']) / (thresholds['normal'] - thresholds['low']))
        
        elif regime == CorrelationRegime.NORMAL:
            if thresholds['low'] <= avg_correlation < thresholds['normal']:
                distance_from_center = abs(avg_correlation - (thresholds['low'] + thresholds['normal']) / 2)
                max_distance = (thresholds['normal'] - thresholds['low']) / 2
                return 1.0 - (distance_from_center / max_distance)
            else:
                return 0.0
        
        elif regime == CorrelationRegime.HIGH:
            if thresholds['normal'] <= avg_correlation < thresholds['high']:
                distance_from_center = abs(avg_correlation - (thresholds['normal'] + thresholds['high']) / 2)
                max_distance = (thresholds['high'] - thresholds['normal']) / 2
                return 1.0 - (distance_from_center / max_distance)
            else:
                return 0.0
        
        elif regime == CorrelationRegime.CRISIS:
            if avg_correlation >= thresholds['high']:
                return min(1.0, (avg_correlation - thresholds['high']) / (1.0 - thresholds['high']))
            else:
                return 0.0
        
        return 0.0
    
    def _calculate_regime_confidence(self, regime_duration: timedelta, avg_correlation: float) -> float:
        """Calculate confidence in regime detection"""
        
        # Base confidence on regime duration and correlation strength
        duration_hours = regime_duration.total_seconds() / 3600
        
        # Confidence increases with duration but plateaus
        duration_confidence = min(1.0, duration_hours / 24)  # Full confidence after 24 hours
        
        # Confidence increases with extreme correlation values
        correlation_confidence = min(1.0, abs(avg_correlation - 0.5) * 2)  # Max confidence at 0 or 1
        
        # Combined confidence
        overall_confidence = (duration_confidence + correlation_confidence) / 2
        
        return max(0.1, min(1.0, overall_confidence))  # Keep between 0.1 and 1.0
    
    async def calculate_tail_dependence(
        self,
        asset1_returns: pd.Series,
        asset2_returns: pd.Series,
        threshold_percentile: float = 0.05
    ) -> TailDependenceResult:
        """Calculate tail dependence between two assets"""
        
        try:
            # Align series
            aligned_data = pd.DataFrame({
                'asset1': asset1_returns,
                'asset2': asset2_returns
            }).dropna()
            
            if len(aligned_data) < self.min_observations:
                raise ValueError(f"Insufficient aligned data: {len(aligned_data)} < {self.min_observations}")
            
            # Calculate threshold values
            n = len(aligned_data)
            threshold_count = int(n * threshold_percentile)
            
            # Upper tail dependence (both assets in upper tail)
            asset1_upper_threshold = aligned_data['asset1'].quantile(1 - threshold_percentile)
            asset2_upper_threshold = aligned_data['asset2'].quantile(1 - threshold_percentile)
            
            both_upper = ((aligned_data['asset1'] > asset1_upper_threshold) & 
                         (aligned_data['asset2'] > asset2_upper_threshold)).sum()
            
            upper_tail_dependence = both_upper / threshold_count if threshold_count > 0 else 0
            
            # Lower tail dependence (both assets in lower tail)
            asset1_lower_threshold = aligned_data['asset1'].quantile(threshold_percentile)
            asset2_lower_threshold = aligned_data['asset2'].quantile(threshold_percentile)
            
            both_lower = ((aligned_data['asset1'] < asset1_lower_threshold) & 
                         (aligned_data['asset2'] < asset2_lower_threshold)).sum()
            
            lower_tail_dependence = both_lower / threshold_count if threshold_count > 0 else 0
            
            # Calculate correlation in extreme events
            extreme_events = aligned_data[
                ((aligned_data['asset1'] > asset1_upper_threshold) | 
                 (aligned_data['asset1'] < asset1_lower_threshold)) &
                ((aligned_data['asset2'] > asset2_upper_threshold) | 
                 (aligned_data['asset2'] < asset2_lower_threshold))
            ]
            
            if len(extreme_events) > 5:
                tail_correlation = extreme_events['asset1'].corr(extreme_events['asset2'])
            else:
                tail_correlation = 0.0
            
            result = TailDependenceResult(
                asset1=asset1_returns.name or 'asset1',
                asset2=asset2_returns.name or 'asset2',
                upper_tail_dependence=upper_tail_dependence,
                lower_tail_dependence=lower_tail_dependence,
                tail_correlation=tail_correlation,
                extreme_percentile=threshold_percentile
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating tail dependence: {e}")
            raise
    
    async def stress_test_correlations(
        self,
        correlation_matrix: pd.DataFrame,
        stress_scenarios: Dict[str, float]
    ) -> Dict[str, pd.DataFrame]:
        """Stress test correlation matrix under different scenarios"""
        
        try:
            stressed_matrices = {}
            
            for scenario_name, stress_factor in stress_scenarios.items():
                
                if scenario_name == "correlation_breakdown":
                    # Scenario where all correlations go to zero
                    stressed_matrix = pd.DataFrame(
                        np.eye(len(correlation_matrix)),
                        index=correlation_matrix.index,
                        columns=correlation_matrix.columns
                    )
                
                elif scenario_name == "correlation_spike":
                    # Scenario where all correlations increase
                    original_values = correlation_matrix.values
                    n = len(original_values)
                    
                    # Increase off-diagonal elements
                    stressed_values = original_values.copy()
                    for i in range(n):
                        for j in range(n):
                            if i != j:
                                current_corr = original_values[i, j]
                                # Move correlation towards 1 or -1 based on sign
                                if current_corr >= 0:
                                    stressed_values[i, j] = current_corr + (1 - current_corr) * stress_factor
                                else:
                                    stressed_values[i, j] = current_corr + (-1 - current_corr) * stress_factor
                    
                    stressed_matrix = pd.DataFrame(
                        stressed_values,
                        index=correlation_matrix.index,
                        columns=correlation_matrix.columns
                    )
                
                elif scenario_name == "sector_contagion":
                    # Scenario where within-sector correlations spike
                    stressed_matrix = correlation_matrix.copy()
                    
                    # This would need sector mapping information
                    # For now, increase correlations by stress_factor
                    for i in range(len(stressed_matrix)):
                        for j in range(len(stressed_matrix)):
                            if i != j:
                                current_corr = stressed_matrix.iloc[i, j]
                                stressed_matrix.iloc[i, j] = min(0.99, current_corr * (1 + stress_factor))
                
                else:
                    # Default: multiply all correlations by stress factor
                    stressed_values = correlation_matrix.values.copy()
                    n = len(stressed_values)
                    
                    for i in range(n):
                        for j in range(n):
                            if i != j:
                                stressed_values[i, j] *= stress_factor
                    
                    stressed_matrix = pd.DataFrame(
                        stressed_values,
                        index=correlation_matrix.index,
                        columns=correlation_matrix.columns
                    )
                
                # Ensure matrix remains valid (correlations between -1 and 1)
                stressed_matrix = stressed_matrix.clip(-0.99, 0.99)
                
                # Ensure diagonal remains 1
                np.fill_diagonal(stressed_matrix.values, 1.0)
                
                stressed_matrices[scenario_name] = stressed_matrix
            
            return stressed_matrices
            
        except Exception as e:
            logger.error(f"Error stress testing correlations: {e}")
            raise
    
    def get_correlation_statistics(self, correlation_matrix: pd.DataFrame) -> Dict[str, float]:
        """Calculate summary statistics for correlation matrix"""
        
        try:
            # Get upper triangle excluding diagonal
            corr_values = correlation_matrix.values
            n = len(corr_values)
            upper_triangle = np.triu(corr_values, k=1)
            correlations = upper_triangle[upper_triangle != 0]
            
            if len(correlations) == 0:
                return {}
            
            statistics = {
                'mean_correlation': float(np.mean(correlations)),
                'median_correlation': float(np.median(correlations)),
                'std_correlation': float(np.std(correlations)),
                'min_correlation': float(np.min(correlations)),
                'max_correlation': float(np.max(correlations)),
                'positive_correlations': float(np.sum(correlations > 0) / len(correlations)),
                'high_correlations': float(np.sum(correlations > 0.7) / len(correlations)),
                'negative_correlations': float(np.sum(correlations < 0) / len(correlations)),
                'near_zero_correlations': float(np.sum(np.abs(correlations) < 0.1) / len(correlations))
            }
            
            return statistics
            
        except Exception as e:
            logger.error(f"Error calculating correlation statistics: {e}")
            return {}
    
    def get_calculation_history(self) -> List[Dict[str, Any]]:
        """Get correlation calculation history"""
        with self._lock:
            return list(self._calculation_history)
    
    def get_regime_history(self) -> List[Tuple[datetime, CorrelationRegime]]:
        """Get correlation regime history"""
        with self._lock:
            return list(self._regime_history)
    
    def clear_cache(self) -> None:
        """Clear correlation calculation cache"""
        with self._lock:
            self._correlation_cache.clear()
        
        logger.info("Correlation calculation cache cleared")
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        logger.info("CorrelationAnalyzer cleanup completed")