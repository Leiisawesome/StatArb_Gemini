"""
Strategy Optimizer Tests

Tests for StrategyOptimizer, ParameterSearchEngine, and PerformanceComparator.
"""

import pytest
import numpy as np
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from backtest.optimization.strategy_optimizer import (
    StrategyOptimizer,
    OptimizationResult
)
from backtest.optimization.parameter_search import (
    ParameterSearchEngine,
    SearchSpace
)
from backtest.optimization.performance_comparator import PerformanceComparator


class TestStrategyOptimizer:
    """Tests for StrategyOptimizer"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.optimizer = StrategyOptimizer()
        self.strategy_type = "momentum"
        self.symbols = ["NVDA", "TSLA"]
        self.search_space = {
            'lookback_period': [30, 60, 90],
            'momentum_threshold': [0.01, 0.02, 0.03]
        }
    
    def test_optimizer_initialization(self):
        """Test 1: Optimizer initializes correctly"""
        assert self.optimizer is not None
        assert self.optimizer.parameter_registry is not None
        assert self.optimizer.configuration_store is not None
        assert isinstance(self.optimizer.optimization_results, list)
    
    @pytest.mark.asyncio
    async def test_run_baseline_backtest(self):
        """Test 2: Baseline backtest runs for multiple symbols"""
        # Mock the _run_single_backtest method
        mock_result = OptimizationResult(
            strategy_type=self.strategy_type,
            symbol="NVDA",
            parameters={'test': 1},
            sharpe_ratio=1.8,
            max_drawdown=0.12,
            win_rate=0.58,
            profit_factor=1.7,
            total_return=0.25,
            trade_count=120
        )
        
        self.optimizer._run_single_backtest = AsyncMock(return_value=mock_result)
        
        # Run baseline
        results = await self.optimizer.run_baseline_backtest(
            self.strategy_type,
            self.symbols
        )
        
        assert len(results) == 2
        assert "NVDA" in results
        assert "TSLA" in results
    
    @pytest.mark.asyncio
    async def test_optimize_strategy_grid_search(self):
        """Test 3: Strategy optimization with grid search"""
        # Mock backtest
        mock_result = OptimizationResult(
            strategy_type=self.strategy_type,
            symbol="NVDA",
            parameters={'lookback_period': 60},
            sharpe_ratio=1.9,
            max_drawdown=0.10,
            win_rate=0.60,
            profit_factor=1.8,
            total_return=0.28,
            trade_count=130
        )
        
        self.optimizer._run_single_backtest = AsyncMock(return_value=mock_result)
        
        # Run optimization
        results = await self.optimizer.optimize_strategy(
            self.strategy_type,
            self.search_space,
            ["NVDA"],
            optimization_method="grid_search"
        )
        
        assert len(results) > 0
        assert all(isinstance(r, OptimizationResult) for r in results)
    
    def test_generate_grid_search_combinations(self):
        """Test 4: Grid search combinations generation"""
        combinations = self.optimizer._generate_grid_search_combinations(
            self.search_space
        )
        
        # Should have 3 * 3 = 9 combinations
        assert len(combinations) == 9
        
        # Check first combination structure
        assert 'lookback_period' in combinations[0]
        assert 'momentum_threshold' in combinations[0]
    
    def test_rank_results(self):
        """Test 5: Results ranking works correctly"""
        results = [
            OptimizationResult(
                strategy_type=self.strategy_type,
                symbol="NVDA",
                parameters={},
                sharpe_ratio=1.5,
                max_drawdown=0.15,
                win_rate=0.55,
                profit_factor=1.5,
                total_return=0.20,
                trade_count=100
            ),
            OptimizationResult(
                strategy_type=self.strategy_type,
                symbol="TSLA",
                parameters={},
                sharpe_ratio=2.0,  # Better
                max_drawdown=0.10,
                win_rate=0.60,
                profit_factor=1.8,
                total_return=0.30,
                trade_count=120
            )
        ]
        
        ranked = self.optimizer._rank_results(results)
        
        # Best should be first (highest Sharpe)
        assert ranked[0].sharpe_ratio == 2.0
        assert ranked[1].sharpe_ratio == 1.5
    
    def test_get_top_results(self):
        """Test 6: Get top N results"""
        # Add some results
        for i in range(15):
            result = OptimizationResult(
                strategy_type=self.strategy_type,
                symbol="NVDA",
                parameters={'test': i},
                sharpe_ratio=1.0 + i * 0.1,
                max_drawdown=0.15,
                win_rate=0.55,
                profit_factor=1.5,
                total_return=0.20,
                trade_count=100
            )
            self.optimizer.optimization_results.append(result)
        
        # Get top 5
        top_5 = self.optimizer.get_top_results(n=5)
        assert len(top_5) == 5
    
    def test_result_meets_criteria(self):
        """Test 7: Result criteria checking"""
        good_result = OptimizationResult(
            strategy_type=self.strategy_type,
            symbol="NVDA",
            parameters={},
            sharpe_ratio=2.0,
            max_drawdown=0.10,
            win_rate=0.60,
            profit_factor=2.0,
            total_return=0.30,
            trade_count=150
        )
        
        bad_result = OptimizationResult(
            strategy_type=self.strategy_type,
            symbol="TSLA",
            parameters={},
            sharpe_ratio=0.8,  # Too low
            max_drawdown=0.20,
            win_rate=0.45,
            profit_factor=0.9,
            total_return=0.05,
            trade_count=50
        )
        
        assert good_result.meets_criteria()
        assert not bad_result.meets_criteria()
    
    @pytest.mark.asyncio
    async def test_save_optimal_parameters(self):
        """Test 8: Save optimal parameters"""
        result = OptimizationResult(
            strategy_type=self.strategy_type,
            symbol="NVDA",
            parameters={'lookback_period': 60},
            sharpe_ratio=2.0,
            max_drawdown=0.10,
            win_rate=0.60,
            profit_factor=2.0,
            total_return=0.30,
            trade_count=150
        )
        
        success = await self.optimizer.save_optimal_parameters(result)
        assert success
        
        # Verify saved to registry
        params = self.optimizer.parameter_registry.get_parameters(
            self.strategy_type,
            "NVDA"
        )
        assert params == result.parameters
    
    def test_generate_optimization_report(self):
        """Test 9: Optimization report generation"""
        # Add some results
        for i in range(5):
            result = OptimizationResult(
                strategy_type=self.strategy_type,
                symbol="NVDA",
                parameters={'test': i},
                sharpe_ratio=1.5 + i * 0.1,
                max_drawdown=0.12,
                win_rate=0.58,
                profit_factor=1.7,
                total_return=0.25,
                trade_count=120
            )
            self.optimizer.optimization_results.append(result)
        
        report = self.optimizer.generate_optimization_report(self.strategy_type)
        
        assert 'strategy_type' in report
        assert 'total_configurations' in report
        assert report['total_configurations'] == 5
    
    def test_error_handling(self):
        """Test 10: Error handling works correctly"""
        # Test with empty results
        report = self.optimizer.generate_optimization_report("non_existent")
        assert 'error' in report


class TestParameterSearchEngine:
    """Tests for ParameterSearchEngine"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.search_engine = ParameterSearchEngine()
        self.search_space = SearchSpace(
            parameters={
                'param1': [1, 2, 3],
                'param2': [10, 20, 30]
            }
        )
    
    def test_search_engine_initialization(self):
        """Test 11: Search engine initializes"""
        assert self.search_engine is not None
    
    def test_search_space_validation(self):
        """Test 12: Search space validation"""
        # Valid space
        is_valid, error = self.search_space.validate()
        assert is_valid
        assert error is None
        
        # Invalid space (empty)
        empty_space = SearchSpace(parameters={})
        is_valid, error = empty_space.validate()
        assert not is_valid
    
    def test_grid_search(self):
        """Test 13: Grid search algorithm"""
        def objective(params):
            return params['param1'] + params['param2']
        
        results = self.search_engine.grid_search(
            self.search_space,
            objective,
            maximize=True
        )
        
        # Should have 9 results (3 * 3)
        assert len(results) == 9
        
        # Best should be (3, 30) = 33
        best_params, best_score = results[0]
        assert best_score == 33
    
    def test_random_search(self):
        """Test 14: Random search algorithm"""
        def objective(params):
            return params['param1'] * params['param2']
        
        results = self.search_engine.random_search(
            self.search_space,
            objective,
            n_iterations=20,
            maximize=True,
            seed=42
        )
        
        assert len(results) == 20
        assert all(isinstance(r[0], dict) for r in results)
    
    def test_search_time_estimation(self):
        """Test 15: Search time estimation"""
        estimate = self.search_engine.estimate_search_time(
            self.search_space,
            evaluation_time_seconds=1.0,
            method="grid_search"
        )
        
        assert 'n_evaluations' in estimate
        assert estimate['n_evaluations'] == 9  # 3 * 3
        assert estimate['total_seconds'] == 9.0


