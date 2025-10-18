# Institutional Backtest "Lego Brick" Assembly Guide
## Detailed Component-by-Component Integration Plan

**Created**: January 15, 2025  
**Purpose**: Map each core_engine "Lego Brick" to backtest application components  
**Framework**: institutional-backtest-workflow.mdc + 13 Rules  

---

## 🧱 Available "Lego Bricks" (Core Engine Components)

### Inventory of All Core Engine Components

```
core_engine/ (The "Lego Brick Factory")
│
├── 🔴 Layer 0: Regime Detection (Rule 13 - Foundation)
│   └── regime/engine.py
│       └── EnhancedRegimeEngine (initialization_order=5)
│           ├── on_market_data() → RegimeContext
│           ├── get_current_regime() → RegimeAnalysis
│           ├── subscribe_to_regime_changes()
│           └── analyze_regime_history() → Historical regimes
│
├── 🟢 Layer 1: System Orchestration
│   └── system/
│       ├── hierarchical_orchestrator.py
│       │   └── HierarchicalSystemOrchestrator
│       │       ├── register_component(name, component, layer, order)
│       │       ├── initialize_all_components()
│       │       ├── start_all_components()
│       │       └── stop_all_components()
│       └── integration_manager.py
│           └── SystemIntegrationManager (multi-phase init)
│
├── 🟡 Layer 2: Governance (Rule 4)
│   └── system/central_risk_manager.py
│       └── CentralRiskManager (initialization_order=25)
│           ├── authorize_trading_decision() → Authorization
│           ├── update_position() → Position state
│           ├── get_risk_metrics() → Risk analytics
│           ├── set_regime_engine() ← Regime injection
│           └── on_regime_change() ← Regime callback
│
├── 🔵 Layer 3: Data Management (Rule 3)
│   └── data/
│       ├── manager.py
│       │   └── ClickHouseDataManager (initialization_order=10)
│       │       ├── load_market_data() → Historical DataFrame
│       │       ├── get_historical_bars() → Bar data
│       │       ├── set_regime_engine() ← Regime injection
│       │       └── on_regime_change() ← Regime callback
│       └── liquidity_engine.py (Rule 12)
│           └── LiquidityAssessmentEngine (initialization_order=12)
│               ├── assess_liquidity_score() → LiquidityScore
│               ├── get_liquidity_regime() → Regime
│               └── filter_by_liquidity() → Filtered signals
│
├── 🟣 Layer 4: Core Processing Pipeline
│   └── processing/
│       ├── indicators/engine.py
│       │   └── EnhancedTechnicalIndicators (initialization_order=15)
│       │       ├── calculate_indicators() → DataFrame with indicators
│       │       ├── set_regime_engine() ← Regime injection
│       │       └── on_regime_change() ← Regime-adaptive params
│       ├── features/engineer.py
│       │   └── EnhancedFeatureEngineer (initialization_order=16)
│       │       ├── create_features() → ML-ready features
│       │       ├── set_regime_engine() ← Regime injection
│       │       └── on_regime_change() ← Regime-aware features
│       └── signals/generator.py
│           └── EnhancedSignalGenerator (initialization_order=17)
│               ├── generate_signals() → Trading signals
│               ├── set_regime_engine() ← Regime injection
│               ├── on_regime_change() ← Regime-filtered signals
│               └── filter_by_liquidity() → Liquidity-constrained
│
├── 🟠 Layer 5: Strategy & Analytics
│   ├── trading/strategies/
│   │   ├── manager.py
│   │   │   └── StrategyManager (initialization_order=20)
│   │   │       ├── register_enhanced_strategy() → Register
│   │   │       ├── execute_strategies() → Strategy signals
│   │   │       ├── aggregate_signals() → Multi-strategy
│   │   │       ├── set_regime_engine() ← Regime injection
│   │   │       └── on_regime_change() ← Dynamic weighting
│   │   └── implementations/
│   │       ├── enhanced_momentum.py
│   │       ├── enhanced_mean_reversion.py
│   │       ├── enhanced_statistical_arbitrage.py
│   │       └── ... (7 more strategies)
│   └── analytics/
│       ├── metrics_calculator.py
│       │   └── EnhancedMetricsCalculator (initialization_order=32)
│       │       ├── calculate_metrics() → Performance metrics
│       │       ├── calculate_regime_metrics() → Regime stats
│       │       └── set_regime_engine() ← Regime injection
│       ├── performance_analyzer.py
│       │   └── PerformanceAnalyzer (initialization_order=33)
│       │       ├── analyze_performance() → Complete analysis
│       │       ├── calculate_regime_attribution() → Attribution
│       │       ├── generate_report() → Report dict
│       │       └── set_regime_engine() ← Regime injection
│       └── manager_enhanced.py
│           └── EnhancedAnalyticsManager (initialization_order=35)
│               ├── process_trade_result() → Update analytics
│               ├── get_analytics_summary() → Summary
│               └── set_regime_engine() ← Regime injection
│
└── ⚫ Layer 6: Trading & Execution
    ├── trading/engine.py
    │   └── EnhancedTradingEngine (initialization_order=30)
    │       ├── create_execution_plan() → Execution plan
    │       ├── optimize_execution() → Order optimization
    │       ├── set_regime_engine() ← Regime injection
    │       └── on_regime_change() ← Regime-optimized execution
    └── system/unified_execution_engine.py
        └── UnifiedExecutionEngine (initialization_order=40)
            ├── execute_authorized_trade() → ExecutionResult
            ├── simulate_fill() → Fill simulation (backtest)
            ├── apply_execution_costs() → Realistic costs
            └── set_regime_engine() ← Regime injection
```

---

## 🏗️ Backtest Application Architecture Using Lego Bricks

