# Testing Framework Configuration System

## Overview

The testing framework now includes a comprehensive configuration system that makes it easy to adjust trading periods, universes, strategy parameters, and risk settings without modifying code.

## Quick Start

### 1. Default Test (Single Day TSLA)
```bash
cd /Users/lei/Documents/GitHub/StatArb_Gemini/StatArb_Gemini
PYTHONPATH=$PWD ./ai_integration_env/bin/python testing_framework/advanced_momentum_backtest.py
```

### 2. View Available Configurations
```bash
PYTHONPATH=$PWD ./ai_integration_env/bin/python testing_framework/run_backtest_examples.py --list-configs
```

### 3. Run Examples
```bash
# Quick test
PYTHONPATH=$PWD ./ai_integration_env/bin/python testing_framework/run_backtest_examples.py --quick

# Custom symbols
PYTHONPATH=$PWD ./ai_integration_env/bin/python testing_framework/run_backtest_examples.py --custom AAPL MSFT

# Predefined scenario
PYTHONPATH=$PWD ./ai_integration_env/bin/python testing_framework/run_backtest_examples.py --scenario quick_test
```

## Configuration Files

### Main Configuration: `testing_framework/config/test_config.yaml`

Contains all trading settings:

- **Trading Periods**: single_day, one_week, one_month, three_months, full_year
- **Universe**: Symbol lists and categories (high_momentum, large_cap, etfs, etc.)
- **Strategies**: advanced_momentum, mean_reversion, multi_momentum
- **Risk Management**: Position sizing, stop losses, drawdown limits
- **Data Settings**: Intervals, validation rules

### Quick Overrides: `testing_framework/config/quick_overrides.yaml`

Simple overrides for testing:
- quick_aapl_test: Test AAPL instead of TSLA
- multi_symbol_test: Test multiple symbols
- conservative_test: Lower risk parameters
- tech_test: Test tech stocks (AAPL, MSFT, GOOGL, NVDA)

## Configuration Structure

### Trading Periods
```yaml
trading_periods:
  single_day:
    start_date: "2024-12-20"
    end_date: "2024-12-20"
    start_time: "09:30:00"
    end_time: "16:00:00"
    timezone: "US/Eastern"
```

### Strategy Configuration
```yaml
strategies:
  advanced_momentum:
    template: "professional_momentum_v1"
    symbols: ["TSLA"]
    period: "single_day"
    interval: "1min"
    capital: 100000.0
    parameters:
      lookback_period: 20
      momentum_threshold: 0.015  # 1.5%
      max_position_size: 0.15    # 15%
```

### Universe Management
```yaml
universe:
  symbols: ["TSLA", "AAPL", "MSFT", "GOOGL", "NVDA", "SPY"]
  categories:
    high_momentum: ["TSLA", "NVDA", "AMD"]
    large_cap: ["AAPL", "MSFT", "GOOGL"]
    etfs: ["SPY", "QQQ", "IWM"]
```

## Parameter Validation

The system validates all parameters according to template bounds:

- **momentum_threshold**: 0.001 to 0.1 (0.1% to 10%)
- **lookback_period**: 5 to 100 periods
- **max_position_size**: Up to 100% (0.0 to 1.0)
- **confidence_threshold**: 0.5 to 0.95 (50% to 95%)

## Examples

### Run Different Symbols
```python
# In Python code
from testing_framework.advanced_momentum_backtest import main
import asyncio

# Custom configuration
custom_config = {
    'strategy': {
        'symbols': ['AAPL', 'MSFT']
    },
    'trading_period': {
        'period': 'one_week'
    }
}

asyncio.run(main("advanced_momentum", custom_config))
```

### Run Predefined Scenarios
```python
from testing_framework.run_backtest_examples import run_scenario_test

# Available scenarios: quick_test, momentum_comprehensive, strategy_comparison, regime_test
run_scenario_test('momentum_comprehensive')
```

### Modify Risk Parameters
```yaml
# Add to test_config.yaml or use as custom_config
strategy:
  parameters:
    max_position_size: 0.05      # Conservative 5% max position
    momentum_threshold: 0.025    # Higher 2.5% threshold
risk_management:
  global:
    max_portfolio_risk: 0.01     # 1% max portfolio risk
```

## Available Configurations

### Trading Periods
- **single_day**: 2024-12-20 (Quick validation)
- **one_week**: 2024-12-16 to 2024-12-20
- **one_month**: 2024-11-20 to 2024-12-20
- **three_months**: 2024-09-20 to 2024-12-20
- **full_year**: 2024-01-01 to 2024-12-31

### Strategies
- **advanced_momentum**: Professional momentum with risk management
- **mean_reversion**: Mean reversion strategy
- **multi_momentum**: Multi-symbol momentum testing

### Data Intervals
- **1min**: High-frequency testing
- **5min**: Medium-frequency
- **15min**: Lower-frequency
- **1h**: Hourly bars
- **1d**: Daily bars

## Output

Each test produces comprehensive results including:

- **Trading Performance**: Returns, Sharpe ratio, win rate, profit factor
- **Risk Metrics**: Max drawdown, current drawdown, risk-adjusted returns
- **Execution Details**: Trade log, timing, regime detection
- **System Validation**: All components status and health checks

## Tips

1. **Start Small**: Use `single_day` period for initial testing
2. **Validate Parameters**: System will reject invalid parameter values
3. **Monitor Performance**: Check execution time and memory usage
4. **Use Categories**: Leverage universe categories for systematic testing
5. **Custom Overrides**: Use custom_config for one-off parameter changes

## File Structure

```
testing_framework/
├── config/
│   ├── test_config.yaml           # Main configuration
│   ├── quick_overrides.yaml       # Simple overrides
│   └── config_manager.py          # Configuration loader
├── advanced_momentum_backtest.py  # Main backtest
├── run_backtest_examples.py       # Examples and CLI
└── docs/
    └── README.md                   # This file
```

The configuration system provides maximum flexibility while maintaining professional-grade parameter validation and comprehensive testing capabilities.
