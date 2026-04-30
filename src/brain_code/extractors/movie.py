from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from .. import omdb
from ..config import Settings
from ..files import _atomic_write

MOVIES_FOLDER = "01 Area/Tvs and Movies"


def ensure_file(
    raw_title: str, settings: Settings, kind_hint: str | None = None
) -> tuple[bool, str, dict | None]:
    """Look up via OMDB, create the file if absent. Returns (was_created, canonical_title, omdb_data).

    canonical_title is OMDB's official title when available, else raw_title verbatim.
    """
    omdb_data = omdb.lookup(raw_title, kind_hint=kind_hint)
    canonical = (omdb_data["title"] if omdb_data else raw_title).strip()
    if not canonical:
        return False, raw_title, omdb_data

    folder = settings.vault_root / MOVIES_FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    file_path = folder / f"{canonical}.md"
    if file_path.exists():
        return False, canonical, omdb_data

    _atomic_write(file_path, _render_new_file(canonical, omdb_data))
    return True, canonical, omdb_data


def append_watch(
    canonical_title: str,
    log: dict,
    settings: Settings,
    today: date,
    was_created: bool,
) -> str:
    file_path = settings.vault_root / MOVIES_FOLDER / f"{canonical_title}.md"
    if not file_path.exists():
        return ""

    _append_watch_block(file_path, format_watch(log, today))

    rating = log.get("rating")
    if rating is not None:
        _update_simple_frontmatter_field(file_path, "rating", str(rating))

    rating_str = f"rating {rating}/10" if rating is not None else "no rating"
    icon = "🆕" if was_created else "🎬"
    kind = "show" if (log.get("kind") == "tv") else "movie"
    return f"{icon} [[{canonical_title}]] {kind} watched ({rating_str})"


def format_watch(log: dict, today: date) -> str:
    lines: list[str] = [f"### {today.isoformat()}"]
    if (rating := log.get("rating")) is not None:
        lines.append(f"- Rating: {rating}/10")
    if (season := log.get("season")) is not None:
        lines.append(f"- Season: {season}")
    if (episode := log.get("episode")) is not None:
        lines.append(f"- Episode: {episode}")
    if notes := (log.get("notes") or "").strip():
        lines.append(f"- {notes}")
    return "\n".join(lines)


def _render_new_file(title: str, omdb_data: dict | None) -> str:
    if omdb_data is None:
        # Minimal stub when OMDB lookup fails or no API key
        return (
            "---\n"
            'category: "[[Movies]]"\n'
            "tags:\n"
            "  - movies\n"
            "  - watched\n"
            "rating:\n"
            "---\n"
            f"# [[{title}]]\n"
            "\n"
            "## Watches\n"
        )

    is_tv = omdb_data["type"] == "series"
    category = "[[TV Shows]]" if is_tv else "[[Movies]]"
    type_tag = "tv-shows" if is_tv else "movies"

    lines: list[str] = ["---", f'category: "{category}"']
    if omdb_data["poster"]:
        lines.append(f'poster: "{omdb_data["poster"]}"')
    if omdb_data["imdb_id"]:
        lines.append(f'imdbId: "{omdb_data["imdb_id"]}"')
    if omdb_data["imdb_rating"]:
        lines.append(f'scoreImdb: "{omdb_data["imdb_rating"]}"')
    if omdb_data["runtime"]:
        lines.append(f'length: "{omdb_data["runtime"]}"')
    if omdb_data["directors"]:
        lines.append("director:")
        for d in omdb_data["directors"]:
            lines.append(f'  - "[[{d}]]"')
    if omdb_data["genres"]:
        lines.append("genre:")
        for g in omdb_data["genres"]:
            lines.append(f'  - "[[{g}]]"')
    if omdb_data["year"] is not None:
        lines.append(f"year: {omdb_data['year']}")
    if omdb_data["actors"]:
        lines.append("cast:")
        for a in omdb_data["actors"]:
            lines.append(f'  - "[[{a}]]"')
    if omdb_data["plot"]:
        plot = omdb_data["plot"].replace('"', "'")
        lines.append(f'plot: "{plot}"')
    lines.append("tags:")
    lines.append(f"  - {type_tag}")
    lines.append("  - watched")
    lines.append("rating:")
    lines.append("---")
    lines.append(f"# [[{title}]]")
    lines.append("")
    lines.append("## Watches")
    return "\n".join(lines) + "\n"


def _append_watch_block(file_path: Path, watch_block: str) -> None:
    content = file_path.read_text(encoding="utf-8")
    if "## Watches" not in content:
        content = content.rstrip() + "\n\n## Watches\n"
    new_content = content.rstrip() + "\n\n" + watch_block + "\n"
    _atomic_write(file_path, new_content)


_FRONTMATTER_FIELD_RE_CACHE: dict[str, re.Pattern[str]] = {}


def _update_simple_frontmatter_field(file_path: Path, key: str, value: str) -> None:
    """Update the first 'key: ...' line in the file's frontmatter."""
    content = file_path.read_text(encoding="utf-8")
    if not content.startswith("---\n"):
        return
    end = content.find("\n---\n", 4)
    if end == -1:
        return
    fm = content[4:end]
    pattern = _FRONTMATTER_FIELD_RE_CACHE.get(key)
    if pattern is None:
        pattern = re.compile(rf"^({re.escape(key)}:)\s*[^\n]*$", re.MULTILINE)
        _FRONTMATTER_FIELD_RE_CACHE[key] = pattern
    new_fm, n = pattern.subn(rf"\g<1> {value}", fm, count=1)
    if n == 0:
        return
    _atomic_write(file_path, content[:4] + new_fm + content[end:])
