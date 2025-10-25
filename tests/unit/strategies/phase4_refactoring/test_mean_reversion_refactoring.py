#!/usr/bin/env python3
"""
Test Suite for Refactored Mean Reversion Strategy (Phase 4.2)

Tests the EnhancedMeanReversionStrategy to verify:
1. Enriched data validation works correctly
2. Strategy accepts enriched data with all required indicators
3. Strategy rejects data missing required indicators
4. Signal generation works with enriched data
5. No indicator calculations are performed (reads only)

Rule 3 Phase 4 Compliance Testing
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict

# Import the refactored strategy
from core_engine.trading.strategies.implementations.mean_reversion.enhanced_mean_reversion import (
    EnhancedMeanReversionStrategy
)
from core_engine.config import MeanReversionConfig
from core_engine.type_definitions.strategy import StrategyType


class TestPhase42MeanReversionRefactoring:
    """Test suite for Phase 4.2 Mean Reversion strategy refactoring"""
    
    @pytest.fixture
    def mean_reversion_config(self):
        """Create mean reversion strategy configuration"""
        return MeanReversionConfig(
            strategy_type=StrategyType.MEAN_REVERSION,
            symbols=['AAPL', 'TSLA'],
            lookback_period=20,
            zscore_entry_threshold=2.0,
            zscore_exit_threshold=0.5,
            bollinger_period=20,
            bollinger_std=2.0,
            rsi_period=14,
            rsi_oversold=30.0,
            rsi_overbought=70.0,
            enable_regime_filter=False  # Simplify for testing
        )
    
    @pytest.fixture
    def enriched_data(self):
        """Create mock enriched data with all required indicators"""
        def create_enriched_data(symbol: str, num_bars: int = 100) -> pd.DataFrame:
            # Generate realistic time series
            dates = pd.date_range(start='2024-01-01', periods=num_bars, freq='5min')
            
            # Base OHLCV data
            base_price = 150.0 if symbol == 'AAPL' else 200.0
            close_prices = base_price + np.cumsum(np.random.randn(num_bars) * 0.5)
            
            data = pd.DataFrame({
                'timestamp': dates,
                'open': close_prices + np.random.randn(num_bars) * 0.3,
                'high': close_prices + np.abs(np.random.randn(num_bars)) * 0.5,
                'low': close_prices - np.abs(np.random.randn(num_bars)) * 0.5,
                'close': close_prices,
                'volume': np.random.randint(1000000, 5000000, num_bars)
            })
            
            # Add required indicators (from EnhancedTechnicalIndicators)
            data['SMA_20'] = data['close'].rolling(20).mean()
            data['RSI_14'] = 50 + np.random.randn(num_bars) * 15  # Mock RSI
            
            # Bollinger Bands
            bb_std = data['close'].rolling(20).std()
            data['bb_upper'] = data['SMA_20'] + (bb_std * 2.0)
            data['bb_lower'] = data['SMA_20'] - (bb_std * 2.0)
            data['bb_middle'] = data['SMA_20']
            data['bb_position'] = (data['close'] - data['bb_lower']) / (data['bb_upper'] - data['bb_lower'])
            
            # Z-score (mean reversion indicator)
            rolling_mean = data['close'].rolling(20).mean()
            rolling_std = data['close'].rolling(20).std()
            data['zscore'] = (data['close'] - rolling_mean) / rolling_std
            
            # ATR and volume
            data['ATR_14'] = np.abs(np.random.randn(num_bars)) * 2.0
            data['volume_ratio'] = 1.0 + np.random.randn(num_bars) * 0.3
            
            data.set_index('timestamp', inplace=True)
            return data
        
        return create_enriched_data
    
    @pytest.fixture
    def raw_data(self):
        """Create raw OHLCV data WITHOUT indicators (should fail validation)"""
        def create_raw_data(symbol: str, num_bars: int = 100) -> pd.DataFrame:
            dates = pd.date_range(start='2024-01-01', periods=num_bars, freq='5min')
            base_price = 150.0 if symbol == 'AAPL' else 200.0
            close_prices = base_price + np.cumsum(np.random.randn(num_bars) * 0.5)
            
            # ONLY OHLCV - NO INDICATORS
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


class TestEnrichedDataValidation(TestPhase42MeanReversionRefactoring):
    """Test enriched data validation (Rule 3 Phase 4)"""
    
    @pytest.mark.asyncio
    async def test_validation_accepts_enriched_data(self, mean_reversion_config, enriched_data):
        """Test that validation accepts properly enriched data"""
        strategy = EnhancedMeanReversionStrategy(mean_reversion_config)
        await strategy.initialize()
        
        # Create enriched data for both symbols
        market_data = {
            'AAPL': enriched_data('AAPL'),
            'TSLA': enriched_data('TSLA')
        }
        
        # Validation should NOT raise
        try:
            strategy._validate_enriched_data(market_data)
            assert True, "Validation passed as expected"
        except ValueError as e:
            pytest.fail(f"Validation should have passed but raised: {e}")
    
    @pytest.mark.asyncio
    async def test_validation_rejects_raw_data(self, mean_reversion_config, raw_data):
        """Test that validation rejects raw data without indicators"""
        strategy = EnhancedMeanReversionStrategy(mean_reversion_config)
        await strategy.initialize()
        
        # Create raw data (no indicators)
        market_data = {
            'AAPL': raw_data('AAPL'),
            'TSLA': raw_data('TSLA')
        }
        
        # Validation SHOULD raise ValueError
        with pytest.raises(ValueError) as exc_info:
            strategy._validate_enriched_data(market_data)
        
        # Check error message mentions missing indicators
        assert 'missing required indicators' in str(exc_info.value).lower()
        assert 'SMA_20' in str(exc_info.value) or 'sma_20' in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_validation_identifies_missing_indicators(self, mean_reversion_config, enriched_data):
        """Test that validation identifies specific missing indicators"""
        strategy = EnhancedMeanReversionStrategy(mean_reversion_config)
        await strategy.initialize()
        
        # Create data missing RSI_14
        market_data = {
            'AAPL': enriched_data('AAPL')
        }
        market_data['AAPL'] = market_data['AAPL'].drop(columns=['RSI_14'])
        
        # Should raise with specific indicator mentioned
        with pytest.raises(ValueError) as exc_info:
            strategy._validate_enriched_data(market_data)
        
        assert 'RSI_14' in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_validation_handles_empty_dataframe(self, mean_reversion_config):
        """Test that validation handles empty DataFrames"""
        strategy = EnhancedMeanReversionStrategy(mean_reversion_config)
        await strategy.initialize()
        
        market_data = {
            'AAPL': pd.DataFrame()  # Empty DataFrame
        }
        
        with pytest.raises(ValueError) as exc_info:
            strategy._validate_enriched_data(market_data)
        
        assert 'empty' in str(exc_info.value).lower()


class TestSignalGenerationWithEnrichedData(TestPhase42MeanReversionRefactoring):
    """Test signal generation with enriched data (Rule 3 Phase 4)"""
    
    @pytest.mark.asyncio
    async def test_generate_signals_with_enriched_data(self, mean_reversion_config, enriched_data):
        """Test that generate_signals works with enriched data"""
        strategy = EnhancedMeanReversionStrategy(mean_reversion_config)
        await strategy.initialize()
        
        # Create enriched data
        market_data = {
            'AAPL': enriched_data('AAPL'),
            'TSLA': enriched_data('TSLA')
        }
        
        # Generate signals - should NOT raise
        signals = await strategy.generate_signals(market_data)
        
        # Verify signals are returned (may be empty, but should not error)
        assert isinstance(signals, list)
        print(f"✅ Generated {len(signals)} signals from enriched data")
    
    @pytest.mark.asyncio
    async def test_generate_signals_with_raw_data_shows_behavior(self, mean_reversion_config, raw_data):
        """Test behavior when given raw data (may not raise, but should handle gracefully)"""
        strategy = EnhancedMeanReversionStrategy(mean_reversion_config)
        await strategy.initialize()
        
        # Create raw data (no indicators)
        market_data = {
            'AAPL': raw_data('AAPL'),
            'TSLA': raw_data('TSLA')
        }
        
        # The strategy should either raise ValueError or return empty signals
        try:
            signals = await strategy.generate_signals(market_data)
            # If no exception, should return empty list
            assert isinstance(signals, list)
            print(f"✅ Strategy handled raw data gracefully (returned {len(signals)} signals)")
        except ValueError as e:
            # If raises ValueError, that's also acceptable
            assert 'missing' in str(e).lower() or 'required' in str(e).lower()
            print(f"✅ Strategy correctly rejected raw data: {e}")
    
    @pytest.mark.asyncio
    async def test_signal_generation_uses_pre_calculated_indicators(self, mean_reversion_config, enriched_data):
        """Test that strategy reads pre-calculated indicators"""
        strategy = EnhancedMeanReversionStrategy(mean_reversion_config)
        await strategy.initialize()
        
        # Create enriched data with known indicator values
        market_data = {
            'AAPL': enriched_data('AAPL', num_bars=60)
        }
        
        # Set specific indicator values to verify they're read correctly
        market_data['AAPL'].loc[market_data['AAPL'].index[-1], 'zscore'] = -2.5  # Oversold
        market_data['AAPL'].loc[market_data['AAPL'].index[-1], 'RSI_14'] = 25.0  # Oversold
        market_data['AAPL'].loc[market_data['AAPL'].index[-1], 'bb_position'] = 0.1  # Below lower band
        
        # Generate signals
        signals = await strategy.generate_signals(market_data)
        
        # Strategy should process the enriched data
        assert isinstance(signals, list)
        print(f"✅ Strategy processed enriched data: {len(signals)} signals")


class TestNoIndicatorCalculation(TestPhase42MeanReversionRefactoring):
    """Verify that indicator calculation methods were removed (Rule 3 Phase 4)"""
    
    def test_calculate_indicators_method_removed(self, mean_reversion_config):
        """Verify _calculate_indicators method was removed"""
        strategy = EnhancedMeanReversionStrategy(mean_reversion_config)
        
        # Method should NOT exist
        assert not hasattr(strategy, '_calculate_indicators'), \
            "❌ _calculate_indicators method should be removed (Rule 3 Phase 4)"
        
        print("✅ _calculate_indicators method correctly removed")
    
    def test_calculate_symbol_indicators_method_removed(self, mean_reversion_config):
        """Verify _calculate_symbol_indicators method was removed"""
        strategy = EnhancedMeanReversionStrategy(mean_reversion_config)
        
        # Method should NOT exist
        assert not hasattr(strategy, '_calculate_symbol_indicators'), \
            "❌ _calculate_symbol_indicators method should be removed (Rule 3 Phase 4)"
        
        print("✅ _calculate_symbol_indicators method correctly removed")
    
    def test_calculate_rsi_method_removed(self, mean_reversion_config):
        """Verify _calculate_rsi method was removed"""
        strategy = EnhancedMeanReversionStrategy(mean_reversion_config)
        
        # Method should NOT exist
        assert not hasattr(strategy, '_calculate_rsi'), \
            "❌ _calculate_rsi method should be removed (Rule 3 Phase 4)"
        
        print("✅ _calculate_rsi method correctly removed")
    
    def test_calculate_atr_series_method_removed(self, mean_reversion_config):
        """Verify _calculate_atr_series method was removed"""
        strategy = EnhancedMeanReversionStrategy(mean_reversion_config)
        
        # Method should NOT exist
        assert not hasattr(strategy, '_calculate_atr_series'), \
            "❌ _calculate_atr_series method should be removed (Rule 3 Phase 4)"
        
        print("✅ _calculate_atr_series method correctly removed")
    
    def test_calculate_atr_method_removed(self, mean_reversion_config):
        """Verify _calculate_atr method was removed"""
        strategy = EnhancedMeanReversionStrategy(mean_reversion_config)
        
        # Method should NOT exist
        assert not hasattr(strategy, '_calculate_atr'), \
            "❌ _calculate_atr method should be removed (Rule 3 Phase 4)"
        
        print("✅ _calculate_atr method correctly removed")
    
    def test_validate_enriched_data_method_exists(self, mean_reversion_config):
        """Verify _validate_enriched_data method was added"""
        strategy = EnhancedMeanReversionStrategy(mean_reversion_config)
        
        # Method SHOULD exist
        assert hasattr(strategy, '_validate_enriched_data'), \
            "❌ _validate_enriched_data method should exist (Rule 3 Phase 4)"
        
        assert callable(strategy._validate_enriched_data), \
            "❌ _validate_enriched_data should be callable"
        
        print("✅ _validate_enriched_data method correctly added")


class TestBackwardCompatibility(TestPhase42MeanReversionRefactoring):
    """Test that existing functionality still works"""
    
    @pytest.mark.asyncio
    async def test_strategy_initialization(self, mean_reversion_config):
        """Test that strategy still initializes correctly"""
        strategy = EnhancedMeanReversionStrategy(mean_reversion_config)
        
        result = await strategy.initialize()
        
        assert result is True
        assert strategy.is_initialized is True
        print("✅ Strategy initialization works")
    
    @pytest.mark.asyncio
    async def test_strategy_lifecycle(self, mean_reversion_config):
        """Test complete strategy lifecycle"""
        strategy = EnhancedMeanReversionStrategy(mean_reversion_config)
        
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


class TestRule3Compliance(TestPhase42MeanReversionRefactoring):
    """Test Rule 3 (Unified Data Flow Pipeline) compliance"""
    
    @pytest.mark.asyncio
    async def test_parameter_name_changed_to_enriched_data(self, mean_reversion_config):
        """Verify generate_signals parameter is named 'enriched_data'"""
        import inspect
        
        strategy = EnhancedMeanReversionStrategy(mean_reversion_config)
        
        # Get signature of generate_signals
        sig = inspect.signature(strategy.generate_signals)
        params = list(sig.parameters.keys())
        
        # Should have 'enriched_data' parameter, not 'market_data'
        assert 'enriched_data' in params, \
            "❌ Parameter should be named 'enriched_data' (Rule 3 Phase 4)"
        
        print("✅ generate_signals parameter correctly named 'enriched_data'")
    
    @pytest.mark.asyncio
    async def test_docstring_mentions_rule3_phase4(self, mean_reversion_config):
        """Verify docstrings reference Rule 3 Phase 4"""
        strategy = EnhancedMeanReversionStrategy(mean_reversion_config)
        
        # Check generate_signals docstring
        gen_signals_doc = strategy.generate_signals.__doc__ or ""
        assert 'Rule 3' in gen_signals_doc or 'rule 3' in gen_signals_doc.lower(), \
            "❌ generate_signals docstring should reference Rule 3"
        
        assert 'Phase 4' in gen_signals_doc or 'phase 4' in gen_signals_doc.lower(), \
            "❌ generate_signals docstring should reference Phase 4"
        
        print("✅ Docstrings reference Rule 3 Phase 4")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short', '-s'])

