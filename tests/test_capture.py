from datetime import date
from pathlib import Path

import pytest

from brain_code.capture import capture
from brain_code.config import Settings

DAILY_TEMPLATE = """---
created: <% tp.file.creation_date() %>
tags:
  - daily
---
tags:: [[+Daily Notes]]

# <% moment(tp.file.title,'YYYY-MM-DD').format("dddd, MMMM DD, YYYY") %>

---
# 📝 Notes

# Today Media
"""

FOOD_TEMPLATE = """---
tags:
  - Restaurant
---
# [[<% tp.file.title %>]]
<% await tp.file.move("/01 Area/Food/" + tp.file.title) %>

## Notes
-
"""

PEOPLE_TEMPLATE = """---
aliases:
---
tags:: [[People MOC]]

# [[<% tp.file.title %>]]
<% await tp.file.move("/Extras/People/" + tp.file.title) %>

## Notes
-
"""


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    vault = tmp_path / "vault"
    (vault / "Extras/People").mkdir(parents=True)
    (vault / "01 Area/Food").mkdir(parents=True)
    (vault / "Extras/Templates").mkdir(parents=True)
    (vault / "Extras/Templates/Template, Daily Note.md").write_text(
        DAILY_TEMPLATE, encoding="utf-8"
    )
    (vault / "Extras/Templates/Template, Food.md").write_text(
        FOOD_TEMPLATE, encoding="utf-8"
    )
    (vault / "Extras/Templates/Template, People.md").write_text(
        PEOPLE_TEMPLATE, encoding="utf-8"
    )
    return Settings(
        vault_root=vault,
        project_root=tmp_path / "project",
        api_key="test-key",
    )


def test_capture_appends_bullet_and_logs_restaurant(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
):
    today = date(2026, 4, 30)
    monkeypatch.setattr("brain_code.capture.target_date_for_append", lambda: today)
    monkeypatch.setattr(
        "brain_code.capture.append_pass",
        lambda *a, **kw: "- جربت [[كرم]] برجر 7/10",
    )
    monkeypatch.setattr(
        "brain_code.capture.extract_logs",
        lambda *a, **kw: [
            {
                "type": "restaurant_visit",
                "entity": "كرم",
                "items": [{"name": "Burger", "rating": 7}, {"name": "Fries", "rating": 10}],
                "overall": 7,
            }
        ],
    )

    result = capture("ordered from كرم. burger 7/10 fries 10/10 overall 7", settings)

    daily = settings.vault_root / "03 Timestamps/2026/04-April/2026-04-30-Thursday.md"
    assert daily.exists()
    daily_content = daily.read_text(encoding="utf-8")
    assert "- جربت [[كرم]] برجر 7/10" in daily_content

    food = settings.vault_root / "01 Area/Food/كرم.md"
    assert food.exists()
    food_content = food.read_text(encoding="utf-8")
    assert "## Visits" in food_content
    assert "### 2026-04-30" in food_content
    assert "- Burger — 7/10" in food_content
    assert "- Fries — 10/10" in food_content
    assert "**Overall: 7/10**" in food_content

    rendered = result.render()
    assert "- جربت [[كرم]] برجر 7/10" in rendered
    assert "🆕" in rendered or "🍽" in rendered
    assert "كرم" in rendered


def test_capture_no_side_effects_when_logs_empty(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
):
    today = date(2026, 4, 30)
    monkeypatch.setattr("brain_code.capture.target_date_for_append", lambda: today)
    monkeypatch.setattr(
        "brain_code.capture.append_pass",
        lambda *a, **kw: "- went to the beach today",
    )
    monkeypatch.setattr("brain_code.capture.extract_logs", lambda *a, **kw: [])

    result = capture("went to the beach today", settings)

    assert result.side_effects == []
    assert "- went to the beach today" in result.bullet
    food_dir = settings.vault_root / "01 Area/Food"
    assert list(food_dir.iterdir()) == []


def test_capture_multiple_restaurant_visits(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
):
    today = date(2026, 4, 30)
    monkeypatch.setattr("brain_code.capture.target_date_for_append", lambda: today)
    monkeypatch.setattr(
        "brain_code.capture.append_pass",
        lambda *a, **kw: "- went to A then B",
    )
    monkeypatch.setattr(
        "brain_code.capture.extract_logs",
        lambda *a, **kw: [
            {"type": "restaurant_visit", "entity": "A", "overall": 8},
            {"type": "restaurant_visit", "entity": "B", "overall": 5},
        ],
    )
    result = capture("went to A then B", settings)
    assert (settings.vault_root / "01 Area/Food/A.md").exists()
    assert (settings.vault_root / "01 Area/Food/B.md").exists()
    assert len(result.side_effects) == 2


def test_capture_unknown_log_type_ignored(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
):
    today = date(2026, 4, 30)
    monkeypatch.setattr("brain_code.capture.target_date_for_append", lambda: today)
    monkeypatch.setattr("brain_code.capture.append_pass", lambda *a, **kw: "- bullet")
    monkeypatch.setattr(
        "brain_code.capture.extract_logs",
        lambda *a, **kw: [{"type": "future_type_we_dont_handle", "entity": "X"}],
    )
    result = capture("something", settings)
    assert result.side_effects == []
