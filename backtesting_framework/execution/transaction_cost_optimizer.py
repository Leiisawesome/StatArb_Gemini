#!/usr/bin/env python3
"""
Transaction Cost Optimizer
Phase 2: Core System Integration - Batch 2
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class TransactionCostOptimizer:
    """Transaction cost optimization system"""
    
    def __init__(self):
        self.cost_models = {}
        self.optimization_history = []
        
        # Default cost parameters
        self.default_commission = 0.005  # $5 per trade
        self.default_slippage = 0.001    # 0.1% slippage
        self.default_market_impact = 0.0001  # 0.01% per $10k
        
        logger.info("Initialized TransactionCostOptimizer")
    
    def calculate_transaction_costs(self, symbol: str, side: str, quantity: int, 
                                  price: float, order_type: str = "MARKET") -> Dict:
        """Calculate total transaction costs"""
        
        # Commission costs
        commission_cost = self.default_commission
        
        # Slippage costs
        slippage_cost = price * quantity * self.default_slippage
        
        # Market impact costs
        trade_value = price * quantity
        market_impact_cost = trade_value * self.default_market_impact * (trade_value / 10000)
        
        # Total costs
        total_cost = commission_cost + slippage_cost + market_impact_cost
        total_cost_bps = (total_cost / trade_value) * 10000  # Basis points
        
        cost_breakdown = {
            'commission': commission_cost,
            'slippage': slippage_cost,
            'market_impact': market_impact_cost,
            'total_cost': total_cost,
            'total_cost_bps': total_cost_bps,
            'trade_value': trade_value
        }
        
        logger.debug(f"Transaction costs for {side} {quantity} {symbol}: ${total_cost:.2f} ({total_cost_bps:.1f} bps)")
        return cost_breakdown
    
    def optimize_order_size(self, symbol: str, side: str, total_quantity: int,
                          price: float, max_cost_bps: float = 10.0) -> Dict:
        """Optimize order size to minimize transaction costs"""
        
        # Test different order sizes
        order_sizes = [total_quantity]  # Start with single order
        
        # Split into smaller orders if beneficial
        if total_quantity > 1000:
            order_sizes.extend([total_quantity // 2, total_quantity // 4])
        
        best_config = None
        min_total_cost = float('inf')
        
        for order_size in order_sizes:
            if order_size <= 0:
                continue
            
            num_orders = (total_quantity + order_size - 1) // order_size  # Ceiling division
            actual_order_size = total_quantity // num_orders
            
            # Calculate costs for this configuration
            cost_per_order = self.calculate_transaction_costs(symbol, side, actual_order_size, price)
            total_cost = cost_per_order['total_cost'] * num_orders
            total_cost_bps = (total_cost / (price * total_quantity)) * 10000
            
            if total_cost_bps <= max_cost_bps and total_cost < min_total_cost:
                min_total_cost = total_cost
                best_config = {
                    'order_size': actual_order_size,
                    'num_orders': num_orders,
                    'total_cost': total_cost,
                    'total_cost_bps': total_cost_bps,
                    'cost_per_order': cost_per_order
                }
        
        if best_config:
            logger.info(f"Optimized order size: {best_config['num_orders']} orders of {best_config['order_size']} "
                       f"(cost: {best_config['total_cost_bps']:.1f} bps)")
        else:
            logger.warning(f"Could not optimize order size within {max_cost_bps} bps limit")
        
        return best_config
    
    def get_cost_summary(self) -> Dict:
        """Get transaction cost summary"""
        if not self.optimization_history:
            return {
                'total_trades': 0,
                'total_costs': 0,
                'avg_cost_bps': 0,
                'cost_breakdown': {}
            }
        
        total_trades = len(self.optimization_history)
        total_costs = sum(record['total_cost'] for record in self.optimization_history)
        avg_cost_bps = np.mean([record['total_cost_bps'] for record in self.optimization_history])
        
        # Cost breakdown
        cost_breakdown = {
            'commission': sum(record['cost_breakdown']['commission'] for record in self.optimization_history),
            'slippage': sum(record['cost_breakdown']['slippage'] for record in self.optimization_history),
            'market_impact': sum(record['cost_breakdown']['market_impact'] for record in self.optimization_history)
        }
        
        return {
            'total_trades': total_trades,
            'total_costs': total_costs,
            'avg_cost_bps': avg_cost_bps,
            'cost_breakdown': cost_breakdown
        } 