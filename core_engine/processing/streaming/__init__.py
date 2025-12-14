"""
Streaming Processing Module
===========================

Components for real-time streaming data processing in paper trading mode.

- StreamingBufferManager: Per-symbol rolling DataFrames for batch indicator reuse
- StreamingIndicatorAdapter: Wraps batch indicators for streaming use
- StreamingFeatureAdapter: Apply pre-trained scalers to single rows

Author: StatArb_Gemini Core Engine
Version: 1.0.0 (Paper Trading Evolution - Phase 2)
"""

from .buffer_manager import StreamingBufferManager
from .adapters import StreamingIndicatorAdapter, StreamingFeatureAdapter

__all__ = [
    'StreamingBufferManager',
    'StreamingIndicatorAdapter',
    'StreamingFeatureAdapter',
]

