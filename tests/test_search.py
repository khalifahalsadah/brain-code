from datetime import date
from pathlib import Path

import pytest

from brain_code.config import Settings
from brain_code.search import search


def _write_note(vault: Path, d: date, body: str) -> Path:
    rel = (
        f"03 Timestamps/{d.strftime('%Y')}/{d.strftime('%m-%B')}/"
        f"{d.strftime('%Y-%m-%d-%A')}.md"
    )
    path = vault / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        vault_root=tmp_path / "vault",
        project_root=tmp_path / "project",
        api_key=None,
    )


def test_search_no_matches(settings: Settings):
    out = search("nothing", settings)
    assert "no matches" in out


def test_search_empty_term(settings: Settings):
    assert "empty" in search("   ", settings)


def test_search_finds_matching_bullet(settings: Settings):
    _write_note(
        settings.vault_root,
        date(2026, 4, 17),
        "# 📝 Notes\n- جبت سوار ل[[روان]]\n- اشتريت عصير\n",
    )
    out = search("روان", settings)
    assert "روان" in out
    assert "📅 2026-04-17" in out


def test_search_case_insensitive_latin(settings: Settings):
    _write_note(
        settings.vault_root,
        date(2026, 4, 18),
        "- watched Inception with Sara\n",
    )
    out = search("inception", settings)
    assert "Inception" in out


def test_search_returns_most_recent_first(settings: Settings):
    _write_note(settings.vault_root, date(2026, 2, 1), "- met [[ahmed]] in feb\n")
    _write_note(settings.vault_root, date(2026, 3, 1), "- met [[ahmed]] in mar\n")
    _write_note(settings.vault_root, date(2026, 4, 1), "- met [[ahmed]] in apr\n")
    out = search("ahmed", settings, max_results=2)
    apr_pos = out.find("apr")
    mar_pos = out.find("mar")
    feb_pos = out.find("feb")
    assert apr_pos < mar_pos
    assert feb_pos == -1  # not in top 2
    assert "3 matches" in out


def test_search_only_bullet_lines(settings: Settings):
    _write_note(
        settings.vault_root,
        date(2026, 4, 1),
        "Some prose containing apple\n- bullet about apple\nMore prose with apple",
    )
    out = search("apple", settings)
    # Only the bullet line should appear, not prose
    assert "- bullet about apple" in out
    assert "1 match" in out


def test_search_ignores_non_daily_files(settings: Settings):
    other = settings.vault_root / "03 Timestamps" / "Index.md"
    other.parent.mkdir(parents=True, exist_ok=True)
    other.write_text("- random index bullet about widget\n", encoding="utf-8")
    out = search("widget", settings)
    assert "no matches" in out
