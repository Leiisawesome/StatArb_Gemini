# Institutional Backtest System - User Guide

**Version**: 1.0.0  
**Date**: October 17, 2025  
**Status**: Production-Ready ✅

---

## 📖 Table of Contents

1. [Introduction](#introduction)
2. [Quick Start](#quick-start)
3. [Installation](#installation)
4. [Basic Usage](#basic-usage)
5. [Configuration](#configuration)
6. [Running Backtests](#running-backtests)
7. [Understanding Results](#understanding-results)
8. [Advanced Features](#advanced-features)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)
11. [API Reference](#api-reference)

---

## Introduction

The Institutional Backtest System is a production-grade framework for validating trading strategies using historical data with institutional-quality execution simulation.

### Key Features

- **🏗️ Institutional Architecture**: 12 integrated components following strict governance patterns
- **🌐 Regime-Aware Trading**: Automatic market regime detection and adaptation (Rule 13)
- **💰 Realistic Execution**: Transaction costs, slippage, market impact modeling (Rule 12)
- **⚠️ Risk Management**: Centralized risk authorization and position management (Rule 4)
- **📊 Multi-Strategy Support**: Coordinate multiple strategies with signal aggregation
- **🎯 Performance Attribution**: Strategy-level and regime-level performance breakdowns
- **⚡ High Performance**: 2,000+ bars/sec processing speed
- **🔒 Production-Ready**: Zero memory leaks, comprehensive error handling

### System Requirements

- **Python**: 3.9+
- **Operating System**: macOS, Linux, Windows
- **Memory**: 4GB minimum, 8GB recommended
- **Storage**: 10GB for ClickHouse data
- **Database**: ClickHouse (for historical data)

---

## Quick Start

### 30-Second Start

```bash
# 1. Activate environment
source ai_integration_env/bin/activate

# 2. Run example
python backtest/examples/simple_momentum_backtest.py

# 3. View results
cat backtest_results/simple_momentum_example_results.json
```

### 2-Minute Start

```bash
# 1. Activate environment
source ai_integration_env/bin/activate

# 2. Generate configuration
python -m backtest.cli.main config --template momentum --output my_backtest.json

# 3. Run backtest
python -m backtest.cli.main run --config my_backtest.json

# 4. View results
ls -lh backtest_results/
```

### 5-Minute Start (Interactive)

```bash
# 1. Activate environment
source ai_integration_env/bin/activate

# 2. Launch interactive mode
python -m backtest.cli.main interactive

# Follow the prompts to configure and run your backtest
```

---

## Installation

### Prerequisites

1. **ClickHouse Database**:
   ```bash
   # macOS
   brew install clickhouse
   
   # Start ClickHouse
   clickhouse server
   ```

2. **Python Environment**:
   ```bash
   # Create virtual environment (if not exists)
   python3 -m venv ai_integration_env
   
   # Activate environment
   source ai_integration_env/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

### Verification

```bash
# Verify installation
python -c "from backtest.engine.institutional_backtest_engine import InstitutionalBacktestEngine; print('✅ Installation successful')"
```

---

## Basic Usage

### Three Ways to Run Backtests

#### 1. Using Examples (Easiest)

```bash
# Simple momentum strategy
python backtest/examples/simple_momentum_backtest.py

# Multi-strategy portfolio
python backtest/examples/multi_strategy_backtest.py

# Advanced regime-aware
python backtest/examples/advanced_regime_aware_backtest.py
```

#### 2. Using CLI (Recommended)

```bash
# With configuration file
python -m backtest.cli.main run --config my_config.json

# With command-line arguments
python -m backtest.cli.main run \
  --symbols NVDA,TSLA \
  --start-date 2024-01-01 \
  --end-date 2024-03-31 \
  --strategies momentum \
  --initial-capital 100000

# Interactive mode
python -m backtest.cli.main interactive
```

#### 3. Using Python API (Advanced)

```python
import asyncio
from backtest.engine.institutional_backtest_engine import InstitutionalBacktestEngine
from backtest.config.backtest_config import BacktestConfiguration, DataConfig, ...

# Create configuration
config = BacktestConfiguration(...)

# Create engine
engine = InstitutionalBacktestEngine(config=config)

# Run backtest
results = asyncio.run(engine.run_backtest())
```

---

## Configuration

### Configuration Structure

A backtest configuration consists of 6 main sections:

```python
BacktestConfiguration(
    backtest_name="my_backtest",        # Unique identifier
    backtest_mode="historical",          # Mode (always "historical")
    data=DataConfig(...),                # Data configuration
    strategies=[...],                     # Strategy configuration(s)
    risk=RiskConfig(...),                # Risk parameters
    execution=ExecutionConfig(...),      # Execution settings
    analytics=AnalyticsConfig(...)       # Analytics settings
)
```

### 1. Data Configuration

Defines what data to load:

```python
DataConfig(
    symbols=['NVDA', 'TSLA', 'AAPL'],  # Trading symbols
    start_date='2024-01-01',            # Start date (YYYY-MM-DD)
    end_date='2024-03-31',              # End date (YYYY-MM-DD)
    interval='1min'                      # Bar interval
)
```

**Supported Intervals**:
- `1min` - 1-minute bars (highest resolution)
- `5min` - 5-minute bars
- `15min` - 15-minute bars
- `1h` - 1-hour bars
- `1d` - Daily bars

### 2. Strategy Configuration

Defines trading strategies:

```python
StrategyConfig(
    strategy_type='momentum',           # Strategy type
    strategy_name='my_momentum',        # Unique name
    allocation_pct=0.50,                # 50% of capital
    max_position_size=0.10,             # Max 10% per position
    parameters={                        # Strategy-specific parameters
        'lookback_period': 20,
        'momentum_threshold': 0.02,
        'enable_regime_filter': True
    }
)
```

**Available Strategies**:
- `momentum` - Momentum-based trading
- `mean_reversion` - Mean reversion strategy
- `trend_following` - Trend following
- `breakout` - Breakout trading
- `statistical_arbitrage` - Statistical arbitrage
- `pairs_trading` - Pairs trading
- `volatility` - Volatility-based trading
- `arbitrage` - Arbitrage opportunities
- `factor` - Multi-factor investment
- `multi_asset` - Multi-asset allocation

### 3. Risk Configuration

Defines risk limits:

```python
RiskConfig(
    initial_capital=1_000_000.0,    # Starting capital ($)
    max_position_size=0.10,         # 10% max per position
    max_daily_var=0.05,            # 5% max daily VaR
    max_concentration=0.20,        # 20% max concentration
    min_signal_confidence=0.60     # 60% min confidence
)
```

**Risk Parameters**:
- `initial_capital`: Starting portfolio value
- `max_position_size`: Maximum % of portfolio per position
- `max_daily_var`: Maximum daily Value at Risk
- `max_concentration`: Maximum concentration per position
- `min_signal_confidence`: Minimum signal confidence to trade

### 4. Execution Configuration

Defines execution simulation:

```python
ExecutionConfig(
    enable_realistic_fills=True,        # Enable realistic fills
    enable_cost_modeling=True,          # Enable cost models
    apply_slippage=True,                # Apply slippage
    apply_market_impact=True,           # Apply market impact
    enable_liquidity_filtering=True     # Filter by liquidity
)
```

### 5. Analytics Configuration

Defines analytics and reporting:

```python
AnalyticsConfig(
    enable_regime_attribution=True,     # Regime attribution
    enable_strategy_attribution=True,   # Strategy attribution
    generate_html_report=True,          # HTML report
    generate_json_report=True,          # JSON report
    generate_csv_trades=True            # CSV trade log
)
```

### Configuration Templates

Generate pre-configured templates:

```bash
# Simple single-strategy
python -m backtest.cli.main config --template simple --output simple.json

# Momentum strategy
python -m backtest.cli.main config --template momentum --output momentum.json

# Mean reversion strategy
python -m backtest.cli.main config --template mean_reversion --output mr.json

# Multi-strategy portfolio
python -m backtest.cli.main config --template multi_strategy --output multi.json
```

---

## Running Backtests

### Command-Line Interface

#### List Available Commands

```bash
python -m backtest.cli.main --help
```

#### Run Backtest

```bash
# With configuration file
python -m backtest.cli.main run --config my_config.json

# With inline parameters
python -m backtest.cli.main run \
  --symbols NVDA \
  --start-date 2024-01-01 \
  --end-date 2024-03-31 \
  --strategies momentum \
  --initial-capital 100000 \
  --output my_results
```

#### Validate Configuration

```bash
python -m backtest.cli.main validate --config my_config.json
```

#### List Strategies

```bash
python -m backtest.cli.main list-strategies
```

#### Interactive Mode

```bash
python -m backtest.cli.main interactive
```

### Python API

```python
import asyncio
from backtest.engine.institutional_backtest_engine import InstitutionalBacktestEngine
from backtest.config.backtest_config import *

async def run_backtest():
    # Create configuration
    config = BacktestConfiguration(
        backtest_name="my_api_backtest",
        backtest_mode="historical",
        data=DataConfig(
            symbols=['NVDA'],
            start_date='2024-01-01',
            end_date='2024-03-31',
            interval='1min'
        ),
        strategies=[
            StrategyConfig(
                strategy_type='momentum',
                strategy_name='momentum_1',
                allocation_pct=1.0,
                max_position_size=0.10
            )
        ],
        risk=RiskConfig(
            initial_capital=100_000.0,
            max_position_size=0.10,
            max_daily_var=0.05,
            max_concentration=0.20
        ),
        execution=ExecutionConfig(
            enable_realistic_fills=True,
            enable_cost_modeling=True
        ),
        analytics=AnalyticsConfig(
            enable_regime_attribution=True,
            generate_html_report=True
        )
    )
    
    # Create engine
    engine = InstitutionalBacktestEngine(config=config)
    
    # Initialize
    await engine.initialize()
    
    # Run backtest
    results = await engine.run_backtest()
    
    # Generate report
    report = await engine.generate_performance_report()
    
    return results, report

# Run
results, report = asyncio.run(run_backtest())
```

---

## Understanding Results

### Results Structure

Backtest results include:

```python
{
    'success': True,                    # Success flag
    'total_bars': 52685,               # Bars processed
    'duration': 26.00,                  # Duration (seconds)
    'bars_per_second': 2026.2,        # Processing speed
    'total_trades': 15,                # Total trades
    'summary': {                        # Performance summary
        'total_return_pct': 5.23,
        'sharpe_ratio': 1.45,
        'max_drawdown_pct': -2.10,
        'win_rate': 60.0,
        ...
    },
    'report': {...}                     # Detailed report
}
```

### Key Performance Metrics

#### Returns
- **Total Return**: Overall portfolio return (%)
- **Annualized Return**: Return annualized to yearly rate
- **Daily Returns**: Average daily return

#### Risk-Adjusted Metrics
- **Sharpe Ratio**: Return per unit of risk (>1.0 is good)
- **Sortino Ratio**: Return per unit of downside risk
- **Calmar Ratio**: Return / Max Drawdown

#### Risk Metrics
- **Max Drawdown**: Largest peak-to-trough decline (%)
- **Current Drawdown**: Current decline from peak (%)
- **Value at Risk (VaR)**: Maximum expected loss at confidence level
- **Volatility**: Standard deviation of returns

#### Trade Metrics
- **Total Trades**: Number of trades executed
- **Win Rate**: Percentage of profitable trades
- **Profit Factor**: Gross profit / Gross loss
- **Average Trade**: Average profit per trade

### Viewing Results

#### JSON Results
```bash
cat backtest_results/my_backtest_results.json | jq '.'
```

#### Trade Log (CSV)
```bash
# Open in spreadsheet
open backtest_results/my_backtest_trades.csv
```

#### Performance Report
```bash
# View JSON report
cat backtest_results/my_backtest_report.json | jq '.summary'
```

---

## Advanced Features

### 1. Multi-Strategy Coordination

Combine multiple strategies with automatic signal aggregation:

```python
strategies=[
    StrategyConfig(strategy_type='momentum', allocation_pct=0.60, ...),
    StrategyConfig(strategy_type='mean_reversion', allocation_pct=0.40, ...)
]
```

**Features**:
- Automatic signal aggregation
- Conflict resolution
- Strategy-level attribution
- Dynamic weighting

### 2. Regime-Aware Trading (Rule 13)

Automatic market regime detection and adaptation:

```python
strategies=[
    StrategyConfig(
        strategy_type='momentum',
        parameters={'enable_regime_filter': True}  # Enable regime awareness
    )
]
```

**Features**:
- Automatic regime detection per bar
- Regime-adjusted risk limits
- Regime-based strategy weighting
- Regime attribution in reports

### 3. Realistic Execution (Rule 12)

Institutional-grade execution simulation:

```python
execution=ExecutionConfig(
    enable_realistic_fills=True,        # Realistic fill simulation
    enable_cost_modeling=True,          # Transaction cost modeling
    apply_spread_cost=True,             # Bid-ask spread
    apply_market_impact=True,           # Market impact (Almgren-Chriss)
    apply_slippage=True,                # Slippage modeling
    enable_liquidity_filtering=True     # Liquidity-based filtering
)
```

**Cost Components**:
- Bid-ask spread (5 bps default)
- Market impact (Almgren-Chriss model)
- Slippage (2 bps base)
- Commission (configurable)

### 4. Risk Management (Rule 4)

Centralized risk authorization:

```python
risk=RiskConfig(
    max_position_size=0.10,      # Position limits
    max_daily_var=0.05,          # VaR limits
    max_concentration=0.20,      # Concentration limits
    min_signal_confidence=0.60   # Quality filters
)
```

**Features**:
- Pre-trade risk checks
- Position limit enforcement
- VaR monitoring
- Concentration limits

---

## Best Practices

### Data Selection

✅ **DO**:
- Start with 3+ months of data
- Use 1-minute bars for high resolution
- Include multiple symbols for portfolio effects
- Verify data quality before backtesting

❌ **DON'T**:
- Use less than 30 days (insufficient for warm-up)
- Mix timeframes in single backtest
- Skip data validation
- Ignore missing data periods

### Strategy Configuration

✅ **DO**:
- Enable regime filtering for adaptability
- Use multiple strategies for diversification
- Set reasonable confidence thresholds (60%+)
- Test strategies independently first

❌ **DON'T**:
- Over-allocate to single strategy (>70%)
- Use extreme parameters without validation
- Skip warm-up period considerations
- Ignore strategy correlations

### Risk Management

✅ **DO**:
- Start with conservative limits (5-10%)
- Monitor max drawdown carefully
- Use concentration limits
- Test different risk scenarios

❌ **DON'T**:
- Use aggressive limits without understanding
- Ignore VaR warnings
- Skip position limit checks
- Over-leverage the portfolio

### Performance Analysis

✅ **DO**:
- Review Sharpe ratio (target >1.0)
- Analyze drawdown periods
- Check win rate (50-60% typical)
- Compare regime performance

❌ **DON'T**:
- Focus only on returns
- Ignore risk metrics
- Skip trade-level analysis
- Overlook execution costs

---

## Troubleshooting

### Common Issues

#### 1. No Trades Executed

**Symptoms**: `total_trades: 0`

**Causes**:
- Indicators need warm-up (20-50 bars)
- Signal thresholds too strict
- Insufficient data period

**Solutions**:
```bash
# Use longer period
--start-date 2024-01-01 --end-date 2024-03-31  # 3 months

# Lower confidence threshold
min_signal_confidence=0.50  # From 0.60

# Check strategy parameters
momentum_threshold=0.015  # From 0.02
```

#### 2. Slow Performance

**Symptoms**: Processing < 500 bars/sec

**Causes**:
- Too many 1-minute bars
- Complex multi-strategy setup
- Insufficient system resources

**Solutions**:
```bash
# Use larger intervals
interval='5min'  # Instead of '1min'

# Reduce symbols
symbols=['NVDA']  # Instead of 5 symbols

# Shorter period for testing
--start-date 2024-03-01 --end-date 2024-03-31  # 1 month
```

#### 3. Memory Issues

**Symptoms**: Out of memory errors

**Causes**:
- Large dataset
- Memory leaks (shouldn't happen in prod)
- Insufficient RAM

**Solutions**:
```bash
# Process smaller chunks
interval='15min'  # Larger intervals

# Fewer symbols
symbols=['NVDA', 'TSLA']  # Instead of 10

# Shorter periods
# Process quarter at a time instead of full year
```

#### 4. Configuration Errors

**Symptoms**: `Configuration validation failed`

**Causes**:
- Missing required fields
- Invalid parameter values
- Incorrect date formats

**Solutions**:
```bash
# Validate configuration
python -m backtest.cli.main validate --config my_config.json

# Use templates
python -m backtest.cli.main config --template momentum --output fixed.json

# Check required fields
# - backtest_name
# - data.symbols
# - data.start_date, data.end_date
# - strategies (at least one)
# - risk.initial_capital
```

### Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `No historical data loaded` | Data loading failed | Check ClickHouse is running |
| `Regime engine not configured` | Missing regime engine | Enable regime detection |
| `Authorization rejected` | Risk limits exceeded | Adjust risk parameters |
| `Invalid configuration` | Configuration errors | Validate config file |

### Getting Help

1. **Check documentation**:
   ```bash
   python -m backtest.cli.main --help
   python -m backtest.cli.main run --help
   ```

2. **Review examples**:
   ```bash
   cat backtest/examples/README.md
   ```

3. **Validate configuration**:
   ```bash
   python -m backtest.cli.main validate --config my_config.json
   ```

4. **Enable verbose logging**:
   ```bash
   python -m backtest.cli.main run --config my_config.json --verbose
   ```

---

## API Reference

### Core Classes

#### InstitutionalBacktestEngine

Main backtest engine orchestrating all components.

```python
engine = InstitutionalBacktestEngine(config: BacktestConfiguration)
await engine.initialize() -> bool
await engine.run_backtest() -> Dict[str, Any]
await engine.generate_performance_report() -> Dict[str, Any]
await engine.shutdown() -> None
```

#### BacktestConfiguration

Complete backtest configuration.

```python
config = BacktestConfiguration(
    backtest_name: str,
    backtest_mode: str,
    data: DataConfig,
    strategies: List[StrategyConfig],
    risk: RiskConfig,
    execution: ExecutionConfig,
    analytics: AnalyticsConfig
)
```

### Configuration Classes

- `DataConfig` - Data configuration
- `StrategyConfig` - Strategy configuration
- `RiskConfig` - Risk parameters
- `ExecutionConfig` - Execution settings
- `AnalyticsConfig` - Analytics settings

### CLI Commands

- `run` - Run a backtest
- `validate` - Validate configuration
- `list-strategies` - List available strategies
- `interactive` - Interactive mode
- `config` - Generate configuration template
- `report` - Generate report from results

---

**🎉 You're now ready to use the Institutional Backtest System!**

Start with the examples, then progress to custom configurations. Happy backtesting! 🚀

