from __future__ import annotations

from anthropic import Anthropic

from .config import APPEND_MODEL, SYNTHESIZE_MODEL, Settings, load_settings
from .prompts import load_prompt, render


def append_pass(
    raw_text: str,
    matched_entities_ctx: str,
    known_names: str,
    settings: Settings | None = None,
) -> str:
    """Light pass: clean text, resolve [[wikilinks]], output ONE Arabic bullet."""
    s = settings or load_settings()
    if not s.api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    client = Anthropic(api_key=s.api_key)
    system = load_prompt("append_system.md", s)
    user = render(
        "append_user.md.tmpl",
        s,
        raw_text=raw_text,
        matched_entities=matched_entities_ctx or "(none matched)",
        known_names=known_names or "(none)",
    )
    response = client.messages.create(
        model=APPEND_MODEL,
        max_tokens=512,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return _extract_text(response).strip()


def synthesize_pass(
    raw_bullets: str,
    style_examples: str,
    entity_context: str,
    date_iso: str,
    settings: Settings | None = None,
) -> str:
    """Heavy pass: rewrite raw bullets as polished narrative in user's voice."""
    s = settings or load_settings()
    if not s.api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    client = Anthropic(api_key=s.api_key)
    system_text = load_prompt("synthesize_system.md", s)
    cached_block = render(
        "synthesize_cached.md.tmpl",
        s,
        style_examples=style_examples or "(no examples available)",
        entity_context=entity_context or "(no specific entities mentioned)",
    )
    user_text = render(
        "synthesize_user.md.tmpl",
        s,
        date=date_iso,
        raw_bullets=raw_bullets,
    )
    response = client.messages.create(
        model=SYNTHESIZE_MODEL,
        max_tokens=4096,
        system=[
            {"type": "text", "text": system_text},
            {
                "type": "text",
                "text": cached_block,
                "cache_control": {"type": "ephemeral"},
            },
        ],
        messages=[{"role": "user", "content": user_text}],
    )
    return _extract_text(response).strip()


def extract_logs(
    raw_text: str,
    known_restaurants: str,
    known_movies_tv: str,
    settings: Settings | None = None,
) -> list[dict]:
    """Detect structured side-effect logs in a captured message via tool_use.

    Returns the `logs` array. Empty list if nothing structured was detected.
    """
    s = settings or load_settings()
    if not s.api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    client = Anthropic(api_key=s.api_key)
    system = load_prompt("extract_logs_system.md", s)
    user = render(
        "extract_logs_user.md.tmpl",
        s,
        raw_text=raw_text,
        known_restaurants=known_restaurants or "(none yet)",
        known_movies_tv=known_movies_tv or "(none yet)",
    )
    tool = {
        "name": "record_logs",
        "description": (
            "Record structured side-effect logs detected in the captured message. "
            "Always called exactly once per message."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "logs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["restaurant_visit", "movie_watched"],
                            },
                            "entity": {"type": "string"},
                            "items": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "rating": {"type": "number"},
                                    },
                                    "required": ["name"],
                                },
                            },
                            "overall": {"type": "number"},
                            "kind": {
                                "type": "string",
                                "enum": ["movie", "tv"],
                            },
                            "rating": {"type": "number"},
                            "season": {"type": "number"},
                            "episode": {"type": "number"},
                            "notes": {"type": "string"},
                        },
                        "required": ["type", "entity"],
                    },
                },
            },
            "required": ["logs"],
        },
    }
    response = client.messages.create(
        model=APPEND_MODEL,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user}],
        tools=[tool],
        tool_choice={"type": "tool", "name": "record_logs"},
    )
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "record_logs":
            return block.input.get("logs", [])
    return []


def _extract_text(response) -> str:
    for block in response.content:
        if getattr(block, "type", None) == "text":
            return block.text
    return ""
