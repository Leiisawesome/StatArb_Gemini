"""
Template-Aware Backtesting Engine
=================================

Advanced backtesting engine that integrates with the hybrid template system,
supporting template inheritance, category-aware testing, and performance analytics.

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

from strategy_templates.base import TemplateRegistry, BaseTemplate, TemplateCategory
from strategy_layer.template_integration import TemplateStrategyManager, TemplatePerformanceTracker
from scenario_layer.backtesting.historical_backtesting_engine import (
    BacktestConfig, TimeRange, DataReplayMode, BacktestStatus
)

logger = logging.getLogger(__name__)

class TemplateBacktestMode(Enum):
    """Template-specific backtesting modes"""
    SINGLE_TEMPLATE = "single_template"           # Test one template
    INHERITANCE_CHAIN = "inheritance_chain"       # Test template + all parents
    CATEGORY_COMPARISON = "category_comparison"   # Compare templates in category
    CROSS_CATEGORY = "cross_category"            # Test across multiple categories
    ENSEMBLE_TESTING = "ensemble_testing"        # Test composite templates

@dataclass
class TemplateBacktestConfig:
    """Configuration for template-aware backtesting"""
    # Template settings
    template_ids: List[str]
    base_config: BacktestConfig
    template_mode: TemplateBacktestMode = TemplateBacktestMode.SINGLE_TEMPLATE
    category_filter: Optional[TemplateCategory] = None
    inheritance_depth: int = -1  # -1 for unlimited depth
    
    # Backtesting parameters
    custom_parameters: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # per template
    
    # Template-specific settings
    enable_inheritance_analysis: bool = True
    enable_category_benchmarking: bool = True
    enable_performance_comparison: bool = True
    
    # Advanced features
    parameter_sensitivity_analysis: bool = False
    walk_forward_by_template: bool = False
    cross_validation_folds: int = 0  # 0 to disable

@dataclass
class TemplateBacktestResult:
    """Results from template-aware backtesting"""
    backtest_id: str
    template_id: str
    template_category: TemplateCategory
    config: TemplateBacktestConfig
    
    # Performance metrics
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    
    # Template-specific metrics
    inheritance_performance: Dict[str, float]  # Performance vs parent templates
    category_rank: int
    category_percentile: float
    
    # Detailed results
    trades: List[Dict[str, Any]] = field(default_factory=list)
    positions: pd.DataFrame = field(default=None)
    equity_curve: pd.Series = field(default=None)
    metrics_timeline: pd.DataFrame = field(default=None)
    
    # Analysis results
    performance_attribution: Dict[str, Any] = field(default_factory=dict)
    risk_decomposition: Dict[str, Any] = field(default_factory=dict)
    execution_stats: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization"""
        return {
            'backtest_id': self.backtest_id,
            'template_id': self.template_id,
            'template_category': self.template_category.value,
            'total_return': self.total_return,
            'annualized_return': self.annualized_return,
            'volatility': self.volatility,
            'sharpe_ratio': self.sharpe_ratio,
            'max_drawdown': self.max_drawdown,
            'win_rate': self.win_rate,
            'inheritance_performance': self.inheritance_performance,
            'category_rank': self.category_rank,
            'category_percentile': self.category_percentile,
            'performance_attribution': self.performance_attribution,
            'risk_decomposition': self.risk_decomposition,
            'execution_stats': self.execution_stats
        }

@dataclass
class CategoryComparisonResult:
    """Results from category-based template comparison"""
    category: TemplateCategory
    template_results: List[TemplateBacktestResult]
    
    # Category statistics
    avg_return: float
    avg_volatility: float
    avg_sharpe: float
    best_template: str
    worst_template: str
    
    # Rankings
    template_rankings: List[Tuple[str, float]]  # (template_id, score)
    
    def get_top_templates(self, n: int = 5) -> List[Tuple[str, float]]:
        """Get top N templates by performance"""
        return self.template_rankings[:n]

