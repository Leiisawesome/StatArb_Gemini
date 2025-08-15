"""
Adaptation Coordinator - Multi-Strategy Adaptation Coordination
==============================================================

Coordinates multiple adaptation strategies and resolves conflicts between
different adaptation recommendations with template inheritance awareness.

Author: Pro Quant Desk Trader
"""

import asyncio
import logging
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple, Set
from collections import defaultdict, deque

from strategy_templates.base import TemplateRegistry, TemplateCategory
from .dynamic_adaptation_framework import DynamicAdaptationFramework, AdaptationTrigger, AdaptationMode, AdaptationResult
from .performance_adaptation import PerformanceAdaptation, PerformanceDegradationLevel
from .market_regime_adaptation import MarketRegimeAdaptation, MarketRegime
from .parameter_optimizer import ParameterOptimizer, OptimizationResult


class AdaptationPriority(Enum):
    """Priority levels for different types of adaptations"""
    EMERGENCY = "emergency"          # Crisis response (highest priority)
    HIGH = "high"                   # Risk management adaptations
    MEDIUM = "medium"               # Performance optimizations
    LOW = "low"                     # Routine adjustments
    MAINTENANCE = "maintenance"      # Background optimizations


class AdaptationConflictResolution(Enum):
    """Methods for resolving conflicting adaptation recommendations"""
    HIGHEST_PRIORITY = "highest_priority"    # Use highest priority adaptation
    WEIGHTED_AVERAGE = "weighted_average"    # Weighted combination
    CONSERVATIVE_CHOICE = "conservative_choice"  # Most conservative option
    TEMPLATE_BASED = "template_based"        # Based on template category
    PERFORMANCE_BASED = "performance_based"  # Based on historical performance


@dataclass
class AdaptationRequest:
    """Request for parameter adaptation"""
    source: str                              # Source of the request
    priority: AdaptationPriority
    trigger: AdaptationTrigger
    parameters: Dict[str, float]
    confidence: float
    timestamp: datetime
    context: Dict[str, Any] = field(default_factory=dict)
    template_category: Optional[TemplateCategory] = None


@dataclass
class CoordinatorConfig:
    """Configuration for the adaptation coordinator"""
    # Conflict resolution settings
    conflict_resolution_method: AdaptationConflictResolution = AdaptationConflictResolution.TEMPLATE_BASED
    max_adaptation_frequency: timedelta = timedelta(minutes=15)
    min_confidence_threshold: float = 0.6
    
    # Priority weights for different adaptation sources
    source_weights: Dict[str, float] = field(default_factory=lambda: {
        'performance_adaptation': 0.30,
        'market_regime_adaptation': 0.25,
        'parameter_optimizer': 0.20,
        'dynamic_framework': 0.15,
        'manual_override': 0.10
    })
    
    # Template category coordination settings
    category_coordination_rules: Dict[TemplateCategory, Dict[str, Any]] = field(default_factory=lambda: {
        TemplateCategory.BASE: {
            'max_simultaneous_adaptations': 1,
            'adaptation_aggressiveness': 0.5,
            'conflict_tolerance': 0.3
        },
        TemplateCategory.SPECIFIC: {
            'max_simultaneous_adaptations': 2,
            'adaptation_aggressiveness': 0.8,
            'conflict_tolerance': 0.5
        },
        TemplateCategory.COMPOSITE: {
            'max_simultaneous_adaptations': 3,
            'adaptation_aggressiveness': 1.0,
            'conflict_tolerance': 0.7
        }
    })
    
    # Safety and validation settings
    enable_adaptation_validation: bool = True
    max_parameter_deviation: float = 0.5  # 50% max deviation from original
    require_consensus_threshold: float = 0.7  # 70% agreement for major changes
    adaptation_rollback_enabled: bool = True


@dataclass
class CoordinationResult:
    """Result of adaptation coordination"""
    success: bool
    final_parameters: Dict[str, Any]
    coordination_method: AdaptationConflictResolution
    participating_sources: List[str]
    conflicts_detected: int
    conflicts_resolved: int
    confidence_score: float
    adaptation_magnitude: float
    execution_time_ms: float
    recommendations: List[str]
    error_message: Optional[str] = None
    source_contributions: Dict[str, float] = field(default_factory=dict)


