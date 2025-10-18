# Institutional Backtest System - Examples

This directory contains ready-to-run examples demonstrating the capabilities of the institutional backtest system.

## 📚 Available Examples

### 1. **Simple Momentum Backtest** (`simple_momentum_backtest.py`)

**Best for**: Beginners, learning the basics

**Features**:
- Single momentum strategy
- Single symbol (NVDA)
- 3-month backtest period
- Realistic execution costs
- Complete performance report

**Usage**:
```bash
python backtest/examples/simple_momentum_backtest.py
```

**What you'll learn**:
- Basic configuration structure
- How to define strategies
- Running a backtest
- Interpreting results

---

### 2. **Multi-Strategy Backtest** (`multi_strategy_backtest.py`)

**Best for**: Intermediate users, portfolio management

**Features**:
- Combines momentum (60%) and mean reversion (40%) strategies
- Multiple symbols (NVDA, TSLA, AAPL)
- Strategy coordination and conflict resolution
- Performance attribution by strategy

**Usage**:
```bash
python backtest/examples/multi_strategy_backtest.py
```

**What you'll learn**:
- Multi-strategy configuration
- Strategy allocation
- Signal aggregation
- Strategy attribution analysis

---

### 3. **Advanced Regime-Aware Backtest** (`advanced_regime_aware_backtest.py`)

**Best for**: Advanced users, institutional-grade trading

**Features**:
- 3 strategies optimized for different market regimes
- Regime detection and adaptation (Rule 13: Regime-First Principle)
- 5-symbol portfolio (NVDA, TSLA, AAPL, MSFT, GOOGL)
- Complete regime and strategy attribution
- Institutional-grade risk management

**Usage**:
```bash
python backtest/examples/advanced_regime_aware_backtest.py
```

**What you'll learn**:
- Regime-aware trading
- Advanced multi-strategy coordination
- Regime attribution analysis
- Institutional risk management

---

## 🚀 Quick Start

### 1. Ensure Dependencies Installed

```bash
source ai_integration_env/bin/activate
pip install -r requirements.txt
```

### 2. Run an Example

```bash
# Start with the simple example
python backtest/examples/simple_momentum_backtest.py

# Progress to multi-strategy
python backtest/examples/multi_strategy_backtest.py

# Try advanced features
python backtest/examples/advanced_regime_aware_backtest.py
```

### 3. View Results

Results are saved to `backtest_results/` directory:
- `*_results.json` - Complete backtest results
- `*_report.json` - Detailed performance report
- `*_trades.csv` - Trade-by-trade history

---

## 📊 Example Comparison

| Feature | Simple | Multi-Strategy | Advanced |
|---------|--------|----------------|----------|
| **Complexity** | Beginner | Intermediate | Advanced |
| **Strategies** | 1 | 2 | 3 |
| **Symbols** | 1 | 3 | 5 |
| **Duration** | 3 months | 3 months | 6 months |
| **Regime Awareness** | Basic | Medium | Full |
| **Attribution** | Basic | Strategy | Regime + Strategy |
| **Run Time** | ~30 sec | ~60 sec | ~3 min |

---

## 🎯 Configuration Templates

Each example can be used as a template for your own backtests. Key configuration sections:

### Data Configuration
```python
data=DataConfig(
    symbols=['NVDA', 'TSLA'],  # Symbols to trade
    start_date='2024-01-01',   # Start date
    end_date='2024-03-31',     # End date
    interval='1min'            # Bar interval
)
```

### Strategy Configuration
```python
strategies=[
    StrategyConfig(
        strategy_type='momentum',        # Strategy type
        strategy_name='my_momentum',     # Unique name
        allocation_pct=0.60,             # 60% of capital
        max_position_size=0.10,          # Max position size
        parameters={                      # Strategy-specific params
            'lookback_period': 20,
            'momentum_threshold': 0.02
        }
    )
]
```

### Risk Configuration
```python
risk=RiskConfig(
    initial_capital=100_000.0,    # Starting capital
    max_position_size=0.10,       # 10% max per position
    max_daily_var=0.05,          # 5% max daily VaR
    max_concentration=0.20        # 20% max concentration
)
```

---

## 🔧 Customization Guide

### Modify an Example

1. **Copy an example**:
   ```bash
   cp backtest/examples/simple_momentum_backtest.py my_backtest.py
   ```

2. **Edit configuration**:
   - Change symbols
   - Adjust date range
   - Modify strategy parameters
   - Update risk limits

3. **Run your backtest**:
   ```bash
   python my_backtest.py
   ```

