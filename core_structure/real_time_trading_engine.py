#!/usr/bin/env python3
"""
RealTimeTradingEngine: Trading Logic and Signal Generation (Optimized)
======================================================================

Component in the essential flow: Market Data -> UnifiedDataManager -> UnifiedRegimeEngine -> RiskManager -> StrategyManager -> **RealTimeTradingEngine** -> UnifiedExecutionEngine -> PortfolioManager

This engine receives trading signals from StrategyManager and determines HOW to execute trades before sending them to UnifiedExecutionEngine.
It leverages existing high-quality functional components rather than duplicating functionality.

Key Features:
- Trade orchestration delegating to existing UnifiedExecutionEngine
- Market data management using existing market data infrastructure
- Order management leveraging existing OrderManager and SmartOrderRouter
- Strategy allocation coordinating existing optimization components
- Integration with SystemOrchestrator

Author: Professional Trading System Architecture
Version: 2.0.0 (Optimized Delegation)
"""

import asyncio
import logging
import time
import threading
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import deque, defaultdict
import pandas as pd
import numpy as np

# Import existing high-quality functional components (fail-fast architecture)
try:
    from .components.execution import UnifiedExecutionEngine
    from .analytics import CoreAnalyticsEngine, MonitoringAnalyticsEngine
    from .infrastructure.types import OrderType, OrderStatus
    from .strategies import BaseStrategy
    EXECUTION_ENGINE_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("✅ Core execution components loaded successfully")
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.error(f"❌ Required components not available - fail-fast architecture: {e}")
    raise ImportError("Essential execution components not available")

# Additional enums and classes if needed
class TradingMode(Enum):
    PAPER_TRADING = "paper"
    LIVE_TRADING = "live"
    BACKTESTING = "backtest"

@dataclass
class TradingSignal:
    symbol: str
    action: str
    quantity: float
    price: float
    timestamp: datetime

logger = logging.getLogger(__name__)

class TradingMode(Enum):
    """Real-time trading modes"""
    PAPER_TRADING = "paper_trading"
    LIVE_TRADING = "live_trading"
    SIMULATION = "simulation"
    BACKTEST = "backtest"

class DataSourceType(Enum):
    """Types of market data sources"""
    INTERACTIVE_BROKERS = "interactive_brokers"
    YAHOO_FINANCE = "yahoo_finance"
    ALPHA_VANTAGE = "alpha_vantage"
    POLYGON = "polygon"
    WEBSOCKET = "websocket"

class OrderExecutionMode(Enum):
    """Order execution modes"""
    IMMEDIATE = "immediate"
    MARKET_HOURS_ONLY = "market_hours_only"
    BEST_EXECUTION = "best_execution"
    TWAP = "twap"
    VWAP = "vwap"

@dataclass
class RealTimeMarketData:
    """Real-time market data tick"""
    symbol: str
    timestamp: datetime
    bid: float
    ask: float
    last: float
    volume: int
    bid_size: int = 0
    ask_size: int = 0
    source: str = "default"
    latency_ms: float = 0.0
    quality_score: float = 1.0

@dataclass
class RealTimeTradingConfiguration:
    """Configuration for real-time trading - leverages existing components"""
    trading_mode: TradingMode = TradingMode.PAPER_TRADING
    primary_data_source: DataSourceType = DataSourceType.INTERACTIVE_BROKERS
    fallback_data_sources: List[DataSourceType] = field(default_factory=lambda: [DataSourceType.YAHOO_FINANCE])
    order_execution_mode: OrderExecutionMode = OrderExecutionMode.BEST_EXECUTION
    
    # Market data settings
    market_data_timeout_seconds: float = 5.0
    max_latency_ms: float = 100.0
    data_quality_threshold: float = 0.8
    
    # Trading settings
    max_orders_per_second: int = 10
    order_timeout_seconds: float = 30.0
    position_check_interval_seconds: float = 10.0
    
    # Risk management
    max_daily_loss: float = 0.02  # 2% max daily loss
    max_position_concentration: float = 0.1  # 10% max per position
    circuit_breaker_enabled: bool = True
    
    # Configuration for underlying engines
    execution_engine_config: Optional[Dict[str, Any]] = None
    market_data_config: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.execution_engine_config is None:
            self.execution_engine_config = {
                "enable_smart_routing": True,
                "enable_cost_optimization": True,
                "enable_ibkr_integration": True
            }
        if self.market_data_config is None:
            self.market_data_config = {
                "enable_real_time": True,
                "cache_data": True,
                "quality_monitoring": True
            }

