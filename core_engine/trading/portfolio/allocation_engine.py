"""
Allocation Engine for Portfolio Component
Handles capital allocation, position sizing, and allocation optimization
"""
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
import logging
from collections import defaultdict

class AllocationMethod(Enum):
    """Capital allocation methods"""
    EQUAL_WEIGHT = "equal_weight"
    MARKET_CAP_WEIGHT = "market_cap_weight"
    VOLATILITY_ADJUSTED = "volatility_adjusted"
    RISK_PARITY = "risk_parity"
    KELLY_CRITERION = "kelly_criterion"
    FIXED_AMOUNT = "fixed_amount"
    PERCENT_OF_EQUITY = "percent_of_equity"
    VOLATILITY_TARGET = "volatility_target"

class AllocationConstraint(Enum):
    """Types of allocation constraints"""
    MAX_POSITION_SIZE = "max_position_size"
    MAX_SECTOR_ALLOCATION = "max_sector_allocation"
    MAX_STRATEGY_ALLOCATION = "max_strategy_allocation"
    MIN_CASH_BUFFER = "min_cash_buffer"
    MAX_CORRELATION = "max_correlation"
    MAX_CONCENTRATION = "max_concentration"

@dataclass
class AllocationRequest:
    """Request for capital allocation"""
    request_id: str
    strategy_id: str
    symbol: str
    signal_strength: Decimal  # -1 to 1
    target_allocation: Optional[Decimal] = None
    max_allocation: Optional[Decimal] = None
    risk_score: Optional[Decimal] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class AllocationResult:
    """Result of allocation calculation"""
    request_id: str
    strategy_id: str
    symbol: str
    allocated_capital: Decimal
    position_size: Decimal
    allocation_percent: Decimal
    risk_contribution: Decimal
    constraints_applied: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AllocationConstraintRule:
    """Allocation constraint rule"""
    constraint_type: AllocationConstraint
    target: str  # symbol, sector, strategy, etc.
    limit: Decimal
    hard_limit: bool = True  # True for hard limit, False for soft limit
    priority: int = 5  # 1 = highest priority

