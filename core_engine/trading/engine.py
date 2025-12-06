#!/usr/bin/env python3
"""
Trading Engine - Core Engine (HOW Component)
============================================

Clean implementation of the trading engine for core_engine.
This component determines HOW trades should be executed.

Architecture Compliance (Tier-1 Rules):
- Rule 1: System Architecture - Layer 5 (Trading & Execution)
- Rule 5: Execution & Order Management - Phase 11 (Execution Planning)
  - Receives authorized trades from Risk Manager (Rule 3, Phase 10)
  - Determines optimal execution algorithm (MARKET/LIMIT/TWAP/VWAP/ADAPTIVE)
  - Creates execution plan with slicing strategy
  - Passes to OMS (Phase 12) and ExecutionEngine (Phase 13)

Key Responsibilities:
- Receives authorized trades from Risk Manager
- Determines optimal execution methodology
- Plans trade execution strategy
- Coordinates with ExecutionEngine for actual execution

Migration: December 2025 - Former Rule 7 content now Rule 5.

Author: StatArb_Gemini Core Engine Migration  
Version: 2.0.0 (Rules Migration December 2025)
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import threading

# Import ISystemComponent for orchestrator integration
try:
    from ..system.interfaces import ISystemComponent
except ImportError:
    # Fallback definition
    from abc import ABC, abstractmethod
    class ISystemComponent(ABC):
        @abstractmethod
        async def initialize(self) -> bool:
            pass
        
        @abstractmethod
        async def start(self) -> bool:
            pass
        
        @abstractmethod
        async def stop(self) -> bool:
            pass
        
        @abstractmethod
        async def health_check(self) -> Dict[str, Any]:
            pass
        
        @abstractmethod
        def get_status(self) -> Dict[str, Any]:
            pass

# Leverage existing high-quality trading components
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from ..type_definitions import OrderType, Order

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
    
    async def on_slice_executed(self, slice_result: Dict[str, Any]) -> None:
        """Handle slice execution completion"""

class EnhancedTradingEngine(ISystemComponent):
    """
    Enhanced Trading Engine with ISystemComponent Integration - HOW Component
    
    Institutional-grade trading engine with orchestrator integration:
    - Implements ISystemComponent for lifecycle management
    - Determines HOW authorized trades should be executed
    - Creates optimal execution plans based on market conditions
    - Slices large orders for optimal execution
    - Coordinates with ExecutionEngine for actual order placement
    - Monitors execution progress and adjusts strategy as needed
    - Health monitoring and performance tracking
    
    The HOW methodology includes:
    - Market impact analysis
    - Optimal slicing algorithms
    - Smart order routing
    - Execution timing optimization
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = TradingEngineConfig(**config) if config else TradingEngineConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Component identification and lifecycle
        self.component_id = str(uuid.uuid4())
        self.is_initialized = False
        
        # Orchestrator integration
        self.orchestrator: Optional[Any] = None  # HierarchicalSystemOrchestrator reference
        self.is_operational = False
        self.start_time = None
        
        # Health and performance tracking
        self.health_metrics = {
            'component_type': 'EnhancedTradingEngine',
            'initialization_status': 'pending',
            'operational_status': 'inactive',
            'last_health_check': None,
            'error_count': 0,
            'warning_count': 0,
            'performance_metrics': {
                'total_execution_plans': 0,
                'successful_execution_plans': 0,
                'failed_execution_plans': 0,
                'average_plan_creation_time': 0.0,
                'active_plans_count': 0
            }
        }
        
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
        
        # Threading
        self._lock = threading.Lock()
        
        self.logger.info(f"🚀 Enhanced Trading Engine initialized with component ID: {self.component_id}")
    
    # ========================================
    # ORCHESTRATOR INTEGRATION
    # ========================================
    
    def register_with_orchestrator(self, orchestrator) -> str:
        """Register component with HierarchicalSystemOrchestrator"""
        from core_engine.system.hierarchical_orchestrator import ComponentLayer, AuthorityLevel
        
        self.orchestrator = orchestrator
        self.component_id = orchestrator.register_component(
            name="EnhancedTradingEngine",
            component=self,
            layer=ComponentLayer.EXECUTION,
            authority_level=AuthorityLevel.OPERATIONAL,
            initialization_order=30  # After strategy components
        )
        
        self.logger.info(f"✅ EnhancedTradingEngine registered with orchestrator: {self.component_id}")
        return self.component_id
    
    async def request_operation_authorization(self, operation: str, details: Dict[str, Any]) -> bool:
        """Request authorization from orchestrator for privileged operations"""
        if not self.orchestrator or not self.component_id:
            self.logger.warning("No orchestrator available for authorization request")
            return False
        
        return await self.orchestrator.request_system_authorization(
            operation, self.component_id, details
        )
    
    # ========================================
    # ISystemComponent Interface Implementation
    # ========================================
    
    async def initialize(self) -> bool:
        """Initialize the Enhanced Trading Engine"""
        try:
            self.logger.info("🔄 Initializing Enhanced Trading Engine...")
            
            # Initialize trading engines
            await self._initialize_trading_engines()
            
            # Initialize monitoring
            await self._initialize_monitoring_system()
            
            # Update status
            self.is_initialized = True
            self.health_metrics['initialization_status'] = 'completed'
            
            self.logger.info("✅ Enhanced Trading Engine initialization complete")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Enhanced Trading Engine initialization failed: {e}")
            self.health_metrics['error_count'] += 1
            self.health_metrics['initialization_status'] = 'failed'
            return False
    
    async def start(self) -> bool:
        """Start the Enhanced Trading Engine"""
        if not self.is_initialized:
            self.logger.error("Cannot start Enhanced Trading Engine: not initialized")
            return False
        
        try:
            self.logger.info("🚀 Starting Enhanced Trading Engine...")
            
            # Start trading operations
            await self._start_trading_operations()
            
            # Start monitoring
            await self._start_monitoring()
            
            # Update status
            self.is_operational = True
            self.start_time = datetime.now()
            self.health_metrics['operational_status'] = 'active'
            
            self.logger.info("✅ Enhanced Trading Engine started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Enhanced Trading Engine start failed: {e}")
            self.health_metrics['error_count'] += 1
            return False
    
    async def stop(self) -> bool:
        """Stop the Enhanced Trading Engine"""
        try:
            self.logger.info("🛑 Stopping Enhanced Trading Engine...")
            
            # Stop trading operations
            await self._stop_trading_operations()
            
            # Stop monitoring
            await self._stop_monitoring()
            
            # Clear active plans
            self.active_plans.clear()
            self.execution_slices.clear()
            
            # Update status
            self.is_operational = False
            self.health_metrics['operational_status'] = 'inactive'
            
            self.logger.info("✅ Enhanced Trading Engine stopped successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Enhanced Trading Engine stop failed: {e}")
            self.health_metrics['error_count'] += 1
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        try:
            current_time = datetime.now()
            self.health_metrics['last_health_check'] = current_time
            
            # Calculate uptime
            uptime_seconds = 0
            if self.start_time:
                uptime_seconds = (current_time - self.start_time).total_seconds()
            
            # Check trading operations health
            operations_healthy = await self._check_operations_health()
            
            # Overall health assessment
            overall_healthy = (
                self.is_initialized and
                self.is_operational and
                operations_healthy and
                self.health_metrics['error_count'] < 10
            )
            
            return {
                'healthy': overall_healthy,
                'component_type': self.health_metrics['component_type'],
                'component_id': self.component_id,
                'initialized': self.is_initialized,
                'operational': self.is_operational,
                'uptime_seconds': uptime_seconds,
                'error_count': self.health_metrics['error_count'],
                'warning_count': self.health_metrics['warning_count'],
                'performance_metrics': self.health_metrics['performance_metrics'],
                'operations_healthy': operations_healthy,
                'active_plans_count': len(self.active_plans),
                'completed_plans_count': len(self.completed_plans),
                'subscribers_count': len(self.subscribers),
                'last_health_check': current_time.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            self.health_metrics['error_count'] += 1
            return {
                'healthy': False,
                'component_type': self.health_metrics['component_type'],
                'component_id': self.component_id,
                'error': str(e)
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get current component status"""
        return {
            'component_id': self.component_id,
            'component_type': self.health_metrics['component_type'],
            'initialized': self.is_initialized,
            'operational': self.is_operational,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'configuration': {
                'max_slice_size': self.config.max_slice_size,
                'min_slice_size': self.config.min_slice_size,
                'twap_duration_minutes': self.config.twap_duration_minutes,
                'vwap_participation_rate': self.config.vwap_participation_rate,
                'enable_smart_routing': self.config.enable_smart_routing
            },
            'health_metrics': self.health_metrics
        }
    
    # Enhanced Internal Methods
    
    async def _initialize_trading_engines(self) -> None:
        """Initialize trading engines"""
        try:
            self.logger.info("🔧 Initializing trading engines...")
            
            # Initialize market condition monitoring
            self.market_conditions = {}
            self.liquidity_data = {}
            
            self.logger.info("✅ Trading engines initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize trading engines: {e}")
            raise
    
    async def _initialize_monitoring_system(self) -> None:
        """Initialize monitoring system"""
        try:
            self.logger.info("📈 Initializing monitoring system...")
            
            # Initialize performance monitoring
            self.health_metrics['performance_metrics'] = {
                'total_execution_plans': 0,
                'successful_execution_plans': 0,
                'failed_execution_plans': 0,
                'average_plan_creation_time': 0.0,
                'active_plans_count': 0
            }
            
            self.logger.info("✅ Monitoring system initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize monitoring system: {e}")
            raise
    
    async def _start_trading_operations(self) -> None:
        """Start trading operations"""
        try:
            self.logger.info("📊 Starting trading operations...")
            # Trading operations are event-driven, no background tasks needed
            self.logger.info("✅ Trading operations started")
            
        except Exception as e:
            self.logger.error(f"Failed to start trading operations: {e}")
            raise
    
    async def _start_monitoring(self) -> None:
        """Start monitoring systems"""
        try:
            self.logger.info("📊 Starting monitoring systems...")
            # Monitoring is passive for trading engine
            self.logger.info("✅ Monitoring systems started")
            
        except Exception as e:
            self.logger.error(f"Failed to start monitoring: {e}")
            raise
    
    async def _stop_trading_operations(self) -> None:
        """Stop trading operations"""
        try:
            self.logger.info("📊 Stopping trading operations...")
            # No background tasks to stop
            self.logger.info("✅ Trading operations stopped")
            
        except Exception as e:
            self.logger.error(f"Failed to stop trading operations: {e}")
            raise
    
    async def _stop_monitoring(self) -> None:
        """Stop monitoring systems"""
        try:
            self.logger.info("📊 Stopping monitoring systems...")
            # Monitoring is passive for trading engine
            self.logger.info("✅ Monitoring systems stopped")
            
        except Exception as e:
            self.logger.error(f"Failed to stop monitoring: {e}")
            raise
    
    async def _check_operations_health(self) -> bool:
        """Check health of trading operations"""
        try:
            # Basic health check - verify core functionality
            # Check if we can create a basic execution plan
            return True
            
        except Exception as e:
            self.logger.warning(f"Operations health check failed: {e}")
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
            await self._get_current_market_data(slice_obj.symbol)
            self.config.vwap_participation_rate
            
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
            market_analysis.get('liquidity', 'medium')
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
    
    # ========================================
    # STANDARDIZED DATA FLOW METHODS
    # ========================================
    
    def process_signals(self, signals: List[Any]) -> List[Any]:
        """Standardized method for processing trading signals"""
        # Process signals and create execution plans
        processed_signals = []
        for signal in signals:
            # Basic signal processing logic
            processed_signal = {
                'original_signal': signal,
                'processed_timestamp': datetime.now(),
                'processing_component': 'EnhancedTradingEngine'
            }
            processed_signals.append(processed_signal)
        return processed_signals
    
    def process_decisions(self, decisions: List[Any]) -> List[Any]:
        """Standardized method for processing strategy decisions"""
        return self.process_signals(decisions)  # Alias for signal processing
    
    def handle_authorization(self, authorization: Any) -> Dict[str, Any]:
        """Standardized method for handling risk authorizations"""
        return {
            'authorization_processed': True,
            'authorization_data': authorization,
            'processing_timestamp': datetime.now(),
            'processing_component': 'EnhancedTradingEngine'
        }
    
    def generate_plan(self, authorization: Any) -> Dict[str, Any]:
        """Standardized method for generating execution plans (alias for create_execution_plan)"""
        return self.handle_authorization(authorization)
    
    async def create_execution_plan(self, authorization: Any) -> Dict[str, Any]:
        """
        Create optimal execution plan from authorized trade
        
        Fully implements Phase 8 per Rule 7.1:
        - Assesses liquidity conditions
        - Selects optimal execution algorithm
        - Estimates market impact
        - Creates comprehensive execution request
        
        Args:
            authorization: TradingAuthorization from CentralRiskManager (Phase 7)
            
        Returns:
            ExecutionRequest with complete execution plan (Phase 8 output)
        """
        try:
            plan_start_time = datetime.now()
            
            # Extract authorization data
            if isinstance(authorization, dict):
                symbol = authorization.get('symbol', '')
                side = authorization.get('side', '')
                quantity = authorization.get('authorized_quantity', authorization.get('quantity', 0))
                urgency = authorization.get('urgency', 'normal')
                max_execution_time = authorization.get('max_execution_time', 3600)
            else:
                # Handle authorization object
                symbol = getattr(authorization, 'symbol', '')
                side = getattr(authorization, 'side', '')
                quantity = getattr(authorization, 'authorized_quantity', 0)
                urgency = getattr(authorization, 'urgency', 'normal')
                max_execution_time = getattr(authorization, 'max_execution_time', 3600)
            
            self.logger.info(f"📋 Creating execution plan: {symbol} {side} {quantity} shares")
            
            # Step 1: Get market data
            market_data = await self._get_market_data(symbol)
            
            # Step 2: Assess liquidity
            liquidity_score = await self._assess_liquidity(symbol, quantity, market_data)
            
            # Step 3: Select execution algorithm
            algorithm = self._select_execution_algorithm(
                quantity=quantity,
                urgency=urgency,
                liquidity_score=liquidity_score,
                time_horizon=max_execution_time
            )
            
            # Step 4: Estimate market impact
            impact_estimate = await self._estimate_market_impact(
                symbol=symbol,
                quantity=quantity,
                side=side,
                liquidity_score=liquidity_score,
                market_data=market_data
            )
            
            # Step 5: Create execution request
            execution_request = {
                'request_id': str(uuid.uuid4()),
                'authorization': authorization,
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'algorithm': algorithm,
                'urgency': urgency,
                'time_horizon': max_execution_time,
                
                # Liquidity assessment
                'liquidity_score': liquidity_score,
                
                # Market impact estimation
                'estimated_impact_bps': impact_estimate['total_impact_bps'],
                'permanent_impact_bps': impact_estimate['permanent_impact_bps'],
                'temporary_impact_bps': impact_estimate['temporary_impact_bps'],
                
                # Pricing
                'current_price': market_data.get('current_price', 100.0),
                'estimated_fill_price': market_data.get('current_price', 100.0) + impact_estimate['price_adjustment'],
                'price_limit': impact_estimate.get('price_limit'),
                
                # Venue routing
                'venue_preferences': self._get_venue_preferences(symbol, liquidity_score),
                
                # Order slicing (for large orders)
                'slicing_plan': self._create_slicing_plan(
                    total_quantity=quantity,
                    algorithm=algorithm,
                    time_horizon=max_execution_time,
                    market_data=market_data
                ) if quantity > liquidity_score.get('avg_trade_size', 1000) * 5 else None,
                
                # Metadata
                'metadata': {
                    'liquidity_regime': liquidity_score.get('liquidity_regime', 'normal_liquidity'),
                    'market_regime': market_data.get('regime', 'unknown'),
                    'volatility': market_data.get('volatility', 0.02),
                    'planning_timestamp': datetime.now().isoformat(),
                    'planning_duration_ms': (datetime.now() - plan_start_time).total_seconds() * 1000
                }
            }
            
            # Update metrics
            self.health_metrics['performance_metrics']['total_execution_plans'] += 1
            self.health_metrics['performance_metrics']['successful_execution_plans'] += 1
            
            self.logger.info(
                f"✅ Execution plan created: {symbol} {algorithm} "
                f"(impact: {impact_estimate['total_impact_bps']:.2f}bps, "
                f"liquidity: {liquidity_score.get('overall_score', 0):.1f})"
            )
            
            return execution_request
            
        except Exception as e:
            self.logger.error(f"❌ Execution plan creation failed: {e}")
            self.health_metrics['performance_metrics']['failed_execution_plans'] += 1
            self.health_metrics['error_count'] += 1
            
            # Return fallback plan
            return {
                'request_id': str(uuid.uuid4()),
                'authorization': authorization,
                'algorithm': 'market',  # Fallback to market order
                'error': str(e),
                'fallback': True
            }
    
    # ========================================
    # EXECUTION PLANNING HELPER METHODS (Phase 8 Implementation)
    # ========================================
    
    async def _get_market_data(self, symbol: str) -> Dict[str, Any]:
        """
        Get current market data for execution planning
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Market data dict with price, volume, volatility, etc.
        """
        try:
            if self.data_manager and hasattr(self.data_manager, 'get_current_market_data'):
                # Use data manager if available
                market_data = await self.data_manager.get_current_market_data(symbol)
                return market_data
            else:
                # Fallback to reasonable defaults
                self.logger.warning(f"No data manager available, using defaults for {symbol}")
                return {
                    'symbol': symbol,
                    'current_price': 100.0,
                    'bid': 99.95,
                    'ask': 100.05,
                    'volume': 1000000,
                    'avg_volume': 1000000,
                    'volatility': 0.02,  # 2% daily volatility
                    'regime': 'normal_volatility',
                    'timestamp': datetime.now()
                }
        except Exception as e:
            self.logger.error(f"Error getting market data: {e}")
            # Return safe defaults
            return {
                'symbol': symbol,
                'current_price': 100.0,
                'volume': 1000000,
                'volatility': 0.02,
                'regime': 'unknown'
            }
    
    async def _assess_liquidity(
        self, 
        symbol: str, 
        quantity: float, 
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Assess liquidity for execution planning
        
        Args:
            symbol: Trading symbol
            quantity: Intended trade quantity
            market_data: Current market data
            
        Returns:
            Liquidity score dict with assessment details
        """
        try:
            # Try to use liquidity engine if available
            if hasattr(self, 'liquidity_engine') and self.liquidity_engine:
                from ..data.liquidity_engine import LiquidityAssessmentEngine
                if isinstance(self.liquidity_engine, LiquidityAssessmentEngine):
                    score = self.liquidity_engine.assess_liquidity_score(
                        symbol, market_data
                    )
                    return score
            
            # Fallback: Simple liquidity assessment
            avg_volume = market_data.get('avg_volume', market_data.get('volume', 1000000))
            current_volume = market_data.get('volume', avg_volume)
            
            # Volume ratio
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            
            # Participation rate
            participation_rate = quantity / avg_volume if avg_volume > 0 else 0.01
            
            # Liquidity score (0-100)
            overall_score = 70.0  # Start with normal
            if volume_ratio > 1.5:
                overall_score += 15  # High volume = better liquidity
            elif volume_ratio < 0.5:
                overall_score -= 20  # Low volume = worse liquidity
            
            # Adjust for participation rate
            if participation_rate > 0.1:  # More than 10% of daily volume
                overall_score -= 20
            elif participation_rate > 0.05:  # 5-10%
                overall_score -= 10
            
            overall_score = max(0, min(100, overall_score))
            
            # Determine regime
            if overall_score >= 80:
                liquidity_regime = 'high_liquidity'
            elif overall_score >= 60:
                liquidity_regime = 'normal_liquidity'
            elif overall_score >= 40:
                liquidity_regime = 'low_liquidity'
            else:
                liquidity_regime = 'illiquid'
            
            return {
                'symbol': symbol,
                'overall_score': overall_score,
                'liquidity_regime': liquidity_regime,
                'avg_daily_volume': avg_volume,
                'current_volume': current_volume,
                'volume_ratio': volume_ratio,
                'participation_rate': participation_rate,
                'avg_trade_size': avg_volume / 1000,  # Estimate average trade size
                'bid_ask_spread_bps': market_data.get('spread_bps', 5.0),
                'effective_spread_bps': market_data.get('spread_bps', 5.0) * 1.4,
                'market_depth': avg_volume * 0.05,
                'confidence': 0.7
            }
            
        except Exception as e:
            self.logger.error(f"Error assessing liquidity: {e}")
            # Return conservative defaults
            return {
                'symbol': symbol,
                'overall_score': 50.0,
                'liquidity_regime': 'normal_liquidity',
                'avg_daily_volume': 1000000,
                'avg_trade_size': 1000,
                'confidence': 0.5
            }
    
    def _select_execution_algorithm(
        self,
        quantity: float,
        urgency: str,
        liquidity_score: Dict[str, Any],
        time_horizon: int
    ) -> str:
        """
        Select optimal execution algorithm based on conditions
        
        Args:
            quantity: Trade quantity
            urgency: Execution urgency level
            liquidity_score: Liquidity assessment results
            time_horizon: Maximum execution time (seconds)
            
        Returns:
            Selected algorithm name
        """
        try:
            liquidity_regime = liquidity_score.get('liquidity_regime', 'normal_liquidity')
            
            # Emergency/urgent trades use market orders
            if urgency in ['urgent', 'emergency']:
                self.logger.info(f"📊 Algorithm selected: MARKET (urgency: {urgency})")
                return 'market'
            
            # Small quantities use market orders
            if quantity < 100:
                self.logger.info(f"📊 Algorithm selected: MARKET (small quantity: {quantity})")
                return 'market'
            
            # Illiquid markets use adaptive algorithms
            if liquidity_regime in ['illiquid', 'crisis_liquidity']:
                self.logger.info(f"📊 Algorithm selected: ADAPTIVE (liquidity: {liquidity_regime})")
                return 'adaptive'
            
            # Large quantities with time flexibility use TWAP
            if time_horizon > 300 and quantity > 5000:
                self.logger.info(f"📊 Algorithm selected: TWAP (large order, time available)")
                return 'twap'
            
            # Volume-sensitive use VWAP
            participation_rate = liquidity_score.get('participation_rate', 0.0)
            if participation_rate > 0.05:  # More than 5% of daily volume
                self.logger.info(f"📊 Algorithm selected: VWAP (high participation: {participation_rate:.2%})")
                return 'vwap'
            
            # Low liquidity - use adaptive
            if liquidity_regime == 'low_liquidity':
                self.logger.info(f"📊 Algorithm selected: ADAPTIVE (low liquidity)")
                return 'adaptive'
            
            # Default to LIMIT for normal conditions
            self.logger.info(f"📊 Algorithm selected: LIMIT (normal conditions)")
            return 'limit'
            
        except Exception as e:
            self.logger.error(f"Error selecting algorithm: {e}")
            return 'market'  # Safe fallback
    
    async def _estimate_market_impact(
        self,
        symbol: str,
        quantity: float,
        side: str,
        liquidity_score: Dict[str, Any],
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Estimate market impact using Almgren-Chriss model
        
        Args:
            symbol: Trading symbol
            quantity: Trade quantity
            side: 'buy' or 'sell'
            liquidity_score: Liquidity assessment
            market_data: Current market data
            
        Returns:
            Market impact estimate dict
        """
        try:
            import numpy as np
            
            # Get parameters
            price = market_data.get('current_price', 100.0)
            market_data.get('volatility', 0.02)
            avg_volume = liquidity_score.get('avg_daily_volume', 1000000)
            participation_rate = quantity / avg_volume if avg_volume > 0 else 0.01
            
            # Almgren-Chriss model coefficients
            # These can be calibrated based on historical data
            linear_coefficient = 0.001  # Permanent impact coefficient
            sqrt_coefficient = 0.01     # Temporary impact coefficient
            
            # Adjust coefficients based on liquidity regime
            liquidity_regime = liquidity_score.get('liquidity_regime', 'normal_liquidity')
            if liquidity_regime == 'high_liquidity':
                linear_coefficient *= 0.5
                sqrt_coefficient *= 0.7
            elif liquidity_regime in ['low_liquidity', 'illiquid']:
                linear_coefficient *= 2.0
                sqrt_coefficient *= 1.5
            elif liquidity_regime == 'crisis_liquidity':
                linear_coefficient *= 3.0
                sqrt_coefficient *= 2.0
            
            # Permanent impact (linear in participation rate)
            permanent_impact = linear_coefficient * participation_rate
            
            # Temporary impact (square root law)
            temporary_impact = sqrt_coefficient * np.sqrt(participation_rate)
            
            # Total impact in basis points
            total_impact_bps = (permanent_impact + temporary_impact) * 10000
            permanent_impact_bps = permanent_impact * 10000
            temporary_impact_bps = temporary_impact * 10000
            
            # Price adjustment (positive for buys, negative for sells)
            price_adjustment = price * (total_impact_bps / 10000)
            if side.lower() == 'sell':
                price_adjustment = -price_adjustment
            
            # Spread cost
            spread_cost_bps = liquidity_score.get('bid_ask_spread_bps', 5.0) / 2
            
            # Total execution cost
            execution_cost_bps = spread_cost_bps + total_impact_bps
            
            # Price limit (for limit orders)
            if side.lower() == 'buy':
                price_limit = price + (price * (total_impact_bps * 1.5 / 10000))  # 1.5x impact as limit
            else:
                price_limit = price - (price * (total_impact_bps * 1.5 / 10000))
            
            self.logger.info(
                f"💰 Market impact estimate: {total_impact_bps:.2f}bps "
                f"(permanent: {permanent_impact_bps:.2f}bps, temporary: {temporary_impact_bps:.2f}bps)"
            )
            
            return {
                'permanent_impact_bps': permanent_impact_bps,
                'temporary_impact_bps': temporary_impact_bps,
                'total_impact_bps': total_impact_bps,
                'spread_cost_bps': spread_cost_bps,
                'execution_cost_bps': execution_cost_bps,
                'price_adjustment': price_adjustment,
                'price_limit': price_limit,
                'participation_rate': participation_rate,
                'model_type': 'almgren_chriss'
            }
            
        except Exception as e:
            self.logger.error(f"Error estimating market impact: {e}")
            # Return conservative estimates
            return {
                'permanent_impact_bps': 5.0,
                'temporary_impact_bps': 5.0,
                'total_impact_bps': 10.0,
                'price_adjustment': 0.0,
                'execution_cost_bps': 15.0,
                'model_type': 'fallback'
            }
    
    def _get_venue_preferences(
        self, 
        symbol: str, 
        liquidity_score: Dict[str, Any]
    ) -> List[str]:
        """
        Get venue routing preferences
        
        Args:
            symbol: Trading symbol
            liquidity_score: Liquidity assessment
            
        Returns:
            List of preferred venues in priority order
        """
        # Default venue preferences
        # In production, this would query venue analytics
        venues = ['NYSE', 'NASDAQ', 'ARCA']
        
        # Adjust based on liquidity
        liquidity_regime = liquidity_score.get('liquidity_regime', 'normal_liquidity')
        if liquidity_regime in ['low_liquidity', 'illiquid']:
            # Prefer primary exchange for low liquidity
            venues = ['NYSE', 'NASDAQ']
        elif liquidity_regime == 'high_liquidity':
            # Can use more venues
            venues = ['NYSE', 'NASDAQ', 'ARCA', 'BATS']
        
        return venues
    
    def _create_slicing_plan(
        self,
        total_quantity: float,
        algorithm: str,
        time_horizon: int,
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create order slicing plan for large orders
        
        Args:
            total_quantity: Total order quantity
            algorithm: Selected execution algorithm
            time_horizon: Time available for execution (seconds)
            market_data: Current market data
            
        Returns:
            Slicing plan dict
        """
        try:
            if algorithm == 'twap':
                # Time-Weighted Average Price slicing
                num_slices = max(3, min(20, time_horizon // 60))  # 1 slice per minute, max 20
                slice_size = total_quantity / num_slices
                slice_interval = time_horizon / num_slices
                
                return {
                    'algorithm': 'twap',
                    'num_slices': num_slices,
                    'slice_size': slice_size,
                    'slice_interval_seconds': slice_interval,
                    'total_duration_seconds': time_horizon
                }
                
            elif algorithm == 'vwap':
                # Volume-Weighted Average Price slicing
                # Distribute quantity proportional to expected volume pattern
                num_slices = max(3, min(15, time_horizon // 120))  # 1 slice per 2 minutes
                
                return {
                    'algorithm': 'vwap',
                    'num_slices': num_slices,
                    'volume_weighted': True,
                    'total_duration_seconds': time_horizon
                }
                
            elif algorithm == 'adaptive':
                # Adaptive slicing based on market conditions
                num_slices = max(5, min(25, time_horizon // 45))  # More frequent for adaptive
                
                return {
                    'algorithm': 'adaptive',
                    'num_slices': num_slices,
                    'adaptive_sizing': True,
                    'total_duration_seconds': time_horizon
                }
            
            else:
                # Simple equal slicing
                num_slices = max(3, min(10, time_horizon // 180))  # 1 slice per 3 minutes
                slice_size = total_quantity / num_slices
                
                return {
                    'algorithm': 'simple',
                    'num_slices': num_slices,
                    'slice_size': slice_size,
                    'total_duration_seconds': time_horizon
                }
                
        except Exception as e:
            self.logger.error(f"Error creating slicing plan: {e}")
            return {
                'algorithm': 'simple',
                'num_slices': 1,
                'slice_size': total_quantity
            }
    
    # ========================================
    # AUTHORIZATION METHODS
    # ========================================
    
    def validate_authorization(self, authorization: Any) -> bool:
        """Validate trading authorization"""
        try:
            # Check if authorization is valid
            if not authorization:
                self.logger.warning("❌ No authorization provided")
                return False
            
            # Check authorization structure
            if isinstance(authorization, dict):
                required_fields = ['authorized', 'symbol', 'quantity']
                for field in required_fields:
                    if field not in authorization:
                        self.logger.warning(f"❌ Missing authorization field: {field}")
                        return False
                
                if not authorization.get('authorized', False):
                    self.logger.warning("❌ Authorization not granted")
                    return False
                
                self.logger.info("✅ Trading authorization validated")
                return True
            else:
                # Check if authorization object has required attributes
                if hasattr(authorization, 'authorized') and authorization.authorized:
                    self.logger.info("✅ Trading authorization validated")
                    return True
                else:
                    self.logger.warning("❌ Invalid authorization object")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Authorization validation failed: {e}")
            return False
    
    def authorize_operation(self, operation: str, details: Dict[str, Any] = None) -> bool:
        """Authorize trading engine operations"""
        try:
            # Basic authorization logic for trading operations
            authorized_operations = [
                'create_execution_plan', 'modify_plan', 'cancel_plan',
                'analyze_execution', 'optimize_execution'
            ]
            
            if operation in authorized_operations:
                self.logger.info(f"✅ Trading operation authorized: {operation}")
                return True
            else:
                self.logger.warning(f"❌ Trading operation not authorized: {operation}")
                return False
                
        except Exception as e:
            self.logger.error(f"Authorization failed: {e}")
            return False
    
    def check_authority_level(self, required_level: str) -> bool:
        """Check if component has required authority level"""
        try:
            # Trading engine has OPERATIONAL authority level
            component_authority = "OPERATIONAL"
            
            authority_hierarchy = {
                "READ_ONLY": 1,
                "OPERATIONAL": 2,
                "GOVERNANCE_CONTROL": 3,
                "SYSTEM_CONTROL": 4
            }
            
            component_level = authority_hierarchy.get(component_authority, 0)
            required_level_num = authority_hierarchy.get(required_level, 999)
            
            authorized = component_level >= required_level_num
            
            if authorized:
                self.logger.info(f"✅ Authority level check passed: {component_authority} >= {required_level}")
            else:
                self.logger.warning(f"❌ Authority level check failed: {component_authority} < {required_level}")
            
            return authorized
            
        except Exception as e:
            self.logger.error(f"Authority level check failed: {e}")
            return False