### Application Structure
```
backtest/ (New application - uses core_engine bricks)
│
├── config/
│   ├── backtest_config.py
│   │   └── BacktestConfiguration
│   │       ├── DataConfig → Configures ClickHouseDataManager
│   │       ├── StrategyConfig[] → Configures StrategyManager
│   │       ├── RiskConfig → Configures CentralRiskManager
│   │       ├── ExecutionConfig → Configures UnifiedExecutionEngine
│   │       └── AnalyticsConfig → Configures AnalyticsManager
│   └── examples/
│       └── *.json (example configurations)
│
├── engine/
│   ├── institutional_backtest_engine.py
│   │   └── InstitutionalBacktestEngine
│   │       ├── Uses: ALL 9 core_engine components
│   │       ├── Orchestrates: Component initialization (order 5→40)
│   │       ├── Executes: Main backtest loop
│   │       └── Coordinates: Data flow through components
│   │
│   ├── backtest_orchestrator.py
│   │   └── BacktestOrchestrator
│   │       ├── Uses: HierarchicalSystemOrchestrator
│   │       ├── Registers: All 9 components with correct orders
│   │       └── Injects: Regime engine into all components
│   │
│   ├── historical_execution_simulator.py
│   │   └── HistoricalExecutionSimulator
│   │       ├── Uses: UnifiedExecutionEngine
│   │       ├── Simulates: Realistic fills (Rule 12)
│   │       └── Applies: Spread + Impact + Slippage costs
│   │
│   └── position_tracker.py
│       └── PositionTracker
│           ├── Uses: CentralRiskManager callbacks
│           ├── Tracks: Positions, cash, P&L
│           └── Validates: Risk limits
│
├── reporting/
│   └── performance_reporter.py
│       └── PerformanceReporter
│           ├── Uses: PerformanceAnalyzer
│           ├── Uses: EnhancedMetricsCalculator
│           ├── Uses: EnhancedAnalyticsManager
│           └── Generates: HTML/JSON reports
│
└── cli/
    └── backtest_cli.py
        └── CLI interface
            ├── Loads: BacktestConfiguration
            ├── Creates: InstitutionalBacktestEngine
            └── Runs: Complete backtest workflow
```

---

## 📋 Detailed Lego Brick Integration Plan

### PHASE 0: Foundation - Regime Engine (Rule 13)

#### Brick: `EnhancedRegimeEngine`
**Location**: `core_engine/regime/engine.py`  
**Used By**: `InstitutionalBacktestEngine.initialize()`  
**Initialization Order**: **5 (FIRST)**

```python
# In backtest/engine/institutional_backtest_engine.py

async def initialize(self):
    """Initialize all components - REGIME FIRST"""
    
    # ═══════════════════════════════════════════════════════════
    # BRICK #1: EnhancedRegimeEngine (Rule 13 - Foundation Layer)
    # ═══════════════════════════════════════════════════════════
    
    logger.info("🔴 BRICK #1: EnhancedRegimeEngine (order=5)")
    
    # Create regime engine with config
    from core_engine.regime.engine import EnhancedRegimeEngine
    
    self.components['regime_engine'] = EnhancedRegimeEngine({
        'lookback_window': 60,
        'volatility_window': 20,
        'trend_threshold': 0.02,
        'regime_change_threshold': 0.7,
        'enable_enhanced_detection': True,
        'enable_multi_timeframe_analysis': True,
        'enable_ml_based_prediction': True
    })
    
    # Register with orchestrator (order=5 ensures it initializes FIRST)
    self.orchestrator.register_component(
        name="EnhancedRegimeEngine",
        component=self.components['regime_engine'],
        layer=ComponentLayer.SUPPORT,
        authority_level=AuthorityLevel.OPERATIONAL,
        initialization_order=5  # 🔥 LOWEST = FIRST
    )
    
    # Initialize and start
    await self.components['regime_engine'].initialize()
    await self.components['regime_engine'].start()
    
    logger.info("   ✅ RegimeEngine initialized - Foundation ready")
    
    # This component provides:
    # - on_market_data(row) → RegimeContext for each bar
    # - get_current_regime() → Current regime classification
    # - subscribe_to_regime_changes(callback) → Notify other components
    # - analyze_regime_history() → Historical regime distribution
```

**What this brick gives us**:
- ✅ Market regime classification (bull/bear/sideways/volatile/crisis)
- ✅ Volatility regime (low/normal/high/extreme)
- ✅ Liquidity regime (high/normal/low/crisis)
- ✅ Regime transition detection
- ✅ Regime history for attribution

**How it's used in backtest**:
1. **Initialization**: Called FIRST (order=5)
2. **Per-bar processing**: `on_market_data(row)` for each historical bar
3. **Component injection**: Injected into all 8+ other components
4. **Regime callbacks**: All components subscribe to regime changes
5. **Post-backtest**: Regime history used for attribution analysis

---

### PHASE 1: Data Management (Rule 3)

#### Brick: `ClickHouseDataManager`
**Location**: `core_engine/data/manager.py`  
**Used By**: `InstitutionalBacktestEngine.initialize()`, `_load_historical_data()`  
**Initialization Order**: **10**

```python
# In backtest/engine/institutional_backtest_engine.py

async def initialize(self):
    # ... RegimeEngine initialized above ...
    
    # ═══════════════════════════════════════════════════════════
    # BRICK #2: ClickHouseDataManager (Rule 3 - Data Authority)
    # ═══════════════════════════════════════════════════════════
    
    logger.info("🔵 BRICK #2: ClickHouseDataManager (order=10)")
    
    from core_engine.data.manager import (
        ClickHouseDataManager, ClickHouseDataConfig
    )
    
    # Create data config from backtest config
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
    
    self.components['data_manager'] = ClickHouseDataManager(data_config)
    
    # 🔥 INJECT REGIME ENGINE (Rule 13)
    self.components['data_manager'].set_regime_engine(
        self.components['regime_engine']
    )
    
    # Subscribe data manager to regime changes
    self.components['regime_engine'].subscribe_to_regime_changes(
        self.components['data_manager'].on_regime_change
    )
    
    # Register with orchestrator
    self.orchestrator.register_component(
        name="ClickHouseDataManager",
        component=self.components['data_manager'],
        layer=ComponentLayer.SUPPORT,
        authority_level=AuthorityLevel.OPERATIONAL,
        initialization_order=10  # After regime (5)
    )
    
    logger.info("   ✅ DataManager initialized with regime awareness")
    
    # This component provides:
    # - load_market_data() → Complete historical DataFrame
    # - get_historical_bars() → Iterator for bar-by-bar processing
    # - validate_data_quality() → Data completeness checks

async def _load_historical_data(self) -> pd.DataFrame:
    """Load all historical data for backtest"""
    
    logger.info(f"📊 Loading historical data...")
    logger.info(f"   Symbols: {', '.join(self.config.data.symbols)}")
    logger.info(f"   Period: {self.config.data.start_date} to {self.config.data.end_date}")
    logger.info(f"   Interval: {self.config.data.interval}")
    
    # Use BRICK #2: ClickHouseDataManager
    market_data = self.components['data_manager'].load_market_data(
        symbols=self.config.data.symbols,
        start_time=datetime.strptime(self.config.data.start_date, "%Y-%m-%d"),
        end_time=datetime.strptime(self.config.data.end_date, "%Y-%m-%d"),
        interval=self.config.data.interval
    )
    
    # Validate data quality
    validation = self.components['data_manager'].validate_data_quality(market_data)
    if not validation['valid']:
        raise ValueError(f"Data quality issues: {validation['errors']}")
    
    logger.info(f"   ✅ Loaded {len(market_data):,} bars")
    logger.info(f"   ✅ Data quality: {validation['quality_score']:.1f}/100")
    
    return market_data
```

