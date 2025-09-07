"""
Core Structure Signal Conversion Module
======================================

Professional signal conversion system integrated into core_structure
for transforming raw strategy outputs into standardized trading signals.

Migration Summary:
- Moved from trade_engine/conversion to core_structure/components/signal_generation/conversion
- Full integration with unified signal generation pipeline
- Enhanced performance through core_structure infrastructure

Author: Professional Trading System Architecture
Version: 2.0.0 (Core Structure Integrated)
"""

from .signal_converter import SignalConverter, SignalConversionConfig

__all__ = [
    'SignalConverter',
    'SignalConversionConfig'
]
