#!/usr/bin/env python3
"""
Backtesting Execution Engine
============================

Pure simulation execution engine for historical backtesting.
No IBKR integration - uses market data simulation only.

Author: Pro Quant Desk Trader
"""

import logging
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import uuid

from .execution_engine import ExecutionRequest, ExecutionResult, ExecutionStatus, ExecutionAlgorithm
from .order_manager import OrderSide

logger = logging.getLogger(__name__)


class BacktestingExecutionEngine:
    """
    Pure simulation execution engine for historical backtesting
    
    Features:
    - No IBKR dependencies 
    - Realistic slippage and commission simulation
    - Market impact modeling
    - Instant execution with simulated delay
    - Professional execution analytics
    """
    
    def __init__(self, commission_rate: float = 0.001, slippage_bps: float = 1.0):
        """Initialize backtesting execution engine"""
        self.commission_rate = commission_rate  # 0.1% commission
        self.slippage_bps = slippage_bps  # 1 basis point slippage
        
        # Simulation parameters
        self.backtesting_data_provider = None
        self.execution_history: List[ExecutionResult] = []
        
        # Market simulation
        self.market_impact_factor = 0.0001  # 0.01% market impact per $100K order
        self.bid_ask_spread_bps = 2.0  # 2 basis points spread
        
        logger.info("✅ Backtesting Execution Engine initialized (Pure Simulation Mode)")
    
    def set_backtesting_data_provider(self, data_provider):
        """Set backtesting data provider for price simulation"""
        self.backtesting_data_provider = data_provider
        logger.info("✅ Backtesting data provider connected to execution engine")
    
    async def execute_order(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute order using pure simulation (no IBKR)"""
        start_time = datetime.now()
        
        try:
            # Get current market price from backtesting data
            current_price = self._get_simulation_price(request.symbol)
            if current_price is None:
                current_price = 100.0  # Fallback price for missing data
            
            # Calculate execution price with realistic market effects
            execution_price = self._calculate_execution_price(
                request.symbol, request.side, request.quantity, current_price
            )
            
            # Calculate commission and slippage
            commission = request.quantity * execution_price * self.commission_rate
            slippage = execution_price * (self.slippage_bps / 10000.0)
            
            # Apply slippage direction based on order side
            if request.side == OrderSide.BUY:
                final_price = execution_price + slippage
            else:  # SELL
                final_price = execution_price - slippage
            
            # Simulate small processing delay (realistic but fast)
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Create successful execution result
            result = ExecutionResult(
                request_id=request.request_id,
                status=ExecutionStatus.SUCCESS,
                symbol=request.symbol,
                side=request.side,
                requested_quantity=request.quantity,
                executed_quantity=request.quantity,  # Full fill in simulation
                average_price=final_price,
                total_cost=commission,
                execution_time=execution_time,
                algorithm_used=request.algorithm
            )
            
            # Store execution for analytics
            self.execution_history.append(result)
            
            logger.debug(f"✅ SIMULATED EXECUTION: {request.symbol} {request.side} "
                        f"{request.quantity} @ ${final_price:.2f} (commission: ${commission:.2f})")
            
            return result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Backtesting execution error: {e}")
            
            return ExecutionResult(
                request_id=request.request_id,
                status=ExecutionStatus.FAILED,
                symbol=request.symbol,
                side=request.side,
                requested_quantity=request.quantity,
                execution_time=execution_time,
                error_message=f"Simulation error: {str(e)}"
            )
    
    def _get_simulation_price(self, symbol: str) -> Optional[float]:
        """Get current price from backtesting data provider"""
        if self.backtesting_data_provider:
            return self.backtesting_data_provider.get_current_price(symbol)
        return None
    
    def _calculate_execution_price(self, symbol: str, side: OrderSide, 
                                 quantity: float, market_price: float) -> float:
        """Calculate realistic execution price with market impact"""
        
        # Base execution price
        execution_price = market_price
        
        # Add bid-ask spread impact
        spread_impact = market_price * (self.bid_ask_spread_bps / 20000.0)  # Half spread
        if side == OrderSide.BUY:
            execution_price += spread_impact  # Buy at ask
        else:
            execution_price -= spread_impact  # Sell at bid
        
        # Add market impact (larger orders have more impact)
        order_value = quantity * market_price
        market_impact = order_value * self.market_impact_factor
        market_impact_price = market_price * (market_impact / 100000.0)  # Scale to price
        
        if side == OrderSide.BUY:
            execution_price += market_impact_price  # Buy pushes price up
        else:
            execution_price -= market_impact_price  # Sell pushes price down
        
        return max(0.01, execution_price)  # Ensure positive price
    
    def get_execution_analytics(self) -> Dict[str, Any]:
        """Get execution analytics for performance review"""
        if not self.execution_history:
            return {"total_executions": 0}
        
        successful_executions = [e for e in self.execution_history if e.status == ExecutionStatus.SUCCESS]
        
        total_commission = sum(e.total_cost for e in successful_executions)
        avg_execution_time = np.mean([e.execution_time for e in successful_executions])
        
        return {
            "total_executions": len(self.execution_history),
            "successful_executions": len(successful_executions),
            "success_rate": len(successful_executions) / len(self.execution_history) if self.execution_history else 0,
            "total_commission": total_commission,
            "avg_execution_time_ms": avg_execution_time * 1000,
            "avg_commission_per_trade": total_commission / len(successful_executions) if successful_executions else 0
        }
    
    def reset_execution_history(self):
        """Reset execution history for new backtest"""
        self.execution_history.clear()
        logger.info("🔄 Execution history reset for new backtest")
