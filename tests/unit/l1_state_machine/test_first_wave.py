from __future__ import annotations

import json
from datetime import datetime
from datetime import date
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from l1_microstructure.config import FrameworkConfig
from l1_microstructure.datasets import PipelineTransitionDatasetBuilder
from l1_microstructure.events import QuoteEvent
from l1_microstructure.ingest import ExtendedHoursSessionFilter, ExclusionWindow, HistoricalBatchRequest, LiveSubscriptionRequest, MassiveFilterConfig, MassivePayloadNormalizer, MassiveRESTConfig, MassiveRESTDataSource, MassiveWebSocketConfig, MassiveWebSocketDataSource
from l1_microstructure.labeling import ForwardDriftLabeler, HorizonLabelRequest
from l1_microstructure.replay import DeterministicReplayEngine
from tests.unit.l1_state_machine.support import FixtureMarketDataSource as InMemoryMassiveDataSource


def _et_ns(year: int, month: int, day: int, hour: int, minute: int, second: int = 0) -> int:
    timestamp = datetime(year, month, day, hour, minute, second, tzinfo=ZoneInfo("America/New_York"))
    return int(timestamp.timestamp() * 1_000_000_000)


def test_massive_payload_normalizer_handles_quote_and_trade_payloads() -> None:
    normalizer = MassivePayloadNormalizer()

    quote = normalizer.normalize(
        {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 1, 22, 9, 30, 0), "bp": 100.0, "ap": 100.02, "bs": 200, "as": 100, "q": 7}
    )
    trade = normalizer.normalize(
        {"ev": "T", "sym": "AAPL", "t": _et_ns(2024, 1, 22, 9, 30, 1), "p": 100.02, "s": 150, "side": "buy", "q": 8}
    )

    assert quote is not None
    assert trade is not None
    assert quote.timestamp_ns < trade.timestamp_ns


@pytest.mark.parametrize(
    "payload",
    [
        {"ev": "Q", "sym": "AAPL", "t": 1710163800000, "bp": 100.02, "ap": 100.0, "bs": 100, "as": 100},
        {"ev": "Q", "sym": "AAPL", "t": 1710163800000, "bp": float("nan"), "ap": 100.0, "bs": 100, "as": 100},
        {"ev": "T", "sym": "AAPL", "t": 1710163800000, "p": 0.0, "s": 100},
        {"ev": "T", "sym": "AAPL", "t": 1710163800000, "p": 100.0, "s": 0},
    ],
)
def test_massive_payload_normalizer_drops_invalid_market_values(payload) -> None:
    assert MassivePayloadNormalizer().normalize(payload) is None


def test_massive_payload_normalizer_converts_websocket_millisecond_timestamps_to_nanoseconds() -> None:
    normalizer = MassivePayloadNormalizer()

    quote = normalizer.normalize(
        {"ev": "Q", "sym": "AAPL", "t": 1710163800000, "bp": 100.0, "ap": 100.02, "bs": 200, "as": 100, "q": 7}
    )
    trade = normalizer.normalize(
        {"ev": "T", "sym": "AAPL", "t": 1710163801000, "p": 100.02, "s": 150, "side": "buy", "q": 8}
    )

    assert quote is not None
    assert trade is not None
    assert quote.timestamp_ns == 1710163800000 * 1_000_000
    assert trade.timestamp_ns == 1710163801000 * 1_000_000


def test_massive_payload_normalizer_preserves_rest_nanosecond_timestamps_on_generic_fields() -> None:
    normalizer = MassivePayloadNormalizer()

    quote = normalizer.normalize(
        {
            "ev": "Q",
            "sym": "AAPL",
            "t": _et_ns(2024, 3, 11, 9, 30, 0),
            "bp": 100.0,
            "ap": 100.02,
            "bs": 200,
            "as": 100,
            "q": 7,
        }
    )

    assert quote is not None
    assert quote.timestamp_ns == _et_ns(2024, 3, 11, 9, 30, 0)


