#!/usr/bin/env python3
"""
Market Regime Detection
Phase 3: Advanced Analytics & Optimization - Batch 2
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

class RegimeDetector:
    """Market regime detection using various methods"""
    
    def __init__(self):
        self.regime_history = []
        self.current_regime = None
        self.regime_models = {}
        
        logger.info("Initialized RegimeDetector")
    
    def detect_regimes_volatility(self, data: pd.DataFrame, window: int = 20, 
                                 n_regimes: int = 3) -> Dict:
        """Detect market regimes based on volatility clustering"""
        
        if len(data) < window * 2:
            logger.warning(f"Insufficient data for regime detection: {len(data)} < {window * 2}")
            return {}
        
        # Calculate rolling volatility
        returns = data['close'].pct_change().dropna()
        rolling_vol = returns.rolling(window=window).std()
        
        # Remove NaN values
        clean_vol = rolling_vol.dropna()
        
        if len(clean_vol) < n_regimes * 10:
            logger.warning(f"Insufficient data for clustering: {len(clean_vol)} points")
            return {}
        
        # Prepare features for clustering
        features = pd.DataFrame({
            'volatility': clean_vol,
            'volatility_ma': clean_vol.rolling(window=5).mean(),
            'volatility_std': clean_vol.rolling(window=5).std()
        }).dropna()
        
        # Standardize features
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features)
        
        # Perform clustering
        kmeans = KMeans(n_clusters=n_regimes, random_state=42)
        regime_labels = kmeans.fit_predict(features_scaled)
        
        # Analyze regimes
        regime_analysis = {}
        for i in range(n_regimes):
            regime_mask = regime_labels == i
            regime_vol = features['volatility'][regime_mask]
            
            regime_analysis[f'regime_{i}'] = {
                'volatility_mean': regime_vol.mean(),
                'volatility_std': regime_vol.std(),
                'duration_mean': self._calculate_regime_duration(regime_labels, i),
                'frequency': regime_mask.sum() / len(regime_labels),
                'regime_type': self._classify_regime(regime_vol.mean())
            }
        
        # Create regime time series
        regime_series = pd.Series(regime_labels, index=features.index)
        
        results = {
            'regime_labels': regime_labels.tolist(),
            'regime_series': regime_series,
            'regime_analysis': regime_analysis,
            'current_regime': regime_labels[-1] if len(regime_labels) > 0 else None,
            'detection_method': 'volatility_clustering',
            'n_regimes': n_regimes
        }
        
        # Store regime history
        self.regime_history.append({
            'timestamp': datetime.now(),
            'method': 'volatility_clustering',
            'current_regime': results['current_regime'],
            'regime_analysis': regime_analysis
        })
        
        self.current_regime = results['current_regime']
        
        logger.info(f"Volatility regime detection completed: {n_regimes} regimes identified")
        return results
    
    def detect_regimes_momentum(self, data: pd.DataFrame, window: int = 20) -> Dict:
        """Detect market regimes based on momentum indicators"""
        
        if len(data) < window * 2:
            logger.warning(f"Insufficient data for momentum regime detection: {len(data)} < {window * 2}")
            return {}
        
        # Calculate momentum indicators
        returns = data['close'].pct_change().dropna()
        
        features = pd.DataFrame({
            'momentum_5d': returns.rolling(5).sum(),
            'momentum_10d': returns.rolling(10).sum(),
            'momentum_20d': returns.rolling(20).sum(),
            'rsi': self._calculate_rsi(data['close'], 14),
            'price_position': (data['close'] - data['close'].rolling(20).min()) / 
                             (data['close'].rolling(20).max() - data['close'].rolling(20).min())
        }).dropna()
        
        # Define regime thresholds
        regime_labels = np.zeros(len(features))
        
        # Bull market: high momentum, high RSI, high price position
        bull_mask = (features['momentum_20d'] > 0.05) & (features['rsi'] > 60) & (features['price_position'] > 0.7)
        regime_labels[bull_mask] = 2  # Bull regime
        
        # Bear market: negative momentum, low RSI, low price position
        bear_mask = (features['momentum_20d'] < -0.05) & (features['rsi'] < 40) & (features['price_position'] < 0.3)
        regime_labels[bear_mask] = 0  # Bear regime
        
        # Sideways market: everything else
        regime_labels[(regime_labels != 2) & (regime_labels != 0)] = 1  # Sideways regime
        
        # Analyze regimes
        regime_analysis = {}
        regime_names = {0: 'bear', 1: 'sideways', 2: 'bull'}
        
        for regime_id, regime_name in regime_names.items():
            regime_mask = regime_labels == regime_id
            if regime_mask.sum() > 0:
                regime_data = features[regime_mask]
                
                regime_analysis[regime_name] = {
                    'momentum_mean': regime_data['momentum_20d'].mean(),
                    'rsi_mean': regime_data['rsi'].mean(),
                    'price_position_mean': regime_data['price_position'].mean(),
                    'duration_mean': self._calculate_regime_duration(regime_labels, regime_id),
                    'frequency': regime_mask.sum() / len(regime_labels)
                }
        
        # Create regime time series
        regime_series = pd.Series(regime_labels, index=features.index)
        
        results = {
            'regime_labels': regime_labels.tolist(),
            'regime_series': regime_series,
            'regime_analysis': regime_analysis,
            'current_regime': regime_labels[-1] if len(regime_labels) > 0 else None,
            'detection_method': 'momentum_indicators',
            'n_regimes': 3
        }
        
        # Store regime history
        self.regime_history.append({
            'timestamp': datetime.now(),
            'method': 'momentum_indicators',
            'current_regime': results['current_regime'],
            'regime_analysis': regime_analysis
        })
        
        self.current_regime = results['current_regime']
        
        logger.info(f"Momentum regime detection completed: {len(regime_analysis)} regimes identified")
        return results
    
    def _calculate_rsi(self, prices: pd.Series, window: int = 14) -> pd.Series:
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_regime_duration(self, regime_labels: np.ndarray, regime_id: int) -> float:
        """Calculate average duration of a regime"""
        durations = []
        current_duration = 0
        
        for label in regime_labels:
            if label == regime_id:
                current_duration += 1
            elif current_duration > 0:
                durations.append(current_duration)
                current_duration = 0
        
        if current_duration > 0:
            durations.append(current_duration)
        
        return np.mean(durations) if durations else 0
    
    def _classify_regime(self, volatility: float) -> str:
        """Classify regime based on volatility level"""
        if volatility < 0.01:
            return 'low_volatility'
        elif volatility < 0.02:
            return 'medium_volatility'
        else:
            return 'high_volatility'
    
    def get_regime_summary(self) -> Dict:
        """Get regime detection summary"""
        return {
            'current_regime': self.current_regime,
            'regime_history_count': len(self.regime_history),
            'detection_methods': list(set(r['method'] for r in self.regime_history))
        }
