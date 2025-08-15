"""
Dynamic Adaptation Framework - Core Component
=============================================

Enhanced framework for runtime strategy adaptation integrated with hybrid templates.
Provides template-inheritance-aware adaptation with category-specific rules.

Author: Pro Quant Desk Trader
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

from strategy_templates.base import TemplateRegistry, TemplateInheritanceManager, TemplateCategory


class AdaptationTrigger(Enum):
    """Types of adaptation triggers"""
    PERFORMANCE_DEGRADATION = "performance_degradation"
    VOLATILITY_CHANGE = "volatility_change"
    MARKET_REGIME_CHANGE = "market_regime_change"
    CORRELATION_BREAKDOWN = "correlation_breakdown"
    RISK_THRESHOLD_BREACH = "risk_threshold_breach"
    MANUAL_TRIGGER = "manual_trigger"


class AdaptationMode(Enum):
    """Adaptation execution modes"""
    CONSERVATIVE = "conservative"  # Small incremental changes
    MODERATE = "moderate"         # Balanced adaptation
    AGGRESSIVE = "aggressive"     # Rapid adaptation
    EMERGENCY = "emergency"       # Maximum adaptation speed


@dataclass
class AdaptationResult:
    """Result of an adaptation execution"""
    success: bool
    adaptation_type: AdaptationTrigger
    adaptation_mode: AdaptationMode
    original_parameters: Dict[str, Any]
    adapted_parameters: Dict[str, Any]
    adaptation_magnitude: float
    timestamp: datetime
    template_category: TemplateCategory
    confidence_score: float
    rollback_available: bool = True
    error_message: Optional[str] = None


@dataclass
class AdaptationFrameworkConfig:
    """Configuration for the dynamic adaptation framework"""
    # Trigger thresholds by template category
    performance_degradation_thresholds: Dict[TemplateCategory, float] = field(default_factory=lambda: {
        TemplateCategory.BASE: 0.15,      # 15% degradation threshold
        TemplateCategory.SPECIFIC: 0.12,  # 12% degradation threshold  
        TemplateCategory.COMPOSITE: 0.10  # 10% degradation threshold
    })
    
    volatility_change_thresholds: Dict[TemplateCategory, float] = field(default_factory=lambda: {
        TemplateCategory.BASE: 0.30,      # 30% volatility change
        TemplateCategory.SPECIFIC: 0.25,  # 25% volatility change
        TemplateCategory.COMPOSITE: 0.20  # 20% volatility change
    })
    
    # Adaptation limits by template category
    max_parameter_change: Dict[TemplateCategory, float] = field(default_factory=lambda: {
        TemplateCategory.BASE: 0.25,      # 25% max change for base templates
        TemplateCategory.SPECIFIC: 0.35,  # 35% max change for specific templates
        TemplateCategory.COMPOSITE: 0.45  # 45% max change for composite templates
    })
    
    # Timing configurations
    min_adaptation_interval: timedelta = timedelta(minutes=15)
    adaptation_cooldown: timedelta = timedelta(hours=1)
    max_adaptations_per_day: int = 10
    
    # Safety configurations
    enable_rollback: bool = True
    require_confirmation: bool = False
    max_consecutive_adaptations: int = 3
    confidence_threshold: float = 0.7


class DynamicAdaptationFramework:
    """
    Enhanced framework for runtime strategy adaptation with hybrid template support
    """
    
    def __init__(self, 
                 template_registry: TemplateRegistry,
                 config: Optional[AdaptationFrameworkConfig] = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.template_registry = template_registry
        self.config = config or AdaptationFrameworkConfig()
        
        # Initialize components
        self.inheritance_manager = TemplateInheritanceManager(template_registry)
        
        # Adaptation state tracking
        self.adaptation_history: List[AdaptationResult] = []
        self.last_adaptation_time: Optional[datetime] = None
        self.consecutive_adaptations = 0
        self.current_template_id: Optional[str] = None
        self.original_parameters: Dict[str, Any] = {}
        
        # Performance tracking
        self.performance_baseline: Dict[str, float] = {}
        self.volatility_baseline: float = 0.0
        self.current_market_regime: Optional[str] = None
        
        self.logger.info("Dynamic Adaptation Framework initialized")
    
    async def initialize_for_template(self, template_id: str, initial_parameters: Dict[str, Any]):
        """Initialize the adaptation framework for a specific template"""
        try:
            self.current_template_id = template_id
            self.original_parameters = initial_parameters.copy()
            
            # Get template for category information
            template = self.template_registry.get_template(template_id)
            if not template:
                raise ValueError(f"Template {template_id} not found")
            
            # Reset adaptation state
            self.adaptation_history.clear()
            self.consecutive_adaptations = 0
            self.last_adaptation_time = None
            
            self.logger.info(f"Adaptation framework initialized for template {template_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize adaptation framework: {e}")
            raise
    
    async def check_adaptation_triggers(self, 
                                      market_data: Dict[str, Any], 
                                      performance_metrics: Dict[str, float]) -> Tuple[bool, List[AdaptationTrigger]]:
        """
        Check if adaptation is needed based on current conditions
        """
        try:
            if not self.current_template_id:
                return False, []
            
            # Check if we're in cooldown period
            if self._is_in_cooldown():
                return False, []
            
            triggered_adaptations = []
            
            # Get template category for threshold selection
            template = self.template_registry.get_template(self.current_template_id)
            template_category = template.metadata.category
            
            # Check performance degradation
            if await self._check_performance_degradation(performance_metrics, template_category):
                triggered_adaptations.append(AdaptationTrigger.PERFORMANCE_DEGRADATION)
            
            # Check volatility changes
            if await self._check_volatility_change(market_data, template_category):
                triggered_adaptations.append(AdaptationTrigger.VOLATILITY_CHANGE)
            
            # Check market regime changes
            if await self._check_market_regime_change(market_data, template_category):
                triggered_adaptations.append(AdaptationTrigger.MARKET_REGIME_CHANGE)
            
            # Check risk threshold breaches
            if await self._check_risk_threshold_breach(performance_metrics, template_category):
                triggered_adaptations.append(AdaptationTrigger.RISK_THRESHOLD_BREACH)
            
            adaptation_needed = len(triggered_adaptations) > 0
            
            if adaptation_needed:
                self.logger.info(f"Adaptation triggers detected: {[t.value for t in triggered_adaptations]}")
            
            return adaptation_needed, triggered_adaptations
            
        except Exception as e:
            self.logger.error(f"Error checking adaptation triggers: {e}")
            return False, []
    
    async def execute_adaptation(self, 
                               market_data: Dict[str, Any],
                               performance_metrics: Dict[str, float],
                               triggers: List[AdaptationTrigger],
                               adaptation_mode: AdaptationMode = AdaptationMode.MODERATE) -> AdaptationResult:
        """
        Execute parameter adaptation based on triggers and current conditions
        """
        try:
            if not self.current_template_id:
                raise ValueError("No template initialized for adaptation")
            
            # Get template and category
            template = self.template_registry.get_template(self.current_template_id)
            template_category = template.metadata.category
            
            # Determine adaptation parameters
            adaptation_magnitude = self._calculate_adaptation_magnitude(triggers, adaptation_mode, template_category)
            
            # Get template inheritance chain for bounds
            inheritance_chain = self.inheritance_manager.get_inheritance_chain(self.current_template_id)
            
            # Calculate optimal parameters
            adapted_parameters = await self._calculate_adapted_parameters(
                market_data, performance_metrics, triggers, adaptation_magnitude, inheritance_chain
            )
            
            # Validate adaptation within template bounds
            validated_parameters = self._validate_adaptation_bounds(adapted_parameters, template_category)
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(
                triggers, adaptation_magnitude, template_category
            )
            
            # Create adaptation result
            result = AdaptationResult(
                success=True,
                adaptation_type=triggers[0] if triggers else AdaptationTrigger.MANUAL_TRIGGER,
                adaptation_mode=adaptation_mode,
                original_parameters=self.original_parameters.copy(),
                adapted_parameters=validated_parameters,
                adaptation_magnitude=adaptation_magnitude,
                timestamp=datetime.now(),
                template_category=template_category,
                confidence_score=confidence_score,
                rollback_available=self.config.enable_rollback
            )
            
            # Record adaptation
            self._record_adaptation(result)
            
            self.logger.info(f"Adaptation executed successfully with confidence {confidence_score:.3f}")
            return result
            
        except Exception as e:
            error_msg = f"Adaptation execution failed: {e}"
            self.logger.error(error_msg)
            
            # Return failed result
            return AdaptationResult(
                success=False,
                adaptation_type=triggers[0] if triggers else AdaptationTrigger.MANUAL_TRIGGER,
                adaptation_mode=adaptation_mode,
                original_parameters=self.original_parameters.copy(),
                adapted_parameters={},
                adaptation_magnitude=0.0,
                timestamp=datetime.now(),
                template_category=TemplateCategory.BASE,
                confidence_score=0.0,
                rollback_available=False,
                error_message=error_msg
            )
    
    async def rollback_adaptation(self, steps: int = 1) -> bool:
        """
        Rollback previous adaptations
        """
        try:
            if not self.config.enable_rollback:
                self.logger.warning("Rollback is disabled")
                return False
            
            if len(self.adaptation_history) < steps:
                self.logger.warning(f"Cannot rollback {steps} steps, only {len(self.adaptation_history)} adaptations available")
                return False
            
            # Remove the last 'steps' adaptations
            for _ in range(steps):
                if self.adaptation_history:
                    removed_adaptation = self.adaptation_history.pop()
                    self.logger.info(f"Rolled back adaptation from {removed_adaptation.timestamp}")
            
            # Reset consecutive adaptations counter
            self.consecutive_adaptations = max(0, self.consecutive_adaptations - steps)
            
            self.logger.info(f"Successfully rolled back {steps} adaptation(s)")
            return True
            
        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
            return False
    
    def get_adaptation_summary(self) -> Dict[str, Any]:
        """Get summary of recent adaptations"""
        if not self.adaptation_history:
            return {
                'total_adaptations': 0,
                'recent_adaptations': [],
                'adaptation_frequency': 0.0,
                'average_confidence': 0.0,
                'success_rate': 0.0
            }
        
        recent_adaptations = self.adaptation_history[-10:]  # Last 10 adaptations
        successful_adaptations = [a for a in self.adaptation_history if a.success]
        
        return {
            'total_adaptations': len(self.adaptation_history),
            'recent_adaptations': [
                {
                    'timestamp': a.timestamp.isoformat(),
                    'type': a.adaptation_type.value,
                    'mode': a.adaptation_mode.value,
                    'magnitude': a.adaptation_magnitude,
                    'confidence': a.confidence_score,
                    'success': a.success
                }
                for a in recent_adaptations
            ],
            'adaptation_frequency': len(self.adaptation_history) / max(1, (datetime.now() - self.adaptation_history[0].timestamp).days),
            'average_confidence': np.mean([a.confidence_score for a in self.adaptation_history]),
            'success_rate': len(successful_adaptations) / len(self.adaptation_history),
            'consecutive_adaptations': self.consecutive_adaptations,
            'last_adaptation': self.last_adaptation_time.isoformat() if self.last_adaptation_time else None
        }
    
    # Private helper methods
    def _is_in_cooldown(self) -> bool:
        """Check if adaptation is in cooldown period"""
        if not self.last_adaptation_time:
            return False
        
        time_since_last = datetime.now() - self.last_adaptation_time
        return time_since_last < self.config.adaptation_cooldown
    
    async def _check_performance_degradation(self, 
                                           performance_metrics: Dict[str, float], 
                                           template_category: TemplateCategory) -> bool:
        """Check for performance degradation"""
        if not self.performance_baseline:
            # Initialize baseline
            self.performance_baseline = performance_metrics.copy()
            return False
        
        threshold = self.config.performance_degradation_thresholds[template_category]
        
        # Check key performance metrics
        for metric, current_value in performance_metrics.items():
            if metric in self.performance_baseline:
                baseline_value = self.performance_baseline[metric]
                if baseline_value > 0:  # Avoid division by zero
                    degradation = (baseline_value - current_value) / baseline_value
                    if degradation > threshold:
                        self.logger.info(f"Performance degradation detected in {metric}: {degradation:.3f} > {threshold}")
                        return True
        
        return False
    
    async def _check_volatility_change(self, 
                                     market_data: Dict[str, Any], 
                                     template_category: TemplateCategory) -> bool:
        """Check for significant volatility changes"""
        # Calculate current volatility (simplified)
        prices = market_data.get('prices', [])
        if len(prices) < 20:  # Need sufficient data
            return False
        
        current_volatility = np.std(prices[-20:])  # 20-period volatility
        
        if self.volatility_baseline == 0:
            self.volatility_baseline = current_volatility
            return False
        
        threshold = self.config.volatility_change_thresholds[template_category]
        volatility_change = abs(current_volatility - self.volatility_baseline) / self.volatility_baseline
        
        if volatility_change > threshold:
            self.logger.info(f"Volatility change detected: {volatility_change:.3f} > {threshold}")
            self.volatility_baseline = current_volatility  # Update baseline
            return True
        
        return False
    
    async def _check_market_regime_change(self, 
                                        market_data: Dict[str, Any], 
                                        template_category: TemplateCategory) -> bool:
        """Check for market regime changes"""
        # Simplified regime detection based on price trends
        prices = market_data.get('prices', [])
        if len(prices) < 50:  # Need sufficient data
            return False
        
        # Calculate trend indicators
        short_ma = np.mean(prices[-10:])
        long_ma = np.mean(prices[-50:])
        
        # Determine current regime
        if short_ma > long_ma * 1.02:
            current_regime = "bullish"
        elif short_ma < long_ma * 0.98:
            current_regime = "bearish"
        else:
            current_regime = "sideways"
        
        if self.current_market_regime is None:
            self.current_market_regime = current_regime
            return False
        
        if current_regime != self.current_market_regime:
            self.logger.info(f"Market regime change: {self.current_market_regime} -> {current_regime}")
            self.current_market_regime = current_regime
            return True
        
        return False
    
    async def _check_risk_threshold_breach(self, 
                                         performance_metrics: Dict[str, float], 
                                         template_category: TemplateCategory) -> bool:
        """Check for risk threshold breaches"""
        # Check drawdown
        max_drawdown = performance_metrics.get('max_drawdown', 0)
        if template_category == TemplateCategory.BASE and max_drawdown > 0.15:
            return True
        elif template_category == TemplateCategory.SPECIFIC and max_drawdown > 0.20:
            return True
        elif template_category == TemplateCategory.COMPOSITE and max_drawdown > 0.25:
            return True
        
        # Check volatility
        volatility = performance_metrics.get('volatility', 0)
        if volatility > 0.30:  # 30% volatility threshold
            return True
        
        return False
    
    def _calculate_adaptation_magnitude(self, 
                                      triggers: List[AdaptationTrigger],
                                      adaptation_mode: AdaptationMode,
                                      template_category: TemplateCategory) -> float:
        """Calculate the magnitude of adaptation needed"""
        # Base magnitude from adaptation mode
        mode_magnitudes = {
            AdaptationMode.CONSERVATIVE: 0.1,
            AdaptationMode.MODERATE: 0.2,
            AdaptationMode.AGGRESSIVE: 0.4,
            AdaptationMode.EMERGENCY: 0.6
        }
        
        base_magnitude = mode_magnitudes[adaptation_mode]
        
        # Adjust based on number and severity of triggers
        trigger_multiplier = min(len(triggers) * 0.2, 1.0)
        
        # Apply template category limits
        max_change = self.config.max_parameter_change[template_category]
        
        magnitude = min(base_magnitude * (1 + trigger_multiplier), max_change)
        
        return magnitude
    
    async def _calculate_adapted_parameters(self, 
                                          market_data: Dict[str, Any],
                                          performance_metrics: Dict[str, float],
                                          triggers: List[AdaptationTrigger],
                                          magnitude: float,
                                          inheritance_chain: List[str]) -> Dict[str, Any]:
        """Calculate adapted parameters based on conditions"""
        adapted_params = self.original_parameters.copy()
        
        # Apply adaptations based on triggers
        for trigger in triggers:
            if trigger == AdaptationTrigger.PERFORMANCE_DEGRADATION:
                adapted_params = self._adapt_for_performance_degradation(adapted_params, magnitude)
            elif trigger == AdaptationTrigger.VOLATILITY_CHANGE:
                adapted_params = self._adapt_for_volatility_change(adapted_params, magnitude, market_data)
            elif trigger == AdaptationTrigger.MARKET_REGIME_CHANGE:
                adapted_params = self._adapt_for_regime_change(adapted_params, magnitude)
            elif trigger == AdaptationTrigger.RISK_THRESHOLD_BREACH:
                adapted_params = self._adapt_for_risk_breach(adapted_params, magnitude)
        
        return adapted_params
    
    def _adapt_for_performance_degradation(self, params: Dict[str, Any], magnitude: float) -> Dict[str, Any]:
        """Adapt parameters for performance degradation"""
        # Increase signal sensitivity
        if 'signal_threshold' in params:
            params['signal_threshold'] = max(0.1, params['signal_threshold'] * (1 - magnitude))
        
        # Reduce position sizes for safety
        if 'max_position_size' in params:
            params['max_position_size'] = max(0.01, params['max_position_size'] * (1 - magnitude * 0.5))
        
        return params
    
    def _adapt_for_volatility_change(self, params: Dict[str, Any], magnitude: float, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Adapt parameters for volatility changes"""
        # Adjust stop losses based on volatility
        if 'stop_loss_pct' in params:
            current_vol = np.std(market_data.get('prices', [])[-20:]) if len(market_data.get('prices', [])) >= 20 else 0.02
            vol_adjustment = min(current_vol * 2, 0.1)  # Cap at 10%
            params['stop_loss_pct'] = params['stop_loss_pct'] + vol_adjustment * magnitude
        
        return params
    
    def _adapt_for_regime_change(self, params: Dict[str, Any], magnitude: float) -> Dict[str, Any]:
        """Adapt parameters for market regime changes"""
        # Adjust signal thresholds based on regime
        if self.current_market_regime == "bearish":
            # More conservative in bearish markets
            if 'signal_threshold' in params:
                params['signal_threshold'] = min(1.0, params['signal_threshold'] * (1 + magnitude))
        elif self.current_market_regime == "bullish":
            # More aggressive in bullish markets
            if 'signal_threshold' in params:
                params['signal_threshold'] = max(0.1, params['signal_threshold'] * (1 - magnitude * 0.5))
        
        return params
    
    def _adapt_for_risk_breach(self, params: Dict[str, Any], magnitude: float) -> Dict[str, Any]:
        """Adapt parameters for risk threshold breaches"""
        # Reduce all risk parameters
        risk_reduction = magnitude
        
        if 'max_position_size' in params:
            params['max_position_size'] = max(0.01, params['max_position_size'] * (1 - risk_reduction))
        
        if 'risk_per_trade' in params:
            params['risk_per_trade'] = max(0.005, params['risk_per_trade'] * (1 - risk_reduction))
        
        return params
    
    def _validate_adaptation_bounds(self, adapted_params: Dict[str, Any], template_category: TemplateCategory) -> Dict[str, Any]:
        """Validate that adapted parameters are within acceptable bounds"""
        validated_params = adapted_params.copy()
        
        # Apply category-specific bounds
        bounds = {
            'signal_threshold': (0.1, 1.0),
            'max_position_size': (0.01, 0.5),
            'risk_per_trade': (0.005, 0.05),
            'stop_loss_pct': (0.01, 0.30),
            'take_profit_pct': (0.05, 1.0)
        }
        
        for param, (min_val, max_val) in bounds.items():
            if param in validated_params:
                validated_params[param] = max(min_val, min(max_val, validated_params[param]))
        
        return validated_params
    
    def _calculate_confidence_score(self, 
                                  triggers: List[AdaptationTrigger],
                                  magnitude: float,
                                  template_category: TemplateCategory) -> float:
        """Calculate confidence score for the adaptation"""
        # Base confidence from trigger strength
        base_confidence = min(len(triggers) * 0.3, 0.9)
        
        # Adjust based on magnitude (moderate changes have higher confidence)
        if 0.1 <= magnitude <= 0.3:
            magnitude_confidence = 1.0
        elif magnitude < 0.1:
            magnitude_confidence = 0.7
        else:
            magnitude_confidence = 0.6
        
        # Template category confidence
        category_confidence = {
            TemplateCategory.BASE: 0.8,      # More conservative
            TemplateCategory.SPECIFIC: 0.9,  # Well-tested parameters
            TemplateCategory.COMPOSITE: 0.7  # More complex, less predictable
        }[template_category]
        
        # Historical success rate
        historical_confidence = 0.8  # Would be calculated from adaptation history
        
        # Combine factors
        confidence = (base_confidence * 0.3 + 
                     magnitude_confidence * 0.3 + 
                     category_confidence * 0.2 + 
                     historical_confidence * 0.2)
        
        return min(confidence, 1.0)
    
    def _record_adaptation(self, result: AdaptationResult):
        """Record adaptation in history"""
        self.adaptation_history.append(result)
        self.last_adaptation_time = result.timestamp
        
        if result.success:
            self.consecutive_adaptations += 1
        else:
            self.consecutive_adaptations = 0
        
        # Limit history size
        if len(self.adaptation_history) > 100:
            self.adaptation_history = self.adaptation_history[-50:]  # Keep last 50