def test_in_memory_massive_source_filters_and_orders_rth_events() -> None:
    payloads = [
        {"ev": "T", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 29, 59), "p": 99.9, "s": 100},
        {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 0), "bp": 100.0, "ap": 100.01, "bs": 100, "as": 100, "q": 4},
        {"ev": "T", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 0), "p": 100.01, "s": 200, "q": 9},
    ]
    source = InMemoryMassiveDataSource(payloads)
    request = HistoricalBatchRequest(symbols=("AAPL",), trade_date=date(2024, 3, 11))

    events = list(source.load_historical(request))

    assert len(events) == 2
    assert events[0].timestamp_ns <= events[1].timestamp_ns


def test_extended_hours_session_filter_can_include_premarket_and_after_hours() -> None:
    payloads = [
        {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 8, 0, 0), "bp": 99.5, "ap": 99.55, "bs": 100, "as": 100},
        {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 0), "bp": 100.0, "ap": 100.02, "bs": 100, "as": 100},
        {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 16, 30, 0), "bp": 100.5, "ap": 100.55, "bs": 100, "as": 100},
    ]
    source = InMemoryMassiveDataSource(
        payloads,
        session_filter=ExtendedHoursSessionFilter(include_premarket=True, include_after_hours=True),
    )

    events = list(source.subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))

    assert [event.timestamp_ns for event in events] == [
        _et_ns(2024, 3, 11, 8, 0, 0),
        _et_ns(2024, 3, 11, 9, 30, 0),
        _et_ns(2024, 3, 11, 16, 30, 0),
    ]


def test_extended_hours_session_filter_can_exclude_rth() -> None:
    payloads = [
        {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 8, 0, 0), "bp": 99.5, "ap": 99.55, "bs": 100, "as": 100},
        {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 0), "bp": 100.0, "ap": 100.02, "bs": 100, "as": 100},
        {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 16, 30, 0), "bp": 100.5, "ap": 100.55, "bs": 100, "as": 100},
    ]
    source = InMemoryMassiveDataSource(
        payloads,
        session_filter=ExtendedHoursSessionFilter(include_rth=False, include_premarket=True, include_after_hours=True),
    )

    events = list(source.subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))

    assert [event.timestamp_ns for event in events] == [
        _et_ns(2024, 3, 11, 8, 0, 0),
        _et_ns(2024, 3, 11, 16, 30, 0),
    ]


def test_replay_engine_can_checkpoint_and_resume() -> None:
    source = InMemoryMassiveDataSource(
        [
            {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 0), "bp": 100.0, "ap": 100.01, "bs": 100, "as": 100, "q": 1},
            {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 1), "bp": 100.01, "ap": 100.02, "bs": 100, "as": 100, "q": 2},
            {"ev": "T", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 2), "p": 100.02, "s": 100, "q": 3},
        ]
    )
    events = list(source.subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))
    replay = DeterministicReplayEngine()

    iterator = iter(replay.replay(events))
    first = next(iterator)
    checkpoint = replay.checkpoint()
    resumed_cursor = replay.restore(checkpoint)
    tail = list(replay.replay(events))

    assert first.timestamp_ns < tail[0].timestamp_ns
    assert resumed_cursor.current_index == checkpoint.event_index


def test_forward_drift_labeler_marks_horizon_and_censoring() -> None:
    source = InMemoryMassiveDataSource(
        [
            {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 0), "bp": 100.0, "ap": 100.02, "bs": 200, "as": 100},
            {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 3), "bp": 100.03, "ap": 100.05, "bs": 180, "as": 90},
        ]
    )
    events = list(source.subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))
    labeler = ForwardDriftLabeler()
    label = labeler.label(
        HorizonLabelRequest(symbol="AAPL", horizon_ns=2_000_000_000, start_timestamp_ns=events[0].timestamp_ns, reference_price=100.01),
        events,
    )

    assert label.end_timestamp_ns >= events[0].timestamp_ns + 2_000_000_000
    assert label.realized_drift_bps > 0.0
    assert label.censored is False


