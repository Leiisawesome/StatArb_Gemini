# Pipeline Refactoring Roadmap
## Fixing the Critical Architectural Gap

**Date:** October 24, 2025  
**Priority:** 🔴 **CRITICAL**  
**Status:** PLANNING  
**Estimated Effort:** 2-3 days

---

## Overview

**Problem:** Strategies are bypassing the Processing Brick pipeline and calculating their own indicators, violating Rule 3 (Unified Data Flow Pipeline).

**Solution:** Implement proper pipeline orchestration and refactor strategies to consume enriched data instead of raw OHLCV.

---

## Phased Implementation Plan

### ✅ Phase 0: Planning & Documentation (CURRENT)
**Duration:** 1 hour  
**Status:** IN PROGRESS

Tasks:
1. ✅ Identify architectural gap
2. ✅ Document current vs. intended flow
3. ✅ Create detailed audit document
4. 🔄 Update Rule 3 with detailed pipeline specification
5. 🔄 Create implementation roadmap

---

### 📋 Phase 1: Update Rule 3 (Enhanced Pipeline Specification)
**Duration:** 2 hours  
**Status:** PLANNED

**Objective:** Update Rule 3 to explicitly define the complete pipeline flow with component responsibilities.

**Tasks:**
1. **Enhance Rule 3 with 10-phase pipeline** (from complete_trading_signal_flow.md)
2. **Add explicit component contracts:**
   - DataManager responsibility: Load raw OHLCV
   - Indicators Engine: Calculate 29+ indicators
   - Feature Engineer: Create 50+ features
   - Signal Generator: Generate preliminary signals
   - Strategy: Consume enriched data, generate strategy signals
3. **Add PROHIBITED patterns:**
   - ❌ Strategies CANNOT calculate indicators
   - ❌ Strategies CANNOT process raw OHLCV
   - ❌ Components CANNOT bypass pipeline
4. **Add enforcement mechanisms:**
   - Type checking for enriched data
   - Validation that strategies receive correct DataFrame format
   - Unit tests for pipeline compliance

**Deliverables:**
- ✅ Updated Rule 3 (.cursor/rules/TIER-1-ARCHITECTURAL-RULES/rule-3-data-flow-pipeline.mdc)
- ✅ Complete pipeline flow specification
- ✅ Component responsibility matrix

---

### 🏗️ Phase 2: Create Pipeline Orchestrator
**Duration:** 4-6 hours  
**Status:** PLANNED

**Objective:** Create a central orchestrator that coordinates the complete processing pipeline.

**Implementation:**

**File:** `core_engine/processing/pipeline_orchestrator.py`

