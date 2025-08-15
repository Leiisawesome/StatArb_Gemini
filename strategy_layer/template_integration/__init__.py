"""
Template Integration Layer
=========================

Integration layer connecting the hybrid template system with the existing
strategy layer, providing backward compatibility and template-centric execution.

Author: Pro Quant Desk Trader
"""

from .template_strategy_adapter import TemplateStrategyAdapter
from .template_strategy_manager import TemplateStrategyManager
from .template_strategy_executor import TemplateStrategyExecutor
from .legacy_migration_bridge import LegacyMigrationBridge
from .template_performance_tracker import TemplatePerformanceTracker

__all__ = [
    'TemplateStrategyAdapter',
    'TemplateStrategyManager',
    'TemplateStrategyExecutor',
    'LegacyMigrationBridge',
    'TemplatePerformanceTracker'
]
