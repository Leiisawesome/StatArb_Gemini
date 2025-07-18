"""
Transaction Cost Optimization System

Professional-grade transaction cost estimation and optimization with:
- Broker-specific commission structures
- Real-time cost estimation
- Maker-taker rebate optimization
- Volume-based tier optimization
- Multi-venue routing optimization
- Timing optimization

Author: Pro Quant Desk Trader
"""

import numpy as np
import pandas as pd
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import logging
from abc import ABC, abstractmethod


class BrokerType(Enum):
    """Broker categories with different pricing structures"""
    PRIME_BROKERAGE = "prime_brokerage"      # Goldman, Morgan Stanley, etc.
    INSTITUTIONAL_ECN = "institutional_ecn"   # BATS, ARCA, etc.
    RETAIL_PRO = "retail_pro"                # Interactive Brokers Pro
    RETAIL_STANDARD = "retail_standard"      # TD Ameritrade, Schwab
    CRYPTO_EXCHANGE = "crypto_exchange"      # Binance, Coinbase Pro
    DARK_POOL = "dark_pool"                  # Liquidnet, ITG POSIT


class VenueType(Enum):
    """Execution venue types"""
    EXCHANGE = "exchange"
    ECN = "ecn"
    DARK_POOL = "dark_pool"
    MARKET_MAKER = "market_maker"
    CROSSING_NETWORK = "crossing_network"


