"""Typed liveness and trading-readiness reports for supervised production."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class OperationalStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    NOT_READY = "not_ready"


@dataclass(frozen=True, slots=True)
class OperationalCheck:
    code: str
    passed: bool
    message: str
    required: bool = True
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "passed": self.passed,
            "required": self.required,
            "message": self.message,
            "details": dict(self.details),
        }


@dataclass(frozen=True, slots=True)
class RuntimeHealthReport:
    timestamp_ns: int
    status: OperationalStatus
    alive: bool
    checks: tuple[OperationalCheck, ...]

    @classmethod
    def from_checks(cls, timestamp_ns: int, checks: tuple[OperationalCheck, ...]) -> RuntimeHealthReport:
        return cls(
            timestamp_ns=timestamp_ns,
            status=OperationalStatus.HEALTHY if all(check.passed for check in checks) else OperationalStatus.DEGRADED,
            alive=True,
            checks=checks,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp_ns": self.timestamp_ns,
            "status": self.status.value,
            "alive": self.alive,
            "checks": [check.to_dict() for check in self.checks],
        }


@dataclass(frozen=True, slots=True)
class RuntimeReadinessReport:
    timestamp_ns: int
    status: OperationalStatus
    ready: bool
    lifecycle: str
    checks: tuple[OperationalCheck, ...]

    @classmethod
    def from_checks(
        cls,
        timestamp_ns: int,
        lifecycle: str,
        checks: tuple[OperationalCheck, ...],
    ) -> RuntimeReadinessReport:
        ready = all(check.passed for check in checks if check.required)
        status = (
            OperationalStatus.NOT_READY
            if not ready
            else OperationalStatus.HEALTHY
            if all(check.passed for check in checks)
            else OperationalStatus.DEGRADED
        )
        return cls(timestamp_ns, status, ready, lifecycle, checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp_ns": self.timestamp_ns,
            "status": self.status.value,
            "ready": self.ready,
            "lifecycle": self.lifecycle,
            "checks": [check.to_dict() for check in self.checks],
        }
