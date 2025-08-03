"""
Test suite for ExecutionBridge: Production ↔ Backtesting Execution Integration

This module provides comprehensive tests for the ExecutionBridge class, including:
- Basic functionality testing
- Performance testing
- Integration testing
- Error handling testing
- Market impact modeling testing
- Transaction cost calculation testing
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import time
import logging

# Add the core_structure to the path
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core_structure'))

from execution.execution_bridge import (
    ExecutionBridge, 
    ExecutionBridgeConfig, 
    ExecutionOrder,
    ExecutionResult,
    ExecutionMode,
    OrderType,
    MarketImpactResult,
    TransactionCostResult,
    create_execution_bridge,
    execute_orders_for_backtesting
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestExecutionBridge:
    """Test cases for ExecutionBridge"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.config = ExecutionBridgeConfig(
            execution_mode=ExecutionMode.BACKTESTING,
            enable_market_impact=True,
            enable_transaction_costs=True,
            commission_rate=0.001,
            slippage_rate=0.0005,
            impact_sensitivity=0.1
        )
        self.bridge = ExecutionBridge(self.config)
        
        # Create sample market data
        dates = pd.date_range(start='2024-01-01', end='2024-01-10', freq='D')
        self.market_data = pd.DataFrame({
            'open': [100 + i for i in range(len(dates))],
            'high': [105 + i for i in range(len(dates))],
            'low': [95 + i for i in range(len(dates))],
            'close': [102 + i for i in range(len(dates))],
            'volume': [1000000 + i * 10000 for i in range(len(dates))]
        }, index=dates)
        
        # Create sample portfolio state
        self.portfolio_state = {
            'total_value': 100000,
            'cash': 50000,
            'positions': {'AAPL': 100, 'SPY': 200}
        }
    
    def test_execution_bridge_initialization(self):
        """Test ExecutionBridge initialization"""
        assert self.bridge.config.execution_mode == ExecutionMode.BACKTESTING
        assert self.bridge.config.enable_market_impact == True
        assert self.bridge.config.enable_transaction_costs == True
        assert self.bridge.config.commission_rate == 0.001
        assert self.bridge.config.slippage_rate == 0.0005
    
    def test_execution_order_creation(self):
        """Test ExecutionOrder creation"""
        order = ExecutionOrder(
            symbol="AAPL",
            side="buy",
            quantity=100,
            order_type=OrderType.MARKET,
            price=150.0
        )
        
        assert order.symbol == "AAPL"
        assert order.side == "buy"
        assert order.quantity == 100
        assert order.order_type == OrderType.MARKET
        assert order.price == 150.0
    
    def test_basic_order_execution(self):
        """Test basic order execution"""
        order = ExecutionOrder(
            symbol="AAPL",
            side="buy",
            quantity=100,
            order_type=OrderType.MARKET,
            price=150.0
        )
        
        result = self.bridge.execute_order(order, self.market_data, self.portfolio_state)
        
        assert result.symbol == "AAPL"
        assert result.side == "buy"
        assert result.quantity == 100
        assert result.filled_quantity == 100
        assert result.status == "filled"
        assert result.commission > 0
        assert result.slippage > 0
        assert result.market_impact > 0
    
    def test_market_impact_calculation(self):
        """Test market impact calculation"""
        order = ExecutionOrder(
            symbol="AAPL",
            side="buy",
            quantity=1000,  # Large order for impact
            order_type=OrderType.MARKET,
            price=150.0
        )
        
        market_impact = self.bridge._calculate_market_impact(order, self.market_data)
        
        assert market_impact.symbol == "AAPL"
        assert market_impact.quantity == 1000
        assert market_impact.side == "buy"
        assert market_impact.base_price == 150.0
        assert market_impact.impacted_price > market_impact.base_price  # Buy impact
        assert market_impact.impact_amount > 0
        assert market_impact.impact_percentage > 0
    
    def test_transaction_cost_calculation(self):
        """Test transaction cost calculation"""
        order = ExecutionOrder(
            symbol="AAPL",
            side="buy",
            quantity=100,
            order_type=OrderType.MARKET,
            price=150.0
        )
        
        market_impact = MarketImpactResult(
            symbol="AAPL",
            quantity=100,
            side="buy",
            base_price=150.0,
            impacted_price=150.15,
            impact_amount=0.15,
            impact_percentage=0.001,
            model_used="linear",
            confidence=0.8
        )
        
        transaction_costs = self.bridge._calculate_transaction_costs(order, market_impact)
        
        assert transaction_costs.symbol == "AAPL"
        assert transaction_costs.quantity == 100
        assert transaction_costs.price == 150.15
        assert transaction_costs.commission > 0
        assert transaction_costs.slippage > 0
        assert transaction_costs.total_cost > 0
        assert transaction_costs.cost_percentage > 0
    
    def test_batch_order_execution(self):
        """Test batch order execution"""
        orders = [
            ExecutionOrder("AAPL", "buy", 100, OrderType.MARKET, 150.0),
            ExecutionOrder("SPY", "sell", 50, OrderType.MARKET, 400.0),
            ExecutionOrder("MSFT", "buy", 75, OrderType.MARKET, 300.0)
        ]
        
        market_data = {
            'AAPL': self.market_data,
            'SPY': self.market_data,
            'MSFT': self.market_data
        }
        
        results = self.bridge.execute_orders_batch(orders, market_data, self.portfolio_state)
        
        assert len(results) == 3
        assert all(result.status == "filled" for result in results)
        assert results[0].symbol == "AAPL"
        assert results[1].symbol == "SPY"
        assert results[2].symbol == "MSFT"
    
    def test_order_validation(self):
        """Test order validation"""
        # Test invalid quantity
        invalid_order = ExecutionOrder("AAPL", "buy", -100, OrderType.MARKET, 150.0)
        
        with pytest.raises(ValueError, match="Invalid quantity"):
            self.bridge._validate_order(invalid_order)
        
        # Test order size below minimum
        small_order = ExecutionOrder("AAPL", "buy", 1, OrderType.MARKET, 50.0)
        
        with pytest.raises(ValueError, match="Order size below minimum"):
            self.bridge._validate_order(small_order)
        
        # Test order size exceeds position limit
        large_order = ExecutionOrder("AAPL", "buy", 10000, OrderType.MARKET, 150.0)
        
        with pytest.raises(ValueError, match="Order size exceeds position limit"):
            self.bridge._validate_order(large_order, self.portfolio_state)
    
    def test_different_execution_modes(self):
        """Test different execution modes"""
        order = ExecutionOrder("AAPL", "buy", 100, OrderType.MARKET, 150.0)
        
        # Test backtesting mode
        backtesting_config = ExecutionBridgeConfig(execution_mode=ExecutionMode.BACKTESTING)
        backtesting_bridge = ExecutionBridge(backtesting_config)
        backtesting_result = backtesting_bridge.execute_order(order, self.market_data)
        assert backtesting_result.metadata['mode'] == 'backtesting'
        
        # Test simulation mode
        simulation_config = ExecutionBridgeConfig(execution_mode=ExecutionMode.SIMULATION)
        simulation_bridge = ExecutionBridge(simulation_config)
        simulation_result = simulation_bridge.execute_order(order, self.market_data)
        assert simulation_result.metadata['mode'] == 'simulation'
    
    def test_performance_statistics(self):
        """Test performance statistics tracking"""
        orders = [
            ExecutionOrder("AAPL", "buy", 100, OrderType.MARKET, 150.0),
            ExecutionOrder("SPY", "sell", 50, OrderType.MARKET, 400.0)
        ]
        
        for order in orders:
            self.bridge.execute_order(order, self.market_data)
        
        stats = self.bridge.get_performance_stats()
        
        assert stats['total_orders'] == 2
        assert stats['successful_orders'] == 2
        assert stats['failed_orders'] == 0
        assert stats['total_commission'] > 0
        assert stats['total_slippage'] > 0
        assert stats['total_market_impact'] > 0
        assert stats['avg_execution_time'] > 0
    
    def test_error_handling(self):
        """Test error handling"""
        # Test with invalid order
        invalid_order = ExecutionOrder("AAPL", "buy", -100, OrderType.MARKET, 150.0)
        
        result = self.bridge.execute_order(invalid_order, self.market_data)
        
        assert result.status == "rejected"
        assert result.error_message is not None
        assert result.filled_quantity == 0
    
    def test_convenience_function(self):
        """Test convenience function for backtesting"""
        orders = [
            ExecutionOrder("AAPL", "buy", 100, OrderType.MARKET, 150.0),
            ExecutionOrder("SPY", "sell", 50, OrderType.MARKET, 400.0)
        ]
        
        market_data = {
            'AAPL': self.market_data,
            'SPY': self.market_data
        }
        
        results = execute_orders_for_backtesting(orders, market_data, self.portfolio_state)
        
        assert len(results) == 2
        assert all(result.status == "filled" for result in results)
    
    def test_market_impact_disabled(self):
        """Test execution with market impact disabled"""
        config = ExecutionBridgeConfig(
            execution_mode=ExecutionMode.BACKTESTING,
            enable_market_impact=False
        )
        bridge = ExecutionBridge(config)
        
        order = ExecutionOrder("AAPL", "buy", 1000, OrderType.MARKET, 150.0)
        market_impact = bridge._calculate_market_impact(order, self.market_data)
        
        assert market_impact.impact_amount == 0.0
        assert market_impact.impact_percentage == 0.0
        assert market_impact.model_used == "none"
    
    def test_transaction_costs_disabled(self):
        """Test execution with transaction costs disabled"""
        config = ExecutionBridgeConfig(
            execution_mode=ExecutionMode.BACKTESTING,
            enable_transaction_costs=False
        )
        bridge = ExecutionBridge(config)
        
        order = ExecutionOrder("AAPL", "buy", 100, OrderType.MARKET, 150.0)
        market_impact = MarketImpactResult(
            symbol="AAPL",
            quantity=100,
            side="buy",
            base_price=150.0,
            impacted_price=150.0,
            impact_amount=0.0,
            impact_percentage=0.0,
            model_used="none",
            confidence=1.0
        )
        
        transaction_costs = bridge._calculate_transaction_costs(order, market_impact)
        
        assert transaction_costs.commission == 0.0
        assert transaction_costs.slippage == 0.0
        assert transaction_costs.total_cost == 0.0
        assert transaction_costs.model_used == "none"
    
    def test_order_types(self):
        """Test different order types"""
        order_types = [
            OrderType.MARKET,
            OrderType.LIMIT,
            OrderType.STOP,
            OrderType.TWAP,
            OrderType.VWAP
        ]
        
        for order_type in order_types:
            order = ExecutionOrder("AAPL", "buy", 100, order_type, 150.0)
            result = self.bridge.execute_order(order, self.market_data)
            
            assert result.status == "filled"
            assert result.symbol == "AAPL"
    
    def test_bridge_shutdown(self):
        """Test bridge shutdown"""
        self.bridge.shutdown()
        # Should not raise any exceptions
    
    def test_reset_performance_stats(self):
        """Test performance statistics reset"""
        order = ExecutionOrder("AAPL", "buy", 100, OrderType.MARKET, 150.0)
        self.bridge.execute_order(order, self.market_data)
        
        # Verify stats are populated
        stats = self.bridge.get_performance_stats()
        assert stats['total_orders'] > 0
        
        # Reset stats
        self.bridge.reset_performance_stats()
        
        # Verify stats are reset
        stats = self.bridge.get_performance_stats()
        assert stats['total_orders'] == 0
        assert stats['successful_orders'] == 0
        assert stats['total_commission'] == 0.0

