# Desk-Grade Experiment Suite

Clean orchestration layer for `InstitutionalBacktestEngine`.

## 🎯 Design Principles

1. **Zero Re-Implementation**: Use engine as black box, no custom logic
2. **Consistent Interface**: All experiments inherit from `BaseExperiment`
3. **Config-Driven**: All parameters via YAML configs
4. **Structured Output**: JSON results + CSV summaries

---

## 📁 Directory Structure

```
backtest/
├── engine/                          # Black box (don't touch)
│   ├── institutional_backtest_engine.py
│   ├── historical_execution_simulator.py
│   └── strategy_optimizer.py
│
├── experiments/                     # Experiment implementations
│   ├── __init__.py
│   ├── base_experiment.py          # Abstract base class
│   ├── smoke_test.py               # Experiment 1
│   └── (more experiments TBD)
│
├── configs/                         # YAML configs
│   ├── base_config.yaml            # Default settings
│   ├── smoke_test.yaml             # Smoke test config
│   └── baseline_aapl.yaml          # Baseline backtest config
│
├── utils/                           # Shared utilities
│   └── config_loader.py            # YAML loader
│
├── results/                         # Output directory
│   ├── *.json                      # Individual results
│   └── experiment_summary.csv      # All runs
│
└── run_suite.py                     # Master runner
```

---

## 🚀 Quick Start

### 1. Run Smoke Test
```bash
cd backtest
python run_suite.py --experiment smoke_test
```

### 2. Run with Custom Config
```bash
python run_suite.py --experiment baseline --config configs/my_config.yaml
```

### 3. List Available Experiments
```bash
python run_suite.py --list
```

---

## 📋 Available Experiments

### **Experiment 1: Smoke Test**
- **Purpose**: Quick sanity check (< 30 seconds)
- **Config**: `configs/smoke_test.yaml`
- **Tests**:
  - Engine initialization
  - Single symbol, 1-day backtest
  - Simple mean reversion strategy
  - Result generation

**Run:**
```bash
python run_suite.py --experiment smoke_test
```

---

## ⚙️ Configuration

### Base Config (`configs/base_config.yaml`)
Default settings for all experiments. Override in experiment-specific configs.

**Key Parameters:**
- `symbols`: List of symbols to trade
- `interval`: Data frequency (`1min`, `5min`, `1h`, `1D`)
- `start_date` / `end_date`: Backtest period
- `initial_capital`: Starting portfolio value
- `strategies`: List of strategy configurations

**Example:**
```yaml
symbols: ["AAPL", "TSLA"]
interval: "1min"
start_date: "2023-01-01"
end_date: "2024-12-31"
initial_capital: 5000000

strategies:
  - type: "mean_reversion"
    name: "MR_20"
    allocation_pct: 1.0
    parameters:
      lookback: 20
      z_entry: 2.0
      z_exit: 0.5
```

---

## 📊 Output

### Console Summary
```
================================================================================
📊 EXPERIMENT SUMMARY: Smoke_Test
================================================================================
Type:           smoke_test
Status:         ✅ SUCCESS
Duration:       12.45s

Performance Metrics:
  Total Return:       2.35%
  Sharpe Ratio:       1.42
  Max Drawdown:      -0.87%
  Total Trades:         23
  Win Rate:          56.5%
================================================================================
```

### JSON Results
Saved to `results/{experiment_name}_{timestamp}.json`:
```json
{
  "experiment_name": "Smoke_Test",
  "experiment_type": "smoke_test",
  "run_timestamp": "2025-11-23T10:30:00",
  "duration_seconds": 12.45,
  "performance": {
    "total_return_pct": 2.35,
    "sharpe_ratio": 1.42,
    "max_drawdown_pct": -0.87,
    "total_trades": 23,
    "win_rate": 56.5
  },
  "engine_results": { /* full engine output */ }
}
```

### CSV Summary
All runs appended to `results/experiment_summary.csv`:
```csv
timestamp,experiment_name,experiment_type,total_return_pct,sharpe_ratio,...
2025-11-23T10:30:00,Smoke_Test,smoke_test,2.35,1.42,-0.87,23,56.5,12.45,true
```