```python
from dataclasses import dataclass
from typing import Dict, List, Optional
import pandas as pd
from datetime import datetime

from core_engine.system.interfaces import ISystemComponent, IRegimeAware
from core_engine.data.manager import ClickHouseDataManager
from core_engine.processing.indicators.engine import EnhancedTechnicalIndicators
from core_engine.processing.features.engineer import EnhancedFeatureEngineer
from core_engine.processing.signals.generator import EnhancedSignalGenerator
from core_engine.config import DataConfig, IndicatorConfig, FeatureConfig, SignalConfig

@dataclass
class EnrichedMarketData:
    """
    Container for fully processed market data
    Guarantees data has passed through complete pipeline
    """
    symbol: str
    timeframe: str
    raw_data: pd.DataFrame  # Original OHLCV
    indicators: pd.DataFrame  # OHLCV + 29+ indicators
    features: pd.DataFrame  # OHLCV + indicators + 50+ features
    signals: pd.DataFrame  # OHLCV + indicators + features + preliminary signals
    processing_timestamp: datetime
    pipeline_version: str = "1.0.0"
    
    def get_enriched_dataframe(self) -> pd.DataFrame:
        """Get fully enriched DataFrame ready for strategy consumption"""
        return self.signals.copy()

class ProcessingPipelineOrchestrator(ISystemComponent, IRegimeAware):
    """
    Central orchestrator for the complete data processing pipeline
    
    Coordinates: DataManager → Indicators → Features → Signals
    
    This ensures ALL strategies consume the SAME enriched data,
    eliminating indicator calculation duplication.
    
    **Rule 3 Compliance:** Enforces unified data flow pipeline
    """
    
    def __init__(
        self,
        data_config: Optional[DataConfig] = None,
        indicator_config: Optional[IndicatorConfig] = None,
        feature_config: Optional[FeatureConfig] = None,
        signal_config: Optional[SignalConfig] = None
    ):
        # Component initialization
        self.component_name = "ProcessingPipelineOrchestrator"
        self.is_initialized = False
        self.is_operational = False
        
        # Load configurations
        self.data_config = data_config or DataConfig()
        self.indicator_config = indicator_config or IndicatorConfig()
        self.feature_config = feature_config or FeatureConfig()
        self.signal_config = signal_config or SignalConfig()
        
        # Initialize pipeline components
        self.data_manager = None
        self.indicators_engine = None
        self.feature_engineer = None
        self.signal_generator = None
        
        # Regime awareness
        self.regime_engine = None
        self.current_regime_context = None
        
        # Processing cache
        self.enriched_data_cache: Dict[str, EnrichedMarketData] = {}
        self.cache_ttl = 300  # 5 minutes
        
        logger.info("✅ ProcessingPipelineOrchestrator initialized (Rule 3 enforcement)")
    
    # ================================================================
    # ISystemComponent Implementation
    # ================================================================
    
    async def initialize(self) -> bool:
        """Initialize all pipeline components"""
        try:
            # Initialize DataManager
            self.data_manager = ClickHouseDataManager(self.data_config)
            await self.data_manager.initialize()
            
            # Initialize Indicators Engine
            self.indicators_engine = EnhancedTechnicalIndicators(self.indicator_config)
            await self.indicators_engine.initialize()
            
            # Initialize Feature Engineer
            self.feature_engineer = EnhancedFeatureEngineer(self.feature_config)
            await self.feature_engineer.initialize()
            
            # Initialize Signal Generator
            self.signal_generator = EnhancedSignalGenerator(self.signal_config)
            await self.signal_generator.initialize()
            
            self.is_initialized = True
            logger.info("✅ Pipeline orchestrator initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Pipeline orchestrator initialization failed: {e}")
            return False
    
    async def start(self) -> bool:
        """Start pipeline operations"""
        if not self.is_initialized:
            return False
        
        self.is_operational = True
        logger.info("✅ Pipeline orchestrator operational")
        return True
    
    async def stop(self) -> bool:
        """Stop pipeline operations"""
        self.is_operational = False
        logger.info("Pipeline orchestrator stopped")
        return True
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of all pipeline components"""
        return {
            'orchestrator_healthy': self.is_operational,
            'data_manager': await self.data_manager.health_check() if self.data_manager else {'healthy': False},
            'indicators_engine': await self.indicators_engine.health_check() if self.indicators_engine else {'healthy': False},
            'feature_engineer': await self.feature_engineer.health_check() if self.feature_engineer else {'healthy': False},
            'signal_generator': await self.signal_generator.health_check() if self.signal_generator else {'healthy': False},
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get pipeline orchestrator status"""
        return {
            'component_name': self.component_name,
            'initialized': self.is_initialized,
            'operational': self.is_operational,
            'cache_size': len(self.enriched_data_cache),
        }
    
    # ================================================================
    # IRegimeAware Implementation
    # ================================================================
    
    def set_regime_engine(self, regime_engine: Any) -> None:
        """Inject regime engine and propagate to pipeline components"""
        self.regime_engine = regime_engine
        
        # Propagate to all pipeline components
        if self.indicators_engine:
            self.indicators_engine.set_regime_engine(regime_engine)
        if self.feature_engineer:
            self.feature_engineer.set_regime_engine(regime_engine)
        if self.signal_generator:
            self.signal_generator.set_regime_engine(regime_engine)
        
        logger.info("✅ Regime engine injected into pipeline")
    
    async def on_regime_change(self, new_regime_context) -> None:
        """Handle regime change and propagate to components"""
        self.current_regime_context = new_regime_context
        
        # Propagate to pipeline components
        if self.indicators_engine:
            await self.indicators_engine.on_regime_change(new_regime_context)
        if self.feature_engineer:
            await self.feature_engineer.on_regime_change(new_regime_context)
        if self.signal_generator:
            await self.signal_generator.on_regime_change(new_regime_context)
        
        # Clear cache on regime change (indicators may need recalculation)
        self.enriched_data_cache.clear()
        logger.info(f"Regime changed to {new_regime_context.primary_regime}, cache cleared")
    
    def get_current_regime_context(self):
        """Get current regime context"""
        return self.current_regime_context
    
    async def adapt_to_regime(self, regime_context) -> Dict[str, Any]:
        """Adapt pipeline processing to regime"""
        # Pipeline adapts by propagating regime to components
        return {
            'regime': regime_context.primary_regime if regime_context else None,
            'pipeline_adapted': True
        }
    
    def validate_regime_dependency(self) -> bool:
        """Validate regime engine is configured"""
        return self.regime_engine is not None
    
    # ================================================================
    # Core Pipeline Orchestration
    # ================================================================
    
    async def process_market_data(
        self,
        symbols: List[str],
        start_time: datetime,
        end_time: datetime,
        timeframe: str = "1min"
    ) -> Dict[str, EnrichedMarketData]:
        """
        Process raw market data through complete pipeline
        
        Returns fully enriched data ready for strategy consumption
        
        Pipeline Flow:
        1. Load raw OHLCV (DataManager)
        2. Calculate indicators (EnhancedTechnicalIndicators)
        3. Engineer features (EnhancedFeatureEngineer)
        4. Generate signals (EnhancedSignalGenerator)
        
        Args:
            symbols: List of symbols to process
            start_time: Start of data range
            end_time: End of data range
            timeframe: Data timeframe (default: 1min)
        
        Returns:
            Dict[symbol, EnrichedMarketData] - Fully processed data per symbol
        """
        enriched_data = {}
        
        try:
            # PHASE 1: Load raw OHLCV data
            logger.info(f"📊 Phase 1: Loading raw OHLCV for {len(symbols)} symbols")
            raw_data = await self.data_manager.load_market_data(
                symbols=symbols,
                start_time=start_time,
                end_time=end_time,
                interval=timeframe
            )
            
            # Process each symbol through pipeline
            for symbol in symbols:
                symbol_data = raw_data[raw_data['symbol'] == symbol].copy()
                
                if symbol_data.empty:
                    logger.warning(f"No data for {symbol}, skipping")
                    continue
                
                # PHASE 2: Calculate technical indicators
                logger.debug(f"🔧 Phase 2: Calculating indicators for {symbol}")
                indicators_df = self.indicators_engine.calculate_indicators(symbol_data)
                
                # PHASE 3: Engineer features
                logger.debug(f"🔬 Phase 3: Engineering features for {symbol}")
                features_df = self.feature_engineer.create_features(indicators_df)
                
                # PHASE 4: Generate preliminary signals
                logger.debug(f"📡 Phase 4: Generating signals for {symbol}")
                signals_df = self.signal_generator.generate_signals(features_df)
                
                # Create enriched data container
                enriched_data[symbol] = EnrichedMarketData(
                    symbol=symbol,
                    timeframe=timeframe,
                    raw_data=symbol_data,
                    indicators=indicators_df,
                    features=features_df,
                    signals=signals_df,
                    processing_timestamp=datetime.now()
                )
                
                logger.info(f"✅ {symbol} processed: {len(symbol_data)} bars → {len(signals_df.columns)} total columns")
            
            logger.info(f"✅ Pipeline complete: {len(enriched_data)} symbols processed")
            return enriched_data
            
        except Exception as e:
            logger.error(f"Pipeline processing failed: {e}")
            return {}
    
    def get_enriched_dataframe(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        Get enriched DataFrame for a symbol
        
        Returns fully processed DataFrame ready for strategy consumption
        """
        if symbol in self.enriched_data_cache:
            return self.enriched_data_cache[symbol].get_enriched_dataframe()
        return None
```

