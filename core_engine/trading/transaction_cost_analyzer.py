"""
Trading Engine - Transaction Cost Analyzer
Advanced transaction cost analysis with market microstructure modeling and cost attribution
"""

import logging
import threading
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque

from .order_manager import OrderSide
from .execution_handler import ExecutionReport, ExecutionMetrics

logger = logging.getLogger(__name__)


class CostComponent(Enum):
    """Transaction cost components"""
    SPREAD_COST = "spread_cost"
    MARKET_IMPACT = "market_impact"
    TIMING_COST = "timing_cost"
    COMMISSION = "commission"
    FEES = "fees"
    OPPORTUNITY_COST = "opportunity_cost"
    SLIPPAGE = "slippage"


class BenchmarkType(Enum):
    """Benchmark types for cost analysis"""
    ARRIVAL_PRICE = "arrival_price"
    VWAP = "vwap"
    TWAP = "twap"
    OPEN_PRICE = "open_price"
    CLOSE_PRICE = "close_price"
    MIDPOINT = "midpoint"
    IMPLEMENTATION_SHORTFALL = "implementation_shortfall"


@dataclass
class TransactionCostBreakdown:
    """Detailed transaction cost breakdown"""
    order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    execution_value: float
    benchmark_value: float
    benchmark_type: BenchmarkType
    
    # Cost components in basis points
    spread_cost_bps: float
    market_impact_bps: float
    timing_cost_bps: float
    commission_bps: float
    fees_bps: float
    opportunity_cost_bps: float
    total_cost_bps: float
    
    # Absolute cost amounts
    spread_cost_amount: float
    market_impact_amount: float
    timing_cost_amount: float
    commission_amount: float
    fees_amount: float
    opportunity_cost_amount: float
    total_cost_amount: float
    
    # Attribution
    cost_attribution: Dict[str, float] = field(default_factory=dict)
    market_conditions: Dict[str, float] = field(default_factory=dict)
    execution_quality: Dict[str, float] = field(default_factory=dict)
    
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class MarketMicrostructure:
    """Market microstructure metrics"""
    symbol: str
    timestamp: datetime
    
    # Spread metrics
    bid_ask_spread: float
    effective_spread: float
    realized_spread: float
    
    # Depth metrics
    bid_depth: float
    ask_depth: float
    total_depth: float
    
    # Price impact metrics
    temporary_impact: float
    permanent_impact: float
    
    # Volatility metrics
    intraday_volatility: float
    price_variance: float
    
    # Volume metrics
    turnover_rate: float
    volume_concentration: float
    
    # Market quality
    price_efficiency: float
    liquidity_score: float


@dataclass
class CostAttribution:
    """Cost attribution analysis"""
    order_id: str
    total_cost_bps: float
    
    # Factor attribution
    market_structure_impact: float  # % of total cost
    timing_impact: float           # % of total cost
    size_impact: float            # % of total cost
    volatility_impact: float      # % of total cost
    liquidity_impact: float       # % of total cost
    execution_impact: float       # % of total cost
    
    # Decomposition
    systematic_cost: float        # Unavoidable cost
    alpha_cost: float            # Cost due to information/alpha
    execution_cost: float        # Cost due to execution quality
    
    recommendations: List[str] = field(default_factory=list)


