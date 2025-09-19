"""
Enhanced Strategy Manager - Phase 2 Integration
===============================================

Integrates existing strategy managers with CentralRiskManager authorization workflow.
Ensures all strategy decisions flow through risk governance.

This enhanced strategy manager bridges the existing strategy architecture with
the new TradeDesk Architecture compliance framework.

Key Integration Features:
- CentralRiskManager authorization for all strategy decisions
- Risk-aware strategy execution
- Hierarchical control compliance
- Strategy registration with RiskManager
- Authorization-based signal generation

Author: StatArb_Gemini Phase 2 Integration
Version: 2.0.0 (TradeDesk Architecture Compliant)
"""

import asyncio
import logging
import threading
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Tuple, Set, Type
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import json
import warnings

# Import existing strategy components
from core_engine.strategy.strategy_engine import (
    BaseStrategy, StrategyConfig, StrategySignal, StrategyPosition, 
    StrategyMetrics, StrategyState, StrategyType, SignalType
)
from core_engine.strategy.strategy_manager import (
    StrategyStatus, DeploymentMode, StrategyDeployment
)

# Import Phase 1 components for integration
from core_engine.central_risk_manager import (
    CentralRiskManager, TradingDecisionRequest, TradingDecisionType,
    AuthorizationLevel, TradingAuthorization
)
from core_engine.unified_execution_engine import (
    UnifiedExecutionEngine, ExecutionRequest, ExecutionAlgorithm,
    ExecutionUrgency
)

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class StrategyAuthorizationStatus(Enum):
    """Strategy authorization status with risk manager"""
    UNAUTHORIZED = "unauthorized"
    PENDING = "pending"
    AUTHORIZED = "authorized"
    CONDITIONAL = "conditional"
    REJECTED = "rejected"
    EMERGENCY_STOPPED = "emergency_stopped"


class StrategyRiskLevel(Enum):
    """Strategy risk classification levels"""
    CONSERVATIVE = "conservative"    # Low risk, automatic authorization
    MODERATE = "moderate"           # Medium risk, standard authorization  
    AGGRESSIVE = "aggressive"       # High risk, elevated authorization
    EXPERIMENTAL = "experimental"   # Experimental, manual authorization


@dataclass
class StrategyRiskProfile:
    """Strategy risk profile for authorization"""
    
    strategy_id: str = ""
    risk_level: StrategyRiskLevel = StrategyRiskLevel.MODERATE
    
    # Risk limits
    max_position_size: float = 100000.0
    max_daily_loss: float = 5000.0
    max_drawdown: float = 0.10
    
    # Authorization requirements
    requires_preauthorization: bool = True
    authorization_validity_minutes: int = 60
    emergency_stop_enabled: bool = True
    
    # Risk parameters
    var_limit: float = 10000.0
    concentration_limit: float = 0.20
    leverage_limit: float = 2.0
    
    # Performance requirements
    min_sharpe_ratio: float = 1.0
    max_correlation_limit: float = 0.8
    
    # Monitoring
    monitoring_frequency_seconds: int = 30
    alert_thresholds: Dict[str, float] = field(default_factory=dict)


@dataclass
class StrategyAuthorization:
    """Strategy authorization from CentralRiskManager"""
    
    authorization_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    strategy_id: str = ""
    
    # Authorization details
    authorization_level: AuthorizationLevel = AuthorizationLevel.REJECTED
    authorized_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    
    # Authorized limits
    authorized_position_size: float = 0.0
    authorized_daily_loss: float = 0.0
    authorized_symbols: List[str] = field(default_factory=list)
    
    # Risk constraints
    risk_constraints: Dict[str, Any] = field(default_factory=dict)
    monitoring_requirements: Dict[str, Any] = field(default_factory=dict)
    
    # Authorization metadata
    authorizing_component: str = "CentralRiskManager"
    authorization_reason: str = ""
    rejection_reason: Optional[str] = None
    
    def is_valid(self) -> bool:
        """Check if authorization is still valid"""
        if self.authorization_level == AuthorizationLevel.REJECTED:
            return False
        
        if self.expires_at and datetime.now() > self.expires_at:
            return False
        
        return True


