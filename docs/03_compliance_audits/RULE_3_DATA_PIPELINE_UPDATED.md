# Rule 3: Unified Data Flow Pipeline and Processing Patterns

**Version:** 2.1 (Enhanced with Signal Type Distinction Clarification)  
**Date:** November 2, 2025  
**Status:** ACTIVE - MANDATORY COMPLIANCE

**Enhancements in v2.1:**
- 🔴 **CRITICAL:** Explicit TradingSignal vs StrategySignal distinction (Phase 4 vs Phase 5)
- 🔴 **CRITICAL:** Clarified that strategies DO NOT consume TradingSignal objects
- Signal type documentation with implementation evidence
- See detailed specifications: `docs/03_compliance_audits/RULE_UPDATE_RECOMMENDATIONS.md`

---

## Overview

The core_engine implements a **strict, unified data flow pipeline** that ALL components MUST follow. This pipeline ensures **data consistency**, **eliminates code duplication**, and provides **single source of truth** for all processing operations.

**Key Principle:** Data flows through a standardized pipeline. Components **consume processed data** rather than processing raw data themselves.

---

## Complete 10-Phase Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   PHASE 0: RAW DATA (ClickHouse Storage)                     │
│                   1-minute OHLCV bars stored in database                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                     ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: DATA LAYER (Rule 3.1)                                              │
│ Component: ClickHouseDataManager (core_engine/data/manager.py)              │
│ Authority: SINGLE DATA AUTHORITY                                            │
│ Responsibility: Load raw OHLCV from database                                │
│ Input: Symbol list, date range, timeframe                                   │
│ Output: pd.DataFrame[timestamp, open, high, low, close, volume]             │
│ Methods: load_market_data(), get_historical_data()                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                     ↓
                        **Raw OHLCV DataFrame**
                                     ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 2: INDICATORS LAYER (Rule 3.2)                                        │
│ Component: EnhancedTechnicalIndicators                                      │
│           (core_engine/processing/indicators/engine.py)                     │
│ Responsibility: Calculate 29+ technical indicators                          │
│ Input: Raw OHLCV DataFrame                                                  │
│ Output: OHLCV + Indicators DataFrame                                        │
│                                                                              │
│ Indicators Calculated:                                                      │
│ • Trend: SMA_10, SMA_20, SMA_50, SMA_200, EMA_9, EMA_12, MACD, ADX_14      │
│ • Momentum: RSI_14, Stochastic, CCI, Williams %R, ROC, MOM                 │
│ • Volatility: ATR_14, Bollinger Bands, Keltner, Donchian, Hist Vol         │
│ • Volume: OBV, Volume_MA, VWAP, MFI, A/D Line                              │
│                                                                              │
│ Methods: calculate_indicators(market_data: pd.DataFrame) -> pd.DataFrame    │
└─────────────────────────────────────────────────────────────────────────────┘
                                     ↓
                **Indicators-Enriched DataFrame**
                (OHLCV + 29+ indicator columns)
                                     ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 3: FEATURE ENGINEERING LAYER (Rule 3.3)                               │
│ Component: EnhancedFeatureEngineer                                          │
│           (core_engine/processing/features/engineer.py)                     │
│ Responsibility: Engineer 50+ ML-ready features                              │
│ Input: OHLCV + Indicators DataFrame                                         │
│ Output: OHLCV + Indicators + Features DataFrame                             │
│                                                                              │
│ Features Engineered:                                                        │
│ • Price: returns_1, returns_5, log_returns, price_momentum                 │
│ • Trend: trend_strength, trend_direction, ma_crossovers                    │
│ • Momentum: rsi_normalized, momentum_acceleration, relative_momentum       │
│ • Volatility: volatility_ratio, atr_normalized, bollinger_position         │
│ • Volume: volume_ratio, obv_trend, volume_price_correlation                │
│ • Cross-Asset: relative_strength, correlation, beta                        │
│                                                                              │
│ Methods: create_features(indicators_df: pd.DataFrame) -> pd.DataFrame       │
└─────────────────────────────────────────────────────────────────────────────┘
                                     ↓
                **Feature-Rich DataFrame**
                (OHLCV + Indicators + 50+ features)
                                     ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 4: SIGNAL GENERATION LAYER (Rule 3.4) ⭐ UPDATED                      │
