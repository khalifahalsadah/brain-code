from __future__ import annotations

from datetime import date, timedelta

from .config import Settings
from .dates import target_date_for_append
from .files import daily_note_path, read_auto_region

VALID_PERIODS = ("today", "yesterday", "week", "help")


def recall(period: str, settings: Settings) -> str:
    period = period.lower().lstrip("/")
    if period == "today":
        return _recall_date(settings, target_date_for_append())
    if period == "yesterday":
        return _recall_date(settings, target_date_for_append() - timedelta(days=1))
    if period == "week":
        return _recall_week(settings)
    if period == "help":
        return _help()
    return f"unknown command: /{period}\n\n{_help()}"


def _recall_date(settings: Settings, target: date) -> str:
    path = daily_note_path(settings, target)
    if not path.exists():
        return f"📭 no daily note for {target.isoformat()}"
    content = read_auto_region(path).strip()
    if not content:
        return f"📭 {target.isoformat()}: no bullets yet"
    return f"📝 {target.isoformat()}\n\n{content}"


def _recall_week(settings: Settings) -> str:
    today = target_date_for_append()
    lines: list[str] = []
    for i in range(7):
        d = today - timedelta(days=i)
        path = daily_note_path(settings, d)
        if not path.exists():
            lines.append(f"— {d.strftime('%a %Y-%m-%d')}: (none)")
            continue
        content = read_auto_region(path).strip()
        n_bullets = sum(
            1 for line in content.splitlines() if line.lstrip().startswith("-")
        )
        marker = "•" if n_bullets > 0 else "—"
        lines.append(f"{marker} {d.strftime('%a %Y-%m-%d')}: {n_bullets} bullets")
    return "📅 Last 7 days\n\n" + "\n".join(lines)


def _help() -> str:
    return (
        "Commands:\n"
        "/today — show today's captured bullets\n"
        "/yesterday — show yesterday's bullets\n"
        "/week — bullet counts for the last 7 days\n"
        "/search <term> — find bullets across all daily notes\n"
        "/undo — remove the last bullet from today\n"
        "/help — this message\n\n"
        "Anything else (text or voice) is appended to today's daily note."
    )