**What this brick gives us**:
- ✅ Historical market data from ClickHouse
- ✅ Data validation and quality checks
- ✅ Efficient data loading with caching
- ✅ Regime-tagged data (via injection)

**How it's used in backtest**:
1. **Initialization**: Loads historical data once
2. **Validation**: Checks data completeness/quality
3. **Iteration**: Provides bar-by-bar iterator
4. **Regime awareness**: Tags data with regime context

---

#### Brick: `LiquidityAssessmentEngine`
**Location**: `core_engine/data/liquidity_engine.py`  
**Used By**: `InstitutionalBacktestEngine._assess_liquidity()`, `_filter_signals_by_liquidity()`  
**Initialization Order**: **12**

```python
# In backtest/engine/institutional_backtest_engine.py

async def initialize(self):
    # ... RegimeEngine, DataManager initialized above ...
    
    # ═══════════════════════════════════════════════════════════
    # BRICK #3: LiquidityAssessmentEngine (Rule 12 - Liquidity)
    # ═══════════════════════════════════════════════════════════
    
    logger.info("🟢 BRICK #3: LiquidityAssessmentEngine (order=12)")
    
    from core_engine.data.liquidity_engine import (
        LiquidityAssessmentEngine, HistoricalLiquidityConfig
    )
    
    # Create liquidity config from backtest config
    liquidity_config = HistoricalLiquidityConfig(
        enable_historical_liquidity=True,
        enable_liquidity_filtering=self.config.execution.enable_liquidity_filtering,
        liquidity_thresholds={
            'min_daily_volume': 100_000,
            'max_spread_bps': self.config.execution.max_spread_bps,
            'min_depth': 50_000,
            'max_impact_bps': 30
        },
        skip_illiquid_trades=True,
        reduce_size_on_low_liquidity=True,
        liquidity_reduction_factor=0.5
    )
    
    self.components['liquidity_engine'] = LiquidityAssessmentEngine(liquidity_config)
    
    # 🔥 INJECT REGIME ENGINE (Rule 13)
    self.components['liquidity_engine'].set_regime_engine(
        self.components['regime_engine']
    )
    
    # Register with orchestrator
    self.orchestrator.register_component(
        name="LiquidityAssessmentEngine",
        component=self.components['liquidity_engine'],
        layer=ComponentLayer.SUPPORT,
        authority_level=AuthorityLevel.OPERATIONAL,
        initialization_order=12  # After data (10), before processing (15)
    )
    
    logger.info("   ✅ LiquidityEngine initialized with regime awareness")
    
    # This component provides:
    # - assess_liquidity_score() → LiquidityScore (0-100)
    # - get_liquidity_regime() → Liquidity classification
    # - filter_signals_by_liquidity() → Filtered signal list

async def _filter_signals_by_liquidity(self, signals: List[Signal]) -> List[Signal]:
    """Filter signals based on liquidity constraints (Rule 12)"""
    
    if not self.config.execution.enable_liquidity_filtering:
        return signals
    
    filtered_signals = []
    filtered_out = 0
    
    for signal in signals:
        # Use BRICK #3: LiquidityAssessmentEngine
        liquidity_score = await self.components['liquidity_engine'].assess_liquidity_score(
            symbol=signal.symbol,
            quantity=signal.target_quantity,
            historical_data=signal.market_data  # Historical liquidity context
        )
        
        # Filter by minimum liquidity score
        if liquidity_score.overall_score >= self.config.execution.min_liquidity_score:
            # Estimate market impact
            from core_engine.liquidity.impact import MarketImpactModel
            
            impact_estimate = await self.impact_model.estimate_market_impact(
                symbol=signal.symbol,
                quantity=signal.target_quantity,
                side=signal.signal_type.value,
                urgency='normal'
            )
            
            # Accept if impact is acceptable
            if impact_estimate.total_impact_bps < 30:  # Max 30 bps
                signal.metadata['liquidity_score'] = liquidity_score.overall_score
                signal.metadata['estimated_impact_bps'] = impact_estimate.total_impact_bps
                filtered_signals.append(signal)
            else:
                filtered_out += 1
                self.signals_filtered += 1
        else:
            filtered_out += 1
            self.signals_filtered += 1
    
    logger.info(f"   🔍 Liquidity filtering: {len(signals)} → {len(filtered_signals)} "
               f"({filtered_out} filtered)")
    
    return filtered_signals
```

**What this brick gives us**:
- ✅ Historical liquidity scoring (0-100)
- ✅ Liquidity regime classification
- ✅ Signal filtering by liquidity
- ✅ Trade size adjustment for low liquidity

**How it's used in backtest**:
1. **Signal filtering**: Filters signals before risk authorization
2. **Size adjustment**: Reduces order size in low liquidity
3. **Skip illiquid**: Skips trades in illiquid conditions
4. **Regime-aware**: Adapts thresholds to regime

---

### PHASE 2: Processing Pipeline (Rules 3, 13)

#### Brick: `EnhancedTechnicalIndicators`
**Location**: `core_engine/processing/indicators/engine.py`  
**Used By**: `InstitutionalBacktestEngine._process_signals()`  
**Initialization Order**: **15**

