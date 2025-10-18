# 🚀 Strategy Optimization Quick Start Guide

**Quick Reference**: Start here for each optimization session

---

## 📋 CURRENT STATUS

**Phase**: Phase 0 - Infrastructure Setup (Not Started)  
**Next Steps**: Create optimization framework, run baselines  
**Strategies**: 0/10 optimized

---

## 🎯 QUICK SESSION CHECKLIST

### **Before Starting Any Phase**
- [ ] Read phase goals in `.cursor/rules/strategy-optimization-workflow.mdc`
- [ ] Review success criteria (Sharpe > 1.5, DD < 15%, etc.)
- [ ] Prepare backtest configuration
- [ ] Clear terminal, activate environment

### **During Session**
- [ ] Follow 7-step Escort process (Baseline → Search → Regime → Cost → Stats → Integration → Docs)
- [ ] Run tests continuously
- [ ] Document metrics in real-time
- [ ] Save intermediate results

### **After Session**
- [ ] Verify all success criteria met
- [ ] Generate phase completion document
- [ ] Update this quick start with progress
- [ ] Commit changes with clear message

---

## 🔧 STANDARD COMMANDS

### **Environment Setup**
```bash
# Activate environment
source ai_integration_env/bin/activate

# Verify ClickHouse running
brew services list | grep clickhouse
```

### **Run Baseline Backtest**
```bash
# Single strategy baseline
python -c "
from backtest.optimization.strategy_optimizer import StrategyOptimizer
from core_engine.type_definitions.strategy import StrategyType

optimizer = StrategyOptimizer()
result = await optimizer.run_baseline(StrategyType.MOMENTUM)
print(result)
"
```

### **Run Parameter Optimization**
```bash
# Grid search optimization
python -c "
from backtest.optimization.strategy_optimizer import StrategyOptimizer

optimizer = StrategyOptimizer()
results = await optimizer.optimize_strategy(
    strategy_type=StrategyType.MOMENTUM,
    search_space={
        'lookback_period': [10, 20, 30, 60],
        'momentum_threshold': [0.01, 0.02, 0.03, 0.04]
    },
    method='grid_search'
)
print(results)
"
```

### **Run Tests**
```bash
# Phase-specific tests
pytest tests/optimization/test_phase0_infrastructure.py -v

# All optimization tests
pytest tests/optimization/ -v

# With coverage
pytest tests/optimization/ --cov=backtest.optimization --cov-report=term-missing
```

---

## 📊 SUCCESS CRITERIA AT A GLANCE

### **Minimum Requirements** (Must Pass)
- Sharpe Ratio > 1.5
- Max Drawdown < 15%
- Win Rate > 55%
- Profit Factor > 1.5
- Positive in 4+ regimes
- > 100 trades
- Positive after costs

### **Target Goals** (Aim For)
- Sharpe Ratio > 2.0
- Max Drawdown < 10%
- Win Rate > 60%
- Profit Factor > 2.0
- Positive in all 5 regimes
- > 200 trades

---

## 🗺️ PHASE ROADMAP

### **Phase 0: Infrastructure** (Current)
**Goal**: Create optimization framework  
**Duration**: 1 session  
**Status**: Not Started ⏳

### **Tier 1: Core Alpha** (Next)
- Phase 1: Statistical Arbitrage (2-3 sessions)
- Phase 2: Momentum (2-3 sessions)
- Phase 3: Mean Reversion (2-3 sessions)

### **Tier 2: Diversifiers**
- Phase 4: Pairs Trading (2-3 sessions)
- Phase 5: Volatility (2-3 sessions)
- Phase 6: Trend Following (2-3 sessions)

### **Tier 3: Tactical**
- Phase 7: Breakout (2-3 sessions)
- Phase 8: Factor (2-3 sessions)
- Phase 9: Multi-Asset (2-3 sessions)

### **Tier 4: Advanced**
- Phase 10: Arbitrage (2-3 sessions)

### **Portfolio & Deployment**
- Phase 11: Multi-Strategy Portfolio (3-4 sessions)
- Phase 12: Live Trading Prep (2-3 sessions)

---

## 🛠️ CODE TEMPLATES

