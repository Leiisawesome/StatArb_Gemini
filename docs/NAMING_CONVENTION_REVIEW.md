# Naming Convention Review - Phase 9 / Broker Integration

**Date**: October 13, 2025  
**Status**: Proposed Changes

---

## 🎯 Problem Statement

Current naming conventions are not intuitive:
- `tests/phase9/` → Doesn't clearly indicate it's for broker integration testing
- `core_engine/config/phase9_config.py` → Generic "phase9" doesn't describe the configuration purpose
- "Phase 9" is a project timeline reference, not a functional description

---

## 📋 Proposed Naming Changes

### 1. Test Directory Structure

**Current**:
```
tests/
├── phase9/
│   ├── test_day1_config.py
│   ├── test_day2_connection.py
│   └── test_day2_error_handling.py
```

**Proposed Option A** (Descriptive):
```
tests/
├── broker_integration/
│   ├── test_config_loading.py
│   ├── test_broker_connection.py
│   └── test_error_handling.py
```

**Proposed Option B** (More Specific):
```
tests/
├── live_trading/
│   ├── test_broker_config.py
│   ├── test_alpaca_connection.py
│   └── test_connection_errors.py
```

**Proposed Option C** (Hybrid):
```
tests/
├── broker_integration/
│   ├── config/
│   │   └── test_broker_config_loading.py
│   ├── connection/
│   │   ├── test_alpaca_connection.py
│   │   └── test_connection_error_handling.py
│   ├── orders/
│   │   ├── test_market_orders.py
│   │   └── test_limit_orders.py
│   └── positions/
│       └── test_position_tracking.py
```

---

### 2. Configuration Files

**Current**:
```
core_engine/config/
├── phase9_config.py
├── component_config.py
├── system_config.py
└── unified_config.py
```

**Proposed**:
```
core_engine/config/
├── broker_config.py  (was: phase9_config.py)
├── component_config.py
├── system_config.py
└── unified_config.py
```

**Alternative (More Specific)**:
```
core_engine/config/
├── live_trading_config.py  (was: phase9_config.py)
├── component_config.py
├── system_config.py
└── unified_config.py
```

---

### 3. Documentation Files

**Current**:
```
docs/
├── PHASE_9_QUICK_START.md
├── PHASE_9_WEEK_1_DAY_1-2.md
└── .env.example (references PHASE_9_*)
```

**Proposed**:
```
docs/
├── BROKER_INTEGRATION_QUICK_START.md
├── BROKER_INTEGRATION_WEEK_1.md
└── .env.example (use BROKER_* or TRADING_*)
```

---

### 4. Environment Variables

**Current in .env**:
```bash
# Phase 9 specific
PHASE_9_TRADING_MODE=paper
PHASE_9_MAX_POSITION_SIZE=100
PHASE_9_PAPER_TRADING_ONLY=true
```

**Proposed Option A** (Simple):
```bash
TRADING_MODE=paper
MAX_POSITION_SIZE=100
PAPER_TRADING_ONLY=true
```

**Proposed Option B** (Namespaced):
```bash
BROKER_TRADING_MODE=paper
BROKER_MAX_POSITION_SIZE=100
BROKER_PAPER_TRADING_ONLY=true
```

**Proposed Option C** (Feature-based):
```bash
LIVE_TRADING_MODE=paper
LIVE_MAX_POSITION_SIZE=100
LIVE_PAPER_TRADING_ONLY=true
```

---

## 🔍 Detailed Analysis

### Test Directory Naming

**Recommendation**: `tests/broker_integration/` with subdirectories

**Rationale**:
- ✅ **Descriptive**: Immediately clear what's being tested
- ✅ **Consistent**: Matches other test directories (unit, integration, performance)
- ✅ **Scalable**: Can add subdirectories for different brokers or test types
- ✅ **Searchable**: Easy to find in IDE and git
- ✅ **Future-proof**: Not tied to project timeline