class TestExecutionBridgePerformance:
    """Performance tests for ExecutionBridge"""
    
    def setup_method(self):
        """Set up performance test fixtures"""
        self.config = ExecutionBridgeConfig(
            execution_mode=ExecutionMode.BACKTESTING,
            max_concurrent_orders=10
        )
        self.bridge = ExecutionBridge(self.config)
        
        # Create large dataset
        dates = pd.date_range(start='2024-01-01', end='2024-01-31', freq='D')
        self.market_data = pd.DataFrame({
            'open': [100 + i for i in range(len(dates))],
            'high': [105 + i for i in range(len(dates))],
            'low': [95 + i for i in range(len(dates))],
            'close': [102 + i for i in range(len(dates))],
            'volume': [1000000 + i * 10000 for i in range(len(dates))]
        }, index=dates)
    
    def test_single_order_performance(self):
        """Test single order execution performance"""
        order = ExecutionOrder("AAPL", "buy", 100, OrderType.MARKET, 150.0)
        
        start_time = time.time()
        result = self.bridge.execute_order(order, self.market_data)
        execution_time = time.time() - start_time
        
        assert execution_time < 1.0  # Should complete within 1 second
        assert result.status == "filled"
    
    def test_batch_order_performance(self):
        """Test batch order execution performance"""
        orders = [
            ExecutionOrder(f"SYMBOL_{i}", "buy", 100, OrderType.MARKET, 150.0)
            for i in range(50)
        ]
        
        market_data = {
            f"SYMBOL_{i}": self.market_data for i in range(50)
        }
        
        start_time = time.time()
        results = self.bridge.execute_orders_batch(orders, market_data)
        execution_time = time.time() - start_time
        
        assert execution_time < 5.0  # Should complete within 5 seconds
        assert len(results) == 50
        assert all(result.status == "filled" for result in results)
    
    def test_concurrent_execution_efficiency(self):
        """Test concurrent execution efficiency"""
        # Sequential execution
        orders = [
            ExecutionOrder(f"SYMBOL_{i}", "buy", 100, OrderType.MARKET, 150.0)
            for i in range(10)
        ]
        
        market_data = {
            f"SYMBOL_{i}": self.market_data for i in range(10)
        }
        
        # Sequential timing
        start_time = time.time()
        sequential_results = []
        for order in orders:
            result = self.bridge.execute_order(order, market_data[order.symbol])
            sequential_results.append(result)
        sequential_time = time.time() - start_time
        
        # Batch timing
        start_time = time.time()
        batch_results = self.bridge.execute_orders_batch(orders, market_data)
        batch_time = time.time() - start_time
        
        # Batch should be more efficient
        assert batch_time < sequential_time
        assert len(batch_results) == len(sequential_results)