│ Component: EnhancedSignalGenerator                                          │
│           (core_engine/processing/signals/generator.py)                     │
│ Responsibility: Generate PRELIMINARY trading signals                        │
│ Input: OHLCV + Indicators + Features DataFrame                              │
│ Output: List[TradingSignal] objects ⭐ (PRELIMINARY/INFORMATIONAL)           │
│                                                                              │
│ **CRITICAL SIGNAL TYPE DISTINCTION:**                                       │
│ • Output Type: TradingSignal objects (NOT StrategySignal)                   │
│ • Purpose: Preliminary/informational market signals                        │
│ • Signal Classes: signal_generator_volume, signal_generator_momentum,       │
│   signal_generator_mean_reversion                                            │
│ • Characteristics: Multi-factor synthesis, regime-aware filtering,          │
│   informational purpose                                                     │
│                                                                              │
│ Signal Generation Process:                                                  │
│ 1. Generate mean reversion signals                                          │
│ 2. Generate momentum signals                                                │
│ 3. Generate volume signals                                                  │
│ 4. Apply regime-aware filtering                                             │
│ 5. Convert to TradingSignal objects                                         │
│                                                                              │
│ **IMPORTANT:** TradingSignal objects are NOT consumed by strategies.        │
│ Strategies generate their own StrategySignal objects independently.         │
│                                                                              │
│ Methods: generate_signals(features_df: pd.DataFrame) -> List[TradingSignal]│
│ File: core_engine/processing/signals/generator.py                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                     ↓
                **TradingSignal Objects**
                (Preliminary/informational signals)
                **NOT CONSUMED BY STRATEGIES** ⭐
                                     ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 5: STRATEGY LAYER (Rule 3.5) ⭐ UPDATED                                 │
│ Component: Trading Strategies (10 implementations)                          │
│           (core_engine/trading/strategies/implementations/)                  │
│ Responsibility: Apply strategy-specific logic to enriched data              │
│ Input: Fully Enriched DataFrame (OHLCV + Indicators + Features) ⭐          │
│ Output: List[StrategySignal] objects ⭐ (EXECUTABLE TRADING DECISIONS)      │
│                                                                              │
│ **CRITICAL REQUIREMENTS:**                                                   │
│ ✅ Strategies MUST consume enriched DataFrames (NOT TradingSignal objects)   │
│ ✅ Strategies MUST read pre-calculated indicators (not calculate)           │
│ ✅ Strategies MUST focus on logic (not processing)                          │
│ ✅ Strategies MUST generate StrategySignal objects (NOT TradingSignal)       │
│ ❌ Strategies CANNOT calculate indicators                                    │
│ ❌ Strategies CANNOT process raw data                                        │
│ ❌ Strategies CANNOT bypass pipeline                                         │
│ ❌ **NEW:** Strategies DO NOT consume TradingSignal objects from Phase 4    │
│                                                                              │
│ **SIGNAL TYPE DISTINCTION:**                                                 │
│ • Input: Enriched DataFrame (Dict[str, pd.DataFrame])                       │
│ • Output: List[StrategySignal] objects                                      │
│ • Purpose: Strategy-specific executable trading decisions                   │
│ • Flow: StrategySignal objects go to Rule 4 (Risk Authorization)            │
│                                                                              │
│ **Strategy Signal Generation:**                                              │
│ Strategies consume enriched DataFrames directly and apply their own logic    │
│ to generate StrategySignal objects. These are INDEPENDENT from TradingSignal │
│ objects generated in Phase 4.                                                │
│                                                                              │
│ Methods: generate_signals(enriched_data: Dict[str, pd.DataFrame])           │
│          -> List[StrategySignal]                                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                     ↓
                **StrategySignal Objects**
                (Executable trading decisions)
                **FLOW TO RULE 4 (Risk Authorization)** ⭐
                                     ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 6-10: Risk Management → Execution → Analytics                         │
