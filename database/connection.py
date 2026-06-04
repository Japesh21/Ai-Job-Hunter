import sqlite3
import logging
from pathlib import Path
from config.settings import DB_PATH
from database.models import ALL_TABLES, CREATE_INDEXES

logger = logging.getLogger(__name__)


def get_connection() -> sqlite3.Connection:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db() -> None:
    conn = get_connection()
    with conn:
        for ddl in ALL_TABLES:
            conn.execute(ddl)
        for idx in CREATE_INDEXES:
            conn.execute(idx)
    logger.info("Database initialised at %s", DB_PATH)
    conn.close()
