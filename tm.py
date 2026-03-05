#!/usr/bin/env python3
"""
tm - taskmaster CLI
Usage:
  tm project add <name> <path>
  tm project list
  tm add <project> <title> [plan]
  tm list [project] [--all]
  tm show <project> <id>
  tm start <project> <id>
  tm done <project> <id>
  tm delete <project> <id>
  tm edit <project> <id> [--title <title>] [--plan <plan>] [--status <status>]
"""

import sqlite3
import sys
import os
import subprocess
from datetime import datetime
from pathlib import Path

DB_PATH = Path(os.environ.get("TM_DB", Path.home() / ".taskmaster" / "tasks.db"))


# ── DB ──────────────────────────────────────────────────────────────────────

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


# ── HELPERS ─────────────────────────────────────────────────────────────────

def resolve_project(conn, name):
    row = conn.execute("SELECT * FROM projects WHERE name = ?", (name,)).fetchone()
    if not row:
        die(f"Project '{name}' not found. Add it with: tm project add {name} <path>")
    return row


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


STATUS_ICONS = {
    "pending":     "○",
    "in_progress": "◉",
    "done":        "✓",
    "blocked":     "✗",
}


def fmt_task(t, verbose=False):
    icon = STATUS_ICONS.get(t["status"], "?")
    line = f"  [{t['id']:>3}] {icon}  {t['title']}"
    if verbose and t["plan"]:
        for l in t["plan"].splitlines():
            line += f"\n         {l}"
    return line


# ── COMMANDS ────────────────────────────────────────────────────────────────

def cmd_project_add(args):
    if len(args) < 2:
        die("usage: tm project add <name> <path>")
    name, path = args[0], args[1]
    path = str(Path(path).expanduser().resolve())
    if not Path(path).exists():
        die(f"path does not exist: {path}")
    with get_db() as conn:
        conn.execute("INSERT INTO projects (name, path) VALUES (?, ?)", (name, path))
    print(f"added project '{name}' → {path}")


def cmd_project_list(_):
    with get_db() as conn:
        rows = conn.execute("SELECT p.*, COUNT(t.id) as task_count FROM projects p LEFT JOIN tasks t ON t.project_id = p.id GROUP BY p.id ORDER BY p.name").fetchall()
    if not rows:
        print("no projects yet. add one with: tm project add <name> <path>")
        return
    for r in rows:
        pending = 0
        with get_db() as conn:
            pending = conn.execute("SELECT COUNT(*) FROM tasks WHERE project_id=? AND status!='done'", (r["id"],)).fetchone()[0]
        print(f"  {r['name']:<20} {r['path']}  ({pending} pending)")


def cmd_add(args):
    if len(args) < 2:
        die("usage: tm add <project> <title> [plan]")
    project_name = args[0]
    title = args[1]
    plan = args[2] if len(args) > 2 else None
    with get_db() as conn:
        project = resolve_project(conn, project_name)
        conn.execute(
            "INSERT INTO tasks (project_id, title, plan) VALUES (?, ?, ?)",
            (project["id"], title, plan)
        )
        task_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    print(f"added task #{task_id} to '{project_name}'")


def cmd_list(args):
    show_all = "--all" in args
    args = [a for a in args if a != "--all"]

    with get_db() as conn:
        if show_all:
            projects = conn.execute("SELECT * FROM projects ORDER BY name").fetchall()
            for p in projects:
                tasks = conn.execute(
                    "SELECT * FROM tasks WHERE project_id=? ORDER BY status, id", (p["id"],)
                ).fetchall()
                if not tasks:
                    continue
                print(f"\n{p['name']}  ({p['path']})")
                for t in tasks:
                    print(fmt_task(t))
        else:
            if not args:
                die("usage: tm list <project> [--all]")
            project = resolve_project(conn, args[0])
            tasks = conn.execute(
                "SELECT * FROM tasks WHERE project_id=? ORDER BY status, id", (project["id"],)
            ).fetchall()
            if not tasks:
                print(f"no tasks in '{args[0]}'")
                return
            print(f"\n{project['name']}  ({project['path']})")
            for t in tasks:
                print(fmt_task(t))
            print()


def cmd_show(args):
    if len(args) < 2:
        die("usage: tm show <project> <id>")
    with get_db() as conn:
        project = resolve_project(conn, args[0])
        task = conn.execute("SELECT * FROM tasks WHERE id=? AND project_id=?", (args[1], project["id"])).fetchone()
        if not task:
            die(f"task #{args[1]} not found in '{args[0]}'")
    print(f"\n[{task['id']}] {task['title']}")
    print(f"status:  {task['status']}")
    print(f"created: {task['created_at']}")
    if task["started_at"]:
        print(f"started: {task['started_at']}")
    if task["completed_at"]:
        print(f"done:    {task['completed_at']}")
    if task["plan"]:
        print(f"\nplan:\n  {task['plan'].replace(chr(10), chr(10)+'  ')}")
    print()


