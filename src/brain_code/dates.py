from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

from .config import LATE_NIGHT_CUTOFF_HOUR, TIMEZONE


def now_local() -> datetime:
    return datetime.now(TIMEZONE)


def target_date_for_append(now: datetime | None = None) -> date:
    """Real-time append target: messages before 04:00 local time map to yesterday."""
    n = now or now_local()
    if n.hour < LATE_NIGHT_CUTOFF_HOUR:
        return (n - timedelta(days=1)).date()
    return n.date()


def target_date_for_synthesize(now: datetime | None = None) -> date:
    """Nightly synthesize target: the most recent fully-completed logical day.

    A logical day runs from LATE_NIGHT_CUTOFF_HOUR to the same hour next calendar
    day. The cron fires at 04:05, so logical-yesterday is what we synthesize.
    """
    n = now or now_local()
    logical_today = target_date_for_append(n)
    return logical_today - timedelta(days=1)


def daily_note_relative_path(d: date) -> Path:
    """Vault-relative path: 03 Timestamps/YYYY/MM-MMMM/YYYY-MM-DD-dddd.md"""
    return Path(
        "03 Timestamps",
        d.strftime("%Y"),
        d.strftime("%m-%B"),
        f"{d.strftime('%Y-%m-%d-%A')}.md",
    )


def daily_note_basename(d: date) -> str:
    """Filename without extension, used for wikilinks (e.g. yesterday/tomorrow nav)."""
    return d.strftime("%Y-%m-%d-%A")


def daily_note_wikilink_target(d: date) -> str:
    """Path used inside [[ ]] for yesterday/tomorrow nav."""
    return (
        f"03 Timestamps/{d.strftime('%Y')}/"
        f"{d.strftime('%m-%B')}/{daily_note_basename(d)}"
    )
