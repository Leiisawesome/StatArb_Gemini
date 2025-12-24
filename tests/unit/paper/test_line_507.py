import pytest
from unittest.mock import MagicMock
from core_engine.paper.engine import PaperTradingEngine, PaperTradingConfig

@pytest.mark.asyncio
async def test_line_507():
    config = PaperTradingConfig(session_id="test")
    engine = PaperTradingEngine(config=config)
    engine._paper_broker = MagicMock()
    engine._paper_broker.set_market_data.side_effect = Exception("Broker error")
    
    event = MagicMock()
    event.symbol = "AAPL"
    event.payload = {"close": 150.0}
    
    await engine._process_bar(event)
    assert engine._paper_broker.set_market_data.called
