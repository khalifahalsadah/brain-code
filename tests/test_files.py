from datetime import date
from pathlib import Path

import pytest

from brain_code.config import Settings
from brain_code.files import (
    append_to_auto_region,
    daily_note_path,
    ensure_daily_note,
    pop_last_bullet,
    read_auto_region,
    replace_auto_region,
)

DAILY_TEMPLATE = """---
created: <% tp.file.creation_date() %>
tags:
  - daily
---
tags:: [[+Daily Notes]]

# <% moment(tp.file.title,'YYYY-MM-DD').format("dddd, MMMM DD, YYYY") %>

<< [[03 Timestamps/<% tp.date.now("YYYY", -1) %>/<% tp.date.now("MM-MMMM", -1) %>/<% tp.date.now("YYYY-MM-DD-dddd", -1) %>|Yesterday]] | [[03 Timestamps/<% tp.date.now("YYYY", 1) %>/<% tp.date.now("MM-MMMM", 1) %>/<% tp.date.now("YYYY-MM-DD-dddd", 1) %>|Tomorrow]] >>

---
# 📝 Notes

# Today Media
- ld
"""


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    vault = tmp_path / "vault"
    template_path = vault / "Extras/Templates/Template, Daily Note.md"
    template_path.parent.mkdir(parents=True)
    template_path.write_text(DAILY_TEMPLATE, encoding="utf-8")
    return Settings(
        vault_root=vault,
        project_root=tmp_path / "project",
        api_key=None,
    )


def test_ensure_daily_note_creates_file(settings: Settings):
    target = date(2026, 4, 30)
    path = ensure_daily_note(settings, target)
    assert path.exists()
    assert path == daily_note_path(settings, target)
    expected_rel = "03 Timestamps/2026/04-April/2026-04-30-Thursday.md"
    assert str(path).endswith(expected_rel)


def test_ensure_daily_note_idempotent(settings: Settings):
    target = date(2026, 4, 30)
    path = ensure_daily_note(settings, target)
    path.write_text(path.read_text() + "\nUSER ADDITION\n")
    same = ensure_daily_note(settings, target)
    assert same == path
    assert "USER ADDITION" in path.read_text()


def test_ensure_daily_note_injects_markers(settings: Settings):
    path = ensure_daily_note(settings, date(2026, 4, 30))
    content = path.read_text()
    assert "<!-- auto-region -->" in content
    assert "<!-- /auto-region -->" in content
    assert content.index("<!-- auto-region -->") > content.index("# 📝 Notes")


def test_append_creates_markers_if_missing(settings: Settings):
    path = settings.vault_root / "test.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# 📝 Notes\n\n# Today Media\n", encoding="utf-8")
    append_to_auto_region(path, "- مرحبا")
    content = path.read_text()
    assert "<!-- auto-region -->" in content
    assert "- مرحبا\n<!-- /auto-region -->" in content


def test_append_inserts_before_close_marker(settings: Settings):
    path = settings.vault_root / "test.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# 📝 Notes\n<!-- auto-region -->\n- existing\n<!-- /auto-region -->\n",
        encoding="utf-8",
    )
    append_to_auto_region(path, "- جديد")
    content = path.read_text()
    assert content.index("- existing") < content.index("- جديد")
    assert content.index("- جديد") < content.index("<!-- /auto-region -->")


def test_append_strips_trailing_newlines_on_input(settings: Settings):
    path = settings.vault_root / "test.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# 📝 Notes\n<!-- auto-region -->\n<!-- /auto-region -->\n",
        encoding="utf-8",
    )
    append_to_auto_region(path, "- test\n\n\n")
    content = path.read_text()
    # Exactly one bullet line, no extra blanks
    assert "- test\n<!-- /auto-region -->" in content


def test_read_auto_region_returns_inner(settings: Settings):
    path = settings.vault_root / "test.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "preamble\n<!-- auto-region -->\n- one\n- two\n<!-- /auto-region -->\nepilogue\n",
        encoding="utf-8",
    )
    inner = read_auto_region(path)
    assert inner == "- one\n- two\n"


def test_read_auto_region_empty_when_no_markers(settings: Settings):
    path = settings.vault_root / "test.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("nothing here", encoding="utf-8")
    assert read_auto_region(path) == ""


def test_replace_auto_region_preserves_outside(settings: Settings):
    path = settings.vault_root / "test.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "BEFORE\n<!-- auto-region -->\n- raw\n<!-- /auto-region -->\nAFTER\n",
        encoding="utf-8",
    )
    replace_auto_region(path, "- polished one\n- polished two")
    content = path.read_text()
    assert "BEFORE\n" in content
    assert "AFTER\n" in content
    assert "- raw" not in content
    assert "- polished one" in content
    assert "- polished two" in content
    assert "<!-- auto-region -->" in content
    assert "<!-- /auto-region -->" in content


def test_pop_last_bullet_single(settings: Settings):
    path = settings.vault_root / "test.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# 📝 Notes\n<!-- auto-region -->\n- one\n- two\n<!-- /auto-region -->\n",
        encoding="utf-8",
    )
    removed = pop_last_bullet(path)
    assert removed == "- two"
    content = path.read_text(encoding="utf-8")
    assert "- one" in content
    assert "- two" not in content


def test_pop_last_bullet_with_nested(settings: Settings):
    path = settings.vault_root / "test.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# 📝 Notes\n<!-- auto-region -->\n- parent\n\t- child A\n\t- child B\n<!-- /auto-region -->\n",
        encoding="utf-8",
    )
    removed = pop_last_bullet(path)
    assert "- parent" in removed
    assert "child A" in removed
    assert "child B" in removed
    content = path.read_text(encoding="utf-8")
    assert "parent" not in content
    assert "child A" not in content


def test_pop_last_bullet_keeps_earlier_bullets(settings: Settings):
    path = settings.vault_root / "test.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# 📝 Notes\n<!-- auto-region -->\n- first\n- middle\n\t- nested\n- last\n<!-- /auto-region -->\n",
        encoding="utf-8",
    )
    removed = pop_last_bullet(path)
    assert removed == "- last"
    content = path.read_text(encoding="utf-8")
    assert "- first" in content
    assert "- middle" in content
    assert "\t- nested" in content
    assert "- last" not in content


def test_pop_last_bullet_empty_region(settings: Settings):
    path = settings.vault_root / "test.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# 📝 Notes\n<!-- auto-region -->\n<!-- /auto-region -->\n",
        encoding="utf-8",
    )
    assert pop_last_bullet(path) is None


def test_replace_auto_region_raises_without_markers(settings: Settings):
    path = settings.vault_root / "test.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("no markers", encoding="utf-8")
    with pytest.raises(ValueError):
        replace_auto_region(path, "anything")
