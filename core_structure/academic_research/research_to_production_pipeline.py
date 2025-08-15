"""
Research-to-Production Pipeline - Academic Strategy Deployment
==============================================================

Pipeline for converting academic research strategies into production-ready
trading systems with proper constraints, enhancements, and validation.

Author: Pro Quant Desk Trader
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable, Tuple
from datetime import datetime
import copy

from .academic_strategy_registry import AcademicTemplate, AcademicStrategyRegistry
from .academic_strategy_validator import AcademicStrategyValidator, ValidationResult
from strategy_templates.base import TemplateRegistry, TemplateCategory


@dataclass
class ProductionConstraints:
    """Production deployment constraints"""
    # Risk constraints
    max_position_size: float = 0.25
    max_daily_loss: float = 0.05
    max_portfolio_volatility: float = 0.20
    max_leverage: float = 3.0
    
    # Execution constraints
    commission_rate: float = 0.001
    max_slippage: float = 0.002
    min_liquidity: float = 1000000
    max_order_size: float = 0.01  # as fraction of daily volume
    
    # Performance constraints
    min_sharpe_ratio: float = 0.5
    max_drawdown: float = 0.20
    min_win_rate: float = 0.45
    
    # Trading constraints
    min_holding_period: int = 1  # days
    max_holding_period: int = 365  # days
    min_trade_frequency: int = 1  # trades per month
    max_trade_frequency: int = 1000  # trades per month
    
    # Market constraints
    allowed_markets: List[str] = field(default_factory=lambda: ['US_EQUITY', 'US_FUTURES'])
    excluded_sectors: List[str] = field(default_factory=list)
    min_market_cap: float = 1000000000  # $1B minimum
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'risk_constraints': {
                'max_position_size': self.max_position_size,
                'max_daily_loss': self.max_daily_loss,
                'max_portfolio_volatility': self.max_portfolio_volatility,
                'max_leverage': self.max_leverage
            },
            'execution_constraints': {
                'commission_rate': self.commission_rate,
                'max_slippage': self.max_slippage,
                'min_liquidity': self.min_liquidity,
                'max_order_size': self.max_order_size
            },
            'performance_constraints': {
                'min_sharpe_ratio': self.min_sharpe_ratio,
                'max_drawdown': self.max_drawdown,
                'min_win_rate': self.min_win_rate
            },
            'trading_constraints': {
                'min_holding_period': self.min_holding_period,
                'max_holding_period': self.max_holding_period,
                'min_trade_frequency': self.min_trade_frequency,
                'max_trade_frequency': self.max_trade_frequency
            },
            'market_constraints': {
                'allowed_markets': self.allowed_markets,
                'excluded_sectors': self.excluded_sectors,
                'min_market_cap': self.min_market_cap
            }
        }


@dataclass
class ProductionEnhancement:
    """Production enhancement applied to academic strategy"""
    enhancement_type: str
    description: str
    parameters_added: Dict[str, Any]
    rationale: str
    impact_estimate: Optional[str] = None


@dataclass
class ProductionEvaluation:
    """Complete evaluation of academic strategy for production"""
    academic_template: AcademicTemplate
    production_template: Dict[str, Any]
    validation_result: ValidationResult
    applied_constraints: ProductionConstraints
    enhancements: List[ProductionEnhancement]
    
    # Assessment scores
    deployment_readiness_score: float = 0.0
    risk_assessment_score: float = 0.0
    expected_performance_impact: float = 0.0
    
    # Deployment recommendations
    deployment_recommendations: List[str] = field(default_factory=list)
    monitoring_requirements: List[str] = field(default_factory=list)
    rollout_strategy: Optional[str] = None
    
    # Production metadata
    evaluation_date: str = field(default_factory=lambda: datetime.now().isoformat())
    evaluator_id: Optional[str] = None
    approval_status: str = "pending"


class ResearchToProductionPipeline:
    """
    Comprehensive pipeline for converting academic research to production strategies
    """
    
    def __init__(self, 
                 academic_registry: AcademicStrategyRegistry,
                 template_registry: TemplateRegistry):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.academic_registry = academic_registry
        self.template_registry = template_registry
        self.validator = AcademicStrategyValidator()
        
        # Pipeline components
        self.enhancer = None  # Will be set when needed
        self.constraint_applicator = ProductionConstraintApplicator()
        
        # Default production constraints
        self.default_constraints = ProductionConstraints()
        
        # Pipeline history
        self.evaluation_history: List[ProductionEvaluation] = []
        
        self.logger.info("Research-to-Production Pipeline initialized")
    
    def evaluate_academic_strategy(self, 
                                 academic_template_id: str,
                                 production_constraints: Optional[ProductionConstraints] = None,
                                 custom_enhancements: Optional[List[str]] = None) -> ProductionEvaluation:
        """
        Complete evaluation of academic strategy for production deployment
        """
        try:
            self.logger.info(f"Evaluating academic strategy for production: {academic_template_id}")
            
            # Get academic template
            academic_template = self.academic_registry.get_academic_strategy(academic_template_id)
            if not academic_template:
                raise ValueError(f"Academic template {academic_template_id} not found")
            
            # Use provided constraints or defaults
            constraints = production_constraints or self.default_constraints
            
            # 1. Initial validation of academic strategy
            self.logger.info("Step 1: Validating academic strategy")
            validation_result = self.validator.validate_academic_strategy(
                academic_template, 
                constraints.to_dict()
            )
            
            # 2. Apply production constraints
            self.logger.info("Step 2: Applying production constraints")
            constrained_template = self.constraint_applicator.apply_constraints(
                academic_template, constraints
            )
            
            # 3. Apply production enhancements
            self.logger.info("Step 3: Applying production enhancements")
            enhanced_template, enhancements = self._apply_production_enhancements(
                constrained_template, custom_enhancements or []
            )
            
            # 4. Final validation of production template
            self.logger.info("Step 4: Final production validation")
            final_validation = self.validator.validate_academic_strategy(
                enhanced_template, constraints.to_dict()
            )
            
            # 5. Calculate assessment scores
            assessment_scores = self._calculate_assessment_scores(
                validation_result, final_validation, enhancements
            )
            
            # 6. Generate deployment recommendations
            recommendations = self._generate_deployment_recommendations(
                academic_template, final_validation, assessment_scores
            )
            
            # Create production evaluation
            evaluation = ProductionEvaluation(
                academic_template=academic_template,
                production_template=enhanced_template.base_template,
                validation_result=final_validation,
                applied_constraints=constraints,
                enhancements=enhancements,
                deployment_readiness_score=assessment_scores['deployment_readiness'],
                risk_assessment_score=assessment_scores['risk_assessment'],
                expected_performance_impact=assessment_scores['performance_impact'],
                deployment_recommendations=recommendations['deployment'],
                monitoring_requirements=recommendations['monitoring'],
                rollout_strategy=recommendations['rollout']
            )
            
            # Store evaluation
            self.evaluation_history.append(evaluation)
            
            self.logger.info(f"Evaluation completed. Deployment readiness: {evaluation.deployment_readiness_score:.2f}")
            
            return evaluation
            
        except Exception as e:
            self.logger.error(f"Production evaluation failed: {e}")
            raise
    
    def _apply_production_enhancements(self, 
                                     template: AcademicTemplate,
                                     custom_enhancements: List[str]) -> Tuple[AcademicTemplate, List[ProductionEnhancement]]:
        """Apply production-specific enhancements"""
        enhanced_template = copy.deepcopy(template)
        enhancements = []
        
        # Standard enhancements
        standard_enhancements = [
            'dynamic_adaptation',
            'regime_detection',
            'transaction_cost_modeling',
            'liquidity_constraints',
            'risk_overlay'
        ]
        
        all_enhancements = list(set(standard_enhancements + custom_enhancements))
        
        for enhancement_type in all_enhancements:
            enhancement = self._apply_single_enhancement(enhanced_template, enhancement_type)
            if enhancement:
                enhancements.append(enhancement)
        
        return enhanced_template, enhancements
    
    def _apply_single_enhancement(self, template: AcademicTemplate, enhancement_type: str) -> Optional[ProductionEnhancement]:
        """Apply single production enhancement"""
        base_params = template.base_template.get('base_parameters', {})
        
        if enhancement_type == 'dynamic_adaptation':
            return self._add_dynamic_adaptation(base_params)
        elif enhancement_type == 'regime_detection':
            return self._add_regime_detection(base_params)
        elif enhancement_type == 'transaction_cost_modeling':
            return self._add_transaction_cost_modeling(base_params)
        elif enhancement_type == 'liquidity_constraints':
            return self._add_liquidity_constraints(base_params)
        elif enhancement_type == 'risk_overlay':
            return self._add_risk_overlay(base_params)
        
        return None
    
    def _add_dynamic_adaptation(self, base_params: Dict[str, Any]) -> ProductionEnhancement:
        """Add dynamic adaptation framework"""
        adaptation_params = {
            'adaptation_enabled': True,
            'adaptation_frequency': 'daily',
            'parameter_bounds': self._extract_parameter_bounds(base_params),
            'adaptation_triggers': {
                'performance_degradation': 0.1,
                'volatility_change': 0.5,
                'regime_change': True
            },
            'adaptation_method': 'bayesian_optimization'
        }
        
        base_params['dynamic_adaptation'] = adaptation_params
        
        return ProductionEnhancement(
            enhancement_type='dynamic_adaptation',
            description='Added dynamic parameter adaptation framework',
            parameters_added=adaptation_params,
            rationale='Enable real-time strategy optimization based on market conditions',
            impact_estimate='Expected 10-20% improvement in risk-adjusted returns'
        )
    
    def _add_regime_detection(self, base_params: Dict[str, Any]) -> ProductionEnhancement:
        """Add market regime detection"""
        regime_params = {
            'enabled': True,
            'detection_method': 'hidden_markov_model',
            'regime_types': ['low_volatility', 'high_volatility', 'trending', 'mean_reverting'],
            'lookback_period': 252,  # 1 year
            'adaptation_rules': {
                'low_volatility': {'position_size_multiplier': 1.2},
                'high_volatility': {'position_size_multiplier': 0.8},
                'trending': {'momentum_weight': 1.5},
                'mean_reverting': {'mean_reversion_weight': 1.5}
            }
        }
        
        base_params['regime_detection'] = regime_params
        
        return ProductionEnhancement(
            enhancement_type='regime_detection',
            description='Added market regime detection and adaptation',
            parameters_added=regime_params,
            rationale='Adapt strategy behavior to different market conditions',
            impact_estimate='Expected 15-25% reduction in drawdowns'
        )
    
    def _add_transaction_cost_modeling(self, base_params: Dict[str, Any]) -> ProductionEnhancement:
        """Add comprehensive transaction cost modeling"""
        cost_params = {
            'enabled': True,
            'commission_model': 'tiered',
            'bid_ask_spread_model': 'market_impact',
            'market_impact_model': 'almgren_chriss',
            'slippage_estimation': 'historical_average',
            'cost_optimization': {
                'enabled': True,
                'method': 'implementation_shortfall',
                'urgency_factor': 0.5
            }
        }
        
        if 'execution' not in base_params:
            base_params['execution'] = {}
        base_params['execution']['transaction_cost_modeling'] = cost_params
        
        return ProductionEnhancement(
            enhancement_type='transaction_cost_modeling',
            description='Added comprehensive transaction cost modeling',
            parameters_added=cost_params,
            rationale='Accurate cost estimation for realistic performance expectations',
            impact_estimate='Typical 50-100 bps annual performance drag'
        )
    
    def _add_liquidity_constraints(self, base_params: Dict[str, Any]) -> ProductionEnhancement:
        """Add liquidity-based position constraints"""
        liquidity_params = {
            'enabled': True,
            'min_daily_volume': 1000000,  # $1M minimum
            'max_volume_participation': 0.05,  # 5% max
            'liquidity_buffer': 0.2,  # 20% buffer
            'illiquidity_penalty': {
                'enabled': True,
                'threshold': 0.1,
                'penalty_factor': 2.0
            }
        }
        
        if 'execution' not in base_params:
            base_params['execution'] = {}
        base_params['execution']['liquidity_constraints'] = liquidity_params
        
        return ProductionEnhancement(
            enhancement_type='liquidity_constraints',
            description='Added liquidity-based position constraints',
            parameters_added=liquidity_params,
            rationale='Ensure positions can be executed without excessive market impact',
            impact_estimate='Reduces available universe by ~20% but improves execution quality'
        )
    
    def _add_risk_overlay(self, base_params: Dict[str, Any]) -> ProductionEnhancement:
        """Add production risk overlay"""
        risk_params = {
            'enabled': True,
            'daily_var_limit': 0.02,  # 2% daily VaR
            'portfolio_correlation_limit': 0.8,
            'sector_concentration_limit': 0.3,
            'emergency_stop_loss': 0.05,  # 5% daily loss
            'risk_attribution': {
                'enabled': True,
                'factors': ['market', 'sector', 'style', 'specific']
            }
        }
        
        if 'risk_management' not in base_params:
            base_params['risk_management'] = {}
        base_params['risk_management']['production_overlay'] = risk_params
        
        return ProductionEnhancement(
            enhancement_type='risk_overlay',
            description='Added production risk management overlay',
            parameters_added=risk_params,
            rationale='Additional risk controls for live trading environment',
            impact_estimate='Reduces tail risk by ~30% with minimal performance impact'
        )
    
    def _extract_parameter_bounds(self, base_params: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Extract parameter bounds for dynamic adaptation"""
        bounds = {}
        
        # Extract signal generation parameters
        signal_params = base_params.get('signal_generation', {})
        if 'indicators' in signal_params:
            for indicator_name, config in signal_params['indicators'].items():
                if 'period' in config:
                    bounds[f'{indicator_name}_period'] = {
                        'min': max(1, int(config['period'] * 0.5)),
                        'max': int(config['period'] * 2.0),
                        'default': config['period']
                    }
                if 'threshold' in config:
                    bounds[f'{indicator_name}_threshold'] = {
                        'min': config['threshold'] * 0.5,
                        'max': config['threshold'] * 2.0,
                        'default': config['threshold']
                    }
        
        return bounds
    
    def _calculate_assessment_scores(self, 
                                   initial_validation: ValidationResult,
                                   final_validation: ValidationResult,
                                   enhancements: List[ProductionEnhancement]) -> Dict[str, float]:
        """Calculate comprehensive assessment scores"""
        
        # Deployment readiness (based on final validation)
        deployment_readiness = final_validation.overall_score
        
        # Risk assessment (combination of validation scores)
        risk_assessment = (
            final_validation.category_scores.get('risk_management', 0.5) * 0.4 +
            final_validation.category_scores.get('production_constraints', 0.5) * 0.3 +
            final_validation.category_scores.get('statistical_significance', 0.5) * 0.3
        )
        
        # Performance impact (estimated from enhancements)
        performance_impact = 0.0
        enhancement_bonus = len(enhancements) * 0.05  # 5% bonus per enhancement
        performance_impact = min(0.3, enhancement_bonus)  # Cap at 30%
        
        return {
            'deployment_readiness': deployment_readiness,
            'risk_assessment': risk_assessment,
            'performance_impact': performance_impact
        }
    
    def _generate_deployment_recommendations(self, 
                                           template: AcademicTemplate,
                                           validation: ValidationResult,
                                           scores: Dict[str, float]) -> Dict[str, Any]:
        """Generate comprehensive deployment recommendations"""
        
        deployment_recs = []
        monitoring_recs = []
        rollout_strategy = "conservative"
        
        # Deployment recommendations based on scores
        if scores['deployment_readiness'] >= 0.8:
            deployment_recs.append("Strategy ready for full production deployment")
            rollout_strategy = "standard"
        elif scores['deployment_readiness'] >= 0.6:
            deployment_recs.append("Strategy suitable for limited production deployment")
            deployment_recs.append("Recommend gradual capital allocation increase")
            rollout_strategy = "gradual"
        else:
            deployment_recs.append("Strategy requires additional development before production")
            deployment_recs.append("Address validation issues before deployment")
            rollout_strategy = "development"
        
        # Risk-based recommendations
        if scores['risk_assessment'] < 0.7:
            deployment_recs.append("Implement additional risk monitoring")
            monitoring_recs.append("Daily risk attribution analysis")
            monitoring_recs.append("Real-time position concentration monitoring")
        
        # Standard monitoring requirements
        monitoring_recs.extend([
            "Daily performance tracking vs academic expectations",
            "Transaction cost analysis",
            "Slippage and execution quality monitoring",
            "Parameter stability monitoring"
        ])
        
        # Research field specific recommendations
        field = template.academic_metadata.research_field
        if field.value == 'momentum':
            monitoring_recs.append("Market regime change detection")
        elif field.value == 'mean_reversion':
            monitoring_recs.append("Correlation structure stability monitoring")
        
        return {
            'deployment': deployment_recs,
            'monitoring': monitoring_recs,
            'rollout': rollout_strategy
        }
    
    def get_pipeline_summary(self) -> Dict[str, Any]:
        """Get comprehensive pipeline summary"""
        return {
            'total_evaluations': len(self.evaluation_history),
            'deployment_ready_count': len([e for e in self.evaluation_history if e.deployment_readiness_score >= 0.6]),
            'average_deployment_score': sum(e.deployment_readiness_score for e in self.evaluation_history) / len(self.evaluation_history) if self.evaluation_history else 0,
            'recent_evaluations': [
                {
                    'template_id': e.academic_template.template_id,
                    'evaluation_date': e.evaluation_date,
                    'deployment_readiness': e.deployment_readiness_score,
                    'approval_status': e.approval_status
                }
                for e in self.evaluation_history[-10:]
            ]
        }


