from rich.text import Text
from forge_cli.config import STATUS_ICONS
from forge_cli.utils.display import STATUS_STYLES


def fmt_task(t, verbose=False) -> Text:
    status = t["status"]
    icon = STATUS_ICONS.get(status, "?")
    style = STATUS_STYLES.get(status, "")
    line = Text(f"  [{t['id']:>3}] {icon}  {t['title']}", style=style)
    if verbose and t["plan"]:
        for plan_line in t["plan"].splitlines():
            line.append(f"\n         {plan_line}", style="dim")
    return line
