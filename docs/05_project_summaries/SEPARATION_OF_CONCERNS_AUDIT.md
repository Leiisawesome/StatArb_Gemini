# Separation of Concerns Audit Report

**Date:** November 29, 2025  
**Scope:** core_engine architectural compliance audit

---

## Executive Summary

Overall, the codebase demonstrates **GOOD** separation of concerns with clear domain boundaries. However, there are several areas requiring attention:

| Domain | Status | Issues Found |
|--------|--------|--------------|
| **Position** | ⚠️ NEEDS CLEANUP | Multiple Position classes across files |
| **Portfolio** | ✅ COMPLIANT | Proper layering |
| **Signal** | ⚠️ MINOR ISSUE | 2 Signal types (TradingSignal vs StrategySignal) |
| **Risk** | ✅ COMPLIANT | CentralRiskManager as SSOT authority |
| **Regime** | ✅ COMPLIANT | Clean separation in `core_engine/regime/` |
| **Order** | ✅ COMPLIANT | Single source in `type_definitions/orders.py` |
| **Execution** | ✅ COMPLIANT | UnifiedExecutionEngine under Risk authority |
| **Data** | ⚠️ DEPRECATED ITEMS | Legacy configs need removal |
| **Analytics** | ✅ COMPLIANT | Clean separation |
| **Strategy** | ✅ COMPLIANT | Position tracking deprecated per SSOT |

---

## Detailed Findings

### 1. POSITION Domain ⚠️ NEEDS CLEANUP

**Issue:** Multiple `Position` class definitions exist across the codebase.

| Location | Class | Status |
|----------|-------|--------|
| `core_engine/trading/position_book.py` | `BookPosition` | ✅ **SSOT** |
| `core_engine/type_definitions/portfolio.py` | `Position` | ⚠️ Lightweight type |
| `core_engine/type_definitions/broker_types.py` | `Position` | ⚠️ Broker-specific |
| `core_engine/trading/portfolio/position_manager.py` | `Position` | ❌ **DUPLICATE** |
| `core_engine/trading/strategies/strategy_engine.py` | `StrategyPosition` | ⚠️ DEPRECATED |
| `core_engine/trading/execution/fill_processor.py` | `PositionManager` | ❌ **DEPRECATED** |

**Recommendation:**
1. `BookPosition` in `position_book.py` should be the SSOT
2. Mark `portfolio/position_manager.py::Position` as deprecated
3. Remove or consolidate `type_definitions/portfolio.py::Position`
4. Keep `broker_types.py::Position` for broker API compatibility only

---

### 2. SIGNAL Domain ⚠️ MINOR ISSUE

**Issue:** Two Signal types exist with overlapping purposes.

| Location | Class | Purpose |
|----------|-------|---------|
| `trading/strategies/strategy_engine.py` | `StrategySignal` | Strategy-generated signals |
| `trading/strategies/manager.py` | `TradingSignal` | Aggregated trading signals |

**Analysis:**
- `StrategySignal` is produced by individual strategies
- `TradingSignal` is the aggregated result after multi-strategy coordination
- This is intentional design (strategy → aggregation → execution)

**Recommendation:** Document the signal flow explicitly:
```
Strategy.generate_signals() → StrategySignal
↓
StrategyManager.aggregate() → TradingSignal  
↓
CentralRiskManager.authorize() → ExecutionRequest
```

---

### 3. RISK Domain ✅ COMPLIANT

**Architecture:**
- `core_engine/system/central_risk_manager.py` - **Central Authority (SSOT)**
- `core_engine/risk/manager_enhanced.py` - Risk calculation components

**Compliance:**
- All trading decisions flow through `CentralRiskManager`
- `UnifiedExecutionEngine` operates under Risk authority
- Position tracking delegated to `PositionBook` (SSOT)

---

### 4. REGIME Domain ✅ COMPLIANT

**Clean separation in `core_engine/regime/`:**
- `engine.py` - Main regime engine
- `regime_detector.py` - Detection algorithms
- `regime_classifier.py` - Classification logic
- `regime_indicators.py` - Indicator calculations
- `regime_transition_manager.py` - State transitions
- `market_regime_analyzer.py` - Market analysis