**Deliverables:**
- ✅ `core_engine/processing/pipeline_orchestrator.py` (350+ lines)
- ✅ `EnrichedMarketData` container class
- ✅ Full ISystemComponent + IRegimeAware integration
- ✅ Unit tests for pipeline orchestrator

---

### 🔄 Phase 3: Refactor StrategyManager Integration
**Duration:** 3-4 hours  
**Status:** PLANNED

**Objective:** Modify StrategyManager to use pipeline orchestrator instead of passing raw data to strategies.

**Changes:**

**File:** `core_engine/trading/strategies/manager.py`

```python
class StrategyManager(ISystemComponent):
    """
    Enhanced StrategyManager with pipeline integration
    
    **CRITICAL CHANGE:** Strategies now receive ENRICHED data
    from the ProcessingPipelineOrchestrator, not raw OHLCV.
    """
    
    def __init__(self, config):
        # ... existing init ...
        
        # NEW: Pipeline orchestrator integration
        self.pipeline = ProcessingPipelineOrchestrator(
            data_config=config.data_config,
            indicator_config=config.indicator_config,
            feature_config=config.feature_config,
            signal_config=config.signal_config
        )
        
    async def initialize(self) -> bool:
        """Initialize manager and pipeline"""
        # Initialize pipeline first
        pipeline_ready = await self.pipeline.initialize()
        if not pipeline_ready:
            logger.error("Pipeline initialization failed")
            return False
        
        # Initialize strategies
        # ... existing strategy init ...
        
        return True
    
    async def generate_all_signals(
        self,
        symbols: List[str],
        start_time: datetime,
        end_time: datetime,
        timeframe: str = "1min"
    ) -> List[StrategySignal]:
        """
        Generate signals from all strategies using pipeline
        
        **KEY CHANGE:** Process data through pipeline ONCE,
        then all strategies consume SAME enriched data.
        """
        
        # STEP 1: Process data through pipeline ONCE
        logger.info(f"Processing {len(symbols)} symbols through pipeline")
        enriched_data = await self.pipeline.process_market_data(
            symbols=symbols,
            start_time=start_time,
            end_time=end_time,
            timeframe=timeframe
        )
        
        # STEP 2: All strategies consume SAME enriched data
        all_signals = []
        
        for strategy_id, strategy in self.strategies.items():
            try:
                # Convert enriched data to format expected by strategy
                strategy_data = {
                    symbol: enriched.get_enriched_dataframe()
                    for symbol, enriched in enriched_data.items()
                }
                
                # Strategy receives ENRICHED data (not raw OHLCV)
                strategy_signals = await strategy.generate_signals(strategy_data)
                all_signals.extend(strategy_signals)
                
                logger.info(f"Strategy {strategy_id}: generated {len(strategy_signals)} signals")
                
            except Exception as e:
                logger.error(f"Strategy {strategy_id} failed: {e}")
                continue
        
        logger.info(f"Total signals generated: {len(all_signals)} from {len(self.strategies)} strategies")
        return all_signals
```