class TestExecutionBridgeIntegration:
    """Integration tests for ExecutionBridge"""
    
    def setup_method(self):
        """Set up integration test fixtures"""
        self.config = ExecutionBridgeConfig(
            execution_mode=ExecutionMode.BACKTESTING,
            enable_market_impact=True,
            enable_transaction_costs=True
        )
        self.bridge = ExecutionBridge(self.config)
    
    def test_signal_to_execution_integration(self):
        """Test integration from signals to execution"""
        # Simulate signals from SignalBridge
        signals = {
            'AAPL': 0.8,  # Strong buy signal
            'SPY': -0.3,  # Weak sell signal
            'MSFT': 0.5   # Moderate buy signal
        }
        
        # Convert signals to orders
        orders = []
        for symbol, signal in signals.items():
            if abs(signal) > 0.1:  # Only trade if signal is significant
                side = "buy" if signal > 0 else "sell"
                quantity = int(abs(signal) * 100)  # Scale quantity by signal strength
                
                order = ExecutionOrder(
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    order_type=OrderType.MARKET
                )
                orders.append(order)
        
        # Execute orders
        market_data = {
            'AAPL': pd.DataFrame({'close': [150.0] * 10}),
            'SPY': pd.DataFrame({'close': [400.0] * 10}),
            'MSFT': pd.DataFrame({'close': [300.0] * 10})
        }
        
        results = self.bridge.execute_orders_batch(orders, market_data)
        
        assert len(results) == 3
        assert all(result.status == "filled" for result in results)
        
        # Verify order directions match signals
        aapl_result = next(r for r in results if r.symbol == 'AAPL')
        spy_result = next(r for r in results if r.symbol == 'SPY')
        msft_result = next(r for r in results if r.symbol == 'MSFT')
        
        assert aapl_result.side == "buy"
        assert spy_result.side == "sell"
        assert msft_result.side == "buy"
    
    def test_portfolio_state_integration(self):
        """Test integration with portfolio state"""
        portfolio_state = {
            'total_value': 100000,
            'cash': 50000,
            'positions': {'AAPL': 100, 'SPY': 200},
            'risk_limits': {'max_position_size': 0.1}
        }
        
        # Test order within limits
        valid_order = ExecutionOrder("MSFT", "buy", 50, OrderType.MARKET, 300.0)
        result = self.bridge.execute_order(valid_order, None, portfolio_state)
        assert result.status == "filled"
        
        # Test order exceeding limits
        invalid_order = ExecutionOrder("MSFT", "buy", 10000, OrderType.MARKET, 300.0)
        result = self.bridge.execute_order(invalid_order, None, portfolio_state)
        assert result.status == "rejected"
    
    def test_market_data_integration(self):
        """Test integration with market data"""
        # Create realistic market data
        dates = pd.date_range(start='2024-01-01', end='2024-01-10', freq='D')
        market_data = pd.DataFrame({
            'open': [100 + i for i in range(len(dates))],
            'high': [105 + i for i in range(len(dates))],
            'low': [95 + i for i in range(len(dates))],
            'close': [102 + i for i in range(len(dates))],
            'volume': [1000000 + i * 10000 for i in range(len(dates))]
        }, index=dates)
        
        order = ExecutionOrder("AAPL", "buy", 100, OrderType.MARKET, 150.0)
        result = self.bridge.execute_order(order, market_data)
        
        assert result.status == "filled"
        assert result.execution_price > 0
        assert result.market_impact >= 0
        assert result.commission > 0

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"]) 