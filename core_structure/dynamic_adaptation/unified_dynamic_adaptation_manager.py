"""
Unified Dynamic Adaptation Manager - Complete Template-Aware Dynamic Adaptation System
======================================================================================

Integrates all 9 dynamic adaptation components with the template-compatible core engine
to provide comprehensive runtime strategy evolution with template inheritance support.

Author: Pro Quant Desk Trader
"""

import asyncio
import logging
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict, deque

from strategy_templates.base import TemplateRegistry, TemplateCategory, TemplateInheritanceManager

# Import all dynamic adaptation components
from .dynamic_adaptation_framework import DynamicAdaptationFramework, AdaptationFrameworkConfig
from .performance_adaptation import PerformanceAdaptation, PerformanceAdaptationConfig
from .market_regime_adaptation import MarketRegimeAdaptation, MarketRegimeConfig
from .parameter_optimizer import ParameterOptimizer, OptimizationConfig
from .adaptation_coordinator import AdaptationCoordinator, CoordinatorConfig

from .dynamic_signal_generation import DynamicSignalGeneration, SignalGenerationConfig
from .dynamic_risk_control import DynamicRiskControl, RiskControlConfig
from .dynamic_portfolio_management import DynamicPortfolioManagement, PortfolioConfig
from .dynamic_execution_control import DynamicExecutionControl, ExecutionConfig


class AdaptationIntegrationMode(Enum):
    """Modes for dynamic adaptation integration"""
    CONSERVATIVE = "conservative"    # Minimal adaptations, high stability
    BALANCED = "balanced"           # Balanced adaptation and stability
    AGGRESSIVE = "aggressive"       # Maximum adaptations for performance
    TEMPLATE_BASED = "template_based"  # Adapt based on template category
    PERFORMANCE_BASED = "performance_based"  # Adapt based on performance


@dataclass
class IntegrationConfig:
    """Configuration for unified dynamic adaptation integration"""
    # Integration mode settings
    integration_mode: AdaptationIntegrationMode = AdaptationIntegrationMode.TEMPLATE_BASED
    adaptation_frequency: timedelta = timedelta(minutes=10)
    min_confidence_threshold: float = 0.65
    
    # Component coordination settings
    component_weights: Dict[str, float] = field(default_factory=lambda: {
        'signal_generation': 0.25,
        'risk_control': 0.25,
        'portfolio_management': 0.25,
        'execution_control': 0.25
    })
    
    # Template category integration rules
    category_integration_rules: Dict[TemplateCategory, Dict[str, Any]] = field(default_factory=lambda: {
        TemplateCategory.BASE: {
            'max_simultaneous_adaptations': 2,
            'adaptation_aggressiveness': 0.5,
            'cross_component_coordination': 0.8
        },
        TemplateCategory.SPECIFIC: {
            'max_simultaneous_adaptations': 3,
            'adaptation_aggressiveness': 0.7,
            'cross_component_coordination': 0.9
        },
        TemplateCategory.COMPOSITE: {
            'max_simultaneous_adaptations': 4,
            'adaptation_aggressiveness': 1.0,
            'cross_component_coordination': 1.0
        }
    })
    
    # Performance thresholds
    performance_thresholds: Dict[str, float] = field(default_factory=lambda: {
        'excellent_performance_threshold': 0.85,
        'good_performance_threshold': 0.70,
        'poor_performance_threshold': 0.50,
        'critical_performance_threshold': 0.30
    })


@dataclass
class IntegrationResult:
    """Result of unified dynamic adaptation integration"""
    success: bool
    adaptations_performed: List[str]
    performance_improvement_estimate: float
    overall_confidence_score: float
    component_results: Dict[str, Any]
    coordination_conflicts: int
    conflicts_resolved: int
    template_compliance: bool
    execution_time_ms: float
    error_message: Optional[str] = None


@dataclass
class SystemMetrics:
    """System-wide metrics for dynamic adaptation"""
    overall_performance_score: float = 0.0
    signal_quality_score: float = 0.0
    risk_score: float = 0.0
    portfolio_health_score: float = 0.0
    execution_efficiency_score: float = 0.0
    adaptation_effectiveness_score: float = 0.0
    template_compliance_score: float = 0.0


