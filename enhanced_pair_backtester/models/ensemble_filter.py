"""
Ensemble Trade Filter for Statistical Arbitrage

This module implements an ensemble approach to trade filtering that combines:
- Kalman filter dynamic hedge ratios and uncertainty
- HMM regime detection and regime-specific behavior
- Technical indicators and market microstructure signals
- Risk management and position sizing recommendations

The ensemble provides:
- Trade signal strength (0-100)
- Confidence intervals
- Risk-adjusted position sizing
- Regime-aware entry/exit thresholds
- Multi-timeframe analysis

Author: Pro Quant Desk Trader
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Any, Union
import logging
from scipy import stats
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import classification_report, accuracy_score
import warnings

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


@dataclass
class TradeSignal:
    """Container for trade signal information"""
    signal_type: str  # 'LONG', 'SHORT', 'HOLD'
    strength: float  # 0-100 signal strength
    confidence: float  # 0-1 confidence level
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float  # Recommended position size (0-1)
    holding_period: int  # Expected holding period in periods
    risk_reward_ratio: float
    regime: str  # Current market regime
    features: Dict[str, float]  # Feature values used for decision


@dataclass
class EnsembleResult:
    """Results from ensemble trade filter"""
    current_signal: TradeSignal
    signal_history: List[TradeSignal]
    model_predictions: Dict[str, float]  # Individual model predictions
    feature_importance: Dict[str, float]
    performance_metrics: Dict[str, Any]
    calibration_stats: Dict[str, Any]
    
    @property
    def should_trade(self) -> bool:
        """Whether to execute the trade based on ensemble criteria"""
        return (self.current_signal.strength > 60 and 
                self.current_signal.confidence > 0.7 and
                self.current_signal.position_size > 0.1)
    
    @property
    def risk_level(self) -> str:
        """Current risk level assessment"""
        if self.current_signal.confidence > 0.8:
            return "LOW"
        elif self.current_signal.confidence > 0.6:
            return "MEDIUM"
        else:
            return "HIGH"


class EnsembleTradeFilter:
    """
    Ensemble Trade Filter for Statistical Arbitrage
    
    Combines multiple models and signals:
    1. Kalman Filter: Dynamic hedge ratios and uncertainty
    2. HMM Regime Detection: Market regime classification
    3. Technical Indicators: RSI, Bollinger Bands, etc.
    4. Mean Reversion Signals: Z-scores and half-life
    5. Volatility Regime: GARCH-like volatility clustering
    6. Machine Learning: Random Forest, Gradient Boosting, Logistic Regression
    """
    
    def __init__(self, 
                 lookback_window: int = 252,
                 confidence_threshold: float = 0.7,
                 strength_threshold: float = 60,
                 max_position_size: float = 0.5,
                 risk_free_rate: float = 0.02,
                 random_state: int = 42):
        """
        Initialize ensemble trade filter
        
        Args:
            lookback_window: Lookback period for feature calculation
            confidence_threshold: Minimum confidence for trade execution
            strength_threshold: Minimum signal strength for trade execution
            max_position_size: Maximum position size (0-1)
            risk_free_rate: Risk-free rate for Sharpe calculations
            random_state: Random seed for reproducibility
        """
        self.lookback_window = lookback_window
        self.confidence_threshold = confidence_threshold
        self.strength_threshold = strength_threshold
        self.max_position_size = max_position_size
        self.risk_free_rate = risk_free_rate
        self.random_state = random_state
        
        # Model components
        self.models = {
            'random_forest': RandomForestClassifier(
                n_estimators=100, 
                max_depth=10, 
                random_state=random_state,
                n_jobs=-1
            ),
            'gradient_boosting': GradientBoostingClassifier(
                n_estimators=100, 
                max_depth=6, 
                random_state=random_state
            ),
            'logistic_regression': LogisticRegression(
                random_state=random_state,
                max_iter=1000
            )
        }
        
        self.scaler = StandardScaler()
        self.is_fitted = False
        self.feature_names = []
        self.signal_history = []
        
        logger.info("Initialized ensemble trade filter with 3 base models")
    
    def _calculate_technical_features(self, 
                                    spread: pd.Series,
                                    price1: pd.Series,
                                    price2: pd.Series) -> pd.DataFrame:
        """Calculate technical analysis features"""
        features = pd.DataFrame(index=spread.index)
        
        # Spread-based features
        features['spread'] = spread
        features['spread_returns'] = spread.pct_change()
        features['spread_volatility'] = features['spread_returns'].rolling(20).std()
        
        # Z-score features (multiple timeframes)
        for window in [20, 60, 120]:
            rolling_mean = spread.rolling(window).mean()
            rolling_std = spread.rolling(window).std()
            features[f'z_score_{window}'] = (spread - rolling_mean) / rolling_std
        
        # RSI for spread
        features['spread_rsi'] = self._calculate_rsi(spread, 14)
        
        # Bollinger Bands
        bb_period = 20
        bb_std = 2
        bb_mean = spread.rolling(bb_period).mean()
        bb_std_dev = spread.rolling(bb_period).std()
        features['bb_upper'] = bb_mean + (bb_std * bb_std_dev)
        features['bb_lower'] = bb_mean - (bb_std * bb_std_dev)
        features['bb_position'] = (spread - bb_mean) / (bb_std * bb_std_dev)
        
        # Mean reversion features
        features['half_life'] = self._calculate_half_life(spread, 60)
        features['mean_reversion_strength'] = self._calculate_mean_reversion_strength(spread, 60)
        
        # Volatility clustering
        features['vol_regime'] = self._detect_volatility_regime(features['spread_returns'], 20)
        
        # Price momentum for individual assets
        features['price1_momentum'] = price1.pct_change(10)
        features['price2_momentum'] = price2.pct_change(10)
        features['momentum_divergence'] = features['price1_momentum'] - features['price2_momentum']
        
        # Volume proxy (using price volatility as proxy)
        features['volume_proxy'] = (price1.pct_change().abs() + price2.pct_change().abs()) / 2
        features['volume_sma'] = features['volume_proxy'].rolling(20).mean()
        features['volume_ratio'] = features['volume_proxy'] / features['volume_sma']
        
        return features.fillna(method='ffill').fillna(0)
    
    def _calculate_rsi(self, series: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_half_life(self, series: pd.Series, window: int) -> pd.Series:
        """Calculate half-life of mean reversion"""
        half_lives = []
        
        for i in range(window, len(series)):
            y = series.iloc[i-window:i]
            y_lag = y.shift(1).dropna()
            y_ret = y.diff().dropna()
            
            if len(y_lag) > 10:
                # Estimate AR(1) coefficient
                try:
                    from sklearn.linear_model import LinearRegression
                    model = LinearRegression()
                    model.fit(y_lag.values.reshape(-1, 1), y_ret.values)
                    beta = model.coef_[0]
                    
                    if beta < 0:
                        half_life = -np.log(2) / np.log(1 + beta)
                    else:
                        half_life = np.inf
                except:
                    half_life = np.inf
            else:
                half_life = np.inf
            
            half_lives.append(half_life)
        
        # Pad with NaN for the initial window
        result = pd.Series([np.nan] * window + half_lives, index=series.index)
        return result.fillna(method='ffill')
    
    def _calculate_mean_reversion_strength(self, series: pd.Series, window: int) -> pd.Series:
        """Calculate mean reversion strength using Hurst exponent"""
        hurst_values = []
        
        for i in range(window, len(series)):
            y = series.iloc[i-window:i].values
            
            if len(y) > 10:
                try:
                    # Calculate Hurst exponent
                    lags = range(2, min(20, len(y)//2))
                    tau = [np.sqrt(np.std(np.subtract(y[lag:], y[:-lag]))) for lag in lags]
                    
                    if len(tau) > 3:
                        poly = np.polyfit(np.log(lags), np.log(tau), 1)
                        hurst = poly[0] * 2.0
                        
                        # Convert to mean reversion strength (0-1)
                        # Hurst < 0.5 = mean reverting, Hurst > 0.5 = trending
                        strength = max(0, 1 - 2 * abs(hurst - 0.5))
                    else:
                        strength = 0.5
                except:
                    strength = 0.5
            else:
                strength = 0.5
            
            hurst_values.append(strength)
        
        result = pd.Series([np.nan] * window + hurst_values, index=series.index)
        return result.fillna(method='ffill')
    
    def _detect_volatility_regime(self, returns: pd.Series, window: int) -> pd.Series:
        """Detect volatility regime (0=low, 1=high)"""
        volatility = returns.rolling(window).std()
        vol_percentile = volatility.rolling(window*2).rank(pct=True)
        regime = (vol_percentile > 0.7).astype(int)
        return regime
    
    def _create_labels(self, 
                      spread: pd.Series,
                      future_returns: pd.Series,
                      holding_period: int = 5) -> pd.Series:
        """Create trading labels based on future returns"""
        # Calculate future returns over holding period
        future_ret = future_returns.shift(-holding_period)
        
        # Create labels: 1 for profitable trades, 0 for unprofitable
        labels = pd.Series(0, index=spread.index)
        
        # Long signals: expect spread to decrease (negative returns)
        # Short signals: expect spread to increase (positive returns)
        
        # Use percentile-based labeling
        ret_percentiles = future_ret.rolling(252).rank(pct=True)
        
        # Label as 1 if future return is in extreme percentiles
        labels[(ret_percentiles < 0.2) | (ret_percentiles > 0.8)] = 1
        
        return labels
    
    def _extract_features(self, 
                         spread: pd.Series,
                         price1: pd.Series,
                         price2: pd.Series,
                         kalman_result: Optional[Any] = None,
                         hmm_result: Optional[Any] = None) -> pd.DataFrame:
        """Extract all features for ensemble model"""
        
        # Technical features
        tech_features = self._calculate_technical_features(spread, price1, price2)
        
        # Kalman filter features
        if kalman_result is not None:
            if hasattr(kalman_result, 'hedge_ratios'):
                # Dynamic hedge ratio features
                hedge_ratios = pd.Series(kalman_result.hedge_ratios, index=spread.index)
                tech_features['hedge_ratio'] = hedge_ratios
                tech_features['hedge_ratio_change'] = hedge_ratios.pct_change()
                tech_features['hedge_ratio_volatility'] = hedge_ratios.rolling(20).std()
                
                # Uncertainty features
                if hasattr(kalman_result, 'hedge_ratio_variance'):
                    uncertainty = pd.Series(np.sqrt(kalman_result.hedge_ratio_variance), index=spread.index)
                    tech_features['kalman_uncertainty'] = uncertainty
                    tech_features['uncertainty_regime'] = (uncertainty > uncertainty.rolling(60).median()).astype(int)
        
        # HMM regime features
        if hmm_result is not None:
            if hasattr(hmm_result, 'states'):
                # Ensure regime states match spread index length
                if len(hmm_result.states) == len(spread):
                    regime_states = pd.Series(hmm_result.states, index=spread.index)
                    tech_features['regime'] = regime_states
                    
                    # One-hot encode regimes
                    for i, regime_name in enumerate(hmm_result.regime_states):
                        tech_features[f'regime_{regime_name.name}'] = (regime_states == i).astype(int)
                    
                    # Regime transition features
                    tech_features['regime_change'] = (regime_states.diff() != 0).astype(int)
                    
                    # Regime probabilities
                    if hasattr(hmm_result, 'state_probabilities'):
                        if len(hmm_result.state_probabilities) == len(spread):
                            state_probs = pd.DataFrame(hmm_result.state_probabilities, index=spread.index)
                            tech_features['regime_confidence'] = state_probs.max(axis=1)
                            tech_features['regime_entropy'] = -(state_probs * np.log(state_probs + 1e-10)).sum(axis=1)
                else:
                    logger.warning(f"HMM states length ({len(hmm_result.states)}) doesn't match spread length ({len(spread)})")
                    # Add dummy regime features
                    tech_features['regime'] = 0
                    tech_features['regime_change'] = 0
                    tech_features['regime_confidence'] = 0.5
        
        # Interaction features
        if 'z_score_60' in tech_features.columns and 'regime' in tech_features.columns:
            tech_features['z_score_regime_interaction'] = tech_features['z_score_60'] * tech_features['regime']
        
        return tech_features
    
    def fit(self, 
            spread: pd.Series,
            price1: pd.Series,
            price2: pd.Series,
            kalman_result: Optional[Any] = None,
            hmm_result: Optional[Any] = None,
            holding_period: int = 5) -> Dict[str, Any]:
        """
        Fit ensemble models to historical data
        
        Args:
            spread: Spread time series
            price1: First asset price series
            price2: Second asset price series
            kalman_result: Kalman filter results
            hmm_result: HMM regime detection results
            holding_period: Holding period for label creation
            
        Returns:
            Dictionary with fitting results and performance metrics
        """
        logger.info("Fitting ensemble trade filter...")
        
        # Extract features
        features = self._extract_features(spread, price1, price2, kalman_result, hmm_result)
        
        # Create labels
        spread_returns = spread.pct_change()
        labels = self._create_labels(spread, spread_returns, holding_period)
        
        # Align data
        common_index = features.index.intersection(labels.index)
        features_aligned = features.loc[common_index]
        labels_aligned = labels.loc[common_index]
        
        # Remove NaN values
        valid_mask = ~(features_aligned.isna().any(axis=1) | labels_aligned.isna())
        features_clean = features_aligned[valid_mask]
        labels_clean = labels_aligned[valid_mask]
        
        if len(features_clean) < 100:
            raise ValueError("Insufficient clean data for training")
        
        # Store feature names
        self.feature_names = list(features_clean.columns)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(features_clean)
        y = labels_clean.values
        
        # Time series cross-validation
        tscv = TimeSeriesSplit(n_splits=5)
        model_scores = {}
        
        # Train each model
        for model_name, model in self.models.items():
            logger.info(f"Training {model_name}...")
            
            # Cross-validation
            cv_scores = []
            for train_idx, val_idx in tscv.split(X_scaled):
                X_train, X_val = X_scaled[train_idx], X_scaled[val_idx]
                y_train, y_val = y[train_idx], y[val_idx]
                
                model.fit(X_train, y_train)
                score = model.score(X_val, y_val)
                cv_scores.append(score)
            
            model_scores[model_name] = np.mean(cv_scores)
            logger.info(f"{model_name} CV score: {model_scores[model_name]:.4f}")
            
            # Fit on full data
            model.fit(X_scaled, y)
        
        # Calculate feature importance
        feature_importance = {}
        if hasattr(self.models['random_forest'], 'feature_importances_'):
            for i, feature in enumerate(self.feature_names):
                feature_importance[feature] = self.models['random_forest'].feature_importances_[i]
        
        # Performance metrics
        performance_metrics = {
            'model_scores': model_scores,
            'best_model': max(model_scores, key=model_scores.get),
            'n_features': len(self.feature_names),
            'n_samples': len(features_clean),
            'label_distribution': labels_clean.value_counts().to_dict()
        }
        
        self.is_fitted = True
        
        logger.info(f"Ensemble training completed. Best model: {performance_metrics['best_model']}")
        
        return {
            'performance_metrics': performance_metrics,
            'feature_importance': feature_importance,
            'model_scores': model_scores
        }
    
    def predict(self, 
                spread: pd.Series,
                price1: pd.Series,
                price2: pd.Series,
                kalman_result: Optional[Any] = None,
                hmm_result: Optional[Any] = None) -> EnsembleResult:
        """
        Generate trading signals using ensemble approach
        
        Args:
            spread: Current spread time series
            price1: First asset price series
            price2: Second asset price series
            kalman_result: Kalman filter results
            hmm_result: HMM regime detection results
            
        Returns:
            EnsembleResult with trading recommendations
        """
        if not self.is_fitted:
            raise ValueError("Model must be fitted before prediction")
        
        # Extract features
        features = self._extract_features(spread, price1, price2, kalman_result, hmm_result)
        
        # Get latest features
        latest_features = features.iloc[-1:][self.feature_names]
        
        if latest_features.isna().any().any():
            logger.warning("NaN values in latest features, filling with zeros")
            latest_features = latest_features.fillna(0)
        
        # Scale features
        X_scaled = self.scaler.transform(latest_features)
        
        # Get predictions from each model
        model_predictions = {}
        model_probabilities = {}
        
        for model_name, model in self.models.items():
            pred = model.predict(X_scaled)[0]
            prob = model.predict_proba(X_scaled)[0]
            
            model_predictions[model_name] = pred
            model_probabilities[model_name] = prob[1]  # Probability of class 1
        
        # Ensemble prediction (weighted average)
        ensemble_prob = np.mean(list(model_probabilities.values()))
        ensemble_pred = int(ensemble_prob > 0.5)
        
        # Generate trading signal
        current_signal = self._generate_signal(
            spread, price1, price2, 
            ensemble_pred, ensemble_prob,
            latest_features, kalman_result, hmm_result
        )
        
        # Update signal history
        self.signal_history.append(current_signal)
        
        # Keep only recent history
        if len(self.signal_history) > 1000:
            self.signal_history = self.signal_history[-1000:]
        
        # Calculate feature importance (if available)
        feature_importance = {}
        if hasattr(self.models['random_forest'], 'feature_importances_'):
            for i, feature in enumerate(self.feature_names):
                feature_importance[feature] = self.models['random_forest'].feature_importances_[i]
        
        return EnsembleResult(
            current_signal=current_signal,
            signal_history=self.signal_history.copy(),
            model_predictions=model_probabilities,
            feature_importance=feature_importance,
            performance_metrics={},
            calibration_stats={}
        )
    
    def _generate_signal(self, 
                        spread: pd.Series,
                        price1: pd.Series,
                        price2: pd.Series,
                        prediction: int,
                        probability: float,
                        features: pd.DataFrame,
                        kalman_result: Optional[Any] = None,
                        hmm_result: Optional[Any] = None) -> TradeSignal:
        """Generate detailed trading signal"""
        
        current_spread = spread.iloc[-1]
        current_price1 = price1.iloc[-1]
        current_price2 = price2.iloc[-1]
        
        # Determine signal type based on z-score and prediction
        z_score = features['z_score_60'].iloc[-1] if 'z_score_60' in features.columns else 0
        
        if prediction == 1:  # Model predicts profitable trade
            if z_score > 0:  # Spread is high, expect mean reversion
                signal_type = "SHORT"
                entry_price = current_spread
                stop_loss = current_spread * 1.02  # 2% stop loss
                take_profit = current_spread * 0.98  # 2% take profit
            else:  # Spread is low, expect mean reversion
                signal_type = "LONG"
                entry_price = current_spread
                stop_loss = current_spread * 0.98  # 2% stop loss
                take_profit = current_spread * 1.02  # 2% take profit
        else:
            signal_type = "HOLD"
            entry_price = current_spread
            stop_loss = current_spread
            take_profit = current_spread
        
        # Calculate signal strength (0-100)
        strength = probability * 100
        
        # Adjust strength based on regime
        if hmm_result is not None and hasattr(hmm_result, 'current_regime_probability'):
            regime_confidence = hmm_result.current_regime_probability
            strength *= regime_confidence
        
        # Calculate position size based on Kelly criterion
        position_size = self._calculate_position_size(
            spread, probability, features, kalman_result
        )
        
        # Estimate holding period
        holding_period = self._estimate_holding_period(features, hmm_result)
        
        # Calculate risk-reward ratio
        if signal_type != "HOLD":
            risk = abs(entry_price - stop_loss)
            reward = abs(take_profit - entry_price)
            risk_reward_ratio = reward / risk if risk > 0 else 0
        else:
            risk_reward_ratio = 0
        
        # Current regime
        current_regime = "Unknown"
        if hmm_result is not None and hasattr(hmm_result, 'current_regime_name'):
            current_regime = hmm_result.current_regime_name
        
        # Feature values for transparency
        feature_dict = features.iloc[-1].to_dict()
        
        return TradeSignal(
            signal_type=signal_type,
            strength=strength,
            confidence=probability,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=position_size,
            holding_period=holding_period,
            risk_reward_ratio=risk_reward_ratio,
            regime=current_regime,
            features=feature_dict
        )
    
    def _calculate_position_size(self, 
                               spread: pd.Series,
                               probability: float,
                               features: pd.DataFrame,
                               kalman_result: Optional[Any] = None) -> float:
        """Calculate position size using Kelly criterion and risk management"""
        
        # Base Kelly calculation
        win_rate = probability
        avg_win = 0.02  # Expected 2% profit
        avg_loss = 0.02  # Expected 2% loss
        
        if win_rate > 0.5:
            kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
        else:
            kelly_fraction = 0
        
        # Apply risk management constraints
        kelly_fraction = max(0, min(kelly_fraction, 0.25))  # Cap at 25%
        
        # Adjust for volatility
        if 'spread_volatility' in features.columns:
            volatility = features['spread_volatility'].iloc[-1]
            if volatility > 0:
                vol_adjustment = min(1.0, 0.02 / volatility)  # Target 2% volatility
                kelly_fraction *= vol_adjustment
        
        # Adjust for Kalman uncertainty
        if kalman_result is not None and hasattr(kalman_result, 'current_uncertainty'):
            uncertainty = kalman_result.current_uncertainty
            uncertainty_adjustment = max(0.1, 1 - uncertainty)
            kelly_fraction *= uncertainty_adjustment
        
        # Final position size
        position_size = min(kelly_fraction, self.max_position_size)
        
        return max(0, position_size)
    
    def _estimate_holding_period(self, 
                               features: pd.DataFrame,
                               hmm_result: Optional[Any] = None) -> int:
        """Estimate optimal holding period"""
        
        # Base holding period
        holding_period = 5
        
        # Adjust based on half-life
        if 'half_life' in features.columns:
            half_life = features['half_life'].iloc[-1]
            if not np.isinf(half_life) and half_life > 0:
                holding_period = int(min(20, max(2, half_life * 2)))
        
        # Adjust based on regime persistence
        if hmm_result is not None and hasattr(hmm_result, 'regime_states'):
            current_regime_id = hmm_result.current_regime
            if current_regime_id < len(hmm_result.regime_states):
                persistence = hmm_result.regime_states[current_regime_id].persistence
                holding_period = int(min(holding_period, max(2, persistence)))
        
        return holding_period


def create_ensemble_filter(spread: pd.Series,
                         price1: pd.Series,
                         price2: pd.Series,
                         kalman_result: Optional[Any] = None,
                         hmm_result: Optional[Any] = None,
                         **kwargs) -> EnsembleResult:
    """
    Convenience function to create and fit ensemble filter
    
    Args:
        spread: Spread time series
        price1: First asset price series
        price2: Second asset price series
        kalman_result: Kalman filter results
        hmm_result: HMM regime detection results
        **kwargs: Additional parameters for EnsembleTradeFilter
        
    Returns:
        EnsembleResult with trading recommendations
    """
    filter_obj = EnsembleTradeFilter(**kwargs)
    
    # Use 80% of data for training, 20% for prediction
    split_point = int(len(spread) * 0.8)
    
    # Training data
    train_spread = spread.iloc[:split_point]
    train_price1 = price1.iloc[:split_point]
    train_price2 = price2.iloc[:split_point]
    
    # Fit the model
    filter_obj.fit(train_spread, train_price1, train_price2, kalman_result, hmm_result)
    
    # Generate prediction on full data
    result = filter_obj.predict(spread, price1, price2, kalman_result, hmm_result)
    
    return result 