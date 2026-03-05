import os
from pathlib import Path

DB_PATH = Path(os.environ.get("TM_DB", Path.home() / ".taskmaster" / "tasks.db"))

STATUS_ICONS = {
    "pending":     "○",
    "in_progress": "◉",
    "done":        "✓",
    "blocked":     "✗",
}

VALID_STATUSES = ("pending", "in_progress", "done", "blocked")