def test_forward_drift_labeler_reuses_preindexed_timestamps() -> None:
    reads = 0

    class CountingEvent:
        symbol = "AAPL"

        def __init__(self, timestamp_ns: int):
            self._timestamp_ns = timestamp_ns

        @property
        def timestamp_ns(self) -> int:
            nonlocal reads
            reads += 1
            return self._timestamp_ns

    events = [CountingEvent(1), CountingEvent(2), CountingEvent(3)]
    labeler = ForwardDriftLabeler(preindexed_events={"AAPL": events})
    reads_after_index = reads
    request = HorizonLabelRequest("AAPL", horizon_ns=1, start_timestamp_ns=1, reference_price=100.0)

    labeler.label(request)
    labeler.label(request)

    assert reads == reads_after_index


def test_forward_drift_labeler_does_not_scan_dense_pre_horizon_events(monkeypatch) -> None:
    events = [
        QuoteEvent(
            symbol="AAPL",
            timestamp_ns=index,
            bid_price=100.0 + index / 100_000.0,
            ask_price=100.01 + index / 100_000.0,
            bid_size=100,
            ask_size=100,
        )
        for index in range(10_001)
    ]
    labeler = ForwardDriftLabeler(preindexed_events={"AAPL": events})
    calls = 0
    original = labeler._price_for_event

    def counted(event):
        nonlocal calls
        calls += 1
        return original(event)

    monkeypatch.setattr(labeler, "_price_for_event", counted)

    label = labeler.label(
        HorizonLabelRequest(
            symbol="AAPL",
            horizon_ns=9_000,
            start_timestamp_ns=0,
            reference_price=100.005,
        )
    )

    assert label.end_timestamp_ns == 9_000
    assert not label.censored
    assert calls == 1


def test_dataset_builder_creates_state_and_transition_panels() -> None:
    source = InMemoryMassiveDataSource(
        [
            {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 0), "bp": 100.0, "ap": 100.02, "bs": 100, "as": 100},
            {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 1), "bp": 100.01, "ap": 100.02, "bs": 400, "as": 50},
            {"ev": "T", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 2), "p": 100.02, "s": 400, "side": "buy"},
            {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 4), "bp": 100.04, "ap": 100.08, "bs": 40, "as": 300},
            {"ev": "T", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 5), "p": 100.04, "s": 500, "side": "sell"},
        ]
    )
    events = list(source.subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))
    config = FrameworkConfig()
    config.transition.mahalanobis_threshold = 0.0
    builder = PipelineTransitionDatasetBuilder(events, config=config)

    state_panel = builder.build_state_panel("AAPL")
    transition_panel = builder.build_transition_panel("AAPL")

    assert not state_panel.frame.empty
    assert "state_label" in state_panel.frame.columns
    assert not transition_panel.frame.empty
    assert "horizon_ns" in transition_panel.frame.columns
    assert transition_panel.frame["horizon_ns"].nunique() == len(config.transition.drift_horizon_ns_values)
    assert "realized_drift_bps" in transition_panel.frame.columns


def test_in_memory_massive_source_filters_trade_conditions_and_corrections() -> None:
    payloads = [
        {"ev": "T", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 0), "p": 100.0, "s": 100, "conditions": ["late"]},
        {"ev": "T", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 1), "p": 100.01, "s": 100, "is_correction": True},
        {"ev": "T", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 2), "p": 100.02, "s": 100},
    ]
    source = InMemoryMassiveDataSource(payloads)

    events = list(source.subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))

    assert len(events) == 1
    assert events[0].timestamp_ns == _et_ns(2024, 3, 11, 9, 30, 2)


def test_in_memory_massive_source_applies_trade_correction_replacement_lifecycle() -> None:
    payloads = [
        {"ev": "T", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 0), "p": 100.00, "s": 100, "q": 10},
        {
            "ev": "T",
            "sym": "AAPL",
            "t": _et_ns(2024, 3, 11, 9, 30, 1),
            "p": 100.05,
            "s": 150,
            "q": 11,
            "is_correction": True,
            "correction_action": "replace",
            "original_sequence_number": 10,
        },
    ]
    source = InMemoryMassiveDataSource(
        payloads,
        filter_config=MassiveFilterConfig(exclude_corrections=False, apply_trade_correction_lifecycle=True),
    )

    events = list(source.subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))

    assert len(events) == 1
    assert events[0].timestamp_ns == _et_ns(2024, 3, 11, 9, 30, 1)
    assert events[0].price == 100.05
    assert events[0].size == 150