### **Template: Run Baseline Backtest**
```python
from backtest.optimization.strategy_optimizer import StrategyOptimizer
from core_engine.type_definitions.strategy import StrategyType
import asyncio

async def run_baseline():
    optimizer = StrategyOptimizer()
    
    # Run baseline
    result = await optimizer.run_baseline_backtest(
        strategy_type=StrategyType.MOMENTUM,
        start_date="2022-01-01",
        end_date="2024-06-30",
        symbols=['NVDA', 'TSLA', 'AAPL']
    )
    
    # Print metrics
    print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
    print(f"Max Drawdown: {result.max_drawdown:.2%}")
    print(f"Win Rate: {result.win_rate:.2%}")
    print(f"Profit Factor: {result.profit_factor:.2f}")
    
    return result

if __name__ == "__main__":
    asyncio.run(run_baseline())
```

### **Template: Parameter Optimization**
```python
from backtest.optimization.strategy_optimizer import StrategyOptimizer
from core_engine.type_definitions.strategy import StrategyType
import asyncio

async def optimize_strategy():
    optimizer = StrategyOptimizer()
    
    # Define search space
    search_space = {
        'lookback_period': [10, 20, 30, 60, 90],
        'momentum_threshold': [0.01, 0.02, 0.03, 0.04, 0.05],
        'adx_threshold': [20, 25, 30, 35]
    }
    
    # Run optimization
    results = await optimizer.optimize_strategy(
        strategy_type=StrategyType.MOMENTUM,
        search_space=search_space,
        optimization_method='grid_search',  # or 'bayesian'
        optimization_metric='sharpe_ratio',
        start_date="2022-01-01",
        end_date="2024-03-31",  # Leave last 3 months for out-of-sample
        symbols=['NVDA', 'TSLA', 'AAPL']
    )
    
    # Print top 5 results
    for i, result in enumerate(results.top_results[:5], 1):
        print(f"\nRank {i}:")
        print(f"  Parameters: {result.parameters}")
        print(f"  Sharpe: {result.sharpe_ratio:.2f}")
        print(f"  Max DD: {result.max_drawdown:.2%}")
        print(f"  Win Rate: {result.win_rate:.2%}")
        print(f"  Profit Factor: {result.profit_factor:.2f}")
    
    return results

if __name__ == "__main__":
    asyncio.run(optimize_strategy())
```

### **Template: Regime Analysis**
```python
from backtest.optimization.regime_analyzer import RegimeAnalyzer
import asyncio

async def analyze_regimes():
    analyzer = RegimeAnalyzer()
    
    # Analyze regime performance
    regime_analysis = await analyzer.analyze_regime_performance(
        backtest_result=optimized_result,
        regime_types=['bull_low_vol', 'bear_high_vol', 'sideways', 
                     'trending', 'crisis']
    )
    
    # Print regime-specific metrics
    for regime, metrics in regime_analysis.regime_metrics.items():
        print(f"\n{regime.upper()}:")
        print(f"  Sharpe: {metrics.sharpe_ratio:.2f}")
        print(f"  Win Rate: {metrics.win_rate:.2%}")
        print(f"  Avg Return: {metrics.avg_return:.2%}")
    
    return regime_analysis

if __name__ == "__main__":
    asyncio.run(analyze_regimes())
```

---

## 📈 QUICK METRICS REFERENCE

### **Performance Metrics**
```python
# Sharpe Ratio = (Return - RiskFreeRate) / Volatility
# Target: > 1.5 (excellent: > 2.0)

# Sortino Ratio = (Return - RiskFreeRate) / Downside Deviation
# Target: > 2.0

# Calmar Ratio = Annual Return / Max Drawdown
# Target: > 1.0

# Profit Factor = Gross Profit / Gross Loss
# Target: > 1.5 (excellent: > 2.0)
```

### **Risk Metrics**
```python
# Maximum Drawdown = (Peak - Trough) / Peak
# Target: < 15% (excellent: < 10%)

# Win Rate = Winning Trades / Total Trades
# Target: > 55% (excellent: > 60%)

# Average Win/Loss Ratio = Avg Win / Avg Loss
# Target: > 1.5
```

---

## 🎯 7-STEP ESCORT PROCESS

### **Step 1: Baseline** 📏
- Run with default parameters
- Document all metrics
- Identify weaknesses

### **Step 2: Search** 🔍
- Define search space
- Run optimization
- Select top parameters

### **Step 3: Regime** 🌍
- Test in each regime
- Optimize regime-specific params
- Validate regime detection

### **Step 4: Costs** 💰
- Apply transaction costs
- Validate net positive
- Optimize trade frequency

### **Step 5: Stats** 📈
- Run significance tests
- Validate sample size
- Check overfitting

