"""
Order Generator for Load Testing
=================================

Generates realistic trading orders for production load testing.

Features:
- Realistic order patterns (market hours, volume profiles)
- Multi-strategy simulation (momentum, mean reversion, pairs)
- Configurable order rates and distribution
- Market condition simulation
"""

import asyncio
import random
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import numpy as np

logger = logging.getLogger(__name__)


class OrderPattern(Enum):
    """Order generation patterns"""
    STEADY = "steady"  # Constant rate
    BURST = "burst"  # Periodic bursts
    MARKET_HOURS = "market_hours"  # Realistic market hours pattern
    RANDOM = "random"  # Random intervals
    STRESS = "stress"  # Maximum stress load


class StrategyType(Enum):
    """Strategy types for order generation"""
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    PAIRS_TRADING = "pairs_trading"
    MIXED = "mixed"


@dataclass
class OrderGeneratorConfig:
    """Configuration for order generator"""
    
    # Order rate settings
    target_orders_per_day: int = 10000
    pattern: OrderPattern = OrderPattern.MARKET_HOURS
    
    # Strategy distribution (should sum to 1.0)
    strategy_weights: Dict[str, float] = field(default_factory=lambda: {
        "momentum": 0.35,
        "mean_reversion": 0.35,
        "pairs_trading": 0.30
    })
    
    # Order size distribution
    min_order_size: int = 100
    max_order_size: int = 10000
    avg_order_size: int = 1000
    
    # Symbol pool
    symbols: List[str] = field(default_factory=lambda: [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'JPM',
        'BAC', 'WFC', 'GS', 'MS', 'V', 'MA', 'XOM', 'CVX', 'PFE', 'JNJ',
        'UNH', 'WMT', 'HD', 'DIS', 'NFLX', 'INTC', 'CSCO', 'ORCL'
    ])
    
    # Market hours (US Eastern Time)
    market_open_hour: int = 9  # 9:30 AM
    market_open_minute: int = 30
    market_close_hour: int = 16  # 4:00 PM
    market_close_minute: int = 0
    
    # Burst settings (for BURST pattern)
    burst_frequency_minutes: int = 15
    burst_duration_seconds: int = 60
    burst_multiplier: float = 5.0
    
    # Realistic delays
    min_order_interval_ms: int = 10
    max_order_interval_ms: int = 5000


