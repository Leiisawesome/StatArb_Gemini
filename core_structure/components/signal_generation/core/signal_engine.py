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
        """Extract basic technical features when feature processor not available"""
        try:
            latest = market_data.iloc[-1]
            
            features = {
                'price': float(latest['close']),
                'volume': float(latest['volume']),
                'returns_1d': float((latest['close'] / market_data.iloc[-2]['close'] - 1)) if len(market_data) > 1 else 0.0,
                'volatility_20d': float(market_data['close'].pct_change().rolling(20).std().iloc[-1]) if len(market_data) >= 20 else 0.0,
            }
            
            # RSI if TA available
            if TA_AVAILABLE and len(market_data) >= 14:
                try:
                    rsi = ta.momentum.RSIIndicator(market_data['close'], window=14)
                    features['rsi_14'] = float(rsi.rsi().iloc[-1])
                except:
                    features['rsi_14'] = 50.0
            
            return features
            
        except Exception as e:
            self.logger.warning(f"Error extracting basic features: {e}")
            return {}
    
    def _generate_core_signal(self, symbol: str, market_data: pd.DataFrame, 
                             features: Dict[str, float], 
                             regime_info: Optional[Dict[str, Any]]) -> Optional[TradingSignal]:
        """Generate core trading signal based on features and regime"""
        try:
            # Simple momentum-based signal generation (can be enhanced with ML models)
            confidence = 0.0
            signal_type = SignalType.NEUTRAL
            strength = SignalStrength.WEAK
            
            # Extract key features
            returns_1d = features.get('returns_1d', 0.0)
            volatility = features.get('volatility_20d', 0.0)
            rsi = features.get('rsi_14', 50.0)
            
            # Basic momentum signal
            if abs(returns_1d) > 0.001:  # 0.1% threshold
                # Momentum direction
                if returns_1d > 0:
                    signal_type = SignalType.LONG
                else:
                    signal_type = SignalType.SHORT
                
                # Confidence based on momentum strength and RSI
                momentum_strength = min(abs(returns_1d) * 100, 5.0)  # Cap at 5%
                
                if rsi < 30 and returns_1d > 0:  # Oversold bouncing up
                    confidence = min(0.8, 0.4 + momentum_strength * 0.1)
                elif rsi > 70 and returns_1d < 0:  # Overbought falling down  
                    confidence = min(0.8, 0.4 + momentum_strength * 0.1)
                else:
                    confidence = min(0.6, 0.2 + momentum_strength * 0.05)
                
                # Adjust for volatility
                if volatility > 0.03:  # High volatility
                    confidence *= 0.8
                
                # Regime adjustment
                if regime_info:
                    regime_confidence = regime_info.get('confidence', 0.5)
                    regime_type = regime_info.get('regime', 'unknown')
                    
                    if regime_type == 'trending' and signal_type != SignalType.NEUTRAL:
                        confidence *= (1.0 + regime_confidence * 0.2)  # Boost trending signals
                    elif regime_type == 'mean_reverting':
                        confidence *= 0.8  # Reduce momentum signals in mean-reverting regime
                
                # Determine strength
                if confidence > 0.7:
                    strength = SignalStrength.VERY_STRONG
                elif confidence > 0.55:
                    strength = SignalStrength.STRONG
                elif confidence > 0.4:
                    strength = SignalStrength.MODERATE
                elif confidence > 0.25:
                    strength = SignalStrength.WEAK
                else:
                    strength = SignalStrength.VERY_WEAK
            
            # Check minimum confidence threshold
            if confidence < self.config.min_confidence_threshold:
                return None
            
            # Create signal
            signal = TradingSignal(
                symbol=symbol,
                signal_type=signal_type,
                strength=strength,
                confidence=confidence,
                timestamp=datetime.now(),
                entry_price=features.get('price'),
                features=features,
                regime=regime_info.get('regime') if regime_info else None,
                regime_confidence=regime_info.get('confidence') if regime_info else None
            )
            
            return signal
            
        except Exception as e:
            self.logger.error(f"Error in core signal generation for {symbol}: {e}")
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
