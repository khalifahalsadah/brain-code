from __future__ import annotations

from dataclasses import dataclass

from .claude import append_pass, extract_logs
from .config import Settings
from .dates import (
    daily_note_relative_path,
    target_date_for_append,
)
from .entities import load_registry
from .extractors import movie, restaurant
from .files import append_to_auto_region, ensure_daily_note
from .stubs import create_stub, log_unmatched, parse_unknown_flags, strip_unknown_flags
from .wikilinks import gather_context, list_known_names, match_entities


@dataclass
class CaptureResult:
    bullet: str
    target_path: str
    side_effects: list[str]

    def render(self) -> str:
        out = f"✓ {self.target_path}: {self.bullet}"
        if self.side_effects:
            out += "\n" + "\n".join(self.side_effects)
        return out


def capture(raw_text: str, settings: Settings) -> CaptureResult:
    """Capture pipeline: extract logs first, pre-create entities, then bullet, then visits.

    Order matters: structured-log extraction runs before the bullet pass so that any
    new entity files (e.g., a new restaurant) exist by the time the bullet pass loads
    the registry. This way Haiku sees the entity in its known list and wraps it in
    `[[ ]]` correctly.
    """
    target = target_date_for_append()

    # Pass 1: detect structured side-effect logs
    pre_registry = load_registry(settings)
    known_restaurants = _names_by_type(pre_registry, "food")
    known_movies_tv = _names_by_type(pre_registry, "movies_tv")
    logs = extract_logs(raw_text, known_restaurants, known_movies_tv, settings)

    # Pre-create entity files for each detected log so they join the registry.
    # Movies use OMDB canonical title (which may differ from raw user title).
    created_state: dict[tuple[str, str], bool] = {}
    canonical_movie_titles: dict[str, str] = {}  # raw -> canonical
    movie_omdb_data: dict[str, dict | None] = {}  # canonical -> omdb dict
    for log in logs:
        log_type = log.get("type")
        entity = log.get("entity", "").strip()
        if not entity:
            continue
        if log_type == "restaurant_visit":
            created_state[("restaurant_visit", entity)] = restaurant.ensure_file(entity, settings)
        elif log_type == "movie_watched":
            was_created, canonical, omdb_data = movie.ensure_file(
                entity, settings, kind_hint=log.get("kind")
            )
            canonical_movie_titles[entity] = canonical
            movie_omdb_data[canonical] = omdb_data
            created_state[("movie_watched", canonical)] = was_created

    # Pass 2: bullet generation with the now-updated registry
    registry = load_registry(settings)
    matched = match_entities(raw_text, registry)
    matched_ctx = gather_context(matched)
    known_names = list_known_names(registry)
    bullet = append_pass(raw_text, matched_ctx, known_names, settings)

    # Auto-stubs for any unknown people/food that Haiku flagged
    flags = parse_unknown_flags(bullet)
    bullet_clean = strip_unknown_flags(bullet)
    for type_, name in flags:
        if type_ in ("people", "food"):
            create_stub(settings, type_, name)
        else:
            log_unmatched(settings, type_, name)

    # Append bullet to daily note
    note_path = ensure_daily_note(settings, target)
    append_to_auto_region(note_path, bullet_clean)

    # Pass 3: append visit / watch details to entity files
    side_effects: list[str] = []
    for log in logs:
        log_type = log.get("type")
        entity = log.get("entity", "").strip()
        if not entity:
            continue
        if log_type == "restaurant_visit":
            msg = restaurant.append_visit(
                entity,
                log,
                settings,
                target,
                was_created=created_state.get(("restaurant_visit", entity), False),
            )
            if msg:
                side_effects.append(msg)
        elif log_type == "movie_watched":
            canonical = canonical_movie_titles.get(entity, entity)
            msg = movie.append_watch(
                canonical,
                log,
                settings,
                target,
                was_created=created_state.get(("movie_watched", canonical), False),
            )
            if msg:
                side_effects.append(msg)

    return CaptureResult(
        bullet=bullet_clean,
        target_path=str(daily_note_relative_path(target)),
        side_effects=side_effects,
    )


def _names_by_type(registry, type_: str) -> str:
    names = sorted({e.name for e in registry if e.type == type_})
    if not names:
        return f"(no {type_} entities in vault yet)"
    return "\n".join(f"- {n}" for n in names)
