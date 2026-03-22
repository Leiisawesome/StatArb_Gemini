from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from l1_microstructure.events import MarketEvent, QuoteEvent, TradeEvent, TradeSide

from .interfaces import EventNormalizer, SessionFilter

_EASTERN = ZoneInfo("America/New_York")
_DEFAULT_EXCLUDED_TRADE_CONDITIONS = frozenset(
    {
        "average_price",
        "closing_auction",
        "closing_print",
        "correction",
        "derivatively_priced",
        "late",
        "late_report",
        "opening_auction",
        "opening_print",
        "out_of_sequence",
        "prior_reference_price",
        "sold_out_of_sequence",
    }
)


@dataclass(frozen=True, slots=True)
class ExclusionWindow:
    start_ns: int
    end_ns: int
    label: str = "custom"
    symbols: tuple[str, ...] | None = None

    def contains(self, timestamp_ns: int) -> bool:
        return self.start_ns <= timestamp_ns <= self.end_ns

    def applies_to(self, symbol: str) -> bool:
        return self.symbols is None or symbol in self.symbols

    def accepts(self, symbol: str, timestamp_ns: int) -> bool:
        return self.applies_to(symbol) and self.contains(timestamp_ns)


@dataclass(frozen=True, slots=True)
class MassiveFilterConfig:
    exclude_trade_conditions: frozenset[str] = _DEFAULT_EXCLUDED_TRADE_CONDITIONS
    exclude_corrections: bool = True
    exclude_late_prints: bool = True
    apply_trade_correction_lifecycle: bool = True
    opening_auction_exclusion_seconds: int = 0
    closing_auction_exclusion_seconds: int = 0
    macro_exclusion_windows: tuple[ExclusionWindow, ...] = ()
    earnings_exclusion_windows: tuple[ExclusionWindow, ...] = ()
    exclude_halted_periods: bool = True
    post_halt_resume_exclusion_seconds: int = 0
    exclude_active_auction_periods: bool = True
    post_auction_resume_exclusion_seconds: int = 0


def _coerce_timestamp_ns(payload: dict[str, Any]) -> int:
    explicit_ns_keys = ("sip_timestamp", "participant_timestamp", "timestamp_ns")
    inferred_unit_keys = ("timestamp", "t")
    for key in (*explicit_ns_keys, *inferred_unit_keys):
        value = payload.get(key)
        if value is None:
            continue
        timestamp = int(value)
        if key in explicit_ns_keys:
            return timestamp
        return _infer_epoch_timestamp_ns(timestamp)
    raise ValueError("payload is missing a timestamp field")


def _infer_epoch_timestamp_ns(timestamp: int) -> int:
    absolute_timestamp = abs(timestamp)
    if absolute_timestamp >= 100_000_000_000_000_000:
        return timestamp
    if absolute_timestamp >= 100_000_000_000_000:
        return timestamp * 1_000
    if absolute_timestamp >= 100_000_000_000:
        return timestamp * 1_000_000
    return timestamp * 1_000_000_000


def _coerce_symbol(payload: dict[str, Any]) -> str:
    for key in ("symbol", "ticker", "sym"):
        value = payload.get(key)
        if value:
            return str(value)
    raise ValueError("payload is missing a symbol field")


def _event_priority(event: MarketEvent) -> int:
    return 0 if isinstance(event, QuoteEvent) else 1


def event_sort_key(event: MarketEvent) -> tuple[int, int, int]:
    sequence_number = event.sequence_number if event.sequence_number is not None else (2**31 - 1)
    return event.timestamp_ns, sequence_number, _event_priority(event)


@dataclass(slots=True)
class RTHSessionFilter(SessionFilter):
    market_open_hour: int = 9
    market_open_minute: int = 30
    market_close_hour: int = 16
    market_close_minute: int = 0

    def accepts(self, symbol: str, timestamp_ns: int) -> bool:
        minute_of_day = _minute_of_day(timestamp_ns)
        open_minute = self.market_open_hour * 60 + self.market_open_minute
        close_minute = self.market_close_hour * 60 + self.market_close_minute
        return open_minute <= minute_of_day < close_minute


