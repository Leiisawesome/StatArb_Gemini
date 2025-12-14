#!/usr/bin/env python3
"""
Unit Tests for Enhanced TCA Analyzer
====================================

Comprehensive test coverage for transaction cost analysis functionality.

Test Coverage:
- TCA report generation and validation
- Benchmark price calculations (VWAP, TWAP, arrival)
- Cost calculations in basis points
- Slippage analysis and market impact
- Quality score calculations
- Aggregate statistics
- Error handling and edge cases

Author: StatArb_Gemini Test Suite
Date: November 4, 2025
"""

import pytest
import numpy as np
from unittest.mock import Mock
from dataclasses import dataclass

from core_engine.analytics.tca_analyzer import (
    EnhancedTCAAnalyzer,
    TCAReport
)

@dataclass
class MockExecutionResult:
    """Mock execution result for testing"""
    request_id: str = "test_exec_001"
    symbol: str = "AAPL"
    filled_quantity: float = 1000.0
    avg_fill_price: float = 150.0
    execution_time: float = 60.0  # seconds
    algorithm_used: str = "vwap"

class TestTCAReport:
    """Test TCA report data structure"""

    def test_tca_report_creation(self):
        """Test TCA report can be created with valid data"""
        report = TCAReport(
            execution_id="test_001",
            symbol="AAPL",
            side="buy",
            quantity=1000.0,
            arrival_price=150.0,
            vwap_benchmark=149.5,
            twap_benchmark=149.8,
            avg_fill_price=150.5,
            arrival_cost_bps=33.33,
            vwap_performance_bps=67.22,
            twap_performance_bps=47.24,
            implementation_shortfall_bps=33.33,
            realized_slippage_bps=33.33,
            expected_slippage_bps=25.0,
            slippage_surprise_bps=8.33,
            permanent_impact_bps=10.0,
            temporary_impact_bps=23.33,
            total_impact_bps=33.33,
            execution_time_seconds=60.0,
            opportunity_cost_bps=2.0,
            timing_cost_bps=1.0,
            commission_bps=3.33,
            total_cost_bps=37.66,
            overall_quality_score=85.0,
            execution_efficiency_score=90.0,
            timing_score=95.0,
            cost_score=85.0,
            algorithm_used="vwap"
        )

        assert report.execution_id == "test_001"
        assert report.symbol == "AAPL"
        assert report.side == "buy"
        assert report.quantity == 1000.0
        assert report.avg_fill_price == 150.5
        assert report.total_cost_bps == 37.66
        assert report.overall_quality_score == 85.0

    def test_tca_report_to_dict(self):
        """Test TCA report conversion to dictionary"""
        report = TCAReport(
            execution_id="test_001",
            symbol="AAPL",
            side="buy",
            quantity=1000.0,
            arrival_price=150.0,
            vwap_benchmark=149.5,
            twap_benchmark=149.8,
            avg_fill_price=150.5,
            arrival_cost_bps=33.33,
            vwap_performance_bps=67.22,
            twap_performance_bps=47.24,
            implementation_shortfall_bps=33.33,
            realized_slippage_bps=33.33,
            expected_slippage_bps=25.0,
            slippage_surprise_bps=8.33,
            permanent_impact_bps=10.0,
            temporary_impact_bps=23.33,
            total_impact_bps=33.33,
            execution_time_seconds=60.0,
            opportunity_cost_bps=2.0,
            timing_cost_bps=1.0,
            commission_bps=3.33,
            total_cost_bps=37.66,
            overall_quality_score=85.0,
            execution_efficiency_score=90.0,
            timing_score=95.0,
            cost_score=85.0,
            algorithm_used="vwap"
        )

        report_dict = report.to_dict()

        assert report_dict['execution_id'] == "test_001"
        assert report_dict['symbol'] == "AAPL"
        assert report_dict['quantity'] == 1000.0
        assert report_dict['avg_fill_price'] == 150.5
        assert report_dict['total_cost_bps'] == 37.66
        assert report_dict['overall_quality_score'] == 85.0
        assert 'timestamp' in report_dict

