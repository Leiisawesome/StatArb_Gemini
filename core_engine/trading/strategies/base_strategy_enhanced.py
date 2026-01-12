"""
Enhanced BaseStrategy with ISystemComponent Integration
=====================================================

Professional base strategy class that implements ISystemComponent interface
for seamless orchestrator integration and institutional-grade lifecycle management.

This enhanced base class provides:
- ISystemComponent interface compliance
- Professional error handling and logging
- Health monitoring and status reporting
- Performance tracking and metrics
- Risk management integration
- Configuration validation

Author: StatArb_Gemini Architecture Compliance
Version: 1.0.0 (Phase 2.3 Enhancement)
"""

import logging
import uuid
import warnings
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import numpy as np

# Type checking imports for PositionBook integration
if TYPE_CHECKING:
    from ..position_book import IPositionBook

# Import ISystemComponent for orchestrator integration
try:
    from ...system.interfaces import ISystemComponent
except ImportError:
    # Fallback definition
    from abc import ABC, abstractmethod
    class ISystemComponent(ABC):
        @abstractmethod
        async def initialize(self) -> bool:
            pass

        @abstractmethod
        async def start(self) -> bool:
            pass

        @abstractmethod
        async def stop(self) -> bool:
            pass

        @abstractmethod
        async def health_check(self) -> Dict[str, Any]:
            pass

        @abstractmethod
        def get_status(self) -> Dict[str, Any]:
            pass

# Strategy contracts (Rule 7)
from .contracts import StrategySignal, StrategyState
from core_engine.type_definitions.strategy import SignalType, StrategyType

logger = logging.getLogger(__name__)

