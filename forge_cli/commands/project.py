from pathlib import Path
import click
import rich.box
from rich.table import Table
from rich.text import Text
from forge_cli.db import get_db
from forge_cli.utils.display import console

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click.group(context_settings=CONTEXT_SETTINGS)
def project():
    """Manage registered project directories.

    Projects are named aliases for local directories. All task commands
    reference projects by their NAME rather than the full path.
    """


@project.command("add")
@click.argument("name", metavar="NAME")
@click.argument("path", metavar="PATH")
def project_add(name, path):
    """Register a directory as a named project.

    NAME must be unique. PATH is expanded and resolved to an absolute path;
    it must already exist on disk.
    """
    path = str(Path(path).expanduser().resolve())
    if not Path(path).exists():
        raise click.ClickException(f"path does not exist: {path}")
    with get_db() as conn:
        conn.execute("INSERT INTO projects (name, path) VALUES (?, ?)", (name, path))
    console.print(f"[success]added project[/] [bold]{name}[/bold] → {path}")


@project.command("list")
def project_list():
    """List all registered projects.

    Shows each project's name, path, and number of non-done tasks (pending count).
    """
    with get_db() as conn:
        rows = conn.execute(
            "SELECT p.*, COUNT(t.id) as task_count FROM projects p "
            "LEFT JOIN tasks t ON t.project_id = p.id GROUP BY p.id ORDER BY p.name"
        ).fetchall()
    if not rows:
        console.print("[dim]no projects yet. add one with: tm project add <name> <path>[/dim]")
        return

    table = Table(box=rich.box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("project", no_wrap=True, style="bold")
    table.add_column("path", style="dim")
    table.add_column("pending", justify="right")

    for r in rows:
        with get_db() as conn:
            pending = conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE project_id=? AND status!='done'",
                (r["id"],)
            ).fetchone()[0]
        pending_text = Text(str(pending), style="dim" if pending == 0 else "")
        table.add_row(r["name"], r["path"], pending_text)

    console.print(table)
