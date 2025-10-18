"""
Strategy Optimizer

Main optimization engine for strategy parameter tuning with symbol awareness.

Features:
- Baseline performance measurement
- Parameter optimization using multiple search algorithms
- Symbol-aware optimization
- Result ranking and analysis
- Integration with parameter registry
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import pandas as pd
import numpy as np
from pathlib import Path
import json

from .config_management.parameter_registry import CentralParameterRegistry
from .config_management.configuration_store import ConfigurationStore


logger = logging.getLogger(__name__)


@dataclass
class OptimizationResult:
    """Result from strategy optimization"""
    strategy_type: str
    symbol: Optional[str]
    parameters: Dict[str, Any]
    
    # Performance metrics
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    total_return: float
    trade_count: int
    
    # Additional metrics
    sortino_ratio: Optional[float] = None
    calmar_ratio: Optional[float] = None
    average_trade: Optional[float] = None
    
    # Regime performance
    regime_performance: Dict[str, float] = field(default_factory=dict)
    
    # Cost analysis
    total_costs: Optional[float] = None
    net_return: Optional[float] = None
    
    # Metadata
    optimization_method: str = "grid_search"
    timestamp: datetime = field(default_factory=datetime.now)
    
    def meets_criteria(
        self,
        min_sharpe: float = 1.5,
        max_dd: float = 0.15,
        min_win_rate: float = 0.55,
        min_pf: float = 1.5,
        min_trades: int = 100
    ) -> bool:
        """Check if result meets success criteria"""
        return (
            self.sharpe_ratio >= min_sharpe and
            self.max_drawdown <= max_dd and
            self.win_rate >= min_win_rate and
            self.profit_factor >= min_pf and
            self.trade_count >= min_trades
        )


class StrategyOptimizer:
    """
    Main strategy optimization engine with symbol awareness.
    
    Coordinates parameter optimization for strategies across symbols.
    """
    
    def __init__(
        self,
        parameter_registry: Optional[CentralParameterRegistry] = None,
        configuration_store: Optional[ConfigurationStore] = None,
        backtest_engine: Optional[Any] = None
    ):
        """
        Initialize strategy optimizer.
        
        Args:
            parameter_registry: Central parameter registry
            configuration_store: Configuration store for persistence
            backtest_engine: Backtest engine for running optimizations
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize components
        self.parameter_registry = parameter_registry or CentralParameterRegistry()
        self.configuration_store = configuration_store or ConfigurationStore()
        self.backtest_engine = backtest_engine
        
        # Results storage
        self.optimization_results: List[OptimizationResult] = []
        self.baseline_results: Dict[str, OptimizationResult] = {}
        
        self.logger.info("StrategyOptimizer initialized")
    
    async def run_baseline_backtest(
        self,
        strategy_type: str,
        symbols: List[str],
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, OptimizationResult]:
        """
        Run baseline backtests for multiple symbols.
        
        Args:
            strategy_type: Strategy type to test
            symbols: List of symbols to test
            parameters: Optional baseline parameters (uses defaults if None)
        
        Returns:
            Dictionary mapping symbols to baseline results
        """
        baseline_results = {}
        
        for symbol in symbols:
            try:
                self.logger.info(f"Running baseline backtest: {strategy_type} on {symbol}")
                
                # Get parameters
                if parameters is None:
                    params = self.parameter_registry.get_parameters(strategy_type, None)
                else:
                    params = parameters
                
                # Run backtest
                result = await self._run_single_backtest(
                    strategy_type, symbol, params
                )
                
                if result:
                    baseline_results[symbol] = result
                    self.baseline_results[f"{strategy_type}:{symbol}"] = result
                    
                    self.logger.info(
                        f"Baseline {symbol}: Sharpe={result.sharpe_ratio:.2f}, "
                        f"DD={result.max_drawdown:.1%}, WR={result.win_rate:.1%}"
                    )
                    
            except Exception as e:
                self.logger.error(f"Baseline backtest failed for {symbol}: {e}")
        
        return baseline_results
    
    async def optimize_strategy(
        self,
        strategy_type: str,
        search_space: Dict[str, List[Any]],
        symbols: List[str],
        optimization_method: str = "grid_search"
    ) -> List[OptimizationResult]:
        """
        Optimize strategy across multiple symbols.
        
        Args:
            strategy_type: Strategy type
            search_space: Parameter search space
            symbols: Symbols to optimize
            optimization_method: "grid_search" or "bayesian"
        
        Returns:
            List of optimization results ranked by performance
        """
        all_results = []
        
        self.logger.info(
            f"Starting optimization for {strategy_type} across {len(symbols)} symbols "
            f"using {optimization_method}"
        )
        
        for symbol in symbols:
            try:
                # Optimize for this symbol
                symbol_results = await self._optimize_single_symbol(
                    strategy_type, symbol, search_space, optimization_method
                )
                
                all_results.extend(symbol_results)
                
                # Log best result for this symbol
                if symbol_results:
                    best = symbol_results[0]
                    self.logger.info(
                        f"Best for {symbol}: Sharpe={best.sharpe_ratio:.2f}, "
                        f"DD={best.max_drawdown:.1%}, WR={best.win_rate:.1%}"
                    )
                    
            except Exception as e:
                self.logger.error(f"Optimization failed for {symbol}: {e}")
        
        # Rank all results
        ranked_results = self._rank_results(all_results)
        
        # Store results
        self.optimization_results.extend(ranked_results)
        
        self.logger.info(
            f"Optimization complete: {len(ranked_results)} configurations tested"
        )
        
        return ranked_results
    
    async def _optimize_single_symbol(
        self,
        strategy_type: str,
        symbol: str,
        search_space: Dict[str, List[Any]],
        optimization_method: str
    ) -> List[OptimizationResult]:
        """
        Optimize strategy for a single symbol.
        
        Args:
            strategy_type: Strategy type
            symbol: Symbol to optimize
            search_space: Parameter search space
            optimization_method: Optimization method
        
        Returns:
            List of results for this symbol (sorted by performance)
        """
        results = []
        
        # Generate parameter combinations
        if optimization_method == "grid_search":
            param_combinations = self._generate_grid_search_combinations(search_space)
        elif optimization_method == "bayesian":
            # Bayesian optimization would be implemented by ParameterSearchEngine
            # For now, fall back to grid search
            param_combinations = self._generate_grid_search_combinations(search_space)
        else:
            raise ValueError(f"Unknown optimization method: {optimization_method}")
        
        total_combinations = len(param_combinations)
        self.logger.info(
            f"Testing {total_combinations} parameter combinations for {strategy_type}:{symbol}"
        )
        
        # Test each combination
        for i, params in enumerate(param_combinations, 1):
            try:
                # Run backtest
                result = await self._run_single_backtest(strategy_type, symbol, params)
                
                if result:
                    result.optimization_method = optimization_method
                    results.append(result)
                
                # Log progress
                if i % 10 == 0 or i == total_combinations:
                    self.logger.info(
                        f"Progress: {i}/{total_combinations} combinations tested"
                    )
                    
            except Exception as e:
                self.logger.error(f"Backtest failed for combination {i}: {e}")
        
        # Sort by Sharpe ratio
        results.sort(key=lambda r: r.sharpe_ratio, reverse=True)
        
        return results
    
    async def _run_single_backtest(
        self,
        strategy_type: str,
        symbol: str,
        parameters: Dict[str, Any]
    ) -> Optional[OptimizationResult]:
        """
        Run a single backtest with given parameters.
        
        Args:
            strategy_type: Strategy type
            symbol: Symbol to test
            parameters: Strategy parameters
        
        Returns:
            Optimization result or None if backtest failed
        """
        try:
            # This would integrate with the actual backtest engine
            # For now, we'll simulate with placeholder metrics
            
            # TODO: Replace with actual backtest engine integration
            # backtest_result = await self.backtest_engine.run(...)
            
            # Placeholder implementation
            result = OptimizationResult(
                strategy_type=strategy_type,
                symbol=symbol,
                parameters=parameters.copy(),
                sharpe_ratio=np.random.uniform(0.5, 2.5),  # Placeholder
                max_drawdown=np.random.uniform(0.05, 0.20),  # Placeholder
                win_rate=np.random.uniform(0.45, 0.65),  # Placeholder
                profit_factor=np.random.uniform(1.0, 2.5),  # Placeholder
                total_return=np.random.uniform(-0.10, 0.30),  # Placeholder
                trade_count=np.random.randint(50, 200),  # Placeholder
                timestamp=datetime.now()
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Backtest execution failed: {e}")
            return None
    
    def _generate_grid_search_combinations(
        self,
        search_space: Dict[str, List[Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate all combinations for grid search.
        
        Args:
            search_space: Parameter search space
        
        Returns:
            List of parameter combinations
        """
        import itertools
        
        # Get all parameter names and values
        param_names = list(search_space.keys())
        param_values = [search_space[name] for name in param_names]
        
        # Generate all combinations
        combinations = []
        for combo in itertools.product(*param_values):
            param_dict = dict(zip(param_names, combo))
            combinations.append(param_dict)
        
        return combinations
    
    def _rank_results(
        self,
        results: List[OptimizationResult]
    ) -> List[OptimizationResult]:
        """
        Rank results by multiple criteria.
        
        Primary: Sharpe ratio
        Secondary: Max drawdown (lower is better)
        Tertiary: Win rate
        
        Args:
            results: List of optimization results
        
        Returns:
            Sorted list of results
        """
        # Sort by multiple criteria
        sorted_results = sorted(
            results,
            key=lambda r: (
                -r.sharpe_ratio,  # Higher is better (negative for descending)
                r.max_drawdown,   # Lower is better (ascending)
                -r.win_rate       # Higher is better (negative for descending)
            )
        )
        
        return sorted_results
    
    def get_top_results(
        self,
        n: int = 10,
        strategy_type: Optional[str] = None,
        symbol: Optional[str] = None,
        meet_criteria: bool = False
    ) -> List[OptimizationResult]:
        """
        Get top N optimization results.
        
        Args:
            n: Number of results to return
            strategy_type: Optional filter by strategy type
            symbol: Optional filter by symbol
            meet_criteria: Only return results meeting success criteria
        
        Returns:
            Top N results
        """
        # Filter results
        filtered = self.optimization_results
        
        if strategy_type:
            filtered = [r for r in filtered if r.strategy_type == strategy_type]
        
        if symbol:
            filtered = [r for r in filtered if r.symbol == symbol]
        
        if meet_criteria:
            filtered = [r for r in filtered if r.meets_criteria()]
        
        # Return top N
        return filtered[:n]
    
    async def save_optimal_parameters(
        self,
        result: OptimizationResult,
        save_to_registry: bool = True,
        save_to_store: bool = True
    ) -> bool:
        """
        Save optimal parameters from result.
        
        Args:
            result: Optimization result
            save_to_registry: Save to parameter registry
            save_to_store: Save to configuration store
        
        Returns:
            True if save successful
        """
        try:
            success = True
            
            # Save to registry
            if save_to_registry:
                success &= self.parameter_registry.update_parameters(
                    result.strategy_type,
                    result.parameters,
                    result.symbol,
                    changed_by="optimizer",
                    change_reason=f"Optimization result: Sharpe={result.sharpe_ratio:.2f}"
                )
            
            # Save to store
            if save_to_store:
                success &= self.configuration_store.save_parameters(
                    result.strategy_type,
                    result.parameters,
                    result.symbol,
                    save_version=True
                )
            
            if success:
                symbol_str = result.symbol if result.symbol else "default"
                self.logger.info(
                    f"Saved optimal parameters for {result.strategy_type}:{symbol_str}"
                )
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to save optimal parameters: {e}")
            return False
    
    def generate_optimization_report(
        self,
        strategy_type: str,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive optimization report.
        
        Args:
            strategy_type: Strategy type
            output_path: Optional path to save report
        
        Returns:
            Report dictionary
        """
        # Filter results for this strategy
        results = [r for r in self.optimization_results if r.strategy_type == strategy_type]
        
        if not results:
            return {'error': f'No results found for {strategy_type}'}
        
        # Calculate statistics
        report = {
            'strategy_type': strategy_type,
            'total_configurations': len(results),
            'configurations_meeting_criteria': len([r for r in results if r.meets_criteria()]),
            'symbols_tested': len(set(r.symbol for r in results)),
            'best_overall': self._result_to_dict(results[0]) if results else None,
            'statistics': {
                'sharpe_mean': np.mean([r.sharpe_ratio for r in results]),
                'sharpe_std': np.std([r.sharpe_ratio for r in results]),
                'sharpe_max': np.max([r.sharpe_ratio for r in results]),
                'drawdown_mean': np.mean([r.max_drawdown for r in results]),
                'drawdown_max': np.max([r.max_drawdown for r in results]),
                'win_rate_mean': np.mean([r.win_rate for r in results]),
            },
            'top_10_results': [self._result_to_dict(r) for r in results[:10]],
            'timestamp': datetime.now().isoformat()
        }
        
        # Save report if path provided
        if output_path:
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)
            self.logger.info(f"Optimization report saved to {output_path}")
        
        return report
    
    def _result_to_dict(self, result: OptimizationResult) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            'strategy_type': result.strategy_type,
            'symbol': result.symbol,
            'parameters': result.parameters,
            'sharpe_ratio': result.sharpe_ratio,
            'max_drawdown': result.max_drawdown,
            'win_rate': result.win_rate,
            'profit_factor': result.profit_factor,
            'total_return': result.total_return,
            'trade_count': result.trade_count,
            'meets_criteria': result.meets_criteria()
        }

