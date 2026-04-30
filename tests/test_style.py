from datetime import date
from pathlib import Path

import pytest

from brain_code.config import Settings
from brain_code.style import find_recent_daily_notes, style_examples_text


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    vault = tmp_path / "vault"
    base = vault / "03 Timestamps"
    feb = base / "2026" / "02-February"
    feb.mkdir(parents=True)
    for day in [17, 18, 19, 20, 21]:
        (feb / f"2026-02-{day:02d}-Day.md").write_text(
            f"day {day} content", encoding="utf-8"
        )
    march = base / "2026" / "03-March"
    march.mkdir()
    (march / "2026-03-03-Tuesday.md").write_text("march 3 content", encoding="utf-8")
    # Add a non-daily file (should be ignored)
    (base / "2026" / "Index.md").write_text("not a daily", encoding="utf-8")
    return Settings(
        vault_root=vault,
        project_root=tmp_path / "project",
        api_key=None,
    )


def test_find_recent_returns_most_recent_n(settings: Settings):
    paths = find_recent_daily_notes(settings, before=date(2026, 4, 30), count=3)
    stems = [p.stem for p in paths]
    assert stems == [
        "2026-03-03-Tuesday",
        "2026-02-21-Day",
        "2026-02-20-Day",
    ]


def test_find_recent_excludes_target_date_and_after(settings: Settings):
    paths = find_recent_daily_notes(settings, before=date(2026, 2, 19), count=10)
    stems = [p.stem for p in paths]
    assert stems == ["2026-02-18-Day", "2026-02-17-Day"]


def test_find_recent_ignores_non_daily_files(settings: Settings):
    paths = find_recent_daily_notes(settings, before=date(2026, 12, 31), count=10)
    assert all("Index" not in p.stem for p in paths)


def test_style_examples_concatenates(settings: Settings):
    paths = find_recent_daily_notes(settings, before=date(2026, 4, 30), count=2)
    text = style_examples_text(paths)
    assert "=== 2026-03-03-Tuesday ===" in text
    assert "march 3 content" in text
    assert "=== 2026-02-21-Day ===" in text