**Subdirectory Structure**:
```
tests/broker_integration/
├── __init__.py
├── README.md
├── config/
│   ├── __init__.py
│   └── test_broker_config_loading.py
├── connection/
│   ├── __init__.py
│   ├── test_alpaca_connection.py
│   ├── test_ib_connection.py (future)
│   └── test_connection_errors.py
├── trading/
│   ├── __init__.py
│   ├── orders/
│   │   ├── test_market_orders.py
│   │   ├── test_limit_orders.py
│   │   └── test_stop_orders.py
│   └── positions/
│       ├── test_position_tracking.py
│       └── test_pnl_calculation.py
└── data_feeds/
    ├── __init__.py
    ├── test_live_market_data.py
    └── test_websocket_streaming.py
```

---

### Configuration File Naming

**Recommendation**: `broker_config.py`

**Rationale**:
- ✅ **Clear Purpose**: Immediately identifies broker-related configuration
- ✅ **Consistent**: Matches naming pattern (component_config, system_config)
- ✅ **Accurate**: Contains broker credentials, risk limits, trading settings
- ✅ **Flexible**: Can encompass multiple brokers (Alpaca, IB, etc.)

**Alternative Options**:
1. `live_trading_config.py` - Emphasizes live trading aspect
2. `trading_broker_config.py` - Very explicit
3. `production_broker_config.py` - Emphasizes production use

---

### Environment Variable Naming

**Recommendation**: Use `BROKER_*` or `TRADING_*` prefixes

**Current Issues**:
- `PHASE_9_*` is not descriptive
- Ties configuration to project timeline
- Not clear what feature it relates to

**Proposed Structure**:
```bash
# ============================================
# Broker Integration Configuration
# ============================================

# Broker Selection
BROKER_TYPE=alpaca
TRADING_MODE=paper

# Alpaca Configuration
ALPACA_API_KEY=REDACTED
ALPACA_SECRET_KEY=REDACTED
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Trading Risk Limits
TRADING_MAX_POSITION_SIZE=100
TRADING_MAX_POSITION_VALUE=1000.00
TRADING_MAX_DAILY_TRADES=10
TRADING_MAX_DAILY_LOSS=100.00

# Safety Settings
TRADING_PAPER_ONLY=true
TRADING_REQUIRE_APPROVAL=true
TRADING_ENABLE_KILL_SWITCH=true
```

---

## 📦 Migration Plan

### Step 1: Create New Structure (Non-Breaking)
1. Create new directories/files alongside old ones
2. Update imports to use both old and new names (with deprecation warnings)
3. Copy tests to new locations

### Step 2: Update References (Gradual)
1. Update documentation to reference new names
2. Update new code to use new names
3. Update .env.example with new variable names

### Step 3: Deprecate Old Names (Phase Out)
1. Add deprecation warnings to old imports
2. Update all internal references
3. Document migration in CHANGELOG

### Step 4: Remove Old Names (Final)
1. Remove old files after grace period
2. Update all tests
3. Final documentation update

---

## 🎯 Recommended Action Plan

### Immediate Changes (Today)

**Rename Test Directory**:
```bash
# Rename directory
mv tests/phase9 tests/broker_integration

# Rename test files for clarity
cd tests/broker_integration
mv test_day1_config.py test_broker_config_loading.py
mv test_day2_connection.py test_alpaca_connection.py
mv test_day2_error_handling.py test_connection_error_handling.py
```

**Rename Config File**:
```bash
cd core_engine/config
mv phase9_config.py broker_config.py
```

**Update Imports**:
- Update all imports from `phase9_config` to `broker_config`
- Update all imports referencing `tests/phase9`

**Update Documentation**:
- Rename documentation files
- Update references in README
- Update .env.example variable names

---

### Environment Variable Migration

**Create Updated .env.example**:
```bash
# Old variables (deprecated)
#PHASE_9_TRADING_MODE=paper        # Use TRADING_MODE instead
#PHASE_9_MAX_POSITION_SIZE=100     # Use TRADING_MAX_POSITION_SIZE instead

# New variables
TRADING_MODE=paper
BROKER_TYPE=alpaca
TRADING_MAX_POSITION_SIZE=100
TRADING_MAX_POSITION_VALUE=1000.00
```

