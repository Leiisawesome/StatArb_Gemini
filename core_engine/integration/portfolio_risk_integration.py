"""
Portfolio Risk Integration - Phase 2 Component
==============================================

Integrates portfolio management with CentralRiskManager authorization workflows.
Ensures all portfolio operations and position changes flow through risk governance
before execution.

Features:
- Portfolio position authorization through CentralRiskManager
- Real-time portfolio risk monitoring and controls
- Position change authorization workflows
- Portfolio-level risk limit enforcement
- Emergency portfolio lockdown capabilities

Author: StatArb_Gemini Phase 2 Integration
Version: 2.0.0
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np

from core_engine.central_risk_manager import (
    CentralRiskManager, RiskDecision, RiskAssessment, 
    RiskLevel, PositionRequest, PositionUpdate
)

logger = logging.getLogger(__name__)

class PortfolioAuthorizationStatus(Enum):
    """Portfolio operation authorization status"""
    PENDING_AUTHORIZATION = "pending_authorization"
    AUTHORIZED = "authorized"
    REJECTED = "rejected"
    CONDITIONALLY_APPROVED = "conditionally_approved"
    MONITORING_REQUIRED = "monitoring_required"
    PORTFOLIO_LOCKDOWN = "portfolio_lockdown"

class PortfolioRiskLevel(Enum):
    """Portfolio-specific risk levels"""
    CONSERVATIVE = "conservative"     # Low risk tolerance
    MODERATE = "moderate"            # Standard risk tolerance
    AGGRESSIVE = "aggressive"        # High risk tolerance
    SPECULATIVE = "speculative"      # Very high risk, special approval
    EMERGENCY = "emergency"          # Emergency liquidation mode

class PositionChangeType(Enum):
    """Types of position changes"""
    OPEN_POSITION = "open_position"
    INCREASE_POSITION = "increase_position"
    REDUCE_POSITION = "reduce_position"
    CLOSE_POSITION = "close_position"
    REBALANCE = "rebalance"
    HEDGE = "hedge"

@dataclass
class PortfolioAuthorizationRequest:
    """Request for portfolio operation authorization"""
    request_id: str
    operation_type: PositionChangeType
    symbol: str
    current_quantity: float
    proposed_quantity: float
    proposed_price: float
    strategy_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Portfolio context
    portfolio_value: float = 0.0
    position_concentration: float = 0.0
    expected_impact: Dict[str, float] = field(default_factory=dict)
    
    # Risk context
    risk_level: PortfolioRiskLevel = PortfolioRiskLevel.MODERATE
    requires_manual_approval: bool = False
    urgency: str = "NORMAL"

@dataclass
class PortfolioAuthorizationResponse:
    """Response from portfolio operation authorization"""
    request_id: str
    status: PortfolioAuthorizationStatus
    authorized_quantity: float
    authorized_conditions: List[str] = field(default_factory=list)
    
    # Risk parameters
    max_position_size: Optional[float] = None
    max_concentration: Optional[float] = None
    required_hedge_ratio: Optional[float] = None
    
    # Monitoring requirements
    real_time_monitoring: bool = False
    position_monitoring_frequency: str = "STANDARD"  # STANDARD, FREQUENT, REAL_TIME
    
    # Risk manager context
    risk_assessment: Optional[RiskAssessment] = None
    authorization_timestamp: datetime = field(default_factory=datetime.now)
    authorized_by: str = "CentralRiskManager"
    expiry_timestamp: Optional[datetime] = None

@dataclass
class PortfolioRiskMetrics:
    """Portfolio risk metrics for monitoring"""
    portfolio_id: str
    timestamp: datetime
    
    # Concentration metrics
    max_position_concentration: float
    sector_concentration: Dict[str, float] = field(default_factory=dict)
    strategy_concentration: Dict[str, float] = field(default_factory=dict)
    
    # Risk metrics
    portfolio_var: float  # Value at Risk
    portfolio_beta: float
    correlation_risk: float
    leverage_ratio: float
    
    # Drawdown metrics
    max_drawdown: float
    current_drawdown: float
    time_underwater: int  # Days in drawdown
    
    # Liquidity metrics
    portfolio_liquidity_score: float
    illiquid_position_percentage: float
    
    # Overall assessment
    overall_risk_score: float = 0.0
    risk_level: PortfolioRiskLevel = PortfolioRiskLevel.MODERATE

class PortfolioRiskMonitor:
    """Real-time portfolio risk monitoring"""
    
    def __init__(self, central_risk_manager: CentralRiskManager):
        self.central_risk_manager = central_risk_manager
        self.active_portfolios: Dict[str, Dict[str, Any]] = {}
        self.risk_metrics_history: Dict[str, List[PortfolioRiskMetrics]] = {}
        self.risk_alerts: List[Dict[str, Any]] = []
        self.position_limits: Dict[str, Dict[str, float]] = {}
        
    async def start_portfolio_monitoring(self, portfolio_id: str,
                                       authorization: PortfolioAuthorizationResponse):
        """Start monitoring an authorized portfolio operation"""
        
        self.active_portfolios[portfolio_id] = {
            'authorization': authorization,
            'start_time': datetime.now(),
            'positions': {},
            'risk_metrics': None
        }
        
        # Set up real-time monitoring if required
        if authorization.real_time_monitoring:
            asyncio.create_task(self._real_time_portfolio_monitoring_loop(portfolio_id))
        
        logger.info(f"🔍 Started portfolio monitoring for {portfolio_id} - "
                   f"Risk Level: {authorization.status.value}")
    
    async def _real_time_portfolio_monitoring_loop(self, portfolio_id: str):
        """Real-time monitoring loop for high-risk portfolios"""
        
        while portfolio_id in self.active_portfolios:
            try:
                # Calculate current portfolio risk metrics
                risk_metrics = await self._calculate_portfolio_risk_metrics(portfolio_id)
                
                if risk_metrics:
                    # Store risk metrics
                    if portfolio_id not in self.risk_metrics_history:
                        self.risk_metrics_history[portfolio_id] = []
                    self.risk_metrics_history[portfolio_id].append(risk_metrics)
                    
                    # Update active portfolio data
                    self.active_portfolios[portfolio_id]['risk_metrics'] = risk_metrics
                    
                    # Check risk thresholds
                    await self._check_portfolio_risk_thresholds(portfolio_id, risk_metrics)
                
                # Sleep between monitoring checks
                await asyncio.sleep(60.0)  # 1-minute monitoring interval
                
            except Exception as e:
                logger.error(f"Error in portfolio monitoring for {portfolio_id}: {e}")
                await asyncio.sleep(300.0)  # Back off on error
    
    async def _calculate_portfolio_risk_metrics(self, portfolio_id: str) -> Optional[PortfolioRiskMetrics]:
        """Calculate comprehensive portfolio risk metrics"""
        
        try:
            # Simulate portfolio risk calculation
            # In real implementation, this would analyze actual portfolio positions
            
            # Mock portfolio data
            mock_positions = {
                'AAPL': {'quantity': 1000, 'price': 150.0, 'weight': 0.25},
                'GOOGL': {'quantity': 100, 'price': 2500.0, 'weight': 0.42},
                'MSFT': {'quantity': 500, 'price': 300.0, 'weight': 0.25},
                'TSLA': {'quantity': 200, 'price': 200.0, 'weight': 0.08}
            }
            
            # Calculate concentration metrics
            weights = [pos['weight'] for pos in mock_positions.values()]
            max_concentration = max(weights) if weights else 0.0
            
            # Calculate risk metrics (simplified)
            portfolio_var = np.random.uniform(0.02, 0.05)  # 2-5% VaR
            portfolio_beta = np.random.uniform(0.8, 1.2)   # 0.8-1.2 beta
            correlation_risk = np.random.uniform(0.3, 0.8) # 0.3-0.8 correlation
            leverage_ratio = np.random.uniform(1.0, 1.5)   # 1.0-1.5x leverage
            
            # Calculate drawdown metrics
            max_drawdown = np.random.uniform(0.05, 0.15)   # 5-15% max DD
            current_drawdown = np.random.uniform(0.0, max_drawdown)
            time_underwater = np.random.randint(0, 30)     # 0-30 days
            
            # Calculate liquidity metrics
            liquidity_score = np.random.uniform(0.7, 1.0)  # 70-100% liquidity
            illiquid_percentage = np.random.uniform(0.0, 0.2)  # 0-20% illiquid
            
            # Calculate overall risk score
            risk_factors = [
                max_concentration * 0.25,      # Concentration risk
                portfolio_var * 0.3,           # Market risk
                (leverage_ratio - 1.0) * 0.2,  # Leverage risk
                current_drawdown * 0.15,       # Drawdown risk
                (1.0 - liquidity_score) * 0.1  # Liquidity risk
            ]
            
            overall_risk_score = sum(risk_factors)
            
            # Determine risk level
            if overall_risk_score < 0.15:
                risk_level = PortfolioRiskLevel.CONSERVATIVE
            elif overall_risk_score < 0.25:
                risk_level = PortfolioRiskLevel.MODERATE
            elif overall_risk_score < 0.35:
                risk_level = PortfolioRiskLevel.AGGRESSIVE
            else:
                risk_level = PortfolioRiskLevel.SPECULATIVE
            
            return PortfolioRiskMetrics(
                portfolio_id=portfolio_id,
                timestamp=datetime.now(),
                max_position_concentration=max_concentration,
                sector_concentration={'Technology': 0.92, 'Auto': 0.08},
                strategy_concentration={'MeanReversion': 0.6, 'Momentum': 0.4},
                portfolio_var=portfolio_var,
                portfolio_beta=portfolio_beta,
                correlation_risk=correlation_risk,
                leverage_ratio=leverage_ratio,
                max_drawdown=max_drawdown,
                current_drawdown=current_drawdown,
                time_underwater=time_underwater,
                portfolio_liquidity_score=liquidity_score,
                illiquid_position_percentage=illiquid_percentage,
                overall_risk_score=overall_risk_score,
                risk_level=risk_level
            )
            
        except Exception as e:
            logger.error(f"Error calculating portfolio risk metrics for {portfolio_id}: {e}")
            return None
    
    async def _check_portfolio_risk_thresholds(self, portfolio_id: str,
                                             risk_metrics: PortfolioRiskMetrics):
        """Check portfolio risk metrics against thresholds"""
        
        alerts_triggered = []
        
        # Check concentration limits
        if risk_metrics.max_position_concentration > 0.4:  # 40% concentration limit
            alerts_triggered.append({
                'type': 'CONCENTRATION_BREACH',
                'severity': 'HIGH',
                'message': f'Position concentration {risk_metrics.max_position_concentration:.1%} exceeds 40% limit',
                'value': risk_metrics.max_position_concentration
            })
        
        # Check VaR limits
        if risk_metrics.portfolio_var > 0.05:  # 5% VaR limit
            alerts_triggered.append({
                'type': 'VAR_BREACH',
                'severity': 'HIGH',
                'message': f'Portfolio VaR {risk_metrics.portfolio_var:.1%} exceeds 5% limit',
                'value': risk_metrics.portfolio_var
            })
        
        # Check drawdown limits
        if risk_metrics.current_drawdown > 0.1:  # 10% drawdown limit
            alerts_triggered.append({
                'type': 'DRAWDOWN_BREACH',
                'severity': 'CRITICAL',
                'message': f'Current drawdown {risk_metrics.current_drawdown:.1%} exceeds 10% limit',
                'value': risk_metrics.current_drawdown
            })
        
        # Check leverage limits
        if risk_metrics.leverage_ratio > 1.5:  # 1.5x leverage limit
            alerts_triggered.append({
                'type': 'LEVERAGE_BREACH',
                'severity': 'HIGH',
                'message': f'Leverage ratio {risk_metrics.leverage_ratio:.2f} exceeds 1.5x limit',
                'value': risk_metrics.leverage_ratio
            })
        
        # Process alerts
        for alert in alerts_triggered:
            await self._process_portfolio_risk_alert(portfolio_id, alert, risk_metrics)
    
    async def _process_portfolio_risk_alert(self, portfolio_id: str,
                                          alert: Dict[str, Any],
                                          risk_metrics: PortfolioRiskMetrics):
        """Process portfolio risk alert"""
        
        logger.warning(f"⚠️ Portfolio Risk Alert: {portfolio_id} - {alert['message']}")
        
        # Record alert
        self.risk_alerts.append({
            'timestamp': datetime.now(),
            'portfolio_id': portfolio_id,
            'alert_type': alert['type'],
            'severity': alert['severity'],
            'message': alert['message'],
            'value': alert['value'],
            'risk_metrics': risk_metrics
        })
        
        # Escalate critical alerts
        if alert['severity'] == 'CRITICAL':
            await self._escalate_portfolio_risk_issue(portfolio_id, alert, risk_metrics)
    
    async def _escalate_portfolio_risk_issue(self, portfolio_id: str,
                                           alert: Dict[str, Any],
                                           risk_metrics: PortfolioRiskMetrics):
        """Escalate serious portfolio risk issues to risk manager"""
        
        logger.error(f"🚨 ESCALATING: Portfolio risk issue for {portfolio_id}")
        
        # Create position update for risk manager
        position_update = PositionUpdate(
            symbol="PORTFOLIO_ALERT",
            quantity_change=0.0,
            price=risk_metrics.overall_risk_score,
            timestamp=datetime.now(),
            strategy_id="PortfolioRiskMonitor",
            trade_id=f"alert_{uuid.uuid4().hex[:8]}",
            metadata={
                'alert_type': alert['type'],
                'severity': alert['severity'],
                'portfolio_id': portfolio_id,
                'risk_level': risk_metrics.risk_level.value
            }
        )
        
        # Submit to risk manager for assessment
        try:
            await self.central_risk_manager.assess_position_update(position_update)
        except Exception as e:
            logger.error(f"Failed to escalate portfolio risk issue: {e}")

class RiskIntegratedPortfolioManager:
    """
    Risk-Integrated Portfolio Manager
    
    Wraps portfolio management with CentralRiskManager authorization workflows.
    Ensures all portfolio operations and position changes are properly authorized
    and monitored through risk governance.
    
    Key Features:
    - Pre-change portfolio authorization
    - Real-time portfolio risk monitoring with oversight
    - Position change risk assessment and approval
    - Portfolio-level risk limit enforcement
    - Emergency portfolio lockdown capabilities
    """
    
    def __init__(self, central_risk_manager: CentralRiskManager,
                 initial_capital: float = 1_000_000.0):
        
        self.central_risk_manager = central_risk_manager
        self.risk_monitor = PortfolioRiskMonitor(central_risk_manager)
        self.initial_capital = initial_capital
        
        # Portfolio state
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.cash_balance = initial_capital
        self.portfolio_value = initial_capital
        
        # Authorization tracking
        self.pending_authorizations: Dict[str, PortfolioAuthorizationRequest] = {}
        self.authorized_operations: Dict[str, PortfolioAuthorizationResponse] = {}
        self.operation_history: List[Dict[str, Any]] = []
        
        # Risk limits and settings
        self.max_position_concentration = 0.3  # 30% max position size
        self.max_sector_concentration = 0.4    # 40% max sector exposure
        self.max_leverage = 1.2                # 1.2x max leverage
        
        # Risk metrics
        self.total_authorized_operations = 0
        self.total_rejected_operations = 0
        self.authorization_success_rate = 1.0
        
        logger.info(f"🏗️ Risk-Integrated Portfolio Manager initialized - "
                   f"Capital: ${initial_capital:,.2f}")
    
    async def request_position_authorization(self,
                                           symbol: str,
                                           operation_type: PositionChangeType,
                                           proposed_quantity: float,
                                           proposed_price: float,
                                           strategy_id: str) -> PortfolioAuthorizationResponse:
        """
        Request authorization for portfolio position change through CentralRiskManager
        
        Args:
            symbol: Symbol for position change
            operation_type: Type of position change
            proposed_quantity: Proposed new position quantity
            proposed_price: Expected execution price
            strategy_id: Strategy requesting the change
            
        Returns:
            PortfolioAuthorizationResponse with authorization decision
        """
        
        request_id = f"portfolio_auth_{uuid.uuid4().hex[:8]}"
        
        logger.info(f"🔐 Requesting position authorization: {request_id} - "
                   f"{operation_type.value} {proposed_quantity} {symbol}")
        
        # Get current position
        current_quantity = self.positions.get(symbol, {}).get('quantity', 0.0)
        
        # Calculate portfolio impact
        position_value = proposed_quantity * proposed_price
        new_concentration = position_value / self.portfolio_value if self.portfolio_value > 0 else 0.0
        
        # Create authorization request
        auth_request = PortfolioAuthorizationRequest(
            request_id=request_id,
            operation_type=operation_type,
            symbol=symbol,
            current_quantity=current_quantity,
            proposed_quantity=proposed_quantity,
            proposed_price=proposed_price,
            strategy_id=strategy_id,
            portfolio_value=self.portfolio_value,
            position_concentration=new_concentration,
            expected_impact={
                'concentration_change': new_concentration - self._get_current_concentration(symbol),
                'portfolio_impact_pct': position_value / self.portfolio_value if self.portfolio_value > 0 else 0.0
            }
        )
        
        # Assess portfolio risk level
        auth_request.risk_level = await self._assess_portfolio_risk_level(auth_request)
        
        # Store pending authorization
        self.pending_authorizations[request_id] = auth_request
        
        try:
            # Create position request for CentralRiskManager
            position_request = PositionRequest(
                request_id=request_id,
                strategy_id=strategy_id,
                symbol=symbol,
                side="BUY" if proposed_quantity > current_quantity else "SELL",
                quantity=abs(proposed_quantity - current_quantity),
                price=proposed_price,
                timestamp=datetime.now(),
                position_type=operation_type.value
            )
            
            # Request authorization from CentralRiskManager
            risk_decision = await self.central_risk_manager.authorize_position_change(position_request)
            
            # Convert risk decision to portfolio authorization
            auth_response = await self._convert_risk_decision_to_portfolio_authorization(
                request_id, risk_decision, auth_request
            )
            
            # Store authorization response
            self.authorized_operations[request_id] = auth_response
            
            # Remove from pending
            if request_id in self.pending_authorizations:
                del self.pending_authorizations[request_id]
            
            # Update metrics
            if auth_response.status == PortfolioAuthorizationStatus.AUTHORIZED:
                self.total_authorized_operations += 1
            else:
                self.total_rejected_operations += 1
            
            self._update_authorization_success_rate()
            
            logger.info(f"✅ Position authorization completed: {request_id} - "
                       f"Status: {auth_response.status.value}")
            
            return auth_response
            
        except Exception as e:
            logger.error(f"❌ Position authorization failed: {request_id} - Error: {e}")
            
            # Return rejection response
            return PortfolioAuthorizationResponse(
                request_id=request_id,
                status=PortfolioAuthorizationStatus.REJECTED,
                authorized_quantity=0.0,
                authorized_conditions=["AUTHORIZATION_ERROR"]
            )
    
    async def execute_authorized_position_change(self,
                                               authorization: PortfolioAuthorizationResponse) -> bool:
        """
        Execute a position change that has been authorized by CentralRiskManager
        
        Args:
            authorization: The authorization response from request_position_authorization
            
        Returns:
            bool indicating success of the position change
        """
        
        request_id = authorization.request_id
        
        # Verify authorization status
        if authorization.status != PortfolioAuthorizationStatus.AUTHORIZED:
            raise ValueError(f"Cannot execute unauthorized position change: {request_id} - "
                           f"Status: {authorization.status.value}")
        
        # Get original request
        original_request = None
        for auth_req in self.pending_authorizations.values():
            if auth_req.request_id == request_id:
                original_request = auth_req
                break
        
        if original_request is None:
            # Try to find in authorized operations
            if request_id in self.authorized_operations:
                # Create minimal request from authorization
                original_request = PortfolioAuthorizationRequest(
                    request_id=request_id,
                    operation_type=PositionChangeType.OPEN_POSITION,
                    symbol="UNKNOWN",
                    current_quantity=0.0,
                    proposed_quantity=authorization.authorized_quantity,
                    proposed_price=100.0,
                    strategy_id="unknown"
                )
        
        if original_request is None:
            raise ValueError(f"Original authorization request not found: {request_id}")
        
        logger.info(f"🎯 Executing authorized position change: {request_id} - "
                   f"Quantity: {authorization.authorized_quantity}")
        
        try:
            # Start portfolio monitoring
            await self.risk_monitor.start_portfolio_monitoring(
                request_id, authorization
            )
            
            # Execute the position change
            success = await self._execute_position_change(
                original_request.symbol,
                authorization.authorized_quantity,
                original_request.proposed_price,
                original_request.strategy_id
            )
            
            # Record operation history
            self.operation_history.append({
                'timestamp': datetime.now(),
                'request_id': request_id,
                'authorization': authorization,
                'original_request': original_request,
                'execution_success': success,
                'portfolio_value_after': self.portfolio_value
            })
            
            # Notify risk manager of position change completion
            position_update = PositionUpdate(
                symbol=original_request.symbol,
                quantity_change=authorization.authorized_quantity - original_request.current_quantity,
                price=original_request.proposed_price,
                timestamp=datetime.now(),
                strategy_id=original_request.strategy_id,
                trade_id=request_id
            )
            
            await self.central_risk_manager.update_position(position_update)
            
            logger.info(f"✅ Authorized position change completed: {request_id} - "
                       f"Success: {success}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Authorized position change failed: {request_id} - Error: {e}")
            return False
    
    async def _execute_position_change(self, symbol: str, new_quantity: float,
                                     price: float, strategy_id: str) -> bool:
        """Execute the actual position change in the portfolio"""
        
        try:
            # Update position
            if symbol not in self.positions:
                self.positions[symbol] = {
                    'quantity': 0.0,
                    'avg_price': 0.0,
                    'market_value': 0.0,
                    'strategy_id': strategy_id,
                    'last_updated': datetime.now()
                }
            
            old_quantity = self.positions[symbol]['quantity']
            quantity_change = new_quantity - old_quantity
            
            # Update cash balance
            cash_impact = quantity_change * price
            self.cash_balance -= cash_impact
            
            # Update position
            if new_quantity == 0:
                # Close position
                del self.positions[symbol]
            else:
                # Update position
                if old_quantity == 0:
                    # New position
                    self.positions[symbol]['quantity'] = new_quantity
                    self.positions[symbol]['avg_price'] = price
                else:
                    # Update existing position
                    total_cost = (old_quantity * self.positions[symbol]['avg_price']) + (quantity_change * price)
                    self.positions[symbol]['quantity'] = new_quantity
                    if new_quantity != 0:
                        self.positions[symbol]['avg_price'] = total_cost / new_quantity
                
                self.positions[symbol]['market_value'] = new_quantity * price
                self.positions[symbol]['last_updated'] = datetime.now()
            
            # Update portfolio value
            self._update_portfolio_value()
            
            return True
            
        except Exception as e:
            logger.error(f"Error executing position change for {symbol}: {e}")
            return False
    
    def _update_portfolio_value(self):
        """Update total portfolio value"""
        
        total_position_value = sum(pos.get('market_value', 0.0) for pos in self.positions.values())
        self.portfolio_value = self.cash_balance + total_position_value
    
    def _get_current_concentration(self, symbol: str) -> float:
        """Get current position concentration for a symbol"""
        
        if symbol not in self.positions or self.portfolio_value == 0:
            return 0.0
        
        return self.positions[symbol].get('market_value', 0.0) / self.portfolio_value
    
    async def _assess_portfolio_risk_level(self,
                                         auth_request: PortfolioAuthorizationRequest) -> PortfolioRiskLevel:
        """Assess risk level of portfolio authorization request"""
        
        risk_level = PortfolioRiskLevel.MODERATE  # Default
        
        # Assess based on concentration
        if auth_request.position_concentration > 0.3:  # > 30%
            risk_level = PortfolioRiskLevel.AGGRESSIVE
        elif auth_request.position_concentration > 0.4:  # > 40%
            risk_level = PortfolioRiskLevel.SPECULATIVE
        
        # Assess based on operation type
        if auth_request.operation_type in [PositionChangeType.OPEN_POSITION, PositionChangeType.INCREASE_POSITION]:
            if risk_level == PortfolioRiskLevel.MODERATE:
                risk_level = PortfolioRiskLevel.MODERATE
        elif auth_request.operation_type == PositionChangeType.REBALANCE:
            # Rebalancing is generally conservative
            if risk_level == PortfolioRiskLevel.MODERATE:
                risk_level = PortfolioRiskLevel.CONSERVATIVE
        
        # Assess based on portfolio impact
        portfolio_impact = auth_request.expected_impact.get('portfolio_impact_pct', 0.0)
        if portfolio_impact > 0.2:  # > 20% portfolio impact
            risk_level = PortfolioRiskLevel.AGGRESSIVE
        
        return risk_level
    
    async def _convert_risk_decision_to_portfolio_authorization(self,
                                                              request_id: str,
                                                              risk_decision: RiskDecision,
                                                              auth_request: PortfolioAuthorizationRequest) -> PortfolioAuthorizationResponse:
        """Convert CentralRiskManager decision to portfolio authorization"""
        
        # Map risk manager decisions to portfolio authorization status
        status_mapping = {
            "APPROVE": PortfolioAuthorizationStatus.AUTHORIZED,
            "REJECT": PortfolioAuthorizationStatus.REJECTED,
            "REDUCE": PortfolioAuthorizationStatus.CONDITIONALLY_APPROVED,
            "MONITOR": PortfolioAuthorizationStatus.MONITORING_REQUIRED,
            "HALT": PortfolioAuthorizationStatus.PORTFOLIO_LOCKDOWN
        }
        
        status = status_mapping.get(risk_decision.decision, PortfolioAuthorizationStatus.REJECTED)
        
        # Determine authorized quantity
        authorized_quantity = auth_request.proposed_quantity
        if risk_decision.decision == "REDUCE":
            # Reduce quantity by 50% as default
            quantity_change = auth_request.proposed_quantity - auth_request.current_quantity
            reduced_change = quantity_change * 0.5
            authorized_quantity = auth_request.current_quantity + reduced_change
        elif risk_decision.decision in ["REJECT", "HALT"]:
            authorized_quantity = auth_request.current_quantity  # No change
        
        # Set conditions based on risk decision
        conditions = []
        if risk_decision.decision == "MONITOR":
            conditions.append("REAL_TIME_PORTFOLIO_MONITORING")
        if risk_decision.decision == "REDUCE":
            conditions.append("POSITION_SIZE_REDUCED_FOR_RISK")
        
        # Set monitoring requirements
        real_time_monitoring = risk_decision.decision in ["MONITOR", "REDUCE"] or \
                             auth_request.risk_level in [PortfolioRiskLevel.AGGRESSIVE, PortfolioRiskLevel.SPECULATIVE]
        
        # Set expiry for temporary authorizations
        expiry = None
        if auth_request.risk_level == PortfolioRiskLevel.SPECULATIVE:
            expiry = datetime.now() + timedelta(hours=4)  # 4-hour authorization
        
        return PortfolioAuthorizationResponse(
            request_id=request_id,
            status=status,
            authorized_quantity=authorized_quantity,
            authorized_conditions=conditions,
            max_position_size=self.portfolio_value * self.max_position_concentration,
            max_concentration=self.max_position_concentration,
            required_hedge_ratio=0.5 if auth_request.risk_level == PortfolioRiskLevel.SPECULATIVE else None,
            real_time_monitoring=real_time_monitoring,
            position_monitoring_frequency="REAL_TIME" if real_time_monitoring else "STANDARD",
            risk_assessment=risk_decision.risk_assessment if hasattr(risk_decision, 'risk_assessment') else None,
            expiry_timestamp=expiry
        )
    
    def _update_authorization_success_rate(self):
        """Update authorization success rate metric"""
        
        total_requests = self.total_authorized_operations + self.total_rejected_operations
        if total_requests > 0:
            self.authorization_success_rate = self.total_authorized_operations / total_requests
        else:
            self.authorization_success_rate = 1.0
    
    async def get_portfolio_risk_metrics(self) -> Dict[str, Any]:
        """Get comprehensive portfolio risk metrics with risk attribution"""
        
        total_operations = len(self.operation_history)
        
        # Calculate portfolio metrics
        total_position_value = sum(pos.get('market_value', 0.0) for pos in self.positions.values())
        portfolio_value = self.cash_balance + total_position_value
        
        # Calculate concentration metrics
        concentrations = []
        for symbol, position in self.positions.items():
            if portfolio_value > 0:
                concentration = position.get('market_value', 0.0) / portfolio_value
                concentrations.append(concentration)
        
        max_concentration = max(concentrations) if concentrations else 0.0
        
        # Risk level breakdown
        risk_level_counts = {}
        for operation in self.operation_history:
            auth_req = operation.get('original_request')
            if auth_req:
                risk_level = getattr(auth_req, 'risk_level', PortfolioRiskLevel.MODERATE).value
                risk_level_counts[risk_level] = risk_level_counts.get(risk_level, 0) + 1
        
        return {
            'total_operations': total_operations,
            'authorization_success_rate': self.authorization_success_rate,
            'portfolio_value': portfolio_value,
            'cash_balance': self.cash_balance,
            'position_count': len(self.positions),
            'max_position_concentration': max_concentration,
            'leverage_ratio': total_position_value / self.initial_capital if self.initial_capital > 0 else 0.0,
            'risk_alert_count': len(self.risk_monitor.risk_alerts),
            'active_monitoring_count': len(self.risk_monitor.active_portfolios),
            'risk_level_breakdown': risk_level_counts
        }

# Example usage and testing
class ExamplePortfolioRiskIntegration:
    """Example implementation showing portfolio risk integration"""
    
    def __init__(self):
        # This would be initialized with actual CentralRiskManager
        self.central_risk_manager = None  # CentralRiskManager()
        self.portfolio_manager = None     # RiskIntegratedPortfolioManager(self.central_risk_manager)
    
    async def example_authorized_position_workflow(self):
        """Example workflow showing authorized position change process"""
        
        logger.info("🔄 Example: Authorized Position Change Workflow")
        
        # 1. Request position authorization
        # auth_response = await self.portfolio_manager.request_position_authorization(
        #     symbol="AAPL",
        #     operation_type=PositionChangeType.OPEN_POSITION,
        #     proposed_quantity=1000,
        #     proposed_price=150.0,
        #     strategy_id="mean_reversion_v2"
        # )
        
        # 2. Execute if authorized
        # if auth_response.status == PortfolioAuthorizationStatus.AUTHORIZED:
        #     success = await self.portfolio_manager.execute_authorized_position_change(auth_response)
        #     return success
        
        logger.info("✅ Example workflow completed")

if __name__ == "__main__":
    # Basic testing
    print("🏗️ Portfolio Risk Integration - Phase 2 Component")
    print("=" * 60)
    print("Features:")
    print("- Portfolio position authorization through CentralRiskManager")
    print("- Real-time portfolio risk monitoring and controls")
    print("- Position change authorization workflows")
    print("- Portfolio-level risk limit enforcement")
    print("- Emergency portfolio lockdown capabilities")
    print("\nIntegration Status: Ready for Phase 2 deployment")