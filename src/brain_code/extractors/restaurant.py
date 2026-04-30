from __future__ import annotations

from datetime import date
from pathlib import Path

from ..config import Settings
from ..files import _atomic_write
from ..templates import expand_entity_stub_template


def handle(log: dict, settings: Settings, today: date) -> str:
    """Append a visit block to the restaurant's file, creating it if absent.

    Returns a one-line confirmation string for the Telegram reply.
    """
    entity = log["entity"].strip()
    if not entity:
        return ""

    food_dir = settings.vault_root / "01 Area/Food"
    food_dir.mkdir(parents=True, exist_ok=True)
    file_path = food_dir / f"{entity}.md"

    created = False
    if not file_path.exists():
        template_path = settings.vault_root / settings.template_food
        if template_path.exists():
            template = template_path.read_text(encoding="utf-8")
            rendered = expand_entity_stub_template(template, entity)
        else:
            rendered = f"# [[{entity}]]\n\n## Notes\n- \n"
        _atomic_write(file_path, rendered)
        created = True

    visit_block = format_visit(log, today)
    _append_visit(file_path, visit_block)

    overall = log.get("overall")
    overall_str = f"{overall}/10" if overall is not None else "no rating"
    icon = "🆕" if created else "🍽"
    return f"{icon} [[{entity}]] visit logged ({overall_str})"


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


def _append_visit(file_path: Path, visit_block: str) -> None:
    content = file_path.read_text(encoding="utf-8")
    if "## Visits" not in content:
        content = content.rstrip() + "\n\n## Visits\n"
    new_content = content.rstrip() + "\n\n" + visit_block + "\n"
    _atomic_write(file_path, new_content)
