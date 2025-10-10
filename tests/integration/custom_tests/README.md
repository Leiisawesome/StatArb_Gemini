# Custom Integration Tests

**Location:** `tests/integration/custom_tests/`  
**Status:** Non-pytest framework  
**Date Moved:** October 10, 2025

## Overview

This directory contains 17 comprehensive integration test files (14,000+ lines total) that use a custom test framework instead of pytest.

## Test Files

### Analytics & Monitoring (3 files)
1. **test_analytics_integration.py** (1,359 lines)
   - Real-time analytics processing
   - Performance monitoring
   - Cross-component analytics communication

2. **test_performance_monitoring_integration.py** (879 lines)
   - Performance metrics collection
   - Monitoring systems integration

3. **test_regime_transition_integration.py** (909 lines)
   - Market regime detection
   - Transition handling

### Broker & Trading (3 files)
4. **test_broker_integration.py** (854 lines)
   - Multi-broker connectivity
   - Order routing and execution

5. **test_venue_routing_integration.py** (852 lines)
   - Venue selection logic
   - Order routing strategies

6. **test_authorization_flow_integration.py** (1,183 lines)
   - Authorization workflows
   - Permission management

### Data Management (3 files)
7. **test_data_caching_integration.py** (844 lines)
   - Data caching strategies
   - Cache invalidation

8. **test_data_flow_integration.py** (751 lines)
   - Data pipeline integration
   - Real-time data flow

9. **test_configuration_management_integration.py** (950 lines)
   - Configuration loading
   - Dynamic configuration updates

### System Integration (4 files)
10. **test_comprehensive_system_integration.py** (986 lines)
    - End-to-end system integration
    - Multi-component coordination

11. **test_orchestrator_integration.py** (988 lines)
    - System orchestration
    - Component coordination

12. **test_dependency_injection_integration.py** (607 lines)
    - Dependency injection patterns
    - Component lifecycle

13. **test_event_driven_integration.py** (524 lines)
    - Event-driven architecture
    - Event propagation

### Risk & Testing (3 files)
14. **test_enhanced_risk_integration.py** (898 lines)
    - Risk management integration
    - Real-time risk monitoring

15. **test_stress_testing_integration.py** (514 lines)
    - System stress testing
    - Performance under load

16. **test_callback_integration.py** (799 lines)
    - Callback mechanisms
    - Async callback handling

### Utilities (1 file)
17. **test_helpers.py** (597 lines)
    - Test helper functions
    - Assertion utilities
    - Mock data builders

## Test Framework

These tests use a custom framework with classes like:
- `AnalyticsIntegrationTester`
- `BrokerIntegrationTester`
- `DataFlowIntegrationTester`
- etc.

## Why Not Pytest?

These tests were written with a custom test runner framework that:
1. Uses custom result collectors
2. Has its own assertion methods
3. Runs tests through main() functions
4. Reports results in custom format

## Running These Tests

**Current Status:** Cannot be run with pytest

**Options:**
1. **Keep as-is:** Maintain custom framework
2. **Convert to pytest:** Refactor to use pytest decorators and assertions
3. **Create custom runner:** Build a runner script for the custom framework

## Conversion to Pytest (Future)

To convert these tests to pytest:

```python
# Before (Custom Framework)
class AnalyticsIntegrationTester:
    def test_real_time_analytics(self):
        result = self.run_test(...)
        return AnalyticsIntegrationTestResult(...)

# After (Pytest)
import pytest

@pytest.mark.asyncio
async def test_real_time_analytics():
    # Test code
    assert result.success
```

## Value Assessment

**High Value Tests:**
- Comprehensive coverage (14,000+ lines)
- Test complex integration scenarios
- Well-documented test cases
- Cover critical system interactions

**Conversion Effort:**
- Estimated: 2-3 weeks for full conversion
- Can be done incrementally
- May require restructuring

## Recommendation

**Short-term:** Keep in custom_tests/ directory, document as-is  
**Medium-term:** Consider conversion if integration test coverage gaps identified  
**Long-term:** Standardize all tests on pytest framework

## Notes

- These tests complement the 4 pytest-based integration tests
- pytest integration tests: test_e2e_trading.py, test_failure_scenarios.py, test_simple_trading_workflow.py, test_system_stress.py
- Custom tests provide additional comprehensive coverage
- Not currently blocking production deployment

---

**Archived:** October 10, 2025  
**Phase 4 Week 5.1 Cleanup**
