import pytest
from unittest.mock import MagicMock, AsyncMock, ANY
from livepapertest.execution.gated_unified_execution_engine import GatedUnifiedExecutionEngine, BlockedExecutionResult
from livepapertest.execution.execution_gate import ExecutionGate, ExecutionGateConfig

@pytest.mark.asyncio
async def test_gated_engine_execute_allowed():
    mock_inner = AsyncMock()
    mock_inner.execute_with_mode_routing.return_value = MagicMock(status="FILLED")
    
    cfg = ExecutionGateConfig(enable_orders_config=True, enable_orders_cli=True)
    gate = ExecutionGate(cfg)
    
    engine = GatedUnifiedExecutionEngine(inner=mock_inner, gate=gate)
    
    request = MagicMock()
    result = await engine.execute_with_mode_routing(request)
    
    assert result.status == "FILLED"
    mock_inner.execute_with_mode_routing.assert_called_once_with(request)

@pytest.mark.asyncio
async def test_gated_engine_execute_blocked():
    mock_inner = AsyncMock()
    
    cfg = ExecutionGateConfig(enable_orders_config=False)
    gate = ExecutionGate(cfg)
    
    mock_journal = MagicMock()
    engine = GatedUnifiedExecutionEngine(inner=mock_inner, gate=gate, journal=mock_journal)
    
    request = MagicMock()
    result = await engine.execute_with_mode_routing(request)
    
    assert isinstance(result, BlockedExecutionResult)
    assert result.status == "BLOCKED"
    assert result.reason == "enable_orders_config_false"
    
    mock_inner.execute_with_mode_routing.assert_not_called()
    mock_journal.log_system.assert_called_with("kill_switch_block", ANY)

@pytest.mark.asyncio
async def test_gated_engine_proxy_methods():
    mock_inner = MagicMock()
    gate = MagicMock()
    engine = GatedUnifiedExecutionEngine(inner=mock_inner, gate=gate)
    
    engine.set_live_broker("broker")
    mock_inner.set_live_broker.assert_called_with("broker")
    
    engine.set_execution_mode("mode")
    mock_inner.set_execution_mode.assert_called_with("mode")
    
    engine.set_paper_broker("paper")
    mock_inner.set_paper_broker.assert_called_with("paper")
