"""
Unified Signal Engine - Core Signal Generation
==============================================

Consolidated signal generation engine combining:
- Core signal generation logic (from signal_generator.py)
- Signal processing and validation
- Risk-aware signal filtering
- Performance monitoring and metrics

This module replaces the overly complex signal_generator.py (1,504 lines)
with a focused, maintainable core engine.

Author: GitHub Copilot Architecture Simplification
Version: 4.0 (Consolidated)
"""

import asyncio
import logging
import threading
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional, Union, Tuple
import pandas as pd
import numpy as np

# Core infrastructure imports  
try:
    from core_structure.infrastructure.config import UnifiedConfigManager as ConfigManager
    from core_structure.infrastructure.message_bus import MessageBus
    from core_structure.infrastructure.metrics_collector import MetricsCollector
    from core_structure.infrastructure.database_layer import DatabaseClient
except ImportError:
    # Fallback for testing
    ConfigManager = None
    MessageBus = None
    MetricsCollector = None
    DatabaseClient = None

# Import consolidated optimization modules
try:
    from ..optimization.portfolio_optimizer import PortfolioOptimizationEngine, OptimizationConfig
    from ..optimization.timing_engine import TimingEngine, TimingConfig
    OPTIMIZATION_AVAILABLE = True
except ImportError:
    OPTIMIZATION_AVAILABLE = False

# Market data imports
try:
    from ...market_data import DataManager
    from ...market_data.feeds import MarketTick, DataType
except ImportError:
    DataManager = None
    MarketTick = None
    DataType = None

# External dependencies with graceful fallback
try:
    import ta
    from sklearn.preprocessing import StandardScaler, RobustScaler
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score
    from scipy import stats
    from scipy.optimize import minimize
    TA_AVAILABLE = True
    SKLEARN_AVAILABLE = True
    SCIPY_AVAILABLE = True
except ImportError:
    TA_AVAILABLE = False
    SKLEARN_AVAILABLE = False
    SCIPY_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)

class SignalType(Enum):
    """Trading signal types with direction"""
    LONG = 1
    SHORT = -1
    NEUTRAL = 0
    EXIT = 99

class SignalStrength(Enum):
    """Signal strength classification"""
    VERY_STRONG = 5
    STRONG = 4
    MODERATE = 3
    WEAK = 2
    VERY_WEAK = 1

@dataclass
class SignalConfig:
    """Configuration for signal generation engine"""
    # Core signal parameters
    min_confidence_threshold: float = 0.35
    max_position_size: float = 0.15
    lookback_period: int = 60
    
    # Risk management
    enable_risk_filtering: bool = True
    max_correlation: float = 0.7
    max_portfolio_heat: float = 0.5
    
    # Performance optimization
    enable_caching: bool = True
    cache_ttl_seconds: int = 300
    signal_cache_ttl: int = 300
    parallel_processing: bool = True
    max_workers: int = 4
    max_parallel_symbols: int = 8
    
    # Feature engineering
    enable_feature_engineering: bool = True
    feature_selection: bool = True
    max_features: int = 50
    
    # Advanced signal processing
    enable_ml_enhancement: bool = True
    enable_regime_detection: bool = True
    enable_adaptive_thresholds: bool = True
    enable_kalman_filtering: bool = True
    
    # Optimization parameters
    enable_parameter_optimization: bool = True
    optimization_frequency: int = 100
    lookback_optimization: int = 500
    
    # Signal validation
    enable_validation: bool = True
    min_data_points: int = 20
    outlier_detection: bool = True

