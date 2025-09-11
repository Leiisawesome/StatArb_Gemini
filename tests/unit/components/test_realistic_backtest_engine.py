#!/usr/bin/env python3
"""
Test Suite for Realistic Backtesting Engine
===========================================

Comprehensive test coverage for the realistic backtesting engine including:
- Realistic simulation with slippage and latency
- Market impact modeling
- Order rejection scenarios
- Performance attribution
- Risk management integration
- Multi-strategy backtesting
- Edge cases and error handling

Author: Test Coverage Implementation - Phase 3
"""

import pytest
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass

# Import backtesting engine classes
from core_structure.components.backtesting.realistic_backtest_engine import (
    RealisticBacktestEngine,
    BacktestConfig,
    BacktestResult
)

# Mock execution and portfolio components
try:
    from core_structure.components.execution.unified_execution_engine import (
        UnifiedExecutionEngine, ExecutionMode, ExecutionRequest, ExecutionResult
    )
    from core_structure.components.portfolio.unified_portfolio_bridge import (
        UnifiedPortfolioBridge, TradingMode as PortfolioTradingMode
    )
    from core_structure.components.risk.unified_risk_manager import (
        UnifiedRiskManager, RiskLimits, TradingMode as RiskTradingMode
    )
    COMPONENTS_AVAILABLE = True
except ImportError:
    COMPONENTS_AVAILABLE = False
    # Define mock classes
    class UnifiedExecutionEngine:
        pass
    class UnifiedPortfolioBridge:
        pass
    class UnifiedRiskManager:
        pass
    ExecutionMode = Mock()
    ExecutionRequest = Mock()
    ExecutionResult = Mock()
    PortfolioTradingMode = Mock()
    RiskLimits = Mock()
    RiskTradingMode = Mock()


class TestBacktestConfig:
    """Test cases for BacktestConfig dataclass"""

    def test_default_configuration(self):
        """Test default backtest configuration"""
        config = BacktestConfig()

        assert config.initial_capital == 100000.0
        assert isinstance(config.start_date, datetime)
        assert isinstance(config.end_date, datetime)
        assert config.enable_slippage == True
        assert config.enable_latency == True
        assert config.enable_market_impact == True
        assert config.enable_order_rejection == True
        assert config.base_slippage_bps == 2.0
        assert config.volatility_slippage_factor == 0.5
        assert config.size_impact_factor == 0.1
        assert config.default_volatility == 0.02
        assert config.default_spread_bps == 5.0
        assert config.liquidity_factor == 1.0
        assert config.risk_limits is None
        assert isinstance(config.strategy_allocations, dict)
        assert len(config.strategy_allocations) == 0
        assert config.benchmark_symbol == "SPY"
        assert config.risk_free_rate == 0.045

    def test_custom_configuration(self):
        """Test custom backtest configuration"""
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        risk_limits = Mock()  # Mock risk limits
        strategy_allocations = {"strategy1": 0.6, "strategy2": 0.4}

        config = BacktestConfig(
            initial_capital=500000.0,
            start_date=start_date,
            end_date=end_date,
            enable_slippage=False,
            enable_latency=False,
            enable_market_impact=False,
            enable_order_rejection=False,
            base_slippage_bps=5.0,
            volatility_slippage_factor=0.8,
            size_impact_factor=0.2,
            default_volatility=0.05,
            default_spread_bps=10.0,
            liquidity_factor=0.8,
            risk_limits=risk_limits,
            strategy_allocations=strategy_allocations,
            benchmark_symbol="QQQ",
            risk_free_rate=0.03
        )

        assert config.initial_capital == 500000.0
        assert config.start_date == start_date
        assert config.end_date == end_date
        assert config.enable_slippage == False
        assert config.enable_latency == False
        assert config.enable_market_impact == False
        assert config.enable_order_rejection == False
        assert config.base_slippage_bps == 5.0
        assert config.volatility_slippage_factor == 0.8
        assert config.size_impact_factor == 0.2
        assert config.default_volatility == 0.05
        assert config.default_spread_bps == 10.0
        assert config.liquidity_factor == 0.8
        assert config.risk_limits == risk_limits
        assert config.strategy_allocations == strategy_allocations
        assert config.benchmark_symbol == "QQQ"
        assert config.risk_free_rate == 0.03


