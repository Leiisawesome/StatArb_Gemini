# Phase 3: Statistical Arbitrage Optimization - Action Plan

## Executive Summary

**Goal:** Transform Statistical Arbitrage strategy from Grade F (0.00 Sharpe) to Grade A+ (2.0+ Sharpe)

**Current Status:** Strategy has excellent implementation but uses generic config (missing strategy-specific parameters)

**Target Performance:**
- Sharpe Ratio: 0.00 → 2.0+
- Annual Return: 0% → 30-50%
- Max Drawdown: 0% → <10%
- Win Rate: 0% → 60-70%

---

## Current Implementation Analysis

### ✅ What's Already Implemented (Excellent!)

The `EnhancedStatisticalArbitrageStrategy` already has:

**1. Comprehensive Configuration (`StatisticalArbitrageConfig`):**
```python
- cointegration_lookback: 252 days
- entry_zscore_threshold: 2.0
- exit_zscore_threshold: 0.5
- stop_loss_zscore: 3.5
- kalman_filter_enabled: True
- ou_process_modeling: True
- error_correction_model: True
- asset_universe: 8 tech stocks
```

**2. Advanced Statistical Models:**
- ✅ Cointegration analysis (Engle-Granger, Johansen)
- ✅ Kalman filters for dynamic hedge ratios
- ✅ Ornstein-Uhlenbeck process modeling
- ✅ Error Correction Model (ECM)
- ✅ Statistical significance testing

**3. Professional Risk Management:**
- ✅ Risk parity position sizing
- ✅ Stop loss mechanisms
- ✅ Maximum holding period
- ✅ Correlation decay monitoring

**4. Comprehensive Tracking:**
- ✅ Spread metrics (SpreadMetrics dataclass)
- ✅ Performance monitoring
- ✅ Trade history
- ✅ Daily P&L tracking

### ❌ What's Missing (The Problem)

**Issue:** Strategy tester uses generic `StrategyConfig` instead of `StatisticalArbitrageConfig`

**Result:** Strategy can't generate trades because it validates for stat arb parameters:
```python
# Validation in enhanced_statistical_arbitrage.py line 319:
if self.config.entry_zscore_threshold <= self.config.exit_zscore_threshold:
    return False  # ← Fails because generic config missing these attributes!
```

**Impact:** Grade F with 0 trades despite having all the code ready!

---

## Phase 3 Tasks Breakdown

### 📋 Task 3.1: Analyze Current Implementation (15 min) ✅

**Status:** COMPLETE (this document)

**Findings:**
- Strategy code is production-ready
- Just needs proper configuration integration
- All advanced features already implemented

---

### 🔧 Task 3.2: Implement Strategy Config Factory (1-2 hours)

**Goal:** Enable strategy tester to use strategy-specific configs

**Deliverables:**

**1. Create Config Factory (`tests/strategy_assessment/strategy_config_factory.py`):**
```python
class StrategyConfigFactory:
    """Factory for creating strategy-specific configurations"""
    
    @staticmethod
    def create_statistical_arbitrage_config(
        symbols: List[str],
        **kwargs
    ) -> StatisticalArbitrageConfig:
        """Create optimized StatArb config"""
        
        return StatisticalArbitrageConfig(
            strategy_id="statistical_arbitrage_v1",
            strategy_type=StrategyType.STATISTICAL_ARBITRAGE,
            
            # Asset universe (from test symbols)
            asset_universe=symbols,
            
            # Cointegration parameters
            cointegration_lookback=252,
            min_cointegration_pvalue=0.05,
            min_correlation=0.70,
            
            # Spread trading (will be optimized in 3.4)
            entry_zscore_threshold=2.0,
            exit_zscore_threshold=0.5,
            stop_loss_zscore=3.5,
            
            # Position sizing
            max_spread_positions=5,
            base_position_size=0.02,
            position_size_method="risk_parity",
            
            # Models
            kalman_filter_enabled=True,
            ou_process_modeling=True,
            error_correction_model=True,
            
            # Override from kwargs
            **kwargs
        )
```

