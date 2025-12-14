from datetime import datetime

import pandas as pd

from core_engine.processing.pipeline_orchestrator import ProcessingPipelineOrchestrator

def test_get_liquidity_at_timestamp_exact_and_nearest():
    orchestrator = ProcessingPipelineOrchestrator()
    symbol = "TSLA"
    timestamps = [
        datetime(2024, 1, 2, 9, 30),
        datetime(2024, 1, 2, 9, 31),
        datetime(2024, 1, 2, 9, 32),
    ]
    sequence = [
        {'timestamp': timestamps[0], 'overall_score': 60.0, 'bar_index': 0},
        {'timestamp': timestamps[1], 'overall_score': 55.0, 'bar_index': 1},
        {'timestamp': timestamps[2], 'overall_score': 50.0, 'bar_index': 2},
    ]
    orchestrator.liquidity_sequence[symbol] = sequence
    orchestrator.liquidity_by_timestamp[symbol] = {entry['timestamp']: entry for entry in sequence}

    exact = orchestrator.get_liquidity_at_timestamp(symbol, timestamps[1])
    assert exact['overall_score'] == 55.0

    nearest = orchestrator.get_liquidity_at_timestamp(symbol, datetime(2024, 1, 2, 9, 31, 30))
    assert nearest['overall_score'] == 55.0

def test_merge_liquidity_features_adds_columns():
    orchestrator = ProcessingPipelineOrchestrator()
    symbol = "TSLA"
    timestamp = datetime(2024, 1, 2, 9, 30)
    orchestrator.liquidity_sequence[symbol] = [{
        'timestamp': timestamp,
        'overall_score': 72.0,
        'confidence': 0.8,
        'liquidity_regime': 'normal_liquidity',
        'liquidity_risk_score': 25.0,
        'slippage_risk': 1.5,
        'bid_ask_spread_bps': 4.0,
        'effective_spread_bps': 5.5,
        'market_depth': 60000,
        'volume_ratio': 1.1,
        'bar_index': 0
    }]
    orchestrator.liquidity_by_timestamp[symbol] = {
        timestamp: orchestrator.liquidity_sequence[symbol][0]
    }

    features_df = pd.DataFrame({
        'timestamp': [timestamp],
        'feature': [1.0]
    })

    merged = orchestrator._merge_liquidity_features(features_df, symbol)
    assert 'liquidity_score' in merged.columns
    assert 'liquidity_regime' in merged.columns
    assert merged.loc[0, 'liquidity_score'] == 72.0
    assert merged.loc[0, 'liquidity_regime'] == 'normal_liquidity'