class TestBacktestResult:
    """Test cases for BacktestResult dataclass"""

    def test_backtest_result_creation(self):
        """Test backtest result creation"""
        result = BacktestResult(
            total_return=0.15,
            total_return_pct=15.0,
            sharpe_ratio=1.8,
            max_drawdown=0.08,
            win_rate=0.65,
            total_trades=150,
            avg_slippage_bps=3.5,
            total_commission=750.0,
            avg_execution_time_ms=45.0,
            final_portfolio_value=115000.0,
            peak_portfolio_value=118000.0
        )

        assert result.total_return == 0.15
        assert result.total_return_pct == 15.0
        assert result.sharpe_ratio == 1.8
        assert result.max_drawdown == 0.08
        assert result.win_rate == 0.65
        assert result.total_trades == 150
        assert result.avg_slippage_bps == 3.5
        assert result.total_commission == 750.0
        assert result.avg_execution_time_ms == 45.0
        assert result.final_portfolio_value == 115000.0
        assert result.peak_portfolio_value == 118000.0

    def test_backtest_result_calculations(self):
        """Test backtest result calculations"""
        result = BacktestResult(
            total_return=0.25,
            total_return_pct=25.0,
            sharpe_ratio=2.1,
            max_drawdown=0.12,
            win_rate=0.70,
            total_trades=200,
            avg_slippage_bps=4.2,
            total_commission=1200.0,
            avg_execution_time_ms=38.0,
            final_portfolio_value=125000.0,
            peak_portfolio_value=130000.0
        )

        # Test derived calculations
        assert result.total_return > 0
        assert result.win_rate > 0.5
        assert result.sharpe_ratio > 1.0


