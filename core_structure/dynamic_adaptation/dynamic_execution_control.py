"""
Dynamic Execution Control - Template-Aware Adaptive Execution Control
=====================================================================

Template-inheritance-aware adaptive execution control that dynamically adjusts
order types, timing, and execution strategies based on market conditions.

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


class ExecutionAdaptationMode(Enum):
    """Execution adaptation modes"""
    CONSERVATIVE = "conservative"        # Focus on minimizing market impact
    BALANCED = "balanced"               # Balance speed and impact
    AGGRESSIVE = "aggressive"           # Focus on speed of execution
    LIQUIDITY_BASED = "liquidity_based" # Adapt based on liquidity
    VOLATILITY_BASED = "volatility_based" # Adapt based on volatility


class OrderType(Enum):
    """Order types for execution"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TWAP = "twap"
    VWAP = "vwap"
    ICEBERG = "iceberg"
    HIDDEN = "hidden"


class ExecutionAlgorithm(Enum):
    """Execution algorithms"""
    SIMPLE = "simple"
    TWAP = "twap"          # Time-Weighted Average Price
    VWAP = "vwap"          # Volume-Weighted Average Price
    POV = "pov"            # Participation of Volume
    IS = "implementation_shortfall"  # Implementation Shortfall
    ADAPTIVE = "adaptive"   # Adaptive algorithm


@dataclass
class ExecutionParameters:
    """Execution control parameters"""
    default_order_type: OrderType = OrderType.LIMIT
    execution_algorithm: ExecutionAlgorithm = ExecutionAlgorithm.TWAP
    max_order_size_pct: float = 0.1        # 10% of daily volume
    participation_rate: float = 0.2        # 20% participation rate
    urgency_factor: float = 0.5            # Execution urgency (0-1)
    price_improvement_threshold: float = 0.001  # 0.1% price improvement
    timeout_minutes: int = 30              # Order timeout
    slice_duration_minutes: int = 5        # Time slice duration
    min_fill_size: float = 100.0          # Minimum fill size
    max_market_impact_bps: int = 10        # 10 bps max market impact


@dataclass
class ExecutionMetrics:
    """Execution performance metrics"""
    total_orders: int = 0
    filled_orders: int = 0
    fill_rate: float = 0.0
    avg_fill_time_seconds: float = 0.0
    avg_slippage_bps: float = 0.0
    avg_market_impact_bps: float = 0.0
    implementation_shortfall: float = 0.0
    participation_rate_achieved: float = 0.0
    price_improvement_rate: float = 0.0


@dataclass
class ExecutionConfig:
    """Configuration for dynamic execution control"""
    # Adaptation settings
    adaptation_mode: ExecutionAdaptationMode = ExecutionAdaptationMode.BALANCED
    adaptation_frequency: timedelta = timedelta(minutes=15)
    min_confidence_threshold: float = 0.7
    
    # Template category execution rules
    category_execution_rules: Dict[TemplateCategory, Dict[str, Any]] = field(default_factory=lambda: {
        TemplateCategory.BASE: {
            'max_execution_adjustment': 0.1,    # 10% max adjustment
            'execution_conservatism': 0.8,      # High conservatism
            'algorithm_flexibility': 0.4        # Low flexibility
        },
        TemplateCategory.SPECIFIC: {
            'max_execution_adjustment': 0.2,    # 20% max adjustment
            'execution_conservatism': 0.6,      # Medium conservatism
            'algorithm_flexibility': 0.7        # Medium flexibility
        },
        TemplateCategory.COMPOSITE: {
            'max_execution_adjustment': 0.3,    # 30% max adjustment
            'execution_conservatism': 0.4,      # Low conservatism
            'algorithm_flexibility': 1.0        # High flexibility
        }
    })
    
    # Execution adaptation triggers
    adaptation_triggers: Dict[str, float] = field(default_factory=lambda: {
        'high_slippage_threshold_bps': 15,
        'low_fill_rate_threshold': 0.7,
        'high_market_impact_threshold_bps': 20,
        'volatility_spike_threshold': 0.03,
        'liquidity_dry_up_threshold': 0.5
    })


@dataclass
class ExecutionAdaptationResult:
    """Result of execution control adaptation"""
    success: bool
    adapted_parameters: ExecutionParameters
    algorithm_changes: List[str]
    adaptation_magnitude: float
    performance_improvement_estimate: float
    confidence_score: float
    adaptation_reasons: List[str]
    template_compliance: bool
    execution_time_ms: float
    error_message: Optional[str] = None


