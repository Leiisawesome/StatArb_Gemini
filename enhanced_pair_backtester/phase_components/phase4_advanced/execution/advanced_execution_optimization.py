"""
Advanced Execution Optimization System
======================================

This module implements a comprehensive execution optimization system for multi-strategy
quantitative trading, providing advanced execution algorithms, market impact modeling,
optimal order routing, and intelligent order management.

Key Features:
- Multiple execution algorithms (TWAP, VWAP, Implementation Shortfall, POV)
- Market impact modeling and prediction
- Optimal order routing and venue selection
- Smart order management and slicing
- Real-time execution monitoring and adaptation
- Transaction cost analysis and optimization
- Liquidity analysis and timing optimization

Author: Pro Quant Desk Trader
Date: 2024
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
import json
import sqlite3
import threading
import time
import warnings
from abc import ABC, abstractmethod
import heapq
from collections import defaultdict, deque

# Statistical and optimization libraries
from scipy import stats
from scipy.optimize import minimize, differential_evolution
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error
import joblib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExecutionAlgorithm(Enum):
    """Types of execution algorithms"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    TWAP = "TWAP"
    VWAP = "VWAP"
    IMPLEMENTATION_SHORTFALL = "IMPLEMENTATION_SHORTFALL"
    PARTICIPATION_OF_VOLUME = "PARTICIPATION_OF_VOLUME"
    ARRIVAL_PRICE = "ARRIVAL_PRICE"
    CLOSE_PRICE = "CLOSE_PRICE"
    ICEBERG = "ICEBERG"
    HIDDEN_LIQUIDITY = "HIDDEN_LIQUIDITY"
    ADAPTIVE = "ADAPTIVE"

class OrderType(Enum):
    """Order types"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"
    TRAILING_STOP = "TRAILING_STOP"
    FILL_OR_KILL = "FILL_OR_KILL"
    IMMEDIATE_OR_CANCEL = "IMMEDIATE_OR_CANCEL"
    GOOD_TILL_CANCEL = "GOOD_TILL_CANCEL"

class OrderStatus(Enum):
    """Order status"""
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"

class VenueType(Enum):
    """Trading venue types"""
    PRIMARY_EXCHANGE = "PRIMARY_EXCHANGE"
    DARK_POOL = "DARK_POOL"
    ECN = "ECN"
    CROSSING_NETWORK = "CROSSING_NETWORK"
    RETAIL_MARKET_MAKER = "RETAIL_MARKET_MAKER"
    ALTERNATIVE_TRADING_SYSTEM = "ALTERNATIVE_TRADING_SYSTEM"

class ExecutionUrgency(Enum):
    """Execution urgency levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"
    IMMEDIATE = "IMMEDIATE"

@dataclass
class MarketData:
    """Real-time market data"""
    symbol: str
    timestamp: datetime
    
    # Price data
    bid_price: float
    ask_price: float
    last_price: float
    
    # Size data
    bid_size: int
    ask_size: int
    last_size: int
    
    # Volume data
    volume: int
    vwap: float
    
    # Market microstructure
    spread: float
    midpoint: float
    
    # Liquidity metrics
    market_impact_estimate: float
    available_liquidity: Dict[str, int] = field(default_factory=dict)  # By venue

@dataclass
class OrderInstruction:
    """Order instruction for execution"""
    instruction_id: str
    symbol: str
    side: str  # 'BUY' or 'SELL'
    quantity: int
    
    # Execution parameters
    algorithm: ExecutionAlgorithm
    urgency: ExecutionUrgency
    time_horizon: timedelta
    
    # Price constraints
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    
    # Execution constraints
    max_participation_rate: float = 0.20  # Max 20% of volume
    min_fill_size: int = 100
    max_slice_size: Optional[int] = None
    
    # Venue preferences
    preferred_venues: List[VenueType] = field(default_factory=list)
    avoid_venues: List[VenueType] = field(default_factory=list)
    
    # Risk parameters
    max_market_impact: float = 0.005  # 50 bps
    max_timing_risk: float = 0.002  # 20 bps
    
    # Metadata
    parent_strategy: Optional[str] = None
    creation_time: datetime = field(default_factory=datetime.now)

@dataclass
class Order:
    """Individual order"""
    order_id: str
    instruction_id: str
    symbol: str
    side: str
    quantity: int
    order_type: OrderType
    
    # Price
    price: Optional[float] = None
    
    # Venue
    venue: VenueType = VenueType.PRIMARY_EXCHANGE
    
    # Status
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    remaining_quantity: int = 0
    
    # Execution details
    average_fill_price: float = 0.0
    total_fees: float = 0.0
    
    # Timing
    creation_time: datetime = field(default_factory=datetime.now)
    submission_time: Optional[datetime] = None
    fill_time: Optional[datetime] = None
    
    # Market impact
    estimated_impact: float = 0.0
    actual_impact: float = 0.0

@dataclass
class Fill:
    """Order fill"""
    fill_id: str
    order_id: str
    symbol: str
    side: str
    quantity: int
    price: float
    
    # Venue and timing
    venue: VenueType
    timestamp: datetime
    
    # Costs
    commission: float = 0.0
    fees: float = 0.0
    
    # Market impact
    market_impact: float = 0.0
    
    # Liquidity
    liquidity_flag: str = "UNKNOWN"  # "ADDED", "REMOVED", "HIDDEN"

@dataclass
class ExecutionReport:
    """Execution performance report"""
    instruction_id: str
    symbol: str
    
    # Execution summary
    total_quantity: int
    filled_quantity: int
    fill_rate: float
    
    # Performance metrics
    arrival_price: float
    average_execution_price: float
    implementation_shortfall: float
    market_impact: float
    timing_cost: float
    
    # Transaction costs
    total_commission: float
    total_fees: float
    total_transaction_cost: float
    
    # Timing metrics
    start_time: datetime
    end_time: datetime
    execution_duration: timedelta
    
    # Algorithm performance
    algorithm_used: ExecutionAlgorithm
    algorithm_effectiveness: float
    
    # Venue analysis
    venue_breakdown: Dict[VenueType, Dict[str, Any]] = field(default_factory=dict)