```python
# In backtest/engine/institutional_backtest_engine.py

async def initialize(self):
    # ... Previous bricks initialized ...
    
    # ═══════════════════════════════════════════════════════════
    # BRICK #4: EnhancedTechnicalIndicators (Rule 3 - Processing)
    # ═══════════════════════════════════════════════════════════
    
    logger.info("🟣 BRICK #4: EnhancedTechnicalIndicators (order=15)")
    
    from core_engine.processing.indicators.engine import EnhancedTechnicalIndicators
    
    self.components['indicators_engine'] = EnhancedTechnicalIndicators({
        'enable_trend_indicators': True,
        'enable_momentum_indicators': True,
        'enable_volatility_indicators': True,
        'enable_volume_indicators': True,
        'enable_regime_adaptive': True
    })
    
    # 🔥 INJECT REGIME ENGINE (Rule 13)
    self.components['indicators_engine'].set_regime_engine(
        self.components['regime_engine']
    )
    
    # Subscribe to regime changes for adaptive parameters
    self.components['regime_engine'].subscribe_to_regime_changes(
        self.components['indicators_engine'].on_regime_change
    )
    
    # Register with orchestrator
    self.orchestrator.register_component(
        name="EnhancedTechnicalIndicators",
        component=self.components['indicators_engine'],
        layer=ComponentLayer.SUPPORT,
        authority_level=AuthorityLevel.OPERATIONAL,
        initialization_order=15  # After liquidity (12)
    )
    
    logger.info("   ✅ IndicatorsEngine initialized with regime adaptation")
    
    # This component provides:
    # - calculate_indicators() → DataFrame with technical indicators
    # - Regime-adaptive parameters (e.g., longer MAs in volatile regimes)

async def _process_signals(self, market_update: Dict, liquidity_score: float):
    """Process signals using complete pipeline"""
    
    # STEP 1: Use BRICK #4 - Calculate technical indicators
    indicators_df = self.components['indicators_engine'].calculate_indicators(
        self.current_market_data  # Last N bars for indicator calculation
    )
    
    # STEP 2: Use BRICK #5 - Engineer features
    # STEP 3: Use BRICK #6 - Generate signals
    # (shown in next sections)
```

**What this brick gives us**:
- ✅ Technical indicators (SMA, EMA, RSI, MACD, Bollinger Bands, ATR, etc.)
- ✅ Regime-adaptive indicator parameters
- ✅ Volume-based indicators
- ✅ Volatility indicators

**How it's used in backtest**:
1. **Per-signal-period**: Calculate indicators for current window
2. **Regime-adaptive**: Adjust parameters based on regime
3. **Feature input**: Provides indicators to feature engineer

---

#### Brick: `EnhancedFeatureEngineer`
**Location**: `core_engine/processing/features/engineer.py`  
**Used By**: `InstitutionalBacktestEngine._process_signals()`  
**Initialization Order**: **16**

```python
# Continuing _process_signals() method...

async def initialize(self):
    # ... Previous bricks ...
    
    # ═══════════════════════════════════════════════════════════
    # BRICK #5: EnhancedFeatureEngineer (Rule 3 - Features)
    # ═══════════════════════════════════════════════════════════
    
    logger.info("🟣 BRICK #5: EnhancedFeatureEngineer (order=16)")
    
    from core_engine.processing.features.engineer import EnhancedFeatureEngineer
    
    self.components['feature_engineer'] = EnhancedFeatureEngineer({
        'enable_statistical_features': True,
        'enable_technical_features': True,
        'enable_regime_features': True,
        'lookback_window': 60
    })
    
    # 🔥 INJECT REGIME ENGINE (Rule 13)
    self.components['feature_engineer'].set_regime_engine(
        self.components['regime_engine']
    )
    
    self.components['regime_engine'].subscribe_to_regime_changes(
        self.components['feature_engineer'].on_regime_change
    )
    
    self.orchestrator.register_component(
        name="EnhancedFeatureEngineer",
        component=self.components['feature_engineer'],
        layer=ComponentLayer.SUPPORT,
        initialization_order=16  # After indicators (15)
    )
    
    logger.info("   ✅ FeatureEngineer initialized")

async def _process_signals(self, market_update: Dict, liquidity_score: float):
    # STEP 1: Calculate indicators (shown above)
    indicators_df = self.components['indicators_engine'].calculate_indicators(...)
    
    # STEP 2: Use BRICK #5 - Engineer ML-ready features
    features_df = self.components['feature_engineer'].create_features(
        indicators_df
    )
    
    # STEP 3: Use BRICK #6 - Generate signals (next)
```

**What this brick gives us**:
- ✅ ML-ready features from indicators
- ✅ Statistical features (z-scores, rankings, etc.)
- ✅ Regime-aware features
- ✅ Normalized features

**How it's used in backtest**:
1. **Feature creation**: Transforms indicators into ML features
2. **Regime features**: Adds regime context as features
3. **Signal input**: Provides features to signal generator

---

#### Brick: `EnhancedSignalGenerator`
**Location**: `core_engine/processing/signals/generator.py`  
**Used By**: `InstitutionalBacktestEngine._process_signals()`  
**Initialization Order**: **17**

```python
async def initialize(self):
    # ... Previous bricks ...
    
    # ═══════════════════════════════════════════════════════════
    # BRICK #6: EnhancedSignalGenerator (Rule 3 - Signals)
    # ═══════════════════════════════════════════════════════════
    
    logger.info("🟣 BRICK #6: EnhancedSignalGenerator (order=17)")
    
    from core_engine.processing.signals.generator import EnhancedSignalGenerator
    
    self.components['signal_generator'] = EnhancedSignalGenerator({
        'min_confidence_threshold': self.config.risk.min_signal_confidence,
        'enable_regime_filtering': True,
        'enable_multi_signal': True
    })
    
    # 🔥 INJECT REGIME ENGINE (Rule 13)
    self.components['signal_generator'].set_regime_engine(
        self.components['regime_engine']
    )
    
    self.components['regime_engine'].subscribe_to_regime_changes(
        self.components['signal_generator'].on_regime_change
    )
    
    self.orchestrator.register_component(
        name="EnhancedSignalGenerator",
        component=self.components['signal_generator'],
        layer=ComponentLayer.SUPPORT,
        initialization_order=17  # After features (16)
    )
    
    logger.info("   ✅ SignalGenerator initialized")

async def _process_signals(self, market_update: Dict, liquidity_score: float):
    # STEP 1: Calculate indicators
    indicators_df = self.components['indicators_engine'].calculate_indicators(...)
    
    # STEP 2: Engineer features
    features_df = self.components['feature_engineer'].create_features(indicators_df)
    
    # STEP 3: Use BRICK #6 - Generate trading signals
    raw_signals = self.components['signal_generator'].generate_signals(features_df)
    
    self.signals_generated += len(raw_signals)
    
    # STEP 4: Filter signals by liquidity (using BRICK #3)
    filtered_signals = await self._filter_signals_by_liquidity(raw_signals)
    
    # STEP 5: Process through multi-strategy aggregation (next phase)
```

