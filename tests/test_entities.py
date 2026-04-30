from pathlib import Path

import pytest

from brain_code.config import Settings
from brain_code.entities import _parse_aliases, load_registry


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    v = tmp_path / "vault"
    (v / "Extras/People").mkdir(parents=True)
    (v / "01 Area/Food").mkdir(parents=True)
    (v / "01 Area/Tvs and Movies").mkdir(parents=True)
    (v / "01 Area/Work").mkdir(parents=True)

    # People — mix of empty aliases, scalar alias, list alias
    (v / "Extras/People/روان.md").write_text(
        "---\naliases: \n---\n# روان\n", encoding="utf-8"
    )
    (v / "Extras/People/يويو.md").write_text(
        "---\naliases: yoyo\nbirthday: 2025-07-07\n---\n# يويو\n",
        encoding="utf-8",
    )
    (v / "Extras/People/Ahmed Zaki.md").write_text(
        "---\naliases:\n  - أحمد\n  - Ahmed\n---\n# Ahmed Zaki\n",
        encoding="utf-8",
    )
    (v / "Extras/People/.hidden.md").write_text("ignored", encoding="utf-8")

    # Food
    (v / "01 Area/Food/قهوة عمق و برجر.md").write_text("entity", encoding="utf-8")
    (v / "01 Area/Food/Cassette.md").write_text("entity", encoding="utf-8")

    # Movies + show subfolders
    (v / "01 Area/Tvs and Movies/Inception.md").write_text("movie", encoding="utf-8")
    (v / "01 Area/Tvs and Movies/Ludwig.md").write_text("show index", encoding="utf-8")
    (v / "01 Area/Tvs and Movies/Andor").mkdir()  # folder-only show
    (v / "01 Area/Tvs and Movies/Ludwig").mkdir()  # folder for show with index file

    # Work projects (subdirs only)
    (v / "01 Area/Work/Mala").mkdir()
    (v / "01 Area/Work/WTD").mkdir()
    (v / "01 Area/Work/SomeFile.md").write_text("not a project", encoding="utf-8")

    return v


@pytest.fixture
def settings(vault: Path, tmp_path: Path) -> Settings:
    return Settings(
        vault_root=vault,
        project_root=tmp_path / "project",
        api_key=None,
    )


def test_load_registry_includes_all_types(settings: Settings):
    registry = load_registry(settings)
    types = {e.type for e in registry}
    assert types == {"people", "food", "movies_tv", "work_projects"}


def test_load_registry_people_count(settings: Settings):
    registry = load_registry(settings)
    people = [e for e in registry if e.type == "people"]
    names = {e.name for e in people}
    assert names == {"روان", "يويو", "Ahmed Zaki"}


def test_load_registry_aliases_parsed(settings: Settings):
    registry = load_registry(settings)
    by_name = {e.name: e for e in registry if e.type == "people"}
    assert by_name["روان"].aliases == ()
    assert by_name["يويو"].aliases == ("yoyo",)
    assert by_name["Ahmed Zaki"].aliases == ("أحمد", "Ahmed")


def test_load_registry_food(settings: Settings):
    registry = load_registry(settings)
    food = [e.name for e in registry if e.type == "food"]
    assert set(food) == {"قهوة عمق و برجر", "Cassette"}


def test_load_registry_movies_tv_includes_files_and_dirs(settings: Settings):
    registry = load_registry(settings)
    movies = [e for e in registry if e.type == "movies_tv"]
    by_name = {e.name: e for e in movies}
    # Top-level file
    assert "Inception" in by_name
    assert by_name["Inception"].is_dir is False
    # Show that has both file and dir → file wins, dir not duplicated
    assert "Ludwig" in by_name
    assert by_name["Ludwig"].is_dir is False
    # Show with only dir
    assert "Andor" in by_name
    assert by_name["Andor"].is_dir is True
    # No duplicates
    assert len(movies) == len({e.name for e in movies})


def test_load_registry_work_projects_only_subdirs(settings: Settings):
    registry = load_registry(settings)
    projects = [e for e in registry if e.type == "work_projects"]
    names = {e.name for e in projects}
    assert names == {"Mala", "WTD"}
    assert all(e.is_dir for e in projects)


def test_all_names_includes_aliases():
    from brain_code.entities import Entity

    e = Entity(
        name="Ahmed Zaki",
        type="people",
        path=Path("/tmp/x.md"),
        is_dir=False,
        aliases=("Ahmed", "أحمد"),
    )
    assert e.all_names == ("Ahmed Zaki", "Ahmed", "أحمد")


def test_parse_aliases_empty_field():
    assert _parse_aliases("---\naliases: \n---\n") == ()


def test_parse_aliases_scalar():
    assert _parse_aliases("---\naliases: yoyo\n---\n") == ("yoyo",)


def test_parse_aliases_inline_list():
    assert _parse_aliases('---\naliases: [foo, "bar"]\n---\n') == ("foo", "bar")


def test_parse_aliases_block_list():
    out = _parse_aliases("---\naliases:\n  - first\n  - second\n  - 'third'\n---\n")
    assert out == ("first", "second", "third")


def test_parse_aliases_no_frontmatter():
    assert _parse_aliases("# just content") == ()


def test_parse_aliases_no_aliases_key():
    assert _parse_aliases("---\nfoo: bar\n---\n") == ()