class MarketImpactModel:
    """Market impact prediction model"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Model parameters
        self.temporary_impact_decay = config.get('temporary_impact_decay', 0.5)
        self.permanent_impact_factor = config.get('permanent_impact_factor', 0.3)
        
        # Models
        self.impact_models: Dict[str, Any] = {}
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize market impact models"""
        # Temporary impact model (square-root law)
        self.impact_models['temporary'] = {
            'type': 'square_root',
            'parameters': {
                'sigma': 0.02,  # Daily volatility
                'adv': 1000000,  # Average daily volume
                'gamma': 0.5    # Impact exponent
            }
        }
        
        # Permanent impact model
        self.impact_models['permanent'] = {
            'type': 'linear',
            'parameters': {
                'lambda': 0.1,  # Permanent impact coefficient
                'adv': 1000000  # Average daily volume
            }
        }
        
        # ML-based impact model
        self.impact_models['ml'] = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
    
    def predict_market_impact(self, symbol: str, side: str, quantity: int, 
                            urgency: ExecutionUrgency, 
                            market_data: MarketData) -> Dict[str, float]:
        """Predict market impact for an order"""
        try:
            # Calculate participation rate
            participation_rate = self._calculate_participation_rate(quantity, market_data, urgency)
            
            # Temporary impact (square-root law)
            temporary_impact = self._calculate_temporary_impact(
                symbol, quantity, participation_rate, market_data
            )
            
            # Permanent impact
            permanent_impact = self._calculate_permanent_impact(
                symbol, quantity, market_data
            )
            
            # Total impact
            total_impact = temporary_impact + permanent_impact
            
            # Timing risk
            timing_risk = self._calculate_timing_risk(symbol, urgency, market_data)
            
            return {
                'temporary_impact': temporary_impact,
                'permanent_impact': permanent_impact,
                'total_impact': total_impact,
                'timing_risk': timing_risk,
                'participation_rate': participation_rate
            }
            
        except Exception as e:
            logger.error(f"Error predicting market impact: {e}")
            return {
                'temporary_impact': 0.001,
                'permanent_impact': 0.0005,
                'total_impact': 0.0015,
                'timing_risk': 0.001,
                'participation_rate': 0.1
            }
    
    def _calculate_participation_rate(self, quantity: int, market_data: MarketData, 
                                    urgency: ExecutionUrgency) -> float:
        """Calculate optimal participation rate"""
        # Base participation rate based on urgency
        urgency_rates = {
            ExecutionUrgency.LOW: 0.05,
            ExecutionUrgency.MEDIUM: 0.10,
            ExecutionUrgency.HIGH: 0.20,
            ExecutionUrgency.URGENT: 0.35,
            ExecutionUrgency.IMMEDIATE: 0.50
        }
        
        base_rate = urgency_rates.get(urgency, 0.10)
        
        # Adjust for order size relative to average volume
        if market_data.volume > 0:
            size_factor = quantity / market_data.volume
            # Reduce participation rate for large orders
            adjusted_rate = base_rate * (1 - min(0.5, size_factor))
        else:
            adjusted_rate = base_rate
        
        return max(0.01, min(0.50, adjusted_rate))
    
    def _calculate_temporary_impact(self, symbol: str, quantity: int, 
                                  participation_rate: float, 
                                  market_data: MarketData) -> float:
        """Calculate temporary market impact"""
        try:
            # Square-root law: impact = sigma * sqrt(quantity / ADV) * gamma
            params = self.impact_models['temporary']['parameters']
            
            # Use current volume as proxy for ADV
            adv = max(market_data.volume * 252, 100000)  # Annualize and set minimum
            
            # Calculate impact
            impact = params['sigma'] * np.sqrt(quantity / adv) * params['gamma']
            
            # Adjust for participation rate (higher rate = higher impact)
            impact *= (1 + participation_rate)
            
            # Adjust for spread (wider spread = higher impact)
            spread_adjustment = market_data.spread / market_data.midpoint if market_data.midpoint > 0 else 0.001
            impact *= (1 + spread_adjustment * 10)
            
            return impact
            
        except Exception as e:
            logger.error(f"Error calculating temporary impact: {e}")
            return 0.001
    
    def _calculate_permanent_impact(self, symbol: str, quantity: int, 
                                  market_data: MarketData) -> float:
        """Calculate permanent market impact"""
        try:
            # Linear model: impact = lambda * (quantity / ADV)
            params = self.impact_models['permanent']['parameters']
            
            # Use current volume as proxy for ADV
            adv = max(market_data.volume * 252, 100000)
            
            # Calculate impact
            impact = params['lambda'] * (quantity / adv)
            
            return impact * self.permanent_impact_factor
            
        except Exception as e:
            logger.error(f"Error calculating permanent impact: {e}")
            return 0.0005
    
    def _calculate_timing_risk(self, symbol: str, urgency: ExecutionUrgency, 
                             market_data: MarketData) -> float:
        """Calculate timing risk"""
        try:
            # Base timing risk based on urgency
            urgency_risks = {
                ExecutionUrgency.LOW: 0.003,
                ExecutionUrgency.MEDIUM: 0.002,
                ExecutionUrgency.HIGH: 0.001,
                ExecutionUrgency.URGENT: 0.0005,
                ExecutionUrgency.IMMEDIATE: 0.0001
            }
            
            base_risk = urgency_risks.get(urgency, 0.002)
            
            # Adjust for volatility
            if hasattr(market_data, 'volatility'):
                vol_adjustment = getattr(market_data, 'volatility', 0.02) / 0.02
                base_risk *= vol_adjustment
            
            return base_risk
            
        except Exception as e:
            logger.error(f"Error calculating timing risk: {e}")
            return 0.002

class BaseExecutionAlgorithm(ABC):
    """Base class for execution algorithms"""
    
    def __init__(self, algorithm_type: ExecutionAlgorithm, config: Dict[str, Any]):
        self.algorithm_type = algorithm_type
        self.config = config
        
        # Market impact model
        self.impact_model = MarketImpactModel(config.get('impact_model', {}))
        
        # Algorithm parameters
        self.max_slice_size = config.get('max_slice_size', 1000)
        self.min_slice_size = config.get('min_slice_size', 100)
        self.slice_interval = config.get('slice_interval', 30)  # seconds
        
        # Performance tracking
        self.execution_history: List[ExecutionReport] = []
    
    @abstractmethod
    def generate_child_orders(self, instruction: OrderInstruction, 
                            market_data: MarketData) -> List[Order]:
        """Generate child orders for execution"""
        pass
    
    @abstractmethod
    def update_execution(self, instruction: OrderInstruction, 
                        market_data: MarketData,
                        active_orders: List[Order],
                        fills: List[Fill]) -> List[Order]:
        """Update execution based on market conditions and fills"""
        pass
    
    def calculate_slice_size(self, remaining_quantity: int, time_remaining: timedelta,
                           participation_rate: float, market_data: MarketData) -> int:
        """Calculate optimal slice size"""
        try:
            # Time-based slicing
            if time_remaining.total_seconds() > 0:
                time_slices = max(1, time_remaining.total_seconds() / self.slice_interval)
                time_based_size = remaining_quantity / time_slices
            else:
                time_based_size = remaining_quantity
            
            # Volume-based slicing
            if market_data.volume > 0:
                volume_based_size = market_data.volume * participation_rate
            else:
                volume_based_size = self.max_slice_size
            
            # Take minimum to be conservative
            slice_size = min(time_based_size, volume_based_size)
            
            # Apply size constraints
            slice_size = max(self.min_slice_size, min(self.max_slice_size, slice_size))
            slice_size = min(slice_size, remaining_quantity)
            
            return int(slice_size)
            
        except Exception as e:
            logger.error(f"Error calculating slice size: {e}")
            return min(self.min_slice_size, remaining_quantity)

