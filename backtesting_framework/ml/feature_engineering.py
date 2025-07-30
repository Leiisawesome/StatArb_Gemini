#!/usr/bin/env python3
"""
Feature Engineering
Phase 3: Advanced Analytics & Optimization - Batch 1
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class FeatureEngineer:
    """Feature engineering for ML models"""
    
    def __init__(self):
        self.feature_config = {
            'technical_indicators': True,
            'price_features': True,
            'volume_features': True,
            'volatility_features': True,
            'momentum_features': True
        }
        logger.info("Initialized FeatureEngineer")
    
    def create_features(self, data: pd.DataFrame, symbol: str = None) -> pd.DataFrame:
        """Create comprehensive feature set from market data"""
        
        if data.empty:
            logger.warning(f"Empty data provided for {symbol}")
            return pd.DataFrame()
        
        features = data.copy()
        
        # Price features
        if self.feature_config['price_features']:
            features = self._add_price_features(features)
        
        # Technical indicators
        if self.feature_config['technical_indicators']:
            features = self._add_technical_indicators(features)
        
        # Volume features
        if self.feature_config['volume_features']:
            features = self._add_volume_features(features)
        
        # Volatility features
        if self.feature_config['volatility_features']:
            features = self._add_volatility_features(features)
        
        # Momentum features
        if self.feature_config['momentum_features']:
            features = self._add_momentum_features(features)
        
        # Remove NaN values
        features = features.dropna()
        
        logger.info(f"Created {len(features.columns)} features for {symbol}")
        return features
    
    def _add_price_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add price-based features"""
        features = data.copy()
        
        # Price changes
        features['price_change'] = features['close'].pct_change()
        features['price_change_2d'] = features['close'].pct_change(2)
        features['price_change_5d'] = features['close'].pct_change(5)
        
        # High-Low spread
        features['hl_spread'] = (features['high'] - features['low']) / features['close']
        
        # Open-Close spread
        features['oc_spread'] = (features['close'] - features['open']) / features['open']
        
        # Price position within day range
        features['price_position'] = (features['close'] - features['low']) / (features['high'] - features['low'])
        
        return features
    
    def _add_technical_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators"""
        features = data.copy()
        
        # RSI
        features['rsi'] = self._calculate_rsi(features['close'], window=14)
        
        # MACD
        macd, signal = self._calculate_macd(features['close'])
        features['macd'] = macd
        features['macd_signal'] = signal
        features['macd_histogram'] = macd - signal
        
        # Bollinger Bands
        bb_upper, bb_lower = self._calculate_bollinger_bands(features['close'])
        features['bb_upper'] = bb_upper
        features['bb_lower'] = bb_lower
        features['bb_position'] = (features['close'] - bb_lower) / (bb_upper - bb_lower)
        
        # Moving averages
        features['sma_5'] = features['close'].rolling(5).mean()
        features['sma_20'] = features['close'].rolling(20).mean()
        features['ema_12'] = features['close'].ewm(span=12).mean()
        features['ema_26'] = features['close'].ewm(span=26).mean()
        
        return features
    
    def _add_volume_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add volume-based features"""
        features = data.copy()
        
        # Volume changes
        features['volume_change'] = features['volume'].pct_change()
        features['volume_ma_5'] = features['volume'].rolling(5).mean()
        features['volume_ma_20'] = features['volume'].rolling(20).mean()
        
        # Volume-price relationship
        features['volume_price_trend'] = (features['volume'] * features['price_change']).rolling(5).sum()
        
        # Volume ratio
        features['volume_ratio'] = features['volume'] / features['volume_ma_20']
        
        return features
    
    def _add_volatility_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add volatility features"""
        features = data.copy()
        
        # Rolling volatility
        features['volatility_5d'] = features['price_change'].rolling(5).std()
        features['volatility_20d'] = features['price_change'].rolling(20).std()
        
        # Realized volatility
        features['realized_vol'] = np.sqrt((features['price_change']**2).rolling(20).sum())
        
        # Parkinson volatility
        features['parkinson_vol'] = np.sqrt(
            ((np.log(features['high'] / features['low'])**2) / (4 * np.log(2))).rolling(20).mean()
        )
        
        return features
    
    def _add_momentum_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add momentum features"""
        features = data.copy()
        
        # Momentum indicators
        features['momentum_5d'] = features['close'] / features['close'].shift(5) - 1
        features['momentum_10d'] = features['close'] / features['close'].shift(10) - 1
        features['momentum_20d'] = features['close'] / features['close'].shift(20) - 1
        
        # Rate of change
        features['roc_5d'] = (features['close'] - features['close'].shift(5)) / features['close'].shift(5)
        features['roc_10d'] = (features['close'] - features['close'].shift(10)) / features['close'].shift(10)
        
        # Williams %R
        features['williams_r'] = self._calculate_williams_r(features)
        
        return features
    
    def _calculate_rsi(self, prices: pd.Series, window: int = 14) -> pd.Series:
        """Calculate RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
        """Calculate MACD"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=signal).mean()
        return macd, signal_line
    
    def _calculate_bollinger_bands(self, prices: pd.Series, window: int = 20, std_dev: int = 2) -> tuple:
        """Calculate Bollinger Bands"""
        sma = prices.rolling(window=window).mean()
        std = prices.rolling(window=window).std()
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        return upper_band, lower_band
    
    def _calculate_williams_r(self, data: pd.DataFrame, window: int = 14) -> pd.Series:
        """Calculate Williams %R"""
        highest_high = data['high'].rolling(window=window).max()
        lowest_low = data['low'].rolling(window=window).min()
        williams_r = -100 * (highest_high - data['close']) / (highest_high - lowest_low)
        return williams_r
    
    def get_feature_summary(self) -> Dict:
        """Get feature engineering summary"""
        return {
            'feature_config': self.feature_config,
            'total_feature_types': len(self.feature_config),
            'enabled_features': sum(self.feature_config.values())
        }
