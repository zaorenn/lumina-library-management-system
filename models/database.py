"""SQLite connection and schema lifecycle helpers for LibSys."""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import bcrypt

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH: str | Path = Path(os.getenv("LIBSYS_DB_PATH", BASE_DIR / "libsys.db"))
SCHEMA_PATH = BASE_DIR / "schema.sql"
DEFAULT_ADMIN_USERNAME = os.getenv("LIBSYS_ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_PASSWORD = os.getenv("LIBSYS_ADMIN_PASSWORD", "admin123")
DEMO_MEMBER_ENABLED = os.getenv("LIBSYS_ENABLE_DEMO_ACCOUNT", "1").strip().lower() not in {
    "0",
    "false",
    "no",
}
DEMO_MEMBER_USERNAME = "uye"
DEMO_MEMBER_PASSWORD = "uye123"


def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Return a configured SQLite connection.

    Foreign-key enforcement is connection-scoped in SQLite, so it must be
    enabled every time. A busy timeout makes short concurrent GUI operations
    retry instead of failing immediately with ``database is locked``.
    """

    path = Path(db_path or DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 10000")
    return connection


@contextmanager
def db_session(*, immediate: bool = False) -> Iterator[sqlite3.Connection]:
    """Provide a transaction that always commits or rolls back cleanly."""

    connection = get_connection()
    try:
        if immediate:
            connection.execute("BEGIN IMMEDIATE")
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _column_names(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}


def _migrate_legacy_schema(connection: sqlite3.Connection) -> None:
    """Apply small, non-destructive migrations to databases from older builds."""

    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    if "books" in tables and "is_active" not in _column_names(connection, "books"):
        connection.execute("ALTER TABLE books ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")
    if "members" in tables and "is_active" not in _column_names(connection, "members"):
        connection.execute("ALTER TABLE members ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")
    if "members" in tables and "username" not in _column_names(connection, "members"):
        connection.execute("ALTER TABLE members ADD COLUMN username TEXT COLLATE NOCASE")
    if "book_requests" in tables:
        request_columns = _column_names(connection, "book_requests")
        if "category" not in request_columns:
            connection.execute("ALTER TABLE book_requests ADD COLUMN category TEXT NOT NULL DEFAULT 'Genel'")
        if "published_year" not in request_columns:
            connection.execute("ALTER TABLE book_requests ADD COLUMN published_year INTEGER")
        if "description" not in request_columns:
            connection.execute("ALTER TABLE book_requests ADD COLUMN description TEXT NOT NULL DEFAULT ''")


def _ensure_demo_member_record(connection: sqlite3.Connection, *, reset_password: bool = False) -> None:
    existing = connection.execute(
        "SELECT id FROM members WHERE username = ? COLLATE NOCASE",
        (DEMO_MEMBER_USERNAME,),
    ).fetchone()
    if existing:
        connection.execute(
            """
            UPDATE members
            SET name = 'Deneme Üyesi', email = '', phone = '',
                is_approved = 1, is_active = 1, must_change_password = 0
            WHERE id = ?
            """,
            (existing[0],),
        )
        if reset_password:
            password_hash = bcrypt.hashpw(DEMO_MEMBER_PASSWORD.encode("utf-8"), bcrypt.gensalt()).decode(
                "utf-8"
            )
            connection.execute(
                "UPDATE members SET password_hash = ? WHERE id = ?",
                (password_hash, existing[0]),
            )
        return

    password_hash = bcrypt.hashpw(DEMO_MEMBER_PASSWORD.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    cursor = connection.execute(
        """
        INSERT INTO members
            (name, username, email, phone, password_hash,
             is_approved, is_active, must_change_password)
        VALUES ('Deneme Üyesi', ?, '', '', ?, 1, 1, 0)
        """,
        (DEMO_MEMBER_USERNAME, password_hash),
    )
    connection.execute(
        """
        INSERT INTO audit_logs (action_type, table_name, record_id, description)
        VALUES ('CREATE', 'members', ?, 'Yönetici demo üyesi oluşturuldu: Deneme Üyesi')
        """,
        (cursor.lastrowid,),
    )


def init_db(*, seed_catalog: bool = True) -> None:
    """Create or safely upgrade the database and ensure an admin account exists."""

    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with db_session() as connection:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
        _migrate_legacy_schema(connection)
        connection.executescript(schema)
        connection.execute("PRAGMA user_version = 4")

        admin_count = connection.execute("SELECT COUNT(*) FROM admins").fetchone()[0]
        if admin_count == 0:
            password_hash = bcrypt.hashpw(DEFAULT_ADMIN_PASSWORD.encode("utf-8"), bcrypt.gensalt()).decode(
                "utf-8"
            )
            connection.execute(
                """
                INSERT INTO admins (username, password_hash, name, email)
                VALUES (?, ?, ?, ?)
                """,
                (
                    DEFAULT_ADMIN_USERNAME,
                    password_hash,
                    "Sistem Yöneticisi",
                    "admin@libsys.local",
                ),
            )

        if DEMO_MEMBER_ENABLED:
            _ensure_demo_member_record(connection)

        if seed_catalog:
            from models.catalog import ensure_default_catalog

            ensure_default_catalog(connection)


def ensure_demo_member(*, reset_password: bool = True) -> None:
    """Create the evaluator account without relaxing public registration rules."""

    with db_session() as connection:
        _ensure_demo_member_record(connection, reset_password=reset_password)


def check_integrity() -> tuple[bool, str]:
    """Run SQLite's built-in integrity check for the administration panel."""

    connection = get_connection()
    try:
        result = connection.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        connection.close()
    return result == "ok", result


def refresh_catalog_metadata() -> int:
    """Restore summaries and cover URLs for the curated catalog."""

    from models.catalog import ensure_default_catalog

    with db_session() as connection:
        return ensure_default_catalog(connection)


if __name__ == "__main__":
    init_db()
