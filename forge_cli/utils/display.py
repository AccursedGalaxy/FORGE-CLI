from rich.console import Console
from rich.theme import Theme

console = Console(theme=Theme({
    "status.pending":     "",
    "status.in_progress": "bold yellow",
    "status.done":        "dim",
    "status.blocked":     "bold red",
    "label":              "dim",
    "project.header":     "bold",
    "success":            "green",
    "plan.border":        "dim cyan",
}))

STATUS_STYLES: dict[str, str] = {
    "pending":     "status.pending",
    "in_progress": "status.in_progress",
    "done":        "status.done",
    "blocked":     "status.blocked",
}

PAGER_LINE_THRESHOLD = 25
PLAN_PREVIEW_LINES = 12
