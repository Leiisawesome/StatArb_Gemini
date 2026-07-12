"""Typed configuration for the supervised trading runtime."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class OperatingMode(str, Enum):
    PAPER = "paper"
    LIVE = "live"


@dataclass(frozen=True, slots=True)
class RiskLimits:
    daily_loss_fraction: float = 0.01
    max_gross_exposure: float = 0.25
    max_symbol_exposure: float = 0.03
    allow_leverage: bool = False
    allow_shorting: bool = False


@dataclass(frozen=True, slots=True)
class SessionPolicy:
    timezone: str = "America/New_York"
    market_open: str = "09:30"
    stop_entries: str = "15:50"
    flatten_at: str = "15:58"
    market_close: str = "16:00"


@dataclass(frozen=True, slots=True)
class ProductionConfig:
    symbols: tuple[str, ...]
    artifact_root: Path
    promoted_run_ids: dict[str, str]
    database_path: Path = Path("var/trading.sqlite3")
    mode: OperatingMode = OperatingMode.PAPER
    broker_env_file: Path | None = Path("broker.env")
    api_host: str = "127.0.0.1"
    api_port: int = 8765
    event_stale_after_seconds: float = 5.0
    warmup_seconds: float = 1800.0
    reconnect_backoff_seconds: float = 15.0
    flatten_timeout_seconds: float = 60.0
    risk: RiskLimits = field(default_factory=RiskLimits)
    session: SessionPolicy = field(default_factory=SessionPolicy)
    live_risk_acknowledgement: str | None = None

    def __post_init__(self) -> None:
        normalized = tuple(symbol.strip().upper() for symbol in self.symbols)
        if not normalized or len(normalized) > 25:
            raise ValueError("production runtime requires between 1 and 25 symbols")
        if len(set(normalized)) != len(normalized):
            raise ValueError("production symbols must be unique")
        object.__setattr__(self, "symbols", normalized)
        missing_models = [symbol for symbol in normalized if not self.promoted_run_ids.get(symbol)]
        if missing_models:
            raise ValueError(f"missing promoted run ids for symbols: {missing_models}")
        if self.api_host not in {"127.0.0.1", "::1", "localhost"}:
            raise ValueError("production API must bind to localhost")
        if self.event_stale_after_seconds <= 0:
            raise ValueError("event_stale_after_seconds must be positive")
        if self.warmup_seconds < 0:
            raise ValueError("warmup_seconds cannot be negative")
        if self.reconnect_backoff_seconds <= 0 or self.flatten_timeout_seconds <= 0:
            raise ValueError("reconnect and flatten timeouts must be positive")
        self._validate_fraction("daily_loss_fraction", self.risk.daily_loss_fraction)
        self._validate_fraction("max_gross_exposure", self.risk.max_gross_exposure)
        self._validate_fraction("max_symbol_exposure", self.risk.max_symbol_exposure)
        if self.risk.max_symbol_exposure > self.risk.max_gross_exposure:
            raise ValueError("max_symbol_exposure cannot exceed max_gross_exposure")
        if self.mode is OperatingMode.LIVE and self.live_risk_acknowledgement != "I_ACCEPT_LIVE_CAPITAL_RISK":
            raise ValueError("live mode requires the explicit live capital risk acknowledgement")

    @classmethod
    def from_json(cls, path: str | Path) -> "ProductionConfig":
        source = Path(path)
        payload = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("production configuration must be a JSON object")
        risk = RiskLimits(**dict(payload.pop("risk", {})))
        session = SessionPolicy(**dict(payload.pop("session", {})))
        for key in ("artifact_root", "database_path", "broker_env_file"):
            if payload.get(key) is not None:
                payload[key] = Path(payload[key]).expanduser()
        payload["symbols"] = tuple(payload["symbols"])
        payload["mode"] = OperatingMode(payload.get("mode", OperatingMode.PAPER.value))
        return cls(risk=risk, session=session, **payload)

    def public_dict(self) -> dict[str, Any]:
        return {
            "symbols": list(self.symbols),
            "artifact_root": str(self.artifact_root),
            "database_path": str(self.database_path),
            "mode": self.mode.value,
            "api_host": self.api_host,
            "api_port": self.api_port,
            "event_stale_after_seconds": self.event_stale_after_seconds,
            "warmup_seconds": self.warmup_seconds,
        }

    @staticmethod
    def _validate_fraction(name: str, value: float) -> None:
        if not 0.0 < float(value) <= 1.0:
            raise ValueError(f"{name} must be in (0, 1]")
