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
    """Signal strength classification with comparison support"""
    VERY_WEAK = 1
    WEAK = 2
    MODERATE = 3
    STRONG = 4
    VERY_STRONG = 5
    
    def __lt__(self, other):
        if isinstance(other, SignalStrength):
            return self.value < other.value
        return NotImplemented
    
    def __le__(self, other):
        if isinstance(other, SignalStrength):
            return self.value <= other.value
        return NotImplemented
    
    def __gt__(self, other):
        if isinstance(other, SignalStrength):
            return self.value > other.value
        return NotImplemented
    
    def __ge__(self, other):
        if isinstance(other, SignalStrength):
            return self.value >= other.value
        return NotImplemented

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
    enable_ml_features: bool = True
    enable_regime_detection: bool = True
    enable_adaptive_thresholds: bool = True
    enable_kalman_filtering: bool = True
    
    # Optimization parameters
    enable_parameter_optimization: bool = True
    optimization_frequency: int = 100
    lookback_optimization: int = 500
    
    # Signal validation and processing
    enable_validation: bool = True
    min_data_points: int = 20
    outlier_detection: bool = True
    signal_decay_factor: float = 0.95

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
        
        # Signal history tracking
        self.signal_history: Dict[str, List[TradingSignal]] = {}
        self.signal_count: int = 0
        
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
        else:
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
        
        # Position sizing
        self.position_sizer = None
        
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
                       regime_info: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Generate trading signal for a symbol
        
        Args:
            symbol: Trading symbol
            market_data: Historical market data
            features: Pre-computed features (optional)
            regime_info: Market regime information (optional)
            
        Returns:
            Trading signal dictionary or None if no signal generated
        """
        start_time = time.time()
        
        try:
            # Validate inputs
            if not self._validate_inputs(symbol, market_data):
                return self._default_signal_dict(symbol)
            
            # Check cache first
            if self.config.enable_caching:
                cached_signal = self._get_cached_signal(symbol, market_data)
                if cached_signal:
                    return cached_signal.to_dict() if hasattr(cached_signal, 'to_dict') else self._default_signal_dict(symbol)
            
            # Extract or compute features
            if features is None and hasattr(self, 'feature_processor') and self.feature_processor:
                features = self.feature_processor.extract_features(market_data)
            elif features is None:
                features = self._extract_basic_features(market_data)
            
            # Generate core signal
            signal = self._generate_core_signal(symbol, market_data, features, regime_info)
            
            if signal:
                # Apply risk filtering
                if self.config.enable_risk_filtering and not self._pass_risk_filter(signal):
                    self.performance_metrics['signals_filtered'] += 1
                    return self._default_signal_dict(symbol)
                
                # Optimize timing and position size
                signal = self._optimize_signal(signal, market_data)
                
                # Cache signal
                if self.config.enable_caching:
                    self._cache_signal(symbol, signal)
                
                # Update metrics
                self._update_performance_metrics(signal, time.time() - start_time)
                
                self.logger.debug(f"Generated signal for {symbol}: {signal.signal_type.name} "
                                f"(confidence: {signal.confidence:.3f}, strength: {signal.strength.name})")
                
                # Update signal history
                self.update_signal_history(signal)
                
                # Return as dictionary
                return signal.to_dict()
            
            self.logger.debug("No core signal generated")
            return self._default_signal_dict(symbol)
            
        except Exception as e:
            self.logger.error(f"Error generating signal for {symbol}: {e}")
            return self._default_signal_dict(symbol)

    def _default_signal_dict(self, symbol: str) -> Dict[str, Any]:
        """Return a default neutral signal dict for edge cases/tests"""
        return {
            'signal_id': f'def_{int(time.time()*1000)}',
            'symbol': symbol,
            'signal_type': SignalType.NEUTRAL,
            'strength': SignalStrength.WEAK,
            'confidence': 0.0,
            'timestamp': datetime.now(),
            'entry_price': None,
            'position_size': None,
            'stop_loss': None,
            'take_profit': None,
            'features': {},
            'regime': None,
            'regime_confidence': None,
            'expected_return': None,
            'expected_risk': None,
            'sharpe_ratio': None,
            'model_id': None,
            'model_version': None,
            'feature_importance': None,
            'created_at': datetime.now().isoformat()
        }
    
    def _validate_inputs(self, symbol: str, market_data: pd.DataFrame) -> bool:
        """Validate signal generation inputs"""
        if not symbol or market_data.empty:
            return False
        
        if len(market_data) < self.config.min_data_points:
            self.logger.debug(f"Insufficient data for {symbol}: {len(market_data)} < {self.config.min_data_points}")
            return False
        
        required_columns = ['high', 'low', 'close', 'volume']
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
        if not hasattr(self, 'portfolio_optimizer') or not self.portfolio_optimizer:
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
            if hasattr(self, 'position_sizer') and self.position_sizer and signal.entry_price:
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
    
    def update_signal_history(self, signal):
        """Update signal history for a symbol"""
        # Handle both TradingSignal objects and dictionaries
        if isinstance(signal, dict):
            symbol = signal.get('symbol')
        else:
            symbol = signal.symbol
            
        if symbol not in self.signal_history:
            self.signal_history[symbol] = []
        
        self.signal_history[symbol].append(signal)
        self.signal_count += 1
        
        # Keep only last 100 signals per symbol to prevent memory issues
        if len(self.signal_history[symbol]) > 100:
            self.signal_history[symbol] = self.signal_history[symbol][-100:]
    
    def get_signal_history(self, symbol: str, limit: Optional[int] = None) -> List[TradingSignal]:
        """Get signal history for a symbol"""
        if symbol not in self.signal_history:
            return []
        
        history = self.signal_history[symbol]
        if limit is not None:
            return history[-limit:]
        return history.copy()
    
    def clear_signal_history(self, symbol: Optional[str] = None):
        """Clear signal history for a symbol or all symbols"""
        if symbol is None:
            self.signal_history.clear()
        elif symbol in self.signal_history:
            self.signal_history[symbol].clear()
    
    def generate_base_signals(self, symbol: str, market_data: pd.DataFrame) -> Dict[str, Any]:
        """Generate base signals for a symbol"""
        try:
            if not self._validate_inputs(symbol, market_data):
                return {}
            
            features = self._extract_basic_features(market_data)
            signals = {}
            
            # Generate basic momentum signal
            momentum_signal = self._calculate_momentum_factor(
                features.get('returns_1d', 0.0),
                features.get('momentum_10d', 0.0),
                features.get('volatility_20d', 0.0)
            )
            
            signals['momentum'] = {
                'signal_type': SignalType.LONG if momentum_signal > 0 else SignalType.SHORT,
                'strength': SignalStrength.STRONG if abs(momentum_signal) > 0.3 else SignalStrength.MODERATE,
                'confidence': min(abs(momentum_signal), 0.95),
                'value': momentum_signal
            }
            
            # Generate mean reversion signal
            mean_reversion_signal = self._calculate_mean_reversion_factor(
                features.get('rsi_14', 50.0),
                features.get('rsi_21', 50.0),
                features.get('bollinger_position', 0.5)
            )
            
            signals['mean_reversion'] = {
                'signal_type': SignalType.LONG if mean_reversion_signal > 0 else SignalType.SHORT,
                'strength': SignalStrength.STRONG if abs(mean_reversion_signal) > 0.3 else SignalStrength.MODERATE,
                'confidence': min(abs(mean_reversion_signal), 0.95),
                'value': mean_reversion_signal
            }
            
            # Generate trend signal
            trend_signal = self.calculate_trend_signal(market_data['close'])
            
            signals['trend'] = {
                'signal_type': SignalType.LONG if trend_signal > 0 else SignalType.SHORT,
                'strength': SignalStrength.STRONG if abs(trend_signal) > 0.3 else SignalStrength.MODERATE,
                'confidence': min(abs(trend_signal), 0.95),
                'value': trend_signal
            }
            
            return signals
        except Exception as e:
            self.logger.error(f"Error generating base signals for {symbol}: {e}")
            return {}
    
    def calculate_momentum_signal(self, prices: pd.Series) -> float:
        """Calculate momentum signal from price series"""
        try:
            if len(prices) < 10:
                return 0.0
            
            # Simple momentum calculation
            short_term = prices.iloc[-1] / prices.iloc[-5] - 1
            long_term = prices.iloc[-1] / prices.iloc[-10] - 1
            
            return (short_term * 0.7 + long_term * 0.3)
        except Exception as e:
            self.logger.error(f"Error calculating momentum signal: {e}")
            return 0.0
    
    def calculate_mean_reversion_signal(self, prices: pd.Series) -> float:
        """Calculate mean reversion signal from price series"""
        try:
            if len(prices) < 20:
                return 0.0
            
            # Simple mean reversion based on Bollinger Bands
            sma = prices.rolling(20).mean().iloc[-1]
            std = prices.rolling(20).std().iloc[-1]
            current_price = prices.iloc[-1]
            
            upper_band = sma + 2 * std
            lower_band = sma - 2 * std
            
            if current_price > upper_band:
                return -0.8  # Sell signal
            elif current_price < lower_band:
                return 0.8   # Buy signal
            else:
                return 0.0   # Neutral
        except Exception as e:
            self.logger.error(f"Error calculating mean reversion signal: {e}")
            return 0.0
    
    def calculate_trend_signal(self, prices: pd.Series) -> float:
        """Calculate trend signal from price series"""
        try:
            if len(prices) < 20:
                return 0.0
            
            # Simple trend based on moving averages
            short_ma = prices.rolling(10).mean().iloc[-1]
            long_ma = prices.rolling(20).mean().iloc[-1]
            
            if short_ma > long_ma * 1.001:
                return 0.7  # Uptrend
            elif short_ma < long_ma * 0.999:
                return -0.7  # Downtrend
            else:
                return 0.0   # Sideways
        except Exception as e:
            self.logger.error(f"Error calculating trend signal: {e}")
            return 0.0
    
    def combine_signals(self, signals: Dict[str, float]) -> float:
        """Combine multiple signals into a single signal"""
        try:
            if not signals:
                return 0.0
            
            # Simple weighted average
            weights = {
                'momentum': 0.4,
                'mean_reversion': 0.3,
                'trend': 0.3
            }
            
            combined = 0.0
            total_weight = 0.0
            
            for signal_type, value in signals.items():
                weight = weights.get(signal_type, 0.2)
                combined += value * weight
                total_weight += weight
            
            return combined / total_weight if total_weight > 0 else 0.0
        except Exception as e:
            self.logger.error(f"Error combining signals: {e}")
            return 0.0
    
    def apply_risk_filters(self, signal: float, confidence: float, risk_metrics: Dict[str, float]) -> float:
        """Apply risk filters to signal"""
        try:
            # Simple risk filtering based on volatility
            volatility = risk_metrics.get('volatility', 0.02)
            max_drawdown = risk_metrics.get('max_drawdown', 0.05)
            
            # Reduce signal strength if volatility is high
            if volatility > 0.03:
                signal *= 0.7
            
            # Reduce signal strength if max drawdown is high
            if max_drawdown > 0.1:
                signal *= 0.8
            
            return signal
        except Exception as e:
            self.logger.error(f"Error applying risk filters: {e}")
            return signal
    
    def calculate_signal_confidence(self, signals: Dict[str, float]) -> float:
        """Calculate overall confidence from multiple signals"""
        try:
            if not signals:
                return 0.0
            
            # Average absolute signal strength as confidence
            abs_signals = [abs(s) for s in signals.values()]
            return min(sum(abs_signals) / len(abs_signals), 1.0)
        except Exception as e:
            self.logger.error(f"Error calculating signal confidence: {e}")
            return 0.0
    
    def validate_signal(self, signal: Dict[str, Any]) -> bool:
        """Validate signal structure and quality"""
        try:
            required_fields = ['symbol', 'signal_type', 'strength', 'confidence', 'timestamp']
            if not all(field in signal for field in required_fields):
                return False
            
            # Check confidence threshold
            if signal.get('confidence', 0.0) < self.config.min_confidence_threshold:
                return False
            
            return True
        except Exception as e:
            self.logger.error(f"Error validating signal: {e}")
            return False
    
    def calculate_signal_metrics(self, symbol: str) -> Dict[str, Any]:
        """Calculate performance metrics for signals"""
        try:
            history = self.get_signal_history(symbol)
            if not history:
                return {
                    'total_signals': 0,
                    'win_rate': 0.0,
                    'avg_return': 0.0,
                    'avg_confidence': 0.0
                }
            
            total_signals = len(history)
            winning_signals = 0
            total_return = 0.0
            total_confidence = 0.0
            
            for signal in history:
                if 'outcome' in signal:
                    total_return += signal['outcome']
                    if signal['outcome'] > 0:
                        winning_signals += 1
                
                if 'confidence' in signal:
                    total_confidence += signal['confidence']
            
            win_rate = winning_signals / total_signals if total_signals > 0 else 0.0
            avg_return = total_return / total_signals if total_signals > 0 else 0.0
            avg_confidence = total_confidence / total_signals if total_signals > 0 else 0.0
            
            return {
                'total_signals': total_signals,
                'win_rate': win_rate,
                'avg_return': avg_return,
                'avg_confidence': avg_confidence
            }
        except Exception as e:
            self.logger.error(f"Error calculating signal metrics for {symbol}: {e}")
            return {
                'total_signals': 0,
                'win_rate': 0.0,
                'avg_return': 0.0,
                'avg_confidence': 0.0
            }
    def process_market_data(self, symbol: str, market_data: pd.DataFrame) -> pd.DataFrame:
        """Process market data for signal generation"""
        try:
            # Basic data cleaning and validation
            if market_data.empty:
                return market_data
            
            # Ensure required columns exist
            required_cols = ['close', 'high', 'low', 'volume']
            for col in required_cols:
                if col not in market_data.columns:
                    market_data[col] = 0.0
            
            # Remove NaN values
            market_data = market_data.dropna()
            
            return market_data
        except Exception as e:
            self.logger.error(f"Error processing market data for {symbol}: {e}")
            return market_data
    
    def apply_signal_decay(self, signal: float, age_hours: float) -> float:
        """Apply time-based signal decay"""
        try:
            decay_factor = self.config.signal_decay_factor ** age_hours
            return signal * decay_factor
        except Exception as e:
            self.logger.error(f"Error applying signal decay: {e}")
            return signal
    
    def generate_multi_timeframe_signals(self, symbol: str, multi_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Generate signals across multiple timeframes"""
        try:
            timeframe_signals = {}
            combined_confidence = 0.0
            combined_signal_type = SignalType.NEUTRAL
            
            for timeframe, data in multi_data.items():
                if not data.empty and len(data) >= 20:
                    signal = self.generate_signal(f"{symbol}_{timeframe}", data)
                    if signal:
                        timeframe_signals[timeframe] = signal
                        combined_confidence += signal.get('confidence', 0.0)
                        # Use the signal type from the longest timeframe as primary
                        if timeframe == max(multi_data.keys(), key=len):
                            combined_signal_type = signal.get('signal_type', SignalType.NEUTRAL)
            
            # Calculate combined signal
            num_timeframes = len(timeframe_signals)
            if num_timeframes > 0:
                combined_confidence /= num_timeframes
                
                combined_signal = {
                    'symbol': symbol,
                    'signal_type': combined_signal_type,
                    'strength': SignalStrength.STRONG if combined_confidence > 0.7 else SignalStrength.MODERATE,
                    'confidence': combined_confidence,
                    'timestamp': datetime.now()
                }
            else:
                combined_signal = None
            
            return {
                'combined_signal': combined_signal,
                'timeframe_signals': timeframe_signals
            }
        except Exception as e:
            self.logger.error(f"Error generating multi-timeframe signals for {symbol}: {e}")
            return {
                'combined_signal': None,
                'timeframe_signals': {}
            }
    
    def calculate_risk_adjusted_position_size(self, signal_strength: float, confidence: float, 
                                            volatility: float, portfolio_value: float) -> float:
        """Calculate risk-adjusted position size"""
        try:
            # Simple position sizing based on Kelly criterion approximation
            base_size = portfolio_value * 0.02  # 2% of portfolio
            
            # Adjust for signal strength and confidence
            adjustment = signal_strength * confidence
            
            # Adjust for volatility (higher volatility = smaller position)
            vol_adjustment = 1.0 / (1.0 + volatility * 10)
            
            position_size = base_size * adjustment * vol_adjustment
            
            # Cap at reasonable limits
            return min(max(position_size, 0), portfolio_value * 0.1)
        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return 0.0
    
    def apply_correlation_filter(self, signals: Dict[str, float], correlation_matrix: pd.DataFrame) -> Dict[str, float]:
        """Apply correlation filter to signals"""
        try:
            filtered_signals = {}
            
            for symbol, signal in signals.items():
                if symbol in correlation_matrix.index:
                    # Check correlation with other signals
                    correlations = correlation_matrix.loc[symbol]
                    high_corr_count = sum(1 for corr in correlations if abs(corr) > 0.7)
                    
                    # Reduce signal if highly correlated with many others
                    if high_corr_count > 2:
                        signal *= 0.7
                    
                    filtered_signals[symbol] = signal
                else:
                    filtered_signals[symbol] = signal
            
            return filtered_signals
        except Exception as e:
            self.logger.error(f"Error applying correlation filter: {e}")
            return signals
    
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
            
            # Adjust for volatility (higher volatility reduces momentum signal)
            if volatility > 0.02:
                momentum_score *= 0.8
            
            return momentum_score
        except Exception as e:
            self.logger.error(f"Error calculating momentum factor: {e}")
            return 0.0
    
    def _calculate_mean_reversion_factor(self, rsi_14: float, rsi_21: float, bollinger_position: float) -> float:
        """Calculate mean reversion factor"""
        try:
            mean_reversion_score = 0.0
            
            # RSI-based mean reversion
            if rsi_14 < 30:
                mean_reversion_score += 0.8  # Oversold
            elif rsi_14 > 70:
                mean_reversion_score -= 0.8  # Overbought
            
            if rsi_21 < 30:
                mean_reversion_score += 0.6
            elif rsi_21 > 70:
                mean_reversion_score -= 0.6
            
            # Bollinger Band position
            if bollinger_position < 0.2:
                mean_reversion_score += 0.5  # Near lower band
            elif bollinger_position > 0.8:
                mean_reversion_score -= 0.5  # Near upper band
            
            return mean_reversion_score
        except Exception as e:
            self.logger.error(f"Error calculating mean reversion factor: {e}")
            return 0.0
    
    def _calculate_volume_factor(self, volume_ratio: float, returns_1d: float) -> float:
        """Calculate volume confirmation factor"""
        try:
            volume_score = 0.0
            
            # Volume confirmation
            if volume_ratio > 1.2 and abs(returns_1d) > 0.005:
                volume_score += returns_1d * 3  # High volume + price movement
            elif volume_ratio < 0.8:
                volume_score += returns_1d * 0.5  # Low volume reduces signal
            
            return volume_score
        except Exception as e:
            self.logger.error(f"Error calculating volume factor: {e}")
            return 0.0
    
    def _calculate_volatility_factor(self, volatility: float, features: Dict[str, float]) -> float:
        """Calculate volatility regime factor"""
        try:
            vol_score = 0.0
            
            # Volatility adjustment
            if volatility > 0.03:
                vol_score -= 0.3  # High volatility reduces confidence
            elif volatility < 0.01:
                vol_score += 0.2  # Low volatility increases confidence
            
            return vol_score
        except Exception as e:
            self.logger.error(f"Error calculating volatility factor: {e}")
            return 0.0
    
    def _calculate_adaptive_weights(self, market_data: pd.DataFrame, regime_info: Optional[Dict[str, Any]]) -> List[float]:
        """Calculate adaptive weights for signal factors"""
        try:
            # Default weights
            weights = [0.4, 0.3, 0.2, 0.1]
            
            # Adjust based on market regime
            if regime_info:
                regime = regime_info.get('regime', 'neutral')
                if regime == 'trending':
                    weights = [0.5, 0.2, 0.2, 0.1]  # Favor momentum
                elif regime == 'ranging':
                    weights = [0.2, 0.5, 0.2, 0.1]  # Favor mean reversion
            
            return weights
        except Exception as e:
            self.logger.error(f"Error calculating adaptive weights: {e}")
            return [0.4, 0.3, 0.2, 0.1]
    
    def _pass_risk_filter(self, signal: TradingSignal) -> bool:
        """Apply risk filters to signal"""
        try:
            # Basic risk filters
            if signal.confidence < self.config.min_confidence_threshold:
                return False
            
            # Check position size limits
            if signal.position_size and signal.position_size > self.config.max_position_size:
                return False
            
            # Additional risk checks can be added here
            return True
        except Exception as e:
            self.logger.error(f"Error in risk filter: {e}")
            return False
    
    def _optimize_signal(self, signal: TradingSignal, market_data: pd.DataFrame) -> TradingSignal:
        """Optimize signal timing and position size"""
        try:
            # Basic optimization - can be enhanced
            return signal
        except Exception as e:
            self.logger.error(f"Error optimizing signal: {e}")
            return signal
    
    def _apply_regime_adjustment(self, signal_type: SignalType, regime_info: Dict[str, Any]) -> float:
        """Apply regime-based adjustments to signal confidence"""
        try:
            regime = regime_info.get('regime', 'neutral')
            regime_confidence = regime_info.get('confidence', 0.5)
            
            # Adjust confidence based on regime
            if regime == 'trending' and signal_type in [SignalType.LONG, SignalType.SHORT]:
                return 1.2  # Boost trend-following signals
            elif regime == 'ranging' and signal_type == SignalType.NEUTRAL:
                return 1.1  # Boost neutral signals in ranging markets
            else:
                return 0.9  # Slight reduction for mismatched signals
            
        except Exception as e:
            self.logger.error(f"Error applying regime adjustment: {e}")
            return 1.0
    
    def _apply_ml_enhancement(self, features: Dict[str, float], regime_info: Optional[Dict[str, Any]]) -> float:
        """Apply ML-based enhancements to signal confidence"""
        try:
            # Simple ML enhancement - can be expanded with actual ML models
            if self.config.enable_ml_features and hasattr(self, '_ml_model'):
                # Placeholder for ML model prediction
                ml_confidence = 1.0
            else:
                ml_confidence = 1.0
            
            return ml_confidence
        except Exception as e:
            self.logger.error(f"Error applying ML enhancement: {e}")
            return 1.0
    
    def _calculate_adaptive_threshold(self, market_data: pd.DataFrame) -> float:
        """Calculate adaptive confidence threshold based on market conditions"""
        try:
            if len(market_data) < 20:
                return self.config.min_confidence_threshold
            
            # Calculate market volatility
            returns = market_data['close'].pct_change().dropna()
            volatility = returns.std()
            
            # Higher volatility requires higher confidence threshold
            if volatility > 0.03:
                return self.config.min_confidence_threshold * 1.5
            elif volatility < 0.01:
                return self.config.min_confidence_threshold * 0.8
            else:
                return self.config.min_confidence_threshold
            
        except Exception as e:
            self.logger.error(f"Error calculating adaptive threshold: {e}")
            return self.config.min_confidence_threshold

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