**2. Modify Strategy Tester (`tests/strategy_assessment/strategy_tester.py`):**
```python
# Replace generic config with strategy-specific configs
async def _load_strategy_implementation(self, config: StrategyTestConfig):
    # ...
    
    # Create strategy-specific config
    strategy_config = StrategyConfigFactory.create_config(
        strategy_type=config.strategy_name,
        symbols=config.symbols,
        **config.strategy_config
    )
    
    # Instantiate with proper config
    strategy = strategy_class(strategy_config)
```

**Success Criteria:**
- [ ] Config factory creates all 10 strategy configs
- [ ] Strategy tester uses strategy-specific configs
- [ ] StatArb strategy passes validation
- [ ] StatArb strategy generates signals

**ETA:** 1-2 hours

---

### 🔬 Task 3.3: Implement Pairs Selection Framework (2-3 hours)

**Goal:** Automated pairs selection with cointegration testing

**Current:** Asset universe is hardcoded in config

**Target:** Dynamic pairs selection based on statistical tests

**Deliverables:**

**1. Pairs Selection Module (`tests/strategy_assessment/pairs_selection.py`):**
```python
class PairsSelector:
    """Automated pairs selection for statistical arbitrage"""
    
    def select_cointegrated_pairs(
        self,
        price_data: Dict[str, pd.DataFrame],
        min_correlation: float = 0.7,
        min_cointegration_pvalue: float = 0.05,
        lookback_period: int = 252
    ) -> List[Tuple[str, str, Dict[str, Any]]]:
        """
        Select cointegrated pairs from asset universe
        
        Returns:
            List of (asset1, asset2, {metrics}) tuples
        """
        
        pairs = []
        symbols = list(price_data.keys())
        
        for i, sym1 in enumerate(symbols):
            for sym2 in symbols[i+1:]:
                # 1. Check correlation
                corr = self._calculate_correlation(
                    price_data[sym1], 
                    price_data[sym2],
                    lookback_period
                )
                
                if abs(corr) < min_correlation:
                    continue
                
                # 2. Test cointegration
                pvalue, hedge_ratio = self._test_cointegration(
                    price_data[sym1],
                    price_data[sym2]
                )
                
                if pvalue > min_cointegration_pvalue:
                    continue
                
                # 3. Calculate quality metrics
                metrics = {
                    'correlation': corr,
                    'cointegration_pvalue': pvalue,
                    'hedge_ratio': hedge_ratio,
                    'half_life': self._calculate_half_life(...),
                    'adf_statistic': self._adf_test(...),
                    'quality_score': self._calculate_quality(...)
                }
                
                pairs.append((sym1, sym2, metrics))
        
        # Sort by quality score
        pairs.sort(key=lambda x: x[2]['quality_score'], reverse=True)
        
        return pairs
```

**2. Integration with Strategy:**
```python
# Run pairs selection before backtesting
pairs_selector = PairsSelector()
selected_pairs = pairs_selector.select_cointegrated_pairs(
    price_data=market_data,
    min_correlation=0.7,
    min_cointegration_pvalue=0.05
)

logger.info(f"Selected {len(selected_pairs)} cointegrated pairs")
for pair in selected_pairs[:5]:  # Top 5
    logger.info(f"  {pair[0]}-{pair[1]}: "
               f"corr={pair[2]['correlation']:.3f}, "
               f"pvalue={pair[2]['cointegration_pvalue']:.4f}")
```

**Success Criteria:**
- [ ] Pairs selector identifies cointegrated pairs
- [ ] Quality scoring ranks best pairs
- [ ] Half-life and ADF statistics calculated
- [ ] Integration with strategy backtest

**ETA:** 2-3 hours

---

### ⚡ Task 3.4: Optimize Z-Score Parameters (3-4 hours)

**Goal:** Find optimal entry/exit thresholds via grid search

**Current:** Using default thresholds (entry=2.0, exit=0.5)

**Target:** Optimized thresholds maximizing Sharpe ratio

**Deliverables:**