class TestRealisticBacktestEngine:
    """Test cases for RealisticBacktestEngine class"""

    def setup_method(self):
        """Setup test fixtures"""
        self.config = BacktestConfig()
        self.engine = RealisticBacktestEngine(self.config)

        # Mock components if not available
        if not COMPONENTS_AVAILABLE:
            self.engine.execution_engine = Mock()
            self.engine.portfolio_bridge = Mock()
            self.engine.risk_manager = Mock()

    def test_initialization(self):
        """Test backtest engine initialization"""
        assert self.engine.config == self.config
        assert self.engine.initial_capital == self.config.initial_capital
        assert isinstance(self.engine.backtest_results, list)
        assert len(self.engine.backtest_results) == 0

    def test_load_market_data(self):
        """Test market data loading"""
        # Create sample market data
        data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=100, freq='1D'),
            'open': np.random.uniform(100, 110, 100),
            'high': np.random.uniform(105, 115, 100),
            'low': np.random.uniform(95, 105, 100),
            'close': np.random.uniform(100, 110, 100),
            'volume': np.random.randint(1000, 10000, 100)
        })

        self.engine.load_market_data("AAPL", data)

        # Check that data was loaded
        assert "AAPL" in self.engine.market_data
        assert isinstance(self.engine.market_data["AAPL"], pd.DataFrame)

    def test_set_execution_parameters(self):
        """Test execution parameter setting"""
        volatility = 0.03
        spread_bps = 8.0
        liquidity = 0.9

        self.engine.set_execution_parameters(volatility, spread_bps, liquidity)

        # Check that parameters were set
        assert self.engine.current_volatility == volatility
        assert self.engine.current_spread_bps == spread_bps
        assert self.engine.current_liquidity == liquidity

    def test_add_strategy(self):
        """Test strategy addition"""
        def sample_strategy(market_data, portfolio_state):
            return {"AAPL": 0.1}  # 10% allocation to AAPL

        self.engine.add_strategy("sample_strategy", sample_strategy)

        assert "sample_strategy" in self.engine.strategies
        assert self.engine.strategies["sample_strategy"] == sample_strategy

    def test_validate_backtest_setup(self):
        """Test backtest setup validation"""
        # Add minimal required components
        self.engine.load_market_data("AAPL", pd.DataFrame({'close': [100, 101, 102]}))

        def dummy_strategy(data, portfolio):
            return {}

        self.engine.add_strategy("dummy", dummy_strategy)

        is_valid, issues = self.engine.validate_backtest_setup()

        assert isinstance(is_valid, bool)
        assert isinstance(issues, list)

    def test_run_backtest_single_strategy(self):
        """Test running backtest with single strategy"""
        # Setup minimal backtest
        data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10, freq='1D'),
            'close': [100, 101, 102, 103, 104, 105, 106, 107, 108, 109]
        })
        self.engine.load_market_data("AAPL", data)

        def buy_and_hold_strategy(market_data, portfolio_state):
            return {"AAPL": 1.0}  # 100% allocation to AAPL

        self.engine.add_strategy("buy_and_hold", buy_and_hold_strategy)

        # Mock execution engine methods
        if hasattr(self.engine, 'execution_engine'):
            self.engine.execution_engine.execute_order = Mock(return_value=Mock(
                executed_quantity=100,
                executed_price=100.0,
                slippage_bps=2.0,
                commission=5.0
            ))

        results = self.engine.run_backtest()

        assert isinstance(results, list)
        assert len(results) > 0

    def test_run_backtest_multiple_strategies(self):
        """Test running backtest with multiple strategies"""
        # Setup market data
        data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=20, freq='1D'),
            'close': np.linspace(100, 120, 20)
        })
        self.engine.load_market_data("AAPL", data)
        self.engine.load_market_data("GOOGL", data * 2)  # Different scale

        # Add multiple strategies
        def strategy1(market_data, portfolio_state):
            return {"AAPL": 0.6, "GOOGL": 0.4}

        def strategy2(market_data, portfolio_state):
            return {"AAPL": 0.8, "GOOGL": 0.2}

        self.engine.add_strategy("strategy1", strategy1)
        self.engine.add_strategy("strategy2", strategy2)

        # Mock execution
        if hasattr(self.engine, 'execution_engine'):
            self.engine.execution_engine.execute_order = Mock(return_value=Mock(
                executed_quantity=100,
                executed_price=100.0,
                slippage_bps=2.0,
                commission=5.0
            ))

        results = self.engine.run_backtest()

        assert isinstance(results, list)
        assert len(results) >= 2  # At least one result per strategy

    def test_calculate_performance_metrics(self):
        """Test performance metrics calculation"""
        # Create sample portfolio values over time
        portfolio_values = [100000, 102000, 101000, 103000, 102500, 104000]
        trades = [
            Mock(executed_quantity=100, executed_price=100.0, slippage_bps=2.0, commission=5.0),
            Mock(executed_quantity=-50, executed_price=102.0, slippage_bps=1.5, commission=3.0)
        ]

        metrics = self.engine.calculate_performance_metrics(portfolio_values, trades)

        assert isinstance(metrics, BacktestResult)
        assert metrics.total_return >= 0
        assert metrics.total_trades == len(trades)
        assert metrics.avg_slippage_bps > 0
        assert metrics.total_commission > 0

    def test_apply_slippage_model(self):
        """Test slippage model application"""
        order_size = 1000
        current_price = 150.0
        volatility = 0.02

        slippage_price = self.engine.apply_slippage_model(order_size, current_price, volatility)

        assert isinstance(slippage_price, float)
        assert slippage_price != current_price  # Should be different due to slippage

    def test_simulate_market_impact(self):
        """Test market impact simulation"""
        order_size = 5000
        average_volume = 10000
        current_price = 200.0

        impacted_price = self.engine.simulate_market_impact(order_size, average_volume, current_price)

        assert isinstance(impacted_price, float)
        assert impacted_price != current_price  # Should be different due to impact

    def test_simulate_execution_latency(self):
        """Test execution latency simulation"""
        latency_ms = self.engine.simulate_execution_latency()

        assert isinstance(latency_ms, float)
        assert latency_ms > 0

    def test_generate_order_rejection(self):
        """Test order rejection generation"""
        # Test with different scenarios
        large_order = 100000  # Very large order
        rejection_prob_large = self.engine.generate_order_rejection_probability(large_order, 100000)
        assert rejection_prob_large > 0

        normal_order = 1000  # Normal order
        rejection_prob_normal = self.engine.generate_order_rejection_probability(normal_order, 100000)
        assert rejection_prob_normal >= 0

    def test_update_portfolio_state(self):
        """Test portfolio state updates"""
        initial_state = {
            "cash": 100000.0,
            "positions": {},
            "total_value": 100000.0
        }

        # Simulate a trade
        trade = Mock(
            symbol="AAPL",
            executed_quantity=100,
            executed_price=150.0,
            commission=7.5
        )

        new_state = self.engine.update_portfolio_state(initial_state, trade)

        assert isinstance(new_state, dict)
        assert new_state["cash"] < initial_state["cash"]  # Cash should decrease
        assert "AAPL" in new_state["positions"]
        assert new_state["total_value"] != initial_state["total_value"]

    def test_apply_risk_management(self):
        """Test risk management application"""
        portfolio_state = {
            "cash": 50000.0,
            "positions": {"AAPL": {"quantity": 1000, "avg_price": 150.0}},
            "total_value": 200000.0
        }

        risk_limits = Mock()
        risk_limits.max_position_size = 0.2
        risk_limits.max_drawdown = 0.1

        adjusted_allocations = self.engine.apply_risk_management(portfolio_state, risk_limits)

        assert isinstance(adjusted_allocations, dict)

    def test_calculate_benchmark_returns(self):
        """Test benchmark returns calculation"""
        benchmark_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10, freq='1D'),
            'close': [300, 302, 298, 305, 303, 308, 306, 310, 309, 312]
        })

        benchmark_returns = self.engine.calculate_benchmark_returns(benchmark_data)

        assert isinstance(benchmark_returns, list)
        assert len(benchmark_returns) == len(benchmark_data) - 1  # One less than data points

    def test_calculate_risk_metrics(self):
        """Test risk metrics calculation"""
        portfolio_values = [100000, 102000, 101000, 103000, 102500, 104000, 103000, 105000]

        risk_metrics = self.engine.calculate_risk_metrics(portfolio_values)

        assert isinstance(risk_metrics, dict)
        assert "max_drawdown" in risk_metrics
        assert "volatility" in risk_metrics
        assert "sharpe_ratio" in risk_metrics
        assert risk_metrics["max_drawdown"] >= 0
        assert risk_metrics["volatility"] >= 0

    def test_export_backtest_results(self):
        """Test backtest results export"""
        # Create sample results
        results = [
            BacktestResult(
                total_return=0.15,
                total_return_pct=15.0,
                sharpe_ratio=1.8,
                max_drawdown=0.08,
                win_rate=0.65,
                total_trades=150,
                avg_slippage_bps=3.5,
                total_commission=750.0,
                avg_execution_time_ms=45.0,
                final_portfolio_value=115000.0,
                peak_portfolio_value=118000.0
            )
        ]

        self.engine.backtest_results = results

        export_data = self.engine.export_backtest_results()

        assert isinstance(export_data, dict)
        assert "results" in export_data
        assert len(export_data["results"]) == len(results)

    def test_get_backtest_summary(self):
        """Test backtest summary generation"""
        # Create sample results
        results = [
            BacktestResult(
                total_return=0.15,
                total_return_pct=15.0,
                sharpe_ratio=1.8,
                max_drawdown=0.08,
                win_rate=0.65,
                total_trades=150,
                avg_slippage_bps=3.5,
                total_commission=750.0,
                avg_execution_time_ms=45.0,
                final_portfolio_value=115000.0,
                peak_portfolio_value=118000.0
            ),
            BacktestResult(
                total_return=0.08,
                total_return_pct=8.0,
                sharpe_ratio=1.2,
                max_drawdown=0.12,
                win_rate=0.55,
                total_trades=120,
                avg_slippage_bps=4.2,
                total_commission=600.0,
                avg_execution_time_ms=52.0,
                final_portfolio_value=108000.0,
                peak_portfolio_value=112000.0
            )
        ]

        self.engine.backtest_results = results

        summary = self.engine.get_backtest_summary()

        assert isinstance(summary, dict)
        assert "total_strategies" in summary
        assert "best_performing_strategy" in summary
        assert "average_return" in summary
        assert summary["total_strategies"] == len(results)


