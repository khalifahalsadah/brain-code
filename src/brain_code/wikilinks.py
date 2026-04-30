from __future__ import annotations

from .entities import Entity


def match_entities(raw_text: str, registry: list[Entity]) -> list[Entity]:
    """Return entities whose name OR any alias appears as a case-insensitive substring of raw_text.

    Latin alphabet matches are case-insensitive; Arabic matches are exact (no case).
    Entities are returned at most once even if multiple names matched.
    """
    text_lower = raw_text.lower()
    matched: list[Entity] = []
    seen_paths: set[str] = set()
    for entity in registry:
        path_key = str(entity.path)
        if path_key in seen_paths:
            continue
        for name in entity.all_names:
            if not name:
                continue
            if name.lower() in text_lower:
                matched.append(entity)
                seen_paths.add(path_key)
                break
    return matched


def gather_context(matched: list[Entity]) -> str:
    """Build a context string of full file contents for matched non-directory entities.

    Directory entities (e.g. work projects, show subfolders) are listed by name only.
    """
    sections: list[str] = []
    dirs: list[Entity] = []
    for entity in matched:
        if entity.is_dir:
            dirs.append(entity)
            continue
        try:
            content = entity.path.read_text(encoding="utf-8")
        except OSError:
            continue
        header = (
            f"=== {entity.type}: {entity.name} ===\n"
            f"(file: {entity.path.name})\n"
        )
        sections.append(header + content.strip())

    if dirs:
        listing = "\n".join(f"- {e.type}: {e.name}" for e in dirs)
        sections.append(f"=== known link targets (no full content) ===\n{listing}")

    return "\n\n".join(sections)


def list_known_names(registry: list[Entity]) -> str:
    """Compact listing of all entity names (and aliases) — useful for compact prompts."""
    by_type: dict[str, list[str]] = {}
    for entity in registry:
        by_type.setdefault(entity.type, []).append(entity.name)
        for alias in entity.aliases:
            by_type[entity.type].append(f"{alias} (alias of {entity.name})")

    parts: list[str] = []
    for type_, names in by_type.items():
        parts.append(f"## {type_}\n" + "\n".join(f"- {n}" for n in sorted(set(names))))
    return "\n\n".join(parts)
