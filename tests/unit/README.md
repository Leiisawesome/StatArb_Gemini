# Unit Tests Organization

This directory contains comprehensive unit tests for the StatArb_Gemini core engine, organized by module and functionality.

## Directory Structure

```
tests/unit/
├── analytics/          # Analytics engine tests
├── broker/            # Broker integration tests
├── config/            # Configuration management tests
├── data/              # Data management tests
├── execution/         # Execution engine tests
├── processing/        # Data processing pipeline tests
│   ├── test_pipeline_orchestrator.py         # Phase 2: Pipeline orchestrator (22 tests)
│   ├── test_indicators_engine_comprehensive.py
│   ├── test_feature_engineer.py
│   └── test_signal_generator.py
├── regime/            # Market regime detection tests
├── risk/              # Risk management tests
├── strategies/        # Trading strategies tests
│   ├── phase4_refactoring/                   # Phase 4: Strategy refactoring tests
│   │   ├── test_momentum_refactoring.py      # Phase 4.1 (15 tests)
│   │   ├── test_mean_reversion_refactoring.py # Phase 4.2 (17 tests)
│   │   ├── test_statistical_arbitrage_refactoring.py # Phase 4.3 (15 tests)
│   │   └── test_remaining_strategies.py       # Phase 4.5 (15 tests for 7 strategies)
│   ├── test_all_strategies.py                 # Comprehensive strategy tests
│   ├── test_base_strategy_enhanced.py         # Base strategy framework tests
│   ├── test_strategy_manager.py               # Strategy manager tests
│   ├── test_strategy_manager_pipeline.py      # Phase 3: Pipeline integration
│   └── conftest.py                             # Test configuration
├── system/            # System orchestration tests
├── trading/           # Trading engine tests
└── utils/             # Utility module tests
```

## Test Categories

### 1. Processing Tests (`processing/`)
**Purpose:** Test data processing pipeline components

**Key Tests:**
- `test_pipeline_orchestrator.py` - ProcessingPipelineOrchestrator (Rule 3 enforcer)
- `test_indicators_engine_comprehensive.py` - Technical indicators (29+ indicators)
- `test_feature_engineer.py` - Feature engineering (50+ features)
- `test_signal_generator.py` - Signal generation

**Coverage:** 100+ tests

---

### 2. Strategy Tests (`strategies/`)
**Purpose:** Test trading strategy implementations

#### Core Strategy Tests
- `test_all_strategies.py` - Comprehensive tests for all 10 strategy implementations
- `test_base_strategy_enhanced.py` - Base strategy framework and ISystemComponent integration
- `test_strategy_manager.py` - Strategy manager orchestration
- `test_strategy_manager_pipeline.py` - Strategy manager pipeline integration

#### Phase 4 Refactoring Tests (`strategies/phase4_refactoring/`)
**Purpose:** Validate Phase 4 pipeline refactoring - ensures strategies consume enriched data instead of calculating their own indicators

**Background:**
- **Phase 4** addressed a critical architectural gap where strategies were bypassing the processing pipeline
- All strategies were refactored to consume pre-calculated indicators from `ProcessingPipelineOrchestrator`
- This enforces Rule 3 (Unified Data Flow Pipeline)

**Test Files:**
1. **`test_momentum_refactoring.py`** (15 tests)
   - Validates Momentum strategy consumes enriched data
   - Tests enriched data validation
   - Verifies indicator calculation methods removed
   - Pattern A (Technical) implementation

2. **`test_mean_reversion_refactoring.py`** (17 tests)
   - Validates Mean Reversion strategy integration
   - Tests RSI, Bollinger Bands, ATR from enriched data
   - Pattern A (Technical) implementation

3. **`test_statistical_arbitrage_refactoring.py`** (15 tests)
   - Validates Statistical Arbitrage integration
   - Tests pre-calculated returns usage
   - Pattern B (Statistical) implementation