class TWAPAlgorithm(BaseExecutionAlgorithm):
    """Time-Weighted Average Price algorithm"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(ExecutionAlgorithm.TWAP, config)
        
        # TWAP specific parameters
        self.execution_intervals = config.get('execution_intervals', 10)
        self.price_improvement_threshold = config.get('price_improvement_threshold', 0.001)
    
    def generate_child_orders(self, instruction: OrderInstruction, 
                            market_data: MarketData) -> List[Order]:
        """Generate TWAP child orders"""
        try:
            child_orders = []
            
            # Calculate time slices
            total_time = instruction.time_horizon.total_seconds()
            slice_interval = total_time / self.execution_intervals
            slice_size = instruction.quantity / self.execution_intervals
            
            # Generate orders for each time slice
            for i in range(self.execution_intervals):
                # Calculate execution time
                execution_time = datetime.now() + timedelta(seconds=i * slice_interval)
                
                # Determine order type and price
                if instruction.urgency in [ExecutionUrgency.URGENT, ExecutionUrgency.IMMEDIATE]:
                    order_type = OrderType.MARKET
                    price = None
                else:
                    order_type = OrderType.LIMIT
                    # Use midpoint as limit price
                    price = market_data.midpoint
                
                # Create child order
                order = Order(
                    order_id=f"{instruction.instruction_id}_twap_{i}",
                    instruction_id=instruction.instruction_id,
                    symbol=instruction.symbol,
                    side=instruction.side,
                    quantity=int(slice_size),
                    order_type=order_type,
                    price=price,
                    venue=VenueType.PRIMARY_EXCHANGE
                )
                
                child_orders.append(order)
            
            return child_orders
            
        except Exception as e:
            logger.error(f"Error generating TWAP orders: {e}")
            return []
    
    def update_execution(self, instruction: OrderInstruction, 
                        market_data: MarketData,
                        active_orders: List[Order],
                        fills: List[Fill]) -> List[Order]:
        """Update TWAP execution"""
        try:
            updated_orders = []
            
            for order in active_orders:
                if order.status == OrderStatus.SUBMITTED:
                    # Check if we should update limit price
                    if order.order_type == OrderType.LIMIT and order.price:
                        # Update price if market has moved significantly
                        price_diff = abs(market_data.midpoint - order.price) / order.price
                        
                        if price_diff > self.price_improvement_threshold:
                            # Cancel and replace with new price
                            order.status = OrderStatus.CANCELLED
                            
                            # Create new order with updated price
                            new_order = Order(
                                order_id=f"{order.order_id}_updated",
                                instruction_id=order.instruction_id,
                                symbol=order.symbol,
                                side=order.side,
                                quantity=order.remaining_quantity,
                                order_type=order.order_type,
                                price=market_data.midpoint,
                                venue=order.venue
                            )
                            
                            updated_orders.append(new_order)
                
                updated_orders.append(order)
            
            return updated_orders
            
        except Exception as e:
            logger.error(f"Error updating TWAP execution: {e}")
            return active_orders

class VWAPAlgorithm(BaseExecutionAlgorithm):
    """Volume-Weighted Average Price algorithm"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(ExecutionAlgorithm.VWAP, config)
        
        # VWAP specific parameters
        self.volume_profile = config.get('volume_profile', 'HISTORICAL')  # or 'INTRADAY'
        self.participation_rate = config.get('participation_rate', 0.10)
        
        # Historical volume profile (simplified)
        self.historical_profile = {
            9: 0.05, 10: 0.08, 11: 0.12, 12: 0.10, 13: 0.08,
            14: 0.12, 15: 0.15, 16: 0.30  # Higher volume at close
        }
    
    def generate_child_orders(self, instruction: OrderInstruction, 
                            market_data: MarketData) -> List[Order]:
        """Generate VWAP child orders"""
        try:
            child_orders = []
            
            # Get volume profile
            volume_profile = self._get_volume_profile(instruction.time_horizon)
            
            # Calculate order sizes based on expected volume
            total_expected_volume = sum(volume_profile.values())
            
            for hour, volume_fraction in volume_profile.items():
                # Calculate slice size based on volume fraction and participation rate
                expected_hour_volume = market_data.volume * volume_fraction
                slice_size = min(
                    instruction.quantity * volume_fraction,
                    expected_hour_volume * self.participation_rate
                )
                
                if slice_size >= self.min_slice_size:
                    # Determine order type
                    order_type = OrderType.LIMIT
                    price = market_data.midpoint
                    
                    # Create child order
                    order = Order(
                        order_id=f"{instruction.instruction_id}_vwap_{hour}",
                        instruction_id=instruction.instruction_id,
                        symbol=instruction.symbol,
                        side=instruction.side,
                        quantity=int(slice_size),
                        order_type=order_type,
                        price=price,
                        venue=VenueType.PRIMARY_EXCHANGE
                    )
                    
                    child_orders.append(order)
            
            return child_orders
            
        except Exception as e:
            logger.error(f"Error generating VWAP orders: {e}")
            return []
    
    def _get_volume_profile(self, time_horizon: timedelta) -> Dict[int, float]:
        """Get volume profile for execution period"""
        try:
            current_hour = datetime.now().hour
            end_hour = (datetime.now() + time_horizon).hour
            
            if end_hour <= current_hour:
                end_hour += 24  # Next day
            
            # Extract relevant hours from historical profile
            relevant_profile = {}
            total_fraction = 0.0
            
            for hour in range(current_hour, min(end_hour + 1, 17)):  # Market hours
                if hour in self.historical_profile:
                    relevant_profile[hour] = self.historical_profile[hour]
                    total_fraction += self.historical_profile[hour]
            
            # Normalize
            if total_fraction > 0:
                for hour in relevant_profile:
                    relevant_profile[hour] /= total_fraction
            
            return relevant_profile
            
        except Exception as e:
            logger.error(f"Error getting volume profile: {e}")
            return {datetime.now().hour: 1.0}
    
    def update_execution(self, instruction: OrderInstruction, 
                        market_data: MarketData,
                        active_orders: List[Order],
                        fills: List[Fill]) -> List[Order]:
        """Update VWAP execution"""
        try:
            updated_orders = []
            
            # Calculate current VWAP performance
            current_vwap = self._calculate_current_vwap(fills)
            market_vwap = market_data.vwap
            
            for order in active_orders:
                if order.status == OrderStatus.SUBMITTED:
                    # Adjust participation rate based on VWAP performance
                    if current_vwap > market_vwap * 1.001:  # Behind VWAP
                        # Increase aggression
                        if order.order_type == OrderType.LIMIT:
                            # Improve price slightly
                            if instruction.side == 'BUY':
                                new_price = min(order.price * 1.0005, market_data.ask_price)
                            else:
                                new_price = max(order.price * 0.9995, market_data.bid_price)
                            
                            order.price = new_price
                    
                updated_orders.append(order)
            
            return updated_orders
            
        except Exception as e:
            logger.error(f"Error updating VWAP execution: {e}")
            return active_orders
    
    def _calculate_current_vwap(self, fills: List[Fill]) -> float:
        """Calculate current VWAP from fills"""
        try:
            if not fills:
                return 0.0
            
            total_value = sum(fill.quantity * fill.price for fill in fills)
            total_quantity = sum(fill.quantity for fill in fills)
            
            return total_value / total_quantity if total_quantity > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating current VWAP: {e}")
            return 0.0

