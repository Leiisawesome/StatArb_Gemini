# Unified Configuration System for Scalable Backtesting

## 🎯 Overview

This document describes the **Unified Configuration System** that eliminates hardcoded parameters and provides a scalable, maintainable approach to backtest configuration management.

## ❌ Problems with Current Hardcoded Approach

### Before: Hardcoded Parameters
```python
# ❌ Scattered hardcoded parameters
config = PairsBacktestConfig(
    symbol_pairs=[("GLD", "GDX")],  # Hardcoded symbols
    start_date="2025-01-01",        # Hardcoded dates
    end_date="2025-01-31", 
    initial_capital=100000.0,       # Hardcoded capital
)

# ❌ Parameters buried in main() functions
symbols=['TSLA'],                   # Hardcoded in code
start_date="2024-12-20",           # Hardcoded in code
end_date="2024-12-20",             # Hardcoded in code
```

### Issues:
- **Scattered Configuration**: Parameters spread across multiple files
- **Poor Scalability**: Adding new strategies requires code changes
- **Testing Limitations**: Can't easily run comparative tests
- **Maintenance Overhead**: Parameter changes require editing multiple files
- **No Validation**: No error checking for invalid configurations
- **Environment Issues**: No support for dev/test/prod environments

## ✅ Solution: Unified Configuration System

### After: Configuration-Driven Approach
```python
# ✅ Clean, configuration-driven approach
config = load_config("pairs_trading.pairs_etf_conservative")

# ✅ Easy overrides without code changes
config = load_config("pairs_trading.pairs_etf_conservative", 
                    overrides={'period': 'jan_2025', 'interval': '1min'})

# ✅ Multiple configurations without hardcoding
backtest = RefactoredPairsTradingBacktest("pairs_trading.pairs_tech_aggressive")
```

## 🏗️ Architecture Components

### 1. Configuration Files

#### `unified_backtest_config.yaml`
- **Central configuration** for all strategies and parameters
- **Hierarchical structure** with universes, periods, strategies
- **Environment overrides** for dev/test/prod
- **Test scenarios** for comprehensive testing

#### `unified_config_manager.py`
- **Configuration loading and validation**
- **Parameter inheritance and overrides**
- **Environment-specific configurations**
- **Error handling and validation**

#### `BacktestConfigFactory`
- **Configuration-driven backtest creation**
- **Strategy comparison utilities**
- **Multi-timeframe analysis support**
- **Test scenario management**

### 2. Configuration Schema

```yaml
# Global defaults
global:
  default_capital: 100000.0
  default_interval: "5min"
  default_risk_limit: 0.02

# Trading universes
universes:
  single_assets:
    tech_stocks: ["AAPL", "MSFT", "GOOGL", "NVDA"]
    high_momentum: ["TSLA", "NVDA", "AMD"]
  pairs:
    etf_pairs: [["GLD", "GDX"], ["SPY", "QQQ"]]
    tech_pairs: [["AAPL", "MSFT"], ["GOOGL", "AMZN"]]

# Trading periods
periods:
  jan_2025:
    start_date: "2025-01-01"
    end_date: "2025-01-31"
  quick_test:
    start_date: "2024-12-20"
    end_date: "2024-12-20"

# Strategy configurations
strategies:
  momentum:
    momentum_single_tsla:
      type: "momentum"
      universe: "single_assets.high_momentum"
      symbols: ["TSLA"]
      period: "jan_2025"
      parameters:
        lookback_period: 20
        momentum_threshold: 0.015
  
  pairs_trading:
    pairs_etf_conservative:
      type: "pairs_trading"
      universe: "pairs.etf_pairs"
      symbol_pairs: [["GLD", "GDX"]]
      parameters:
        entry_zscore_long: -1.0
        entry_zscore_short: 1.0
```

## 🚀 Usage Examples

### 1. Single Strategy Execution

```python
from config.unified_config_manager import load_config

# Load default configuration
config = load_config("momentum.momentum_single_tsla")

# Load with overrides
config = load_config("pairs_trading.pairs_etf_conservative", 
                    overrides={
                        'period': 'three_months',
                        'interval': '1min',
                        'parameters': {'entry_zscore_long': -0.8}
                    })
```

### 2. Test Scenario Execution

```python
from config.unified_config_manager import load_scenario

# Load predefined test scenario
configs = load_scenario("strategy_comparison")

# Run all strategies in scenario
for config in configs:
    backtest = create_backtest(config)
    await backtest.run()
```

### 3. Strategy Comparison

```python
from config.unified_config_manager import BacktestConfigFactory

factory = BacktestConfigFactory(Environment.DEVELOPMENT)

# Compare multiple strategies
strategies = [
    "momentum.momentum_single_tsla",
    "mean_reversion.mean_reversion_aggressive", 
    "pairs_trading.pairs_etf_conservative"
]

configs = factory.create_comparison_configs(strategies, {
    'period': 'jan_2025',
    'capital': 100000.0
})
```

