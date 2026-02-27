"""
Institutional Backtest Engine
==============================

Main orchestration engine for institutional-grade backtesting.
Coordinates all 9 core_engine "Lego Bricks" following the 13 Rules.

Architecture:
    - Phase 2: Data & Regime layer (Bricks #1-3)
    - Phase 3: Processing pipeline (Bricks #4-6)
    - Phase 4: Strategy & Risk (Bricks #7-8)
    - Phase 5: Execution (Brick #9)
    - Phase 6: Analytics (Bricks #10-12)

Follows:
    - Rule 2 (Regime-First Principle) (RegimeEngine initializes first)
    - Rule 7 Section B (Liquidity Management) (Liquidity filtering enabled)
    - Rule 5: Multi-Strategy Coordination (StrategyManager coordination)
    - Rule 4: Central Risk Management (CentralRiskManager authorization)
    - Rule 10: Production Standards (Comprehensive monitoring)
"""

from typing import Dict, Any, List, Optional
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import logging
import math
import pandas as pd
import sys
import asyncio

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Configuration (CENTRALIZED - using core_engine configs per Rule 1, Section 7)
from core_engine.config import BacktestConfig

# Core engine orchestration (BRICK #0)
from core_engine.system.hierarchical_orchestrator import (
    HierarchicalSystemOrchestrator,
    ComponentLayer,
    AuthorityLevel
)

# Position tracking (SSOT - Phase 2 PositionBook Integration)
from core_engine.trading.position_book import PositionBook, IPositionBook

# EOD guard logic (extracted from engine monolith)
from backtest.engine.eod_guard import EODGuard

# Mixin modules (extracted for maintainability)
from backtest.engine.initialization import InitializationMixin
from backtest.engine.session_management import SessionManagementMixin
from backtest.engine.reporting import ReportingMixin

logger = logging.getLogger(__name__)

def _signal_to_dict(s) -> dict:
    """Convert a Signal object to a canonical dict for DataFrame construction.

    Canonical field name is ``signal_type`` (not ``signal``).
    Downstream consumers already handle both, but we standardise here.
    """
    strength_raw = getattr(s, 'signal_strength', getattr(s, 'strength', 0.5))
    if hasattr(strength_raw, 'value'):
        strength_raw = strength_raw.value

    return {
        'strategy_id': getattr(s, 'strategy_id', 'backtest_strategy'),
        'symbol': s.symbol,
        'signal_type': s.signal_type.value if hasattr(s.signal_type, 'value') else s.signal_type,
        'confidence': s.confidence,
        'signal_strength': strength_raw,
        'strength': getattr(s, 'strength', 0.5),
        'expected_return': getattr(s, 'expected_return', None),
        'timestamp': getattr(s, 'timestamp', None),
        'target_weight': getattr(s, 'target_weight', None),
        'quantity_type': getattr(s, 'quantity_type', 'ABSOLUTE'),
        'target_quantity': getattr(s, 'target_quantity', 0),
        'additional_data': getattr(s, 'additional_data', {}),
    }

