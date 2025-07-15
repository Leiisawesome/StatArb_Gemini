"""
Market Impact and Slippage Models

Professional-grade models for estimating transaction costs and market impact
based on academic research and industry best practices.

Implements:
- Square-root market impact model (Almgren & Chriss)
- Temporary vs permanent impact decomposition
- Volatility-adjusted impact estimation
- Market microstructure considerations
- Regime-dependent impact modeling

Author: Pro Quant Desk Trader
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
from abc import ABC, abstractmethod


class MarketRegime(Enum):
    """Market regime classifications affecting transaction costs"""
    NORMAL = "normal"
    VOLATILE = "volatile"
    STRESSED = "stressed"
    ILLIQUID = "illiquid"


class ImpactType(Enum):
    """Types of market impact"""
    TEMPORARY = "temporary"
    PERMANENT = "permanent"
    TOTAL = "total"


@dataclass
class MarketConditions:
    """Current market conditions affecting execution quality"""
    volatility: float  # Recent volatility measure (annualized)
    volume: float      # Recent average volume (shares)
    spread: float      # Current bid-ask spread (fraction)
    price: float = 100.0  # Current price
    
    # Market microstructure
    order_book_depth: float = 1000.0  # Depth at best bid/ask
    tick_size: float = 0.01  # Minimum price increment
    
    # Timing factors
    time_to_close: float = 4.0  # Hours to market close
    is_opening: bool = False
    is_closing: bool = False
    
    # Regime classification
    regime: MarketRegime = MarketRegime.NORMAL
    
    def __post_init__(self):
        """Classify market regime based on conditions"""
        if self.volatility > 0.08:  # 8% daily volatility
            self.regime = MarketRegime.STRESSED
        elif self.volatility > 0.04:  # 4% daily volatility
            self.regime = MarketRegime.VOLATILE
        elif self.volume < 100_000:  # Low volume threshold
            self.regime = MarketRegime.ILLIQUID
        else:
            self.regime = MarketRegime.NORMAL


@dataclass
class ImpactEstimate:
    """Market impact estimation result"""
    temporary_impact: float = 0.0      # Temporary price impact (bps)
    permanent_impact: float = 0.0      # Permanent price impact (bps)
    total_impact: float = 0.0          # Total impact (bps)
    
    # Cost breakdown
    spread_cost: float = 0.0           # Bid-ask spread cost (bps)
    market_impact_cost: float = 0.0    # Market impact cost (bps)
    timing_cost: float = 0.0           # Timing/delay cost (bps)
    
    # Confidence metrics
    confidence_level: float = 0.95
    impact_volatility: float = 0.0     # Volatility of impact estimate
    
    def __post_init__(self):
        """Calculate derived fields"""
        self.total_impact = self.temporary_impact + self.permanent_impact
        self.market_impact_cost = self.total_impact


@dataclass
class TransactionCosts:
    """Comprehensive transaction cost breakdown"""
    # Direct costs
    commission: float = 0.0            # Fixed commission
    exchange_fees: float = 0.0         # Exchange fees
    regulatory_fees: float = 0.0       # SEC/FINRA fees
    
    # Market impact costs
    spread_cost: float = 0.0           # Bid-ask spread cost
    market_impact: float = 0.0         # Price impact
    slippage: float = 0.0             # Execution slippage
    
    # Timing costs
    timing_cost: float = 0.0           # Delay/timing cost
    opportunity_cost: float = 0.0      # Missed opportunity cost
    
    # Total costs
    total_cost: float = 0.0            # Total transaction cost
    
    def __post_init__(self):
        """Calculate total cost"""
        self.total_cost = (self.commission + self.exchange_fees + self.regulatory_fees +
                          self.spread_cost + self.market_impact + self.slippage +
                          self.timing_cost + self.opportunity_cost)


class BaseImpactModel(ABC):
    """Base class for market impact models"""
    
    @abstractmethod
    def estimate_impact(self, 
                       order_size: float,
                       market_conditions: MarketConditions,
                       **kwargs) -> ImpactEstimate:
        """Estimate market impact for given order"""
        pass


class SquareRootImpactModel(BaseImpactModel):
    """
    Square-root market impact model based on Almgren & Chriss (2000)
    
    Temporary Impact: I_temp = η * σ * (Q/V)^(1/2) * sign(Q)
    Permanent Impact: I_perm = γ * σ * (Q/V)^(1/2) * sign(Q)
    
    Where:
    - η: temporary impact coefficient
    - γ: permanent impact coefficient  
    - σ: volatility
    - Q: order size
    - V: average volume
    """
    
    def __init__(self, 
                 temp_impact_coeff: float = 0.5,     # η parameter
                 perm_impact_coeff: float = 0.1,     # γ parameter
                 volatility_scaling: float = 1.0,    # Volatility scaling
                 regime_adjustments: Optional[Dict[MarketRegime, float]] = None):
        """
        Initialize square-root impact model
        
        Args:
            temp_impact_coeff: Temporary impact coefficient (η)
            perm_impact_coeff: Permanent impact coefficient (γ)
            volatility_scaling: Volatility scaling factor
            regime_adjustments: Regime-specific adjustments
        """
        self.temp_impact_coeff = temp_impact_coeff
        self.perm_impact_coeff = perm_impact_coeff
        self.volatility_scaling = volatility_scaling
        
        # Default regime adjustments
        self.regime_adjustments = regime_adjustments or {
            MarketRegime.NORMAL: 1.0,
            MarketRegime.VOLATILE: 1.5,
            MarketRegime.STRESSED: 2.5,
            MarketRegime.ILLIQUID: 3.0
        }
        
        self.logger = logging.getLogger(__name__)
    
    def estimate_impact(self, 
                       order_size: float,
                       market_conditions: MarketConditions,
                       **kwargs) -> ImpactEstimate:
        """
        Estimate market impact using square-root model
        
        Args:
            order_size: Order size in shares (signed)
            market_conditions: Market conditions
            
        Returns:
            ImpactEstimate with impact breakdown
        """
        if order_size == 0 or market_conditions.volume == 0:
            return ImpactEstimate()
        
        # Calculate participation rate
        participation_rate = abs(order_size) / market_conditions.volume
        
        # Base impact calculation
        volatility_factor = market_conditions.volatility * self.volatility_scaling
        size_factor = np.sqrt(participation_rate)
        
        # Temporary impact
        temp_impact = (self.temp_impact_coeff * volatility_factor * size_factor) * 10000  # Convert to bps
        
        # Permanent impact
        perm_impact = (self.perm_impact_coeff * volatility_factor * size_factor) * 10000  # Convert to bps
        
        # Apply regime adjustment
        regime_mult = self.regime_adjustments.get(market_conditions.regime, 1.0)
        temp_impact *= regime_mult
        perm_impact *= regime_mult
        
        # Calculate spread cost
        spread_cost = market_conditions.spread * 10000 / 2  # Half-spread in bps
        
        # Calculate timing cost (based on volatility and time)
        timing_cost = self._calculate_timing_cost(market_conditions, **kwargs)
        
        # Impact volatility (uncertainty in estimate)
        impact_volatility = temp_impact * 0.3  # 30% uncertainty
        
        return ImpactEstimate(
            temporary_impact=temp_impact,
            permanent_impact=perm_impact,
            spread_cost=spread_cost,
            timing_cost=timing_cost,
            impact_volatility=impact_volatility
        )
    
    def _calculate_timing_cost(self, market_conditions: MarketConditions, **kwargs) -> float:
        """Calculate timing cost based on delay and volatility"""
        execution_time = kwargs.get('execution_time', 0.0)  # Hours
        
        if execution_time <= 0:
            return 0.0
        
        # Timing cost = volatility * sqrt(time) * timing_factor
        timing_factor = 0.1  # 10% of volatility per sqrt(hour)
        timing_cost = (market_conditions.volatility * np.sqrt(execution_time) * 
                      timing_factor) * 10000  # Convert to bps
        
        return timing_cost


class LinearImpactModel(BaseImpactModel):
    """
    Linear market impact model
    
    Impact = α * (Q/V) * σ
    
    Simpler model suitable for smaller orders
    """
    
    def __init__(self, 
                 impact_coeff: float = 0.1,
                 volatility_scaling: float = 1.0):
        """
        Initialize linear impact model
        
        Args:
            impact_coeff: Linear impact coefficient
            volatility_scaling: Volatility scaling factor
        """
        self.impact_coeff = impact_coeff
        self.volatility_scaling = volatility_scaling
        self.logger = logging.getLogger(__name__)
    
    def estimate_impact(self, 
                       order_size: float,
                       market_conditions: MarketConditions,
                       **kwargs) -> ImpactEstimate:
        """Estimate impact using linear model"""
        if order_size == 0 or market_conditions.volume == 0:
            return ImpactEstimate()
        
        # Calculate participation rate
        participation_rate = abs(order_size) / market_conditions.volume
        
        # Linear impact
        impact = (self.impact_coeff * participation_rate * 
                 market_conditions.volatility * self.volatility_scaling) * 10000
        
        # Assume 70% temporary, 30% permanent
        temp_impact = impact * 0.7
        perm_impact = impact * 0.3
        
        # Spread cost
        spread_cost = market_conditions.spread * 10000 / 2
        
        return ImpactEstimate(
            temporary_impact=temp_impact,
            permanent_impact=perm_impact,
            spread_cost=spread_cost
        )


class AdaptiveImpactModel(BaseImpactModel):
    """
    Adaptive impact model that learns from execution history
    
    Combines multiple models and adjusts based on observed impact
    """
    
    def __init__(self):
        """Initialize adaptive model"""
        self.square_root_model = SquareRootImpactModel()
        self.linear_model = LinearImpactModel()
        
        # Model weights (learned over time)
        self.model_weights = {
            'square_root': 0.7,
            'linear': 0.3
        }
        
        # Historical impact data for learning
        self.impact_history: List[Dict[str, Any]] = []
        self.learning_rate = 0.1
        
        self.logger = logging.getLogger(__name__)
    
    def estimate_impact(self, 
                       order_size: float,
                       market_conditions: MarketConditions,
                       **kwargs) -> ImpactEstimate:
        """Estimate impact using adaptive ensemble"""
        # Get estimates from both models
        sqrt_estimate = self.square_root_model.estimate_impact(order_size, market_conditions, **kwargs)
        linear_estimate = self.linear_model.estimate_impact(order_size, market_conditions, **kwargs)
        
        # Weighted combination
        temp_impact = (sqrt_estimate.temporary_impact * self.model_weights['square_root'] +
                      linear_estimate.temporary_impact * self.model_weights['linear'])
        
        perm_impact = (sqrt_estimate.permanent_impact * self.model_weights['square_root'] +
                      linear_estimate.permanent_impact * self.model_weights['linear'])
        
        spread_cost = max(sqrt_estimate.spread_cost, linear_estimate.spread_cost)
        
        return ImpactEstimate(
            temporary_impact=temp_impact,
            permanent_impact=perm_impact,
            spread_cost=spread_cost,
            impact_volatility=temp_impact * 0.4  # Higher uncertainty for adaptive model
        )
    
    def update_model(self, 
                    order_size: float,
                    market_conditions: MarketConditions,
                    observed_impact: float):
        """Update model weights based on observed impact"""
        # Get predictions from both models
        sqrt_pred = self.square_root_model.estimate_impact(order_size, market_conditions)
        linear_pred = self.linear_model.estimate_impact(order_size, market_conditions)
        
        # Calculate errors
        sqrt_error = abs(sqrt_pred.total_impact - observed_impact)
        linear_error = abs(linear_pred.total_impact - observed_impact)
        
        # Update weights (favor model with lower error)
        if sqrt_error < linear_error:
            self.model_weights['square_root'] += self.learning_rate * 0.1
            self.model_weights['linear'] -= self.learning_rate * 0.1
        else:
            self.model_weights['square_root'] -= self.learning_rate * 0.1
            self.model_weights['linear'] += self.learning_rate * 0.1
        
        # Normalize weights
        total_weight = sum(self.model_weights.values())
        for key in self.model_weights:
            self.model_weights[key] /= total_weight
        
        # Store history
        self.impact_history.append({
            'order_size': order_size,
            'market_conditions': market_conditions,
            'observed_impact': observed_impact,
            'sqrt_prediction': sqrt_pred.total_impact,
            'linear_prediction': linear_pred.total_impact,
            'timestamp': datetime.now()
        })
        
        # Keep only recent history
        if len(self.impact_history) > 1000:
            self.impact_history = self.impact_history[-1000:]


class MarketImpactModel:
    """
    Comprehensive market impact modeling system
    
    Features:
    - Multiple impact models (square-root, linear, adaptive)
    - Regime-dependent impact estimation
    - Transaction cost breakdown
    - Model selection and ensemble
    """
    
    def __init__(self, 
                 commission_rate: float = 0.0005,
                 default_model: str = "square_root"):
        """
        Initialize market impact model
        
        Args:
            commission_rate: Commission rate (fraction)
            default_model: Default impact model to use
        """
        self.commission_rate = commission_rate
        self.default_model = default_model
        
        # Initialize impact models
        self.models = {
            'square_root': SquareRootImpactModel(),
            'linear': LinearImpactModel(),
            'adaptive': AdaptiveImpactModel()
        }
        
        # Model selection logic
        self.model_selection_rules = {
            'small_orders': 'linear',      # < 5% of volume
            'large_orders': 'square_root', # > 20% of volume
            'normal_orders': 'adaptive'    # 5-20% of volume
        }
        
        self.logger = logging.getLogger(__name__)
    
    def estimate_execution_price(self, 
                               order_value: float,
                               current_price: float,
                               market_conditions: MarketConditions,
                               average_volume: float,
                               execution_time: float = 0.0) -> Tuple[float, TransactionCosts]:
        """
        Estimate execution price and transaction costs
        
        Args:
            order_value: Order value (signed, negative for sells)
            current_price: Current market price
            market_conditions: Market conditions
            average_volume: Average daily volume
            execution_time: Expected execution time (hours)
            
        Returns:
            Tuple of (execution_price, transaction_costs)
        """
        # Calculate order size in shares
        order_size = order_value / current_price
        
        # Select appropriate model
        model_name = self._select_model(order_size, market_conditions.volume)
        model = self.models[model_name]
        
        # Estimate impact
        impact_estimate = model.estimate_impact(
            order_size=order_size,
            market_conditions=market_conditions,
            execution_time=execution_time
        )
        
        # Calculate execution price
        impact_bps = impact_estimate.total_impact
        price_impact = current_price * (impact_bps / 10000)
        
        if order_value > 0:  # Buy order
            execution_price = current_price + price_impact
        else:  # Sell order
            execution_price = current_price - price_impact
        
        # Calculate transaction costs
        transaction_costs = TransactionCosts(
            commission=abs(order_value) * self.commission_rate,
            spread_cost=abs(order_value) * (impact_estimate.spread_cost / 10000),
            market_impact=abs(order_value) * (impact_estimate.market_impact_cost / 10000),
            timing_cost=abs(order_value) * (impact_estimate.timing_cost / 10000)
        )
        
        return execution_price, transaction_costs
    
    def _select_model(self, order_size: float, daily_volume: float) -> str:
        """Select appropriate impact model based on order characteristics"""
        if daily_volume == 0:
            return self.default_model
        
        participation_rate = abs(order_size) / daily_volume
        
        if participation_rate < 0.05:  # Small order
            return self.model_selection_rules['small_orders']
        elif participation_rate > 0.20:  # Large order
            return self.model_selection_rules['large_orders']
        else:  # Normal order
            return self.model_selection_rules['normal_orders']
    
    def calibrate_model(self, 
                       symbol: str,
                       historical_data: pd.DataFrame,
                       execution_data: pd.DataFrame):
        """
        Calibrate impact model parameters using historical data
        
        Args:
            symbol: Symbol to calibrate for
            historical_data: Historical price/volume data
            execution_data: Historical execution data
        """
        # This would implement model calibration using historical execution data
        # For now, we'll use default parameters
        self.logger.info(f"Model calibration for {symbol} - using default parameters")
    
    def get_model_performance(self) -> Dict[str, Any]:
        """Get performance metrics for impact models"""
        adaptive_model = self.models['adaptive']
        
        performance = {
            'total_predictions': len(adaptive_model.impact_history),
            'model_weights': dict(adaptive_model.model_weights),
            'recent_accuracy': self._calculate_recent_accuracy(adaptive_model.impact_history)
        }
        
        return performance
    
    def _calculate_recent_accuracy(self, history: List[Dict[str, Any]]) -> float:
        """Calculate recent prediction accuracy"""
        if len(history) < 10:
            return 0.0
        
        recent_history = history[-50:]  # Last 50 predictions
        errors = []
        
        for record in recent_history:
            observed = record['observed_impact']
            predicted = record['sqrt_prediction']  # Use square-root as baseline
            
            if observed != 0:
                error = abs(predicted - observed) / abs(observed)
                errors.append(error)
        
        return 1.0 - np.mean(errors) if errors else 0.0


# Convenience functions for common use cases
def estimate_market_conditions(price_data: pd.DataFrame, 
                             volume_data: pd.DataFrame,
                             current_price: float) -> MarketConditions:
    """
    Estimate market conditions from historical data
    
    Args:
        price_data: Historical price data
        volume_data: Historical volume data
        current_price: Current market price
        
    Returns:
        MarketConditions object
    """
    # Calculate volatility (20-day)
    returns = price_data.pct_change().dropna()
    volatility = returns.std() * np.sqrt(252)  # Annualized
    
    # Calculate average volume (20-day)
    avg_volume = volume_data.tail(20).mean()
    
    # Estimate spread (simplified)
    spread = 0.001  # 10 bps default
    
    return MarketConditions(
        volatility=volatility,
        volume=avg_volume,
        spread=spread,
        price=current_price
    )


def calculate_optimal_execution_schedule(total_quantity: float,
                                       market_conditions: MarketConditions,
                                       execution_horizon: float,
                                       risk_aversion: float = 0.5) -> List[Tuple[float, float]]:
    """
    Calculate optimal execution schedule using Almgren-Chriss framework
    
    Args:
        total_quantity: Total quantity to execute
        market_conditions: Market conditions
        execution_horizon: Execution horizon (hours)
        risk_aversion: Risk aversion parameter
        
    Returns:
        List of (time, quantity) tuples
    """
    # Simplified implementation - in practice would use full AC optimization
    num_slices = max(1, int(execution_horizon * 2))  # 30-minute slices
    slice_size = total_quantity / num_slices
    
    schedule = []
    for i in range(num_slices):
        time = (i + 1) * (execution_horizon / num_slices)
        schedule.append((time, slice_size))
    
    return schedule 