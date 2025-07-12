"""
Kalman Filter for Dynamic Hedge Ratio Estimation

This module implements a Kalman filter specifically designed for tracking
time-varying hedge ratios in statistical arbitrage pair trading.

The state space model assumes:
- State: [hedge_ratio, hedge_ratio_drift]
- Observation: price_y = hedge_ratio * price_x + noise

Key Features:
- Adaptive estimation of hedge ratios over time
- Handles regime changes and structural breaks
- Provides uncertainty estimates
- Optimized for financial time series
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Tuple, Optional, List
import logging
from scipy.optimize import minimize_scalar

logger = logging.getLogger(__name__)


@dataclass
class KalmanResult:
    """Results from Kalman filter hedge ratio estimation"""
    hedge_ratios: np.ndarray
    hedge_ratio_variance: np.ndarray
    log_likelihood: float
    innovation_variance: float
    state_variance: float
    filtered_spreads: np.ndarray
    prediction_errors: np.ndarray
    
    @property
    def current_hedge_ratio(self) -> float:
        """Current (most recent) hedge ratio estimate"""
        return float(self.hedge_ratios[-1])
    
    @property
    def current_uncertainty(self) -> float:
        """Current uncertainty in hedge ratio estimate"""
        return np.sqrt(self.hedge_ratio_variance[-1])
    
    @property
    def mean_hedge_ratio(self) -> float:
        """Average hedge ratio over the period"""
        return np.mean(self.hedge_ratios)


class KalmanHedgeRatioFilter:
    """
    Kalman Filter for Dynamic Hedge Ratio Estimation
    
    Uses a state-space model to track time-varying hedge ratios:
    
    State equation: β_t = β_{t-1} + w_t  (random walk)
    Observation equation: y_t = β_t * x_t + v_t
    
    Where:
    - β_t is the hedge ratio at time t
    - x_t, y_t are the asset prices
    - w_t ~ N(0, Q) is state noise
    - v_t ~ N(0, R) is observation noise
    """
    
    def __init__(self, 
                 initial_hedge_ratio: Optional[float] = None,
                 initial_variance: float = 1.0,
                 state_variance: Optional[float] = None,
                 observation_variance: Optional[float] = None,
                 auto_tune: bool = True):
        """
        Initialize Kalman filter
        
        Args:
            initial_hedge_ratio: Initial hedge ratio estimate (if None, uses OLS)
            initial_variance: Initial variance of hedge ratio estimate
            state_variance: Process noise variance (if None, estimated via MLE)
            observation_variance: Observation noise variance (if None, estimated via MLE)
            auto_tune: Whether to automatically tune parameters via MLE
        """
        self.initial_hedge_ratio = initial_hedge_ratio
        self.initial_variance = initial_variance
        self.state_variance = state_variance
        self.observation_variance = observation_variance
        self.auto_tune = auto_tune
        
        # Internal state
        self.is_fitted = False
        self.n_observations = 0
        self.current_hedge_ratio = 0.0
        self.current_uncertainty = 0.0
        self.final_state_variance = 0.0
        self.final_observation_variance = 0.0
        
    def _initialize_parameters(self, x: np.ndarray, y: np.ndarray) -> Tuple[float, float, float, float]:
        """Initialize filter parameters"""
        # Initial hedge ratio via OLS if not provided
        if self.initial_hedge_ratio is None:
            beta_0 = float(np.cov(x, y)[0, 1] / np.var(x))
        else:
            beta_0 = self.initial_hedge_ratio
            
        # Initial variance
        P_0 = self.initial_variance
        
        # Estimate noise variances if not provided
        if self.state_variance is None or self.observation_variance is None:
            if self.auto_tune:
                Q, R = self._estimate_noise_variances(x, y, beta_0)
            else:
                # Default values based on empirical studies
                Q = 1e-4  # Small process noise for hedge ratios
                R = float(np.var(y - beta_0 * x))  # Residual variance
        else:
            Q = self.state_variance
            R = self.observation_variance
            
        return beta_0, P_0, Q, R
    
    def _estimate_noise_variances(self, x: np.ndarray, y: np.ndarray, 
                                 beta_0: float) -> Tuple[float, float]:
        """Estimate optimal noise variances via Maximum Likelihood"""
        
        def negative_log_likelihood(params):
            """Negative log-likelihood for optimization"""
            log_Q, log_R = params
            Q = np.exp(log_Q)
            R = np.exp(log_R)
            
            try:
                _, _, ll, _, _ = self._kalman_filter(x, y, beta_0, self.initial_variance, Q, R)
                return -ll
            except:
                return 1e10  # Return large value if filter fails
        
        # Grid search for reasonable starting values
        best_ll = -np.inf
        best_params = None
        
        for log_Q in np.linspace(-8, -2, 7):  # Q from 1e-8 to 1e-2
            for log_R in np.linspace(-4, 2, 7):   # R from 1e-4 to 1e2
                try:
                    _, _, ll, _, _ = self._kalman_filter(x, y, beta_0, self.initial_variance, 
                                                       np.exp(log_Q), np.exp(log_R))
                    if ll > best_ll:
                        best_ll = ll
                        best_params = (log_Q, log_R)
                except:
                    continue
        
        if best_params is None:
            logger.warning("MLE estimation failed, using default values")
            return 1e-4, np.var(y - beta_0 * x)
        
        # Fine-tune around best parameters
        try:
            from scipy.optimize import minimize
            result = minimize(negative_log_likelihood, best_params, 
                            method='Nelder-Mead', options={'maxiter': 100})
            if result.success:
                log_Q_opt, log_R_opt = result.x
                Q_opt = np.exp(log_Q_opt)
                R_opt = np.exp(log_R_opt)
            else:
                Q_opt = np.exp(best_params[0])
                R_opt = np.exp(best_params[1])
        except:
            Q_opt = np.exp(best_params[0])
            R_opt = np.exp(best_params[1])
        
        logger.info(f"Estimated noise variances: Q={Q_opt:.2e}, R={R_opt:.2e}")
        return float(Q_opt), float(R_opt)
    
    def _kalman_filter(self, x: np.ndarray, y: np.ndarray, 
                      beta_0: float, P_0: float, Q: float, R: float) -> Tuple[np.ndarray, np.ndarray, float, np.ndarray, np.ndarray]:
        """
        Run Kalman filter
        
        Returns:
            hedge_ratios: Filtered hedge ratio estimates
            variances: Variance of hedge ratio estimates
            log_likelihood: Log-likelihood of the model
            innovations: One-step-ahead prediction errors
            spreads: Filtered spreads
        """
        n = len(x)
        
        # Initialize arrays
        hedge_ratios = np.zeros(n)
        variances = np.zeros(n)
        innovations = np.zeros(n)
        spreads = np.zeros(n)
        
        # Initialize state
        beta_t = beta_0
        P_t = P_0
        
        log_likelihood = 0.0
        
        for t in range(n):
            # Prediction step
            beta_pred = beta_t  # Random walk: β_t|t-1 = β_{t-1}
            P_pred = P_t + Q    # P_t|t-1 = P_{t-1} + Q
            
            # Observation prediction
            y_pred = beta_pred * x[t]
            innovation = y[t] - y_pred
            
            # Innovation variance
            S = P_pred * x[t]**2 + R
            
            # Kalman gain
            K = P_pred * x[t] / S
            
            # Update step
            beta_t = beta_pred + K * innovation
            P_t = P_pred - K * x[t] * P_pred
            
            # Store results
            hedge_ratios[t] = beta_t
            variances[t] = P_t
            innovations[t] = innovation
            spreads[t] = y[t] - beta_t * x[t]
            
            # Update log-likelihood
            log_likelihood += -0.5 * (np.log(2 * np.pi) + np.log(S) + innovation**2 / S)
        
        return hedge_ratios, variances, log_likelihood, innovations, spreads
    
    def fit(self, x: np.ndarray, y: np.ndarray) -> 'KalmanResult':
        """
        Fit Kalman filter to data
        
        Args:
            x: Asset X prices (independent variable)
            y: Asset Y prices (dependent variable)
            
        Returns:
            KalmanResult with filtered estimates
        """
        # Convert to numpy arrays
        x = np.asarray(x)
        y = np.asarray(y)
        
        if len(x) != len(y):
            raise ValueError("x and y must have the same length")
        
        if len(x) < 2:
            raise ValueError("Need at least 2 observations")
        
        self.n_observations = len(x)
        
        # Initialize parameters
        beta_0, P_0, Q, R = self._initialize_parameters(x, y)
        
        # Run Kalman filter
        hedge_ratios, variances, log_likelihood, innovations, spreads = self._kalman_filter(
            x, y, beta_0, P_0, Q, R
        )
        
        self.is_fitted = True
        
        # Store final parameters
        self.final_state_variance = Q
        self.final_observation_variance = R
        self.current_hedge_ratio = float(hedge_ratios[-1])
        self.current_uncertainty = float(np.sqrt(variances[-1]))
        
        return KalmanResult(
            hedge_ratios=hedge_ratios,
            hedge_ratio_variance=variances,
            log_likelihood=log_likelihood,
            innovation_variance=R,
            state_variance=Q,
            filtered_spreads=spreads,
            prediction_errors=innovations
        )
    
    def predict(self, x_new: np.ndarray, n_steps: int = 1) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predict future hedge ratios
        
        Args:
            x_new: New X values for prediction
            n_steps: Number of steps ahead to predict
            
        Returns:
            Tuple of (predicted_hedge_ratios, prediction_variances)
        """
        if not self.is_fitted:
            raise ValueError("Filter must be fitted before prediction")
        
        # For random walk model, prediction is just the last estimate
        # with increasing variance
        predictions = np.full(n_steps, self.current_hedge_ratio)
        variances = np.array([self.current_uncertainty**2 + i * self.final_state_variance 
                            for i in range(1, n_steps + 1)])
        
        return predictions, variances
    
    def update(self, x_new: float, y_new: float) -> Tuple[float, float]:
        """
        Update filter with new observation
        
        Args:
            x_new: New X value
            y_new: New Y value
            
        Returns:
            Tuple of (new_hedge_ratio, new_variance)
        """
        if not self.is_fitted:
            raise ValueError("Filter must be fitted before updating")
        
        # Get current state
        beta_t = self.current_hedge_ratio
        P_t = self.current_uncertainty**2
        
        # Prediction step
        beta_pred = beta_t
        P_pred = P_t + self.final_state_variance
        
        # Update step
        y_pred = beta_pred * x_new
        innovation = y_new - y_pred
        S = P_pred * x_new**2 + self.final_observation_variance
        K = P_pred * x_new / S
        
        beta_new = beta_pred + K * innovation
        P_new = P_pred - K * x_new * P_pred
        
        return beta_new, P_new


def create_kalman_filter(x: np.ndarray, y: np.ndarray, 
                        auto_tune: bool = True, **kwargs) -> KalmanResult:
    """
    Convenience function to create and fit a Kalman filter
    
    Args:
        x: Asset X prices
        y: Asset Y prices
        auto_tune: Whether to auto-tune parameters
        **kwargs: Additional parameters for KalmanHedgeRatioFilter
        
    Returns:
        KalmanResult with fitted estimates
    """
    kf = KalmanHedgeRatioFilter(auto_tune=auto_tune, **kwargs)
    return kf.fit(x, y) 