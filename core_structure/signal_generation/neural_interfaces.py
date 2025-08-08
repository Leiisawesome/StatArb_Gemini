#!/usr/bin/env python3
"""
Neural Network Architecture Interfaces
=====================================

Core interfaces for integrating the GPT-5 enhanced neural network architecture
with the existing Unified Core System. These interfaces ensure seamless
integration while maintaining backward compatibility.

Author: Neural Architecture Team
Date: 2025-01-27
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import numpy as np
import pandas as pd

# Configure logging
logger = logging.getLogger(__name__)

class SignalType(Enum):
    """Trading signal types"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE = "close"

class RegimeType(Enum):
    """Market regime types"""
    TRENDING = "trending"
    MEAN_REVERTING = "mean_reverting"
    VOLATILE = "volatile"
    SIDEWAYS = "sideways"
    UNKNOWN = "unknown"

@dataclass
class NeuralSignal:
    """Neural network generated trading signal"""
    signal_type: SignalType
    confidence: float
    strength: float
    timestamp: datetime
    regime: RegimeType
    uncertainty: float
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class NeuralConfig:
    """Configuration for neural network architecture"""
    # Performance settings
    latency_target_ms: int = 100
    throughput_target: int = 1000
    
    # Neural network settings
    attention_heads: int = 16
    embedding_dim: int = 1024
    temporal_layers: int = 3
    
    # GPT-5 integration
    gpt5_enabled: bool = True
    gpt5_temperature: float = 0.1
    gpt5_max_tokens: int = 500
    
    # Safety settings
    max_position_size: float = 0.1
    min_confidence_threshold: float = 0.6
    max_uncertainty_threshold: float = 0.3

