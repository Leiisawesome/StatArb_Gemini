"""
Rollback management for parameter adaptations.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging
import json
from .adaptation_metrics import PerformanceSnapshot, AdaptationMetrics


@dataclass
class AdaptationSnapshot:
    """Snapshot of system state before parameter adaptation."""
    
    snapshot_id: str
    strategy_id: str
    timestamp: datetime
    
    # Parameter state
    parameters_before: Dict[str, Any]
    parameters_after: Dict[str, Any]
    
    # Performance state
    performance_before: PerformanceSnapshot
    
    # Market conditions
    market_conditions: Dict[str, float]
    
    # Adaptation metadata
    adaptation_reason: str
    adaptation_confidence: float
    expected_improvement: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert snapshot to dictionary for serialization."""
        return {
            'snapshot_id': self.snapshot_id,
            'strategy_id': self.strategy_id,
            'timestamp': self.timestamp.isoformat(),
            'parameters_before': self.parameters_before,
            'parameters_after': self.parameters_after,
            'performance_before': {
                'sharpe_ratio': self.performance_before.sharpe_ratio,
                'max_drawdown': self.performance_before.max_drawdown,
                'win_rate': self.performance_before.win_rate,
                'total_trades': self.performance_before.total_trades
            },
            'market_conditions': self.market_conditions,
            'adaptation_reason': self.adaptation_reason,
            'adaptation_confidence': self.adaptation_confidence,
            'expected_improvement': self.expected_improvement
        }


@dataclass
class RollbackDecision:
    """Decision result for parameter rollback."""
    
    should_rollback: bool
    confidence: float
    reason: str
    rollback_parameters: Dict[str, Any] = None
    performance_comparison: Dict[str, float] = None
    
    def __str__(self) -> str:
        action = "ROLLBACK" if self.should_rollback else "CONTINUE"
        return f"RollbackDecision({action}, confidence={self.confidence:.2f}, reason='{self.reason}')"


@dataclass 
class RollbackResult:
    """Result of rollback execution."""
    
    success: bool
    snapshot_id: str
    parameters_restored: Dict[str, Any]
    timestamp: datetime
    error_message: Optional[str] = None
    
    def __str__(self) -> str:
        status = "SUCCESS" if self.success else "FAILED"
        return f"RollbackResult({status}, snapshot={self.snapshot_id})"


