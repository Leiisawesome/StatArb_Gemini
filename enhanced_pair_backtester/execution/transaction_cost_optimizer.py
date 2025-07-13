#!/usr/bin/env python3
"""
Transaction Cost Optimization System
Professional-grade transaction cost estimation with broker-specific pricing
"""

import numpy as np
import pandas as pd
from datetime import datetime, time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

class BrokerType(Enum):
    """Broker categories with different pricing structures"""
    PRIME_BROKERAGE = "prime_brokerage"      # Goldman, Morgan Stanley, etc.
    INSTITUTIONAL_ECN = "institutional_ecn"   # BATS, ARCA, etc.
    RETAIL_PRO = "retail_pro"                # Interactive Brokers Pro
    RETAIL_STANDARD = "retail_standard"      # TD Ameritrade, Schwab
    CRYPTO_EXCHANGE = "crypto_exchange"      # Binance, Coinbase Pro
    DARK_POOL = "dark_pool"                  # Liquidnet, ITG POSIT

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

class LiquidityType(Enum):
    """Liquidity provision type"""
    MAKER = "maker"    # Provides liquidity (rebates)
    TAKER = "taker"    # Takes liquidity (fees)
    MIXED = "mixed"    # Combination

@dataclass
class BrokerCommissionStructure:
    """Broker-specific commission structure"""
    broker_name: str
    broker_type: BrokerType
    
    # Per-share pricing
    per_share_rate: float = 0.0
    min_per_share: float = 0.0
    max_per_share: float = 0.0
    
    # Per-trade pricing
    per_trade_rate: float = 0.0
    min_per_trade: float = 0.0
    max_per_trade: float = 0.0
    
    # Percentage-based pricing
    percentage_rate: float = 0.0
    min_percentage: float = 0.0
    max_percentage: float = 0.0
    
    # Maker-taker pricing
    maker_rebate: float = 0.0      # Rebate for providing liquidity
    taker_fee: float = 0.0         # Fee for taking liquidity
    
    # Volume-based tiers
    volume_tiers: Dict[float, Dict[str, float]] = field(default_factory=dict)
    
    # Additional fees
    regulatory_fees: float = 0.0    # SEC/FINRA fees
    clearing_fees: float = 0.0      # Clearing fees
    exchange_fees: float = 0.0      # Exchange fees
    
    # Special pricing for different instruments
    etf_discount: float = 0.0       # ETF trading discount
    options_multiplier: float = 1.0  # Options pricing multiplier
    
    # Borrowing costs for short selling
    base_borrow_rate: float = 0.0   # Base borrow rate
    hard_to_borrow_premium: float = 0.0  # HTB premium

@dataclass
class TransactionCostBreakdown:
    """Detailed transaction cost breakdown"""
    # Primary costs
    commission: float = 0.0
    spread_cost: float = 0.0
    market_impact: float = 0.0
    slippage: float = 0.0
    
    # Secondary costs
    regulatory_fees: float = 0.0
    clearing_fees: float = 0.0
    exchange_fees: float = 0.0
    borrowing_cost: float = 0.0
    
    # Rebates and discounts
    maker_rebate: float = 0.0
    volume_discount: float = 0.0
    etf_discount: float = 0.0
    
    # Timing costs
    timing_cost: float = 0.0
    opportunity_cost: float = 0.0
    
    # Total costs
    gross_cost: float = 0.0
    net_cost: float = 0.0
    cost_basis_points: float = 0.0
    
    def __post_init__(self):
        """Calculate total costs"""
        self.gross_cost = (
            self.commission + self.spread_cost + self.market_impact + 
            self.slippage + self.regulatory_fees + self.clearing_fees + 
            self.exchange_fees + self.borrowing_cost + self.timing_cost + 
            self.opportunity_cost
        )
        
        self.net_cost = (
            self.gross_cost - self.maker_rebate - 
            self.volume_discount - self.etf_discount
        )

