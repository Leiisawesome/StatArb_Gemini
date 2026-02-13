"""
Central Risk Manager - TradeDesk Architecture Compliance
=======================================================

Enhanced RiskManager implementing the central governance hub pattern.
Serves as the single authority for ALL trading decisions in the system.

Architecture Compliance (Tier-1 Rules):
- Rule 1: System Architecture - Component integration, Layer 1 (Governance)
- Rule 3: Risk & Compliance Governance - Phases 6-10 (Authorization Pipeline)
- Rule 5: Execution & Order Management - Phase 15 (Position Update Authority)
- Rule 6: Operations & Recovery - P&L Monitoring, Reconciliation integration

Key Responsibilities:
- Central hub that encapsulates all trading decisions
- Controls WHAT (StrategyManager) → HOW (TradingEngine) → ACTION (UnifiedExecutionEngine)
- No component can execute trades independently
- All trading decisions flow through RiskManager authorization
- Regime-aware risk management with direct RegimeEngine integration
- SINGLE AUTHORITY for position updates (Phase 15)

Migration: December 2025 - Former Rule 4 content now Rule 3.

Author: StatArb_Gemini Architecture Compliance
Version: 2.0.0 (Rules Migration December 2025)
"""

import asyncio
import logging
import uuid
import time
import itertools
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum
from collections import deque, defaultdict

import numpy as np

# Fast ID counters for performance-critical decision requests
_fast_id_iterator = itertools.count()

def get_fast_id(prefix: str = "id") -> str:
    """Lock-free thread-safe ID generation avoiding expensive UUID calls (GAP 4-5)"""
    return f"{prefix}_{time.time_ns()}_{next(_fast_id_iterator)}"

from core_engine.exceptions import ConfigurationRequiredError

# Import the UnifiedExecutionEngine and ISystemComponent
from .unified_execution_engine import (
    UnifiedExecutionEngine, ExecutionAuthorization, ExecutionRequest,
    ExecutionResult, ExecutionAlgorithm, ExecutionUrgency
)
from .interfaces import ISystemComponent, IRegimeAware, RegimeContext
from .circuit_breakers import CircuitBreakerLevel

# Single source of truth for regimes
from ..type_definitions.regime import MarketRegime, MarketRegimeState

# PHASE 6: Import centralized RiskConfig (Rule 1, Section 7)
from ..config.component_config import RiskConfig

# ADS v3.1 / Institutional extensions
from core_engine.alpha.ads_components import Cooldown
from core_engine.risk.volatility_forecast import sigma_eff, correlation_change, stop_distance_pct, VolStopParams
from core_engine.risk.multi_exit_engine import decide_exit
from core_engine.risk.position_sizing.kelly_sizer import (
    KellyParams,
    compute_fractional_kelly_fraction_of_capital,
)

# PHASE 2 (PositionBook Integration): Type hints only to avoid circular import
# Actual import is deferred to runtime in set_position_book() and update_position()
if TYPE_CHECKING:
    from ..trading.position_book import IPositionBook

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

@dataclass(slots=True)
class TradingDecisionRequest:
    """Request for trading decision authorization"""

    request_id: str = field(default_factory=lambda: get_fast_id("req"))
    root_signal_id: str = ""  # Root signal that triggered this request (causal link)
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

@dataclass(slots=True)
class TradingAuthorization:
    """Authorization result for trading decisions"""

    authorization_id: str = field(default_factory=lambda: get_fast_id("auth"))
    request_id: str = ""
    root_signal_id: str = ""  # Cascaded signal ID for audit trail

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

