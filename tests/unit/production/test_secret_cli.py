from __future__ import annotations

import pytest
from massive.exceptions import BadResponse

from l1_microstructure.production.secret_cli import _massive_failure_code, main


def test_secret_cli_generates_console_token_without_printing_it(monkeypatch, capsys) -> None:
    stored: dict[str, str] = {}
    monkeypatch.setattr(
        "l1_microstructure.production.secret_cli.set_secret",
        lambda name, value: stored.__setitem__(name, value),
    )

    exit_code = main(["TRADING_CONSOLE_TOKEN", "--generate"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert stored["TRADING_CONSOLE_TOKEN"]
    assert len(stored["TRADING_CONSOLE_TOKEN"]) >= 32
    assert stored["TRADING_CONSOLE_TOKEN"] not in output


def test_secret_cli_rejects_generation_for_vendor_credential() -> None:
    with pytest.raises(SystemExit):
        main(["MASSIVE_API_KEY", "--generate"])


def test_secret_cli_validates_massive_key_without_printing_it(monkeypatch, capsys) -> None:
    secret = "massive-secret-value"
    observed: list[str] = []
    monkeypatch.setattr(
        "l1_microstructure.production.secret_cli.get_secret",
        lambda _name: secret,
    )
    monkeypatch.setattr(
        "l1_microstructure.production.secret_cli._validate_massive_api_key",
        observed.append,
    )

    exit_code = main(["MASSIVE_API_KEY", "--validate"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert observed == [secret]
    assert secret not in output
    assert "validation passed" in output


def test_secret_cli_redacts_massive_validation_failure(monkeypatch, capsys) -> None:
    secret = "massive-secret-value"
    monkeypatch.setattr(
        "l1_microstructure.production.secret_cli.get_secret",
        lambda _name: secret,
    )
    monkeypatch.setattr(
        "l1_microstructure.production.secret_cli._validate_massive_api_key",
        lambda _value: (_ for _ in ()).throw(RuntimeError(f"rejected {secret}")),
    )

    exit_code = main(["MASSIVE_API_KEY", "--validate"])

    output = capsys.readouterr().out
    assert exit_code == 2
    assert secret not in output
    assert "validation failed" in output


@pytest.mark.parametrize(
    ("payload", "expected"),
    (
        ('{"status":"ERROR","error":"API Key was not found"}', "credential_rejected"),
        (
            '{"status":"NOT_AUTHORIZED","message":"subscription entitlement required"}',
            "data_entitlement_missing",
        ),
        ('{"status":"ERROR","message":"unknown rejection"}', "vendor_request_rejected"),
    ),
)
def test_massive_failure_classification_is_redacted(payload, expected) -> None:
    assert _massive_failure_code(BadResponse(payload)) == expected
