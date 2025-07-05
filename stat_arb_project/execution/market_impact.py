"""
Professional Market Impact and Slippage Modeling
Implements realistic execution costs for institutional trading.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class MarketImpactParams:
    """Market impact model parameters."""
    # Linear impact parameters
    linear_impact: float = 0.0001  # 1bp per $1M notional
    square_root_impact: float = 0.0005  # Square root model parameter
    
    # Temporary vs permanent impact
    temporary_impact_factor: float = 0.6  # 60% temporary, 40% permanent
    impact_decay_half_life: float = 10.0  # Minutes
    
    # Volume-based parameters
    avg_daily_volume_factor: float = 0.1  # Max 10% of ADV
    volume_impact_threshold: float = 0.05  # 5% of ADV triggers higher impact
    
    # Market conditions
    volatility_impact_multiplier: float = 1.5  # Higher vol = higher impact
    spread_impact_multiplier: float = 1.2  # Wider spreads = higher impact

class MarketImpactModel:
    """
    Professional market impact model incorporating:
    - Linear and square root impact models
    - Temporary vs permanent impact
    - Volume-based constraints
    - Market condition adjustments
    """
    
    def __init__(self, params: Optional[MarketImpactParams] = None):
        self.params = params or MarketImpactParams()
        self.impact_history = []
        
    def calculate_market_impact(self,
                              order_size: float,
                              current_price: float,
                              avg_daily_volume: float,
                              current_volatility: float,
                              current_spread: float,
                              market_conditions: str = 'normal') -> Dict[str, float]:
        """
        Calculate comprehensive market impact.
        
        Args:
            order_size: Order size in shares/contracts
            current_price: Current market price
            avg_daily_volume: Average daily volume
            current_volatility: Current volatility (annualized)
            current_spread: Current bid-ask spread
            market_conditions: 'normal', 'stressed', 'liquid'
            
        Returns:
            Market impact analysis
        """
        # Calculate notional value
        notional = order_size * current_price
        
        # Volume constraint check
        volume_ratio = order_size / avg_daily_volume
        if volume_ratio > self.params.avg_daily_volume_factor:
            logger.warning(f"Order size {volume_ratio:.2%} exceeds volume limit")
            return self._calculate_impact_with_volume_constraint(
                order_size, current_price, avg_daily_volume, current_volatility, current_spread
            )
        
        # Base impact calculation
        linear_impact = self._calculate_linear_impact(notional, current_price)
        sqrt_impact = self._calculate_square_root_impact(order_size, current_price, avg_daily_volume)
        
        # Combine impacts (Almgren-Chriss model)
        total_impact = linear_impact + sqrt_impact
        
        # Market condition adjustments
        condition_multiplier = self._get_market_condition_multiplier(market_conditions)
        volatility_adjustment = self._calculate_volatility_adjustment(current_volatility)
        spread_adjustment = self._calculate_spread_adjustment(current_spread)
        
        # Apply adjustments
        adjusted_impact = total_impact * condition_multiplier * volatility_adjustment * spread_adjustment
        
        # Split into temporary and permanent
        temporary_impact = adjusted_impact * self.params.temporary_impact_factor
        permanent_impact = adjusted_impact * (1 - self.params.temporary_impact_factor)
        
        # Calculate execution price
        execution_price = current_price * (1 + adjusted_impact)
        
        # Store impact history
        impact_record = {
            'timestamp': pd.Timestamp.now(),
            'order_size': order_size,
            'notional': notional,
            'current_price': current_price,
            'execution_price': execution_price,
            'total_impact': adjusted_impact,
            'temporary_impact': temporary_impact,
            'permanent_impact': permanent_impact,
            'volume_ratio': volume_ratio,
            'market_conditions': market_conditions
        }
        self.impact_history.append(impact_record)
        
        return {
            'execution_price': execution_price,
            'total_impact_bps': adjusted_impact * 10000,  # Convert to basis points
            'temporary_impact_bps': temporary_impact * 10000,
            'permanent_impact_bps': permanent_impact * 10000,
            'volume_ratio': volume_ratio,
            'impact_decay_time': self.params.impact_decay_half_life,
            'market_condition_multiplier': condition_multiplier
        }
    
    def _calculate_linear_impact(self, notional: float, current_price: float) -> float:
        """Calculate linear market impact."""
        return self.params.linear_impact * (notional / 1e6)  # Per $1M notional
    
    def _calculate_square_root_impact(self, order_size: float, current_price: float, avg_volume: float) -> float:
        """Calculate square root market impact."""
        volume_ratio = order_size / avg_volume
        return self.params.square_root_impact * np.sqrt(volume_ratio)
    
    def _calculate_impact_with_volume_constraint(self,
                                               order_size: float,
                                               current_price: float,
                                               avg_volume: float,
                                               volatility: float,
                                               spread: float) -> Dict[str, Any]:
        """Calculate impact when order size exceeds volume constraints."""
        max_order_size = avg_volume * self.params.avg_daily_volume_factor
        excess_ratio = order_size / max_order_size
        
        # Apply penalty for large orders
        penalty_multiplier = 1 + (excess_ratio - 1) * 2  # 2x penalty for excess
        
        # Calculate base impact with constrained size
        base_impact = self.calculate_market_impact(
            max_order_size, current_price, avg_volume, volatility, spread
        )
        
        # Apply penalty
        base_impact['total_impact_bps'] = float(base_impact['total_impact_bps'] * penalty_multiplier)
        base_impact['execution_price'] = float(current_price * (1 + base_impact['total_impact_bps'] / 10000))
        
        return base_impact
    
    def _get_market_condition_multiplier(self, market_conditions: str) -> float:
        """Get market condition multiplier."""
        multipliers = {
            'liquid': 0.8,
            'normal': 1.0,
            'stressed': 1.5,
            'crisis': 2.0
        }
        return multipliers.get(market_conditions, 1.0)
    
    def _calculate_volatility_adjustment(self, volatility: float) -> float:
        """Calculate volatility-based impact adjustment."""
        base_vol = 0.15  # 15% annual volatility baseline
        vol_ratio = volatility / base_vol
        return 1 + (vol_ratio - 1) * (self.params.volatility_impact_multiplier - 1)
    
    def _calculate_spread_adjustment(self, spread: float) -> float:
        """Calculate spread-based impact adjustment."""
        base_spread = 0.001  # 10bp baseline spread
        spread_ratio = spread / base_spread
        return 1 + (spread_ratio - 1) * (self.params.spread_impact_multiplier - 1)
    
    def estimate_impact_decay(self, initial_impact: float, time_minutes: float) -> float:
        """Estimate impact decay over time."""
        decay_factor = np.exp(-np.log(2) * time_minutes / self.params.impact_decay_half_life)
        return initial_impact * decay_factor
    
    def get_impact_statistics(self) -> Dict[str, float]:
        """Get market impact statistics."""
        if not self.impact_history:
            return {}
        
        impacts = [record['total_impact'] for record in self.impact_history]
        volume_ratios = [record['volume_ratio'] for record in self.impact_history]
        
        return {
            'avg_impact_bps': np.mean(impacts) * 10000,
            'max_impact_bps': np.max(impacts) * 10000,
            'impact_volatility': np.std(impacts) * 10000,
            'avg_volume_ratio': np.mean(volume_ratios),
            'total_orders': len(self.impact_history)
        }

class SlippageModel:
    """
    Slippage modeling for different order types and market conditions.
    """
    
    def __init__(self):
        self.slippage_params = {
            'market_order': 0.0005,  # 5bp for market orders
            'limit_order': 0.0001,   # 1bp for limit orders
            'stop_order': 0.0010,    # 10bp for stop orders
            'iceberg_order': 0.0002, # 2bp for iceberg orders
        }
    
    def calculate_slippage(self,
                          order_type: str,
                          order_size: float,
                          avg_volume: float,
                          market_volatility: float,
                          spread: float) -> float:
        """
        Calculate expected slippage for different order types.
        
        Args:
            order_type: Type of order
            order_size: Order size
            avg_volume: Average daily volume
            market_volatility: Market volatility
            spread: Bid-ask spread
            
        Returns:
            Expected slippage in basis points
        """
        base_slippage = self.slippage_params.get(order_type, 0.0005)
        
        # Volume adjustment
        volume_ratio = order_size / avg_volume
        volume_adjustment = np.sqrt(volume_ratio)
        
        # Volatility adjustment
        vol_adjustment = market_volatility / 0.15  # Normalized to 15% vol
        
        # Spread adjustment
        spread_adjustment = spread / 0.001  # Normalized to 10bp spread
        
        # Combine adjustments
        total_slippage = base_slippage * volume_adjustment * vol_adjustment * spread_adjustment
        
        return total_slippage * 10000  # Convert to basis points

class TransactionCostOptimizer:
    """
    Optimize transaction costs through smart order routing and timing.
    """
    
    def __init__(self, market_impact_model: MarketImpactModel, slippage_model: SlippageModel):
        self.impact_model = market_impact_model
        self.slippage_model = slippage_model
    
    def optimize_order_size(self,
                           target_notional: float,
                           current_price: float,
                           avg_volume: float,
                           volatility: float,
                           spread: float,
                           time_horizon: float = 60.0) -> Dict[str, Any]:
        """
        Optimize order size to minimize total transaction costs.
        
        Args:
            target_notional: Target notional value
            current_price: Current market price
            avg_volume: Average daily volume
            volatility: Market volatility
            spread: Bid-ask spread
            time_horizon: Trading time horizon in minutes
            
        Returns:
            Optimization results
        """
        target_shares = target_notional / current_price
        
        # Test different order sizes
        order_sizes = np.linspace(target_shares * 0.1, target_shares, 20)
        costs = []
        
        for size in order_sizes:
            # Calculate market impact
            impact_result = self.impact_model.calculate_market_impact(
                size, current_price, avg_volume, volatility, spread
            )
            
            # Calculate slippage
            slippage = self.slippage_model.calculate_slippage(
                'market_order', size, avg_volume, volatility, spread
            )
            
            # Total cost
            total_cost_bps = impact_result['total_impact_bps'] + slippage
            
            costs.append({
                'order_size': size,
                'notional': size * current_price,
                'total_cost_bps': total_cost_bps,
                'impact_cost_bps': impact_result['total_impact_bps'],
                'slippage_cost_bps': slippage
            })
        
        # Find optimal size
        optimal_idx = np.argmin([cost['total_cost_bps'] for cost in costs])
        optimal_result = costs[optimal_idx]
        
        return {
            'optimal_order_size': optimal_result['order_size'],
            'optimal_notional': optimal_result['notional'],
            'min_total_cost_bps': optimal_result['total_cost_bps'],
            'impact_cost_bps': optimal_result['impact_cost_bps'],
            'slippage_cost_bps': optimal_result['slippage_cost_bps'],
            'all_options': costs
        }
    
    def calculate_optimal_timing(self,
                                order_size: float,
                                avg_volume: float,
                                volatility: float,
                                spread: float) -> Dict[str, Any]:
        """
        Calculate optimal timing for order execution.
        
        Args:
            order_size: Order size
            avg_volume: Average daily volume
            volatility: Market volatility
            spread: Bid-ask spread
            
        Returns:
            Timing optimization results
        """
        # Volume-based timing
        volume_ratio = order_size / avg_volume
        if volume_ratio > 0.1:
            recommended_timing = 'extended'  # Spread over multiple hours
        elif volume_ratio > 0.05:
            recommended_timing = 'gradual'   # Spread over 1-2 hours
        else:
            recommended_timing = 'immediate' # Execute immediately
        
        # Volatility-based timing
        if volatility > 0.25:
            timing_adjustment = 'reduce_size'  # High vol = smaller orders
        elif volatility < 0.10:
            timing_adjustment = 'normal'
        else:
            timing_adjustment = 'normal'
        
        # Spread-based timing
        if spread > 0.002:  # 20bp spread
            spread_adjustment = 'wait_for_tighter_spread'
        else:
            spread_adjustment = 'execute_now'
        
        return {
            'recommended_timing': recommended_timing,
            'timing_adjustment': timing_adjustment,
            'spread_adjustment': spread_adjustment,
            'estimated_duration_minutes': self._estimate_execution_duration(order_size, avg_volume)
        }
    
    def _estimate_execution_duration(self, order_size: float, avg_volume: float) -> float:
        """Estimate execution duration in minutes."""
        volume_ratio = order_size / avg_volume
        if volume_ratio < 0.01:
            return 5.0  # 5 minutes for small orders
        elif volume_ratio < 0.05:
            return 30.0  # 30 minutes for medium orders
        else:
            return 120.0  # 2 hours for large orders 