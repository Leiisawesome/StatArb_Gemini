#!/usr/bin/env python3
"""
Test Suite for Unified Execution Engine
=======================================

Comprehensive test coverage for the unified execution engine including:
- Realistic execution simulation
- Slippage modeling
- Latency simulation
- Multi-mode execution (backtesting, paper trading, live trading)
- Pair trade execution
- Error handling and edge cases

Author: Test Coverage Implementation - Phase 3
"""

import pytest
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, List, Optional

# Import the execution engine and related classes
from core_structure.components.execution.unified_execution_engine import (
    UnifiedExecutionEngine,
    ExecutionMode,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    MarketConditions,
    SlippageModel,
    LatencySimulator
)


class TestSlippageModel:
    """Test cases for slippage modeling"""

    def setup_method(self):
        """Setup test fixtures"""
        self.model = SlippageModel()
        self.market_conditions = MarketConditions(
            volatility=0.02,
            bid_ask_spread_bps=5.0,
            market_impact_factor=1.0,
            liquidity_factor=1.0
        )

    def test_calculate_slippage_normal_conditions(self):
        """Test slippage calculation under normal market conditions"""
        request = ExecutionRequest(
            request_id="test_001",
            strategy_id="test_strategy",
            symbol="AAPL",
            side="BUY",
            quantity=100,
            order_type="MARKET",
            price=150.0
        )

        slippage = self.model.calculate_slippage(request, self.market_conditions, 100000.0)

        # Should be positive (adverse to trader)
        assert slippage > 0
        # Should be reasonable (less than 10bps under normal conditions)
        assert slippage < 10.0

    def test_calculate_slippage_high_volatility(self):
        """Test slippage calculation with high volatility"""
        high_vol_conditions = MarketConditions(
            volatility=0.10,  # High volatility
            bid_ask_spread_bps=5.0,
            market_impact_factor=1.0,
            liquidity_factor=1.0
        )

        request = ExecutionRequest(
            request_id="test_002",
            strategy_id="test_strategy",
            symbol="AAPL",
            side="BUY",
            quantity=100,
            order_type="MARKET",
            price=150.0
        )

        slippage = self.model.calculate_slippage(request, high_vol_conditions, 100000.0)

        # Should be higher due to volatility
        assert slippage > 2.0  # Base slippage

    def test_calculate_slippage_large_order(self):
        """Test slippage calculation for large orders"""
        request = ExecutionRequest(
            request_id="test_003",
            strategy_id="test_strategy",
            symbol="AAPL",
            side="BUY",
            quantity=10000,  # Large order
            order_type="MARKET",
            price=150.0
        )

        slippage = self.model.calculate_slippage(request, self.market_conditions, 100000.0)

        # Should be higher due to size impact
        assert slippage > 2.0  # Base slippage

    def test_calculate_slippage_urgent_order(self):
        """Test slippage calculation for urgent orders"""
        request = ExecutionRequest(
            request_id="test_004",
            strategy_id="test_strategy",
            symbol="AAPL",
            side="BUY",
            quantity=100,
            order_type="MARKET",
            price=150.0,
            urgency="URGENT"
        )

        slippage = self.model.calculate_slippage(request, self.market_conditions, 100000.0)

        # Should be higher due to urgency
        assert slippage > 2.0  # Base slippage

    def test_calculate_slippage_low_liquidity(self):
        """Test slippage calculation with low liquidity"""
        low_liq_conditions = MarketConditions(
            volatility=0.02,
            bid_ask_spread_bps=5.0,
            market_impact_factor=1.0,
            liquidity_factor=0.3  # Low liquidity
        )

        request = ExecutionRequest(
            request_id="test_005",
            strategy_id="test_strategy",
            symbol="AAPL",
            side="BUY",
            quantity=100,
            order_type="MARKET",
            price=150.0
        )

        slippage = self.model.calculate_slippage(request, low_liq_conditions, 100000.0)

        # Should be higher due to low liquidity
        assert slippage > 2.0  # Base slippage


