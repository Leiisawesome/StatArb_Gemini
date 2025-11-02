"""
Unit tests for Liquidity Assessment Engine
Tests component lifecycle, liquidity assessment, and regime classification
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock
from datetime import datetime

from core_engine.data.liquidity_engine import (
    LiquidityAssessmentEngine,
    LiquidityRegime
)

logger = __import__('logging').getLogger(__name__)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def liquidity_engine():
    """Create liquidity assessment engine instance"""
    return LiquidityAssessmentEngine()


@pytest.fixture
def liquidity_engine_with_config():
    """Create liquidity assessment engine with custom config"""
    config = {
        'liquidity_threshold_high': 80.0,
        'liquidity_threshold_low': 20.0,
        'spread_threshold_bps': 10.0
    }
    return LiquidityAssessmentEngine(config=config)


@pytest.fixture
def sample_market_data():
    """Sample market data for liquidity assessment"""
    return {
        'volume': 1000000,
        'bid_price': 99.95,
        'ask_price': 100.05,
        'spread_bps': 10.0,
        'daily_volume': 5000000
    }


@pytest.fixture
def mock_orchestrator():
    """Create mock orchestrator"""
    orchestrator = Mock()
    orchestrator.register_component = Mock(return_value='component_123')
    return orchestrator


# =============================================================================
# TEST INITIALIZATION
# =============================================================================

class TestInitialization:
    """Test liquidity engine initialization"""
    
    def test_default_initialization(self, liquidity_engine):
        """Test default initialization"""
        assert liquidity_engine is not None
        assert liquidity_engine.config == {}
        assert liquidity_engine.is_initialized is False
        assert liquidity_engine.is_operational is False
        assert liquidity_engine.component_id is not None
        assert liquidity_engine.orchestrator is None
    
    def test_custom_config_initialization(self, liquidity_engine_with_config):
        """Test initialization with custom config"""
        assert liquidity_engine_with_config.config is not None
        assert 'liquidity_threshold_high' in liquidity_engine_with_config.config
        assert liquidity_engine_with_config.config['liquidity_threshold_high'] == 80.0
    
    def test_component_id_generation(self):
        """Test that component IDs are unique"""
        engine1 = LiquidityAssessmentEngine()
        engine2 = LiquidityAssessmentEngine()
        assert engine1.component_id != engine2.component_id
    
    def test_orchestrator_registration(self, liquidity_engine, mock_orchestrator):
        """Test orchestrator registration"""
        component_id = liquidity_engine.register_with_orchestrator(mock_orchestrator)
        
        assert liquidity_engine.orchestrator == mock_orchestrator
        assert component_id == liquidity_engine.component_id
        mock_orchestrator.register_component.assert_not_called()  # register_with_orchestrator doesn't call this


# =============================================================================
# TEST COMPONENT LIFECYCLE
# =============================================================================

class TestComponentLifecycle:
    """Test component lifecycle methods"""
    
    @pytest.mark.asyncio
    async def test_initialize(self, liquidity_engine):
        """Test component initialization"""
        result = await liquidity_engine.initialize()
        
        assert result is True
        assert liquidity_engine.is_initialized is True
        assert liquidity_engine.is_operational is False  # Not started yet
    
    @pytest.mark.asyncio
    async def test_initialize_already_initialized(self, liquidity_engine):
        """Test re-initialization"""
        await liquidity_engine.initialize()
        result = await liquidity_engine.initialize()
        
        assert result is True
        assert liquidity_engine.is_initialized is True
    
    @pytest.mark.asyncio
    async def test_start_success(self, liquidity_engine):
        """Test successful start"""
        await liquidity_engine.initialize()
        result = await liquidity_engine.start()
        
        assert result is True
        assert liquidity_engine.is_operational is True
        assert liquidity_engine.is_initialized is True
    
    @pytest.mark.asyncio
    async def test_start_without_initialization(self, liquidity_engine):
        """Test start without initialization fails"""
        result = await liquidity_engine.start()
        
        assert result is False
        assert liquidity_engine.is_operational is False
    
    @pytest.mark.asyncio
    async def test_start_twice(self, liquidity_engine):
        """Test starting twice"""
        await liquidity_engine.initialize()
        result1 = await liquidity_engine.start()
        result2 = await liquidity_engine.start()
        
        assert result1 is True
        assert result2 is True
        assert liquidity_engine.is_operational is True
    
    @pytest.mark.asyncio
    async def test_stop(self, liquidity_engine):
        """Test component stop"""
        await liquidity_engine.initialize()
        await liquidity_engine.start()
        
        result = await liquidity_engine.stop()
        
        assert result is True
        assert liquidity_engine.is_operational is False
        assert liquidity_engine.is_initialized is True  # Initialization persists
    
    @pytest.mark.asyncio
    async def test_stop_when_not_started(self, liquidity_engine):
        """Test stop when not started"""
        await liquidity_engine.initialize()
        
        result = await liquidity_engine.stop()
        
        assert result is True
        assert liquidity_engine.is_operational is False
    
    @pytest.mark.asyncio
    async def test_full_lifecycle(self, liquidity_engine):
        """Test complete lifecycle sequence"""
        # Initialize
        init_result = await liquidity_engine.initialize()
        assert init_result is True
        
        # Start
        start_result = await liquidity_engine.start()
        assert start_result is True
        
        # Stop
        stop_result = await liquidity_engine.stop()
        assert stop_result is True
        
        # Verify final state
        assert liquidity_engine.is_initialized is True
        assert liquidity_engine.is_operational is False


# =============================================================================
# TEST HEALTH CHECKS
# =============================================================================

class TestHealthChecks:
    """Test health check and status methods"""
    
    @pytest.mark.asyncio
    async def test_health_check_uninitialized(self, liquidity_engine):
        """Test health check when not initialized"""
        health = await liquidity_engine.health_check()
        
        assert health['healthy'] is False
        assert health['initialized'] is False
        assert health['operational'] is False
        assert health['component_id'] == liquidity_engine.component_id
        assert health['component_type'] == 'LiquidityAssessmentEngine'
    
    @pytest.mark.asyncio
    async def test_health_check_initialized_not_started(self, liquidity_engine):
        """Test health check when initialized but not started"""
        await liquidity_engine.initialize()
        health = await liquidity_engine.health_check()
        
        assert health['healthy'] is False
        assert health['initialized'] is True
        assert health['operational'] is False
    
    @pytest.mark.asyncio
    async def test_health_check_operational(self, liquidity_engine):
        """Test health check when operational"""
        await liquidity_engine.initialize()
        await liquidity_engine.start()
        health = await liquidity_engine.health_check()
        
        assert health['healthy'] is True
        assert health['initialized'] is True
        assert health['operational'] is True
    
    def test_get_status_uninitialized(self, liquidity_engine):
        """Test get status when not initialized"""
        status = liquidity_engine.get_status()
        
        assert status['initialized'] is False
        assert status['operational'] is False
        assert status['component_id'] == liquidity_engine.component_id
    
    def test_get_status_initialized(self, liquidity_engine):
        """Test get status when initialized"""
        asyncio.run(liquidity_engine.initialize())
        status = liquidity_engine.get_status()
        
        assert status['initialized'] is True
        assert status['operational'] is False
    
    def test_get_status_operational(self, liquidity_engine):
        """Test get status when operational"""
        asyncio.run(liquidity_engine.initialize())
        asyncio.run(liquidity_engine.start())
        status = liquidity_engine.get_status()
        
        assert status['initialized'] is True
        assert status['operational'] is True


# =============================================================================
# TEST LIQUIDITY ASSESSMENT
# =============================================================================

class TestLiquidityAssessment:
    """Test liquidity assessment functionality"""
    
    def test_assess_liquidity_score_basic(self, liquidity_engine, sample_market_data):
        """Test basic liquidity assessment"""
        result = liquidity_engine.assess_liquidity_score(
            symbol='AAPL',
            market_data=sample_market_data
        )
        
        assert result is not None
        assert result['symbol'] == 'AAPL'
        assert 'timestamp' in result
        assert isinstance(result['timestamp'], datetime)
        assert 'overall_score' in result
        assert result['overall_score'] == 70.0
        assert result['liquidity_regime'] == LiquidityRegime.NORMAL_LIQUIDITY
        assert 'confidence' in result
        assert result['confidence'] == 0.8
    
    def test_assess_liquidity_score_with_volume(self, liquidity_engine):
        """Test liquidity assessment with volume data"""
        market_data = {
            'volume': 2000000,
            'bid_price': 100.0,
            'ask_price': 100.1
        }
        
        result = liquidity_engine.assess_liquidity_score(
            symbol='MSFT',
            market_data=market_data
        )
        
        assert result['symbol'] == 'MSFT'
        assert result['avg_daily_volume'] == 2000000
        assert result['current_volume'] == 2000000
    
    def test_assess_liquidity_score_without_volume(self, liquidity_engine):
        """Test liquidity assessment without volume in market data"""
        market_data = {
            'price': 100.0
        }
        
        result = liquidity_engine.assess_liquidity_score(
            symbol='GOOGL',
            market_data=market_data
        )
        
        # Should use default volume
        assert result['avg_daily_volume'] == 100000
        assert result['current_volume'] == 100000
    
    def test_assess_liquidity_score_all_fields(self, liquidity_engine, sample_market_data):
        """Test that all expected fields are present in result"""
        result = liquidity_engine.assess_liquidity_score(
            symbol='TSLA',
            market_data=sample_market_data
        )
        
        # Check all expected fields
        assert 'symbol' in result
        assert 'timestamp' in result
        assert 'overall_score' in result
        assert 'liquidity_regime' in result
        assert 'confidence' in result
        assert 'avg_daily_volume' in result
        assert 'current_volume' in result
        assert 'volume_ratio' in result
        assert 'bid_ask_spread_bps' in result
        assert 'effective_spread_bps' in result
        assert 'market_depth' in result
        assert 'liquidity_risk_score' in result
        assert 'slippage_risk' in result
        
        # Check field types
        assert isinstance(result['overall_score'], float)
        assert isinstance(result['liquidity_regime'], LiquidityRegime)
        assert isinstance(result['confidence'], float)
        assert isinstance(result['volume_ratio'], float)
        assert isinstance(result['bid_ask_spread_bps'], float)
    
    def test_assess_liquidity_score_regime_normal(self, liquidity_engine):
        """Test that assessment returns normal liquidity regime"""
        market_data = {'volume': 1000000}
        
        result = liquidity_engine.assess_liquidity_score(
            symbol='AAPL',
            market_data=market_data
        )
        
        assert result['liquidity_regime'] == LiquidityRegime.NORMAL_LIQUIDITY
    
    def test_assess_liquidity_score_multiple_symbols(self, liquidity_engine):
        """Test liquidity assessment for multiple symbols"""
        symbols = ['AAPL', 'MSFT', 'GOOGL']
        market_data = {'volume': 1000000}
        
        results = {}
        for symbol in symbols:
            results[symbol] = liquidity_engine.assess_liquidity_score(
                symbol=symbol,
                market_data=market_data
            )
        
        assert len(results) == 3
        assert all(r['symbol'] == s for s, r in results.items())
        assert all(r['liquidity_regime'] == LiquidityRegime.NORMAL_LIQUIDITY 
                  for r in results.values())
    
    def test_assess_liquidity_score_with_historical_data(self, liquidity_engine, sample_market_data):
        """Test liquidity assessment with historical data parameter"""
        historical_data = Mock()
        
        result = liquidity_engine.assess_liquidity_score(
            symbol='AAPL',
            market_data=sample_market_data,
            historical_data=historical_data
        )
        
        # Should still work with historical data parameter
        assert result is not None
        assert result['symbol'] == 'AAPL'


# =============================================================================
# TEST EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Test edge cases and error handling"""
    
    @pytest.mark.asyncio
    async def test_initialize_error_handling(self, liquidity_engine):
        """Test initialization error handling"""
        # Initialize should handle errors gracefully
        result = await liquidity_engine.initialize()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_start_error_handling(self, liquidity_engine):
        """Test start error handling"""
        await liquidity_engine.initialize()
        # Start should handle errors gracefully
        result = await liquidity_engine.start()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_stop_error_handling(self, liquidity_engine):
        """Test stop error handling"""
        # Stop should handle errors gracefully
        result = await liquidity_engine.stop()
        assert result is True
    
    def test_assess_liquidity_empty_market_data(self, liquidity_engine):
        """Test liquidity assessment with empty market data"""
        result = liquidity_engine.assess_liquidity_score(
            symbol='AAPL',
            market_data={}
        )
        
        # Should use defaults
        assert result is not None
        assert result['avg_daily_volume'] == 100000
        assert result['current_volume'] == 100000
    
    def test_assess_liquidity_none_market_data(self, liquidity_engine):
        """Test liquidity assessment with None market data raises error"""
        # Should raise AttributeError when market_data is None
        with pytest.raises(AttributeError):
            liquidity_engine.assess_liquidity_score(
                symbol='AAPL',
                market_data=None
            )