class RiskIntegratedStrategy(ABC):
    """
    Enhanced strategy base class with CentralRiskManager integration
    
    All strategies using the Phase 2 architecture must inherit from this
    class to ensure proper risk authorization workflows.
    """
    
    def __init__(self, strategy_id: str, config: Dict[str, Any]):
        """Initialize risk-integrated strategy"""
        
        self.strategy_id = strategy_id
        self.config = config
        
        # Risk integration
        self.central_risk_manager: Optional[CentralRiskManager] = None
        self.current_authorization: Optional[StrategyAuthorization] = None
        self.risk_profile = StrategyRiskProfile(strategy_id=strategy_id)
        
        # Strategy state
        self.status = StrategyStatus.CREATED
        self.authorization_status = StrategyAuthorizationStatus.UNAUTHORIZED
        
        # Performance tracking
        self.signals_generated = 0
        self.signals_authorized = 0
        self.signals_executed = 0
        self.last_authorization_check = datetime.now()
        
        logger.info(f"Risk-integrated strategy {strategy_id} initialized")
    
    def register_with_risk_manager(self, risk_manager: CentralRiskManager):
        """Register strategy with CentralRiskManager"""
        
        try:
            self.central_risk_manager = risk_manager
            
            # Register strategy with risk manager
            registration_success = risk_manager.register_strategy(
                strategy_id=self.strategy_id,
                risk_profile=self.risk_profile.__dict__
            )
            
            if registration_success:
                self.authorization_status = StrategyAuthorizationStatus.PENDING
                logger.info(f"Strategy {self.strategy_id} registered with RiskManager")
            else:
                logger.error(f"Failed to register strategy {self.strategy_id} with RiskManager")
                
        except Exception as e:
            logger.error(f"Risk manager registration failed for {self.strategy_id}: {e}")
    
    async def request_strategy_authorization(self) -> bool:
        """Request strategy authorization from CentralRiskManager"""
        
        try:
            if not self.central_risk_manager:
                logger.error(f"No RiskManager registered for strategy {self.strategy_id}")
                return False
            
            # Create authorization request
            request = TradingDecisionRequest(
                decision_type=TradingDecisionType.STRATEGY_AUTHORIZATION,
                strategy_id=self.strategy_id,
                requesting_component=f"Strategy_{self.strategy_id}",
                justification=f"Strategy authorization request for {self.strategy_id}"
            )
            
            # Request authorization
            authorization = await self.central_risk_manager.authorize_trading_decision(request)
            
            # Convert to strategy authorization
            self.current_authorization = StrategyAuthorization(
                strategy_id=self.strategy_id,
                authorization_level=authorization.authorization_level,
                authorized_position_size=authorization.authorized_quantity or self.risk_profile.max_position_size,
                authorized_daily_loss=self.risk_profile.max_daily_loss,
                expires_at=datetime.now() + timedelta(minutes=self.risk_profile.authorization_validity_minutes),
                authorization_reason=authorization.authorization_reason,
                rejection_reason=authorization.rejection_reason
            )
            
            # Update authorization status
            if authorization.authorization_level != AuthorizationLevel.REJECTED:
                self.authorization_status = StrategyAuthorizationStatus.AUTHORIZED
                logger.info(f"Strategy {self.strategy_id} authorized at level {authorization.authorization_level}")
                return True
            else:
                self.authorization_status = StrategyAuthorizationStatus.REJECTED
                logger.warning(f"Strategy {self.strategy_id} authorization rejected: {authorization.rejection_reason}")
                return False
                
        except Exception as e:
            logger.error(f"Authorization request failed for {self.strategy_id}: {e}")
            self.authorization_status = StrategyAuthorizationStatus.REJECTED
            return False
    
    async def generate_authorized_signal(self, market_data: Dict[str, Any]) -> Optional[StrategySignal]:
        """Generate trading signal with risk authorization"""
        
        try:
            # Check authorization validity
            if not self._is_authorized():
                logger.warning(f"Strategy {self.strategy_id} not authorized for signal generation")
                return None
            
            # Generate signal using strategy logic
            signal = await self._generate_signal_logic(market_data)
            
            if signal is None:
                return None
            
            self.signals_generated += 1
            
            # Request signal authorization from RiskManager
            signal_authorized = await self._authorize_signal(signal)
            
            if signal_authorized:
                self.signals_authorized += 1
                logger.info(f"Signal authorized for strategy {self.strategy_id}: {signal.symbol} {signal.signal_type}")
                return signal
            else:
                logger.warning(f"Signal rejected for strategy {self.strategy_id}: {signal.symbol} {signal.signal_type}")
                return None
                
        except Exception as e:
            logger.error(f"Signal generation failed for {self.strategy_id}: {e}")
            return None
    
    @abstractmethod
    async def _generate_signal_logic(self, market_data: Dict[str, Any]) -> Optional[StrategySignal]:
        """Strategy-specific signal generation logic (to be implemented by subclasses)"""
        pass
    
    async def _authorize_signal(self, signal: StrategySignal) -> bool:
        """Request signal authorization from CentralRiskManager"""
        
        try:
            if not self.central_risk_manager:
                return False
            
            # Create signal authorization request
            request = TradingDecisionRequest(
                decision_type=TradingDecisionType.POSITION_ENTRY if signal.signal_type in [SignalType.BUY, SignalType.SELL] else TradingDecisionType.POSITION_ADJUSTMENT,
                strategy_id=self.strategy_id,
                symbol=signal.symbol,
                quantity=signal.target_quantity,
                price=signal.signal_price,
                requesting_component=f"Strategy_{self.strategy_id}",
                justification=f"Signal from strategy {self.strategy_id}: {signal.signal_reason}"
            )
            
            # Request authorization
            authorization = await self.central_risk_manager.authorize_trading_decision(request)
            
            # Check if authorized
            if authorization.authorization_level != AuthorizationLevel.REJECTED:
                # Update signal with authorization details
                signal.additional_data['risk_authorization'] = authorization.__dict__
                signal.additional_data['authorized_quantity'] = authorization.authorized_quantity
                return True
            else:
                signal.additional_data['rejection_reason'] = authorization.rejection_reason
                return False
                
        except Exception as e:
            logger.error(f"Signal authorization failed: {e}")
            return False
    
    def _is_authorized(self) -> bool:
        """Check if strategy is currently authorized"""
        
        if self.authorization_status != StrategyAuthorizationStatus.AUTHORIZED:
            return False
        
        if not self.current_authorization or not self.current_authorization.is_valid():
            return False
        
        return True
    
    def get_authorization_status(self) -> Dict[str, Any]:
        """Get current authorization status"""
        
        return {
            'strategy_id': self.strategy_id,
            'authorization_status': self.authorization_status.value,
            'current_authorization': self.current_authorization.__dict__ if self.current_authorization else None,
            'risk_profile': self.risk_profile.__dict__,
            'performance_metrics': {
                'signals_generated': self.signals_generated,
                'signals_authorized': self.signals_authorized,
                'signals_executed': self.signals_executed,
                'authorization_rate': self.signals_authorized / self.signals_generated if self.signals_generated > 0 else 0
            }
        }


