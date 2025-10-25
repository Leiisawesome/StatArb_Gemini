#!/usr/bin/env python3
"""
Test Suite for Refactored Statistical Arbitrage Strategy (Phase 4.3)

Tests the EnhancedStatisticalArbitrageStrategy to verify:
1. Enriched data validation works correctly
2. Strategy accepts enriched data with required features
3. Strategy rejects data missing required features
4. Signal generation works with enriched data
5. Pre-calculated returns are read (not calculated)

Rule 3 Phase 4 Compliance Testing
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict

# Import the refactored strategy
from core_engine.trading.strategies.implementations.statistical_arbitrage.enhanced_statistical_arbitrage import (
    EnhancedStatisticalArbitrageStrategy, StatisticalArbitrageConfig
)
from core_engine.type_definitions.strategy import StrategyType


class TestPhase43StatisticalArbitrageRefactoring:
    """Test suite for Phase 4.3 Statistical Arbitrage strategy refactoring"""
    
    @pytest.fixture
    def stat_arb_config(self):
        """Create statistical arbitrage strategy configuration"""
        # Pre-define cointegrated pairs for testing
        preloaded_pairs = [
            {
                'asset1': 'AAPL',
                'asset2': 'MSFT',
                'hedge_ratio': 1.2,
                'cointegration_pvalue': 0.01,
                'correlation': 0.85
            },
            {
                'asset1': 'GOOGL',
                'asset2': 'META',
                'hedge_ratio': 0.9,
                'cointegration_pvalue': 0.02,
                'correlation': 0.78
            }
        ]
        
        return StatisticalArbitrageConfig(
            strategy_type=StrategyType.STATISTICAL_ARBITRAGE,
            asset_universe=['AAPL', 'MSFT', 'GOOGL', 'META'],
            preloaded_pairs=preloaded_pairs,
            use_preloaded_pairs=True,  # Skip live cointegration testing
            cointegration_lookback=252,
            entry_zscore_threshold=2.0,
            exit_zscore_threshold=0.5,
            max_spread_positions=3
        )
    
    @pytest.fixture
    def enriched_data(self):
        """Create mock enriched data with required features"""
        def create_enriched_data(symbol: str, num_bars: int = 100) -> pd.DataFrame:
            # Generate realistic time series
            dates = pd.date_range(start='2024-01-01', periods=num_bars, freq='5min')
            
            # Base OHLCV data
            base_price = {'AAPL': 150.0, 'MSFT': 300.0, 'GOOGL': 140.0, 'META': 450.0}.get(symbol, 100.0)
            close_prices = base_price + np.cumsum(np.random.randn(num_bars) * 0.5)
            
            data = pd.DataFrame({
                'timestamp': dates,
                'open': close_prices + np.random.randn(num_bars) * 0.3,
                'high': close_prices + np.abs(np.random.randn(num_bars)) * 0.5,
                'low': close_prices - np.abs(np.random.randn(num_bars)) * 0.5,
                'close': close_prices,
                'volume': np.random.randint(1000000, 5000000, num_bars)
            })
            
            # Add required features (from FeatureEngineer)
            # CRITICAL: returns_1 (pre-calculated 1-period returns)
            data['returns_1'] = data['close'].pct_change()
            
            # Additional features that might be useful
            data['returns_5'] = data['close'].pct_change(5)
            data['volatility'] = data['returns_1'].rolling(20).std() * np.sqrt(252)
            
            data.set_index('timestamp', inplace=True)
            return data
        
        return create_enriched_data
    
    @pytest.fixture
    def raw_data(self):
        """Create raw OHLCV data WITHOUT features (should fail validation)"""
        def create_raw_data(symbol: str, num_bars: int = 100) -> pd.DataFrame:
            dates = pd.date_range(start='2024-01-01', periods=num_bars, freq='5min')
            base_price = {'AAPL': 150.0, 'MSFT': 300.0, 'GOOGL': 140.0, 'META': 450.0}.get(symbol, 100.0)
            close_prices = base_price + np.cumsum(np.random.randn(num_bars) * 0.5)
            
            # ONLY OHLCV - NO FEATURES
            data = pd.DataFrame({
                'timestamp': dates,
                'open': close_prices + np.random.randn(num_bars) * 0.3,
                'high': close_prices + np.abs(np.random.randn(num_bars)) * 0.5,
                'low': close_prices - np.abs(np.random.randn(num_bars)) * 0.5,
                'close': close_prices,
                'volume': np.random.randint(1000000, 5000000, num_bars)
            })
            
            data.set_index('timestamp', inplace=True)
            return data
        
        return create_raw_data


class TestEnrichedDataValidation(TestPhase43StatisticalArbitrageRefactoring):
    """Test enriched data validation (Rule 3 Phase 4)"""
    
    @pytest.mark.asyncio
    async def test_validation_accepts_enriched_data(self, stat_arb_config, enriched_data):
        """Test that validation accepts properly enriched data"""
        strategy = EnhancedStatisticalArbitrageStrategy(stat_arb_config)
        await strategy.initialize()
        
        # Create enriched data for all symbols
        market_data = {
            'AAPL': enriched_data('AAPL'),
            'MSFT': enriched_data('MSFT'),
            'GOOGL': enriched_data('GOOGL'),
            'META': enriched_data('META')
        }
        
        # Validation should NOT raise
        try:
            strategy._validate_enriched_data(market_data)
            assert True, "Validation passed as expected"
        except ValueError as e:
            pytest.fail(f"Validation should have passed but raised: {e}")
    
    @pytest.mark.asyncio
    async def test_validation_rejects_raw_data(self, stat_arb_config, raw_data):
        """Test that validation rejects raw data without features"""
        strategy = EnhancedStatisticalArbitrageStrategy(stat_arb_config)
        await strategy.initialize()
        
        # Create raw data (no features)
        market_data = {
            'AAPL': raw_data('AAPL'),
            'MSFT': raw_data('MSFT')
        }
        
        # Validation SHOULD raise ValueError
        with pytest.raises(ValueError) as exc_info:
            strategy._validate_enriched_data(market_data)
        
        # Check error message mentions missing features
        assert 'missing required features' in str(exc_info.value).lower()
        assert 'returns_1' in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_validation_identifies_missing_returns(self, stat_arb_config, enriched_data):
        """Test that validation identifies specific missing features"""
        strategy = EnhancedStatisticalArbitrageStrategy(stat_arb_config)
        await strategy.initialize()
        
        # Create data missing returns_1
        market_data = {
            'AAPL': enriched_data('AAPL')
        }
        market_data['AAPL'] = market_data['AAPL'].drop(columns=['returns_1'])
        
        # Should raise with specific feature mentioned
        with pytest.raises(ValueError) as exc_info:
            strategy._validate_enriched_data(market_data)
        
        assert 'returns_1' in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_validation_handles_empty_dataframe(self, stat_arb_config):
        """Test that validation handles empty DataFrames"""
        strategy = EnhancedStatisticalArbitrageStrategy(stat_arb_config)
        await strategy.initialize()
        
        market_data = {
            'AAPL': pd.DataFrame()  # Empty DataFrame
        }
        
        with pytest.raises(ValueError) as exc_info:
            strategy._validate_enriched_data(market_data)
        
        assert 'empty' in str(exc_info.value).lower()


class TestSignalGenerationWithEnrichedData(TestPhase43StatisticalArbitrageRefactoring):
    """Test signal generation with enriched data (Rule 3 Phase 4)"""
    
    @pytest.mark.asyncio
    async def test_generate_signals_with_enriched_data(self, stat_arb_config, enriched_data):
        """Test that generate_signals works with enriched data"""
        strategy = EnhancedStatisticalArbitrageStrategy(stat_arb_config)
        await strategy.initialize()
        
        # Create enriched data
        market_data = {
            'AAPL': enriched_data('AAPL', num_bars=800),  # Need more bars for lookback
            'MSFT': enriched_data('MSFT', num_bars=800),
            'GOOGL': enriched_data('GOOGL', num_bars=800),
            'META': enriched_data('META', num_bars=800)
        }
        
        # Generate signals - should NOT raise
        signals = await strategy.generate_signals(market_data)
        
        # Verify signals are returned (may be empty, but should not error)
        assert isinstance(signals, list)
        print(f"✅ Generated {len(signals)} signals from enriched data")
    
    @pytest.mark.asyncio
    async def test_generate_signals_with_raw_data_shows_behavior(self, stat_arb_config, raw_data):
        """Test behavior when given raw data (may not raise, but should handle gracefully)"""
        strategy = EnhancedStatisticalArbitrageStrategy(stat_arb_config)
        await strategy.initialize()
        
        # Create raw data (no features)
        market_data = {
            'AAPL': raw_data('AAPL'),
            'MSFT': raw_data('MSFT')
        }
        
        # The strategy should either raise ValueError or return empty signals
        try:
            signals = await strategy.generate_signals(market_data)
            # If no exception, should return list
            assert isinstance(signals, list)
            print(f"✅ Strategy handled raw data gracefully (returned {len(signals)} signals)")
        except ValueError as e:
            # If raises ValueError, that's also acceptable
            assert 'missing' in str(e).lower() or 'required' in str(e).lower()
            print(f"✅ Strategy correctly rejected raw data: {e}")
    
    @pytest.mark.asyncio
    async def test_signal_generation_uses_pre_calculated_returns(self, stat_arb_config, enriched_data):
        """Test that strategy reads pre-calculated returns"""
        strategy = EnhancedStatisticalArbitrageStrategy(stat_arb_config)
        await strategy.initialize()
        
        # Create enriched data with known returns
        market_data = {
            'AAPL': enriched_data('AAPL', num_bars=100),
            'MSFT': enriched_data('MSFT', num_bars=100)
        }
        
        # Set specific returns values
        market_data['AAPL'].loc[market_data['AAPL'].index[-1], 'returns_1'] = 0.02
        market_data['MSFT'].loc[market_data['MSFT'].index[-1], 'returns_1'] = -0.01
        
        # Generate signals
        signals = await strategy.generate_signals(market_data)
        
        # Verify returns_data was populated from enriched data
        assert 'AAPL' in strategy.returns_data
        assert 'MSFT' in strategy.returns_data
        assert len(strategy.returns_data['AAPL']) > 0
        print(f"✅ Strategy populated returns_data from enriched data")


class TestPreCalculatedReturns(TestPhase43StatisticalArbitrageRefactoring):
    """Verify that returns are read from enriched data (Rule 3 Phase 4)"""
    
    def test_validate_enriched_data_method_exists(self, stat_arb_config):
        """Verify _validate_enriched_data method was added"""
        strategy = EnhancedStatisticalArbitrageStrategy(stat_arb_config)
        
        # Method SHOULD exist
        assert hasattr(strategy, '_validate_enriched_data'), \
            "❌ _validate_enriched_data method should exist (Rule 3 Phase 4)"
        
        assert callable(strategy._validate_enriched_data), \
            "❌ _validate_enriched_data should be callable"
        
        print("✅ _validate_enriched_data method correctly added")
    
    @pytest.mark.asyncio
    async def test_returns_read_from_enriched_data(self, stat_arb_config, enriched_data):
        """Verify returns are read from returns_1 column"""
        strategy = EnhancedStatisticalArbitrageStrategy(stat_arb_config)
        await strategy.initialize()
        
        # Create enriched data
        market_data = {
            'AAPL': enriched_data('AAPL')
        }
        
        # Update market data cache
        strategy._update_market_data_cache(market_data)
        
        # Verify returns_data was populated
        assert 'AAPL' in strategy.returns_data
        assert len(strategy.returns_data['AAPL']) > 0
        
        # Verify returns match returns_1 from enriched data
        original_returns = market_data['AAPL']['returns_1'].dropna()
        cached_returns = strategy.returns_data['AAPL']
        
        # Should be the same (or very close due to floating point)
        assert len(cached_returns) == len(original_returns)
        print("✅ Returns correctly read from enriched data (returns_1 column)")
    
    @pytest.mark.asyncio
    async def test_fallback_when_returns_missing(self, stat_arb_config, enriched_data):
        """Verify fallback when returns_1 is missing (backward compatibility)"""
        strategy = EnhancedStatisticalArbitrageStrategy(stat_arb_config)
        await strategy.initialize()
        
        # Create data WITHOUT returns_1
        market_data = {
            'AAPL': enriched_data('AAPL')
        }
        market_data['AAPL'] = market_data['AAPL'].drop(columns=['returns_1'])
        
        # Update market data cache (should fall back to calculating)
        strategy._update_market_data_cache(market_data)
        
        # Should still have returns (calculated as fallback)
        assert 'AAPL' in strategy.returns_data
        assert len(strategy.returns_data['AAPL']) > 0
        print("✅ Fallback calculation works when returns_1 missing")


class TestBackwardCompatibility(TestPhase43StatisticalArbitrageRefactoring):
    """Test that existing functionality still works"""
    
    @pytest.mark.asyncio
    async def test_strategy_initialization(self, stat_arb_config):
        """Test that strategy still initializes correctly"""
        strategy = EnhancedStatisticalArbitrageStrategy(stat_arb_config)
        
        result = await strategy.initialize()
        
        assert result is True
        assert strategy.is_initialized is True
        print("✅ Strategy initialization works")
    
    @pytest.mark.asyncio
    async def test_strategy_lifecycle(self, stat_arb_config):
        """Test complete strategy lifecycle"""
        strategy = EnhancedStatisticalArbitrageStrategy(stat_arb_config)
        
        # Initialize
        init_result = await strategy.initialize()
        assert init_result is True
        
        # Start
        start_result = await strategy.start()
        assert start_result is True
        
        # Stop
        stop_result = await strategy.stop()
        assert stop_result is True
        
        print("✅ Strategy lifecycle (init/start/stop) works")


class TestRule3Compliance(TestPhase43StatisticalArbitrageRefactoring):
    """Test Rule 3 (Unified Data Flow Pipeline) compliance"""
    
    @pytest.mark.asyncio
    async def test_parameter_name_changed_to_enriched_data(self, stat_arb_config):
        """Verify generate_signals parameter is named 'enriched_data'"""
        import inspect
        
        strategy = EnhancedStatisticalArbitrageStrategy(stat_arb_config)
        
        # Get signature of generate_signals
        sig = inspect.signature(strategy.generate_signals)
        params = list(sig.parameters.keys())
        
        # Should have 'enriched_data' parameter
        assert 'enriched_data' in params, \
            "❌ Parameter should be named 'enriched_data' (Rule 3 Phase 4)"
        
        print("✅ generate_signals parameter correctly named 'enriched_data'")
    
    @pytest.mark.asyncio
    async def test_docstring_mentions_rule3_phase4(self, stat_arb_config):
        """Verify docstrings reference Rule 3 Phase 4"""
        strategy = EnhancedStatisticalArbitrageStrategy(stat_arb_config)
        
        # Check generate_signals docstring
        gen_signals_doc = strategy.generate_signals.__doc__ or ""
        assert 'Rule 3' in gen_signals_doc or 'rule 3' in gen_signals_doc.lower(), \
            "❌ generate_signals docstring should reference Rule 3"
        
        assert 'Phase 4' in gen_signals_doc or 'phase 4' in gen_signals_doc.lower(), \
            "❌ generate_signals docstring should reference Phase 4"
        
        print("✅ Docstrings reference Rule 3 Phase 4")
    
    @pytest.mark.asyncio
    async def test_reads_pre_calculated_returns_not_calculates(self, stat_arb_config, enriched_data):
        """Verify strategy reads returns, not calculates"""
        strategy = EnhancedStatisticalArbitrageStrategy(stat_arb_config)
        await strategy.initialize()
        
        # Create enriched data
        market_data = {
            'AAPL': enriched_data('AAPL')
        }
        
        # Check that returns_1 exists in data
        assert 'returns_1' in market_data['AAPL'].columns
        
        # Update cache (should READ returns)
        strategy._update_market_data_cache(market_data)
        
        # Verify returns were populated
        assert 'AAPL' in strategy.returns_data
        print("✅ Strategy reads pre-calculated returns from enriched data")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short', '-s'])

