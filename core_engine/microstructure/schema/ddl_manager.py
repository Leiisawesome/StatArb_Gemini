"""
ClickHouse DDL manager for microstructure tables.

Reads and applies the DDL from clickhouse_ddl.sql against the configured
ClickHouse instance. Uses aiohttp POST for compatibility with existing patterns.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)

DDL_PATH = Path(__file__).parent / "clickhouse_ddl.sql"


class DDLManager:
    """Applies and verifies ClickHouse schema for microstructure tables."""

    EXPECTED_TABLES = [
        "polygon_data.microstructure_trades",
        "polygon_data.microstructure_quotes",
        "polygon_data.microstructure_buckets",
        "polygon_data.microstructure_diagnostics",
    ]

    def __init__(self, clickhouse_url: str = "http://localhost:8123"):
        self._url = clickhouse_url

    async def _execute(self, query: str) -> str:
        """Execute a single ClickHouse statement via HTTP POST."""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self._url,
                data=query,
                headers={"Content-Type": "text/plain"},
            ) as resp:
                text = await resp.text()
                if resp.status != 200:
                    raise RuntimeError(
                        f"ClickHouse query failed ({resp.status}): {text.strip()}"
                    )
                return text.strip()

    async def apply_ddl(self) -> List[str]:
        """
        Execute all DDL statements from clickhouse_ddl.sql.

        Returns list of table names that were created/verified.
        """
        content = DDL_PATH.read_text()

        # Strip comment-only lines
        lines = [l for l in content.split("\n") if not l.strip().startswith("--")]
        clean = "\n".join(lines)

        # Split on CREATE TABLE
        raw_stmts = re.split(r"(?=CREATE TABLE)", clean)
        stmts = [s.strip().rstrip(";") for s in raw_stmts if s.strip().startswith("CREATE TABLE")]

        created: List[str] = []
        for stmt in stmts:
            match = re.search(r"CREATE TABLE IF NOT EXISTS\s+(\S+)", stmt)
            table_name = match.group(1) if match else "unknown"
            try:
                await self._execute(stmt)
                created.append(table_name)
                logger.info("DDL applied: %s", table_name)
            except RuntimeError as e:
                logger.error("DDL failed for %s: %s", table_name, e)
                raise

        return created

    async def verify_schema(self) -> Dict[str, int]:
        """
        Verify all expected tables exist and return column counts.

        Returns dict of {table_name: column_count}.
        Raises RuntimeError if any table is missing.
        """
        result = await self._execute(
            "SELECT table, count() AS cols "
            "FROM system.columns "
            "WHERE database = 'polygon_data' AND table LIKE 'microstructure%' "
            "GROUP BY table FORMAT TSVWithNames"
        )

        found: Dict[str, int] = {}
        for line in result.strip().split("\n")[1:]:  # skip header
            parts = line.split("\t")
            if len(parts) == 2:
                found[f"polygon_data.{parts[0]}"] = int(parts[1])

        missing = [t for t in self.EXPECTED_TABLES if t not in found]
        if missing:
            raise RuntimeError(f"Missing tables: {missing}")

        return found

    async def get_storage_usage(self) -> Dict[str, float]:
        """Return storage usage in MB for each microstructure table."""
        result = await self._execute(
            "SELECT table, "
            "sum(bytes_on_disk) / 1048576 AS mb, "
            "sum(rows) AS rows "
            "FROM system.parts "
            "WHERE database = 'polygon_data' AND table LIKE 'microstructure%' "
            "AND active = 1 "
            "GROUP BY table FORMAT TSVWithNames"
        )

        usage: Dict[str, float] = {}
        for line in result.strip().split("\n")[1:]:
            parts = line.split("\t")
            if len(parts) >= 2:
                usage[parts[0]] = float(parts[1])

        return usage

    async def get_total_storage_gb(self) -> float:
        """Return total storage used by ALL polygon_data tables in GB."""
        result = await self._execute(
            "SELECT sum(bytes_on_disk) / 1073741824 AS gb "
            "FROM system.parts "
            "WHERE database = 'polygon_data' AND active = 1 "
            "FORMAT TSVWithNames"
        )
        for line in result.strip().split("\n")[1:]:
            return float(line.strip())
        return 0.0

    async def get_row_count(self, table: str) -> int:
        """Return row count for a specific table."""
        result = await self._execute(f"SELECT count() FROM {table} FORMAT TSVWithNames")
        for line in result.strip().split("\n")[1:]:
            return int(line.strip())
        return 0

    async def get_symbol_day_count(self, table: str, symbol: str) -> int:
        """Return number of distinct dates for a symbol in a table."""
        result = await self._execute(
            f"SELECT uniqExact(ingestion_date) FROM {table} "
            f"WHERE symbol = '{symbol}' FORMAT TSVWithNames"
        )
        for line in result.strip().split("\n")[1:]:
            return int(line.strip())
        return 0
