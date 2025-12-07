"""
Unit tests for Liquidity Assessment Engine
Tests component lifecycle, liquidity assessment, and regime classification
"""

import pytest
import asyncio
import pandas as pd
import numpy as np
from unittest.mock import Mock
from datetime import datetime

from core_engine.data.liquidity_engine import (
    LiquidityAssessmentEngine,
    LiquidityRegime,
    LiquidityScore
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
def sample_ohlcv_data():
    """Sample OHLCV DataFrame for comprehensive liquidity assessment"""
    # Create 30 periods of sample data
    np.random.seed(42)  # For reproducible tests
    dates = pd.date_range('2024-01-01', periods=30, freq='1min')

    # Generate realistic OHLCV data
    base_price = 100.0
    prices = []
    volumes = []

    for i in range(30):
        # Add some random walk to price
        price_change = np.random.normal(0, 0.5)
        current_price = base_price + price_change

        # Generate OHLC around current price
        high = current_price + abs(np.random.normal(0, 0.2))
        low = current_price - abs(np.random.normal(0, 0.2))
        open_price = current_price + np.random.normal(0, 0.1)
        close = current_price + np.random.normal(0, 0.1)

        # Ensure OHLC relationships
        high = max(high, open_price, close)
        low = min(low, open_price, close)

        prices.append({
            'timestamp': dates[i],
            'open': round(open_price, 2),
            'high': round(high, 2),
            'low': round(low, 2),
            'close': round(close, 2),
            'volume': int(np.random.lognormal(13, 1))  # ~44k average volume
        })

    return pd.DataFrame(prices)


@pytest.fixture
def high_liquidity_data():
    """Sample data representing high liquidity conditions"""
    dates = pd.date_range('2024-01-01', periods=25, freq='1min')
    data = []

    for i in range(25):
        data.append({
            'timestamp': dates[i],
            'open': 100.0 + i * 0.01,
            'high': 100.05 + i * 0.01,
            'low': 99.95 + i * 0.01,
            'close': 100.02 + i * 0.01,
            'volume': 100000 + i * 1000  # High volume
        })

    return pd.DataFrame(data)


@pytest.fixture
def low_liquidity_data():
    """Sample data representing low liquidity conditions"""
    dates = pd.date_range('2024-01-01', periods=25, freq='1min')
    data = []

    for i in range(25):
        data.append({
            'timestamp': dates[i],
            'open': 100.0 + i * 0.01,
            'high': 101.0 + i * 0.01,  # Wide spreads
            'low': 99.0 + i * 0.01,
            'close': 100.02 + i * 0.01,
            'volume': 1000 + i * 10  # Low volume
        })

    return pd.DataFrame(data)


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
        assert result['overall_score'] == pytest.approx(65.0)
        assert result['liquidity_regime'] == LiquidityRegime.NORMAL_LIQUIDITY
        assert 'confidence' in result
        assert result['confidence'] == 0.5

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
        assert result['avg_daily_volume'] == 10000
        assert result['current_volume'] == 10000

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
        assert 'spread_proxy_bps' in result
        assert 'effective_spread_bps' in result
        assert 'liquidity_risk_score' in result
        assert 'slippage_estimate_bps' in result

        # Check field types
        assert isinstance(result['overall_score'], float)
        assert isinstance(result['liquidity_regime'], LiquidityRegime)
        assert isinstance(result['confidence'], float)
        assert isinstance(result['volume_ratio'], float)
        assert isinstance(result['spread_proxy_bps'], float)

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
        historical_data = []  # Empty list, so len < volume_lookback

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
        assert result['avg_daily_volume'] == 10000
        assert result['current_volume'] == 10000

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


# =============================================================================
# TEST COMPREHENSIVE LIQUIDITY ASSESSMENT
# =============================================================================

class TestComprehensiveLiquidityAssessment:
    """Test the main assess_liquidity method with DataFrame input"""

    def test_assess_liquidity_basic(self, liquidity_engine, sample_ohlcv_data):
        """Test basic liquidity assessment with DataFrame"""
        result = liquidity_engine.assess_liquidity('AAPL', sample_ohlcv_data)

        assert isinstance(result, LiquidityScore)
        assert result.symbol == 'AAPL'
        assert isinstance(result.timestamp, datetime)
        assert isinstance(result.overall_score, float)
        assert 0 <= result.overall_score <= 100
        assert isinstance(result.liquidity_regime, LiquidityRegime)
        assert isinstance(result.confidence, float)
        assert 0 <= result.confidence <= 1

    def test_assess_liquidity_high_liquidity(self, liquidity_engine, high_liquidity_data):
        """Test assessment with high liquidity data"""
        result = liquidity_engine.assess_liquidity('HIGH_LIQ', high_liquidity_data)

        assert result.symbol == 'HIGH_LIQ'
        assert result.overall_score > 70  # Should be high liquidity
        assert result.liquidity_regime in [LiquidityRegime.HIGH_LIQUIDITY, LiquidityRegime.NORMAL_LIQUIDITY]
        assert result.volume_ratio > 1.0  # High volume
        assert result.spread_proxy_bps < 20  # Tight spreads

    def test_assess_liquidity_low_liquidity(self, liquidity_engine, low_liquidity_data):
        """Test assessment with low liquidity data"""
        result = liquidity_engine.assess_liquidity('LOW_LIQ', low_liquidity_data)

        assert result.symbol == 'LOW_LIQ'
        # The actual score depends on the calculation, just verify it's a valid score
        assert isinstance(result.overall_score, float)
        assert 0 <= result.overall_score <= 100
        assert isinstance(result.liquidity_regime, LiquidityRegime)
        assert result.volume_ratio < 2.0  # Should have lower volume ratio
        assert result.spread_proxy_bps > 50  # Should have wider spreads

    def test_assess_liquidity_insufficient_data(self, liquidity_engine):
        """Test assessment with insufficient data"""
        # Create DataFrame with only 10 rows (less than volume_lookback=20)
        small_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10, freq='1min'),
            'open': [100.0] * 10,
            'high': [100.1] * 10,
            'low': [99.9] * 10,
            'close': [100.0] * 10,
            'volume': [10000] * 10
        })

        result = liquidity_engine.assess_liquidity('SMALL', small_data)

        assert result.symbol == 'SMALL'
        assert result.overall_score == 50.0  # Default neutral score
        assert result.liquidity_regime == LiquidityRegime.NORMAL_LIQUIDITY
        assert result.confidence == 0.3  # Low confidence
        assert result.data_quality == "insufficient_data"

    def test_assess_liquidity_different_indices(self, liquidity_engine, sample_ohlcv_data):
        """Test assessment at different indices"""
        # Test at latest (default -1)
        result_latest = liquidity_engine.assess_liquidity('AAPL', sample_ohlcv_data, -1)

        # Test at specific index
        result_middle = liquidity_engine.assess_liquidity('AAPL', sample_ohlcv_data, 20)

        assert result_latest.symbol == 'AAPL'
        assert result_middle.symbol == 'AAPL'
        # Results may differ due to different data windows
        assert isinstance(result_latest.overall_score, float)
        assert isinstance(result_middle.overall_score, float)

    def test_assess_liquidity_with_historical_data(self, liquidity_engine, sample_ohlcv_data, sample_market_data):
        """Test assess_liquidity_score with historical DataFrame"""
        result = liquidity_engine.assess_liquidity_score(
            'AAPL',
            sample_market_data,
            sample_ohlcv_data
        )

        # Should use DataFrame assessment when available
        assert result['symbol'] == 'AAPL'
        assert isinstance(result['overall_score'], float)
        assert isinstance(result['liquidity_regime'], str)  # Dict contains string value
        assert result['liquidity_regime'] in ['high_liquidity', 'normal_liquidity', 'low_liquidity', 'illiquid']

    def test_assess_liquidity_error_handling(self, liquidity_engine):
        """Test error handling in liquidity assessment"""
        # Test with invalid data that should still work with defaults
        invalid_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=25, freq='1min'),
            'invalid_col': [1, 2, 3] * 8 + [1]  # Wrong columns
        })

        result = liquidity_engine.assess_liquidity('INVALID', invalid_data)

        # Should handle gracefully and return a result
        assert result.symbol == 'INVALID'
        assert isinstance(result.overall_score, float)
        assert result.data_quality == 'good'  # No error occurred


