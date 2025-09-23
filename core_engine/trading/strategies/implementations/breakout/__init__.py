"""
Breakout Strategies

Breakout and breakdown strategies that trade on price breakouts above resistance
or below support levels. These strategies identify consolidation patterns and
enter positions when price breaks out of established ranges.
"""

from .advanced_breakout import AdvancedBreakoutStrategy, BreakoutConfig, BreakoutType, ConsolidationPattern

__all__ = [
    'AdvancedBreakoutStrategy',
    'BreakoutConfig',
    'BreakoutType',
    'ConsolidationPattern'
]