def cmd_start(args):
    if len(args) < 2:
        die("usage: tm start <project> <id>")
    with get_db() as conn:
        project = resolve_project(conn, args[0])
        task = conn.execute("SELECT * FROM tasks WHERE id=? AND project_id=?", (args[1], project["id"])).fetchone()
        if not task:
            die(f"task #{args[1]} not found in '{args[0]}'")
        conn.execute(
            "UPDATE tasks SET status='in_progress', started_at=datetime('now') WHERE id=?",
            (task["id"],)
        )

    print(f"\n▶  {task['title']}")
    if task["plan"]:
        print(f"\nplan:\n  {task['plan'].replace(chr(10), chr(10)+'  ')}")
    print(f"\nproject: {project['path']}")
    print(f"\nlaunching claude code...\n")

    prompt = f"Task: {task['title']}\n\nPlan:\n{task['plan'] or 'No plan provided. Use your best judgement.'}\n\nImplement this task. When done, summarize what you did."

    os.chdir(project["path"])
    subprocess.run(["claude", "--dangerously-skip-permissions", "--print", prompt])

    print(f"\n✓  mark done with: tm done {args[0]} {args[1]}")


def cmd_done(args):
    if len(args) < 2:
        die("usage: tm done <project> <id>")
    with get_db() as conn:
        project = resolve_project(conn, args[0])
        task = conn.execute("SELECT * FROM tasks WHERE id=? AND project_id=?", (args[1], project["id"])).fetchone()
        if not task:
            die(f"task #{args[1]} not found in '{args[0]}'")
        conn.execute(
            "UPDATE tasks SET status='done', completed_at=datetime('now') WHERE id=?",
            (task["id"],)
        )
    print(f"✓  #{args[1]} '{task['title']}' marked done")


def cmd_delete(args):
    if len(args) < 2:
        die("usage: tm delete <project> <id>")
    with get_db() as conn:
        project = resolve_project(conn, args[0])
        task = conn.execute("SELECT * FROM tasks WHERE id=? AND project_id=?", (args[1], project["id"])).fetchone()
        if not task:
            die(f"task #{args[1]} not found in '{args[0]}'")
        conn.execute("DELETE FROM tasks WHERE id=?", (task["id"],))
    print(f"deleted #{args[1]} '{task['title']}'")


def cmd_edit(args):
    if len(args) < 2:
        die("usage: tm edit <project> <id> [--title <title>] [--plan <plan>] [--status <status>]")
    with get_db() as conn:
        project = resolve_project(conn, args[0])
        task = conn.execute("SELECT * FROM tasks WHERE id=? AND project_id=?", (args[1], project["id"])).fetchone()
        if not task:
            die(f"task #{args[1]} not found in '{args[0]}'")

        rest = args[2:]
        updates = {}
        i = 0
        while i < len(rest):
            if rest[i] == "--title" and i+1 < len(rest):
                updates["title"] = rest[i+1]; i += 2
            elif rest[i] == "--plan" and i+1 < len(rest):
                updates["plan"] = rest[i+1]; i += 2
            elif rest[i] == "--status" and i+1 < len(rest):
                updates["status"] = rest[i+1]; i += 2
            else:
                i += 1

        if not updates:
            die("nothing to update. use --title, --plan, or --status")

        set_clause = ", ".join(f"{k}=?" for k in updates)
        conn.execute(f"UPDATE tasks SET {set_clause} WHERE id=?", (*updates.values(), task["id"]))
    print(f"updated #{args[1]}")


# ── MAIN ────────────────────────────────────────────────────────────────────

COMMANDS = {
    "project": {
        "add":  cmd_project_add,
        "list": cmd_project_list,
    },
    "add":    cmd_add,
    "list":   cmd_list,
    "show":   cmd_show,
    "start":  cmd_start,
    "done":   cmd_done,
    "delete": cmd_delete,
    "edit":   cmd_edit,
}


def usage():
    print(__doc__.strip())
    sys.exit(0)


def main():
    init_db()
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        usage()

    cmd = args[0]

    if cmd == "project":
        if len(args) < 2:
            usage()
        sub = args[1]
        if sub not in COMMANDS["project"]:
            die(f"unknown subcommand: project {sub}")
        COMMANDS["project"][sub](args[2:])
    elif cmd in COMMANDS:
        COMMANDS[cmd](args[1:])
    else:
        die(f"unknown command: {cmd}")


if __name__ == "__main__":
    main()
