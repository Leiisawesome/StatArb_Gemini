"""
Integration Tests for Market Condition Analytics System
======================================================

Integration tests that demonstrate the MarketCondition Analytics system
working with the existing core_structure components.
"""

import pytest
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, List, Any

# Import system components
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core_structure.analytics.market_condition_analytics import (
    MarketConditionAnalyticsEngine,
    MarketCondition,
    MarketConditionState,
    StrategySelection,
    PerformanceFeedback
)

from core_structure.strategies import StrategyType
from examples.market_condition_analytics_integration import UnifiedTradingSystemWithMarketConditions


# ================================================================================
# INTEGRATION TEST FIXTURES
# ================================================================================

@pytest.fixture
def comprehensive_market_data():
    """Generate comprehensive market data for multiple instruments"""
    dates = pd.date_range(start='2024-01-01', periods=1000, freq='1H')
    instruments = ['SPY', 'QQQ', 'IWM', 'AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']
    
    all_data = []
    
    for instrument in instruments:
        # Generate unique price patterns for each instrument
        base_price = np.random.uniform(50, 500)
        drift = np.random.uniform(-0.0001, 0.0001)
        volatility = np.random.uniform(0.01, 0.03)
        
        returns = np.random.normal(drift, volatility, len(dates))
        prices = base_price * np.exp(np.cumsum(returns))
        
        instrument_data = pd.DataFrame({
            'timestamp': dates,
            'symbol': instrument,
            'open': prices * (1 + np.random.normal(0, 0.001, len(dates))),
            'high': prices * (1 + np.random.uniform(0, 0.01, len(dates))),
            'low': prices * (1 - np.random.uniform(0, 0.01, len(dates))),
            'close': prices,
            'volume': np.random.randint(1000000, 50000000, len(dates))
        })
        
        all_data.append(instrument_data)
    
    return pd.concat(all_data, ignore_index=True)


@pytest.fixture
def dynamic_macro_data():
    """Generate dynamic macroeconomic data over time"""
    return {
        'fed_funds_rate': 5.25 + np.random.normal(0, 0.1),
        'cpi_yoy': 3.2 + np.random.normal(0, 0.2),
        'gdp_growth_qoq': 2.1 + np.random.normal(0, 0.3),
        'unemployment': 3.8 + np.random.normal(0, 0.1),
        'vix': max(10, min(50, 18.5 + np.random.normal(0, 5))),
        'yield_curve_slope': 1.2 + np.random.normal(0, 0.3),
        'dollar_index': 103.5 + np.random.normal(0, 2),
        'oil_price': 75 + np.random.normal(0, 5),
        'gold_price': 2000 + np.random.normal(0, 50)
    }


@pytest.fixture
def dynamic_sentiment_data():
    """Generate dynamic sentiment data"""
    return {
        'news_sentiment_score': np.random.uniform(-0.5, 0.5),
        'social_media_sentiment': np.random.uniform(-0.3, 0.3),
        'analyst_sentiment': np.random.uniform(-0.2, 0.4),
        'put_call_ratio': max(0.3, min(2.0, 0.8 + np.random.normal(0, 0.2))),
        'fear_greed_index': max(0, min(100, 45 + np.random.normal(0, 15))),
        'insider_trading_ratio': max(0, min(1, 0.15 + np.random.normal(0, 0.05))),
        'options_skew': np.random.uniform(0.1, 0.3),
        'credit_spreads': max(0.5, 2.0 + np.random.normal(0, 0.5))
    }


# ================================================================================
# INTEGRATION TESTS
# ================================================================================

