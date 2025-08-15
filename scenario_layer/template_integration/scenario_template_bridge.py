"""
Scenario Template Bridge
=======================

Bridge component that connects legacy scenario systems with the new
template-aware infrastructure, providing migration and compatibility.

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

from strategy_templates.base import TemplateRegistry, BaseTemplate, TemplateCategory
from scenario_layer.backtesting.historical_backtesting_engine import (
    BacktestConfig, HistoricalBacktestingEngine, BacktestResult
)
from .template_backtesting_engine import (
    TemplateBacktestingEngine, TemplateBacktestConfig, TemplateBacktestResult
)

logger = logging.getLogger(__name__)

class BridgeMode(Enum):
    """Bridge operation modes"""
    LEGACY_TO_TEMPLATE = "legacy_to_template"      # Convert legacy to template
    TEMPLATE_TO_LEGACY = "template_to_legacy"      # Convert template to legacy
    PARALLEL_EXECUTION = "parallel_execution"      # Run both systems
    VALIDATION_MODE = "validation_mode"            # Compare results

@dataclass
class LegacyScenarioDefinition:
    """Legacy scenario definition for migration"""
    scenario_name: str
    config_path: str
    strategy_parameters: Dict[str, Any]
    backtest_config: BacktestConfig
    expected_results: Optional[Dict[str, float]] = None

@dataclass
class BridgeConfig:
    """Configuration for scenario template bridge"""
    bridge_mode: BridgeMode
    
    # Migration settings
    auto_convert_legacy: bool = True
    preserve_legacy_behavior: bool = True
    validation_threshold: float = 0.05  # 5% tolerance for result differences
    
    # Template mapping
    legacy_to_template_mapping: Dict[str, str] = field(default_factory=dict)
    default_template_category: TemplateCategory = TemplateCategory.BASE
    
    # Execution settings
    run_legacy_validation: bool = True
    generate_migration_report: bool = True

@dataclass
class BridgeResult:
    """Result from bridge operation"""
    bridge_mode: BridgeMode
    operation_id: str
    
    # Results from both systems
    legacy_results: Optional[Dict[str, Any]] = None
    template_results: Optional[Dict[str, Any]] = None
    
    # Comparison analysis
    results_comparison: Optional[Dict[str, Any]] = None
    migration_analysis: Optional[Dict[str, Any]] = None
    
    # Performance metrics
    execution_time_legacy: float = 0.0
    execution_time_template: float = 0.0
    performance_improvement: float = 0.0
    
    # Validation results
    validation_passed: bool = True
    validation_details: Dict[str, Any] = field(default_factory=dict)

class ScenarioTemplateBridge:
    """
    Bridge system for seamless integration between legacy scenario testing
    and the new template-aware infrastructure.
    """
    
    def __init__(self, template_registry: TemplateRegistry,
                 template_backtesting_engine: TemplateBacktestingEngine,
                 legacy_backtesting_engine: Optional[HistoricalBacktestingEngine] = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.template_registry = template_registry
        self.template_backtesting_engine = template_backtesting_engine
        self.legacy_backtesting_engine = legacy_backtesting_engine
        
        # Bridge state
        self.bridge_operations: Dict[str, BridgeResult] = {}
        self.legacy_scenarios: Dict[str, LegacyScenarioDefinition] = {}
        self.migration_mappings: Dict[str, str] = {}
        
        # Performance tracking
        self.bridge_history: List[Dict[str, Any]] = []
        
        self.logger.info("ScenarioTemplateBridge initialized")
    
    async def execute_bridge_operation(self, config: BridgeConfig,
                                     scenarios: List[str],
                                     templates: List[str]) -> BridgeResult:
        """
        Execute bridge operation between legacy and template systems
        """
        try:
            operation_id = f"bridge_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.logger.info(f"Starting bridge operation {operation_id}")
            self.logger.info(f"Mode: {config.bridge_mode.value}")
            
            result = BridgeResult(
                bridge_mode=config.bridge_mode,
                operation_id=operation_id
            )
            
            if config.bridge_mode == BridgeMode.LEGACY_TO_TEMPLATE:
                result = await self._execute_legacy_to_template(config, scenarios, templates, result)
            
            elif config.bridge_mode == BridgeMode.TEMPLATE_TO_LEGACY:
                result = await self._execute_template_to_legacy(config, scenarios, templates, result)
            
            elif config.bridge_mode == BridgeMode.PARALLEL_EXECUTION:
                result = await self._execute_parallel_mode(config, scenarios, templates, result)
            
            elif config.bridge_mode == BridgeMode.VALIDATION_MODE:
                result = await self._execute_validation_mode(config, scenarios, templates, result)
            
            # Store bridge operation result
            self.bridge_operations[operation_id] = result
            
            # Update bridge history
            self.bridge_history.append({
                'operation_id': operation_id,
                'bridge_mode': config.bridge_mode.value,
                'timestamp': datetime.now(),
                'scenarios_count': len(scenarios),
                'templates_count': len(templates),
                'validation_passed': result.validation_passed
            })
            
            self.logger.info(f"Bridge operation {operation_id} completed")
            return result
            
        except Exception as e:
            self.logger.error(f"Bridge operation failed: {e}")
            raise
    
    async def _execute_legacy_to_template(self, config: BridgeConfig,
                                        scenarios: List[str], templates: List[str],
                                        result: BridgeResult) -> BridgeResult:
        """Execute legacy to template migration"""
        
        self.logger.info("Executing legacy to template migration")
        
        # Convert legacy scenarios to template format
        converted_templates = []
        for scenario_name in scenarios:
            if scenario_name in self.legacy_scenarios:
                legacy_scenario = self.legacy_scenarios[scenario_name]
                
                # Convert to template
                template_id = await self._convert_legacy_to_template(
                    legacy_scenario, config
                )
                if template_id:
                    converted_templates.append(template_id)
        
        # Run template-based backtesting
        if converted_templates:
            start_time = datetime.now()
            
            template_config = TemplateBacktestConfig(
                template_ids=converted_templates,
                base_config=self._create_default_backtest_config()
            )
            
            template_results = await self.template_backtesting_engine.run_template_backtest(
                template_config
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            result.execution_time_template = execution_time
            result.template_results = template_results
        
        # Generate migration analysis
        result.migration_analysis = await self._analyze_migration_quality(
            scenarios, converted_templates, config
        )
        
        return result
    
    async def _execute_template_to_legacy(self, config: BridgeConfig,
                                        scenarios: List[str], templates: List[str],
                                        result: BridgeResult) -> BridgeResult:
        """Execute template to legacy conversion"""
        
        self.logger.info("Executing template to legacy conversion")
        
        # Convert templates to legacy format
        legacy_configs = []
        for template_id in templates:
            legacy_config = await self._convert_template_to_legacy(template_id, config)
            if legacy_config:
                legacy_configs.append(legacy_config)
        
        # Run legacy backtesting (if legacy engine available)
        if self.legacy_backtesting_engine and legacy_configs:
            start_time = datetime.now()
            
            legacy_results = {}
            for i, legacy_config in enumerate(legacy_configs):
                try:
                    # This would run the legacy backtesting engine
                    # For now, we'll simulate the results
                    legacy_result = await self._simulate_legacy_backtest(legacy_config)
                    legacy_results[f"legacy_{i}"] = legacy_result
                except Exception as e:
                    self.logger.error(f"Legacy backtest failed: {e}")
            
            execution_time = (datetime.now() - start_time).total_seconds()
            result.execution_time_legacy = execution_time
            result.legacy_results = legacy_results
        
        return result
    
    async def _execute_parallel_mode(self, config: BridgeConfig,
                                   scenarios: List[str], templates: List[str],
                                   result: BridgeResult) -> BridgeResult:
        """Execute both systems in parallel for comparison"""
        
        self.logger.info("Executing parallel mode")
        
        # Run both legacy and template systems
        legacy_task = None
        template_task = None
        
        # Start template execution
        if templates:
            template_config = TemplateBacktestConfig(
                template_ids=templates,
                base_config=self._create_default_backtest_config()
            )
            template_start = datetime.now()
            template_results = await self.template_backtesting_engine.run_template_backtest(
                template_config
            )
            result.execution_time_template = (datetime.now() - template_start).total_seconds()
            result.template_results = template_results
        
        # Simulate legacy execution
        if scenarios and self.legacy_backtesting_engine:
            legacy_start = datetime.now()
            legacy_results = {}
            
            for scenario_name in scenarios:
                if scenario_name in self.legacy_scenarios:
                    legacy_scenario = self.legacy_scenarios[scenario_name]
                    legacy_result = await self._simulate_legacy_backtest(legacy_scenario)
                    legacy_results[scenario_name] = legacy_result
            
            result.execution_time_legacy = (datetime.now() - legacy_start).total_seconds()
            result.legacy_results = legacy_results
        
        # Compare results
        if result.legacy_results and result.template_results:
            result.results_comparison = await self._compare_results(
                result.legacy_results, result.template_results, config
            )
            
            # Calculate performance improvement
            if result.execution_time_legacy > 0:
                result.performance_improvement = (
                    (result.execution_time_legacy - result.execution_time_template) /
                    result.execution_time_legacy
                )
        
        return result
    
    async def _execute_validation_mode(self, config: BridgeConfig,
                                     scenarios: List[str], templates: List[str],
                                     result: BridgeResult) -> BridgeResult:
        """Execute validation comparing both systems"""
        
        self.logger.info("Executing validation mode")
        
        # Run parallel execution first
        result = await self._execute_parallel_mode(config, scenarios, templates, result)
        
        # Perform detailed validation
        if result.results_comparison:
            validation_results = await self._perform_detailed_validation(
                result.results_comparison, config
            )
            
            result.validation_passed = validation_results['overall_validation']
            result.validation_details = validation_results
        
        return result
    
    async def _convert_legacy_to_template(self, legacy_scenario: LegacyScenarioDefinition,
                                        config: BridgeConfig) -> Optional[str]:
        """Convert legacy scenario to template format"""
        
        try:
            # Extract template information from legacy scenario
            template_id = f"migrated_{legacy_scenario.scenario_name}"
            
            # Create template metadata
            template_metadata = {
                'template_id': template_id,
                'name': f"Migrated: {legacy_scenario.scenario_name}",
                'description': f"Auto-migrated from legacy scenario {legacy_scenario.scenario_name}",
                'category': config.default_template_category,
                'version': '1.0.0',
                'tags': ['migrated', 'legacy'],
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
            
            # Convert strategy parameters to template format
            template_parameters = self._convert_legacy_parameters(
                legacy_scenario.strategy_parameters
            )
            
            # Create template structure
            template_data = {
                'metadata': template_metadata,
                'parameters': template_parameters,
                'components': self._extract_legacy_components(legacy_scenario),
                'constraints': self._extract_legacy_constraints(legacy_scenario)
            }
            
            # Register template in registry (simplified registration)
            # In practice, this would use the full template registration process
            self.migration_mappings[legacy_scenario.scenario_name] = template_id
            
            self.logger.info(f"Converted legacy scenario {legacy_scenario.scenario_name} to template {template_id}")
            return template_id
            
        except Exception as e:
            self.logger.error(f"Failed to convert legacy scenario {legacy_scenario.scenario_name}: {e}")
            return None
    
    async def _convert_template_to_legacy(self, template_id: str,
                                        config: BridgeConfig) -> Optional[Dict[str, Any]]:
        """Convert template to legacy format"""
        
        try:
            template = self.template_registry.get_template(template_id)
            if not template:
                return None
            
            # Extract legacy-compatible configuration
            legacy_config = {
                'strategy_name': template.metadata.name,
                'strategy_parameters': self._convert_template_parameters_to_legacy(
                    template.parameters
                ),
                'backtest_config': self._create_default_backtest_config(),
                'template_source': template_id
            }
            
            self.logger.info(f"Converted template {template_id} to legacy format")
            return legacy_config
            
        except Exception as e:
            self.logger.error(f"Failed to convert template {template_id} to legacy: {e}")
            return None
    
    def _convert_legacy_parameters(self, legacy_params: Dict[str, Any]) -> Dict[str, Any]:
        """Convert legacy parameters to template parameter format"""
        
        # Map common legacy parameter names to template format
        parameter_mapping = {
            'lookback_period': 'signal_lookback',
            'position_size': 'position_sizing.base_size',
            'stop_loss': 'risk_management.stop_loss_pct',
            'take_profit': 'risk_management.take_profit_pct',
            'rebalance_freq': 'execution.rebalance_frequency'
        }
        
        converted_params = {}
        
        for legacy_key, legacy_value in legacy_params.items():
            # Use mapped key if available, otherwise use original key
            template_key = parameter_mapping.get(legacy_key, legacy_key)
            converted_params[template_key] = legacy_value
        
        return converted_params
    
    def _extract_legacy_components(self, legacy_scenario: LegacyScenarioDefinition) -> Dict[str, Any]:
        """Extract component definitions from legacy scenario"""
        
        # Default component structure for migrated strategies
        components = {
            'signal_generator': {
                'type': 'technical_indicators',
                'config': {
                    'indicators': ['momentum', 'mean_reversion'],
                    'lookback_period': legacy_scenario.strategy_parameters.get('lookback_period', 20)
                }
            },
            'risk_manager': {
                'type': 'basic_risk_manager',
                'config': {
                    'max_position_size': legacy_scenario.strategy_parameters.get('position_size', 0.1),
                    'stop_loss_pct': legacy_scenario.strategy_parameters.get('stop_loss', 0.05)
                }
            },
            'execution_engine': {
                'type': 'market_orders',
                'config': {
                    'order_type': 'market',
                    'execution_delay': 0
                }
            }
        }
        
        return components
    
    def _extract_legacy_constraints(self, legacy_scenario: LegacyScenarioDefinition) -> Dict[str, Any]:
        """Extract constraints from legacy scenario"""
        
        constraints = {
            'risk_limits': {
                'max_drawdown': 0.20,
                'max_leverage': 2.0,
                'sector_concentration': 0.30
            },
            'execution_constraints': {
                'min_order_size': 100,
                'max_order_size': 10000,
                'trading_hours': 'market_hours'
            }
        }
        
        return constraints
    
    def _convert_template_parameters_to_legacy(self, template_params: Dict[str, Any]) -> Dict[str, Any]:
        """Convert template parameters to legacy format"""
        
        # Reverse mapping from template to legacy format
        legacy_mapping = {
            'signal_lookback': 'lookback_period',
            'position_sizing.base_size': 'position_size',
            'risk_management.stop_loss_pct': 'stop_loss',
            'risk_management.take_profit_pct': 'take_profit',
            'execution.rebalance_frequency': 'rebalance_freq'
        }
        
        legacy_params = {}
        
        for template_key, template_value in template_params.items():
            # Use reverse mapped key if available
            legacy_key = legacy_mapping.get(template_key, template_key)
            legacy_params[legacy_key] = template_value
        
        return legacy_params
    
    async def _simulate_legacy_backtest(self, legacy_config: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate legacy backtesting results"""
        
        # Simulate legacy backtest results
        # In practice, this would call the actual legacy backtesting engine
        
        return {
            'total_return': np.random.uniform(0.05, 0.15),
            'sharpe_ratio': np.random.uniform(0.8, 1.5),
            'max_drawdown': np.random.uniform(0.08, 0.18),
            'volatility': np.random.uniform(0.12, 0.20),
            'win_rate': np.random.uniform(0.45, 0.65),
            'num_trades': np.random.randint(50, 200),
            'execution_time': np.random.uniform(10, 30)  # seconds
        }
    
    async def _compare_results(self, legacy_results: Dict[str, Any],
                             template_results: Dict[str, Any],
                             config: BridgeConfig) -> Dict[str, Any]:
        """Compare results between legacy and template systems"""
        
        comparison = {
            'performance_metrics': {},
            'execution_metrics': {},
            'result_differences': {},
            'correlation_analysis': {}
        }
        
        # Extract comparable metrics
        legacy_metrics = self._extract_comparable_metrics(legacy_results)
        template_metrics = self._extract_comparable_metrics(template_results)
        
        # Compare performance metrics
        for metric in ['total_return', 'sharpe_ratio', 'max_drawdown', 'volatility']:
            if metric in legacy_metrics and metric in template_metrics:
                legacy_val = legacy_metrics[metric]
                template_val = template_metrics[metric]
                
                difference = abs(legacy_val - template_val)
                relative_diff = difference / max(abs(legacy_val), 0.001)
                
                comparison['performance_metrics'][metric] = {
                    'legacy_value': legacy_val,
                    'template_value': template_val,
                    'absolute_difference': difference,
                    'relative_difference': relative_diff,
                    'within_tolerance': relative_diff <= config.validation_threshold
                }
        
        # Compare execution metrics
        comparison['execution_metrics'] = {
            'legacy_execution_time': self._get_avg_execution_time(legacy_results),
            'template_execution_time': self._get_avg_execution_time(template_results),
            'performance_improvement': self._calculate_performance_improvement(
                legacy_results, template_results
            )
        }
        
        return comparison
    
    def _extract_comparable_metrics(self, results: Dict[str, Any]) -> Dict[str, float]:
        """Extract comparable metrics from results"""
        
        metrics = {}
        
        # Handle both legacy and template result formats
        if isinstance(results, dict):
            for key, value in results.items():
                if isinstance(value, dict):
                    # Template results format
                    if hasattr(value, 'total_return'):
                        metrics['total_return'] = value.total_return
                        metrics['sharpe_ratio'] = value.sharpe_ratio
                        metrics['max_drawdown'] = value.max_drawdown
                        metrics['volatility'] = value.volatility
                    elif 'total_return' in value:
                        # Dictionary format
                        metrics.update({k: v for k, v in value.items() 
                                      if isinstance(v, (int, float))})
                elif isinstance(value, (int, float)):
                    # Direct metric
                    metrics[key] = value
        
        return metrics
    
    def _get_avg_execution_time(self, results: Dict[str, Any]) -> float:
        """Get average execution time from results"""
        
        execution_times = []
        
        for value in results.values():
            if isinstance(value, dict) and 'execution_time' in value:
                execution_times.append(value['execution_time'])
        
        return np.mean(execution_times) if execution_times else 0.0
    
    def _calculate_performance_improvement(self, legacy_results: Dict[str, Any],
                                         template_results: Dict[str, Any]) -> float:
        """Calculate performance improvement from template system"""
        
        legacy_time = self._get_avg_execution_time(legacy_results)
        template_time = self._get_avg_execution_time(template_results)
        
        if legacy_time > 0:
            return (legacy_time - template_time) / legacy_time
        
        return 0.0
    
    async def _perform_detailed_validation(self, comparison: Dict[str, Any],
                                         config: BridgeConfig) -> Dict[str, Any]:
        """Perform detailed validation of results"""
        
        validation = {
            'overall_validation': True,
            'metric_validations': {},
            'validation_summary': {},
            'failed_validations': []
        }
        
        # Validate each performance metric
        if 'performance_metrics' in comparison:
            for metric, details in comparison['performance_metrics'].items():
                within_tolerance = details.get('within_tolerance', False)
                validation['metric_validations'][metric] = within_tolerance
                
                if not within_tolerance:
                    validation['overall_validation'] = False
                    validation['failed_validations'].append({
                        'metric': metric,
                        'legacy_value': details['legacy_value'],
                        'template_value': details['template_value'],
                        'difference': details['relative_difference']
                    })
        
        # Validation summary
        total_metrics = len(validation['metric_validations'])
        passed_metrics = sum(validation['metric_validations'].values())
        
        validation['validation_summary'] = {
            'total_metrics': total_metrics,
            'passed_metrics': passed_metrics,
            'failed_metrics': total_metrics - passed_metrics,
            'success_rate': passed_metrics / max(total_metrics, 1)
        }
        
        return validation
    
    def _create_default_backtest_config(self) -> BacktestConfig:
        """Create default backtest configuration"""
        
        from scenario_layer.backtesting.historical_backtesting_engine import TimeRange
        
        time_range = TimeRange(
            start_date=datetime.now() - timedelta(days=252),
            end_date=datetime.now() - timedelta(days=1)
        )
        
        return BacktestConfig(
            time_range=time_range,
            initial_capital=100000.0,
            symbols=['AAPL', 'GOOGL', 'MSFT'],
            save_trades=True,
            save_positions=True
        )
    
    async def _analyze_migration_quality(self, scenarios: List[str],
                                       converted_templates: List[str],
                                       config: BridgeConfig) -> Dict[str, Any]:
        """Analyze the quality of migration from legacy to template"""
        
        analysis = {
            'migration_success_rate': len(converted_templates) / max(len(scenarios), 1),
            'converted_templates': converted_templates,
            'failed_conversions': [s for s in scenarios if s not in self.migration_mappings],
            'migration_recommendations': []
        }
        
        # Generate recommendations based on migration results
        if analysis['migration_success_rate'] < 1.0:
            analysis['migration_recommendations'].append(
                "Review failed conversions for complex legacy scenarios"
            )
        
        if analysis['migration_success_rate'] > 0.8:
            analysis['migration_recommendations'].append(
                "Migration successful - consider deprecating legacy scenarios"
            )
        
        return analysis
    
    def register_legacy_scenario(self, scenario: LegacyScenarioDefinition):
        """Register a legacy scenario for bridge operations"""
        
        self.legacy_scenarios[scenario.scenario_name] = scenario
        self.logger.info(f"Registered legacy scenario: {scenario.scenario_name}")
    
    def get_bridge_summary(self) -> Dict[str, Any]:
        """Get summary of bridge operations"""
        
        return {
            'total_operations': len(self.bridge_operations),
            'legacy_scenarios_registered': len(self.legacy_scenarios),
            'migration_mappings': len(self.migration_mappings),
            'recent_operations': len([op for op in self.bridge_history 
                                    if (datetime.now() - op['timestamp']).days <= 7]),
            'validation_success_rate': np.mean([op['validation_passed'] for op in self.bridge_history]) 
                                     if self.bridge_history else 0.0,
            'operation_types': {
                mode.value: sum(1 for op in self.bridge_history if op['bridge_mode'] == mode.value)
                for mode in BridgeMode
            }
        }
