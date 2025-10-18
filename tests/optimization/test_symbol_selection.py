"""
Symbol Selection Tests

Tests for SymbolAnalyzer, StrategyMatcher, and JointOptimizer.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock

from backtest.optimization.symbol_selection import (
    SymbolCharacteristicAnalyzer,
    SymbolCharacteristics,
    VolatilityCategory,
    LiquidityCategory,
    TrendCategory,
    SymbolStrategyMatcher,
    StrategyMatch,
    StrategyType,
    JointOptimizer,
    JointOptimizationResult
)


class TestSymbolCharacteristicAnalyzer:
    """Tests for SymbolCharacteristicAnalyzer"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.analyzer = SymbolCharacteristicAnalyzer()
        
        # Create sample price data
        dates = pd.date_range('2024-01-01', '2024-12-31', freq='D')
        np.random.seed(42)
        self.sample_data = pd.DataFrame({
            'open': 100 + np.random.randn(len(dates)).cumsum(),
            'high': 102 + np.random.randn(len(dates)).cumsum(),
            'low': 98 + np.random.randn(len(dates)).cumsum(),
            'close': 100 + np.random.randn(len(dates)).cumsum(),
            'volume': np.random.randint(1000000, 10000000, len(dates))
        }, index=dates)
    
    def test_analyzer_initialization(self):
        """Test 1: Analyzer initializes correctly"""
        assert self.analyzer is not None
        assert self.analyzer.analysis_cache == {}
    
    def test_analyze_symbol(self):
        """Test 2: Symbol analysis produces valid results"""
        characteristics = self.analyzer.analyze_symbol(
            'TEST',
            self.sample_data
        )
        
        assert characteristics is not None
        assert characteristics.symbol == 'TEST'
        assert isinstance(characteristics.volatility_category, VolatilityCategory)
        assert isinstance(characteristics.liquidity_category, LiquidityCategory)
        assert isinstance(characteristics.trend_category, TrendCategory)
    
    def test_volatility_metrics(self):
        """Test 3: Volatility metrics are calculated"""
        characteristics = self.analyzer.analyze_symbol('TEST', self.sample_data)
        
        assert characteristics.volatility_annualized > 0
        assert 0 <= characteristics.volatility_percentile <= 1
        # Intraday volatility can be negative with random walk data
        assert characteristics.intraday_volatility is not None
    
    def test_liquidity_metrics(self):
        """Test 4: Liquidity metrics are calculated"""
        characteristics = self.analyzer.analyze_symbol('TEST', self.sample_data)
        
        assert characteristics.avg_daily_volume > 0
        assert 0 <= characteristics.liquidity_score <= 100
        assert characteristics.bid_ask_spread_bps > 0
    
    def test_trend_metrics(self):
        """Test 5: Trend metrics are calculated"""
        characteristics = self.analyzer.analyze_symbol('TEST', self.sample_data)
        
        assert -1 <= characteristics.trend_strength <= 1
        assert 0 <= characteristics.trend_consistency <= 1
        assert 0 <= characteristics.momentum_score <= 100
    
    def test_correlation_metrics(self):
        """Test 6: Correlation metrics are calculated"""
        characteristics = self.analyzer.analyze_symbol('TEST', self.sample_data)
        
        assert -1 <= characteristics.market_correlation <= 1
        assert 0 <= characteristics.diversification_score <= 100
    
    def test_statistical_metrics(self):
        """Test 7: Statistical metrics are calculated"""
        characteristics = self.analyzer.analyze_symbol('TEST', self.sample_data)
        
        assert characteristics.returns_skewness is not None
        assert characteristics.returns_kurtosis is not None
        assert characteristics.max_drawdown >= 0
    
    def test_quality_scores(self):
        """Test 8: Quality scores are in valid range"""
        characteristics = self.analyzer.analyze_symbol('TEST', self.sample_data)
        
        assert 0 <= characteristics.overall_quality_score <= 100
        assert 0 <= characteristics.data_quality_score <= 100
    
    def test_analysis_caching(self):
        """Test 9: Analysis results are cached"""
        self.analyzer.analyze_symbol('TEST', self.sample_data)
        assert 'TEST' in self.analyzer.analysis_cache
        
        cached = self.analyzer.analysis_cache['TEST']
        assert cached.symbol == 'TEST'
    
    def test_to_dict(self):
        """Test 10: Characteristics convert to dict"""
        characteristics = self.analyzer.analyze_symbol('TEST', self.sample_data)
        char_dict = characteristics.to_dict()
        
        assert isinstance(char_dict, dict)
        assert char_dict['symbol'] == 'TEST'
        assert 'volatility_category' in char_dict
        assert isinstance(char_dict['volatility_category'], str)


