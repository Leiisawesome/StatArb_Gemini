import pytest
import pandas as pd
import numpy as np
from picker.ranker import Ranker

@pytest.fixture
def sample_config():
    return {
        'selection': {
            'target_count': 2,
            'hysteresis': {
                'keep_rank_threshold': 3,
                'enter_rank_threshold': 2
            },
            'weights': {
                'liquidity': 0.4,
                'stability': 0.3,
                'efficiency': 0.3
            }
        }
    }

@pytest.fixture
def sample_candidates():
    data = {
        'symbol': ['A', 'B', 'C', 'D'],
        'dollar_vol': [1000000, 500000, 100000, 50000],
        'realized_vol': [0.2, 0.1, 0.3, 0.4],
        'avg_spread_bps': [10, 5, 20, 30],
        'liquidity_stability': [1.0, 0.5, 2.0, 3.0],
        'mean_reversion': [0.1, 0.8, 0.2, 0.4],
        'market_cap': [100e9, 50e9, 1e9, 0.5e9],
        'ticker_type': ['CS', 'CS', 'CS', 'CS'],
        'sector': ['Tech', 'Tech', 'Finance', 'Finance']
    }
    return pd.DataFrame(data).set_index('symbol')

def test_ranker_regime_weights(sample_config, sample_candidates):
    # Add regime weights to config
    sample_config['selection']['regime_weights'] = {
        'choppy': {
            'mean_reversion': 0.8,
            'liquidity': 0.1,
            'stability': 0.1
        }
    }
    ranker = Ranker(sample_config)
    
    # B has highest mean_reversion (0.8)
    result = ranker.select_universe(sample_candidates, regime_label='choppy')
    universe = result['symbols']
    
    assert 'B' in universe
    assert universe['B']['rank'] == 1

def test_ranker_basic(sample_config, sample_candidates):
    ranker = Ranker(sample_config)
    result = ranker.select_universe(sample_candidates)
    universe = result['symbols']
    
    assert len(universe) == 2
    # B should be top ranked because it has low vol and low spread
    assert 'B' in universe
    assert universe['B']['rank'] == 1

def test_ranker_hysteresis(sample_config, sample_candidates):
    ranker = Ranker(sample_config)
    
    # Previous universe has 'C' which is ranked lower
    # But if it's within keep_rank_threshold, it might stay if we have space
    # Actually the logic in ranker.py is:
    # if is_incumbent: if rank <= keep_rank_threshold: selected.append(symbol)
    # else: if rank <= enter_rank_threshold: selected.append(symbol)
    
    # Let's see the ranks first
    # A: high liq, med vol, med spread
    # B: med liq, low vol, low spread -> likely #1
    # C: low liq, high vol, high spread -> likely #3 or #4
    
    previous = {'C'}
    result = ranker.select_universe(sample_candidates, previous_universe=previous)
    universe = result['symbols']
    
    # Even if C is incumbent, if its rank is > 3 (keep_rank_threshold), it won't be selected by hysteresis
    # But it might be selected by fallback if we don't reach target_count
    
    assert len(universe) == 2

def test_ranker_empty(sample_config):
    ranker = Ranker(sample_config)
    result = ranker.select_universe(pd.DataFrame())
    assert result['symbols'] == {}

def test_ranker_normalize_edge_case(sample_config):
    ranker = Ranker(sample_config)
    series = pd.Series([10, 10, 10])
    norm = ranker._normalize(series)
    assert (norm == 0.5).all()

def test_ranker_fallback_logic(sample_config, sample_candidates):
    # Set target count higher than what can be filled by Pass 1 & 2
    sample_config['selection']['target_count'] = 10
    ranker = Ranker(sample_config)
    
    result = ranker.select_universe(sample_candidates)
    # Should still return all 4 candidates because of fallback
    assert len(result['symbols']) == 4

def test_ranker_clustering(sample_config):
    # Need at least 5 symbols for clustering
    sample_config['selection']['target_count'] = 6
    sample_config['selection']['hysteresis']['enter_rank_threshold'] = 10
    data = {
        'symbol': ['A', 'B', 'C', 'D', 'E', 'F'],
        'dollar_vol': [1e6]*6,
        'realized_vol': [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
        'avg_spread_bps': [5]*6,
        'market_cap': [10e9]*6,
        'ticker_type': ['CS']*6,
        'sector': ['Tech']*6
    }
    df = pd.DataFrame(data).set_index('symbol')
    ranker = Ranker(sample_config)
    result = ranker.select_universe(df)
    
    assert len(result['symbols']) >= 5
    assert 'clusters' in result['diagnostics']
    assert len(result['diagnostics']['clusters']) > 0

def test_ranker_regime_policy(sample_config, sample_candidates):
    sample_config['selection']['regime_policies'] = {
        'volatile': {
            'weights': {'stability': 1.0, 'liquidity': 0.0, 'efficiency': 0.0},
            'buckets': {'large': 1, 'mid': 1, 'etf': 1, 'small': 1}
        }
    }
    ranker = Ranker(sample_config)
    result = ranker.select_universe(sample_candidates, regime_label='volatile')
    
    # In 'volatile' regime, we only care about stability
    # B has lowest vol (0.1), so it should be rank 1
    assert result['symbols']['B']['rank'] == 1
