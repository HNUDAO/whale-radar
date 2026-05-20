import sqlite3
from datetime import datetime, timezone

import config


def _connect() -> sqlite3.Connection:
    return sqlite3.connect(config.DB_PATH)


def init_db():
    conn = _connect()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS processed_txs (
            tx_key      TEXT PRIMARY KEY,
            tx_hash     TEXT NOT NULL,
            alert_type  TEXT NOT NULL,
            address     TEXT NOT NULL,
            block_number INTEGER NOT NULL,
            created_at  TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_processed_address
        ON processed_txs (address, block_number)
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS last_block (
            address TEXT PRIMARY KEY,
            block_number INTEGER NOT NULL
        )
    """)
    conn.commit()
    conn.close()


class BatchWriter:
    def __init__(self):
        self._conn = _connect()

    def is_processed(self, tx_key: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM processed_txs WHERE tx_key = ?", (tx_key,)
        ).fetchone()
        return row is not None

    def mark_processed(
        self, tx_key: str, tx_hash: str, alert_type: str,
        address: str, block_number: int,
    ):
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "INSERT OR IGNORE INTO processed_txs "
            "(tx_key, tx_hash, alert_type, address, block_number, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (tx_key, tx_hash, alert_type, address, block_number, now),
        )

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()


def get_last_block(address: str) -> int | None:
    conn = _connect()
    row = conn.execute(
        "SELECT block_number FROM last_block WHERE address = ?", (address,)
    ).fetchone()
    conn.close()
    return row[0] if row else None


def set_last_block(address: str, block: int):
    conn = _connect()
    conn.execute(
        "INSERT OR REPLACE INTO last_block (address, block_number) VALUES (?, ?)",
        (address, block),
    )
    conn.commit()
    conn.close()
