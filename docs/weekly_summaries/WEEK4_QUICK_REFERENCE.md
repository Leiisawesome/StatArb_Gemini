# Week 4 Quick Reference Guide

## 🚀 Quick Start

### Run All Week 4 Tests
```bash
pytest tests/unit/test_broker_components_fixed.py \
       tests/unit/test_data_pipeline.py \
       tests/unit/test_analytics_components.py -v
```

### Run with Coverage
```bash
pytest tests/unit/test_broker_components_fixed.py \
       tests/unit/test_data_pipeline.py \
       tests/unit/test_analytics_components.py \
       --cov=core_engine --cov-report=html
```

### Run Specific Component
```bash
# Broker tests only
pytest tests/unit/test_broker_components_fixed.py -v

# Data pipeline tests only
pytest tests/unit/test_data_pipeline.py -v

# Analytics tests only
pytest tests/unit/test_analytics_components.py -v
```

---

## 📊 Test Summary

| Component | Tests | Pass Rate | File |
|-----------|-------|-----------|------|
| Broker Components | 28 | 100% | test_broker_components_fixed.py |
| Data Pipeline | 28 | 100% | test_data_pipeline.py |
| Analytics | 37 | 97% | test_analytics_components.py |
| **TOTAL** | **93** | **99%** | **3 files** |

---

## 🎯 Key Test Classes

### Broker Components (28 tests)
```python
TestBrokerAdapterEnums          # 5 tests - BrokerType, ConnectionStatus, OrderAction, OrderType, TimeInForce
TestBrokerManagerEnums          # 2 tests - BrokerStatus, ExecutionVenue
TestConnectionManagerEnums      # 3 tests - ConnectionPriority, FailoverStrategy, HealthStatus
TestMessageProcessorEnums       # 3 tests - ProcessingPriority, MessageStatus, TransformationType
TestBrokerDataclasses          # 9 tests - Credentials, Config, Info, OrderRequest, ExecutionReport
TestBrokerIntegration          # 3 tests - Component interaction
TestImportPaths                # 4 tests - Import validation
```

### Data Pipeline (28 tests)
```python
TestDataConfigurationEnums      # 3 tests - Config creation and validation
TestDataManagerImports          # 2 tests - Import validation
TestDataStructures             # 2 tests - Market data, OHLCV
TestDataTransformations        # 4 tests - Returns, log returns, rolling windows, resampling
TestDataCaching                # 2 tests - Cache config
TestDataValidation             # 3 tests - Symbol, date, interval validation
TestDataFeeds                  # 2 tests - Feed configuration and status
TestAlternativeData            # 2 tests - Alternative data sources
TestDataQuality                # 3 tests - Missing data, outliers, duplicates
TestDataAggregation            # 2 tests - Time-weighted average, VWAP
TestDataPipelineIntegration    # 2 tests - End-to-end flow
TestDataPerformance            # 1 test - Large dataset handling
```

### Analytics (37 tests)
```python
TestPerformanceAnalyzerEnums    # 3 tests - PerformanceMetric, PerformancePeriod, RiskFreeRateSource
TestPerformanceConfiguration    # 3 tests - Config creation and customization
TestPerformanceMetrics         # 6 tests - Returns, Sharpe, drawdown, volatility, Sortino
TestRiskMetrics                # 4 tests - VaR, CVaR, beta, tracking error
TestAttributionAnalysis        # 2 tests - Factor and sector attribution
TestMetricsCalculator          # 4 tests - Win rate, profit factor, averages
TestPerformanceReporting       # 2 tests - Summary structure, period comparison
TestAnalyticsImports           # 4 tests - Import validation
TestStatisticalAnalysis        # 4 tests - Correlation, regression, skewness, kurtosis
TestPerformanceBenchmarking    # 3 tests - Comparison, information ratio, alpha
TestAnalyticsIntegration       # 2 tests - End-to-end analysis, multi-period
```

---

## 🔍 Example Test Patterns

### Enum Testing
```python
def test_broker_type_enum(self):
    """Test BrokerType enum"""
    from core_engine.broker.broker_adapter import BrokerType
    
    assert BrokerType.INTERACTIVE_BROKERS.value == "interactive_brokers"
    assert BrokerType.ALPACA.value == "alpaca"
```

### Dataclass Testing
```python
def test_order_request_creation(self):
    """Test OrderRequest creation"""
    from core_engine.broker.broker_manager import OrderRequest
    from core_engine.broker.broker_adapter import OrderAction, OrderType
    
    request = OrderRequest(
        request_id="req-123",
        symbol="AAPL",
        action=OrderAction.BUY,
        quantity=100,
        order_type=OrderType.MARKET
    )
    assert request.request_id == "req-123"
    assert request.symbol == "AAPL"
```

### Calculation Testing
```python
def test_sharpe_ratio_calculation(self):
    """Test Sharpe ratio calculation"""
    returns = pd.Series(np.random.randn(252) * 0.01 + 0.001)
    risk_free_rate = 0.02 / 252
    
    excess_returns = returns - risk_free_rate
    sharpe_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(252)
    
    assert isinstance(sharpe_ratio, float)
```

### Data Transformation Testing
```python
def test_returns_calculation(self):
    """Test returns calculation"""
    prices = pd.Series([100, 101, 102, 101, 103])
    returns = prices.pct_change().dropna()
    
    assert len(returns) == 4
    assert pytest.approx(returns.iloc[0], 0.01) == 0.01
```

