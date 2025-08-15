"""
Dynamic Risk Control - Template-Aware Adaptive Risk Management
==============================================================

Template-inheritance-aware adaptive risk management that dynamically adjusts
risk parameters, position sizes, and stop-losses based on market conditions.

Author: Pro Quant Desk Trader
"""

import asyncio
import logging
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from collections import deque

from strategy_templates.base import TemplateRegistry, TemplateCategory, TemplateInheritanceManager


class RiskAdaptationMode(Enum):
    """Risk adaptation modes"""
    CONSERVATIVE = "conservative"    # Minimize risk exposure
    MODERATE = "moderate"           # Balanced risk management
    AGGRESSIVE = "aggressive"       # Allow higher risk for returns
    VOLATILITY_BASED = "volatility_based"  # Adapt based on volatility
    DRAWDOWN_BASED = "drawdown_based"      # Adapt based on drawdown


class RiskMetricType(Enum):
    """Types of risk metrics"""
    POSITION_SIZE = "position_size"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    MAX_DRAWDOWN = "max_drawdown"
    VAR = "value_at_risk"
    LEVERAGE = "leverage"
    CORRELATION = "correlation"
    VOLATILITY = "volatility"


@dataclass
class RiskParameters:
    """Risk management parameters"""
    max_position_size: float = 0.1      # 10% max position
    stop_loss_pct: float = 0.05         # 5% stop loss
    take_profit_pct: float = 0.15       # 15% take profit
    max_drawdown_limit: float = 0.20    # 20% max drawdown
    max_daily_loss: float = 0.05        # 5% max daily loss
    var_confidence: float = 0.95        # 95% VaR confidence
    max_leverage: float = 2.0           # 2x max leverage
    correlation_limit: float = 0.7      # 70% max correlation
    volatility_limit: float = 0.30     # 30% max volatility


@dataclass
class RiskControlConfig:
    """Configuration for dynamic risk control"""
    # Adaptation settings
    adaptation_mode: RiskAdaptationMode = RiskAdaptationMode.MODERATE
    adaptation_frequency: timedelta = timedelta(minutes=30)
    min_confidence_threshold: float = 0.7
    
    # Template category risk rules
    category_risk_rules: Dict[TemplateCategory, Dict[str, Any]] = field(default_factory=lambda: {
        TemplateCategory.BASE: {
            'max_risk_adjustment': 0.1,      # 10% max adjustment
            'risk_tolerance': 0.5,           # Conservative
            'adaptation_speed': 0.3          # Slow adaptation
        },
        TemplateCategory.SPECIFIC: {
            'max_risk_adjustment': 0.2,      # 20% max adjustment
            'risk_tolerance': 0.7,           # Moderate
            'adaptation_speed': 0.6          # Medium adaptation
        },
        TemplateCategory.COMPOSITE: {
            'max_risk_adjustment': 0.3,      # 30% max adjustment
            'risk_tolerance': 0.9,           # Aggressive
            'adaptation_speed': 0.9          # Fast adaptation
        }
    })
    
    # Risk thresholds for adaptation triggers
    risk_thresholds: Dict[str, float] = field(default_factory=lambda: {
        'high_volatility_threshold': 0.25,
        'drawdown_trigger_threshold': 0.10,
        'correlation_warning_threshold': 0.60,
        'var_breach_threshold': 0.05
    })


@dataclass
class RiskAdaptationResult:
    """Result of risk control adaptation"""
    success: bool
    adapted_parameters: RiskParameters
    adaptation_magnitude: float
    risk_reduction_estimate: float
    confidence_score: float
    adaptation_reasons: List[str]
    template_compliance: bool
    execution_time_ms: float
    error_message: Optional[str] = None


