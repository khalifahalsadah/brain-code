from datetime import date

from brain_code.templates import (
    expand_daily_template,
    expand_entity_stub_template,
    inject_auto_region_markers,
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

----
### Notes created today
```dataview
List FROM "" WHERE file.cday = date("<%tp.date.now("YYYY-MM-DD")%>") SORT file.ctime asc
```
"""


def test_daily_template_creation_date():
    out = expand_daily_template(DAILY_TEMPLATE, date(2026, 4, 30))
    assert "created: 2026-04-30" in out


def test_daily_template_title_formatted():
    out = expand_daily_template(DAILY_TEMPLATE, date(2026, 4, 30))
    assert "# Thursday, April 30, 2026" in out


def test_daily_template_yesterday_link():
    out = expand_daily_template(DAILY_TEMPLATE, date(2026, 4, 30))
    assert "[[03 Timestamps/2026/04-April/2026-04-29-Wednesday|Yesterday]]" in out


def test_daily_template_tomorrow_link():
    out = expand_daily_template(DAILY_TEMPLATE, date(2026, 4, 30))
    assert "[[03 Timestamps/2026/05-May/2026-05-01-Friday|Tomorrow]]" in out


def test_daily_template_yesterday_year_rollover():
    out = expand_daily_template(DAILY_TEMPLATE, date(2026, 1, 1))
    assert "[[03 Timestamps/2025/12-December/2025-12-31-Wednesday|Yesterday]]" in out


def test_daily_template_tomorrow_year_rollover():
    out = expand_daily_template(DAILY_TEMPLATE, date(2025, 12, 31))
    assert "[[03 Timestamps/2026/01-January/2026-01-01-Thursday|Tomorrow]]" in out


def test_daily_template_dataview_uses_today_iso():
    out = expand_daily_template(DAILY_TEMPLATE, date(2026, 4, 30))
    assert 'date("2026-04-30")' in out


def test_daily_template_no_remaining_placeholders():
    out = expand_daily_template(DAILY_TEMPLATE, date(2026, 4, 30))
    assert "<%" not in out
    assert "%>" not in out


PEOPLE_TEMPLATE = """---
company:
location:
title:
email:
website:
aliases:
---
tags:: [[People MOC]]

# [[<% tp.file.title %>]]
<% await tp.file.move("/Extras/People/" + tp.file.title) %>

## Notes
-

## Meetings
"""


def test_people_template_substitutes_name():
    out = expand_entity_stub_template(PEOPLE_TEMPLATE, "روان")
    assert "# [[روان]]" in out


def test_people_template_drops_move_line():
    out = expand_entity_stub_template(PEOPLE_TEMPLATE, "روان")
    assert "tp.file.move" not in out
    assert "<%" not in out


def test_people_template_preserves_structure():
    out = expand_entity_stub_template(PEOPLE_TEMPLATE, "Ahmed")
    assert "tags:: [[People MOC]]" in out
    assert "## Notes" in out
    assert "## Meetings" in out


FOOD_TEMPLATE = """---
tags:
  - Restaurant
  - Cafe
location:
rating: ⭐️⭐️⭐️⭐️⭐️
---
# [[<% tp.file.title %>]]
<% await tp.file.move("/01 Area/Food/" + tp.file.title) %>

## Notes
-
"""


def test_food_template_substitutes_name():
    out = expand_entity_stub_template(FOOD_TEMPLATE, "كرم")
    assert "# [[كرم]]" in out
    assert "tp.file.move" not in out


def test_inject_markers_when_absent():
    content = "tags:: [[+Daily Notes]]\n\n# Thursday\n\n# 📝 Notes\n\n# Today Media\n- foo\n"
    out = inject_auto_region_markers(content)
    assert "<!-- auto-region -->\n<!-- /auto-region -->" in out
    assert out.index("<!-- auto-region -->") > out.index("# 📝 Notes")
    assert out.index("<!-- auto-region -->") < out.index("# Today Media")


def test_inject_markers_idempotent():
    content = "# 📝 Notes\n<!-- auto-region -->\n- foo\n<!-- /auto-region -->\n"
    out = inject_auto_region_markers(content)
    assert out == content


def test_inject_markers_no_notes_heading():
    content = "no heading here"
    out = inject_auto_region_markers(content)
    assert out == content
