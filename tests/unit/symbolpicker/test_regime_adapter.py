import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime
import pandas as pd
from symbolpicker.regime_adapter import RegimeAdapter

@pytest.fixture
def sample_config():
    return {}

@pytest.mark.asyncio
async def test_regime_adapter_basic(sample_config):
    adapter = RegimeAdapter(sample_config)
    
    # Mock Polygon service
    mock_polygon = MagicMock()
    mock_polygon.get_bars = AsyncMock()
    
    # Mock return data for benchmarks
    mock_df = pd.DataFrame({
        'open': [100, 101, 102],
        'high': [105, 106, 107],
        'low': [95, 96, 97],
        'close': [100, 101, 102],
        'volume': [1000, 1100, 1200]
    }, index=pd.date_range('2023-01-01', periods=3))
    mock_polygon.get_bars.return_value = mock_df
    
    # Mock the internal engine
    adapter.engine = MagicMock()
    adapter.engine.process_market_data.return_value = {'market_data_processed': True}
    
    # Mock the current_regime property
    mock_regime = MagicMock()
    mock_regime.primary_regime.value = 'bull'
    mock_regime.confidence = 0.8
    mock_regime.directional_regime = 'bullish'
    mock_regime.volatility_regime = 'low'
    mock_regime.stress_level = 0.1
    adapter.engine.current_regime = mock_regime
    
    result = await adapter.generate_regime_label(mock_polygon, datetime.now())
    
    assert result['primary'] == 'bull'
    assert result['confidence'] == 0.8
    assert result['details']['directional'] == 'bullish'

@pytest.mark.asyncio
async def test_regime_adapter_no_data(sample_config):
    adapter = RegimeAdapter(sample_config)
    mock_polygon = MagicMock()
    mock_polygon.get_bars = AsyncMock(return_value=pd.DataFrame())
    
    result = await adapter.generate_regime_label(mock_polygon, datetime.now())
    assert result['primary'] == 'unknown'
    assert result['confidence'] == 0.0
