"""
IBKR Execution Bridge
====================

Integration bridge between the Unified Core Engine and IBKR broker.
This bridge implements the execution interface to route orders through IBKR
while maintaining the abstraction layer for multi-broker support.

Features:
- Seamless IBKR integration with unified core engine
- Order type translation between core engine and IBKR
- Real-time execution status tracking
- Portfolio synchronization
- Risk management integration

Author: Pro Quant Desk Trader
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid

# Core execution imports
from .execution_engine import ExecutionRequest, ExecutionResult, ExecutionStatus, ExecutionAlgorithm
from .order_manager import Order, OrderStatus, OrderType, OrderSide

# IBKR integration imports
from ..broker_integration import (
    IBKRClient, IBKRConfig, 
    Order as IBKROrder, OrderResult, OrderType as IBKROrderType, 
    OrderSide as IBKROrderSide, OrderStatus as IBKROrderStatus,
    Position, PortfolioSummary, MarketData
)

logger = logging.getLogger(__name__)


class IBKRExecutionBridge:
    """
    Bridge between Unified Core Engine and IBKR
    
    This bridge translates core engine execution requests into IBKR orders
    and provides seamless integration while maintaining abstraction.
    """
    
    def __init__(self, ibkr_config: IBKRConfig):
        """Initialize the IBKR execution bridge"""
        self.config = ibkr_config
        self.ibkr_client = IBKRClient(ibkr_config)
        
        # Execution tracking
        self.active_executions: Dict[str, ExecutionRequest] = {}
        self.execution_results: Dict[str, ExecutionResult] = {}
        self.ibkr_order_mapping: Dict[str, str] = {}  # core_id -> ibkr_id
        
        # Portfolio sync
        self.last_portfolio_sync = None
        self.portfolio_sync_interval = 30  # seconds
        
        # Market data cache
        self.market_data_cache: Dict[str, MarketData] = {}
        
        logger.info("IBKR Execution Bridge initialized")
    
    async def connect(self) -> bool:
        """Connect to IBKR"""
        try:
            success = await self.ibkr_client.connect()
            if success:
                logger.info("✅ IBKR Execution Bridge connected")
                # Start portfolio sync
                asyncio.create_task(self._portfolio_sync_loop())
                return True
            else:
                logger.error("❌ Failed to connect IBKR Execution Bridge")
                return False
        except Exception as e:
            logger.error(f"IBKR connection error: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from IBKR"""
        try:
            return await self.ibkr_client.disconnect()
        except Exception as e:
            logger.error(f"IBKR disconnection error: {e}")
            return False
    
    async def execute_order(self, request: ExecutionRequest) -> ExecutionResult:
        """
        Execute order through IBKR
        
        Translates core engine execution request to IBKR order and tracks execution.
        """
        try:
            # Store request
            self.active_executions[request.request_id] = request
            
            # Create initial result
            result = ExecutionResult(
                request_id=request.request_id,
                status=ExecutionStatus.PENDING,
                symbol=request.symbol,
                side=request.side,
                requested_quantity=request.quantity,
                algorithm_used=request.algorithm,
                execution_time=datetime.now()
            )
            
            # Validate connection
            if not await self.ibkr_client.is_connected():
                result.status = ExecutionStatus.FAILED
                result.error_message = "IBKR not connected"
                return result
            
            # Translate request to IBKR order
            ibkr_order = self._create_ibkr_order(request)
            
            # Execute order through IBKR
            logger.info(f"Executing order via IBKR: {request.symbol} {request.side} {request.quantity}")
            order_result = await self.ibkr_client.place_order(ibkr_order)
            
            # Map order IDs
            self.ibkr_order_mapping[request.request_id] = order_result.order_id
            
            # Update result with IBKR response
            result.status = self._map_ibkr_status_to_execution_status(order_result.status)
            result.executed_quantity = order_result.filled_quantity
            result.average_price = order_result.average_price or 0.0
            result.commission = order_result.commission
            result.error_message = order_result.message if order_result.error_code else None
            
            # Store result
            self.execution_results[request.request_id] = result
            
            logger.info(f"Order executed: {result.status.value} - {request.symbol}")
            return result
            
        except Exception as e:
            logger.error(f"Order execution error: {e}")
            result.status = ExecutionStatus.FAILED
            result.error_message = str(e)
            return result
    
    async def cancel_order(self, request_id: str) -> bool:
        """Cancel order through IBKR"""
        try:
            if request_id not in self.ibkr_order_mapping:
                logger.warning(f"Order {request_id} not found in mapping")
                return False
            
            ibkr_order_id = self.ibkr_order_mapping[request_id]
            success = await self.ibkr_client.cancel_order(ibkr_order_id)
            
            if success:
                # Update execution result
                if request_id in self.execution_results:
                    self.execution_results[request_id].status = ExecutionStatus.CANCELLED
                logger.info(f"Order cancelled: {request_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Order cancellation error: {e}")
            return False
    
    async def get_order_status(self, request_id: str) -> Optional[ExecutionResult]:
        """Get real-time order status from IBKR"""
        try:
            if request_id not in self.ibkr_order_mapping:
                return self.execution_results.get(request_id)
            
            ibkr_order_id = self.ibkr_order_mapping[request_id]
            ibkr_status = await self.ibkr_client.get_order_status(ibkr_order_id)
            
            # Update stored result
            if request_id in self.execution_results:
                result = self.execution_results[request_id]
                result.status = self._map_ibkr_status_to_execution_status(ibkr_status)
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"Order status error: {e}")
            return None
    
    async def get_portfolio_summary(self) -> Optional[PortfolioSummary]:
        """Get portfolio summary from IBKR"""
        try:
            return await self.ibkr_client.get_portfolio_summary()
        except Exception as e:
            logger.error(f"Portfolio summary error: {e}")
            return None
    
    async def get_positions(self) -> Dict[str, Position]:
        """Get current positions from IBKR"""
        try:
            return await self.ibkr_client.get_positions()
        except Exception as e:
            logger.error(f"Positions error: {e}")
            return {}
    
    async def get_market_data(self, symbol: str) -> Optional[MarketData]:
        """Get real-time market data from IBKR"""
        try:
            market_data = await self.ibkr_client.get_market_data(symbol)
            if market_data:
                self.market_data_cache[symbol] = market_data
            return market_data
        except Exception as e:
            logger.error(f"Market data error for {symbol}: {e}")
            return None
    
    def _create_ibkr_order(self, request: ExecutionRequest) -> IBKROrder:
        """Translate core execution request to IBKR order"""
        
        # Map order side
        if request.side.upper() == "BUY":
            ibkr_side = IBKROrderSide.BUY
        elif request.side.upper() == "SELL":
            ibkr_side = IBKROrderSide.SELL
        else:
            raise ValueError(f"Invalid order side: {request.side}")
        
        # Map order type based on algorithm
        if request.algorithm == ExecutionAlgorithm.MARKET:
            ibkr_type = IBKROrderType.MARKET
            price = None
        elif request.algorithm == ExecutionAlgorithm.TWAP:
            # For TWAP, use market order with TWAP algo params
            ibkr_type = IBKROrderType.MARKET
            price = None
        elif request.algorithm == ExecutionAlgorithm.VWAP:
            # For VWAP, use market order with VWAP algo params
            ibkr_type = IBKROrderType.MARKET
            price = None
        else:
            # Default to market order
            ibkr_type = IBKROrderType.MARKET
            price = None
        
        # Get market data for price if needed
        if price is None and ibkr_type == IBKROrderType.LIMIT:
            # Use cached market data or current price
            if request.symbol in self.market_data_cache:
                market_data = self.market_data_cache[request.symbol]
                if ibkr_side == IBKROrderSide.BUY:
                    price = market_data.ask  # Buy at ask
                else:
                    price = market_data.bid  # Sell at bid
        
        # Create IBKR order
        ibkr_order = IBKROrder(
            order_id=str(uuid.uuid4()),
            symbol=request.symbol,
            side=ibkr_side,
            order_type=ibkr_type,
            quantity=float(request.quantity),
            price=price,
            strategy_id=request.strategy_id
        )
        
        # Add algorithm parameters if needed
        if request.algorithm in [ExecutionAlgorithm.TWAP, ExecutionAlgorithm.VWAP]:
            ibkr_order.algo_params = {
                "algorithm": request.algorithm.value,
                "duration": getattr(request, 'duration', 3600),  # 1 hour default
                "start_time": datetime.now().isoformat(),
                "urgency": getattr(request, 'urgency', 'NORMAL')
            }
        
        return ibkr_order
    
    def _map_ibkr_status_to_execution_status(self, ibkr_status: IBKROrderStatus) -> ExecutionStatus:
        """Map IBKR order status to core execution status"""
        mapping = {
            IBKROrderStatus.PENDING: ExecutionStatus.PENDING,
            IBKROrderStatus.SUBMITTED: ExecutionStatus.EXECUTING,
            IBKROrderStatus.FILLED: ExecutionStatus.SUCCESS,
            IBKROrderStatus.PARTIALLY_FILLED: ExecutionStatus.PARTIAL,
            IBKROrderStatus.CANCELLED: ExecutionStatus.CANCELLED,
            IBKROrderStatus.REJECTED: ExecutionStatus.REJECTED,
            IBKROrderStatus.EXPIRED: ExecutionStatus.FAILED
        }
        return mapping.get(ibkr_status, ExecutionStatus.FAILED)
    
    async def _portfolio_sync_loop(self):
        """Background task for portfolio synchronization"""
        while True:
            try:
                await asyncio.sleep(self.portfolio_sync_interval)
                
                if await self.ibkr_client.is_connected():
                    # Update portfolio data
                    portfolio = await self.get_portfolio_summary()
                    positions = await self.get_positions()
                    
                    if portfolio:
                        self.last_portfolio_sync = datetime.now()
                        logger.debug("Portfolio synchronized with IBKR")
                
            except asyncio.CancelledError:
                logger.info("Portfolio sync loop cancelled")
                break
            except Exception as e:
                logger.error(f"Portfolio sync error: {e}")
                await asyncio.sleep(10)  # Wait before retry


