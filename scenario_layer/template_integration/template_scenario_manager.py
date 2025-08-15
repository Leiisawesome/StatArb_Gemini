"""
Template Scenario Manager
========================

Manages template-based scenario testing including stress testing,
Monte Carlo simulations, and multi-dimensional scenario analysis.

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
import json
from collections import defaultdict
import uuid

from strategy_templates.base import TemplateRegistry, BaseTemplate, TemplateCategory
from strategy_layer.template_integration import TemplateStrategyManager
from .template_backtesting_engine import TemplateBacktestingEngine, TemplateBacktestConfig, TemplateBacktestResult

logger = logging.getLogger(__name__)

class ScenarioType(Enum):
    """Types of scenario testing"""
    STRESS_TEST = "stress_test"                    # Extreme market conditions
    MONTE_CARLO = "monte_carlo"                    # Random scenario generation
    HISTORICAL_REPLAY = "historical_replay"       # Historical market events
    PARAMETER_SWEEP = "parameter_sweep"            # Parameter sensitivity analysis
    MARKET_REGIME = "market_regime"               # Different market regimes
    CORRELATION_SHOCK = "correlation_shock"        # Correlation breakdown scenarios
    VOLATILITY_REGIME = "volatility_regime"       # High/low volatility periods

class ScenarioSeverity(Enum):
    """Severity levels for stress scenarios"""
    MILD = "mild"           # 1-2 sigma events
    MODERATE = "moderate"   # 2-3 sigma events  
    SEVERE = "severe"       # 3-4 sigma events
    EXTREME = "extreme"     # 4+ sigma events

@dataclass
class ScenarioDefinition:
    """Definition of a testing scenario"""
    scenario_id: str
    name: str
    scenario_type: ScenarioType
    severity: ScenarioSeverity
    description: str
    
    # Market parameters
    market_conditions: Dict[str, Any] = field(default_factory=dict)
    duration_days: int = 30
    
    # Template filters
    applicable_categories: List[TemplateCategory] = field(default_factory=list)
    applicable_templates: List[str] = field(default_factory=list)
    
    # Scenario parameters
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'scenario_id': self.scenario_id,
            'name': self.name,
            'scenario_type': self.scenario_type.value,
            'severity': self.severity.value,
            'description': self.description,
            'market_conditions': self.market_conditions,
            'duration_days': self.duration_days,
            'applicable_categories': [cat.value for cat in self.applicable_categories],
            'applicable_templates': self.applicable_templates,
            'parameters': self.parameters
        }

@dataclass 
class ScenarioResult:
    """Result from scenario testing"""
    scenario_id: str
    template_id: str
    scenario_definition: ScenarioDefinition
    
    # Performance under scenario
    scenario_return: float
    scenario_volatility: float
    scenario_sharpe: float
    scenario_max_drawdown: float
    
    # Risk metrics
    var_95: float  # 95% Value at Risk
    cvar_95: float # 95% Conditional Value at Risk
    stress_loss: float  # Loss under stress scenario
    
    # Template-specific metrics
    category_relative_performance: float  # vs other templates in category
    inheritance_resilience: Dict[str, float]  # Performance vs parent templates
    
    # Detailed analysis
    daily_returns: pd.Series = field(default=None)
    risk_decomposition: Dict[str, Any] = field(default_factory=dict)
    scenario_attribution: Dict[str, Any] = field(default_factory=dict)
    
    def get_risk_grade(self) -> str:
        """Get risk grade based on performance"""
        if self.scenario_max_drawdown < 0.05:
            return "A"
        elif self.scenario_max_drawdown < 0.10:
            return "B"
        elif self.scenario_max_drawdown < 0.20:
            return "C"
        elif self.scenario_max_drawdown < 0.35:
            return "D"
        else:
            return "F"

@dataclass
class ScenarioSuite:
    """Collection of scenarios for comprehensive testing"""
    suite_id: str
    name: str
    scenarios: List[ScenarioDefinition]
    template_filters: Dict[str, Any] = field(default_factory=dict)
    
    def get_scenarios_by_type(self, scenario_type: ScenarioType) -> List[ScenarioDefinition]:
        """Get scenarios of specific type"""
        return [s for s in self.scenarios if s.scenario_type == scenario_type]

class TemplateScenarioManager:
    """
    Manages comprehensive scenario testing for template-based strategies
    with support for stress testing, Monte Carlo analysis, and regime testing.
    """
    
    def __init__(self, template_registry: TemplateRegistry,
                 strategy_manager: TemplateStrategyManager,
                 backtesting_engine: TemplateBacktestingEngine):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.template_registry = template_registry
        self.strategy_manager = strategy_manager
        self.backtesting_engine = backtesting_engine
        
        # Scenario management
        self.scenario_definitions: Dict[str, ScenarioDefinition] = {}
        self.scenario_suites: Dict[str, ScenarioSuite] = {}
        self.scenario_results: Dict[str, ScenarioResult] = {}
        
        # Predefined scenarios
        self._initialize_predefined_scenarios()
        
        self.logger.info("TemplateScenarioManager initialized")
    
    def _initialize_predefined_scenarios(self):
        """Initialize common scenario definitions"""
        
        # Market crash scenario
        crash_scenario = ScenarioDefinition(
            scenario_id="market_crash_2008",
            name="Market Crash (2008-style)",
            scenario_type=ScenarioType.STRESS_TEST,
            severity=ScenarioSeverity.EXTREME,
            description="Severe market downturn with high volatility and correlation breakdown",
            market_conditions={
                "equity_return": -0.40,  # 40% market decline
                "volatility_multiplier": 3.0,  # 3x normal volatility
                "correlation_increase": 0.8,   # High correlation during stress
                "liquidity_reduction": 0.5     # 50% liquidity reduction
            },
            duration_days=180,
            applicable_categories=[TemplateCategory.BASE, TemplateCategory.SPECIFIC],
            parameters={
                "daily_vol": 0.05,  # 5% daily volatility
                "trend_bias": -0.02  # Negative trend bias
            }
        )
        self.scenario_definitions[crash_scenario.scenario_id] = crash_scenario
        
        # High volatility regime
        high_vol_scenario = ScenarioDefinition(
            scenario_id="high_volatility_regime",
            name="High Volatility Regime",
            scenario_type=ScenarioType.VOLATILITY_REGIME,
            severity=ScenarioSeverity.MODERATE,
            description="Extended period of elevated market volatility",
            market_conditions={
                "volatility_multiplier": 2.0,
                "volatility_clustering": True,
                "mean_reversion_speed": 0.5
            },
            duration_days=90,
            applicable_categories=[TemplateCategory.BASE, TemplateCategory.SPECIFIC, TemplateCategory.COMPOSITE],
            parameters={
                "daily_vol": 0.03,
                "vol_persistence": 0.8
            }
        )
        self.scenario_definitions[high_vol_scenario.scenario_id] = high_vol_scenario
        
        # Interest rate shock
        rate_shock_scenario = ScenarioDefinition(
            scenario_id="interest_rate_shock",
            name="Interest Rate Shock",
            scenario_type=ScenarioType.STRESS_TEST,
            severity=ScenarioSeverity.SEVERE,
            description="Sudden large change in interest rates",
            market_conditions={
                "rate_change_bps": 300,  # 3% rate increase
                "curve_steepening": True,
                "credit_spread_widening": 150  # 1.5% credit spread increase
            },
            duration_days=60,
            applicable_categories=[TemplateCategory.SPECIFIC],  # Mainly fixed income
            parameters={
                "duration_impact": -0.15,  # Negative duration impact
                "credit_impact": -0.08     # Credit spread impact
            }
        )
        self.scenario_definitions[rate_shock_scenario.scenario_id] = rate_shock_scenario
        
        # Currency crisis
        fx_crisis_scenario = ScenarioDefinition(
            scenario_id="currency_crisis",
            name="Currency Crisis",
            scenario_type=ScenarioType.STRESS_TEST,
            severity=ScenarioSeverity.SEVERE,
            description="Major currency devaluation and FX market disruption",
            market_conditions={
                "fx_volatility_multiplier": 4.0,
                "carry_trade_unwind": True,
                "central_bank_intervention": True
            },
            duration_days=45,
            applicable_categories=[TemplateCategory.SPECIFIC],  # Currency strategies
            parameters={
                "major_currency_move": -0.25,  # 25% devaluation
                "volatility_spike": 0.06       # 6% daily vol
            }
        )
        self.scenario_definitions[fx_crisis_scenario.scenario_id] = fx_crisis_scenario
    
    async def run_scenario_test(self, scenario_id: str, template_ids: List[str]) -> Dict[str, ScenarioResult]:
        """
        Run scenario test for specified templates
        """
        try:
            if scenario_id not in self.scenario_definitions:
                raise ValueError(f"Scenario {scenario_id} not found")
            
            scenario = self.scenario_definitions[scenario_id]
            self.logger.info(f"Running scenario test: {scenario.name}")
            self.logger.info(f"Testing {len(template_ids)} templates")
            
            results = {}
            
            for template_id in template_ids:
                template = self.template_registry.get_template(template_id)
                if not template:
                    self.logger.warning(f"Template {template_id} not found")
                    continue
                
                # Check if scenario applies to this template
                if not self._is_scenario_applicable(scenario, template):
                    self.logger.info(f"Scenario {scenario_id} not applicable to template {template_id}")
                    continue
                
                self.logger.info(f"Running scenario {scenario_id} for template {template_id}")
                
                # Run scenario simulation
                result = await self._simulate_scenario(scenario, template)
                results[template_id] = result
                
                # Store result
                result_key = f"{scenario_id}_{template_id}"
                self.scenario_results[result_key] = result
            
            self.logger.info(f"Scenario test {scenario_id} completed: {len(results)} results")
            return results
            
        except Exception as e:
            self.logger.error(f"Scenario test failed: {e}")
            raise
    
    async def run_scenario_suite(self, suite_id: str, template_ids: List[str]) -> Dict[str, Dict[str, ScenarioResult]]:
        """
        Run a complete scenario suite for templates
        """
        if suite_id not in self.scenario_suites:
            raise ValueError(f"Scenario suite {suite_id} not found")
        
        suite = self.scenario_suites[suite_id]
        self.logger.info(f"Running scenario suite: {suite.name}")
        self.logger.info(f"Suite contains {len(suite.scenarios)} scenarios")
        
        suite_results = {}
        
        for scenario in suite.scenarios:
            try:
                scenario_results = await self.run_scenario_test(scenario.scenario_id, template_ids)
                suite_results[scenario.scenario_id] = scenario_results
            except Exception as e:
                self.logger.error(f"Scenario {scenario.scenario_id} failed in suite: {e}")
        
        return suite_results
    
    async def run_monte_carlo_scenarios(self, template_ids: List[str], 
                                      num_simulations: int = 1000) -> Dict[str, List[ScenarioResult]]:
        """
        Run Monte Carlo scenario simulations
        """
        self.logger.info(f"Running Monte Carlo scenarios: {num_simulations} simulations")
        
        mc_results = defaultdict(list)
        
        for template_id in template_ids:
            template = self.template_registry.get_template(template_id)
            if not template:
                continue
            
            self.logger.info(f"Running Monte Carlo for template {template_id}")
            
            for i in range(num_simulations):
                # Generate random scenario
                mc_scenario = self._generate_monte_carlo_scenario(f"mc_{i}")
                
                try:
                    result = await self._simulate_scenario(mc_scenario, template)
                    mc_results[template_id].append(result)
                except Exception as e:
                    self.logger.debug(f"Monte Carlo simulation {i} failed for {template_id}: {e}")
        
        # Calculate Monte Carlo statistics
        for template_id, results in mc_results.items():
            self._calculate_monte_carlo_statistics(template_id, results)
        
        return dict(mc_results)
    
    async def run_parameter_sweep(self, template_id: str, parameter_ranges: Dict[str, Tuple[float, float]],
                                steps: int = 10) -> Dict[str, ScenarioResult]:
        """
        Run parameter sensitivity analysis
        """
        template = self.template_registry.get_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")
        
        self.logger.info(f"Running parameter sweep for template {template_id}")
        self.logger.info(f"Testing {len(parameter_ranges)} parameters with {steps} steps each")
        
        sweep_results = {}
        
        for param_name, (min_val, max_val) in parameter_ranges.items():
            param_values = np.linspace(min_val, max_val, steps)
            
            for i, param_value in enumerate(param_values):
                # Create scenario with parameter variation
                scenario = ScenarioDefinition(
                    scenario_id=f"param_sweep_{param_name}_{i}",
                    name=f"Parameter Sweep: {param_name} = {param_value:.3f}",
                    scenario_type=ScenarioType.PARAMETER_SWEEP,
                    severity=ScenarioSeverity.MILD,
                    description=f"Parameter sensitivity test for {param_name}",
                    market_conditions={"parameter_override": {param_name: param_value}},
                    duration_days=30
                )
                
                try:
                    result = await self._simulate_scenario(scenario, template)
                    sweep_results[f"{param_name}_{param_value:.3f}"] = result
                except Exception as e:
                    self.logger.debug(f"Parameter sweep failed for {param_name}={param_value}: {e}")
        
        return sweep_results
    
    async def _simulate_scenario(self, scenario: ScenarioDefinition, 
                               template: BaseTemplate) -> ScenarioResult:
        """
        Simulate a specific scenario for a template
        """
        
        # Generate scenario-specific market data
        market_data = self._generate_scenario_market_data(scenario)
        
        # Create strategy instance
        instance_id = self.strategy_manager.create_strategy_instance(
            template.metadata.template_id,
            custom_parameters=scenario.market_conditions.get("parameter_override", {})
        )
        
        try:
            # Simulate strategy performance under scenario
            portfolio_returns = []
            portfolio_value = 100000.0  # Initial capital
            daily_returns = []
            
            # Generate time series for scenario duration
            dates = pd.date_range(
                start=datetime.now() - timedelta(days=scenario.duration_days),
                periods=scenario.duration_days,
                freq='D'
            )
            
            for date in dates:
                # Create market snapshot for this date
                market_snapshot = self._get_scenario_market_snapshot(market_data, date, scenario)
                
                try:
                    # Execute strategy
                    result = self.strategy_manager.execute_strategy_instance(instance_id, market_snapshot)
                    
                    # Calculate daily return based on scenario conditions
                    daily_return = self._calculate_scenario_return(
                        result, scenario, market_snapshot
                    )
                    
                    daily_returns.append(daily_return)
                    portfolio_value *= (1 + daily_return)
                    portfolio_returns.append(portfolio_value)
                    
                except Exception as e:
                    # Use scenario default return on execution failure
                    daily_return = scenario.market_conditions.get("default_return", -0.001)
                    daily_returns.append(daily_return)
                    portfolio_value *= (1 + daily_return)
                    portfolio_returns.append(portfolio_value)
            
            # Calculate scenario performance metrics
            returns_series = pd.Series(daily_returns, index=dates)
            performance_metrics = self._calculate_scenario_performance_metrics(returns_series)
            
            # Calculate risk metrics
            risk_metrics = self._calculate_scenario_risk_metrics(returns_series)
            
            # Analyze template-specific performance
            template_analysis = await self._analyze_template_scenario_performance(
                template, scenario, performance_metrics, risk_metrics
            )
            
            # Create scenario result
            result = ScenarioResult(
                scenario_id=scenario.scenario_id,
                template_id=template.metadata.template_id,
                scenario_definition=scenario,
                
                scenario_return=performance_metrics['total_return'],
                scenario_volatility=performance_metrics['volatility'],
                scenario_sharpe=performance_metrics['sharpe_ratio'],
                scenario_max_drawdown=performance_metrics['max_drawdown'],
                
                var_95=risk_metrics['var_95'],
                cvar_95=risk_metrics['cvar_95'],
                stress_loss=risk_metrics['stress_loss'],
                
                category_relative_performance=template_analysis['category_relative_performance'],
                inheritance_resilience=template_analysis['inheritance_resilience'],
                
                daily_returns=returns_series,
                risk_decomposition=risk_metrics,
                scenario_attribution=template_analysis
            )
            
            return result
            
        finally:
            # Clean up strategy instance
            try:
                self.strategy_manager.stop_strategy_instance(instance_id)
            except:
                pass
    
    def _is_scenario_applicable(self, scenario: ScenarioDefinition, template: BaseTemplate) -> bool:
        """Check if scenario is applicable to template"""
        
        # Check category applicability
        if scenario.applicable_categories and template.metadata.category not in scenario.applicable_categories:
            return False
        
        # Check specific template inclusion
        if scenario.applicable_templates and template.metadata.template_id not in scenario.applicable_templates:
            return False
        
        # Special logic for asset-specific scenarios
        if scenario.scenario_type == ScenarioType.STRESS_TEST:
            if "interest_rate" in scenario.scenario_id and "fixed_income" not in template.metadata.tags:
                return False
            
            if "currency" in scenario.scenario_id and "currency" not in template.metadata.tags:
                return False
        
        return True
    
    def _generate_monte_carlo_scenario(self, scenario_id: str) -> ScenarioDefinition:
        """Generate random Monte Carlo scenario"""
        
        # Random market conditions
        market_return = np.random.normal(0.08, 0.15)  # Annual return
        volatility_multiplier = np.random.lognormal(0, 0.5)  # Vol multiplier
        correlation_shift = np.random.uniform(-0.3, 0.3)  # Correlation change
        
        scenario = ScenarioDefinition(
            scenario_id=scenario_id,
            name=f"Monte Carlo Scenario {scenario_id}",
            scenario_type=ScenarioType.MONTE_CARLO,
            severity=ScenarioSeverity.MILD,
            description="Randomly generated market scenario",
            market_conditions={
                "annual_return": market_return,
                "volatility_multiplier": volatility_multiplier,
                "correlation_shift": correlation_shift,
                "liquidity_factor": np.random.uniform(0.8, 1.2)
            },
            duration_days=np.random.randint(30, 180),
            applicable_categories=[TemplateCategory.BASE, TemplateCategory.SPECIFIC, TemplateCategory.COMPOSITE]
        )
        
        return scenario
    
    def _generate_scenario_market_data(self, scenario: ScenarioDefinition) -> Dict[str, Any]:
        """Generate market data specific to scenario conditions"""
        
        # Base market parameters
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'SPY']
        
        # Apply scenario-specific modifications
        if scenario.scenario_type == ScenarioType.STRESS_TEST:
            return self._generate_stress_test_data(scenario, symbols)
        elif scenario.scenario_type == ScenarioType.VOLATILITY_REGIME:
            return self._generate_volatility_regime_data(scenario, symbols)
        elif scenario.scenario_type == ScenarioType.MONTE_CARLO:
            return self._generate_monte_carlo_data(scenario, symbols)
        else:
            return self._generate_default_scenario_data(scenario, symbols)
    
    def _generate_stress_test_data(self, scenario: ScenarioDefinition, symbols: List[str]) -> Dict[str, Any]:
        """Generate market data for stress testing"""
        
        market_data = {}
        base_volatility = 0.02  # 2% daily volatility
        
        for symbol in symbols:
            # Apply stress conditions
            vol_multiplier = scenario.market_conditions.get("volatility_multiplier", 2.0)
            return_bias = scenario.market_conditions.get("trend_bias", -0.01)
            
            # Generate stressed returns
            returns = np.random.normal(return_bias, base_volatility * vol_multiplier, scenario.duration_days)
            
            # Add correlation breakdown during stress
            if scenario.market_conditions.get("correlation_increase", False):
                # Increase correlation during stress periods
                stress_factor = np.random.normal(0, 0.01, scenario.duration_days)
                returns += stress_factor
            
            market_data[symbol] = {
                'returns': returns,
                'volatility': base_volatility * vol_multiplier,
                'correlation_factor': scenario.market_conditions.get("correlation_increase", 0.0)
            }
        
        return market_data
    
    def _generate_volatility_regime_data(self, scenario: ScenarioDefinition, symbols: List[str]) -> Dict[str, Any]:
        """Generate market data for volatility regime testing"""
        
        market_data = {}
        base_volatility = 0.015
        
        vol_multiplier = scenario.market_conditions.get("volatility_multiplier", 1.5)
        persistence = scenario.parameters.get("vol_persistence", 0.7)
        
        for symbol in symbols:
            # Generate GARCH-like volatility clustering
            vol_series = [base_volatility * vol_multiplier]
            
            for i in range(1, scenario.duration_days):
                # Volatility clustering
                vol_shock = np.random.normal(0, 0.002)
                new_vol = persistence * vol_series[-1] + (1 - persistence) * base_volatility * vol_multiplier + vol_shock
                vol_series.append(max(0.005, new_vol))  # Floor at 0.5%
            
            # Generate returns with time-varying volatility
            returns = [np.random.normal(0, vol) for vol in vol_series]
            
            market_data[symbol] = {
                'returns': returns,
                'volatility_series': vol_series,
                'regime_type': 'high_volatility'
            }
        
        return market_data
    
    def _generate_monte_carlo_data(self, scenario: ScenarioDefinition, symbols: List[str]) -> Dict[str, Any]:
        """Generate market data for Monte Carlo simulation"""
        
        market_data = {}
        
        annual_return = scenario.market_conditions.get("annual_return", 0.08)
        vol_multiplier = scenario.market_conditions.get("volatility_multiplier", 1.0)
        base_volatility = 0.016
        
        daily_return = annual_return / 252
        daily_volatility = base_volatility * vol_multiplier
        
        for symbol in symbols:
            returns = np.random.normal(daily_return, daily_volatility, scenario.duration_days)
            
            market_data[symbol] = {
                'returns': returns,
                'expected_return': daily_return,
                'volatility': daily_volatility
            }
        
        return market_data
    
    def _generate_default_scenario_data(self, scenario: ScenarioDefinition, symbols: List[str]) -> Dict[str, Any]:
        """Generate default market data for scenario"""
        
        market_data = {}
        
        for symbol in symbols:
            returns = np.random.normal(0.0003, 0.015, scenario.duration_days)  # Neutral market
            
            market_data[symbol] = {
                'returns': returns,
                'volatility': 0.015
            }
        
        return market_data
    
    def _get_scenario_market_snapshot(self, market_data: Dict[str, Any], 
                                    date: datetime, scenario: ScenarioDefinition) -> Dict[str, Any]:
        """Get market snapshot for specific date in scenario"""
        
        day_index = (date - (datetime.now() - timedelta(days=scenario.duration_days))).days
        day_index = max(0, min(day_index, scenario.duration_days - 1))
        
        snapshot = {
            'timestamp': date,
            'symbols': list(market_data.keys()),
            'prices': {},
            'volumes': {},
            'scenario_conditions': scenario.market_conditions
        }
        
        # Apply scenario-specific market conditions
        for symbol, data in market_data.items():
            if 'returns' in data and day_index < len(data['returns']):
                # Use pre-generated scenario returns
                daily_return = data['returns'][day_index]
                price = 100.0 * (1 + daily_return)  # Simplified pricing
            else:
                price = 100.0  # Default price
            
            snapshot['prices'][symbol] = price
            snapshot['volumes'][symbol] = np.random.uniform(100000, 1000000)
        
        return snapshot
    
    def _calculate_scenario_return(self, strategy_result, scenario: ScenarioDefinition,
                                 market_snapshot: Dict[str, Any]) -> float:
        """Calculate daily return under scenario conditions"""
        
        if strategy_result.errors:
            # Return scenario default on strategy failure
            return scenario.market_conditions.get("default_return", -0.001)
        
        # Simple return calculation based on strategy signals and market conditions
        total_signal_strength = sum(abs(signal) for signal in strategy_result.signals.values())
        
        if total_signal_strength == 0:
            return 0.0
        
        # Apply scenario market conditions to returns
        base_return = total_signal_strength * 0.001  # Base return from signals
        
        # Apply scenario-specific modifications
        if scenario.scenario_type == ScenarioType.STRESS_TEST:
            stress_factor = scenario.market_conditions.get("trend_bias", 0.0)
            volatility_factor = scenario.market_conditions.get("volatility_multiplier", 1.0)
            base_return += stress_factor
            base_return *= (1.0 / volatility_factor)  # Inverse relationship with volatility
        
        return base_return
    
    def _calculate_scenario_performance_metrics(self, returns: pd.Series) -> Dict[str, float]:
        """Calculate performance metrics for scenario"""
        
        if returns.empty:
            return {
                'total_return': 0.0,
                'volatility': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0
            }
        
        total_return = (1 + returns).prod() - 1
        volatility = returns.std() * np.sqrt(252)  # Annualized
        sharpe_ratio = (returns.mean() * 252) / max(volatility, 0.001)
        
        # Calculate max drawdown
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        
        return {
            'total_return': total_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': abs(max_drawdown)
        }
    
    def _calculate_scenario_risk_metrics(self, returns: pd.Series) -> Dict[str, float]:
        """Calculate risk metrics for scenario"""
        
        if returns.empty:
            return {
                'var_95': 0.0,
                'cvar_95': 0.0,
                'stress_loss': 0.0
            }
        
        # Value at Risk (95%)
        var_95 = np.percentile(returns, 5)
        
        # Conditional Value at Risk (95%)
        cvar_95 = returns[returns <= var_95].mean()
        
        # Stress loss (worst single day)
        stress_loss = returns.min()
        
        return {
            'var_95': abs(var_95),
            'cvar_95': abs(cvar_95),
            'stress_loss': abs(stress_loss)
        }
    
    async def _analyze_template_scenario_performance(self, template: BaseTemplate,
                                                   scenario: ScenarioDefinition,
                                                   performance_metrics: Dict[str, float],
                                                   risk_metrics: Dict[str, float]) -> Dict[str, Any]:
        """Analyze template-specific performance under scenario"""
        
        analysis = {
            'template_category': template.metadata.category.value,
            'scenario_type': scenario.scenario_type.value,
            'category_relative_performance': 0.0,  # Placeholder
            'inheritance_resilience': {}
        }
        
        # Analyze inheritance resilience
        for parent_id in template.metadata.parent_templates:
            # Simplified analysis - would compare with actual parent performance
            resilience_score = np.random.uniform(0.8, 1.2)  # Mock resilience score
            analysis['inheritance_resilience'][parent_id] = resilience_score
        
        return analysis
    
    def _calculate_monte_carlo_statistics(self, template_id: str, results: List[ScenarioResult]):
        """Calculate Monte Carlo statistics for template"""
        
        if not results:
            return
        
        returns = [r.scenario_return for r in results]
        sharpe_ratios = [r.scenario_sharpe for r in results]
        max_drawdowns = [r.scenario_max_drawdown for r in results]
        
        stats = {
            'mean_return': np.mean(returns),
            'return_std': np.std(returns),
            'return_5th_percentile': np.percentile(returns, 5),
            'return_95th_percentile': np.percentile(returns, 95),
            'mean_sharpe': np.mean(sharpe_ratios),
            'worst_case_drawdown': np.max(max_drawdowns),
            'success_rate': sum(1 for r in returns if r > 0) / len(returns)
        }
        
        self.logger.info(f"Monte Carlo stats for {template_id}: {stats}")
    
    def create_scenario_suite(self, suite_name: str, scenario_ids: List[str],
                            template_filters: Dict[str, Any] = None) -> str:
        """Create a new scenario suite"""
        
        suite_id = f"suite_{uuid.uuid4().hex[:8]}"
        scenarios = [self.scenario_definitions[sid] for sid in scenario_ids if sid in self.scenario_definitions]
        
        suite = ScenarioSuite(
            suite_id=suite_id,
            name=suite_name,
            scenarios=scenarios,
            template_filters=template_filters or {}
        )
        
        self.scenario_suites[suite_id] = suite
        
        self.logger.info(f"Created scenario suite {suite_id} with {len(scenarios)} scenarios")
        return suite_id
    
    def get_scenario_summary(self) -> Dict[str, Any]:
        """Get summary of scenario testing activities"""
        
        return {
            'total_scenarios': len(self.scenario_definitions),
            'scenario_suites': len(self.scenario_suites),
            'completed_tests': len(self.scenario_results),
            'scenario_types': list(set(s.scenario_type.value for s in self.scenario_definitions.values())),
            'severity_distribution': {
                severity.value: sum(1 for s in self.scenario_definitions.values() if s.severity == severity)
                for severity in ScenarioSeverity
            }
        }
