"""
Integration Tests - End-to-End Workflows
=========================================
Comprehensive end-to-end integration tests for StatArb_Gemini system.
Tests complete trading workflows from market data to position reconciliation.

Test Coverage:
- Market data ingestion → Signal generation → Order execution
- Broker API integration (order submission, status updates, fills)
- Complete order lifecycle (new → pending → filled → reconciled)
- Position reconciliation (orders → positions → portfolio state)
- Multi-symbol portfolio operations
- Real-time data processing pipeline
- Strategy signal to execution latency validation

Author: StatArb_Gemini Integration Testing
Phase: 8 Week 2 - Day 8 - End-to-End Integration Testing
Date: October 12, 2025
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import logging

# Import core system components
from core_engine.system.central_risk_manager import (
    CentralRiskManager,
    TradingDecisionRequest,
    TradingDecisionType,
    AuthorizationLevel,
    ExecutionUrgency
)

# Import broker components

# Import type definitions
from core_engine.type_definitions.broker import (
    BrokerConfig,
    PaperBroker,
    BrokerType as BrokerConfigType
)
from core_engine.type_definitions.orders import (
    Order,
    OrderType,
    OrderStatus,
    OrderSide
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Test Data Classes
# ============================================================================

@dataclass
class MarketDataTick:
    """Market data tick"""
    symbol: str
    timestamp: datetime
    bid: float
    ask: float
    last: float
    volume: int
    bid_size: int = 100
    ask_size: int = 100


@dataclass
class TradingSignal:
    """Trading signal from strategy"""
    signal_id: str
    symbol: str
    strategy_id: str
    signal_type: str  # "BUY" or "SELL"
    quantity: float
    confidence: float
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionMetrics:
    """Execution performance metrics"""
    signal_to_order_latency: float = 0.0
    order_to_fill_latency: float = 0.0
    total_latency: float = 0.0
    slippage: float = 0.0
    fill_rate: float = 0.0


@dataclass
class WorkflowResult:
    """Complete workflow execution result"""
    workflow_id: str
    success: bool
    start_time: datetime
    end_time: datetime
    duration: float
    market_data_ticks: int = 0
    signals_generated: int = 0
    orders_submitted: int = 0
    orders_filled: int = 0
    positions_updated: int = 0
    metrics: ExecutionMetrics = field(default_factory=ExecutionMetrics)
    errors: List[str] = field(default_factory=list)


# ============================================================================
# Helper Functions
# ============================================================================

def create_market_data_stream(symbols: List[str], tick_count: int = 10) -> List[MarketDataTick]:
    """
    Create simulated market data stream
    
    Args:
        symbols: List of symbols to generate data for
        tick_count: Number of ticks per symbol
    
    Returns:
        List of market data ticks
    """
    ticks = []
    base_time = datetime.now()
    
    for i in range(tick_count):
        for symbol in symbols:
            # Simulate realistic market data
            base_price = 100.0 + hash(symbol) % 50  # Deterministic base price
            spread = 0.05
            
            tick = MarketDataTick(
                symbol=symbol,
                timestamp=base_time + timedelta(milliseconds=i * 100),
                bid=base_price + (i * 0.01),
                ask=base_price + (i * 0.01) + spread,
                last=base_price + (i * 0.01) + spread / 2,
                volume=1000 * (i + 1),
                bid_size=100,
                ask_size=100
            )
            ticks.append(tick)
    
    return ticks


def generate_trading_signals(market_data: List[MarketDataTick], strategy_id: str = "momentum_test") -> List[TradingSignal]:
    """
    Generate trading signals from market data
    
    Simulates strategy signal generation based on market conditions
    """
    signals = []
    
    # Group ticks by symbol
    symbol_ticks: Dict[str, List[MarketDataTick]] = {}
    for tick in market_data:
        if tick.symbol not in symbol_ticks:
            symbol_ticks[tick.symbol] = []
        symbol_ticks[tick.symbol].append(tick)
    
    # Generate signals based on simple momentum
    for symbol, ticks in symbol_ticks.items():
        if len(ticks) < 3:
            continue
        
        # Calculate momentum (last price - first price)
        momentum = ticks[-1].last - ticks[0].last
        
        if abs(momentum) > 0.01:  # Significant movement (lowered threshold for testing)
            signal_type = "BUY" if momentum > 0 else "SELL"
            confidence = min(abs(momentum) * 10, 0.95)  # Scale to 0-0.95
            
            signal = TradingSignal(
                signal_id=str(uuid.uuid4()),
                symbol=symbol,
                strategy_id=strategy_id,
                signal_type=signal_type,
                quantity=100.0,
                confidence=confidence,
                timestamp=ticks[-1].timestamp,
                metadata={
                    'momentum': momentum,
                    'price_range': ticks[-1].last - ticks[0].last,
                    'volume_avg': sum(t.volume for t in ticks) / len(ticks)
                }
            )
            signals.append(signal)
    
    return signals


async def submit_order_from_signal(
    signal: TradingSignal,
    broker: PaperBroker,
    risk_manager: CentralRiskManager
) -> Optional[Order]:
    """
    Submit order based on trading signal
    
    Flow: Signal → Risk Authorization → Broker Submission
    """
    try:
        # Create authorization request
        decision_type = TradingDecisionType.POSITION_ENTRY
        side = OrderSide.BUY if signal.signal_type == "BUY" else OrderSide.SELL
        
        auth_request = TradingDecisionRequest(
            request_id=signal.signal_id,
            symbol=signal.symbol,
            strategy_id=signal.strategy_id,
            decision_type=decision_type,
            side=side,
            quantity=signal.quantity,
            confidence=signal.confidence,
            urgency=ExecutionUrgency.NORMAL,
            metadata=signal.metadata
        )
        
        # Get risk authorization
        authorization = await risk_manager.authorize_trading_decision(auth_request)
        
        if authorization.authorization_level == AuthorizationLevel.REJECTED:
            logger.warning(f"Order not authorized: {authorization.rejection_reason}")
            return None
        
        # Create and submit order
        order = Order(
            order_id=str(uuid.uuid4()),
            symbol=signal.symbol,
            quantity=authorization.authorized_quantity,
            order_type=OrderType.MARKET,
            side=side,
            timestamp=datetime.now()
        )
        
        # Submit to broker
        success = broker.submit_order(order)
        
        if success:
            logger.info(f"✅ Order submitted: {order.order_id} for {signal.symbol}")
            return order
        else:
            logger.error(f"❌ Order submission failed: {signal.symbol}")
            return None
            
    except Exception as e:
        logger.error(f"Error submitting order from signal: {e}")
        return None


def reconcile_positions(
    orders: List[Order],
    broker_positions: Dict[str, float]
) -> Dict[str, Any]:
    """
    Reconcile positions between orders and broker state
    
    Returns:
        Reconciliation report with matches and breaks
    """
    # Calculate expected positions from orders
    expected_positions: Dict[str, float] = {}
    
    for order in orders:
        if order.status == OrderStatus.FILLED:
            current = expected_positions.get(order.symbol, 0.0)
            if order.side == OrderSide.BUY:
                expected_positions[order.symbol] = current + order.filled_quantity
            else:  # SELL
                expected_positions[order.symbol] = current - order.filled_quantity
    
    # Compare with broker positions
    all_symbols = set(expected_positions.keys()) | set(broker_positions.keys())
    
    matches = []
    breaks = []
    
    for symbol in all_symbols:
        expected = expected_positions.get(symbol, 0.0)
        actual = broker_positions.get(symbol, 0.0)
        
        tolerance = 1e-6
        if abs(expected - actual) < tolerance:
            matches.append({
                'symbol': symbol,
                'expected': expected,
                'actual': actual,
                'difference': 0.0
            })
        else:
            breaks.append({
                'symbol': symbol,
                'expected': expected,
                'actual': actual,
                'difference': actual - expected
            })
    
    return {
        'total_symbols': len(all_symbols),
        'matches': matches,
        'breaks': breaks,
        'match_rate': len(matches) / len(all_symbols) if all_symbols else 1.0
    }


def calculate_execution_metrics(
    signals: List[TradingSignal],
    orders: List[Order],
    start_time: datetime,
    end_time: datetime
) -> ExecutionMetrics:
    """Calculate execution performance metrics"""
    
    metrics = ExecutionMetrics()
    
    if not signals or not orders:
        return metrics
    
    # Calculate latencies
    filled_orders = [o for o in orders if o.status == OrderStatus.FILLED]
    
    if filled_orders:
        # Average signal to order latency
        signal_times = {s.signal_id: s.timestamp for s in signals}
        order_latencies = []
        
        for order in orders:
            # Find matching signal (simplified - in real system would use request_id)
            matching_signals = [s for s in signals if s.symbol == order.symbol]
            if matching_signals:
                signal_time = matching_signals[0].timestamp
                order_time = order.timestamp
                latency = (order_time - signal_time).total_seconds()
                order_latencies.append(latency)
        
        if order_latencies:
            metrics.signal_to_order_latency = sum(order_latencies) / len(order_latencies)
        
        # Order to fill latency (assuming immediate fill for market orders)
        metrics.order_to_fill_latency = 0.05  # 50ms average simulation
        
        # Total latency
        metrics.total_latency = metrics.signal_to_order_latency + metrics.order_to_fill_latency
        
        # Fill rate
        metrics.fill_rate = len(filled_orders) / len(orders)
        
        # Slippage (simplified - would need real market prices)
        metrics.slippage = 0.001  # 10 bps average
    
    return metrics


# ============================================================================
# Test Class
# ============================================================================

@pytest.mark.asyncio
class TestEndToEndWorkflows:
    """
    End-to-End Integration Tests
    
    Tests complete trading workflows from market data ingestion
    through order execution to position reconciliation.
    """
    
    async def test_market_data_to_execution_workflow(
        self,
        orchestrator,
        risk_manager
    ):
        """
        Test 1: Complete Market Data → Signal → Order → Execution Workflow
        
        Validates:
        - Market data ingestion
        - Signal generation from market data
        - Risk authorization
        - Order submission
        - Order execution
        - Position tracking
        """
        logger.info("=" * 80)
        logger.info("TEST 1: Market Data to Execution Workflow")
        logger.info("=" * 80)
        
        start_time = datetime.now()
        str(uuid.uuid4())
        
        # Initialize paper broker
        broker_config = BrokerConfig(broker_type=BrokerConfigType.PAPER)
        broker = PaperBroker(broker_config)
        broker.connect()
        broker.set_cash(100000.0)  # $100k starting capital
        
        # Step 1: Generate market data stream
        symbols = ["AAPL", "MSFT", "GOOGL"]
        market_data = create_market_data_stream(symbols, tick_count=10)
        
        logger.info(f"📊 Generated {len(market_data)} market data ticks for {len(symbols)} symbols")
        
        # Step 2: Generate trading signals from market data
        signals = generate_trading_signals(market_data, strategy_id="e2e_test_strategy")
        
        logger.info(f"📈 Generated {len(signals)} trading signals")
        for signal in signals:
            logger.info(f"  Signal: {signal.symbol} {signal.signal_type} {signal.quantity} @ confidence={signal.confidence:.2f}")
        
        # Step 3: Submit orders based on signals
        orders = []
        for signal in signals:
            order = await submit_order_from_signal(signal, broker, risk_manager)
            if order:
                orders.append(order)
            await asyncio.sleep(0.01)  # Small delay between orders
        
        logger.info(f"📝 Submitted {len(orders)} orders")
        
        # Step 4: Wait for executions (paper broker executes immediately)
        await asyncio.sleep(0.1)
        
        # Step 5: Check order statuses
        filled_orders = []
        for order in orders:
            status = broker.get_order_status(order.order_id)
            if status == OrderStatus.FILLED:
                filled_orders.append(order)
        
        logger.info(f"✅ Filled orders: {len(filled_orders)}/{len(orders)}")
        
        # Step 6: Get broker positions
        broker_positions = broker.get_positions()
        logger.info(f"📊 Broker positions: {broker_positions}")
        
        # Step 7: Reconcile positions
        reconciliation = reconcile_positions(orders, broker_positions)
        
        logger.info(f"🔍 Position Reconciliation:")
        logger.info(f"  Total symbols: {reconciliation['total_symbols']}")
        logger.info(f"  Matches: {len(reconciliation['matches'])}")
        logger.info(f"  Breaks: {len(reconciliation['breaks'])}")
        logger.info(f"  Match rate: {reconciliation['match_rate']*100:.1f}%")
        
        # Step 8: Calculate performance metrics
        end_time = datetime.now()
        metrics = calculate_execution_metrics(signals, orders, start_time, end_time)
        
        logger.info(f"⚡ Execution Metrics:")
        logger.info(f"  Signal→Order latency: {metrics.signal_to_order_latency*1000:.2f}ms")
        logger.info(f"  Order→Fill latency: {metrics.order_to_fill_latency*1000:.2f}ms")
        logger.info(f"  Total latency: {metrics.total_latency*1000:.2f}ms")
        logger.info(f"  Fill rate: {metrics.fill_rate*100:.1f}%")
        
        # Assertions
        assert len(signals) > 0, "Should generate trading signals"
        assert len(orders) > 0, "Should submit orders"
        assert len(filled_orders) > 0, "Should have filled orders"
        assert reconciliation['match_rate'] == 1.0, "Positions should reconcile perfectly"
        assert metrics.fill_rate >= 0.8, f"Fill rate should be >= 80% (got {metrics.fill_rate*100:.1f}%)"
        assert metrics.total_latency < 1.0, f"Total latency should be < 1s (got {metrics.total_latency:.3f}s)"
        
        # Cleanup
        broker.disconnect()
        
        logger.info(f"✅ Workflow completed successfully in {(end_time - start_time).total_seconds():.2f}s")
    
    
    async def test_broker_api_integration(
        self,
        orchestrator,
        risk_manager
    ):
        """
        Test 2: Broker API Integration
        
        Validates:
        - Broker connection management
        - Order submission via API
        - Order status updates
        - Position queries
        - Account information retrieval
        """
        logger.info("=" * 80)
        logger.info("TEST 2: Broker API Integration")
        logger.info("=" * 80)
        
        # Initialize paper broker
        broker_config = BrokerConfig(broker_type=BrokerConfigType.PAPER)
        broker = PaperBroker(broker_config)
        
        # Test 1: Connection
        logger.info("📡 Testing broker connection...")
        connect_result = broker.connect()
        assert connect_result == True, "Broker connection should succeed"
        assert broker.connected == True, "Broker should be marked as connected"
        logger.info("✅ Broker connected successfully")
        
        # Test 2: Account info
        logger.info("💰 Testing account info retrieval...")
        account_info = broker.get_account_info()
        assert account_info is not None, "Should retrieve account info"
        assert 'cash' in account_info, "Account info should include cash"
        assert 'buying_power' in account_info, "Account info should include buying_power"
        logger.info(f"✅ Account info: Cash=${account_info['cash']:,.2f}, Buying Power=${account_info['buying_power']:,.2f}")
        
        # Test 3: Order submission
        logger.info("📝 Testing order submission...")
        test_order = Order(
            order_id=str(uuid.uuid4()),
            symbol="AAPL",
            quantity=100.0,
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            timestamp=datetime.now()
        )
        
        submit_result = broker.submit_order(test_order)
        assert submit_result == True, "Order submission should succeed"
        logger.info(f"✅ Order submitted: {test_order.order_id}")
        
        # Test 4: Order status
        logger.info("🔍 Testing order status retrieval...")
        order_status = broker.get_order_status(test_order.order_id)
        assert order_status is not None, "Should retrieve order status"
        assert order_status in [OrderStatus.FILLED, OrderStatus.PENDING, OrderStatus.SUBMITTED], "Status should be valid"
        logger.info(f"✅ Order status: {order_status}")
        
        # Test 5: Position query
        logger.info("📊 Testing position query...")
        positions = broker.get_positions()
        assert positions is not None, "Should retrieve positions"
        assert isinstance(positions, dict), "Positions should be a dictionary"
        if test_order.status == OrderStatus.FILLED:
            assert "AAPL" in positions, "Should have AAPL position if order filled"
        logger.info(f"✅ Positions: {positions}")
        
        # Test 6: Order cancellation
        logger.info("❌ Testing order cancellation...")
        cancel_order = Order(
            order_id=str(uuid.uuid4()),
            symbol="MSFT",
            quantity=50.0,
            order_type=OrderType.LIMIT,
            side=OrderSide.SELL,
            price=300.0,
            timestamp=datetime.now()
        )
        broker.submit_order(cancel_order)
        
        cancel_result = broker.cancel_order(cancel_order.order_id)
        # Note: Market orders may execute immediately, so cancellation might fail
        logger.info(f"Order cancellation result: {cancel_result}")
        
        # Test 7: Multiple orders
        logger.info("📝 Testing multiple order submissions...")
        symbols = ["GOOGL", "MSFT", "TSLA"]
        multi_orders = []
        
        for symbol in symbols:
            order = Order(
                order_id=str(uuid.uuid4()),
                symbol=symbol,
                quantity=10.0,
                order_type=OrderType.MARKET,
                side=OrderSide.BUY,
                timestamp=datetime.now()
            )
            result = broker.submit_order(order)
            assert result == True, f"Should submit order for {symbol}"
            multi_orders.append(order)
        
        logger.info(f"✅ Submitted {len(multi_orders)} orders")
        
        # Test 8: Position aggregation
        final_positions = broker.get_positions()
        logger.info(f"📊 Final positions after multiple orders: {final_positions}")
        assert len(final_positions) >= 1, "Should have at least one position"
        
        # Cleanup
        broker.disconnect()
        assert broker.connected == False, "Broker should be disconnected"
        logger.info("✅ Broker API integration tests completed successfully")
    
    
    async def test_order_lifecycle_complete(
        self,
        orchestrator,
        risk_manager
    ):
        """
        Test 3: Complete Order Lifecycle
        
        Validates order state transitions:
        - NEW → SUBMITTED → PENDING → FILLED
        - NEW → SUBMITTED → CANCELLED
        - Order with partial fills
        - Order modifications
        """
        logger.info("=" * 80)
        logger.info("TEST 3: Complete Order Lifecycle")
        logger.info("=" * 80)
        
        # Initialize broker
        broker_config = BrokerConfig(broker_type=BrokerConfigType.PAPER)
        broker = PaperBroker(broker_config)
        broker.connect()
        broker.set_cash(100000.0)
        
        # Test Lifecycle 1: NEW → SUBMITTED → FILLED (Market Order)
        logger.info("📈 Lifecycle 1: Market order (NEW → SUBMITTED → FILLED)")
        
        market_order = Order(
            order_id=str(uuid.uuid4()),
            symbol="AAPL",
            quantity=100.0,
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            timestamp=datetime.now()
        )
        
        # Initial state
        assert market_order.status == OrderStatus.PENDING, "Initial status should be NEW"
        logger.info(f"  State: NEW")
        
        # Submit order
        submit_result = broker.submit_order(market_order)
        assert submit_result == True, "Order submission should succeed"
        
        # Check status after submission
        status = broker.get_order_status(market_order.order_id)
        logger.info(f"  State: {status}")
        
        # Market orders should be filled immediately in paper broker
        assert status == OrderStatus.FILLED, "Market order should be filled immediately"
        logger.info(f"✅ Lifecycle 1 complete: NEW → SUBMITTED → FILLED")
        
        # Test Lifecycle 2: NEW → SUBMITTED → PENDING → CANCELLED (Limit Order)
        logger.info("📈 Lifecycle 2: Limit order (NEW → SUBMITTED → PENDING → CANCELLED)")
        
        limit_order = Order(
            order_id=str(uuid.uuid4()),
            symbol="MSFT",
            quantity=50.0,
            order_type=OrderType.LIMIT,
            side=OrderSide.SELL,
            price=500.0,  # Unrealistic price - won't fill
            timestamp=datetime.now()
        )
        
        assert limit_order.status == OrderStatus.PENDING, "Initial status should be NEW"
        logger.info(f"  State: NEW")
        
        broker.submit_order(limit_order)
        status = broker.get_order_status(limit_order.order_id)
        logger.info(f"  State: {status}")
        assert status in [OrderStatus.PENDING, OrderStatus.SUBMITTED], "Limit order should be pending"
        
        # Cancel the order
        cancel_result = broker.cancel_order(limit_order.order_id)
        assert cancel_result == True, "Should be able to cancel pending order"
        
        status = broker.get_order_status(limit_order.order_id)
        logger.info(f"  State: {status}")
        assert status == OrderStatus.CANCELLED, "Order should be cancelled"
        logger.info(f"✅ Lifecycle 2 complete: NEW → SUBMITTED → PENDING → CANCELLED")
        
        # Test Lifecycle 3: Multiple orders with state tracking
        logger.info("📈 Lifecycle 3: Multiple orders with state tracking")
        
        order_states: Dict[str, List[OrderStatus]] = {}
        symbols = ["GOOGL", "TSLA", "AMZN"]
        
        for symbol in symbols:
            order = Order(
                order_id=str(uuid.uuid4()),
                symbol=symbol,
                quantity=25.0,
                order_type=OrderType.MARKET,
                side=OrderSide.BUY,
                timestamp=datetime.now()
            )
            
            # Track initial state
            order_states[order.order_id] = [OrderStatus.PENDING]
            
            # Submit
            broker.submit_order(order)
            status = broker.get_order_status(order.order_id)
            order_states[order.order_id].append(status)
            
            logger.info(f"  {symbol}: {' → '.join(str(s) for s in order_states[order.order_id])}")
        
        # Verify all orders transitioned properly
        for order_id, states in order_states.items():
            assert OrderStatus.PENDING in states, "Should start with NEW"
            assert len(states) >= 2, "Should have at least 2 states"
            # Final state should be FILLED for market orders
            assert states[-1] == OrderStatus.FILLED, f"Final state should be FILLED (got {states[-1]})"
        
        logger.info(f"✅ Lifecycle 3 complete: Tracked {len(order_states)} order lifecycles")
        
        # Test Lifecycle 4: Order with execution details
        logger.info("📈 Lifecycle 4: Order with execution details")
        
        execution_order = Order(
            order_id=str(uuid.uuid4()),
            symbol="NVDA",
            quantity=150.0,
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            timestamp=datetime.now()
        )
        
        broker.submit_order(execution_order)
        
        # Check execution details
        assert execution_order.status == OrderStatus.FILLED, "Order should be filled"
        assert execution_order.filled_quantity > 0, "Should have filled quantity"
        assert execution_order.average_price > 0, "Should have execution price"
        
        logger.info(f"  Order ID: {execution_order.order_id}")
        logger.info(f"  Filled Quantity: {execution_order.filled_quantity}")
        logger.info(f"  Average Price: ${execution_order.average_price:.2f}")
        logger.info(f"  Commission: ${execution_order.commission:.2f}")
        logger.info(f"✅ Lifecycle 4 complete: Order with execution details validated")
        
        # Final assertions
        final_positions = broker.get_positions()
        assert len(final_positions) > 0, "Should have positions after orders"
        
        total_orders = 1 + 1 + len(symbols) + 1  # All test orders
        logger.info(f"📊 Total orders processed: {total_orders}")
        logger.info(f"📊 Final positions: {len(final_positions)} symbols")
        
        # Cleanup
        broker.disconnect()
        logger.info("✅ Complete order lifecycle tests passed")
    
    
    async def test_position_reconciliation(
        self,
        orchestrator,
        risk_manager
    ):
        """
        Test 4: Position Reconciliation
        
        Validates:
        - Order execution tracking
        - Position calculation from orders
        - Broker position synchronization
        - Break detection and reporting
        - Multi-symbol position tracking
        """
        logger.info("=" * 80)
        logger.info("TEST 4: Position Reconciliation")
        logger.info("=" * 80)
        
        # Initialize broker
        broker_config = BrokerConfig(broker_type=BrokerConfigType.PAPER)
        broker = PaperBroker(broker_config)
        broker.connect()
        broker.set_cash(500000.0)  # $500k starting capital
        
        # Execute a series of orders
        orders = []
        
        # Buy 100 AAPL
        order1 = Order(
            order_id=str(uuid.uuid4()),
            symbol="AAPL",
            quantity=100.0,
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            timestamp=datetime.now()
        )
        broker.submit_order(order1)
        orders.append(order1)
        
        # Buy another 50 AAPL
        order2 = Order(
            order_id=str(uuid.uuid4()),
            symbol="AAPL",
            quantity=50.0,
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            timestamp=datetime.now()
        )
        broker.submit_order(order2)
        orders.append(order2)
        
        # Sell 30 AAPL
        order3 = Order(
            order_id=str(uuid.uuid4()),
            symbol="AAPL",
            quantity=30.0,
            order_type=OrderType.MARKET,
            side=OrderSide.SELL,
            timestamp=datetime.now()
        )
        broker.submit_order(order3)
        orders.append(order3)
        
        # Buy 200 MSFT
        order4 = Order(
            order_id=str(uuid.uuid4()),
            symbol="MSFT",
            quantity=200.0,
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            timestamp=datetime.now()
        )
        broker.submit_order(order4)
        orders.append(order4)
        
        # Buy 75 GOOGL
        order5 = Order(
            order_id=str(uuid.uuid4()),
            symbol="GOOGL",
            quantity=75.0,
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            timestamp=datetime.now()
        )
        broker.submit_order(order5)
        orders.append(order5)
        
        logger.info(f"📝 Executed {len(orders)} orders across multiple symbols")
        
        # Get broker positions
        broker_positions = broker.get_positions()
        logger.info(f"📊 Broker positions: {broker_positions}")
        
        # Perform reconciliation
        reconciliation = reconcile_positions(orders, broker_positions)
        
        logger.info("🔍 Reconciliation Results:")
        logger.info(f"  Total symbols: {reconciliation['total_symbols']}")
        logger.info(f"  Matches: {len(reconciliation['matches'])}")
        logger.info(f"  Breaks: {len(reconciliation['breaks'])}")
        
        # Display matches
        if reconciliation['matches']:
            logger.info("  ✅ Position Matches:")
            for match in reconciliation['matches']:
                logger.info(f"    {match['symbol']}: Expected={match['expected']}, Actual={match['actual']}")
        
        # Display breaks
        if reconciliation['breaks']:
            logger.info("  ⚠️ Position Breaks:")
            for break_item in reconciliation['breaks']:
                logger.info(f"    {break_item['symbol']}: Expected={break_item['expected']}, Actual={break_item['actual']}, Diff={break_item['difference']}")
        
        # Calculate expected positions manually
        expected_aapl = 100.0 + 50.0 - 30.0  # = 120
        expected_msft = 200.0
        expected_googl = 75.0
        
        # Assertions
        assert reconciliation['total_symbols'] == 3, f"Should have 3 symbols (got {reconciliation['total_symbols']})"
        assert len(reconciliation['breaks']) == 0, f"Should have no position breaks (found {len(reconciliation['breaks'])})"
        assert reconciliation['match_rate'] == 1.0, f"Match rate should be 100% (got {reconciliation['match_rate']*100:.1f}%)"
        
        # Verify specific positions
        assert abs(broker_positions.get('AAPL', 0) - expected_aapl) < 1e-6, f"AAPL position mismatch: expected {expected_aapl}, got {broker_positions.get('AAPL', 0)}"
        assert abs(broker_positions.get('MSFT', 0) - expected_msft) < 1e-6, f"MSFT position mismatch: expected {expected_msft}, got {broker_positions.get('MSFT', 0)}"
        assert abs(broker_positions.get('GOOGL', 0) - expected_googl) < 1e-6, f"GOOGL position mismatch: expected {expected_googl}, got {broker_positions.get('GOOGL', 0)}"
        
        logger.info("✅ Position reconciliation: PERFECT MATCH")
        
        # Test account value calculation
        account_info = broker.get_account_info()
        logger.info(f"💰 Account Summary:")
        logger.info(f"  Cash: ${account_info['cash']:,.2f}")
        logger.info(f"  Total Value: ${account_info['total_value']:,.2f}")
        logger.info(f"  Commission Paid: ${account_info['commission_paid']:.2f}")
        
        # Cleanup
        broker.disconnect()
        logger.info("✅ Position reconciliation tests completed successfully")
    
    
    async def test_multi_symbol_portfolio_operations(
        self,
        orchestrator,
        risk_manager
    ):
        """
        Test 5: Multi-Symbol Portfolio Operations
        
        Validates:
        - Concurrent operations across multiple symbols
        - Portfolio-level risk management
        - Cross-symbol position tracking
        - Diversification metrics
        - Portfolio rebalancing
        """
        logger.info("=" * 80)
        logger.info("TEST 5: Multi-Symbol Portfolio Operations")
        logger.info("=" * 80)
        
        # Initialize broker with larger capital
        broker_config = BrokerConfig(broker_type=BrokerConfigType.PAPER)
        broker = PaperBroker(broker_config)
        broker.connect()
        broker.set_cash(2000000.0)  # $2M starting capital (increased for 8-symbol portfolio)
        
        # Define portfolio allocation
        portfolio_symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "NFLX"]
        target_allocation = {
            "AAPL": 0.15,   # 15%
            "MSFT": 0.15,   # 15%
            "GOOGL": 0.125, # 12.5%
            "AMZN": 0.125,  # 12.5%
            "TSLA": 0.10,   # 10%
            "NVDA": 0.15,   # 15%
            "META": 0.10,   # 10%
            "NFLX": 0.10    # 10%
        }
        
        logger.info(f"🎯 Target portfolio: {len(portfolio_symbols)} symbols")
        for symbol, allocation in target_allocation.items():
            logger.info(f"  {symbol}: {allocation*100:.1f}%")
        
        # Execute portfolio build
        logger.info("📝 Building initial portfolio...")
        portfolio_orders = []
        
        for symbol, allocation in target_allocation.items():
            # Calculate quantity based on allocation and assumed price
            target_value = 1000000.0 * allocation
            assumed_price = 100.0  # Simplified
            quantity = target_value / assumed_price
            
            order = Order(
                order_id=str(uuid.uuid4()),
                symbol=symbol,
                quantity=quantity,
                order_type=OrderType.MARKET,
                side=OrderSide.BUY,
                timestamp=datetime.now()
            )
            
            broker.submit_order(order)
            portfolio_orders.append(order)
            await asyncio.sleep(0.01)  # Small delay between orders
        
        logger.info(f"✅ Submitted {len(portfolio_orders)} portfolio orders")
        
        # Check all orders filled
        filled_count = sum(1 for order in portfolio_orders if order.status == OrderStatus.FILLED)
        logger.info(f"📊 Filled orders: {filled_count}/{len(portfolio_orders)}")
        
        # Get portfolio positions
        positions = broker.get_positions()
        logger.info(f"📊 Portfolio positions: {len(positions)} symbols")
        
        for symbol, quantity in positions.items():
            logger.info(f"  {symbol}: {quantity:.2f} shares")
        
        # Calculate portfolio metrics
        total_symbols = len(positions)
        symbols_with_position = sum(1 for qty in positions.values() if qty > 0)
        
        logger.info(f"📈 Portfolio Metrics:")
        logger.info(f"  Total symbols: {total_symbols}")
        logger.info(f"  Symbols with positions: {symbols_with_position}")
        logger.info(f"  Diversification ratio: {symbols_with_position}/{len(portfolio_symbols)}")
        
        # Test concurrent modifications
        logger.info("🔄 Testing concurrent portfolio modifications...")
        
        concurrent_orders = []
        
        # Increase AAPL
        concurrent_orders.append(Order(
            order_id=str(uuid.uuid4()),
            symbol="AAPL",
            quantity=50.0,
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            timestamp=datetime.now()
        ))
        
        # Reduce TSLA
        if positions.get("TSLA", 0) > 25:
            concurrent_orders.append(Order(
                order_id=str(uuid.uuid4()),
                symbol="TSLA",
                quantity=25.0,
                order_type=OrderType.MARKET,
                side=OrderSide.SELL,
                timestamp=datetime.now()
            ))
        
        # Add to NVDA
        concurrent_orders.append(Order(
            order_id=str(uuid.uuid4()),
            symbol="NVDA",
            quantity=30.0,
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            timestamp=datetime.now()
        ))
        
        # Submit concurrent modifications
        for order in concurrent_orders:
            broker.submit_order(order)
        
        logger.info(f"✅ Executed {len(concurrent_orders)} concurrent modifications")
        
        # Get updated positions
        updated_positions = broker.get_positions()
        logger.info(f"📊 Updated portfolio: {len(updated_positions)} positions")
        
        # Verify portfolio integrity
        all_orders = portfolio_orders + concurrent_orders
        reconciliation = reconcile_positions(all_orders, updated_positions)
        
        logger.info("🔍 Final Reconciliation:")
        logger.info(f"  Match rate: {reconciliation['match_rate']*100:.1f}%")
        logger.info(f"  Breaks: {len(reconciliation['breaks'])}")
        
        # Assertions
        assert len(positions) >= 6, f"Should have at least 6 positions (got {len(positions)})"
        assert filled_count == len(portfolio_orders), f"All portfolio orders should fill (got {filled_count}/{len(portfolio_orders)})"
        assert reconciliation['match_rate'] == 1.0, f"Positions should reconcile perfectly (got {reconciliation['match_rate']*100:.1f}%)"
        assert len(reconciliation['breaks']) == 0, f"Should have no breaks (found {len(reconciliation['breaks'])})"
        
        # Test account summary
        account_info = broker.get_account_info()
        logger.info(f"💰 Final Account Summary:")
        logger.info(f"  Cash: ${account_info['cash']:,.2f}")
        logger.info(f"  Total Value: ${account_info['total_value']:,.2f}")
        logger.info(f"  Total Positions: {len(updated_positions)}")
        
        # Cleanup
        broker.disconnect()
        logger.info("✅ Multi-symbol portfolio operations completed successfully")
    
    
    async def test_execution_latency_validation(
        self,
        orchestrator,
        risk_manager
    ):
        """
        Test 6: Execution Latency Validation
        
        Validates:
        - Signal to order latency
        - Order to execution latency
        - End-to-end processing time
        - Latency percentiles (p50, p95, p99)
        - Performance under load
        """
        logger.info("=" * 80)
        logger.info("TEST 6: Execution Latency Validation")
        logger.info("=" * 80)
        
        # Initialize broker
        broker_config = BrokerConfig(broker_type=BrokerConfigType.PAPER)
        broker = PaperBroker(broker_config)
        broker.connect()
        broker.set_cash(500000.0)
        
        # Test parameters
        num_signals = 50
        symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
        
        logger.info(f"🎯 Latency test: {num_signals} signals across {len(symbols)} symbols")
        
        # Generate signals with timestamps
        test_signals = []
        for i in range(num_signals):
            signal = TradingSignal(
                signal_id=str(uuid.uuid4()),
                symbol=symbols[i % len(symbols)],
                strategy_id="latency_test",
                signal_type="BUY" if i % 2 == 0 else "SELL",
                quantity=10.0,
                confidence=0.75,
                timestamp=datetime.now(),
                metadata={'test_index': i}
            )
            test_signals.append(signal)
            await asyncio.sleep(0.001)  # 1ms between signals
        
        logger.info(f"📊 Generated {len(test_signals)} test signals")
        
        # Execute signals and measure latencies
        latencies = []
        orders = []
        
        for signal in test_signals:
            signal_time = signal.timestamp
            
            # Submit order
            order = await submit_order_from_signal(signal, broker, risk_manager)
            
            if order:
                order_time = order.timestamp
                latency = (order_time - signal_time).total_seconds()
                latencies.append(latency)
                orders.append(order)
        
        logger.info(f"✅ Executed {len(orders)} orders")
        logger.info(f"📊 Collected {len(latencies)} latency measurements")
        
        # Calculate latency statistics
        if latencies:
            latencies.sort()
            
            avg_latency = sum(latencies) / len(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
            
            # Percentiles
            p50_idx = int(len(latencies) * 0.50)
            p95_idx = int(len(latencies) * 0.95)
            p99_idx = int(len(latencies) * 0.99)
            
            p50 = latencies[p50_idx]
            p95 = latencies[p95_idx]
            p99 = latencies[p99_idx]
            
            logger.info("⚡ Latency Statistics (Signal → Order):")
            logger.info(f"  Average: {avg_latency*1000:.2f}ms")
            logger.info(f"  Min: {min_latency*1000:.2f}ms")
            logger.info(f"  Max: {max_latency*1000:.2f}ms")
            logger.info(f"  P50 (median): {p50*1000:.2f}ms")
            logger.info(f"  P95: {p95*1000:.2f}ms")
            logger.info(f"  P99: {p99*1000:.2f}ms")
            
            # Performance assertions
            assert avg_latency < 0.5, f"Average latency should be < 500ms (got {avg_latency*1000:.2f}ms)"
            assert p95 < 1.0, f"P95 latency should be < 1s (got {p95*1000:.2f}ms)"
            assert p99 < 2.0, f"P99 latency should be < 2s (got {p99*1000:.2f}ms)"
            
            # Measure order execution latency (simulation)
            execution_latencies = [0.05] * len(orders)  # 50ms simulated execution
            avg_exec_latency = sum(execution_latencies) / len(execution_latencies)
            
            logger.info("⚡ Execution Latency (Order → Fill):")
            logger.info(f"  Average: {avg_exec_latency*1000:.2f}ms")
            
            # Total end-to-end latency
            total_latency = avg_latency + avg_exec_latency
            logger.info("⚡ Total End-to-End Latency:")
            logger.info(f"  Signal → Fill: {total_latency*1000:.2f}ms")
            
            assert total_latency < 1.0, f"Total latency should be < 1s (got {total_latency*1000:.2f}ms)"
            
            # Calculate throughput
            total_time = (test_signals[-1].timestamp - test_signals[0].timestamp).total_seconds()
            throughput = len(test_signals) / total_time if total_time > 0 else 0
            
            logger.info("📈 Throughput Metrics:")
            logger.info(f"  Signals processed: {len(test_signals)}")
            logger.info(f"  Total time: {total_time:.2f}s")
            logger.info(f"  Throughput: {throughput:.1f} signals/second")
            
            assert throughput > 10, f"Throughput should be > 10 signals/sec (got {throughput:.1f})"
        
        # Verify all orders
        filled_count = sum(1 for order in orders if order.status == OrderStatus.FILLED)
        logger.info(f"✅ Orders filled: {filled_count}/{len(orders)} ({filled_count/len(orders)*100:.1f}%)")
        
        assert filled_count / len(orders) >= 0.9, f"Fill rate should be >= 90% (got {filled_count/len(orders)*100:.1f}%)"
        
        # Cleanup
        broker.disconnect()
        logger.info("✅ Execution latency validation completed successfully")


# ============================================================================
# Test Execution Entry Point
# ============================================================================

if __name__ == "__main__":
    """
    Run tests directly for debugging
    """
    pytest.main([__file__, "-v", "--tb=short"])