class TestRealisticBacktestEngineIntegration:
    """Integration tests for realistic backtest engine"""

    def setup_method(self):
        """Setup test fixtures"""
        self.config = BacktestConfig()
        self.engine = RealisticBacktestEngine(self.config)

    def test_complete_backtest_workflow(self):
        """Test complete backtest workflow"""
        # 1. Setup market data
        data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=50, freq='1D'),
            'open': np.random.uniform(100, 110, 50),
            'high': np.random.uniform(105, 115, 50),
            'low': np.random.uniform(95, 105, 50),
            'close': np.random.uniform(100, 110, 50),
            'volume': np.random.randint(1000, 10000, 50)
        })
        self.engine.load_market_data("AAPL", data)

        # 2. Add strategy
        def momentum_strategy(market_data, portfolio_state):
            # Simple momentum strategy
            if len(market_data) > 5:
                recent_returns = market_data['close'].pct_change().tail(5).mean()
                if recent_returns > 0.001:
                    return {"AAPL": 0.8}  # Go long
                elif recent_returns < -0.001:
                    return {"AAPL": -0.8}  # Go short
            return {"AAPL": 0.0}  # Neutral

        self.engine.add_strategy("momentum", momentum_strategy)

        # 3. Validate setup
        is_valid, issues = self.engine.validate_backtest_setup()
        assert isinstance(is_valid, bool)

        # 4. Run backtest (with mocked execution)
        if hasattr(self.engine, 'execution_engine'):
            self.engine.execution_engine.execute_order = Mock(return_value=Mock(
                executed_quantity=100,
                executed_price=105.0,
                slippage_bps=3.0,
                commission=5.25
            ))

        results = self.engine.run_backtest()

        # 5. Verify results
        assert isinstance(results, list)
        if len(results) > 0:
            result = results[0]
            assert isinstance(result, BacktestResult)
            assert hasattr(result, 'total_return')

    def test_multi_asset_backtest(self):
        """Test backtest with multiple assets"""
        # Setup data for multiple assets
        assets = ["AAPL", "GOOGL", "MSFT"]
        for asset in assets:
            data = pd.DataFrame({
                'timestamp': pd.date_range('2024-01-01', periods=30, freq='1D'),
                'close': np.random.uniform(100, 150, 30),
                'volume': np.random.randint(1000, 10000, 30)
            })
            self.engine.load_market_data(asset, data)

        # Multi-asset strategy
        def multi_asset_strategy(market_data, portfolio_state):
            allocations = {}
            for asset in assets:
                if asset in market_data:
                    allocations[asset] = 1.0 / len(assets)  # Equal weight
            return allocations

        self.engine.add_strategy("multi_asset", multi_asset_strategy)

        # Mock execution for multiple assets
        if hasattr(self.engine, 'execution_engine'):
            def mock_execute_order(request):
                return Mock(
                    executed_quantity=request.quantity,
                    executed_price=100.0,
                    slippage_bps=2.5,
                    commission=5.0
                )
            self.engine.execution_engine.execute_order = Mock(side_effect=mock_execute_order)

        results = self.engine.run_backtest()

        assert isinstance(results, list)

    def test_backtest_with_risk_management(self):
        """Test backtest with risk management"""
        # Setup data
        data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=40, freq='1D'),
            'close': np.random.uniform(100, 120, 40),
            'volume': np.random.randint(1000, 10000, 40)
        })
        self.engine.load_market_data("AAPL", data)

        # Strategy with position sizing
        def risk_aware_strategy(market_data, portfolio_state):
            volatility = market_data['close'].pct_change().std()
            if volatility < 0.02:  # Low volatility
                return {"AAPL": 0.5}
            else:  # High volatility
                return {"AAPL": 0.2}
            return {"AAPL": 0.0}

        self.engine.add_strategy("risk_aware", risk_aware_strategy)

        # Mock execution
        if hasattr(self.engine, 'execution_engine'):
            self.engine.execution_engine.execute_order = Mock(return_value=Mock(
                executed_quantity=100,
                executed_price=110.0,
                slippage_bps=2.0,
                commission=5.5
            ))

        results = self.engine.run_backtest()

        assert isinstance(results, list)

    def test_backtest_performance_comparison(self):
        """Test performance comparison between strategies"""
        # Setup data
        data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=60, freq='1D'),
            'close': np.linspace(100, 130, 60),  # Upward trend
            'volume': np.random.randint(1000, 10000, 60)
        })
        self.engine.load_market_data("AAPL", data)

        # Buy and hold strategy
        def buy_and_hold(market_data, portfolio_state):
            return {"AAPL": 1.0}

        # Mean reversion strategy
        def mean_reversion(market_data, portfolio_state):
            if len(market_data) > 10:
                current_price = market_data['close'].iloc[-1]
                ma_10 = market_data['close'].tail(10).mean()
                if current_price > ma_10 * 1.02:  # 2% above MA
                    return {"AAPL": -0.5}  # Short
                elif current_price < ma_10 * 0.98:  # 2% below MA
                    return {"AAPL": 0.5}  # Long
            return {"AAPL": 0.0}

        self.engine.add_strategy("buy_and_hold", buy_and_hold)
        self.engine.add_strategy("mean_reversion", mean_reversion)

        # Mock execution
        if hasattr(self.engine, 'execution_engine'):
            self.engine.execution_engine.execute_order = Mock(return_value=Mock(
                executed_quantity=100,
                executed_price=115.0,
                slippage_bps=2.5,
                commission=5.75
            ))

        results = self.engine.run_backtest()

        # Should have results for both strategies
        assert isinstance(results, list)
        assert len(results) >= 2

        # Check that results are different (strategies should perform differently)
        if len(results) >= 2:
            returns = [r.total_return for r in results]
            assert not all(r == returns[0] for r in returns)  # Not all identical