# =============================================================================
# TEST INTEGRATION
# =============================================================================

class TestIntegration:
    """Test integration scenarios"""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self, liquidity_engine, sample_market_data):
        """Test complete workflow from initialization to assessment"""
        # Initialize
        await liquidity_engine.initialize()
        assert liquidity_engine.is_initialized is True
        
        # Start
        await liquidity_engine.start()
        assert liquidity_engine.is_operational is True
        
        # Perform assessment
        result = liquidity_engine.assess_liquidity_score(
            symbol='AAPL',
            market_data=sample_market_data
        )
        assert result is not None
        assert result['symbol'] == 'AAPL'
        
        # Check health
        health = await liquidity_engine.health_check()
        assert health['healthy'] is True
        
        # Stop
        await liquidity_engine.stop()
        assert liquidity_engine.is_operational is False
    
    @pytest.mark.asyncio
    async def test_orchestrator_integration(self, liquidity_engine, mock_orchestrator):
        """Test orchestrator integration"""
        # Register with orchestrator
        component_id = liquidity_engine.register_with_orchestrator(mock_orchestrator)
        
        # Verify registration
        assert liquidity_engine.orchestrator == mock_orchestrator
        assert component_id == liquidity_engine.component_id
        
        # Initialize and start
        await liquidity_engine.initialize()
        await liquidity_engine.start()
        
        # Verify operational
        health = await liquidity_engine.health_check()
        assert health['healthy'] is True
    
    def test_multiple_assessments(self, liquidity_engine):
        """Test multiple consecutive assessments"""
        market_data = {'volume': 1000000}
        
        results = []
        for i in range(10):
            result = liquidity_engine.assess_liquidity_score(
                symbol=f'SYMBOL_{i}',
                market_data=market_data
            )
            results.append(result)
        
        assert len(results) == 10
        assert all(r is not None for r in results)
        assert all(r['liquidity_regime'] == LiquidityRegime.NORMAL_LIQUIDITY 
                  for r in results)