**1. Parameter Optimizer (`tests/strategy_assessment/parameter_optimizer.py`):**
```python
class ParameterOptimizer:
    """Grid search parameter optimization"""
    
    def optimize_zscore_thresholds(
        self,
        strategy: EnhancedStatisticalArbitrageStrategy,
        market_data: Dict[str, pd.DataFrame],
        param_grid: Dict[str, List[float]]
    ) -> Dict[str, Any]:
        """
        Optimize z-score entry/exit thresholds
        
        Args:
            param_grid: {
                'entry_zscore': [1.5, 2.0, 2.5, 3.0],
                'exit_zscore': [0.3, 0.5, 0.7, 1.0],
                'stop_loss_zscore': [3.0, 3.5, 4.0]
            }
        
        Returns:
            Best parameters and performance metrics
        """
        
        results = []
        
        for entry in param_grid['entry_zscore']:
            for exit in param_grid['exit_zscore']:
                for stop in param_grid['stop_loss_zscore']:
                    # Skip invalid combinations
                    if not (exit < entry < stop):
                        continue
                    
                    # Create config with these parameters
                    config = strategy.config.copy()
                    config.entry_zscore_threshold = entry
                    config.exit_zscore_threshold = exit
                    config.stop_loss_zscore = stop
                    
                    # Run backtest
                    backtest_result = self.run_backtest(
                        strategy, market_data, config
                    )
                    
                    results.append({
                        'entry_zscore': entry,
                        'exit_zscore': exit,
                        'stop_loss_zscore': stop,
                        'sharpe_ratio': backtest_result.sharpe_ratio,
                        'annual_return': backtest_result.annual_return,
                        'max_drawdown': backtest_result.max_drawdown,
                        'win_rate': backtest_result.win_rate,
                        'total_trades': backtest_result.total_trades
                    })
        
        # Find best parameters (maximize Sharpe)
        best = max(results, key=lambda x: x['sharpe_ratio'])
        
        return {
            'best_parameters': best,
            'all_results': results,
            'optimization_summary': self._create_summary(results)
        }
```

**2. Optimization Grids:**
```python
# Coarse grid (initial search)
coarse_grid = {
    'entry_zscore': [1.5, 2.0, 2.5, 3.0],
    'exit_zscore': [0.3, 0.5, 0.7, 1.0],
    'stop_loss_zscore': [3.0, 3.5, 4.0, 4.5]
}

# Fine grid (refinement around best)
fine_grid = {
    'entry_zscore': np.linspace(1.8, 2.2, 9),
    'exit_zscore': np.linspace(0.4, 0.6, 5),
    'stop_loss_zscore': np.linspace(3.3, 3.7, 5)
}
```

**Success Criteria:**
- [ ] Grid search completes for all combinations
- [ ] Best parameters identified (maximize Sharpe)
- [ ] Performance comparison vs defaults
- [ ] Visualization of parameter sensitivity

**ETA:** 3-4 hours

---

### 🎛️ Task 3.5: Kalman Filter Optimization (2-3 hours)

**Goal:** Optimize Kalman filter parameters for hedge ratio estimation

**Current:** Kalman filter implemented but with default parameters

**Target:** Optimized noise parameters for better hedge ratio tracking

**Deliverables:**

**1. Kalman Filter Tuning:**
```python
def optimize_kalman_parameters(
    self,
    price_data: Dict[str, pd.DataFrame],
    param_grid: Dict[str, List[float]]
) -> Dict[str, float]:
    """
    Optimize Kalman filter noise parameters
    
    Args:
        param_grid: {
            'process_noise': [1e-5, 1e-4, 1e-3],
            'measurement_noise': [1e-2, 1e-1, 1.0]
        }
    """
    
    best_params = None
    best_score = -np.inf
    
    for process in param_grid['process_noise']:
        for measurement in param_grid['measurement_noise']:
            # Test hedge ratio tracking quality
            score = self._evaluate_hedge_ratio_quality(
                price_data, process, measurement
            )
            
            if score > best_score:
                best_score = score
                best_params = {
                    'process_noise': process,
                    'measurement_noise': measurement
                }
    
    return best_params
```

**Success Criteria:**
- [ ] Kalman parameters optimized for hedge ratio stability
- [ ] Hedge ratio tracking quality improved
- [ ] Reduced slippage from hedge ratio drift

**ETA:** 2-3 hours

---

### 📊 Task 3.6: ECM-Based Timing Optimization (2-3 hours)

**Goal:** Optimize Error Correction Model for better entry/exit timing

