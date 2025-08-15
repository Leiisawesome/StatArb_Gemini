"""
Hybrid Template Infrastructure
=============================

Three-tier template system providing single source of truth for strategy definitions.
Supports inheritance, composition, and dynamic adaptation.

Architecture:
- Base Templates: Core algorithmic patterns and foundational logic
- Specific Templates: Asset/market/regime-specific adaptations  
- Composite Templates: Complex strategies combining multiple templates

Author: Pro Quant Desk Trader
"""

from .base.template_registry import TemplateRegistry
from .base.template_inheritance import TemplateInheritanceManager
from .base.strategy_assembler import StrategyAssembler
from .base.template_validator import TemplateValidator

from .specific.asset_templates import AssetSpecificTemplates
from .specific.market_templates import MarketSpecificTemplates  
from .specific.regime_templates import RegimeSpecificTemplates

from .composite.strategy_composer import StrategyComposer
from .composite.portfolio_templates import PortfolioTemplates
from .composite.ensemble_templates import EnsembleTemplates

__all__ = [
    # Core Infrastructure
    'TemplateRegistry',
    'TemplateInheritanceManager', 
    'StrategyAssembler',
    'TemplateValidator',
    
    # Specific Templates
    'AssetSpecificTemplates',
    'MarketSpecificTemplates',
    'RegimeSpecificTemplates',
    
    # Composite Templates
    'StrategyComposer',
    'PortfolioTemplates', 
    'EnsembleTemplates'
]