class DynamicExecutionControl:
    """
    Template-inheritance-aware adaptive execution control
    """
    
    def __init__(self, 
                 template_registry: TemplateRegistry,
                 config: Optional[ExecutionConfig] = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.template_registry = template_registry
        self.config = config or ExecutionConfig()
        
        # Initialize components
        self.inheritance_manager = TemplateInheritanceManager(template_registry)
        
        # Execution control state
        self.current_template_id: Optional[str] = None
        self.current_template_category: Optional[TemplateCategory] = None
        self.base_execution_parameters = ExecutionParameters()
        self.adapted_execution_parameters = ExecutionParameters()
        
        # Execution tracking
        self.execution_history: deque = deque(maxlen=200)
        self.slippage_history: deque = deque(maxlen=100)
        self.fill_rate_history: deque = deque(maxlen=50)
        self.market_impact_history: deque = deque(maxlen=100)
        
        # Adaptation tracking
        self.adaptation_history: List[ExecutionAdaptationResult] = []
        self.last_adaptation_time: Optional[datetime] = None
        
        # Market condition tracking
        self.current_volatility: float = 0.0
        self.current_liquidity_score: float = 1.0
        self.recent_volume: deque = deque(maxlen=20)
        
        self.logger.info("Dynamic Execution Control initialized")
    
    def initialize_for_template(self, template_id: str):
        """Initialize execution control for a specific template"""
        try:
            template = self.template_registry.get_template(template_id)
            if not template:
                raise ValueError(f"Template {template_id} not found")
            
            self.current_template_id = template_id
            self.current_template_category = template.metadata.category
            
            # Extract execution parameters from template
            self.base_execution_parameters = self._extract_template_execution_parameters(template_id)
            self.adapted_execution_parameters = ExecutionParameters(
                default_order_type=self.base_execution_parameters.default_order_type,
                execution_algorithm=self.base_execution_parameters.execution_algorithm,
                max_order_size_pct=self.base_execution_parameters.max_order_size_pct,
                participation_rate=self.base_execution_parameters.participation_rate,
                urgency_factor=self.base_execution_parameters.urgency_factor,
                price_improvement_threshold=self.base_execution_parameters.price_improvement_threshold,
                timeout_minutes=self.base_execution_parameters.timeout_minutes,
                slice_duration_minutes=self.base_execution_parameters.slice_duration_minutes,
                min_fill_size=self.base_execution_parameters.min_fill_size,
                max_market_impact_bps=self.base_execution_parameters.max_market_impact_bps
            )
            
            # Reset state
            self.execution_history.clear()
            self.slippage_history.clear()
            self.fill_rate_history.clear()
            self.market_impact_history.clear()
            self.adaptation_history.clear()
            self.last_adaptation_time = None
            self.recent_volume.clear()
            
            self.logger.info(f"Execution control initialized for template {template_id} (category: {self.current_template_category.value})")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize execution control: {e}")
            raise
    
    async def execute_adaptive_orders(self, 
                                    orders: List[Dict[str, Any]], 
                                    market_data: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Execute orders with adaptive execution control
        """
        try:
            if not self.current_template_id:
                raise ValueError("Execution control not initialized for template")
            
            start_time = datetime.now()
            
            # Update market conditions
            self._update_market_conditions(market_data)
            
            # Check if execution adaptation is needed
            adaptation_needed, adaptation_reasons = self._check_execution_adaptation_triggers()
            
            # Perform execution adaptation if needed
            adaptation_result = None
            if adaptation_needed:
                adaptation_result = await self._perform_execution_adaptation(market_data, adaptation_reasons)
                if adaptation_result.success:
                    self.adaptation_history.append(adaptation_result)
                    self.last_adaptation_time = datetime.now()
                    self.logger.info(f"Execution adaptation performed: {adaptation_result.performance_improvement_estimate:.2%} improvement")
            
            # Execute orders with current parameters
            execution_results = []
            for order in orders:
                result = await self._execute_single_order(order, market_data)
                execution_results.append(result)
                
                # Track execution for adaptation
                self._track_execution_result(result)
            
            # Calculate execution metrics
            execution_metrics = self._calculate_execution_metrics()
            
            # Prepare execution summary
            execution_summary = {
                'execution_results': execution_results,
                'execution_metrics': self._execution_metrics_to_dict(execution_metrics),
                'execution_parameters': self._execution_parameters_to_dict(self.adapted_execution_parameters),
                'adaptation_status': {
                    'adaptation_performed': adaptation_needed,
                    'adaptation_reasons': adaptation_reasons,
                    'last_adaptation': self.last_adaptation_time.isoformat() if self.last_adaptation_time else None,
                    'adaptations_count': len(self.adaptation_history)
                },
                'market_conditions': {
                    'volatility': self.current_volatility,
                    'liquidity_score': self.current_liquidity_score,
                    'recent_avg_volume': np.mean(list(self.recent_volume)) if self.recent_volume else 0.0
                },
                'template_info': {
                    'template_id': self.current_template_id,
                    'template_category': self.current_template_category.value if self.current_template_category else None
                },
                'execution_time_ms': (datetime.now() - start_time).total_seconds() * 1000
            }
            
            return execution_results, execution_summary
            
        except Exception as e:
            error_msg = f"Execution control failed: {e}"
            self.logger.error(error_msg)
            
            return [], {
                'error': error_msg,
                'orders_attempted': len(orders) if orders else 0,
                'orders_executed': 0
            }
    
    def update_execution_feedback(self, execution_data: Dict[str, Any]):
        """Update execution feedback for adaptation"""
        try:
            # Track execution metrics
            if 'slippage_bps' in execution_data:
                self.slippage_history.append(execution_data['slippage_bps'])
            
            if 'fill_rate' in execution_data:
                self.fill_rate_history.append(execution_data['fill_rate'])
            
            if 'market_impact_bps' in execution_data:
                self.market_impact_history.append(execution_data['market_impact_bps'])
            
            # Add to execution history
            self.execution_history.append({
                'timestamp': datetime.now(),
                'data': execution_data.copy()
            })
            
            self.logger.debug(f"Execution feedback updated: {len(self.execution_history)} records")
            
        except Exception as e:
            self.logger.error(f"Failed to update execution feedback: {e}")
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get comprehensive execution control summary"""
        current_metrics = self._calculate_execution_metrics()
        
        return {
            'current_metrics': self._execution_metrics_to_dict(current_metrics),
            'current_parameters': self._execution_parameters_to_dict(self.adapted_execution_parameters),
            'base_parameters': self._execution_parameters_to_dict(self.base_execution_parameters),
            'adaptation_summary': {
                'total_adaptations': len(self.adaptation_history),
                'successful_adaptations': len([a for a in self.adaptation_history if a.success]),
                'average_improvement': np.mean([a.performance_improvement_estimate for a in self.adaptation_history if a.success]) if self.adaptation_history else 0.0,
                'last_adaptation': self.last_adaptation_time.isoformat() if self.last_adaptation_time else None
            },
            'performance_trends': {
                'slippage_trend': self._calculate_trend(list(self.slippage_history)) if len(self.slippage_history) > 5 else 0.0,
                'fill_rate_trend': self._calculate_trend(list(self.fill_rate_history)) if len(self.fill_rate_history) > 5 else 0.0,
                'market_impact_trend': self._calculate_trend(list(self.market_impact_history)) if len(self.market_impact_history) > 5 else 0.0
            },
            'template_info': {
                'template_id': self.current_template_id,
                'template_category': self.current_template_category.value if self.current_template_category else None
            }
        }
    
    # Private helper methods (Part 1)
    def _extract_template_execution_parameters(self, template_id: str) -> ExecutionParameters:
        """Extract execution parameters from template and inheritance chain"""
        try:
            # Get resolved template with inheritance
            resolved_template = self.inheritance_manager.resolve_inheritance(template_id)
            if not resolved_template:
                template = self.template_registry.get_template(template_id)
                resolved_template = template if template else None
            
            if not resolved_template:
                return ExecutionParameters()  # Default parameters
            
            # Extract execution parameters
            exec_params = ExecutionParameters()
            
            # Check template parameters for execution settings
            if hasattr(resolved_template, 'parameters') and resolved_template.parameters:
                params = resolved_template.parameters
                
                # Map template parameters to execution parameters
                param_mappings = {
                    'max_order_size_pct': 'max_order_size_pct',
                    'participation_rate': 'participation_rate',
                    'urgency_factor': 'urgency_factor',
                    'timeout_minutes': 'timeout_minutes'
                }
                
                for template_param, exec_param in param_mappings.items():
                    if template_param in params:
                        value = params[template_param]
                        if hasattr(exec_params, exec_param):
                            setattr(exec_params, exec_param, float(value))
            
            # Check template components for execution engine settings
            if hasattr(resolved_template, 'components') and resolved_template.components:
                exec_config = resolved_template.components.get('execution_engine', {})
                
                for param_name, param_value in exec_config.items():
                    if hasattr(exec_params, param_name):
                        if param_name in ['default_order_type', 'execution_algorithm']:
                            # Handle enum conversions
                            try:
                                if param_name == 'default_order_type':
                                    setattr(exec_params, param_name, OrderType(param_value))
                                elif param_name == 'execution_algorithm':
                                    setattr(exec_params, param_name, ExecutionAlgorithm(param_value))
                            except ValueError:
                                pass  # Keep default
                        else:
                            setattr(exec_params, param_name, param_value)
            
            # Apply template category adjustments
            category_adjustments = self._get_category_execution_adjustments()
            exec_params = self._apply_category_execution_adjustments(exec_params, category_adjustments)
            
            return exec_params
            
        except Exception as e:
            self.logger.error(f"Error extracting template execution parameters: {e}")
            return ExecutionParameters()  # Return default parameters
    
    def _get_category_execution_adjustments(self) -> Dict[str, float]:
        """Get execution parameter adjustments based on template category"""
        if self.current_template_category == TemplateCategory.BASE:
            return {
                'participation_rate_multiplier': 0.8,      # More conservative participation
                'urgency_multiplier': 0.7,                 # Lower urgency
                'max_order_size_multiplier': 0.8,          # Smaller orders
                'timeout_multiplier': 1.3                  # Longer timeouts
            }
        elif self.current_template_category == TemplateCategory.SPECIFIC:
            return {
                'participation_rate_multiplier': 1.0,      # Standard participation
                'urgency_multiplier': 1.0,                 # Standard urgency
                'max_order_size_multiplier': 1.0,          # Standard order size
                'timeout_multiplier': 1.0                  # Standard timeout
            }
        elif self.current_template_category == TemplateCategory.COMPOSITE:
            return {
                'participation_rate_multiplier': 1.2,      # More aggressive participation
                'urgency_multiplier': 1.3,                 # Higher urgency
                'max_order_size_multiplier': 1.2,          # Larger orders
                'timeout_multiplier': 0.8                  # Shorter timeouts
            }
        else:
            return {
                'participation_rate_multiplier': 1.0,
                'urgency_multiplier': 1.0,
                'max_order_size_multiplier': 1.0,
                'timeout_multiplier': 1.0
            }
    
    def _apply_category_execution_adjustments(self, params: ExecutionParameters, adjustments: Dict[str, float]) -> ExecutionParameters:
        """Apply category-specific adjustments to execution parameters"""
        adjusted_params = ExecutionParameters(
            default_order_type=params.default_order_type,
            execution_algorithm=params.execution_algorithm,
            max_order_size_pct=params.max_order_size_pct * adjustments.get('max_order_size_multiplier', 1.0),
            participation_rate=params.participation_rate * adjustments.get('participation_rate_multiplier', 1.0),
            urgency_factor=params.urgency_factor * adjustments.get('urgency_multiplier', 1.0),
            price_improvement_threshold=params.price_improvement_threshold,  # Keep unchanged
            timeout_minutes=int(params.timeout_minutes * adjustments.get('timeout_multiplier', 1.0)),
            slice_duration_minutes=params.slice_duration_minutes,  # Keep unchanged
            min_fill_size=params.min_fill_size,  # Keep unchanged
            max_market_impact_bps=params.max_market_impact_bps  # Keep unchanged
        )
        
        # Ensure values stay within reasonable bounds
        adjusted_params.max_order_size_pct = max(0.01, min(0.5, adjusted_params.max_order_size_pct))     # 1% to 50%
        adjusted_params.participation_rate = max(0.05, min(0.8, adjusted_params.participation_rate))     # 5% to 80%
        adjusted_params.urgency_factor = max(0.1, min(1.0, adjusted_params.urgency_factor))             # 10% to 100%
        adjusted_params.timeout_minutes = max(5, min(180, adjusted_params.timeout_minutes))              # 5 to 180 minutes
        
        return adjusted_params
    
    def _update_market_conditions(self, market_data: Dict[str, Any]):
        """Update market conditions for execution adaptation"""
        try:
            # Update volatility
            if 'volatility' in market_data:
                self.current_volatility = market_data['volatility']
            elif 'prices' in market_data and len(market_data['prices']) > 10:
                # Calculate volatility from price data
                prices = np.array(market_data['prices'])
                returns = np.diff(np.log(prices))
                self.current_volatility = np.std(returns) * np.sqrt(252)  # Annualized
            
            # Update liquidity score
            if 'liquidity_score' in market_data:
                self.current_liquidity_score = market_data['liquidity_score']
            elif 'bid_ask_spread' in market_data and 'volume' in market_data:
                # Estimate liquidity from spread and volume
                spread = market_data['bid_ask_spread']
                volume = market_data['volume']
                # Simple liquidity score (lower spread + higher volume = higher liquidity)
                self.current_liquidity_score = min(1.0, (1.0 / (1.0 + spread * 1000)) * (volume / 10000) ** 0.5)
            
            # Update volume history
            if 'volume' in market_data:
                self.recent_volume.append(market_data['volume'])
            
        except Exception as e:
            self.logger.error(f"Error updating market conditions: {e}")
    
    def _check_execution_adaptation_triggers(self) -> Tuple[bool, List[str]]:
        """Check if execution adaptation is needed"""
        reasons = []
        
        try:
            # Check adaptation frequency
            if self.last_adaptation_time:
                time_since_last = datetime.now() - self.last_adaptation_time
                if time_since_last < self.config.adaptation_frequency:
                    return False, []
            
            # Check high slippage
            if len(self.slippage_history) >= 5:
                avg_slippage = np.mean(list(self.slippage_history)[-5:])
                if avg_slippage > self.config.adaptation_triggers['high_slippage_threshold_bps']:
                    reasons.append("high_slippage")
            
            # Check low fill rate
            if len(self.fill_rate_history) >= 3:
                avg_fill_rate = np.mean(list(self.fill_rate_history)[-3:])
                if avg_fill_rate < self.config.adaptation_triggers['low_fill_rate_threshold']:
                    reasons.append("low_fill_rate")
            
            # Check high market impact
            if len(self.market_impact_history) >= 5:
                avg_impact = np.mean(list(self.market_impact_history)[-5:])
                if avg_impact > self.config.adaptation_triggers['high_market_impact_threshold_bps']:
                    reasons.append("high_market_impact")
            
            # Check volatility spike
            if self.current_volatility > self.config.adaptation_triggers['volatility_spike_threshold']:
                reasons.append("volatility_spike")
            
            # Check liquidity dry up
            if self.current_liquidity_score < self.config.adaptation_triggers['liquidity_dry_up_threshold']:
                reasons.append("liquidity_dry_up")
            
            return len(reasons) > 0, reasons
            
        except Exception as e:
            self.logger.error(f"Error checking execution adaptation triggers: {e}")
            return False, []
    
    async def _perform_execution_adaptation(self, market_data: Dict[str, Any], reasons: List[str]) -> ExecutionAdaptationResult:
        """Perform execution parameter adaptation"""
        try:
            start_time = datetime.now()
            
            # Create new adapted parameters
            new_params = ExecutionParameters(
                default_order_type=self.adapted_execution_parameters.default_order_type,
                execution_algorithm=self.adapted_execution_parameters.execution_algorithm,
                max_order_size_pct=self.adapted_execution_parameters.max_order_size_pct,
                participation_rate=self.adapted_execution_parameters.participation_rate,
                urgency_factor=self.adapted_execution_parameters.urgency_factor,
                price_improvement_threshold=self.adapted_execution_parameters.price_improvement_threshold,
                timeout_minutes=self.adapted_execution_parameters.timeout_minutes,
                slice_duration_minutes=self.adapted_execution_parameters.slice_duration_minutes,
                min_fill_size=self.adapted_execution_parameters.min_fill_size,
                max_market_impact_bps=self.adapted_execution_parameters.max_market_impact_bps
            )
            
            # Get category rules
            category_rules = self.config.category_execution_rules.get(self.current_template_category, {})
            max_adjustment = category_rules.get('max_execution_adjustment', 0.2)
            algorithm_flexibility = category_rules.get('algorithm_flexibility', 0.7)
            
            # Adapt parameters based on reasons
            adaptation_magnitude = 0.0
            algorithm_changes = []
            
            if 'high_slippage' in reasons:
                # Reduce participation rate and increase timeout
                participation_adjustment = min(max_adjustment, 0.2 * algorithm_flexibility)
                timeout_adjustment = min(max_adjustment, 0.3 * algorithm_flexibility)
                
                new_params.participation_rate *= (1 - participation_adjustment)
                new_params.timeout_minutes = int(new_params.timeout_minutes * (1 + timeout_adjustment))
                adaptation_magnitude += participation_adjustment + timeout_adjustment
                
                # Consider switching to more passive algorithm
                if algorithm_flexibility > 0.7 and new_params.execution_algorithm == ExecutionAlgorithm.SIMPLE:
                    new_params.execution_algorithm = ExecutionAlgorithm.TWAP
                    algorithm_changes.append("switched_to_twap_for_slippage")
            
            if 'low_fill_rate' in reasons:
                # Increase urgency and switch to more aggressive order types
                urgency_adjustment = min(max_adjustment, 0.3 * algorithm_flexibility)
                
                new_params.urgency_factor = min(1.0, new_params.urgency_factor * (1 + urgency_adjustment))
                adaptation_magnitude += urgency_adjustment
                
                # Switch to market orders if necessary
                if algorithm_flexibility > 0.5 and new_params.default_order_type == OrderType.LIMIT:
                    new_params.default_order_type = OrderType.MARKET
                    algorithm_changes.append("switched_to_market_orders_for_fills")
            
            if 'high_market_impact' in reasons:
                # Reduce order sizes and participation rate
                order_size_adjustment = min(max_adjustment, 0.25 * algorithm_flexibility)
                participation_adjustment = min(max_adjustment, 0.2 * algorithm_flexibility)
                
                new_params.max_order_size_pct *= (1 - order_size_adjustment)
                new_params.participation_rate *= (1 - participation_adjustment)
                adaptation_magnitude += order_size_adjustment + participation_adjustment
                
                # Switch to VWAP for better price execution
                if algorithm_flexibility > 0.6:
                    new_params.execution_algorithm = ExecutionAlgorithm.VWAP
                    algorithm_changes.append("switched_to_vwap_for_impact")
            
            if 'volatility_spike' in reasons:
                # Increase slice duration and reduce urgency
                volatility_adjustment = min(max_adjustment, 0.2 * algorithm_flexibility)
                
                new_params.slice_duration_minutes = min(30, int(new_params.slice_duration_minutes * (1 + volatility_adjustment)))
                new_params.urgency_factor *= (1 - volatility_adjustment)
                adaptation_magnitude += volatility_adjustment
                
                # Switch to more conservative execution
                if new_params.execution_algorithm == ExecutionAlgorithm.SIMPLE:
                    new_params.execution_algorithm = ExecutionAlgorithm.TWAP
                    algorithm_changes.append("switched_to_twap_for_volatility")
            
            if 'liquidity_dry_up' in reasons:
                # Reduce participation rate and increase patience
                liquidity_adjustment = min(max_adjustment, 0.3 * algorithm_flexibility)
                
                new_params.participation_rate *= (1 - liquidity_adjustment)
                new_params.timeout_minutes = int(new_params.timeout_minutes * (1 + liquidity_adjustment))
                adaptation_magnitude += liquidity_adjustment
                
                # Switch to iceberg orders for large positions
                if algorithm_flexibility > 0.8:
                    new_params.default_order_type = OrderType.ICEBERG
                    algorithm_changes.append("switched_to_iceberg_for_liquidity")
            
            # Ensure parameters stay within bounds
            new_params = self._enforce_execution_parameter_bounds(new_params)
            
            # Validate template compliance
            template_compliance = self._validate_execution_template_compliance(new_params)
            
            if template_compliance:
                # Calculate performance improvement estimate
                improvement_estimate = self._estimate_execution_performance_improvement(self.adapted_execution_parameters, new_params)
                
                # Calculate confidence score
                confidence_score = self._calculate_execution_adaptation_confidence(reasons, adaptation_magnitude)
                
                # Apply adaptations
                self.adapted_execution_parameters = new_params
                
                result = ExecutionAdaptationResult(
                    success=True,
                    adapted_parameters=new_params,
                    algorithm_changes=algorithm_changes,
                    adaptation_magnitude=adaptation_magnitude,
                    performance_improvement_estimate=improvement_estimate,
                    confidence_score=confidence_score,
                    adaptation_reasons=reasons,
                    template_compliance=True,
                    execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000
                )
                
            else:
                result = ExecutionAdaptationResult(
                    success=False,
                    adapted_parameters=self.adapted_execution_parameters,
                    algorithm_changes=[],
                    adaptation_magnitude=0.0,
                    performance_improvement_estimate=0.0,
                    confidence_score=0.0,
                    adaptation_reasons=reasons,
                    template_compliance=False,
                    execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                    error_message="Template compliance validation failed"
                )
            
            return result
            
        except Exception as e:
            error_msg = f"Execution adaptation failed: {e}"
            self.logger.error(error_msg)
            
            return ExecutionAdaptationResult(
                success=False,
                adapted_parameters=self.adapted_execution_parameters,
                algorithm_changes=[],
                adaptation_magnitude=0.0,
                performance_improvement_estimate=0.0,
                confidence_score=0.0,
                adaptation_reasons=reasons,
                template_compliance=False,
                execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                error_message=error_msg
            )
    
    async def _execute_single_order(self, order: Dict[str, Any], market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single order with current parameters (simplified simulation)"""
        try:
            # Simulate order execution based on current parameters
            symbol = order.get('symbol', 'UNKNOWN')
            side = order.get('side', 'buy')
            quantity = order.get('quantity', 100)
            order_type = order.get('order_type', self.adapted_execution_parameters.default_order_type.value)
            
            # Simulate execution metrics
            fill_rate = min(1.0, 0.7 + (self.current_liquidity_score * 0.3))
            executed_quantity = quantity * fill_rate
            
            # Simulate slippage based on market conditions
            base_slippage = 5.0  # 5 bps base slippage
            volatility_multiplier = 1.0 + (self.current_volatility * 10)
            liquidity_multiplier = 2.0 - self.current_liquidity_score
            participation_multiplier = 1.0 + (self.adapted_execution_parameters.participation_rate * 0.5)
            
            slippage_bps = base_slippage * volatility_multiplier * liquidity_multiplier * participation_multiplier
            
            # Simulate market impact
            market_impact_bps = min(self.adapted_execution_parameters.max_market_impact_bps, 
                                  slippage_bps * 0.6)
            
            # Calculate execution time
            base_time = 30.0  # 30 seconds base
            urgency_multiplier = 2.0 - self.adapted_execution_parameters.urgency_factor
            execution_time = base_time * urgency_multiplier
            
            return {
                'symbol': symbol,
                'side': side,
                'quantity_requested': quantity,
                'quantity_executed': executed_quantity,
                'fill_rate': fill_rate,
                'order_type': order_type,
                'execution_algorithm': self.adapted_execution_parameters.execution_algorithm.value,
                'slippage_bps': slippage_bps,
                'market_impact_bps': market_impact_bps,
                'execution_time_seconds': execution_time,
                'timestamp': datetime.now(),
                'success': fill_rate > 0.5
            }
            
        except Exception as e:
            self.logger.error(f"Error executing order: {e}")
            return {
                'symbol': order.get('symbol', 'UNKNOWN'),
                'success': False,
                'error': str(e)
            }
    
    def _track_execution_result(self, result: Dict[str, Any]):
        """Track execution result for adaptation"""
        try:
            if result.get('success', False):
                # Track metrics
                if 'slippage_bps' in result:
                    self.slippage_history.append(result['slippage_bps'])
                
                if 'fill_rate' in result:
                    self.fill_rate_history.append(result['fill_rate'])
                
                if 'market_impact_bps' in result:
                    self.market_impact_history.append(result['market_impact_bps'])
            
        except Exception as e:
            self.logger.error(f"Error tracking execution result: {e}")
    
    def _calculate_execution_metrics(self) -> ExecutionMetrics:
        """Calculate current execution metrics"""
        try:
            # Calculate from recent execution history
            recent_executions = list(self.execution_history)[-20:] if len(self.execution_history) > 0 else []
            
            if not recent_executions:
                return ExecutionMetrics()
            
            total_orders = len(recent_executions)
            filled_orders = len([e for e in recent_executions if e['data'].get('success', False)])
            fill_rate = filled_orders / total_orders if total_orders > 0 else 0.0
            
            # Calculate averages
            successful_executions = [e['data'] for e in recent_executions if e['data'].get('success', False)]
            
            avg_fill_time = np.mean([e.get('execution_time_seconds', 0) for e in successful_executions]) if successful_executions else 0.0
            avg_slippage = np.mean(list(self.slippage_history)) if self.slippage_history else 0.0
            avg_market_impact = np.mean(list(self.market_impact_history)) if self.market_impact_history else 0.0
            
            # Calculate implementation shortfall (simplified)
            implementation_shortfall = avg_slippage + avg_market_impact if successful_executions else 0.0
            
            # Calculate participation rate achieved
            participation_achieved = self.adapted_execution_parameters.participation_rate * fill_rate
            
            # Calculate price improvement rate (simplified)
            price_improvement_rate = max(0.0, 1.0 - (avg_slippage / 20.0)) if avg_slippage > 0 else 0.5
            
            return ExecutionMetrics(
                total_orders=total_orders,
                filled_orders=filled_orders,
                fill_rate=fill_rate,
                avg_fill_time_seconds=avg_fill_time,
                avg_slippage_bps=avg_slippage,
                avg_market_impact_bps=avg_market_impact,
                implementation_shortfall=implementation_shortfall,
                participation_rate_achieved=participation_achieved,
                price_improvement_rate=price_improvement_rate
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating execution metrics: {e}")
            return ExecutionMetrics()
    
    # Utility and validation methods
    def _enforce_execution_parameter_bounds(self, params: ExecutionParameters) -> ExecutionParameters:
        """Ensure execution parameters stay within reasonable bounds"""
        bounded_params = ExecutionParameters(
            default_order_type=params.default_order_type,
            execution_algorithm=params.execution_algorithm,
            max_order_size_pct=max(0.01, min(0.5, params.max_order_size_pct)),           # 1% to 50%
            participation_rate=max(0.05, min(0.8, params.participation_rate)),           # 5% to 80%
            urgency_factor=max(0.1, min(1.0, params.urgency_factor)),                   # 10% to 100%
            price_improvement_threshold=max(0.0001, min(0.01, params.price_improvement_threshold)),  # 0.01% to 1%
            timeout_minutes=max(5, min(180, params.timeout_minutes)),                    # 5 to 180 minutes
            slice_duration_minutes=max(1, min(60, params.slice_duration_minutes)),       # 1 to 60 minutes
            min_fill_size=max(1.0, min(10000.0, params.min_fill_size)),                 # $1 to $10,000
            max_market_impact_bps=max(1, min(100, params.max_market_impact_bps))         # 1 to 100 bps
        )
        
        return bounded_params
    
    def _validate_execution_template_compliance(self, params: ExecutionParameters) -> bool:
        """Validate execution parameters against template constraints"""
        try:
            # Get category rules
            category_rules = self.config.category_execution_rules.get(self.current_template_category, {})
            max_adjustment = category_rules.get('max_execution_adjustment', 0.3)
            
            # Check each parameter against base parameters
            base = self.base_execution_parameters
            
            # Calculate maximum allowed deviations
            checks = [
                ('max_order_size_pct', params.max_order_size_pct, base.max_order_size_pct),
                ('participation_rate', params.participation_rate, base.participation_rate),
                ('urgency_factor', params.urgency_factor, base.urgency_factor),
                ('timeout_minutes', params.timeout_minutes, base.timeout_minutes)
            ]
            
            for param_name, new_value, base_value in checks:
                if base_value > 0:
                    deviation = abs((new_value - base_value) / base_value)
                    if deviation > max_adjustment:
                        self.logger.warning(f"Execution parameter {param_name} deviation {deviation:.2%} exceeds limit {max_adjustment:.2%}")
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating execution template compliance: {e}")
            return False
    
    def _estimate_execution_performance_improvement(self, old_params: ExecutionParameters, new_params: ExecutionParameters) -> float:
        """Estimate performance improvement from parameter changes"""
        try:
            improvement_factors = []
            
            # Participation rate improvement
            if new_params.participation_rate != old_params.participation_rate:
                # Lower participation usually means less market impact
                participation_improvement = (old_params.participation_rate - new_params.participation_rate) / old_params.participation_rate
                improvement_factors.append(participation_improvement * 0.3)
            
            # Urgency factor improvement
            if new_params.urgency_factor != old_params.urgency_factor:
                # Higher urgency usually means faster fills but more slippage
                urgency_change = (new_params.urgency_factor - old_params.urgency_factor) / old_params.urgency_factor
                # Improvement depends on context - for now, assume moderate urgency is best
                optimal_urgency = 0.6
                old_distance = abs(old_params.urgency_factor - optimal_urgency)
                new_distance = abs(new_params.urgency_factor - optimal_urgency)
                if new_distance < old_distance:
                    improvement_factors.append(0.1)
            
            # Timeout improvement
            if new_params.timeout_minutes != old_params.timeout_minutes:
                # Longer timeouts usually mean better prices but slower execution
                timeout_improvement = (new_params.timeout_minutes - old_params.timeout_minutes) / old_params.timeout_minutes
                improvement_factors.append(timeout_improvement * 0.05)
            
            # Order size improvement
            if new_params.max_order_size_pct != old_params.max_order_size_pct:
                # Smaller orders usually mean less market impact
                size_improvement = (old_params.max_order_size_pct - new_params.max_order_size_pct) / old_params.max_order_size_pct
                improvement_factors.append(size_improvement * 0.2)
            
            # Calculate total improvement
            total_improvement = sum(improvement_factors)
            
            return max(0.0, min(0.3, total_improvement))  # Cap at 30% improvement
            
        except Exception as e:
            self.logger.error(f"Error estimating execution performance improvement: {e}")
            return 0.0
    
    def _calculate_execution_adaptation_confidence(self, reasons: List[str], adaptation_magnitude: float) -> float:
        """Calculate confidence in execution adaptation decision"""
        
        base_confidence = 0.75  # Base confidence for execution management
        
        # Adjust based on adaptation magnitude
        if adaptation_magnitude > 0.25:
            base_confidence -= 0.1  # Large changes are riskier
        elif adaptation_magnitude < 0.05:
            base_confidence -= 0.05  # Very small changes may not help
        
        # Adjust based on reasons
        reason_confidence_adjustments = {
            'high_slippage': 0.1,          # High confidence for slippage response
            'low_fill_rate': 0.08,         # High confidence for fill rate response
            'high_market_impact': 0.12,    # Highest confidence for impact response
            'volatility_spike': 0.05,      # Medium confidence for volatility response
            'liquidity_dry_up': 0.07       # High confidence for liquidity response
        }
        
        for reason in reasons:
            base_confidence += reason_confidence_adjustments.get(reason, 0.0)
        
        # Adjust based on historical adaptation success
        if len(self.adaptation_history) > 3:
            recent_success_rate = np.mean([a.success for a in self.adaptation_history[-3:]])
            base_confidence = base_confidence * 0.8 + recent_success_rate * 0.2
        
        # Adjust based on market conditions
        if self.current_liquidity_score > 0.8:
            base_confidence += 0.05  # Higher confidence in liquid markets
        elif self.current_liquidity_score < 0.4:
            base_confidence -= 0.05  # Lower confidence in illiquid markets
        
        return max(0.1, min(1.0, base_confidence))
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend direction for a list of values"""
        if len(values) < 3:
            return 0.0
        
        # Simple linear regression slope
        x = np.arange(len(values))
        y = np.array(values)
        slope, _ = np.polyfit(x, y, 1)
        
        return slope
    
    def _execution_metrics_to_dict(self, metrics: ExecutionMetrics) -> Dict[str, Any]:
        """Convert execution metrics to dictionary for serialization"""
        return {
            'total_orders': metrics.total_orders,
            'filled_orders': metrics.filled_orders,
            'fill_rate': metrics.fill_rate,
            'avg_fill_time_seconds': metrics.avg_fill_time_seconds,
            'avg_slippage_bps': metrics.avg_slippage_bps,
            'avg_market_impact_bps': metrics.avg_market_impact_bps,
            'implementation_shortfall': metrics.implementation_shortfall,
            'participation_rate_achieved': metrics.participation_rate_achieved,
            'price_improvement_rate': metrics.price_improvement_rate
        }
    
    def _execution_parameters_to_dict(self, params: ExecutionParameters) -> Dict[str, Any]:
        """Convert execution parameters to dictionary for serialization"""
        return {
            'default_order_type': params.default_order_type.value,
            'execution_algorithm': params.execution_algorithm.value,
            'max_order_size_pct': params.max_order_size_pct,
            'participation_rate': params.participation_rate,
            'urgency_factor': params.urgency_factor,
            'price_improvement_threshold': params.price_improvement_threshold,
            'timeout_minutes': params.timeout_minutes,
            'slice_duration_minutes': params.slice_duration_minutes,
            'min_fill_size': params.min_fill_size,
            'max_market_impact_bps': params.max_market_impact_bps
        }
