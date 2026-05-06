import sqlite3
import hashlib
from datetime import datetime
from contextlib import contextmanager

DB_PATH = "tracker.db"


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS news_items (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                content_hash TEXT UNIQUE NOT NULL,
                title       TEXT NOT NULL,
                source_url  TEXT NOT NULL,
                source_name TEXT NOT NULL,
                category    TEXT NOT NULL,
                summary     TEXT,
                severity    TEXT,
                published_at TEXT,
                fetched_at  TEXT NOT NULL,
                alerted     INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS digest_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                sent_at     TEXT NOT NULL,
                item_count  INTEGER NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_fetched_at ON news_items (fetched_at);
            CREATE INDEX IF NOT EXISTS idx_category   ON news_items (category);
            CREATE INDEX IF NOT EXISTS idx_alerted    ON news_items (alerted);
        """)


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def make_hash(title: str, url: str) -> str:
    return hashlib.sha256(f"{title}|{url}".encode()).hexdigest()


def is_duplicate(content_hash: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM news_items WHERE content_hash = ?", (content_hash,)
        ).fetchone()
        return row is not None


def insert_item(item: dict) -> int | None:
    """Insert a new item. Returns row id or None if duplicate."""
    content_hash = make_hash(item["title"], item["source_url"])
    if is_duplicate(content_hash):
        return None
    with get_conn() as conn:
        cursor = conn.execute(
            """INSERT INTO news_items
               (content_hash, title, source_url, source_name, category,
                summary, severity, published_at, fetched_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                content_hash,
                item["title"],
                item["source_url"],
                item["source_name"],
                item["category"],
                item.get("summary"),
                item.get("severity"),
                item.get("published_at"),
                datetime.utcnow().isoformat(),
            ),
        )
        return cursor.lastrowid


def get_unalerted() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM news_items WHERE alerted = 0 ORDER BY fetched_at ASC"
        ).fetchall()
        return [dict(r) for r in rows]


def mark_alerted(item_ids: list[int]):
    with get_conn() as conn:
        conn.execute(
            f"UPDATE news_items SET alerted = 1 WHERE id IN ({','.join('?' * len(item_ids))})",
            item_ids,
        )


def get_recent_items(hours: int = 24) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM news_items
               WHERE fetched_at >= datetime('now', ?)
               ORDER BY fetched_at DESC""",
            (f"-{hours} hours",),
        ).fetchall()
        return [dict(r) for r in rows]


def get_count_since(since_iso: str) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM news_items WHERE fetched_at > ?", (since_iso,)
        ).fetchone()
        return row[0]


def log_digest(item_count: int):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO digest_log (sent_at, item_count) VALUES (?, ?)",
            (datetime.utcnow().isoformat(), item_count),
        )


def get_all_items(page: int = 1, per_page: int = 50, category: str = None) -> dict:
    offset = (page - 1) * per_page
    with get_conn() as conn:
        if category:
            total = conn.execute(
                "SELECT COUNT(*) FROM news_items WHERE category = ?", (category,)
            ).fetchone()[0]
            rows = conn.execute(
                """SELECT * FROM news_items WHERE category = ?
                   ORDER BY fetched_at DESC LIMIT ? OFFSET ?""",
                (category, per_page, offset),
            ).fetchall()
        else:
            total = conn.execute("SELECT COUNT(*) FROM news_items").fetchone()[0]
            rows = conn.execute(
                "SELECT * FROM news_items ORDER BY fetched_at DESC LIMIT ? OFFSET ?",
                (per_page, offset),
            ).fetchall()
        return {"items": [dict(r) for r in rows], "total": total, "page": page, "per_page": per_page}