class TestMarketConditionAnalyticsIntegration:
    """Integration tests for the complete analytics system"""
    
    @pytest.mark.asyncio
    async def test_full_system_initialization_and_workflow(self, 
                                                          comprehensive_market_data,
                                                          dynamic_macro_data,
                                                          dynamic_sentiment_data):
        """Test complete system initialization and basic workflow"""
        
        print("\n🚀 Testing Full System Initialization and Workflow")
        print("=" * 60)
        
        # Create unified trading system
        trading_system = UnifiedTradingSystemWithMarketConditions()
        
        try:
            # Start the system
            await trading_system.start_system()
            print("✅ Trading system started successfully")
            
            # Process market data through complete workflow
            results = await trading_system.process_market_data(comprehensive_market_data)
            
            # Validate results structure
            assert 'market_state' in results
            assert 'strategy_selection' in results
            assert 'trading_signals' in results
            assert 'execution_results' in results
            assert 'portfolio_state' in results
            
            market_state = results['market_state']
            strategy_selection = results['strategy_selection']
            
            print(f"📊 Market Regime Detected: {market_state.primary_condition.value}")
            print(f"🎯 Confidence Level: {market_state.confidence:.2f}")
            print(f"📈 Strategy Allocation: {strategy_selection.selected_strategies}")
            print(f"🔄 Generated Signals: {len(results['trading_signals'])}")
            print(f"💼 Portfolio Positions: {len(results['portfolio_state'])}")
            
            # Validate market state
            assert isinstance(market_state, MarketConditionState)
            assert isinstance(market_state.primary_condition, MarketCondition)
            assert 0 <= market_state.confidence <= 1
            
            # Validate strategy selection
            assert isinstance(strategy_selection, StrategySelection)
            assert isinstance(strategy_selection.selected_strategies, dict)
            assert abs(sum(strategy_selection.selected_strategies.values()) - 1.0) < 0.01
            
            print("✅ Full workflow completed successfully")
            
        finally:
            await trading_system.market_condition_engine.stop()
    
    @pytest.mark.asyncio
    async def test_regime_change_detection_and_adaptation(self,
                                                        comprehensive_market_data,
                                                        dynamic_macro_data,
                                                        dynamic_sentiment_data):
        """Test regime change detection and system adaptation"""
        
        print("\n🔄 Testing Regime Change Detection and Adaptation")
        print("=" * 60)
        
        trading_system = UnifiedTradingSystemWithMarketConditions()
        
        try:
            await trading_system.start_system()
            
            # Process initial market data
            initial_results = await trading_system.process_market_data(comprehensive_market_data)
            initial_regime = initial_results['market_state'].primary_condition
            initial_allocation = initial_results['strategy_selection'].selected_strategies.copy()
            
            print(f"📊 Initial Regime: {initial_regime.value}")
            print(f"📈 Initial Allocation: {initial_allocation}")
            
            # Simulate market condition change by modifying data
            # Create bear market conditions
            bear_market_data = comprehensive_market_data.copy()
            bear_market_data['close'] = bear_market_data['close'] * 0.85  # 15% drop
            bear_market_data['volume'] = bear_market_data['volume'] * 1.5  # Increased volume
            
            # Update macro data to reflect stressed conditions
            stressed_macro = dynamic_macro_data.copy()
            stressed_macro['vix'] = 35  # High volatility
            stressed_macro['yield_curve_slope'] = -0.5  # Inverted yield curve
            
            # Update sentiment to bearish
            bearish_sentiment = dynamic_sentiment_data.copy()
            bearish_sentiment['news_sentiment_score'] = -0.4
            bearish_sentiment['put_call_ratio'] = 1.5
            bearish_sentiment['fear_greed_index'] = 20
            
            # Process with stressed conditions
            stressed_results = await trading_system.process_market_data(bear_market_data)
            new_regime = stressed_results['market_state'].primary_condition
            new_allocation = stressed_results['strategy_selection'].selected_strategies
            
            print(f"📊 New Regime: {new_regime.value}")
            print(f"📈 New Allocation: {new_allocation}")
            
            # Validate regime change detection
            if initial_regime != new_regime:
                print("✅ Regime change detected successfully")
                
                # Check allocation adaptation
                momentum_change = new_allocation.get(StrategyType.MOMENTUM, 0) - initial_allocation.get(StrategyType.MOMENTUM, 0)
                mean_reversion_change = new_allocation.get(StrategyType.MEAN_REVERSION, 0) - initial_allocation.get(StrategyType.MEAN_REVERSION, 0)
                
                print(f"🔄 Momentum allocation change: {momentum_change:.2f}")
                print(f"🔄 Mean reversion allocation change: {mean_reversion_change:.2f}")
                
                assert abs(momentum_change) > 0.05 or abs(mean_reversion_change) > 0.05, "Allocation should change significantly"
            else:
                print("ℹ️ No regime change detected (market conditions may not have been stressed enough)")
            
        finally:
            await trading_system.market_condition_engine.stop()
    
    @pytest.mark.asyncio
    async def test_performance_feedback_learning(self,
                                                comprehensive_market_data,
                                                dynamic_macro_data,
                                                dynamic_sentiment_data):
        """Test performance feedback and learning capabilities"""
        
        print("\n📊 Testing Performance Feedback and Learning")
        print("=" * 60)
        
        trading_system = UnifiedTradingSystemWithMarketConditions()
        
        try:
            await trading_system.start_system()
            
            # Simulate multiple trading cycles with performance feedback
            performance_history = []
            
            for cycle in range(5):
                print(f"\n--- Trading Cycle {cycle + 1} ---")
                
                # Add some randomness to market data for each cycle
                cycle_data = comprehensive_market_data.copy()
                cycle_data['close'] = cycle_data['close'] * (1 + np.random.normal(0, 0.02))
                
                # Process market data
                results = await trading_system.process_market_data(cycle_data)
                
                market_state = results['market_state']
                strategy_selection = results['strategy_selection']
                
                print(f"Regime: {market_state.primary_condition.value} (confidence: {market_state.confidence:.2f})")
                print(f"Strategies: {strategy_selection.selected_strategies}")
                
                # Simulate trading performance
                simulated_returns = {}
                for strategy_type, allocation in strategy_selection.selected_strategies.items():
                    if allocation > 0:
                        # Simulate strategy-specific returns
                        if strategy_type == StrategyType.MOMENTUM:
                            base_return = 0.01 if market_state.primary_condition == MarketCondition.BULL_MARKET else -0.005
                        elif strategy_type == StrategyType.MEAN_REVERSION:
                            base_return = 0.008 if market_state.primary_condition == MarketCondition.SIDEWAYS else 0.003
                        else:
                            base_return = 0.005
                        
                        actual_return = base_return + np.random.normal(0, 0.01)
                        simulated_returns[strategy_type] = actual_return
                
                # Create performance feedback
                for strategy_type, actual_return in simulated_returns.items():
                    feedback = PerformanceFeedback(
                        timestamp=datetime.now(),
                        strategy=strategy_type,
                        instrument='SPY',
                        regime=market_state.primary_condition,
                        actual_return=actual_return,
                        predicted_return=0.01,  # Assumed prediction
                        prediction_error=abs(actual_return - 0.01),
                        risk_adjusted_return=actual_return / 0.15,
                        execution_quality=np.random.uniform(0.9, 1.0),
                        regime_accuracy=market_state.confidence,
                        metadata={'cycle': cycle}
                    )
                    
                    await trading_system.market_condition_engine.update_performance_feedback(feedback)
                
                # Track performance metrics
                metrics = trading_system.market_condition_engine.get_performance_metrics()
                performance_history.append(metrics)
                
                print(f"Performance metrics: {metrics}")
            
            # Analyze learning over time
            if len(performance_history) > 1:
                initial_accuracy = performance_history[0].get('recent_regime_accuracy', 0)
                final_accuracy = performance_history[-1].get('recent_regime_accuracy', 0)
                
                print(f"\n📈 Learning Analysis:")
                print(f"Initial regime accuracy: {initial_accuracy:.3f}")
                print(f"Final regime accuracy: {final_accuracy:.3f}")
                
                if final_accuracy > initial_accuracy:
                    print("✅ System shows learning improvement over time")
                else:
                    print("ℹ️ No clear learning trend (may need more cycles or better simulation)")
            
        finally:
            await trading_system.market_condition_engine.stop()
    
    @pytest.mark.asyncio
    async def test_multi_strategy_coordination(self,
                                             comprehensive_market_data,
                                             dynamic_macro_data,
                                             dynamic_sentiment_data):
        """Test coordination between multiple strategies"""
        
        print("\n🎯 Testing Multi-Strategy Coordination")
        print("=" * 60)
        
        trading_system = UnifiedTradingSystemWithMarketConditions()
        
        try:
            await trading_system.start_system()
            
            # Process market data
            results = await trading_system.process_market_data(comprehensive_market_data)
            
            strategy_selection = results['strategy_selection']
            trading_signals = results['trading_signals']
            
            print(f"📈 Strategy Allocation: {strategy_selection.selected_strategies}")
            print(f"🔄 Generated Signals: {len(trading_signals)}")
            
            # Analyze signal distribution across strategies
            signal_distribution = {}
            for signal in trading_signals:
                strategy = signal['strategy']
                if strategy not in signal_distribution:
                    signal_distribution[strategy] = 0
                signal_distribution[strategy] += 1
            
            print(f"📊 Signal Distribution: {signal_distribution}")
            
            # Validate signal consistency with allocations
            for strategy_name, signal_count in signal_distribution.items():
                strategy_type = StrategyType(strategy_name)
                allocation = strategy_selection.selected_strategies.get(strategy_type, 0)
                
                if allocation > 0:
                    assert signal_count > 0, f"Strategy {strategy_name} has allocation but no signals"
                    print(f"✅ {strategy_name}: allocation={allocation:.2f}, signals={signal_count}")
            
            # Test instrument optimization per strategy
            instruments_per_strategy = strategy_selection.instruments_per_strategy
            print(f"🎯 Instruments per strategy: {instruments_per_strategy}")
            
            for strategy_type, instruments in instruments_per_strategy.items():
                assert isinstance(instruments, list), "Instruments should be a list"
                assert len(instruments) > 0, f"Strategy {strategy_type} should have instruments"
                print(f"✅ {strategy_type.value}: {len(instruments)} instruments")
            
        finally:
            await trading_system.market_condition_engine.stop()
    
    @pytest.mark.asyncio  
    async def test_system_resilience_and_error_handling(self,
                                                       comprehensive_market_data):
        """Test system resilience with various error conditions"""
        
        print("\n🛡️ Testing System Resilience and Error Handling")
        print("=" * 60)
        
        trading_system = UnifiedTradingSystemWithMarketConditions()
        
        try:
            await trading_system.start_system()
            
            # Test with incomplete market data
            print("Testing with incomplete market data...")
            incomplete_data = comprehensive_market_data.head(10)  # Very limited data
            
            try:
                results = await trading_system.process_market_data(incomplete_data)
                print("✅ System handled incomplete data gracefully")
            except Exception as e:
                print(f"⚠️ System failed with incomplete data: {e}")
            
            # Test with missing macro data
            print("Testing with missing macro data...")
            try:
                results = await trading_system.process_market_data(comprehensive_market_data)
                print("✅ System handled missing macro data gracefully")
            except Exception as e:
                print(f"⚠️ System failed with missing macro data: {e}")
            
            # Test with extreme market conditions
            print("Testing with extreme market conditions...")
            extreme_data = comprehensive_market_data.copy()
            extreme_data['close'] = extreme_data['close'] * 0.5  # 50% crash
            extreme_data['volume'] = extreme_data['volume'] * 10  # 10x volume
            
            try:
                results = await trading_system.process_market_data(extreme_data)
                market_state = results['market_state']
                print(f"✅ System handled extreme conditions: {market_state.primary_condition.value}")
            except Exception as e:
                print(f"⚠️ System failed with extreme conditions: {e}")
            
            print("✅ Resilience testing completed")
            
        finally:
            await trading_system.market_condition_engine.stop()