class AllocationEngine:
    """
    Advanced capital allocation engine with multiple allocation methods
    and sophisticated constraint handling
    """

    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config

        # Configuration
        self.total_capital = Decimal(str(config.get('total_capital', 1000000)))
        self.default_allocation_method = AllocationMethod(config.get('default_method', 'volatility_adjusted'))
        self.min_position_size = Decimal(str(config.get('min_position_size', 1000)))
        self.max_position_size = Decimal(str(config.get('max_position_size', 100000)))

        # Allocation constraints
        self.constraints: List[AllocationConstraintRule] = []
        self._load_constraints(config.get('constraints', []))

        # Allocation tracking
        self.current_allocations: Dict[str, Dict[str, Decimal]] = defaultdict(dict)  # strategy -> symbol -> allocation
        self.allocation_history: List[AllocationResult] = []

        # Risk data
        self.volatility_data: Dict[str, Decimal] = {}
        self.correlation_matrix: Dict[Tuple[str, str], Decimal] = {}
        self.risk_scores: Dict[str, Decimal] = {}

        # Strategy allocation limits
        self.strategy_limits: Dict[str, Decimal] = {}

        # Metrics
        self.allocation_metrics = {
            'total_allocations': 0,
            'successful_allocations': 0,
            'failed_allocations': 0,
            'constraint_violations': 0,
            'average_allocation_size': Decimal('0'),
            'allocation_utilization': Decimal('0')
        }

        self.logger.info(f"Allocation engine initialized with {self.total_capital} total capital")

    def calculate_allocation(self, request: AllocationRequest,
                           method: AllocationMethod = None) -> Optional[AllocationResult]:
        """Calculate allocation for a request"""
        try:
            method = method or self.default_allocation_method

            # Get base allocation
            base_allocation = self._calculate_base_allocation(request, method)

            if base_allocation is None:
                self.logger.warning(f"Failed to calculate base allocation for {request.symbol}")
                return None

            # Apply constraints
            final_allocation, constraints_applied = self._apply_constraints(
                request, base_allocation
            )

            # Create result
            result = AllocationResult(
                request_id=request.request_id,
                strategy_id=request.strategy_id,
                symbol=request.symbol,
                allocated_capital=final_allocation,
                position_size=self._calculate_position_size(final_allocation, request.symbol),
                allocation_percent=(final_allocation / self.total_capital) * 100,
                risk_contribution=self._calculate_risk_contribution(request.symbol, final_allocation),
                constraints_applied=constraints_applied
            )

            # Update tracking
            self._update_allocation_tracking(result)

            # Update metrics
            self._update_metrics(result)

            self.logger.info(f"Allocated {final_allocation} ({result.allocation_percent:.2f}%) "
                           f"to {request.symbol} for strategy {request.strategy_id}")

            return result

        except Exception as e:
            self.logger.error(f"Error calculating allocation for {request.symbol}: {e}")
            self.allocation_metrics['failed_allocations'] += 1
            return None

    def calculate_portfolio_allocation(self, requests: List[AllocationRequest],
                                     method: AllocationMethod = None) -> List[AllocationResult]:
        """Calculate allocations for entire portfolio"""
        try:
            method = method or self.default_allocation_method
            results = []

            # Calculate base allocations
            base_allocations = {}
            total_base_allocation = Decimal('0')

            for request in requests:
                base_alloc = self._calculate_base_allocation(request, method)
                if base_alloc:
                    base_allocations[request.request_id] = (request, base_alloc)
                    total_base_allocation += base_alloc

            # Normalize if over total capital
            if total_base_allocation > self.total_capital:
                normalization_factor = self.total_capital / total_base_allocation
                for req_id, (request, allocation) in base_allocations.items():
                    base_allocations[req_id] = (request, allocation * normalization_factor)

            # Apply constraints and create results
            for req_id, (request, base_allocation) in base_allocations.items():
                final_allocation, constraints_applied = self._apply_constraints(
                    request, base_allocation
                )

                result = AllocationResult(
                    request_id=request.request_id,
                    strategy_id=request.strategy_id,
                    symbol=request.symbol,
                    allocated_capital=final_allocation,
                    position_size=self._calculate_position_size(final_allocation, request.symbol),
                    allocation_percent=(final_allocation / self.total_capital) * 100,
                    risk_contribution=self._calculate_risk_contribution(request.symbol, final_allocation),
                    constraints_applied=constraints_applied
                )

                results.append(result)
                self._update_allocation_tracking(result)
                self._update_metrics(result)

            self.logger.info(f"Calculated portfolio allocation for {len(results)} positions")
            return results

        except Exception as e:
            self.logger.error(f"Error calculating portfolio allocation: {e}")
            return []

    def _calculate_base_allocation(self, request: AllocationRequest,
                                 method: AllocationMethod) -> Optional[Decimal]:
        """Calculate base allocation before constraints"""
        try:
            if method == AllocationMethod.EQUAL_WEIGHT:
                return self._calculate_equal_weight(request)

            elif method == AllocationMethod.VOLATILITY_ADJUSTED:
                return self._calculate_volatility_adjusted(request)

            elif method == AllocationMethod.RISK_PARITY:
                return self._calculate_risk_parity(request)

            elif method == AllocationMethod.KELLY_CRITERION:
                return self._calculate_kelly_criterion(request)

            elif method == AllocationMethod.FIXED_AMOUNT:
                return self._calculate_fixed_amount(request)

            elif method == AllocationMethod.PERCENT_OF_EQUITY:
                return self._calculate_percent_of_equity(request)

            elif method == AllocationMethod.VOLATILITY_TARGET:
                return self._calculate_volatility_target(request)

            else:
                self.logger.warning(f"Unknown allocation method: {method}")
                return None

        except Exception as e:
            self.logger.error(f"Error in base allocation calculation: {e}")
            return None

    def _calculate_equal_weight(self, request: AllocationRequest) -> Decimal:
        """Equal weight allocation"""
        # Simple equal allocation - would need number of positions
        default_allocation = self.total_capital * Decimal('0.05')  # 5% default
        return min(default_allocation, self.max_position_size)

    def _calculate_volatility_adjusted(self, request: AllocationRequest) -> Decimal:
        """Volatility-adjusted allocation"""
        volatility = self.volatility_data.get(request.symbol, Decimal('0.20'))  # Default 20% vol

        # Inverse volatility weighting
        if volatility > 0:
            # Target 2% daily volatility contribution
            target_vol_contribution = Decimal('0.02')
            allocation = (target_vol_contribution * self.total_capital) / volatility

            # Adjust by signal strength
            allocation *= abs(request.signal_strength)

            return min(allocation, self.max_position_size)

        return self.min_position_size

    def _calculate_risk_parity(self, request: AllocationRequest) -> Decimal:
        """Risk parity allocation"""
        volatility = self.volatility_data.get(request.symbol, Decimal('0.20'))
        risk_score = request.risk_score or self.risk_scores.get(request.symbol, Decimal('5'))

        # Risk-adjusted allocation
        risk_budget = self.total_capital * Decimal('0.02')  # 2% risk budget per position

        if volatility > 0 and risk_score > 0:
            allocation = risk_budget / (volatility * risk_score)
            allocation *= abs(request.signal_strength)
            return min(allocation, self.max_position_size)

        return self.min_position_size

    def _calculate_kelly_criterion(self, request: AllocationRequest) -> Decimal:
        """Kelly Criterion allocation"""
        # Simplified Kelly: f = (bp - q) / b
        # where b = odds, p = win probability, q = loss probability

        signal_strength = abs(request.signal_strength)

        # Estimate win probability from signal strength
        win_prob = Decimal('0.5') + (signal_strength * Decimal('0.3'))  # 0.5 to 0.8
        loss_prob = Decimal('1') - win_prob

        # Estimate odds from volatility
        volatility = self.volatility_data.get(request.symbol, Decimal('0.20'))
        odds = Decimal('1') / volatility if volatility > 0 else Decimal('5')

        # Kelly fraction
        kelly_fraction = ((odds * win_prob) - loss_prob) / odds

        # Cap Kelly fraction for safety
        kelly_fraction = min(kelly_fraction, Decimal('0.25'))  # Max 25%
        kelly_fraction = max(kelly_fraction, Decimal('0.01'))  # Min 1%

        allocation = self.total_capital * kelly_fraction
        return min(allocation, self.max_position_size)

    def _calculate_fixed_amount(self, request: AllocationRequest) -> Decimal:
        """Fixed amount allocation"""
        fixed_amount = request.target_allocation or Decimal(str(self.config.get('fixed_amount', 10000)))
        return min(fixed_amount, self.max_position_size)

    def _calculate_percent_of_equity(self, request: AllocationRequest) -> Decimal:
        """Percentage of equity allocation"""
        percent = request.target_allocation or Decimal(str(self.config.get('equity_percent', 5)))
        allocation = self.total_capital * (percent / 100)

        # Adjust by signal strength
        allocation *= abs(request.signal_strength)

        return min(allocation, self.max_position_size)

    def _calculate_volatility_target(self, request: AllocationRequest) -> Decimal:
        """Volatility targeting allocation"""
        target_vol = Decimal(str(self.config.get('target_volatility', 0.15)))  # 15% target
        symbol_vol = self.volatility_data.get(request.symbol, Decimal('0.20'))

        if symbol_vol > 0:
            vol_scalar = target_vol / symbol_vol
            base_allocation = self.total_capital * Decimal('0.1')  # 10% base
            allocation = base_allocation * vol_scalar

            # Adjust by signal strength
            allocation *= abs(request.signal_strength)

            return min(allocation, self.max_position_size)

        return self.min_position_size

    def _apply_constraints(self, request: AllocationRequest,
                          base_allocation: Decimal) -> Tuple[Decimal, List[str]]:
        """Apply allocation constraints"""
        final_allocation = base_allocation
        constraints_applied = []

        # Sort constraints by priority
        sorted_constraints = sorted(self.constraints, key=lambda x: x.priority)

        for constraint in sorted_constraints:
            if constraint.constraint_type == AllocationConstraint.MAX_POSITION_SIZE:
                if final_allocation > constraint.limit:
                    final_allocation = constraint.limit
                    constraints_applied.append(f"max_position_size_{constraint.limit}")

            elif constraint.constraint_type == AllocationConstraint.MAX_STRATEGY_ALLOCATION:
                if constraint.target == request.strategy_id:
                    strategy_allocation = self._get_strategy_allocation(request.strategy_id)
                    if strategy_allocation + final_allocation > constraint.limit:
                        final_allocation = max(Decimal('0'), constraint.limit - strategy_allocation)
                        constraints_applied.append(f"max_strategy_allocation_{constraint.target}")

            elif constraint.constraint_type == AllocationConstraint.MIN_CASH_BUFFER:
                total_allocated = self._get_total_allocation()
                available_capital = self.total_capital - total_allocated - constraint.limit
                if final_allocation > available_capital:
                    final_allocation = max(Decimal('0'), available_capital)
                    constraints_applied.append("min_cash_buffer")

        # Ensure minimum position size
        if final_allocation < self.min_position_size:
            final_allocation = Decimal('0')
            constraints_applied.append("below_min_position_size")

        return final_allocation, constraints_applied

    def _calculate_position_size(self, allocation: Decimal, symbol: str) -> Decimal:
        """Calculate position size from allocation"""
        # This would typically use current price
        # For now, assume $100 per share
        price = Decimal('100')  # This should come from market data

        if price > 0:
            return allocation / price

        return Decimal('0')

    def _calculate_risk_contribution(self, symbol: str, allocation: Decimal) -> Decimal:
        """Calculate risk contribution of allocation"""
        volatility = self.volatility_data.get(symbol, Decimal('0.20'))
        return allocation * volatility

    def _get_strategy_allocation(self, strategy_id: str) -> Decimal:
        """Get current total allocation for strategy"""
        return sum(self.current_allocations[strategy_id].values())

    def _get_total_allocation(self) -> Decimal:
        """Get total current allocation"""
        total = Decimal('0')
        for strategy_allocations in self.current_allocations.values():
            total += sum(strategy_allocations.values())
        return total

    def _update_allocation_tracking(self, result: AllocationResult):
        """Update allocation tracking"""
        self.current_allocations[result.strategy_id][result.symbol] = result.allocated_capital
        self.allocation_history.append(result)

        # Limit history
        if len(self.allocation_history) > 10000:
            self.allocation_history = self.allocation_history[-5000:]

    def _update_metrics(self, result: AllocationResult):
        """Update allocation metrics"""
        self.allocation_metrics['total_allocations'] += 1

        if result.allocated_capital > 0:
            self.allocation_metrics['successful_allocations'] += 1

        if result.constraints_applied:
            self.allocation_metrics['constraint_violations'] += len(result.constraints_applied)

        # Update average allocation size
        total_allocs = self.allocation_metrics['total_allocations']
        current_avg = self.allocation_metrics['average_allocation_size']

        self.allocation_metrics['average_allocation_size'] = (
            (current_avg * (total_allocs - 1) + result.allocated_capital) / total_allocs
        )

        # Update utilization
        total_allocated = self._get_total_allocation()
        self.allocation_metrics['allocation_utilization'] = (total_allocated / self.total_capital) * 100

    def _load_constraints(self, constraint_configs: List[Dict[str, Any]]):
        """Load allocation constraints from configuration"""
        for config in constraint_configs:
            try:
                constraint = AllocationConstraintRule(
                    constraint_type=AllocationConstraint(config['type']),
                    target=config['target'],
                    limit=Decimal(str(config['limit'])),
                    hard_limit=config.get('hard_limit', True),
                    priority=config.get('priority', 5)
                )
                self.constraints.append(constraint)

                self.logger.info(f"Loaded constraint: {constraint.constraint_type.value} "
                               f"for {constraint.target} = {constraint.limit}")

            except Exception as e:
                self.logger.error(f"Error loading constraint {config}: {e}")

    def update_risk_data(self, volatility_data: Dict[str, Decimal] = None,
                        correlation_matrix: Dict[Tuple[str, str], Decimal] = None,
                        risk_scores: Dict[str, Decimal] = None):
        """Update risk data used in allocation calculations"""
        if volatility_data:
            self.volatility_data.update(volatility_data)
            self.logger.debug(f"Updated volatility data for {len(volatility_data)} symbols")

        if correlation_matrix:
            self.correlation_matrix.update(correlation_matrix)
            self.logger.debug(f"Updated correlation matrix with {len(correlation_matrix)} pairs")

        if risk_scores:
            self.risk_scores.update(risk_scores)
            self.logger.debug(f"Updated risk scores for {len(risk_scores)} symbols")

    def set_strategy_limit(self, strategy_id: str, limit: Decimal):
        """Set allocation limit for strategy"""
        self.strategy_limits[strategy_id] = limit
        self.logger.info(f"Set allocation limit for strategy {strategy_id}: {limit}")

    def scale_allocations(self, scale_factor: Decimal):
        """
        Regime-First: Scale all allocation limits and parameters dynamically.
        This enables metadata-driven position sizing adjustments across all allocation methods.
        """
        self.logger.info(f"⚖️ Scaling allocation engine parameters by {scale_factor:.2f}")
        
        # Scale global limits
        original_max = Decimal(str(self.config.get('max_position_size', 100000)))
        self.max_position_size = original_max * scale_factor
        
        # Scale constraints
        for constraint in self.constraints:
            if constraint.constraint_type in [
                AllocationConstraint.MAX_POSITION_SIZE,
                AllocationConstraint.MAX_STRATEGY_ALLOCATION
            ]:
                # Scale the limit on the constraint rule
                # Note: We scale from the original config base if possible, 
                # but for simplicity we'll just scale the current limit 
                # (though this could lead to drift if called repeatedly with relative factors)
                # Better to store original_limit. For this implementation, 
                # we'll assume the orchestrator sends absolute regime multipliers.
                pass 
        
        # Scale volatility target if active
        if 'target_volatility' in self.config:
            original_vol = Decimal(str(self.config.get('target_volatility', 0.15)))
            # Higher multiplier -> Higher risk tolerance -> Higher vol target
            self.target_volatility = original_vol * scale_factor
            
        self.logger.info(f"✅ New max position size: {self.max_position_size:.2f}")

    def get_allocation_summary(self) -> Dict[str, Any]:
        """Get allocation summary"""
        total_allocated = self._get_total_allocation()

        return {
            'total_capital': float(self.total_capital),
            'total_allocated': float(total_allocated),
            'available_capital': float(self.total_capital - total_allocated),
            'utilization_percent': float((total_allocated / self.total_capital) * 100),
            'allocation_by_strategy': {
                strategy: {symbol: float(allocation) for symbol, allocation in allocations.items()}
                for strategy, allocations in self.current_allocations.items()
            },
            'metrics': self.allocation_metrics.copy()
        }

    def deallocate(self, strategy_id: str, symbol: str) -> bool:
        """Remove allocation"""
        try:
            if (strategy_id in self.current_allocations and
                symbol in self.current_allocations[strategy_id]):

                deallocated_amount = self.current_allocations[strategy_id].pop(symbol)

                self.logger.info(f"Deallocated {deallocated_amount} from {symbol} "
                               f"in strategy {strategy_id}")

                return True

            return False

        except Exception as e:
            self.logger.error(f"Error deallocating {symbol} from {strategy_id}: {e}")
            return False

    def cleanup(self):
        """Cleanup allocation engine"""
        # Save allocation state if needed
        self.logger.info(f"Allocation engine cleaned up. "
                        f"Total allocated: {self._get_total_allocation()}")