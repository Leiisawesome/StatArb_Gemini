"""
Breakout Strategies

Breakout and breakdown strategies that trade on price breakouts above resistance
or below support levels. These strategies identify consolidation patterns and
enter positions when price breaks out of established ranges.
"""

from .enhanced_breakout import EnhancedBreakoutStrategy, BreakoutConfig

__all__ = [
    'AdvancedBreakoutStrategy',
    'BreakoutConfig',
    'BreakoutType',
    'ConsolidationPattern'
]