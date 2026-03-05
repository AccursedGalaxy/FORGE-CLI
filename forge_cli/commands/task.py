import os
import subprocess
import click
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from forge_cli.config import STATUS_ICONS, VALID_STATUSES
from forge_cli.db import get_db, resolve_project
from forge_cli.utils.display import console, STATUS_STYLES, PLAN_PREVIEW_LINES
from forge_cli.utils.fmt import fmt_task


@click.command("add")
@click.argument("project")
@click.argument("title")
@click.option("--plan", default=None, help="Implementation plan passed verbatim to Claude when the task is started.")
def add(project, title, plan):
    """Add a task to a project.

    PROJECT is the registered project name (see `tm project list`).
    TITLE is a short description of the work to be done.
    Use --plan to provide a detailed step-by-step plan; it will be shown to
    Claude when the task is started with `tm start`.
    """
    with get_db() as conn:
        proj = resolve_project(conn, project)
        conn.execute(
            "INSERT INTO tasks (project_id, title, plan) VALUES (?, ?, ?)",
            (proj["id"], title, plan)
        )
        task_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    console.print(f"[success]added task #{task_id} to '{project}'[/]")


@click.command("list")
@click.argument("project", required=False)
@click.option("--all", "show_all", is_flag=True, default=False, help="List tasks for all projects.")
def list_(project, show_all):
    """List tasks for a project or all projects.

    \b
    Examples:
      tm list myapp          List tasks for the 'myapp' project
      tm list --all          List tasks across every registered project
    """
    with get_db() as conn:
        if show_all:
            projects = conn.execute("SELECT * FROM projects ORDER BY name").fetchall()
            for p in projects:
                tasks = conn.execute(
                    "SELECT * FROM tasks WHERE project_id=? ORDER BY status, id", (p["id"],)
                ).fetchall()
                if not tasks:
                    continue
                console.print(f"\n[project.header]{p['name']}[/]  [label]{p['path']}[/label]")
                for t in tasks:
                    console.print(fmt_task(t))
        else:
            if not project:
                raise click.ClickException("usage: tm list <project> [--all]")
            proj = resolve_project(conn, project)
            tasks = conn.execute(
                "SELECT * FROM tasks WHERE project_id=? ORDER BY status, id", (proj["id"],)
            ).fetchall()
            if not tasks:
                console.print(f"[dim]no tasks in '{project}'[/dim]")
                return
            console.print(f"\n[project.header]{proj['name']}[/]  [label]{proj['path']}[/label]")
            for t in tasks:
                console.print(fmt_task(t))
            console.print()


@click.command("show")
@click.argument("project")
@click.argument("id", type=int)
def show(project, id):
    """Show full details of a task.

    Displays status, timestamps (started/completed only shown if set),
    and the full plan text if one exists.
    """
    with get_db() as conn:
        proj = resolve_project(conn, project)
        task = conn.execute(
            "SELECT * FROM tasks WHERE id=? AND project_id=?", (id, proj["id"])
        ).fetchone()
        if not task:
            raise click.ClickException(f"task #{id} not found in '{project}'")

    status = task["status"]
    icon = STATUS_ICONS.get(status, "?")
    style = STATUS_STYLES.get(status, "")

    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="label")
    grid.add_column()
    grid.add_row("status", Text(f"{icon}  {status}", style=style))
    grid.add_row("created", task["created_at"])
    if task["started_at"]:
        grid.add_row("started", task["started_at"])
    if task["completed_at"]:
        grid.add_row("done", task["completed_at"])

    content = grid
    if task["plan"]:
        from rich.console import Group
        from rich.rule import Rule
        from rich.padding import Padding
        plan_block = Padding(task["plan"], (1, 0, 0, 2))
        content = Group(grid, Rule(style="plan.border"), plan_block)

    console.print(Panel(content, title=f"[bold]#{task['id']} {task['title']}[/bold]", expand=False))
    console.print()


