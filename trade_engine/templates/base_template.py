"""
Strategy Template System
========================

Professional strategy template system implementing the pure "WHAT" layer
for strategy definitions. Templates define strategy logic without implementation,
following the Template Pattern for clean separation of concerns.

Author: Professional Trading System Architecture
Version: 1.0.0
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
from datetime import datetime
import logging


class SignalCondition(Enum):
    """Signal condition types for template definitions."""
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    EQUAL_TO = "equal_to"
    BETWEEN = "between"
    OUTSIDE_RANGE = "outside_range"
    TREND_UP = "trend_up"
    TREND_DOWN = "trend_down"
    CROSSOVER_ABOVE = "crossover_above"
    CROSSOVER_BELOW = "crossover_below"


class TemplateValidationError(Exception):
    """Raised when template validation fails."""
    pass


@dataclass
class ParameterBounds:
    """Parameter bounds definition for template parameters."""
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_values: Optional[List[Any]] = None
    data_type: type = float
    is_required: bool = True
    default_value: Optional[Any] = None
    
    def validate(self, value: Any) -> bool:
        """Validate a parameter value against bounds."""
        if value is None and self.is_required:
            return False
        
        if value is None and not self.is_required:
            return True
        
        # Type validation
        if not isinstance(value, self.data_type):
            try:
                value = self.data_type(value)
            except (ValueError, TypeError):
                return False
        
        # Range validation
        if self.min_value is not None and value < self.min_value:
            return False
        
        if self.max_value is not None and value > self.max_value:
            return False
        
        # Allowed values validation
        if self.allowed_values is not None and value not in self.allowed_values:
            return False
        
        return True


@dataclass
class SignalRule:
    """Signal rule definition for template-based signal generation."""
    rule_id: str
    condition: SignalCondition
    indicator: str
    threshold: Union[float, str]  # Can be a parameter reference like "${threshold}"
    signal_strength: float = 1.0
    confidence_multiplier: float = 1.0
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Validate signal rule."""
        if not 0.0 <= self.signal_strength <= 1.0:
            raise TemplateValidationError(f"Signal strength must be between 0 and 1, got {self.signal_strength}")
        
        if not 0.0 <= self.confidence_multiplier <= 2.0:
            raise TemplateValidationError(f"Confidence multiplier must be between 0 and 2, got {self.confidence_multiplier}")


@dataclass
class RiskRule:
    """Risk rule definition for template-based risk management."""
    rule_id: str
    rule_type: str  # "position_size", "stop_loss", "take_profit", "max_drawdown"
    threshold: Union[float, str]
    action: str  # "limit", "exit", "reduce"
    priority: int = 1
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class EntryExitRule:
    """Entry/exit rule definition for template-based trade management."""
    rule_id: str
    trigger_type: str  # "signal", "time", "price", "indicator"
    condition: SignalCondition
    value: Union[float, str]
    action: str  # "enter_long", "enter_short", "exit_long", "exit_short"
    priority: int = 1
    metadata: Optional[Dict[str, Any]] = None


