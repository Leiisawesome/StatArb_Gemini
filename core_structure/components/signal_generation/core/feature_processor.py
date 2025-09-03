"""
Consolidated Feature Processor
=============================

Unified feature engineering combining:
- Technical indicators (from feature_engine.py)
- Market microstructure features
- Statistical and regime-aware features
- Performance-optimized feature computation

This module consolidates feature engineering functionality from:
- feature_engine.py (776 lines)
- indicators/feature_engineering.py
- indicators/technical_indicators.py

Author: GitHub Copilot Architecture Simplification
Version: 4.0 (Consolidated)
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
import asyncio
import time
from collections import defaultdict, deque

# External dependencies with graceful fallback
try:
    import ta
    TA_AVAILABLE = True
except ImportError:
    TA_AVAILABLE = False

try:
    from sklearn.preprocessing import StandardScaler, RobustScaler, MinMaxScaler
    from sklearn.feature_selection import SelectKBest, f_classif
    from sklearn.decomposition import PCA
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    from scipy import stats
    from scipy.signal import find_peaks
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)

class FeatureType(Enum):
    """Feature categories"""
    TECHNICAL = "technical"
    STATISTICAL = "statistical"
    MICROSTRUCTURE = "microstructure"
    REGIME = "regime"
    ALTERNATIVE = "alternative"
    CUSTOM = "custom"

class FeatureQuality(Enum):
    """Feature quality indicators"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INVALID = "invalid"

@dataclass
class FeatureConfig:
    """Configuration for feature engineering"""
    # Technical indicators
    enable_technical: bool = True
    rsi_periods: List[int] = field(default_factory=lambda: [14, 21])
    ma_periods: List[int] = field(default_factory=lambda: [5, 10, 20, 50])
    bollinger_periods: List[int] = field(default_factory=lambda: [20])
    
    # Statistical features
    enable_statistical: bool = True
    lookback_windows: List[int] = field(default_factory=lambda: [5, 10, 20, 60])
    autocorr_lags: List[int] = field(default_factory=lambda: [1, 5, 10])
    
    # Market microstructure
    enable_microstructure: bool = True
    volume_windows: List[int] = field(default_factory=lambda: [5, 20])
    tick_features: bool = True
    
    # Feature processing
    standardize_features: bool = True
    remove_outliers: bool = True
    outlier_threshold: float = 3.0
    
    # Performance optimization
    cache_features: bool = True
    parallel_computation: bool = True
    max_features: int = 50

@dataclass
class FeatureSet:
    """Container for computed features with metadata"""
    features: Dict[str, float]
    feature_types: Dict[str, FeatureType]
    quality_scores: Dict[str, FeatureQuality]
    computation_time: float
    timestamp: datetime
    
    def get_features_by_type(self, feature_type: FeatureType) -> Dict[str, float]:
        """Get features of specific type"""
        return {
            name: value for name, value in self.features.items()
            if self.feature_types.get(name) == feature_type
        }
    
    def get_high_quality_features(self) -> Dict[str, float]:
        """Get only high quality features"""
        return {
            name: value for name, value in self.features.items()
            if self.quality_scores.get(name) == FeatureQuality.HIGH
        }

