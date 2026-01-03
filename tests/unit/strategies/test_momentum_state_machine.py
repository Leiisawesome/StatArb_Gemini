import pytest
import pandas as pd
from datetime import datetime, time
from core_engine.trading.strategies.implementations.momentum.momentum_state_machine import (
    MomentumStateMachine, SymbolStateName
)

@pytest.fixture
def state_machine():
    return MomentumStateMachine()

@pytest.fixture
def mock_config():
    class Config:
        orb_minutes = 15
        tightness_threshold = 0.75
        setup_expiry_bars = 10
        max_extension_atr = 1.5
        anchor_ma = 'sma_20'
    return Config()

def create_mock_bar(price, high=None, low=None, volume_ratio=1.0, timestamp=None, atr=1.0, sma_20=None):
    """Helper to create a data row."""
    data = {
        'close': price,
        'high': high if high is not None else price,
        'low': low if low is not None else price,
        'volume_ratio': volume_ratio,
        'atr': atr,
        'ATR_14': atr,
        'sma_20': sma_20 if sma_20 is not None else price - 2.0
    }
    series = pd.Series(data)
    series.name = timestamp if timestamp else datetime(2024, 12, 20, 10, 30)
    return series

def test_initialization(state_machine):
    state = state_machine.get_state("TSLA")
    assert state.state == SymbolStateName.FLAT
    assert state.symbol == "TSLA"

def test_orb_filter(state_machine, mock_config):
    # Bar during ORB (10:30 - 15 mins = 10:45)
    ts = datetime(2024, 12, 20, 9, 35) # 5 mins after open
    bar = create_mock_bar(100, timestamp=ts)
    df = pd.DataFrame([bar])
    
    triggered, reason = state_machine.evaluate("TSLA", 0, bar, df, mock_config)
    assert not triggered
    assert state_machine.get_state("TSLA").state == SymbolStateName.FLAT

def test_setup_identification(state_machine, mock_config):
    # Setup data for near-high and tightness
    # Index 20+, not in ORB
    ts = datetime(2024, 12, 20, 11, 0)
    
    # Create history (20 bars)
    history = []
    for i in range(20):
        history.append(create_mock_bar(100, high=105, low=95))
    
    # Current bar: Near high (104.5 >= 0.98 * 105), Tightness (ratio < 0.75)
    # Average ATR in history is 1.0. Current ATR 0.5 -> ratio 0.5
    current_bar = create_mock_bar(104.5, high=105, low=104, timestamp=ts, atr=0.5)
    df = pd.DataFrame(history + [current_bar])
    
    triggered, reason = state_machine.evaluate("TSLA", 20, current_bar, df, mock_config)
    
    assert not triggered
    assert reason == "setup_identified"
    state = state_machine.get_state("TSLA")
    assert state.state == SymbolStateName.SETUP_BREAKOUT
    assert state.setup_high == 105.0
    assert state.setup_low == 95.0

def test_setup_invalidation_price(state_machine, mock_config):
    # First get into setup
    test_setup_identification(state_machine, mock_config)
    
    # Breach setup low (95.0)
    bad_bar = create_mock_bar(94.0, timestamp=datetime(2024, 12, 20, 11, 5))
    df = pd.DataFrame([bad_bar]) # df not strictly used for state check here but for structure
    
    triggered, reason = state_machine.evaluate("TSLA", 21, bad_bar, df, mock_config)
    assert not triggered
    assert reason == "invalidation_price_breach"
    assert state_machine.get_state("TSLA").state == SymbolStateName.FLAT

def test_setup_expiry(state_machine, mock_config):
    test_setup_identification(state_machine, mock_config)
    
    # Age the setup
    state = state_machine.get_state("TSLA")
    for _ in range(11): # Expiry is 10
        bar = create_mock_bar(104.0)
        state_machine.evaluate("TSLA", 21, bar, pd.DataFrame([bar]), mock_config)
        
    assert state.state == SymbolStateName.FLAT

def test_trigger_breakout(state_machine, mock_config):
    test_setup_identification(state_machine, mock_config)
    
    # Breakout high (105.0) with volume (> 1.1) and no extension
    trigger_bar = create_mock_bar(106.0, high=107, timestamp=datetime(2024, 12, 20, 11, 5), 
                                 volume_ratio=1.5, sma_20=105.0, atr=1.0)
    # extension = (106 - 105) / 1.0 = 1.0 (< 1.5 threshold)
    
    df = pd.DataFrame([trigger_bar])
    df.columns = trigger_bar.index # Ensure columns match
    
    triggered, reason = state_machine.evaluate("TSLA", 21, trigger_bar, df, mock_config)
    assert triggered
    assert reason == "breakout_acceleration"

def test_extension_trap(state_machine, mock_config):
    test_setup_identification(state_machine, mock_config)
    
    # Breakout high (105.0) but too far from SMA
    # current=110, sma=105, atr=1.0 -> extension = 5.0 (> 1.5)
    trap_bar = create_mock_bar(110.0, timestamp=datetime(2024, 12, 20, 11, 5), 
                              volume_ratio=1.5, sma_20=105.0, atr=1.0)
    
    df = pd.DataFrame([trap_bar])
    triggered, reason = state_machine.evaluate("TSLA", 21, trap_bar, df, mock_config)
    
    assert not triggered
    assert reason == "invalidation_extension_trap"
    assert state_machine.get_state("TSLA").state == SymbolStateName.FLAT

def test_reconciliation(state_machine):
    # Test reconciliation moves state
    state_machine.reconcile("TSLA", True) # Position found
    assert state_machine.get_state("TSLA").state == SymbolStateName.IN_POSITION
    
    state_machine.reconcile("TSLA", False) # Position lost
    assert state_machine.get_state("TSLA").state == SymbolStateName.FLAT