class DynamicRiskControl:
    """
    Template-inheritance-aware adaptive risk management
    """
    
    def __init__(self, 
                 template_registry: TemplateRegistry,
                 config: Optional[RiskControlConfig] = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.template_registry = template_registry
        self.config = config or RiskControlConfig()
        
        # Initialize components
        self.inheritance_manager = TemplateInheritanceManager(template_registry)
        
        # Risk control state
        self.current_template_id: Optional[str] = None
        self.current_template_category: Optional[TemplateCategory] = None
        self.base_risk_parameters = RiskParameters()
        self.adapted_risk_parameters = RiskParameters()
        
        # Risk tracking
        self.drawdown_history: deque = deque(maxlen=100)
        self.volatility_history: deque = deque(maxlen=50)
        self.position_history: deque = deque(maxlen=100)
        self.loss_history: deque = deque(maxlen=100)
        
        # Adaptation tracking
        self.adaptation_history: List[RiskAdaptationResult] = []
        self.last_adaptation_time: Optional[datetime] = None
        self.risk_breach_count: Dict[str, int] = {}
        
        # Portfolio state
        self.current_portfolio_value: float = 100000.0  # Default $100k
        self.current_drawdown: float = 0.0
        self.daily_pnl: float = 0.0
        
        self.logger.info("Dynamic Risk Control initialized")
    
    def initialize_for_template(self, template_id: str, initial_portfolio_value: float = 100000.0):
        """Initialize risk control for a specific template"""
        try:
            template = self.template_registry.get_template(template_id)
            if not template:
                raise ValueError(f"Template {template_id} not found")
            
            self.current_template_id = template_id
            self.current_template_category = template.metadata.category
            self.current_portfolio_value = initial_portfolio_value
            
            # Extract risk parameters from template
            self.base_risk_parameters = self._extract_template_risk_parameters(template_id)
            self.adapted_risk_parameters = RiskParameters(
                max_position_size=self.base_risk_parameters.max_position_size,
                stop_loss_pct=self.base_risk_parameters.stop_loss_pct,
                take_profit_pct=self.base_risk_parameters.take_profit_pct,
                max_drawdown_limit=self.base_risk_parameters.max_drawdown_limit,
                max_daily_loss=self.base_risk_parameters.max_daily_loss,
                var_confidence=self.base_risk_parameters.var_confidence,
                max_leverage=self.base_risk_parameters.max_leverage,
                correlation_limit=self.base_risk_parameters.correlation_limit,
                volatility_limit=self.base_risk_parameters.volatility_limit
            )
            
            # Reset state
            self.drawdown_history.clear()
            self.volatility_history.clear()
            self.position_history.clear()
            self.loss_history.clear()
            self.adaptation_history.clear()
            self.risk_breach_count.clear()
            self.last_adaptation_time = None
            self.current_drawdown = 0.0
            self.daily_pnl = 0.0
            
            self.logger.info(f"Risk control initialized for template {template_id} (category: {self.current_template_category.value})")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize risk control: {e}")
            raise
    
    async def validate_adaptive_risk(self, 
                                   signals: List[Dict[str, Any]], 
                                   portfolio_state: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Validate and adapt risk for trading signals
        """
        try:
            if not self.current_template_id:
                raise ValueError("Risk control not initialized for template")
            
            start_time = datetime.now()
            
            # Update portfolio state
            self._update_portfolio_state(portfolio_state)
            
            # Check if risk adaptation is needed
            adaptation_needed, adaptation_reasons = self._check_risk_adaptation_triggers()
            
            # Perform risk adaptation if needed
            adaptation_result = None
            if adaptation_needed:
                adaptation_result = await self._perform_risk_adaptation(adaptation_reasons)
                if adaptation_result.success:
                    self.adaptation_history.append(adaptation_result)
                    self.last_adaptation_time = datetime.now()
                    self.logger.info(f"Risk adaptation performed: {adaptation_result.risk_reduction_estimate:.2%} risk reduction")
            
            # Validate signals with current risk parameters
            validated_signals = []
            risk_metrics = {}
            
            for signal in signals:
                validated_signal, signal_risk_metrics = await self._validate_signal_risk(signal, portfolio_state)
                if validated_signal:
                    validated_signals.append(validated_signal)
                    risk_metrics[signal.get('symbol', 'unknown')] = signal_risk_metrics
            
            # Calculate portfolio-level risk metrics
            portfolio_risk_metrics = self._calculate_portfolio_risk_metrics(validated_signals, portfolio_state)
            
            # Prepare risk summary
            risk_summary = {
                'validated_signals_count': len(validated_signals),
                'rejected_signals_count': len(signals) - len(validated_signals),
                'portfolio_risk_metrics': portfolio_risk_metrics,
                'signal_risk_metrics': risk_metrics,
                'current_risk_parameters': self._risk_parameters_to_dict(self.adapted_risk_parameters),
                'adaptation_status': {
                    'adaptation_performed': adaptation_needed,
                    'adaptation_reasons': adaptation_reasons,
                    'last_adaptation': self.last_adaptation_time.isoformat() if self.last_adaptation_time else None,
                    'adaptations_count': len(self.adaptation_history)
                },
                'risk_breaches': self.risk_breach_count.copy(),
                'execution_time_ms': (datetime.now() - start_time).total_seconds() * 1000
            }
            
            return validated_signals, risk_summary
            
        except Exception as e:
            error_msg = f"Risk validation failed: {e}"
            self.logger.error(error_msg)
            
            return [], {
                'error': error_msg,
                'validated_signals_count': 0,
                'rejected_signals_count': len(signals) if signals else 0
            }
    
    def update_portfolio_performance(self, performance_data: Dict[str, Any]):
        """Update portfolio performance for risk tracking"""
        try:
            # Update portfolio value
            if 'portfolio_value' in performance_data:
                old_value = self.current_portfolio_value
                self.current_portfolio_value = performance_data['portfolio_value']
                
                # Calculate drawdown
                if old_value > 0:
                    self.daily_pnl = (self.current_portfolio_value - old_value) / old_value
                    
                    # Update drawdown if this is a loss
                    if self.daily_pnl < 0:
                        self.current_drawdown = max(self.current_drawdown, abs(self.daily_pnl))
                        self.drawdown_history.append(self.current_drawdown)
            
            # Update volatility tracking
            if 'volatility' in performance_data:
                self.volatility_history.append(performance_data['volatility'])
            
            # Update loss tracking
            if 'daily_loss' in performance_data:
                self.loss_history.append(performance_data['daily_loss'])
            
            # Update position tracking
            if 'positions' in performance_data:
                total_position_size = sum(abs(pos.get('size', 0)) for pos in performance_data['positions'])
                self.position_history.append(total_position_size)
            
            self.logger.debug(f"Portfolio performance updated: value={self.current_portfolio_value:.2f}, drawdown={self.current_drawdown:.2%}")
            
        except Exception as e:
            self.logger.error(f"Failed to update portfolio performance: {e}")
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """Get comprehensive risk management summary"""
        return {
            'current_risk_parameters': self._risk_parameters_to_dict(self.adapted_risk_parameters),
            'base_risk_parameters': self._risk_parameters_to_dict(self.base_risk_parameters),
            'portfolio_metrics': {
                'current_value': self.current_portfolio_value,
                'current_drawdown': self.current_drawdown,
                'daily_pnl': self.daily_pnl,
                'volatility': self.volatility_history[-1] if self.volatility_history else 0.0
            },
            'adaptation_summary': {
                'total_adaptations': len(self.adaptation_history),
                'successful_adaptations': len([a for a in self.adaptation_history if a.success]),
                'average_risk_reduction': np.mean([a.risk_reduction_estimate for a in self.adaptation_history if a.success]) if self.adaptation_history else 0.0,
                'last_adaptation': self.last_adaptation_time.isoformat() if self.last_adaptation_time else None
            },
            'risk_breaches': self.risk_breach_count.copy(),
            'template_info': {
                'template_id': self.current_template_id,
                'template_category': self.current_template_category.value if self.current_template_category else None
            }
        }
    
    # Private helper methods
    def _extract_template_risk_parameters(self, template_id: str) -> RiskParameters:
        """Extract risk parameters from template and inheritance chain"""
        try:
            # Get resolved template with inheritance
            resolved_template = self.inheritance_manager.resolve_inheritance(template_id)
            if not resolved_template:
                template = self.template_registry.get_template(template_id)
                resolved_template = template if template else None
            
            if not resolved_template:
                return RiskParameters()  # Default parameters
            
            # Extract risk parameters from template
            risk_params = RiskParameters()
            
            # Check template parameters for risk settings
            if hasattr(resolved_template, 'parameters') and resolved_template.parameters:
                params = resolved_template.parameters
                
                # Map template parameters to risk parameters
                if 'max_position_size' in params:
                    risk_params.max_position_size = float(params['max_position_size'])
                if 'stop_loss_pct' in params:
                    risk_params.stop_loss_pct = float(params['stop_loss_pct'])
                if 'take_profit_pct' in params:
                    risk_params.take_profit_pct = float(params['take_profit_pct'])
                if 'max_drawdown_limit' in params:
                    risk_params.max_drawdown_limit = float(params['max_drawdown_limit'])
                if 'max_daily_loss' in params:
                    risk_params.max_daily_loss = float(params['max_daily_loss'])
                if 'max_leverage' in params:
                    risk_params.max_leverage = float(params['max_leverage'])
            
            # Check template components for risk manager settings
            if hasattr(resolved_template, 'components') and resolved_template.components:
                risk_config = resolved_template.components.get('risk_manager', {})
                
                for param_name, param_value in risk_config.items():
                    if hasattr(risk_params, param_name):
                        setattr(risk_params, param_name, float(param_value))
            
            # Apply template category defaults
            category_adjustments = self._get_category_risk_adjustments()
            risk_params = self._apply_category_adjustments(risk_params, category_adjustments)
            
            return risk_params
            
        except Exception as e:
            self.logger.error(f"Error extracting template risk parameters: {e}")
            return RiskParameters()  # Return default parameters
    
    def _get_category_risk_adjustments(self) -> Dict[str, float]:
        """Get risk parameter adjustments based on template category"""
        if self.current_template_category == TemplateCategory.BASE:
            return {
                'max_position_size_multiplier': 0.8,    # More conservative
                'stop_loss_multiplier': 0.8,            # Tighter stops
                'max_drawdown_multiplier': 0.8,         # Lower drawdown limit
                'max_leverage_multiplier': 0.7          # Lower leverage
            }
        elif self.current_template_category == TemplateCategory.SPECIFIC:
            return {
                'max_position_size_multiplier': 1.0,    # Standard
                'stop_loss_multiplier': 1.0,            # Standard stops
                'max_drawdown_multiplier': 1.0,         # Standard drawdown
                'max_leverage_multiplier': 1.0          # Standard leverage
            }
        elif self.current_template_category == TemplateCategory.COMPOSITE:
            return {
                'max_position_size_multiplier': 1.2,    # More aggressive
                'stop_loss_multiplier': 1.1,            # Wider stops
                'max_drawdown_multiplier': 1.2,         # Higher drawdown tolerance
                'max_leverage_multiplier': 1.3          # Higher leverage
            }
        else:
            return {
                'max_position_size_multiplier': 1.0,
                'stop_loss_multiplier': 1.0,
                'max_drawdown_multiplier': 1.0,
                'max_leverage_multiplier': 1.0
            }
    
    def _apply_category_adjustments(self, risk_params: RiskParameters, adjustments: Dict[str, float]) -> RiskParameters:
        """Apply category-specific adjustments to risk parameters"""
        adjusted_params = RiskParameters(
            max_position_size=risk_params.max_position_size * adjustments.get('max_position_size_multiplier', 1.0),
            stop_loss_pct=risk_params.stop_loss_pct * adjustments.get('stop_loss_multiplier', 1.0),
            take_profit_pct=risk_params.take_profit_pct,  # Keep take profit unchanged
            max_drawdown_limit=risk_params.max_drawdown_limit * adjustments.get('max_drawdown_multiplier', 1.0),
            max_daily_loss=risk_params.max_daily_loss,    # Keep daily loss limit unchanged
            var_confidence=risk_params.var_confidence,    # Keep VaR confidence unchanged
            max_leverage=risk_params.max_leverage * adjustments.get('max_leverage_multiplier', 1.0),
            correlation_limit=risk_params.correlation_limit,  # Keep correlation limit unchanged
            volatility_limit=risk_params.volatility_limit    # Keep volatility limit unchanged
        )
        
        return adjusted_params
    
    def _update_portfolio_state(self, portfolio_state: Dict[str, Any]):
        """Update internal portfolio state from external data"""
        try:
            if 'portfolio_value' in portfolio_state:
                self.current_portfolio_value = portfolio_state['portfolio_value']
            
            if 'current_drawdown' in portfolio_state:
                self.current_drawdown = portfolio_state['current_drawdown']
                self.drawdown_history.append(self.current_drawdown)
            
            if 'daily_pnl' in portfolio_state:
                self.daily_pnl = portfolio_state['daily_pnl']
            
            if 'volatility' in portfolio_state:
                self.volatility_history.append(portfolio_state['volatility'])
            
        except Exception as e:
            self.logger.error(f"Error updating portfolio state: {e}")
    
    def _check_risk_adaptation_triggers(self) -> Tuple[bool, List[str]]:
        """Check if risk adaptation is needed"""
        reasons = []
        
        try:
            # Check adaptation frequency
            if self.last_adaptation_time:
                time_since_last = datetime.now() - self.last_adaptation_time
                if time_since_last < self.config.adaptation_frequency:
                    return False, []
            
            # Check drawdown breach
            if self.current_drawdown > self.config.risk_thresholds['drawdown_trigger_threshold']:
                reasons.append("drawdown_breach")
                self.risk_breach_count['drawdown_breach'] = self.risk_breach_count.get('drawdown_breach', 0) + 1
            
            # Check volatility spike
            if len(self.volatility_history) > 0:
                current_vol = self.volatility_history[-1]
                if current_vol > self.config.risk_thresholds['high_volatility_threshold']:
                    reasons.append("high_volatility")
                    self.risk_breach_count['high_volatility'] = self.risk_breach_count.get('high_volatility', 0) + 1
            
            # Check daily loss limit
            if abs(self.daily_pnl) > self.adapted_risk_parameters.max_daily_loss:
                reasons.append("daily_loss_breach")
                self.risk_breach_count['daily_loss_breach'] = self.risk_breach_count.get('daily_loss_breach', 0) + 1
            
            # Check consecutive losses
            if len(self.loss_history) >= 3:
                recent_losses = list(self.loss_history)[-3:]
                if all(loss > 0 for loss in recent_losses):
                    reasons.append("consecutive_losses")
            
            return len(reasons) > 0, reasons
            
        except Exception as e:
            self.logger.error(f"Error checking risk adaptation triggers: {e}")
            return False, []
    
    async def _perform_risk_adaptation(self, reasons: List[str]) -> RiskAdaptationResult:
        """Perform risk parameter adaptation"""
        try:
            start_time = datetime.now()
            
            # Create new adapted parameters
            new_params = RiskParameters(
                max_position_size=self.adapted_risk_parameters.max_position_size,
                stop_loss_pct=self.adapted_risk_parameters.stop_loss_pct,
                take_profit_pct=self.adapted_risk_parameters.take_profit_pct,
                max_drawdown_limit=self.adapted_risk_parameters.max_drawdown_limit,
                max_daily_loss=self.adapted_risk_parameters.max_daily_loss,
                var_confidence=self.adapted_risk_parameters.var_confidence,
                max_leverage=self.adapted_risk_parameters.max_leverage,
                correlation_limit=self.adapted_risk_parameters.correlation_limit,
                volatility_limit=self.adapted_risk_parameters.volatility_limit
            )
            
            # Get category risk rules
            category_rules = self.config.category_risk_rules.get(self.current_template_category, {})
            max_adjustment = category_rules.get('max_risk_adjustment', 0.2)
            adaptation_speed = category_rules.get('adaptation_speed', 0.6)
            
            # Adapt parameters based on reasons
            adaptation_magnitude = 0.0
            
            if 'drawdown_breach' in reasons:
                # Reduce position sizes and tighten stops
                position_reduction = min(max_adjustment, 0.2 * adaptation_speed)
                stop_tightening = min(max_adjustment, 0.15 * adaptation_speed)
                
                new_params.max_position_size *= (1 - position_reduction)
                new_params.stop_loss_pct *= (1 - stop_tightening)
                adaptation_magnitude += position_reduction + stop_tightening
            
            if 'high_volatility' in reasons:
                # Reduce position sizes and leverage
                volatility_adjustment = min(max_adjustment, 0.25 * adaptation_speed)
                
                new_params.max_position_size *= (1 - volatility_adjustment)
                new_params.max_leverage *= (1 - volatility_adjustment * 0.5)
                adaptation_magnitude += volatility_adjustment
            
            if 'daily_loss_breach' in reasons:
                # Emergency risk reduction
                emergency_reduction = min(max_adjustment, 0.3 * adaptation_speed)
                
                new_params.max_position_size *= (1 - emergency_reduction)
                new_params.max_daily_loss *= (1 - emergency_reduction * 0.5)
                adaptation_magnitude += emergency_reduction
            
            if 'consecutive_losses' in reasons:
                # Gradual risk reduction
                loss_adjustment = min(max_adjustment, 0.15 * adaptation_speed)
                
                new_params.max_position_size *= (1 - loss_adjustment)
                adaptation_magnitude += loss_adjustment
            
            # Ensure parameters stay within reasonable bounds
            new_params = self._enforce_risk_parameter_bounds(new_params)
            
            # Validate template compliance
            template_compliance = self._validate_risk_template_compliance(new_params)
            
            if template_compliance:
                # Calculate risk reduction estimate
                risk_reduction = self._estimate_risk_reduction(self.adapted_risk_parameters, new_params)
                
                # Calculate confidence score
                confidence_score = self._calculate_risk_adaptation_confidence(reasons, adaptation_magnitude)
                
                # Apply adaptations
                self.adapted_risk_parameters = new_params
                
                result = RiskAdaptationResult(
                    success=True,
                    adapted_parameters=new_params,
                    adaptation_magnitude=adaptation_magnitude,
                    risk_reduction_estimate=risk_reduction,
                    confidence_score=confidence_score,
                    adaptation_reasons=reasons,
                    template_compliance=True,
                    execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000
                )
                
            else:
                result = RiskAdaptationResult(
                    success=False,
                    adapted_parameters=self.adapted_risk_parameters,
                    adaptation_magnitude=0.0,
                    risk_reduction_estimate=0.0,
                    confidence_score=0.0,
                    adaptation_reasons=reasons,
                    template_compliance=False,
                    execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                    error_message="Template compliance validation failed"
                )
            
            return result
            
        except Exception as e:
            error_msg = f"Risk adaptation failed: {e}"
            self.logger.error(error_msg)
            
            return RiskAdaptationResult(
                success=False,
                adapted_parameters=self.adapted_risk_parameters,
                adaptation_magnitude=0.0,
                risk_reduction_estimate=0.0,
                confidence_score=0.0,
                adaptation_reasons=reasons,
                template_compliance=False,
                execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                error_message=error_msg
            )
    
    async def _validate_signal_risk(self, signal: Dict[str, Any], portfolio_state: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
        """Validate individual signal against risk parameters"""
        try:
            signal_copy = signal.copy()
            risk_metrics = {}
            
            # Get signal properties
            position_size = signal.get('position_size', 0.1)
            signal_strength = signal.get('strength', 0.5)
            symbol = signal.get('symbol', 'UNKNOWN')
            
            # Validate position size
            max_allowed_position = self.adapted_risk_parameters.max_position_size
            if position_size > max_allowed_position:
                # Adjust position size
                signal_copy['position_size'] = max_allowed_position
                signal_copy['position_adjusted'] = True
                risk_metrics['position_size_adjusted'] = True
                risk_metrics['original_position_size'] = position_size
                risk_metrics['adjusted_position_size'] = max_allowed_position
            
            # Calculate and validate stop loss
            current_price = signal.get('current_price', 100.0)
            signal_direction = signal.get('direction', 'buy')
            
            if signal_direction.lower() == 'buy':
                stop_loss_price = current_price * (1 - self.adapted_risk_parameters.stop_loss_pct)
                take_profit_price = current_price * (1 + self.adapted_risk_parameters.take_profit_pct)
            else:  # sell
                stop_loss_price = current_price * (1 + self.adapted_risk_parameters.stop_loss_pct)
                take_profit_price = current_price * (1 - self.adapted_risk_parameters.take_profit_pct)
            
            signal_copy['stop_loss_price'] = stop_loss_price
            signal_copy['take_profit_price'] = take_profit_price
            
            # Calculate risk metrics
            position_value = signal_copy['position_size'] * self.current_portfolio_value
            max_loss = position_value * self.adapted_risk_parameters.stop_loss_pct
            
            risk_metrics.update({
                'position_value': position_value,
                'max_potential_loss': max_loss,
                'risk_reward_ratio': self.adapted_risk_parameters.take_profit_pct / self.adapted_risk_parameters.stop_loss_pct,
                'stop_loss_price': stop_loss_price,
                'take_profit_price': take_profit_price,
                'position_risk_percentage': max_loss / self.current_portfolio_value
            })
            
            # Check if signal passes all risk checks
            if self._passes_risk_validation(signal_copy, risk_metrics):
                return signal_copy, risk_metrics
            else:
                risk_metrics['rejected'] = True
                return None, risk_metrics
            
        except Exception as e:
            self.logger.error(f"Error validating signal risk: {e}")
            return None, {'error': str(e)}
    
    def _passes_risk_validation(self, signal: Dict[str, Any], risk_metrics: Dict[str, Any]) -> bool:
        """Check if signal passes all risk validation checks"""
        
        # Check position size limit
        if signal.get('position_size', 0) > self.adapted_risk_parameters.max_position_size:
            return False
        
        # Check maximum potential loss
        max_loss_pct = risk_metrics.get('position_risk_percentage', 0)
        if max_loss_pct > self.adapted_risk_parameters.max_daily_loss:
            return False
        
        # Check portfolio drawdown limit
        if self.current_drawdown > self.adapted_risk_parameters.max_drawdown_limit:
            return False
        
        # Check volatility limit (if available)
        if len(self.volatility_history) > 0:
            current_vol = self.volatility_history[-1]
            if current_vol > self.adapted_risk_parameters.volatility_limit:
                return False
        
        return True
    
    def _calculate_portfolio_risk_metrics(self, signals: List[Dict[str, Any]], portfolio_state: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate portfolio-level risk metrics"""
        try:
            total_position_value = 0.0
            total_max_loss = 0.0
            signal_count = len(signals)
            
            for signal in signals:
                position_size = signal.get('position_size', 0)
                position_value = position_size * self.current_portfolio_value
                max_loss = position_value * self.adapted_risk_parameters.stop_loss_pct
                
                total_position_value += position_value
                total_max_loss += max_loss
            
            portfolio_utilization = total_position_value / self.current_portfolio_value if self.current_portfolio_value > 0 else 0.0
            portfolio_risk_pct = total_max_loss / self.current_portfolio_value if self.current_portfolio_value > 0 else 0.0
            
            return {
                'total_position_value': total_position_value,
                'portfolio_utilization': portfolio_utilization,
                'total_max_loss': total_max_loss,
                'portfolio_risk_percentage': portfolio_risk_pct,
                'active_signals_count': signal_count,
                'current_drawdown': self.current_drawdown,
                'daily_pnl': self.daily_pnl,
                'risk_parameters_compliance': portfolio_risk_pct <= self.adapted_risk_parameters.max_daily_loss
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating portfolio risk metrics: {e}")
            return {'error': str(e)}
    
    def _enforce_risk_parameter_bounds(self, params: RiskParameters) -> RiskParameters:
        """Ensure risk parameters stay within reasonable bounds"""
        
        # Enforce minimum and maximum bounds
        bounded_params = RiskParameters(
            max_position_size=max(0.01, min(0.5, params.max_position_size)),           # 1% to 50%
            stop_loss_pct=max(0.005, min(0.2, params.stop_loss_pct)),                # 0.5% to 20%
            take_profit_pct=max(0.01, min(1.0, params.take_profit_pct)),             # 1% to 100%
            max_drawdown_limit=max(0.05, min(0.5, params.max_drawdown_limit)),       # 5% to 50%
            max_daily_loss=max(0.01, min(0.2, params.max_daily_loss)),               # 1% to 20%
            var_confidence=max(0.90, min(0.99, params.var_confidence)),              # 90% to 99%
            max_leverage=max(1.0, min(5.0, params.max_leverage)),                    # 1x to 5x
            correlation_limit=max(0.3, min(1.0, params.correlation_limit)),          # 30% to 100%
            volatility_limit=max(0.1, min(1.0, params.volatility_limit))             # 10% to 100%
        )
        
        return bounded_params
    
    def _validate_risk_template_compliance(self, params: RiskParameters) -> bool:
        """Validate risk parameters against template constraints"""
        try:
            # Get category rules
            category_rules = self.config.category_risk_rules.get(self.current_template_category, {})
            max_adjustment = category_rules.get('max_risk_adjustment', 0.3)
            
            # Check each parameter against base parameters
            base = self.base_risk_parameters
            
            # Calculate maximum allowed deviations
            checks = [
                ('max_position_size', params.max_position_size, base.max_position_size),
                ('stop_loss_pct', params.stop_loss_pct, base.stop_loss_pct),
                ('max_drawdown_limit', params.max_drawdown_limit, base.max_drawdown_limit),
                ('max_daily_loss', params.max_daily_loss, base.max_daily_loss),
                ('max_leverage', params.max_leverage, base.max_leverage)
            ]
            
            for param_name, new_value, base_value in checks:
                if base_value > 0:
                    deviation = abs((new_value - base_value) / base_value)
                    if deviation > max_adjustment:
                        self.logger.warning(f"Risk parameter {param_name} deviation {deviation:.2%} exceeds limit {max_adjustment:.2%}")
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating risk template compliance: {e}")
            return False
    
    def _estimate_risk_reduction(self, old_params: RiskParameters, new_params: RiskParameters) -> float:
        """Estimate risk reduction from parameter changes"""
        try:
            # Calculate risk reduction for key parameters
            position_reduction = (old_params.max_position_size - new_params.max_position_size) / old_params.max_position_size if old_params.max_position_size > 0 else 0
            stop_tightening = (old_params.stop_loss_pct - new_params.stop_loss_pct) / old_params.stop_loss_pct if old_params.stop_loss_pct > 0 else 0
            leverage_reduction = (old_params.max_leverage - new_params.max_leverage) / old_params.max_leverage if old_params.max_leverage > 0 else 0
            
            # Weighted average of risk reductions
            total_risk_reduction = (position_reduction * 0.4 + 
                                  stop_tightening * 0.4 + 
                                  leverage_reduction * 0.2)
            
            return max(0.0, min(0.5, total_risk_reduction))  # Cap at 50% reduction
            
        except Exception as e:
            self.logger.error(f"Error estimating risk reduction: {e}")
            return 0.0
    
    def _calculate_risk_adaptation_confidence(self, reasons: List[str], adaptation_magnitude: float) -> float:
        """Calculate confidence in risk adaptation decision"""
        
        base_confidence = 0.8  # Higher base confidence for risk management
        
        # Adjust based on adaptation magnitude
        if adaptation_magnitude > 0.3:
            base_confidence -= 0.1  # Large changes are riskier
        elif adaptation_magnitude < 0.05:
            base_confidence -= 0.1  # Very small changes may not help
        
        # Adjust based on reasons
        reason_confidence_adjustments = {
            'drawdown_breach': 0.1,      # High confidence for drawdown response
            'high_volatility': 0.05,     # Medium confidence for volatility response
            'daily_loss_breach': 0.15,   # Highest confidence for loss limit breach
            'consecutive_losses': 0.05   # Low confidence for pattern-based triggers
        }
        
        for reason in reasons:
            base_confidence += reason_confidence_adjustments.get(reason, 0.0)
        
        # Adjust based on historical adaptation success
        if len(self.adaptation_history) > 5:
            recent_success_rate = np.mean([a.success for a in self.adaptation_history[-5:]])
            base_confidence = base_confidence * 0.7 + recent_success_rate * 0.3
        
        return max(0.1, min(1.0, base_confidence))
    
    def _risk_parameters_to_dict(self, params: RiskParameters) -> Dict[str, Any]:
        """Convert risk parameters to dictionary for serialization"""
        return {
            'max_position_size': params.max_position_size,
            'stop_loss_pct': params.stop_loss_pct,
            'take_profit_pct': params.take_profit_pct,
            'max_drawdown_limit': params.max_drawdown_limit,
            'max_daily_loss': params.max_daily_loss,
            'var_confidence': params.var_confidence,
            'max_leverage': params.max_leverage,
            'correlation_limit': params.correlation_limit,
            'volatility_limit': params.volatility_limit
        }
