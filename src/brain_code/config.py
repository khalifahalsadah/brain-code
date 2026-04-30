from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_PROJECT_ROOT / ".env")

TIMEZONE = ZoneInfo("Asia/Riyadh")
LATE_NIGHT_CUTOFF_HOUR = 4

APPEND_MODEL = "claude-haiku-4-5-20251001"
SYNTHESIZE_MODEL = "claude-sonnet-4-6"

AUTO_REGION_OPEN = "<!-- auto-region -->"
AUTO_REGION_CLOSE = "<!-- /auto-region -->"
NOTES_HEADING = "# 📝 Notes"


@dataclass(frozen=True)
class EntityFolder:
    name: str
    path: Path
    recursive: bool
    auto_stub: bool
    stub_template: Path | None


@dataclass(frozen=True)
class Settings:
    vault_root: Path
    project_root: Path
    api_key: str | None
    daily_notes_subdir: Path = field(default=Path("03 Timestamps"))
    template_daily: Path = field(default=Path("Extras/Templates/Template, Daily Note.md"))
    template_people: Path = field(default=Path("Extras/Templates/Template, People.md"))
    template_food: Path = field(default=Path("Extras/Templates/Template, Food.md"))

    @property
    def daily_notes_root(self) -> Path:
        return self.vault_root / self.daily_notes_subdir

    @property
    def entity_folders(self) -> list[EntityFolder]:
        return [
            EntityFolder(
                name="people",
                path=self.vault_root / "Extras/People",
                recursive=False,
                auto_stub=True,
                stub_template=self.vault_root / self.template_people,
            ),
            EntityFolder(
                name="food",
                path=self.vault_root / "01 Area/Food",
                recursive=False,
                auto_stub=True,
                stub_template=self.vault_root / self.template_food,
            ),
            EntityFolder(
                name="movies_tv",
                path=self.vault_root / "01 Area/Tvs and Movies",
                recursive=True,
                auto_stub=False,
                stub_template=None,
            ),
            EntityFolder(
                name="work_projects",
                path=self.vault_root / "01 Area/Work",
                recursive=False,
                auto_stub=False,
                stub_template=None,
            ),
        ]

    @property
    def unmatched_log(self) -> Path:
        return self.project_root / "unmatched.log"


def load_settings() -> Settings:
    vault_root = Path(os.environ.get("VAULT_ROOT", "/Users/khalifah/Brain")).expanduser()
    return Settings(
        vault_root=vault_root,
        project_root=_PROJECT_ROOT,
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
    )