class TemplateBacktestingEngine:
    """
    Advanced backtesting engine with template-aware capabilities,
    inheritance analysis, and category-based performance comparison.
    """
    
    def __init__(self, template_registry: TemplateRegistry,
                 strategy_manager: TemplateStrategyManager,
                 performance_tracker: TemplatePerformanceTracker):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.template_registry = template_registry
        self.strategy_manager = strategy_manager
        self.performance_tracker = performance_tracker
        
        # Backtesting state
        self.active_backtests: Dict[str, TemplateBacktestConfig] = {}
        self.backtest_results: Dict[str, TemplateBacktestResult] = {}
        self.category_comparisons: Dict[str, CategoryComparisonResult] = {}
        
        # Performance tracking
        self.backtest_history: List[Dict[str, Any]] = []
        
        # Market data simulation
        self.market_data_cache: Dict[str, pd.DataFrame] = {}
        
        self.logger.info("TemplateBacktestingEngine initialized")
    
    async def run_template_backtest(self, config: TemplateBacktestConfig) -> Dict[str, TemplateBacktestResult]:
        """
        Run comprehensive template-aware backtesting
        """
        try:
            backtest_id = f"backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.active_backtests[backtest_id] = config
            
            self.logger.info(f"Starting template backtest {backtest_id}")
            self.logger.info(f"Mode: {config.template_mode.value}, Templates: {len(config.template_ids)}")
            
            results = {}
            
            if config.template_mode == TemplateBacktestMode.SINGLE_TEMPLATE:
                results = await self._run_single_template_backtests(config, backtest_id)
            
            elif config.template_mode == TemplateBacktestMode.INHERITANCE_CHAIN:
                results = await self._run_inheritance_chain_backtests(config, backtest_id)
            
            elif config.template_mode == TemplateBacktestMode.CATEGORY_COMPARISON:
                results = await self._run_category_comparison_backtests(config, backtest_id)
            
            elif config.template_mode == TemplateBacktestMode.CROSS_CATEGORY:
                results = await self._run_cross_category_backtests(config, backtest_id)
            
            elif config.template_mode == TemplateBacktestMode.ENSEMBLE_TESTING:
                results = await self._run_ensemble_backtests(config, backtest_id)
            
            # Store results
            for template_id, result in results.items():
                self.backtest_results[f"{backtest_id}_{template_id}"] = result
            
            # Update performance tracking
            await self._update_backtest_performance_tracking(results, config)
            
            self.logger.info(f"Template backtest {backtest_id} completed with {len(results)} results")
            return results
            
        except Exception as e:
            self.logger.error(f"Template backtest failed: {e}")
            raise
        finally:
            if backtest_id in self.active_backtests:
                del self.active_backtests[backtest_id]
    
    async def _run_single_template_backtests(self, config: TemplateBacktestConfig,
                                           backtest_id: str) -> Dict[str, TemplateBacktestResult]:
        """Run backtests for individual templates"""
        results = {}
        
        for template_id in config.template_ids:
            self.logger.info(f"Running backtest for template {template_id}")
            
            # Get template
            template = self.template_registry.get_template(template_id)
            if not template:
                self.logger.warning(f"Template {template_id} not found")
                continue
            
            # Create strategy instance
            instance_id = self.strategy_manager.create_strategy_instance(
                template_id,
                custom_parameters=config.custom_parameters.get(template_id, {})
            )
            
            try:
                # Run backtest simulation
                result = await self._simulate_backtest(
                    template, instance_id, config.base_config, backtest_id
                )
                
                # Add template-specific analysis
                result = await self._enhance_with_template_analysis(result, template, config)
                
                results[template_id] = result
                
            except Exception as e:
                self.logger.error(f"Backtest failed for template {template_id}: {e}")
            
            finally:
                # Clean up strategy instance
                try:
                    self.strategy_manager.stop_strategy_instance(instance_id)
                except:
                    pass
        
        return results
    
    async def _run_inheritance_chain_backtests(self, config: TemplateBacktestConfig,
                                             backtest_id: str) -> Dict[str, TemplateBacktestResult]:
        """Run backtests for template inheritance chains"""
        results = {}
        
        for template_id in config.template_ids:
            # Get inheritance chain
            inheritance_chain = self._get_inheritance_chain(template_id, config.inheritance_depth)
            
            self.logger.info(f"Running inheritance chain backtest for {template_id}: {len(inheritance_chain)} templates")
            
            for chain_template_id in inheritance_chain:
                template = self.template_registry.get_template(chain_template_id)
                if not template:
                    continue
                
                instance_id = self.strategy_manager.create_strategy_instance(
                    chain_template_id,
                    custom_parameters=config.custom_parameters.get(chain_template_id, {})
                )
                
                try:
                    result = await self._simulate_backtest(
                        template, instance_id, config.base_config, backtest_id
                    )
                    
                    # Add inheritance analysis
                    result = await self._analyze_inheritance_performance(
                        result, template, inheritance_chain
                    )
                    
                    results[chain_template_id] = result
                    
                except Exception as e:
                    self.logger.error(f"Inheritance backtest failed for {chain_template_id}: {e}")
                
                finally:
                    try:
                        self.strategy_manager.stop_strategy_instance(instance_id)
                    except:
                        pass
        
        return results
    
    async def _run_category_comparison_backtests(self, config: TemplateBacktestConfig,
                                                backtest_id: str) -> Dict[str, TemplateBacktestResult]:
        """Run backtests for category comparison"""
        results = {}
        
        # Get templates by category
        if config.category_filter:
            category_templates = self.template_registry.search_templates(
                category=config.category_filter
            )
        else:
            category_templates = [
                self.template_registry.get_template(tid) for tid in config.template_ids
            ]
        
        category_templates = [t for t in category_templates if t is not None]
        
        self.logger.info(f"Running category comparison for {len(category_templates)} templates")
        
        # Run backtests for all templates in category
        for template in category_templates:
            instance_id = self.strategy_manager.create_strategy_instance(
                template.metadata.template_id,
                custom_parameters=config.custom_parameters.get(template.metadata.template_id, {})
            )
            
            try:
                result = await self._simulate_backtest(
                    template, instance_id, config.base_config, backtest_id
                )
                
                results[template.metadata.template_id] = result
                
            except Exception as e:
                self.logger.error(f"Category backtest failed for {template.metadata.template_id}: {e}")
            
            finally:
                try:
                    self.strategy_manager.stop_strategy_instance(instance_id)
                except:
                    pass
        
        # Perform category analysis
        if results:
            await self._analyze_category_performance(results, config.category_filter or TemplateCategory.BASE)
        
        return results
    
    async def _run_cross_category_backtests(self, config: TemplateBacktestConfig,
                                          backtest_id: str) -> Dict[str, TemplateBacktestResult]:
        """Run backtests across multiple categories"""
        results = {}
        
        # Group templates by category
        category_groups = defaultdict(list)
        for template_id in config.template_ids:
            template = self.template_registry.get_template(template_id)
            if template:
                category_groups[template.metadata.category].append(template)
        
        self.logger.info(f"Running cross-category backtest across {len(category_groups)} categories")
        
        # Run backtests for each category
        for category, templates in category_groups.items():
            self.logger.info(f"Testing {len(templates)} templates in category {category.value}")
            
            for template in templates:
                instance_id = self.strategy_manager.create_strategy_instance(
                    template.metadata.template_id,
                    custom_parameters=config.custom_parameters.get(template.metadata.template_id, {})
                )
                
                try:
                    result = await self._simulate_backtest(
                        template, instance_id, config.base_config, backtest_id
                    )
                    
                    # Add cross-category analysis
                    result = await self._enhance_with_cross_category_analysis(
                        result, template, category_groups
                    )
                    
                    results[template.metadata.template_id] = result
                    
                except Exception as e:
                    self.logger.error(f"Cross-category backtest failed for {template.metadata.template_id}: {e}")
                
                finally:
                    try:
                        self.strategy_manager.stop_strategy_instance(instance_id)
                    except:
                        pass
        
        return results
    
    async def _run_ensemble_backtests(self, config: TemplateBacktestConfig,
                                    backtest_id: str) -> Dict[str, TemplateBacktestResult]:
        """Run backtests for ensemble/composite templates"""
        results = {}
        
        # Filter for composite templates
        composite_templates = []
        for template_id in config.template_ids:
            template = self.template_registry.get_template(template_id)
            if template and template.metadata.category == TemplateCategory.COMPOSITE:
                composite_templates.append(template)
        
        self.logger.info(f"Running ensemble backtest for {len(composite_templates)} composite templates")
        
        for template in composite_templates:
            # Create multiple instances for ensemble testing
            ensemble_instances = []
            
            # Create instances for each component of the composite template
            num_ensemble_instances = min(3, len(template.metadata.parent_templates) + 1)
            
            for i in range(num_ensemble_instances):
                instance_id = self.strategy_manager.create_strategy_instance(
                    template.metadata.template_id,
                    instance_name=f"{template.metadata.template_id}_ensemble_{i}",
                    custom_parameters=config.custom_parameters.get(template.metadata.template_id, {})
                )
                ensemble_instances.append(instance_id)
            
            try:
                # Run ensemble simulation
                result = await self._simulate_ensemble_backtest(
                    template, ensemble_instances, config.base_config, backtest_id
                )
                
                results[template.metadata.template_id] = result
                
            except Exception as e:
                self.logger.error(f"Ensemble backtest failed for {template.metadata.template_id}: {e}")
            
            finally:
                # Clean up ensemble instances
                for instance_id in ensemble_instances:
                    try:
                        self.strategy_manager.stop_strategy_instance(instance_id)
                    except:
                        pass
        
        return results
    
    async def _simulate_backtest(self, template: BaseTemplate, instance_id: str,
                               base_config: BacktestConfig, backtest_id: str) -> TemplateBacktestResult:
        """Simulate backtesting for a template"""
        
        # Generate synthetic market data for simulation
        market_data = self._generate_market_data(base_config)
        
        # Initialize tracking variables
        equity_curve = []
        trades = []
        positions = []
        portfolio_value = base_config.initial_capital
        current_positions = {}
        
        # Get time series for simulation
        time_series = self._generate_time_series(base_config.time_range)
        
        total_executions = 0
        successful_executions = 0
        
        # Simulate strategy execution over time period
        for timestamp in time_series[::max(1, len(time_series) // 100)]:  # Sample 100 points
            try:
                # Create market snapshot
                market_snapshot = self._get_market_snapshot(market_data, timestamp, base_config.symbols)
                
                # Execute strategy
                result = self.strategy_manager.execute_strategy_instance(instance_id, market_snapshot)
                total_executions += 1
                
                if not result.errors:
                    successful_executions += 1
                    
                    # Process signals and update positions
                    new_trades, updated_positions = self._process_strategy_signals(
                        result, current_positions, portfolio_value, timestamp, base_config
                    )
                    
                    trades.extend(new_trades)
                    current_positions.update(updated_positions)
                
                # Update portfolio value
                portfolio_value = self._calculate_portfolio_value(
                    current_positions, market_snapshot, base_config.initial_capital
                )
                
                equity_curve.append({
                    'timestamp': timestamp,
                    'portfolio_value': portfolio_value,
                    'positions': len(current_positions)
                })
                
                # Store position snapshot
                positions.append({
                    'timestamp': timestamp,
                    'positions': current_positions.copy(),
                    'portfolio_value': portfolio_value
                })
                
            except Exception as e:
                self.logger.debug(f"Simulation step failed: {e}")
                continue
        
        # Calculate performance metrics
        performance_metrics = self._calculate_performance_metrics(
            equity_curve, trades, base_config.initial_capital
        )
        
        # Create result
        result = TemplateBacktestResult(
            backtest_id=f"{backtest_id}_{template.metadata.template_id}",
            template_id=template.metadata.template_id,
            template_category=template.metadata.category,
            config=None,  # Will be set by caller
            
            # Performance metrics
            total_return=performance_metrics['total_return'],
            annualized_return=performance_metrics['annualized_return'],
            volatility=performance_metrics['volatility'],
            sharpe_ratio=performance_metrics['sharpe_ratio'],
            max_drawdown=performance_metrics['max_drawdown'],
            win_rate=performance_metrics['win_rate'],
            
            # Template-specific metrics (will be enhanced)
            inheritance_performance={},
            category_rank=0,
            category_percentile=0.0,
            
            # Detailed results
            trades=trades,
            equity_curve=pd.Series([eq['portfolio_value'] for eq in equity_curve]),
            
            # Analysis results
            execution_stats={
                'total_executions': total_executions,
                'successful_executions': successful_executions,
                'success_rate': successful_executions / max(total_executions, 1),
                'total_trades': len(trades)
            }
        )
        
        return result
    
    async def _simulate_ensemble_backtest(self, template: BaseTemplate, instance_ids: List[str],
                                        base_config: BacktestConfig, backtest_id: str) -> TemplateBacktestResult:
        """Simulate ensemble backtesting with multiple instances"""
        
        # Run individual backtests for each instance
        individual_results = []
        
        for instance_id in instance_ids:
            try:
                result = await self._simulate_backtest(template, instance_id, base_config, backtest_id)
                individual_results.append(result)
            except Exception as e:
                self.logger.error(f"Ensemble member backtest failed: {e}")
        
        if not individual_results:
            raise ValueError("No successful ensemble member backtests")
        
        # Combine results for ensemble performance
        ensemble_metrics = self._combine_ensemble_results(individual_results)
        
        # Create ensemble result
        ensemble_result = TemplateBacktestResult(
            backtest_id=f"{backtest_id}_{template.metadata.template_id}_ensemble",
            template_id=template.metadata.template_id,
            template_category=template.metadata.category,
            config=None,
            
            total_return=ensemble_metrics['total_return'],
            annualized_return=ensemble_metrics['annualized_return'],
            volatility=ensemble_metrics['volatility'],
            sharpe_ratio=ensemble_metrics['sharpe_ratio'],
            max_drawdown=ensemble_metrics['max_drawdown'],
            win_rate=ensemble_metrics['win_rate'],
            
            inheritance_performance={},
            category_rank=0,
            category_percentile=0.0,
            
            execution_stats={
                'ensemble_members': len(individual_results),
                'avg_success_rate': np.mean([r.execution_stats['success_rate'] for r in individual_results]),
                'total_trades': sum(r.execution_stats['total_trades'] for r in individual_results)
            }
        )
        
        return ensemble_result
    
    def _generate_market_data(self, config: BacktestConfig) -> Dict[str, pd.DataFrame]:
        """Generate synthetic market data for backtesting simulation"""
        
        # Generate synthetic price data
        market_data = {}
        
        time_range = pd.date_range(
            start=config.time_range.start_date,
            end=config.time_range.end_date,
            freq='1H'  # Hourly data
        )
        
        for symbol in config.symbols or ['AAPL', 'GOOGL', 'MSFT', 'AMZN']:
            # Generate realistic price movements
            initial_price = np.random.uniform(50, 300)
            returns = np.random.normal(0.0001, 0.02, len(time_range))  # Small positive drift, 2% volatility
            
            prices = [initial_price]
            for ret in returns[1:]:
                prices.append(prices[-1] * (1 + ret))
            
            volumes = np.random.lognormal(12, 1, len(time_range))  # Log-normal volume distribution
            
            df = pd.DataFrame({
                'timestamp': time_range,
                'symbol': symbol,
                'price': prices,
                'volume': volumes,
                'high': [p * np.random.uniform(1.001, 1.02) for p in prices],
                'low': [p * np.random.uniform(0.98, 0.999) for p in prices],
                'open': prices,  # Simplified
                'close': prices
            }).set_index('timestamp')
            
            market_data[symbol] = df
        
        return market_data
    
    def _generate_time_series(self, time_range: TimeRange) -> pd.DatetimeIndex:
        """Generate time series for backtesting"""
        return pd.date_range(
            start=time_range.start_date,
            end=time_range.end_date,
            freq='1H'
        )
    
    def _get_market_snapshot(self, market_data: Dict[str, pd.DataFrame],
                           timestamp: datetime, symbols: List[str]) -> Dict[str, Any]:
        """Get market data snapshot at specific timestamp"""
        
        snapshot = {
            'timestamp': timestamp,
            'symbols': symbols or list(market_data.keys()),
            'prices': {},
            'volumes': {}
        }
        
        for symbol in snapshot['symbols']:
            if symbol in market_data:
                df = market_data[symbol]
                # Find closest timestamp
                closest_idx = df.index.get_indexer([timestamp], method='nearest')[0]
                if closest_idx < len(df):
                    row = df.iloc[closest_idx]
                    snapshot['prices'][symbol] = row['price']
                    snapshot['volumes'][symbol] = row['volume']
        
        return snapshot
    
    def _process_strategy_signals(self, result, current_positions: Dict[str, float],
                                portfolio_value: float, timestamp: datetime,
                                config: BacktestConfig) -> Tuple[List[Dict], Dict[str, float]]:
        """Process strategy signals and generate trades"""
        
        new_trades = []
        updated_positions = {}
        
        # Simple signal processing - in real implementation would be more sophisticated
        for symbol, signal in result.signals.items():
            if abs(signal) > 0.1:  # Signal threshold
                position_size = result.positions.get(symbol, 0.0)
                
                if position_size != 0:
                    # Calculate trade
                    trade = {
                        'timestamp': timestamp,
                        'symbol': symbol,
                        'signal': signal,
                        'size': position_size,
                        'side': 'BUY' if position_size > 0 else 'SELL',
                        'price': 100.0,  # Simplified pricing
                        'commission': abs(position_size * 100.0) * config.commission_rate
                    }
                    
                    new_trades.append(trade)
                    updated_positions[symbol] = current_positions.get(symbol, 0.0) + position_size
        
        return new_trades, updated_positions
    
    def _calculate_portfolio_value(self, positions: Dict[str, float],
                                 market_snapshot: Dict[str, Any], initial_capital: float) -> float:
        """Calculate current portfolio value"""
        
        total_value = initial_capital  # Start with cash
        
        for symbol, position in positions.items():
            if symbol in market_snapshot['prices']:
                price = market_snapshot['prices'][symbol]
                total_value += position * price
        
        return total_value
    
    def _calculate_performance_metrics(self, equity_curve: List[Dict],
                                     trades: List[Dict], initial_capital: float) -> Dict[str, float]:
        """Calculate performance metrics from backtest results"""
        
        if not equity_curve:
            return {
                'total_return': 0.0,
                'annualized_return': 0.0,
                'volatility': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'win_rate': 0.0
            }
        
        # Extract portfolio values
        values = [eq['portfolio_value'] for eq in equity_curve]
        
        # Calculate returns
        returns = np.diff(values) / values[:-1]
        total_return = (values[-1] - initial_capital) / initial_capital
        
        # Annualized return (assuming daily frequency)
        days = len(values)
        annualized_return = (1 + total_return) ** (252 / max(days, 1)) - 1
        
        # Volatility
        volatility = np.std(returns) * np.sqrt(252) if len(returns) > 1 else 0.0
        
        # Sharpe ratio
        sharpe_ratio = annualized_return / max(volatility, 0.001)
        
        # Max drawdown
        peak = np.maximum.accumulate(values)
        drawdown = (values - peak) / peak
        max_drawdown = np.min(drawdown)
        
        # Win rate
        if trades:
            winning_trades = sum(1 for trade in trades if trade.get('pnl', 0) > 0)
            win_rate = winning_trades / len(trades)
        else:
            win_rate = 0.0
        
        return {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': abs(max_drawdown),
            'win_rate': win_rate
        }
    
    def _combine_ensemble_results(self, individual_results: List[TemplateBacktestResult]) -> Dict[str, float]:
        """Combine individual backtest results for ensemble performance"""
        
        if not individual_results:
            return {}
        
        # Average key metrics
        metrics = {
            'total_return': np.mean([r.total_return for r in individual_results]),
            'annualized_return': np.mean([r.annualized_return for r in individual_results]),
            'volatility': np.mean([r.volatility for r in individual_results]),
            'sharpe_ratio': np.mean([r.sharpe_ratio for r in individual_results]),
            'max_drawdown': np.mean([r.max_drawdown for r in individual_results]),
            'win_rate': np.mean([r.win_rate for r in individual_results])
        }
        
        return metrics
    
    async def _enhance_with_template_analysis(self, result: TemplateBacktestResult,
                                            template: BaseTemplate, config: TemplateBacktestConfig) -> TemplateBacktestResult:
        """Enhance result with template-specific analysis"""
        
        if config.enable_inheritance_analysis and template.metadata.parent_templates:
            # Analyze inheritance performance impact
            result.inheritance_performance = await self._analyze_template_inheritance_impact(template)
        
        if config.enable_category_benchmarking:
            # Calculate category ranking
            result.category_rank, result.category_percentile = await self._calculate_category_ranking(
                template, result.sharpe_ratio
            )
        
        return result
    
    async def _analyze_inheritance_performance(self, result: TemplateBacktestResult,
                                             template: BaseTemplate, inheritance_chain: List[str]) -> TemplateBacktestResult:
        """Analyze performance impact of template inheritance"""
        
        # Compare performance with parent templates
        parent_performance = {}
        
        for parent_id in template.metadata.parent_templates:
            if parent_id in self.backtest_results:
                parent_result = self.backtest_results[parent_id]
                performance_diff = result.sharpe_ratio - parent_result.sharpe_ratio
                parent_performance[parent_id] = performance_diff
        
        result.inheritance_performance = parent_performance
        
        return result
    
    async def _enhance_with_cross_category_analysis(self, result: TemplateBacktestResult,
                                                  template: BaseTemplate, category_groups: Dict) -> TemplateBacktestResult:
        """Enhance result with cross-category analysis"""
        
        # Add cross-category performance comparison
        result.performance_attribution['cross_category'] = {
            'template_category': template.metadata.category.value,
            'relative_performance': 'analysis_pending'  # Would be calculated with actual data
        }
        
        return result
    
    async def _analyze_category_performance(self, results: Dict[str, TemplateBacktestResult],
                                          category: TemplateCategory):
        """Analyze performance within a category"""
        
        if not results:
            return
        
        # Sort results by performance
        sorted_results = sorted(results.values(), key=lambda r: r.sharpe_ratio, reverse=True)
        
        # Calculate category statistics
        returns = [r.total_return for r in sorted_results]
        sharpe_ratios = [r.sharpe_ratio for r in sorted_results]
        
        category_result = CategoryComparisonResult(
            category=category,
            template_results=sorted_results,
            avg_return=np.mean(returns),
            avg_volatility=np.mean([r.volatility for r in sorted_results]),
            avg_sharpe=np.mean(sharpe_ratios),
            best_template=sorted_results[0].template_id if sorted_results else "",
            worst_template=sorted_results[-1].template_id if sorted_results else "",
            template_rankings=[(r.template_id, r.sharpe_ratio) for r in sorted_results]
        )
        
        self.category_comparisons[f"{category.value}_comparison"] = category_result
    
    def _get_inheritance_chain(self, template_id: str, max_depth: int) -> List[str]:
        """Get inheritance chain for a template"""
        
        chain = [template_id]
        template = self.template_registry.get_template(template_id)
        
        if not template or max_depth == 0:
            return chain
        
        # Add parent templates
        for parent_id in template.metadata.parent_templates:
            if max_depth == -1 or len(chain) < max_depth:
                parent_chain = self._get_inheritance_chain(parent_id, max_depth - 1 if max_depth > 0 else -1)
                chain.extend(parent_chain)
        
        return list(dict.fromkeys(chain))  # Remove duplicates while preserving order
    
    async def _analyze_template_inheritance_impact(self, template: BaseTemplate) -> Dict[str, float]:
        """Analyze inheritance impact on template performance"""
        
        # Placeholder analysis - would compare with actual parent template performance
        inheritance_impact = {}
        
        for parent_id in template.metadata.parent_templates:
            # Simulate performance comparison
            inheritance_impact[parent_id] = np.random.uniform(-0.1, 0.2)  # Random improvement/degradation
        
        return inheritance_impact
    
    async def _calculate_category_ranking(self, template: BaseTemplate, performance_score: float) -> Tuple[int, float]:
        """Calculate template ranking within its category"""
        
        # Get all templates in same category
        category_templates = self.template_registry.search_templates(category=template.metadata.category)
        
        # Simplified ranking calculation
        rank = max(1, len(category_templates) // 2)  # Assume middle ranking
        percentile = 50.0  # Assume 50th percentile
        
        return rank, percentile
    
    async def _update_backtest_performance_tracking(self, results: Dict[str, TemplateBacktestResult],
                                                  config: TemplateBacktestConfig):
        """Update performance tracking with backtest results"""
        
        # Record backtest performance in tracker
        for template_id, result in results.items():
            # Convert backtest result to performance tracking format
            backtest_record = {
                'template_id': template_id,
                'backtest_performance': {
                    'total_return': result.total_return,
                    'sharpe_ratio': result.sharpe_ratio,
                    'max_drawdown': result.max_drawdown,
                    'win_rate': result.win_rate
                },
                'execution_stats': result.execution_stats,
                'backtest_date': datetime.now()
            }
            
            self.backtest_history.append(backtest_record)
    
    def get_backtest_summary(self) -> Dict[str, Any]:
        """Get summary of all backtesting activities"""
        
        return {
            'total_backtests': len(self.backtest_results),
            'active_backtests': len(self.active_backtests),
            'category_comparisons': len(self.category_comparisons),
            'templates_tested': len(set(r.template_id for r in self.backtest_results.values())),
            'avg_performance': {
                'sharpe_ratio': np.mean([r.sharpe_ratio for r in self.backtest_results.values()]) if self.backtest_results else 0.0,
                'total_return': np.mean([r.total_return for r in self.backtest_results.values()]) if self.backtest_results else 0.0
            }
        }
