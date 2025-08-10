"""
Signal Generation Module for AI-Ready Statistical Arbitrage System
=================================================================

This module provides advanced signal generation capabilities with:
- AI-ready model interfaces and feature engineering
- Enhanced regime detection with real-time adaptation
- Professional-grade signal generation with risk management
- Scalable architecture for institutional deployment

Key Components:
- SignalGenerator: Core signal generation engine
- RegimeDetector: Market state classification
- ModelEnsemble: AI-ready model aggregation
- FeatureEngine: Advanced feature engineering for ML models

Author: Pro Quant Desk Trader
"""

import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# Core signal generation components
try:
    from .signal_generator import (
        SignalGenerator,
        SignalConfig, 
        TradingSignal,
        SignalType,
        SignalStrength
    )
    
    from .regime_detector import (
        RegimeDetector,
        RegimeType,
        RegimeConfig,
        RegimeState,
        MarketRegime
    )
    
    # ModelEnsemble removed - functionality moved to strategy_layer
    
    from .feature_engine import (
        FeatureEngine,
        FeatureConfig,
        FeatureSet,
        TechnicalFeatures,
        MarketMicrostructure
    )
    
    logger.info("Signal generation module loaded successfully")
    
except ImportError as e:
    logger.warning(f"Some signal generation components not available: {e}")
    # Graceful degradation - define minimal interface
    SignalGenerator = None
    RegimeDetector = None
    FeatureEngine = None

# Module exports
__all__ = [
    # Core signal generation
    'SignalGenerator',
    'SignalConfig', 
    'TradingSignal',
    'SignalType',
    'SignalStrength',
    
    # Regime detection  
    'RegimeDetector',
    'RegimeType',
    'RegimeConfig',
    'RegimeState',
    'MarketRegime',
    
    # Model ensemble (moved to strategy_layer)
    
    # Feature engineering
    'FeatureEngine',
    'FeatureConfig',
    'FeatureSet',
    'TechnicalFeatures',
    'MarketMicrostructure'
]

def create_signal_generator(config: Optional[Dict[str, Any]] = None) -> Optional['SignalGenerator']:
    """
    Factory function to create a SignalGenerator instance
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        SignalGenerator instance or None if not available
    """
    if SignalGenerator is None:
        logger.error("SignalGenerator not available")
        return None
    
    try:
        return SignalGenerator(config)
    except Exception as e:
        logger.error(f"Failed to create SignalGenerator: {e}")
        return None

def create_regime_detector(config: Optional[Dict[str, Any]] = None) -> Optional['RegimeDetector']:
    """
    Factory function to create a RegimeDetector instance
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        RegimeDetector instance or None if not available
    """
    if RegimeDetector is None:
        logger.error("RegimeDetector not available")
        return None
    
    try:
        return RegimeDetector(config)
    except Exception as e:
        logger.error(f"Failed to create RegimeDetector: {e}")
        return None

def get_module_health() -> Dict[str, Any]:
    """
    Get health status of signal generation module
    
    Returns:
        Dictionary with module health information
    """
    components = {
        'SignalGenerator': SignalGenerator is not None,
        'RegimeDetector': RegimeDetector is not None,
        'FeatureEngine': FeatureEngine is not None
    }
    
    available_count = sum(components.values())
    total_count = len(components)
    
    return {
        'module': 'signal_generation',
        'status': 'healthy' if available_count == total_count else 'degraded',
        'components': components,
        'availability': f"{available_count}/{total_count}",
        'timestamp': logger.handlers[0].formatter.formatTime(logging.LogRecord('', 0, '', 0, '', (), None)) if logger.handlers else None
    } 