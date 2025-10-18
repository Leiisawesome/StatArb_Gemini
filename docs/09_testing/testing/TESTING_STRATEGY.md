# Testing Strategy - StatArb Gemini

## Quick Reference

```bash
# Fast development testing (no verbose, no coverage)
pytest -o addopts="" tests/unit/

# Single test file
pytest -o addopts="" tests/unit/test_analytics_components.py

# Single test class
pytest -o addopts="" tests/unit/test_file.py::TestClassName

# Single test method
pytest -o addopts="" tests/unit/test_file.py::TestClassName::test_method_name

# Stop on first failure
pytest -o addopts="" -x tests/unit/

# Run with maxfail (stop after N failures)
pytest -o addopts="" --maxfail=10 tests/unit/
```

## Understanding Test Execution Times

### Test Collection: ~5-6 seconds (1690 tests)
- **Normal behavior** - pytest scans all test files
- Not a hang, just takes time with large test suites

### Individual Test Speed:
- **Unit tests**: 0.01-0.05s per test
- **Integration tests**: 0.1-0.5s per test (with setup/teardown)
- **E2E tests**: 0.5-2s per test (full system initialization)

### Full Suite Execution:
- **Unit tests only** (~1596 tests): 1-2 minutes
- **Integration tests only** (~94 tests): 2-5 minutes  
- **Full suite** (1690 tests): 5-10 minutes

## Targeted Test Subsets

### 1. Unit Tests (Fast - Use for Development)

```bash
# All unit tests (1596 tests, ~1-2 min)
pytest -o addopts="" tests/unit/

# Analytics components only
pytest -o addopts="" tests/unit/test_analytics_*

# Risk components only
pytest -o addopts="" tests/unit/test_risk_*

# Trading components only
pytest -o addopts="" tests/unit/test_trading_*

# Data components only
pytest -o addopts="" tests/unit/test_data_*

# System components only
pytest -o addopts="" tests/unit/test_system_*
```

### 2. Integration Tests (Medium Speed)

```bash
# All integration tests (~94 tests, ~2-5 min)
pytest -o addopts="" tests/integration/

# E2E trading workflow
pytest -o addopts="" tests/integration/test_e2e_trading.py

# Enhanced system integration
pytest -o addopts="" tests/integration/test_enhanced_system_integration.py
```

### 3. Component-Specific Testing

```bash
# Analytics Manager
pytest -o addopts="" tests/unit/test_analytics_manager_comprehensive.py

# Risk Manager  
pytest -o addopts="" tests/unit/test_central_risk_manager.py

# Strategy Engine
pytest -o addopts="" tests/unit/test_strategy_*.py

# Order Management
pytest -o addopts="" tests/unit/test_order_*.py
```

### 4. Quick Smoke Test (Fastest - ~30 seconds)

```bash
# Run integration tests only (validates core workflows)
pytest -o addopts="" -x tests/integration/
```

## Test Execution Patterns

### Pattern 1: TDD Development Cycle
```bash
# 1. Run tests for component you're changing
pytest -o addopts="" tests/unit/test_your_component.py -x

# 2. Fix issues, repeat until passing

# 3. Run related integration tests
pytest -o addopts="" tests/integration/test_related.py

# 4. Before commit: run full unit suite
pytest -o addopts="" tests/unit/ --maxfail=10
```

### Pattern 2: Bug Investigation
```bash
# 1. Run failing test in isolation with verbose
pytest -o addopts="" -vv tests/path/to/test.py::TestClass::test_method

# 2. Add --tb=long for full traceback
pytest -o addopts="" --tb=long tests/path/to/test.py::TestClass::test_method

# 3. Run with pdb debugger
pytest -o addopts="" --pdb tests/path/to/test.py::TestClass::test_method
```

### Pattern 3: Pre-Commit Validation
```bash
# 1. Run unit tests for modified components
pytest -o addopts="" tests/unit/ --maxfail=5

# 2. If passing, run integration tests
pytest -o addopts="" tests/integration/ --maxfail=3

# 3. Optional: run with coverage for final check
pytest --cov=core_engine tests/unit/ --cov-report=term-missing
```

### Pattern 4: CI/CD Pipeline
```bash
# 1. Fast feedback (unit tests only)
pytest tests/unit/ -x --maxfail=10

# 2. Integration validation
pytest tests/integration/ --maxfail=5

# 3. Full suite with coverage (nightly builds)
pytest tests/ --cov=core_engine --cov-report=html --cov-fail-under=80
```

## Why `-o addopts=""` Works

**Problem**: Default `pytest.ini` has verbose options:
```ini
addopts = 
    --verbose
    --tb=short
    --strict-markers
    --disable-warnings
    --color=yes
    --durations=10
    --maxfail=5
```

**Solution**: `-o addopts=""` overrides these for faster execution:
- No verbose output (faster rendering)
- No durations calculation
- No maxfail limit (run all tests or use custom --maxfail)

**Result**: 10-20x faster for large test suites

## Test Categories by Speed

### Ultra-Fast (<5 min)
```bash
pytest -o addopts="" tests/unit/test_analytics_components.py
pytest -o addopts="" tests/unit/test_risk_components.py
pytest -o addopts="" tests/unit/test_type_definitions.py
```