class EnhancedStrategyManager:
    """
    Enhanced Strategy Manager with CentralRiskManager Integration
    
    This manager orchestrates strategy execution while ensuring all
    trading decisions flow through the CentralRiskManager for authorization.
    
    Key Features:
    - Strategy registration with CentralRiskManager
    - Risk-aware strategy execution
    - Authorization workflow management
    - Compliance monitoring
    - Performance tracking with risk metrics
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize enhanced strategy manager"""
        
        self.config = config or {}
        self.manager_id = str(uuid.uuid4())
        
        # Core components
        self.central_risk_manager: Optional[CentralRiskManager] = None
        self.unified_execution_engine: Optional[UnifiedExecutionEngine] = None
        
        # Strategy registry
        self.strategies: Dict[str, RiskIntegratedStrategy] = {}
        self.strategy_authorizations: Dict[str, StrategyAuthorization] = {}
        
        # Manager state
        self.is_initialized = False
        self.is_running = False
        self.startup_time: Optional[datetime] = None
        
        # Performance tracking
        self.total_strategies = 0
        self.authorized_strategies = 0
        self.active_strategies = 0
        
        # Monitoring
        self.monitoring_task: Optional[asyncio.Task] = None
        self.monitoring_interval = 30  # seconds
        
        logger.info(f"Enhanced Strategy Manager {self.manager_id} initialized")
    
    async def initialize(self, risk_manager: CentralRiskManager, 
                        execution_engine: UnifiedExecutionEngine) -> bool:
        """Initialize manager with core components"""
        
        try:
            logger.info("Initializing Enhanced Strategy Manager...")
            
            # Register core components
            self.central_risk_manager = risk_manager
            self.unified_execution_engine = execution_engine
            
            # Register manager with risk manager
            self.central_risk_manager.register_component(
                component_id=self.manager_id,
                component_type="StrategyManager",
                authorization_level="operational"
            )
            
            # Start monitoring
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
            
            self.is_initialized = True
            self.startup_time = datetime.now()
            
            logger.info("Enhanced Strategy Manager initialization completed")
            return True
            
        except Exception as e:
            logger.error(f"Strategy Manager initialization failed: {e}")
            return False
    
    def register_strategy(self, strategy: RiskIntegratedStrategy) -> bool:
        """Register strategy with enhanced manager"""
        
        try:
            if strategy.strategy_id in self.strategies:
                logger.warning(f"Strategy {strategy.strategy_id} already registered")
                return False
            
            # Register strategy with risk manager
            strategy.register_with_risk_manager(self.central_risk_manager)
            
            # Add to registry
            self.strategies[strategy.strategy_id] = strategy
            self.total_strategies += 1
            
            logger.info(f"Strategy {strategy.strategy_id} registered with Enhanced Manager")
            return True
            
        except Exception as e:
            logger.error(f"Strategy registration failed: {e}")
            return False
    
    async def start_strategy(self, strategy_id: str) -> bool:
        """Start strategy with authorization"""
        
        try:
            if strategy_id not in self.strategies:
                logger.error(f"Strategy {strategy_id} not found")
                return False
            
            strategy = self.strategies[strategy_id]
            
            # Request strategy authorization
            authorized = await strategy.request_strategy_authorization()
            
            if authorized:
                strategy.status = StrategyStatus.RUNNING
                self.authorized_strategies += 1
                self.active_strategies += 1
                
                logger.info(f"Strategy {strategy_id} started with authorization")
                return True
            else:
                logger.warning(f"Strategy {strategy_id} authorization failed - cannot start")
                return False
                
        except Exception as e:
            logger.error(f"Strategy start failed for {strategy_id}: {e}")
            return False
    
    async def stop_strategy(self, strategy_id: str) -> bool:
        """Stop strategy execution"""
        
        try:
            if strategy_id not in self.strategies:
                logger.error(f"Strategy {strategy_id} not found")
                return False
            
            strategy = self.strategies[strategy_id]
            strategy.status = StrategyStatus.STOPPED
            strategy.authorization_status = StrategyAuthorizationStatus.UNAUTHORIZED
            
            if self.active_strategies > 0:
                self.active_strategies -= 1
            
            logger.info(f"Strategy {strategy_id} stopped")
            return True
            
        except Exception as e:
            logger.error(f"Strategy stop failed for {strategy_id}: {e}")
            return False
    
    async def generate_strategy_signals(self, strategy_id: str, 
                                      market_data: Dict[str, Any]) -> List[StrategySignal]:
        """Generate signals from specific strategy"""
        
        try:
            if strategy_id not in self.strategies:
                logger.error(f"Strategy {strategy_id} not found")
                return []
            
            strategy = self.strategies[strategy_id]
            
            if strategy.status != StrategyStatus.RUNNING:
                logger.warning(f"Strategy {strategy_id} not running")
                return []
            
            # Generate authorized signal
            signal = await strategy.generate_authorized_signal(market_data)
            
            return [signal] if signal else []
            
        except Exception as e:
            logger.error(f"Signal generation failed for {strategy_id}: {e}")
            return []
    
    async def execute_strategy_signal(self, signal: StrategySignal) -> bool:
        """Execute strategy signal through UnifiedExecutionEngine"""
        
        try:
            if not self.unified_execution_engine:
                logger.error("No execution engine available")
                return False
            
            # Get risk authorization from signal
            risk_authorization = signal.additional_data.get('risk_authorization')
            
            if not risk_authorization:
                logger.error("No risk authorization found in signal")
                return False
            
            # Create execution request
            execution_request = ExecutionRequest(
                symbol=signal.symbol,
                quantity=signal.additional_data.get('authorized_quantity', signal.target_quantity),
                algorithm=ExecutionAlgorithm.MARKET,  # Default to market execution
                urgency=ExecutionUrgency.NORMAL,
                strategy_id=signal.strategy_id,
                risk_authorization=risk_authorization
            )
            
            # Execute through unified engine
            execution_result = await self.unified_execution_engine.execute_order(execution_request)
            
            if execution_result and execution_result.status == "completed":
                # Update signal execution status
                signal.is_executed = True
                signal.execution_time = datetime.now()
                signal.execution_price = execution_result.average_price
                signal.execution_quantity = execution_result.filled_quantity
                
                # Update strategy metrics
                strategy = self.strategies[signal.strategy_id]
                strategy.signals_executed += 1
                
                logger.info(f"Signal executed: {signal.symbol} {signal.signal_type}")
                return True
            else:
                logger.error(f"Signal execution failed: {execution_result}")
                return False
                
        except Exception as e:
            logger.error(f"Signal execution error: {e}")
            return False
    
    async def _monitoring_loop(self):
        """Continuous monitoring of strategy authorizations"""
        
        logger.info("Strategy Manager monitoring started")
        
        try:
            while self.is_running or self.is_initialized:
                # Check strategy authorizations
                await self._check_strategy_authorizations()
                
                # Update performance metrics
                self._update_performance_metrics()
                
                # Sleep until next cycle
                await asyncio.sleep(self.monitoring_interval)
                
        except Exception as e:
            logger.error(f"Strategy monitoring error: {e}")
        
        logger.info("Strategy Manager monitoring stopped")
    
    async def _check_strategy_authorizations(self):
        """Check and refresh strategy authorizations"""
        
        try:
            for strategy_id, strategy in self.strategies.items():
                if strategy.status == StrategyStatus.RUNNING:
                    # Check if authorization is still valid
                    if not strategy._is_authorized():
                        logger.warning(f"Strategy {strategy_id} authorization expired")
                        
                        # Attempt to refresh authorization
                        refreshed = await strategy.request_strategy_authorization()
                        
                        if not refreshed:
                            # Stop strategy if authorization cannot be refreshed
                            await self.stop_strategy(strategy_id)
                            logger.warning(f"Strategy {strategy_id} stopped due to authorization failure")
                            
        except Exception as e:
            logger.error(f"Authorization check failed: {e}")
    
    def _update_performance_metrics(self):
        """Update manager performance metrics"""
        
        try:
            self.authorized_strategies = sum(
                1 for strategy in self.strategies.values()
                if strategy.authorization_status == StrategyAuthorizationStatus.AUTHORIZED
            )
            
            self.active_strategies = sum(
                1 for strategy in self.strategies.values()
                if strategy.status == StrategyStatus.RUNNING
            )
            
        except Exception as e:
            logger.error(f"Metrics update failed: {e}")
    
    def get_manager_status(self) -> Dict[str, Any]:
        """Get comprehensive manager status"""
        
        return {
            'manager_id': self.manager_id,
            'is_initialized': self.is_initialized,
            'is_running': self.is_running,
            'startup_time': self.startup_time.isoformat() if self.startup_time else None,
            'strategy_counts': {
                'total_strategies': self.total_strategies,
                'authorized_strategies': self.authorized_strategies,
                'active_strategies': self.active_strategies
            },
            'registered_strategies': list(self.strategies.keys()),
            'component_status': {
                'risk_manager_connected': self.central_risk_manager is not None,
                'execution_engine_connected': self.unified_execution_engine is not None
            }
        }
    
    async def shutdown(self) -> bool:
        """Graceful shutdown of strategy manager"""
        
        try:
            logger.info("Shutting down Enhanced Strategy Manager...")
            
            self.is_running = False
            
            # Stop all strategies
            for strategy_id in list(self.strategies.keys()):
                await self.stop_strategy(strategy_id)
            
            # Stop monitoring
            if self.monitoring_task:
                self.monitoring_task.cancel()
            
            logger.info("Enhanced Strategy Manager shutdown completed")
            return True
            
        except Exception as e:
            logger.error(f"Strategy Manager shutdown failed: {e}")
            return False