def test_in_memory_massive_source_applies_trade_correction_cancel_lifecycle() -> None:
    payloads = [
        {"ev": "T", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 0), "p": 100.00, "s": 100, "q": 10},
        {
            "ev": "T",
            "sym": "AAPL",
            "t": _et_ns(2024, 3, 11, 9, 30, 1),
            "p": 100.00,
            "s": 100,
            "q": 12,
            "is_correction": True,
            "correction_action": "cancel",
            "original_sequence_number": 10,
        },
    ]
    source = InMemoryMassiveDataSource(
        payloads,
        filter_config=MassiveFilterConfig(exclude_corrections=False, apply_trade_correction_lifecycle=True),
    )

    events = list(source.subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))

    assert events == []


def test_in_memory_massive_source_applies_macro_and_auction_exclusions() -> None:
    exclusion_window = ExclusionWindow(
        start_ns=_et_ns(2024, 3, 11, 10, 0, 0),
        end_ns=_et_ns(2024, 3, 11, 10, 0, 5),
        label="macro-window",
    )
    source = InMemoryMassiveDataSource(
        [
            {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 0), "bp": 100.0, "ap": 100.02, "bs": 100, "as": 100},
            {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 7), "bp": 100.01, "ap": 100.03, "bs": 100, "as": 100},
            {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 10, 0, 2), "bp": 100.04, "ap": 100.06, "bs": 100, "as": 100},
            {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 10, 1, 0), "bp": 100.05, "ap": 100.07, "bs": 100, "as": 100},
        ],
        filter_config=MassiveFilterConfig(
            opening_auction_exclusion_seconds=5,
            macro_exclusion_windows=(exclusion_window,),
        ),
    )

    events = list(source.subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))

    assert len(events) == 2
    assert events[0].timestamp_ns == _et_ns(2024, 3, 11, 9, 30, 7)
    assert events[1].timestamp_ns == _et_ns(2024, 3, 11, 10, 1, 0)


def test_in_memory_massive_source_applies_symbol_specific_earnings_exclusions() -> None:
    earnings_window = ExclusionWindow(
        start_ns=_et_ns(2024, 3, 11, 11, 0, 0),
        end_ns=_et_ns(2024, 3, 11, 11, 5, 0),
        label="earnings-window",
        symbols=("AAPL",),
    )
    source = InMemoryMassiveDataSource(
        [
            {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 10, 59, 59), "bp": 100.0, "ap": 100.02, "bs": 100, "as": 100},
            {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 11, 0, 30), "bp": 100.01, "ap": 100.03, "bs": 100, "as": 100},
            {"ev": "Q", "sym": "MSFT", "t": _et_ns(2024, 3, 11, 11, 1, 0), "bp": 200.0, "ap": 200.02, "bs": 100, "as": 100},
            {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 11, 6, 0), "bp": 100.02, "ap": 100.04, "bs": 100, "as": 100},
        ],
        filter_config=MassiveFilterConfig(earnings_exclusion_windows=(earnings_window,)),
    )

    aapl_events = list(source.subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))
    msft_events = list(source.subscribe_live(LiveSubscriptionRequest(symbols=("MSFT",))))

    assert [event.timestamp_ns for event in aapl_events] == [_et_ns(2024, 3, 11, 10, 59, 59), _et_ns(2024, 3, 11, 11, 6, 0)]
    assert [event.timestamp_ns for event in msft_events] == [_et_ns(2024, 3, 11, 11, 1, 0)]