@dataclass
class GeneratedOrder:
    """Generated order for testing"""
    order_id: str
    symbol: str
    side: str  # BUY or SELL
    quantity: float
    order_type: str  # MARKET, LIMIT
    limit_price: Optional[float] = None
    strategy: str = "momentum"
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class OrderGenerator:
    """
    Realistic Order Generator for Load Testing
    
    Generates orders following realistic trading patterns:
    - Market hours concentration
    - Strategy-specific patterns
    - Realistic order sizes and intervals
    """
    
    def __init__(self, config: Optional[OrderGeneratorConfig] = None):
        self.config = config or OrderGeneratorConfig()
        self.orders_generated = 0
        self.is_running = False
        self._generation_task: Optional[asyncio.Task] = None
        self._order_queue: asyncio.Queue = asyncio.Queue()
        
        # Calculate orders per hour for different time periods
        self._calculate_order_rates()
        
        logger.info(f"📦 Order Generator initialized - Target: {self.config.target_orders_per_day:,} orders/day")
    
    def _calculate_order_rates(self):
        """Calculate order generation rates for different patterns"""
        total_orders = self.config.target_orders_per_day
        
        if self.config.pattern == OrderPattern.STEADY:
            # Constant rate throughout the day
            self.orders_per_hour = total_orders / 24
            self.orders_per_minute = self.orders_per_hour / 60
            
        elif self.config.pattern == OrderPattern.MARKET_HOURS:
            # Concentrate 90% of orders in market hours (6.5 hours)
            market_hours = 6.5
            self.market_orders_per_hour = (total_orders * 0.9) / market_hours
            self.after_hours_orders_per_hour = (total_orders * 0.1) / (24 - market_hours)
            
        elif self.config.pattern == OrderPattern.STRESS:
            # Maximum sustainable load
            self.orders_per_second = total_orders / (24 * 3600)
            
        logger.info(f"📊 Order rates calculated for {self.config.pattern.value} pattern")
    
    def _get_current_order_rate(self, current_time: datetime) -> float:
        """Get order rate for current time based on pattern"""
        
        if self.config.pattern == OrderPattern.STEADY:
            return self.orders_per_minute
        
        elif self.config.pattern == OrderPattern.MARKET_HOURS:
            # Check if in market hours
            hour = current_time.hour
            minute = current_time.minute
            
            market_open = (hour > self.config.market_open_hour or 
                          (hour == self.config.market_open_hour and 
                           minute >= self.config.market_open_minute))
            market_close = (hour < self.config.market_close_hour or 
                           (hour == self.config.market_close_hour and 
                            minute < self.config.market_close_minute))
            
            if market_open and market_close:
                # Peak hours: 10-11 AM and 3-4 PM (higher volume)
                if (10 <= hour < 11) or (15 <= hour < 16):
                    return self.market_orders_per_hour / 60 * 1.5
                else:
                    return self.market_orders_per_hour / 60
            else:
                return self.after_hours_orders_per_hour / 60
        
        elif self.config.pattern == OrderPattern.BURST:
            # Check if in burst window
            minutes_elapsed = current_time.minute % self.config.burst_frequency_minutes
            if minutes_elapsed < (self.config.burst_duration_seconds / 60):
                return self.orders_per_minute * self.config.burst_multiplier
            else:
                return self.orders_per_minute * 0.2  # Quiet period
        
        elif self.config.pattern == OrderPattern.RANDOM:
            # Random rate with variation
            base_rate = self.config.target_orders_per_day / (24 * 60)
            return base_rate * random.uniform(0.5, 2.0)
        
        else:  # STRESS
            return self.orders_per_second * 60
    
    def _generate_order_size(self) -> int:
        """Generate realistic order size using log-normal distribution"""
        # Most orders are small, few are large (realistic trading pattern)
        size = int(np.random.lognormal(
            mean=np.log(self.config.avg_order_size),
            sigma=0.5
        ))
        
        # Clamp to min/max
        size = max(self.config.min_order_size, 
                  min(self.config.max_order_size, size))
        
        # Round to lots of 100
        return (size // 100) * 100
    
    def _select_strategy(self) -> str:
        """Select strategy based on configured weights"""
        strategies = list(self.config.strategy_weights.keys())
        weights = list(self.config.strategy_weights.values())
        return random.choices(strategies, weights=weights)[0]
    
    def _generate_symbol_pair(self) -> Tuple[str, str]:
        """Generate correlated symbol pair for pairs trading"""
        # Common pairs
        pairs = [
            ('AAPL', 'MSFT'), ('JPM', 'BAC'), ('XOM', 'CVX'),
            ('PFE', 'JNJ'), ('V', 'MA'), ('GOOGL', 'META')
        ]
        return random.choice(pairs)
    
    def _generate_single_order(self, strategy: Optional[str] = None) -> GeneratedOrder:
        """Generate a single order"""
        
        if strategy is None:
            strategy = self._select_strategy()
        
        # Generate based on strategy
        if strategy == "pairs_trading":
            # Generate pair order
            symbol1, symbol2 = self._generate_symbol_pair()
            symbol = random.choice([symbol1, symbol2])
        else:
            symbol = random.choice(self.config.symbols)
        
        # Determine side
        if strategy == "momentum":
            # Momentum tends to buy trending stocks
            side = "BUY" if random.random() > 0.4 else "SELL"
        elif strategy == "mean_reversion":
            # Mean reversion is balanced
            side = random.choice(["BUY", "SELL"])
        else:  # pairs_trading
            side = random.choice(["BUY", "SELL"])
        
        # Generate quantity
        quantity = self._generate_order_size()
        
        # Determine order type (70% market, 30% limit)
        if random.random() > 0.3:
            order_type = "MARKET"
            limit_price = None
        else:
            order_type = "LIMIT"
            # Generate realistic limit price (within 0.5% of "market")
            base_price = random.uniform(50, 500)
            limit_price = round(base_price * random.uniform(0.995, 1.005), 2)
        
        # Generate order ID
        order_id = f"LOAD_{self.orders_generated:08d}"
        self.orders_generated += 1
        
        return GeneratedOrder(
            order_id=order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price,
            strategy=strategy,
            timestamp=datetime.now(),
            metadata={
                'pattern': self.config.pattern.value,
                'test_run': True
            }
        )
    
    async def generate_orders(self, duration_seconds: Optional[int] = None) -> List[GeneratedOrder]:
        """
        Generate orders for specified duration
        
        Args:
            duration_seconds: How long to generate orders (None = run indefinitely)
        
        Returns:
            List of generated orders
        """
        self.is_running = True
        orders = []
        start_time = datetime.now()
        
        logger.info(f"🚀 Starting order generation - Pattern: {self.config.pattern.value}")
        
        try:
            while self.is_running:
                current_time = datetime.now()
                
                # Check duration
                if duration_seconds and (current_time - start_time).total_seconds() >= duration_seconds:
                    break
                
                # Get current order rate
                orders_per_minute = self._get_current_order_rate(current_time)
                
                if orders_per_minute > 0:
                    # Calculate interval
                    interval_seconds = 60.0 / orders_per_minute
                    
                    # Add some randomness
                    interval_seconds *= random.uniform(0.8, 1.2)
                    
                    # Generate order
                    order = self._generate_single_order()
                    orders.append(order)
                    
                    # Queue for processing
                    await self._order_queue.put(order)
                    
                    # Log progress
                    if self.orders_generated % 100 == 0:
                        elapsed = (current_time - start_time).total_seconds()
                        rate = self.orders_generated / elapsed if elapsed > 0 else 0
                        logger.info(f"📦 Generated {self.orders_generated:,} orders ({rate:.1f} orders/sec)")
                    
                    # Wait for next order
                    await asyncio.sleep(interval_seconds)
                else:
                    # No orders at this time
                    await asyncio.sleep(1)
        
        except asyncio.CancelledError:
            logger.info("⏹️  Order generation cancelled")
        finally:
            self.is_running = False
        
        return orders
    
    async def get_next_order(self, timeout: float = 1.0) -> Optional[GeneratedOrder]:
        """Get next order from queue"""
        try:
            return await asyncio.wait_for(self._order_queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None
    
    def start_background_generation(self):
        """Start background order generation"""
        if self._generation_task is None or self._generation_task.done():
            self._generation_task = asyncio.create_task(self.generate_orders())
            logger.info("🔄 Background order generation started")
    
    async def stop(self):
        """Stop order generation"""
        self.is_running = False
        if self._generation_task:
            self._generation_task.cancel()
            try:
                await self._generation_task
            except asyncio.CancelledError:
                pass
        logger.info(f"⏹️  Order generation stopped - Total: {self.orders_generated:,} orders")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get generation statistics"""
        return {
            'total_orders_generated': self.orders_generated,
            'is_running': self.is_running,
            'pattern': self.config.pattern.value,
            'target_orders_per_day': self.config.target_orders_per_day,
            'queue_size': self._order_queue.qsize()
        }


# Convenience function for quick testing
async def generate_test_orders(count: int = 100, pattern: OrderPattern = OrderPattern.STEADY) -> List[GeneratedOrder]:
    """Generate a fixed number of test orders quickly"""
    config = OrderGeneratorConfig(
        target_orders_per_day=count * 144,  # Scale to daily rate
        pattern=pattern
    )
    
    generator = OrderGenerator(config)
    
    # Calculate duration to generate 'count' orders at target rate
    duration = count / (config.target_orders_per_day / (24 * 3600))
    
    orders = await generator.generate_orders(duration_seconds=int(duration) + 1)
    await generator.stop()
    
    return orders[:count]  # Return exactly 'count' orders


if __name__ == "__main__":
    # Test the order generator
    logging.basicConfig(level=logging.INFO)
    
    async def test():
        print("Testing Order Generator...")
        print("-" * 50)
        
        # Test 1: Generate 100 orders in steady pattern
        print("\n1. Steady pattern (100 orders)")
        orders = await generate_test_orders(100, OrderPattern.STEADY)
        print(f"   Generated: {len(orders)} orders")
        print(f"   First order: {orders[0].symbol} {orders[0].side} {orders[0].quantity}")
        
        # Test 2: Market hours pattern
        print("\n2. Market hours pattern (50 orders)")
        orders = await generate_test_orders(50, OrderPattern.MARKET_HOURS)
        print(f"   Generated: {len(orders)} orders")
        
        # Test 3: Check strategy distribution
        print("\n3. Strategy distribution")
        strategies = [o.strategy for o in orders]
        for strategy in set(strategies):
            count = strategies.count(strategy)
            print(f"   {strategy}: {count} ({count/len(orders)*100:.1f}%)")
        
        print("\n✅ Order generator tests complete!")
    
    asyncio.run(test())
