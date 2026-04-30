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


def test_ensure_file_creates_new(settings: Settings):
    created = restaurant.ensure_file("كرم", settings)
    assert created is True
    file_path = settings.vault_root / "01 Area/Food/كرم.md"
    assert file_path.exists()
    content = file_path.read_text(encoding="utf-8")
    assert "# [[كرم]]" in content


def test_ensure_file_idempotent(settings: Settings):
    restaurant.ensure_file("كرم", settings)
    second = restaurant.ensure_file("كرم", settings)
    assert second is False


def test_append_visit_to_freshly_created_file(settings: Settings):
    restaurant.ensure_file("كرم", settings)
    log = {
        "type": "restaurant_visit",
        "entity": "كرم",
        "items": [{"name": "برجر", "rating": 7}, {"name": "فرايز", "rating": 10}],
        "overall": 6,
    }
    msg = restaurant.append_visit("كرم", log, settings, date(2026, 4, 30), was_created=True)
    file_path = settings.vault_root / "01 Area/Food/كرم.md"
    content = file_path.read_text(encoding="utf-8")
    assert "## Visits" in content
    assert "### 2026-04-30" in content
    assert "- برجر — 7/10" in content
    assert "- فرايز — 10/10" in content
    assert "**Overall: 6/10**" in content
    assert "🆕" in msg
    assert "overall 6/10" in msg


def test_append_visit_to_existing_file_preserves_history(settings: Settings):
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
    msg = restaurant.append_visit("كرم", log, settings, date(2026, 4, 30), was_created=False)
    content = file_path.read_text(encoding="utf-8")
    assert "### 2026-04-29" in content
    assert "soup — 5/10" in content
    assert "### 2026-04-30" in content
    assert "burger — 8/10" in content
    assert "old notes" in content
    assert "🍽" in msg


def test_append_visit_creates_visits_section_if_missing(settings: Settings):
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
    restaurant.append_visit("Cassette", log, settings, date(2026, 4, 30), was_created=False)
    content = file_path.read_text(encoding="utf-8")
    assert "## Visits" in content
    assert "- Coffee — 9/10" in content


def test_append_visit_summary_with_only_item_rating(settings: Settings):
    """When user gives item ratings but no overall, summary should reflect that."""
    restaurant.ensure_file("لغاويص", settings)
    log = {
        "type": "restaurant_visit",
        "entity": "لغاويص",
        "items": [{"name": "شاورما كيتو", "rating": 10}],
    }
    msg = restaurant.append_visit("لغاويص", log, settings, date(2026, 4, 30), was_created=True)
    assert "1 item rated" in msg
    assert "no rating" not in msg


def test_append_visit_no_ratings_no_overall(settings: Settings):
    restaurant.ensure_file("FoodSpot", settings)
    log = {
        "type": "restaurant_visit",
        "entity": "FoodSpot",
        "items": [{"name": "Wrap"}, {"name": "Soda"}],
    }
    msg = restaurant.append_visit("FoodSpot", log, settings, date(2026, 4, 30), was_created=True)
    assert "2 items logged" in msg


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
