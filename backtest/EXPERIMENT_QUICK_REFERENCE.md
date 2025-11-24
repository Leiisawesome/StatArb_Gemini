# Experiment Suite - Quick Reference
====================================

## **🚀 Quick Start**

### **List All Experiments**
```bash
python3 backtest/run_suite.py --list
```

### **Run Single Experiment**
```bash
# Fast tests (< 2 min)
python3 backtest/run_suite.py --experiment smoke_test
python3 backtest/run_suite.py --experiment liquidity_stress
python3 backtest/run_suite.py --experiment correlation_stress
python3 backtest/run_suite.py --experiment survivorship_bias
python3 backtest/run_suite.py --experiment data_error

# Medium tests (2-10 min)
python3 backtest/run_suite.py --experiment baseline
python3 backtest/run_suite.py --experiment monte_carlo
python3 backtest/run_suite.py --experiment regime_specific

# Long tests (10-30 min)
python3 backtest/run_suite.py --experiment parameter_sweep
python3 backtest/run_suite.py --experiment walk_forward
```

### **Custom Config**
```bash
python3 backtest/run_suite.py --experiment baseline \
  --config backtest/configs/my_custom.yaml
```

---

## **📊 Experiment Catalog (All 10)**

| Experiment | Time | Purpose | Key Metric |
|------------|------|---------|------------|
| smoke_test | 30s | Sanity check | Pass/Fail |
| baseline | 5-10min | Performance baseline | Sharpe Ratio |
| parameter_sweep | 10-30min | Optimize parameters | Best combo |
| walk_forward | 20-60min | Out-of-sample validation | OOS performance |
| monte_carlo | 6-10min | Probabilistic risk | VaR, Percentiles |
| regime_specific | 5-10min | Regime adaptation | Best regime |
| liquidity_stress | 1-2min | Execution resilience | Cost degradation |
| correlation_stress | 1-2min | Diversification test | Sharpe degradation |
| survivorship_bias | 1-2min | Realistic expectations | Bias estimate |
| data_error | 2-3min | Data quality robustness | Sensitivity score |

---

## **🎯 Use Cases**

### **Daily Validation**
```bash
python3 backtest/run_suite.py --experiment smoke_test
```

### **Strategy Optimization**
```bash
python3 backtest/run_suite.py --experiment parameter_sweep
python3 backtest/run_suite.py --experiment walk_forward
```

### **Risk Assessment**
```bash
python3 backtest/run_suite.py --experiment monte_carlo
python3 backtest/run_suite.py --experiment liquidity_stress
python3 backtest/run_suite.py --experiment correlation_stress
```

### **Robustness Testing**
```bash
python3 backtest/run_suite.py --experiment survivorship_bias
python3 backtest/run_suite.py --experiment data_error
```

---

## **📁 Output Files**

All results saved to `backtest/results/`:

```
backtest/results/
├── experiment_summary.csv              # Summary of all runs
├── smoke_test_*.json                   # Full smoke test results
├── baseline_*.json                     # Full baseline results
├── parameter_sweep_*_sweep_*.csv       # Parameter grid
├── walk_forward_*_wf_*.csv            # Walk-forward windows
├── monte_carlo_*_mc_*.csv             # All MC simulations
├── regime_specific_*_regime_*.csv      # Regime breakdown
├── liquidity_stress_*_liquidity_*.csv  # Liquidity scenarios
├── correlation_stress_*_correlation_*.csv
├── survivorship_bias_*_survivorship_*.csv
└── data_error_*_data_errors_*.csv
```

---

## **⚙️ Config File Locations**

```
backtest/configs/
├── base_config.yaml           # Default settings (inherited by all)
├── smoke_test.yaml
├── baseline_backtest.yaml
├── parameter_sweep.yaml
├── walk_forward_quick.yaml
├── monte_carlo.yaml
├── regime_specific.yaml
├── liquidity_stress.yaml
├── correlation_stress.yaml
├── survivorship_bias.yaml
└── data_error.yaml
```

---

## **🔧 Common Customizations**

### **Change Test Period**
Edit config file:
```yaml
start_date: "2024-01-01"
end_date: "2024-01-31"
```

### **Change Strategy Parameters**
```yaml
strategy:
  parameters:
    zscore_entry_threshold: 1.5  # More signals
    base_position_pct: 0.03      # Larger positions
```

### **Change Number of Simulations (Monte Carlo)**
```yaml
monte_carlo:
  n_simulations: 100  # Increase from 20
```

### **Change Parameter Grid (Parameter Sweep)**
```yaml
parameter_grid:
  zscore_entry_threshold: [1.0, 1.5, 2.0, 2.5]
  base_position_pct: [0.01, 0.02, 0.03, 0.04, 0.05]
```

---

## **📈 Reading Results**

### **JSON Output Structure**
```python
{
  "experiment_name": "...",
  "experiment_type": "...",
  "performance": {
    "total_return_pct": 0.0,
    "sharpe_ratio": 0.0,
    "max_drawdown_pct": 0.0,
    "total_trades": 0,
    "win_rate": 0.0
  },
  "custom_metrics": { ... },
  "engine_results": { ... }
}
```

### **Quick Analysis**
```python
import pandas as pd

# Load all results
summary = pd.read_csv('backtest/results/experiment_summary.csv')
summary.sort_values('sharpe_ratio', ascending=False)

# Load specific experiment
mc_results = pd.read_csv('backtest/results/monte_carlo_*_mc_*.csv')
mc_results['total_return_pct'].describe()
```

---

## **🐛 Troubleshooting**

### **"Config file not found"**
```bash
# Check available configs
ls backtest/configs/
```

### **"Unknown experiment"**
```bash
# List available experiments
python3 backtest/run_suite.py --list
```

### **Slow Execution**
- Use single-day test periods for quick tests
- Reduce n_simulations for Monte Carlo
- Use smaller parameter grids for sweeps

### **No Trades Generated**
Expected behavior - adjust strategy thresholds:
```yaml
strategy:
  parameters:
    zscore_entry_threshold: 1.5  # Lower = more signals
    enable_regime_filter: false   # Disable filtering
    scan_all_bars: true           # Check all bars
```

---

## **✅ Validation Checklist**

Before committing changes:

- [ ] Run smoke test: `python3 backtest/run_suite.py --experiment smoke_test`
- [ ] Check results directory: `ls backtest/results/`
- [ ] Verify JSON output: `python3 -m json.tool backtest/results/*.json`
- [ ] Check CSV output: `head backtest/results/*.csv`
- [ ] Run linter: `flake8 backtest/experiments/`

---

**For Full Documentation:**
- `docs/08_analysis/ALL_10_EXPERIMENTS_COMPLETE.md` - Complete catalog
- `docs/08_analysis/EXPERIMENT_VALIDATION_COMPLETE.md` - Test results
- `backtest/QUICK_START.md` - Getting started guide
- `backtest/experiments/README.md` - Framework details

---

**Status:** ✅ All 10 experiments ready for production use!