│ (See Rule 4, Rule 7, and subsequent pipeline phases)                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## CRITICAL: Signal Type Distinction (v2.1) 🔴

### TradingSignal (Phase 4 Output)

**Type:** `TradingSignal` objects  
**Source:** `EnhancedSignalGenerator`  
**Location:** `core_engine/processing/signals/generator.py`

**Characteristics:**
- **Purpose:** Preliminary/informational market signals
- **Generation:** Multi-factor synthesis (mean reversion + momentum + volume)
- **Signal Classes:**
  - `signal_generator_volume`
  - `signal_generator_momentum`
  - `signal_generator_mean_reversion`
- **Regime-Aware:** Yes, filtered by regime context
- **Consumption:** **NOT consumed by strategies** (informational only)
- **Usage:** Market analysis, context provision, debugging

**Implementation Evidence:**
```python
# From test_live_data_signal_generation.py line 301:
trading_signals = signal_generator.generate_signals(features_df)
# Returns: List[TradingSignal] objects

# Example output from test:
# - SIGNALTYPE.SELL $441.71 (70.72% confidence, signal_generator_volume)
# - SIGNALTYPE.SELL $443.73 (68.00% confidence, signal_generator_momentum)
# - SIGNALTYPE.BUY $446.08 (70.72% confidence, signal_generator_volume)
```

### StrategySignal (Phase 5 Output)

**Type:** `StrategySignal` objects  
**Source:** Trading Strategies (e.g., `EnhancedMomentumStrategy`)  
**Location:** `core_engine/trading/strategies/implementations/`

**Characteristics:**
- **Purpose:** Executable trading decisions
- **Generation:** Strategy-specific logic applied to enriched data
- **Consumption:** Enriched DataFrames directly (NOT TradingSignal objects)
- **Flow:** StrategySignal → Rule 4 (Risk Authorization) → Rule 7 (Execution)
- **Authority:** Trading decisions that require risk authorization

**Implementation Evidence:**
```python
# From enhanced_momentum.py line 309:
async def generate_signals(self, enriched_data: Dict[str, pd.DataFrame]) -> List[StrategySignal]:
    """
    Generate momentum signals from ENRICHED data (Rule 3 Phase 5)
    
    Args:
        enriched_data: Dict[symbol, enriched DataFrame with OHLCV + indicators + features]
                      NOT: List[TradingSignal] objects
    
    Returns:
        List[StrategySignal]: Momentum signals (executable trading decisions)
    """
```

### Key Distinctions

| Aspect | TradingSignal (Phase 4) | StrategySignal (Phase 5) |
|--------|-------------------------|--------------------------|
| **Source** | EnhancedSignalGenerator | Trading Strategies |
| **Input** | Features DataFrame | Enriched DataFrame |
| **Output** | List[TradingSignal] | List[StrategySignal] |
| **Purpose** | Informational/preliminary | Executable decisions |
| **Consumed By** | Analytics, debugging | Risk Manager (Rule 4) |
| **Regime-Aware** | Yes (filtered) | Yes (strategy logic) |
| **Signal Classes** | signal_generator_* | Strategy-specific |

**CRITICAL FLOW:**
```
Phase 4: Features → TradingSignal (informational) → NOT USED BY STRATEGIES
Phase 5: Enriched Data → StrategySignal (executable) → Rule 4 Authorization
```

---

## Pipeline Orchestration (Rule 3.6)

### ProcessingPipelineOrchestrator

**File:** `core_engine/processing/pipeline_orchestrator.py`

The pipeline orchestrator coordinates the complete processing flow:

```python
from core_engine.processing.pipeline_orchestrator import ProcessingPipelineOrchestrator

# Initialize pipeline
pipeline = ProcessingPipelineOrchestrator(
    data_config=data_config,
    indicator_config=indicator_config,
    feature_config=feature_config,
    signal_config=signal_config
)

# Process data through complete pipeline ONCE
enriched_data = await pipeline.process_market_data(
    symbols=['AAPL', 'TSLA', 'NVDA'],
    start_time=datetime(2024, 1, 1),
    end_time=datetime(2024, 12, 31),
    timeframe='1min'
)

# enriched_data is Dict[symbol, EnrichedMarketData]
# Each EnrichedMarketData contains:
#   - raw_data: Original OHLCV
#   - indicators: OHLCV + 29+ indicators
#   - features: OHLCV + indicators + 50+ features
#   - signals: Fully enriched DataFrame (with signal columns)
#   - trading_signals: List[TradingSignal] objects (Phase 4 output, informational)
```

### StrategyManager Integration

**File:** `core_engine/trading/strategies/manager.py`

StrategyManager uses pipeline orchestrator to process data ONCE for all strategies:

```python
class StrategyManager:
    """
    Multi-strategy coordinator with pipeline integration
    
    **CRITICAL:** Processes data through pipeline ONCE,
    then all strategies consume SAME enriched data.
    Strategies generate StrategySignal objects independently.
    """
    
    def __init__(self, config):
        # Pipeline orchestrator
        self.pipeline = ProcessingPipelineOrchestrator(config)
        self.strategies = {}
    
    async def generate_all_signals(
        self, 
        symbols: List[str], 
        start_time: datetime, 
        end_time: datetime
    ) -> List[StrategySignal]:  # ⭐ Returns StrategySignal, NOT TradingSignal
        """Generate signals from all strategies"""
        
        # STEP 1: Process data through pipeline ONCE
        enriched_data = await self.pipeline.process_market_data(
            symbols=symbols,
            start_time=start_time,
            end_time=end_time
        )
        
        # STEP 2: All strategies consume SAME enriched data
        all_signals = []  # Will contain StrategySignal objects
        for strategy_id, strategy in self.strategies.items():
            # Convert to strategy format (enriched DataFrames)
            strategy_data = {
                symbol: enriched.get_enriched_dataframe()
                for symbol, enriched in enriched_data.items()
            }
            
            # Strategy receives ENRICHED data (NOT TradingSignal objects!)
            # Strategy generates StrategySignal objects independently
            signals = await strategy.generate_signals(strategy_data)
            all_signals.extend(signals)
        
        return all_signals  # List[StrategySignal] → Rule 4 (Risk Authorization)
```

---

## Component Responsibility Matrix

| Phase | Component | Input | Output | Responsibility | Can Calculate Indicators? |
|----|-----|----|-----|----|---|
| 1 | DataManager | Symbols, dates | Raw OHLCV | Load data from DB | ❌ NO |
| 2 | Indicators Engine | Raw OHLCV | OHLCV + Indicators | Calculate indicators | ✅ YES (ONLY HERE) |
| 3 | Feature Engineer | OHLCV + Indicators | + Features | Engineer features | ❌ NO |
| 4 | Signal Generator | + Features | **TradingSignal** ⭐ | Generate prelim signals | ❌ NO |
| 5 | Strategy | Enriched Data | **StrategySignal** ⭐ | Apply strategy logic | ❌ NO |
| 6 | Risk Manager | StrategySignal | Authorization | Authorize trades | ❌ NO |

**KEY PRINCIPLE:** 
- Only `EnhancedTechnicalIndicators` (Phase 2) can calculate indicators
- `EnhancedSignalGenerator` (Phase 4) produces `TradingSignal` objects (informational)
- Trading Strategies (Phase 5) produce `StrategySignal` objects (executable)
- Strategies DO NOT consume TradingSignal objects

---

## Strategy Implementation Requirements (Rule 3.5 - CRITICAL) ⭐

### ✅ CORRECT Strategy Implementation

