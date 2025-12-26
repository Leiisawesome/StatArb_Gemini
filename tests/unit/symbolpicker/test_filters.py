import pytest
import pandas as pd
from symbolpicker.filters import CoarseFilter

@pytest.fixture
def sample_config():
    return {
        'filters': {
            'min_price': 5.0,
            'min_adv_30d': 1000000,
            'exclude_tickers': ['XYZ']
        }
    }

@pytest.fixture
def sample_snapshot():
    data = {
        'symbol': ['AAPL', 'MSFT', 'PENY', 'LONGTICKER', 'XYZ'],
        'close': [150.0, 300.0, 1.0, 100.0, 200.0],
        'volume': [100000, 50000, 1000000, 20000, 10000]
    }
    df = pd.DataFrame(data).set_index('symbol')
    return df

def test_coarse_filter_basic(sample_config, sample_snapshot):
    cf = CoarseFilter(sample_config)
    candidates = cf.filter_universe(sample_snapshot)
    
    # AAPL: price 150 >= 5, adv 15M >= 1M, len 4 <= 4 -> PASS
    # MSFT: price 300 >= 5, adv 15M >= 1M, len 4 <= 4 -> PASS
    # PENY: price 1 < 5 -> FAIL
    # LONGTICKER: len 10 > 4 -> FAIL
    # XYZ: in exclude_tickers -> FAIL
    
    assert 'AAPL' in candidates
    assert 'MSFT' in candidates
    assert 'PENY' not in candidates
    assert 'LONGTICKER' not in candidates
    assert 'XYZ' not in candidates
    assert len(candidates) == 2

def test_coarse_filter_empty(sample_config):
    cf = CoarseFilter(sample_config)
    candidates = cf.filter_universe(pd.DataFrame())
    assert candidates == []

def test_coarse_filter_no_matches(sample_config):
    cf = CoarseFilter(sample_config)
    data = {
        'symbol': ['PENY'],
        'close': [1.0],
        'volume': [100]
    }
    df = pd.DataFrame(data).set_index('symbol')
    candidates = cf.filter_universe(df)
    assert candidates == []
