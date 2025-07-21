# StatArb Backtesting Framework

**Status:** ✅ Production Ready | Clean Codebase | Portfolio Tracking Fixed

Professional backtesting framework for quantitative trading strategies, designed to work with the StatArb_Gemini core system.

## Architecture Overview

This framework provides a clean separation between:
- **Core System**: Production-ready trading infrastructure (`core_structure/`)
- **Backtesting**: Research and development environment (`backtesting_framework/`)

## Directory Structure

```
backtesting_framework/
├── strategies/          # Strategy implementations
│   ├── base_strategy.py # Base strategy class
│   ├── pairs_trading.py # Statistical arbitrage strategy
│   └── __init__.py
├── experiments/         # Strategy experiments
│   ├── experiment_runner.py # Main experiment orchestrator
│   ├── parameter_sweep.py  # Parameter optimization
│   ├── run_example.py      # Example usage script
│   └── __init__.py
├── configs/             # Strategy configurations
│   ├── base_config.yaml # Base configuration
│   └── strategies/      # Strategy-specific configs
│       └── pairs_trading.yaml
├── results/             # Backtest results and reports (created at runtime)
├── utils/               # Backtesting utilities (future expansion)
├── docs/                # Comprehensive documentation
│   ├── README.md       # Documentation index
│   ├── QUICK_START.md  # Getting started guide
│   └── *.md            # Additional guides and references
├── requirements.txt     # Dependencies
├── README.md           # Framework overview (this file)
└── __init__.py         # Package initialization
```

## 📚 Documentation

**Complete documentation is available in the [`docs/`](docs/) directory:**

- 🚀 **[Quick Start Guide](docs/QUICK_START.md)** - Get up and running immediately
- 📋 **[Framework Summary](docs/FRAMEWORK_SUMMARY.md)** - Complete architectural overview  
- 🏭 **[Production Setup](docs/PRODUCTION_SETUP_GUIDE.md)** - Production deployment guide
- 📊 **[Data Integration](docs/DATA_INTEGRATION_GUIDE.md)** - Data sources and setup
- ✅ **[Project Status](docs/CLEANUP_COMPLETE.md)** - Current state and cleanup summary

**Start with the [Documentation Index](docs/README.md) for a complete overview.**

## Key Benefits

### 1. **Clean Separation**
- Core system remains production-ready
- No risk of test code contaminating live systems
- Independent versioning and development

### 2. **Rapid Strategy Development**
- Quick iteration on strategy ideas
- Easy parameter optimization
- Comprehensive performance analysis

### 3. **Professional Workflow**
- Structured experiment management
- Reproducible results
- Comprehensive reporting

## Usage Examples

### Basic Strategy Backtest
```python
from backtesting_framework import ExperimentRunner, ExperimentConfig

# Create configuration
config = ExperimentConfig(
    name="My Strategy Test",
    symbols=["AAPL", "MSFT"],
    start_date="2023-01-01",
    end_date="2023-12-31",
    strategy_class="PairsTradingStrategy",
    initial_capital=100000.0
)

# Run experiment
runner = ExperimentRunner()
result = runner.run_experiment(config)

# Analyze results
print(f"Total Return: {result.strategy_metrics['total_return']:.2%}")
print(f"Sharpe Ratio: {result.strategy_metrics['sharpe_ratio']:.2f}")
```

### Parameter Optimization
```python
from backtesting_framework import ParameterSweep, OptimizationConfig

# Define parameter ranges
opt_config = OptimizationConfig(
    optimization_metric="sharpe_ratio",
    search_method="grid_search",
    parameter_ranges={
        'z_entry_threshold': [1.5, 2.0, 2.5, 3.0],
        'lookback_window': [30, 60, 90, 120]
    }
)

# Run optimization
sweep = ParameterSweep(base_config, opt_config)
opt_result = sweep.optimize(PairsTradingStrategy)

# Get best parameters
print(f"Best Sharpe: {opt_result.best_metric:.2f}")
print(f"Best Params: {opt_result.best_params}")
```

### Configuration File Usage
```python
# Load from YAML file
result = runner.run_experiment_from_file("configs/strategies/pairs_trading.yaml")
```

## Integration with Core System

The backtesting framework seamlessly integrates with the StatArb_Gemini core system:

```python
# Import core components
from core_structure.market_data.data_manager import DataManager
from core_structure.analytics.performance_analytics import PerformanceAnalyzer

# Use in backtesting
data_manager = DataManager()
performance_analyzer = PerformanceAnalyzer()
```

## Best Practices

### 1. **Strategy Development**
- Inherit from `BaseStrategy` class
- Implement required methods: `generate_signals()`, `calculate_positions()`
- Use proper error handling and logging

### 2. **Experiment Management**
- Use descriptive experiment names
- Save all parameters and results
- Include data versioning

### 3. **Performance Analysis**
- Use multiple performance metrics
- Include benchmark comparisons
- Analyze drawdowns and risk metrics

### 4. **Reproducibility**
- Set random seeds
- Save all data and parameters
- Use version control for configurations

## Configuration

Strategy configurations are stored in YAML format:

```yaml
# configs/strategies/pairs_trading.yaml
name: "AAPL-MSFT Pairs Trading"
description: "Statistical arbitrage between AAPL and MSFT"
symbols: ["AAPL", "MSFT"]
start_date: "2023-01-01"
end_date: "2023-12-31"

strategy_class: "PairsTradingStrategy"
strategy_params:
  z_entry_threshold: 2.0
  z_exit_threshold: 0.5
  lookback_window: 60
  correlation_threshold: 0.8

initial_capital: 100000.0
commission_rate: 0.001
slippage_rate: 0.0005
max_position_size: 0.2
benchmark_symbol: "SPY"
```

## Dependencies

The framework requires the core system components plus additional backtesting-specific packages:

```
pandas>=1.5.0
numpy>=1.21.0
matplotlib>=3.5.0
seaborn>=0.11.0
scipy>=1.9.0
scikit-learn>=1.1.0
plotly>=5.0.0
pyyaml>=6.0
```

## Getting Started

1. **Install Dependencies**
   ```bash
   cd backtesting_framework
   pip install -r requirements.txt
   ```

2. **Run Example**
   ```bash
   python experiments/run_example.py
   ```

3. **Create Custom Strategy**
   ```bash
   cp strategies/base_strategy.py strategies/my_strategy.py
   # Edit my_strategy.py with your logic
   ```

4. **Run Experiment**
   ```bash
   python experiments/experiment_runner.py
   ```

## Contributing

When adding new strategies or experiments:

1. Follow the existing code structure
2. Add comprehensive documentation
3. Include unit tests
4. Update this README if needed

## License

This framework is part of the StatArb_Gemini project and follows the same licensing terms. 