class TestLatencySimulator:
    """Test cases for latency simulation"""

    def test_backtesting_mode_latencies(self):
        """Test latency parameters for backtesting mode"""
        simulator = LatencySimulator(ExecutionMode.BACKTESTING)

        # Check latency ranges
        latencies = simulator.latencies[ExecutionMode.BACKTESTING]
        assert latencies["processing"] == (1, 5)
        assert latencies["network"] == (0, 2)
        assert latencies["venue"] == (5, 20)

    def test_paper_trading_mode_latencies(self):
        """Test latency parameters for paper trading mode"""
        simulator = LatencySimulator(ExecutionMode.PAPER_TRADING)

        latencies = simulator.latencies[ExecutionMode.PAPER_TRADING]
        assert latencies["processing"] == (5, 15)
        assert latencies["network"] == (10, 50)
        assert latencies["venue"] == (20, 100)

    def test_live_trading_mode_latencies(self):
        """Test latency parameters for live trading mode"""
        simulator = LatencySimulator(ExecutionMode.LIVE_TRADING)

        latencies = simulator.latencies[ExecutionMode.LIVE_TRADING]
        assert latencies["processing"] == (2, 8)
        assert latencies["network"] == (5, 30)
        assert latencies["venue"] == (10, 80)

    @pytest.mark.asyncio
    async def test_add_execution_delay_backtesting(self):
        """Test execution delay in backtesting mode (should not actually delay)"""
        simulator = LatencySimulator(ExecutionMode.BACKTESTING)
        request = ExecutionRequest(
            request_id="test_001",
            strategy_id="test_strategy",
            symbol="AAPL",
            side="BUY",
            quantity=100,
            order_type="MARKET"
        )

        start_time = datetime.now()
        delay = await simulator.add_execution_delay(request)
        end_time = datetime.now()

        # Should return a delay value
        assert delay > 0
        # Should not have actually delayed (backtesting mode)
        assert (end_time - start_time).total_seconds() < 0.1

    @pytest.mark.asyncio
    async def test_add_execution_delay_urgent_order(self):
        """Test execution delay for urgent orders"""
        simulator = LatencySimulator(ExecutionMode.PAPER_TRADING)
        request = ExecutionRequest(
            request_id="test_002",
            strategy_id="test_strategy",
            symbol="AAPL",
            side="BUY",
            quantity=100,
            order_type="MARKET",
            urgency="URGENT"
        )

        delay = await simulator.add_execution_delay(request)

        # Should be faster than normal
        assert delay > 0
        # Urgent orders should have reduced latency
        assert delay < 0.2  # Less than 200ms for urgent orders