class AdaptationRollbackManager:
    """Manages parameter adaptation rollback based on performance monitoring."""
    
    def __init__(self, strategy_id: str):
        self.strategy_id = strategy_id
        self.logger = logging.getLogger(__name__)
        
        # Storage for snapshots and decisions
        self.adaptation_snapshots: Dict[str, AdaptationSnapshot] = {}
        self.rollback_history: List[RollbackResult] = []
        
        # Configuration
        self.monitoring_window_trades = 50
        self.performance_degradation_threshold = -0.20  # 20% degradation
        self.min_monitoring_period_hours = 2
        
    def create_adaptation_snapshot(self,
                                 parameters_before: Dict[str, Any],
                                 parameters_after: Dict[str, Any],
                                 performance_before: PerformanceSnapshot,
                                 market_conditions: Dict[str, float],
                                 adaptation_reason: str,
                                 adaptation_confidence: float = 0.5,
                                 expected_improvement: float = 0.1) -> str:
        """
        Create snapshot before parameter adaptation.
        
        Args:
            parameters_before: Parameter values before adaptation
            parameters_after: Parameter values after adaptation
            performance_before: Performance snapshot before adaptation
            market_conditions: Current market conditions
            adaptation_reason: Reason for adaptation
            adaptation_confidence: Confidence in adaptation (0-1)
            expected_improvement: Expected performance improvement
            
        Returns:
            Snapshot ID for later reference
        """
        snapshot_id = f"snapshot_{self.strategy_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        snapshot = AdaptationSnapshot(
            snapshot_id=snapshot_id,
            strategy_id=self.strategy_id,
            timestamp=datetime.now(),
            parameters_before=parameters_before.copy(),
            parameters_after=parameters_after.copy(),
            performance_before=performance_before,
            market_conditions=market_conditions.copy(),
            adaptation_reason=adaptation_reason,
            adaptation_confidence=adaptation_confidence,
            expected_improvement=expected_improvement
        )
        
        self.adaptation_snapshots[snapshot_id] = snapshot
        
        self.logger.info(f"Created adaptation snapshot {snapshot_id} for strategy {self.strategy_id}")
        self.logger.debug(f"Snapshot details: {snapshot.to_dict()}")
        
        return snapshot_id
    
    def evaluate_rollback_decision(self,
                                 snapshot_id: str,
                                 current_performance: PerformanceSnapshot,
                                 current_market_conditions: Dict[str, float]) -> RollbackDecision:
        """
        Evaluate whether to rollback based on performance since adaptation.
        
        Args:
            snapshot_id: ID of adaptation snapshot
            current_performance: Current performance snapshot
            current_market_conditions: Current market conditions
            
        Returns:
            RollbackDecision with recommendation
        """
        if snapshot_id not in self.adaptation_snapshots:
            return RollbackDecision(
                should_rollback=False,
                confidence=0.0,
                reason=f"Snapshot {snapshot_id} not found"
            )
        
        snapshot = self.adaptation_snapshots[snapshot_id]
        
        # Check minimum monitoring period
        time_since_adaptation = datetime.now() - snapshot.timestamp
        if time_since_adaptation < timedelta(hours=self.min_monitoring_period_hours):
            return RollbackDecision(
                should_rollback=False,
                confidence=0.0,
                reason=f"Insufficient monitoring time: {time_since_adaptation}"
            )
        
        # Check minimum trades for evaluation
        trades_since_adaptation = current_performance.total_trades - snapshot.performance_before.total_trades
        if trades_since_adaptation < self.monitoring_window_trades:
            return RollbackDecision(
                should_rollback=False,
                confidence=0.2,
                reason=f"Insufficient trades for evaluation: {trades_since_adaptation}"
            )
        
        # Calculate performance comparison
        performance_comparison = self._calculate_performance_change(
            snapshot.performance_before,
            current_performance
        )
        
        # Evaluate rollback criteria
        rollback_score = self._calculate_rollback_score(
            snapshot,
            performance_comparison,
            current_market_conditions
        )
        
        # Make rollback decision
        should_rollback = rollback_score > 0.6  # 60% confidence threshold
        reason = self._generate_rollback_reason(rollback_score, performance_comparison)
        
        decision = RollbackDecision(
            should_rollback=should_rollback,
            confidence=rollback_score,
            reason=reason,
            rollback_parameters=snapshot.parameters_before if should_rollback else None,
            performance_comparison=performance_comparison
        )
        
        self.logger.info(f"Rollback evaluation for {snapshot_id}: {decision}")
        
        return decision
    
    async def execute_rollback(self, 
                             snapshot_id: str,
                             parameter_setter_callback) -> RollbackResult:
        """
        Execute parameter rollback to snapshot state.
        
        Args:
            snapshot_id: ID of snapshot to rollback to
            parameter_setter_callback: Async function to set parameters
            
        Returns:
            RollbackResult with execution status
        """
        if snapshot_id not in self.adaptation_snapshots:
            return RollbackResult(
                success=False,
                snapshot_id=snapshot_id,
                parameters_restored={},
                timestamp=datetime.now(),
                error_message=f"Snapshot {snapshot_id} not found"
            )
        
        snapshot = self.adaptation_snapshots[snapshot_id]
        
        try:
            # Execute parameter rollback via callback
            await parameter_setter_callback(snapshot.parameters_before)
            
            result = RollbackResult(
                success=True,
                snapshot_id=snapshot_id,
                parameters_restored=snapshot.parameters_before.copy(),
                timestamp=datetime.now()
            )
            
            self.rollback_history.append(result)
            
            self.logger.info(f"Successfully executed rollback for {snapshot_id}")
            self.logger.info(f"Restored parameters: {snapshot.parameters_before}")
            
            return result
            
        except Exception as e:
            error_msg = f"Failed to execute rollback: {str(e)}"
            self.logger.error(error_msg)
            
            return RollbackResult(
                success=False,
                snapshot_id=snapshot_id,
                parameters_restored={},
                timestamp=datetime.now(),
                error_message=error_msg
            )
    
    def get_rollback_history(self) -> List[RollbackResult]:
        """Get history of rollback executions."""
        return self.rollback_history.copy()
    
    def cleanup_old_snapshots(self, max_age_days: int = 30) -> int:
        """
        Clean up old snapshots beyond retention period.
        
        Args:
            max_age_days: Maximum age of snapshots to keep
            
        Returns:
            Number of snapshots cleaned up
        """
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        
        old_snapshots = [
            snapshot_id for snapshot_id, snapshot in self.adaptation_snapshots.items()
            if snapshot.timestamp < cutoff_date
        ]
        
        for snapshot_id in old_snapshots:
            del self.adaptation_snapshots[snapshot_id]
        
        if old_snapshots:
            self.logger.info(f"Cleaned up {len(old_snapshots)} old snapshots")
        
        return len(old_snapshots)
    
    def _calculate_performance_change(self,
                                    before: PerformanceSnapshot,
                                    after: PerformanceSnapshot) -> Dict[str, float]:
        """Calculate performance changes between snapshots."""
        return {
            'sharpe_change': after.sharpe_ratio - before.sharpe_ratio,
            'return_change_pct': ((after.total_return - before.total_return) / 
                                abs(before.total_return) if before.total_return != 0 else 0),
            'drawdown_change': after.max_drawdown - before.max_drawdown,
            'win_rate_change': after.win_rate - before.win_rate,
            'profit_factor_change': after.profit_factor - before.profit_factor,
            'volatility_change': after.volatility - before.volatility,
            'trades_added': after.total_trades - before.total_trades
        }
    
    def _calculate_rollback_score(self,
                                snapshot: AdaptationSnapshot,
                                performance_comparison: Dict[str, float],
                                current_market_conditions: Dict[str, float]) -> float:
        """
        Calculate rollback confidence score (0-1).
        
        Higher score means higher confidence that rollback is needed.
        """
        score_components = {}
        
        # Performance degradation component (0-0.4)
        sharpe_degradation = max(0, -performance_comparison['sharpe_change']) / 2.0
        drawdown_increase = max(0, performance_comparison['drawdown_change']) * 2.0
        win_rate_decline = max(0, -performance_comparison['win_rate_change']) * 2.0
        
        score_components['performance'] = min(0.4, (sharpe_degradation + drawdown_increase + win_rate_decline) / 3)
        
        # Expectation vs reality component (0-0.3)
        expected = snapshot.expected_improvement
        actual = performance_comparison.get('return_change_pct', 0)
        expectation_miss = max(0, expected - actual) / expected if expected > 0 else 0
        score_components['expectation'] = min(0.3, expectation_miss)
        
        # Adaptation confidence discount (0-0.2)
        # Lower confidence adaptations more likely to be rolled back
        confidence_discount = (1.0 - snapshot.adaptation_confidence) * 0.2
        score_components['confidence'] = confidence_discount
        
        # Market condition change component (0-0.1)
        # If market conditions changed significantly, adaptation may be less valid
        market_change = self._calculate_market_condition_change(
            snapshot.market_conditions, 
            current_market_conditions
        )
        score_components['market'] = min(0.1, market_change)
        
        total_score = sum(score_components.values())
        
        self.logger.debug(f"Rollback score components: {score_components}, total: {total_score:.3f}")
        
        return min(1.0, total_score)
    
    def _calculate_market_condition_change(self,
                                         before: Dict[str, float],
                                         after: Dict[str, float]) -> float:
        """Calculate market condition change score."""
        if not before or not after:
            return 0.0
        
        # Compare common market indicators
        common_keys = set(before.keys()) & set(after.keys())
        if not common_keys:
            return 0.0
        
        changes = []
        for key in common_keys:
            if before[key] != 0:
                relative_change = abs(after[key] - before[key]) / abs(before[key])
                changes.append(relative_change)
        
        return sum(changes) / len(changes) if changes else 0.0
    
    def _generate_rollback_reason(self,
                                score: float,
                                performance_comparison: Dict[str, float]) -> str:
        """Generate human-readable reason for rollback decision."""
        if score <= 0.3:
            return "Performance stable, no rollback needed"
        elif score <= 0.6:
            return "Minor performance concerns, monitoring continues"
        else:
            reasons = []
            
            if performance_comparison['sharpe_change'] < -0.5:
                reasons.append("significant Sharpe ratio decline")
            
            if performance_comparison['drawdown_change'] > 0.05:
                reasons.append("increased drawdown")
            
            if performance_comparison['win_rate_change'] < -0.1:
                reasons.append("declining win rate")
            
            if not reasons:
                reasons.append("overall performance degradation")
            
            return f"Performance degradation detected: {', '.join(reasons)}"
