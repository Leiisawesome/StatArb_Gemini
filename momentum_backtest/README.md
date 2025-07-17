# Production-Ready Momentum Backtest System

A comprehensive, enterprise-grade momentum trading backtesting framework with risk management, performance analytics, and production deployment capabilities.

## 🚀 Features

### Core Capabilities
- **Configurable Training/Testing Periods**: Flexible date ranges for backtesting
- **Academic-Standard Momentum Strategy**: Based on Jegadeesh & Titman (1993) research
- **Production-Grade Risk Management**: Position sizing, portfolio risk controls, drawdown monitoring
- **Comprehensive Performance Analytics**: Sharpe ratio, Sortino ratio, Calmar ratio, drawdown analysis
- **ClickHouse Integration**: High-performance database queries for large-scale tick data
- **Modular Architecture**: Separated concerns for maintainability and testing

### Technical Infrastructure
- **Configuration Management**: Environment-based configs with validation
- **Logging System**: Structured logging with file rotation
- **Error Handling**: Robust error management with detailed diagnostics
- **Performance Optimization**: Efficient data processing and memory management
- **Testing Framework**: Comprehensive test coverage with synthetic data support

## 📁 Project Structure

```
momentum_backtest/
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── setup.py                          # Package installation
├── config/                           # Configuration files
│   ├── default_config.json          # Default configuration
│   └── production_config.json       # Production settings
├── src/                              # Source code
│   ├── __init__.py
│   ├── data/                         # Data loading and management
│   │   ├── __init__.py
│   │   └── clickhouse_connector.py   # Database integration
│   ├── strategy/                     # Trading strategies
│   │   ├── __init__.py
│   │   ├── base_strategy.py          # Strategy interface
│   │   └── momentum_strategy.py      # Momentum implementation
│   ├── backtesting/                  # Backtesting engine
│   │   ├── __init__.py
│   │   ├── backtest_engine.py        # Core backtesting logic
│   │   └── portfolio_manager.py      # Portfolio tracking
│   ├── risk/                         # Risk management
│   │   ├── __init__.py
│   │   └── risk_manager.py           # Position sizing & risk controls
│   └── utils/                        # Utilities
│       ├── __init__.py
│       ├── logger.py                 # Logging configuration
│       └── performance.py            # Performance metrics
├── scripts/                          # Executable scripts
│   ├── run_backtest.py              # Main backtest runner
│   └── quick_test.py                # Quick validation
├── tests/                           # Test suite
│   ├── __init__.py
│   ├── test_data_loader.py          # Data loading tests
│   ├── test_strategy.py             # Strategy tests
│   └── test_backtest.py             # Backtest integration tests
├── docs/                            # Documentation
│   ├── configuration.md             # Configuration guide
│   ├── api_reference.md             # API documentation
│   └── examples.md                  # Usage examples
└── results/                         # Output directory
    ├── backtests/                   # Backtest results
    └── reports/                     # Performance reports
```

## 🔧 Installation

1. **Clone and setup environment**:
```bash
cd momentum_backtest
pip install -e .
```

2. **Configure database connection**:
```bash
cp config/default_config.json config/local_config.json
# Edit local_config.json with your ClickHouse settings
```

## 🎯 Quick Start

### Basic Usage
```python
from momentum_backtest import MomentumBacktest

# Initialize with configuration
backtest = MomentumBacktest.from_config('config/default_config.json')

# Run backtest
results = backtest.run(
    training_start='2023-01-01',
    training_end='2024-01-31',
    testing_start='2025-01-01',
    testing_end='2025-06-30',
    initial_capital=100000
)

# Print results
print(f"Total Return: {results.total_return:.2%}")
print(f"Sharpe Ratio: {results.sharpe_ratio:.2f}")
```

### Command Line Interface
```bash
# Run with default configuration
python scripts/run_backtest.py

# Run with custom parameters
python scripts/run_backtest.py \
    --training-start 2023-01-01 \
    --training-end 2024-01-31 \
    --testing-start 2025-01-01 \
    --testing-end 2025-06-30 \
    --initial-capital 100000

# Quick validation test
python scripts/quick_test.py
```

## Key Features
- Real ClickHouse data integration
- Professional momentum strategy implementation
- Realistic transaction cost modeling
- Comprehensive performance analytics
- Risk management integration
- Production-ready execution simulation

## Quick Start

### Option 1: Interactive Mode (Recommended)
```bash
# Start interactive quick start
python quickstart.py

# Follow the menu options:
# 1. Run Setup (install dependencies)
# 2. Run System Tests (validate components) 
# 3. Run Backtest (execute momentum strategy)
# 4. Show Results (view output files)
```

### Option 2: Automatic Mode
```bash
# Run complete pipeline automatically
python quickstart.py auto
```

### Option 3: Manual Step-by-Step
```bash
# 1. Setup environment
python setup.py

# 2. Validate system (optional)
python test_system.py

# 3. Run backtest
python run_backtest.py
```

### Option 4: Individual Components
```bash
# Setup only
python quickstart.py setup

# Tests only  
python quickstart.py test

# Backtest only
python quickstart.py backtest
```

## Advanced Usage
```bash
# Custom configuration
python run_backtest.py --config config/backtest_config.yaml

# Custom output directory
python run_backtest.py --output-dir custom_results

# Debug mode
python run_backtest.py --log-level DEBUG
```

## Results
All backtest results, performance reports, and visualizations will be saved in the `results/` directory.
