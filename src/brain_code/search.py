from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from .config import Settings


def search(
    term: str,
    settings: Settings,
    max_results: int = 5,
    max_chars: int = 3500,
) -> str:
    """Search daily-note bullets for a term (case-insensitive substring).

    Returns formatted string with up to `max_results` most-recent matches, capped
    at `max_chars` to fit in a single Telegram message.
    """
    term = term.strip()
    if not term:
        return "🔍 empty search term"

    matches = _collect_matches(settings.daily_notes_root, term)
    if not matches:
        return f"🔍 no matches for '{term}'"

    matches.sort(key=lambda t: t[0], reverse=True)

    header = (
        f"🔍 '{term}' — {len(matches)} match"
        f"{'es' if len(matches) != 1 else ''}, showing latest {min(len(matches), max_results)}"
    )
    out = [header, ""]
    for d, line in matches[:max_results]:
        block = f"📅 {d.isoformat()}\n   {line}"
        if sum(len(s) + 1 for s in out) + len(block) > max_chars:
            break
        out.append(block)
    return "\n".join(out)


def _collect_matches(root: Path, term: str) -> list[tuple[date, str]]:
    if not root.exists():
        return []
    needle = term.lower()
    out: list[tuple[date, str]] = []
    for path in root.rglob("*.md"):
        d = _parse_date(path.stem)
        if d is None:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for line in content.splitlines():
            stripped = line.lstrip()
            if not stripped.startswith("-"):
                continue
            if needle in stripped.lower():
                out.append((d, stripped))
    return out


def _parse_date(stem: str) -> date | None:
    if len(stem) < 10:
        return None
    try:
        return datetime.strptime(stem[:10], "%Y-%m-%d").date()
    except ValueError:
        return None