class InstitutionalBacktestEngine(InitializationMixin, SessionManagementMixin, ReportingMixin):
    """
    Institutional-Grade Backtest Engine

    Orchestrates all 9 core_engine Lego Bricks to perform comprehensive
    backtesting with regime awareness, liquidity filtering, multi-strategy
    coordination, and centralized risk management.

    Initialization Order (Rule 2 - Regime-First):
        5  - RegimeManager (FIRST!)
        10 - ClickHouseDataManager
        12 - LiquidityAssessmentEngine
        15 - EnhancedTechnicalIndicators
        16 - EnhancedFeatureEngineer
        17 - EnhancedSignalGenerator
        20 - StrategyManager
        25 - CentralRiskManager (GOVERNANCE)
        30 - EnhancedTradingEngine
        32 - EnhancedMetricsCalculator
        33 - PerformanceAnalyzer
        35 - EnhancedAnalyticsManager
        40 - UnifiedExecutionEngine

    Usage:
        config = BacktestConfig.from_dict({"backtest_name": "My Backtest", ...})
        engine = InstitutionalBacktestEngine(config)
        await engine.initialize()
        results = await engine.run_backtest()
        report = await engine.generate_report()
    """

    # ------------------------------------------------------------------
    # Named constants (formerly magic numbers scattered through the code)
    # ------------------------------------------------------------------
    #: Minimum position quantity to be considered "open" (shares)
    MIN_POSITION_QTY = 0.001
    #: Near-zero epsilon for floating-point comparisons
    EPSILON = 1e-9

    def __init__(self, config: BacktestConfig):
        """
        Initialize backtest engine with configuration

        Args:
            config: Complete backtest configuration mapping to all Lego Bricks
        """
        # Canonicalize backtest outputs under backtest/results/ regardless of CWD.
        # This prevents duplicated folders like backtest/backtest_results, reports/, etc.
        from pathlib import Path as _Path
        from backtest.utils.paths import backtest_results_dir

        if hasattr(config, "output_directory"):
            od = getattr(config, "output_directory", None)
            if not od:
                config.output_directory = str(backtest_results_dir())
            else:
                od_path = _Path(str(od))
                if not od_path.is_absolute():
                    # Keep everything under the canonical results root.
                    # If caller provided "reports" or "some_subdir", nest it under backtest/results/.
                    # If caller provided legacy defaults, collapse them to backtest/results/.
                    if str(od) in ("backtest_results", "backtest/results"):
                        config.output_directory = str(backtest_results_dir())
                    else:
                        config.output_directory = str(backtest_results_dir() / od_path)

        # AXIS8 FIX: Validate critical config at construction time.
        # BacktestConfig.validate() is only called via CLI, not direct instantiation.
        if config.initial_capital <= 0:
            raise ValueError(
                f"initial_capital must be > 0, got {config.initial_capital}. "
                f"A zero-capital backtest produces meaningless results."
            )

        self.config = config
        self.backtest_name = config.backtest_name
        self.backtest_mode = config.backtest_mode

        # Config-driven defaults (single source of truth: BacktestConfig)
        self.DEFAULT_SPREAD_BPS = getattr(config, 'base_spread_bps', 5.0)
        self.DEFAULT_VOLATILITY = 0.02  # No config knob yet; stable assumption
        self.DEFAULT_LIQUIDITY_SCORE = 100.0  # Max = fully liquid
        self.DEFAULT_COMMISSION_PER_SHARE = getattr(config, 'commission_per_trade', 0.005)

        # Orchestrator (BRICK #0 - System Control)
        self.orchestrator = HierarchicalSystemOrchestrator()

        # PositionBook: single source of truth for all position/cash state
        _commission = self.DEFAULT_COMMISSION_PER_SHARE
        self.position_book: IPositionBook = PositionBook(
            initial_cash=config.initial_capital,
            default_commission_per_share=_commission
        )
        logger.info(f"📘 PositionBook initialized with ${config.initial_capital:,.2f} initial capital (SSOT)")

        # Component registry (will be populated during initialization)
        self.components: Dict[str, Any] = {}
        self.component_ids: Dict[str, str] = {}

        # Phase 2 components (Data & Regime)
        self.regime_engine = None      # BRICK #1 (order=5)
        self.data_manager = None       # BRICK #2 (order=10)
        self.liquidity_engine = None   # BRICK #3 (order=12)

        # Phase 3 components (Processing)
        self.indicators_engine = None  # BRICK #4 (order=15)
        self.feature_engineer = None   # BRICK #5 (order=16)
        self.signal_generator = None   # BRICK #6 (order=17)

        # Phase 4 components (Strategy & Risk)
        self.strategy_manager = None   # BRICK #7 (order=20)
        self.risk_manager = None       # BRICK #8 (order=25) - GOVERNANCE
        # CentralRiskManager reads from position_book, does not maintain separate state

        # Phase 5 components (Execution)
        self.trading_engine = None     # BRICK #9a (order=30)
        self.execution_engine = None   # BRICK #9b (order=40)
        self.order_management_system = None  # P4: Optional OMS for path parity

        # Phase 6 components (Analytics)
        self.metrics_calculator = None # BRICK #10 (order=32)
        self.performance_analyzer = None # BRICK #11 (order=33)
        self.analytics_manager = None  # BRICK #12 (order=35)
        # Historical data for strategies
        self.historical_market_data: Dict[str, pd.DataFrame] = {}

        # Backtest state
        self.is_initialized = False
        self.is_running = False
        self.current_bar_index = 0
        self.historical_data: Optional[pd.DataFrame] = None

        # Parity default: disable simulated order rejections/retries unless explicitly enabled.
        # Papertest smoke tests run with deterministic fills (fill_probability=1.0, no partials).
        self.disable_rejections: bool = bool(getattr(config, "disable_rejections", True))

        # Results tracking
        self.backtest_results: Dict[str, Any] = {}
        self.execution_history: List[Dict[str, Any]] = []
        self.position_history: List[Dict[str, Any]] = []

        # Memory cap for long backtests
        # position_history is sampled down when it exceeds this limit.
        # execution_history is kept in full (trades are sparse) but warned.
        self._max_position_history = 200_000
        self._position_history_trim_warned = False

        # Pending signals queue: bar N signals execute at bar N+1 (no look-ahead)
        self.pending_signals: List[Dict[str, Any]] = []

        # Hot-loop caches (Phase 1 rollout, zero behavior change)
        self._market_calendar = None
        self._rth_asset_class = None
        self._rth_tz_name = "America/New_York"
        # Performance fast-path flags.
        # SAFE caches (pure memoization, no behavioral change) → default ON.
        # Behavioral paths (iteration/slicing logic) → default OFF until individually validated.
        self._use_fast_timestamp_cache = bool(getattr(config, "use_fast_timestamp_cache", True))
        self._use_fast_tz_alignment = bool(getattr(config, "use_fast_tz_alignment", True))
        self._use_fast_precalc_bar_lookup = bool(getattr(config, "use_fast_precalc_bar_lookup", True))
        self._use_fast_symbol_time_slice = bool(getattr(config, "use_fast_symbol_time_slice", True))
        self._use_fast_market_data_index_cache = bool(getattr(config, "use_fast_market_data_index_cache", True))
        self._use_fast_precalc_indexed_slice = bool(getattr(config, "use_fast_precalc_indexed_slice", True))
        self._use_fast_strategy_param_cache = bool(getattr(config, "use_fast_strategy_param_cache", True))
        self._use_fast_trace_context_cache = bool(getattr(config, "use_fast_trace_context_cache", True))
        # Behavioral paths — keep OFF to avoid trading logic divergence.
        self._use_fast_signal_iteration = bool(getattr(config, "use_fast_signal_iteration", False))
        self._use_fast_bar_iteration = bool(getattr(config, "use_fast_bar_iteration", False))
        self._use_fast_price_update = bool(getattr(config, "use_fast_price_update", False))
        self._use_fast_symbol_bar_lookup = bool(getattr(config, "use_fast_symbol_bar_lookup", False))
        self._use_fast_execution_symbol_bar_cache = bool(getattr(config, "use_fast_execution_symbol_bar_cache", False))
        self._price_lookup_cache: Dict[str, Any] = {}
        self._symbol_bar_cache: Dict[str, Any] = {}
        self._timestamp_series_cache: Dict[str, Any] = {}
        self._precalc_bar_lookup_cache: Dict[str, Any] = {}
        self._time_slice_cache: Dict[str, Any] = {}
        self._market_data_index_cache: Dict[str, Any] = {}
        self._precalc_indexed_slice_cache: Dict[str, Any] = {}
        self._strategy_param_cache: Optional[Dict[str, Any]] = None

        # EOD guard (extracted helper — owns all EOD time parsing & signal gating)
        self.eod_guard = EODGuard(config)

        # P1 F3: Survivorship bias — track symbols that had no price when we had positions
        self._symbol_dropout_tracker: set = set()

        # Intraday Session Isolation (day-boundary state reset)
        self._intraday_session_isolation: bool = bool(
            getattr(config, "intraday_session_isolation", False)
        )
        self._current_trading_date = None  # date object — tracks current trading day
        self._session_start_timestamp = None  # timestamp of first bar in current session

        logger.info(f"✅ InstitutionalBacktestEngine created: {self.backtest_name}")

    # ============================================================
    # Rule 1: ISystemComponent Interface Validation
    # ============================================================

    def _validate_component_interface(self, component: Any, component_name: str) -> Dict[str, Any]:
        """
        Validate that a component implements ISystemComponent interface (Rule 1)

        COMPLIANCE FIX: Implements Rule 1 interface validation requirements.

        Required Methods (ISystemComponent):
        - initialize() -> bool
        - start() -> bool
        - stop() -> bool
        - health_check() -> Dict[str, Any]
        - get_status() -> Dict[str, Any]

        Enhanced Methods (Optional):
        - configure_dependencies(orchestrator) -> bool
        - validate_configuration() -> Dict[str, Any]
        - prepare_for_shutdown() -> bool
        - get_performance_metrics() -> Dict[str, Any]

        Args:
            component: Component instance to validate
            component_name: Name of component for error reporting

        Returns:
            Dict with validation results
        """
        validation_result = {
            'component_name': component_name,
            'implements_interface': True,
            'missing_methods': [],
            'has_enhanced_methods': False,
            'enhanced_methods_present': [],
            'warnings': []
        }

        # Required methods (ISystemComponent core)
        required_methods = [
            'initialize',
            'start',
            'stop',
            'health_check',
            'get_status'
        ]

        # Enhanced methods (ISystemComponent v2.0)
        enhanced_methods = [
            'configure_dependencies',
            'validate_configuration',
            'prepare_for_shutdown',
            'get_performance_metrics'
        ]

        # Check required methods
        for method_name in required_methods:
            if not hasattr(component, method_name):
                validation_result['missing_methods'].append(method_name)
                validation_result['implements_interface'] = False

        # Check enhanced methods
        for method_name in enhanced_methods:
            if hasattr(component, method_name):
                validation_result['enhanced_methods_present'].append(method_name)

        if len(validation_result['enhanced_methods_present']) > 0:
            validation_result['has_enhanced_methods'] = True

        # Add warnings for missing enhanced methods
        if not validation_result['has_enhanced_methods']:
            validation_result['warnings'].append(
                f"{component_name} missing enhanced methods (Rule 1 v2.0). "
                f"Consider implementing: {', '.join(enhanced_methods)}"
            )

        return validation_result

    async def validate_all_components(self) -> Dict[str, Any]:
        """
        Validate that ALL registered components implement ISystemComponent (Rule 1)

        COMPLIANCE FIX: System-wide component interface validation.

        This ensures architectural compliance by validating that every component
        in the system properly implements the ISystemComponent interface, which
        is required for:
        - Proper lifecycle management
        - Health monitoring
        - Status reporting
        - Graceful shutdown

        Returns:
            Dict with validation results for all components
        """
        logger.info("\n" + "=" * 80)
        logger.info("🔍 RULE 1 COMPLIANCE: ISystemComponent Interface Validation")
        logger.info("=" * 80)

        validation_results = {
            'total_components': 0,
            'compliant_components': 0,
            'non_compliant_components': 0,
            'enhanced_components': 0,
            'component_validations': {},
            'overall_compliant': True
        }

        # Validate all registered components
        for component_name, component in self.components.items():
            if component is None:
                continue

            validation_results['total_components'] += 1

            # Validate component
            result = self._validate_component_interface(component, component_name)
            validation_results['component_validations'][component_name] = result

            # Update counters
            if result['implements_interface']:
                validation_results['compliant_components'] += 1
                if result['has_enhanced_methods']:
                    validation_results['enhanced_components'] += 1
            else:
                validation_results['non_compliant_components'] += 1
                validation_results['overall_compliant'] = False

                # Log non-compliant component
                logger.error(
                    f"❌ {component_name} does NOT implement ISystemComponent!\n"
                    f"   Missing methods: {', '.join(result['missing_methods'])}"
                )

        # Log summary
        logger.info(f"\n📊 Validation Summary:")
        logger.info(f"   Total Components: {validation_results['total_components']}")
        logger.info(f"   ✅ Compliant: {validation_results['compliant_components']}")
        logger.info(f"   ❌ Non-Compliant: {validation_results['non_compliant_components']}")
        logger.info(f"   ⭐ Enhanced (v2.0): {validation_results['enhanced_components']}")

        if validation_results['overall_compliant']:
            logger.info(f"\n✅ Rule 1 Compliance: PASSED - All components implement ISystemComponent")
        else:
            logger.warning(f"\n⚠️  Rule 1 Compliance: FAILED - Some components missing interface methods")

        logger.info("=" * 80 + "\n")

        return validation_results

    # ============================================================
    # Rule 2: IRegimeAware Interface Implementation
    # ============================================================

    def set_regime_engine(self, regime_engine: Any) -> None:
        """
        Set regime engine for regime-aware backtesting (Rule 2 - IRegimeAware)

        COMPLIANCE FIX: Implements IRegimeAware interface per Rule 2.

        The backtest engine itself becomes regime-aware, allowing it to:
        - Adapt backtest parameters to market regime
        - Log regime transitions during backtest
        - Generate regime-specific performance metrics

        Args:
            regime_engine: RegimeManager instance
        """
        self.regime_engine = regime_engine
        logger.info("✅ Regime engine injected into BacktestEngine (Rule 2 IRegimeAware)")

    async def on_regime_change(self, new_regime_context: Dict[str, Any]) -> None:
        """
        Handle regime change events during backtest (Rule 2 - IRegimeAware)

        COMPLIANCE FIX: Implements regime change callback per Rule 2.

        This is called whenever the regime engine detects a regime transition.
        The backtest engine can:
        - Log regime transitions with timestamps
        - Adjust backtest parameters (e.g., risk limits, position sizes)
        - Generate regime transition markers for analytics

        Args:
            new_regime_context: New regime context with regime type, confidence, etc.
        """
        if not new_regime_context:
            return

        primary_regime = new_regime_context.get('primary_regime', 'unknown')
        confidence = new_regime_context.get('confidence', 0.0)
        timestamp = new_regime_context.get('timestamp', 'unknown')

        # Log regime transition
        logger.info(
            f"🔄 Regime Transition @ {timestamp}: {primary_regime} "
            f"(confidence: {confidence:.2%})"
        )

        # Adapt backtest behavior to regime (optional - currently informational only)
        await self.adapt_to_regime(new_regime_context)

    def get_current_regime_context(self) -> Optional[Dict[str, Any]]:
        """
        Get current regime context (Rule 2 - IRegimeAware)

        COMPLIANCE FIX: Implements regime context retrieval per Rule 2.

        Returns:
            Current regime context from regime engine, or None if not available
        """
        if self.regime_engine and hasattr(self.regime_engine, 'get_current_regime_context'):
            try:
                context = self.regime_engine.get_current_regime_context()
                if context:
                    if hasattr(context, '__dict__'):
                        return context.__dict__
                    return context
            except Exception as e:
                logger.warning(f"Failed to get current regime: {e}")
                return None
        return None

    async def adapt_to_regime(self, regime_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adapt backtest parameters to current regime (Rule 2 - IRegimeAware)

        COMPLIANCE FIX: Implements regime adaptation per Rule 2.

        The backtest engine can adapt its behavior based on regime:
        - Adjust execution cost multipliers
        - Modify risk limits
        - Update position sizing constraints
        - Change transaction cost assumptions

        Args:
            regime_context: Regime context with regime type, volatility, etc.

        Returns:
            Dict with adaptation results
        """
        primary_regime = regime_context.get('primary_regime', 'normal_volatility')
        volatility_regime = regime_context.get('volatility_regime', 'normal_volatility')

        adaptation_result = {
            'regime': primary_regime,
            'volatility_regime': volatility_regime,
            'adaptations_applied': [],
            'timestamp': regime_context.get('timestamp', 'unknown')
        }

        # Regime-specific adaptations (informational for backtesting)
        regime_multipliers = {
            'low_volatility': {
                'execution_cost_multiplier': 0.8,
                'risk_limit_multiplier': 1.2,
                'position_size_multiplier': 1.1
            },
            'normal_volatility': {
                'execution_cost_multiplier': 1.0,
                'risk_limit_multiplier': 1.0,
                'position_size_multiplier': 1.0
            },
            'high_volatility': {
                'execution_cost_multiplier': 1.3,
                'risk_limit_multiplier': 0.7,
                'position_size_multiplier': 0.8
            },
            'extreme_volatility': {
                'execution_cost_multiplier': 1.8,
                'risk_limit_multiplier': 0.4,
                'position_size_multiplier': 0.5
            }
        }

        multipliers = regime_multipliers.get(
            volatility_regime,
            regime_multipliers['normal_volatility']
        )

        adaptation_result['multipliers'] = multipliers
        adaptation_result['adaptations_applied'].append(
            f"Execution costs: {multipliers['execution_cost_multiplier']:.1f}x"
        )
        adaptation_result['adaptations_applied'].append(
            f"Risk limits: {multipliers['risk_limit_multiplier']:.1f}x"
        )
        adaptation_result['adaptations_applied'].append(
            f"Position sizing: {multipliers['position_size_multiplier']:.1f}x"
        )

        # Note: For backtesting, these are informational
        # Components like ExecutionEngine and RiskManager have their own regime adaptations

        return adaptation_result

    def validate_regime_dependency(self) -> bool:
        """
        Validate that regime engine is properly configured (Rule 2 - IRegimeAware)

        COMPLIANCE FIX: Implements regime dependency validation per Rule 2.

        Returns:
            True if regime engine is available and functional
        """
        if not self.regime_engine:
            logger.warning("⚠️  Regime engine not configured (Rule 2 IRegimeAware)")
            return False

        if not hasattr(self.regime_engine, 'get_current_regime_context'):
            logger.warning("⚠️  Regime engine missing required methods (get_current_regime_context)")
            return False

        logger.info("✅ Regime dependency validated (Rule 2 IRegimeAware)")
        return True

    # ============================================================
    # PHASE 2.1: Orchestrator Setup & Component Registration
    # ============================================================

    async def initialize(self) -> bool:
        """
        Initialize backtest engine and all components

        This method will be enhanced phase-by-phase:
        - Phase 2: Data & Regime components (Bricks #1-3)
        - Phase 3: Processing pipeline (Bricks #4-6)
        - Phase 4: Strategy & Risk (Bricks #7-8)
        - Phase 5: Execution (Brick #9)
        - Phase 6: Analytics (Bricks #10-12)

        Returns:
            True if initialization successful
        """
        try:
            logger.info("=" * 80)
            logger.info(f"🚀 INITIALIZING: {self.backtest_name}")
            logger.info("=" * 80)

            # Phase 2: Initialize Data & Regime layer
            await self._initialize_phase2_data_regime()

            # Phase 3: Initialize Processing pipeline
            await self._initialize_phase3_processing_pipeline()

            # Phase 4: Initialize Strategy & Risk
            await self._initialize_phase4_strategy_risk()

            # Phase 5: Initialize Execution
            await self._initialize_phase5_execution()

            # Phase 6: Initialize Analytics
            await self._initialize_phase6_analytics()

            # Orchestrator drives component lifecycle; engine retains phase sequencing
            if len(self.components) > 0:
                logger.info(f"   Components registered: {len(self.components)}")

                # Initialize components in registration (priority) order via orchestrator
                _critical_components = {'data_manager', 'risk_manager', 'strategy_manager',
                                        'clickhouse_data_manager', 'central_risk_manager'}
                for component_name, component in sorted(
                    self.components.items(),
                    key=lambda kv: getattr(kv[1], 'initialization_order', 100) if hasattr(kv[1], 'initialization_order') else 100,
                ):
                    _is_critical = any(c in component_name.lower() for c in _critical_components)
                    try:
                        # Skip initialize() for already-initialized components,
                        # but ALWAYS call start() — the phase methods call
                        # initialize() but not start(), so is_operational stays
                        # False without this.
                        if hasattr(component, 'is_initialized') and component.is_initialized:
                            logger.info(f"   {component_name} already initialized, calling start()...")
                        elif hasattr(component, 'initialize'):
                            await component.initialize()
                        if hasattr(component, 'start'):
                            await component.start()
                        logger.info(f"   ✅ {component_name} started")
                    except Exception as e:
                        if _is_critical:
                            logger.error(f"   ❌ CRITICAL component {component_name} failed: {e}")
                            raise RuntimeError(f"Critical component {component_name} failed to initialize: {e}") from e
                        else:
                            logger.warning(f"   ⚠️ Optional component {component_name} failed: {e}")

                # C3: Start the orchestrator itself so health_check / status work
                try:
                    self.orchestrator.system_status = self.orchestrator.system_status.__class__('ready')
                    await self.orchestrator.start()
                    logger.info("✅ HierarchicalSystemOrchestrator → OPERATIONAL")
                except Exception as orch_err:
                    logger.warning(f"⚠️ Orchestrator start (non-fatal): {orch_err}")

                logger.info(f"\n✅ {len(self.components)} components initialized")
            else:
                logger.info("\n⚠️  No components registered - skipping initialization")

            # Validate component compliance (Rule 1 + Rule 2)
            validation_results = await self.validate_all_components()
            regime_dependency_valid = self.validate_regime_dependency()

            if not validation_results['overall_compliant']:
                logger.warning("⚠️ Rule 1 compliance validation failed — proceeding with warnings")
            if not regime_dependency_valid:
                logger.warning("⚠️ Rule 2 regime dependency validation failed — proceeding with warnings")

            # Mark initialized only AFTER validation passes
            self.is_initialized = True

            logger.info("\n" + "=" * 80)
            logger.info("✅ INITIALIZATION COMPLETE")
            logger.info("=" * 80)
            logger.info(f"   Backtest: {self.backtest_name}")
            logger.info(f"   Mode: {self.backtest_mode}")  # backtest_mode is already a string
            logger.info(f"   Period: {self.config.start_date} → {self.config.end_date}")
            logger.info(f"   Symbols: {', '.join(self.config.symbols)}")
            logger.info(f"   Strategies: {len(self.config.strategies)}")
            logger.info(f"   Components Registered: {len(self.components)}")
            logger.info(f"   Rule 1 Compliance (ISystemComponent): {'✅ PASSED' if validation_results['overall_compliant'] else '⚠️ FAILED'}")
            logger.info(f"   Rule 2 Compliance (IRegimeAware): {'✅ PASSED' if regime_dependency_valid else '⚠️ FAILED'}")
            logger.info("=" * 80 + "\n")

            return True

        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}", exc_info=True)
            # Clean up any already-started components to prevent resource leaks
            try:
                await self.shutdown()
            except Exception as shutdown_err:
                logger.warning(f"⚠️ Cleanup after failed init also failed: {shutdown_err}")
            return False

    # ------------------------------------------------------------------
    # Initialization methods: see initialization.py (InitializationMixin)
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Reporting methods: see reporting.py (ReportingMixin)
    # ------------------------------------------------------------------

    # ============================================================
    # MAIN BACKTEST LOOP (PHASE 7)
    # ============================================================

    def _discard_final_pending_signals(self, bars_processed: int) -> None:
        """Discard pending signals from the last bar (no next bar to execute on)."""
        if self.pending_signals and bars_processed > 0:
            logger.info(
                f"⏳ Discarding {len(self.pending_signals)} pending signal(s) "
                f"from final bar (no next bar to execute on)"
            )
            for sig in self.pending_signals:
                logger.debug(
                    f"   Discarded: {sig.get('symbol')} {sig.get('side')} "
                    f"qty={sig.get('quantity', 0):.2f}"
                )
            self.pending_signals = []

    async def _force_close_open_positions(self, bar, timestamp) -> None:
        """Force-close all open positions at backtest end (last bar's close price)."""
        if not (self.risk_manager and self.risk_manager.current_positions):
            return
        open_positions = dict(self.risk_manager.current_positions)
        if not open_positions:
            return
        logger.info(
            f"🔒 Force-closing {len(open_positions)} open position(s) at backtest end"
        )
        last_close = bar.get('close', 0) if bar is not None else 0
        for sym, qty in open_positions.items():
            if abs(qty) < self.EPSILON:
                continue
            close_side = 'sell' if qty > 0 else 'buy'
            close_qty = abs(qty)
            # Get symbol-specific price
            sym_close = self._get_symbol_close_at_timestamp(
                sym, timestamp, fallback=last_close,
            )

            try:

                # Route force-close through execution simulator for cost modeling

                _fill_price = sym_close

                _total_cost_bps = 0.0

                if hasattr(self, 'execution_simulator'):

                    _fc_market_data = {

                        'close': sym_close,

                        'volume': bar.get('volume', 1000000) if bar is not None else 1000000,

                        'volatility': bar.get('volatility', 0.02) if bar is not None else 0.02,

                        'timestamp': timestamp,

                    }

                    _fc_fill = self.execution_simulator.simulate_fill(

                        symbol=sym,

                        side=close_side,

                        quantity=close_qty,

                        decision_price=sym_close,

                        market_data=_fc_market_data,

                        authorization_id=f'END_CLOSE_{sym}',

                        strategy_id='BACKTEST_END_CLOSE',

                    )

                    _fill_price = _fc_fill.fill_price

                    _total_cost_bps = _fc_fill.costs.total_cost_bps

                # CP4 + CP5 trace for backtest-end close
                self._emit_cp4_cp5_trace(
                    method="backtest_end_close",
                    trace_id=f"end_close_{sym}_{timestamp}",
                    symbol=sym, bar_timestamp=timestamp, side=close_side,
                    quantity=close_qty, decision_price=sym_close,
                    fill_price=_fill_price, market_price=sym_close,
                    strategy_id="BACKTEST_END_CLOSE",
                    authorization_id=f'END_CLOSE_{sym}',
                    cp4_output={"success": True, "backtest_end_close": True},
                    cp4_metadata={"regime": "backtest_end"},
                    cp5_output={"total_cost_bps": float(_total_cost_bps)},
                    cp5_metadata={"backtest_end_close": True},
                )

                # Capture realized_pnl from position update

                position_update = await self.risk_manager.update_position(

                    symbol=sym, side=close_side, quantity=close_qty,

                    price=_fill_price, timestamp=timestamp,

                    strategy_id='BACKTEST_END_CLOSE',

                    backtest_fill=True,

                )

                _rpnl = 0.0

                if isinstance(position_update, dict):

                    _rpnl = position_update.get('realized_pnl', 0.0)

                self.execution_history.append({

                    'timestamp': timestamp, 'symbol': sym,

                    'side': close_side, 'quantity': close_qty,

                    'fill_price': _fill_price, 'market_price': sym_close,

                    'decision_price': sym_close, 'confidence': 1.0,

                    'strategy_id': 'BACKTEST_END_CLOSE',

                    'authorization_id': f'END_CLOSE_{sym}',

                    'total_cost_bps': _total_cost_bps,

                    'realized_pnl': _rpnl,

                })

            except Exception as e:

                logger.warning(f"⚠️ Failed to close {sym} at backtest end: {e}")

    async def run_backtest(self) -> Dict[str, Any]:
        """
        Execute complete backtest with bar-by-bar processing

        This is the main orchestration method that runs the complete backtest:

        Flow:
        1. Validate initialization
        2. Load historical data
        3. Process each bar:
           a. Update regime engine
           b. Generate indicators
           c. Engineer features
           d. Generate signals
           e. Execute strategies ✅ Phase 7.2
           f. Authorize trades
           g. Simulate execution
           h. Update positions
        4. Generate performance report
        5. Return results

        Returns:
            Dict with backtest results including:
            - summary: BacktestSummary object
            - total_bars: Number of bars processed
            - total_trades: Number of trades executed
            - final_capital: Ending portfolio value
            - report: Formatted performance report
        """
        logger.info("\n" + "=" * 80)
        logger.info("🚀 STARTING BACKTEST EXECUTION")
        logger.info("=" * 80)
        logger.info(f"   Backtest: {self.backtest_name}")
        logger.info(f"   Period: {self.config.start_date} → {self.config.end_date}")
        logger.info(f"   Symbols: {', '.join(self.config.symbols)}")
        logger.info("=" * 80 + "\n")

        if not self.is_initialized:
            raise RuntimeError("Engine not initialized. Call initialize() first.")

        # Pre-share execution cost parameters with CRM for Gate 6 cost alignment.
        # Must happen before any signal processing (i.e., before simulate_execution
        # creates the HistoricalExecutionSimulator).
        if hasattr(self, 'risk_manager') and self.risk_manager is not None:
            self.risk_manager._exec_sim_config = {
                'base_spread_bps': getattr(self.config, 'base_spread_bps', 5.0),
                'base_slippage_bps': getattr(self.config, 'base_slippage_bps', 2.0),
                'commission_per_share': getattr(self.config, 'commission_per_trade', 0.005),
                'impact_linear_coeff': getattr(self.config, 'linear_coefficient', 0.1),
                'impact_sqrt_coeff': getattr(self.config, 'sqrt_coefficient', 0.5),
            }

        try:
            start_time = datetime.now()
            self.is_running = True

            # Ensure we have historical data
            if self.historical_data is None or self.historical_data.empty:
                logger.error("❌ No historical data loaded")
                return {
                    'success': False,
                    'error': 'No historical data available'
                }

            total_bars = len(self.historical_data)
            logger.info(f"📊 Processing {total_bars} bars...")
            logger.info(f"   Data points: {len(self.historical_data)}")
            logger.info(f"   Start: {self.historical_data.index[0]}")
            logger.info(f"   End: {self.historical_data.index[-1]}")
            logger.info("")

            # Pre-calculate indicators/features via PipelineOrchestrator
            # (per-session when intraday_session_isolation is enabled)
            logger.info("🔧 Pre-calculating indicators and features via PipelineOrchestrator...")
            pre_calc_start = datetime.now()

            try:
                self.pre_calculated_indicators_per_symbol: Dict[str, pd.DataFrame] = {}
                self.pre_calculated_features_per_symbol: Dict[str, pd.DataFrame] = {}

                # Build raw_data dict from already-loaded market_data
                raw_data_per_symbol: Dict[str, pd.DataFrame] = {}
                for sym in self.config.symbols:
                    if sym not in self.market_data or self.market_data[sym].empty:
                        logger.warning(f"   ⚠️ No data for {sym}, skipping")
                        continue
                    sym_data = self.market_data[sym].copy()
                    if 'timestamp' not in sym_data.columns:
                        sym_data = sym_data.reset_index()
                    raw_data_per_symbol[sym] = sym_data

                if self._intraday_session_isolation:
                    # Per-session pre-calculation: each day uses warmup + day
                    # data so expanding normalization is scoped identically
                    # to what an individual-day run would see.
                    await self._pre_calculate_per_session(raw_data_per_symbol)
                else:
                    # Standard: compute features across entire dataset at once
                    enriched_results = await self.pipeline_orchestrator.process_preloaded_data(
                        raw_data_per_symbol=raw_data_per_symbol,
                        timeframe=self.config.interval,
                    )
                    for sym, enriched in enriched_results.items():
                        self.pre_calculated_indicators_per_symbol[sym] = enriched.indicators
                        self.pre_calculated_features_per_symbol[sym] = enriched.features
                        logger.info(
                            f"   ✅ {sym}: {len(enriched.features)} bars "
                            f"({enriched.indicator_columns} indicators, "
                            f"{enriched.feature_columns} features)"
                        )

                # Backward compatibility: set primary symbol aliases
                primary_symbol = self.config.symbols[0] if self.config.symbols else None
                self.pre_calculated_indicators = (
                    self.pre_calculated_indicators_per_symbol.get(primary_symbol)
                    if primary_symbol else None
                )
                self.pre_calculated_features = (
                    self.pre_calculated_features_per_symbol.get(primary_symbol)
                    if primary_symbol else None
                )

                # Pre-calculated signals (optional — strategies generate on-the-fly)
                self.pre_calculated_signals = None

                pre_calc_duration = (datetime.now() - pre_calc_start).total_seconds()
                logger.info(f"   ⏱️  Pre-calculation completed in {pre_calc_duration:.2f} seconds")
                logger.info(f"   🔗 Code path: PipelineOrchestrator (same as papertest/live)")
                logger.info("")

            except Exception as e:
                logger.error(f"❌ Pre-calculation via PipelineOrchestrator failed: {e}")
                logger.warning("⚠️  Falling back to on-the-fly calculation")
                self.pre_calculated_indicators = None
                self.pre_calculated_features = None
                self.pre_calculated_signals = None

            # Bar-by-bar processing
            bars_processed = 0
            bars_with_signals = 0
            bars_with_trades = 0
            pre_calc_index = 0  # Track index in pre_calculated_features (which excludes warmup)

            # Circuit breaker — halt after N consecutive bar errors
            # Prevents runaway error loops from burning CPU while producing garbage.
            _consecutive_errors = 0
            _MAX_CONSECUTIVE_ERRORS = 50

            # Record initial position state
            if self.risk_manager:
                # Use CentralRiskManager for position state (Rule 4)
                # P&L values come from pnl_tracker (if available)
                pnl_source = getattr(self, 'pnl_tracker', None) or self.risk_manager
                initial_snapshot = {
                    'timestamp': self.historical_data.index[0] if not self.historical_data.empty else datetime.now(),
                    'equity': self.risk_manager.portfolio_value if hasattr(self.risk_manager, 'portfolio_value') else self.config.initial_capital,
                    'cash': self.risk_manager.available_cash,
                    'total_pnl': getattr(pnl_source, 'total_pnl', 0.0),
                    'realized_pnl': getattr(pnl_source, 'realized_pnl', 0.0),
                    'unrealized_pnl': getattr(pnl_source, 'unrealized_pnl', 0.0),
                    'position_count': len(self.risk_manager.current_positions),
                    'max_drawdown': getattr(self.risk_manager, 'max_drawdown', 0.0),
                    'max_drawdown_pct': getattr(self.risk_manager, 'max_drawdown_pct', 0.0)
                }
                self.position_history.append(initial_snapshot)

            # Progress tracking
            progress_interval = max(1, total_bars // 20)  # Report every 5%

            if self._use_fast_bar_iteration:
                historical_rows = self._prepare_historical_rows_fast(self.historical_data)
            else:
                historical_rows = self.historical_data.iterrows()

            for idx, (index_val, bar) in enumerate(historical_rows):
                # Extract timestamp from bar if available, otherwise use index
                timestamp = bar.get('timestamp', index_val)

                # Skip warmup period (Rule 3: Data Pipeline)
                # We only process bars within the requested simulation period
                if self._is_before_simulation_start(timestamp):
                    continue  # Skip warmup bars

                # Defensive RTH gate (should be no-op if data was filtered to RTH at load time).
                # Use MarketCalendar (asset-class aware) instead of hardcoding 09:30–16:00.
                if not self._is_within_rth(timestamp, idx):
                    continue

                # ============================================================
                # INTRADAY SESSION ISOLATION — Day-Boundary State Reset
                #
                # Both first-day and day-boundary cases use the SAME warmup
                # source (historical_data) with the SAME cap to guarantee
                # that multi-day and individual-day runs see identical state.
                # ============================================================
                if self._intraday_session_isolation:
                    bar_date = pd.Timestamp(timestamp).date()
                    if self._current_trading_date is None or bar_date != self._current_trading_date:
                        is_first = self._current_trading_date is None
                        label = (
                            f"First trading day {bar_date}"
                            if is_first
                            else f"Day boundary {self._current_trading_date} → {bar_date}"
                        )
                        logger.info(f"\n🔄 SESSION ISOLATION: {label}")

                        # Always collect warmup from historical_data (deterministic)
                        warmup_bars_snapshot = self._collect_warmup_bars_before_date(bar_date)
                        self._reset_session_state()
                        if warmup_bars_snapshot:
                            self._warmup_replay(warmup_bars_snapshot)

                        # Record the day's start timestamp so that
                        # features_historical in _process_single_bar is
                        # clipped to the current session only.
                        self._session_start_timestamp = pd.Timestamp(timestamp)

                    self._current_trading_date = bar_date

                self.current_bar_index = idx

                # Update all symbol prices for mark-to-market valuation
                self._update_current_prices_from_market_data(timestamp)

                # Progress reporting
                if idx % progress_interval == 0 or idx == total_bars - 1:
                    progress_pct = (idx + 1) / total_bars * 100
                    logger.info(f"   Progress: {progress_pct:5.1f}% ({idx+1}/{total_bars}) - "
                              f"Trades: {len(self.execution_history)}")

                try:
                    # Process current bar
                    bar_result = await self._process_single_bar(bar, timestamp, idx, pre_calc_index)

                    bars_processed += 1
                    if bar_result.get('signals_generated', 0) > 0:
                        bars_with_signals += 1
                    if bar_result.get('trades_executed', 0) > 0:
                        bars_with_trades += 1

                    # Check for EOD liquidation (intraday trading rule)
                    eod_liquidated = await self._check_eod_liquidation(timestamp, bar)
                    if eod_liquidated > 0:
                        bars_with_trades += 1  # Count EOD as a trading bar

                except Exception as e:
                    _consecutive_errors += 1
                    logger.error(f"❌ Error processing bar {idx} at {timestamp}: {e}")
                    # Halt backtest if consecutive errors exceed threshold
                    if _consecutive_errors >= _MAX_CONSECUTIVE_ERRORS:
                        logger.error(
                            f"🛑 CIRCUIT BREAKER: {_consecutive_errors} consecutive bar errors "
                            f"— aborting backtest to prevent garbage results"
                        )
                        raise RuntimeError(
                            f"Circuit breaker tripped: {_consecutive_errors} consecutive bar processing errors"
                        )
                    continue
                else:
                    _consecutive_errors = 0  # Reset on success
                finally:
                    # Always advance pre_calc_index, even on error
                    # pre_calc_index tracks position in the timeline, not processed bars.
                    # Skipping it on error causes all subsequent iloc slices to drift.
                    pre_calc_index += 1

            # Discard trailing pending signals (no N+1 bar to execute on)
            self._discard_final_pending_signals(bars_processed)

            # Force-close all open positions at last bar's close
            if bars_processed > 0:
                await self._force_close_open_positions(bar, timestamp)

            # Backtest complete
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            logger.info("\n" + "=" * 80)
            logger.info("✅ BACKTEST EXECUTION COMPLETE")
            logger.info("=" * 80)
            logger.info(f"   Bars Processed: {bars_processed}/{total_bars}")
            logger.info(f"   Bars with Signals: {bars_with_signals}")
            logger.info(f"   Bars with Trades: {bars_with_trades}")
            logger.info(f"   Total Trades: {len(self.execution_history)}")
            logger.info(f"   Duration: {duration:.2f} seconds")
            # Guard against zero duration
            logger.info(f"   Speed: {bars_processed/duration:.1f} bars/sec" if duration > 0 else f"   Speed: N/A (duration < 1ms)")
            logger.info("=" * 80 + "\n")

            # Generate performance report
            logger.info("📊 Generating performance report...")
            report = self.generate_performance_report(format='console', export=True)
            summary = self.get_performance_summary()

            # Compile results
            results = {
                'success': True,
                'summary': summary,
                'execution_history': self.execution_history,
                'position_history': self.position_history,
                'total_bars': bars_processed,
                'bars_processed': bars_processed,
                'bars_with_signals': bars_with_signals,
                'bars_with_trades': bars_with_trades,
                'total_trades': len(self.execution_history),
                # Position tracker reference removed (PositionBook is SSOT)
                'final_capital': self.risk_manager.portfolio_value if self.risk_manager else self.config.initial_capital,
                'duration_seconds': duration,
                'bars_per_second': bars_processed / duration if duration > 0 else 0,
                'report': report,
                'start_time': start_time,
                'end_time': end_time,
                # P1 F3: Survivorship bias — symbols that had no price when we had positions
                'symbols_dropped_out': list(self._symbol_dropout_tracker),
            }

            return results

        except Exception as e:
            logger.error(f"❌ Backtest execution failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'total_bars': bars_processed if 'bars_processed' in locals() else 0,
                'total_trades': len(self.execution_history)
            }
        finally:
            # AXIS7 FIX: Ensure resources are released on both success and failure.
            # This prevents ClickHouse connection leaks on mid-backtest exceptions.
            self.is_running = False
            try:
                if hasattr(self, 'data_manager') and self.data_manager is not None:
                    if hasattr(self.data_manager, 'stop'):
                        current_task = asyncio.current_task()
                        if current_task and current_task.cancelling():
                            logger.debug("Skipping blocking DataManager stop during task cancellation")
                        else:
                            await asyncio.wait_for(asyncio.shield(self.data_manager.stop()), timeout=5.0)
                            logger.debug("DataManager stopped in finally block")
            except asyncio.TimeoutError:
                logger.debug("DataManager cleanup timed out in finally block")
            except asyncio.CancelledError:
                logger.debug("DataManager cleanup cancelled in finally block")
            except Exception as cleanup_err:
                logger.debug(f"DataManager cleanup in finally: {cleanup_err}")

    # ------------------------------------------------------------------
    # Session management methods: see session_management.py (SessionManagementMixin)
    # ------------------------------------------------------------------

    async def _check_eod_liquidation(self, timestamp: datetime, bar: pd.Series) -> int:
        """
        Check if we should perform EOD liquidation and close all positions.

        Intraday Trading Rule: Close all positions before market close to avoid
        overnight gap risk. This is critical for intraday mean reversion strategies.

        Args:
            timestamp: Current bar timestamp
            bar: Current bar data (for close price)

        Returns:
            Number of positions liquidated
        """
        # Get current positions from CentralRiskManager (Rule 4)
        if not self.risk_manager:
            return 0

        positions = self.risk_manager.current_positions.copy()
        if not positions:
            return 0

        ts = pd.Timestamp(timestamp)
        if ts.tzinfo is not None:
            ts = ts.tz_convert('America/New_York')

        symbols_to_liquidate = []

        # ADS v3.1: Contextual EOD check per position via EODGuard
        for symbol, qty in positions.items():
            if abs(qty) < self.MIN_POSITION_QTY:
                continue

            strat_id = None
            if self.position_book:
                pos = self.position_book.get_position(symbol)
                strat_id = getattr(pos, 'strategy_id', None)

            if self.eod_guard.should_liquidate_position(
                timestamp, symbol, strat_id, self._get_strategy_param
            ):
                symbols_to_liquidate.append((symbol, qty, strat_id))

        if not symbols_to_liquidate:
            return 0

        # Idempotency: only liquidate once per day
        if self.eod_guard.already_liquidated(ts.date()):
            return 0

        self.eod_guard.mark_liquidated(ts.date())

        logger.info(f"\n⏰ EOD LIQUIDATION @ {ts.strftime('%H:%M')} - Closing {len(symbols_to_liquidate)} positions contextually")

        liquidated = 0
        # Default close price from current bar (fallback for single-symbol)
        default_close_price = bar.get('close', bar.get('Close', 0))

        for symbol, position_qty, strat_id in symbols_to_liquidate:
            # Get symbol-specific close price (CRITICAL for multi-symbol portfolios)
            close_price = self._get_symbol_close_at_timestamp(
                symbol, timestamp, fallback=default_close_price,
            )

            # EOD liquidation closes positions regardless of P&L (intraday risk rule).
            # This keeps backtests consistent when strategies are entry-intent only (Rule 7).

            # Create a liquidation sell order
            side = 'sell' if position_qty > 0 else 'buy'  # Sell longs, buy to cover shorts
            qty = abs(position_qty)

            # Route EOD liquidation through execution simulator for realistic costs
            eod_market_data = {
                'close': close_price,
                'volume': bar.get('volume', 1000000),
                'volatility': bar.get('volatility', 0.02),
                'timestamp': timestamp,
            }

            # Get regime context for cost scaling
            eod_regime_context = None
            if self.regime_engine and hasattr(self.regime_engine, 'get_current_regime'):
                try:
                    eod_regime_context = self.regime_engine.get_current_regime()
                except Exception as e:
                    logger.debug(f"EOD regime context retrieval failed: {e}")

            # Use simulator if available, otherwise fall back to manual construction
            if hasattr(self, 'execution_simulator'):
                simulated_fill = self.execution_simulator.simulate_fill(
                    symbol=symbol,
                    side=side,
                    quantity=qty,
                    decision_price=close_price,
                    market_data=eod_market_data,
                    authorization_id=f'EOD_LIQUIDATION_{timestamp}_{symbol}',
                    strategy_id=strat_id or 'EOD_LIQUIDATION',
                    regime_context=eod_regime_context,
                )
                execution = self._build_execution_dict(
                    timestamp=timestamp, symbol=symbol, side=side, quantity=qty,
                    decision_price=close_price,
                    market_price=simulated_fill.market_price,
                    fill_price=simulated_fill.fill_price,
                    strategy_id=strat_id or 'EOD_LIQUIDATION',
                    authorization_id=f'EOD_LIQUIDATION_{timestamp}_{symbol}',
                    fill_id=simulated_fill.fill_id,
                    total_cost_bps=simulated_fill.costs.total_cost_bps,
                    spread_cost_bps=simulated_fill.costs.spread_cost_bps,
                    market_impact_bps=simulated_fill.costs.market_impact_bps,
                    slippage_bps=simulated_fill.costs.slippage_bps,
                    commission_bps=simulated_fill.costs.commission_bps,
                    total_cost_dollars=simulated_fill.costs.total_cost_dollars,
                    permanent_impact_bps=simulated_fill.costs.permanent_impact_bps,
                    temporary_impact_bps=simulated_fill.costs.temporary_impact_bps,
                    implementation_shortfall_bps=simulated_fill.implementation_shortfall_bps,
                    arrival_cost_bps=simulated_fill.arrival_cost_bps,
                    regime=simulated_fill.costs.regime or 'eod_close',
                    liquidity_score=simulated_fill.costs.liquidity_score,
                )
                fill_price_for_pnl = simulated_fill.fill_price
            else:
                # Fallback: minimal cost estimate (only if simulator not initialized)
                estimated_cost_bps = self.DEFAULT_SPREAD_BPS
                cost_mult = estimated_cost_bps / 10000
                fill_price_fallback = close_price * (1.0 - cost_mult) if side == 'sell' else close_price * (1.0 + cost_mult)
                execution = self._build_execution_dict(
                    timestamp=timestamp, symbol=symbol, side=side, quantity=qty,
                    decision_price=close_price, market_price=close_price,
                    fill_price=fill_price_fallback,
                    strategy_id=strat_id or 'EOD_LIQUIDATION',
                    authorization_id=f'EOD_LIQUIDATION_{timestamp}_{symbol}',
                    fill_id=f'eod_fill_{timestamp}_{symbol}',
                    total_cost_bps=estimated_cost_bps,
                    spread_cost_bps=2.5, market_impact_bps=2.5,
                    total_cost_dollars=qty * close_price * estimated_cost_bps / 10000,
                    temporary_impact_bps=2.5,
                )
                fill_price_for_pnl = fill_price_fallback

            # CP4 + CP5 trace for EOD liquidation
            self._emit_cp4_cp5_trace(
                method="_check_eod_liquidation",
                trace_id=execution.get('fill_id') or execution.get('authorization_id') or f"eod_{symbol}_{timestamp}",
                symbol=symbol, bar_timestamp=timestamp, side=side,
                quantity=qty, decision_price=close_price,
                fill_price=execution['fill_price'],
                market_price=execution.get('market_price', close_price),
                strategy_id=execution.get('strategy_id', 'EOD_LIQUIDATION'),
                authorization_id=execution.get('authorization_id', ''),
                cp4_output={"success": True, "eod_liquidation": True},
                cp4_metadata={"regime": execution.get('regime', 'eod_close')},
                cp5_output={
                    "total_cost_bps": float(execution.get('total_cost_bps', 0)),
                    "spread_cost_bps": float(execution.get('spread_cost_bps', 0)),
                    "market_impact_bps": float(execution.get('market_impact_bps', 0)),
                    "slippage_bps": float(execution.get('slippage_bps', 0)),
                    "commission_bps": float(execution.get('commission_bps', 0)),
                    "total_cost_dollars": float(execution.get('total_cost_dollars', 0)),
                    "implementation_shortfall_bps": float(execution.get('implementation_shortfall_bps', 0)),
                },
                cp5_metadata={"eod_liquidation": True, "arrival_cost_bps": float(execution.get('arrival_cost_bps', 0))},
            )

            # Update position via CentralRiskManager (Rule 4)
            # H4: Pass backtest_fill=True to skip CRM's internal cost deduction
            # (costs already embedded in fill_price by execution simulator)
            position_update = await self.risk_manager.update_position(
                symbol=symbol,
                side=side,
                quantity=qty,
                price=fill_price_for_pnl,
                timestamp=timestamp,
                strategy_id=strat_id,
                backtest_fill=True,
            )

            # Update execution with actual P&L from risk manager
            if position_update:
                execution['realized_pnl'] = position_update.get('realized_pnl', 0.0)

            self.execution_history.append(execution)
            liquidated += 1

            logger.info(f"   💰 EOD: {side.upper()} {qty:.2f} {symbol} @ ${close_price:.2f} [Strategy: {strat_id}]")

        logger.info(f"   ✅ Liquidated {liquidated} positions\n")
        return liquidated

    def _get_strategy_param(self, param_name: str, default: any = None, strategy_id: str = None) -> any:
        """
        Get a parameter from the strategy config.
        If strategy_id is provided, looks for that specific strategy.
        Otherwise, defaults to the first strategy in the list.

        Args:
            param_name: Parameter name to retrieve
            default: Default value if not found
            strategy_id: Optional strategy name to look up

        Returns:
            Parameter value or default
        """
        if self._use_fast_strategy_param_cache:
            if self._strategy_param_cache is None:
                first_params = {}
                params_by_name = {}
                if hasattr(self.config, 'strategies') and self.config.strategies:
                    first_strategy = self.config.strategies[0]
                    if isinstance(first_strategy, dict):
                        first_params = first_strategy.get('parameters', {}) or {}

                    for strat in self.config.strategies:
                        if isinstance(strat, dict):
                            name = strat.get('name')
                            if name:
                                params_by_name[name] = strat.get('parameters', {}) or {}

                self._strategy_param_cache = {
                    'first_params': first_params,
                    'params_by_name': params_by_name,
                }

            params_by_name = self._strategy_param_cache.get('params_by_name', {})
            if strategy_id:
                params = params_by_name.get(strategy_id)
                if params is None:
                    return default
                if param_name in params:
                    return params.get(param_name)
                return default

            first_params = self._strategy_param_cache.get('first_params', {})
            return first_params.get(param_name, default)

        if hasattr(self.config, 'strategies') and self.config.strategies:
            # Try to find specific strategy if provided
            if strategy_id:
                for strat in self.config.strategies:
                    if isinstance(strat, dict) and strat.get('name') == strategy_id:
                        params = strat.get('parameters', {})
                        if param_name in params:
                            return params.get(param_name)
                        # Specific strategy found, but param missing - do NOT fall back to strategies[0]
                        # unless strategy_id was strategies[0]'s name.
                        return default
                # strategy_id provided but not found in config - return default
                return default
            
            # Fallback to the first strategy ONLY if no strategy_id was provided
            strategy = self.config.strategies[0]
            if isinstance(strategy, dict):
                params = strategy.get('parameters', {})
                return params.get(param_name, default)
        return default

    def _resolve_symbol_bar(self, symbol: str, bar_timestamp, current_bar):
        """
        Resolve the correct OHLCV bar for a specific symbol at a given timestamp.

        In multi-symbol backtests, `current_bar` may belong to a different symbol.
        This method looks up the correct bar from market_data or pre_calculated_features.

        Args:
            symbol: The symbol to resolve bar data for
            bar_timestamp: Timestamp of the bar to look up
            current_bar: The current iteration bar (fallback)

        Returns:
            Bar data (Series or dict-like) for the requested symbol
        """
        sym_bar = current_bar
        try:
            cur_sym = None
            try:
                cur_sym = current_bar.get('symbol', None)
            except Exception:
                cur_sym = None

            if cur_sym is not None and str(cur_sym) == str(symbol):
                return sym_bar

            fast_bar = self._resolve_symbol_bar_fast(symbol, bar_timestamp)
            if fast_bar is not None:
                return fast_bar

            # Prefer the loaded per-symbol OHLCV from self.market_data (authoritative).
            try:
                md = getattr(self, "market_data", None)
                sym_df = md.get(symbol) if isinstance(md, dict) else None
                if sym_df is not None and hasattr(sym_df, "empty") and not sym_df.empty:
                    ts_idx = pd.Timestamp(bar_timestamp)
                    # Index lookup
                    if getattr(sym_df.index, "dtype", None) is not None:
                        try:
                            if ts_idx in sym_df.index:
                                sym_bar = sym_df.loc[ts_idx]
                                if hasattr(sym_bar, "iloc"):
                                    sym_bar = sym_bar.iloc[-1] if len(sym_bar) > 0 else sym_bar
                        except Exception:
                            pass
                    # Column filter fallback
                    if (sym_bar is current_bar) and ('timestamp' in getattr(sym_df, "columns", [])):
                        ts_ser = pd.to_datetime(sym_df['timestamp'])
                        m = ts_ser == ts_idx
                        if m.any():
                            sym_bar = sym_df.loc[m].iloc[-1]
            except Exception:
                pass

            # Fallback: pre_calculated_features if available
            if sym_bar is current_bar:
                dfp = getattr(self, "pre_calculated_features", None)
                if dfp is not None and hasattr(dfp, "empty") and not dfp.empty:
                    ts_idx = pd.Timestamp(bar_timestamp)
                    if 'timestamp' in dfp.columns:
                        ts_ser = pd.to_datetime(dfp['timestamp'])
                        m = (dfp.get('symbol') == symbol) & (ts_ser == ts_idx)
                        if m.any():
                            sym_bar = dfp.loc[m].iloc[-1]
                    else:
                        try:
                            df_sym = dfp[dfp.get('symbol') == symbol]
                            df_sym = df_sym.loc[:ts_idx]
                            if len(df_sym) > 0:
                                sym_bar = df_sym.iloc[-1]
                        except Exception:
                            pass
        except Exception:
            sym_bar = current_bar

        return sym_bar

    def _resolve_symbol_bar_fast(self, symbol: str, bar_timestamp) -> Optional[Dict[str, Any]]:
        """Fast symbol bar resolution via cached datetime-index searchsorted."""
        if not self._use_fast_symbol_bar_lookup:
            return None

        md = getattr(self, "market_data", None)
        sym_df = md.get(symbol) if isinstance(md, dict) else None
        if sym_df is None or getattr(sym_df, 'empty', True):
            return None

        cache_key = f"md::{symbol}"
        cache = self._symbol_bar_cache.get(cache_key)
        if cache is None:
            cache = self._build_symbol_bar_cache(sym_df)
            self._symbol_bar_cache[cache_key] = cache if cache is not None else {'disabled': True}
            cache = self._symbol_bar_cache[cache_key]

        if cache.get('disabled', False):
            return None

        ts_idx = self._align_timestamp_to_index_tz(
            pd.Timestamp(bar_timestamp),
            cache['idx_tz'],
            cache=None,
        )
        idx_obj = cache['idx_obj']

        pos = int(idx_obj.searchsorted(ts_idx, side='right')) - 1
        if pos < 0:
            return None

        row = cache['records'][pos]
        # Preserve original behavior: only return exact timestamp matches.
        if pd.Timestamp(row['timestamp']) != ts_idx:
            return None

        return row

    def _build_symbol_bar_cache(self, sym_df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Build per-symbol bar lookup cache for exact timestamp resolution."""
        if sym_df is None or sym_df.empty:
            return None

        if isinstance(sym_df.index, pd.DatetimeIndex):
            idx_obj = sym_df.index
            df_tmp = sym_df.copy()
            df_tmp = df_tmp.reset_index(drop=False)
            ts_col = 'timestamp' if 'timestamp' in df_tmp.columns else df_tmp.columns[0]
            if ts_col != 'timestamp':
                df_tmp = df_tmp.rename(columns={ts_col: 'timestamp'})
        elif 'timestamp' in sym_df.columns:
            idx_obj = pd.DatetimeIndex(sym_df['timestamp'])
            df_tmp = sym_df.copy()
            df_tmp['timestamp'] = pd.to_datetime(df_tmp['timestamp'])
        else:
            return None

        if not getattr(idx_obj, 'is_monotonic_increasing', False):
            return None

        records = df_tmp.to_dict('records')
        return {
            'idx_obj': idx_obj,
            'idx_tz': getattr(idx_obj, 'tz', None),
            'records': records,
        }

    def _build_market_data_dict(self, sym_bar, bar_timestamp, current_price: float) -> Dict[str, Any]:
        """
        Build the market_data dict for the execution simulator from a resolved symbol bar.

        Args:
            sym_bar: Resolved bar data (from _resolve_symbol_bar)
            bar_timestamp: Timestamp for the bar
            current_price: Current execution price

        Returns:
            Dict with timestamp, open, high, low, close, volume, volatility
        """
        return {
            'timestamp': bar_timestamp,
            'open': sym_bar.get('open', current_price),
            'high': sym_bar.get('high', current_price),
            'low': sym_bar.get('low', current_price),
            'close': current_price,
            'volume': sym_bar.get('volume', 0),
            'volatility': sym_bar.get('volatility', self.DEFAULT_VOLATILITY),
        }

    async def _generate_signals_for_bar(
        self,
        bar_dict: dict,
        timestamp,
        bar_index: int,
        pre_calc_index: int = 0,
    ):
        """Generate signals for a single bar using pre-calculated or on-the-fly data.

        Returns
        -------
        (bar_df, signals_df) : tuple
            bar_df is the single-row DataFrame for the current bar (used by
            downstream trade authorization).  signals_df is the DataFrame of
            generated signals, or None if no signals.
        """
        # Step 2: Use pre-calculated data for StrategyManager inputs (PT-style = indicators)
        # Check if we have pre-calculated indicators/features available
        use_pre_calculated = False
        if hasattr(self, 'pre_calculated_indicators') and self.pre_calculated_indicators is not None:
            if isinstance(self.pre_calculated_indicators, pd.DataFrame) and not self.pre_calculated_indicators.empty:
                use_pre_calculated = True
        if not use_pre_calculated and hasattr(self, 'pre_calculated_features') and self.pre_calculated_features is not None:
            if isinstance(self.pre_calculated_features, pd.DataFrame) and not self.pre_calculated_features.empty:
                use_pre_calculated = True

        signals_df = None

        # Always create bar_df from current bar (needed for price lookup in trade authorization)
        bar_df_dict = dict(bar_dict)
        if 'timestamp' in bar_df_dict:
            bar_df_dict.pop('timestamp')
        bar_df = pd.DataFrame([bar_df_dict], index=[timestamp])
        bar_df.index.name = 'timestamp'
        bar_df = bar_df.reset_index()

        if use_pre_calculated:
            # Get pre-calculated features UP TO AND INCLUDING current bar
            # Strategy needs historical context, not just the single bar
            try:
                # Match by timestamp instead of index to handle filtered bars correctly
                bar_timestamp = pd.Timestamp(timestamp)

                # Find index of current bar in pre_calculated_features
                if 'timestamp' in self.pre_calculated_features.columns:
                    current_bar_iloc = self._get_precalc_bar_iloc_fast(
                        "precalc_features_main",
                        self.pre_calculated_features,
                        bar_timestamp,
                    )
                    if current_bar_iloc is None:
                        timestamps = self._get_cached_timestamp_series(
                            "precalc_features_main",
                            self.pre_calculated_features,
                        )
                        current_bar_mask = timestamps == bar_timestamp
                        if current_bar_mask.any():
                            import numpy as np
                            current_bar_iloc = np.argmax(current_bar_mask.values)

                    if current_bar_iloc is not None:
                        # Exclude current bar to prevent lookahead bias
                        features_historical = self.pre_calculated_features.iloc[:current_bar_iloc].copy()

                        # Ensure features_historical has timestamp index for strategy consistency
                        if 'timestamp' in features_historical.columns:
                            features_historical = features_historical.set_index('timestamp')
                    else:
                        features_historical = pd.DataFrame()
                elif hasattr(self.pre_calculated_features.index, 'equals'):
                    # Exclude current bar via index comparison
                    mask = self.pre_calculated_features.index < bar_timestamp
                    features_historical = self.pre_calculated_features[mask].copy()
                else:
                    # Fallback: exclude current bar via iloc
                    if pre_calc_index < len(self.pre_calculated_features):
                        features_historical = self.pre_calculated_features.iloc[:pre_calc_index].copy()
                    else:
                        features_historical = pd.DataFrame()  # Empty if out of bounds

                # SESSION ISOLATION: Clip features_historical to the
                # current trading day so that multi-day runs see the
                # same historical depth as individual-day runs.
                if (
                    not features_historical.empty
                    and self._intraday_session_isolation
                    and self._session_start_timestamp is not None
                    and 'timestamp' in features_historical.columns
                ):
                    session_mask = features_historical['timestamp'] >= self._session_start_timestamp
                    features_historical = features_historical[session_mask].copy()

                if not features_historical.empty:
                    # Ensure features_historical has expected format
                    if 'timestamp' in features_historical.columns:
                        # Keep `timestamp` for strategies (required for correct bar timestamp propagation).
                        # If downstream logic wants a regime-specific alias, add it as a copy.
                        if 'regime_timestamp' not in features_historical.columns:
                            features_historical['regime_timestamp'] = features_historical['timestamp']

                    # Call strategy's generate_signals with Dict[symbol, enriched DataFrame with indicators]
                    # Strategy receives pre-calculated indicators with FULL HISTORICAL CONTEXT
                    # Get current positions for strategy context (ENHANCED with entry prices)
                    current_positions = self.risk_manager.current_positions if self.risk_manager else {}

                    # ========================================
                    # PRICE-AWARE POSITION CONTEXT
                    # ========================================
                    # Build rich position context with entry prices and unrealized P&L
                    # Use CURRENT bar's close price for mark-to-market
                    position_details = {}
                    if self.risk_manager and hasattr(self, 'pnl_tracker') and self.pnl_tracker:
                        for sym, qty in current_positions.items():
                            if abs(qty) > self.MIN_POSITION_QTY:  # Has position
                                entry_price = self.pnl_tracker.position_cost_basis.get(sym, 0.0)
                                entry_time = getattr(self.pnl_tracker, 'position_entry_time', {}).get(sym)

                                # Determine if position is carried over from a previous day
                                is_carried_over = False
                                if entry_time:
                                    # Handle timezone awareness for comparison
                                    entry_date = entry_time.date() if hasattr(entry_time, 'date') else None
                                    current_date = bar_timestamp.date() if hasattr(bar_timestamp, 'date') else None

                                    if entry_date and current_date and entry_date < current_date:
                                        is_carried_over = True

                                # Use current bar's close price, not stale cached price
                                if not features_historical.empty and 'close' in features_historical.columns:
                                    current_price_sym = features_historical['close'].iloc[-1]
                                else:
                                    current_price_sym = self.risk_manager.current_prices.get(sym, entry_price)
                                unrealized_pnl = (current_price_sym - entry_price) * qty
                                pnl_pct = ((current_price_sym - entry_price) / entry_price * 100) if entry_price > 0 else 0.0
                                position_details[sym] = {
                                    'quantity': qty,
                                    'entry_price': entry_price,
                                    'entry_time': entry_time,
                                    'current_price': current_price_sym,
                                    'unrealized_pnl': unrealized_pnl,
                                    'pnl_pct': pnl_pct,
                                    'is_profitable': pnl_pct > 0,
                                    'is_carried_over': is_carried_over
                                }

                    # Build per-symbol enriched data: OHLCV + indicators + selected features
                    enriched_data_per_symbol = {}
                    is_multi_symbol = len(self.config.symbols) > 1
                    tz_align_cache = {} if self._use_fast_tz_alignment else None

                    for sym in self.config.symbols:
                        # Prefer per-symbol pre-calculated INDICATORS (closer to PT semantics).
                        if hasattr(self, 'pre_calculated_indicators_per_symbol') and sym in getattr(self, 'pre_calculated_indicators_per_symbol', {}):
                            sym_ind = self.pre_calculated_indicators_per_symbol[sym]
                            if sym_ind is not None and len(sym_ind) > 0:
                                if 'timestamp' in sym_ind.columns:
                                    df_enriched = self._slice_precalc_indexed_before_timestamp_fast(
                                        f"precalc_ind_sym::{sym}",
                                        sym_ind,
                                        bar_timestamp,
                                        tz_align_cache=tz_align_cache,
                                    )
                                    if df_enriched is None:
                                        df_enriched = self._slice_df_before_timestamp_fast(
                                        f"precalc_ind_sym::{sym}",
                                        sym_ind,
                                        bar_timestamp,
                                        tz_align_cache=tz_align_cache,
                                        )
                                    if df_enriched is None:
                                        ts_compare = pd.Timestamp(bar_timestamp)
                                        sym_ts = self._get_cached_timestamp_series(
                                            f"precalc_ind_sym::{sym}",
                                            sym_ind,
                                        )
                                        ts_compare = self._align_timestamp_to_index_tz(
                                            ts_compare,
                                            getattr(sym_ts.dt, 'tz', None),
                                            cache=tz_align_cache,
                                        )
                                        # AXIS2 FIX: Strict < to EXCLUDE current bar's close
                                        # from signal generation (prevents lookahead bias).
                                        mask = sym_ts < ts_compare
                                        df_enriched = sym_ind[mask].copy()
                                        # Ensure datetime index for strategy zscore/window logic
                                        try:
                                            if 'timestamp' in df_enriched.columns:
                                                df_enriched = df_enriched.set_index('timestamp')
                                        except Exception as _idx_err:
                                            logger.debug(f"Enriched data index set for {sym}: {_idx_err}")
                                    enriched_data_per_symbol[sym] = df_enriched
                                    continue

                        # Single-symbol fallback: use the pre-calculated indicators slice (not features)
                        if not is_multi_symbol and getattr(self, 'pre_calculated_indicators', None) is not None:
                            try:
                                ind_df = self.pre_calculated_indicators
                                if isinstance(ind_df, pd.DataFrame) and not ind_df.empty:
                                    if 'timestamp' in ind_df.columns:
                                        df_enriched = self._slice_precalc_indexed_before_timestamp_fast(
                                            "precalc_ind_single",
                                            ind_df,
                                            bar_timestamp,
                                            tz_align_cache=tz_align_cache,
                                        )
                                        if df_enriched is None:
                                            df_enriched = self._slice_df_before_timestamp_fast(
                                            "precalc_ind_single",
                                            ind_df,
                                            bar_timestamp,
                                            tz_align_cache=tz_align_cache,
                                            )
                                        if df_enriched is None:
                                            ts_compare = pd.Timestamp(bar_timestamp)
                                            ind_ts = self._get_cached_timestamp_series(
                                                "precalc_ind_single",
                                                ind_df,
                                            )
                                            ts_compare = self._align_timestamp_to_index_tz(
                                                ts_compare,
                                                getattr(ind_ts.dt, 'tz', None),
                                                cache=tz_align_cache,
                                            )
                                            # AXIS2 FIX: Strict < to EXCLUDE current bar
                                            m = ind_ts < ts_compare
                                            df_enriched = ind_df[m].copy()
                                            if 'timestamp' in df_enriched.columns:
                                                df_enriched = df_enriched.set_index('timestamp')
                                        enriched_data_per_symbol[sym] = df_enriched
                                        continue
                            except Exception as _ind_err:
                                logger.debug(f"Single-symbol indicator fallback for {sym}: {_ind_err}")

                        # Last resort: use features_historical (kept for backward compatibility)
                        if not is_multi_symbol and not features_historical.empty:
                            enriched_data_per_symbol[sym] = features_historical
                            continue

                        logger.warning(
                            f"⚠️  No enriched features available for {sym}; skipping raw market_data fallback"
                        )
                        enriched_data_per_symbol[sym] = pd.DataFrame(
                            columns=['open', 'high', 'low', 'close', 'volume']
                        )

                    # Merge feature-only columns (ADS gating features) into indicator data.
                    # Feature columns like directional_coherence, transition_score,
                    # vol_of_vol, composite_accel_norm are NOT in the indicator engine
                    # output. We selectively merge them from the pre-calculated features
                    # DataFrame, avoiding full replacement (which would clobber indicator
                    # column scales via feature-engineer normalization).
                    _FEATURE_ONLY_COLS = [
                        'directional_coherence', 'transition_score', 'vol_of_vol',
                        'composite_accel_norm', 'composite_velocity_norm',
                        'composite_velocity', 'momentum_acceleration',
                    ]
                    for sym, df_ind in enriched_data_per_symbol.items():
                        if df_ind is None or df_ind.empty:
                            continue
                        # Locate the matching features source
                        _feat_src = None
                        if hasattr(self, 'pre_calculated_features_per_symbol') and sym in getattr(self, 'pre_calculated_features_per_symbol', {}):
                            _feat_src = self.pre_calculated_features_per_symbol[sym]
                        elif hasattr(self, 'pre_calculated_features') and self.pre_calculated_features is not None:
                            _feat_src = self.pre_calculated_features
                        if _feat_src is None or _feat_src.empty:
                            continue

                        # Determine which columns to merge (present in features, missing in indicators)
                        cols_to_merge = [c for c in _FEATURE_ONLY_COLS if c in _feat_src.columns and c not in df_ind.columns]
                        if not cols_to_merge:
                            continue

                        try:
                            # Align features to indicator index for safe merge
                            _feat_indexed = _feat_src
                            if 'timestamp' in _feat_indexed.columns and not isinstance(_feat_indexed.index, pd.DatetimeIndex):
                                _feat_indexed = _feat_indexed.set_index('timestamp')
                            # Use reindex to align, filling NaN for missing timestamps
                            for col in cols_to_merge:
                                if col in _feat_indexed.columns:
                                    df_ind[col] = _feat_indexed[col].reindex(df_ind.index).values
                        except Exception as _merge_err:
                            logger.debug(f"Feature column merge for {sym}: {_merge_err}")

                    # SESSION ISOLATION: Clip enriched data to the current
                    # trading session so multi-day runs give the strategy
                    # the same historical depth as individual-day runs.
                    if (
                        self._intraday_session_isolation
                        and self._session_start_timestamp is not None
                    ):
                        for _iso_sym in list(enriched_data_per_symbol.keys()):
                            _iso_df = enriched_data_per_symbol[_iso_sym]
                            if _iso_df is None or _iso_df.empty:
                                continue
                            # Determine which column / index holds timestamps
                            if 'timestamp' in _iso_df.columns:
                                _iso_mask = _iso_df['timestamp'] >= self._session_start_timestamp
                                enriched_data_per_symbol[_iso_sym] = _iso_df[_iso_mask].copy()
                            elif isinstance(_iso_df.index, pd.DatetimeIndex):
                                _iso_mask = _iso_df.index >= self._session_start_timestamp
                                enriched_data_per_symbol[_iso_sym] = _iso_df[_iso_mask].copy()

                    # --- CP1s: Pipeline Trace - Bar Feature Slice (lookahead guard) ---
                    # This is the most dangerous data handoff in the pipeline.
                    # Records what the strategy actually receives so post-hoc
                    # auditing can verify no-lookahead for every single bar.
                    try:
                        from core_engine.utils.pipeline_trace import get_tracer, CP1s_BAR_SLICE
                        _cp1s_tracer = get_tracer()
                        if _cp1s_tracer.enabled:
                            # Determine the last timestamp in the feature slice
                            _primary_sym = self.config.symbols[0] if self.config.symbols else None
                            _slice_df = enriched_data_per_symbol.get(_primary_sym)
                            _slice_end_ts = None
                            _slice_rows = 0
                            if _slice_df is not None and not _slice_df.empty:
                                _slice_rows = len(_slice_df)
                                if 'timestamp' in _slice_df.columns:
                                    _slice_end_ts = str(_slice_df['timestamp'].iloc[-1])
                                elif hasattr(_slice_df.index, 'max'):
                                    _slice_end_ts = str(_slice_df.index[-1])

                            _lookahead_safe = True
                            if _slice_end_ts is not None:
                                try:
                                    _slice_end_pd = pd.Timestamp(_slice_end_ts)
                                    _bar_ts_pd = pd.Timestamp(bar_timestamp)
                                    _lookahead_safe = _slice_end_pd < _bar_ts_pd
                                except Exception:
                                    pass

                            _cp1s_tracer.emit(
                                trace_id=f"slice_{_primary_sym}_{bar_timestamp}",
                                checkpoint=CP1s_BAR_SLICE,
                                component="InstitutionalBacktestEngine",
                                method="_process_single_bar",
                                symbol=_primary_sym or "",
                                bar_timestamp=str(bar_timestamp),
                                input_data={
                                    "bar_timestamp": str(bar_timestamp),
                                    "bar_index": bar_index,
                                    "pre_calc_index": pre_calc_index,
                                },
                                output_data={
                                    "slice_end_timestamp": _slice_end_ts,
                                    "slice_rows": _slice_rows,
                                    "symbols_in_slice": list(enriched_data_per_symbol.keys()),
                                    "lookahead_safe": _lookahead_safe,
                                },
                                metadata={
                                    "lookahead_safe": _lookahead_safe,
                                },
                            )
                    except Exception:
                        pass  # Tracing must never break the bar loop

                    signals_result = await self.strategy_manager.generate_signals(
                        self.config.symbols,
                        enriched_data_per_symbol,
                        current_positions,
                        position_details=position_details  # Pass rich position context
                    )
                    # Strategy returns List[Signal], convert to DataFrame
                    if signals_result is not None and len(signals_result) > 0:
                        signals_df = pd.DataFrame([_signal_to_dict(s) for s in signals_result])
                else:
                    # No historical data before this bar (expected for first bar).
                    # Fall back to on-the-fly calculation.
                    use_pre_calculated = False
                    logger.debug(f"Pre-calculated features not found for timestamp {bar_timestamp}, falling back to on-the-fly")

            except Exception as e:
                use_pre_calculated = False
                logger.warning(f"⚠️  Pre-calculation access failed: {e}, falling back to on-the-fly")

        # Fallback to on-the-fly calculation if pre-calculated data not available
        if not use_pre_calculated:
            # bar_df already created above (before the pre-calc branch)

            # Accumulate historical market data for strategies
            for symbol in self.config.symbols:
                if symbol not in self.historical_market_data:
                    self.historical_market_data[symbol] = pd.DataFrame()
                # Append current bar to historical data
                self.historical_market_data[symbol] = pd.concat([self.historical_market_data[symbol], bar_df], ignore_index=True)

            # Calculate on-the-fly using accumulated history
            symbol = self.config.symbols[0]  # Standard for single-asset on-the-fly fallback
            historical_df = self.historical_market_data.get(symbol, bar_df)

            indicators_df = self.indicators_engine.calculate_indicators(historical_df) if self.indicators_engine else historical_df
            features_df = self.feature_engineer.create_features(indicators_df) if self.feature_engineer and indicators_df is not None else indicators_df

            # Use enriched features even in on-the-fly fallback
            if self.strategy_manager and hasattr(self.strategy_manager, 'active_strategies') and self.strategy_manager.active_strategies:
                # STRATEGY generates signals based on enriched features (not raw OHLCV)
                try:
                    logger.debug(f"Pre-calculation unavailable, generating enriched features on-the-fly at bar {bar_index}")

                    # Pass enriched features to strategy (not raw OHLCV)
                    # Get current positions for strategy context
                    current_positions = self.risk_manager.current_positions if self.risk_manager else {}

                    # Build rich position context (fallback path)
                    position_details = {}
                    if self.risk_manager and hasattr(self, 'pnl_tracker') and self.pnl_tracker:
                        for sym, qty in current_positions.items():
                            if abs(qty) > self.MIN_POSITION_QTY:
                                entry_price = self.pnl_tracker.position_cost_basis.get(sym, 0.0)
                                current_price_sym = self.risk_manager.current_prices.get(sym, 0.0)
                                unrealized_pnl = self.pnl_tracker.position_pnl.get(sym, 0.0)
                                pnl_pct = ((current_price_sym - entry_price) / entry_price * 100) if entry_price > 0 else 0.0
                                position_details[sym] = {
                                    'quantity': qty,
                                    'entry_price': entry_price,
                                    'current_price': current_price_sym,
                                    'unrealized_pnl': unrealized_pnl,
                                    'pnl_pct': pnl_pct,
                                    'is_profitable': pnl_pct > 0  # Fix: use pnl_pct, not unrealized_pnl
                                }

                    # Build enriched_data_per_symbol from on-the-fly features_df
                    # (not raw market_data — strategies expect enriched columns)
                    enriched_data_per_symbol = {}
                    for sym in self.config.symbols:
                        if features_df is not None and not features_df.empty:
                            # Use the freshly-computed features (OHLCV + indicators + features)
                            enriched_data_per_symbol[sym] = features_df.copy()
                        else:
                            logger.warning(
                                f"[WARN] No enriched features for {sym} in on-the-fly path; raw fallback disabled"
                            )
                            enriched_data_per_symbol[sym] = pd.DataFrame(
                                columns=['open', 'high', 'low', 'close', 'volume']
                            )

                    signals_result = await self.strategy_manager.generate_signals(
                        self.config.symbols,
                        enriched_data_per_symbol,
                        current_positions,
                        position_details=position_details  # Pass rich position context
                    )

                    # Strategy returns List[Signal], convert to DataFrame
                    if signals_result is not None:
                        if isinstance(signals_result, list) and len(signals_result) > 0:
                            signals_df = pd.DataFrame([_signal_to_dict(s) for s in signals_result])
                            logger.info(f"   [OK] Generated {len(signals_df)} signals from fallback enriched features")
                        elif isinstance(signals_result, pd.DataFrame) and not signals_result.empty:
                            signals_df = signals_result
                except Exception as e:
                    logger.error(f"Fallback strategy generation failed: {e}", exc_info=True)
                    # No further fallback — signal generation is the strategy's
                    # responsibility.  If the strategy fails, no signals for this bar.
            else:
                # No strategy manager — cannot generate signals.
                logger.warning("[WARN] No strategy manager available, skipping signal generation")

        return bar_df, signals_df

    async def _process_single_bar(self,
                                  bar: pd.Series,
                                  timestamp: datetime,
                                  bar_index: int,
                                  pre_calc_index: int = 0) -> Dict[str, Any]:
        """
        Process a single bar of market data through the complete pipeline.

        Optimized: each logical step is delegated to a focused helper method
        for readability, testability, and profiling granularity.
        """
        bar_results = {
            'timestamp': timestamp,
            'bar_index': bar_index,
            'signals_generated': 0,
            'trades_authorized': 0,
            'trades_executed': 0,
            'regime': None
        }

        try:
            bar_dict = self._bar_to_dict(bar)

            # Step 1: Update regime engine (Rule 2 - Regime-First)
            self._update_regime_for_bar(bar_dict, timestamp, bar_index)

            # Step 2: EOD guard
            _eod_guard_active = self.eod_guard.is_active(timestamp)
            if _eod_guard_active and self.pending_signals:
                kept, discarded = self.eod_guard.filter_signals(self.pending_signals)
                if discarded > 0:
                    logger.debug(
                        f"EOD guard: Discarding {discarded} entry pending signals "
                        f"at {timestamp} (kept {len(kept)} exits)"
                    )
                self.pending_signals = kept

            # Step 3: Execute prior-bar pending signals at THIS bar's open
            bar_results['trades_executed'] = await self._drain_pending_signals(
                bar, timestamp, bar_index
            )

            # EOD guard: skip signal generation entirely
            if _eod_guard_active:
                bar_results['signals_generated'] = 0
                return bar_results

            # Generate signals for this bar (pre-calculated or on-the-fly)
            bar_df, signals_df = await self._generate_signals_for_bar(
                bar_dict, timestamp, bar_index, pre_calc_index
            )
            if signals_df is not None and not signals_df.empty:
                bar_results['signals_generated'] = len(signals_df)

            # Step 3: Generate NEW signals and QUEUE them for next bar
            # Signals generated at bar N will execute at bar N+1 open
            if signals_df is not None and not signals_df.empty:
                # Get authorized trades (validation happens now, execution happens next bar)
                authorized_trades = await self._get_authorized_trades_for_bar(
                    bar_df, signals_df, timestamp
                )

                bar_results['trades_authorized'] = len(authorized_trades)

                # QUEUE authorized trades for next bar execution (not immediate!)
                if authorized_trades:
                    for trade in authorized_trades:
                        # Store the signal bar's close price for reference (decision price)
                        trade['signal_bar_close'] = bar.get('close', 0)
                        trade['signal_bar_index'] = bar_index
                        trade['signal_timestamp'] = timestamp

                    self.pending_signals.extend(authorized_trades)

            # Update market prices for unrealized P&L via CentralRiskManager (Rule 4)
            await self._update_market_prices_for_bar(timestamp)

            # ADS v3.1 exits in backtest: synthesize exit signals when multi-exit rules trigger.
            await self._evaluate_multi_exit_rules(bar, bar_index, timestamp)

            # Record position history after execution
            self._record_position_snapshot(timestamp)

            return bar_results

        except Exception as e:
            logger.error(f"❌ Error processing bar at {timestamp}: {e}")
            bar_results['error'] = str(e)
            return bar_results

    # ============================================================
    # EXTRACTED HELPERS FROM _process_single_bar (optimization)
    # ============================================================

    def _update_regime_for_bar(
        self,
        bar_dict: Dict[str, Any],
        timestamp: datetime,
        bar_index: int,
    ) -> None:
        """Step 1: Feed bar to regime engine (Rule 2 - Regime-First)."""
        if not self.regime_engine:
            return
        regime_bar_dict = dict(bar_dict)
        regime_bar_dict['timestamp'] = timestamp
        try:
            # Feed bar to RegimeManager for regime state update
            self.regime_engine.process_market_data(regime_bar_dict)
        except Exception as e:
            if bar_index == 0:
                logger.warning(f"⚠️ Regime engine processing failed: {e}")

    async def _drain_pending_signals(
        self,
        bar: pd.Series,
        timestamp: datetime,
        bar_index: int,
    ) -> int:
        """Execute prior-bar pending signals at current bar's OPEN price.

        Returns the number of trades executed.
        """
        if not self.pending_signals:
            return 0

        try:
            max_signal_age_bars = 1
            fresh_signals = []
            for sig in self.pending_signals:
                sig_bar_idx = sig.get('signal_bar_index')
                if sig_bar_idx is None:
                    logger.warning(
                        f"⚠️ Dropping signal with no signal_bar_index: "
                        f"{sig.get('symbol')} {sig.get('side')} — treating as stale"
                    )
                elif (bar_index - sig_bar_idx) > max_signal_age_bars:
                    logger.warning(
                        f"⚠️ Expired stale signal: {sig.get('symbol')} {sig.get('side')} "
                        f"(age={bar_index - sig_bar_idx} bars > max {max_signal_age_bars})"
                    )
                else:
                    fresh_signals.append(sig)

            open_price = bar.get('open', bar.get('close', 0))
            executed_trades = await self._execute_pending_signals(
                fresh_signals,
                bar,
                timestamp,
                execution_price=open_price,
            )
            return len(executed_trades)
        except Exception:
            logger.warning("Pending-signal execution failed", exc_info=True)
            return 0
        finally:
            self.pending_signals = []

    def _record_position_snapshot(self, timestamp: datetime) -> None:
        """Record position state for equity curve / analytics."""
        if not self.risk_manager:
            return

        pnl_source = getattr(self, 'pnl_tracker', None) or self.risk_manager
        snapshot = {
            'timestamp': timestamp,
            'equity': (
                self.risk_manager.portfolio_value
                if hasattr(self.risk_manager, 'portfolio_value')
                else self.config.initial_capital
            ),
            'cash': self.risk_manager.available_cash,
            'total_pnl': getattr(pnl_source, 'total_pnl', 0.0),
            'realized_pnl': getattr(pnl_source, 'realized_pnl', 0.0),
            'unrealized_pnl': getattr(pnl_source, 'unrealized_pnl', 0.0),
            'position_count': len(self.risk_manager.current_positions),
            'max_drawdown': getattr(self.risk_manager, 'max_drawdown', 0.0),
            'max_drawdown_pct': getattr(self.risk_manager, 'max_drawdown_pct', 0.0),
        }
        self.position_history.append(snapshot)

        # Downsample with peak/trough retention if over memory cap
        if len(self.position_history) > self._max_position_history:
            if not self._position_history_trim_warned:
                logger.info(
                    f"📊 position_history exceeded {self._max_position_history} entries — "
                    f"downsampling with peak/trough retention"
                )
                self._position_history_trim_warned = True
            self.position_history = self._downsample_with_peaks(self.position_history)

    # ============================================================
    # PER-BAR MARKET PRICE UPDATE
    # ============================================================

    async def _update_market_prices_for_bar(self, timestamp) -> None:
        """
        Collect the latest close prices for all open positions and push them to
        CentralRiskManager in a single batch.

        This is extracted from _process_single_bar for readability. It performs a
        timezone-safe lookup against self.market_data.
        """
        if not (self.risk_manager and self.risk_manager.current_positions):
            return

        current_prices = {}
        bar_ts = pd.Timestamp(timestamp)
        tz_align_cache = {} if self._use_fast_tz_alignment else None
        for symbol in self.risk_manager.current_positions.keys():
            if symbol not in self.market_data:
                continue

            symbol_data = self.market_data[symbol]
            try:
                fast_close = self._get_latest_close_price_fast(
                    symbol,
                    symbol_data,
                    bar_ts,
                    tz_align_cache=tz_align_cache,
                )
                if fast_close is not None:
                    current_prices[symbol] = fast_close
                    continue

                sym_df = symbol_data
                sym_df_indexed = self._get_market_data_time_indexed(
                    f"mtm::{symbol}",
                    sym_df,
                )
                if sym_df_indexed is not None:
                    sym_df = sym_df_indexed

                ts_compare = self._align_timestamp_to_index_tz(
                    bar_ts,
                    getattr(sym_df.index, 'tz', None),
                    cache=tz_align_cache,
                )

                filtered = sym_df[sym_df.index <= ts_compare]
                if len(filtered) > 0:
                    close_col = 'close' if 'close' in filtered.columns else 'Close'
                    if close_col in filtered.columns:
                        current_prices[symbol] = float(filtered[close_col].iloc[-1])
                        continue
            except Exception:
                pass

            # Fallback: use last available close in the dataframe
            if not symbol_data.empty:
                try:
                    close_col = 'close' if 'close' in symbol_data.columns else 'Close'
                    if close_col in symbol_data.columns:
                        current_prices[symbol] = float(symbol_data[close_col].iloc[-1])
                except Exception:
                    pass

        # P1 F3: Survivorship bias — symbols without price when we have positions
        for symbol in list(self.risk_manager.current_positions.keys()):
            if symbol not in current_prices:
                self._symbol_dropout_tracker.add(symbol)
                fallback_price = None
                if hasattr(self.risk_manager, 'pnl_tracker') and self.risk_manager.pnl_tracker:
                    fallback_price = self.risk_manager.pnl_tracker.position_cost_basis.get(symbol)
                if fallback_price is None and self.position_book:
                    pos = self.position_book.get_position(symbol)
                    if pos is not None:
                        fallback_price = getattr(pos, 'avg_entry_price', None) or getattr(pos, 'current_price', None)
                if fallback_price is not None and fallback_price > 0:
                    current_prices[symbol] = float(fallback_price)
                    logger.warning(
                        "⚠️ P1 F3: No price for %s (position held) — using cost basis $%.4f; "
                        "symbol tracked as dropout",
                        symbol, fallback_price,
                    )
                else:
                    logger.warning(
                        "⚠️ P1 F3: No price for %s (position held) — cannot update; "
                        "symbol tracked as dropout",
                        symbol,
                    )

        # Update via CentralRiskManager (single source of truth)
        if current_prices and hasattr(self.risk_manager, 'update_market_prices'):
            await self.risk_manager.update_market_prices(current_prices, timestamp=timestamp)

    # ============================================================
    # ADS MULTI-EXIT EVALUATION
    # ============================================================

    @staticmethod
    def _safe_float(v):
        """Safe float conversion (None-safe)."""
        if v is None:
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    async def _evaluate_multi_exit_rules(
        self,
        bar: pd.Series,
        bar_index: int,
        timestamp: datetime,
    ) -> None:
        """
        ADS v3.1: Evaluate multi-exit rules for all open positions and queue
        exit signals when triggered.

        This is a self-contained step extracted from _process_single_bar for
        readability.  It only appends to self.pending_signals; the actual
        execution happens on the next bar.
        """
        try:
            if not (self.risk_manager and self.risk_manager.current_positions and self.position_book is not None):
                return

            from core_engine.risk.multi_exit_engine import decide_exit

            exit_rows = []
            positions = self.position_book.get_all_positions()
            for sym, pos in positions.items():
                strat_id = getattr(pos, 'strategy_id', None)
                enable_ads_multi_exit = bool(self._get_strategy_param("enable_ads_multi_exit", False, strategy_id=strat_id))
                max_holding_minutes = float(self._get_strategy_param("max_holding_minutes", 0.0, strategy_id=strat_id) or 0.0)

                if not enable_ads_multi_exit or max_holding_minutes <= 0:
                    continue

                enable_forward_vol_stops = bool(self._get_strategy_param("enable_forward_vol_stops", False, strategy_id=strat_id))

                try:
                    pos_is_long = getattr(pos, "is_long", True)
                    qty = float(getattr(pos, "quantity", 0.0))
                    if abs(qty) <= 0:
                        continue
                    opened_at = getattr(pos, "opened_at", None)
                    if opened_at is None:
                        continue

                    exit_side = "sell" if pos_is_long else "buy"

                    # Skip if an exit is already pending for this symbol
                    if any((t.get("symbol") == sym and str(t.get("side", "")).lower() == exit_side) for t in (self.pending_signals or [])):
                        continue

                    held_mins = (timestamp - opened_at).total_seconds() / 60.0

                    # Direction-aware PnL
                    avg_entry = float(getattr(pos, "avg_entry_price", 0.0) or 0.0)
                    px = float(self.risk_manager.current_prices.get(sym, avg_entry) or avg_entry or 0.0)
                    if avg_entry > 0:
                        pnl_pct = ((px - avg_entry) / avg_entry) * 100.0 if pos_is_long else ((avg_entry - px) / avg_entry) * 100.0
                    else:
                        pnl_pct = 0.0

                    # Optional forward-looking vol stop
                    stop_loss_pct_val = self._compute_vol_stop(
                        sym, enable_forward_vol_stops
                    )

                    # Entry & current state for health-based exits
                    pos_meta = getattr(pos, "metadata", None) or {}
                    _sf = self._safe_float

                    entry_state = {
                        'coherence': _sf(pos_meta.get("entry_coherence")),
                        'composite_accel': _sf(pos_meta.get("entry_composite_accel")),
                        'vol_of_vol': _sf(pos_meta.get("entry_vol_of_vol")),
                        'transition_score': _sf(pos_meta.get("transition_score")),
                        'composite_z': _sf(pos_meta.get("composite_z")),
                        # Causal chain entry state
                        'flow_confirmed': pos_meta.get("entry_flow_confirmed"),
                    }
                    current_state = self._lookup_current_exit_features(sym, timestamp)

                    # Resolve strategy-specific momentum columns from position metadata
                    _short_mom = None
                    _medium_mom = None
                    _feat_row = current_state.pop('_feat_row', None)
                    if _feat_row is not None:
                        _short_col = pos_meta.get("entry_short_momentum_col", "momentum_10")
                        _medium_col = pos_meta.get("entry_medium_momentum_col", "momentum_20")
                        _short_mom = _sf(_feat_row.get(_short_col))
                        _medium_mom = _sf(_feat_row.get(_medium_col))

                    # Config parameters (strategy-specific)
                    _health_crit = float(self._get_strategy_param("health_critical_threshold", 0.15, strategy_id=strat_id))
                    _accel_exhaust = float(self._get_strategy_param("accel_exhaustion_threshold", -0.3, strategy_id=strat_id))
                    _tp_init = float(self._get_strategy_param("tp_initial_pct", 2.0, strategy_id=strat_id))
                    _tp_floor = float(self._get_strategy_param("tp_floor_pct", 0.3, strategy_id=strat_id))
                    _tp_decay = float(self._get_strategy_param("tp_decay_minutes", 30.0, strategy_id=strat_id))
                    _health_tp = float(self._get_strategy_param("health_tp_trigger", 0.7, strategy_id=strat_id))

                    _noise_floor = float(self._get_strategy_param("momentum_noise_floor", 0.001, strategy_id=strat_id))

                    decision = decide_exit(
                        now=timestamp,
                        opened_at=opened_at,
                        pnl_pct=float(pnl_pct),
                        is_long=pos_is_long,
                        stop_loss_pct=stop_loss_pct_val,
                        # Entry transition state
                        entry_coherence=entry_state['coherence'],
                        entry_composite_accel=entry_state['composite_accel'],
                        entry_vol_of_vol=entry_state['vol_of_vol'],
                        entry_transition_score=entry_state['transition_score'],
                        entry_composite_z=entry_state['composite_z'],
                        # Causal chain entry state
                        entry_flow_confirmed=entry_state.get('flow_confirmed'),
                        # Current transition state
                        current_coherence=current_state.get('coherence'),
                        current_composite_accel=current_state.get('composite_accel'),
                        current_vol_of_vol=current_state.get('vol_of_vol'),
                        current_composite_z=current_state.get('composite_z'),
                        # Causal chain current state
                        current_short_momentum=_short_mom,
                        current_medium_momentum=_medium_mom,
                        current_volume_ratio=current_state.get('volume_ratio'),
                        # Thresholds
                        health_critical_threshold=_health_crit,
                        accel_exhaustion_threshold=_accel_exhaust,
                        momentum_noise_floor=_noise_floor,
                        tp_initial_pct=_tp_init,
                        tp_floor_pct=_tp_floor,
                        tp_decay_minutes=_tp_decay,
                        health_tp_trigger=_health_tp,
                        max_holding_minutes=float(max_holding_minutes),
                        liquidity_bad=False,
                        liquidity_details=None,
                    )

                    if decision.should_exit:
                        exit_signal_type = "long_exit" if pos_is_long else "short_exit"
                        exit_rows.append({
                            "symbol": sym,
                            "signal_type": exit_signal_type,
                            "side": exit_side,
                            "strategy_id": strat_id,
                            "confidence": 1.0,
                            "strength": 1.0,
                            "timestamp": timestamp,
                            "additional_data": {
                                "ads_exit": decision.reason,
                                "ads_exit_details": decision.details,
                                "held_minutes": held_mins,
                                "pnl_pct": float(pnl_pct),
                                "stop_loss_pct": float(stop_loss_pct_val) if stop_loss_pct_val is not None else None,
                                "position_side": "long" if pos_is_long else "short",
                            },
                        })
                except Exception:
                    continue

            if exit_rows:
                exit_df = pd.DataFrame(exit_rows)
                bar_df_local = pd.DataFrame([bar.to_dict()])
                authorized_exits = await self._get_authorized_trades_for_bar(bar_df_local, exit_df, timestamp)
                if authorized_exits:
                    for trade in authorized_exits:
                        trade["signal_bar_close"] = bar.get("close", 0)
                        trade["signal_bar_index"] = bar_index
                        trade["signal_timestamp"] = timestamp
                    self.pending_signals.extend(authorized_exits)
        except Exception as e:
            logger.warning(f"ADS exit processing error (non-fatal): {e}")

    def _compute_vol_stop(self, sym: str, enabled: bool) -> Optional[float]:
        """Compute forward-looking vol stop distance for a symbol, if enabled."""
        if not enabled:
            return None
        try:
            import numpy as np
            from core_engine.risk.volatility_forecast import (
                VolStopParams, correlation_change, sigma_eff, stop_distance_pct,
            )
            sym_prices = list(getattr(self.risk_manager, "_price_history", {}).get(sym, []))
            if len(sym_prices) < 3:
                return None
            sp = np.asarray(sym_prices, dtype=float)
            sym_returns = list(np.diff(sp) / sp[:-1])

            benchmark = str(getattr(self.risk_manager.config, "corr_benchmark_symbol", "SPY"))
            bench_prices = list(getattr(self.risk_manager, "_price_history", {}).get(benchmark, []))
            bench_returns = []
            if len(bench_prices) >= 3:
                bp = np.asarray(bench_prices, dtype=float)
                bench_returns = list(np.diff(bp) / bp[:-1])

            s_eff, _, _ = sigma_eff(
                sym_returns,
                realized_window=int(getattr(self.risk_manager.config, "vol_realized_window", 20)),
                lambda_=float(getattr(self.risk_manager.config, "vol_ewma_lambda", 0.94)),
            )
            d_rho = correlation_change(
                sym_returns, bench_returns,
                short_window=int(getattr(self.risk_manager.config, "corr_short_window", 20)),
                long_window=int(getattr(self.risk_manager.config, "corr_long_window", 60)),
            )
            params = VolStopParams(
                k=float(getattr(self.risk_manager.config, "stop_k", 2.0)),
                kappa=float(getattr(self.risk_manager.config, "stop_kappa", 0.5)),
                overnight_mult=float(getattr(self.risk_manager.config, "stop_overnight_mult", 1.5)),
            )
            sl_frac = stop_distance_pct(s_eff, delta_rho=d_rho, params=params, overnight=False)
            return float(sl_frac) * 100.0
        except Exception:
            return None

    def _lookup_current_exit_features(self, sym: str, timestamp) -> Dict[str, Any]:
        """
        Look up current-state features (coherence, accel, vol_of_vol, composite_z)
        from pre-calculated enriched data for exit evaluation.
        """
        result: Dict[str, Any] = {}
        try:
            _feat_df = None
            if hasattr(self, "pre_calculated_features_per_symbol") and sym in self.pre_calculated_features_per_symbol:
                _feat_df = self.pre_calculated_features_per_symbol[sym]
            elif hasattr(self, "pre_calculated_features") and self.pre_calculated_features is not None:
                _feat_df = self.pre_calculated_features

            if _feat_df is None or len(_feat_df) == 0:
                return result

            _bar_ts = pd.Timestamp(timestamp)
            _feat_row = None
            if isinstance(_feat_df.index, pd.DatetimeIndex):
                if _bar_ts in _feat_df.index:
                    _feat_row = _feat_df.loc[_bar_ts]
                    if hasattr(_feat_row, "iloc") and len(_feat_row.shape) > 1:
                        _feat_row = _feat_row.iloc[-1]
            elif "timestamp" in _feat_df.columns:
                _ts_col = self._get_cached_timestamp_series(
                    f"exit_feat::{sym}",
                    _feat_df,
                )
                _mask = _ts_col == _bar_ts
                if _mask.any():
                    _feat_row = _feat_df.loc[_mask.values].iloc[-1]

            if _feat_row is not None:
                _sf = self._safe_float
                result['coherence'] = _sf(_feat_row.get("directional_coherence"))
                result['composite_accel'] = _sf(_feat_row.get("composite_accel_norm"))
                result['vol_of_vol'] = _sf(_feat_row.get("vol_of_vol"))
                result['composite_z'] = _sf(_feat_row.get("composite_z"))
                # Causal chain features (for alignment_health + flow_health)
                result['volume_ratio'] = _sf(_feat_row.get("volume_ratio"))
                # Momentum columns are strategy-specific (e.g. momentum_10,
                # momentum_20).  The caller provides the column names from
                # position metadata so this lookup is strategy-agnostic.
                result['_feat_row'] = _feat_row  # Expose raw row for column lookup
        except Exception as _feat_err:
            if not getattr(self, "_exit_feat_err_logged", False):
                self._exit_feat_err_logged = True
                logger.warning(f"Exit feature lookup error: {_feat_err}")

        return result

    # ============================================================
    # STRATEGY SIGNAL PROCESSING (PHASE 7.2)
    # ============================================================

    async def _get_authorized_trades_for_bar(self,
                                            bar_df: pd.DataFrame,
                                            signals_df: pd.DataFrame,
                                            timestamp: datetime) -> List[Any]:
        """
        Process signals through strategy manager and get authorized trades

        This method completes the orchestrator lifecycle by connecting:
        1. Generated signals (from processing pipeline)
        2. Strategy evaluation and aggregation
        3. Risk authorization (CentralRiskManager)

        Flow:
            signals → strategy_manager → risk_manager → authorized_trades

        Args:
            bar_df: Current bar data
            signals_df: Generated signals from pipeline
            timestamp: Current timestamp

        Returns:
            List of authorized trades ready for execution
        """
        authorized_trades = []

        try:
            # Check if risk manager is available and initialized
            if self.risk_manager is None:
                logger.warning("⚠️  No risk manager available - signals cannot be authorized")
                return authorized_trades

            if not hasattr(self.risk_manager, 'is_initialized') or not self.risk_manager.is_initialized:
                logger.warning("⚠️  Risk manager not initialized - signals cannot be authorized")
                return authorized_trades
            # Phase 7.2: Strategy manager processes signals
            # For now, we'll directly authorize signals from the pipeline
            # In future phases, this will involve multi-strategy coordination

            # Resolve per-symbol signal conflicts (keep higher-confidence signal)
            _entry_signals = {'buy', 'long_entry', 'short_entry', 'short'}
            _exit_signals = {'sell', 'long_exit', 'short_exit', 'cover', 'close',
                             'close_long', 'close_short', 'flatten'}

            # Group signals by symbol
            symbol_signals = defaultdict(list)
            if self._use_fast_signal_iteration:
                signal_rows_for_group = self._prepare_signal_rows_fast(signals_df)
            else:
                signal_rows_for_group = signals_df.iterrows()

            for _idx, _row in signal_rows_for_group:
                _sym = _row.get('symbol', self.config.symbols[0])
                symbol_signals[_sym].append((_idx, _row))

            # Build a filtered index set — drop lower-confidence side of conflicts
            drop_indices = set()
            for _sym, _sigs in symbol_signals.items():
                if len(_sigs) < 2:
                    continue
                buy_sigs = []
                sell_sigs = []
                for _idx, _row in _sigs:
                    _st_raw = _row.get('signal_type', _row.get('signal', 'HOLD'))
                    _st = _st_raw.value.lower() if hasattr(_st_raw, 'value') else str(_st_raw).lower()
                    if _st in _entry_signals:
                        buy_sigs.append((_idx, _row))
                    elif _st in _exit_signals:
                        sell_sigs.append((_idx, _row))
                if buy_sigs and sell_sigs:
                    # Conflict detected — keep the side with higher max confidence
                    best_buy_conf = max(r.get('confidence', 0) for _, r in buy_sigs)
                    best_sell_conf = max(r.get('confidence', 0) for _, r in sell_sigs)
                    losers = sell_sigs if best_buy_conf >= best_sell_conf else buy_sigs
                    for _idx, _ in losers:
                        drop_indices.add(_idx)
                    logger.info(
                        f"⚔️ Signal conflict on {_sym}: "
                        f"{len(buy_sigs)} buy vs {len(sell_sigs)} sell — "
                        f"dropping {'sell' if best_buy_conf >= best_sell_conf else 'buy'} side"
                    )

            # Track per-bar aggregate cash commitment
            # Prevents multiple BUY signals on the same bar from exceeding
            # available cash when processed sequentially.
            _bar_cash_committed = 0.0
            _available_cash_at_bar = (
                self.risk_manager.available_cash if hasattr(self.risk_manager, 'available_cash')
                else self.config.initial_capital
            )

            # Convert signals to trade requests
            from backtest.utils.validation import validate_signal as _validate_signal
            if self._use_fast_signal_iteration:
                signal_rows_for_auth = self._prepare_signal_rows_fast(signals_df)
            else:
                signal_rows_for_auth = signals_df.iterrows()

            for idx, signal_row in signal_rows_for_auth:
                # H6: Skip signals dropped by conflict resolution
                if idx in drop_indices:
                    continue

                # Validate signal fields before processing
                # Uses soft gate (log + skip) rather than hard raise to avoid crashing
                # the entire backtest on a single malformed signal.
                try:
                    _sig_dict = signal_row.to_dict() if hasattr(signal_row, 'to_dict') else dict(signal_row)
                    # Map 'signal_type' to 'signal' key that validate_signal expects
                    if 'signal' not in _sig_dict and 'signal_type' in _sig_dict:
                        _st = _sig_dict['signal_type']
                        _sig_dict['signal'] = _st.value if hasattr(_st, 'value') else str(_st)
                    # Require symbol + signal type
                    _validate_signal(_sig_dict, bar_index=0,
                                     required_fields=['symbol', 'signal'])
                except Exception as _val_err:
                    logger.warning(f"⚠️ Signal validation failed (skipping): {_val_err}")
                    continue

                # Extract signal information
                symbol = signal_row.get('symbol', self.config.symbols[0])

                # Handle signal_type - can be either SignalType enum, string, or 'signal' field
                signal_type_raw = signal_row.get('signal_type', signal_row.get('signal', 'HOLD'))
                # Convert to lowercase string for comparison
                if hasattr(signal_type_raw, 'value'):
                    signal_type = signal_type_raw.value.lower()  # SignalType enum
                elif hasattr(signal_type_raw, 'lower'):
                    signal_type = signal_type_raw.lower()  # string
                else:
                    signal_type = str(signal_type_raw).lower()

                confidence = signal_row.get('confidence', 0.5)
                signal_strength = signal_row.get('signal_strength', signal_row.get('strength', 0))
                expected_return = signal_row.get('expected_return', None)
                if isinstance(expected_return, (int, float)) and not math.isfinite(expected_return):
                    expected_return = None

                if hasattr(signal_strength, 'value'):
                    signal_strength = signal_strength.value
                try:
                    signal_strength = float(signal_strength)
                except Exception:
                    signal_strength = float(confidence) if isinstance(confidence, (int, float)) else 0.5
                if not math.isfinite(signal_strength):
                    signal_strength = float(confidence) if isinstance(confidence, (int, float)) else 0.5
                signal_strength = max(0.0, min(1.0, signal_strength))

                # Guard against NaN/Inf confidence (would bypass risk gates)
                if not isinstance(confidence, (int, float)) or not math.isfinite(confidence):
                    logger.warning(
                        f"⚠️ Invalid confidence={confidence} for {symbol} — dropping signal"
                    )
                    continue

                # Extract sizing hints from signal
                target_weight = signal_row.get('target_weight', None)
                quantity_type = signal_row.get('quantity_type', 'ABSOLUTE')
                target_quantity = signal_row.get('target_quantity', 0)

                # Signal type → action mapping

                # Normalize signal type to lowercase for comparison
                signal_type_lower = signal_type.lower() if isinstance(signal_type, str) else str(signal_type).lower()

                # Signal type classification (must match conflict resolver)
                entry_signals = ['buy', 'long_entry', 'short_entry', 'short']
                exit_signals = ['sell', 'long_exit', 'short_exit', 'close',
                                'close_long', 'close_short', 'cover', 'flatten']
                actionable_signals = entry_signals + exit_signals

                if signal_type_lower in actionable_signals:

                    # Get current position from CentralRiskManager (Rule 4 SSOT)
                    current_position = 0.0
                    if self.risk_manager:
                        current_position = self.risk_manager.current_positions.get(symbol, 0.0)

                    has_long = current_position > 0
                    has_short = current_position < 0

                    # Get current price for position calculations
                    # For multi-symbol, get price from self.market_data since bar_df may only have primary symbol
                    if symbol in self.market_data and len(self.market_data[symbol]) > 0:
                        sym_data = self.market_data[symbol]
                        if 'timestamp' in sym_data.columns and not isinstance(sym_data.index, pd.DatetimeIndex):
                            sym_data = sym_data.set_index('timestamp')
                        # Filter up to current timestamp
                        ts_compare = pd.Timestamp(timestamp)
                        # Align timezone between timestamp and index
                        if hasattr(sym_data.index, 'tz') and sym_data.index.tz is not None and ts_compare.tz is None:
                            ts_compare = ts_compare.tz_localize(sym_data.index.tz)
                        elif hasattr(ts_compare, 'tz') and ts_compare.tz is not None and (not hasattr(sym_data.index, 'tz') or sym_data.index.tz is None):
                            ts_compare = ts_compare.tz_localize(None)
                        filtered_data = sym_data[sym_data.index <= ts_compare]
                        if len(filtered_data) > 0:
                            current_price = float(filtered_data['close'].iloc[-1])
                        else:
                            # No price data available — skip signal
                            logger.warning(
                                f"⚠️ No price data for {symbol} at {timestamp} "
                                f"(market_data exists but filtered to 0 rows) — skipping signal"
                            )
                            continue
                    elif not bar_df.empty and 'close' in bar_df.columns:
                        # Only use bar_df if it contains data for THIS symbol
                        if 'symbol' in bar_df.columns:
                            symbol_bars = bar_df[bar_df['symbol'] == symbol]
                        else:
                            # Single-symbol bar_df — only use if it matches the signal's symbol
                            symbol_bars = bar_df if symbol == self.config.symbols[0] else pd.DataFrame()
                        if len(symbol_bars) > 0:
                            current_price = float(symbol_bars['close'].iloc[-1])
                        else:
                            logger.warning(
                                f"⚠️ No price data for {symbol} at {timestamp} — skipping signal"
                            )
                            continue
                    else:
                        logger.warning(f"⚠️ No price data for {symbol} at {timestamp} — skipping signal")
                        continue

                    # ================================================================
                    # Determine trade action based on explicit signal type
                    # ================================================================
                    side = None
                    quantity = 0

                    # Helper function for position sizing
                    def calculate_entry_quantity():
                        nonlocal quantity
                        if quantity_type == "PERCENTAGE" and target_weight is not None and target_weight > 0:
                            portfolio_value = self.risk_manager.portfolio_value if (
                                self.risk_manager and hasattr(self.risk_manager, 'portfolio_value')
                            ) else self.config.initial_capital
                            dollar_amount = target_weight * portfolio_value
                            quantity = dollar_amount / current_price
                            quantity = max(1.0, float(quantity))
                            logger.debug(f"   💰 Percentage sizing: {target_weight:.2%} of ${portfolio_value:,.0f} = {quantity} shares @ ${current_price:.2f}")
                        elif target_quantity > 0:
                            quantity = max(1.0, float(target_quantity))
                            logger.debug(f"   💰 Absolute sizing: {quantity} shares")
                        else:
                            if self.config.strategies and len(self.config.strategies) > 0:
                                strategy_params = self.config.strategies[0].get('parameters', {})
                                base_position_pct = strategy_params.get('base_position_pct', None)
                                if base_position_pct is not None:
                                    position_size_pct = base_position_pct
                                else:
                                    position_size_pct = self.config.strategies[0].get('max_position_size', self.config.max_position_size)
                            else:
                                position_size_pct = self.config.max_position_size
                            # Parity with papertest: size off live portfolio value (cash + positions),
                            # not the static initial_capital.
                            portfolio_value = self.risk_manager.portfolio_value if (
                                self.risk_manager and hasattr(self.risk_manager, 'portfolio_value')
                            ) else self.config.initial_capital
                            dollar_amount = position_size_pct * portfolio_value
                            quantity = dollar_amount / current_price
                            quantity = max(1.0, float(quantity))
                            logger.debug(f"   💰 Fallback sizing: {position_size_pct:.2%} of ${portfolio_value:,.0f} = {quantity} shares @ ${current_price:.2f}")
                        return quantity

                    # ==============================================================
                    # LONG_ENTRY / BUY: Open long position
                    # ==============================================================
                    if signal_type_lower in ['long_entry', 'buy']:
                        if has_short:
                            # First close the short, then open long
                            side = 'buy'
                            quantity = abs(float(current_position))  # Cover short first
                            logger.debug(f"   🔄 Covering short position: {quantity} shares")
                            # Note: Next iteration should open long
                        elif not has_long:
                            # Open new long position
                            side = 'buy'
                            calculate_entry_quantity()
                            logger.debug(f"   📈 Opening LONG: {quantity} shares")
                        else:
                            # Already have long, skip
                            logger.debug(f"   ⏭️  Skipping LONG_ENTRY for {symbol}: already have long position")
                            continue

                    # ==============================================================
                    # LONG_EXIT / CLOSE_LONG: Close long position
                    # ==============================================================
                    elif signal_type_lower in ['long_exit', 'close_long']:
                        if has_long:
                            side = 'sell'
                            quantity = abs(float(current_position))
                            logger.debug(f"   📉 Closing LONG: {quantity} shares")
                        else:
                            logger.debug(f"   ⏭️  Skipping LONG_EXIT for {symbol}: no long position to close")
                            continue

                    # ==============================================================
                    # SHORT_ENTRY: Open short position OR close long (if shorts disabled)
                    # ==============================================================
                    elif signal_type_lower in ['short_entry', 'short']:
                        if has_long:
                            # Close the long position first (or instead of shorting)
                            side = 'sell'
                            quantity = abs(float(current_position))
                            logger.debug(f"   📉 Closing LONG (from SHORT_ENTRY signal): {quantity} shares")
                            # Note: If shorts allowed, next iteration could open short
                        elif not has_short:
                            if getattr(self.config, 'allow_shorts', False):
                                # Open short position
                                side = 'sell'
                                calculate_entry_quantity()
                                logger.debug(f"   📉 Opening SHORT: {quantity} shares")
                            else:
                                logger.debug(f"   ⏭️  Skipping SHORT_ENTRY for {symbol}: shorts not allowed")
                                continue
                        else:
                            logger.debug(f"   ⏭️  Skipping SHORT_ENTRY for {symbol}: already have short position")
                            continue

                    # ==============================================================
                    # SHORT_EXIT / CLOSE_SHORT: Close short position
                    # ==============================================================
                    elif signal_type_lower in ['short_exit', 'close_short', 'cover']:
                        if has_short:
                            side = 'buy'
                            quantity = abs(float(current_position))
                            logger.debug(f"   📈 Closing SHORT (covering): {quantity} shares")
                        else:
                            logger.debug(f"   ⏭️  Skipping SHORT_EXIT for {symbol}: no short position to cover")
                            continue

                    # Legacy SELL: close long or open short
                    elif signal_type_lower == 'sell':
                        if has_long:
                            # Close long position
                            side = 'sell'
                            quantity = abs(float(current_position))
                            logger.debug(f"   📉 Closing LONG (from legacy SELL): {quantity} shares")
                        elif not has_short:
                            if getattr(self.config, 'allow_shorts', False):
                                side = 'sell'
                                calculate_entry_quantity()
                                logger.debug(f"   📉 Opening SHORT (from legacy SELL): {quantity} shares")
                            else:
                                logger.debug(f"   ⏭️  Skipping SELL for {symbol}: no position to close and shorts not allowed")
                                continue
                        else:
                            continue

                    # ==============================================================
                    # CLOSE: Close any position
                    # ==============================================================
                    elif signal_type_lower in ['close', 'flatten']:
                        if has_long:
                            side = 'sell'
                            quantity = abs(float(current_position))
                            logger.debug(f"   📉 Closing LONG (from CLOSE): {quantity} shares")
                        elif has_short:
                            side = 'buy'
                            quantity = abs(float(current_position))
                            logger.debug(f"   📈 Closing SHORT (from CLOSE): {quantity} shares")
                        else:
                            logger.debug(f"   ⏭️  Skipping CLOSE for {symbol}: no position to close")
                            continue

                    else:
                        logger.debug(f"   ⚠️  Unknown signal type: {signal_type_lower}")
                        continue

                    # Validate we have a valid trade
                    if side is None or quantity <= 0:
                        continue

                    # Pre-authorization per-bar cash budget check
                    # Reject BUY signals that would exceed remaining bar budget.
                    if side == 'buy' and current_price > 0:
                        trade_cost_est = quantity * current_price
                        remaining_cash = _available_cash_at_bar - _bar_cash_committed
                        if remaining_cash < trade_cost_est:
                            # Try to size down to remaining cash
                            if remaining_cash > current_price:
                                quantity = max(1.0, remaining_cash / current_price)
                                logger.debug(
                                    f"   ⚠️ C3: Reduced {symbol} BUY qty to {quantity:.0f} "
                                    f"(bar cash budget: ${remaining_cash:,.0f})"
                                )
                            else:
                                logger.debug(
                                    f"   ⛔ C3: Skipping {symbol} BUY — bar cash budget "
                                    f"exhausted (${remaining_cash:,.0f} < ${trade_cost_est:,.0f})"
                                )
                                continue

                    # Request authorization from CentralRiskManager (BRICK #8)
                    if self.risk_manager:
                        # C1: Determine if signal is an exit (skips sizing scale-down)
                        is_exit_signal = signal_type_lower in exit_signals

                        # 6-gate authorization pipeline

                        # Extract bar volume/volatility for Gate 6 cost model alignment
                        _bar_vol = 0.0
                        _bar_volatility = self.DEFAULT_VOLATILITY
                        try:
                            if 'filtered_data' in dir() and filtered_data is not None and len(filtered_data) > 0:
                                _last_bar = filtered_data.iloc[-1]
                                _bar_vol = float(_last_bar.get('volume', 0)) if hasattr(_last_bar, 'get') else float(getattr(_last_bar, 'volume', 0))
                                _bar_volatility = float(_last_bar.get('volatility', self.DEFAULT_VOLATILITY)) if hasattr(_last_bar, 'get') else float(getattr(_last_bar, 'volatility', self.DEFAULT_VOLATILITY))
                            elif hasattr(signal_row, 'get'):
                                _bar_vol = float(signal_row.get('volume', 0))
                                _bar_volatility = float(signal_row.get('volatility', self.DEFAULT_VOLATILITY))
                        except Exception:
                            pass

                        # Available cash with intra-bar commitment tracking
                        _real_cash = (
                            float(self.risk_manager._position_book.get_cash_balance())
                            if getattr(self.risk_manager, '_position_book', None)
                            else getattr(self.risk_manager, 'available_cash',
                                         self.risk_manager.portfolio_value * 0.95)
                        )
                        _signal_available_cash = max(0.0, _real_cash - _bar_cash_committed)

                        _6gate_signal = {
                            'symbol': symbol,
                            'side': side,
                            'requested_quantity': quantity,
                            'signal_strength': signal_strength,
                            'confidence': confidence,
                            'expected_return': expected_return,
                            'strategy_id': signal_row.get('strategy_id', 'backtest_strategy'),
                            'signal_timestamp': timestamp,
                            'arrival_price': current_price,
                            'stop_loss_pct': 0.02,
                            # Signal metadata
                            'is_exit': is_exit_signal,
                            'signal_type': signal_type,
                            'target_weight': target_weight,
                            'quantity_type': quantity_type,
                            'available_cash': _signal_available_cash,
                            'original_signal_metadata': {
                                'strength': signal_strength,
                                'expected_return': expected_return,
                                'target_weight': target_weight,
                                'signal_type': signal_type,
                            },
                            # Gate 6 cost model inputs (aligned with execution simulator)
                            'bar_volume': _bar_vol,
                            'bar_volatility': _bar_volatility,
                        }
                        _6gate_result = await self.risk_manager.authorize_signal_6gate(
                            signal=_6gate_signal,
                            current_price=current_price,
                            portfolio_value=self.risk_manager.portfolio_value,
                        )
                        # Adapt 6-gate result to authorization interface
                        from core_engine.system.central_risk_manager import AuthorizationLevel
                        class _6GateAuth:
                            pass
                        authorization = _6GateAuth()
                        authorization.authorization_level = (
                            AuthorizationLevel.AUTOMATIC if _6gate_result.get('authorized', False)
                            else AuthorizationLevel.REJECTED
                        )
                        authorization.authorized_quantity = _6gate_result.get('authorized_quantity', 0.0)
                        authorization.authorization_id = f"6gate_{symbol}_{self.current_bar_index}"
                        authorization.rejection_reason = _6gate_result.get('rejection_reason', '')
                        authorization.gate_diagnostics = _6gate_result.get('gates', {})

                        # Check if authorized
                        from core_engine.system.central_risk_manager import AuthorizationLevel
                        if authorization.authorization_level != AuthorizationLevel.REJECTED:
                            auth_qty = authorization.authorized_quantity
                            # Authorized: add to list for next-bar execution
                            authorized_trades.append({
                                'strategy_id': signal_row.get('strategy_id', 'backtest_strategy'),
                                'symbol': symbol,
                                'side': side,
                                'quantity': auth_qty,
                                'confidence': confidence,
                                'signal_strength': signal_strength,
                                'signal_type': signal_type,
                                'authorization': authorization,
                                'timestamp': timestamp,
                                'current_price': current_price,
                                'additional_data': signal_row.get('additional_data', {}),
                            })
                            # Debit per-bar cash budget for BUY
                            if side == 'buy' and current_price > 0:
                                _bar_cash_committed += auth_qty * current_price
                        else:
                            # Log rejected trades for diagnostics (was silently dropped)
                            logger.debug(
                                f"⛔ Trade REJECTED: {symbol} {side} "
                                f"qty={authorization.authorized_quantity:.2f} "
                                f"reason={getattr(authorization, 'rejection_reason', 'N/A')}"
                            )
                else:
                    continue

        except Exception as e:
            logger.error(f"❌ Error getting authorized trades: {e}")

        return authorized_trades

    def _prepare_signal_rows_fast(self, signals_df: pd.DataFrame) -> List[Any]:
        """Materialize signal rows as (index, row_dict) pairs for lower-overhead iteration."""
        if signals_df is None or signals_df.empty:
            return []

        indices = signals_df.index.tolist()
        records = signals_df.to_dict('records')
        return list(zip(indices, records))

    def _prepare_historical_rows_fast(self, historical_df: pd.DataFrame) -> List[Any]:
        """Materialize historical bars as (index, row_dict) pairs for lower-overhead iteration."""
        if historical_df is None or historical_df.empty:
            return []

        indices = historical_df.index.tolist()
        records = historical_df.to_dict('records')
        return list(zip(indices, records))

    def _get_cached_timestamp_series(self, cache_key: str, df: pd.DataFrame):
        """Return cached pd.to_datetime(df['timestamp']) for stable DataFrames in hot loops.

        Uses ``id(df)`` (object identity) as the primary freshness key so that
        pre-calculated DataFrames that never change across bars hit the cache
        every time, instead of the old ``len(df)`` check which invalidated on
        every growing-window slice.
        """
        if df is None or df.empty or 'timestamp' not in df.columns:
            return pd.Series(dtype='datetime64[ns]')

        if not self._use_fast_timestamp_cache:
            return pd.to_datetime(df['timestamp'])

        df_id = id(df)
        cached = self._timestamp_series_cache.get(cache_key)
        if cached is not None and cached.get('df_id') == df_id:
            return cached['series']

        series = pd.to_datetime(df['timestamp'])
        self._timestamp_series_cache[cache_key] = {
            'df_id': df_id,
            'series': series,
        }
        return series

    def _align_timestamp_to_index_tz(
        self,
        base_ts: pd.Timestamp,
        index_tz,
        cache: Optional[Dict[Any, pd.Timestamp]] = None,
    ) -> pd.Timestamp:
        """Align a timestamp to index timezone semantics with optional per-bar cache."""
        if cache is not None:
            key = index_tz if index_tz is not None else "__naive__"
            cached = cache.get(key)
            if cached is not None:
                return cached

        ts_cmp = pd.Timestamp(base_ts)
        if index_tz is not None and ts_cmp.tz is None:
            ts_cmp = ts_cmp.tz_localize(index_tz)
        elif index_tz is None and ts_cmp.tz is not None:
            ts_cmp = ts_cmp.tz_localize(None)

        if cache is not None:
            key = index_tz if index_tz is not None else "__naive__"
            cache[key] = ts_cmp

        return ts_cmp

    def _bar_to_dict(self, bar: Any) -> Dict[str, Any]:
        """Convert a bar row (Series or mapping) into a plain dict."""
        if hasattr(bar, 'to_dict'):
            return bar.to_dict()
        if isinstance(bar, dict):
            return dict(bar)
        try:
            return dict(bar)
        except Exception:
            return {}

    @staticmethod
    def _downsample_with_peaks(history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """C6 FIX: Downsample position_history by 50% while retaining peak
        equity and trough drawdown snapshots for faithful curve reconstruction.

        Algorithm:
        1. Mark the global equity-peak and drawdown-trough indices.
        2. Keep every-other entry (base downsample).
        3. Force-include any marked peak/trough that was about to be dropped.
        """
        if len(history) < 4:
            return history

        # Identify peak-equity and trough-drawdown indices
        peak_idx = 0
        trough_idx = 0
        peak_equity = -float('inf')
        worst_dd = float('inf')

        for i, snap in enumerate(history):
            eq = snap.get('equity', 0)
            dd = snap.get('max_drawdown_pct', 0)
            if eq > peak_equity:
                peak_equity = eq
                peak_idx = i
            if dd < worst_dd:
                worst_dd = dd
                trough_idx = i

        # Base downsample: keep every-other + always keep first and last
        keep_set = {0, len(history) - 1, peak_idx, trough_idx}
        for i in range(0, len(history), 2):
            keep_set.add(i)

        return [history[i] for i in sorted(keep_set)]

    def _get_precalc_bar_iloc_fast(
        self,
        cache_key: str,
        df: pd.DataFrame,
        bar_timestamp: pd.Timestamp,
    ) -> Optional[int]:
        """Resolve exact bar iloc via cached searchsorted when timestamp column is monotonic.

        Uses ``id(df)`` for cache freshness (same fix as _get_cached_timestamp_series)
        so that pre-calculated DataFrames that stay constant across bars always hit the cache.
        """
        if not self._use_fast_precalc_bar_lookup:
            return None
        if df is None or df.empty or 'timestamp' not in df.columns:
            return None

        df_id = id(df)
        cache = self._precalc_bar_lookup_cache.get(cache_key)
        if cache is None or cache.get('df_id') != df_id:
            ts_series = self._get_cached_timestamp_series(cache_key, df)
            idx_obj = pd.DatetimeIndex(ts_series)
            if not getattr(idx_obj, 'is_monotonic_increasing', False):
                self._precalc_bar_lookup_cache[cache_key] = {
                    'df_id': df_id,
                    'disabled': True,
                }
                return None
            cache = {
                'df_id': df_id,
                'idx_obj': idx_obj,
                'idx_tz': getattr(idx_obj, 'tz', None),
            }
            self._precalc_bar_lookup_cache[cache_key] = cache

        if cache.get('disabled', False):
            return None

        ts_cmp = self._align_timestamp_to_index_tz(
            pd.Timestamp(bar_timestamp),
            cache.get('idx_tz'),
            cache=None,
        )
        idx_obj = cache['idx_obj']
        pos = int(idx_obj.searchsorted(ts_cmp, side='left'))
        if 0 <= pos < len(idx_obj) and idx_obj[pos] == ts_cmp:
            return pos
        return None

    def _slice_df_before_timestamp_fast(
        self,
        cache_key: str,
        df: pd.DataFrame,
        bar_timestamp: pd.Timestamp,
        tz_align_cache: Optional[Dict[Any, pd.Timestamp]] = None,
    ) -> Optional[pd.DataFrame]:
        """Return df rows strictly before timestamp via cached searchsorted; None means fallback."""
        if not self._use_fast_symbol_time_slice:
            return None
        if df is None or df.empty or 'timestamp' not in df.columns:
            return None

        df_id = id(df)
        cache = self._time_slice_cache.get(cache_key)
        if cache is None or cache.get('df_id') != df_id:
            ts_series = self._get_cached_timestamp_series(cache_key, df)
            idx_obj = pd.DatetimeIndex(ts_series)
            if not getattr(idx_obj, 'is_monotonic_increasing', False):
                self._time_slice_cache[cache_key] = {
                    'df_id': df_id,
                    'disabled': True,
                }
                return None
            cache = {
                'df_id': df_id,
                'idx_obj': idx_obj,
                'idx_tz': getattr(idx_obj, 'tz', None),
            }
            self._time_slice_cache[cache_key] = cache

        if cache.get('disabled', False):
            return None

        ts_cmp = self._align_timestamp_to_index_tz(
            pd.Timestamp(bar_timestamp),
            cache.get('idx_tz'),
            cache=tz_align_cache,
        )
        idx_obj = cache['idx_obj']
        cut = int(idx_obj.searchsorted(ts_cmp, side='left'))
        return df.iloc[:cut].copy()

    def _get_market_data_time_indexed(
        self,
        cache_key: str,
        df: pd.DataFrame,
    ) -> Optional[pd.DataFrame]:
        """Return timestamp-indexed market data with optional cache for repeated lookups."""
        if df is None or df.empty:
            return None
        if isinstance(df.index, pd.DatetimeIndex):
            return df
        if 'timestamp' not in df.columns:
            return None
        if not self._use_fast_market_data_index_cache:
            return df.set_index('timestamp')

        df_id = id(df)
        cached = self._market_data_index_cache.get(cache_key)
        if cached is not None and cached.get('df_id') == df_id:
            return cached['df']

        idx_df = df.set_index('timestamp')
        self._market_data_index_cache[cache_key] = {
            'df_id': df_id,
            'df': idx_df,
        }
        return idx_df

    def _slice_precalc_indexed_before_timestamp_fast(
        self,
        cache_key: str,
        df: pd.DataFrame,
        bar_timestamp: pd.Timestamp,
        tz_align_cache: Optional[Dict[Any, pd.Timestamp]] = None,
    ) -> Optional[pd.DataFrame]:
        """Return pre-calculated indicator rows before timestamp from cached timestamp-indexed view."""
        if not self._use_fast_precalc_indexed_slice:
            return None
        if df is None or df.empty or 'timestamp' not in df.columns:
            return None

        df_id = id(df)
        cache = self._precalc_indexed_slice_cache.get(cache_key)
        if cache is None or cache.get('df_id') != df_id:
            ts_series = self._get_cached_timestamp_series(cache_key, df)
            idx_obj = pd.DatetimeIndex(ts_series)
            if not getattr(idx_obj, 'is_monotonic_increasing', False):
                self._precalc_indexed_slice_cache[cache_key] = {
                    'df_id': df_id,
                    'disabled': True,
                }
                return None
            indexed_df = df.set_index('timestamp')
            cache = {
                'df_id': df_id,
                'idx_obj': idx_obj,
                'idx_tz': getattr(idx_obj, 'tz', None),
                'indexed_df': indexed_df,
            }
            self._precalc_indexed_slice_cache[cache_key] = cache

        if cache.get('disabled', False):
            return None

        ts_cmp = self._align_timestamp_to_index_tz(
            pd.Timestamp(bar_timestamp),
            cache.get('idx_tz'),
            cache=tz_align_cache,
        )
        idx_obj = cache['idx_obj']
        cut = int(idx_obj.searchsorted(ts_cmp, side='left'))
        return cache['indexed_df'].iloc[:cut].copy()

    # ============================================================
    # EXECUTION FLOW METHODS
    # ============================================================

    async def _execute_pending_signals(self,
                                       pending_signals: List[Dict[str, Any]],
                                       current_bar: pd.Series,
                                       bar_timestamp: datetime,
                                       execution_price: float) -> List[Dict[str, Any]]:
        """
        Execute pending signals from previous bar at current bar's OPEN price.

        CRITICAL FIX: This eliminates look-ahead bias by ensuring signals
        generated at bar N are executed at bar N+1's OPEN price, not bar N's
        close price.

        Real-world analogy:
        - At bar N close, you see the price and decide to trade
        - You submit an order (takes time)
        - Order fills at bar N+1 open (earliest realistic execution)

        Args:
            pending_signals: Signals queued from previous bar
            current_bar: Current bar data (used for OPEN price)
            bar_timestamp: Current bar timestamp
            execution_price: Price to use for execution (typically current bar's OPEN)

        Returns:
            List of executed trades
        """
        if not pending_signals:
            return []

        executed_trades = []

        try:
            # Modify each pending signal to use the OPEN price instead of close
            for signal in pending_signals:
                # Override the execution price with current bar's OPEN
                signal['execution_price'] = execution_price
                signal['execution_timestamp'] = bar_timestamp
                signal['execution_bar_index'] = self.current_bar_index

            # Use existing simulate_execution but with modified price
            executed_trades = await self.simulate_execution(
                pending_signals,
                current_bar,
                bar_timestamp,
                override_price=execution_price  # Pass the OPEN price
            )

        except Exception as e:
            logger.error(f"❌ Error executing pending signals: {e}")

        return executed_trades

    def _get_symbol_close_at_timestamp(
        self,
        symbol: str,
        timestamp,
        fallback: float = 0.0,
    ) -> float:
        """Get the close price for *symbol* at or before *timestamp*.

        Tries:
          1. Fast cached path via ``_get_latest_close_price_fast``
          2. Manual DataFrame filter with timezone alignment
          3. Last available close in market_data
          4. *fallback*

        Used by _check_eod_liquidation, _force_close_open_positions,
        and _get_authorized_trades_for_bar to avoid duplicating 20+ lines
        of timezone-aware price lookup logic.
        """
        if symbol not in self.market_data or self.market_data[symbol].empty:
            return fallback

        sym_df = self.market_data[symbol]
        bar_ts = pd.Timestamp(timestamp)

        # Fast path (session_management mixin)
        fast_price = self._get_latest_close_price_fast(symbol, sym_df, bar_ts)
        if fast_price is not None:
            return fast_price

        # Slow path: timezone-align and filter
        sym_indexed = self._get_market_data_time_indexed(
            f"price_lookup::{symbol}", sym_df,
        )
        if sym_indexed is None:
            sym_indexed = sym_df

        ts_cmp = bar_ts
        idx_tz = getattr(sym_indexed.index, 'tz', None)
        ts_tz = getattr(ts_cmp, 'tz', None) or getattr(ts_cmp, 'tzinfo', None)
        if idx_tz is not None and ts_tz is None:
            ts_cmp = ts_cmp.tz_localize(idx_tz)
        elif idx_tz is None and ts_tz is not None:
            ts_cmp = ts_cmp.tz_localize(None)

        filtered = sym_indexed[sym_indexed.index <= ts_cmp]
        if len(filtered) > 0:
            close_col = 'close' if 'close' in filtered.columns else 'Close'
            if close_col in filtered.columns:
                return float(filtered[close_col].iloc[-1])

        # Ultimate fallback: last available close
        close_col = 'close' if 'close' in sym_df.columns else 'Close'
        if close_col in sym_df.columns and not sym_df.empty:
            return float(sym_df[close_col].iloc[-1])

        return fallback

    def _build_execution_dict(
        self,
        *,
        timestamp,
        symbol: str,
        side: str,
        quantity: float,
        decision_price: float,
        market_price: float,
        fill_price: float,
        strategy_id: str = "EOD_LIQUIDATION",
        authorization_id: str = "",
        fill_id: str = "",
        confidence: float = 1.0,
        signal_strength: float = 0.0,
        total_cost_bps: float = 0.0,
        spread_cost_bps: float = 0.0,
        market_impact_bps: float = 0.0,
        slippage_bps: float = 0.0,
        commission_bps: float = 0.0,
        total_cost_dollars: float = 0.0,
        permanent_impact_bps: float = 0.0,
        temporary_impact_bps: float = 0.0,
        implementation_shortfall_bps: float = 0.0,
        arrival_cost_bps: float = 0.0,
        regime: str = "eod_close",
        liquidity_score: float = None,
    ) -> dict:
        """Build a standard execution record dict from plain values.

        Used by _check_eod_liquidation and _force_close_open_positions
        to avoid duplicating the 30+ field execution dict structure.
        """
        return {
            'timestamp': timestamp,
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'requested_quantity': quantity,
            'quantity_reduction': 0,
            'decision_price': decision_price,
            'market_price': market_price,
            'fill_price': fill_price,
            'confidence': confidence,
            'signal_strength': signal_strength,
            'signal_timestamp': timestamp,
            'signal_bar_close': decision_price,
            'execution_delay_bars': 0,
            'total_cost_bps': total_cost_bps,
            'spread_cost_bps': spread_cost_bps,
            'market_impact_bps': market_impact_bps,
            'slippage_bps': slippage_bps,
            'commission_bps': commission_bps,
            'total_cost_dollars': total_cost_dollars,
            'permanent_impact_bps': permanent_impact_bps,
            'temporary_impact_bps': temporary_impact_bps,
            'implementation_shortfall_bps': implementation_shortfall_bps,
            'arrival_cost_bps': arrival_cost_bps,
            'realized_pnl': 0.0,
            'retry_count': 0,
            'had_rejections': False,
            'rejection_count': 0,
            'authorization_id': authorization_id,
            'strategy_id': strategy_id,
            'strategy_run': strategy_id,
            'fill_id': fill_id,
            'regime': regime,
            'liquidity_score': liquidity_score if liquidity_score is not None else self.DEFAULT_LIQUIDITY_SCORE,
        }

    def _build_executed_trade_record(
        self,
        bar_timestamp,
        symbol: str,
        side: str,
        quantity: float,
        actual_quantity: float,
        simulated_fill,
        execution_result: dict,
        auth_trade: dict,
        position_update: dict,
    ) -> dict:
        """Build the executed trade record dict from fill + authorization data."""
        return {
            'timestamp': bar_timestamp,
            'symbol': symbol,
            'side': side,
            'quantity': actual_quantity,
            'requested_quantity': quantity,
            'quantity_reduction': quantity - actual_quantity if actual_quantity < quantity else 0,
            'decision_price': simulated_fill.decision_price,
            'market_price': simulated_fill.market_price,
            'fill_price': simulated_fill.fill_price,
            # Signal quality metrics
            'confidence': auth_trade.get('confidence', 0.0),
            'signal_strength': auth_trade.get('signal_strength', auth_trade.get('strength', 0)),
            # Next-bar execution tracking
            'signal_timestamp': auth_trade.get('signal_timestamp', bar_timestamp),
            'signal_bar_close': auth_trade.get('signal_bar_close', simulated_fill.decision_price),
            'execution_delay_bars': 1 if auth_trade.get('signal_bar_index') is not None else 0,
            # Cost breakdown
            'total_cost_bps': simulated_fill.costs.total_cost_bps,
            'spread_cost_bps': simulated_fill.costs.spread_cost_bps,
            'market_impact_bps': simulated_fill.costs.market_impact_bps,
            'slippage_bps': simulated_fill.costs.slippage_bps,
            'commission_bps': simulated_fill.costs.commission_bps,
            'total_cost_dollars': simulated_fill.costs.total_cost_dollars,
            # Impact breakdown
            'permanent_impact_bps': simulated_fill.costs.permanent_impact_bps,
            'temporary_impact_bps': simulated_fill.costs.temporary_impact_bps,
            # Fill quality
            'implementation_shortfall_bps': simulated_fill.implementation_shortfall_bps,
            'arrival_cost_bps': simulated_fill.arrival_cost_bps,
            # P&L from CentralRiskManager (Rule 4)
            'realized_pnl': position_update.get('realized_pnl', 0.0),
            # Rejection handling
            'retry_count': execution_result['retry_count'],
            'had_rejections': len(execution_result['rejection_history']) > 0,
            'rejection_count': len(execution_result['rejection_history']),
            # Metadata
            'authorization_id': getattr(auth_trade.get('authorization', {}), 'authorization_id', ''),
            'strategy_id': auth_trade.get('strategy_id', 'backtest_strategy'),
            'strategy_run': auth_trade.get('strategy_id', 'backtest_strategy'),
            'fill_id': simulated_fill.fill_id,
            'regime': simulated_fill.costs.regime,
            'liquidity_score': simulated_fill.costs.liquidity_score,
        }

    def _emit_cp4_cp5_trace(
        self,
        *,
        method: str,
        trace_id: str,
        symbol: str,
        bar_timestamp,
        side: str,
        quantity: float,
        decision_price: float,
        fill_price: float,
        strategy_id: str = "",
        authorization_id: str = "",
        market_price: float = None,
        execution_price: float = None,
        cp4_output: dict = None,
        cp4_metadata: dict = None,
        cp5_output: dict = None,
        cp5_metadata: dict = None,
        cp4_extra_input: dict = None,
    ) -> None:
        """Emit CP4 (order create) and CP5 (fill) pipeline trace checkpoints.

        Shared by simulate_execution, _check_eod_liquidation, and
        _force_close_open_positions.  Lazily imports the tracer so this
        is zero-cost when tracing is disabled.
        """
        try:
            from core_engine.utils.pipeline_trace import (
                get_tracer, CP4_ORDER_CREATE, CP5_FILL,
            )
            tracer = get_tracer()
            if not tracer.enabled:
                return

            _mp = market_price if market_price is not None else decision_price
            _ep = execution_price if execution_price is not None else fill_price
            _ts = str(bar_timestamp)

            # CP4: Order Creation
            cp4_input = {
                "authorization_id": authorization_id,
                "symbol": symbol,
                "side": side,
                "quantity": float(quantity),
                "decision_price": float(decision_price),
                "execution_price": float(_ep),
                "strategy_id": strategy_id,
            }
            if cp4_extra_input:
                cp4_input.update(cp4_extra_input)
            tracer.emit(
                trace_id=trace_id,
                checkpoint=CP4_ORDER_CREATE,
                component="InstitutionalBacktestEngine",
                method=method,
                symbol=symbol,
                bar_timestamp=_ts,
                input_data=cp4_input,
                output_data=cp4_output or {"success": True},
                metadata=cp4_metadata or {},
            )

            # CP5: Fill
            cp5_input = {
                "fill_id": trace_id,
                "symbol": symbol,
                "side": side,
                "quantity": float(quantity),
                "decision_price": float(decision_price),
                "market_price": float(_mp),
                "price": float(fill_price),
                "fill_price": float(fill_price),
                "success": True,
            }
            tracer.emit(
                trace_id=trace_id,
                checkpoint=CP5_FILL,
                component="InstitutionalBacktestEngine",
                method=method,
                symbol=symbol,
                bar_timestamp=_ts,
                input_data=cp5_input,
                output_data=cp5_output or {},
                metadata=cp5_metadata or {},
            )
        except Exception:
            pass  # Tracing must never break the hot loop

    async def simulate_execution(self,
                                 authorized_trades: List[Any],
                                 current_bar: pd.Series,
                                 bar_timestamp: datetime,
                                 override_price: float = None) -> List[Dict[str, Any]]:
        """
        Simulate realistic trade execution using HistoricalExecutionSimulator

        This method bridges the gap between risk-authorized trades and
        simulated execution with realistic transaction costs.

        Flow:
            1. Take authorized trades from CentralRiskManager
            2. Get regime context and liquidity scores
            3. Call HistoricalExecutionSimulator for each trade
            4. Apply realistic costs (spread + impact + slippage)
            5. Update positions via PositionTracker
            6. Record executed trades with full cost breakdown

        Args:
            authorized_trades: List of authorized trades from CentralRiskManager
            current_bar: Current market data bar
            bar_timestamp: Timestamp of current bar
            override_price: If provided, use this price instead of bar's close (for next-bar execution)

        Returns:
            List of executed trades with cost breakdown
        """

        if not authorized_trades:
            return []

        try:
            # Verify execution simulator is available (created in Phase 5)
            if not hasattr(self, 'execution_simulator') or self.execution_simulator is None:
                raise RuntimeError(
                    "execution_simulator not initialized — did Phase 5 complete? "
                    "(P1-4: eager init should have created it)"
                )

            # P4: Initialize OMS for path parity when enabled
            if getattr(self.config, 'use_oms', False) and self.order_management_system is None:
                from core_engine.system.order_management_system import OrderManagementSystem
                self.order_management_system = OrderManagementSystem(config={})
                logger.info("📋 OMS enabled for backtest path parity")

            executed_trades = []

            # Execute SELLs before BUYs to free cash first
            # Without this, BUYs may be rejected for insufficient cash even
            # though pending SELLs would have provided the funds.
            authorized_trades = sorted(
                authorized_trades,
                key=lambda t: 0 if t.get('side', '').lower() == 'sell' else 1
            )

            execution_symbol_bar_cache = {} if self._use_fast_execution_symbol_bar_cache else None
            cached_cp45_tracer = None
            cached_cp45_enabled = False
            cached_cp4 = None
            cached_cp5 = None
            if self._use_fast_trace_context_cache:
                from core_engine.utils.pipeline_trace import get_tracer, CP4_ORDER_CREATE, CP5_FILL
                cached_cp45_tracer = get_tracer()
                cached_cp45_enabled = bool(cached_cp45_tracer.enabled)
                cached_cp4 = CP4_ORDER_CREATE
                cached_cp5 = CP5_FILL

            for auth_trade in authorized_trades:
                try:
                    # Extract trade details from authorization dict
                    symbol = auth_trade['symbol']
                    side = auth_trade['side']
                    quantity = auth_trade['quantity']

                    # ========================================
                    # POSITION-AWARE EXECUTION VALIDATION
                    # ========================================
                    # Re-check position state at execution time (Rule 4 compliance)
                    # This prevents stale authorizations from executing incorrectly
                    if self.risk_manager:
                        current_position = self.risk_manager.current_positions.get(symbol, 0.0)
                        allow_shorts = getattr(self.config, 'allow_shorts', False)
                        eps_pos = self.EPSILON

                        if side.lower() == 'buy' and current_position > eps_pos:
                            # Already LONG - skip duplicate BUY
                            logger.info(f"⚠️  Skipping BUY {symbol}: already LONG ({current_position:.2f} shares)")
                            continue

                        elif side.lower() == 'sell':
                            if current_position <= eps_pos and not allow_shorts:
                                # No position to sell and shorts not allowed
                                logger.info(f"⚠️  Skipping SELL {symbol}: no position to close (shorts not allowed)")
                                continue
                            elif current_position > eps_pos:
                                # Cap sell quantity to actual position
                                if quantity > (current_position + eps_pos):
                                    logger.info(f"🔒 Adjusting SELL qty for {symbol}: {quantity} → {current_position:.2f}")
                                    quantity = current_position
                                    auth_trade['quantity'] = quantity

                    # Price priority: 1) override_price (next-bar OPEN)
                    #                 2) auth_trade['current_price'] (auth-time)
                    #                 3) current_bar['close'] (fallback)
                    if override_price is not None:
                        # Next-bar OPEN is the correct execution price
                        current_price = override_price
                        # Decision price = signal bar's close (for implementation shortfall calc)
                        decision_price = auth_trade.get('signal_bar_close', override_price)
                    elif 'current_price' in auth_trade and auth_trade['current_price'] is not None:
                        # Multi-symbol fallback: use authorization-time price
                        current_price = auth_trade['current_price']
                        decision_price = current_price
                    else:
                        current_price = current_bar.get('close', 0)
                        decision_price = current_price

                    # Get regime context (Rule 2 Regime-First)
                    regime_context = None
                    if self.regime_engine:
                        # Try to get regime context if method exists
                        if hasattr(self.regime_engine, 'get_current_regime_context'):
                            regime_context = self.regime_engine.get_current_regime_context()  # Not async!
                        elif hasattr(self.regime_engine, 'current_regime'):
                            # Fallback: use current_regime attribute if available
                            regime_context = self.regime_engine.current_regime

                    # Get liquidity score (Rule 7 Section B)
                    liquidity_score = None
                    if self.liquidity_engine and hasattr(self.liquidity_engine, 'assess_liquidity_score'):
                        try:
                            # Prepare market data dict for liquidity assessment
                            liquidity_market_data = {
                                'timestamp': bar_timestamp,
                                'close': current_price,  # Use current_price
                                'volume': current_bar.get('volume', 0),
                                'high': current_bar.get('high', current_price),
                                'low': current_bar.get('low', current_price)
                            }
                            liquidity_assessment = self.liquidity_engine.assess_liquidity_score(
                                symbol, liquidity_market_data, historical_data=None
                            )
                            liquidity_score = liquidity_assessment.overall_score if liquidity_assessment else None
                        except Exception:
                            logger.debug(f"Liquidity assessment failed for {symbol}, proceeding without")

                    # Resolve correct symbol bar for transaction cost modeling
                    if execution_symbol_bar_cache is not None and symbol in execution_symbol_bar_cache:
                        sym_bar = execution_symbol_bar_cache[symbol]
                    else:
                        sym_bar = self._resolve_symbol_bar(symbol, bar_timestamp, current_bar)
                        if execution_symbol_bar_cache is not None:
                            execution_symbol_bar_cache[symbol] = sym_bar
                    market_data = self._build_market_data_dict(sym_bar, bar_timestamp, current_price)

                    # SPRINT 0.3: Simulate fill with rejection handling (GAP 4-3)
                    # Prepare regime context dict
                    regime_dict = None
                    if regime_context:
                        if hasattr(regime_context, '__dict__'):
                            regime_dict = regime_context.__dict__
                        elif isinstance(regime_context, dict):
                            regime_dict = regime_context

                    # Use simulate_fill_with_rejection for realistic order rejection modeling
                    if quantity <= 0:
                        continue

                    _auth_id = getattr(auth_trade.get('authorization', {}), 'authorization_id', '')
                    _strategy_id = auth_trade.get('strategy_id', 'backtest_strategy')

                    execution_result = self.execution_simulator.simulate_fill_with_rejection(
                        symbol=symbol,
                        side=side.lower(),
                        quantity=quantity,
                        decision_price=decision_price,
                        market_data=market_data,
                        authorization_id=_auth_id,
                        strategy_id=_strategy_id,
                        regime_context=regime_dict,
                        liquidity_score=liquidity_score,
                        max_retries=3  # Allow up to 3 retries with modifications
                    )

                    # --- CP4: Pipeline Trace - Order Creation (backtest path) ---
                    if self._use_fast_trace_context_cache:
                        _cp45_tracer = cached_cp45_tracer
                        _cp45_enabled = cached_cp45_enabled
                        _cp4_checkpoint = cached_cp4
                        _cp5_checkpoint = cached_cp5
                    else:
                        from core_engine.utils.pipeline_trace import get_tracer, CP4_ORDER_CREATE, CP5_FILL
                        _cp45_tracer = get_tracer()
                        _cp45_enabled = bool(_cp45_tracer.enabled)
                        _cp4_checkpoint = CP4_ORDER_CREATE
                        _cp5_checkpoint = CP5_FILL

                    if _cp45_enabled:
                        _cp4_auth_obj = auth_trade.get('authorization')
                        _cp45_tracer.emit(
                            trace_id=_auth_id or f"order_{symbol}_{bar_timestamp}",
                            checkpoint=_cp4_checkpoint,
                            component="InstitutionalBacktestEngine",
                            method="simulate_execution",
                            symbol=symbol,
                            bar_timestamp=str(bar_timestamp),
                            input_data={
                                "authorization_id": _auth_id,
                                "symbol": symbol,
                                "side": side,
                                "quantity": float(quantity),
                                "decision_price": float(decision_price),
                                "execution_price": float(current_price),
                                "strategy_id": _strategy_id,
                                "authorized_quantity": float(getattr(_cp4_auth_obj, 'authorized_quantity', 0)) if _cp4_auth_obj else float(quantity),
                                "authorization_level": str(getattr(_cp4_auth_obj, 'authorization_level', '')) if _cp4_auth_obj else '',
                            },
                            output_data={
                                "success": execution_result['success'],
                                "retry_count": execution_result['retry_count'],
                                "rejection_count": len(execution_result['rejection_history']),
                                "final_quantity": float(execution_result.get('final_quantity', 0)),
                            },
                            metadata={
                                "regime": str(regime_dict.get('regime', 'unknown')) if regime_dict else "unknown",
                                "liquidity_score": float(liquidity_score) if liquidity_score is not None else None,
                            },
                        )

                    # Check if execution was successful
                    if not execution_result['success']:
                        # Order was rejected and retries exhausted
                        logger.warning(f"[FAIL] Order REJECTED after {execution_result['retry_count']} retries: {symbol} {side} {quantity}")
                        logger.warning(f"   Rejection history: {len(execution_result['rejection_history'])} rejections")
                        logger.warning(f"   Failure reason: {execution_result.get('failure_reason', 'Unknown')}")

                        # Track rejection stats
                        if not hasattr(self, 'rejection_stats'):
                            self.rejection_stats = {
                                'total_rejections': 0,
                                'rejected_trades': [],
                                'rejection_reasons': {}
                            }

                        self.rejection_stats['total_rejections'] += 1
                        self.rejection_stats['rejected_trades'].append({
                            'timestamp': bar_timestamp,
                            'symbol': symbol,
                            'side': side,
                            'quantity': quantity,
                            'rejection_history': execution_result['rejection_history'],
                            'failure_reason': execution_result.get('failure_reason')
                        })

                        # Count rejection reasons
                        for rejection in execution_result['rejection_history']:
                            reason = rejection['rejection_code']
                            self.rejection_stats['rejection_reasons'][reason] = \
                                self.rejection_stats['rejection_reasons'].get(reason, 0) + 1

                        continue  # Skip this trade and move to next

                    # Execution successful - extract fill
                    simulated_fill = execution_result['fill']
                    actual_quantity = execution_result['final_quantity']  # May be reduced from retries
                    if actual_quantity <= 0:
                        continue

                    # Log if quantity was reduced
                    if actual_quantity < quantity:
                        logger.info(f"[INFO] Quantity reduced during retry: {quantity} -> {actual_quantity} ({symbol})")

                    # P4: Route through OMS when enabled for path parity
                    if self.order_management_system is not None:
                        try:
                            _oms_order = await self.order_management_system.create_order(
                                authorization_id=_auth_id,
                                symbol=symbol,
                                side=side,
                                quantity=float(actual_quantity),
                                strategy_id=_strategy_id,
                            )
                            await self.order_management_system.submit_order(_oms_order.order_id)
                            await self.order_management_system.record_fill(
                                order_id=_oms_order.order_id,
                                fill_quantity=float(actual_quantity),
                                fill_price=float(simulated_fill.fill_price),
                                commission=float(simulated_fill.costs.total_cost_dollars),
                            )
                        except Exception as _oms_err:
                            logger.warning(f"OMS routing failed (non-fatal): {_oms_err}")

                    # --- CP5: Pipeline Trace - Fill (backtest path) ---
                    if _cp45_enabled:
                        _cp45_tracer.emit(
                            trace_id=simulated_fill.fill_id or _auth_id or f"fill_{symbol}_{bar_timestamp}",
                            checkpoint=_cp5_checkpoint,
                            component="InstitutionalBacktestEngine",
                            method="simulate_execution",
                            symbol=symbol,
                            bar_timestamp=str(bar_timestamp),
                            input_data={
                                "fill_id": simulated_fill.fill_id,
                                "symbol": symbol,
                                "side": side,
                                "quantity": float(actual_quantity),
                                "decision_price": float(simulated_fill.decision_price),
                                "market_price": float(simulated_fill.market_price),
                                "price": float(simulated_fill.fill_price),
                                "fill_price": float(simulated_fill.fill_price),
                                "success": execution_result['success'],
                                "final_quantity": float(execution_result.get('final_quantity', 0)),
                                "retry_count": execution_result['retry_count'],
                                "rejection_count": len(execution_result['rejection_history']),
                            },
                            output_data={
                                "total_cost_bps": float(simulated_fill.costs.total_cost_bps),
                                "spread_cost_bps": float(simulated_fill.costs.spread_cost_bps),
                                "market_impact_bps": float(simulated_fill.costs.market_impact_bps),
                                "slippage_bps": float(simulated_fill.costs.slippage_bps),
                                "commission_bps": float(simulated_fill.costs.commission_bps),
                                "total_cost_dollars": float(simulated_fill.costs.total_cost_dollars),
                                "implementation_shortfall_bps": float(simulated_fill.implementation_shortfall_bps),
                            },
                            metadata={
                                "arrival_cost_bps": float(simulated_fill.arrival_cost_bps),
                                "permanent_impact_bps": float(simulated_fill.costs.permanent_impact_bps),
                                "temporary_impact_bps": float(simulated_fill.costs.temporary_impact_bps),
                            },
                        )

                    # Update positions via CentralRiskManager
                    position_update = {}
                    if self.risk_manager:
                        try:
                            # H4: backtest_fill=True tells CRM that costs are already
                            # embedded in fill_price by HistoricalExecutionSimulator
                            # Build metadata with cost attribution from execution simulator
                            _fill_metadata = auth_trade.get('additional_data', {}) or {}
                            _fill_metadata['cost_attribution'] = {
                                'total_cost_bps': float(simulated_fill.costs.total_cost_bps),
                                'spread_cost_bps': float(simulated_fill.costs.spread_cost_bps),
                                'market_impact_bps': float(simulated_fill.costs.market_impact_bps),
                                'slippage_bps': float(simulated_fill.costs.slippage_bps),
                                'commission_bps': float(simulated_fill.costs.commission_bps),
                                'total_cost_dollars': float(simulated_fill.costs.total_cost_dollars),
                                'implementation_shortfall_bps': float(simulated_fill.implementation_shortfall_bps),
                                'decision_price': float(simulated_fill.decision_price),
                                'market_price': float(simulated_fill.market_price),
                                'fill_price': float(simulated_fill.fill_price),
                            }
                            position_update = await self.risk_manager.update_position(
                                symbol=symbol,
                                side=side,
                                quantity=actual_quantity,  # Use actual quantity (may be reduced)
                                price=simulated_fill.fill_price,  # Use fill price (includes costs)
                                timestamp=bar_timestamp,
                                strategy_id=auth_trade.get('strategy_id', ''),  # Carry over strategy attribution
                                metadata=_fill_metadata,
                                backtest_fill=True,
                            )
                            logger.debug(f"📈 Position updated via RiskManager (Rule 4): {position_update}")
                            # Skip recording if position update was rejected
                            if isinstance(position_update, dict) and not position_update.get('success', True):
                                logger.warning(
                                    f"⚠️ Position update rejected for {symbol}: "
                                    f"{position_update.get('error', 'unknown')} — skipping trade record"
                                )
                                continue
                        except Exception as e:
                            logger.error(f"❌ Position update failed for {symbol}: {e}")
                            position_update = {'realized_pnl': 0.0}
                            # Don't record phantom trades on exceptions
                            continue
                    else:
                        logger.warning(f"⚠️  No RiskManager available - position update skipped (violates Rule 4)")

                    # Build trade record
                    executed_trade = self._build_executed_trade_record(
                        bar_timestamp, symbol, side, quantity,
                        actual_quantity, simulated_fill, execution_result,
                        auth_trade, position_update,
                    )

                    executed_trades.append(executed_trade)

                    # Add to execution history
                    self.execution_history.append(executed_trade)

                    logger.info(f"✅ Trade executed and recorded: {symbol} {side} {quantity}")

                except Exception as e:
                    logger.error(f"❌ Failed to simulate execution for {auth_trade.get('symbol', 'unknown')}: {e}")
                    logger.error(f"   Trade details: {auth_trade}")
                    import traceback
                    logger.error(f"   Traceback: {traceback.format_exc()}")
                    continue

            if executed_trades:
                logger.info(f"✅ Simulated {len(executed_trades)} executions with realistic costs")

            return executed_trades

        except Exception as e:
            logger.error(f"❌ Execution simulation failed: {e}", exc_info=True)
            return []

    # ============================================================
    # Lifecycle Management
    # ============================================================

    async def shutdown(self) -> bool:
        """
        Graceful shutdown of backtest engine.

        C5 R3 FIX: Idempotent — safe to call multiple times.
        H6 R3 FIX: Per-component timeout prevents hangs.

        Returns:
            True if shutdown successful
        """
        # C5: Idempotency guard
        if not self.is_initialized and not self.is_running:
            logger.debug("Engine already shut down (idempotent no-op)")
            return True

        try:
            logger.info("\n🛑 Shutting down backtest engine...")

            # Stop all components with timeout (H6 R3 FIX)
            for component_name, component in self.components.items():
                try:
                    if hasattr(component, 'stop') and callable(getattr(component, 'stop', None)):
                        await asyncio.wait_for(component.stop(), timeout=5.0)
                        logger.info(f"   ✅ {component_name} stopped")
                except asyncio.TimeoutError:
                    logger.warning(f"   ⚠️ {component_name} shutdown timed out (5s)")
                except Exception as e:
                    logger.error(f"   ❌ Failed to stop {component_name}: {e}")

            # Clear references to help GC
            self.components.clear()
            self.component_ids.clear()
            self.is_running = False
            self.is_initialized = False

            # P1 F8: Reset singletons to prevent state leakage between backtest runs
            try:
                from core_engine.utils.pipeline_trace import PipelineTracer
                PipelineTracer.reset_instance()
                logger.debug("PipelineTracer singleton reset")
            except Exception as e:
                logger.debug("PipelineTracer reset skipped: %s", e)

            logger.info("✅ Shutdown complete\n")
            return True

        except Exception as e:
            logger.error(f"❌ Shutdown failed: {e}")
            self.is_running = False
            self.is_initialized = False
            return False

    # ============================================================
    # Status & Monitoring
    # ============================================================

    def get_status(self) -> Dict[str, Any]:
        """Get current engine status"""
        return {
            'backtest_name': self.backtest_name,
            # Guard against raw string enum (no .value attribute)
            'backtest_mode': self.backtest_mode.value if hasattr(self.backtest_mode, 'value') else str(self.backtest_mode),
            'is_initialized': self.is_initialized,
            'is_running': self.is_running,
            'components_registered': len(self.components),
            'current_bar': self.current_bar_index,
            'phase_status': {
                'phase2_data_regime': 'skeleton_only',
                'phase3_processing': 'not_started',
                'phase4_strategy_risk': 'not_started',
                'phase5_execution': 'not_started',
                'phase6_analytics': 'not_started',
                'phase7_integration': 'not_started'
            }
        }

    def __repr__(self) -> str:
        """String representation"""
        return (
            f"InstitutionalBacktestEngine(\n"
            f"  name='{self.backtest_name}',\n"
            f"  mode={self.backtest_mode.value},\n"
            f"  initialized={self.is_initialized},\n"
            f"  components={len(self.components)}\n"
            f")"
        )

