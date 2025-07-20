# Backtesting Framework - Clean Codebase

A professional quantitative trading backtesting framework with modular architecture and core structure integration.

## 📁 Project Structure

```
backtesting_framework/
├── 📚 Documentation
│   ├── README.md                 # Main documentation
│   ├── QUICK_START.md           # Getting started guide  
│   ├── DATA_INTEGRATION_GUIDE.md # Data integration setup
│   └── FRAMEWORK_SUMMARY.md     # Framework architecture overview
│
├── 🎯 Core Modules
│   ├── strategies/              # Trading strategy implementations
│   │   ├── __init__.py
│   │   ├── base_strategy.py     # Abstract base strategy class
│   │   ├── momentum_strategy.py # Advanced momentum trading strategy
│   │   └── pairs_trading.py     # Pairs trading strategy
│   │
│   ├── utils/                   # Utility modules
│   │   ├── __init__.py
│   │   └── data_integration.py  # Data loading and integration
│   │
│   └── configs/                 # Configuration files
│       ├── base_config.yaml     # Base configuration
│       └── strategies/          # Strategy-specific configs
│
├── 🧪 Development
│   ├── experiments/             # Research and experimentation
│   │   ├── __init__.py
│   │   ├── experiment_runner.py # Framework for running experiments
│   │   ├── parameter_sweep.py   # Parameter optimization tools
│   │   └── run_example.py       # Example usage
│   │
│   └── results/                 # Output directory (empty, populated at runtime)
│
├── ⚙️ Configuration
│   ├── requirements.txt         # Python dependencies
│   ├── .gitignore              # Git ignore patterns
│   └── __init__.py             # Package initialization
```

## 🚀 Key Features

### **Professional Architecture**
- ✅ Modular strategy design with abstract base classes
- ✅ Loose coupling with core_structure integration
- ✅ Graceful fallback implementations
- ✅ Comprehensive error handling and logging

### **Advanced Momentum Strategy**
- ✅ Multiple momentum calculation types (simple, log, risk-adjusted)
- ✅ Sophisticated configuration with 20+ parameters
- ✅ Training and validation phases
- ✅ Real-time signal generation and position sizing

### **Data Integration**
- ✅ ClickHouse integration for historical data
- ✅ Fallback data management systems
- ✅ Data quality validation and filtering
- ✅ Multiple data source support

### **Development Ready**
- ✅ Clean codebase with no temporary files
- ✅ Comprehensive documentation
- ✅ Example usage and experimentation framework
- ✅ Professional git ignore patterns

## 📊 Current Status

**✅ PRODUCTION READY**
- All temporary debug and test files removed
- Python cache files cleaned
- Documentation organized and current
- Professional project structure maintained
- Core functionality tested and working

## 🎯 Next Steps

1. **Strategy Development**: Add new trading strategies in `strategies/`
2. **Data Enhancement**: Extend data sources in `utils/data_integration.py`
3. **Experimentation**: Use `experiments/` for research and optimization
4. **Configuration**: Customize settings in `configs/`

---

*Clean codebase maintained as of July 20, 2025*
