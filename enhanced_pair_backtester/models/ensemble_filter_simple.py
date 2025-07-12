"""
Simplified Ensemble Trade Filter for Statistical Arbitrage

A streamlined version of the ensemble filter that focuses on:
- Core technical indicators
- Basic regime awareness
- Simple machine learning models
- Robust data handling

Author: Pro Quant Desk Trader
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import logging
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import warnings

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


@dataclass
class SimpleTradeSignal:
    """Simplified trade signal container"""
    signal_type: str  # 'LONG', 'SHORT', 'HOLD'
    strength: float  # 0-100
    confidence: float  # 0-1
    position_size: float  # 0-1
    regime: str
    z_score: float
    rsi: float


@dataclass
class SimpleEnsembleResult:
    """Simplified ensemble result"""
    current_signal: SimpleTradeSignal
    model_prediction: float
    feature_importance: Dict[str, float]
    
    @property
    def should_trade(self) -> bool:
        """Whether to execute the trade"""
        return (self.current_signal.strength > 60 and 
                self.current_signal.confidence > 0.6)
    
    @property
    def risk_level(self) -> str:
        """Risk level assessment"""
        if self.current_signal.confidence > 0.8:
            return "LOW"
        elif self.current_signal.confidence > 0.6:
            return "MEDIUM"
        else:
            return "HIGH"


class SimpleEnsembleFilter:
    """
    Simplified Ensemble Trade Filter
    
    Uses basic technical indicators and a single Random Forest model
    for reliable trade signal generation.
    """
    
    def __init__(self, 
                 lookback_window: int = 60,
                 max_position_size: float = 0.3,
                 random_state: int = 42):
        """Initialize simple ensemble filter"""
        self.lookback_window = lookback_window
        self.max_position_size = max_position_size
        self.random_state = random_state
        
        self.model = RandomForestClassifier(
            n_estimators=50,
            max_depth=8,
            random_state=random_state,
            n_jobs=-1
        )
        
        self.scaler = StandardScaler()
        self.is_fitted = False
        self.feature_names = []
        
        logger.info("Initialized simple ensemble filter")
    
    def _calculate_features(self, spread: pd.Series) -> pd.DataFrame:
        """Calculate basic technical features"""
        features = pd.DataFrame(index=spread.index)
        
        # Basic spread features
        features['spread_returns'] = spread.pct_change()
        features['spread_volatility'] = features['spread_returns'].rolling(20).std()
        
        # Z-scores (multiple timeframes)
        for window in [20, 60]:
            rolling_mean = spread.rolling(window).mean()
            rolling_std = spread.rolling(window).std()
            features[f'z_score_{window}'] = (spread - rolling_mean) / rolling_std
        
        # RSI
        features['rsi'] = self._calculate_rsi(spread, 14)
        
        # Moving averages
        features['sma_20'] = spread.rolling(20).mean()
        features['sma_60'] = spread.rolling(60).mean()
        features['ma_ratio'] = features['sma_20'] / features['sma_60']
        
        # Volatility regime (simple)
        vol_20 = features['spread_returns'].rolling(20).std()
        vol_60 = features['spread_returns'].rolling(60).std()
        features['vol_regime'] = (vol_20 > vol_60).astype(int)
        
        # Momentum
        features['momentum_5'] = spread.pct_change(5)
        features['momentum_10'] = spread.pct_change(10)
        
        # Clean data
        features = features.replace([np.inf, -np.inf], np.nan)
        features = features.fillna(method='ffill').fillna(0)
        
        return features
    
    def _calculate_rsi(self, series: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI"""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / (loss + 1e-10)  # Avoid division by zero
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50)  # Neutral RSI for NaN values
    
    def _create_labels(self, spread: pd.Series, holding_period: int = 5) -> pd.Series:
        """Create simple trading labels"""
        future_returns = spread.pct_change(holding_period).shift(-holding_period)
        
        # Label profitable trades (top/bottom 30%)
        labels = pd.Series(0, index=spread.index)
        
        # Rolling percentile labeling
        rolling_percentiles = future_returns.rolling(252).rank(pct=True)
        
        # Profitable trades in extreme percentiles
        labels[(rolling_percentiles < 0.3) | (rolling_percentiles > 0.7)] = 1
        
        return labels
    
    def fit(self, spread: pd.Series, hmm_result: Optional[Any] = None) -> Dict[str, Any]:
        """Fit the simple ensemble model"""
        logger.info("Fitting simple ensemble filter...")
        
        # Calculate features
        features = self._calculate_features(spread)
        
        # Add regime information if available
        if hmm_result is not None and hasattr(hmm_result, 'states'):
            if len(hmm_result.states) == len(spread):
                features['regime'] = hmm_result.states
            else:
                # Use a simple volatility-based regime
                vol = features['spread_returns'].rolling(20).std()
                features['regime'] = (vol > vol.rolling(60).median()).astype(int)
        else:
            # Default regime based on volatility
            vol = features['spread_returns'].rolling(20).std()
            features['regime'] = (vol > vol.rolling(60).median()).astype(int)
        
        # Create labels
        labels = self._create_labels(spread)
        
        # Align data and remove NaN
        common_index = features.index.intersection(labels.index)
        features_aligned = features.loc[common_index]
        labels_aligned = labels.loc[common_index]
        
        # Remove rows with NaN or infinite values
        valid_mask = (
            ~features_aligned.isna().any(axis=1) & 
            ~labels_aligned.isna() &
            np.isfinite(features_aligned.values).all(axis=1)
        )
        
        features_clean = features_aligned[valid_mask]
        labels_clean = labels_aligned[valid_mask]
        
        if len(features_clean) < 100:
            raise ValueError(f"Insufficient clean data: {len(features_clean)} samples")
        
        # Store feature names
        self.feature_names = list(features_clean.columns)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(features_clean)
        y = labels_clean.values
        
        # Train model
        self.model.fit(X_scaled, y)
        
        # Calculate performance metrics
        train_score = self.model.score(X_scaled, y)
        
        # Feature importance
        feature_importance = {}
        for i, feature in enumerate(self.feature_names):
            feature_importance[feature] = self.model.feature_importances_[i]
        
        self.is_fitted = True
        
        logger.info(f"Simple ensemble training completed. Score: {train_score:.4f}")
        
        return {
            'train_score': train_score,
            'n_features': len(self.feature_names),
            'n_samples': len(features_clean),
            'feature_importance': feature_importance
        }
    
    def predict(self, spread: pd.Series, hmm_result: Optional[Any] = None) -> SimpleEnsembleResult:
        """Generate trading signal"""
        if not self.is_fitted:
            raise ValueError("Model must be fitted before prediction")
        
        # Calculate features
        features = self._calculate_features(spread)
        
        # Add regime information
        if hmm_result is not None and hasattr(hmm_result, 'states'):
            if len(hmm_result.states) == len(spread):
                features['regime'] = hmm_result.states
            else:
                vol = features['spread_returns'].rolling(20).std()
                features['regime'] = (vol > vol.rolling(60).median()).astype(int)
        else:
            vol = features['spread_returns'].rolling(20).std()
            features['regime'] = (vol > vol.rolling(60).median()).astype(int)
        
        # Get latest features
        latest_features = features.iloc[-1:][self.feature_names]
        
        # Handle any remaining NaN or infinite values
        latest_features = latest_features.replace([np.inf, -np.inf], np.nan)
        latest_features = latest_features.fillna(0)
        
        # Scale features
        X_scaled = self.scaler.transform(latest_features)
        
        # Get prediction
        prediction = self.model.predict(X_scaled)[0]
        probability = self.model.predict_proba(X_scaled)[0][1]
        
        # Generate signal
        current_signal = self._generate_signal(spread, prediction, probability, latest_features, hmm_result)
        
        # Feature importance
        feature_importance = {}
        for i, feature in enumerate(self.feature_names):
            feature_importance[feature] = self.model.feature_importances_[i]
        
        return SimpleEnsembleResult(
            current_signal=current_signal,
            model_prediction=probability,
            feature_importance=feature_importance
        )
    
    def _generate_signal(self, spread: pd.Series, prediction: int, probability: float, 
                        features: pd.DataFrame, hmm_result: Optional[Any] = None) -> SimpleTradeSignal:
        """Generate trading signal"""
        
        # Get current values
        z_score = features['z_score_60'].iloc[-1]
        rsi = features['rsi'].iloc[-1]
        
        # Determine signal type
        if prediction == 1:  # Model predicts profitable trade
            if z_score > 0:  # Spread is high
                signal_type = "SHORT"
            else:  # Spread is low
                signal_type = "LONG"
        else:
            signal_type = "HOLD"
        
        # Calculate strength
        strength = probability * 100
        
        # Adjust strength based on z-score magnitude
        strength *= min(1.0, abs(z_score) / 2.0)
        
        # Calculate position size (Kelly-like)
        if prediction == 1:
            position_size = min(self.max_position_size, probability * 0.5)
        else:
            position_size = 0.0
        
        # Current regime
        regime = "Unknown"
        if hmm_result is not None and hasattr(hmm_result, 'current_regime_name'):
            regime = hmm_result.current_regime_name
        
        return SimpleTradeSignal(
            signal_type=signal_type,
            strength=strength,
            confidence=probability,
            position_size=position_size,
            regime=regime,
            z_score=z_score,
            rsi=rsi
        )


def create_simple_ensemble_filter(spread: pd.Series, 
                                 hmm_result: Optional[Any] = None,
                                 **kwargs) -> SimpleEnsembleResult:
    """
    Convenience function to create and fit simple ensemble filter
    
    Args:
        spread: Spread time series
        hmm_result: HMM regime detection results
        **kwargs: Additional parameters
        
    Returns:
        SimpleEnsembleResult with trading recommendations
    """
    filter_obj = SimpleEnsembleFilter(**kwargs)
    
    # Use 80% of data for training
    split_point = int(len(spread) * 0.8)
    train_spread = spread.iloc[:split_point]
    
    # Fit the model
    filter_obj.fit(train_spread, hmm_result)
    
    # Generate prediction on full data
    result = filter_obj.predict(spread, hmm_result)
    
    return result 