class BaseTemplate(ABC):
    """
    Abstract base class for all strategy templates.
    
    Templates define the pure "WHAT" of a strategy:
    - What signals to generate
    - What risk rules to apply
    - What entry/exit logic to use
    
    Templates do NOT implement the "HOW" - that's handled by strategy implementations.
    """
    
    def __init__(self, template_id: str, name: str, description: str):
        """
        Initialize base template.
        
        Args:
            template_id: Unique identifier for the template
            name: Human-readable name
            description: Template description
        """
        self.template_id = template_id
        self.name = name
        self.description = description
        self.logger = logging.getLogger(__name__)
        
        # Template definition components
        self._parameter_bounds: Dict[str, ParameterBounds] = {}
        self._signal_rules: List[SignalRule] = []
        self._risk_rules: List[RiskRule] = []
        self._entry_exit_rules: List[EntryExitRule] = []
        self._required_indicators: List[str] = []
        self._metadata: Dict[str, Any] = {}
        
        # Template validation
        self._is_validated = False
        
        # Initialize template-specific definitions
        self._define_template()
        
    @abstractmethod
    def _define_template(self) -> None:
        """Define template-specific signal rules, risk rules, and parameters."""
        pass
    
    def add_parameter_bounds(self, parameter_name: str, bounds: ParameterBounds) -> None:
        """Add parameter bounds definition."""
        self._parameter_bounds[parameter_name] = bounds
        self.logger.debug(f"Added parameter bounds for {parameter_name}")
    
    def add_signal_rule(self, rule: SignalRule) -> None:
        """Add signal rule to template."""
        self._signal_rules.append(rule)
        self.logger.debug(f"Added signal rule: {rule.rule_id}")
    
    def add_risk_rule(self, rule: RiskRule) -> None:
        """Add risk rule to template."""
        self._risk_rules.append(rule)
        self.logger.debug(f"Added risk rule: {rule.rule_id}")
    
    def add_entry_exit_rule(self, rule: EntryExitRule) -> None:
        """Add entry/exit rule to template."""
        self._entry_exit_rules.append(rule)
        self.logger.debug(f"Added entry/exit rule: {rule.rule_id}")
    
    def add_required_indicator(self, indicator: str) -> None:
        """Add required indicator to template."""
        if indicator not in self._required_indicators:
            self._required_indicators.append(indicator)
            self.logger.debug(f"Added required indicator: {indicator}")
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """
        Validate parameters against template bounds.
        
        Args:
            parameters: Parameters to validate
            
        Returns:
            True if all parameters are valid
            
        Raises:
            TemplateValidationError: If validation fails
        """
        errors = []
        
        # Check all required parameters are present
        for param_name, bounds in self._parameter_bounds.items():
            if bounds.is_required and param_name not in parameters:
                errors.append(f"Required parameter missing: {param_name}")
                continue
            
            if param_name in parameters:
                if not bounds.validate(parameters[param_name]):
                    errors.append(f"Parameter {param_name} validation failed: {parameters[param_name]}")
        
        if errors:
            raise TemplateValidationError(f"Parameter validation failed: {'; '.join(errors)}")
        
        return True
    
    def get_signal_rules(self) -> List[SignalRule]:
        """Get all signal rules defined in template."""
        return self._signal_rules.copy()
    
    def get_risk_rules(self) -> List[RiskRule]:
        """Get all risk rules defined in template."""
        return self._risk_rules.copy()
    
    def get_entry_exit_rules(self) -> List[EntryExitRule]:
        """Get all entry/exit rules defined in template."""
        return self._entry_exit_rules.copy()
    
    def get_required_indicators(self) -> List[str]:
        """Get all required indicators for template."""
        return self._required_indicators.copy()
    
    def get_parameter_bounds(self) -> Dict[str, ParameterBounds]:
        """Get all parameter bounds definitions."""
        return self._parameter_bounds.copy()
    
    def resolve_parameter_references(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve parameter references in template rules.
        
        Args:
            parameters: Parameter values to use for resolution
            
        Returns:
            Resolved template configuration
        """
        resolved_config = {
            'signal_rules': [],
            'risk_rules': [],
            'entry_exit_rules': [],
            'parameters': parameters.copy()
        }
        
        # Resolve signal rules
        for rule in self._signal_rules:
            resolved_rule = self._resolve_rule_parameters(rule, parameters)
            resolved_config['signal_rules'].append(resolved_rule)
        
        # Resolve risk rules
        for rule in self._risk_rules:
            resolved_rule = self._resolve_rule_parameters(rule, parameters)
            resolved_config['risk_rules'].append(resolved_rule)
        
        # Resolve entry/exit rules
        for rule in self._entry_exit_rules:
            resolved_rule = self._resolve_rule_parameters(rule, parameters)
            resolved_config['entry_exit_rules'].append(resolved_rule)
        
        return resolved_config
    
    def _resolve_rule_parameters(self, rule: Any, parameters: Dict[str, Any]) -> Any:
        """Resolve parameter references in a rule."""
        import copy
        resolved_rule = copy.deepcopy(rule)
        
        # Resolve threshold parameter references
        if hasattr(resolved_rule, 'threshold') and isinstance(resolved_rule.threshold, str):
            if resolved_rule.threshold.startswith('${') and resolved_rule.threshold.endswith('}'):
                param_name = resolved_rule.threshold[2:-1]
                if param_name in parameters:
                    resolved_rule.threshold = parameters[param_name]
        
        # Resolve value parameter references  
        if hasattr(resolved_rule, 'value') and isinstance(resolved_rule.value, str):
            if resolved_rule.value.startswith('${') and resolved_rule.value.endswith('}'):
                param_name = resolved_rule.value[2:-1]
                if param_name in parameters:
                    resolved_rule.value = parameters[param_name]
        
        return resolved_rule
    
    def get_template_info(self) -> Dict[str, Any]:
        """Get comprehensive template information."""
        return {
            'template_id': self.template_id,
            'name': self.name,
            'description': self.description,
            'parameter_count': len(self._parameter_bounds),
            'signal_rules_count': len(self._signal_rules),
            'risk_rules_count': len(self._risk_rules),
            'entry_exit_rules_count': len(self._entry_exit_rules),
            'required_indicators': self._required_indicators.copy(),
            'parameters': list(self._parameter_bounds.keys()),
            'metadata': self._metadata.copy()
        }


class TemplateRegistry:
    """
    Registry for managing strategy templates.
    
    Provides centralized template management with registration,
    discovery, and validation capabilities.
    """
    
    def __init__(self):
        """Initialize template registry."""
        self.logger = logging.getLogger(__name__)
        self._templates: Dict[str, BaseTemplate] = {}
        self._template_categories: Dict[str, List[str]] = {}
    
    def register_template(self, template: BaseTemplate, category: str = "general") -> None:
        """
        Register a template in the registry.
        
        Args:
            template: Template to register
            category: Template category for organization
        """
        if not isinstance(template, BaseTemplate):
            raise TemplateValidationError("Template must inherit from BaseTemplate")
        
        if template.template_id in self._templates:
            # Template already registered, skip silently
            return
        
        self._templates[template.template_id] = template
        
        if category not in self._template_categories:
            self._template_categories[category] = []
        
        self._template_categories[category].append(template.template_id)
        
        self.logger.info(f"Registered template {template.template_id} in category {category}")
    
    def get_template(self, template_id: str) -> Optional[BaseTemplate]:
        """Get template by ID."""
        return self._templates.get(template_id)
    
    def list_templates(self, category: Optional[str] = None) -> List[str]:
        """List available templates, optionally filtered by category."""
        if category:
            return self._template_categories.get(category, [])
        return list(self._templates.keys())
    
    def get_template_info(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get template information."""
        template = self.get_template(template_id)
        return template.get_template_info() if template else None
    
    def validate_template_parameters(self, template_id: str, parameters: Dict[str, Any]) -> bool:
        """Validate parameters for a specific template."""
        template = self.get_template(template_id)
        if not template:
            raise TemplateValidationError(f"Template {template_id} not found")
        
        return template.validate_parameters(parameters)
    
    def get_registry_status(self) -> Dict[str, Any]:
        """Get registry status information."""
        return {
            'total_templates': len(self._templates),
            'categories': dict([(cat, len(templates)) for cat, templates in self._template_categories.items()]),
            'template_ids': list(self._templates.keys())
        }


# Global template registry instance
template_registry = TemplateRegistry()


def register_default_templates():
    """Register default templates with the registry"""
    try:
        # Register momentum template
        from .momentum_template import ProfessionalMomentumTemplate
        momentum_template = ProfessionalMomentumTemplate()
        template_registry.register_template(momentum_template, "momentum")
    except ImportError:
        pass
    
    try:
        # Register mean reversion template
        from .mean_reversion_template import ProfessionalMeanReversionTemplate
        mean_reversion_template = ProfessionalMeanReversionTemplate()
        template_registry.register_template(mean_reversion_template, "mean_reversion")
    except ImportError:
        pass
    
    try:
        # Register pairs trading template
        from .pairs_trading_template import ProfessionalPairsTradingTemplate
        pairs_template = ProfessionalPairsTradingTemplate()
        template_registry.register_template(pairs_template, "pairs_trading")
    except ImportError:
        pass


# Auto-register templates on import
register_default_templates()
