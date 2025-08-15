"""
Category-Aware Simulator
=======================

Specialized simulator for category-specific template testing with
category-aware performance analysis and cross-category benchmarking.

Author: Pro Quant Desk Trader
"""

import logging
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta
from enum import Enum
import asyncio
from collections import defaultdict

from strategy_templates.base import TemplateRegistry, BaseTemplate, TemplateCategory
from strategy_layer.template_integration import TemplateStrategyManager
from .template_scenario_manager import TemplateScenarioManager, ScenarioResult

logger = logging.getLogger(__name__)

class SimulationMode(Enum):
    """Category simulation modes"""
    WITHIN_CATEGORY = "within_category"          # Simulate within single category
    CROSS_CATEGORY = "cross_category"            # Compare across categories
    INHERITANCE_CHAIN = "inheritance_chain"      # Simulate inheritance relationships
    CATEGORY_STRESS = "category_stress"          # Category-specific stress testing

@dataclass
class CategorySimulationConfig:
    """Configuration for category-aware simulation"""
    target_categories: List[TemplateCategory]
    simulation_mode: SimulationMode
    
    # Simulation parameters
    simulation_days: int = 252  # One year
    num_monte_carlo_runs: int = 100
    confidence_levels: List[float] = field(default_factory=lambda: [0.95, 0.99])
    
    # Category-specific settings
    category_benchmarks: Dict[TemplateCategory, str] = field(default_factory=dict)
    category_constraints: Dict[TemplateCategory, Dict[str, Any]] = field(default_factory=dict)
    
    # Cross-category analysis
    enable_correlation_analysis: bool = True
    enable_diversification_analysis: bool = True

@dataclass
class CategoryPerformanceMetrics:
    """Performance metrics specific to template categories"""
    category: TemplateCategory
    template_count: int
    
    # Aggregate metrics
    avg_return: float
    avg_volatility: float
    avg_sharpe: float
    median_sharpe: float
    
    # Risk metrics
    avg_max_drawdown: float
    worst_case_drawdown: float
    category_var_95: float
    
    # Category-specific metrics
    diversification_ratio: float
    correlation_with_benchmark: float
    category_beta: float
    
    # Template distribution
    top_performers: List[Tuple[str, float]]  # (template_id, sharpe_ratio)
    bottom_performers: List[Tuple[str, float]]
    
    def get_category_grade(self) -> str:
        """Get overall category performance grade"""
        if self.avg_sharpe > 1.5:
            return "A"
        elif self.avg_sharpe > 1.0:
            return "B"
        elif self.avg_sharpe > 0.5:
            return "C"
        elif self.avg_sharpe > 0.0:
            return "D"
        else:
            return "F"

@dataclass
class CrossCategoryComparison:
    """Results from cross-category comparison"""
    comparison_id: str
    categories_compared: List[TemplateCategory]
    
    # Performance ranking
    category_rankings: List[Tuple[TemplateCategory, float]]  # (category, avg_sharpe)
    
    # Statistical analysis
    performance_correlation_matrix: pd.DataFrame
    risk_return_efficiency: Dict[TemplateCategory, float]
    diversification_benefits: Dict[Tuple[TemplateCategory, TemplateCategory], float]
    
    # Recommendations
    optimal_category_allocation: Dict[TemplateCategory, float]
    category_complementarity_scores: Dict[Tuple[TemplateCategory, TemplateCategory], float]

