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


def _extract_text(response) -> str:
    for block in response.content:
        if getattr(block, "type", None) == "text":
            return block.text
    return ""
