"""macOS Keychain-backed production secret resolution."""

from __future__ import annotations

import os

import keyring

_SERVICE = "statarb-gemini"


def get_secret(name: str, *, allow_environment: bool = True) -> str | None:
    value = keyring.get_password(_SERVICE, name)
    if value:
        return value
    return os.environ.get(name) if allow_environment else None


def set_secret(name: str, value: str) -> None:
    if not name or not value:
        raise ValueError("secret name and value are required")
    keyring.set_password(_SERVICE, name, value)