def test_in_memory_massive_source_filters_halts_and_post_resume_buffer() -> None:
    source = InMemoryMassiveDataSource(
        [
            {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 0), "bp": 100.0, "ap": 100.02, "bs": 100, "as": 100},
            {"ev": "status", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 1), "status": "trading halted"},
            {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 2), "bp": 100.01, "ap": 100.03, "bs": 100, "as": 100},
            {"ev": "status", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 4), "status": "trading resumed"},
            {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 5), "bp": 100.02, "ap": 100.04, "bs": 100, "as": 100},
            {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 7), "bp": 100.03, "ap": 100.05, "bs": 100, "as": 100},
        ],
        filter_config=MassiveFilterConfig(post_halt_resume_exclusion_seconds=2),
    )

    events = list(source.subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))

    assert [event.timestamp_ns for event in events] == [_et_ns(2024, 3, 11, 9, 30, 0), _et_ns(2024, 3, 11, 9, 30, 7)]


def test_in_memory_massive_source_filters_active_auction_periods_and_post_auction_buffer() -> None:
    source = InMemoryMassiveDataSource(
        [
            {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 0), "bp": 99.98, "ap": 100.00, "bs": 100, "as": 100},
            {"ev": "status", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 0), "status": "opening auction imbalance"},
            {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 1), "bp": 100.00, "ap": 100.02, "bs": 100, "as": 100},
            {"ev": "status", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 3), "status": "auction complete"},
            {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 4), "bp": 100.01, "ap": 100.03, "bs": 100, "as": 100},
            {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 5), "bp": 100.02, "ap": 100.04, "bs": 100, "as": 100},
        ],
        filter_config=MassiveFilterConfig(post_auction_resume_exclusion_seconds=1),
    )

    events = list(source.subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))

    assert [event.timestamp_ns for event in events] == [_et_ns(2024, 3, 11, 9, 30, 0), _et_ns(2024, 3, 11, 9, 30, 5)]


def test_massive_websocket_data_source_streams_and_filters_messages() -> None:
    class FakeWebSocketClient:
        def __init__(self) -> None:
            self.connect_kwargs: dict[str, object] | None = None
            self.closed = False

        def run(self, handle_msg, **kwargs) -> None:
            self.connect_kwargs = kwargs
            handle_msg(json.dumps([{"ev": "status", "message": "connected"}]))
            handle_msg(
                json.dumps(
                    [
                        {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 0), "bp": 100.0, "ap": 100.02, "bs": 100, "as": 100},
                        {"ev": "status", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 1), "status": "trading halted"},
                        {"ev": "T", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 2), "p": 100.01, "s": 100, "conditions": ["late"]},
                        {"ev": "T", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 3), "p": 100.02, "s": 100},
                        {"ev": "status", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 4), "status": "trading resumed"},
                        {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 5), "bp": 100.01, "ap": 100.03, "bs": 100, "as": 100},
                        {"ev": "T", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 7), "p": 100.03, "s": 100},
                    ]
                )
            )

        async def close(self) -> None:
            self.closed = False
            self.closed = True

    fake_client = FakeWebSocketClient()
    source = MassiveWebSocketDataSource(
        MassiveWebSocketConfig(endpoint="wss://example.invalid", api_key="secret"),
        filter_config=MassiveFilterConfig(post_halt_resume_exclusion_seconds=2),
        client_factory=lambda config, request: fake_client,
    )

    events = list(source.subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))

    assert len(events) == 2
    assert events[0].timestamp_ns == _et_ns(2024, 3, 11, 9, 30, 0)
    assert events[1].timestamp_ns == _et_ns(2024, 3, 11, 9, 30, 7)
    assert fake_client.closed is True


def test_massive_websocket_data_source_reorders_cross_channel_events() -> None:
    class FakeWebSocketClient:
        def run(self, handle_msg, **kwargs) -> None:
            handle_msg(
                json.dumps(
                    [
                        {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 0), "bp": 100.0, "ap": 100.02, "bs": 100, "as": 100},
                        {"ev": "T", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 0) + 200_000_000, "p": 100.01, "s": 100},
                        {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 0) + 100_000_000, "bp": 100.01, "ap": 100.03, "bs": 120, "as": 80},
                    ]
                )
            )

        async def close(self) -> None:
            return None

    source = MassiveWebSocketDataSource(
        MassiveWebSocketConfig(endpoint="wss://example.invalid", api_key="secret"),
        client_factory=lambda config, request: FakeWebSocketClient(),
    )

    events = list(source.subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))

    assert [event.timestamp_ns for event in events] == sorted(event.timestamp_ns for event in events)


