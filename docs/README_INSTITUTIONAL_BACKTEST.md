# Institutional-Grade Backtest Engine

## Overview

The **InstitutionalBacktestEngine** is an enhanced backtesting framework that implements the complete 13-phase institutional workflow as defined in the StatArb_Gemini architecture documentation. This engine provides professional-grade backtesting capabilities with system orchestration, risk management integration, and comprehensive performance attribution.

## Key Features

### 🏗️ **13-Phase Institutional Workflow**
- **Phase 1**: System Initialization & Configuration
- **Phase 2**: Data Loading & Market Preparation  
- **Phase 3**: Regime Analysis & Market Context
- **Phase 4**: Strategy Signal Generation
- **Phase 5**: Risk Assessment & Pre-Trade Analysis
- **Phase 6**: Execution Planning & Order Preparation
- **Phase 7**: Simulated Trade Execution
- **Phase 8**: Real-Time Position Monitoring
- **Phase 9**: Position Exit Management
- **Phase 10**: Trade Settlement & Accounting
- **Phase 11**: Performance Analysis & Attribution
- **Phase 12**: Backtest Continuation & Learning
- **Phase 13**: Backtest Completion & Final Reporting

### 🎯 **Architecture Compliance**
- **SystemOrchestrator Integration**: Full component registration and lifecycle management
- **CentralRiskManager Authorization**: All trading decisions flow through risk management
- **Hierarchical Control**: Proper authority levels and governance boundaries
- **Data Flow Compliance**: Uses established data pipeline patterns

### 🧠 **Advanced Analytics**
- **Regime-Aware Backtesting**: Dynamic parameter adjustment based on market conditions
- **Multi-Strategy Support**: Portfolio-level backtesting with strategy attribution
- **Performance Attribution**: Regime, factor, and risk-based performance breakdown
- **Transaction Cost Analysis**: Comprehensive cost modeling and impact analysis

### 🔬 **Validation Framework**
- **Walk-Forward Analysis**: Out-of-sample testing with rolling windows
- **Monte Carlo Simulation**: Statistical validation with confidence intervals
- **Benchmark Comparison**: Alpha, beta, and information ratio analysis
- **Overfitting Detection**: Robust validation methodologies

## Quick Start

### Basic Usage

```python
import asyncio
from datetime import datetime
from core_engine.trading.strategies import (
    InstitutionalBacktestEngine, InstitutionalBacktestConfig,
    AdvancedMomentumStrategy, MomentumConfig
)

async def run_backtest():
    # Configure institutional backtest
    config = InstitutionalBacktestConfig(
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 12, 31),
        initial_capital=1000000.0,
        enable_system_orchestration=True,
        enable_risk_authorization=True,
        enable_regime_awareness=True
    )
    
    # Create strategy
    momentum_config = MomentumConfig(
        strategy_id="institutional_momentum",
        lookback_periods=[1, 3, 6],
        signal_threshold=0.1
    )
    strategy = AdvancedMomentumStrategy(momentum_config)
    
    # Create and run backtest
    engine = InstitutionalBacktestEngine(config)
    result = await engine.run_institutional_backtest(
        strategy=strategy,
        market_data=market_data,
        benchmark_data=benchmark_data
    )
    
    # Display results
    print(f"Total Return: {result.total_return:.2%}")
    print(f"Sharpe Ratio: {result.sharpe_ratio:.3f}")
    print(f"Max Drawdown: {result.max_drawdown:.2%}")

# Run the backtest
asyncio.run(run_backtest())
```

### Multi-Strategy Backtesting

```python
# Create multiple strategies
strategies = {
    "momentum_short": AdvancedMomentumStrategy(short_term_config),
    "momentum_long": AdvancedMomentumStrategy(long_term_config),
    "mean_reversion": AdvancedMeanReversionStrategy(mr_config)
}

# Configure for multi-strategy
config = InstitutionalBacktestConfig(
    enable_multi_strategy=True,
    strategy_allocation={"momentum_short": 0.4, "momentum_long": 0.3, "mean_reversion": 0.3}
)

# Run multi-strategy backtest
result = await engine.run_institutional_backtest(
    strategy=strategies,
    market_data=market_data
)

# Analyze strategy performance
for strategy_name, performance in result.strategy_performance.items():
    print(f"{strategy_name}: {performance['total_pnl']:.2f}")
```