**Current:** ECM implemented but not optimized

**Target:** Optimized ECM parameters for improved mean reversion timing

**Deliverables:**

**1. ECM Parameter Optimization:**
```python
def optimize_ecm_parameters(
    self,
    spread_data: pd.Series,
    param_grid: Dict[str, List[int]]
) -> Dict[str, Any]:
    """
    Optimize ECM lag order and other parameters
    
    Args:
        param_grid: {
            'lag_order': [1, 2, 3, 4, 5],
            'deterministic': ['nc', 'co', 'ci']
        }
    """
    
    best_params = None
    best_aic = np.inf
    
    for lag in param_grid['lag_order']:
        for det in param_grid['deterministic']:
            try:
                model = VECM(spread_data, k_ar_diff=lag, deterministic=det)
                results = model.fit()
                
                if results.aic < best_aic:
                    best_aic = results.aic
                    best_params = {
                        'lag_order': lag,
                        'deterministic': det,
                        'aic': results.aic,
                        'bic': results.bic,
                        'speed_of_adjustment': results.alpha
                    }
            except:
                continue
    
    return best_params
```

**Success Criteria:**
- [ ] ECM parameters optimized (minimize AIC)
- [ ] Speed of adjustment calculated
- [ ] Better timing for entries/exits

**ETA:** 2-3 hours

---

### 🚀 Task 3.7: Comprehensive Parameter Optimization (4-6 hours)

**Goal:** Optimize ALL parameters jointly

**Approach:** Two-stage optimization

**Stage 1: Individual Parameter Optimization**
- Z-scores (Task 3.4)
- Kalman filter (Task 3.5)  
- ECM parameters (Task 3.6)
- Position sizing
- Holding periods

**Stage 2: Joint Optimization**
```python
def joint_optimization(
    self,
    market_data: Dict[str, pd.DataFrame],
    param_space: Dict[str, Tuple[float, float]]
) -> Dict[str, Any]:
    """
    Joint optimization using Bayesian optimization
    
    Args:
        param_space: {
            'entry_zscore': (1.5, 3.0),
            'exit_zscore': (0.3, 1.0),
            'cointegration_lookback': (100, 500),
            'min_correlation': (0.6, 0.9),
            # ... more parameters
        }
    """
    
    from skopt import gp_minimize
    
    def objective(params):
        # Create config from parameters
        config = self._create_config_from_params(params)
        
        # Run backtest
        result = self.run_backtest(market_data, config)
        
        # Return negative Sharpe (minimize)
        return -result.sharpe_ratio
    
    # Bayesian optimization
    result = gp_minimize(
        objective,
        dimensions=param_space.values(),
        n_calls=100,
        random_state=42
    )
    
    return {
        'best_parameters': result.x,
        'best_sharpe': -result.fun,
        'optimization_history': result.func_vals
    }
```

**Success Criteria:**
- [ ] All parameters optimized jointly
- [ ] Sharpe ratio maximized
- [ ] Robustness validated via walk-forward
- [ ] Parameter stability confirmed

**ETA:** 4-6 hours

---

### 🧪 Task 3.8: Comprehensive Backtesting & Validation (3-4 hours)

**Goal:** Validate optimized strategy on full historical data

**Test Suite:**

**1. Full Year Backtest (2024):**
```python
# Test optimized strategy on 2024 data
result = backtest_optimized_strategy(
    symbols=['NVDA', 'TSLA', 'AAPL', 'MSFT', 'GOOGL'],
    start_date='2024-01-01',
    end_date='2024-12-31',
    optimized_config=best_config
)
```

**2. Walk-Forward Analysis:**
```python
# Test parameter stability over time
walk_forward_results = run_walk_forward_analysis(
    n_splits=6,  # 6 periods (2 months each)
    train_window=60,  # 60 days training
    test_window=30    # 30 days testing
)
```

**3. Regime-Specific Performance:**
```python
# Analyze performance by market regime
regime_performance = analyze_regime_performance(
    regimes=['bull', 'bear', 'high_vol', 'low_vol', 'sideways']
)
```