class AdaptationCoordinator:
    """
    Coordinates multiple adaptation strategies and resolves conflicts
    """
    
    def __init__(self, 
                 template_registry: TemplateRegistry,
                 config: Optional[CoordinatorConfig] = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.template_registry = template_registry
        self.config = config or CoordinatorConfig()
        
        # Adaptation components
        self.adaptation_framework: Optional[DynamicAdaptationFramework] = None
        self.performance_adaptation: Optional[PerformanceAdaptation] = None
        self.regime_adaptation: Optional[MarketRegimeAdaptation] = None
        self.parameter_optimizer: Optional[ParameterOptimizer] = None
        
        # Coordination state
        self.pending_requests: deque = deque(maxlen=100)
        self.active_adaptations: Dict[str, AdaptationRequest] = {}
        self.adaptation_history: List[CoordinationResult] = []
        self.last_adaptation_time: Optional[datetime] = None
        
        # Template context
        self.current_template_id: Optional[str] = None
        self.current_template_category: Optional[TemplateCategory] = None
        self.original_parameters: Dict[str, Any] = {}
        
        # Conflict tracking
        self.conflict_patterns: Dict[str, int] = defaultdict(int)
        self.source_performance: Dict[str, List[float]] = defaultdict(list)
        
        self.logger.info("Adaptation Coordinator initialized")
    
    def initialize_adaptation_components(self,
                                       adaptation_framework: DynamicAdaptationFramework,
                                       performance_adaptation: PerformanceAdaptation,
                                       regime_adaptation: MarketRegimeAdaptation,
                                       parameter_optimizer: ParameterOptimizer):
        """Initialize all adaptation components"""
        self.adaptation_framework = adaptation_framework
        self.performance_adaptation = performance_adaptation
        self.regime_adaptation = regime_adaptation
        self.parameter_optimizer = parameter_optimizer
        
        self.logger.info("All adaptation components initialized")
    
    def initialize_for_template(self, template_id: str, initial_parameters: Dict[str, Any]):
        """Initialize coordinator for a specific template"""
        try:
            template = self.template_registry.get_template(template_id)
            if not template:
                raise ValueError(f"Template {template_id} not found")
            
            self.current_template_id = template_id
            self.current_template_category = template.metadata.category
            self.original_parameters = initial_parameters.copy()
            
            # Clear state
            self.pending_requests.clear()
            self.active_adaptations.clear()
            self.last_adaptation_time = None
            
            self.logger.info(f"Coordinator initialized for template {template_id} (category: {self.current_template_category.value})")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize coordinator: {e}")
            raise
    
    async def coordinate_adaptations(self, 
                                   market_data: Dict[str, Any],
                                   performance_metrics: Dict[str, float],
                                   current_parameters: Dict[str, Any]) -> CoordinationResult:
        """
        Coordinate all adaptation strategies and resolve conflicts
        """
        try:
            start_time = datetime.now()
            
            # Check if adaptation is allowed (frequency limits)
            if not self._can_adapt_now():
                return CoordinationResult(
                    success=False,
                    final_parameters=current_parameters,
                    coordination_method=self.config.conflict_resolution_method,
                    participating_sources=[],
                    conflicts_detected=0,
                    conflicts_resolved=0,
                    confidence_score=0.0,
                    adaptation_magnitude=0.0,
                    execution_time_ms=0.0,
                    recommendations=["Adaptation frequency limit reached"],
                    error_message="Too frequent adaptation attempts"
                )
            
            # Collect adaptation requests from all sources
            adaptation_requests = await self._collect_adaptation_requests(
                market_data, performance_metrics, current_parameters
            )
            
            if not adaptation_requests:
                return CoordinationResult(
                    success=True,
                    final_parameters=current_parameters,
                    coordination_method=self.config.conflict_resolution_method,
                    participating_sources=[],
                    conflicts_detected=0,
                    conflicts_resolved=0,
                    confidence_score=1.0,
                    adaptation_magnitude=0.0,
                    execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                    recommendations=["No adaptations needed"]
                )
            
            # Detect and analyze conflicts
            conflicts = self._detect_conflicts(adaptation_requests)
            
            # Resolve conflicts and determine final parameters
            final_parameters, coordination_details = await self._resolve_conflicts(
                adaptation_requests, conflicts, current_parameters
            )
            
            # Validate the final parameters
            validation_result = self._validate_adaptation(final_parameters, current_parameters)
            
            if not validation_result['valid']:
                return CoordinationResult(
                    success=False,
                    final_parameters=current_parameters,
                    coordination_method=self.config.conflict_resolution_method,
                    participating_sources=[req.source for req in adaptation_requests],
                    conflicts_detected=len(conflicts),
                    conflicts_resolved=0,
                    confidence_score=0.0,
                    adaptation_magnitude=0.0,
                    execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                    recommendations=["Validation failed"],
                    error_message=validation_result['error_message']
                )
            
            # Calculate metrics
            adaptation_magnitude = self._calculate_adaptation_magnitude(current_parameters, final_parameters)
            confidence_score = self._calculate_coordination_confidence(adaptation_requests, coordination_details)
            
            # Record successful coordination
            result = CoordinationResult(
                success=True,
                final_parameters=final_parameters,
                coordination_method=coordination_details['method'],
                participating_sources=[req.source for req in adaptation_requests],
                conflicts_detected=len(conflicts),
                conflicts_resolved=coordination_details['conflicts_resolved'],
                confidence_score=confidence_score,
                adaptation_magnitude=adaptation_magnitude,
                execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                recommendations=coordination_details['recommendations'],
                source_contributions=coordination_details['contributions']
            )
            
            # Update state
            self.last_adaptation_time = datetime.now()
            self.adaptation_history.append(result)
            self._update_source_performance(adaptation_requests, result)
            
            return result
            
        except Exception as e:
            error_msg = f"Coordination failed: {e}"
            self.logger.error(error_msg)
            
            return CoordinationResult(
                success=False,
                final_parameters=current_parameters,
                coordination_method=self.config.conflict_resolution_method,
                participating_sources=[],
                conflicts_detected=0,
                conflicts_resolved=0,
                confidence_score=0.0,
                adaptation_magnitude=0.0,
                execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                recommendations=[],
                error_message=error_msg
            )
    
    def get_coordination_summary(self) -> Dict[str, Any]:
        """Get comprehensive coordination summary"""
        if not self.adaptation_history:
            return {
                'total_coordinations': 0,
                'success_rate': 0.0,
                'average_conflicts': 0.0,
                'conflict_resolution_rate': 0.0,
                'source_effectiveness': {},
                'coordination_trends': 'no_data'
            }
        
        successful_coordinations = [r for r in self.adaptation_history if r.success]
        
        return {
            'total_coordinations': len(self.adaptation_history),
            'success_rate': len(successful_coordinations) / len(self.adaptation_history),
            'average_conflicts': np.mean([r.conflicts_detected for r in self.adaptation_history]),
            'conflict_resolution_rate': np.mean([r.conflicts_resolved / max(1, r.conflicts_detected) for r in self.adaptation_history]),
            'average_confidence': np.mean([r.confidence_score for r in successful_coordinations]) if successful_coordinations else 0.0,
            'average_adaptation_magnitude': np.mean([r.adaptation_magnitude for r in successful_coordinations]) if successful_coordinations else 0.0,
            'source_effectiveness': self._analyze_source_effectiveness(),
            'coordination_trends': self._analyze_coordination_trends(),
            'conflict_patterns': dict(self.conflict_patterns)
        }
    
    # Private helper methods
    def _can_adapt_now(self) -> bool:
        """Check if adaptation is allowed based on frequency limits"""
        if not self.last_adaptation_time:
            return True
        
        time_since_last = datetime.now() - self.last_adaptation_time
        return time_since_last >= self.config.max_adaptation_frequency
    
    async def _collect_adaptation_requests(self, 
                                         market_data: Dict[str, Any],
                                         performance_metrics: Dict[str, float],
                                         current_parameters: Dict[str, Any]) -> List[AdaptationRequest]:
        """Collect adaptation requests from all sources"""
        requests = []
        
        try:
            # Performance Adaptation
            if self.performance_adaptation:
                perf_needed = self.performance_adaptation.update_performance_metrics(performance_metrics)
                if perf_needed:
                    perf_params = self.performance_adaptation.get_adaptation_parameters(
                        self.performance_adaptation.last_degradation_level
                    )
                    if perf_params:
                        requests.append(AdaptationRequest(
                            source='performance_adaptation',
                            priority=self._map_degradation_to_priority(self.performance_adaptation.last_degradation_level),
                            trigger=AdaptationTrigger.PERFORMANCE_DEGRADATION,
                            parameters=perf_params,
                            confidence=0.8,
                            timestamp=datetime.now(),
                            template_category=self.current_template_category
                        ))
            
            # Market Regime Adaptation
            if self.regime_adaptation:
                regime_changed = self.regime_adaptation.update_market_data(market_data)
                if regime_changed:
                    regime_params = self.regime_adaptation.get_regime_adaptation_parameters()
                    if regime_params:
                        requests.append(AdaptationRequest(
                            source='market_regime_adaptation',
                            priority=AdaptationPriority.MEDIUM,
                            trigger=AdaptationTrigger.MARKET_REGIME_CHANGE,
                            parameters=regime_params,
                            confidence=self.regime_adaptation.regime_confidence,
                            timestamp=datetime.now(),
                            template_category=self.current_template_category
                        ))
            
            # Parameter Optimizer
            if self.parameter_optimizer:
                opt_recommendations = self.parameter_optimizer.get_optimization_recommendations(
                    current_parameters, performance_metrics
                )
                if opt_recommendations.get('expected_improvement', 0) > 0.05:  # 5% threshold
                    # Generate optimization parameters (simplified)
                    opt_params = {
                        'signal_threshold_adjustment': 0.05,
                        'position_size_adjustment': -0.02
                    }
                    requests.append(AdaptationRequest(
                        source='parameter_optimizer',
                        priority=AdaptationPriority.LOW,
                        trigger=AdaptationTrigger.MANUAL_TRIGGER,
                        parameters=opt_params,
                        confidence=0.7,
                        timestamp=datetime.now(),
                        template_category=self.current_template_category
                    ))
            
            # Dynamic Adaptation Framework
            if self.adaptation_framework:
                triggers_needed, triggers = await self.adaptation_framework.check_adaptation_triggers(
                    market_data, performance_metrics
                )
                if triggers_needed:
                    # Get adaptation from framework
                    framework_result = await self.adaptation_framework.execute_adaptation(
                        market_data, performance_metrics, triggers
                    )
                    if framework_result.success:
                        # Convert to parameter adjustments
                        framework_params = self._convert_adaptation_result_to_parameters(framework_result)
                        requests.append(AdaptationRequest(
                            source='dynamic_framework',
                            priority=self._map_trigger_to_priority(triggers[0] if triggers else AdaptationTrigger.MANUAL_TRIGGER),
                            trigger=triggers[0] if triggers else AdaptationTrigger.MANUAL_TRIGGER,
                            parameters=framework_params,
                            confidence=framework_result.confidence_score,
                            timestamp=datetime.now(),
                            template_category=self.current_template_category
                        ))
            
        except Exception as e:
            self.logger.error(f"Error collecting adaptation requests: {e}")
        
        # Filter requests by confidence threshold
        filtered_requests = [r for r in requests if r.confidence >= self.config.min_confidence_threshold]
        
        self.logger.info(f"Collected {len(filtered_requests)} adaptation requests from {len(set(r.source for r in filtered_requests))} sources")
        
        return filtered_requests
    
    def _detect_conflicts(self, requests: List[AdaptationRequest]) -> List[Tuple[AdaptationRequest, AdaptationRequest, str]]:
        """Detect conflicts between adaptation requests"""
        conflicts = []
        
        for i, req1 in enumerate(requests):
            for j, req2 in enumerate(requests[i+1:], i+1):
                conflict_type = self._check_parameter_conflict(req1, req2)
                if conflict_type:
                    conflicts.append((req1, req2, conflict_type))
                    
                    # Record conflict pattern
                    conflict_key = f"{req1.source}-{req2.source}"
                    self.conflict_patterns[conflict_key] += 1
        
        return conflicts
    
    def _check_parameter_conflict(self, req1: AdaptationRequest, req2: AdaptationRequest) -> Optional[str]:
        """Check if two requests conflict on parameter adjustments"""
        
        # Check for opposing adjustments
        for param in req1.parameters:
            if param in req2.parameters:
                val1 = req1.parameters[param]
                val2 = req2.parameters[param]
                
                # Check for opposing directions
                if (val1 > 0 and val2 < 0) or (val1 < 0 and val2 > 0):
                    if abs(val1) > 0.05 and abs(val2) > 0.05:  # Significant opposing changes
                        return "opposing_direction"
                
                # Check for magnitude conflicts
                if abs(val1 - val2) > 0.2:  # 20% difference threshold
                    return "magnitude_conflict"
        
        # Check for priority conflicts
        if req1.priority == AdaptationPriority.EMERGENCY and req2.priority == AdaptationPriority.EMERGENCY:
            return "priority_conflict"
        
        return None
    
    async def _resolve_conflicts(self, 
                               requests: List[AdaptationRequest],
                               conflicts: List[Tuple[AdaptationRequest, AdaptationRequest, str]],
                               current_parameters: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Resolve conflicts and determine final parameters"""
        
        method = self.config.conflict_resolution_method
        final_parameters = current_parameters.copy()
        coordination_details = {
            'method': method,
            'conflicts_resolved': 0,
            'recommendations': [],
            'contributions': {}
        }
        
        if not requests:
            return final_parameters, coordination_details
        
        try:
            if method == AdaptationConflictResolution.HIGHEST_PRIORITY:
                final_parameters, details = self._resolve_by_priority(requests, current_parameters)
            elif method == AdaptationConflictResolution.WEIGHTED_AVERAGE:
                final_parameters, details = self._resolve_by_weighted_average(requests, current_parameters)
            elif method == AdaptationConflictResolution.CONSERVATIVE_CHOICE:
                final_parameters, details = self._resolve_by_conservative_choice(requests, current_parameters)
            elif method == AdaptationConflictResolution.TEMPLATE_BASED:
                final_parameters, details = self._resolve_by_template_category(requests, current_parameters)
            elif method == AdaptationConflictResolution.PERFORMANCE_BASED:
                final_parameters, details = self._resolve_by_performance_history(requests, current_parameters)
            else:
                # Default to template-based
                final_parameters, details = self._resolve_by_template_category(requests, current_parameters)
            
            coordination_details.update(details)
            coordination_details['conflicts_resolved'] = len(conflicts)
            
        except Exception as e:
            self.logger.error(f"Error resolving conflicts: {e}")
            coordination_details['recommendations'].append(f"Conflict resolution failed: {e}")
        
        return final_parameters, coordination_details
    
    def _resolve_by_priority(self, requests: List[AdaptationRequest], current_parameters: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Resolve conflicts by using highest priority request"""
        
        # Sort by priority (emergency first)
        priority_order = [AdaptationPriority.EMERGENCY, AdaptationPriority.HIGH, AdaptationPriority.MEDIUM, AdaptationPriority.LOW, AdaptationPriority.MAINTENANCE]
        sorted_requests = sorted(requests, key=lambda r: priority_order.index(r.priority))
        
        final_parameters = current_parameters.copy()
        contributions = {}
        
        # Apply highest priority request
        if sorted_requests:
            highest_priority_req = sorted_requests[0]
            final_parameters = self._apply_parameter_adjustments(final_parameters, highest_priority_req.parameters)
            contributions[highest_priority_req.source] = 1.0
        
        return final_parameters, {
            'contributions': contributions,
            'recommendations': [f"Applied highest priority adaptation from {highest_priority_req.source}"]
        }
    
    def _resolve_by_weighted_average(self, requests: List[AdaptationRequest], current_parameters: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Resolve conflicts by weighted average of all requests"""
        
        final_parameters = current_parameters.copy()
        contributions = {}
        parameter_adjustments = defaultdict(list)
        
        # Collect all parameter adjustments with weights
        total_weight = 0.0
        for req in requests:
            source_weight = self.config.source_weights.get(req.source, 0.1)
            confidence_weight = req.confidence
            priority_weight = self._get_priority_weight(req.priority)
            
            combined_weight = source_weight * confidence_weight * priority_weight
            total_weight += combined_weight
            contributions[req.source] = combined_weight
            
            for param, adjustment in req.parameters.items():
                parameter_adjustments[param].append((adjustment, combined_weight))
        
        # Calculate weighted average for each parameter
        if total_weight > 0:
            for param, adjustments in parameter_adjustments.items():
                weighted_sum = sum(adj * weight for adj, weight in adjustments)
                avg_adjustment = weighted_sum / total_weight
                
                if param in final_parameters:
                    final_parameters[param] = final_parameters[param] * (1 + avg_adjustment)
                else:
                    final_parameters[param] = avg_adjustment
            
            # Normalize contributions
            for source in contributions:
                contributions[source] /= total_weight
        
        return final_parameters, {
            'contributions': contributions,
            'recommendations': [f"Applied weighted average of {len(requests)} adaptation requests"]
        }
    
    def _resolve_by_conservative_choice(self, requests: List[AdaptationRequest], current_parameters: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Resolve conflicts by choosing the most conservative option"""
        
        final_parameters = current_parameters.copy()
        contributions = {}
        
        # For each parameter, choose the most conservative adjustment
        all_parameters = set()
        for req in requests:
            all_parameters.update(req.parameters.keys())
        
        for param in all_parameters:
            adjustments = []
            sources = []
            
            for req in requests:
                if param in req.parameters:
                    adjustments.append(req.parameters[param])
                    sources.append(req.source)
            
            if adjustments:
                # Choose most conservative (smallest absolute value)
                conservative_idx = min(range(len(adjustments)), key=lambda i: abs(adjustments[i]))
                conservative_adjustment = adjustments[conservative_idx]
                conservative_source = sources[conservative_idx]
                
                final_parameters = self._apply_parameter_adjustments(final_parameters, {param: conservative_adjustment})
                contributions[conservative_source] = contributions.get(conservative_source, 0) + 1
        
        # Normalize contributions
        total_contributions = sum(contributions.values())
        if total_contributions > 0:
            for source in contributions:
                contributions[source] /= total_contributions
        
        return final_parameters, {
            'contributions': contributions,
            'recommendations': ["Applied most conservative adaptation choices"]
        }
    
    def _resolve_by_template_category(self, requests: List[AdaptationRequest], current_parameters: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Resolve conflicts based on template category rules"""
        
        if not self.current_template_category:
            return self._resolve_by_weighted_average(requests, current_parameters)
        
        category_rules = self.config.category_coordination_rules[self.current_template_category]
        max_adaptations = category_rules['max_simultaneous_adaptations']
        aggressiveness = category_rules['adaptation_aggressiveness']
        
        # Limit number of simultaneous adaptations
        limited_requests = requests[:max_adaptations] if len(requests) > max_adaptations else requests
        
        # Apply aggressiveness factor to all adjustments
        final_parameters = current_parameters.copy()
        contributions = {}
        
        for req in limited_requests:
            adjusted_params = {}
            for param, adjustment in req.parameters.items():
                adjusted_params[param] = adjustment * aggressiveness
            
            final_parameters = self._apply_parameter_adjustments(final_parameters, adjusted_params)
            contributions[req.source] = aggressiveness
        
        return final_parameters, {
            'contributions': contributions,
            'recommendations': [f"Applied {len(limited_requests)} adaptations with {aggressiveness:.1%} aggressiveness for {self.current_template_category.value} template"]
        }
    
    def _resolve_by_performance_history(self, requests: List[AdaptationRequest], current_parameters: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Resolve conflicts based on historical performance of sources"""
        
        # Calculate source reliability based on historical performance
        source_reliability = {}
        for req in requests:
            if req.source in self.source_performance and self.source_performance[req.source]:
                source_reliability[req.source] = np.mean(self.source_performance[req.source])
            else:
                source_reliability[req.source] = 0.5  # Default reliability
        
        # Weight requests by reliability
        weighted_requests = []
        for req in requests:
            reliability = source_reliability[req.source]
            weighted_requests.append((req, reliability))
        
        # Sort by reliability and apply top performers
        weighted_requests.sort(key=lambda x: x[1], reverse=True)
        
        final_parameters = current_parameters.copy()
        contributions = {}
        
        total_reliability = sum(reliability for _, reliability in weighted_requests)
        
        for req, reliability in weighted_requests:
            weight = reliability / total_reliability if total_reliability > 0 else 1.0 / len(weighted_requests)
            
            adjusted_params = {}
            for param, adjustment in req.parameters.items():
                adjusted_params[param] = adjustment * weight
            
            final_parameters = self._apply_parameter_adjustments(final_parameters, adjusted_params)
            contributions[req.source] = weight
        
        return final_parameters, {
            'contributions': contributions,
            'recommendations': [f"Applied adaptations weighted by historical performance reliability"]
        }
    
    def _apply_parameter_adjustments(self, parameters: Dict[str, Any], adjustments: Dict[str, float]) -> Dict[str, Any]:
        """Apply parameter adjustments to current parameters"""
        updated_parameters = parameters.copy()
        
        for param, adjustment in adjustments.items():
            if param.endswith('_adjustment'):
                # This is an adjustment to an existing parameter
                base_param = param.replace('_adjustment', '')
                if base_param in updated_parameters:
                    current_value = updated_parameters[base_param]
                    if isinstance(current_value, (int, float)):
                        updated_parameters[base_param] = current_value * (1 + adjustment)
            elif param.endswith('_multiplier'):
                # This is a multiplier for an existing parameter
                base_param = param.replace('_multiplier', '')
                if base_param in updated_parameters:
                    current_value = updated_parameters[base_param]
                    if isinstance(current_value, (int, float)):
                        updated_parameters[base_param] = current_value * adjustment
            else:
                # Direct parameter update
                if param in updated_parameters:
                    current_value = updated_parameters[param]
                    if isinstance(current_value, (int, float)):
                        updated_parameters[param] = current_value + adjustment
                else:
                    updated_parameters[param] = adjustment
        
        return updated_parameters
    
    def _validate_adaptation(self, new_parameters: Dict[str, Any], original_parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that the adaptation is safe and reasonable"""
        
        if not self.config.enable_adaptation_validation:
            return {'valid': True}
        
        # Check for excessive parameter deviations
        for param, new_value in new_parameters.items():
            if param in original_parameters:
                original_value = original_parameters[param]
                if isinstance(original_value, (int, float)) and original_value != 0:
                    deviation = abs((new_value - original_value) / original_value)
                    if deviation > self.config.max_parameter_deviation:
                        return {
                            'valid': False,
                            'error_message': f"Parameter {param} deviation {deviation:.2%} exceeds maximum {self.config.max_parameter_deviation:.2%}"
                        }
        
        # Check for reasonable parameter ranges
        reasonable_ranges = {
            'signal_threshold': (0.01, 0.99),
            'max_position_size': (0.001, 0.8),
            'risk_per_trade': (0.001, 0.1),
            'stop_loss_pct': (0.005, 0.5),
            'take_profit_pct': (0.01, 2.0)
        }
        
        for param, value in new_parameters.items():
            if param in reasonable_ranges and isinstance(value, (int, float)):
                min_val, max_val = reasonable_ranges[param]
                if value < min_val or value > max_val:
                    return {
                        'valid': False,
                        'error_message': f"Parameter {param} value {value} outside reasonable range [{min_val}, {max_val}]"
                    }
        
        return {'valid': True}
    
    def _calculate_adaptation_magnitude(self, original: Dict[str, Any], adapted: Dict[str, Any]) -> float:
        """Calculate the magnitude of adaptation"""
        total_change = 0.0
        param_count = 0
        
        for param, new_value in adapted.items():
            if param in original and isinstance(new_value, (int, float)) and isinstance(original[param], (int, float)):
                if original[param] != 0:
                    relative_change = abs((new_value - original[param]) / original[param])
                    total_change += relative_change
                    param_count += 1
        
        return total_change / param_count if param_count > 0 else 0.0
    
    def _calculate_coordination_confidence(self, requests: List[AdaptationRequest], details: Dict[str, Any]) -> float:
        """Calculate confidence in the coordination result"""
        if not requests:
            return 1.0
        
        # Base confidence from request confidences
        avg_request_confidence = np.mean([req.confidence for req in requests])
        
        # Penalty for conflicts
        conflict_penalty = 1.0 - (details.get('conflicts_detected', 0) * 0.1)
        
        # Bonus for consensus
        if len(requests) > 1:
            consensus_bonus = 1.0 + (details.get('conflicts_resolved', 0) / max(1, details.get('conflicts_detected', 1))) * 0.2
        else:
            consensus_bonus = 1.0
        
        # Template category confidence adjustment
        category_adjustment = {
            TemplateCategory.BASE: 0.9,
            TemplateCategory.SPECIFIC: 1.0,
            TemplateCategory.COMPOSITE: 0.8
        }.get(self.current_template_category, 1.0)
        
        confidence = avg_request_confidence * conflict_penalty * consensus_bonus * category_adjustment
        
        return min(1.0, max(0.0, confidence))
    
    def _map_degradation_to_priority(self, degradation_level: PerformanceDegradationLevel) -> AdaptationPriority:
        """Map performance degradation level to adaptation priority"""
        mapping = {
            PerformanceDegradationLevel.CRITICAL: AdaptationPriority.EMERGENCY,
            PerformanceDegradationLevel.MAJOR: AdaptationPriority.HIGH,
            PerformanceDegradationLevel.MODERATE: AdaptationPriority.MEDIUM,
            PerformanceDegradationLevel.MINOR: AdaptationPriority.LOW,
            PerformanceDegradationLevel.NONE: AdaptationPriority.MAINTENANCE
        }
        return mapping.get(degradation_level, AdaptationPriority.LOW)
    
    def _map_trigger_to_priority(self, trigger: AdaptationTrigger) -> AdaptationPriority:
        """Map adaptation trigger to priority level"""
        mapping = {
            AdaptationTrigger.RISK_THRESHOLD_BREACH: AdaptationPriority.EMERGENCY,
            AdaptationTrigger.PERFORMANCE_DEGRADATION: AdaptationPriority.HIGH,
            AdaptationTrigger.MARKET_REGIME_CHANGE: AdaptationPriority.MEDIUM,
            AdaptationTrigger.VOLATILITY_CHANGE: AdaptationPriority.MEDIUM,
            AdaptationTrigger.CORRELATION_BREAKDOWN: AdaptationPriority.LOW,
            AdaptationTrigger.MANUAL_TRIGGER: AdaptationPriority.LOW
        }
        return mapping.get(trigger, AdaptationPriority.LOW)
    
    def _get_priority_weight(self, priority: AdaptationPriority) -> float:
        """Get weight for different priority levels"""
        weights = {
            AdaptationPriority.EMERGENCY: 2.0,
            AdaptationPriority.HIGH: 1.5,
            AdaptationPriority.MEDIUM: 1.0,
            AdaptationPriority.LOW: 0.7,
            AdaptationPriority.MAINTENANCE: 0.5
        }
        return weights.get(priority, 1.0)
    
    def _convert_adaptation_result_to_parameters(self, result: AdaptationResult) -> Dict[str, float]:
        """Convert adaptation result to parameter adjustments"""
        # Simplified conversion - in practice this would be more sophisticated
        adjustments = {}
        
        magnitude = result.adaptation_magnitude
        
        if result.adaptation_type == AdaptationTrigger.PERFORMANCE_DEGRADATION:
            adjustments['signal_threshold_adjustment'] = magnitude * 0.1  # Increase selectivity
            adjustments['position_size_multiplier'] = 1.0 - magnitude * 0.2  # Reduce positions
        elif result.adaptation_type == AdaptationTrigger.VOLATILITY_CHANGE:
            adjustments['stop_loss_multiplier'] = 1.0 + magnitude * 0.3  # Widen stops
            adjustments['position_size_multiplier'] = 1.0 - magnitude * 0.1  # Reduce positions
        elif result.adaptation_type == AdaptationTrigger.MARKET_REGIME_CHANGE:
            adjustments['signal_threshold_adjustment'] = magnitude * 0.05  # Slight selectivity change
        
        return adjustments
    
    def _update_source_performance(self, requests: List[AdaptationRequest], result: CoordinationResult):
        """Update performance tracking for adaptation sources"""
        for req in requests:
            if req.source in result.source_contributions:
                contribution = result.source_contributions[req.source]
                performance_score = result.confidence_score * contribution
                
                self.source_performance[req.source].append(performance_score)
                
                # Keep only recent performance data
                if len(self.source_performance[req.source]) > 20:
                    self.source_performance[req.source] = self.source_performance[req.source][-20:]
    
    def _analyze_source_effectiveness(self) -> Dict[str, Dict[str, float]]:
        """Analyze effectiveness of different adaptation sources"""
        effectiveness = {}
        
        for source, performance_history in self.source_performance.items():
            if performance_history:
                effectiveness[source] = {
                    'average_performance': np.mean(performance_history),
                    'consistency': 1.0 - np.std(performance_history),  # Lower std = higher consistency
                    'recent_trend': self._calculate_trend(performance_history[-5:]) if len(performance_history) >= 5 else 0.0,
                    'usage_count': len(performance_history)
                }
        
        return effectiveness
    
    def _analyze_coordination_trends(self) -> str:
        """Analyze trends in coordination results"""
        if len(self.adaptation_history) < 3:
            return 'insufficient_data'
        
        recent_confidence = [r.confidence_score for r in self.adaptation_history[-5:]]
        
        if len(recent_confidence) > 1:
            trend_slope = np.polyfit(range(len(recent_confidence)), recent_confidence, 1)[0]
            
            if trend_slope > 0.05:
                return 'improving'
            elif trend_slope < -0.05:
                return 'declining'
            else:
                return 'stable'
        
        return 'stable'
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend direction for a list of values"""
        if len(values) < 2:
            return 0.0
        
        return np.polyfit(range(len(values)), values, 1)[0]