class TestEnhancedTCAAnalyzer:
    """Test Enhanced TCA Analyzer functionality"""

    @pytest.fixture
    def analyzer(self):
        """Create TCA analyzer instance"""
        return EnhancedTCAAnalyzer()

    @pytest.fixture
    def mock_execution_result(self):
        """Create mock execution result"""
        return MockExecutionResult()

    @pytest.mark.asyncio
    async def test_analyze_execution_success(self, analyzer, mock_execution_result):
        """Test successful execution analysis"""
        market_data = {
            'volatility': 0.02,
            'spread_bps': 5.0
        }

        report = await analyzer.analyze_execution(
            mock_execution_result,
            market_data
        )

        assert isinstance(report, TCAReport)
        assert report.execution_id == "test_exec_001"
        assert report.symbol == "AAPL"
        assert report.quantity == 1000.0
        assert report.avg_fill_price == 150.0
        assert report.algorithm_used == "vwap"

        # Verify all costs are calculated
        assert isinstance(report.total_cost_bps, (int, float))
        assert isinstance(report.overall_quality_score, (int, float))
        assert 0 <= report.overall_quality_score <= 100

        # Verify slippage calculations
        assert isinstance(report.realized_slippage_bps, (int, float))
        assert isinstance(report.expected_slippage_bps, (int, float))

        # Verify market impact
        assert isinstance(report.permanent_impact_bps, (int, float))
        assert isinstance(report.temporary_impact_bps, (int, float))
        assert abs(report.total_impact_bps - (report.permanent_impact_bps + report.temporary_impact_bps)) < 0.01

    @pytest.mark.asyncio
    async def test_analyze_execution_with_none_market_data(self, analyzer, mock_execution_result):
        """Test execution analysis with None market data"""
        report = await analyzer.analyze_execution(
            mock_execution_result,
            None
        )

        assert isinstance(report, TCAReport)
        assert report.execution_id == "test_exec_001"
        assert report.symbol == "AAPL"

    def test_calculate_bps_cost(self, analyzer):
        """Test basis points cost calculation"""
        # Positive cost (execution worse than benchmark)
        cost = analyzer._calculate_bps_cost(100.5, 100.0)
        assert cost == 50.0  # 50 bps

        # Negative cost (execution better than benchmark)
        cost = analyzer._calculate_bps_cost(99.5, 100.0)
        assert cost == -50.0  # -50 bps

        # Zero benchmark protection
        cost = analyzer._calculate_bps_cost(100.0, 0.0)
        assert cost == 0.0

    def test_estimate_expected_slippage(self, analyzer):
        """Test expected slippage estimation"""
        # Small quantity
        slippage = analyzer._estimate_expected_slippage(100.0, None)
        assert slippage > 0

        # Large quantity (should have higher slippage)
        large_slippage = analyzer._estimate_expected_slippage(10000.0, None)
        assert large_slippage > slippage

    def test_calculate_opportunity_cost(self, analyzer):
        """Test opportunity cost calculation"""
        # Short execution time
        cost = analyzer._calculate_opportunity_cost(30.0, None)
        assert cost > 0

        # Long execution time (higher cost)
        long_cost = analyzer._calculate_opportunity_cost(120.0, None)
        assert long_cost > cost

    def test_calculate_commission_bps(self, analyzer):
        """Test commission calculation in basis points"""
        # Standard commission calculation
        commission = analyzer._calculate_commission_bps(1000.0, 100.0)
        expected = (0.005 * 1000.0) / (1000.0 * 100.0) * 10000
        assert abs(commission - expected) < 0.01

        # Zero notional protection
        commission = analyzer._calculate_commission_bps(1000.0, 0.0)
        assert commission == 0.0

    def test_calculate_quality_score(self, analyzer):
        """Test overall quality score calculation"""
        # Excellent execution (< 5 bps)
        score = analyzer._calculate_quality_score(3.0)
        assert score == 100.0

        # Good execution (5-10 bps)
        score = analyzer._calculate_quality_score(7.5)
        assert 80.0 <= score <= 100.0

        # Fair execution (10-20 bps)
        score = analyzer._calculate_quality_score(15.0)
        assert 60.0 <= score <= 80.0

        # Poor execution (> 20 bps)
        score = analyzer._calculate_quality_score(25.0)
        assert score < 60.0

    def test_calculate_efficiency_score(self, analyzer):
        """Test execution efficiency score calculation"""
        # Better than expected (ratio < 0.8)
        score = analyzer._calculate_efficiency_score(7.9, 10.0)  # ratio = 0.79
        assert score == 100.0

        # Boundary case: exactly 0.8 ratio
        score = analyzer._calculate_efficiency_score(8.0, 10.0)  # ratio = 0.8
        assert score == 90.0  # Falls into elif since not < 0.8

        # As expected (0.8 <= ratio < 1.2)
        score = analyzer._calculate_efficiency_score(11.0, 10.0)  # ratio = 1.1
        assert score == 90.0

        # Slightly worse (1.2 <= ratio < 1.5)
        score = analyzer._calculate_efficiency_score(14.0, 10.0)  # ratio = 1.4
        assert score == 70.0

        # Much worse (ratio >= 1.5)
        score = analyzer._calculate_efficiency_score(20.0, 10.0)  # ratio = 2.0
        assert score == 50.0

        # Zero expected slippage protection
        score = analyzer._calculate_efficiency_score(5.0, 0.0)
        assert score == 100.0

    def test_calculate_timing_score(self, analyzer):
        """Test timing score calculation"""
        # Fast execution for small order
        score = analyzer._calculate_timing_score(30.0, 500.0)
        assert score >= 90.0

        # Slow execution for small order
        score = analyzer._calculate_timing_score(120.0, 500.0)
        assert score < 90.0

        # Reasonable execution for large order
        score = analyzer._calculate_timing_score(120.0, 2000.0)
        assert score >= 70.0

    def test_calculate_cost_score(self, analyzer):
        """Test cost score calculation (delegates to quality score)"""
        score = analyzer._calculate_cost_score(10.0)
        quality_score = analyzer._calculate_quality_score(10.0)
        assert score == quality_score

    @pytest.mark.asyncio
    async def test_analyze_execution_error_handling(self, analyzer):
        """Test error handling in execution analysis"""
        # Invalid execution result
        invalid_result = Mock()
        invalid_result.request_id = None
        invalid_result.symbol = None
        invalid_result.filled_quantity = None
        invalid_result.avg_fill_price = None
        invalid_result.execution_time = None
        invalid_result.algorithm_used = None

        report = await analyzer.analyze_execution(invalid_result, None)

        assert isinstance(report, TCAReport)
        assert report.execution_id == 'error'
        assert report.symbol == 'UNKNOWN'
        assert report.quantity == 0.0
        assert report.avg_fill_price == 0.0
        assert report.total_cost_bps == 0.0
        assert report.overall_quality_score == 0.0

    def test_get_aggregate_statistics_empty_history(self, analyzer):
        """Test aggregate statistics with no history"""
        stats = analyzer.get_aggregate_statistics()
        assert stats == {}

    @pytest.mark.asyncio
    async def test_get_aggregate_statistics_with_history(self, analyzer, mock_execution_result):
        """Test aggregate statistics with execution history"""
        # Add multiple executions
        for i in range(3):
            mock_result = MockExecutionResult(
                request_id=f"test_exec_{i}",
                symbol="AAPL",
                filled_quantity=1000.0 + i * 100,
                avg_fill_price=150.0 + i * 0.5
            )
            await analyzer.analyze_execution(mock_result, None)

        stats = analyzer.get_aggregate_statistics()

        assert stats['total_executions'] == 3
        assert 'avg_total_cost_bps' in stats
        assert 'avg_quality_score' in stats
        assert 'avg_slippage_bps' in stats
        assert 'best_execution' in stats
        assert 'worst_execution' in stats

        # Verify best/worst executions
        assert isinstance(stats['best_execution'], TCAReport)
        assert isinstance(stats['worst_execution'], TCAReport)

    @pytest.mark.asyncio
    async def test_benchmark_calculations(self, analyzer):
        """Test benchmark price calculations"""
        fill_price = 100.0

        # Mock the random number generator for consistent results
        np.random.seed(42)

        benchmarks = await analyzer._calculate_benchmarks("AAPL", fill_price, None)

        assert 'arrival_price' in benchmarks
        assert 'vwap' in benchmarks
        assert 'twap' in benchmarks

        # All benchmarks should be close to fill price (within 1%)
        for benchmark_name, benchmark_price in benchmarks.items():
            assert abs(benchmark_price - fill_price) / fill_price < 0.01

    def test_tca_history_storage(self, analyzer):
        """Test TCA report history storage"""
        assert len(analyzer.tca_history) == 0

        # Create a mock report and add it manually
        report = TCAReport(
            execution_id="manual_test",
            symbol="TEST",
            side="buy",
            quantity=100.0,
            arrival_price=100.0,
            vwap_benchmark=99.5,
            twap_benchmark=99.8,
            avg_fill_price=100.5,
            arrival_cost_bps=50.0,
            vwap_performance_bps=101.01,
            twap_performance_bps=71.07,
            implementation_shortfall_bps=50.0,
            realized_slippage_bps=50.0,
            expected_slippage_bps=31.62,
            slippage_surprise_bps=18.38,
            permanent_impact_bps=15.0,
            temporary_impact_bps=35.0,
            total_impact_bps=50.0,
            execution_time_seconds=60.0,
            opportunity_cost_bps=2.0,
            timing_cost_bps=1.0,
            commission_bps=5.0,
            total_cost_bps=58.0,
            overall_quality_score=60.0,
            execution_efficiency_score=70.0,
            timing_score=80.0,
            cost_score=60.0,
            algorithm_used="test"
        )

        analyzer.tca_history.append(report)
        assert len(analyzer.tca_history) == 1
        assert analyzer.tca_history[0].execution_id == "manual_test"

    def test_config_initialization(self):
        """Test analyzer initialization with custom config"""
        config = {'custom_setting': 'test_value'}
        analyzer = EnhancedTCAAnalyzer(config)

        assert analyzer.config == config

    @pytest.mark.asyncio
    async def test_market_impact_decomposition(self, analyzer, mock_execution_result):
        """Test market impact decomposition logic"""
        report = await analyzer.analyze_execution(mock_execution_result, None)

        # Verify permanent impact is 30% of realized slippage
        expected_permanent = abs(report.realized_slippage_bps) * 0.3
        assert abs(report.permanent_impact_bps - expected_permanent) < 0.01

        # Verify temporary impact is 70% of realized slippage
        expected_temporary = abs(report.realized_slippage_bps) * 0.7
        assert abs(report.temporary_impact_bps - expected_temporary) < 0.01

        # Verify total impact equals sum of components
        assert abs(report.total_impact_bps - (report.permanent_impact_bps + report.temporary_impact_bps)) < 0.01

    @pytest.mark.asyncio
    async def test_implementation_shortfall_calculation(self, analyzer, mock_execution_result):
        """Test implementation shortfall calculation"""
        report = await analyzer.analyze_execution(mock_execution_result, None)

        # Implementation shortfall should equal arrival cost
        assert report.implementation_shortfall_bps == report.arrival_cost_bps

    @pytest.mark.asyncio
    async def test_timing_cost_calculation(self, analyzer, mock_execution_result):
        """Test timing cost calculation"""
        report = await analyzer.analyze_execution(mock_execution_result, None)

        # Timing cost should be half of opportunity cost
        expected_timing_cost = report.opportunity_cost_bps * 0.5
        assert abs(report.timing_cost_bps - expected_timing_cost) < 0.01

    @pytest.mark.asyncio
    async def test_total_cost_composition(self, analyzer, mock_execution_result):
        """Test total cost includes all components"""
        report = await analyzer.analyze_execution(mock_execution_result, None)

        expected_total = (
            abs(report.arrival_cost_bps) +
            report.commission_bps +
            report.timing_cost_bps
        )

        assert abs(report.total_cost_bps - expected_total) < 0.01