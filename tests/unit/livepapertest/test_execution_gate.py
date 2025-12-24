import os
import pytest
from livepapertest.execution.execution_gate import ExecutionGate, ExecutionGateConfig

def test_execution_gate_orders_enabled():
    cfg = ExecutionGateConfig(enable_orders_config=True, enable_orders_cli=True)
    gate = ExecutionGate(cfg)
    assert gate.orders_enabled() is True
    assert gate.should_block() is None

def test_execution_gate_orders_disabled_config():
    cfg = ExecutionGateConfig(enable_orders_config=False, enable_orders_cli=True)
    gate = ExecutionGate(cfg)
    assert gate.orders_enabled() is False
    assert gate.should_block() == "enable_orders_config_false"

def test_execution_gate_orders_disabled_cli():
    cfg = ExecutionGateConfig(enable_orders_config=True, enable_orders_cli=False)
    gate = ExecutionGate(cfg)
    assert gate.orders_enabled() is False
    assert gate.should_block() == "enable_orders_cli_missing"

def test_execution_gate_kill_switch(monkeypatch):
    cfg = ExecutionGateConfig(enable_orders_config=True, enable_orders_cli=True)
    gate = ExecutionGate(cfg)
    
    monkeypatch.setenv("LIVEPAPER_KILL_SWITCH", "1")
    assert gate.is_kill_switch_active() is True
    assert gate.orders_enabled() is False
    assert gate.should_block() == "kill_switch_env"
    
    monkeypatch.setenv("LIVEPAPER_KILL_SWITCH", "true")
    assert gate.is_kill_switch_active() is True
    
    monkeypatch.setenv("LIVEPAPER_KILL_SWITCH", "0")
    assert gate.is_kill_switch_active() is False
    assert gate.orders_enabled() is True

def test_execution_gate_stale_data_block():
    def mock_guard(symbol):
        return symbol == "AAPL"
    
    cfg = ExecutionGateConfig(
        enable_orders_config=True, 
        enable_orders_cli=True,
        should_block_orders=mock_guard
    )
    gate = ExecutionGate(cfg)
    
    assert gate.should_block("AAPL") == "data_stale_block"
    assert gate.should_block("MSFT") is None

def test_execution_gate_guard_error():
    def mock_guard(symbol):
        raise Exception("Guard failed")
    
    cfg = ExecutionGateConfig(
        enable_orders_config=True, 
        enable_orders_cli=True,
        should_block_orders=mock_guard
    )
    gate = ExecutionGate(cfg)
    
    assert gate.should_block("AAPL") == "data_stale_guard_error"

def test_execution_gate_block_payload():
    cfg = ExecutionGateConfig(enable_orders_config=False)
    gate = ExecutionGate(cfg)
    reason = gate.should_block("AAPL")
    payload = gate.block_payload(reason, "AAPL")
    
    assert payload["blocked"] is True
    assert payload["reason"] == "enable_orders_config_false"
    assert payload["symbol"] == "AAPL"
    assert "timestamp" in payload
    assert payload["kill_switch_env_var"] == "LIVEPAPER_KILL_SWITCH"
