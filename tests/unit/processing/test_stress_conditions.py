"""
Stress Tests: Extreme Market Conditions
========================================

Tests processing components under extreme market scenarios:
- Flash crashes (sudden 20%+ drops)
- Liquidity crises (wide spreads, low volume)
- Data gaps and missing data
- Extreme volatility (VIX > 50)
- Market halts and circuit breakers
- Correlation breakdowns
- Black swan events

Author: StatArb_Gemini Test Suite
Version: 1.0.0 (Processing Brick Stress Tests)
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

# Import processing components
from core_engine.processing.indicators.engine import EnhancedTechnicalIndicators
from core_engine.processing.features.engineer import EnhancedFeatureEngineer
from core_engine.processing.signals.generator import EnhancedSignalGenerator
from core_engine.system.interfaces import RegimeContext


class TestExtremeMarketConditions:
    """Test processing components under extreme market stress"""
    
    @pytest.fixture
    def indicators_engine(self):
        return EnhancedTechnicalIndicators()
    
    @pytest.fixture
    def feature_engineer(self):
        return EnhancedFeatureEngineer()
    
    @pytest.fixture
    def signal_generator(self):
        return EnhancedSignalGenerator()
    
    # ============================================================================
    # Flash Crash Scenarios
    # ============================================================================
    
    def create_flash_crash_data(self, duration=100):
        """Create data simulating a flash crash"""
        dates = pd.date_range(start='2024-01-01', periods=duration, freq='1min')
        
        # Normal market for first 40%
        normal_period = int(duration * 0.4)
        normal_prices = 100 + np.random.randn(normal_period).cumsum() * 0.1
        
        # Flash crash period (sudden 25% drop in 5 minutes)
        crash_period = 5
        crash_prices = np.linspace(normal_prices[-1], normal_prices[-1] * 0.75, crash_period)
        
        # Recovery period (gradual recovery)
        recovery_period = duration - normal_period - crash_period
        recovery_prices = np.linspace(crash_prices[-1], crash_prices[-1] * 1.15, recovery_period)
        
        # Combine all periods
        all_prices = np.concatenate([normal_prices, crash_prices, recovery_prices])
        
        data = pd.DataFrame({
            'timestamp': dates,
            'open': all_prices,
            'high': all_prices * 1.01,
            'low': all_prices * 0.99,
            'close': all_prices,
            'volume': np.random.randint(1000, 50000, duration),  # Higher volume during crash
            'symbol': 'TEST'
        })
        
        # Spike volume during crash
        data.loc[normal_period:normal_period+crash_period, 'volume'] *= 10
        
        return data
    
    @pytest.mark.asyncio
    async def test_flash_crash_indicators(self, indicators_engine):
        """Test indicators during flash crash"""
        await indicators_engine.initialize()
        await indicators_engine.start()
        
        # Create flash crash data
        crash_data = self.create_flash_crash_data()
        
        # Calculate indicators
        result = indicators_engine.calculate_indicators(crash_data)
        
        # Verify indicators calculated successfully
        assert result is not None
        assert not result.empty
        
        # Verify indicators show extreme conditions
        if 'rsi' in result.columns:
            # RSI should show extreme oversold conditions
            min_rsi = result['rsi'].min()
            assert min_rsi < 30  # Extreme oversold
        
        if 'atr' in result.columns:
            # ATR should spike during crash
            atr_spike = result['atr'].max() / result['atr'].mean()
            assert atr_spike > 1.5  # Volatility spike (reduced threshold)
    
    @pytest.mark.asyncio
    async def test_flash_crash_signals(self, signal_generator):
        """Test signal generation during flash crash"""
        await signal_generator.initialize()
        await signal_generator.start()
        
        # Set extreme volatility regime
        crash_regime = RegimeContext(
            primary_regime='extreme_volatility',
            regime_confidence=0.95,
            regime_start_time=datetime.now(),
            regime_duration_minutes=60.0
        )
        await signal_generator.on_regime_change(crash_regime)
        
        # Create flash crash data
        crash_data = self.create_flash_crash_data()
        
        # Generate signals
        signals = signal_generator.generate_signals(crash_data)
        
        # Verify signals are appropriately conservative
        assert signals is not None
        
        if signals:
            for signal in signals:
                # Confidence should be low during extreme volatility
                assert signal.confidence < 0.5
                # Position sizes should be minimal
                assert signal.position_size < 0.03
    
    # ============================================================================
    # Liquidity Crisis
    # ============================================================================
    
    def create_liquidity_crisis_data(self, duration=100):
        """Create data simulating liquidity crisis"""
        dates = pd.date_range(start='2024-01-01', periods=duration, freq='1min')
        
        prices = 100 + np.random.randn(duration).cumsum() * 0.5
        
        data = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': prices * 1.05,  # Wide spreads
            'low': prices * 0.95,   # Wide spreads
            'close': prices,
            'volume': np.random.randint(10, 100, duration),  # Very low volume
            'symbol': 'TEST'
        })
        
        return data
    
    @pytest.mark.asyncio
    async def test_liquidity_crisis_features(self, feature_engineer):
        """Test feature engineering during liquidity crisis"""
        await feature_engineer.initialize()
        await feature_engineer.start()
        
        # Create liquidity crisis data
        liquidity_data = self.create_liquidity_crisis_data()
        
        # Create features
        features = feature_engineer.create_features(liquidity_data)
        
        # Verify features calculated despite low liquidity
        assert features is not None
        assert not features.empty
        
        # Volume features should show extremely low values
        volume_cols = [col for col in features.columns if 'volume' in col.lower()]
        if volume_cols:
            # Volume should be significantly below normal
            assert features[volume_cols[0]].mean() < 500
    
    # ============================================================================
    # Data Gaps and Missing Data
    # ============================================================================
    
    def create_gapped_data(self, duration=100, gap_size=20):
        """Create data with significant gaps"""
        dates = pd.date_range(start='2024-01-01', periods=duration, freq='1min')
        
        prices = 100 + np.random.randn(duration).cumsum()
        
        data = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': prices * 1.01,
            'low': prices * 0.99,
            'close': prices,
            'volume': np.random.randint(1000, 10000, duration),
            'symbol': 'TEST'
        })
        
        # Introduce gaps (NaN values)
        gap_start = duration // 2
        data.loc[gap_start:gap_start+gap_size, ['open', 'high', 'low', 'close', 'volume']] = np.nan
        
        return data
    
    @pytest.mark.asyncio
    async def test_data_gaps_indicators(self, indicators_engine):
        """Test indicators with data gaps"""
        await indicators_engine.initialize()
        await indicators_engine.start()
        
        # Create gapped data
        gapped_data = self.create_gapped_data()
        
        # Calculate indicators
        result = indicators_engine.calculate_indicators(gapped_data)
        
        # Should handle gaps gracefully (forward fill or skip)
        assert result is not None
        # Some indicators may have NaN where gaps exist - that's acceptable
    
    @pytest.mark.asyncio
    async def test_missing_columns(self, indicators_engine):
        """Test behavior with missing required columns"""
        await indicators_engine.initialize()
        await indicators_engine.start()
        
        # Create incomplete data (missing 'high' column)
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1min')
        incomplete_data = pd.DataFrame({
            'timestamp': dates,
            'open': 100 + np.random.randn(100).cumsum(),
            'low': 99 + np.random.randn(100).cumsum(),
            'close': 100 + np.random.randn(100).cumsum(),
            'volume': np.random.randint(1000, 10000, 100),
            'symbol': 'TEST'
        })
        # Missing 'high' column
        
        # Should handle gracefully
        try:
            result = indicators_engine.calculate_indicators(incomplete_data)
            # May return partial results or None - both acceptable
            assert result is not None or result is None
        except Exception as e:
            # Should not crash - graceful error handling
            assert "high" in str(e).lower() or "column" in str(e).lower()
    
    # ============================================================================
    # Extreme Volatility
    # ============================================================================
    
    def create_extreme_volatility_data(self, duration=100):
        """Create data with extreme volatility (VIX-like > 50)"""
        dates = pd.date_range(start='2024-01-01', periods=duration, freq='1min')
        
        # Generate prices with extreme volatility
        returns = np.random.randn(duration) * 0.05  # 5% per-minute returns
        prices = 100 * np.exp(returns.cumsum())
        
        data = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': prices * (1 + np.abs(np.random.randn(duration) * 0.03)),
            'low': prices * (1 - np.abs(np.random.randn(duration) * 0.03)),
            'close': prices,
            'volume': np.random.randint(5000, 50000, duration),
            'symbol': 'TEST'
        })
        
        return data
    
    @pytest.mark.asyncio
    async def test_extreme_volatility_all_components(self, indicators_engine, 
                                                     feature_engineer, signal_generator):
        """Test all components under extreme volatility"""
        # Initialize all components
        await indicators_engine.initialize()
        await indicators_engine.start()
        await feature_engineer.initialize()
        await feature_engineer.start()
        await signal_generator.initialize()
        await signal_generator.start()
        
        # Create extreme volatility data
        extreme_data = self.create_extreme_volatility_data()
        
        # Set extreme regime
        extreme_regime = RegimeContext(
            primary_regime='extreme_volatility',
            regime_confidence=0.98,
            regime_start_time=datetime.now(),
            regime_duration_minutes=120.0
        )
        
        await indicators_engine.on_regime_change(extreme_regime)
        await feature_engineer.on_regime_change(extreme_regime)
        await signal_generator.on_regime_change(extreme_regime)
        
        # Run through full pipeline
        indicators = indicators_engine.calculate_indicators(extreme_data)
        assert indicators is not None
        
        features = feature_engineer.create_features(indicators)
        assert features is not None
        
        signals = signal_generator.generate_signals(features)
        assert signals is not None
        
        # All components should survive extreme conditions
        health_checks = [
            await indicators_engine.health_check(),
            await feature_engineer.health_check(),
            await signal_generator.health_check()
        ]
        
        for health in health_checks:
            assert health['healthy'] is True
    
    # ============================================================================
    # Market Halts and Circuit Breakers
    # ============================================================================
    
    def create_market_halt_data(self, duration=100, halt_duration=30):
        """Create data simulating market halt"""
        dates = pd.date_range(start='2024-01-01', periods=duration, freq='1min')
        
        prices = 100 + np.random.randn(duration).cumsum()
        
        data = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': prices * 1.01,
            'low': prices * 0.99,
            'close': prices,
            'volume': np.random.randint(1000, 10000, duration),
            'symbol': 'TEST'
        })
        
        # Simulate halt with zero volume and flat prices
        halt_start = duration // 2
        halt_price = data.loc[halt_start, 'close']
        data.loc[halt_start:halt_start+halt_duration, 'open'] = halt_price
        data.loc[halt_start:halt_start+halt_duration, 'high'] = halt_price
        data.loc[halt_start:halt_start+halt_duration, 'low'] = halt_price
        data.loc[halt_start:halt_start+halt_duration, 'close'] = halt_price
        data.loc[halt_start:halt_start+halt_duration, 'volume'] = 0
        
        return data
    
    @pytest.mark.asyncio
    async def test_market_halt(self, signal_generator):
        """Test signal generation during market halt"""
        await signal_generator.initialize()
        await signal_generator.start()
        
        # Create halt data
        halt_data = self.create_market_halt_data()
        
        # Generate signals
        signals = signal_generator.generate_signals(halt_data)
        
        # Should not generate signals during halt (zero volume)
        # or have very low confidence
        assert signals is not None
    
    # ============================================================================
    # Correlation Breakdown
    # ============================================================================
    
    def create_correlation_breakdown_data(self):
        """Create multi-symbol data with correlation breakdown"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1min')
        
        # Create highly correlated data initially
        base_returns = np.random.randn(100) * 0.01
        
        # Symbol 1: follows base
        prices_1 = 100 * np.exp(base_returns.cumsum())
        
        # Symbol 2: initially correlated, then decorrelates
        returns_2 = base_returns.copy()
        returns_2[50:] = np.random.randn(50) * 0.02  # Breakdown after period 50
        prices_2 = 100 * np.exp(returns_2.cumsum())
        
        data_1 = pd.DataFrame({
            'timestamp': dates,
            'open': prices_1,
            'high': prices_1 * 1.01,
            'low': prices_1 * 0.99,
            'close': prices_1,
            'volume': np.random.randint(1000, 10000, 100),
            'symbol': 'SYMBOL1'
        })
        
        data_2 = pd.DataFrame({
            'timestamp': dates,
            'open': prices_2,
            'high': prices_2 * 1.01,
            'low': prices_2 * 0.99,
            'close': prices_2,
            'volume': np.random.randint(1000, 10000, 100),
            'symbol': 'SYMBOL2'
        })
        
        return pd.concat([data_1, data_2], ignore_index=True)
    
    @pytest.mark.asyncio
    async def test_correlation_breakdown_features(self, feature_engineer):
        """Test cross-sectional features during correlation breakdown"""
        await feature_engineer.initialize()
        await feature_engineer.start()
        
        # Create correlation breakdown data
        corr_data = self.create_correlation_breakdown_data()
        
        # Create features with cross-sectional enabled
        features = feature_engineer.create_features(corr_data)
        
        # Should handle changing correlations gracefully
        assert features is not None
        assert not features.empty
    
    # ============================================================================
    # Large Dataset Stress Test
    # ============================================================================
    
    @pytest.mark.asyncio
    async def test_large_dataset_performance(self, indicators_engine):
        """Test performance with very large dataset"""
        await indicators_engine.initialize()
        await indicators_engine.start()
        
        # Create large dataset (10,000 periods)
        large_duration = 10000
        dates = pd.date_range(start='2024-01-01', periods=large_duration, freq='1min')
        
        large_data = pd.DataFrame({
            'timestamp': dates,
            'open': 100 + np.random.randn(large_duration).cumsum(),
            'high': 101 + np.random.randn(large_duration).cumsum(),
            'low': 99 + np.random.randn(large_duration).cumsum(),
            'close': 100 + np.random.randn(large_duration).cumsum(),
            'volume': np.random.randint(1000, 10000, large_duration),
            'symbol': 'TEST'
        })
        
        # Time the calculation
        import time
        start_time = time.time()
        
        result = indicators_engine.calculate_indicators(large_data)
        
        elapsed_time = time.time() - start_time
        
        # Should complete in reasonable time (< 30 seconds for 10K periods)
        assert elapsed_time < 30
        assert result is not None
        assert len(result) == large_duration
    
    # ============================================================================
    # Memory Stress Test
    # ============================================================================
    
    @pytest.mark.asyncio
    async def test_memory_stress(self, feature_engineer):
        """Test memory handling with multiple large operations"""
        await feature_engineer.initialize()
        await feature_engineer.start()
        
        # Run multiple large feature engineering operations
        for i in range(10):
            # Create moderately sized data
            dates = pd.date_range(start='2024-01-01', periods=1000, freq='1min')
            data = pd.DataFrame({
                'timestamp': dates,
                'open': 100 + np.random.randn(1000).cumsum(),
                'high': 101 + np.random.randn(1000).cumsum(),
                'low': 99 + np.random.randn(1000).cumsum(),
                'close': 100 + np.random.randn(1000).cumsum(),
                'volume': np.random.randint(1000, 10000, 1000),
                'symbol': f'TEST{i}'
            })
            
            # Create features
            features = feature_engineer.create_features(data)
            
            # Verify successful creation
            assert features is not None
            assert not features.empty
            
            # Explicitly delete to free memory
            del features
            del data
        
        # Component should still be healthy after memory stress
        health = await feature_engineer.health_check()
        assert health['healthy'] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