## Configuration Options

### InstitutionalBacktestConfig

```python
config = InstitutionalBacktestConfig(
    # Basic settings
    start_date=datetime(2023, 1, 1),
    end_date=datetime(2023, 12, 31),
    initial_capital=1000000.0,
    benchmark_symbol="SPY",
    
    # System integration
    enable_system_orchestration=True,    # Use SystemOrchestrator
    enable_risk_authorization=True,      # Use CentralRiskManager
    enable_regime_awareness=True,        # Use UnifiedRegimeEngine
    
    # Multi-strategy settings
    enable_multi_strategy=False,
    strategy_allocation={},
    rebalance_strategies=True,
    
    # Transaction costs
    commission_rate=0.001,               # 0.1% commission
    slippage_rate=0.0005,               # 0.05% slippage
    
    # Advanced analytics
    enable_regime_attribution=True,
    enable_factor_attribution=True,
    enable_risk_attribution=True,
    enable_transaction_cost_analysis=True,
    
    # Validation
    enable_walk_forward=False,
    walk_forward_periods=12,
    enable_monte_carlo=False,
    monte_carlo_runs=1000,
    
    # Output
    generate_institutional_report=True,
    save_detailed_logs=True,
    output_directory="institutional_backtest_results"
)
```

## Results and Analytics

### InstitutionalBacktestResult

The enhanced result object provides comprehensive analytics:

```python
# Basic performance metrics
result.total_return              # Total return
result.annualized_return         # Annualized return
result.sharpe_ratio             # Sharpe ratio
result.max_drawdown             # Maximum drawdown
result.volatility               # Volatility

# Trading statistics
result.total_trades             # Number of trades
result.win_rate                 # Win rate
result.profit_factor            # Profit factor

# Phase execution results
result.phase_results            # Detailed phase execution data
result.system_utilization       # System performance metrics

# Regime performance (if enabled)
result.regime_performance       # Performance by market regime
result.regime_transitions       # Regime transition analysis

# Multi-strategy results (if applicable)
result.strategy_performance     # Individual strategy performance
result.strategy_correlations    # Strategy correlation matrix

# Advanced analytics
result.factor_attribution       # Factor-based attribution
result.risk_attribution         # Risk-based attribution
result.transaction_cost_breakdown # Cost analysis

# Validation results
result.walk_forward_results     # Walk-forward analysis
result.monte_carlo_stats        # Monte Carlo statistics
```

### Phase Execution Tracking

```python
# Get phase execution summary
phase_summary = engine.get_phase_summary()
print(f"Successful phases: {phase_summary['successful_phases']}/{phase_summary['total_phases']}")

# Detailed phase results
for phase, phase_result in result.phase_results.items():
    print(f"{phase.value}: {phase_result.success} ({phase_result.execution_time:.3f}s)")
    
    # Phase metrics
    for metric, value in phase_result.metrics.items():
        print(f"  {metric}: {value}")
```

## Advanced Features

### Regime-Aware Backtesting

The engine automatically adjusts strategy parameters based on market regime:

```python
# Regime adjustments are automatic when enabled
config = InstitutionalBacktestConfig(
    enable_regime_awareness=True,
    regime_adjustment_enabled=True,
    regime_transition_handling="gradual"  # gradual, immediate, none
)

# View regime performance
for regime, performance in result.regime_performance.items():
    print(f"{regime}: {performance['total_return']:.2%} return")
```

### Walk-Forward Analysis

```python
# Enable walk-forward validation
config = InstitutionalBacktestConfig(
    enable_walk_forward=True,
    walk_forward_periods=12,  # 12-month periods
    training_period=252,      # Training days
    testing_period=63         # Testing days
)

# Run walk-forward analysis
wf_results = await engine.run_walk_forward_analysis(
    strategy_class=AdvancedMomentumStrategy,
    base_config=momentum_config,
    market_data=market_data
)

# Analyze out-of-sample performance
for i, wf_result in enumerate(wf_results):
    print(f"Period {i+1}: {wf_result.total_return:.2%}")
```

### Monte Carlo Simulation