### **Step 6: Integration** 🔗
- Test in multi-strategy
- Validate risk manager
- Test execution quality

### **Step 7: Docs** 📚
- Document parameters
- Record metrics
- Write playbook

---

## 📁 FILE LOCATIONS

### **Optimization Code**
- `backtest/optimization/strategy_optimizer.py` - Main optimizer
- `backtest/optimization/parameter_search.py` - Search algorithms
- `backtest/optimization/performance_comparator.py` - Comparison
- `backtest/optimization/regime_analyzer.py` - Regime analysis

### **Configuration**
- `backtest/config/optimization/` - Optimization configs
- `backtest/config/strategy_params/` - Optimized parameters

### **Tests**
- `tests/optimization/test_phase*.py` - Phase tests
- `tests/optimization/test_strategy_optimizer.py` - Optimizer tests

### **Documentation**
- `docs/optimization/PHASE*_COMPLETE.md` - Phase completion docs
- `docs/optimization/baseline_performance.md` - Baseline metrics
- `docs/optimization/optimization_results.md` - Results summary

---

## 🚨 COMMON PITFALLS TO AVOID

1. **Overfitting**: Always use train/test split (e.g., 2022-2024 train, last 3 months test)
2. **Look-ahead Bias**: Ensure no future data in parameter selection
3. **Survivorship Bias**: Include delisted/failed trades
4. **Transaction Costs**: Always apply realistic costs
5. **Sample Size**: Ensure > 100 trades for statistical significance
6. **Regime Bias**: Test across all market regimes
7. **Curve Fitting**: Avoid too many parameters (< 5 per strategy)

---

## 💡 OPTIMIZATION TIPS

1. **Start Simple**: Begin with fewer parameters, add complexity gradually
2. **Focus on Sharpe**: Sharpe ratio is primary metric (risk-adjusted)
3. **Watch Drawdown**: Max DD is critical for live trading survival
4. **Test Regimes**: Performance must be positive in multiple regimes
5. **Validate Costs**: Net returns after costs are what matter
6. **Check Correlation**: Low correlation between strategies = better diversification
7. **Document Everything**: Save all configurations and results

---

## 📊 PROGRESS TRACKER

### **Infrastructure** (Phase 0)
- [ ] StrategyOptimizer implemented
- [ ] ParameterSearchEngine implemented
- [ ] PerformanceComparator implemented
- [ ] RegimeAnalyzer implemented
- [ ] Baseline backtests complete (0/10)
- [ ] Phase 0 documentation complete

### **Tier 1: Core Alpha** (Phases 1-3)
- [ ] Statistical Arbitrage optimized
- [ ] Momentum optimized
- [ ] Mean Reversion optimized

### **Tier 2: Diversifiers** (Phases 4-6)
- [ ] Pairs Trading optimized
- [ ] Volatility optimized
- [ ] Trend Following optimized

### **Tier 3: Tactical** (Phases 7-9)
- [ ] Breakout optimized
- [ ] Factor optimized
- [ ] Multi-Asset optimized

### **Tier 4: Advanced** (Phase 10)
- [ ] Arbitrage optimized

### **Portfolio** (Phases 11-12)
- [ ] Multi-strategy portfolio optimized
- [ ] Live trading preparation complete

---

## 🎯 NEXT SESSION GOALS

### **Phase 0 Session 1**
1. Create `backtest/optimization/` directory structure
2. Implement `StrategyOptimizer` class (300+ lines)
3. Implement `ParameterSearchEngine` class (200+ lines)
4. Implement `PerformanceComparator` class (150+ lines)
5. Run baseline backtest for Statistical Arbitrage strategy
6. Document baseline metrics
7. Write tests for infrastructure
8. Generate Phase 0 completion document

**Expected Duration**: 1-2 hours  
**Success Criteria**: Infrastructure operational, 1 baseline complete

---

## 📚 REFERENCE LINKS

- **Main Workflow**: `.cursor/rules/strategy-optimization-workflow.mdc`
- **Detailed Plan**: `docs/STRATEGY_OPTIMIZATION_PLAN.md`
- **Session Context**: `docs/SESSION_CONTEXT_HANDOFF.md`
- **Backtest Guide**: `docs/USER_GUIDE.md`

---

**Quick Start Ready!** 🚀

Use this guide as your quick reference during each optimization session. Update progress tracker after each phase completion.

**Let's create those silver bullets!** 🎯

