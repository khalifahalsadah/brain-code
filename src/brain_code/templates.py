from __future__ import annotations

import re
from datetime import date, timedelta

from .config import AUTO_REGION_CLOSE, AUTO_REGION_OPEN, NOTES_HEADING


def _shift(d: date, days: int) -> date:
    return d + timedelta(days=days)


def expand_daily_template(template: str, target: date) -> str:
    """Expand all Templater placeholders in Template, Daily Note.md for target date."""
    out = template

    # <% tp.file.creation_date() %>  →  YYYY-MM-DD
    out = re.sub(
        r"<%\s*tp\.file\.creation_date\(\)\s*%>",
        target.strftime("%Y-%m-%d"),
        out,
    )

    # <% moment(tp.file.title,'YYYY-MM-DD').format("dddd, MMMM DD, YYYY") %>
    out = re.sub(
        r"<%\s*moment\(tp\.file\.title\s*,\s*['\"]YYYY-MM-DD['\"]\)\.format\(['\"]dddd, MMMM DD, YYYY['\"]\)\s*%>",
        target.strftime("%A, %B %d, %Y"),
        out,
    )

    # <% tp.date.now("YYYY", N) %>, ("MM-MMMM", N), ("YYYY-MM-DD-dddd", N)
    def _date_now(match: re.Match[str]) -> str:
        fmt = match.group(1)
        offset = int(match.group(2))
        d = _shift(target, offset)
        return _format_moment(d, fmt)

    out = re.sub(
        r"<%\s*tp\.date\.now\(['\"]([^'\"]+)['\"]\s*,\s*(-?\d+)\)\s*%>",
        _date_now,
        out,
    )

    # <%tp.date.now("YYYY-MM-DD")%>  (no offset, used inside dataview blocks)
    def _date_now_no_offset(match: re.Match[str]) -> str:
        return _format_moment(target, match.group(1))

    out = re.sub(
        r"<%\s*tp\.date\.now\(['\"]([^'\"]+)['\"]\)\s*%>",
        _date_now_no_offset,
        out,
    )

    # <% tp.file.title %>  →  basename (e.g., 2026-04-30-Thursday)
    out = re.sub(
        r"<%\s*tp\.file\.title\s*%>",
        target.strftime("%Y-%m-%d-%A"),
        out,
    )

    return out


def expand_entity_stub_template(template: str, name: str) -> str:
    """Expand placeholders in Template, People.md / Template, Food.md for a new stub."""
    out = template

    # Drop `<% await tp.file.move(...) %>` line entirely (we write to final path directly)
    out = re.sub(
        r"^.*<%\s*await\s+tp\.file\.move\([^)]*\)\s*%>.*\n?",
        "",
        out,
        flags=re.MULTILINE,
    )

    # <% tp.file.title %>  →  the entity name
    out = re.sub(r"<%\s*tp\.file\.title\s*%>", name, out)

    return out


def inject_auto_region_markers(content: str) -> str:
    """Ensure <!-- auto-region --> ... <!-- /auto-region --> exists right after # 📝 Notes.

    No-op if markers already present anywhere in the document.
    """
    if AUTO_REGION_OPEN in content and AUTO_REGION_CLOSE in content:
        return content

    pattern = re.compile(rf"^{re.escape(NOTES_HEADING)}\s*$", re.MULTILINE)
    match = pattern.search(content)
    if not match:
        return content

    insertion = f"\n{AUTO_REGION_OPEN}\n{AUTO_REGION_CLOSE}\n"
    end = match.end()
    return content[:end] + insertion + content[end:]


def _format_moment(d: date, moment_fmt: str) -> str:
    """Convert moment.js-style format tokens to strftime output for the given date."""
    # Order matters: longer tokens first to avoid partial matches.
    tokens = [
        ("YYYY", d.strftime("%Y")),
        ("MMMM", d.strftime("%B")),
        ("dddd", d.strftime("%A")),
        ("MM", d.strftime("%m")),
        ("DD", d.strftime("%d")),
    ]
    out = moment_fmt
    placeholders: dict[str, str] = {}
    for i, (token, value) in enumerate(tokens):
        sentinel = f"\x00{i}\x00"
        out = out.replace(token, sentinel)
        placeholders[sentinel] = value
    for sentinel, value in placeholders.items():
        out = out.replace(sentinel, value)
    return out