**Deliverables:**
- ✅ Modified StrategyManager with pipeline integration
- ✅ Backward compatibility for existing tests
- ✅ Integration tests

---

### 🎯 Phase 4: Refactor Momentum Strategy (Proof of Concept)
**Duration:** 4-6 hours  
**Status:** PLANNED

**Objective:** Refactor one strategy (Momentum) as proof-of-concept. Remove all indicator calculation code.

**Changes:**

**File:** `core_engine/trading/strategies/implementations/momentum/enhanced_momentum.py`

**BEFORE (current state):**
- 1,105 lines total
- ~150 lines of indicator calculation code
- Methods to REMOVE:
  - `_calculate_indicators()` (lines 581-590)
  - `_calculate_symbol_indicators()` (lines 592-633)
  - `_calculate_adx()` (lines 634-673)
  - `_update_momentum_analysis()` (lines 679-748)

**AFTER (refactored):**
- ~700 lines (36% reduction!)
- ZERO indicator calculation code
- Strategy ONLY contains logic

**Implementation:**

```python
class EnhancedMomentumStrategy(EnhancedBaseStrategy):
    """
    Refactored Momentum Strategy (Pipeline-Compliant)
    
    **CRITICAL CHANGE:** This strategy NO LONGER calculates indicators.
    It receives ENRICHED data from ProcessingPipelineOrchestrator.
    
    Input DataFrame columns include:
    - OHLCV: timestamp, open, high, low, close, volume
    - 29+ Indicators: SMA_10, SMA_20, RSI_14, MACD, ADX_14, ATR_14, etc.
    - 50+ Features: momentum_score, trend_strength, volatility_ratio, etc.
    - Preliminary signals: signal_type, signal_strength, confidence
    """
    
    async def generate_signals(
        self, 
        enriched_data: Dict[str, pd.DataFrame]  # ENRICHED, not raw!
    ) -> List[StrategySignal]:
        """
        Generate momentum signals from PRE-PROCESSED data
        
        Args:
            enriched_data: Dict[symbol, DataFrame with OHLCV + indicators + features]
        
        Returns:
            List[StrategySignal]
        """
        signals = []
        
        try:
            # Validate data is enriched (has indicators)
            self._validate_enriched_data(enriched_data)
            
            # Generate signals for each symbol
            for symbol in self.config.symbols:
                if symbol not in enriched_data:
                    logger.warning(f"{symbol} not in enriched_data")
                    continue
                
                data = enriched_data[symbol]
                
                # Check minimum data requirements
                if len(data) < self.config.long_period:
                    logger.debug(f"{symbol}: insufficient data")
                    continue
                
                # Generate signals for symbol
                symbol_signals = await self._generate_symbol_signals(symbol, data)
                signals.extend(symbol_signals)
            
            logger.info(f"Momentum Strategy: generated {len(signals)} signals")
            return signals
            
        except Exception as e:
            logger.error(f"Signal generation failed: {e}")
            return []
    
    def _validate_enriched_data(self, enriched_data: Dict[str, pd.DataFrame]) -> None:
        """
        Validate that data is enriched (has indicators + features)
        
        Raises ValueError if data is raw OHLCV without indicators
        """
        required_columns = ['SMA_10', 'RSI_14', 'ADX_14', 'ATR_14', 'volume_ratio']
        
        for symbol, data in enriched_data.items():
            missing = [col for col in required_columns if col not in data.columns]
            if missing:
                raise ValueError(
                    f"{symbol} missing required indicators: {missing}. "
                    f"Data must be enriched via ProcessingPipelineOrchestrator. "
                    f"Available columns: {list(data.columns)[:10]}..."
                )
    
    async def _generate_symbol_signals(
        self, 
        symbol: str, 
        data: pd.DataFrame  # ENRICHED data
    ) -> List[StrategySignal]:
        """
        Generate signals for a specific symbol
        
        **CRITICAL:** Data is enriched, indicators are PRE-CALCULATED
        """
        signals = []
        
        try:
            # Skip if already have position
            if symbol in self.active_positions:
                return signals
            
            # READ pre-calculated indicators (NO calculation!)
            current_row = data.iloc[-1]
            
            # Momentum indicators (PRE-CALCULATED by pipeline)
            momentum_short = data['momentum_short'].iloc[-1]  # From features
            momentum_medium = data['momentum_medium'].iloc[-1]
            momentum_long = data['momentum_long'].iloc[-1]
            
            # Trend quality (PRE-CALCULATED by pipeline)
            adx = current_row['ADX_14']  # From indicators
            
            # Volume confirmation (PRE-CALCULATED by pipeline)
            volume_ratio = current_row['volume_ratio']  # From features
            
            # Additional features (PRE-CALCULATED by pipeline)
            rsi = current_row['RSI_14']  # From indicators
            sma_50 = current_row['SMA_50']  # From indicators
            current_price = current_row['close']
            
            # STRATEGY LOGIC ONLY (no calculation!)
            
            # Check bullish momentum conditions
            bullish_conditions = [
                momentum_short > self.config.momentum_threshold,
                momentum_medium > 0,
                momentum_long > 0,
                adx > self.config.adx_threshold,
                volume_ratio > self.config.volume_threshold,
                rsi < 70,  # Not overbought
                current_price > sma_50  # Uptrend
            ]
            
            bullish_count = sum(bullish_conditions)
            
            # Generate BUY signal if conditions met
            if bullish_count >= 5:  # At least 5 of 7 conditions
                confidence = self._calculate_signal_confidence(
                    bullish_count, 
                    momentum_short, 
                    adx, 
                    volume_ratio
                )
                
                if confidence > 0.6:
                    signal = StrategySignal(
                        strategy_id=self.strategy_id,
                        symbol=symbol,
                        signal_type=SignalType.BUY,
                        strength=min(momentum_short / self.config.momentum_threshold, 1.0),
                        confidence=confidence,
                        target_quantity=self.config.base_position_pct,
                        timestamp=datetime.now(),
                        additional_data={
                            'momentum_short': momentum_short,
                            'momentum_medium': momentum_medium,
                            'momentum_long': momentum_long,
                            'adx': adx,
                            'volume_ratio': volume_ratio,
                            'rsi': rsi,
                            'entry_price': current_price
                        }
                    )
                    signals.append(signal)
                    logger.info(f"BUY signal: {symbol} @ {current_price:.2f} (confidence: {confidence:.2f})")
            
            # Similar logic for SELL signals...
            
            return signals
            
        except Exception as e:
            logger.error(f"Symbol signal generation failed for {symbol}: {e}")
            return []
    
    def _calculate_signal_confidence(
        self, 
        conditions_met: int, 
        momentum: float, 
        adx: float, 
        volume_ratio: float
    ) -> float:
        """
        Calculate signal confidence from strategy logic
        
        NOTE: Does NOT calculate indicators, only evaluates them
        """
        base_confidence = conditions_met / 7.0  # 7 total conditions
        
        # Boost confidence for strong momentum
        momentum_boost = min(momentum / (self.config.momentum_threshold * 2), 0.2)
        
        # Boost confidence for strong trend
        adx_boost = min((adx - self.config.adx_threshold) / 50, 0.1)
        
        # Boost confidence for high volume
        volume_boost = min((volume_ratio - self.config.volume_threshold) / 2, 0.1)
        
        confidence = base_confidence + momentum_boost + adx_boost + volume_boost
        return min(confidence, 1.0)
    
    # REMOVED METHODS (no longer needed):
    # - _calculate_indicators()
    # - _calculate_symbol_indicators()
    # - _calculate_adx()
    # - _update_momentum_analysis()
    # - All indicator calculation code (~150 lines removed)
```