class OrderType(Enum):
    """Order types with different cost structures"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    ICEBERG = "iceberg"
    TWAP = "twap"
    VWAP = "vwap"
    IMPLEMENTATION_SHORTFALL = "implementation_shortfall"


@dataclass
class BrokerCommissionStructure:
    """Broker commission structure definition"""
    broker_name: str
    broker_type: BrokerType
    
    # Basic commission structure
    per_share_rate: float = 0.001        # Per share rate
    min_per_trade: float = 1.0           # Minimum per trade
    max_per_trade: float = 0.0           # Maximum per trade (0 = no max)
    
    # Maker-taker structure
    maker_rebate: float = 0.0            # Rebate for adding liquidity
    taker_fee: float = 0.0               # Fee for removing liquidity
    
    # Additional fees
    regulatory_fees: float = 0.0000221   # SEC fee (per dollar)
    clearing_fees: float = 0.0001        # Clearing fees (per share)
    
    # Volume tiers (monthly volume -> rates)
    volume_tiers: Dict[int, Dict[str, float]] = field(default_factory=dict)
    
    # Special rates
    etf_rate: float = 0.0                # Special ETF rate
    options_rate: float = 0.65           # Options rate (per contract)
    
    # Borrowing costs (for short selling)
    base_borrow_rate: float = 0.01       # Base borrow rate
    hard_to_borrow_premium: float = 0.0  # HTB premium
    
    def get_effective_rate(self, monthly_volume: int, is_maker: bool = False) -> float:
        """Get effective rate based on volume tier"""
        # Find applicable tier
        applicable_tier = None
        for tier_volume in sorted(self.volume_tiers.keys()):
            if monthly_volume >= tier_volume:
                applicable_tier = self.volume_tiers[tier_volume]
        
        if applicable_tier:
            if is_maker and 'maker_rebate' in applicable_tier:
                return -applicable_tier['maker_rebate']  # Negative for rebate
            elif not is_maker and 'taker_fee' in applicable_tier:
                return applicable_tier['taker_fee']
            elif 'per_share_rate' in applicable_tier:
                return applicable_tier['per_share_rate']
        
        # Default rates
        if is_maker:
            return -self.maker_rebate  # Negative for rebate
        else:
            return self.taker_fee if self.taker_fee > 0 else self.per_share_rate


@dataclass
class VenueCharacteristics:
    """Execution venue characteristics"""
    venue_name: str
    venue_type: VenueType
    
    # Liquidity characteristics
    average_spread: float = 0.001        # Average bid-ask spread
    depth_at_touch: float = 1000.0       # Average depth at best bid/ask
    fill_probability: float = 0.95       # Probability of fill
    
    # Cost structure
    maker_rebate: float = 0.0002         # Maker rebate (per share)
    taker_fee: float = 0.0030           # Taker fee (per share)
    
    # Execution quality
    average_improvement: float = 0.0001  # Average price improvement
    market_impact_factor: float = 1.0    # Market impact multiplier
    
    # Operational
    latency: float = 0.5                 # Average latency (ms)
    uptime: float = 0.999               # Uptime percentage
    
    # Access requirements
    min_order_size: int = 1             # Minimum order size
    max_order_size: int = 1_000_000     # Maximum order size
    
    def get_expected_cost(self, order_size: int, is_aggressive: bool = True) -> float:
        """Calculate expected cost for order"""
        if is_aggressive:
            # Aggressive order (market/marketable limit)
            cost = self.taker_fee + self.average_spread / 2
        else:
            # Passive order (limit at/better than NBBO)
            cost = -self.maker_rebate + self.average_improvement
        
        return cost * order_size


@dataclass
class CostOptimizationResult:
    """Result of cost optimization"""
    recommended_broker: str
    recommended_venue: str
    recommended_order_type: OrderType
    estimated_cost: float
    estimated_savings: float
    
    # Detailed breakdown
    commission_cost: float = 0.0
    market_impact_cost: float = 0.0
    spread_cost: float = 0.0
    timing_cost: float = 0.0
    opportunity_cost: float = 0.0
    
    # Alternative options
    alternatives: List[Dict[str, Any]] = field(default_factory=list)
    
    # Confidence metrics
    confidence_level: float = 0.8
    cost_volatility: float = 0.0


class TransactionCostOptimizer:
    """
    Professional transaction cost optimization system
    
    Features:
    - Broker-specific commission structures
    - Real-time cost estimation
    - Maker-taker rebate optimization
    - Volume-based tier optimization
    - Multi-venue routing optimization
    - Timing optimization
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.broker_structures = self._initialize_broker_structures()
        self.venue_characteristics = self._initialize_venue_characteristics()
        self.market_data_cache = {}
        self.volume_tracking = {}  # Track monthly volumes for tier calculation
        
    def _initialize_broker_structures(self) -> Dict[str, BrokerCommissionStructure]:
        """Initialize broker commission structures"""
        
        structures = {}
        
        # Prime Brokerage (Goldman Sachs example)
        structures['goldman_sachs'] = BrokerCommissionStructure(
            broker_name="Goldman Sachs",
            broker_type=BrokerType.PRIME_BROKERAGE,
            per_share_rate=0.002,  # $0.002 per share
            min_per_trade=5.0,
            max_per_trade=0.0,  # No maximum
            maker_rebate=0.0002,   # $0.0002 per share rebate
            taker_fee=0.003,       # $0.003 per share fee
            regulatory_fees=0.0000221,  # SEC fee
            clearing_fees=0.0002,
            volume_tiers={
                1_000_000: {'per_share_rate': 0.0018, 'maker_rebate': 0.00025},
                10_000_000: {'per_share_rate': 0.0015, 'maker_rebate': 0.0003},
                100_000_000: {'per_share_rate': 0.001, 'maker_rebate': 0.00035}
            },
            base_borrow_rate=0.015,  # 1.5% base borrow rate
            hard_to_borrow_premium=0.05  # 5% HTB premium
        )
        
        # Institutional ECN (Interactive Brokers Pro)
        structures['interactive_brokers'] = BrokerCommissionStructure(
            broker_name="Interactive Brokers Pro",
            broker_type=BrokerType.INSTITUTIONAL_ECN,
            per_share_rate=0.0005,  # $0.0005 per share
            min_per_trade=1.0,
            max_per_trade=1.0,  # 1% of trade value
            maker_rebate=0.0001,
            taker_fee=0.0025,
            regulatory_fees=0.0000221,
            clearing_fees=0.0001,
            volume_tiers={
                300_000: {'per_share_rate': 0.0003},
                3_000_000: {'per_share_rate': 0.0002},
                20_000_000: {'per_share_rate': 0.0001}
            },
            base_borrow_rate=0.0183,  # 1.83% base rate
            hard_to_borrow_premium=0.0
        )
        
        # Retail Standard (TD Ameritrade example)
        structures['td_ameritrade'] = BrokerCommissionStructure(
            broker_name="TD Ameritrade",
            broker_type=BrokerType.RETAIL_STANDARD,
            per_share_rate=0.0,  # Commission-free
            min_per_trade=0.0,
            max_per_trade=0.0,
            maker_rebate=0.0,
            taker_fee=0.0,
            regulatory_fees=0.0000221,
            clearing_fees=0.0,
            base_borrow_rate=0.0925,  # 9.25% base rate
            hard_to_borrow_premium=0.0
        )
        
        # Crypto Exchange (Binance example)
        structures['binance'] = BrokerCommissionStructure(
            broker_name="Binance",
            broker_type=BrokerType.CRYPTO_EXCHANGE,
            per_share_rate=0.001,  # 0.1% fee
            min_per_trade=0.0,
            max_per_trade=0.0,
            maker_rebate=0.0001,   # 0.01% rebate
            taker_fee=0.001,       # 0.1% fee
            regulatory_fees=0.0,
            clearing_fees=0.0,
            volume_tiers={
                50: {'maker_rebate': 0.0001, 'taker_fee': 0.001},      # 50 BTC
                500: {'maker_rebate': 0.0002, 'taker_fee': 0.0009},    # 500 BTC
                1000: {'maker_rebate': 0.0003, 'taker_fee': 0.0008}    # 1000 BTC
            }
        )
        
        return structures
    
    def _initialize_venue_characteristics(self) -> Dict[str, VenueCharacteristics]:
        """Initialize venue characteristics"""
        
        venues = {}
        
        # Major exchanges
        venues['nasdaq'] = VenueCharacteristics(
            venue_name="NASDAQ",
            venue_type=VenueType.EXCHANGE,
            average_spread=0.001,
            depth_at_touch=2000.0,
            fill_probability=0.98,
            maker_rebate=0.0002,
            taker_fee=0.0030,
            average_improvement=0.0001,
            latency=0.3,
            uptime=0.9999
        )
        
        venues['nyse'] = VenueCharacteristics(
            venue_name="NYSE",
            venue_type=VenueType.EXCHANGE,
            average_spread=0.001,
            depth_at_touch=1800.0,
            fill_probability=0.97,
            maker_rebate=0.00015,
            taker_fee=0.0025,
            average_improvement=0.00008,
            latency=0.4,
            uptime=0.9999
        )
        
        # ECNs
        venues['bats'] = VenueCharacteristics(
            venue_name="BATS",
            venue_type=VenueType.ECN,
            average_spread=0.001,
            depth_at_touch=1500.0,
            fill_probability=0.95,
            maker_rebate=0.0003,
            taker_fee=0.0030,
            average_improvement=0.00012,
            latency=0.2,
            uptime=0.999
        )
        
        # Dark pools
        venues['liquidnet'] = VenueCharacteristics(
            venue_name="Liquidnet",
            venue_type=VenueType.DARK_POOL,
            average_spread=0.0005,  # Midpoint execution
            depth_at_touch=5000.0,
            fill_probability=0.7,   # Lower fill probability
            maker_rebate=0.0,
            taker_fee=0.0001,       # Low explicit cost
            average_improvement=0.0005,  # Midpoint improvement
            market_impact_factor=0.3,    # Lower market impact
            latency=2.0,            # Higher latency
            uptime=0.998,
            min_order_size=5000     # Minimum block size
        )
        
        return venues
    
    def optimize_execution_cost(self, 
                              symbol: str,
                              order_size: int,
                              order_value: float,
                              urgency: float = 0.5,
                              current_volume: int = 0,
                              market_conditions: Optional[Dict[str, Any]] = None) -> CostOptimizationResult:
        """
        Optimize execution cost across brokers and venues
        
        Args:
            symbol: Symbol to trade
            order_size: Order size in shares
            order_value: Order value in dollars
            urgency: Urgency level (0=patient, 1=urgent)
            current_volume: Current monthly volume
            market_conditions: Current market conditions
            
        Returns:
            CostOptimizationResult with recommendations
        """
        best_cost = float('inf')
        best_option = None
        alternatives = []
        
        # Evaluate all broker-venue combinations
        for broker_name, broker_struct in self.broker_structures.items():
            for venue_name, venue_char in self.venue_characteristics.items():
                
                # Check if venue is suitable for order
                if order_size < venue_char.min_order_size or order_size > venue_char.max_order_size:
                    continue
                
                # Calculate cost for this combination
                cost_breakdown = self._calculate_execution_cost(
                    broker_struct, venue_char, symbol, order_size, order_value, 
                    urgency, current_volume, market_conditions
                )
                
                total_cost = sum(cost_breakdown.values())
                
                option = {
                    'broker': broker_name,
                    'venue': venue_name,
                    'total_cost': total_cost,
                    'cost_breakdown': cost_breakdown,
                    'expected_fill_rate': venue_char.fill_probability
                }
                
                alternatives.append(option)
                
                if total_cost < best_cost:
                    best_cost = total_cost
                    best_option = option
        
        # Sort alternatives by cost
        alternatives.sort(key=lambda x: x['total_cost'])
        
        # Calculate savings vs worst option
        worst_cost = max(alt['total_cost'] for alt in alternatives)
        savings = worst_cost - best_cost
        
        # Determine optimal order type based on urgency
        if urgency > 0.8:
            order_type = OrderType.MARKET
        elif urgency > 0.5:
            order_type = OrderType.LIMIT
        else:
            order_type = OrderType.TWAP
        
        return CostOptimizationResult(
            recommended_broker=best_option['broker'],
            recommended_venue=best_option['venue'],
            recommended_order_type=order_type,
            estimated_cost=best_cost,
            estimated_savings=savings,
            commission_cost=best_option['cost_breakdown']['commission'],
            market_impact_cost=best_option['cost_breakdown']['market_impact'],
            spread_cost=best_option['cost_breakdown']['spread'],
            timing_cost=best_option['cost_breakdown']['timing'],
            alternatives=alternatives[:5],  # Top 5 alternatives
            confidence_level=0.85,
            cost_volatility=best_cost * 0.1  # 10% cost volatility
        )
    
    def _calculate_execution_cost(self, 
                                broker: BrokerCommissionStructure,
                                venue: VenueCharacteristics,
                                symbol: str,
                                order_size: int,
                                order_value: float,
                                urgency: float,
                                current_volume: int,
                                market_conditions: Optional[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate detailed execution cost breakdown"""
        
        costs = {}
        
        # Commission cost
        effective_rate = broker.get_effective_rate(current_volume, is_maker=(urgency < 0.5))
        commission = max(
            order_size * effective_rate,
            broker.min_per_trade
        )
        if broker.max_per_trade > 0:
            commission = min(commission, order_value * broker.max_per_trade)
        
        costs['commission'] = commission
        
        # Regulatory fees
        costs['regulatory'] = order_value * broker.regulatory_fees
        
        # Clearing fees
        costs['clearing'] = order_size * broker.clearing_fees
        
        # Venue costs (spread and market impact)
        if urgency > 0.5:  # Aggressive order
            costs['spread'] = order_size * venue.taker_fee
            costs['market_impact'] = order_value * venue.average_spread * venue.market_impact_factor
        else:  # Passive order
            costs['spread'] = -order_size * venue.maker_rebate  # Negative for rebate
            costs['market_impact'] = order_value * venue.average_spread * 0.3  # Reduced impact
        
        # Timing cost (based on urgency and venue latency)
        timing_factor = urgency * venue.latency / 1000  # Convert ms to seconds
        costs['timing'] = order_value * timing_factor * 0.0001  # 1 bp per second
        
        # Opportunity cost (for delayed execution)
        if urgency < 0.5:
            volatility = market_conditions.get('volatility', 0.02) if market_conditions else 0.02
            delay_hours = (1 - urgency) * 2  # Up to 2 hours delay
            costs['opportunity'] = order_value * volatility * np.sqrt(delay_hours / 24)
        else:
            costs['opportunity'] = 0.0
        
        return costs
    
    def get_broker_comparison(self, 
                            order_size: int,
                            order_value: float,
                            monthly_volume: int = 0) -> pd.DataFrame:
        """
        Compare costs across different brokers
        
        Args:
            order_size: Order size in shares
            order_value: Order value in dollars
            monthly_volume: Monthly trading volume
            
        Returns:
            DataFrame with broker comparison
        """
        comparison_data = []
        
        for broker_name, broker_struct in self.broker_structures.items():
            # Calculate costs for maker and taker
            maker_rate = broker_struct.get_effective_rate(monthly_volume, is_maker=True)
            taker_rate = broker_struct.get_effective_rate(monthly_volume, is_maker=False)
            
            maker_cost = max(order_size * maker_rate, broker_struct.min_per_trade)
            taker_cost = max(order_size * taker_rate, broker_struct.min_per_trade)
            
            # Add regulatory fees
            regulatory_cost = order_value * broker_struct.regulatory_fees
            
            comparison_data.append({
                'Broker': broker_name,
                'Type': broker_struct.broker_type.value,
                'Maker Cost': maker_cost + regulatory_cost,
                'Taker Cost': taker_cost + regulatory_cost,
                'Per Share Rate': broker_struct.per_share_rate,
                'Min Per Trade': broker_struct.min_per_trade,
                'Maker Rebate': broker_struct.maker_rebate,
                'Taker Fee': broker_struct.taker_fee
            })
        
        return pd.DataFrame(comparison_data)
    
    def get_venue_comparison(self, order_size: int) -> pd.DataFrame:
        """
        Compare execution venues
        
        Args:
            order_size: Order size in shares
            
        Returns:
            DataFrame with venue comparison
        """
        comparison_data = []
        
        for venue_name, venue_char in self.venue_characteristics.items():
            # Check if venue accepts this order size
            suitable = (order_size >= venue_char.min_order_size and 
                       order_size <= venue_char.max_order_size)
            
            comparison_data.append({
                'Venue': venue_name,
                'Type': venue_char.venue_type.value,
                'Avg Spread': venue_char.average_spread * 10000,  # bps
                'Depth': venue_char.depth_at_touch,
                'Fill Prob': venue_char.fill_probability * 100,  # %
                'Maker Rebate': venue_char.maker_rebate * 10000,  # bps
                'Taker Fee': venue_char.taker_fee * 10000,  # bps
                'Latency': venue_char.latency,
                'Suitable': suitable
            })
        
        return pd.DataFrame(comparison_data)
    
    def calculate_total_cost_of_ownership(self, 
                                        trading_profile: Dict[str, Any],
                                        time_horizon: int = 12) -> Dict[str, float]:
        """
        Calculate total cost of ownership for different broker options
        
        Args:
            trading_profile: Trading profile with volume, frequency, etc.
            time_horizon: Time horizon in months
            
        Returns:
            Dictionary with TCO for each broker
        """
        monthly_volume = trading_profile.get('monthly_volume', 1_000_000)
        avg_order_size = trading_profile.get('avg_order_size', 1000)
        orders_per_month = trading_profile.get('orders_per_month', 100)
        maker_ratio = trading_profile.get('maker_ratio', 0.6)  # 60% maker orders
        
        tco_results = {}
        
        for broker_name, broker_struct in self.broker_structures.items():
            # Calculate monthly costs
            maker_rate = broker_struct.get_effective_rate(monthly_volume, is_maker=True)
            taker_rate = broker_struct.get_effective_rate(monthly_volume, is_maker=False)
            
            # Commission costs
            maker_orders = orders_per_month * maker_ratio
            taker_orders = orders_per_month * (1 - maker_ratio)
            
            monthly_commission = (
                maker_orders * max(avg_order_size * maker_rate, broker_struct.min_per_trade) +
                taker_orders * max(avg_order_size * taker_rate, broker_struct.min_per_trade)
            )
            
            # Regulatory fees
            avg_order_value = avg_order_size * 50  # Assume $50 average price
            monthly_regulatory = orders_per_month * avg_order_value * broker_struct.regulatory_fees
            
            # Total monthly cost
            monthly_total = monthly_commission + monthly_regulatory
            
            # Total cost over time horizon
            tco_results[broker_name] = monthly_total * time_horizon
        
        return tco_results
    
    def optimize_timing(self, 
                       symbol: str,
                       order_size: int,
                       target_completion: datetime,
                       market_schedule: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize execution timing to minimize costs
        
        Args:
            symbol: Symbol to trade
            order_size: Order size
            target_completion: Target completion time
            market_schedule: Market schedule and characteristics
            
        Returns:
            Timing optimization recommendations
        """
        # Market open/close effects
        market_open = market_schedule.get('market_open', time(9, 30))
        market_close = market_schedule.get('market_close', time(16, 0))
        
        current_time = datetime.now().time()
        
        recommendations = {
            'optimal_start_time': None,
            'execution_schedule': [],
            'cost_savings': 0.0,
            'reasoning': []
        }
        
        # Avoid first/last 30 minutes (higher volatility and costs)
        avoid_start = datetime.combine(datetime.now().date(), market_open)
        avoid_end_morning = avoid_start + timedelta(minutes=30)
        
        avoid_start_afternoon = datetime.combine(datetime.now().date(), market_close) - timedelta(minutes=30)
        avoid_end = datetime.combine(datetime.now().date(), market_close)
        
        # Optimal execution window (10:00 AM - 3:30 PM)
        optimal_start = datetime.combine(datetime.now().date(), time(10, 0))
        optimal_end = datetime.combine(datetime.now().date(), time(15, 30))
        
        if optimal_start <= target_completion <= optimal_end:
            recommendations['optimal_start_time'] = optimal_start
            recommendations['reasoning'].append("Executing during optimal hours (10:00 AM - 3:30 PM)")
            recommendations['cost_savings'] = 0.15  # 15% cost savings
        else:
            recommendations['optimal_start_time'] = max(optimal_start, datetime.now())
            recommendations['reasoning'].append("Delaying execution to optimal hours")
            recommendations['cost_savings'] = 0.10  # 10% cost savings
        
        # Create execution schedule (TWAP-style)
        execution_window = (target_completion - recommendations['optimal_start_time']).total_seconds() / 3600
        num_slices = max(1, int(execution_window * 2))  # 30-minute slices
        slice_size = order_size / num_slices
        
        for i in range(num_slices):
            execution_time = recommendations['optimal_start_time'] + timedelta(minutes=30 * i)
            recommendations['execution_schedule'].append({
                'time': execution_time,
                'quantity': slice_size,
                'expected_cost_reduction': 0.05  # 5% per slice
            })
        
        return recommendations
    
    def get_cost_analytics(self) -> Dict[str, Any]:
        """Get cost analytics and performance metrics"""
        return {
            'total_brokers': len(self.broker_structures),
            'total_venues': len(self.venue_characteristics),
            'broker_types': list(set(b.broker_type.value for b in self.broker_structures.values())),
            'venue_types': list(set(v.venue_type.value for v in self.venue_characteristics.values())),
            'average_commission_rate': np.mean([b.per_share_rate for b in self.broker_structures.values()]),
            'average_spread': np.mean([v.average_spread for v in self.venue_characteristics.values()]),
            'volume_tracking': dict(self.volume_tracking)
        }
    
    def update_volume_tracking(self, broker: str, volume: int):
        """Update volume tracking for tier calculation"""
        if broker not in self.volume_tracking:
            self.volume_tracking[broker] = {'monthly_volume': 0, 'last_reset': datetime.now()}
        
        # Reset monthly volume if new month
        last_reset = self.volume_tracking[broker]['last_reset']
        if datetime.now().month != last_reset.month:
            self.volume_tracking[broker]['monthly_volume'] = 0
            self.volume_tracking[broker]['last_reset'] = datetime.now()
        
        self.volume_tracking[broker]['monthly_volume'] += volume 