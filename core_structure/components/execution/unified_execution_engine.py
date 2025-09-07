#!/usr/bin/env python3
"""
Unified Execution Engine
========================

Professional execution engine that provides consistent execution logic
across backtesting, paper trading, and live trading modes.

Features:
- Single execution path for all trading modes
- Realistic slippage and latency simulation for backtesting
- Advanced order management integration
- Market impact modeling
- Execution cost analysis
- Performance attribution

Author: Pro Quant Desk Trader
"""

import asyncio
import logging
import random
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import uuid

logger = logging.getLogger(__name__)

class ExecutionMode(Enum):
    """Execution mode for different trading environments"""
    BACKTESTING = "BACKTESTING"
    PAPER_TRADING = "PAPER_TRADING"
    LIVE_TRADING = "LIVE_TRADING"

class ExecutionStatus(Enum):
    """Execution status"""
    PENDING = "PENDING"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

@dataclass
class ExecutionRequest:
    """Unified execution request"""
    request_id: str
    strategy_id: str
    symbol: str
    side: str  # 'BUY' or 'SELL'
    quantity: float
    order_type: str  # 'MARKET', 'LIMIT', 'STOP_LOSS', etc.
    price: Optional[float] = None  # For limit orders
    stop_price: Optional[float] = None  # For stop orders
    time_in_force: str = "DAY"
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Risk management
    max_slippage_pct: float = 0.001  # 0.1% max slippage
    urgency: str = "NORMAL"  # NORMAL, HIGH, URGENT
    
    # Metadata
    signal_confidence: float = 1.0
    expected_hold_time: Optional[timedelta] = None

@dataclass
class ExecutionResult:
    """Unified execution result"""
    request_id: str
    execution_id: str
    status: ExecutionStatus
    
    # Execution details
    executed_quantity: float
    executed_price: float
    execution_time: datetime
    
    # Cost analysis
    slippage_bps: float  # Basis points
    commission: float
    market_impact_bps: float
    total_cost_bps: float
    
    # Performance attribution
    expected_price: float
    price_improvement_bps: float
    
    # Metadata
    execution_venue: str = "SIMULATED"
    execution_algorithm: str = "MARKET"
    notes: str = ""

@dataclass
class MarketConditions:
    """Current market conditions for execution modeling"""
    volatility: float = 0.02  # Daily volatility
    bid_ask_spread_bps: float = 5.0  # Bid-ask spread in basis points
    market_impact_factor: float = 1.0  # Market impact multiplier
    liquidity_factor: float = 1.0  # Liquidity availability (0-1)
    
class SlippageModel:
    """Professional slippage modeling for realistic backtesting"""
    
    def __init__(self):
        self.base_slippage_bps = 2.0  # Base slippage in basis points
        self.volatility_multiplier = 0.5  # Volatility impact on slippage
        self.size_impact_factor = 0.1  # Size impact on slippage
        
    def calculate_slippage(self, request: ExecutionRequest, market_conditions: MarketConditions, 
                          market_value: float) -> float:
        """Calculate realistic slippage based on market conditions"""
        
        # Base slippage
        slippage_bps = self.base_slippage_bps
        
        # Volatility impact
        vol_impact = market_conditions.volatility * self.volatility_multiplier * 100
        slippage_bps += vol_impact
        
        # Size impact (larger orders have more slippage)
        order_value = request.quantity * (request.price or 100)  # Approximate value
        size_factor = min(order_value / 100000, 2.0)  # Cap at 2x for very large orders
        slippage_bps += size_factor * self.size_impact_factor * 100
        
        # Urgency impact
        urgency_multiplier = {
            "NORMAL": 1.0,
            "HIGH": 1.5,
            "URGENT": 2.0
        }.get(request.urgency, 1.0)
        slippage_bps *= urgency_multiplier
        
        # Market impact
        slippage_bps *= market_conditions.market_impact_factor
        
        # Liquidity impact
        liquidity_penalty = (1.0 - market_conditions.liquidity_factor) * 5.0
        slippage_bps += liquidity_penalty
        
        # Add random component (market noise)
        noise = random.gauss(0, slippage_bps * 0.2)  # 20% noise
        slippage_bps += noise
        
        # Ensure positive slippage (adverse to trader)
        return max(0.1, slippage_bps)

