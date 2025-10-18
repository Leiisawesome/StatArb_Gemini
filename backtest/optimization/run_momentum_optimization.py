"""
Momentum Strategy Optimization - Phase 1.1
==========================================

Complete optimization workflow for the Enhanced Momentum Strategy using
the institutional backtest engine and optimization infrastructure.

This script orchestrates:
1. Baseline backtest with default parameters
2. Grid search across parameter space
3. Result analysis and ranking
4. Parameter sensitivity analysis
5. Result persistence for Phase 1.2

Author: StatArb_Gemini Strategy Optimization Initiative
Version: 1.0.0 (Phase 1.1)
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
import numpy as np

# Import optimization infrastructure
from backtest.optimization.backtest_optimizer_interface import BacktestOptimizerInterface
from backtest.optimization.config_management.parameter_registry import CentralParameterRegistry
from backtest.optimization.performance_comparator import PerformanceComparator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MomentumOptimizer:
    """
    Orchestrates the complete Momentum strategy optimization workflow
    
    Phase 1.1 Objectives:
    - Prove end-to-end optimization workflow
    - Test parameter search infrastructure
    - Validate backtest integration
    - Generate baseline performance metrics
    """
    
    def __init__(self):
        """Initialize Momentum optimizer"""
        
        self.optimizer_interface = BacktestOptimizerInterface()
        self.parameter_registry = CentralParameterRegistry()
        self.performance_comparator = PerformanceComparator()
        
        # Results storage
        self.results_dir = Path("backtest_results/momentum_optimization")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Strategy identification
        self.strategy_name = "enhanced_momentum"
        self.strategy_type = "momentum"
        
        logger.info("🚀 Momentum Strategy Optimizer initialized")
    
    def get_default_parameters(self) -> Dict[str, Any]:
        """Get default Momentum strategy parameters"""
        
        return {
            # Momentum parameters
            'short_period': 10,
            'medium_period': 20,
            'long_period': 50,
            'momentum_threshold': 0.02,
            
            # Trend quality
            'adx_period': 14,
            'adx_threshold': 25.0,
            
            # Volume confirmation
            'volume_ma_period': 20,
            'volume_threshold': 1.2,
            
            # Position sizing
            'base_position_pct': 0.03,
            'max_position_pct': 0.08,
            
            # Risk management
            'momentum_stop_pct': 0.03,
            'trailing_stop_pct': 0.02,
            'profit_target_ratio': 3.0,
            'max_holding_period': 20,
            
            # Breakout detection
            'enable_breakout_detection': True,
            'breakout_lookback': 20,
            'breakout_threshold': 0.02
        }
    
    async def run_baseline(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Run baseline backtest with default parameters
        
        Args:
            symbols: List of symbols to test
            
        Returns:
            Baseline backtest results
        """
        
        logger.info("=" * 80)
        logger.info("PHASE 1.1 - BASELINE BACKTEST")
        logger.info("=" * 80)
        
        # Get default parameters
        default_params = self.get_default_parameters()
        
        # Register parameters
        self.parameter_registry.update_parameters(
            strategy_type=self.strategy_type,
            parameters=default_params,
            changed_by='optimization_baseline',
            change_reason='Phase 1.1 baseline parameters'
        )
        
        logger.info(f"📊 Running baseline with symbols: {symbols}")
        logger.info(f"📋 Default parameters: {json.dumps(default_params, indent=2)}")
        
        # Run backtest
        result = await self.optimizer_interface.run_single_backtest(
            strategy_type=self.strategy_type,
            strategy_params=default_params,
            symbols=symbols,
            custom_config={'run_name': 'baseline'}
        )
        
        # Log results
        if result['success']:
            metrics = result['metrics']
            logger.info("\n" + "=" * 80)
            logger.info("BASELINE RESULTS")
            logger.info("=" * 80)
            logger.info(f"Total Return:     {metrics['total_return']:.2%}")
            logger.info(f"Sharpe Ratio:     {metrics['sharpe_ratio']:.3f}")
            logger.info(f"Max Drawdown:     {metrics['max_drawdown']:.2%}")
            logger.info(f"Win Rate:         {metrics['win_rate']:.2%}")
            logger.info(f"Trade Count:      {metrics['trade_count']}")
            logger.info(f"Profit Factor:    {metrics['profit_factor']:.2f}")
            logger.info("=" * 80 + "\n")
        else:
            logger.error(f"❌ Baseline backtest failed: {result.get('error', 'Unknown error')}")
        
        # Save baseline results
        self._save_results([result], "baseline_results.json")
        
        return result
    
    def define_search_space(self, optimization_level: str = 'moderate') -> Dict[str, List[Any]]:
        """
        Define parameter search space
        
        Args:
            optimization_level: 'quick', 'moderate', or 'comprehensive'
            
        Returns:
            Dictionary of parameter search spaces
        """
        
        if optimization_level == 'quick':
            # Quick search: 3x3x2 = 18 combinations
            return {
                'momentum_threshold': [0.015, 0.02, 0.025],
                'adx_threshold': [20.0, 25.0, 30.0],
                'volume_threshold': [1.0, 1.2]
            }
        
        elif optimization_level == 'moderate':
            # Moderate search: 3x3x3x2 = 54 combinations
            return {
                'momentum_threshold': [0.015, 0.02, 0.025],
                'adx_threshold': [20.0, 25.0, 30.0],
                'volume_threshold': [1.0, 1.2, 1.5],
                'momentum_stop_pct': [0.02, 0.03]
            }
        
        else:  # comprehensive
            # Comprehensive search: 4x4x3x3x2 = 288 combinations
            return {
                'short_period': [8, 10, 12, 15],
                'momentum_threshold': [0.01, 0.015, 0.02, 0.025],
                'adx_threshold': [20.0, 25.0, 30.0],
                'volume_threshold': [1.0, 1.2, 1.5],
                'momentum_stop_pct': [0.02, 0.03]
            }
    
    def _generate_combinations(self, base_params: Dict[str, Any], 
                              search_space: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
        """
        Generate all parameter combinations from search space
        
        Args:
            base_params: Base parameters
            search_space: Parameter search space
            
        Returns:
            List of parameter combinations
        """
        import itertools
        
        # Get parameter names and values
        param_names = list(search_space.keys())
        param_values = [search_space[name] for name in param_names]
        
        # Generate all combinations
        combinations = []
        for values in itertools.product(*param_values):
            # Start with base parameters
            params = base_params.copy()
            
            # Override with search space values
            for name, value in zip(param_names, values):
                params[name] = value
            
            combinations.append(params)
        
        return combinations
    
    async def run_grid_search(self, symbols: List[str], 
                            optimization_level: str = 'quick') -> List[Dict[str, Any]]:
        """
        Run grid search optimization
        
        Args:
            symbols: List of symbols to test
            optimization_level: Level of optimization depth
            
        Returns:
            List of optimization results
        """
        
        logger.info("=" * 80)
        logger.info(f"PHASE 1.1 - GRID SEARCH OPTIMIZATION ({optimization_level.upper()})")
        logger.info("=" * 80)
        
        # Define search space
        search_space = self.define_search_space(optimization_level)
        
        logger.info(f"📊 Search space parameters:")
        for param, values in search_space.items():
            logger.info(f"  - {param}: {values}")
        
        # Calculate total combinations
        total_combinations = 1
        for values in search_space.values():
            total_combinations *= len(values)
        
        logger.info(f"🔢 Total combinations: {total_combinations}")
        logger.info(f"⏱️  Estimated time: ~{total_combinations * 2} minutes (2 min/backtest)")
        
        # Get default parameters as base
        base_params = self.get_default_parameters()
        
        # Generate parameter combinations from search space
        param_combinations = self._generate_combinations(base_params, search_space)
        
        logger.info(f"📊 Generated {len(param_combinations)} parameter combinations")
        
        # Run batch optimization
        logger.info("\n🔄 Starting grid search...")
        
        results = await self.optimizer_interface.batch_optimize(
            strategy_type=self.strategy_type,
            parameter_combinations=param_combinations,
            symbols=symbols,
            max_concurrent=2  # Limit concurrency for stability
        )
        
        logger.info(f"\n✅ Grid search complete: {len(results)} backtests executed")
        
        # Save all results
        self._save_results(results, f"grid_search_{optimization_level}_results.json")
        
        return results
    
    def analyze_results(self, results: List[Dict[str, Any]], 
                       top_n: int = 10) -> Dict[str, Any]:
        """
        Analyze optimization results
        
        Args:
            results: List of backtest results
            top_n: Number of top configurations to return
            
        Returns:
            Analysis summary with top performers
        """
        
        logger.info("=" * 80)
        logger.info("RESULTS ANALYSIS")
        logger.info("=" * 80)
        
        # Filter successful results
        successful_results = [r for r in results if r['success']]
        
        logger.info(f"📊 Total backtests: {len(results)}")
        logger.info(f"✅ Successful: {len(successful_results)}")
        logger.info(f"❌ Failed: {len(results) - len(successful_results)}")
        
        if not successful_results:
            logger.error("❌ No successful results to analyze")
            return {'top_configs': [], 'statistics': {}}
        
        # Rank by Sharpe ratio (primary metric)
        top_by_sharpe = self.performance_comparator.rank_results(
            successful_results,
            metric='sharpe_ratio',
            ascending=False
        )[:top_n]
        
        # Rank by total return
        top_by_return = self.performance_comparator.rank_results(
            successful_results,
            metric='total_return',
            ascending=False
        )[:top_n]
        
        # Rank by profit factor
        top_by_profit_factor = self.performance_comparator.rank_results(
            successful_results,
            metric='profit_factor',
            ascending=False
        )[:top_n]
        
        # Display top configurations
        logger.info(f"\n🏆 TOP {top_n} BY SHARPE RATIO:")
        logger.info("-" * 80)
        for i, result in enumerate(top_by_sharpe, 1):
            metrics = result['metrics']
            params = result['parameters']
            logger.info(f"\n#{i} | Sharpe: {metrics['sharpe_ratio']:.3f} | "
                       f"Return: {metrics['total_return']:.2%} | "
                       f"MaxDD: {metrics['max_drawdown']:.2%}")
            logger.info(f"    Parameters: {json.dumps(params, indent=4)}")
        
        # Calculate statistics
        sharpe_ratios = [r['metrics']['sharpe_ratio'] for r in successful_results]
        returns = [r['metrics']['total_return'] for r in successful_results]
        
        statistics = {
            'total_backtests': len(results),
            'successful_backtests': len(successful_results),
            'failed_backtests': len(results) - len(successful_results),
            'sharpe_ratio': {
                'mean': np.mean(sharpe_ratios),
                'std': np.std(sharpe_ratios),
                'min': np.min(sharpe_ratios),
                'max': np.max(sharpe_ratios),
                'median': np.median(sharpe_ratios)
            },
            'total_return': {
                'mean': np.mean(returns),
                'std': np.std(returns),
                'min': np.min(returns),
                'max': np.max(returns),
                'median': np.median(returns)
            }
        }
        
        logger.info("\n📈 PERFORMANCE STATISTICS:")
        logger.info("-" * 80)
        logger.info(f"Sharpe Ratio - Mean: {statistics['sharpe_ratio']['mean']:.3f}, "
                   f"Std: {statistics['sharpe_ratio']['std']:.3f}, "
                   f"Range: [{statistics['sharpe_ratio']['min']:.3f}, "
                   f"{statistics['sharpe_ratio']['max']:.3f}]")
        logger.info(f"Total Return - Mean: {statistics['total_return']['mean']:.2%}, "
                   f"Std: {statistics['total_return']['std']:.2%}, "
                   f"Range: [{statistics['total_return']['min']:.2%}, "
                   f"{statistics['total_return']['max']:.2%}]")
        
        analysis = {
            'top_by_sharpe': top_by_sharpe,
            'top_by_return': top_by_return,
            'top_by_profit_factor': top_by_profit_factor,
            'statistics': statistics,
            'timestamp': datetime.now().isoformat()
        }
        
        # Save analysis
        self._save_results(analysis, "optimization_analysis.json")
        
        return analysis
    
    def generate_parameter_sensitivity_report(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate parameter sensitivity analysis
        
        Args:
            results: List of backtest results
            
        Returns:
            Sensitivity analysis report
        """
        
        logger.info("\n" + "=" * 80)
        logger.info("PARAMETER SENSITIVITY ANALYSIS")
        logger.info("=" * 80)
        
        successful_results = [r for r in results if r['success']]
        
        if not successful_results:
            return {}
        
        # Extract parameter values and metrics
        param_names = set()
        for result in successful_results:
            param_names.update(result['parameters'].keys())
        
        sensitivity = {}
        
        for param in param_names:
            # Group results by parameter value
            param_groups = {}
            for result in successful_results:
                param_value = result['parameters'].get(param)
                if param_value is not None:
                    if param_value not in param_groups:
                        param_groups[param_value] = []
                    param_groups[param_value].append(result['metrics'])
            
            # Calculate average performance for each value
            param_performance = {}
            for value, metrics_list in param_groups.items():
                sharpe_ratios = [m['sharpe_ratio'] for m in metrics_list]
                returns = [m['total_return'] for m in metrics_list]
                
                param_performance[str(value)] = {
                    'count': len(metrics_list),
                    'avg_sharpe': np.mean(sharpe_ratios),
                    'avg_return': np.mean(returns),
                    'std_sharpe': np.std(sharpe_ratios),
                    'std_return': np.std(returns)
                }
            
            sensitivity[param] = param_performance
            
            # Log sensitivity
            logger.info(f"\n📊 {param}:")
            for value, perf in param_performance.items():
                logger.info(f"  {value}: Sharpe={perf['avg_sharpe']:.3f} ±{perf['std_sharpe']:.3f}, "
                           f"Return={perf['avg_return']:.2%} ±{perf['std_return']:.2%} "
                           f"({perf['count']} samples)")
        
        # Save sensitivity analysis
        self._save_results(sensitivity, "parameter_sensitivity.json")
        
        return sensitivity
    
    def _save_results(self, results: Any, filename: str):
        """Save results to JSON file"""
        
        filepath = self.results_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"💾 Results saved to: {filepath}")
    
    def generate_summary_report(self, baseline: Dict[str, Any],
                               analysis: Dict[str, Any],
                               sensitivity: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate final summary report
        
        Args:
            baseline: Baseline results
            analysis: Optimization analysis
            sensitivity: Sensitivity analysis
            
        Returns:
            Complete summary report
        """
        
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 1.1 SUMMARY REPORT")
        logger.info("=" * 80)
        
        # Best configuration
        best_config = analysis['top_by_sharpe'][0] if analysis['top_by_sharpe'] else None
        
        if best_config:
            improvement = {
                'sharpe_improvement': best_config['metrics']['sharpe_ratio'] - baseline['metrics']['sharpe_ratio'],
                'return_improvement': best_config['metrics']['total_return'] - baseline['metrics']['total_return'],
                'sharpe_improvement_pct': ((best_config['metrics']['sharpe_ratio'] / baseline['metrics']['sharpe_ratio']) - 1) * 100
            }
            
            logger.info(f"\n🏆 BEST CONFIGURATION:")
            logger.info(f"  Sharpe Ratio: {best_config['metrics']['sharpe_ratio']:.3f} "
                       f"(+{improvement['sharpe_improvement']:.3f}, +{improvement['sharpe_improvement_pct']:.1f}%)")
            logger.info(f"  Total Return: {best_config['metrics']['total_return']:.2%} "
                       f"(+{improvement['return_improvement']:.2%})")
            logger.info(f"  Max Drawdown: {best_config['metrics']['max_drawdown']:.2%}")
            logger.info(f"  Win Rate: {best_config['metrics']['win_rate']:.2%}")
            logger.info(f"  Parameters: {json.dumps(best_config['parameters'], indent=4)}")
        
        summary = {
            'baseline_performance': baseline['metrics'],
            'best_performance': best_config['metrics'] if best_config else None,
            'improvement': improvement if best_config else None,
            'optimization_statistics': analysis['statistics'],
            'parameter_sensitivity': sensitivity,
            'phase': '1.1',
            'strategy': 'momentum',
            'timestamp': datetime.now().isoformat()
        }
        
        # Save summary
        self._save_results(summary, "phase1_1_summary.json")
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ PHASE 1.1 COMPLETE")
        logger.info("=" * 80)
        logger.info(f"📁 Results saved to: {self.results_dir}")
        logger.info(f"📊 Next: Phase 1.2 - Symbol Selection & Joint Optimization")
        
        return summary


async def async_main():
    """Main async execution function"""
    
    print("\n" + "=" * 80)
    print("MOMENTUM STRATEGY OPTIMIZATION - PHASE 1.1")
    print("Institutional Backtest Engine + Optimization Infrastructure")
    print("=" * 80 + "\n")
    
    # Initialize optimizer
    optimizer = MomentumOptimizer()
    
    # Define test symbols (liquid, high-momentum candidates)
    symbols = ['NVDA', 'TSLA']  # Tech momentum leaders
    
    # Step 1: Run baseline
    print("\n🎯 STEP 1: Baseline Backtest")
    print("-" * 80)
    baseline_result = await optimizer.run_baseline(symbols)
    
    if not baseline_result['success']:
        print("\n❌ Baseline failed - cannot proceed with optimization")
        return
    
    # Step 2: Run grid search (start with 'quick' for validation)
    print("\n🎯 STEP 2: Grid Search Optimization")
    print("-" * 80)
    optimization_results = await optimizer.run_grid_search(
        symbols=symbols,
        optimization_level='quick'  # Start with quick search (18 combinations)
    )
    
    # Step 3: Analyze results
    print("\n🎯 STEP 3: Results Analysis")
    print("-" * 80)
    analysis = optimizer.analyze_results(optimization_results, top_n=5)
    
    # Step 4: Parameter sensitivity
    print("\n🎯 STEP 4: Parameter Sensitivity Analysis")
    print("-" * 80)
    sensitivity = optimizer.generate_parameter_sensitivity_report(optimization_results)
    
    # Step 5: Generate summary
    print("\n🎯 STEP 5: Summary Report")
    print("-" * 80)
    summary = optimizer.generate_summary_report(baseline_result, analysis, sensitivity)
    
    print("\n" + "=" * 80)
    print("🎉 PHASE 1.1 OPTIMIZATION COMPLETE!")
    print("=" * 80)
    print(f"\n📁 All results saved to: backtest_results/momentum_optimization/")
    print(f"🚀 Ready for Phase 1.2: Symbol Selection & Joint Optimization")


def main():
    """Main entry point"""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()