---

## 🔧 Creating New Experiments

### Step 1: Create Experiment Class

```python
# backtest/experiments/my_experiment.py

from backtest.experiments.base_experiment import BaseExperiment, ExperimentResult
from backtest.engine.institutional_backtest_engine import InstitutionalBacktestEngine

class MyExperiment(BaseExperiment):
    def get_description(self) -> str:
        return "My custom experiment"
    
    async def run(self) -> ExperimentResult:
        # Create config
        config = self._create_config()
        
        # Run engine (BLACK BOX - no custom logic)
        engine = InstitutionalBacktestEngine(config)
        await engine.initialize()
        results = await engine.run_backtest()
        
        # Extract metrics
        metrics = self._extract_performance_metrics(results)
        
        # Return structured result
        return ExperimentResult(...)
```

### Step 2: Create Config File

```yaml
# backtest/configs/my_experiment.yaml
experiment_name: "My_Experiment"
experiment_type: "custom"

symbols: ["AAPL"]
# ... other settings
```

### Step 3: Register in `run_suite.py`

```python
EXPERIMENTS = {
    'my_experiment': {
        'class': MyExperiment,
        'default_config': 'backtest/configs/my_experiment.yaml',
        'description': 'My custom experiment'
    },
    # ... other experiments
}
```

### Step 4: Run

```bash
python run_suite.py --experiment my_experiment
```

---

## 🚫 Prohibited Patterns

### ❌ DON'T Re-Implement Engine Logic
```python
# BAD - custom signal generation
class BadExperiment(BaseExperiment):
    def calculate_signals(self, data):
        return my_custom_logic(data)  # ❌ NO!
```

### ❌ DON'T Bypass Config
```python
# BAD - hardcoded parameters
config = BacktestConfig(
    symbols=["AAPL"],  # ❌ Should come from YAML
    lookback=20        # ❌ Should come from YAML
)
```

### ✅ DO Orchestrate Engine
```python
# GOOD - use engine as black box
async def run(self):
    config = load_config(self.config_path)
    engine = InstitutionalBacktestEngine(config)
    await engine.initialize()
    results = await engine.run_backtest()
    return self._format_results(results)
```

---

## 📚 Experiment Roadmap

### ✅ Implemented
- [x] **Experiment 1**: Smoke Test

### 🔄 Planned (Priority Order)
- [ ] **Experiment 2**: Baseline Backtest (full period)
- [ ] **Experiment 3**: Parameter Sweep (grid search)
- [ ] **Experiment 4**: Walk-Forward (rolling windows)
- [ ] **Experiment 5**: Monte Carlo (resampling)
- [ ] **Experiment 6**: Regime Sensitivity
- [ ] **Experiment 7**: Liquidity Stress
- [ ] **Experiment 8**: Execution Comparison
- [ ] **Experiment 9**: Data Resilience

---

## 🎓 Best Practices

1. **Always use YAML configs** - no hardcoded parameters
2. **Never re-implement engine logic** - orchestrate only
3. **Save all results** - enable reproducibility
4. **Log experiment metadata** - git hash, versions, RNG seeds
5. **Use base_config.yaml** - DRY principle
6. **Print concise summaries** - desk-readable output
7. **Structure output** - JSON + CSV for analysis

---

## 🔍 Troubleshooting

### Issue: Config not found
```bash
FileNotFoundError: Config file not found: my_config.yaml
```
**Solution**: Use absolute path or ensure working directory is `backtest/`

### Issue: Engine import fails
```bash
ImportError: cannot import InstitutionalBacktestEngine
```
**Solution**: Ensure parent directory is in Python path

### Issue: ClickHouse connection error
```bash
ConnectionError: Could not connect to ClickHouse
```
**Solution**: Update `clickhouse` section in config file

---

## 📞 Support

For issues or questions:
1. Check experiment logs in `results/`
2. Review base config (`configs/base_config.yaml`)
3. Verify engine initialization in smoke test

---

**Version**: 1.0  
**Last Updated**: November 23, 2025  
**Maintainer**: StatArb_Gemini Core Engine

