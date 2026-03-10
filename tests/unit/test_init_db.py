from pathlib import Path
import sqlite3

from src.database.init_db import init_db


def test_init_db_creates_file(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    init_db(db_path)
    assert db_path.exists()
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scenario_runs'")
        assert cursor.fetchone() is not None
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='change_log'")
        assert cursor.fetchone() is not None
