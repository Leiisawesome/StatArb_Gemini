#!/usr/bin/env python3
"""
Unit Tests for Phase 3 Enhanced Processing Components
====================================================

Tests for the enhanced processing pipeline components with ISystemComponent integration:
- EnhancedTechnicalIndicators
- EnhancedFeatureEngineer  
- EnhancedSignalGenerator

Author: StatArb_Gemini Testing Team
Version: 1.0.0 (Phase 3 Testing)
"""

import pytest
import pytest_asyncio
import pandas as pd
import numpy as np
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import asyncio

# Import enhanced processing components
from core_engine.processing.indicators.engine import (
    EnhancedTechnicalIndicators, EnhancedIndicatorConfig
)
from core_engine.processing.features.engineer import (
    EnhancedFeatureEngineer, FeatureConfig
)
from core_engine.processing.signals.generator import (
    EnhancedSignalGenerator, SignalConfig
)


class TestEnhancedTechnicalIndicatorsBasics:
    """Test suite for Enhanced Technical Indicators basic functionality"""

    @pytest_asyncio.fixture
    async def indicators_config(self):
        """Fixture for indicators configuration"""
        return EnhancedIndicatorConfig(
            enable_caching=True,
            parallel_processing=False
        )

    @pytest_asyncio.fixture
    async def indicators_engine(self, indicators_config):
        """Fixture for indicators engine"""
        engine = EnhancedTechnicalIndicators(indicators_config)
        yield engine
        if engine.is_operational:
            await engine.stop()

    @pytest_asyncio.fixture
    async def sample_ohlcv_data(self):
        """Fixture for sample OHLCV data"""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(100) * 0.02)
        
        return pd.DataFrame({
            'symbol': ['AAPL'] * 100,
            'timestamp': dates,
            'open': prices * (1 + np.random.randn(100) * 0.001),
            'high': prices * (1 + np.abs(np.random.randn(100)) * 0.002),
            'low': prices * (1 - np.abs(np.random.randn(100)) * 0.002),
            'close': prices,
            'volume': np.random.randint(1000, 10000, 100)
        })

    @pytest.mark.asyncio
    async def test_indicators_creation(self, indicators_config):
        """Test indicators engine creation"""
        engine = EnhancedTechnicalIndicators(indicators_config)
        assert engine is not None
        assert engine.component_id is not None
        assert not engine.is_initialized
        assert not engine.is_operational

    @pytest.mark.asyncio
    async def test_indicators_initialization(self, indicators_engine):
        """Test indicators engine initialization"""
        result = await indicators_engine.initialize()
        assert result is True
        assert indicators_engine.is_initialized
        assert not indicators_engine.is_operational

    @pytest.mark.asyncio
    async def test_indicators_lifecycle(self, indicators_engine):
        """Test indicators engine lifecycle"""
        # Initialize
        init_result = await indicators_engine.initialize()
        assert init_result is True
        assert indicators_engine.is_initialized

        # Start
        start_result = await indicators_engine.start()
        assert start_result is True
        assert indicators_engine.is_operational

        # Stop
        stop_result = await indicators_engine.stop()
        assert stop_result is True
        assert not indicators_engine.is_operational

    @pytest.mark.asyncio
    async def test_indicators_health_check(self, indicators_engine):
        """Test indicators engine health check"""
        await indicators_engine.initialize()
        await indicators_engine.start()
        
        health = await indicators_engine.health_check()
        assert health['healthy'] is True
        assert health['component_type'] == 'EnhancedTechnicalIndicators'
        assert health['initialized'] is True
        assert health['operational'] is True

    @pytest.mark.asyncio
    async def test_indicators_status(self, indicators_engine):
        """Test indicators engine status reporting"""
        await indicators_engine.initialize()
        
        status = indicators_engine.get_status()
        assert status['component_type'] == 'EnhancedTechnicalIndicators'
        assert status['initialized'] is True
        assert 'configuration' in status
        assert 'health_metrics' in status

    @pytest.mark.asyncio
    async def test_indicators_calculation(self, indicators_engine, sample_ohlcv_data):
        """Test indicators calculation functionality"""
        await indicators_engine.initialize()
        await indicators_engine.start()
        
        # Test calculation
        result = indicators_engine.calculate_indicators(sample_ohlcv_data)
        assert result is not None
        assert len(result) == len(sample_ohlcv_data)
        assert len(result.columns) > len(sample_ohlcv_data.columns)