**Deliverables:**
- ✅ Refactored Momentum Strategy (~400 lines removed)
- ✅ Validation that data is enriched
- ✅ Unit tests with mock enriched data
- ✅ Integration test with pipeline orchestrator

---

### 📦 Phase 5: Migrate Remaining 9 Strategies
**Duration:** 8-12 hours (1-1.5 hours per strategy)  
**Status:** PLANNED

**Objective:** Apply same refactoring to all remaining strategies.

**Strategies to migrate:**
1. ✅ Momentum (Phase 4 - proof of concept)
2. Mean Reversion
3. Statistical Arbitrage
4. Trend Following
5. Breakout
6. Pairs Trading
7. Factor
8. Multi-Asset
9. Volatility
10. Arbitrage

**Per-strategy checklist:**
- [ ] Remove indicator calculation methods
- [ ] Add enriched data validation
- [ ] Update signal generation to READ indicators
- [ ] Remove ~100-200 lines of calculation code
- [ ] Add unit tests with mock enriched data
- [ ] Verify integration test passes

**Expected Code Reduction:**
- 10 strategies × 150 lines avg = **1,500 lines removed**
- Strategies reduced from ~1,000 lines to ~600-700 lines each

---

### 🧪 Phase 6: Comprehensive Testing
**Duration:** 6-8 hours  
**Status:** PLANNED

