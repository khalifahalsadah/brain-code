from pathlib import Path

import pytest

from brain_code.config import Settings
from brain_code.stubs import (
    create_stub,
    log_unmatched,
    parse_unknown_flags,
    strip_unknown_flags,
)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    vault = tmp_path / "vault"
    (vault / "Extras/People").mkdir(parents=True)
    (vault / "01 Area/Food").mkdir(parents=True)
    (vault / "Extras/Templates").mkdir(parents=True)
    (vault / "Extras/Templates/Template, People.md").write_text(
        "---\naliases:\n---\ntags:: [[People MOC]]\n\n# [[<% tp.file.title %>]]\n<% await tp.file.move(\"/Extras/People/\" + tp.file.title) %>\n",
        encoding="utf-8",
    )
    (vault / "Extras/Templates/Template, Food.md").write_text(
        "---\nrating:\n---\n# [[<% tp.file.title %>]]\n<% await tp.file.move(\"/01 Area/Food/\" + tp.file.title) %>\n",
        encoding="utf-8",
    )
    return Settings(
        vault_root=vault,
        project_root=tmp_path / "project",
        api_key=None,
    )


def test_parse_unknown_flags_single():
    flags = parse_unknown_flags("- met <!--unknown:type=people,name=أحمد--> today")
    assert flags == [("people", "أحمد")]


def test_parse_unknown_flags_multiple():
    bullet = (
        "- went with <!--unknown:type=people,name=Sara--> to "
        "<!--unknown:type=food,name=NewCafe-->"
    )
    flags = parse_unknown_flags(bullet)
    assert flags == [("people", "Sara"), ("food", "NewCafe")]


def test_parse_unknown_flags_none():
    assert parse_unknown_flags("- nothing flagged") == []


def test_strip_unknown_flags():
    out = strip_unknown_flags("- met [[X]] <!--unknown:type=people,name=X-->")
    assert out == "- met [[X]]"


def test_create_stub_people(settings: Settings):
    path = create_stub(settings, "people", "أحمد التميمي")
    assert path is not None
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "# [[أحمد التميمي]]" in content
    assert "tp.file.move" not in content


def test_create_stub_food(settings: Settings):
    path = create_stub(settings, "food", "كرم")
    assert path is not None
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "# [[كرم]]" in content


def test_create_stub_returns_none_if_exists(settings: Settings):
    create_stub(settings, "people", "Existing")
    second = create_stub(settings, "people", "Existing")
    assert second is None


def test_create_stub_unknown_type(settings: Settings):
    assert create_stub(settings, "movies_tv", "Inception") is None


def test_log_unmatched_appends(settings: Settings):
    log_unmatched(settings, "movies_tv", "Inception")
    log_unmatched(settings, "movies_tv", "Andor")
    content = settings.unmatched_log.read_text(encoding="utf-8")
    assert "movies_tv\tInception" in content
    assert "movies_tv\tAndor" in content
