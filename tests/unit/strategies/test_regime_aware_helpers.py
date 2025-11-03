"""
Regime-Aware Test Helpers
==========================

Helper functions for regime-aware testing across all strategies.

Author: StatArb_Gemini Test Suite
Date: November 3, 2025
Priority 2: Regime-Aware Testing
"""

from unittest.mock import Mock, MagicMock
from typing import Dict, Any, Optional


def create_mock_regime_engine(
    primary_regime: str = 'normal_volatility',
    volatility_regime: str = 'normal',
    trend_regime: str = 'trending',
    confidence: float = 0.8
) -> Mock:
    """
    Create a mock regime engine for testing
    
    Args:
        primary_regime: Primary market regime
        volatility_regime: Volatility classification (low/normal/high/extreme)
        trend_regime: Trend classification (trending/sideways/choppy)
        confidence: Regime confidence (0.0-1.0)
    
    Returns:
        Mock regime engine with specified regime context
    """
    regime_engine = Mock()
    
    # Mock get_current_regime_context
    regime_context = {
        'primary_regime': primary_regime,
        'volatility_regime': volatility_regime,
        'trend_regime': trend_regime,
        'confidence': confidence
    }
    
    regime_engine.get_current_regime_context = Mock(return_value=regime_context)
    regime_engine.current_regime_context = regime_context
    
    return regime_engine


def create_regime_context_mock(
    primary_regime: str = 'normal_volatility',
    volatility_regime: str = 'normal',
    trend_regime: str = 'trending',
    confidence: float = 0.8
) -> Mock:
    """
    Create a mock regime context object
    
    Args:
        primary_regime: Primary market regime
        volatility_regime: Volatility classification
        trend_regime: Trend classification
        confidence: Regime confidence
    
    Returns:
        Mock regime context object
    """
    regime_context = Mock()
    regime_context.primary_regime = primary_regime
    regime_context.volatility_regime = volatility_regime
    regime_context.trend_regime = trend_regime
    regime_context.confidence = confidence
    
    return regime_context


# Standard regime configurations for testing
REGIME_CONFIGS = {
    'low_volatility': {
        'primary_regime': 'low_volatility',
        'volatility_regime': 'low',
        'trend_regime': 'trending',
        'confidence': 0.85
    },
    'normal_volatility': {
        'primary_regime': 'normal_volatility',
        'volatility_regime': 'normal',
        'trend_regime': 'trending',
        'confidence': 0.80
    },
    'high_volatility': {
        'primary_regime': 'high_volatility',
        'volatility_regime': 'high',
        'trend_regime': 'choppy',
        'confidence': 0.75
    },
    'extreme_volatility': {
        'primary_regime': 'extreme_volatility',
        'volatility_regime': 'extreme',
        'trend_regime': 'chaotic',
        'confidence': 0.70
    },
    'sideways': {
        'primary_regime': 'normal_volatility',
        'volatility_regime': 'normal',
        'trend_regime': 'sideways',
        'confidence': 0.80
    },
    'trending': {
        'primary_regime': 'normal_volatility',
        'volatility_regime': 'normal',
        'trend_regime': 'trending',
        'confidence': 0.82
    },
    'choppy': {
        'primary_regime': 'high_volatility',
        'volatility_regime': 'high',
        'trend_regime': 'choppy',
        'confidence': 0.70
    }
}


def get_regime_config(regime_name: str) -> Dict[str, Any]:
    """
    Get predefined regime configuration
    
    Args:
        regime_name: Name of regime (e.g., 'low_volatility', 'high_volatility')
    
    Returns:
        Dict with regime configuration
    """
    return REGIME_CONFIGS.get(regime_name, REGIME_CONFIGS['normal_volatility']).copy()

