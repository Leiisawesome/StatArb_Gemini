"""
Historical Execution Simulator
==============================

Simulates realistic trade execution for backtesting with institutional-grade
transaction cost analysis (TCA).

This simulator applies realistic execution costs:
- Bid-ask spread costs
- Market impact (Almgren-Chriss model)
- Slippage (volatility-adjusted)
- Execution delays
- Partial fills (optional)

Follows Rule 12 (Liquidity Management) and Rule 13 (Regime-First Principle).

Author: StatArb_Gemini Backtest System
Version: 1.0.0
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import numpy as np
import logging

logger = logging.getLogger(__name__)


class FillModel(Enum):
    """Fill price models for historical simulation"""
    MIDPOINT = "midpoint"                      # Fill at mid price (no spread cost)
    MIDPOINT_PLUS_HALF_SPREAD = "midpoint_plus_half_spread"  # Mid + half spread
    WORST_CASE = "worst_case"                  # Fill at ask (buy) or bid (sell)
    REALISTIC = "realistic"                    # Spread + impact + slippage
    AGGRESSIVE = "aggressive"                  # Minimal cost (optimistic)


@dataclass
class ExecutionCosts:
    """Breakdown of execution costs"""
    
    # Cost components (in basis points)
    spread_cost_bps: float = 0.0          # Bid-ask spread cost
    market_impact_bps: float = 0.0        # Temporary + permanent impact
    slippage_bps: float = 0.0             # Additional slippage
    commission_bps: float = 0.0           # Commission/fees
    total_cost_bps: float = 0.0           # Total transaction cost
    
    # Cost breakdown (in currency)
    spread_cost_dollars: float = 0.0
    market_impact_dollars: float = 0.0
    slippage_dollars: float = 0.0
    commission_dollars: float = 0.0
    total_cost_dollars: float = 0.0
    
    # Impact components
    permanent_impact_bps: float = 0.0     # Permanent price impact
    temporary_impact_bps: float = 0.0     # Temporary impact (recovers)
    
    # Metadata
    fill_model: str = "realistic"
    regime: Optional[str] = None
    liquidity_score: Optional[float] = None


@dataclass
class SimulatedFill:
    """Simulated trade fill with realistic costs"""
    
    # Fill details
    symbol: str
    side: str                              # 'buy' or 'sell'
    quantity: float
    fill_price: float                      # Actual fill price (including costs)
    decision_price: float                  # Price when decision was made
    market_price: float                    # Mid-market price at execution
    
    # Timestamps
    decision_time: datetime
    execution_time: datetime
    
    # Cost breakdown
    costs: ExecutionCosts
    
    # Fill quality metrics
    implementation_shortfall_bps: float = 0.0  # Cost vs decision price
    arrival_cost_bps: float = 0.0              # Cost vs arrival price
    
    # Market conditions
    spread_bps: float = 0.0
    volatility: float = 0.0
    volume: float = 0.0
    
    # Metadata
    fill_id: str = ""
    authorization_id: str = ""
    strategy_id: str = ""


class HistoricalExecutionSimulator:
    """
    Simulates realistic trade execution for backtesting
    
    This simulator applies realistic execution costs based on market
    microstructure, liquidity conditions, and regime factors.
    
    Cost Models:
    - Spread Cost: Based on historical bid-ask spreads
    - Market Impact: Almgren-Chriss or Kyle's Lambda model
    - Slippage: Volatility-adjusted random slippage
    - Commission: Fixed per-share or percentage
    
    Regime Awareness (Rule 13):
    - Execution costs scale with volatility regime
    - Impact multipliers: low_vol=0.8x, high_vol=1.3x, extreme=1.8x
    
    Liquidity Management (Rule 12):
    - Higher costs in low liquidity conditions
    - Liquidity score affects spread and impact
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize historical execution simulator
        
        Args:
            config: Execution simulation configuration
        """
        self.config = config or {}
        
        # Fill model configuration
        self.fill_model = FillModel(self.config.get('fill_model', 'realistic'))
        
        # Cost model parameters
        self.base_spread_bps = self.config.get('base_spread_bps', 5.0)      # 5 bps base spread
        self.base_slippage_bps = self.config.get('base_slippage_bps', 2.0)  # 2 bps base slippage
        self.commission_per_share = self.config.get('commission_per_share', 0.005)  # $0.005/share
        
        # Market impact parameters (Almgren-Chriss)
        self.impact_linear_coeff = self.config.get('impact_linear_coeff', 0.1)
        self.impact_sqrt_coeff = self.config.get('impact_sqrt_coeff', 0.5)
        self.permanent_impact_ratio = self.config.get('permanent_impact_ratio', 0.3)  # 30% permanent
        
        # Regime multipliers (Rule 13)
        self.regime_multipliers = self.config.get('regime_multipliers', {
            'low_volatility': 0.8,
            'normal_volatility': 1.0,
            'high_volatility': 1.3,
            'extreme_volatility': 1.8,
            'crisis': 2.5
        })
        
        # Liquidity adjustments (Rule 12)
        self.liquidity_cost_multipliers = self.config.get('liquidity_multipliers', {
            'high': 0.8,      # High liquidity = lower costs
            'normal': 1.0,    # Normal liquidity = base costs
            'low': 1.3,       # Low liquidity = higher costs
            'illiquid': 1.8,  # Illiquid = much higher costs
            'crisis': 2.5     # Crisis liquidity = extreme costs
        })
        
        # Execution simulation settings
        self.enable_random_slippage = self.config.get('enable_random_slippage', True)
        self.slippage_std = self.config.get('slippage_std', 0.5)  # Std dev in bps
        
        # Timing
        self.execution_delay_seconds = self.config.get('execution_delay_seconds', 0)
        
        logger.info(f"✅ HistoricalExecutionSimulator initialized")
        logger.info(f"   Fill Model: {self.fill_model.value}")
        logger.info(f"   Base Spread: {self.base_spread_bps} bps")
        logger.info(f"   Base Slippage: {self.base_slippage_bps} bps")
        logger.info(f"   Commission: ${self.commission_per_share}/share")
        logger.info(f"   Impact Model: Almgren-Chriss (linear={self.impact_linear_coeff}, sqrt={self.impact_sqrt_coeff})")
    
    def simulate_fill(self,
                     symbol: str,
                     side: str,
                     quantity: float,
                     decision_price: float,
                     market_data: Dict[str, Any],
                     authorization_id: str = "",
                     strategy_id: str = "",
                     regime_context: Optional[Dict[str, Any]] = None,
                     liquidity_score: Optional[float] = None) -> SimulatedFill:
        """
        Simulate a realistic trade fill with transaction costs
        
        Args:
            symbol: Trading symbol
            side: 'buy' or 'sell'
            quantity: Number of shares
            decision_price: Price when trading decision was made
            market_data: Current market data (price, volume, volatility, etc.)
            authorization_id: Risk authorization ID
            strategy_id: Strategy that generated the trade
            regime_context: Market regime information (Rule 13)
            liquidity_score: Liquidity score 0-100 (Rule 12)
        
        Returns:
            SimulatedFill with realistic execution costs
        """
        
        try:
            # Extract market data
            market_price = market_data.get('close', decision_price)
            volume = market_data.get('volume', 1000000)
            volatility = market_data.get('volatility', 0.02)
            decision_time = market_data.get('timestamp', datetime.now())
            
            # Calculate execution time (with optional delay)
            execution_time = decision_time + timedelta(seconds=self.execution_delay_seconds)
            
            # Step 1: Calculate spread cost
            spread_cost_bps = self._calculate_spread_cost(
                symbol, market_price, regime_context, liquidity_score
            )
            
            # Step 2: Calculate market impact
            impact_result = self._calculate_market_impact(
                symbol, quantity, market_price, volume, volatility,
                regime_context, liquidity_score
            )
            market_impact_bps = impact_result['total_impact_bps']
            permanent_impact_bps = impact_result['permanent_impact_bps']
            temporary_impact_bps = impact_result['temporary_impact_bps']
            
            # Step 3: Calculate slippage
            slippage_bps = self._calculate_slippage(
                market_price, volatility, regime_context
            )
            
            # Step 4: Calculate commission
            commission_dollars = quantity * self.commission_per_share
            commission_bps = (commission_dollars / (quantity * market_price)) * 10000
            
            # Step 5: Calculate total cost in bps
            total_cost_bps = spread_cost_bps + market_impact_bps + slippage_bps + commission_bps
            
            # Step 6: Calculate fill price
            fill_price = self._calculate_fill_price(
                side, market_price, total_cost_bps
            )
            
            # Step 7: Calculate cost breakdown in dollars
            notional_value = quantity * market_price
            spread_cost_dollars = (spread_cost_bps / 10000) * notional_value
            market_impact_dollars = (market_impact_bps / 10000) * notional_value
            slippage_dollars = (slippage_bps / 10000) * notional_value
            total_cost_dollars = spread_cost_dollars + market_impact_dollars + slippage_dollars + commission_dollars
            
            # Step 8: Calculate fill quality metrics
            implementation_shortfall_bps = abs(fill_price - decision_price) / decision_price * 10000
            arrival_cost_bps = abs(fill_price - market_price) / market_price * 10000
            
            # Create execution costs breakdown
            costs = ExecutionCosts(
                spread_cost_bps=spread_cost_bps,
                market_impact_bps=market_impact_bps,
                slippage_bps=slippage_bps,
                commission_bps=commission_bps,
                total_cost_bps=total_cost_bps,
                spread_cost_dollars=spread_cost_dollars,
                market_impact_dollars=market_impact_dollars,
                slippage_dollars=slippage_dollars,
                commission_dollars=commission_dollars,
                total_cost_dollars=total_cost_dollars,
                permanent_impact_bps=permanent_impact_bps,
                temporary_impact_bps=temporary_impact_bps,
                fill_model=self.fill_model.value,
                regime=regime_context.get('primary_regime') if regime_context else None,
                liquidity_score=liquidity_score
            )
            
            # Create simulated fill
            fill = SimulatedFill(
                symbol=symbol,
                side=side,
                quantity=quantity,
                fill_price=fill_price,
                decision_price=decision_price,
                market_price=market_price,
                decision_time=decision_time,
                execution_time=execution_time,
                costs=costs,
                implementation_shortfall_bps=implementation_shortfall_bps,
                arrival_cost_bps=arrival_cost_bps,
                spread_bps=spread_cost_bps,
                volatility=volatility,
                volume=volume,
                fill_id=f"fill_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                authorization_id=authorization_id,
                strategy_id=strategy_id
            )
            
            logger.debug(f"Simulated {side.upper()} {quantity} {symbol} @ ${fill_price:.2f} "
                        f"(cost: {total_cost_bps:.1f} bps)")
            
            return fill
            
        except Exception as e:
            logger.error(f"Error simulating fill for {symbol}: {e}", exc_info=True)
            # Return fallback fill with conservative costs
            return self._create_fallback_fill(
                symbol, side, quantity, decision_price, market_data,
                authorization_id, strategy_id
            )
    
    def _calculate_spread_cost(self,
                              symbol: str,
                              price: float,
                              regime_context: Optional[Dict[str, Any]],
                              liquidity_score: Optional[float]) -> float:
        """
        Calculate bid-ask spread cost in basis points
        
        Spread cost is affected by:
        - Base spread (instrument specific)
        - Volatility regime (Rule 13)
        - Liquidity conditions (Rule 12)
        """
        
        # Start with base spread
        spread_bps = self.base_spread_bps
        
        # Adjust for regime (Rule 13)
        if regime_context:
            volatility_regime = regime_context.get('volatility_regime', 'normal_volatility')
            regime_multiplier = self.regime_multipliers.get(volatility_regime, 1.0)
            spread_bps *= regime_multiplier
        
        # Adjust for liquidity (Rule 12)
        if liquidity_score is not None:
            # Map liquidity score (0-100) to multiplier
            if liquidity_score >= 80:
                liquidity_regime = 'high'
            elif liquidity_score >= 60:
                liquidity_regime = 'normal'
            elif liquidity_score >= 40:
                liquidity_regime = 'low'
            else:
                liquidity_regime = 'illiquid'
            
            liquidity_multiplier = self.liquidity_cost_multipliers.get(liquidity_regime, 1.0)
            spread_bps *= liquidity_multiplier
        
        # Apply half-spread (we cross the spread)
        spread_cost = spread_bps / 2.0
        
        return max(spread_cost, 0.5)  # Minimum 0.5 bps
    
    def _calculate_market_impact(self,
                                symbol: str,
                                quantity: float,
                                price: float,
                                volume: float,
                                volatility: float,
                                regime_context: Optional[Dict[str, Any]],
                                liquidity_score: Optional[float]) -> Dict[str, float]:
        """
        Calculate market impact using Almgren-Chriss model
        
        Market impact has two components:
        - Permanent impact: Persistent price movement (30%)
        - Temporary impact: Recovers after trade (70%)
        
        Impact is affected by:
        - Order size relative to volume
        - Volatility
        - Regime conditions (Rule 13)
        - Liquidity (Rule 12)
        """
        
        # Calculate participation rate
        daily_volume = volume * 390  # Assume 390 1-min bars per day
        participation_rate = quantity / daily_volume if daily_volume > 0 else 0.01
        participation_rate = min(participation_rate, 1.0)  # Cap at 100%
        
        # Almgren-Chriss impact model
        linear_impact = self.impact_linear_coeff * participation_rate
        sqrt_impact = self.impact_sqrt_coeff * np.sqrt(participation_rate)
        base_impact_bps = (linear_impact + sqrt_impact) * 10000
        
        # Adjust for volatility
        volatility_adjustment = 1.0 + (volatility - 0.02) * 10  # Scale around 2% vol
        volatility_adjustment = max(0.5, min(volatility_adjustment, 2.0))  # Cap adjustment
        base_impact_bps *= volatility_adjustment
        
        # Adjust for regime (Rule 13)
        if regime_context:
            volatility_regime = regime_context.get('volatility_regime', 'normal_volatility')
            regime_multiplier = self.regime_multipliers.get(volatility_regime, 1.0)
            base_impact_bps *= regime_multiplier
        
        # Adjust for liquidity (Rule 12)
        if liquidity_score is not None:
            if liquidity_score >= 80:
                liquidity_multiplier = 0.8
            elif liquidity_score >= 60:
                liquidity_multiplier = 1.0
            elif liquidity_score >= 40:
                liquidity_multiplier = 1.3
            else:
                liquidity_multiplier = 1.8
            
            base_impact_bps *= liquidity_multiplier
        
        # Split into permanent and temporary
        permanent_impact_bps = base_impact_bps * self.permanent_impact_ratio
        temporary_impact_bps = base_impact_bps * (1.0 - self.permanent_impact_ratio)
        
        return {
            'total_impact_bps': base_impact_bps,
            'permanent_impact_bps': permanent_impact_bps,
            'temporary_impact_bps': temporary_impact_bps,
            'participation_rate': participation_rate
        }
    
    def _calculate_slippage(self,
                          price: float,
                          volatility: float,
                          regime_context: Optional[Dict[str, Any]]) -> float:
        """
        Calculate random slippage based on volatility
        
        Slippage represents additional execution uncertainty beyond
        spread and impact. It's modeled as a random variable scaled
        by volatility.
        """
        
        # Base slippage
        slippage_bps = self.base_slippage_bps
        
        # Scale by volatility (higher vol = more slippage)
        volatility_scaling = volatility / 0.02  # Normalize to 2% vol
        slippage_bps *= volatility_scaling
        
        # Add random component if enabled
        if self.enable_random_slippage:
            random_component = np.random.normal(0, self.slippage_std)
            slippage_bps += random_component
        
        # Ensure non-negative
        slippage_bps = max(slippage_bps, 0.0)
        
        return slippage_bps
    
    def _calculate_fill_price(self, side: str, market_price: float, total_cost_bps: float) -> float:
        """
        Calculate actual fill price including all costs
        
        For BUY orders: fill price is HIGHER (we pay more)
        For SELL orders: fill price is LOWER (we receive less)
        """
        
        cost_multiplier = total_cost_bps / 10000  # Convert bps to decimal
        
        if side.lower() == 'buy':
            # Pay more on buys
            fill_price = market_price * (1.0 + cost_multiplier)
        else:  # sell
            # Receive less on sells
            fill_price = market_price * (1.0 - cost_multiplier)
        
        return fill_price
    
    def _create_fallback_fill(self,
                             symbol: str,
                             side: str,
                             quantity: float,
                             decision_price: float,
                             market_data: Dict[str, Any],
                             authorization_id: str,
                             strategy_id: str) -> SimulatedFill:
        """Create a conservative fallback fill if simulation fails"""
        
        market_price = market_data.get('close', decision_price)
        decision_time = market_data.get('timestamp', datetime.now())
        
        # Conservative costs (worst case)
        conservative_cost_bps = 20.0  # 20 bps total
        fill_price = self._calculate_fill_price(side, market_price, conservative_cost_bps)
        
        costs = ExecutionCosts(
            spread_cost_bps=10.0,
            market_impact_bps=5.0,
            slippage_bps=3.0,
            commission_bps=2.0,
            total_cost_bps=conservative_cost_bps,
            fill_model="fallback"
        )
        
        return SimulatedFill(
            symbol=symbol,
            side=side,
            quantity=quantity,
            fill_price=fill_price,
            decision_price=decision_price,
            market_price=market_price,
            decision_time=decision_time,
            execution_time=decision_time,
            costs=costs,
            implementation_shortfall_bps=conservative_cost_bps,
            fill_id=f"fallback_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            authorization_id=authorization_id,
            strategy_id=strategy_id
        )
    
    def calculate_execution_quality_score(self, fill: SimulatedFill) -> float:
        """
        Calculate execution quality score (0-100)
        
        Higher score = better execution quality (lower costs)
        """
        
        # Cost-based scoring (inverse relationship)
        # 0 bps = 100 score, 50 bps = 0 score
        max_cost_bps = 50.0
        cost_score = max(0, 100 * (1 - fill.costs.total_cost_bps / max_cost_bps))
        
        return min(100, max(0, cost_score))
    
    def get_statistics(self, fills: List[SimulatedFill]) -> Dict[str, Any]:
        """
        Calculate aggregate statistics for multiple fills
        
        Returns:
            Dictionary with execution statistics and TCA metrics
        """
        
        if not fills:
            return {}
        
        # Aggregate costs
        total_costs_bps = [fill.costs.total_cost_bps for fill in fills]
        spread_costs_bps = [fill.costs.spread_cost_bps for fill in fills]
        impact_costs_bps = [fill.costs.market_impact_bps for fill in fills]
        slippage_costs_bps = [fill.costs.slippage_bps for fill in fills]
        
        # Aggregate dollars
        total_costs_dollars = sum(fill.costs.total_cost_dollars for fill in fills)
        
        # Execution quality scores
        quality_scores = [self.calculate_execution_quality_score(fill) for fill in fills]
        
        return {
            'total_fills': len(fills),
            'total_cost_dollars': total_costs_dollars,
            
            # Cost statistics (bps)
            'avg_total_cost_bps': np.mean(total_costs_bps),
            'median_total_cost_bps': np.median(total_costs_bps),
            'max_total_cost_bps': np.max(total_costs_bps),
            'min_total_cost_bps': np.min(total_costs_bps),
            
            # Component breakdown (bps)
            'avg_spread_cost_bps': np.mean(spread_costs_bps),
            'avg_impact_cost_bps': np.mean(impact_costs_bps),
            'avg_slippage_cost_bps': np.mean(slippage_costs_bps),
            
            # Execution quality
            'avg_execution_quality_score': np.mean(quality_scores),
            'median_execution_quality_score': np.median(quality_scores),
            
            # Fill breakdown
            'buy_fills': len([f for f in fills if f.side.lower() == 'buy']),
            'sell_fills': len([f for f in fills if f.side.lower() == 'sell']),
            
            # Total traded value
            'total_notional': sum(f.quantity * f.market_price for f in fills)
        }

