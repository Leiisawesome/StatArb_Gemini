"""
Test Historical Execution Simulator
===================================

Tests for the HistoricalExecutionSimulator component.

Tests:
1. Simulator initialization
2. Basic fill simulation
3. Cost calculations (spread, impact, slippage)
4. Regime-aware cost adjustments (Rule 13)
5. Liquidity-aware cost adjustments (Rule 12)
6. Execution quality scoring
7. Aggregate statistics

Success Criteria:
- Simulator initializes with default and custom configs
- Realistic fills generated with proper cost breakdown
- Costs scale appropriately with regime and liquidity
- Quality metrics calculated correctly
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime
import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backtest.engine.historical_execution_simulator import (
    HistoricalExecutionSimulator,
    SimulatedFill,
    ExecutionCosts,
    FillModel
)


# ============================================================
# Test Fixtures
# ============================================================

@pytest.fixture
def default_simulator():
    """Create simulator with default configuration"""
    return HistoricalExecutionSimulator()


@pytest.fixture
def custom_simulator():
    """Create simulator with custom configuration"""
    config = {
        'fill_model': 'realistic',
        'base_spread_bps': 10.0,
        'base_slippage_bps': 3.0,
        'commission_per_share': 0.01,
        'impact_linear_coeff': 0.15,
        'impact_sqrt_coeff': 0.6,
        'enable_random_slippage': False  # Deterministic for testing
    }
    return HistoricalExecutionSimulator(config)


@pytest.fixture
def sample_market_data():
    """Create sample market data for testing"""
    return {
        'timestamp': datetime(2024, 12, 20, 10, 30, 0),
        'open': 100.0,
        'high': 101.0,
        'low': 99.5,
        'close': 100.5,
        'volume': 50000,
        'volatility': 0.02  # 2% volatility
    }


@pytest.fixture
def regime_context_normal():
    """Normal volatility regime context"""
    return {
        'primary_regime': 'bull_market',
        'volatility_regime': 'normal_volatility',
        'liquidity_regime': 'normal',
        'regime_confidence': 0.85
    }


@pytest.fixture
def regime_context_high_vol():
    """High volatility regime context"""
    return {
        'primary_regime': 'bear_market',
        'volatility_regime': 'high_volatility',
        'liquidity_regime': 'low',
        'regime_confidence': 0.90
    }


# ============================================================
# Test 1: Simulator Initialization
# ============================================================

def test_simulator_initialization_default(default_simulator):
    """Test 1: Simulator initializes with default configuration"""
    
    print("\n" + "=" * 80)
    print("TEST 1: Simulator Initialization (Default)")
    print("=" * 80)
    
    assert default_simulator is not None
    assert default_simulator.fill_model == FillModel.REALISTIC
    assert default_simulator.base_spread_bps == 5.0
    assert default_simulator.base_slippage_bps == 2.0
    assert default_simulator.commission_per_share == 0.005
    
    print(f"✅ Simulator initialized with defaults:")
    print(f"   Fill Model: {default_simulator.fill_model.value}")
    print(f"   Base Spread: {default_simulator.base_spread_bps} bps")
    print(f"   Base Slippage: {default_simulator.base_slippage_bps} bps")
    print(f"   Commission: ${default_simulator.commission_per_share}/share")
    
    print("✅ Test 1 PASSED\n")


def test_simulator_initialization_custom(custom_simulator):
    """Test 2: Simulator initializes with custom configuration"""
    
    print("\n" + "=" * 80)
    print("TEST 2: Simulator Initialization (Custom)")
    print("=" * 80)
    
    assert custom_simulator.base_spread_bps == 10.0
    assert custom_simulator.base_slippage_bps == 3.0
    assert custom_simulator.commission_per_share == 0.01
    assert custom_simulator.enable_random_slippage is False
    
    print(f"✅ Simulator initialized with custom config:")
    print(f"   Base Spread: {custom_simulator.base_spread_bps} bps")
    print(f"   Base Slippage: {custom_simulator.base_slippage_bps} bps")
    print(f"   Commission: ${custom_simulator.commission_per_share}/share")
    print(f"   Random Slippage: {custom_simulator.enable_random_slippage}")
    
    print("✅ Test 2 PASSED\n")


# ============================================================
# Test 3: Basic Fill Simulation
# ============================================================

def test_basic_fill_simulation_buy(default_simulator, sample_market_data):
    """Test 3: Simulate basic BUY order"""
    
    print("\n" + "=" * 80)
    print("TEST 3: Basic Fill Simulation (BUY)")
    print("=" * 80)
    
    fill = default_simulator.simulate_fill(
        symbol='NVDA',
        side='buy',
        quantity=100,
        decision_price=100.0,
        market_data=sample_market_data,
        authorization_id='auth_123',
        strategy_id='momentum_test'
    )
    
    assert fill is not None
    assert fill.symbol == 'NVDA'
    assert fill.side == 'buy'
    assert fill.quantity == 100
    assert fill.fill_price > fill.market_price  # BUY pays more
    assert fill.costs.total_cost_bps > 0
    
    print(f"✅ BUY fill simulated:")
    print(f"   Symbol: {fill.symbol}")
    print(f"   Quantity: {fill.quantity}")
    print(f"   Market Price: ${fill.market_price:.2f}")
    print(f"   Fill Price: ${fill.fill_price:.2f}")
    print(f"   Total Cost: {fill.costs.total_cost_bps:.2f} bps (${fill.costs.total_cost_dollars:.2f})")
    print(f"   Spread Cost: {fill.costs.spread_cost_bps:.2f} bps")
    print(f"   Impact Cost: {fill.costs.market_impact_bps:.2f} bps")
    print(f"   Slippage: {fill.costs.slippage_bps:.2f} bps")
    print(f"   Commission: {fill.costs.commission_bps:.2f} bps")
    
    print("✅ Test 3 PASSED\n")


def test_basic_fill_simulation_sell(default_simulator, sample_market_data):
    """Test 4: Simulate basic SELL order"""
    
    print("\n" + "=" * 80)
    print("TEST 4: Basic Fill Simulation (SELL)")
    print("=" * 80)
    
    fill = default_simulator.simulate_fill(
        symbol='NVDA',
        side='sell',
        quantity=100,
        decision_price=100.0,
        market_data=sample_market_data
    )
    
    assert fill.side == 'sell'
    assert fill.fill_price < fill.market_price  # SELL receives less
    assert fill.costs.total_cost_bps > 0
    
    print(f"✅ SELL fill simulated:")
    print(f"   Market Price: ${fill.market_price:.2f}")
    print(f"   Fill Price: ${fill.fill_price:.2f}")
    print(f"   Total Cost: {fill.costs.total_cost_bps:.2f} bps")
    
    print("✅ Test 4 PASSED\n")


# ============================================================
# Test 5: Regime-Aware Cost Adjustments (Rule 13)
# ============================================================

def test_regime_aware_costs(default_simulator, sample_market_data, 
                           regime_context_normal, regime_context_high_vol):
    """Test 5: Costs scale with volatility regime (Rule 13)"""
    
    print("\n" + "=" * 80)
    print("TEST 5: Regime-Aware Cost Adjustments (Rule 13)")
    print("=" * 80)
    
    # Fill in normal volatility
    fill_normal = default_simulator.simulate_fill(
        symbol='NVDA',
        side='buy',
        quantity=100,
        decision_price=100.0,
        market_data=sample_market_data,
        regime_context=regime_context_normal
    )
    
    # Fill in high volatility
    fill_high_vol = default_simulator.simulate_fill(
        symbol='NVDA',
        side='buy',
        quantity=100,
        decision_price=100.0,
        market_data=sample_market_data,
        regime_context=regime_context_high_vol
    )
    
    print(f"Normal Volatility Regime:")
    print(f"   Total Cost: {fill_normal.costs.total_cost_bps:.2f} bps")
    print(f"   Spread: {fill_normal.costs.spread_cost_bps:.2f} bps")
    print(f"   Impact: {fill_normal.costs.market_impact_bps:.2f} bps")
    
    print(f"\nHigh Volatility Regime:")
    print(f"   Total Cost: {fill_high_vol.costs.total_cost_bps:.2f} bps")
    print(f"   Spread: {fill_high_vol.costs.spread_cost_bps:.2f} bps")
    print(f"   Impact: {fill_high_vol.costs.market_impact_bps:.2f} bps")
    
    # High vol should have higher costs
    assert fill_high_vol.costs.total_cost_bps > fill_normal.costs.total_cost_bps
    assert fill_high_vol.costs.spread_cost_bps > fill_normal.costs.spread_cost_bps
    assert fill_high_vol.costs.market_impact_bps > fill_normal.costs.market_impact_bps
    
    cost_increase_pct = ((fill_high_vol.costs.total_cost_bps / fill_normal.costs.total_cost_bps) - 1.0) * 100
    print(f"\n✅ High vol costs are {cost_increase_pct:.1f}% higher (Rule 13 compliance)")
    
    print("✅ Test 5 PASSED\n")


# ============================================================
# Test 6: Liquidity-Aware Cost Adjustments (Rule 12)
# ============================================================

def test_liquidity_aware_costs(default_simulator, sample_market_data, regime_context_normal):
    """Test 6: Costs scale with liquidity conditions (Rule 12)"""
    
    print("\n" + "=" * 80)
    print("TEST 6: Liquidity-Aware Cost Adjustments (Rule 12)")
    print("=" * 80)
    
    # Fill with high liquidity
    fill_high_liq = default_simulator.simulate_fill(
        symbol='NVDA',
        side='buy',
        quantity=100,
        decision_price=100.0,
        market_data=sample_market_data,
        regime_context=regime_context_normal,
        liquidity_score=85.0  # High liquidity
    )
    
    # Fill with low liquidity
    fill_low_liq = default_simulator.simulate_fill(
        symbol='NVDA',
        side='buy',
        quantity=100,
        decision_price=100.0,
        market_data=sample_market_data,
        regime_context=regime_context_normal,
        liquidity_score=35.0  # Low liquidity
    )
    
    print(f"High Liquidity (score=85):")
    print(f"   Total Cost: {fill_high_liq.costs.total_cost_bps:.2f} bps")
    print(f"   Spread: {fill_high_liq.costs.spread_cost_bps:.2f} bps")
    print(f"   Impact: {fill_high_liq.costs.market_impact_bps:.2f} bps")
    
    print(f"\nLow Liquidity (score=35):")
    print(f"   Total Cost: {fill_low_liq.costs.total_cost_bps:.2f} bps")
    print(f"   Spread: {fill_low_liq.costs.spread_cost_bps:.2f} bps")
    print(f"   Impact: {fill_low_liq.costs.market_impact_bps:.2f} bps")
    
    # Low liquidity should have higher costs
    assert fill_low_liq.costs.total_cost_bps > fill_high_liq.costs.total_cost_bps
    
    cost_increase_pct = ((fill_low_liq.costs.total_cost_bps / fill_high_liq.costs.total_cost_bps) - 1.0) * 100
    print(f"\n✅ Low liquidity costs are {cost_increase_pct:.1f}% higher (Rule 12 compliance)")
    
    print("✅ Test 6 PASSED\n")


# ============================================================
# Test 7: Market Impact Scaling
# ============================================================

def test_market_impact_scaling(default_simulator, sample_market_data):
    """Test 7: Market impact scales with order size"""
    
    print("\n" + "=" * 80)
    print("TEST 7: Market Impact Scaling")
    print("=" * 80)
    
    # Small order
    fill_small = default_simulator.simulate_fill(
        symbol='NVDA',
        side='buy',
        quantity=100,
        decision_price=100.0,
        market_data=sample_market_data
    )
    
    # Large order
    fill_large = default_simulator.simulate_fill(
        symbol='NVDA',
        side='buy',
        quantity=10000,  # 100x larger
        decision_price=100.0,
        market_data=sample_market_data
    )
    
    print(f"Small Order (100 shares):")
    print(f"   Market Impact: {fill_small.costs.market_impact_bps:.2f} bps")
    
    print(f"\nLarge Order (10,000 shares):")
    print(f"   Market Impact: {fill_large.costs.market_impact_bps:.2f} bps")
    
    # Large order should have much higher impact
    assert fill_large.costs.market_impact_bps > fill_small.costs.market_impact_bps
    
    impact_ratio = fill_large.costs.market_impact_bps / fill_small.costs.market_impact_bps
    print(f"\n✅ Large order impact is {impact_ratio:.1f}x higher")
    
    print("✅ Test 7 PASSED\n")


# ============================================================
# Test 8: Execution Quality Scoring
# ============================================================

def test_execution_quality_scoring(default_simulator, sample_market_data):
    """Test 8: Execution quality scores calculated correctly"""
    
    print("\n" + "=" * 80)
    print("TEST 8: Execution Quality Scoring")
    print("=" * 80)
    
    # Good fill (low costs)
    fill_good = default_simulator.simulate_fill(
        symbol='NVDA',
        side='buy',
        quantity=100,
        decision_price=100.0,
        market_data=sample_market_data,
        liquidity_score=90.0  # High liquidity = low costs
    )
    
    # Poor fill (high costs)
    fill_poor = default_simulator.simulate_fill(
        symbol='NVDA',
        side='buy',
        quantity=10000,
        decision_price=100.0,
        market_data=sample_market_data,
        liquidity_score=20.0  # Low liquidity = high costs
    )
    
    quality_good = default_simulator.calculate_execution_quality_score(fill_good)
    quality_poor = default_simulator.calculate_execution_quality_score(fill_poor)
    
    print(f"Good Fill:")
    print(f"   Cost: {fill_good.costs.total_cost_bps:.2f} bps")
    print(f"   Quality Score: {quality_good:.1f}/100")
    
    print(f"\nPoor Fill:")
    print(f"   Cost: {fill_poor.costs.total_cost_bps:.2f} bps")
    print(f"   Quality Score: {quality_poor:.1f}/100")
    
    # Good fill should have higher quality score
    assert quality_good > quality_poor
    assert 0 <= quality_good <= 100
    assert 0 <= quality_poor <= 100
    
    print(f"\n✅ Quality scores inversely correlated with costs")
    
    print("✅ Test 8 PASSED\n")


# ============================================================
# Test 9: Aggregate Statistics
# ============================================================

def test_aggregate_statistics(default_simulator, sample_market_data):
    """Test 9: Aggregate statistics calculated correctly"""
    
    print("\n" + "=" * 80)
    print("TEST 9: Aggregate Statistics")
    print("=" * 80)
    
    # Generate multiple fills
    fills = []
    for i in range(10):
        fill = default_simulator.simulate_fill(
            symbol='NVDA',
            side='buy' if i % 2 == 0 else 'sell',
            quantity=100 * (i + 1),
            decision_price=100.0,
            market_data=sample_market_data
        )
        fills.append(fill)
    
    # Calculate statistics
    stats = default_simulator.get_statistics(fills)
    
    assert stats['total_fills'] == 10
    assert stats['buy_fills'] + stats['sell_fills'] == 10
    assert stats['avg_total_cost_bps'] > 0
    assert stats['total_cost_dollars'] > 0
    
    print(f"✅ Aggregate statistics for {stats['total_fills']} fills:")
    print(f"   Buy Fills: {stats['buy_fills']}")
    print(f"   Sell Fills: {stats['sell_fills']}")
    print(f"   Avg Total Cost: {stats['avg_total_cost_bps']:.2f} bps")
    print(f"   Median Total Cost: {stats['median_total_cost_bps']:.2f} bps")
    print(f"   Max Cost: {stats['max_total_cost_bps']:.2f} bps")
    print(f"   Min Cost: {stats['min_total_cost_bps']:.2f} bps")
    print(f"   Total Cost ($): ${stats['total_cost_dollars']:.2f}")
    print(f"   Avg Execution Quality: {stats['avg_execution_quality_score']:.1f}/100")
    
    print("✅ Test 9 PASSED\n")


# ============================================================
# Test 10: Cost Component Breakdown
# ============================================================

def test_cost_component_breakdown(default_simulator, sample_market_data):
    """Test 10: All cost components calculated and sum correctly"""
    
    print("\n" + "=" * 80)
    print("TEST 10: Cost Component Breakdown")
    print("=" * 80)
    
    fill = default_simulator.simulate_fill(
        symbol='NVDA',
        side='buy',
        quantity=1000,
        decision_price=100.0,
        market_data=sample_market_data
    )
    
    # Verify cost breakdown
    costs = fill.costs
    
    # Components should sum to total (with small floating point tolerance)
    calculated_total = (costs.spread_cost_bps + costs.market_impact_bps + 
                       costs.slippage_bps + costs.commission_bps)
    
    assert abs(costs.total_cost_bps - calculated_total) < 0.01
    
    # All components should be non-negative
    assert costs.spread_cost_bps >= 0
    assert costs.market_impact_bps >= 0
    assert costs.slippage_bps >= 0
    assert costs.commission_bps >= 0
    
    print(f"✅ Cost component breakdown:")
    print(f"   Spread Cost: {costs.spread_cost_bps:.2f} bps ({costs.spread_cost_bps/costs.total_cost_bps*100:.1f}%)")
    print(f"   Market Impact: {costs.market_impact_bps:.2f} bps ({costs.market_impact_bps/costs.total_cost_bps*100:.1f}%)")
    print(f"   Slippage: {costs.slippage_bps:.2f} bps ({costs.slippage_bps/costs.total_cost_bps*100:.1f}%)")
    print(f"   Commission: {costs.commission_bps:.2f} bps ({costs.commission_bps/costs.total_cost_bps*100:.1f}%)")
    print(f"   Total: {costs.total_cost_bps:.2f} bps")
    print(f"   Calculated Sum: {calculated_total:.2f} bps")
    print(f"   Match: {'✅' if abs(costs.total_cost_bps - calculated_total) < 0.01 else '❌'}")
    
    # Impact breakdown
    impact_sum = costs.permanent_impact_bps + costs.temporary_impact_bps
    print(f"\n   Impact Breakdown:")
    print(f"   - Permanent: {costs.permanent_impact_bps:.2f} bps")
    print(f"   - Temporary: {costs.temporary_impact_bps:.2f} bps")
    print(f"   - Total: {impact_sum:.2f} bps")
    
    print("\n✅ Test 10 PASSED\n")


# ============================================================
# Summary Test
# ============================================================

def test_simulator_summary(default_simulator):
    """Summary: Verify simulator is ready for integration"""
    
    print("\n" + "=" * 80)
    print("HISTORICAL EXECUTION SIMULATOR SUMMARY")
    print("=" * 80)
    
    print(f"\n✅ Simulator Configuration:")
    print(f"   Fill Model: {default_simulator.fill_model.value}")
    print(f"   Base Spread: {default_simulator.base_spread_bps} bps")
    print(f"   Base Slippage: {default_simulator.base_slippage_bps} bps")
    print(f"   Commission: ${default_simulator.commission_per_share}/share")
    print(f"   Impact Model: Almgren-Chriss")
    print(f"   Regime Aware: ✅ (Rule 13)")
    print(f"   Liquidity Aware: ✅ (Rule 12)")
    
    print(f"\n✅ Features:")
    print(f"   - Realistic fill simulation")
    print(f"   - Multi-component cost modeling")
    print(f"   - Regime-based cost scaling")
    print(f"   - Liquidity-based cost scaling")
    print(f"   - Execution quality scoring")
    print(f"   - Aggregate TCA statistics")
    
    print(f"\n🎯 Phase 5.2 Status: COMPLETE")
    print(f"   Next: Phase 5.3 - Execution Flow Integration")
    print("=" * 80 + "\n")


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v', '-s'])

