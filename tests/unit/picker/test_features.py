import pytest
import pandas as pd
import numpy as np
from picker.features import IntradayFeatureEngine

@pytest.fixture
def sample_config():
    return {
        'features': {
            'lookback_days': 1
        }
    }

@pytest.fixture
def sample_minute_data():
    # Create 20 minutes of data for two symbols to ensure sub-sampling works
    times = pd.date_range("2023-01-01 09:30", periods=20, freq="min")
    
    df1 = pd.DataFrame({
        'timestamp': times,
        'open': [100.0] * 20,
        'high': [101.0] * 20,
        'low': [99.0] * 20,
        'close': [100.0, 101.0, 99.0, 100.0, 101.0, 99.0, 100.0, 101.0, 99.0, 100.0] * 2,
        'volume': [1000] * 20
    })
    
    df2 = pd.DataFrame({
        'timestamp': times,
        'open': [200.0] * 20,
        'high': [200.1] * 20,
        'low': [199.9] * 20,
        'close': [200.0] * 20,
        'volume': [500] * 20
    })
    
    return {
        'SYM1': df1,
        'SYM2': df2
    }

def test_compute_features(sample_config, sample_minute_data):
    engine = IntradayFeatureEngine(sample_config)
    features_df = engine.compute_features(sample_minute_data)
    
    assert not features_df.empty
    assert 'SYM1' in features_df.index
    assert 'SYM2' in features_df.index
    assert 'realized_vol' in features_df.columns
    assert 'avg_spread_bps' in features_df.columns
    assert 'liquidity_stability' in features_df.columns
    
    # SYM1 has more price movement, so realized_vol should be higher than SYM2
    assert features_df.loc['SYM1', 'realized_vol'] > features_df.loc['SYM2', 'realized_vol']
    
    # SYM1 spread: (101-99)/100 = 0.02 = 200 bps
    # SYM2 spread: (200.1-199.9)/200 = 0.001 = 10 bps
    assert features_df.loc['SYM1', 'avg_spread_bps'] == pytest.approx(200.0, rel=1e-3)
    assert features_df.loc['SYM2', 'avg_spread_bps'] == pytest.approx(10.0, rel=1e-3)
    
    # Check mean_reversion feature
    assert 'mean_reversion' in features_df.columns
    # SYM1 has price crosses, SYM2 is flat
    assert features_df.loc['SYM1', 'mean_reversion'] >= 0

def test_compute_micro_stability(sample_config):
    engine = IntradayFeatureEngine(sample_config)
    
    # Create 10 seconds of data
    times = pd.date_range("2023-01-01 09:30", periods=10, freq="s")
    df = pd.DataFrame({
        'timestamp': times,
        'close': [100.0, 100.1, 100.0, 99.9, 100.0, 100.1, 100.0, 99.9, 100.0, 100.1],
        'volume': [100, 100, 0, 100, 100, 0, 100, 100, 0, 100] # 3 voids
    })
    
    score_dict = engine.compute_micro_stability({'SYM1': df})
    assert 'SYM1' in score_dict
    score = score_dict['SYM1']['micro_score']
    assert 0 <= score <= 1
    # With 3 voids out of 10, and some jitter, score should be less than 1
    assert score < 1.0

def test_compute_features_empty(sample_config):
    engine = IntradayFeatureEngine(sample_config)
    features_df = engine.compute_features({})
    assert features_df.empty
