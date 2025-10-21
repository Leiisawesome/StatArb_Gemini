# StatArb_Gemini Test Suite

**Comprehensive test coverage** for the StatArb_Gemini institutional trading system.

---

## 📁 Test Organization (3-Tier Structure)

### 🎯 Tier 1: Unit Tests (`unit/`)
**Purpose:** Fast, isolated component tests  
**Execution Time:** < 5 seconds  
**Run Frequency:** Every commit

```bash
pytest tests/unit/ -v
```

**Coverage:**
- ✅ 96 unit test files
- ✅ Analytics, Broker, Config, Data
- ✅ Processing (Indicators, Features, Signals)
- ✅ **Regime-aware components** (NEW)
- ✅ Risk, Strategies (10 strategies)
- ✅ System, Trading, Utils

---

### 🔗 Tier 2: Integration Tests (`integration/`)
**Purpose:** Multi-component interaction tests  
**Execution Time:** ~30 seconds  
**Run Frequency:** Pre-merge

```bash
pytest tests/integration/ -v
```

**Coverage:**
- ✅ Component integration
- ✅ End-to-end workflows
- ✅ Edge cases & failure scenarios
- ✅ Monitoring & performance
- ✅ Stress testing
- ✅ System-level integration

---

### 🎭 Tier 3: Specialized Tests

#### 3A: Backtest Tests (`backtest/`)
**Purpose:** Backtest engine validation  
**Execution Time:** ~2 minutes  
**Run Frequency:** Nightly

```bash
pytest tests/backtest/ -v
```

**Coverage:** 14 phase-based tests (Phase 0-9)

#### 3B: Functional Tests (`functional/`)
**Purpose:** Layer-by-layer functional validation  
**Execution Time:** ~1 minute  
**Run Frequency:** Pre-release

```bash
pytest tests/functional/ -v
```

**Coverage:** 6-layer architecture validation

#### 3C: Performance Tests (`performance/`)
**Purpose:** Performance benchmarking & profiling  
**Execution Time:** ~5 minutes  
**Run Frequency:** Weekly

```bash
pytest tests/performance/ -v
```

**Coverage:**
- Benchmarks
- Profiling (memory, CPU)
- Stress tests
- Throughput testing
- Latency testing

#### 3D: Production Tests (`production/`)
**Purpose:** Production readiness validation  
**Execution Time:** ~2 minutes  
**Run Frequency:** Pre-deployment

```bash
pytest tests/production/ -v
```

**Coverage:** Failover, load testing, stress testing

#### 3E: Compliance Tests (`compliance/`)
**Purpose:** Regulatory & rule compliance  
**Execution Time:** ~1 minute  
**Run Frequency:** Weekly

```bash
pytest tests/compliance/tests/ -v
```

**Coverage:**
- `audits/` - Audit controls & reporting
- `frameworks/` - Compliance frameworks
- `tests/` - Compliance validation tests

#### 3F: Strategy Assessment (`strategy_assessment/`)
**Purpose:** Strategy evaluation & validation  
**Execution Time:** ~3 minutes  
**Run Frequency:** On-demand

#### 3G: Broker Integration (`broker_integration/`)
**Purpose:** Broker connectivity testing  
**Execution Time:** ~30 seconds  
**Run Frequency:** Pre-production

#### 3H: Load Testing (`load_testing/`)
**Purpose:** System load & scalability testing  
**Execution Time:** ~10 minutes  
**Run Frequency:** Weekly

#### 3I: Optimization Tests (`optimization/`)
**Purpose:** Parameter & strategy optimization  
**Execution Time:** ~1 minute  
**Run Frequency:** On-demand

---

## 🚀 Quick Start

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Tier
```bash
# Fast unit tests only
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# Full validation (all tiers)
pytest tests/unit/ tests/integration/ tests/functional/ -v
```

### Run by Category
```bash
# Processing pipeline tests
pytest tests/unit/processing/ -v

# Regime-aware tests
pytest tests/unit/regime/ -v

# Strategy tests
pytest tests/unit/strategies/ -v

# All backtest tests
pytest tests/backtest/ -v
```

---

## 📊 Test Metrics