### Change Data Period

```python
# Use last 30 days
end_date = datetime.now()
start_date = end_date - timedelta(days=30)

# Use specific dates
start_date = '2024-01-01'
end_date = '2024-06-30'

# Use full year
start_date = '2024-01-01'
end_date = '2024-12-31'
```

### Add More Strategies

```python
strategies=[
    StrategyConfig(strategy_type='momentum', allocation_pct=0.33, ...),
    StrategyConfig(strategy_type='mean_reversion', allocation_pct=0.33, ...),
    StrategyConfig(strategy_type='trend_following', allocation_pct=0.34, ...)
]
```

### Adjust Risk Parameters

```python
# Conservative (lower risk)
risk=RiskConfig(
    max_position_size=0.05,  # 5% max
    max_daily_var=0.02,      # 2% VaR
    max_concentration=0.10   # 10% concentration
)

# Aggressive (higher risk)
risk=RiskConfig(
    max_position_size=0.15,  # 15% max
    max_daily_var=0.08,      # 8% VaR
    max_concentration=0.25   # 25% concentration
)
```

---

## 📈 Available Strategies

The system supports 10 built-in strategies:

1. **momentum** - Momentum-based trading
2. **mean_reversion** - Mean reversion strategy
3. **trend_following** - Trend following strategy
4. **breakout** - Breakout trading
5. **statistical_arbitrage** - Statistical arbitrage
6. **pairs_trading** - Pairs trading
7. **volatility** - Volatility-based trading
8. **arbitrage** - Arbitrage opportunities
9. **factor** - Multi-factor investment
10. **multi_asset** - Multi-asset allocation

Use the CLI to see available strategies:
```bash
python -m backtest.cli.main list-strategies
```

---

## 🎓 Learning Path

**Recommended progression**:

1. **Start here**: Run `simple_momentum_backtest.py`
   - Understand basic configuration
   - See a complete backtest lifecycle
   - Review performance metrics

2. **Level up**: Run `multi_strategy_backtest.py`
   - Learn strategy combination
   - Understand signal aggregation
   - Analyze strategy attribution

3. **Master it**: Run `advanced_regime_aware_backtest.py`
   - Experience regime detection
   - See adaptive strategy weighting
   - Understand institutional risk management

4. **Build your own**: Customize an example
   - Modify strategies
   - Adjust parameters
   - Create your own backtests

---

## 💡 Tips and Best Practices

### Performance Optimization
- Use larger intervals (`5min`, `15min`) for faster backtests
- Reduce date range for testing
- Start with fewer symbols

### Strategy Selection
- Use momentum in trending markets
- Use mean reversion in range-bound markets
- Combine strategies for diversification
- Enable regime filtering for better adaptation

### Risk Management
- Start with conservative risk limits
- Gradually increase as you understand performance
- Monitor drawdowns carefully
- Use position size limits

### Result Analysis
- Check trade count (should be > 0 after warm-up)
- Review win rate (50-60% is typical)
- Analyze drawdown (lower is better)
- Compare Sharpe ratio (> 1.0 is good)

---

## 🐛 Troubleshooting

### No Trades Executed

**Cause**: Indicators need warm-up period (20-50 bars)

**Solution**: 
- Use longer date range (30+ days minimum)
- Check signal generation is working after warm-up
- Review strategy parameters (thresholds may be too strict)

### Slow Performance

**Cause**: Too many bars or complex strategies

**Solution**:
- Use larger intervals (`5min` instead of `1min`)
- Reduce date range for testing
- Fewer symbols initially

### Configuration Errors

**Cause**: Invalid parameters

**Solution**:
- Check all required fields are present
- Verify dates are in `YYYY-MM-DD` format
- Ensure allocations sum to 1.0 (100%)
- Validate strategy types are supported

---

## 📞 Support

For questions or issues:
1. Check the main README in the project root
2. Review documentation in `docs/`
3. Examine test files in `tests/backtest/`
4. Use the CLI help: `python -m backtest.cli.main --help`

---

## 🎯 Next Steps

After running the examples:

1. **Explore the CLI**: Try the interactive mode
   ```bash
   python -m backtest.cli.main interactive
   ```

2. **Generate templates**: Create configuration files
   ```bash
   python -m backtest.cli.main config --template momentum --output my_config.json
   ```

3. **Run custom backtests**: Use your own configurations
   ```bash
   python -m backtest.cli.main run --config my_config.json
   ```

4. **Optimize strategies**: Test different parameters (Phase 9.2)

---

**Happy backtesting! 🚀**