```python
# Enable Monte Carlo validation
config = InstitutionalBacktestConfig(
    enable_monte_carlo=True,
    monte_carlo_runs=1000
)

# Run Monte Carlo simulation
mc_stats = await engine.run_monte_carlo_simulation(
    strategy=strategy,
    market_data=market_data
)

# Analyze statistical properties
print(f"Mean return: {mc_stats['mean_return']:.2%}")
print(f"95% VaR: {mc_stats['var_95']:.2%}")
print(f"Probability of positive returns: {mc_stats['probability_positive']:.1%}")
```

## Export and Reporting

### Comprehensive Results Export

```python
# Export institutional results
exported_files = await engine.export_institutional_results(result)

# Files exported:
# - main_results.json: Core performance metrics
# - phase_summary.json: Phase execution details
# - trades.csv: Complete trade log
# - portfolio.csv: Portfolio history
```

### Custom Reporting

```python
# Generate custom reports
if result.regime_performance:
    print("=== Regime Performance Analysis ===")
    for regime, perf in result.regime_performance.items():
        print(f"{regime}:")
        print(f"  Total Return: {perf['total_return']:.2%}")
        print(f"  Sharpe Ratio: {perf['sharpe_ratio']:.3f}")
        print(f"  Periods: {perf['periods']}")

if result.strategy_performance:
    print("=== Strategy Performance Breakdown ===")
    for strategy, perf in result.strategy_performance.items():
        print(f"{strategy}: ${perf['total_pnl']:,.2f} P&L")
```

## Testing and Validation

### Running Tests

```python
# Run the test suite
python core_engine/trading/strategies/test_institutional_backtest.py

# Run the demonstration
python examples/institutional_backtest_demo.py
```

### Test Coverage

The test suite includes:
- Single strategy backtesting
- Multi-strategy backtesting  
- Phase execution validation
- System integration testing
- Performance analytics validation

## Architecture Integration

### Component Registration

The engine automatically registers with the SystemOrchestrator:

```python
# Automatic registration when system orchestration is enabled
config = InstitutionalBacktestConfig(enable_system_orchestration=True)
engine = InstitutionalBacktestEngine(config)

# Component is registered with proper authority levels
# - Layer: EXECUTION
# - Authority: OPERATIONAL
# - Initialization Order: 10
```

### Risk Management Integration

All trading decisions flow through the CentralRiskManager:

```python
# Risk authorization is automatic when enabled
config = InstitutionalBacktestConfig(enable_risk_authorization=True)

# Each signal goes through risk assessment:
# 1. Create TradingDecisionRequest
# 2. Request authorization from CentralRiskManager
# 3. Execute only if authorized
# 4. Respect position limits and risk budgets
```

### Data Flow Compliance

The engine follows established data flow patterns:

```python
# Data flows through proper channels:
# Market Data → ClickHouseDataManager → Processing Pipeline → Strategies
# Signals → CentralRiskManager → UnifiedExecutionEngine → Portfolio
```

## Performance Considerations

### Optimization Tips

1. **Enable Caching**: Use data caching for repeated backtests
2. **Parallel Processing**: Multi-strategy backtests run strategies in parallel
3. **Memory Management**: Large datasets are processed in chunks
4. **Phase Optimization**: Each phase is optimized for performance

### Scalability

- **Large Datasets**: Handles multi-year, multi-symbol datasets efficiently
- **Multiple Strategies**: Supports portfolio-level multi-strategy backtesting
- **Complex Analytics**: Advanced attribution and validation with minimal overhead

## Troubleshooting

### Common Issues

1. **Initialization Failures**: Check component dependencies and configurations
2. **Risk Authorization Rejections**: Review risk limits and position sizing
3. **Data Quality Issues**: Validate market data completeness and format
4. **Phase Execution Errors**: Check phase results for detailed error messages

### Debug Mode

```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check phase execution details
for phase, result in backtest_result.phase_results.items():
    if not result.success:
        print(f"Phase {phase.value} failed:")
        for error in result.errors:
            print(f"  - {error}")
```

## Contributing

When extending the institutional backtest engine:

1. **Follow Architecture Patterns**: Maintain compliance with SystemOrchestrator
2. **Add Phase Tracking**: New features should integrate with phase execution
3. **Include Tests**: Add comprehensive test coverage
4. **Document Changes**: Update this README and code documentation

## License

This institutional backtest engine is part of the StatArb_Gemini project and follows the same licensing terms.
