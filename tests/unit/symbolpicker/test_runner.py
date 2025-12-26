import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
import pandas as pd
from symbolpicker.runner import SymbolPickerRunner

@pytest.fixture
def mock_config():
    return {
        'filters': {'min_price': 5, 'min_adv_30d': 1000000},
        'features': {'lookback_days': 1},
        'selection': {
            'target_count': 10,
            'hysteresis': {'keep_rank_threshold': 15, 'enter_rank_threshold': 10},
            'weights': {'liquidity': 0.4, 'stability': 0.3, 'efficiency': 0.3}
        },
        'output': {'directory': 'test_picks', 'filename_format': 'test.json'}
    }

@pytest.mark.asyncio
@patch('symbolpicker.runner.create_polygon_rest_service')
@patch('symbolpicker.runner.CoarseFilter')
@patch('symbolpicker.runner.IntradayFeatureEngine')
@patch('symbolpicker.runner.Ranker')
@patch('symbolpicker.runner.RegimeAdapter')
@patch('symbolpicker.runner.ArtifactExporter')
async def test_runner_run(
    mock_exporter_cls,
    mock_adapter_cls,
    mock_ranker_cls,
    mock_engine_cls,
    mock_filter_cls,
    mock_create_polygon,
    mock_config
):
    # Setup mocks
    runner = SymbolPickerRunner()
    runner.config = mock_config
    
    mock_polygon = MagicMock()
    mock_polygon.is_initialized = True
    mock_polygon.get_grouped_daily_bars = AsyncMock(return_value=pd.DataFrame({
        'close': [150.0, 300.0],
        'volume': [100000, 50000]
    }, index=['AAPL', 'MSFT']))
    mock_polygon.get_bars_multi = AsyncMock(return_value={
        'AAPL': pd.DataFrame({'close': [150, 151], 'high': [151, 152], 'low': [149, 150], 'volume': [100, 100]}),
        'MSFT': pd.DataFrame({'close': [300, 301], 'high': [301, 302], 'low': [299, 300], 'volume': [50, 50]})
    })
    mock_polygon.close = AsyncMock()
    mock_create_polygon.return_value = mock_polygon
    
    mock_filter = mock_filter_cls.return_value
    mock_filter.filter_universe.return_value = ['AAPL', 'MSFT']
    
    mock_engine = mock_engine_cls.return_value
    mock_engine.compute_features.return_value = pd.DataFrame(index=['AAPL', 'MSFT'])
    
    mock_ranker = mock_ranker_cls.return_value
    mock_ranker.select_universe.return_value = {
        'AAPL': {'rank': 1, 'score': 0.9, 'metrics': {'dollar_vol': 1000000, 'realized_vol': 0.2, 'avg_spread_bps': 10}},
        'MSFT': {'rank': 2, 'score': 0.8, 'metrics': {'dollar_vol': 500000, 'realized_vol': 0.1, 'avg_spread_bps': 5}}
    }
    
    mock_adapter = mock_adapter_cls.return_value
    mock_adapter.generate_regime_label = AsyncMock(return_value={'label': 'BULL'})
    
    mock_exporter = mock_exporter_cls.return_value
    mock_exporter.export.return_value = "test_path.json"
    
    # Run
    result = await runner.run(datetime(2023, 1, 1))
    
    assert result == "test_path.json"
    mock_filter.filter_universe.assert_called_once()
    mock_engine.compute_features.assert_called_once()
    mock_ranker.select_universe.assert_called_once()
    mock_adapter.generate_regime_label.assert_called_once()
    mock_exporter.export.assert_called_once()