class TestEnhancedFeatureEngineerBasics:
    """Test suite for Enhanced Feature Engineer basic functionality"""

    @pytest_asyncio.fixture
    async def features_config(self):
        """Fixture for features configuration"""
        return FeatureConfig(
            use_normalization=True,
            normalization_method='robust'
        )

    @pytest_asyncio.fixture
    async def feature_engineer(self, features_config):
        """Fixture for feature engineer"""
        engineer = EnhancedFeatureEngineer(features_config)
        yield engineer
        if engineer.is_operational:
            await engineer.stop()

    @pytest_asyncio.fixture
    async def sample_indicators_data(self):
        """Fixture for sample indicators data"""
        dates = pd.date_range('2024-01-01', periods=50, freq='D')
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(50) * 0.02)
        
        return pd.DataFrame({
            'symbol': ['AAPL'] * 50,
            'timestamp': dates,
            'open': prices * (1 + np.random.randn(50) * 0.001),
            'high': prices * (1 + np.abs(np.random.randn(50)) * 0.002),
            'low': prices * (1 - np.abs(np.random.randn(50)) * 0.002),
            'close': prices,
            'volume': np.random.randint(1000, 10000, 50),
            'rsi': 50 + np.random.randn(50) * 10,
            'sma_20': prices * (1 + np.random.randn(50) * 0.001)
        })

    @pytest.mark.asyncio
    async def test_features_creation(self, features_config):
        """Test feature engineer creation"""
        engineer = EnhancedFeatureEngineer(features_config)
        assert engineer is not None
        assert engineer.component_id is not None
        assert not engineer.is_initialized
        assert not engineer.is_operational

    @pytest.mark.asyncio
    async def test_features_initialization(self, feature_engineer):
        """Test feature engineer initialization"""
        result = await feature_engineer.initialize()
        assert result is True
        assert feature_engineer.is_initialized
        assert not feature_engineer.is_operational

    @pytest.mark.asyncio
    async def test_features_lifecycle(self, feature_engineer):
        """Test feature engineer lifecycle"""
        # Initialize
        init_result = await feature_engineer.initialize()
        assert init_result is True
        assert feature_engineer.is_initialized

        # Start
        start_result = await feature_engineer.start()
        assert start_result is True
        assert feature_engineer.is_operational

        # Stop
        stop_result = await feature_engineer.stop()
        assert stop_result is True
        assert not feature_engineer.is_operational

    @pytest.mark.asyncio
    async def test_features_health_check(self, feature_engineer):
        """Test feature engineer health check"""
        await feature_engineer.initialize()
        await feature_engineer.start()
        
        health = await feature_engineer.health_check()
        assert health['healthy'] is True
        assert health['component_type'] == 'EnhancedFeatureEngineer'
        assert health['initialized'] is True
        assert health['operational'] is True

    @pytest.mark.asyncio
    async def test_features_status(self, feature_engineer):
        """Test feature engineer status reporting"""
        await feature_engineer.initialize()
        
        status = feature_engineer.get_status()
        assert status['component_type'] == 'EnhancedFeatureEngineer'
        assert status['initialized'] is True
        assert 'configuration' in status
        assert 'health_metrics' in status

    @pytest.mark.asyncio
    async def test_features_creation_functionality(self, feature_engineer, sample_indicators_data):
        """Test feature creation functionality"""
        await feature_engineer.initialize()
        await feature_engineer.start()
        
        # Test feature creation
        result = feature_engineer.create_features(sample_indicators_data)
        assert result is not None
        assert len(result) == len(sample_indicators_data)
        assert len(result.columns) > len(sample_indicators_data.columns)


