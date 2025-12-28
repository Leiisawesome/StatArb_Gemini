import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
import pandas as pd
from picker.runner import SymbolPickerRunner

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
@patch('picker.runner.create_polygon_rest_service')
@patch('picker.runner.CoarseFilter')
@patch('picker.runner.IntradayFeatureEngine')
@patch('picker.runner.Ranker')
@patch('picker.runner.RegimeAdapter')
@patch('picker.runner.ArtifactExporter')
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
    mock_polygon.get_ticker_details_multi = AsyncMock(return_value={
        'AAPL': {'market_cap': 2e12, 'sic_description': 'Tech', 'type': 'CS'},
        'MSFT': {'market_cap': 2e12, 'sic_description': 'Tech', 'type': 'CS'}
    })
    mock_polygon.get_bars_multi = AsyncMock(return_value={
        'AAPL': pd.DataFrame({'close': [150, 151], 'high': [151, 152], 'low': [149, 150], 'volume': [100, 100]}),
        'MSFT': pd.DataFrame({'close': [300, 301], 'high': [301, 302], 'low': [299, 300], 'volume': [50, 50]})
    })
    mock_polygon.get_bars = AsyncMock(return_value=pd.DataFrame())
    mock_polygon.get_adv_multi = AsyncMock(return_value={'AAPL': 1000000.0, 'MSFT': 500000.0})
    mock_polygon.get_upcoming_earnings = AsyncMock(return_value={})
    mock_polygon.get_last_quote_multi = AsyncMock(return_value={})
    mock_polygon.get_borrow_info_multi = AsyncMock(return_value={})
    mock_polygon.close = AsyncMock()
    mock_create_polygon.return_value = mock_polygon
    
    mock_filter = mock_filter_cls.return_value
    mock_filter.filter_universe.return_value = ['AAPL', 'MSFT']
    
    mock_engine = mock_engine_cls.return_value
    mock_engine.compute_features.return_value = pd.DataFrame({
        'realized_vol': [0.2, 0.1],
        'avg_spread_bps': [10, 5]
    }, index=['AAPL', 'MSFT'])
    
    mock_ranker = mock_ranker_cls.return_value
    mock_ranker.cap_thresholds = {'small_max': 2.0, 'mid_max': 10.0}
    
    def side_effect(df, previous_universe=None, regime_label="UNKNOWN", correlation_matrix=None):
        df['score'] = [0.9, 0.8]
        df['rank'] = [1, 2]
        df['bucket'] = ['large', 'large']
        return {
            'symbols': {
                'AAPL': {'rank': 1, 'score': 0.9, 'bucket': 'large', 'sector': 'Tech', 'metrics': {'dollar_vol': 1000000, 'realized_vol': 0.2, 'avg_spread_bps': 10}},
                'MSFT': {'rank': 2, 'score': 0.8, 'bucket': 'large', 'sector': 'Tech', 'metrics': {'dollar_vol': 500000, 'realized_vol': 0.1, 'avg_spread_bps': 5}}
            },
            'diagnostics': {'churn': 0.0}
        }
    mock_ranker.select_universe.side_effect = side_effect
    
    mock_adapter = mock_adapter_cls.return_value
    mock_adapter.generate_regime_label = AsyncMock(return_value={'primary': 'BULL'})
    
    mock_exporter = mock_exporter_cls.return_value
    mock_exporter.export.return_value = "test_path.json"
    
    # Run
    result = await runner.run(datetime(2023, 1, 1))
    
    assert result['artifact_path'] == "test_path.json"
    mock_filter.filter_universe.assert_called_once()
    mock_engine.compute_features.assert_called_once()
    mock_ranker.select_universe.assert_called_once()
    mock_adapter.generate_regime_label.assert_called_once()
    mock_exporter.export.assert_called_once()
