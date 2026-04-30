from pathlib import Path

import pytest

from brain_code.entities import Entity
from brain_code.wikilinks import gather_context, list_known_names, match_entities


@pytest.fixture
def people(tmp_path: Path) -> list[Entity]:
    rawan = tmp_path / "روان.md"
    rawan.write_text("# روان\n\n## Notes\n- بنت\n", encoding="utf-8")
    yoyo = tmp_path / "يويو.md"
    yoyo.write_text("# يويو\n\n## Notes\n- بنتي\n", encoding="utf-8")
    ahmed = tmp_path / "Ahmed Zaki.md"
    ahmed.write_text("# Ahmed Zaki\n", encoding="utf-8")
    return [
        Entity(name="روان", type="people", path=rawan, is_dir=False),
        Entity(name="يويو", type="people", path=yoyo, is_dir=False, aliases=("yoyo",)),
        Entity(
            name="Ahmed Zaki",
            type="people",
            path=ahmed,
            is_dir=False,
            aliases=("Ahmed",),
        ),
    ]


def test_match_arabic_name(people: list[Entity]):
    matched = match_entities("كنت مع روان في عمق", people)
    names = [e.name for e in matched]
    assert "روان" in names


def test_match_alias_case_insensitive(people: list[Entity]):
    matched = match_entities("yoyo went to bed", people)
    names = [e.name for e in matched]
    assert "يويو" in names


def test_match_full_name_case_insensitive(people: list[Entity]):
    matched = match_entities("ahmed zaki was there", people)
    names = [e.name for e in matched]
    assert "Ahmed Zaki" in names


def test_no_match_returns_empty(people: list[Entity]):
    assert match_entities("random text", people) == []


def test_match_dedupes_overlapping_names(people: list[Entity]):
    # "Ahmed" matches both via alias and full name "Ahmed Zaki"
    matched = match_entities("Ahmed went home", people)
    assert len([e for e in matched if e.name == "Ahmed Zaki"]) == 1


def test_gather_context_includes_file_content(people: list[Entity]):
    matched = match_entities("yoyo went to bed", people)
    ctx = gather_context(matched)
    assert "people: يويو" in ctx
    assert "بنتي" in ctx


def test_gather_context_handles_dir_entity(tmp_path: Path):
    proj_dir = tmp_path / "WTD"
    proj_dir.mkdir()
    e = Entity(name="WTD", type="work_projects", path=proj_dir, is_dir=True)
    ctx = gather_context([e])
    assert "known link targets" in ctx
    assert "WTD" in ctx


def test_list_known_names_groups_by_type(people: list[Entity]):
    out = list_known_names(people)
    assert "## people" in out
    assert "روان" in out
    assert "yoyo (alias of يويو)" in out
