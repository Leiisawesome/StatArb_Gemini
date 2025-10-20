# HistoricalExecutionSimulator Usage Guide

## Overview

The `HistoricalExecutionSimulator` is an institutional-grade execution simulator that provides realistic trade execution costs for backtesting. It implements **Rule 12 (Liquidity Management)** and **Rule 13 (Regime-First Principle)** to ensure execution costs accurately reflect market conditions.

## Key Features

### 🎯 **Realistic Execution Costs**
- **Bid-Ask Spread Costs**: Based on historical spreads
- **Market Impact**: Almgren-Chriss model for permanent/temporary impact
- **Slippage**: Volatility-adjusted random slippage
- **Commission**: Fixed per-share or percentage costs

### 🎯 **Regime-Aware Execution (Rule 13)**
- **Volatility Scaling**: Costs scale with market volatility regime
- **Regime Multipliers**: 
  - Low volatility: 0.8x (lower costs)
  - Normal volatility: 1.0x (base costs)
  - High volatility: 1.3x (higher costs)
  - Extreme volatility: 1.8x (much higher costs)
  - Crisis: 2.5x (extreme costs)

### 🎯 **Liquidity-Aware Execution (Rule 12)**
- **Liquidity Scoring**: 0-100 liquidity score affects costs
- **Liquidity Multipliers**:
  - High liquidity (80+): 0.8x (lower costs)
  - Normal liquidity (60-79): 1.0x (base costs)
  - Low liquidity (40-59): 1.3x (higher costs)
  - Illiquid (<40): 1.8x (much higher costs)
  - Crisis: 2.5x (extreme costs)

## Basic Usage

### 1. **Initialization**

```python
from backtest.engine.historical_execution_simulator import HistoricalExecutionSimulator

# Default configuration
simulator = HistoricalExecutionSimulator()

# Custom configuration
config = {
    'fill_model': 'realistic',
    'base_spread_bps': 10.0,           # 10 bps base spread
    'base_slippage_bps': 3.0,          # 3 bps base slippage
    'commission_per_share': 0.01,      # $0.01 per share
    'impact_linear_coeff': 0.15,       # Almgren-Chriss linear coefficient
    'impact_sqrt_coeff': 0.6,          # Almgren-Chriss sqrt coefficient
    'enable_random_slippage': True     # Enable random slippage
}
simulator = HistoricalExecutionSimulator(config)
```

### 2. **Basic Fill Simulation**

```python
# Sample market data
market_data = {
    'timestamp': datetime(2024, 12, 20, 10, 30, 0),
    'open': 100.0,
    'high': 101.0,
    'low': 99.5,
    'close': 100.5,
    'volume': 50000,
    'volatility': 0.02  # 2% volatility
}

# Simulate a BUY order
fill = simulator.simulate_fill(
    symbol='NVDA',
    side='buy',
    quantity=100,
    decision_price=100.0,
    market_data=market_data,
    authorization_id='auth_123',
    strategy_id='momentum_test'
)

print(f"Fill Price: ${fill.fill_price:.2f}")
print(f"Market Price: ${fill.market_price:.2f}")
print(f"Total Cost: {fill.costs.total_cost_bps:.2f} bps")
print(f"Cost ($): ${fill.costs.total_cost_dollars:.2f}")
```

### 3. **Regime-Aware Execution**

```python
# Normal volatility regime
regime_context_normal = {
    'primary_regime': 'bull_market',
    'volatility_regime': 'normal_volatility',
    'liquidity_regime': 'normal',
    'regime_confidence': 0.85
}

# High volatility regime
regime_context_high_vol = {
    'primary_regime': 'bear_market',
    'volatility_regime': 'high_volatility',
    'liquidity_regime': 'low',
    'regime_confidence': 0.90
}

# Fill in normal volatility
fill_normal = simulator.simulate_fill(
    symbol='NVDA',
    side='buy',
    quantity=100,
    decision_price=100.0,
    market_data=market_data,
    regime_context=regime_context_normal
)

# Fill in high volatility
fill_high_vol = simulator.simulate_fill(
    symbol='NVDA',
    side='buy',
    quantity=100,
    decision_price=100.0,
    market_data=market_data,
    regime_context=regime_context_high_vol
)

print(f"Normal Vol Cost: {fill_normal.costs.total_cost_bps:.2f} bps")
print(f"High Vol Cost: {fill_high_vol.costs.total_cost_bps:.2f} bps")
# High volatility should have higher costs (Rule 13)
```

### 4. **Liquidity-Aware Execution**