**What this brick gives us**:
- ✅ Trading signals (BUY/SELL/HOLD)
- ✅ Signal confidence scores
- ✅ Regime-filtered signals
- ✅ Multi-signal support

**How it's used in backtest**:
1. **Signal generation**: Creates trading signals from features
2. **Regime filtering**: Filters signals inappropriate for regime
3. **Confidence scoring**: Assigns confidence to each signal
4. **Strategy input**: Signals fed to strategy manager

---

### PHASE 3: Strategy Management (Rule 8)

#### Brick: `StrategyManager` + Enhanced Strategies
**Location**: `core_engine/trading/strategies/manager.py`  
**Used By**: `InstitutionalBacktestEngine._execute_strategies()`  
**Initialization Order**: **20**

```python
async def initialize(self):
    # ... Previous bricks ...
    
    # ═══════════════════════════════════════════════════════════
    # BRICK #7: StrategyManager + Enhanced Strategies (Rule 8)
    # ═══════════════════════════════════════════════════════════
    
    logger.info("🟠 BRICK #7: StrategyManager (order=20)")
    
    from core_engine.trading.strategies.manager import (
        StrategyManager, EnhancedStrategyFactory
    )
    from core_engine.type_definitions.strategy import StrategyType
    
    self.components['strategy_manager'] = StrategyManager({
        'enable_enhanced_strategies': True,
        'auto_discover_strategies': True,
        'max_concurrent_strategies': 10,
        'enable_signal_aggregation': True,
        'enable_conflict_resolution': True,
        'enable_strategy_attribution': True
    })
    
    # 🔥 INJECT REGIME ENGINE (Rule 13)
    self.components['strategy_manager'].set_regime_engine(
        self.components['regime_engine']
    )
    
    self.components['regime_engine'].subscribe_to_regime_changes(
        self.components['strategy_manager'].on_regime_change
    )
    
    # Register strategies from backtest config
    factory = EnhancedStrategyFactory()
    
    for strategy_config in self.config.strategies:
        # Map strategy_type string to StrategyType enum
        strategy_type = StrategyType[strategy_config.strategy_type.upper()]
        
        # Register enhanced strategy
        success = await self.components['strategy_manager'].register_enhanced_strategy(
            strategy_type=strategy_type,
            config={
                'name': strategy_config.strategy_name,
                'allocation_pct': strategy_config.allocation_pct,
                **strategy_config.parameters
            }
        )
        
        if success:
            logger.info(f"   ✅ Registered strategy: {strategy_config.strategy_name}")
    
    self.orchestrator.register_component(
        name="StrategyManager",
        component=self.components['strategy_manager'],
        layer=ComponentLayer.EXECUTION,
        initialization_order=20  # After processing pipeline (17)
    )
    
    logger.info(f"   ✅ StrategyManager initialized with {len(self.config.strategies)} strategies")
    
    # This component provides:
    # - execute_strategies() → Execute all registered strategies
    # - aggregate_signals() → Multi-strategy signal aggregation
    # - resolve_conflicts() → Signal conflict resolution
    # - get_strategy_performance() → Per-strategy attribution

async def _execute_strategies(self, filtered_signals: List[Signal]) -> List[Signal]:
    """Execute multi-strategy coordination (Rule 8)"""
    
    # Use BRICK #7: StrategyManager
    
    # Execute all registered strategies
    strategy_signals = await self.components['strategy_manager'].execute_strategies(
        market_data=self.current_market_data,
        signals=filtered_signals  # Pre-filtered by liquidity
    )
    
    # Aggregate signals from multiple strategies
    aggregated_signals = await self.components['strategy_manager'].aggregate_signals(
        strategy_signals
    )
    
    logger.info(f"   🎯 Strategy execution: {len(strategy_signals)} → {len(aggregated_signals)} aggregated signals")
    
    return aggregated_signals
```

**What this brick gives us**:
- ✅ Multi-strategy coordination
- ✅ Signal aggregation (weighted by confidence)
- ✅ Conflict resolution (when strategies disagree)
- ✅ Dynamic strategy weighting based on regime
- ✅ Per-strategy performance attribution
- ✅ 10 enhanced strategy implementations

**How it's used in backtest**:
1. **Strategy registration**: Register strategies from config
2. **Strategy execution**: Run all strategies on current data
3. **Signal aggregation**: Combine signals from multiple strategies
4. **Regime weighting**: Adjust strategy weights by regime
5. **Performance tracking**: Track per-strategy returns

---

### PHASE 4: Risk Management & Governance (Rule 4)

#### Brick: `CentralRiskManager`
**Location**: `core_engine/system/central_risk_manager.py`  
**Used By**: `InstitutionalBacktestEngine._authorize_trades()`  
**Initialization Order**: **25**

