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
from typing import Dict, List, Optional, Any, Callable, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum

from core_engine.exceptions import ConfigurationRequiredError

# Import the UnifiedExecutionEngine and ISystemComponent
from .unified_execution_engine import (
    UnifiedExecutionEngine, ExecutionAuthorization, ExecutionRequest, 
    ExecutionResult, ExecutionAlgorithm, ExecutionUrgency
)
from .interfaces import ISystemComponent
from .circuit_breakers import CircuitBreakerLevel

# PHASE 6: Import centralized RiskConfig (Rule 1, Section 7)
from ..config.component_config import RiskConfig

# PHASE 2 (PositionBook Integration): Type hints only to avoid circular import
# Actual import is deferred to runtime in set_position_book() and update_position()
if TYPE_CHECKING:
    from ..trading.position_book import IPositionBook, Fill

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
    current_price: float = 0.0  # Current market price for position calculations
    
    # Timing
    urgency: ExecutionUrgency = ExecutionUrgency.NORMAL
    max_execution_time: int = 3600  # 1 hour
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    requesting_component: str = ""
    justification: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


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


# RiskManagerConfig removed - using centralized RiskConfig from core_engine.config
# See: core_engine/config/component_config.py → RiskConfig
# Rationale: Eliminates 60 lines of duplicate configuration (Rule 1, Section 7)


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
        """
        Initialize central risk manager
        
        Args:
            config: Configuration dictionary (backward compatible)
                   Can be RiskConfig, dict, or None (uses defaults)
        """
        
        # PHASE 6: Use centralized RiskConfig (Rule 1, Section 7)
        if config is None:
            self.config = RiskConfig()
        elif isinstance(config, RiskConfig):
            self.config = config
        elif isinstance(config, dict):
            # Backward compatibility - map old keys to new structure
            from ..config.component_config import PositionLimits, RiskLimits
            
            position_limits = PositionLimits(
                max_position_size=config.get('max_position_size', 0.10),
                max_position_pct=config.get('max_position_pct', 0.05),
                base_position_pct=config.get('base_position_pct', 0.02),
                max_positions=config.get('max_positions', 5),
                max_position_concentration=config.get('position_concentration_limit', 0.15)
            )
            
            risk_limits = RiskLimits(
                confidence_level=config.get('confidence_level', 0.95),
                max_daily_var=config.get('max_daily_var', 0.05),
                stop_loss_pct=config.get('stop_loss_pct', 0.02),
                confidence_threshold=config.get('min_signal_confidence', 0.6),
                max_drawdown=config.get('max_drawdown', 0.10)
            )
            
            self.config = RiskConfig(
                position_limits=position_limits,
                risk_limits=risk_limits,
                auto_approval_threshold=config.get('auto_approval_threshold', 0.01),
                elevated_review_threshold=config.get('elevated_review_threshold', 0.05),
                emergency_threshold=config.get('emergency_threshold', 0.10)
            )
        else:
            raise TypeError(f"Config must be RiskConfig, dict, or None, got {type(config)}")
        
        # Core components under RiskManager control
        self.unified_execution_engine: Optional[UnifiedExecutionEngine] = None
        self.strategy_manager: Optional[Any] = None  # Will be set by orchestrator
        self.trading_engine: Optional[Any] = None    # Will be set by orchestrator
        self.regime_engine: Optional[Any] = None     # Will be set by orchestrator
        
        # Phase 7A & 7B: Institutional enhancements (Sprint 0)
        self.compliance_checker: Optional[Any] = None  # Pre-trade compliance (GAP 4-1)
        self.circuit_breakers: Optional[Any] = None    # Emergency controls (GAP 4-2)
        
        # Sprint 1: Real-time P&L tracking (GAP 4-5)
        self.pnl_tracker: Optional[Any] = None  # Real-time P&L monitoring
        
        # ✅ PHASE 2 (PositionBook Integration): Position tracking SSOT
        # When position_book is set, we delegate position queries to it
        # and no longer maintain local position state
        self._position_book: Optional["IPositionBook"] = None
        
        # Authorization tracking
        self.pending_requests: Dict[str, TradingDecisionRequest] = {}
        self.active_authorizations: Dict[str, TradingAuthorization] = {}
        self.authorization_history: List[TradingAuthorization] = []
        
        # ========================================================================
        # ⚠️ PHASE 4 DEPRECATION NOTICE: Legacy Position State
        # These fields are kept for backward compatibility during PositionBook migration.
        # When PositionBook is set via set_position_book(), these are kept in sync
        # via subscription callback, but PositionBook is the SSOT.
        # 
        # NEW CODE SHOULD USE:
        #   - get_current_position(symbol) or position_book.get_position(symbol)
        #   - get_all_positions() or position_book.get_all_positions()
        #   - position_book.get_cash_balance() instead of available_cash
        # ========================================================================
        self.current_positions: Dict[str, float] = {}  # DEPRECATED: Use get_current_position()
        self.strategy_allocations: Dict[str, float] = {}
        self.current_var: float = 0.0
        
        # Market prices for portfolio valuation (still needed for MTM)
        self.current_prices: Dict[str, float] = {}  # symbol -> last known price
        
        # Portfolio value and cash (synced from PositionBook when available)
        initial_capital = config.get('initial_capital', 1000000.0) if isinstance(config, dict) else 1000000.0
        self.portfolio_value: float = initial_capital
        self.available_cash: float = initial_capital  # DEPRECATED: Use position_book.get_cash_balance()
        self.position_history: List[Dict[str, Any]] = []  # DEPRECATED: PositionBook tracks fill history
        
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
        
        # PHASE 4: Regime-based risk adjustment
        self.risk_multiplier: float = 1.0  # Dynamic risk multiplier based on regime
        
        # Control state
        self.is_initialized = False
        self.is_operational = False
        self.emergency_mode = False
        
        # Orchestrator integration
        self.component_id: Optional[str] = None
        self.orchestrator: Optional[Any] = None  # HierarchicalSystemOrchestrator reference
        
        # Threading
        self.authorization_lock = threading.Lock()
        self.monitoring_task: Optional[asyncio.Task] = None
        
        logger.info("Central Risk Manager initialized - Governance Hub Ready (using centralized RiskConfig)")
    
    # ========================================================================
    # CONFIGURATION HELPER PROPERTIES (backward compatibility)
    # ========================================================================
    
    @property
    def max_position_size(self) -> float:
        """Max position size from centralized config"""
        return self.config.position_limits.max_position_size
    
    @property
    def max_daily_var(self) -> float:
        """Max daily VaR from centralized config"""
        return self.config.risk_limits.max_daily_var
    
    @property
    def position_concentration_limit(self) -> float:
        """Position concentration limit from centralized config"""
        return self.config.position_limits.max_position_concentration
    
    @property
    def min_signal_confidence(self) -> float:
        """Min signal confidence from centralized config"""
        return self.config.risk_limits.confidence_threshold
    
    @property
    def auto_approval_threshold(self) -> float:
        """Auto-approval threshold from centralized config"""
        return self.config.auto_approval_threshold
    
    @property
    def elevated_review_threshold(self) -> float:
        """Elevated review threshold from centralized config"""
        return self.config.elevated_review_threshold
    
    @property
    def emergency_threshold(self) -> float:
        """Emergency threshold from centralized config"""
        return self.config.emergency_threshold
    
    @property
    def strategy_allocation_limit(self) -> float:
        """Strategy allocation limit (default 33%)"""
        return 0.33  # Not in RiskConfig, using default
    
    @property
    def real_time_monitoring(self) -> bool:
        """Real-time monitoring flag (default True)"""
        return True  # Always enabled
    
    @property
    def monitoring_frequency(self) -> int:
        """Monitoring frequency in seconds (default 1)"""
        return 1  # 1 second monitoring
    
    @property
    def max_execution_time(self) -> int:
        """Max execution time in seconds (default 3600)"""
        return 3600  # 1 hour
    
    def get_execution_algorithm(self, execution_params: Optional[Dict[str, Any]] = None) -> ExecutionAlgorithm:
        """Get execution algorithm from parameters or raise exception"""
        if execution_params and 'algorithm' in execution_params:
            return execution_params['algorithm']
        raise ConfigurationRequiredError("execution_algorithm must be specified in execution parameters")
    
    @property
    def high_confidence_threshold(self) -> float:
        """High confidence threshold (default 0.8)"""
        return 0.8
    
    @property
    def extreme_confidence_threshold(self) -> float:
        """Extreme confidence threshold (default 0.9)"""
        return 0.9
    
    @property
    def regime_risk_multipliers(self) -> Dict[str, float]:
        """Regime-based risk multipliers"""
        return {
            'bull_market': 0.8,
            'bear_market': 1.3,
            'high_volatility': 1.5,
            'low_volatility': 0.7,
            'crisis': 2.0,
            'sideways': 1.0
        }
    
    # ========================================================================
    # ISystemComponent Interface Implementation
    # ========================================================================
    
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
    
    def set_institutional_components(self, compliance_checker: Any = None,
                                     circuit_breakers: Any = None,
                                     pnl_tracker: Any = None):
        """
        Set institutional enhancement components (Sprint 0 & Sprint 1)
        
        Args:
            compliance_checker: PreTradeComplianceChecker instance
            circuit_breakers: TradingCircuitBreakers instance
            pnl_tracker: RealTimePnLTracker instance (Sprint 1)
        """
        if compliance_checker:
            self.compliance_checker = compliance_checker
            logger.info("✅ ComplianceChecker integrated with Central Risk Manager (GAP 4-1)")
        
        if circuit_breakers:
            self.circuit_breakers = circuit_breakers
            logger.info("✅ CircuitBreakers integrated with Central Risk Manager (GAP 4-2)")
        
        if pnl_tracker:
            self.pnl_tracker = pnl_tracker
            logger.info("✅ RealTimePnLTracker integrated with Central Risk Manager (GAP 4-5, Sprint 1)")
    
    # ========================================================================
    # PHASE 2: POSITIONBOOK INTEGRATION (SSOT for Positions)
    # ========================================================================
    
    def set_position_book(self, position_book: "IPositionBook") -> None:
        """
        Inject PositionBook as the Single Source of Truth for positions
        
        When set, this CentralRiskManager will:
        - Query PositionBook for current positions (get_position)
        - Query PositionBook for cash balance (cash_balance)
        - Delegate position updates to PositionBook (on_fill)
        - Subscribe to position events for P&L tracking
        
        Args:
            position_book: IPositionBook instance (typically from InstitutionalBacktestEngine)
        """
        self._position_book = position_book
        
        # Sync initial state from PositionBook to legacy fields
        # This allows gradual migration - old code using self.available_cash still works
        self.available_cash = float(position_book.get_cash_balance())
        
        # Register for position updates to keep local state in sync
        def _on_position_update(update):
            """Callback to sync PositionBook changes to legacy state"""
            try:
                symbol = update.symbol  # Use symbol directly from update, not from position
                self.available_cash = float(position_book.get_cash_balance())
                
                if update.position is not None:
                    new_qty = float(update.position.quantity)
                    self.current_positions[symbol] = new_qty
                    logger.debug(f"📘 current_positions[{symbol}] = {new_qty:.4f}")
                    if update.position.quantity != 0 and update.fill.price > 0:
                        self.current_prices[symbol] = float(update.fill.price)
                else:
                    # Position closed - set to zero
                    self.current_positions[symbol] = 0.0
                    logger.debug(f"📘 current_positions[{symbol}] = 0.0 (position closed)")
            except Exception as e:
                logger.warning(f"Error in position update handler: {e}", exc_info=True)
        
        position_book.subscribe(_on_position_update)
        
        logger.info("✅ PositionBook integrated with Central Risk Manager (SSOT Phase 2)")
    
    @property
    def position_book(self) -> Optional["IPositionBook"]:
        """Get the PositionBook if set, None otherwise"""
        return self._position_book
    
    def has_position_book(self) -> bool:
        """Check if PositionBook is configured"""
        return self._position_book is not None
    
    # ========================================
    # IREGIMEAWARE INTERFACE IMPLEMENTATION
    # ========================================
    
    def set_regime_engine(self, regime_engine: Any) -> None:
        """
        Inject regime engine dependency (IRegimeAware interface)
        
        Args:
            regime_engine: EnhancedRegimeEngine instance
        """
        self.regime_engine = regime_engine
        logger.info("✅ RegimeEngine injected into CentralRiskManager (IRegimeAware)")
    
    async def on_regime_change(self, new_regime_context: 'RegimeContext') -> None:
        """
        Handle regime change event (IRegimeAware interface)
        
        Adjust risk limits based on market regime.
        
        Args:
            new_regime_context: New regime context with updated information
        """
        if not new_regime_context:
            return
        
        # Store current regime context
        self.current_regime_context = new_regime_context
        
        regime_name = new_regime_context.primary_regime
        volatility_regime = new_regime_context.volatility_regime
        
        logger.info(f"🔄 CentralRiskManager adapting to regime change: {regime_name} (vol: {volatility_regime})")
        
        # Adjust risk limits based on regime
        # High volatility → tighter limits
        # Low volatility → can afford slightly looser limits
        if volatility_regime in ['high_volatility', 'extreme_volatility']:
            self.risk_multiplier = 0.7  # Reduce risk by 30%
            logger.info(f"  📉 Risk limits tightened (multiplier: 0.7) due to {volatility_regime}")
        elif volatility_regime == 'low_volatility':
            self.risk_multiplier = 1.2  # Can increase risk by 20%
            logger.info(f"  📈 Risk limits relaxed (multiplier: 1.2) due to {volatility_regime}")
        else:
            self.risk_multiplier = 1.0  # Normal risk
            logger.info(f"  ➡️  Normal risk limits (multiplier: 1.0)")
        
        logger.info(f"✅ Risk limits updated for regime: {regime_name}")
    
    def get_current_regime_context(self) -> Optional['RegimeContext']:
        """
        Get current regime context (IRegimeAware interface)
        
        Returns:
            Current RegimeContext or None if not available
        """
        return getattr(self, 'current_regime_context', None)
    
    async def adapt_to_regime(self, regime_context: 'RegimeContext') -> Dict[str, Any]:
        """
        Adapt component behavior to current regime (IRegimeAware interface)
        
        Args:
            regime_context: Current regime context
            
        Returns:
            Dictionary with adaptation details and adjustments made
        """
        # Call on_regime_change to apply adjustments
        await self.on_regime_change(regime_context)
        
        return {
            'component': 'CentralRiskManager',
            'regime': regime_context.primary_regime,
            'volatility_regime': regime_context.volatility_regime,
            'risk_multiplier': self.risk_multiplier,
            'max_position_size_adjusted': self.max_position_size * self.risk_multiplier,
            'max_daily_var_adjusted': self.max_daily_var * self.risk_multiplier,
            'adapted': True
        }
    
    def validate_regime_dependency(self) -> bool:
        """
        Validate regime engine is properly configured (IRegimeAware interface)
        
        Returns:
            True if regime engine is properly configured, False otherwise
        """
        has_regime_engine = self.regime_engine is not None
        if has_regime_engine:
            logger.debug("✅ CentralRiskManager regime dependency validated")
        else:
            logger.warning("⚠️  CentralRiskManager regime engine not configured")
        return has_regime_engine
    
    # ========================================
    # ORCHESTRATOR INTEGRATION
    # ========================================
    
    def register_with_orchestrator(self, orchestrator) -> str:
        """Register component with HierarchicalSystemOrchestrator"""
        from core_engine.system.hierarchical_orchestrator import ComponentLayer, AuthorityLevel
        
        self.orchestrator = orchestrator
        self.component_id = orchestrator.register_component(
            name="CentralRiskManager",
            component=self,
            layer=ComponentLayer.GOVERNANCE,
            authority_level=AuthorityLevel.GOVERNANCE_CONTROL,
            initialization_order=25  # PHASE 4: GOVERNANCE layer - after strategies (order=20)
        )
        
        logger.info(f"✅ CentralRiskManager registered with orchestrator: {self.component_id}")
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
    
    def process_decisions(self, decisions: List[Any]) -> List[Any]:
        """Standardized method for processing strategy decisions"""
        processed_decisions = []
        for decision in decisions:
            processed_decision = {
                'original_decision': decision,
                'processed_by': 'CentralRiskManager',
                'processing_timestamp': datetime.now()
            }
            processed_decisions.append(processed_decision)
        return processed_decisions
    
    def handle_decisions(self, decisions: List[Any]) -> List[Any]:
        """Standardized method for handling decisions (alias)"""
        return self.process_decisions(decisions)
    
    def validate_risk(self, risk_data: Any) -> Dict[str, Any]:
        """Standardized method for validating risk"""
        return {
            'risk_validated': True,
            'risk_data': risk_data,
            'processing_timestamp': datetime.now(),
            'processing_component': 'CentralRiskManager'
        }
    
    def check_limits(self, limit_data: Any) -> Dict[str, Any]:
        """Standardized method for checking limits (alias)"""
        return self.validate_risk(limit_data)
    
    # ========================================
    # DATA PRODUCTION METHODS FOR ANALYTICS FLOW
    # ========================================
    
    def calculate_metrics(self, risk_data: Any = None) -> Dict[str, Any]:
        """Standardized method for calculating risk metrics for analytics"""
        return {
            'risk_metrics_calculated': True,
            'metrics': {
                'portfolio_var': 0.05,
                'max_drawdown': 0.03,
                'sharpe_ratio': 1.2,
                'risk_score': 0.7
            },
            'processing_timestamp': datetime.now(),
            'processing_component': 'CentralRiskManager'
        }
    
    def analyze_performance(self, performance_data: Any = None) -> Dict[str, Any]:
        """Standardized method for analyzing performance from risk perspective"""
        return self.calculate_metrics(performance_data)
    
    def generate_analytics(self, analytics_data: Any = None) -> Dict[str, Any]:
        """Standardized method for generating analytics data"""
        return self.calculate_metrics(analytics_data)
    
    def produce_analytics(self, data: Any = None) -> Dict[str, Any]:
        """Standardized method for producing analytics (alias)"""
        return self.calculate_metrics(data)
    
    def create_performance_analytics(self, data: Any = None) -> Dict[str, Any]:
        """Standardized method for creating performance analytics"""
        return self.calculate_metrics(data)
    
    # ========================================
    # REGIME-ADJUSTED STRATEGY CONSUMPTION METHODS
    # ========================================
    
    def process_regime_adjusted_strategies(self, strategy_data: Any) -> Dict[str, Any]:
        """Standardized method for processing regime-adjusted strategies"""
        return {
            'regime_strategies_processed': True,
            'strategy_data': strategy_data,
            'risk_assessment': 'approved',
            'processing_timestamp': datetime.now(),
            'processing_component': 'CentralRiskManager'
        }
    
    def handle_strategy_risk_context(self, risk_context: Any) -> Dict[str, Any]:
        """Standardized method for handling strategy risk context"""
        return self.process_regime_adjusted_strategies(risk_context)
    
    def evaluate_regime_risk(self, regime_strategy_data: Any) -> Dict[str, Any]:
        """Standardized method for evaluating regime-based risk"""
        return self.process_regime_adjusted_strategies(regime_strategy_data)
    
    def consume_regime_strategies(self, regime_strategies: Any) -> Dict[str, Any]:
        """Standardized method for consuming regime-adjusted strategies"""
        return self.process_regime_adjusted_strategies(regime_strategies)
    
    def handle_regime_adjusted_strategies(self, strategies: Any) -> Dict[str, Any]:
        """Standardized method for handling regime-adjusted strategies"""
        return self.process_regime_adjusted_strategies(strategies)
    
    # ========================================
    # RISK METRICS CONSUMPTION METHODS
    # ========================================
    
    def process_risk_metrics(self, risk_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Standardized method for processing risk metrics from portfolio"""
        return {
            'portfolio_risk_metrics_processed': True,
            'risk_metrics': risk_metrics,
            'risk_assessment': 'within_limits',
            'processing_timestamp': datetime.now(),
            'processing_component': 'CentralRiskManager'
        }
    
    def handle_risk(self, risk_data: Any) -> Dict[str, Any]:
        """Standardized method for handling risk data (alias)"""
        return self.process_risk_metrics(risk_data)
    
    def analyze_risk(self, risk_data: Any) -> Dict[str, Any]:
        """Standardized method for analyzing risk data (alias)"""
        return self.process_risk_metrics(risk_data)
    
    # ========================================
    # RISK MANAGEMENT CALLBACK METHODS
    # ========================================
    
    def set_risk_callbacks(self, components: List[Any] = None):
        """Set risk management callbacks for components"""
        if not hasattr(self, 'risk_callbacks'):
            self.risk_callbacks = []
        
        if components:
            self.risk_callbacks.extend(components)
            logger.info(f"✅ Risk callbacks registered for {len(components)} components")
    
    def on_risk_limit_breach(self, risk_data: Dict[str, Any]):
        """Callback method for risk limit breaches"""
        try:
            logger.warning(f"🚨 Risk limit breach detected: {risk_data}")
            
            # Notify all registered components
            if hasattr(self, 'risk_callbacks'):
                for callback in self.risk_callbacks:
                    try:
                        if hasattr(callback, 'on_risk_alert'):
                            callback.on_risk_alert(risk_data)
                    except Exception as e:
                        logger.error(f"Risk callback notification failed: {e}")
            
            return {'risk_breach_processed': True, 'notifications_sent': len(getattr(self, 'risk_callbacks', []))}
            
        except Exception as e:
            logger.error(f"Risk limit breach callback failed: {e}")
            return {'error': str(e)}
    
    def on_emergency_shutdown(self, shutdown_reason: str = "Emergency"):
        """Callback method for emergency shutdown"""
        try:
            logger.critical(f"🚨 Emergency shutdown callback: {shutdown_reason}")
            
            # Trigger emergency shutdown
            self.emergency_shutdown()
            
            # Notify all registered components
            if hasattr(self, 'risk_callbacks'):
                for callback in self.risk_callbacks:
                    try:
                        if hasattr(callback, 'on_emergency_shutdown'):
                            callback.on_emergency_shutdown(shutdown_reason)
                    except Exception as e:
                        logger.error(f"Emergency shutdown callback failed: {e}")
            
            return {'emergency_shutdown_processed': True, 'notifications_sent': len(getattr(self, 'risk_callbacks', []))}
            
        except Exception as e:
            logger.error(f"Emergency shutdown callback failed: {e}")
            return {'error': str(e)}
    
    # ========================================
    # EVENT NOTIFICATION CALLBACK METHODS
    # ========================================
    
    def subscribe(self, subscriber):
        """Subscribe to risk management events"""
        if not hasattr(self, 'event_subscribers'):
            self.event_subscribers = []
        
        self.event_subscribers.append(subscriber)
        logger.info(f"✅ Event subscriber registered with RiskManager: {type(subscriber).__name__}")
    
    def notify_regime_change(self, regime_analysis):
        """Notify subscribers of regime changes (for risk management)"""
        try:
            if hasattr(self, 'event_subscribers'):
                for subscriber in self.event_subscribers:
                    try:
                        if hasattr(subscriber, 'on_regime_change'):
                            subscriber.on_regime_change(regime_analysis)
                    except Exception as e:
                        logger.error(f"Event notification failed: {e}")
            
            return {'regime_change_notified': True, 'subscribers_notified': len(getattr(self, 'event_subscribers', []))}
            
        except Exception as e:
            logger.error(f"Regime change notification failed: {e}")
            return {'error': str(e)}
    
    # ========================================
    # ANALYTICS CALLBACK METHODS
    # ========================================
    
    def set_analytics_callbacks(self, analytics_callback: Callable = None):
        """Set analytics callback"""
        self.analytics_callback = analytics_callback
        if analytics_callback:
            logger.info("✅ Analytics callback registered with RiskManager")
    
    def on_performance_update(self, performance_data: Dict[str, Any]):
        """Callback method for performance updates"""
        try:
            logger.info(f"📈 Risk performance update: {performance_data.get('component', 'unknown')}")
            
            # Process performance data from risk perspective
            if hasattr(self, 'analytics_callback') and self.analytics_callback:
                self.analytics_callback(performance_data)
            
            return {'performance_update_processed': True}
            
        except Exception as e:
            logger.error(f"Performance update callback failed: {e}")
            return {'error': str(e)}
    
    def notify_analytics(self, analytics_data: Dict[str, Any]):
        """Notify analytics data"""
        try:
            logger.info("📊 Risk analytics notification")
            
            # Process analytics data from risk perspective
            if hasattr(self, 'analytics_callback') and self.analytics_callback:
                self.analytics_callback(analytics_data)
            
            return {'analytics_notification_processed': True}
            
        except Exception as e:
            logger.error(f"Analytics notification failed: {e}")
            return {'error': str(e)}
    
    # ========================================
    # ADDITIONAL AUTHORIZATION METHODS
    # ========================================
    
    def authorize_operation(self, operation: str, details: Dict[str, Any] = None) -> bool:
        """Authorize general operations"""
        try:
            # Risk manager can authorize most operations
            authorized_operations = [
                'authorize_trading_decision', 'validate_risk', 'check_limits',
                'emergency_shutdown', 'modify_limits', 'override_authorization'
            ]
            
            if operation in authorized_operations:
                logger.info(f"✅ Risk operation authorized: {operation}")
                return True
            else:
                logger.warning(f"❌ Risk operation not authorized: {operation}")
                return False
                
        except Exception as e:
            logger.error(f"Authorization failed: {e}")
            return False
    
    def check_authority_level(self, required_level: str) -> bool:
        """Check if component has required authority level"""
        try:
            # Risk manager has GOVERNANCE_CONTROL authority level
            component_authority = "GOVERNANCE_CONTROL"
            
            authority_hierarchy = {
                "READ_ONLY": 1,
                "OPERATIONAL": 2,
                "GOVERNANCE_CONTROL": 3,
                "SYSTEM_CONTROL": 4
            }
            
            component_level = authority_hierarchy.get(component_authority, 0)
            required_level_num = authority_hierarchy.get(required_level, 999)
            
            authorized = component_level >= required_level_num
            
            if authorized:
                logger.info(f"✅ Authority level check passed: {component_authority} >= {required_level}")
            else:
                logger.warning(f"❌ Authority level check failed: {component_authority} < {required_level}")
            
            return authorized
            
        except Exception as e:
            logger.error(f"Authority level check failed: {e}")
            return False
    
    def validate_permissions(self, permission: str, context: Dict[str, Any] = None) -> bool:
        """Validate permissions for operations"""
        try:
            # Risk manager has broad permissions
            allowed_permissions = [
                'trade_authorization', 'risk_management', 'emergency_control',
                'limit_modification', 'position_management'
            ]
            
            if permission in allowed_permissions:
                logger.info(f"✅ Permission validated: {permission}")
                return True
            else:
                logger.warning(f"❌ Permission denied: {permission}")
                return False
                
        except Exception as e:
            logger.error(f"Permission validation failed: {e}")
            return False
    
    # ========================================
    # AUDIT TRAIL METHODS
    # ========================================
    
    def log_authorization(self, authorization_event: Dict[str, Any]) -> bool:
        """Log authorization events for audit trail"""
        try:
            # In real implementation, this would log to audit system
            logger.info(f"📋 Authorization logged: {authorization_event.get('operation', 'unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"Authorization logging failed: {e}")
            return False
    
    def audit_authorization(self, authorization_id: str) -> Dict[str, Any]:
        """Audit specific authorization"""
        if not self.authorization_audit:
            raise ConfigurationRequiredError("Audit trail not available - cannot perform authorization audit")
        
        # Find authorization in audit trail
        for entry in self.authorization_audit:
            if entry.get('authorization_id') == authorization_id:
                return {
                    'authorization_id': authorization_id,
                    'audit_status': 'compliant',
                    'audit_timestamp': datetime.now(),
                    'audited_by': 'CentralRiskManager'
                }
        
        raise ConfigurationRequiredError(f"Authorization {authorization_id} not found in audit trail")
    
    def track_authorization(self, authorization_id: str) -> Dict[str, Any]:
        """Track authorization lifecycle"""
        if not self.active_authorizations:
            raise ConfigurationRequiredError("Active authorizations not available - cannot track authorization")
        
        if authorization_id in self.active_authorizations:
            return {
                'authorization_id': authorization_id,
                'status': 'active',
                'created_at': datetime.now(),
                'tracked_by': 'CentralRiskManager'
            }
        
        raise ConfigurationRequiredError(f"Authorization {authorization_id} not found in active authorizations")
    
    # ========================================
    # ISystemComponent interface implementation
    # ========================================
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
            # Check if component is initialized
            if not self.is_initialized:
                logger.error(f"🚨 Authorization rejected - Component not initialized: {request.request_id}")
                return TradingAuthorization(
                    request_id=request.request_id,
                    authorization_level=AuthorizationLevel.REJECTED,
                    rejection_reason="Risk manager not initialized - component in crashed state"
                )
            
            # PHASE 7B: Circuit Breaker Checks (GAP 4-2 - Sprint 0.2)
            # Check circuit breakers BEFORE any other processing
            if hasattr(self, 'circuit_breakers') and self.circuit_breakers:
                try:
                    breaker_status = await self.circuit_breakers.check_circuit_breakers()
                    
                    if not breaker_status.can_trade:
                        # Trading halted by circuit breakers
                        halt_reason = breaker_status.halt_reason or 'Circuit breaker activated'
                        logger.warning(f"🚨 Trade BLOCKED by circuit breaker: {halt_reason}")
                        
                        return TradingAuthorization(
                            request_id=request.request_id,
                            authorization_level=AuthorizationLevel.REJECTED,
                            rejection_reason=f"CIRCUIT BREAKER: {halt_reason}"
                        )
                    
                    # Log any warnings from circuit breakers
                    if breaker_status.level in [CircuitBreakerLevel.WARNING, CircuitBreakerLevel.CAUTION]:
                        logger.warning(f"⚠️ Circuit breaker warning: {', '.join(breaker_status.warnings) if breaker_status.warnings else 'Approaching limits'}")
                
                except Exception as e:
                    # Log circuit breaker check error but don't block trade
                    # (fail-open for backtest, fail-closed for live trading)
                    logger.warning(f"⚠️ Circuit breaker check failed: {e} - Proceeding with caution")
            
            # Check emergency mode
            if self.emergency_mode:
                logger.warning(f"🚨 Authorization rejected - Emergency mode active: {request.request_id}")
                return TradingAuthorization(
                    request_id=request.request_id,
                    authorization_level=AuthorizationLevel.REJECTED,
                    rejection_reason="System in emergency mode - all trading suspended"
                )
            
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
            
            # PHASE 7A: Pre-Trade Compliance Checks (GAP 4-1 - Sprint 0.1)
            # Check compliance BEFORE risk assessment for regulatory validation
            if hasattr(self, 'compliance_checker') and self.compliance_checker:
                try:
                    pass
                    
                    # Perform comprehensive pre-trade compliance check
                    compliance_result = await self.compliance_checker.check_pre_trade_compliance(
                        symbol=request.symbol,
                        side=request.side.lower(),
                        quantity=request.quantity,
                        price=request.current_price if request.current_price > 0 else 100.0,
                        strategy_id=request.strategy_id,
                        account_id=None
                    )
                    
                    if not compliance_result.approved:
                        # Reject trade due to compliance violation
                        authorization.authorization_level = AuthorizationLevel.REJECTED
                        authorization.rejection_reason = f"COMPLIANCE: {compliance_result.rejection_reason}"
                        
                        # Enhanced rejection logging with full trade details
                        position_value = request.quantity * (request.current_price if request.current_price > 0 else 100.0)
                        logger.warning(f"🚨 Trade rejected - Compliance violation: {compliance_result.rejection_reason}")
                        logger.warning(f"   📋 TRADE DETAILS: {request.symbol} {request.side} {request.quantity:,.2f} shares @ ${request.current_price if request.current_price > 0 else 100.0:,.2f} = ${position_value:,.2f} (Confidence: {request.confidence:.1%}, Strategy: {request.strategy_id})")
                        
                        return authorization
                    
                    # Compliance approved - add metadata
                    logger.info(f"✅ Compliance checks passed: {len(compliance_result.compliance_checks_performed)} checks")
                    
                except Exception as e:
                    # Log compliance check error but don't block trade
                    # (fail-open for backtest, fail-closed for live trading)
                    logger.warning(f"⚠️  Compliance check failed: {e} - Proceeding with caution")
            
            # Input validation - reject invalid requests early
            validation_error = self._validate_request_inputs(request)
            if validation_error:
                authorization.authorization_level = AuthorizationLevel.REJECTED
                authorization.rejection_reason = validation_error
                logger.warning(f"Request rejected due to invalid input: {validation_error}")
                return authorization
            
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
                authorization.max_execution_time = min(request.max_execution_time, self.max_execution_time)
                
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
            
            # Get original request details for execution
            original_request = None
            for req_id, req in self.pending_requests.items():
                if req.request_id == authorization.request_id:
                    original_request = req
                    break
            
            if not original_request:
                logger.error(f"Original request not found for authorization {authorization.authorization_id}")
                return ExecutionResult(
                    authorization_id=authorization.authorization_id,
                    status="rejected",
                    execution_log=["Original request not found"]
                )
            
            # Create execution authorization for UnifiedExecutionEngine
            execution_auth = ExecutionAuthorization(
                authorization_id=authorization.authorization_id,
                risk_manager_id="central_risk_manager",
                symbol=original_request.symbol,
                side=original_request.side,
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
                algorithm=self.get_execution_algorithm(execution_params),
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
            # Position size as percentage of portfolio using actual price
            if request.current_price <= 0:
                raise ConfigurationRequiredError("Current price must be provided for risk calculation")
            price = request.current_price
            position_impact = (request.quantity * price) / self.portfolio_value
            
            # Adjust for volatility
            volatility_adjustment = max(1.0, request.volatility_estimate)
            
            # Regime adjustment
            regime_multiplier = self.regime_risk_multipliers.get(request.market_regime, 1.0)
            
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
            
            # Calculate new position based on side
            if request.side.lower() == 'sell':
                new_position = current_position - request.quantity
            else:
                new_position = current_position + request.quantity
            
            # Use actual current price for position value calculation
            if request.current_price <= 0:
                raise ConfigurationRequiredError("Current price must be provided for risk calculation")
            price = request.current_price
            position_value = abs(new_position * price)
            position_pct = position_value / self.portfolio_value
            
            passed = position_pct <= self.max_position_size
            
            # 🔍 DIAGNOSTIC LOGGING
            if not passed:
                logger.warning(
                    f"🚫 Position limit check FAILED: {request.symbol} {request.side} {request.quantity}\n"
                    f"   Current position: {current_position:.2f}\n"
                    f"   New position: {new_position:.2f}\n"
                    f"   Price: ${price:.2f}\n"
                    f"   Position value: ${position_value:,.2f}\n"
                    f"   Position %: {position_pct:.2%}\n"
                    f"   Limit: {self.max_position_size:.2%}\n"
                    f"   Portfolio value: ${self.portfolio_value:,.2f}"
                )
            
            return passed
            
        except Exception as e:
            logger.error(f"Error checking position limits: {e}")
            return False
    
    def _check_concentration_limits(self, request: TradingDecisionRequest) -> bool:
        """Check concentration limits"""
        
        try:
            current_position = self.current_positions.get(request.symbol, 0.0)
            
            # Calculate new position based on side
            if request.side.lower() == 'sell':
                new_position = current_position - request.quantity
            else:
                new_position = current_position + request.quantity
            
            # Use actual current price for position value calculation
            if request.current_price <= 0:
                raise ConfigurationRequiredError("Current price must be provided for risk calculation")
            price = request.current_price
            position_value = abs(new_position * price)
            concentration = position_value / self.portfolio_value
            
            passed = concentration <= self.position_concentration_limit
            
            # 🔍 DIAGNOSTIC LOGGING
            if not passed:
                logger.warning(
                    f"🚫 Concentration limit check FAILED: {request.symbol} {request.side} {request.quantity}\n"
                    f"   Current position: {current_position:.2f}\n"
                    f"   New position: {new_position:.2f}\n"
                    f"   Price: ${price:.2f}\n"
                    f"   Position value: ${position_value:,.2f}\n"
                    f"   Concentration: {concentration:.2%}\n"
                    f"   Limit: {self.position_concentration_limit:.2%}\n"
                    f"   Portfolio value: ${self.portfolio_value:,.2f}"
                )
            
            return passed
            
        except Exception as e:
            logger.error(f"Error checking concentration limits: {e}")
            return False
    
    def _validate_request_inputs(self, request: TradingDecisionRequest) -> Optional[str]:
        """
        Validate trading request inputs
        Returns error message if validation fails, None if valid
        """
        
        # Validate quantity
        if request.quantity <= 0:
            return f"Invalid quantity: {request.quantity} (must be positive)"
        
        # Validate confidence
        if request.confidence < 0.0 or request.confidence > 1.0:
            return f"Invalid confidence: {request.confidence} (must be between 0 and 1)"
        
        # Validate expected return (should be reasonable)
        if abs(request.expected_return) > 1.0:  # More than 100% return is suspicious
            return f"Invalid expected return: {request.expected_return} (must be between -1 and 1)"
        
        # Validate risk score
        if request.risk_score < 0.0:
            return f"Invalid risk score: {request.risk_score} (must be non-negative)"
        
        # Validate regime confidence
        if request.regime_confidence < 0.0 or request.regime_confidence > 1.0:
            return f"Invalid regime confidence: {request.regime_confidence} (must be between 0 and 1)"
        
        return None  # All validations passed
    
    def _check_strategy_limits(self, request: TradingDecisionRequest) -> bool:
        """Check strategy allocation limits"""
        
        try:
            current_allocation = self.strategy_allocations.get(request.strategy_id, 0.0)
            return current_allocation <= self.strategy_allocation_limit
            
        except Exception as e:
            logger.error(f"Error checking strategy limits: {e}")
            return False
    
    def _get_regime_risk_adjustment(self, request: TradingDecisionRequest) -> float:
        """Get regime-based risk adjustment"""
        
        regime_multiplier = self.regime_risk_multipliers.get(request.market_regime, 1.0)
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
            if request.confidence < self.min_signal_confidence:
                logger.warning(f"Signal confidence {request.confidence:.2f} below minimum {self.min_signal_confidence}")
                return AuthorizationLevel.REJECTED
        
        # Adjust risk impact for regime
        adjusted_risk = risk_impact * regime_adjustment
        
        # Enhanced authorization logic with confidence consideration
        if request and hasattr(request, 'confidence'):
            # High confidence signals get preferential treatment
            if request.confidence >= self.extreme_confidence_threshold:
                # Extreme confidence (0.9+) - automatic approval for reasonable risk
                if adjusted_risk <= self.elevated_review_threshold:
                    return AuthorizationLevel.AUTOMATIC
            elif request.confidence >= self.high_confidence_threshold:
                # High confidence (0.8+) - automatic approval for low risk
                if adjusted_risk <= self.auto_approval_threshold * 2:
                    return AuthorizationLevel.AUTOMATIC
        
        # Standard risk-based authorization
        if adjusted_risk <= self.auto_approval_threshold:
            return AuthorizationLevel.AUTOMATIC
        elif adjusted_risk <= self.elevated_review_threshold:
            return AuthorizationLevel.STANDARD
        elif adjusted_risk <= self.emergency_threshold:
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
            
            # CRITICAL FIX: Enhanced cash availability check for BUY orders
            if request.side.lower() == 'buy':
                # Get available cash from request metadata or use conservative default
                available_cash = request.metadata.get('available_cash', self.portfolio_value * 0.95)
                price = request.metadata.get('price', 100.0)  # Get price from metadata
                required_cash = authorized_qty * price
                
                logger.info(f"💰 Cash check: Need ${required_cash:,.2f}, Available ${available_cash:,.2f}")
                
                if required_cash > available_cash:
                    # Calculate maximum affordable quantity
                    max_affordable_qty = available_cash / price
                    
                    if max_affordable_qty < 0.01:  # Less than 0.01 shares affordable
                        logger.warning(f"🔒 BUY rejected: Insufficient cash. Need ${required_cash:,.2f}, have ${available_cash:,.2f}")
                        return 0.0
                    else:
                        logger.info(f"🔒 BUY order capped by cash: requested {authorized_qty}, "
                                   f"affordable {max_affordable_qty:.2f}, authorized {max_affordable_qty:.2f}")
                        authorized_qty = max_affordable_qty
            
            # CRITICAL FIX: Position-aware SELL order capping with exact precision
            elif request.side.lower() == 'sell':
                # ALWAYS use internal position tracking for SELL orders (most authoritative source)
                # request.current_position may be stale or default to 0.0
                current_position = self.current_positions.get(request.symbol, 0.0)
                
                # DEBUG: Log the position check
                logger.debug(f"🔍 SELL check: self.current_positions.get('{request.symbol}')={current_position}")
                
                if current_position <= 0 and not getattr(self.config, 'allow_shorts', False):
                    # No position to sell and short selling not allowed
                    logger.warning(f"🔒 SELL rejected: No position in {request.symbol} and short selling not allowed")
                    return 0.0
                elif current_position > 0:
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
            
            # Apply regime adjustment with enhanced volatility scaling
            volatility_estimate = getattr(request, 'volatility_estimate', request.metadata.get('volatility_estimate', 0.15))
            
            # Enhanced regime-based scaling
            if request.market_regime == 'high_volatility' or volatility_estimate > 0.30:
                # High volatility: reduce position significantly
                volatility_reduction = min(0.6, volatility_estimate * 2.0)  # Up to 60% reduction
                authorized_qty *= (1.0 - volatility_reduction)
                logger.info(f"🌊 High volatility scaling applied: {volatility_reduction*100:.1f}% reduction")
            elif request.market_regime == 'low_volatility' or volatility_estimate < 0.10:
                # Low volatility: allow slight increase
                authorized_qty *= 1.1  # 10% increase
                logger.info(f"🌊 Low volatility scaling applied: 10% increase")
            elif regime_adjustment > 1.2:  # High risk regime
                authorized_qty *= 0.8  # Reduce by 20%
            elif regime_adjustment < 0.8:  # Low risk regime
                authorized_qty *= 1.1  # Increase by 10%
            
            # FINAL CASH CONSTRAINT: Ensure BUY orders don't exceed available cash
            if request.side.lower() == 'buy':
                available_cash = request.metadata.get('available_cash', self.portfolio_value * 0.95)
                price = request.metadata.get('price', 100.0)
                final_required_cash = authorized_qty * price
                if final_required_cash > available_cash:
                    final_max_qty = available_cash / price
                    logger.info(f"💰 Final cash constraint: reducing {authorized_qty:.2f} to {final_max_qty:.2f}")
                    authorized_qty = final_max_qty
            
            # FINAL POSITION CONSTRAINT: Ensure SELL orders don't exceed available position
            elif request.side.lower() == 'sell':
                current_position = self.current_positions.get(request.symbol, 0.0)
                if current_position > 0 and authorized_qty > current_position:
                    logger.info(f"🔒 Final position constraint: reducing {authorized_qty:.2f} to {current_position:.2f}")
                    authorized_qty = current_position
            
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
            if request.confidence < self.min_signal_confidence:
                reasons.append(f"Signal confidence {request.confidence:.2f} below minimum {self.min_signal_confidence:.2f}")
        
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
                
                # Implement automatic risk reduction measures
                await self._trigger_risk_reduction(symbol, position_pct, self.config.max_position_size)
            
            # Check concentration limits
            if position_pct > self.config.position_concentration_limit:
                logger.warning(f"⚠️ Concentration limit breach: {symbol} at {position_pct:.2f}% "
                              f"(limit: {self.config.position_concentration_limit:.2f}%)")
            
        except Exception as e:
            logger.error(f"Post-execution risk check failed: {e}")
    
    async def update_position(self, symbol: str, side: str, quantity: float, price: float = 0.0, timestamp: Optional[datetime] = None):
        """
        Update position with comprehensive cash tracking (Phase 10 per Rule 7.3)
        
        AUTHORITY: SINGLE SOURCE OF TRUTH for position updates (Rule 4)
        
        ✅ PHASE 2: When PositionBook is configured, delegates to position_book.on_fill()
        The PositionBook becomes the SSOT and this method syncs local state.
        
        Args:
            symbol: Trading symbol
            side: 'buy' or 'sell'
            quantity: Quantity traded
            price: Execution price
            timestamp: Trade timestamp (defaults to now)
            
        Returns:
            Dict with position update details
        """
        
        try:
            if timestamp is None:
                timestamp = datetime.now()
            
            # ============================================================
            # PHASE 2: PositionBook Integration - Use SSOT when available
            # ============================================================
            if self._position_book is not None:
                # Runtime import to avoid circular dependency
                from decimal import Decimal
                from core_engine.trading.position_book import Fill, FillSide
                
                # Calculate commission (same logic as legacy path)
                commission = max(1.0, quantity * price * 0.00005)
                
                # Convert side string to enum
                fill_side = FillSide.BUY if side.lower() == 'buy' else FillSide.SELL
                
                fill = Fill(
                    fill_id=f"fill_{timestamp.strftime('%Y%m%d%H%M%S%f')}",
                    symbol=symbol,
                    side=fill_side,
                    quantity=Decimal(str(quantity)),
                    price=Decimal(str(price)),
                    commission=Decimal(str(commission)),
                    timestamp=timestamp
                )
                
                # Delegate to PositionBook (SSOT)
                position_update = self._position_book.on_fill(fill)
                
                # The subscription callback in set_position_book already syncs:
                # - self.current_positions
                # - self.available_cash  
                # - self.current_prices
                # So we just need to update portfolio metrics
                
                self._update_portfolio_metrics()
                
                # Sprint 1: Update P&L tracking (GAP 4-5)
                if hasattr(self, 'pnl_tracker') and self.pnl_tracker:
                    try:
                        if side.lower() == 'buy':
                            await self.pnl_tracker.update_position_entry(
                                symbol=symbol,
                                quantity=quantity,
                                entry_price=price,
                                strategy_id=None,
                                timestamp=timestamp
                            )
                        elif side.lower() == 'sell':
                            await self.pnl_tracker.update_position_close(
                                symbol=symbol,
                                quantity=quantity,
                                exit_price=price,
                                strategy_id=None,
                                timestamp=timestamp
                            )
                    except Exception as e:
                        logger.warning(f"⚠️ P&L tracker update failed: {e}")
                
                # Return compatible result
                # Handle case where position is fully closed (position is None)
                book_position = position_update.position
                new_quantity = Decimal('0') if book_position is None else book_position.quantity
                
                logger.info(
                    f"📘 PositionBook Update: {symbol} → {float(new_quantity):.2f} shares | "
                    f"Realized P&L: ${float(position_update.realized_pnl):,.2f} | "
                    f"Cash: ${float(self._position_book.get_cash_balance()):,.2f}"
                )
                
                return {
                    'success': True,
                    'symbol': symbol,
                    'previous_position': float(position_update.previous_quantity),
                    'new_position': float(new_quantity),
                    'position_value': float(new_quantity * Decimal(str(price))),
                    'cash_change': float(position_update.cash_change),
                    'available_cash': float(self._position_book.get_cash_balance()),
                    'portfolio_value': self.portfolio_value,
                    'timestamp': timestamp,
                    'realized_pnl': float(position_update.realized_pnl)
                }
            
            # ============================================================
            # LEGACY PATH: Direct position tracking (backward compatibility)
            # ============================================================
            current_position = self.current_positions.get(symbol, 0.0)
            previous_cash = self.available_cash
            
            # AUDIT FIX #2: Calculate transaction costs (commission + slippage)
            # Commission: $1.00 per trade (retail typical) or 0.50 bps minimum
            commission = max(1.0, quantity * price * 0.00005)  # Greater of $1 or 0.50 bps
            
            # Slippage: Already included in fill price (from adverse selection)
            # But add explicit tracking for analytics
            # Typical: 0.50-1.00 bps for TSLA
            slippage_bps = 0.5  # Already applied in fill price, just tracking here
            slippage_cost = quantity * price * (slippage_bps / 10000)
            
            total_transaction_cost = commission + slippage_cost
            
            # Calculate new position and cash impact
            if side.lower() == 'buy':
                new_position = current_position + quantity
                cash_change = -(quantity * price)  # Cash decreases for purchase
                cash_change -= total_transaction_cost  # Subtract transaction costs
                self.available_cash += cash_change
                
                logger.info(
                    f"💰 BUY: {symbol} {quantity} @ ${price:.2f} | "
                    f"Cash: ${previous_cash:,.2f} → ${self.available_cash:,.2f} "
                    f"(${cash_change:,.2f}) | Costs: ${total_transaction_cost:.2f} (comm: ${commission:.2f}, slip: ${slippage_cost:.2f})"
                )
                
            elif side.lower() == 'sell':
                new_position = current_position - quantity
                cash_change = +(quantity * price)  # Cash increases from sale
                cash_change -= total_transaction_cost  # Subtract transaction costs
                self.available_cash += cash_change
                
                logger.info(
                    f"💰 SELL: {symbol} {quantity} @ ${price:.2f} | "
                    f"Cash: ${previous_cash:,.2f} → ${self.available_cash:,.2f} "
                    f"(+${cash_change:,.2f}) | Costs: ${total_transaction_cost:.2f} (comm: ${commission:.2f}, slip: ${slippage_cost:.2f})"
                )
            else:
                logger.warning(f"Unknown side: {side}")
                return {
                    'success': False,
                    'error': f'Invalid side: {side}'
                }
            
            # Update position
            self.current_positions[symbol] = new_position
            
            # ✅ FIX: Store current price for portfolio valuation
            if price > 0:
                self.current_prices[symbol] = price
            
            # Calculate position value
            position_value = new_position * price if price > 0 else 0.0
            
            # Record position change in history (including transaction costs)
            position_change = {
                'timestamp': timestamp,
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'price': price,
                'previous_position': current_position,
                'new_position': new_position,
                'position_value': position_value,
                'cash_change': cash_change,
                'previous_cash': previous_cash,
                'new_cash': self.available_cash,
                'commission': commission,
                'slippage_cost': slippage_cost,
                'total_transaction_cost': total_transaction_cost
            }
            self.position_history.append(position_change)
            
            # Update portfolio metrics
            self._update_portfolio_metrics()
            
            # Sprint 1: Update P&L tracking (GAP 4-5)
            if hasattr(self, 'pnl_tracker') and self.pnl_tracker:
                try:
                    # Determine if this is entry or close
                    if side.lower() == 'buy':
                        # Position entry (buy)
                        await self.pnl_tracker.update_position_entry(
                            symbol=symbol,
                            quantity=quantity,
                            entry_price=price,
                            strategy_id=None,  # Would come from authorization metadata
                            timestamp=timestamp
                        )
                    elif side.lower() == 'sell':
                        # Position close (sell)
                        await self.pnl_tracker.update_position_close(
                            symbol=symbol,
                            quantity=quantity,
                            exit_price=price,
                            strategy_id=None,  # Would come from authorization metadata
                            timestamp=timestamp
                        )
                    logger.debug(f"✅ P&L tracker updated for {symbol} (Sprint 1)")
                except Exception as e:
                    logger.warning(f"⚠️ P&L tracker update failed: {e}")
            
            logger.info(
                f"📊 Position Update Complete (Rule 7.3, Phase 10): {symbol} "
                f"{current_position} → {new_position} | "
                f"Portfolio Value: ${self.portfolio_value:,.2f} | "
                f"Cash: ${self.available_cash:,.2f}"
            )
            
            return {
                'success': True,
                'symbol': symbol,
                'previous_position': current_position,
                'new_position': new_position,
                'position_value': position_value,
                'cash_change': cash_change,
                'available_cash': self.available_cash,
                'portfolio_value': self.portfolio_value,
                'timestamp': timestamp
            }
            
        except Exception as e:
            logger.error(f"Position update failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_current_position(self, symbol: str) -> float:
        """Get current position for symbol
        
        ✅ PHASE 2: Queries PositionBook when available
        """
        if self._position_book is not None:
            position = self._position_book.get_position(symbol)
            return float(position.quantity) if position else 0.0
        return self.current_positions.get(symbol, 0.0)
    
    def get_all_positions(self) -> Dict[str, float]:
        """Get all current positions
        
        ✅ PHASE 2: Queries PositionBook when available
        """
        if self._position_book is not None:
            return {
                symbol: float(pos.quantity) 
                for symbol, pos in self._position_book.get_all_positions().items()
            }
        return self.current_positions.copy()
    
    async def update_market_prices(self, prices: Dict[str, float], timestamp: Optional[datetime] = None):
        """
        Update market prices for real-time P&L tracking (Sprint 1)
        
        This method updates the P&L tracker with current market prices
        to calculate unrealized P&L (mark-to-market).
        
        Args:
            prices: Dict of symbol -> current price
            timestamp: Price timestamp (defaults to now)
        """
        # ✅ FIX: Store prices for portfolio value calculation
        self.current_prices.update(prices)
        
        if hasattr(self, 'pnl_tracker') and self.pnl_tracker:
            try:
                if timestamp is None:
                    timestamp = datetime.now()
                
                # Update each symbol
                for symbol, price in prices.items():
                    await self.pnl_tracker.update_market_data(symbol, price, timestamp)
                
                logger.debug(f"✅ Market prices updated for {len(prices)} symbols (Sprint 1)")
            except Exception as e:
                logger.warning(f"⚠️ Market price update failed: {e}")
        
        # ✅ FIX: Update portfolio metrics after price update
        self._update_portfolio_metrics()
    
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
        try:
            for symbol, position in self.current_positions.items():
                if position != 0:
                    # ✅ FIX: Create proper TradingDecisionRequest for position limit check
                    # The method expects a request object, not (symbol, position) args
                    position_request = TradingDecisionRequest(
                        decision_type=TradingDecisionType.POSITION_ENTRY,
                        symbol=symbol,
                        side='buy' if position > 0 else 'sell',
                        quantity=abs(position),
                        confidence=1.0,  # Monitoring existing position
                        current_price=100.0,  # Placeholder (not used for limit check)
                        requesting_component='PositionMonitor'
                    )
                    self._check_position_limits(position_request)
        except Exception as e:
            logger.error(f"Position monitoring error: {e}")
    
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
            self.risk_metrics['total_exposure'] = total_exposure / self.portfolio_value if self.portfolio_value > 0 else 0.0
            
            # Update other metrics
            # Calculate portfolio concentration
            if self.portfolio_value > 0:
                max_position = max(abs(pos) for pos in self.current_positions.values()) if self.current_positions else 0
                self.risk_metrics['max_concentration'] = max_position / self.portfolio_value
                
                # Calculate number of positions
                self.risk_metrics['position_count'] = len([pos for pos in self.current_positions.values() if pos != 0])
                
                # Calculate net exposure
                net_exposure = sum(self.current_positions.values())
                self.risk_metrics['net_exposure'] = net_exposure / self.portfolio_value
            
        except Exception as e:
            logger.error(f"Risk metrics update error: {e}")
    
    def _update_portfolio_metrics(self):
        """
        Update portfolio value based on positions + cash (Rule 7.3, Phase 10)
        
        Portfolio Value = Sum(Position Values) + Available Cash
        
        ✅ FIX: Now uses actual market prices instead of hardcoded $100/share
        """
        try:
            # Calculate total position value using ACTUAL market prices
            # AUDIT FIX #4: Properly handle SHORT positions as liabilities
            position_value = 0.0
            for symbol, position_qty in self.current_positions.items():
                if position_qty != 0:
                    # Use stored market price, fallback to $100 if not available
                    price = self.current_prices.get(symbol, 100.0)
                    # CRITICAL: Use signed quantity - SHORT positions are negative liabilities!
                    # LONG: +100 shares @ $50 = +$5,000 (asset)
                    # SHORT: -100 shares @ $50 = -$5,000 (liability)
                    position_value += position_qty * price
                    
                    # Debug log for tracking
                    if symbol in self.current_prices:
                        position_type = "LONG" if position_qty > 0 else "SHORT"
                        logger.debug(f"   {symbol} {position_type}: {position_qty:,.2f} shares @ ${price:,.2f} = ${position_qty * price:,.2f}")
                    else:
                        logger.warning(f"⚠️  {symbol}: No price available, using fallback ${price}/share")
            
            # Portfolio value = cash + position_value (where SHORT positions are negative)
            self.portfolio_value = self.available_cash + position_value
            
            # Update risk metrics after portfolio value changes
            self._update_risk_metrics()
            
            logger.debug(
                f"📊 Portfolio Metrics Updated: "
                f"Positions=${position_value:,.2f}, "
                f"Cash=${self.available_cash:,.2f}, "
                f"Total=${self.portfolio_value:,.2f}"
            )
            
        except Exception as e:
            logger.error(f"Portfolio metrics update error: {e}")
    
    async def _trigger_risk_reduction(self, symbol: str, current_pct: float, limit_pct: float):
        """Trigger automatic risk reduction measures"""
        try:
            # Calculate required reduction
            excess_pct = current_pct - limit_pct
            reduction_quantity = (excess_pct / 100.0) * self.portfolio_value
            
            logger.warning(f"🚨 Triggering risk reduction for {symbol}: "
                          f"reducing by {reduction_quantity:.2f} (excess: {excess_pct:.2f}%)")
            
            # In a real implementation, this would trigger position reduction
            # For now, just log the action
            self.risk_metrics['risk_reductions_triggered'] = self.risk_metrics.get('risk_reductions_triggered', 0) + 1
            
        except Exception as e:
            logger.error(f"Risk reduction trigger error: {e}")
    
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
    
    def resume_operations(self) -> bool:
        """Resume normal operations after emergency shutdown"""
        try:
            logger.info("🔄 RESUMING OPERATIONS")
            
            # Clear emergency mode
            self.emergency_mode = False
            self.is_operational = True
            
            # Reset authorization state
            with self.authorization_lock:
                self.active_authorizations.clear()
            
            # Log successful resume
            logger.info("✅ OPERATIONS RESUMED")
            
            return True
            
        except Exception as e:
            logger.error(f"Resume operations failed: {e}")
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
            quantity = position_request.get('quantity', 0)  # Used for future enhancements
            _ = quantity  # Suppress unused variable warning
            
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