```python
# High liquidity fill
fill_high_liq = simulator.simulate_fill(
    symbol='NVDA',
    side='buy',
    quantity=100,
    decision_price=100.0,
    market_data=market_data,
    liquidity_score=85.0  # High liquidity
)

# Low liquidity fill
fill_low_liq = simulator.simulate_fill(
    symbol='NVDA',
    side='buy',
    quantity=100,
    decision_price=100.0,
    market_data=market_data,
    liquidity_score=35.0  # Low liquidity
)

print(f"High Liquidity Cost: {fill_high_liq.costs.total_cost_bps:.2f} bps")
print(f"Low Liquidity Cost: {fill_low_liq.costs.total_cost_bps:.2f} bps")
# Low liquidity should have higher costs (Rule 12)
```

## Advanced Usage

### 1. **Execution Quality Analysis**

```python
# Calculate execution quality score (0-100)
quality_score = simulator.calculate_execution_quality_score(fill)
print(f"Execution Quality: {quality_score:.1f}/100")

# Higher score = better execution (lower costs)
# 0 bps cost = 100 score, 50 bps cost = 0 score
```

### 2. **Aggregate Statistics**

```python
# Generate multiple fills
fills = []
for i in range(10):
    fill = simulator.simulate_fill(
        symbol='NVDA',
        side='buy' if i % 2 == 0 else 'sell',
        quantity=100 * (i + 1),
        decision_price=100.0,
        market_data=market_data
    )
    fills.append(fill)

# Calculate aggregate statistics
stats = simulator.get_statistics(fills)

print(f"Total Fills: {stats['total_fills']}")
print(f"Buy Fills: {stats['buy_fills']}")
print(f"Sell Fills: {stats['sell_fills']}")
print(f"Avg Total Cost: {stats['avg_total_cost_bps']:.2f} bps")
print(f"Total Cost ($): ${stats['total_cost_dollars']:.2f}")
print(f"Avg Quality Score: {stats['avg_execution_quality_score']:.1f}/100")
```

### 3. **Cost Component Analysis**

```python
fill = simulator.simulate_fill(
    symbol='NVDA',
    side='buy',
    quantity=1000,
    decision_price=100.0,
    market_data=market_data
)

costs = fill.costs

print(f"Cost Breakdown:")
print(f"  Spread Cost: {costs.spread_cost_bps:.2f} bps ({costs.spread_cost_bps/costs.total_cost_bps*100:.1f}%)")
print(f"  Market Impact: {costs.market_impact_bps:.2f} bps ({costs.market_impact_bps/costs.total_cost_bps*100:.1f}%)")
print(f"  Slippage: {costs.slippage_bps:.2f} bps ({costs.slippage_bps/costs.total_cost_bps*100:.1f}%)")
print(f"  Commission: {costs.commission_bps:.2f} bps ({costs.commission_bps/costs.total_cost_bps*100:.1f}%)")
print(f"  Total: {costs.total_cost_bps:.2f} bps")

print(f"\nImpact Breakdown:")
print(f"  Permanent Impact: {costs.permanent_impact_bps:.2f} bps")
print(f"  Temporary Impact: {costs.temporary_impact_bps:.2f} bps")
```

## Configuration Options

### **Fill Models**

```python
from backtest.engine.historical_execution_simulator import FillModel

# Available fill models:
# - MIDPOINT: Fill at mid price (no spread cost)
# - MIDPOINT_PLUS_HALF_SPREAD: Mid + half spread
# - WORST_CASE: Fill at ask (buy) or bid (sell)
# - REALISTIC: Spread + impact + slippage (recommended)
# - AGGRESSIVE: Minimal cost (optimistic)
```

### **Custom Regime Multipliers**

```python
config = {
    'regime_multipliers': {
        'low_volatility': 0.8,      # 20% lower costs
        'normal_volatility': 1.0,    # Base costs
        'high_volatility': 1.3,      # 30% higher costs
        'extreme_volatility': 1.8,   # 80% higher costs
        'crisis': 2.5                # 150% higher costs
    }
}
```

### **Custom Liquidity Multipliers**

```python
config = {
    'liquidity_multipliers': {
        'high': 0.8,      # 20% lower costs
        'normal': 1.0,     # Base costs
        'low': 1.3,        # 30% higher costs
        'illiquid': 1.8,   # 80% higher costs
        'crisis': 2.5      # 150% higher costs
    }
}
```

## Integration with Backtest Engine

### **Institutional Backtest Engine Integration**

```python
# The simulator is automatically integrated into the InstitutionalBacktestEngine
from backtest.engine.institutional_backtest_engine import InstitutionalBacktestEngine

# Execution simulation is handled automatically during backtesting
backtest_engine = InstitutionalBacktestEngine(config)
results = await backtest_engine.run_backtest(
    strategy_config=strategy_config,
    data_config=data_config,
    risk_config=risk_config,
    execution_config=execution_config  # Includes simulator settings
)
```

### **Execution Configuration**

