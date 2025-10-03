"""
Portfolio Rebalancer for Portfolio Component
Handles portfolio rebalancing, drift management, and optimization
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum
import logging

from .position_manager import Position, PositionType, PositionManager
from .allocation_engine import AllocationEngine, AllocationRequest, AllocationResult

class RebalanceFrequency(Enum):
    """Rebalancing frequency"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    THRESHOLD_BASED = "threshold_based"
    VOLATILITY_BASED = "volatility_based"

class RebalanceType(Enum):
    """Types of rebalancing"""
    FULL_REBALANCE = "full_rebalance"
    DRIFT_CORRECTION = "drift_correction"
    RISK_REBALANCE = "risk_rebalance"
    OPPORTUNISTIC = "opportunistic"
    EMERGENCY = "emergency"

@dataclass
class RebalanceTarget:
    """Target allocation for rebalancing"""
    symbol: str
    strategy_id: str
    target_weight: Decimal
    target_allocation: Decimal
    current_allocation: Decimal
    drift: Decimal
    priority: int = 5
    
    @property
    def drift_percent(self) -> Decimal:
        """Drift as percentage of target"""
        if self.target_allocation == 0:
            return Decimal('0')
        return (self.drift / self.target_allocation) * 100

@dataclass
class RebalanceAction:
    """Rebalancing action"""
    symbol: str
    strategy_id: str
    action_type: str  # 'buy', 'sell', 'hold'
    current_position: Decimal
    target_position: Decimal
    trade_amount: Decimal
    trade_value: Decimal
    urgency: int = 5  # 1 = urgent, 10 = low priority

@dataclass
class RebalanceResult:
    """Result of rebalancing operation"""
    rebalance_id: str
    rebalance_type: RebalanceType
    trigger_reason: str
    targets: List[RebalanceTarget]
    actions: List[RebalanceAction]
    total_turnover: Decimal
    execution_cost: Decimal
    risk_reduction: Decimal
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "pending"  # pending, executing, completed, failed

