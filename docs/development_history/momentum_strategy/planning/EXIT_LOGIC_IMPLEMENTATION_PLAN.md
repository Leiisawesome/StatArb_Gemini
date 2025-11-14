# Implementation Plan: Hybrid Exit Logic

**Objective:** Implement the NEW hybrid exit logic to generate SELL signals  
**Estimated Effort:** 4-6 hours  
**Priority:** CRITICAL

---

## Phase 1: Config Updates (30 minutes)

### Task 1.1: Update MomentumConfig

**File:** `core_engine/config/strategies.py`

**Add these fields:**

```python
@dataclass
class MomentumConfig(BaseStrategyConfig):
    # ... existing fields ...
    
    # ===== NEW: ATR-based risk management =====
    atr_initial_stop_multiple: float = 1.8
    """ATR multiple for initial stop loss. Default: 1.8x ATR"""
    
    atr_trailing_activation: float = 0.75
    """Profit in ATR multiples to activate trailing stop. Default: 0.75x ATR"""
    
    atr_trailing_distance: float = 0.8
    """Trailing stop distance in ATR multiples. Default: 0.8x ATR"""
    
    # ===== NEW: Composite signal exits =====
    composite_z_exit: float = 0.7
    """Composite Z-score threshold to trigger exit. Default: 0.7"""
    
    composite_pct_exit: float = 55.0
    """Composite percentile threshold to trigger exit. Default: 55.0"""
    
    # ===== NEW: Volume-based exits =====
    volume_failure_multiplier: float = 0.9
    """Volume ratio to trigger volume-failure exit. Default: 0.9x average"""
    
    volume_failure_window: int = 20
    """Lookback window for volume failure check. Default: 20 bars"""
    
    # ===== NEW: Time-based exits =====
    time_stop_minutes: int = 90
    """Maximum holding period in minutes. Default: 90 minutes"""
    
    # ===== DEPRECATED: Remove after migration =====
    # max_holding_period: int  # Use time_stop_minutes instead
    # momentum_threshold_low_multiplier: float  # Not used
```

**Validation:** Ensure all defaults are set correctly

---

## Phase 2: Position Tracking Enhancements (1 hour)

### Task 2.1: Add High Water Mark Tracking

**File:** `core_engine/trading/strategies/implementations/momentum/enhanced_momentum.py`

**Update `_track_position_entry()`:**

```python
def _track_position_entry(self, symbol: str, entry_price: float, 
                         quantity: float, signal_type: SignalType,
                         bar_timestamp: datetime) -> None:
    """
    Track position entry with bar timestamp (NOT datetime.now())
    
    CRITICAL FIX: Use bar_timestamp from enriched data, not wall clock time
    """
    
    if symbol not in self.position_tracker:
        self.position_tracker[symbol] = {
            'direction': 1 if signal_type == SignalType.BUY else -1,
            'avg_entry_price': entry_price,
            'total_quantity': quantity,
            'entry_time': bar_timestamp,  # ✅ Bar timestamp, not datetime.now()
            'scale_ins': 0,
            'high_water_mark': entry_price,  # NEW: Track peak price
            'trailing_stop_activated': False,  # NEW: Track if trailing activated
            'last_update_time': bar_timestamp  # NEW: Track last update
        }
    else:
        # Scale-in logic (update avg price, quantity)
        pos = self.position_tracker[symbol]
        total_cost = pos['avg_entry_price'] * pos['total_quantity'] + entry_price * quantity
        pos['total_quantity'] += quantity
        pos['avg_entry_price'] = total_cost / pos['total_quantity']
        pos['scale_ins'] += 1
        pos['last_update_time'] = bar_timestamp
```

### Task 2.2: Update High Water Mark per Bar

**Add method:**

```python
def _update_high_water_mark(self, symbol: str, current_price: float) -> None:
    """Update high water mark for trailing stop calculation"""
    
    if symbol in self.position_tracker:
        pos = self.position_tracker[symbol]
        
        if pos['direction'] == 1:  # LONG position
            pos['high_water_mark'] = max(pos['high_water_mark'], current_price)
        else:  # SHORT position
            pos['high_water_mark'] = min(pos['high_water_mark'], current_price)
```

