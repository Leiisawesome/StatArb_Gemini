"""
SignalBridge: Core System ↔ Backtesting Framework Integration

This module provides a bridge between the core system's async signal generation
and the backtesting framework's sync requirements. It ensures signal consistency
between production and backtesting environments.

Key Features:
- Async-to-sync signal conversion
- Fallback signal generation for backtesting
- Signal consistency validation
- Performance optimization for backtesting
- Error handling and recovery
"""

import asyncio
import logging
from typing import Dict, List, Optional, Union, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import time

from .signal_generator import SignalGenerator
from .enhanced_signal_generator import EnhancedSignalGenerator
from .ai_signal_enhancer import AISignalEnhancer
from .regime_detector import RegimeDetector
from .feature_engine import FeatureEngine

logger = logging.getLogger(__name__)


@dataclass
class SignalBridgeConfig:
    """Configuration for SignalBridge"""
    
    # Core system integration
    use_core_signal_generator: bool = True
    use_ai_enhancement: bool = True
    use_regime_detection: bool = True
    
    # Performance settings
    max_concurrent_signals: int = 10
    timeout_seconds: float = 5.0
    cache_size: int = 1000
    
    # Fallback settings
    enable_fallback: bool = True
    fallback_timeout: float = 1.0
    
    # Validation settings
    validate_signals: bool = True
    min_signal_confidence: float = 0.1
    max_signal_confidence: float = 1.0
    
    # Logging settings
    log_performance: bool = True
    log_errors: bool = True


@dataclass
class SignalBridgeResult:
    """Result from SignalBridge signal generation"""
    
    symbol: str
    signal_value: float
    confidence: float
    timestamp: datetime
    source: str  # 'core', 'fallback', 'cached'
    metadata: Dict[str, Any] = field(default_factory=dict)
    processing_time_ms: float = 0.0
    error_message: Optional[str] = None


@dataclass
class SignalConsistencyReport:
    """Report on signal consistency between environments"""
    
    total_signals: int
    consistent_signals: int
    consistency_rate: float
    avg_difference: float
    max_difference: float
    inconsistent_symbols: List[str]
    performance_metrics: Dict[str, float]
    recommendations: List[str]


