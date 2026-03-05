import os
import subprocess
import click
from forge_cli.config import VALID_STATUSES
from forge_cli.db import get_db, resolve_project
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
    print(f"added task #{task_id} to '{project}'")


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
                print(f"\n{p['name']}  ({p['path']})")
                for t in tasks:
                    print(fmt_task(t))
        else:
            if not project:
                raise click.ClickException("usage: tm list <project> [--all]")
            proj = resolve_project(conn, project)
            tasks = conn.execute(
                "SELECT * FROM tasks WHERE project_id=? ORDER BY status, id", (proj["id"],)
            ).fetchall()
            if not tasks:
                print(f"no tasks in '{project}'")
                return
            print(f"\n{proj['name']}  ({proj['path']})")
            for t in tasks:
                print(fmt_task(t))
            print()


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

    print(f"\n▶  {task['title']}")
    if task["plan"]:
        print(f"\nplan:\n  {task['plan'].replace(chr(10), chr(10)+'  ')}")
    print(f"\nproject: {proj['path']}")
    print(f"\nlaunching claude code...\n")

    prompt = (
        f"Task: {task['title']}\n\nPlan:\n"
        f"{task['plan'] or 'No plan provided. Use your best judgement.'}\n\n"
        f"Implement this task. When done, summarize what you did."
    )

    os.chdir(proj["path"])
    subprocess.run(["claude", "--dangerously-skip-permissions", "--print", prompt])

    print(f"\n✓  mark done with: tm done {project} {id}")


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
    print(f"✓  #{id} '{task['title']}' marked done")


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
    print(f"deleted #{id} '{task['title']}'")


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
    print(f"updated #{id}")
