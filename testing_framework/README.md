# StatArb Gemini Testing Framework

Comprehensive testing infrastructure for the statistical arbitrage trading system.

## Overview

This testing framework provides a unified approach to testing all aspects of the StatArb Gemini system, including:

- **Multi-Strategy Backtesting**: Real ClickHouse data with time-series processing
- **End-to-End Validation**: Complete system integration testing
- **Performance Analytics**: Portfolio metrics and performance validation
- **Data Integration**: Real market data flow validation

## Test Structure

```
testing_framework/
├── __init__.py                              # Framework initialization
├── README.md                               # This documentation
├── run_all_tests.py                        # Main test runner
├── multi_strategy_backtest_real_data.py    # Multi-strategy backtesting
└── comprehensive_end_to_end_test_suite.py  # End-to-end validation
```

## Usage

### From Project Root

```bash
# Run all tests
python run_tests.py

# Run specific test
python run_tests.py --test=multi_strategy_backtest_real_data

# Run tests by category
python run_tests.py --category=multi_strategy

# List available tests
python run_tests.py --list
```

### Direct Framework Access

```bash
# Run from testing framework directory
cd testing_framework/
python run_all_tests.py

# Or run individual tests
python multi_strategy_backtest_real_data.py
```

## Available Tests

### Multi-Strategy Category

- **`multi_strategy_backtest_real_data`**: Complete multi-strategy backtesting with real ClickHouse data
  - Tests TSLA and NVDA momentum and mean reversion strategies
  - Uses real January 2025 market data (36,000+ data points)
  - Validates time-series signal generation and trade execution
  - Calculates real performance metrics and P&L

### End-to-End Category

- **`comprehensive_end_to_end_test_suite`**: Comprehensive system validation
  - Tests all core system components
  - Validates data flow and integration
  - Checks configuration and setup

## Test Results

Test results are automatically saved to:
- **Logs**: `test_run_YYYYMMDD_HHMMSS.log`
- **Reports**: `test_report_YYYYMMDD_HHMMSS.txt`

## Adding New Tests

To add a new test to the framework:

1. Create your test file in `testing_framework/`
2. Update `AVAILABLE_TESTS` in `__init__.py`
3. Ensure your test returns proper exit codes (0 = success, non-zero = failure)

Example:
```python
# In __init__.py
AVAILABLE_TESTS = {
    "your_new_test": {
        "description": "Description of your test",
        "category": "your_category",
        "file": "your_test_file.py"
    }
}
```

## Test Categories

- **`multi_strategy`**: Multi-strategy backtesting and validation
- **`end_to_end`**: Complete system integration testing
- **`performance`**: Performance metrics and analytics validation
- **`integration`**: Data flow and component integration testing

## Requirements

- Python 3.8+
- ClickHouse database with market data
- All project dependencies installed
- Proper environment configuration

## Architecture

The testing framework follows these principles:

1. **Unified Entry Point**: Single command to run all tests
2. **Categorized Tests**: Tests organized by functionality
3. **Comprehensive Reporting**: Detailed logs and reports
4. **Real Data Testing**: Uses actual market data for validation
5. **Modular Design**: Easy to add new tests and categories

## Performance Expectations

- **Multi-Strategy Backtest**: ~2-3 minutes (processes 36,000+ data points)
- **End-to-End Suite**: ~1-2 minutes (comprehensive validation)
- **Total Test Suite**: ~5-10 minutes for complete validation

## Troubleshooting

Common issues and solutions:

1. **ClickHouse Connection**: Ensure ClickHouse is running and accessible
2. **Data Missing**: Verify market data is loaded in ClickHouse
3. **Memory Issues**: Large datasets may require sufficient RAM
4. **Timeout**: Tests have 30-minute timeout for complex operations

## Contributing

When adding tests:
- Follow existing naming conventions
- Include comprehensive docstrings
- Add proper error handling
- Update this README with new test information
- Ensure tests are deterministic and repeatable
