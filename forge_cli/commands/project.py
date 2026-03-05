from pathlib import Path
import click
from forge_cli.db import get_db


@click.group()
def project():
    """Manage projects."""


@project.command("add")
@click.argument("name")
@click.argument("path")
def project_add(name, path):
    """Add a project."""
    path = str(Path(path).expanduser().resolve())
    if not Path(path).exists():
        raise click.ClickException(f"path does not exist: {path}")
    with get_db() as conn:
        conn.execute("INSERT INTO projects (name, path) VALUES (?, ?)", (name, path))
    print(f"added project '{name}' → {path}")


@project.command("list")
def project_list():
    """List all projects."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT p.*, COUNT(t.id) as task_count FROM projects p "
            "LEFT JOIN tasks t ON t.project_id = p.id GROUP BY p.id ORDER BY p.name"
        ).fetchall()
    if not rows:
        print("no projects yet. add one with: tm project add <name> <path>")
        return
    for r in rows:
        with get_db() as conn:
            pending = conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE project_id=? AND status!='done'",
                (r["id"],)
            ).fetchone()[0]
        print(f"  {r['name']:<20} {r['path']}  ({pending} pending)")
