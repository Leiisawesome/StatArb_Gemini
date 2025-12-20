"""
Unified Execution Engine - TradeDesk Architecture Compliance
===========================================================

Central execution hub that consolidates all execution capabilities under RiskManager control.
Implements the ACTION layer in the institutional WHAT → HOW → ACTION hierarchy.

Architecture Compliance (Tier-1 Rules):
- Rule 1: System Architecture - Layer 5 (Trading & Execution)
- Rule 5: Execution & Order Management - Phase 13 (Execution Action)
  - Receives orders from OMS (Phase 12)
  - Executes trades per algorithm (MARKET/TWAP/VWAP/ADAPTIVE)
  - Reports fills to RiskManager for position update (Phase 15)
  - Triggers TCA analytics (Phase 16)

Key Responsibilities:
- All execution flows through RiskManager authorization (Rule 3)
- Complete trade lifecycle management
- Institutional-grade execution algorithms
- Comprehensive execution analytics and reporting (Rule 4)
- Operates exclusively under RiskManager authority
- No independent trading decisions
- All executions require authorization tokens
- Complete audit trail and risk integration

Migration: December 2025 - Former Rule 7 content now Rule 5.

Author: StatArb_Gemini Architecture Compliance
Version: 2.0.0 (Rules Migration December 2025)
"""

import asyncio
import logging
import threading
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field

from core_engine.exceptions import ConfigurationRequiredError
from enum import Enum
from abc import ABC, abstractmethod
import numpy as np
from collections import defaultdict
import warnings

# Import ISystemComponent for orchestrator integration
from .interfaces import ISystemComponent

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)

class ExecutionStatus(Enum):
    """Execution status"""
    PENDING_AUTHORIZATION = "pending_authorization"
    AUTHORIZED = "authorized"
    EXECUTING = "executing"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    FAILED = "failed"
    EXPIRED = "expired"

class ExecutionAlgorithm(Enum):
    """Execution algorithm types"""
    MARKET = "market"
    LIMIT = "limit"
    TWAP = "twap"  # Time-Weighted Average Price
    VWAP = "vwap"  # Volume-Weighted Average Price
    POV = "pov"    # Participation of Volume
    IS = "implementation_shortfall"
    ICEBERG = "iceberg"
    SNIPER = "sniper"
    GUERRILLA = "guerrilla"
    ADAPTIVE = "adaptive"
    SMART_ROUTING = "smart_routing"

class ExecutionUrgency(Enum):
    """Execution urgency levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    EMERGENCY = "emergency"

class VenueType(Enum):
    """Trading venue types"""
    EXCHANGE = "exchange"
    ECN = "ecn"
    DARK_POOL = "dark_pool"
    MARKET_MAKER = "market_maker"
    CROSSING_NETWORK = "crossing_network"

@dataclass
class ExecutionAuthorization:
    """Risk Manager authorization for execution"""

    authorization_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    risk_manager_id: str = ""

    # Authorization details
    symbol: str = ""
    side: str = ""  # buy/sell
    quantity: float = 0.0
    max_quantity: float = 0.0  # Maximum authorized quantity
    price_limit: Optional[float] = None

    # Risk constraints
    max_position_impact: float = 0.05  # 5% max position impact
    max_market_impact: float = 0.01   # 1% max market impact
    max_execution_time: int = 3600     # 1 hour max execution time

    # Authorization metadata
    strategy_id: str = ""
    risk_budget_allocation: float = 0.0
    authorized_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime = field(default_factory=lambda: datetime.now() + timedelta(hours=1))

    # Execution constraints
    allowed_algorithms: List[ExecutionAlgorithm] = field(default_factory=list)
    allowed_venues: List[str] = field(default_factory=list)
    urgency_level: ExecutionUrgency = ExecutionUrgency.NORMAL

    # Validation
    is_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)

    def validate_authorization(self) -> bool:
        """Validate authorization is still valid"""

        if datetime.now() > self.expires_at:
            self.is_valid = False
            self.validation_errors.append("Authorization expired")
            return False

        if not self.symbol or not self.side:
            self.is_valid = False
            self.validation_errors.append("Missing required fields")
            return False

        if self.quantity <= 0 or self.max_quantity <= 0:
            self.is_valid = False
            self.validation_errors.append("Invalid quantities")
            return False

        if not self.allowed_algorithms:
            self.is_valid = False
            self.validation_errors.append("No allowed algorithms specified")
            return False

        return True

@dataclass
class ExecutionRequest:
    """Execution request with risk authorization"""

    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    authorization: ExecutionAuthorization = field(default_factory=ExecutionAuthorization)

    # Execution parameters
    algorithm: ExecutionAlgorithm = ExecutionAlgorithm.ADAPTIVE
    urgency: ExecutionUrgency = ExecutionUrgency.NORMAL
    time_horizon: int = 300  # 5 minutes default

    # Algorithm-specific parameters
    algorithm_params: Dict[str, Any] = field(default_factory=dict)
    venue_preferences: List[str] = field(default_factory=list)

    # Execution constraints
    max_participation_rate: float = 0.20  # 20% max volume participation
    min_fill_size: float = 100
    max_slice_size: float = 1000

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    priority: int = 5  # 1-10 scale
    strategy_context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ExecutionResult:
    """Execution result and analytics"""

    request_id: str = ""
    authorization_id: str = ""

    # Execution outcome
    status: ExecutionStatus = ExecutionStatus.PENDING_AUTHORIZATION
    filled_quantity: float = 0.0
    remaining_quantity: float = 0.0
    avg_fill_price: float = 0.0
    algorithm_used: ExecutionAlgorithm = ExecutionAlgorithm.MARKET

    # Execution analytics
    total_cost: float = 0.0
    market_impact: float = 0.0
    timing_cost: float = 0.0
    commission_cost: float = 0.0
    slippage: float = 0.0

    # Performance metrics
    implementation_shortfall: float = 0.0
    participation_rate: float = 0.0
    execution_time: float = 0.0  # seconds
    venue_breakdown: Dict[str, float] = field(default_factory=dict)

    # Risk compliance
    risk_limit_breaches: List[str] = field(default_factory=list)
    position_impact: float = 0.0
    portfolio_impact: float = 0.0

    # Timestamps
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Fill details
    fills: List[Dict[str, Any]] = field(default_factory=list)
    execution_log: List[str] = field(default_factory=list)

@dataclass
class MarketImpactModel:
    """Market impact estimation model"""

    # Linear impact parameters
    linear_coeff: float = 0.001
    sqrt_coeff: float = 0.0005
    permanent_impact_ratio: float = 0.3

    # Volatility adjustments
    volatility_multiplier: float = 1.0

    # Liquidity parameters
    avg_daily_volume: float = 1000000
    typical_spread: float = 0.01

    def estimate_impact(self, quantity: float, price: float, urgency: ExecutionUrgency) -> float:
        """Estimate market impact for execution"""

        try:
            # Volume percentage
            volume_pct = quantity / self.avg_daily_volume

            # Base impact
            linear_impact = self.linear_coeff * volume_pct
            sqrt_impact = self.sqrt_coeff * np.sqrt(volume_pct)
            base_impact = linear_impact + sqrt_impact

            # Urgency adjustment
            urgency_multiplier = {
                ExecutionUrgency.LOW: 0.7,
                ExecutionUrgency.NORMAL: 1.0,
                ExecutionUrgency.HIGH: 1.5,
                ExecutionUrgency.URGENT: 2.0,
                ExecutionUrgency.EMERGENCY: 3.0
            }.get(urgency, 1.0)

            # Total impact
            total_impact = base_impact * urgency_multiplier * self.volatility_multiplier

            return min(total_impact, 0.05)  # Cap at 5%

        except Exception as e:
            logger.error(f"Error estimating market impact: {e}")
            return 0.01  # Conservative default

class IExecutionAlgorithm(ABC):
    """Interface for execution algorithms"""

    @abstractmethod
    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute the trade request"""

    @abstractmethod
    def estimate_execution_time(self, request: ExecutionRequest) -> float:
        """Estimate execution time in seconds"""

    @abstractmethod
    async def estimate_market_impact(self, request: ExecutionRequest) -> float:
        """Estimate market impact"""