---

## Phase 3: Implement NEW Hybrid Exit Logic (2-3 hours)

### Task 3.1: Main Exit Check Method

**Add to `enhanced_momentum.py`:**

```python
async def _check_exit_conditions_hybrid(self, 
                                       symbol: str, 
                                       bar_data: pd.Series,
                                       bar_timestamp: datetime) -> Tuple[bool, str]:
    """
    NEW HYBRID EXIT LOGIC (replaces old _check_exit_conditions)
    
    Checks (in priority order):
    1. ATR-based stop loss (hard stop - immediate exit)
    2. ATR-based trailing stop (if activated - lock in profits)
    3. Composite Z-score deterioration (momentum fading)
    4. Composite percentile deterioration (relative weakness)
    5. Volume failure (no follow-through)
    6. Time stop (maximum holding period)
    
    Args:
        symbol: Symbol to check
        bar_data: Current bar with enriched features (pd.Series)
        bar_timestamp: Timestamp of current bar (NOT datetime.now()!)
    
    Returns:
        (should_exit: bool, exit_reason: str)
    """
    
    if symbol not in self.position_tracker:
        return False, ""
    
    pos = self.position_tracker[symbol]
    direction = pos['direction']  # 1=LONG, -1=SHORT
    entry_price = pos['avg_entry_price']
    entry_time = pos['entry_time']
    current_price = bar_data.get('close', 0)
    
    if current_price <= 0:
        return False, ""
    
    # Get ATR for risk calculations
    atr = bar_data.get('atr', bar_data.get('ATR_14', bar_data.get('atr_normalized', 0)))
    
    # ===== EXIT CHECK 1: ATR-based HARD STOP LOSS =====
    if atr > 0:
        stop_distance = atr * self.config.atr_initial_stop_multiple
        
        if direction == 1:  # LONG position
            hard_stop = entry_price - stop_distance
            if current_price <= hard_stop:
                logger.info(f"🛑 {symbol} ATR stop loss: ${current_price:.2f} <= ${hard_stop:.2f} (entry ${entry_price:.2f} - {self.config.atr_initial_stop_multiple}×ATR)")
                return True, "atr_stop_loss"
        else:  # SHORT position
            hard_stop = entry_price + stop_distance
            if current_price >= hard_stop:
                logger.info(f"🛑 {symbol} ATR stop loss: ${current_price:.2f} >= ${hard_stop:.2f}")
                return True, "atr_stop_loss"
    
    # ===== EXIT CHECK 2: ATR-based TRAILING STOP =====
    if atr > 0:
        unrealized_pnl = (current_price - entry_price) * direction
        activation_threshold = atr * self.config.atr_trailing_activation
        
        # Check if trailing stop should activate
        if unrealized_pnl >= activation_threshold:
            if not pos.get('trailing_stop_activated', False):
                pos['trailing_stop_activated'] = True
                logger.info(f"✅ {symbol} Trailing stop ACTIVATED: Profit ${unrealized_pnl:.2f} >= ${activation_threshold:.2f}")
            
            high_water_mark = pos.get('high_water_mark', current_price)
            trailing_distance = atr * self.config.atr_trailing_distance
            
            if direction == 1:  # LONG position
                trailing_stop = high_water_mark - trailing_distance
                if current_price <= trailing_stop:
                    logger.info(f"📉 {symbol} ATR trailing stop: ${current_price:.2f} <= ${trailing_stop:.2f} (HWM ${high_water_mark:.2f} - {self.config.atr_trailing_distance}×ATR)")
                    return True, "atr_trailing_stop"
            else:  # SHORT position
                trailing_stop = high_water_mark + trailing_distance
                if current_price >= trailing_stop:
                    logger.info(f"📈 {symbol} ATR trailing stop: ${current_price:.2f} >= ${trailing_stop:.2f}")
                    return True, "atr_trailing_stop"
    
    # ===== EXIT CHECK 3: COMPOSITE Z-SCORE DETERIORATION =====
    composite_z = bar_data.get('composite_z', 0)
    if composite_z < self.config.composite_z_exit:
        logger.info(f"📊 {symbol} Composite Z deterioration: {composite_z:.2f} < {self.config.composite_z_exit:.2f}")
        return True, "composite_z_deterioration"
    
    # ===== EXIT CHECK 4: COMPOSITE PERCENTILE DETERIORATION =====
    composite_pct = bar_data.get('composite_pct', 50)
    if composite_pct < self.config.composite_pct_exit:
        logger.info(f"📊 {symbol} Composite percentile deterioration: {composite_pct:.1f} < {self.config.composite_pct_exit:.1f}")
        return True, "composite_pct_deterioration"
    
    # ===== EXIT CHECK 5: VOLUME FAILURE =====
    volume = bar_data.get('volume', 0)
    volume_mean = bar_data.get('volume_mean_20', bar_data.get('volume_ratio', 0))
    
    if volume_mean > 0:
        volume_ratio = volume / volume_mean
    else:
        volume_ratio = 1.0
    
    if volume_ratio < self.config.volume_failure_multiplier:
        logger.info(f"📉 {symbol} Volume failure: {volume_ratio:.2f}x < {self.config.volume_failure_multiplier:.2f}x avg")
        return True, "volume_failure"
    
    # ===== EXIT CHECK 6: TIME STOP =====
    time_in_position_sec = (bar_timestamp - entry_time).total_seconds()
    time_in_position_min = time_in_position_sec / 60.0
    
    if time_in_position_min >= self.config.time_stop_minutes:
        logger.info(f"⏰ {symbol} Time stop: {time_in_position_min:.1f} min >= {self.config.time_stop_minutes} min")
        return True, "time_stop"
    
    # No exit condition met
    return False, ""
```

