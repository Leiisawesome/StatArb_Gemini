"""
HMM sequential trainer and inference for regime detection.
"""
import numpy as np
import pandas as pd
from hmmlearn import hmm
from typing import Dict, Any

class GaussianHMM:
    def __init__(self, num_regimes: int):
        """Initializes the Gaussian Hidden Markov Model."""
        self.num_regimes = num_regimes
        self.model = hmm.GaussianHMM(
            n_components=self.num_regimes, 
            covariance_type="full", 
            n_iter=100,
            random_state=42
        )
        self.is_fitted = False

    def fit(self, spread_series: pd.Series) -> 'GaussianHMM' | None:
        """Fits the HMM to the provided spread series."""
        if spread_series.empty or len(spread_series.dropna()) < self.num_regimes:
            print("Warning: Spread series is too short to fit HMM. Skipping.")
            return None
        
        data = spread_series.dropna().values.reshape(-1, 1)
        try:
            self.model.fit(data)
            self.is_fitted = True
            return self
        except ValueError as e:
            print(f"Error fitting HMM: {e}. Skipping HMM training.")
            return None

    def predict_regime(self, point: float) -> int:
        """Predicts the regime for a new data point."""
        if not self.is_fitted: return 0
        data = np.array(point).reshape(-1, 1)
        return self.model.predict(data)[0]
        
    def get_regime_params(self) -> Dict[int, Dict[str, float]]:
        """Returns the mean and std dev for each regime."""
        if not self.is_fitted:
            return {i: {'mean': 0, 'std': 1} for i in range(self.num_regimes)}
        means = self.model.means_.flatten()
        stds = np.sqrt(self.model.covars_.flatten())
        return {i: {'mean': means[i], 'std': stds[i]} for i in range(self.num_regimes)} 