@dataclass
class MarketMicrostructure:
    """Market microstructure data for cost calculation"""
    symbol: str
    timestamp: datetime
    
    # Bid-ask data
    bid_price: float
    ask_price: float
    bid_size: int
    ask_size: int
    
    # Volume and liquidity
    volume: float
    avg_daily_volume: float
    dollar_volume: float
    
    # Volatility measures
    realized_volatility: float
    intraday_volatility: float
    
    # Market structure
    market_maker_presence: float  # 0-1 score
    order_book_depth: float
    price_impact_coefficient: float
    
    # Time-based factors
    time_to_close: float  # Hours to market close
    session_type: str     # "pre", "regular", "post"

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
        
        # Institutional ECN (BATS example)
        structures['bats_ecn'] = BrokerCommissionStructure(
            broker_name="BATS ECN",
            broker_type=BrokerType.INSTITUTIONAL_ECN,
            maker_rebate=0.0003,   # $0.0003 per share rebate
            taker_fee=0.0030,      # $0.003 per share fee
            regulatory_fees=0.0000221,
            exchange_fees=0.0001,
            volume_tiers={
                500_000: {'maker_rebate': 0.00032, 'taker_fee': 0.0029},
                5_000_000: {'maker_rebate': 0.00035, 'taker_fee': 0.0028},
                50_000_000: {'maker_rebate': 0.0004, 'taker_fee': 0.0027}
            }
        )
        
        # Interactive Brokers Pro
        structures['interactive_brokers'] = BrokerCommissionStructure(
            broker_name="Interactive Brokers Pro",
            broker_type=BrokerType.RETAIL_PRO,
            per_share_rate=0.005,  # $0.005 per share
            min_per_trade=1.0,
            max_per_trade=1.0,     # 1% of trade value
            percentage_rate=0.01,
            regulatory_fees=0.0000221,
            clearing_fees=0.0002,
            volume_tiers={
                300_000: {'per_share_rate': 0.0035},
                3_000_000: {'per_share_rate': 0.002},
                20_000_000: {'per_share_rate': 0.0015}
            },
            etf_discount=0.5,  # 50% discount on ETFs
            base_borrow_rate=0.0175
        )
        
        # TD Ameritrade (Retail Standard)
        structures['td_ameritrade'] = BrokerCommissionStructure(
            broker_name="TD Ameritrade",
            broker_type=BrokerType.RETAIL_STANDARD,
            per_trade_rate=0.0,    # $0 stock trades
            regulatory_fees=0.0000221,
            options_multiplier=0.65,  # $0.65 per options contract
            base_borrow_rate=0.0925   # 9.25% base rate
        )
        
        # Schwab (Retail Standard)
        structures['schwab'] = BrokerCommissionStructure(
            broker_name="Charles Schwab",
            broker_type=BrokerType.RETAIL_STANDARD,
            per_trade_rate=0.0,    # $0 stock trades
            regulatory_fees=0.0000221,
            options_multiplier=0.65,
            base_borrow_rate=0.0825
        )
        
        # Dark Pool (Liquidnet example)
        structures['liquidnet'] = BrokerCommissionStructure(
            broker_name="Liquidnet",
            broker_type=BrokerType.DARK_POOL,
            per_share_rate=0.0015,  # $0.0015 per share
            min_per_trade=10.0,
            regulatory_fees=0.0000221,
            clearing_fees=0.0003,
            volume_tiers={
                1_000_000: {'per_share_rate': 0.001},
                10_000_000: {'per_share_rate': 0.0008},
                100_000_000: {'per_share_rate': 0.0006}
            }
        )
        
        return structures
    
    def calculate_transaction_costs(self,
                                  symbol: str,
                                  quantity: int,
                                  price: float,
                                  broker: str,
                                  order_type: OrderType = OrderType.MARKET,
                                  liquidity_type: LiquidityType = LiquidityType.TAKER,
                                  market_data: Optional[MarketMicrostructure] = None) -> TransactionCostBreakdown:
        """
        Calculate comprehensive transaction costs
        
        Args:
            symbol: Trading symbol
            quantity: Number of shares
            price: Execution price
            broker: Broker name
            order_type: Order type
            liquidity_type: Liquidity provision type
            market_data: Market microstructure data
            
        Returns:
            TransactionCostBreakdown with detailed cost analysis
        """
        
        if broker not in self.broker_structures:
            raise ValueError(f"Unknown broker: {broker}")
        
        structure = self.broker_structures[broker]
        notional_value = abs(quantity * price)
        
        # Initialize cost breakdown
        costs = TransactionCostBreakdown()
        
        # 1. Commission calculation
        costs.commission = self._calculate_commission(
            structure, quantity, price, notional_value
        )
        
        # 2. Maker-taker fees/rebates
        if structure.maker_rebate > 0 or structure.taker_fee > 0:
            if liquidity_type == LiquidityType.MAKER:
                costs.maker_rebate = abs(quantity) * structure.maker_rebate
            elif liquidity_type == LiquidityType.TAKER:
                costs.commission += abs(quantity) * structure.taker_fee
        
        # 3. Regulatory fees
        costs.regulatory_fees = notional_value * structure.regulatory_fees
        
        # 4. Clearing and exchange fees
        costs.clearing_fees = abs(quantity) * structure.clearing_fees
        costs.exchange_fees = abs(quantity) * structure.exchange_fees
        
        # 5. Market impact and slippage
        if market_data:
            costs.spread_cost = self._calculate_spread_cost(
                market_data, quantity, order_type
            )
            costs.market_impact = self._calculate_market_impact(
                market_data, quantity, price
            )
            costs.slippage = self._calculate_slippage(
                market_data, quantity, order_type
            )
            costs.timing_cost = self._calculate_timing_cost(
                market_data, quantity, order_type
            )
        
        # 6. Volume discounts
        costs.volume_discount = self._calculate_volume_discount(
            structure, quantity, price
        )
        
        # 7. ETF discounts
        if self._is_etf(symbol):
            costs.etf_discount = costs.commission * structure.etf_discount
        
        # 8. Borrowing costs (for short sales)
        if quantity < 0:  # Short sale
            costs.borrowing_cost = self._calculate_borrowing_cost(
                structure, symbol, notional_value
            )
        
        # Calculate basis points
        if notional_value > 0:
            costs.cost_basis_points = (costs.net_cost / notional_value) * 10000
        
        return costs
    
    def _calculate_commission(self,
                            structure: BrokerCommissionStructure,
                            quantity: int,
                            price: float,
                            notional_value: float) -> float:
        """Calculate base commission"""
        
        # Get current volume tier
        monthly_volume = self._get_monthly_volume(structure.broker_name)
        active_tier = self._get_active_tier(structure, monthly_volume)
        
        # Per-share pricing
        if structure.per_share_rate > 0:
            per_share_rate = active_tier.get('per_share_rate', structure.per_share_rate)
            commission = abs(quantity) * per_share_rate
            
            if structure.min_per_trade > 0:
                commission = max(commission, structure.min_per_trade)
            if structure.max_per_trade > 0:
                commission = min(commission, structure.max_per_trade)
                
            return commission
        
        # Per-trade pricing
        elif structure.per_trade_rate > 0:
            return structure.per_trade_rate
        
        # Percentage-based pricing
        elif structure.percentage_rate > 0:
            commission = notional_value * structure.percentage_rate
            
            if structure.min_percentage > 0:
                commission = max(commission, structure.min_percentage)
            if structure.max_percentage > 0:
                commission = min(commission, structure.max_percentage)
                
            return commission
        
        return 0.0
    
    def _calculate_spread_cost(self,
                             market_data: MarketMicrostructure,
                             quantity: int,
                             order_type: OrderType) -> float:
        """Calculate bid-ask spread cost"""
        
        spread = market_data.ask_price - market_data.bid_price
        
        if order_type == OrderType.MARKET:
            # Market orders pay full spread
            return abs(quantity) * spread * 0.5  # Half spread cost
        elif order_type == OrderType.LIMIT:
            # Limit orders may avoid spread cost
            return abs(quantity) * spread * 0.1  # 10% of spread
        else:
            return abs(quantity) * spread * 0.3  # 30% of spread
    
    def _calculate_market_impact(self,
                               market_data: MarketMicrostructure,
                               quantity: int,
                               price: float) -> float:
        """Calculate permanent market impact"""
        
        # Square root law for market impact
        participation_rate = abs(quantity * price) / market_data.dollar_volume
        
        # Base impact coefficient adjusted for market structure
        base_impact = market_data.price_impact_coefficient * 0.0001
        
        # Volatility adjustment
        volatility_adjustment = 1.0 + market_data.realized_volatility
        
        # Market maker presence adjustment
        mm_adjustment = 1.0 - (market_data.market_maker_presence * 0.3)
        
        impact = (base_impact * 
                 np.sqrt(participation_rate) * 
                 volatility_adjustment * 
                 mm_adjustment * 
                 abs(quantity) * price)
        
        return impact
    
    def _calculate_slippage(self,
                          market_data: MarketMicrostructure,
                          quantity: int,
                          order_type: OrderType) -> float:
        """Calculate temporary slippage"""
        
        base_slippage = 0.0001  # 1 bp base slippage
        
        # Order type adjustment
        order_multipliers = {
            OrderType.MARKET: 1.5,
            OrderType.LIMIT: 0.5,
            OrderType.STOP: 2.0,
            OrderType.TWAP: 0.3,
            OrderType.VWAP: 0.4,
            OrderType.IMPLEMENTATION_SHORTFALL: 0.6
        }
        
        multiplier = order_multipliers.get(order_type, 1.0)
        
        # Volatility adjustment
        volatility_factor = 1.0 + market_data.intraday_volatility * 2.0
        
        # Liquidity adjustment
        liquidity_factor = max(0.5, 1.0 - market_data.order_book_depth)
        
        slippage = (base_slippage * 
                   multiplier * 
                   volatility_factor * 
                   liquidity_factor * 
                   abs(quantity) * market_data.ask_price)
        
        return slippage
    
    def _calculate_timing_cost(self,
                             market_data: MarketMicrostructure,
                             quantity: int,
                             order_type: OrderType) -> float:
        """Calculate timing-related costs"""
        
        # Session-based cost adjustments
        session_multipliers = {
            'pre': 2.0,      # Pre-market premium
            'regular': 1.0,   # Regular hours
            'post': 1.8       # After-hours premium
        }
        
        multiplier = session_multipliers.get(market_data.session_type, 1.0)
        
        # Time to close adjustment (higher cost near close)
        if market_data.time_to_close < 0.5:  # Last 30 minutes
            multiplier *= 1.5
        
        base_timing_cost = 0.0002  # 2 bps base cost
        
        timing_cost = (base_timing_cost * 
                      multiplier * 
                      abs(quantity) * 
                      market_data.ask_price)
        
        return timing_cost
    
    def _calculate_volume_discount(self,
                                 structure: BrokerCommissionStructure,
                                 quantity: int,
                                 price: float) -> float:
        """Calculate volume-based discounts"""
        
        monthly_volume = self._get_monthly_volume(structure.broker_name)
        
        # Volume discount tiers
        if monthly_volume > 100_000_000:
            return abs(quantity * price) * 0.0001  # 1 bp discount
        elif monthly_volume > 10_000_000:
            return abs(quantity * price) * 0.00005  # 0.5 bp discount
        
        return 0.0
    
    def _calculate_borrowing_cost(self,
                                structure: BrokerCommissionStructure,
                                symbol: str,
                                notional_value: float) -> float:
        """Calculate borrowing costs for short sales"""
        
        # Base borrow rate
        borrow_rate = structure.base_borrow_rate
        
        # Hard-to-borrow premium (simplified)
        if self._is_hard_to_borrow(symbol):
            borrow_rate += structure.hard_to_borrow_premium
        
        # Daily borrowing cost
        daily_cost = notional_value * borrow_rate / 365
        
        return daily_cost
    
    def _get_monthly_volume(self, broker: str) -> float:
        """Get monthly trading volume for broker"""
        return self.volume_tracking.get(broker, 0.0)
    
    def _get_active_tier(self, 
                        structure: BrokerCommissionStructure,
                        monthly_volume: float) -> Dict[str, float]:
        """Get active volume tier"""
        
        active_tier = {}
        
        for volume_threshold in sorted(structure.volume_tiers.keys(), reverse=True):
            if monthly_volume >= volume_threshold:
                active_tier = structure.volume_tiers[volume_threshold]
                break
        
        return active_tier
    
    def _is_etf(self, symbol: str) -> bool:
        """Check if symbol is an ETF"""
        etf_symbols = {
            'SPY', 'QQQ', 'IWM', 'TLT', 'TMF', 'TQQQ', 'UPRO', 'TNA', 'SOXL',
            'XLK', 'XLF', 'XLE', 'XLV', 'XLI', 'XLP', 'XLU', 'XLY', 'XLRE'
        }
        return symbol.upper() in etf_symbols
    
    def _is_hard_to_borrow(self, symbol: str) -> bool:
        """Check if symbol is hard to borrow"""
        # Simplified HTB detection
        htb_symbols = {'GME', 'AMC', 'TSLA', 'NVDA'}
        return symbol.upper() in htb_symbols
    
    def optimize_broker_selection(self,
                                symbol: str,
                                quantity: int,
                                price: float,
                                order_type: OrderType = OrderType.MARKET,
                                market_data: Optional[MarketMicrostructure] = None) -> Tuple[str, TransactionCostBreakdown]:
        """
        Optimize broker selection for minimum cost
        
        Args:
            symbol: Trading symbol
            quantity: Number of shares
            price: Expected execution price
            order_type: Order type
            market_data: Market microstructure data
            
        Returns:
            Tuple of (optimal_broker, cost_breakdown)
        """
        
        best_broker = None
        best_cost = float('inf')
        best_breakdown = None
        
        for broker_name in self.broker_structures.keys():
            try:
                cost_breakdown = self.calculate_transaction_costs(
                    symbol=symbol,
                    quantity=quantity,
                    price=price,
                    broker=broker_name,
                    order_type=order_type,
                    market_data=market_data
                )
                
                if cost_breakdown.net_cost < best_cost:
                    best_cost = cost_breakdown.net_cost
                    best_broker = broker_name
                    best_breakdown = cost_breakdown
                    
            except Exception as e:
                self.logger.warning(f"Cost calculation failed for {broker_name}: {e}")
                continue
        
        return best_broker, best_breakdown
    
    def optimize_order_timing(self,
                            symbol: str,
                            quantity: int,
                            price: float,
                            broker: str,
                            time_horizon_hours: float = 24.0) -> Dict[str, Any]:
        """
        Optimize order timing for minimum cost
        
        Args:
            symbol: Trading symbol
            quantity: Number of shares
            price: Expected price
            broker: Broker name
            time_horizon_hours: Time horizon for optimization
            
        Returns:
            Optimization results with timing recommendations
        """
        
        # Time-of-day cost analysis
        time_costs = []
        
        # Sample different times of day
        for hour in range(9, 16):  # 9 AM to 4 PM
            for minute in [0, 15, 30, 45]:
                test_time = time(hour, minute)
                
                # Create mock market data for this time
                mock_market_data = self._create_mock_market_data(symbol, test_time)
                
                cost_breakdown = self.calculate_transaction_costs(
                    symbol=symbol,
                    quantity=quantity,
                    price=price,
                    broker=broker,
                    market_data=mock_market_data
                )
                
                time_costs.append({
                    'time': test_time,
                    'cost': cost_breakdown.net_cost,
                    'cost_bps': cost_breakdown.cost_basis_points,
                    'breakdown': cost_breakdown
                })
        
        # Find optimal time
        optimal_time = min(time_costs, key=lambda x: x['cost'])
        
        return {
            'optimal_time': optimal_time['time'],
            'optimal_cost': optimal_time['cost'],
            'optimal_cost_bps': optimal_time['cost_bps'],
            'cost_range': {
                'min_cost': min(tc['cost'] for tc in time_costs),
                'max_cost': max(tc['cost'] for tc in time_costs),
                'avg_cost': np.mean([tc['cost'] for tc in time_costs])
            },
            'recommendations': self._generate_timing_recommendations(time_costs)
        }
    
    def _create_mock_market_data(self, symbol: str, trade_time: time) -> MarketMicrostructure:
        """Create mock market data for timing analysis"""
        
        # Time-of-day liquidity patterns
        hour = trade_time.hour
        minute = trade_time.minute
        
        # Liquidity is typically lower at open/close
        if hour == 9 and minute < 45:
            liquidity_factor = 0.7  # Lower liquidity at open
        elif hour >= 15:
            liquidity_factor = 0.8  # Lower liquidity at close
        else:
            liquidity_factor = 1.0  # Normal liquidity
        
        # Session type
        if hour < 9:
            session_type = "pre"
        elif hour >= 16:
            session_type = "post"
        else:
            session_type = "regular"
        
        return MarketMicrostructure(
            symbol=symbol,
            timestamp=datetime.combine(datetime.now().date(), trade_time),
            bid_price=100.0,
            ask_price=100.02,
            bid_size=1000,
            ask_size=1000,
            volume=1000000 * liquidity_factor,
            avg_daily_volume=10000000,
            dollar_volume=1000000000 * liquidity_factor,
            realized_volatility=0.02,
            intraday_volatility=0.01,
            market_maker_presence=0.8 * liquidity_factor,
            order_book_depth=0.9 * liquidity_factor,
            price_impact_coefficient=0.1 / liquidity_factor,
            time_to_close=16 - hour - minute/60,
            session_type=session_type
        )
    
    def _generate_timing_recommendations(self, time_costs: List[Dict]) -> List[str]:
        """Generate timing recommendations"""
        
        recommendations = []
        
        # Find best and worst times
        best_times = sorted(time_costs, key=lambda x: x['cost'])[:3]
        worst_times = sorted(time_costs, key=lambda x: x['cost'], reverse=True)[:3]
        
        recommendations.append(f"Best execution times: {[t['time'].strftime('%H:%M') for t in best_times]}")
        recommendations.append(f"Avoid execution times: {[t['time'].strftime('%H:%M') for t in worst_times]}")
        
        # Cost savings analysis
        best_cost = best_times[0]['cost']
        worst_cost = worst_times[0]['cost']
        savings_bps = ((worst_cost - best_cost) / (best_cost + worst_cost) * 2) * 10000
        
        recommendations.append(f"Optimal timing can save up to {savings_bps:.1f} basis points")
        
        return recommendations
    
    def generate_cost_report(self,
                           symbol: str,
                           quantity: int,
                           price: float,
                           broker: str,
                           market_data: Optional[MarketMicrostructure] = None) -> str:
        """Generate comprehensive cost report"""
        
        costs = self.calculate_transaction_costs(
            symbol=symbol,
            quantity=quantity,
            price=price,
            broker=broker,
            market_data=market_data
        )
        
        notional_value = abs(quantity * price)
        
        report = f"""
=== TRANSACTION COST ANALYSIS ===
Symbol: {symbol}
Quantity: {quantity:,} shares
Price: ${price:.2f}
Notional Value: ${notional_value:,.2f}
Broker: {broker}

=== COST BREAKDOWN ===
Commission:         ${costs.commission:,.2f} ({costs.commission/notional_value*10000:.1f} bps)
Spread Cost:        ${costs.spread_cost:,.2f} ({costs.spread_cost/notional_value*10000:.1f} bps)
Market Impact:      ${costs.market_impact:,.2f} ({costs.market_impact/notional_value*10000:.1f} bps)
Slippage:           ${costs.slippage:,.2f} ({costs.slippage/notional_value*10000:.1f} bps)
Regulatory Fees:    ${costs.regulatory_fees:,.2f} ({costs.regulatory_fees/notional_value*10000:.1f} bps)
Timing Cost:        ${costs.timing_cost:,.2f} ({costs.timing_cost/notional_value*10000:.1f} bps)

=== REBATES & DISCOUNTS ===
Maker Rebate:       ${costs.maker_rebate:,.2f} ({costs.maker_rebate/notional_value*10000:.1f} bps)
Volume Discount:    ${costs.volume_discount:,.2f} ({costs.volume_discount/notional_value*10000:.1f} bps)
ETF Discount:       ${costs.etf_discount:,.2f} ({costs.etf_discount/notional_value*10000:.1f} bps)

=== TOTAL COSTS ===
Gross Cost:         ${costs.gross_cost:,.2f} ({costs.gross_cost/notional_value*10000:.1f} bps)
Net Cost:           ${costs.net_cost:,.2f} ({costs.cost_basis_points:.1f} bps)

=== OPTIMIZATION RECOMMENDATIONS ===
"""
        
        # Add broker optimization
        optimal_broker, optimal_costs = self.optimize_broker_selection(
            symbol, quantity, price, market_data=market_data
        )
        
        if optimal_broker != broker:
            savings = costs.net_cost - optimal_costs.net_cost
            report += f"• Switch to {optimal_broker} to save ${savings:.2f} ({savings/notional_value*10000:.1f} bps)\n"
        
        # Add timing optimization
        timing_results = self.optimize_order_timing(symbol, quantity, price, broker)
        timing_savings = costs.net_cost - timing_results['optimal_cost']
        
        if timing_savings > 0:
            report += f"• Execute at {timing_results['optimal_time']} to save ${timing_savings:.2f}\n"
        
        report += f"• Consider using limit orders to reduce spread costs\n"
        report += f"• For large orders, consider TWAP/VWAP algorithms\n"
        
        return report
    
    def update_volume_tracking(self, broker: str, volume: float):
        """Update monthly volume tracking"""
        self.volume_tracking[broker] = self.volume_tracking.get(broker, 0.0) + volume
    
    def get_broker_comparison(self,
                            symbol: str,
                            quantity: int,
                            price: float,
                            market_data: Optional[MarketMicrostructure] = None) -> pd.DataFrame:
        """Get broker cost comparison table"""
        
        comparison_data = []
        
        for broker_name in self.broker_structures.keys():
            try:
                costs = self.calculate_transaction_costs(
                    symbol=symbol,
                    quantity=quantity,
                    price=price,
                    broker=broker_name,
                    market_data=market_data
                )
                
                comparison_data.append({
                    'Broker': broker_name,
                    'Broker Type': self.broker_structures[broker_name].broker_type.value,
                    'Total Cost ($)': costs.net_cost,
                    'Cost (bps)': costs.cost_basis_points,
                    'Commission ($)': costs.commission,
                    'Spread Cost ($)': costs.spread_cost,
                    'Market Impact ($)': costs.market_impact,
                    'Rebates ($)': costs.maker_rebate + costs.volume_discount + costs.etf_discount
                })
                
            except Exception as e:
                self.logger.warning(f"Cost calculation failed for {broker_name}: {e}")
                continue
        
        df = pd.DataFrame(comparison_data)
        return df.sort_values('Total Cost ($)') 