class ImplementationShortfallAlgorithm(BaseExecutionAlgorithm):
    """Implementation Shortfall algorithm"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(ExecutionAlgorithm.IMPLEMENTATION_SHORTFALL, config)
        
        # IS specific parameters
        self.risk_aversion = config.get('risk_aversion', 0.5)
        self.volatility_estimate = config.get('volatility_estimate', 0.02)
        self.adaptation_speed = config.get('adaptation_speed', 0.1)
    
    def generate_child_orders(self, instruction: OrderInstruction, 
                            market_data: MarketData) -> List[Order]:
        """Generate Implementation Shortfall child orders"""
        try:
            child_orders = []
            
            # Calculate optimal execution rate
            optimal_rate = self._calculate_optimal_execution_rate(instruction, market_data)
            
            # Calculate number of slices
            total_time = instruction.time_horizon.total_seconds()
            slice_interval = 60  # 1 minute slices
            num_slices = int(total_time / slice_interval)
            
            # Generate orders with optimal trajectory
            remaining_quantity = instruction.quantity
            
            for i in range(num_slices):
                if remaining_quantity <= 0:
                    break
                
                # Calculate slice size using optimal trajectory
                time_fraction = (i + 1) / num_slices
                target_completion = self._optimal_trajectory(time_fraction, optimal_rate)
                
                target_quantity = instruction.quantity * target_completion
                slice_size = min(
                    target_quantity - (instruction.quantity - remaining_quantity),
                    remaining_quantity
                )
                
                if slice_size >= self.min_slice_size:
                    # Determine order aggressiveness
                    if instruction.urgency == ExecutionUrgency.IMMEDIATE:
                        order_type = OrderType.MARKET
                        price = None
                    else:
                        order_type = OrderType.LIMIT
                        # Price based on market impact trade-off
                        price = self._calculate_optimal_price(
                            instruction, slice_size, market_data
                        )
                    
                    order = Order(
                        order_id=f"{instruction.instruction_id}_is_{i}",
                        instruction_id=instruction.instruction_id,
                        symbol=instruction.symbol,
                        side=instruction.side,
                        quantity=int(slice_size),
                        order_type=order_type,
                        price=price,
                        venue=VenueType.PRIMARY_EXCHANGE
                    )
                    
                    child_orders.append(order)
                    remaining_quantity -= slice_size
            
            return child_orders
            
        except Exception as e:
            logger.error(f"Error generating IS orders: {e}")
            return []
    
    def _calculate_optimal_execution_rate(self, instruction: OrderInstruction, 
                                        market_data: MarketData) -> float:
        """Calculate optimal execution rate for IS algorithm"""
        try:
            # Predict market impact
            impact_prediction = self.impact_model.predict_market_impact(
                instruction.symbol, instruction.side, instruction.quantity,
                instruction.urgency, market_data
            )
            
            # Calculate optimal rate balancing market impact and timing risk
            temporary_impact = impact_prediction['temporary_impact']
            timing_risk = impact_prediction['timing_risk']
            
            # Optimal rate from Almgren-Chriss model
            T = instruction.time_horizon.total_seconds() / 3600  # Hours
            sigma = self.volatility_estimate
            
            # Simplified optimal rate calculation
            if T > 0 and sigma > 0:
                optimal_rate = np.sqrt(timing_risk / (temporary_impact * T))
                optimal_rate = min(1.0, max(0.1, optimal_rate))  # Bounds
            else:
                optimal_rate = 0.5  # Default
            
            return optimal_rate
            
        except Exception as e:
            logger.error(f"Error calculating optimal execution rate: {e}")
            return 0.5
    
    def _optimal_trajectory(self, time_fraction: float, execution_rate: float) -> float:
        """Calculate optimal execution trajectory"""
        try:
            # Exponential trajectory: x(t) = 1 - exp(-rate * t)
            completion = 1 - np.exp(-execution_rate * time_fraction)
            return min(1.0, completion)
            
        except Exception as e:
            logger.error(f"Error calculating optimal trajectory: {e}")
            return time_fraction  # Linear fallback
    
    def _calculate_optimal_price(self, instruction: OrderInstruction, 
                               slice_size: int, market_data: MarketData) -> float:
        """Calculate optimal limit price"""
        try:
            # Predict market impact for this slice
            impact_prediction = self.impact_model.predict_market_impact(
                instruction.symbol, instruction.side, slice_size,
                instruction.urgency, market_data
            )
            
            # Adjust price based on market impact
            if instruction.side == 'BUY':
                # For buy orders, add some impact to midpoint
                optimal_price = market_data.midpoint + (market_data.spread / 4)
                optimal_price += impact_prediction['total_impact'] * market_data.midpoint
            else:
                # For sell orders, subtract some impact from midpoint
                optimal_price = market_data.midpoint - (market_data.spread / 4)
                optimal_price -= impact_prediction['total_impact'] * market_data.midpoint
            
            return optimal_price
            
        except Exception as e:
            logger.error(f"Error calculating optimal price: {e}")
            return market_data.midpoint
    
    def update_execution(self, instruction: OrderInstruction, 
                        market_data: MarketData,
                        active_orders: List[Order],
                        fills: List[Fill]) -> List[Order]:
        """Update IS execution based on performance"""
        try:
            updated_orders = []
            
            # Calculate current implementation shortfall
            current_is = self._calculate_implementation_shortfall(
                instruction, fills, market_data
            )
            
            # Adapt execution based on performance
            for order in active_orders:
                if order.status == OrderStatus.SUBMITTED:
                    # If IS is too high, become more aggressive
                    if current_is > 0.005:  # 50 bps threshold
                        if order.order_type == OrderType.LIMIT:
                            # Move price towards market
                            if instruction.side == 'BUY':
                                new_price = min(order.price * 1.001, market_data.ask_price)
                            else:
                                new_price = max(order.price * 0.999, market_data.bid_price)
                            
                            order.price = new_price
                
                updated_orders.append(order)
            
            return updated_orders
            
        except Exception as e:
            logger.error(f"Error updating IS execution: {e}")
            return active_orders
    
    def _calculate_implementation_shortfall(self, instruction: OrderInstruction,
                                          fills: List[Fill],
                                          market_data: MarketData) -> float:
        """Calculate current implementation shortfall"""
        try:
            if not fills:
                return 0.0
            
            # Calculate average execution price
            total_value = sum(fill.quantity * fill.price for fill in fills)
            total_quantity = sum(fill.quantity for fill in fills)
            avg_price = total_value / total_quantity if total_quantity > 0 else 0.0
            
            # Use arrival price (first market data point)
            arrival_price = market_data.midpoint  # Simplified
            
            # Calculate implementation shortfall
            if instruction.side == 'BUY':
                is_value = (avg_price - arrival_price) / arrival_price
            else:
                is_value = (arrival_price - avg_price) / arrival_price
            
            return is_value
            
        except Exception as e:
            logger.error(f"Error calculating implementation shortfall: {e}")
            return 0.0

class VenueRouter:
    """Intelligent venue routing system"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Venue characteristics
        self.venue_characteristics = self._initialize_venue_characteristics()
        
        # Routing models
        self.routing_models: Dict[str, Any] = {}
        self._initialize_routing_models()
        
        # Performance tracking
        self.venue_performance: Dict[VenueType, Dict[str, float]] = defaultdict(dict)
    
    def _initialize_venue_characteristics(self) -> Dict[VenueType, Dict[str, Any]]:
        """Initialize venue characteristics"""
        return {
            VenueType.PRIMARY_EXCHANGE: {
                'liquidity_score': 0.9,
                'speed_score': 0.8,
                'cost_score': 0.7,
                'market_impact': 0.8,
                'fill_rate': 0.85,
                'typical_spread': 1.0  # Relative to NBBO
            },
            VenueType.DARK_POOL: {
                'liquidity_score': 0.7,
                'speed_score': 0.6,
                'cost_score': 0.9,
                'market_impact': 0.3,
                'fill_rate': 0.6,
                'typical_spread': 0.5
            },
            VenueType.ECN: {
                'liquidity_score': 0.8,
                'speed_score': 0.9,
                'cost_score': 0.8,
                'market_impact': 0.6,
                'fill_rate': 0.8,
                'typical_spread': 0.8
            },
            VenueType.CROSSING_NETWORK: {
                'liquidity_score': 0.6,
                'speed_score': 0.4,
                'cost_score': 0.95,
                'market_impact': 0.1,
                'fill_rate': 0.4,
                'typical_spread': 0.0
            }
        }
    
    def _initialize_routing_models(self):
        """Initialize venue routing models"""
        # Simple scoring model
        self.routing_models['scoring'] = {
            'weights': {
                'liquidity_score': 0.3,
                'speed_score': 0.2,
                'cost_score': 0.3,
                'market_impact': 0.2
            }
        }
        
        # ML-based routing model
        self.routing_models['ml'] = RandomForestRegressor(
            n_estimators=50,
            max_depth=8,
            random_state=42
        )
    
    def select_optimal_venue(self, order: Order, market_data: MarketData,
                           instruction: OrderInstruction) -> VenueType:
        """Select optimal venue for order execution"""
        try:
            # Score each venue
            venue_scores = {}
            
            for venue_type, characteristics in self.venue_characteristics.items():
                # Check venue preferences
                if venue_type in instruction.avoid_venues:
                    continue
                
                # Calculate venue score
                score = self._calculate_venue_score(
                    venue_type, characteristics, order, market_data, instruction
                )
                
                venue_scores[venue_type] = score
            
            # Select venue with highest score
            if venue_scores:
                optimal_venue = max(venue_scores.items(), key=lambda x: x[1])[0]
            else:
                optimal_venue = VenueType.PRIMARY_EXCHANGE  # Default
            
            return optimal_venue
            
        except Exception as e:
            logger.error(f"Error selecting optimal venue: {e}")
            return VenueType.PRIMARY_EXCHANGE
    
    def _calculate_venue_score(self, venue_type: VenueType, 
                             characteristics: Dict[str, Any],
                             order: Order, market_data: MarketData,
                             instruction: OrderInstruction) -> float:
        """Calculate venue score based on order characteristics"""
        try:
            scoring_weights = self.routing_models['scoring']['weights']
            
            # Base score from characteristics
            base_score = 0.0
            for metric, weight in scoring_weights.items():
                if metric in characteristics:
                    base_score += characteristics[metric] * weight
            
            # Adjust for order size
            order_size_factor = order.quantity / max(market_data.volume, 1000)
            if order_size_factor > 0.1:  # Large order
                # Prefer dark pools and crossing networks
                if venue_type in [VenueType.DARK_POOL, VenueType.CROSSING_NETWORK]:
                    base_score *= 1.2
                else:
                    base_score *= 0.9
            
            # Adjust for urgency
            if instruction.urgency in [ExecutionUrgency.URGENT, ExecutionUrgency.IMMEDIATE]:
                # Prefer fast venues
                base_score *= characteristics.get('speed_score', 0.5)
            
            # Adjust for historical performance
            historical_performance = self.venue_performance.get(venue_type, {})
            if 'fill_rate' in historical_performance:
                performance_factor = historical_performance['fill_rate'] / 0.8  # Normalize
                base_score *= performance_factor
            
            return base_score
            
        except Exception as e:
            logger.error(f"Error calculating venue score: {e}")
            return 0.5
    
    def update_venue_performance(self, venue: VenueType, fill: Fill):
        """Update venue performance metrics"""
        try:
            if venue not in self.venue_performance:
                self.venue_performance[venue] = {
                    'total_fills': 0,
                    'total_quantity': 0,
                    'total_value': 0,
                    'fill_rate': 0.8,
                    'avg_market_impact': 0.0
                }
            
            perf = self.venue_performance[venue]
            
            # Update metrics
            perf['total_fills'] += 1
            perf['total_quantity'] += fill.quantity
            perf['total_value'] += fill.quantity * fill.price
            
            # Update fill rate (simplified)
            alpha = 0.1  # Learning rate
            perf['fill_rate'] = alpha * 1.0 + (1 - alpha) * perf['fill_rate']
            
            # Update market impact
            perf['avg_market_impact'] = alpha * fill.market_impact + (1 - alpha) * perf['avg_market_impact']
            
        except Exception as e:
            logger.error(f"Error updating venue performance: {e}")

