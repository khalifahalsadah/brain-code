from __future__ import annotations

import os
import re
import tempfile
from datetime import date
from pathlib import Path

from .config import (
    AUTO_REGION_CLOSE,
    AUTO_REGION_OPEN,
    Settings,
)
from .dates import daily_note_relative_path
from .templates import expand_daily_template, inject_auto_region_markers


def daily_note_path(settings: Settings, target: date) -> Path:
    return settings.vault_root / daily_note_relative_path(target)


def ensure_daily_note(settings: Settings, target: date) -> Path:
    """Return the absolute path to target's daily note, creating from template if absent."""
    path = daily_note_path(settings, target)
    if path.exists():
        return path

    template_path = settings.vault_root / settings.template_daily
    template = template_path.read_text(encoding="utf-8")
    rendered = expand_daily_template(template, target)
    rendered = inject_auto_region_markers(rendered)

    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(path, rendered)
    return path


def append_to_auto_region(path: Path, bullet: str) -> None:
    """Append a bullet line just before <!-- /auto-region -->. Inserts markers if missing."""
    content = path.read_text(encoding="utf-8")
    content = inject_auto_region_markers(content)

    bullet_line = bullet.rstrip("\n") + "\n"
    new_content = content.replace(
        AUTO_REGION_CLOSE,
        f"{bullet_line}{AUTO_REGION_CLOSE}",
        1,
    )
    _atomic_write(path, new_content)


def read_auto_region(path: Path) -> str:
    """Return the content between auto-region markers (without the markers themselves)."""
    content = path.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"{re.escape(AUTO_REGION_OPEN)}\n?(.*?){re.escape(AUTO_REGION_CLOSE)}",
        re.DOTALL,
    )
    match = pattern.search(content)
    if not match:
        return ""
    return match.group(1)


def pop_last_bullet(path: Path) -> str | None:
    """Remove the last top-level bullet (and any trailing nested lines) from auto-region.

    Returns the removed text, or None if there's nothing to undo.
    """
    inner = read_auto_region(path)
    lines = inner.rstrip("\n").splitlines()

    last_idx: int | None = None
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].startswith("- "):
            last_idx = i
            break

    if last_idx is None:
        return None

    removed = "\n".join(lines[last_idx:])
    new_inner = "\n".join(lines[:last_idx])
    replace_auto_region(path, new_inner)
    return removed


def replace_auto_region(path: Path, new_inner: str) -> None:
    """Replace content between auto-region markers atomically. Preserves markers."""
    content = path.read_text(encoding="utf-8")
    if AUTO_REGION_OPEN not in content or AUTO_REGION_CLOSE not in content:
        raise ValueError(f"auto-region markers not found in {path}")

    inner = new_inner.rstrip("\n") + "\n" if new_inner else ""
    pattern = re.compile(
        rf"{re.escape(AUTO_REGION_OPEN)}\n?.*?{re.escape(AUTO_REGION_CLOSE)}",
        re.DOTALL,
    )
    new_content = pattern.sub(
        f"{AUTO_REGION_OPEN}\n{inner}{AUTO_REGION_CLOSE}",
        content,
        count=1,
    )
    _atomic_write(path, new_content)


def _atomic_write(path: Path, content: str) -> None:
    """Write content to path atomically (write to temp + os.replace)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass
        raise