class LatencySimulator:
    """Simulate realistic execution latencies"""
    
    def __init__(self, mode: ExecutionMode):
        self.mode = mode
        
        # Latency parameters by mode (in milliseconds)
        self.latencies = {
            ExecutionMode.BACKTESTING: {
                "processing": (1, 5),      # 1-5ms processing
                "network": (0, 2),         # 0-2ms network (simulated)
                "venue": (5, 20)           # 5-20ms venue processing
            },
            ExecutionMode.PAPER_TRADING: {
                "processing": (5, 15),     # 5-15ms processing
                "network": (10, 50),       # 10-50ms network
                "venue": (20, 100)         # 20-100ms venue processing
            },
            ExecutionMode.LIVE_TRADING: {
                "processing": (2, 8),      # 2-8ms processing
                "network": (5, 30),        # 5-30ms network
                "venue": (10, 80)          # 10-80ms venue processing
            }
        }
    
    async def add_execution_delay(self, request: ExecutionRequest) -> float:
        """Add realistic execution delay"""
        
        latency_config = self.latencies[self.mode]
        
        # Calculate total latency
        processing_delay = random.uniform(*latency_config["processing"])
        network_delay = random.uniform(*latency_config["network"])
        venue_delay = random.uniform(*latency_config["venue"])
        
        total_delay_ms = processing_delay + network_delay + venue_delay
        
        # Urgency reduces latency
        urgency_factor = {
            "NORMAL": 1.0,
            "HIGH": 0.7,
            "URGENT": 0.4
        }.get(request.urgency, 1.0)
        
        total_delay_ms *= urgency_factor
        
        # Convert to seconds and add delay
        delay_seconds = total_delay_ms / 1000.0
        
        if self.mode == ExecutionMode.BACKTESTING:
            # In backtesting, we don't actually wait, just record the delay
            pass
        else:
            await asyncio.sleep(delay_seconds)
        
        return delay_seconds