```python
async def initialize(self):
    # ... Previous bricks ...
    
    # ═══════════════════════════════════════════════════════════
    # BRICK #8: CentralRiskManager (Rule 4 - GOVERNANCE)
    # ═══════════════════════════════════════════════════════════
    
    logger.info("🟡 BRICK #8: CentralRiskManager (order=25)")
    
    from core_engine.system.central_risk_manager import (
        CentralRiskManager, RiskManagerConfig
    )
    
    risk_config = RiskManagerConfig(
        max_position_size=self.config.risk.max_position_size,
        max_daily_var=self.config.risk.max_daily_var,
        position_concentration_limit=self.config.risk.max_concentration,
        strategy_allocation_limit=1.0 / max(1, len(self.config.strategies)),
        min_signal_confidence=self.config.risk.min_signal_confidence,
        initial_capital=self.config.risk.initial_capital,
        enable_regime_adjustments=self.config.risk.enable_regime_adjustments
    )
    
    self.components['risk_manager'] = CentralRiskManager(risk_config)
    
    # 🔥 INJECT REGIME ENGINE (Rule 13)
    self.components['risk_manager'].set_regime_engine(
        self.components['regime_engine']
    )
    
    self.components['regime_engine'].subscribe_to_regime_changes(
        self.components['risk_manager'].on_regime_change
    )
    
    # Set position tracker callback
    self.components['risk_manager'].set_position_callbacks(
        position_update_callback=self.position_tracker.update_position
    )
    
    self.orchestrator.register_component(
        name="CentralRiskManager",
        component=self.components['risk_manager'],
        layer=ComponentLayer.GOVERNANCE,  # 🔥 GOVERNANCE LAYER
        authority_level=AuthorityLevel.GOVERNANCE_CONTROL,  # 🔥 HIGHEST AUTHORITY
        initialization_order=25  # After strategies (20)
    )
    
    logger.info("   ✅ CentralRiskManager initialized - GOVERNANCE layer active")
    
    # This component provides:
    # - authorize_trading_decision() → Authorization/Rejection
    # - update_position() → Position management (SINGLE AUTHORITY)
    # - get_risk_metrics() → Current risk exposure
    # - validate_trade() → Pre-trade risk checks

async def _authorize_trades(self, aggregated_signals: List[Signal]) -> List[ExecutionAuthorization]:
    """Request risk authorization for all trades (Rule 4 - MANDATORY)"""
    
    authorized_trades = []
    
    for signal in aggregated_signals:
        # Use BRICK #8: CentralRiskManager - MANDATORY AUTHORIZATION
        
        # Create authorization request
        from core_engine.system.central_risk_manager import (
            TradingDecisionRequest, TradingDecisionType
        )
        
        request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            symbol=signal.symbol,
            side=signal.signal_type.value,
            quantity=signal.target_quantity,
            strategy_id=signal.metadata.get('strategy_id', 'unknown'),
            confidence=signal.confidence,
            market_regime=self.components['regime_engine'].get_current_regime(),
            requesting_component='InstitutionalBacktestEngine'
        )
        
        self.authorization_requests += 1
        
        # 🔥 MANDATORY: Request authorization
        authorization = await self.components['risk_manager'].authorize_trading_decision(request)
        
        if authorization.authorization_level != AuthorizationLevel.REJECTED:
            self.authorized_trades += 1
            authorized_trades.append(authorization)
            
            logger.debug(f"   ✅ Trade AUTHORIZED: {signal.symbol} {signal.signal_type.value} "
                        f"{authorization.quantity}")
        else:
            self.rejected_trades += 1
            logger.debug(f"   ❌ Trade REJECTED: {signal.symbol} - {authorization.rejection_reason}")
    
    logger.info(f"   ⚖️ Risk authorization: {len(aggregated_signals)} signals → "
               f"{len(authorized_trades)} authorized ({self.rejected_trades} rejected)")
    
    return authorized_trades
```

**What this brick gives us**:
- ✅ **GOVERNANCE AUTHORITY** - Single point of authorization
- ✅ Risk limit enforcement (position size, VaR, concentration)
- ✅ Position management (SINGLE SOURCE OF TRUTH)
- ✅ Regime-adjusted risk limits
- ✅ Trade validation before execution
- ✅ Risk metrics and exposure tracking

**How it's used in backtest**:
1. **Authorization**: **ALL** trades require authorization (MANDATORY)
2. **Position tracking**: Updates positions after each trade
3. **Risk enforcement**: Rejects trades violating risk limits
4. **Regime adjustment**: Scales risk limits by regime
5. **Attribution**: Tracks risk by strategy

---

### PHASE 5: Execution Simulation (Rules 5, 12)

#### Brick: `UnifiedExecutionEngine`
**Location**: `core_engine/system/unified_execution_engine.py`  
**Used By**: `InstitutionalBacktestEngine._simulate_execution()`  
**Initialization Order**: **40**

```python
async def initialize(self):
    # ... Previous bricks ...
    
    # ═══════════════════════════════════════════════════════════
    # BRICK #9: UnifiedExecutionEngine (Rule 5 - ACTION Layer)
    # ═══════════════════════════════════════════════════════════
    
    logger.info("⚫ BRICK #9: UnifiedExecutionEngine (order=40)")
    
    from core_engine.system.unified_execution_engine import UnifiedExecutionEngine
    
    self.components['execution_engine'] = UnifiedExecutionEngine({
        'enable_market_impact': self.config.execution.apply_market_impact,
        'enable_spread_costs': self.config.execution.apply_spread_cost,
        'enable_slippage': self.config.execution.apply_slippage,
        'default_fill_rate': self.config.execution.default_fill_rate,
        'mode': 'backtest'  # Backtest mode (not live)
    })
    
    # 🔥 INJECT REGIME ENGINE (Rule 13)
    self.components['execution_engine'].set_regime_engine(
        self.components['regime_engine']
    )
    
    # Set risk manager callback for position updates
    self.components['execution_engine'].set_position_callbacks(
        risk_manager_callback=self.components['risk_manager'],
        position_update_callback=self.position_tracker.update_position
    )
    
    self.orchestrator.register_component(
        name="UnifiedExecutionEngine",
        component=self.components['execution_engine'],
        layer=ComponentLayer.EXECUTION,
        authority_level=AuthorityLevel.OPERATIONAL,
        initialization_order=40  # LAST (after all other components)
    )
    
    logger.info("   ✅ UnifiedExecutionEngine initialized (ACTION layer)")
    
    # This component provides:
    # - execute_authorized_trade() → Simulated execution result
    # - simulate_fill() → Realistic fill simulation
    # - apply_execution_costs() → Spread + Impact + Slippage

async def _simulate_execution(self, authorized_trade: ExecutionAuthorization) -> Dict[str, Any]:
    """Simulate realistic trade execution (Rules 5 + 12)"""
    
    # Use BRICK #9: UnifiedExecutionEngine
    
    from core_engine.system.unified_execution_engine import (
        ExecutionRequest, ExecutionAlgorithm, ExecutionUrgency
    )
    
    # Create execution request
    execution_request = ExecutionRequest(
        authorization=authorized_trade,
        algorithm=ExecutionAlgorithm.ADAPTIVE,  # Adaptive algorithm
        urgency=ExecutionUrgency.NORMAL,
        time_horizon=300,  # 5 minutes
        execution_style='midpoint_plus_spread'  # Backtest fill model
    )
    
    # Execute with realistic costs (Rule 12)
    execution_result = await self.components['execution_engine'].execute_authorized_trade(
        execution_request
    )
    
    # Track execution costs
    execution_costs = {
        'spread_cost_bps': execution_result.metadata.get('spread_cost_bps', 0),
        'market_impact_bps': execution_result.metadata.get('market_impact_bps', 0),
        'slippage_bps': execution_result.metadata.get('slippage_bps', 0),
        'total_cost_bps': execution_result.metadata.get('total_cost_bps', 0)
    }
    
    # Record trade
    trade_record = {
        'timestamp': execution_result.execution_timestamp,
        'symbol': authorized_trade.symbol,
        'side': authorized_trade.side,
        'quantity': execution_result.filled_quantity,
        'price': execution_result.avg_fill_price,
        'strategy': authorized_trade.metadata.get('strategy_id'),
        'regime': self.components['regime_engine'].get_current_regime(),
        'execution_costs': execution_costs,
        'pnl': 0.0  # Will be calculated later
    }
    
    self.trades.append(trade_record)
    
    logger.debug(f"   💰 Executed: {trade_record['symbol']} {trade_record['side']} "
                f"{trade_record['quantity']} @ ${trade_record['price']:.2f} "
                f"(cost: {execution_costs['total_cost_bps']:.1f} bps)")
    
    return trade_record
```

