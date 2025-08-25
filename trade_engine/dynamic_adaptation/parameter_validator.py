"""
Parameter validation for dynamic adaptation system.
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Union
import logging
from ..templates.base_template import BaseTemplate, ParameterBounds
from ..templates.template_registry import get_trade_engine_template_registry


@dataclass
class ValidationResult:
    """Result of parameter validation."""
    valid: bool
    errors: List[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
    
    @property
    def error_message(self) -> str:
        """Get formatted error message."""
        if not self.errors:
            return ""
        return "; ".join(self.errors)
    
    @property
    def warning_message(self) -> str:
        """Get formatted warning message."""
        if not self.warnings:
            return ""
        return "; ".join(self.warnings)


class ParameterValidator:
    """Validates parameter changes against template bounds and constraints."""
    
    def __init__(self, template_id: str):
        self.template_id = template_id
        self.logger = logging.getLogger(__name__)
        
        # Get template from new trade engine registry
        registry = get_trade_engine_template_registry()
        self.template = registry.get_template(template_id)
        if not self.template:
            raise ValueError(f"Template {template_id} not found in registry")
        
        self.parameter_bounds = self.template._parameter_bounds
        
    def validate_parameter_change(self, 
                                parameter_name: str, 
                                new_value: Any,
                                current_value: Any = None) -> ValidationResult:
        """
        Validate a single parameter change.
        
        Args:
            parameter_name: Name of parameter to validate
            new_value: Proposed new value
            current_value: Current value (for relative change validation)
            
        Returns:
            ValidationResult with validation status and any errors/warnings
        """
        errors = []
        warnings = []
        
        # Check if parameter exists in template
        if parameter_name not in self.parameter_bounds:
            errors.append(f"Parameter '{parameter_name}' not defined in template '{self.template_id}'")
            return ValidationResult(valid=False, errors=errors)
        
        bounds = self.parameter_bounds[parameter_name]
        
        # Type validation first
        type_valid, type_error = self._validate_type(parameter_name, new_value, bounds)
        if not type_valid:
            errors.append(type_error)
            # Don't continue with range validation if type is wrong
            return ValidationResult(valid=False, errors=errors, warnings=warnings)
        
        # Range validation (only if type is correct)
        range_valid, range_error = self._validate_range(parameter_name, new_value, bounds)
        if not range_valid:
            errors.append(range_error)
        
        # Change magnitude validation (if current value provided)
        if current_value is not None:
            change_warnings = self._validate_change_magnitude(parameter_name, current_value, new_value, bounds)
            warnings.extend(change_warnings)
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def validate_parameter_set(self, 
                             new_parameters: Dict[str, Any],
                             current_parameters: Dict[str, Any] = None) -> ValidationResult:
        """
        Validate a complete set of parameter changes.
        
        Args:
            new_parameters: Dictionary of parameter changes
            current_parameters: Current parameter values
            
        Returns:
            ValidationResult with overall validation status
        """
        all_errors = []
        all_warnings = []
        
        # Validate each parameter individually
        for param_name, new_value in new_parameters.items():
            current_value = current_parameters.get(param_name) if current_parameters else None
            
            result = self.validate_parameter_change(param_name, new_value, current_value)
            
            if not result.valid:
                all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)
        
        # Cross-parameter validation
        cross_validation_result = self._validate_parameter_relationships(new_parameters, current_parameters)
        all_errors.extend(cross_validation_result.errors)
        all_warnings.extend(cross_validation_result.warnings)
        
        return ValidationResult(
            valid=len(all_errors) == 0,
            errors=all_errors,
            warnings=all_warnings
        )
    
    def validate_adaptation_magnitude(self, 
                                    parameter_changes: Dict[str, Any],
                                    current_parameters: Dict[str, Any],
                                    max_change_percentage: float = 0.25) -> ValidationResult:
        """
        Validate that parameter changes don't exceed maximum adaptation magnitude.
        
        Args:
            parameter_changes: Proposed parameter changes
            current_parameters: Current parameter values
            max_change_percentage: Maximum allowed change as percentage (0.25 = 25%)
            
        Returns:
            ValidationResult with magnitude validation
        """
        errors = []
        warnings = []
        
        for param_name, new_value in parameter_changes.items():
            if param_name not in current_parameters:
                warnings.append(f"No current value for parameter '{param_name}' - cannot validate change magnitude")
                continue
            
            current_value = current_parameters[param_name]
            
            # Calculate relative change
            if isinstance(current_value, (int, float)) and current_value != 0:
                relative_change = abs(new_value - current_value) / abs(current_value)
                
                if relative_change > max_change_percentage:
                    errors.append(
                        f"Parameter '{param_name}' change too large: "
                        f"{relative_change:.1%} > {max_change_percentage:.1%} maximum"
                    )
                elif relative_change > max_change_percentage * 0.8:  # Warning at 80% of max
                    warnings.append(
                        f"Parameter '{param_name}' change is large: {relative_change:.1%}"
                    )
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def get_safe_parameter_range(self, parameter_name: str, current_value: Any) -> Dict[str, Any]:
        """
        Get safe adaptation range for a parameter based on current value.
        
        Args:
            parameter_name: Name of parameter
            current_value: Current parameter value
            
        Returns:
            Dictionary with 'min' and 'max' safe values for adaptation
        """
        if parameter_name not in self.parameter_bounds:
            raise ValueError(f"Parameter '{parameter_name}' not found in template bounds")
        
        bounds = self.parameter_bounds[parameter_name]
        
        # Start with template bounds
        safe_min = bounds.min_value if bounds.min_value is not None else current_value * 0.5
        safe_max = bounds.max_value if bounds.max_value is not None else current_value * 2.0
        
        # Narrow to adaptation-safe range (25% change max)
        if isinstance(current_value, (int, float)):
            adaptation_range = abs(current_value) * 0.25
            safe_min = max(safe_min, current_value - adaptation_range)
            safe_max = min(safe_max, current_value + adaptation_range)
        
        return {
            'min': safe_min,
            'max': safe_max,
            'current': current_value,
            'template_min': bounds.min_value,
            'template_max': bounds.max_value
        }
    
    def _validate_type(self, parameter_name: str, value: Any, bounds: ParameterBounds) -> tuple[bool, str]:
        """Validate parameter type."""
        expected_type = bounds.data_type
        
        if not isinstance(value, expected_type):
            return False, f"Parameter '{parameter_name}' must be {expected_type.__name__}, got {type(value).__name__}"
        
        return True, ""
    
    def _validate_range(self, parameter_name: str, value: Any, bounds: ParameterBounds) -> tuple[bool, str]:
        """Validate parameter is within bounds."""
        # Min value check
        if bounds.min_value is not None and value < bounds.min_value:
            return False, f"Parameter '{parameter_name}' value {value} below minimum {bounds.min_value}"
        
        # Max value check  
        if bounds.max_value is not None and value > bounds.max_value:
            return False, f"Parameter '{parameter_name}' value {value} above maximum {bounds.max_value}"
        
        return True, ""
    
    def _validate_change_magnitude(self, 
                                 parameter_name: str,
                                 current_value: Any, 
                                 new_value: Any,
                                 bounds: ParameterBounds) -> List[str]:
        """Validate change magnitude and return warnings."""
        warnings = []
        
        if not isinstance(current_value, (int, float)) or not isinstance(new_value, (int, float)):
            return warnings
        
        if current_value == 0:
            return warnings
        
        # Calculate relative change
        relative_change = abs(new_value - current_value) / abs(current_value)
        
        # Warning for large changes
        if relative_change > 0.5:  # 50% change
            warnings.append(f"Large change in '{parameter_name}': {relative_change:.1%}")
        elif relative_change < 0.01:  # Less than 1% change
            warnings.append(f"Very small change in '{parameter_name}': {relative_change:.1%}")
        
        return warnings
    
    def _validate_parameter_relationships(self, 
                                        new_parameters: Dict[str, Any],
                                        current_parameters: Dict[str, Any] = None) -> ValidationResult:
        """
        Validate relationships between parameters.
        
        This implements business logic constraints like:
        - stop_loss_pct should be less than take_profit_pct
        - position_size should consider risk parameters
        - momentum_threshold should align with confidence_threshold
        """
        errors = []
        warnings = []
        
        # Get full parameter set (current + new changes)
        if current_parameters:
            full_params = current_parameters.copy()
            full_params.update(new_parameters)
        else:
            full_params = new_parameters
        
        # Validate stop loss vs take profit
        if 'stop_loss_pct' in full_params and 'take_profit_pct' in full_params:
            stop_loss = full_params['stop_loss_pct']
            take_profit = full_params['take_profit_pct']
            
            if stop_loss >= take_profit:
                errors.append(f"Stop loss ({stop_loss}) must be less than take profit ({take_profit})")
        
        # Validate position size vs risk parameters
        if 'position_size' in full_params:
            position_size = full_params['position_size']
            
            if position_size > 0.3:  # 30% position size
                if 'stop_loss_pct' in full_params and full_params['stop_loss_pct'] > 0.05:
                    warnings.append("Large position size with high stop loss increases risk")
        
        # Validate momentum threshold vs confidence threshold
        if 'momentum_threshold' in full_params and 'confidence_threshold' in full_params:
            momentum_thresh = full_params['momentum_threshold']
            confidence_thresh = full_params['confidence_threshold']
            
            # High momentum threshold should pair with high confidence
            if momentum_thresh > 0.02 and confidence_thresh < 0.7:
                warnings.append("High momentum threshold with low confidence may reduce signal quality")
        
        # Validate lookback periods are reasonable
        if 'lookback_period' in full_params and 'volume_lookback' in full_params:
            main_lookback = full_params['lookback_period']
            volume_lookback = full_params['volume_lookback']
            
            if volume_lookback > main_lookback:
                warnings.append("Volume lookback period longer than main lookback period")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