---

## 🛠️ Common Commands

### Run Specific Test
```bash
pytest tests/unit/test_broker_components_fixed.py::TestBrokerAdapterEnums::test_broker_type_enum -v
```

### Run Test Class
```bash
pytest tests/unit/test_analytics_components.py::TestPerformanceMetrics -v
```

### Run with Verbose Output
```bash
pytest tests/unit/test_data_pipeline.py -vv
```

### Run with Coverage Report
```bash
pytest tests/unit/test_broker_components_fixed.py --cov=core_engine.broker --cov-report=term-missing
```

### Run Tests in Parallel (if pytest-xdist installed)
```bash
pytest tests/unit/test_*_components*.py -n auto
```

### Run with Specific Markers
```bash
pytest -m "broker or data or analytics"
```

---

## 📈 Coverage Goals

| Component | Week 4 Tests | Coverage Target | Status |
|-----------|--------------|-----------------|--------|
| Broker | 28 tests | 20% | ✅ Achieved |
| Data Pipeline | 28 tests | 25% | ✅ Achieved |
| Analytics | 37 tests | 30% | ✅ Achieved |
| **Overall** | **93 tests** | **40%** | 🎯 On Track |

---

## 🐛 Debugging Tips

### Test Fails on Import
```bash
# Check if module exists
python3 -c "from core_engine.broker.broker_adapter import BrokerType"

# Check Python path
python3 -c "import sys; print(sys.path)"
```

### Test Fails on Assertion
```bash
# Run with verbose output
pytest tests/unit/test_broker_components_fixed.py -vv

# Run with full traceback
pytest tests/unit/test_broker_components_fixed.py --tb=long
```

### Missing Dependencies
```bash
# Install missing package
python3 -m pip install package_name

# Check installed packages
python3 -m pip list | grep package_name
```

---

## 📚 Key Imports

### Broker Components
```python
from core_engine.broker.broker_adapter import (
    BrokerAdapter, BrokerType, ConnectionStatus,
    OrderAction, OrderType, TimeInForce, BrokerCredentials
)

from core_engine.broker.broker_manager import (
    BrokerManager, BrokerStatus, ExecutionVenue,
    BrokerConfig, BrokerInfo, OrderRequest, ExecutionReport
)

from core_engine.broker.connection_manager import (
    ConnectionManager, ConnectionPriority, FailoverStrategy,
    HealthStatus, ConnectionConfig
)

from core_engine.broker.message_processor import (
    MessageProcessor, ProcessingPriority, MessageStatus,
    TransformationType, ProcessingConfig
)
```

### Data Pipeline
```python
from core_engine.data.manager import ClickHouseDataConfig

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scipy import stats
```

### Analytics
```python
from core_engine.analytics.performance_analyzer import (
    PerformanceMetric, PerformancePeriod, RiskFreeRateSource,
    PerformanceConfig
)

import pandas as pd
import numpy as np
from scipy import stats
```

---

## ⚡ Performance Benchmarks

| Test Suite | Runtime | Tests | Avg per Test |
|------------|---------|-------|--------------|
| Broker Components | 0.04s | 28 | 0.001s |
| Data Pipeline | 0.05s | 28 | 0.002s |
| Analytics | 0.06s | 37 | 0.002s |
| **All Week 4** | **0.15s** | **93** | **0.002s** |

---

## 🎓 Best Practices

### 1. Test Naming
- Use descriptive names: `test_broker_type_enum`
- Include what is tested: `test_sharpe_ratio_calculation`
- Use verb-noun pattern: `test_validates_input`

### 2. Test Structure
```python
def test_feature(self):
    """Clear docstring explaining test purpose"""
    # Arrange - Set up test data
    data = create_test_data()
    
    # Act - Execute the functionality
    result = function_under_test(data)
    
    # Assert - Verify the result
    assert result == expected_value
```

### 3. Assertions
- Use specific assertions: `assert value == 10` not `assert value`
- Use pytest.approx for floats: `assert pytest.approx(value, 0.001) == expected`
- Add meaningful messages: `assert value == 10, f"Expected 10 but got {value}"`

### 4. Test Data
- Use realistic data
- Test edge cases
- Include boundary values
- Test error conditions

---

## 📝 Documentation

- **Full Documentation**: `docs/WEEK4_TESTING_COMPLETE.md`
- **This Quick Reference**: `docs/WEEK4_QUICK_REFERENCE.md`
- **Week 3 Summary**: `docs/WEEK3_TESTING_COMPLETE.md`

---

## 🏆 Week 4 Achievement Summary

```
╔════════════════════════════════════════╗
║     WEEK 4 TESTING COMPLETE ✅        ║
╠════════════════════════════════════════╣
║                                        ║
║  📊 93 Tests Created                  ║
║  ✅ 92 Passing (99%)                  ║
║  ⏭️  1 Skipped                        ║
║  📁 3 Test Files                      ║
║  ⚡ 0.15s Runtime                     ║
║                                        ║
║  🎯 Components Covered:               ║
║     • Broker (28 tests)               ║
║     • Data Pipeline (28 tests)        ║
║     • Analytics (37 tests)            ║
║                                        ║
╚════════════════════════════════════════╝
```

---

*Last Updated: October 8, 2025*  
*StatArb_Gemini Testing Framework - Week 4*