class TestEnhancedSignalGeneratorBasics:
    """Test suite for Enhanced Signal Generator basic functionality"""

    @pytest_asyncio.fixture
    async def signals_config(self):
        """Fixture for signals configuration"""
        return SignalConfig()

    @pytest_asyncio.fixture
    async def signal_generator(self, signals_config):
        """Fixture for signal generator"""
        generator = EnhancedSignalGenerator(signals_config)
        yield generator
        if generator.is_operational:
            await generator.stop()

    @pytest_asyncio.fixture
    async def sample_features_data(self):
        """Fixture for sample features data"""
        dates = pd.date_range('2024-01-01', periods=50, freq='D')
        np.random.seed(42)
        
        return pd.DataFrame({
            'symbol': ['AAPL'] * 50,
            'timestamp': dates,
            'close': 100 + np.cumsum(np.random.randn(50) * 0.02),
            'rsi': 50 + np.random.randn(50) * 15,
            'macd': np.random.randn(50) * 0.5,
            'bb_upper': 105 + np.random.randn(50) * 2,
            'bb_lower': 95 + np.random.randn(50) * 2,
            'volume': np.random.randint(1000, 10000, 50),
            'volume_sma': np.random.randint(2000, 8000, 50)
        })

    @pytest.mark.asyncio
    async def test_signals_creation(self, signals_config):
        """Test signal generator creation"""
        generator = EnhancedSignalGenerator(signals_config)
        assert generator is not None
        assert generator.component_id is not None
        assert not generator.is_initialized
        assert not generator.is_operational

    @pytest.mark.asyncio
    async def test_signals_initialization(self, signal_generator):
        """Test signal generator initialization"""
        result = await signal_generator.initialize()
        assert result is True
        assert signal_generator.is_initialized
        assert not signal_generator.is_operational

    @pytest.mark.asyncio
    async def test_signals_lifecycle(self, signal_generator):
        """Test signal generator lifecycle"""
        # Initialize
        init_result = await signal_generator.initialize()
        assert init_result is True
        assert signal_generator.is_initialized

        # Start
        start_result = await signal_generator.start()
        assert start_result is True
        assert signal_generator.is_operational

        # Stop
        stop_result = await signal_generator.stop()
        assert stop_result is True
        assert not signal_generator.is_operational

    @pytest.mark.asyncio
    async def test_signals_health_check(self, signal_generator):
        """Test signal generator health check"""
        await signal_generator.initialize()
        await signal_generator.start()
        
        health = await signal_generator.health_check()
        assert health['healthy'] is True
        assert health['component_type'] == 'EnhancedSignalGenerator'
        assert health['initialized'] is True
        assert health['operational'] is True

    @pytest.mark.asyncio
    async def test_signals_status(self, signal_generator):
        """Test signal generator status reporting"""
        await signal_generator.initialize()
        
        status = signal_generator.get_status()
        assert status['component_type'] == 'EnhancedSignalGenerator'
        assert status['initialized'] is True
        assert 'configuration' in status
        assert 'health_metrics' in status

    @pytest.mark.asyncio
    async def test_signals_generation_functionality(self, signal_generator, sample_features_data):
        """Test signal generation functionality"""
        await signal_generator.initialize()
        await signal_generator.start()
        
        # Test signal generation
        result = signal_generator.generate_signals(sample_features_data)
        assert result is not None
        assert isinstance(result, list)
        # Note: May return 0 signals with random test data, which is expected


