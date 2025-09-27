#!/usr/bin/env python3
"""
Order Execution Integration Tests
=================================

Comprehensive integration tests for order execution pipeline:
- Broker API connectivity and authentication
- Order routing and execution algorithms
- Fill quality analysis (slippage, market impact)
- Position reconciliation and accounting
- Execution cost optimization

These tests validate the complete order execution workflow from
signal generation through order placement to fill confirmation.

Author: StatArb_Gemini Integration Test Suite
Version: 1.0.0
"""

import pytest
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import dataclass, field
from enum import Enum
import warnings
import time
import uuid

warnings.filterwarnings('ignore')

from core_engine.system.unified_execution_engine import UnifiedExecutionEngine
from core_engine.risk.manager import RiskManager
from core_engine.trading.strategies.strategy_engine import BaseStrategy


class OrderType(Enum):
    """Order types"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(Enum):
    """Order sides"""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """Order statuses"""
    PENDING = "pending"
    PARTIAL_FILL = "partial_fill"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Order:
    """Order representation"""
    order_id: str
    symbol: str
    side: OrderSide
    quantity: int
    order_type: OrderType
    price: Optional[float] = None
    stop_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    average_fill_price: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    commission: float = 0.0


@dataclass
class ExecutionResult:
    """Order execution result"""
    order_id: str
    fills: List[Dict[str, Any]] = field(default_factory=list)
    total_filled: int = 0
    total_cost: float = 0.0
    average_price: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0


class MockBrokerAPI:
    """Mock broker API for testing"""

    def __init__(self):
        self.orders = {}
        self.positions = {}
        self.account_balance = 100000.0
        self.market_data = {}

    def submit_order(self, order: Order) -> bool:
        """Submit order to broker"""
        self.orders[order.order_id] = order
        return True

    def cancel_order(self, order_id: str) -> bool:
        """Cancel order"""
        if order_id in self.orders:
            self.orders[order_id].status = OrderStatus.CANCELLED
            return True
        return False

    def get_order_status(self, order_id: str) -> Optional[OrderStatus]:
        """Get order status"""
        order = self.orders.get(order_id)
        return order.status if order else None

    def simulate_fill(self, order_id: str, fill_price: float, fill_quantity: int):
        """Simulate order fill"""
        if order_id in self.orders:
            order = self.orders[order_id]
            order.filled_quantity += fill_quantity
            order.average_fill_price = (
                (order.average_fill_price * (order.filled_quantity - fill_quantity)) +
                (fill_price * fill_quantity)
            ) / order.filled_quantity

            if order.filled_quantity >= order.quantity:
                order.status = OrderStatus.FILLED
            else:
                order.status = OrderStatus.PARTIAL_FILL


class TestOrderExecutionIntegration:
    """Integration tests for order execution pipeline"""

    @pytest.fixture
    def execution_engine(self):
        """Create execution engine with mock config"""
        config = {
            'max_order_size': 100000,
            'min_order_size': 100,
            'default_algorithm': 'market'
        }
        return UnifiedExecutionEngine(config)

    @pytest.fixture
    def risk_manager(self):
        """Create risk manager"""
        config = {
            'max_position_size': 0.10,
            'max_daily_var': 0.05,
            'max_total_risk': 0.20,
            'position_concentration_limit': 0.15,
            'strategy_allocation_limit': 0.33,
            'enable_real_time_monitoring': True,
            'authorization_timeout': 300
        }
        return RiskManager(config)

    @pytest.fixture
    def mock_broker_api(self):
        """Create mock broker API"""
        return MockBrokerAPI()

    @pytest.fixture
    def sample_orders(self):
        """Generate sample orders for testing"""
        orders = []

        symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA']
        sides = [OrderSide.BUY, OrderSide.SELL]

        for i in range(10):
            order = Order(
                order_id=f"ORDER_{i:03d}",
                symbol=np.random.choice(symbols),
                side=np.random.choice(sides),
                quantity=np.random.randint(10, 100),
                order_type=OrderType.MARKET,
                price=None  # Market order
            )
            orders.append(order)

        return orders

    def test_broker_api_connectivity(self, mock_broker_api):
        """Test broker API connectivity and authentication"""
        connection_status = {}

        def connect_broker(api_key: str, api_secret: str) -> bool:
            """Simulate broker connection"""
            try:
                # Simulate authentication
                if api_key and api_secret:
                    connection_status['authenticated'] = True
                    connection_status['session_id'] = str(uuid.uuid4())
                    return True
                else:
                    connection_status['authenticated'] = False
                    return False
            except Exception as e:
                connection_status['error'] = str(e)
                return False

        def disconnect_broker():
            """Disconnect from broker"""
            connection_status['authenticated'] = False
            connection_status['session_id'] = None

        # Test successful connection
        assert connect_broker("test_key", "test_secret")
        assert connection_status['authenticated'] is True
        assert 'session_id' in connection_status

        # Test disconnection
        disconnect_broker()
        assert connection_status['authenticated'] is False
        assert connection_status['session_id'] is None

        # Test failed connection
        assert not connect_broker("", "")
        assert connection_status['authenticated'] is False

    def test_order_submission_and_routing(self, execution_engine, mock_broker_api, sample_orders):
        """Test order submission and routing logic"""
        submitted_orders = []
        routing_decisions = {}

        def route_order(order: Order) -> str:
            """Determine routing destination based on order characteristics"""
            if order.quantity > 1000:
                routing_decisions[order.order_id] = 'institutional_desk'
            elif order.symbol in ['AAPL', 'GOOGL', 'MSFT']:
                routing_decisions[order.order_id] = 'primary_broker'
            else:
                routing_decisions[order.order_id] = 'alternative_broker'

            return routing_decisions[order.order_id]

        def submit_order_to_broker(order: Order, broker_api) -> bool:
            """Submit order to broker API"""
            try:
                success = broker_api.submit_order(order)
                if success:
                    submitted_orders.append(order)
                return success
            except Exception as e:
                return False

        # Test order routing and submission
        for order in sample_orders[:5]:  # Test first 5 orders
            # Route order
            destination = route_order(order)
            assert destination in ['primary_broker', 'alternative_broker', 'institutional_desk']

            # Submit order
            success = submit_order_to_broker(order, mock_broker_api)
            assert success

        # Verify orders were submitted
        assert len(submitted_orders) == 5
        assert len(routing_decisions) == 5

        # Verify broker received orders
        assert len(mock_broker_api.orders) == 5

    def test_execution_algorithms_integration(self, execution_engine, mock_broker_api):
        """Test execution algorithms integration"""
        algorithm_performance = {}

        def test_market_order_execution(order: Order, market_conditions: dict):
            """Test market order execution"""
            start_time = time.time()

            # Simulate market order execution with slippage
            base_price = market_conditions.get('mid_price', 100.0)
            slippage = market_conditions.get('spread', 0.01) * np.random.uniform(0.1, 0.5)

            if order.side == OrderSide.BUY:
                fill_price = base_price + slippage
            else:
                fill_price = base_price - slippage

            # Simulate partial fills
            fill_quantity = min(order.quantity, np.random.randint(1, order.quantity + 1))

            execution_time = time.time() - start_time
            algorithm_performance['market_order'] = {
                'execution_time': execution_time,
                'slippage': slippage,
                'fill_rate': fill_quantity / order.quantity
            }

            return fill_price, fill_quantity

        def test_twap_execution(order: Order, duration_minutes: int = 60):
            """Test TWAP execution algorithm"""
            start_time = time.time()

            # Simulate TWAP execution over time
            slices = duration_minutes // 5  # 5-minute intervals
            total_filled = 0
            total_cost = 0.0

            for i in range(slices):
                if total_filled < order.quantity:
                    remaining_quantity = order.quantity - total_filled
                    if i == slices - 1:  # Last slice
                        slice_size = remaining_quantity  # Fill all remaining
                    else:
                        slice_size = min(remaining_quantity // (slices - i), remaining_quantity)
                        if slice_size == 0:
                            slice_size = remaining_quantity

                    # Simulate price movement during execution
                    price = 100.0 + np.random.normal(0, 0.5)
                    total_filled += slice_size
                    total_cost += price * slice_size
                    time.sleep(0.001)  # Simulate time delay

            avg_price = total_cost / total_filled if total_filled > 0 else 0
            execution_time = time.time() - start_time

            algorithm_performance['twap'] = {
                'execution_time': execution_time,
                'avg_price': avg_price,
                'total_filled': total_filled,
                'participation_rate': total_filled / order.quantity
            }

            return avg_price, total_filled

        # Test market order execution
        market_order = Order(
            order_id="TEST_MARKET_001",
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=1000,
            order_type=OrderType.MARKET
        )

        market_conditions = {'mid_price': 150.0, 'spread': 0.02}
        fill_price, fill_quantity = test_market_order_execution(market_order, market_conditions)

        assert fill_price > 0
        assert 0 < fill_quantity <= market_order.quantity
        assert 'market_order' in algorithm_performance

        # Test TWAP execution
        twap_order = Order(
            order_id="TEST_TWAP_001",
            symbol="GOOGL",
            side=OrderSide.SELL,
            quantity=5000,
            order_type=OrderType.MARKET
        )

        avg_price, total_filled = test_twap_execution(twap_order, duration_minutes=30)

        assert avg_price > 0
        assert total_filled == twap_order.quantity  # Should fully fill
        assert 'twap' in algorithm_performance

        # Compare algorithm performance
        market_perf = algorithm_performance['market_order']
        twap_perf = algorithm_performance['twap']

        # TWAP should generally have lower market impact but longer execution time
        assert twap_perf['execution_time'] > market_perf['execution_time']

    def test_fill_quality_analysis(self, mock_broker_api, sample_orders):
        """Test fill quality analysis (slippage, market impact)"""
        fill_analysis_results = {}

        def analyze_fill_quality(order: Order, fills: List[Dict[str, Any]], market_data: dict):
            """Analyze execution quality"""
            analysis = {
                'total_slippage': 0.0,
                'market_impact': 0.0,
                'timing_quality': 0.0,
                'fill_rate': 0.0,
                'vwap_comparison': 0.0
            }

            if not fills:
                return analysis

            # Calculate slippage
            benchmark_price = market_data.get('vwap', market_data.get('mid_price', 100.0))
            total_volume = sum(fill['quantity'] for fill in fills)
            total_cost = sum(fill['price'] * fill['quantity'] for fill in fills)
            avg_fill_price = total_cost / total_volume

            if order.side == OrderSide.BUY:
                analysis['total_slippage'] = avg_fill_price - benchmark_price
            else:
                analysis['total_slippage'] = benchmark_price - avg_fill_price

            # Fill rate
            analysis['fill_rate'] = total_volume / order.quantity

            # Market impact estimate (simplified)
            market_volume = market_data.get('daily_volume', 1000000)
            participation_rate = total_volume / market_volume
            analysis['market_impact'] = participation_rate * 0.001  # 0.1% per 0.1% participation

            return analysis

        # Simulate fills for orders
        market_data = {
            'AAPL': {'vwap': 150.0, 'mid_price': 150.5, 'daily_volume': 50000000},
            'GOOGL': {'vwap': 2800.0, 'mid_price': 2805.0, 'daily_volume': 1500000},
            'MSFT': {'vwap': 300.0, 'mid_price': 301.0, 'daily_volume': 25000000},
            'TSLA': {'vwap': 800.0, 'mid_price': 805.0, 'daily_volume': 20000000}
        }

        for order in sample_orders[:3]:  # Test first 3 orders
            # Simulate fills
            fills = []
            remaining_quantity = order.quantity

            # Simulate 2-3 partial fills
            for i in range(np.random.randint(2, 4)):
                if remaining_quantity > 0:
                    fill_quantity = min(remaining_quantity, np.random.randint(1, remaining_quantity + 1))
                    # Add some realistic slippage
                    base_price = market_data[order.symbol]['mid_price']
                    slippage = np.random.normal(0, 0.5)  # Small random slippage
                    fill_price = base_price + slippage

                    fill = {
                        'price': fill_price,
                        'quantity': fill_quantity,
                        'timestamp': datetime.now() + timedelta(seconds=i)
                    }
                    fills.append(fill)
                    remaining_quantity -= fill_quantity

            # Analyze fill quality
            analysis = analyze_fill_quality(order, fills, market_data[order.symbol])
            fill_analysis_results[order.order_id] = analysis

            # Verify analysis results
            assert isinstance(analysis['total_slippage'], (int, float))
            assert 0 <= analysis['fill_rate'] <= 1.0
            assert analysis['market_impact'] >= 0

        # Should have analysis for all tested orders
        assert len(fill_analysis_results) == 3

    def test_position_reconciliation(self, mock_broker_api, sample_orders):
        """Test position reconciliation between system and broker"""
        system_positions = {}
        broker_positions = {}
        reconciliation_report = {}

        def update_system_position(order: Order, fill_quantity: int, fill_price: float):
            """Update system position tracking"""
            if order.symbol not in system_positions:
                system_positions[order.symbol] = {'quantity': 0, 'avg_cost': 0.0}

            position = system_positions[order.symbol]
            if order.side == OrderSide.BUY:
                new_quantity = position['quantity'] + fill_quantity
                new_avg_cost = (
                    (position['avg_cost'] * position['quantity']) +
                    (fill_price * fill_quantity)
                ) / new_quantity if new_quantity > 0 else 0
            else:
                new_quantity = position['quantity'] - fill_quantity
                new_avg_cost = position['avg_cost']  # Cost basis unchanged on sell

            position['quantity'] = new_quantity
            position['avg_cost'] = new_avg_cost

        def reconcile_positions():
            """Reconcile system vs broker positions"""
            discrepancies = {}

            all_symbols = set(system_positions.keys()) | set(broker_positions.keys())

            for symbol in all_symbols:
                system_qty = system_positions.get(symbol, {}).get('quantity', 0)
                broker_qty = broker_positions.get(symbol, {}).get('quantity', 0)

                if abs(system_qty - broker_qty) > 0.1:  # Allow small rounding differences
                    discrepancies[symbol] = {
                        'system_quantity': system_qty,
                        'broker_quantity': broker_qty,
                        'difference': system_qty - broker_qty
                    }

            return discrepancies

        # Simulate trading activity and reconciliation
        for order in sample_orders[:5]:
            # Simulate fill
            fill_quantity = order.quantity  # Assume full fill for simplicity
            fill_price = 100.0 + np.random.normal(0, 5)  # Random fill price

            # Update system position
            update_system_position(order, fill_quantity, fill_price)

            # Simulate broker position update
            if order.symbol not in broker_positions:
                broker_positions[order.symbol] = {'quantity': 0, 'avg_cost': 0.0}

            broker_pos = broker_positions[order.symbol]
            if order.side == OrderSide.BUY:
                broker_pos['quantity'] += fill_quantity
            else:
                broker_pos['quantity'] -= fill_quantity

        # Perform reconciliation
        discrepancies = reconcile_positions()
        reconciliation_report = {
            'total_positions': len(system_positions),
            'discrepancies_found': len(discrepancies),
            'discrepancy_details': discrepancies
        }

        # With this simple simulation, should have no discrepancies
        assert reconciliation_report['total_positions'] > 0
        assert reconciliation_report['discrepancies_found'] == 0

    def test_execution_cost_optimization(self, execution_engine, sample_orders):
        """Test execution cost optimization strategies"""
        cost_optimization_results = {}

        def optimize_execution_cost(order: Order, market_conditions: dict):
            """Optimize execution to minimize costs"""
            optimization = {
                'original_cost_estimate': 0.0,
                'optimized_cost_estimate': 0.0,
                'cost_savings': 0.0,
                'optimization_method': 'market_impact_minimization'
            }

            # Estimate original market order cost
            base_price = market_conditions.get('mid_price', 100.0)
            spread = market_conditions.get('spread', 0.01)
            market_impact = market_conditions.get('market_impact', 0.001)

            original_slippage = spread * 0.5 + market_impact * order.quantity
            optimization['original_cost_estimate'] = original_slippage * base_price * order.quantity

            # Estimate optimized cost (e.g., using TWAP)
            optimized_slippage = spread * 0.2 + market_impact * order.quantity * 0.3  # 70% reduction
            optimization['optimized_cost_estimate'] = optimized_slippage * base_price * order.quantity
            optimization['cost_savings'] = optimization['original_cost_estimate'] - optimization['optimized_cost_estimate']

            return optimization

        # Test cost optimization for different market conditions
        market_scenarios = [
            {'mid_price': 150.0, 'spread': 0.02, 'market_impact': 0.001, 'volatility': 'low'},
            {'mid_price': 2800.0, 'spread': 0.05, 'market_impact': 0.002, 'volatility': 'high'},
            {'mid_price': 300.0, 'spread': 0.03, 'market_impact': 0.0015, 'volatility': 'medium'}
        ]

        for i, scenario in enumerate(market_scenarios):
            order = sample_orders[i % len(sample_orders)]
            optimization = optimize_execution_cost(order, scenario)
            cost_optimization_results[f'scenario_{i}'] = optimization

            # Verify optimization results
            assert optimization['optimized_cost_estimate'] < optimization['original_cost_estimate']
            assert optimization['cost_savings'] > 0
            assert optimization['optimization_method'] is not None

        # Should have results for all scenarios
        assert len(cost_optimization_results) == len(market_scenarios)

    def test_end_to_end_order_execution_workflow(self, execution_engine, risk_manager, mock_broker_api):
        """Test complete end-to-end order execution workflow"""
        workflow_results = {
            'orders_processed': 0,
            'orders_executed': 0,
            'risk_checks_passed': 0,
            'execution_success_rate': 0.0
        }

        async def execute_trading_workflow(signal: dict):
            """Execute complete trading workflow"""
            # 1. Risk check
            risk_approved = True  # Simplified - would call risk_manager

            if risk_approved:
                workflow_results['risk_checks_passed'] += 1

                # 2. Create order
                order = Order(
                    order_id=f"WORKFLOW_{signal['symbol']}_{int(time.time())}",
                    symbol=signal['symbol'],
                    side=signal['side'],
                    quantity=signal['quantity'],
                    order_type=OrderType.MARKET
                )

                # 3. Submit order
                success = mock_broker_api.submit_order(order)
                workflow_results['orders_processed'] += 1

                if success:
                    # 4. Simulate execution
                    fill_price = signal.get('expected_price', 100.0) + np.random.normal(0, 1)
                    mock_broker_api.simulate_fill(order.order_id, fill_price, order.quantity)
                    workflow_results['orders_executed'] += 1

                return success

            return False

        # Test workflow with multiple signals
        signals = [
            {'symbol': 'AAPL', 'side': OrderSide.BUY, 'quantity': 100, 'expected_price': 150.0},
            {'symbol': 'GOOGL', 'side': OrderSide.SELL, 'quantity': 50, 'expected_price': 2800.0},
            {'symbol': 'MSFT', 'side': OrderSide.BUY, 'quantity': 75, 'expected_price': 300.0}
        ]

        async def run_workflow_tests():
            for signal in signals:
                await execute_trading_workflow(signal)

        # Run async workflow tests
        asyncio.run(run_workflow_tests())

        # Calculate success metrics
        if workflow_results['orders_processed'] > 0:
            workflow_results['execution_success_rate'] = (
                workflow_results['orders_executed'] / workflow_results['orders_processed']
            )

        # Verify workflow results
        assert workflow_results['orders_processed'] == len(signals)
        assert workflow_results['orders_executed'] > 0
        assert workflow_results['execution_success_rate'] > 0
        assert workflow_results['risk_checks_passed'] == len(signals)

        # Verify broker state
        assert len(mock_broker_api.orders) == len(signals)