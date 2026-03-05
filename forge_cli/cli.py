import click
from forge_cli.db import init_db
from forge_cli.commands.project import project
from forge_cli.commands.task import add, list_, show, start, done, delete, edit


@click.group()
def cli():
    """tm - taskmaster CLI"""
    init_db()


cli.add_command(project)
for cmd in [add, list_, show, start, done, delete, edit]:
    cli.add_command(cmd)