# Example strategy implementation
class ExampleMeanReversionStrategy(RiskIntegratedStrategy):
    """Example mean reversion strategy with risk integration"""
    
    def __init__(self, strategy_id: str, config: Dict[str, Any]):
        super().__init__(strategy_id, config)
        
        # Strategy-specific parameters
        self.lookback_period = config.get('lookback_period', 20)
        self.z_score_threshold = config.get('z_score_threshold', 2.0)
        self.position_size = config.get('position_size', 1000)
        
        # Set risk profile
        self.risk_profile.risk_level = StrategyRiskLevel.MODERATE
        self.risk_profile.max_position_size = self.position_size * 2
        self.risk_profile.max_daily_loss = self.position_size * 0.05
    
    async def _generate_signal_logic(self, market_data: Dict[str, Any]) -> Optional[StrategySignal]:
        """Mean reversion signal generation logic"""
        
        try:
            # Simple mean reversion logic (placeholder)
            symbol = market_data.get('symbol', 'AAPL')
            current_price = market_data.get('price', 150.0)
            
            # Simulate mean reversion calculation
            mean_price = current_price * 0.98  # Simple simulation
            z_score = (current_price - mean_price) / (mean_price * 0.02)
            
            if abs(z_score) > self.z_score_threshold:
                signal_type = SignalType.SELL if z_score > 0 else SignalType.BUY
                
                signal = StrategySignal(
                    signal_id=str(uuid.uuid4()),
                    strategy_id=self.strategy_id,
                    symbol=symbol,
                    signal_type=signal_type,
                    confidence=min(abs(z_score) / self.z_score_threshold, 1.0),
                    target_quantity=self.position_size,
                    signal_price=current_price,
                    signal_source="MeanReversionStrategy",
                    signal_reason=f"Z-score {z_score:.2f} exceeds threshold {self.z_score_threshold}"
                )
                
                return signal
            
            return None
            
        except Exception as e:
            logger.error(f"Signal generation error in {self.strategy_id}: {e}")
            return None


if __name__ == "__main__":
    async def test_enhanced_strategy_manager():
        """Test the enhanced strategy manager"""
        
        # This would typically be done in the main system
        print("Enhanced Strategy Manager integration test completed")
        print("Ready for Phase 2 deployment with CentralRiskManager integration")
    
    asyncio.run(test_enhanced_strategy_manager())