class CentralRiskManager(ISystemComponent, IRegimeAware):
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
                emergency_threshold=config.get('emergency_threshold', 0.10),
                max_total_risk=config.get('max_total_risk', 0.20),
                # ADS v3.1 / institutional extensions (dict-config path MUST preserve these)
                enable_ads_cooldown=config.get("enable_ads_cooldown", True),
                ads_cooldown_mode=config.get("ads_cooldown_mode", "block_entries"),
                pvsi_threshold=config.get("pvsi_threshold", 2.0),
                pvsi_baseline_window=config.get("pvsi_baseline_window", 100),
                pvsi_recent_window=config.get("pvsi_recent_window", 20),
                enable_ads_multi_exit=config.get("enable_ads_multi_exit", True),
                max_holding_minutes=config.get("max_holding_minutes", 24 * 60),
                enable_forward_vol_stops=config.get("enable_forward_vol_stops", True),
                vol_realized_window=config.get("vol_realized_window", 20),
                vol_ewma_lambda=config.get("vol_ewma_lambda", 0.94),
                corr_benchmark_symbol=config.get("corr_benchmark_symbol", "SPY"),
                corr_short_window=config.get("corr_short_window", 20),
                corr_long_window=config.get("corr_long_window", 60),
                stop_k=config.get("stop_k", 2.0),
                stop_kappa=config.get("stop_kappa", 0.5),
                stop_overnight_mult=config.get("stop_overnight_mult", 1.5),
                enable_fractional_kelly_sizing=config.get("enable_fractional_kelly_sizing", True),
                kelly_frac=config.get("kelly_frac", 0.33),
                kelly_min=config.get("kelly_min", 0.02),
                kelly_max=config.get("kelly_max", 0.20),
                kelly_prior_a=config.get("kelly_prior_a", 5.0),
                kelly_prior_b=config.get("kelly_prior_b", 5.0),
                kelly_min_trades=config.get("kelly_min_trades", 30),
                kelly_uncertainty_floor=config.get("kelly_uncertainty_floor", 0.3),
                kelly_dd_gamma=config.get("kelly_dd_gamma", 2.0),
            )

            # Store allow_shorts config (not part of RiskConfig dataclass)
            self.config.allow_shorts = config.get('allow_shorts', False)
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

        # --------------------------------------------------------------------
        # ADS v3.1 / Institutional: lightweight state for monitoring + sizing
        # --------------------------------------------------------------------
        # Rolling price history for EWMA vol + correlation change (best-effort)
        self._price_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=500))

        # Closed-trade outcome history for Kelly + PVSI cooldown (per strategy_id)
        # Stored as risk-normalized return proxy (pnl_pct/100 by default)
        self._strategy_trade_outcomes: Dict[str, List[float]] = defaultdict(list)

        # ADS PVSI cooldown trackers (per strategy_id)
        self._strategy_cooldowns: Dict[str, Cooldown] = {}

        # Prevent repeated exit firing while an exit is already in-flight
        self._exit_in_flight: set[str] = set()

        # High-water mark tracking for drawdown factor (Kelly)
        self._portfolio_hwm: float = 0.0

        # Optional: liquidity engine (if injected by orchestrator)
        self.liquidity_engine: Optional[Any] = None

        # Portfolio value and cash (synced from PositionBook when available)
        initial_capital = config.get('initial_capital', 100000.0) if isinstance(config, dict) else 100000.0
        self.portfolio_value: float = initial_capital
        self.available_cash: float = initial_capital  # DEPRECATED: Use position_book.get_cash_balance()
        self.position_history: List[Dict[str, Any]] = []  # DEPRECATED: PositionBook tracks fill history

        self._portfolio_hwm = float(initial_capital)

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
        self.trading_mode = 'backtest'  # 'backtest', 'paper', or 'live'

        # Orchestrator integration
        self.component_id: Optional[str] = None
        self.orchestrator: Optional[Any] = None  # HierarchicalSystemOrchestrator reference

        # Threading
        self.authorization_lock = asyncio.Lock()
        self.monitoring_task: Optional[asyncio.Task] = None

        logger.info("Central Risk Manager initialized - Governance Hub Ready (using centralized RiskConfig)")

    # ========================================================================
    # INTRADAY SESSION ISOLATION — Day-Boundary Reset
    # ========================================================================

    def reset_intraday_state(self) -> None:
        """Reset runtime state that leaks across trading-day boundaries.

        Called by the backtest engine at each new trading-day open when
        ``intraday_session_isolation`` is enabled.  This ensures that
        volatility-based stop distances (σ_eff, Δρ), cooldown trackers,
        Kelly sizing history, and drawdown HWM all start fresh, making
        each day fully independent.
        """
        # 1. Rolling price history → vol stops + correlation change
        self._price_history.clear()

        # 2. PVSI cooldown trackers (per-strategy)
        self._strategy_cooldowns.clear()

        # 3. Exit-in-flight guard
        self._exit_in_flight.clear()

        # 4. Strategy trade outcomes (Kelly / PVSI sizing history)
        self._strategy_trade_outcomes.clear()

        # 5. Portfolio high-water mark → drawdown gating
        initial_capital = float(getattr(self.config, 'initial_capital', 100000))
        self._portfolio_hwm = initial_capital

        logger.debug(
            "CRM: intraday state reset (price_history, cooldowns, "
            "exit-in-flight, trade_outcomes, portfolio_hwm)"
        )

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
        """Strategy allocation limit from centralized config"""
        return self.config.strategy_allocation_limit

    @property
    def real_time_monitoring(self) -> bool:
        """Real-time monitoring flag from centralized config"""
        return self.config.real_time_monitoring

    @property
    def monitoring_frequency(self) -> int:
        """Monitoring frequency in seconds from centralized config"""
        return self.config.monitoring_frequency_seconds

    @property
    def max_execution_time(self) -> int:
        """Max execution time in seconds from centralized config"""
        return self.config.max_execution_time_seconds

    def get_execution_algorithm(self, execution_params: Optional[Dict[str, Any]] = None) -> ExecutionAlgorithm:
        """Get execution algorithm from parameters or raise exception"""
        if execution_params and 'algorithm' in execution_params:
            return execution_params['algorithm']
        raise ConfigurationRequiredError("execution_algorithm must be specified in execution parameters")

    @property
    def high_confidence_threshold(self) -> float:
        """High confidence threshold from centralized config"""
        return self.config.high_confidence_threshold

    @property
    def extreme_confidence_threshold(self) -> float:
        """Extreme confidence threshold from centralized config"""
        return self.config.extreme_confidence_threshold

    @property
    def regime_risk_multipliers(self) -> Dict[str, float]:
        """
        Regime-based risk multipliers (affects risk assessment impact)
        Values > 1.0 increase perceived risk, < 1.0 decrease it.
        """
        return {
            # Primary Regimes
            MarketRegime.BULL_LOW_VOL.value: 0.7,
            MarketRegime.BULL_HIGH_VOL.value: 1.0,
            MarketRegime.BEAR_LOW_VOL.value: 1.2,
            MarketRegime.BEAR_HIGH_VOL.value: 1.6,
            
            # Volatility Regimes
            MarketRegime.LOW_VOLATILITY.value: 0.8,
            MarketRegime.NORMAL_VOLATILITY.value: 1.0,
            MarketRegime.HIGH_VOLATILITY.value: 1.4,
            MarketRegime.EXTREME_VOLATILITY.value: 1.8,
            
            # Stress Regimes
            MarketRegime.CRISIS.value: 2.5,
            MarketRegime.CHOPPY.value: 1.3,
            MarketRegime.EUPHORIA.value: 1.5,
            
            # Legacy/Fallback
            'bull_market': 0.8,
            'bear_market': 1.3,
            'high_volatility': 1.5,
            'low_volatility': 0.7,
            'crisis': 2.5,
            'sideways': 1.0,
            'unknown': 1.0
        }

    def _get_regime_scaling_factor(self, regime_str: str) -> float:
        """
        Get regime-specific position scaling factor (affects authorized quantity)
        Values < 1.0 reduce size, > 1.0 increase size (within limits).
        """
        scaling_map = {
            # High-confidence favorable regimes
            MarketRegime.BULL_LOW_VOL.value: 1.2,
            MarketRegime.NORMAL_VOLATILITY.value: 1.0,
            MarketRegime.LOW_VOLATILITY.value: 1.1,
            
            # Cautious regimes
            MarketRegime.BULL_HIGH_VOL.value: 0.8,
            MarketRegime.BEAR_LOW_VOL.value: 0.7,
            MarketRegime.RANGE_BOUND.value: 0.9,
            MarketRegime.WEAK_TRENDING.value: 0.8,
            
            # High-risk regimes (Scaling down)
            MarketRegime.BEAR_HIGH_VOL.value: 0.4,
            MarketRegime.HIGH_VOLATILITY.value: 0.5,
            MarketRegime.CHOPPY.value: 0.5,
            MarketRegime.EUPHORIA.value: 0.6,
            MarketRegime.EXTREME_VOLATILITY.value: 0.2,
            MarketRegime.CRISIS.value: 0.1, # Effectively handled by gate too
        }
        return scaling_map.get(regime_str, 1.0)

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
                    # CRITICAL FIX: PositionBook stores quantity as POSITIVE with separate side
                    # CentralRiskManager uses SIGNED quantities (negative for shorts)
                    raw_qty = float(update.position.quantity)
                    if raw_qty != 0.0:
                        # Apply sign based on position side
                        if update.position.is_short:
                            new_qty = -raw_qty  # Short positions have negative quantity
                        else:
                            new_qty = raw_qty   # Long positions have positive quantity
                        self.current_positions[symbol] = new_qty
                        logger.debug(f"📘 current_positions[{symbol}] = {new_qty:.4f} (side={update.position.side})")
                        if update.fill.price > 0:
                            self.current_prices[symbol] = float(update.fill.price)
                    else:
                        # Position fully closed - remove from dict
                        if symbol in self.current_positions:
                            del self.current_positions[symbol]
                            logger.debug(f"📘 current_positions[{symbol}] removed (position closed)")
                else:
                    # Position closed - remove from dict
                    if symbol in self.current_positions:
                        del self.current_positions[symbol]
                        logger.debug(f"📘 current_positions[{symbol}] removed (position closed)")

                # ADS v3.1: update cooldown + trade outcome stats on fills/closes
                try:
                    self._handle_position_update_ads(update)
                except Exception as e:
                    logger.debug(f"ADS position update handler failed: {e}")
            except Exception as e:
                logger.warning(f"Error in position update handler: {e}", exc_info=True)

        position_book.subscribe(_on_position_update)

        logger.info("✅ PositionBook integrated with Central Risk Manager (SSOT Phase 2)")

    @property
    def position_book(self) -> Optional["IPositionBook"]:
        """Get the PositionBook if set, None otherwise"""
        return self._position_book

    def set_liquidity_engine(self, liquidity_engine: Any) -> None:
        """
        Inject LiquidityAssessmentEngine (optional).

        Used for ADS v3.1 multi-exit liquidity stop and sizing liquidity factor.
        """
        self.liquidity_engine = liquidity_engine
        logger.info("✅ LiquidityAssessmentEngine injected into CentralRiskManager")

    def set_oms(self, oms: Any) -> None:
        """
        Set the Order Management System.

        Args:
            oms: OrderManagementSystem instance
        """
        self._oms = oms
        logger.info("✅ OrderManagementSystem registered with Central Risk Manager")

    def set_order_management_system(self, oms: Any) -> None:
        """Alias for set_oms"""
        self.set_oms(oms)

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
        # Rule: Use provided context multiplier as primary authority (Pro-Grade Integration)
        if hasattr(new_regime_context, 'risk_multiplier') and new_regime_context.risk_multiplier != 1.0:
            self.risk_multiplier = new_regime_context.risk_multiplier
            logger.info(f"  📊 Risk limits scaled by RegimeContext multiplier: {self.risk_multiplier:.2f}")
        else:
            # High volatility → tighter limits
            # Low volatility → can afford slightly looser limits
            if volatility_regime in ['high_volatility', 'extreme_volatility', 'high', 'extreme']:
                self.risk_multiplier = 0.7  # Reduce risk by 30%
                logger.info(f"  📉 Risk limits tightened (heuristic multiplier: 0.7) due to {volatility_regime}")
            elif volatility_regime in ['low_volatility', 'low']:
                self.risk_multiplier = 1.2  # Can increase risk by 20%
                logger.info(f"  📈 Risk limits relaxed (heuristic multiplier: 1.2) due to {volatility_regime}")
            else:
                self.risk_multiplier = 1.0  # Normal risk
                logger.info(f"  ➡️  Normal risk limits (multiplier: 1.0)")

        logger.info(f"✅ Risk limits updated for regime: {regime_name}")

        # Propagate to sub-components if they are subscribers
        if self.circuit_breakers and hasattr(self.circuit_breakers, 'on_regime_change'):
            # Convert context to state or just pass context if we unify them
            # For now, we try to extract the state if possible, or pass context
            await self.circuit_breakers.on_regime_change(new_regime_context)
            
        if self.pnl_tracker and hasattr(self.pnl_tracker, 'on_regime_change'):
            await self.pnl_tracker.on_regime_change(new_regime_context)

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

    async def authorize_batch(self, requests: List[TradingDecisionRequest]) -> List[TradingAuthorization]:
        """
        Vectorized authorization path for batch signal processing (Hotspot 3).
        Processes multiple requests efficiently to avoid object creation overhead 
        if possible, though currently focuses on minimizing asyncio overhead.
        """
        if not requests:
            return []

        # Optimization: process in one lock if appropriate, or parallelize
        # For now, we reuse the existing logic but minimize logging and overhead
        tasks = [self.authorize_trading_decision(req) for req in requests]
        
        # We can use a smaller timeout or batching if needed
        return await asyncio.gather(*tasks)

    async def authorize_trading_decision(self, request: TradingDecisionRequest) -> TradingAuthorization:
        """
        Central authorization point for ALL trading decisions
        OPTIMIZED (Hotspot 3): Reduced logging and fast-path for backtesting
        """

        try:
            # Check if component is initialized
            if not self.is_initialized:
                logger.error(f"🚨 Authorization rejected - {request.request_id}")
                return TradingAuthorization(
                    request_id=request.request_id,
                    authorization_level=AuthorizationLevel.REJECTED,
                    rejection_reason="Not initialized"
                )

            # PHASE 7B: Circuit Breaker Checks
            if hasattr(self, 'circuit_breakers') and self.circuit_breakers:
                try:
                    breaker_status = await self.circuit_breakers.check_circuit_breakers()
                    if not breaker_status.can_trade:
                        return TradingAuthorization(
                            request_id=request.request_id,
                            authorization_level=AuthorizationLevel.REJECTED,
                            rejection_reason=f"CIRCUIT BREAKER: {breaker_status.halt_reason}"
                        )
                except Exception as e:
                    # Fail-closed in live/paper mode, fail-open only in backtest
                    trading_mode = getattr(self, 'trading_mode', 'backtest')
                    if trading_mode in ('live', 'paper'):
                        logger.error(f"Circuit breaker check failed (fail-closed): {e}")
                        return TradingAuthorization(
                            request_id=request.request_id,
                            authorization_level=AuthorizationLevel.REJECTED,
                            rejection_reason=f"CIRCUIT_BREAKER_ERROR: {e}"
                        )
                    else:
                        logger.warning(f"Circuit breaker check failed (fail-open in backtest): {e}")

            # Check emergency mode
            if self.emergency_mode:
                return TradingAuthorization(
                    request_id=request.request_id,
                    authorization_level=AuthorizationLevel.REJECTED,
                    rejection_reason="Emergency mode"
                )

            # Store pending request (Safe locking - GAP 4-5)
            async with self.authorization_lock:
                self.pending_requests[request.request_id] = request

            # Perform comprehensive risk assessment (OUTSIDE lock to prevent loop blockage)
            try:
                authorization = await self._assess_trading_request(request)
            finally:
                # Ensure we clean up even if assessment fails
                async with self.authorization_lock:
                    self.pending_requests.pop(request.request_id, None)

            # Store result (Safe locking)
            async with self.authorization_lock:
                if authorization.authorization_level != AuthorizationLevel.REJECTED:
                    self.active_authorizations[authorization.authorization_id] = authorization

                # Add to history only if not in high-performance mode
                if len(self.authorization_history) < 10000:
                    self.authorization_history.append(authorization)

            # --- CP3: Pipeline Trace - Risk Authorization ---
            from core_engine.utils.pipeline_trace import get_tracer, CP3_RISK_AUTH
            _cp3_tracer = get_tracer()
            if _cp3_tracer.enabled:
                _cp3_is_authorized = authorization.authorization_level != AuthorizationLevel.REJECTED
                _cp3_tracer.emit(
                    trace_id=getattr(request, 'root_signal_id', '') or request.request_id,
                    checkpoint=CP3_RISK_AUTH,
                    component="CentralRiskManager",
                    method="authorize_trading_decision",
                    symbol=request.symbol,
                    bar_timestamp=request.metadata.get('timestamp', '') if request.metadata else '',
                    input_data={
                        "request_id": request.request_id,
                        "symbol": request.symbol,
                        "side": request.side,
                        "quantity": float(request.quantity),
                        "confidence": float(request.confidence),
                        "current_price": float(request.current_price),
                        "strategy_id": request.strategy_id,
                        "signal_type": (request.metadata or {}).get('signal_type', ''),
                        "strength": (request.metadata or {}).get('original_signal_metadata', {}).get('strength', 0),
                        "target_weight": (request.metadata or {}).get('target_weight'),
                    },
                    output_data={
                        "authorized": _cp3_is_authorized,
                        "authorization_id": getattr(authorization, 'authorization_id', ''),
                        "authorized_quantity": float(getattr(authorization, 'authorized_quantity', 0)),
                        "rejection_reason": getattr(authorization, 'rejection_reason', None),
                        "authorization_level": str(authorization.authorization_level),
                    },
                    metadata={
                        "authorized": _cp3_is_authorized,
                        "sizing_diagnostics": (request.metadata or {}).get('_sizing_diagnostics', {}),
                    },
                )

            return authorization

        except Exception as e:
            logger.error(f"Authorization process failed: {e}")
            return TradingAuthorization(request_id=request.request_id, 
                                      authorization_level=AuthorizationLevel.REJECTED,
                                      rejection_reason=str(e))

    async def _assess_trading_request(self, request: TradingDecisionRequest) -> TradingAuthorization:
        """Comprehensive risk assessment of trading request"""

        try:
            authorization = TradingAuthorization(
                request_id=request.request_id,
                root_signal_id=request.root_signal_id
            )

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
                    # P1-1 FIX: Fail-closed in ALL modes. The previous fail-open behavior
                    # in backtest mode hid real compliance issues during testing, meaning
                    # strategies could appear compliant in backtest but fail in production.
                    trading_mode = getattr(self, 'trading_mode', 'backtest')
                    logger.error(f"Compliance check failed (fail-closed, mode={trading_mode}): {e}")
                    authorization.authorization_level = AuthorizationLevel.REJECTED
                    authorization.rejection_reason = f"COMPLIANCE_ERROR: {e}"
                    return authorization

            # Input validation - reject invalid requests early
            validation_error = self._validate_request_inputs(request)
            if validation_error:
                authorization.authorization_level = AuthorizationLevel.REJECTED
                authorization.rejection_reason = validation_error
                logger.warning(f"Request rejected due to invalid input: {validation_error}")
                return authorization

            # PHASE 2: Regime Risk Gate (Pre-emptive)
            regime_error = self._check_regime_gate(request)
            if regime_error:
                authorization.authorization_level = AuthorizationLevel.REJECTED
                authorization.rejection_reason = regime_error
                logger.warning(f"Request rejected by Regime Gate: {regime_error}")
                return authorization

            # ADS v3.1 §8: PVSI cooldown gate (entry-only)
            if (
                self.config.enable_ads_cooldown
                and request.decision_type == TradingDecisionType.POSITION_ENTRY
                and request.side
                and request.side.lower() == "buy"
                and request.strategy_id
            ):
                cd = self._strategy_cooldowns.get(request.strategy_id)
                if cd is not None and cd.needs_cooldown():
                    pvsi = 0.0
                    try:
                        pvsi = float(cd.compute())
                    except Exception:
                        pvsi = 0.0

                    mode = str(getattr(self.config, "ads_cooldown_mode", "block_entries")).lower()
                    if mode == "scale_entries":
                        # Apply scaling later in sizing/quantity calc
                        request.metadata["ads_cooldown_scale"] = 0.5
                        request.metadata["ads_pvsi"] = pvsi
                        request.metadata["ads_cooldown_active"] = True
                        logger.warning(f"⚠️ PVSI cooldown active for {request.strategy_id}: PVSI={pvsi:.2f} (scaling entries)")
                    else:
                        authorization.authorization_level = AuthorizationLevel.REJECTED
                        authorization.rejection_reason = f"PVSI_COOLDOWN: PVSI={pvsi:.2f} >= {self.config.pvsi_threshold}"
                        logger.warning(f"🚫 Entry blocked by PVSI cooldown for {request.strategy_id}: PVSI={pvsi:.2f}")
                        return authorization

            # ----------------------------------------------------------------
            # CRITICAL: Quantity unit normalization (PERCENTAGE -> shares)
            # StrategyManager may pass quantity as a *weight* (e.g., 0.10 = 10%),
            # which must be converted to shares before any min(request.quantity, ...)
            # enforcement or cash checks.
            # ----------------------------------------------------------------
            try:
                if request.decision_type == TradingDecisionType.POSITION_ENTRY and request.side.lower() == "buy":
                    meta = request.metadata or {}
                    orig = meta.get("original_signal_metadata", {}) or {}
                    quantity_type = str(meta.get("quantity_type", orig.get("quantity_type", "")) or "").upper()

                    # Prefer explicit target_weight; fall back to strategy target_weight if present
                    target_weight = meta.get("target_weight", orig.get("target_weight", None))
                    if target_weight is None:
                        # Some signals store percentage under position_size
                        target_weight = orig.get("position_size", None)

                    price = float(request.current_price or meta.get("price", 0.0) or self.current_prices.get(request.symbol, 0.0) or 0.0)

                    if quantity_type == "PERCENTAGE" and target_weight is not None and price > 0:
                        tw = float(target_weight)
                        # Guard against percent-as-100 (e.g., 10 instead of 0.10)
                        if tw > 1.0:
                            tw = tw / 100.0

                        tw = max(0.0, min(1.0, tw))
                        computed_qty = (float(self.portfolio_value) * tw) / price

                        # P1-2 FIX: Store the computed share quantity in metadata
                        # instead of mutating request.quantity, which changes the
                        # meaning of the field and confuses downstream consumers
                        # that may inspect the original request.
                        meta["authorized_quantity_shares"] = float(computed_qty)
                        meta["original_quantity"] = request.quantity

                        # Still set request.quantity for backward compatibility,
                        # but document the mutation clearly
                        request.quantity = float(computed_qty)

                        # Provide cash/price hints for later checks
                        if "price" not in meta:
                            meta["price"] = price
                        if "available_cash" not in meta:
                            meta["available_cash"] = float(self.available_cash)
                        meta["computed_from_target_weight"] = True
                        meta["target_weight"] = tw
                        meta["quantity_type"] = "ABSOLUTE"
                        request.metadata = meta
            except Exception as e:
                logger.debug(f"Quantity normalization failed (continuing with raw quantity): {e}")

            # Risk impact assessment
            risk_impact = self._calculate_risk_impact(request)

            # CHECK 6 (Rule 3): Daily VaR hard gate
            try:
                current_var = self.risk_metrics.get('var_utilization', 0.0)
                max_daily_var = self.max_daily_var  # From RiskConfig
                if current_var > max_daily_var:
                    authorization.authorization_level = AuthorizationLevel.REJECTED
                    authorization.rejection_reason = (
                        f"Daily VaR limit exceeded: {current_var:.2%} > {max_daily_var:.2%}"
                    )
                    logger.warning(f"🚫 VaR gate: {authorization.rejection_reason}")
                    return authorization
            except Exception as e:
                logger.debug(f"VaR gate check skipped (data unavailable): {e}")

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
                # Never authorize MORE than was requested (critical for deterministic sizing + governance)
                if request.quantity and request.quantity > 0:
                    authorization.authorized_quantity = min(float(request.quantity), float(authorized_qty))
                else:
                    authorization.authorized_quantity = float(authorized_qty)
                authorization.max_quantity = authorization.authorized_quantity

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
                expires_at=authorization.expires_at,
                root_signal_id=authorization.root_signal_id
            )

            # Create execution request
            execution_request = ExecutionRequest(
                authorization=execution_auth,
                root_signal_id=authorization.root_signal_id,
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
            # AXIS1 FIX: Guard against zero portfolio_value
            position_impact = (request.quantity * price) / self.portfolio_value if self.portfolio_value > 0 else 1.0

            # Adjust for volatility
            volatility_adjustment = max(1.0, request.volatility_estimate)

            # Total risk impact (without regime adjustment, added later in authorization)
            total_impact = position_impact * volatility_adjustment

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
            # AXIS1 FIX: Guard against zero portfolio_value
            position_pct = position_value / self.portfolio_value if self.portfolio_value > 0 else 1.0

            # Use small tolerance for floating point comparisons (Rule 3)
            # This prevents rejections due to tiny precision errors (e.g. 10.000000000000001% > 10.0%)
            tolerance = 1e-5
            passed = position_pct <= (self.max_position_size + tolerance)

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
            # AXIS1 FIX: Guard against zero portfolio_value
            concentration = position_value / self.portfolio_value if self.portfolio_value > 0 else 1.0

            # Use small tolerance for floating point comparisons (Rule 3)
            tolerance = 1e-6
            passed = concentration <= (self.position_concentration_limit + tolerance)

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

    def _check_regime_gate(self, request: TradingDecisionRequest) -> Optional[str]:
        """
        Gate 4: Pre-emptive Regime Risk Gate
        Blocks or scales entries during high-risk regimes (Crisis, Bear High Vol)
        """
        if not self.regime_engine:
            return None

        # Access current regime context
        try:
            regime_state = self.regime_engine.get_current_regime()
            if not regime_state:
                return None

            # Check if high risk (Crisis, Extreme Vol, etc.)
            regime = regime_state.primary_regime
            
            # Only block entries, allow exits (important!)
            is_entry = request.decision_type in (
                TradingDecisionType.POSITION_ENTRY, 
                TradingDecisionType.STRATEGY_ACTIVATION
            )
            
            if is_entry and regime.is_high_risk():
                return f"REGIME_GATE: Current regime {regime.value} is high-risk. Entries blocked."

        except Exception as e:
            logger.warning(f"Error checking regime gate: {e}")
            
        return None

    def _check_strategy_limits(self, request: TradingDecisionRequest) -> bool:
        """Check strategy allocation limits"""

        try:
            current_allocation = self.strategy_allocations.get(request.strategy_id, 0.0)
            return current_allocation <= self.strategy_allocation_limit

        except Exception as e:
            logger.error(f"Error checking strategy limits: {e}")
            return False

    def _get_regime_risk_adjustment(self, request: TradingDecisionRequest) -> float:
        """
        Get regime-based risk adjustment multiplier.
        Uses the dynamic self.risk_multiplier from the RegimeManager (Rule 1, Section 7).
        """
        # If we have a system-wide risk multiplier, use it directly
        # It's already calculated based on primary regime and confidence
        return self.risk_multiplier

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
        ARCHITECTURAL FIX: Calculate authorized quantity with proper cash, position and regime validation
        """

        try:
            # Start with requested quantity
            authorized_qty = request.quantity

            # P3: Build scaling diagnostics for trace transparency
            _diag = {
                'requested_quantity': float(request.quantity),
                'scaling_factors': {},
                'constraints_applied': [],
            }
            
            # CRITICAL FIX: Enhanced cash availability check for BUY orders
            if request.side.lower() == 'buy':
                # Get available cash from request metadata or use conservative default
                available_cash = request.metadata.get('available_cash', self.portfolio_value * 0.95)
                price = request.metadata.get('price', request.current_price or 100.0)  # Prefer request.current_price
                required_cash = authorized_qty * price

                logger.info(f"💰 Cash check: Need ${required_cash:,.2f}, Available ${available_cash:,.2f}")

                if required_cash > available_cash:
                    # Calculate maximum affordable quantity
                    max_affordable_qty = available_cash / price

                    if max_affordable_qty < 0.01:  # Less than 0.01 shares affordable
                        logger.warning(f"🔒 BUY rejected: Insufficient cash. Need ${required_cash:,.2f}, have ${available_cash:,.2f}")
                        _diag['constraints_applied'].append('cash_rejected')
                        request.metadata['_sizing_diagnostics'] = _diag
                        return 0.0
                    else:
                        logger.info(f"🔒 BUY order capped by cash: requested {authorized_qty}, "
                                   f"affordable {max_affordable_qty:.2f}, authorized {max_affordable_qty:.2f}")
                        _diag['constraints_applied'].append(f'cash_cap:{authorized_qty:.2f}->{max_affordable_qty:.2f}')
                        authorized_qty = max_affordable_qty

            # CRITICAL FIX: Position-aware SELL order capping with exact precision
            elif request.side.lower() == 'sell':
                # ALWAYS use internal position tracking for SELL orders (most authoritative source)
                # request.current_position may be stale or default to 0.0
                current_position = self.current_positions.get(request.symbol, 0.0)

                if current_position <= 0 and not getattr(self.config, 'allow_shorts', False):
                    # No position to sell and short selling not allowed
                    logger.warning(f"🔒 SELL rejected: No position in {request.symbol} and short selling not allowed")
                    _diag['constraints_applied'].append('no_position_no_shorts')
                    request.metadata['_sizing_diagnostics'] = _diag
                    return 0.0
                elif current_position > 0:
                    # Cap SELL quantity by actual position with exact precision
                    max_sellable = abs(current_position)
                    if authorized_qty > max_sellable:
                        logger.info(f"🔒 SELL order capped: requested {authorized_qty:.2f}, "
                                   f"available {max_sellable:.2f}, authorized {max_sellable:.2f}")
                        _diag['constraints_applied'].append(f'position_cap:{authorized_qty:.2f}->{max_sellable:.2f}')
                        authorized_qty = max_sellable

            # F6 FIX: Skip risk/regime/vol/confidence scaling for exits.
            # Exit signals should close the full position — scaling them down
            # leaves residual positions that drift with no active management.
            if request.decision_type == TradingDecisionType.POSITION_EXIT:
                _diag['scaling_factors']['exit_bypass'] = True
                request.metadata['_sizing_diagnostics'] = _diag
                return max(0.0, authorized_qty)

            # Apply risk-based adjustment (entries only)
            if risk_impact > self.config.auto_approval_threshold:
                # Reduce quantity for higher risk
                risk_reduction = min(0.5, (risk_impact - self.config.auto_approval_threshold) * 2)
                authorized_qty *= (1.0 - risk_reduction)

            # PROFESSIONAL REGIME-BASED SCALING
            current_regime = request.market_regime
            if current_regime == "unknown" and self.regime_engine:
                try:
                    regime_state = self.regime_engine.get_current_regime()
                    if regime_state:
                        current_regime = regime_state.primary_regime.value
                except Exception:
                    pass

            # Phase 1: Direct Regime Scaling Factor (Regime-First Architecture)
            # Use the centrally computed regime_adjustment (multiplier)
            regime_scaling = regime_adjustment
            
            # Phase 2: Supplemental Volatility Scaling
            volatility_estimate = getattr(request, 'volatility_estimate', request.metadata.get('volatility_estimate', 0.15))
            vol_scaling = 1.0
            if volatility_estimate > 0.40:
                vol_scaling = 0.5 # 50% haircut for extreme realized vol
            elif volatility_estimate > 0.25:
                vol_scaling = 0.8 # 20% haircut for elevated vol
            elif volatility_estimate < 0.10:
                vol_scaling = 1.1 # 10% boost for quiet markets
            
            # Phase 3: Confidence-Based Scaling (Alpha filter)
            confidence_scaling = 1.0
            if request.confidence < 0.6:
                confidence_scaling = 0.5 # Halve size for marginal signals
            elif request.confidence > 0.9:
                confidence_scaling = 1.2 # Turbocharge high confidence

            # Combine scaling factors (multiplicative for compounding safety)
            combined_scaling = regime_scaling * vol_scaling * confidence_scaling
            
            # Absolute max scaling boost is 1.25x for safety
            combined_scaling = min(1.25, combined_scaling)
            
            previous_qty = authorized_qty
            authorized_qty *= combined_scaling

            # P3: Record scaling diagnostics
            _diag['scaling_factors'] = {
                'regime_scaling': regime_scaling,
                'vol_scaling': vol_scaling,
                'confidence_scaling': confidence_scaling,
                'combined_scaling': combined_scaling,
                'regime': current_regime,
                'volatility_estimate': volatility_estimate,
                'confidence': request.confidence,
                'qty_before_scaling': previous_qty,
                'qty_after_scaling': authorized_qty,
            }
            
            if abs(combined_scaling - 1.0) > 0.01:
                logger.info(f"🌊 Regime Scaling: {current_regime} | Vol: {volatility_estimate:.2f} | "
                           f"Conf: {request.confidence:.2f} | Total Scaler: {combined_scaling:.2f} | "
                           f"Qty: {previous_qty:.2f} -> {authorized_qty:.2f}")

            # ADS v3.1: apply cooldown scaling if requested by assessment
            cooldown_scale = float(request.metadata.get("ads_cooldown_scale", 1.0))
            if cooldown_scale < 1.0:
                authorized_qty *= max(0.0, cooldown_scale)

            # ADS v3.1 §7: fractional Kelly sizing (entry scaling; RiskManager enforces caps)
            if (
                getattr(self.config, "enable_fractional_kelly_sizing", False)
                and request.decision_type == TradingDecisionType.POSITION_ENTRY
                and request.side.lower() == "buy"
                and request.strategy_id
            ):
                try:
                    price = float(request.metadata.get("price", request.current_price or 100.0))
                    if price > 0:
                        # Extract signal strength in [0,1] from original signal metadata when available
                        sig_meta = request.metadata.get("original_signal_metadata", {}) or {}
                        signal_strength = sig_meta.get("signal_strength", None)
                        if signal_strength is None:
                            signal_strength = sig_meta.get("strength", None)
                        if signal_strength is None:
                            # Sometimes strategies express size as weight; treat as strength proxy
                            signal_strength = sig_meta.get("target_weight", sig_meta.get("position_size", request.confidence))
                        signal_strength = float(signal_strength) if signal_strength is not None else float(request.confidence)
                        signal_strength = max(0.0, min(1.0, signal_strength))

                        # Liquidity factor best-effort: if strategy provided one, use it; else default 1.0
                        liquidity_factor = float(sig_meta.get("liquidity_factor", 1.0))
                        liquidity_factor = max(0.0, min(1.0, liquidity_factor))

                        # Drawdown state from risk manager portfolio value tracking
                        current_dd = 0.0
                        if self._portfolio_hwm > 0:
                            current_dd = max(0.0, (float(self._portfolio_hwm) - float(self.portfolio_value)) / float(self._portfolio_hwm))
                        max_dd = float(getattr(self.config.risk_limits, "max_drawdown", 0.10))

                        # Regime factor: use risk multiplier already applied by on_regime_change
                        regime_factor = float(getattr(self, "risk_multiplier", 1.0))

                        # Per-strategy trade outcomes (risk-normalized return proxy)
                        pnls = self._strategy_trade_outcomes.get(request.strategy_id, [])

                        # IMPORTANT: Do not apply Kelly sizing until sufficient sample size exists.
                        # Before min_trades, keep the strategy's requested sizing (target_weight / base sizing)
                        # to avoid collapsing to tiny positions from priors.
                        min_trades = int(getattr(self.config, "kelly_min_trades", 30))
                        if len(pnls) < min_trades:
                            pnls = []  # explicit: skip Kelly cap entirely

                        kp = KellyParams(
                            kelly_frac=float(getattr(self.config, "kelly_frac", 0.33)),
                            kelly_min=float(getattr(self.config, "kelly_min", 0.02)),
                            kelly_max=float(getattr(self.config, "kelly_max", 0.20)),
                            prior_a=float(getattr(self.config, "kelly_prior_a", 5.0)),
                            prior_b=float(getattr(self.config, "kelly_prior_b", 5.0)),
                            min_trades=min_trades,
                            uncertainty_floor=float(getattr(self.config, "kelly_uncertainty_floor", 0.3)),
                            dd_gamma=float(getattr(self.config, "kelly_dd_gamma", 2.0)),
                        )

                        if not pnls:
                            # Skip Kelly (insufficient sample)
                            raise RuntimeError("kelly_insufficient_trades")

                        res = compute_fractional_kelly_fraction_of_capital(
                            signal_strength=signal_strength,
                            pnls=pnls,
                            liquidity_factor=liquidity_factor,
                            current_dd=current_dd,
                            max_dd=max_dd,
                            regime_factor=regime_factor,
                            params=kp,
                        )

                        desired_qty = (float(self.portfolio_value) * float(res.target_fraction_of_capital)) / price
                        if desired_qty >= 0:
                            authorized_qty = min(float(authorized_qty), float(desired_qty))
                            request.metadata["ads_kelly"] = res.diagnostics
                            request.metadata["ads_kelly_target_fraction"] = float(res.target_fraction_of_capital)
                except Exception as e:
                    logger.debug(f"Kelly sizing failed (fallback to requested quantity): {e}")

            # FINAL CASH CONSTRAINT: Ensure BUY orders don't exceed available cash
            if request.side.lower() == 'buy':
                available_cash = request.metadata.get('available_cash', self.portfolio_value * 0.95)
                price = request.metadata.get('price', request.current_price or 100.0)
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

            # Precision: keep full float precision for fractional-share parity.
            # Only snap extremely small residuals to 0 to avoid position “dust”.
            authorized_qty = float(authorized_qty)
            if abs(authorized_qty) < 1e-6:
                authorized_qty = 0.0
            authorized_qty = max(0.0, authorized_qty)

            # P3: Store final diagnostics
            _diag['authorized_quantity'] = authorized_qty
            _diag['reduction_ratio'] = authorized_qty / request.quantity if request.quantity > 0 else 0.0
            request.metadata['_sizing_diagnostics'] = _diag

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
            # P2-24 FIX: The original formula `new_position * 100.0 / portfolio_value` treats
            # new_position as a dollar value, but if new_position is in shares, this is wrong.
            # Use the latest price from market data to convert shares to dollar exposure.
            # Fallback to the original formula if price is unavailable.
            latest_price = self._get_latest_price(symbol) if hasattr(self, '_get_latest_price') else None
            if latest_price and latest_price > 0:
                position_value = abs(new_position * latest_price)
            else:
                # Fallback: assume new_position is already a dollar value
                position_value = abs(new_position)
            position_pct = (position_value / self.portfolio_value * 100.0) if self.portfolio_value > 0 else 100.0

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

    async def update_position(self, symbol: str, side: str, quantity: float, price: float = 0.0, timestamp: Optional[datetime] = None, strategy_id: str = "", metadata: Optional[Dict[str, Any]] = None, **kwargs):
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
            strategy_id: Optional strategy identifier for attribution

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

                # F3 FIX: Respect backtest_fill flag — when True, the
                # HistoricalExecutionSimulator has already embedded all costs
                # (spread, impact, slippage, commission) into fill_price.
                # Applying commission again double-counts.
                is_backtest_fill = kwargs.get('backtest_fill', False)
                if is_backtest_fill:
                    commission = 0.0
                else:
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
                    timestamp=timestamp,
                    strategy_id=strategy_id,
                    metadata=metadata or {}
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
                                strategy_id=strategy_id,
                                timestamp=timestamp
                            )
                        elif side.lower() == 'sell':
                            await self.pnl_tracker.update_position_close(
                                symbol=symbol,
                                quantity=quantity,
                                exit_price=price,
                                strategy_id=strategy_id,
                                timestamp=timestamp
                            )
                        # P1: Record cost attribution from execution simulator
                        _cost_attr_data = (metadata or {}).get('cost_attribution', {})
                        if _cost_attr_data:
                            self.pnl_tracker.record_cost_attribution(
                                symbol=symbol,
                                cost_attribution=_cost_attr_data,
                                strategy_id=strategy_id,
                            )
                    except Exception as e:
                        logger.warning(f"⚠️ P&L tracker update failed: {e}")

                # Return compatible result
                # Handle case where position is fully closed (position is None)
                book_position = position_update.position
                new_quantity = Decimal('0') if book_position is None else book_position.quantity

                logger.info(
                    f"[PB] PositionBook Update: {symbol} -> {float(new_quantity):.2f} shares | "
                    f"Realized P&L: ${float(position_update.realized_pnl):,.2f} | "
                    f"Cash: ${float(self._position_book.get_cash_balance()):,.2f}"
                )

                # Extract cost attribution from fill metadata (propagated from execution simulator)
                _cost_attr = (metadata or {}).get('cost_attribution', {})

                _result = {
                    'success': True,
                    'symbol': symbol,
                    'previous_position': float(position_update.previous_quantity),
                    'new_position': float(new_quantity),
                    'position_value': float(new_quantity * Decimal(str(price))),
                    'cash_change': float(position_update.cash_change),
                    'available_cash': float(self._position_book.get_cash_balance()),
                    'portfolio_value': self.portfolio_value,
                    'timestamp': timestamp,
                    'realized_pnl': float(position_update.realized_pnl),
                    'cost_attribution': _cost_attr,
                }

                # --- CP7: Pipeline Trace - PnL Calculation ---
                from core_engine.utils.pipeline_trace import get_tracer, CP7_PNL
                _cp7_tracer = get_tracer()
                if _cp7_tracer.enabled:
                    realized_pnl = float(position_update.realized_pnl)
                    unrealized_pnl = 0.0
                    total_pnl = 0.0
                    position_pnl = 0.0
                    cost_basis = 0.0

                    if hasattr(self, 'pnl_tracker') and self.pnl_tracker:
                        realized_pnl = float(self.pnl_tracker.realized_pnl)
                        unrealized_pnl = float(self.pnl_tracker.unrealized_pnl)
                        total_pnl = float(self.pnl_tracker.total_pnl)
                        position_pnl = float(self.pnl_tracker.position_pnl.get(symbol, 0.0))
                        cost_basis = float(self.pnl_tracker.position_cost_basis.get(symbol, 0.0))
                    else:
                        try:
                            unrealized_pnl = float(self._position_book.get_unrealized_pnl())
                        except Exception:
                            unrealized_pnl = 0.0
                        total_pnl = realized_pnl + unrealized_pnl

                    if total_pnl == 0.0 and (realized_pnl != 0.0 or unrealized_pnl != 0.0):
                        total_pnl = realized_pnl + unrealized_pnl

                    _cp7_tracer.emit(
                        trace_id=fill.fill_id,
                        checkpoint=CP7_PNL,
                        component="CentralRiskManager",
                        method="update_position",
                        symbol=symbol,
                        bar_timestamp=str(timestamp),
                        input_data={
                            "fill_id": fill.fill_id,
                            "side": side,
                            "quantity": float(quantity),
                            "price": float(price),
                            "previous_position": float(position_update.previous_quantity),
                            "previous_quantity": float(position_update.previous_quantity),
                            "new_position": float(new_quantity),
                            "new_quantity": float(new_quantity),
                            "cost_basis": cost_basis,
                            "event_type": position_update.event_type.value if hasattr(position_update.event_type, 'value') else str(position_update.event_type),
                            "realized_pnl": float(position_update.realized_pnl),
                            "cash_change": float(position_update.cash_change),
                            "new_avg_price": float(position_update.new_avg_price),
                            "total_realized_pnl": float(self._position_book._total_realized_pnl),
                        },
                        output_data={
                            "realized_pnl": realized_pnl,
                            "unrealized_pnl": unrealized_pnl,
                            "total_pnl": total_pnl,
                            "position_pnl": position_pnl,
                            "cash_change": float(position_update.cash_change),
                            "cash_balance": float(self._position_book.get_cash_balance()),
                            "portfolio_value": self.portfolio_value,
                        },
                        metadata={
                            "positions_count": len(self.current_positions),
                            "total_realized_pnl": float(self._position_book._total_realized_pnl),
                            "cost_attribution": _cost_attr,
                        },
                    )

                return _result

            # ============================================================
            # LEGACY PATH: Direct position tracking (backward compatibility)
            # ============================================================
            current_position = self.current_positions.get(symbol, 0.0)
            previous_cash = self.available_cash

            # H4 COST OWNERSHIP BOUNDARY:
            # In backtest mode, the HistoricalExecutionSimulator has ALREADY
            # embedded all transaction costs (spread, impact, slippage, commission)
            # into the fill_price. The price passed here IS the cost-adjusted fill.
            # Therefore, we set transaction_cost = 0 in backtest mode to avoid
            # double-counting. In live/paper mode, the broker fill price is the
            # raw fill and costs must be deducted separately.
            is_backtest_fill = kwargs.get('backtest_fill', False)
            if is_backtest_fill:
                commission = 0.0
                slippage_cost = 0.0
            else:
                commission = max(1.0, quantity * price * 0.00005)  # Greater of $1 or 0.50 bps
                slippage_bps = 0.5
                slippage_cost = quantity * price * (slippage_bps / 10000)

            total_transaction_cost = commission + slippage_cost

            # Calculate new position and cash impact
            if side.lower() == 'buy':
                new_position = current_position + quantity
                cash_change = -(quantity * price)  # Cash decreases for purchase
                cash_change -= total_transaction_cost  # Subtract transaction costs

                # H4 R3 FIX + C2 R4 FIX: Cash balance gate.
                # If covering a short, only the EXCESS portion (going long beyond
                # the cover) requires cash. A pure cover frees margin, not spends cash.
                is_covering_short = current_position < 0
                if is_covering_short:
                    cover_qty = min(quantity, abs(current_position))
                    excess_long_qty = quantity - cover_qty
                    if excess_long_qty > 0:
                        # AXIS3 FIX: The FULL trade costs cash = quantity * price + costs.
                        # The cover portion costs cover_qty * price in cash outflow.
                        # The excess portion costs excess_long_qty * price.
                        # Validate the TOTAL won't make cash negative.
                        if (self.available_cash + cash_change) < 0:
                            logger.warning(
                                f"❌ BUY REJECTED: {symbol} {quantity} @ ${price:.2f} — "
                                f"covers {cover_qty} short + excess {excess_long_qty} long "
                                f"total cash impact ${cash_change:,.2f} exceeds "
                                f"available ${self.available_cash:,.2f}"
                            )
                            return {
                                'success': False,
                                'error': f'Insufficient cash for cover+long reversal'
                            }
                elif (self.available_cash + cash_change) < 0:
                    logger.warning(
                        f"❌ BUY REJECTED: {symbol} {quantity} @ ${price:.2f} — "
                        f"insufficient cash (${self.available_cash:,.2f} + ${cash_change:,.2f} < 0)"
                    )
                    return {
                        'success': False,
                        'error': f'Insufficient cash: need ${abs(cash_change):,.2f}, have ${self.available_cash:,.2f}'
                    }

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

            # Update position - remove from dict if closed
            if new_position != 0.0:
                self.current_positions[symbol] = new_position
            else:
                # Position fully closed - remove from dict
                if symbol in self.current_positions:
                    del self.current_positions[symbol]
                    logger.debug(f"📘 current_positions[{symbol}] removed (position closed)")

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

            # C4 R3 FIX: Compute realized P&L for the legacy path (no PositionBook).
            # Logic: closing or reducing a position realizes P&L. Opening increases
            # the cost basis. Direction is inferred from current_position sign.
            realized_pnl = 0.0
            is_closing = False
            if side.lower() == 'buy' and current_position < 0:
                # Buying to cover a short — this is a close
                close_qty = min(quantity, abs(current_position))
                avg_entry = getattr(self, '_avg_entry_prices', {}).get(symbol, price)
                realized_pnl = close_qty * (avg_entry - price)  # Short P&L: entry - exit
                is_closing = True
            elif side.lower() == 'sell' and current_position > 0:
                # Selling a long — this is a close
                close_qty = min(quantity, current_position)
                avg_entry = getattr(self, '_avg_entry_prices', {}).get(symbol, price)
                realized_pnl = close_qty * (price - avg_entry)  # Long P&L: exit - entry
                is_closing = True

            # Update average entry price for new/increased positions
            if not hasattr(self, '_avg_entry_prices'):
                self._avg_entry_prices = {}

            if not is_closing:
                # Opening or adding to position — update avg entry
                existing_qty = abs(current_position)
                existing_entry = self._avg_entry_prices.get(symbol, 0.0)
                total_qty = existing_qty + quantity
                if total_qty > 0:
                    self._avg_entry_prices[symbol] = (
                        (existing_entry * existing_qty + price * quantity) / total_qty
                    )
            elif abs(new_position) < 1e-9:
                # Fully closed — remove entry price
                self._avg_entry_prices.pop(symbol, None)
            elif (current_position > 0 and new_position < 0) or \
                 (current_position < 0 and new_position > 0):
                # C1 R4 FIX: Position REVERSED (long→short or short→long).
                # The closing leg P&L was already computed above.
                # Now track the entry price for the NEW direction at current price.
                self._avg_entry_prices[symbol] = price

            # AXIS3 FIX: pnl_tracker integration with correct quantities.
            # For reversals, close the old leg with close_qty, then open the new leg.
            _strategy_id = kwargs.get('strategy_id', None)
            if hasattr(self, 'pnl_tracker') and self.pnl_tracker:
                try:
                    if is_closing:
                        # Use close_qty (not full quantity) — the actual closed portion
                        _close_qty = close_qty if close_qty > 0 else quantity
                        await self.pnl_tracker.update_position_close(
                            symbol=symbol,
                            quantity=_close_qty,
                            exit_price=price,
                            strategy_id=_strategy_id,
                            timestamp=timestamp
                        )
                        # For reversals, also record the opening leg of the new direction
                        _is_reversal = (
                            (current_position > 0 and new_position < 0) or
                            (current_position < 0 and new_position > 0)
                        )
                        if _is_reversal and abs(new_position) > 1e-9:
                            await self.pnl_tracker.update_position_entry(
                                symbol=symbol,
                                quantity=abs(new_position),
                                entry_price=price,
                                strategy_id=_strategy_id,
                                timestamp=timestamp
                            )
                    else:
                        await self.pnl_tracker.update_position_entry(
                            symbol=symbol,
                            quantity=quantity,
                            entry_price=price,
                            strategy_id=_strategy_id,
                            timestamp=timestamp
                        )
                    logger.debug(f"✅ P&L tracker updated for {symbol}")
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
                'timestamp': timestamp,
                'realized_pnl': realized_pnl,  # C4 R3 FIX: always present
            }

        except Exception as e:
            logger.error(f"Position update failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_current_position(self, symbol: str) -> float:
        """Get current SIGNED position for symbol.

        Returns positive for LONG, negative for SHORT, 0.0 for FLAT.

        ✅ PHASE 2: Queries PositionBook when available.
        P0-1 FIX: PositionBook stores quantity as always-positive with a
        separate ``side`` field. This method now applies the sign so that
        downstream consumers (Gate 3, concentration checks, sizing) receive
        the correct signed quantity.
        """
        if self._position_book is not None:
            position = self._position_book.get_position(symbol)
            if position is None:
                return 0.0
            raw_qty = float(position.quantity)
            # Apply sign: negative for SHORT, positive for LONG/FLAT
            if position.side.value == 'short':
                return -raw_qty
            return raw_qty
        return self.current_positions.get(symbol, 0.0)

    def get_all_positions(self) -> Dict[str, float]:
        """Get all current positions as SIGNED quantities.

        Returns positive for LONG, negative for SHORT.

        ✅ PHASE 2: Queries PositionBook when available.
        P0-1 FIX: Returns signed quantities from PositionBook.
        """
        if self._position_book is not None:
            result = {}
            for symbol, pos in self._position_book.get_all_positions().items():
                raw_qty = float(pos.quantity)
                if pos.side.value == 'short':
                    result[symbol] = -raw_qty
                else:
                    result[symbol] = raw_qty
            return result
        return self.current_positions.copy()

    def get_position_details(self) -> Dict[str, Dict[str, Any]]:
        """
        Get detailed position information including entry price and P&L

        Used by strategies for PRICE-AWARE decision making.

        Returns:
            Dict mapping symbol to position details:
            {
                'quantity': float,        # Current position size
                'entry_price': float,     # Average entry price (cost basis)
                'current_price': float,   # Current market price
                'unrealized_pnl': float,  # Unrealized P&L in dollars
                'pnl_pct': float,         # Unrealized P&L as percentage
                'is_profitable': bool     # True if position is profitable
            }
        """
        position_details = {}

        # Get all active positions
        all_positions = self.get_all_positions()

        for symbol, quantity in all_positions.items():
            if abs(quantity) < 0.001:  # Skip zero positions
                continue

            # Get entry price from P&L tracker
            entry_price = 0.0
            unrealized_pnl = 0.0

            if hasattr(self, 'pnl_tracker') and self.pnl_tracker:
                entry_price = self.pnl_tracker.position_cost_basis.get(symbol, 0.0)
                unrealized_pnl = self.pnl_tracker.position_pnl.get(symbol, 0.0)

            # Get current price
            current_price = self.current_prices.get(symbol, entry_price)

            # Calculate P&L percentage
            if entry_price > 0:
                if quantity > 0:  # Long position
                    pnl_pct = ((current_price - entry_price) / entry_price) * 100.0
                else:  # Short position
                    pnl_pct = ((entry_price - current_price) / entry_price) * 100.0
            else:
                pnl_pct = 0.0

            position_details[symbol] = {
                'quantity': quantity,
                'entry_price': entry_price,
                'current_price': current_price,
                'unrealized_pnl': unrealized_pnl,
                'pnl_pct': pnl_pct,
                'is_profitable': pnl_pct > 0
            }

        return position_details

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

        # ADS v3.1: maintain lightweight price history for σ_eff and Δρ
        for symbol, price in prices.items():
            try:
                p = float(price)
                if p > 0 and np.isfinite(p):  # type: ignore[name-defined]
                    self._price_history[symbol].append(p)
            except Exception:
                continue

        if hasattr(self, 'pnl_tracker') and self.pnl_tracker:
            try:
                if timestamp is None:
                    timestamp = datetime.now()

                # Use vectorized batch update for performance (Sprint 1 Enhancement)
                await self.pnl_tracker.update_market_data_batch(prices, timestamp)

                logger.debug(f"✅ Market prices updated for {len(prices)} symbols (Vectorized)")
            except Exception as e:
                logger.warning(f"⚠️ Market price update failed: {e}")

        # ✅ FIX: Update portfolio metrics after price update
        self._update_portfolio_metrics()

        # Update drawdown high-water mark (best-effort)
        try:
            self._portfolio_hwm = max(float(self._portfolio_hwm), float(self.portfolio_value))
        except Exception:
            pass

    # ========================================================================
    # ADS v3.1: COOLDOWN + TRADE OUTCOME TRACKING (from PositionBook events)
    # ========================================================================

    def _handle_position_update_ads(self, update: Any) -> None:
        """
        Consume PositionBook updates to maintain:
        - Per-strategy trade outcome history (for Kelly sizing)
        - Per-strategy PVSI cooldown state (ADS §8)
        - Exit-in-flight cleanup
        """
        try:
            symbol = getattr(update, "symbol", None)
            event_type = getattr(update, "event_type", None)
            event_name = getattr(event_type, "value", str(event_type)).lower() if event_type is not None else "unknown"

            # Cleanup exit-in-flight if position is closed
            if symbol and event_name == "closed":
                if symbol in self._exit_in_flight:
                    self._exit_in_flight.discard(symbol)

            # Track realized PnL on close for sizing/cooldown
            if event_name != "closed":
                return

            fill = getattr(update, "fill", None)
            strategy_id = getattr(fill, "strategy_id", "") if fill is not None else ""
            if not strategy_id:
                # If strategy_id missing, do not contaminate per-strategy stats
                return

            realized_pnl = getattr(update, "realized_pnl", None)
            prev_qty = getattr(update, "previous_quantity", None)
            prev_avg = getattr(update, "previous_avg_price", None)

            # Risk-normalized return proxy: realized_pnl / notional
            pnl_ret = 0.0
            try:
                notional = abs(float(prev_qty) * float(prev_avg)) if prev_qty is not None and prev_avg is not None else 0.0
                pnl = float(realized_pnl) if realized_pnl is not None else 0.0
                pnl_ret = (pnl / notional) if notional > 0 else 0.0
            except Exception:
                pnl_ret = 0.0

            # Store trade outcomes (cap size for memory)
            hist = self._strategy_trade_outcomes[strategy_id]
            hist.append(float(pnl_ret))
            if len(hist) > 2000:
                del hist[: len(hist) - 2000]

            # Update PVSI cooldown
            if self.config.enable_ads_cooldown:
                cd = self._strategy_cooldowns.get(strategy_id)
                if cd is None:
                    cd = Cooldown(
                        pnl_history=[],
                        regime_history=[],
                        threshold=float(self.config.pvsi_threshold),
                        baseline_window=int(self.config.pvsi_baseline_window),
                        recent_window=int(self.config.pvsi_recent_window),
                    )
                    self._strategy_cooldowns[strategy_id] = cd

                regime = getattr(getattr(self, "current_regime_context", None), "primary_regime", "unknown")
                cd.update(pnl=pnl_ret, regime=str(regime))

        except Exception as e:
            logger.debug(f"_handle_position_update_ads error: {e}")

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
            # ADS v3.1: multi-exit core monitoring (PositionBook preferred)
            if getattr(self.config, "enable_ads_multi_exit", False) and self.position_book is not None:
                now = datetime.now()
                positions = self.position_book.get_all_positions()

                benchmark = str(getattr(self.config, "corr_benchmark_symbol", "SPY"))
                bench_prices = list(self._price_history.get(benchmark, []))
                bench_returns: List[float] = []
                if len(bench_prices) >= 3:
                    bp = np.asarray(bench_prices, dtype=float)
                    bench_returns = list(np.diff(bp) / bp[:-1])

                for symbol, pos in positions.items():
                    try:
                        if symbol in self._exit_in_flight:
                            continue

                        pnl_pct = float(getattr(pos, "pnl_percent", 0.0))
                        opened_at = getattr(pos, "opened_at", now)

                        # Forward-looking volatility stop (% distance)
                        stop_loss_pct_val: Optional[float] = None
                        if getattr(self.config, "enable_forward_vol_stops", False):
                            sym_prices = list(self._price_history.get(symbol, []))
                            if len(sym_prices) >= 3:
                                sp = np.asarray(sym_prices, dtype=float)
                                sym_returns = list(np.diff(sp) / sp[:-1])

                                s_eff, s_real, s_fcst = sigma_eff(
                                    sym_returns,
                                    realized_window=int(getattr(self.config, "vol_realized_window", 20)),
                                    lambda_=float(getattr(self.config, "vol_ewma_lambda", 0.94)),
                                )
                                d_rho = correlation_change(
                                    sym_returns,
                                    bench_returns,
                                    short_window=int(getattr(self.config, "corr_short_window", 20)),
                                    long_window=int(getattr(self.config, "corr_long_window", 60)),
                                )
                                params = VolStopParams(
                                    k=float(getattr(self.config, "stop_k", 2.0)) * self.risk_multiplier,
                                    kappa=float(getattr(self.config, "stop_kappa", 0.5)),
                                    overnight_mult=float(getattr(self.config, "stop_overnight_mult", 1.5)),
                                )
                                sl_frac = stop_distance_pct(s_eff, delta_rho=d_rho, params=params, overnight=False)
                                stop_loss_pct_val = float(sl_frac) * 100.0
                                # Attach for diagnostics (optional)
                                _ = (s_real, s_fcst)

                        # Liquidity stop (best-effort; only if liquidity engine is injected)
                        liquidity_bad = False
                        liquidity_details: Optional[Dict[str, Any]] = None
                        if self.liquidity_engine is not None:
                            # Without OHLCV, liquidity engine will degrade to limited assessment
                            md = {"close": float(getattr(pos, "current_price", 0.0))}
                            try:
                                liq = self.liquidity_engine.assess_liquidity_score(symbol, md)
                                eff_spread = float(liq.get("effective_spread_bps", 0.0))
                                liq_reg = str(liq.get("liquidity_regime", "normal_liquidity"))
                                # Conservative trigger: very wide effective spread or crisis/illiquid regime
                                if eff_spread > 80.0 or ("crisis" in liq_reg) or ("illiquid" in liq_reg):
                                    liquidity_bad = True
                                    liquidity_details = {"effective_spread_bps": eff_spread, "liquidity_regime": liq_reg}
                            except Exception:
                                pass

                        # ==========================================================
                        # Transition Lifecycle: extract entry & current state
                        # for multi-dimensional health-based exits.
                        # ==========================================================
                        def _sf(v):
                            """Safe float conversion (None-safe)."""
                            if v is None:
                                return None
                            try:
                                return float(v)
                            except (TypeError, ValueError):
                                return None

                        pos_meta = getattr(pos, "metadata", None) or getattr(pos, "additional_data", None) or {}

                        # Entry state (from position metadata, captured at signal time)
                        _entry_coh = _sf(pos_meta.get("entry_coherence"))
                        _entry_accel = _sf(pos_meta.get("entry_composite_accel"))
                        _entry_vov = _sf(pos_meta.get("entry_vol_of_vol"))
                        _entry_ts = _sf(pos_meta.get("transition_score"))
                        _entry_cz = _sf(pos_meta.get("composite_z"))
                        # Causal chain entry state
                        _entry_flow = pos_meta.get("entry_flow_confirmed")

                        # Current state (from latest enriched data store)
                        _cur_coh = None
                        _cur_accel = None
                        _cur_vov = None
                        _cur_cz = None
                        _cur_short_mom = None
                        _cur_medium_mom = None
                        _cur_vol_ratio = None
                        try:
                            if hasattr(self, "_latest_enriched") and symbol in self._latest_enriched:
                                _enriched = self._latest_enriched[symbol]
                                _cur_coh = _sf(_enriched.get("directional_coherence"))
                                _cur_accel = _sf(_enriched.get("composite_accel_norm"))
                                _cur_vov = _sf(_enriched.get("vol_of_vol"))
                                _cur_cz = _sf(_enriched.get("composite_z"))
                                _cur_vol_ratio = _sf(_enriched.get("volume_ratio"))
                                # Resolve strategy-specific momentum columns
                                _short_col = pos_meta.get("entry_short_momentum_col", "momentum_10")
                                _medium_col = pos_meta.get("entry_medium_momentum_col", "momentum_20")
                                _cur_short_mom = _sf(_enriched.get(_short_col))
                                _cur_medium_mom = _sf(_enriched.get(_medium_col))
                        except Exception:
                            pass

                        # Config parameters
                        pos_is_long = getattr(pos, "is_long", True)
                        _health_crit = float(getattr(self.config, "health_critical_threshold", 0.15))
                        _accel_exhaust = float(getattr(self.config, "accel_exhaustion_threshold", -0.3))
                        _tp_init = float(getattr(self.config, "tp_initial_pct", 2.0))
                        _tp_floor = float(getattr(self.config, "tp_floor_pct", 0.3))
                        _tp_decay = float(getattr(self.config, "tp_decay_minutes", 30.0))
                        _health_tp = float(getattr(self.config, "health_tp_trigger", 0.7))

                        decision = decide_exit(
                            now=now,
                            opened_at=opened_at,
                            pnl_pct=pnl_pct,
                            is_long=pos_is_long,
                            stop_loss_pct=stop_loss_pct_val,
                            # Entry transition state
                            entry_coherence=_entry_coh,
                            entry_composite_accel=_entry_accel,
                            entry_vol_of_vol=_entry_vov,
                            entry_transition_score=_entry_ts,
                            entry_composite_z=_entry_cz,
                            # Causal chain entry state
                            entry_flow_confirmed=_entry_flow,
                            # Current transition state
                            current_coherence=_cur_coh,
                            current_composite_accel=_cur_accel,
                            current_vol_of_vol=_cur_vov,
                            current_composite_z=_cur_cz,
                            # Causal chain current state
                            current_short_momentum=_cur_short_mom,
                            current_medium_momentum=_cur_medium_mom,
                            current_volume_ratio=_cur_vol_ratio,
                            # Config
                            health_critical_threshold=_health_crit,
                            accel_exhaustion_threshold=_accel_exhaust,
                            tp_initial_pct=_tp_init,
                            tp_floor_pct=_tp_floor,
                            tp_decay_minutes=_tp_decay,
                            health_tp_trigger=_health_tp,
                            max_holding_minutes=float(getattr(self.config, "max_holding_minutes", 24 * 60)) * self.risk_multiplier,
                            liquidity_bad=liquidity_bad,
                            liquidity_details=liquidity_details,
                        )

                        if decision.should_exit:
                            # Trigger governed exit via authorization + execution
                            side = "sell" if getattr(pos, "is_long", True) else "buy"
                            qty = float(getattr(pos, "quantity", 0.0))
                            qty = abs(qty)
                            px = float(getattr(pos, "current_price", 0.0)) if getattr(pos, "current_price", 0.0) else float(self.current_prices.get(symbol, 100.0))
                            strategy_id = str(getattr(pos, "strategy_id", "")) or "unknown"

                            self._exit_in_flight.add(symbol)

                            req = TradingDecisionRequest(
                                decision_type=TradingDecisionType.POSITION_EXIT,
                                strategy_id=strategy_id,
                                symbol=symbol,
                                side=side,
                                quantity=qty,
                                confidence=1.0,
                                current_price=px,
                                urgency=ExecutionUrgency.URGENT,
                                requesting_component="RiskMonitor",
                                justification=f"ADS_MULTI_EXIT:{decision.reason}",
                                metadata={"ads_exit": decision.reason, "ads_exit_details": decision.details},
                            )

                            auth = await self.authorize_trading_decision(req)
                            if auth.authorization_level != AuthorizationLevel.REJECTED and auth.authorized_quantity > 0:
                                await self.execute_authorized_trade(
                                    auth,
                                    execution_params={"urgency": ExecutionUrgency.URGENT},
                                )
                            else:
                                # If rejected, clear exit-in-flight so it can be retried next cycle
                                self._exit_in_flight.discard(symbol)
                    except Exception as e:
                        logger.debug(f"ADS multi-exit monitoring error for {symbol}: {e}")

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

            async with self.authorization_lock:
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

    # ========================================
    # 6-GATE AUTHORIZATION PIPELINE (Paper Trading Evolution)
    # ========================================
    #
    # Gates (from plan Section 5):
    # - Gate 0: Circuit Breakers (existing)
    # - Gate 1: Session Gate
    # - Gate 2: Price-Aware Validation
    # - Gate 3: Position-Aware Validation
    # - Gate 4: Regime-Aware Adjustment
    # - Gate 5: P&L-Aware Risk Budget
    # - Gate 6: Final Authorization

    def set_session_gate(self, session_gate: Any) -> None:
        """Inject TradingSessionGate reference."""
        self._session_gate = session_gate
        logger.info("✅ TradingSessionGate injected into CentralRiskManager")

    def set_risk_budget(self, risk_budget: Any) -> None:
        """Inject RiskBudgetState reference."""
        self._risk_budget = risk_budget
        logger.info("✅ RiskBudgetState injected into CentralRiskManager")

    def set_price_source_config(
        self,
        mode: str = 'BAR_ONLY',
        adv_table: Optional[Dict[str, float]] = None,
        spread_table: Optional[Dict[str, float]] = None,
        default_adv: float = 1_000_000,
        default_spread_bps: float = 5.0,
        impact_coefficient: float = 10.0,
    ) -> None:
        """
        Configure price source for Gate 2.

        Args:
            mode: 'BAR_ONLY' or 'QUOTE_ENABLED'
            adv_table: Symbol -> 20-day ADV in shares
            spread_table: Symbol -> median spread in bps
            default_adv: Default ADV if symbol not in table
            default_spread_bps: Default spread if not available
            impact_coefficient: Market impact coefficient
        """
        self._price_source_mode = mode
        self._adv_table = adv_table or {}
        self._spread_table = spread_table or {}
        self._default_adv = default_adv
        self._default_spread_bps = default_spread_bps
        self._impact_coefficient = impact_coefficient

    # ================================================================
    # ENHANCED 6-GATE AUTHORIZATION PIPELINE (v2)
    #
    # Gate 0: Circuit Breakers       — binary kill-switch / halt check
    # Gate 1: Session Gate           — trading hours / session validity
    # Gate 2: Price Validation       — staleness + slippage estimation
    # Gate 3: Position Constraints   — hard cash/position/concentration limits
    # Gate 4: Multi-Factor Sizing    — regime × volatility × confidence scaling
    #                                  + exit bypass + Kelly cap
    # Gate 5: Risk Budget            — per-trade / daily loss budget check
    # Gate 6: Cost Gate (NEW)        — reject if estimated cost > expected edge
    # Gate 7: Final Authorization    — minimum order size + waterfall summary
    #
    # Architectural advantages over traditional path:
    # - Each gate emits timing + qty waterfall for full auditability
    # - Single unified exit with complete CP3 trace
    # - Cost-awareness prevents negative-expectancy trades
    # - Diagnostics dict attached to result for downstream analytics
    # ================================================================

    async def authorize_signal_6gate(
        self,
        signal: Dict[str, Any],
        current_price: float,
        portfolio_value: float,
    ) -> Dict[str, Any]:
        """
        Enhanced 6-Gate authorization pipeline (v2) with full quantity scaling,
        cost-awareness, and per-gate waterfall audit trail.

        Args:
            signal: Dict with keys:
                - symbol, side, requested_quantity, signal_strength, confidence
                - strategy_id, signal_timestamp, arrival_price
                - stop_price or stop_loss_pct
                - is_exit: bool (exit signals skip sizing scaling)
                - available_cash: float (for buy-side cash constraint)
                - target_weight, quantity_type, original_signal_metadata
            current_price: Latest price for validation
            portfolio_value: Current portfolio value

        Returns:
            Dict with: authorized, authorized_quantity, rejection_reason,
            gate_passed, estimated_fill_price, max_loss_estimate, gates (waterfall),
            sizing_diagnostics
        """
        import time as _time

        result = {
            'authorized': False,
            'authorized_quantity': 0.0,
            'rejection_reason': '',
            'gate_passed': 'NONE',
            'estimated_fill_price': current_price,
            'max_loss_estimate': 0.0,
            'gates': {},
            'sizing_diagnostics': {},
        }

        symbol = signal.get('symbol', '')
        side = signal.get('side', '')
        requested_qty = float(signal.get('requested_quantity', 0.0))
        arrival_price = signal.get('arrival_price', current_price)
        is_exit = signal.get('is_exit', False)
        candidate_qty = requested_qty
        _pipeline_t0 = _time.monotonic()

        # --- Waterfall: tracks qty at each gate boundary ---
        _waterfall = [{'gate': 'input', 'qty': candidate_qty}]

        def _record_gate(name: str, gate_result: Dict, qty_after: float, t0: float):
            """Attach timing and qty delta to gate result for audit."""
            gate_result['elapsed_us'] = int((_time.monotonic() - t0) * 1_000_000)
            gate_result['qty_in'] = _waterfall[-1]['qty']
            gate_result['qty_out'] = qty_after
            _waterfall.append({'gate': name, 'qty': qty_after})

        _done = False

        # ============================================================
        # GATE 0: Circuit Breakers (binary)
        # ============================================================
        _t0 = _time.monotonic()
        gate0 = self._gate0_circuit_breakers()
        _record_gate('G0_circuit_breakers', gate0, candidate_qty, _t0)
        result['gates']['G0_circuit_breakers'] = gate0

        if not gate0['passed']:
            result['rejection_reason'] = gate0['reason']
            _done = True

        # ============================================================
        # GATE 1: Session Gate
        # ============================================================
        if not _done:
            result['gate_passed'] = 'G0'
            _t0 = _time.monotonic()
            gate1 = self._gate1_session(symbol, signal.get('signal_timestamp'))
            _record_gate('G1_session', gate1, candidate_qty, _t0)
            result['gates']['G1_session'] = gate1

            if not gate1['passed']:
                result['rejection_reason'] = gate1['reason']
                _done = True

        # ============================================================
        # GATE 2: Price Validation + Slippage Estimation
        # ============================================================
        if not _done:
            result['gate_passed'] = 'G1'
            _t0 = _time.monotonic()
            gate2 = self._gate2_price_validation(
                symbol, side, candidate_qty, arrival_price, current_price
            )
            _record_gate('G2_price', gate2, candidate_qty, _t0)
            result['gates']['G2_price'] = gate2

            if not gate2['passed']:
                result['rejection_reason'] = gate2['reason']
                _done = True
            else:
                result['estimated_fill_price'] = gate2['estimated_fill_price']

        # ============================================================
        # GATE 3: Hard Position / Cash Constraints
        # (ported from traditional path's cash-cap + sell-cap logic)
        # ============================================================
        if not _done:
            result['gate_passed'] = 'G2'
            _t0 = _time.monotonic()
            gate3 = await self._gate3_position_constraints(
                symbol, side, candidate_qty, current_price, portfolio_value, signal
            )
            _record_gate('G3_position', gate3, gate3.get('capped_quantity', candidate_qty), _t0)
            result['gates']['G3_position'] = gate3

            if not gate3['passed']:
                result['rejection_reason'] = gate3['reason']
                _done = True
            else:
                candidate_qty = gate3['capped_quantity']

        # ============================================================
        # GATE 4: Multi-Factor Sizing
        # (regime × volatility × confidence scaling, exit bypass, Kelly)
        # Ported from _calculate_authorized_quantity
        # ============================================================
        if not _done:
            result['gate_passed'] = 'G3'
            _t0 = _time.monotonic()
            gate4 = self._gate4_multifactor_sizing(
                symbol, side, candidate_qty, signal, portfolio_value, current_price
            )
            _record_gate('G4_sizing', gate4, gate4.get('sized_quantity', candidate_qty), _t0)
            result['gates']['G4_sizing'] = gate4
            result['sizing_diagnostics'] = gate4.get('diagnostics', {})

            if not gate4['passed']:
                result['rejection_reason'] = gate4['reason']
                _done = True
            else:
                candidate_qty = gate4['sized_quantity']

        # ============================================================
        # GATE 5: Risk Budget (per-trade + daily loss budget)
        # ============================================================
        if not _done:
            result['gate_passed'] = 'G4'

            # Ensure risk budget has current portfolio value
            risk_budget = getattr(self, "_risk_budget", None)
            if risk_budget is not None and hasattr(risk_budget, "update_portfolio_value"):
                try:
                    risk_budget.update_portfolio_value(float(portfolio_value))
                except Exception:
                    pass

            stop_price = signal.get('stop_price')
            stop_loss_pct = signal.get('stop_loss_pct', 0.02)
            if stop_price is None:
                if side == 'buy':
                    stop_price = arrival_price * (1 - stop_loss_pct)
                else:
                    stop_price = arrival_price * (1 + stop_loss_pct)

            _t0 = _time.monotonic()
            gate5 = self._gate5_risk_budget(
                candidate_qty, result['estimated_fill_price'], stop_price, side
            )
            _record_gate('G5_risk_budget', gate5, min(candidate_qty, gate5.get('max_quantity', candidate_qty)), _t0)
            result['gates']['G5_risk_budget'] = gate5

            if not gate5['passed']:
                result['rejection_reason'] = gate5['reason']
                _done = True
            else:
                candidate_qty = min(candidate_qty, gate5.get('max_quantity', candidate_qty))
                result['max_loss_estimate'] = gate5.get('max_loss', 0.0)

        # ============================================================
        # GATE 6: Cost Gate (aligned with HistoricalExecutionSimulator)
        # Reject if estimated execution cost exceeds expected edge.
        # EXIT BYPASS: Exit signals always pass — cannot trap positions.
        # ============================================================
        if not _done:
            result['gate_passed'] = 'G5'
            # Propagate bar-level volume/volatility for cost model alignment
            self._last_bar_volume = float(signal.get('bar_volume', 0))
            self._last_bar_volatility = float(signal.get('bar_volatility', 0.02))
            _t0 = _time.monotonic()

            if is_exit:
                # Exit signals bypass cost gate — closing a position is mandatory
                gate6 = {
                    'passed': True,
                    'adjusted_quantity': candidate_qty,
                    'cost_bps': 0.0,
                    'expected_edge_bps': 0.0,
                    'cost_edge_ratio': 0.0,
                    'cost_dollars': 0.0,
                    'cost_breakdown': {},
                    'exit_bypass': True,
                }
            else:
                gate6 = self._gate6_cost_awareness(
                    symbol, side, candidate_qty, current_price,
                    signal.get('signal_strength', 0.5), result.get('estimated_fill_price', current_price)
                )
            _record_gate('G6_cost', gate6, gate6.get('adjusted_quantity', candidate_qty), _t0)
            result['gates']['G6_cost'] = gate6

            if not gate6['passed']:
                result['rejection_reason'] = gate6['reason']
                _done = True
            else:
                candidate_qty = gate6.get('adjusted_quantity', candidate_qty)

        # ============================================================
        # GATE 7: Final Authorization (minimum order + waterfall summary)
        # ============================================================
        if not _done:
            result['gate_passed'] = 'G6'

            min_order_size = 1.0
            try:
                pl = getattr(self.config, "position_limits", None)
                if pl is not None:
                    min_order_size = float(getattr(pl, "min_order_size", min_order_size))
            except Exception:
                min_order_size = 1.0

            # Precision: snap dust to 0
            if abs(candidate_qty) < 1e-6:
                candidate_qty = 0.0
            candidate_qty = max(0.0, candidate_qty)

            _t0 = _time.monotonic()
            if candidate_qty < min_order_size:
                gate7 = {
                    'passed': False,
                    'reason': f"Quantity {candidate_qty:.2f} below minimum {min_order_size}",
                    'min_order_size': min_order_size,
                }
                result['rejection_reason'] = gate7['reason']
            else:
                gate7 = {'passed': True, 'min_order_size': min_order_size}
                result['gate_passed'] = 'G7'
                result['authorized'] = True
                result['authorized_quantity'] = candidate_qty

            _record_gate('G7_final', gate7, candidate_qty, _t0)
            result['gates']['G7_final'] = gate7

        # --- Waterfall summary ---
        result['_waterfall'] = _waterfall
        result['_pipeline_elapsed_us'] = int((_time.monotonic() - _pipeline_t0) * 1_000_000)
        if requested_qty > 0:
            result['sizing_diagnostics']['reduction_ratio'] = candidate_qty / requested_qty
        result['sizing_diagnostics']['requested_quantity'] = requested_qty
        result['sizing_diagnostics']['final_quantity'] = candidate_qty

        # --- CP3: Pipeline Trace for ALL outcomes (auth + rejection) ---
        try:
            from core_engine.utils.pipeline_trace import get_tracer, CP3_RISK_AUTH
            _cp3_tracer = get_tracer()
            if _cp3_tracer.enabled:
                _cp3_tracer.emit(
                    trace_id=f"6gate_{symbol}",
                    checkpoint=CP3_RISK_AUTH,
                    component="CentralRiskManager",
                    method="authorize_signal_6gate",
                    symbol=symbol,
                    bar_timestamp=str(signal.get('signal_timestamp', '')),
                    input_data={
                        "symbol": symbol,
                        "side": side,
                        "quantity": float(requested_qty),
                        "signal_strength": float(signal.get('signal_strength', 0)),
                        "confidence": float(signal.get('confidence', 0)),
                        "arrival_price": float(arrival_price),
                        "stop_loss_pct": float(signal.get('stop_loss_pct', 0)),
                        "strategy_id": signal.get('strategy_id', ''),
                        "is_exit": is_exit,
                        "target_weight": signal.get('target_weight'),
                    },
                    output_data={
                        "authorized": result['authorized'],
                        "authorization_id": f"6gate_{symbol}",
                        "authorized_quantity": float(result['authorized_quantity']),
                        "rejection_reason": result['rejection_reason'] or None,
                        "authorization_level": "AUTOMATIC" if result['authorized'] else "REJECTED",
                        "gate_passed": result['gate_passed'],
                    },
                    metadata={
                        "authorized": result['authorized'],
                        "sizing_diagnostics": result['sizing_diagnostics'],
                        "waterfall": _waterfall,
                        "pipeline_elapsed_us": result['_pipeline_elapsed_us'],
                    },
                )
        except Exception:
            pass  # Trace emission must never break authorization

        return result

    # ----------------------------------------------------------------
    # Gate helper methods
    # ----------------------------------------------------------------

    def _gate0_circuit_breakers(self) -> Dict[str, Any]:
        """Gate 0: Check circuit breakers and kill switch."""
        if hasattr(self, 'circuit_breakers') and self.circuit_breakers:
            level = self.circuit_breakers.current_level
            if level in (CircuitBreakerLevel.HALT, CircuitBreakerLevel.EMERGENCY):
                return {'passed': False, 'reason': f'Circuit breaker tripped: {level.name}'}

        if getattr(self, '_kill_switch_active', False):
            return {'passed': False, 'reason': 'Kill switch active'}

        return {'passed': True}

    def _gate1_session(self, symbol: str, timestamp: Optional[datetime] = None) -> Dict[str, Any]:
        """Gate 1: Check session/trading hours (uses signal timestamp for determinism)."""
        session_gate = getattr(self, '_session_gate', None)

        if session_gate is None:
            return {'passed': True, 'reason': 'No session gate configured'}

        check_result = session_gate.check(timestamp=timestamp, symbol=symbol)

        if check_result.decision.name == 'ALLOW':
            return {'passed': True, 'session': check_result.current_session.name}
        else:
            return {'passed': False, 'reason': check_result.reason}

    def _gate2_price_validation(
        self,
        symbol: str,
        side: str,
        quantity: float,
        arrival_price: float,
        current_price: float,
    ) -> Dict[str, Any]:
        """Gate 2: Price-aware validation with slippage estimation."""
        import math

        adv_table = getattr(self, '_adv_table', {})
        spread_table = getattr(self, '_spread_table', {})
        default_adv = getattr(self, '_default_adv', 1_000_000)
        default_spread = getattr(self, '_default_spread_bps', 5.0)
        impact_coef = getattr(self, '_impact_coefficient', 10.0)

        adv = adv_table.get(symbol, default_adv)
        spread_bps = spread_table.get(symbol, default_spread)

        spread_cost_bps = spread_bps / 2
        participation = quantity / adv if adv > 0 else 0
        impact_cost_bps = math.sqrt(participation) * impact_coef
        slippage_bps = spread_cost_bps + impact_cost_bps

        if side == 'buy':
            estimated_fill = current_price * (1 + slippage_bps / 10000)
        else:
            estimated_fill = current_price * (1 - slippage_bps / 10000)

        # Check price move from arrival (stale signal detection)
        price_move_pct = abs(current_price - arrival_price) / arrival_price if arrival_price > 0 else 0
        stale_threshold = getattr(self.config, 'stale_signal_threshold_pct', 0.01)

        if price_move_pct > stale_threshold:
            return {
                'passed': False,
                'reason': f'Stale signal: price moved {price_move_pct:.1%} > {stale_threshold:.1%}',
                'price_move_pct': price_move_pct,
            }

        max_slippage = getattr(self.config, 'max_acceptable_slippage_bps', 50.0)
        if slippage_bps > max_slippage:
            return {
                'passed': False,
                'reason': f'Excessive slippage: {slippage_bps:.1f}bps > {max_slippage:.1f}bps',
                'slippage_bps': slippage_bps,
            }

        return {
            'passed': True,
            'estimated_fill_price': estimated_fill,
            'slippage_bps': slippage_bps,
            'spread_bps': spread_bps,
            'impact_bps': impact_cost_bps,
            'adv': adv,
            'participation_rate': participation,
        }

    async def _gate3_position_constraints(
        self,
        symbol: str,
        side: str,
        quantity: float,
        current_price: float,
        portfolio_value: float,
        signal: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Gate 3: Hard position and cash constraints (ported from traditional path).

        For BUY:  cap by available cash
        For SELL: cap by current position (no naked shorts unless configured)
        Both:     cap by max position concentration
        """
        constraints = []
        capped_qty = quantity

        # --- Resolve current position (SSOT: PositionBook > legacy map) ---
        # P0-1 FIX: Use get_current_position() which returns SIGNED quantity
        # (negative for shorts). Previously, reading pos.quantity directly
        # returned unsigned value, breaking sell-side and concentration checks
        # when allow_shorts=True.
        current_position = 0.0
        try:
            current_position = float(self.get_current_position(symbol) or 0.0)
        except Exception:
            current_position = 0.0

        # --- Pending exposure from OMS ---
        pending_buy_qty = 0.0
        pending_sell_qty = 0.0
        oms = getattr(self, "_oms", None) or getattr(self, "order_management_system", None)
        if oms and hasattr(oms, "get_pending_exposure"):
            try:
                pending = oms.get_pending_exposure(symbol)
                if pending:
                    pending_buy_qty = float(pending.get("pending_buy_qty", 0.0) or 0.0)
                    pending_sell_qty = float(pending.get("pending_sell_qty", 0.0) or 0.0)
            except Exception:
                pass
        pending_qty = pending_buy_qty - pending_sell_qty

        # --- BUY: Cash constraint ---
        if side == 'buy':
            # P0-2 FIX: Use actual tracked cash from PositionBook/CRM as default,
            # not the unreliable 95%-of-portfolio heuristic. The signal may
            # carry pre-committed cash (P0-3), so prefer signal > real cash > fallback.
            _real_cash = getattr(self, 'available_cash', portfolio_value * 0.95)
            available_cash = signal.get('available_cash', _real_cash)
            required_cash = capped_qty * current_price
            if required_cash > available_cash:
                max_affordable = available_cash / current_price if current_price > 0 else 0
                if max_affordable < 0.01:
                    return {
                        'passed': False,
                        'reason': f'Insufficient cash: need ${required_cash:,.0f}, have ${available_cash:,.0f}',
                        'capped_quantity': 0.0,
                        'current_position': current_position,
                        'constraints': ['cash_rejected'],
                    }
                constraints.append(f'cash_cap:{capped_qty:.1f}->{max_affordable:.1f}')
                capped_qty = max_affordable

        # --- SELL: Position constraint ---
        elif side == 'sell':
            if current_position <= 0 and not getattr(self.config, 'allow_shorts', False):
                return {
                    'passed': False,
                    'reason': f'No position in {symbol} and short selling not allowed',
                    'capped_quantity': 0.0,
                    'current_position': current_position,
                    'constraints': ['no_position_no_shorts'],
                }
            if current_position > 0:
                sellable = current_position + pending_buy_qty
                if capped_qty > sellable:
                    constraints.append(f'position_cap:{capped_qty:.1f}->{sellable:.1f}')
                    capped_qty = sellable

        # --- Concentration limit (max % of portfolio in one symbol) ---
        max_position_pct = 0.05
        try:
            pl = getattr(self.config, "position_limits", None)
            if pl is not None and hasattr(pl, "max_position_pct"):
                max_position_pct = float(getattr(pl, "max_position_pct", max_position_pct) or max_position_pct)
            elif hasattr(self.config, "max_position_pct"):
                max_position_pct = float(getattr(self.config, "max_position_pct", max_position_pct) or max_position_pct)
            elif hasattr(self.config, "max_position_size"):
                max_position_pct = float(getattr(self.config, "max_position_size", max_position_pct) or max_position_pct)
        except Exception:
            max_position_pct = 0.05

        max_position_value = portfolio_value * max_position_pct
        side_multiplier = 1.0 if side == 'buy' else -1.0
        post_trade_position = current_position + pending_qty + (side_multiplier * capped_qty)
        post_trade_value = abs(post_trade_position) * current_price

        if post_trade_value > max_position_value and side == 'buy':
            allowed_value = max_position_value - abs(current_position + pending_qty) * current_price
            concentration_max = allowed_value / current_price if current_price > 0 else 0
            concentration_max = max(0.0, concentration_max)
            if concentration_max < capped_qty:
                constraints.append(f'concentration_cap:{capped_qty:.1f}->{concentration_max:.1f}')
                capped_qty = concentration_max

        capped_qty = max(0.0, capped_qty)
        position_pct = post_trade_value / portfolio_value if portfolio_value > 0 else 0

        return {
            'passed': capped_qty > 0,
            'reason': '' if capped_qty > 0 else 'Position limits exceeded',
            'capped_quantity': capped_qty,
            'position_pct': position_pct,
            'current_position': current_position,
            'pending_qty': pending_qty,
            'max_position_pct': max_position_pct,
            'constraints': constraints,
        }

    def _gate4_multifactor_sizing(
        self,
        symbol: str,
        side: str,
        quantity: float,
        signal: Dict[str, Any],
        portfolio_value: float,
        current_price: float,
    ) -> Dict[str, Any]:
        """
        Gate 4: Multi-factor sizing (ported from traditional _calculate_authorized_quantity).

        Applies: regime scaling × volatility scaling × confidence scaling
        Plus:    exit bypass, ADS cooldown, fractional Kelly cap
        """
        sized_qty = quantity
        is_exit = signal.get('is_exit', False)
        confidence = float(signal.get('confidence', 0.5))
        signal_strength = float(signal.get('signal_strength', 0.5))
        strategy_id = signal.get('strategy_id', '')

        diag: Dict[str, Any] = {
            'qty_in': quantity,
            'is_exit': is_exit,
            'scaling_factors': {},
            'constraints_applied': [],
        }

        # ---- EXIT BYPASS: exits should not be scaled down ----
        if is_exit:
            diag['scaling_factors']['exit_bypass'] = True
            diag['qty_out'] = sized_qty
            return {
                'passed': True,
                'sized_quantity': sized_qty,
                'diagnostics': diag,
            }

        # ---- HARD CONFIDENCE FLOOR (reinstated for 6-gate parity) ----
        # After C1 removed the traditional authorize_trading_decision path,
        # risk.min_signal_confidence became dead config.  Enforce it here so
        # the YAML-declared threshold actually rejects low-confidence entries
        # rather than merely halving their size.
        min_conf = self.min_signal_confidence  # from config.risk_limits.confidence_threshold
        if confidence < min_conf:
            diag['scaling_factors']['confidence_floor_reject'] = True
            diag['min_signal_confidence'] = min_conf
            diag['signal_confidence'] = confidence
            diag['qty_out'] = 0.0
            return {
                'passed': False,
                'reason': (
                    f'Confidence {confidence:.2%} below minimum '
                    f'{min_conf:.2%} (hard floor)'
                ),
                'sized_quantity': 0.0,
                'diagnostics': diag,
            }

        # ---- Phase 0: Risk-Impact Reduction (ported from traditional path) ----
        # Trade-size-as-%-of-portfolio × volatility → reduction if above threshold
        # NOTE: TradingDecisionRequest.volatility_estimate defaults to 0.0;
        #       we match that default for sizing parity with the traditional path.
        risk_impact = 0.0
        if portfolio_value > 0 and current_price > 0:
            position_impact = (quantity * current_price) / portfolio_value
            volatility_est = float(signal.get('volatility_estimate', 0.0))
            vol_adj = max(1.0, volatility_est)
            risk_impact = position_impact * vol_adj

        auto_threshold = float(getattr(self.config, 'auto_approval_threshold', 0.01))
        risk_reduction_factor = 1.0
        if risk_impact > auto_threshold:
            risk_reduction = min(0.5, (risk_impact - auto_threshold) * 2)
            risk_reduction_factor = 1.0 - risk_reduction
            sized_qty *= risk_reduction_factor

        diag['risk_impact'] = {
            'risk_impact_score': risk_impact,
            'auto_threshold': auto_threshold,
            'risk_reduction_factor': risk_reduction_factor,
            'qty_after_risk_reduction': sized_qty,
        }

        # ---- Phase 1: Regime Scaling ----
        regime_engine = getattr(self, 'regime_engine', None)
        current_regime = 'unknown'
        regime_scaling = float(getattr(self, 'risk_multiplier', 1.0))

        if regime_engine is not None:
            try:
                ctx = regime_engine.get_current_regime_context()
                if ctx is not None:
                    vol_regime = str(getattr(ctx, 'volatility_regime', 'normal')).lower()
                    current_regime = vol_regime

                    # Discrete regime multipliers (same as old Gate 4)
                    vol_multipliers = {
                        'low': 1.10, 'low_volatility': 1.10,
                        'normal': 1.00,
                        'high': 0.60, 'high_volatility': 0.60,
                        'extreme': 0.30, 'extreme_volatility': 0.30,
                        'crisis': 0.0,
                    }
                    regime_scaling = vol_multipliers.get(vol_regime, 1.0)

                    if regime_scaling <= 0:
                        diag['scaling_factors'] = {'regime_scaling': 0.0, 'regime': current_regime}
                        return {
                            'passed': False,
                            'reason': f'Trading suspended in {vol_regime} regime',
                            'sized_quantity': 0.0,
                            'diagnostics': diag,
                        }
            except Exception:
                pass

        # ---- Phase 2: Volatility Scaling ----
        # Match traditional path source: TradingDecisionRequest.volatility_estimate defaults 0.0
        volatility_estimate = float(signal.get('volatility_estimate', 0.0))
        vol_scaling = 1.0
        if volatility_estimate > 0.40:
            vol_scaling = 0.5
        elif volatility_estimate > 0.25:
            vol_scaling = 0.8
        elif volatility_estimate < 0.10:
            vol_scaling = 1.1

        # ---- Phase 3: Confidence Scaling ----
        confidence_scaling = 1.0
        if confidence < 0.6:
            confidence_scaling = 0.5
        elif confidence > 0.9:
            confidence_scaling = 1.2

        # ---- Combine (multiplicative, capped at 1.25x for safety) ----
        combined_scaling = regime_scaling * vol_scaling * confidence_scaling
        combined_scaling = min(1.25, combined_scaling)

        qty_before = sized_qty
        sized_qty *= combined_scaling

        diag['scaling_factors'] = {
            'regime_scaling': regime_scaling,
            'regime': current_regime,
            'vol_scaling': vol_scaling,
            'volatility_estimate': volatility_estimate,
            'confidence_scaling': confidence_scaling,
            'confidence': confidence,
            'combined_scaling': combined_scaling,
            'qty_before_scaling': qty_before,
            'qty_after_scaling': sized_qty,
        }

        # ---- Phase 4: ADS Cooldown ----
        cooldown_scale = float(signal.get('ads_cooldown_scale', 1.0))
        if cooldown_scale < 1.0:
            sized_qty *= max(0.0, cooldown_scale)
            diag['constraints_applied'].append(f'ads_cooldown:{cooldown_scale:.2f}')

        # ---- Phase 5: Fractional Kelly Cap ----
        if (
            getattr(self.config, "enable_fractional_kelly_sizing", False)
            and side == "buy"
            and strategy_id
        ):
            try:
                from core_engine.risk.position_sizing.kelly_sizer import (
                    KellyParams, compute_fractional_kelly_fraction_of_capital,
                )
                price = current_price or 100.0

                sig_meta = signal.get('original_signal_metadata', {}) or {}
                ss = sig_meta.get('signal_strength', sig_meta.get('strength', None))
                if ss is None:
                    ss = sig_meta.get('target_weight', sig_meta.get('position_size', confidence))
                ss = max(0.0, min(1.0, float(ss) if ss is not None else float(confidence)))

                liquidity_factor = float(sig_meta.get('liquidity_factor', 1.0))
                liquidity_factor = max(0.0, min(1.0, liquidity_factor))

                current_dd = 0.0
                if self._portfolio_hwm > 0:
                    current_dd = max(0.0, (float(self._portfolio_hwm) - float(portfolio_value)) / float(self._portfolio_hwm))
                max_dd = float(getattr(self.config.risk_limits, "max_drawdown", 0.10))
                regime_factor = float(getattr(self, "risk_multiplier", 1.0))

                pnls = self._strategy_trade_outcomes.get(strategy_id, [])
                min_trades = int(getattr(self.config, "kelly_min_trades", 30))
                if len(pnls) < min_trades:
                    pnls = []  # Skip Kelly until sufficient sample

                if pnls:
                    kp = KellyParams(
                        kelly_frac=float(getattr(self.config, "kelly_frac", 0.33)),
                        kelly_min=float(getattr(self.config, "kelly_min", 0.02)),
                        kelly_max=float(getattr(self.config, "kelly_max", 0.20)),
                        prior_a=float(getattr(self.config, "kelly_prior_a", 5.0)),
                        prior_b=float(getattr(self.config, "kelly_prior_b", 5.0)),
                        min_trades=min_trades,
                        uncertainty_floor=float(getattr(self.config, "kelly_uncertainty_floor", 0.3)),
                        dd_gamma=float(getattr(self.config, "kelly_dd_gamma", 2.0)),
                    )
                    res = compute_fractional_kelly_fraction_of_capital(
                        signal_strength=ss,
                        pnls=pnls,
                        liquidity_factor=liquidity_factor,
                        current_dd=current_dd,
                        max_dd=max_dd,
                        regime_factor=regime_factor,
                        params=kp,
                    )
                    desired_qty = (float(portfolio_value) * float(res.target_fraction_of_capital)) / price
                    if desired_qty >= 0 and desired_qty < sized_qty:
                        diag['constraints_applied'].append(
                            f'kelly_cap:{sized_qty:.1f}->{desired_qty:.1f}'
                        )
                        sized_qty = desired_qty
                        diag['kelly_diagnostics'] = res.diagnostics
                        diag['kelly_target_fraction'] = float(res.target_fraction_of_capital)
            except Exception as e:
                diag['kelly_skip_reason'] = str(e)

        # ---- Final re-application of cash/position constraint (post-scaling) ----
        if side == 'buy':
            available_cash = signal.get('available_cash', portfolio_value * 0.95)
            final_required = sized_qty * current_price
            if final_required > available_cash and current_price > 0:
                new_max = available_cash / current_price
                diag['constraints_applied'].append(f'final_cash_cap:{sized_qty:.1f}->{new_max:.1f}')
                sized_qty = new_max
        elif side == 'sell':
            current_pos = self.current_positions.get(symbol, 0.0)
            if current_pos > 0 and sized_qty > current_pos:
                diag['constraints_applied'].append(f'final_position_cap:{sized_qty:.1f}->{current_pos:.1f}')
                sized_qty = current_pos

        sized_qty = max(0.0, float(sized_qty))
        diag['qty_out'] = sized_qty

        return {
            'passed': sized_qty > 0 or is_exit,
            'reason': '' if sized_qty > 0 else 'Quantity scaled to zero',
            'sized_quantity': sized_qty,
            'diagnostics': diag,
        }

    def _gate5_risk_budget(
        self,
        quantity: float,
        estimated_fill_price: float,
        stop_price: float,
        side: str,
    ) -> Dict[str, Any]:
        """Gate 5: P&L-aware risk budget check."""
        risk_budget = getattr(self, '_risk_budget', None)

        if risk_budget is None:
            return {
                'passed': True,
                'max_quantity': quantity,
                'max_loss': 0.0,
                'reason': 'No risk budget configured',
            }

        check = risk_budget.check_trade_risk(
            candidate_quantity=quantity,
            estimated_fill_price=estimated_fill_price,
            effective_stop_price=stop_price,
            side=side,
        )

        return {
            'passed': check['allowed'],
            'max_quantity': check['max_quantity'],
            'max_loss': check['max_loss'],
            'available_risk': check.get('available_risk', 0),
            'reason': check.get('resize_reason', ''),
        }

    def _gate6_cost_awareness(
        self,
        symbol: str,
        side: str,
        quantity: float,
        current_price: float,
        signal_strength: float,
        estimated_fill_price: float,
    ) -> Dict[str, Any]:
        """
        Gate 6: Cost-awareness gate aligned with HistoricalExecutionSimulator.

        Replicates the exact same Almgren-Chriss cost model that the execution
        simulator uses (spread + market impact + slippage + commission), then
        compares the estimated round-trip cost against expected edge.

        Rejects trades where round-trip cost > expected edge (negative expectancy).
        """
        import math

        if quantity <= 0:
            return {'passed': True, 'adjusted_quantity': quantity, 'reason': 'Zero quantity',
                    'cost_breakdown': {}}

        # ================================================================
        # Resolve execution simulator parameters (same defaults as
        # HistoricalExecutionSimulator.__init__)
        # ================================================================
        exec_cfg = getattr(self, '_exec_sim_config', None) or {}
        base_spread_bps     = float(exec_cfg.get('base_spread_bps', 5.0))
        base_slippage_bps   = float(exec_cfg.get('base_slippage_bps', 2.0))
        commission_per_share = float(exec_cfg.get('commission_per_share', 0.005))
        impact_linear_coeff = float(exec_cfg.get('impact_linear_coeff', 0.1))
        impact_sqrt_coeff   = float(exec_cfg.get('impact_sqrt_coeff', 0.5))

        # Regime multiplier (same lookup as simulator)
        regime_mult = 1.0
        regime_engine = getattr(self, 'regime_engine', None)
        vol_regime = 'normal_volatility'
        if regime_engine is not None:
            try:
                ctx = regime_engine.get_current_regime_context()
                if ctx is not None:
                    vol_regime = str(getattr(ctx, 'volatility_regime', 'normal_volatility'))
            except Exception:
                pass
        regime_multipliers = {
            'low_volatility': 0.8, 'low': 0.8,
            'normal_volatility': 1.0, 'normal': 1.0,
            'high_volatility': 1.3, 'high': 1.3,
            'extreme_volatility': 1.8, 'extreme': 1.8,
            'crisis': 2.5,
        }
        regime_mult = regime_multipliers.get(vol_regime, 1.0)

        # ================================================================
        # 1. SPREAD COST (half-spread, same as simulator)
        # ================================================================
        spread_cost_bps = (base_spread_bps * regime_mult) / 2.0
        spread_cost_bps = max(spread_cost_bps, 0.5)

        # ================================================================
        # 2. MARKET IMPACT — Almgren-Chriss (exact simulator formula)
        # ================================================================
        # Use bar volume from Gate 2 data or default
        bar_volume = float(getattr(self, '_last_bar_volume', 0))
        daily_volume_multiplier = 350  # Same as simulator
        daily_volume = bar_volume * daily_volume_multiplier if bar_volume > 0 else 1e6
        participation_rate = quantity / daily_volume if daily_volume > 0 else 0.01
        participation_rate = min(participation_rate, 1.0)

        linear_impact = impact_linear_coeff * participation_rate
        sqrt_impact = impact_sqrt_coeff * math.sqrt(participation_rate)
        base_impact_bps = (linear_impact + sqrt_impact) * 10000

        # Volatility adjustment (simulator uses bar volatility, default 0.02)
        bar_volatility = float(getattr(self, '_last_bar_volatility', 0.02))
        vol_adj = 1.0 + (bar_volatility - 0.02) * 10
        vol_adj = max(0.5, min(vol_adj, 2.0))
        impact_bps = base_impact_bps * vol_adj * regime_mult

        # ================================================================
        # 3. SLIPPAGE (deterministic estimate; simulator adds random noise
        #    but we use the mean for pre-trade estimation)
        # ================================================================
        slippage_bps = base_slippage_bps * (bar_volatility / 0.02) * regime_mult
        slippage_bps = max(slippage_bps, 0.0)

        # ================================================================
        # 4. COMMISSION
        # ================================================================
        commission_bps = 0.0
        if current_price > 0:
            commission_bps = (commission_per_share / current_price) * 10000

        # ================================================================
        # TOTAL ONE-WAY COST
        # ================================================================
        one_way_cost_bps = spread_cost_bps + impact_bps + slippage_bps + commission_bps
        round_trip_cost_bps = one_way_cost_bps * 2

        # Dollar cost
        one_way_cost_dollars = (one_way_cost_bps / 10000) * current_price * quantity
        round_trip_cost_dollars = one_way_cost_dollars * 2

        cost_breakdown = {
            'spread_cost_bps': spread_cost_bps,
            'impact_bps': impact_bps,
            'slippage_bps': slippage_bps,
            'commission_bps': commission_bps,
            'one_way_total_bps': one_way_cost_bps,
            'round_trip_total_bps': round_trip_cost_bps,
            'round_trip_dollars': round_trip_cost_dollars,
            'regime': vol_regime,
            'regime_mult': regime_mult,
            'participation_rate': participation_rate,
            'bar_volatility': bar_volatility,
        }

        # ================================================================
        # EXPECTED EDGE vs COST
        # ================================================================
        base_edge_bps = float(getattr(self.config, 'base_edge_bps', 20.0))
        expected_edge_bps = float(signal_strength) * base_edge_bps

        cost_edge_ratio = round_trip_cost_bps / expected_edge_bps if expected_edge_bps > 0 else float('inf')
        max_cost_edge_ratio = float(getattr(self.config, 'max_cost_edge_ratio', 0.80))

        adjusted_qty = quantity

        if cost_edge_ratio > max_cost_edge_ratio and expected_edge_bps > 0:
            if cost_edge_ratio > 1.0:
                # Negative expectancy: cost exceeds expected edge
                return {
                    'passed': False,
                    'reason': (
                        f'Negative expectancy: RT cost {round_trip_cost_bps:.1f}bps > '
                        f'edge {expected_edge_bps:.1f}bps (ratio={cost_edge_ratio:.2f})'
                    ),
                    'adjusted_quantity': 0.0,
                    'cost_bps': round_trip_cost_bps,
                    'expected_edge_bps': expected_edge_bps,
                    'cost_edge_ratio': cost_edge_ratio,
                    'cost_dollars': round_trip_cost_dollars,
                    'cost_breakdown': cost_breakdown,
                }
            else:
                # Marginal: cost is high but below 100% of edge
                # Let it through but flag
                cost_breakdown['marginal_warning'] = True

        return {
            'passed': True,
            'adjusted_quantity': adjusted_qty,
            'cost_bps': round_trip_cost_bps,
            'expected_edge_bps': expected_edge_bps,
            'cost_edge_ratio': cost_edge_ratio,
            'cost_dollars': round_trip_cost_dollars,
            'cost_breakdown': cost_breakdown,
        }

