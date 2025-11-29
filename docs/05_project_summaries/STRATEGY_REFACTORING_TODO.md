# Strategy Refactoring: Separation of Concerns

## Objective
Refactor strategies to be **pure signal generators** while delegating position management to PositionBook (SSOT) and Risk Manager.

## Architectural Principle
> **Strategies should ONLY concern themselves with generating signals, not position tracking.**
> Position management is the responsibility of the Risk Manager and PositionBook (Single Source of Truth).

---

## TODO List - ALL COMPLETE ✅

### Phase 1: Base Strategy Cleanup ✅
- [x] 1. Mark `self._positions` in `EnhancedBaseStrategy` as DEPRECATED (for backward compat)
- [x] 2. Mark `update_positions()` abstract method as DEPRECATED  
- [x] 3. Mark `calculate_position_size()` as DEPRECATED (move to Risk Manager)
- [x] 4. Add optional read-only position query via PositionBook (`set_position_book()`)
- [x] 5. Add `self._position_book: Optional[IPositionBook]` for read-only position access
- [x] 6. Add `_has_position()` and `_get_position_quantity()` helper methods

### Phase 2: Strategy Implementations Cleanup ✅
- [x] 7. Add deprecation notice to `EnhancedMeanReversionStrategy` position tracking
- [x] 8. Add deprecation notice to `EnhancedBreakoutStrategy` position tracking
- [x] 9. Add deprecation notice to `EnhancedFactorStrategy` position tracking
- [x] 10. Add deprecation notice to `EnhancedVolatilityStrategy` position tracking
- [x] 11. Add deprecation notice to `EnhancedMultiAssetStrategy` position tracking
- [x] 12. Add deprecation notice to `EnhancedArbitrageStrategy` (no active_positions field)
- [x] 13. Add deprecation notice to `EnhancedStatisticalArbitrageStrategy` position tracking
- [x] 14. Add deprecation notice to `EnhancedPairsTradingStrategy` position tracking
- [x] 15. Add deprecation notice to `EnhancedTrendFollowingStrategy` position tracking
- [x] 16. Add deprecation notice to `EnhancedMomentumStrategy` position tracking

### Phase 3: Strategy Engine Cleanup ✅
- [x] 17. Mark `self._positions` in `BaseStrategy` (strategy_engine.py) as DEPRECATED

### Phase 4: Testing & Validation ✅
- [x] 18. Run all tests to ensure no regressions - **207 passed** ✅

---

## Implementation Notes

### What Strategies SHOULD Do:
1. **Analyze market data** - Read enriched data with indicators
2. **Generate signals** - Create `StrategySignal` objects with entry/exit recommendations
3. **Calculate signal strength/confidence** - Determine quality of trading opportunity
4. **Respect regime context** - Adapt signal generation based on market regime

### What Strategies SHOULD NOT Do:
1. ❌ Track positions internally (use PositionBook via read-only query)
2. ❌ Manage stop-losses/profit-targets (Risk Manager responsibility)
3. ❌ Calculate position sizes (Risk Manager responsibility)
4. ❌ Track P&L (PositionBook/Analytics responsibility)

### Migration Path for Strategies:
```python
# OLD (deprecated):
self.active_positions: Dict[str, Dict[str, Any]] = {}
self.entry_prices: Dict[str, float] = {}
self.stop_losses: Dict[str, float] = {}

# NEW (recommended):
# Query PositionBook for read-only position info if needed for signal generation
if self._position_book:
    current_position = self._position_book.get_position(symbol)
```

### Read-Only Position Access Pattern:
```python
def set_position_book(self, position_book: IPositionBook) -> None:
    """Set PositionBook for read-only position queries (optional)."""
    self._position_book = position_book

def _has_position(self, symbol: str) -> bool:
    """Check if there's an existing position (read-only query)."""
    if self._position_book:
        pos = self._position_book.get_position(symbol)
        return pos is not None and pos.net_quantity != 0
    return False

def _get_position_quantity(self, symbol: str) -> float:
    """Get current position quantity (read-only query)."""
    if self._position_book:
        pos = self._position_book.get_position(symbol)
        return pos.net_quantity if pos else 0.0
    return 0.0
```

---

## Completed: November 29, 2025 ✅

### Summary of Changes

**Files Modified:**
1. `core_engine/trading/strategies/base_strategy_enhanced.py` - Added PositionBook integration, deprecation notices
2. `core_engine/trading/strategies/strategy_engine.py` - Added deprecation notices to BaseStrategy
3. `core_engine/trading/strategies/implementations/mean_reversion/enhanced_mean_reversion.py`
4. `core_engine/trading/strategies/implementations/breakout/enhanced_breakout.py`
5. `core_engine/trading/strategies/implementations/factor/enhanced_factor.py`
6. `core_engine/trading/strategies/implementations/volatility/enhanced_volatility.py`
7. `core_engine/trading/strategies/implementations/multi_asset/enhanced_multi_asset.py`
8. `core_engine/trading/strategies/implementations/arbitrage/enhanced_arbitrage.py`
9. `core_engine/trading/strategies/implementations/statistical_arbitrage/enhanced_statistical_arbitrage.py`
10. `core_engine/trading/strategies/implementations/pairs_trading/enhanced_pairs_trading.py`
11. `core_engine/trading/strategies/implementations/trend_following/enhanced_trend_following.py`
12. `core_engine/trading/strategies/implementations/momentum/enhanced_momentum.py`

**New Features in EnhancedBaseStrategy:**
- `set_position_book(position_book)` - Link PositionBook for read-only access
- `_has_position(symbol)` - Check if position exists
- `_get_position_quantity(symbol)` - Get position quantity

**Test Results:** 207 passed ✅

All strategy files have been updated with deprecation notices for position tracking fields.
The architectural principle is now documented and strategies are ready for gradual migration.
