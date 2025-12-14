"""
Paper Trading Module
====================

Main paper trading engine that integrates all components for
dual-mode (backtest + paper trading) operation.

Components:
- PaperTradingEngine: Main event loop orchestrating all components

Author: StatArb_Gemini Core Engine
Version: 1.0.0 (Paper Trading Evolution - Phase 6)
"""

from .engine import PaperTradingEngine

__all__ = [
    'PaperTradingEngine',
]