class TestPerformanceComparator:
    """Tests for PerformanceComparator"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.comparator = PerformanceComparator()
        self.results = [
            {
                'strategy_type': 'momentum',
                'symbol': 'NVDA',
                'sharpe_ratio': 1.8,
                'max_drawdown': 0.12,
                'win_rate': 0.58,
                'profit_factor': 1.7,
                'trade_count': 120,
                'parameters': {'lookback': 60}
            },
            {
                'strategy_type': 'momentum',
                'symbol': 'TSLA',
                'sharpe_ratio': 2.1,
                'max_drawdown': 0.10,
                'win_rate': 0.62,
                'profit_factor': 1.9,
                'trade_count': 150,
                'parameters': {'lookback': 90}
            }
        ]
    
    def test_comparator_initialization(self):
        """Test 16: Comparator initializes"""
        assert self.comparator is not None
        assert isinstance(self.comparator.comparison_history, list)
    
    def test_compare_strategies(self):
        """Test 17: Strategy comparison"""
        comparison = self.comparator.compare_strategies(
            self.results,
            primary_metric='sharpe_ratio'
        )
        
        assert comparison is not None
        assert comparison.best_item == "momentum:TSLA"  # Higher Sharpe
        assert len(comparison.compared_items) == 2
    
    def test_compare_parameters(self):
        """Test 18: Parameter comparison"""
        df = self.comparator.compare_parameters(
            self.results,
            'lookback',
            'sharpe_ratio'
        )
        
        assert len(df) > 0
        assert 'parameter_value' in df.columns
    
    def test_compare_symbols(self):
        """Test 19: Symbol comparison"""
        df = self.comparator.compare_symbols(
            self.results,
            'momentum',
            'sharpe_ratio'
        )
        
        assert len(df) == 2
        assert 'symbol' in df.columns
    
    def test_get_best_by_metric(self):
        """Test 20: Get best result by metric"""
        best = self.comparator.get_best_by_metric(
            self.results,
            'sharpe_ratio'
        )
        
        assert best is not None
        assert best['symbol'] == 'TSLA'  # Higher Sharpe
    
    def test_filter_by_criteria(self):
        """Test 21: Filter results by criteria"""
        # Use default criteria that both results should pass first
        filtered_all = self.comparator.filter_by_criteria(self.results)
        assert len(filtered_all) == 2  # Both should pass defaults
        
        # Now filter with stricter criteria - only TSLA should pass
        filtered = self.comparator.filter_by_criteria(
            self.results,
            min_sharpe=2.0,  # Only TSLA has 2.1
            max_dd=0.15,  # Both are < 0.15
            min_win_rate=0.55,  # Both > 0.55
            min_pf=1.0,  # Both > 1.0
            min_trades=100  # Both > 100
        )
        
        assert len(filtered) == 1
        assert filtered[0]['symbol'] == 'TSLA'
    
    def test_generate_comparison_report(self):
        """Test 22: Comparison report generation"""
        comparison = self.comparator.compare_strategies(
            self.results,
            primary_metric='sharpe_ratio'
        )
        
        report = self.comparator.generate_comparison_report(comparison)
        
        assert isinstance(report, str)
        assert "PERFORMANCE COMPARISON REPORT" in report
        assert "momentum:TSLA" in report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

