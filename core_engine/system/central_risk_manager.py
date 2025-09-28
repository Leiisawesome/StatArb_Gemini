"""
Central Risk Manager - TradeDesk Architecture Compliance
=======================================================

Enhanced RiskManager implementing the central governance hub pattern.
Serves as the single authority for ALL trading decisions in the system.

Architecture Compliance:
- Central hub that encapsulates all trading decisions
- Controls WHAT (StrategyManager) → HOW (TradingEngine) → ACTION (UnifiedExecutionEngine)
- No component can execute trades independently
- All trading decisions flow through RiskManager authorization
- Regime-aware risk management with direct RegimeEngine integration

Author: StatArb_Gemini Architecture Compliance
Version: 1.0.0 (TradeDesk Architecture)
"""

import asyncio
import logging
import threading
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np
import json
from collections import defaultdict

# Import the UnifiedExecutionEngine and ISystemComponent
from .unified_execution_engine import (
    UnifiedExecutionEngine, ExecutionAuthorization, ExecutionRequest, 
    ExecutionResult, ExecutionAlgorithm, ExecutionUrgency
)
from .interfaces import ISystemComponent

logger = logging.getLogger(__name__)


class TradingDecisionType(Enum):
    """Types of trading decisions requiring authorization"""
    STRATEGY_ACTIVATION = "strategy_activation"
    STRATEGY_DEACTIVATION = "strategy_deactivation"
    POSITION_ENTRY = "position_entry"
    POSITION_EXIT = "position_exit"
    POSITION_ADJUSTMENT = "position_adjustment"
    PORTFOLIO_REBALANCING = "portfolio_rebalancing"
    EMERGENCY_LIQUIDATION = "emergency_liquidation"
    RISK_LIMIT_ADJUSTMENT = "risk_limit_adjustment"


class AuthorizationLevel(Enum):
    """Authorization levels for different decision types"""
    AUTOMATIC = "automatic"      # Auto-approved within normal parameters
    STANDARD = "standard"        # Normal review process
    ELEVATED = "elevated"        # Requires elevated review
    EMERGENCY = "emergency"      # Emergency authorization
    REJECTED = "rejected"        # Authorization denied


@dataclass
class TradingDecisionRequest:
    """Request for trading decision authorization"""
    
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    decision_type: TradingDecisionType = TradingDecisionType.POSITION_ENTRY
    
    # Request details
    strategy_id: str = ""
    symbol: str = ""
    side: str = ""  # buy/sell/hold
    quantity: float = 0.0
    expected_return: float = 0.0
    confidence: float = 0.0
    
    # Risk context
    current_position: float = 0.0
    portfolio_impact: float = 0.0
    risk_score: float = 0.0
    
    # Market context
    market_regime: str = "unknown"
    regime_confidence: float = 0.0
    volatility_estimate: float = 0.0
    
    # Timing
    urgency: ExecutionUrgency = ExecutionUrgency.NORMAL
    max_execution_time: int = 3600  # 1 hour
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    requesting_component: str = ""
    justification: str = ""


@dataclass
class TradingAuthorization:
    """Authorization result for trading decisions"""
    
    authorization_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str = ""
    
    # Authorization result
    authorization_level: AuthorizationLevel = AuthorizationLevel.REJECTED
    authorized_quantity: float = 0.0
    max_quantity: float = 0.0
    
    # Risk constraints
    position_limit: float = 0.0
    risk_budget_allocation: float = 0.0
    max_market_impact: float = 0.01
    
    # Execution constraints
    allowed_algorithms: List[ExecutionAlgorithm] = field(default_factory=list)
    max_execution_time: int = 3600
    venue_restrictions: List[str] = field(default_factory=list)
    
    # Authorization metadata
    risk_manager_id: str = "central_risk_manager"
    authorized_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime = field(default_factory=lambda: datetime.now() + timedelta(hours=1))
    
    # Conditions and restrictions
    conditions: List[str] = field(default_factory=list)
    restrictions: List[str] = field(default_factory=list)
    monitoring_requirements: List[str] = field(default_factory=list)
    
    # Validation
    is_valid: bool = True
    rejection_reason: str = ""


@dataclass
class RiskManagerConfig:
    """
    Configuration for the central risk manager
    Enhanced with proper signal confidence requirements from test findings
    """
    
    # Risk limits
    max_position_size: float = 0.10  # 10% max position
    max_daily_var: float = 0.05      # 5% daily VaR
    max_total_risk: float = 0.20     # 20% total portfolio risk
    position_concentration_limit: float = 0.15  # 15% per position
    strategy_allocation_limit: float = 0.33     # 33% per strategy
    
    # Signal confidence requirements (from test findings)
    min_signal_confidence: float = 0.6  # Minimum confidence for authorization
    high_confidence_threshold: float = 0.8  # High confidence for automatic approval
    extreme_confidence_threshold: float = 0.9  # Extreme confidence signals
    
    # Authorization settings
    auto_approval_threshold: float = 0.01  # 1% auto-approve threshold
    elevated_review_threshold: float = 0.05  # 5% elevated review
    emergency_threshold: float = 0.10      # 10% emergency threshold
    
    # Execution settings
    default_execution_algorithm: ExecutionAlgorithm = ExecutionAlgorithm.ADAPTIVE
    max_execution_time: int = 3600  # 1 hour
    
    # Monitoring
    real_time_monitoring: bool = True
    monitoring_frequency: int = 1  # seconds
    alert_thresholds: Dict[str, float] = field(default_factory=lambda: {
        'position_limit_breach': 0.95,
        'var_limit_breach': 0.90,
        'concentration_breach': 0.90
    })
    
    # Regime integration
    regime_risk_multipliers: Dict[str, float] = field(default_factory=lambda: {
        'bull_market': 0.8,
        'bear_market': 1.3,
        'high_volatility': 1.5,
        'low_volatility': 0.7,
        'crisis': 2.0,
        'sideways': 1.0
    })


