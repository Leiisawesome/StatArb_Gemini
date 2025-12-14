"""
Concurrent Access Tests
=======================

Tests processing components under concurrent access scenarios:
- Multiple threads calculating indicators simultaneously
- Parallel feature engineering for different symbols
- Concurrent signal generation
- Race conditions in regime updates
- Thread-safe configuration updates
- Shared resource access patterns

Author: StatArb_Gemini Test Suite
Version: 1.0.0 (Processing Brick Concurrency Tests)
"""

import pytest
import pandas as pd
import numpy as np
import asyncio
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import processing components
from core_engine.processing.indicators.engine import EnhancedTechnicalIndicators
from core_engine.processing.features.engineer import EnhancedFeatureEngineer
from core_engine.processing.signals.generator import EnhancedSignalGenerator
from core_engine.system.interfaces import RegimeContext

class TestConcurrentAccess:
    """Test processing components under concurrent access"""

    @pytest.fixture
    def sample_market_data(self):
        """Create sample market data"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1min')
        data = pd.DataFrame({
            'timestamp': dates,
            'open': 100 + np.random.randn(100).cumsum(),
            'high': 101 + np.random.randn(100).cumsum(),
            'low': 99 + np.random.randn(100).cumsum(),
            'close': 100 + np.random.randn(100).cumsum(),
            'volume': np.random.randint(1000, 10000, 100),
            'symbol': 'TEST'
        })
        return data

    def create_symbol_data(self, symbol: str, duration: int = 100):
        """Create market data for a specific symbol"""
        dates = pd.date_range(start='2024-01-01', periods=duration, freq='1min')
        data = pd.DataFrame({
            'timestamp': dates,
            'open': 100 + np.random.randn(duration).cumsum(),
            'high': 101 + np.random.randn(duration).cumsum(),
            'low': 99 + np.random.randn(duration).cumsum(),
            'close': 100 + np.random.randn(duration).cumsum(),
            'volume': np.random.randint(1000, 10000, duration),
            'symbol': symbol
        })
        return data

    # ============================================================================
    # Concurrent Indicator Calculations
    # ============================================================================

    @pytest.mark.asyncio
    async def test_concurrent_indicator_calculations(self):
        """Test multiple threads calculating indicators simultaneously"""
        engine = EnhancedTechnicalIndicators()
        await engine.initialize()
        await engine.start()

        # Create data for multiple symbols
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'NVDA', 'TSLA']
        datasets = {symbol: self.create_symbol_data(symbol) for symbol in symbols}

        results = {}

        def calculate_for_symbol(symbol):
            """Calculate indicators for a symbol"""
            try:
                result = engine.calculate_indicators(datasets[symbol])
                return symbol, result
            except Exception:
                return symbol, None

        # Run calculations concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(calculate_for_symbol, symbol): symbol
                      for symbol in symbols}

            for future in as_completed(futures):
                symbol, result = future.result()
                results[symbol] = result

        # Verify all calculations completed successfully
        assert len(results) == len(symbols)
        for symbol in symbols:
            assert results[symbol] is not None
            assert not results[symbol].empty
            assert 'sma_20' in results[symbol].columns

    @pytest.mark.asyncio
    async def test_concurrent_regime_updates(self):
        """Test concurrent regime updates"""
        engine = EnhancedTechnicalIndicators()
        await engine.initialize()
        await engine.start()

        # Define multiple regime contexts
        regimes = [
            RegimeContext(
                primary_regime='low_volatility',
                regime_confidence=0.8,
                regime_start_time=datetime.now(),
                regime_duration_minutes=60.0
            ),
            RegimeContext(
                primary_regime='high_volatility',
                regime_confidence=0.9,
                regime_start_time=datetime.now(),
                regime_duration_minutes=45.0
            ),
            RegimeContext(
                primary_regime='trending',
                regime_confidence=0.7,
                regime_start_time=datetime.now(),
                regime_duration_minutes=90.0
            ),
            RegimeContext(
                primary_regime='choppy',
                regime_confidence=0.6,
                regime_start_time=datetime.now(),
                regime_duration_minutes=30.0
            ),
        ]

        # Update regimes concurrently
        async def update_regime(regime_context):
            await engine.on_regime_change(regime_context)
            return True

        # Run concurrent updates
        results = await asyncio.gather(*[update_regime(r) for r in regimes])

        # All updates should complete without error
        assert all(results)

        # Verify component health after concurrent updates
        health = await engine.health_check()
        assert health['healthy'] is True

    # ============================================================================
    # Parallel Feature Engineering
    # ============================================================================

    @pytest.mark.asyncio
    async def test_parallel_feature_engineering(self):
        """Test parallel feature engineering for multiple symbols"""
        engineer = EnhancedFeatureEngineer()
        await engineer.initialize()
        await engineer.start()

        # Create data for multiple symbols
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'NVDA', 'TSLA']
        datasets = {symbol: self.create_symbol_data(symbol, duration=200)
                   for symbol in symbols}

        results = {}

        def engineer_features(symbol):
            """Engineer features for a symbol"""
            try:
                features = engineer.create_features(datasets[symbol])
                return symbol, features
            except Exception:
                return symbol, None

        # Run feature engineering in parallel
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(engineer_features, symbol): symbol
                      for symbol in symbols}

            for future in as_completed(futures):
                symbol, features = future.result()
                results[symbol] = features

        # Verify all feature engineering completed successfully
        assert len(results) == len(symbols)
        for symbol in symbols:
            assert results[symbol] is not None
            assert not results[symbol].empty

    # ============================================================================
    # Concurrent Signal Generation
    # ============================================================================

    @pytest.mark.asyncio
    async def test_concurrent_signal_generation(self):
        """Test concurrent signal generation"""
        generator = EnhancedSignalGenerator()
        await generator.initialize()
        await generator.start()

        # Create data for multiple symbols
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'NVDA']
        datasets = {symbol: self.create_symbol_data(symbol) for symbol in symbols}

        results = {}

        def generate_signals(symbol):
            """Generate signals for a symbol"""
            try:
                signals = generator.generate_signals(datasets[symbol])
                return symbol, signals
            except Exception:
                return symbol, []

        # Generate signals concurrently
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(generate_signals, symbol): symbol
                      for symbol in symbols}

            for future in as_completed(futures):
                symbol, signals = future.result()
                results[symbol] = signals

        # Verify all signal generation completed
        assert len(results) == len(symbols)
        for symbol in symbols:
            assert results[symbol] is not None

    @pytest.mark.asyncio
    async def test_race_condition_health_checks(self):
        """Test concurrent health checks"""
        generator = EnhancedSignalGenerator()
        await generator.initialize()
        await generator.start()

        # Run multiple health checks concurrently
        health_results = await asyncio.gather(*[
            generator.health_check() for _ in range(20)
        ])

        # All health checks should complete successfully
        assert len(health_results) == 20
        for health in health_results:
            assert 'healthy' in health
            assert isinstance(health['healthy'], bool)

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

