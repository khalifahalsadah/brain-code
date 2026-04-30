from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .config import Settings


@dataclass(frozen=True)
class Entity:
    name: str
    type: str
    path: Path
    is_dir: bool
    aliases: tuple[str, ...] = field(default=())

    @property
    def all_names(self) -> tuple[str, ...]:
        return (self.name, *self.aliases)


def load_registry(settings: Settings) -> list[Entity]:
    """Scan all configured entity folders and return the registry."""
    out: list[Entity] = []
    for folder in settings.entity_folders:
        if not folder.path.exists():
            continue
        if folder.name == "people":
            out.extend(_load_people(folder.path))
        elif folder.name == "work_projects":
            out.extend(_load_subdirs_as_entities(folder.path, type_="work_projects"))
        elif folder.name == "movies_tv":
            out.extend(_load_files_and_subdirs(folder.path, type_="movies_tv"))
        else:
            out.extend(_load_files(folder.path, type_=folder.name))
    return out


def _load_files(folder: Path, type_: str) -> list[Entity]:
    return [
        Entity(name=p.stem, type=type_, path=p, is_dir=False)
        for p in sorted(folder.glob("*.md"))
        if not p.name.startswith(".")
    ]


def _load_subdirs_as_entities(folder: Path, type_: str) -> list[Entity]:
    return [
        Entity(name=p.name, type=type_, path=p, is_dir=True)
        for p in sorted(folder.iterdir())
        if p.is_dir() and not p.name.startswith(".")
    ]


def _load_files_and_subdirs(folder: Path, type_: str) -> list[Entity]:
    """Top-level .md files + subdirectory names (e.g. shows with episode subfolders)."""
    seen: set[str] = set()
    out: list[Entity] = []
    for p in sorted(folder.glob("*.md")):
        if p.name.startswith("."):
            continue
        out.append(Entity(name=p.stem, type=type_, path=p, is_dir=False))
        seen.add(p.stem)
    for p in sorted(folder.iterdir()):
        if not p.is_dir() or p.name.startswith("."):
            continue
        if p.name in seen:
            continue
        out.append(Entity(name=p.name, type=type_, path=p, is_dir=True))
    return out


def _load_people(folder: Path) -> list[Entity]:
    out: list[Entity] = []
    for p in sorted(folder.glob("*.md")):
        if p.name.startswith("."):
            continue
        try:
            content = p.read_text(encoding="utf-8")
        except OSError:
            continue
        aliases = _parse_aliases(content)
        out.append(
            Entity(
                name=p.stem,
                type="people",
                path=p,
                is_dir=False,
                aliases=aliases,
            )
        )
    return out


_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|$)", re.DOTALL)
_ALIASES_BLOCK_RE = re.compile(
    r"^aliases:[ \t]*(?P<inline>[^\n]*)(?P<rest>(?:\n[ \t]+-[^\n]*)*)",
    re.MULTILINE,
)


def _parse_aliases(content: str) -> tuple[str, ...]:
    fm_match = _FRONTMATTER_RE.match(content)
    if not fm_match:
        return ()
    fm = fm_match.group(1)
    block_match = _ALIASES_BLOCK_RE.search(fm)
    if not block_match:
        return ()

    inline = block_match.group("inline").strip()
    rest = block_match.group("rest")

    items: list[str] = []
    if rest:
        # Multi-line list form:
        # aliases:
        #   - foo
        #   - bar
        for line in rest.strip("\n").splitlines():
            stripped = line.strip()
            if stripped.startswith("-"):
                items.append(_strip_quotes(stripped[1:].strip()))
    elif inline.startswith("[") and inline.endswith("]"):
        # Inline list form: aliases: [foo, bar]
        items = [_strip_quotes(s.strip()) for s in inline[1:-1].split(",") if s.strip()]
    elif inline:
        # Scalar form: aliases: yoyo
        items = [_strip_quotes(inline)]

    return tuple(a for a in items if a)


def _strip_quotes(s: str) -> str:
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    return s
