from __future__ import annotations

from pathlib import Path

from .config import Settings, load_settings


def load_prompt(name: str, settings: Settings | None = None) -> str:
    """Read prompts/<name> as text. Name should include the extension."""
    s = settings or load_settings()
    path = _prompt_path(s, name)
    return path.read_text(encoding="utf-8")


def render(prompt_file: str, settings: Settings | None = None, /, **variables: str) -> str:
    """Load prompts/<prompt_file> and substitute {{var}} placeholders.

    Substitution is literal string replacement — no Jinja, no escaping.
    Unknown placeholders are left intact (intentional: easier to debug).
    """
    template = load_prompt(prompt_file, settings)
    out = template
    for key, value in variables.items():
        out = out.replace(f"{{{{{key}}}}}", str(value))
    return out


def _prompt_path(settings: Settings, name: str) -> Path:
    return settings.project_root / "prompts" / name