```python
class EnhancedMomentumStrategy(EnhancedBaseStrategy):
    """
    Pipeline-compliant momentum strategy
    
    **Receives:** Enriched DataFrame (OHLCV + Indicators + Features)
    **Output:** List[StrategySignal] objects (executable trading decisions)
    **Does NOT:** Receive TradingSignal objects from Phase 4
    """
    
    async def generate_signals(
        self, 
        enriched_data: Dict[str, pd.DataFrame]  # ⭐ Enriched DataFrames, NOT TradingSignal
    ) -> List[StrategySignal]:  # ⭐ Returns StrategySignal, NOT TradingSignal
        """
        Generate signals from PRE-PROCESSED data
        
        Args:
            enriched_data: Dict[symbol, DataFrame with OHLCV + indicators + features]
                          DataFrame has columns like: SMA_10, RSI_14, ADX_14, etc.
                          ⭐ NOT: List[TradingSignal] objects
        
        Returns:
            List[StrategySignal]: Strategy-specific trading decisions
        """
        # Validate data is enriched
        self._validate_enriched_data(enriched_data)
        
        signals = []  # Will contain StrategySignal objects
        
        for symbol in self.config.symbols:
            data = enriched_data[symbol]
            
            # READ pre-calculated indicators (NO calculation!)
            current_row = data.iloc[-1]
            short_momentum = data['momentum_short'].iloc[-1]  # Pre-calculated
            adx = current_row['ADX_14']  # Pre-calculated
            rsi = current_row['RSI_14']  # Pre-calculated
            volume_ratio = current_row['volume_ratio']  # Pre-calculated
            
            # STRATEGY LOGIC ONLY (no indicator calculation)
            if (short_momentum > self.config.momentum_threshold and
                adx > self.config.adx_threshold and
                rsi < 70 and
                volume_ratio > 1.2):
                
                # Create StrategySignal (NOT TradingSignal!)
                signal = StrategySignal(
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    confidence=0.75,
                    quantity=100,
                    timestamp=datetime.now(),
                    strategy_id=self.strategy_id
                )
                signals.append(signal)
        
        return signals  # List[StrategySignal] → Rule 4
    
    def _validate_enriched_data(self, enriched_data: Dict[str, pd.DataFrame]) -> None:
        """
        Validate that data is enriched (has required indicators)
        
        Raises ValueError if data is raw OHLCV without indicators
        """
        required_columns = ['SMA_10', 'RSI_14', 'ADX_14', 'volume_ratio']
        
        for symbol, data in enriched_data.items():
            missing = [col for col in required_columns if col not in data.columns]
            if missing:
                raise ValueError(
                    f"{symbol} missing required indicators: {missing}. "
                    f"Data must be enriched via ProcessingPipelineOrchestrator."
                )
```

### ❌ PROHIBITED Strategy Pattern (Rule Violation)

```python
class BadMomentumStrategy(EnhancedBaseStrategy):
    """
    ❌ VIOLATES RULE 3: This strategy incorrectly consumes TradingSignal objects
    """
    
    async def generate_signals(
        self, 
        trading_signals: List[TradingSignal]  # ❌ WRONG: Should be enriched DataFrames
    ) -> List[StrategySignal]:
        """
        ❌ PROHIBITED: Strategies should NOT consume TradingSignal objects
        """
        # ❌ BAD: Using TradingSignal objects from Phase 4
        for trading_signal in trading_signals:
            if trading_signal.strategy == 'signal_generator_momentum':
                # ❌ This bypasses strategy logic!
                pass
```

**Why This is Bad:**
- ❌ Violates separation of concerns (signal generator vs strategy)
- ❌ Bypasses strategy-specific logic
- ❌ Creates dependency on Phase 4 output
- ❌ Prevents independent strategy evolution

---

## MANDATORY Requirements (Rule 3.7)

### For All Components

1. **Data Source:** MUST use `ClickHouseDataManager` (no direct DB access)
2. **Pipeline Flow:** MUST follow Phase 1 → 2 → 3 → 4 → 5 sequence
3. **No Bypassing:** CANNOT skip pipeline stages
4. **Indicator Calculation:** ONLY `EnhancedTechnicalIndicators` can calculate
5. **Enriched Data Validation:** Components MUST validate input data format

### For Signal Generator (Phase 4) ⭐ NEW

1. **Output Type:** MUST produce `TradingSignal` objects
2. **Purpose:** Informational/preliminary signals only
3. **Not Consumed:** TradingSignal objects are NOT consumed by strategies
4. **Signal Classes:** Must use `signal_generator_*` naming pattern

