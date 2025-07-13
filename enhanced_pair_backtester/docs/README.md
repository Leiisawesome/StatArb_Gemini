# Enhanced Pair Backtesting System

A comprehensive, production-ready statistical arbitrage framework for pair trading strategies.

## 🚀 Features

- **Advanced Model Ensemble**: Kalman Filter, HMM Regime Detection, Ensemble ML
- **Multi-Source Data**: ClickHouse, Polygon, CSV support
- **Realistic Execution**: Transaction costs, slippage, market impact simulation
- **Comprehensive Analysis**: Performance, risk, and regime analysis
- **Professional Output**: Reports, visualizations, CSV exports
- **Production Ready**: Command-line interface with extensive configuration options

## 📋 System Requirements

- Python 3.8+
- ClickHouse database (optional, for data storage)
- Required packages (see requirements.txt)

## 🛠️ Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure data sources in `config/data_config.yaml`

## 🎯 Quick Start

### Basic Usage
```bash
# Run backtest on TLT/TMF pair
python main.py --pair TLT_TMF

# Quick test mode (faster execution)
python main.py --pair TLT_TMF --quick-test

# Full analysis with all models
python main.py --pair TLT_TMF --use-all-models --save-all
```

### Custom Pairs
```bash
# Custom symbol pair
python main.py --symbols AAPL MSFT --training-start 2023-01-01

# Custom configuration
python main.py --config my_config.json --verbose
```

## 📊 Supported Pairs

- **TLT/TMF**: Treasury bond ETFs
- **QQQ/TQQQ**: Technology sector leverage
- **IWM/TNA**: Small-cap leverage
- **UVIX/UVXY**: Volatility products
- **Custom pairs**: Any symbol combination

## 🔧 Configuration

### Command Line Options

- `--pair`: Pre-defined pair (TLT_TMF, QQQ_TQQQ, etc.)
- `--symbols`: Custom symbol pair
- `--training-start/end`: Training period dates
- `--testing-start/end`: Testing period dates
- `--use-all-models`: Enable all advanced models
- `--walk-forward`: Enable walk-forward analysis
- `--quick-test`: Fast execution mode
- `--save-all`: Save all outputs
- `--verbose`: Detailed logging

### Configuration Files

Use JSON configuration files for complex setups:
```json
{
  "symbol1": "TLT",
  "symbol2": "TMF",
  "training_start": "2023-01-01",
  "training_end": "2024-12-31",
  "use_kalman_filter": true,
  "use_hmm_regime": true,
  "use_ensemble_filter": true,
  "initial_capital": 1000000
}
```

## 📈 Model Components

### 1. Spread Calculator
- **OLS Regression**: Static hedge ratio estimation
- **Kalman Filter**: Dynamic hedge ratio with MLE parameter tuning
- **Total Least Squares**: Errors-in-variables approach
- **Rolling Methods**: Time-varying hedge ratios

### 2. Regime Detection
- **HMM Models**: 3-regime detection (Mean Reverting, Trending, Volatile)
- **Optimized Performance**: 10x subsampling for speed
- **Regime Statistics**: Persistence, volatility, frequency analysis

### 3. Ensemble Filter
- **Random Forest**: ML-based trade filtering
- **Technical Indicators**: RSI, moving averages, momentum
- **Regime Integration**: Regime-aware feature engineering
- **Confidence Scoring**: Signal strength assessment

### 4. Signal Generation
- **Regime-Aware Thresholds**: Different entry/exit for each regime
- **Multi-Layer Filtering**: Z-score, ensemble, strength requirements
- **Risk Management**: Kelly Criterion position sizing, stop-loss

## 📊 Output Analysis

### Performance Metrics
- Total Return, Annualized Return, Sharpe Ratio
- Maximum Drawdown, Calmar Ratio
- Win Rate, Profit Factor, Average Win/Loss

### Risk Metrics
- Value at Risk (VaR), Conditional VaR
- Beta, Alpha, Information Ratio
- Volatility analysis, correlation metrics

### Trading Statistics
- Total trades, execution costs
- Slippage analysis, market impact
- Regime-specific performance

## 🗂️ Project Structure

```
enhanced_pair_backtester/
├── main.py                 # Main entry point
├── config/                 # Configuration management
├── data/                   # Data loading and processing
├── models/                 # Model implementations
├── backtesting/            # Backtesting engine
├── execution/              # Trade execution simulation
├── analysis/               # Performance analysis
├── visualization/          # Chart generation
├── utils/                  # Utility functions
└── results/                # Output directory
```

## 🔄 Workflow

1. **Data Loading**: Multi-source data ingestion and validation
2. **Model Training**: Train ensemble models on historical data
3. **Signal Generation**: Generate regime-aware trading signals
4. **Backtesting**: Simulate realistic trade execution
5. **Analysis**: Comprehensive performance and risk analysis
6. **Visualization**: Generate professional charts and reports

## 📋 Example Results

```
PERFORMANCE METRICS:
  Total Return: 15.2%
  Annualized Return: 12.8%
  Sharpe Ratio: 1.45
  Maximum Drawdown: -8.3%

TRADING STATISTICS:
  Total Trades: 47
  Win Rate: 63.8%
  Profit Factor: 1.82

RISK METRICS:
  Value at Risk (95%): -2.1%
  Beta: 0.15
  Information Ratio: 0.89
```

## 🛡️ Risk Management

- **Position Sizing**: Kelly Criterion, Risk Parity
- **Stop Loss**: Dynamic stop-loss based on regime
- **Drawdown Control**: Maximum drawdown limits
- **Exposure Limits**: Position concentration controls

## 🔧 Advanced Features

### Walk-Forward Analysis
```bash
python main.py --pair TLT_TMF --walk-forward
```

### Custom Models
The system supports custom model implementations through plugin architecture.

### Real-Time Integration
Ready for live trading integration with broker APIs.

## 🐛 Troubleshooting

### Common Issues

1. **Data Connection**: Verify ClickHouse connection settings
2. **Memory Usage**: Use `--quick-test` for large datasets
3. **Model Convergence**: Check HMM parameters if convergence fails
4. **Performance**: Enable parallel processing with `--parallel`

### Debug Mode
```bash
python main.py --pair TLT_TMF --debug --log-level DEBUG
```

## 📚 Documentation

- **API Reference**: See docstrings in source code
- **Configuration Guide**: Check `config/` directory
- **Examples**: See `examples/` directory
- **Performance Tuning**: Refer to optimization guides

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add comprehensive tests
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- Built by Pro Quant Desk Trader
- Inspired by modern statistical arbitrage techniques
- Optimized for production trading environments

---

**Ready for Production Use** 🚀

For support and questions, please refer to the documentation or create an issue. 