class TestUnifiedExecutionEngine:
    """Test cases for the unified execution engine"""

    def setup_method(self):
        """Setup test fixtures"""
        self.engine = UnifiedExecutionEngine(
            mode=ExecutionMode.BACKTESTING,
            initial_capital=100000.0
        )

        # Set up market data
        self.engine.update_market_data("AAPL", 150.0)
        self.engine.update_market_data("GOOGL", 2800.0)

    def test_initialization(self):
        """Test engine initialization"""
        assert self.engine.mode == ExecutionMode.BACKTESTING
        assert self.engine.initial_capital == 100000.0
        assert len(self.engine.execution_history) == 0
        assert len(self.engine.pending_executions) == 0

    def test_update_market_conditions(self):
        """Test market conditions update"""
        conditions = MarketConditions(
            volatility=0.03,
            bid_ask_spread_bps=7.0,
            market_impact_factor=1.2,
            liquidity_factor=0.8
        )

        self.engine.update_market_conditions(conditions)

        assert self.engine.market_conditions.volatility == 0.03
        assert self.engine.market_conditions.bid_ask_spread_bps == 7.0

    def test_update_market_data(self):
        """Test market data updates"""
        timestamp = datetime.now()

        self.engine.update_market_data("TSLA", 800.0, timestamp)

        assert self.engine.current_prices["TSLA"] == 800.0
        assert len(self.engine.price_history["TSLA"]) == 1
        assert self.engine.price_history["TSLA"][0] == (timestamp, 800.0)

    @pytest.mark.asyncio
    async def test_validate_execution_request_valid(self):
        """Test validation of valid execution request"""
        request = ExecutionRequest(
            request_id="test_001",
            strategy_id="test_strategy",
            symbol="AAPL",
            side="BUY",
            quantity=100,
            order_type="MARKET"
        )

        is_valid, message = await self.engine._validate_execution_request(request)

        assert is_valid is True
        assert message == "Valid"

    @pytest.mark.asyncio
    async def test_validate_execution_request_no_market_data(self):
        """Test validation when no market data is available"""
        request = ExecutionRequest(
            request_id="test_002",
            strategy_id="test_strategy",
            symbol="UNKNOWN",
            side="BUY",
            quantity=100,
            order_type="MARKET"
        )

        is_valid, message = await self.engine._validate_execution_request(request)

        assert is_valid is False
        assert "No market data available" in message

    @pytest.mark.asyncio
    async def test_validate_execution_request_invalid_quantity(self):
        """Test validation with invalid quantity"""
        request = ExecutionRequest(
            request_id="test_003",
            strategy_id="test_strategy",
            symbol="AAPL",
            side="BUY",
            quantity=-100,  # Invalid negative quantity
            order_type="MARKET"
        )

        is_valid, message = await self.engine._validate_execution_request(request)

        assert is_valid is False
        assert "Invalid quantity" in message

    @pytest.mark.asyncio
    async def test_validate_execution_request_duplicate_id(self):
        """Test validation with duplicate request ID"""
        request = ExecutionRequest(
            request_id="duplicate_test",
            strategy_id="test_strategy",
            symbol="AAPL",
            side="BUY",
            quantity=100,
            order_type="MARKET"
        )

        # Add to pending first
        self.engine.pending_executions[request.request_id] = request

        is_valid, message = await self.engine._validate_execution_request(request)

        assert is_valid is False
        assert "Duplicate request ID" in message

    @pytest.mark.asyncio
    async def test_calculate_execution_price_buy_order(self):
        """Test execution price calculation for buy orders"""
        request = ExecutionRequest(
            request_id="test_004",
            strategy_id="test_strategy",
            symbol="AAPL",
            side="BUY",
            quantity=100,
            order_type="MARKET"
        )

        price = await self.engine._calculate_execution_price(request)

        # Should be higher than current price due to slippage
        assert price > 150.0
        # Should not be excessively higher
        assert price < 151.0

    @pytest.mark.asyncio
    async def test_calculate_execution_price_sell_order(self):
        """Test execution price calculation for sell orders"""
        request = ExecutionRequest(
            request_id="test_005",
            strategy_id="test_strategy",
            symbol="AAPL",
            side="SELL",
            quantity=100,
            order_type="MARKET"
        )

        price = await self.engine._calculate_execution_price(request)

        # Should be lower than current price due to slippage
        assert price < 150.0
        # Should not be excessively lower
        assert price > 149.0

    @pytest.mark.asyncio
    async def test_execute_order_market_buy(self):
        """Test execution of market buy order"""
        import uuid
        request = ExecutionRequest(
            request_id=f"test_buy_{uuid.uuid4().hex[:8]}",
            strategy_id="test_strategy",
            symbol="AAPL",
            side="BUY",
            quantity=100,
            order_type="MARKET"
        )

        result = await self.engine.execute_order(request)

        # Check result structure
        assert isinstance(result, ExecutionResult)
        assert result.request_id == request.request_id
        assert result.status == ExecutionStatus.FILLED
        assert result.executed_quantity == 100
        assert result.executed_price > 150.0  # Slippage applied
        assert result.slippage_bps > 0
        assert result.commission >= 0
        assert result.execution_time is not None

        # Check engine state
        assert len(self.engine.execution_history) == 1
        assert request.request_id not in self.engine.pending_executions

    @pytest.mark.asyncio
    async def test_execute_order_market_sell(self):
        """Test execution of market sell order"""
        import uuid
        request = ExecutionRequest(
            request_id=f"test_sell_{uuid.uuid4().hex[:8]}",
            strategy_id="test_strategy",
            symbol="AAPL",
            side="SELL",
            quantity=100,
            order_type="MARKET"
        )

        result = await self.engine.execute_order(request)

        assert result.status == ExecutionStatus.FILLED
        assert result.executed_quantity == 100
        assert result.executed_price < 150.0  # Slippage applied
        assert result.slippage_bps > 0

    @pytest.mark.asyncio
    async def test_execute_pair_trade(self):
        """Test execution of coordinated pair trade"""
        result1, result2 = await self.engine.execute_pair_trade(
            symbol1="AAPL",
            symbol2="GOOGL",
            quantity1=100,
            quantity2=-50  # Sell GOOGL
        )

        # Check both results
        assert result1.status == ExecutionStatus.FILLED
        assert result2.status == ExecutionStatus.FILLED
        assert result1.executed_quantity == 100
        assert result2.executed_quantity == 50
        # Note: ExecutionResult doesn't include symbol, but we can verify execution occurred

        # Check execution history
        assert len(self.engine.execution_history) == 2

    @pytest.mark.asyncio
    async def test_execute_order_with_missing_market_data(self):
        """Test execution when market data is missing"""
        import uuid
        request = ExecutionRequest(
            request_id=f"test_missing_{uuid.uuid4().hex[:8]}",
            strategy_id="test_strategy",
            symbol="MISSING",
            side="BUY",
            quantity=100,
            order_type="MARKET"
        )

        result = await self.engine.execute_order(request)

        assert result.status == ExecutionStatus.REJECTED
        assert "No market data available" in result.notes

    @pytest.mark.asyncio
    async def test_execute_order_invalid_quantity(self):
        """Test execution with invalid quantity"""
        import uuid
        request = ExecutionRequest(
            request_id=f"test_invalid_{uuid.uuid4().hex[:8]}",
            strategy_id="test_strategy",
            symbol="AAPL",
            side="BUY",
            quantity=0,  # Invalid quantity
            order_type="MARKET"
        )

        result = await self.engine.execute_order(request)

        assert result.status == ExecutionStatus.REJECTED
        assert "Invalid quantity" in result.notes

    def test_performance_metrics_tracking(self):
        """Test that performance metrics are properly tracked"""
        # Initially should be zero
        assert self.engine.total_slippage_cost == 0.0
        assert self.engine.total_commission_cost == 0.0
        assert self.engine.execution_count == 0

        # After executions, metrics should be updated
        # (This would be tested after running actual executions)

    @pytest.mark.asyncio
    async def test_multiple_concurrent_orders(self):
        """Test execution of multiple concurrent orders"""
        import uuid
        base_id = uuid.uuid4().hex[:8]
        requests = [
            ExecutionRequest(
                request_id=f"concurrent_{base_id}_{i}",
                strategy_id="test_strategy",
                symbol="AAPL",
                side="BUY" if i % 2 == 0 else "SELL",
                quantity=100,
                order_type="MARKET"
            ) for i in range(5)
        ]

        # Execute all concurrently
        results = await asyncio.gather(*[
            self.engine.execute_order(request) for request in requests
        ])

        # All should be filled
        assert all(result.status == ExecutionStatus.FILLED for result in results)
        assert len(self.engine.execution_history) == 5

    @pytest.mark.asyncio
    async def test_execution_with_custom_market_conditions(self):
        """Test execution with custom market conditions"""
        # Set high volatility conditions
        conditions = MarketConditions(
            volatility=0.08,
            bid_ask_spread_bps=10.0,
            market_impact_factor=1.5,
            liquidity_factor=0.7
        )
        self.engine.update_market_conditions(conditions)

        request = ExecutionRequest(
            request_id="test_conditions_001",
            strategy_id="test_strategy",
            symbol="AAPL",
            side="BUY",
            quantity=100,
            order_type="MARKET"
        )

        result = await self.engine.execute_order(request)

        assert result.status == ExecutionStatus.FILLED
        # Slippage should be higher due to adverse conditions
        assert result.slippage_bps > 5.0