**Test Suite:**

**File:** `tests/integration/test_pipeline_orchestrator.py`
```python
class TestPipelineOrchestrator:
    """Comprehensive pipeline orchestrator tests"""
    
    async def test_complete_pipeline_flow(self):
        """Test data flows through all pipeline stages"""
        pass
    
    async def test_enriched_data_format(self):
        """Verify enriched data has all required columns"""
        pass
    
    async def test_strategy_receives_enriched_data(self):
        """Verify strategies receive enriched data, not raw"""
        pass
    
    async def test_indicator_consistency(self):
        """Verify same indicators across all strategies"""
        pass
    
    async def test_performance_vs_old_architecture(self):
        """Compare performance: pipeline vs. per-strategy calculation"""
        pass
```

**File:** `tests/integration/test_strategy_pipeline_integration.py`
```python
class TestStrategyPipelineIntegration:
    """Test strategies work with pipeline"""
    
    async def test_momentum_strategy_with_pipeline(self):
        """Momentum strategy generates signals from pipeline data"""
        pass
    
    async def test_all_strategies_with_pipeline(self):
        """All 10 strategies work with pipeline"""
        pass
    
    async def test_multi_strategy_same_data(self):
        """Multiple strategies consume same enriched data"""
        pass
```

**File:** `tests/compliance/test_rule3_enforcement.py`
```python
class TestRule3Enforcement:
    """Verify Rule 3 compliance"""
    
    def test_strategies_cannot_calculate_indicators(self):
        """Strategies don't have indicator calculation methods"""
        pass
    
    def test_enriched_data_validation(self):
        """Strategies validate data is enriched"""
        pass
    
    def test_pipeline_flow_complete(self):
        """Complete flow: Data → Indicators → Features → Signals → Strategy"""
        pass
```