def test_massive_websocket_config_rejects_negative_reorder_window() -> None:
    with pytest.raises(ValueError, match="reorder window"):
        MassiveWebSocketConfig(reorder_window_seconds=-0.001)


def test_massive_websocket_data_source_filters_active_auction_status_messages() -> None:
    class FakeWebSocketClient:
        def __init__(self) -> None:
            self.closed = False

        def run(self, handle_msg, **kwargs) -> None:
            handle_msg(
                json.dumps(
                    [
                        {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 0), "bp": 99.98, "ap": 100.00, "bs": 100, "as": 100},
                        {"ev": "status", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 0), "status": "opening auction imbalance"},
                        {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 1), "bp": 100.0, "ap": 100.02, "bs": 100, "as": 100},
                        {"ev": "status", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 3), "status": "auction complete"},
                        {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 5), "bp": 100.02, "ap": 100.04, "bs": 100, "as": 100},
                    ]
                )
            )

        async def close(self) -> None:
            self.closed = True

    source = MassiveWebSocketDataSource(
        MassiveWebSocketConfig(endpoint="wss://example.invalid", api_key="secret"),
        filter_config=MassiveFilterConfig(post_auction_resume_exclusion_seconds=1),
        client_factory=lambda config, request: FakeWebSocketClient(),
    )

    events = list(source.subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))

    assert [event.timestamp_ns for event in events] == [_et_ns(2024, 3, 11, 9, 30, 0), _et_ns(2024, 3, 11, 9, 30, 5)]


def test_massive_rest_data_source_merges_quotes_and_trades() -> None:
    class FakeRestClient:
        def list_quotes(self, symbol: str, **kwargs):
            assert symbol == "AAPL"
            return [
                SimpleNamespace(
                    sip_timestamp=_et_ns(2024, 3, 11, 9, 30, 0),
                    participant_timestamp=None,
                    bid_price=100.0,
                    ask_price=100.02,
                    bid_size=100,
                    ask_size=120,
                    bid_exchange=11,
                    ask_exchange=12,
                    sequence_number=1,
                    conditions=None,
                    indicators=None,
                    trf_timestamp=None,
                ),
                SimpleNamespace(
                    sip_timestamp=_et_ns(2024, 3, 11, 9, 30, 2),
                    participant_timestamp=None,
                    bid_price=100.01,
                    ask_price=100.03,
                    bid_size=90,
                    ask_size=110,
                    bid_exchange=11,
                    ask_exchange=12,
                    sequence_number=3,
                    conditions=None,
                    indicators=None,
                    trf_timestamp=None,
                ),
            ]

        def list_trades(self, symbol: str, **kwargs):
            assert symbol == "AAPL"
            return [
                SimpleNamespace(
                    sip_timestamp=_et_ns(2024, 3, 11, 9, 30, 1),
                    participant_timestamp=None,
                    price=100.02,
                    size=200,
                    exchange=11,
                    sequence_number=2,
                    conditions=None,
                    id="trade-1",
                    trf_id=None,
                    trf_timestamp=None,
                    correction=None,
                )
            ]

    source = MassiveRESTDataSource(
        MassiveRESTConfig(api_key="secret"),
        client_factory=lambda config: FakeRestClient(),
    )

    events = list(source.load_historical(HistoricalBatchRequest(symbols=("AAPL",), trade_date=date(2024, 3, 11))))

    assert [event.timestamp_ns for event in events] == [
        _et_ns(2024, 3, 11, 9, 30, 0),
        _et_ns(2024, 3, 11, 9, 30, 1),
        _et_ns(2024, 3, 11, 9, 30, 2),
    ]