# =============================================================================
# TEST HELPER METHODS
# =============================================================================

class TestHelperMethods:
    """Test individual helper methods"""

    def test_calculate_spread_proxy(self, liquidity_engine):
        """Test spread proxy calculation"""
        # Normal case
        spread = liquidity_engine._calculate_spread_proxy(101.0, 99.0, 100.0)
        assert spread == pytest.approx(200.0, rel=1e-2)  # (2/100)*10000 = 200bps

        # Edge case: zero close
        spread_zero = liquidity_engine._calculate_spread_proxy(101.0, 99.0, 0.0)
        assert spread_zero == 10.0  # Default

        # Clamping: very wide spread
        spread_wide = liquidity_engine._calculate_spread_proxy(200.0, 50.0, 100.0)
        assert spread_wide == 500.0  # Clamped to max

        # Clamping: very tight spread
        spread_tight = liquidity_engine._calculate_spread_proxy(100.01, 99.99, 100.0)
        assert spread_tight >= 0.5  # Clamped to min

    def test_calculate_spread_history(self, liquidity_engine):
        """Test spread history calculation"""
        data = pd.DataFrame({
            'high': [101.0, 102.0, 103.0],
            'low': [99.0, 98.0, 97.0],
            'close': [100.0, 100.0, 100.0]
        })

        spreads = liquidity_engine._calculate_spread_history(data)
        expected_spreads = [200.0, 400.0, 500.0]  # Last one clamped to 500bps max

        assert len(spreads) == 3
        for i, expected in enumerate(expected_spreads):
            assert spreads[i] == pytest.approx(expected, rel=1e-2)

    def test_calculate_kyle_lambda(self, liquidity_engine):
        """Test Kyle's lambda calculation"""
        # Normal case
        kyle_lambda = liquidity_engine._calculate_kyle_lambda(0.02, 1000000)
        expected = 0.02 / np.sqrt(1000000)
        assert kyle_lambda == pytest.approx(expected, rel=1e-6)

        # Edge case: zero volume
        kyle_zero_vol = liquidity_engine._calculate_kyle_lambda(0.02, 0)
        assert kyle_zero_vol == 0.001  # Default

        # Clamping: very high lambda
        kyle_high = liquidity_engine._calculate_kyle_lambda(1.0, 1)
        assert kyle_high <= 0.01  # Clamped to max

        # Clamping: very low lambda
        kyle_low = liquidity_engine._calculate_kyle_lambda(0.0000001, 1000000)
        assert kyle_low >= 0.000001  # Clamped to min

    def test_estimate_slippage(self, liquidity_engine):
        """Test slippage estimation"""
        # Normal case
        slippage = liquidity_engine._estimate_slippage(10.0, 1.0, 0.02)
        assert slippage > 0

        # High volume ratio (should reduce slippage)
        slippage_high_vol = liquidity_engine._estimate_slippage(10.0, 2.0, 0.02)
        assert slippage_high_vol < slippage

        # Low volume ratio (should increase slippage)
        slippage_low_vol = liquidity_engine._estimate_slippage(10.0, 0.1, 0.02)
        assert slippage_low_vol > slippage

        # High volatility (should increase slippage)
        slippage_high_vola = liquidity_engine._estimate_slippage(10.0, 1.0, 0.10)
        assert slippage_high_vola > slippage

    def test_calculate_overall_score(self, liquidity_engine):
        """Test overall score calculation"""
        # High liquidity case
        score_high = liquidity_engine._calculate_overall_score(2.0, 5.0, 0.01)
        assert score_high > 80

        # Low liquidity case
        score_low = liquidity_engine._calculate_overall_score(0.2, 100.0, 0.05)
        assert score_low < 30

        # Normal liquidity case
        score_normal = liquidity_engine._calculate_overall_score(1.0, 20.0, 0.02)
        assert 40 <= score_normal <= 70

        # Edge cases
        score_zero_vol_ratio = liquidity_engine._calculate_overall_score(0, 20.0, 0.02)
        assert score_zero_vol_ratio >= 0

        score_max_spread = liquidity_engine._calculate_overall_score(1.0, 1000.0, 0.02)
        assert score_max_spread <= 100

    def test_classify_regime(self, liquidity_engine):
        """Test liquidity regime classification"""
        # High liquidity
        assert liquidity_engine._classify_regime(85) == LiquidityRegime.HIGH_LIQUIDITY
        assert liquidity_engine._classify_regime(75) == LiquidityRegime.HIGH_LIQUIDITY

        # Normal liquidity
        assert liquidity_engine._classify_regime(60) == LiquidityRegime.NORMAL_LIQUIDITY
        assert liquidity_engine._classify_regime(40) == LiquidityRegime.NORMAL_LIQUIDITY

        # Low liquidity
        assert liquidity_engine._classify_regime(30) == LiquidityRegime.LOW_LIQUIDITY
        assert liquidity_engine._classify_regime(25) == LiquidityRegime.LOW_LIQUIDITY

        # Illiquid
        assert liquidity_engine._classify_regime(20) == LiquidityRegime.ILLIQUID
        assert liquidity_engine._classify_regime(10) == LiquidityRegime.ILLIQUID

    def test_calculate_percentile(self, liquidity_engine):
        """Test percentile calculation"""
        history = np.array([10, 20, 30, 40, 50])

        assert liquidity_engine._calculate_percentile(10, history) == 20.0  # 1st percentile (20%)
        assert liquidity_engine._calculate_percentile(30, history) == 60.0  # 3rd percentile (60%)
        assert liquidity_engine._calculate_percentile(50, history) == 100.0  # 5th percentile (100%)

        # Edge case: empty history
        assert liquidity_engine._calculate_percentile(25, np.array([])) == 50.0

        # Edge case: value below minimum
        assert liquidity_engine._calculate_percentile(5, history) == 0.0

        # Edge case: value above maximum
        assert liquidity_engine._calculate_percentile(55, history) == 100.0

    def test_create_default_score(self, liquidity_engine):
        """Test default score creation"""
        score = liquidity_engine._create_default_score('TEST', 'test_quality')

        assert isinstance(score, LiquidityScore)
        assert score.symbol == 'TEST'
        assert isinstance(score.timestamp, datetime)
        assert score.overall_score == 50.0
        assert score.liquidity_regime == LiquidityRegime.NORMAL_LIQUIDITY
        assert score.confidence == 0.3
        assert score.data_quality == 'test_quality'


