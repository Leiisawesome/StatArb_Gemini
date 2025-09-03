"""
Optimization Components
======================

Optimization functionality including:
- portfolio_optimizer.py: Portfolio optimization and position sizing
- timing_engine.py: Market timing and execution optimization

These components handle optimization aspects of signal generation
including portfolio allocation and execution timing.
"""

from .portfolio_optimizer import (
    PortfolioOptimizationEngine,
    AllocationResult,
    PositionSize,
    OptimizationMethod,
    PositionSizeMethod,
    OptimizationConfig
)

from .timing_engine import (
    TimingEngine,
    TimingSignal,
    ExecutionWindow,
    TimingStrategy,
    ExecutionTiming,
    TimingConfig
)

# Backward compatibility
PortfolioOptimizer = PortfolioOptimizationEngine
PositionSizer = PortfolioOptimizationEngine
TimingOptimizer = TimingEngine

__all__ = [
    'PortfolioOptimizationEngine',
    'AllocationResult',
    'PositionSize',
    'OptimizationMethod',
    'PositionSizeMethod',
    'OptimizationConfig',
    'TimingEngine',
    'TimingSignal',
    'ExecutionWindow',
    'TimingStrategy',
    'ExecutionTiming',
    'TimingConfig',
    'PortfolioOptimizer',  # Backward compatibility
    'PositionSizer',       # Backward compatibility
    'TimingOptimizer'      # Backward compatibility
]