**4. Monte Carlo Stress Testing:**
```python
# Test robustness via Monte Carlo
monte_carlo_results = run_monte_carlo_test(
    n_simulations=1000,
    confidence_level=0.95
)
```

**Success Criteria:**
- [ ] Sharpe Ratio: >2.0
- [ ] Annual Return: >30%
- [ ] Max Drawdown: <10%
- [ ] Win Rate: >60%
- [ ] Positive returns in all regimes
- [ ] Parameter stability confirmed
- [ ] 95% confidence in profitability

**ETA:** 3-4 hours

---

## Timeline & Milestones

### Week 1: Configuration & Pairs Selection
- **Days 1-2:** Tasks 3.1-3.2 (Config factory)
- **Days 3-4:** Task 3.3 (Pairs selection)
- **Day 5:** Integration testing

### Week 2: Parameter Optimization  
- **Days 1-2:** Task 3.4 (Z-score optimization)
- **Day 3:** Task 3.5 (Kalman filter)
- **Day 4:** Task 3.6 (ECM optimization)
- **Day 5:** Task 3.7 (Joint optimization)

### Week 3: Validation & Documentation
- **Days 1-2:** Task 3.8 (Comprehensive backtesting)
- **Day 3:** Performance analysis & documentation
- **Days 4-5:** Buffer for refinements

**Total ETA:** 2-3 weeks

---

## Expected Performance Improvements

### Current (Phase 2 Baseline)
```
Grade:              F
Sharpe Ratio:       0.00
Annual Return:      0.00%
Max Drawdown:       0.00%
Win Rate:           0.00%
Total Trades:       0
```

### Target (Phase 3 Optimized)
```
Grade:              A+
Sharpe Ratio:       2.0-2.5
Annual Return:      30-50%
Max Drawdown:       5-10%
Win Rate:           60-70%
Total Trades:       50-100/year
Profit Factor:      2.0-3.0
```

### Key Improvements Expected:

**1. Signal Generation:** 0 → 50-100 trades/year
- Proper configuration enables trading
- Cointegrated pairs identified
- Entry/exit signals generated

**2. Risk-Adjusted Returns:** 0.00 → 2.0+ Sharpe
- Optimized z-score thresholds
- Better entry/exit timing (ECM)
- Dynamic hedge ratios (Kalman)

**3. Win Rate:** 0% → 60-70%
- Mean reversion validated
- Stop losses protect downside
- Quality pairs selection

**4. Drawdown Control:** 0% → 5-10%
- Risk parity sizing
- Maximum holding periods
- Correlation monitoring

---

## Success Metrics

### Critical Success Factors:
1. ✅ Strategy generates trades (>0 signals)
2. ✅ Sharpe ratio >1.5 (institutional minimum)
3. ✅ Win rate >55% (mean reversion validated)
4. ✅ Max drawdown <15% (acceptable risk)
5. ✅ Positive in all market regimes

### Stretch Goals:
- 🎯 Sharpe ratio >2.0 (excellent)
- 🎯 Annual return >40% (outstanding)
- 🎯 Win rate >65% (exceptional)
- 🎯 Max drawdown <8% (superior risk control)

---

## Risk Mitigation

### Technical Risks:
1. **Overfitting** - Mitigated by walk-forward analysis
2. **Parameter Instability** - Monitored via regime analysis
3. **Data Quality** - Phase 2 validation ensures quality
4. **Computational Cost** - Grid search parallelized

### Strategy Risks:
1. **Correlation Breakdown** - Monitor correlation decay
2. **Regime Changes** - Regime-specific parameters
3. **Liquidity** - Position sizing considers slippage
4. **Transaction Costs** - Cost-aware optimization

---

## Next Immediate Step

**START WITH:** Task 3.2 - Implement Strategy Config Factory

**Why First:**
- Unblocks everything else
- Strategy immediately starts generating signals
- Can validate implementation works
- Quick win (1-2 hours)

**Command to proceed:**
```python
# Create config factory
# Modify strategy tester
# Run quick validation test
```

---

**Document Status:** 📋 READY FOR EXECUTION  
**Priority Level:** 🔥 HIGH  
**Blocking Issues:** None  
**Ready to Start:** ✅ YES

**Let's transform this strategy from 0 to hero! 🚀**