class PortfolioRebalancer:
    """
    Advanced portfolio rebalancing system with multiple rebalancing strategies
    """
    
    def __init__(self, config: Dict[str, Any], position_manager: PositionManager,
                 allocation_engine: AllocationEngine):
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.position_manager = position_manager
        self.allocation_engine = allocation_engine
        
        # Rebalancing configuration
        self.rebalance_frequency = RebalanceFrequency(config.get('frequency', 'threshold_based'))
        self.drift_threshold = Decimal(str(config.get('drift_threshold', 0.05)))  # 5%
        self.min_trade_size = Decimal(str(config.get('min_trade_size', 1000)))
        self.max_turnover = Decimal(str(config.get('max_turnover', 0.20)))  # 20%
        
        # Risk-based rebalancing
        self.risk_threshold = Decimal(str(config.get('risk_threshold', 0.15)))
        self.correlation_threshold = Decimal(str(config.get('correlation_threshold', 0.8)))
        
        # Cost considerations
        self.transaction_cost_rate = Decimal(str(config.get('transaction_cost_rate', 0.001)))  # 0.1%
        self.market_impact_factor = Decimal(str(config.get('market_impact_factor', 0.0005)))
        
        # Target portfolios
        self.target_portfolios: Dict[str, Dict[str, Decimal]] = {}  # strategy -> symbol -> weight
        self.target_allocations: Dict[str, Dict[str, Decimal]] = {}  # strategy -> symbol -> allocation
        
        # Rebalancing history
        self.rebalance_history: List[RebalanceResult] = []
        self.last_rebalance_time: Optional[datetime] = None
        
        # Metrics
        self.rebalance_metrics = {
            'total_rebalances': 0,
            'successful_rebalances': 0,
            'failed_rebalances': 0,
            'total_turnover': Decimal('0'),
            'total_transaction_costs': Decimal('0'),
            'average_drift_reduction': Decimal('0'),
            'rebalances_by_type': {}
        }
        
        self.logger.info("Portfolio rebalancer initialized")
    
    def set_target_portfolio(self, strategy_id: str, targets: Dict[str, Decimal]):
        """Set target weights for a strategy"""
        # Normalize weights to sum to 1
        total_weight = sum(targets.values())
        if total_weight > 0:
            normalized_targets = {symbol: weight / total_weight 
                                for symbol, weight in targets.items()}
            self.target_portfolios[strategy_id] = normalized_targets
            
            # Calculate target allocations
            strategy_capital = self.allocation_engine.get_strategy_allocation(strategy_id)
            if strategy_capital == 0:
                strategy_capital = self.allocation_engine.total_capital * Decimal('0.1')  # Default 10%
            
            self.target_allocations[strategy_id] = {
                symbol: weight * strategy_capital
                for symbol, weight in normalized_targets.items()
            }
            
            self.logger.info(f"Set target portfolio for strategy {strategy_id} "
                           f"with {len(targets)} symbols")
    
    def check_rebalance_needed(self, strategy_id: str = None) -> Dict[str, Any]:
        """Check if rebalancing is needed"""
        try:
            rebalance_needed = False
            triggers = []
            strategy_analysis = {}
            
            strategies_to_check = [strategy_id] if strategy_id else list(self.target_portfolios.keys())
            
            for strat_id in strategies_to_check:
                analysis = self._analyze_strategy_drift(strat_id)
                strategy_analysis[strat_id] = analysis
                
                # Check drift threshold
                if analysis['max_drift_percent'] > self.drift_threshold * 100:
                    rebalance_needed = True
                    triggers.append(f"drift_threshold_{strat_id}")
                
                # Check risk metrics
                if analysis['risk_concentration'] > self.risk_threshold:
                    rebalance_needed = True
                    triggers.append(f"risk_concentration_{strat_id}")
                
                # Check correlation clustering
                if analysis['max_correlation'] > self.correlation_threshold:
                    rebalance_needed = True
                    triggers.append(f"correlation_clustering_{strat_id}")
            
            # Check time-based triggers
            if self._check_time_trigger():
                rebalance_needed = True
                triggers.append("scheduled_rebalance")
            
            return {
                'rebalance_needed': rebalance_needed,
                'triggers': triggers,
                'strategy_analysis': strategy_analysis,
                'last_rebalance': self.last_rebalance_time
            }
            
        except Exception as e:
            self.logger.error(f"Error checking rebalance need: {e}")
            return {'rebalance_needed': False, 'error': str(e)}
    
    def execute_rebalance(self, strategy_id: str = None, 
                         rebalance_type: RebalanceType = RebalanceType.DRIFT_CORRECTION,
                         force: bool = False) -> Optional[RebalanceResult]:
        """Execute portfolio rebalancing"""
        try:
            # Check if rebalancing is needed
            if not force:
                check_result = self.check_rebalance_needed(strategy_id)
                if not check_result['rebalance_needed']:
                    self.logger.info("No rebalancing needed")
                    return None
                
                trigger_reason = ", ".join(check_result['triggers'])
            else:
                trigger_reason = "forced_rebalance"
            
            # Generate rebalancing targets
            targets = self._generate_rebalance_targets(strategy_id)
            if not targets:
                self.logger.warning("No rebalancing targets generated")
                return None
            
            # Generate rebalancing actions
            actions = self._generate_rebalance_actions(targets)
            
            # Filter actions by minimum trade size
            actions = [action for action in actions 
                      if abs(action.trade_value) >= self.min_trade_size]
            
            if not actions:
                self.logger.info("No significant rebalancing actions needed")
                return None
            
            # Check turnover limits
            total_turnover = self._calculate_turnover(actions)
            if total_turnover > self.max_turnover:
                actions = self._reduce_turnover(actions, total_turnover)
                total_turnover = self._calculate_turnover(actions)
            
            # Calculate costs
            execution_cost = self._calculate_execution_cost(actions)
            
            # Create rebalance result
            result = RebalanceResult(
                rebalance_id=f"rebal_{datetime.now().timestamp()}",
                rebalance_type=rebalance_type,
                trigger_reason=trigger_reason,
                targets=targets,
                actions=actions,
                total_turnover=total_turnover,
                execution_cost=execution_cost,
                risk_reduction=self._estimate_risk_reduction(targets)
            )
            
            # Execute if actions exist
            if actions:
                success = self._execute_rebalance_actions(result)
                result.status = "completed" if success else "failed"
            else:
                result.status = "no_action_needed"
            
            # Update tracking
            self._update_rebalance_tracking(result)
            
            self.logger.info(f"Executed rebalance {result.rebalance_id}: "
                           f"{len(actions)} actions, turnover: {total_turnover:.2%}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error executing rebalance: {e}")
            return None
    
    def _analyze_strategy_drift(self, strategy_id: str) -> Dict[str, Any]:
        """Analyze drift for a strategy"""
        if strategy_id not in self.target_portfolios:
            return {'error': 'Strategy not found'}
        
        current_positions = self.position_manager.get_positions_by_strategy(strategy_id)
        target_weights = self.target_portfolios[strategy_id]
        target_allocations = self.target_allocations.get(strategy_id, {})
        
        # Calculate current allocations
        current_allocations = {}
        total_current_value = Decimal('0')
        
        for position in current_positions:
            current_allocations[position.symbol] = position.market_value
            total_current_value += abs(position.market_value)
        
        # Calculate current weights
        current_weights = {}
        if total_current_value > 0:
            current_weights = {symbol: allocation / total_current_value
                             for symbol, allocation in current_allocations.items()}
        
        # Calculate drifts
        drifts = {}
        for symbol in set(list(target_weights.keys()) + list(current_weights.keys())):
            target_weight = target_weights.get(symbol, Decimal('0'))
            current_weight = current_weights.get(symbol, Decimal('0'))
            drift = current_weight - target_weight
            drifts[symbol] = {
                'target_weight': target_weight,
                'current_weight': current_weight,
                'drift': drift,
                'drift_percent': (drift / target_weight * 100) if target_weight > 0 else Decimal('0')
            }
        
        # Calculate metrics
        max_drift = max(abs(d['drift']) for d in drifts.values()) if drifts else Decimal('0')
        max_drift_percent = max(abs(d['drift_percent']) for d in drifts.values()) if drifts else Decimal('0')
        
        # Risk concentration (simplified)
        risk_concentration = max(current_weights.values()) if current_weights else Decimal('0')
        
        # Correlation analysis (simplified)
        max_correlation = Decimal('0.5')  # Placeholder - would calculate from correlation matrix
        
        return {
            'strategy_id': strategy_id,
            'current_allocations': current_allocations,
            'target_allocations': target_allocations,
            'drifts': drifts,
            'max_drift': max_drift,
            'max_drift_percent': max_drift_percent,
            'risk_concentration': risk_concentration,
            'max_correlation': max_correlation,
            'total_value': total_current_value
        }
    
    def _generate_rebalance_targets(self, strategy_id: str = None) -> List[RebalanceTarget]:
        """Generate rebalancing targets"""
        targets = []
        
        strategies_to_rebalance = [strategy_id] if strategy_id else list(self.target_portfolios.keys())
        
        for strat_id in strategies_to_rebalance:
            if strat_id not in self.target_portfolios:
                continue
            
            analysis = self._analyze_strategy_drift(strat_id)
            
            for symbol, drift_info in analysis['drifts'].items():
                if abs(drift_info['drift']) > self.drift_threshold:
                    target = RebalanceTarget(
                        symbol=symbol,
                        strategy_id=strat_id,
                        target_weight=drift_info['target_weight'],
                        target_allocation=analysis['target_allocations'].get(symbol, Decimal('0')),
                        current_allocation=analysis['current_allocations'].get(symbol, Decimal('0')),
                        drift=drift_info['drift'],
                        priority=self._calculate_rebalance_priority(drift_info)
                    )
                    targets.append(target)
        
        # Sort by priority
        targets.sort(key=lambda x: x.priority)
        
        return targets
    
    def _generate_rebalance_actions(self, targets: List[RebalanceTarget]) -> List[RebalanceAction]:
        """Generate specific rebalancing actions"""
        actions = []
        
        for target in targets:
            allocation_diff = target.target_allocation - target.current_allocation
            
            # Get current position
            positions = self.position_manager.get_positions_by_symbol(target.symbol)
            strategy_positions = [p for p in positions if p.strategy_id == target.strategy_id]
            
            current_position = Decimal('0')
            if strategy_positions:
                current_position = sum(p.quantity for p in strategy_positions)
            
            # Calculate target position (simplified)
            price = Decimal('100')  # This should come from market data
            target_position = target.target_allocation / price if price > 0 else Decimal('0')
            
            trade_amount = target_position - current_position
            trade_value = trade_amount * price
            
            if abs(trade_value) >= self.min_trade_size:
                action_type = 'buy' if trade_amount > 0 else 'sell'
                
                action = RebalanceAction(
                    symbol=target.symbol,
                    strategy_id=target.strategy_id,
                    action_type=action_type,
                    current_position=current_position,
                    target_position=target_position,
                    trade_amount=trade_amount,
                    trade_value=trade_value,
                    urgency=target.priority
                )
                actions.append(action)
        
        return actions
    
    def _calculate_turnover(self, actions: List[RebalanceAction]) -> Decimal:
        """Calculate portfolio turnover from actions"""
        total_trade_value = sum(abs(action.trade_value) for action in actions)
        total_portfolio_value = self.allocation_engine.total_capital
        
        if total_portfolio_value > 0:
            return total_trade_value / total_portfolio_value
        
        return Decimal('0')
    
    def _reduce_turnover(self, actions: List[RebalanceAction], 
                        current_turnover: Decimal) -> List[RebalanceAction]:
        """Reduce turnover by prioritizing actions"""
        if current_turnover <= self.max_turnover:
            return actions
        
        # Sort by urgency (priority)
        sorted_actions = sorted(actions, key=lambda x: x.urgency)
        
        # Keep adding actions until we hit turnover limit
        reduced_actions = []
        cumulative_turnover = Decimal('0')
        total_portfolio_value = self.allocation_engine.total_capital
        
        for action in sorted_actions:
            action_turnover = abs(action.trade_value) / total_portfolio_value
            
            if cumulative_turnover + action_turnover <= self.max_turnover:
                reduced_actions.append(action)
                cumulative_turnover += action_turnover
            else:
                break
        
        self.logger.info(f"Reduced actions from {len(actions)} to {len(reduced_actions)} "
                        f"to meet turnover limit")
        
        return reduced_actions
    
    def _calculate_execution_cost(self, actions: List[RebalanceAction]) -> Decimal:
        """Calculate estimated execution costs"""
        total_cost = Decimal('0')
        
        for action in actions:
            # Transaction cost
            transaction_cost = abs(action.trade_value) * self.transaction_cost_rate
            
            # Market impact cost (simplified)
            market_impact = abs(action.trade_value) * self.market_impact_factor
            
            total_cost += transaction_cost + market_impact
        
        return total_cost
    
    def _estimate_risk_reduction(self, targets: List[RebalanceTarget]) -> Decimal:
        """Estimate risk reduction from rebalancing"""
        # Simplified risk reduction estimate based on drift reduction
        total_drift_reduction = sum(abs(target.drift) for target in targets)
        return total_drift_reduction * Decimal('0.1')  # Assume 10% conversion to risk reduction
    
    def _execute_rebalance_actions(self, result: RebalanceResult) -> bool:
        """Execute the rebalancing actions (integration with trading system)"""
        try:
            successful_actions = 0
            
            for action in result.actions:
                # This would integrate with the trading system
                # For now, just log the action
                self.logger.info(f"Rebalance action: {action.action_type} "
                                f"{action.trade_amount} of {action.symbol}")
                
                # Simulate successful execution
                successful_actions += 1
            
            return successful_actions == len(result.actions)
            
        except Exception as e:
            self.logger.error(f"Error executing rebalance actions: {e}")
            return False
    
    def _calculate_rebalance_priority(self, drift_info: Dict[str, Any]) -> int:
        """Calculate rebalancing priority"""
        drift_percent = abs(drift_info['drift_percent'])
        
        if drift_percent > 20:
            return 1  # Critical
        elif drift_percent > 15:
            return 2  # High
        elif drift_percent > 10:
            return 3  # Medium
        else:
            return 4  # Low
    
    def _check_time_trigger(self) -> bool:
        """Check if time-based rebalancing is needed"""
        if not self.last_rebalance_time:
            return True
        
        now = datetime.now(timezone.utc)
        time_since_last = now - self.last_rebalance_time
        
        if self.rebalance_frequency == RebalanceFrequency.DAILY:
            return time_since_last >= timedelta(days=1)
        elif self.rebalance_frequency == RebalanceFrequency.WEEKLY:
            return time_since_last >= timedelta(weeks=1)
        elif self.rebalance_frequency == RebalanceFrequency.MONTHLY:
            return time_since_last >= timedelta(days=30)
        elif self.rebalance_frequency == RebalanceFrequency.QUARTERLY:
            return time_since_last >= timedelta(days=90)
        
        return False
    
    def _update_rebalance_tracking(self, result: RebalanceResult):
        """Update rebalancing tracking and metrics"""
        self.rebalance_history.append(result)
        self.last_rebalance_time = result.timestamp
        
        # Update metrics
        self.rebalance_metrics['total_rebalances'] += 1
        
        if result.status == "completed":
            self.rebalance_metrics['successful_rebalances'] += 1
        elif result.status == "failed":
            self.rebalance_metrics['failed_rebalances'] += 1
        
        self.rebalance_metrics['total_turnover'] += result.total_turnover
        self.rebalance_metrics['total_transaction_costs'] += result.execution_cost
        
        # Update average drift reduction
        total_rebalances = self.rebalance_metrics['total_rebalances']
        current_avg = self.rebalance_metrics['average_drift_reduction']
        self.rebalance_metrics['average_drift_reduction'] = (
            (current_avg * (total_rebalances - 1) + result.risk_reduction) / total_rebalances
        )
        
        # Update by type
        rebalance_type = result.rebalance_type.value
        if rebalance_type not in self.rebalance_metrics['rebalances_by_type']:
            self.rebalance_metrics['rebalances_by_type'][rebalance_type] = 0
        self.rebalance_metrics['rebalances_by_type'][rebalance_type] += 1
        
        # Limit history
        if len(self.rebalance_history) > 1000:
            self.rebalance_history = self.rebalance_history[-500:]
    
    def get_rebalance_status(self) -> Dict[str, Any]:
        """Get current rebalancing status"""
        return {
            'last_rebalance': self.last_rebalance_time,
            'rebalance_frequency': self.rebalance_frequency.value,
            'drift_threshold': float(self.drift_threshold),
            'metrics': self.rebalance_metrics.copy(),
            'pending_rebalances': self.check_rebalance_needed(),
            'target_portfolios': {
                strategy: {symbol: float(weight) for symbol, weight in weights.items()}
                for strategy, weights in self.target_portfolios.items()
            }
        }
    
    def cleanup(self):
        """Cleanup rebalancer"""
        self.logger.info(f"Portfolio rebalancer cleaned up. "
                        f"Total rebalances: {self.rebalance_metrics['total_rebalances']}")