"""
Unit tests for EnhancedBaseStrategy (Rule 7 aligned)

Focus:
- lifecycle wiring basics
- PositionBook SSOT helpers (_has_position, _get_position_quantity)
- health/status reporting doesn't depend on legacy internal position state
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pytest

from core_engine.trading.strategies.base_strategy_enhanced import EnhancedBaseStrategy
from core_engine.trading.strategies.contracts import StrategySignal
from core_engine.type_definitions.strategy import StrategyType, SignalType


@dataclass
class MockConfig:
    strategy_id: str = "mock_strategy"
    strategy_type: StrategyType = StrategyType.CUSTOM
    symbols: List[str] = field(default_factory=lambda: ["AAPL"])
    paper_trading_mode: bool = True
    max_position_size: float = 0.1
    max_daily_loss: float = 0.02


class _MockPosition:
    def __init__(self, quantity: float, is_short: bool = False):
        self.quantity = abs(float(quantity))
        self.is_short = bool(is_short)

    @property
    def is_flat(self) -> bool:
        return self.quantity == 0.0


class _MockPositionBook:
    def __init__(self, positions: Optional[Dict[str, _MockPosition]] = None):
        self._positions = positions or {}

    def get_position(self, symbol: str) -> Optional[_MockPosition]:
        return self._positions.get(symbol)

    def get_all_positions(self) -> Dict[str, _MockPosition]:
        return dict(self._positions)


class MockStrategy(EnhancedBaseStrategy):
    async def generate_signals(self, market_data: Dict[str, Any]) -> List[StrategySignal]:
        return [
            StrategySignal(
                strategy_id=self.strategy_id,
                symbol="AAPL",
                signal_type=SignalType.HOLD,
                strength=0.0,
                confidence=0.0,
            )
        ]

    async def _initialize_strategy_components(self) -> bool:
        return True

    async def _start_strategy_operations(self) -> bool:
        return True

    async def _stop_strategy_operations(self) -> None:
        return None

    async def _check_strategy_health(self) -> Dict[str, Any]:
        return {"strategy_healthy": True}

    def _get_strategy_config_summary(self) -> Dict[str, Any]:
        return {"strategy_type": "Mock"}


def test_position_book_helpers() -> None:
    s = MockStrategy(MockConfig())
    pb = _MockPositionBook(
        positions={
            "AAPL": _MockPosition(quantity=10.0, is_short=False),
            "TSLA": _MockPosition(quantity=5.0, is_short=True),
        }
    )
    s.set_position_book(pb)  # SSOT injection

    assert s._has_position("AAPL") is True
    assert s._has_position("MSFT") is False

    assert s._get_position_quantity("AAPL") == 10.0
    assert s._get_position_quantity("TSLA") == -5.0
    assert s._get_position_quantity("MSFT") == 0.0


@pytest.mark.asyncio
async def test_health_check_does_not_require_legacy_position_state() -> None:
    s = MockStrategy(MockConfig())
    res = await s.health_check()
    assert "healthy" in res
    assert "strategy_id" in res

