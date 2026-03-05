# FORGE-CLI (`tm`)

`forge-cli` is an AI-powered task runner that launches Claude Code against your tasks. The `tm` command lets you register project directories, manage tasks, and run Claude autonomously to implement them.

## Install

```bash
pip install -e .
```

Requires Python 3.13+ and the `claude` CLI in your PATH.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `TM_DB`  | `~/.taskmaster/tasks.db` | Path to the SQLite database |

## Quick Start

```bash
# Register a project
tm project add myapp ~/Projects/myapp

# Generate an AI plan, then save it as a task
tm plan myapp "Refactor the auth module"

# Or add a task manually
tm add myapp "Fix the login bug" --plan "Check auth middleware in src/auth.py"

# Launch Claude Code on it
tm start myapp 1

# Mark done
tm done myapp 1
```

## Commands

### Projects

```
tm project add <name> <path>   Register a project directory (name must be unique)
tm project list                List all projects with pending task counts
```

### Tasks

```
tm add <project> <title> [--plan <text>]              Add a task
tm list <project>                                      List tasks for a project
tm list --all                                          List tasks across all projects
tm show <project> <id>                                 Show full task details
tm start <project> <id>                                Start task (launches Claude Code)
tm done <project> <id>                                 Mark task as done
tm edit <project> <id> [--title] [--plan] [--status]  Edit task fields
tm delete <project> <id>                               Delete a task
```

**Task statuses:** `pending` `in_progress` `done` `blocked`

### Planning

```
tm plan <project> <title>      Generate an AI plan and optionally save as a task
```

`tm plan` runs Claude in planning-only mode — it explores your codebase and produces a step-by-step implementation plan without making any changes. You are then prompted to save the plan as a new task.

## How `tm start` Works

`tm start` marks the task as `in_progress`, then runs:

```
claude --dangerously-skip-permissions --print "<task title + plan>"
```

from the project's registered directory. Claude Code implements the task autonomously and prints a summary when done.

> **Note:** `--dangerously-skip-permissions` allows Claude to act without
> confirmation prompts. Only use `tm start` on projects and tasks you trust.

## Workflow Example

```bash
# 1. Register your project once
tm project add myapp ~/Projects/myapp

# 2. Generate a plan for a new feature
tm plan myapp "Add rate limiting to the API"
# → Claude explores the codebase, streams a plan, prompts to save

# 3. Review saved tasks
tm list myapp

# 4. Start Claude on the task (autonomous implementation)
tm start myapp 1

# 5. Review the output, then mark done
tm done myapp 1

# 6. Check across all projects
tm list --all
```

## Storage

Tasks are stored in `~/.taskmaster/tasks.db` (SQLite). Override the path with the `TM_DB` environment variable.