---

## Phase 4: Wire Exit Logic into update_positions() (30 minutes)

### Task 4.1: Call Exit Check Every Bar

**Update `update_positions()` method:**

```python
async def update_positions(self, enriched_data: Dict[str, pd.DataFrame]) -> List[StrategySignal]:
    """
    Update position tracking and check exit conditions
    
    CRITICAL: This is called EVERY BAR during simulation
    Must check exit conditions for ALL active positions
    
    Args:
        enriched_data: Dict[symbol, enriched DataFrame with indicators/features]
    
    Returns:
        List of EXIT signals (SELL orders)
    """
    exit_signals = []
    
    for symbol, data in enriched_data.items():
        if symbol in self.position_tracker and not data.empty:
            latest_bar = data.iloc[-1]
            bar_timestamp = latest_bar.name if isinstance(latest_bar.name, datetime) else datetime.now()
            current_price = latest_bar.get('close', 0)
            
            # Update high water mark (for trailing stops)
            self._update_high_water_mark(symbol, current_price)
            
            # ✅ CHECK EXIT CONDITIONS (NEW HYBRID LOGIC)
            should_exit, exit_reason = await self._check_exit_conditions_hybrid(
                symbol, latest_bar, bar_timestamp
            )
            
            if should_exit:
                logger.info(f"📉 Exit triggered for {symbol}: {exit_reason}")
                
                # Generate EXIT signal
                pos = self.position_tracker[symbol]
                exit_signal = StrategySignal(
                    strategy_id=self.strategy_id,
                    symbol=symbol,
                    signal_type=SignalType.SELL if pos['direction'] == 1 else SignalType.BUY,
                    strength=1.0,
                    confidence=0.9,
                    quantity=pos['total_quantity'],
                    timestamp=bar_timestamp,
                    signal_source=self.__class__.__name__,
                    signal_reason=exit_reason,
                    additional_data={
                        'action': 'exit',
                        'exit_reason': exit_reason,
                        'entry_price': pos['avg_entry_price'],
                        'exit_price': current_price,
                        'holding_time_min': (bar_timestamp - pos['entry_time']).total_seconds() / 60.0
                    }
                )
                
                exit_signals.append(exit_signal)
                
                # Clean up position tracking
                del self.position_tracker[symbol]
                logger.info(f"🔄 Position closed: {symbol} ({exit_reason})")
    
    return exit_signals
```