class CentralRiskManager(ISystemComponent):
    """
    Central Risk Manager - Institutional Governance Hub
    
    Implements the central governance pattern where ALL trading decisions
    flow through the RiskManager. No component can execute trades independently.
    
    Architecture:
    - WHAT (StrategyManager): Determines trading strategies → submits to RiskManager
    - HOW (TradingEngine): Plans execution methodology → under RiskManager control
    - ACTION (UnifiedExecutionEngine): Executes trades → requires RiskManager authorization
    - MONITORING: Continuous risk monitoring and dynamic limit adjustment
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize central risk manager"""
        
        self.config = RiskManagerConfig(**(config or {}))
        
        # Core components under RiskManager control
        self.unified_execution_engine: Optional[UnifiedExecutionEngine] = None
        self.strategy_manager: Optional[Any] = None  # Will be set by orchestrator
        self.trading_engine: Optional[Any] = None    # Will be set by orchestrator
        self.regime_engine: Optional[Any] = None     # Will be set by orchestrator
        
        # Authorization tracking
        self.pending_requests: Dict[str, TradingDecisionRequest] = {}
        self.active_authorizations: Dict[str, TradingAuthorization] = {}
        self.authorization_history: List[TradingAuthorization] = []
        
        # Risk state
        self.current_positions: Dict[str, float] = {}
        self.strategy_allocations: Dict[str, float] = {}
        self.current_var: float = 0.0
        self.portfolio_value: float = 1000000.0  # $1M default
        
        # Risk limits and audit trails (FIXED: Missing initialization)
        self.risk_limits: Dict[str, float] = {
            'max_risk_score': 0.8,
            'max_portfolio_impact': 0.1,
            'max_position_concentration': 0.2
        }
        self.authorization_audit: List[Dict[str, Any]] = []
        self.escalation_audit: List[Dict[str, Any]] = []
        
        # Risk metrics
        self.risk_metrics = {
            'total_exposure': 0.0,
            'concentration_risk': 0.0,
            'var_utilization': 0.0,
            'strategy_diversification': 0.0,
            'regime_risk_adjustment': 1.0
        }
        
        # Control state
        self.is_initialized = False
        self.is_operational = False
        self.emergency_mode = False
        
        # Threading
        self.authorization_lock = threading.Lock()
        self.monitoring_task: Optional[asyncio.Task] = None
        
        logger.info("Central Risk Manager initialized - Governance Hub Ready")
    
    async def initialize(self, execution_config: Optional[Dict[str, Any]] = None) -> bool:
        """Initialize the central risk manager and all controlled components"""
        
        try:
            logger.info("Initializing Central Risk Manager...")
            
            # Initialize UnifiedExecutionEngine under our control
            self.unified_execution_engine = UnifiedExecutionEngine(execution_config or {})
            
            # Start monitoring
            if self.config.real_time_monitoring:
                self.monitoring_task = asyncio.create_task(self._continuous_monitoring())
            
            self.is_initialized = True
            self.is_operational = True
            
            logger.info("✅ Central Risk Manager initialization completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Central Risk Manager initialization failed: {e}")
            return False
    
    def set_controlled_components(self, strategy_manager: Any = None, 
                                trading_engine: Any = None,
                                regime_engine: Any = None):
        """Set components under RiskManager control"""
        
        if strategy_manager:
            self.strategy_manager = strategy_manager
            logger.info("✅ StrategyManager registered with Central Risk Manager")
        
        if trading_engine:
            self.trading_engine = trading_engine
            logger.info("✅ TradingEngine registered with Central Risk Manager")
            
        if regime_engine:
            self.regime_engine = regime_engine
            logger.info("✅ RegimeEngine registered with Central Risk Manager")
    
    # ISystemComponent interface implementation
    async def start(self) -> bool:
        """Start component operations"""
        if not self.is_initialized:
            logger.error("Cannot start CentralRiskManager - not initialized")
            return False
        
        try:
            self.is_operational = True
            logger.info("✅ Central Risk Manager started and operational")
            return True
        except Exception as e:
            logger.error(f"❌ Central Risk Manager start failed: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop component operations"""
        try:
            self.is_operational = False
            
            # Cancel monitoring task
            if self.monitoring_task:
                self.monitoring_task.cancel()
                
            logger.info("✅ Central Risk Manager stopped")
            return True
        except Exception as e:
            logger.error(f"❌ Central Risk Manager stop failed: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        return {
            'healthy': self.is_operational and self.is_initialized,
            'initialized': self.is_initialized,
            'operational': self.is_operational,
            'component_type': 'CentralRiskManager',
            'active_authorizations': len(self.active_authorizations),
            'pending_requests': len(self.pending_requests),
            'current_var': self.current_var,
            'portfolio_value': self.portfolio_value,
            'total_positions': len(self.current_positions),
            'execution_engine_available': self.unified_execution_engine is not None
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get component status"""
        return {
            'component_type': 'CentralRiskManager',
            'initialized': self.is_initialized,
            'operational': self.is_operational,
            'active_authorizations': len(self.active_authorizations),
            'pending_requests': len(self.pending_requests),
            'current_positions': len(self.current_positions),
            'portfolio_value': self.portfolio_value,
            'risk_metrics': self.risk_metrics.copy(),
            'controlled_components': {
                'strategy_manager': self.strategy_manager is not None,
                'trading_engine': self.trading_engine is not None,
                'regime_engine': self.regime_engine is not None,
                'execution_engine': self.unified_execution_engine is not None
            }
        }
    
    async def authorize_trading_decision(self, request: TradingDecisionRequest) -> TradingAuthorization:
        """
        Central authorization point for ALL trading decisions
        
        This is the core governance method - every trading decision in the system
        must flow through this authorization process.
        """
        
        try:
            with self.authorization_lock:
                logger.info(f"Processing authorization request: {request.request_id}")
                
                # Store pending request
                self.pending_requests[request.request_id] = request
                
                # Perform comprehensive risk assessment
                authorization = await self._assess_trading_request(request)
                
                # Store authorization
                if authorization.authorization_level != AuthorizationLevel.REJECTED:
                    self.active_authorizations[authorization.authorization_id] = authorization
                
                # Add to history
                self.authorization_history.append(authorization)
                
                # Clean up pending request
                self.pending_requests.pop(request.request_id, None)
                
                logger.info(f"Authorization completed: {authorization.authorization_level.value}")
                return authorization
                
        except Exception as e:
            logger.error(f"Authorization process failed: {e}")
            
            # Return rejection
            return TradingAuthorization(
                request_id=request.request_id,
                authorization_level=AuthorizationLevel.REJECTED,
                rejection_reason=f"Authorization process error: {e}"
            )
    
    async def _assess_trading_request(self, request: TradingDecisionRequest) -> TradingAuthorization:
        """Comprehensive risk assessment of trading request"""
        
        try:
            authorization = TradingAuthorization(request_id=request.request_id)
            
            # Risk impact assessment
            risk_impact = self._calculate_risk_impact(request)
            
            # Position limit check
            position_check = self._check_position_limits(request)
            
            # Concentration check
            concentration_check = self._check_concentration_limits(request)
            
            # Strategy allocation check
            strategy_check = self._check_strategy_limits(request)
            
            # Regime-based risk adjustment
            regime_adjustment = self._get_regime_risk_adjustment(request)
            
            # Determine authorization level
            authorization_level = self._determine_authorization_level(
                risk_impact, position_check, concentration_check, strategy_check, regime_adjustment, request
            )
            
            # Set authorization details
            authorization.authorization_level = authorization_level
            
            if authorization_level != AuthorizationLevel.REJECTED:
                # Calculate authorized quantity
                authorized_qty = self._calculate_authorized_quantity(request, risk_impact, regime_adjustment)
                authorization.authorized_quantity = authorized_qty
                authorization.max_quantity = min(request.quantity, authorized_qty * 1.1)  # 10% buffer
                
                # Set risk constraints
                authorization.position_limit = self._get_position_limit(request.symbol)
                authorization.risk_budget_allocation = risk_impact
                authorization.max_market_impact = self._get_max_market_impact(request)
                
                # Set execution constraints
                authorization.allowed_algorithms = self._get_allowed_algorithms(request)
                authorization.max_execution_time = min(request.max_execution_time, self.config.max_execution_time)
                
                # Set conditions and monitoring
                authorization.conditions = self._get_authorization_conditions(request, risk_impact)
                authorization.monitoring_requirements = self._get_monitoring_requirements(request)
                
                logger.info(f"Authorized: {authorized_qty} of {request.quantity} requested")
            else:
                authorization.rejection_reason = self._get_rejection_reason(
                    position_check, concentration_check, strategy_check, risk_impact, request
                )
                logger.warning(f"Request rejected: {authorization.rejection_reason}")
            
            return authorization
            
        except Exception as e:
            logger.error(f"Risk assessment failed: {e}")
            
            return TradingAuthorization(
                request_id=request.request_id,
                authorization_level=AuthorizationLevel.REJECTED,
                rejection_reason=f"Risk assessment error: {e}"
            )
    
    async def execute_authorized_trade(self, authorization: TradingAuthorization,
                                     execution_params: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        """
        Execute trade using UnifiedExecutionEngine with RiskManager authorization
        
        This method bridges the authorization and execution phases while maintaining
        central control throughout the process.
        """
        
        try:
            if not self.unified_execution_engine:
                raise RuntimeError("UnifiedExecutionEngine not initialized")
            
            # Validate authorization
            if not self._validate_authorization(authorization):
                return ExecutionResult(
                    authorization_id=authorization.authorization_id,
                    status="rejected",
                    execution_log=["Authorization validation failed"]
                )
            
            # Create execution authorization for UnifiedExecutionEngine
            execution_auth = ExecutionAuthorization(
                authorization_id=authorization.authorization_id,
                risk_manager_id="central_risk_manager",
                symbol=authorization.request_id,  # TODO: Extract from original request
                side="buy",  # TODO: Extract from original request
                quantity=authorization.authorized_quantity,
                max_quantity=authorization.max_quantity,
                max_market_impact=authorization.max_market_impact,
                max_execution_time=authorization.max_execution_time,
                allowed_algorithms=authorization.allowed_algorithms,
                expires_at=authorization.expires_at
            )
            
            # Create execution request
            execution_request = ExecutionRequest(
                authorization=execution_auth,
                algorithm=execution_params.get('algorithm', self.config.default_execution_algorithm) if execution_params else self.config.default_execution_algorithm,
                urgency=execution_params.get('urgency', ExecutionUrgency.NORMAL) if execution_params else ExecutionUrgency.NORMAL
            )
            
            # Execute through UnifiedExecutionEngine
            logger.info(f"Executing authorized trade: {authorization.authorization_id}")
            result = await self.unified_execution_engine.execute_authorized_trade(execution_request)
            
            # Post-execution risk monitoring
            await self._post_execution_monitoring(authorization, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Authorized trade execution failed: {e}")
            
            return ExecutionResult(
                authorization_id=authorization.authorization_id,
                status="failed",
                execution_log=[f"Execution failed: {e}"]
            )
    
    def _calculate_risk_impact(self, request: TradingDecisionRequest) -> float:
        """Calculate risk impact of trading request"""
        
        try:
            # Position size as percentage of portfolio
            position_impact = (request.quantity * 100.0) / self.portfolio_value  # Assuming $100/share
            
            # Adjust for volatility
            volatility_adjustment = max(1.0, request.volatility_estimate)
            
            # Regime adjustment
            regime_multiplier = self.config.regime_risk_multipliers.get(request.market_regime, 1.0)
            
            # Total risk impact
            total_impact = position_impact * volatility_adjustment * regime_multiplier
            
            return total_impact
            
        except Exception as e:
            logger.error(f"Error calculating risk impact: {e}")
            return 0.10  # Conservative default
    
    def _check_position_limits(self, request: TradingDecisionRequest) -> bool:
        """Check if request violates position limits"""
        
        try:
            current_position = self.current_positions.get(request.symbol, 0.0)
            new_position = current_position + request.quantity
            position_pct = abs(new_position * 100.0) / self.portfolio_value  # Assuming $100/share
            
            return position_pct <= self.config.max_position_size
            
        except Exception as e:
            logger.error(f"Error checking position limits: {e}")
            return False
    
    def _check_concentration_limits(self, request: TradingDecisionRequest) -> bool:
        """Check concentration limits"""
        
        try:
            current_position = self.current_positions.get(request.symbol, 0.0)
            new_position = current_position + request.quantity
            concentration = abs(new_position * 100.0) / self.portfolio_value
            
            return concentration <= self.config.position_concentration_limit
            
        except Exception as e:
            logger.error(f"Error checking concentration limits: {e}")
            return False
    
    def _check_strategy_limits(self, request: TradingDecisionRequest) -> bool:
        """Check strategy allocation limits"""
        
        try:
            current_allocation = self.strategy_allocations.get(request.strategy_id, 0.0)
            return current_allocation <= self.config.strategy_allocation_limit
            
        except Exception as e:
            logger.error(f"Error checking strategy limits: {e}")
            return False
    
    def _get_regime_risk_adjustment(self, request: TradingDecisionRequest) -> float:
        """Get regime-based risk adjustment"""
        
        regime_multiplier = self.config.regime_risk_multipliers.get(request.market_regime, 1.0)
        confidence_adjustment = max(0.5, request.regime_confidence)  # Minimum 50% confidence
        
        return regime_multiplier * confidence_adjustment
    
    def _determine_authorization_level(self, risk_impact: float, position_check: bool,
                                     concentration_check: bool, strategy_check: bool,
                                     regime_adjustment: float, request: Optional[TradingDecisionRequest] = None) -> AuthorizationLevel:
        """
        Determine authorization level based on risk assessment
        Enhanced with signal confidence validation from test findings
        """
        
        # Check for rejection conditions
        if not (position_check and concentration_check and strategy_check):
            return AuthorizationLevel.REJECTED
        
        # Signal confidence validation (from test findings)
        if request and hasattr(request, 'confidence'):
            if request.confidence < self.config.min_signal_confidence:
                logger.warning(f"Signal confidence {request.confidence:.2f} below minimum {self.config.min_signal_confidence}")
                return AuthorizationLevel.REJECTED
        
        # Adjust risk impact for regime
        adjusted_risk = risk_impact * regime_adjustment
        
        # Enhanced authorization logic with confidence consideration
        if request and hasattr(request, 'confidence'):
            # High confidence signals get preferential treatment
            if request.confidence >= self.config.extreme_confidence_threshold:
                # Extreme confidence (0.9+) - automatic approval for reasonable risk
                if adjusted_risk <= self.config.elevated_review_threshold:
                    return AuthorizationLevel.AUTOMATIC
            elif request.confidence >= self.config.high_confidence_threshold:
                # High confidence (0.8+) - automatic approval for low risk
                if adjusted_risk <= self.config.auto_approval_threshold * 2:
                    return AuthorizationLevel.AUTOMATIC
        
        # Standard risk-based authorization
        if adjusted_risk <= self.config.auto_approval_threshold:
            return AuthorizationLevel.AUTOMATIC
        elif adjusted_risk <= self.config.elevated_review_threshold:
            return AuthorizationLevel.STANDARD
        elif adjusted_risk <= self.config.emergency_threshold:
            return AuthorizationLevel.ELEVATED
        else:
            return AuthorizationLevel.EMERGENCY
    
    def _calculate_authorized_quantity(self, request: TradingDecisionRequest,
                                     risk_impact: float, regime_adjustment: float) -> float:
        """
        ARCHITECTURAL FIX: Calculate authorized quantity with proper cash and position validation
        """
        
        try:
            # Start with requested quantity
            authorized_qty = request.quantity
            
            # CRITICAL FIX: Cash availability check for BUY orders BEFORE authorization
            if request.side.lower() == 'buy':
                # Get available cash (this should be passed from the trading component)
                available_cash = getattr(request, 'available_cash', self.portfolio_value * 0.95)  # Conservative default
                required_cash = authorized_qty * getattr(request, 'price', 100.0)  # Default price if not provided
                
                if required_cash > available_cash:
                    # Reduce quantity to fit available cash
                    max_affordable_qty = available_cash / getattr(request, 'price', 100.0)
                    if max_affordable_qty < 1.0:  # Less than 1 share affordable
                        logger.warning(f"🔒 BUY rejected: Insufficient cash. Need ${required_cash:.2f}, have ${available_cash:.2f}")
                        return 0.0
                    else:
                        logger.info(f"🔒 BUY order capped by cash: requested {authorized_qty}, "
                                   f"affordable {max_affordable_qty:.2f}, authorized {max_affordable_qty:.2f}")
                        authorized_qty = max_affordable_qty
            
            # CRITICAL FIX: Position-aware SELL order capping with exact precision
            elif request.side.lower() == 'sell':
                current_position = self.current_positions.get(request.symbol, 0.0)
                
                if current_position <= 0:
                    # No position to sell
                    logger.warning(f"🔒 SELL rejected: No position in {request.symbol}")
                    return 0.0
                else:
                    # Cap SELL quantity by actual position with exact precision
                    max_sellable = abs(current_position)
                    if authorized_qty > max_sellable:
                        logger.info(f"🔒 SELL order capped: requested {authorized_qty:.2f}, "
                                   f"available {max_sellable:.2f}, authorized {max_sellable:.2f}")
                        authorized_qty = max_sellable
            
            # Apply risk-based adjustment
            if risk_impact > self.config.auto_approval_threshold:
                # Reduce quantity for higher risk
                risk_reduction = min(0.5, (risk_impact - self.config.auto_approval_threshold) * 2)
                authorized_qty *= (1.0 - risk_reduction)
            
            # Apply regime adjustment
            if regime_adjustment > 1.2:  # High risk regime
                authorized_qty *= 0.8  # Reduce by 20%
            elif regime_adjustment < 0.8:  # Low risk regime
                authorized_qty *= 1.1  # Increase by 10%
            
            # PRECISION FIX: Round to 2 decimal places to avoid floating point errors
            authorized_qty = max(0.0, round(authorized_qty, 2))
            
            return authorized_qty
            
        except Exception as e:
            logger.error(f"Error calculating authorized quantity: {e}")
            return 0.0
    
    def _get_position_limit(self, symbol: str) -> float:
        """Get position limit for symbol"""
        return self.config.max_position_size
    
    def _get_max_market_impact(self, request: TradingDecisionRequest) -> float:
        """Get maximum allowed market impact"""
        
        if request.urgency == ExecutionUrgency.EMERGENCY:
            return 0.05  # 5% max for emergency
        elif request.urgency == ExecutionUrgency.URGENT:
            return 0.02  # 2% max for urgent
        else:
            return 0.01  # 1% max for normal
    
    def _get_allowed_algorithms(self, request: TradingDecisionRequest) -> List[ExecutionAlgorithm]:
        """Get allowed execution algorithms for request"""
        
        if request.urgency == ExecutionUrgency.EMERGENCY:
            return [ExecutionAlgorithm.MARKET]
        elif request.urgency == ExecutionUrgency.URGENT:
            return [ExecutionAlgorithm.MARKET, ExecutionAlgorithm.ADAPTIVE]
        else:
            return [ExecutionAlgorithm.MARKET, ExecutionAlgorithm.TWAP, ExecutionAlgorithm.ADAPTIVE]
    
    def _get_authorization_conditions(self, request: TradingDecisionRequest, risk_impact: float) -> List[str]:
        """Get authorization conditions"""
        
        conditions = []
        
        if risk_impact > self.config.auto_approval_threshold:
            conditions.append("Enhanced monitoring required")
        
        if request.urgency in [ExecutionUrgency.URGENT, ExecutionUrgency.EMERGENCY]:
            conditions.append("Immediate execution required")
        
        if request.regime_confidence < 0.7:
            conditions.append("Low regime confidence - exercise caution")
        
        return conditions
    
    def _get_monitoring_requirements(self, request: TradingDecisionRequest) -> List[str]:
        """Get monitoring requirements for authorization"""
        
        requirements = ["Real-time position monitoring", "Market impact tracking"]
        
        if request.decision_type == TradingDecisionType.EMERGENCY_LIQUIDATION:
            requirements.append("Emergency liquidation monitoring")
        
        return requirements
    
    def _validate_authorization(self, authorization: TradingAuthorization) -> bool:
        """Validate authorization is still valid"""
        
        if datetime.now() > authorization.expires_at:
            return False
        
        if authorization.authorization_level == AuthorizationLevel.REJECTED:
            return False
        
        return authorization.is_valid
    
    def _get_rejection_reason(self, position_check: bool, concentration_check: bool,
                            strategy_check: bool, risk_impact: float, request: Optional[TradingDecisionRequest] = None) -> str:
        """Get detailed rejection reason"""
        
        reasons = []
        
        # Check confidence first
        if request and hasattr(request, 'confidence'):
            if request.confidence < self.config.min_signal_confidence:
                reasons.append(f"Signal confidence {request.confidence:.2f} below minimum {self.config.min_signal_confidence:.2f}")
        
        if not position_check:
            reasons.append("Position limit exceeded")
        
        if not concentration_check:
            reasons.append("Concentration limit exceeded")
        
        if not strategy_check:
            reasons.append("Strategy allocation limit exceeded")
        
        if risk_impact > self.config.emergency_threshold:
            reasons.append("Risk impact exceeds emergency threshold")
        
        return "; ".join(reasons) if reasons else "Risk assessment failed"
    
    async def _post_execution_monitoring(self, authorization: TradingAuthorization,
                                       result: ExecutionResult):
        """
        Post-execution monitoring and risk assessment
        ENHANCED: Real-time position tracking and risk updates
        """
        
        try:
            # Extract trade details from authorization and result
            # Note: This requires the original request to be stored
            original_request = None
            for req_id, req in self.pending_requests.items():
                if req.request_id == authorization.request_id:
                    original_request = req
                    break
            
            if original_request and hasattr(result, 'filled_quantity'):
                symbol = original_request.symbol
                side = original_request.side.lower()
                filled_qty = result.filled_quantity
                
                # Update position tracking
                current_position = self.current_positions.get(symbol, 0.0)
                
                if side == 'buy':
                    new_position = current_position + filled_qty
                elif side == 'sell':
                    new_position = current_position - filled_qty
                else:
                    new_position = current_position
                
                self.current_positions[symbol] = new_position
                
                logger.info(f"📊 Position updated: {symbol} {current_position} → {new_position} "
                           f"({side.upper()} {filled_qty})")
                
                # Update risk metrics
                self._update_risk_metrics()
                
                # Check for risk limit breaches after position update
                await self._check_post_execution_risk_limits(symbol, new_position)
            
            logger.info(f"Post-execution monitoring completed for {authorization.authorization_id}")
            
        except Exception as e:
            logger.error(f"Post-execution monitoring failed: {e}")
    
    async def _check_post_execution_risk_limits(self, symbol: str, new_position: float):
        """Check risk limits after position update"""
        
        try:
            # Check position limits
            position_pct = abs(new_position * 100.0) / self.portfolio_value  # Assuming $100/share
            
            if position_pct > self.config.max_position_size:
                logger.warning(f"⚠️ Position limit breach: {symbol} at {position_pct:.2f}% "
                              f"(limit: {self.config.max_position_size:.2f}%)")
                
                # TODO: Implement automatic risk reduction measures
            
            # Check concentration limits
            if position_pct > self.config.position_concentration_limit:
                logger.warning(f"⚠️ Concentration limit breach: {symbol} at {position_pct:.2f}% "
                              f"(limit: {self.config.position_concentration_limit:.2f}%)")
            
        except Exception as e:
            logger.error(f"Post-execution risk check failed: {e}")
    
    def update_position(self, symbol: str, side: str, quantity: float, price: float = 0.0):
        """
        Manual position update method for external position tracking
        ENHANCED: Unified position tracking for all components
        """
        
        try:
            current_position = self.current_positions.get(symbol, 0.0)
            
            if side.lower() == 'buy':
                new_position = current_position + quantity
            elif side.lower() == 'sell':
                new_position = current_position - quantity
            else:
                logger.warning(f"Unknown side: {side}")
                return
            
            self.current_positions[symbol] = new_position
            
            logger.info(f"📊 Manual position update: {symbol} {current_position} → {new_position} "
                       f"({side.upper()} {quantity})")
            
            # Update risk metrics
            self._update_risk_metrics()
            
        except Exception as e:
            logger.error(f"Manual position update failed: {e}")
    
    def get_current_position(self, symbol: str) -> float:
        """Get current position for symbol"""
        return self.current_positions.get(symbol, 0.0)
    
    def get_all_positions(self) -> Dict[str, float]:
        """Get all current positions"""
        return self.current_positions.copy()
    
    @property
    def authorization_audit_trail(self) -> List[Dict[str, Any]]:
        """Get the authorization audit trail"""
        return self.authorization_audit
    
    async def _continuous_monitoring(self):
        """Continuous risk monitoring loop"""
        
        logger.info("Starting continuous risk monitoring")
        
        try:
            while self.is_operational:
                # Monitor active positions
                await self._monitor_positions()
                
                # Monitor active authorizations
                await self._monitor_authorizations()
                
                # Check for risk limit breaches
                await self._check_portfolio_risk_limits()
                
                # Update risk metrics
                self._update_risk_metrics()
                
                # Sleep until next monitoring cycle
                await asyncio.sleep(self.config.monitoring_frequency)
                
        except Exception as e:
            logger.error(f"Continuous monitoring error: {e}")
        
        logger.info("Continuous risk monitoring stopped")
    
    async def _monitor_positions(self):
        """Monitor current positions for risk"""
        pass  # TODO: Implement position monitoring
    
    async def _monitor_authorizations(self):
        """Monitor active authorizations for expiry"""
        
        try:
            current_time = datetime.now()
            expired_authorizations = []
            
            with self.authorization_lock:
                for auth_id, authorization in self.active_authorizations.items():
                    if current_time > authorization.expires_at:
                        expired_authorizations.append(auth_id)
                
                # Remove expired authorizations
                for auth_id in expired_authorizations:
                    self.active_authorizations.pop(auth_id, None)
                    logger.info(f"Authorization expired: {auth_id}")
                    
        except Exception as e:
            logger.error(f"Authorization monitoring error: {e}")
    
    async def _check_portfolio_risk_limits(self):
        """Check for risk limit breaches during continuous monitoring"""
        try:
            # Check portfolio-level risk limits
            total_exposure = sum(abs(pos * 100.0) for pos in self.current_positions.values())
            exposure_ratio = total_exposure / self.portfolio_value if self.portfolio_value > 0 else 0
            
            # Check if exposure exceeds limits
            if exposure_ratio > self.config.max_daily_var:
                logger.warning(f"Portfolio exposure ({exposure_ratio:.2%}) exceeds limit ({self.config.max_daily_var:.2%})")
            
            # Check individual position limits
            for symbol, position in self.current_positions.items():
                position_value = abs(position * 100.0)  # Assuming $100 per share for demo
                position_ratio = position_value / self.portfolio_value if self.portfolio_value > 0 else 0
                
                if position_ratio > self.config.max_position_size:
                    logger.warning(f"Position {symbol} ({position_ratio:.2%}) exceeds limit ({self.config.max_position_size:.2%})")
                    
        except Exception as e:
            logger.error(f"Risk limits check failed: {e}")
    
    def _update_risk_metrics(self):
        """Update current risk metrics"""
        
        try:
            # Calculate total exposure
            total_exposure = sum(abs(pos * 100.0) for pos in self.current_positions.values())
            self.risk_metrics['total_exposure'] = total_exposure / self.portfolio_value
            
            # Update other metrics
            # TODO: Implement comprehensive risk metric calculations
            
        except Exception as e:
            logger.error(f"Risk metrics update error: {e}")
    
    def get_risk_status(self) -> Dict[str, Any]:
        """Get current risk status"""
        
        return {
            'is_operational': self.is_operational,
            'emergency_mode': self.emergency_mode,
            'active_authorizations': len(self.active_authorizations),
            'current_positions': len(self.current_positions),
            'risk_metrics': self.risk_metrics.copy(),
            'portfolio_value': self.portfolio_value
        }
    
    def emergency_shutdown(self) -> bool:
        """Emergency shutdown of all trading operations"""
        
        try:
            logger.warning("🚨 EMERGENCY SHUTDOWN INITIATED")
            
            self.emergency_mode = True
            self.is_operational = False
            
            # Cancel all active authorizations
            with self.authorization_lock:
                cancelled_count = len(self.active_authorizations)
                self.active_authorizations.clear()
                logger.warning(f"Cancelled {cancelled_count} active authorizations")
            
            # Stop monitoring
            if self.monitoring_task:
                self.monitoring_task.cancel()
            
            logger.warning("🚨 EMERGENCY SHUTDOWN COMPLETED")
            return True
            
        except Exception as e:
            logger.error(f"Emergency shutdown failed: {e}")
            return False
    
    def shutdown(self):
        """Graceful shutdown of risk manager"""
        
        try:
            logger.info("Shutting down Central Risk Manager")
            
            self.is_operational = False
            
            # Stop monitoring
            if self.monitoring_task:
                self.monitoring_task.cancel()
            
            # Shutdown execution engine
            if self.unified_execution_engine:
                self.unified_execution_engine.shutdown()
            
            logger.info("Central Risk Manager shutdown completed")
            
        except Exception as e:
            logger.error(f"Shutdown error: {e}")

    # ========================================
    # RISK AUTHORIZATION METHODS
    # ========================================

    def authorize_risk_operation(self, risk_operation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Authorize risk operations through central risk governance

        Args:
            risk_operation: Operation requiring authorization with:
                - operation_type: Type of risk operation
                - risk_severity: Risk severity level
                - impact_assessment: Risk impact assessment
                - requester: Requesting component/authority

        Returns:
            Authorization decision
        """
        try:
            operation_type = risk_operation.get('operation_type')
            risk_severity = risk_operation.get('risk_severity', 'medium')
            impact_assessment = risk_operation.get('impact_assessment', {})
            requester = risk_operation.get('requester', 'unknown')

            # Assess risk impact
            risk_score = self._assess_risk_impact(impact_assessment)

            # Determine authorization requirements
            required_level = self._determine_authorization_level(risk_severity, risk_score)

            # Check current risk limits
            limits_check = self._check_risk_limits(risk_operation)

            # Make authorization decision
            if limits_check['within_limits'] and risk_score < self.risk_limits['max_risk_score']:
                authorization = {
                    'authorized': True,
                    'authorization_level': required_level.value,
                    'risk_score': risk_score,
                    'limits_check': limits_check,
                    'timestamp': datetime.now().isoformat(),
                    'authorization_id': f"auth_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                }
            else:
                authorization = {
                    'authorized': False,
                    'reason': limits_check.get('violation_reason', 'risk_limits_exceeded'),
                    'risk_score': risk_score,
                    'required_level': required_level.value,
                    'limits_check': limits_check,
                    'timestamp': datetime.now().isoformat()
                }

            # Log authorization decision
            logger.info(f"Risk operation authorization: {operation_type} - {authorization['authorized']}")

            # Add to authorization audit trail
            audit_entry = {
                'timestamp': datetime.now().isoformat(),
                'operation_type': operation_type,
                'risk_severity': risk_severity,
                'requester': requester,
                'risk_score': risk_score,
                'authorized': authorization['authorized'],
                'authorization_id': authorization.get('authorization_id')
            }
            self.authorization_audit.append(audit_entry)

            return authorization

        except Exception as e:
            logger.error(f"Risk operation authorization failed: {e}")
            return {
                'authorized': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def escalate_risk_authorization(self, escalation_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Escalate risk authorization to higher authority levels

        Args:
            escalation_request: Escalation details with:
                - operation: Operation requiring escalation
                - current_level: Current authorization level
                - escalation_reason: Reason for escalation
                - risk_assessment: Updated risk assessment

        Returns:
            Escalation result
        """
        try:
            operation = escalation_request.get('operation')
            current_level = escalation_request.get('current_level', AuthorizationLevel.OPERATIONAL)
            escalation_reason = escalation_request.get('escalation_reason', 'risk_threshold_exceeded')
            risk_assessment = escalation_request.get('risk_assessment', {})

            # Determine escalation target
            escalation_target = self._determine_escalation_target(current_level, escalation_reason)

            # Re-assess risk with additional context
            updated_risk_score = self._assess_risk_impact(risk_assessment)

            # Perform escalation
            escalation_result = {
                'escalated': True,
                'from_level': current_level.value,
                'to_level': escalation_target.value,
                'escalation_reason': escalation_reason,
                'updated_risk_score': updated_risk_score,
                'escalation_timestamp': datetime.now().isoformat(),
                'escalation_id': f"esc_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'requires_manual_review': escalation_target == AuthorizationLevel.GOVERNANCE_CONTROL
            }

            # Log escalation
            logger.warning(f"Risk authorization escalated: {operation} from {current_level.value} to {escalation_target.value}")

            # Add to escalation audit trail
            escalation_audit = {
                'timestamp': datetime.now().isoformat(),
                'operation': operation,
                'from_level': current_level.value,
                'to_level': escalation_target.value,
                'reason': escalation_reason,
                'risk_score': updated_risk_score,
                'escalation_id': escalation_result['escalation_id']
            }
            self.escalation_audit.append(escalation_audit)

            return escalation_result

        except Exception as e:
            logger.error(f"Risk authorization escalation failed: {e}")
            return {
                'escalated': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def _assess_risk_impact(self, impact_assessment: Dict[str, Any]) -> float:
        """
        Assess the risk impact score for an operation

        Args:
            impact_assessment: Risk impact assessment data

        Returns:
            Risk impact score (0-1 scale)
        """
        try:
            # Extract risk factors
            portfolio_impact = impact_assessment.get('portfolio_impact', 0.1)
            volatility_impact = impact_assessment.get('volatility_impact', 0.1)
            liquidity_impact = impact_assessment.get('liquidity_impact', 0.1)
            correlation_impact = impact_assessment.get('correlation_impact', 0.1)

            # Calculate weighted risk score
            risk_score = (
                portfolio_impact * 0.4 +
                volatility_impact * 0.3 +
                liquidity_impact * 0.2 +
                correlation_impact * 0.1
            )

            return min(risk_score, 1.0)  # Cap at 1.0

        except Exception as e:
            logger.error(f"Risk impact assessment failed: {e}")
            return 0.5  # Default medium risk


    def _determine_escalation_target(self, current_level: AuthorizationLevel, reason: str) -> AuthorizationLevel:
        """
        Determine escalation target based on current level and reason

        Args:
            current_level: Current authorization level
            reason: Escalation reason

        Returns:
            Target escalation level
        """
        try:
            escalation_map = {
                AuthorizationLevel.OPERATIONAL: AuthorizationLevel.TACTICAL,
                AuthorizationLevel.TACTICAL: AuthorizationLevel.STRATEGIC,
                AuthorizationLevel.STRATEGIC: AuthorizationLevel.GOVERNANCE_CONTROL,
                AuthorizationLevel.GOVERNANCE_CONTROL: AuthorizationLevel.GOVERNANCE_CONTROL
            }

            # Escalate one level up, or to governance for critical reasons
            if reason in ['risk_threshold_exceeded', 'emergency_condition', 'system_failure']:
                return AuthorizationLevel.GOVERNANCE_CONTROL
            else:
                return escalation_map.get(current_level, AuthorizationLevel.GOVERNANCE_CONTROL)

        except Exception as e:
            logger.error(f"Escalation target determination failed: {e}")
            return AuthorizationLevel.GOVERNANCE_CONTROL

    def _check_risk_limits(self, risk_operation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if operation is within current risk limits

        Args:
            risk_operation: Risk operation details

        Returns:
            Risk limits check result
        """
        try:
            impact_assessment = risk_operation.get('impact_assessment', {})

            # Check portfolio impact limits
            portfolio_impact = impact_assessment.get('portfolio_impact', 0)
            max_portfolio_impact = self.risk_limits.get('max_portfolio_impact', 0.1)

            if portfolio_impact > max_portfolio_impact:
                return {
                    'within_limits': False,
                    'violation_reason': 'portfolio_impact_exceeded',
                    'current_impact': portfolio_impact,
                    'limit': max_portfolio_impact
                }

            # Check position concentration limits
            concentration_impact = impact_assessment.get('concentration_impact', 0)
            max_concentration = self.risk_limits.get('max_position_concentration', 0.2)

            if concentration_impact > max_concentration:
                return {
                    'within_limits': False,
                    'violation_reason': 'concentration_limit_exceeded',
                    'current_concentration': concentration_impact,
                    'limit': max_concentration
                }

            return {
                'within_limits': True,
                'portfolio_impact': portfolio_impact,
                'concentration_impact': concentration_impact
            }

        except Exception as e:
            logger.error(f"Risk limits check failed: {e}")
            return {
                'within_limits': False,
                'violation_reason': 'check_failed',
                'error': str(e)
            }

    async def generate_risk_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive risk report
        
        Returns:
            Detailed risk analysis report
        """
        try:
            # Gather current risk metrics
            risk_metrics = {
                'portfolio_var': getattr(self, 'portfolio_var', 0.0),
                'current_exposure': getattr(self, 'current_exposure', 0.0),
                'risk_limits': self.risk_limits.copy(),
                'active_positions': len(getattr(self, 'active_positions', {})),
                'risk_breaches': getattr(self, 'risk_breaches', []),
                'stress_test_results': getattr(self, 'stress_test_results', {})
            }
            
            # Generate risk assessment
            risk_assessment = {
                'overall_risk_level': 'low',  # Would be calculated based on metrics
                'key_risk_factors': [
                    'Market volatility',
                    'Position concentration',
                    'Liquidity risk',
                    'Counterparty risk'
                ],
                'recommendations': [
                    'Monitor position sizes',
                    'Diversify across sectors',
                    'Maintain liquidity buffers'
                ]
            }
            
            risk_report = {
                'report_type': 'risk_analysis',
                'generation_timestamp': datetime.now().isoformat(),
                'reporting_period': 'current',
                'risk_metrics': risk_metrics,
                'risk_assessment': risk_assessment,
                'compliance_status': 'compliant',  # Would check against regulatory limits
                'action_items': [],  # Would list required actions
                'next_review_date': (datetime.now() + timedelta(days=30)).isoformat()
            }
            
            return risk_report
            
        except Exception as e:
            logger.error(f"Error generating risk report: {e}")
            return {
                'report_type': 'risk_analysis',
                'error': str(e),
                'generation_timestamp': datetime.now().isoformat()
            }


    # ========================================
    # POSITION AUTHORIZATION METHODS
    # ========================================

    async def authorize_position(self, position_request: Dict[str, Any]) -> bool:
        """
        Authorize a position through the central risk management system

        Args:
            position_request: Position authorization request with:
                - symbol: Trading symbol
                - quantity: Position size
                - value: Position value
                - risk_level: Risk assessment

        Returns:
            True if position is authorized
        """
        try:
            # Perform risk assessment
            risk_assessment = self._assess_position_risk(position_request)
            
            # Check against risk limits
            within_limits = self._check_position_limits(position_request)
            
            # Make authorization decision
            authorized = risk_assessment['risk_score'] < 0.7 and within_limits
            
            # Log authorization
            logger.info(f"Position authorization: {position_request.get('symbol', 'unknown')} - {'approved' if authorized else 'rejected'}")
            
            return authorized

        except Exception as e:
            logger.error(f"Position authorization failed: {e}")
            return False

    def _assess_position_risk(self, position_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess risk of a position

        Args:
            position_request: Position details

        Returns:
            Risk assessment
        """
        try:
            value = position_request.get('value', 0)
            quantity = position_request.get('quantity', 0)
            
            # Simple risk scoring based on position size
            risk_score = min(value / 1000000.0, 1.0)  # Scale to 0-1
            
            return {
                'risk_score': risk_score,
                'risk_factors': ['position_size', 'concentration'],
                'assessment_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Position risk assessment failed: {e}")
            return {'risk_score': 1.0, 'error': str(e)}


    # ========================================
    # RISK LIMIT VALIDATION METHODS
    # ========================================

    async def validate_risk_limits(self, portfolio_risk: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate portfolio risk against established limits

        Args:
            portfolio_risk: Portfolio risk metrics with:
                - total_value: Total portfolio value
                - current_exposure: Current risk exposure
                - max_exposure_limit: Maximum allowed exposure
                - var_limit: Value at Risk limit

        Returns:
            Risk limit validation result
        """
        try:
            total_value = portfolio_risk.get('total_value', 0)
            current_exposure = portfolio_risk.get('current_exposure', 0)
            max_exposure_limit = portfolio_risk.get('max_exposure_limit', total_value * 0.2)
            var_limit = portfolio_risk.get('var_limit', total_value * 0.05)

            # Validate exposure limits
            exposure_ratio = current_exposure / total_value if total_value > 0 else 0
            max_exposure_ratio = max_exposure_limit / total_value if total_value > 0 else 0

            within_limits = True
            violations = []

            if exposure_ratio > max_exposure_ratio:
                within_limits = False
                violations.append({
                    'type': 'exposure_limit',
                    'current': exposure_ratio,
                    'limit': max_exposure_ratio,
                    'message': f'Exposure ratio {exposure_ratio:.2%} exceeds limit {max_exposure_ratio:.2%}'
                })

            # Validate VaR limits
            if 'current_var' in portfolio_risk:
                current_var = portfolio_risk['current_var']
                if current_var > var_limit:
                    within_limits = False
                    violations.append({
                        'type': 'var_limit',
                        'current': current_var,
                        'limit': var_limit,
                        'message': f'VaR {current_var:.2f} exceeds limit {var_limit:.2f}'
                    })

            # Additional risk validations
            if 'concentration_limit' in portfolio_risk:
                concentration = portfolio_risk.get('current_concentration', 0)
                conc_limit = portfolio_risk['concentration_limit']
                if concentration > conc_limit:
                    within_limits = False
                    violations.append({
                        'type': 'concentration_limit',
                        'current': concentration,
                        'limit': conc_limit,
                        'message': f'Concentration {concentration:.2%} exceeds limit {conc_limit:.2%}'
                    })

            result = {
                'within_limits': within_limits,
                'violations': violations,
                'exposure_ratio': exposure_ratio,
                'max_exposure_ratio': max_exposure_ratio,
                'validation_timestamp': datetime.now().isoformat(),
                'recommendations': []
            }

            # Generate recommendations if violations exist
            if violations:
                result['recommendations'] = [
                    "Reduce position sizes to comply with exposure limits",
                    "Diversify portfolio to reduce concentration risk",
                    "Implement stricter risk controls"
                ]

            logger.info(f"Risk limit validation: {'passed' if within_limits else 'failed'}")
            return result

        except Exception as e:
            logger.error(f"Risk limit validation failed: {e}")
            return {
                'within_limits': False,
                'error': str(e),
                'validation_timestamp': datetime.now().isoformat()
            }


# Example usage
if __name__ == "__main__":
    async def test_central_risk_manager():
        """Test the central risk manager"""
        
        # Initialize risk manager
        config = {
            'max_position_size': 0.10,
            'auto_approval_threshold': 0.01
        }
        
        risk_manager = CentralRiskManager(config)
        await risk_manager.initialize()
        
        # Create trading decision request
        request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            strategy_id="test_strategy",
            symbol="AAPL",
            side="buy",
            quantity=1000.0,
            expected_return=0.05,
            confidence=0.8,
            market_regime="bull_market",
            regime_confidence=0.9,
            urgency=ExecutionUrgency.NORMAL
        )
        
        # Request authorization
        print("Requesting trading authorization...")
        authorization = await risk_manager.authorize_trading_decision(request)
        
        print(f"Authorization result: {authorization.authorization_level.value}")
        print(f"Authorized quantity: {authorization.authorized_quantity}")
        
        if authorization.authorization_level != AuthorizationLevel.REJECTED:
            # Execute authorized trade
            result = await risk_manager.execute_authorized_trade(authorization)
            print(f"Execution result: {result.status}")
        
        # Get risk status
        status = risk_manager.get_risk_status()
        print(f"Risk status: {status}")


# Example usage
if __name__ == "__main__":
    # Run test
    asyncio.run(test_central_risk_manager())