class ProductionConstraintApplicator:
    """Applies production constraints to academic templates"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def apply_constraints(self, 
                         template: AcademicTemplate, 
                         constraints: ProductionConstraints) -> AcademicTemplate:
        """Apply production constraints to template"""
        constrained_template = copy.deepcopy(template)
        base_params = constrained_template.base_template.get('base_parameters', {})
        
        # Apply risk constraints
        self._apply_risk_constraints(base_params, constraints)
        
        # Apply execution constraints
        self._apply_execution_constraints(base_params, constraints)
        
        # Apply trading constraints
        self._apply_trading_constraints(base_params, constraints)
        
        # Apply market constraints
        self._apply_market_constraints(base_params, constraints)
        
        return constrained_template
    
    def _apply_risk_constraints(self, base_params: Dict[str, Any], constraints: ProductionConstraints):
        """Apply risk-related constraints"""
        if 'risk_management' not in base_params:
            base_params['risk_management'] = {}
        
        risk_mgmt = base_params['risk_management']
        
        # Position sizing constraints
        if 'position_sizing' not in risk_mgmt:
            risk_mgmt['position_sizing'] = {}
        
        risk_mgmt['position_sizing']['max_position_size'] = min(
            risk_mgmt['position_sizing'].get('max_position_size', 1.0),
            constraints.max_position_size
        )
        
        # Daily loss limit
        risk_mgmt['max_daily_loss'] = constraints.max_daily_loss
        
        # Portfolio volatility limit
        risk_mgmt['max_portfolio_volatility'] = constraints.max_portfolio_volatility
        
        # Leverage constraint
        risk_mgmt['max_leverage'] = constraints.max_leverage
    
    def _apply_execution_constraints(self, base_params: Dict[str, Any], constraints: ProductionConstraints):
        """Apply execution-related constraints"""
        if 'execution' not in base_params:
            base_params['execution'] = {}
        
        execution = base_params['execution']
        
        # Transaction cost parameters
        execution['commission_rate'] = constraints.commission_rate
        execution['max_slippage'] = constraints.max_slippage
        execution['min_liquidity'] = constraints.min_liquidity
        execution['max_order_size'] = constraints.max_order_size
    
    def _apply_trading_constraints(self, base_params: Dict[str, Any], constraints: ProductionConstraints):
        """Apply trading-related constraints"""
        if 'trading_rules' not in base_params:
            base_params['trading_rules'] = {}
        
        trading = base_params['trading_rules']
        
        # Holding period constraints
        trading['min_holding_period'] = constraints.min_holding_period
        trading['max_holding_period'] = constraints.max_holding_period
        
        # Trading frequency constraints
        trading['min_trade_frequency'] = constraints.min_trade_frequency
        trading['max_trade_frequency'] = constraints.max_trade_frequency
    
    def _apply_market_constraints(self, base_params: Dict[str, Any], constraints: ProductionConstraints):
        """Apply market-related constraints"""
        if 'market_selection' not in base_params:
            base_params['market_selection'] = {}
        
        market = base_params['market_selection']
        
        # Market and sector constraints
        market['allowed_markets'] = constraints.allowed_markets
        market['excluded_sectors'] = constraints.excluded_sectors
        market['min_market_cap'] = constraints.min_market_cap