class UnifiedExecutionEngine:
    """
    Unified Execution Engine
    
    Provides consistent execution logic across all trading modes:
    - Backtesting: Realistic simulation with slippage and delays
    - Paper Trading: Simulated execution with real-world timing
    - Live Trading: Actual order routing and execution
    
    Key Features:
    - Single execution path for all modes
    - Realistic cost modeling
    - Performance attribution
    - Risk-aware execution
    - Advanced order management integration
    """
    
    def __init__(self, mode: ExecutionMode, initial_capital: float = 100000.0):
        self.mode = mode
        self.initial_capital = initial_capital
        
        # Execution components
        self.slippage_model = SlippageModel()
        self.latency_simulator = LatencySimulator(mode)
        
        # Market conditions (updated in real-time for live trading)
        self.market_conditions = MarketConditions()
        
        # Execution tracking
        self.execution_history: List[ExecutionResult] = []
        self.pending_executions: Dict[str, ExecutionRequest] = {}
        
        # Performance metrics
        self.total_slippage_cost = 0.0
        self.total_commission_cost = 0.0
        self.total_market_impact = 0.0
        self.execution_count = 0
        
        # Market data (for realistic pricing)
        self.current_prices: Dict[str, float] = {}
        self.price_history: Dict[str, List[Tuple[datetime, float]]] = {}
        
        logger.info(f"🎯 Unified Execution Engine initialized - Mode: {mode.value}")
    
    def update_market_conditions(self, conditions: MarketConditions):
        """Update market conditions for execution modeling"""
        self.market_conditions = conditions
        logger.debug(f"Market conditions updated: Vol={conditions.volatility:.3f}, "
                    f"Spread={conditions.bid_ask_spread_bps:.1f}bps")
    
    def update_market_data(self, symbol: str, price: float, timestamp: Optional[datetime] = None):
        """Update market data for execution"""
        if timestamp is None:
            timestamp = datetime.now()
        
        self.current_prices[symbol] = price
        
        # Maintain price history
        if symbol not in self.price_history:
            self.price_history[symbol] = []
        
        self.price_history[symbol].append((timestamp, price))
        
        # Keep only recent history (last 1000 points)
        if len(self.price_history[symbol]) > 1000:
            self.price_history[symbol] = self.price_history[symbol][-1000:]
    
    async def execute_order(self, request: ExecutionRequest) -> ExecutionResult:
        """
        Execute order with unified logic across all modes
        
        This is the single entry point for all order execution,
        ensuring consistent behavior across backtesting and live trading.
        """
        
        try:
            logger.info(f"🎯 Executing order: {request.side} {request.quantity} {request.symbol} "
                       f"({request.order_type}) - Mode: {self.mode.value}")
            
            # Add to pending executions
            self.pending_executions[request.request_id] = request
            
            # Step 1: Pre-execution validation
            validation_result = await self._validate_execution_request(request)
            if not validation_result[0]:
                return self._create_rejected_result(request, validation_result[1])
            
            # Step 2: Add realistic execution delay
            execution_delay = await self.latency_simulator.add_execution_delay(request)
            
            # Step 3: Determine execution price with slippage
            execution_price = await self._calculate_execution_price(request)
            
            # Step 4: Execute based on mode
            if self.mode == ExecutionMode.BACKTESTING:
                result = await self._execute_backtesting_order(request, execution_price, execution_delay)
            elif self.mode == ExecutionMode.PAPER_TRADING:
                result = await self._execute_paper_trading_order(request, execution_price, execution_delay)
            else:  # LIVE_TRADING
                result = await self._execute_live_trading_order(request, execution_price, execution_delay)
            
            # Step 5: Record execution and update metrics
            await self._record_execution(result)
            
            # Remove from pending
            self.pending_executions.pop(request.request_id, None)
            
            logger.info(f"✅ Execution complete: {result.executed_quantity} {request.symbol} @ "
                       f"${result.executed_price:.4f} (Slippage: {result.slippage_bps:.2f}bps)")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Execution failed for {request.request_id}: {e}")
            self.pending_executions.pop(request.request_id, None)
            return self._create_rejected_result(request, f"Execution error: {str(e)}")
    
    async def _validate_execution_request(self, request: ExecutionRequest) -> Tuple[bool, str]:
        """Validate execution request"""
        
        # Check if we have current price data
        if request.symbol not in self.current_prices:
            return False, f"No market data available for {request.symbol}"
        
        # Check quantity
        if request.quantity <= 0:
            return False, f"Invalid quantity: {request.quantity}"
        
        # Check for duplicate request
        if request.request_id in self.pending_executions:
            return False, f"Duplicate request ID: {request.request_id}"
        
        # Mode-specific validations
        if self.mode == ExecutionMode.LIVE_TRADING:
            # Additional validations for live trading
            current_price = self.current_prices[request.symbol]
            order_value = request.quantity * current_price
            
            # Check order size limits
            if order_value > self.initial_capital * 0.2:  # Max 20% of capital per order
                return False, f"Order too large: ${order_value:,.0f} > 20% of capital"
        
        return True, "Valid"
    
    async def _calculate_execution_price(self, request: ExecutionRequest) -> float:
        """Calculate realistic execution price with slippage"""
        
        current_price = self.current_prices[request.symbol]
        
        if self.mode == ExecutionMode.BACKTESTING:
            # Apply realistic slippage model
            market_value = self.initial_capital  # Simplified
            slippage_bps = self.slippage_model.calculate_slippage(
                request, self.market_conditions, market_value
            )
            
            # Apply slippage (adverse to trader)
            slippage_factor = slippage_bps / 10000.0  # Convert bps to decimal
            
            if request.side == "BUY":
                execution_price = current_price * (1 + slippage_factor)
            else:  # SELL
                execution_price = current_price * (1 - slippage_factor)
            
            return execution_price
            
        elif self.mode == ExecutionMode.PAPER_TRADING:
            # Simplified slippage for paper trading
            slippage_bps = 3.0  # Fixed 3bps slippage
            slippage_factor = slippage_bps / 10000.0
            
            if request.side == "BUY":
                return current_price * (1 + slippage_factor)
            else:
                return current_price * (1 - slippage_factor)
                
        else:  # LIVE_TRADING
            # For live trading, price would come from actual execution
            # For now, return current price (would be replaced by broker integration)
            return current_price
    
    async def _execute_backtesting_order(self, request: ExecutionRequest, 
                                       execution_price: float, delay: float) -> ExecutionResult:
        """Execute order in backtesting mode with realistic simulation"""
        
        # Calculate costs
        current_price = self.current_prices[request.symbol]
        slippage_bps = abs(execution_price - current_price) / current_price * 10000
        
        # Commission (simplified model)
        commission = max(1.0, request.quantity * 0.005)  # $0.005 per share, min $1
        
        # Market impact (for large orders)
        order_value = request.quantity * execution_price
        market_impact_bps = min(order_value / 100000 * 2.0, 10.0)  # Max 10bps
        
        # Total cost
        total_cost_bps = slippage_bps + market_impact_bps + (commission / order_value * 10000)
        
        # Price improvement (sometimes we get better prices)
        price_improvement_bps = 0.0
        if random.random() < 0.1:  # 10% chance of price improvement
            price_improvement_bps = random.uniform(0.5, 2.0)
            if request.side == "BUY":
                execution_price *= (1 - price_improvement_bps / 10000)
            else:
                execution_price *= (1 + price_improvement_bps / 10000)
        
        return ExecutionResult(
            request_id=request.request_id,
            execution_id=f"exec_{uuid.uuid4().hex[:8]}",
            status=ExecutionStatus.FILLED,
            executed_quantity=request.quantity,
            executed_price=execution_price,
            execution_time=datetime.now(),
            slippage_bps=slippage_bps,
            commission=commission,
            market_impact_bps=market_impact_bps,
            total_cost_bps=total_cost_bps,
            expected_price=current_price,
            price_improvement_bps=price_improvement_bps,
            execution_venue="BACKTESTING_SIM",
            execution_algorithm="REALISTIC_SIM"
        )
    
    async def _execute_paper_trading_order(self, request: ExecutionRequest,
                                         execution_price: float, delay: float) -> ExecutionResult:
        """Execute order in paper trading mode"""
        
        # Similar to backtesting but with different cost assumptions
        current_price = self.current_prices[request.symbol]
        slippage_bps = abs(execution_price - current_price) / current_price * 10000
        
        # Paper trading commission (broker-specific)
        commission = 0.0  # Many brokers offer commission-free paper trading
        
        # Reduced market impact for paper trading
        market_impact_bps = 1.0  # Fixed 1bp market impact
        
        total_cost_bps = slippage_bps + market_impact_bps
        
        return ExecutionResult(
            request_id=request.request_id,
            execution_id=f"paper_{uuid.uuid4().hex[:8]}",
            status=ExecutionStatus.FILLED,
            executed_quantity=request.quantity,
            executed_price=execution_price,
            execution_time=datetime.now(),
            slippage_bps=slippage_bps,
            commission=commission,
            market_impact_bps=market_impact_bps,
            total_cost_bps=total_cost_bps,
            expected_price=current_price,
            price_improvement_bps=0.0,
            execution_venue="PAPER_TRADING",
            execution_algorithm="SIMULATED"
        )
    
    async def _execute_live_trading_order(self, request: ExecutionRequest,
                                        execution_price: float, delay: float) -> ExecutionResult:
        """Execute order in live trading mode (placeholder for broker integration)"""
        
        # This would integrate with actual broker APIs (IBKR, etc.)
        # For now, return a placeholder result
        
        return ExecutionResult(
            request_id=request.request_id,
            execution_id=f"live_{uuid.uuid4().hex[:8]}",
            status=ExecutionStatus.FILLED,
            executed_quantity=request.quantity,
            executed_price=execution_price,
            execution_time=datetime.now(),
            slippage_bps=2.0,  # Would come from actual execution
            commission=1.0,    # Would come from broker
            market_impact_bps=1.0,
            total_cost_bps=4.0,
            expected_price=self.current_prices[request.symbol],
            price_improvement_bps=0.0,
            execution_venue="LIVE_BROKER",
            execution_algorithm="SMART_ROUTER"
        )
    
    def _create_rejected_result(self, request: ExecutionRequest, reason: str) -> ExecutionResult:
        """Create rejected execution result"""
        
        return ExecutionResult(
            request_id=request.request_id,
            execution_id=f"rejected_{uuid.uuid4().hex[:8]}",
            status=ExecutionStatus.REJECTED,
            executed_quantity=0.0,
            executed_price=0.0,
            execution_time=datetime.now(),
            slippage_bps=0.0,
            commission=0.0,
            market_impact_bps=0.0,
            total_cost_bps=0.0,
            expected_price=self.current_prices.get(request.symbol, 0.0),
            price_improvement_bps=0.0,
            execution_venue="REJECTED",
            execution_algorithm="VALIDATION",
            notes=reason
        )
    
    async def _record_execution(self, result: ExecutionResult):
        """Record execution and update performance metrics"""
        
        self.execution_history.append(result)
        
        if result.status == ExecutionStatus.FILLED:
            self.execution_count += 1
            self.total_slippage_cost += result.slippage_bps
            self.total_commission_cost += result.commission
            self.total_market_impact += result.market_impact_bps
        
        # Keep history manageable
        if len(self.execution_history) > 10000:
            self.execution_history = self.execution_history[-10000:]
    
    def get_execution_statistics(self) -> Dict[str, Any]:
        """Get execution performance statistics"""
        
        if self.execution_count == 0:
            return {"message": "No executions recorded"}
        
        return {
            "total_executions": self.execution_count,
            "average_slippage_bps": self.total_slippage_cost / self.execution_count,
            "total_commission": self.total_commission_cost,
            "average_market_impact_bps": self.total_market_impact / self.execution_count,
            "fill_rate": len([r for r in self.execution_history if r.status == ExecutionStatus.FILLED]) / len(self.execution_history),
            "recent_executions": len([r for r in self.execution_history if r.execution_time > datetime.now() - timedelta(hours=1)])
        }
    
    def get_execution_history(self, hours: int = 24) -> List[ExecutionResult]:
        """Get recent execution history"""
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [result for result in self.execution_history if result.execution_time >= cutoff_time]

# Factory function for easy creation
def create_execution_engine(mode: ExecutionMode, initial_capital: float = 100000.0) -> UnifiedExecutionEngine:
    """Create unified execution engine for specified mode"""
    return UnifiedExecutionEngine(mode, initial_capital)