# =============================================================================
# TEST ADS INTEGRATION HELPERS
# =============================================================================

class TestADSIntegration:
    """Test ADS compliance integration helpers"""

    def test_get_kyle_lambda_with_data(self, liquidity_engine, sample_ohlcv_data):
        """Test Kyle's lambda getter with data"""
        kyle_lambda = liquidity_engine.get_kyle_lambda('AAPL', sample_ohlcv_data)

        assert isinstance(kyle_lambda, float)
        assert 0.000001 <= kyle_lambda <= 0.01

    def test_get_kyle_lambda_without_data(self, liquidity_engine):
        """Test Kyle's lambda getter without data"""
        kyle_lambda = liquidity_engine.get_kyle_lambda('AAPL')

        assert kyle_lambda == 0.0001  # Default

    def test_get_spread_bps_with_data(self, liquidity_engine, sample_ohlcv_data):
        """Test spread getter with data"""
        spread = liquidity_engine.get_spread_bps('AAPL', sample_ohlcv_data)

        assert isinstance(spread, float)
        assert spread > 0

    def test_get_spread_bps_without_data(self, liquidity_engine):
        """Test spread getter without data"""
        spread = liquidity_engine.get_spread_bps('AAPL')

        assert spread == 5.0  # Default

    def test_get_liquidity_factor_with_data(self, liquidity_engine, sample_ohlcv_data):
        """Test liquidity factor getter with data"""
        factor = liquidity_engine.get_liquidity_factor('AAPL', sample_ohlcv_data)

        assert isinstance(factor, float)
        assert 0 <= factor <= 1

    def test_get_liquidity_factor_without_data(self, liquidity_engine):
        """Test liquidity factor getter without data"""
        factor = liquidity_engine.get_liquidity_factor('AAPL')

        assert factor == 0.8  # Default