| Category | Files | Tests | Coverage | Speed |
|----------|-------|-------|----------|-------|
| **Unit** | 96 | 500+ | 85%+ | ⚡ Fast |
| **Integration** | 35+ | 150+ | 80%+ | 🏃 Medium |
| **Backtest** | 14 | 50+ | 90%+ | 🐢 Slow |
| **Functional** | 10 | 40+ | 85%+ | 🏃 Medium |
| **Performance** | 30+ | 100+ | N/A | 🐌 Very Slow |
| **Total** | **200+** | **1000+** | **85%+** | **Mixed** |

---

## 🧪 Test Naming Conventions

### Unit Tests
```python
# Format: test_{component}_{functionality}.py
test_technical_indicators.py
test_regime_aware_pipeline.py
test_enhanced_momentum.py
```

### Integration Tests
```python
# Format: test_{workflow}_{integration}.py
test_data_pipeline_integration.py
test_strategy_risk_integration.py
```

### Functional Tests
```python
# Format: layer{N}_{layer_name}_tests.py
layer1_system_orchestration_tests.py
layer4_core_processing_tests.py
```

---

## 🔧 Test Utilities

### Fixtures (`fixtures/`)
- `core_fixtures.py` - Core component fixtures
- `data_fixtures.py` - Market data fixtures
- `integration_fixtures.py` - Integration test fixtures
- `mock_factories.py` - Mock object factories
- `strategy_fixtures.py` - Strategy test fixtures

### Helpers (`utils/`)
- `assertions.py` - Custom assertions
- `builders.py` - Test data builders
- `helpers.py` - Test helper functions

### Configuration (`conftest.py`)
- Global pytest configuration
- Shared fixtures
- Test session setup/teardown

---

## 📝 Adding New Tests

### Step 1: Choose Tier
- **Unit** - Testing single component in isolation
- **Integration** - Testing component interactions
- **Specialized** - Specific test category (backtest, performance, etc.)

### Step 2: Choose Directory
```bash
# Unit test for regime component
tests/unit/regime/test_new_feature.py

# Integration test for workflow
tests/integration/workflows/test_new_workflow.py

# Performance benchmark
tests/performance/benchmarks/test_new_benchmark.py
```

### Step 3: Follow Naming Convention
```python
# File: test_{feature}.py
# Class: Test{FeatureName}
# Methods: test_{scenario}_{expected_behavior}

class TestRegimeAdaptation:
    def test_high_volatility_adapts_parameters(self):
        # Test implementation
        pass
    
    def test_low_volatility_adapts_parameters(self):
        # Test implementation
        pass
```

---

## 🎯 CI/CD Test Strategy

### Pull Request
```bash
# Fast validation (< 1 min)
pytest tests/unit/ tests/integration/ -v -x
```

### Pre-Merge
```bash
# Comprehensive validation (< 5 min)
pytest tests/unit/ tests/integration/ tests/functional/ -v
```

### Nightly Build
```bash
# Full suite including slow tests (< 30 min)
pytest tests/ -v --slow
```

### Release Candidate
```bash
# Complete validation including performance (< 1 hour)
pytest tests/ -v --all --benchmark
```

---

## 📚 Documentation

- **Test Plan:** `docs/TEST_ORGANIZATION_PLAN.md`
- **Compliance:** `docs/code-reviews/CORE_ENGINE_7_RULES_COMPLIANCE_AUDIT.md`
- **Regime Tests:** `docs/code-reviews/CORE_PIPELINE_IREGIME_AWARE_COMPLETE.md`

---

## 🏆 Test Quality Standards

### Coverage Targets
- **Unit Tests:** 85%+ coverage
- **Integration Tests:** 80%+ coverage
- **Critical Paths:** 95%+ coverage

### Performance Targets
- **Unit Tests:** < 0.1s per test
- **Integration Tests:** < 5s per test
- **Full Suite:** < 30 min

### Quality Metrics
- **Flakiness:** < 1%
- **False Positives:** 0%
- **Maintenance Time:** < 10% of dev time

---

**Status:** ✅ ORGANIZED & PRODUCTION READY  
**Last Updated:** October 21, 2025  
**Test Count:** 1000+ tests across 200+ files

