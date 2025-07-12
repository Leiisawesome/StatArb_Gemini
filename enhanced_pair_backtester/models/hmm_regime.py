"""
Hidden Markov Model for Regime Detection in Pair Trading

This module implements a Hidden Markov Model specifically designed for detecting
market regimes in statistical arbitrage pair trading strategies.

Key Features:
- Multi-state regime detection (trending, mean-reverting, volatile, etc.)
- Gaussian mixture emissions for continuous observations
- Forward-backward algorithm for state inference
- Viterbi algorithm for most likely state sequence
- Real-time regime classification
- Regime-specific statistics and transitions

Regimes Detected:
1. Mean Reverting: Low volatility, stationary spread
2. Trending: Persistent directional movement
3. Volatile: High volatility, unstable relationships
4. Transitional: Regime change periods

Author: Pro Quant Desk Trader
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Tuple, List, Dict, Optional, Any
import logging
from scipy.stats import norm, multivariate_normal
from scipy.optimize import minimize
import warnings

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


@dataclass
class RegimeState:
    """Container for regime state information"""
    id: int
    name: str
    description: str
    mean_return: float
    volatility: float
    mean_reversion_strength: float
    persistence: float  # Expected duration in this state


@dataclass
class HMMResult:
    """Results from HMM regime detection"""
    states: np.ndarray  # Most likely state sequence
    state_probabilities: np.ndarray  # Probability of each state at each time
    log_likelihood: float
    regime_states: List[RegimeState]
    transition_matrix: np.ndarray
    emission_parameters: Dict[str, Any]
    current_regime: int
    current_regime_probability: float
    regime_statistics: Dict[str, Any]
    
    @property
    def current_regime_name(self) -> str:
        """Current regime name"""
        return self.regime_states[self.current_regime].name
    
    @property
    def regime_changes(self) -> List[int]:
        """Indices where regime changes occur"""
        return list(np.where(np.diff(self.states) != 0)[0] + 1)
    
    @property
    def regime_durations(self) -> Dict[str, List[int]]:
        """Duration of each regime period"""
        durations = {state.name: [] for state in self.regime_states}
        
        current_state = self.states[0]
        current_duration = 1
        
        for i in range(1, len(self.states)):
            if self.states[i] == current_state:
                current_duration += 1
            else:
                durations[self.regime_states[current_state].name].append(current_duration)
                current_state = self.states[i]
                current_duration = 1
        
        # Add final duration
        durations[self.regime_states[current_state].name].append(current_duration)
        
        return durations


class HMMRegimeDetector:
    """
    Hidden Markov Model for Regime Detection
    
    Implements a multi-state HMM to detect different market regimes in pair trading:
    - State 0: Mean Reverting (low volatility, stationary)
    - State 1: Trending (persistent directional movement)  
    - State 2: Volatile (high volatility, unstable)
    - State 3: Transitional (regime change periods)
    """
    
    def __init__(self, 
                 n_states: int = 3,
                 state_names: Optional[List[str]] = None,
                 max_iterations: int = 100,
                 tolerance: float = 1e-6,
                 random_state: Optional[int] = None):
        """
        Initialize HMM regime detector
        
        Args:
            n_states: Number of hidden states (regimes)
            state_names: Custom names for states
            max_iterations: Maximum EM iterations
            tolerance: Convergence tolerance
            random_state: Random seed for reproducibility
        """
        self.n_states = n_states
        self.max_iterations = max_iterations
        self.tolerance = tolerance
        self.random_state = random_state
        
        if random_state is not None:
            np.random.seed(random_state)
        
        # Default state names and descriptions
        if state_names is None:
            if n_states == 3:
                self.state_names = ['Mean_Reverting', 'Trending', 'Volatile']
                self.state_descriptions = [
                    'Low volatility, stationary spread behavior',
                    'Persistent directional movement in spread',
                    'High volatility, unstable relationships'
                ]
            elif n_states == 4:
                self.state_names = ['Mean_Reverting', 'Trending', 'Volatile', 'Transitional']
                self.state_descriptions = [
                    'Low volatility, stationary spread behavior',
                    'Persistent directional movement in spread',
                    'High volatility, unstable relationships',
                    'Regime change transition periods'
                ]
            else:
                self.state_names = [f'Regime_{i}' for i in range(n_states)]
                self.state_descriptions = [f'Market regime {i}' for i in range(n_states)]
        else:
            self.state_names = state_names
            self.state_descriptions = [f'Market regime {i}' for i in range(n_states)]
        
        # Model parameters (will be learned)
        self.transition_matrix = None
        self.initial_probabilities = None
        self.emission_means = None
        self.emission_covariances = None
        self.is_fitted = False
        
        logger.info(f"Initialized HMM with {n_states} states: {self.state_names}")
    
    def _initialize_parameters(self, observations: np.ndarray) -> None:
        """Initialize model parameters"""
        n_obs, n_features = observations.shape
        
        # Initialize transition matrix (slightly biased towards staying in same state)
        self.transition_matrix = np.random.dirichlet(np.ones(self.n_states) * 2, self.n_states)
        np.fill_diagonal(self.transition_matrix, self.transition_matrix.diagonal() + 0.5)
        self.transition_matrix = self.transition_matrix / self.transition_matrix.sum(axis=1, keepdims=True)
        
        # Initialize initial state probabilities
        self.initial_probabilities = np.ones(self.n_states) / self.n_states
        
        # Initialize emission parameters using k-means-like approach
        self.emission_means = np.zeros((self.n_states, n_features))
        self.emission_covariances = np.zeros((self.n_states, n_features, n_features))
        
        # Divide observations into clusters for initialization
        cluster_size = n_obs // self.n_states
        for i in range(self.n_states):
            start_idx = i * cluster_size
            end_idx = (i + 1) * cluster_size if i < self.n_states - 1 else n_obs
            cluster_data = observations[start_idx:end_idx]
            
            self.emission_means[i] = np.mean(cluster_data, axis=0)
            cov = np.cov(cluster_data.T)
            if cov.ndim == 0:
                cov = np.array([[cov]])
            elif cov.ndim == 1:
                cov = np.diag(cov)
            
            # Ensure positive definite covariance
            self.emission_covariances[i] = cov + np.eye(n_features) * 1e-6
    
    def _forward_algorithm(self, observations: np.ndarray) -> Tuple[np.ndarray, float]:
        """Forward algorithm for computing forward probabilities"""
        n_obs = len(observations)
        forward_probs = np.zeros((n_obs, self.n_states))
        
        # Initialize
        for i in range(self.n_states):
            forward_probs[0, i] = (self.initial_probabilities[i] * 
                                  self._emission_probability(observations[0], i))
        
        # Forward pass
        for t in range(1, n_obs):
            for j in range(self.n_states):
                forward_probs[t, j] = (
                    np.sum(forward_probs[t-1] * self.transition_matrix[:, j]) *
                    self._emission_probability(observations[t], j)
                )
        
        # Compute log-likelihood
        log_likelihood = np.log(np.sum(forward_probs[-1]) + 1e-10)
        
        return forward_probs, log_likelihood
    
    def _backward_algorithm(self, observations: np.ndarray) -> np.ndarray:
        """Backward algorithm for computing backward probabilities"""
        n_obs = len(observations)
        backward_probs = np.zeros((n_obs, self.n_states))
        
        # Initialize
        backward_probs[-1] = 1.0
        
        # Backward pass
        for t in range(n_obs - 2, -1, -1):
            for i in range(self.n_states):
                backward_probs[t, i] = np.sum(
                    self.transition_matrix[i] * 
                    backward_probs[t+1] * 
                    np.array([self._emission_probability(observations[t+1], j) 
                             for j in range(self.n_states)])
                )
        
        return backward_probs
    
    def _emission_probability(self, observation: np.ndarray, state: int) -> float:
        """Compute emission probability for given observation and state"""
        try:
            if len(observation.shape) == 0:
                observation = np.array([observation])
            
            mean = self.emission_means[state]
            cov = self.emission_covariances[state]
            
            # Handle 1D case
            if len(mean) == 1:
                return norm.pdf(observation[0], mean[0], np.sqrt(cov[0, 0]))
            else:
                return multivariate_normal.pdf(observation, mean, cov)
        except:
            return 1e-10  # Small probability for numerical stability
    
    def _viterbi_algorithm(self, observations: np.ndarray) -> np.ndarray:
        """Viterbi algorithm for finding most likely state sequence"""
        n_obs = len(observations)
        
        # Initialize
        delta = np.zeros((n_obs, self.n_states))
        psi = np.zeros((n_obs, self.n_states), dtype=int)
        
        # Initialize first time step
        for i in range(self.n_states):
            delta[0, i] = (self.initial_probabilities[i] * 
                          self._emission_probability(observations[0], i))
        
        # Forward pass
        for t in range(1, n_obs):
            for j in range(self.n_states):
                probs = delta[t-1] * self.transition_matrix[:, j]
                psi[t, j] = np.argmax(probs)
                delta[t, j] = (np.max(probs) * 
                              self._emission_probability(observations[t], j))
        
        # Backward pass - find most likely path
        states = np.zeros(n_obs, dtype=int)
        states[-1] = np.argmax(delta[-1])
        
        for t in range(n_obs - 2, -1, -1):
            states[t] = psi[t + 1, states[t + 1]]
        
        return states
    
    def _expectation_maximization(self, observations: np.ndarray) -> float:
        """EM algorithm for parameter estimation"""
        n_obs, n_features = observations.shape
        
        # E-step: compute forward-backward probabilities
        forward_probs, log_likelihood = self._forward_algorithm(observations)
        backward_probs = self._backward_algorithm(observations)
        
        # Compute gamma (state probabilities) and xi (transition probabilities)
        gamma = forward_probs * backward_probs
        gamma = gamma / (np.sum(gamma, axis=1, keepdims=True) + 1e-10)
        
        xi = np.zeros((n_obs - 1, self.n_states, self.n_states))
        for t in range(n_obs - 1):
            for i in range(self.n_states):
                for j in range(self.n_states):
                    xi[t, i, j] = (
                        forward_probs[t, i] * 
                        self.transition_matrix[i, j] * 
                        self._emission_probability(observations[t+1], j) * 
                        backward_probs[t+1, j]
                    )
        
        # Normalize xi
        xi_sum = np.sum(xi, axis=(1, 2), keepdims=True)
        xi = xi / (xi_sum + 1e-10)
        
        # M-step: update parameters
        # Update initial probabilities
        self.initial_probabilities = gamma[0] / np.sum(gamma[0])
        
        # Update transition matrix
        for i in range(self.n_states):
            for j in range(self.n_states):
                self.transition_matrix[i, j] = (
                    np.sum(xi[:, i, j]) / (np.sum(gamma[:-1, i]) + 1e-10)
                )
        
        # Update emission parameters
        for i in range(self.n_states):
            gamma_sum = np.sum(gamma[:, i]) + 1e-10
            
            # Update means
            self.emission_means[i] = np.sum(
                observations * gamma[:, i:i+1], axis=0
            ) / gamma_sum
            
            # Update covariances
            diff = observations - self.emission_means[i]
            self.emission_covariances[i] = (
                np.sum(gamma[:, i:i+1, np.newaxis] * diff[:, :, np.newaxis] * 
                      diff[:, np.newaxis, :], axis=0) / gamma_sum
            )
            
            # Ensure positive definite
            self.emission_covariances[i] += np.eye(n_features) * 1e-6
        
        return log_likelihood
    
    def fit(self, spread_data: pd.Series, 
            additional_features: Optional[pd.DataFrame] = None) -> 'HMMResult':
        """
        Fit HMM to spread data and additional features
        
        Args:
            spread_data: Spread time series
            additional_features: Additional features (volatility, returns, etc.)
            
        Returns:
            HMMResult with regime detection results
        """
        # Prepare observations
        observations = self._prepare_observations(spread_data, additional_features)
        
        # Initialize parameters
        self._initialize_parameters(observations)
        
        # EM algorithm
        prev_log_likelihood = -np.inf
        
        for iteration in range(self.max_iterations):
            log_likelihood = self._expectation_maximization(observations)
            
            # Check convergence
            if abs(log_likelihood - prev_log_likelihood) < self.tolerance:
                logger.info(f"EM converged after {iteration + 1} iterations")
                break
            
            prev_log_likelihood = log_likelihood
        else:
            logger.warning(f"EM did not converge after {self.max_iterations} iterations")
        
        # Get most likely state sequence
        states = self._viterbi_algorithm(observations)
        
        # Compute state probabilities
        forward_probs, _ = self._forward_algorithm(observations)
        backward_probs = self._backward_algorithm(observations)
        state_probabilities = forward_probs * backward_probs
        state_probabilities = state_probabilities / np.sum(state_probabilities, axis=1, keepdims=True)
        
        # Create regime states
        regime_states = self._create_regime_states(observations, states)
        
        # Calculate regime statistics
        regime_statistics = self._calculate_regime_statistics(
            observations, states, spread_data.index
        )
        
        self.is_fitted = True
        
        return HMMResult(
            states=states,
            state_probabilities=state_probabilities,
            log_likelihood=log_likelihood,
            regime_states=regime_states,
            transition_matrix=self.transition_matrix,
            emission_parameters={
                'means': self.emission_means,
                'covariances': self.emission_covariances
            },
            current_regime=states[-1],
            current_regime_probability=state_probabilities[-1, states[-1]],
            regime_statistics=regime_statistics
        )
    
    def _prepare_observations(self, spread_data: pd.Series, 
                            additional_features: Optional[pd.DataFrame] = None) -> np.ndarray:
        """Prepare observation matrix for HMM"""
        # Basic features from spread
        returns = spread_data.pct_change().fillna(0)
        volatility = returns.rolling(window=20).std().fillna(returns.std())
        z_scores = (spread_data - spread_data.rolling(window=60).mean()) / spread_data.rolling(window=60).std()
        z_scores = z_scores.fillna(0)
        
        # Create observation matrix
        observations = np.column_stack([
            returns.values,
            volatility.values,
            z_scores.values
        ])
        
        # Add additional features if provided
        if additional_features is not None:
            # Align indices
            common_index = spread_data.index.intersection(additional_features.index)
            if len(common_index) > 0:
                additional_aligned = additional_features.loc[common_index].fillna(0)
                spread_aligned = spread_data.loc[common_index]
                
                # Recalculate basic features for aligned data
                returns_aligned = spread_aligned.pct_change().fillna(0)
                volatility_aligned = returns_aligned.rolling(window=20).std().fillna(returns_aligned.std())
                z_scores_aligned = ((spread_aligned - spread_aligned.rolling(window=60).mean()) / 
                                  spread_aligned.rolling(window=60).std()).fillna(0)
                
                observations = np.column_stack([
                    returns_aligned.values,
                    volatility_aligned.values,
                    z_scores_aligned.values,
                    additional_aligned.values
                ])
        
        # Remove any remaining NaN values
        observations = np.nan_to_num(observations, nan=0.0, posinf=0.0, neginf=0.0)
        
        return observations
    
    def _create_regime_states(self, observations: np.ndarray, states: np.ndarray) -> List[RegimeState]:
        """Create regime state objects with statistics"""
        regime_states = []
        
        for i in range(self.n_states):
            state_mask = states == i
            if np.sum(state_mask) > 0:
                state_obs = observations[state_mask]
                
                # Calculate statistics
                mean_return = np.mean(state_obs[:, 0])  # Returns
                volatility = np.mean(state_obs[:, 1])   # Volatility
                
                # Mean reversion strength (inverse of absolute z-score)
                mean_z_score = np.mean(np.abs(state_obs[:, 2]))
                mean_reversion_strength = 1.0 / (1.0 + mean_z_score)
                
                # Persistence (expected duration based on transition matrix)
                persistence = 1.0 / (1.0 - self.transition_matrix[i, i]) if self.transition_matrix[i, i] < 1.0 else 10.0
            else:
                mean_return = 0.0
                volatility = 0.0
                mean_reversion_strength = 0.5
                persistence = 1.0
            
            regime_state = RegimeState(
                id=i,
                name=self.state_names[i],
                description=self.state_descriptions[i],
                mean_return=mean_return,
                volatility=volatility,
                mean_reversion_strength=mean_reversion_strength,
                persistence=persistence
            )
            
            regime_states.append(regime_state)
        
        return regime_states
    
    def _calculate_regime_statistics(self, observations: np.ndarray, 
                                   states: np.ndarray, 
                                   time_index: pd.Index) -> Dict[str, Any]:
        """Calculate comprehensive regime statistics"""
        stats = {}
        
        # Overall statistics
        stats['total_observations'] = len(states)
        stats['regime_changes'] = len(np.where(np.diff(states) != 0)[0])
        stats['average_regime_duration'] = len(states) / (stats['regime_changes'] + 1)
        
        # Per-regime statistics
        for i in range(self.n_states):
            regime_name = self.state_names[i]
            state_mask = states == i
            
            stats[f'{regime_name}_frequency'] = np.sum(state_mask) / len(states)
            stats[f'{regime_name}_count'] = np.sum(state_mask)
            
            if np.sum(state_mask) > 0:
                state_obs = observations[state_mask]
                stats[f'{regime_name}_mean_return'] = np.mean(state_obs[:, 0])
                stats[f'{regime_name}_volatility'] = np.mean(state_obs[:, 1])
                stats[f'{regime_name}_mean_z_score'] = np.mean(state_obs[:, 2])
        
        # Transition statistics
        stats['transition_matrix'] = self.transition_matrix.tolist()
        stats['regime_names'] = self.state_names
        
        return stats
    
    def predict_regime(self, new_observations: np.ndarray) -> Tuple[int, np.ndarray]:
        """
        Predict regime for new observations
        
        Args:
            new_observations: New observation data
            
        Returns:
            Tuple of (most_likely_regime, regime_probabilities)
        """
        if not self.is_fitted:
            raise ValueError("Model must be fitted before prediction")
        
        # Compute probabilities for each regime
        regime_probs = np.zeros(self.n_states)
        
        for i in range(self.n_states):
            regime_probs[i] = self._emission_probability(new_observations, i)
        
        # Normalize probabilities
        regime_probs = regime_probs / (np.sum(regime_probs) + 1e-10)
        
        # Most likely regime
        most_likely_regime = np.argmax(regime_probs)
        
        return most_likely_regime, regime_probs


def create_hmm_detector(spread_data: pd.Series, 
                       n_states: int = 3,
                       additional_features: Optional[pd.DataFrame] = None,
                       **kwargs) -> HMMResult:
    """
    Convenience function to create and fit an HMM detector
    
    Args:
        spread_data: Spread time series
        n_states: Number of regimes to detect
        additional_features: Additional features for regime detection
        **kwargs: Additional parameters for HMMRegimeDetector
        
    Returns:
        HMMResult with regime detection results
    """
    detector = HMMRegimeDetector(n_states=n_states, **kwargs)
    return detector.fit(spread_data, additional_features) 