@dataclass(slots=True)
class ExtendedHoursSessionFilter(SessionFilter):
    include_rth: bool = True
    include_premarket: bool = False
    include_after_hours: bool = False
    premarket_open_hour: int = 4
    premarket_open_minute: int = 0
    market_open_hour: int = 9
    market_open_minute: int = 30
    market_close_hour: int = 16
    market_close_minute: int = 0
    after_hours_close_hour: int = 20
    after_hours_close_minute: int = 0

    def accepts(self, symbol: str, timestamp_ns: int) -> bool:
        minute_of_day = _minute_of_day(timestamp_ns)
        premarket_open = self.premarket_open_hour * 60 + self.premarket_open_minute
        market_open = self.market_open_hour * 60 + self.market_open_minute
        market_close = self.market_close_hour * 60 + self.market_close_minute
        after_hours_close = self.after_hours_close_hour * 60 + self.after_hours_close_minute
        if self.include_premarket and premarket_open <= minute_of_day < market_open:
            return True
        if self.include_rth and market_open <= minute_of_day < market_close:
            return True
        if self.include_after_hours and market_close <= minute_of_day < after_hours_close:
            return True
        return False


def _minute_of_day(timestamp_ns: int) -> int:
    timestamp = datetime.fromtimestamp(timestamp_ns / 1_000_000_000.0, tz=timezone.utc).astimezone(_EASTERN)
    return timestamp.hour * 60 + timestamp.minute


class MassivePayloadNormalizer(EventNormalizer):
    def normalize(self, payload: dict[str, Any] | Any) -> MarketEvent | None:
        if isinstance(payload, (QuoteEvent, TradeEvent)):
            return payload
        if not isinstance(payload, dict):
            raise TypeError("MassivePayloadNormalizer expects dict-like payloads or normalized events")

        event_type = str(payload.get("ev") or payload.get("event_type") or payload.get("type") or "").lower()
        if event_type in {"q", "quote"}:
            return self._normalize_quote(payload)
        if event_type in {"t", "trade"}:
            return self._normalize_trade(payload)

        if {"bid_price", "ask_price"}.issubset(payload) or {"bp", "ap"}.issubset(payload):
            return self._normalize_quote(payload)
        if "price" in payload or "p" in payload:
            return self._normalize_trade(payload)
        return None

    def _normalize_quote(self, payload: dict[str, Any]) -> QuoteEvent:
        return QuoteEvent(
            symbol=_coerce_symbol(payload),
            timestamp_ns=_coerce_timestamp_ns(payload),
            bid_price=float(payload.get("bid_price", payload.get("bp"))),
            ask_price=float(payload.get("ask_price", payload.get("ap"))),
            bid_size=int(payload.get("bid_size", payload.get("bs"))),
            ask_size=int(payload.get("ask_size", payload.get("as"))),
            exchange=self._coerce_optional_string(payload, "exchange", "bx", "x"),
            sequence_number=self._coerce_optional_int(payload, "sequence_number", "q", "seq"),
        )

    def _normalize_trade(self, payload: dict[str, Any]) -> TradeEvent:
        return TradeEvent(
            symbol=_coerce_symbol(payload),
            timestamp_ns=_coerce_timestamp_ns(payload),
            price=float(payload.get("price", payload.get("p"))),
            size=int(payload.get("size", payload.get("s"))),
            side=self._coerce_trade_side(payload),
            exchange=self._coerce_optional_string(payload, "exchange", "x"),
            sequence_number=self._coerce_optional_int(payload, "sequence_number", "q", "seq"),
        )

    @staticmethod
    def _coerce_optional_string(payload: dict[str, Any], *keys: str) -> str | None:
        for key in keys:
            value = payload.get(key)
            if value is not None:
                return str(value)
        return None

    @staticmethod
    def _coerce_optional_int(payload: dict[str, Any], *keys: str) -> int | None:
        for key in keys:
            value = payload.get(key)
            if value is not None:
                return int(value)
        return None

    @staticmethod
    def _coerce_trade_side(payload: dict[str, Any]) -> TradeSide:
        raw_side = payload.get("side")
        if raw_side is None:
            return TradeSide.UNKNOWN
        side = str(raw_side).lower()
        if side in {"b", "buy", "bid"}:
            return TradeSide.BUY
        if side in {"s", "sell", "ask"}:
            return TradeSide.SELL
        return TradeSide.UNKNOWN


