#!/usr/bin/env python3
"""
Feature Engineering Module for Core Engine
==========================================

Transforms technical indicators into trading features for signal generation.
Creates normalized, scaled, and cross-sectional features suitable for ML models.

Author: StatArb_Gemini Core Engine
Version: 1.0.0 (Feature Engineering)
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from sklearn.preprocessing import StandardScaler, RobustScaler
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

@dataclass
class FeatureConfig:
    """Configuration for feature engineering"""
    # Normalization
    use_normalization: bool = True
    normalization_method: str = "robust"  # "standard", "robust", "minmax"
    lookback_periods: List[int] = None  # Periods for rolling statistics
    
    # Cross-sectional features
    enable_cross_sectional: bool = True
    cross_sectional_universe: List[str] = None  # Symbols for cross-sectional analysis
    
    # Feature selection
    max_features: Optional[int] = None
    feature_importance_threshold: float = 0.01
    
    # Lag features
    lag_periods: List[int] = None
    
    def __post_init__(self):
        if self.lookback_periods is None:
            self.lookback_periods = [5, 10, 20]
        if self.lag_periods is None:
            self.lag_periods = [1, 2, 3]
        if self.cross_sectional_universe is None:
            self.cross_sectional_universe = ['NVDA', 'TSLA', 'AAPL', 'MSFT', 'GOOGL', 'SPY', 'QQQ']

class FeatureEngineer:
    """
    Feature Engineering for Trading Signals
    
    Transforms technical indicators into ML-ready features:
    - Normalization and scaling
    - Lag features for temporal patterns
    - Cross-sectional features for relative analysis
    - Rolling statistics and momentum features
    """
    
    def __init__(self, config: Optional[FeatureConfig] = None):
        self.config = config or FeatureConfig()
        self.logger = logging.getLogger("feature_engineer")
        
        # Scalers for different feature types
        self.scalers: Dict[str, Any] = {}
        
        # Feature metadata
        self.feature_columns: List[str] = []
        self.target_columns: List[str] = []
        
        self.logger.info("FeatureEngineer initialized")
    
    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create trading features from indicators DataFrame
        
        Args:
            df: DataFrame with indicators (from TechnicalIndicators)
            
        Returns:
            DataFrame with engineered features
        """
        if df.empty:
            return df
        
        self.logger.info(f"Creating features for {len(df['symbol'].unique())} symbols")
        
        # Process each symbol separately, then combine
        result_dfs = []
        
        for symbol in df['symbol'].unique():
            symbol_df = df[df['symbol'] == symbol].copy().sort_values('timestamp')
            
            if len(symbol_df) < 10:  # Need minimum data for feature engineering
                self.logger.warning(f"Insufficient data for {symbol}, skipping feature engineering")
                continue
            
            # Create features for this symbol
            symbol_df = self._create_symbol_features(symbol_df)
            result_dfs.append(symbol_df)
        
        if not result_dfs:
            return pd.DataFrame()
        
        # Combine all symbols
        result = pd.concat(result_dfs, ignore_index=True)
        
        # Create cross-sectional features
        if self.config.enable_cross_sectional:
            result = self._create_cross_sectional_features(result)
        
        # Normalize features
        if self.config.use_normalization:
            result = self._normalize_features(result)
        
        # Store feature metadata
        self._update_feature_metadata(result)
        
        self.logger.info(f"Created {len(self.feature_columns)} features for {len(result)} records")
        return result
    
    def _create_symbol_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create features for a single symbol"""
        # Basic price features
        df = self._create_price_features(df)
        
        # Momentum features
        df = self._create_momentum_features(df)
        
        # Volatility features
        df = self._create_volatility_features(df)
        
        # Volume features
        df = self._create_volume_features(df)
        
        # Technical indicator features
        df = self._create_indicator_features(df)
        
        # Lag features
        df = self._create_lag_features(df)
        
        # Rolling statistics
        df = self._create_rolling_features(df)
        
        return df
    
    def _create_price_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create price-based features"""
        # Returns at different horizons
        for period in [1, 2, 3, 5, 10]:
            if len(df) > period:
                df[f'return_{period}d'] = df['close'].pct_change(period)
        
        # Log returns
        df['log_return'] = np.log(df['close'] / df['close'].shift(1))
        
        # OHLC ratios
        df['hl_ratio'] = (df['high'] - df['low']) / df['close']
        df['oc_ratio'] = (df['open'] - df['close']) / df['close']
        df['body_size'] = np.abs(df['close'] - df['open']) / df['close']
        df['upper_shadow'] = (df['high'] - np.maximum(df['open'], df['close'])) / df['close']
        df['lower_shadow'] = (np.minimum(df['open'], df['close']) - df['low']) / df['close']
        
        # Price momentum
        df['price_acceleration'] = df['log_return'].diff()
        
        return df
    
    def _create_momentum_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create momentum-based features"""
        # RSI-based features
        if 'rsi' in df.columns:
            df['rsi_normalized'] = (df['rsi'] - 50) / 50  # Center at 0
            df['rsi_oversold'] = (df['rsi'] < 30).astype(int)
            df['rsi_overbought'] = (df['rsi'] > 70).astype(int)
            df['rsi_momentum'] = df['rsi'].diff()
        
        # MACD features
        if 'macd' in df.columns and 'macd_signal' in df.columns:
            df['macd_divergence'] = df['macd'] - df['macd_signal']
            df['macd_bullish'] = (df['macd'] > df['macd_signal']).astype(int)
            if 'macd_histogram' in df.columns:
                df['macd_hist_momentum'] = df['macd_histogram'].diff()
        
        # Stochastic features
        if 'stoch_k' in df.columns:
            df['stoch_oversold'] = (df['stoch_k'] < 20).astype(int)
            df['stoch_overbought'] = (df['stoch_k'] > 80).astype(int)
            if 'stoch_d' in df.columns:
                df['stoch_crossover'] = (df['stoch_k'] > df['stoch_d']).astype(int)
        
        # Rate of change features
        roc_cols = [col for col in df.columns if col.startswith('roc_')]
        for col in roc_cols:
            df[f'{col}_normalized'] = df[col] / df[col].rolling(20).std()
        
        return df
    
    def _create_volatility_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create volatility-based features"""
        # Bollinger Band features
        if 'bb_position' in df.columns:
            df['bb_squeeze'] = (df['bb_width'] < df['bb_width'].rolling(20).quantile(0.2)).astype(int)
            df['bb_breakout_up'] = ((df['close'] > df['bb_upper']) & 
                                   (df['close'].shift(1) <= df['bb_upper'].shift(1))).astype(int)
            df['bb_breakout_down'] = ((df['close'] < df['bb_lower']) & 
                                     (df['close'].shift(1) >= df['bb_lower'].shift(1))).astype(int)
        
        # ATR features
        if 'atr' in df.columns:
            df['atr_normalized'] = df['atr'] / df['close']
            df['atr_percentile'] = df['atr'].rolling(50).rank(pct=True)
        
        # Historical volatility features
        vol_cols = [col for col in df.columns if col.startswith('volatility_')]
        for col in vol_cols:
            period = col.split('_')[1]
            df[f'vol_regime_{period}'] = (df[col] > df[col].rolling(60).quantile(0.7)).astype(int)
        
        # Volatility clustering
        df['vol_clustering'] = (df['log_return'].abs() > 
                               df['log_return'].abs().rolling(20).quantile(0.8)).astype(int)
        
        return df
    
    def _create_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create volume-based features"""
        if 'volume' not in df.columns:
            return df
        
        # Volume momentum
        df['volume_change'] = df['volume'].pct_change()
        df['volume_acceleration'] = df['volume_change'].diff()
        
        # Volume-price relationship
        df['volume_price_trend'] = df['volume_change'] * df['return_1d']
        
        # Volume breakouts
        if 'volume_sma' in df.columns:
            df['volume_breakout'] = (df['volume'] > 2 * df['volume_sma']).astype(int)
        
        # OBV features
        if 'obv' in df.columns:
            df['obv_momentum'] = df['obv'].pct_change()
            df['obv_divergence'] = np.sign(df['return_1d']) != np.sign(df['obv_momentum'])
        
        return df
    
    def _create_indicator_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create features from technical indicators"""
        # Moving average features
        sma_cols = [col for col in df.columns if col.startswith('sma_')]
        ema_cols = [col for col in df.columns if col.startswith('ema_')]
        
        # Distance from moving averages
        for col in sma_cols + ema_cols:
            df[f'{col}_distance'] = (df['close'] - df[col]) / df[col]
            df[f'{col}_above'] = (df['close'] > df[col]).astype(int)
        
        # Moving average slope
        for col in sma_cols[:2]:  # Only for shorter periods to avoid overfitting
            df[f'{col}_slope'] = df[col].pct_change()
        
        # Golden/Death cross signals
        if 'sma_20' in df.columns and 'sma_50' in df.columns:
            df['golden_cross'] = ((df['sma_20'] > df['sma_50']) & 
                                 (df['sma_20'].shift(1) <= df['sma_50'].shift(1))).astype(int)
            df['death_cross'] = ((df['sma_20'] < df['sma_50']) & 
                                (df['sma_20'].shift(1) >= df['sma_50'].shift(1))).astype(int)
        
        return df
    
    def _create_lag_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create lagged features for temporal patterns"""
        # Key features to lag
        key_features = ['return_1d', 'rsi', 'volume_change', 'atr_normalized']
        
        for feature in key_features:
            if feature in df.columns:
                for lag in self.config.lag_periods:
                    df[f'{feature}_lag_{lag}'] = df[feature].shift(lag)
        
        return df
    
    def _create_rolling_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create rolling statistics features"""
        base_features = ['return_1d', 'volume_change', 'hl_ratio']
        
        for feature in base_features:
            if feature in df.columns:
                for period in self.config.lookback_periods:
                    if len(df) >= period:
                        # Rolling statistics
                        df[f'{feature}_mean_{period}'] = df[feature].rolling(period).mean()
                        df[f'{feature}_std_{period}'] = df[feature].rolling(period).std()
                        df[f'{feature}_skew_{period}'] = df[feature].rolling(period).skew()
                        df[f'{feature}_rank_{period}'] = df[feature].rolling(period).rank(pct=True)
        
        return df
    
    def _create_cross_sectional_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create cross-sectional (relative) features"""
        # Group by timestamp for cross-sectional analysis
        grouped = df.groupby('timestamp')
        
        # Key features for cross-sectional analysis
        cs_features = ['return_1d', 'rsi', 'volume_ratio', 'atr_normalized']
        
        for feature in cs_features:
            if feature in df.columns:
                # Cross-sectional rank
                df[f'{feature}_cs_rank'] = grouped[feature].rank(pct=True)
                
                # Z-score relative to universe
                df[f'{feature}_cs_zscore'] = grouped[feature].transform(
                    lambda x: (x - x.mean()) / x.std() if x.std() > 0 else 0
                )
                
                # Quintile assignment
                df[f'{feature}_cs_quintile'] = grouped[feature].transform(
                    lambda x: pd.qcut(x, min(5, len(x.unique())), labels=list(range(1, min(6, len(x.unique())+1))), duplicates='drop') if len(x.unique()) > 1 else 1
                )
        
        return df
    
    def _normalize_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize features using configured method
        CRITICAL: Preserve raw trading indicators for signal generation
        """
        # Identify feature columns (exclude metadata AND core trading indicators)
        metadata_cols = ['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']
        
        # CRITICAL: Preserve core trading indicators that strategies need
        # Use actual column names from indicators engine
        trading_indicators = [
            'sma_5', 'sma_10', 'sma_20', 'sma_50', 'sma_200',
            'ema_5', 'ema_9', 'ema_10', 'ema_20', 'ema_21', 'ema_50', 'ema_200',
            'bb_upper', 'bb_lower', 'bb_middle', 'bb_width', 'bb_position',  # Actual BB column names
            'rsi', 'rsi_14', 'rsi_21',  # Include both possible RSI names
            'macd', 'macd_signal', 'macd_histogram',
            'atr', 'atr_14', 'adx', 'adx_14', 'cci', 'cci_20', 
            'williams_r', 'williams_r_14',
            'stoch_k', 'stoch_d', 'obv', 'vwap',
            # Additional indicators that might exist
            'momentum', 'roc', 'trix', 'ultimate_oscillator'
        ]
        
        # Columns to preserve (don't normalize)
        preserve_cols = metadata_cols + trading_indicators
        
        # Only normalize derived features, not core trading indicators
        feature_cols = [col for col in df.columns 
                       if col not in preserve_cols 
                       and not col.endswith('_quintile')
                       and not col.startswith('price_')  # Preserve price-based indicators
                       and not col.startswith('return_')]  # Preserve return calculations
        
        if not feature_cols:
            return df
        
        # Choose scaler
        if self.config.normalization_method == "standard":
            scaler = StandardScaler()
        elif self.config.normalization_method == "robust":
            scaler = RobustScaler()
        else:  # minmax
            from sklearn.preprocessing import MinMaxScaler
            scaler = MinMaxScaler()
        
        # Fit and transform features
        try:
            # Handle NaN and infinity values
            feature_data = df[feature_cols].copy()
            
            # Replace infinity values with NaN, then fill with 0
            feature_data = feature_data.replace([np.inf, -np.inf], np.nan)
            feature_data = feature_data.fillna(0)
            
            # Check for any remaining problematic values (handle different data types)
            try:
                has_inf = np.any(np.isinf(feature_data.select_dtypes(include=[np.number]).values))
                has_nan = np.any(np.isnan(feature_data.select_dtypes(include=[np.number]).values))
            except (TypeError, ValueError):
                # Fallback for mixed data types
                has_inf = False
                has_nan = False
                for col in feature_data.columns:
                    if feature_data[col].dtype in ['float64', 'float32', 'int64', 'int32']:
                        col_data = pd.to_numeric(feature_data[col], errors='coerce')
                        if np.any(np.isinf(col_data)) or np.any(np.isnan(col_data)):
                            has_inf = True
                            has_nan = True
                            break
            
            if has_inf or has_nan:
                self.logger.warning("Still have inf/nan values after cleaning, using median fill")
                for col in feature_data.columns:
                    if feature_data[col].dtype in ['float64', 'float32']:
                        median_val = feature_data[col].replace([np.inf, -np.inf], np.nan).median()
                        if np.isnan(median_val):
                            median_val = 0.0
                        feature_data[col] = feature_data[col].replace([np.inf, -np.inf, np.nan], median_val)
            
            # Fit scaler on cleaned data
            scaled_features = scaler.fit_transform(feature_data)
            
            # Replace original features with scaled versions
            df[feature_cols] = scaled_features
            
            # Store scaler for future use
            self.scalers['main'] = scaler
            
            # Data integrity validation after normalization
            self._validate_data_integrity(df)
            
            self.logger.info(f"Normalized {len(feature_cols)} features using {self.config.normalization_method} scaling")
            self.logger.info(f"Preserved {len(preserve_cols)} core trading indicators")
            
        except Exception as e:
            self.logger.error(f"Feature normalization failed: {e}")
        
        return df
    
    def _validate_data_integrity(self, df: pd.DataFrame):
        """
        Validate data integrity after feature engineering
        CRITICAL: Catch data corruption that could cause trading errors
        """
        try:
            # Check core trading indicators are preserved
            core_indicators = ['close', 'sma_20', 'bb_upper_20', 'bb_lower_20', 'rsi_14']
            
            for indicator in core_indicators:
                if indicator in df.columns:
                    values = df[indicator].dropna()
                    if len(values) > 0:
                        # Check for reasonable price ranges
                        if indicator in ['close', 'sma_20', 'bb_upper_20', 'bb_lower_20']:
                            if values.min() < 1.0:  # Prices should be > $1
                                self.logger.error(f"❌ DATA CORRUPTION: {indicator} has values < $1.00 (min: {values.min():.4f})")
                                raise ValueError(f"Data corruption detected in {indicator}")
                            
                            if values.max() > 10000.0:  # Reasonable upper bound
                                self.logger.warning(f"⚠️ UNUSUAL VALUES: {indicator} has very high values (max: {values.max():.2f})")
                        
                        # Check RSI is in valid range
                        elif indicator == 'rsi_14':
                            if values.min() < 0 or values.max() > 100:
                                self.logger.error(f"❌ DATA CORRUPTION: RSI out of range [0,100] (range: {values.min():.2f}-{values.max():.2f})")
                                raise ValueError(f"RSI data corruption detected")
            
            # Check for extreme z-score issues
            if 'close' in df.columns and 'sma_20' in df.columns:
                latest_close = df['close'].iloc[-1]
                latest_sma = df['sma_20'].iloc[-1]
                
                if abs(latest_close - latest_sma) / latest_close > 0.5:  # >50% deviation
                    self.logger.warning(f"⚠️ EXTREME DEVIATION: Close ${latest_close:.2f} vs SMA ${latest_sma:.2f}")
            
            self.logger.debug("✅ Data integrity validation passed")
            
        except Exception as e:
            self.logger.error(f"❌ Data integrity validation failed: {e}")
            raise
    
    def _update_feature_metadata(self, df: pd.DataFrame):
        """Update feature column metadata"""
        metadata_cols = ['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']
        self.feature_columns = [col for col in df.columns if col not in metadata_cols]
        
        # Identify potential target columns (future returns)
        self.target_columns = [col for col in df.columns if 'return_' in col and '_lag_' not in col]
    
    def get_feature_importance(self, df: pd.DataFrame, target_col: str = 'return_1d') -> pd.DataFrame:
        """Calculate feature importance using correlation with target"""
        if target_col not in df.columns:
            self.logger.warning(f"Target column {target_col} not found")
            return pd.DataFrame()
        
        # Calculate correlations
        feature_cols = [col for col in self.feature_columns if col != target_col]
        correlations = []
        
        for col in feature_cols:
            if col in df.columns:
                corr = df[col].corr(df[target_col])
                correlations.append({
                    'feature': col,
                    'correlation': corr,
                    'abs_correlation': abs(corr) if not pd.isna(corr) else 0
                })
        
        importance_df = pd.DataFrame(correlations)
        importance_df = importance_df.sort_values('abs_correlation', ascending=False)
        
        return importance_df
    
    def select_features(self, df: pd.DataFrame, importance_df: pd.DataFrame) -> pd.DataFrame:
        """Select top features based on importance"""
        if importance_df.empty:
            return df
        
        # Apply threshold
        selected_features = importance_df[
            importance_df['abs_correlation'] >= self.config.feature_importance_threshold
        ]['feature'].tolist()
        
        # Apply max features limit
        if self.config.max_features and len(selected_features) > self.config.max_features:
            selected_features = selected_features[:self.config.max_features]
        
        # Keep metadata columns and selected features
        metadata_cols = ['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']
        keep_cols = metadata_cols + selected_features + self.target_columns
        keep_cols = [col for col in keep_cols if col in df.columns]
        
        result = df[keep_cols].copy()
        
        self.logger.info(f"Selected {len(selected_features)} features from {len(self.feature_columns)} total")
        return result