**What this brick gives us**:
- ✅ Realistic fill simulation
- ✅ Execution cost modeling (spread + impact + slippage)
- ✅ Fill price calculation (midpoint + half spread)
- ✅ Position updates through callbacks
- ✅ Execution quality metrics

**How it's used in backtest**:
1. **Trade execution**: Simulates realistic fills for authorized trades
2. **Cost application**: Applies all execution costs (Rule 12)
3. **Position updates**: Updates positions via callbacks
4. **Execution tracking**: Records all execution details

---

### PHASE 6: Analytics & Reporting (Rule 9)

#### Brick: `EnhancedAnalyticsManager`, `PerformanceAnalyzer`, `EnhancedMetricsCalculator`
**Location**: `core_engine/analytics/`  
**Used By**: `InstitutionalBacktestEngine.generate_report()`  
**Initialization Order**: **32, 33, 35**

```python
async def initialize(self):
    # ... Previous 9 bricks ...
    
    # ═══════════════════════════════════════════════════════════
    # Analytics Components (Rule 9)
    # ═══════════════════════════════════════════════════════════
    
    logger.info("🔷 Analytics Components (orders 32-35)")
    
    from core_engine.analytics.metrics_calculator import EnhancedMetricsCalculator
    from core_engine.analytics.performance_analyzer import PerformanceAnalyzer
    from core_engine.analytics.manager_enhanced import EnhancedAnalyticsManager
    
    # Metrics Calculator
    self.components['metrics_calculator'] = EnhancedMetricsCalculator()
    self.components['metrics_calculator'].set_regime_engine(self.components['regime_engine'])
    self.orchestrator.register_component(
        "EnhancedMetricsCalculator", 
        self.components['metrics_calculator'],
        ComponentLayer.EXECUTION,
        initialization_order=32
    )
    
    # Performance Analyzer
    self.components['performance_analyzer'] = PerformanceAnalyzer()
    self.components['performance_analyzer'].set_regime_engine(self.components['regime_engine'])
    self.orchestrator.register_component(
        "PerformanceAnalyzer",
        self.components['performance_analyzer'],
        ComponentLayer.EXECUTION,
        initialization_order=33
    )
    
    # Analytics Manager
    self.components['analytics_manager'] = EnhancedAnalyticsManager()
    self.components['analytics_manager'].set_regime_engine(self.components['regime_engine'])
    self.orchestrator.register_component(
        "EnhancedAnalyticsManager",
        self.components['analytics_manager'],
        ComponentLayer.EXECUTION,
        initialization_order=35
    )
    
    logger.info("   ✅ Analytics components initialized")

def generate_report(self) -> Dict[str, Any]:
    """Generate comprehensive report using analytics bricks"""
    
    # Use analytics bricks to calculate metrics
    
    # 1. Calculate performance metrics
    performance_metrics = self.components['metrics_calculator'].calculate_metrics(
        trades=self.trades,
        initial_capital=self.config.risk.initial_capital
    )
    
    # 2. Analyze performance with regime attribution
    performance_analysis = self.components['performance_analyzer'].analyze_performance(
        trades=self.trades,
        regime_history=self.regime_history,
        metrics=performance_metrics
    )
    
    # 3. Get analytics summary
    analytics_summary = self.components['analytics_manager'].get_analytics_summary(
        timeframe='full_backtest'
    )
    
    # Compile comprehensive report
    report = {
        'backtest_config': {
            'name': self.config.backtest_name,
            'symbols': self.config.data.symbols,
            'period': f"{self.config.data.start_date} to {self.config.data.end_date}",
            'strategies': [s.strategy_name for s in self.config.strategies]
        },
        'performance_metrics': performance_metrics,
        'performance_analysis': performance_analysis,
        'analytics_summary': analytics_summary,
        'execution_summary': {
            'total_trades': len(self.trades),
            'signals_generated': self.signals_generated,
            'signals_filtered': self.signals_filtered,
            'authorization_rate': self.authorized_trades / max(1, self.authorization_requests)
        },
        'regime_analysis': self._analyze_regime_performance()
    }
    
    return report
```

**What these bricks give us**:
- ✅ Comprehensive performance metrics (Sharpe, Sortino, Calmar, etc.)
- ✅ Regime-based attribution (performance by regime)
- ✅ Strategy-based attribution (performance by strategy)
- ✅ Risk analytics (VaR, drawdown, etc.)
- ✅ Execution quality analysis

