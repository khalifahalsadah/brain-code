from __future__ import annotations

import re
from pathlib import Path

from .config import Settings
from .files import _atomic_write
from .templates import expand_entity_stub_template

UNKNOWN_RE = re.compile(
    r"<!--\s*unknown:\s*type=(?P<type>people|food)\s*,\s*name=(?P<name>[^>]+?)\s*-->",
)


def parse_unknown_flags(bullet: str) -> list[tuple[str, str]]:
    """Return list of (type, name) tuples from <!--unknown:...--> comments in the bullet."""
    return [(m.group("type"), m.group("name").strip()) for m in UNKNOWN_RE.finditer(bullet)]


def strip_unknown_flags(bullet: str) -> str:
    """Remove <!--unknown:...--> comments from the bullet."""
    return UNKNOWN_RE.sub("", bullet).rstrip()


def create_stub(settings: Settings, type_: str, name: str) -> Path | None:
    """Create a stub file for an unknown entity if it doesn't already exist.

    Returns the path of the created file, or None if it already existed or type
    is not auto-stubbable.
    """
    folder = _folder_for_type(settings, type_)
    template_path = _template_for_type(settings, type_)
    if folder is None or template_path is None:
        return None

    target = folder / f"{name}.md"
    if target.exists():
        return None

    template = template_path.read_text(encoding="utf-8")
    rendered = expand_entity_stub_template(template, name)
    target.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(target, rendered)
    return target


def _folder_for_type(settings: Settings, type_: str) -> Path | None:
    for f in settings.entity_folders:
        if f.name == "people" and type_ == "people":
            return f.path
        if f.name == "food" and type_ == "food":
            return f.path
    return None


def _template_for_type(settings: Settings, type_: str) -> Path | None:
    for f in settings.entity_folders:
        if f.name == "people" and type_ == "people":
            return f.stub_template
        if f.name == "food" and type_ == "food":
            return f.stub_template
    return None


def log_unmatched(settings: Settings, type_: str, name: str) -> None:
    """Append unmatched entity name to project-level unmatched.log."""
    settings.unmatched_log.parent.mkdir(parents=True, exist_ok=True)
    with settings.unmatched_log.open("a", encoding="utf-8") as f:
        f.write(f"{type_}\t{name}\n")
