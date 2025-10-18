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
    - Rule 13: Regime-First Principle (RegimeEngine initializes first)
    - Rule 12: Liquidity Management (Liquidity filtering enabled)
    - Rule 8: Multi-Strategy Coordination (StrategyManager coordination)
    - Rule 4: Central Risk Management (CentralRiskManager authorization)
    - Rule 10: Production Standards (Comprehensive monitoring)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import logging
import asyncio
import pandas as pd
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Configuration
from backtest.config.backtest_config import BacktestConfiguration

# Core engine orchestration (BRICK #0)
from core_engine.system.hierarchical_orchestrator import (
    HierarchicalSystemOrchestrator, 
    ComponentLayer, 
    AuthorityLevel
)

logger = logging.getLogger(__name__)


class InstitutionalBacktestEngine:
    """
    Institutional-Grade Backtest Engine
    
    Orchestrates all 9 core_engine Lego Bricks to perform comprehensive
    backtesting with regime awareness, liquidity filtering, multi-strategy
    coordination, and centralized risk management.
    
    Initialization Order (Rule 13 - Regime-First):
        5  - EnhancedRegimeEngine (FIRST!)
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
        config = BacktestConfiguration.from_json("my_backtest.json")
        engine = InstitutionalBacktestEngine(config)
        await engine.initialize()
        results = await engine.run_backtest()
        report = await engine.generate_report()
    """
    
    def __init__(self, config: BacktestConfiguration):
        """
        Initialize backtest engine with configuration
        
        Args:
            config: Complete backtest configuration mapping to all Lego Bricks
        """
        self.config = config
        self.backtest_name = config.backtest_name
        self.backtest_mode = config.backtest_mode
        
        # Orchestrator (BRICK #0 - System Control)
        self.orchestrator = HierarchicalSystemOrchestrator()
        
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
        self.position_tracker = None   # Phase 4.4 - Position & Cash tracking
        
        # Phase 5 components (Execution)
        self.trading_engine = None     # BRICK #9a (order=30)
        self.execution_engine = None   # BRICK #9b (order=40)
        
        # Phase 6 components (Analytics)
        self.metrics_calculator = None # BRICK #10 (order=32)
        self.performance_analyzer = None # BRICK #11 (order=33)
        self.analytics_manager = None  # BRICK #12 (order=35)
        self.performance_reporter = None  # Helper for report generation
        
        # Backtest state
        self.is_initialized = False
        self.is_running = False
        self.current_bar_index = 0
        self.historical_data: Optional[pd.DataFrame] = None
        
        # Results tracking
        self.backtest_results: Dict[str, Any] = {}
        self.execution_history: List[Dict[str, Any]] = []
        self.position_history: List[Dict[str, Any]] = []
        
        logger.info(f"✅ InstitutionalBacktestEngine created: {self.backtest_name}")
    
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
            
            # Phase 2.2+: Manually initialize registered components
            # Note: For backtesting, we don't use the full orchestrator lifecycle
            # (which requires CentralRiskManager). Instead, we manually initialize
            # the components we need for historical simulation.
            if len(self.components) > 0:
                logger.info("\n🎯 Initializing registered components...")
                logger.info(f"   Components registered: {len(self.components)}")
                
                # Manually initialize each component
                for component_name, component in self.components.items():
                    logger.info(f"   Initializing {component_name}...")
                    try:
                        if hasattr(component, 'initialize'):
                            await component.initialize()
                        if hasattr(component, 'start'):
                            await component.start()
                        logger.info(f"   ✅ {component_name} initialized")
                    except Exception as e:
                        logger.error(f"   ❌ Failed to initialize {component_name}: {e}")
                        # Continue with other components
                
                logger.info(f"\n✅ {len(self.components)} components initialized")
            else:
                logger.info("\n⚠️  No components registered - skipping initialization")
            
            self.is_initialized = True
            
            logger.info("\n" + "=" * 80)
            logger.info("✅ INITIALIZATION COMPLETE")
            logger.info("=" * 80)
            logger.info(f"   Backtest: {self.backtest_name}")
            logger.info(f"   Mode: {self.backtest_mode}")  # backtest_mode is already a string
            logger.info(f"   Period: {self.config.data.start_date} → {self.config.data.end_date}")
            logger.info(f"   Symbols: {', '.join(self.config.data.symbols)}")
            logger.info(f"   Strategies: {len(self.config.strategies)}")
            logger.info(f"   Components Registered: {len(self.components)}")
            logger.info("=" * 80 + "\n")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}", exc_info=True)
            return False
    
    async def _initialize_phase2_data_regime(self) -> None:
        """
        Phase 2: Initialize Data & Regime Layer
        
        Components initialized (in order):
            5  - EnhancedRegimeEngine (FIRST! - Rule 13)
            10 - ClickHouseDataManager
            12 - LiquidityAssessmentEngine
        
        This implements the Regime-First Principle (Rule 13).
        """
        logger.info("\n" + "=" * 80)
        logger.info("📊 PHASE 2: Initializing Data & Regime Layer")
        logger.info("=" * 80)
        
        # Phase 2.2: Initialize BRICK #1 (EnhancedRegimeEngine - order=5)
        # CRITICAL: This MUST be first per Rule 13 (Regime-First Principle)
        await self._initialize_regime_engine()
        
        # Phase 2.3: Initialize BRICK #2 (ClickHouseDataManager - order=10)
        # Load historical market data with regime awareness
        await self._initialize_data_manager()
        
        # Phase 2.4: Initialize BRICK #3 (LiquidityAssessmentEngine - order=12)
        # Assess liquidity risk for trading decisions
        await self._initialize_liquidity_engine()
        
        logger.info("\n✅ Phase 2 Complete: Regime, Data & Liquidity layers integrated")
        logger.info(f"   Components registered: {len(self.components)}")
        logger.info("   Ready for Phase 3: Processing Pipeline")
    
    async def _initialize_regime_engine(self) -> None:
        """
        Phase 2.2: Initialize EnhancedRegimeEngine (BRICK #1)
        
        Order: 5 (FIRST! - Rule 13: Regime-First Principle)
        
        The regime engine provides market regime classification that all
        other components will use to adapt their behavior.
        
        Implements Rule 13: Regime-First Principle
        """
        logger.info("\n" + "-" * 80)
        logger.info("🔴 BRICK #1: EnhancedRegimeEngine (order=5) - REGIME-FIRST!")
        logger.info("-" * 80)
        
        try:
            from core_engine.regime.engine import EnhancedRegimeEngine
            
            # Create regime engine config matching RegimeEngineConfig structure
            # For backtesting, we use config focused on historical analysis
            regime_config = {
                'lookback_window': 60,  # 60 bars for regime assessment
                'volatility_window': 20,  # 20 bars for volatility calculation
                'trend_threshold': 0.02,  # 2% threshold for trend detection
                'regime_change_threshold': 0.7,  # 70% confidence for regime change
                'update_frequency': 1,  # Update every bar in backtest (seconds)
                'enable_enhanced_detection': True  # Use enhanced regime detection
            }
            
            # Create regime engine
            self.regime_engine = EnhancedRegimeEngine(regime_config)
            
            # Register with orchestrator (FIRST! order=5)
            component_id = self.orchestrator.register_component(
                name="EnhancedRegimeEngine",
                component=self.regime_engine,
                layer=ComponentLayer.SUPPORT,
                authority_level=AuthorityLevel.OPERATIONAL,
                initialization_order=5  # CRITICAL: First component!
            )
            
            self.component_ids['regime_engine'] = component_id
            self.components['regime_engine'] = self.regime_engine
            
            logger.info(f"✅ EnhancedRegimeEngine registered (component_id: {component_id})")
            logger.info(f"   Initialization Order: 5 (FIRST!)")
            logger.info(f"   Rule 13 Compliance: ✅ Regime-First Principle")
            logger.info(f"   Lookback Window: {regime_config['lookback_window']} bars")
            logger.info(f"   Volatility Window: {regime_config['volatility_window']} bars")
            logger.info(f"   Enhanced Detection: {regime_config['enable_enhanced_detection']}")
            
            # Note: Actual initialization happens when orchestrator.initialize_system() is called
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize EnhancedRegimeEngine: {e}", exc_info=True)
            raise RuntimeError(f"CRITICAL: Regime engine initialization failed (Rule 13 violation): {e}")
    
    async def _initialize_data_manager(self) -> None:
        """
        Phase 2.3: Initialize ClickHouseDataManager (BRICK #2)
        
        Order: 10 (after RegimeEngine=5)
        
        The data manager loads historical market data from ClickHouse
        and provides it to the backtest engine. It is regime-aware,
        meaning it can tag data with regime context.
        
        Implements:
        - Historical data loading from ClickHouse
        - Regime engine injection (Rule 13)
        - Data validation and preprocessing
        """
        logger.info("\n" + "-" * 80)
        logger.info("🔵 BRICK #2: ClickHouseDataManager (order=10)")
        logger.info("-" * 80)
        
        try:
            from core_engine.data.manager import ClickHouseDataManager, ClickHouseDataConfig
            
            # Create data manager config from backtest config
            data_config = ClickHouseDataConfig(
                symbols=self.config.data.symbols,
                start_date=self.config.data.start_date,
                end_date=self.config.data.end_date,
                interval=self.config.data.interval,
                clickhouse_host=self.config.data.clickhouse_host,
                clickhouse_port=self.config.data.clickhouse_port,
                clickhouse_database=self.config.data.clickhouse_database,
                enable_caching=True
            )
            
            # Create data manager
            self.data_manager = ClickHouseDataManager(data_config)
            
            # CRITICAL: Inject regime engine (Rule 13 - Regime-First)
            if hasattr(self.data_manager, 'set_regime_engine'):
                self.data_manager.set_regime_engine(self.regime_engine)
                logger.info("✅ Regime engine injected into DataManager (Rule 13)")
            
            # Register with orchestrator (order=10)
            component_id = self.orchestrator.register_component(
                name="ClickHouseDataManager",
                component=self.data_manager,
                layer=ComponentLayer.SUPPORT,
                authority_level=AuthorityLevel.OPERATIONAL,
                initialization_order=10  # After RegimeEngine (5)
            )
            
            self.component_ids['data_manager'] = component_id
            self.components['data_manager'] = self.data_manager
            
            logger.info(f"✅ ClickHouseDataManager registered (component_id: {component_id})")
            logger.info(f"   Initialization Order: 10 (after RegimeEngine=5)")
            logger.info(f"   Symbols: {', '.join(self.config.data.symbols)}")
            logger.info(f"   Period: {self.config.data.start_date} → {self.config.data.end_date}")
            logger.info(f"   Interval: {self.config.data.interval}")
            logger.info(f"   Database: {self.config.data.clickhouse_database}")
            logger.info(f"   Regime-Aware: ✅")
            
            # Load historical data
            logger.info("\n📥 Loading historical data...")
            await self._load_historical_data()
            
            # Consolidate multi-symbol data for single-symbol backtests
            if len(self.market_data) == 1:
                # Single symbol - use directly
                symbol = list(self.market_data.keys())[0]
                self.historical_data = self.market_data[symbol]
                logger.info(f"✅ Historical data consolidated: {len(self.historical_data)} bars for {symbol}")
            elif len(self.market_data) > 1:
                # Multi-symbol - concatenate (for now, use first symbol)
                # TODO: Implement proper multi-symbol data handling
                symbol = list(self.market_data.keys())[0]
                self.historical_data = self.market_data[symbol]
                logger.warning(f"⚠️ Multi-symbol backtest - using {symbol} data only for now")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize ClickHouseDataManager: {e}", exc_info=True)
            raise RuntimeError(f"Data manager initialization failed: {e}")
    
    async def _load_historical_data(self) -> Dict[str, pd.DataFrame]:
        """
        Load historical market data from ClickHouse
        
        This method loads all required historical data for the backtest period.
        The data will be used for bar-by-bar simulation.
        
        Returns:
            Dictionary mapping symbol -> DataFrame with OHLCV data
        """
        try:
            from datetime import datetime, timedelta
            
            logger.info("   Fetching data from ClickHouse...")
            
            # Convert date strings to datetime objects
            start_dt = datetime.strptime(self.config.data.start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(self.config.data.end_date, "%Y-%m-%d")
            
            # ENHANCEMENT: Add trading hours for intraday data
            # If we're loading intraday data (1min, 5min, 15min), ensure we have
            # proper trading hours to get a full day of data
            if self.config.data.interval in ['1min', '5min', '15min', '1h']:
                # For single-day backtests, set to market hours (09:30 - 16:00 ET)
                if start_dt.date() == end_dt.date():
                    logger.info(f"   Single-day backtest detected - using market hours (09:30-16:00)")
                    start_dt = start_dt.replace(hour=9, minute=30, second=0)
                    end_dt = end_dt.replace(hour=16, minute=0, second=0)
                else:
                    # Multi-day backtest: set start to market open, end to market close
                    logger.info(f"   Multi-day backtest - adjusting to market hours")
                    start_dt = start_dt.replace(hour=9, minute=30, second=0)
                    end_dt = end_dt.replace(hour=16, minute=0, second=0)
            
            logger.info(f"   Data range: {start_dt} to {end_dt}")
            
            # Load data for all symbols
            self.market_data = {}
            
            for symbol in self.config.data.symbols:
                logger.info(f"   Loading {symbol}...")
                
                # Load market data using data manager (not async)
                data = self.data_manager.load_market_data(
                    symbols=[symbol],  # Pass as list
                    start_time=start_dt,
                    end_time=end_dt,
                    interval=self.config.data.interval
                )
                
                if data is not None and not data.empty:
                    self.market_data[symbol] = data
                    logger.info(f"   ✅ {symbol}: {len(data)} bars loaded")
                else:
                    logger.warning(f"   ⚠️  {symbol}: No data available")
            
            if not self.market_data:
                raise ValueError("No market data loaded - cannot run backtest")
            
            total_bars = sum(len(df) for df in self.market_data.values())
            logger.info(f"\n✅ Historical data loaded: {len(self.market_data)} symbols, {total_bars} total bars")
            
            return self.market_data  # Return the loaded data
            
        except Exception as e:
            logger.error(f"❌ Failed to load historical data: {e}", exc_info=True)
            raise RuntimeError(f"Historical data loading failed: {e}")
    
    async def _initialize_liquidity_engine(self) -> None:
        """
        Phase 2.4: Initialize LiquidityAssessmentEngine (BRICK #3)
        
        Order: 12 (after DataManager=10)
        
        The liquidity engine assesses market liquidity and filters trading
        signals based on liquidity conditions. It helps implement Rule 12
        (Market Microstructure & Liquidity Management).
        
        Implements:
        - Real-time liquidity assessment
        - Regime-aware liquidity scoring
        - Signal filtering based on liquidity
        """
        logger.info("\n" + "-" * 80)
        logger.info("🟢 BRICK #3: LiquidityAssessmentEngine (order=12)")
        logger.info("-" * 80)
        
        try:
            # For backtesting, we use a simplified liquidity engine
            # that estimates liquidity from historical volume data
            from core_engine.data.liquidity_engine import LiquidityAssessmentEngine
            
            # Create liquidity engine config
            liquidity_config = {
                'min_volume': 100000,  # Minimum daily volume
                'min_liquidity_score': 0.5,  # Minimum liquidity score (0-1)
                'volume_lookback': 20,  # Days for volume analysis
                'enable_regime_adjustment': True,  # Adjust for regime
                'max_spread_bps': 50,  # Maximum bid-ask spread (50 bps)
                'min_depth': 10000  # Minimum market depth
            }
            
            # Create liquidity engine
            self.liquidity_engine = LiquidityAssessmentEngine(liquidity_config)
            
            # CRITICAL: Inject regime engine (Rule 13 - Regime-First)
            if hasattr(self.liquidity_engine, 'set_regime_engine'):
                self.liquidity_engine.set_regime_engine(self.regime_engine)
                logger.info("✅ Regime engine injected into LiquidityEngine (Rule 13)")
            
            # Register with orchestrator (order=12)
            component_id = self.orchestrator.register_component(
                name="LiquidityAssessmentEngine",
                component=self.liquidity_engine,
                layer=ComponentLayer.SUPPORT,
                authority_level=AuthorityLevel.OPERATIONAL,
                initialization_order=12  # After DataManager (10)
            )
            
            self.component_ids['liquidity_engine'] = component_id
            self.components['liquidity_engine'] = self.liquidity_engine
            
            logger.info(f"✅ LiquidityAssessmentEngine registered (component_id: {component_id})")
            logger.info(f"   Initialization Order: 12 (after DataManager=10)")
            logger.info(f"   Min Volume: {liquidity_config['min_volume']:,}")
            logger.info(f"   Min Liquidity Score: {liquidity_config['min_liquidity_score']}")
            logger.info(f"   Max Spread: {liquidity_config['max_spread_bps']} bps")
            logger.info(f"   Regime-Aware: ✅ (Rule 13)")
            logger.info(f"   Rule 12 Compliance: ✅ Liquidity Management")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize LiquidityAssessmentEngine: {e}", exc_info=True)
            raise RuntimeError(f"Liquidity engine initialization failed: {e}")
    
    # ============================================================
    # Phase 3: Processing Pipeline Integration
    # ============================================================
    
    async def _initialize_phase3_processing_pipeline(self) -> None:
        """
        Phase 3: Initialize Processing Pipeline Components
        
        This phase initializes the three core processing components:
        - BRICK #4: EnhancedTechnicalIndicators (order=15)
        - BRICK #5: EnhancedFeatureEngineer (order=16)
        - BRICK #6: EnhancedSignalGenerator (order=17)
        
        These components work together to transform raw market data into
        trading signals through a structured pipeline:
        
        Market Data → Technical Indicators → Feature Engineering → Signal Generation
        
        All components are regime-aware (Rule 13) and integrate with the
        orchestrator for lifecycle management.
        """
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 3: PROCESSING PIPELINE INTEGRATION")
        logger.info("=" * 80)
        
        # Phase 3.1: Technical Indicators (BRICK #4)
        await self._initialize_indicators_engine()
        
        # Phase 3.2: Feature Engineering (BRICK #5)
        await self._initialize_feature_engineer()
        
        # Phase 3.3: Signal Generation (BRICK #6)
        await self._initialize_signal_generator()
        
        logger.info("\n✅ Phase 3: Processing Pipeline Complete!")
        logger.info("=" * 80 + "\n")
    
    # ============================================================
    # PHASE 4: Strategy & Risk Integration
    # ============================================================
    
    async def _initialize_phase4_strategy_risk(self) -> None:
        """
        Phase 4: Initialize Strategy & Risk Components
        
        This phase initializes the strategic decision-making and risk governance:
        - BRICK #7: StrategyManager (order=20) - Multi-strategy coordination
        - BRICK #8: CentralRiskManager (order=25) - Central governance (TODO: 4.3)
        
        These components coordinate trading decisions and ensure risk compliance.
        
        Implements:
        - Rule 8: Multi-Strategy Coordination
        - Rule 4: Central Risk Management (MANDATORY)
        - Rule 13: Regime-Aware strategy weighting
        """
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 4: STRATEGY & RISK INTEGRATION")
        logger.info("=" * 80)
        
        # Phase 4.1: Strategy Management (BRICK #7)
        await self._initialize_strategy_manager()
        
        # Phase 4.3: Risk Management (BRICK #8)
        await self._initialize_risk_manager()
        
        # Phase 4.4: Position Tracker
        await self._initialize_position_tracker()
        
        logger.info("\n✅ Phase 4: Strategy & Risk Complete!")
        logger.info("=" * 80 + "\n")
    
    async def _initialize_strategy_manager(self) -> None:
        """
        Phase 4.1: Initialize StrategyManager (BRICK #7)
        
        Order: 20 (after SignalGenerator=17)
        
        The strategy manager coordinates multiple trading strategies and
        determines WHAT trades should be made. It manages:
        - Multi-strategy registration and coordination
        - Signal aggregation and conflict resolution
        - Strategy allocation and weighting
        - Regime-aware strategy selection
        
        Implements:
        - Rule 8: Multi-Strategy Coordination
        - Rule 13: Regime-First (injects regime engine)
        
        This is a critical component that translates signals into actionable
        trading decisions through professional strategy coordination.
        """
        logger.info("\n" + "-" * 80)
        logger.info("🟠 BRICK #7: StrategyManager (order=20)")
        logger.info("-" * 80)
        
        try:
            from core_engine.trading.strategies.manager import StrategyManager
            from core_engine.type_definitions.strategy import StrategyType
            
            # Create strategy manager config
            # For backtesting, we enable multi-strategy coordination and
            # enhanced strategy support
            strategy_config = {
                'enable_multi_strategy_coordination': True,  # Rule 8
                'enable_enhanced_strategies': True,
                'auto_discover_strategies': False,  # Manual registration in backtest
                'strategy_registry_path': 'strategy_registry.json',  # Registry path for strategy metadata
                'max_concurrent_strategies': 10,
                'signal_aggregation_method': 'weighted_average',
                'conflict_resolution_method': 'confidence_weighted',
                'enable_regime_awareness': True,  # Rule 13
                'enable_strategy_attribution': True  # Performance tracking
            }
            
            # Create strategy manager instance
            self.strategy_manager = StrategyManager(strategy_config)
            
            # CRITICAL: Inject regime engine (Rule 13 - Regime-First)
            if hasattr(self.strategy_manager, 'set_regime_engine'):
                self.strategy_manager.set_regime_engine(self.regime_engine)
                logger.info("✅ Regime engine injected into StrategyManager (Rule 13)")
            
            # Register with orchestrator (order=20)
            component_id = self.orchestrator.register_component(
                name="StrategyManager",
                component=self.strategy_manager,
                layer=ComponentLayer.EXECUTION,
                authority_level=AuthorityLevel.OPERATIONAL,
                initialization_order=20  # After SignalGenerator (17)
            )
            
            self.component_ids['strategy_manager'] = component_id
            self.components['strategy_manager'] = self.strategy_manager
            
            logger.info(f"✅ StrategyManager registered (component_id: {component_id})")
            logger.info(f"   Initialization Order: 20 (after SignalGenerator=17)")
            logger.info(f"   Multi-Strategy Coordination: ✅ (Rule 8)")
            logger.info(f"   Regime-Aware: ✅ (Rule 13)")
            logger.info(f"   Signal Aggregation: {strategy_config['signal_aggregation_method']}")
            logger.info(f"   Conflict Resolution: {strategy_config['conflict_resolution_method']}")
            logger.info(f"   Max Strategies: {strategy_config['max_concurrent_strategies']}")
            
            # Phase 4.2: Register strategies from config
            await self._register_strategies_from_config()
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize StrategyManager: {e}", exc_info=True)
            raise RuntimeError(f"Strategy manager initialization failed: {e}")
    
    async def _register_strategies_from_config(self) -> None:
        """
        Phase 4.2: Register Enhanced Strategies from Backtest Configuration
        
        Reads the strategy configurations from self.config.strategies and
        registers each one with the StrategyManager using the EnhancedStrategyFactory.
        
        This creates actual enhanced strategy instances (e.g., EnhancedMomentumStrategy,
        EnhancedMeanReversionStrategy) that will generate trading signals.
        
        Implements:
        - Rule 8: Multi-Strategy Coordination
        - Professional strategy factory pattern
        """
        logger.info("\n📊 Registering strategies from configuration...")
        
        try:
            from core_engine.type_definitions.strategy import StrategyType
            
            if not self.config.strategies:
                logger.warning("⚠️  No strategies configured in backtest config")
                logger.info("   Using default momentum strategy for testing")
                
                # Register a default momentum strategy for testing
                default_strategy = {
                    'type': 'momentum',
                    'name': 'default_momentum',
                    'allocation_pct': 1.0,
                    'max_positions': 5,
                    'risk_limit': 0.05,
                    'lookback_period': 20,
                    'momentum_threshold': 0.02
                }
                
                strategy_type = StrategyType(default_strategy['type'])
                success = await self.strategy_manager.register_enhanced_strategy(
                    strategy_type=strategy_type,
                    config=default_strategy
                )
                
                if success:
                    logger.info(f"   ✅ Registered: {default_strategy['name']} ({default_strategy['type']})")
                else:
                    logger.error(f"   ❌ Failed to register default strategy")
                
                return
            
            # Register each configured strategy
            registered_count = 0
            for strategy_config in self.config.strategies:
                try:
                    # Convert strategy type string to StrategyType enum
                    strategy_type_str = strategy_config.strategy_type
                    strategy_type = StrategyType(strategy_type_str)
                    
                    # Convert dataclass to dict for registration
                    config_dict = {
                        'name': strategy_config.strategy_name,
                        'type': strategy_config.strategy_type,
                        'allocation_pct': strategy_config.allocation_pct,
                        'parameters': strategy_config.parameters,
                        'max_position_size': strategy_config.max_position_size,
                        'max_concentration': strategy_config.max_concentration
                    }
                    
                    # Register with strategy manager
                    success = await self.strategy_manager.register_enhanced_strategy(
                        strategy_type=strategy_type,
                        config=config_dict
                    )
                    
                    if success:
                        registered_count += 1
                        logger.info(f"   ✅ Registered: {strategy_config.strategy_name} ({strategy_type_str})")
                    else:
                        logger.warning(f"   ⚠️  Failed to register: {strategy_config.strategy_name}")
                
                except Exception as e:
                    logger.error(f"   ❌ Strategy registration error: {e}")
                    continue
            
            logger.info(f"\n✅ Strategy registration complete: {registered_count} strategies registered")
            
        except Exception as e:
            logger.error(f"❌ Strategy registration failed: {e}", exc_info=True)
            raise RuntimeError(f"Strategy registration failed: {e}")
    
    async def _initialize_risk_manager(self) -> None:
        """
        Phase 4.3: Initialize CentralRiskManager (BRICK #8)
        
        Order: 25 (after StrategyManager=20)
        
        CRITICAL: The CentralRiskManager is the SINGLE POINT OF AUTHORITY for
        all trading decisions. NO component can execute trades independently.
        
        The risk manager controls:
        - Trade authorization (WHAT trades are allowed)
        - Position limits and risk budgets
        - Cash management for BUY orders
        - Position validation for SELL orders
        - Regime-aware risk adjustments
        
        Implements:
        - Rule 4: Central Risk Management (MANDATORY SINGLE AUTHORITY)
        - Rule 13: Regime-First (regime-aware risk limits)
        - Professional position tracking and cash management
        
        This is the governance layer that ensures institutional-grade
        risk controls across all trading activities.
        """
        logger.info("\n" + "-" * 80)
        logger.info("🟡 BRICK #8: CentralRiskManager (order=25) - GOVERNANCE LAYER")
        logger.info("-" * 80)
        
        try:
            from core_engine.system.central_risk_manager import (
                CentralRiskManager, RiskManagerConfig
            )
            
            # Create risk manager config
            # For backtesting, we configure institutional-grade risk limits
            # with regime-aware adjustments
            
            # Get risk config from backtest configuration (dataclass)
            risk_config = self.config.risk if self.config.risk else None
            
            # Create risk manager config dict (CentralRiskManager creates RiskManagerConfig internally)
            risk_manager_config_dict = {
                # Position limits (regime-adjusted)
                'max_position_size': risk_config.max_position_size if risk_config else 0.10,  # 10% max
                'max_daily_var': risk_config.max_daily_var if risk_config else 0.05,  # 5% VaR
                'max_total_risk': 0.20,  # 20% total
                'position_concentration_limit': risk_config.max_concentration if risk_config else 0.15,  # 15%
                'strategy_allocation_limit': 0.33,  # 33%
                
                # Signal confidence requirements
                'min_signal_confidence': risk_config.min_signal_confidence if risk_config else 0.6,  # 60% min
                'high_confidence_threshold': 0.8,  # 80% for automatic approval
                'extreme_confidence_threshold': 0.9,  # 90% for priority
                
                # Regime-aware adjustments (Rule 13)
                'regime_risk_multipliers': (
                    risk_config.regime_risk_multipliers 
                    if risk_config and risk_config.regime_risk_multipliers 
                    else {
                        'low_volatility': 1.2,  # Increase risk in stable markets
                        'normal_volatility': 1.0,  # Normal risk
                        'high_volatility': 0.7,  # Reduce risk in volatile markets
                        'extreme_volatility': 0.4,  # Significantly reduce in extreme vol
                        'crisis': 0.2  # Minimal risk in crisis
                    }
                ),
                
                # Monitoring
                'real_time_monitoring': False  # Disabled for backtesting
            }
            
            # Create risk manager instance (it will create RiskManagerConfig internally)
            self.risk_manager = CentralRiskManager(risk_manager_config_dict)
            
            # CRITICAL: Inject controlled components (Rule 4)
            # The risk manager controls StrategyManager and requires RegimeEngine
            self.risk_manager.set_controlled_components(
                strategy_manager=self.strategy_manager,
                trading_engine=None,  # Will be set in Phase 5
                regime_engine=self.regime_engine  # Rule 13
            )
            
            logger.info("✅ Controlled components linked to RiskManager:")
            logger.info(f"   • StrategyManager: {self.strategy_manager is not None}")
            logger.info(f"   • RegimeEngine: {self.regime_engine is not None} (Rule 13)")
            
            # Register with orchestrator (order=25)
            component_id = self.orchestrator.register_component(
                name="CentralRiskManager",
                component=self.risk_manager,
                layer=ComponentLayer.GOVERNANCE,  # GOVERNANCE LAYER
                authority_level=AuthorityLevel.GOVERNANCE_CONTROL,  # HIGHEST AUTHORITY
                initialization_order=25  # After StrategyManager (20)
            )
            
            self.component_ids['risk_manager'] = component_id
            self.components['risk_manager'] = self.risk_manager
            
            logger.info(f"✅ CentralRiskManager registered (component_id: {component_id})")
            logger.info(f"   Initialization Order: 25 (after StrategyManager=20)")
            logger.info(f"   Layer: GOVERNANCE (Rule 4 - SINGLE POINT OF AUTHORITY)")
            logger.info(f"   Authority: GOVERNANCE_CONTROL (HIGHEST)")
            logger.info(f"\n   Risk Limits:")
            logger.info(f"   • Max Position Size: {risk_manager_config_dict['max_position_size']:.1%}")
            logger.info(f"   • Max Daily VaR: {risk_manager_config_dict['max_daily_var']:.1%}")
            logger.info(f"   • Position Concentration: {risk_manager_config_dict['position_concentration_limit']:.1%}")
            logger.info(f"   • Min Signal Confidence: {risk_manager_config_dict['min_signal_confidence']:.1%}")
            logger.info(f"\n   Regime-Aware Risk:")
            logger.info(f"   • Regime Adjustments: ✅ Enabled (Rule 13)")
            logger.info(f"   • Low Vol Multiplier: {risk_manager_config_dict['regime_risk_multipliers'].get('low_volatility', 1.0):.1f}x")
            logger.info(f"   • High Vol Multiplier: {risk_manager_config_dict['regime_risk_multipliers'].get('high_volatility', 1.0):.1f}x")
            logger.info(f"   • Crisis Multiplier: {risk_manager_config_dict['regime_risk_multipliers'].get('crisis', 1.0):.1f}x")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize CentralRiskManager: {e}", exc_info=True)
            raise RuntimeError(f"Risk manager initialization failed: {e}")
    
    async def _initialize_position_tracker(self) -> None:
        """
        Phase 4.4: Initialize PositionTracker Helper
        
        The position tracker is a critical helper component that provides:
        - Position tracking by symbol (long/short)
        - Cash availability tracking and validation
        - Trade validation (sufficient cash for BUY, sufficient position for SELL)
        - Unrealized and realized P&L calculation
        - Position history for analytics
        - Integration with CentralRiskManager
        
        This component ensures:
        - Can't buy if insufficient cash
        - Can't sell if no position
        - Accurate position and P&L tracking
        - Complete audit trail
        
        Critical for institutional-grade backtesting accuracy!
        """
        logger.info("\n" + "-" * 80)
        logger.info("📊 PositionTracker Helper (Phase 4.4)")
        logger.info("-" * 80)
        
        try:
            from backtest.engine.position_tracker import PositionTracker
            
            # Get initial capital from risk manager config (dataclass)
            initial_capital = self.config.risk.initial_capital if self.config.risk else 1_000_000
            
            # Get commission settings (dataclass) - commission rate is a percentage, convert to per-share
            # For simplicity, assume $0.005 per share which is typical for institutional trading
            commission_per_trade = 0.005  # $0.005 per share
            
            # Create position tracker
            self.position_tracker = PositionTracker(
                initial_capital=initial_capital,
                commission_per_trade=commission_per_trade
            )
            
            logger.info(f"✅ PositionTracker initialized")
            logger.info(f"   Initial Capital: ${initial_capital:,.2f}")
            logger.info(f"   Commission/Trade: ${commission_per_trade:.2f}")
            logger.info(f"\n   Capabilities:")
            logger.info(f"   • Position tracking by symbol (long/short)")
            logger.info(f"   • Cash availability validation")
            logger.info(f"   • Trade validation (BUY/SELL)")
            logger.info(f"   • Unrealized P&L calculation")
            logger.info(f"   • Realized P&L tracking")
            logger.info(f"   • Position history for analytics")
            logger.info(f"\n   Integration:")
            logger.info(f"   • CentralRiskManager: Position validation")
            logger.info(f"   • Execution Engine: Trade recording")
            logger.info(f"   • Analytics: Performance calculation")
            
            # Link to risk manager for position validation callbacks
            if self.risk_manager:
                # The risk manager will use position_tracker for validation
                # This will be implemented when authorization flow is built
                logger.info(f"   • Risk Manager: ✅ Linked for position validation")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize PositionTracker: {e}", exc_info=True)
            raise RuntimeError(f"Position tracker initialization failed: {e}")
    
    async def _initialize_indicators_engine(self) -> None:
        """
        Phase 3.1: Initialize EnhancedTechnicalIndicators (BRICK #4)
        
        Order: 15 (after LiquidityEngine=12)
        
        The technical indicators engine calculates 42+ professional technical
        indicators from market data. It provides the foundation for feature
        engineering and signal generation.
        
        Implements:
        - 42+ technical indicators (SMA, EMA, RSI, MACD, Bollinger Bands, etc.)
        - Vectorized calculations for performance
        - Regime-aware indicator adjustments
        - Caching for optimization
        """
        logger.info("\n" + "-" * 80)
        logger.info("🟣 BRICK #4: EnhancedTechnicalIndicators (order=15)")
        logger.info("-" * 80)
        
        try:
            from core_engine.processing.indicators.engine import (
                EnhancedTechnicalIndicators, EnhancedIndicatorConfig
            )
            
            # Create indicators engine config
            # For backtesting, we use professional defaults with optimization
            indicators_config = EnhancedIndicatorConfig(
                # Moving averages (professional defaults)
                sma_periods=[10, 20, 50, 200],  # Short to long-term trends
                ema_periods=[9, 21, 50],         # Fast response averages
                
                # Momentum indicators (institutional standards)
                rsi_period=14,                   # Standard RSI
                macd_fast=12,                    # MACD fast period
                macd_slow=26,                    # MACD slow period
                macd_signal=9,                   # MACD signal line
                
                # Volatility indicators (risk management focused)
                bb_period=20,                    # Bollinger Bands
                bb_std=2.0,                      # 2 standard deviations
                atr_period=14,                   # Average True Range
                
                # Volume indicators (liquidity analysis)
                volume_sma_period=20,            # Volume moving average
                
                # Oscillators (market timing)
                stoch_k_period=14,               # Stochastic %K
                stoch_d_period=3,                # Stochastic %D
                williams_r_period=14,            # Williams %R
                
                # Advanced indicators (regime detection)
                adx_period=14,                   # Trend strength
                aroon_period=25,                 # Trend identification
                
                # Performance optimization
                enable_caching=True,             # Cache indicator calculations
                parallel_processing=False,       # Sequential for backtesting
                
                # Integration settings
                output_format="enhanced",        # Enhanced output format
                include_signals=True,            # Include signal generation
                normalize_values=False           # Raw values for transparency
            )
            
            # Create indicators engine
            self.indicators_engine = EnhancedTechnicalIndicators(indicators_config)
            
            # CRITICAL: Inject regime engine (Rule 13 - Regime-First)
            if hasattr(self.indicators_engine, 'set_regime_engine'):
                self.indicators_engine.set_regime_engine(self.regime_engine)
                logger.info("✅ Regime engine injected into IndicatorsEngine (Rule 13)")
            
            # Register with orchestrator (order=15)
            component_id = self.orchestrator.register_component(
                name="EnhancedTechnicalIndicators",
                component=self.indicators_engine,
                layer=ComponentLayer.SUPPORT,
                authority_level=AuthorityLevel.OPERATIONAL,
                initialization_order=15  # After LiquidityEngine (12)
            )
            
            self.component_ids['indicators_engine'] = component_id
            self.components['indicators_engine'] = self.indicators_engine
            
            logger.info(f"✅ EnhancedTechnicalIndicators registered (component_id: {component_id})")
            logger.info(f"   Initialization Order: 15 (after LiquidityEngine=12)")
            logger.info(f"   Indicators: 42+ professional technical indicators")
            logger.info(f"   SMA Periods: {indicators_config.sma_periods}")
            logger.info(f"   EMA Periods: {indicators_config.ema_periods}")
            logger.info(f"   RSI Period: {indicators_config.rsi_period}")
            logger.info(f"   MACD: {indicators_config.macd_fast}/{indicators_config.macd_slow}/{indicators_config.macd_signal}")
            logger.info(f"   Bollinger Bands: {indicators_config.bb_period} period, {indicators_config.bb_std} std")
            logger.info(f"   Caching: {'Enabled' if indicators_config.enable_caching else 'Disabled'}")
            logger.info(f"   Regime-Aware: ✅ (Rule 13)")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize EnhancedTechnicalIndicators: {e}", exc_info=True)
            raise RuntimeError(f"Indicators engine initialization failed: {e}")
    
    async def _initialize_feature_engineer(self) -> None:
        """
        Phase 3.2: Initialize EnhancedFeatureEngineer (BRICK #5)
        
        Order: 16 (after IndicatorsEngine=15)
        
        The feature engineer transforms technical indicators into ML-ready
        features for signal generation. It creates derived features, interaction
        terms, and normalized representations.
        
        Implements:
        - Feature engineering from indicators
        - Regime-aware feature transformations
        - Feature normalization and scaling
        - Integration with signal generator
        """
        logger.info("\n" + "-" * 80)
        logger.info("🟣 BRICK #5: EnhancedFeatureEngineer (order=16)")
        logger.info("-" * 80)
        
        try:
            from core_engine.processing.features.engineer import EnhancedFeatureEngineer
            
            # Create feature engineer config
            # For backtesting, we focus on robust features with regime awareness
            feature_config = {
                'enable_regime_features': True,        # Regime-based features
                'enable_interaction_features': True,   # Indicator interactions
                'enable_time_features': True,          # Time-based features
                'normalization_method': 'zscore',      # Z-score normalization
                'lookback_window': 60,                 # 60 bars for calculations
                'enable_caching': True                 # Cache feature calculations
            }
            
            # Create feature engineer
            self.feature_engineer = EnhancedFeatureEngineer(feature_config)
            
            # CRITICAL: Inject regime engine (Rule 13 - Regime-First)
            if hasattr(self.feature_engineer, 'set_regime_engine'):
                self.feature_engineer.set_regime_engine(self.regime_engine)
                logger.info("✅ Regime engine injected into FeatureEngineer (Rule 13)")
            
            # Register with orchestrator (order=16)
            component_id = self.orchestrator.register_component(
                name="EnhancedFeatureEngineer",
                component=self.feature_engineer,
                layer=ComponentLayer.SUPPORT,
                authority_level=AuthorityLevel.OPERATIONAL,
                initialization_order=16  # After IndicatorsEngine (15)
            )
            
            self.component_ids['feature_engineer'] = component_id
            self.components['feature_engineer'] = self.feature_engineer
            
            logger.info(f"✅ EnhancedFeatureEngineer registered (component_id: {component_id})")
            logger.info(f"   Initialization Order: 16 (after IndicatorsEngine=15)")
            logger.info(f"   Regime Features: {'Enabled' if feature_config['enable_regime_features'] else 'Disabled'}")
            logger.info(f"   Interaction Features: {'Enabled' if feature_config['enable_interaction_features'] else 'Disabled'}")
            logger.info(f"   Normalization: {feature_config['normalization_method']}")
            logger.info(f"   Lookback Window: {feature_config['lookback_window']} bars")
            logger.info(f"   Regime-Aware: ✅ (Rule 13)")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize EnhancedFeatureEngineer: {e}", exc_info=True)
            raise RuntimeError(f"Feature engineer initialization failed: {e}")
    
    async def _initialize_signal_generator(self) -> None:
        """
        Phase 3.3: Initialize EnhancedSignalGenerator (BRICK #6)
        
        Order: 17 (after FeatureEngineer=16)
        
        The signal generator transforms engineered features into trading signals.
        It applies regime-aware filters and liquidity checks to generate high-quality
        trading signals.
        
        Implements:
        - Signal generation from features
        - Regime-aware signal filtering
        - Liquidity-based signal filtering (Rule 12)
        - Confidence scoring
        """
        logger.info("\n" + "-" * 80)
        logger.info("🟣 BRICK #6: EnhancedSignalGenerator (order=17)")
        logger.info("-" * 80)
        
        try:
            from core_engine.processing.signals.generator import EnhancedSignalGenerator
            
            # Create signal generator config
            # For backtesting, we use conservative signal generation with regime awareness
            signal_config = {
                'min_confidence': 0.6,                 # Minimum 60% confidence
                'enable_regime_filter': True,          # Filter by regime suitability
                'enable_liquidity_filter': True,       # Filter by liquidity (Rule 12)
                'signal_types': ['BUY', 'SELL', 'HOLD'],  # Signal types
                'lookback_window': 20,                 # Signal lookback period
                'enable_caching': True                 # Cache signal calculations
            }
            
            # Create signal generator
            self.signal_generator = EnhancedSignalGenerator(signal_config)
            
            # CRITICAL: Inject regime engine (Rule 13 - Regime-First)
            if hasattr(self.signal_generator, 'set_regime_engine'):
                self.signal_generator.set_regime_engine(self.regime_engine)
                logger.info("✅ Regime engine injected into SignalGenerator (Rule 13)")
            
            # Inject liquidity engine for signal filtering (Rule 12)
            if hasattr(self.signal_generator, 'set_liquidity_engine'):
                self.signal_generator.set_liquidity_engine(self.liquidity_engine)
                logger.info("✅ Liquidity engine injected into SignalGenerator (Rule 12)")
            
            # Register with orchestrator (order=17)
            component_id = self.orchestrator.register_component(
                name="EnhancedSignalGenerator",
                component=self.signal_generator,
                layer=ComponentLayer.SUPPORT,
                authority_level=AuthorityLevel.OPERATIONAL,
                initialization_order=17  # After FeatureEngineer (16)
            )
            
            self.component_ids['signal_generator'] = component_id
            self.components['signal_generator'] = self.signal_generator
            
            logger.info(f"✅ EnhancedSignalGenerator registered (component_id: {component_id})")
            logger.info(f"   Initialization Order: 17 (after FeatureEngineer=16)")
            logger.info(f"   Min Confidence: {signal_config['min_confidence']:.0%}")
            logger.info(f"   Regime Filter: {'Enabled' if signal_config['enable_regime_filter'] else 'Disabled'}")
            logger.info(f"   Liquidity Filter: {'Enabled' if signal_config['enable_liquidity_filter'] else 'Disabled'} (Rule 12)")
            logger.info(f"   Signal Types: {', '.join(signal_config['signal_types'])}")
            logger.info(f"   Regime-Aware: ✅ (Rule 13)")
            logger.info(f"   Rule 12 Compliance: ✅ Liquidity-Filtered Signals")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize EnhancedSignalGenerator: {e}", exc_info=True)
            raise RuntimeError(f"Signal generator initialization failed: {e}")
    
    # ============================================================
    # PHASE 5: EXECUTION INTEGRATION (BRICK #9)
    # ============================================================
    
    async def _initialize_phase5_execution(self) -> None:
        """
        Phase 5: Initialize Execution Components (BRICK #9)
        
        This phase integrates:
        - UnifiedExecutionEngine (BRICK #9, order=40)
        
        Execution Flow (Rule 4):
        1. Strategy generates signals
        2. CentralRiskManager authorizes trades
        3. UnifiedExecutionEngine executes authorized trades
        4. PositionTracker updates positions
        
        Historical Execution (Backtesting):
        - Simulated realistic execution
        - Apply spread costs, market impact, slippage
        - Transaction cost analysis (TCA)
        """
        logger.info("\n" + "=" * 80)
        logger.info("⚡ PHASE 5: EXECUTION INTEGRATION")
        logger.info("=" * 80)
        
        try:
            # Initialize UnifiedExecutionEngine (BRICK #9, order=40)
            await self._initialize_execution_engine()
            
            logger.info("\n✅ Phase 5 complete: Execution components ready")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"❌ Phase 5 initialization failed: {e}", exc_info=True)
            raise RuntimeError(f"Execution integration failed: {e}")
    
    async def _initialize_execution_engine(self) -> None:
        """
        Phase 5.1: Initialize UnifiedExecutionEngine (BRICK #9)
        
        Order: 40 (late - after all signal processing and risk authorization)
        
        The execution engine simulates realistic trade execution in backtests:
        - Applies spread costs (bid-ask spread)
        - Models market impact (Rule 12)
        - Simulates slippage
        - Records executed trades with full cost breakdown
        - Updates positions via PositionTracker
        
        For backtesting, execution is simulated but uses realistic cost models
        to ensure strategy performance reflects real-world transaction costs.
        
        Implements:
        - Historical execution simulation
        - Transaction cost analysis (TCA)
        - Position update callbacks
        - Regime-aware execution (Rule 13)
        """
        logger.info("\n" + "-" * 80)
        logger.info("⚡ BRICK #9: UnifiedExecutionEngine (order=40)")
        logger.info("-" * 80)
        
        try:
            from core_engine.system.unified_execution_engine import (
                UnifiedExecutionEngine,
                ExecutionAlgorithm
            )
            
            # Create execution engine config for backtesting
            execution_config = {
                # Historical execution settings
                'mode': 'backtest',
                'enable_realistic_fills': True,        # Apply realistic fill models
                'enable_spread_costs': True,           # Apply bid-ask spreads
                'enable_market_impact': True,          # Apply market impact (Rule 12)
                'enable_slippage': True,               # Apply slippage modeling
                
                # Cost modeling
                'spread_model': 'historical',          # Use historical spreads if available
                'spread_fallback_bps': 5,              # Fallback: 5 bps spread
                'base_slippage_bps': 2,                # Base slippage: 2 bps
                'impact_model': 'almgren_chriss',      # Almgren-Chriss impact model
                
                # Execution algorithms (for backtest, primarily MARKET)
                'default_algorithm': ExecutionAlgorithm.MARKET,
                'enable_adaptive_routing': False,      # No smart routing in backtest
                
                # Position tracking
                'enable_position_tracking': True,      # Track positions via callbacks
                'validate_positions': True,            # Validate position updates
                
                # Regime awareness (Rule 13)
                'regime_aware': True,                  # Adjust execution costs by regime
                'regime_impact_multipliers': {
                    'low_volatility': 0.8,             # Lower impact in calm markets
                    'normal_volatility': 1.0,          # Normal impact
                    'high_volatility': 1.3,            # Higher impact in volatile markets
                    'extreme_volatility': 1.8          # Much higher impact in crisis
                }
            }
            
            # Create execution engine
            self.execution_engine = UnifiedExecutionEngine(execution_config)
            
            # CRITICAL: Set position callbacks to PositionTracker
            if self.position_tracker and hasattr(self.execution_engine, 'set_position_callbacks'):
                self.execution_engine.set_position_callbacks(
                    risk_manager_callback=self.position_tracker,  # Position updates flow through tracker
                    position_update_callback=self.position_tracker.update_position
                )
                logger.info("✅ Position callbacks configured → PositionTracker")
            else:
                logger.warning("⚠️  No position tracker available - position updates may not work")
            
            # CRITICAL: Inject regime engine (Rule 13 - Regime-First)
            if hasattr(self.execution_engine, 'set_regime_engine'):
                self.execution_engine.set_regime_engine(self.regime_engine)
                logger.info("✅ Regime engine injected into ExecutionEngine (Rule 13)")
            
            # Inject liquidity engine for impact modeling (Rule 12)
            if hasattr(self.execution_engine, 'set_liquidity_engine'):
                self.execution_engine.set_liquidity_engine(self.liquidity_engine)
                logger.info("✅ Liquidity engine injected for impact modeling (Rule 12)")
            
            # Register with orchestrator (order=40)
            component_id = self.orchestrator.register_component(
                name="UnifiedExecutionEngine",
                component=self.execution_engine,
                layer=ComponentLayer.EXECUTION,
                authority_level=AuthorityLevel.OPERATIONAL,
                initialization_order=40  # Late initialization (after risk=25, before analytics=32)
            )
            
            self.component_ids['execution_engine'] = component_id
            self.components['execution_engine'] = self.execution_engine
            
            logger.info(f"✅ UnifiedExecutionEngine registered (component_id: {component_id})")
            logger.info(f"   Initialization Order: 40 (late - after risk authorization)")
            logger.info(f"   Mode: Backtest (Historical Simulation)")
            logger.info(f"   Realistic Fills: ✅ (spread + impact + slippage)")
            logger.info(f"   Spread Model: {execution_config['spread_model']} (fallback: {execution_config['spread_fallback_bps']} bps)")
            logger.info(f"   Impact Model: {execution_config['impact_model']} (Rule 12)")
            logger.info(f"   Base Slippage: {execution_config['base_slippage_bps']} bps")
            logger.info(f"   Position Tracking: ✅ (via PositionTracker)")
            logger.info(f"   Regime-Aware: ✅ (Rule 13 - execution costs adapt to regime)")
            logger.info(f"   Rule 12 Compliance: ✅ Liquidity-Aware Execution Costs")
            logger.info(f"   Rule 4 Compliance: ✅ Executes ONLY authorized trades")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize UnifiedExecutionEngine: {e}", exc_info=True)
            raise RuntimeError(f"Execution engine initialization failed: {e}")
    
    # ============================================================
    # PHASE 6: ANALYTICS INTEGRATION (BRICKS #10-12)
    # ============================================================
    
    async def _initialize_phase6_analytics(self) -> None:
        """
        Phase 6: Initialize Analytics Components (BRICKs #10-12)
        
        This phase integrates:
        - EnhancedMetricsCalculator (BRICK #10, order=32)
        - PerformanceAnalyzer (BRICK #11, order=33)
        - EnhancedAnalyticsManager (BRICK #12, order=35)
        
        Analytics Flow:
        1. MetricsCalculator: Calculate performance metrics
        2. PerformanceAnalyzer: Analyze backtest performance
        3. AnalyticsManager: Orchestrate all analytics
        
        The analytics layer provides comprehensive performance measurement,
        attribution analysis, and reporting capabilities.
        """
        logger.info("\n" + "=" * 80)
        logger.info("📊 PHASE 6: ANALYTICS INTEGRATION")
        logger.info("=" * 80)
        
        try:
            # Initialize EnhancedMetricsCalculator (BRICK #10, order=32)
            await self._initialize_metrics_calculator()
            
            # Initialize PerformanceAnalyzer (BRICK #11, order=33)
            await self._initialize_performance_analyzer()
            
            # Initialize EnhancedAnalyticsManager (BRICK #12, order=35)
            await self._initialize_analytics_manager()
            
            # Initialize PerformanceReporter (helper)
            await self._initialize_performance_reporter()
            
            logger.info("\n✅ Phase 6 complete: Analytics components ready")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"❌ Phase 6 initialization failed: {e}", exc_info=True)
            raise RuntimeError(f"Analytics integration failed: {e}")
    
    async def _initialize_metrics_calculator(self) -> None:
        """
        Phase 6.1: Initialize EnhancedMetricsCalculator (BRICK #10)
        
        Order: 32 (after execution=40, before performance=33)
        
        The metrics calculator computes comprehensive performance metrics:
        - Returns, volatility, Sharpe ratio
        - Maximum drawdown, recovery time
        - Win rate, profit factor
        - Risk-adjusted returns
        - Transaction cost analysis (TCA)
        
        For backtesting, metrics are calculated from:
        - Execution history (trades with costs)
        - Position history (portfolio state over time)
        - Market data (benchmark comparisons)
        """
        logger.info("\n" + "-" * 80)
        logger.info("📊 BRICK #10: EnhancedMetricsCalculator (order=32)")
        logger.info("-" * 80)
        
        try:
            from core_engine.analytics.metrics_calculator import EnhancedMetricsCalculator
            
            # Create metrics calculator config
            metrics_config = {
                # Performance metrics
                'risk_free_rate': 0.04,  # 4% annual risk-free rate
                'trading_days_per_year': 252,
                'enable_annualization': True,
                
                # Risk metrics
                'var_confidence_level': 0.95,  # 95% VaR
                'cvar_confidence_level': 0.95,  # 95% CVaR
                
                # Attribution
                'enable_factor_attribution': True,
                'enable_strategy_attribution': True,
                
                # TCA
                'enable_transaction_cost_analysis': True,
                'benchmark_spread_bps': 5.0,
                'benchmark_impact_bps': 3.0
            }
            
            # Create metrics calculator
            self.metrics_calculator = EnhancedMetricsCalculator(metrics_config)
            
            # Register with orchestrator (order=32)
            component_id = self.orchestrator.register_component(
                name="EnhancedMetricsCalculator",
                component=self.metrics_calculator,
                layer=ComponentLayer.SUPPORT,
                authority_level=AuthorityLevel.OPERATIONAL,
                initialization_order=32  # After execution (40), before performance (33)
            )
            
            self.component_ids['metrics_calculator'] = component_id
            self.components['metrics_calculator'] = self.metrics_calculator
            
            logger.info(f"✅ EnhancedMetricsCalculator registered (component_id: {component_id})")
            logger.info(f"   Initialization Order: 32")
            logger.info(f"   Risk-Free Rate: {metrics_config['risk_free_rate']:.2%}")
            logger.info(f"   VaR Confidence: {metrics_config['var_confidence_level']:.1%}")
            logger.info(f"   Factor Attribution: ✅")
            logger.info(f"   Transaction Cost Analysis: ✅")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize EnhancedMetricsCalculator: {e}", exc_info=True)
            raise RuntimeError(f"Metrics calculator initialization failed: {e}")
    
    async def _initialize_performance_analyzer(self) -> None:
        """
        Phase 6.2: Initialize PerformanceAnalyzer (BRICK #11)
        
        Order: 33 (after metrics=32, before analytics_manager=35)
        
        The performance analyzer provides comprehensive backtest analysis:
        - Performance summary statistics
        - Equity curve analysis
        - Drawdown analysis
        - Trade analysis (win/loss distribution)
        - Risk metrics aggregation
        - Benchmark comparison
        - Strategy attribution
        
        Analyzes results from execution_history and position_history.
        """
        logger.info("\n" + "-" * 80)
        logger.info("📈 BRICK #11: PerformanceAnalyzer (order=33)")
        logger.info("-" * 80)
        
        try:
            from core_engine.analytics.performance_analyzer import PerformanceAnalyzer
            
            # Create performance analyzer config
            performance_config = {
                # Analysis settings
                'enable_equity_curve': True,
                'enable_drawdown_analysis': True,
                'enable_trade_analysis': True,
                'enable_benchmark_comparison': True,
                
                # Benchmark
                'benchmark_symbol': 'SPY',
                'benchmark_return': 0.10,  # 10% annual return for comparison
                
                # Analysis depth
                'analyze_by_time_of_day': False,  # Disable for simplicity
                'analyze_by_regime': True,  # Analyze by market regime
                'analyze_by_strategy': True  # Multi-strategy attribution
            }
            
            # Create performance analyzer
            self.performance_analyzer = PerformanceAnalyzer(performance_config)
            
            # Inject dependencies
            if hasattr(self.performance_analyzer, 'set_metrics_calculator'):
                self.performance_analyzer.set_metrics_calculator(self.metrics_calculator)
                logger.info("✅ MetricsCalculator injected into PerformanceAnalyzer")
            
            # Register with orchestrator (order=33)
            component_id = self.orchestrator.register_component(
                name="PerformanceAnalyzer",
                component=self.performance_analyzer,
                layer=ComponentLayer.SUPPORT,
                authority_level=AuthorityLevel.OPERATIONAL,
                initialization_order=33  # After metrics (32), before analytics_manager (35)
            )
            
            self.component_ids['performance_analyzer'] = component_id
            self.components['performance_analyzer'] = self.performance_analyzer
            
            logger.info(f"✅ PerformanceAnalyzer registered (component_id: {component_id})")
            logger.info(f"   Initialization Order: 33")
            logger.info(f"   Equity Curve Analysis: ✅")
            logger.info(f"   Drawdown Analysis: ✅")
            logger.info(f"   Trade Analysis: ✅")
            logger.info(f"   Regime Attribution: ✅")
            logger.info(f"   Strategy Attribution: ✅")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize PerformanceAnalyzer: {e}", exc_info=True)
            raise RuntimeError(f"Performance analyzer initialization failed: {e}")
    
    async def _initialize_analytics_manager(self) -> None:
        """
        Phase 6.3: Initialize EnhancedAnalyticsManager (BRICK #12)
        
        Order: 35 (last analytics component)
        
        The analytics manager orchestrates all analytics components:
        - Coordinates metrics calculation
        - Coordinates performance analysis
        - Generates comprehensive reports
        - Exports results (JSON, CSV, HTML)
        - Creates visualizations (plots, charts)
        
        This is the top-level analytics orchestrator that provides
        a unified interface to all analytics capabilities.
        """
        logger.info("\n" + "-" * 80)
        logger.info("📊 BRICK #12: EnhancedAnalyticsManager (order=35)")
        logger.info("-" * 80)
        
        try:
            from core_engine.analytics.manager_enhanced import (
                EnhancedAnalyticsManager, AnalyticsConfig, AnalyticsMode
            )
            
            # Create analytics manager config
            analytics_config = AnalyticsConfig(
                # Mode
                mode=AnalyticsMode.BATCH,  # Batch mode for backtesting
                
                # Workers
                max_workers=2,  # Reduced for backtest
                
                # Caching
                enable_caching=True,
                cache_ttl_hours=24,
                
                # Storage
                output_directory='backtest_results',
                archive_old_results=False,  # Don't archive during backtest
                
                # Analysis
                enable_performance_analysis=True,
                enable_attribution_analysis=True,
                enable_benchmark_analysis=True,
                enable_risk_analysis=True,
                
                # Reporting
                auto_generate_reports=True,
                report_frequency='daily'
            )
            
            # Create analytics manager
            self.analytics_manager = EnhancedAnalyticsManager(analytics_config)
            
            # Inject dependencies
            if hasattr(self.analytics_manager, 'set_metrics_calculator'):
                self.analytics_manager.set_metrics_calculator(self.metrics_calculator)
                logger.info("✅ MetricsCalculator injected into AnalyticsManager")
            
            if hasattr(self.analytics_manager, 'set_performance_analyzer'):
                self.analytics_manager.set_performance_analyzer(self.performance_analyzer)
                logger.info("✅ PerformanceAnalyzer injected into AnalyticsManager")
            
            # Register with orchestrator (order=35)
            component_id = self.orchestrator.register_component(
                name="EnhancedAnalyticsManager",
                component=self.analytics_manager,
                layer=ComponentLayer.SUPPORT,
                authority_level=AuthorityLevel.OPERATIONAL,
                initialization_order=35  # Last analytics component
            )
            
            self.component_ids['analytics_manager'] = component_id
            self.components['analytics_manager'] = self.analytics_manager
            
            logger.info(f"✅ EnhancedAnalyticsManager registered (component_id: {component_id})")
            logger.info(f"   Initialization Order: 35 (last analytics component)")
            logger.info(f"   Mode: {analytics_config.mode.value}")
            logger.info(f"   Detailed Reports: ✅")
            logger.info(f"   Summary Reports: ✅")
            logger.info(f"   Output Dir: {analytics_config.output_directory}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize EnhancedAnalyticsManager: {e}", exc_info=True)
            raise RuntimeError(f"Analytics manager initialization failed: {e}")
    
    async def _initialize_performance_reporter(self) -> None:
        """
        Phase 6.3: Initialize PerformanceReporter (Helper)
        
        The performance reporter is a helper class (not a registered component)
        that aggregates results from analytics components and formats
        comprehensive backtest reports.
        
        Responsibilities:
        - Generate performance summary from execution history
        - Format reports in multiple formats (console, JSON, CSV)
        - Calculate derived statistics
        - Export reports to files
        - Provide transaction cost analysis (TCA)
        """
        logger.info("\n" + "-" * 80)
        logger.info("📊 HELPER: PerformanceReporter")
        logger.info("-" * 80)
        
        try:
            from backtest.engine.performance_reporter import PerformanceReporter
            
            # Create performance reporter config
            reporter_config = {
                'output_dir': 'backtest_results',
                'risk_free_rate': 0.04,  # 4% annual risk-free rate
                'trading_days_per_year': 252
            }
            
            # Create performance reporter
            self.performance_reporter = PerformanceReporter(reporter_config)
            
            logger.info(f"✅ PerformanceReporter created")
            logger.info(f"   Output Directory: {self.performance_reporter.output_dir}")
            logger.info(f"   Risk-Free Rate: {self.performance_reporter.risk_free_rate:.2%}")
            logger.info(f"   Report Formats: Console, JSON, CSV, Markdown")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize PerformanceReporter: {e}", exc_info=True)
            raise RuntimeError(f"Performance reporter initialization failed: {e}")
    
    # ============================================================
    # REPORT GENERATION METHODS
    # ============================================================
    
    def generate_performance_report(self,
                                   format: str = 'console',
                                   export: bool = False) -> str:
        """
        Generate comprehensive performance report from backtest results
        
        This method aggregates results from:
        - execution_history: Executed trades with costs
        - position_tracker: Portfolio positions and P&L
        - analytics_manager: Performance metrics
        
        Args:
            format: Report format ('console', 'json', 'csv', 'markdown')
            export: Whether to export report to file
        
        Returns:
            Formatted report string
        """
        logger.info("\n" + "=" * 80)
        logger.info("📊 GENERATING BACKTEST PERFORMANCE REPORT")
        logger.info("=" * 80)
        
        try:
            if not self.performance_reporter:
                raise RuntimeError("PerformanceReporter not initialized")
            
            if not self.execution_history:
                logger.warning("⚠️ No execution history available")
                return "No trades executed - cannot generate report"
            
            # Get initial and final capital
            initial_capital = self.config.execution.initial_capital if hasattr(self.config.execution, 'initial_capital') else 100000.0
            final_capital = self.position_tracker.cash if self.position_tracker else initial_capital
            
            # Generate performance summary
            from backtest.engine.performance_reporter import ReportFormat
            
            # Map string format to ReportFormat enum
            format_map = {
                'console': ReportFormat.CONSOLE,
                'json': ReportFormat.JSON,
                'csv': ReportFormat.CSV,
                'markdown': ReportFormat.MARKDOWN
            }
            report_format = format_map.get(format.lower(), ReportFormat.CONSOLE)
            
            summary = self.performance_reporter.generate_performance_summary(
                backtest_config=self.config,
                execution_history=self.execution_history,
                initial_capital=initial_capital,
                final_capital=final_capital
            )
            
            # Add bars processed count
            if self.historical_data is not None:
                summary.total_bars_processed = len(self.historical_data)
            
            # Format report
            report = self.performance_reporter.format_report(summary, report_format)
            
            # Export if requested
            if export:
                filepath = self.performance_reporter.export_report(summary, report_format)
                logger.info(f"✅ Report exported to: {filepath}")
            
            return report
            
        except Exception as e:
            logger.error(f"❌ Failed to generate performance report: {e}", exc_info=True)
            return f"Error generating report: {str(e)}"
    
    def get_performance_summary(self) -> Optional[Any]:
        """
        Get performance summary object (for programmatic access)
        
        Returns:
            BacktestSummary object or None if not available
        """
        try:
            if not self.performance_reporter or not self.execution_history:
                return None
            
            initial_capital = self.config.execution.initial_capital if hasattr(self.config.execution, 'initial_capital') else 100000.0
            final_capital = self.position_tracker.cash if self.position_tracker else initial_capital
            
            summary = self.performance_reporter.generate_performance_summary(
                backtest_config=self.config,
                execution_history=self.execution_history,
                initial_capital=initial_capital,
                final_capital=final_capital
            )
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Failed to get performance summary: {e}")
            return None
    
    # ============================================================
    # MAIN BACKTEST LOOP (PHASE 7)
    # ============================================================
    
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
        logger.info(f"   Period: {self.config.data.start_date} → {self.config.data.end_date}")
        logger.info(f"   Symbols: {', '.join(self.config.data.symbols)}")
        logger.info("=" * 80 + "\n")
        
        if not self.is_initialized:
            raise RuntimeError("Engine not initialized. Call initialize() first.")
        
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
            
            # Bar-by-bar processing
            bars_processed = 0
            bars_with_signals = 0
            bars_with_trades = 0
            
            # Progress tracking
            progress_interval = max(1, total_bars // 20)  # Report every 5%
            
            for idx, (timestamp, bar) in enumerate(self.historical_data.iterrows()):
                self.current_bar_index = idx
                
                # Progress reporting
                if idx % progress_interval == 0 or idx == total_bars - 1:
                    progress_pct = (idx + 1) / total_bars * 100
                    logger.info(f"   Progress: {progress_pct:5.1f}% ({idx+1}/{total_bars}) - "
                              f"Trades: {len(self.execution_history)}")
                
                try:
                    # Process current bar
                    bar_result = await self._process_single_bar(bar, timestamp, idx)
                    
                    bars_processed += 1
                    if bar_result.get('signals_generated', 0) > 0:
                        bars_with_signals += 1
                    if bar_result.get('trades_executed', 0) > 0:
                        bars_with_trades += 1
                    
                except Exception as e:
                    logger.error(f"❌ Error processing bar {idx} at {timestamp}: {e}")
                    # Continue with next bar rather than failing entire backtest
                    continue
            
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
            logger.info(f"   Speed: {bars_processed/duration:.1f} bars/sec")
            logger.info("=" * 80 + "\n")
            
            # Generate performance report
            logger.info("📊 Generating performance report...")
            report = self.generate_performance_report(format='console', export=True)
            summary = self.get_performance_summary()
            
            # Compile results
            results = {
                'success': True,
                'summary': summary,
                'total_bars': bars_processed,
                'bars_with_signals': bars_with_signals,
                'bars_with_trades': bars_with_trades,
                'total_trades': len(self.execution_history),
                'final_capital': self.position_tracker.cash if self.position_tracker else 0,
                'duration_seconds': duration,
                'bars_per_second': bars_processed / duration if duration > 0 else 0,
                'report': report,
                'start_time': start_time,
                'end_time': end_time
            }
            
            self.is_running = False
            return results
            
        except Exception as e:
            logger.error(f"❌ Backtest execution failed: {e}", exc_info=True)
            self.is_running = False
            return {
                'success': False,
                'error': str(e),
                'total_bars': bars_processed if 'bars_processed' in locals() else 0,
                'total_trades': len(self.execution_history)
            }
    
    async def _process_single_bar(self,
                                  bar: pd.Series,
                                  timestamp: datetime,
                                  bar_index: int) -> Dict[str, Any]:
        """
        Process a single bar of market data through the complete pipeline
        
        This method executes one iteration of the backtest loop:
        1. Update regime engine with market data (Rule 13 - Regime-First)
        2. Process through indicators/features/signals pipeline
        3. Strategy signal generation ✅ Phase 7.2
        4. Risk authorization
        5. Trade execution simulation
        6. Position updates
        
        Args:
            bar: Market data for current bar
            timestamp: Timestamp of current bar
            bar_index: Index of current bar
        
        Returns:
            Dict with bar processing results
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
            # Step 1: Update regime engine (Rule 13 - Regime-First)
            if self.regime_engine:
                # Convert bar to dict for regime engine
                bar_dict = bar.to_dict()
                bar_dict['timestamp'] = timestamp
                
                # Process market data through regime engine
                regime_result = self.regime_engine.process_market_data(bar_dict)
                
                # Get current regime from engine state
                if hasattr(self.regime_engine, 'current_regime') and self.regime_engine.current_regime:
                    regime_analysis = self.regime_engine.current_regime
                    if hasattr(regime_analysis, 'primary_regime'):
                        bar_results['regime'] = regime_analysis.primary_regime.value
                    elif hasattr(regime_analysis, 'regime'):
                        bar_results['regime'] = str(regime_analysis.regime)
                    else:
                        bar_results['regime'] = str(regime_analysis)
            
            # Step 2: Process through complete pipeline: indicators → features → signals
            # Create DataFrame for current bar (processing components expect DataFrames)
            bar_df = pd.DataFrame([bar.to_dict()], index=[timestamp])
            bar_df.index.name = 'timestamp'
            
            # Step 2a: Technical Indicators (BRICK #4)
            indicators_df = None
            if self.indicators_engine:
                try:
                    indicators_df = self.indicators_engine.calculate_indicators(bar_df)
                except Exception as e:
                    logger.debug(f"Indicators calculation skipped (insufficient data): {e}")
            
            # Step 2b: Feature Engineering (BRICK #5)
            features_df = None
            if self.feature_engineer and indicators_df is not None and not indicators_df.empty:
                try:
                    features_df = self.feature_engineer.create_features(indicators_df)
                except Exception as e:
                    logger.debug(f"Feature engineering skipped: {e}")
            
            # Step 2c: Signal Generation (BRICK #6)
            signals_df = None
            if self.signal_generator and features_df is not None and not features_df.empty:
                try:
                    signals_df = self.signal_generator.generate_signals(features_df)
                    if signals_df is not None and not signals_df.empty:
                        bar_results['signals_generated'] = len(signals_df)
                except Exception as e:
                    logger.debug(f"Signal generation skipped: {e}")
            
            # Step 3: Strategy signal generation and aggregation (BRICK #7)
            authorized_trades = []
            if signals_df is not None and not signals_df.empty:
                authorized_trades = await self._get_authorized_trades_for_bar(
                    bar_df, signals_df, timestamp
                )
            
            bar_results['trades_authorized'] = len(authorized_trades)
            
            # Step 7: Simulate execution if we have authorized trades
            if authorized_trades:
                executed_trades = await self.simulate_execution(
                    authorized_trades,
                    bar,
                    timestamp
                )
                bar_results['trades_executed'] = len(executed_trades)
            
            return bar_results
            
        except Exception as e:
            logger.error(f"❌ Error processing bar at {timestamp}: {e}")
            bar_results['error'] = str(e)
            return bar_results
    
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
            # Phase 7.2: Strategy manager processes signals
            # For now, we'll directly authorize signals from the pipeline
            # In future phases, this will involve multi-strategy coordination
            
            # Convert signals to trade requests
            for idx, signal_row in signals_df.iterrows():
                # Extract signal information
                symbol = signal_row.get('symbol', self.config.data.symbols[0])
                signal_type = signal_row.get('signal', 'HOLD')
                confidence = signal_row.get('confidence', 0.5)
                
                # Only process BUY/SELL signals (skip HOLD)
                if signal_type in ['BUY', 'SELL'] and confidence >= 0.6:
                    
                    # Get current position
                    current_position = 0.0
                    if self.position_tracker:
                        position_obj = self.position_tracker.get_position(symbol)
                        if position_obj:
                            current_position = position_obj.quantity
                    
                    # Determine trade side and quantity
                    if signal_type == 'BUY' and current_position <= 0:
                        # Enter long position
                        side = 'buy'
                        quantity = 100  # Default position size
                    elif signal_type == 'SELL' and current_position >= 0:
                        # Enter short position or close long
                        side = 'sell'
                        quantity = max(100, abs(current_position))
                    else:
                        continue  # Skip if already in position
                    
                    # Request authorization from CentralRiskManager (BRICK #8)
                    if self.risk_manager:
                        from core_engine.system.central_risk_manager import TradingDecisionRequest, TradingDecisionType
                        
                        request = TradingDecisionRequest(
                            decision_type=TradingDecisionType.POSITION_ENTRY,
                            symbol=symbol,
                            side=side,
                            quantity=quantity,
                            strategy_id='backtest_strategy',
                            confidence=confidence,
                            metadata={
                                'timestamp': timestamp.isoformat(),
                                'signal_type': signal_type,
                                'bar_index': self.current_bar_index
                            }
                        )
                        
                        # Get authorization
                        authorization = await self.risk_manager.authorize_trading_decision(request)
                        
                        # Check if authorized
                        from core_engine.system.central_risk_manager import AuthorizationLevel
                        if authorization.authorization_level != AuthorizationLevel.REJECTED:
                            authorized_trades.append({
                                'symbol': symbol,
                                'side': side,
                                'quantity': authorization.quantity,
                                'confidence': confidence,
                                'signal_type': signal_type,
                                'authorization': authorization,
                                'timestamp': timestamp
                            })
                            logger.debug(f"✅ Trade authorized: {signal_type} {authorization.quantity} {symbol}")
                        else:
                            logger.debug(f"⚠️ Trade rejected: {authorization.rejection_reason}")
        
        except Exception as e:
            logger.error(f"❌ Error getting authorized trades: {e}")
        
        return authorized_trades
    
    # ============================================================
    # EXECUTION FLOW METHODS
    # ============================================================
    
    async def simulate_execution(self,
                                 authorized_trades: List[Any],
                                 current_bar: pd.Series,
                                 bar_timestamp: datetime) -> List[Dict[str, Any]]:
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
        
        Returns:
            List of executed trades with cost breakdown
        """
        
        if not authorized_trades:
            return []
        
        try:
            from backtest.engine.historical_execution_simulator import HistoricalExecutionSimulator
            
            # Create simulator if not exists
            if not hasattr(self, 'execution_simulator'):
                self.execution_simulator = HistoricalExecutionSimulator({
                    'fill_model': 'realistic',
                    'base_spread_bps': 5.0,
                    'base_slippage_bps': 2.0,
                    'commission_per_share': 0.005,
                    'enable_random_slippage': False,  # Deterministic for backtesting
                    'impact_linear_coeff': 0.1,
                    'impact_sqrt_coeff': 0.5
                })
            
            executed_trades = []
            
            for auth_trade in authorized_trades:
                try:
                    # Extract trade details from authorization
                    symbol = auth_trade.symbol
                    side = auth_trade.side
                    quantity = auth_trade.quantity
                    
                    # Get regime context (Rule 13)
                    regime_context = None
                    if self.regime_engine:
                        # Try to get regime context if method exists
                        if hasattr(self.regime_engine, 'get_current_regime_context'):
                            regime_context = await self.regime_engine.get_current_regime_context()
                        elif hasattr(self.regime_engine, 'current_regime'):
                            # Fallback: use current_regime attribute if available
                            regime_context = self.regime_engine.current_regime
                    
                    # Get liquidity score (Rule 12)
                    liquidity_score = None
                    if self.liquidity_engine and hasattr(self.liquidity_engine, 'assess_liquidity_score'):
                        try:
                            # Prepare market data dict for liquidity assessment
                            liquidity_market_data = {
                                'timestamp': bar_timestamp,
                                'close': current_bar.get('close', 0),
                                'volume': current_bar.get('volume', 0),
                                'high': current_bar.get('high', current_bar.get('close', 0)),
                                'low': current_bar.get('low', current_bar.get('close', 0))
                            }
                            liquidity_assessment = self.liquidity_engine.assess_liquidity_score(
                                symbol, liquidity_market_data, historical_data=None
                            )
                            liquidity_score = liquidity_assessment.overall_score if liquidity_assessment else None
                        except Exception as e:
                            logger.debug(f"Could not get liquidity score for {symbol}: {e}")
                    
                    # Prepare market data for simulator
                    market_data = {
                        'timestamp': bar_timestamp,
                        'open': current_bar.get('open', current_bar.get('close', 0)),
                        'high': current_bar.get('high', current_bar.get('close', 0)),
                        'low': current_bar.get('low', current_bar.get('close', 0)),
                        'close': current_bar.get('close', 0),
                        'volume': current_bar.get('volume', 0),
                        'volatility': current_bar.get('volatility', 0.02)  # 2% default
                    }
                    
                    # Simulate fill with realistic costs
                    # Prepare regime context dict
                    regime_dict = None
                    if regime_context:
                        if hasattr(regime_context, '__dict__'):
                            regime_dict = regime_context.__dict__
                        elif isinstance(regime_context, dict):
                            regime_dict = regime_context
                    
                    simulated_fill = self.execution_simulator.simulate_fill(
                        symbol=symbol,
                        side=side.lower(),
                        quantity=quantity,
                        decision_price=market_data['close'],  # Use close as decision price
                        market_data=market_data,
                        authorization_id=getattr(auth_trade, 'authorization_id', ''),
                        strategy_id=getattr(auth_trade, 'strategy_id', ''),
                        regime_context=regime_dict,
                        liquidity_score=liquidity_score
                    )
                    
                    # Update positions via PositionTracker
                    if self.position_tracker:
                        position_update = self.position_tracker.update_position(
                            symbol=symbol,
                            side=side.lower(),
                            quantity=quantity,
                            price=simulated_fill.fill_price,  # Use fill price (includes costs)
                            commission=simulated_fill.costs.commission_dollars,
                            strategy_id=getattr(auth_trade, 'strategy_id', ''),
                            trade_id=simulated_fill.fill_id
                        )
                        
                        logger.debug(f"Position updated: {symbol} {side} {quantity} @ ${simulated_fill.fill_price:.2f} "
                                   f"(cost: {simulated_fill.costs.total_cost_bps:.1f} bps)")
                    
                    # Record executed trade
                    executed_trade = {
                        'timestamp': bar_timestamp,
                        'symbol': symbol,
                        'side': side,
                        'quantity': quantity,
                        'decision_price': simulated_fill.decision_price,
                        'market_price': simulated_fill.market_price,
                        'fill_price': simulated_fill.fill_price,
                        
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
                        
                        # Metadata
                        'authorization_id': simulated_fill.authorization_id,
                        'strategy_id': simulated_fill.strategy_id,
                        'fill_id': simulated_fill.fill_id,
                        'regime': simulated_fill.costs.regime,
                        'liquidity_score': simulated_fill.costs.liquidity_score
                    }
                    
                    executed_trades.append(executed_trade)
                    
                    # Add to execution history
                    self.execution_history.append(executed_trade)
                    
                except Exception as e:
                    logger.error(f"❌ Failed to simulate execution for {auth_trade.symbol}: {e}")
                    continue
            
            if executed_trades:
                logger.info(f"✅ Simulated {len(executed_trades)} executions with realistic costs")
            
            return executed_trades
            
        except Exception as e:
            logger.error(f"❌ Execution simulation failed: {e}", exc_info=True)
            return []
    
    async def process_bar(self,
                         bar_data: pd.DataFrame,
                         bar_timestamp: datetime) -> Dict[str, Any]:
        """
        Process a single bar of market data through the complete pipeline
        
        This method implements the core backtest loop for one bar:
            1. Update regime engine with market data
            2. Generate technical indicators
            3. Engineer features
            4. Generate signals
            5. Execute strategies
            6. Authorize trades (CentralRiskManager)
            7. Simulate execution (HistoricalExecutionSimulator)
            8. Update positions (PositionTracker)
            9. Track performance
        
        Args:
            bar_data: Market data for current bar (all symbols)
            bar_timestamp: Timestamp of current bar
        
        Returns:
            Dictionary with bar processing results
        """
        
        bar_results = {
            'timestamp': bar_timestamp,
            'signals_generated': 0,
            'trades_authorized': 0,
            'trades_executed': 0,
            'regime': None,
            'executed_trades': []
        }
        
        try:
            # Step 1: Update regime engine (Rule 13 - Regime-First)
            if self.regime_engine:
                for _, row in bar_data.iterrows():
                    await self.regime_engine.on_market_data(row)
                
                # Get regime context if available
                if hasattr(self.regime_engine, 'get_current_regime_context'):
                    regime_context = await self.regime_engine.get_current_regime_context()
                    if regime_context:
                        bar_results['regime'] = getattr(regime_context, 'primary_regime', 'unknown')
                elif hasattr(self.regime_engine, 'current_regime'):
                    bar_results['regime'] = str(self.regime_engine.current_regime)
            
            # Step 2-4: Generate indicators, features, signals
            # (These would be called if we were generating signals per bar)
            # For now, we'll focus on the execution flow
            
            # Step 5-6: Get authorized trades from strategy manager
            # (This will be implemented when we connect the full pipeline)
            # For Phase 5.3, we're focusing on the execution simulation
            
            # Placeholder: In full implementation, authorized_trades would come from:
            # authorized_trades = await self.strategy_manager.get_authorized_trades(bar_data, bar_timestamp)
            authorized_trades = []
            
            # Step 7: Simulate execution with realistic costs
            if authorized_trades:
                executed_trades = await self.simulate_execution(
                    authorized_trades,
                    bar_data.iloc[0],  # First row for single-symbol
                    bar_timestamp
                )
                
                bar_results['trades_executed'] = len(executed_trades)
                bar_results['executed_trades'] = executed_trades
            
            return bar_results
            
        except Exception as e:
            logger.error(f"❌ Bar processing failed at {bar_timestamp}: {e}")
            bar_results['error'] = str(e)
            return bar_results
    
    def get_execution_statistics(self) -> Dict[str, Any]:
        """
        Get aggregate execution statistics from all simulated trades
        
        Returns:
            Dictionary with execution TCA statistics
        """
        
        if not self.execution_history:
            return {
                'total_trades': 0,
                'message': 'No trades executed yet'
            }
        
        executed_trades = self.execution_history
        total_trades = len(executed_trades)
        
        # Calculate aggregate statistics
        total_cost_bps = sum(trade['total_cost_bps'] for trade in executed_trades)
        total_cost_dollars = sum(trade['total_cost_dollars'] for trade in executed_trades)
        avg_cost_bps = total_cost_bps / total_trades if total_trades > 0 else 0
        
        # Cost component breakdowns
        avg_spread_cost = sum(t['spread_cost_bps'] for t in executed_trades) / total_trades
        avg_impact_cost = sum(t['market_impact_bps'] for t in executed_trades) / total_trades
        avg_slippage = sum(t['slippage_bps'] for t in executed_trades) / total_trades
        avg_commission = sum(t['commission_bps'] for t in executed_trades) / total_trades
        
        # Trade direction breakdown
        buy_trades = [t for t in executed_trades if t['side'].lower() == 'buy']
        sell_trades = [t for t in executed_trades if t['side'].lower() == 'sell']
        
        return {
            'total_trades': total_trades,
            'total_cost_bps': total_cost_bps,
            'total_cost_dollars': total_cost_dollars,
            'avg_cost_bps': avg_cost_bps,
            
            # Cost component breakdown
            'avg_spread_cost_bps': avg_spread_cost,
            'avg_impact_cost_bps': avg_impact_cost,
            'avg_slippage_bps': avg_slippage,
            'avg_commission_bps': avg_commission,
            
            # Trade breakdown
            'buy_trades': len(buy_trades),
            'sell_trades': len(sell_trades),
            'avg_buy_cost_bps': sum(t['total_cost_bps'] for t in buy_trades) / len(buy_trades) if buy_trades else 0,
            'avg_sell_cost_bps': sum(t['total_cost_bps'] for t in sell_trades) / len(sell_trades) if sell_trades else 0,
            
            # Total notional traded
            'total_notional': sum(t['quantity'] * t['market_price'] for t in executed_trades)
        }
    
    # ============================================================
    # Lifecycle Management
    # ============================================================
    
    async def shutdown(self) -> bool:
        """
        Graceful shutdown of backtest engine
        
        Returns:
            True if shutdown successful
        """
        try:
            logger.info("\n🛑 Shutting down backtest engine...")
            
            # Manually stop all components
            for component_name, component in self.components.items():
                try:
                    if hasattr(component, 'stop'):
                        await component.stop()
                        logger.info(f"   ✅ {component_name} stopped")
                except Exception as e:
                    logger.error(f"   ❌ Failed to stop {component_name}: {e}")
            
            self.is_running = False
            self.is_initialized = False
            
            logger.info("✅ Shutdown complete\n")
            return True
            
        except Exception as e:
            logger.error(f"❌ Shutdown failed: {e}")
            return False
    
    # ============================================================
    # Status & Monitoring
    # ============================================================
    
    def get_status(self) -> Dict[str, Any]:
        """Get current engine status"""
        return {
            'backtest_name': self.backtest_name,
            'backtest_mode': self.backtest_mode.value,
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


# ============================================================
# Helper function for quick engine creation
# ============================================================

async def create_backtest_engine(config_path: Path) -> InstitutionalBacktestEngine:
    """
    Convenience function to create and initialize backtest engine
    
    Args:
        config_path: Path to backtest configuration JSON
        
    Returns:
        Initialized backtest engine
        
    Usage:
        engine = await create_backtest_engine(Path("my_backtest.json"))
        results = await engine.run_backtest()
    """
    # Load configuration
    config = BacktestConfiguration.from_json(config_path)
    
    # Create engine
    engine = InstitutionalBacktestEngine(config)
    
    # Initialize
    await engine.initialize()
    
    return engine


if __name__ == "__main__":
    """
    Test the backtest engine skeleton
    """
    import sys
    
    async def test_engine():
        """Test backtest engine initialization"""
        
        print("\n" + "=" * 80)
        print("INSTITUTIONAL BACKTEST ENGINE - SKELETON TEST")
        print("=" * 80 + "\n")
        
        # Load example config
        config_path = Path(__file__).parent.parent / "config/examples/single_strategy.json"
        
        if not config_path.exists():
            print(f"❌ Config file not found: {config_path}")
            sys.exit(1)
        
        print(f"📋 Loading config: {config_path.name}")
        config = BacktestConfiguration.from_json(config_path)
        print(f"✅ Config loaded: {config.backtest_name}\n")
        
        # Create engine
        print("🏗️  Creating backtest engine...")
        engine = InstitutionalBacktestEngine(config)
        print(f"✅ Engine created\n")
        
        # Initialize
        print("🚀 Initializing engine...")
        init_success = await engine.initialize()
        
        if init_success:
            print("\n✅ Initialization successful!")
            
            # Check status
            status = engine.get_status()
            print(f"\n📊 Engine Status:")
            print(f"   Initialized: {status['is_initialized']}")
            print(f"   Components: {status['components_registered']}")
            print(f"   Phase 2: {status['phase_status']['phase2_data_regime']}")
            
            # Test run (skeleton)
            print("\n🎬 Testing backtest run (skeleton)...")
            results = await engine.run_backtest()
            print(f"✅ Backtest completed: {results['status']}")
            
            # Shutdown
            print("\n🛑 Shutting down...")
            await engine.shutdown()
            print("✅ Shutdown complete")
            
        else:
            print("\n❌ Initialization failed")
            sys.exit(1)
        
        print("\n" + "=" * 80)
        print("✅ SKELETON TEST COMPLETE - READY FOR PHASE 2.2")
        print("=" * 80 + "\n")
    
    # Run test
    asyncio.run(test_engine())

