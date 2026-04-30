from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from brain_code.dates import (
    daily_note_basename,
    daily_note_relative_path,
    daily_note_wikilink_target,
    target_date_for_append,
    target_date_for_synthesize,
)

TZ = ZoneInfo("Asia/Riyadh")


def test_append_target_after_4am_is_today():
    now = datetime(2026, 4, 30, 9, 0, tzinfo=TZ)
    assert target_date_for_append(now) == date(2026, 4, 30)


def test_append_target_before_4am_maps_to_yesterday():
    now = datetime(2026, 4, 30, 2, 0, tzinfo=TZ)
    assert target_date_for_append(now) == date(2026, 4, 29)


def test_append_target_at_4am_sharp_is_today():
    now = datetime(2026, 4, 30, 4, 0, tzinfo=TZ)
    assert target_date_for_append(now) == date(2026, 4, 30)


def test_append_target_rolls_over_year_boundary():
    now = datetime(2026, 1, 1, 1, 30, tzinfo=TZ)
    assert target_date_for_append(now) == date(2025, 12, 31)


def test_synthesize_at_cron_time_processes_logical_yesterday():
    # Cron fires at 04:05 → logical day just ended → process the day before.
    now = datetime(2026, 4, 30, 4, 5, tzinfo=TZ)
    assert target_date_for_synthesize(now) == date(2026, 4, 29)


def test_synthesize_run_in_evening_still_processes_logical_yesterday():
    # If run manually at 22:00, today's logical day is not over → process yesterday.
    now = datetime(2026, 4, 30, 22, 0, tzinfo=TZ)
    assert target_date_for_synthesize(now) == date(2026, 4, 29)


def test_synthesize_run_pre_4am_processes_two_days_ago():
    # If run at 02:00, logical-today is yesterday (April 29) → process April 28.
    now = datetime(2026, 4, 30, 2, 0, tzinfo=TZ)
    assert target_date_for_synthesize(now) == date(2026, 4, 28)


def test_daily_note_relative_path():
    p = daily_note_relative_path(date(2026, 4, 30))
    assert p == Path("03 Timestamps/2026/04-April/2026-04-30-Thursday.md")


def test_daily_note_relative_path_january():
    p = daily_note_relative_path(date(2026, 1, 1))
    assert p == Path("03 Timestamps/2026/01-January/2026-01-01-Thursday.md")


def test_daily_note_basename():
    assert daily_note_basename(date(2026, 4, 30)) == "2026-04-30-Thursday"


def test_wikilink_target_for_navigation():
    target = daily_note_wikilink_target(date(2026, 4, 29))
    assert target == "03 Timestamps/2026/04-April/2026-04-29-Wednesday"
