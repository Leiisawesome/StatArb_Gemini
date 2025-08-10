"""
Transaction Cost Optimization Module - Phase 1 Enhancement
Implements cost-aware signal filtering and trade size optimization
"""

import logging
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class CostConfig:
    """Configuration for transaction cost optimization"""
    # Commission settings
    commission_rate: float = 0.0005  # 5 bps commission
    min_commission: float = 1.0      # Minimum commission per trade ($1)
    max_commission: float = 50.0     # Maximum commission per trade ($50)
    
    # Slippage settings
    slippage_bps: float = 2.0        # 2 bps slippage
    slippage_volatility_multiplier: float = 1.5  # Slippage increases with volatility
    
    # Minimum profit thresholds - PHASE 4 OPTIMIZATION (QUALITY FOCUS)
    min_net_return_bps: float = 10.0   # Increased from 5.0 to 10.0 bps for quality trades
    min_trade_size_usd: float = 50.0   # Increased from 25.0 to 50.0 USD for meaningful trades
    
    # Cost optimization
    enable_cost_optimization: bool = True
    require_positive_net_return: bool = True

class TransactionCostOptimizer:
    """Optimize trades considering transaction costs"""
    
    def __init__(self, config: Optional[CostConfig] = None):
        self.config = config or CostConfig()
        self.trade_cost_history = []
        self.cost_metrics = {
            'total_commission': 0.0,
            'total_slippage': 0.0,
            'total_trades': 0,
            'avg_commission': 0.0,
            'avg_slippage': 0.0
        }
    
    def calculate_expected_net_return(
        self,
        signal: Dict[str, Any],
        position_value: float,
        current_volatility: float = 0.02
    ) -> float:
        """
        Calculate expected return after transaction costs
        
        Args:
            signal: Trading signal dictionary
            position_value: Position value in USD
            current_volatility: Current market volatility
        
        Returns:
            Expected net return as a decimal (e.g., 0.02 for 2%)
        """
        try:
            # Extract signal parameters
            confidence = signal.get('confidence', 0.0)
            expected_return = signal.get('expected_return', 0.0)
            
            # Calculate gross expected return
            gross_return = confidence * expected_return
            
            # Calculate transaction costs
            commission_cost = self._calculate_commission_cost(position_value)
            slippage_cost = self._calculate_slippage_cost(position_value, current_volatility)
            total_cost = commission_cost + slippage_cost
            
            # Convert costs to return percentage
            cost_as_return = total_cost / position_value
            
            # Net expected return
            net_return = gross_return - cost_as_return
            
            logger.debug(f"Cost calculation: gross_return={gross_return:.4f}, "
                        f"commission={commission_cost:.2f}, slippage={slippage_cost:.2f}, "
                        f"total_cost={total_cost:.2f}, net_return={net_return:.4f}")
            
            return net_return
            
        except Exception as e:
            logger.error(f"Net return calculation failed: {e}")
            return 0.0
    
    def should_execute_trade(
        self,
        signal: Dict[str, Any],
        position_value: float,
        current_volatility: float = 0.02,
        min_net_return: Optional[float] = None
    ) -> bool:
        """
        Determine if trade should be executed after considering costs
        
        Args:
            signal: Trading signal dictionary
            position_value: Position value in USD
            current_volatility: Current market volatility
            min_net_return: Minimum required net return (default from config)
        
        Returns:
            True if trade should be executed
        """
        try:
            if not self.config.enable_cost_optimization:
                return True
            
            # Check minimum trade size
            if position_value < self.config.min_trade_size_usd:
                logger.debug(f"Trade rejected: position_value ${position_value:.2f} < min_size ${self.config.min_trade_size_usd}")
                return False
            
            # Calculate expected net return
            net_return = self.calculate_expected_net_return(signal, position_value, current_volatility)
            
            # Use provided threshold or default
            threshold = min_net_return or (self.config.min_net_return_bps / 10000)  # Convert bps to decimal
            
            # Check if net return exceeds minimum threshold
            should_execute = net_return > threshold
            
            if not should_execute:
                logger.debug(f"Trade rejected: net_return {net_return:.4f} < threshold {threshold:.4f}")
            
            return should_execute
            
        except Exception as e:
            logger.error(f"Trade execution check failed: {e}")
            return False  # Conservative: don't trade if we can't calculate costs
    
    def optimize_trade_size(
        self,
        signal: Dict[str, Any],
        available_capital: float,
        current_volatility: float = 0.02,
        fixed_costs: Optional[float] = None
    ) -> float:
        """
        Optimize trade size considering fixed and variable costs
        
        Args:
            signal: Trading signal dictionary
            available_capital: Available capital for trading
            current_volatility: Current market volatility
            fixed_costs: Fixed costs per trade (default from config)
        
        Returns:
            Optimized position size as fraction of capital
        """
        try:
            # Use default fixed costs if not provided
            fixed_costs = fixed_costs or self.config.min_commission
            
            # Calculate minimum trade size to cover fixed costs
            expected_return = signal.get('expected_return', 0.02)  # Default 2%
            min_return_needed = fixed_costs / available_capital
            
            if expected_return <= 0:
                return 0.0
            
            # Minimum trade size to be economical
            min_trade_size = min_return_needed / expected_return
            
            # Get base position size from signal
            base_size = signal.get('position_size', 0.1)  # Default 10%
            
            # Ensure trade size is economical
            optimal_size = max(min_trade_size, base_size)
            
            # Apply volatility adjustment
            if current_volatility > 0.05:  # High volatility
                optimal_size *= 0.8  # Reduce size in high volatility
            
            # Apply bounds
            final_size = max(0.01, min(0.15, optimal_size))  # Between 1% and 15%
            
            logger.debug(f"Trade size optimization: base_size={base_size:.3f}, "
                        f"min_size={min_trade_size:.3f}, optimal_size={optimal_size:.3f}, "
                        f"final_size={final_size:.3f}")
            
            return final_size
            
        except Exception as e:
            logger.error(f"Trade size optimization failed: {e}")
            return 0.05  # Conservative 5% default
    
    def _calculate_commission_cost(self, position_value: float) -> float:
        """Calculate commission cost for a trade"""
        commission = position_value * self.config.commission_rate
        return max(self.config.min_commission, min(commission, self.config.max_commission))
    
    def _calculate_slippage_cost(
        self, 
        position_value: float, 
        current_volatility: float
    ) -> float:
        """Calculate slippage cost based on position size and volatility"""
        # Base slippage
        base_slippage = position_value * (self.config.slippage_bps / 10000)
        
        # Volatility adjustment
        vol_adjustment = 1.0 + (current_volatility - 0.02) * self.config.slippage_volatility_multiplier
        vol_adjustment = max(0.5, min(2.0, vol_adjustment))  # Bound between 0.5x and 2x
        
        return base_slippage * vol_adjustment
    
    def update_cost_metrics(self, trade_result: Dict[str, Any]) -> None:
        """Update cost metrics based on completed trade"""
        try:
            commission = trade_result.get('commission', 0.0)
            slippage = trade_result.get('slippage', 0.0)
            
            # Update totals
            self.cost_metrics['total_commission'] += commission
            self.cost_metrics['total_slippage'] += slippage
            self.cost_metrics['total_trades'] += 1
            
            # Update averages
            if self.cost_metrics['total_trades'] > 0:
                self.cost_metrics['avg_commission'] = (
                    self.cost_metrics['total_commission'] / self.cost_metrics['total_trades']
                )
                self.cost_metrics['avg_slippage'] = (
                    self.cost_metrics['total_slippage'] / self.cost_metrics['total_trades']
                )
            
            # Store trade cost record
            self.trade_cost_history.append({
                'timestamp': trade_result.get('timestamp'),
                'commission': commission,
                'slippage': slippage,
                'total_cost': commission + slippage,
                'position_value': trade_result.get('position_value', 0.0)
            })
            
            logger.debug(f"Updated cost metrics: avg_commission=${self.cost_metrics['avg_commission']:.2f}, "
                        f"avg_slippage=${self.cost_metrics['avg_slippage']:.2f}")
            
        except Exception as e:
            logger.error(f"Failed to update cost metrics: {e}")
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Get current cost metrics summary"""
        return {
            'total_commission': self.cost_metrics['total_commission'],
            'total_slippage': self.cost_metrics['total_slippage'],
            'total_trades': self.cost_metrics['total_trades'],
            'avg_commission': self.cost_metrics['avg_commission'],
            'avg_slippage': self.cost_metrics['avg_slippage'],
            'total_costs': self.cost_metrics['total_commission'] + self.cost_metrics['total_slippage'],
            'cost_per_trade': (
                (self.cost_metrics['total_commission'] + self.cost_metrics['total_slippage']) /
                self.cost_metrics['total_trades']
                if self.cost_metrics['total_trades'] > 0 else 0.0
            )
        }
