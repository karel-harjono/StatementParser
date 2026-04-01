import sqlite3
import logging
from pathlib import Path

from app.config import DB_PATH, DATA_DIR

logger = logging.getLogger(__name__)


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    schema_path = Path(__file__).parent / "schema.sql"
    conn = get_connection()
    with conn:
        conn.executescript(schema_path.read_text())
    logger.info("Database initialized at %s", DB_PATH)