class TestExecutionModes:
    """Test execution behavior across different modes"""

    @pytest.mark.asyncio
    async def test_backtesting_mode_execution(self):
        """Test execution in backtesting mode"""
        import uuid
        engine = UnifiedExecutionEngine(
            mode=ExecutionMode.BACKTESTING,
            initial_capital=100000.0
        )
        engine.update_market_data("AAPL", 150.0)

        request = ExecutionRequest(
            request_id=f"backtest_{uuid.uuid4().hex[:8]}",
            strategy_id="test_strategy",
            symbol="AAPL",
            side="BUY",
            quantity=100,
            order_type="MARKET"
        )

        result = await engine.execute_order(request)

        assert result.status == ExecutionStatus.FILLED
        assert result.execution_venue == "BACKTESTING_SIM"
        assert result.execution_algorithm == "REALISTIC_SIM"

    @pytest.mark.asyncio
    async def test_paper_trading_mode_execution(self):
        """Test execution in paper trading mode"""
        import uuid
        engine = UnifiedExecutionEngine(
            mode=ExecutionMode.PAPER_TRADING,
            initial_capital=100000.0
        )
        engine.update_market_data("AAPL", 150.0)

        request = ExecutionRequest(
            request_id=f"paper_{uuid.uuid4().hex[:8]}",
            strategy_id="test_strategy",
            symbol="AAPL",
            side="BUY",
            quantity=100,
            order_type="MARKET"
        )

        result = await engine.execute_order(request)

        assert result.status == ExecutionStatus.FILLED
        assert result.execution_venue == "PAPER_TRADING"

    @pytest.mark.asyncio
    async def test_live_trading_mode_validation(self):
        """Test validation in live trading mode"""
        import uuid
        engine = UnifiedExecutionEngine(
            mode=ExecutionMode.LIVE_TRADING,
            initial_capital=100000.0
        )
        engine.update_market_data("AAPL", 150.0)

        # Large order that should be rejected in live mode
        request = ExecutionRequest(
            request_id=f"live_large_{uuid.uuid4().hex[:8]}",
            strategy_id="test_strategy",
            symbol="AAPL",
            side="BUY",
            quantity=10000,  # Very large order
            order_type="MARKET",
            price=150.0
        )

        result = await engine.execute_order(request)

        # Should be rejected due to size limits in live mode
        assert result.status == ExecutionStatus.REJECTED


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def setup_method(self):
        """Setup test fixtures"""
        self.engine = UnifiedExecutionEngine(
            mode=ExecutionMode.BACKTESTING,
            initial_capital=100000.0
        )

    @pytest.mark.asyncio
    async def test_execution_with_extreme_volatility(self):
        """Test execution under extreme market volatility"""
        conditions = MarketConditions(
            volatility=0.50,  # Extreme volatility
            bid_ask_spread_bps=50.0,
            market_impact_factor=3.0,
            liquidity_factor=0.1
        )
        self.engine.update_market_conditions(conditions)
        self.engine.update_market_data("AAPL", 150.0)

        request = ExecutionRequest(
            request_id="extreme_vol_001",
            strategy_id="test_strategy",
            symbol="AAPL",
            side="BUY",
            quantity=100,
            order_type="MARKET"
        )

        result = await self.engine.execute_order(request)

        assert result.status == ExecutionStatus.FILLED
        # Slippage should be very high
        assert result.slippage_bps > 20.0

    @pytest.mark.asyncio
    async def test_execution_with_zero_price(self):
        """Test execution when market price is zero"""
        import uuid
        self.engine.update_market_data("ZERO_STOCK", 0.0)

        request = ExecutionRequest(
            request_id=f"zero_price_{uuid.uuid4().hex[:8]}",
            strategy_id="test_strategy",
            symbol="ZERO_STOCK",
            side="BUY",
            quantity=100,
            order_type="MARKET"
        )

        result = await self.engine.execute_order(request)

        # Should still execute but with zero price
        assert result.status == ExecutionStatus.FILLED
        assert result.executed_price == 0.0

    @pytest.mark.asyncio
    async def test_execution_with_very_small_quantity(self):
        """Test execution with very small quantities"""
        import uuid
        self.engine.update_market_data("AAPL", 150.0)

        request = ExecutionRequest(
            request_id=f"small_qty_{uuid.uuid4().hex[:8]}",
            strategy_id="test_strategy",
            symbol="AAPL",
            side="BUY",
            quantity=0.01,  # Very small quantity
            order_type="MARKET"
        )

        result = await self.engine.execute_order(request)

        assert result.status == ExecutionStatus.FILLED
        assert result.executed_quantity == 0.01

    @pytest.mark.asyncio
    async def test_concurrent_execution_stress_test(self):
        """Stress test with many concurrent executions"""
        import uuid
        base_id = uuid.uuid4().hex[:8]
        self.engine.update_market_data("AAPL", 150.0)
        self.engine.update_market_data("GOOGL", 2800.0)
        self.engine.update_market_data("TSLA", 800.0)

        # Create many requests
        symbols = ["AAPL", "GOOGL", "TSLA"]
        requests = []
        for i in range(50):
            request = ExecutionRequest(
                request_id=f"stress_{base_id}_{i}",
                strategy_id="stress_test",
                symbol=symbols[i % 3],
                side="BUY" if i % 2 == 0 else "SELL",
                quantity=10,
                order_type="MARKET"
            )
            requests.append(request)

        # Execute all concurrently
        results = await asyncio.gather(*[
            self.engine.execute_order(request) for request in requests
        ])

        # All should complete successfully
        assert all(result.status == ExecutionStatus.FILLED for result in results)
        assert len(self.engine.execution_history) == 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