---

## Phase 5: Testing (1-2 hours)

### Task 5.1: Unit Tests

**Create:** `tests/unit/test_momentum_exit_logic.py`

**Test cases:**
1. ATR stop loss triggers correctly
2. ATR trailing stop activates and triggers
3. Composite Z-score exit triggers
4. Composite percentile exit triggers
5. Volume failure exit triggers
6. Time stop triggers
7. Multiple exit conditions (priority order)

### Task 5.2: Integration Test

**Run:** `python3 tests/integration/live_data_validation.py`

**Expected outcomes:**
- ✅ BUY signals generate (same as before)
- ✅ **SELL signals generate when exit conditions met**
- ✅ Positions close properly
- ✅ P&L calculated correctly

### Task 5.3: Verification Checklist

- [ ] Exit signals logged with reason
- [ ] Position tracker cleaned up after exit
- [ ] No orphaned positions
- [ ] Time calculations use bar timestamp (not wall clock)
- [ ] ATR values correctly accessed from enriched data
- [ ] Composite Z/percentile values correctly accessed
- [ ] Volume ratio calculated correctly

---

## Phase 6: Documentation (30 minutes)

### Task 6.1: Update Strategy Documentation

**File:** `docs/MOMENTUM_STRATEGY_SPECIFICATION.md`

**Add section:** "Exit Logic - Hybrid Multi-Condition System"

### Task 6.2: Update Config Documentation

**File:** `docs/CONFIGURATION_GUIDE.md`

**Document new `MomentumConfig` fields**

---

## Rollout Plan

### Step 1: Implement (Do First)
1. Update `MomentumConfig` (Phase 1)
2. Add position tracking enhancements (Phase 2)
3. Implement hybrid exit logic (Phase 3)
4. Wire into `update_positions()` (Phase 4)

### Step 2: Test (Before Commit)
1. Unit tests (Phase 5.1)
2. Integration test (Phase 5.2)
3. Verify checklist (Phase 5.3)

### Step 3: Document (After Testing)
1. Strategy docs (Phase 6.1)
2. Config docs (Phase 6.2)

### Step 4: Commit
```bash
git add core_engine/config/strategies.py
git add core_engine/trading/strategies/implementations/momentum/enhanced_momentum.py
git add tests/unit/test_momentum_exit_logic.py
git commit -m "feat: Implement hybrid exit logic with ATR stops, composite signals, and volume failure detection"
```

---

## Success Criteria

✅ **Exit signals generate** when conditions met  
✅ **All 6 exit conditions** implemented and working  
✅ **Position tracking** uses bar timestamps (not wall clock)  
✅ **Tests pass** (unit + integration)  
✅ **No regressions** in existing functionality  
✅ **Documentation complete**  

---

## Estimated Timeline

| Phase | Duration | Can Parallelize? |
|-------|----------|------------------|
| Phase 1: Config | 30 min | No (prerequisite) |
| Phase 2: Tracking | 1 hour | No (prerequisite) |
| Phase 3: Exit Logic | 2-3 hours | No (core work) |
| Phase 4: Integration | 30 min | No (wiring) |
| Phase 5: Testing | 1-2 hours | Partially |
| Phase 6: Docs | 30 min | Yes (parallel) |
| **TOTAL** | **5.5-7.5 hours** | **Sequential** |

**Realistic estimate: 1-2 working days**

---

## Risk Mitigation

### Risk 1: Breaking Existing Logic
**Mitigation:** Keep old `_check_exit_conditions()` as `_check_exit_conditions_legacy()` for fallback

### Risk 2: Performance Impact
**Mitigation:** Profile exit checks, ensure <1ms per symbol per bar

### Risk 3: Missing Edge Cases
**Mitigation:** Comprehensive unit tests with edge cases

---

**Ready to implement? Let me know and I'll start with Phase 1!** 🚀

