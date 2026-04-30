from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from brain_code.config import Settings
from brain_code.recall import recall

TZ = ZoneInfo("Asia/Riyadh")


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    vault = tmp_path / "vault"
    (vault / "Extras/Templates").mkdir(parents=True)
    return Settings(
        vault_root=vault,
        project_root=tmp_path / "project",
        api_key=None,
    )


def _write_note(settings: Settings, d: date, body: str) -> Path:
    rel = (
        f"03 Timestamps/{d.strftime('%Y')}/{d.strftime('%m-%B')}/"
        f"{d.strftime('%Y-%m-%d-%A')}.md"
    )
    path = settings.vault_root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"# 📝 Notes\n<!-- auto-region -->\n{body}\n<!-- /auto-region -->\n",
        encoding="utf-8",
    )
    return path


def test_recall_help(settings: Settings):
    out = recall("help", settings)
    assert "/today" in out and "/week" in out


def test_recall_unknown_command_includes_help(settings: Settings):
    out = recall("nonsense", settings)
    assert "unknown" in out
    assert "/today" in out


def test_recall_strips_leading_slash(settings: Settings):
    out = recall("/help", settings)
    assert "/today" in out


def test_recall_today_no_file(settings: Settings):
    out = recall("today", settings)
    assert "no daily note" in out


def test_recall_today_empty_region(settings: Settings, monkeypatch: pytest.MonkeyPatch):
    today = date(2026, 4, 30)
    monkeypatch.setattr("brain_code.recall.target_date_for_append", lambda: today)
    _write_note(settings, today, "")
    out = recall("today", settings)
    assert "no bullets yet" in out


def test_recall_today_returns_bullets(settings: Settings, monkeypatch: pytest.MonkeyPatch):
    today = date(2026, 4, 30)
    monkeypatch.setattr("brain_code.recall.target_date_for_append", lambda: today)
    _write_note(settings, today, "- first\n- second")
    out = recall("today", settings)
    assert "📝 2026-04-30" in out
    assert "- first" in out
    assert "- second" in out


def test_recall_yesterday(settings: Settings, monkeypatch: pytest.MonkeyPatch):
    today = date(2026, 4, 30)
    monkeypatch.setattr("brain_code.recall.target_date_for_append", lambda: today)
    _write_note(settings, today - timedelta(days=1), "- ran ten kilometers")
    out = recall("yesterday", settings)
    assert "📝 2026-04-29" in out
    assert "- ran ten kilometers" in out


def test_recall_week_lists_seven_days(settings: Settings, monkeypatch: pytest.MonkeyPatch):
    today = date(2026, 4, 30)
    monkeypatch.setattr("brain_code.recall.target_date_for_append", lambda: today)
    _write_note(settings, today, "- one\n- two\n- three")
    _write_note(settings, today - timedelta(days=2), "- alpha")
    out = recall("week", settings)
    assert "Last 7 days" in out
    assert "Thu 2026-04-30: 3 bullets" in out
    assert "Tue 2026-04-28: 1 bullets" in out
    assert "(none)" in out
    assert out.count("\n") >= 7