class StrategyHealthStatus(Enum):
    """Strategy health status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    FAILED = "failed"

@dataclass
class StrategyPerformanceMetrics:
    """Enhanced strategy performance metrics"""

    # Basic metrics
    total_signals: int = 0
    successful_signals: int = 0
    failed_signals: int = 0

    # Performance metrics
    total_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0

    # Risk metrics
    var_95: float = 0.0
    volatility: float = 0.0
    beta: float = 0.0

    # Operational metrics
    avg_signal_generation_time: float = 0.0
    last_signal_timestamp: Optional[datetime] = None
    uptime_percentage: float = 0.0

    # Health metrics
    error_count: int = 0
    warning_count: int = 0
    last_error: Optional[str] = None
    last_health_check: Optional[datetime] = None

class EnhancedBaseStrategy(ISystemComponent, ABC):
    """
    Enhanced Base Strategy with ISystemComponent Integration

    Professional base class for all trading strategies that provides:
    - ISystemComponent interface compliance
    - Professional lifecycle management
    - Health monitoring and status reporting
    - Performance tracking and analytics
    - Risk management integration
    - Configuration validation
    """

    def __init__(self, config: Any):
        """Initialize enhanced base strategy"""

        # Basic strategy setup
        self.config = config
        self.strategy_id = config.strategy_id or str(uuid.uuid4())
        self.strategy_type = getattr(config, 'strategy_type', StrategyType.STATISTICAL_ARBITRAGE)
        self.state = StrategyState.INACTIVE

        # Instance logger for this strategy
        self.logger = logging.getLogger(f"{self.__class__.__name__}.{self.strategy_id}")

        # ISystemComponent state management
        self.is_initialized = False
        self.is_operational = False
        self.component_id: Optional[str] = None
        self.initialization_time = datetime.now()
        self.orchestrator: Optional[Any] = None  # HierarchicalSystemOrchestrator reference
        self.last_error: Optional[str] = None

        # ========================================
        # POSITION BOOK INTEGRATION (SSOT)
        # ========================================
        # PositionBook is the Single Source of Truth for all position tracking.
        # Strategies should use this for READ-ONLY position queries.
        self._position_book: Optional['IPositionBook'] = None

        # Strategy data (signals + cached data)
        self._signals: List[StrategySignal] = []
        self._market_data: Dict[str, pd.DataFrame] = {}
        self._indicators: Dict[str, pd.Series] = {}

        # Enhanced performance tracking
        self.performance_metrics = StrategyPerformanceMetrics()
        self.start_time: Optional[datetime] = None
        self.stop_time: Optional[datetime] = None

        # Health monitoring
        self.health_status = StrategyHealthStatus.HEALTHY
        self.health_checks_performed = 0
        self.last_health_check: Optional[datetime] = None

        # Risk management
        self.risk_manager: Optional[Any] = None
        self.max_position_size: float = getattr(config, 'max_position_size', 0.1)
        self.max_drawdown_limit: float = getattr(config, 'max_daily_loss', 0.2)

        # Performance monitoring
        self._signal_generation_times: List[float] = []
        self._error_log: List[Dict[str, Any]] = []
        self._warning_log: List[Dict[str, Any]] = []

        logger.info(f"🧠 Enhanced Strategy {self.strategy_id} ({self.strategy_type.value}) initialized")

    # ========================================
    # ORCHESTRATOR INTEGRATION
    # ========================================

    def register_with_orchestrator(self, orchestrator) -> str:
        """Register strategy with HierarchicalSystemOrchestrator"""
        from core_engine.system.hierarchical_orchestrator import ComponentLayer, AuthorityLevel

        self.orchestrator = orchestrator
        self.component_id = orchestrator.register_component(
            name=f"{self.__class__.__name__}_{self.strategy_id}",
            component=self,
            layer=ComponentLayer.EXECUTION,
            authority_level=AuthorityLevel.OPERATIONAL,
            initialization_order=50  # After all core components
        )

        logger.info(f"✅ Strategy {self.strategy_id} registered with orchestrator: {self.component_id}")
        return self.component_id

    async def request_operation_authorization(self, operation: str, details: Dict[str, Any]) -> bool:
        """Request authorization from orchestrator for privileged operations"""
        if not self.orchestrator or not self.component_id:
            logger.warning(f"No orchestrator available for authorization request in {self.strategy_id}")
            return False

        return await self.orchestrator.request_system_authorization(
            operation, self.component_id, details
        )

    # ========================================
    # STRATEGY CALLBACK METHODS
    # ========================================

    def set_signal_callback(self, callback: Callable):
        """Set signal callback for strategy notifications"""
        self.signal_callback = callback
        self.logger.info("✅ Signal callback registered with strategy")

    def on_signal_generated(self, signal_data: Dict[str, Any]):
        """Callback method for signal generation"""
        try:
            self.logger.info(f"📡 Strategy signal generated: {signal_data.get('symbol', 'unknown')}")

            # Notify callback if set
            if hasattr(self, 'signal_callback') and self.signal_callback:
                self.signal_callback(signal_data)

            return {'signal_callback_processed': True}

        except Exception as e:
            self.logger.error(f"Signal callback failed: {e}")
            return {'error': str(e)}

    def register_callback(self, callback_type: str, callback: Callable):
        """Register a callback for specific events"""
        try:
            if callback_type == 'signal':
                self.set_signal_callback(callback)
                return True
            else:
                self.logger.warning(f"Unknown callback type: {callback_type}")
                return False

        except Exception as e:
            self.logger.error(f"Callback registration failed: {e}")
            return False

    # ========================================
    # ISYSTEMCOMPONENT INTERFACE IMPLEMENTATION
    # ========================================

    async def initialize(self) -> bool:
        """Initialize the strategy"""

        try:
            logger.info(f"🔄 Initializing strategy {self.strategy_id}...")

            # Validate configuration
            if not self._validate_configuration():
                self.last_error = "Configuration validation failed"
                logger.error(f"❌ Configuration validation failed for {self.strategy_id}")
                return False

            # Initialize strategy-specific components
            if not await self._initialize_strategy_components():
                logger.error(f"❌ Strategy component initialization failed for {self.strategy_id}")
                return False

            # Initialize data structures
            self._initialize_data_structures()

            # Initialize performance tracking
            self._initialize_performance_tracking()

            # Set state
            self.is_initialized = True
            self.state = StrategyState.INACTIVE  # Ready to start

            logger.info(f"✅ Strategy {self.strategy_id} initialized successfully")
            return True

        except Exception as e:
            self.last_error = str(e)
            self._log_error("Initialization failed", e)
            logger.error(f"❌ Strategy {self.strategy_id} initialization failed: {e}")
            return False

    async def start(self) -> bool:
        """Start the strategy operations"""

        try:
            if not self.is_initialized:
                logger.error(f"❌ Cannot start - strategy {self.strategy_id} not initialized")
                return False

            logger.info(f"🚀 Starting strategy {self.strategy_id}...")

            # Start strategy-specific operations
            if not await self._start_strategy_operations():
                logger.error(f"❌ Failed to start strategy operations for {self.strategy_id}")
                return False

            # Set operational state
            self.is_operational = True
            self.state = StrategyState.ACTIVE
            self.start_time = datetime.now()

            logger.info(f"✅ Strategy {self.strategy_id} operational")
            return True

        except Exception as e:
            self.last_error = str(e)
            self._log_error("Start failed", e)
            logger.error(f"❌ Strategy {self.strategy_id} start failed: {e}")
            return False

    async def stop(self) -> bool:
        """Stop the strategy operations"""

        try:
            logger.info(f"🔄 Stopping strategy {self.strategy_id}...")

            # Stop strategy-specific operations
            await self._stop_strategy_operations()

            # Close any open positions (if configured to do so)
            if getattr(self.config, 'paper_trading_mode', True):
                await self._close_all_positions()

            # Set stopped state
            self.is_operational = False
            self.state = StrategyState.STOPPED
            self.stop_time = datetime.now()

            # Update performance metrics
            self._update_final_performance_metrics()

            logger.info(f"✅ Strategy {self.strategy_id} stopped")
            return True

        except Exception as e:
            self.last_error = str(e)
            self._log_error("Stop failed", e)
            logger.error(f"❌ Strategy {self.strategy_id} stop failed: {e}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""

        try:
            self.health_checks_performed += 1
            self.last_health_check = datetime.now()

            health_status = {
                'healthy': True,
                'initialized': self.is_initialized,
                'operational': self.is_operational,
                'component_type': 'Strategy',
                'strategy_id': self.strategy_id,
                'strategy_type': self.strategy_type.value,
                'state': self.state.value,
                'health_status': self.health_status.value,
                'last_error': self.last_error,
                'performance_metrics': {
                    'total_signals': self.performance_metrics.total_signals,
                    'success_rate': self._calculate_success_rate(),
                    'win_rate': self.performance_metrics.win_rate,
                    'total_return': self.performance_metrics.total_return,
                    'sharpe_ratio': self.performance_metrics.sharpe_ratio,
                    'max_drawdown': self.performance_metrics.max_drawdown,
                    'error_count': self.performance_metrics.error_count,
                    'warning_count': self.performance_metrics.warning_count
                },
                'operational_metrics': {
                    'uptime_percentage': self._calculate_uptime_percentage(),
                    'avg_signal_time': self.performance_metrics.avg_signal_generation_time,
                    'health_checks_performed': self.health_checks_performed,
                    'active_positions': self._get_active_position_count(),
                    'signals_generated': len(self._signals)
                }
            }

            # Check strategy-specific health
            strategy_health = await self._check_strategy_health()
            health_status.update(strategy_health)

            # Determine overall health
            if (self.performance_metrics.error_count > 10 or
                self.performance_metrics.max_drawdown > self.max_drawdown_limit or
                not strategy_health.get('strategy_healthy', True)):
                health_status['healthy'] = False
                self.health_status = StrategyHealthStatus.CRITICAL
            elif (self.performance_metrics.warning_count > 5 or
                  self.performance_metrics.max_drawdown > self.max_drawdown_limit * 0.7):
                health_status['healthy'] = True  # Still healthy but with warnings
                self.health_status = StrategyHealthStatus.WARNING
            else:
                self.health_status = StrategyHealthStatus.HEALTHY

            return health_status

        except Exception as e:
            self._log_error("Health check failed", e)
            return {
                'healthy': False,
                'error': str(e),
                'component_type': 'Strategy',
                'strategy_id': self.strategy_id
            }

    def get_status(self) -> Dict[str, Any]:
        """Get current status of the strategy"""

        return {
            'component_id': self.component_id,
            'component_type': 'Strategy',
            'strategy_id': self.strategy_id,
            'strategy_type': self.strategy_type.value,
            'initialized': self.is_initialized,
            'operational': self.is_operational,
            'state': self.state.value,
            'health_status': self.health_status.value,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'stop_time': self.stop_time.isoformat() if self.stop_time else None,
            'last_error': self.last_error,
            'performance_summary': {
                'total_signals': self.performance_metrics.total_signals,
                'success_rate': self._calculate_success_rate(),
                'total_return': self.performance_metrics.total_return,
                'max_drawdown': self.performance_metrics.max_drawdown,
                'active_positions': self._get_active_position_count(),
                'error_count': self.performance_metrics.error_count
            },
            'config_summary': {
                'max_position_size': self.max_position_size,
                'max_drawdown_limit': self.max_drawdown_limit,
                'strategy_specific': self._get_strategy_config_summary()
            }
        }

    # ========================================
    # ABSTRACT METHODS FOR STRATEGY IMPLEMENTATION
    # ========================================

    @abstractmethod
    async def generate_signals(self, market_data: Dict[str, pd.DataFrame]) -> List[StrategySignal]:
        """
        Generate trading signals based on market data.

        This is the PRIMARY responsibility of a strategy - analyzing market data
        and generating buy/sell/hold signals.

        Args:
            market_data: Dict of symbol -> enriched DataFrame with indicators

        Returns:
            List of StrategySignal objects
        """

    async def update_positions(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """
        DEPRECATED: Position tracking should be handled by PositionBook (SSOT).

        This method is deprecated. Position management is the responsibility
        of the Risk Manager and PositionBook. Strategies should focus on
        signal generation only.

        For backward compatibility, subclasses may still implement this method,
        but new strategies should not use internal position tracking.

        Migration path:
        - Use self._position_book.get_position(symbol) for read-only queries
        - Do not implement internal position tracking
        - Let Risk Manager handle position sizing, stops, and targets
        """
        # Default no-op for forward compatibility: strategies should not track positions.
        # Kept because some legacy execution paths still call update_positions().
        warnings.warn(
            "Strategy.update_positions() is deprecated. Position tracking should be handled by "
            "Risk Manager + PositionBook. This default implementation is a no-op.",
            DeprecationWarning,
            stacklevel=2,
        )
        return None

    def calculate_position_size(self, signal: StrategySignal, market_data: Dict[str, pd.DataFrame]) -> float:
        """
        DEPRECATED: Position sizing should be handled by Risk Manager.

        ⚠️  This method is DEPRECATED and should NOT be used.

        Position sizing is the responsibility of the Risk Manager,
        not the strategy. The Risk Manager uses PositionBook (SSOT)
        for position state and applies sizing rules.

        This default implementation returns 0.0 (no position).
        Subclasses may override for backward compatibility, but
        new strategies should NOT implement position sizing.

        Correct approach:
        - Set signal.confidence in generate_signals()
        - Let Risk Manager apply position sizing via TradingDecisionRequest
        - See core_engine/risk/ for proper sizing integration

        Returns:
            float: Always returns 0.0 - sizing delegated to Risk Manager
        """
        warnings.warn(
            f"Strategy.calculate_position_size() is deprecated. "
            f"Position sizing should be handled by Risk Manager. "
            f"This method returns 0.0 - use Risk Manager for actual sizing.",
            DeprecationWarning,
            stacklevel=2
        )
        return 0.0

    # ========================================
    # STRATEGY LIFECYCLE HOOKS (OVERRIDE AS NEEDED)
    # ========================================

    async def _initialize_strategy_components(self) -> bool:
        """Initialize strategy-specific components (override in subclass)"""
        return True

    async def _start_strategy_operations(self) -> bool:
        """Start strategy-specific operations (override in subclass)"""
        return True

    async def _stop_strategy_operations(self) -> None:
        """Stop strategy-specific operations (override in subclass)"""

    async def _check_strategy_health(self) -> Dict[str, Any]:
        """Check strategy-specific health (override in subclass)"""
        return {
            "strategy_healthy": True,
            "active_positions": self._get_active_position_count(),
        }

    def _get_strategy_config_summary(self) -> Dict[str, Any]:
        """Get strategy-specific configuration summary (override in subclass)"""
        # Generic best-effort summary. Strategy implementations may extend this,
        # but should not be required to implement it (Rule 7: keep implementations alpha-only).
        try:
            symbols = getattr(self.config, "symbols", None)
            if isinstance(symbols, (list, tuple)):
                symbols_count = len(symbols)
            else:
                symbols_count = None
        except Exception:
            symbols_count = None

        return {
            "symbols_count": symbols_count,
            "max_position_size": getattr(self.config, "max_position_size", None),
            "max_daily_loss": getattr(self.config, "max_daily_loss", None),
        }

    # ========================================
    # INTERNAL HELPER METHODS
    # ========================================

    def _validate_configuration(self) -> bool:
        """Validate strategy configuration"""

        try:
            # Basic validation
            if not self.strategy_id:
                logger.error("Strategy ID is required")
                return False

            if self.max_position_size <= 0 or self.max_position_size > 1:
                logger.error("Max position size must be between 0 and 1")
                return False

            if self.max_drawdown_limit <= 0 or self.max_drawdown_limit > 1:
                logger.error("Max drawdown limit must be between 0 and 1")
                return False

            # Strategy-specific validation (override in subclass)
            return self._validate_strategy_config()

        except Exception as e:
            logger.error(f"Configuration validation error: {e}")
            return False

    def _validate_strategy_config(self) -> bool:
        """Validate strategy-specific configuration (override in subclass)"""
        # Generic validation. Strategies may add stricter validation, but should not
        # need to (Rule 7: keep implementations alpha-only).
        try:
            if hasattr(self.config, "symbols"):
                symbols = getattr(self.config, "symbols", None)
                if not symbols:
                    logger.error("No symbols configured")
                    return False
        except Exception as e:
            logger.error(f"Strategy config validation error: {e}")
            return False

        return True

    def _initialize_data_structures(self) -> None:
        """Initialize data structures"""
        self._signals.clear()
        self._market_data.clear()
        self._indicators.clear()

    def _initialize_performance_tracking(self) -> None:
        """Initialize performance tracking"""
        self.performance_metrics = StrategyPerformanceMetrics()
        self._signal_generation_times.clear()
        self._error_log.clear()
        self._warning_log.clear()

    def _get_active_position_count(self) -> int:
        """Count active positions using PositionBook (SSOT)."""
        if not self._position_book:
            return 0
        try:
            positions = self._position_book.get_all_positions()
            # BookPosition uses quantity + side; treat any non-flat as active.
            return len([p for p in positions.values() if getattr(p, "is_flat", False) is False])
        except Exception:
            return 0

    async def _close_all_positions(self) -> None:
        """
        Best-effort close request for all open positions.

        NOTE: Position state is SSOT in PositionBook. This method emits CLOSE intent
        as StrategySignal(s) to the Risk Manager if one is attached.
        """
        if not self._position_book:
            return
        if not self.risk_manager:
            logger.warning(f"No risk_manager attached; cannot request closes for {self.strategy_id}")
            return

        try:
            positions = self._position_book.get_all_positions()
            for symbol, pos in positions.items():
                if getattr(pos, "is_flat", False):
                    continue

                # BookPosition.quantity is absolute; side tells direction.
                is_long = bool(getattr(pos, "is_long", False))
                signal_type = SignalType.SELL if is_long else SignalType.BUY
                qty = float(getattr(pos, "quantity", 0.0))
                if qty <= 0:
                    continue

                close_signal = StrategySignal(
                    strategy_id=self.strategy_id,
                    symbol=symbol,
                    signal_type=signal_type,
                    strength=1.0,
                    confidence=1.0,
                    quantity_type="ABSOLUTE",
                    target_quantity=qty,
                    timestamp=datetime.now(),
                    signal_reason="strategy_stop_close_all",
                    additional_data={"reason": "strategy_stop"},
                )
                await self.risk_manager.process_signal(close_signal)
        except Exception as e:
            self._log_error("Failed to request close-all via Risk Manager", e)

    def _update_final_performance_metrics(self) -> None:
        """Update final performance metrics on stop"""
        if self.start_time and self.stop_time:
            total_time = (self.stop_time - self.start_time).total_seconds()
            if total_time > 0:
                self.performance_metrics.uptime_percentage = 100.0  # Assume full uptime for now

    def _calculate_success_rate(self) -> float:
        """Calculate signal success rate"""
        if self.performance_metrics.total_signals == 0:
            return 0.0
        return self.performance_metrics.successful_signals / self.performance_metrics.total_signals

    def _calculate_uptime_percentage(self) -> float:
        """Calculate strategy uptime percentage"""
        if not self.start_time:
            return 0.0

        end_time = self.stop_time or datetime.now()
        total_time = (end_time - self.start_time).total_seconds()

        if total_time <= 0:
            return 0.0

        # For now, assume 100% uptime if operational
        return 100.0 if self.is_operational else self.performance_metrics.uptime_percentage

    def _log_error(self, message: str, exception: Exception) -> None:
        """Log error with tracking"""
        error_entry = {
            'timestamp': datetime.now(),
            'message': message,
            'exception': str(exception),
            'strategy_id': self.strategy_id
        }

        self._error_log.append(error_entry)
        self.performance_metrics.error_count += 1
        self.performance_metrics.last_error = f"{message}: {str(exception)}"

        # Keep error log size manageable
        if len(self._error_log) > 100:
            self._error_log = self._error_log[-50:]

    def _log_warning(self, message: str) -> None:
        """Log warning with tracking"""
        warning_entry = {
            'timestamp': datetime.now(),
            'message': message,
            'strategy_id': self.strategy_id
        }

        self._warning_log.append(warning_entry)
        self.performance_metrics.warning_count += 1

        # Keep warning log size manageable
        if len(self._warning_log) > 100:
            self._warning_log = self._warning_log[-50:]

    # ========================================
    # PERFORMANCE TRACKING METHODS
    # ========================================

    def track_signal_generation_time(self, generation_time: float) -> None:
        """Track signal generation time"""
        self._signal_generation_times.append(generation_time)

        # Calculate rolling average
        if self._signal_generation_times:
            self.performance_metrics.avg_signal_generation_time = np.mean(self._signal_generation_times[-100:])

    def update_performance_metrics(self, signal: StrategySignal, success: bool) -> None:
        """Update performance metrics after signal processing"""
        self.performance_metrics.total_signals += 1
        self.performance_metrics.last_signal_timestamp = datetime.now()

        if success:
            self.performance_metrics.successful_signals += 1
        else:
            self.performance_metrics.failed_signals += 1

    def set_risk_manager(self, risk_manager: Any) -> None:
        """Set risk manager reference"""
        self.risk_manager = risk_manager
        logger.info(f"🔗 Risk Manager linked to strategy {self.strategy_id}")

    # ========================================
    # POSITION BOOK INTEGRATION (SSOT)
    # ========================================

    def set_position_book(self, position_book: 'IPositionBook') -> None:
        """
        Set PositionBook for read-only position queries.

        The PositionBook is the Single Source of Truth (SSOT) for all position
        tracking. Strategies can use this for read-only queries to check
        existing positions when generating signals.

        Args:
            position_book: IPositionBook instance for position queries
        """
        self._position_book = position_book
        logger.info(f"📚 PositionBook linked to strategy {self.strategy_id}")

    def _has_position(self, symbol: str) -> bool:
        """
        Check if there's an existing position for a symbol (read-only query).

        Uses PositionBook (SSOT) for position state instead of internal tracking.

        Args:
            symbol: Symbol to check

        Returns:
            True if position exists with non-zero quantity, False otherwise
        """
        if not self._position_book:
            return False
        pos = self._position_book.get_position(symbol)
        if pos is None:
            return False
        return bool(getattr(pos, "is_flat", True) is False)

    def _get_position_quantity(self, symbol: str) -> float:
        """
        Get current position quantity for a symbol (read-only query).

        Uses PositionBook (SSOT) for position state instead of internal tracking.

        Args:
            symbol: Symbol to query

        Returns:
            Net quantity (positive for long, negative for short, 0 if no position)
        """
        if not self._position_book:
            return 0.0
        pos = self._position_book.get_position(symbol)
        if pos is None:
            return 0.0
        qty = float(getattr(pos, "quantity", 0.0))
        if getattr(pos, "is_short", False):
            return -qty
        return qty

    # ========================================
    # REGIME AWARENESS (IRegimeAware Interface)
    # ========================================

    def set_regime_engine(self, regime_engine: Any) -> None:
        """
        Inject regime engine dependency (IRegimeAware interface)

        Args:
            regime_engine: EnhancedRegimeEngine instance
        """
        self.regime_engine = regime_engine
        logger.info(f"🔄 Regime engine linked to strategy {self.strategy_id}")

    def get_current_regime_context(self) -> Optional[Any]:
        """
        Get current regime context (IRegimeAware interface)

        Returns:
            Current RegimeContext or None if not available
        """
        if hasattr(self, 'regime_engine') and self.regime_engine:
            try:
                # Try to get current regime (may be async, so we return None if not available)
                if hasattr(self.regime_engine, 'get_current_regime_context'):
                    return self.regime_engine.get_current_regime_context()
                elif hasattr(self.regime_engine, 'current_regime_context'):
                    return self.regime_engine.current_regime_context
            except Exception as e:
                logger.debug(f"Could not get regime context: {e}")
        return None

    async def on_regime_change(self, new_regime_context: Any) -> None:
        """
        Handle regime change event (IRegimeAware interface)

        Args:
            new_regime_context: New RegimeContext with updated information
        """
        try:
            # Store current regime context
            if not hasattr(self, '_current_regime_context'):
                self._current_regime_context = None
            self._current_regime_context = new_regime_context

            # Log regime change
            regime_name = getattr(new_regime_context, 'primary_regime', 'unknown')
            logger.info(f"🔄 Strategy {self.strategy_id} adapting to regime: {regime_name}")

            # Strategy-specific adaptation (override in subclass if needed)
            await self._adapt_to_regime(new_regime_context)

        except Exception as e:
            logger.error(f"❌ Error handling regime change: {e}")

    async def adapt_to_regime(self, regime_context: Any) -> Dict[str, Any]:
        """
        Adapt component behavior to current regime (IRegimeAware interface)

        Args:
            regime_context: RegimeContext to adapt to

        Returns:
            Dict with adaptation results
        """
        return await self._adapt_to_regime(regime_context)

    async def _adapt_to_regime(self, regime_context: Any) -> Dict[str, Any]:
        """
        Internal method for regime adaptation (override in subclass)

        Args:
            regime_context: RegimeContext to adapt to

        Returns:
            Dict with adaptation results
        """
        # Default implementation - override in strategy subclasses
        return {
            'adapted': True,
            'regime': getattr(regime_context, 'primary_regime', 'unknown'),
            'strategy_id': self.strategy_id
        }

    def validate_regime_dependency(self) -> bool:
        """
        Validate regime engine is properly configured (IRegimeAware interface)

        Returns:
            True if regime engine is available, False otherwise
        """
        return hasattr(self, 'regime_engine') and self.regime_engine is not None

    # ========================================
    # UTILITY METHODS
    # ========================================

    def get_recent_signals(self, count: int = 10) -> List[StrategySignal]:
        """Get recent signals"""
        return self._signals[-count:] if self._signals else []

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        # Get position count from PositionBook if available, otherwise fallback
        active_pos_count = self._get_active_position_count()
        total_pos_count = 0
        if self._position_book:
            try:
                total_pos_count = len(self._position_book.get_all_positions())
            except Exception:
                total_pos_count = 0

        return {
            'strategy_id': self.strategy_id,
            'strategy_type': self.strategy_type.value,
            'state': self.state.value,
            'health_status': self.health_status.value,
            'performance_metrics': {
                'total_signals': self.performance_metrics.total_signals,
                'success_rate': self._calculate_success_rate(),
                'win_rate': self.performance_metrics.win_rate,
                'total_return': self.performance_metrics.total_return,
                'sharpe_ratio': self.performance_metrics.sharpe_ratio,
                'max_drawdown': self.performance_metrics.max_drawdown,
                'volatility': self.performance_metrics.volatility,
                'var_95': self.performance_metrics.var_95
            },
            'operational_metrics': {
                'uptime_percentage': self._calculate_uptime_percentage(),
                'avg_signal_generation_time': self.performance_metrics.avg_signal_generation_time,
                'error_count': self.performance_metrics.error_count,
                'warning_count': self.performance_metrics.warning_count,
                'health_checks_performed': self.health_checks_performed
            },
            'positions': {
                'active_positions': active_pos_count,
                'total_positions': total_pos_count
            }
        }
