"""
Data processing module for the enhanced pair backtesting system.
Handles data cleaning, alignment, and feature engineering for any trading pair.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import logging
from scipy import stats

logger = logging.getLogger(__name__)

class DataProcessor:
    """
    Generic data processor for pair trading data.
    Handles cleaning, alignment, and feature engineering for any trading pair.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the data processor.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.lookback_window = config.get('lookback_window', 60)
        self.min_observations = config.get('min_observations', 100)
    
    def process_pair_data(self, 
                         df1: pd.DataFrame, 
                         df2: pd.DataFrame, 
                         symbol1: str, 
                         symbol2: str) -> pd.DataFrame:
        """
        Process and align data for a trading pair.
        
        Args:
            df1: First symbol data
            df2: Second symbol data
            symbol1: First symbol name
            symbol2: Second symbol name
            
        Returns:
            Aligned and processed DataFrame
        """
        logger.info(f"Processing pair data for {symbol1}/{symbol2}")
        
        # Align data by timestamp
        aligned_data = self._align_data(df1, df2, symbol1, symbol2)
        
        # Clean data
        cleaned_data = self._clean_data(aligned_data, symbol1, symbol2)
        
        # Calculate spread and z-score
        spread_data = self._calculate_spread_features(cleaned_data, symbol1, symbol2)
        
        # Add technical indicators
        technical_data = self._add_technical_indicators(spread_data, symbol1, symbol2)
        
        # Add regime features
        regime_data = self._add_regime_features(technical_data, symbol1, symbol2)
        
        logger.info(f"Processed data: {len(regime_data)} observations")
        
        return regime_data
    
    def _align_data(self, 
                   df1: pd.DataFrame, 
                   df2: pd.DataFrame, 
                   symbol1: str, 
                   symbol2: str) -> pd.DataFrame:
        """Align data by timestamp."""
        # Get common timestamps
        common_index = df1.index.intersection(df2.index)
        
        if len(common_index) < self.min_observations:
            raise ValueError(f"Insufficient overlapping data: {len(common_index)} observations")
        
        # Create aligned DataFrame
        aligned = pd.DataFrame(index=common_index)
        
        # Add price data
        aligned[f'{symbol1}_close'] = df1.loc[common_index, 'close']
        aligned[f'{symbol2}_close'] = df2.loc[common_index, 'close']
        
        # Add OHLCV data if available
        for col in ['open', 'high', 'low', 'volume']:
            if col in df1.columns:
                aligned[f'{symbol1}_{col}'] = df1.loc[common_index, col]
            if col in df2.columns:
                aligned[f'{symbol2}_{col}'] = df2.loc[common_index, col]
        
        # Add returns
        aligned[f'{symbol1}_returns'] = df1.loc[common_index, 'returns']
        aligned[f'{symbol2}_returns'] = df2.loc[common_index, 'returns']
        
        return aligned.sort_index()
    
    def _clean_data(self, 
                   df: pd.DataFrame, 
                   symbol1: str, 
                   symbol2: str) -> pd.DataFrame:
        """Clean the aligned data."""
        # Remove rows with missing prices
        price_cols = [f'{symbol1}_close', f'{symbol2}_close']
        df = df.dropna(subset=price_cols)
        
        # Remove zero or negative prices
        for col in price_cols:
            df = df[df[col] > 0]
        
        # Remove extreme returns (>50% in one period)
        return_cols = [f'{symbol1}_returns', f'{symbol2}_returns']
        for col in return_cols:
            if col in df.columns:
                df = df[df[col].abs() < 0.5]
        
        # Forward fill missing values for other columns
        df = df.fillna(method='ffill')
        
        # Remove any remaining NaN values
        df = df.dropna()
        
        logger.info(f"Data cleaning removed {len(df)} rows")
        
        return df
    
    def _calculate_spread_features(self, 
                                  df: pd.DataFrame, 
                                  symbol1: str, 
                                  symbol2: str) -> pd.DataFrame:
        """Calculate spread and related features."""
        # Calculate simple spread (will be replaced with hedge ratio later)
        df['spread'] = df[f'{symbol1}_close'] - df[f'{symbol2}_close']
        
        # Calculate rolling statistics
        df['spread_mean'] = df['spread'].rolling(window=self.lookback_window).mean()
        df['spread_std'] = df['spread'].rolling(window=self.lookback_window).std()
        
        # Calculate z-score
        df['z_score'] = (df['spread'] - df['spread_mean']) / df['spread_std']
        
        # Calculate spread returns
        df['spread_returns'] = df['spread'].pct_change()
        
        # Calculate rolling correlation
        df['correlation'] = df[f'{symbol1}_returns'].rolling(
            window=self.lookback_window
        ).corr(df[f'{symbol2}_returns'])
        
        return df
    
    def _add_technical_indicators(self, 
                                 df: pd.DataFrame, 
                                 symbol1: str, 
                                 symbol2: str) -> pd.DataFrame:
        """Add technical indicators."""
        # Price momentum
        for symbol in [symbol1, symbol2]:
            price_col = f'{symbol}_close'
            
            # Simple moving averages
            df[f'{symbol}_sma_10'] = df[price_col].rolling(window=10).mean()
            df[f'{symbol}_sma_30'] = df[price_col].rolling(window=30).mean()
            
            # Price relative to moving average
            df[f'{symbol}_price_ma_ratio'] = df[price_col] / df[f'{symbol}_sma_30']
            
            # Volatility
            df[f'{symbol}_volatility'] = df[f'{symbol}_returns'].rolling(
                window=20
            ).std() * np.sqrt(252)
            
            # RSI-like indicator
            df[f'{symbol}_rsi'] = self._calculate_rsi(df[f'{symbol}_returns'])
        
        # Spread momentum
        df['spread_momentum'] = df['spread'].diff(5)  # 5-period momentum
        df['spread_volatility'] = df['spread_returns'].rolling(window=20).std()
        
        # Bollinger Bands for spread
        df['spread_upper_band'] = df['spread_mean'] + 2 * df['spread_std']
        df['spread_lower_band'] = df['spread_mean'] - 2 * df['spread_std']
        
        return df
    
    def _calculate_rsi(self, returns: pd.Series, window: int = 14) -> pd.Series:
        """Calculate RSI-like indicator from returns."""
        gains = returns.where(returns > 0, 0)
        losses = -returns.where(returns < 0, 0)
        
        avg_gains = gains.rolling(window=window).mean()
        avg_losses = losses.rolling(window=window).mean()
        
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _add_regime_features(self, 
                            df: pd.DataFrame, 
                            symbol1: str, 
                            symbol2: str) -> pd.DataFrame:
        """Add regime-related features."""
        # Volatility regime indicators
        df['volatility_regime'] = self._classify_volatility_regime(df['spread_volatility'])
        
        # Correlation regime
        df['correlation_regime'] = self._classify_correlation_regime(df['correlation'])
        
        # Spread level regime
        df['spread_level_regime'] = self._classify_spread_level_regime(df['z_score'])
        
        # Market stress indicators
        df['market_stress'] = self._calculate_market_stress(df, symbol1, symbol2)
        
        return df
    
    def _classify_volatility_regime(self, volatility: pd.Series) -> pd.Series:
        """Classify volatility into regimes."""
        # Use quantiles to define regimes
        vol_quantiles = volatility.quantile([0.33, 0.67])
        
        regime = pd.Series(index=volatility.index, dtype=int)
        regime[volatility <= vol_quantiles.iloc[0]] = 0  # Low volatility
        regime[(volatility > vol_quantiles.iloc[0]) & 
               (volatility <= vol_quantiles.iloc[1])] = 1  # Medium volatility
        regime[volatility > vol_quantiles.iloc[1]] = 2  # High volatility
        
        return regime
    
    def _classify_correlation_regime(self, correlation: pd.Series) -> pd.Series:
        """Classify correlation into regimes."""
        # Use fixed thresholds for correlation
        regime = pd.Series(index=correlation.index, dtype=int)
        regime[correlation < 0.5] = 0  # Low correlation
        regime[(correlation >= 0.5) & (correlation < 0.8)] = 1  # Medium correlation
        regime[correlation >= 0.8] = 2  # High correlation
        
        return regime
    
    def _classify_spread_level_regime(self, z_score: pd.Series) -> pd.Series:
        """Classify spread level into regimes."""
        regime = pd.Series(index=z_score.index, dtype=int)
        regime[z_score.abs() < 1.0] = 0  # Normal regime
        regime[(z_score.abs() >= 1.0) & (z_score.abs() < 2.0)] = 1  # Moderate regime
        regime[z_score.abs() >= 2.0] = 2  # Extreme regime
        
        return regime
    
    def _calculate_market_stress(self, 
                                df: pd.DataFrame, 
                                symbol1: str, 
                                symbol2: str) -> pd.Series:
        """Calculate market stress indicator."""
        # Combine volatility and correlation changes
        vol1 = df[f'{symbol1}_volatility']
        vol2 = df[f'{symbol2}_volatility']
        corr = df['correlation']
        
        # Normalized stress components
        vol_stress = (vol1 + vol2) / 2
        corr_stress = (1 - corr).abs()  # Stress when correlation breaks down
        
        # Combined stress indicator
        stress = (vol_stress.rolling(window=5).mean() + 
                 corr_stress.rolling(window=5).mean()) / 2
        
        return stress
    
    def get_features_for_ml(self, 
                           df: pd.DataFrame, 
                           symbol1: str, 
                           symbol2: str) -> pd.DataFrame:
        """
        Extract features for machine learning models.
        
        Args:
            df: Processed data
            symbol1: First symbol
            symbol2: Second symbol
            
        Returns:
            DataFrame with ML features
        """
        feature_columns = [
            'z_score',
            'spread_momentum',
            'spread_volatility',
            'correlation',
            'volatility_regime',
            'correlation_regime',
            'spread_level_regime',
            'market_stress'
        ]
        
        # Add price momentum features
        for symbol in [symbol1, symbol2]:
            feature_columns.extend([
                f'{symbol}_price_ma_ratio',
                f'{symbol}_volatility',
                f'{symbol}_rsi'
            ])
        
        # Select available features
        available_features = [col for col in feature_columns if col in df.columns]
        
        features = df[available_features].copy()
        
        # Forward fill missing values
        features = features.fillna(method='ffill')
        
        # Remove any remaining NaN values
        features = features.dropna()
        
        logger.info(f"Extracted {len(available_features)} features for ML")
        
        return features
    
    def create_training_labels(self, 
                              df: pd.DataFrame, 
                              lookahead_periods: int = 20) -> pd.Series:
        """
        Create labels for training ML models.
        
        Args:
            df: Processed data
            lookahead_periods: Periods to look ahead for labeling
            
        Returns:
            Series with binary labels (1 for successful mean reversion, 0 otherwise)
        """
        z_scores = df['z_score'].copy()
        
        # Create labels based on mean reversion
        labels = pd.Series(index=z_scores.index, dtype=int)
        
        for i in range(len(z_scores) - lookahead_periods):
            current_z = z_scores.iloc[i]
            future_z = z_scores.iloc[i:i+lookahead_periods]
            
            # Check if spread reverts to mean within lookahead period
            if abs(current_z) > 1.0:  # Only label when spread is away from mean
                if np.sign(current_z) != np.sign(future_z).mode()[0]:
                    labels.iloc[i] = 1  # Successful reversion
                else:
                    labels.iloc[i] = 0  # No reversion
            else:
                labels.iloc[i] = 0  # Not a trading opportunity
        
        return labels
    
    def split_data(self, 
                  df: pd.DataFrame, 
                  train_start: str, 
                  train_end: str, 
                  test_start: str, 
                  test_end: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Split data into training and testing sets.
        
        Args:
            df: Full dataset
            train_start: Training start date
            train_end: Training end date
            test_start: Testing start date
            test_end: Testing end date
            
        Returns:
            Tuple of (training_data, testing_data)
        """
        train_data = df.loc[train_start:train_end].copy()
        test_data = df.loc[test_start:test_end].copy()
        
        logger.info(f"Training data: {len(train_data)} observations")
        logger.info(f"Testing data: {len(test_data)} observations")
        
        return train_data, test_data
    
    def validate_processed_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate processed data quality.
        
        Args:
            df: Processed data
            
        Returns:
            Dictionary with validation results
        """
        validation = {
            'valid': True,
            'issues': [],
            'warnings': [],
            'statistics': {}
        }
        
        # Check for sufficient data
        if len(df) < self.min_observations:
            validation['valid'] = False
            validation['issues'].append(f"Insufficient data: {len(df)} < {self.min_observations}")
        
        # Check for missing values
        missing_pct = df.isnull().sum().sum() / (len(df) * len(df.columns)) * 100
        if missing_pct > 5:
            validation['warnings'].append(f"High missing data: {missing_pct:.1f}%")
        
        # Check z-score distribution
        if 'z_score' in df.columns:
            z_stats = df['z_score'].describe()
            validation['statistics']['z_score'] = z_stats.to_dict()
            
            if abs(z_stats['mean']) > 0.5:
                validation['warnings'].append(f"Z-score mean not centered: {z_stats['mean']:.2f}")
        
        # Check spread statistics
        if 'spread' in df.columns:
            spread_stats = df['spread'].describe()
            validation['statistics']['spread'] = spread_stats.to_dict()
        
        return validation 