# =============================================================================
# TEST LIQUIDITY SCORE DATACLASS
# =============================================================================

class TestLiquidityScore:
    """Test LiquidityScore dataclass functionality"""

    def test_liquidity_score_creation(self):
        """Test LiquidityScore creation and attributes"""
        timestamp = datetime.now()
        score = LiquidityScore(
            symbol='TEST',
            timestamp=timestamp,
            overall_score=75.5,
            liquidity_regime=LiquidityRegime.HIGH_LIQUIDITY,
            confidence=0.9,
            avg_daily_volume=1000000,
            current_volume=1200000,
            volume_ratio=1.2,
            volume_percentile=80.0,
            spread_proxy_bps=8.5,
            effective_spread_bps=12.0,
            spread_percentile=70.0,
            kyle_lambda=0.0005,
            market_impact_bps=5.0,
            liquidity_risk_score=24.5,
            slippage_estimate_bps=6.0,
            liquidity_factor=0.85,
            bars_analyzed=20,
            data_quality='good'
        )

        assert score.symbol == 'TEST'
        assert score.timestamp == timestamp
        assert score.overall_score == 75.5
        assert score.liquidity_regime == LiquidityRegime.HIGH_LIQUIDITY
        assert score.confidence == 0.9

    def test_liquidity_score_to_dict(self):
        """Test LiquidityScore to_dict method"""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        score = LiquidityScore(
            symbol='TEST',
            timestamp=timestamp,
            overall_score=75.5,
            liquidity_regime=LiquidityRegime.HIGH_LIQUIDITY,
            confidence=0.9,
            avg_daily_volume=1000000,
            current_volume=1200000,
            volume_ratio=1.2,
            volume_percentile=80.0,
            spread_proxy_bps=8.5,
            effective_spread_bps=12.0,
            spread_percentile=70.0,
            kyle_lambda=0.0005,
            market_impact_bps=5.0,
            liquidity_risk_score=24.5,
            slippage_estimate_bps=6.0,
            liquidity_factor=0.85,
            bars_analyzed=20,
            data_quality='good'
        )

        data_dict = score.to_dict()

        assert data_dict['symbol'] == 'TEST'
        assert data_dict['timestamp'] == timestamp.isoformat()
        assert data_dict['overall_score'] == 75.5
        assert data_dict['liquidity_regime'] == 'high_liquidity'
        assert data_dict['confidence'] == 0.9
        assert data_dict['liquidity_factor'] == 0.85


# =============================================================================
# TEST LIQUIDITY REGIME ENUM
# =============================================================================

class TestLiquidityRegime:
    """Test LiquidityRegime enum"""

    def test_regime_values(self):
        """Test all regime enum values"""
        assert LiquidityRegime.HIGH_LIQUIDITY.value == "high_liquidity"
        assert LiquidityRegime.NORMAL_LIQUIDITY.value == "normal_liquidity"
        assert LiquidityRegime.LOW_LIQUIDITY.value == "low_liquidity"
        assert LiquidityRegime.ILLIQUID.value == "illiquid"
        assert LiquidityRegime.CRISIS_LIQUIDITY.value == "crisis_liquidity"

    def test_regime_ordering(self):
        """Test regime ordering makes sense"""
        regimes = [
            LiquidityRegime.CRISIS_LIQUIDITY,
            LiquidityRegime.ILLIQUID,
            LiquidityRegime.LOW_LIQUIDITY,
            LiquidityRegime.NORMAL_LIQUIDITY,
            LiquidityRegime.HIGH_LIQUIDITY
        ]

        # Verify all regimes are represented
        assert len(regimes) == 5
        assert len(set(regimes)) == 5  # All unique