**Deliverables:**
- ✅ 30+ integration tests
- ✅ 20+ compliance tests
- ✅ Performance benchmarks
- ✅ Test coverage report

---

### 📚 Phase 7: Documentation Updates
**Duration:** 4 hours  
**Status:** PLANNED

**Documents to update:**

1. **Rule 3** (.cursor/rules/TIER-1-ARCHITECTURAL-RULES/rule-3-data-flow-pipeline.mdc)
   - Add complete 10-phase pipeline specification
   - Add component responsibility matrix
   - Add PROHIBITED patterns
   - Add enforcement mechanisms

2. **Architecture Guide** (docs/02_architecture/)
   - Update architecture diagrams
   - Document pipeline orchestrator
   - Update strategy development guide

3. **Strategy Development Guide** (new document)
   - How to consume enriched data
   - Available indicators and features
   - Example strategy implementation

4. **Migration Guide** (new document)
   - For developers with custom strategies
   - Step-by-step migration instructions
   - Before/after code examples

**Deliverables:**
- ✅ Updated Rule 3 with complete specification
- ✅ Updated architecture documentation
- ✅ New strategy development guide
- ✅ Migration guide for custom strategies

---

### 🚀 Phase 8: Backtest Integration & Validation
**Duration:** 4-6 hours  
**Status:** PLANNED

**Objective:** Update backtest engine to use pipeline orchestrator.

**Changes:**

**File:** `backtest/engine/institutional_backtest_engine.py`

```python
class InstitutionalBacktestEngine:
    """
    Enhanced backtest engine with pipeline integration
    """
    
    def __init__(self, config):
        # ... existing init ...
        
        # NEW: Pipeline orchestrator
        self.pipeline = ProcessingPipelineOrchestrator(
            data_config=config.data_config,
            indicator_config=config.indicator_config,
            feature_config=config.feature_config,
            signal_config=config.signal_config
        )
    
    async def run_backtest(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> BacktestResult:
        """Run backtest with pipeline"""
        
        # Process ALL data through pipeline ONCE
        logger.info("Processing historical data through pipeline...")
        enriched_data = await self.pipeline.process_market_data(
            symbols=self.symbols,
            start_time=start_date,
            end_time=end_date,
            timeframe=self.timeframe
        )
        
        # Iterate through time
        for timestamp in self.trading_timestamps:
            # Slice enriched data to current timestamp
            current_data = self._slice_to_timestamp(enriched_data, timestamp)
            
            # All strategies consume same enriched data
            signals = await self.strategy_manager.generate_all_signals(current_data)
            
            # Process signals through risk and execution
            for signal in signals:
                await self._process_signal(signal)
        
        return self.generate_results()
```

