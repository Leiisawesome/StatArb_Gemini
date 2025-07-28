# 🚀 StatArb Gemini - Academic Algorithmic Trading System

A comprehensive algorithmic trading system that integrates academic research foundations with real-time trading capabilities, featuring multi-factor ensemble strategies and advanced risk management.

## 📊 **System Overview**

StatArb Gemini is built on a modular architecture that separates core academic components from application layers, providing:

- **Academic Momentum Signals**: Based on published research (Jegadeesh & Titman, Moskowitz et al., Gervais et al.)
- **Real-Time Trading**: Live market data processing and signal generation
- **Comprehensive Backtesting**: Historical validation with academic benchmarks
- **SPY Benchmark Analysis**: Performance comparison against S&P 500 ETF
- **Advanced Optimization**: Multi-dimensional parameter optimization

## 🏗️ **Architecture**

```
StatArb_Gemini/
├── core_structure/           # Core academic foundations
│   ├── signal_generation/    # Academic signal generation
│   │   ├── indicators/       # Enhanced technical indicators
│   │   └── enhanced_signal_generator.py
│   ├── performance/         # Benchmark analysis
│   │   └── benchmark_analyzer.py
│   └── infrastructure/      # Configuration & database
│       ├── config/          # Enhanced configuration management
│       └── database/        # ClickHouse integration
├── backtesting_framework/   # Historical testing
│   ├── strategies/          # Strategy implementations
│   ├── tests/              # Comprehensive test suite
│   └── optimization/       # Parameter optimization
├── real_time/              # Live trading system
│   └── enhanced_real_time_system.py
└── docs/                   # Complete documentation
```

## 🎯 **Key Features**

### **Academic Research Integration**
- **Multi-horizon Momentum**: 3-252 day lookback periods
- **Volume-Weighted Signals**: Based on Gervais et al. (2001)
- **Market Regime Detection**: Bull/bear/volatile market states
- **Crash Protection**: Daniel & Moskowitz (2016) momentum crash protection
- **Macro-Adjusted Momentum**: Business cycle effects (Chordia & Shivakumar, 2002)

### **Performance Metrics**
- **Information Ratio**: (Strategy Return - SPY Return) / Tracking Error
- **Sharpe Ratio**: Risk-adjusted returns
- **Maximum Drawdown**: Peak-to-trough decline
- **Beta**: Market correlation
- **Tracking Error**: Benchmark deviation

### **Academic Benchmarks**
- **Information Ratio**: > 0.5 (academic target)
- **Sharpe Ratio**: > 1.0 (risk-adjusted target)
- **Maximum Drawdown**: < 20% (risk management)
- **Beta**: < 0.3 (low market correlation)

## 🚀 **Quick Start**

### **Prerequisites**
- Python 3.8+
- ClickHouse database
- Polygon.io API key (for real-time data)

### **Installation**
```bash
# Clone repository
git clone https://github.com/Leiisawesome/StatArb_Gemini.git
cd StatArb_Gemini

# Install dependencies
pip install -r backtesting_framework/requirements.txt

# Setup ClickHouse
# (Follow ClickHouse installation guide)

# Configure API keys
export POLYGON_API_KEY="your_api_key_here"
```

### **Running Tests**
```bash
# Phase 0: Configuration Testing
python backtesting_framework/tests/phase_tests/test_phase0_configuration.py

# Phase 1: Core Enhancements
python backtesting_framework/tests/phase_tests/test_phase1_core_enhancements.py

# Phase 2: Backtesting Integration
python backtesting_framework/tests/phase_tests/test_phase2_integration.py

# Phase 3: Real-Time Integration
python real_time/test_phase3_real_time_integration.py
```

### **Running Backtesting**
```python
from backtesting_framework.enhanced_backtesting_engine import EnhancedBacktestingEngine

# Initialize engine
engine = EnhancedBacktestingEngine()

# Load data
engine.load_data(['SPY', 'AAPL', 'MSFT'], '2023-01-01', '2025-06-30')

# Run backtest
results = await engine.run_backtest()

# Analyze results
print(f"Information Ratio: {results['information_ratio']:.3f}")
```

