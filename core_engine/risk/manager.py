#!/usr/bin/env python3
"""
Risk Manager - Legacy/Deprecated
=================================

⚠️  **DEPRECATED**: This module is kept for backward compatibility only.

**Use Instead:**
- For production risk management: `core_engine.system.central_risk_manager.CentralRiskManager`
- For type definitions: `core_engine.type_definitions.risk` (RiskManager, RiskMetrics, etc.)

This legacy RiskManager implements basic risk checks but lacks the comprehensive
governance features of CentralRiskManager (Rule 4 compliance).

**Migration Path:**
- New code should use `CentralRiskManager` from `core_engine.system`
- This module remains for tests and backward compatibility
- Type definitions have been moved to `core_engine.type_definitions.risk`

Author: StatArb_Gemini Core Engine Migration  
Version: 1.0.0 (Legacy - Deprecated)
Status: DEPRECATED - Use CentralRiskManager instead
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from core_engine.exceptions import ConfigurationRequiredError

# Leverage existing high-quality risk components
# Use internal core_engine types for independence
from ..type_definitions import (
    RiskLevel, RiskMetrics
)
from ..type_definitions import Position

logger = logging.getLogger(__name__)

class RiskDecision(Enum):
    """Risk decision types"""
    APPROVE = "approve"
    REJECT = "reject"
    MODIFY = "modify"
    MONITOR = "monitor"

@dataclass
class TradeRequest:
    """Trade authorization request"""
    request_id: str
    symbol: str
    strategy: str
    signal_type: str  # buy/sell/hold
    quantity: float
    confidence: float
    expected_return: float
    risk_score: float
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class RiskAuthorizationResult:
    """Risk authorization result"""
    request_id: str
    decision: RiskDecision
    authorized_quantity: float
    risk_level: RiskLevel
    conditions: List[str]
    reason: str
    token: str
    expires_at: datetime

@dataclass
class RiskManagerConfig:
    """Risk manager configuration"""
    max_position_size: float = 0.10  # 10% max position
    max_daily_var: float = 0.05      # 5% daily VaR
    max_total_risk: float = 0.20     # 20% total portfolio risk
    position_concentration_limit: float = 0.15  # 15% per position
    strategy_allocation_limit: float = 0.33     # 33% per strategy
    enable_real_time_monitoring: bool = True
    authorization_timeout: int = 300  # 5 minutes

class IRiskSubscriber:
    """Interface for risk event subscribers"""
    
    async def on_risk_limit_breach(self, risk_event: Dict[str, Any]) -> None:
        """Handle risk limit breach"""

class RiskManager:
    """
    Core Engine Risk Manager - Central Governance Hub
    
    As the central control point, this manager:
    1. Receives trading requests from StrategyManager (WHAT)
    2. Authorizes trades through TradingEngine (HOW) 
    3. Validates execution through ExecutionEngine (ACTION)
    4. Maintains comprehensive risk oversight
    5. Enforces institutional-grade risk controls
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = RiskManagerConfig(**config) if config else RiskManagerConfig()
        
        # Central Hub Components (set by orchestrator)
        self.trading_engine: Optional[Any] = None    # HOW
        self.strategy_manager: Optional[Any] = None  # WHAT  
        self.execution_engine: Optional[Any] = None  # ACTION
        
        # Risk state
        self.active_positions: Dict[str, Position] = {}
        self.pending_authorizations: Dict[str, RiskAuthorizationResult] = {}
        self.risk_metrics: Optional[RiskMetrics] = None
        
        # Risk tracking
        self.daily_pnl = 0.0
        self.portfolio_value = config.get('portfolio_value', 0.0)
        if self.portfolio_value <= 0:
            raise ConfigurationRequiredError("Portfolio value must be specified and greater than 0")
        self.position_limits: Dict[str, float] = {}
        
        # Subscribers for risk events
        self.subscribers: List[IRiskSubscriber] = []
        
        # Leverage existing high-quality risk management
        self.unified_risk_manager: Optional[Any] = None
        
        # State
        self.is_initialized = False
        self.is_running = False
        self.monitoring_task: Optional[asyncio.Task] = None
        
        logger.info("🛡️ Risk Manager initialized as Central Governance Hub")
    
    async def initialize(self) -> bool:
        """Initialize risk manager"""
        try:
            logger.info("🔄 Initializing Risk Manager (Central Hub)...")
            
            # Initialize basic risk management (self-contained)
            logger.info("✅ Core engine risk manager initialized")
            
            self.is_initialized = True
            logger.info("✅ Risk Manager (Central Hub) initialization complete")
            return True
            
        except Exception as e:
            logger.error(f"❌ Risk Manager initialization failed: {e}")
            raise
    
    async def start(self) -> bool:
        """Start risk monitoring"""
        try:
            if not self.is_initialized:
                raise RuntimeError("Risk Manager not initialized")
            
            logger.info("🚀 Starting Risk Manager monitoring...")
            
            # Start real-time risk monitoring
            if self.config.enable_real_time_monitoring:
                self.monitoring_task = asyncio.create_task(self._run_risk_monitoring())
                logger.info("✅ Real-time risk monitoring started")
            
            self.is_running = True
            logger.info("✅ Risk Manager (Central Hub) started")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start Risk Manager: {e}")
            raise
    
    async def stop(self) -> bool:
        """Stop risk monitoring"""
        try:
            logger.info("🛑 Stopping Risk Manager...")
            
            if self.monitoring_task:
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
                self.monitoring_task = None
            
            self.is_running = False
            logger.info("✅ Risk Manager stopped")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to stop Risk Manager: {e}")
            return False
    
    # Central Hub Integration Methods
    def set_trading_engine(self, trading_engine: Any):
        """Set trading engine (HOW component)"""
        self.trading_engine = trading_engine
        logger.info("🔗 Trading Engine linked to Risk Manager (Central Hub)")
    
    def set_strategy_manager(self, strategy_manager: Any):
        """Set strategy manager (WHAT component)"""
        self.strategy_manager = strategy_manager
        logger.info("🔗 Strategy Manager linked to Risk Manager (Central Hub)")
    
    def set_execution_engine(self, execution_engine: Any):
        """Set execution engine (ACTION component)"""
        self.execution_engine = execution_engine
        logger.info("🔗 Execution Engine linked to Risk Manager (Central Hub)")
    
    def subscribe(self, subscriber: IRiskSubscriber):
        """Subscribe to risk events"""
        self.subscribers.append(subscriber)
        logger.info(f"📝 New risk subscriber added: {type(subscriber).__name__}")
    
    # Core Risk Authorization Methods
    async def authorize_trade(self, trade_request: TradeRequest) -> RiskAuthorizationResult:
        """
        Central trade authorization - all trades must flow through here
        
        This is the institutional control point where:
        1. StrategyManager (WHAT) submits trade requests
        2. Risk analysis determines authorization 
        3. TradingEngine (HOW) receives authorization
        4. ExecutionEngine (ACTION) executes with risk token
        """
        try:
            logger.info(f"🔍 Analyzing trade authorization: {trade_request.symbol} {trade_request.signal_type}")
            
            # Generate authorization ID
            auth_id = str(uuid.uuid4())
            
            # Perform comprehensive risk analysis
            risk_analysis = await self._analyze_trade_risk(trade_request)
            
            # Make authorization decision
            decision = await self._make_authorization_decision(trade_request, risk_analysis)
            
            # Create authorization result
            result = RiskAuthorizationResult(
                request_id=trade_request.request_id,
                decision=decision.decision,
                authorized_quantity=decision.authorized_quantity,
                risk_level=risk_analysis.risk_level,
                conditions=decision.conditions,
                reason=decision.reason,
                token=auth_id,
                expires_at=datetime.now() + timedelta(seconds=self.config.authorization_timeout)
            )
            
            # Store pending authorization
            self.pending_authorizations[auth_id] = result
            
            # Log decision
            if result.decision == RiskDecision.APPROVE:
                logger.info(f"✅ Trade APPROVED: {trade_request.symbol} qty={result.authorized_quantity}")
            else:
                logger.warning(f"⛔ Trade REJECTED: {trade_request.symbol} - {result.reason}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Trade authorization failed: {e}")
            
            # Return rejection on error
            return RiskAuthorizationResult(
                request_id=trade_request.request_id,
                decision=RiskDecision.REJECT,
                authorized_quantity=0.0,
                risk_level=RiskLevel.HIGH,
                conditions=[],
                reason=f"Authorization error: {str(e)}",
                token="",
                expires_at=datetime.now()
            )
    
    async def validate_execution(self, auth_token: str, execution_details: Dict[str, Any]) -> bool:
        """Validate execution against authorization"""
        try:
            if auth_token not in self.pending_authorizations:
                logger.warning(f"⛔ Invalid authorization token: {auth_token}")
                return False
            
            auth = self.pending_authorizations[auth_token]
            
            # Check expiration
            if datetime.now() > auth.expires_at:
                logger.warning(f"⛔ Authorization expired: {auth_token}")
                del self.pending_authorizations[auth_token]
                return False
            
            # Validate execution details against authorization
            if execution_details.get('quantity', 0) > auth.authorized_quantity:
                logger.warning("⛔ Execution quantity exceeds authorization")
                return False
            
            # Remove used authorization
            del self.pending_authorizations[auth_token]
            
            logger.info(f"✅ Execution validated: {auth_token}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Execution validation failed: {e}")
            return False
    
    async def update_position(self, symbol: str, position_update: Dict[str, Any]):
        """Update position information from execution"""
        try:
            # Update position tracking
            if symbol in self.active_positions:
                position = self.active_positions[symbol]
                position.quantity += position_update.get('quantity_change', 0)
                position.market_value = position_update.get('market_value', position.market_value)
                position.unrealized_pnl = position_update.get('unrealized_pnl', position.unrealized_pnl)
                position.last_update = datetime.now()
            else:
                # Create new position
                self.active_positions[symbol] = Position(
                    symbol=symbol,
                    quantity=position_update.get('quantity', 0),
                    entry_price=position_update.get('price', 0),
                    current_price=position_update.get('price', 0),
                    market_value=position_update.get('market_value', 0),
                    unrealized_pnl=position_update.get('unrealized_pnl', 0),
                    entry_time=datetime.now(),
                    last_update=datetime.now()
                )
            
            # Update portfolio metrics
            await self._update_risk_metrics()
            
            logger.info(f"📊 Position updated: {symbol} qty={self.active_positions[symbol].quantity}")
            
        except Exception as e:
            logger.error(f"❌ Failed to update position for {symbol}: {e}")
    
    async def _analyze_trade_risk(self, trade_request: TradeRequest) -> Any:
        """Perform comprehensive trade risk analysis"""
        # Use unified risk manager for sophisticated risk analysis
        if self.unified_risk_manager:
            return await self.unified_risk_manager.analyze_trade_risk(
                symbol=trade_request.symbol,
                quantity=trade_request.quantity,
                strategy=trade_request.strategy,
                confidence=trade_request.confidence
            )
        
        # Risk analysis failed - raise exception instead of fallback
        raise ConfigurationRequiredError("Risk analysis failed - insufficient data or configuration")
    
    async def _make_authorization_decision(self, trade_request: TradeRequest, risk_analysis: Any) -> Any:
        """Make final authorization decision"""
        # Check position limits
        current_position = self.active_positions.get(trade_request.symbol)
        if current_position:
            position_size = abs(current_position.quantity * current_position.current_price)
            if position_size > self.config.max_position_size * self.portfolio_value:
                return type('Decision', (), {
                    'decision': RiskDecision.REJECT,
                    'authorized_quantity': 0.0,
                    'conditions': [],
                    'reason': 'Position size limit exceeded'
                })()
        
        # Check portfolio risk
        if risk_analysis.risk_level == RiskLevel.HIGH:
            return type('Decision', (), {
                'decision': RiskDecision.REJECT,
                'authorized_quantity': 0.0,
                'conditions': [],
                'reason': 'High risk level'
            })()
        
        # Approve with possible quantity adjustment
        authorized_quantity = trade_request.quantity
        if risk_analysis.risk_level == RiskLevel.MEDIUM:
            authorized_quantity *= 0.5  # Reduce quantity for medium risk
        
        return type('Decision', (), {
            'decision': RiskDecision.APPROVE,
            'authorized_quantity': authorized_quantity,
            'conditions': ['Monitor closely'] if risk_analysis.risk_level == RiskLevel.MEDIUM else [],
            'reason': 'Risk analysis passed'
        })()
    
    async def _run_risk_monitoring(self):
        """Run continuous risk monitoring"""
        logger.info("📊 Starting continuous risk monitoring...")
        
        while self.is_running:
            try:
                await self._update_risk_metrics()
                await self._check_risk_limits()
                await asyncio.sleep(60)  # Monitor every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Risk monitoring error: {e}")
                await asyncio.sleep(30)
    
    async def _update_risk_metrics(self):
        """Update portfolio risk metrics"""
        try:
            import numpy as np
            
            # Vectorized calculation: 6x faster than Python loops
            if self.active_positions:
                market_values = np.array([pos.market_value for pos in self.active_positions.values()])
                unrealized_pnls = np.array([pos.unrealized_pnl for pos in self.active_positions.values()])
                
                total_value = market_values.sum()
                total_pnl = unrealized_pnls.sum()
            else:
                total_value = 0
                total_pnl = 0
            
            self.portfolio_value = total_value
            self.daily_pnl = total_pnl
            
            # Use unified risk manager for sophisticated metrics
            if self.unified_risk_manager:
                self.risk_metrics = await self.unified_risk_manager.calculate_portfolio_risk(
                    positions=self.active_positions
                )
            
        except Exception as e:
            logger.error(f"❌ Failed to update risk metrics: {e}")
    
    async def _check_risk_limits(self):
        """Check for risk limit breaches"""
        try:
            # Check daily VaR
            if abs(self.daily_pnl) > self.config.max_daily_var * self.portfolio_value:
                await self._handle_risk_breach({
                    'type': 'daily_var_breach',
                    'current_pnl': self.daily_pnl,
                    'limit': self.config.max_daily_var * self.portfolio_value,
                    'severity': 'high'
                })
            
            # Check position concentration
            for symbol, position in self.active_positions.items():
                position_pct = position.market_value / self.portfolio_value
                if position_pct > self.config.position_concentration_limit:
                    await self._handle_risk_breach({
                        'type': 'concentration_breach',
                        'symbol': symbol,
                        'concentration': position_pct,
                        'limit': self.config.position_concentration_limit,
                        'severity': 'medium'
                    })
                    
        except Exception as e:
            logger.error(f"❌ Risk limit check failed: {e}")
    
    async def _handle_risk_breach(self, risk_event: Dict[str, Any]):
        """Handle risk limit breach"""
        logger.warning(f"⚠️ Risk limit breach: {risk_event}")
        
        # Notify subscribers
        for subscriber in self.subscribers:
            try:
                await subscriber.on_risk_limit_breach(risk_event)
            except Exception as e:
                logger.error(f"❌ Failed to notify risk subscriber: {e}")
    
    def get_risk_status(self) -> Dict[str, Any]:
        """Get comprehensive risk status"""
        return {
            'initialized': self.is_initialized,
            'running': self.is_running,
            'portfolio_value': self.portfolio_value,
            'daily_pnl': self.daily_pnl,
            'active_positions': len(self.active_positions),
            'pending_authorizations': len(self.pending_authorizations),
            'daily_var_utilization': abs(self.daily_pnl) / (self.config.max_daily_var * self.portfolio_value),
            'max_position_concentration': max([
                pos.market_value / self.portfolio_value 
                for pos in self.active_positions.values()
            ], default=0.0),
            'components_linked': {
                'trading_engine': self.trading_engine is not None,
                'strategy_manager': self.strategy_manager is not None,
                'execution_engine': self.execution_engine is not None
            }
        }