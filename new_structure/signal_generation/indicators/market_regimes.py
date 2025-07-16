"""
Market Regime Detection and Classification System
================================================

Advanced market regime detection using technical indicators,
volatility analysis, and machine learning techniques.
Preserves our proven regime detection while enabling integration.

Author: Pro Trading System
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Union
from sklearn.cluster import KMeans
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
from scipy import stats
from scipy.signal import find_peaks
import warnings
warnings.filterwarnings('ignore')

class MarketRegimeDetector:
    """
    Comprehensive market regime detection system
    Identifies trending, ranging, volatile, and calm market periods
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize regime detector"""
        self.config = config or {}
        
        # Regime detection parameters
        self.volatility_lookback = self.config.get('volatility_lookback', 20)
        self.trend_lookback = self.config.get('trend_lookback', 50)
        self.regime_smoothing = self.config.get('regime_smoothing', 5)
        
        # Thresholds
        self.high_volatility_threshold = self.config.get('high_volatility_threshold', 0.75)
        self.low_volatility_threshold = self.config.get('low_volatility_threshold', 0.25)
        self.strong_trend_threshold = self.config.get('strong_trend_threshold', 0.7)
        self.weak_trend_threshold = self.config.get('weak_trend_threshold', 0.3)
        
        # Model components
        self.scaler = StandardScaler()
        self.kmeans_model = None
        self.gmm_model = None
        
        # Regime history
        self.regime_history = {}
        self.regime_stats = {}
    
    def detect_regimes(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect market regimes using multiple approaches
        
        Args:
            df: DataFrame with OHLCV data and technical indicators
            
        Returns:
            DataFrame with regime classifications
        """
        regime_df = df.copy()
        
        print("🔍 Detecting market regimes...")
        
        # Basic regime indicators
        regime_df = self._calculate_regime_indicators(regime_df)
        
        # Rule-based regime detection
        regime_df = self._rule_based_regimes(regime_df)
        
        # Statistical regime detection
        regime_df = self._statistical_regimes(regime_df)
        
        # Machine learning regime detection
        regime_df = self._ml_based_regimes(regime_df)
        
        # Ensemble regime classification
        regime_df = self._ensemble_regime_classification(regime_df)
        
        # Regime transition analysis
        regime_df = self._analyze_regime_transitions(regime_df)
        
        # Regime persistence and quality metrics
        regime_df = self._calculate_regime_metrics(regime_df)
        
        print(f"✅ Market regime detection complete")
        
        return regime_df
    
    def _calculate_regime_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate indicators for regime detection"""
        
        # Volatility measures
        returns = df['close'].pct_change()
        df['realized_volatility'] = returns.rolling(self.volatility_lookback).std() * np.sqrt(252)
        df['volatility_percentile'] = df['realized_volatility'].rolling(252).rank(pct=True)
        
        # Trend strength measures
        for period in [10, 20, 50]:
            # Linear regression trend strength
            def calc_trend_strength(series):
                if len(series) < period:
                    return np.nan
                x = np.arange(len(series))
                try:
                    slope, _, r_value, _, _ = stats.linregress(x, series.values)
                    return slope * (r_value ** 2)  # Slope weighted by R-squared
                except:
                    return np.nan
            
            df[f'trend_strength_{period}'] = df['close'].rolling(period).apply(calc_trend_strength)
        
        # Moving average relationships
        if all(col in df.columns for col in ['sma_20', 'sma_50']):
            df['ma_slope_20'] = df['sma_20'].pct_change(5)
            df['ma_slope_50'] = df['sma_50'].pct_change(10)
            df['ma_separation'] = (df['sma_20'] - df['sma_50']) / df['sma_50']
            df['price_ma_distance'] = (df['close'] - df['sma_20']) / df['sma_20']
        
        # ADX-like directional movement
        if all(col in df.columns for col in ['high', 'low']):
            high_diff = df['high'].diff()
            low_diff = df['low'].diff()
            
            plus_dm = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0)
            minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0)
            
            # True Range for normalization
            tr1 = df['high'] - df['low']
            tr2 = abs(df['high'] - df['close'].shift(1))
            tr3 = abs(df['low'] - df['close'].shift(1))
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            plus_di = 100 * (pd.Series(plus_dm).rolling(14).sum() / true_range.rolling(14).sum())
            minus_di = 100 * (pd.Series(minus_dm).rolling(14).sum() / true_range.rolling(14).sum())
            
            df['plus_di'] = plus_di
            df['minus_di'] = minus_di
            df['dx'] = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
            df['adx'] = df['dx'].rolling(14).mean()
        
        # Volume-based regime indicators
        if 'volume' in df.columns:
            df['volume_volatility'] = df['volume'].rolling(20).std() / df['volume'].rolling(20).mean()
            df['volume_trend'] = df['volume'].rolling(20).apply(
                lambda x: stats.linregress(range(len(x)), x)[0] if len(x) == 20 else np.nan
            )
        
        # Price action patterns
        df['higher_highs'] = (df['high'] > df['high'].shift(1)).rolling(10).sum()
        df['lower_lows'] = (df['low'] < df['low'].shift(1)).rolling(10).sum()
        df['price_compression'] = (df['high'].rolling(20).max() - df['low'].rolling(20).min()) / df['close']
        
        return df
    
    def _rule_based_regimes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply rule-based regime classification"""
        
        # Initialize regime classifications
        df['volatility_regime'] = 'medium'
        df['trend_regime'] = 'sideways'
        df['volume_regime'] = 'normal'
        
        # Volatility regimes
        df.loc[df['volatility_percentile'] > self.high_volatility_threshold, 'volatility_regime'] = 'high'
        df.loc[df['volatility_percentile'] < self.low_volatility_threshold, 'volatility_regime'] = 'low'
        
        # Trend regimes
        if 'trend_strength_20' in df.columns:
            trend_percentile = df['trend_strength_20'].rolling(100).rank(pct=True)
            df.loc[trend_percentile > self.strong_trend_threshold, 'trend_regime'] = 'trending'
            df.loc[trend_percentile < self.weak_trend_threshold, 'trend_regime'] = 'ranging'
            
            # Direction within trending
            df.loc[(df['trend_regime'] == 'trending') & (df['trend_strength_20'] > 0), 'trend_regime'] = 'uptrend'
            df.loc[(df['trend_regime'] == 'trending') & (df['trend_strength_20'] < 0), 'trend_regime'] = 'downtrend'
        
        # ADX-based trend classification
        if 'adx' in df.columns:
            df.loc[df['adx'] > 25, 'adx_regime'] = 'trending'
            df.loc[df['adx'] < 20, 'adx_regime'] = 'ranging'
            df.loc[(df['adx'] >= 20) & (df['adx'] <= 25), 'adx_regime'] = 'transitional'
        
        # Volume regimes
        if 'volume_volatility' in df.columns:
            volume_percentile = df['volume_volatility'].rolling(60).rank(pct=True)
            df.loc[volume_percentile > 0.8, 'volume_regime'] = 'high'
            df.loc[volume_percentile < 0.2, 'volume_regime'] = 'low'
        
        # Combined rule-based regime
        df['rule_based_regime'] = (
            df['volatility_regime'] + '_' + 
            df['trend_regime'] + '_' + 
            df['volume_regime']
        )
        
        return df
    
    def _statistical_regimes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Statistical regime detection using change point analysis"""
        
        # Variance change points
        returns = df['close'].pct_change().dropna()
        if len(returns) > 50:
            # Rolling variance
            rolling_var = returns.rolling(20).var()
            
            # Change point detection using CUSUM
            cumsum = np.cumsum(rolling_var - rolling_var.mean())
            df['variance_cusum'] = np.nan
            df.loc[rolling_var.index, 'variance_cusum'] = cumsum
            
            # Detect change points
            change_points = find_peaks(np.abs(cumsum), height=np.std(cumsum) * 2)[0]
            df['variance_change_point'] = 0
            if len(change_points) > 0:
                df.iloc[change_points]['variance_change_point'] = 1
        
        # Mean reversion vs momentum regimes
        # Calculate autocorrelation to detect regime
        def rolling_autocorr(series, lag=1, window=50):
            return series.rolling(window).apply(
                lambda x: x.autocorr(lag=lag) if len(x) > lag else np.nan
            )
        
        df['autocorr_1'] = rolling_autocorr(returns, lag=1)
        df['autocorr_5'] = rolling_autocorr(returns, lag=5)
        
        # Classify based on autocorrelation
        df['mean_reversion_regime'] = 'neutral'
        df.loc[df['autocorr_1'] < -0.1, 'mean_reversion_regime'] = 'mean_reverting'
        df.loc[df['autocorr_1'] > 0.1, 'mean_reversion_regime'] = 'momentum'
        
        # Hurst exponent for trend persistence
        def hurst_exponent(series, max_lag=20):
            """Calculate Hurst exponent"""
            if len(series) < max_lag * 2:
                return np.nan
            
            lags = range(2, max_lag)
            tau = [np.sqrt(np.std(np.subtract(series[lag:], series[:-lag]))) for lag in lags]
            
            # Linear fit to log-log plot
            try:
                poly = np.polyfit(np.log(lags), np.log(tau), 1)
                return poly[0]
            except:
                return np.nan
        
        df['hurst_exponent'] = df['close'].rolling(100).apply(hurst_exponent)
        
        # Classify based on Hurst exponent
        df['hurst_regime'] = 'neutral'
        df.loc[df['hurst_exponent'] > 0.6, 'hurst_regime'] = 'trending'
        df.loc[df['hurst_exponent'] < 0.4, 'hurst_regime'] = 'mean_reverting'
        
        return df
    
    def _ml_based_regimes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Machine learning based regime detection"""
        
        # Prepare features for clustering
        feature_columns = [
            'realized_volatility', 'trend_strength_20', 'ma_separation',
            'price_ma_distance', 'adx', 'volume_volatility'
        ]
        
        # Filter available features
        available_features = [col for col in feature_columns if col in df.columns]
        
        if len(available_features) >= 3:
            # Prepare data
            features = df[available_features].fillna(0)
            
            # Standardize features
            features_scaled = self.scaler.fit_transform(features)
            
            # K-means clustering
            self.kmeans_model = KMeans(n_clusters=4, random_state=42, n_init=10)
            df['kmeans_regime'] = self.kmeans_model.fit_predict(features_scaled)
            
            # Gaussian Mixture Model
            self.gmm_model = GaussianMixture(n_components=4, random_state=42)
            df['gmm_regime'] = self.gmm_model.fit_predict(features_scaled)
            df['gmm_probability'] = self.gmm_model.predict_proba(features_scaled).max(axis=1)
            
            # Interpret clusters based on centroids
            cluster_interpretation = self._interpret_clusters(features_scaled)
            
            # Map clusters to meaningful names
            df['kmeans_regime_named'] = df['kmeans_regime'].map(cluster_interpretation['kmeans'])
            df['gmm_regime_named'] = df['gmm_regime'].map(cluster_interpretation['gmm'])
        
        return df
    
    def _interpret_clusters(self, features_scaled: np.ndarray) -> Dict[str, Dict[int, str]]:
        """Interpret cluster meanings based on centroids"""
        interpretations = {'kmeans': {}, 'gmm': {}}
        
        # K-means interpretation
        if self.kmeans_model is not None:
            centroids = self.kmeans_model.cluster_centers_
            
            for i, centroid in enumerate(centroids):
                # Interpret based on feature values
                volatility = centroid[0]  # realized_volatility
                trend = centroid[1] if len(centroid) > 1 else 0  # trend_strength
                
                if volatility > 0.5 and abs(trend) > 0.5:
                    regime_name = 'volatile_trending'
                elif volatility > 0.5 and abs(trend) <= 0.5:
                    regime_name = 'volatile_ranging'
                elif volatility <= 0.5 and abs(trend) > 0.5:
                    regime_name = 'calm_trending'
                else:
                    regime_name = 'calm_ranging'
                
                interpretations['kmeans'][i] = regime_name
        
        # GMM interpretation (similar logic)
        if self.gmm_model is not None:
            means = self.gmm_model.means_
            
            for i, mean in enumerate(means):
                volatility = mean[0]
                trend = mean[1] if len(mean) > 1 else 0
                
                if volatility > 0.5 and abs(trend) > 0.5:
                    regime_name = 'volatile_trending'
                elif volatility > 0.5 and abs(trend) <= 0.5:
                    regime_name = 'volatile_ranging'
                elif volatility <= 0.5 and abs(trend) > 0.5:
                    regime_name = 'calm_trending'
                else:
                    regime_name = 'calm_ranging'
                
                interpretations['gmm'][i] = regime_name
        
        return interpretations
    
    def _ensemble_regime_classification(self, df: pd.DataFrame) -> pd.DataFrame:
        """Combine multiple regime detection methods"""
        
        # Weight different approaches
        regime_scores = pd.DataFrame(index=df.index)
        
        # Rule-based contribution
        if 'volatility_regime' in df.columns and 'trend_regime' in df.columns:
            regime_scores['volatility_score'] = df['volatility_regime'].map({
                'low': -1, 'medium': 0, 'high': 1
            })
            regime_scores['trend_score'] = df['trend_regime'].map({
                'ranging': -1, 'sideways': 0, 'uptrend': 1, 'downtrend': -1, 'trending': 0.5
            })
        
        # Statistical contribution
        if 'hurst_exponent' in df.columns:
            regime_scores['persistence_score'] = (df['hurst_exponent'] - 0.5) * 2
        
        # ML contribution
        if 'gmm_probability' in df.columns:
            regime_scores['confidence_score'] = df['gmm_probability']
        
        # Calculate composite scores
        df['volatility_composite'] = regime_scores['volatility_score'].fillna(0)
        df['trend_composite'] = regime_scores['trend_score'].fillna(0)
        df['persistence_composite'] = regime_scores['persistence_score'].fillna(0)
        
        # Final ensemble regime
        conditions = [
            (df['volatility_composite'] > 0.5) & (abs(df['trend_composite']) > 0.5),
            (df['volatility_composite'] > 0.5) & (abs(df['trend_composite']) <= 0.5),
            (df['volatility_composite'] <= 0.5) & (abs(df['trend_composite']) > 0.5),
            (df['volatility_composite'] <= 0.5) & (abs(df['trend_composite']) <= 0.5)
        ]
        
        choices = [
            'volatile_trending',
            'volatile_ranging', 
            'calm_trending',
            'calm_ranging'
        ]
        
        df['ensemble_regime'] = np.select(conditions, choices, default='unknown')
        
        # Add trend direction
        df.loc[(df['ensemble_regime'].str.contains('trending')) & (df['trend_composite'] > 0), 
               'ensemble_regime'] = df['ensemble_regime'] + '_up'
        df.loc[(df['ensemble_regime'].str.contains('trending')) & (df['trend_composite'] < 0), 
               'ensemble_regime'] = df['ensemble_regime'] + '_down'
        
        return df
    
    def _analyze_regime_transitions(self, df: pd.DataFrame) -> pd.DataFrame:
        """Analyze regime transitions and persistence"""
        
        if 'ensemble_regime' in df.columns:
            # Regime changes
            df['regime_change'] = (df['ensemble_regime'] != df['ensemble_regime'].shift(1)).astype(int)
            
            # Regime persistence
            regime_groups = (df['ensemble_regime'] != df['ensemble_regime'].shift(1)).cumsum()
            df['regime_persistence'] = regime_groups.groupby(regime_groups).cumcount() + 1
            
            # Time since regime change
            df['days_in_regime'] = df.groupby('ensemble_regime').cumcount() + 1
            
            # Regime transition probabilities
            transition_matrix = self._calculate_transition_matrix(df['ensemble_regime'])
            df['transition_probability'] = self._get_transition_probabilities(
                df['ensemble_regime'], transition_matrix
            )
        
        return df
    
    def _calculate_transition_matrix(self, regime_series: pd.Series) -> pd.DataFrame:
        """Calculate regime transition probability matrix"""
        regimes = regime_series.dropna()
        unique_regimes = regimes.unique()
        
        # Initialize transition matrix
        transition_matrix = pd.DataFrame(
            0, index=unique_regimes, columns=unique_regimes
        )
        
        # Count transitions
        for i in range(1, len(regimes)):
            from_regime = regimes.iloc[i-1]
            to_regime = regimes.iloc[i]
            transition_matrix.loc[from_regime, to_regime] += 1
        
        # Normalize to probabilities
        transition_matrix = transition_matrix.div(transition_matrix.sum(axis=1), axis=0).fillna(0)
        
        return transition_matrix
    
    def _get_transition_probabilities(self, regime_series: pd.Series, 
                                    transition_matrix: pd.DataFrame) -> pd.Series:
        """Get transition probabilities for each observation"""
        probabilities = pd.Series(index=regime_series.index, dtype=float)
        
        for i in range(1, len(regime_series)):
            current_regime = regime_series.iloc[i-1]
            next_regime = regime_series.iloc[i]
            
            if current_regime in transition_matrix.index and next_regime in transition_matrix.columns:
                probabilities.iloc[i] = transition_matrix.loc[current_regime, next_regime]
            else:
                probabilities.iloc[i] = 0
        
        return probabilities
    
    def _calculate_regime_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate regime quality and stability metrics"""
        
        if 'ensemble_regime' in df.columns:
            # Regime stability (lower volatility within regime)
            regime_groups = df.groupby('ensemble_regime')
            
            df['regime_stability'] = np.nan
            for regime, group in regime_groups:
                if len(group) > 5:  # Minimum observations
                    stability = 1 / (1 + group['realized_volatility'].std())
                    df.loc[group.index, 'regime_stability'] = stability
            
            # Regime predictive power
            forward_returns = df['close'].pct_change().shift(-1)
            df['regime_predictive_power'] = df.groupby('ensemble_regime')[forward_returns.name].transform(
                lambda x: abs(x.mean()) / (x.std() + 1e-8)
            )
            
            # Regime confidence
            if 'gmm_probability' in df.columns:
                df['regime_confidence'] = df['gmm_probability']
            else:
                df['regime_confidence'] = df['regime_persistence'] / (df['regime_persistence'] + 5)
        
        return df
    
    def get_current_regime(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get current market regime with confidence metrics"""
        if len(df) == 0:
            return {'regime': 'unknown', 'confidence': 0}
        
        latest = df.iloc[-1]
        
        return {
            'regime': latest.get('ensemble_regime', 'unknown'),
            'confidence': latest.get('regime_confidence', 0),
            'volatility_level': latest.get('volatility_regime', 'unknown'),
            'trend_direction': latest.get('trend_regime', 'unknown'),
            'days_in_regime': latest.get('days_in_regime', 0),
            'stability': latest.get('regime_stability', 0)
        }
    
    def get_regime_statistics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get comprehensive regime statistics"""
        if 'ensemble_regime' not in df.columns:
            return {}
        
        regime_stats = {}
        
        # Regime distribution
        regime_counts = df['ensemble_regime'].value_counts()
        regime_stats['distribution'] = regime_counts.to_dict()
        
        # Average regime duration
        regime_groups = (df['ensemble_regime'] != df['ensemble_regime'].shift(1)).cumsum()
        durations = regime_groups.groupby([regime_groups, df['ensemble_regime']]).size()
        avg_durations = durations.groupby(level=1).mean()
        regime_stats['average_duration'] = avg_durations.to_dict()
        
        # Regime performance
        returns = df['close'].pct_change()
        regime_performance = df.groupby('ensemble_regime')[returns.name].agg(['mean', 'std', 'count'])
        regime_stats['performance'] = regime_performance.to_dict('index')
        
        return regime_stats

# Integration functions
def detect_market_regimes(data: pd.DataFrame, config: Optional[Dict] = None) -> pd.DataFrame:
    """
    Main entry point for market regime detection
    
    Args:
        data: DataFrame with OHLCV and technical indicators
        config: Optional configuration dictionary
        
    Returns:
        DataFrame with regime classifications
    """
    detector = MarketRegimeDetector(config)
    regime_data = detector.detect_regimes(data)
    
    return regime_data

def get_current_market_regime(data: pd.DataFrame) -> Dict[str, Any]:
    """Get current market regime analysis"""
    detector = MarketRegimeDetector()
    regime_data = detector.detect_regimes(data)
    
    return detector.get_current_regime(regime_data)

# Export for new_structure integration
__all__ = [
    'MarketRegimeDetector',
    'detect_market_regimes',
    'get_current_market_regime'
]
