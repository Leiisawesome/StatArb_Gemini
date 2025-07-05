"""
Advanced Signal Generation System
Implements regime detection, volatility clustering, ML enhancement, and alternative data integration.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass
import logging
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import classification_report, mean_squared_error
import warnings
from scipy import stats
from scipy.signal import find_peaks

logger = logging.getLogger(__name__)

@dataclass
class MarketRegime:
    """Market regime information."""
    regime_type: str  # 'bull', 'bear', 'sideways', 'volatile', 'calm'
    confidence: float
    duration: int
    volatility_level: float
    trend_strength: float
    regime_score: float
    timestamp: pd.Timestamp

@dataclass
class SignalFeatures:
    """Advanced signal features."""
    technical_features: Dict[str, float]
    regime_features: Dict[str, float]
    volatility_features: Dict[str, float]
    alternative_features: Dict[str, float]
    ml_features: Dict[str, float]

class TechnicalIndicators:
    """Pure Pandas/Numpy implementation of technical indicators."""
    
    @staticmethod
    def sma(prices: pd.Series, period: int) -> pd.Series:
        """Simple Moving Average."""
        return prices.rolling(window=period).mean()
    
    @staticmethod
    def ema(prices: pd.Series, period: int) -> pd.Series:
        """Exponential Moving Average."""
        return prices.ewm(span=period).mean()
    
    @staticmethod
    def rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """Relative Strength Index."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """MACD (Moving Average Convergence Divergence)."""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram
    
    @staticmethod
    def bollinger_bands(prices: pd.Series, period: int = 20, std_dev: int = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Bollinger Bands."""
        middle = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        return upper, middle, lower
    
    @staticmethod
    def stochastic(prices: pd.Series, period: int = 14) -> Tuple[pd.Series, pd.Series]:
        """Stochastic Oscillator."""
        low_min = prices.rolling(window=period).min()
        high_max = prices.rolling(window=period).max()
        k_percent = 100 * ((prices - low_min) / (high_max - low_min))
        d_percent = k_percent.rolling(window=3).mean()
        return k_percent, d_percent
    
    @staticmethod
    def williams_r(prices: pd.Series, period: int = 14) -> pd.Series:
        """Williams %R."""
        low_min = prices.rolling(window=period).min()
        high_max = prices.rolling(window=period).max()
        williams_r = -100 * ((high_max - prices) / (high_max - low_min))
        return williams_r
    
    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Average True Range."""
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr

class RegimeDetector:
    """
    Advanced market regime detection using multiple methodologies.
    """
    
    def __init__(self, lookback_window: int = 252):
        self.lookback_window = lookback_window
        self.regime_history: List[MarketRegime] = []
        self.volatility_regime_thresholds = {
            'low': 0.15,
            'medium': 0.25,
            'high': 0.35
        }
        
    def detect_regime(self, 
                     price_data: pd.Series,
                     volume_data: Optional[pd.Series] = None) -> MarketRegime:
        """
        Detect current market regime using multiple indicators.
        
        Args:
            price_data: Price time series
            volume_data: Volume time series (optional)
            
        Returns:
            Current market regime
        """
        # Calculate returns
        returns = price_data.pct_change().dropna()
        
        # 1. Trend-based regime detection
        trend_regime = self._detect_trend_regime(returns)
        
        # 2. Volatility-based regime detection
        volatility_regime = self._detect_volatility_regime(returns)
        
        # 3. Volume-based regime detection (if available)
        volume_regime = self._detect_volume_regime(volume_data) if volume_data is not None else 'normal'
        
        # 4. Combine regimes
        combined_regime = self._combine_regimes(trend_regime, volatility_regime, volume_regime)
        
        # 5. Calculate regime metrics
        regime_metrics = self._calculate_regime_metrics(returns, combined_regime)
        
        # Create regime object
        regime = MarketRegime(
            regime_type=combined_regime,
            confidence=regime_metrics['confidence'],
            duration=regime_metrics['duration'],
            volatility_level=regime_metrics['volatility'],
            trend_strength=regime_metrics['trend_strength'],
            regime_score=regime_metrics['regime_score'],
            timestamp=pd.Timestamp.now()
        )
        
        self.regime_history.append(regime)
        return regime
    
    def _detect_trend_regime(self, returns: pd.Series) -> str:
        """Detect trend-based regime."""
        # Calculate trend indicators
        sma_20 = returns.rolling(20).mean()
        sma_50 = returns.rolling(50).mean()
        sma_200 = returns.rolling(200).mean()
        
        # Current trend
        current_trend = sma_20.iloc[-1] if not pd.isna(sma_20.iloc[-1]) else 0
        
        # Trend strength
        trend_strength = abs(current_trend) / returns.std()
        
        # Determine regime
        if trend_strength > 0.5:
            if current_trend > 0:
                return 'bull'
            else:
                return 'bear'
        else:
            return 'sideways'
    
    def _detect_volatility_regime(self, returns: pd.Series) -> str:
        """Detect volatility-based regime."""
        # Calculate rolling volatility
        rolling_vol = returns.rolling(20).std() * np.sqrt(252)
        current_vol = rolling_vol.iloc[-1] if not pd.isna(rolling_vol.iloc[-1]) else 0.2
        
        # Volatility regime
        if current_vol < self.volatility_regime_thresholds['low']:
            return 'calm'
        elif current_vol > self.volatility_regime_thresholds['high']:
            return 'volatile'
        else:
            return 'normal'
    
    def _detect_volume_regime(self, volume_data: pd.Series) -> str:
        """Detect volume-based regime."""
        # Calculate volume indicators
        avg_volume = volume_data.rolling(20).mean()
        current_volume = volume_data.iloc[-1]
        volume_ratio = current_volume / avg_volume.iloc[-1] if not pd.isna(avg_volume.iloc[-1]) else 1.0
        
        if volume_ratio > 1.5:
            return 'high_volume'
        elif volume_ratio < 0.5:
            return 'low_volume'
        else:
            return 'normal'
    
    def _combine_regimes(self, trend: str, volatility: str, volume: str) -> str:
        """Combine different regime indicators."""
        # Priority: volatility > trend > volume
        if volatility in ['volatile', 'calm']:
            return volatility
        elif trend in ['bull', 'bear']:
            return trend
        else:
            return 'sideways'
    
    def _calculate_regime_metrics(self, returns: pd.Series, regime: str) -> Dict[str, float]:
        """Calculate regime-specific metrics."""
        # Volatility
        volatility = returns.rolling(20).std().iloc[-1] * np.sqrt(252)
        
        # Trend strength
        trend_strength = abs(returns.rolling(20).mean().iloc[-1]) / returns.std()
        
        # Regime confidence (based on consistency)
        confidence = self._calculate_regime_confidence(regime)
        
        # Duration
        duration = self._calculate_regime_duration(regime)
        
        # Regime score
        regime_score = self._calculate_regime_score(regime, volatility, trend_strength)
        
        return {
            'volatility': volatility,
            'trend_strength': trend_strength,
            'confidence': confidence,
            'duration': duration,
            'regime_score': regime_score
        }
    
    def _calculate_regime_confidence(self, regime: str) -> float:
        """Calculate regime confidence based on historical consistency."""
        if len(self.regime_history) < 5:
            return 0.5
        
        recent_regimes = [r.regime_type for r in self.regime_history[-5:]]
        regime_consistency = recent_regimes.count(regime) / len(recent_regimes)
        
        return regime_consistency
    
    def _calculate_regime_duration(self, regime: str) -> int:
        """Calculate current regime duration."""
        if not self.regime_history:
            return 1
        
        duration = 1
        for i in range(len(self.regime_history) - 2, -1, -1):
            if self.regime_history[i].regime_type == regime:
                duration += 1
            else:
                break
        
        return duration
    
    def _calculate_regime_score(self, regime: str, volatility: float, trend_strength: float) -> float:
        """Calculate regime score."""
        base_score = 0.5
        
        # Volatility adjustment
        if regime == 'volatile':
            vol_score = min(volatility / 0.3, 1.0)
        elif regime == 'calm':
            vol_score = max(1.0 - volatility / 0.15, 0.0)
        else:
            vol_score = 0.5
        
        # Trend adjustment
        if regime in ['bull', 'bear']:
            trend_score = min(trend_strength, 1.0)
        else:
            trend_score = 0.5
        
        return (base_score + vol_score + trend_score) / 3

class VolatilityClusterDetector:
    """
    Volatility clustering detection using GARCH and regime-switching models.
    """
    
    def __init__(self, window_size: int = 60):
        self.window_size = window_size
        self.volatility_regimes = []
        self.garch_parameters = {}
        
    def detect_volatility_clustering(self, returns: pd.Series) -> Dict[str, Any]:
        """
        Detect volatility clustering patterns.
        
        Args:
            returns: Return time series
            
        Returns:
            Volatility clustering analysis
        """
        # 1. Calculate volatility measures
        rolling_vol = returns.rolling(20).std()
        realized_vol = np.sqrt(np.sum(returns.rolling(5) ** 2))
        
        # 2. Detect volatility persistence
        vol_persistence = self._calculate_volatility_persistence(returns)
        
        # 3. Detect volatility regime changes
        regime_changes = self._detect_volatility_regime_changes(rolling_vol)
        
        # 4. Calculate GARCH-like parameters
        garch_params = self._estimate_garch_parameters(returns)
        
        # 5. Forecast volatility
        vol_forecast = self._forecast_volatility(returns, garch_params)
        
        return {
            'current_volatility': rolling_vol.iloc[-1],
            'volatility_persistence': vol_persistence,
            'regime_changes': regime_changes,
            'garch_parameters': garch_params,
            'volatility_forecast': vol_forecast,
            'clustering_strength': self._calculate_clustering_strength(returns)
        }
    
    def _calculate_volatility_persistence(self, returns: pd.Series) -> float:
        """Calculate volatility persistence using autocorrelation."""
        # Calculate squared returns
        squared_returns = returns ** 2
        
        # Calculate autocorrelation at lag 1
        if len(squared_returns) > 1:
            autocorr = squared_returns.autocorr(lag=1)
            return abs(autocorr) if not pd.isna(autocorr) else 0.0
        else:
            return 0.0
    
    def _detect_volatility_regime_changes(self, volatility: pd.Series) -> List[int]:
        """Detect volatility regime change points."""
        # Use change point detection
        change_points = []
        
        # Simple threshold-based detection
        vol_mean = volatility.rolling(60).mean()
        vol_std = volatility.rolling(60).std()
        
        for i in range(60, len(volatility)):
            if abs(volatility.iloc[i] - vol_mean.iloc[i]) > 2 * vol_std.iloc[i]:
                change_points.append(i)
        
        return change_points
    
    def _estimate_garch_parameters(self, returns: pd.Series) -> Dict[str, float]:
        """Estimate GARCH-like parameters."""
        # Simplified GARCH parameter estimation
        squared_returns = returns ** 2
        mean_squared = squared_returns.mean()
        
        # Estimate persistence parameter (alpha + beta)
        if len(squared_returns) > 1:
            autocorr = squared_returns.autocorr(lag=1)
            persistence = abs(autocorr) if not pd.isna(autocorr) else 0.1
        else:
            persistence = 0.1
        
        # Estimate parameters
        alpha = persistence * 0.3  # ARCH parameter
        beta = persistence * 0.7   # GARCH parameter
        omega = mean_squared * (1 - persistence)  # Constant
        
        return {
            'omega': omega,
            'alpha': alpha,
            'beta': beta,
            'persistence': persistence
        }
    
    def _forecast_volatility(self, returns: pd.Series, garch_params: Dict[str, float]) -> float:
        """Forecast volatility using GARCH parameters."""
        # Current volatility
        current_vol = returns.rolling(20).std().iloc[-1]
        
        # GARCH forecast
        omega = garch_params['omega']
        alpha = garch_params['alpha']
        beta = garch_params['beta']
        
        # Simplified forecast
        forecast_vol = np.sqrt(omega + alpha * returns.iloc[-1]**2 + beta * current_vol**2)
        
        return forecast_vol
    
    def _calculate_clustering_strength(self, returns: pd.Series) -> float:
        """Calculate volatility clustering strength."""
        # Use Ljung-Box test for autocorrelation
        squared_returns = returns ** 2
        
        if len(squared_returns) > 10:
            # Calculate autocorrelations
            autocorrs = []
            for lag in range(1, 6):
                autocorr = squared_returns.autocorr(lag=lag)
                if not pd.isna(autocorr):
                    autocorrs.append(autocorr)
            
            if autocorrs:
                # Clustering strength based on average autocorrelation
                clustering_strength = np.mean([abs(ac) for ac in autocorrs])
                return min(clustering_strength, 1.0)
        
        return 0.0

class MLSignalEnhancer:
    """
    Machine learning signal enhancement using ensemble methods.
    """
    
    def __init__(self, feature_window: int = 60):
        self.feature_window = feature_window
        self.classifier = RandomForestClassifier(n_estimators=100, random_state=42)
        self.regressor = GradientBoostingRegressor(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_importance = {}
        self.indicators = TechnicalIndicators()
        
    def extract_features(self, price_data: pd.Series, volume_data: Optional[pd.Series] = None) -> pd.DataFrame:
        """
        Extract comprehensive features for ML models.
        
        Args:
            price_data: Price time series
            volume_data: Volume time series (optional)
            
        Returns:
            Feature DataFrame
        """
        features = pd.DataFrame(index=price_data.index)
        
        # Price-based features
        returns = price_data.pct_change()
        features['returns'] = returns
        features['log_returns'] = np.log(price_data / price_data.shift(1))
        
        # Technical indicators using pure Pandas/Numpy
        features['sma_20'] = self.indicators.sma(price_data, 20)
        features['sma_50'] = self.indicators.sma(price_data, 50)
        features['ema_12'] = self.indicators.ema(price_data, 12)
        features['ema_26'] = self.indicators.ema(price_data, 26)
        
        # Momentum indicators
        features['rsi'] = self.indicators.rsi(price_data)
        macd_line, macd_signal, macd_hist = self.indicators.macd(price_data)
        features['macd'] = macd_line
        features['macd_signal'] = macd_signal
        features['macd_histogram'] = macd_hist
        
        # Volatility indicators
        bb_upper, bb_middle, bb_lower = self.indicators.bollinger_bands(price_data)
        features['bb_upper'] = bb_upper
        features['bb_middle'] = bb_middle
        features['bb_lower'] = bb_lower
        features['bb_width'] = (bb_upper - bb_lower) / bb_middle
        features['bb_position'] = (price_data - bb_lower) / (bb_upper - bb_lower)
        
        # Stochastic oscillator
        k_percent, d_percent = self.indicators.stochastic(price_data)
        features['stoch_k'] = k_percent
        features['stoch_d'] = d_percent
        
        # Williams %R
        features['williams_r'] = self.indicators.williams_r(price_data)
        
        # Volume features (if available)
        if volume_data is not None:
            features['volume'] = volume_data
            features['volume_sma'] = volume_data.rolling(20).mean()
            features['volume_ratio'] = volume_data / features['volume_sma']
            features['price_volume_corr'] = self._rolling_correlation(returns, volume_data.pct_change(), 20)
        
        # Statistical features
        features['returns_skew'] = returns.rolling(20).skew()
        features['returns_kurtosis'] = returns.rolling(20).kurt()
        features['volatility'] = returns.rolling(20).std()
        features['volatility_of_volatility'] = features['volatility'].rolling(20).std()
        
        # Lagged features
        for lag in [1, 2, 3, 5, 10]:
            features[f'returns_lag_{lag}'] = returns.shift(lag)
            if volume_data is not None:
                features[f'volume_lag_{lag}'] = volume_data.shift(lag)
        
        return features.dropna()
    
    def train_models(self, features: pd.DataFrame, targets: pd.Series, target_type: str = 'classification'):
        """
        Train ML models on historical data.
        
        Args:
            features: Feature DataFrame
            targets: Target series
            target_type: 'classification' or 'regression'
        """
        # Prepare data
        X = features.dropna()
        y = targets.loc[X.index]
        
        if len(X) < 100:
            logger.warning("Insufficient data for training")
            return
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train models
        if target_type == 'classification':
            self.classifier.fit(X_scaled, y)
            self.is_trained = True
            self.feature_importance = dict(zip(X.columns, self.classifier.feature_importances_))
        else:
            self.regressor.fit(X_scaled, y)
            self.is_trained = True
            self.feature_importance = dict(zip(X.columns, self.regressor.feature_importances_))
        
        logger.info(f"Trained {target_type} model with {len(X)} samples")
    
    def predict_signal(self, features: pd.DataFrame) -> Dict[str, float]:
        """
        Predict enhanced signal using trained models.
        
        Args:
            features: Current feature values
            
        Returns:
            Enhanced signal predictions
        """
        if not self.is_trained:
            return {'ml_signal': 0.0, 'confidence': 0.0}
        
        # Prepare features
        X = features.iloc[-1:].values
        X_scaled = self.scaler.transform(X)
        
        # Get predictions
        if hasattr(self.classifier, 'predict_proba'):
            class_proba = self.classifier.predict_proba(X_scaled)[0]
            ml_signal = class_proba[1] - class_proba[0]  # Probability difference
            confidence = max(class_proba)
        else:
            ml_signal = self.regressor.predict(X_scaled)[0]
            confidence = 0.5  # Default confidence for regression
        
        return {
            'ml_signal': ml_signal,
            'confidence': confidence,
            'feature_importance': self.feature_importance
        }
    
    def _rolling_correlation(self, series1: pd.Series, series2: pd.Series, window: int) -> pd.Series:
        """Calculate rolling correlation."""
        return series1.rolling(window).corr(series2)

class AlternativeDataIntegrator:
    """
    Alternative data integration for signal enhancement.
    """
    
    def __init__(self):
        self.sentiment_data = {}
        self.macro_data = {}
        self.flow_data = {}
        
    def integrate_sentiment_data(self, sentiment_scores: Dict[str, float]) -> Dict[str, float]:
        """
        Integrate sentiment data into signals.
        
        Args:
            sentiment_scores: Sentiment scores for symbols
            
        Returns:
            Sentiment-adjusted signals
        """
        sentiment_signals = {}
        
        for symbol, score in sentiment_scores.items():
            # Normalize sentiment score to [-1, 1]
            normalized_score = 2 * (score - 0.5) if score is not None else 0.0
            
            # Apply sentiment adjustment
            sentiment_signals[symbol] = {
                'sentiment_score': normalized_score,
                'sentiment_weight': 0.3,  # 30% weight to sentiment
                'adjusted_signal': normalized_score * 0.3
            }
        
        return sentiment_signals
    
    def integrate_macro_data(self, macro_indicators: Dict[str, float]) -> Dict[str, float]:
        """
        Integrate macroeconomic data into signals.
        
        Args:
            macro_indicators: Macroeconomic indicators
            
        Returns:
            Macro-adjusted signals
        """
        macro_signals = {}
        
        # VIX adjustment
        if 'vix' in macro_indicators:
            vix = macro_indicators['vix']
            vix_signal = -0.5 if vix > 30 else 0.0 if vix > 20 else 0.3
            macro_signals['vix_signal'] = vix_signal
        
        # Interest rate adjustment
        if 'interest_rate' in macro_indicators:
            rate = macro_indicators['interest_rate']
            rate_signal = -0.2 if rate > 0.05 else 0.1
            macro_signals['rate_signal'] = rate_signal
        
        # Currency adjustment
        if 'dollar_index' in macro_indicators:
            dollar = macro_indicators['dollar_index']
            dollar_signal = -0.3 if dollar > 100 else 0.2
            macro_signals['dollar_signal'] = dollar_signal
        
        return macro_signals
    
    def integrate_flow_data(self, flow_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Integrate flow data (institutional flows, options flow) into signals.
        
        Args:
            flow_data: Flow data dictionary
            
        Returns:
            Flow-adjusted signals
        """
        flow_signals = {}
        
        # Institutional flow
        if 'institutional_flow' in flow_data:
            inst_flow = flow_data['institutional_flow']
            flow_signals['institutional_signal'] = np.tanh(inst_flow / 1e6)  # Normalize large flows
        
        # Options flow
        if 'options_flow' in flow_data:
            options_flow = flow_data['options_flow']
            flow_signals['options_signal'] = np.tanh(options_flow / 1e5)
        
        # ETF flows
        if 'etf_flow' in flow_data:
            etf_flow = flow_data['etf_flow']
            flow_signals['etf_signal'] = np.tanh(etf_flow / 1e6)
        
        return flow_signals

