"""
Trade Engine Templates Module
============================

Advanced template system for the trade_engine, providing ML-driven templates
that replace legacy strategy_templates with modern architecture.

Author: Pro Quant Desk Trader
"""

# Import new template registry system
from .template_registry import (
    TradeEngineTemplateRegistry,
    TradeEngineTemplate,
    TradeEngineTemplateMetadata,
    TradeEngineTemplateCategory,
    TradeEngineTemplateType,
    TemplateStatus,
    get_trade_engine_template_registry
)

# Legacy template imports (for backward compatibility during migration)
try:
    from .template_bridge import TemplateStrategyBridge, TemplateConfiguration
    from .base_template import BaseTemplate, TemplateValidationError
    from .momentum_template import ProfessionalMomentumTemplate
    from .mean_reversion_template import ProfessionalMeanReversionTemplate
    from .pairs_trading_template import ProfessionalPairsTradingTemplate, PairsConfiguration
    LEGACY_TEMPLATES_AVAILABLE = True
except ImportError:
    LEGACY_TEMPLATES_AVAILABLE = False

__all__ = [
    # New template registry system
    'TradeEngineTemplateRegistry',
    'TradeEngineTemplate', 
    'TradeEngineTemplateMetadata',
    'TradeEngineTemplateCategory',
    'TradeEngineTemplateType',
    'TemplateStatus',
    'get_trade_engine_template_registry',
    
    # Legacy templates (for backward compatibility)
    'TemplateStrategyBridge',
    'TemplateConfiguration',
    'BaseTemplate',
    'TemplateValidationError',
    'ProfessionalMomentumTemplate',
    'ProfessionalMeanReversionTemplate',
    'ProfessionalPairsTradingTemplate',
    'PairsConfiguration',
    'LEGACY_TEMPLATES_AVAILABLE'
]
