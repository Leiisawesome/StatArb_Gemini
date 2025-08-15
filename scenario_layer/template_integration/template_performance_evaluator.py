"""
Template Performance Evaluator
==============================

Comprehensive performance evaluation system for template-based strategies
with advanced analytics, attribution analysis, and benchmarking capabilities.

Author: Pro Quant Desk Trader
"""

import logging
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta
from enum import Enum
import json
from collections import defaultdict

from strategy_templates.base import TemplateRegistry, BaseTemplate, TemplateCategory
from .template_backtesting_engine import TemplateBacktestResult
from .template_scenario_manager import ScenarioResult
from .category_aware_simulator import CategoryPerformanceMetrics

logger = logging.getLogger(__name__)

class EvaluationMetric(Enum):
    """Types of performance evaluation metrics"""
    RISK_ADJUSTED_RETURN = "risk_adjusted_return"
    CONSISTENCY = "consistency"
    DRAWDOWN_CONTROL = "drawdown_control"
    TAIL_RISK = "tail_risk"
    DIVERSIFICATION = "diversification"
    FACTOR_EXPOSURE = "factor_exposure"
    IMPLEMENTATION_QUALITY = "implementation_quality"

class BenchmarkType(Enum):
    """Types of benchmarks for comparison"""
    CATEGORY_AVERAGE = "category_average"
    MARKET_INDEX = "market_index"
    RISK_FREE_RATE = "risk_free_rate"
    CUSTOM_BENCHMARK = "custom_benchmark"
    PARENT_TEMPLATE = "parent_template"

@dataclass
class PerformanceScore:
    """Individual performance score for a metric"""
    metric: EvaluationMetric
    score: float  # 0-100 scale
    percentile: float  # Percentile within category
    grade: str  # A, B, C, D, F
    details: Dict[str, Any] = field(default_factory=dict)
    
    def is_passing(self) -> bool:
        """Check if score meets minimum threshold"""
        return self.score >= 60.0

@dataclass
class TemplateEvaluation:
    """Comprehensive evaluation of a template's performance"""
    template_id: str
    template_category: TemplateCategory
    evaluation_date: datetime
    
    # Overall scores
    overall_score: float
    overall_grade: str
    overall_percentile: float
    
    # Individual metric scores
    metric_scores: Dict[EvaluationMetric, PerformanceScore]
    
    # Benchmark comparisons
    benchmark_comparisons: Dict[BenchmarkType, Dict[str, float]]
    
    # Performance attribution
    performance_attribution: Dict[str, Any]
    
    # Risk analysis
    risk_analysis: Dict[str, Any]
    
    # Recommendations
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]
    
    def get_top_metrics(self, n: int = 3) -> List[Tuple[EvaluationMetric, float]]:
        """Get top performing metrics"""
        metric_scores = [(metric, score.score) for metric, score in self.metric_scores.items()]
        metric_scores.sort(key=lambda x: x[1], reverse=True)
        return metric_scores[:n]
    
    def get_bottom_metrics(self, n: int = 3) -> List[Tuple[EvaluationMetric, float]]:
        """Get bottom performing metrics"""
        metric_scores = [(metric, score.score) for metric, score in self.metric_scores.items()]
        metric_scores.sort(key=lambda x: x[1])
        return metric_scores[:n]

@dataclass
class EvaluationConfig:
    """Configuration for performance evaluation"""
    # Evaluation scope
    include_backtesting: bool = True
    include_scenario_testing: bool = True
    include_category_comparison: bool = True
    include_inheritance_analysis: bool = True
    
    # Benchmark settings
    benchmark_types: List[BenchmarkType] = field(default_factory=lambda: [
        BenchmarkType.CATEGORY_AVERAGE, BenchmarkType.PARENT_TEMPLATE
    ])
    custom_benchmarks: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Evaluation parameters
    evaluation_period_days: int = 252  # One year
    confidence_levels: List[float] = field(default_factory=lambda: [0.95, 0.99])
    risk_free_rate: float = 0.02  # 2% annual
    
    # Weightings for overall score
    metric_weights: Dict[EvaluationMetric, float] = field(default_factory=lambda: {
        EvaluationMetric.RISK_ADJUSTED_RETURN: 0.25,
        EvaluationMetric.CONSISTENCY: 0.20,
        EvaluationMetric.DRAWDOWN_CONTROL: 0.20,
        EvaluationMetric.TAIL_RISK: 0.15,
        EvaluationMetric.DIVERSIFICATION: 0.10,
        EvaluationMetric.IMPLEMENTATION_QUALITY: 0.10
    })