class MassiveEventFilterMixin:
    normalizer: EventNormalizer
    session_filter: SessionFilter
    filter_config: MassiveFilterConfig
    _active_halts: dict[str, int]
    _resume_exclusion_until_ns: dict[str, int]
    _active_auctions: dict[str, int]
    _auction_resume_exclusion_until_ns: dict[str, int]
    _active_trade_indices: dict[str, int]
    _all_exclusion_windows: tuple

    def _initialize_massive_event_filters(
        self,
        normalizer: EventNormalizer | None,
        session_filter: SessionFilter | None,
        filter_config: MassiveFilterConfig | None,
    ) -> None:
        self.normalizer = normalizer or MassivePayloadNormalizer()
        self.session_filter = session_filter or RTHSessionFilter()
        self.filter_config = filter_config or MassiveFilterConfig()
        # Pre-concatenate once; avoids tuple construction on every _in_exclusion_window call
        self._all_exclusion_windows = (
            *self.filter_config.macro_exclusion_windows,
            *self.filter_config.earnings_exclusion_windows,
        )
        self._reset_halt_state()

    def _normalize_payloads(self, payloads: Iterable[dict[str, Any] | MarketEvent]) -> list[MarketEvent]:
        self._reset_halt_state()
        events: list[MarketEvent | None] = []
        for payload in self._sorted_payloads(payloads):
            halt_signal = self._halt_signal(payload)
            if halt_signal is not None:
                self._apply_halt_signal(halt_signal)
                continue
            auction_signal = self._auction_signal(payload)
            if auction_signal is not None:
                self._apply_auction_signal(auction_signal)
                continue
            if self._apply_trade_correction_lifecycle(payload, events):
                continue
            if not self._payload_is_eligible(payload):
                continue
            event = self.normalizer.normalize(payload)
            if event is not None:
                if not self._event_is_eligible(event):
                    continue
                events.append(event)
                self._register_trade_event(event, payload, len(events) - 1)
        return sorted([event for event in events if event is not None], key=event_sort_key)

    def _payload_is_eligible(self, payload: dict[str, Any] | MarketEvent) -> bool:
        if isinstance(payload, (QuoteEvent, TradeEvent)):
            return not self._in_halt_exclusion(payload.symbol, payload.timestamp_ns)
        if not isinstance(payload, dict):
            return False
        event_type = str(payload.get("ev") or payload.get("event_type") or payload.get("type") or "").lower()
        if event_type not in {"q", "quote", "t", "trade"} and not (
            {"bid_price", "ask_price"}.issubset(payload)
            or {"bp", "ap"}.issubset(payload)
            or "price" in payload
            or "p" in payload
        ):
            return False
        symbol = _coerce_symbol(payload)
        timestamp_ns = _coerce_timestamp_ns(payload)
        if self._in_exclusion_window(symbol, timestamp_ns):
            return False
        if self._in_auction_exclusion(timestamp_ns):
            return False
        if self._in_active_auction_exclusion(symbol, timestamp_ns):
            return False
        if self._in_halt_exclusion(symbol, timestamp_ns):
            return False
        if event_type in {"t", "trade"} or "price" in payload or "p" in payload:
            if self.filter_config.exclude_corrections and self._is_correction(payload):
                return False
            if self.filter_config.exclude_late_prints and self._is_late_print(payload):
                return False
            if self._trade_conditions(payload) & self.filter_config.exclude_trade_conditions:
                return False
        return True

    def _event_is_eligible(self, event: MarketEvent) -> bool:
        timestamp_ns = event.timestamp_ns
        if self._in_exclusion_window(event.symbol, timestamp_ns):
            return False
        if self._in_auction_exclusion(timestamp_ns):
            return False
        if self._in_active_auction_exclusion(event.symbol, timestamp_ns):
            return False
        if self._in_halt_exclusion(event.symbol, timestamp_ns):
            return False
        return True

    def _in_exclusion_window(self, symbol: str, timestamp_ns: int) -> bool:
        return any(window.accepts(symbol, timestamp_ns) for window in self._all_exclusion_windows)

    def _in_halt_exclusion(self, symbol: str, timestamp_ns: int) -> bool:
        if not self.filter_config.exclude_halted_periods:
            return False
        halt_start_ns = self._active_halts.get(symbol)
        if halt_start_ns is not None and timestamp_ns >= halt_start_ns:
            return True
        resume_cutoff_ns = self._resume_exclusion_until_ns.get(symbol)
        if resume_cutoff_ns is not None and timestamp_ns <= resume_cutoff_ns:
            return True
        return False

    def _apply_halt_signal(self, signal: tuple[str, str, int]) -> None:
        symbol, action, timestamp_ns = signal
        if action == "halt":
            self._active_halts[symbol] = timestamp_ns
            self._resume_exclusion_until_ns.pop(symbol, None)
            return
        self._active_halts.pop(symbol, None)
        resume_buffer_ns = int(max(self.filter_config.post_halt_resume_exclusion_seconds, 0) * 1_000_000_000)
        if resume_buffer_ns > 0:
            self._resume_exclusion_until_ns[symbol] = timestamp_ns + resume_buffer_ns
        else:
            self._resume_exclusion_until_ns.pop(symbol, None)

    def _in_active_auction_exclusion(self, symbol: str, timestamp_ns: int) -> bool:
        if not self.filter_config.exclude_active_auction_periods:
            return False
        auction_start_ns = self._active_auctions.get(symbol)
        if auction_start_ns is not None and timestamp_ns >= auction_start_ns:
            return True
        resume_cutoff_ns = self._auction_resume_exclusion_until_ns.get(symbol)
        if resume_cutoff_ns is not None and timestamp_ns <= resume_cutoff_ns:
            return True
        return False

    def _apply_auction_signal(self, signal: tuple[str, str, int]) -> None:
        symbol, action, timestamp_ns = signal
        if action == "start":
            self._active_auctions[symbol] = timestamp_ns
            self._auction_resume_exclusion_until_ns.pop(symbol, None)
            return
        self._active_auctions.pop(symbol, None)
        resume_buffer_ns = int(max(self.filter_config.post_auction_resume_exclusion_seconds, 0) * 1_000_000_000)
        if resume_buffer_ns > 0:
            self._auction_resume_exclusion_until_ns[symbol] = timestamp_ns + resume_buffer_ns
        else:
            self._auction_resume_exclusion_until_ns.pop(symbol, None)

    def _reset_halt_state(self) -> None:
        self._active_halts = {}
        self._resume_exclusion_until_ns = {}
        self._active_auctions = {}
        self._auction_resume_exclusion_until_ns = {}
        self._active_trade_indices = {}

    def _apply_trade_correction_lifecycle(
        self,
        payload: dict[str, Any] | MarketEvent,
        events: list[MarketEvent | None],
    ) -> bool:
        if not self.filter_config.apply_trade_correction_lifecycle:
            return False
        instruction = self._trade_correction_instruction(payload)
        if instruction is None:
            return False
        target_key, action = instruction
        target_index = self._active_trade_indices.pop(target_key, None)
        if target_index is None:
            return True
        events[target_index] = None
        if action == "cancel":
            return True
        if not self._payload_is_eligible_without_correction_filters(payload):
            return True
        replacement_event = self.normalizer.normalize(payload)
        if not isinstance(replacement_event, TradeEvent):
            return True
        if not self._event_is_eligible(replacement_event):
            return True
        events[target_index] = replacement_event
        self._register_trade_event(replacement_event, payload, target_index)
        return True

    def _register_trade_event(self, event: MarketEvent, payload: dict[str, Any] | MarketEvent, event_index: int) -> None:
        if not isinstance(event, TradeEvent):
            return
        for trade_key in self._trade_keys(payload, event):
            self._active_trade_indices[trade_key] = event_index

    def _payload_is_eligible_without_correction_filters(self, payload: dict[str, Any] | MarketEvent) -> bool:
        if isinstance(payload, (QuoteEvent, TradeEvent)):
            return self._payload_is_eligible(payload)
        if not isinstance(payload, dict):
            return False
        event_type = str(payload.get("ev") or payload.get("event_type") or payload.get("type") or "").lower()
        if event_type not in {"t", "trade"} and "price" not in payload and "p" not in payload:
            return self._payload_is_eligible(payload)
        symbol = _coerce_symbol(payload)
        timestamp_ns = _coerce_timestamp_ns(payload)
        if self._in_exclusion_window(symbol, timestamp_ns):
            return False
        if self._in_auction_exclusion(timestamp_ns):
            return False
        if self._in_active_auction_exclusion(symbol, timestamp_ns):
            return False
        if self._in_halt_exclusion(symbol, timestamp_ns):
            return False
        if self.filter_config.exclude_late_prints and self._is_late_print(payload):
            return False
        filtered_conditions = set(self.filter_config.exclude_trade_conditions) - {"correction"}
        return not (self._trade_conditions(payload) & filtered_conditions)

    @staticmethod
    def _trade_keys(payload: dict[str, Any] | MarketEvent, event: TradeEvent | None = None) -> tuple[str, ...]:
        symbol = event.symbol if event is not None else None
        sequence_number = event.sequence_number if event is not None else None
        if isinstance(payload, dict):
            if symbol is None:
                try:
                    symbol = _coerce_symbol(payload)
                except ValueError:
                    symbol = None
            if sequence_number is None:
                for key in ("sequence_number", "q", "seq"):
                    value = payload.get(key)
                    if value is not None:
                        sequence_number = int(value)
                        break
            trade_id = payload.get("trade_id", payload.get("id", payload.get("i")))
        else:
            trade_id = None
        if symbol is None:
            return ()
        keys: list[str] = []
        if sequence_number is not None:
            keys.append(f"{symbol}|seq|{int(sequence_number)}")
        if trade_id is not None:
            keys.append(f"{symbol}|id|{trade_id}")
        return tuple(keys)

    @staticmethod
    def _trade_correction_instruction(payload: dict[str, Any] | MarketEvent) -> tuple[str, str] | None:
        if not isinstance(payload, dict):
            return None
        event_type = str(payload.get("ev") or payload.get("event_type") or payload.get("type") or "").lower()
        if event_type not in {"t", "trade"} and "price" not in payload and "p" not in payload:
            return None
        action_raw = payload.get("correction_action", payload.get("correction_type", payload.get("correction")))
        is_correction = payload.get("is_correction") in (True, 1, "1", "true", "True")
        if action_raw is None and not is_correction:
            return None
        action_text = str(action_raw).strip().lower() if action_raw is not None else "replace"
        action = "cancel" if action_text in {"cancel", "delete", "remove", "cancelled"} else "replace"
        try:
            symbol = _coerce_symbol(payload)
        except ValueError:
            return None
        for key in (
            "original_sequence_number",
            "original_seq",
            "correction_target_sequence_number",
            "corrected_sequence_number",
            "cancel_sequence_number",
        ):
            value = payload.get(key)
            if value is not None:
                return f"{symbol}|seq|{int(value)}", action
        for key in ("original_trade_id", "correction_target_trade_id", "cancel_trade_id"):
            value = payload.get(key)
            if value is not None:
                return f"{symbol}|id|{value}", action
        return None

    @staticmethod
    def _sorted_payloads(payloads: Iterable[dict[str, Any] | MarketEvent]) -> list[dict[str, Any] | MarketEvent]:
        records = list(payloads)

        def sort_key(item: dict[str, Any] | MarketEvent) -> tuple[int, int, int]:
            if isinstance(item, (QuoteEvent, TradeEvent)):
                sequence_number = item.sequence_number if item.sequence_number is not None else (2**31 - 1)
                return item.timestamp_ns, sequence_number, _event_priority(item)
            if isinstance(item, dict):
                timestamp_ns = _coerce_timestamp_ns(item) if any(key in item for key in ("sip_timestamp", "participant_timestamp", "timestamp_ns", "timestamp", "t")) else (2**63 - 1)
                sequence_number = int(item.get("sequence_number", item.get("q", item.get("seq", 2**31 - 1))))
                event_type = str(item.get("ev") or item.get("event_type") or item.get("type") or "").lower()
                priority = 0 if event_type in {"q", "quote"} else 1 if event_type in {"t", "trade"} else 2
                return timestamp_ns, sequence_number, priority
            return 2**63 - 1, 2**31 - 1, 3

        return sorted(records, key=sort_key)

    @staticmethod
    def _halt_signal(payload: dict[str, Any] | MarketEvent) -> tuple[str, str, int] | None:
        if isinstance(payload, (QuoteEvent, TradeEvent)) or not isinstance(payload, dict):
            return None
        event_type = str(payload.get("ev") or payload.get("event_type") or payload.get("type") or "").lower()
        status_fields = [
            str(payload.get("message", "")),
            str(payload.get("status", "")),
            str(payload.get("trading_status", "")),
            str(payload.get("status_reason", "")),
        ]
        status_text = " ".join(value.lower() for value in status_fields if value)
        has_status_shape = event_type in {"status", "s"} or any(field for field in status_fields) or any(
            key in payload for key in ("halted", "trading_halted", "trading_status")
        )
        if not has_status_shape:
            return None
        if payload.get("halted") in (False, 0, "0", "false", "False") or payload.get("trading_halted") in (False, 0, "0", "false", "False"):
            action = "resume"
        elif payload.get("halted") in (True, 1, "1", "true", "True") or payload.get("trading_halted") in (True, 1, "1", "true", "True"):
            action = "halt"
        elif any(token in status_text for token in ("resume", "resumed", "trading_resumed", "trading resumed", "unhalt")):
            action = "resume"
        elif any(token in status_text for token in ("halt", "halted", "paused", "pause", "volatility pause", "ludp", "news pending")):
            action = "halt"
        else:
            return None
        try:
            symbol = _coerce_symbol(payload)
            timestamp_ns = _coerce_timestamp_ns(payload)
        except ValueError:
            return None
        return symbol, action, timestamp_ns

    @staticmethod
    def _auction_signal(payload: dict[str, Any] | MarketEvent) -> tuple[str, str, int] | None:
        if isinstance(payload, (QuoteEvent, TradeEvent)) or not isinstance(payload, dict):
            return None
        event_type = str(payload.get("ev") or payload.get("event_type") or payload.get("type") or "").lower()
        status_fields = [
            str(payload.get("message", "")),
            str(payload.get("status", "")),
            str(payload.get("trading_status", "")),
            str(payload.get("auction_state", "")),
        ]
        status_text = " ".join(value.lower() for value in status_fields if value)
        has_status_shape = event_type in {"status", "s"} or any(field for field in status_fields) or any(
            key in payload for key in ("auction", "auction_active", "auction_state")
        )
        if not has_status_shape or "auction" not in status_text and not any(key in payload for key in ("auction", "auction_active", "auction_state")):
            return None
        if payload.get("auction") in (False, 0, "0", "false", "False") or payload.get("auction_active") in (False, 0, "0", "false", "False"):
            action = "end"
        elif payload.get("auction") in (True, 1, "1", "true", "True") or payload.get("auction_active") in (True, 1, "1", "true", "True"):
            action = "start"
        elif any(token in status_text for token in ("auction complete", "auction ended", "cross complete", "resume continuous", "continuous trading resumed")):
            action = "end"
        elif any(token in status_text for token in ("opening auction", "closing auction", "auction started", "auction imbalance", "cross pending")):
            action = "start"
        else:
            return None
        try:
            symbol = _coerce_symbol(payload)
            timestamp_ns = _coerce_timestamp_ns(payload)
        except ValueError:
            return None
        return symbol, action, timestamp_ns

    def _in_auction_exclusion(self, timestamp_ns: int) -> bool:
        timestamp = datetime.fromtimestamp(timestamp_ns / 1_000_000_000.0, tz=timezone.utc).astimezone(_EASTERN)
        minute_of_day = timestamp.hour * 60 + timestamp.minute
        second_of_minute = timestamp.second
        open_seconds = self.filter_config.opening_auction_exclusion_seconds
        close_seconds = self.filter_config.closing_auction_exclusion_seconds
        if open_seconds > 0:
            seconds_from_open = ((minute_of_day - (9 * 60 + 30)) * 60) + second_of_minute
            if 0 <= seconds_from_open < open_seconds:
                return True
        if close_seconds > 0:
            seconds_to_close = (((16 * 60) - minute_of_day) * 60) - second_of_minute
            if 0 <= seconds_to_close < close_seconds:
                return True
        return False

    @staticmethod
    def _is_correction(payload: dict[str, Any]) -> bool:
        for key in ("is_correction", "correction", "correction_indicator", "corrected"):
            if payload.get(key) in (True, 1, "1", "true", "True"):
                return True
        return False

    @staticmethod
    def _is_late_print(payload: dict[str, Any]) -> bool:
        for key in ("is_late", "late", "late_report"):
            if payload.get(key) in (True, 1, "1", "true", "True"):
                return True
        return "late" in MassiveEventFilterMixin._trade_conditions(payload)

    @staticmethod
    def _trade_conditions(payload: dict[str, Any]) -> set[str]:
        raw_conditions = payload.get("conditions", payload.get("condition", payload.get("c")))
        if raw_conditions is None:
            return set()
        values = raw_conditions if isinstance(raw_conditions, (list, tuple, set)) else (raw_conditions,)
        return {str(value).strip().lower() for value in values if str(value).strip()}
