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
    mock_polygon.get_bars_multi = AsyncMock()
    
    # Mock return data for benchmarks
    mock_df = pd.DataFrame({'close': [100, 101, 102]})
    mock_polygon.get_bars_multi.return_value = {
        'SPY': mock_df,
        'TLT': mock_df
    }
    
    # Mock the internal analyzer
    adapter.analyzer = MagicMock()
    adapter.analyzer.analyze_market_regime.return_value = {
        'regime_summary': {
            'primary_regime': 'BULL',
            'risk_environment': 'RISK_ON',
            'market_cycle': 'EXPANSION',
            'confidence': 0.8,
            'stress_levels': {}
        }
    }
    
    result = await adapter.generate_regime_label(mock_polygon, datetime.now())
    
    assert result['label'] == 'BULL'
    assert result['confidence'] == 0.8
    assert result['risk_environment'] == 'RISK_ON'

@pytest.mark.asyncio
async def test_regime_adapter_no_data(sample_config):
    adapter = RegimeAdapter(sample_config)
    mock_polygon = MagicMock()
    mock_polygon.get_bars_multi = AsyncMock(return_value={})
    
    result = await adapter.generate_regime_label(mock_polygon, datetime.now())
    assert result['label'] == 'UNKNOWN'
    assert result['confidence'] == 0.0
