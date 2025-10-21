# Quick Start Guide - StatArb_Gemini

**Version:** 2.0  
**Last Updated:** October 21, 2025  
**Estimated Time:** 10-15 minutes

---

## 🎯 OVERVIEW

StatArb_Gemini is an **institutional-grade algorithmic trading system** with:
- ✅ **10 enhanced trading strategies**
- ✅ **Centralized risk governance**
- ✅ **Multi-strategy coordination**
- ✅ **Comprehensive backtesting**
- ✅ **95% rule compliance**

---

## 🚀 GETTING STARTED

### Prerequisites
```bash
# Python 3.9+
python --version

# Virtual environment (recommended)
python -m venv ai_integration_env
source ai_integration_env/bin/activate  # macOS/Linux
# or
ai_integration_env\Scripts\activate     # Windows
```

### Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "import pandas, numpy, clickhouse_connect; print('✅ Ready')"
```

---

## 📊 SYSTEM ARCHITECTURE

### Core Components

```
StatArb_Gemini/
├── core_engine/              # 9 Production-Ready "Lego Bricks"
│   ├── data/                 # ClickHouseDataManager (Rule 3)
│   ├── regime/               # EnhancedRegimeEngine (Rule 2)
│   ├── processing/           # Indicators, Features, Signals
│   ├── trading/              # Strategies, Execution, Portfolio
│   ├── risk/                 # CentralRiskManager (Rule 4)
│   ├── analytics/            # Performance, Attribution, Metrics
│   └── system/               # Orchestrator, Integration
│
├── backtest/                 # Institutional Backtest Engine
│   ├── engine/               # InstitutionalBacktestEngine
│   ├── config/               # Backtest configurations
│   └── tests/                # Comprehensive test suite
│
├── tests/                    # System-wide tests
│
└── .cursor/rules/            # 7 Architectural Rules + 3 Standards
```

---

## 🎯 QUICK START: RUN A BACKTEST

### Step 1: Configure Your Backtest

```python
# backtest/config/examples/single_strategy.json
{
    "data_config": {
        "symbols": ["NVDA", "TSLA", "AAPL"],
        "start_date": "2024-12-20",
        "end_date": "2024-12-20",
        "interval": "1min"
    },
    "strategy_config": {
        "strategy_type": "momentum",
        "lookback_period": 60,
        "momentum_threshold": 0.02
    },
    "risk_config": {
        "initial_capital": 1000000,
        "max_position_size": 0.10,
        "max_daily_var": 0.05
    }
}
```

### Step 2: Run the Backtest

```python
from backtest.engine.institutional_backtest_engine import InstitutionalBacktestEngine
from backtest.config.backtest_config import BacktestConfig

# Load configuration
config = BacktestConfig.from_file('backtest/config/examples/single_strategy.json')

# Create engine
engine = InstitutionalBacktestEngine(config)

# Run backtest
results = await engine.run_backtest()

# Generate report
report = await engine.generate_report()
print(report)
```

### Step 3: Review Results

```python
# Performance Metrics
print(f"Total Return: {results['total_return']:.2%}")
print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
print(f"Max Drawdown: {results['max_drawdown']:.2%}")
print(f"Win Rate: {results['win_rate']:.2%}")
print(f"Total Trades: {results['total_trades']}")
```

---

## 🏗️ ARCHITECTURE: 7 CORE RULES

### Rule 1: Component Integration
- All components implement `ISystemComponent`
- Lifecycle managed by `HierarchicalSystemOrchestrator`
- **Status:** ✅ 98% compliant (25 components)

### Rule 2: Hierarchical Architecture & Regime-First
- 6-layer hierarchy: System → Governance → Data → Processing → Strategy → Execution
- `EnhancedRegimeEngine` initializes FIRST (order=5)
- **Status:** ✅ 96% compliant

### Rule 3: Unified Data Flow
- Single data authority: `ClickHouseDataManager`
- No direct database access allowed
- **Status:** ✅ 92% compliant

### Rule 4: Centralized Risk Governance
- `CentralRiskManager` = single point of authority
- ALL trades require authorization
- **Status:** ✅ 98% compliant (22 components)

### Rule 5: Multi-Strategy Coordination
- Signal aggregation via `MultiStrategySignalAggregator`
- Conflict resolution via `SignalConflictResolver`
- **Status:** ✅ 97% compliant (10 strategies)

### Rule 6: Advanced Analytics
- Performance attribution, regime-aware metrics
- Multi-timeframe analysis
- **Status:** ✅ 95% compliant

### Rule 7: Execution Management
- Unified execution via `UnifiedExecutionEngine`
- TCA, smart routing, market microstructure
- **Status:** ✅ 96% compliant

**Overall Compliance:** ✅ **95% - Institutional Grade**

---

## 🎯 USE CASES

### 1. Single Strategy Backtest
```python
# Use provided example
config = BacktestConfig.from_file('backtest/config/examples/single_strategy.json')
```

### 2. Multi-Strategy Backtest
```python
# Coordinate multiple strategies
config = BacktestConfig.from_file('backtest/config/examples/multi_strategy.json')
```

### 3. Regime-Adaptive Strategy
```python
# Strategies adapt to market regimes
config = BacktestConfig.from_file('backtest/config/examples/regime_adaptive.json')
```

---

## 📚 NEXT STEPS

### For Beginners:
1. ✅ Run the single strategy example above
2. 📖 Read [Architecture Overview](../architecture/README.md)
3. 🔍 Review [Compliance Audit](../code-reviews/CORE_ENGINE_7_RULES_COMPLIANCE_AUDIT.md)

### For Quants:
1. 📊 Review the 10 enhanced strategies in `core_engine/trading/strategies/implementations/`
2. 🧪 Run multi-strategy backtests
3. 🎯 Start Alpha hunting

### For Developers:
1. 📖 Study the [7 Architectural Rules](../architecture/RULES_OVERVIEW.md)
2. 🔧 Follow `.cursor/rules/` for development
3. ✅ Maintain 95%+ compliance

---

## 🆘 TROUBLESHOOTING

### Common Issues

**Issue:** Import errors
```bash
# Solution: Ensure you're in project root and venv is activated
cd /path/to/StatArb_Gemini
source ai_integration_env/bin/activate
export PYTHONPATH=$PYTHONPATH:$(pwd)
```

**Issue:** ClickHouse connection
```bash
# Solution: Check ClickHouse configuration
# Verify in backtest config that connection details are correct
```

**Issue:** Test failures
```bash
# Solution: Run tests individually to isolate
pytest tests/backtest/test_phase1_config.py -v
```

---

## 📖 ADDITIONAL RESOURCES

- **Architecture Details:** [../architecture/README.md](../architecture/README.md)
- **Compliance Audit:** [../code-reviews/CORE_ENGINE_7_RULES_COMPLIANCE_AUDIT.md](../code-reviews/CORE_ENGINE_7_RULES_COMPLIANCE_AUDIT.md)
- **Rule Reference:** [../../.cursor/rules/00-INDEX.mdc](../../.cursor/rules/00-INDEX.mdc)
- **Project README:** [../../README.md](../../README.md)

---

## ✅ CHECKLIST

Before starting Alpha hunting:
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Virtual environment activated
- [ ] Backtest examples run successfully
- [ ] Architecture overview reviewed
- [ ] Compliance audit understood (95% score)

**You're ready to start! 🚀**

---

**Last Updated:** October 21, 2025  
**Status:** Production Ready  
**Support:** See [docs/README.md](../README.md) for additional resources