**Validation:**
1. Run existing backtests with pipeline
2. Verify results match pre-refactor results
3. Measure performance improvement
4. Generate comparison report

**Deliverables:**
- ✅ Updated backtest engine
- ✅ Backtest validation suite
- ✅ Performance comparison report
- ✅ Regression test suite

---

## Success Criteria

### Phase Completion Criteria

**Phase 1-3:** ✅ Infrastructure Ready
- [ ] Rule 3 updated with complete specification
- [ ] Pipeline orchestrator implemented
- [ ] StrategyManager integrated with pipeline
- [ ] All tests pass

**Phase 4:** ✅ Proof of Concept
- [ ] Momentum strategy refactored
- [ ] 150+ lines of indicator code removed
- [ ] Strategy receives enriched data
- [ ] Integration test passes

**Phase 5:** ✅ Full Migration
- [ ] All 10 strategies refactored
- [ ] 1,500+ lines of duplicated code removed
- [ ] All strategies use pipeline
- [ ] All tests pass

**Phase 6-7:** ✅ Quality Assurance
- [ ] 50+ tests added
- [ ] Test coverage > 80%
- [ ] Documentation complete
- [ ] Code reviews passed

**Phase 8:** ✅ Production Ready
- [ ] Backtest integration complete
- [ ] Performance validated
- [ ] Regression tests pass
- [ ] Ready for deployment

---

## Performance Improvements (Expected)

### Code Reduction
- **Before:** 10 strategies × 1,000 lines = 10,000 lines
- **After:** 10 strategies × 700 lines = 7,000 lines
- **Savings:** 3,000 lines (30% reduction)

### Execution Performance
- **Before:** 10 strategies × indicator calculation time = 10x overhead
- **After:** 1 pipeline × indicator calculation time = 1x overhead
- **Improvement:** ~90% reduction in indicator calculation time

### Maintenance Benefits
- **Before:** Bug in ADX calculation → fix in 10 places
- **After:** Bug in ADX calculation → fix in 1 place
- **Improvement:** 90% reduction in maintenance effort

---

## Risk Mitigation

### Rollback Plan
- Keep old strategy implementations in `legacy/` directory
- Feature flag for pipeline vs. direct calculation
- Gradual migration (strategy-by-strategy)
- Comprehensive regression testing

### Compatibility
- Maintain backward compatibility for tests
- Support both raw and enriched data formats during transition
- Gradual deprecation of old methods

---

## Timeline

**Week 1:**
- Monday: Phase 1-2 (Rule 3 + Pipeline Orchestrator)
- Tuesday: Phase 3-4 (StrategyManager + Momentum refactor)
- Wednesday: Phase 5 (Migrate remaining strategies)

**Week 2:**
- Thursday: Phase 6 (Testing)
- Friday: Phase 7-8 (Documentation + Backtest)

**Total:** 2-3 days of focused development

---

## Next Steps

1. **Get approval** for this roadmap
2. **Create feature branch**: `feature/pipeline-refactoring`
3. **Start Phase 1**: Update Rule 3
4. **Implement Phase 2**: Create pipeline orchestrator
5. **Prove concept (Phase 4)**: Refactor Momentum strategy
6. **Full migration (Phase 5)**: Migrate all strategies
7. **Quality assurance (Phase 6-7)**: Testing + docs
8. **Production ready (Phase 8)**: Backtest integration

---

**Status:** READY FOR IMPLEMENTATION  
**Blocking Issues:** None  
**Dependencies:** None  
**Approval Required:** Yes