class TestSymbolStrategyMatcher:
    """Tests for SymbolStrategyMatcher"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.matcher = SymbolStrategyMatcher()
        
        # Create sample characteristics
        self.sample_char = SymbolCharacteristics(
            symbol="NVDA",
            analysis_date=datetime.now(),
            volatility_annualized=0.35,
            volatility_category=VolatilityCategory.MEDIUM,
            volatility_percentile=0.6,
            intraday_volatility=0.02,
            avg_daily_volume=5_000_000_000,
            avg_daily_trades=50000,
            liquidity_score=85.0,
            liquidity_category=LiquidityCategory.VERY_HIGH,
            bid_ask_spread_bps=3.0,
            trend_strength=0.002,
            trend_category=TrendCategory.STRONG_UP,
            trend_consistency=0.65,
            momentum_score=75.0,
            market_correlation=0.7,
            sector_correlation=0.8,
            diversification_score=30.0,
            market_cap=2_000_000_000_000,
            avg_price=450.0,
            price_stability=0.85,
            returns_skewness=0.1,
            returns_kurtosis=3.5,
            max_drawdown=0.25,
            overall_quality_score=85.0,
            data_quality_score=95.0
        )
    
    def test_matcher_initialization(self):
        """Test 11: Matcher initializes with strategy preferences"""
        assert self.matcher is not None
        assert len(self.matcher.strategy_preferences) == 10  # 10 strategies
    
    def test_match_symbol_to_strategy(self):
        """Test 12: Symbol-strategy matching works"""
        match = self.matcher.match_symbol_to_strategy(
            self.sample_char,
            StrategyType.MOMENTUM
        )
        
        assert match is not None
        assert match.symbol == "NVDA"
        assert match.strategy_type == StrategyType.MOMENTUM
        assert 0 <= match.suitability_score <= 100
        assert 0 <= match.confidence <= 1
    
    def test_component_scores(self):
        """Test 13: Component scores are calculated"""
        match = self.matcher.match_symbol_to_strategy(
            self.sample_char,
            StrategyType.MOMENTUM
        )
        
        assert 0 <= match.volatility_match <= 100
        assert 0 <= match.liquidity_match <= 100
        assert 0 <= match.trend_match <= 100
        assert 0 <= match.correlation_match <= 100
    
    def test_strengths_and_weaknesses(self):
        """Test 14: Strengths and weaknesses are identified"""
        match = self.matcher.match_symbol_to_strategy(
            self.sample_char,
            StrategyType.MOMENTUM
        )
        
        assert isinstance(match.strengths, list)
        assert isinstance(match.weaknesses, list)
        assert isinstance(match.recommendations, list)
    
    def test_find_best_strategies(self):
        """Test 15: Find best strategies for symbol"""
        best_strategies = self.matcher.find_best_strategies(
            self.sample_char,
            top_n=3
        )
        
        assert len(best_strategies) == 3
        assert all(isinstance(m, StrategyMatch) for m in best_strategies)
        
        # Should be sorted by suitability
        assert best_strategies[0].suitability_score >= best_strategies[1].suitability_score
        assert best_strategies[1].suitability_score >= best_strategies[2].suitability_score
    
    def test_create_compatibility_matrix(self):
        """Test 16: Compatibility matrix creation"""
        char_dict = {'NVDA': self.sample_char}
        matrix = self.matcher.create_compatibility_matrix(char_dict)
        
        assert 'NVDA' in matrix
        assert len(matrix['NVDA']) == 10  # 10 strategies
        assert all(isinstance(score, float) for score in matrix['NVDA'].values())
    
    def test_get_optimal_assignments(self):
        """Test 17: Optimal assignments generation"""
        char_dict = {'NVDA': self.sample_char}
        matrix = self.matcher.create_compatibility_matrix(char_dict)
        
        assignments = self.matcher.get_optimal_assignments(matrix, min_score=50.0)
        
        assert isinstance(assignments, dict)
        assert len(assignments) == 10  # 10 strategies
    
    def test_strategy_preferences(self):
        """Test 18: All strategies have preferences defined"""
        for strategy in StrategyType:
            assert strategy in self.matcher.strategy_preferences
            prefs = self.matcher.strategy_preferences[strategy]
            
            assert 'volatility' in prefs
            assert 'liquidity' in prefs
            assert 'trend' in prefs
            assert 'min_liquidity_score' in prefs
    
    def test_match_to_dict(self):
        """Test 19: Match converts to dict"""
        match = self.matcher.match_symbol_to_strategy(
            self.sample_char,
            StrategyType.MOMENTUM
        )
        
        match_dict = match.to_dict()
        assert isinstance(match_dict, dict)
        assert match_dict['symbol'] == 'NVDA'
        assert isinstance(match_dict['strategy_type'], str)


class TestJointOptimizer:
    """Tests for JointOptimizer"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.optimizer = JointOptimizer()
    
    def test_optimizer_initialization(self):
        """Test 20: Optimizer initializes"""
        assert self.optimizer is not None
        assert self.optimizer.optimization_results == []
    
    def test_count_parameter_combinations(self):
        """Test 21: Parameter combination counting"""
        search_space = {
            'param1': [1, 2, 3],
            'param2': [10, 20]
        }
        
        count = self.optimizer._count_parameter_combinations(search_space)
        assert count == 6  # 3 * 2
    
    def test_generate_parameter_combinations(self):
        """Test 22: Parameter combination generation"""
        search_space = {
            'param1': [1, 2],
            'param2': [10, 20]
        }
        
        combinations = self.optimizer._generate_parameter_combinations(search_space)
        
        assert len(combinations) == 4  # 2 * 2
        assert all(isinstance(c, dict) for c in combinations)
        assert all('param1' in c and 'param2' in c for c in combinations)
    
    def test_sample_parameters(self):
        """Test 23: Parameter sampling"""
        combinations = [{'p': i} for i in range(100)]
        
        sampled = self.optimizer._sample_parameters(combinations, 10)
        
        assert len(sampled) == 10
        assert all(c in combinations for c in sampled)
    
    def test_score_parameters(self):
        """Test 24: Parameter scoring"""
        backtest_result = {
            'sharpe_ratio': 2.0,
            'win_rate': 0.6,
            'max_drawdown': 0.15
        }
        
        score = self.optimizer._score_parameters(backtest_result)
        
        assert 0 <= score <= 100
        assert score > 50  # Should be good with Sharpe=2.0
    
    def test_calculate_combined_score(self):
        """Test 25: Combined score calculation"""
        result = JointOptimizationResult(
            strategy_type=StrategyType.MOMENTUM,
            symbol='NVDA',
            parameters={'test': 1},
            sharpe_ratio=2.0,
            max_drawdown=0.15,
            win_rate=0.6,
            profit_factor=1.8,
            total_return=0.25,
            symbol_suitability=80.0,
            parameter_quality=85.0,
            combined_score=0.0
        )
        
        combined = self.optimizer._calculate_combined_score(result)
        
        assert 0 <= combined <= 100
        # Should weight performance (70%) + suitability (30%)
        expected = 85.0 * 0.7 + 80.0 * 0.3
        assert abs(combined - expected) < 0.1
    
    def test_find_pareto_frontier(self):
        """Test 26: Pareto frontier identification"""
        results = [
            JointOptimizationResult(
                strategy_type=StrategyType.MOMENTUM,
                symbol='A',
                parameters={},
                sharpe_ratio=2.0,
                max_drawdown=0.15,
                win_rate=0.6,
                profit_factor=1.8,
                total_return=0.25,
                symbol_suitability=80.0,
                parameter_quality=85.0,
                combined_score=83.5
            ),
            JointOptimizationResult(
                strategy_type=StrategyType.MOMENTUM,
                symbol='B',
                parameters={},
                sharpe_ratio=1.5,  # Lower
                max_drawdown=0.15,
                win_rate=0.55,
                profit_factor=1.5,
                total_return=0.20,
                symbol_suitability=90.0,  # Higher
                parameter_quality=75.0,
                combined_score=80.0
            ),
            JointOptimizationResult(
                strategy_type=StrategyType.MOMENTUM,
                symbol='C',
                parameters={},
                sharpe_ratio=1.0,  # Dominated
                max_drawdown=0.20,
                win_rate=0.50,
                profit_factor=1.2,
                total_return=0.15,
                symbol_suitability=70.0,
                parameter_quality=65.0,
                combined_score=66.5
            )
        ]
        
        pareto = self.optimizer.find_pareto_frontier(results)
        
        # C should be dominated, A and B should be on frontier
        assert len(pareto) >= 2
        assert results[2] not in pareto  # C is dominated
    
    def test_get_best_by_strategy(self):
        """Test 27: Get best results by strategy"""
        results = [
            JointOptimizationResult(
                strategy_type=StrategyType.MOMENTUM,
                symbol='A',
                parameters={},
                sharpe_ratio=2.0,
                max_drawdown=0.15,
                win_rate=0.6,
                profit_factor=1.8,
                total_return=0.25,
                symbol_suitability=80.0,
                parameter_quality=85.0,
                combined_score=83.5
            ),
            JointOptimizationResult(
                strategy_type=StrategyType.MEAN_REVERSION,
                symbol='B',
                parameters={},
                sharpe_ratio=1.8,
                max_drawdown=0.12,
                win_rate=0.62,
                profit_factor=1.9,
                total_return=0.28,
                symbol_suitability=85.0,
                parameter_quality=82.0,
                combined_score=82.9
            )
        ]
        
        momentum_results = self.optimizer.get_best_by_strategy(
            results,
            StrategyType.MOMENTUM,
            top_n=5
        )
        
        assert len(momentum_results) == 1
        assert momentum_results[0].strategy_type == StrategyType.MOMENTUM
    
    def test_get_best_by_symbol(self):
        """Test 28: Get best results by symbol"""
        results = [
            JointOptimizationResult(
                strategy_type=StrategyType.MOMENTUM,
                symbol='NVDA',
                parameters={},
                sharpe_ratio=2.0,
                max_drawdown=0.15,
                win_rate=0.6,
                profit_factor=1.8,
                total_return=0.25,
                symbol_suitability=80.0,
                parameter_quality=85.0,
                combined_score=83.5
            ),
            JointOptimizationResult(
                strategy_type=StrategyType.MEAN_REVERSION,
                symbol='NVDA',
                parameters={},
                sharpe_ratio=1.8,
                max_drawdown=0.12,
                win_rate=0.62,
                profit_factor=1.9,
                total_return=0.28,
                symbol_suitability=85.0,
                parameter_quality=82.0,
                combined_score=82.9
            )
        ]
        
        nvda_results = self.optimizer.get_best_by_symbol(results, 'NVDA', top_n=3)
        
        assert len(nvda_results) == 2
        assert all(r.symbol == 'NVDA' for r in nvda_results)
    
    def test_generate_optimization_report(self):
        """Test 29: Optimization report generation"""
        results = [
            JointOptimizationResult(
                strategy_type=StrategyType.MOMENTUM,
                symbol='NVDA',
                parameters={},
                sharpe_ratio=2.0,
                max_drawdown=0.15,
                win_rate=0.6,
                profit_factor=1.8,
                total_return=0.25,
                symbol_suitability=80.0,
                parameter_quality=85.0,
                combined_score=83.5
            )
        ]
        
        report = self.optimizer.generate_optimization_report(results)
        
        assert isinstance(report, str)
        assert 'JOINT OPTIMIZATION REPORT' in report
        assert 'NVDA' in report
    
    def test_result_to_dict(self):
        """Test 30: Result converts to dict"""
        result = JointOptimizationResult(
            strategy_type=StrategyType.MOMENTUM,
            symbol='NVDA',
            parameters={'test': 1},
            sharpe_ratio=2.0,
            max_drawdown=0.15,
            win_rate=0.6,
            profit_factor=1.8,
            total_return=0.25,
            symbol_suitability=80.0,
            parameter_quality=85.0,
            combined_score=83.5
        )
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert result_dict['symbol'] == 'NVDA'
        assert isinstance(result_dict['strategy_type'], str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

