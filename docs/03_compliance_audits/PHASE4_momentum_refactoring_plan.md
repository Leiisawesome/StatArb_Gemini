# Phase 4.1: Momentum Strategy Refactoring Plan

**Target:** `core_engine/trading/strategies/implementations/momentum/enhanced_momentum.py`  
**Current Size:** 1,105 lines  
**Goal:** Remove indicator calculations, add enriched data validation, update signal generation

---

## Changes Required

### 1. Add Enriched Data Validation Method

**Location:** After `__init__` method

```python
def _validate_enriched_data(self, enriched_data: Dict[str, pd.DataFrame]) -> None:
    """
    Validate that data is enriched with required indicators (Rule 3 Phase 4)
    
    Args:
        enriched_data: Dict[symbol, enriched DataFrame]
        
    Raises:
        ValueError: If data is missing required indicators
    """
    required_indicators = [
        'SMA_10', 'SMA_20', 'SMA_50',  # Moving averages
        'RSI_14',                       # Momentum oscillator
        'ADX_14',                       # Trend strength
        'MACD', 'MACD_signal',         # MACD indicators
        'ATR_14',                       # Volatility
        'volume_ratio'                  # Volume indicator
    ]
    
    for symbol, data in enriched_data.items():
        missing = [col for col in required_indicators if col not in data.columns]
        if missing:
            raise ValueError(
                f"{symbol} missing required indicators: {missing}. "
                f"Data must be enriched via ProcessingPipelineOrchestrator (Rule 3). "
                f"Available columns: {list(data.columns[:20])}"
            )
        
        logger.debug(f"✅ {symbol} enriched data validated: {len(required_indicators)} indicators present")
```

### 2. Remove Indicator Calculation Methods

**Delete these methods (lines ~581-650):**
- `_calculate_indicators()`
- `_calculate_symbol_indicators()`
- `_calculate_adx()`

**Total Lines Removed:** ~150 lines

### 3. Update `generate_signals()` Method

**OLD Pattern (lines 272-310):**
```python
async def generate_signals(self, market_data: Dict[str, pd.DataFrame]) -> List[StrategySignal]:
    # Update market data
    self._update_market_data(market_data)
    
    # Calculate indicators  # ❌ REMOVE THIS
    self._calculate_indicators()
    
    # Update momentum analysis
    self._update_momentum_analysis()
    
    # Generate signals
    for symbol in self.config.symbols:
        signal = self._generate_symbol_signal(symbol)
        # ...
```

**NEW Pattern:**
```python
async def generate_signals(self, enriched_data: Dict[str, pd.DataFrame]) -> List[StrategySignal]:
    """
    Generate momentum signals from ENRICHED data (Rule 3 Phase 4)
    
    Args:
        enriched_data: Dict[symbol, enriched DataFrame with OHLCV + indicators + features]
        
    Returns:
        List[StrategySignal]: Momentum signals
    """
    start_time = datetime.now()
    signals = []
    
    try:
        # PHASE 4: Validate enriched data (Rule 3)
        self._validate_enriched_data(enriched_data)
        
        # Update market data (enriched)
        self._update_market_data(enriched_data)
        
        # Update momentum analysis (using pre-calculated indicators)
        self._update_momentum_analysis()
        
        # Generate signals for each symbol
        for symbol in self.config.symbols:
            if symbol not in enriched_data:
                logger.warning(f"⚠️  {symbol} not in enriched data")
                continue
            
            signal = self._generate_symbol_signal(symbol)
            if signal:
                signals.append(signal)
        
        # Log performance
        elapsed = (datetime.now() - start_time).total_seconds() * 1000
        logger.info(
            f"📊 Momentum strategy generated {len(signals)} signals "
            f"from enriched data in {elapsed:.1f}ms (Rule 3 Phase 4)"
        )
        
        return signals
        
    except ValueError as e:
        logger.error(f"❌ Enriched data validation failed: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Signal generation failed: {e}")
        return []
```

### 4. Update `_update_momentum_analysis()` to READ Indicators

**OLD Pattern:**
```python
def _update_momentum_analysis(self) -> None:
    # Calculate momentum from indicators
    momentum = self.indicators[symbol]['momentum_short']
    # ...
```

**NEW Pattern:**
```python
def _update_momentum_analysis(self) -> None:
    """
    Update momentum analysis using PRE-CALCULATED indicators (Rule 3 Phase 4)
    
    Reads indicators from enriched data, does NOT calculate them.
    """
    for symbol in self.config.symbols:
        if symbol not in self.market_data:
            continue
        
        data = self.market_data[symbol]
        
        # READ pre-calculated indicators (NOT calculate!)
        current_row = data.iloc[-1]
        
        self.momentum_data[symbol] = {
            'momentum_short': current_row.get('momentum_short', 0.0),  # From FeatureEngineer
            'sma_10': current_row.get('SMA_10', current_row['close']),
            'sma_20': current_row.get('SMA_20', current_row['close']),
            'sma_50': current_row.get('SMA_50', current_row['close']),
            'rsi': current_row.get('RSI_14', 50.0),
            'adx': current_row.get('ADX_14', 0.0),
            'macd': current_row.get('MACD', 0.0),
            'atr': current_row.get('ATR_14', 0.0),
            'volume_ratio': current_row.get('volume_ratio', 1.0),
            'trend_strength': current_row.get('trend_strength', 0.0),  # From FeatureEngineer
            'price': current_row['close']
        }
```

### 5. Update Signal Generation Logic

**Ensure `_generate_symbol_signal()` uses `self.momentum_data` which now contains PRE-CALCULATED values:**

No changes needed - this method already reads from `self.momentum_data`.

---

## Implementation Steps

1. ✅ Add `_validate_enriched_data()` method
2. ✅ Update `generate_signals()` signature and logic
3. ✅ Update `_update_momentum_analysis()` to READ indicators
4. ✅ Delete `_calculate_indicators()` method
5. ✅ Delete `_calculate_symbol_indicators()` method
6. ✅ Delete `_calculate_adx()` method
7. ✅ Update docstrings to reference Rule 3 Phase 4
8. ✅ Test with enriched data

---

## Expected Results

**Before:**
- File: 1,105 lines
- Methods: 45+
- Calculates own indicators: ❌ Violates Rule 3

**After:**
- File: ~950 lines (-155 lines, -14%)
- Methods: 42 (-3 methods)
- Reads pre-calculated indicators: ✅ Rule 3 compliant

---

## Testing Strategy

1. Unit test with enriched data
2. Verify validation catches missing indicators
3. Confirm signal generation uses enriched data
4. Performance comparison (should be faster)

---

**Status:** READY TO IMPLEMENT