class CategoryAwareSimulator:
    """
    Advanced simulator that provides category-specific analysis,
    cross-category benchmarking, and inheritance-aware performance testing.
    """
    
    def __init__(self, template_registry: TemplateRegistry,
                 strategy_manager: TemplateStrategyManager,
                 scenario_manager: TemplateScenarioManager):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.template_registry = template_registry
        self.strategy_manager = strategy_manager
        self.scenario_manager = scenario_manager
        
        # Simulation state
        self.simulation_results: Dict[str, Dict[str, Any]] = {}
        self.category_metrics: Dict[TemplateCategory, CategoryPerformanceMetrics] = {}
        self.cross_category_analyses: Dict[str, CrossCategoryComparison] = {}
        
        # Category benchmarks
        self.category_benchmarks = self._initialize_category_benchmarks()
        
        self.logger.info("CategoryAwareSimulator initialized")
    
    def _initialize_category_benchmarks(self) -> Dict[TemplateCategory, Dict[str, float]]:
        """Initialize category-specific benchmark metrics"""
        
        return {
            TemplateCategory.BASE: {
                'expected_sharpe': 0.8,
                'max_drawdown_threshold': 0.15,
                'min_return': 0.06
            },
            TemplateCategory.SPECIFIC: {
                'expected_sharpe': 1.0,
                'max_drawdown_threshold': 0.20,
                'min_return': 0.08
            },
            TemplateCategory.COMPOSITE: {
                'expected_sharpe': 1.2,
                'max_drawdown_threshold': 0.12,
                'min_return': 0.10
            }
        }
    
    async def run_category_simulation(self, config: CategorySimulationConfig) -> Dict[str, Any]:
        """
        Run comprehensive category-aware simulation
        """
        try:
            simulation_id = f"cat_sim_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.logger.info(f"Starting category simulation {simulation_id}")
            self.logger.info(f"Mode: {config.simulation_mode.value}, Categories: {len(config.target_categories)}")
            
            results = {}
            
            if config.simulation_mode == SimulationMode.WITHIN_CATEGORY:
                results = await self._run_within_category_simulation(config, simulation_id)
            
            elif config.simulation_mode == SimulationMode.CROSS_CATEGORY:
                results = await self._run_cross_category_simulation(config, simulation_id)
            
            elif config.simulation_mode == SimulationMode.INHERITANCE_CHAIN:
                results = await self._run_inheritance_chain_simulation(config, simulation_id)
            
            elif config.simulation_mode == SimulationMode.CATEGORY_STRESS:
                results = await self._run_category_stress_simulation(config, simulation_id)
            
            # Store results
            self.simulation_results[simulation_id] = results
            
            self.logger.info(f"Category simulation {simulation_id} completed")
            return results
            
        except Exception as e:
            self.logger.error(f"Category simulation failed: {e}")
            raise
    
    async def _run_within_category_simulation(self, config: CategorySimulationConfig,
                                            simulation_id: str) -> Dict[str, Any]:
        """Run simulation within each category"""
        
        results = {}
        
        for category in config.target_categories:
            self.logger.info(f"Running within-category simulation for {category.value}")
            
            # Get all templates in category
            category_templates = self.template_registry.search_templates(category=category)
            
            if not category_templates:
                self.logger.warning(f"No templates found in category {category.value}")
                continue
            
            # Run simulations for each template in category
            template_results = {}
            
            for template in category_templates:
                try:
                    # Run Monte Carlo simulations
                    mc_results = await self._run_template_monte_carlo(
                        template, config.num_monte_carlo_runs, config.simulation_days
                    )
                    
                    template_results[template.metadata.template_id] = mc_results
                    
                except Exception as e:
                    self.logger.error(f"Simulation failed for template {template.metadata.template_id}: {e}")
            
            # Calculate category-level metrics
            if template_results:
                category_metrics = self._calculate_category_metrics(category, template_results)
                self.category_metrics[category] = category_metrics
                
                results[category.value] = {
                    'template_results': template_results,
                    'category_metrics': category_metrics,
                    'benchmark_comparison': self._compare_with_category_benchmark(category, category_metrics)
                }
        
        return results
    
    async def _run_cross_category_simulation(self, config: CategorySimulationConfig,
                                           simulation_id: str) -> Dict[str, Any]:
        """Run cross-category comparison simulation"""
        
        self.logger.info(f"Running cross-category simulation across {len(config.target_categories)} categories")
        
        # First run within-category simulations
        within_category_results = await self._run_within_category_simulation(config, simulation_id)
        
        # Perform cross-category analysis
        cross_category_analysis = await self._perform_cross_category_analysis(
            config.target_categories, within_category_results
        )
        
        # Calculate diversification benefits
        diversification_analysis = self._calculate_diversification_benefits(
            config.target_categories, within_category_results
        )
        
        # Generate optimal allocation recommendations
        optimal_allocation = self._calculate_optimal_category_allocation(
            config.target_categories, within_category_results
        )
        
        results = {
            'within_category_results': within_category_results,
            'cross_category_analysis': cross_category_analysis,
            'diversification_analysis': diversification_analysis,
            'optimal_allocation': optimal_allocation,
            'correlation_matrix': self._calculate_category_correlation_matrix(within_category_results)
        }
        
        return results
    
    async def _run_inheritance_chain_simulation(self, config: CategorySimulationConfig,
                                              simulation_id: str) -> Dict[str, Any]:
        """Run simulation focusing on template inheritance chains"""
        
        self.logger.info("Running inheritance chain simulation")
        
        results = {}
        
        for category in config.target_categories:
            category_templates = self.template_registry.search_templates(category=category)
            
            for template in category_templates:
                if template.metadata.parent_templates:
                    # Analyze inheritance chain performance
                    inheritance_analysis = await self._analyze_inheritance_chain_performance(
                        template, config.simulation_days
                    )
                    
                    results[template.metadata.template_id] = inheritance_analysis
        
        return results
    
    async def _run_category_stress_simulation(self, config: CategorySimulationConfig,
                                            simulation_id: str) -> Dict[str, Any]:
        """Run category-specific stress testing"""
        
        self.logger.info("Running category stress simulation")
        
        results = {}
        
        for category in config.target_categories:
            # Define category-specific stress scenarios
            stress_scenarios = self._get_category_stress_scenarios(category)
            
            category_templates = self.template_registry.search_templates(category=category)
            
            category_stress_results = {}
            
            for scenario_id in stress_scenarios:
                template_ids = [t.metadata.template_id for t in category_templates]
                
                scenario_results = await self.scenario_manager.run_scenario_test(
                    scenario_id, template_ids
                )
                
                category_stress_results[scenario_id] = scenario_results
            
            # Analyze category resilience
            category_resilience = self._analyze_category_resilience(category_stress_results)
            
            results[category.value] = {
                'stress_scenarios': category_stress_results,
                'resilience_analysis': category_resilience
            }
        
        return results
    
    async def _run_template_monte_carlo(self, template: BaseTemplate, 
                                      num_runs: int, simulation_days: int) -> Dict[str, Any]:
        """Run Monte Carlo simulation for a single template"""
        
        # Run Monte Carlo scenarios
        mc_results = await self.scenario_manager.run_monte_carlo_scenarios(
            [template.metadata.template_id], num_runs
        )
        
        if template.metadata.template_id not in mc_results:
            return {}
        
        scenario_results = mc_results[template.metadata.template_id]
        
        # Calculate statistics
        returns = [r.scenario_return for r in scenario_results]
        sharpe_ratios = [r.scenario_sharpe for r in scenario_results]
        max_drawdowns = [r.scenario_max_drawdown for r in scenario_results]
        
        statistics = {
            'mean_return': np.mean(returns),
            'std_return': np.std(returns),
            'mean_sharpe': np.mean(sharpe_ratios),
            'std_sharpe': np.std(sharpe_ratios),
            'mean_max_drawdown': np.mean(max_drawdowns),
            'worst_drawdown': np.max(max_drawdowns),
            'success_rate': sum(1 for r in returns if r > 0) / len(returns),
            'var_95': np.percentile(returns, 5),
            'var_99': np.percentile(returns, 1),
            'scenario_results': scenario_results
        }
        
        return statistics
    
    def _calculate_category_metrics(self, category: TemplateCategory,
                                  template_results: Dict[str, Dict[str, Any]]) -> CategoryPerformanceMetrics:
        """Calculate aggregate metrics for a category"""
        
        if not template_results:
            return CategoryPerformanceMetrics(
                category=category,
                template_count=0,
                avg_return=0.0,
                avg_volatility=0.0,
                avg_sharpe=0.0,
                median_sharpe=0.0,
                avg_max_drawdown=0.0,
                worst_case_drawdown=0.0,
                category_var_95=0.0,
                diversification_ratio=0.0,
                correlation_with_benchmark=0.0,
                category_beta=1.0,
                top_performers=[],
                bottom_performers=[]
            )
        
        # Extract metrics from template results
        returns = []
        sharpe_ratios = []
        max_drawdowns = []
        
        for template_id, results in template_results.items():
            if 'mean_return' in results:
                returns.append(results['mean_return'])
                sharpe_ratios.append(results['mean_sharpe'])
                max_drawdowns.append(results['mean_max_drawdown'])
        
        # Calculate aggregate metrics
        avg_return = np.mean(returns) if returns else 0.0
        avg_sharpe = np.mean(sharpe_ratios) if sharpe_ratios else 0.0
        median_sharpe = np.median(sharpe_ratios) if sharpe_ratios else 0.0
        avg_max_drawdown = np.mean(max_drawdowns) if max_drawdowns else 0.0
        worst_case_drawdown = np.max(max_drawdowns) if max_drawdowns else 0.0
        
        # Calculate volatility (simplified)
        returns_std = np.std(returns) if len(returns) > 1 else 0.0
        avg_volatility = returns_std * np.sqrt(252)  # Annualized
        
        # Category-specific metrics
        category_var_95 = np.percentile(returns, 5) if returns else 0.0
        
        # Rank templates by performance
        template_performance = [(tid, template_results[tid].get('mean_sharpe', 0.0)) 
                              for tid in template_results.keys()]
        template_performance.sort(key=lambda x: x[1], reverse=True)
        
        top_performers = template_performance[:min(3, len(template_performance))]
        bottom_performers = template_performance[-min(3, len(template_performance)):]
        
        return CategoryPerformanceMetrics(
            category=category,
            template_count=len(template_results),
            avg_return=avg_return,
            avg_volatility=avg_volatility,
            avg_sharpe=avg_sharpe,
            median_sharpe=median_sharpe,
            avg_max_drawdown=avg_max_drawdown,
            worst_case_drawdown=worst_case_drawdown,
            category_var_95=abs(category_var_95),
            diversification_ratio=self._calculate_diversification_ratio(template_results),
            correlation_with_benchmark=0.7,  # Simplified - would calculate actual correlation
            category_beta=1.0,  # Simplified - would calculate actual beta
            top_performers=top_performers,
            bottom_performers=bottom_performers
        )
    
    def _calculate_diversification_ratio(self, template_results: Dict[str, Dict[str, Any]]) -> float:
        """Calculate diversification ratio for templates in category"""
        
        if len(template_results) < 2:
            return 1.0
        
        # Simplified diversification calculation
        # In practice, would use actual return correlations
        returns = [results.get('mean_return', 0.0) for results in template_results.values()]
        volatilities = [results.get('std_return', 0.0) for results in template_results.values()]
        
        if not returns or not volatilities:
            return 1.0
        
        # Portfolio return and volatility (equal weights)
        portfolio_return = np.mean(returns)
        
        # Simplified portfolio volatility (assuming moderate correlation)
        avg_correlation = 0.5  # Assumed correlation
        portfolio_variance = (1.0 / len(volatilities)) * np.sum(np.array(volatilities) ** 2)
        portfolio_variance += (1.0 - 1.0/len(volatilities)) * avg_correlation * np.mean(volatilities) ** 2
        portfolio_volatility = np.sqrt(portfolio_variance)
        
        # Diversification ratio
        weighted_avg_volatility = np.mean(volatilities)
        diversification_ratio = weighted_avg_volatility / max(portfolio_volatility, 0.001)
        
        return min(diversification_ratio, 3.0)  # Cap at reasonable level
    
    async def _perform_cross_category_analysis(self, categories: List[TemplateCategory],
                                             within_category_results: Dict[str, Any]) -> CrossCategoryComparison:
        """Perform comprehensive cross-category analysis"""
        
        comparison_id = f"cross_cat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Calculate category rankings
        category_rankings = []
        for category in categories:
            if category.value in within_category_results:
                metrics = within_category_results[category.value]['category_metrics']
                category_rankings.append((category, metrics.avg_sharpe))
        
        category_rankings.sort(key=lambda x: x[1], reverse=True)
        
        # Calculate correlation matrix (simplified)
        correlation_data = {}
        for category in categories:
            if category.value in within_category_results:
                metrics = within_category_results[category.value]['category_metrics']
                correlation_data[category.value] = metrics.avg_return
        
        correlation_matrix = pd.DataFrame([correlation_data])  # Simplified
        
        # Calculate risk-return efficiency
        risk_return_efficiency = {}
        for category in categories:
            if category.value in within_category_results:
                metrics = within_category_results[category.value]['category_metrics']
                efficiency = metrics.avg_sharpe / max(metrics.avg_volatility, 0.001)
                risk_return_efficiency[category] = efficiency
        
        comparison = CrossCategoryComparison(
            comparison_id=comparison_id,
            categories_compared=categories,
            category_rankings=category_rankings,
            performance_correlation_matrix=correlation_matrix,
            risk_return_efficiency=risk_return_efficiency,
            diversification_benefits={},  # Would be calculated with actual data
            optimal_category_allocation={},  # Would be calculated with optimization
            category_complementarity_scores={}  # Would be calculated with correlation analysis
        )
        
        self.cross_category_analyses[comparison_id] = comparison
        return comparison
    
    def _calculate_diversification_benefits(self, categories: List[TemplateCategory],
                                          within_category_results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate diversification benefits across categories"""
        
        diversification_analysis = {
            'single_category_risk': {},
            'multi_category_risk': {},
            'diversification_benefit': {}
        }
        
        # Calculate single category risks
        for category in categories:
            if category.value in within_category_results:
                metrics = within_category_results[category.value]['category_metrics']
                diversification_analysis['single_category_risk'][category.value] = metrics.avg_max_drawdown
        
        # Calculate multi-category portfolio risk (simplified)
        if len(categories) > 1:
            single_risks = list(diversification_analysis['single_category_risk'].values())
            # Assume moderate correlation between categories
            portfolio_risk = np.sqrt(np.mean(np.array(single_risks) ** 2) * 0.7)  # 0.7 correlation assumption
            diversification_analysis['multi_category_risk'] = portfolio_risk
            diversification_analysis['diversification_benefit'] = np.mean(single_risks) - portfolio_risk
        
        return diversification_analysis
    
    def _calculate_optimal_category_allocation(self, categories: List[TemplateCategory],
                                             within_category_results: Dict[str, Any]) -> Dict[str, float]:
        """Calculate optimal allocation across categories"""
        
        # Simplified optimization - equal risk budgeting
        allocation = {}
        total_categories = len([cat for cat in categories if cat.value in within_category_results])
        
        if total_categories > 0:
            equal_weight = 1.0 / total_categories
            for category in categories:
                if category.value in within_category_results:
                    allocation[category.value] = equal_weight
        
        return allocation
    
    def _calculate_category_correlation_matrix(self, within_category_results: Dict[str, Any]) -> pd.DataFrame:
        """Calculate correlation matrix between categories"""
        
        # Extract category returns for correlation calculation
        category_data = {}
        
        for category_name, results in within_category_results.items():
            if 'category_metrics' in results:
                metrics = results['category_metrics']
                # Use return as proxy for correlation calculation
                category_data[category_name] = [metrics.avg_return]
        
        if len(category_data) < 2:
            return pd.DataFrame()
        
        # Create correlation matrix (simplified - would use actual return series)
        df = pd.DataFrame(category_data)
        correlation_matrix = df.corr()
        
        return correlation_matrix
    
    async def _analyze_inheritance_chain_performance(self, template: BaseTemplate,
                                                   simulation_days: int) -> Dict[str, Any]:
        """Analyze performance across template inheritance chain"""
        
        inheritance_chain = [template.metadata.template_id]
        inheritance_chain.extend(template.metadata.parent_templates)
        
        chain_results = {}
        
        for template_id in inheritance_chain:
            try:
                chain_template = self.template_registry.get_template(template_id)
                if chain_template:
                    mc_results = await self._run_template_monte_carlo(
                        chain_template, 50, simulation_days  # Fewer runs for inheritance analysis
                    )
                    chain_results[template_id] = mc_results
            except Exception as e:
                self.logger.error(f"Inheritance analysis failed for {template_id}: {e}")
        
        # Analyze inheritance impact
        inheritance_analysis = {
            'inheritance_chain': inheritance_chain,
            'chain_results': chain_results,
            'inheritance_impact': self._calculate_inheritance_impact(chain_results),
            'performance_progression': self._analyze_performance_progression(chain_results, inheritance_chain)
        }
        
        return inheritance_analysis
    
    def _calculate_inheritance_impact(self, chain_results: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
        """Calculate impact of inheritance on performance"""
        
        inheritance_impact = {}
        
        template_ids = list(chain_results.keys())
        if len(template_ids) < 2:
            return inheritance_impact
        
        # Compare child vs parent performance
        for i in range(len(template_ids) - 1):
            child_id = template_ids[i]
            parent_id = template_ids[i + 1]
            
            if child_id in chain_results and parent_id in chain_results:
                child_sharpe = chain_results[child_id].get('mean_sharpe', 0.0)
                parent_sharpe = chain_results[parent_id].get('mean_sharpe', 0.0)
                
                impact = child_sharpe - parent_sharpe
                inheritance_impact[f"{child_id}_vs_{parent_id}"] = impact
        
        return inheritance_impact
    
    def _analyze_performance_progression(self, chain_results: Dict[str, Dict[str, Any]],
                                       inheritance_chain: List[str]) -> Dict[str, Any]:
        """Analyze performance progression through inheritance chain"""
        
        progression = {
            'sharpe_progression': [],
            'return_progression': [],
            'risk_progression': []
        }
        
        for template_id in inheritance_chain:
            if template_id in chain_results:
                results = chain_results[template_id]
                progression['sharpe_progression'].append(results.get('mean_sharpe', 0.0))
                progression['return_progression'].append(results.get('mean_return', 0.0))
                progression['risk_progression'].append(results.get('std_return', 0.0))
        
        return progression
    
    def _get_category_stress_scenarios(self, category: TemplateCategory) -> List[str]:
        """Get stress scenarios applicable to specific category"""
        
        if category == TemplateCategory.SPECIFIC:
            return ["market_crash_2008", "interest_rate_shock", "currency_crisis"]
        elif category == TemplateCategory.COMPOSITE:
            return ["market_crash_2008", "high_volatility_regime"]
        else:  # BASE
            return ["market_crash_2008", "high_volatility_regime"]
    
    def _analyze_category_resilience(self, stress_results: Dict[str, Dict[str, ScenarioResult]]) -> Dict[str, Any]:
        """Analyze category resilience under stress scenarios"""
        
        resilience_analysis = {
            'stress_performance': {},
            'resilience_score': 0.0,
            'worst_scenario': '',
            'recovery_potential': 0.0
        }
        
        total_stress_loss = 0.0
        scenario_count = 0
        worst_loss = 0.0
        worst_scenario = ''
        
        for scenario_id, template_results in stress_results.items():
            scenario_losses = [result.stress_loss for result in template_results.values()]
            
            if scenario_losses:
                avg_loss = np.mean(scenario_losses)
                max_loss = np.max(scenario_losses)
                
                resilience_analysis['stress_performance'][scenario_id] = {
                    'avg_loss': avg_loss,
                    'max_loss': max_loss,
                    'templates_affected': len(scenario_losses)
                }
                
                total_stress_loss += avg_loss
                scenario_count += 1
                
                if max_loss > worst_loss:
                    worst_loss = max_loss
                    worst_scenario = scenario_id
        
        # Calculate overall resilience score (lower is better)
        if scenario_count > 0:
            avg_stress_loss = total_stress_loss / scenario_count
            resilience_score = 1.0 / max(avg_stress_loss, 0.01)  # Inverse of average loss
            resilience_analysis['resilience_score'] = min(resilience_score, 10.0)
        
        resilience_analysis['worst_scenario'] = worst_scenario
        resilience_analysis['recovery_potential'] = max(0.0, 1.0 - worst_loss)  # Simplified recovery metric
        
        return resilience_analysis
    
    def _compare_with_category_benchmark(self, category: TemplateCategory,
                                       metrics: CategoryPerformanceMetrics) -> Dict[str, Any]:
        """Compare category performance with benchmarks"""
        
        benchmarks = self.category_benchmarks.get(category, {})
        
        comparison = {
            'benchmark_met': True,
            'performance_vs_benchmark': {},
            'areas_of_concern': [],
            'recommendations': []
        }
        
        # Compare with expected Sharpe ratio
        expected_sharpe = benchmarks.get('expected_sharpe', 0.0)
        if metrics.avg_sharpe < expected_sharpe:
            comparison['benchmark_met'] = False
            comparison['areas_of_concern'].append('Below expected Sharpe ratio')
            comparison['recommendations'].append('Review signal generation and risk management')
        
        comparison['performance_vs_benchmark']['sharpe_ratio'] = {
            'actual': metrics.avg_sharpe,
            'expected': expected_sharpe,
            'ratio': metrics.avg_sharpe / max(expected_sharpe, 0.001)
        }
        
        # Compare with max drawdown threshold
        max_dd_threshold = benchmarks.get('max_drawdown_threshold', 0.20)
        if metrics.avg_max_drawdown > max_dd_threshold:
            comparison['benchmark_met'] = False
            comparison['areas_of_concern'].append('Excessive drawdown')
            comparison['recommendations'].append('Implement stronger risk controls')
        
        comparison['performance_vs_benchmark']['max_drawdown'] = {
            'actual': metrics.avg_max_drawdown,
            'threshold': max_dd_threshold,
            'acceptable': metrics.avg_max_drawdown <= max_dd_threshold
        }
        
        return comparison
    
    def get_simulation_summary(self) -> Dict[str, Any]:
        """Get summary of all simulation activities"""
        
        return {
            'total_simulations': len(self.simulation_results),
            'categories_analyzed': len(self.category_metrics),
            'cross_category_analyses': len(self.cross_category_analyses),
            'category_performance_summary': {
                category.value: {
                    'avg_sharpe': metrics.avg_sharpe,
                    'template_count': metrics.template_count,
                    'grade': metrics.get_category_grade()
                }
                for category, metrics in self.category_metrics.items()
            }
        }