@dataclass
class TradingSignal:
    """Enhanced trading signal with comprehensive metadata"""
    symbol: str
    signal_type: SignalType
    strength: SignalStrength
    confidence: float
    timestamp: datetime
    
    # Price and sizing
    entry_price: Optional[float] = None
    position_size: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    # Features and context
    features: Optional[Dict[str, float]] = None
    regime: Optional[str] = None
    regime_confidence: Optional[float] = None
    
    # Risk metrics
    expected_return: Optional[float] = None
    expected_risk: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    
    # Model attribution
    model_id: Optional[str] = None
    model_version: Optional[str] = None
    feature_importance: Optional[Dict[str, float]] = None
    
    # Metadata
    signal_id: str = field(default_factory=lambda: f"sig_{int(time.time() * 1000)}")
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert signal to dictionary for serialization"""
        return {
            'signal_id': self.signal_id,
            'symbol': self.symbol,
            'signal_type': self.signal_type.name if isinstance(self.signal_type, SignalType) else str(self.signal_type),
            'strength': self.strength.name if isinstance(self.strength, SignalStrength) else str(self.strength),
            'confidence': self.confidence,
            'timestamp': self.timestamp.isoformat(),
            'entry_price': self.entry_price,
            'position_size': self.position_size,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'features': self.features,
            'regime': self.regime,
            'regime_confidence': self.regime_confidence,
            'expected_return': self.expected_return,
            'expected_risk': self.expected_risk,
            'sharpe_ratio': self.sharpe_ratio,
            'model_id': self.model_id,
            'model_version': self.model_version,
            'feature_importance': self.feature_importance,
            'created_at': self.created_at.isoformat()
        }

@dataclass
class SignalMetrics:
    """Signal generation performance metrics"""
    signals_generated: int = 0
    successful_signals: int = 0
    failed_signals: int = 0
    avg_confidence: float = 0.0
    avg_generation_time: float = 0.0
    avg_sharpe_ratio: float = 0.0
    cache_hit_rate: float = 0.0
    last_update: datetime = field(default_factory=datetime.now)
    
    def success_rate(self) -> float:
        """Calculate signal generation success rate"""
        if self.signals_generated == 0:
            return 0.0
        return self.successful_signals / self.signals_generated
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
            'signals_generated': self.signals_generated,
            'successful_signals': self.successful_signals,
            'failed_signals': self.failed_signals,
            'success_rate': self.success_rate(),
            'avg_confidence': self.avg_confidence,
            'avg_generation_time': self.avg_generation_time,
            'avg_sharpe_ratio': self.avg_sharpe_ratio,
            'cache_hit_rate': self.cache_hit_rate,
            'last_update': self.last_update.isoformat()
        }

class UnifiedSignalEngine:
    """
    Unified Signal Generation Engine
    
    Consolidated core signal generation functionality combining:
    - Signal generation and validation
    - Risk-aware filtering
    - Performance optimization
    - Comprehensive monitoring
    """
    
    def __init__(self, config: Optional[SignalConfig] = None):
        """Initialize unified signal engine"""
        self.config = config or SignalConfig()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Core components
        self._initialize_components()
        
        # Performance tracking
        self.performance_metrics = {
            'signals_generated': 0,
            'signals_filtered': 0,
            'avg_confidence': 0.0,
            'avg_processing_time': 0.0,
            'last_update': datetime.now()
        }
        
        # Caching and optimization
        self._signal_cache = {}
        self._feature_cache = {}
        self._lock = threading.Lock()
        
        # Initialize optimization components
        if self.config.enable_feature_engineering:
            try:
                from ..core.feature_processor import FeatureProcessor
                self.feature_processor = FeatureProcessor()
            except ImportError:
                self.logger.warning("FeatureProcessor not available - using basic features")
                self.feature_processor = None
        
        self.logger.info(f"UnifiedSignalEngine initialized with config: min_confidence={self.config.min_confidence_threshold}, max_position_size={self.config.max_position_size}")
    
    def _initialize_components(self):
        """Initialize core signal generation components"""
        # Portfolio optimization
        if OPTIMIZATION_AVAILABLE and self.config.enable_risk_filtering:
            try:
                optimization_config = OptimizationConfig(
                    max_position_size=0.1,
                    target_volatility=0.15
                )
                self.portfolio_optimizer = PortfolioOptimizationEngine(optimization_config)
            except Exception as e:
                self.logger.warning(f"Portfolio optimizer initialization failed: {e}")
                self.portfolio_optimizer = None
        else:
            self.portfolio_optimizer = None
        
        # Timing optimization
        if OPTIMIZATION_AVAILABLE:
            try:
                timing_config = TimingConfig()
                self.timing_engine = TimingEngine(timing_config)
            except Exception as e:
                self.logger.warning(f"Timing engine initialization failed: {e}")
                self.timing_engine = None
        else:
            self.timing_engine = None
        
        # Infrastructure services
        self._initialize_infrastructure()
    
    def _initialize_infrastructure(self):
        """Initialize infrastructure services"""
        try:
            if ConfigManager:
                self.config_manager = ConfigManager()
            if MessageBus:
                self.message_bus = MessageBus()
            if MetricsCollector:
                self.metrics_collector = MetricsCollector()
        except Exception as e:
            self.logger.warning(f"Infrastructure initialization failed: {e}")
    
    def generate_signal(self, symbol: str, market_data: pd.DataFrame, 
                       features: Optional[Dict[str, float]] = None,
                       regime_info: Optional[Dict[str, Any]] = None) -> Optional[TradingSignal]:
        """
        Generate trading signal for a symbol
        
        Args:
            symbol: Trading symbol
            market_data: Historical market data
            features: Pre-computed features (optional)
            regime_info: Market regime information (optional)
            
        Returns:
            Trading signal or None if no signal generated
        """
        start_time = time.time()
        
        try:
            # Validate inputs
            if not self._validate_inputs(symbol, market_data):
                return None
            
            # Check cache first
            if self.config.enable_caching:
                cached_signal = self._get_cached_signal(symbol, market_data)
                if cached_signal:
                    return cached_signal
            
            # Extract or compute features
            if features is None and self.feature_processor:
                features = self.feature_processor.extract_features(market_data)
            elif features is None:
                features = self._extract_basic_features(market_data)
            
            # Generate core signal
            signal = self._generate_core_signal(symbol, market_data, features, regime_info)
            
            if signal:
                # Apply risk filtering
                if self.config.enable_risk_filtering and not self._pass_risk_filter(signal):
                    self.performance_metrics['signals_filtered'] += 1
                    return None
                
                # Optimize timing and position size
                signal = self._optimize_signal(signal, market_data)
                
                # Cache signal
                if self.config.enable_caching:
                    self._cache_signal(symbol, signal)
                
                # Update metrics
                self._update_performance_metrics(signal, time.time() - start_time)
                
                self.logger.debug(f"Generated signal for {symbol}: {signal.signal_type.name} "
                                f"(confidence: {signal.confidence:.3f}, strength: {signal.strength.name})")
            
            return signal
            
        except Exception as e:
            self.logger.error(f"Error generating signal for {symbol}: {e}")
            return None
    
    def _validate_inputs(self, symbol: str, market_data: pd.DataFrame) -> bool:
        """Validate signal generation inputs"""
        if not symbol or market_data.empty:
            return False
        
        if len(market_data) < self.config.min_data_points:
            self.logger.debug(f"Insufficient data for {symbol}: {len(market_data)} < {self.config.min_data_points}")
            return False
        
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in market_data.columns for col in required_columns):
            self.logger.warning(f"Missing required columns for {symbol}")
            return False
        
        return True
    
    def _extract_basic_features(self, market_data: pd.DataFrame) -> Dict[str, float]:
        """Extract enhanced technical features with advanced indicators"""
        try:
            latest = market_data.iloc[-1]
            prices = market_data['close']
            
            features = {
                'price': float(latest['close']),
                'volume': float(latest['volume']),
                'returns_1d': float((latest['close'] / market_data.iloc[-2]['close'] - 1)) if len(market_data) > 1 else 0.0,
                'volatility_20d': float(market_data['close'].pct_change().rolling(20).std().iloc[-1]) if len(market_data) >= 20 else 0.0,
            }
            
            # Enhanced technical indicators
            if len(market_data) >= 20:
                # Multiple timeframe analysis
                for period in [5, 10, 20, 50]:
                    if len(prices) >= period:
                        sma = prices.rolling(period).mean().iloc[-1]
                        features[f'sma_{period}'] = float(sma)
                        features[f'price_to_sma_{period}'] = float(latest['close'] / sma - 1) if sma > 0 else 0.0
                
                # Bollinger Bands
                if len(prices) >= 20:
                    sma_20 = prices.rolling(20).mean()
                    std_20 = prices.rolling(20).std()
                    bb_upper = (sma_20 + 2 * std_20).iloc[-1]
                    bb_lower = (sma_20 - 2 * std_20).iloc[-1]
                    bb_position = (latest['close'] - bb_lower) / (bb_upper - bb_lower) if bb_upper != bb_lower else 0.5
                    features['bollinger_position'] = float(bb_position)
                
                # Enhanced volatility measures
                returns = prices.pct_change().dropna()
                if len(returns) >= 10:
                    features['volatility_10d'] = float(returns.iloc[-10:].std())
                    features['volatility_ratio'] = float(returns.iloc[-10:].std() / returns.std()) if returns.std() > 0 else 1.0
                
                # Momentum indicators
                if len(prices) >= 10:
                    momentum_10 = (prices.iloc[-1] / prices.iloc[-10] - 1) if prices.iloc[-10] > 0 else 0.0
                    features['momentum_10d'] = float(momentum_10)
                
                # Volume analysis
                if 'volume' in market_data.columns and len(market_data) >= 20:
                    volume_sma = market_data['volume'].rolling(20).mean().iloc[-1]
                    features['volume_ratio'] = float(latest['volume'] / volume_sma) if volume_sma > 0 else 1.0
            
            # RSI with multiple periods
            if TA_AVAILABLE:
                for period in [14, 21]:
                    if len(market_data) >= period:
                        try:
                            rsi = ta.momentum.RSIIndicator(market_data['close'], window=period)
                            features[f'rsi_{period}'] = float(rsi.rsi().iloc[-1])
                        except:
                            features[f'rsi_{period}'] = 50.0
            
            # MACD if available
            if TA_AVAILABLE and len(market_data) >= 26:
                try:
                    macd = ta.trend.MACD(market_data['close'])
                    features['macd'] = float(macd.macd().iloc[-1])
                    features['macd_signal'] = float(macd.macd_signal().iloc[-1])
                    features['macd_histogram'] = float(macd.macd_diff().iloc[-1])
                except:
                    pass
            
            # Regime detection features
            if self.config.enable_regime_detection and len(market_data) >= 50:
                regime_features = self._extract_regime_features(market_data)
                features.update(regime_features)
            
            return features
            
        except Exception as e:
            self.logger.warning(f"Error extracting enhanced features: {e}")
            return {}
    
    def _generate_core_signal(self, symbol: str, market_data: pd.DataFrame, 
                             features: Dict[str, float], 
                             regime_info: Optional[Dict[str, Any]]) -> Optional[TradingSignal]:
        """Generate enhanced core trading signal with advanced algorithms"""
        try:
            # Multi-factor signal generation
            confidence = 0.0
            signal_type = SignalType.NEUTRAL
            strength = SignalStrength.WEAK
            
            # Extract enhanced features
            returns_1d = features.get('returns_1d', 0.0)
            volatility = features.get('volatility_20d', 0.0)
            rsi_14 = features.get('rsi_14', 50.0)
            rsi_21 = features.get('rsi_21', 50.0)
            bollinger_position = features.get('bollinger_position', 0.5)
            momentum_10d = features.get('momentum_10d', 0.0)
            volume_ratio = features.get('volume_ratio', 1.0)
            
            # Enhanced signal generation with multiple factors
            signal_factors = []
            
            # Factor 1: Enhanced momentum analysis
            momentum_signal = self._calculate_momentum_factor(returns_1d, momentum_10d, volatility)
            signal_factors.append(momentum_signal)
            
            # Factor 2: Mean reversion analysis
            mean_reversion_signal = self._calculate_mean_reversion_factor(rsi_14, rsi_21, bollinger_position)
            signal_factors.append(mean_reversion_signal)
            
            # Factor 3: Volume confirmation
            volume_signal = self._calculate_volume_factor(volume_ratio, returns_1d)
            signal_factors.append(volume_signal)
            
            # Factor 4: Volatility regime adjustment
            volatility_signal = self._calculate_volatility_factor(volatility, features)
            signal_factors.append(volatility_signal)
            
            # Combine factors with adaptive weights
            if self.config.enable_adaptive_thresholds:
                weights = self._calculate_adaptive_weights(market_data, regime_info)
            else:
                weights = [0.4, 0.3, 0.2, 0.1]  # Default weights
            
            # Weighted combination of signals
            combined_signal = sum(factor * weight for factor, weight in zip(signal_factors, weights))
            confidence = abs(combined_signal)
            
            # Determine signal direction
            if combined_signal > 0.1:
                signal_type = SignalType.LONG
            elif combined_signal < -0.1:
                signal_type = SignalType.SHORT
            else:
                signal_type = SignalType.NEUTRAL
            
            # ML enhancement if enabled
            if self.config.enable_ml_enhancement and hasattr(self, '_ml_model'):
                ml_adjustment = self._apply_ml_enhancement(features, regime_info)
                confidence *= ml_adjustment
            
            # Regime-aware adjustments
            if regime_info and self.config.enable_regime_detection:
                regime_adjustment = self._apply_regime_adjustment(signal_type, regime_info)
                confidence *= regime_adjustment
            
            # Adaptive threshold adjustment
            if self.config.enable_adaptive_thresholds:
                adaptive_threshold = self._calculate_adaptive_threshold(market_data)
                if confidence < adaptive_threshold:
                    return None
            else:
                if confidence < self.config.min_confidence_threshold:
                    return None
            
            # Determine signal strength
            strength = self._determine_signal_strength(confidence, combined_signal)
            
            # Apply Kalman filtering if enabled
            if self.config.enable_kalman_filtering:
                confidence = self._apply_kalman_filter(confidence, symbol)
            
            # Create enhanced signal
            signal = TradingSignal(
                symbol=symbol,
                signal_type=signal_type,
                strength=strength,
                confidence=confidence,
                timestamp=datetime.now(),
                entry_price=features.get('price'),
                features=features,
                regime=regime_info.get('regime') if regime_info else None,
                regime_confidence=regime_info.get('confidence') if regime_info else None,
                model_id='enhanced_signal_engine',
                model_version='2.0',
                feature_importance={
                    'momentum': signal_factors[0] * weights[0],
                    'mean_reversion': signal_factors[1] * weights[1],
                    'volume': signal_factors[2] * weights[2],
                    'volatility': signal_factors[3] * weights[3]
                }
            )
            
            return signal
            
        except Exception as e:
            self.logger.error(f"Error in enhanced signal generation for {symbol}: {e}")
            return None
    
    def _pass_risk_filter(self, signal: TradingSignal) -> bool:
        """Apply risk filtering to signal"""
        if not self.risk_optimizer:
            return True
        
        try:
            # Basic risk checks
            if signal.confidence < self.config.min_confidence_threshold:
                return False
            
            # Portfolio-level risk checks would go here
            # (requires portfolio state which is not available in this context)
            
            return True
            
        except Exception as e:
            self.logger.warning(f"Risk filter error: {e}")
            return True  # Default to allow signal
    
    def _optimize_signal(self, signal: TradingSignal, market_data: pd.DataFrame) -> TradingSignal:
        """Optimize signal timing and position sizing"""
        try:
            # Position sizing
            if self.position_sizer and signal.entry_price:
                position_size = self.position_sizer.calculate_position_size(
                    signal.symbol,
                    signal.entry_price,
                    signal.confidence,
                    signal.features or {}
                )
                signal.position_size = min(position_size, self.config.max_position_size)
            
            # Stop loss and take profit levels
            if signal.entry_price and len(market_data) > 20:
                atr = market_data['high'].rolling(20).max() - market_data['low'].rolling(20).min()
                avg_atr = atr.rolling(20).mean().iloc[-1]
                
                if signal.signal_type == SignalType.LONG:
                    signal.stop_loss = signal.entry_price * (1 - 0.02)  # 2% stop
                    signal.take_profit = signal.entry_price * (1 + 0.04)  # 4% target
                elif signal.signal_type == SignalType.SHORT:
                    signal.stop_loss = signal.entry_price * (1 + 0.02)
                    signal.take_profit = signal.entry_price * (1 - 0.04)
            
            return signal
            
        except Exception as e:
            self.logger.warning(f"Signal optimization error: {e}")
            return signal
    
    def _get_cached_signal(self, symbol: str, market_data: pd.DataFrame) -> Optional[TradingSignal]:
        """Get cached signal if available and valid"""
        with self._lock:
            cache_key = f"{symbol}_{hash(str(market_data.iloc[-1].to_dict()))}"
            
            if cache_key in self._signal_cache:
                cached_signal, timestamp = self._signal_cache[cache_key]
                if (datetime.now() - timestamp).total_seconds() < self.config.cache_ttl_seconds:
                    return cached_signal
                else:
                    del self._signal_cache[cache_key]
        
        return None
    
    def _cache_signal(self, symbol: str, signal: TradingSignal):
        """Cache signal for future use"""
        with self._lock:
            cache_key = f"{symbol}_{hash(str(signal.features))}"
            self._signal_cache[cache_key] = (signal, datetime.now())
            
            # Cleanup old cache entries
            if len(self._signal_cache) > 1000:
                old_keys = list(self._signal_cache.keys())[:100]
                for key in old_keys:
                    del self._signal_cache[key]
    
    def _update_performance_metrics(self, signal: TradingSignal, processing_time: float):
        """Update performance tracking metrics"""
        self.performance_metrics['signals_generated'] += 1
        
        # Rolling average of confidence
        total_signals = self.performance_metrics['signals_generated']
        old_avg_confidence = self.performance_metrics['avg_confidence']
        self.performance_metrics['avg_confidence'] = (
            (old_avg_confidence * (total_signals - 1) + signal.confidence) / total_signals
        )
        
        # Rolling average of processing time
        old_avg_time = self.performance_metrics['avg_processing_time']
        self.performance_metrics['avg_processing_time'] = (
            (old_avg_time * (total_signals - 1) + processing_time) / total_signals
        )
        
        self.performance_metrics['last_update'] = datetime.now()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        return self.performance_metrics.copy()
    
    def reset_cache(self):
        """Reset all caches"""
        with self._lock:
            self._signal_cache.clear()
            self._feature_cache.clear()
        self.logger.info("Signal caches reset")
    
    def _extract_regime_features(self, market_data: pd.DataFrame) -> Dict[str, float]:
        """Extract market regime detection features"""
        try:
            prices = market_data['close']
            returns = prices.pct_change().dropna()
            
            regime_features = {}
            
            # Volatility regime indicators
            if len(returns) >= 20:
                short_vol = returns.iloc[-10:].std()
                long_vol = returns.iloc[-20:].std()
                regime_features['vol_regime_ratio'] = float(short_vol / long_vol) if long_vol > 0 else 1.0
            
            # Trend strength
            if len(prices) >= 50:
                short_ma = prices.iloc[-20:].mean()
                long_ma = prices.iloc[-50:].mean()
                regime_features['trend_strength'] = float((short_ma - long_ma) / long_ma) if long_ma > 0 else 0.0
            
            # Mean reversion tendency
            if len(returns) >= 30:
                autocorr = returns.iloc[-30:].autocorr() if len(returns) >= 30 else 0
                regime_features['mean_reversion_tendency'] = float(autocorr) if not pd.isna(autocorr) else 0.0
            
            return regime_features
            
        except Exception as e:
            self.logger.warning(f"Regime feature extraction failed: {e}")
            return {}
    
    def _calculate_momentum_factor(self, returns_1d: float, momentum_10d: float, volatility: float) -> float:
        """Calculate momentum factor for signal generation"""
        try:
            # Combine short and medium term momentum
            momentum_score = 0.0
            
            # Short-term momentum (1-day)
            if abs(returns_1d) > 0.001:
                momentum_score += returns_1d * 5  # Scale up
            
            # Medium-term momentum (10-day)
            if abs(momentum_10d) > 0.01:
                momentum_score += momentum_10d * 2
            
            # Volatility adjustment
            if volatility > 0.02:  # High volatility
                momentum_score *= 0.8
            
            return max(min(momentum_score, 1.0), -1.0)  # Bound between -1 and 1
            
        except Exception:
            return 0.0
    
    def _calculate_mean_reversion_factor(self, rsi_14: float, rsi_21: float, bollinger_position: float) -> float:
        """Calculate mean reversion factor for signal generation"""
        try:
            reversion_score = 0.0
            
            # RSI-based mean reversion
            avg_rsi = (rsi_14 + rsi_21) / 2
            if avg_rsi < 30:
                reversion_score += (30 - avg_rsi) / 30  # Oversold -> positive (buy signal)
            elif avg_rsi > 70:
                reversion_score -= (avg_rsi - 70) / 30  # Overbought -> negative (sell signal)
            
            # Bollinger Band position
            if bollinger_position < 0.2:
                reversion_score += (0.2 - bollinger_position) * 2  # Near lower band -> buy
            elif bollinger_position > 0.8:
                reversion_score -= (bollinger_position - 0.8) * 2  # Near upper band -> sell
            
            return max(min(reversion_score, 1.0), -1.0)
            
        except Exception:
            return 0.0
    
    def _calculate_volume_factor(self, volume_ratio: float, returns_1d: float) -> float:
        """Calculate volume confirmation factor"""
        try:
            volume_score = 0.0
            
            # Volume confirmation of price moves
            if volume_ratio > 1.2 and abs(returns_1d) > 0.005:
                # High volume confirms price movement
                volume_score = returns_1d * (volume_ratio - 1.0)
            elif volume_ratio < 0.8:
                # Low volume weakens signals
                volume_score = returns_1d * -0.2
            
            return max(min(volume_score, 0.5), -0.5)  # Smaller impact
            
        except Exception:
            return 0.0
    
    def _calculate_volatility_factor(self, volatility: float, features: Dict[str, float]) -> float:
        """Calculate volatility regime factor"""
        try:
            vol_ratio = features.get('volatility_ratio', 1.0)
            
            # Volatility regime adjustment
            if vol_ratio > 1.5:  # High volatility regime
                return -0.2  # Reduce signal strength
            elif vol_ratio < 0.7:  # Low volatility regime
                return 0.1   # Slightly boost signals
            else:
                return 0.0   # Neutral
                
        except Exception:
            return 0.0
    
    def _calculate_adaptive_weights(self, market_data: pd.DataFrame, regime_info: Optional[Dict[str, Any]]) -> List[float]:
        """Calculate adaptive weights based on market conditions"""
        try:
            # Default weights
            weights = [0.4, 0.3, 0.2, 0.1]  # [momentum, mean_reversion, volume, volatility]
            
            # Adjust based on regime
            if regime_info:
                regime = regime_info.get('regime', 'unknown')
                
                if regime == 'trending':
                    weights = [0.6, 0.2, 0.15, 0.05]  # Boost momentum
                elif regime == 'mean_reverting':
                    weights = [0.2, 0.6, 0.15, 0.05]  # Boost mean reversion
                elif regime == 'volatile':
                    weights = [0.3, 0.3, 0.3, 0.1]    # Balanced with more volume
            
            return weights
            
        except Exception:
            return [0.4, 0.3, 0.2, 0.1]
    
    def _apply_ml_enhancement(self, features: Dict[str, float], regime_info: Optional[Dict[str, Any]]) -> float:
        """Apply ML model enhancement (placeholder for future ML integration)"""
        try:
            # Placeholder for ML model
            # In practice, this would use a trained model to adjust confidence
            
            # Simple heuristic enhancement
            enhancement = 1.0
            
            # Boost confidence if multiple indicators align
            rsi = features.get('rsi_14', 50.0)
            momentum = features.get('momentum_10d', 0.0)
            
            if (rsi < 30 and momentum > 0.02) or (rsi > 70 and momentum < -0.02):
                enhancement = 1.2  # Boost when RSI and momentum align
            
            return min(enhancement, 1.5)  # Cap enhancement
            
        except Exception:
            return 1.0
    
    def _apply_regime_adjustment(self, signal_type: SignalType, regime_info: Dict[str, Any]) -> float:
        """Apply regime-based signal adjustment"""
        try:
            regime = regime_info.get('regime', 'unknown')
            regime_confidence = regime_info.get('confidence', 0.5)
            
            if regime == 'trending' and signal_type in [SignalType.LONG, SignalType.SHORT]:
                return 1.0 + regime_confidence * 0.3  # Boost trending signals
            elif regime == 'mean_reverting':
                return 0.8  # Reduce momentum signals in mean-reverting markets
            elif regime == 'volatile':
                return 0.9  # Slightly reduce signals in volatile markets
            else:
                return 1.0
                
        except Exception:
            return 1.0
    
    def _calculate_adaptive_threshold(self, market_data: pd.DataFrame) -> float:
        """Calculate adaptive confidence threshold based on market conditions"""
        try:
            returns = market_data['close'].pct_change().dropna()
            
            if len(returns) < 20:
                return self.config.min_confidence_threshold
            
            # Adjust threshold based on recent volatility
            recent_vol = returns.iloc[-20:].std()
            avg_vol = returns.std()
            
            vol_ratio = recent_vol / avg_vol if avg_vol > 0 else 1.0
            
            # Higher volatility -> higher threshold
            adaptive_threshold = self.config.min_confidence_threshold * vol_ratio
            
            # Keep within reasonable bounds
            return max(min(adaptive_threshold, 0.8), 0.2)
            
        except Exception:
            return self.config.min_confidence_threshold
    
    def _determine_signal_strength(self, confidence: float, combined_signal: float) -> SignalStrength:
        """Determine signal strength based on confidence and signal magnitude"""
        try:
            signal_magnitude = abs(combined_signal)
            
            if confidence > 0.8 and signal_magnitude > 0.5:
                return SignalStrength.VERY_STRONG
            elif confidence > 0.65 and signal_magnitude > 0.3:
                return SignalStrength.STRONG
            elif confidence > 0.5 and signal_magnitude > 0.2:
                return SignalStrength.MODERATE
            elif confidence > 0.35:
                return SignalStrength.WEAK
            else:
                return SignalStrength.VERY_WEAK
                
        except Exception:
            return SignalStrength.WEAK
    
    def _apply_kalman_filter(self, confidence: float, symbol: str) -> float:
        """Apply Kalman filter to smooth confidence values"""
        try:
            if not hasattr(self, '_kalman_states'):
                self._kalman_states = {}
            
            if symbol not in self._kalman_states:
                self._kalman_states[symbol] = {
                    'estimate': confidence,
                    'error_covariance': 0.1,
                    'process_noise': 0.01,
                    'measurement_noise': 0.05
                }
                return confidence
            
            state = self._kalman_states[symbol]
            
            # Prediction step
            predicted_estimate = state['estimate']
            predicted_error_covariance = state['error_covariance'] + state['process_noise']
            
            # Update step
            kalman_gain = predicted_error_covariance / (predicted_error_covariance + state['measurement_noise'])
            updated_estimate = predicted_estimate + kalman_gain * (confidence - predicted_estimate)
            updated_error_covariance = (1 - kalman_gain) * predicted_error_covariance
            
            # Store updated state
            state['estimate'] = updated_estimate
            state['error_covariance'] = updated_error_covariance
            
            return updated_estimate
            
        except Exception as e:
            self.logger.warning(f"Kalman filter failed: {e}")
            return confidence

# Export consolidated signal engine
SignalGenerator = UnifiedSignalEngine  # Backward compatibility alias

__all__ = [
    'UnifiedSignalEngine',
    'SignalGenerator',  # Backward compatibility
    'TradingSignal',
    'SignalType',
    'SignalStrength',
    'SignalConfig'
]