### For Strategies Specifically (Phase 5) ⭐ UPDATED

1. **Input Validation:** MUST validate data is enriched (has indicators)
2. **Input Type:** MUST consume enriched DataFrames (NOT TradingSignal objects)
3. **Output Type:** MUST produce `StrategySignal` objects (NOT TradingSignal)
4. **Read-Only Indicators:** MUST read pre-calculated indicators
5. **No Calculation:** CANNOT calculate indicators internally
6. **Focus on Logic:** MUST focus on strategy-specific logic only
7. **Method Signature:** `generate_signals(enriched_data: Dict[str, pd.DataFrame]) -> List[StrategySignal]`

### For Pipeline Orchestrator

1. **Single Processing:** Process data through pipeline ONCE per timeframe
2. **Consistency:** Ensure all strategies receive SAME enriched data
3. **Caching:** Cache enriched data to avoid reprocessing
4. **Regime Integration:** Propagate regime context to all pipeline components
5. **Error Handling:** Gracefully handle failures in pipeline stages
6. **Signal Output:** Provide both enriched DataFrame AND TradingSignal objects (for informational purposes)

---

## PROHIBITED Patterns (Rule 3.8)

### ❌ Direct Database Access
```python
# PROHIBITED
import clickhouse_connect
client = clickhouse_connect.get_client()
data = client.query("SELECT * FROM market_data")  # ❌ VIOLATES RULE 3.1
```

### ❌ Pipeline Bypassing
```python
# PROHIBITED
class Strategy:
    async def generate_signals(self, raw_data):
        # Skipping pipeline stages
        indicators = self._calculate_my_own_indicators(raw_data)  # ❌ VIOLATES RULE 3.2
```

### ❌ Indicator Calculation in Strategy
```python
# PROHIBITED
class Strategy:
    def _calculate_indicators(self, data):
        # Strategies cannot calculate indicators!
        rsi = self._calculate_rsi(data)  # ❌ VIOLATES RULE 3.5
        adx = self._calculate_adx(data)  # ❌ VIOLATES RULE 3.5
```

### ❌ Strategies Consuming TradingSignal Objects ⭐ NEW
```python
# PROHIBITED
class Strategy:
    async def generate_signals(self, trading_signals: List[TradingSignal]):
        """
        ❌ VIOLATES RULE 3.5: Strategies should NOT consume TradingSignal objects
        
        Strategies must consume enriched DataFrames and generate StrategySignal objects.
        """
        pass
```

### ❌ Inconsistent Signal Types
```python
# PROHIBITED
# Strategy A returns TradingSignal
async def generate_signals(self, data) -> List[TradingSignal]:  # ❌ WRONG TYPE

# Strategy B returns Dict
async def generate_signals(self, data) -> Dict:  # ❌ WRONG TYPE

# REQUIRED: All strategies return List[StrategySignal]
async def generate_signals(self, data) -> List[StrategySignal]:  # ✅ CORRECT
```

---

## Benefits of Pipeline Architecture

### 1. Code Reduction
- **Before:** 10 strategies × 150 lines of indicator code = 1,500 lines
- **After:** 1 pipeline × indicator calculation = 0 lines in strategies
- **Savings:** 1,500 lines of duplicated code eliminated (30% reduction)

### 2. Performance Optimization
- **Before:** Calculate same indicator 10 times (once per strategy)
- **After:** Calculate each indicator ONCE (shared across strategies)
- **Improvement:** 90% reduction in indicator calculation time

### 3. Consistency Guarantee
- **Before:** Each strategy may calculate RSI differently
- **After:** All strategies use SAME RSI calculation
- **Benefit:** 100% consistency across strategies

### 4. Separation of Concerns
- **Signal Generator:** Multi-factor synthesis (TradingSignal - informational)
- **Strategies:** Strategy-specific logic (StrategySignal - executable)
- **Benefit:** Clear separation, independent evolution