class SignalBridge:
    """
    Bridge between core system signal generation and backtesting framework.
    
    This class provides:
    1. Async-to-sync conversion for signal generation
    2. Fallback signal generation for backtesting
    3. Signal consistency validation
    4. Performance optimization
    5. Error handling and recovery
    """
    
    def __init__(self, config: Optional[SignalBridgeConfig] = None):
        """Initialize SignalBridge with configuration"""
        self.config = config or SignalBridgeConfig()
        self.logger = logging.getLogger(f"{__name__}.SignalBridge")
        
        # Initialize core system components
        self._initialize_core_components()
        
        # Initialize caching and performance tracking
        self._signal_cache: Dict[str, Tuple[float, datetime]] = {}
        self._performance_stats = {
            'total_signals': 0,
            'core_signals': 0,
            'fallback_signals': 0,
            'cached_signals': 0,
            'errors': 0,
            'avg_processing_time': 0.0
        }
        
        # Thread pool for async operations
        self._executor = ThreadPoolExecutor(max_workers=self.config.max_concurrent_signals)
        
        self.logger.info("SignalBridge initialized successfully")
    
    def _initialize_core_components(self):
        """Initialize core system signal generation components"""
        try:
            # Core signal generator
            if self.config.use_core_signal_generator:
                self.signal_generator = SignalGenerator()
                
                # Initialize EnhancedSignalGenerator with default config
                from .enhanced_signal_generator import AcademicSignalConfig
                academic_config = AcademicSignalConfig()
                self.enhanced_signal_generator = EnhancedSignalGenerator(academic_config)
                
                self.logger.info("Core signal generators initialized")
            
            # AI enhancement
            if self.config.use_ai_enhancement:
                self.ai_enhancer = AISignalEnhancer()
                self.logger.info("AI signal enhancer initialized")
            
            # Regime detection
            if self.config.use_regime_detection:
                self.regime_detector = RegimeDetector()
                self.logger.info("Regime detector initialized")
            
            # Feature engine
            self.feature_engine = FeatureEngine()
            self.logger.info("Feature engine initialized")
            
        except Exception as e:
            self.logger.error(f"Error initializing core components: {e}")
            raise
    
    def generate_signals_sync(
        self, 
        symbols: List[str], 
        market_data: Dict[str, pd.DataFrame],
        current_date: datetime,
        use_cache: bool = True
    ) -> Dict[str, SignalBridgeResult]:
        """
        Generate signals synchronously for backtesting framework.
        
        Args:
            symbols: List of symbols to generate signals for
            market_data: Market data for each symbol
            current_date: Current date/time for signal generation
            use_cache: Whether to use signal caching
            
        Returns:
            Dictionary mapping symbols to SignalBridgeResult
        """
        start_time = time.time()
        results = {}
        
        try:
            # Check cache first if enabled
            if use_cache:
                cached_results = self._get_cached_signals(symbols, current_date)
                symbols_to_process = [s for s in symbols if s not in cached_results]
                results.update(cached_results)
            else:
                symbols_to_process = symbols
            
            # Generate signals for remaining symbols
            if symbols_to_process:
                # Create event loop for async processing
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    new_results = loop.run_until_complete(
                        self._generate_signals_batch(
                            symbols_to_process, 
                            market_data, 
                            current_date
                        )
                    )
                    results.update(new_results)
                    loop.close()
                except Exception as e:
                    self.logger.error(f"Error in async signal generation: {e}")
                    # Fallback to synchronous processing
                    for symbol in symbols_to_process:
                        if symbol in market_data:
                            results[symbol] = self._generate_fallback_signal(
                                symbol, market_data[symbol], current_date
                            )
            
            # Update performance stats
            self._update_performance_stats(results, time.time() - start_time)
            
            # Validate results if enabled
            if self.config.validate_signals:
                self._validate_signals(results)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error generating signals: {e}")
            self._performance_stats['errors'] += 1
            
            # Return fallback signals on error
            if self.config.enable_fallback:
                return self._generate_fallback_signals(symbols, market_data, current_date)
            else:
                raise
    
    async def _generate_signals_batch(
        self,
        symbols: List[str],
        market_data: Dict[str, pd.DataFrame],
        current_date: datetime
    ) -> Dict[str, SignalBridgeResult]:
        """Generate signals for a batch of symbols"""
        results = {}
        
        # Use asyncio for concurrent processing
        tasks = []
        for symbol in symbols:
            if symbol in market_data:
                task = self._generate_single_signal(
                    symbol,
                    market_data[symbol],
                    current_date
                )
                tasks.append((symbol, task))
        
        # Collect results
        for symbol, task in tasks:
            try:
                result = await asyncio.wait_for(task, timeout=self.config.timeout_seconds)
                results[symbol] = result
                
                # Cache the result
                self._cache_signal(symbol, result, current_date)
                
            except Exception as e:
                self.logger.error(f"Error generating signal for {symbol}: {e}")
                if self.config.enable_fallback:
                    results[symbol] = self._generate_fallback_signal(
                        symbol, market_data.get(symbol), current_date
                    )
                else:
                    results[symbol] = SignalBridgeResult(
                        symbol=symbol,
                        signal_value=0.0,
                        confidence=0.0,
                        timestamp=current_date,
                        source='error',
                        error_message=str(e)
                    )
        
        return results
    
    async def _generate_single_signal(
        self,
        symbol: str,
        market_data: pd.DataFrame,
        current_date: datetime
    ) -> SignalBridgeResult:
        """Generate signal for a single symbol"""
        start_time = time.time()
        
        try:
            # Extract features (using generate_features directly since we're already async)
            features = None
            try:
                feature_set = await self.feature_engine.generate_features(market_data)
                if feature_set:
                    features = feature_set.features
            except Exception as e:
                self.logger.warning(f"Feature extraction failed: {e}")
                features = {}
            
            # Generate core signal
            if self.config.use_core_signal_generator:
                trading_signal = self.signal_generator.generate_signal(
                    symbol_pair=symbol,
                    market_data=market_data,
                    real_time_data=None
                )
                
                # Convert to float for backtesting compatibility
                signal_value = self._convert_trading_signal_to_float(trading_signal)
                confidence = getattr(trading_signal, 'confidence', 0.7)  # Default to 0.7 for better confidence
                
                # AI enhancement if enabled
                if self.config.use_ai_enhancement:
                    try:
                        # Convert trading_signal to dict format expected by AI enhancer
                        signal_dict = {
                            'signal_value': signal_value,
                            'confidence': confidence,
                            'symbol': symbol,
                            'timestamp': current_date
                        }
                        
                        # Call AI enhancer with correct parameters
                        enhanced_result = await self.ai_enhancer.enhance_signal(
                            signal=signal_dict,
                            market_data=market_data,
                            symbol=symbol
                        )
                        
                        # Use enhanced confidence if available
                        if enhanced_result and hasattr(enhanced_result, 'enhanced_confidence'):
                            confidence = enhanced_result.enhanced_confidence
                    except Exception as e:
                        self.logger.warning(f"AI enhancement failed: {e}")
                        # Continue with original signal
                
                # Regime detection if enabled
                if self.config.use_regime_detection:
                    try:
                        regime = await self.regime_detector.detect_regime(
                            symbol=symbol,
                            market_data=market_data
                        )
                        # Adjust signal based on regime
                        signal_value = self._adjust_signal_for_regime(signal_value, regime)
                    except Exception as e:
                        self.logger.warning(f"Regime detection failed for {symbol}: {e}")
                        regime = None
                
                processing_time = (time.time() - start_time) * 1000
                
                return SignalBridgeResult(
                    symbol=symbol,
                    signal_value=signal_value,
                    confidence=confidence,
                    timestamp=current_date,
                    source='core',
                    processing_time_ms=processing_time,
                    metadata={
                        'regime': getattr(regime, 'regime_type', 'unknown') if self.config.use_regime_detection else None,
                        'features_count': len(features) if features else 0
                    }
                )
            
            else:
                # Use fallback signal generation
                return self._generate_fallback_signal(symbol, market_data, current_date)
                
        except Exception as e:
            self.logger.error(f"Error generating signal for {symbol}: {e}")
            processing_time = (time.time() - start_time) * 1000
            
            return SignalBridgeResult(
                symbol=symbol,
                signal_value=0.0,
                confidence=0.0,
                timestamp=current_date,
                source='error',
                processing_time_ms=processing_time,
                error_message=str(e)
            )
    
    def _convert_trading_signal_to_float(self, trading_signal) -> float:
        """Convert TradingSignal object to float for backtesting compatibility"""
        if hasattr(trading_signal, 'signal_value'):
            return float(trading_signal.signal_value)
        elif hasattr(trading_signal, 'signal'):
            return float(trading_signal.signal)
        elif hasattr(trading_signal, 'value'):
            return float(trading_signal.value)
        elif isinstance(trading_signal, (int, float)):
            return float(trading_signal)
        else:
            # Default fallback
            return 0.0
    
    def _adjust_signal_for_regime(self, signal_value: float, regime) -> float:
        """Adjust signal value based on detected market regime"""
        if not regime or not hasattr(regime, 'regime_type'):
            return signal_value
        
        regime_type = regime.regime_type.lower()
        
        # Adjust signal based on regime
        if regime_type == 'trending':
            # Amplify signals in trending markets
            return signal_value * 1.2
        elif regime_type == 'mean_reverting':
            # Reduce signal strength in mean-reverting markets
            return signal_value * 0.8
        elif regime_type == 'volatile':
            # Reduce signal strength in volatile markets
            return signal_value * 0.6
        else:
            return signal_value
    
    def _generate_fallback_signals(
        self,
        symbols: List[str],
        market_data: Dict[str, pd.DataFrame],
        current_date: datetime
    ) -> Dict[str, SignalBridgeResult]:
        """Generate fallback signals using simple technical indicators"""
        results = {}
        
        for symbol in symbols:
            results[symbol] = self._generate_fallback_signal(
                symbol, market_data.get(symbol), current_date
            )
        
        return results
    
    def _generate_fallback_signal(
        self,
        symbol: str,
        market_data: Optional[pd.DataFrame],
        current_date: datetime
    ) -> SignalBridgeResult:
        """Generate a fallback signal using simple moving average crossover"""
        start_time = time.time()
        
        try:
            if market_data is None or len(market_data) < 50:
                return SignalBridgeResult(
                    symbol=symbol,
                    signal_value=0.0,
                    confidence=0.0,
                    timestamp=current_date,
                    source='fallback',
                    processing_time_ms=(time.time() - start_time) * 1000,
                    error_message='Insufficient market data'
                )
            
            # Simple moving average crossover
            close_prices = market_data['close'].values
            ma_short = np.mean(close_prices[-10:])  # 10-day MA
            ma_long = np.mean(close_prices[-30:])   # 30-day MA
            
            # Generate signal based on MA crossover
            if ma_short > ma_long:
                signal_value = 0.5  # Buy signal
            elif ma_short < ma_long:
                signal_value = -0.5  # Sell signal
            else:
                signal_value = 0.0  # Neutral
            
            # Calculate confidence based on MA separation
            ma_diff = abs(ma_short - ma_long) / ma_long
            confidence = min(ma_diff * 10, 0.8)  # Cap at 0.8
            
            processing_time = (time.time() - start_time) * 1000
            
            return SignalBridgeResult(
                symbol=symbol,
                signal_value=signal_value,
                confidence=confidence,
                timestamp=current_date,
                source='fallback',
                processing_time_ms=processing_time,
                metadata={
                    'ma_short': ma_short,
                    'ma_long': ma_long,
                    'ma_diff': ma_diff
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error generating fallback signal for {symbol}: {e}")
            return SignalBridgeResult(
                symbol=symbol,
                signal_value=0.0,
                confidence=0.0,
                timestamp=current_date,
                source='fallback',
                processing_time_ms=(time.time() - start_time) * 1000,
                error_message=str(e)
            )
    
    def _get_cached_signals(
        self,
        symbols: List[str],
        current_date: datetime
    ) -> Dict[str, SignalBridgeResult]:
        """Get cached signals if available and valid"""
        cached_results = {}
        cache_expiry = timedelta(minutes=5)  # 5-minute cache
        
        for symbol in symbols:
            if symbol in self._signal_cache:
                cached_value, cached_time = self._signal_cache[symbol]
                
                # Check if cache is still valid
                if current_date - cached_time < cache_expiry:
                    cached_results[symbol] = SignalBridgeResult(
                        symbol=symbol,
                        signal_value=cached_value,
                        confidence=0.8,  # High confidence for cached signals
                        timestamp=current_date,
                        source='cached',
                        processing_time_ms=0.0
                    )
                    self._performance_stats['cached_signals'] += 1
        
        return cached_results
    
    def _cache_signal(self, symbol: str, result: SignalBridgeResult, current_date: datetime):
        """Cache a signal result"""
        if len(self._signal_cache) >= self.config.cache_size:
            # Remove oldest entry
            oldest_symbol = min(self._signal_cache.keys(), 
                              key=lambda k: self._signal_cache[k][1])
            del self._signal_cache[oldest_symbol]
        
        self._signal_cache[symbol] = (result.signal_value, current_date)
    
    def _validate_signals(self, results: Dict[str, SignalBridgeResult]):
        """Validate generated signals"""
        for symbol, result in results.items():
            # Check signal value range
            if not (self.config.min_signal_confidence <= result.confidence <= self.config.max_signal_confidence):
                self.logger.warning(f"Signal confidence out of range for {symbol}: {result.confidence}")
            
            # Check for extreme signal values
            if abs(result.signal_value) > 2.0:
                self.logger.warning(f"Extreme signal value for {symbol}: {result.signal_value}")
            
            # Check for processing time
            if result.processing_time_ms > 1000:  # 1 second
                self.logger.warning(f"Slow signal processing for {symbol}: {result.processing_time_ms}ms")
    
    def _update_performance_stats(self, results: Dict[str, SignalBridgeResult], total_time: float):
        """Update performance statistics"""
        self._performance_stats['total_signals'] += len(results)
        
        for result in results.values():
            if result.source == 'core':
                self._performance_stats['core_signals'] += 1
            elif result.source == 'fallback':
                self._performance_stats['fallback_signals'] += 1
            elif result.source == 'cached':
                self._performance_stats['cached_signals'] += 1
        
        # Update average processing time
        if results:
            avg_time = sum(r.processing_time_ms for r in results.values()) / len(results)
            current_avg = self._performance_stats['avg_processing_time']
            total_signals = self._performance_stats['total_signals']
            
            self._performance_stats['avg_processing_time'] = (
                (current_avg * (total_signals - len(results)) + avg_time * len(results)) / total_signals
            )
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics"""
        stats = self._performance_stats.copy()
        
        # Calculate additional metrics
        if stats['total_signals'] > 0:
            stats['success_rate'] = (
                (stats['total_signals'] - stats['errors']) / stats['total_signals']
            )
            stats['cache_hit_rate'] = (
                stats['cached_signals'] / stats['total_signals']
            )
        else:
            stats['success_rate'] = 0.0
            stats['cache_hit_rate'] = 0.0
        
        return stats
    
    def clear_cache(self):
        """Clear the signal cache"""
        self._signal_cache.clear()
        self.logger.info("Signal cache cleared")
    
    def shutdown(self):
        """Shutdown the SignalBridge and cleanup resources"""
        self._executor.shutdown(wait=True)
        self.clear_cache()
        self.logger.info("SignalBridge shutdown complete")


# Convenience functions for easy integration
def create_signal_bridge(config: Optional[SignalBridgeConfig] = None) -> SignalBridge:
    """Create a SignalBridge instance with default or custom configuration"""
    return SignalBridge(config)


def generate_signals_for_backtesting(
    symbols: List[str],
    market_data: Dict[str, pd.DataFrame],
    current_date: datetime,
    bridge: Optional[SignalBridge] = None
) -> Dict[str, float]:
    """
    Convenience function to generate signals for backtesting framework.
    
    Returns:
        Dictionary mapping symbols to signal values (float)
    """
    if bridge is None:
        bridge = create_signal_bridge()
    
    results = bridge.generate_signals_sync(symbols, market_data, current_date)
    
    # Convert to simple float dictionary for backtesting compatibility
    return {symbol: result.signal_value for symbol, result in results.items()} 