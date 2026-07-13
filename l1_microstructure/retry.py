"""Typed, deterministic retry policy contracts for infrastructure boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from random import random
from time import time_ns
from typing import Callable, Generic, TypeVar, cast


T = TypeVar("T")
RetryClassifier = Callable[[Exception], bool]


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 3
    initial_delay_seconds: float = 1.0
    backoff_multiplier: float = 2.0
    maximum_delay_seconds: float = 30.0
    jitter_fraction: float = 0.0

    def __post_init__(self) -> None:
        if isinstance(self.max_attempts, bool) or not isinstance(self.max_attempts, int) or self.max_attempts < 1:
            raise ValueError("retry max_attempts must be a positive integer")
        numeric_values = (
            self.initial_delay_seconds,
            self.backoff_multiplier,
            self.maximum_delay_seconds,
            self.jitter_fraction,
        )
        if not all(isfinite(float(value)) for value in numeric_values):
            raise ValueError("retry policy values must be finite")
        if self.initial_delay_seconds < 0.0:
            raise ValueError("retry initial delay cannot be negative")
        if self.backoff_multiplier < 1.0:
            raise ValueError("retry backoff multiplier must be at least one")
        if self.maximum_delay_seconds < 0.0:
            raise ValueError("retry maximum delay cannot be negative")
        if not 0.0 <= self.jitter_fraction <= 1.0:
            raise ValueError("retry jitter fraction must be between zero and one")

    def delay_seconds(self, failed_attempt: int, *, random_value: float = 0.5) -> float:
        if failed_attempt < 1:
            raise ValueError("failed attempt number must be positive")
        if not 0.0 <= random_value <= 1.0:
            raise ValueError("retry random value must be between zero and one")
        try:
            uncapped = self.initial_delay_seconds * self.backoff_multiplier ** (failed_attempt - 1)
        except OverflowError:
            uncapped = float("inf")
        base_delay = min(uncapped, self.maximum_delay_seconds)
        jitter_multiplier = 1.0 + self.jitter_fraction * ((2.0 * random_value) - 1.0)
        return max(0.0, min(base_delay * jitter_multiplier, self.maximum_delay_seconds))


@dataclass(frozen=True, slots=True)
class ExceptionRetryClassifier:
    retryable: tuple[type[Exception], ...] = (TimeoutError, ConnectionError)
    non_retryable: tuple[type[Exception], ...] = ()

    def __post_init__(self) -> None:
        for group in (self.retryable, self.non_retryable):
            if not isinstance(group, tuple) or any(
                not isinstance(exception_type, type) or not issubclass(exception_type, Exception)
                for exception_type in group
            ):
                raise TypeError("retry exception classifications must contain Exception types")

    def __call__(self, error: Exception) -> bool:
        if isinstance(error, self.non_retryable):
            return False
        return isinstance(error, self.retryable)


@dataclass(frozen=True, slots=True)
class RetryFailure:
    attempt: int
    timestamp_ns: int
    error: Exception
    retryable: bool
    will_retry: bool
    delay_seconds: float

    @property
    def error_type(self) -> str:
        return type(self.error).__name__


class RetryExecutionError(RuntimeError):
    def __init__(self, result: "RetryResult[object]") -> None:
        failure = result.final_failure
        detail = "unknown failure" if failure is None else f"{failure.error_type}: {failure.error}"
        super().__init__(f"operation failed after {result.attempts} attempt(s): {detail}")
        self.result = result


@dataclass(frozen=True, slots=True)
class RetryResult(Generic[T]):
    succeeded: bool
    attempts: int
    value: T | None
    failures: tuple[RetryFailure, ...]

    @property
    def final_failure(self) -> RetryFailure | None:
        return self.failures[-1] if self.failures else None

    def unwrap(self) -> T:
        if not self.succeeded:
            error = RetryExecutionError(cast("RetryResult[object]", self))
            cause = self.final_failure.error if self.final_failure is not None else None
            raise error from cause
        return cast(T, self.value)


class RetryExecutor:
    """Execute a policy using injected wait, clock, and randomness hooks."""

    def __init__(
        self,
        policy: RetryPolicy,
        *,
        wait: Callable[[float], None],
        classifier: RetryClassifier | None = None,
        clock: Callable[[], int] = time_ns,
        random_source: Callable[[], float] = random,
    ) -> None:
        self.policy = policy
        self.wait = wait
        self.classifier = classifier or ExceptionRetryClassifier()
        self.clock = clock
        self.random_source = random_source

    def execute(self, operation: Callable[[], T]) -> RetryResult[T]:
        failures: list[RetryFailure] = []
        for attempt in range(1, self.policy.max_attempts + 1):
            try:
                return RetryResult(succeeded=True, attempts=attempt, value=operation(), failures=tuple(failures))
            except Exception as error:
                retryable = bool(self.classifier(error))
                will_retry = retryable and attempt < self.policy.max_attempts
                delay = (
                    self.policy.delay_seconds(attempt, random_value=float(self.random_source())) if will_retry else 0.0
                )
                failures.append(
                    RetryFailure(
                        attempt=attempt,
                        timestamp_ns=int(self.clock()),
                        error=error,
                        retryable=retryable,
                        will_retry=will_retry,
                        delay_seconds=delay,
                    )
                )
                if not will_retry:
                    return RetryResult(succeeded=False, attempts=attempt, value=None, failures=tuple(failures))
                self.wait(delay)
        raise AssertionError("retry executor exhausted without producing a result")