```python
execution_config = {
    'simulator': {
        'fill_model': 'realistic',
        'base_spread_bps': 5.0,
        'base_slippage_bps': 2.0,
        'commission_per_share': 0.005,
        'enable_random_slippage': True
    }
}
```

## Performance Considerations

### **Deterministic vs Random Simulation**

```python
# For reproducible backtests (recommended)
config = {
    'enable_random_slippage': False  # Deterministic slippage
}

# For realistic simulation (production)
config = {
    'enable_random_slippage': True,   # Random slippage
    'slippage_std': 0.5               # Standard deviation in bps
}
```

### **Cost Model Selection**

```python
# Conservative (higher costs)
config = {
    'base_spread_bps': 10.0,
    'base_slippage_bps': 5.0,
    'impact_linear_coeff': 0.2,
    'impact_sqrt_coeff': 0.8
}

# Optimistic (lower costs)
config = {
    'base_spread_bps': 3.0,
    'base_slippage_bps': 1.0,
    'impact_linear_coeff': 0.1,
    'impact_sqrt_coeff': 0.4
}
```

## Best Practices

### 1. **Regime Context Integration**
- Always pass current regime context for accurate cost scaling
- Use regime confidence to adjust cost uncertainty
- Monitor regime transitions for cost impact

### 2. **Liquidity Assessment**
- Use real-time liquidity scores when available
- Fall back to historical liquidity patterns
- Consider liquidity regime in execution timing

### 3. **Cost Validation**
- Compare simulated costs to historical TCA data
- Validate cost components sum correctly
- Monitor execution quality scores

### 4. **Performance Optimization**
- Use deterministic mode for backtesting
- Enable random slippage for realistic simulation
- Cache regime and liquidity assessments

## Example: Complete Execution Simulation

```python
import asyncio
from datetime import datetime
from backtest.engine.historical_execution_simulator import HistoricalExecutionSimulator

async def complete_execution_example():
    """Complete example of execution simulation"""
    
    # Initialize simulator
    config = {
        'fill_model': 'realistic',
        'base_spread_bps': 5.0,
        'base_slippage_bps': 2.0,
        'commission_per_share': 0.005,
        'enable_random_slippage': True
    }
    simulator = HistoricalExecutionSimulator(config)
    
    # Market data
    market_data = {
        'timestamp': datetime(2024, 12, 20, 10, 30, 0),
        'close': 150.0,
        'volume': 100000,
        'volatility': 0.025
    }
    
    # Regime context
    regime_context = {
        'primary_regime': 'bull_market',
        'volatility_regime': 'normal_volatility',
        'liquidity_regime': 'normal',
        'regime_confidence': 0.85
    }
    
    # Simulate multiple trades
    trades = [
        {'symbol': 'NVDA', 'side': 'buy', 'quantity': 100},
        {'symbol': 'NVDA', 'side': 'sell', 'quantity': 50},
        {'symbol': 'AAPL', 'side': 'buy', 'quantity': 200}
    ]
    
    fills = []
    for trade in trades:
        fill = simulator.simulate_fill(
            symbol=trade['symbol'],
            side=trade['side'],
            quantity=trade['quantity'],
            decision_price=market_data['close'],
            market_data=market_data,
            regime_context=regime_context,
            liquidity_score=75.0
        )
        fills.append(fill)
        
        print(f"Trade: {trade['side'].upper()} {trade['quantity']} {trade['symbol']}")
        print(f"  Fill Price: ${fill.fill_price:.2f}")
        print(f"  Total Cost: {fill.costs.total_cost_bps:.2f} bps")
        print(f"  Quality Score: {simulator.calculate_execution_quality_score(fill):.1f}/100")
        print()
    
    # Aggregate statistics
    stats = simulator.get_statistics(fills)
    print(f"Aggregate Statistics:")
    print(f"  Total Fills: {stats['total_fills']}")
    print(f"  Avg Cost: {stats['avg_total_cost_bps']:.2f} bps")
    print(f"  Total Cost: ${stats['total_cost_dollars']:.2f}")
    print(f"  Avg Quality: {stats['avg_execution_quality_score']:.1f}/100")

if __name__ == "__main__":
    asyncio.run(complete_execution_example())
```

## Summary

The `HistoricalExecutionSimulator` provides:

✅ **Realistic Execution Costs**: Spread, impact, slippage, commission  
✅ **Regime-Aware Scaling**: Costs adapt to volatility regime (Rule 13)  
✅ **Liquidity-Aware Scaling**: Costs adapt to liquidity conditions (Rule 12)  
✅ **Execution Quality Scoring**: 0-100 quality metrics  
✅ **Aggregate TCA**: Comprehensive transaction cost analysis  
✅ **Institutional Integration**: Seamless backtest engine integration  

This simulator ensures that backtesting results accurately reflect real-world execution costs, providing more realistic performance estimates for trading strategies.