class AdvancedSignalGenerator:
    """
    Main advanced signal generator combining all components.
    """
    
    def __init__(self):
        self.regime_detector = RegimeDetector()
        self.volatility_detector = VolatilityClusterDetector()
        self.ml_enhancer = MLSignalEnhancer()
        self.alt_data_integrator = AlternativeDataIntegrator()
        
    def generate_advanced_signals(self,
                                 price_data: pd.Series,
                                 volume_data: Optional[pd.Series] = None,
                                 sentiment_data: Optional[Dict[str, float]] = None,
                                 macro_data: Optional[Dict[str, float]] = None,
                                 flow_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate comprehensive advanced signals.
        
        Args:
            price_data: Price time series
            volume_data: Volume time series
            sentiment_data: Sentiment data
            macro_data: Macroeconomic data
            flow_data: Flow data
            
        Returns:
            Advanced signal analysis
        """
        # 1. Regime detection
        regime = self.regime_detector.detect_regime(price_data, volume_data)
        
        # 2. Volatility clustering
        volatility_analysis = self.volatility_detector.detect_volatility_clustering(price_data.pct_change())
        
        # 3. ML signal enhancement
        features = self.ml_enhancer.extract_features(price_data, volume_data)
        ml_signals = self.ml_enhancer.predict_signal(features)
        
        # 4. Alternative data integration
        alt_signals = {}
        if sentiment_data:
            alt_signals['sentiment'] = self.alt_data_integrator.integrate_sentiment_data(sentiment_data)
        if macro_data:
            alt_signals['macro'] = self.alt_data_integrator.integrate_macro_data(macro_data)
        if flow_data:
            alt_signals['flow'] = self.alt_data_integrator.integrate_flow_data(flow_data)
        
        # 5. Combine signals
        combined_signal = self._combine_signals(regime, volatility_analysis, ml_signals, alt_signals)
        
        return {
            'regime': regime,
            'volatility_analysis': volatility_analysis,
            'ml_signals': ml_signals,
            'alternative_signals': alt_signals,
            'combined_signal': combined_signal,
            'signal_confidence': self._calculate_signal_confidence(regime, ml_signals, alt_signals)
        }
    
    def _combine_signals(self,
                        regime: MarketRegime,
                        volatility_analysis: Dict[str, Any],
                        ml_signals: Dict[str, float],
                        alt_signals: Dict[str, Any]) -> float:
        """Combine all signals into final signal."""
        # Base signal from regime
        regime_signal = self._regime_to_signal(regime.regime_type)
        
        # Volatility adjustment
        vol_adjustment = self._volatility_adjustment(volatility_analysis)
        
        # ML signal
        ml_signal = ml_signals.get('ml_signal', 0.0)
        
        # Alternative data signals
        alt_signal = self._combine_alternative_signals(alt_signals)
        
        # Weighted combination
        weights = {
            'regime': 0.3,
            'volatility': 0.2,
            'ml': 0.3,
            'alternative': 0.2
        }
        
        combined = (regime_signal * weights['regime'] +
                   vol_adjustment * weights['volatility'] +
                   ml_signal * weights['ml'] +
                   alt_signal * weights['alternative'])
        
        return np.clip(combined, -1.0, 1.0)
    
    def _regime_to_signal(self, regime_type: str) -> float:
        """Convert regime type to signal value."""
        regime_signals = {
            'bull': 0.8,
            'bear': -0.8,
            'sideways': 0.0,
            'volatile': 0.2,
            'calm': -0.1
        }
        return regime_signals.get(regime_type, 0.0)
    
    def _volatility_adjustment(self, volatility_analysis: Dict[str, Any]) -> float:
        """Calculate volatility-based signal adjustment."""
        current_vol = volatility_analysis.get('current_volatility', 0.2)
        clustering_strength = volatility_analysis.get('clustering_strength', 0.0)
        
        # High volatility with clustering suggests trend continuation
        if current_vol > 0.3 and clustering_strength > 0.5:
            return 0.3
        elif current_vol < 0.15:
            return -0.2
        else:
            return 0.0
    
    def _combine_alternative_signals(self, alt_signals: Dict[str, Any]) -> float:
        """Combine alternative data signals."""
        combined = 0.0
        count = 0
        
        for signal_type, signals in alt_signals.items():
            if isinstance(signals, dict):
                for key, value in signals.items():
                    if isinstance(value, dict) and 'adjusted_signal' in value:
                        combined += value['adjusted_signal']
                        count += 1
                    elif isinstance(value, (int, float)):
                        combined += value
                        count += 1
        
        return combined / count if count > 0 else 0.0
    
    def _calculate_signal_confidence(self,
                                   regime: MarketRegime,
                                   ml_signals: Dict[str, float],
                                   alt_signals: Dict[str, Any]) -> float:
        """Calculate overall signal confidence."""
        # Regime confidence
        regime_confidence = regime.confidence
        
        # ML confidence
        ml_confidence = ml_signals.get('confidence', 0.5)
        
        # Alternative data confidence (simplified)
        alt_confidence = 0.7 if alt_signals else 0.5
        
        # Weighted average
        confidence = (regime_confidence * 0.4 + 
                     ml_confidence * 0.4 + 
                     alt_confidence * 0.2)
        
        return confidence 