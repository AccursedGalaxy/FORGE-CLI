from forge_cli.config import STATUS_ICONS


def fmt_task(t, verbose=False):
    icon = STATUS_ICONS.get(t["status"], "?")
    line = f"  [{t['id']:>3}] {icon}  {t['title']}"
    if verbose and t["plan"]:
        for l in t["plan"].splitlines():
            line += f"\n         {l}"
    return line