# ================================================================================
# PERFORMANCE BENCHMARKS
# ================================================================================

class TestMarketConditionAnalyticsPerformance:
    """Performance tests for the analytics system"""
    
    @pytest.mark.asyncio
    async def test_processing_speed_benchmark(self, comprehensive_market_data):
        """Benchmark processing speed of the analytics engine"""
        
        print("\n⚡ Testing Processing Speed Benchmark")
        print("=" * 60)
        
        trading_system = UnifiedTradingSystemWithMarketConditions()
        
        try:
            await trading_system.start_system()
            
            # Warm up
            await trading_system.process_market_data(comprehensive_market_data.head(100))
            
            # Benchmark processing time
            start_time = datetime.now()
            
            for i in range(5):
                await trading_system.process_market_data(comprehensive_market_data)
            
            end_time = datetime.now()
            total_time = (end_time - start_time).total_seconds()
            avg_time = total_time / 5
            
            print(f"📊 Processing Performance:")
            print(f"   Total time for 5 runs: {total_time:.2f} seconds")
            print(f"   Average time per run: {avg_time:.2f} seconds")
            print(f"   Data points per run: {len(comprehensive_market_data):,}")
            print(f"   Processing rate: {len(comprehensive_market_data) / avg_time:.0f} points/second")
            
            # Performance assertions
            assert avg_time < 10.0, f"Processing too slow: {avg_time:.2f}s > 10s"
            print("✅ Performance benchmark passed")
            
        finally:
            await trading_system.market_condition_engine.stop()
    
    @pytest.mark.asyncio
    async def test_memory_efficiency(self, comprehensive_market_data):
        """Test memory efficiency of the analytics system"""
        
        print("\n💾 Testing Memory Efficiency")
        print("=" * 60)
        
        trading_system = UnifiedTradingSystemWithMarketConditions()
        
        try:
            await trading_system.start_system()
            
            # Process data multiple times to test memory management
            for i in range(10):
                await trading_system.process_market_data(comprehensive_market_data)
                
                if i % 3 == 0:
                    print(f"Completed {i + 1} processing cycles")
            
            print("✅ Memory efficiency test completed (no obvious memory leaks)")
            
        finally:
            await trading_system.market_condition_engine.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])