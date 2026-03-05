import os
import subprocess
import sys
import click
from rich.rule import Rule
from forge_cli.db import get_db, resolve_project
from forge_cli.utils.display import console, PAGER_LINE_THRESHOLD

PLANNING_PROMPT = """\
You are a planning assistant. Do NOT implement anything.

Project: {project_name}
Path: {project_path}
Task: {title}

Explore the codebase to understand the structure, then produce a \
concise step-by-step implementation plan for the task above.

Include: specific files to create/modify, key implementation steps, \
and any non-obvious considerations.

Output ONLY the plan. No preamble, no summary.\
"""

@click.command("plan")
@click.argument("project")
@click.argument("title")
def plan(project, title):
    """Generate an AI implementation plan for a task using Claude.

    Runs Claude in planning-only mode (no code changes) against the project
    directory. Claude explores the codebase and produces a concise step-by-step
    plan for TITLE, which is streamed to the terminal.

    After the plan is displayed you are prompted to save it as a new task.
    The saved task can then be executed with `tm start <project> <id>`.

    \b
    Example:
      tm plan myapp "Refactor the auth module"
    """
    with get_db() as conn:
        proj = resolve_project(conn, project)

    prompt = PLANNING_PROMPT.format(
        project_name=proj["name"],
        project_path=proj["path"],
        title=title,
    )

    console.print()
    console.print(Rule(f"[bold]Planning: {title}[/bold]", style="plan.border"))
    os.chdir(proj["path"])

    proc = subprocess.Popen(
        ["claude", "--print", prompt],
        stdout=subprocess.PIPE,
        text=True,
    )
    lines = []
    for line in proc.stdout:
        print(line, end="", flush=True)
        lines.append(line)
    proc.wait()

    console.print(Rule(style="plan.border"))

    if proc.returncode != 0:
        raise click.ClickException("claude exited with an error.")

    plan_text = "".join(lines).strip()
    if not plan_text:
        raise click.ClickException("claude returned an empty plan.")

    if len(lines) > PAGER_LINE_THRESHOLD and sys.stdout.isatty():
        if click.confirm(f"\nPlan is {len(lines)} lines. Review in pager?", default=False):
            with console.pager(styles=False):
                console.print(plan_text)

    if not click.confirm("\nSave as new task?", default=True):
        console.print("[dim]discarded.[/dim]")
        return

    with get_db() as conn:
        proj_row = resolve_project(conn, project)
        conn.execute(
            "INSERT INTO tasks (project_id, title, plan) VALUES (?, ?, ?)",
            (proj_row["id"], title, plan_text),
        )
        task_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    console.print(f"[success]added task #{task_id} to '{project}'[/]")