4. **`test_remaining_strategies.py`** (15 tests for 7 strategies)
   - Factor Strategy (Pattern A)
   - Volatility Strategy (Pattern A)
   - Breakout Strategy (Pattern A)
   - Pairs Trading Strategy (Pattern B)
   - Arbitrage Strategy (Pattern B)
   - Multi-Asset Strategy (Hybrid)
   - Trend Following Strategy (Pattern A)

**Total Phase 4 Tests:** 62 tests
**Pass Rate:** 100% ✅

**Documentation:** See `docs/03_compliance_audits/PHASE4.*.md`

---

### 3. Risk Management Tests (`risk/`)
**Purpose:** Test risk management components

**Key Tests:**
- `test_central_risk_manager.py` - Central risk governance (Rule 4)
- `test_var_calculator.py` - Value at Risk calculations
- `test_exposure_calculator.py` - Position exposure
- `test_correlation_analyzer.py` - Portfolio correlation
- `test_stress_tester_comprehensive.py` - Stress testing

---

### 4. System Tests (`system/`)
**Purpose:** Test system orchestration and integration

**Key Tests:**
- `test_hierarchical_orchestrator.py` - System orchestrator
- `test_isystemcomponent_implementations.py` - Component lifecycle
- `test_central_risk_manager.py` - Risk governance integration

---

### 5. Analytics Tests (`analytics/`)
**Purpose:** Test performance analytics and attribution

**Key Tests:**
- `test_analytics_manager_comprehensive.py`
- `test_metrics_calculator.py`
- `test_performance_analyzer.py`
- `test_attribution_analyzer.py`

---

## Running Tests

### Run All Unit Tests
```bash
pytest tests/unit/ -v
```

### Run Specific Module
```bash
# Processing tests
pytest tests/unit/processing/ -v

# Strategy tests
pytest tests/unit/strategies/ -v

# Phase 4 refactoring tests only
pytest tests/unit/strategies/phase4_refactoring/ -v

# Risk tests
pytest tests/unit/risk/ -v
```

### Run Specific Test File
```bash
pytest tests/unit/processing/test_pipeline_orchestrator.py -v
pytest tests/unit/strategies/phase4_refactoring/test_momentum_refactoring.py -v
```

### Run with Coverage
```bash
pytest tests/unit/ --cov=core_engine --cov-report=html
```

---

## Test Statistics

### Overall Coverage
- **Total Unit Tests:** ~300+ tests
- **Pass Rate:** 100%
- **Code Coverage:** 85%+ (varies by module)

### Module Breakdown
| Module | Tests | Coverage |
|--------|-------|----------|
| Processing | 100+ | 90%+ |
| Strategies | 150+ | 85%+ |
| Risk | 50+ | 90%+ |
| System | 40+ | 85%+ |
| Analytics | 30+ | 80%+ |
| Execution | 40+ | 85%+ |
| Data | 30+ | 85%+ |

---

## Test Conventions

### Naming
- Test files: `test_<component_name>.py`
- Test classes: `Test<ComponentName>`
- Test methods: `test_<functionality>`

### Organization
- Tests organized by module (mirrors `core_engine/` structure)
- Related tests grouped in classes
- Fixtures in `conftest.py` at appropriate levels

### Documentation
- Each test class has docstring explaining purpose
- Complex tests have inline comments
- Edge cases explicitly documented

---

## Continuous Integration

All unit tests run automatically on:
- Every commit (pre-commit hooks)
- Pull requests (GitHub Actions)
- Daily schedule (regression testing)

**Required:** 100% pass rate for merge approval

---

## Related Documentation

- **Integration Tests:** `tests/integration/README.md`
- **Compliance Audits:** `docs/03_compliance_audits/`
- **Architecture Rules:** `.cursor/rules/TIER-1-ARCHITECTURAL-RULES/`

---

**Last Updated:** October 25, 2025
**Status:** ✅ Organized and Validated

