"""Database connection, initialization, and migration management."""

import os
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = os.path.join(os.getcwd(), "kb", "pka.db")
SCHEMA_DIR = Path(__file__).parent
CURRENT_SCHEMA_VERSION = 1

# Track whether sqlite-vec is available
_vec_available = None


def vec_available() -> bool:
    """Check if sqlite-vec extension is available."""
    global _vec_available
    if _vec_available is None:
        try:
            import sqlite_vec  # noqa: F401
            _vec_available = True
        except ImportError:
            _vec_available = False
    return _vec_available


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Open a connection with WAL mode and foreign keys enabled."""
    db_path = db_path or DEFAULT_DB_PATH
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    # Load sqlite-vec if available
    if vec_available():
        import sqlite_vec
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)

    return conn


def init_db(db_path: str | None = None) -> sqlite3.Connection:
    """Initialize the database: run schema and set up vec table if available."""
    conn = get_connection(db_path)

    # Check current version
    try:
        row = conn.execute(
            "SELECT MAX(version) as v FROM schema_version"
        ).fetchone()
        current_version = row["v"] if row and row["v"] else 0
    except sqlite3.OperationalError:
        current_version = 0

    if current_version < CURRENT_SCHEMA_VERSION:
        schema_sql = (SCHEMA_DIR / "schema.sql").read_text()
        conn.executescript(schema_sql)

    # Create sqlite-vec virtual table if extension is available
    if vec_available():
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS items_vec USING vec0(
                item_id INTEGER PRIMARY KEY,
                embedding float[384]
            )
        """)
        conn.commit()

    return conn


def get_schema_version(conn: sqlite3.Connection) -> int:
    """Return the current schema version."""
    try:
        row = conn.execute(
            "SELECT MAX(version) as v FROM schema_version"
        ).fetchone()
        return row["v"] if row and row["v"] else 0
    except sqlite3.OperationalError:
        return 0
