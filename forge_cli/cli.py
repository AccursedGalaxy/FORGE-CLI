import click
from forge_cli.db import init_db
from forge_cli.commands.project import project
from forge_cli.commands.task import add, list_, show, start, done, delete, edit
from forge_cli.commands.plan import plan

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click.group(context_settings=CONTEXT_SETTINGS)
def cli():
    """tm — AI-powered task runner for Claude Code.

    Register projects by directory, manage tasks, and launch Claude Code
    autonomously against each task. Tasks persist in a local SQLite database.

    \b
    Configuration:
      TM_DB   Path to the SQLite database (default: ~/.taskmaster/tasks.db)

    \b
    Typical workflow:
      tm project add myapp ~/Projects/myapp
      tm plan myapp "Refactor auth module"
      tm list myapp
      tm start myapp 1
      tm done myapp 1
    """
    init_db()


cli.add_command(project)
cli.add_command(plan)
for cmd in [add, list_, show, start, done, delete, edit]:
    cli.add_command(cmd)