### **Running Real-Time System**
```python
from real_time.enhanced_real_time_system import EnhancedRealTimeSystem

# Initialize system
system = EnhancedRealTimeSystem()

# Start trading
await system.initialize()
await system.start_trading()

# Monitor performance
status = system.get_system_status()
print(f"Portfolio Value: ${status['portfolio_value']:,.2f}")
```

## 📚 **Documentation**

### **Complete Documentation**
- **[System Documentation](docs/SYSTEM_DOCUMENTATION.md)**: Comprehensive system overview
- **[User Training Guide](docs/USER_TRAINING_GUIDE.md)**: Step-by-step training materials
- **[Enhanced Plan Phases 2-4](docs/ENHANCED_PLAN_PHASES_2_4.md)**: Implementation roadmap
- **[Enhanced Plan Phases 5-6](docs/ENHANCED_PLAN_PHASES_5_6.md)**: Optimization and documentation

### **Academic References**
1. **Jegadeesh & Titman (1993)**: Cross-sectional momentum
2. **Carhart (1997)**: Four-factor model
3. **Moskowitz & Grinblatt (1999)**: Industry momentum
4. **Hong & Stein (1999)**: News diffusion model
5. **Chordia & Shivakumar (2002)**: Business cycle effects
6. **Cooper et al. (2004)**: Market states
7. **Moskowitz et al. (2012)**: Time series momentum
8. **Gervais et al. (2001)**: Volume premium
9. **Daniel & Moskowitz (2016)**: Momentum crashes

## 🔧 **Configuration**

### **Strategy Configuration**
```yaml
# backtesting_framework/configs/strategies/enhanced_momentum_strategy.yaml
name: "enhanced_momentum"
version: "2.0.0"
parameters:
  momentum_lookback_short: 5
  momentum_lookback_medium: 21
  momentum_lookback_long: 60
  momentum_lookback_intermediate: 120
  volume_weight: 0.3
  regime_weight: 1.0
  signal_threshold: 0.7
```

### **Academic Parameter Ranges**
- **Momentum Lookback**: 3-252 days (academic standard)
- **Volume Weight**: 0.1-0.5 (Gervais et al., 2001)
- **Regime Weight**: 0.8-1.5 (Cooper et al., 2004)
- **Signal Threshold**: 0.5-0.9 (standard practice)

## 🧪 **Testing Framework**

### **Phase Tests**
- **Phase 0**: Configuration architecture validation
- **Phase 1**: Core academic enhancements testing
- **Phase 2**: Backtesting framework integration
- **Phase 3**: Real-time system integration

### **Additional Testing (Planned)**
- **Phase 4**: Real historical data testing
- **Phase 5**: Performance optimization
- **Phase 6**: Documentation and training

## 📊 **Performance Optimization**

### **Parameter Optimization**
```python
from backtesting_framework.optimization.advanced_parameter_optimizer import AdvancedParameterOptimizer

# Initialize optimizer
optimizer = AdvancedParameterOptimizer(config)

# Run optimization
results = await optimizer.optimize_parameters(data)
```

### **Multi-dimensional Sweeps**
- **Full Factorial**: Complete parameter space exploration
- **Latin Hypercube**: Efficient sampling methods
- **Sensitivity Analysis**: Parameter impact assessment

### **SPY Benchmark Optimization**
- **Information Ratio**: Primary optimization objective
- **Tracking Error**: Secondary objective
- **Beta**: Market correlation minimization
- **Excess Return**: Absolute performance target

## 🔍 **Troubleshooting**

### **Common Issues**
1. **Data Loading Errors**: Check ClickHouse connection and symbol names
2. **Configuration Errors**: Validate YAML syntax and parameter ranges
3. **Performance Issues**: Monitor system resources and database performance

### **Debug Mode**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 **License**

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 **Support**

- **GitHub Issues**: Report bugs and request features
- **Documentation**: Check the docs directory first
- **Academic Questions**: Review the academic references

---

## **Version History**

- **v3.0.0**: Complete academic integration with real-time capabilities
- **v2.0.0**: Enhanced backtesting framework with academic foundations  
- **v1.0.0**: Initial implementation with basic momentum strategy

---

**Built with ❤️ by the StatArb Gemini Team** 