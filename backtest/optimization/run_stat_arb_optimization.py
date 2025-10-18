"""
Statistical Arbitrage Strategy Optimization

Phase 1.1: Baseline Performance & Parameter Search

This script demonstrates the complete optimization workflow:
1. Run baseline with default parameters
2. Define parameter search space
3. Execute grid search optimization
4. Analyze results and identify best configurations

Usage:
    python -m backtest.optimization.run_stat_arb_optimization
"""

import sys
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import json

# Add project root
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backtest.optimization.backtest_optimizer_interface import BacktestOptimizerInterface
from backtest.optimization.parameter_search import ParameterSearchEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)8s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class StatArbOptimizer:
    """Statistical Arbitrage Strategy Optimizer"""
    
    def __init__(self):
        self.results_dir = project_root / "backtest_results" / "stat_arb_optimization"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize optimizer interface
        self.interface = BacktestOptimizerInterface()
        
        # Initialize parameter search engine
        self.search_engine = ParameterSearchEngine()
    
    def get_default_parameters(self) -> Dict[str, Any]:
        """Get default Statistical Arbitrage parameters"""
        return {
            'cointegration_lookback': 252,
            'min_cointegration_pvalue': 0.05,
            'min_correlation': 0.7,
            'entry_zscore_threshold': 2.0,
            'exit_zscore_threshold': 0.5,
            'stop_loss_zscore': 3.5,
            'max_spread_positions': 5,
            'base_position_size': 0.02
        }
    
    def get_parameter_search_space(self) -> Dict[str, List[Any]]:
        """
        Define parameter search space for Statistical Arbitrage
        
        Focus on the most impactful parameters:
        - entry_zscore_threshold: When to enter trades
        - exit_zscore_threshold: When to exit trades
        - base_position_size: Position sizing
        """
        return {
            'cointegration_lookback': [252],  # Fixed: 1 year
            'min_cointegration_pvalue': [0.05],  # Fixed: 5% significance
            'min_correlation': [0.7],  # Fixed: 70% min correlation
            
            # OPTIMIZATION TARGETS:
            'entry_zscore_threshold': [1.5, 2.0, 2.5],  # 3 values
            'exit_zscore_threshold': [0.3, 0.5, 0.7],    # 3 values
            'stop_loss_zscore': [3.5],  # Fixed
            'max_spread_positions': [5],  # Fixed
            'base_position_size': [0.015, 0.020, 0.025]  # 3 values: 1.5%, 2%, 2.5%
        }
    
    async def run_baseline(self, symbols: List[str]) -> Dict[str, Any]:
        """Run baseline backtest with default parameters"""
        
        logger.info("\n" + "="*80)
        logger.info("PHASE 1.1.1: BASELINE PERFORMANCE TEST")
        logger.info("="*80)
        
        default_params = self.get_default_parameters()
        
        logger.info(f"\nBaseline Configuration:")
        logger.info(f"  Strategy: Statistical Arbitrage")
        logger.info(f"  Symbols: {', '.join(symbols)}")
        logger.info(f"  Parameters: {json.dumps(default_params, indent=4)}")
        
        logger.info("\n🚀 Running baseline backtest...")
        
        result = await self.interface.run_single_backtest(
            strategy_type='statistical_arbitrage',
            strategy_params=default_params,
            symbols=symbols
        )
        
        if result.get('success'):
            logger.info("\n✅ Baseline backtest complete!")
            self._display_result(result, "BASELINE")
            
            # Save baseline result
            baseline_file = self.results_dir / "baseline_result.json"
            with open(baseline_file, 'w') as f:
                json.dump(result, f, indent=2)
            
            logger.info(f"\n💾 Baseline saved: {baseline_file}")
        else:
            logger.error(f"\n❌ Baseline failed: {result.get('error')}")
        
        return result
    
    async def run_grid_search(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """Run grid search optimization"""
        
        logger.info("\n" + "="*80)
        logger.info("PHASE 1.1.2-1.1.3: PARAMETER GRID SEARCH")
        logger.info("="*80)
        
        search_space = self.get_parameter_search_space()
        
        # Calculate total combinations
        total_combinations = 1
        for values in search_space.values():
            total_combinations *= len(values)
        
        logger.info(f"\nSearch Space:")
        for param, values in search_space.items():
            if len(values) > 1:
                logger.info(f"  {param}: {values}")
        
        logger.info(f"\nTotal Combinations: {total_combinations}")
        logger.info(f"Estimated Time: ~{total_combinations * 2} minutes (2 min/backtest)")
        logger.info(f"Symbols: {', '.join(symbols)}")
        
        # Generate parameter combinations
        from itertools import product
        keys = list(search_space.keys())
        values = [search_space[k] for k in keys]
        
        param_combinations = []
        for combo in product(*values):
            param_dict = dict(zip(keys, combo))
            param_combinations.append(param_dict)
        
        logger.info(f"\n🔍 Starting grid search with {len(param_combinations)} combinations...")
        logger.info("=" * 80)
        
        # Run batch optimization
        results = await self.interface.batch_optimize(
            strategy_type='statistical_arbitrage',
            parameter_combinations=param_combinations,
            symbols=symbols,
            max_concurrent=2  # Limit concurrent to avoid resource issues
        )
        
        logger.info("=" * 80)
        logger.info(f"✅ Grid search complete: {len(results)}/{len(param_combinations)} successful")
        
        # Save all results
        results_file = self.results_dir / "grid_search_results.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"💾 Results saved: {results_file}")
        
        return results
    
    def analyze_results(self, results: List[Dict[str, Any]]) -> None:
        """Analyze optimization results"""
        
        logger.info("\n" + "="*80)
        logger.info("PHASE 1.1.4: RESULTS ANALYSIS")
        logger.info("="*80)
        
        if not results:
            logger.warning("No results to analyze")
            return
        
        # Get top results
        top_5 = self.interface.get_best_results(results, 'sharpe_ratio', 5)
        
        logger.info(f"\n🏆 TOP 5 CONFIGURATIONS (by Sharpe Ratio):")
        logger.info("-" * 80)
        
        for i, result in enumerate(top_5, 1):
            logger.info(f"\n#{i} Configuration:")
            logger.info(f"  Sharpe Ratio:  {result['sharpe_ratio']:>8.2f}")
            logger.info(f"  Total Return:  {result['total_return']*100:>8.2f}%")
            logger.info(f"  Max Drawdown:  {result['max_drawdown']*100:>8.2f}%")
            logger.info(f"  Win Rate:      {result['win_rate']*100:>8.1f}%")
            logger.info(f"  Profit Factor: {result['profit_factor']:>8.2f}")
            logger.info(f"  Total Trades:  {result['total_trades']:>8d}")
            logger.info(f"\n  Parameters:")
            for key, value in result['parameters'].items():
                logger.info(f"    {key:30s}: {value}")
        
        # Parameter sensitivity analysis
        logger.info("\n📊 PARAMETER SENSITIVITY ANALYSIS:")
        logger.info("-" * 80)
        
        self._analyze_parameter_impact(results, 'entry_zscore_threshold')
        self._analyze_parameter_impact(results, 'exit_zscore_threshold')
        self._analyze_parameter_impact(results, 'base_position_size')
        
        logger.info("\n" + "="*80)
    
    def _analyze_parameter_impact(self, results: List[Dict[str, Any]], param_name: str) -> None:
        """Analyze impact of a specific parameter"""
        
        from collections import defaultdict
        
        # Group results by parameter value
        param_groups = defaultdict(list)
        for result in results:
            if result.get('success'):
                param_value = result['parameters'].get(param_name)
                param_groups[param_value].append(result['sharpe_ratio'])
        
        if not param_groups:
            return
        
        logger.info(f"\n  {param_name}:")
        for value in sorted(param_groups.keys()):
            sharpes = param_groups[value]
            avg_sharpe = sum(sharpes) / len(sharpes)
            logger.info(f"    {value:>6} → Avg Sharpe: {avg_sharpe:>6.2f} ({len(sharpes)} tests)")
    
    def _display_result(self, result: Dict[str, Any], label: str) -> None:
        """Display a single result"""
        
        logger.info(f"\n{label} RESULTS:")
        logger.info("-" * 80)
        logger.info(f"  Sharpe Ratio:  {result['sharpe_ratio']:>8.2f}")
        logger.info(f"  Sortino Ratio: {result['sortino_ratio']:>8.2f}")
        logger.info(f"  Calmar Ratio:  {result['calmar_ratio']:>8.2f}")
        logger.info(f"  Total Return:  {result['total_return']*100:>8.2f}%")
        logger.info(f"  Max Drawdown:  {result['max_drawdown']*100:>8.2f}%")
        logger.info(f"  Win Rate:      {result['win_rate']*100:>8.1f}%")
        logger.info(f"  Profit Factor: {result['profit_factor']:>8.2f}")
        logger.info(f"  Total Trades:  {result['total_trades']:>8d}")
        
        # Assessment
        logger.info(f"\n  Assessment:")
        if result['sharpe_ratio'] >= 2.0:
            logger.info("    ✅ EXCELLENT: Sharpe >= 2.0")
        elif result['sharpe_ratio'] >= 1.5:
            logger.info("    ✓  GOOD: Sharpe >= 1.5")
        elif result['sharpe_ratio'] >= 1.0:
            logger.info("    ~  FAIR: Sharpe >= 1.0")
        else:
            logger.info("    ⚠  NEEDS IMPROVEMENT: Sharpe < 1.0")


async def main():
    """Main execution"""
    
    logger.info("\n" + "="*80)
    logger.info("STATISTICAL ARBITRAGE OPTIMIZATION")
    logger.info("Phase 1.1: Baseline & Parameter Search")
    logger.info("="*80)
    
    optimizer = StatArbOptimizer()
    
    # Define test symbols: GLD/GDX - Classic gold/gold miners pair
    # Known to be cointegrated since miners' value is tied to gold prices
    symbols = ['GLD', 'GDX']
    
    try:
        # Step 1: Run baseline
        baseline_result = await optimizer.run_baseline(symbols)
        
        if not baseline_result.get('success'):
            logger.error("❌ Baseline failed, aborting optimization")
            return 1
        
        # Step 2 & 3: Run grid search
        optimization_results = await optimizer.run_grid_search(symbols)
        
        if not optimization_results:
            logger.error("❌ Grid search produced no valid results")
            return 1
        
        # Step 4: Analyze results
        optimizer.analyze_results(optimization_results)
        
        logger.info("\n" + "="*80)
        logger.info("✅ PHASE 1.1 COMPLETE")
        logger.info("="*80)
        logger.info(f"\nResults Directory: {optimizer.results_dir}")
        logger.info("  - baseline_result.json")
        logger.info("  - grid_search_results.json")
        logger.info("\n🎯 Next: Phase 1.2 - Symbol Selection & Joint Optimization")
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("\n\n⚠ Optimization interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"\n❌ Optimization failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

