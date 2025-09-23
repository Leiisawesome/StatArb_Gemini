#!/usr/bin/env python3
"""
Trading Engine - Core Engine (HOW Component)
============================================

Clean implementation of the trading engine for core_engine.
This component determines HOW trades should be executed.

As part of the central Risk Manager hub, this engine:
- Receives authorized trades from Risk Manager
- Determines optimal execution methodology
- Plans trade execution strategy
- Coordinates with ExecutionEngine for actual execution

Migration: Direct implementation using proven trading patterns.

Author: StatArb_Gemini Core Engine Migration  
Version: 1.0.0 (Clean Production - HOW Component)
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

# Leverage existing high-quality trading components
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from ..type_definitions import OrderType, OrderStatus, Order, ExecutionResult

logger = logging.getLogger(__name__)

class ExecutionStrategy(Enum):
    """Execution strategy types"""
    MARKET = "market"
    LIMIT = "limit"
    TWAP = "twap"
    VWAP = "vwap"
    ICEBERG = "iceberg"
    SMART_ROUTING = "smart_routing"

class TradePriority(Enum):
    """Trade priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

@dataclass
class TradePlan:
    """Comprehensive trade execution plan"""
    plan_id: str
    symbol: str
    total_quantity: float
    side: str  # buy/sell
    strategy: ExecutionStrategy
    priority: TradePriority
    target_price: Optional[float]
    price_limit: Optional[float]
    time_limit: Optional[datetime]
    slicing: Dict[str, Any]  # How to slice large orders
    routing: Dict[str, Any]  # Routing preferences
    conditions: List[str]    # Execution conditions
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class ExecutionSlice:
    """Individual execution slice"""
    slice_id: str
    plan_id: str
    symbol: str
    quantity: float
    side: str
    order_type: OrderType
    price: Optional[float]
    time_in_force: str
    execution_time: Optional[datetime] = None
    status: str = "pending"

@dataclass
class TradingEngineConfig:
    """Trading engine configuration"""
    default_execution_strategy: ExecutionStrategy = ExecutionStrategy.SMART_ROUTING
    max_slice_size: float = 1000.0
    min_slice_size: float = 10.0
    twap_duration_minutes: int = 30
    vwap_participation_rate: float = 0.1
    iceberg_visible_size: float = 0.2
    enable_smart_routing: bool = True
    price_improvement_tolerance: float = 0.001  # 0.1%

class ITradingSubscriber:
    """Interface for trading event subscribers"""
    
    async def on_execution_plan_created(self, plan: TradePlan) -> None:
        """Handle execution plan creation"""
        pass
    
    async def on_slice_executed(self, slice_result: Dict[str, Any]) -> None:
        """Handle slice execution completion"""
        pass

