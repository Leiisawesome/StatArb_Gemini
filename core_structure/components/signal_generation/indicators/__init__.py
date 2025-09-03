"""
Technical Indicators Components
==============================

Technical indicator functionality including:
- technical_indicators.py: All technical indicators and signal processing

This component consolidates all technical indicator calculations
and signal processing functionality.
"""

from .technical_indicators import (
    TechnicalIndicatorsEngine,
    IndicatorResult,
    IndicatorType,
    IndicatorStatus,
    IndicatorConfig
)

# Backward compatibility
TechnicalIndicators = TechnicalIndicatorsEngine
CustomIndicators = TechnicalIndicatorsEngine
SignalProcessor = TechnicalIndicatorsEngine

__all__ = [
    'TechnicalIndicatorsEngine',
    'IndicatorResult',
    'IndicatorType',
    'IndicatorStatus',
    'IndicatorConfig',
    'TechnicalIndicators',  # Backward compatibility
    'CustomIndicators',     # Backward compatibility
    'SignalProcessor'       # Backward compatibility
]
