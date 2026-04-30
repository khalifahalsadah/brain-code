from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from .config import Settings


def find_recent_daily_notes(
    settings: Settings, before: date, count: int = 5
) -> list[Path]:
    """Return the `count` most recent daily-note paths with date strictly < `before`."""
    root = settings.daily_notes_root
    if not root.exists():
        return []

    candidates: list[tuple[date, Path]] = []
    for path in root.rglob("*.md"):
        d = _parse_date_from_basename(path.stem)
        if d is None:
            continue
        if d < before:
            candidates.append((d, path))

    candidates.sort(key=lambda t: t[0], reverse=True)
    return [path for _, path in candidates[:count]]


def style_examples_text(paths: list[Path]) -> str:
    """Concatenate file contents with simple separators for prompt injection."""
    parts: list[str] = []
    for path in paths:
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue
        parts.append(f"=== {path.stem} ===\n{content.strip()}")
    return "\n\n".join(parts)


def _parse_date_from_basename(stem: str) -> date | None:
    """Daily notes are named YYYY-MM-DD-DayName."""
    if len(stem) < 10:
        return None
    try:
        return datetime.strptime(stem[:10], "%Y-%m-%d").date()
    except ValueError:
        return None
