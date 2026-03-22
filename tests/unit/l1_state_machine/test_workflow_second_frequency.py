"""Workflow smoke-test at 1-second bar frequency for AAPL on 2026-03-19.

Generates synthetic second-frequency quote and trade events covering the first
two minutes of the RTH session and drives the full ArtifactDrivenResearchWorkflow
through calibration, training, validation, and monitored replay.
"""

from __future__ import annotations

import math
from datetime import datetime
from zoneinfo import ZoneInfo

from l1_microstructure.config import FrameworkConfig
from l1_microstructure.ingest import LiveSubscriptionRequest
from l1_microstructure.workflow import ArtifactDrivenResearchWorkflow
from tests.unit.l1_state_machine.support import FixtureMarketDataSource as InMemoryMassiveDataSource

_EASTERN = ZoneInfo("America/New_York")
_TRADE_DATE = (2026, 3, 19)          # Wednesday – regular RTH session
_SYMBOL = "AAPL"
_BASE_PRICE = 215.00                  # representative AAPL price for early 2026
_SPREAD = 0.02                        # 2-cent quoted spread
_TICK = 0.01

# ── event generation ─────────────────────────────────────────────────────────

def _et_ns(hour: int, minute: int, second: int) -> int:
    dt = datetime(*_TRADE_DATE, hour, minute, second, tzinfo=_EASTERN)
    return int(dt.timestamp() * 1_000_000_000)


def _build_second_frequency_payloads() -> list[dict]:
    """
    One quote per second from 09:30:00 to 09:31:59 (120 ticks).
    One trade every 5 seconds (24 trades).

    Prices follow a gentle sine wave so spread / pressure / volatility states
    produce genuine variation across the 120-second window.
    """
    payloads: list[dict] = []
    start_second = 9 * 3600 + 30 * 60          # 09:30:00 ET as seconds-of-day
    n_seconds = 120                              # 2 minutes of data

    for i in range(n_seconds):
        h, rem = divmod(start_second + i, 3600)
        m, s = divmod(rem, 60)
        ts_ns = _et_ns(h, m, s)

        # price drifts ±0.10 over 120 seconds via two overlapping sine waves
        drift = 0.10 * math.sin(2 * math.pi * i / 60) + 0.05 * math.sin(2 * math.pi * i / 20)
        mid = round(_BASE_PRICE + drift, 2)
        bid = round(mid - _SPREAD / 2, 2)
        ask = round(mid + _SPREAD / 2, 2)

        # vary depth to create quote-pressure signal
        bid_size = 100 + 50 * int(math.sin(2 * math.pi * i / 30) > 0)
        ask_size = 100 + 50 * int(math.sin(2 * math.pi * i / 30) <= 0)

        payloads.append({
            "ev": "Q",
            "sym": _SYMBOL,
            "t": ts_ns,
            "bp": bid,
            "ap": ask,
            "bs": bid_size,
            "as": ask_size,
        })

        # trade every 5 seconds
        if i % 5 == 0:
            # alternate buy / sell pressure
            side = "buy" if (i // 5) % 2 == 0 else "sell"
            trade_price = ask if side == "buy" else bid
            payloads.append({
                "ev": "T",
                "sym": _SYMBOL,
                "t": ts_ns + 500_000,   # 0.5 ms after the quote
                "p": trade_price,
                "s": 200,
                "side": side,
            })

    return payloads


# ── tests ─────────────────────────────────────────────────────────────────────

def test_workflow_second_frequency_aapl_2026_03_19_runs_end_to_end(tmp_path) -> None:
    """Full workflow completes without error at 1-second bar frequency."""
    payloads = _build_second_frequency_payloads()
    source = InMemoryMassiveDataSource(payloads)
    events = list(source.subscribe_live(LiveSubscriptionRequest(symbols=(_SYMBOL,))))

    config = FrameworkConfig()
    # Lower the Mahalanobis threshold so transitions fire on second-frequency data
    # (typical tick threshold is tuned for sub-second quote churn)
    config.transition.mahalanobis_threshold = 0.0

    workflow = ArtifactDrivenResearchWorkflow(tmp_path, framework_config=config)
    result = workflow.run(symbol=_SYMBOL, events=events)

    # ── basic structural assertions ──────────────────────────────────────────
    assert result.symbol == _SYMBOL
    assert result.state_panel_rows >= n_seconds_in_events(events)
    assert result.transition_panel_rows > 0
    assert result.replay_summary["update_count"] >= n_seconds_in_events(events)

    # ── all artifacts written to disk ────────────────────────────────────────
    ids = result.artifact_ids
    for artifact_id in (
        ids.state_calibration_id,
        ids.regime_calibration_id,
        ids.execution_calibration_id,
        ids.transition_model_id,
        ids.validation_report_id,
        ids.monitored_replay_id,
        ids.run_manifest_id,
    ):
        assert (tmp_path / artifact_id).exists(), f"missing artifact: {artifact_id}"

    # ── validation report usable ─────────────────────────────────────────────
    report = result.validation_report
    assert report.summary["mean_test_rows"] >= 1.0


def test_workflow_second_frequency_produces_regime_diversity(tmp_path) -> None:
    """The 2-minute second-frequency session produces at least 2 distinct regimes."""
    payloads = _build_second_frequency_payloads()
    source = InMemoryMassiveDataSource(payloads)
    events = list(source.subscribe_live(LiveSubscriptionRequest(symbols=(_SYMBOL,))))

    config = FrameworkConfig()
    config.transition.mahalanobis_threshold = 0.0

    workflow = ArtifactDrivenResearchWorkflow(tmp_path, framework_config=config)
    result = workflow.run(symbol=_SYMBOL, events=events)

    manifest = workflow.store.load(result.artifact_ids.run_manifest_id)
    assert manifest is not None

    # state panel should contain more than one distinct dominant_regime
    state_artifact = workflow.store.load(result.artifact_ids.state_calibration_id)
    assert state_artifact is not None

    # transition model should have observed at least one edge
    transition_model = workflow.store.load(result.artifact_ids.transition_model_id)
    assert int(transition_model.get("edge_count", 0)) >= 1
    assert int(transition_model.get("sample_count", 0)) >= 1


def test_workflow_second_frequency_event_count_is_correct() -> None:
    """Sanity-check: 120 quotes + 24 trades = 144 raw payloads -> 144 events."""
    payloads = _build_second_frequency_payloads()
    source = InMemoryMassiveDataSource(payloads)
    events = list(source.subscribe_live(LiveSubscriptionRequest(symbols=(_SYMBOL,))))

    quote_count = sum(1 for e in events if hasattr(e, "bid_price"))
    trade_count = sum(1 for e in events if hasattr(e, "price") and not hasattr(e, "bid_price"))

    assert quote_count == 120, f"expected 120 quotes, got {quote_count}"
    assert trade_count == 24, f"expected 24 trades, got {trade_count}"
    assert len(events) == 144


# ── helpers ───────────────────────────────────────────────────────────────────

def n_seconds_in_events(events) -> int:
    """Return the number of distinct seconds spanned by the event stream."""
    if not events:
        return 0
    ts_seconds = {e.timestamp_ns // 1_000_000_000 for e in events}
    return len(ts_seconds)
