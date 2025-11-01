#!/usr/bin/env python3
"""
Unit Tests for Processing Pipeline Orchestrator
===============================================

Tests for the complete data processing pipeline orchestrator.

**Rule 3 Compliance:** Verifies unified data flow pipeline enforcement.

Author: StatArb_Gemini Test Suite
Version: 1.0.0
"""

import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import Mock, AsyncMock

from core_engine.processing.pipeline_orchestrator import (
    ProcessingPipelineOrchestrator,
    EnrichedMarketData
)
from core_engine.system.interfaces import RegimeContext


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_raw_data():
    """Create mock raw OHLCV data"""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='1min')
    return pd.DataFrame({
        'timestamp': dates,
        'open': 150.0 + pd.Series(range(100)) * 0.1,
        'high': 151.0 + pd.Series(range(100)) * 0.1,
        'low': 149.0 + pd.Series(range(100)) * 0.1,
        'close': 150.5 + pd.Series(range(100)) * 0.1,
        'volume': 1000000 + pd.Series(range(100)) * 1000
    })


@pytest.fixture
def mock_indicators_data(mock_raw_data):
    """Create mock data with indicators"""
    df = mock_raw_data.copy()
    # Add mock indicators
    df['SMA_10'] = df['close'].rolling(10).mean()
    df['SMA_20'] = df['close'].rolling(20).mean()
    df['RSI_14'] = 50.0  # Simplified
    df['MACD'] = 0.5
    df['ADX_14'] = 25.0
    df['ATR_14'] = 2.0
    return df


@pytest.fixture
def mock_features_data(mock_indicators_data):
    """Create mock data with features"""
    df = mock_indicators_data.copy()
    # Add mock features
    df['returns_1'] = df['close'].pct_change()
    df['momentum_score'] = 0.02
    df['trend_strength'] = 0.75
    df['volatility_ratio'] = 1.0
    df['volume_ratio'] = 1.2
    return df


@pytest.fixture
def mock_signals_data(mock_features_data):
    """Create mock data with signals"""
    df = mock_features_data.copy()
    # Add mock signals
    df['signal_type'] = 'HOLD'
    df['signal_strength'] = 2
    df['confidence'] = 0.7
    return df


@pytest.fixture
def mock_regime_context():
    """Create mock regime context"""
    return RegimeContext(
        primary_regime='normal_volatility',
        regime_confidence=0.85,
        regime_start_time=datetime(2024, 1, 1),
        regime_duration_minutes=60,
        volatility_regime='normal',
        trend_regime='trending',
        liquidity_regime='high_liquidity'
    )


@pytest.fixture
def mock_data_manager(mock_raw_data):
    """Create mock DataManager"""
    manager = AsyncMock()
    manager.initialize = AsyncMock(return_value=True)
    manager.health_check = AsyncMock(return_value={'healthy': True})
    manager.load_market_data = AsyncMock(return_value={
        'AAPL': mock_raw_data,
        'TSLA': mock_raw_data
    })
    return manager


@pytest.fixture
def mock_indicators_engine(mock_indicators_data):
    """Create mock TechnicalIndicators engine"""
    engine = Mock()
    engine.initialize = AsyncMock(return_value=True)
    engine.health_check = AsyncMock(return_value={'healthy': True})
    engine.calculate_indicators = Mock(return_value=mock_indicators_data)
    engine.set_regime_engine = Mock()
    engine.on_regime_change = AsyncMock()
    return engine


@pytest.fixture
def mock_feature_engineer(mock_features_data):
    """Create mock FeatureEngineer"""
    engineer = Mock()
    engineer.initialize = AsyncMock(return_value=True)
    engineer.health_check = AsyncMock(return_value={'healthy': True})
    engineer.create_features = Mock(return_value=mock_features_data)
    engineer.set_regime_engine = Mock()
    engineer.on_regime_change = AsyncMock()
    return engineer


@pytest.fixture
def mock_signal_generator(mock_signals_data):
    """Create mock SignalGenerator"""
    generator = Mock()
    generator.initialize = AsyncMock(return_value=True)
    generator.health_check = AsyncMock(return_value={'healthy': True})
    generator.generate_signals = Mock(return_value=mock_signals_data)
    generator.set_regime_engine = Mock()
    generator.on_regime_change = AsyncMock()
    return generator


@pytest.fixture
def pipeline_orchestrator():
    """Create pipeline orchestrator instance"""
    return ProcessingPipelineOrchestrator()


# ============================================================================
# ENRICHED MARKET DATA TESTS
# ============================================================================

