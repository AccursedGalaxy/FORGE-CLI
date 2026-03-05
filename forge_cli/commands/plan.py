import os
import subprocess
import click
from forge_cli.db import get_db, resolve_project

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

    print(f"\nPlanning: {title}\n" + "─" * 60)
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

    print("─" * 60)

    if proc.returncode != 0:
        raise click.ClickException("claude exited with an error.")

    plan_text = "".join(lines).strip()
    if not plan_text:
        raise click.ClickException("claude returned an empty plan.")

    if not click.confirm("\nSave as new task?", default=True):
        print("discarded.")
        return

    with get_db() as conn:
        proj_row = resolve_project(conn, project)
        conn.execute(
            "INSERT INTO tasks (project_id, title, plan) VALUES (?, ?, ?)",
            (proj_row["id"], title, plan_text),
        )
        task_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    print(f"added task #{task_id} to '{project}'")
