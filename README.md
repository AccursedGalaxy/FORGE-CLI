# FORGE-CLI (tm)

A minimal task manager CLI that launches Claude Code directly against your tasks.

## Install

```bash
pip install -e .
```

Requires Python 3.13+ and the `claude` CLI in your PATH.

## Quick Start

```bash
# Register a project
tm project add myapp ~/Projects/myapp

# Add a task
tm add myapp "Fix the login bug" --plan "Check auth middleware in src/auth.py"

# Launch Claude Code on it
tm start myapp 1

# Mark done
tm done myapp 1
```

## Commands

### Projects

```
tm project add <name> <path>   Register a project directory
tm project list                List all projects with pending task counts
```

### Tasks

```
tm add <project> <title> [--plan <text>]          Add a task
tm list <project>                                  List tasks for a project
tm list --all                                      List tasks across all projects
tm show <project> <id>                             Show task details
tm start <project> <id>                            Start task (launches Claude Code)
tm done <project> <id>                             Mark task as done
tm edit <project> <id> [--title] [--plan] [--status]  Edit task fields
tm delete <project> <id>                           Delete a task
```

**Task statuses:** `pending` `in_progress` `done` `blocked`

## How `tm start` Works

`tm start` marks the task as in-progress, then runs:

```
claude --dangerously-skip-permissions --print "<task title + plan>"
```

from the project's registered directory. Claude Code implements the task autonomously and prints a summary when done.

## Storage

Tasks are stored in `~/.taskmaster/tasks.db` (SQLite). Override with `TM_DB=/path/to/db`.