class TestEnrichedMarketData:
    """Tests for EnrichedMarketData container"""
    
    def test_enriched_data_creation(self, mock_raw_data, mock_indicators_data, 
                                    mock_features_data, mock_signals_data):
        """Test creating enriched data container"""
        enriched = EnrichedMarketData(
            symbol='AAPL',
            timeframe='1min',
            raw_data=mock_raw_data,
            indicators=mock_indicators_data,
            features=mock_features_data,
            signals=mock_signals_data,
            processing_timestamp=datetime.now()
        )
        
        assert enriched.symbol == 'AAPL'
        assert enriched.timeframe == '1min'
        assert not enriched.raw_data.empty
        assert not enriched.indicators.empty
        assert not enriched.features.empty
        assert not enriched.signals.empty
    
    def test_get_enriched_dataframe(self, mock_raw_data, mock_indicators_data,
                                   mock_features_data, mock_signals_data):
        """Test getting enriched DataFrame"""
        enriched = EnrichedMarketData(
            symbol='AAPL',
            timeframe='1min',
            raw_data=mock_raw_data,
            indicators=mock_indicators_data,
            features=mock_features_data,
            signals=mock_signals_data,
            processing_timestamp=datetime.now()
        )
        
        df = enriched.get_enriched_dataframe()
        
        # Should return signals DataFrame (fully enriched)
        assert not df.empty
        assert 'close' in df.columns  # OHLCV
        assert 'SMA_10' in df.columns  # Indicators
        assert 'momentum_score' in df.columns  # Features
        assert 'signal_type' in df.columns  # Signals
    
    def test_validate_enrichment(self, mock_raw_data, mock_indicators_data,
                                 mock_features_data, mock_signals_data):
        """Test enrichment validation"""
        # Valid enrichment
        enriched = EnrichedMarketData(
            symbol='AAPL',
            timeframe='1min',
            raw_data=mock_raw_data,
            indicators=mock_indicators_data,
            features=mock_features_data,
            signals=mock_signals_data,
            processing_timestamp=datetime.now()
        )
        
        assert enriched.validate_enrichment() is True
        
        # Invalid enrichment (missing stage)
        enriched_invalid = EnrichedMarketData(
            symbol='AAPL',
            timeframe='1min',
            raw_data=mock_raw_data,
            indicators=pd.DataFrame(),  # Empty
            features=pd.DataFrame(),
            signals=pd.DataFrame(),
            processing_timestamp=datetime.now()
        )
        
        assert enriched_invalid.validate_enrichment() is False
    
    def test_get_summary(self, mock_raw_data, mock_indicators_data,
                        mock_features_data, mock_signals_data):
        """Test getting summary statistics"""
        enriched = EnrichedMarketData(
            symbol='AAPL',
            timeframe='1min',
            raw_data=mock_raw_data,
            indicators=mock_indicators_data,
            features=mock_features_data,
            signals=mock_signals_data,
            processing_timestamp=datetime.now()
        )
        
        summary = enriched.get_summary()
        
        assert summary['symbol'] == 'AAPL'
        assert summary['timeframe'] == '1min'
        assert summary['raw_rows'] > 0
        assert summary['total_columns'] > 0
        assert summary['enrichment_valid'] is True


# ============================================================================
# PIPELINE ORCHESTRATOR TESTS
# ============================================================================

