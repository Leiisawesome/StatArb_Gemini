"""
Template-Aware Scenario Layer Integration
=========================================

Integration layer connecting the scenario layer with the hybrid template system,
providing template-aware backtesting, simulation, and scenario testing capabilities.

Author: Pro Quant Desk Trader
"""

from .template_backtesting_engine import TemplateBacktestingEngine
from .template_scenario_manager import TemplateScenarioManager
from .category_aware_simulator import CategoryAwareSimulator
from .template_performance_evaluator import TemplatePerformanceEvaluator
from .scenario_template_bridge import ScenarioTemplateBridge

__all__ = [
    'TemplateBacktestingEngine',
    'TemplateScenarioManager', 
    'CategoryAwareSimulator',
    'TemplatePerformanceEvaluator',
    'ScenarioTemplateBridge'
]
