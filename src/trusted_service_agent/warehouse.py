"""Read-only warehouse connector: DuckDB locally; Snowflake-style schema `servicing`."""

from pathlib import Path

import duckdb

from trusted_service_agent.paths import DATA

DB = DATA / "warehouse.duckdb"


class Warehouse:
    """Opens the database read-only; there is no method that writes."""

    def __init__(self, path: Path = DB) -> None:
        self.con = duckdb.connect(str(path), read_only=True)

    def rows(self, sql: str, params: list) -> list[dict]:
        cur = self.con.execute(sql, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r, strict=True)) for r in cur.fetchall()]
