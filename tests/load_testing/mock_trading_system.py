"""
Mock Trading System
===================

Simulates the real trading system for load testing without touching production.

Components:
- OrderExecutor: Simulates order execution with realistic latencies
- RiskManager: Simulates risk checks (position limits, exposure limits)
- PositionTracker: Tracks positions and P&L
- MarketDataFeed: Simulates market data updates
"""

import asyncio
import random
import logging
from datetime import datetime
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class OrderStatus(Enum):
    """Order execution status"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    FILLED = "filled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class RejectionReason(Enum):
    """Reasons for order rejection"""
    RISK_LIMIT = "risk_limit_exceeded"
    POSITION_LIMIT = "position_limit_exceeded"
    INVALID_ORDER = "invalid_order"
    SYSTEM_ERROR = "system_error"


@dataclass
class OrderResult:
    """Result of order processing"""
    order_id: str
    status: OrderStatus
    execution_time_ms: float
    fill_price: Optional[float] = None
    fill_quantity: Optional[int] = None
    rejection_reason: Optional[RejectionReason] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Position:
    """Position tracking"""
    symbol: str
    quantity: int = 0
    avg_price: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0


class MockMarketData:
    """
    Mock market data feed
    
    Simulates realistic price movements and market data latency.
    """
    
    def __init__(self):
        self.prices: Dict[str, float] = {}
        self._initialize_prices()
    
    def _initialize_prices(self):
        """Initialize with realistic stock prices"""
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'META', 'NVDA', 'JPM', 'BAC', 'WMT']
        base_prices = [150, 2800, 350, 3200, 800, 450, 900, 150, 30, 160]
        
        for symbol, price in zip(symbols, base_prices):
            self.prices[symbol] = price
    
    def get_price(self, symbol: str) -> float:
        """Get current price with small random walk"""
        if symbol not in self.prices:
            self.prices[symbol] = random.uniform(50, 500)
        
        # Simulate price movement (±0.1%)
        movement = random.uniform(-0.001, 0.001)
        self.prices[symbol] *= (1 + movement)
        
        return round(self.prices[symbol], 2)
    
    async def get_price_async(self, symbol: str) -> float:
        """Async version with simulated latency"""
        await asyncio.sleep(random.uniform(0.001, 0.005))  # 1-5ms latency
        return self.get_price(symbol)


class MockRiskManager:
    """
    Mock risk management system
    
    Simulates risk checks with realistic validation logic.
    """
    
    def __init__(self, max_position_size: int = 10000, max_total_exposure: float = 1_000_000):
        self.max_position_size = max_position_size
        self.max_total_exposure = max_total_exposure
        self.rejection_rate = 0.02  # 2% rejection rate for realism
    
    async def check_order(self, order: Dict[str, Any], current_position: int, total_exposure: float) -> tuple[bool, Optional[RejectionReason]]:
        """
        Check if order passes risk limits
        
        Returns: (approved, rejection_reason)
        """
        # Simulate risk check latency
        await asyncio.sleep(random.uniform(0.002, 0.008))  # 2-8ms
        
        quantity = order.get('quantity', 0)
        price = order.get('price', 0)
        
        # Position limit check
        new_position = abs(current_position + quantity)
        if new_position > self.max_position_size:
            logger.debug(f"Order rejected: position limit ({new_position} > {self.max_position_size})")
            return False, RejectionReason.POSITION_LIMIT
        
        # Exposure limit check
        new_exposure = total_exposure + abs(quantity * price)
        if new_exposure > self.max_total_exposure:
            logger.debug(f"Order rejected: exposure limit ({new_exposure} > {self.max_total_exposure})")
            return False, RejectionReason.RISK_LIMIT
        
        # Random rejection for realism (system errors, etc.)
        if random.random() < self.rejection_rate:
            logger.debug("Order rejected: random system error")
            return False, RejectionReason.SYSTEM_ERROR
        
        return True, None


class MockPositionTracker:
    """
    Mock position tracking system
    
    Tracks positions, P&L, and exposure across all symbols.
    """
    
    def __init__(self):
        self.positions: Dict[str, Position] = {}
        self.total_exposure: float = 0.0
        self.total_realized_pnl: float = 0.0
    
    def get_position(self, symbol: str) -> Position:
        """Get current position for symbol"""
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol=symbol)
        return self.positions[symbol]
    
    def update_position(self, symbol: str, quantity: int, price: float):
        """Update position after order execution"""
        position = self.get_position(symbol)
        
        if position.quantity == 0:
            # New position
            position.quantity = quantity
            position.avg_price = price
        else:
            if (position.quantity > 0 and quantity > 0) or (position.quantity < 0 and quantity < 0):
                # Adding to position
                total_cost = (position.quantity * position.avg_price) + (quantity * price)
                position.quantity += quantity
                position.avg_price = total_cost / position.quantity if position.quantity != 0 else 0
            else:
                # Reducing/closing position
                closed_qty = min(abs(position.quantity), abs(quantity))
                pnl = closed_qty * (price - position.avg_price) * (1 if position.quantity > 0 else -1)
                position.realized_pnl += pnl
                self.total_realized_pnl += pnl
                position.quantity += quantity
        
        # Update total exposure
        self.total_exposure = sum(
            abs(pos.quantity * pos.avg_price) 
            for pos in self.positions.values()
        )
    
    def get_summary(self) -> Dict[str, Any]:
        """Get portfolio summary"""
        return {
            'num_positions': len([p for p in self.positions.values() if p.quantity != 0]),
            'total_exposure': self.total_exposure,
            'total_realized_pnl': self.total_realized_pnl,
            'positions': {
                symbol: {
                    'quantity': pos.quantity,
                    'avg_price': pos.avg_price,
                    'realized_pnl': pos.realized_pnl
                }
                for symbol, pos in self.positions.items()
                if pos.quantity != 0
            }
        }


class MockOrderExecutor:
    """
    Mock order execution system
    
    Simulates realistic order execution with latency, fills, and rejections.
    """
    
    def __init__(self, market_data: MockMarketData, risk_manager: MockRiskManager, 
                 position_tracker: MockPositionTracker):
        self.market_data = market_data
        self.risk_manager = risk_manager
        self.position_tracker = position_tracker
        self.fill_rate = 0.95  # 95% fill rate
        self.avg_execution_latency_ms = 50  # 50ms average
    
    async def execute_order(self, order: Dict[str, Any]) -> OrderResult:
        """
        Execute order with realistic latency and behavior
        
        Process:
        1. Risk check (2-8ms)
        2. Order routing (10-30ms)
        3. Market execution (30-100ms)
        4. Confirmation (5-15ms)
        
        Total: 47-153ms (avg ~75ms)
        """
        start_time = asyncio.get_event_loop().time()
        order_id = order['order_id']
        symbol = order['symbol']
        quantity = order['quantity']
        
        # Step 1: Risk check
        current_position = self.position_tracker.get_position(symbol).quantity
        approved, rejection_reason = await self.risk_manager.check_order(
            order, current_position, self.position_tracker.total_exposure
        )
        
        if not approved:
            execution_time = (asyncio.get_event_loop().time() - start_time) * 1000
            return OrderResult(
                order_id=order_id,
                status=OrderStatus.REJECTED,
                execution_time_ms=execution_time,
                rejection_reason=rejection_reason
            )
        
        # Step 2: Order routing simulation
        await asyncio.sleep(random.uniform(0.010, 0.030))  # 10-30ms
        
        # Step 3: Market execution simulation
        await asyncio.sleep(random.uniform(0.030, 0.100))  # 30-100ms
        
        # Check if order fills (95% fill rate)
        if random.random() > self.fill_rate:
            execution_time = (asyncio.get_event_loop().time() - start_time) * 1000
            return OrderResult(
                order_id=order_id,
                status=OrderStatus.REJECTED,
                execution_time_ms=execution_time,
                rejection_reason=RejectionReason.SYSTEM_ERROR
            )
        
        # Step 4: Get fill price and confirm
        fill_price = await self.market_data.get_price_async(symbol)
        await asyncio.sleep(random.uniform(0.005, 0.015))  # 5-15ms confirmation
        
        # Update position
        self.position_tracker.update_position(symbol, quantity, fill_price)
        
        execution_time = (asyncio.get_event_loop().time() - start_time) * 1000
        
        return OrderResult(
            order_id=order_id,
            status=OrderStatus.FILLED,
            execution_time_ms=execution_time,
            fill_price=fill_price,
            fill_quantity=quantity
        )


class MockTradingSystem:
    """
    Complete mock trading system
    
    Integrates all components for realistic testing.
    """
    
    def __init__(self, max_position_size: int = 10000, max_total_exposure: float = 1_000_000):
        self.market_data = MockMarketData()
        self.risk_manager = MockRiskManager(max_position_size, max_total_exposure)
        self.position_tracker = MockPositionTracker()
        self.executor = MockOrderExecutor(
            self.market_data, self.risk_manager, self.position_tracker
        )
        self.orders_processed = 0
        self.orders_filled = 0
        self.orders_rejected = 0
    
    async def submit_order(self, order: Dict[str, Any]) -> OrderResult:
        """Submit order to the system"""
        result = await self.executor.execute_order(order)
        
        self.orders_processed += 1
        if result.status == OrderStatus.FILLED:
            self.orders_filled += 1
        elif result.status == OrderStatus.REJECTED:
            self.orders_rejected += 1
        
        return result
    
    async def submit_orders_batch(self, orders: List[Dict[str, Any]]) -> List[OrderResult]:
        """Submit multiple orders concurrently"""
        tasks = [self.submit_order(order) for order in orders]
        return await asyncio.gather(*tasks)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        return {
            'orders_processed': self.orders_processed,
            'orders_filled': self.orders_filled,
            'orders_rejected': self.orders_rejected,
            'fill_rate': self.orders_filled / self.orders_processed if self.orders_processed > 0 else 0,
            'rejection_rate': self.orders_rejected / self.orders_processed if self.orders_processed > 0 else 0,
            'portfolio': self.position_tracker.get_summary()
        }
    
    def reset(self):
        """Reset system state"""
        self.market_data = MockMarketData()
        self.position_tracker = MockPositionTracker()
        self.executor = MockOrderExecutor(
            self.market_data, self.risk_manager, self.position_tracker
        )
        self.orders_processed = 0
        self.orders_filled = 0
        self.orders_rejected = 0


# Example usage
async def example_usage():
    """Example of how to use the mock trading system"""
    system = MockTradingSystem()
    
    # Submit a test order
    order = {
        'order_id': 'TEST001',
        'symbol': 'AAPL',
        'quantity': 100,
        'side': 'BUY',
        'strategy': 'momentum'
    }
    
    result = await system.submit_order(order)
    print(f"Order {result.order_id}: {result.status.value}")
    print(f"Execution time: {result.execution_time_ms:.2f}ms")
    
    if result.status == OrderStatus.FILLED:
        print(f"Fill price: ${result.fill_price:.2f}")
    
    print("\nSystem stats:", system.get_stats())


if __name__ == '__main__':
    asyncio.run(example_usage())