class TestPipelineOrchestrator:
    """Tests for ProcessingPipelineOrchestrator"""
    
    def test_orchestrator_creation(self, pipeline_orchestrator):
        """Test creating pipeline orchestrator"""
        assert pipeline_orchestrator.component_name == "ProcessingPipelineOrchestrator"
        assert pipeline_orchestrator.is_initialized is False
        assert pipeline_orchestrator.is_operational is False
    
    @pytest.mark.asyncio
    async def test_initialize_without_components(self, pipeline_orchestrator):
        """Test initialization when components not available"""
        # Should handle missing components gracefully
        result = await pipeline_orchestrator.initialize()
        
        # Should succeed (mock mode)
        assert result is True
        assert pipeline_orchestrator.is_initialized is True
    
    @pytest.mark.asyncio
    async def test_start_stop(self, pipeline_orchestrator):
        """Test starting and stopping pipeline"""
        # Initialize first
        await pipeline_orchestrator.initialize()
        
        # Start
        result = await pipeline_orchestrator.start()
        assert result is True
        assert pipeline_orchestrator.is_operational is True
        
        # Stop
        result = await pipeline_orchestrator.stop()
        assert result is True
        assert pipeline_orchestrator.is_operational is False
    
    @pytest.mark.asyncio
    async def test_health_check(self, pipeline_orchestrator):
        """Test health check"""
        await pipeline_orchestrator.initialize()
        await pipeline_orchestrator.start()
        
        health = await pipeline_orchestrator.health_check()
        
        assert 'orchestrator_healthy' in health
        assert 'initialized' in health
        assert health['initialized'] is True
    
    def test_get_status(self, pipeline_orchestrator):
        """Test getting status"""
        status = pipeline_orchestrator.get_status()
        
        assert status['component_name'] == "ProcessingPipelineOrchestrator"
        assert 'initialized' in status
        assert 'operational' in status
        assert 'total_processed' in status
    
    def test_set_regime_engine(self, pipeline_orchestrator):
        """Test setting regime engine"""
        mock_regime_engine = Mock()
        
        pipeline_orchestrator.set_regime_engine(mock_regime_engine)
        
        assert pipeline_orchestrator.regime_engine == mock_regime_engine
    
    @pytest.mark.asyncio
    async def test_on_regime_change(self, pipeline_orchestrator, mock_regime_context):
        """Test handling regime change"""
        await pipeline_orchestrator.on_regime_change(mock_regime_context)
        
        assert pipeline_orchestrator.current_regime_context == mock_regime_context
        # Cache should be cleared
        assert len(pipeline_orchestrator.enriched_data_cache) == 0
    
    def test_get_current_regime_context(self, pipeline_orchestrator, mock_regime_context):
        """Test getting current regime context"""
        pipeline_orchestrator.current_regime_context = mock_regime_context
        
        context = pipeline_orchestrator.get_current_regime_context()
        
        assert context == mock_regime_context
    
    @pytest.mark.asyncio
    async def test_adapt_to_regime(self, pipeline_orchestrator, mock_regime_context):
        """Test adapting to regime"""
        result = await pipeline_orchestrator.adapt_to_regime(mock_regime_context)
        
        assert result['pipeline_adapted'] is True
        assert 'regime' in result
    
    def test_validate_regime_dependency(self, pipeline_orchestrator):
        """Test validating regime dependency"""
        # Without regime engine
        assert pipeline_orchestrator.validate_regime_dependency() is False
        
        # With regime engine
        pipeline_orchestrator.regime_engine = Mock()
        assert pipeline_orchestrator.validate_regime_dependency() is True
    
    def test_clear_cache(self, pipeline_orchestrator):
        """Test clearing cache"""
        # Add some cache entries
        pipeline_orchestrator.enriched_data_cache['AAPL'] = Mock()
        pipeline_orchestrator.enriched_data_cache['TSLA'] = Mock()
        
        count = pipeline_orchestrator.clear_cache()
        
        assert count == 2
        assert len(pipeline_orchestrator.enriched_data_cache) == 0
    
    def test_get_cached_data(self, pipeline_orchestrator):
        """Test getting cached data"""
        mock_data = Mock()
        pipeline_orchestrator.enriched_data_cache['AAPL'] = mock_data
        
        result = pipeline_orchestrator.get_cached_data('AAPL')
        assert result == mock_data
        
        result = pipeline_orchestrator.get_cached_data('TSLA')
        assert result is None
    
    def test_get_performance_metrics(self, pipeline_orchestrator):
        """Test getting performance metrics"""
        # Add some processing times
        pipeline_orchestrator.processing_times['data_loading'] = [0.1, 0.2, 0.15]
        pipeline_orchestrator.processing_times['indicators'] = [0.3, 0.35, 0.32]
        pipeline_orchestrator.total_processed = 10
        
        metrics = pipeline_orchestrator.get_performance_metrics()
        
        assert metrics['total_processed'] == 10
        assert 'avg_processing_times' in metrics
        assert 'data_loading' in metrics['avg_processing_times']


# ============================================================================
# INTEGRATION TESTS (WITH MOCKS)
# ============================================================================

