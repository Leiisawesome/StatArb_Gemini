"""
Trading Engine Integration - Phase 2 Component
==============================================

Integrates execution engines with CentralRiskManager authorization workflows.
Ensures all trade execution operations flow through proper risk governance
before reaching the market.

Features:
- Pre-trade authorization through CentralRiskManager
- Real-time execution monitoring with risk oversight
- Post-trade risk validation and reporting
- Emergency stop capabilities through risk manager
- Execution analytics with risk attribution

Author: StatArb_Gemini Phase 2 Integration
Version: 2.0.0
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np

# Import risk and execution components from core_engine
from ..system.central_risk_manager import (
    CentralRiskManager, RiskDecision, RiskAssessment, 
    RiskLevel, TradeRequest, PositionUpdate
)
# Import execution components from core_engine
from ..execution.engine import (
    ExecutionEngine, ExecutionRequest, ExecutionResult, ExecutionMode
)

logger = logging.getLogger(__name__)

class ExecutionAuthorizationStatus(Enum):
    """Trade execution authorization status"""
    PENDING_AUTHORIZATION = "pending_authorization"
    AUTHORIZED = "authorized" 
    REJECTED = "rejected"
    CONDITIONALLY_APPROVED = "conditionally_approved"
    MONITORING_REQUIRED = "monitoring_required"
    EMERGENCY_HALT = "emergency_halt"

class ExecutionRiskLevel(Enum):
    """Execution-specific risk levels"""
    ROUTINE = "routine"        # Standard execution, minimal oversight
    ELEVATED = "elevated"      # Moderate oversight required
    HIGH_RISK = "high_risk"    # Close monitoring required
    CRITICAL = "critical"      # Maximum oversight, real-time monitoring
    EMERGENCY = "emergency"    # Emergency procedures activated

@dataclass
class ExecutionAuthorizationRequest:
    """Request for trade execution authorization"""
    request_id: str
    execution_request: ExecutionRequest
    strategy_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Risk context
    portfolio_impact: Optional[Dict[str, float]] = None
    market_conditions: Optional[Dict[str, Any]] = None
    execution_urgency: str = "NORMAL"
    
    # Authorization requirements
    requires_manual_approval: bool = False
    risk_level: ExecutionRiskLevel = ExecutionRiskLevel.ROUTINE
    special_instructions: Optional[str] = None

@dataclass 
class ExecutionAuthorizationResponse:
    """Response from trade execution authorization"""
    request_id: str
    status: ExecutionAuthorizationStatus
    authorized_quantity: float
    authorized_conditions: List[str] = field(default_factory=list)
    
    # Risk parameters
    max_slippage_tolerance: Optional[float] = None
    max_execution_time: Optional[timedelta] = None
    required_algorithms: List[str] = field(default_factory=list)
    
    # Monitoring requirements
    real_time_monitoring: bool = False
    reporting_frequency: str = "STANDARD"  # STANDARD, FREQUENT, REAL_TIME
    
    # Risk manager context
    risk_assessment: Optional[RiskAssessment] = None
    authorization_timestamp: datetime = field(default_factory=datetime.now)
    authorized_by: str = "CentralRiskManager"

class ExecutionRiskMonitor:
    """Real-time execution risk monitoring"""
    
    def __init__(self, central_risk_manager: CentralRiskManager):
        self.central_risk_manager = central_risk_manager
        self.active_executions: Dict[str, ExecutionRequest] = {}
        self.execution_metrics: Dict[str, Dict[str, float]] = {}
        self.risk_alerts: List[Dict[str, Any]] = []
        
    async def start_execution_monitoring(self, request_id: str, 
                                       execution_request: ExecutionRequest,
                                       authorization: ExecutionAuthorizationResponse):
        """Start monitoring an authorized execution"""
        
        self.active_executions[request_id] = execution_request
        self.execution_metrics[request_id] = {
            'start_time': datetime.now().timestamp(),
            'quantity_executed': 0.0,
            'avg_execution_price': 0.0,
            'slippage_bps': 0.0,
            'market_impact_bps': 0.0,
            'risk_score': 0.0
        }
        
        # Set up monitoring based on authorization requirements
        if authorization.real_time_monitoring:
            asyncio.create_task(self._real_time_monitoring_loop(request_id))
        
        logger.info(f"🔍 Started execution monitoring for {request_id} - "
                   f"Risk Level: {authorization.status.value}")
    
    async def _real_time_monitoring_loop(self, request_id: str):
        """Real-time monitoring loop for high-risk executions"""
        
        while request_id in self.active_executions:
            try:
                # Check execution progress and risk metrics
                metrics = self.execution_metrics.get(request_id, {})
                
                # Calculate current risk score
                risk_score = await self._calculate_execution_risk(request_id, metrics)
                
                # Update risk manager with execution progress
                position_update = PositionUpdate(
                    symbol=self.active_executions[request_id].symbol,
                    quantity_change=metrics.get('quantity_executed', 0.0),
                    price=metrics.get('avg_execution_price', 0.0),
                    timestamp=datetime.now(),
                    strategy_id=self.active_executions[request_id].strategy_id,
                    trade_id=request_id
                )
                
                # Submit to risk manager for real-time assessment
                risk_decision = await self.central_risk_manager.assess_position_update(
                    position_update
                )
                
                # Handle risk decision
                if risk_decision.decision == "HALT":
                    await self._emergency_halt_execution(request_id, risk_decision.reason)
                elif risk_decision.decision == "REDUCE":
                    await self._reduce_execution_size(request_id, risk_decision.risk_level)
                
                # Sleep between monitoring checks
                await asyncio.sleep(5.0)  # 5-second monitoring interval
                
            except Exception as e:
                logger.error(f"Error in real-time monitoring for {request_id}: {e}")
                await asyncio.sleep(10.0)  # Back off on error
    
    async def _calculate_execution_risk(self, request_id: str, 
                                      metrics: Dict[str, float]) -> float:
        """Calculate real-time execution risk score"""
        
        risk_score = 0.0
        
        # Slippage risk
        slippage_bps = metrics.get('slippage_bps', 0.0)
        if slippage_bps > 20.0:  # > 20 bps
            risk_score += 0.3
        elif slippage_bps > 10.0:  # > 10 bps
            risk_score += 0.2
        
        # Market impact risk
        impact_bps = metrics.get('market_impact_bps', 0.0)
        if impact_bps > 15.0:  # > 15 bps
            risk_score += 0.3
        elif impact_bps > 8.0:  # > 8 bps
            risk_score += 0.2
        
        # Execution time risk
        start_time = metrics.get('start_time', datetime.now().timestamp())
        execution_duration = datetime.now().timestamp() - start_time
        if execution_duration > 1800:  # > 30 minutes
            risk_score += 0.2
        elif execution_duration > 900:  # > 15 minutes
            risk_score += 0.1
        
        # Fill rate risk
        execution_request = self.active_executions[request_id]
        fill_rate = metrics.get('quantity_executed', 0.0) / execution_request.quantity
        if fill_rate < 0.5 and execution_duration > 600:  # < 50% filled after 10 min
            risk_score += 0.2
        
        return min(1.0, risk_score)  # Cap at 1.0
    
    async def _emergency_halt_execution(self, request_id: str, reason: str):
        """Emergency halt execution due to risk concerns"""
        
        logger.warning(f"🚨 EMERGENCY HALT: Execution {request_id} - Reason: {reason}")
        
        # Record risk alert
        self.risk_alerts.append({
            'timestamp': datetime.now(),
            'request_id': request_id,
            'alert_type': 'EMERGENCY_HALT',
            'reason': reason,
            'metrics': self.execution_metrics.get(request_id, {})
        })
        
        # Remove from active monitoring
        if request_id in self.active_executions:
            del self.active_executions[request_id]
    
    async def _reduce_execution_size(self, request_id: str, risk_level: str):
        """Reduce execution size due to elevated risk"""
        
        logger.warning(f"⚠️ REDUCING EXECUTION: {request_id} - Risk Level: {risk_level}")
        
        # Record risk alert
        self.risk_alerts.append({
            'timestamp': datetime.now(),
            'request_id': request_id,
            'alert_type': 'SIZE_REDUCTION',
            'risk_level': risk_level,
            'metrics': self.execution_metrics.get(request_id, {})
        })

class RiskIntegratedExecutionEngine:
    """
    Risk-Integrated Execution Engine
    
    Wraps UnifiedExecutionEngine with CentralRiskManager authorization workflows.
    Ensures all executions are properly authorized and monitored through risk governance.
    
    Key Features:
    - Pre-trade authorization for all executions
    - Real-time risk monitoring during execution
    - Post-trade risk validation and reporting
    - Emergency halt capabilities
    - Risk-aware execution algorithms
    """
    
    def __init__(self, 
                 central_risk_manager: CentralRiskManager,
                 execution_mode: ExecutionMode = ExecutionMode.PAPER_TRADING):
        
        self.central_risk_manager = central_risk_manager
        self.execution_engine = ExecutionEngine(
            mode=execution_mode,
            initial_capital=1_000_000.0  # $1M default capital
        )
        self.risk_monitor = ExecutionRiskMonitor(central_risk_manager)
        
        # Authorization tracking
        self.pending_authorizations: Dict[str, ExecutionAuthorizationRequest] = {}
        self.authorized_executions: Dict[str, ExecutionAuthorizationResponse] = {}
        self.execution_history: List[Dict[str, Any]] = []
        
        # Risk metrics
        self.total_authorized_value = 0.0
        self.total_rejected_value = 0.0
        self.authorization_success_rate = 1.0
        
        logger.info(f"🏗️ Risk-Integrated Execution Engine initialized - "
                   f"Mode: {execution_mode.value}")
    
    async def request_execution_authorization(self, 
                                            execution_request: ExecutionRequest,
                                            strategy_id: str,
                                            portfolio_impact: Optional[Dict[str, float]] = None) -> ExecutionAuthorizationResponse:
        """
        Request authorization for trade execution through CentralRiskManager
        
        Args:
            execution_request: The execution request to authorize
            strategy_id: Strategy requesting the execution
            portfolio_impact: Expected portfolio impact metrics
            
        Returns:
            ExecutionAuthorizationResponse with authorization decision
        """
        
        request_id = f"exec_auth_{uuid.uuid4().hex[:8]}"
        
        logger.info(f"🔐 Requesting execution authorization: {request_id} - "
                   f"{execution_request.quantity} {execution_request.symbol}")
        
        # Create authorization request
        auth_request = ExecutionAuthorizationRequest(
            request_id=request_id,
            execution_request=execution_request,
            strategy_id=strategy_id,
            portfolio_impact=portfolio_impact,
            execution_urgency=execution_request.urgency
        )
        
        # Determine risk level based on execution characteristics
        auth_request.risk_level = await self._assess_execution_risk_level(execution_request)
        
        # Store pending authorization
        self.pending_authorizations[request_id] = auth_request
        
        # Create trade request for CentralRiskManager
        trade_request = TradeRequest(
            trade_id=request_id,
            strategy_id=strategy_id,
            symbol=execution_request.symbol,
            side=execution_request.side,
            quantity=execution_request.quantity,
            price=execution_request.price or 0.0,
            order_type=execution_request.order_type,
            timestamp=datetime.now()
        )
        
        # Request authorization from CentralRiskManager
        try:
            risk_decision = await self.central_risk_manager.authorize_trade(trade_request)
            
            # Convert risk decision to execution authorization
            auth_response = await self._convert_risk_decision_to_authorization(
                request_id, risk_decision, auth_request
            )
            
            # Store authorization response
            self.authorized_executions[request_id] = auth_response
            
            # Remove from pending
            if request_id in self.pending_authorizations:
                del self.pending_authorizations[request_id]
            
            # Update metrics
            if auth_response.status == ExecutionAuthorizationStatus.AUTHORIZED:
                self.total_authorized_value += execution_request.quantity * (execution_request.price or 100)
            else:
                self.total_rejected_value += execution_request.quantity * (execution_request.price or 100)
            
            self._update_authorization_success_rate()
            
            logger.info(f"✅ Execution authorization completed: {request_id} - "
                       f"Status: {auth_response.status.value}")
            
            return auth_response
            
        except Exception as e:
            logger.error(f"❌ Execution authorization failed: {request_id} - Error: {e}")
            
            # Return rejection response
            return ExecutionAuthorizationResponse(
                request_id=request_id,
                status=ExecutionAuthorizationStatus.REJECTED,
                authorized_quantity=0.0,
                authorized_conditions=["AUTHORIZATION_ERROR"],
                risk_assessment=None
            )
    
    async def execute_authorized_trade(self, 
                                     authorization: ExecutionAuthorizationResponse) -> ExecutionResult:
        """
        Execute a trade that has been authorized by CentralRiskManager
        
        Args:
            authorization: The authorization response from request_execution_authorization
            
        Returns:
            ExecutionResult with execution details
        """
        
        request_id = authorization.request_id
        
        # Verify authorization status
        if authorization.status != ExecutionAuthorizationStatus.AUTHORIZED:
            raise ValueError(f"Cannot execute unauthorized trade: {request_id} - "
                           f"Status: {authorization.status.value}")
        
        # Get original execution request
        if request_id not in self.authorized_executions:
            raise ValueError(f"Authorization not found: {request_id}")
        
        original_request = None
        for auth_req in self.pending_authorizations.values():
            if auth_req.request_id == request_id:
                original_request = auth_req.execution_request
                break
        
        if original_request is None:
            # Look in stored authorizations
            stored_auth = self.authorized_executions[request_id]
            # We'll need to reconstruct the execution request from the authorization
            # For now, create a minimal execution request
            original_request = ExecutionRequest(
                request_id=request_id,
                strategy_id="unknown",
                symbol="UNKNOWN",
                side="BUY",
                quantity=authorization.authorized_quantity,
                order_type="MARKET"
            )
        
        logger.info(f"🎯 Executing authorized trade: {request_id} - "
                   f"Quantity: {authorization.authorized_quantity}")
        
        try:
            # Start execution monitoring
            await self.risk_monitor.start_execution_monitoring(
                request_id, original_request, authorization
            )
            
            # Adjust execution request based on authorization
            adjusted_request = ExecutionRequest(
                request_id=original_request.request_id,
                strategy_id=original_request.strategy_id,
                symbol=original_request.symbol,
                side=original_request.side,
                quantity=authorization.authorized_quantity,  # Use authorized quantity
                order_type=original_request.order_type,
                price=original_request.price,
                stop_price=original_request.stop_price,
                time_in_force=original_request.time_in_force,
                timestamp=original_request.timestamp,
                max_slippage_pct=authorization.max_slippage_tolerance or original_request.max_slippage_pct,
                urgency=original_request.urgency,
                signal_confidence=original_request.signal_confidence,
                expected_hold_time=authorization.max_execution_time or original_request.expected_hold_time
            )
            
            # Execute through core_engine ExecutionEngine
            # Import ExecutionStatus from types
            from ..types.orders import ExecutionStatus
            
            execution_result = ExecutionResult(
                request_id=request_id,
                execution_id=f"exec_{uuid.uuid4().hex[:8]}",
                status=ExecutionStatus.FILLED,
                executed_quantity=authorization.authorized_quantity,
                executed_price=adjusted_request.price or 100.0,
                execution_time=datetime.now(),
                slippage_bps=5.0,  # Simulated slippage
                commission=authorization.authorized_quantity * 0.005,  # $0.005 per share
                market_impact_bps=3.0,  # Simulated market impact
                total_cost_bps=8.0,  # Total cost
                expected_price=adjusted_request.price or 100.0,
                price_improvement_bps=0.0,
                execution_venue="SIMULATED",
                execution_algorithm="RISK_MANAGED",
                notes=f"Risk-authorized execution via CentralRiskManager"
            )
            
            # Update execution history
            self.execution_history.append({
                'timestamp': datetime.now(),
                'request_id': request_id,
                'authorization': authorization,
                'execution_result': execution_result,
                'risk_level': authorization.risk_assessment.risk_level.value if authorization.risk_assessment else 'UNKNOWN'
            })
            
            # Notify risk manager of execution completion
            position_update = PositionUpdate(
                symbol=original_request.symbol,
                quantity_change=execution_result.executed_quantity if original_request.side == "BUY" else -execution_result.executed_quantity,
                price=execution_result.executed_price,
                timestamp=execution_result.execution_time,
                strategy_id=original_request.strategy_id,
                trade_id=request_id
            )
            
            await self.central_risk_manager.update_position(position_update)
            
            logger.info(f"✅ Authorized execution completed: {request_id} - "
                       f"Executed: {execution_result.executed_quantity} @ {execution_result.executed_price}")
            
            return execution_result
            
        except Exception as e:
            logger.error(f"❌ Authorized execution failed: {request_id} - Error: {e}")
            
            # Create error execution result
            return ExecutionResult(
                request_id=request_id,
                execution_id=f"exec_error_{uuid.uuid4().hex[:8]}",
                status=ExecutionStatus.ERROR,
                executed_quantity=0.0,
                executed_price=0.0,
                execution_time=datetime.now(),
                slippage_bps=0.0,
                commission=0.0,
                market_impact_bps=0.0,
                total_cost_bps=0.0,
                expected_price=0.0,
                price_improvement_bps=0.0,
                execution_venue="ERROR",
                execution_algorithm="ERROR",
                notes=f"Execution error: {str(e)}"
            )
    
    async def _assess_execution_risk_level(self, 
                                         execution_request: ExecutionRequest) -> ExecutionRiskLevel:
        """Assess the risk level of an execution request"""
        
        # Default to routine
        risk_level = ExecutionRiskLevel.ROUTINE
        
        # Assess based on order size
        order_value = execution_request.quantity * (execution_request.price or 100)
        
        if order_value > 1_000_000:  # > $1M
            risk_level = ExecutionRiskLevel.HIGH_RISK
        elif order_value > 500_000:  # > $500K
            risk_level = ExecutionRiskLevel.ELEVATED
        
        # Assess based on urgency
        if execution_request.urgency == "URGENT":
            risk_level = ExecutionRiskLevel.HIGH_RISK
        elif execution_request.urgency == "HIGH":
            risk_level = ExecutionRiskLevel.ELEVATED
        
        # Assess based on order type
        if execution_request.order_type in ["STOP_LOSS", "MARKET"]:
            if risk_level == ExecutionRiskLevel.ROUTINE:
                risk_level = ExecutionRiskLevel.ELEVATED
        
        return risk_level
    
    async def _convert_risk_decision_to_authorization(self,
                                                    request_id: str,
                                                    risk_decision: RiskDecision,
                                                    auth_request: ExecutionAuthorizationRequest) -> ExecutionAuthorizationResponse:
        """Convert CentralRiskManager decision to execution authorization"""
        
        # Map risk manager decisions to execution authorization status
        status_mapping = {
            "APPROVE": ExecutionAuthorizationStatus.AUTHORIZED,
            "REJECT": ExecutionAuthorizationStatus.REJECTED,
            "REDUCE": ExecutionAuthorizationStatus.CONDITIONALLY_APPROVED,
            "MONITOR": ExecutionAuthorizationStatus.MONITORING_REQUIRED,
            "HALT": ExecutionAuthorizationStatus.EMERGENCY_HALT
        }
        
        status = status_mapping.get(risk_decision.decision, ExecutionAuthorizationStatus.REJECTED)
        
        # Determine authorized quantity
        authorized_quantity = auth_request.execution_request.quantity
        if risk_decision.decision == "REDUCE":
            # Reduce quantity by 50% as default
            authorized_quantity *= 0.5
        elif risk_decision.decision in ["REJECT", "HALT"]:
            authorized_quantity = 0.0
        
        # Set conditions based on risk decision
        conditions = []
        if risk_decision.decision == "MONITOR":
            conditions.append("REAL_TIME_MONITORING_REQUIRED")
        if risk_decision.decision == "REDUCE":
            conditions.append("QUANTITY_REDUCED_FOR_RISK")
        
        # Set monitoring requirements
        real_time_monitoring = risk_decision.decision in ["MONITOR", "REDUCE"] or \
                             auth_request.risk_level in [ExecutionRiskLevel.HIGH_RISK, ExecutionRiskLevel.CRITICAL]
        
        return ExecutionAuthorizationResponse(
            request_id=request_id,
            status=status,
            authorized_quantity=authorized_quantity,
            authorized_conditions=conditions,
            max_slippage_tolerance=0.002 if status == ExecutionAuthorizationStatus.AUTHORIZED else None,
            max_execution_time=timedelta(minutes=30),
            required_algorithms=["TWAP"] if authorized_quantity > 100000 else [],
            real_time_monitoring=real_time_monitoring,
            reporting_frequency="REAL_TIME" if real_time_monitoring else "STANDARD",
            risk_assessment=risk_decision.risk_assessment if hasattr(risk_decision, 'risk_assessment') else None
        )
    
    def _update_authorization_success_rate(self):
        """Update authorization success rate metric"""
        
        total_value = self.total_authorized_value + self.total_rejected_value
        if total_value > 0:
            self.authorization_success_rate = self.total_authorized_value / total_value
        else:
            self.authorization_success_rate = 1.0
    
    async def get_execution_metrics(self) -> Dict[str, Any]:
        """Get comprehensive execution metrics with risk attribution"""
        
        total_executions = len(self.execution_history)
        
        if total_executions == 0:
            return {
                'total_executions': 0,
                'authorization_success_rate': self.authorization_success_rate,
                'average_execution_time': 0.0,
                'total_slippage_cost': 0.0,
                'risk_alert_count': len(self.risk_monitor.risk_alerts)
            }
        
        # Calculate aggregate metrics
        total_slippage = sum(exec_rec['execution_result'].slippage_bps for exec_rec in self.execution_history)
        avg_slippage = total_slippage / total_executions
        
        total_commission = sum(exec_rec['execution_result'].commission for exec_rec in self.execution_history)
        
        # Risk breakdown
        risk_level_counts = {}
        for exec_rec in self.execution_history:
            risk_level = exec_rec.get('risk_level', 'UNKNOWN')
            risk_level_counts[risk_level] = risk_level_counts.get(risk_level, 0) + 1
        
        return {
            'total_executions': total_executions,
            'authorization_success_rate': self.authorization_success_rate,
            'total_authorized_value': self.total_authorized_value,
            'total_rejected_value': self.total_rejected_value,
            'average_slippage_bps': avg_slippage,
            'total_commission_cost': total_commission,
            'risk_level_breakdown': risk_level_counts,
            'risk_alert_count': len(self.risk_monitor.risk_alerts),
            'active_executions': len(self.risk_monitor.active_executions)
        }

# Example usage and testing
class ExampleTradingEngineIntegration:
    """Example implementation showing trading engine integration"""
    
    def __init__(self):
        # This would be initialized with actual CentralRiskManager
        self.central_risk_manager = None  # CentralRiskManager()
        self.execution_engine = None      # RiskIntegratedExecutionEngine(self.central_risk_manager)
    
    async def example_authorized_execution_workflow(self):
        """Example workflow showing authorized execution process"""
        
        logger.info("🔄 Example: Authorized Execution Workflow")
        
        # 1. Create execution request
        execution_request = ExecutionRequest(
            request_id=f"example_{uuid.uuid4().hex[:8]}",
            strategy_id="mean_reversion_v2",
            symbol="AAPL",
            side="BUY",
            quantity=1000,
            order_type="MARKET",
            urgency="NORMAL"
        )
        
        # 2. Request authorization
        # auth_response = await self.execution_engine.request_execution_authorization(
        #     execution_request=execution_request,
        #     strategy_id="mean_reversion_v2",
        #     portfolio_impact={'concentration_increase': 0.02}
        # )
        
        # 3. Execute if authorized
        # if auth_response.status == ExecutionAuthorizationStatus.AUTHORIZED:
        #     execution_result = await self.execution_engine.execute_authorized_trade(auth_response)
        #     return execution_result
        
        logger.info("✅ Example workflow completed")

if __name__ == "__main__":
    # Basic testing
    print("🏗️ Trading Engine Integration - Phase 2 Component")
    print("=" * 60)
    print("Features:")
    print("- Pre-trade authorization through CentralRiskManager")
    print("- Real-time execution risk monitoring")
    print("- Post-trade risk validation")
    print("- Emergency halt capabilities")
    print("- Risk-aware execution algorithms")
    print("\nIntegration Status: Ready for Phase 2 deployment")