**No violations found.**

---

### 5. PORTFOLIO Domain ✅ COMPLIANT

**Proper layering:**
- `core_engine/trading/portfolio/manager_enhanced.py` - Portfolio management
- `core_engine/trading/portfolio/allocation_engine.py` - Allocation logic
- `core_engine/trading/portfolio/rebalancer.py` - Rebalancing
- `core_engine/trading/portfolio/cash_manager.py` - Cash management

**Integration with PositionBook (SSOT) is correct.**

---

### 6. ORDER Domain ✅ COMPLIANT

**Single source of truth:**
- `core_engine/type_definitions/orders.py`
  - `Order` - Core order type
  - `OrderType` - Order type enum
  - `OrderStatus` - Status enum
  - `OrderSide` - Side enum
  - `ExecutionResult` - Execution result

**All other modules import from this canonical source.**

---

### 7. EXECUTION Domain ✅ COMPLIANT

**Proper hierarchy:**
- `core_engine/system/unified_execution_engine.py` - Central execution (under Risk authority)
- `core_engine/trading/execution/execution_engine.py` - Execution logic
- `core_engine/trading/execution/fill_processor.py` - Fill processing

**Key compliance:** UnifiedExecutionEngine requires `ExecutionAuthorization` from CentralRiskManager.

---

### 8. DATA Domain ⚠️ DEPRECATED ITEMS

**Legacy configs marked for removal:**
- `ClickHouseDataConfig` - Use `DataConfig` instead
- `DataEngineConfig` - Use `DataConfig` instead  
- `ValidationConfiguration` - Use `DataValidationConfig` instead

**Recommendation:** Create migration script to remove deprecated classes.

---

### 9. ANALYTICS Domain ✅ COMPLIANT

**Clean organization:**
- `manager_enhanced.py` - Central analytics manager
- `metrics_calculator.py` - Metrics calculations
- `performance_analyzer.py` - Performance analysis
- `benchmark_analyzer.py` - Benchmark comparison
- `attribution_analyzer.py` - Attribution analysis
- `tca_analyzer.py` - Transaction cost analysis
- `report_generator.py` - Report generation

---

### 10. STRATEGY Domain ✅ COMPLIANT

**Recent refactoring completed:**
- Strategies now focus on signal generation only
- Position tracking deprecated in all 10 strategies
- `PositionBook` integration via `set_position_book()`
- Risk Manager handles position sizing

---

## Action Items

### High Priority
1. **Consolidate Position types** - Mark duplicates as deprecated, document SSOT
2. **Remove deprecated data configs** - Clean up legacy ClickHouse configs

### Medium Priority  
3. **Document Signal flow** - Add architecture doc for StrategySignal → TradingSignal
4. **Audit type_definitions/** - Ensure all enums are imported from canonical sources

### Low Priority
5. **Add deprecation warnings** - Runtime warnings for deprecated classes
6. **Create migration guide** - For teams using deprecated APIs

---

## Compliance Summary

```
✅ Single Source of Truth (SSOT):
   - PositionBook for positions
   - CentralRiskManager for trading authority
   - type_definitions/orders.py for orders
   - type_definitions/strategy.py for SignalType, StrategyType

✅ Clean Domain Boundaries:
   - regime/ - Regime detection only
   - risk/ - Risk calculations only
   - analytics/ - Analytics only
   - trading/strategies/ - Signal generation only

⚠️ Items Needing Attention:
   - Multiple Position class definitions
   - Legacy deprecated configs in data/
```

---

## Appendix: File Count by Domain

| Domain | Files | Status |
|--------|-------|--------|
| `core_engine/regime/` | 8 | ✅ Clean |
| `core_engine/risk/` | 6 | ✅ Clean |
| `core_engine/analytics/` | 9 | ✅ Clean |
| `core_engine/trading/` | ~30 | ⚠️ Position cleanup needed |
| `core_engine/data/` | ~15 | ⚠️ Deprecated configs |
| `core_engine/system/` | ~15 | ✅ Clean |
| `core_engine/type_definitions/` | 9 | ✅ Clean |
| `core_engine/config/` | ~10 | ✅ Clean |
