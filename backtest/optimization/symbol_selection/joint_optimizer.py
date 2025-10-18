"""
Joint Optimizer

Jointly optimizes strategy parameters and symbol selection.
"""

import logging
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from itertools import product

from .symbol_analyzer import SymbolCharacteristics
from .strategy_matcher import StrategyType, StrategyMatch


@dataclass
class JointOptimizationResult:
    """Result of joint parameter + symbol optimization"""
    
    strategy_type: StrategyType
    symbol: str
    parameters: Dict[str, Any]
    
    # Performance metrics
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    total_return: float
    
    # Match quality
    symbol_suitability: float  # From strategy matcher
    parameter_quality: float  # From parameter optimization
    
    # Combined score
    combined_score: float  # Weighted combination
    
    # Ranking
    rank: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['strategy_type'] = self.strategy_type.value
        return data


class JointOptimizer:
    """
    Jointly optimizes parameters and symbol selection.
    
    Features:
    - Cross-product search space
    - Pareto frontier analysis
    - Multi-objective optimization
    - Efficient search strategies
    """
    
    def __init__(self):
        """Initialize joint optimizer"""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.optimization_results: List[JointOptimizationResult] = []
        
        self.logger.info("JointOptimizer initialized")
    
    def optimize_joint(
        self,
        strategy_type: StrategyType,
        parameter_search_space: Dict[str, List[Any]],
        candidate_symbols: List[str],
        symbol_characteristics: Dict[str, SymbolCharacteristics],
        strategy_matcher: Any,
        backtest_function: Any,
        max_combinations: int = 100
    ) -> List[JointOptimizationResult]:
        """
        Perform joint parameter + symbol optimization.
        
        Args:
            strategy_type: Strategy to optimize
            parameter_search_space: Parameter grid
            candidate_symbols: List of candidate symbols
            symbol_characteristics: Symbol characteristics dict
            strategy_matcher: SymbolStrategyMatcher instance
            backtest_function: Function to run backtest
            max_combinations: Maximum combinations to test
            
        Returns:
            List of optimization results, ranked by combined score
        """
        self.logger.info(
            f"Starting joint optimization for {strategy_type.value}: "
            f"{len(candidate_symbols)} symbols x "
            f"{self._count_parameter_combinations(parameter_search_space)} parameters"
        )
        
        results = []
        
        # Pre-score symbols for this strategy
        symbol_scores = {}
        for symbol in candidate_symbols:
            if symbol in symbol_characteristics:
                match = strategy_matcher.match_symbol_to_strategy(
                    symbol_characteristics[symbol],
                    strategy_type
                )
                symbol_scores[symbol] = match.suitability_score
            else:
                symbol_scores[symbol] = 50.0  # Default
        
        # Filter symbols by minimum suitability
        suitable_symbols = [
            sym for sym, score in symbol_scores.items()
            if score >= 60.0
        ]
        
        self.logger.info(
            f"Filtered to {len(suitable_symbols)}/{len(candidate_symbols)} "
            f"suitable symbols (score >= 60)"
        )
        
        # Generate parameter combinations
        param_combinations = self._generate_parameter_combinations(
            parameter_search_space
        )
        
        # Limit total combinations
        total_combinations = len(suitable_symbols) * len(param_combinations)
        if total_combinations > max_combinations:
            # Sample parameters to stay within limit
            n_params_to_test = max_combinations // len(suitable_symbols)
            param_combinations = self._sample_parameters(
                param_combinations,
                n_params_to_test
            )
            
            self.logger.info(
                f"Limited parameter combinations to {len(param_combinations)} "
                f"(total: {len(suitable_symbols) * len(param_combinations)})"
            )
        
        # Test all symbol-parameter combinations
        tested = 0
        for symbol in suitable_symbols:
            for params in param_combinations:
                # Run backtest
                try:
                    backtest_result = backtest_function(
                        strategy_type=strategy_type,
                        symbol=symbol,
                        parameters=params
                    )
                    
                    # Create result
                    result = JointOptimizationResult(
                        strategy_type=strategy_type,
                        symbol=symbol,
                        parameters=params,
                        sharpe_ratio=backtest_result.get('sharpe_ratio', 0.0),
                        max_drawdown=backtest_result.get('max_drawdown', 1.0),
                        win_rate=backtest_result.get('win_rate', 0.0),
                        profit_factor=backtest_result.get('profit_factor', 0.0),
                        total_return=backtest_result.get('total_return', 0.0),
                        symbol_suitability=symbol_scores[symbol],
                        parameter_quality=self._score_parameters(backtest_result),
                        combined_score=0.0  # Will be calculated
                    )
                    
                    # Calculate combined score
                    result.combined_score = self._calculate_combined_score(result)
                    
                    results.append(result)
                    tested += 1
                    
                    if tested % 10 == 0:
                        self.logger.info(f"Progress: {tested} combinations tested")
                        
                except Exception as e:
                    self.logger.warning(
                        f"Backtest failed for {symbol} with {params}: {e}"
                    )
        
        # Rank results
        results.sort(key=lambda r: r.combined_score, reverse=True)
        for i, result in enumerate(results, 1):
            result.rank = i
        
        self.optimization_results.extend(results)
        
        self.logger.info(
            f"Joint optimization complete: tested {tested} combinations, "
            f"found {len(results)} results"
        )
        
        return results
    
    def _count_parameter_combinations(
        self,
        search_space: Dict[str, List[Any]]
    ) -> int:
        """Count total parameter combinations"""
        count = 1
        for values in search_space.values():
            count *= len(values)
        return count
    
    def _generate_parameter_combinations(
        self,
        search_space: Dict[str, List[Any]]
    ) -> List[Dict[str, Any]]:
        """Generate all parameter combinations"""
        keys = list(search_space.keys())
        values = [search_space[k] for k in keys]
        
        combinations = []
        for combo in product(*values):
            param_dict = dict(zip(keys, combo))
            combinations.append(param_dict)
        
        return combinations
    
    def _sample_parameters(
        self,
        combinations: List[Dict[str, Any]],
        n_samples: int
    ) -> List[Dict[str, Any]]:
        """Sample parameter combinations"""
        if len(combinations) <= n_samples:
            return combinations
        
        # Random sampling
        indices = np.random.choice(len(combinations), n_samples, replace=False)
        return [combinations[i] for i in indices]
    
    def _score_parameters(self, backtest_result: Dict[str, Any]) -> float:
        """Score parameter quality (0-100)"""
        
        sharpe = backtest_result.get('sharpe_ratio', 0.0)
        win_rate = backtest_result.get('win_rate', 0.0)
        
        # Normalize Sharpe (0-3 -> 0-100)
        sharpe_score = min(100, (sharpe / 3.0) * 100)
        
        # Win rate score
        win_rate_score = win_rate * 100
        
        # Combined
        return (sharpe_score * 0.7 + win_rate_score * 0.3)
    
    def _calculate_combined_score(
        self,
        result: JointOptimizationResult
    ) -> float:
        """Calculate combined optimization score"""
        
        # Performance component (70%)
        perf_score = result.parameter_quality
        
        # Symbol suitability component (30%)
        symbol_score = result.symbol_suitability
        
        # Combined with weights
        combined = (
            perf_score * 0.70 +
            symbol_score * 0.30
        )
        
        return combined
    
    def find_pareto_frontier(
        self,
        results: List[JointOptimizationResult],
        objective1: str = 'sharpe_ratio',
        objective2: str = 'symbol_suitability'
    ) -> List[JointOptimizationResult]:
        """
        Find Pareto frontier (non-dominated solutions).
        
        Args:
            results: Optimization results
            objective1: First objective to maximize
            objective2: Second objective to maximize
            
        Returns:
            Pareto-optimal results
        """
        pareto = []
        
        for r1 in results:
            is_dominated = False
            
            for r2 in results:
                if r1 == r2:
                    continue
                
                # Check if r1 is dominated by r2
                obj1_r1 = getattr(r1, objective1)
                obj1_r2 = getattr(r2, objective1)
                obj2_r1 = getattr(r1, objective2)
                obj2_r2 = getattr(r2, objective2)
                
                if (obj1_r2 >= obj1_r1 and obj2_r2 >= obj2_r1 and
                    (obj1_r2 > obj1_r1 or obj2_r2 > obj2_r1)):
                    is_dominated = True
                    break
            
            if not is_dominated:
                pareto.append(r1)
        
        self.logger.info(
            f"Found {len(pareto)} Pareto-optimal solutions "
            f"from {len(results)} results"
        )
        
        return pareto
    
    def get_best_by_strategy(
        self,
        results: List[JointOptimizationResult],
        strategy_type: StrategyType,
        top_n: int = 5
    ) -> List[JointOptimizationResult]:
        """Get top N results for a specific strategy"""
        
        strategy_results = [
            r for r in results
            if r.strategy_type == strategy_type
        ]
        
        strategy_results.sort(key=lambda r: r.combined_score, reverse=True)
        
        return strategy_results[:top_n]
    
    def get_best_by_symbol(
        self,
        results: List[JointOptimizationResult],
        symbol: str,
        top_n: int = 3
    ) -> List[JointOptimizationResult]:
        """Get top N strategies for a specific symbol"""
        
        symbol_results = [
            r for r in results
            if r.symbol == symbol
        ]
        
        symbol_results.sort(key=lambda r: r.combined_score, reverse=True)
        
        return symbol_results[:top_n]
    
    def generate_optimization_report(
        self,
        results: List[JointOptimizationResult]
    ) -> str:
        """Generate joint optimization report"""
        
        if not results:
            return "No optimization results available."
        
        # Top 10 overall
        top_10 = sorted(results, key=lambda r: r.combined_score, reverse=True)[:10]
        
        # Group by strategy
        by_strategy = {}
        for result in results:
            strategy = result.strategy_type.value
            if strategy not in by_strategy:
                by_strategy[strategy] = []
            by_strategy[strategy].append(result)
        
        # Build report
        report = []
        report.append("=" * 80)
        report.append("JOINT OPTIMIZATION REPORT (Parameters + Symbols)")
        report.append("=" * 80)
        report.append("")
        
        report.append(f"Total Configurations Tested: {len(results)}")
        report.append(f"Strategies: {len(by_strategy)}")
        report.append(f"Unique Symbols: {len(set(r.symbol for r in results))}")
        report.append("")
        
        report.append("TOP 10 OVERALL RESULTS:")
        report.append("-" * 80)
        for i, result in enumerate(top_10, 1):
            report.append(
                f"{i:2d}. {result.strategy_type.value:25s} | {result.symbol:6s} | "
                f"Score: {result.combined_score:5.1f} | "
                f"Sharpe: {result.sharpe_ratio:5.2f} | "
                f"WR: {result.win_rate*100:5.1f}%"
            )
        
        report.append("")
        report.append("BY STRATEGY:")
        report.append("-" * 80)
        for strategy, strategy_results in sorted(by_strategy.items()):
            best = max(strategy_results, key=lambda r: r.combined_score)
            report.append(
                f"{strategy:25s}: {len(strategy_results):3d} configs | "
                f"Best: {best.symbol} (score: {best.combined_score:.1f})"
            )
        
        report.append("")
        report.append("=" * 80)
        
        return "\n".join(report)


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    print("JointOptimizer initialized")
    print("Ready for joint parameter + symbol optimization")

