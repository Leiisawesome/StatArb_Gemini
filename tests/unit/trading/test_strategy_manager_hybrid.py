#!/usr/bin/env python3
"""
Hybrid MOM/MR recombination tests
"""

import pytest

from core_engine.trading.strategies.manager import (
    StrategyManager,
    TradingSignal,
    SignalType,
    SignalStrength,
)
from core_engine.type_definitions.strategy import StrategyType


@pytest.fixture
def strategy_manager():
    config = {
        "min_confidence_threshold": 0.6,
        "enable_signal_aggregation": True,
    }
    manager = StrategyManager(config)
    manager.hybrid_config.enable_hybrid_recombination = True
    return manager


def _make_signal(symbol, strategy_type, signal_type, confidence, strength, source):
    return TradingSignal(
        signal_id="test",
        strategy_name=source,
        strategy_type=strategy_type,
        symbol=symbol,
        signal_type=signal_type,
        strength=strength,
        confidence=confidence,
        expected_return=0.01,
        risk_score=0.2,
        quantity=0.0,
        target_weight=0.05,
        quantity_type="PERCENTAGE",
        metadata={
            "signal_source": source,
            "expected_holding_period": 5,
            "volatility_normalized_strength": 0.7,
        },
    )


def test_recombine_mom_mr(strategy_manager):
    mom = _make_signal(
        symbol="AAPL",
        strategy_type=StrategyType.MOMENTUM,
        signal_type=SignalType.LONG_ENTRY,
        confidence=0.8,
        strength=SignalStrength.STRONG,
        source="momentum",
    )
    mr = _make_signal(
        symbol="AAPL",
        strategy_type=StrategyType.MEAN_REVERSION,
        signal_type=SignalType.LONG_ENTRY,
        confidence=0.7,
        strength=SignalStrength.MODERATE,
        source="mean_reversion",
    )

    hybrid = strategy_manager._recombine_mom_mr_signals("AAPL", [mom, mr], {"regime": "trending"})
    assert hybrid is not None
    assert hybrid.strategy_name == "hybrid_mom_mr"
    assert hybrid.metadata["signal_source"] == "hybrid_mom_mr"
    assert hybrid.metadata["weights"]["mom"] > 0
    assert hybrid.metadata["weights"]["mr"] > 0
