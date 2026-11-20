import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from app.config import settings


_migration_lock = threading.Lock()
_migration_ready = False


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def database_path() -> Path:
    configured = Path(settings.JOB_DATABASE_PATH).expanduser()
    if not configured.is_absolute():
        configured = Path(__file__).resolve().parents[3] / configured
    return configured


def connect() -> sqlite3.Connection:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=15, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 15000")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


def migrate(connection: sqlite3.Connection | None = None) -> None:
    global _migration_ready
    if _migration_ready:
        return
    with _migration_lock:
        if _migration_ready:
            return
        owned_connection = connection is None
        db = connection or connect()
        try:
            db.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations "
                "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
            )
            applied = {
                row["version"]
                for row in db.execute("SELECT version FROM schema_migrations").fetchall()
            }
            migration_files = sorted(
                Path(__file__).with_name("migrations").glob("[0-9][0-9][0-9][0-9]_*.sql")
            )
            for migration_file in migration_files:
                version = int(migration_file.name[:4])
                if version in applied:
                    continue
                script = migration_file.read_text(encoding="utf-8")
                db.executescript("BEGIN IMMEDIATE;\n" + script)
                db.execute(
                    "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                    (version, utc_now()),
                )
                db.commit()
            _migration_ready = True
        finally:
            if owned_connection:
                db.close()


@contextmanager
def database(*, immediate: bool = False) -> Iterator[sqlite3.Connection]:
    migrate()
    connection = connect()
    try:
        connection.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def reset_migration_cache_for_tests() -> None:
    global _migration_ready
    _migration_ready = False