class TWAPAlgorithm(IExecutionAlgorithm):
    """Time-Weighted Average Price execution algorithm"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.test_mode = False
        self.impact_model = MarketImpactModel()

    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute TWAP strategy"""

        try:
            result = ExecutionResult(
                request_id=request.request_id,
                authorization_id=request.authorization.authorization_id,
                status=ExecutionStatus.EXECUTING,
                algorithm_used=request.algorithm
            )

            # Calculate execution parameters
            total_quantity = request.authorization.quantity
            time_horizon = request.time_horizon
            slice_interval = max(30, time_horizon // 10)  # At least 30 seconds
            slice_size = total_quantity / (time_horizon // slice_interval)

            logger.info(f"Starting TWAP execution: {total_quantity} shares over {time_horizon}s")

            # Execute slices
            executed_quantity = 0.0
            start_time = datetime.now()

            while executed_quantity < total_quantity:
                remaining = total_quantity - executed_quantity
                current_slice = min(slice_size, remaining)

                # Simulate execution (replace with actual broker interface)
                if not self.test_mode:
                    await asyncio.sleep(0.1)  # Simulate network latency

                # Execute through real broker - no mock data
                if not hasattr(self, 'broker_adapter') or not self.broker_adapter:
                    raise ConfigurationRequiredError("Broker adapter required for trade execution")

                try:
                    fill_result = await self.broker_adapter.execute_order({
                        'symbol': request.authorization.symbol,
                        'side': request.authorization.side,
                        'quantity': current_slice,
                        'order_type': 'market'
                    })

                    if not fill_result or not fill_result.get('filled'):
                        raise ConfigurationRequiredError(f"Order execution failed: {fill_result}")

                    fill_price = fill_result.get('fill_price')
                    fill_qty = fill_result.get('fill_quantity')

                    if not fill_price or not fill_qty or fill_price <= 0 or fill_qty <= 0:
                        raise ConfigurationRequiredError(f"Invalid fill data: price={fill_price}, qty={fill_qty}")

                    executed_quantity += fill_qty
                    result.fills.append({
                        'timestamp': datetime.now(),
                        'quantity': fill_qty,
                        'price': fill_price,
                        'venue': fill_result.get('venue', 'UNKNOWN')
                    })
                except Exception as e:
                    raise ConfigurationRequiredError(f"Broker execution failed: {e}")

                # Wait for next slice
                if executed_quantity < total_quantity and not self.test_mode:
                    await asyncio.sleep(slice_interval)

            # Calculate final metrics
            result.filled_quantity = executed_quantity
            result.remaining_quantity = 0.0
            result.avg_fill_price = np.mean([fill['price'] for fill in result.fills])
            result.status = ExecutionStatus.FILLED
            result.completed_at = datetime.now()
            result.execution_time = (result.completed_at - start_time).total_seconds()

            logger.info(f"TWAP execution completed: {executed_quantity} @ {result.avg_fill_price:.4f}")
            return result

        except Exception as e:
            logger.error(f"TWAP execution failed: {e}")
            result.status = ExecutionStatus.FAILED
            result.execution_log.append(f"Execution failed: {e}")
            return result

    def estimate_execution_time(self, request: ExecutionRequest) -> float:
        """Estimate TWAP execution time"""
        return float(request.time_horizon)

    async def _get_current_price(self, symbol: str) -> float:
        """Get current price for a symbol"""
        if self.test_mode:
            return 100.0  # Default test price

        if hasattr(self, 'market_data_manager') and self.market_data_manager:
            try:
                market_data = await self.market_data_manager.get_current_price(symbol)
                if market_data and 'price' in market_data:
                    return market_data['price']
            except Exception as e:
                logger.warning(f"Failed to get current price for {symbol}: {e}")

        return 100.0  # Fallback default price

    async def estimate_market_impact(self, request: ExecutionRequest) -> float:
        """Estimate TWAP market impact"""
        current_price = await self._get_current_price(request.authorization.symbol)
        return self.impact_model.estimate_impact(
            request.authorization.quantity,
            current_price,
            request.urgency
        ) * 0.7  # TWAP typically reduces impact

class MarketAlgorithm(IExecutionAlgorithm):
    """Market order execution algorithm"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.test_mode = False
        self.impact_model = MarketImpactModel()

    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute market order"""

        try:
            result = ExecutionResult(
                request_id=request.request_id,
                authorization_id=request.authorization.authorization_id,
                status=ExecutionStatus.EXECUTING,
                started_at=datetime.now(),
                algorithm_used=request.algorithm
            )

            # Simulate immediate execution
            if not self.test_mode:
                await asyncio.sleep(0.05)  # 50ms latency

            quantity = request.authorization.quantity

            # Get fill price - use test mode price if available, otherwise use market data manager
            if self.test_mode:
                # Test mode: Use price from execution request (backtest simulation)
                fill_price = None

                # Try to get price from algorithm_params (set by test)
                if request.algorithm_params and 'current_price' in request.algorithm_params:
                    fill_price = request.algorithm_params.get('current_price')
                elif request.algorithm_params and 'estimated_fill_price' in request.algorithm_params:
                    fill_price = request.algorithm_params.get('estimated_fill_price')
                elif request.strategy_context and 'current_price' in request.strategy_context:
                    fill_price = request.strategy_context.get('current_price')

                if fill_price is None or fill_price <= 0:
                    # Fallback: Use a default price if not provided (shouldn't happen in test)
                    logger.warning(f"Test mode: No price in request, using default price for {request.authorization.symbol}")
                    fill_price = 100.0  # Default fallback price
            else:
                # Production mode: Get real market price from market data manager
                if not hasattr(self, 'market_data_manager') or not self.market_data_manager:
                    raise ConfigurationRequiredError("Market data manager required for price data")

                try:
                    market_data = await self.market_data_manager.get_current_price(request.authorization.symbol)
                    if not market_data or 'price' not in market_data:
                        raise ConfigurationRequiredError(f"No price data available for {request.authorization.symbol}")

                    fill_price = market_data['price']
                    if fill_price <= 0:
                        raise ConfigurationRequiredError(f"Invalid price data: {fill_price}")
                except Exception as e:
                    raise ConfigurationRequiredError(f"Failed to get market price: {e}")

            # AUDIT FIX #6: Simulate realistic partial fills based on order size
            # Larger orders relative to market volume have lower fill rates
            filled_quantity = quantity
            fill_rate = 1.0  # Default to 100% fill

            if self.test_mode and request.algorithm_params and 'simulate_partial_fills' in request.algorithm_params:
                # Calculate order value in dollars
                order_value = quantity * fill_price

                # Partial fill logic based on order size:
                # - Small orders (<$10k): 99-100% fill rate
                # - Medium orders ($10k-$50k): 97-99% fill rate
                # - Large orders ($50k-$100k): 95-97% fill rate
                # - Very large orders (>$100k): 90-95% fill rate

                import random
                random.seed(int(request.authorization.authorized_at.timestamp() * 1000))  # Deterministic based on authorized_at

                if order_value < 10000:
                    fill_rate = random.uniform(0.99, 1.0)
                elif order_value < 50000:
                    fill_rate = random.uniform(0.97, 0.99)
                elif order_value < 100000:
                    fill_rate = random.uniform(0.95, 0.97)
                else:
                    fill_rate = random.uniform(0.90, 0.95)

                filled_quantity = quantity * fill_rate

                if fill_rate < 1.0:
                    logger.info(f"Partial fill simulation: {filled_quantity:.2f}/{quantity:.2f} shares ({fill_rate*100:.1f}% fill rate, order value: ${order_value:,.0f})")

            result.filled_quantity = filled_quantity
            result.remaining_quantity = quantity - filled_quantity
            result.avg_fill_price = fill_price
            # AUDIT FIX #6: Set status based on fill rate
            if result.remaining_quantity > 0.01:  # Threshold to avoid floating point issues
                result.status = ExecutionStatus.PARTIALLY_FILLED
            else:
                result.status = ExecutionStatus.FILLED
            result.completed_at = datetime.now()
            result.execution_time = (result.completed_at - result.started_at).total_seconds()

            # Initialize fills list if not already initialized
            if not hasattr(result, 'fills') or result.fills is None:
                result.fills = []

            # AUDIT FIX #6: Record actual filled quantity (may be partial)
            result.fills.append({
                'timestamp': result.completed_at,
                'quantity': filled_quantity,  # Use filled_quantity instead of requested quantity
                'price': fill_price,
                'venue': 'SIMULATED_EXCHANGE' if self.test_mode else 'MOCK_EXCHANGE'
            })

            # Calculate execution quality metrics (for test mode, use minimal costs)
            estimated_impact_bps = request.algorithm_params.get('estimated_impact_bps', 0.0) if request.algorithm_params else 0.0

            if self.test_mode:
                # Simulated execution costs (minimal for backtest)
                result.commission_cost = 0.0  # No commission in simulation
                result.slippage = 0.0  # No slippage in simulation (use slippage field)
                result.market_impact = estimated_impact_bps * fill_price * quantity / 10000  # Convert bps to dollars
                result.total_cost = result.market_impact  # Total cost in dollars
            else:
                # Production mode: Calculate real execution costs
                result.commission_cost = 0.0  # TODO: Get from broker
                result.slippage = 0.0  # TODO: Calculate from arrival price
                result.market_impact = estimated_impact_bps * fill_price * quantity / 10000
                result.total_cost = result.commission_cost + result.market_impact

            # AUDIT FIX #6: Log partial fills
            if result.remaining_quantity > 0.01:
                logger.info(f"Market execution PARTIALLY FILLED: {filled_quantity:.2f}/{quantity:.2f} @ {fill_price:.4f} (test_mode={self.test_mode})")
            else:
                logger.info(f"Market execution completed: {quantity:.2f} @ {fill_price:.4f} (test_mode={self.test_mode})")
            return result

        except Exception as e:
            logger.error(f"Market execution failed: {e}")
            result.status = ExecutionStatus.FAILED
            result.execution_log.append(f"Execution failed: {e}")
            return result

    def estimate_execution_time(self, request: ExecutionRequest) -> float:
        """Estimate market execution time"""
        return 1.0  # Nearly instant

    async def estimate_market_impact(self, request: ExecutionRequest) -> float:
        """Estimate market impact"""
        return self.impact_model.estimate_impact(
            request.authorization.quantity,
            100.0,
            request.urgency
        )

class AdaptiveAlgorithm(IExecutionAlgorithm):
    """Adaptive execution algorithm that selects optimal strategy"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._test_mode = False
        self.impact_model = MarketImpactModel()
        self.twap = TWAPAlgorithm(config)
        self.market = MarketAlgorithm(config)

    @property
    def test_mode(self) -> bool:
        """Get test mode"""
        return self._test_mode

    @test_mode.setter
    def test_mode(self, value: bool):
        """Set test mode and propagate to sub-algorithms"""
        self._test_mode = value
        self.twap.test_mode = value
        self.market.test_mode = value

    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute adaptive strategy"""

        try:
            # Select optimal algorithm based on request characteristics
            algorithm = self._select_algorithm(request)

            logger.info(f"Adaptive algorithm selected: {algorithm.__class__.__name__}")

            # Execute using selected algorithm
            return await algorithm.execute(request)

        except Exception as e:
            logger.error(f"Adaptive execution failed: {e}")
            result = ExecutionResult(
                request_id=request.request_id,
                authorization_id=request.authorization.authorization_id,
                status=ExecutionStatus.FAILED,
                algorithm_used=request.algorithm
            )
            result.execution_log.append(f"Execution failed: {e}")
            return result

    def _select_algorithm(self, request: ExecutionRequest) -> IExecutionAlgorithm:
        """Select optimal execution algorithm"""

        quantity = request.authorization.quantity
        urgency = request.urgency
        time_horizon = request.time_horizon

        # Use market orders for small, urgent trades
        if urgency in [ExecutionUrgency.URGENT, ExecutionUrgency.EMERGENCY]:
            return self.market

        # Use market orders for very small quantities
        if quantity < 1000:
            return self.market

        # Use TWAP for larger quantities with time flexibility
        if time_horizon > 300:  # More than 5 minutes
            return self.twap

        # Default to market for simplicity
        return self.market

    def estimate_execution_time(self, request: ExecutionRequest) -> float:
        """Estimate execution time"""
        algorithm = self._select_algorithm(request)
        return algorithm.estimate_execution_time(request)

    async def estimate_market_impact(self, request: ExecutionRequest) -> float:
        """Estimate market impact"""
        algorithm = self._select_algorithm(request)
        return await algorithm.estimate_market_impact(request)

class VWAPAlgorithm(IExecutionAlgorithm):
    """
    Volume-Weighted Average Price (VWAP) execution algorithm

    Executes trades to match the volume profile of the market,
    minimizing market impact by trading in proportion to market volume.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._test_mode = False
        self.impact_model = MarketImpactModel()
        self.order_manager = OrderManager()

    @property
    def test_mode(self) -> bool:
        """Get test mode"""
        return self._test_mode

    @test_mode.setter
    def test_mode(self, value: bool):
        """Set test mode"""
        self._test_mode = value

    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """
        Execute using VWAP strategy

        Slices order to match historical volume profile
        """
        try:
            start_time = datetime.now()
            quantity = request.authorization.quantity
            symbol = request.authorization.symbol
            side = request.authorization.side

            # Get historical volume profile (mock for now)
            volume_profile = self._get_volume_profile(symbol)

            # Create order slices based on volume profile
            order_slices = self._create_vwap_slices(quantity, volume_profile, request.time_horizon)

            logger.info(
                f"🎯 VWAP execution starting: {symbol} {side.upper()} {quantity} "
                f"over {request.time_horizon}s in {len(order_slices)} slices"
            )

            # Test mode: return simulated result
            if self._test_mode:
                return self._create_test_result(request, quantity, order_slices)

            # Execute order slices
            fills = []
            total_filled = 0.0
            total_value = 0.0

            for i, (slice_qty, slice_timing) in enumerate(order_slices):
                # Wait for scheduled time
                await asyncio.sleep(slice_timing)

                # Execute slice (mock execution)
                # Get real market price for slice execution
                if not hasattr(self, 'market_data_manager') or not self.market_data_manager:
                    raise ConfigurationRequiredError("Market data manager required for slice execution")

                try:
                    market_data = await self.market_data_manager.get_current_price(request.authorization.symbol)
                    if not market_data or 'price' not in market_data:
                        raise ConfigurationRequiredError(f"No price data available for slice execution")

                    fill_price = market_data['price']
                    if fill_price <= 0:
                        raise ConfigurationRequiredError(f"Invalid price data for slice: {fill_price}")
                except Exception as e:
                    raise ConfigurationRequiredError(f"Failed to get market price for slice: {e}")
                fill_qty = slice_qty

                fill = {
                    'slice': i + 1,
                    'quantity': fill_qty,
                    'price': fill_price,
                    'timestamp': datetime.now(),
                    'value': fill_qty * fill_price
                }
                fills.append(fill)

                total_filled += fill_qty
                total_value += fill['value']

                logger.info(f"   Slice {i+1}/{len(order_slices)}: {fill_qty:.0f} @ ${fill_price:.2f}")

            # Calculate VWAP
            avg_fill_price = total_value / total_filled if total_filled > 0 else 0.0

            # Create execution result
            result = ExecutionResult(
                request_id=request.request_id,
                authorization_id=request.authorization.authorization_id,
                status=ExecutionStatus.FILLED,
                filled_quantity=total_filled,
                avg_fill_price=avg_fill_price,
                execution_time=(datetime.now() - start_time).total_seconds(),
                algorithm_used=ExecutionAlgorithm.VWAP,
                fills=fills,
                market_impact=self.estimate_market_impact(request)
            )

            result.execution_log.append(
                f"VWAP execution complete: {len(fills)} slices, "
                f"avg price=${avg_fill_price:.2f}"
            )

            return result

        except Exception as e:
            logger.error(f"VWAP execution failed: {e}")
            result = ExecutionResult(
                request_id=request.request_id,
                authorization_id=request.authorization.authorization_id,
                status=ExecutionStatus.FAILED,
                algorithm_used=ExecutionAlgorithm.VWAP
            )
            result.execution_log.append(f"Execution failed: {e}")
            return result

    def _get_volume_profile(self, symbol: str) -> List[float]:
        """
        Get historical intraday volume profile

        In production, this would query actual market data.
        Returns normalized volume distribution across trading day.
        """
        # Mock volume profile (higher volume at open/close, lower midday)
        profile = [
            0.15,  # 9:30-10:00 (high open volume)
            0.10,  # 10:00-11:00
            0.08,  # 11:00-12:00
            0.07,  # 12:00-13:00 (lunch, low volume)
            0.08,  # 13:00-14:00
            0.10,  # 14:00-15:00
            0.12,  # 15:00-15:30
            0.15,  # 15:30-16:00 (high close volume)
            0.15   # 16:00 (close)
        ]
        return profile

    def _create_vwap_slices(
        self,
        total_quantity: float,
        volume_profile: List[float],
        time_horizon: int
    ) -> List[Tuple[float, float]]:
        """
        Create order slices based on volume profile

        Returns: List of (quantity, timing_seconds) tuples
        """
        # Calculate slice quantities proportional to volume
        total_profile = sum(volume_profile)
        slices = []

        # Distribute quantity across volume periods
        time_per_slice = time_horizon / len(volume_profile)

        for i, vol_pct in enumerate(volume_profile):
            slice_qty = total_quantity * (vol_pct / total_profile)
            slice_timing = i * time_per_slice
            slices.append((slice_qty, slice_timing))

        return slices

    def _create_test_result(
        self,
        request: ExecutionRequest,
        quantity: float,
        order_slices: List[Tuple[float, float]]
    ) -> ExecutionResult:
        """Create test mode result"""
        # Simulate fills
        fills = []
        total_value = 0.0

        for i, (slice_qty, _) in enumerate(order_slices):
            fill_price = 100.0 + np.random.normal(0, 0.05)
            fills.append({
                'slice': i + 1,
                'quantity': slice_qty,
                'price': fill_price,
                'value': slice_qty * fill_price,
                'timestamp': datetime.now()
            })
            total_value += slice_qty * fill_price

        avg_price = total_value / quantity

        # Calculate market impact (use sync default since we're in test mode)
        market_impact = self.impact_model.estimate_impact(
            quantity=request.authorization.quantity,
            price=avg_price,
            urgency=request.urgency
        ) * 0.7

        return ExecutionResult(
            request_id=request.request_id,
            authorization_id=request.authorization.authorization_id,
            status=ExecutionStatus.FILLED,
            filled_quantity=quantity,
            avg_fill_price=avg_price,
            execution_time=request.time_horizon,
            algorithm_used=ExecutionAlgorithm.VWAP,
            fills=fills,
            market_impact=market_impact
        )

    def estimate_execution_time(self, request: ExecutionRequest) -> float:
        """Estimate VWAP execution time (uses full time horizon)"""
        return request.time_horizon

    async def _get_current_price(self, symbol: str) -> float:
        """Get current price for a symbol"""
        if self._test_mode:
            return 100.0  # Default test price

        if hasattr(self, 'market_data_manager') and self.market_data_manager:
            try:
                market_data = await self.market_data_manager.get_current_price(symbol)
                if market_data and 'price' in market_data:
                    return market_data['price']
            except Exception as e:
                logger.warning(f"Failed to get current price for {symbol}: {e}")

        return 100.0  # Fallback default price

    async def estimate_market_impact(self, request: ExecutionRequest) -> float:
        """Estimate market impact for VWAP execution"""
        # VWAP typically has lower impact than aggressive strategies
        current_price = await self._get_current_price(request.authorization.symbol)
        return self.impact_model.estimate_impact(
            quantity=request.authorization.quantity,
            price=current_price,
            urgency=request.urgency
        ) * 0.7  # 30% reduction vs aggressive execution

class OrderManager:
    """
    Manages order lifecycle and fill tracking

    Handles:
    - Order creation and submission
    - Fill monitoring and aggregation
    - Partial fill management
    - Order cancellation
    """

    def __init__(self):
        self.active_orders: Dict[str, Dict[str, Any]] = {}
        self.order_history: List[Dict[str, Any]] = []
        self.fills: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    def create_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "market",
        limit_price: Optional[float] = None
    ) -> str:
        """
        Create a new order

        Returns: order_id
        """
        order_id = str(uuid.uuid4())

        order = {
            'order_id': order_id,
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'order_type': order_type,
            'limit_price': limit_price,
            'status': 'pending',
            'filled_quantity': 0.0,
            'remaining_quantity': quantity,
            'avg_fill_price': 0.0,
            'created_at': datetime.now(),
            'fills': []
        }

        self.active_orders[order_id] = order
        logger.info(f"📝 Order created: {order_id} - {symbol} {side.upper()} {quantity}")

        return order_id

    def add_fill(
        self,
        order_id: str,
        fill_quantity: float,
        fill_price: float,
        fill_timestamp: Optional[datetime] = None
    ) -> bool:
        """
        Add a fill to an order

        Handles partial fills and order completion
        """
        if order_id not in self.active_orders:
            logger.warning(f"Order {order_id} not found")
            return False

        order = self.active_orders[order_id]

        if fill_timestamp is None:
            fill_timestamp = datetime.now()

        # Create fill record
        fill = {
            'fill_id': str(uuid.uuid4()),
            'quantity': fill_quantity,
            'price': fill_price,
            'timestamp': fill_timestamp,
            'value': fill_quantity * fill_price
        }

        # Update order
        order['fills'].append(fill)
        order['filled_quantity'] += fill_quantity
        order['remaining_quantity'] -= fill_quantity

        # Recalculate average fill price
        total_value = sum(f['value'] for f in order['fills'])
        order['avg_fill_price'] = total_value / order['filled_quantity']

        # Update order status
        if order['remaining_quantity'] <= 0:
            order['status'] = 'filled'
            order['completed_at'] = fill_timestamp
            logger.info(f"✅ Order {order_id[:8]}... FILLED @ ${order['avg_fill_price']:.2f}")
        else:
            order['status'] = 'partially_filled'
            logger.info(
                f"📊 Order {order_id[:8]}... PARTIAL FILL: "
                f"{order['filled_quantity']:.0f}/{order['quantity']:.0f} "
                f"@ ${fill_price:.2f}"
            )

        # Store fill
        self.fills[order_id].append(fill)

        return True

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an active order"""
        if order_id not in self.active_orders:
            logger.warning(f"Order {order_id} not found for cancellation")
            return False

        order = self.active_orders[order_id]
        order['status'] = 'cancelled'
        order['cancelled_at'] = datetime.now()

        # Move to history
        self.order_history.append(order)
        del self.active_orders[order_id]

        logger.info(f"❌ Order {order_id[:8]}... cancelled")
        return True

    def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get order status and fills"""
        if order_id in self.active_orders:
            return self.active_orders[order_id]

        # Check history
        for order in reversed(self.order_history):
            if order['order_id'] == order_id:
                return order

        return None

    def get_fills(self, order_id: str) -> List[Dict[str, Any]]:
        """Get all fills for an order"""
        return self.fills.get(order_id, [])

    def get_active_orders(self) -> Dict[str, Dict[str, Any]]:
        """Get all active orders"""
        return self.active_orders.copy()

class ExecutionValidator:
    """Validates execution requests against authorization and risk limits"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def validate_request(self, request: ExecutionRequest) -> Tuple[bool, List[str]]:
        """Validate execution request"""

        errors = []

        # Validate authorization
        if not request.authorization.validate_authorization():
            errors.extend(request.authorization.validation_errors)

        # Validate algorithm is allowed
        if (request.authorization.allowed_algorithms and
            request.algorithm not in request.authorization.allowed_algorithms):
            errors.append(f"Algorithm {request.algorithm} not authorized")

        # Validate quantity limits
        if request.authorization.quantity > request.authorization.max_quantity:
            errors.append("Quantity exceeds authorized maximum")

        # Validate time limits
        max_time = request.authorization.max_execution_time
        if request.time_horizon > max_time:
            errors.append(f"Time horizon {request.time_horizon}s exceeds limit {max_time}s")

        return len(errors) == 0, errors

class UnifiedExecutionEngine(ISystemComponent):
    """
    Unified Execution Engine - TradeDesk Architecture Compliance

    Central execution authority operating exclusively under RiskManager control.
    Implements the ACTION layer in the institutional hierarchy.

    Key Features:
    - Mandatory RiskManager authorization for all executions
    - Comprehensive execution algorithms (TWAP, VWAP, Market, Adaptive)
    - Real-time execution monitoring and analytics
    - Complete audit trail and risk compliance
    - Institutional-grade execution performance
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize unified execution engine"""

        self.config = config

        # Test mode configuration for faster testing
        self.test_mode = config.get('test_mode', False)
        self.simulation_delay = 0.0 if self.test_mode else 0.1  # No delay in test mode

        # Core components
        self.validator = ExecutionValidator(config)
        self.impact_model = MarketImpactModel()

        # Execution algorithms
        self.algorithms = {
            ExecutionAlgorithm.MARKET: MarketAlgorithm(config),
            ExecutionAlgorithm.TWAP: TWAPAlgorithm(config),
            ExecutionAlgorithm.VWAP: VWAPAlgorithm(config),  # Week 3 Day 1: VWAP added
            ExecutionAlgorithm.ADAPTIVE: AdaptiveAlgorithm(config)
        }

        # Pass test mode to algorithms
        for algorithm in self.algorithms.values():
            algorithm.test_mode = self.test_mode

        # Execution tracking
        self.active_executions: Dict[str, ExecutionRequest] = {}
        self.execution_history: List[ExecutionResult] = []
        self.authorization_cache: Dict[str, ExecutionAuthorization] = {}

        # ENHANCED: Position tracking integration
        self.position_update_callback = config.get('position_update_callback')
        self.risk_manager_callback = config.get('risk_manager_callback')
        self.enable_position_tracking = config.get('enable_position_tracking', True)

        # Performance tracking
        self.execution_metrics = {
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'avg_execution_time': 0.0,
            'avg_market_impact': 0.0,
            'total_volume': 0.0
        }

        # Threading
        self.execution_lock = threading.Lock()

        # ISystemComponent state management
        self.is_initialized = False
        self.is_operational = False
        self.component_id: Optional[str] = None
        self.orchestrator: Optional[Any] = None  # HierarchicalSystemOrchestrator reference
        self.last_error: Optional[str] = None

        logger.info("✅ Unified Execution Engine initialized with position tracking")

    # ========================================
    # ORCHESTRATOR INTEGRATION
    # ========================================

    def register_with_orchestrator(self, orchestrator) -> str:
        """Register component with HierarchicalSystemOrchestrator"""
        from core_engine.system.hierarchical_orchestrator import ComponentLayer, AuthorityLevel

        self.orchestrator = orchestrator
        self.component_id = orchestrator.register_component(
            name="UnifiedExecutionEngine",
            component=self,
            layer=ComponentLayer.EXECUTION,
            authority_level=AuthorityLevel.OPERATIONAL,
            initialization_order=40  # Late initialization after all dependencies
        )

        logger.info(f"✅ UnifiedExecutionEngine registered with orchestrator: {self.component_id}")
        return self.component_id

    async def request_operation_authorization(self, operation: str, details: Dict[str, Any]) -> bool:
        """Request authorization from orchestrator for privileged operations"""
        if not self.orchestrator or not self.component_id:
            logger.warning("No orchestrator available for authorization request")
            return False

        return await self.orchestrator.request_system_authorization(
            operation, self.component_id, details
        )

    # ========================================
    # STANDARDIZED DATA CONSUMPTION METHODS
    # ========================================

    def process_plan(self, plan: Any) -> Dict[str, Any]:
        """Standardized method for processing execution plans"""
        return {
            'plan_processed': True,
            'plan_data': plan,
            'processing_timestamp': datetime.now(),
            'processing_component': 'UnifiedExecutionEngine'
        }

    def implement_plan(self, plan: Any) -> Dict[str, Any]:
        """Standardized method for implementing plans (alias)"""
        return self.process_plan(plan)

    def execute_plan(self, plan: Any) -> Dict[str, Any]:
        """Standardized method for executing plans (alias)"""
        return self.process_plan(plan)

    # ========================================
    # ISYSTEMCOMPONENT INTERFACE IMPLEMENTATION
    # ========================================

    async def initialize(self) -> bool:
        """Initialize the execution engine"""

        try:
            logger.info("🔄 Initializing UnifiedExecutionEngine...")

            # Initialize execution algorithms
            for algo_name, algorithm in self.algorithms.items():
                if hasattr(algorithm, 'initialize'):
                    success = await algorithm.initialize()
                    if not success:
                        logger.error(f"❌ Failed to initialize algorithm: {algo_name}")
                        return False

            # Initialize market impact model
            if hasattr(self.impact_model, 'initialize'):
                success = await self.impact_model.initialize()
                if not success:
                    logger.error("❌ Failed to initialize market impact model")
                    return False

            # Initialize validator
            if hasattr(self.validator, 'initialize'):
                success = await self.validator.initialize()
                if not success:
                    logger.error("❌ Failed to initialize execution validator")
                    return False

            self.is_initialized = True
            logger.info("✅ UnifiedExecutionEngine initialized successfully")
            return True

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"❌ UnifiedExecutionEngine initialization failed: {e}")
            return False

    async def start(self) -> bool:
        """Start the execution engine operations"""

        try:
            if not self.is_initialized:
                logger.error("❌ Cannot start - engine not initialized")
                return False

            logger.info("🚀 Starting UnifiedExecutionEngine operations...")

            # Start algorithm components
            for algo_name, algorithm in self.algorithms.items():
                if hasattr(algorithm, 'start'):
                    success = await algorithm.start()
                    if not success:
                        logger.warning(f"⚠️ Failed to start algorithm: {algo_name}")

            self.is_operational = True
            logger.info("✅ UnifiedExecutionEngine operational")
            return True

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"❌ UnifiedExecutionEngine start failed: {e}")
            return False

    async def stop(self) -> bool:
        """Stop the execution engine operations"""

        try:
            logger.info("🔄 Stopping UnifiedExecutionEngine...")

            # Cancel all active executions
            with self.execution_lock:
                active_count = len(self.active_executions)
                self.active_executions.clear()

            # Stop algorithm components
            for algo_name, algorithm in self.algorithms.items():
                if hasattr(algorithm, 'stop'):
                    await algorithm.stop()

            self.is_operational = False
            logger.info(f"✅ UnifiedExecutionEngine stopped (cancelled {active_count} active executions)")
            return True

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"❌ UnifiedExecutionEngine stop failed: {e}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check of the execution engine"""

        try:
            health_status = {
                'healthy': True,
                'initialized': self.is_initialized,
                'operational': self.is_operational,
                'component_type': 'UnifiedExecutionEngine',
                'active_executions': len(self.active_executions),
                'total_executions': len(self.execution_history),
                'last_error': self.last_error,
                'algorithms_status': {},
                'performance_metrics': self.execution_metrics.copy()
            }

            # Check algorithm health
            for algo_name, algorithm in self.algorithms.items():
                if hasattr(algorithm, 'health_check'):
                    algo_health = await algorithm.health_check()
                    health_status['algorithms_status'][algo_name.value] = algo_health
                    if not algo_health.get('healthy', True):
                        health_status['healthy'] = False
                else:
                    health_status['algorithms_status'][algo_name.value] = {'healthy': True}

            # Check execution performance
            if self.execution_metrics['total_executions'] > 0:
                success_rate = (self.execution_metrics['successful_executions'] /
                              self.execution_metrics['total_executions'])
                if success_rate < 0.95:  # Less than 95% success rate
                    health_status['healthy'] = False
                    health_status['warning'] = f"Low success rate: {success_rate:.1%}"

            return health_status

        except Exception as e:
            return {
                'healthy': False,
                'error': str(e),
                'component_type': 'UnifiedExecutionEngine'
            }

    def get_status(self) -> Dict[str, Any]:
        """Get current status of the execution engine"""

        return {
            'component_id': self.component_id,
            'component_type': 'UnifiedExecutionEngine',
            'initialized': self.is_initialized,
            'operational': self.is_operational,
            'active_executions': len(self.active_executions),
            'total_executions': len(self.execution_history),
            'execution_metrics': self.execution_metrics.copy(),
            'last_error': self.last_error,
            'algorithms_count': len(self.algorithms),
            'position_tracking_enabled': self.enable_position_tracking
        }

    async def execute_authorized_trade(self, request: ExecutionRequest) -> ExecutionResult:
        """
        Execute trade with RiskManager authorization

        This is the main entry point for all execution requests.
        NO execution can occur without valid RiskManager authorization.
        """

        try:
            with self.execution_lock:
                # Validate authorization and request
                is_valid, errors = self.validator.validate_request(request)

                if not is_valid:
                    logger.error(f"Execution request validation failed: {errors}")
                    return ExecutionResult(
                        request_id=request.request_id,
                        authorization_id=request.authorization.authorization_id,
                        status=ExecutionStatus.REJECTED,
                        execution_log=errors,
                        algorithm_used=request.algorithm
                    )

                # Check algorithm availability
                algorithm = self.algorithms.get(request.algorithm)
                if not algorithm:
                    logger.error(f"Algorithm {request.algorithm} not available")
                    return ExecutionResult(
                        request_id=request.request_id,
                        authorization_id=request.authorization.authorization_id,
                        status=ExecutionStatus.REJECTED,
                        execution_log=[f"Algorithm {request.algorithm} not available"],
                        algorithm_used=request.algorithm
                    )

                # Track active execution
                self.active_executions[request.request_id] = request

                logger.info(f"Starting authorized execution: {request.request_id}")

            # Execute the trade
            result = await algorithm.execute(request)

            # Post-execution processing
            with self.execution_lock:
                # Remove from active executions
                self.active_executions.pop(request.request_id, None)

                # Add to history
                self.execution_history.append(result)

                # Update metrics
                self._update_metrics(result)

                # ENHANCED: Position tracking integration
                await self._handle_position_updates(request, result)

                logger.info(f"Execution completed: {request.request_id} - Status: {result.status}")

            return result

        except Exception as e:
            logger.error(f"Execution engine error: {e}")

            # Clean up and return error result
            with self.execution_lock:
                self.active_executions.pop(request.request_id, None)

            return ExecutionResult(
                request_id=request.request_id,
                authorization_id=request.authorization.authorization_id,
                status=ExecutionStatus.FAILED,
                execution_log=[f"Execution engine error: {e}"],
                algorithm_used=getattr(request, 'algorithm', ExecutionAlgorithm.MARKET)
            )

    def get_execution_status(self, request_id: str) -> Optional[ExecutionStatus]:
        """Get current execution status"""

        with self.execution_lock:
            # Check active executions
            if request_id in self.active_executions:
                return ExecutionStatus.EXECUTING

            # Check execution history
            for result in reversed(self.execution_history):
                if result.request_id == request_id:
                    return result.status

            return None

    def get_execution_result(self, request_id: str) -> Optional[ExecutionResult]:
        """Get execution result"""

        with self.execution_lock:
            for result in reversed(self.execution_history):
                if result.request_id == request_id:
                    return result

            return None

    def cancel_execution(self, request_id: str, authorization_id: str) -> bool:
        """Cancel active execution (requires authorization)"""

        try:
            with self.execution_lock:
                if request_id not in self.active_executions:
                    logger.warning(f"Execution {request_id} not found for cancellation")
                    return False

                request = self.active_executions[request_id]

                # Verify authorization
                if request.authorization.authorization_id != authorization_id:
                    logger.error(f"Authorization mismatch for cancellation: {request_id}")
                    return False

                # Remove from active executions
                self.active_executions.pop(request_id)

                # Create cancelled result for history
                cancelled_result = ExecutionResult(
                    request_id=request_id,
                    authorization_id=authorization_id,
                    status=ExecutionStatus.CANCELLED,
                    algorithm_used=request.algorithm,
                    completed_at=datetime.now()
                )
                cancelled_result.execution_log.append(f"Cancelled at {datetime.now()}")
                self.execution_history.append(cancelled_result)

                logger.info(f"Execution {request_id} cancelled successfully")
                return True

        except Exception as e:
            logger.error(f"Error cancelling execution: {e}")
            return False

    def get_active_executions(self) -> List[str]:
        """Get list of active execution IDs"""

        with self.execution_lock:
            return list(self.active_executions.keys())

    def get_execution_metrics(self) -> Dict[str, Any]:
        """Get execution performance metrics"""

        with self.execution_lock:
            return self.execution_metrics.copy()

    async def estimate_execution_cost(self, request: ExecutionRequest) -> Dict[str, float]:
        """Estimate execution costs before execution"""

        try:
            algorithm = self.algorithms.get(request.algorithm)
            if not algorithm:
                return {'error': 'Algorithm not available'}

            estimated_impact = await algorithm.estimate_market_impact(request)
            estimated_time = algorithm.estimate_execution_time(request)

            quantity = request.authorization.quantity
            symbol = request.authorization.symbol

            # Get real reference price - no mock data
            if not hasattr(self, 'market_data_manager') or not self.market_data_manager:
                raise ConfigurationRequiredError("Market data manager required for reference price")

            try:
                market_data = await self.market_data_manager.get_current_price(symbol)
                if not market_data or 'price' not in market_data:
                    raise ConfigurationRequiredError(f"No price data available for {symbol}")

                price = market_data['price']
                if price <= 0:
                    raise ConfigurationRequiredError(f"Invalid reference price: {price}")
            except Exception as e:
                raise ConfigurationRequiredError(f"Failed to get reference price: {e}")

            costs = {
                'market_impact': estimated_impact * quantity * price,
                'timing_risk': 0.0001 * quantity * price,  # Simplified timing cost
                'commission': 0.005 * quantity,  # $0.005 per share
                'estimated_time': estimated_time,
                'total_cost': (estimated_impact + 0.0001) * quantity * price + 0.005 * quantity
            }

            return costs

        except Exception as e:
            logger.error(f"Error estimating execution cost: {e}")
            return {'error': str(e)}

    def _update_metrics(self, result: ExecutionResult):
        """Update execution performance metrics"""

        try:
            self.execution_metrics['total_executions'] += 1

            if result.status == ExecutionStatus.FILLED:
                self.execution_metrics['successful_executions'] += 1
            else:
                self.execution_metrics['failed_executions'] += 1

            if result.execution_time > 0:
                current_avg = self.execution_metrics['avg_execution_time']
                total_execs = self.execution_metrics['total_executions']
                self.execution_metrics['avg_execution_time'] = (
                    (current_avg * (total_execs - 1) + result.execution_time) / total_execs
                )

            if result.market_impact > 0:
                current_avg = self.execution_metrics['avg_market_impact']
                total_execs = self.execution_metrics['total_executions']
                self.execution_metrics['avg_market_impact'] = (
                    (current_avg * (total_execs - 1) + result.market_impact) / total_execs
                )

            self.execution_metrics['total_volume'] += result.filled_quantity

        except Exception as e:
            logger.error(f"Error updating metrics: {e}")

    def get_execution_report(self, start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Generate execution performance report"""

        try:
            with self.execution_lock:
                # Filter executions by date if provided
                filtered_executions = self.execution_history

                if start_date or end_date:
                    filtered_executions = []
                    for result in self.execution_history:
                        exec_date = result.completed_at or result.started_at
                        if exec_date:
                            if start_date and exec_date < start_date:
                                continue
                            if end_date and exec_date > end_date:
                                continue
                            filtered_executions.append(result)

                if not filtered_executions:
                    return {'message': 'No executions found in date range'}

                # Calculate report metrics
                total_executions = len(filtered_executions)
                successful = sum(1 for r in filtered_executions if r.status == ExecutionStatus.FILLED)
                failed = total_executions - successful

                execution_times = [r.execution_time for r in filtered_executions if r.execution_time > 0]
                market_impacts = [r.market_impact for r in filtered_executions if r.market_impact > 0]
                volumes = [r.filled_quantity for r in filtered_executions]

                report = {
                    'period': {
                        'start_date': start_date.isoformat() if start_date else 'N/A',
                        'end_date': end_date.isoformat() if end_date else 'N/A'
                    },
                    'execution_summary': {
                        'total_executions': total_executions,
                        'successful_executions': successful,
                        'failed_executions': failed,
                        'success_rate': successful / total_executions if total_executions > 0 else 0
                    },
                    'performance_metrics': {
                        'avg_execution_time': np.mean(execution_times) if execution_times else 0,
                        'avg_market_impact': np.mean(market_impacts) if market_impacts else 0,
                        'total_volume': sum(volumes),
                        'avg_volume_per_execution': np.mean(volumes) if volumes else 0
                    },
                    'algorithm_breakdown': self._get_algorithm_breakdown(filtered_executions)
                }

                return report

        except Exception as e:
            logger.error(f"Error generating execution report: {e}")
            return {'error': str(e)}

    def _get_algorithm_breakdown(self, executions: List[ExecutionResult]) -> Dict[str, Any]:
        """Get breakdown by algorithm"""

        try:
            algorithm_stats = defaultdict(lambda: {'count': 0, 'successful': 0, 'volume': 0})

            for result in executions:
                # Get algorithm type from execution result
                algorithm = result.algorithm_used.value

                algorithm_stats[algorithm]['count'] += 1
                if result.status == ExecutionStatus.FILLED:
                    algorithm_stats[algorithm]['successful'] += 1
                algorithm_stats[algorithm]['volume'] += result.filled_quantity

            return dict(algorithm_stats)

        except Exception as e:
            logger.error(f"Error calculating algorithm breakdown: {e}")
            return {}

    async def _handle_position_updates(self, request: ExecutionRequest, result: ExecutionResult):
        """
        Handle position updates after successful execution
        ENHANCED: Integrated position tracking from test implementation
        """
        try:
            # Only update positions for successful executions
            if result.status != ExecutionStatus.FILLED or not self.enable_position_tracking:
                return

            # Extract execution details
            symbol = request.authorization.symbol
            side = request.authorization.side.lower()
            filled_quantity = result.filled_quantity
            avg_price = result.avg_fill_price

            if filled_quantity <= 0:
                return

            # Update position via Risk Manager callback (preferred method)
            if self.risk_manager_callback:
                try:
                    await self._update_position_via_risk_manager(symbol, side, filled_quantity, avg_price)
                except Exception as e:
                    logger.error(f"❌ Risk Manager position update failed: {e}")
            # Fallback to direct position update callback
            elif self.position_update_callback:
                try:
                    await self._update_position_via_callback(symbol, side, filled_quantity, avg_price)
                except Exception as e:
                    logger.error(f"❌ Position callback update failed: {e}")
            else:
                logger.error("❌ No position update mechanism available")
                raise ConfigurationRequiredError("No position update mechanism available")

            logger.info(f"📊 Position updated: {symbol} {side.upper()} {filled_quantity} @ ${avg_price:.2f}")

        except Exception as e:
            logger.error(f"❌ Position update handling failed: {e}")

    async def _update_position_via_risk_manager(self, symbol: str, side: str, quantity: float, price: float):
        """Update position through Risk Manager"""
        if hasattr(self.risk_manager_callback, 'update_position'):
            # Direct method call - check if it's async
            if asyncio.iscoroutinefunction(self.risk_manager_callback.update_position):
                await self.risk_manager_callback.update_position(symbol, side, quantity, price)
            else:
                self.risk_manager_callback.update_position(symbol, side, quantity, price)
        elif callable(self.risk_manager_callback):
            # Callable function
            if asyncio.iscoroutinefunction(self.risk_manager_callback):
                await self.risk_manager_callback(symbol, side, quantity, price)
            else:
                self.risk_manager_callback(symbol, side, quantity, price)
        else:
            logger.warning("Risk Manager callback not callable")

    async def _update_position_via_callback(self, symbol: str, side: str, quantity: float, price: float):
        """Update position through direct callback"""
        if callable(self.position_update_callback):
            await self.position_update_callback(symbol, side, quantity, price)
        else:
            logger.warning("Position update callback not callable")

    def set_position_callbacks(self, risk_manager_callback: Optional[Callable] = None,
                              position_update_callback: Optional[Callable] = None):
        """
        Set position update callbacks
        ENHANCED: Allow dynamic callback registration
        """
        if risk_manager_callback:
            self.risk_manager_callback = risk_manager_callback
            logger.info("✅ Risk Manager callback registered with Execution Engine")

        if position_update_callback:
            self.position_update_callback = position_update_callback
            logger.info("✅ Position update callback registered with Execution Engine")

    def shutdown(self) -> None:
        """Shutdown execution engine"""

        try:
            logger.info("Shutting down Unified Execution Engine")

            # Cancel all active executions
            with self.execution_lock:
                active_count = len(self.active_executions)
                self.active_executions.clear()

                if active_count > 0:
                    logger.warning(f"Cancelled {active_count} active executions during shutdown")

            logger.info("Unified Execution Engine shutdown completed")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

    # ========================================
    # EXECUTION MODE ROUTING (Paper Trading Evolution)
    # ========================================
    #
    # Per plan Section 6.2 - Mode-Aware Execution Routing
    # Routes execution to paper or live broker based on mode

    def set_paper_broker(self, paper_broker: Any) -> None:
        """
        Set the paper broker adapter for paper trading mode.

        Args:
            paper_broker: PaperBrokerAdapter instance
        """
        self._paper_broker = paper_broker
        logger.info("✅ Paper broker set for execution routing")

    def set_live_broker(self, live_broker: Any) -> None:
        """
        Set the live broker adapter for live trading mode.

        Args:
            live_broker: Live broker adapter (IBKR, etc.)
        """
        self._live_broker = live_broker
        logger.info("✅ Live broker set for execution routing")

    def set_execution_mode(self, mode: str) -> None:
        """
        Set execution mode.

        Args:
            mode: 'PAPER' or 'LIVE'
        """
        if mode not in ('PAPER', 'LIVE'):
            raise ValueError(f"Invalid execution mode: {mode}")
        self._execution_mode = mode
        logger.info(f"📊 Execution mode set to: {mode}")

    def get_execution_mode(self) -> str:
        """Get current execution mode."""
        return getattr(self, '_execution_mode', 'PAPER')

    async def execute_with_mode_routing(
        self,
        request: ExecutionRequest,
    ) -> ExecutionResult:
        """
        Execute trade with mode-aware broker routing.

        Routes to paper or live broker based on current execution mode.

        Args:
            request: Execution request with authorization

        Returns:
            ExecutionResult from appropriate broker
        """
        mode = self.get_execution_mode()

        if mode == 'PAPER':
            return await self._execute_paper(request)
        elif mode == 'LIVE':
            return await self._execute_live(request)
        else:
            return ExecutionResult(
                request_id=request.request_id,
                authorization_id=request.authorization.authorization_id,
                status=ExecutionStatus.FAILED,
                execution_log=[f"Unknown execution mode: {mode}"],
                algorithm_used=request.algorithm,
            )

    async def _execute_paper(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute using paper broker."""
        paper_broker = getattr(self, '_paper_broker', None)

        if paper_broker is None:
            logger.error("Paper broker not set")
            return ExecutionResult(
                request_id=request.request_id,
                authorization_id=request.authorization.authorization_id,
                status=ExecutionStatus.FAILED,
                execution_log=["Paper broker not configured"],
                algorithm_used=request.algorithm,
            )

        # Convert request to broker order format
        auth = request.authorization
        side = auth.side.upper() if hasattr(auth.side, 'upper') else str(auth.side)

        from ..type_definitions.broker_types import OrderSide, OrderType, OrderStatus

        order_side = OrderSide.BUY if side in ('BUY', 'buy') else OrderSide.SELL

        # Determine order type
        if hasattr(auth, 'order_type'):
            order_type = auth.order_type
        elif hasattr(request, 'algorithm'):
            # Default to market for most algorithms
            order_type = OrderType.MARKET
        else:
            order_type = OrderType.MARKET

        # Submit to paper broker
        try:
            # If supported, pass one-shot context into paper broker (e.g., decision_price for simulator parity)
            if hasattr(paper_broker, "set_next_order_context"):
                try:
                    ctx = {}
                    if isinstance(getattr(request, "strategy_context", None), dict):
                        ctx.update(request.strategy_context)
                    if isinstance(getattr(request, "algorithm_params", None), dict):
                        ctx.update(request.algorithm_params)
                    # Normalize common field name
                    if "decision_price" in ctx:
                        ctx["decision_price"] = float(ctx["decision_price"])
                    paper_broker.set_next_order_context(ctx)
                except Exception:
                    pass
            if order_type == OrderType.LIMIT and hasattr(auth, 'limit_price'):
                order = paper_broker.submit_limit_order(
                    symbol=auth.symbol,
                    quantity=auth.quantity,
                    side=order_side,
                    limit_price=auth.limit_price,
                )
            else:
                order = paper_broker.submit_market_order(
                    symbol=auth.symbol,
                    quantity=auth.quantity,
                    side=order_side,
                )

            # Wait for fill (paper broker fills quickly)
            import asyncio
            # The paper broker returns an Order with `order_id` (not `.id`).
            order_id = getattr(order, "order_id", None) or getattr(order, "id", None)

            for _ in range(50):  # Wait up to 5 seconds
                await asyncio.sleep(0.1)
                updated_order = paper_broker.get_order(str(order_id))
                if updated_order:
                    st = getattr(updated_order, "status", None)
                    st_val = getattr(st, "value", None) or getattr(st, "name", None) or str(st)
                    if st in (OrderStatus.FILLED, OrderStatus.REJECTED, OrderStatus.CANCELLED) or str(st_val).lower() in ('filled', 'rejected', 'cancelled'):
                        break

            # Build result
            st = getattr(updated_order, "status", None) if updated_order else None
            st_val = getattr(st, "value", None) or getattr(st, "name", None) or str(st)
            is_filled = bool(updated_order) and (st == OrderStatus.FILLED or str(st_val).lower() == "filled")

            if is_filled:
                result = ExecutionResult(
                    request_id=request.request_id,
                    authorization_id=auth.authorization_id,
                    status=ExecutionStatus.FILLED,
                    algorithm_used=request.algorithm,
                )
                result.fill_quantity = updated_order.filled_quantity
                result.fill_price = float(getattr(updated_order, "average_price", 0.0) or 0.0)
                result.execution_log.append(f"Paper fill: {updated_order.filled_quantity} @ {result.fill_price}")
            else:
                result = ExecutionResult(
                    request_id=request.request_id,
                    authorization_id=auth.authorization_id,
                    status=ExecutionStatus.EXECUTING,
                    algorithm_used=request.algorithm,
                )
                result.execution_log.append(f"Paper order not filled yet: {st_val if updated_order else 'unknown'}")

            return result

        except Exception as e:
            logger.error(f"Paper execution error: {e}")
            return ExecutionResult(
                request_id=request.request_id,
                authorization_id=auth.authorization_id,
                status=ExecutionStatus.FAILED,
                execution_log=[f"Paper execution error: {e}"],
                algorithm_used=request.algorithm,
            )

    async def _execute_live(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute using live broker."""
        live_broker = getattr(self, '_live_broker', None)

        if live_broker is None:
            logger.error("Live broker not set")
            return ExecutionResult(
                request_id=request.request_id,
                authorization_id=request.authorization.authorization_id,
                status=ExecutionStatus.FAILED,
                execution_log=["Live broker not configured"],
                algorithm_used=request.algorithm,
            )

        # For live, use the standard authorized trade execution
        # which handles the full algorithm flow
        return await self.execute_authorized_trade(request)

