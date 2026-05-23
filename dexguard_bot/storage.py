from __future__ import annotations

import sqlite3
from pathlib import Path


class Storage:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def _init(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scans (
                    chain_id TEXT NOT NULL,
                    token_address TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    count INTEGER NOT NULL DEFAULT 0,
                    last_scanned_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (chain_id, token_address)
                )
                """
            )

    def record_scan(self, chain_id: str, token_address: str, symbol: str) -> int:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO scans (chain_id, token_address, symbol, count)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(chain_id, token_address)
                DO UPDATE SET
                    count = count + 1,
                    symbol = excluded.symbol,
                    last_scanned_at = CURRENT_TIMESTAMP
                """,
                (chain_id, token_address, symbol),
            )
            row = conn.execute(
                "SELECT count FROM scans WHERE chain_id = ? AND token_address = ?",
                (chain_id, token_address),
            ).fetchone()
        return int(row[0]) if row else 1

    def trending(self, limit: int = 10) -> list[tuple[str, str, str, int]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT chain_id, token_address, symbol, count
                FROM scans
                ORDER BY count DESC, last_scanned_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [(str(a), str(b), str(c), int(d)) for a, b, c, d in rows]
