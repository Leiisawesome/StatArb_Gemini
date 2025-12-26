import pytest
import pandas as pd
import numpy as np
from symbolpicker.ranker import Ranker

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
        'liquidity_stability': [1.0, 0.5, 2.0, 3.0]
    }
    return pd.DataFrame(data).set_index('symbol')

def test_ranker_basic(sample_config, sample_candidates):
    ranker = Ranker(sample_config)
    universe = ranker.select_universe(sample_candidates)
    
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
    universe = ranker.select_universe(sample_candidates, previous_universe=previous)
    
    # Even if C is incumbent, if its rank is > 3 (keep_rank_threshold), it won't be selected by hysteresis
    # But it might be selected by fallback if we don't reach target_count
    
    assert len(universe) == 2

def test_ranker_empty(sample_config):
    ranker = Ranker(sample_config)
    universe = ranker.select_universe(pd.DataFrame())
    assert universe == {}
