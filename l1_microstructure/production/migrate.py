"""Explicit migration tool for trusted legacy pickle artifacts."""

from __future__ import annotations

import argparse
from typing import Sequence

from l1_microstructure.artifacts import LocalArtifactStore


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Migrate trusted local pickle artifacts to JSON")
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("artifact_ids", nargs="+")
    parser.add_argument(
        "--trusted-local-artifacts",
        action="store_true",
        help="confirm that every pickle originated from a trusted local workflow",
    )
    args = parser.parse_args(argv)
    if not args.trusted_local_artifacts:
        parser.error("--trusted-local-artifacts is required because loading pickle can execute code")
    store = LocalArtifactStore(args.artifact_root)
    for artifact_id in args.artifact_ids:
        store.migrate_legacy_pickle(artifact_id, trusted=True)
        print(artifact_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