class FeatureProcessor:
    """
    Consolidated Feature Processing Engine
    
    Unified feature engineering combining technical analysis,
    statistical features, and market microstructure indicators.
    """
    
    def __init__(self, config: Optional[FeatureConfig] = None):
        """Initialize feature processor"""
        self.config = config or FeatureConfig()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Feature cache for performance
        self._feature_cache = {}
        self._cache_ttl = 300  # 5 minutes
        
        # Initialize scalers if sklearn available
        if SKLEARN_AVAILABLE:
            self.scaler = RobustScaler()
            self.feature_selector = SelectKBest(f_classif, k=self.config.max_features)
        else:
            self.scaler = None
            self.feature_selector = None
        
        self.logger.info(f"FeatureProcessor initialized with {len(self._get_available_features())} available features")
    
    def extract_features(self, market_data: pd.DataFrame, 
                        symbol: Optional[str] = None) -> Dict[str, float]:
        """
        Extract comprehensive feature set from market data
        
        Args:
            market_data: OHLCV market data
            symbol: Optional symbol for caching
            
        Returns:
            Dictionary of computed features
        """
        start_time = time.time()
        
        try:
            # Check cache first
            if symbol and self.config.cache_features:
                cached_features = self._get_cached_features(symbol, market_data)
                if cached_features:
                    return cached_features
            
            # Validate input data
            if not self._validate_market_data(market_data):
                return {}
            
            features = {}
            
            # Extract different feature types
            if self.config.enable_technical:
                technical_features = self._extract_technical_features(market_data)
                features.update(technical_features)
            
            if self.config.enable_statistical:
                statistical_features = self._extract_statistical_features(market_data)
                features.update(statistical_features)
            
            if self.config.enable_microstructure:
                microstructure_features = self._extract_microstructure_features(market_data)
                features.update(microstructure_features)
            
            # Post-process features
            features = self._post_process_features(features)
            
            # Cache results
            if symbol and self.config.cache_features:
                self._cache_features(symbol, features, market_data)
            
            computation_time = time.time() - start_time
            self.logger.debug(f"Extracted {len(features)} features in {computation_time:.3f}s")
            
            return features
            
        except Exception as e:
            self.logger.error(f"Error extracting features: {e}")
            return {}
    
    def extract_feature_set(self, market_data: pd.DataFrame, 
                           symbol: Optional[str] = None) -> FeatureSet:
        """Extract features with full metadata"""
        start_time = time.time()
        
        features = self.extract_features(market_data, symbol)
        
        # Determine feature types and quality
        feature_types = self._classify_features(features)
        quality_scores = self._assess_feature_quality(features, market_data)
        
        return FeatureSet(
            features=features,
            feature_types=feature_types,
            quality_scores=quality_scores,
            computation_time=time.time() - start_time,
            timestamp=datetime.now()
        )
    
    def _validate_market_data(self, market_data: pd.DataFrame) -> bool:
        """Validate market data for feature extraction"""
        if market_data.empty:
            return False
        
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in market_data.columns for col in required_columns):
            self.logger.warning("Missing required OHLCV columns")
            return False
        
        if len(market_data) < 2:
            self.logger.warning("Insufficient data points for feature extraction")
            return False
        
        return True
    
    def _extract_technical_features(self, market_data: pd.DataFrame) -> Dict[str, float]:
        """Extract technical analysis features"""
        features = {}
        
        try:
            # Price-based features
            close = market_data['close']
            high = market_data['high']
            low = market_data['low']
            volume = market_data['volume']
            
            # Returns
            returns = close.pct_change()
            features['returns_1d'] = float(returns.iloc[-1]) if not pd.isna(returns.iloc[-1]) else 0.0
            features['returns_5d'] = float(returns.rolling(5).sum().iloc[-1]) if len(returns) >= 5 else 0.0
            
            # Moving averages
            for period in self.config.ma_periods:
                if len(close) >= period:
                    ma = close.rolling(period).mean()
                    features[f'ma_{period}'] = float(ma.iloc[-1])
                    features[f'price_to_ma_{period}'] = float(close.iloc[-1] / ma.iloc[-1] - 1)
            
            # Volatility
            if len(returns) >= 20:
                vol_20 = returns.rolling(20).std()
                features['volatility_20d'] = float(vol_20.iloc[-1])
                features['volatility_ratio'] = float(vol_20.iloc[-1] / vol_20.mean()) if vol_20.mean() > 0 else 1.0
            
            # RSI (if TA library available)
            if TA_AVAILABLE:
                for period in self.config.rsi_periods:
                    if len(close) >= period:
                        try:
                            rsi = ta.momentum.RSIIndicator(close, window=period)
                            features[f'rsi_{period}'] = float(rsi.rsi().iloc[-1])
                        except:
                            features[f'rsi_{period}'] = 50.0
            
            # Bollinger Bands (if TA available)
            if TA_AVAILABLE:
                for period in self.config.bollinger_periods:
                    if len(close) >= period:
                        try:
                            bb = ta.volatility.BollingerBands(close, window=period)
                            bb_high = bb.bollinger_hband().iloc[-1]
                            bb_low = bb.bollinger_lband().iloc[-1]
                            bb_mid = bb.bollinger_mavg().iloc[-1]
                            current_price = close.iloc[-1]
                            
                            features[f'bb_position_{period}'] = float((current_price - bb_low) / (bb_high - bb_low)) if bb_high > bb_low else 0.5
                            features[f'bb_width_{period}'] = float((bb_high - bb_low) / bb_mid) if bb_mid > 0 else 0.0
                        except:
                            features[f'bb_position_{period}'] = 0.5
                            features[f'bb_width_{period}'] = 0.0
            
            # MACD (if TA available)
            if TA_AVAILABLE and len(close) >= 26:
                try:
                    macd = ta.trend.MACD(close)
                    features['macd'] = float(macd.macd().iloc[-1])
                    features['macd_signal'] = float(macd.macd_signal().iloc[-1])
                    features['macd_histogram'] = float(macd.macd_diff().iloc[-1])
                except:
                    features['macd'] = 0.0
                    features['macd_signal'] = 0.0
                    features['macd_histogram'] = 0.0
            
            # Volume features
            if len(volume) >= 20:
                vol_ma = volume.rolling(20).mean()
                features['volume_ratio'] = float(volume.iloc[-1] / vol_ma.iloc[-1]) if vol_ma.iloc[-1] > 0 else 1.0
                features['volume_trend'] = float(volume.rolling(5).mean().iloc[-1] / volume.rolling(20).mean().iloc[-1]) if volume.rolling(20).mean().iloc[-1] > 0 else 1.0
            
        except Exception as e:
            self.logger.warning(f"Error in technical feature extraction: {e}")
        
        return features
    
    def _extract_statistical_features(self, market_data: pd.DataFrame) -> Dict[str, float]:
        """Extract statistical features"""
        features = {}
        
        try:
            close = market_data['close']
            returns = close.pct_change().dropna()
            
            if len(returns) == 0:
                return features
            
            # Basic statistics
            features['returns_mean'] = float(returns.mean())
            features['returns_std'] = float(returns.std())
            features['returns_skew'] = float(returns.skew()) if len(returns) >= 3 else 0.0
            features['returns_kurtosis'] = float(returns.kurtosis()) if len(returns) >= 4 else 0.0
            
            # Percentiles
            if len(returns) >= 10:
                features['returns_p25'] = float(returns.quantile(0.25))
                features['returns_p75'] = float(returns.quantile(0.75))
                features['returns_iqr'] = features['returns_p75'] - features['returns_p25']
            
            # Autocorrelation
            if SCIPY_AVAILABLE:
                for lag in self.config.autocorr_lags:
                    if len(returns) > lag:
                        try:
                            autocorr = np.corrcoef(returns[:-lag], returns[lag:])[0, 1]
                            features[f'autocorr_lag_{lag}'] = float(autocorr) if not np.isnan(autocorr) else 0.0
                        except:
                            features[f'autocorr_lag_{lag}'] = 0.0
            
            # Hurst exponent (simplified calculation)
            if len(returns) >= 50:
                try:
                    cumulative_returns = np.cumsum(returns)
                    ranges = []
                    for window in [10, 20, 30]:
                        if len(cumulative_returns) >= window:
                            rolling_range = pd.Series(cumulative_returns).rolling(window).apply(
                                lambda x: np.max(x) - np.min(x)
                            ).mean()
                            ranges.append(rolling_range)
                    
                    if len(ranges) >= 2 and ranges[0] > 0 and ranges[1] > 0:
                        hurst = np.log(ranges[1] / ranges[0]) / np.log(2)
                        features['hurst_exponent'] = float(hurst)
                except:
                    features['hurst_exponent'] = 0.5
            
        except Exception as e:
            self.logger.warning(f"Error in statistical feature extraction: {e}")
        
        return features
    
    def _extract_microstructure_features(self, market_data: pd.DataFrame) -> Dict[str, float]:
        """Extract market microstructure features"""
        features = {}
        
        try:
            high = market_data['high']
            low = market_data['low']
            close = market_data['close']
            volume = market_data['volume']
            
            # Price ranges
            daily_range = high - low
            features['daily_range_pct'] = float((daily_range.iloc[-1] / close.iloc[-1]) * 100) if close.iloc[-1] > 0 else 0.0
            
            if len(daily_range) >= 20:
                range_ma = daily_range.rolling(20).mean()
                features['range_ratio'] = float(daily_range.iloc[-1] / range_ma.iloc[-1]) if range_ma.iloc[-1] > 0 else 1.0
            
            # True Range (if TA available)
            if TA_AVAILABLE and len(market_data) >= 2:
                try:
                    atr = ta.volatility.AverageTrueRange(high, low, close, window=14)
                    features['atr_14'] = float(atr.average_true_range().iloc[-1])
                    features['atr_ratio'] = float(atr.average_true_range().iloc[-1] / close.iloc[-1]) if close.iloc[-1] > 0 else 0.0
                except:
                    features['atr_14'] = float(daily_range.iloc[-1])
                    features['atr_ratio'] = features['daily_range_pct'] / 100
            
            # Volume-price features
            if len(volume) >= 5:
                # Volume-weighted average price approximation
                vwap = (close * volume).rolling(5).sum() / volume.rolling(5).sum()
                features['price_to_vwap'] = float(close.iloc[-1] / vwap.iloc[-1] - 1) if vwap.iloc[-1] > 0 else 0.0
            
            # On-balance volume (if TA available)
            if TA_AVAILABLE and len(market_data) >= 2:
                try:
                    obv = ta.volume.OnBalanceVolumeIndicator(close, volume)
                    obv_values = obv.on_balance_volume()
                    if len(obv_values) >= 5:
                        obv_change = obv_values.iloc[-1] - obv_values.iloc[-5]
                        features['obv_change_5d'] = float(obv_change)
                except:
                    features['obv_change_5d'] = 0.0
            
        except Exception as e:
            self.logger.warning(f"Error in microstructure feature extraction: {e}")
        
        return features
    
    def _post_process_features(self, features: Dict[str, float]) -> Dict[str, float]:
        """Post-process features (outlier removal, normalization)"""
        if not features:
            return features
        
        processed_features = {}
        
        for name, value in features.items():
            # Remove invalid values
            if pd.isna(value) or np.isinf(value):
                continue
            
            # Outlier detection
            if self.config.remove_outliers:
                if abs(value) > self.config.outlier_threshold * 10:  # Simple outlier check
                    continue
            
            processed_features[name] = float(value)
        
        return processed_features
    
    def _classify_features(self, features: Dict[str, float]) -> Dict[str, FeatureType]:
        """Classify features by type"""
        feature_types = {}
        
        for name in features.keys():
            if any(keyword in name for keyword in ['ma_', 'rsi_', 'bb_', 'macd']):
                feature_types[name] = FeatureType.TECHNICAL
            elif any(keyword in name for keyword in ['returns_', 'volatility', 'skew', 'kurtosis', 'autocorr', 'hurst']):
                feature_types[name] = FeatureType.STATISTICAL
            elif any(keyword in name for keyword in ['volume', 'range', 'atr', 'vwap', 'obv']):
                feature_types[name] = FeatureType.MICROSTRUCTURE
            else:
                feature_types[name] = FeatureType.CUSTOM
        
        return feature_types
    
    def _assess_feature_quality(self, features: Dict[str, float], 
                               market_data: pd.DataFrame) -> Dict[str, FeatureQuality]:
        """Assess quality of computed features"""
        quality_scores = {}
        
        for name, value in features.items():
            # Basic quality assessment
            if pd.isna(value) or np.isinf(value):
                quality_scores[name] = FeatureQuality.INVALID
            elif abs(value) > 100:  # Likely outlier
                quality_scores[name] = FeatureQuality.LOW
            elif len(market_data) >= 50:  # Sufficient data
                quality_scores[name] = FeatureQuality.HIGH
            elif len(market_data) >= 20:  # Moderate data
                quality_scores[name] = FeatureQuality.MEDIUM
            else:  # Insufficient data
                quality_scores[name] = FeatureQuality.LOW
        
        return quality_scores
    
    def _get_cached_features(self, symbol: str, market_data: pd.DataFrame) -> Optional[Dict[str, float]]:
        """Get cached features if available and valid"""
        cache_key = f"{symbol}_{hash(str(market_data.iloc[-1].to_dict()))}"
        
        if cache_key in self._feature_cache:
            cached_features, timestamp = self._feature_cache[cache_key]
            if (datetime.now() - timestamp).total_seconds() < self._cache_ttl:
                return cached_features
            else:
                del self._feature_cache[cache_key]
        
        return None
    
    def _cache_features(self, symbol: str, features: Dict[str, float], market_data: pd.DataFrame):
        """Cache computed features"""
        cache_key = f"{symbol}_{hash(str(market_data.iloc[-1].to_dict()))}"
        self._feature_cache[cache_key] = (features.copy(), datetime.now())
        
        # Cleanup old cache entries
        if len(self._feature_cache) > 1000:
            old_keys = list(self._feature_cache.keys())[:100]
            for key in old_keys:
                del self._feature_cache[key]
    
    def _get_available_features(self) -> List[str]:
        """Get list of available feature types"""
        features = []
        
        if self.config.enable_technical:
            features.extend(['returns', 'moving_averages', 'rsi', 'bollinger_bands', 'macd', 'volume'])
        
        if self.config.enable_statistical:
            features.extend(['statistical_moments', 'autocorrelation', 'hurst_exponent'])
        
        if self.config.enable_microstructure:
            features.extend(['price_ranges', 'atr', 'vwap', 'obv'])
        
        return features
    
    def get_feature_importance(self, features: Dict[str, float], 
                             target: Optional[np.ndarray] = None) -> Dict[str, float]:
        """Get feature importance scores (requires target for supervised methods)"""
        if not SKLEARN_AVAILABLE or not features:
            return {}
        
        try:
            # For now, return equal importance
            # In practice, this would use feature selection methods
            return {name: 1.0 / len(features) for name in features.keys()}
        except Exception as e:
            self.logger.warning(f"Feature importance calculation failed: {e}")
            return {}

# Export consolidated feature processor
FeatureEngine = FeatureProcessor  # Backward compatibility alias

__all__ = [
    'FeatureProcessor',
    'FeatureEngine',  # Backward compatibility
    'FeatureSet',
    'FeatureConfig',
    'FeatureType',
    'FeatureQuality'
]