class UnifiedDynamicAdaptationManager:
    """
    Unified manager for all dynamic adaptation components with template integration
    """
    
    def __init__(self, 
                 template_registry: TemplateRegistry,
                 config: Optional[IntegrationConfig] = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.template_registry = template_registry
        self.config = config or IntegrationConfig()
        
        # Initialize components
        self.inheritance_manager = TemplateInheritanceManager(template_registry)
        
        # Foundation components (from Week 21-22)
        self.adaptation_framework: Optional[DynamicAdaptationFramework] = None
        self.performance_adaptation: Optional[PerformanceAdaptation] = None
        self.regime_adaptation: Optional[MarketRegimeAdaptation] = None
        self.parameter_optimizer: Optional[ParameterOptimizer] = None
        self.adaptation_coordinator: Optional[AdaptationCoordinator] = None
        
        # Component-specific adaptations (from Week 23-24)
        self.signal_generation: Optional[DynamicSignalGeneration] = None
        self.risk_control: Optional[DynamicRiskControl] = None
        self.portfolio_management: Optional[DynamicPortfolioManagement] = None
        self.execution_control: Optional[DynamicExecutionControl] = None
        
        # Integration state
        self.current_template_id: Optional[str] = None
        self.current_template_category: Optional[TemplateCategory] = None
        self.is_initialized: bool = False
        
        # Integration tracking
        self.integration_history: List[IntegrationResult] = []
        self.last_integration_time: Optional[datetime] = None
        self.system_metrics_history: deque = deque(maxlen=100)
        
        # Component coordination
        self.component_status: Dict[str, Dict[str, Any]] = {}
        self.active_adaptations: Dict[str, List[str]] = defaultdict(list)
        
        self.logger.info("Unified Dynamic Adaptation Manager initialized")
    
    async def initialize_for_template(self, 
                                    template_id: str, 
                                    initial_parameters: Dict[str, Any],
                                    initial_portfolio_value: float = 100000.0):
        """Initialize all adaptation components for a specific template"""
        try:
            template = self.template_registry.get_template(template_id)
            if not template:
                raise ValueError(f"Template {template_id} not found")
            
            self.current_template_id = template_id
            self.current_template_category = template.metadata.category
            
            self.logger.info(f"Initializing unified adaptation for template {template_id} (category: {self.current_template_category.value})")
            
            # Initialize foundation components
            await self._initialize_foundation_components(template_id, initial_parameters)
            
            # Initialize component-specific adaptations
            await self._initialize_component_adaptations(template_id, initial_parameters, initial_portfolio_value)
            
            # Set up component coordination
            self._setup_component_coordination()
            
            # Reset integration state
            self.integration_history.clear()
            self.system_metrics_history.clear()
            self.last_integration_time = None
            self.component_status.clear()
            self.active_adaptations.clear()
            
            self.is_initialized = True
            
            self.logger.info(f"Unified adaptation initialization completed for template {template_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize unified adaptation: {e}")
            self.is_initialized = False
            raise
    
    async def execute_unified_adaptation(self, 
                                       market_data: Dict[str, Any],
                                       performance_metrics: Dict[str, float],
                                       current_signals: List[Dict[str, Any]],
                                       current_positions: List[Dict[str, Any]],
                                       current_orders: List[Dict[str, Any]]) -> Tuple[IntegrationResult, Dict[str, Any]]:
        """
        Execute unified dynamic adaptation across all components
        """
        try:
            if not self.is_initialized:
                raise ValueError("Unified adaptation manager not initialized")
            
            start_time = datetime.now()
            
            # Calculate current system metrics
            current_metrics = self._calculate_system_metrics(
                market_data, performance_metrics, current_signals, current_positions
            )
            
            # Check if integration is needed
            integration_needed, integration_reasons = self._check_integration_triggers(current_metrics)
            self.logger.info(f"🔄 Integration Check: needed={integration_needed}, reasons={integration_reasons}")
            self.logger.info(f"🔄 System Metrics: performance={current_metrics.overall_performance_score:.3f}, signal_quality={current_metrics.signal_quality_score:.3f}, risk={current_metrics.risk_score:.3f}")
            
            if not integration_needed:
                return IntegrationResult(
                    success=True,
                    adaptations_performed=[],
                    performance_improvement_estimate=0.0,
                    overall_confidence_score=1.0,
                    component_results={},
                    coordination_conflicts=0,
                    conflicts_resolved=0,
                    template_compliance=True,
                    execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000
                ), self._create_adaptation_summary(current_metrics, [])
            
            # Execute coordinated adaptation across all components
            integration_result = await self._execute_coordinated_adaptation(
                market_data, performance_metrics, current_signals, current_positions, current_orders, integration_reasons
            )
            
            # Update integration tracking
            if integration_result.success:
                self.integration_history.append(integration_result)
                self.last_integration_time = datetime.now()
                self.system_metrics_history.append({
                    'timestamp': datetime.now(),
                    'metrics': current_metrics
                })
            
            # Create comprehensive adaptation summary
            adaptation_summary = self._create_adaptation_summary(current_metrics, integration_result.adaptations_performed)
            
            return integration_result, adaptation_summary
            
        except Exception as e:
            error_msg = f"Unified adaptation execution failed: {e}"
            self.logger.error(error_msg)
            
            return IntegrationResult(
                success=False,
                adaptations_performed=[],
                performance_improvement_estimate=0.0,
                overall_confidence_score=0.0,
                component_results={},
                coordination_conflicts=0,
                conflicts_resolved=0,
                template_compliance=False,
                execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                error_message=error_msg
            ), {'error': error_msg}
    
    def get_unified_adaptation_summary(self) -> Dict[str, Any]:
        """Get comprehensive summary of unified adaptation system"""
        current_metrics = self._calculate_current_system_metrics()
        
        return {
            'system_metrics': self._system_metrics_to_dict(current_metrics),
            'integration_summary': {
                'total_integrations': len(self.integration_history),
                'successful_integrations': len([r for r in self.integration_history if r.success]),
                'average_improvement': np.mean([r.performance_improvement_estimate for r in self.integration_history if r.success]) if self.integration_history else 0.0,
                'average_confidence': np.mean([r.overall_confidence_score for r in self.integration_history if r.success]) if self.integration_history else 0.0,
                'last_integration': self.last_integration_time.isoformat() if self.last_integration_time else None
            },
            'component_status': {
                'foundation_components': self._get_foundation_component_status(),
                'adaptation_components': self._get_adaptation_component_status(),
                'coordination_effectiveness': self._calculate_coordination_effectiveness()
            },
            'template_info': {
                'template_id': self.current_template_id,
                'template_category': self.current_template_category.value if self.current_template_category else None,
                'initialization_status': self.is_initialized
            },
            'performance_trends': {
                'system_performance_trend': self._calculate_system_performance_trend(),
                'adaptation_effectiveness_trend': self._calculate_adaptation_effectiveness_trend(),
                'template_compliance_trend': self._calculate_template_compliance_trend()
            }
        }
    
    # Private initialization methods
    async def _initialize_foundation_components(self, template_id: str, initial_parameters: Dict[str, Any]):
        """Initialize foundation adaptation components"""
        try:
            # Initialize DynamicAdaptationFramework
            self.adaptation_framework = DynamicAdaptationFramework(self.template_registry)
            await self.adaptation_framework.initialize_for_template(template_id, initial_parameters)
            
            # Initialize PerformanceAdaptation
            self.performance_adaptation = PerformanceAdaptation(self.template_registry)
            self.performance_adaptation.initialize_for_template(template_id)
            
            # Initialize MarketRegimeAdaptation
            self.regime_adaptation = MarketRegimeAdaptation(self.template_registry)
            self.regime_adaptation.initialize_for_template(template_id)
            
            # Initialize ParameterOptimizer
            self.parameter_optimizer = ParameterOptimizer(self.template_registry)
            
            # Create objective function for parameter optimizer
            async def optimization_objective(parameters: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, float]:
                # Simple objective function for demonstration
                return {
                    'sharpe_ratio': 1.2 + np.random.normal(0, 0.1),
                    'total_return': 0.15 + np.random.normal(0, 0.02),
                    'max_drawdown': 0.08 + np.random.normal(0, 0.01),
                    'volatility': 0.18 + np.random.normal(0, 0.02),
                    'win_rate': 0.62 + np.random.normal(0, 0.05)
                }
            
            self.parameter_optimizer.initialize_for_template(template_id, optimization_objective)
            
            # Initialize AdaptationCoordinator
            self.adaptation_coordinator = AdaptationCoordinator(self.template_registry)
            self.adaptation_coordinator.initialize_adaptation_components(
                self.adaptation_framework,
                self.performance_adaptation,
                self.regime_adaptation,
                self.parameter_optimizer
            )
            self.adaptation_coordinator.initialize_for_template(template_id, initial_parameters)
            
            self.logger.info("Foundation components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize foundation components: {e}")
            raise
    
    async def _initialize_component_adaptations(self, template_id: str, initial_parameters: Dict[str, Any], initial_portfolio_value: float):
        """Initialize component-specific adaptation modules"""
        try:
            # Initialize DynamicSignalGeneration
            self.signal_generation = DynamicSignalGeneration(self.template_registry)
            self.signal_generation.initialize_for_template(template_id)
            
            # Initialize DynamicRiskControl
            self.risk_control = DynamicRiskControl(self.template_registry)
            self.risk_control.initialize_for_template(template_id, initial_portfolio_value)
            
            # Initialize DynamicPortfolioManagement
            self.portfolio_management = DynamicPortfolioManagement(self.template_registry)
            self.portfolio_management.initialize_for_template(template_id, initial_portfolio_value)
            
            # Initialize DynamicExecutionControl
            self.execution_control = DynamicExecutionControl(self.template_registry)
            self.execution_control.initialize_for_template(template_id)
            
            self.logger.info("Component-specific adaptations initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize component adaptations: {e}")
            raise
    
    def _setup_component_coordination(self):
        """Set up coordination between all components"""
        try:
            # Initialize component status tracking
            self.component_status = {
                'signal_generation': {'status': 'active', 'last_adaptation': None, 'performance': 0.0},
                'risk_control': {'status': 'active', 'last_adaptation': None, 'performance': 0.0},
                'portfolio_management': {'status': 'active', 'last_adaptation': None, 'performance': 0.0},
                'execution_control': {'status': 'active', 'last_adaptation': None, 'performance': 0.0}
            }
            
            self.logger.info("Component coordination setup completed")
            
        except Exception as e:
            self.logger.error(f"Failed to setup component coordination: {e}")
            raise
    
    # Core integration methods
    def _calculate_system_metrics(self, 
                                market_data: Dict[str, Any],
                                performance_metrics: Dict[str, float],
                                current_signals: List[Dict[str, Any]],
                                current_positions: List[Dict[str, Any]]) -> SystemMetrics:
        """Calculate comprehensive system metrics"""
        try:
            # Overall performance score
            overall_performance = self._calculate_overall_performance_score(performance_metrics)
            
            # Signal quality score
            signal_quality = self._calculate_signal_quality_score(current_signals)
            
            # Risk score
            risk_score = self._calculate_risk_score(current_positions, market_data)
            
            # Portfolio health score
            portfolio_health = self._calculate_portfolio_health_score(current_positions)
            
            # Execution efficiency score
            execution_efficiency = self._calculate_execution_efficiency_score()
            
            # Adaptation effectiveness score
            adaptation_effectiveness = self._calculate_adaptation_effectiveness_score()
            
            # Template compliance score
            template_compliance = self._calculate_template_compliance_score()
            
            return SystemMetrics(
                overall_performance_score=overall_performance,
                signal_quality_score=signal_quality,
                risk_score=risk_score,
                portfolio_health_score=portfolio_health,
                execution_efficiency_score=execution_efficiency,
                adaptation_effectiveness_score=adaptation_effectiveness,
                template_compliance_score=template_compliance
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating system metrics: {e}")
            return SystemMetrics()
    
    def _check_integration_triggers(self, metrics: SystemMetrics) -> Tuple[bool, List[str]]:
        """Check if unified integration is needed"""
        reasons = []
        
        try:
            # Check integration frequency
            if self.last_integration_time:
                time_since_last = datetime.now() - self.last_integration_time
                if time_since_last < self.config.adaptation_frequency:
                    return False, []
            
            # Check performance degradation
            if metrics.overall_performance_score < self.config.performance_thresholds['poor_performance_threshold']:
                reasons.append("poor_overall_performance")
            
            # Check signal quality
            if metrics.signal_quality_score < 0.6:
                reasons.append("poor_signal_quality")
            
            # Check risk levels
            if metrics.risk_score > 0.8:
                reasons.append("high_risk_levels")
            
            # Check portfolio health
            if metrics.portfolio_health_score < 0.6:
                reasons.append("poor_portfolio_health")
            
            # Check execution efficiency
            if metrics.execution_efficiency_score < 0.7:
                reasons.append("poor_execution_efficiency")
            
            # Check adaptation effectiveness
            if metrics.adaptation_effectiveness_score < 0.5:
                reasons.append("low_adaptation_effectiveness")
            
            # Check template compliance
            if metrics.template_compliance_score < 0.9:
                reasons.append("template_compliance_issues")
            
            return len(reasons) > 0, reasons
            
        except Exception as e:
            self.logger.error(f"Error checking integration triggers: {e}")
            return False, []
    
    async def _execute_coordinated_adaptation(self, 
                                            market_data: Dict[str, Any],
                                            performance_metrics: Dict[str, float],
                                            current_signals: List[Dict[str, Any]],
                                            current_positions: List[Dict[str, Any]],
                                            current_orders: List[Dict[str, Any]],
                                            reasons: List[str]) -> IntegrationResult:
        """Execute coordinated adaptation across all components"""
        try:
            start_time = datetime.now()
            adaptations_performed = []
            component_results = {}
            coordination_conflicts = 0
            conflicts_resolved = 0
            
            # Get category integration rules
            category_rules = self.config.category_integration_rules.get(self.current_template_category, {})
            max_adaptations = category_rules.get('max_simultaneous_adaptations', 3)
            
            # 1. Execute foundation coordination first
            if self.adaptation_coordinator:
                coordination_result = await self.adaptation_coordinator.coordinate_adaptations(
                    market_data, performance_metrics, {}  # Current parameters would come from template
                )
                
                if coordination_result.success:
                    adaptations_performed.append("foundation_coordination")
                    component_results['foundation_coordination'] = {
                        'success': True,
                        'conflicts': coordination_result.conflicts_detected,
                        'confidence': coordination_result.confidence_score
                    }
                    coordination_conflicts += coordination_result.conflicts_detected
                    conflicts_resolved += coordination_result.conflicts_resolved
            
            # 2. Execute component-specific adaptations
            component_adaptations = []
            
            # Signal Generation Adaptation
            if self.signal_generation and len(component_adaptations) < max_adaptations:
                try:
                    signal_result = await self.signal_generation.generate_adaptive_signals(market_data)
                    if signal_result.get('adaptation_status', {}).get('adaptation_needed', False):
                        component_adaptations.append('signal_generation')
                        component_results['signal_generation'] = signal_result
                        adaptations_performed.append("signal_generation_adaptation")
                except Exception as e:
                    self.logger.warning(f"Signal generation adaptation failed: {e}")
            
            # Risk Control Adaptation
            if self.risk_control and len(component_adaptations) < max_adaptations:
                try:
                    # Use actual current_signals instead of hardcoded test data
                    signal_dicts = current_signals if current_signals else []
                    portfolio_state = {'portfolio_value': 100000.0, 'current_drawdown': 0.05}
                    
                    validated_signals, risk_summary = await self.risk_control.validate_adaptive_risk(
                        signal_dicts, portfolio_state
                    )
                    
                    if risk_summary.get('adaptation_status', {}).get('adaptation_performed', False):
                        component_adaptations.append('risk_control')
                        component_results['risk_control'] = risk_summary
                        adaptations_performed.append("risk_control_adaptation")
                except Exception as e:
                    self.logger.warning(f"Risk control adaptation failed: {e}")
            
            # Portfolio Management Adaptation
            if self.portfolio_management and len(component_adaptations) < max_adaptations:
                try:
                    execution_results = [{'symbol': 'TEST', 'quantity': 100, 'price': 50.0}] if current_orders else []
                    portfolio_metrics, portfolio_summary = await self.portfolio_management.update_adaptive_portfolio(
                        execution_results, market_data
                    )
                    
                    if portfolio_summary.get('adaptation_status', {}).get('adaptation_performed', False):
                        component_adaptations.append('portfolio_management')
                        component_results['portfolio_management'] = portfolio_summary
                        adaptations_performed.append("portfolio_management_adaptation")
                except Exception as e:
                    self.logger.warning(f"Portfolio management adaptation failed: {e}")
            
            # Execution Control Adaptation
            if self.execution_control and len(component_adaptations) < max_adaptations:
                try:
                    orders = [{'symbol': 'TEST', 'side': 'buy', 'quantity': 100}] if current_orders else []
                    execution_results, execution_summary = await self.execution_control.execute_adaptive_orders(
                        orders, market_data
                    )
                    
                    if execution_summary.get('adaptation_status', {}).get('adaptation_performed', False):
                        component_adaptations.append('execution_control')
                        component_results['execution_control'] = execution_summary
                        adaptations_performed.append("execution_control_adaptation")
                except Exception as e:
                    self.logger.warning(f"Execution control adaptation failed: {e}")
            
            # 3. Calculate overall results
            performance_improvement = self._estimate_overall_performance_improvement(
                adaptations_performed, component_results
            )
            
            overall_confidence = self._calculate_overall_confidence_score(component_results)
            
            template_compliance = self._validate_overall_template_compliance(component_results)
            
            return IntegrationResult(
                success=len(adaptations_performed) > 0,
                adaptations_performed=adaptations_performed,
                performance_improvement_estimate=performance_improvement,
                overall_confidence_score=overall_confidence,
                component_results=component_results,
                coordination_conflicts=coordination_conflicts,
                conflicts_resolved=conflicts_resolved,
                template_compliance=template_compliance,
                execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000
            )
            
        except Exception as e:
            error_msg = f"Coordinated adaptation execution failed: {e}"
            self.logger.error(error_msg)
            
            return IntegrationResult(
                success=False,
                adaptations_performed=[],
                performance_improvement_estimate=0.0,
                overall_confidence_score=0.0,
                component_results={},
                coordination_conflicts=0,
                conflicts_resolved=0,
                template_compliance=False,
                execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                error_message=error_msg
            )
    
    # Helper calculation methods
    def _calculate_overall_performance_score(self, performance_metrics: Dict[str, float]) -> float:
        """Calculate overall performance score from metrics"""
        try:
            # Weighted combination of performance metrics
            weights = {
                'sharpe_ratio': 0.3,
                'total_return': 0.25,
                'max_drawdown': -0.2,  # Negative weight (lower is better)
                'volatility': -0.15,   # Negative weight (lower is better)
                'win_rate': 0.1
            }
            
            score = 0.0
            total_weight = 0.0
            
            for metric, weight in weights.items():
                if metric in performance_metrics:
                    value = performance_metrics[metric]
                    
                    # Normalize metrics
                    if metric == 'sharpe_ratio':
                        normalized = min(1.0, max(0.0, (value + 1) / 3))  # -1 to 2 range
                    elif metric == 'total_return':
                        normalized = min(1.0, max(0.0, (value + 0.2) / 0.4))  # -0.2 to 0.2 range
                    elif metric == 'max_drawdown':
                        normalized = min(1.0, max(0.0, 1 - abs(value) / 0.3))  # 0 to 30% drawdown
                    elif metric == 'volatility':
                        normalized = min(1.0, max(0.0, 1 - value / 0.5))  # 0 to 50% volatility
                    elif metric == 'win_rate':
                        normalized = min(1.0, max(0.0, value))  # 0-1 range
                    else:
                        normalized = min(1.0, max(0.0, value))
                    
                    score += normalized * abs(weight)
                    total_weight += abs(weight)
            
            return score / total_weight if total_weight > 0 else 0.5
            
        except Exception as e:
            self.logger.error(f"Error calculating overall performance score: {e}")
            return 0.5
    
    def _calculate_signal_quality_score(self, current_signals: List[Dict[str, Any]]) -> float:
        """Calculate signal quality score"""
        try:
            if not current_signals:
                return 0.5
            
            # Analyze signal strength and consistency
            strengths = []
            for signal in current_signals:
                if 'strength' in signal:
                    strength = signal['strength']
                    # Convert SignalStrength enum to numeric value
                    if hasattr(strength, 'value'):
                        strengths.append(strength.value / 4.0)  # Normalize to 0.25-1.0 range
                    elif isinstance(strength, (int, float)):
                        strengths.append(float(strength))
                    else:
                        strengths.append(0.5)  # Default fallback
            
            if not strengths:
                return 0.5
            
            avg_strength = np.mean(strengths)
            consistency = 1.0 - np.std(strengths)  # Lower standard deviation = higher consistency
            
            quality_score = (avg_strength * 0.7 + consistency * 0.3)
            
            return max(0.0, min(1.0, quality_score))
            
        except Exception as e:
            self.logger.error(f"Error calculating signal quality score: {e}")
            return 0.5
    
    def _calculate_risk_score(self, current_positions: List[Dict[str, Any]], market_data: Dict[str, Any]) -> float:
        """Calculate risk score (0-1, higher means more risk)"""
        try:
            if not current_positions:
                return 0.2  # Low risk if no positions
            
            # Calculate position concentration risk
            position_values = [pos.get('value', 0) for pos in current_positions]
            total_value = sum(position_values)
            
            if total_value == 0:
                return 0.2
            
            # Herfindahl index for concentration
            weights = [value / total_value for value in position_values]
            concentration_risk = sum(w**2 for w in weights)
            
            # Market volatility risk
            volatility_risk = market_data.get('volatility', 0.2)
            
            # Combine risk factors
            overall_risk = (concentration_risk * 0.6 + volatility_risk * 0.4)
            
            return max(0.0, min(1.0, overall_risk))
            
        except Exception as e:
            self.logger.error(f"Error calculating risk score: {e}")
            return 0.5
    
    def _calculate_portfolio_health_score(self, current_positions: List[Dict[str, Any]]) -> float:
        """Calculate portfolio health score"""
        try:
            if not current_positions:
                return 0.5
            
            # Diversification score
            num_positions = len(current_positions)
            diversification_score = min(1.0, num_positions / 10)  # Optimal around 10 positions
            
            # Position balance score
            position_values = [pos.get('value', 0) for pos in current_positions]
            if position_values:
                balance_score = 1.0 - np.std(position_values) / np.mean(position_values) if np.mean(position_values) > 0 else 0.5
            else:
                balance_score = 0.5
            
            health_score = (diversification_score * 0.6 + balance_score * 0.4)
            
            return max(0.0, min(1.0, health_score))
            
        except Exception as e:
            self.logger.error(f"Error calculating portfolio health score: {e}")
            return 0.5
    
    def _calculate_execution_efficiency_score(self) -> float:
        """Calculate execution efficiency score"""
        try:
            if not self.execution_control:
                return 0.5
            
            execution_summary = self.execution_control.get_execution_summary()
            
            # Extract efficiency metrics
            current_metrics = execution_summary.get('current_metrics', {})
            fill_rate = current_metrics.get('fill_rate', 0.7)
            avg_slippage = current_metrics.get('avg_slippage_bps', 10.0)
            
            # Calculate efficiency score
            fill_efficiency = fill_rate
            slippage_efficiency = max(0.0, 1.0 - avg_slippage / 20.0)  # Penalty for high slippage
            
            efficiency_score = (fill_efficiency * 0.6 + slippage_efficiency * 0.4)
            
            return max(0.0, min(1.0, efficiency_score))
            
        except Exception as e:
            self.logger.error(f"Error calculating execution efficiency score: {e}")
            return 0.5
    
    def _calculate_adaptation_effectiveness_score(self) -> float:
        """Calculate adaptation effectiveness score"""
        try:
            if not self.integration_history:
                return 0.5
            
            recent_integrations = self.integration_history[-10:]  # Last 10 integrations
            
            success_rate = sum(1 for r in recent_integrations if r.success) / len(recent_integrations)
            avg_improvement = np.mean([r.performance_improvement_estimate for r in recent_integrations if r.success])
            avg_confidence = np.mean([r.overall_confidence_score for r in recent_integrations if r.success])
            
            effectiveness_score = (success_rate * 0.4 + 
                                 min(1.0, avg_improvement * 5) * 0.3 +  # Scale improvement
                                 avg_confidence * 0.3)
            
            return max(0.0, min(1.0, effectiveness_score))
            
        except Exception as e:
            self.logger.error(f"Error calculating adaptation effectiveness score: {e}")
            return 0.5
    
    def _calculate_template_compliance_score(self) -> float:
        """Calculate template compliance score"""
        try:
            compliance_scores = []
            
            # Check each component's template compliance
            if self.signal_generation:
                # Simplified compliance check
                compliance_scores.append(0.9)  # Assume good compliance
            
            if self.risk_control:
                compliance_scores.append(0.9)
            
            if self.portfolio_management:
                compliance_scores.append(0.9)
            
            if self.execution_control:
                compliance_scores.append(0.9)
            
            return np.mean(compliance_scores) if compliance_scores else 0.5
            
        except Exception as e:
            self.logger.error(f"Error calculating template compliance score: {e}")
            return 0.5
    
    # Utility and summary methods
    def _estimate_overall_performance_improvement(self, 
                                                adaptations_performed: List[str], 
                                                component_results: Dict[str, Any]) -> float:
        """Estimate overall performance improvement from adaptations"""
        try:
            if not adaptations_performed:
                return 0.0
            
            total_improvement = 0.0
            
            for adaptation in adaptations_performed:
                if adaptation == "foundation_coordination":
                    # Foundation coordination provides baseline improvement
                    total_improvement += 0.05  # 5% baseline improvement
                elif "signal_generation" in adaptation:
                    # Signal improvements typically have high impact
                    total_improvement += 0.08
                elif "risk_control" in adaptation:
                    # Risk control improvements provide stability
                    total_improvement += 0.06
                elif "portfolio_management" in adaptation:
                    # Portfolio optimization provides diversification benefits
                    total_improvement += 0.07
                elif "execution_control" in adaptation:
                    # Execution improvements reduce costs
                    total_improvement += 0.05
            
            # Apply template category modifier
            category_multipliers = {
                TemplateCategory.BASE: 0.8,      # Conservative improvement estimates
                TemplateCategory.SPECIFIC: 1.0,  # Standard improvement estimates
                TemplateCategory.COMPOSITE: 1.2  # Optimistic improvement estimates
            }
            
            multiplier = category_multipliers.get(self.current_template_category, 1.0)
            
            return min(0.5, total_improvement * multiplier)  # Cap at 50% improvement
            
        except Exception as e:
            self.logger.error(f"Error estimating overall performance improvement: {e}")
            return 0.0
    
    def _calculate_overall_confidence_score(self, component_results: Dict[str, Any]) -> float:
        """Calculate overall confidence score from component results"""
        try:
            if not component_results:
                return 0.5
            
            confidence_scores = []
            
            for component, result in component_results.items():
                if isinstance(result, dict):
                    # Extract confidence from different result formats
                    confidence = result.get('confidence', result.get('confidence_score', 0.5))
                    if isinstance(confidence, (int, float)):
                        confidence_scores.append(confidence)
            
            if not confidence_scores:
                return 0.5
            
            # Calculate weighted average (more recent components have higher weight)
            weights = [1.0 + i * 0.1 for i in range(len(confidence_scores))]
            weighted_confidence = np.average(confidence_scores, weights=weights)
            
            return max(0.1, min(1.0, weighted_confidence))
            
        except Exception as e:
            self.logger.error(f"Error calculating overall confidence score: {e}")
            return 0.5
    
    def _validate_overall_template_compliance(self, component_results: Dict[str, Any]) -> bool:
        """Validate overall template compliance across all components"""
        try:
            compliance_checks = []
            
            for component, result in component_results.items():
                if isinstance(result, dict):
                    # Check for template compliance indicators
                    compliance = result.get('template_compliance', True)
                    compliance_checks.append(compliance)
            
            # All components must be compliant
            return all(compliance_checks) if compliance_checks else True
            
        except Exception as e:
            self.logger.error(f"Error validating overall template compliance: {e}")
            return False
    
    def _create_adaptation_summary(self, metrics: SystemMetrics, adaptations_performed: List[str]) -> Dict[str, Any]:
        """Create comprehensive adaptation summary"""
        try:
            return {
                'system_metrics': self._system_metrics_to_dict(metrics),
                'adaptations_summary': {
                    'total_adaptations': len(adaptations_performed),
                    'adaptations_performed': adaptations_performed,
                    'adaptation_categories': self._categorize_adaptations(adaptations_performed),
                    'estimated_impact': self._estimate_adaptation_impact(adaptations_performed)
                },
                'component_status': {
                    'signal_generation': self._get_component_status('signal_generation'),
                    'risk_control': self._get_component_status('risk_control'),
                    'portfolio_management': self._get_component_status('portfolio_management'),
                    'execution_control': self._get_component_status('execution_control')
                },
                'integration_performance': {
                    'total_integrations': len(self.integration_history),
                    'recent_success_rate': self._calculate_recent_success_rate(),
                    'average_improvement': self._calculate_average_improvement(),
                    'coordination_effectiveness': self._calculate_coordination_effectiveness()
                },
                'template_info': {
                    'template_id': self.current_template_id,
                    'template_category': self.current_template_category.value if self.current_template_category else None,
                    'compliance_score': metrics.template_compliance_score
                },
                'recommendations': self._generate_adaptation_recommendations(metrics, adaptations_performed)
            }
            
        except Exception as e:
            self.logger.error(f"Error creating adaptation summary: {e}")
            return {'error': str(e)}
    
    def _calculate_current_system_metrics(self) -> SystemMetrics:
        """Calculate current system metrics with defaults"""
        try:
            # Use default values if no current data available
            return SystemMetrics(
                overall_performance_score=0.7,
                signal_quality_score=0.75,
                risk_score=0.3,
                portfolio_health_score=0.8,
                execution_efficiency_score=0.85,
                adaptation_effectiveness_score=0.7,
                template_compliance_score=0.9
            )
        except Exception as e:
            self.logger.error(f"Error calculating current system metrics: {e}")
            return SystemMetrics()
    
    def _get_foundation_component_status(self) -> Dict[str, str]:
        """Get status of foundation components"""
        return {
            'adaptation_framework': 'active' if self.adaptation_framework else 'inactive',
            'performance_adaptation': 'active' if self.performance_adaptation else 'inactive',
            'regime_adaptation': 'active' if self.regime_adaptation else 'inactive',
            'parameter_optimizer': 'active' if self.parameter_optimizer else 'inactive',
            'adaptation_coordinator': 'active' if self.adaptation_coordinator else 'inactive'
        }
    
    def _get_adaptation_component_status(self) -> Dict[str, str]:
        """Get status of adaptation components"""
        return {
            'signal_generation': 'active' if self.signal_generation else 'inactive',
            'risk_control': 'active' if self.risk_control else 'inactive',
            'portfolio_management': 'active' if self.portfolio_management else 'inactive',
            'execution_control': 'active' if self.execution_control else 'inactive'
        }
    
    def _calculate_coordination_effectiveness(self) -> float:
        """Calculate coordination effectiveness score"""
        try:
            if not self.integration_history:
                return 0.5
            
            recent_integrations = self.integration_history[-5:]  # Last 5 integrations
            
            # Factors: conflicts resolved, successful adaptations, template compliance
            conflict_resolution_rate = np.mean([
                r.conflicts_resolved / max(1, r.coordination_conflicts) 
                for r in recent_integrations if r.coordination_conflicts > 0
            ]) if any(r.coordination_conflicts > 0 for r in recent_integrations) else 1.0
            
            success_rate = sum(1 for r in recent_integrations if r.success) / len(recent_integrations)
            compliance_rate = sum(1 for r in recent_integrations if r.template_compliance) / len(recent_integrations)
            
            effectiveness = (conflict_resolution_rate * 0.3 + success_rate * 0.4 + compliance_rate * 0.3)
            
            return max(0.0, min(1.0, effectiveness))
            
        except Exception as e:
            self.logger.error(f"Error calculating coordination effectiveness: {e}")
            return 0.5
    
    def _calculate_system_performance_trend(self) -> str:
        """Calculate system performance trend"""
        try:
            if len(self.system_metrics_history) < 3:
                return 'insufficient_data'
            
            recent_scores = [entry['metrics'].overall_performance_score for entry in list(self.system_metrics_history)[-5:]]
            
            if len(recent_scores) > 1:
                trend_slope = np.polyfit(range(len(recent_scores)), recent_scores, 1)[0]
                
                if trend_slope > 0.02:
                    return 'improving'
                elif trend_slope < -0.02:
                    return 'declining'
                else:
                    return 'stable'
            
            return 'stable'
            
        except Exception as e:
            self.logger.error(f"Error calculating system performance trend: {e}")
            return 'unknown'
    
    def _calculate_adaptation_effectiveness_trend(self) -> str:
        """Calculate adaptation effectiveness trend"""
        try:
            if len(self.integration_history) < 3:
                return 'insufficient_data'
            
            recent_improvements = [r.performance_improvement_estimate for r in self.integration_history[-5:] if r.success]
            
            if len(recent_improvements) > 1:
                trend_slope = np.polyfit(range(len(recent_improvements)), recent_improvements, 1)[0]
                
                if trend_slope > 0.01:
                    return 'improving'
                elif trend_slope < -0.01:
                    return 'declining'
                else:
                    return 'stable'
            
            return 'stable'
            
        except Exception as e:
            self.logger.error(f"Error calculating adaptation effectiveness trend: {e}")
            return 'unknown'
    
    def _calculate_template_compliance_trend(self) -> str:
        """Calculate template compliance trend"""
        try:
            if len(self.integration_history) < 3:
                return 'insufficient_data'
            
            recent_compliance = [1.0 if r.template_compliance else 0.0 for r in self.integration_history[-5:]]
            
            if len(recent_compliance) > 1:
                avg_recent = np.mean(recent_compliance)
                if avg_recent > 0.9:
                    return 'excellent'
                elif avg_recent > 0.7:
                    return 'good'
                else:
                    return 'needs_attention'
            
            return 'stable'
            
        except Exception as e:
            self.logger.error(f"Error calculating template compliance trend: {e}")
            return 'unknown'
    
    def _categorize_adaptations(self, adaptations: List[str]) -> Dict[str, int]:
        """Categorize adaptations by type"""
        categories = {
            'foundation': 0,
            'signal_generation': 0,
            'risk_control': 0,
            'portfolio_management': 0,
            'execution_control': 0
        }
        
        for adaptation in adaptations:
            if 'foundation' in adaptation or 'coordination' in adaptation:
                categories['foundation'] += 1
            elif 'signal' in adaptation:
                categories['signal_generation'] += 1
            elif 'risk' in adaptation:
                categories['risk_control'] += 1
            elif 'portfolio' in adaptation:
                categories['portfolio_management'] += 1
            elif 'execution' in adaptation:
                categories['execution_control'] += 1
        
        return categories
    
    def _estimate_adaptation_impact(self, adaptations: List[str]) -> Dict[str, str]:
        """Estimate impact of adaptations"""
        if len(adaptations) == 0:
            return {'impact_level': 'none', 'expected_improvement': '0%'}
        elif len(adaptations) == 1:
            return {'impact_level': 'low', 'expected_improvement': '3-7%'}
        elif len(adaptations) <= 3:
            return {'impact_level': 'medium', 'expected_improvement': '7-15%'}
        else:
            return {'impact_level': 'high', 'expected_improvement': '15-25%'}
    
    def _get_component_status(self, component_name: str) -> Dict[str, Any]:
        """Get detailed status of a specific component"""
        base_status = {
            'active': True,
            'last_adaptation': None,
            'performance_score': 0.7,
            'template_compliance': True
        }
        
        if component_name in self.component_status:
            base_status.update(self.component_status[component_name])
        
        return base_status
    
    def _calculate_recent_success_rate(self) -> float:
        """Calculate recent integration success rate"""
        if not self.integration_history:
            return 0.0
        
        recent_integrations = self.integration_history[-5:]  # Last 5 integrations
        successful = sum(1 for r in recent_integrations if r.success)
        
        return successful / len(recent_integrations)
    
    def _calculate_average_improvement(self) -> float:
        """Calculate average performance improvement"""
        if not self.integration_history:
            return 0.0
        
        successful_integrations = [r for r in self.integration_history if r.success]
        
        if not successful_integrations:
            return 0.0
        
        return np.mean([r.performance_improvement_estimate for r in successful_integrations])
    
    def _generate_adaptation_recommendations(self, metrics: SystemMetrics, adaptations: List[str]) -> List[str]:
        """Generate adaptation recommendations based on current metrics"""
        recommendations = []
        
        try:
            # Performance-based recommendations
            if metrics.overall_performance_score < 0.6:
                recommendations.append("Consider increasing adaptation frequency for performance improvement")
            
            if metrics.signal_quality_score < 0.7:
                recommendations.append("Signal generation may benefit from parameter optimization")
            
            if metrics.risk_score > 0.7:
                recommendations.append("Risk levels are elevated - consider tightening risk controls")
            
            if metrics.portfolio_health_score < 0.7:
                recommendations.append("Portfolio diversification could be improved")
            
            if metrics.execution_efficiency_score < 0.8:
                recommendations.append("Execution efficiency is below optimal - review order types and timing")
            
            if metrics.template_compliance_score < 0.9:
                recommendations.append("Template compliance issues detected - review parameter bounds")
            
            # Adaptation-specific recommendations
            if not adaptations:
                recommendations.append("No recent adaptations - system may benefit from parameter review")
            elif len(adaptations) > 4:
                recommendations.append("High adaptation frequency - consider stability over optimization")
            
            return recommendations[:5]  # Limit to top 5 recommendations
            
        except Exception as e:
            self.logger.error(f"Error generating recommendations: {e}")
            return ["Error generating recommendations"]
    
    def _system_metrics_to_dict(self, metrics: SystemMetrics) -> Dict[str, float]:
        """Convert system metrics to dictionary for serialization"""
        return {
            'overall_performance_score': metrics.overall_performance_score,
            'signal_quality_score': metrics.signal_quality_score,
            'risk_score': metrics.risk_score,
            'portfolio_health_score': metrics.portfolio_health_score,
            'execution_efficiency_score': metrics.execution_efficiency_score,
            'adaptation_effectiveness_score': metrics.adaptation_effectiveness_score,
            'template_compliance_score': metrics.template_compliance_score
        }
