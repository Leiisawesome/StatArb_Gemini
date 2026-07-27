from __future__ import annotations

import pytest

from l1_microstructure.retry import (
    ExceptionRetryClassifier,
    RetryExecutionError,
    RetryExecutor,
    RetryPolicy,
)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"max_attempts": 0}, "max_attempts"),
        ({"initial_delay_seconds": -1.0}, "initial delay"),
        ({"backoff_multiplier": 0.5}, "backoff multiplier"),
        ({"maximum_delay_seconds": -1.0}, "maximum delay"),
        ({"jitter_fraction": 1.1}, "jitter fraction"),
        ({"initial_delay_seconds": float("nan")}, "must be finite"),
    ],
)
def test_retry_policy_rejects_invalid_configuration(overrides, message) -> None:
    with pytest.raises(ValueError, match=message):
        RetryPolicy(**overrides)


def test_retry_policy_caps_exponential_backoff() -> None:
    policy = RetryPolicy(
        max_attempts=6,
        initial_delay_seconds=1.0,
        backoff_multiplier=2.0,
        maximum_delay_seconds=5.0,
    )

    assert [policy.delay_seconds(attempt) for attempt in range(1, 6)] == [1.0, 2.0, 4.0, 5.0, 5.0]
    assert policy.delay_seconds(100_000) == 5.0


def test_retry_policy_applies_bounded_jitter() -> None:
    policy = RetryPolicy(initial_delay_seconds=10.0, maximum_delay_seconds=20.0, jitter_fraction=0.25)

    assert policy.delay_seconds(1, random_value=0.0) == 7.5
    assert policy.delay_seconds(1, random_value=0.5) == 10.0
    assert policy.delay_seconds(1, random_value=1.0) == 12.5


def test_retry_executor_recovers_from_classified_transient_failures() -> None:
    waits: list[float] = []
    timestamps = iter((101, 102))
    calls = 0

    def operation() -> str:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise TimeoutError(f"timeout {calls}")
        return "connected"

    result = RetryExecutor(
        RetryPolicy(max_attempts=3, initial_delay_seconds=1.0),
        wait=waits.append,
        clock=lambda: next(timestamps),
        random_source=lambda: 0.5,
    ).execute(operation)

    assert result.unwrap() == "connected"
    assert result.attempts == 3
    assert waits == [1.0, 2.0]
    assert [failure.timestamp_ns for failure in result.failures] == [101, 102]
    assert all(failure.retryable and failure.will_retry for failure in result.failures)


def test_retry_executor_stops_immediately_for_non_retryable_failure() -> None:
    waits: list[float] = []
    result = RetryExecutor(RetryPolicy(max_attempts=3), wait=waits.append).execute(
        lambda: (_ for _ in ()).throw(ValueError("invalid request"))
    )

    assert result.succeeded is False
    assert result.attempts == 1
    assert waits == []
    assert result.final_failure is not None
    assert result.final_failure.retryable is False


def test_retry_executor_reports_exhaustion_and_preserves_cause() -> None:
    waits: list[float] = []
    result = RetryExecutor(
        RetryPolicy(max_attempts=3, initial_delay_seconds=0.5),
        wait=waits.append,
        random_source=lambda: 0.5,
    ).execute(lambda: (_ for _ in ()).throw(ConnectionError("offline")))

    assert result.succeeded is False
    assert result.attempts == 3
    assert waits == [0.5, 1.0]
    assert result.final_failure is not None
    assert result.final_failure.will_retry is False
    with pytest.raises(RetryExecutionError, match="failed after 3 attempt") as exc_info:
        result.unwrap()
    assert isinstance(exc_info.value.__cause__, ConnectionError)


def test_exception_classifier_non_retryable_types_take_precedence() -> None:
    class AmbiguousSubmissionError(ConnectionError):
        pass

    classifier = ExceptionRetryClassifier(
        retryable=(ConnectionError,),
        non_retryable=(AmbiguousSubmissionError,),
    )

    assert classifier(ConnectionError("transient")) is True
    assert classifier(AmbiguousSubmissionError("unknown order outcome")) is False