### Fast (5-15 min)
```bash
pytest -o addopts="" tests/unit/
pytest -o addopts="" tests/integration/test_e2e_trading.py
```

### Medium (15-30 min)
```bash
pytest -o addopts="" tests/
pytest tests/unit/ --cov=core_engine
```

### Slow (30+ min)
```bash
pytest tests/ --cov=core_engine --cov-report=html
pytest tests/ --cov=core_engine --cov-fail-under=80
```

## Coverage Analysis (Use Sparingly)

```bash
# Coverage for single file (fast)
pytest --cov=core_engine.analytics.manager_enhanced tests/unit/test_analytics_manager_comprehensive.py

# Coverage for module (medium)
pytest --cov=core_engine.analytics tests/unit/test_analytics_*

# Full coverage (slow - save for CI/CD)
pytest --cov=core_engine tests/ --cov-report=html
```

## Common Issues & Solutions

### Issue: "Tests seem to hang"
**Reality**: Integration tests with setup/teardown take time (10+ seconds each)
**Solution**: Use unit tests for development, integration tests for validation

### Issue: "Full suite takes forever"
**Reality**: 1690 tests × 0.5s avg = 14 minutes minimum
**Solution**: Run targeted subsets during development

### Issue: "Can't find my test"
**Solution**: Use pytest's collection dry-run
```bash
pytest --collect-only tests/ | grep "test_my_feature"
```

### Issue: "Need to see detailed output"
**Solution**: Remove `-o addopts=""` for specific test
```bash
pytest tests/path/to/test.py::test_method -vv
```

## Phase 4 Testing Checklist

### Week 5.1: Test Fixes
- [ ] Run unit tests: `pytest -o addopts="" tests/unit/ --maxfail=50`
- [ ] Identify all failures (expect ~27 in analytics)
- [ ] Fix or remove broken tests
- [ ] Verify: `pytest -o addopts="" tests/unit/`

### Week 5.2: Integration Validation  
- [ ] Run integration tests: `pytest -o addopts="" tests/integration/`
- [ ] All E2E workflows pass
- [ ] System integration tests pass

### Week 5.3: Full Suite
- [ ] Run full suite: `pytest -o addopts="" tests/ --maxfail=20`
- [ ] Achieve 95%+ pass rate
- [ ] Document remaining failures

## Best Practices

### DO:
✅ Run unit tests frequently during development
✅ Use `-o addopts=""` for speed
✅ Run targeted subsets (component-specific)
✅ Use `-x` or `--maxfail` to stop early on failures
✅ Run integration tests before committing
✅ Save full suite + coverage for CI/CD

### DON'T:
❌ Run full suite during active development
❌ Use coverage analysis during TDD cycles  
❌ Run tests without `-o addopts=""` unless needed
❌ Wait for full suite when debugging
❌ Ignore test failures ("I'll fix it later")

## Example Workflows

### Scenario: Fixing Analytics Bug
```bash
# 1. Run just analytics tests
pytest -o addopts="" tests/unit/test_analytics_* -x
# Found failure in test_analytics_manager_comprehensive.py

# 2. Run that file only
pytest -o addopts="" tests/unit/test_analytics_manager_comprehensive.py -x
# Fixed 1 test, now 26 failures remain

# 3. Run specific failing test
pytest -o addopts="" -vv tests/unit/test_analytics_manager_comprehensive.py::TestAnalyticsManagerEnhanced::test_get_regime_aware_metrics
# See detailed error, fix code

# 4. Rerun all analytics tests
pytest -o addopts="" tests/unit/test_analytics_* 
# All passing!

# 5. Run related integration test
pytest -o addopts="" tests/integration/test_enhanced_system_integration.py
# Verify no regression
```

### Scenario: Before Committing Code
```bash
# 1. Quick unit test check
pytest -o addopts="" tests/unit/ --maxfail=5
# 5 failures - need to fix

# 2. After fixes, full unit suite
pytest -o addopts="" tests/unit/
# All passing

# 3. Integration smoke test
pytest -o addopts="" tests/integration/ -x
# All passing

# 4. Commit with confidence!
git commit -m "feat: improved analytics performance"
```

## Performance Tips

1. **Use PyCharm/VSCode test runners** - They cache results and run faster
2. **Run tests in parallel** (with pytest-xdist):
   ```bash
   pytest -o addopts="" -n auto tests/unit/
   ```
3. **Skip slow tests during development**:
   ```bash
   pytest -o addopts="" -m "not slow" tests/unit/
   ```
4. **Use test markers** to categorize:
   ```bash
   pytest -o addopts="" -m "analytics" tests/
   ```

## Summary

- **Development**: Use `-o addopts="" tests/unit/` (1-2 min)
- **Pre-commit**: Add `tests/integration/` (3-7 min total)
- **CI/CD**: Full suite with coverage (10-30 min)
- **Never**: Run full suite during active TDD cycles

**Remember**: Fast feedback loops = productive development! 🚀

---

**Last Updated**: October 9, 2025
**Phase 4**: Production Readiness Testing