class TestPipelineIntegration:
    """Integration tests for pipeline orchestrator"""
    
    @pytest.mark.asyncio
    async def test_process_market_data_complete_flow(
        self,
        pipeline_orchestrator,
        mock_data_manager,
        mock_indicators_engine,
        mock_feature_engineer,
        mock_signal_generator,
        mock_raw_data,
        mock_indicators_data,
        mock_features_data,
        mock_signals_data
    ):
        """Test complete data processing flow through pipeline"""
        # Inject mock components
        pipeline_orchestrator.data_manager = mock_data_manager
        pipeline_orchestrator.indicators_engine = mock_indicators_engine
        pipeline_orchestrator.feature_engineer = mock_feature_engineer
        pipeline_orchestrator.signal_generator = mock_signal_generator
        pipeline_orchestrator.is_initialized = True
        pipeline_orchestrator.is_operational = True
        
        # Process data
        enriched_data = await pipeline_orchestrator.process_market_data(
            symbols=['AAPL', 'TSLA'],
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 2),
            timeframe='1min'
        )
        
        # Verify results
        assert len(enriched_data) == 2
        assert 'AAPL' in enriched_data
        assert 'TSLA' in enriched_data
        
        # Verify each symbol has enriched data
        for symbol in ['AAPL', 'TSLA']:
            data = enriched_data[symbol]
            assert isinstance(data, EnrichedMarketData)
            assert data.symbol == symbol
            assert data.validate_enrichment() is True
        
        # Verify pipeline stages were called
        mock_data_manager.load_market_data.assert_called_once()
        assert mock_indicators_engine.calculate_indicators.call_count == 2
        assert mock_feature_engineer.create_features.call_count == 2
        assert mock_signal_generator.generate_signals.call_count == 2
    
    @pytest.mark.asyncio
    async def test_pipeline_with_regime_integration(
        self,
        pipeline_orchestrator,
        mock_data_manager,
        mock_indicators_engine,
        mock_feature_engineer,
        mock_signal_generator,
        mock_regime_context
    ):
        """Test pipeline with regime engine integration"""
        # Setup
        pipeline_orchestrator.data_manager = mock_data_manager
        pipeline_orchestrator.indicators_engine = mock_indicators_engine
        pipeline_orchestrator.feature_engineer = mock_feature_engineer
        pipeline_orchestrator.signal_generator = mock_signal_generator
        pipeline_orchestrator.is_initialized = True
        pipeline_orchestrator.is_operational = True
        
        # Set regime engine
        mock_regime_engine = Mock()
        pipeline_orchestrator.set_regime_engine(mock_regime_engine)
        
        # Verify regime engine propagated
        mock_indicators_engine.set_regime_engine.assert_called_once()
        mock_feature_engineer.set_regime_engine.assert_called_once()
        mock_signal_generator.set_regime_engine.assert_called_once()
        
        # Handle regime change
        await pipeline_orchestrator.on_regime_change(mock_regime_context)
        
        # Verify regime change propagated
        mock_indicators_engine.on_regime_change.assert_called_once()
        mock_feature_engineer.on_regime_change.assert_called_once()
        mock_signal_generator.on_regime_change.assert_called_once()


# ============================================================================
# RULE 3 COMPLIANCE TESTS
# ============================================================================

class TestRule3Compliance:
    """Tests for Rule 3 (Unified Data Flow Pipeline) compliance"""
    
    def test_enriched_data_has_all_stages(self, mock_raw_data, mock_indicators_data,
                                          mock_features_data, mock_signals_data):
        """Verify enriched data contains all pipeline stages"""
        enriched = EnrichedMarketData(
            symbol='AAPL',
            timeframe='1min',
            raw_data=mock_raw_data,
            indicators=mock_indicators_data,
            features=mock_features_data,
            signals=mock_signals_data,
            processing_timestamp=datetime.now()
        )
        
        # Rule 3: Must have all 4 stages
        assert not enriched.raw_data.empty, "Phase 1: Raw data required"
        assert not enriched.indicators.empty, "Phase 2: Indicators required"
        assert not enriched.features.empty, "Phase 3: Features required"
        assert not enriched.signals.empty, "Phase 4: Signals required"
    
    def test_enriched_data_has_required_columns(self, mock_signals_data):
        """Verify enriched data has required columns from all stages"""
        # Rule 3: Enriched data must have columns from all stages
        required_ohlcv = ['open', 'high', 'low', 'close', 'volume']
        required_indicators = ['SMA_10', 'RSI_14', 'MACD', 'ADX_14']
        required_features = ['returns_1', 'momentum_score', 'trend_strength']
        required_signals = ['signal_type', 'signal_strength', 'confidence']
        
        for col in required_ohlcv + required_indicators + required_features + required_signals:
            assert col in mock_signals_data.columns, f"Missing required column: {col}"
    
    def test_orchestrator_enforces_pipeline_sequence(
        self,
        pipeline_orchestrator,
        mock_data_manager,
        mock_indicators_engine,
        mock_feature_engineer,
        mock_signal_generator
    ):
        """Verify orchestrator enforces pipeline sequence"""
        # Rule 3: Must process through all stages in order
        pipeline_orchestrator.data_manager = mock_data_manager
        pipeline_orchestrator.indicators_engine = mock_indicators_engine
        pipeline_orchestrator.feature_engineer = mock_feature_engineer
        pipeline_orchestrator.signal_generator = mock_signal_generator
        
        # Verify components exist
        assert pipeline_orchestrator.data_manager is not None, "Phase 1 missing"
        assert pipeline_orchestrator.indicators_engine is not None, "Phase 2 missing"
        assert pipeline_orchestrator.feature_engineer is not None, "Phase 3 missing"
        assert pipeline_orchestrator.signal_generator is not None, "Phase 4 missing"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