**Update Config Loader**:
Add fallback for old variable names during transition:
```python
# Support old and new variable names
trading_mode = (
    os.getenv("TRADING_MODE") or 
    os.getenv("PHASE_9_TRADING_MODE") or 
    "paper"
)
```

---

## 📊 Naming Convention Standards

### General Principles

1. **Descriptive over Terse**: `broker_config` > `phase9_config`
2. **Feature-based over Timeline-based**: `broker_integration` > `phase9`
3. **Consistent Patterns**: Match existing naming conventions
4. **Future-proof**: Not tied to project phases or temporary structure
5. **Searchable**: Easy to find with IDE search

### Test File Naming

**Pattern**: `test_<component>_<action>.py`

**Examples**:
- ✅ `test_broker_config_loading.py`
- ✅ `test_alpaca_connection.py`
- ✅ `test_market_order_submission.py`
- ❌ `test_day1_config.py`
- ❌ `test_phase9.py`

### Configuration File Naming

**Pattern**: `<domain>_config.py`

**Examples**:
- ✅ `broker_config.py`
- ✅ `trading_config.py`
- ✅ `data_feed_config.py`
- ❌ `phase9_config.py`
- ❌ `config_9.py`

### Environment Variable Naming

**Pattern**: `<DOMAIN>_<SETTING_NAME>`

**Examples**:
- ✅ `BROKER_TYPE`
- ✅ `TRADING_MODE`
- ✅ `ALPACA_API_KEY`
- ❌ `PHASE_9_MODE`
- ❌ `P9_KEY`

---

## 🔄 Impact Assessment

### Files Affected by Renaming

**Test Files** (3 files):
- `tests/phase9/` → `tests/broker_integration/`
- All test files within

**Config Files** (1 file):
- `core_engine/config/phase9_config.py` → `broker_config.py`

**Import References** (~5-10 files):
- Test files
- Adapter files
- Documentation examples

**Documentation** (3 files):
- `PHASE_9_QUICK_START.md`
- `PHASE_9_WEEK_1_DAY_1-2.md`
- `.env.example`

**Environment Variables**:
- `.env` file (user's local)
- `.env.example` template
- Config loader code

---

## ✅ Recommended Changes Summary

### Priority 1: High Impact, Low Risk

1. **Rename test directory**: `phase9` → `broker_integration`
2. **Rename config file**: `phase9_config.py` → `broker_config.py`
3. **Update test filenames**: Remove "day1", "day2" references
4. **Update documentation filenames**: Remove "PHASE_9" prefix

### Priority 2: Medium Impact, Gradual Transition

5. **Update environment variables**: Add new names with backward compatibility
6. **Update documentation content**: Replace phase references with feature descriptions
7. **Reorganize test subdirectories**: Add config/, connection/, trading/ subdirs

### Priority 3: Nice to Have, Future Enhancement

8. **Add broker-specific subdirectories**: alpaca/, ib/, etc.
9. **Create consistent naming across all test directories**
10. **Document naming conventions for future development**

---

## 🤔 Questions for Discussion

1. **Test Directory**: Do you prefer:
   - `broker_integration/` (broad, flexible)
   - `live_trading/` (specific to feature)
   - `production_broker/` (emphasizes production)

2. **Config File**: Do you prefer:
   - `broker_config.py` (simple, clear)
   - `live_trading_config.py` (feature-specific)
   - `production_broker_config.py` (very explicit)

3. **Environment Variables**: Do you prefer:
   - No prefix: `TRADING_MODE`
   - `BROKER_*`: `BROKER_TRADING_MODE`
   - `TRADING_*`: `TRADING_MODE`, `TRADING_MAX_POSITION_SIZE`

4. **Migration Timeline**: 
   - Rename everything now? (breaking change)
   - Gradual migration with backward compatibility?
   - Keep old names, only use new names for new code?

---

## 📝 Next Steps

Please review and let me know:
1. Which naming options you prefer
2. Whether you want immediate renaming or gradual migration
3. Any other naming concerns in the codebase

Once you approve the naming convention, I can:
1. Execute the renaming
2. Update all imports and references
3. Update documentation
4. Test that everything still works

---

**Document Version**: 1.0  
**Author**: GitHub Copilot  
**Status**: Awaiting Review