class TemplatePerformanceEvaluator:
    """
    Advanced performance evaluation system providing comprehensive analysis
    of template-based strategies with benchmarking and attribution.
    """
    
    def __init__(self, template_registry: TemplateRegistry):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.template_registry = template_registry
        
        # Evaluation results storage
        self.evaluations: Dict[str, TemplateEvaluation] = {}
        self.category_benchmarks: Dict[TemplateCategory, Dict[str, float]] = {}
        
        # Performance tracking
        self.evaluation_history: List[Dict[str, Any]] = []
        
        # Initialize category benchmarks
        self._initialize_category_benchmarks()
        
        self.logger.info("TemplatePerformanceEvaluator initialized")
    
    def _initialize_category_benchmarks(self):
        """Initialize category-specific performance benchmarks"""
        
        self.category_benchmarks = {
            TemplateCategory.BASE: {
                'expected_sharpe': 0.8,
                'expected_return': 0.08,
                'max_drawdown': 0.15,
                'consistency_threshold': 0.7,
                'tail_risk_threshold': 0.05
            },
            TemplateCategory.SPECIFIC: {
                'expected_sharpe': 1.0,
                'expected_return': 0.10,
                'max_drawdown': 0.20,
                'consistency_threshold': 0.6,
                'tail_risk_threshold': 0.06
            },
            TemplateCategory.COMPOSITE: {
                'expected_sharpe': 1.2,
                'expected_return': 0.12,
                'max_drawdown': 0.12,
                'consistency_threshold': 0.8,
                'tail_risk_threshold': 0.04
            }
        }
    
    async def evaluate_template_performance(self, template_id: str,
                                          backtest_results: Optional[List[TemplateBacktestResult]] = None,
                                          scenario_results: Optional[List[ScenarioResult]] = None,
                                          config: Optional[EvaluationConfig] = None) -> TemplateEvaluation:
        """
        Perform comprehensive performance evaluation for a template
        """
        try:
            if config is None:
                config = EvaluationConfig()
            
            template = self.template_registry.get_template(template_id)
            if not template:
                raise ValueError(f"Template {template_id} not found")
            
            self.logger.info(f"Evaluating performance for template {template_id}")
            
            # Calculate individual metric scores
            metric_scores = {}
            
            if config.include_backtesting and backtest_results:
                metric_scores.update(await self._evaluate_backtesting_metrics(
                    template, backtest_results, config
                ))
            
            if config.include_scenario_testing and scenario_results:
                metric_scores.update(await self._evaluate_scenario_metrics(
                    template, scenario_results, config
                ))
            
            # Add category-specific evaluations
            if config.include_category_comparison:
                category_metrics = await self._evaluate_category_performance(template, config)
                metric_scores.update(category_metrics)
            
            # Add inheritance analysis
            if config.include_inheritance_analysis and template.metadata.parent_templates:
                inheritance_metrics = await self._evaluate_inheritance_performance(template, config)
                metric_scores.update(inheritance_metrics)
            
            # Calculate overall score
            overall_score = self._calculate_overall_score(metric_scores, config.metric_weights)
            overall_grade = self._score_to_grade(overall_score)
            overall_percentile = await self._calculate_category_percentile(
                template, overall_score
            )
            
            # Generate benchmark comparisons
            benchmark_comparisons = await self._perform_benchmark_comparisons(
                template, backtest_results, config
            )
            
            # Perform attribution analysis
            performance_attribution = await self._perform_attribution_analysis(
                template, backtest_results, scenario_results
            )
            
            # Analyze risk characteristics
            risk_analysis = await self._perform_risk_analysis(
                template, backtest_results, scenario_results
            )
            
            # Generate insights and recommendations
            strengths, weaknesses, recommendations = await self._generate_insights(
                template, metric_scores, benchmark_comparisons
            )
            
            # Create evaluation result
            evaluation = TemplateEvaluation(
                template_id=template_id,
                template_category=template.metadata.category,
                evaluation_date=datetime.now(),
                overall_score=overall_score,
                overall_grade=overall_grade,
                overall_percentile=overall_percentile,
                metric_scores=metric_scores,
                benchmark_comparisons=benchmark_comparisons,
                performance_attribution=performance_attribution,
                risk_analysis=risk_analysis,
                strengths=strengths,
                weaknesses=weaknesses,
                recommendations=recommendations
            )
            
            # Store evaluation
            self.evaluations[template_id] = evaluation
            
            # Track evaluation history
            self.evaluation_history.append({
                'template_id': template_id,
                'evaluation_date': datetime.now(),
                'overall_score': overall_score,
                'category': template.metadata.category.value
            })
            
            self.logger.info(f"Evaluation completed for {template_id}: {overall_grade} ({overall_score:.1f})")
            return evaluation
            
        except Exception as e:
            self.logger.error(f"Template evaluation failed: {e}")
            raise
    
    async def _evaluate_backtesting_metrics(self, template: BaseTemplate,
                                          backtest_results: List[TemplateBacktestResult],
                                          config: EvaluationConfig) -> Dict[EvaluationMetric, PerformanceScore]:
        """Evaluate metrics from backtesting results"""
        
        if not backtest_results:
            return {}
        
        # Aggregate backtest results
        total_returns = [r.total_return for r in backtest_results]
        sharpe_ratios = [r.sharpe_ratio for r in backtest_results]
        max_drawdowns = [r.max_drawdown for r in backtest_results]
        volatilities = [r.volatility for r in backtest_results]
        
        metric_scores = {}
        
        # Risk-Adjusted Return Score
        avg_sharpe = np.mean(sharpe_ratios)
        category_benchmark = self.category_benchmarks[template.metadata.category]
        expected_sharpe = category_benchmark['expected_sharpe']
        
        rar_score = min(100.0, (avg_sharpe / expected_sharpe) * 80.0)
        metric_scores[EvaluationMetric.RISK_ADJUSTED_RETURN] = PerformanceScore(
            metric=EvaluationMetric.RISK_ADJUSTED_RETURN,
            score=rar_score,
            percentile=await self._calculate_metric_percentile(template, 'sharpe_ratio', avg_sharpe),
            grade=self._score_to_grade(rar_score),
            details={
                'avg_sharpe_ratio': avg_sharpe,
                'expected_sharpe': expected_sharpe,
                'sharpe_ratio_range': [min(sharpe_ratios), max(sharpe_ratios)]
            }
        )
        
        # Consistency Score
        sharpe_std = np.std(sharpe_ratios) if len(sharpe_ratios) > 1 else 0.0
        consistency_score = max(0.0, 100.0 - (sharpe_std / max(avg_sharpe, 0.1)) * 100.0)
        
        metric_scores[EvaluationMetric.CONSISTENCY] = PerformanceScore(
            metric=EvaluationMetric.CONSISTENCY,
            score=consistency_score,
            percentile=await self._calculate_metric_percentile(template, 'consistency', consistency_score),
            grade=self._score_to_grade(consistency_score),
            details={
                'performance_volatility': sharpe_std,
                'consistency_ratio': 1.0 / max(sharpe_std, 0.01)
            }
        )
        
        # Drawdown Control Score
        avg_max_drawdown = np.mean(max_drawdowns)
        max_dd_threshold = category_benchmark['max_drawdown']
        
        dd_score = max(0.0, 100.0 * (1.0 - avg_max_drawdown / max_dd_threshold))
        metric_scores[EvaluationMetric.DRAWDOWN_CONTROL] = PerformanceScore(
            metric=EvaluationMetric.DRAWDOWN_CONTROL,
            score=dd_score,
            percentile=await self._calculate_metric_percentile(template, 'max_drawdown', avg_max_drawdown),
            grade=self._score_to_grade(dd_score),
            details={
                'avg_max_drawdown': avg_max_drawdown,
                'worst_drawdown': max(max_drawdowns),
                'drawdown_threshold': max_dd_threshold
            }
        )
        
        return metric_scores
    
    async def _evaluate_scenario_metrics(self, template: BaseTemplate,
                                       scenario_results: List[ScenarioResult],
                                       config: EvaluationConfig) -> Dict[EvaluationMetric, PerformanceScore]:
        """Evaluate metrics from scenario testing results"""
        
        if not scenario_results:
            return {}
        
        metric_scores = {}
        
        # Tail Risk Score
        var_95_values = [r.var_95 for r in scenario_results]
        cvar_95_values = [r.cvar_95 for r in scenario_results]
        
        avg_var_95 = np.mean(var_95_values)
        avg_cvar_95 = np.mean(cvar_95_values)
        
        category_benchmark = self.category_benchmarks[template.metadata.category]
        tail_risk_threshold = category_benchmark['tail_risk_threshold']
        
        tail_risk_score = max(0.0, 100.0 * (1.0 - avg_cvar_95 / tail_risk_threshold))
        
        metric_scores[EvaluationMetric.TAIL_RISK] = PerformanceScore(
            metric=EvaluationMetric.TAIL_RISK,
            score=tail_risk_score,
            percentile=await self._calculate_metric_percentile(template, 'tail_risk', tail_risk_score),
            grade=self._score_to_grade(tail_risk_score),
            details={
                'avg_var_95': avg_var_95,
                'avg_cvar_95': avg_cvar_95,
                'tail_risk_threshold': tail_risk_threshold,
                'worst_scenario_loss': max([r.stress_loss for r in scenario_results])
            }
        )
        
        return metric_scores
    
    async def _evaluate_category_performance(self, template: BaseTemplate,
                                           config: EvaluationConfig) -> Dict[EvaluationMetric, PerformanceScore]:
        """Evaluate performance relative to category"""
        
        # This would typically compare against other templates in the same category
        # For now, we'll create a placeholder implementation
        
        diversification_score = 75.0  # Placeholder score
        
        return {
            EvaluationMetric.DIVERSIFICATION: PerformanceScore(
                metric=EvaluationMetric.DIVERSIFICATION,
                score=diversification_score,
                percentile=50.0,  # Placeholder
                grade=self._score_to_grade(diversification_score),
                details={
                    'category': template.metadata.category.value,
                    'diversification_analysis': 'placeholder'
                }
            )
        }
    
    async def _evaluate_inheritance_performance(self, template: BaseTemplate,
                                              config: EvaluationConfig) -> Dict[EvaluationMetric, PerformanceScore]:
        """Evaluate performance impact of template inheritance"""
        
        # This would analyze how well the template performs compared to its parents
        # For now, we'll create a placeholder implementation
        
        implementation_score = 80.0  # Placeholder score
        
        return {
            EvaluationMetric.IMPLEMENTATION_QUALITY: PerformanceScore(
                metric=EvaluationMetric.IMPLEMENTATION_QUALITY,
                score=implementation_score,
                percentile=60.0,  # Placeholder
                grade=self._score_to_grade(implementation_score),
                details={
                    'parent_templates': template.metadata.parent_templates,
                    'inheritance_impact': 'positive'  # Placeholder
                }
            )
        }
    
    def _calculate_overall_score(self, metric_scores: Dict[EvaluationMetric, PerformanceScore],
                               weights: Dict[EvaluationMetric, float]) -> float:
        """Calculate weighted overall score"""
        
        if not metric_scores:
            return 0.0
        
        total_weighted_score = 0.0
        total_weight = 0.0
        
        for metric, score in metric_scores.items():
            weight = weights.get(metric, 0.1)  # Default weight
            total_weighted_score += score.score * weight
            total_weight += weight
        
        return total_weighted_score / max(total_weight, 0.001)
    
    def _score_to_grade(self, score: float) -> str:
        """Convert numeric score to letter grade"""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
    
    async def _calculate_category_percentile(self, template: BaseTemplate, score: float) -> float:
        """Calculate percentile within category"""
        
        # This would compare against all templates in the same category
        # For now, return a placeholder percentile
        
        return 50.0 + np.random.uniform(-20, 20)  # Placeholder with some variation
    
    async def _calculate_metric_percentile(self, template: BaseTemplate,
                                         metric_name: str, value: float) -> float:
        """Calculate percentile for specific metric within category"""
        
        # This would compare the metric value against the distribution in the category
        # For now, return a placeholder percentile
        
        return 50.0 + np.random.uniform(-25, 25)  # Placeholder with variation
    
    async def _perform_benchmark_comparisons(self, template: BaseTemplate,
                                           backtest_results: Optional[List[TemplateBacktestResult]],
                                           config: EvaluationConfig) -> Dict[BenchmarkType, Dict[str, float]]:
        """Perform comprehensive benchmark comparisons"""
        
        comparisons = {}
        
        if not backtest_results:
            return comparisons
        
        avg_return = np.mean([r.total_return for r in backtest_results])
        avg_sharpe = np.mean([r.sharpe_ratio for r in backtest_results])
        avg_volatility = np.mean([r.volatility for r in backtest_results])
        
        # Category average comparison
        category_benchmark = self.category_benchmarks[template.metadata.category]
        
        comparisons[BenchmarkType.CATEGORY_AVERAGE] = {
            'return_ratio': avg_return / category_benchmark['expected_return'],
            'sharpe_ratio': avg_sharpe / category_benchmark['expected_sharpe'],
            'excess_return': avg_return - category_benchmark['expected_return']
        }
        
        # Risk-free rate comparison
        comparisons[BenchmarkType.RISK_FREE_RATE] = {
            'excess_return': avg_return - config.risk_free_rate,
            'sharpe_ratio': (avg_return - config.risk_free_rate) / max(avg_volatility, 0.001),
            'information_ratio': avg_sharpe  # Simplified
        }
        
        # Parent template comparison (if applicable)
        if template.metadata.parent_templates:
            # This would compare with actual parent template performance
            # For now, create placeholder comparison
            comparisons[BenchmarkType.PARENT_TEMPLATE] = {
                'performance_improvement': 0.15,  # 15% improvement placeholder
                'risk_reduction': 0.05,  # 5% risk reduction placeholder
                'inheritance_value_add': 0.10  # Value add from inheritance
            }
        
        return comparisons
    
    async def _perform_attribution_analysis(self, template: BaseTemplate,
                                          backtest_results: Optional[List[TemplateBacktestResult]],
                                          scenario_results: Optional[List[ScenarioResult]]) -> Dict[str, Any]:
        """Perform performance attribution analysis"""
        
        attribution = {
            'template_factors': {},
            'market_factors': {},
            'implementation_factors': {},
            'risk_factors': {}
        }
        
        # Template-specific attribution
        attribution['template_factors'] = {
            'category_contribution': template.metadata.category.value,
            'inheritance_contribution': len(template.metadata.parent_templates) * 0.02,  # Placeholder
            'parameter_optimization': 0.05  # Placeholder
        }
        
        # Market factor attribution
        if backtest_results:
            avg_return = np.mean([r.total_return for r in backtest_results])
            attribution['market_factors'] = {
                'market_beta': 0.8,  # Placeholder beta
                'alpha_generation': avg_return - 0.08,  # Excess over market
                'timing_contribution': 0.02  # Placeholder timing value
            }
        
        # Implementation quality attribution
        attribution['implementation_factors'] = {
            'execution_efficiency': 0.98,  # 98% efficiency placeholder
            'cost_impact': -0.005,  # 50 bps cost drag
            'slippage_impact': -0.003  # 30 bps slippage
        }
        
        return attribution
    
    async def _perform_risk_analysis(self, template: BaseTemplate,
                                   backtest_results: Optional[List[TemplateBacktestResult]],
                                   scenario_results: Optional[List[ScenarioResult]]) -> Dict[str, Any]:
        """Perform comprehensive risk analysis"""
        
        risk_analysis = {
            'risk_metrics': {},
            'risk_decomposition': {},
            'stress_test_results': {},
            'risk_attribution': {}
        }
        
        if backtest_results:
            max_drawdowns = [r.max_drawdown for r in backtest_results]
            volatilities = [r.volatility for r in backtest_results]
            
            risk_analysis['risk_metrics'] = {
                'avg_volatility': np.mean(volatilities),
                'avg_max_drawdown': np.mean(max_drawdowns),
                'worst_drawdown': max(max_drawdowns),
                'volatility_stability': 1.0 / max(np.std(volatilities), 0.001)
            }
        
        if scenario_results:
            tail_risks = [r.cvar_95 for r in scenario_results]
            stress_losses = [r.stress_loss for r in scenario_results]
            
            risk_analysis['stress_test_results'] = {
                'avg_tail_risk': np.mean(tail_risks),
                'worst_stress_loss': max(stress_losses),
                'stress_resilience': 1.0 - np.mean(stress_losses)
            }
        
        return risk_analysis
    
    async def _generate_insights(self, template: BaseTemplate,
                               metric_scores: Dict[EvaluationMetric, PerformanceScore],
                               benchmark_comparisons: Dict[BenchmarkType, Dict[str, float]]) -> Tuple[List[str], List[str], List[str]]:
        """Generate insights, strengths, weaknesses, and recommendations"""
        
        strengths = []
        weaknesses = []
        recommendations = []
        
        # Analyze metric scores for strengths and weaknesses
        for metric, score in metric_scores.items():
            if score.score >= 80:
                strengths.append(f"Strong {metric.value.replace('_', ' ')}: {score.grade} grade")
            elif score.score < 60:
                weaknesses.append(f"Weak {metric.value.replace('_', ' ')}: {score.grade} grade")
                
                # Generate specific recommendations
                if metric == EvaluationMetric.RISK_ADJUSTED_RETURN:
                    recommendations.append("Consider improving signal quality or risk management")
                elif metric == EvaluationMetric.DRAWDOWN_CONTROL:
                    recommendations.append("Implement stricter position sizing and stop-loss rules")
                elif metric == EvaluationMetric.CONSISTENCY:
                    recommendations.append("Review parameter stability and market regime adaptation")
        
        # Analyze benchmark comparisons
        category_comparison = benchmark_comparisons.get(BenchmarkType.CATEGORY_AVERAGE, {})
        if category_comparison.get('return_ratio', 1.0) > 1.1:
            strengths.append("Outperforming category average by significant margin")
        elif category_comparison.get('return_ratio', 1.0) < 0.9:
            weaknesses.append("Underperforming category average")
            recommendations.append("Analyze top-performing templates in category for improvement ideas")
        
        # Category-specific recommendations
        if template.metadata.category == TemplateCategory.BASE:
            recommendations.append("Consider specialization to improve performance")
        elif template.metadata.category == TemplateCategory.COMPOSITE:
            recommendations.append("Review component templates for optimization opportunities")
        
        return strengths, weaknesses, recommendations
    
    def compare_templates(self, template_ids: List[str]) -> Dict[str, Any]:
        """Compare performance across multiple templates"""
        
        if not template_ids:
            return {}
        
        evaluations = [self.evaluations[tid] for tid in template_ids if tid in self.evaluations]
        
        if not evaluations:
            return {}
        
        comparison = {
            'template_rankings': [],
            'metric_comparison': {},
            'category_distribution': {},
            'performance_analysis': {}
        }
        
        # Rank templates by overall score
        template_rankings = [(e.template_id, e.overall_score, e.overall_grade) for e in evaluations]
        template_rankings.sort(key=lambda x: x[1], reverse=True)
        comparison['template_rankings'] = template_rankings
        
        # Compare metrics across templates
        for metric in EvaluationMetric:
            metric_scores = []
            for evaluation in evaluations:
                if metric in evaluation.metric_scores:
                    metric_scores.append((evaluation.template_id, evaluation.metric_scores[metric].score))
            
            if metric_scores:
                metric_scores.sort(key=lambda x: x[1], reverse=True)
                comparison['metric_comparison'][metric.value] = metric_scores
        
        # Category distribution
        category_counts = defaultdict(int)
        for evaluation in evaluations:
            category_counts[evaluation.template_category.value] += 1
        comparison['category_distribution'] = dict(category_counts)
        
        # Performance analysis
        scores = [e.overall_score for e in evaluations]
        comparison['performance_analysis'] = {
            'avg_score': np.mean(scores),
            'score_std': np.std(scores),
            'best_score': max(scores),
            'worst_score': min(scores),
            'above_threshold_count': sum(1 for s in scores if s >= 70)
        }
        
        return comparison
    
    def get_evaluation_summary(self) -> Dict[str, Any]:
        """Get summary of all evaluations"""
        
        if not self.evaluations:
            return {}
        
        evaluations = list(self.evaluations.values())
        
        return {
            'total_evaluations': len(evaluations),
            'avg_overall_score': np.mean([e.overall_score for e in evaluations]),
            'grade_distribution': {
                grade: sum(1 for e in evaluations if e.overall_grade == grade)
                for grade in ['A', 'B', 'C', 'D', 'F']
            },
            'category_performance': {
                category.value: {
                    'count': sum(1 for e in evaluations if e.template_category == category),
                    'avg_score': np.mean([e.overall_score for e in evaluations if e.template_category == category])
                }
                for category in TemplateCategory
                if any(e.template_category == category for e in evaluations)
            },
            'recent_evaluations': len([e for e in evaluations 
                                     if (datetime.now() - e.evaluation_date).days <= 7])
        }