@dataclass
class IBKRBridgeConfig:
    """Configuration for IBKR execution bridge"""
    ibkr_config: IBKRConfig
    portfolio_sync_interval: int = 30  # seconds
    market_data_cache_timeout: int = 300  # seconds
    enable_real_time_sync: bool = True
    max_order_retries: int = 3
    order_timeout: int = 30  # seconds


class IBKRExecutionBridgeFactory:
    """Factory for creating IBKR execution bridges"""
    
    @staticmethod
    def create_paper_trading_bridge(account_id: str) -> IBKRExecutionBridge:
        """Create IBKR bridge configured for paper trading"""
        from ..broker_integration.ibkr_config import IBKRSetupHelper
        
        ibkr_config = IBKRSetupHelper.create_paper_trading_config(account_id)
        return IBKRExecutionBridge(ibkr_config)
    
    @staticmethod
    def create_live_trading_bridge(account_id: str) -> IBKRExecutionBridge:
        """Create IBKR bridge configured for live trading"""
        from ..broker_integration.ibkr_config import IBKRSetupHelper
        
        ibkr_config = IBKRSetupHelper.create_live_trading_config(account_id)
        return IBKRExecutionBridge(ibkr_config)
    
    @staticmethod
    def create_custom_bridge(ibkr_config: IBKRConfig) -> IBKRExecutionBridge:
        """Create IBKR bridge with custom configuration"""
        return IBKRExecutionBridge(ibkr_config)
