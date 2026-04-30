from datetime import date
from pathlib import Path

import pytest

from brain_code.config import Settings
from brain_code.extractors import restaurant


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    vault = tmp_path / "vault"
    (vault / "01 Area/Food").mkdir(parents=True)
    (vault / "Extras/Templates").mkdir(parents=True)
    (vault / "Extras/Templates/Template, Food.md").write_text(
        "---\ntags:\n  - Restaurant\nrating:\n---\n# [[<% tp.file.title %>]]\n<% await tp.file.move(\"/01 Area/Food/\" + tp.file.title) %>\n\n## Notes\n- \n",
        encoding="utf-8",
    )
    return Settings(
        vault_root=vault,
        project_root=tmp_path / "project",
        api_key=None,
    )


def test_handle_creates_new_restaurant_file(settings: Settings):
    log = {
        "type": "restaurant_visit",
        "entity": "كرم",
        "items": [{"name": "برجر", "rating": 7}, {"name": "فرايز", "rating": 10}],
        "overall": 6,
    }
    msg = restaurant.handle(log, settings, date(2026, 4, 30))
    file_path = settings.vault_root / "01 Area/Food/كرم.md"
    assert file_path.exists()
    content = file_path.read_text(encoding="utf-8")
    assert "# [[كرم]]" in content
    assert "## Visits" in content
    assert "### 2026-04-30" in content
    assert "- برجر — 7/10" in content
    assert "- فرايز — 10/10" in content
    assert "**Overall: 6/10**" in content
    assert "🆕" in msg


def test_handle_appends_to_existing_file(settings: Settings):
    file_path = settings.vault_root / "01 Area/Food/كرم.md"
    file_path.write_text(
        "---\nrating: ⭐️⭐️⭐️\n---\n# [[كرم]]\n\n## Notes\n- old notes\n\n## Visits\n\n### 2026-04-29\n- soup — 5/10\n",
        encoding="utf-8",
    )
    log = {
        "type": "restaurant_visit",
        "entity": "كرم",
        "items": [{"name": "burger", "rating": 8}],
        "overall": 8,
    }
    msg = restaurant.handle(log, settings, date(2026, 4, 30))
    content = file_path.read_text(encoding="utf-8")
    # Old visit preserved
    assert "### 2026-04-29" in content
    assert "soup — 5/10" in content
    # New visit appended
    assert "### 2026-04-30" in content
    assert "burger — 8/10" in content
    # Notes preserved
    assert "old notes" in content
    assert "🍽" in msg


def test_handle_creates_visits_section_if_missing(settings: Settings):
    file_path = settings.vault_root / "01 Area/Food/Cassette.md"
    file_path.write_text(
        "---\n---\n# [[Cassette]]\n\n## Notes\n- old\n",
        encoding="utf-8",
    )
    log = {
        "type": "restaurant_visit",
        "entity": "Cassette",
        "items": [{"name": "Coffee", "rating": 9}],
    }
    restaurant.handle(log, settings, date(2026, 4, 30))
    content = file_path.read_text(encoding="utf-8")
    assert "## Visits" in content
    assert "### 2026-04-30" in content
    assert "- Coffee — 9/10" in content


def test_handle_skips_empty_entity(settings: Settings):
    log = {"type": "restaurant_visit", "entity": "  "}
    assert restaurant.handle(log, settings, date(2026, 4, 30)) == ""


def test_handle_no_overall_no_ratings(settings: Settings):
    log = {
        "type": "restaurant_visit",
        "entity": "FoodSpot",
        "items": [{"name": "Wrap"}, {"name": "Soda"}],
    }
    msg = restaurant.handle(log, settings, date(2026, 4, 30))
    file_path = settings.vault_root / "01 Area/Food/FoodSpot.md"
    content = file_path.read_text(encoding="utf-8")
    assert "- Wrap" in content
    assert "- Soda" in content
    assert "/10" not in content.split("## Visits")[1]
    assert "no rating" in msg


def test_format_visit_strips_empty_item_names():
    log = {
        "items": [
            {"name": "Pizza", "rating": 7},
            {"name": "  ", "rating": 9},
            {"name": "", "rating": 5},
        ],
        "overall": 7,
    }
    out = restaurant.format_visit(log, date(2026, 4, 30))
    assert "- Pizza — 7/10" in out
    assert out.count("- ") == 2  # Pizza + Overall, empty entries skipped
