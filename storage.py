import sqlite3

import config


def _connect() -> sqlite3.Connection:
    return sqlite3.connect(config.DB_PATH)


def init_db():
    conn = _connect()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS processed_txs (
            tx_hash TEXT PRIMARY KEY
        )
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
    """Collect writes in a single connection to avoid open/close per row."""

    def __init__(self):
        self._conn = _connect()

    def is_processed(self, tx_hash: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM processed_txs WHERE tx_hash = ?", (tx_hash,)
        ).fetchone()
        return row is not None

    def mark_processed(self, tx_hash: str):
        self._conn.execute(
            "INSERT OR IGNORE INTO processed_txs (tx_hash) VALUES (?)", (tx_hash,)
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
