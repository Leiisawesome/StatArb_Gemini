from datetime import datetime

from core_engine.alpha.ads_components import ADSSMSGateInputs, ERAR, PendingSignalContext, PendingSignalQueue, SignalMaturityScore


def test_pending_queue_tick_all_removes_stale():
    q = PendingSignalQueue(max_pending=50)

    sms = SignalMaturityScore.from_inputs(
        ADSSMSGateInputs(
            setup_maturity=0.5,
            setup_validity_prob=0.5,
            signed_flow_support=0.0,
            vol_compression=1.0,
        ),
        pending_bars=0,
        max_pending=1,  # stale when pending_bars > 1
    )
    ctx = PendingSignalContext(
        symbol="TEST",
        side="BUY",
        sms=sms,
        erar=ERAR(),
        raw_signal_strength=0.5,
        timestamp=datetime.now(),
        entry_price=100.0,
        metadata={},
    )

    q.add(ctx)
    assert q.get("TEST", "BUY") is not None

    removed1 = q.tick_all()
    assert removed1 == []
    assert q.get("TEST", "BUY") is not None
    assert q.get("TEST", "BUY").sms.pending_bars == 1

    removed2 = q.tick_all()
    assert removed2 == ["TEST_BUY"]
    assert q.get("TEST", "BUY") is None


def test_pending_queue_get_mature_signals_emits_and_removes():
    q = PendingSignalQueue(max_pending=50)

    sms = SignalMaturityScore.from_inputs(
        ADSSMSGateInputs(
            setup_maturity=1.0,
            setup_validity_prob=1.0,
            signed_flow_support=1.0,
            vol_compression=0.5,
        ),
        pending_bars=0,
        max_pending=50,
    )
    ctx = PendingSignalContext(
        symbol="TEST",
        side="BUY",
        sms=sms,
        erar=ERAR(),
        raw_signal_strength=1.0,
        timestamp=datetime.now(),
        entry_price=100.0,
        metadata={},
    )
    q.add(ctx)

    out = q.get_mature_signals(threshold=0.10, regime="normal")
    assert len(out) == 1
    assert out[0].symbol == "TEST"
    assert out[0].side == "BUY"
    assert q.get("TEST", "BUY") is None

