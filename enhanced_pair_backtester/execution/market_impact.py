"""
Market Impact and Slippage Models

Professional-grade models for estimating transaction costs and market impact
based on academic research and industry best practices.
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class MarketRegime(Enum):
    """Market regime classifications affecting transaction costs"""
    NORMAL = "normal"
    VOLATILE = "volatile"
    STRESSED = "stressed"


@dataclass
class MarketConditions:
    """Current market conditions affecting execution quality"""
    volatility: float  # Recent volatility measure
    volume: float      # Recent average volume
    spread: float      # Current bid-ask spread
    regime: MarketRegime = MarketRegime.NORMAL
    
    def __post_init__(self):
        """Classify market regime based on conditions"""
        if self.volatility > 0.05:  # 5% daily volatility
            self.regime = MarketRegime.STRESSED
        elif self.volatility > 0.03:  # 3% daily volatility
            self.regime = MarketRegime.VOLATILE
        else:
            self.regime = MarketRegime.NORMAL


@dataclass
class TransactionCosts:
    """Comprehensive transaction cost breakdown"""
    commission: float = 0.0      # Fixed commission per trade
    spread_cost: float = 0.0     # Bid-ask spread cost
    market_impact: float = 0.0   # Permanent market impact
    slippage: float = 0.0        # Temporary price impact
    total_cost: float = 0.0      # Total transaction cost
    
    def __post_init__(self):
        """Calculate total cost"""
        self.total_cost = self.commission + self.spread_cost + self.market_impact + self.slippage


class SlippageModel:
    """
    Advanced slippage model based on market microstructure research
    
    Implements square-root market impact model:
    Slippage = α * σ * sqrt(Q/V) * sign(Q)
    
    Where:
    - α: market impact coefficient
    - σ: volatility
    - Q: order quantity
    - V: average volume
    """
    
    def __init__(self, 
                 base_impact: float = 0.0001,  # 1 bp base impact
                 volatility_scaling: float = 1.0,
                 volume_scaling: float = 0.5):
        """
        Initialize slippage model parameters
        
        Args:
            base_impact: Base market impact coefficient
            volatility_scaling: How much volatility affects slippage
            volume_scaling: Square root scaling for volume impact
        """
        self.base_impact = base_impact
        self.volatility_scaling = volatility_scaling
        self.volume_scaling = volume_scaling
    
    def calculate_slippage(self, 
                          order_value: float,
                          market_conditions: MarketConditions,
                          average_volume: float) -> float:
        """
        Calculate slippage for a given order
        
        Args:
            order_value: Dollar value of the order
            market_conditions: Current market conditions
            average_volume: Average daily volume in dollars
            
        Returns:
            Slippage as fraction of order value
        """
        if order_value == 0 or average_volume == 0:
            return 0.0
            
        # Volume participation rate
        participation_rate = abs(order_value) / average_volume
        
        # Base slippage with square root scaling
        base_slippage = self.base_impact * np.sqrt(participation_rate)
        
        # Volatility adjustment
        volatility_adj = 1.0 + self.volatility_scaling * market_conditions.volatility
        
        # Regime adjustment
        regime_multiplier = {
            MarketRegime.NORMAL: 1.0,
            MarketRegime.VOLATILE: 1.5,
            MarketRegime.STRESSED: 2.5
        }
        
        total_slippage = (base_slippage * 
                         volatility_adj * 
                         regime_multiplier[market_conditions.regime])
        
        return min(total_slippage, 0.01)  # Cap at 1%


class MarketImpactModel:
    """
    Comprehensive market impact model for pairs trading
    
    Combines:
    - Temporary impact (slippage)
    - Permanent impact (information content)
    - Spread costs
    - Commission costs
    """
    
    def __init__(self, 
                 commission_rate: float = 0.001,  # 10 bps commission
                 spread_capture: float = 0.5,     # Capture 50% of spread
                 permanent_impact: float = 0.0002): # 2 bps permanent impact
        """
        Initialize market impact model
        
        Args:
            commission_rate: Commission as fraction of trade value
            spread_capture: Fraction of bid-ask spread captured
            permanent_impact: Permanent market impact coefficient
        """
        self.commission_rate = commission_rate
        self.spread_capture = spread_capture
        self.permanent_impact = permanent_impact
        self.slippage_model = SlippageModel()
    
    def calculate_transaction_costs(self,
                                  order_value: float,
                                  market_conditions: MarketConditions,
                                  average_volume: float,
                                  price: float) -> TransactionCosts:
        """
        Calculate comprehensive transaction costs
        
        Args:
            order_value: Dollar value of the order
            market_conditions: Current market conditions
            average_volume: Average daily volume
            price: Current price
            
        Returns:
            TransactionCosts object with detailed breakdown
        """
        abs_order_value = abs(order_value)
        
        # Commission cost
        commission = abs_order_value * self.commission_rate
        
        # Spread cost
        spread_cost = abs_order_value * market_conditions.spread * self.spread_capture
        
        # Market impact (permanent)
        market_impact = abs_order_value * self.permanent_impact
        
        # Slippage (temporary impact)
        slippage_rate = self.slippage_model.calculate_slippage(
            order_value, market_conditions, average_volume
        )
        slippage = abs_order_value * slippage_rate
        
        return TransactionCosts(
            commission=commission,
            spread_cost=spread_cost,
            market_impact=market_impact,
            slippage=slippage
        )
    
    def estimate_execution_price(self,
                               order_value: float,
                               current_price: float,
                               market_conditions: MarketConditions,
                               average_volume: float) -> Tuple[float, TransactionCosts]:
        """
        Estimate execution price including all costs
        
        Args:
            order_value: Dollar value of the order (positive for buy, negative for sell)
            current_price: Current market price
            market_conditions: Current market conditions
            average_volume: Average daily volume
            
        Returns:
            Tuple of (execution_price, transaction_costs)
        """
        costs = self.calculate_transaction_costs(
            order_value, market_conditions, average_volume, current_price
        )
        
        # Adjust price for market impact and slippage
        # Buy orders: price goes up, sell orders: price goes down
        price_impact = (costs.market_impact + costs.slippage) / abs(order_value)
        if order_value > 0:  # Buy order
            execution_price = current_price * (1 + price_impact)
        else:  # Sell order
            execution_price = current_price * (1 - price_impact)
        
        return execution_price, costs


def estimate_market_conditions(price_data: pd.DataFrame,
                             volume_data: Optional[pd.DataFrame] = None,
                             lookback_days: int = 20) -> MarketConditions:
    """
    Estimate current market conditions from price data
    
    Args:
        price_data: DataFrame with price data
        volume_data: Optional DataFrame with volume data
        lookback_days: Number of days to look back for calculations
        
    Returns:
        MarketConditions object
    """
    # Calculate volatility (annualized)
    returns = price_data.pct_change().dropna()
    volatility = float(returns.tail(lookback_days).std() * np.sqrt(252))
    
    # Estimate average volume (use price-based proxy if volume not available)
    if volume_data is not None:
        avg_volume = float(volume_data.tail(lookback_days).mean())
    else:
        # Use price * synthetic volume proxy
        avg_volume = float(price_data.tail(lookback_days).mean()) * 1000000  # $1M synthetic volume
    
    # Estimate spread (use volatility-based proxy)
    spread = max(0.001, volatility * 0.1)  # 10% of volatility as spread proxy
    
    return MarketConditions(
        volatility=volatility,
        volume=avg_volume,
        spread=spread
    ) 