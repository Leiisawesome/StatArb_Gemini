"""
Kalman Filter implementation for estimating hedge ratio (beta) and intercept (alpha).
"""
import numpy as np
import pandas as pd
from pykalman import KalmanFilter as PyKalmanFilter

class KalmanFilter:
    def __init__(self, observation_covariance: float = 1.0, transition_covariance: float = 0.01):
        """Initializes the Kalman Filter for online linear regression."""
        self.observation_covariance = observation_covariance
        self.transition_covariance = transition_covariance
        
        self.kf = PyKalmanFilter(
            transition_matrices=np.eye(2),
            observation_matrices=None,
            initial_state_mean=np.zeros(2),
            initial_state_covariance=np.ones((2, 2)),
            observation_covariance=self.observation_covariance,
            transition_covariance=np.eye(2) * self.transition_covariance
        )
        self.state_means: np.ndarray | None = None
        
    def fit(self, y: pd.Series, x: pd.Series) -> 'KalmanFilter':
        """Fits the Kalman filter to the training data to get initial state."""
        observation_matrices = np.vstack([x.values, np.ones(len(x))]).T[:, np.newaxis, :]
        self.state_means, _ = self.kf.filter(y.values, observation_matrices=observation_matrices)
        return self

    def get_current_state(self) -> np.ndarray:
        """Returns the most recent state (beta, alpha)."""
        if self.state_means is None:
            return np.zeros(2)
        return self.state_means[-1] 