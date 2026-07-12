"""SQLite operational ledger for runtime recovery and auditability."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any, Iterator
from uuid import uuid4


class OperationalLedger:
    SCHEMA_VERSION = 1

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._connection = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA synchronous=FULL")
        self._initialize()

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def append_event(self, category: str, event_type: str, payload: dict[str, Any]) -> int:
        timestamp = datetime.now(timezone.utc).isoformat()
        with self._transaction() as connection:
            cursor = connection.execute(
                "INSERT INTO audit_events(timestamp, category, event_type, payload_json) VALUES (?, ?, ?, ?)",
                (timestamp, category, event_type, self._json(payload)),
            )
            return int(cursor.lastrowid)

    def record_order_intent(self, payload: dict[str, Any], client_order_id: str | None = None) -> str:
        order_id = client_order_id or uuid4().hex
        now = datetime.now(timezone.utc).isoformat()
        with self._transaction() as connection:
            connection.execute(
                "INSERT INTO order_ledger(client_order_id, status, created_at, updated_at, payload_json) VALUES (?, ?, ?, ?, ?)",
                (order_id, "intent_recorded", now, now, self._json(payload)),
            )
        return order_id

    def update_order(self, client_order_id: str, status: str, *, external_order_id: str | None = None, payload: dict[str, Any] | None = None) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._transaction() as connection:
            cursor = connection.execute(
                "UPDATE order_ledger SET status = ?, external_order_id = COALESCE(?, external_order_id), updated_at = ?, payload_json = COALESCE(?, payload_json) WHERE client_order_id = ?",
                (status, external_order_id, now, self._json(payload) if payload is not None else None, client_order_id),
            )
            if cursor.rowcount != 1:
                raise ValueError(f"unknown client order id {client_order_id}")

    def open_orders(self) -> list[dict[str, Any]]:
        terminal = ("filled", "cancelled", "rejected")
        placeholders = ",".join("?" for _ in terminal)
        rows = self._connection.execute(
            f"SELECT * FROM order_ledger WHERE status NOT IN ({placeholders}) ORDER BY id", terminal
        ).fetchall()
        return [self._order_row(row) for row in rows]

    def set_state(self, key: str, value: Any) -> None:
        with self._transaction() as connection:
            connection.execute(
                "INSERT INTO runtime_state(key, value_json, updated_at) VALUES (?, ?, ?) ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json, updated_at = excluded.updated_at",
                (key, self._json(value), datetime.now(timezone.utc).isoformat()),
            )

    def get_state(self, key: str, default: Any = None) -> Any:
        row = self._connection.execute("SELECT value_json FROM runtime_state WHERE key = ?", (key,)).fetchone()
        return default if row is None else json.loads(row["value_json"])

    def recent_events(self, limit: int = 100) -> list[dict[str, Any]]:
        rows = self._connection.execute(
            "SELECT * FROM audit_events ORDER BY id DESC LIMIT ?", (max(int(limit), 1),)
        ).fetchall()
        return [
            {
                "id": int(row["id"]),
                "timestamp": row["timestamp"],
                "category": row["category"],
                "event_type": row["event_type"],
                "payload": json.loads(row["payload_json"]),
            }
            for row in rows
        ]

    def _initialize(self) -> None:
        with self._lock:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_info(version INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS audit_events(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    category TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS order_ledger(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_order_id TEXT NOT NULL UNIQUE,
                    external_order_id TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS runtime_state(
                    key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            row = self._connection.execute("SELECT version FROM schema_info").fetchone()
            if row is None:
                self._connection.execute("INSERT INTO schema_info(version) VALUES (?)", (self.SCHEMA_VERSION,))
            elif int(row["version"]) != self.SCHEMA_VERSION:
                raise ValueError(f"unsupported operational ledger schema version {row['version']}")

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                yield self._connection
            except BaseException:
                self._connection.execute("ROLLBACK")
                raise
            else:
                self._connection.execute("COMMIT")

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value, allow_nan=False, separators=(",", ":"), sort_keys=True, default=str)

    @staticmethod
    def _order_row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "client_order_id": row["client_order_id"],
            "external_order_id": row["external_order_id"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "payload": json.loads(row["payload_json"]),
        }
