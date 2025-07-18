"""
Advanced Feature Engineering for Technical Indicators
=====================================================

Comprehensive feature creation pipeline that transforms our
105+ technical indicators into sophisticated trading features.
Preserves our proven feature engineering while enabling integration.

Author: Pro Trading System
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from scipy import stats
from sklearn.preprocessing import StandardScaler, RobustScaler
from scipy.signal import argrelextrema
import warnings
warnings.filterwarnings('ignore')

class FeatureEngineeringPipeline:
    """
    Advanced feature engineering system for technical indicators
    Creates 200+ sophisticated features from our base indicators
    """
    
    def __init__(self, config=None):
        """Initialize feature engineering pipeline"""
        self.config = config or {}
        
        # Feature generation settings
        self.lookback_periods = [5, 10, 20, 50]
        self.momentum_periods = [3, 5, 10, 15, 20]
        self.volatility_windows = [10, 20, 30]
        self.regime_threshold = 0.02
        
        # Scalers for normalization
        self.standard_scaler = StandardScaler()
        self.robust_scaler = RobustScaler()
        
        # Feature importance tracking
        self.feature_importance = {}
        self.feature_stats = {}
    
    def create_all_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create comprehensive feature set from technical indicators
        
        Args:
            df: DataFrame with OHLCV data and basic technical indicators
            
        Returns:
            DataFrame with 200+ engineered features
        """
        features_df = df.copy()
        
        print("🔧 Starting comprehensive feature engineering...")
        
        # Basic price features
        features_df = self._create_price_features(features_df)
        
        # Volume features
        features_df = self._create_volume_features(features_df)
        
        # Momentum features
        features_df = self._create_momentum_features(features_df)
        
        # Volatility features
        features_df = self._create_volatility_features(features_df)
        
        # Trend features
        features_df = self._create_trend_features(features_df)
        
        # Statistical features
        features_df = self._create_statistical_features(features_df)
        
        # Cross-asset features
        features_df = self._create_cross_asset_features(features_df)
        
        # Market regime features
        features_df = self._create_market_regime_features(features_df)
        
        # Time-based features
        features_df = self._create_time_features(features_df)
        
        # Advanced composite features
        features_df = self._create_composite_features(features_df)
        
        # Feature interactions
        features_df = self._create_feature_interactions(features_df)
        
        # Final normalization
        features_df = self._normalize_features(features_df)
        
        print(f"✅ Feature engineering complete: {len(features_df.columns)} features created")
        
        return features_df
    
    def _create_price_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create price-based features"""
        
        # Price position features
        df['price_position_20'] = (df['close'] - df['close'].rolling(20).min()) / (df['close'].rolling(20).max() - df['close'].rolling(20).min())
        df['price_position_50'] = (df['close'] - df['close'].rolling(50).min()) / (df['close'].rolling(50).max() - df['close'].rolling(50).min())
        
        # Price momentum
        for period in [1, 2, 3, 5, 10, 20]:
            df[f'price_momentum_{period}'] = df['close'].pct_change(period)
            df[f'price_acceleration_{period}'] = df[f'price_momentum_{period}'].diff()
        
        # Gap features
        df['gap_size'] = (df['open'] - df['close'].shift(1)) / df['close'].shift(1)
        df['gap_fill'] = np.where(
            (df['gap_size'] > 0) & (df['low'] <= df['close'].shift(1)), 1,
            np.where((df['gap_size'] < 0) & (df['high'] >= df['close'].shift(1)), -1, 0)
        )
        
        # Intraday features
        df['intraday_range'] = (df['high'] - df['low']) / df['close']
        df['intraday_position'] = (df['close'] - df['low']) / (df['high'] - df['low'])
        df['upper_shadow'] = (df['high'] - np.maximum(df['open'], df['close'])) / df['close']
        df['lower_shadow'] = (np.minimum(df['open'], df['close']) - df['low']) / df['close']
        
        # Body features
        df['body_size'] = abs(df['close'] - df['open']) / df['close']
        df['body_direction'] = np.where(df['close'] > df['open'], 1, -1)
        
        return df
    
    def _create_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create volume-based features"""
        
        # Volume momentum
        for period in self.momentum_periods:
            df[f'volume_momentum_{period}'] = df['volume'].pct_change(period)
            df[f'volume_sma_ratio_{period}'] = df['volume'] / df['volume'].rolling(period).mean()
        
        # Price-volume features
        df['volume_price_trend'] = df['volume'] * np.sign(df['close'].diff())
        df['volume_weighted_price'] = (df['volume'] * df['close']).rolling(20).sum() / df['volume'].rolling(20).sum()
        
        # On-Balance Volume momentum
        obv = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()
        df['obv'] = obv
        df['obv_momentum_10'] = obv.pct_change(10)
        df['obv_momentum_20'] = obv.pct_change(20)
        
        # Accumulation/Distribution Line
        ad_line = ((df['close'] - df['low']) - (df['high'] - df['close'])) / (df['high'] - df['low']) * df['volume']
        ad_line = ad_line.fillna(0).cumsum()
        df['ad_line'] = ad_line
        df['ad_momentum_10'] = ad_line.pct_change(10)
        
        # Volume volatility
        df['volume_volatility_10'] = df['volume'].rolling(10).std() / df['volume'].rolling(10).mean()
        df['volume_volatility_20'] = df['volume'].rolling(20).std() / df['volume'].rolling(20).mean()
        
        return df
    
    def _create_momentum_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create momentum-based features"""
        
        # Rate of Change features
        for period in [5, 10, 15, 20, 30]:
            df[f'roc_{period}'] = ((df['close'] - df['close'].shift(period)) / df['close'].shift(period)) * 100
            df[f'roc_ma_{period}'] = df[f'roc_{period}'].rolling(5).mean()
        
        # Momentum oscillators
        if 'rsi_14' in df.columns:
            df['rsi_momentum'] = df['rsi_14'].diff()
            df['rsi_divergence'] = (df['rsi_14'].diff() * df['close'].pct_change()).rolling(10).mean()
            df['rsi_oversold_strength'] = np.where(df['rsi_14'] < 30, 30 - df['rsi_14'], 0)
            df['rsi_overbought_strength'] = np.where(df['rsi_14'] > 70, df['rsi_14'] - 70, 0)
        
        # MACD features
        if all(col in df.columns for col in ['macd_line', 'macd_signal', 'macd_histogram']):
            df['macd_momentum'] = df['macd_line'].diff()
            df['macd_histogram_momentum'] = df['macd_histogram'].diff()
            df['macd_signal_cross'] = np.where(
                (df['macd_line'] > df['macd_signal']) & (df['macd_line'].shift(1) <= df['macd_signal'].shift(1)), 1,
                np.where((df['macd_line'] < df['macd_signal']) & (df['macd_line'].shift(1) >= df['macd_signal'].shift(1)), -1, 0)
            )
        
        # Stochastic features
        if 'close' in df.columns:
            # Calculate Stochastic %K and %D
            lowest_low = df['low'].rolling(14).min()
            highest_high = df['high'].rolling(14).max()
            k_percent = 100 * ((df['close'] - lowest_low) / (highest_high - lowest_low))
            df['stoch_k'] = k_percent
            df['stoch_d'] = k_percent.rolling(3).mean()
            df['stoch_momentum'] = df['stoch_k'].diff()
            df['stoch_divergence'] = (df['stoch_k'].diff() * df['close'].pct_change()).rolling(10).mean()
        
        # Williams %R
        if all(col in df.columns for col in ['high', 'low', 'close']):
            highest_high_14 = df['high'].rolling(14).max()
            lowest_low_14 = df['low'].rolling(14).min()
            df['williams_r'] = -100 * (highest_high_14 - df['close']) / (highest_high_14 - lowest_low_14)
            df['williams_r_momentum'] = df['williams_r'].diff()
        
        return df
    
    def _create_volatility_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create volatility-based features"""
        
        # Rolling volatility
        for window in self.volatility_windows:
            df[f'volatility_{window}'] = df['close'].pct_change().rolling(window).std() * np.sqrt(252)
            df[f'volatility_rank_{window}'] = df[f'volatility_{window}'].rolling(252).rank(pct=True)
        
        # Volatility regime
        vol_20 = df['close'].pct_change().rolling(20).std()
        vol_60 = df['close'].pct_change().rolling(60).std()
        df['vol_regime'] = np.where(vol_20 > vol_60 * 1.5, 1, np.where(vol_20 < vol_60 * 0.5, -1, 0))
        
        # Bollinger Band features
        if all(col in df.columns for col in ['sma_20']):
            bb_std = df['close'].rolling(20).std()
            df['bb_upper'] = df['sma_20'] + (bb_std * 2)
            df['bb_lower'] = df['sma_20'] - (bb_std * 2)
            df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
            df['bb_squeeze'] = (df['bb_upper'] - df['bb_lower']) / df['sma_20']
            df['bb_breakout'] = np.where(
                (df['close'] > df['bb_upper']) & (df['close'].shift(1) <= df['bb_upper'].shift(1)), 1,
                np.where((df['close'] < df['bb_lower']) & (df['close'].shift(1) >= df['bb_lower'].shift(1)), -1, 0)
            )
        
        # Average True Range features
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift(1))
        low_close = abs(df['low'] - df['close'].shift(1))
        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
        
        for period in [7, 14, 21]:
            df[f'atr_{period}'] = true_range.rolling(period).mean()
            df[f'atr_ratio_{period}'] = df[f'atr_{period}'] / df['close']
            df[f'atr_percentile_{period}'] = df[f'atr_{period}'].rolling(252).rank(pct=True)
        
        return df
    
    def _create_trend_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create trend-based features"""
        
        # Moving average trends
        if all(col in df.columns for col in ['sma_20', 'sma_50', 'ema_12', 'ema_26']):
            # SMA relationships
            df['sma_trend_20'] = np.where(df['sma_20'] > df['sma_20'].shift(1), 1, -1)
            df['sma_trend_50'] = np.where(df['sma_50'] > df['sma_50'].shift(1), 1, -1)
            df['sma_cross'] = np.where(
                (df['sma_20'] > df['sma_50']) & (df['sma_20'].shift(1) <= df['sma_50'].shift(1)), 1,
                np.where((df['sma_20'] < df['sma_50']) & (df['sma_20'].shift(1) >= df['sma_50'].shift(1)), -1, 0)
            )
            
            # EMA relationships
            df['ema_trend_12'] = np.where(df['ema_12'] > df['ema_12'].shift(1), 1, -1)
            df['ema_trend_26'] = np.where(df['ema_26'] > df['ema_26'].shift(1), 1, -1)
            df['ema_cross'] = np.where(
                (df['ema_12'] > df['ema_26']) & (df['ema_12'].shift(1) <= df['ema_26'].shift(1)), 1,
                np.where((df['ema_12'] < df['ema_26']) & (df['ema_12'].shift(1) >= df['ema_26'].shift(1)), -1, 0)
            )
            
            # Price vs MA position
            df['price_vs_sma20'] = (df['close'] - df['sma_20']) / df['sma_20']
            df['price_vs_sma50'] = (df['close'] - df['sma_50']) / df['sma_50']
            df['price_vs_ema12'] = (df['close'] - df['ema_12']) / df['ema_12']
            df['price_vs_ema26'] = (df['close'] - df['ema_26']) / df['ema_26']
        
        # Linear regression trend
        for period in [10, 20, 50]:
            def calc_trend_strength(series):
                if len(series) < period:
                    return np.nan
                x = np.arange(len(series))
                slope, _, r_value, _, _ = stats.linregress(x, series)
                return slope * r_value ** 2
            
            df[f'trend_strength_{period}'] = df['close'].rolling(period).apply(calc_trend_strength)
        
        # Support and resistance levels
        df['resistance_20'] = df['high'].rolling(20).max()
        df['support_20'] = df['low'].rolling(20).min()
        df['resistance_distance'] = (df['resistance_20'] - df['close']) / df['close']
        df['support_distance'] = (df['close'] - df['support_20']) / df['close']
        
        return df
    
    def _create_statistical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create statistical features"""
        
        # Z-scores
        for period in [20, 50, 100]:
            mean = df['close'].rolling(period).mean()
            std = df['close'].rolling(period).std()
            df[f'z_score_{period}'] = (df['close'] - mean) / std
        
        # Percentile rankings
        for period in [20, 60, 252]:
            df[f'percentile_rank_{period}'] = df['close'].rolling(period).rank(pct=True)
        
        # Distribution features
        for period in [20, 50]:
            returns = df['close'].pct_change()
            df[f'skewness_{period}'] = returns.rolling(period).skew()
            df[f'kurtosis_{period}'] = returns.rolling(period).kurt()
        
        # Autocorrelation
        for lag in [1, 5, 10]:
            df[f'autocorr_{lag}'] = df['close'].pct_change().rolling(50).apply(
                lambda x: x.autocorr(lag=lag) if len(x) > lag else np.nan
            )
        
        return df
    
    def _create_cross_asset_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create cross-asset correlation features"""
        
        # This would be expanded with actual cross-asset data
        # For now, create proxy features
        
        # Relative performance vs own history
        for period in [5, 20, 60]:
            df[f'relative_performance_{period}'] = df['close'].pct_change(period) - df['close'].pct_change(period).rolling(252).mean()
        
        # Beta calculation (proxy using own volatility)
        market_returns = df['close'].pct_change()
        for period in [60, 120, 252]:
            asset_returns = df['close'].pct_change()
            df[f'beta_{period}'] = asset_returns.rolling(period).cov(market_returns) / market_returns.rolling(period).var()
        
        return df
    
    def _create_market_regime_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create market regime classification features"""
        
        # Volatility regimes
        vol_20 = df['close'].pct_change().rolling(20).std()
        vol_percentile = vol_20.rolling(252).rank(pct=True)
        
        df['vol_regime'] = pd.cut(vol_percentile, bins=[0, 0.33, 0.66, 1.0], 
                                 labels=['low_vol', 'medium_vol', 'high_vol'])
        
        # Trend regimes
        trend_20 = df['close'].pct_change(20)
        trend_percentile = trend_20.rolling(252).rank(pct=True)
        
        df['trend_regime'] = pd.cut(trend_percentile, bins=[0, 0.33, 0.66, 1.0], 
                                   labels=['downtrend', 'sideways', 'uptrend'])
        
        # Combined regime
        df['market_regime'] = df['vol_regime'].astype(str) + '_' + df['trend_regime'].astype(str)
        
        # Regime change detection
        df['regime_change'] = (df['market_regime'] != df['market_regime'].shift(1)).astype(int)
        
        return df
    
    def _create_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create time-based features"""
        
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df['day_of_week'] = df['date'].dt.dayofweek
            df['month'] = df['date'].dt.month
            df['quarter'] = df['date'].dt.quarter
            df['year'] = df['date'].dt.year
            
            # Cyclical encoding
            df['day_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
            df['day_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
            df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
            df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
        
        # Trading session features
        df['trading_day'] = np.arange(len(df))
        df['days_since_high'] = df.index - df['high'].expanding().apply(lambda x: x.idxmax(), raw=False)
        df['days_since_low'] = df.index - df['low'].expanding().apply(lambda x: x.idxmin(), raw=False)
        
        return df
    
    def _create_composite_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create composite features combining multiple indicators"""
        
        # Momentum composite
        momentum_features = [col for col in df.columns if 'momentum' in col or 'roc_' in col]
        if momentum_features:
            df['momentum_composite'] = df[momentum_features].mean(axis=1)
            df['momentum_strength'] = df[momentum_features].abs().mean(axis=1)
        
        # Trend composite
        trend_features = [col for col in df.columns if 'trend' in col or 'sma_' in col or 'ema_' in col]
        if trend_features:
            numeric_trend_features = df[trend_features].select_dtypes(include=[np.number]).columns
            if len(numeric_trend_features) > 0:
                df['trend_composite'] = df[numeric_trend_features].mean(axis=1)
                df['trend_consistency'] = df[numeric_trend_features].std(axis=1)
        
        # Volatility composite
        vol_features = [col for col in df.columns if 'volatility' in col or 'atr_' in col]
        if vol_features:
            df['volatility_composite'] = df[vol_features].mean(axis=1)
            df['volatility_stability'] = df[vol_features].std(axis=1)
        
        # Oscillator composite
        osc_features = [col for col in df.columns if any(x in col for x in ['rsi', 'stoch', 'williams'])]
        if osc_features:
            df['oscillator_composite'] = df[osc_features].mean(axis=1)
            df['oscillator_divergence'] = df[osc_features].std(axis=1)
        
        return df
    
    def _create_feature_interactions(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create feature interactions"""
        
        # Key feature interactions
        feature_pairs = [
            ('volatility_20', 'volume_momentum_10'),
            ('rsi_14', 'price_momentum_5'),
            ('trend_strength_20', 'volatility_20'),
            ('momentum_composite', 'volume_sma_ratio_20')
        ]
        
        for feat1, feat2 in feature_pairs:
            if feat1 in df.columns and feat2 in df.columns:
                df[f'{feat1}_x_{feat2}'] = df[feat1] * df[feat2]
                df[f'{feat1}_div_{feat2}'] = df[feat1] / (df[feat2] + 1e-8)
        
        return df
    
    def _normalize_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize features for model training"""
        
        # Identify numeric features to normalize
        numeric_features = df.select_dtypes(include=[np.number]).columns
        
        # Exclude certain features from normalization
        exclude_features = ['date', 'symbol', 'volume', 'open', 'high', 'low', 'close']
        features_to_normalize = [col for col in numeric_features if col not in exclude_features]
        
        # Apply robust scaling to handle outliers
        if features_to_normalize:
            # Clean data first - replace inf and very large values
            df_clean = df[features_to_normalize].copy()
            
            # Replace infinity values
            df_clean = df_clean.replace([np.inf, -np.inf], np.nan)
            
            # Cap extreme values (beyond 5 standard deviations)
            for col in df_clean.columns:
                if df_clean[col].std() > 0:
                    mean_val = df_clean[col].mean()
                    std_val = df_clean[col].std()
                    upper_limit = mean_val + 5 * std_val
                    lower_limit = mean_val - 5 * std_val
                    
                    df_clean[col] = df_clean[col].clip(lower_limit, upper_limit)
            
            # Fill NaN values with 0
            df_clean = df_clean.fillna(0)
            
            # Apply robust scaling
            try:
                df[features_to_normalize] = self.robust_scaler.fit_transform(df_clean)
            except Exception as e:
                print(f"Warning: Scaling failed, using simple normalization: {e}")
                # Fallback to simple standardization
                for col in features_to_normalize:
                    if df[col].std() > 0:
                        df[col] = (df[col] - df[col].mean()) / df[col].std()
                    else:
                        df[col] = 0
        
        return df
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance scores"""
        return self.feature_importance
    
    def get_feature_statistics(self) -> Dict[str, Any]:
        """Get comprehensive feature statistics"""
        return self.feature_stats

# Usage example and integration point
def create_enhanced_features(data: pd.DataFrame, config: Optional[Dict] = None) -> pd.DataFrame:
    """
    Main entry point for feature engineering
    
    Args:
        data: DataFrame with OHLCV and basic indicators
        config: Optional configuration dictionary
        
    Returns:
        DataFrame with comprehensive feature set
    """
    pipeline = FeatureEngineeringPipeline(config)
    enhanced_data = pipeline.create_all_features(data)
    
    return enhanced_data

# Export for new_structure integration
__all__ = [
    'FeatureEngineeringPipeline',
    'create_enhanced_features'
]