class TestRealisticBacktestEngineEdgeCases:
    """Test edge cases for realistic backtest engine"""

    def setup_method(self):
        """Setup test fixtures"""
        self.config = BacktestConfig()
        self.engine = RealisticBacktestEngine(self.config)

    def test_empty_market_data_handling(self):
        """Test handling of empty market data"""
        empty_data = pd.DataFrame()

        self.engine.load_market_data("EMPTY", empty_data)

        # Should handle gracefully
        assert "EMPTY" in self.engine.market_data

    def test_single_data_point_handling(self):
        """Test handling of single data point"""
        single_data = pd.DataFrame({
            'timestamp': [datetime.now()],
            'close': [100.0]
        })

        self.engine.load_market_data("SINGLE", single_data)

        assert "SINGLE" in self.engine.market_data
        assert len(self.engine.market_data["SINGLE"]) == 1

    def test_extreme_market_conditions(self):
        """Test handling of extreme market conditions"""
        # Create data with extreme volatility
        extreme_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=20, freq='1D'),
            'close': [100, 50, 200, 10, 500, 75, 300, 25, 400, 150,
                     80, 600, 30, 350, 90, 700, 45, 250, 120, 800],
            'volume': [1000] * 20
        })

        self.engine.load_market_data("EXTREME", extreme_data)

        # Should handle extreme conditions
        assert "EXTREME" in self.engine.market_data

    def test_zero_volume_handling(self):
        """Test handling of zero volume"""
        zero_volume_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10, freq='1D'),
            'close': np.linspace(100, 110, 10),
            'volume': [0] * 10
        })

        self.engine.load_market_data("ZERO_VOL", zero_volume_data)

        assert "ZERO_VOL" in self.engine.market_data

    def test_missing_strategy_handling(self):
        """Test handling when no strategies are added"""
        data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10, freq='1D'),
            'close': np.linspace(100, 110, 10)
        })
        self.engine.load_market_data("AAPL", data)

        # Try to run backtest without strategies
        results = self.engine.run_backtest()

        # Should handle gracefully
        assert isinstance(results, list)

    def test_invalid_strategy_function(self):
        """Test handling of invalid strategy function"""
        def invalid_strategy(market_data, portfolio_state):
            raise ValueError("Strategy error")

        self.engine.add_strategy("invalid", invalid_strategy)

        data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=5, freq='1D'),
            'close': [100, 101, 102, 103, 104]
        })
        self.engine.load_market_data("AAPL", data)

        # Should handle strategy errors gracefully
        results = self.engine.run_backtest()

        assert isinstance(results, list)

    def test_concurrent_backtest_execution(self):
        """Test concurrent backtest execution"""
        import threading

        results = []

        def run_backtest_instance(instance_id):
            config = BacktestConfig()
            engine = RealisticBacktestEngine(config)

            data = pd.DataFrame({
                'timestamp': pd.date_range('2024-01-01', periods=10, freq='1D'),
                'close': np.random.uniform(100, 110, 10)
            })
            engine.load_market_data("AAPL", data)

            def simple_strategy(market_data, portfolio_state):
                return {"AAPL": 0.5}

            engine.add_strategy("simple", simple_strategy)

            result = engine.run_backtest()
            results.append(result)

        # Run multiple backtests concurrently
        threads = []
        for i in range(5):
            thread = threading.Thread(target=run_backtest_instance, args=(i,))
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # All should complete
        assert len(results) == 5
        assert all(isinstance(r, list) for r in results)

    def test_memory_management_with_large_data(self):
        """Test memory management with large datasets"""
        # Create large dataset
        large_data = pd.DataFrame({
            'timestamp': pd.date_range('2020-01-01', periods=10000, freq='1min'),
            'close': np.random.uniform(100, 110, 10000),
            'volume': np.random.randint(1000, 10000, 10000)
        })

        self.engine.load_market_data("LARGE", large_data)

        assert "LARGE" in self.engine.market_data
        assert len(self.engine.market_data["LARGE"]) == 10000

    def test_backtest_timeout_handling(self):
        """Test handling of backtest timeouts"""
        # Create a strategy that takes a long time
        def slow_strategy(market_data, portfolio_state):
            import time
            time.sleep(0.1)  # Small delay
            return {"AAPL": 0.5}

        self.engine.add_strategy("slow", slow_strategy)

        data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=100, freq='1D'),
            'close': np.linspace(100, 120, 100)
        })
        self.engine.load_market_data("AAPL", data)

        # Should complete within reasonable time
        import time
        start_time = time.time()

        results = self.engine.run_backtest()

        end_time = time.time()
        duration = end_time - start_time

        assert duration < 30.0  # Should complete within 30 seconds
        assert isinstance(results, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
