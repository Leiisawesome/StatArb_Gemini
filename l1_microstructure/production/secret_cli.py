"""Interactive Keychain secret management."""

from __future__ import annotations

import argparse
import getpass
from typing import Sequence

from .secrets import get_secret, set_secret


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manage StatArb Gemini secrets in macOS Keychain")
    parser.add_argument("name", choices=("MASSIVE_API_KEY", "TRADING_CONSOLE_TOKEN"))
    parser.add_argument("--check", action="store_true", help="report whether the secret exists")
    args = parser.parse_args(argv)
    if args.check:
        print("configured" if get_secret(args.name, allow_environment=False) else "missing")
        return 0
    value = getpass.getpass(f"{args.name}: ")
    set_secret(args.name, value)
    print(f"stored {args.name} in macOS Keychain")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
