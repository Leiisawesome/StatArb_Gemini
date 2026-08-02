"""Fixed synthetic hot-path benchmarks for the shipped trading engine.

Drives real ``L1MicrostructureStateMachine.on_event`` and
``PipelineTransitionDatasetBuilder.build_panels_single_pass`` — not reimplementations.
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from dataclasses import asdict, dataclass
from typing import Sequence

from l1_microstructure.config import FrameworkConfig
from l1_microstructure.datasets.builders import PipelineTransitionDatasetBuilder
from l1_microstructure.events import MarketEvent, QuoteEvent, TradeEvent, TradeSide
from l1_microstructure.pipeline import L1MicrostructureStateMachine


def make_synthetic_events(
    *,
    symbol: str = "AAPL",
    count: int = 20_000,
    start_ns: int = 1_710_163_800_000_000_000,
    step_ns: int = 50_000_000,
) -> list[MarketEvent]:
    """Deterministic high-frequency quote/trade stream (fixed for before/after compare)."""
    events: list[MarketEvent] = []
    bid = 100.0
    ask = 100.02
    bid_size = 100
    ask_size = 100
    for index in range(count):
        timestamp_ns = start_ns + index * step_ns
        phase = index % 7
        if phase == 0:
            bid += 0.01
            bid_size = 80 + (index % 5) * 40
        elif phase == 1:
            ask += 0.01
            ask_size = 60 + (index % 4) * 30
        elif phase == 2:
            bid -= 0.01
            ask -= 0.01
        elif phase == 3:
            bid_size = 200 + (index % 3) * 50
        elif phase == 4:
            ask_size = 150 + (index % 6) * 20
        mid = (bid + ask) * 0.5
        if phase in {0, 1, 2, 3, 4}:
            events.append(
                QuoteEvent(
                    symbol=symbol,
                    timestamp_ns=timestamp_ns,
                    bid_price=bid,
                    ask_price=ask,
                    bid_size=float(bid_size),
                    ask_size=float(ask_size),
                )
            )
        else:
            side = TradeSide.BUY if phase == 5 else TradeSide.SELL
            price = ask if side is TradeSide.BUY else bid
            events.append(
                TradeEvent(
                    symbol=symbol,
                    timestamp_ns=timestamp_ns,
                    price=price if price > 0 else mid,
                    size=100.0 + (index % 10) * 10.0,
                    side=side,
                )
            )
        # keep a positive spread
        if ask <= bid:
            ask = bid + 0.01
    return events


@dataclass(frozen=True, slots=True)
class BenchResult:
    name: str
    event_count: int
    wall_seconds: float
    events_per_second: float
    p95_event_ns: float | None
    updates: int

    def to_dict(self) -> dict[str, float | int | str | None]:
        return asdict(self)


def bench_on_event(
    events: Sequence[MarketEvent],
    *,
    measure_per_event: bool = True,
    config: FrameworkConfig | None = None,
) -> BenchResult:
    machine = L1MicrostructureStateMachine(config or FrameworkConfig())
    # Warm one pass is intentionally skipped so baseline includes cold start fairly
    # for both before/after; same process still uses identical script.
    per_event_ns: list[float] = []
    updates = 0
    started = time.perf_counter()
    if measure_per_event:
        for event in events:
            t0 = time.perf_counter_ns()
            update = machine.on_event(event)
            per_event_ns.append(float(time.perf_counter_ns() - t0))
            if update is not None:
                updates += 1
    else:
        for event in events:
            if machine.on_event(event) is not None:
                updates += 1
    wall = time.perf_counter() - started
    p95 = float(statistics.quantiles(per_event_ns, n=20)[18]) if per_event_ns else None
    return BenchResult(
        name="on_event",
        event_count=len(events),
        wall_seconds=wall,
        events_per_second=(len(events) / wall) if wall > 0 else 0.0,
        p95_event_ns=p95,
        updates=updates,
    )


def bench_build_panels(
    events: Sequence[MarketEvent],
    *,
    symbol: str = "AAPL",
    config: FrameworkConfig | None = None,
) -> BenchResult:
    builder = PipelineTransitionDatasetBuilder(events, config=config or FrameworkConfig())
    started = time.perf_counter()
    state_panel, transition_panel = builder.build_panels_single_pass(symbol)
    wall = time.perf_counter() - started
    return BenchResult(
        name="build_panels_single_pass",
        event_count=len(events),
        wall_seconds=wall,
        events_per_second=(len(events) / wall) if wall > 0 else 0.0,
        p95_event_ns=None,
        updates=int(state_panel.metadata.get("row_count", len(state_panel.frame)))
        + int(transition_panel.metadata.get("row_count", len(transition_panel.frame))),
    )


def run_suite(event_count: int = 20_000) -> dict[str, object]:
    events = make_synthetic_events(count=event_count)
    on_event = bench_on_event(events, measure_per_event=True)
    panels = bench_build_panels(events)
    return {
        "event_count": event_count,
        "on_event": on_event.to_dict(),
        "build_panels_single_pass": panels.to_dict(),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hot-path microbenchmarks for l1_microstructure")
    parser.add_argument("--event-count", type=int, default=20_000)
    parser.add_argument("--json", action="store_true", help="print JSON only")
    args = parser.parse_args(list(argv) if argv is not None else None)
    payload = run_suite(event_count=max(int(args.event_count), 100))
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