**How they're used in backtest**:
1. **Metrics calculation**: Calculate all performance metrics
2. **Regime attribution**: Analyze performance by regime
3. **Strategy attribution**: Analyze performance by strategy
4. **Report generation**: Compile comprehensive report

---

## 📊 Complete Data Flow Through All Bricks

### Main Backtest Loop
```python
async def run_backtest(self) -> Dict[str, Any]:
    """Main backtest execution using all 9 bricks"""
    
    # ═══════════════════════════════════════════════════════════
    # STEP 1: Load Historical Data (BRICK #2: DataManager)
    # ═══════════════════════════════════════════════════════════
    market_data = await self._load_historical_data()
    
    # ═══════════════════════════════════════════════════════════
    # STEP 2: Process Bar-by-Bar
    # ═══════════════════════════════════════════════════════════
    for idx, bar in market_data.iterrows():
        market_update = bar.to_dict()
        
        # ───────────────────────────────────────────────────────
        # 2.1: BRICK #1 - Regime Detection (FIRST - Rule 13)
        # ───────────────────────────────────────────────────────
        regime_context = await self.components['regime_engine'].on_market_data(market_update)
        self.regime_history.append(regime_context)
        
        # ───────────────────────────────────────────────────────
        # 2.2: BRICK #3 - Liquidity Assessment (Rule 12)
        # ───────────────────────────────────────────────────────
        liquidity_score = await self.components['liquidity_engine'].assess_liquidity_score(
            symbol=market_update['symbol'],
            quantity=10000  # Standard reference
        )
        
        # ───────────────────────────────────────────────────────
        # 2.3: Signal Generation (every N bars)
        # ───────────────────────────────────────────────────────
        if idx % 30 == 0:  # Every 30 bars
            
            # BRICK #4: Calculate indicators
            indicators = self.components['indicators_engine'].calculate_indicators(
                self.current_data_window
            )
            
            # BRICK #5: Engineer features
            features = self.components['feature_engineer'].create_features(indicators)
            
            # BRICK #6: Generate signals
            raw_signals = self.components['signal_generator'].generate_signals(features)
            self.signals_generated += len(raw_signals)
            
            # BRICK #3: Filter by liquidity
            filtered_signals = await self._filter_signals_by_liquidity(raw_signals)
            
            # ───────────────────────────────────────────────────
            # 2.4: BRICK #7 - Multi-Strategy Execution (Rule 8)
            # ───────────────────────────────────────────────────
            aggregated_signals = await self.components['strategy_manager'].aggregate_signals(
                filtered_signals
            )
            
            # ───────────────────────────────────────────────────
            # 2.5: BRICK #8 - Risk Authorization (Rule 4 - MANDATORY)
            # ───────────────────────────────────────────────────
            authorized_trades = await self._authorize_trades(aggregated_signals)
            
            # ───────────────────────────────────────────────────
            # 2.6: BRICK #9 - Execute Trades (Rules 5 + 12)
            # ───────────────────────────────────────────────────
            for authorization in authorized_trades:
                trade_record = await self._simulate_execution(authorization)
                
                # Update position tracker
                self.position_tracker.update_position(
                    symbol=trade_record['symbol'],
                    side=trade_record['side'],
                    quantity=trade_record['quantity'],
                    price=trade_record['price']
                )
    
    # ═══════════════════════════════════════════════════════════
    # STEP 3: Generate Report (Analytics Bricks)
    # ═══════════════════════════════════════════════════════════
    report = self.generate_report()
    
    return report
```

---

## 🎯 Summary: How Each Brick Is Used

| Brick # | Component | Order | Used For | Input | Output |
|---------|-----------|-------|----------|-------|--------|
| **1** | `EnhancedRegimeEngine` | 5 | Market regime detection | Bar data | RegimeContext |
| **2** | `ClickHouseDataManager` | 10 | Historical data loading | Config | DataFrame |
| **3** | `LiquidityAssessmentEngine` | 12 | Liquidity scoring & filtering | Symbol, qty | LiquidityScore |
| **4** | `EnhancedTechnicalIndicators` | 15 | Technical indicators | OHLCV data | Indicators DF |
| **5** | `EnhancedFeatureEngineer` | 16 | ML feature engineering | Indicators | Features DF |
| **6** | `EnhancedSignalGenerator` | 17 | Trading signal generation | Features | Signals |
| **7** | `StrategyManager` | 20 | Multi-strategy coordination | Signals | Aggregated signals |
| **8** | `CentralRiskManager` | 25 | Risk authorization (GOVERNANCE) | Trade request | Authorization |
| **9** | `UnifiedExecutionEngine` | 40 | Trade execution simulation | Authorization | ExecutionResult |
| **10-12** | Analytics Components | 32-35 | Performance analytics | Trades, regimes | Metrics, reports |

---

## ✅ Compliance Checklist

### Rule 13: Regime-First Principle
- ✅ RegimeEngine initializes FIRST (order=5)
- ✅ ALL components injected with regime engine
- ✅ ALL components subscribe to regime changes
- ✅ Regime context used in all decisions

### Rule 12: Liquidity Management
- ✅ LiquidityAssessmentEngine filters signals
- ✅ Market impact applied to all executions
- ✅ Spread costs applied to all fills
- ✅ TCA calculated for all trades

### Rule 8: Multi-Strategy Coordination
- ✅ StrategyManager coordinates multiple strategies
- ✅ Signal aggregation with conflict resolution
- ✅ Dynamic strategy weighting by regime
- ✅ Per-strategy performance attribution

### Rule 4: Central Risk Management
- ✅ ALL trades require CentralRiskManager authorization
- ✅ Risk limits enforced before execution
- ✅ Position tracking through single authority
- ✅ Regime-adjusted risk limits

### Rule 3: Data Flow Pipeline
- ✅ Single data authority (ClickHouseDataManager)
- ✅ Processing pipeline: Data → Indicators → Features → Signals
- ✅ No direct database access in application

### Rule 1: Component Integration
- ✅ ALL components implement ISystemComponent
- ✅ Proper initialization order enforced
- ✅ Health monitoring for all components

---

This guide shows **exactly** how each core_engine "Lego Brick" fits into the backtest application. Ready to start building Phase 1? 🚀