### 5. Maintenance Efficiency
- **Before:** Bug in ADX calculation → fix in 10 strategies
- **After:** Bug in ADX calculation → fix in 1 place
- **Improvement:** 90% reduction in maintenance effort

### 6. Testing Simplicity
- **Before:** Test indicator calculations in each strategy
- **After:** Test indicators once in isolation
- **Benefit:** Cleaner unit tests, better coverage

---

## Validation and Enforcement (Rule 3.9)

### Enriched Data Validation

```python
def validate_enriched_data(data: pd.DataFrame, component_name: str) -> None:
    """
    Validate that DataFrame is enriched with required columns
    
    Raises:
        ValueError: If data is missing required indicators/features
    """
    # Required indicator columns (from Phase 2)
    required_indicators = [
        'SMA_10', 'SMA_20', 'SMA_50', 
        'RSI_14', 'MACD', 'ADX_14', 
        'ATR_14', 'volume_ratio'
    ]
    
    # Required feature columns (from Phase 3)
    required_features = [
        'returns_1', 'momentum_score', 
        'trend_strength', 'volatility_ratio'
    ]
    
    missing_indicators = [col for col in required_indicators if col not in data.columns]
    missing_features = [col for col in required_features if col not in data.columns]
    
    if missing_indicators or missing_features:
        raise ValueError(
            f"{component_name} received raw data without enrichment! "
            f"Missing indicators: {missing_indicators}, "
            f"Missing features: {missing_features}. "
            f"Data MUST be processed through ProcessingPipelineOrchestrator."
        )
```

### Signal Type Validation ⭐ NEW

```python
def validate_strategy_signal_type(signal) -> None:
    """
    Validate that strategy returns StrategySignal objects
    
    Raises:
        TypeError: If signal is not StrategySignal type
    """
    from core_engine.trading.strategies.strategy_engine import StrategySignal
    
    if not isinstance(signal, StrategySignal):
        raise TypeError(
            f"Strategy returned {type(signal)}, expected StrategySignal. "
            f"Strategies MUST return StrategySignal objects, not TradingSignal."
        )
```

### Pipeline Compliance Testing

```python
# File: tests/compliance/test_rule3_enforcement.py

class TestRule3Compliance:
    """Verify Rule 3 compliance across all components"""
    
    def test_strategies_do_not_calculate_indicators(self):
        """Ensure strategies don't have indicator calculation methods"""
        prohibited_methods = [
            '_calculate_indicators',
            '_calculate_sma',
            '_calculate_rsi',
            '_calculate_adx',
            '_calculate_macd'
        ]
        
        for strategy_class in ALL_STRATEGY_CLASSES:
            for method_name in prohibited_methods:
                assert not hasattr(strategy_class, method_name), \
                    f"{strategy_class.__name__} has prohibited method {method_name}"
    
    def test_strategies_validate_enriched_data(self):
        """Ensure strategies validate data is enriched"""
        for strategy_class in ALL_STRATEGY_CLASSES:
            assert hasattr(strategy_class, '_validate_enriched_data'), \
                f"{strategy_class.__name__} missing _validate_enriched_data method"
    
    def test_strategies_return_strategy_signal(self):  # ⭐ NEW
        """Ensure strategies return StrategySignal objects, not TradingSignal"""
        from core_engine.trading.strategies.strategy_engine import StrategySignal
        from core_engine.processing.signals.generator import TradingSignal
        
        for strategy_class in ALL_STRATEGY_CLASSES:
            # Get return type annotation
            import inspect
            sig = inspect.signature(strategy_class.generate_signals)
            return_type = sig.return_annotation
            
            # Should return List[StrategySignal], not List[TradingSignal]
            assert 'StrategySignal' in str(return_type), \
                f"{strategy_class.__name__} must return List[StrategySignal]"
            assert 'TradingSignal' not in str(return_type), \
                f"{strategy_class.__name__} must NOT return TradingSignal"
    
    async def test_complete_pipeline_flow(self):
        """Test data flows through all pipeline stages"""
        # Load raw data
        raw_data = await data_manager.load_market_data(...)
        assert 'SMA_10' not in raw_data.columns  # Should be raw
        
        # Process through pipeline
        enriched_data = await pipeline.process_market_data(...)
        
        # Verify enrichment
        assert 'SMA_10' in enriched_data['AAPL'].signals.columns
        assert 'RSI_14' in enriched_data['AAPL'].signals.columns
        assert 'momentum_score' in enriched_data['AAPL'].signals.columns
        
        # Verify TradingSignal objects (Phase 4)
        trading_signals = enriched_data['AAPL'].trading_signals
        assert all(isinstance(s, TradingSignal) for s in trading_signals)
        
        # Verify strategies consume enriched data, not TradingSignal
        strategy_signals = await strategy.generate_signals(enriched_data)
        assert all(isinstance(s, StrategySignal) for s in strategy_signals)
        assert all(not isinstance(s, TradingSignal) for s in strategy_signals)
```