class TransactionCostAnalyzer:
    """
    Advanced transaction cost analyzer
    
    Provides comprehensive analysis of trading costs with market microstructure
    modeling, cost attribution, and performance benchmarking.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize transaction cost analyzer"""
        self.config = config or {}
        self._lock = threading.Lock()
        
        # Cost analysis tracking
        self._cost_analyses = deque(maxlen=5000)
        self._cost_by_symbol = defaultdict(list)
        self._cost_by_strategy = defaultdict(list)
        self._cost_by_trader = defaultdict(list)
        
        # Market microstructure data
        self._microstructure_data = {}
        
        # Benchmarks and reference prices
        self._benchmark_prices = defaultdict(dict)
        self._reference_data = {}
        
        # Configuration
        self.enable_attribution = self.config.get('enable_attribution', True)
        self.enable_microstructure = self.config.get('enable_microstructure', True)
        self.cost_threshold_bps = self.config.get('cost_threshold_bps', 50)
        
        # Market impact models
        self._impact_models = {
            'linear': self._linear_impact_model,
            'square_root': self._square_root_impact_model,
            'almgren_chriss': self._almgren_chriss_impact_model
        }
        
        # Statistics tracking
        self._cost_statistics = {
            'total_trades_analyzed': 0,
            'average_total_cost_bps': 0.0,
            'average_spread_cost_bps': 0.0,
            'average_market_impact_bps': 0.0,
            'high_cost_trades': 0,
            'cost_efficiency_score': 0.0
        }
        
        logger.info("TransactionCostAnalyzer initialized")
    
    async def analyze_transaction_costs(
        self,
        execution_report: ExecutionReport,
        market_data: Optional[Dict[str, Any]] = None,
        benchmark_type: BenchmarkType = BenchmarkType.ARRIVAL_PRICE
    ) -> TransactionCostBreakdown:
        """
        Analyze transaction costs for an execution
        
        Args:
            execution_report: Execution report to analyze
            market_data: Market data for analysis
            benchmark_type: Benchmark type for cost calculation
            
        Returns:
            Detailed transaction cost breakdown
        """
        try:
            logger.debug(f"Analyzing transaction costs for order {execution_report.order_id}")
            
            metrics = execution_report.metrics
            
            # Get benchmark price
            benchmark_price = await self._get_benchmark_price(
                metrics.symbol, benchmark_type, execution_report.timestamp
            )
            
            # Calculate cost components
            cost_breakdown = await self._calculate_cost_components(
                metrics, benchmark_price, benchmark_type
            )
            
            # Add market microstructure analysis
            if self.enable_microstructure and market_data:
                microstructure = await self._analyze_market_microstructure(
                    metrics.symbol, market_data
                )
                cost_breakdown.market_conditions = self._extract_market_conditions(microstructure)
            
            # Perform cost attribution
            if self.enable_attribution:
                attribution = await self._perform_cost_attribution(
                    cost_breakdown, execution_report, market_data
                )
                cost_breakdown.cost_attribution = attribution.market_structure_impact
            
            # Store analysis
            with self._lock:
                self._cost_analyses.append(cost_breakdown)
                self._cost_by_symbol[metrics.symbol].append(cost_breakdown)
                
                if hasattr(metrics, 'strategy_id') and metrics.strategy_id:
                    self._cost_by_strategy[metrics.strategy_id].append(cost_breakdown)
            
            # Update statistics
            await self._update_cost_statistics(cost_breakdown)
            
            logger.info(f"Cost analysis completed: {cost_breakdown.total_cost_bps:.2f} bps for order {execution_report.order_id}")
            
            return cost_breakdown
            
        except Exception as e:
            logger.error(f"Error analyzing transaction costs: {e}")
            raise
    
    async def _calculate_cost_components(
        self,
        metrics: ExecutionMetrics,
        benchmark_price: float,
        benchmark_type: BenchmarkType
    ) -> TransactionCostBreakdown:
        """Calculate detailed cost components"""
        
        execution_price = metrics.average_execution_price
        quantity = metrics.executed_quantity
        execution_value = quantity * execution_price
        benchmark_value = quantity * benchmark_price
        
        # Calculate price difference
        if metrics.side == OrderSide.BUY:
            price_diff = execution_price - benchmark_price
        else:
            price_diff = benchmark_price - execution_price
        
        # Total cost in basis points
        total_cost_bps = (price_diff / benchmark_price) * 10000 if benchmark_price > 0 else 0
        total_cost_amount = price_diff * quantity
        
        # Decompose costs
        
        # 1. Spread cost (bid-ask spread capture)
        spread_cost_bps = abs(metrics.slippage_bps) * 0.3  # Estimate 30% of slippage is spread
        spread_cost_amount = (spread_cost_bps / 10000) * benchmark_price * quantity
        
        # 2. Market impact (temporary + permanent)
        market_impact_bps = abs(metrics.slippage_bps) * 0.5  # Estimate 50% is market impact
        market_impact_amount = (market_impact_bps / 10000) * benchmark_price * quantity
        
        # 3. Timing cost
        timing_cost_bps = abs(metrics.slippage_bps) * 0.2  # Estimate 20% is timing
        timing_cost_amount = (timing_cost_bps / 10000) * benchmark_price * quantity
        
        # 4. Commission
        total_commission = sum(exec.commission for exec in getattr(metrics, 'executions', []))
        commission_bps = (total_commission / execution_value) * 10000 if execution_value > 0 else 0
        
        # 5. Fees
        total_fees = sum(exec.fees for exec in getattr(metrics, 'executions', []))
        fees_bps = (total_fees / execution_value) * 10000 if execution_value > 0 else 0
        
        # 6. Opportunity cost (for partial fills)
        opportunity_cost_bps = 0
        opportunity_cost_amount = 0
        if metrics.executed_quantity < metrics.total_quantity:
            unfilled_ratio = 1 - (metrics.executed_quantity / metrics.total_quantity)
            opportunity_cost_bps = unfilled_ratio * 5  # Estimate 5 bps per 100% unfilled
            opportunity_cost_amount = (opportunity_cost_bps / 10000) * benchmark_price * quantity
        
        return TransactionCostBreakdown(
            order_id=metrics.order_id,
            symbol=metrics.symbol,
            side=metrics.side,
            quantity=quantity,
            execution_value=execution_value,
            benchmark_value=benchmark_value,
            benchmark_type=benchmark_type,
            
            # Basis points
            spread_cost_bps=spread_cost_bps,
            market_impact_bps=market_impact_bps,
            timing_cost_bps=timing_cost_bps,
            commission_bps=commission_bps,
            fees_bps=fees_bps,
            opportunity_cost_bps=opportunity_cost_bps,
            total_cost_bps=total_cost_bps,
            
            # Absolute amounts
            spread_cost_amount=spread_cost_amount,
            market_impact_amount=market_impact_amount,
            timing_cost_amount=timing_cost_amount,
            commission_amount=total_commission,
            fees_amount=total_fees,
            opportunity_cost_amount=opportunity_cost_amount,
            total_cost_amount=total_cost_amount
        )
    
    async def _get_benchmark_price(
        self,
        symbol: str,
        benchmark_type: BenchmarkType,
        timestamp: datetime
    ) -> float:
        """Get benchmark price for cost calculation"""
        
        # In a real implementation, this would fetch from market data
        # For now, simulate benchmark prices
        
        if benchmark_type == BenchmarkType.ARRIVAL_PRICE:
            # Simulate arrival price (price when order was created)
            base_price = 100.0
            return base_price + np.random.normal(0, 0.1)
        
        elif benchmark_type == BenchmarkType.VWAP:
            # Simulate VWAP
            base_price = 100.0
            return base_price + np.random.normal(0, 0.05)
        
        elif benchmark_type == BenchmarkType.TWAP:
            # Simulate TWAP
            base_price = 100.0
            return base_price + np.random.normal(0, 0.05)
        
        elif benchmark_type == BenchmarkType.MIDPOINT:
            # Simulate midpoint
            base_price = 100.0
            return base_price
        
        else:
            # Default to arrival price
            return 100.0
    
    async def _analyze_market_microstructure(
        self,
        symbol: str,
        market_data: Dict[str, Any]
    ) -> MarketMicrostructure:
        """Analyze market microstructure"""
        
        # Extract market data
        bid_price = market_data.get('bid_price', 99.95)
        ask_price = market_data.get('ask_price', 100.05)
        bid_size = market_data.get('bid_size', 1000)
        ask_size = market_data.get('ask_size', 1000)
        last_price = market_data.get('last_price', 100.0)
        volume = market_data.get('volume', 100000)
        volatility = market_data.get('volatility', 0.2)
        
        # Calculate spreads
        bid_ask_spread = ask_price - bid_price
        effective_spread = bid_ask_spread / 2  # Simplified
        realized_spread = effective_spread * 0.8  # Estimate
        
        # Calculate depth
        total_depth = bid_size + ask_size
        
        # Estimate impacts
        temporary_impact = (bid_ask_spread / last_price) * 0.5 * 10000  # bps
        permanent_impact = temporary_impact * 0.3  # Estimate
        
        # Calculate volatility metrics
        intraday_volatility = volatility / np.sqrt(252)  # Daily to intraday
        price_variance = (last_price * intraday_volatility) ** 2
        
        # Calculate volume metrics
        avg_daily_volume = market_data.get('avg_daily_volume', 1000000)
        turnover_rate = volume / avg_daily_volume if avg_daily_volume > 0 else 0
        volume_concentration = min(1.0, volume / 10000)  # Simplified
        
        # Calculate quality metrics
        price_efficiency = max(0.1, 1.0 - (bid_ask_spread / last_price))
        liquidity_score = min(1.0, total_depth / 10000)  # Simplified
        
        return MarketMicrostructure(
            symbol=symbol,
            timestamp=datetime.now(),
            bid_ask_spread=bid_ask_spread,
            effective_spread=effective_spread,
            realized_spread=realized_spread,
            bid_depth=bid_size,
            ask_depth=ask_size,
            total_depth=total_depth,
            temporary_impact=temporary_impact,
            permanent_impact=permanent_impact,
            intraday_volatility=intraday_volatility,
            price_variance=price_variance,
            turnover_rate=turnover_rate,
            volume_concentration=volume_concentration,
            price_efficiency=price_efficiency,
            liquidity_score=liquidity_score
        )
    
    def _extract_market_conditions(self, microstructure: MarketMicrostructure) -> Dict[str, float]:
        """Extract market conditions for cost analysis"""
        return {
            'spread_bps': (microstructure.bid_ask_spread / 100.0) * 10000,  # Assuming $100 stock
            'depth_score': microstructure.liquidity_score,
            'volatility_score': min(1.0, microstructure.intraday_volatility / 0.02),
            'efficiency_score': microstructure.price_efficiency,
            'turnover_score': min(1.0, microstructure.turnover_rate)
        }
    
    async def _perform_cost_attribution(
        self,
        cost_breakdown: TransactionCostBreakdown,
        execution_report: ExecutionReport,
        market_data: Optional[Dict[str, Any]]
    ) -> CostAttribution:
        """Perform detailed cost attribution analysis"""
        
        total_cost_bps = abs(cost_breakdown.total_cost_bps)
        
        # Factor attribution (simplified model)
        
        # Market structure impact (spread, depth)
        spread_contribution = cost_breakdown.spread_cost_bps / total_cost_bps if total_cost_bps > 0 else 0
        market_structure_impact = spread_contribution * 100
        
        # Timing impact
        timing_contribution = cost_breakdown.timing_cost_bps / total_cost_bps if total_cost_bps > 0 else 0
        timing_impact = timing_contribution * 100
        
        # Size impact
        order_size = execution_report.metrics.executed_quantity
        size_score = min(1.0, order_size / 10000)  # Normalize by 10k shares
        size_impact = size_score * 30  # Up to 30% attribution
        
        # Volatility impact
        volatility_impact = 15  # Simplified - assume 15% on average
        
        # Liquidity impact
        liquidity_impact = 20  # Simplified - assume 20% on average
        
        # Execution impact (remaining)
        execution_impact = max(0, 100 - (market_structure_impact + timing_impact + 
                                       size_impact + volatility_impact + liquidity_impact))
        
        # Normalize to 100%
        total_attribution = (market_structure_impact + timing_impact + size_impact + 
                           volatility_impact + liquidity_impact + execution_impact)
        
        if total_attribution > 0:
            normalization_factor = 100 / total_attribution
            market_structure_impact *= normalization_factor
            timing_impact *= normalization_factor
            size_impact *= normalization_factor
            volatility_impact *= normalization_factor
            liquidity_impact *= normalization_factor
            execution_impact *= normalization_factor
        
        # Cost decomposition
        systematic_cost = total_cost_bps * 0.6  # Unavoidable cost
        alpha_cost = total_cost_bps * 0.2       # Information cost
        execution_cost = total_cost_bps * 0.2   # Execution quality cost
        
        # Generate recommendations
        recommendations = []
        
        if market_structure_impact > 40:
            recommendations.append("High spread cost - consider using dark pools or crossing networks")
        
        if timing_impact > 30:
            recommendations.append("High timing cost - consider faster execution strategies")
        
        if size_impact > 35:
            recommendations.append("High size impact - consider breaking order into smaller pieces")
        
        if execution_impact > 25:
            recommendations.append("High execution cost - review venue selection and algorithms")
        
        return CostAttribution(
            order_id=cost_breakdown.order_id,
            total_cost_bps=total_cost_bps,
            market_structure_impact=market_structure_impact,
            timing_impact=timing_impact,
            size_impact=size_impact,
            volatility_impact=volatility_impact,
            liquidity_impact=liquidity_impact,
            execution_impact=execution_impact,
            systematic_cost=systematic_cost,
            alpha_cost=alpha_cost,
            execution_cost=execution_cost,
            recommendations=recommendations
        )
    
    def _linear_impact_model(self, order_size: float, adv: float) -> float:
        """Linear market impact model"""
        participation_rate = order_size / adv if adv > 0 else 0
        return 0.1 * participation_rate * 10000  # bps
    
    def _square_root_impact_model(self, order_size: float, adv: float) -> float:
        """Square root market impact model"""
        participation_rate = order_size / adv if adv > 0 else 0
        return 0.05 * np.sqrt(participation_rate) * 10000  # bps
    
    def _almgren_chriss_impact_model(self, order_size: float, adv: float, volatility: float = 0.2) -> float:
        """Almgren-Chriss market impact model"""
        participation_rate = order_size / adv if adv > 0 else 0
        return volatility * 0.1 * np.sqrt(participation_rate) * 10000  # bps
    
    async def _update_cost_statistics(self, cost_breakdown: TransactionCostBreakdown) -> None:
        """Update cost analysis statistics"""
        
        with self._lock:
            stats = self._cost_statistics
            
            # Update counters
            stats['total_trades_analyzed'] += 1
            count = stats['total_trades_analyzed']
            
            # Update averages
            current_avg_total = stats['average_total_cost_bps']
            new_total = abs(cost_breakdown.total_cost_bps)
            stats['average_total_cost_bps'] = (
                (current_avg_total * (count - 1) + new_total) / count
            )
            
            current_avg_spread = stats['average_spread_cost_bps']
            new_spread = cost_breakdown.spread_cost_bps
            stats['average_spread_cost_bps'] = (
                (current_avg_spread * (count - 1) + new_spread) / count
            )
            
            current_avg_impact = stats['average_market_impact_bps']
            new_impact = cost_breakdown.market_impact_bps
            stats['average_market_impact_bps'] = (
                (current_avg_impact * (count - 1) + new_impact) / count
            )
            
            # High cost trades
            if abs(cost_breakdown.total_cost_bps) > self.cost_threshold_bps:
                stats['high_cost_trades'] += 1
            
            # Cost efficiency score (inverse of average cost)
            avg_cost = stats['average_total_cost_bps']
            stats['cost_efficiency_score'] = max(0, 100 - avg_cost)
    
    def get_cost_analysis_summary(self, symbol: Optional[str] = None, hours: int = 24) -> Dict[str, Any]:
        """Get cost analysis summary"""
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # Filter analyses
        if symbol:
            with self._lock:
                analyses = [
                    analysis for analysis in self._cost_by_symbol.get(symbol, [])
                    if analysis.timestamp >= cutoff_time
                ]
        else:
            with self._lock:
                analyses = [
                    analysis for analysis in self._cost_analyses
                    if analysis.timestamp >= cutoff_time
                ]
        
        if not analyses:
            return {'message': 'No cost analyses available for the specified period'}
        
        # Calculate summary statistics
        total_costs = [abs(analysis.total_cost_bps) for analysis in analyses]
        spread_costs = [analysis.spread_cost_bps for analysis in analyses]
        impact_costs = [analysis.market_impact_bps for analysis in analyses]
        
        summary = {
            'period_hours': hours,
            'total_trades': len(analyses),
            'symbol': symbol,
            'cost_statistics': {
                'average_total_cost_bps': np.mean(total_costs),
                'median_total_cost_bps': np.median(total_costs),
                'std_total_cost_bps': np.std(total_costs),
                'min_total_cost_bps': np.min(total_costs),
                'max_total_cost_bps': np.max(total_costs),
                'percentile_75_cost_bps': np.percentile(total_costs, 75),
                'percentile_95_cost_bps': np.percentile(total_costs, 95)
            },
            'component_breakdown': {
                'average_spread_cost_bps': np.mean(spread_costs),
                'average_impact_cost_bps': np.mean(impact_costs),
                'spread_cost_percentage': np.mean(spread_costs) / np.mean(total_costs) * 100 if np.mean(total_costs) > 0 else 0,
                'impact_cost_percentage': np.mean(impact_costs) / np.mean(total_costs) * 100 if np.mean(total_costs) > 0 else 0
            },
            'high_cost_trades': len([c for c in total_costs if c > self.cost_threshold_bps]),
            'cost_efficiency_score': max(0, 100 - np.mean(total_costs))
        }
        
        return summary
    
    def get_cost_by_symbol(self, hours: int = 24) -> Dict[str, Dict[str, float]]:
        """Get cost breakdown by symbol"""
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        symbol_costs = {}
        
        with self._lock:
            for symbol, analyses in self._cost_by_symbol.items():
                recent_analyses = [
                    analysis for analysis in analyses
                    if analysis.timestamp >= cutoff_time
                ]
                
                if recent_analyses:
                    total_costs = [abs(analysis.total_cost_bps) for analysis in recent_analyses]
                    symbol_costs[symbol] = {
                        'trade_count': len(recent_analyses),
                        'average_cost_bps': np.mean(total_costs),
                        'total_volume': sum(analysis.quantity for analysis in recent_analyses),
                        'cost_efficiency': max(0, 100 - np.mean(total_costs))
                    }
        
        return symbol_costs
    
    def get_cost_statistics(self) -> Dict[str, Any]:
        """Get overall cost statistics"""
        with self._lock:
            return self._cost_statistics.copy()
    
    def get_recent_high_cost_trades(self, hours: int = 24) -> List[TransactionCostBreakdown]:
        """Get recent high-cost trades"""
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            high_cost_trades = [
                analysis for analysis in self._cost_analyses
                if (analysis.timestamp >= cutoff_time and 
                    abs(analysis.total_cost_bps) > self.cost_threshold_bps)
            ]
        
        # Sort by cost (highest first)
        high_cost_trades.sort(key=lambda x: abs(x.total_cost_bps), reverse=True)
        
        return high_cost_trades
    
    async def cleanup(self) -> None:
        """Cleanup transaction cost analyzer resources"""
        logger.info("TransactionCostAnalyzer cleanup completed")