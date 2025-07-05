"""
Advanced Kalman Filter for Statistical Arbitrage - Professional Implementation
Estimates time-varying hedge ratios, intercepts, and volatility for pair trading.
"""
import numpy as np
import pandas as pd
from typing import Tuple, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class AdvancedKalmanFilter:
    """
    Professional Kalman Filter for pair trading that estimates:
    - Time-varying hedge ratio (beta)
    - Intercept (alpha)
    - Volatility (sigma)
    - State uncertainty
    """
    
    def __init__(self, 
                 initial_beta: float = 1.0,
                 initial_alpha: float = 0.0,
                 initial_volatility: float = 0.01,
                 process_noise_beta: float = 1e-6,
                 process_noise_alpha: float = 1e-6,
                 process_noise_vol: float = 1e-6,
                 observation_noise: float = 1e-4):
        """
        Initialize Kalman Filter for pair trading.
        
        Args:
            initial_beta: Initial hedge ratio estimate
            initial_alpha: Initial intercept estimate
            initial_volatility: Initial volatility estimate
            process_noise_beta: Process noise for beta (how much beta can change)
            process_noise_alpha: Process noise for alpha (how much alpha can change)
            process_noise_vol: Process noise for volatility (how much vol can change)
            observation_noise: Observation noise (measurement uncertainty)
        """
        # State vector: [beta, alpha, log(volatility)]
        self.state = np.array([initial_beta, initial_alpha, np.log(initial_volatility)])
        
        # State covariance matrix (uncertainty in our estimates)
        self.covariance = np.diag([0.1, 0.1, 0.1])  # Initial uncertainty
        
        # Process noise covariance matrix (how much states can change)
        self.Q = np.diag([process_noise_beta, process_noise_alpha, process_noise_vol])
        
        # Observation noise
        self.R = observation_noise
        
        # State history for analysis
        self.state_history = []
        self.covariance_history = []
        self.innovation_history = []
        
        # Performance tracking
        self.is_initialized = False
        self.observation_count = 0
        
    def predict(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prediction step: predict next state based on current state.
        
        Returns:
            Tuple of (predicted_state, predicted_covariance)
        """
        # State transition: states evolve with some uncertainty
        predicted_state = self.state.copy()
        predicted_covariance = self.covariance + self.Q
        
        return predicted_state, predicted_covariance
    
    def update(self, y_price: float, x_price: float) -> Dict[str, Any]:
        """
        Update step: incorporate new observation to refine estimates.
        
        Args:
            y_price: Price of asset Y (dependent variable)
            x_price: Price of asset X (independent variable)
            
        Returns:
            Dictionary with updated state and metrics
        """
        if x_price <= 0:
            logger.warning("Invalid x_price, skipping update")
            return self._get_state_dict()
        
        # Prediction step
        predicted_state, predicted_covariance = self.predict()
        
        # Extract current estimates
        beta_pred = predicted_state[0]
        alpha_pred = predicted_state[1]
        log_vol_pred = predicted_state[2]
        vol_pred = np.exp(log_vol_pred)
        
        # Expected spread based on current estimates
        expected_spread = alpha_pred + beta_pred * x_price
        actual_spread = y_price
        
        # Innovation (prediction error)
        innovation = actual_spread - expected_spread
        
        # Observation matrix: how observation relates to state
        # H = [x_price, 1, 0] for linear relationship
        H = np.array([x_price, 1.0, 0.0])
        
        # Innovation covariance
        innovation_covariance = H @ predicted_covariance @ H.T + self.R
        
        # Kalman gain
        kalman_gain = predicted_covariance @ H.T / innovation_covariance
        
        # Update state
        self.state = predicted_state + kalman_gain * innovation
        
        # Update covariance (Joseph form for numerical stability)
        I = np.eye(len(self.state))
        self.covariance = (I - kalman_gain.reshape(-1, 1) @ H.reshape(1, -1)) @ predicted_covariance
        
        # Store history
        self.state_history.append(self.state.copy())
        self.covariance_history.append(self.covariance.copy())
        self.innovation_history.append(innovation)
        
        # Update counters
        self.observation_count += 1
        if not self.is_initialized and self.observation_count >= 10:
            self.is_initialized = True
        
        return self._get_state_dict()
    
    def _get_state_dict(self) -> Dict[str, Any]:
        """Get current state as dictionary."""
        beta, alpha, log_vol = self.state
        vol = np.exp(log_vol)
        
        return {
            'beta': beta,
            'alpha': alpha,
            'volatility': vol,
            'log_volatility': log_vol,
            'state': self.state.copy(),
            'covariance': self.covariance.copy(),
            'is_initialized': self.is_initialized,
            'observation_count': self.observation_count
        }
    
    def get_hedge_ratio(self) -> float:
        """Get current hedge ratio estimate."""
        return self.state[0]
    
    def get_intercept(self) -> float:
        """Get current intercept estimate."""
        return self.state[1]
    
    def get_volatility(self) -> float:
        """Get current volatility estimate."""
        return np.exp(self.state[2])
    
    def get_state_uncertainty(self) -> np.ndarray:
        """Get uncertainty in state estimates."""
        return np.sqrt(np.diag(self.covariance))
    
    def get_spread_forecast(self, x_price: float) -> Tuple[float, float]:
        """
        Get spread forecast and uncertainty.
        
        Args:
            x_price: Price of asset X
            
        Returns:
            Tuple of (forecasted_spread, forecast_uncertainty)
        """
        beta, alpha, _ = self.state
        forecast = alpha + beta * x_price
        
        # Forecast uncertainty
        H = np.array([x_price, 1.0, 0.0])
        forecast_variance = H @ self.covariance @ H.T + self.R
        forecast_uncertainty = np.sqrt(forecast_variance)
        
        return forecast, forecast_uncertainty
    
    def get_z_score(self, y_price: float, x_price: float) -> float:
        """
        Calculate z-score for current observation.
        
        Args:
            y_price: Price of asset Y
            x_price: Price of asset X
            
        Returns:
            Z-score (how many standard deviations from expected)
        """
        forecast, uncertainty = self.get_spread_forecast(x_price)
        actual_spread = y_price
        z_score = (actual_spread - forecast) / uncertainty if uncertainty > 0 else 0
        
        return z_score
    
    def get_confidence_intervals(self, x_price: float, confidence_level: float = 0.95) -> Tuple[float, float]:
        """
        Get confidence intervals for spread forecast.
        
        Args:
            x_price: Price of asset X
            confidence_level: Confidence level (e.g., 0.95 for 95%)
            
        Returns:
            Tuple of (lower_bound, upper_bound)
        """
        forecast, uncertainty = self.get_spread_forecast(x_price)
        z_critical = 1.96 if confidence_level == 0.95 else 2.58  # 95% or 99%
        
        lower_bound = forecast - z_critical * uncertainty
        upper_bound = forecast + z_critical * uncertainty
        
        return lower_bound, upper_bound
    
    def get_performance_metrics(self) -> Dict[str, float]:
        """Get performance metrics for the filter."""
        if len(self.innovation_history) < 10:
            return {}
        
        innovations = np.array(self.innovation_history)
        
        return {
            'mean_innovation': float(np.mean(innovations)),
            'innovation_std': float(np.std(innovations)),
            'innovation_skew': float(self._calculate_skewness(innovations)),
            'innovation_kurtosis': float(self._calculate_kurtosis(innovations)),
            'filter_convergence': float(self._calculate_convergence()),
            'state_stability': float(self._calculate_state_stability())
        }
    
    def _calculate_skewness(self, data: np.ndarray) -> float:
        """Calculate skewness of innovations."""
        mean = np.mean(data)
        std = np.std(data)
        if std == 0:
            return 0.0
        return np.mean(((data - mean) / std) ** 3)
    
    def _calculate_kurtosis(self, data: np.ndarray) -> float:
        """Calculate kurtosis of innovations."""
        mean = np.mean(data)
        std = np.std(data)
        if std == 0:
            return 0.0
        return np.mean(((data - mean) / std) ** 4) - 3
    
    def _calculate_convergence(self) -> float:
        """Calculate filter convergence metric."""
        if len(self.state_history) < 20:
            return 1.0
        
        # Check if state estimates are stabilizing
        recent_states = np.array(self.state_history[-20:])
        state_changes = np.diff(recent_states, axis=0)
        avg_change = np.mean(np.abs(state_changes))
        
        return 1.0 / (1.0 + avg_change)  # Higher is better
    
    def _calculate_state_stability(self) -> float:
        """Calculate state stability metric."""
        if len(self.covariance_history) < 10:
            return 1.0
        
        # Check if uncertainty is decreasing (filter is learning)
        recent_covs = self.covariance_history[-10:]
        avg_uncertainty = np.mean([np.sqrt(np.diag(cov)) for cov in recent_covs])
        
        return 1.0 / (1.0 + np.mean(avg_uncertainty))  # Higher is better
    
    def reset(self):
        """Reset filter to initial state."""
        self.state = np.array([1.0, 0.0, np.log(0.01)])
        self.covariance = np.diag([0.1, 0.1, 0.1])
        self.state_history = []
        self.covariance_history = []
        self.innovation_history = []
        self.is_initialized = False
        self.observation_count = 0

# Backward compatibility
class KalmanFilter(AdvancedKalmanFilter):
    """Legacy KalmanFilter class for backward compatibility."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def get_mean(self) -> float:
        """Legacy method - returns intercept."""
        return self.get_intercept()
    
    def get_std(self) -> float:
        """Legacy method - returns volatility."""
        return self.get_volatility() 