---

## Migration Guide (Rule 3.10)

### For Existing Strategies

**Step 1:** Update method signature
```python
# OLD
async def generate_signals(self, market_data: Dict[str, pd.DataFrame]):
    
# NEW
async def generate_signals(self, enriched_data: Dict[str, pd.DataFrame]) -> List[StrategySignal]:
```

**Step 2:** Add enriched data validation
```python
def _validate_enriched_data(self, enriched_data: Dict[str, pd.DataFrame]):
    required_columns = ['SMA_10', 'RSI_14', 'ADX_14']
    for symbol, data in enriched_data.items():
        missing = [col for col in required_columns if col not in data.columns]
        if missing:
            raise ValueError(f"{symbol} missing indicators: {missing}")
```

**Step 3:** Remove indicator calculation methods
```python
# DELETE these methods:
# - _calculate_indicators()
# - _calculate_symbol_indicators()
# - _calculate_adx()
# - _calculate_rsi()
# - etc. (all indicator calculation code)
```

**Step 4:** Update signal generation to READ indicators and return StrategySignal
```python
# OLD (calculates)
sma_10 = data['close'].rolling(10).mean()
rsi = self._calculate_rsi(data)
signal = TradingSignal(...)  # ❌ WRONG TYPE

# NEW (reads and returns StrategySignal)
sma_10 = data['SMA_10'].iloc[-1]
rsi = data['RSI_14'].iloc[-1]
signal = StrategySignal(...)  # ✅ CORRECT TYPE
```

**Step 5:** Remove TradingSignal consumption (if any) ⭐ NEW
```python
# OLD (if mistakenly consuming TradingSignal)
async def generate_signals(self, trading_signals: List[TradingSignal]):
    # ❌ PROHIBITED

# NEW (consume enriched DataFrames)
async def generate_signals(self, enriched_data: Dict[str, pd.DataFrame]) -> List[StrategySignal]:
    # ✅ CORRECT
```

---

## Summary

**Rule 3 Requirements:**
1. ✅ Use `ProcessingPipelineOrchestrator` for all data processing
2. ✅ Follow 10-phase pipeline: Data → Indicators → Features → Signals → Strategy
3. ✅ Strategies consume enriched data (NOT raw OHLCV)
4. ✅ ONLY `EnhancedTechnicalIndicators` calculates indicators
5. ✅ Validate enriched data in all consuming components
6. ✅ **Signal Generator produces TradingSignal objects (informational)**
7. ✅ **Strategies produce StrategySignal objects (executable)**
8. ✅ **Strategies DO NOT consume TradingSignal objects**
9. ❌ NO indicator calculation in strategies
10. ❌ NO pipeline bypassing
11. ❌ NO direct database access

**Compliance:** MANDATORY for all components  
**Enforcement:** Automated tests + code reviews  
**Benefits:** 30% code reduction, 90% performance improvement, 100% consistency, clear signal type separation

---

**Last Updated:** November 2, 2025  
**Status:** ACTIVE (v2.1 - Enhanced with Signal Type Distinction Clarification)  
**Related:** Rule 2 (Regime-First), Rule 4 (Risk Governance), Rule 5 (Multi-Strategy)