class NeuralStrategyInterface:
    """
    Interface between neural strategy and core system
    
    This interface ensures that the neural network architecture can
    seamlessly integrate with the existing Unified Core System while
    maintaining backward compatibility.
    """
    
    def __init__(self, config: Optional[NeuralConfig] = None):
        """
        Initialize neural strategy interface
        
        Args:
            config: Neural network configuration
        """
        self.config = config or NeuralConfig()
        self.performance_tracker = PerformanceTracker()
        self.error_handler = ErrorHandler()
        
        # Initialize neural components
        self._initialize_neural_components()
    
    def _initialize_neural_components(self):
        """Initialize neural network components"""
        try:
            # Import neural components (will be implemented in separate files)
            from .neural_modalities import PriceModalityProcessor, VolumeModalityProcessor
            from .neural_feature_selection import DynamicFeatureSelector
            from .neural_ensembles import DynamicEnsembleNetwork
            from .neural_regime import RegimeAwareSignalGenerator
            
            self.price_processor = PriceModalityProcessor()
            self.volume_processor = VolumeModalityProcessor()
            self.feature_selector = DynamicFeatureSelector()
            self.ensemble_network = DynamicEnsembleNetwork()
            self.regime_generator = RegimeAwareSignalGenerator()
            
            logger.info("Neural components initialized successfully")
            
        except ImportError as e:
            logger.warning(f"Neural components not available: {e}")
            self._initialize_fallback_components()
    
    def _initialize_fallback_components(self):
        """Initialize fallback components when neural components are not available"""
        logger.info("Initializing fallback components")
        # Fallback to basic signal generation
        self.price_processor = None
        self.volume_processor = None
        self.feature_selector = None
        self.ensemble_network = None
        self.regime_generator = None
    
    async def generate_signals(self, market_data: Dict[str, Any]) -> Optional[NeuralSignal]:
        """
        Generate trading signals using neural network architecture
        
        Args:
            market_data: Market data dictionary containing OHLCV and other data
            
        Returns:
            NeuralSignal object or None if signal generation fails
        """
        try:
            start_time = datetime.now()
            
            # Validate input data
            if not self._validate_market_data(market_data):
                logger.error("Invalid market data provided")
                return None
            
            # Process through neural architecture
            if self._neural_components_available():
                signal = await self._generate_neural_signal(market_data)
            else:
                signal = await self._generate_fallback_signal(market_data)
            
            # Track performance
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self.performance_tracker.record_processing_time(processing_time)
            
            # Validate signal
            if signal and self._validate_signal(signal):
                return signal
            else:
                logger.warning("Generated signal failed validation")
                return None
                
        except Exception as e:
            logger.error(f"Error generating neural signal: {e}")
            self.error_handler.handle_error(e)
            return None
    
    def _neural_components_available(self) -> bool:
        """Check if neural components are available"""
        return all([
            self.price_processor,
            self.volume_processor,
            self.feature_selector,
            self.ensemble_network,
            self.regime_generator
        ])
    
    async def _generate_neural_signal(self, market_data: Dict[str, Any]) -> Optional[NeuralSignal]:
        """Generate signal using full neural architecture"""
        try:
            # Step 1: Multi-modal processing
            price_features = self.price_processor.process(market_data.get('price', {}))
            volume_features = self.volume_processor.process(market_data.get('volume', {}))
            
            # Step 2: Feature selection
            all_features = {**price_features, **volume_features}
            selected_features = self.feature_selector.select_features(
                all_features, market_data.get('context', {})
            )
            
            # Step 3: Ensemble prediction
            ensemble_result = self.ensemble_network.ensemble_predictions(
                selected_features, market_data.get('context', {})
            )
            
            # Step 4: Regime-aware signal generation
            signal_result = self.regime_generator.generate_signals(
                selected_features, market_data
            )
            
            # Step 5: Synthesize final signal
            signal = self._synthesize_signal(ensemble_result, signal_result)
            
            return signal
            
        except Exception as e:
            logger.error(f"Error in neural signal generation: {e}")
            return None
    
    async def _generate_fallback_signal(self, market_data: Dict[str, Any]) -> Optional[NeuralSignal]:
        """Generate signal using fallback method"""
        try:
            # Simple fallback signal generation
            ohlcv = market_data.get('price', {}).get('ohlcv', [])
            if not ohlcv or len(ohlcv) < 2:
                return None
            
            # Basic momentum signal
            current_price = ohlcv[-1][4]  # Close price
            previous_price = ohlcv[-2][4]
            
            if current_price > previous_price:
                signal_type = SignalType.BUY
                confidence = 0.6
            elif current_price < previous_price:
                signal_type = SignalType.SELL
                confidence = 0.6
            else:
                signal_type = SignalType.HOLD
                confidence = 0.5
            
            return NeuralSignal(
                signal_type=signal_type,
                confidence=confidence,
                strength=abs(current_price - previous_price) / previous_price,
                timestamp=datetime.now(),
                regime=RegimeType.UNKNOWN,
                uncertainty=0.3
            )
            
        except Exception as e:
            logger.error(f"Error in fallback signal generation: {e}")
            return None
    
    def _synthesize_signal(self, ensemble_result: Dict, signal_result: Dict) -> NeuralSignal:
        """Synthesize final signal from ensemble and regime results"""
        try:
            # Extract ensemble prediction
            prediction = ensemble_result.get('prediction', 0)
            confidence = ensemble_result.get('confidence', 0.5)
            uncertainty = ensemble_result.get('uncertainty', 0.3)
            
            # Extract regime information
            regime_name = signal_result.get('current_regime', 'unknown')
            regime = RegimeType(regime_name) if hasattr(RegimeType, regime_name.upper()) else RegimeType.UNKNOWN
            
            # Determine signal type based on prediction
            if prediction > 0.1:
                signal_type = SignalType.BUY
            elif prediction < -0.1:
                signal_type = SignalType.SELL
            else:
                signal_type = SignalType.HOLD
            
            # Apply confidence and uncertainty thresholds
            if confidence < self.config.min_confidence_threshold:
                signal_type = SignalType.HOLD
                confidence *= 0.5
            
            if uncertainty > self.config.max_uncertainty_threshold:
                signal_type = SignalType.HOLD
                confidence *= 0.7
            
            return NeuralSignal(
                signal_type=signal_type,
                confidence=confidence,
                strength=abs(prediction),
                timestamp=datetime.now(),
                regime=regime,
                uncertainty=uncertainty,
                metadata={
                    'ensemble_prediction': prediction,
                    'regime_signals': signal_result.get('regime_signals', {}),
                    'ensemble_weights': ensemble_result.get('weights', {})
                }
            )
            
        except Exception as e:
            logger.error(f"Error synthesizing signal: {e}")
            return None
    
    async def update_from_result(self, trading_result: Dict[str, Any]) -> None:
        """
        Update neural system from trading results
        
        Args:
            trading_result: Result from trading execution
        """
        try:
            # Extract relevant information from trading result
            pnl = trading_result.get('pnl', 0)
            signal_accuracy = trading_result.get('signal_accuracy', 0.5)
            execution_quality = trading_result.get('execution_quality', 0.5)
            
            # Update performance tracking
            self.performance_tracker.record_trading_result({
                'pnl': pnl,
                'signal_accuracy': signal_accuracy,
                'execution_quality': execution_quality,
                'timestamp': datetime.now()
            })
            
            # Update neural components if available
            if self._neural_components_available():
                await self._update_neural_components(trading_result)
            
            logger.debug(f"Updated neural system from trading result: PnL={pnl}, Accuracy={signal_accuracy}")
            
        except Exception as e:
            logger.error(f"Error updating neural system: {e}")
            self.error_handler.handle_error(e)
    
    async def _update_neural_components(self, trading_result: Dict[str, Any]) -> None:
        """Update neural components with trading results"""
        try:
            # Update ensemble network
            if hasattr(self.ensemble_network, 'update_from_result'):
                await self.ensemble_network.update_from_result(trading_result)
            
            # Update regime generator
            if hasattr(self.regime_generator, 'update_from_result'):
                await self.regime_generator.update_from_result(trading_result)
            
            # Update feature selector
            if hasattr(self.feature_selector, 'update_from_result'):
                await self.feature_selector.update_from_result(trading_result)
                
        except Exception as e:
            logger.error(f"Error updating neural components: {e}")
    
    def get_configuration(self) -> Dict[str, Any]:
        """Get neural strategy configuration"""
        return {
            'latency_target_ms': self.config.latency_target_ms,
            'throughput_target': self.config.throughput_target,
            'attention_heads': self.config.attention_heads,
            'embedding_dim': self.config.embedding_dim,
            'temporal_layers': self.config.temporal_layers,
            'gpt5_enabled': self.config.gpt5_enabled,
            'max_position_size': self.config.max_position_size,
            'min_confidence_threshold': self.config.min_confidence_threshold,
            'max_uncertainty_threshold': self.config.max_uncertainty_threshold
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return self.performance_tracker.get_metrics()
    
    def _validate_market_data(self, market_data: Dict[str, Any]) -> bool:
        """Validate market data"""
        required_keys = ['price', 'volume']
        return all(key in market_data for key in required_keys)
    
    def _validate_signal(self, signal: NeuralSignal) -> bool:
        """Validate generated signal"""
        if not signal:
            return False
        
        if signal.confidence < 0 or signal.confidence > 1:
            return False
        
        if signal.uncertainty < 0 or signal.uncertainty > 1:
            return False
        
        if signal.strength < 0:
            return False
        
        return True

class CoreSystemInterface:
    """
    Interface between core system and neural strategy
    
    This interface provides the neural strategy with access to core system
    functionality while maintaining proper separation of concerns.
    """
    
    def __init__(self, core_system):
        """
        Initialize core system interface
        
        Args:
            core_system: Reference to the core system
        """
        self.core_system = core_system
        self.signal_generator = getattr(core_system, 'signal_generator', None)
        self.execution_engine = getattr(core_system, 'execution_engine', None)
        self.risk_manager = getattr(core_system, 'risk_manager', None)
        self.portfolio_manager = getattr(core_system, 'portfolio_manager', None)
    
    async def execute_signals(self, signals: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute signals through core system
        
        Args:
            signals: Signals to execute
            
        Returns:
            Execution result
        """
        try:
            if not self.execution_engine:
                raise ValueError("Execution engine not available")
            
            # Convert neural signals to core system format
            core_signals = self._convert_signals_to_core_format(signals)
            
            # Execute through core system
            result = await self.execution_engine.execute_signals(core_signals)
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing signals: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def get_market_data(self) -> Dict[str, Any]:
        """
        Get market data for neural processing
        
        Returns:
            Market data dictionary
        """
        try:
            # Get market data from core system
            if hasattr(self.core_system, 'get_market_data'):
                return self.core_system.get_market_data()
            else:
                return {}
                
        except Exception as e:
            logger.error(f"Error getting market data: {e}")
            return {}
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get core system status
        
        Returns:
            System status dictionary
        """
        try:
            status = {
                'signal_generator_available': self.signal_generator is not None,
                'execution_engine_available': self.execution_engine is not None,
                'risk_manager_available': self.risk_manager is not None,
                'portfolio_manager_available': self.portfolio_manager is not None
            }
            
            # Add component-specific status
            if self.signal_generator:
                status['signal_generator_status'] = getattr(self.signal_generator, 'get_status', lambda: {})()
            
            if self.execution_engine:
                status['execution_engine_status'] = getattr(self.execution_engine, 'get_status', lambda: {})()
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {'error': str(e)}
    
    def _convert_signals_to_core_format(self, neural_signals: Dict[str, Any]) -> Dict[str, Any]:
        """Convert neural signals to core system format"""
        try:
            # Extract signal information
            signal_type = neural_signals.get('signal_type', 'HOLD')
            confidence = neural_signals.get('confidence', 0.5)
            strength = neural_signals.get('strength', 0.0)
            
            # Convert to core system format
            core_signals = {
                'action': signal_type.lower(),
                'confidence': confidence,
                'strength': strength,
                'timestamp': neural_signals.get('timestamp', datetime.now()),
                'metadata': neural_signals.get('metadata', {})
            }
            
            return core_signals
            
        except Exception as e:
            logger.error(f"Error converting signals: {e}")
            return {'action': 'hold', 'confidence': 0.0, 'strength': 0.0}

class PerformanceTracker:
    """Track performance metrics for neural system"""
    
    def __init__(self):
        self.processing_times = []
        self.trading_results = []
        self.max_history = 1000
    
    def record_processing_time(self, processing_time_ms: float):
        """Record processing time"""
        self.processing_times.append(processing_time_ms)
        if len(self.processing_times) > self.max_history:
            self.processing_times.pop(0)
    
    def record_trading_result(self, result: Dict[str, Any]):
        """Record trading result"""
        self.trading_results.append(result)
        if len(self.trading_results) > self.max_history:
            self.trading_results.pop(0)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        if not self.processing_times:
            return {}
        
        return {
            'avg_processing_time_ms': np.mean(self.processing_times),
            'max_processing_time_ms': np.max(self.processing_times),
            'min_processing_time_ms': np.min(self.processing_times),
            'processing_time_std_ms': np.std(self.processing_times),
            'total_signals_generated': len(self.processing_times),
            'recent_trading_results': self.trading_results[-10:] if self.trading_results else []
        }

class ErrorHandler:
    """Handle errors in neural system"""
    
    def __init__(self):
        self.error_count = 0
        self.error_history = []
        self.max_error_history = 100
    
    def handle_error(self, error: Exception):
        """Handle error"""
        self.error_count += 1
        error_info = {
            'timestamp': datetime.now(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'error_count': self.error_count
        }
        
        self.error_history.append(error_info)
        if len(self.error_history) > self.max_error_history:
            self.error_history.pop(0)
        
        logger.error(f"Neural system error #{self.error_count}: {error}")
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get error summary"""
        return {
            'total_errors': self.error_count,
            'recent_errors': self.error_history[-10:] if self.error_history else [],
            'error_rate': self.error_count / max(1, len(self.error_history))
        }