### 4. Multi-Timeframe Analysis

```python
# Test same strategy across timeframes
intervals = ["1min", "5min", "15min"]
configs = factory.create_multi_timeframe_configs(
    "mean_reversion.mean_reversion_conservative",
    intervals
)
```

## 🔧 Refactoring Existing Backtests

### Step 1: Replace Hardcoded Configuration

**Before:**
```python
class AdvancedPairsTradingBacktest:
    def __init__(self):
        # ❌ Hardcoded parameters
        self.symbol_pairs = [("GLD", "GDX")]
        self.start_date = "2025-01-01"
        self.end_date = "2025-01-31"
        self.initial_capital = 100000.0
```

**After:**
```python
class RefactoredPairsTradingBacktest:
    def __init__(self, config_path: str, overrides: Dict = None):
        # ✅ Configuration-driven
        self.config = load_config(config_path, overrides=overrides)
        self.symbol_pairs = self.config.symbol_pairs
        self.start_date = self.config.period.start_date
        self.end_date = self.config.period.end_date
        self.initial_capital = self.config.initial_capital
```

### Step 2: Update Main Functions

**Before:**
```python
async def main():
    # ❌ Hardcoded in main function
    config = PairsBacktestConfig(
        symbol_pairs=[("GLD", "GDX")],
        start_date="2025-01-01",
        end_date="2025-01-31"
    )
```

**After:**
```python
async def main():
    # ✅ Configuration-driven
    backtest = RefactoredPairsTradingBacktest(
        "pairs_trading.pairs_etf_conservative"
    )
    
    # ✅ Or with overrides
    backtest = RefactoredPairsTradingBacktest(
        "pairs_trading.pairs_etf_conservative",
        overrides={'period': 'jan_2025'}
    )
```

## 🌍 Environment Support

### Development Environment
```yaml
environments:
  development:
    global:
      default_capital: 10000.0  # Smaller capital for dev
    periods:
      default_period: "quick_test"
```

### Production Environment
```yaml
environments:
  production:
    global:
      default_capital: 1000000.0  # Full capital for prod
    periods:
      default_period: "three_months"
```

## ✅ Benefits

### 1. **Scalability**
- Add new strategies without code changes
- Easy parameter experimentation
- Support for unlimited configurations

### 2. **Maintainability**
- Centralized configuration management
- No scattered hardcoded parameters
- Version-controlled configuration files

### 3. **Flexibility**
- Easy parameter overrides
- Environment-specific configurations
- Test scenario management

### 4. **Reliability**
- Configuration validation
- Error handling and logging
- Consistent parameter application

### 5. **Testing**
- Comparative strategy analysis
- Multi-timeframe testing
- Scenario-based validation

## 📊 Migration Checklist

### For Each Existing Backtest:

- [ ] **Identify Hardcoded Parameters**
  - Symbols, dates, capital amounts
  - Strategy-specific parameters
  - Risk management settings

- [ ] **Create Configuration Entry**
  - Add strategy to `unified_backtest_config.yaml`
  - Define universe and period
  - Set strategy parameters

- [ ] **Refactor Backtest Class**
  - Replace hardcoded values with config loading
  - Update `__init__` to accept config path
  - Add parameter validation

- [ ] **Update Main Function**
  - Remove hardcoded configuration
  - Use configuration loading
  - Add override examples

- [ ] **Test Configuration**
  - Verify default configuration works
  - Test parameter overrides
  - Validate error handling

## 🎯 Next Steps

1. **Complete Migration**: Refactor remaining backtests to use configuration system
2. **Add Validation**: Implement comprehensive parameter validation
3. **Extend Universes**: Add more trading universes and pairs
4. **Environment Testing**: Test dev/test/prod environment configurations
5. **Documentation**: Create configuration guides for new strategies

## 📝 Configuration Best Practices

### 1. **Naming Conventions**
- Use descriptive strategy names: `momentum_single_tsla`
- Group by strategy type: `momentum.*`, `pairs_trading.*`
- Use clear period names: `jan_2025`, `three_months`

### 2. **Parameter Organization**
- Group related parameters together
- Use consistent parameter names across strategies
- Provide sensible defaults

### 3. **Validation**
- Validate required parameters
- Check parameter ranges and types
- Provide clear error messages

### 4. **Documentation**
- Document each configuration section
- Explain parameter meanings and ranges
- Provide usage examples

This unified configuration system transforms the backtesting framework from a hardcoded, inflexible system into a scalable, maintainable, and professional-grade trading research platform. 🚀