@dataclass
class TradingSignal:
    """Trading signal from StrategyManager"""
    symbol: str
    action: str  # buy, sell, hold
    quantity: float
    price: float
    strategy: str
    confidence: float
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

class RealTimeTradingEngine:
    """
    Real-time trading engine that leverages existing high-quality functional components.
    
    Instead of implementing market connectivity, execution logic, and data management directly, it delegates to:
    - UnifiedExecutionEngine for all trade execution
    - MarketDataManager for real-time market data feeds
    - OrderManager for order lifecycle management
    - SmartOrderRouter for optimal execution routing
    - CoreAnalytics for trading performance analysis
    """
    
    def __init__(self, config: Optional[RealTimeTradingConfiguration] = None):
        """Initialize the trading engine with delegation to existing components"""
        self.config = config or RealTimeTradingConfiguration()
        
        # Initialize existing functional components
        self._initialize_delegated_components()
        
        # Trading state
        self.active_signals: Dict[str, List[TradingSignal]] = {}
        self.pending_orders: Dict[str, Any] = {}
        self.position_updates: deque = deque(maxlen=1000)
        
        # Market regime context
        self.current_regime: str = "unknown"
        self.regime_confidence: float = 0.0
        
        # Subscribers
        self.subscribers: List[Any] = []
        
        # Component state
        self.is_running = False
        self.trading_task: Optional[asyncio.Task] = None
        
        # Performance tracking
        self.trades_executed: int = 0
        self.execution_analytics: Dict[str, Any] = {}
        
        logger.info("🚀 RealTimeTradingEngine initialized with component delegation")
    
    def _initialize_delegated_components(self) -> None:
        """Initialize existing functional components for delegation"""
        try:
            # Initialize UnifiedExecutionEngine for trade execution (primary component)
            from .components.execution import ExecutionMode
            self.execution_engine = UnifiedExecutionEngine(
                mode=ExecutionMode.LIVE_TRADING if self.config.trading_mode.value == "live" else ExecutionMode.PAPER_TRADING,
                initial_capital=100000.0
            )
            logger.info("✅ Delegating trade execution to UnifiedExecutionEngine")
            
            # Initialize CoreAnalyticsEngine for performance tracking
            self.analytics_engine = CoreAnalyticsEngine()
            logger.info("✅ Delegating analytics to CoreAnalyticsEngine")
            
            # Initialize MonitoringAnalyticsEngine for quality tracking
            self.monitoring_analytics = MonitoringAnalyticsEngine()
            logger.info("✅ Delegating monitoring to MonitoringAnalyticsEngine")
            
            # Initialize AdvancedRiskManager for central risk authority - CRITICAL
            from .advanced_risk_management import AdvancedRiskManager, RiskConfiguration
            risk_config = RiskConfiguration()
            self.risk_manager = AdvancedRiskManager(risk_config)
            logger.info("✅ Delegating risk management to AdvancedRiskManager")
            
            # Set other components to None (not needed with UnifiedExecutionEngine)
            self.order_manager = None
            self.order_router = None
            self.market_data_manager = None
            self.broker_client = None
            
        except Exception as e:
            logger.error(f"❌ Error initializing delegated components: {e}")
            raise RuntimeError(f"Failed to initialize RealTimeTradingEngine: {e}")
            self.analytics_engine = None
            self.broker_client = None
    
    async def startup(self) -> bool:
        """Start the trading engine"""
        try:
            logger.info("🚀 Starting RealTimeTradingEngine with delegated components...")
            
            # Start delegated components
            if self.execution_engine:
                # UnifiedExecutionEngine is already initialized in constructor
                logger.info("✅ UnifiedExecutionEngine ready")
            
            if self.order_manager:
                await self.order_manager.start()
                logger.info("✅ OrderManager started")
            
            if self.order_router:
                await self.order_router.initialize()
                logger.info("✅ SmartOrderRouter started")
            
            if self.market_data_manager:
                await self.market_data_manager.start()
                logger.info("✅ MarketDataManager started")
            
            if self.analytics_engine:
                # CoreAnalyticsEngine is already initialized in constructor
                logger.info("✅ CoreAnalytics ready")
            
            if self.risk_manager:
                await self.risk_manager.initialize()
                logger.info("✅ AdvancedRiskManager initialized")
            
            if self.broker_client:
                await self.broker_client.connect()
                logger.info("✅ IBKR client connected")
            
            # Start trading loop
            self.trading_task = asyncio.create_task(self._trading_loop())
            self.is_running = True
            
            logger.info("✅ RealTimeTradingEngine started successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start RealTimeTradingEngine: {e}")
            return False
    
    async def shutdown(self) -> None:
        """Shutdown the trading engine"""
        try:
            logger.info("⏹️ Shutting down RealTimeTradingEngine...")
            
            self.is_running = False
            
            if self.trading_task:
                self.trading_task.cancel()
                try:
                    await self.trading_task
                except asyncio.CancelledError:
                    pass
            
            # Shutdown delegated components
            if self.execution_engine:
                await self.execution_engine.shutdown()
                logger.info("✅ UnifiedExecutionEngine stopped")
            
            if self.order_manager:
                await self.order_manager.stop()
                logger.info("✅ OrderManager stopped")
            
            if self.order_router:
                await self.order_router.shutdown()
                logger.info("✅ SmartOrderRouter stopped")
            
            if self.market_data_manager:
                await self.market_data_manager.stop()
                logger.info("✅ MarketDataManager stopped")
            
            if self.analytics_engine:
                await self.analytics_engine.shutdown()
                logger.info("✅ CoreAnalytics stopped")
            
            if self.broker_client:
                await self.broker_client.disconnect()
                logger.info("✅ IBKR client disconnected")
            
            logger.info("✅ RealTimeTradingEngine shutdown complete")
            
        except Exception as e:
            logger.error(f"❌ Failed to shutdown RealTimeTradingEngine: {e}")
    
    async def process_trading_signals(self, signals: List[TradingSignal]) -> List[Dict[str, Any]]:
        """Process trading signals with mandatory risk authorization"""
        execution_results = []
        
        try:
            for signal in signals:
                # Store signal for tracking
                if signal.symbol not in self.active_signals:
                    self.active_signals[signal.symbol] = []
                self.active_signals[signal.symbol].append(signal)
                
                # ================================================================================
                # MANDATORY RISK AUTHORIZATION - INSTITUTIONAL PATTERN
                # ================================================================================
                
                if self.risk_manager:
                    # Create trade request for risk authorization
                    from .advanced_risk_management import TradeRequest
                    trade_request = TradeRequest(
                        request_id=f"req_{uuid.uuid4().hex[:8]}",
                        strategy_id=getattr(signal, 'strategy', 'unknown'),
                        symbol=signal.symbol,
                        side='BUY' if signal.action == 'buy' else 'SELL',
                        quantity=signal.quantity,
                        price=signal.price,
                        signal_confidence=getattr(signal, 'confidence', 1.0),
                        metadata={'signal_timestamp': signal.timestamp.isoformat() if hasattr(signal, 'timestamp') else str(datetime.now())}
                    )
                    
                    # Get risk authorization - MANDATORY
                    authorization = await self.risk_manager.authorize_trade(trade_request)
                    
                    if not authorization.approved:
                        # Risk authorization denied - log and skip execution
                        logger.warning(f"🚫 Trade authorization denied for {signal.symbol}: {authorization.reason}")
                        
                        # Record rejected trade
                        rejection_result = {
                            'symbol': signal.symbol,
                            'action': signal.action,
                            'quantity': signal.quantity,
                            'status': 'REJECTED',
                            'reason': f"Risk authorization denied: {authorization.reason}",
                            'authorization_id': authorization.authorization_id,
                            'risk_level': authorization.risk_level.value,
                            'timestamp': datetime.now().isoformat()
                        }
                        execution_results.append(rejection_result)
                        continue
                    
                    # Risk authorization approved - proceed with execution
                    logger.info(f"✅ Trade authorized: {signal.symbol} {signal.action} {signal.quantity} (ID: {authorization.authorization_id})")
                    
                    # Check for risk-adjusted quantity
                    if authorization.adjusted_quantity:
                        original_quantity = signal.quantity
                        signal.quantity = authorization.adjusted_quantity
                        logger.info(f"📊 Quantity adjusted by risk manager: {original_quantity} → {signal.quantity}")
                
                # ================================================================================
                # EXECUTION WITH RISK APPROVAL TOKEN
                # ================================================================================
                
                # Delegate execution to sophisticated execution engine
                if self.execution_engine:
                    # Add authorization metadata to execution
                    execution_metadata = {
                        'authorization_id': authorization.authorization_id if self.risk_manager else 'no_risk_manager',
                        'risk_level': authorization.risk_level.value if self.risk_manager else 'unknown',
                        'risk_conditions': authorization.conditions if self.risk_manager else []
                    }
                    
                    execution_result = await self.execution_engine.execute_signal(
                        symbol=signal.symbol,
                        action=signal.action,
                        quantity=signal.quantity,
                        price=signal.price,
                        strategy=signal.strategy,
                        confidence=signal.confidence,
                        metadata=execution_metadata
                    )
                    execution_results.append(execution_result)
                    self.trades_executed += 1
                    
                    # Notify subscribers
                    self._notify_subscribers("trade_executed", {
                        "signal": signal,
                        "result": execution_result,
                        "authorization": authorization.__dict__ if self.risk_manager else None
                    })
                else:
                    # Fallback execution
                    logger.warning("⚠️ Using fallback execution - UnifiedExecutionEngine not available")
                    execution_result = await self._fallback_execution(signal)
                    execution_results.append(execution_result)
            
            return execution_results
            
        except Exception as e:
            logger.error(f"❌ Error processing trading signals: {e}")
            return []
    
    async def _fallback_execution(self, signal: TradingSignal) -> Dict[str, Any]:
        """Fallback execution when delegated engine not available"""
        try:
            # Simple mock execution for testing
            execution_result = {
                "symbol": signal.symbol,
                "action": signal.action,
                "quantity": signal.quantity,
                "executed_price": signal.price,
                "execution_time": datetime.now(),
                "status": "filled",
                "execution_mode": "fallback",
                "fees": signal.quantity * signal.price * 0.001  # 0.1% fee
            }
            
            logger.info(f"📈 Fallback execution: {signal.action} {signal.quantity} {signal.symbol} @ {signal.price}")
            return execution_result
            
        except Exception as e:
            logger.error(f"❌ Fallback execution failed: {e}")
            return {
                "symbol": signal.symbol,
                "status": "failed",
                "error": str(e)
            }
    
    async def get_market_data(self, symbols: List[str]) -> Dict[str, RealTimeMarketData]:
        """Get real-time market data using delegated market data manager"""
        try:
            if self.market_data_manager:
                # Delegate to sophisticated market data manager
                market_data = await self.market_data_manager.get_real_time_data(symbols)
                
                # Convert to our interface format
                formatted_data = {}
                for symbol, data in market_data.items():
                    formatted_data[symbol] = RealTimeMarketData(
                        symbol=symbol,
                        timestamp=data.get("timestamp", datetime.now()),
                        bid=data.get("bid", 0.0),
                        ask=data.get("ask", 0.0),
                        last=data.get("last", 0.0),
                        volume=data.get("volume", 0),
                        source=data.get("source", "delegated"),
                        quality_score=data.get("quality_score", 1.0)
                    )
                
                return formatted_data
            else:
                # Fallback market data
                logger.warning("⚠️ Using fallback market data - MarketDataManager not available")
                return self._fallback_market_data(symbols)
            
        except Exception as e:
            logger.error(f"❌ Error getting market data: {e}")
            return {}
    
    def _fallback_market_data(self, symbols: List[str]) -> Dict[str, RealTimeMarketData]:
        """Fallback market data when delegated manager not available"""
        fallback_data = {}
        
        for symbol in symbols:
            # Generate mock market data for testing
            base_price = 100.0  # Mock base price
            spread = 0.05
            
            fallback_data[symbol] = RealTimeMarketData(
                symbol=symbol,
                timestamp=datetime.now(),
                bid=base_price - spread/2,
                ask=base_price + spread/2,
                last=base_price,
                volume=1000,
                source="fallback"
            )
        
        return fallback_data
    
    def update_market_regime(self, regime: str, confidence: float) -> None:
        """Update market regime context for execution decisions"""
        self.current_regime = regime
        self.regime_confidence = confidence
        
        logger.info(f"📊 Market regime updated: {regime} (confidence: {confidence:.2f})")
        
        # Update execution engine with regime context
        if self.execution_engine and hasattr(self.execution_engine, 'update_market_context'):
            try:
                self.execution_engine.update_market_context(regime, confidence)
            except Exception as e:
                logger.warning(f"⚠️ Could not update execution engine context: {e}")
        
        # Update order router with regime context
        if self.order_router and hasattr(self.order_router, 'update_market_context'):
            try:
                self.order_router.update_market_context(regime, confidence)
            except Exception as e:
                logger.warning(f"⚠️ Could not update order router context: {e}")
    
    async def _trading_loop(self) -> None:
        """Main trading loop"""
        while self.is_running:
            try:
                # Check for pending orders using delegated order manager
                if self.order_manager:
                    await self.order_manager.check_pending_orders()
                
                # Update execution analytics using delegated analytics
                if self.analytics_engine:
                    await self._update_execution_analytics()
                
                # Sleep for position check interval
                await asyncio.sleep(self.config.position_check_interval_seconds)
                
            except asyncio.CancelledError:
                logger.info("🔄 Trading loop cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Error in trading loop: {e}")
                await asyncio.sleep(1)
    
    async def _update_execution_analytics(self) -> None:
        """Update execution analytics using delegated analytics engine"""
        try:
            if self.analytics_engine and hasattr(self.analytics_engine, 'calculate_execution_metrics'):
                metrics = await self.analytics_engine.calculate_execution_metrics(
                    trades_executed=self.trades_executed,
                    active_signals=self.active_signals,
                    current_regime=self.current_regime
                )
                self.execution_analytics = metrics
            else:
                # Fallback analytics
                self.execution_analytics = {
                    "trades_executed": self.trades_executed,
                    "active_signals_count": sum(len(signals) for signals in self.active_signals.values()),
                    "current_regime": self.current_regime,
                    "regime_confidence": self.regime_confidence,
                    "uptime_seconds": time.time() - getattr(self, '_start_time', time.time())
                }
        except Exception as e:
            logger.warning(f"⚠️ Analytics update failed: {e}")
    
    def _notify_subscribers(self, event_type: str, data: Dict[str, Any]) -> None:
        """Notify subscribers of trading events"""
        for subscriber in self.subscribers:
            try:
                if hasattr(subscriber, 'on_trading_event'):
                    subscriber.on_trading_event(event_type, data)
            except Exception as e:
                logger.error(f"❌ Error notifying subscriber: {e}")
    
    def subscribe(self, subscriber: Any) -> None:
        """Subscribe to trading events"""
        if subscriber not in self.subscribers:
            self.subscribers.append(subscriber)
            logger.info(f"📢 New trading subscriber added: {type(subscriber).__name__}")
    
    def unsubscribe(self, subscriber: Any) -> None:
        """Unsubscribe from trading events"""
        if subscriber in self.subscribers:
            self.subscribers.remove(subscriber)
            logger.info(f"📢 Trading subscriber removed: {type(subscriber).__name__}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive trading engine status"""
        active_signals_count = sum(len(signals) for signals in self.active_signals.values())
        
        return {
            "is_running": self.is_running,
            "trading_mode": self.config.trading_mode.value,
            "current_regime": self.current_regime,
            "regime_confidence": self.regime_confidence,
            "trades_executed": self.trades_executed,
            "active_signals_count": active_signals_count,
            "pending_orders_count": len(self.pending_orders),
            "subscribers_count": len(self.subscribers),
            "delegated_components": {
                "execution_engine_available": self.execution_engine is not None,
                "order_manager_available": self.order_manager is not None,
                "order_router_available": self.order_router is not None,
                "market_data_manager_available": self.market_data_manager is not None,
                "analytics_engine_available": self.analytics_engine is not None,
                "broker_client_available": self.broker_client is not None
            },
            "execution_analytics": self.execution_analytics
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get trading performance metrics using delegated analytics"""
        try:
            if self.analytics_engine and hasattr(self.analytics_engine, 'get_trading_performance'):
                return self.analytics_engine.get_trading_performance(
                    trades_executed=self.trades_executed,
                    execution_analytics=self.execution_analytics,
                    current_regime=self.current_regime
                )
            else:
                # Fallback performance metrics
                return {
                    "total_trades": self.trades_executed,
                    "active_signals": sum(len(signals) for signals in self.active_signals.values()),
                    "regime_context": self.current_regime,
                    "engine_status": "operational" if self.is_running else "stopped",
                    "delegation_status": "fallback"
                }
        except Exception as e:
            logger.error(f"❌ Error getting performance metrics: {e}")
            return {"error": str(e)}

# Factory function
def create_real_time_trading_engine(config: Optional[RealTimeTradingConfiguration] = None) -> RealTimeTradingEngine:
    """Create a RealTimeTradingEngine instance"""
    return RealTimeTradingEngine(config)

# Export for SystemOrchestrator integration
__all__ = [
    'RealTimeTradingEngine', 'RealTimeTradingConfiguration', 'TradingSignal',
    'TradingMode', 'OrderExecutionMode', 'RealTimeMarketData',
    'create_real_time_trading_engine'
]