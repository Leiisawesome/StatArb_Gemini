"""
Composite Template Infrastructure
=================================

Complex strategies combining multiple templates through composition patterns.
"""

from .strategy_composer import StrategyComposer
from .portfolio_templates import PortfolioTemplates
from .ensemble_templates import EnsembleTemplates

__all__ = [
    'StrategyComposer',
    'PortfolioTemplates',
    'EnsembleTemplates'
]
