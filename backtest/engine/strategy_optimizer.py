"""
Strategy Optimizer for Institutional Backtest Engine
====================================================

Provides a framework for iterative strategy fine-tuning using grid search
or random search over strategy parameters.

Features:
- Parameter grid generation
- Iterative backtest execution
- Result aggregation and ranking
- Optimization report generation

Usage:
    optimizer = StrategyOptimizer(base_config)
    results = await optimizer.run_grid_search({
        'lookback_period': [10, 20, 30, 60],
        'momentum_threshold': [0.01, 0.02, 0.05]
    })

Author: StatArb_Gemini Core Engine
"""

import itertools
import logging
import pandas as pd
from typing import Dict, List, Any
from dataclasses import dataclass
import copy

from core_engine.config import BacktestConfig
from backtest.engine.institutional_backtest_engine import InstitutionalBacktestEngine

logger = logging.getLogger(__name__)

@dataclass
class OptimizationResult:
    """Container for a single optimization run result"""
    parameters: Dict[str, Any]
    metrics: Dict[str, float]
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    execution_time_seconds: float

class StrategyOptimizer:
    """
    Orchestrates strategy fine-tuning by running multiple backtest iterations.
    Wraps InstitutionalBacktestEngine.
    """

    def __init__(self, base_config: BacktestConfig):
        """
        Initialize optimizer with a base configuration.

        Args:
            base_config: The template configuration for all runs
        """
        self.base_config = base_config
        self.results: List[OptimizationResult] = []
        self.logger = logging.getLogger(__name__)

    async def run_grid_search(self, param_grid: Dict[str, List[Any]],
                            strategy_name: str = 'default_momentum') -> pd.DataFrame:
        """
        Run exhaustive grid search over parameter space.

        Args:
            param_grid: Dictionary mapping parameter names to lists of values
                        e.g. {'lookback': [10, 20], 'thresh': [0.01, 0.02]}
            strategy_name: Name of the strategy to tune (must exist in config)

        Returns:
            DataFrame containing all results, ranked by Sharpe Ratio
        """
        self.logger.info("=" * 80)
        self.logger.info(f"🚀 STARTING GRID SEARCH: {strategy_name}")
        self.logger.info(f"   Parameters: {list(param_grid.keys())}")
        self.logger.info("=" * 80)

        # Generate all combinations
        keys = param_grid.keys()
        values = param_grid.values()
        combinations = [dict(zip(keys, v)) for v in itertools.product(*values)]

        total_runs = len(combinations)
        self.logger.info(f"   Total Combinations: {total_runs}")

        for i, params in enumerate(combinations):
            self.logger.info(f"\n🔄 Running iteration {i+1}/{total_runs}")
            self.logger.info(f"   Params: {params}")

            # Create run-specific config
            run_config = copy.deepcopy(self.base_config)

            # Update strategy parameters
            # Note: This assumes specific structure of strategies list in config
            strategy_found = False
            for strategy in run_config.strategies:
                if isinstance(strategy, dict) and strategy.get('name') == strategy_name:
                    # Dict-based config
                    if 'parameters' not in strategy:
                        strategy['parameters'] = {}
                    strategy['parameters'].update(params)
                    # Also update top-level keys if they exist (legacy support)
                    for k, v in params.items():
                        if k in strategy:
                            strategy[k] = v
                    strategy_found = True
                    break
                # Add handling for dataclass strategies if needed

            if not strategy_found:
                self.logger.warning(f"⚠️ Strategy {strategy_name} not found in config. Skipping.")
                continue

            # Run backtest
            engine = InstitutionalBacktestEngine(run_config)
            try:
                import time
                start_time = time.time()

                # Initialize and run
                await engine.initialize()
                backtest_results = await engine.run_backtest()

                duration = time.time() - start_time

                # Extract metrics
                metrics = backtest_results.get('performance_summary', {})

                result = OptimizationResult(
                    parameters=params,
                    metrics=metrics,
                    total_return=metrics.get('total_return', 0.0),
                    sharpe_ratio=metrics.get('sharpe_ratio', 0.0),
                    max_drawdown=metrics.get('max_drawdown', 0.0),
                    win_rate=metrics.get('win_rate', 0.0),
                    execution_time_seconds=duration
                )

                self.results.append(result)
                self.logger.info(f"   ✅ Run Complete: Sharpe={result.sharpe_ratio:.2f}, Return={result.total_return:.2%}")

            except Exception as e:
                self.logger.error(f"   ❌ Run Failed: {e}")
            finally:
                # Cleanup to free memory
                await engine.shutdown()

        # Compile results
        return self._generate_results_dataframe()

    def _generate_results_dataframe(self) -> pd.DataFrame:
        """Convert results to DataFrame and rank"""
        if not self.results:
            return pd.DataFrame()

        data = []
        for res in self.results:
            row = res.parameters.copy()
            row.update({
                'total_return': res.total_return,
                'sharpe_ratio': res.sharpe_ratio,
                'max_drawdown': res.max_drawdown,
                'win_rate': res.win_rate,
                'execution_time': res.execution_time_seconds
            })
            data.append(row)

        df = pd.DataFrame(data)
        return df.sort_values(by='sharpe_ratio', ascending=False)