class ExecutionEngine:
    """
    Comprehensive execution engine that manages order execution using
    multiple algorithms and intelligent venue routing
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the execution engine
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        
        # Initialize algorithms
        self.algorithms: Dict[ExecutionAlgorithm, BaseExecutionAlgorithm] = {}
        self._initialize_algorithms()
        
        # Venue router
        self.venue_router = VenueRouter(config.get('venue_config', {}))
        
        # Order management
        self.active_instructions: Dict[str, OrderInstruction] = {}
        self.active_orders: Dict[str, Order] = {}
        self.order_fills: Dict[str, List[Fill]] = defaultdict(list)
        
        # Execution reports
        self.execution_reports: List[ExecutionReport] = []
        
        # Market data
        self.market_data: Dict[str, MarketData] = {}
        
        # Threading
        self.execution_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Database
        self.db_path = config.get('db_path', 'execution_engine.db')
        self._init_database()
        
        logger.info("Execution engine initialized")
    
    def _initialize_algorithms(self):
        """Initialize execution algorithms"""
        algorithm_configs = self.config.get('algorithms', {})
        
        # TWAP
        if 'twap' in algorithm_configs:
            self.algorithms[ExecutionAlgorithm.TWAP] = TWAPAlgorithm(
                algorithm_configs['twap']
            )
        
        # VWAP
        if 'vwap' in algorithm_configs:
            self.algorithms[ExecutionAlgorithm.VWAP] = VWAPAlgorithm(
                algorithm_configs['vwap']
            )
        
        # Implementation Shortfall
        if 'implementation_shortfall' in algorithm_configs:
            self.algorithms[ExecutionAlgorithm.IMPLEMENTATION_SHORTFALL] = ImplementationShortfallAlgorithm(
                algorithm_configs['implementation_shortfall']
            )
        
        logger.info(f"Initialized {len(self.algorithms)} execution algorithms")
    
    def _init_database(self):
        """Initialize execution database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS order_instructions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    instruction_id TEXT UNIQUE NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    algorithm TEXT NOT NULL,
                    urgency TEXT NOT NULL,
                    creation_time DATETIME NOT NULL,
                    time_horizon REAL NOT NULL,
                    status TEXT NOT NULL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT UNIQUE NOT NULL,
                    instruction_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    order_type TEXT NOT NULL,
                    price REAL,
                    venue TEXT NOT NULL,
                    status TEXT NOT NULL,
                    creation_time DATETIME NOT NULL,
                    submission_time DATETIME,
                    fill_time DATETIME
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fills (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fill_id TEXT UNIQUE NOT NULL,
                    order_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    price REAL NOT NULL,
                    venue TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    commission REAL DEFAULT 0,
                    fees REAL DEFAULT 0,
                    market_impact REAL DEFAULT 0
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS execution_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    instruction_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    total_quantity INTEGER NOT NULL,
                    filled_quantity INTEGER NOT NULL,
                    fill_rate REAL NOT NULL,
                    arrival_price REAL NOT NULL,
                    average_execution_price REAL NOT NULL,
                    implementation_shortfall REAL NOT NULL,
                    market_impact REAL NOT NULL,
                    total_transaction_cost REAL NOT NULL,
                    start_time DATETIME NOT NULL,
                    end_time DATETIME NOT NULL,
                    algorithm_used TEXT NOT NULL
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Execution database initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize execution database: {e}")
            raise
    
    def submit_instruction(self, instruction: OrderInstruction) -> bool:
        """Submit order instruction for execution"""
        try:
            # Validate instruction
            if not self._validate_instruction(instruction):
                return False
            
            # Check if algorithm is available
            if instruction.algorithm not in self.algorithms:
                logger.error(f"Algorithm {instruction.algorithm.value} not available")
                return False
            
            # Store instruction
            self.active_instructions[instruction.instruction_id] = instruction
            self._store_instruction(instruction)
            
            # Generate initial child orders
            algorithm = self.algorithms[instruction.algorithm]
            market_data = self.market_data.get(instruction.symbol)
            
            if market_data:
                child_orders = algorithm.generate_child_orders(instruction, market_data)
                
                # Route and submit orders
                for order in child_orders:
                    # Select optimal venue
                    optimal_venue = self.venue_router.select_optimal_venue(
                        order, market_data, instruction
                    )
                    order.venue = optimal_venue
                    
                    # Submit order
                    self._submit_order(order)
            
            logger.info(f"Instruction submitted: {instruction.instruction_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error submitting instruction: {e}")
            return False
    
    def _validate_instruction(self, instruction: OrderInstruction) -> bool:
        """Validate order instruction"""
        try:
            # Basic validation
            if instruction.quantity <= 0:
                logger.error("Invalid quantity")
                return False
            
            if instruction.side not in ['BUY', 'SELL']:
                logger.error("Invalid side")
                return False
            
            if instruction.time_horizon.total_seconds() <= 0:
                logger.error("Invalid time horizon")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating instruction: {e}")
            return False
    
    def _submit_order(self, order: Order):
        """Submit individual order"""
        try:
            # Update order status
            order.status = OrderStatus.SUBMITTED
            order.submission_time = datetime.now()
            order.remaining_quantity = order.quantity
            
            # Store order
            self.active_orders[order.order_id] = order
            self._store_order(order)
            
            # Simulate order submission (in practice, this would connect to broker/exchange)
            logger.info(f"Order submitted: {order.order_id} - {order.quantity} {order.symbol} @ {order.price}")
            
        except Exception as e:
            logger.error(f"Error submitting order: {e}")
    
    def update_market_data(self, symbol: str, market_data: MarketData):
        """Update market data for a symbol"""
        self.market_data[symbol] = market_data
    
    def process_fill(self, fill: Fill):
        """Process order fill"""
        try:
            # Find corresponding order
            order = self.active_orders.get(fill.order_id)
            if not order:
                logger.error(f"Order not found for fill: {fill.order_id}")
                return
            
            # Update order
            order.filled_quantity += fill.quantity
            order.remaining_quantity = order.quantity - order.filled_quantity
            
            # Calculate average fill price
            total_filled_value = order.average_fill_price * (order.filled_quantity - fill.quantity)
            total_filled_value += fill.price * fill.quantity
            order.average_fill_price = total_filled_value / order.filled_quantity
            
            # Update order status
            if order.remaining_quantity <= 0:
                order.status = OrderStatus.FILLED
                order.fill_time = fill.timestamp
            else:
                order.status = OrderStatus.PARTIALLY_FILLED
            
            # Store fill
            self.order_fills[fill.order_id].append(fill)
            self._store_fill(fill)
            
            # Update venue performance
            self.venue_router.update_venue_performance(fill.venue, fill)
            
            logger.info(f"Fill processed: {fill.fill_id} - {fill.quantity} @ {fill.price}")
            
        except Exception as e:
            logger.error(f"Error processing fill: {e}")
    
    def _store_instruction(self, instruction: OrderInstruction):
        """Store instruction in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO order_instructions 
                (instruction_id, symbol, side, quantity, algorithm, urgency,
                 creation_time, time_horizon, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                instruction.instruction_id, instruction.symbol, instruction.side,
                instruction.quantity, instruction.algorithm.value, instruction.urgency.value,
                instruction.creation_time, instruction.time_horizon.total_seconds(),
                'ACTIVE'
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing instruction: {e}")
    
    def _store_order(self, order: Order):
        """Store order in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO orders 
                (order_id, instruction_id, symbol, side, quantity, order_type,
                 price, venue, status, creation_time, submission_time, fill_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                order.order_id, order.instruction_id, order.symbol, order.side,
                order.quantity, order.order_type.value, order.price,
                order.venue.value, order.status.value, order.creation_time,
                order.submission_time, order.fill_time
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing order: {e}")
    
    def _store_fill(self, fill: Fill):
        """Store fill in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO fills 
                (fill_id, order_id, symbol, side, quantity, price, venue,
                 timestamp, commission, fees, market_impact)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                fill.fill_id, fill.order_id, fill.symbol, fill.side,
                fill.quantity, fill.price, fill.venue.value, fill.timestamp,
                fill.commission, fill.fees, fill.market_impact
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing fill: {e}")
    
    def generate_execution_report(self, instruction_id: str) -> Optional[ExecutionReport]:
        """Generate execution report for completed instruction"""
        try:
            instruction = self.active_instructions.get(instruction_id)
            if not instruction:
                return None
            
            # Get all orders for this instruction
            instruction_orders = [
                order for order in self.active_orders.values()
                if order.instruction_id == instruction_id
            ]
            
            # Get all fills
            all_fills = []
            for order in instruction_orders:
                all_fills.extend(self.order_fills.get(order.order_id, []))
            
            if not all_fills:
                return None
            
            # Calculate metrics
            total_quantity = instruction.quantity
            filled_quantity = sum(fill.quantity for fill in all_fills)
            fill_rate = filled_quantity / total_quantity if total_quantity > 0 else 0.0
            
            # Calculate prices
            arrival_price = self.market_data.get(instruction.symbol, MarketData(
                symbol=instruction.symbol, timestamp=datetime.now(),
                bid_price=100, ask_price=100, last_price=100,
                bid_size=0, ask_size=0, last_size=0,
                volume=0, vwap=100, spread=0, midpoint=100,
                market_impact_estimate=0
            )).midpoint
            
            if filled_quantity > 0:
                total_value = sum(fill.quantity * fill.price for fill in all_fills)
                average_execution_price = total_value / filled_quantity
            else:
                average_execution_price = arrival_price
            
            # Calculate implementation shortfall
            if instruction.side == 'BUY':
                implementation_shortfall = (average_execution_price - arrival_price) / arrival_price
            else:
                implementation_shortfall = (arrival_price - average_execution_price) / arrival_price
            
            # Calculate costs
            total_commission = sum(fill.commission for fill in all_fills)
            total_fees = sum(fill.fees for fill in all_fills)
            market_impact = sum(fill.market_impact for fill in all_fills) / len(all_fills) if all_fills else 0.0
            timing_cost = implementation_shortfall - market_impact
            
            # Timing
            start_time = instruction.creation_time
            end_time = max(fill.timestamp for fill in all_fills) if all_fills else start_time
            
            # Create report
            report = ExecutionReport(
                instruction_id=instruction_id,
                symbol=instruction.symbol,
                total_quantity=total_quantity,
                filled_quantity=filled_quantity,
                fill_rate=fill_rate,
                arrival_price=arrival_price,
                average_execution_price=average_execution_price,
                implementation_shortfall=implementation_shortfall,
                market_impact=market_impact,
                timing_cost=timing_cost,
                total_commission=total_commission,
                total_fees=total_fees,
                total_transaction_cost=total_commission + total_fees + abs(implementation_shortfall * total_value),
                start_time=start_time,
                end_time=end_time,
                execution_duration=end_time - start_time,
                algorithm_used=instruction.algorithm,
                algorithm_effectiveness=max(0.0, 1.0 - abs(implementation_shortfall) * 100)  # Simplified
            )
            
            # Store report
            self.execution_reports.append(report)
            self._store_execution_report(report)
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating execution report: {e}")
            return None
    
    def _store_execution_report(self, report: ExecutionReport):
        """Store execution report in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO execution_reports 
                (instruction_id, symbol, total_quantity, filled_quantity, fill_rate,
                 arrival_price, average_execution_price, implementation_shortfall,
                 market_impact, total_transaction_cost, start_time, end_time, algorithm_used)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                report.instruction_id, report.symbol, report.total_quantity,
                report.filled_quantity, report.fill_rate, report.arrival_price,
                report.average_execution_price, report.implementation_shortfall,
                report.market_impact, report.total_transaction_cost,
                report.start_time, report.end_time, report.algorithm_used.value
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing execution report: {e}")
    
    def start_execution_monitoring(self):
        """Start execution monitoring"""
        if self.execution_thread and self.execution_thread.is_alive():
            logger.warning("Execution monitoring already running")
            return
        
        self.stop_event.clear()
        self.execution_thread = threading.Thread(target=self._execution_loop, daemon=True)
        self.execution_thread.start()
        
        logger.info("Execution monitoring started")
    
    def stop_execution_monitoring(self):
        """Stop execution monitoring"""
        self.stop_event.set()
        if self.execution_thread:
            self.execution_thread.join(timeout=5)
        
        logger.info("Execution monitoring stopped")
    
    def _execution_loop(self):
        """Main execution monitoring loop"""
        while not self.stop_event.is_set():
            try:
                # Update active orders
                self._update_active_orders()
                
                # Check for completed instructions
                self._check_completed_instructions()
                
                # Clean up old data
                self._cleanup_old_data()
                
                # Sleep
                self.stop_event.wait(5)  # 5 seconds
                
            except Exception as e:
                logger.error(f"Error in execution loop: {e}")
                time.sleep(5)
    
    def _update_active_orders(self):
        """Update active orders based on market conditions"""
        try:
            for instruction_id, instruction in self.active_instructions.items():
                # Get algorithm
                algorithm = self.algorithms.get(instruction.algorithm)
                if not algorithm:
                    continue
                
                # Get market data
                market_data = self.market_data.get(instruction.symbol)
                if not market_data:
                    continue
                
                # Get active orders for this instruction
                instruction_orders = [
                    order for order in self.active_orders.values()
                    if order.instruction_id == instruction_id and 
                    order.status in [OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED]
                ]
                
                # Get fills
                instruction_fills = []
                for order in instruction_orders:
                    instruction_fills.extend(self.order_fills.get(order.order_id, []))
                
                # Update execution
                updated_orders = algorithm.update_execution(
                    instruction, market_data, instruction_orders, instruction_fills
                )
                
                # Process updated orders
                for order in updated_orders:
                    if order.order_id in self.active_orders:
                        self.active_orders[order.order_id] = order
            
        except Exception as e:
            logger.error(f"Error updating active orders: {e}")
    
    def _check_completed_instructions(self):
        """Check for completed instructions and generate reports"""
        try:
            completed_instructions = []
            
            for instruction_id, instruction in self.active_instructions.items():
                # Check if instruction is complete
                instruction_orders = [
                    order for order in self.active_orders.values()
                    if order.instruction_id == instruction_id
                ]
                
                total_filled = sum(order.filled_quantity for order in instruction_orders)
                
                # Check completion conditions
                time_expired = datetime.now() > instruction.creation_time + instruction.time_horizon
                fully_filled = total_filled >= instruction.quantity
                
                if time_expired or fully_filled:
                    # Generate execution report
                    report = self.generate_execution_report(instruction_id)
                    if report:
                        logger.info(f"Instruction completed: {instruction_id}")
                        logger.info(f"Fill rate: {report.fill_rate:.1%}, IS: {report.implementation_shortfall:.4f}")
                    
                    completed_instructions.append(instruction_id)
            
            # Remove completed instructions
            for instruction_id in completed_instructions:
                del self.active_instructions[instruction_id]
            
        except Exception as e:
            logger.error(f"Error checking completed instructions: {e}")
    
    def _cleanup_old_data(self):
        """Clean up old execution data"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=24)
            
            # Clean up old orders
            old_orders = [
                order_id for order_id, order in self.active_orders.items()
                if order.creation_time < cutoff_time and 
                order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]
            ]
            
            for order_id in old_orders:
                del self.active_orders[order_id]
                if order_id in self.order_fills:
                    del self.order_fills[order_id]
            
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get comprehensive execution summary"""
        try:
            recent_reports = self.execution_reports[-10:] if len(self.execution_reports) >= 10 else self.execution_reports
            
            # Calculate aggregate metrics
            if recent_reports:
                avg_fill_rate = np.mean([r.fill_rate for r in recent_reports])
                avg_implementation_shortfall = np.mean([r.implementation_shortfall for r in recent_reports])
                avg_market_impact = np.mean([r.market_impact for r in recent_reports])
                avg_transaction_cost = np.mean([r.total_transaction_cost for r in recent_reports])
            else:
                avg_fill_rate = 0.0
                avg_implementation_shortfall = 0.0
                avg_market_impact = 0.0
                avg_transaction_cost = 0.0
            
            return {
                'active_instructions': len(self.active_instructions),
                'active_orders': len([o for o in self.active_orders.values() 
                                    if o.status in [OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED]]),
                'total_execution_reports': len(self.execution_reports),
                'available_algorithms': [alg.value for alg in self.algorithms.keys()],
                'performance_metrics': {
                    'avg_fill_rate': avg_fill_rate,
                    'avg_implementation_shortfall': avg_implementation_shortfall,
                    'avg_market_impact': avg_market_impact,
                    'avg_transaction_cost': avg_transaction_cost
                },
                'venue_performance': dict(self.venue_router.venue_performance),
                'recent_reports': [
                    {
                        'instruction_id': r.instruction_id,
                        'symbol': r.symbol,
                        'fill_rate': r.fill_rate,
                        'implementation_shortfall': r.implementation_shortfall,
                        'algorithm_used': r.algorithm_used.value,
                        'execution_duration': r.execution_duration.total_seconds()
                    }
                    for r in recent_reports
                ],
                'monitoring_status': 'RUNNING' if self.execution_thread and self.execution_thread.is_alive() else 'STOPPED',
                'last_update': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating execution summary: {e}")
            return {}

# Example usage
if __name__ == "__main__":
    # Configuration for execution engine
    config = {
        'algorithms': {
            'twap': {
                'execution_intervals': 10,
                'price_improvement_threshold': 0.001,
                'max_slice_size': 1000,
                'min_slice_size': 100
            },
            'vwap': {
                'volume_profile': 'HISTORICAL',
                'participation_rate': 0.10,
                'max_slice_size': 1500,
                'min_slice_size': 100
            },
            'implementation_shortfall': {
                'risk_aversion': 0.5,
                'volatility_estimate': 0.02,
                'adaptation_speed': 0.1,
                'max_slice_size': 2000,
                'min_slice_size': 100
            }
        },
        'venue_config': {},
        'db_path': 'advanced_execution_optimization.db'
    }
    
    # Create execution engine
    execution_engine = ExecutionEngine(config)
    
    # Start monitoring
    execution_engine.start_execution_monitoring()
    
    # Create sample market data
    market_data = MarketData(
        symbol='AAPL',
        timestamp=datetime.now(),
        bid_price=149.95,
        ask_price=150.05,
        last_price=150.00,
        bid_size=1000,
        ask_size=1200,
        last_size=500,
        volume=1000000,
        vwap=149.98,
        spread=0.10,
        midpoint=150.00,
        market_impact_estimate=0.002
    )
    
    execution_engine.update_market_data('AAPL', market_data)
    
    # Create sample order instruction
    instruction = OrderInstruction(
        instruction_id='test_instruction_001',
        symbol='AAPL',
        side='BUY',
        quantity=10000,
        algorithm=ExecutionAlgorithm.IMPLEMENTATION_SHORTFALL,
        urgency=ExecutionUrgency.MEDIUM,
        time_horizon=timedelta(hours=2),
        max_participation_rate=0.15,
        max_market_impact=0.005,
        parent_strategy='MOMENTUM_STRATEGY'
    )
    
    # Submit instruction
    success = execution_engine.submit_instruction(instruction)
    print(f"Instruction submitted: {success}")
    
    # Simulate some fills
    import random
    
    # Get orders for the instruction
    instruction_orders = [
        order for order in execution_engine.active_orders.values()
        if order.instruction_id == instruction.instruction_id
    ]
    
    for order in instruction_orders[:3]:  # Fill first 3 orders
        # Simulate partial fill
        fill_quantity = min(order.quantity, random.randint(100, 500))
        fill_price = market_data.midpoint + random.uniform(-0.02, 0.02)
        
        fill = Fill(
            fill_id=f"fill_{order.order_id}_{int(datetime.now().timestamp())}",
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=fill_quantity,
            price=fill_price,
            venue=order.venue,
            timestamp=datetime.now(),
            commission=fill_quantity * 0.001,  # $0.001 per share
            market_impact=random.uniform(0.0005, 0.002)
        )
        
        execution_engine.process_fill(fill)
        print(f"Fill processed: {fill.quantity} @ {fill.price:.2f}")
    
    # Wait a bit for processing
    time.sleep(2)
    
    # Generate execution report
    report = execution_engine.generate_execution_report(instruction.instruction_id)
    if report:
        print(f"\n--- Execution Report ---")
        print(f"Symbol: {report.symbol}")
        print(f"Total Quantity: {report.total_quantity:,}")
        print(f"Filled Quantity: {report.filled_quantity:,}")
        print(f"Fill Rate: {report.fill_rate:.1%}")
        print(f"Arrival Price: ${report.arrival_price:.2f}")
        print(f"Average Execution Price: ${report.average_execution_price:.2f}")
        print(f"Implementation Shortfall: {report.implementation_shortfall:.4f} ({report.implementation_shortfall*10000:.1f} bps)")
        print(f"Market Impact: {report.market_impact:.4f} ({report.market_impact*10000:.1f} bps)")
        print(f"Total Transaction Cost: ${report.total_transaction_cost:.2f}")
        print(f"Algorithm Used: {report.algorithm_used.value}")
        print(f"Execution Duration: {report.execution_duration}")
    
    # Get execution summary
    summary = execution_engine.get_execution_summary()
    print(f"\nExecution Engine Summary:")
    print(json.dumps(summary, indent=2))
    
    # Stop monitoring
    execution_engine.stop_execution_monitoring() 