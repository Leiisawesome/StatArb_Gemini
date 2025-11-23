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

Follows Rule 7 Section B (Liquidity Management) and Rule 2 (Regime-First Principle).

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
    
    Regime Awareness (Rule 2 Regime-First):
    - Execution costs scale with volatility regime
    - Impact multipliers: low_vol=0.8x, high_vol=1.3x, extreme=1.8x
    
    Liquidity Management (Rule 7 Section B):
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
        
        # Regime multipliers (Rule 2 Regime-First)
        self.regime_multipliers = self.config.get('regime_multipliers', {
            'low_volatility': 0.8,
            'normal_volatility': 1.0,
            'high_volatility': 1.3,
            'extreme_volatility': 1.8,
            'crisis': 2.5
        })
        
        # Liquidity adjustments (Rule 7 Section B)
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
        
        # Rejection simulation (for testing)
        self.disable_rejections = self.config.get('disable_rejections', False)
        
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
            regime_context: Market regime information (Rule 2 Regime-First)
            liquidity_score: Liquidity score 0-100 (Rule 7 Section B)
        
        Returns:
            SimulatedFill with realistic execution costs
        """
        
        try:
            # Extract market data first
            market_price = market_data.get('close', decision_price)
            volume = market_data.get('volume', 1000000)
            volatility = market_data.get('volatility', 0.02)
            decision_time = market_data.get('timestamp', datetime.now())
            
            # Ensure decision_time is a datetime object
            if isinstance(decision_time, (int, float)):
                decision_time = datetime.fromtimestamp(decision_time)
            elif isinstance(decision_time, str):
                try:
                    decision_time = datetime.fromisoformat(decision_time)
                except ValueError:
                    decision_time = datetime.now()
            
            # Skip simulation for zero quantity orders
            if quantity <= 0:
                logger.warning(f"⚠️ Skipping fill simulation for {symbol} {side} {quantity}: zero quantity")
                zero_costs = ExecutionCosts()
                return SimulatedFill(
                    symbol=symbol,
                    side=side,
                    quantity=0,
                    fill_price=market_price,
                    decision_price=decision_price,
                    market_price=market_price,
                    decision_time=decision_time,
                    execution_time=decision_time,
                    costs=zero_costs,
                    authorization_id=authorization_id,
                    strategy_id=strategy_id
                )
            
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
            
            # Step 4: Calculate commission (Asset-Class Aware)
            # Determine asset class from symbol or config
            try:
                from core_engine.data.market_calendar import MarketCalendar
                calendar = MarketCalendar()
                asset_class = calendar.get_asset_class(symbol)
                asset_class_name = asset_class.name
            except ImportError:
                asset_class_name = 'US_EQUITY'  # Fallback

            if asset_class_name == 'CRYPTO':
                # Crypto commission: percentage based (e.g., 10 bps = 0.1%)
                # Maker/Taker model could be added here
                commission_rate_bps = self.config.get('crypto_commission_bps', 10.0)
                commission_bps = commission_rate_bps
                commission_dollars = (commission_bps / 10000) * (quantity * market_price)
            else:
                # Equity commission: per-share based (e.g., $0.005/share)
                commission_dollars = quantity * self.commission_per_share
                if market_price > 0:
                    commission_bps = (commission_dollars / (quantity * market_price)) * 10000
                else:
                    commission_bps = 0.0
            
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
        - Volatility regime (Rule 2 Regime-First)
        - Liquidity conditions (Rule 7 Section B)
        """
        
        # Start with base spread
        spread_bps = self.base_spread_bps
        
        # Adjust for regime (Rule 2 Regime-First)
        if regime_context:
            volatility_regime = regime_context.get('volatility_regime', 'normal_volatility')
            regime_multiplier = self.regime_multipliers.get(volatility_regime, 1.0)
            spread_bps *= regime_multiplier
        
        # Adjust for liquidity (Rule 7 Section B)
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
        - Regime conditions (Rule 2 Regime-First)
        - Liquidity (Rule 7 Section B)
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
        
        # Adjust for regime (Rule 2 Regime-First)
        if regime_context:
            volatility_regime = regime_context.get('volatility_regime', 'normal_volatility')
            regime_multiplier = self.regime_multipliers.get(volatility_regime, 1.0)
            base_impact_bps *= regime_multiplier
        
        # Adjust for liquidity (Rule 7 Section B)
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
    
    # ========================================================================
    # SPRINT 0.3: ORDER REJECTION SIMULATION (GAP 4-3)
    # ========================================================================
    
    def simulate_rejection_scenario(self,
                                    symbol: str,
                                    side: str,
                                    quantity: float,
                                    market_data: Dict[str, Any],
                                    regime_context: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Simulate realistic order rejection scenarios for backtesting
        
        This method models the 8 common rejection patterns from OrderRejectionHandler:
        1. Insufficient margin
        2. Stock halted
        3. Price collar violation
        4. Connection timeout
        5. Duplicate order ID
        6. Market closed
        7. Position limit reached
        8. Unknown error
        
        Args:
            symbol: Trading symbol
            side: 'buy' or 'sell'
            quantity: Order quantity
            market_data: Current market data
            regime_context: Market regime (affects rejection probability)
        
        Returns:
            Rejection info dict if rejected, None if accepted
        """
        
        # Check if rejections are disabled (for testing)
        if self.disable_rejections:
            return None
        
        # Extract market conditions
        market_price = market_data.get('close', 100.0)
        volatility = market_data.get('volatility', 0.02)
        volume = market_data.get('volume', 1000000)
        
        # Get regime
        regime = 'normal_volatility'
        if regime_context:
            regime = regime_context.get('primary_regime', regime)
            if hasattr(regime, 'value'):
                regime = regime.value
        
        # Calculate rejection probability based on regime
        # More volatile regimes = higher rejection probability
        base_rejection_prob = {
            'low_volatility': 0.01,      # 1% rejection in calm markets
            'normal_volatility': 0.02,   # 2% rejection in normal markets
            'high_volatility': 0.05,     # 5% rejection in volatile markets
            'extreme_volatility': 0.10,  # 10% rejection in extreme vol
            'crisis': 0.20               # 20% rejection in crisis
        }.get(regime, 0.02)
        
        # Additional rejection factors
        if quantity * market_price > 1000000:  # Large orders ($1M+)
            base_rejection_prob *= 1.5
        
        if volume < 100000:  # Low volume stocks
            base_rejection_prob *= 1.3
        
        # Determine if order is rejected
        if np.random.random() < base_rejection_prob:
            # Order rejected - determine rejection reason
            rejection_reasons = [
                ('insufficient_margin', 0.15, 'Insufficient margin for trade'),
                ('stock_halted', 0.10, 'Stock trading halted'),
                ('price_collar', 0.20, 'Price outside collar limits'),
                ('connection_timeout', 0.25, 'Connection timeout to exchange'),
                ('duplicate_order_id', 0.05, 'Duplicate order ID'),
                ('market_closed', 0.05, 'Market closed'),
                ('position_limit', 0.10, 'Position limit reached'),
                ('unknown_error', 0.10, 'Unknown broker error')
            ]
            
            # Weighted random selection
            weights = [r[1] for r in rejection_reasons]
            reason_tuple = rejection_reasons[np.random.choice(len(rejection_reasons), p=weights)]
            
            rejection_info = {
                'rejected': True,
                'rejection_code': reason_tuple[0],
                'rejection_reason': reason_tuple[2],
                'rejection_severity': self._get_rejection_severity(reason_tuple[0]),
                'can_retry': self._can_retry_rejection(reason_tuple[0]),
                'suggested_action': self._get_suggested_action(reason_tuple[0], quantity),
                'timestamp': market_data.get('timestamp', datetime.now())
            }
            
            logger.info(f"🚫 Order REJECTED - {symbol} {side} {quantity}: {rejection_info['rejection_reason']}")
            return rejection_info
        
        # Order accepted
        return None
    
    def _get_rejection_severity(self, rejection_code: str) -> str:
        """Get severity level of rejection"""
        severity_map = {
            'insufficient_margin': 'MODERATE',
            'stock_halted': 'HIGH',
            'price_collar': 'MINOR',
            'connection_timeout': 'MINOR',
            'duplicate_order_id': 'MINOR',
            'market_closed': 'MODERATE',
            'position_limit': 'HIGH',
            'unknown_error': 'MODERATE'
        }
        return severity_map.get(rejection_code, 'MODERATE')
    
    def _can_retry_rejection(self, rejection_code: str) -> bool:
        """Determine if rejection can be retried"""
        retryable = {
            'insufficient_margin': True,   # Can retry with smaller quantity
            'stock_halted': False,         # Wait for resumption
            'price_collar': True,          # Can retry with adjusted price
            'connection_timeout': True,    # Can retry after delay
            'duplicate_order_id': True,    # Can retry with new ID
            'market_closed': False,        # Wait for market open
            'position_limit': False,       # Cannot exceed limit
            'unknown_error': True          # Can retry
        }
        return retryable.get(rejection_code, False)
    
    def _get_suggested_action(self, rejection_code: str, original_quantity: float) -> Dict[str, Any]:
        """Get suggested action for handling rejection"""
        actions = {
            'insufficient_margin': {
                'action': 'REDUCE_QUANTITY',
                'modified_quantity': original_quantity * 0.5,
                'retry_delay_seconds': 0,
                'max_retries': 3
            },
            'stock_halted': {
                'action': 'WAIT_FOR_RESUMPTION',
                'modified_quantity': original_quantity,
                'retry_delay_seconds': 300,  # 5 minutes
                'max_retries': 1
            },
            'price_collar': {
                'action': 'ADJUST_PRICE',
                'modified_quantity': original_quantity,
                'retry_delay_seconds': 5,
                'max_retries': 3
            },
            'connection_timeout': {
                'action': 'RETRY_WITH_BACKOFF',
                'modified_quantity': original_quantity,
                'retry_delay_seconds': 5,  # Exponential backoff
                'max_retries': 3
            },
            'duplicate_order_id': {
                'action': 'NEW_ORDER_ID',
                'modified_quantity': original_quantity,
                'retry_delay_seconds': 0,
                'max_retries': 1
            },
            'market_closed': {
                'action': 'CANCEL',
                'modified_quantity': 0,
                'retry_delay_seconds': 0,
                'max_retries': 0
            },
            'position_limit': {
                'action': 'ESCALATE',
                'modified_quantity': 0,
                'retry_delay_seconds': 0,
                'max_retries': 0
            },
            'unknown_error': {
                'action': 'ESCALATE',
                'modified_quantity': original_quantity,
                'retry_delay_seconds': 10,
                'max_retries': 1
            }
        }
        return actions.get(rejection_code, actions['unknown_error'])
    
    def simulate_fill_with_rejection(self,
                                     symbol: str,
                                     side: str,
                                     quantity: float,
                                     decision_price: float,
                                     market_data: Dict[str, Any],
                                     authorization_id: str = "",
                                     strategy_id: str = "",
                                     regime_context: Optional[Dict[str, Any]] = None,
                                     liquidity_score: Optional[float] = None,
                                     max_retries: int = 3) -> Dict[str, Any]:
        """
        Simulate fill with rejection handling and intelligent retries
        
        This is the complete simulation that includes:
        1. Initial rejection check
        2. Retry logic with modifications
        3. Final fill simulation if accepted
        
        Args:
            All standard simulate_fill args plus:
            max_retries: Maximum retry attempts
        
        Returns:
            Dict with 'fill' (SimulatedFill or None) and 'rejection_history'
        """
        
        rejection_history = []
        current_quantity = quantity
        retry_count = 0
        
        while retry_count <= max_retries:
            # Check for rejection
            rejection = self.simulate_rejection_scenario(
                symbol, side, current_quantity, market_data, regime_context
            )
            
            if rejection is None:
                # Order accepted - proceed with fill
                fill = self.simulate_fill(
                    symbol=symbol,
                    side=side,
                    quantity=current_quantity,
                    decision_price=decision_price,
                    market_data=market_data,
                    authorization_id=authorization_id,
                    strategy_id=strategy_id,
                    regime_context=regime_context,
                    liquidity_score=liquidity_score
                )
                
                return {
                    'success': True,
                    'fill': fill,
                    'rejection_history': rejection_history,
                    'retry_count': retry_count,
                    'final_quantity': current_quantity
                }
            
            # Order rejected - check if retryable
            rejection_history.append(rejection)
            
            if not rejection['can_retry'] or retry_count >= max_retries:
                # Cannot retry or max retries exceeded
                logger.warning(f"❌ Order FAILED after {retry_count} retries: {rejection['rejection_reason']}")
                return {
                    'success': False,
                    'fill': None,
                    'rejection_history': rejection_history,
                    'retry_count': retry_count,
                    'final_quantity': 0,
                    'failure_reason': rejection['rejection_reason']
                }
            
            # Apply suggested action
            suggested_action = rejection['suggested_action']
            action_type = suggested_action['action']
            
            if action_type == 'REDUCE_QUANTITY':
                current_quantity = suggested_action['modified_quantity']
                logger.info(f"🔄 Retry {retry_count + 1}: Reducing quantity to {current_quantity}")
            
            elif action_type == 'ADJUST_PRICE':
                # Price adjustment would happen here (simplified for backtest)
                logger.info(f"🔄 Retry {retry_count + 1}: Adjusting price")
            
            elif action_type == 'NEW_ORDER_ID':
                # New order ID (simulated)
                logger.info(f"🔄 Retry {retry_count + 1}: Generating new order ID")
            
            elif action_type == 'RETRY_WITH_BACKOFF':
                # Exponential backoff (simulated)
                delay = suggested_action['retry_delay_seconds'] * (2 ** retry_count)
                logger.info(f"🔄 Retry {retry_count + 1}: Waiting {delay}s (exponential backoff)")
            
            retry_count += 1
        
        # Max retries exceeded
        logger.error(f"❌ Order FAILED: Max retries ({max_retries}) exceeded")
        return {
            'success': False,
            'fill': None,
            'rejection_history': rejection_history,
            'retry_count': retry_count,
            'final_quantity': 0,
            'failure_reason': 'Max retries exceeded'
        }