class TestIntegrationWorkflow:
    """Test suite for integration of enhanced processing components"""

    @pytest_asyncio.fixture
    async def integrated_components(self):
        """Fixture for integrated processing components"""
        indicators_config = EnhancedIndicatorConfig(enable_caching=True)
        features_config = FeatureConfig(use_normalization=True)
        signals_config = SignalConfig()

        indicators = EnhancedTechnicalIndicators(indicators_config)
        features = EnhancedFeatureEngineer(features_config)
        signals = EnhancedSignalGenerator(signals_config)

        yield indicators, features, signals

        # Cleanup
        for component in [indicators, features, signals]:
            if component.is_operational:
                await component.stop()

    @pytest_asyncio.fixture
    async def sample_market_data(self):
        """Fixture for sample market data"""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(100) * 0.02)
        
        return pd.DataFrame({
            'symbol': ['AAPL'] * 100,
            'timestamp': dates,
            'open': prices * (1 + np.random.randn(100) * 0.001),
            'high': prices * (1 + np.abs(np.random.randn(100)) * 0.002),
            'low': prices * (1 - np.abs(np.random.randn(100)) * 0.002),
            'close': prices,
            'volume': np.random.randint(1000, 10000, 100)
        })

    @pytest.mark.asyncio
    async def test_component_integration(self, integrated_components, sample_market_data):
        """Test basic integration of all processing components"""
        indicators, features, signals = integrated_components

        # Initialize all components
        await indicators.initialize()
        await features.initialize()
        await signals.initialize()

        assert indicators.is_initialized
        assert features.is_initialized
        assert signals.is_initialized

        # Start all components
        await indicators.start()
        await features.start()
        await signals.start()

        assert indicators.is_operational
        assert features.is_operational
        assert signals.is_operational

        # Test processing pipeline
        # Step 1: Calculate indicators
        indicators_data = indicators.calculate_indicators(sample_market_data)
        assert indicators_data is not None
        assert len(indicators_data) == len(sample_market_data)

        # Step 2: Engineer features
        features_data = features.create_features(indicators_data)
        assert features_data is not None
        assert len(features_data) == len(indicators_data)

        # Step 3: Generate signals
        signals_data = signals.generate_signals(features_data)
        assert signals_data is not None
        assert isinstance(signals_data, list)

        # Stop all components
        await indicators.stop()
        await features.stop()
        await signals.stop()

        assert not indicators.is_operational
        assert not features.is_operational
        assert not signals.is_operational

    @pytest.mark.asyncio
    async def test_health_checks_all_components(self, integrated_components):
        """Test health checks across all integrated components"""
        indicators, features, signals = integrated_components

        await indicators.initialize()
        await features.initialize()
        await signals.initialize()

        # Start components for health check
        await indicators.start()
        await features.start()
        await signals.start()

        # Test health checks
        indicators_health = await indicators.health_check()
        features_health = await features.health_check()
        signals_health = await signals.health_check()

        assert indicators_health['healthy'] is True
        assert features_health['healthy'] is True
        assert signals_health['healthy'] is True

        # Cleanup
        await indicators.stop()
        await features.stop()
        await signals.stop()

        assert indicators_health['component_type'] == 'EnhancedTechnicalIndicators'
        assert features_health['component_type'] == 'EnhancedFeatureEngineer'
        assert signals_health['component_type'] == 'EnhancedSignalGenerator'

    @pytest.mark.asyncio
    async def test_processing_pipeline_performance(self, integrated_components, sample_market_data):
        """Test processing pipeline performance metrics"""
        indicators, features, signals = integrated_components

        # Initialize and start all components
        for component in [indicators, features, signals]:
            await component.initialize()
            await component.start()

        # Process data and check performance metrics
        indicators_data = indicators.calculate_indicators(sample_market_data)
        features_data = features.create_features(indicators_data)
        signals_data = signals.generate_signals(features_data)

        # Check that all components have performance metrics
        for component in [indicators, features, signals]:
            status = component.get_status()
            assert 'health_metrics' in status
            assert 'performance_metrics' in status['health_metrics']

        # Cleanup
        for component in [indicators, features, signals]:
            await component.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