@click.command("start")
@click.argument("project")
@click.argument("id", type=int)
def start(project, id):
    """Start a task by launching Claude Code autonomously.

    Marks the task as in_progress, then runs:

    \b
      claude --dangerously-skip-permissions --print "<title + plan>"

    from the project's registered directory. Claude implements the task and
    prints a summary when finished. After it completes, mark the task done
    with `tm done <project> <id>`.

    Note: --dangerously-skip-permissions allows Claude to run without
    permission prompts. Only use on projects you trust.
    """
    with get_db() as conn:
        proj = resolve_project(conn, project)
        task = conn.execute(
            "SELECT * FROM tasks WHERE id=? AND project_id=?", (id, proj["id"])
        ).fetchone()
        if not task:
            raise click.ClickException(f"task #{id} not found in '{project}'")
        conn.execute(
            "UPDATE tasks SET status='in_progress', started_at=datetime('now') WHERE id=?",
            (task["id"],)
        )

    console.print(f"\n[bold]▶  {task['title']}[/bold]")

    if task["plan"]:
        plan_lines = task["plan"].splitlines()
        preview = plan_lines[:PLAN_PREVIEW_LINES]
        console.print()
        for line in preview:
            console.print(f"  [dim]{line}[/dim]")
        remaining = len(plan_lines) - PLAN_PREVIEW_LINES
        if remaining > 0:
            console.print(f"  [dim]... {remaining} more lines[/dim]")

    console.print(f"\n[label]project:[/label] {proj['path']}")
    console.print("\n[dim]launching claude code...[/dim]\n")

    prompt = (
        f"Task: {task['title']}\n\nPlan:\n"
        f"{task['plan'] or 'No plan provided. Use your best judgement.'}\n\n"
        f"Implement this task. When done, summarize what you did."
    )

    os.chdir(proj["path"])
    subprocess.run(["claude", "--dangerously-skip-permissions", "--print", prompt])

    console.print(f"\n[success]✓[/]  mark done with: [bold]tm done {project} {id}[/bold]")


@click.command("done")
@click.argument("project")
@click.argument("id", type=int)
def done(project, id):
    """Mark a task as done."""
    with get_db() as conn:
        proj = resolve_project(conn, project)
        task = conn.execute(
            "SELECT * FROM tasks WHERE id=? AND project_id=?", (id, proj["id"])
        ).fetchone()
        if not task:
            raise click.ClickException(f"task #{id} not found in '{project}'")
        conn.execute(
            "UPDATE tasks SET status='done', completed_at=datetime('now') WHERE id=?",
            (task["id"],)
        )
    console.print(f"[success]✓[/]  #{id} '{task['title']}' marked done")


@click.command("delete")
@click.argument("project")
@click.argument("id", type=int)
def delete(project, id):
    """Delete a task."""
    with get_db() as conn:
        proj = resolve_project(conn, project)
        task = conn.execute(
            "SELECT * FROM tasks WHERE id=? AND project_id=?", (id, proj["id"])
        ).fetchone()
        if not task:
            raise click.ClickException(f"task #{id} not found in '{project}'")
        conn.execute("DELETE FROM tasks WHERE id=?", (task["id"],))
    console.print(f"[dim]deleted[/dim] #{id} '{task['title']}'")


@click.command("edit")
@click.argument("project")
@click.argument("id", type=int)
@click.option("--title", default=None, help="New title.")
@click.option("--plan", default=None, help="New plan.")
@click.option("--status", default=None, type=click.Choice(VALID_STATUSES),
              help="New status. Valid values: pending, in_progress, done, blocked.")
def edit(project, id, title, plan, status):
    """Edit one or more fields of a task.

    At least one of --title, --plan, or --status must be provided.
    """
    updates = {k: v for k, v in [("title", title), ("plan", plan), ("status", status)] if v is not None}
    if not updates:
        raise click.ClickException("nothing to update. use --title, --plan, or --status")
    with get_db() as conn:
        proj = resolve_project(conn, project)
        task = conn.execute(
            "SELECT * FROM tasks WHERE id=? AND project_id=?", (id, proj["id"])
        ).fetchone()
        if not task:
            raise click.ClickException(f"task #{id} not found in '{project}'")
        set_clause = ", ".join(f"{k}=?" for k in updates)
        conn.execute(f"UPDATE tasks SET {set_clause} WHERE id=?", (*updates.values(), task["id"]))
    console.print(f"[success]updated[/success] #{id}")
