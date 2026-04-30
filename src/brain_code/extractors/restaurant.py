from __future__ import annotations

from datetime import date
from pathlib import Path

from ..config import Settings
from ..files import _atomic_write
from ..templates import expand_entity_stub_template


def ensure_file(entity: str, settings: Settings) -> bool:
    """Create the restaurant file from Template, Food.md if absent.

    Returns True if a new file was created, False if it already existed.
    """
    food_dir = settings.vault_root / "01 Area/Food"
    food_dir.mkdir(parents=True, exist_ok=True)
    file_path = food_dir / f"{entity}.md"
    if file_path.exists():
        return False
    template_path = settings.vault_root / settings.template_food
    if template_path.exists():
        rendered = expand_entity_stub_template(template_path.read_text(encoding="utf-8"), entity)
    else:
        rendered = f"# [[{entity}]]\n\n## Notes\n- \n"
    _atomic_write(file_path, rendered)
    return True


def append_visit(
    entity: str,
    log: dict,
    settings: Settings,
    today: date,
    was_created: bool,
) -> str:
    """Append a dated visit block to the restaurant's file.

    Returns a one-line confirmation string for the Telegram reply.
    """
    file_path = settings.vault_root / "01 Area/Food" / f"{entity}.md"
    visit_block = format_visit(log, today)
    _append_visit_block(file_path, visit_block)

    overall = log.get("overall")
    item_count = len([i for i in (log.get("items") or []) if i.get("name", "").strip()])
    rated_count = len(
        [
            i
            for i in (log.get("items") or [])
            if i.get("name", "").strip() and i.get("rating") is not None
        ]
    )
    if overall is not None:
        summary = f"overall {overall}/10"
    elif rated_count > 0:
        summary = f"{rated_count} item{'s' if rated_count != 1 else ''} rated"
    elif item_count > 0:
        summary = f"{item_count} item{'s' if item_count != 1 else ''} logged"
    else:
        summary = "no rating"

    icon = "🆕" if was_created else "🍽"
    return f"{icon} [[{entity}]] visit logged ({summary})"


def format_visit(log: dict, today: date) -> str:
    lines: list[str] = [f"### {today.isoformat()}"]
    for item in log.get("items", []) or []:
        name = item.get("name", "").strip()
        if not name:
            continue
        rating = item.get("rating")
        if rating is not None:
            lines.append(f"- {name} — {rating}/10")
        else:
            lines.append(f"- {name}")
    if (overall := log.get("overall")) is not None:
        lines.append(f"- **Overall: {overall}/10**")
    return "\n".join(lines)


def _append_visit_block(file_path: Path, visit_block: str) -> None:
    content = file_path.read_text(encoding="utf-8")
    if "## Visits" not in content:
        content = content.rstrip() + "\n\n## Visits\n"
    new_content = content.rstrip() + "\n\n" + visit_block + "\n"
    _atomic_write(file_path, new_content)
