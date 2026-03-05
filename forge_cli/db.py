import sqlite3
import click
from forge_cli.config import DB_PATH


def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS projects (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT UNIQUE NOT NULL,
                path        TEXT NOT NULL,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id   INTEGER NOT NULL REFERENCES projects(id),
                title        TEXT NOT NULL,
                plan         TEXT,
                status       TEXT DEFAULT 'pending' CHECK(status IN ('pending','in_progress','done','blocked')),
                created_at   TEXT DEFAULT (datetime('now')),
                started_at   TEXT,
                completed_at TEXT
            );
        """)


def resolve_project(conn, name):
    row = conn.execute("SELECT * FROM projects WHERE name = ?", (name,)).fetchone()
    if not row:
        raise click.ClickException(
            f"Project '{name}' not found. Add it with: tm project add {name} <path>"
        )
    return row