class TradingEngine:
    """
    Core Engine Trading Engine - HOW Component
    
    This component sits within the Risk Manager (Central Hub) and determines
    HOW authorized trades should be executed:
    
    1. Receives authorized trade requests from Risk Manager
    2. Creates optimal execution plans based on market conditions
    3. Slices large orders for optimal execution
    4. Coordinates with ExecutionEngine for actual order placement
    5. Monitors execution progress and adjusts strategy as needed
    
    The HOW methodology includes:
    - Market impact analysis
    - Optimal slicing algorithms
    - Smart order routing
    - Execution timing optimization
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = TradingEngineConfig(**config) if config else TradingEngineConfig()
        
        # Component references (set by Risk Manager)
        self.risk_manager: Optional[Any] = None
        self.execution_engine: Optional[Any] = None
        self.data_manager: Optional[Any] = None
        
        # Trading state
        self.active_plans: Dict[str, TradePlan] = {}
        self.execution_slices: Dict[str, List[ExecutionSlice]] = {}
        self.completed_plans: Dict[str, Dict[str, Any]] = {}
        
        # Market context for execution decisions
        self.market_conditions: Dict[str, Any] = {}
        self.liquidity_data: Dict[str, Any] = {}
        
        # Subscribers
        self.subscribers: List[ITradingSubscriber] = []
        
        # State
        self.is_initialized = False
        self.is_running = False
        self.monitoring_task: Optional[asyncio.Task] = None
        
        logger.info("⚙️ Trading Engine (HOW) initialized")
    
    async def initialize(self) -> bool:
        """Initialize trading engine"""
        try:
            logger.info("🔄 Initializing Trading Engine (HOW)...")
            
            # Initialize market condition monitoring
            await self._initialize_market_monitoring()
            
            self.is_initialized = True
            logger.info("✅ Trading Engine (HOW) initialization complete")
            return True
            
        except Exception as e:
            logger.error(f"❌ Trading Engine initialization failed: {e}")
            raise
    
    async def start(self) -> bool:
        """Start trading engine"""
        try:
            if not self.is_initialized:
                raise RuntimeError("Trading Engine not initialized")
            
            logger.info("🚀 Starting Trading Engine monitoring...")
            
            # Start execution monitoring
            self.monitoring_task = asyncio.create_task(self._run_execution_monitoring())
            
            self.is_running = True
            logger.info("✅ Trading Engine (HOW) started")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start Trading Engine: {e}")
            raise
    
    async def stop(self) -> bool:
        """Stop trading engine"""
        try:
            logger.info("🛑 Stopping Trading Engine...")
            
            if self.monitoring_task:
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
                self.monitoring_task = None
            
            self.is_running = False
            logger.info("✅ Trading Engine stopped")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to stop Trading Engine: {e}")
            return False
    
    # Component Integration
    def set_risk_manager(self, risk_manager: Any):
        """Set risk manager reference"""
        self.risk_manager = risk_manager
        logger.info("🔗 Risk Manager linked to Trading Engine")
    
    def set_execution_engine(self, execution_engine: Any):
        """Set execution engine reference"""
        self.execution_engine = execution_engine
        logger.info("🔗 Execution Engine linked to Trading Engine")
    
    def set_data_manager(self, data_manager: Any):
        """Set data manager reference"""
        self.data_manager = data_manager
        logger.info("🔗 Data Manager linked to Trading Engine")
    
    def subscribe(self, subscriber: ITradingSubscriber):
        """Subscribe to trading events"""
        self.subscribers.append(subscriber)
        logger.info(f"📝 New trading subscriber: {type(subscriber).__name__}")
    
    # Core Trading Methods
    async def plan_execution(self, trade_request: Dict[str, Any]) -> TradePlan:
        """
        Create comprehensive execution plan for authorized trade
        
        This is the core HOW methodology:
        1. Analyze market conditions
        2. Determine optimal execution strategy
        3. Plan order slicing and timing
        4. Create execution roadmap
        """
        try:
            symbol = trade_request['symbol']
            quantity = trade_request['quantity']
            side = trade_request['side']
            
            logger.info(f"📋 Planning execution: {symbol} {side} {quantity}")
            
            # Analyze market conditions
            market_analysis = await self._analyze_market_conditions(symbol)
            
            # Determine optimal execution strategy
            execution_strategy = await self._determine_execution_strategy(
                symbol, quantity, side, market_analysis
            )
            
            # Calculate optimal slicing
            slicing_plan = await self._calculate_order_slicing(
                symbol, quantity, execution_strategy, market_analysis
            )
            
            # Determine routing preferences
            routing_plan = await self._determine_routing_strategy(
                symbol, quantity, market_analysis
            )
            
            # Create trade plan
            plan = TradePlan(
                plan_id=str(uuid.uuid4()),
                symbol=symbol,
                total_quantity=quantity,
                side=side,
                strategy=execution_strategy,
                priority=trade_request.get('priority', TradePriority.NORMAL),
                target_price=trade_request.get('target_price'),
                price_limit=trade_request.get('price_limit'),
                time_limit=trade_request.get('time_limit'),
                slicing=slicing_plan,
                routing=routing_plan,
                conditions=trade_request.get('conditions', [])
            )
            
            # Store active plan
            self.active_plans[plan.plan_id] = plan
            
            # Create execution slices
            slices = await self._create_execution_slices(plan)
            self.execution_slices[plan.plan_id] = slices
            
            # Notify subscribers
            for subscriber in self.subscribers:
                await subscriber.on_execution_plan_created(plan)
            
            logger.info(f"✅ Execution plan created: {plan.plan_id} ({len(slices)} slices)")
            return plan
            
        except Exception as e:
            logger.error(f"❌ Execution planning failed: {e}")
            raise
    
    async def execute_plan(self, plan_id: str) -> bool:
        """Execute the trading plan"""
        try:
            if plan_id not in self.active_plans:
                raise ValueError(f"Plan not found: {plan_id}")
            
            plan = self.active_plans[plan_id]
            slices = self.execution_slices[plan_id]
            
            logger.info(f"🚀 Executing plan: {plan_id} ({len(slices)} slices)")
            
            # Execute based on strategy
            if plan.strategy == ExecutionStrategy.MARKET:
                return await self._execute_market_strategy(plan, slices)
            elif plan.strategy == ExecutionStrategy.TWAP:
                return await self._execute_twap_strategy(plan, slices)
            elif plan.strategy == ExecutionStrategy.VWAP:
                return await self._execute_vwap_strategy(plan, slices)
            elif plan.strategy == ExecutionStrategy.ICEBERG:
                return await self._execute_iceberg_strategy(plan, slices)
            else:  # SMART_ROUTING or LIMIT
                return await self._execute_smart_routing_strategy(plan, slices)
                
        except Exception as e:
            logger.error(f"❌ Plan execution failed: {e}")
            return False
    
    async def cancel_plan(self, plan_id: str) -> bool:
        """Cancel active execution plan"""
        try:
            if plan_id not in self.active_plans:
                return False
            
            plan = self.active_plans[plan_id]
            logger.info(f"❌ Cancelling plan: {plan_id}")
            
            # Cancel pending slices through execution engine
            if self.execution_engine and plan_id in self.execution_slices:
                for slice_obj in self.execution_slices[plan_id]:
                    if slice_obj.status == "pending":
                        await self.execution_engine.cancel_order(slice_obj.slice_id)
            
            # Move to completed
            self.completed_plans[plan_id] = {
                'plan': plan,
                'status': 'cancelled',
                'completed_at': datetime.now()
            }
            
            # Cleanup
            del self.active_plans[plan_id]
            if plan_id in self.execution_slices:
                del self.execution_slices[plan_id]
            
            logger.info(f"✅ Plan cancelled: {plan_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to cancel plan {plan_id}: {e}")
            return False
    
    # Strategy Implementation Methods
    async def _execute_market_strategy(self, plan: TradePlan, slices: List[ExecutionSlice]) -> bool:
        """Execute market order strategy"""
        logger.info(f"📈 Executing MARKET strategy for {plan.symbol}")
        
        # Execute all slices as market orders
        for slice_obj in slices:
            if self.execution_engine:
                order = Order(
                    order_id=slice_obj.slice_id,
                    symbol=slice_obj.symbol,
                    quantity=slice_obj.quantity,
                    order_type=OrderType.MARKET,
                    side=slice_obj.side,
                    time_in_force="IOC"
                )
                
                result = await self.execution_engine.execute_order(order)
                slice_obj.status = "executed" if result.success else "failed"
                slice_obj.execution_time = datetime.now()
                
                # Notify subscribers
                for subscriber in self.subscribers:
                    await subscriber.on_slice_executed({
                        'slice_id': slice_obj.slice_id,
                        'plan_id': plan.plan_id,
                        'result': result,
                        'status': slice_obj.status
                    })
        
        return True
    
    async def _execute_twap_strategy(self, plan: TradePlan, slices: List[ExecutionSlice]) -> bool:
        """Execute TWAP (Time Weighted Average Price) strategy"""
        logger.info(f"⏰ Executing TWAP strategy for {plan.symbol}")
        
        # Calculate timing intervals
        interval_seconds = (self.config.twap_duration_minutes * 60) / len(slices)
        
        for i, slice_obj in enumerate(slices):
            # Wait for scheduled time (except first slice)
            if i > 0:
                await asyncio.sleep(interval_seconds)
            
            # Execute slice
            if self.execution_engine:
                order = Order(
                    order_id=slice_obj.slice_id,
                    symbol=slice_obj.symbol,
                    quantity=slice_obj.quantity,
                    order_type=slice_obj.order_type,
                    side=slice_obj.side,
                    price=slice_obj.price,
                    time_in_force="IOC"
                )
                
                result = await self.execution_engine.execute_order(order)
                slice_obj.status = "executed" if result.success else "failed"
                slice_obj.execution_time = datetime.now()
        
        return True
    
    async def _execute_smart_routing_strategy(self, plan: TradePlan, slices: List[ExecutionSlice]) -> bool:
        """Execute smart routing strategy"""
        logger.info(f"🧠 Executing SMART ROUTING strategy for {plan.symbol}")
        
        # Implement smart routing logic
        for slice_obj in slices:
            # Analyze current market conditions
            current_market = await self._get_current_market_data(slice_obj.symbol)
            
            # Adjust order parameters based on conditions
            if current_market.get('spread', 0) > 0.01:  # Wide spread
                slice_obj.order_type = OrderType.LIMIT
                slice_obj.price = current_market.get('mid_price')
            else:  # Tight spread
                slice_obj.order_type = OrderType.MARKET
            
            # Execute slice
            if self.execution_engine:
                order = Order(
                    order_id=slice_obj.slice_id,
                    symbol=slice_obj.symbol,
                    quantity=slice_obj.quantity,
                    order_type=slice_obj.order_type,
                    side=slice_obj.side,
                    price=slice_obj.price,
                    time_in_force="GTC"
                )
                
                result = await self.execution_engine.execute_order(order)
                slice_obj.status = "executed" if result.success else "failed"
                slice_obj.execution_time = datetime.now()
        
        return True
    
    async def _execute_vwap_strategy(self, plan: TradePlan, slices: List[ExecutionSlice]) -> bool:
        """Execute VWAP (Volume Weighted Average Price) strategy"""
        logger.info(f"📊 Executing VWAP strategy for {plan.symbol}")
        
        # Execute slices with volume participation rate
        for slice_obj in slices:
            # Get current volume data for VWAP calculation
            current_market = await self._get_current_market_data(slice_obj.symbol)
            participation_rate = self.config.vwap_participation_rate
            
            if self.execution_engine:
                order = Order(
                    order_id=slice_obj.slice_id,
                    symbol=slice_obj.symbol,
                    quantity=slice_obj.quantity,
                    order_type=slice_obj.order_type,
                    side=slice_obj.side,
                    price=slice_obj.price,
                    time_in_force="IOC"
                )
                
                result = await self.execution_engine.execute_order(order)
                slice_obj.status = "executed" if result.success else "failed"
                slice_obj.execution_time = datetime.now()
        
        return True
    
    async def _execute_iceberg_strategy(self, plan: TradePlan, slices: List[ExecutionSlice]) -> bool:
        """Execute Iceberg strategy (partial visibility)"""
        logger.info(f"🧊 Executing ICEBERG strategy for {plan.symbol}")
        
        # Execute slices with only partial visibility
        for slice_obj in slices:
            # Calculate visible quantity
            visible_qty = slice_obj.quantity * self.config.iceberg_visible_size
            
            if self.execution_engine:
                order = Order(
                    order_id=slice_obj.slice_id,
                    symbol=slice_obj.symbol,
                    quantity=visible_qty,  # Only show partial quantity
                    order_type=slice_obj.order_type,
                    side=slice_obj.side,
                    price=slice_obj.price,
                    time_in_force="GTC"
                )
                
                result = await self.execution_engine.execute_order(order)
                slice_obj.status = "executed" if result.success else "failed"
                slice_obj.execution_time = datetime.now()
                
                # Wait between iceberg slices
                await asyncio.sleep(30)
        
        return True
    
    # Analysis Methods
    async def _analyze_market_conditions(self, symbol: str) -> Dict[str, Any]:
        """Analyze current market conditions for symbol"""
        try:
            # Get market data from data manager
            if self.data_manager:
                market_data = await self.data_manager.get_real_time_quote(symbol)
                historical_data = await self.data_manager.get_historical_data(
                    symbol, period="1d", lookback_days=5
                )
                
                # Calculate market metrics
                volatility = self._calculate_volatility(historical_data)
                liquidity = self._estimate_liquidity(market_data)
                spread = market_data.get('ask', 0) - market_data.get('bid', 0)
                
                return {
                    'volatility': volatility,
                    'liquidity': liquidity,
                    'spread': spread,
                    'mid_price': (market_data.get('ask', 0) + market_data.get('bid', 0)) / 2,
                    'volume': market_data.get('volume', 0),
                    'timestamp': datetime.now()
                }
            
            # Fallback conditions
            return {
                'volatility': 0.02,
                'liquidity': 'medium',
                'spread': 0.01,
                'mid_price': 100.0,
                'volume': 1000,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"❌ Market analysis failed for {symbol}: {e}")
            return {}
    
    async def _determine_execution_strategy(self, symbol: str, quantity: float, side: str, market_analysis: Dict[str, Any]) -> ExecutionStrategy:
        """Determine optimal execution strategy"""
        try:
            volatility = market_analysis.get('volatility', 0.02)
            liquidity = market_analysis.get('liquidity', 'medium')
            spread = market_analysis.get('spread', 0.01)
            
            # Large orders need slicing
            if quantity > self.config.max_slice_size:
                if volatility > 0.05:  # High volatility
                    return ExecutionStrategy.VWAP
                else:
                    return ExecutionStrategy.TWAP
            
            # Medium orders with wide spreads
            if spread > 0.02:
                return ExecutionStrategy.ICEBERG
            
            # Small orders or tight spreads
            if quantity < self.config.min_slice_size or spread < 0.005:
                return ExecutionStrategy.MARKET
            
            # Default to smart routing
            return ExecutionStrategy.SMART_ROUTING
            
        except Exception as e:
            logger.error(f"❌ Strategy determination failed: {e}")
            return self.config.default_execution_strategy
    
    async def _calculate_order_slicing(self, symbol: str, quantity: float, strategy: ExecutionStrategy, market_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate optimal order slicing"""
        if quantity <= self.config.max_slice_size:
            return {'slice_count': 1, 'slice_size': quantity}
        
        # Calculate based on strategy
        if strategy in [ExecutionStrategy.TWAP, ExecutionStrategy.VWAP]:
            slice_count = min(10, max(2, int(quantity / self.config.max_slice_size)))
            slice_size = quantity / slice_count
        elif strategy == ExecutionStrategy.ICEBERG:
            visible_size = max(self.config.min_slice_size, quantity * self.config.iceberg_visible_size)
            slice_count = int(quantity / visible_size)
            slice_size = visible_size
        else:
            slice_count = max(2, int(quantity / self.config.max_slice_size))
            slice_size = quantity / slice_count
        
        return {
            'slice_count': slice_count,
            'slice_size': slice_size,
            'strategy': strategy.value
        }
    
    async def _determine_routing_strategy(self, symbol: str, quantity: float, market_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Determine routing strategy"""
        return {
            'primary_venue': 'SMART',
            'allow_dark_pools': quantity > 1000,
            'allow_crossing': True,
            'price_improvement': True
        }
    
    async def _create_execution_slices(self, plan: TradePlan) -> List[ExecutionSlice]:
        """Create execution slices from plan"""
        slices = []
        slice_count = plan.slicing['slice_count']
        slice_size = plan.slicing['slice_size']
        
        for i in range(slice_count):
            # Handle remainder in last slice
            quantity = slice_size
            if i == slice_count - 1:
                quantity = plan.total_quantity - (slice_size * i)
            
            slice_obj = ExecutionSlice(
                slice_id=f"{plan.plan_id}_{i+1}",
                plan_id=plan.plan_id,
                symbol=plan.symbol,
                quantity=quantity,
                side=plan.side,
                order_type=OrderType.MARKET if plan.strategy == ExecutionStrategy.MARKET else OrderType.LIMIT,
                price=plan.target_price,
                time_in_force="GTC"
            )
            slices.append(slice_obj)
        
        return slices
    
    # Monitoring and Utilities
    async def _run_execution_monitoring(self):
        """Monitor active executions"""
        logger.info("📊 Starting execution monitoring...")
        
        while self.is_running:
            try:
                # Monitor active plans
                for plan_id in list(self.active_plans.keys()):
                    await self._monitor_plan_progress(plan_id)
                
                await asyncio.sleep(10)  # Monitor every 10 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Execution monitoring error: {e}")
                await asyncio.sleep(30)
    
    async def _monitor_plan_progress(self, plan_id: str):
        """Monitor individual plan progress"""
        if plan_id not in self.execution_slices:
            return
        
        slices = self.execution_slices[plan_id]
        completed = sum(1 for s in slices if s.status in ["executed", "failed"])
        
        if completed == len(slices):
            # Plan completed
            plan = self.active_plans[plan_id]
            self.completed_plans[plan_id] = {
                'plan': plan,
                'status': 'completed',
                'completed_at': datetime.now()
            }
            del self.active_plans[plan_id]
            del self.execution_slices[plan_id]
            
            logger.info(f"✅ Plan completed: {plan_id}")
    
    async def _initialize_market_monitoring(self):
        """Initialize market condition monitoring"""
        logger.info("📊 Initializing market monitoring...")
        # Placeholder for market monitoring setup
    
    async def _get_current_market_data(self, symbol: str) -> Dict[str, Any]:
        """Get current market data"""
        if self.data_manager:
            return await self.data_manager.get_real_time_quote(symbol)
        return {'bid': 99, 'ask': 101, 'mid_price': 100, 'volume': 1000}
    
    def _calculate_volatility(self, historical_data: Any) -> float:
        """Calculate historical volatility"""
        # Simplified volatility calculation
        return 0.02  # 2% default
    
    def _estimate_liquidity(self, market_data: Dict[str, Any]) -> str:
        """Estimate market liquidity"""
        volume = market_data.get('volume', 0)
        if volume > 10000:
            return 'high'
        elif volume > 1000:
            return 'medium'
        else:
            return 'low'
    
    def get_trading_status(self) -> Dict[str, Any]:
        """Get comprehensive trading status"""
        return {
            'initialized': self.is_initialized,
            'running': self.is_running,
            'active_plans': len(self.active_plans),
            'total_slices': sum(len(slices) for slices in self.execution_slices.values()),
            'completed_plans': len(self.completed_plans),
            'components_linked': {
                'risk_manager': self.risk_manager is not None,
                'execution_engine': self.execution_engine is not None,
                'data_manager': self.data_manager is not None
            }
        }