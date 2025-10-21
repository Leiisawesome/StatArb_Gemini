# Backtest Examples

This directory contains example scripts demonstrating advanced usage of the institutional backtest system.

## Available Examples

### Momentum Strategy Optimization (`test_momentum_optimization.py`)

**Purpose**: Systematic parameter optimization for momentum strategies

**Features**:
- Tests multiple parameter combinations (momentum threshold, ADX threshold, volume threshold)
- Compares performance across different configurations
- Statistical analysis of optimization results
- Identifies best parameter sets for different objectives (Sharpe ratio, total return, win rate)

**Usage**:
```bash
python backtest/examples/test_momentum_optimization.py
```

**What it does**:
1. Generates parameter combinations to test
2. Runs backtests for each combination
3. Analyzes results and identifies optimal parameters
4. Provides statistical summary of all tested configurations

**Output**:
- Performance comparison across parameter sets
- Best parameters for different optimization objectives
- Statistical summary (means, standard deviations, ranges)

**Note**: This example uses a short 4-day backtest period for faster optimization. For production use, extend the date range for more reliable results.