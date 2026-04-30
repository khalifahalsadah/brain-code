from __future__ import annotations

import sys
from datetime import date as date_cls

import typer

from .claude import append_pass, synthesize_pass
from .config import load_settings
from .dates import (
    daily_note_relative_path,
    target_date_for_append,
    target_date_for_synthesize,
)
from .entities import load_registry
from .files import (
    append_to_auto_region,
    daily_note_path,
    ensure_daily_note,
    pop_last_bullet,
    read_auto_region,
    replace_auto_region,
)
from .recall import recall as recall_fn
from .search import search as search_fn
from .stubs import create_stub, log_unmatched, parse_unknown_flags, strip_unknown_flags
from .style import find_recent_daily_notes, style_examples_text
from .wikilinks import gather_context, list_known_names, match_entities

app = typer.Typer(no_args_is_help=True)


@app.command()
def append(
    text: str = typer.Option(None, "--text", help="Raw input text"),
    stdin: bool = typer.Option(False, "--stdin", help="Read raw input from stdin"),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Skip Claude call; use raw text as bullet. Verifies vault wiring without API cost.",
    ),
) -> None:
    """Real-time append: clean text, resolve wikilinks, append a bullet to today's daily note."""
    raw = _resolve_input(text, stdin)
    if not raw.strip():
        typer.echo("✗ empty input")
        raise typer.Exit(code=1)

    settings = load_settings()
    target = target_date_for_append()
    registry = load_registry(settings)
    matched = match_entities(raw, registry)
    matched_ctx = gather_context(matched)
    known = list_known_names(registry)

    if dry_run:
        bullet = "- " + raw.strip()
        typer.echo(f"[dry-run] matched: {[e.name for e in matched]}")
    else:
        bullet = append_pass(raw, matched_ctx, known, settings)

    flags = parse_unknown_flags(bullet)
    bullet_clean = strip_unknown_flags(bullet)

    for type_, name in flags:
        if type_ in ("people", "food"):
            created = create_stub(settings, type_, name)
            if created is None:
                # Already existed or unsupported type — ignore silently
                continue
        else:
            log_unmatched(settings, type_, name)

    note_path = ensure_daily_note(settings, target)
    append_to_auto_region(note_path, bullet_clean)

    rel = daily_note_relative_path(target)
    typer.echo(f"✓ {rel}: {bullet_clean}")


@app.command()
def synthesize(
    date: str = typer.Option(
        None,
        "--date",
        help="ISO date (YYYY-MM-DD) to synthesize. Defaults to logical-yesterday.",
    ),
) -> None:
    """Nightly: rewrite yesterday's auto-region as polished narrative in user's voice."""
    settings = load_settings()
    target = date_cls.fromisoformat(date) if date else target_date_for_synthesize()
    note_path = daily_note_path(settings, target)

    if not note_path.exists():
        typer.echo(f"⊘ no daily note for {target.isoformat()} — nothing to synthesize")
        return

    raw_bullets = read_auto_region(note_path).strip()
    if not raw_bullets:
        typer.echo(f"⊘ {target.isoformat()}: auto-region is empty — nothing to synthesize")
        return

    registry = load_registry(settings)
    matched = match_entities(raw_bullets, registry)
    entity_ctx = gather_context(matched)

    examples_paths = find_recent_daily_notes(settings, before=target, count=5)
    examples_text = style_examples_text(examples_paths)

    polished = synthesize_pass(
        raw_bullets=raw_bullets,
        style_examples=examples_text,
        entity_context=entity_ctx,
        date_iso=target.isoformat(),
        settings=settings,
    )

    replace_auto_region(note_path, polished)
    excerpt = polished[:200].replace("\n", " ")
    typer.echo(f"📝 {target.isoformat()} synthesized: {excerpt}…")


@app.command()
def recall(
    period: str = typer.Argument(
        "today",
        help="today | yesterday | week | help (leading slash optional)",
    ),
) -> None:
    """Read-only retrieval — used by Telegram slash commands."""
    settings = load_settings()
    typer.echo(recall_fn(period, settings))


@app.command()
def search(
    term: str = typer.Option(None, "--term", help="Search term"),
    b64: str = typer.Option(None, "--b64", help="Base64-encoded search term"),
) -> None:
    """Grep daily-note bullets for a term."""
    if b64:
        import base64

        term = base64.b64decode(b64).decode("utf-8")
    if not term:
        raise typer.BadParameter("provide --term or --b64")
    settings = load_settings()
    typer.echo(search_fn(term, settings))


@app.command()
def undo() -> None:
    """Remove the last bullet from today's auto-region."""
    settings = load_settings()
    target = target_date_for_append()
    path = daily_note_path(settings, target)
    if not path.exists():
        typer.echo(f"📭 no daily note for {target.isoformat()}")
        return
    removed = pop_last_bullet(path)
    if removed is None:
        typer.echo("📭 nothing to undo")
        return
    typer.echo(f"↶ removed:\n{removed}")


def _resolve_input(text: str | None, stdin: bool) -> str:
    if stdin:
        return sys.stdin.read()
    if text is not None:
        return text
    raise typer.BadParameter("provide either --text or --stdin")


if __name__ == "__main__":
    app()
